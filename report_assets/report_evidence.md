# Report evidence pack

*For the KU–UNESCO Global Water Hackathon 2026, Theme 3. Numbers in brackets refer to [references/references.md](../references/references.md). Every result quoted here is **SIMULATED** (VeriFlush virtual testbed v1.1.0) unless a reference is given. Rule for writing the report: write "the simulation predicted…", "under the stated assumptions…" and "requires physical validation". Never write "measured" or "validated".*

**Scope statement (use it verbatim).** VeriFlush verifies **hydraulic water exchange** at the endpoint of a flushed branch. It makes **no** claim about:
- pathogens or Legionella;
- disinfectant residual;
- potability;
- regulatory compliance.

## 1. Problem definition and scale

- Water left standing in building plumbing during low use (closures, empty rooms) loses quality. Large-building guidance recommends flushing, but **the duration needed is very hard to generalise**. Diagnostic tests such as temperature or disinfectant residual can help decide how long to flush each outlet [23].
- Criteria for the efficacy of routine weekly flushing of unoccupied outlets **have not been thoroughly documented** [23].
- Scale example: recommissioning 10 university buildings used more than 14 m³ of water [29].

## 2. Existing flushing practice

- **Dubai Municipality guideline v6 (Aug 2025), Sec. 12-1** [24]:
  - run all taps and showers in guest rooms for **several minutes**, at least weekly when unoccupied and before occupation;
  - remove dead legs;
  - keep cold water below 20 °C.
  - The requirement is stated as a **time**, with no check that the water actually changed.
- **HSE HSG274 Part 2 (2024)** [25]:
  - weekly flushing of infrequently used outlets "for several minutes" (para 2.78);
  - the checklist says to flush **until the outlet temperature stabilises and is comparable to the supply**. VeriFlush automates a version of this criterion: endpoint temperature converging on the supply temperature (φ ≥ 0.85 for 10 s), combined with a volume count.
- **CDC toolkit** [26]: Legionella water management programmes are the standard framework in US buildings.

## 3. Limits of timer-only (and meter-only) flushing

**Evidence types recorded today:** timer, valve-opened signal, upstream meter volume, checklist. None of them observes the **endpoint**.

**Simulation result** (Monte Carlo, 13 scenarios × 40 perturbed events = 520 runs per method, two-region transport, 5 % residual truth threshold; `outputs/tables/method_comparison_overall.csv`):

| Method | False pass (recorded complete, but > 5 % old water left) | Fault-detection rate (fault scenarios) | Uncertain | False failure | Mean water per flush |
|---|---|---|---|---|---|
| Timer-only | **194 / 520 (37 %)** | 0 % | 0 | 0 | 0.82 L |
| Flow + configured volume | **160 / 520 (31 %)** | 26 % | 0 | 73 | 0.98 L |
| VeriFlush | **0 / 520** | **93 %** | 281 (54 %) | 1 | 0.94 L |

**Same comparison with the radially resolved straight-tube physics** (`method_comparison_overall_radial.csv`):

| Method | False pass | Fault-detection rate | Uncertain | False failure |
|---|---|---|---|---|
| Timer-only | 422 / 520 (81 %) | 0 % | 0 | 0 |
| Flow + configured volume | 386 / 520 (74 %) | 26 % | 0 | 73 |
| VeriFlush | **0 / 520** | 92 % | 281 | 5 |

VeriFlush used about 9 % more water here (1.03 L vs 0.94 L).

**Why the meter method fails.** Diversion after the meter (S05) passes metered water that never reaches the endpoint. A meter over-reading (S07) and a configured volume that is too small (S06) stop the flush early. A restriction below the meter's specified range (S02, about 0.27 L/min) causes false failures.

**The honest catch: Uncertain is frequent.**
- VeriFlush returns **Uncertain in 54 % of runs**. Almost all come from scenarios where Uncertain is the correct answer: dead or frozen endpoint sensor, flow-sensor dropout, weak temperature contrast, inconsistent valve feedback, or multiple faults (S03, S08–S12).
- In the six sensitivity scenarios its Uncertain rate is 17 %, which is the weak-contrast scenario S10.
- Report this as designed behaviour ("the system says when it cannot know"), not as a failure. Still, a deployment would need a follow-up action for Uncertain outcomes.

## 4. Methodology

**Digital prototype.** Python simulation of the Rev-B rig design (headline runs use the 6 m × 8 mm spec branch; the 8 m as-built branch is a sensitivity case: VeriFlush 0 false passes and 6/60 false failures, Timer-only 40 % and Flow + configured volume 45 % false passes):
- quasi-steady Darcy–Weisbach hydraulics with diversion tee and valve characteristics;
- 1-D two-region transport of old-water fraction, tracer, temperature and age;
- a radially resolved laminar transport model as a physics cross-check;
- virtual sensors with datasheet-based errors [16]–[22];
- three online decision controllers.

**Truth separation.** Tracer truth is never readable by any decision method. This is enforced by code structure (the `Observation` vs `Truth` records) and by three tests, including a static check of `decisions.py`.

**Recognised-tool layers.**
- **EPANET 2.2 rig models.** All five hydraulic scenarios are written as `.inp` files. Branch, meter and diverted flows and the manifold pressure agree with the Python model within 0.6 %; endpoint arrival agrees within 2 s (`epanet/epanet_vs_python.csv`, Figure 10).
  - **EPANET 2.2 desktop app (MODELLED).** S01 and S05 were also opened and run in EPA's own EPANET 2.2 GUI, with TRACE FEED quality and 1 s steps. Screenshots are in `outputs/epanet_gui/` (see `README.md` there): the map at 15, 30 and 45 s, and the TT101 time series.
    - S01 healthy: the fresh-water front reaches TT101 at about 34 s (50 % crossing).
    - S05 diversion: with DV-101 open, about half the flow leaves before the coil. The front is still short of TT101 at 45 s and crosses 50 % at about 52 s.
    - Both crossings match `epanet_vs_python.csv` (34 s and 52 s).
- **Firmware.** The Arduino controller code, fed the simulated sensor traces, reproduces the Python engine's verdict, stop second and metered litres in 13/13 scenarios.
- **Wokwi.** A virtual-circuit project with the real firmware is included (not yet run in Wokwi).
- **Blender.** A 3D model of the rig, animated from the simulation, is included for communication only. It is not a source of results.

**Cross-check.** EPANET 2.2 via WNTR [13], [15] agrees in the plug-flow limit:

| Quantity | Analytical | Python | EPANET |
|---|---|---|---|
| Endpoint travel time | 32.5 s | 33 s | 34 s |
| Endpoint water age | — | 32.5 s | 32.0 s |
| Head loss | — | — | agrees within 2 % |

**Testing.**
- 40 automated tests: unit consistency, analytical solutions, conservation, convergence, repeatability, decision logic, missing values, truth separation, file generation. See `outputs/tables/validation_table.md`.
- Sensitivity study over 34 one-at-a-time cases (Figure 7).

## 5. Equations

See [assumptions_and_equations.md](../assumptions_and_equations.md). Equations worth showing in the report:
- V = πD²L/4 = 0.3016 L;
- the laminar bound r(θ) = 1/(4θ) for θ ≥ ½. It implies that **3 volumes leave up to 8.3 % old water in a straight laminar tube with no radial mixing, and 5 % needs 5 volumes**;
- the normalised endpoint response φ;
- the endpoint-anchored volume V_est = V_arrival − V_up.

## 6. Innovation

- **Endpoint-anchored verification.**
  - VeriFlush measures, on every flush, how much metered water was needed before fresh water arrived at the endpoint (φ ≥ 0.5).
  - It uses that as the branch's effective volume, so the endpoint becomes a check on the meter. It flags diversion, meter over-reading or a wrong configured volume (arrival ratio ≠ 1), but it cannot tell these causes apart.
  - Diversion, meter bias and wrong configuration show up as an arrival ratio ≠ 1 and are flagged.
  - S05, S06 and S07 are flagged in every seed-0 run (test), and none produced a VeriFlush false pass.
- **Three-way verdict with reasons.** Verified / Failed / Uncertain, each with a human-readable reason, water used and a CSV log. Missing or implausible evidence can never yield "Verified".
- **Low-cost hardware.** Arduino Uno, two DS18B20 probes, a hobby Hall-effect flow sensor, a servo valve and limit switches. A firmware port of the rules is included, but it has not been compiled or run on hardware.

## 7. UN-Water / SDG alignment

- **SDG 6.1** (drinking-water services): evidence that a flush actually exchanged the water in a branch, supporting existing water-safety practice [30]. No claim is made about water quality.
- **SDG 6.4** (water-use efficiency): stop when exchange is verified instead of after a fixed time [30].
- UAE Water Security Strategy 2036: −21 % total demand [27], with a stated aim to halve average per-capita use [28].

## 8. UAE relevance

- In hot climates, cold-water lines warm up in buildings. Proctor et al. warn that temperature stabilisation as a flushing criterion **may not work in summer in hot climates because the water never gets cold** [23].
  - VeriFlush therefore uses the **feed-vs-endpoint contrast** rather than an absolute temperature.
  - It returns Uncertain when the contrast is below 1.5 °C (S10).
- Dubai's guideline sets weekly flushing for unoccupied hotel rooms by time only [24]. VeriFlush adds the missing evidence of exchange.
- Per-capita use of about 550 L/person/day is reported (MOCCAE 2015 via the UAE Government Portal; seen in search results only, so cite as "reported").

## 9. Water-saving potential (MODELLED)

`outputs/tables/water_saving.md`, for one example 300-room hotel with weekly flushing of unoccupied rooms:

| Case | Fixed vs adaptive per outlet | Saving |
|---|---|---|
| Central | 24 L vs 3.4 L | **≈ 320 m³/yr (86 %)** |
| High | — | ≈ 1 200 m³/yr |
| Low | adaptive needs more (12.9 L vs 12 L) | 0, and the fixed policy **under-flushes** |

- Every input is ASSUMED or cited.
- The adaptive volume ignores stagnant risers, so the central and high figures are an upper range.
- **The point for judges:** a fixed time is either wasteful (short branches) or insufficient (long branches). An endpoint check tells which.

## 10. Feasibility

- Bill of materials is hobby-grade (the Rev-B rig is already being built).
- The rules run on an Arduino Uno at 1 Hz.
- Two DS18B20 probes on one 1-Wire bus convert in 750 ms at 12 bit [16].
- The physical PI-101 (0–3 bar) **cannot** resolve the 3–4 kPa signal, so pressure plausibility needs a low-range transducer. Without one, flow dropout vs blockage relies on endpoint temperature only.

## 11. Scalability

**One controller per branch** (or a shared one per riser with solenoid valves). Each flush produces:
- a verdict;
- the measured arrival volume, i.e. that branch's effective volume, as a per-branch baseline;
- water used.

**Drift in the arrival ratio over time** is a simple, explainable anomaly signal for leaks, diversions or meter drift. It is not implemented as a learning layer in this prototype.

## 12. Industry integration (BMS / IoT)

- Verdicts and CSV logs map directly to BMS points (valve command, valve feedback, flow, two temperatures, verdict code, reason) and to the flushing records required by water-safety plans [24], [25].
- Integration is not implemented. This is a design statement.

## 13. Limitations (state them plainly)

1. **Everything is simulated.** No result here is a measurement.
2. **Transport parameters are assumptions.**
   - The two-region N, β and τ are assumed. There is no opened literature value at Dean ≈ 270 with a ≈ 30 s residence time.
   - They are bracketed between straight-tube physics (radial model, 5.9 % residual at 3 volumes) and coil mixing, and must be fitted to the saline-tracer step response.
3. **Temperature cannot see the last near-wall old water.** The temperature plateau sits at a few per cent, set by wall heat gain. After it, temperature carries no information while tracer still leaves (Figure 9). Consequences in the sensitivity study:
   - with a heavier tail (β = 0.20, or slow exchange τ = 120 s), **VeriFlush false-pass rates rise to 60 % and 55 %**;
   - at 1.2 L/min, **45 %**;
   - against a 2 % truth threshold, **60 %** (two-region model);
   - Timer and meter are worse in three of these four cases. At 1.2 L/min the timer, sized for 0.6 L/min, over-flushes and has fewer false passes (17 %) than VeriFlush (45 %). VeriFlush's protection is against hydraulic and metering faults, not against a heavier laminar tail than assumed.
   - Re-run with a 5-volume target (all methods), the same four cases gave **0 VeriFlush false passes** (false failures 10/60 for β = 0.20, τ = 120 s and the 2 % threshold, 0/60 at 1.2 L/min; 53–72 % more water than the 3-volume baseline). Timer and meter still had 33–60 % and 45–60 % false passes in those cases. The volume target should be set from rig tracer data.
4. **The 5 % adequacy threshold and the 3-volume policy are assumptions**, not standards.
5. **Uncertain verdicts are frequent** by design (54 % of all runs, mostly in fault scenarios).
6. **Hardware details are partly assumed.**
   - Hobby flow sensors are unspecified below 0.3 L/min.
   - Probe lag in moving water and the loaded MG996R speed are assumed.
   - The 0–3 bar gauge is unusable for logic.
7. **The rig is small.** It is an 8 mm silicone coil, not a building branch (12–20 mm copper or PPR, bends, fixtures). Scaling needs field data.

## 14. Physical-validation plan (Rev-B rig, saline tracer)

1. **Calibrate.**
   - FT-101 K-factor with a jug and stopwatch at 0.3, 0.6 and 1.0 L/min. Log the K-factor and its low-flow error.
   - Both DS18B20 probes in a common bath: offset.
   - Probe step test in flowing water: τ.
2. **Tracer step response.**
   - Fill the branch with saline (about 1500 µS/cm), flush with feed (about 300 µS/cm) at 0.3, 0.6 and 1.0 L/min.
   - Record outlet conductivity and collected mass on the TK-103 scale at 1 Hz.
   - Fit the two-region N, β, τ and compare with the radial straight-tube prediction and with the 1/(4θ) bound.
3. **Thermal vs tracer.** Run the same flushes with the ice-pack feed and both DS18B20 probes. Check whether the temperature plateau occurs before tracer clearance, as predicted.
4. **Fault scenarios on the rig.** Run each scenario with 5 repeats, using the real fault for each:

   | Scenario | How to create it on the rig |
   |---|---|
   | S02 | R-101 clamp |
   | S03 | servo travel limited |
   | S04 | clamp shut |
   | S05 | DV-101 open |
   | S06 | wrong V_cfg in firmware |
   | S07 | wrong K-factor |
   | S08 | unplug D2 |
   | S09 | unplug TT-101 |
   | S10 | no ice packs |
   | S11 | disconnect LS-OPEN |

   - **Blind protocol:** conductivity (truth) is read only after the verdict is logged.
5. **Compare** the rig confusion matrix with the simulated one (Figure 4). Report agreement and disagreement.
6. **Pressure.** Fit a 0–10 kPa transducer if dropout and blockage discrimination is required. Otherwise, remove pressure from the rules and re-run the simulations.

## Figures for the report

See `outputs/figures/captions.md`:
- Fig 2: diversion comparison;
- Fig 3: verdict grid;
- Fig 6: transport sensitivity with laminar bound;
- Fig 9: thermal vs tracer limitation.

These are the four strongest.
