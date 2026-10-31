"""Quasi-steady hydraulics of the VeriFlush rig (manifold, reference branch,
monitored branch with diversion tee). All heads in metres of water above the
feed-tank water level, flows in m^3/s.

Head loss in a path:  h(Q) = (f(Re) L/D + sum K) * v^2/(2g) + dz
with f = 64/Re (laminar, Re<2000), Blasius 0.316 Re^-0.25 (Re>4000) and linear
interpolation in between (assumption: smooth tube, no transition hysteresis).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.optimize import brentq

from .params import G, NU, RHO, Config

CLOSED_K = 1e12


def friction_factor(re: float) -> float:
    if re <= 0:
        return 0.0
    if re < 2000:
        return 64.0 / re
    f_lam = 64.0 / 2000.0
    f_turb = 0.316 * 4000 ** -0.25
    if re < 4000:
        w = (re - 2000) / 2000.0
        return f_lam + w * (f_turb - f_lam)
    return 0.316 * re ** -0.25


@dataclass(frozen=True)
class Path:
    length_m: float
    d_m: float
    k_sum: float
    dz_m: float = 0.0

    @property
    def area(self) -> float:
        return math.pi * self.d_m ** 2 / 4

    def head(self, q: float) -> float:
        """head loss + elevation for flow q >= 0"""
        if q <= 0:
            return self.dz_m
        v = q / self.area
        re = v * self.d_m / NU
        f = friction_factor(re)
        return (f * self.length_m / self.d_m + self.k_sum) * v * v / (2 * G) + self.dz_m

    def flow(self, h_avail: float) -> float:
        """invert head(): flow for available head (0 if not enough head or closed)"""
        if self.k_sum >= CLOSED_K or h_avail <= self.dz_m:
            return 0.0
        hi = 1e-6
        while self.head(hi) < h_avail:
            hi *= 2
            if hi > 1:
                break
        return brentq(lambda q: self.head(q) - h_avail, 0.0, hi, xtol=1e-14)


def valve_k(k_open: float, opening: float) -> float:
    """Ball-valve style characteristic: Cv ~ x^2  =>  K = K_open / x^4.
    opening <= 0.02 treated as shut (assumption)."""
    if opening <= 0.02:
        return CLOSED_K
    return min(k_open / opening ** 4, CLOSED_K)


@dataclass
class HydState:
    q_ref: float
    q_meter: float      # through FT-101 (true)
    q_branch: float     # through the coil to the endpoint
    q_div: float        # diverted after the meter
    h_manifold: float
    h_junction: float

    @property
    def p_manifold_kpa(self) -> float:
        return RHO * G * self.h_manifold / 1000.0


def solve(cfg: Config, valve_opening: float) -> HydState:
    g, h = cfg.geometry, cfg.hydraulics
    d = g.branch_id_m
    up = Path(0.5, d, h.k_hv + h.k_meter)
    k_coil = h.k_fittings + h.k_restriction + valve_k(h.k_valve_open, valve_opening) + 1.0
    if cfg.faults.blockage:
        k_coil = CLOSED_K
    coil = Path(g.branch_length_m, d, k_coil, g.outlet_rise_m)
    k_div = h.k_diversion_open / max(h.diversion_open, 1e-9) ** 2 if h.diversion_open > 0 else CLOSED_K
    div = Path(h.diversion_length_m, d, k_div, g.outlet_rise_m)
    ref = Path(g.ref_length_m, d, h.k_hv + 150.0 + 1.0, g.outlet_rise_m)   # HV-201 throttled to balance (assumed)

    def monitored(hm: float):
        if hm <= g.outlet_rise_m:
            return 0.0, 0.0, 0.0, hm

        def resid(hj):
            return up.flow(hm - hj) - coil.flow(hj) - div.flow(hj)
        lo, hi = g.outlet_rise_m, hm
        if resid(lo) <= 0:
            return 0.0, 0.0, 0.0, hm
        hj = brentq(resid, lo, hi, xtol=1e-12)
        qc, qd = coil.flow(hj), div.flow(hj)
        return qc + qd, qc, qd, hj

    def total(hm):
        qm, _, _, _ = monitored(hm)
        return ref.flow(hm) + qm

    f = lambda hm: hm - (h.source_head_m - h.source_r_s2m5 * total(hm) ** 2)
    hm = brentq(f, 0.0, h.source_head_m, xtol=1e-12)
    qm, qc, qd, hj = monitored(hm)
    return HydState(ref.flow(hm), qm, qc, qd, hm, hj)
