"""Build the Rev-B rig as EPANET 2.2 input files (.inp) and run them with EPANET (via WNTR).

    python epanet/build_epanet.py

Writes, for each scenario, epanet/VeriFlush_<scenario>.inp (open these in the EPANET 2.2
desktop application) and compares EPANET's hydraulics and water-quality results with the
Python model:  epanet/epanet_vs_python.csv,  outputs/figures/fig10_epanet_rig.(png|svg).

Network (SI units, flows in L/s, Darcy-Weisbach):
  FEED (TK-101, reservoir) -P101 pump (lumped pump + bypass curve H = 0.40 - 200 Q^2, Q in L/s)-> MAN
  MAN -REF (2 m, K 153)-> TK102                         reference branch
  MAN -FT101 (0.5 m, K 42: HV-101 + meter)-> TEE
  TEE -DV101 (0.8 m, K 60, CLOSED unless diverting)-> TK102
  TEE -C01..C12 (12 x 0.5 m coil)-> C12 -R101 (restriction)-> TT101 -XV101 (valve, opens at t = 2 s)-> TK103
Quality: TRACE from FEED (% feed water) and AGE (initial 72 h in the branch). EPANET's quality
solver is plug flow with no dispersion, so it shows travel time and water age, not the laminar tail.
All results are SIMULATED.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", message="Changing the headloss formula")

import wntr  # noqa: E402
from wntr.network.controls import Control, ControlAction, SimTimeCondition  # noqa: E402

from model.hydraulics import CLOSED_K, solve, valve_k  # noqa: E402
from model.params import m3s_to_lpm  # noqa: E402
from scenarios.library import SCENARIOS  # noqa: E402

OUT = Path(__file__).resolve().parent
FIG = ROOT / "outputs" / "figures"
N_COIL = 12
KEYS = ["S01_healthy", "S02_restricted", "S03_partial_valve", "S04_blockage", "S05_diversion"]


def build(key: str, quality: str = "TRACE", duration_s: int = 240) -> wntr.network.WaterNetworkModel:
    cfg = SCENARIOS[key]
    g, h, f = cfg.geometry, cfg.hydraulics, cfg.faults
    d = g.branch_id_m
    wn = wntr.network.WaterNetworkModel()
    wn.name = f"VeriFlush Rev-B rig - {key} - SIMULATED"
    o = wn.options
    o.hydraulic.inpfile_units = "LPS"
    o.hydraulic.headloss = "D-W"
    o.hydraulic.viscosity = 1.0e-6 / 1.004e-6        # relative to EPANET's 20 degC reference -> nu = 1.0e-6 m2/s
    for k in ("duration",):
        setattr(o.time, k, duration_s)
    o.time.hydraulic_timestep = o.time.quality_timestep = o.time.report_timestep = o.time.pattern_timestep = 1
    # ---- nodes (coordinates draw the rig like the schematic; metres on an arbitrary canvas)
    wn.add_reservoir("FEED", base_head=0.0, coordinates=(0, 0))
    wn.add_junction("MAN", elevation=0.0, coordinates=(2, 0))
    wn.add_reservoir("TK102", base_head=g.outlet_rise_m, coordinates=(6, 2.2))
    wn.add_junction("TEE", elevation=0.0, coordinates=(3.2, 0))
    xs = np.linspace(3.6, 8.4, N_COIL)
    for i, x in enumerate(xs, 1):
        wn.add_junction(f"C{i:02d}", elevation=0.0, coordinates=(float(x), 0.35 * (-1) ** i))
    wn.add_junction("TT101", elevation=0.0, coordinates=(9.0, 0))
    wn.add_reservoir("TK103", base_head=g.outlet_rise_m, coordinates=(9.8, -1.2))
    # ---- links
    wn.add_curve("SRC", "HEAD", [(0.0, 0.40), (2e-5, 0.32), (4e-5, 0.08)])   # = H0 - Rs Q^2 (WNTR: Q in m3/s)
    wn.add_pump("P101", "FEED", "MAN", pump_type="HEAD", pump_parameter="SRC")
    rough = 0.0015                                                        # mm, smooth silicone (ASSUMED)
    wn.add_pipe("REF", "MAN", "TK102", length=g.ref_length_m, diameter=d, roughness=rough,
                minor_loss=h.k_hv + 150.0 + 1.0)
    wn.add_pipe("FT101", "MAN", "TEE", length=0.5, diameter=d, roughness=rough, minor_loss=h.k_hv + h.k_meter)
    k_div = h.k_diversion_open / max(h.diversion_open, 1e-9) ** 2 if h.diversion_open > 0 else 60.0
    wn.add_reservoir("TK102D", base_head=g.outlet_rise_m, coordinates=(3.2, -1.6))   # diversion outlet (TK-102)
    wn.add_pipe("DV101", "TEE", "TK102D", length=h.diversion_length_m, diameter=d, roughness=rough,
                minor_loss=k_div, initial_status="OPEN" if h.diversion_open > 0 else "CLOSED")
    seg = g.branch_length_m / N_COIL
    prev = "TEE"
    for i in range(1, N_COIL + 1):
        wn.add_pipe(f"P{i:02d}", prev, f"C{i:02d}", length=seg, diameter=d, roughness=rough,
                    minor_loss=(h.k_fittings + 1.0) / N_COIL,
                    initial_status="CLOSED" if (f.blockage and i == N_COIL // 2) else "OPEN")
        prev = f"C{i:02d}"
    wn.add_pipe("R101", prev, "TT101", length=0.01, diameter=d, roughness=rough, minor_loss=h.k_restriction)
    k_valve = valve_k(h.k_valve_open, f.valve_max_open)
    wn.add_pipe("XV101", "TT101", "TK103", length=0.01, diameter=d, roughness=rough,
                minor_loss=min(k_valve, 1e6), initial_status="CLOSED")
    opn = ControlAction(wn.get_link("XV101"), "status", 1)
    wn.add_control("XV101_open_at_2s", Control(SimTimeCondition(wn, "=", 2), opn))
    # ---- quality
    if quality == "TRACE":
        o.quality.parameter = "TRACE"
        o.quality.trace_node = "FEED"
    else:
        o.quality.parameter = "AGE"
        for n in ["TEE", "TT101"] + [f"C{i:02d}" for i in range(1, N_COIL + 1)]:
            wn.get_node(n).initial_quality = 72 * 3600.0           # WNTR uses seconds; written as hours
    return wn


def run(wn, prefix: str):
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        try:
            return wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=prefix)
        finally:
            os.chdir(cwd)


LABELS = [  # (x, y, text): rig tags and sensor positions drawn on the EPANET map
    (-0.4, 0.55, "TK-101 feed + TT-100"), (1.0, -0.45, "P-101 pump+bypass"), (1.6, 0.45, "MAN: PI-101 (virtual 0-10 kPa)"),
    (2.3, -0.45, "FT-101 flow sensor"), (3.05, -0.55, "DV-101 diversion"), (4.6, 0.75, "6 m x 8 mm coil (C01-C12)"),
    (8.6, 0.45, "TT-101 endpoint"), (9.0, -0.55, "XV-101 servo valve + LS-OPEN/CLOSED"), (9.7, -1.65, "TK-103 outlet"),
    (5.6, 2.6, "TK-102 reference"), (2.6, -2.05, "TK-102 diversion"),
]


def add_labels(inp: Path, key: str):
    """Add [LABELS] and a descriptive [TITLE] so the model reads as the rig in the EPANET 2.2 GUI."""
    s = inp.read_text()
    lab = "[LABELS]\n;X-Coord  Y-Coord  Label\n" + "".join(f' {x:.2f}  {y:.2f}  "{t}"\n' for x, y, t in LABELS) + "\n"
    if "[LABELS]" in s:                                           # WNTR writes an empty section: fill it
        s = s.replace("[LABELS]\n", lab.rstrip("\n") + "\n", 1)
    else:
        s = s.replace("[END]", lab + "[END]", 1)
    title = (f"VeriFlush Rev-B rig - {key} - SIMULATED\nQuality: TRACE from FEED = % fresh water. XV-101 opens at t = 2 s.\n"
             "Sensors are labelled on the map; EPANET is plug flow (no laminar tail).\n")
    s = s.replace("[TITLE]\n", "[TITLE]\n" + title, 1)
    inp.write_text(s)


def main():
    rows, traces = [], {}
    for key in KEYS:
        wn = build(key, "TRACE")
        inp = OUT / f"VeriFlush_{key}.inp"
        wntr.network.write_inpfile(wn, str(inp), units="LPS")
        add_labels(inp, key)
        r = run(wn, "tr")
        a = run(build(key, "AGE"), "age")
        flow = r.link["flowrate"]
        q_epa = float(flow["XV101"].iloc[-1]) * 60000          # m3/s -> L/min
        q_div = float(flow["DV101"].iloc[-1]) * 60000
        q_ft = float(flow["FT101"].iloc[-1]) * 60000
        cfg = SCENARIOS[key]
        hs = solve(cfg, cfg.faults.valve_max_open)
        tr = r.node["quality"]["TT101"]
        t50 = float(tr.index[np.argmax(tr.values >= 50)]) if (tr.values >= 50).any() else math.nan
        age_end = float(a.node["quality"]["TT101"].iloc[-1])    # s
        v_up = 0.5 * math.pi * cfg.geometry.branch_id_m ** 2 / 4 * 1000
        q_py = m3s_to_lpm(hs.q_branch)
        t50_plug = (cfg.geometry.branch_volume_l + v_up) / q_py * 60 + 2 if q_py > 0 else math.nan
        rows.append(dict(
            scenario=key, epanet_branch_flow_lpm=round(q_epa, 4), python_branch_flow_lpm=round(q_py, 4),
            epanet_meter_flow_lpm=round(q_ft, 4), python_meter_flow_lpm=round(m3s_to_lpm(hs.q_meter), 4),
            epanet_diverted_lpm=round(q_div, 4), python_diverted_lpm=round(m3s_to_lpm(hs.q_div), 4),
            epanet_manifold_kpa=round(float(r.node["pressure"]["MAN"].iloc[-1]) * 9.79, 3),
            python_manifold_kpa=round(hs.p_manifold_kpa, 3),
            epanet_t50_endpoint_s=t50, plug_flow_t50_s=round(t50_plug, 1),
            epanet_endpoint_age_end_s=round(age_end, 1)))
        traces[key] = tr
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "epanet_vs_python.csv", index=False)
    print(df.to_string(index=False))
    figure()
    return df


def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("oldfresh", ["#b3541e", "#d8d2c6", "#2a78d6"])
    fig, axes = plt.subplots(3, 2, figsize=(7.4, 5.2), gridspec_kw=dict(hspace=0.35, wspace=0.06))
    for col, key in enumerate(["S01_healthy", "S05_diversion"]):
        wn = build(key, "TRACE")
        r = run(wn, "fig")
        lq = r.link["quality"]
        for row, t in enumerate((15, 30, 45)):
            ax = axes[row, col]
            segs, vals = [], []
            for name, link in wn.links():
                a, b = link.start_node.coordinates, link.end_node.coordinates
                segs.append([a, b])
                vals.append(float(lq[name].loc[t]))
            lc = LineCollection(segs, cmap=cmap, norm=plt.Normalize(0, 100), linewidths=4, capstyle="round")
            lc.set_array(np.array(vals))
            ax.add_collection(lc)
            for name, node in wn.nodes():
                if node.node_type == "Reservoir":
                    ax.plot(*node.coordinates, "s", ms=7, color="#141413")
                    ax.annotate(name, node.coordinates, xytext=(0, 7), textcoords="offset points", ha="center",
                                fontsize=6.5, color="#52514e")
            ax.annotate("TT-101", wn.get_node("TT101").coordinates, xytext=(0, 7), textcoords="offset points",
                        ha="center", fontsize=6.5, color="#52514e")
            pct = float(r.node["quality"]["TT101"].loc[t])
            ax.set_title(f"{'Healthy' if col == 0 else 'Diversion'} · t = {t} s · endpoint {pct:.0f} % fresh",
                         fontsize=8, loc="left")
            ax.set_xlim(-0.5, 10.4)
            ax.set_ylim(-2.0, 2.6)
            ax.set_aspect("equal")
            ax.axis("off")
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 100), cmap=cmap), ax=axes, shrink=0.5,
                      orientation="horizontal", pad=0.03, aspect=40,
                      label="fresh (feed) water in pipe, % (EPANET TRACE). Brown = stagnant old water")
    cb.outline.set_visible(False)
    fig.text(0.99, -0.01, "SIMULATED DATA · EPANET 2.2 via WNTR 1.5", ha="right", fontsize=6.5, color="#8a8984")
    fig.savefig(FIG / "fig10_epanet_rig.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(FIG / "fig10_epanet_rig.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
