"""Report figures (PNG 300 dpi + SVG) from the CSVs written by run_experiments.py.

    python make_figures.py

Every figure shows SIMULATED data from the VeriFlush virtual testbed.
Captions are written to outputs/figures/captions.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import poisson  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from model import params as P  # noqa: E402
from model.hydraulics import Path as HPath  # noqa: E402
from model.radial import laminar_bound, make_transport  # noqa: E402

RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
TAB, FIG = ROOT / "outputs" / "tables", ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# palette: reference categorical slots (validated adjacent + all-pairs for 3 series) and status steps
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
METHOD_COLOR = {"VeriFlush": "#2a78d6", "Flow + configured volume": "#eb6834", "Timer-only": "#1baf7a"}
METHOD_ORDER = ["Timer-only", "Flow + configured volume", "VeriFlush"]
OUTCOME_COLOR = {"True pass": "#0ca30c", "True failure": "#2a78d6", "Uncertain": "#fab219",
                 "False failure": "#ec835a", "False pass": "#d03b3b"}
OUTCOMES = ["True pass", "True failure", "Uncertain", "False failure", "False pass"]
OLD, FRESH = "#b3541e", "#2a78d6"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.titlesize": 9.5, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelcolor": INK2, "axes.edgecolor": "#b9b8b3", "axes.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.5, "xtick.color": INK2, "ytick.color": INK2, "xtick.major.width": 0.5,
    "ytick.major.width": 0.5, "legend.frameon": False, "lines.linewidth": 1.6, "figure.dpi": 110,
    "savefig.facecolor": "white", "figure.facecolor": "white",
})

CAPTIONS: list[tuple[str, str]] = []


def save(fig, name: str, caption: str):
    fig.text(0.995, -0.04, "SIMULATED DATA", ha="right", va="top", fontsize=6.5, color=MUTED)
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    CAPTIONS.append((name, caption))


def raw(scn: str, method: str, radial: bool = False) -> pd.DataFrame:
    tag = "__radial" if radial else ""
    return pd.read_csv(RAW / f"{scn}__{method}__seed0{tag}.csv")


def rep_row(scn: str, method_name: str, backend="two_region") -> pd.Series:
    r = pd.read_csv(PROC / "representative_runs_seed0.csv")
    return r[(r.scenario == scn) & (r.method == method_name) & (r.backend == backend)].iloc[0]


# ---------------------------------------------------------------- fig 1
def fig_healthy():
    d = raw("S01_healthy", "veriflush")
    s = rep_row("S01_healthy", "VeriFlush")
    t = d.obs_t_s
    fig, ax = plt.subplots(4, 1, figsize=(6.8, 7.2), sharex=True, gridspec_kw=dict(hspace=0.35))
    ax[0].step(t, d.obs_ft_flow_lpm, where="post", color=METHOD_COLOR["VeriFlush"], lw=1.0, label="FT-101 reading")
    ax[0].plot(t, d.truth_q_branch_lpm, color=INK2, lw=1.0, ls="--", label="true branch flow")
    ax[0].set_ylabel("flow (L/min)")
    ax[0].set_title("a  Flow")
    ax[0].legend(loc="lower right", ncol=2)
    ax[1].plot(t, d.truth_valve_pos * 100, color=INK, lw=1.2, label="XV-101 position")
    ax[1].step(t, d.obs_ls_open * 100, where="post", color=METHOD_COLOR["VeriFlush"], lw=1.0, label="LS-OPEN (100 = made)")
    ax[1].set_ylabel("% open")
    ax[1].set_title("b  Valve command feedback")
    ax[1].legend(loc="center right", ncol=2)
    ax[2].plot(t, d.obs_tt100_c, color=FRESH, lw=1.2, label="TT-100 feed")
    ax[2].plot(t, d.obs_tt101_c, color=OLD, lw=1.2, label="TT-101 endpoint")
    ax[2].plot(t, d.truth_t_endpoint_c, color=INK2, lw=0.9, ls="--", label="true endpoint temperature")
    ax[2].set_ylabel("temperature (°C)")
    ax[2].set_title("c  Endpoint thermal response (decision input)")
    ax[2].legend(loc="center right")
    ax[3].plot(t, d.truth_f_old_outlet * 100, color=OLD, lw=1.2, label="old water in outflow")
    ax[3].plot(t, d.truth_residual_old_fraction * 100, color=INK, lw=1.2, label="old water left in branch")
    ax[3].axhline(5, color=MUTED, lw=0.8, ls=":")
    ax[3].text(t.iloc[-1], 6, "5 % adequacy threshold", ha="right", color=MUTED, fontsize=7)
    ax[3].set_ylabel("old water (%)")
    ax[3].set_xlabel("time (s)")
    ax[3].set_title("d  Tracer truth (evaluation only, never read by any method)")
    ax[3].legend(loc="upper right")
    for a in ax:
        a.axvline(s.t_close_s, color=INK, lw=0.7, ls="-.")
    ax[0].text(s.t_close_s + 2, ax[0].get_ylim()[1] * 0.92, f"VeriFlush: {s.verdict}", fontsize=7.5, color=INK)
    save(fig, "fig01_healthy_timeseries",
         "Healthy flush (S01, seed 0, two-region transport), VeriFlush controlling. (a) FT-101 reading vs true "
         "branch flow; (b) XV-101 position and LS-OPEN; (c) TT-100/TT-101 readings used by the decision engine; "
         "(d) tracer truth: old-water fraction in the outflow and remaining in the branch. Dash-dot line: valve "
         f"closed with verdict '{s.verdict}' at t = {s.t_close_s:.0f} s. SIMULATED.")


# ---------------------------------------------------------------- fig 2
def fig_diversion():
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw=dict(width_ratios=[1.6, 1], wspace=0.35))
    names = {"timeronly": "Timer-only", "flow": "Flow + configured volume", "veriflush": "VeriFlush"}
    bars = []
    for key, name in names.items():
        d = raw("S05_diversion", key)
        s = rep_row("S05_diversion", name)
        ax[0].plot(d.obs_t_s, d.truth_residual_old_fraction * 100, color=METHOD_COLOR[name], lw=1.5, label=name)
        ax[0].plot([s.t_close_s], [s.residual_old_fraction * 100], "o", ms=5, color=METHOD_COLOR[name],
                   mec="white", mew=1.5)
        bars.append((name, s.residual_old_fraction * 100, s.verdict, s.water_used_l))
    ax[0].axhline(5, color=MUTED, lw=0.8, ls=":")
    ax[0].set_ylim(0, 40)
    ax[0].set_xlabel("time (s)")
    ax[0].set_ylabel("old water left in branch (%)")
    ax[0].set_title("a  Residual old water (truth), dot = valve closed")
    ax[0].legend(loc="upper right")
    for i, (name, r, v, w) in enumerate(bars):
        ax[1].barh(i, r, color=METHOD_COLOR[name], height=0.55)
        ax[1].text(r + 0.4, i, f"{r:.1f} %  ·  '{v}'  ·  {w:.2f} L", va="center", fontsize=7, color=INK)
    ax[1].axvline(5, color=MUTED, lw=0.8, ls=":")
    ax[1].set_yticks(range(len(bars)), [b[0].replace(" + ", "\n+ ") for b in bars])
    ax[1].set_xlim(0, max(b[1] for b in bars) * 2.3)
    ax[1].set_xlabel("residual at stop (%)")
    ax[1].set_title("b  Outcome")
    ax[1].grid(axis="y", visible=False)
    save(fig, "fig02_diversion_comparison",
         "Diversion after the meter (S05, seed 0): about half the metered water leaves through DV-101 before the "
         "branch. Timer-only and Flow + configured volume record completion; VeriFlush keeps flushing until the "
         "endpoint-anchored volume is reached and reports the volume mismatch as a warning. Labels: residual at "
         "stop, verdict, total water used. SIMULATED (two-region transport).")


# ---------------------------------------------------------------- fig 3
def _grid(ax, mbs: pd.DataFrame, title: str, show_y=True):
    scen = sorted(mbs.scenario.unique())
    for j, m in enumerate(METHOD_ORDER):
        for i, sc in enumerate(scen):
            r = mbs[(mbs.scenario == sc) & (mbs.method == m)].iloc[0]
            counts = {o: int(r[o]) for o in OUTCOMES}
            n = sum(counts.values())
            left = 0.0
            for o in OUTCOMES:
                w = counts[o] / n
                if w > 0:
                    ax.barh(i, w * 0.96, left=j + left * 0.96 + 0.02, height=0.78, color=OUTCOME_COLOR[o],
                            edgecolor="white", linewidth=0.8)
                left += w
            top = max(counts, key=counts.get)
            ax.text(j + 0.5, i, f"{counts[top] / n:.0%}", ha="center", va="center", fontsize=6.5,
                    color="white" if top in ("True pass", "True failure", "False pass") else INK)
    ax.set_yticks(range(len(scen)), [s.replace("_", " ") for s in scen] if show_y else [])
    ax.set_xticks([0.5, 1.5, 2.5], ["Timer-only", "Flow +\nconfigured vol.", "VeriFlush"])
    ax.set_xlim(0, 3)
    ax.set_ylim(len(scen) - 0.5, -0.5)
    ax.grid(False)
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(title)


def fig_verdict_grid():
    a = pd.read_csv(TAB / "method_comparison_by_scenario.csv")
    b = pd.read_csv(TAB / "method_comparison_by_scenario_radial.csv")
    n = int(a.runs.iloc[0])
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 4.6), gridspec_kw=dict(wspace=0.05))
    _grid(ax[0], a, "a  Two-region transport (baseline)")
    _grid(ax[1], b, "b  Radial laminar, straight tube", show_y=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=OUTCOME_COLOR[o]) for o in OUTCOMES]
    fig.legend(handles, OUTCOMES, loc="lower center", ncol=5, bbox_to_anchor=(0.55, -0.02))
    save(fig, "fig03_verdict_grid",
         f"Scenario x method outcome mix over {n} Monte-Carlo runs per cell (perturbed physical event, same seed for "
         "every method). Bar segments: share of runs in each outcome against tracer truth (5 % residual threshold); "
         "number: share of the most frequent outcome. (a) baseline two-region transport; (b) radially resolved "
         "laminar transport with molecular diffusion only (straight-tube physics, no coil mixing). SIMULATED.")


# ---------------------------------------------------------------- fig 4
def fig_confusion():
    fig, ax = plt.subplots(2, 3, figsize=(7.2, 4.4), gridspec_kw=dict(hspace=0.55, wspace=0.12))
    for row, (fn, lab) in enumerate([("monte_carlo_runs.csv", "two-region"), ("monte_carlo_runs_radial.csv", "radial")]):
        mc = pd.read_csv(PROC / fn)
        for j, m in enumerate(METHOD_ORDER):
            d = mc[mc.method == m]
            mat = np.zeros((2, 3), int)
            for ti, adeq in enumerate([True, False]):
                for vi, v in enumerate(["Verified", "Failed", "Uncertain"]):
                    mat[ti, vi] = int(((d.truth_adequate == adeq) & (d.verdict == v)).sum())
            a = ax[row, j]
            a.imshow(mat, cmap="Blues", vmin=0, vmax=len(d) * 0.75)
            for (ti, vi), c in np.ndenumerate(mat):
                bad = (ti == 1 and vi == 0)
                a.text(vi, ti, str(c), ha="center", va="center", fontsize=8.5, fontweight="bold" if bad else None,
                       color="#d03b3b" if bad and c > 0 else (INK if c < len(d) * 0.4 else "white"))
            a.set_xticks([0, 1, 2], ["Verified", "Failed", "Uncertain"])
            a.set_yticks([0, 1], ["adequate", "inadequate"] if j == 0 else ["", ""])
            a.grid(False)
            a.tick_params(length=0)
            a.set_title(f"{m} ({lab})", fontsize=8)
    save(fig, "fig04_confusion_matrices",
         "Confusion matrices: verdict (columns) vs tracer truth (rows; adequate = residual old water <= 5 %), all "
         "Monte-Carlo runs pooled over scenarios. Red bold cell = false pass (inadequate exchange recorded as "
         "verified). Top row: two-region transport; bottom row: radial straight-tube transport. SIMULATED.")


# ---------------------------------------------------------------- fig 5
def fig_water_residual():
    mc = pd.read_csv(PROC / "monte_carlo_runs.csv")
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    for m in METHOD_ORDER:
        d = mc[mc.method == m]
        ax.scatter(d.water_used_l, d.residual_old_fraction.clip(lower=1e-4) * 100, s=10, alpha=0.55,
                   color=METHOD_COLOR[m], edgecolor="white", linewidth=0.3, label=m)
    ax.axhline(5, color=MUTED, lw=0.8, ls=":")
    ax.set_yscale("log")
    ax.set_xlabel("water used per flush (L, metered + diverted)")
    ax.set_ylabel("residual old water at stop (%)")
    ax.legend(loc="upper right", markerscale=1.8)
    ax.set_title("Water used vs exchange achieved")
    save(fig, "fig05_water_vs_residual",
         "Water used vs residual old-water fraction at stop for every Monte-Carlo run (two-region transport). "
         "Points above the dotted 5 % line are inadequate exchanges. Residuals below 0.01 % are drawn at 0.01 %. "
         "SIMULATED.")


# ---------------------------------------------------------------- fig 6
def fig_transport():
    tc = pd.read_csv(PROC / "transport_curves.csv")
    style = {
        "plug flow (EPANET 2.2 assumption)": (MUTED, ":", 1.2),
        "analytical laminar bound 1/(4 theta)": (INK, "--", 1.4),
        "radial D=0 (numerical laminar bound)": ("#6250d6", "-", 0.9),
        "radial straight tube, salt (molecular D)": (OLD, "-", 1.8),
        "radial, coil mixing x10 (ASSUMED)": ("#e87ba4", "-", 1.4),
        "two-region baseline (N=10, beta=0.10, tau=60 s)": (FRESH, "-", 1.8),
        "tanks-in-series only (N=10, beta=0)": ("#1baf7a", "-", 1.2),
        "two-region N=5": (FRESH, "--", 1.0),
        "two-region beta=0.20": (FRESH, "-.", 1.0),
        "two-region tau=120 s": (FRESH, ":", 1.2),
    }
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    for name, (c, ls, lw) in style.items():
        d = tc[tc.model == name]
        ax.plot(d.theta, d.residual.clip(lower=1e-4) * 100, color=c, ls=ls, lw=lw, label=name)
    ax.axhline(5, color=MUTED, lw=0.7)
    ax.axvline(3, color=MUTED, lw=0.7)
    ax.text(3.05, 60, "3-volume policy", fontsize=7, color=MUTED)
    ax.set_yscale("log")
    ax.set_ylim(0.01, 100)
    ax.set_xlim(0, 8)
    ax.set_xlabel("pipe volumes passed, θ (–)")
    ax.set_ylabel("old water left in branch (%)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=6.8)
    ax.set_title("Transport-model sensitivity: residual vs volumes, healthy flow")
    save(fig, "fig06_transport_sensitivity",
         "In-pipe residual old-water fraction vs pipe volumes passed at the healthy flow (0.63 L/min, Re ≈ 1670) "
         "for the transport models used. Plug flow (EPANET 2.2) clears the pipe at θ = 1; the laminar segregated "
         "bound 1/(4θ) needs θ = 5 for 5 %; molecular diffusion in a straight tube lowers the tail. Around the 3-volume "
         "policy (θ ≈ 2–4) the two-region baseline lies between straight-tube physics and coil-enhanced mixing; beyond "
         "θ ≈ 4.2 it is above the straight-tube curve (heavier tail). Coil mixing factor is ASSUMED. MODELLED.")


# ---------------------------------------------------------------- fig 7
def fig_thresholds():
    sb = pd.read_csv(TAB / "sensitivity_by_case.csv")
    import json
    order = json.loads((ROOT / "data" / "simulation_metadata.json").read_text())["sensitivity_cases"]
    sb = sb.set_index("case").loc[[c for c in order if c in set(sb.case)]].reset_index()
    vf = sb[sb.method == "VeriFlush"].reset_index(drop=True)
    fig, ax = plt.subplots(1, 2, figsize=(7.6, 6.6), gridspec_kw=dict(width_ratios=[1.5, 1], wspace=0.08))
    cases = list(vf.case)
    for i, r in vf.iterrows():
        left = 0
        for o in OUTCOMES:
            w = r[o] / r.runs
            if w:
                ax[0].barh(i, w, left=left, color=OUTCOME_COLOR[o], height=0.75, edgecolor="white", linewidth=0.6)
            left += w
    ax[0].set_yticks(range(len(cases)), cases, fontsize=7)
    ax[0].set_ylim(len(cases) - 0.5, -0.5)
    ax[0].set_xlim(0, 1)
    ax[0].xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax[0].set_title("a  VeriFlush outcome mix per case")
    ax[0].grid(axis="y", visible=False)
    for m in METHOD_ORDER:
        d = sb[sb.method == m].set_index("case").reindex(cases)
        ax[1].plot(d["False pass"] / d.runs, range(len(cases)), "o", ms=4.5, color=METHOD_COLOR[m], label=m,
                   mec="white", mew=0.8)
    ax[1].set_ylim(len(cases) - 0.5, -0.5)
    ax[1].set_yticks(range(len(cases)), [])
    ax[1].xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax[1].set_title("b  False-pass rate, all methods")
    ax[1].legend(loc="lower right", fontsize=6.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=OUTCOME_COLOR[o]) for o in OUTCOMES]
    fig.legend(handles, OUTCOMES, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.01))
    n = int(vf.runs.iloc[0])
    save(fig, "fig07_sensitivity",
         f"One-at-a-time sensitivity ({n} runs per case per method: scenarios S01, S02, S05, S06, S07, S10). "
         "(a) VeriFlush outcome mix for every transport, probe, truth-threshold, VeriFlush-threshold, policy, "
         "geometry and flow case. (b) false-pass rate of each method in the same cases. SIMULATED.")


# ---------------------------------------------------------------- fig 8
def fig_verification():
    fig, ax = plt.subplots(2, 2, figsize=(7.0, 5.4), gridspec_kw=dict(hspace=0.45, wspace=0.3))
    # a: tanks-in-series vs Erlang
    n = 10
    cfg = P.with_changes(P.Config(), transport=dict(n_cells_branch=n, slow_fraction=0.0, max_cell_fraction=0.02))
    tr = make_transport(cfg)
    v = cfg.geometry.branch_volume_l / 1000
    q = v / 60.0
    th, sim = [], []
    for k in range(1, 241):
        tr.step(1.0, q, q, 13.0)
        th.append(k / 60)
        sim.append(tr.residual_old_fraction)
    th = np.array(th)
    exact = [poisson.cdf(np.arange(n), n * t).mean() for t in th]
    ax[0, 0].plot(th, np.array(exact) * 100, color=INK, lw=2.6, alpha=0.25, label="exact (Erlang/Poisson)")
    ax[0, 0].plot(th, np.array(sim) * 100, color=FRESH, lw=1.2, label="model, N = 10")
    ax[0, 0].set_title("a  Tanks-in-series vs exact")
    ax[0, 0].set_xlabel("θ (–)")
    ax[0, 0].set_ylabel("residual (%)")
    ax[0, 0].legend()
    # b: radial D=0 vs 1/(4 theta)
    tc = pd.read_csv(PROC / "transport_curves.csv")
    d0 = tc[tc.model == "radial D=0 (numerical laminar bound)"]
    ax[0, 1].plot(d0.theta, laminar_bound(d0.theta) * 100, color=INK, lw=2.6, alpha=0.25, label="1/(4θ) analytical")
    ax[0, 1].plot(d0.theta, d0.residual * 100, color=OLD, lw=1.2, label="radial model, D = 0")
    ax[0, 1].set_title("b  Laminar segregated-flow bound")
    ax[0, 1].set_xlabel("θ (–)")
    ax[0, 1].set_ylabel("residual (%)")
    ax[0, 1].legend()
    # c: WNTR vs python plug
    w = pd.read_csv(PROC / "wntr_crosscheck_curves.csv")
    ax[1, 0].plot(w.t_s, w.epanet_trace_pct, color=INK, lw=2.6, alpha=0.25, label="EPANET 2.2 via WNTR")
    ax[1, 0].plot(w.t_s, w.python_plug_fresh_pct, color=FRESH, lw=1.2, label="Python, plug limit")
    ax[1, 0].set_xlim(20, 45)
    ax[1, 0].set_title("c  Endpoint travel time")
    ax[1, 0].set_xlabel("time (s)")
    ax[1, 0].set_ylabel("feed water at endpoint (%)")
    ax[1, 0].legend(loc="lower right")
    # d: Hagen-Poiseuille
    p = HPath(6.0, 0.008, 0.0)
    qs = np.linspace(0.05, 0.75, 40)
    hp = [128 * P.MU * 6.0 * P.lpm_to_m3s(x) / (np.pi * P.RHO * P.G * 0.008 ** 4) * 1000 for x in qs]
    ax[1, 1].plot(qs, hp, color=INK, lw=2.6, alpha=0.25, label="Hagen–Poiseuille")
    ax[1, 1].plot(qs, [p.head(P.lpm_to_m3s(x)) * 1000 for x in qs], color=FRESH, lw=1.2, label="model, f = 64/Re")
    ax[1, 1].set_title("d  Laminar head loss, 6 m × 8 mm")
    ax[1, 1].set_xlabel("flow (L/min)")
    ax[1, 1].set_ylabel("head loss (mm H₂O)")
    ax[1, 1].legend()
    save(fig, "fig08_analytical_verification",
         "Verification against exact or independent results: (a) mobile-zone tanks-in-series vs the Erlang/Poisson "
         "solution; (b) radially resolved model with zero diffusion vs the laminar segregated-flow bound 1/(4θ); "
         "(c) endpoint breakthrough in the plug-flow limit vs EPANET 2.2 (WNTR 1.5) TRACE; (d) laminar head loss vs "
         "Hagen–Poiseuille. Grey thick lines: reference; coloured thin lines: model. MODELLED.")


# ---------------------------------------------------------------- fig 9
def fig_thermal_limit():
    tc = pd.read_csv(PROC / "transport_curves.csv")
    base = P.Config()
    t_old, t_feed = base.thermal.t_old_c, base.thermal.t_feed_c
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True, gridspec_kw=dict(wspace=0.08))
    for a, name, title in [(ax[0], "two-region baseline (N=10, beta=0.10, tau=60 s)", "a  Two-region (baseline)"),
                           (ax[1], "radial straight tube, salt (molecular D)", "b  Radial laminar, straight tube")]:
        d = tc[tc.model == name]
        phi = (t_old - d.outlet_temp_c) / (t_old - t_feed)
        a.plot(d.theta, (1 - phi) * 100, color=OLD, lw=1.6, label="temperature: 1 − φ at outlet")
        a.plot(d.theta, d.outlet_old_fraction * 100, color=INK, lw=1.6, label="tracer: old water in outflow")
        a.axhline(15, color=MUTED, lw=0.7, ls=":")
        a.text(7.9, 17, "φ = 0.85 plateau rule", ha="right", fontsize=7, color=MUTED)
        a.set_xlim(0, 8)
        a.set_xlabel("θ (–)")
        a.set_title(title)
    ax[0].set_ylabel("remaining signal (%)")
    ax[0].legend(loc="upper right")
    save(fig, "fig09_thermal_vs_tracer",
         "Thermal vs tracer signal at the outlet, healthy flow, ideal sensor (no probe lag). Temperature is shown as "
         "1 − φ. In both models the temperature settles on a plateau of a few per cent (room heat gain through the "
         "tube wall), after which it carries no further information, while old water is still leaving in the "
         "outflow. In the radial model the silicone wall's heat capacity also makes the "
         "temperature lag the tracer before the plateau. A temperature plateau is evidence of bulk exchange, not "
         "proof that the last near-wall old water has left. MODELLED.")


def main():
    for f in (fig_healthy, fig_diversion, fig_verdict_grid, fig_confusion, fig_water_residual, fig_transport,
              fig_thresholds, fig_verification, fig_thermal_limit):
        f()
        print("ok", f.__name__)
    lines = ["# Figure captions", "", "All figures: SIMULATED or MODELLED data from the VeriFlush virtual testbed. "
             "PNG at 300 dpi and SVG in this folder.", ""]
    for i, (name, cap) in enumerate(CAPTIONS, 1):
        lines += [f"**Figure {i}: `{name}`.** {cap}", ""]
    (FIG / "captions.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
