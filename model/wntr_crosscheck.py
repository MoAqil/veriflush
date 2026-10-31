"""WNTR / EPANET 2.2 cross-check of the monitored branch.

Builds the same 6 m x 8 mm branch in WNTR and compares, at the healthy flow:
  1. hydraulics: EPANET Darcy-Weisbach head loss vs model.hydraulics.Path (laminar)
  2. travel time: EPANET TRACE (plug flow) vs the Python 1-D model in its plug-flow
     limit (beta = 0, N = 300 cells) and vs L/U
  3. water age at the endpoint after the flush
EPANET's quality solver is Lagrangian plug flow with no axial dispersion, so it cannot
show the laminar tail; that is the reason it is a cross-check and not the core model.
EPANET-MSX 2.0 (bundled with WNTR 1.5) was also tried with a molecular diffusivity, but
the WNTR 1.5 MSX writer did not carry the initial tracer state through (outlet read 0 from
t = 0), so no MSX result is reported. MSX applies Taylor-Aris dispersion, which needs
t >> R^2/D (~1e4 s for salt here) while the branch residence time is ~29 s, so it would
not represent this branch correctly anyway (see assumptions_and_equations.md).
All outputs are SIMULATED.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .hydraulics import Path
from .params import NU, Config, lpm_to_m3s, with_changes
from .transport import Transport


def build(cfg: Config, q_lpm: float, duration_s: int = 120):
    import warnings

    import wntr
    warnings.filterwarnings("ignore", message="Changing the headloss formula")
    g = cfg.geometry
    wn = wntr.network.WaterNetworkModel()
    wn.options.hydraulic.headloss = "D-W"
    wn.options.time.duration = duration_s
    wn.options.time.hydraulic_timestep = 1
    wn.options.time.quality_timestep = 1
    wn.options.time.report_timestep = 1
    wn.options.time.pattern_timestep = 1
    wn.add_reservoir("FEED", base_head=10.0)
    wn.add_junction("J_IN", base_demand=0.0, elevation=0.0)
    wn.add_junction("J_END", base_demand=lpm_to_m3s(q_lpm), elevation=0.0)
    # upstream line with the same internal volume as the Python model's upstream dead volume
    a = math.pi * g.branch_id_m ** 2 / 4
    wn.add_pipe("UP", "FEED", "J_IN", length=cfg.geometry.upstream_volume_l / 1000 / a, diameter=g.branch_id_m,
                roughness=0.0015, minor_loss=0.0)
    wn.add_pipe("BRANCH", "J_IN", "J_END", length=g.branch_length_m, diameter=g.branch_id_m,
                roughness=0.0015, minor_loss=0.0)    # D-W roughness in mm (smooth silicone, ASSUMED)
    return wn


def run_epanet(cfg: Config, q_lpm: float, mode: str, duration_s: int = 120):
    import wntr
    wn = build(cfg, q_lpm, duration_s)
    if mode == "TRACE":
        wn.options.quality.parameter = "TRACE"
        wn.options.quality.trace_node = "FEED"
    else:
        wn.options.quality.parameter = "AGE"
    import os
    import tempfile
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d:          # EPANET writes .inp/.rpt/.bin scratch files
        os.chdir(d)
        try:
            res = wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=f"wntr_{mode.lower()}")
        finally:
            os.chdir(cwd)
    return wn, res


def crosscheck(cfg: Config | None = None, q_lpm: float = 0.63) -> dict:
    cfg = cfg or Config()
    g = cfg.geometry
    q = lpm_to_m3s(q_lpm)
    u = q / (math.pi * g.branch_id_m ** 2 / 4)
    a = math.pi * g.branch_id_m ** 2 / 4
    t_plug = (g.branch_volume_l + g.upstream_volume_l) / 1000 / q      # feed -> endpoint, plug flow
    wn, tr = run_epanet(cfg, q_lpm, "TRACE")
    trace = tr.node["quality"]["J_END"]                     # % of water from FEED
    hl_epanet = float(tr.node["head"]["J_IN"].iloc[1] - tr.node["head"]["J_END"].iloc[1])
    t_arr_epanet = float(trace.index[np.argmax(trace.values >= 50.0)])
    _, ar = run_epanet(cfg, q_lpm, "AGE")
    age_end_epanet_s = float(ar.node["quality"]["J_END"].iloc[-1])   # WNTR reports AGE in s
    # Python 1-D model in its plug-flow limit
    pc = with_changes(cfg, transport=dict(n_cells_branch=300, slow_fraction=0.0, n_cells_upstream=40,
                                          max_cell_fraction=0.5))
    t1 = Transport(pc)
    t1.up[0][:] = 1.0              # treat the upstream line as old water too, as EPANET does (initial quality 0)
    times, fresh, age = [], [], []
    for k in range(1, 121):
        t1.step(1.0, q, q, cfg.thermal.t_feed_c)
        times.append(k)
        fresh.append(100.0 * (1 - t1.outlet[0]))
        age.append(t1.outlet[3] * 3600.0)
    fresh = np.array(fresh)
    t_arr_py = float(times[int(np.argmax(fresh >= 50.0))])
    hl_py = Path(g.branch_length_m, g.branch_id_m, 0.0).head(q)
    curves = pd.DataFrame({"t_s": times, "python_plug_fresh_pct": fresh,
                           "epanet_trace_pct": trace.reindex(times).values,
                           "python_plug_age_s": age,
                           "epanet_age_s": ar.node["quality"]["J_END"].reindex(times).values})
    return dict(
        q_lpm=q_lpm, reynolds=u * g.branch_id_m / NU, mean_velocity_m_s=u,
        travel_time_analytic_s=t_plug, travel_time_epanet_s=t_arr_epanet, travel_time_python_plug_s=t_arr_py,
        endpoint_age_epanet_s=age_end_epanet_s, endpoint_age_python_plug_s=float(age[-1]),
        headloss_branch_epanet_m=hl_epanet, headloss_branch_python_m=hl_py,
        curves=curves,
    )
