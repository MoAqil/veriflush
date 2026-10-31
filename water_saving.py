"""Building-scale water-saving estimate: fixed-duration weekly flushing vs adaptive (VeriFlush-style) stop.

    python water_saving.py   ->  outputs/tables/water_saving.csv, outputs/tables/water_saving.md

Every input is either cited (reference number in references/references.md) or labelled ASSUMED.
The adaptive-stop volume multiplier comes from the SIMULATED Monte-Carlo runs of the rig
(healthy scenario, VeriFlush): water used / true branch volume. Results are MODELLED estimates.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
TAB = ROOT / "outputs" / "tables"

# (low-saving, central, high-saving) cases; each row: value tuple, unit, source
INPUTS = {
    "rooms": ((300, 300, 300), "rooms", "ASSUMED example: one 300-room hotel"),
    "unoccupied_fraction": ((0.15, 0.25, 0.35), "-", "ASSUMED share of rooms unoccupied >= 7 days in a given week"),
    "outlets_per_room": ((3, 4, 5), "outlets", "ASSUMED (basin, shower, bath, bidet spray / kitchenette)"),
    "fixed_flush_min": ((2.0, 3.0, 5.0), "min", "ASSUMED reading of 'several minutes' weekly [DM-HSD-GU44 v6 s.12-1; HSG274-2 para 2.78]"),
    "outlet_flow_lpm": ((6.0, 8.0, 9.0), "L/min", "ASSUMED low-flow fixture flows (UAE green-code limits NOT VERIFIED)"),
    "branch_length_m": ((12.0, 6.0, 3.0), "m", "ASSUMED riser-to-outlet run in a guest room"),
    "branch_id_mm": ((16.0, 15.0, 13.0), "mm", "ASSUMED 1/2-inch class pipe internal diameter"),
    "volumes_needed": ((5.0, 3.0, 3.0), "pipe volumes", "policy: 3 volumes; low case uses 5 = laminar 1/(4 theta) <= 5 % bound (this work)"),
}
WEEKS = 52
PER_CAPITA_LPD = 550.0   # UAE ~550 L/person/day, MOCCAE State of Environment 2015 as reported by u.ae (seen in search only)


def sim_overhead() -> float:
    """SIMULATED: VeriFlush water used / (target volumes x true branch volume), healthy MC runs."""
    f = ROOT / "data" / "processed" / "monte_carlo_runs.csv"
    mc = pd.read_csv(f)
    d = mc[(mc.scenario == "S01_healthy") & (mc.method == "VeriFlush")]
    return float((d.water_used_l / (3.0 * d.true_branch_volume_l)).median())


def estimate() -> pd.DataFrame:
    over = sim_overhead()
    rows = []
    for k, case in enumerate(("low saving", "central", "high saving")):
        x = {n: v[0][k] for n, v in INPUTS.items()}
        v_branch = math.pi / 4 * (x["branch_id_mm"] / 1000) ** 2 * x["branch_length_m"] * 1000      # L
        fixed = x["fixed_flush_min"] * x["outlet_flow_lpm"]                                          # L per outlet
        adaptive = x["volumes_needed"] * v_branch * over                                             # L per outlet
        n_flush = x["rooms"] * x["unoccupied_fraction"] * x["outlets_per_room"] * WEEKS
        net = (fixed - adaptive) * n_flush / 1000                                                    # m3/yr, can be < 0
        save = max(net, 0.0)
        rows.append(dict(case=case, **x, branch_volume_l=round(v_branch, 3), sim_overhead_factor=round(over, 3),
                         fixed_per_outlet_l=round(fixed, 2), adaptive_per_outlet_l=round(adaptive, 2),
                         flushes_per_year=round(n_flush), fixed_m3_per_year=round(fixed * n_flush / 1000, 1),
                         adaptive_m3_per_year=round(adaptive * n_flush / 1000, 1), net_difference_m3_per_year=round(net, 1), saving_m3_per_year=round(save, 1),
                         saving_pct=round(100 * save / (fixed * n_flush / 1000), 1),
                         fixed_time_sufficient=fixed >= adaptive,
                         person_days_equivalent=round(save * 1000 / PER_CAPITA_LPD)))
    return pd.DataFrame(rows)


def main():
    TAB.mkdir(parents=True, exist_ok=True)
    df = estimate()
    df.to_csv(TAB / "water_saving.csv", index=False)
    lines = ["# Water-saving estimate (MODELLED)", "",
             "Fixed-duration weekly flushing of unoccupied guest-room outlets vs an adaptive stop at the required "
             "number of pipe volumes, verified at the endpoint. One example 300-room hotel. Not a measured saving.", "",
             "## Inputs", "", "| input | low saving | central | high saving | unit | source |", "|---|---|---|---|---|---|"]
    for n, (v, u, src) in INPUTS.items():
        lines.append(f"| {n} | {v[0]} | {v[1]} | {v[2]} | {u} | {src} |")
    lines += [f"| adaptive overhead factor | {df.sim_overhead_factor[0]} | {df.sim_overhead_factor[0]} | "
              f"{df.sim_overhead_factor[0]} | - | SIMULATED: median VeriFlush water used / (3 x branch volume), S01 Monte Carlo |",
              "", "## Results", "", "| case | branch volume (L) | fixed per outlet (L) | adaptive per outlet (L) | "
              "fixed (m³/yr) | adaptive (m³/yr) | saving (m³/yr) | saving (%) |", "|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        lines.append(f"| {r.case} | {r.branch_volume_l} | {r.fixed_per_outlet_l} | {r.adaptive_per_outlet_l} | "
                     f"{r.fixed_m3_per_year} | {r.adaptive_m3_per_year} | {r.saving_m3_per_year} | {r.saving_pct} |")
    lines += ["", "## Reading the numbers", "",
              "- The saving comes from stopping when the branch has been exchanged instead of running a fixed time. "
              "If a branch is long or the flow is low, the adaptive stop can need **more** water than the fixed time; "
              "the column `fixed_time_sufficient` in the CSV flags that case (the fixed policy would then under-flush).",
              "- The adaptive volume assumes the endpoint verification works on that outlet. Where VeriFlush returns "
              "Uncertain (for example weak temperature contrast in summer, Proctor et al. 2020), the outlet falls back "
              "to the fixed policy and saves nothing.",
              f"- Person-days equivalent uses about {PER_CAPITA_LPD:.0f} L/person/day for the UAE (MOCCAE 2015 as reported "
              "by the UAE Government Portal; seen in search results only, treat as indicative).",
              "- The adaptive volume counts only the outlet branch. If the riser or floor main is also stagnant (whole "
              "floor unoccupied), fresh water must first reach the branch inlet and the adaptive volume grows; the large "
              "percentage savings in the central and high cases then shrink. Treat them as an upper range.",
              "- The central case uses the 3-volume policy. The simulation shows 3 volumes can leave more than 5 % old "
              "water when the laminar tail is heavy (assumptions_and_equations.md, Section 3); the low case uses 5 volumes.",
              "- Requires physical validation: real branch volumes, fixture flows and occupancy patterns must be "
              "measured in the target building."]
    (TAB / "water_saving.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(df[["case", "fixed_per_outlet_l", "adaptive_per_outlet_l", "saving_m3_per_year", "saving_pct"]].to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
