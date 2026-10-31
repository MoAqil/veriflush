"""Regenerate everything: tests + validation table, experiments, figures, water-saving
estimate, offline dashboard and screenshots.

    python run_all.py            # full (about 10-20 min)
    python run_all.py --quick    # reduced seeds, for a smoke test

All generated numbers are SIMULATED / MODELLED.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

# test name -> (requirement area, expected behaviour)
VALIDATION = {
    "test_pipe_volume_6m_8mm": ("Pipe volume", "V = πD²L/4 = 0.3016 L for 6 m × 8 mm"),
    "test_pipe_volume_8m_8mm": ("Pipe volume", "0.4021 L for the 8 m Rev-B branch"),
    "test_flow_unit_round_trip": ("Unit consistency", "L/min ↔ m³/s conversions are exact"),
    "test_configured_volume_defaults_to_ideal": ("Unit consistency", "configured volume defaults to the ideal pipe volume"),
    "test_hagen_poiseuille": ("Hydraulics", "laminar head loss equals Hagen–Poiseuille"),
    "test_friction_factor_continuity": ("Hydraulics", "f = 64/Re below 2000 and Blasius at 4000"),
    "test_inverse_flow": ("Numerical stability", "flow(head) inverts head(flow)"),
    "test_continuity_at_fault_tee": ("Mass/volume conservation", "Q_meter = Q_branch + Q_diversion at the tee"),
    "test_healthy_flow_in_rig_range": ("Physical plausibility", "healthy flow inside the 0.3–1.2 L/min rig target"),
    "test_closed_valve_zero_flow": ("Physical plausibility", "closed XV-101 gives zero flow"),
    "test_blockage_raises_manifold_pressure": ("Physical plausibility", "blockage raises manifold pressure"),
    "test_tanks_in_series_matches_erlang": ("Analytical verification", "mobile zone matches the Erlang/Poisson solution"),
    "test_tracer_mass_conservation": ("Mass/volume conservation", "tracer inventory + outflow is conserved (two-region)"),
    "test_water_volume_balance": ("Mass/volume conservation", "outlet + diverted volume = metered volume"),
    "test_temperature_bounds": ("Physical plausibility", "temperatures stay between feed and stagnant values"),
    "test_time_step_convergence": ("Time-step convergence", "halving the sub-step changes residual < 0.002"),
    "test_no_flow_no_exchange": ("Physical plausibility", "no flow, no exchange"),
    "test_truth_not_visible_to_methods": ("Truth/decision separation", "Observation and Known contain no truth fields"),
    "test_decisions_independent_of_truth_tracer": ("Truth/decision separation", "changing tracer truth changes no decision"),
    "test_repeatable_with_seed": ("Fixed-seed repeatability", "same seed gives identical time series"),
    "test_expected_verdicts": ("Decision logic", "VeriFlush verdicts for S01, S04, S08–S12 as designed"),
    "test_diversion_and_wrong_volume_are_flagged": ("Decision logic", "S05/S06/S07 raise the volume-mismatch warning"),
    "test_timer_never_detects": ("Decision logic", "timer-only always records completion"),
    "test_missing_values_handled": ("Missing values", "NaN/None samples never crash and never give Verified"),
    "test_every_result_has_reason": ("Decision logic", "every verdict carries a reason"),
    "test_all_methods_stop_by_time_limit": ("Decision logic", "every method stops by t_max"),
    "test_sensor_ranges": ("Physical plausibility", "sensor values inside physical ranges; residual never increases"),
    "test_csv_and_figure_generation": ("CSV and figure generation", "CSV and PNG are written"),
    "test_laminar_bound_formula": ("Analytical verification", "1 − θ / 1/(4θ) piecewise bound"),
    "test_zero_diffusion_matches_laminar_bound": ("Analytical verification", "radial model with D = 0 reproduces 1/(4θ)"),
    "test_grid_convergence": ("Numerical stability", "radial model grid-converged (20×120 vs 40×240)"),
    "test_diffusion_only_reduces_residual": ("Physical plausibility", "molecular diffusion shortens the laminar tail"),
    "test_tracer_conservation": ("Mass/volume conservation", "tracer conserved in the radial model"),
    "test_temperature_bounded": ("Physical plausibility", "radial temperatures bounded by feed and stagnant values"),
    "test_profile_shape_and_range": ("Physical plausibility", "branch profile in [0,1], inlet fresher than endpoint"),
    "test_decision_module_never_touches_truth": ("Truth/decision separation", "decisions.py imports and names no truth object (static check)"),
    "test_radial_decisions_independent_of_tracer": ("Truth/decision separation", "tracer independence also holds with the radial model"),
    "test_truth_threshold_not_in_controller_inputs": ("Truth/decision separation", "adequacy threshold is not a controller input"),
    "test_radial_expected_verdicts": ("Decision logic", "S01/S04/S10 verdicts unchanged with radial physics"),
    "test_epanet_agrees_in_plug_flow_limit": ("Independent cross-check", "EPANET 2.2 travel time, age, head loss agree with the Python model"),
    "test_firmware_matches_python_engine": ("Firmware", "Arduino firmware (host-compiled) gives the same verdict and stop second as the Python engine, 13/13 scenarios"),
    "test_payload_and_render": ("Dashboard", "dashboard payload complete; SIMULATED banner and TRUTH label present"),
}


def step(*args):
    print("\n>>", " ".join(args), flush=True)
    subprocess.run([PY, *args], cwd=ROOT, check=True)


def tests_and_validation_table():
    with tempfile.TemporaryDirectory() as d:
        xml = Path(d) / "junit.xml"
        r = subprocess.run([PY, "-m", "pytest", "tests", "-q", f"--junitxml={xml}"], cwd=ROOT)
        cases = ET.parse(xml).getroot().iter("testcase")
        rows = []
        for c in cases:
            name = c.get("name")
            status = "FAIL" if c.find("failure") is not None or c.find("error") is not None else \
                "SKIPPED" if c.find("skipped") is not None else "PASS"
            area, expect = VALIDATION.get(name, ("(unmapped)", ""))
            rows.append((area, expect, f"`{c.get('classname').split('.')[-1]}.{name}`", status, float(c.get("time"))))
    rows.sort()
    n_pass = sum(r[3] == "PASS" for r in rows)
    lines = ["# Validation table", "", f"Generated by `python run_all.py`. {n_pass}/{len(rows)} tests passed. "
             "Tests check the virtual testbed itself (code, numerics and logic); they are not physical validation.", "",
             "| Area | Expected behaviour | Test | Result | Time (s) |", "|---|---|---|---|---|"]
    lines += [f"| {a} | {e} | {t} | {s} | {tm:.2f} |" for a, e, t, s, tm in rows]
    (ROOT / "outputs" / "tables" / "validation_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"validation table: {n_pass}/{len(rows)} PASS")
    if r.returncode:
        raise SystemExit("tests failed; see output above")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-screenshots", action="store_true")
    a = ap.parse_args()
    (ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
    tests_and_validation_table()
    step("run_experiments.py", *(["--quick"] if a.quick else []))
    step("water_saving.py")
    step("epanet/build_epanet.py")
    from firmware.hil.run_replay import compiler
    if compiler():
        step("firmware/hil/run_replay.py")
    step("make_figures.py")
    step("dashboard/export_html.py")
    if not a.no_screenshots:
        step("dashboard/screenshots.py")
    print("\nAll outputs regenerated. See STATUS.md.")


if __name__ == "__main__":
    main()
