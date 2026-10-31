"""Radially resolved laminar transport (cross-check backend for `transport.Transport`).

The branch is split into M equal-area annuli ("rings") x Nz axial cells. Each ring
carries plug flow at its share of the Poiseuille profile, u(r) = 2U(1 - r^2/R^2); rings
exchange salt / heat / age by radial diffusion only. No tuned N, beta or tau: the tail
comes from the velocity profile and the molecular diffusivities.

  ring j (equal area, s_j = (j+0.5)/M):   u_j = 2U(1 - s_j)          (sum u_j / M = U)
  advection (first-order upwind, Courant <= 1 in the fastest ring)
  radial exchange per unit ring volume:   g_i = 2 D rho_i M / (R^2 dRho_i)
  heat: rings + silicone wall node (heat capacity C_w) + loss to room (G_out)

With D -> 0 the in-pipe residual tends to the laminar segregated-flow result
r(theta) = 1 - theta (theta < 1/2), 1/(4 theta) (theta >= 1/2)   [see laminar_bound].
Radial exchange is integrated exactly per sub-step with a matrix exponential, so
it is unconditionally stable. Exposes the same interface as transport.Transport.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.linalg import expm

from .params import CP, RHO, Config, l_to_m3

F, C, T, A = 0, 1, 2, 3
K_WATER = 0.598          # W/(m.K), water ~20 degC
ALPHA_WATER = K_WATER / (RHO * CP)   # ~1.43e-7 m^2/s


def laminar_bound(theta):
    """In-pipe old-water fraction after theta pipe volumes of laminar (Poiseuille) flow
    with no radial mixing at all (segregated flow)."""
    th = np.asarray(theta, dtype=float)
    return np.where(th < 0.5, 1.0 - th, 1.0 / (4.0 * np.maximum(th, 1e-12)))


def _radial_matrix(m: int, r: float, d: float) -> np.ndarray:
    rho_i = np.sqrt(np.arange(1, m) / m)                 # interfaces
    rho_c = np.sqrt((np.arange(m) + 0.5) / m)            # ring centres (area-median)
    g = d * 2 * rho_i * m / (r ** 2 * np.diff(rho_c))
    k = np.zeros((m, m))
    for i, gi in enumerate(g):
        k[i, i] -= gi
        k[i + 1, i + 1] -= gi
        k[i, i + 1] += gi
        k[i + 1, i] += gi
    return k


class RadialTransport:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        tr, th, tp, g = cfg.tracer, cfg.thermal, cfg.transport, cfg.geometry
        self.m, self.nz = tp.n_rings, tp.n_axial
        self.r = g.branch_id_m / 2
        self.area = math.pi * self.r ** 2
        self.v_br = l_to_m3(g.branch_volume_l)
        self.l_eff = self.v_br / self.area                 # fittings volume lengthens the branch
        self.dz = self.l_eff / self.nz
        self.u_rel = 2.0 * (1.0 - (np.arange(self.m) + 0.5) / self.m)
        self.cell_v = self.v_br / (self.m * self.nz)
        # upstream line: same tanks-in-series as the 1-D model
        self.n_up = tp.n_cells_upstream
        self.vc_up = l_to_m3(g.upstream_volume_l) / self.n_up
        self.up = np.zeros((4, self.n_up))
        self.up[C], self.up[T], self.up[A] = tr.c_fresh_uscm, th.t_env_c, tr.age_old_h
        # branch state: rows F, C, T, A ; shape (4, M, Nz)
        self.x = np.zeros((4, self.m, self.nz))
        self.x[F], self.x[C], self.x[T], self.x[A] = 1.0, tr.c_old_uscm, th.t_old_c, tr.age_old_h
        self.tw = np.full(self.nz, th.t_old_c)             # silicone wall temperature
        # radial operators
        f = tp.radial_mix_factor
        self.k_s = _radial_matrix(self.m, self.r, tp.d_salt_m2s * f)
        kh = np.zeros((self.m + 1, self.m + 1))
        kh[:self.m, :self.m] = _radial_matrix(self.m, self.r, ALPHA_WATER * f)
        c_ring = RHO * CP * self.area / self.m             # J/(K.m) per ring
        c_w = tp.wall_heat_capacity_j_mk
        g_in = tp.wall_conductance_w_mk
        c_water = RHO * CP * self.area
        g_out = (c_water + c_w) / th.tau_wall_s            # keeps the lumped tube time constant
        o, w = self.m - 1, self.m
        kh[o, o] -= g_in / c_ring
        kh[o, w] += g_in / c_ring
        kh[w, w] -= (g_in + g_out) / c_w
        kh[w, o] += g_in / c_w
        self.k_h = kh
        self._e = {}
        self.tracer_out = 0.0
        self.old_out = 0.0
        self.vol_out = 0.0
        self.vol_div = 0.0

    def _expm(self, h):
        key = round(h, 9)
        if key not in self._e:
            self._e[key] = (expm(self.k_s * h), expm(self.k_h * h))
        return self._e[key]

    # ---------- truth ----------
    @property
    def residual_old_fraction(self) -> float:
        return float(self.x[F].mean())

    @property
    def outlet(self) -> np.ndarray:
        """flow-weighted (mixing-cup) outlet values"""
        return self.x[:, :, -1] @ self.u_rel / self.m

    def profile(self, n: int = 20) -> np.ndarray:
        """TRUTH: cross-section-mean old-water fraction along the branch, resampled to n points."""
        f = self.x[F].mean(axis=0)
        return np.interp((np.arange(n) + 0.5) / n, (np.arange(self.nz) + 0.5) / self.nz, f)

    def branch_mean(self, row: int) -> float:
        return float(self.x[row].mean())

    def tracer_inventory(self) -> float:
        cf = self.cfg.tracer.c_fresh_uscm
        return float(((self.x[C] - cf) * self.cell_v).sum() + ((self.up[C] - cf) * self.vc_up).sum())

    # ---------- dynamics ----------
    def step(self, dt: float, q_meter: float, q_branch: float, t_feed: float) -> None:
        th, tr, tp = self.cfg.thermal, self.cfg.tracer, self.cfg.transport
        u_max = q_branch / self.area * self.u_rel[0]
        frac = max(q_meter * dt / self.vc_up / tp.max_cell_fraction, u_max * dt / self.dz / 0.9)
        n_sub = max(1, int(math.ceil(frac)))
        h = dt / n_sub
        e_s, e_h = self._expm(h)
        inflow = np.array([0.0, tr.c_fresh_uscm, t_feed, tr.age_feed_h])
        k_wall_up = h / th.tau_wall_s
        cr = (q_branch / self.area * h / self.dz) * self.u_rel          # Courant per ring
        for _ in range(n_sub):
            a_up = q_meter * h / self.vc_up
            prev = np.concatenate([inflow[:, None], self.up[:, :-1]], axis=1)
            up_out = self.up[:, -1].copy()
            self.up += a_up * (prev - self.up)
            self.up[T] += k_wall_up * (th.t_env_c - self.up[T])
            self.up[A] += h / 3600.0
            # advection, each ring is plug flow (upwind)
            last = self.x[:, :, -1].copy()
            prev = np.concatenate([np.repeat(up_out[:, None, None], self.m, axis=1), self.x[:, :, :-1]], axis=2)
            self.x += cr[None, :, None] * (prev - self.x)
            dv = q_branch * h
            out = last @ self.u_rel / self.m
            self.tracer_out += (out[C] - tr.c_fresh_uscm) * dv
            self.old_out += out[F] * dv
            self.vol_out += dv
            self.vol_div += (q_meter - q_branch) * h
            # radial exchange (exact for the sub-step)
            for row in (F, C, A):
                self.x[row] = e_s @ self.x[row]
            stack = np.vstack([self.x[T], self.tw[None, :]]) - th.t_env_c
            stack = e_h @ stack + th.t_env_c
            self.x[T], self.tw = stack[:self.m], stack[self.m]
            self.x[A] += h / 3600.0


def make_transport(cfg: Config):
    if cfg.transport.model == "radial":
        return RadialTransport(cfg)
    from .transport import Transport
    return Transport(cfg)
