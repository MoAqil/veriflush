"""Scenario library. Each entry returns a Config. All scenarios are SYNTHETIC."""
from __future__ import annotations

import numpy as np

from model.params import Config, with_changes

BASE = Config()


def _c(name, desc, fault=True, **groups):
    cfg = with_changes(BASE, name=name, description=desc, has_fault=fault, **groups)
    return cfg


SCENARIOS = {
    "S01_healthy": _c("S01_healthy", "Healthy exchange: valve opens, ~0.63 L/min, 11 degC contrast.", fault=False),
    "S02_restricted": _c("S02_restricted", "R-101 clamp tightened (K=600): branch flow falls to ~0.27 L/min.",
                         hydraulics=dict(k_restriction=600.0)),
    "S03_partial_valve": _c("S03_partial_valve", "XV-101 jams at 35 % travel; LS-OPEN never made.",
                            faults=dict(valve_max_open=0.35)),
    "S04_blockage": _c("S04_blockage", "Complete blockage downstream of the meter (no flow through the branch).",
                       faults=dict(blockage=True)),
    "S05_diversion": _c("S05_diversion", "DV-101 open: about half of the metered water leaves before the branch.",
                        hydraulics=dict(diversion_open=1.0)),
    "S06_wrong_volume": _c("S06_wrong_volume", "Software configured with half the true branch volume (0.151 L).",
                           configured_volume_l=0.151),
    "S07_flow_bias": _c("S07_flow_bias", "FT-101 over-reads by 40 % (wrong K-factor / calibration).",
                        faults=dict(flow_bias=1.40)),
    "S08_flow_dropout": _c("S08_flow_dropout", "FT-101 signal lost 25 s after the valve opens.",
                           faults=dict(flow_dropout_t_s=27.0)),
    "S09a_tt101_frozen": _c("S09a_tt101_frozen", "TT-101 reading frozen from the start (bus hang).",
                            faults=dict(tt101_mode="frozen", tt101_fault_t_s=0.0)),
    "S09b_tt101_disconnected": _c("S09b_tt101_disconnected", "TT-101 disconnected 20 s into the flush (-127 degC).",
                                  faults=dict(tt101_mode="disconnected", tt101_fault_t_s=22.0)),
    "S10_weak_contrast": _c("S10_weak_contrast", "Feed only 0.6 degC colder than the stagnant water (no ice packs).",
                            fault=False, thermal=dict(t_feed_c=23.4)),
    "S11_valve_feedback": _c("S11_valve_feedback", "LS-OPEN wire broken: valve really opens, feedback says it did not.",
                             faults=dict(ls_open_broken=True)),
    "S12_multiple": _c("S12_multiple", "Diversion open AND TT-101 frozen.",
                       hydraulics=dict(diversion_open=1.0), faults=dict(tt101_mode="frozen", tt101_fault_t_s=0.0)),
}


def perturbed(cfg: Config, seed: int) -> Config:
    """Monte-Carlo variation of the physical event (same for every method at a given seed)."""
    r = np.random.default_rng(1000 + seed)
    th = cfg.thermal
    weak = abs(th.t_old_c - th.t_feed_c) < 2.0
    t_old = th.t_old_c + r.normal(0, 1.0)
    dT = (th.t_old_c - th.t_feed_c) + (r.normal(0, 0.2) if weak else r.normal(0, 1.5))
    return with_changes(
        cfg,
        thermal=dict(t_old_c=t_old, t_env_c=t_old + r.normal(0, 0.5), t_feed_c=t_old - dT),
        hydraulics=dict(source_head_m=cfg.hydraulics.source_head_m * (1 + r.normal(0, 0.08)),
                        k_meter=cfg.hydraulics.k_meter * (1 + r.normal(0, 0.15))),
        geometry=dict(fittings_volume_l=max(0.0, r.normal(0.01, 0.005))),
    )
