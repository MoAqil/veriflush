"""Run one virtual flush event under one verification method.

The same `Config` + `seed` reproduce the same underlying event (same sensor biases,
same noise sequence) for every method; methods differ only in when they close
the valve and what they conclude. All outputs are SIMULATED.
"""
from __future__ import annotations

import math
from dataclasses import asdict

import numpy as np
import pandas as pd

from .decisions import FAILED, METHODS, UNCERTAIN, VERIFIED, Controller, Known
from .hydraulics import solve
from .params import Config, m3_to_l, m3s_to_lpm, with_changes
from .sensors import Observation, SensorBank, Truth, Valve
from .radial import make_transport


PROFILE_N = 20


def run(cfg: Config, method_cls, seed: int = 0, record: bool = True, post_s: float = 8.0):
    rng = np.random.default_rng(seed)
    known = Known.from_config(cfg)
    ctrl: Controller = method_cls(known)
    tr = make_transport(cfg)
    valve = Valve(cfg)
    sens = SensorBank(cfg, rng)
    ct_rng = np.random.default_rng(seed + 10_000)        # truth instrument noise, independent stream
    dt = cfg.policy.dt_s
    pump_off_cfg = with_changes(cfg, hydraulics=dict(source_head_m=0.0))
    rows = []
    cmd = 0
    t = 0.0
    t_end = None
    hyd_cache: dict = {}
    t_feed = cfg.thermal.t_feed_c
    while True:
        pump_on = not ctrl.done
        pos = valve.step(cmd, dt)
        key = (pump_on, round(pos, 4))
        if key not in hyd_cache:
            hyd_cache[key] = solve(cfg if pump_on else pump_off_cfg, pos) if pump_on else None
        hs = hyd_cache[key]
        q_m = hs.q_meter if hs else 0.0
        q_b = hs.q_branch if hs else 0.0
        p_kpa = hs.p_manifold_kpa if hs else 0.0
        t_feed = cfg.thermal.t_feed_c + cfg.thermal.feed_drift_c_per_min * t / 60.0
        tr.step(dt, q_m, q_b, t_feed)
        t += dt
        out = tr.outlet
        pulses, flow, p_meas, tt100, tt101 = sens.read(t, dt, m3s_to_lpm(q_m), p_kpa, t_feed, float(out[2]))
        ls_open, ls_closed = valve.switches()
        obs = Observation(t, cmd, pulses, flow, p_meas, tt100, tt101, ls_open, ls_closed)
        truth = Truth(t, m3s_to_lpm(q_m), m3s_to_lpm(q_b), m3s_to_lpm(q_m - q_b), pos, float(out[2]), t_feed,
                      float(out[0]), tr.residual_old_fraction,
                      float(out[1]) * (1 + ct_rng.normal(0, cfg.sensors.ct_noise_frac)),
                      float(out[3]), tr.branch_mean(3), p_kpa)
        was_done = ctrl.done
        cmd = ctrl.step(obs)
        if record:
            r = {f"obs_{k}": v for k, v in asdict(obs).items()}
            r.update({f"truth_{k}": v for k, v in asdict(truth).items() if k != "t_s"})
            r["ctrl_cmd_next"] = cmd
            r["ctrl_phi"] = getattr(ctrl, "phi", math.nan)
            r["ctrl_v_l"] = ctrl.v
            for i, f in enumerate(tr.profile(PROFILE_N)):
                r[f"truth_profile_{i:02d}"] = round(float(f), 4)
            rows.append(r)
        if ctrl.done and not was_done:
            t_end = t + post_s
        if t_end is not None and t >= t_end:
            break
        if t > cfg.policy.t_max_s + 60:
            break
    res = ctrl.res
    resid = tr.residual_old_fraction
    adequate = resid <= cfg.adequate_residual
    summary = dict(
        scenario=cfg.name, method=ctrl.name, seed=seed, verdict=res.verdict, reason=res.reason,
        warnings=" | ".join(res.warnings), flagged=bool(res.warnings) or res.verdict != VERIFIED,
        t_close_s=res.t_close_s, flush_duration_s=res.t_close_s - cfg.policy.t_valve_cmd_s,
        v_recorded_l=res.v_recorded_l,
        water_used_l=m3_to_l(tr.vol_out + tr.vol_div),
        water_branch_l=m3_to_l(tr.vol_out), water_diverted_l=m3_to_l(tr.vol_div),
        true_branch_volume_l=cfg.geometry.branch_volume_l, configured_l=cfg.configured_l,
        true_volumes_exchanged=m3_to_l(tr.vol_out) / cfg.geometry.branch_volume_l,
        residual_old_fraction=resid, truth_adequate=adequate,
        has_fault=cfg.has_fault,
        tracer_initial=None, tracer_balance_error=None,
    )
    for k, v in res.extras.items():
        summary[f"vf_{k}"] = v
    summary["outcome"] = classify(res.verdict, adequate)
    df = pd.DataFrame(rows) if record else None
    return summary, df, tr


def classify(verdict: str, adequate: bool) -> str:
    if verdict == VERIFIED:
        return "True pass" if adequate else "False pass"
    if verdict == FAILED:
        return "True failure" if not adequate else "False failure"
    return "Uncertain"


def run_all_methods(cfg: Config, seed: int = 0, record: bool = True):
    return [run(cfg, m, seed, record) for m in METHODS]


def time_to_adequate(cfg: Config, seed: int = 0, horizon_s: float = 600.0) -> float:
    """Time after the valve command until the TRUE residual first drops below the adequacy
    threshold, with the valve held open (reference run, not a method)."""
    tr = make_transport(cfg)
    valve = Valve(cfg)
    dt = cfg.policy.dt_s
    t = 0.0
    while t < horizon_s:
        cmd = 1 if t >= cfg.policy.t_valve_cmd_s else 0
        pos = valve.step(cmd, dt)
        hs = solve(cfg, pos)
        tr.step(dt, hs.q_meter, hs.q_branch, cfg.thermal.t_feed_c)
        t += dt
        if tr.residual_old_fraction <= cfg.adequate_residual:
            return t - cfg.policy.t_valve_cmd_s
    return math.nan
