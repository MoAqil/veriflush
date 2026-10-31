"""VeriFlush interactive dashboard (Streamlit).

    streamlit run dashboard/app.py

Runs the virtual testbed live for the chosen scenario, transport model, seed and
optional fault overrides, then shows the animated rig player (same player as the
offline HTML export), the three-method comparison and CSV downloads.
All data are SIMULATED.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload import BACKEND_LABEL, render, scenario_payload  # noqa: E402

from model.decisions import METHODS  # noqa: E402
from model.params import MODEL_VERSION, with_changes  # noqa: E402
from model.simulate import run  # noqa: E402
from scenarios.library import SCENARIOS  # noqa: E402

st.set_page_config(page_title="VeriFlush digital prototype", layout="wide")
st.markdown(
    "<div style='background:#141413;color:#f4f3ef;padding:8px 14px;border-radius:6px;font:600 12px monospace;"
    "letter-spacing:.08em'>■ SIMULATED DATA · VIRTUAL TESTBED OUTPUT, NOT PHYSICAL MEASUREMENTS</div>",
    unsafe_allow_html=True)

with st.sidebar:
    st.header("Event")
    key = st.selectbox("Scenario", list(SCENARIOS), format_func=lambda k: k.replace("_", " "))
    backend = st.radio("Transport model (truth physics)", list(BACKEND_LABEL), format_func=BACKEND_LABEL.get)
    seed = st.number_input("Seed (sensor noise and biases)", 0, 999, 0)
    st.header("Overrides (optional)")
    base = SCENARIOS[key]
    length = st.select_slider("Branch length (m)", [6.0, 8.0], value=base.geometry.branch_length_m)
    div = st.slider("DV-101 diversion opening", 0.0, 1.0, float(base.hydraulics.diversion_open), 0.05)
    k_r = st.slider("R-101 restriction K", 0.0, 1500.0, float(base.hydraulics.k_restriction), 50.0)
    t_feed = st.slider("Feed temperature (°C)", 8.0, 24.0, float(base.thermal.t_feed_c), 0.1)
    bias = st.slider("FT-101 bias (x reading)", 0.5, 2.0, float(base.faults.flow_bias), 0.05)
    thr = st.select_slider("Truth threshold (residual)", [0.02, 0.05, 0.10], value=base.adequate_residual)
    st.caption("Overrides change the simulated physical event. VeriFlush thresholds are fixed "
               "(see assumptions_and_equations.md and the sensitivity study).")

cfg = with_changes(base, geometry=dict(branch_length_m=length),
                   hydraulics=dict(diversion_open=div, k_restriction=k_r),
                   thermal=dict(t_feed_c=t_feed), faults=dict(flow_bias=bias),
                   adequate_residual=thr, transport=dict(model=backend))
if cfg.configured_volume_l is None and length != base.geometry.branch_length_m:
    st.sidebar.info("Configured volume follows the new length (ideal pipe volume).")


@st.cache_data(show_spinner="Running the virtual flush for all three methods…")
def simulate(cfg_repr: str, seed: int):    # cfg_repr is the cache key
    sp = scenario_payload(key, cfg, seed)
    frames = {}
    for m in METHODS:
        _, df, _ = run(cfg, m, seed=seed, record=True)
        df.insert(0, "data_status", "SIMULATED")
        frames[m.name] = df
    return sp, frames


sp, frames = simulate(repr(cfg), int(seed))
payload = dict(meta=dict(status="SIMULATED", model_version=MODEL_VERSION,
                         seed=int(seed), generated_utc="live run", backends={backend: BACKEND_LABEL[backend]}),
               data={backend: [sp]})
components.html(render(payload), height=1720, scrolling=True)

st.subheader("Three-method comparison")
rows = [dict(method=m, verdict=r["verdict"], outcome_vs_truth=r["outcome"], stop_s=r["t_close"],
             water_used_l=r["water_used"], residual_truth_pct=round(100 * r["residual"], 2), reason=r["reason"],
             warnings=" | ".join(r["warnings"])) for m, r in sp["runs"].items()]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.caption("residual_truth_pct and outcome_vs_truth come from the tracer TRUTH, which no method can read.")

cols = st.columns(len(frames))
for c, (m, df) in zip(cols, frames.items()):
    c.download_button(f"CSV · {m}", df.to_csv(index=False).encode(), file_name=f"veriflush_{key}_{m.split()[0]}_seed{seed}.csv",
                      mime="text/csv", use_container_width=True)
