"""VeriFlush virtual testbed: parameters, units and constants.

Every value here is a MODELLING ASSUMPTION unless a source is given in
assumptions_and_equations.md. Units are SI internally (m, s, m^3, kg, K/degC, Pa)
with helper conversions for the lab units used on the rig (L, L/min, kPa).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict, replace

MODEL_VERSION = "1.2.0"

G = 9.81            # m/s^2
RHO = 998.0         # kg/m^3, water ~20 degC
MU = 1.0e-3         # Pa.s, dynamic viscosity ~20 degC
NU = MU / RHO       # m^2/s
CP = 4186.0         # J/(kg.K)

# ---------------- unit helpers ----------------
def lpm_to_m3s(q_lpm: float) -> float:
    return q_lpm / 1000.0 / 60.0


def m3s_to_lpm(q: float) -> float:
    return q * 1000.0 * 60.0


def m3_to_l(v: float) -> float:
    return v * 1000.0


def l_to_m3(v_l: float) -> float:
    return v_l / 1000.0


def pipe_volume_m3(d_m: float, l_m: float) -> float:
    """V = pi D^2 / 4 * L"""
    return math.pi * d_m ** 2 / 4.0 * l_m


@dataclass(frozen=True)
class Geometry:
    branch_length_m: float = 6.0          # monitored branch (spec). Rev-B rig uses 8.0
    branch_id_m: float = 0.008            # 8 mm internal diameter
    fittings_volume_l: float = 0.0        # extra internal volume of fittings in the branch (truth)
    upstream_volume_l: float = 0.040      # manifold + meter + short tubes before the branch (thermal dead volume)
    ref_length_m: float = 2.0             # reference branch
    outlet_rise_m: float = 0.15           # outlet above feed-tank water level
    coil_radius_m: float = 0.15           # coil radius (for Dean number reporting only)

    @property
    def branch_volume_l(self) -> float:
        return m3_to_l(pipe_volume_m3(self.branch_id_m, self.branch_length_m)) + self.fittings_volume_l


@dataclass(frozen=True)
class Hydraulics:
    # Lumped source curve of pump + bypass BV-101 seen at the manifold: H = H0 - Rs*Q^2
    source_head_m: float = 0.40           # calibrated so healthy branch flow ~0.63 L/min (see docs)
    source_r_s2m5: float = 2.0e8          # m / (m^3/s)^2
    k_meter: float = 40.0                 # minor-loss K of small Hall-effect flow sensor + reducers (assumed)
    k_fittings: float = 6.0               # tees, joiner, barbs along branch
    k_valve_open: float = 2.0             # XV-101 fully open
    k_restriction: float = 0.0            # R-101 clamp (0 = fully open)
    k_hv: float = 2.0                     # HV-101 / HV-201 open
    k_diversion_open: float = 60.0        # DV-101 path when open (valve + 0.8 m line + outlet)
    diversion_open: float = 0.0           # 0 = closed, 1 = fully open
    diversion_length_m: float = 0.8


@dataclass(frozen=True)
class Thermal:
    t_old_c: float = 24.0                 # stagnant water in branch (room temperature)
    t_feed_c: float = 13.0                # feed tank with ice packs
    t_env_c: float = 24.0                 # room air
    tau_wall_s: float = 875.0             # lumped water-to-room time constant of 8x10 silicone tube (estimate)
    feed_drift_c_per_min: float = 0.05    # feed tank warming


@dataclass(frozen=True)
class Tracer:
    c_old_uscm: float = 1500.0            # saline 'old water' tracer (truth only)
    c_fresh_uscm: float = 300.0           # feed water conductivity
    age_old_h: float = 72.0               # assumed stagnation before the flush
    age_feed_h: float = 0.0


@dataclass(frozen=True)
class Transport:
    n_cells_branch: int = 10              # tanks-in-series dispersion of the mobile zone (RTD variance ~1/N)
    n_cells_upstream: int = 4
    slow_fraction: float = 0.10           # near-wall slow zone (laminar tail); 0 = pure tanks-in-series
    exchange_tau_s: float = 60.0          # slow<->mobile solute exchange time constant
    heat_exchange_tau_s: float = 30.0     # faster for heat (thermal diffusivity >> salt diffusivity)
    max_cell_fraction: float = 0.2        # explicit sub-step limit (Q*dt/Vcell)
    # backend: "two_region" (1-D, assumed N/beta/tau) or "radial" (Poiseuille rings + molecular diffusion)
    model: str = "two_region"
    n_rings: int = 20
    n_axial: int = 120
    d_salt_m2s: float = 1.5e-9            # NaCl in water ~20-25 degC (order of magnitude well established)
    radial_mix_factor: float = 1.0        # 1 = straight tube; >1 crude proxy for Dean-vortex mixing in the coil (ASSUMED)
    wall_heat_capacity_j_mk: float = 40.0 # 8x10 mm silicone wall, rho*cp ~1.4e6 J/(m^3.K) (ASSUMED)
    wall_conductance_w_mk: float = 10.0   # fluid -> mid-wall conduction, k_silicone ~0.2 W/(m.K) (ASSUMED)


@dataclass(frozen=True)
class SensorSpec:
    ft_k_pulses_per_l: float = 5880.0     # assumed hobby Hall sensor (~98 Hz per L/min); calibrate with jug
    ft_k_error_sd: float = 0.03           # unit-to-unit K-factor error (1 sd)
    ft_qmin_lpm: float = 0.30             # below this the rotor under-reads (assumed)
    ft_qstall_lpm: float = 0.10           # below this no pulses
    pt_noise_kpa: float = 0.05             # VIRTUAL low-range transducer (0-10 kPa); the rig gauge (0-3 bar) cannot resolve this
    pt_res_kpa: float = 0.01
    tt_res_c: float = 0.0625              # DS18B20 12-bit
    tt_noise_c: float = 0.03
    tt_bias_sd_c: float = 0.15            # within the +/-0.5 degC datasheet band
    tt_tau_endpoint_s: float = 5.0        # still-water test of a sheathed probe gave 6.2-6.9 s [Perea Martins 2022]; moving water assumed faster (sweep 2..10 s)
    tt_tau_feed_s: float = 10.0
    ct_noise_frac: float = 0.01           # conductivity truth sensor
    ls_open_threshold: float = 0.95       # fraction of travel that presses LS-OPEN
    ls_closed_threshold: float = 0.05
    servo_rate_per_s: float = 2.0         # fraction of full travel per second (90 deg in 0.5 s)


@dataclass(frozen=True)
class Faults:
    flow_bias: float = 1.0                # multiplier on FT-101 reading
    flow_dropout_t_s: float | None = None # FT-101 stops producing pulses at t
    tt101_mode: str = "ok"                # ok | frozen | disconnected
    tt101_fault_t_s: float = 0.0
    valve_max_open: float = 1.0           # stuck partially open
    valve_stuck_closed: bool = False
    ls_open_broken: bool = False          # LS-OPEN never asserts
    blockage: bool = False


@dataclass(frozen=True)
class Policy:
    """Shared operating policy and method thresholds."""
    dt_s: float = 1.0                      # controller / logging period
    t_valve_cmd_s: float = 2.0
    t_max_s: float = 300.0                 # every method must stop by this time
    target_volumes: float = 3.0            # required exchanged branch volumes
    design_flow_lpm: float = 0.60          # used by the timer method to size its timer
    # VeriFlush rule thresholds
    min_contrast_c: float = 1.5
    phi_arrival: float = 0.5
    phi_plateau: float = 0.85
    plateau_hold_s: float = 10.0
    ratio_warn_high: float = 1.4
    ratio_warn_low: float = 0.6
    ratio_fail: float = 3.0
    valve_confirm_s: float = 3.0
    no_flow_lpm: float = 0.05
    blockage_confirm_s: float = 30.0
    dropout_confirm_s: float = 10.0
    dp_draw_min_kpa: float = 0.15          # manifold pressure drop expected when the branch draws water


@dataclass(frozen=True)
class Config:
    name: str = "healthy"
    description: str = ""
    geometry: Geometry = field(default_factory=Geometry)
    hydraulics: Hydraulics = field(default_factory=Hydraulics)
    thermal: Thermal = field(default_factory=Thermal)
    tracer: Tracer = field(default_factory=Tracer)
    transport: Transport = field(default_factory=Transport)
    sensors: SensorSpec = field(default_factory=SensorSpec)
    faults: Faults = field(default_factory=Faults)
    policy: Policy = field(default_factory=Policy)
    configured_volume_l: float | None = None   # what the software believes (None = ideal pipe volume)
    configured_upstream_l: float = 0.040
    adequate_residual: float = 0.05            # TRUTH threshold (evaluation only; not in Policy, so no controller sees it)
    has_fault: bool = False

    @property
    def configured_l(self) -> float:
        if self.configured_volume_l is not None:
            return self.configured_volume_l
        return m3_to_l(pipe_volume_m3(self.geometry.branch_id_m, self.geometry.branch_length_m))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["configured_l"] = self.configured_l
        d["true_branch_volume_l"] = self.geometry.branch_volume_l
        return d


def with_changes(cfg: Config, **groups) -> Config:
    """replace nested groups: with_changes(cfg, faults=dict(flow_bias=1.4))"""
    kw = {}
    for k, v in groups.items():
        if isinstance(v, dict):
            kw[k] = replace(getattr(cfg, k), **v)
        else:
            kw[k] = v
    return replace(cfg, **kw)
