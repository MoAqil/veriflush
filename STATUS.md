# STATUS (30 Oct 2026, model v1.1.0)

All results are **SIMULATED**. None of them is a physical measurement.

## What works

| Deliverable | Where | State |
|---|---|---|
| Software decision matrix | `software_comparison.md` | done; WNTR now run as a cross-check |
| Working simulation | `model/`, `run_experiments.py` | two-region baseline plus a new radially resolved laminar backend (`model/radial.py`) |
| Virtual sensor spec | `virtual_sensor_spec.md` | done, with datasheet sources |
| Scenario library | `scenarios/library.py` | S01–S12, with S09 split into a and b: 13 scenarios |
| Decision engines | `model/decisions.py` | timer-only, flow + configured volume, VeriFlush; **thresholds unchanged from the draft** |
| Metrics vs tracer truth | `outputs/tables/method_comparison_*.csv`, `truth_threshold_rescore*.csv` | 520 runs per method per transport model |
| Figures | `outputs/figures/` | 9 figures, PNG at 300 dpi and SVG, with `captions.md` |
| Sensitivity | `outputs/tables/sensitivity_by_case.csv`, Figure 7 | 34 cases × 6 scenarios × 10 seeds |
| WNTR / EPANET cross-check | `model/wntr_crosscheck.py`, `outputs/tables/wntr_crosscheck.csv` | travel time, age and head loss agree in the plug-flow limit |
| Interactive dashboard | `dashboard/app.py` | runs live simulations with fault overrides; opened and checked in a browser, no server errors |
| Offline dashboard | `outputs/veriflush_dashboard.html` (1.8 MB, no dependencies) | animated rig, controls, verdict, TRUTH panel, 6 charts, 3-method table, CSV download; checked in a browser |
| Screenshots | `outputs/screenshots/` (17) | every scenario at its final verdict, plus 4 extra views |
| Tests and validation table | `tests/`, `outputs/tables/validation_table.md` | **42/42 pass**: the draft's 28 plus 14 new |
| Water-saving estimate | `water_saving.py`, `outputs/tables/water_saving.md` | low / central / high; inputs cited or ASSUMED |
| Equations and assumptions | `assumptions_and_equations.md` | done |
| IEEE references | `references/references.md`, `references/research_notes.md` | 30 sources, each with check status |
| Report evidence, limitations, validation plan | `report_assets/report_evidence.md` | done |
| Video script | `video/one_minute_script.md` | done; **no MP4 recorded** |
| Reproducibility | `requirements.txt` (pinned), `data/simulation_metadata.json`, `run_all.py` | done |
| Firmware (P2) | `firmware/veriflush/veriflush.ino`, `firmware/logger.py` | compiles with g++ 16 against Arduino stand-ins; **replay of the simulated sensor traces gives the same verdict, stop second and litres as the Python engine in 13/13 scenarios** (`outputs/tables/firmware_vs_python.csv`); not yet run on an Uno |
| EPANET 2.2 rig models | `epanet/VeriFlush_S0*.inp`, `epanet/epanet_vs_python.csv`, Figure 10 | 5 scenarios; flows and manifold pressure within 0.6 % of the Python model, endpoint arrival within 2 s |
| Wokwi project | `wokwi/` | real firmware + DS18B20s + servo + rig-emulator custom chip. Loaded into wokwi.com and the circuit renders; Wokwi's AVR compiler caught an Arduino prototype-ordering bug (fixed). Rebuild then failed on network timeouts to wokwi.com, so **not yet run to a verdict in Wokwi** |
| Blender 3D model | `3d/build_rig.py`, `3d/README.md`, `3d/renders/` | **planned** Rev-B assembly (rig not yet built), modelled to match the team's purchased parts (photos in `3d/reference_photos/`): push-fit valves, brass barbs, YF-S401, MG996R, ANDELI switches, IP65 box with Uno + screw shield + XL4015; coil colour, valve and TK-103 level animated from the S01 simulation. Tanks, former, layout ASSUMED |

## Headline results (SIMULATED, 5 % residual truth threshold, 520 runs per method)

| Method | False passes: two-region | False passes: radial straight tube | Fault detection | Uncertain |
|---|---|---|---|---|
| Timer-only | 194 (37 %) | 422 (81 %) | 0 % | 0 % |
| Flow + configured volume | 160 (31 %) | 386 (74 %) | 26 % | 0 % |
| VeriFlush | **0** | **0** | 93 % / 92 % | 54 % |

Wrong failures of a good flush:

| Method | Two-region | Radial straight tube |
|---|---|---|
| Timer-only | 0 | 0 |
| Flow + configured volume | 73 | 73 |
| VeriFlush | 1 | 5 |

**What is new compared with the head-start draft:**
- **Radially resolved laminar model.** It has no tuned transport parameters and reproduces the analytical 1/(4θ) bound to within 0.003.
  - Using it, 3 volumes in a straight 8 mm tube leave **5.9 %** old water (bound 8.3 %; two-region baseline 4.0 %).
  - The two-region baseline is therefore *not* conservative relative to straight-tube physics, and the 3-volume / 5 % policy pair is marginal.
- **VeriFlush is not immune to the laminar tail.** In the sensitivity study it gives false passes when:
  - the tail is heavier than the baseline: β = 0.20 → 60 %; τ = 120 s → 55 %;
  - flow is 1.2 L/min → 45 %;
  - truth threshold is 2 % → 60 %.
- **Temperature cannot see the last near-wall old water** (Figure 9).
- Re-run with a 5-volume target (all methods), the same four cases gave **0 VeriFlush false passes** (false failures 10/60 for β = 0.20, τ = 120 s and the 2 % threshold, 0/60 at 1.2 L/min; 53–72 % more water than the 3-volume baseline). Timer and meter still had 33–60 % and 45–60 % false passes in those cases.
- **Pressure.** The 0–3 bar PI-101 cannot resolve the rig's 3–4 kPa. Pressure logic is a virtual 0–10 kPa transducer that the rig does not yet have.
- **Probe time constant.** Default changed from 4 s to 5 s, based on a published still-water test (6.2–6.9 s).

## How it was tested

- `pytest`: 42 tests, run on Windows 11, Python 3.12.4. Coverage:
  - unit consistency; pipe volume;
  - Hagen–Poiseuille; Erlang tanks-in-series; laminar bound;
  - grid and time-step convergence;
  - tracer and volume conservation;
  - fixed-seed repeatability;
  - expected verdicts; NaN/None input;
  - truth separation: runtime (tracer change does not change decisions) and a static AST check of `decisions.py`;
  - CSV and figure output; dashboard payload;
  - WNTR agreement.
- Full Monte Carlo and sensitivity: `python run_experiments.py`, 343 s.
- Dashboards:
  - offline HTML opened in the in-app browser, played, scrubbed, switched across scenarios;
  - Streamlit app launched and rendered with no server errors;
  - headless-Edge screenshots of all 13 scenarios inspected.
- Independent review: a separate agent checked numbers vs tables, citations, simulated-vs-measured wording and truth separation. The fixes are listed in the review section below.

## Still unverified

- **All numbers against the physical rig.**
- Transport parameters N, β, τ (ASSUMED, bracketed), and the coil-mixing factor (ASSUMED proxy).
- Hall-sensor behaviour below 0.3 L/min; probe τ in moving water; loaded servo speed; source curve H₀ and R_s (calibrated to about 0.63 L/min, not pump data).
- **EPANET-MSX:** attempted, but WNTR 1.5's MSX writer did not carry the initial tracer state. No MSX result.
- **Firmware:** not compiled. Test it in Wokwi first.
- **UAE per-capita 550 L/day:** reported (seen in search results), not opened. UAE fixture-flow limits not verified.
- **References not opened at all:** [3] Levenspiel and [9] Saxena & Nigam. Do not use them for specific claims.
- **No Playwright MP4.** Record the video with OBS from the deep links.

## Next on the physical rig (in order)

1. Calibrate the FT-101 K-factor at 0.3, 0.6 and 1.0 L/min, and the DS18B20 offsets and τ in flow.
2. **Saline step-response runs** at 3 flows. Fit N, β, τ and compare with the radial prediction. This decides whether the volume target should be 3 or 5.
3. Thermal vs tracer on the same runs, to confirm or refute Figure 9.
4. Fault scenarios with 5 repeats each and a blind truth read. Build the rig confusion matrix.
5. Decide on pressure: fit a 0–10 kPa transducer, or drop pressure from the rules.
6. Flash the firmware (after a Wokwi test) and log with `firmware/logger.py`.

## Reproduce everything

**Windows, from `digital_prototype/`:**

```bash
py -3.12 -m venv $HOME\.venvs\veriflush
```

```bash
$HOME\.venvs\veriflush\Scripts\python -m pip install -r requirements.txt
```

```bash
$HOME\.venvs\veriflush\Scripts\python run_all.py
```

```bash
$HOME\.venvs\veriflush\Scripts\python -m streamlit run dashboard/app.py
```

`run_all.py` regenerates the following, all with seeds fixed:
- the validation table;
- the Monte Carlo and sensitivity runs;
- the water-saving estimate;
- the figures;
- the offline dashboard;
- the screenshots.

## Review findings and fixes

An independent agent (no access to the build reasoning) checked numbers, citations, wording and truth separation. It found 12 issues; all were fixed:

| # | Finding | Fix |
|---|---|---|
| 1 | 5-volume claim not supported (never run with the heavy-tail cases) | 4 combined cases added and run; text now quotes their results |
| 2 | "timer and meter worse in the same cases" false at 1.2 L/min | reworded with the 17 % vs 45 % numbers |
| 3 | 5.8 / 3.8 / "< 0.1 %" did not match the transport CSV | corrected to 5.9 / 4.0 / 0.7 %; flow stated as 0.63 L/min |
| 4 | verification records claimed but missing | software_comparison check line corrected; this section added |
| 5 | NOT OPENED source [3] used for a claim | removed |
| 6 | headlines said "Rev-B rig" but use the 6 m spec branch | stated everywhere; 8 m case results quoted |
| 7 | Figure 6 caption overstated "between" | caption limited to θ ≈ 2–4 |
| 8 | wording: SDG 6.1 health-adjacent, "self-calibrating", "exactly this criterion", video lines | reworded |
| 9 | Dean number ≈ 260 | ≈ 270 |
| 10 | water-saving CSV clamped a negative saving to 0 | `net_difference_m3_per_year` column added |
| 11 | Figure 9 caption mentioned in-branch residual not plotted | corrected |
| 12 | truth threshold sat in `Policy` (readable by controllers); unlabelled truth values in the dashboard | moved to `Config.adequate_residual` + new test; dashboard labels say "truth" |

Spot-checked sources opened by the reviewer: [1], [23], [24], [25] (all support the claims); MathWorks, Modelica, Streamlit, COMSOL pages live; AnyLogic page 403 (claim supported via search); Wokwi and [18] unreachable at review time.

## Update 31 Oct 2026

- **EPANET 2.2 desktop app.** S01 and S05 were run in the desktop app (`epanet2w.exe`). The map at 15, 30 and 45 s and the TT101 graphs are in `outputs/epanet_gui/`. The TT101 50 % crossings (34 s and 52 s) match `epanet_vs_python.csv`. The app needs `0:00:01` typed into its time steps (see the README there).
- **Real Uno build.** `arduino-cli compile -b arduino:avr:uno firmware/veriflush` passes. Toolchain: arduino-cli 1.5.1, arduino:avr 1.8.8, OneWire, DallasTemperature and Servo 1.3.0. Size: 12,952 B flash (40 %) and 384 B RAM (18 %). The sketch has not been uploaded to a board yet.
- **Final report.** `report_assets/fill_report.py` fills the report's simulation-answerable fields with SIMULATED values and writes a new .docx. Fields that need physical data stay yellow.
