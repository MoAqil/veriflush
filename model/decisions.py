"""Three flush-verification methods, run as online controllers.

Each controller sees only:
  * `Known`   - what the operator configured (volume, policy, sensor K-factor)
  * `Observation` samples, one per period, in time order.
It returns a valve command each step and, when finished, a verdict:
  VERIFIED / FAILED / UNCERTAIN, a human-readable reason and warnings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .params import Config, Policy
from .sensors import DS18B20_DISCONNECTED, Observation

VERIFIED, FAILED, UNCERTAIN = "Verified", "Failed", "Uncertain"


@dataclass(frozen=True)
class Known:
    configured_l: float
    configured_upstream_l: float
    policy: Policy
    k_nominal: float

    @classmethod
    def from_config(cls, cfg: Config) -> "Known":
        return cls(cfg.configured_l, cfg.configured_upstream_l, cfg.policy, cfg.sensors.ft_k_pulses_per_l)


@dataclass
class Result:
    method: str
    verdict: str = ""
    reason: str = ""
    warnings: list = field(default_factory=list)
    t_close_s: float = math.nan
    v_recorded_l: float = math.nan
    extras: dict = field(default_factory=dict)


def _f(x) -> float:
    """missing-value safe float (None/NaN -> nan)"""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return math.nan
    return x


class Controller:
    name = "base"

    def __init__(self, known: Known):
        self.k = known
        self.p = known.policy
        self.cmd = 0
        self.done = False
        self.res = Result(self.name)
        self.v = 0.0

    def _integrate(self, obs: Observation):
        q = _f(obs.ft_flow_lpm)
        if not math.isnan(q):
            self.v += q * self.p.dt_s / 60.0

    def _close(self, t, verdict, reason):
        self.cmd = 0
        self.done = True
        self.res.verdict, self.res.reason = verdict, reason
        self.res.t_close_s = t
        self.res.v_recorded_l = self.v

    def step(self, obs: Observation) -> int:
        raise NotImplementedError


class TimerOnly(Controller):
    """Open the valve for a fixed time sized from the design flow; always records completion."""
    name = "Timer-only"

    def __init__(self, known: Known):
        super().__init__(known)
        self.t_run = known.policy.target_volumes * known.configured_l / known.policy.design_flow_lpm * 60.0

    def step(self, obs):
        if self.done:
            return 0
        t = obs.t_s
        self._integrate(obs)
        if t >= self.p.t_valve_cmd_s:
            self.cmd = 1
        if t >= self.p.t_valve_cmd_s + self.t_run:
            self._close(t, VERIFIED, f"Timer elapsed ({self.t_run:.0f} s). Flush recorded as complete.")
        return self.cmd


class FlowVolume(Controller):
    """Flush until the upstream meter records target x configured volume."""
    name = "Flow + configured volume"

    def step(self, obs):
        if self.done:
            return 0
        t = obs.t_s
        if t >= self.p.t_valve_cmd_s:
            self.cmd = 1
            self._integrate(obs)
        need = self.p.target_volumes * self.k.configured_l
        if self.v >= need:
            self._close(t, VERIFIED, f"Meter recorded {self.v:.3f} L >= {need:.3f} L "
                                     f"({self.p.target_volumes:.0f} x configured {self.k.configured_l:.3f} L).")
        elif t >= self.p.t_max_s:
            self._close(t, FAILED, f"Time limit reached with only {self.v:.3f} L of {need:.3f} L recorded.")
        return self.cmd


def _valid_temp(x: float) -> bool:
    return (not math.isnan(x)) and x != DS18B20_DISCONNECTED and x != 85.0 and -10.0 <= x <= 60.0


class VeriFlush(Controller):
    """Rule-based verification: valve feedback + metered volume + endpoint thermal
    response + sensor plausibility. Endpoint-anchored volume accounting."""
    name = "VeriFlush"

    def __init__(self, known: Known):
        super().__init__(known)
        self.pre100, self.pre101, self.pre_p = [], [], []
        self.t0_101 = self.t0_100 = self.p0 = math.nan
        self.contrast = math.nan
        self.endpoint_ok = True
        self.endpoint_issue = ""
        self.weak = False
        self.v_arr = math.nan
        self.t_arr = math.nan
        self.phi = math.nan
        self.plateau_s = 0.0
        self.valve_state = "unknown"     # confirmed | partial | switch_fault | not_open
        self.zero_flow_s = 0.0
        self.had_flow = False
        self.dropout = False
        self.last_good_q = math.nan
        self.same_101 = 0
        self.last_101 = math.nan
        self.e_expected = known.configured_l + known.configured_upstream_l
        self.q_sum = 0.0
        self.q_n = 0
        self.dp_sum = 0.0
        self.dp_n = 0

    # ---------------- helpers ----------------
    def _verdict(self, t, verdict, reason):
        self.res.extras.update(dict(
            contrast_c=self.contrast, v_arrival_l=self.v_arr, t_arrival_s=self.t_arr,
            arrival_ratio=self._ratio(), v_est_l=self._v_est(),
            valve_state=self.valve_state, endpoint_ok=self.endpoint_ok, dropout=self.dropout,
            mean_dp_kpa=(self.dp_sum / self.dp_n) if self.dp_n else math.nan,
            n_eff=self._n_eff()))
        self._close(t, verdict, reason)

    def _v_est(self) -> float:
        """Endpoint-anchored estimate of the branch volume, in METERED litres:
        metered volume at fresh-water arrival minus the configured upstream dead volume."""
        if math.isnan(self.v_arr):
            return math.nan
        return max(self.v_arr - self.k.configured_upstream_l, 0.2 * self.k.configured_l)

    def _ratio(self) -> float:
        return self._v_est() / self.k.configured_l

    def _n_eff(self) -> float:
        if math.isnan(self.v_arr):
            return self.v / self.k.configured_l
        return self.v / self._v_est()

    def _warn(self, w):
        if w not in self.res.warnings:
            self.res.warnings.append(w)

    # ---------------- main loop ----------------
    def step(self, obs):
        if self.done:
            return 0
        p, t = self.p, obs.t_s
        tt100, tt101, pk = _f(obs.tt100_c), _f(obs.tt101_c), _f(obs.pt_kpa)
        q = _f(obs.ft_flow_lpm)

        # ---- phase 0: baseline before opening
        if t < p.t_valve_cmd_s:
            if _valid_temp(tt100): self.pre100.append(tt100)
            if _valid_temp(tt101): self.pre101.append(tt101)
            if not math.isnan(pk): self.pre_p.append(pk)
            return 0
        if self.cmd == 0 and not self.done:
            self.cmd = 1
            self.t0_100 = sum(self.pre100) / len(self.pre100) if self.pre100 else math.nan
            self.t0_101 = sum(self.pre101) / len(self.pre101) if self.pre101 else math.nan
            self.p0 = sum(self.pre_p) / len(self.pre_p) if self.pre_p else math.nan
            if math.isnan(self.t0_101):
                self.endpoint_ok, self.endpoint_issue = False, "TT-101 gave no valid reading before the flush"
            if math.isnan(self.t0_100):
                self.endpoint_ok, self.endpoint_issue = False, "TT-100 gave no valid reading before the flush"
            if self.endpoint_ok:
                self.contrast = self.t0_101 - self.t0_100
                if abs(self.contrast) < p.min_contrast_c:
                    self.weak = True
            return 1

        # ---- volume from the meter
        self._integrate(obs)
        if not math.isnan(q):
            if q > p.no_flow_lpm:
                self.had_flow = True
                self.last_good_q = q
                self.zero_flow_s = 0.0
                self.q_sum += q
                self.q_n += 1
            else:
                self.zero_flow_s += p.dt_s
        else:
            self.zero_flow_s += p.dt_s
        if not math.isnan(pk) and not math.isnan(self.p0):
            self.dp_sum += self.p0 - pk
            self.dp_n += 1

        # ---- valve feedback
        if t >= p.t_valve_cmd_s + p.valve_confirm_s and self.valve_state in ("unknown", "pending"):
            if obs.ls_open and not obs.ls_closed:
                self.valve_state = "confirmed"
            elif obs.ls_closed:
                self.valve_state = "not_open"
            else:
                self.valve_state = "pending"   # decide with flow evidence below
        if self.valve_state == "pending" and self.q_n >= 5:
            mean_q = self.q_sum / self.q_n
            if mean_q < 0.8 * p.design_flow_lpm:
                self.valve_state = "partial"
                self._warn(f"LS-OPEN not made and flow is {mean_q:.2f} L/min "
                           f"({mean_q / p.design_flow_lpm:.0%} of design): XV-101 probably only partly open")
            else:
                self.valve_state = "switch_fault"
                self._warn("LS-OPEN not made although flow is normal: limit switch or wiring fault")

        # ---- endpoint sensor health
        if self.endpoint_ok and not _valid_temp(tt101):
            self.endpoint_ok = False
            self.endpoint_issue = f"TT-101 invalid reading ({tt101:g}) at t={t:.0f} s (disconnected?)"
        if self.endpoint_ok:
            self.same_101 = self.same_101 + 1 if tt101 == self.last_101 else 0
            self.last_101 = tt101
        # ---- endpoint response
        if self.endpoint_ok and not self.weak and _valid_temp(tt100):
            denom = tt100 - self.t0_101
            self.phi = (tt101 - self.t0_101) / denom if abs(denom) > 1e-6 else math.nan
            if math.isnan(self.v_arr) and self.phi >= p.phi_arrival:
                self.v_arr, self.t_arr = self.v, t
                r = self._ratio()
                if r > p.ratio_warn_high:
                    self._warn(f"Endpoint-anchored branch volume is {r:.1f}x the configured volume: "
                               "possible diversion/leak after the meter, meter over-reading, or configured volume too small")
                elif r < p.ratio_warn_low:
                    self._warn(f"Endpoint-anchored branch volume is only {r:.1f}x the configured volume: "
                               "meter under-reading or configured volume too large")
            self.plateau_s = self.plateau_s + p.dt_s if self.phi >= p.phi_plateau else 0.0
            # frozen: no change at all while fresh water should already be there
            if (math.isnan(self.v_arr) and self.same_101 >= 15 and self.v > 1.5 * self.e_expected):
                self.endpoint_ok = False
                self.endpoint_issue = "TT-101 reading frozen while fresh water was expected at the endpoint"

        # ---- flow-signal dropout (flow stopped but endpoint still responding / pressure still drawn)
        dp_now = (self.p0 - pk) if not (math.isnan(pk) or math.isnan(self.p0)) else math.nan
        drawing = (not math.isnan(dp_now)) and dp_now > p.dp_draw_min_kpa
        if (self.had_flow and not self.dropout and self.zero_flow_s >= p.dropout_confirm_s and drawing):
            self.dropout = True
            self._warn(f"FT-101 signal lost at about t={t - self.zero_flow_s:.0f} s while the manifold pressure "
                       "still shows the branch drawing water")

        # ================= decisions =================
        # 1. valve never opened
        if self.valve_state == "not_open" and self.zero_flow_s >= 10:
            self._verdict(t, FAILED, "XV-101 did not open: LS-CLOSED stayed made and no flow was recorded.")
            return 0
        # 2. no flow at all with valve apparently open
        if (not self.had_flow and self.zero_flow_s >= p.blockage_confirm_s and self.valve_state != "not_open"):
            if drawing:
                self._verdict(t, UNCERTAIN, "No FT-101 pulses, but pressure shows the branch drawing water: "
                                            "flow sensor fault suspected; exchange cannot be quantified.")
            else:
                self._verdict(t, FAILED, f"No flow for {self.zero_flow_s:.0f} s with the valve commanded open and no "
                                         "pressure drop at the manifold: blockage or closed isolation valve.")
            return 0
        # 3. severe mismatch
        if not math.isnan(self.v_arr) and self._ratio() > p.ratio_fail:
            self._verdict(t, FAILED, f"Fresh water needed {self._ratio():.1f}x the configured branch volume to reach "
                                     "the endpoint: metered water is not reaching the branch end (diversion/leak) "
                                     "or the configured volume is badly wrong.")
            return 0
        if (self.endpoint_ok and not self.weak and math.isnan(self.v_arr) and not self.dropout
                and self.v > p.ratio_fail * self.e_expected):
            self._verdict(t, FAILED, f"{self.v:.2f} L metered ({self.v / self.e_expected:.1f}x expected) but no fresh-water "
                                     "response at the endpoint: water is not reaching the branch end.")
            return 0

        endpoint_usable = self.endpoint_ok and not self.weak
        need = p.target_volumes * self.k.configured_l
        # 4. normal completion with endpoint evidence
        if endpoint_usable and not math.isnan(self.v_arr) and not self.dropout:
            if self._n_eff() >= p.target_volumes and self.plateau_s >= p.plateau_hold_s:
                if self.valve_state == "confirmed":
                    self._verdict(t, VERIFIED, f"Valve confirmed open; fresh water reached the endpoint at "
                                               f"{self.v_arr:.3f} L (branch volume estimate {self._ratio():.2f}x configured); "
                                               f"{self._n_eff():.1f} endpoint-anchored volumes exchanged; endpoint "
                                               f"temperature stable at {self.phi:.0%} of the feed contrast.")
                else:
                    self._verdict(t, UNCERTAIN, "Hydraulic and endpoint evidence complete, but valve position "
                                                f"feedback is inconsistent ({self.valve_state.replace('_', ' ')}).")
                return 0
        # 5. fallback when the endpoint cannot be used: meter-only flush, but never 'Verified'
        if not endpoint_usable and self.v >= need:
            why = ("temperature contrast only {:.2f} degC (< {:.1f})".format(abs(self.contrast), p.min_contrast_c)
                   if self.weak else self.endpoint_issue)
            self._verdict(t, UNCERTAIN, f"Metered {self.v:.3f} L (>= {need:.3f} L) but endpoint evidence unavailable: {why}.")
            return 0
        # 6. dropout: wait for thermal plateau + an estimated volume, then report Uncertain
        if self.dropout and endpoint_usable:
            est = self.v + (self.last_good_q * self.zero_flow_s / 60.0 if not math.isnan(self.last_good_q) else 0)
            n_est = est / self.k.configured_l
            if self.plateau_s >= p.plateau_hold_s and n_est >= p.target_volumes:
                self._verdict(t, UNCERTAIN, f"Endpoint shows fresh water, but FT-101 failed during the flush; volume "
                                            f"only estimated ({est:.2f} L), not measured.")
                return 0
        # 7. time limit
        if t >= p.t_max_s:
            if not endpoint_usable:
                why = "weak temperature contrast" if self.weak else self.endpoint_issue
                self._verdict(t, UNCERTAIN, f"Time limit: only {self.v:.3f} L metered and endpoint evidence unavailable ({why}).")
            elif self.dropout:
                self._verdict(t, UNCERTAIN, "Time limit reached after FT-101 signal loss; exchange cannot be confirmed.")
            elif math.isnan(self.v_arr):
                self._verdict(t, FAILED, f"Time limit: fresh water never reached the endpoint ({self.v:.3f} L metered).")
            else:
                self._verdict(t, FAILED, f"Time limit: only {self._n_eff():.1f} of {p.target_volumes:.0f} endpoint-anchored "
                                         "volumes exchanged (flow too low).")
            return 0
        return 1


METHODS = [TimerOnly, FlowVolume, VeriFlush]
