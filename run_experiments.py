"""Run every scenario, the Monte-Carlo comparison and the sensitivity studies.

    python run_experiments.py            # full run (~10-15 min)
    python run_experiments.py --quick    # 8 seeds per scenario, 2 per sensitivity case

All numbers written by this script are SIMULATED outputs of the VeriFlush virtual
testbed. They are not physical measurements.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from model.decisions import METHODS  # noqa: E402
from model.hydraulics import solve  # noqa: E402
from model.params import MODEL_VERSION, Config, m3s_to_lpm, with_changes  # noqa: E402
from model.radial import laminar_bound, make_transport  # noqa: E402
from model.simulate import classify, run, time_to_adequate  # noqa: E402
from scenarios.library import SCENARIOS, perturbed  # noqa: E402

RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
for d in (RAW, PROC, TAB):
    d.mkdir(parents=True, exist_ok=True)

OUTCOMES = ["True pass", "False pass", "True failure", "False failure", "Uncertain"]
SIM_NOTE = "SIMULATED - VeriFlush virtual testbed v" + MODEL_VERSION
BACKENDS = {"two_region": "1-D two-region (baseline)", "radial": "radial laminar, straight tube (physics cross-check)"}


def _backend(cfg: Config, backend: str) -> Config:
    return cfg if backend == "two_region" else with_changes(cfg, transport=dict(model=backend))


def short(m) -> str:
    return m.name.split()[0].replace("-", "").lower()


def representative_runs():
    rows = []
    for backend in BACKENDS:
        for key, cfg in SCENARIOS.items():
            for m in METHODS:
                s, df, _ = run(_backend(cfg, backend), m, seed=0, record=True)
                tag = "" if backend == "two_region" else "__radial"
                fname = f"{key}__{short(m)}__seed0{tag}.csv"
                df.insert(0, "data_status", "simulated")
                df.to_csv(RAW / fname, index=False)
                s["raw_file"], s["backend"] = fname, backend
                rows.append(s)
    out = pd.DataFrame(rows)
    out.to_csv(PROC / "representative_runs_seed0.csv", index=False)
    return out


def monte_carlo(n_seeds: int, backend: str):
    rows = []
    for key, cfg in SCENARIOS.items():
        for seed in range(n_seeds):
            c = _backend(perturbed(cfg, seed), backend)
            tta = time_to_adequate(c) if seed < 5 else math.nan
            for m in METHODS:
                s, _, _ = run(c, m, seed=seed, record=False)
                s["scenario"], s["backend"] = key, backend
                s["time_to_adequate_ref_s"] = tta
                rows.append(s)
    df = pd.DataFrame(rows)
    suffix = "" if backend == "two_region" else "_radial"
    df.to_csv(PROC / f"monte_carlo_runs{suffix}.csv", index=False)
    return df


def metrics(df: pd.DataFrame, by=("method",)) -> pd.DataFrame:
    g = df.groupby(list(by))
    out = g["outcome"].value_counts().unstack(fill_value=0).reindex(columns=OUTCOMES, fill_value=0)
    out["runs"] = g.size()
    fault = df[df.has_fault]
    if len(fault):
        out["fault_detection_rate"] = fault.groupby(list(by))["flagged"].mean()
    out["false_pass_rate"] = out["False pass"] / out["runs"]
    out["uncertain_rate"] = out["Uncertain"] / out["runs"]
    out["mean_water_l"] = g["water_used_l"].mean()
    out["mean_duration_s"] = g["flush_duration_s"].mean()
    out["mean_residual_old_fraction"] = g["residual_old_fraction"].mean()
    out["max_residual_old_fraction"] = g["residual_old_fraction"].max()
    return out.reset_index()


def head_for_flow(cfg: Config, q_lpm: float) -> float:
    f = lambda h: m3s_to_lpm(solve(with_changes(cfg, hydraulics=dict(source_head_m=h)), 1.0).q_meter) - q_lpm
    return brentq(f, 0.16, 5.0, xtol=1e-6)


def sensitivity_cases() -> dict:
    base = Config()
    flows = {f"flow {q:.2f} L/min": dict(hydraulics=dict(source_head_m=head_for_flow(base, q)))
             for q in (0.30, 0.45, 0.90, 1.20)}
    return {
        "baseline (N=10, beta=0.10, tau=60/30 s)": {},
        # transport (truth model) parameters
        "transport N=5": dict(transport=dict(n_cells_branch=5)),
        "transport N=20": dict(transport=dict(n_cells_branch=20)),
        "transport beta=0 (no tail)": dict(transport=dict(slow_fraction=0.0)),
        "transport beta=0.20": dict(transport=dict(slow_fraction=0.20)),
        "transport tau_solute=30 s": dict(transport=dict(exchange_tau_s=30.0)),
        "transport tau_solute=120 s": dict(transport=dict(exchange_tau_s=120.0)),
        "transport tau_heat=10 s": dict(transport=dict(heat_exchange_tau_s=10.0)),
        "transport tau_heat=60 s": dict(transport=dict(heat_exchange_tau_s=60.0)),
        "radial straight tube (molecular D)": dict(transport=dict(model="radial")),
        "radial, coil mixing x10 (ASSUMED)": dict(transport=dict(model="radial", radial_mix_factor=10.0)),
        "radial, coil mixing x100 (ASSUMED)": dict(transport=dict(model="radial", radial_mix_factor=100.0)),
        # probe
        "probe tau_TT101=2 s": dict(sensors=dict(tt_tau_endpoint_s=2.0)),
        "probe tau_TT101=10 s": dict(sensors=dict(tt_tau_endpoint_s=10.0)),
        # truth threshold
        "truth threshold 2 %": dict(adequate_residual=0.02),
        "truth threshold 10 %": dict(adequate_residual=0.10),
        # VeriFlush thresholds
        "VF min contrast 1.0 degC": dict(policy=dict(min_contrast_c=1.0)),
        "VF min contrast 2.5 degC": dict(policy=dict(min_contrast_c=2.5)),
        "VF phi_arrival 0.4": dict(policy=dict(phi_arrival=0.4)),
        "VF phi_arrival 0.6": dict(policy=dict(phi_arrival=0.6)),
        "VF plateau 0.80": dict(policy=dict(phi_plateau=0.80)),
        "VF plateau 0.90": dict(policy=dict(phi_plateau=0.90)),
        "VF plateau hold 5 s": dict(policy=dict(plateau_hold_s=5.0)),
        "VF plateau hold 20 s": dict(policy=dict(plateau_hold_s=20.0)),
        "VF ratio warn 1.2": dict(policy=dict(ratio_warn_high=1.2)),
        "VF ratio warn 1.6": dict(policy=dict(ratio_warn_high=1.6)),
        "VF ratio fail 2.5": dict(policy=dict(ratio_fail=2.5)),
        "VF ratio fail 3.5": dict(policy=dict(ratio_fail=3.5)),
        # operating policy (applies to all methods)
        "policy 5 volumes (all methods)": dict(policy=dict(target_volumes=5.0)),
        "policy 5 volumes + beta=0.20": dict(policy=dict(target_volumes=5.0), transport=dict(slow_fraction=0.20)),
        "policy 5 volumes + tau_solute=120 s": dict(policy=dict(target_volumes=5.0), transport=dict(exchange_tau_s=120.0)),
        "policy 5 volumes + truth threshold 2 %": dict(policy=dict(target_volumes=5.0), adequate_residual=0.02),
        "branch 8 m (Rev-B rig)": dict(geometry=dict(branch_length_m=8.0)),
        **flows,
        "policy 5 volumes + flow 1.20 L/min": dict(policy=dict(target_volumes=5.0), **flows["flow 1.20 L/min"]),
    }


SENS_KEYS = ["S01_healthy", "S02_restricted", "S05_diversion", "S06_wrong_volume", "S07_flow_bias", "S10_weak_contrast"]


def sensitivity(n_seeds: int):
    rows = []
    for cname, ch in sensitivity_cases().items():
        for key in SENS_KEYS:
            for seed in range(n_seeds):
                c = perturbed(SCENARIOS[key], seed)
                if ch:
                    c = with_changes(c, **ch)
                for m in METHODS:
                    s, _, _ = run(c, m, seed=seed, record=False)
                    s["scenario"], s["case"] = key, cname
                    rows.append(s)
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "sensitivity_runs.csv", index=False)
    return df


def threshold_reclassification(mc: pd.DataFrame) -> pd.DataFrame:
    """Re-score the SAME Monte-Carlo runs against 2 / 5 / 10 % truth thresholds (decisions unchanged)."""
    rows = []
    for thr in (0.02, 0.05, 0.10):
        d = mc.copy()
        d["outcome"] = [classify(v, r <= thr) for v, r in zip(d.verdict, d.residual_old_fraction)]
        m = metrics(d)
        m.insert(0, "truth_threshold", thr)
        rows.append(m)
    return pd.concat(rows, ignore_index=True)


def transport_curves() -> pd.DataFrame:
    """In-pipe residual old-water fraction vs pipe volumes passed, constant healthy flow, SIMULATED."""
    base = Config()
    q = solve(base, 1.0).q_branch
    models = {
        "two-region baseline (N=10, beta=0.10, tau=60 s)": {},
        "tanks-in-series only (N=10, beta=0)": dict(transport=dict(slow_fraction=0.0)),
        "two-region N=5": dict(transport=dict(n_cells_branch=5)),
        "two-region beta=0.20": dict(transport=dict(slow_fraction=0.20)),
        "two-region tau=120 s": dict(transport=dict(exchange_tau_s=120.0)),
        "radial straight tube, salt (molecular D)": dict(transport=dict(model="radial")),
        "radial, coil mixing x10 (ASSUMED)": dict(transport=dict(model="radial", radial_mix_factor=10.0)),
        "radial D=0 (numerical laminar bound)": dict(transport=dict(model="radial", d_salt_m2s=0.0)),
    }
    v = base.geometry.branch_volume_l / 1000
    t_vol = v / q
    rows = []
    for name, ch in models.items():
        cfg = with_changes(base, **ch) if ch else base
        tr = make_transport(cfg)              # upstream line already holds fresh water (F = 0)
        tr.up[2][:] = base.thermal.t_feed_c   # ...at feed temperature, so heat and tracer start together
        n = int(math.ceil(8 * t_vol))
        for k in range(1, n + 1):
            tr.step(1.0, q, q, base.thermal.t_feed_c)
            rows.append(dict(model=name, theta=k / t_vol, residual=tr.residual_old_fraction,
                             outlet_old_fraction=float(tr.outlet[0]), outlet_temp_c=float(tr.outlet[2])))
    th = np.linspace(0.01, 8, 400)
    rows += [dict(model="analytical laminar bound 1/(4 theta)", theta=t, residual=float(r)) for t, r in zip(th, laminar_bound(th))]
    rows += [dict(model="plug flow (EPANET 2.2 assumption)", theta=t, residual=max(0.0, 1 - t)) for t in th]
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "transport_curves.csv", index=False)
    return df


def wntr_check():
    try:
        from model.wntr_crosscheck import crosscheck
    except ImportError:
        return None
    r = crosscheck()
    r.pop("curves").to_csv(PROC / "wntr_crosscheck_curves.csv", index=False)
    pd.DataFrame([r]).T.rename(columns={0: "value"}).to_csv(TAB / "wntr_crosscheck.csv")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", type=int, default=40)
    a = ap.parse_args()
    n = 8 if a.quick else a.seeds
    n_sens = 2 if a.quick else 10
    t0 = time.time()
    rep = representative_runs()
    print(f"representative runs: {len(rep)}  ({time.time() - t0:.0f} s)")
    summary = {}
    for backend in BACKENDS:
        mc = monte_carlo(n, backend)
        sfx = "" if backend == "two_region" else "_radial"
        m_all, m_sc = metrics(mc), metrics(mc, by=("scenario", "method"))
        m_all.to_csv(TAB / f"method_comparison_overall{sfx}.csv", index=False)
        m_sc.to_csv(TAB / f"method_comparison_by_scenario{sfx}.csv", index=False)
        threshold_reclassification(mc).to_csv(TAB / f"truth_threshold_rescore{sfx}.csv", index=False)
        if backend == "two_region":
            tta = mc.groupby("scenario")["time_to_adequate_ref_s"].mean().rename("mean_time_to_adequate_s_valve_held_open")
            tta.to_csv(TAB / "time_to_adequate_reference.csv")
        summary[backend] = m_all
        print(f"monte carlo [{backend}] done ({time.time() - t0:.0f} s)")
        print(m_all[["method"] + OUTCOMES + ["fault_detection_rate", "mean_water_l"]].to_string(index=False))
    sens = sensitivity(n_sens)
    metrics(sens, by=("case", "method")).to_csv(TAB / "sensitivity_by_case.csv", index=False)
    print(f"sensitivity done ({time.time() - t0:.0f} s)")
    transport_curves()
    w = wntr_check()
    meta = dict(
        status="SIMULATED", model_version=MODEL_VERSION, created_utc=datetime.now(timezone.utc).isoformat(),
        python=platform.python_version(), platform=platform.platform(),
        numpy=np.__version__, pandas=pd.__version__, scipy=__import__("scipy").__version__,
        matplotlib=__import__("matplotlib").__version__,
        wntr=(__import__("wntr").__version__ if w is not None else "not installed"),
        seeds_per_scenario=n, seeds_per_sensitivity_case=n_sens,
        seed_rule="method seed = s; physical perturbation seed = 1000+s; truth sensor = s+10000",
        transport_backends=BACKENDS,
        scenarios={k: v.description for k, v in SCENARIOS.items()},
        sensitivity_scenarios=SENS_KEYS, sensitivity_cases=list(sensitivity_cases()),
        base_config=Config().to_dict(), runtime_s=round(time.time() - t0, 1),
        outputs=["data/raw/*.csv", "data/processed/*.csv", "outputs/tables/*.csv"],
    )
    (ROOT / "data" / "simulation_metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"done in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
