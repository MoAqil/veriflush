# Figure captions

All figures: SIMULATED or MODELLED data from the VeriFlush virtual testbed. PNG at 300 dpi and SVG in this folder.

**Figure 1: `fig01_healthy_timeseries`.** Healthy flush (S01, seed 0, two-region transport), VeriFlush controlling. (a) FT-101 reading vs true branch flow; (b) XV-101 position and LS-OPEN; (c) TT-100/TT-101 readings used by the decision engine; (d) tracer truth: old-water fraction in the outflow and remaining in the branch. Dash-dot line: valve closed with verdict 'Verified' at t = 94 s. SIMULATED.

**Figure 2: `fig02_diversion_comparison`.** Diversion after the meter (S05, seed 0): about half the metered water leaves through DV-101 before the branch. Timer-only and Flow + configured volume record completion; VeriFlush keeps flushing until the endpoint-anchored volume is reached and reports the volume mismatch as a warning. Labels: residual at stop, verdict, total water used. SIMULATED (two-region transport).

**Figure 3: `fig03_verdict_grid`.** Scenario x method outcome mix over 40 Monte-Carlo runs per cell (perturbed physical event, same seed for every method). Bar segments: share of runs in each outcome against tracer truth (5 % residual threshold); number: share of the most frequent outcome. (a) baseline two-region transport; (b) radially resolved laminar transport with molecular diffusion only (straight-tube physics, no coil mixing). SIMULATED.

**Figure 4: `fig04_confusion_matrices`.** Confusion matrices: verdict (columns) vs tracer truth (rows; adequate = residual old water <= 5 %), all Monte-Carlo runs pooled over scenarios. Red bold cell = false pass (inadequate exchange recorded as verified). Top row: two-region transport; bottom row: radial straight-tube transport. SIMULATED.

**Figure 5: `fig05_water_vs_residual`.** Water used vs residual old-water fraction at stop for every Monte-Carlo run (two-region transport). Points above the dotted 5 % line are inadequate exchanges. Residuals below 0.01 % are drawn at 0.01 %. SIMULATED.

**Figure 6: `fig06_transport_sensitivity`.** In-pipe residual old-water fraction vs pipe volumes passed at the healthy flow (0.63 L/min, Re ≈ 1670) for the transport models used. Plug flow (EPANET 2.2) clears the pipe at θ = 1; the laminar segregated bound 1/(4θ) needs θ = 5 for 5 %; molecular diffusion in a straight tube lowers the tail. Around the 3-volume policy (θ ≈ 2–4) the two-region baseline lies between straight-tube physics and coil-enhanced mixing; beyond θ ≈ 4.2 it is above the straight-tube curve (heavier tail). Coil mixing factor is ASSUMED. MODELLED.

**Figure 7: `fig07_sensitivity`.** One-at-a-time sensitivity (60 runs per case per method: scenarios S01, S02, S05, S06, S07, S10). (a) VeriFlush outcome mix for every transport, probe, truth-threshold, VeriFlush-threshold, policy, geometry and flow case. (b) false-pass rate of each method in the same cases. SIMULATED.

**Figure 8: `fig08_analytical_verification`.** Verification against exact or independent results: (a) mobile-zone tanks-in-series vs the Erlang/Poisson solution; (b) radially resolved model with zero diffusion vs the laminar segregated-flow bound 1/(4θ); (c) endpoint breakthrough in the plug-flow limit vs EPANET 2.2 (WNTR 1.5) TRACE; (d) laminar head loss vs Hagen–Poiseuille. Grey thick lines: reference; coloured thin lines: model. MODELLED.

**Figure 9: `fig09_thermal_vs_tracer`.** Thermal vs tracer signal at the outlet, healthy flow, ideal sensor (no probe lag). Temperature is shown as 1 − φ. In both models the temperature settles on a plateau of a few per cent (room heat gain through the tube wall), after which it carries no further information, while old water is still leaving in the outflow. In the radial model the silicone wall's heat capacity also makes the temperature lag the tracer before the plateau. A temperature plateau is evidence of bulk exchange, not proof that the last near-wall old water has left. MODELLED.
