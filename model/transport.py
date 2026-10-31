"""1-D transport of old-water fraction, conductivity tracer, temperature and water age.

Model: the upstream line and the monitored branch are discretised into equal-volume
cells. Each branch cell has a MOBILE zone (fraction 1-beta, tanks-in-series
advection) and a SLOW near-wall zone (fraction beta) that exchanges with the mobile
zone by first-order mass transfer (mobile-immobile / two-region model). This gives
the long tail typical of laminar pipe flow that pure tanks-in-series cannot.

Mobile cell i:   (1-b) dX_i/dt = (Q/Vc)(X_{i-1}-X_i) + b k (S_i - X_i)
Slow cell i:          dS_i/dt = k (X_i - S_i)
Wall heat loss (both zones):  dT/dt += (T_env - T)/tau_wall ;  age: dA/dt += 1
k = 1/exchange_tau_s for solute, old fraction and age; 1/heat_exchange_tau_s for heat.
Integrated with explicit Euler sub-steps (Courant <= max_cell_fraction, k*h <= 0.1).
"""
from __future__ import annotations

import math

import numpy as np

from .params import Config, l_to_m3

F, C, T, A = 0, 1, 2, 3


class Transport:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        tr, th, tp = cfg.tracer, cfg.thermal, cfg.transport
        self.n_up, self.n_br = tp.n_cells_upstream, tp.n_cells_branch
        self.beta = tp.slow_fraction
        self.v_up = l_to_m3(cfg.geometry.upstream_volume_l)
        self.v_br = l_to_m3(cfg.geometry.branch_volume_l)
        self.vc_up = self.v_up / self.n_up
        self.vc_br = self.v_br / self.n_br
        self.up = np.zeros((4, self.n_up))
        self.up[C], self.up[T], self.up[A] = tr.c_fresh_uscm, th.t_env_c, tr.age_old_h
        self.br = np.zeros((4, self.n_br))
        self.br[F], self.br[C], self.br[T], self.br[A] = 1.0, tr.c_old_uscm, th.t_old_c, tr.age_old_h
        self.sl = self.br.copy()                       # slow zone, same initial state
        k_s = 1.0 / tp.exchange_tau_s if tp.exchange_tau_s > 0 else 0.0
        k_h = 1.0 / tp.heat_exchange_tau_s if tp.heat_exchange_tau_s > 0 else 0.0
        self.k = np.array([k_s, k_s, k_h, k_s])[:, None]
        self.tracer_out = 0.0
        self.old_out = 0.0
        self.vol_out = 0.0
        self.vol_div = 0.0

    # ---------- truth ----------
    @property
    def residual_old_fraction(self) -> float:
        return float((1 - self.beta) * self.br[F].mean() + self.beta * self.sl[F].mean())

    @property
    def outlet(self) -> np.ndarray:
        return self.br[:, -1]

    def tracer_inventory(self) -> float:
        cf = self.cfg.tracer.c_fresh_uscm
        return float(((1 - self.beta) * (self.br[C] - cf) * self.vc_br).sum()
                     + (self.beta * (self.sl[C] - cf) * self.vc_br).sum()
                     + ((self.up[C] - cf) * self.vc_up).sum())

    def profile(self, n: int = 20) -> np.ndarray:
        """TRUTH: old-water fraction along the branch (inlet -> endpoint), resampled to n points."""
        f = (1 - self.beta) * self.br[F] + self.beta * self.sl[F]
        return np.interp((np.arange(n) + 0.5) / n, (np.arange(self.n_br) + 0.5) / self.n_br, f)

    def branch_mean(self, row: int) -> float:
        return float((1 - self.beta) * self.br[row].mean() + self.beta * self.sl[row].mean())

    # ---------- dynamics ----------
    def step(self, dt: float, q_meter: float, q_branch: float, t_feed: float) -> None:
        th, tr, tp = self.cfg.thermal, self.cfg.tracer, self.cfg.transport
        vm = (1 - self.beta) * self.vc_br
        frac = max(q_meter * dt / self.vc_up, q_branch * dt / vm, float(self.k.max()) * dt / 0.1)
        n_sub = max(1, int(math.ceil(frac / tp.max_cell_fraction)) if frac > 0 else 1)
        h = dt / n_sub
        inflow = np.array([0.0, tr.c_fresh_uscm, t_feed, tr.age_feed_h])
        k_wall = h / th.tau_wall_s
        b = self.beta
        for _ in range(n_sub):
            a_up = q_meter * h / self.vc_up
            prev = np.concatenate([inflow[:, None], self.up[:, :-1]], axis=1)
            up_out = self.up[:, -1].copy()
            self.up += a_up * (prev - self.up)
            a_br = q_branch * h / vm
            prev = np.concatenate([up_out[:, None], self.br[:, :-1]], axis=1)
            out = self.br[:, -1].copy()
            self.br += a_br * (prev - self.br)
            if b > 0:
                ex = self.k * h * (self.sl - self.br)          # mobile <- slow
                self.br += ex * b / (1 - b)
                self.sl -= ex
            dv = q_branch * h
            self.tracer_out += (out[C] - tr.c_fresh_uscm) * dv
            self.old_out += out[F] * dv
            self.vol_out += dv
            self.vol_div += (q_meter - q_branch) * h
            for z in (self.up, self.br, self.sl):
                z[T] += k_wall * (th.t_env_c - z[T])
                z[A] += h / 3600.0
