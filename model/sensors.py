"""Virtual sensors and the XV-101 valve actuator.

The decision engines only ever receive an `Observation`. Truth signals (tracer,
old-water fraction, true flow) live in `Truth` and are never passed to them.
"""
from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

from .params import Config

DS18B20_DISCONNECTED = -127.0


@dataclass(frozen=True)
class Observation:
    """Everything the Arduino could log at one sample. No truth fields allowed."""
    t_s: float
    valve_cmd: int                 # 1 = open commanded
    ft_pulses: int                 # FT-101 pulses in the last sample period
    ft_flow_lpm: float             # FT-101 converted with the NOMINAL K-factor
    pt_kpa: float                  # PI-101 (virtual transducer)
    tt100_c: float                 # TT-100 feed temperature
    tt101_c: float                 # TT-101 endpoint temperature
    ls_open: int
    ls_closed: int


OBS_FIELDS = [f.name for f in fields(Observation)]


@dataclass(frozen=True)
class Truth:
    t_s: float
    q_meter_lpm: float
    q_branch_lpm: float
    q_div_lpm: float
    valve_pos: float
    t_endpoint_c: float
    t_feed_c: float
    f_old_outlet: float
    residual_old_fraction: float
    c_endpoint_uscm: float          # conductivity truth sensor CT-101 (with its own noise)
    age_outlet_h: float
    age_branch_mean_h: float
    p_manifold_kpa: float


class Valve:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.pos = 0.0

    def step(self, cmd: int, dt: float) -> float:
        f = self.cfg.faults
        target = (f.valve_max_open if cmd else 0.0)
        if f.valve_stuck_closed:
            target = 0.0
        rate = self.cfg.sensors.servo_rate_per_s * dt
        self.pos += float(np.clip(target - self.pos, -rate, rate))
        return self.pos

    def switches(self) -> tuple[int, int]:
        s, f = self.cfg.sensors, self.cfg.faults
        ls_open = int(self.pos >= s.ls_open_threshold and not f.ls_open_broken)
        ls_closed = int(self.pos <= s.ls_closed_threshold)
        return ls_open, ls_closed


class SensorBank:
    """Generates FT-101, PI-101, TT-100, TT-101 readings from true values."""

    def __init__(self, cfg: Config, rng: np.random.Generator):
        s = cfg.sensors
        self.cfg = cfg
        self.rng = rng
        self.k_true = s.ft_k_pulses_per_l * (1 + rng.normal(0, s.ft_k_error_sd))
        self.carry = 0.0
        self.bias100 = float(np.clip(rng.normal(0, s.tt_bias_sd_c), -0.5, 0.5))
        self.bias101 = float(np.clip(rng.normal(0, s.tt_bias_sd_c), -0.5, 0.5))
        self.lag100 = None
        self.lag101 = None
        self.frozen101 = None

    def _ds18b20(self, value: float) -> float:
        s = self.cfg.sensors
        v = value + self.rng.normal(0, s.tt_noise_c)
        return round(v / s.tt_res_c) * s.tt_res_c

    def read(self, t: float, dt: float, q_meter_lpm: float, p_kpa: float,
             t_feed: float, t_end: float) -> tuple[int, float, float, float, float]:
        s, f = self.cfg.sensors, self.cfg.faults
        # ---- FT-101: Hall-effect turbine, low-flow under-reading, bias, dropout
        q = q_meter_lpm
        if q < s.ft_qstall_lpm:
            resp = 0.0
        elif q < s.ft_qmin_lpm:
            resp = (q - s.ft_qstall_lpm) / (s.ft_qmin_lpm - s.ft_qstall_lpm)
        else:
            resp = 1.0
        rate = self.k_true * q / 60.0 * resp * f.flow_bias           # pulses per second
        expected = rate * dt + self.carry
        pulses = int(expected)
        self.carry = expected - pulses
        if pulses > 0:
            pulses = max(0, pulses + int(self.rng.integers(-1, 2)))   # +/-1 pulse window jitter
        if f.flow_dropout_t_s is not None and t >= f.flow_dropout_t_s:
            pulses = 0
        flow = pulses / s.ft_k_pulses_per_l / dt * 60.0
        # ---- PI-101
        p = round((p_kpa + self.rng.normal(0, s.pt_noise_kpa)) / s.pt_res_kpa) * s.pt_res_kpa
        # ---- TT-100 / TT-101 first-order lag
        if self.lag100 is None:
            self.lag100, self.lag101 = t_feed, t_end
        self.lag100 += (t_feed - self.lag100) * min(1.0, dt / s.tt_tau_feed_s)
        self.lag101 += (t_end - self.lag101) * min(1.0, dt / s.tt_tau_endpoint_s)
        tt100 = self._ds18b20(self.lag100 + self.bias100)
        tt101 = self._ds18b20(self.lag101 + self.bias101)
        if f.tt101_mode != "ok" and t >= f.tt101_fault_t_s:
            if f.tt101_mode == "disconnected":
                tt101 = DS18B20_DISCONNECTED
            elif f.tt101_mode == "frozen":
                if self.frozen101 is None:
                    self.frozen101 = tt101
                tt101 = self.frozen101
        return pulses, flow, p, tt100, tt101
