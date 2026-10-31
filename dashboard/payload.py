"""Turn simulation runs into the JSON payload used by the dashboard player (template.html).

The payload carries decision-visible signals and TRUTH signals in clearly separated
fields; the player shows truth only in panels labelled 'TRUTH: not used by VeriFlush'.
All values are SIMULATED.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.decisions import METHODS  # noqa: E402
from model.params import MODEL_VERSION, Config, with_changes  # noqa: E402
from model.simulate import PROFILE_N, run  # noqa: E402
from scenarios.library import SCENARIOS  # noqa: E402

BACKEND_LABEL = {"two_region": "Two-region transport (baseline)", "radial": "Radial laminar, straight tube"}
TEMPLATE = Path(__file__).with_name("template.html")


def _r(a, nd=3):
    out = []
    for x in a:
        x = float(x)
        out.append(None if math.isnan(x) else round(x, nd))
    return out


def run_payload(summary: dict, df) -> dict:
    prof = df[[f"truth_profile_{i:02d}" for i in range(PROFILE_N)]].to_numpy()
    s = summary
    return dict(
        verdict=s["verdict"], reason=s["reason"], warnings=[w for w in s["warnings"].split(" | ") if w],
        t_close=s["t_close_s"], water_used=round(s["water_used_l"], 4), water_diverted=round(s["water_diverted_l"], 4),
        residual=round(s["residual_old_fraction"], 5), outcome=s["outcome"], v_recorded=round(s["v_recorded_l"], 4),
        series=dict(
            t=_r(df.obs_t_s, 1), cmd=df.obs_valve_cmd.astype(int).tolist(), lso=df.obs_ls_open.astype(int).tolist(),
            lsc=df.obs_ls_closed.astype(int).tolist(), q=_r(df.obs_ft_flow_lpm), v=_r(df.ctrl_v_l, 4),
            tt100=_r(df.obs_tt100_c), tt101=_r(df.obs_tt101_c), p=_r(df.obs_pt_kpa),
            # ---- TRUTH (evaluation / visualisation only)
            pos=_r(df.truth_valve_pos), qt=_r(df.truth_q_branch_lpm), qd=_r(df.truth_q_div_lpm),
            fo=_r(df.truth_f_old_outlet, 4), res=_r(df.truth_residual_old_fraction, 4),
            cond=_r(df.truth_c_endpoint_uscm, 0), prof=np.round(prof, 3).tolist(),
        ),
    )


def scenario_payload(key: str, cfg: Config, seed: int = 0) -> dict:
    runs = {}
    for m in METHODS:
        s, df, _ = run(cfg, m, seed=seed, record=True)
        runs[m.name] = run_payload(s, df)
    return dict(key=key, title=key.split("_", 1)[1].replace("_", " "), code=key.split("_")[0],
                description=cfg.description, has_fault=cfg.has_fault, configured_l=round(cfg.configured_l, 4),
                true_l=round(cfg.geometry.branch_volume_l, 4), length_m=cfg.geometry.branch_length_m,
                diversion_open=cfg.hydraulics.diversion_open, adequate=cfg.adequate_residual,
                target_volumes=cfg.policy.target_volumes, runs=runs)


def build(scenarios: dict | None = None, backends=("two_region", "radial"), seed: int = 0) -> dict:
    scenarios = scenarios or SCENARIOS
    data = {}
    for b in backends:
        data[b] = [scenario_payload(k, c if b == "two_region" else with_changes(c, transport=dict(model=b)), seed)
                   for k, c in scenarios.items()]
    return dict(meta=dict(status="SIMULATED", model_version=MODEL_VERSION, seed=seed,
                          generated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                          backends={b: BACKEND_LABEL.get(b, b) for b in backends}),
                data=data)


def render(payload: dict) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    js = json.dumps(payload, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    return html.replace("/*__PAYLOAD__*/null", js)
