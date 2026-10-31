# Assumptions and equations

*VeriFlush virtual testbed, model v1.1.0.*

- Symbols are in SI units unless stated.
- Rig units are L, L/min, kPa and °C.
- Reference numbers point to [references/references.md](references/references.md).
- **ASSUMED** marks a modelling choice with no source; each one has a sensitivity case in `outputs/tables/sensitivity_by_case.csv`.
- Everything the model produces is SIMULATED. The simulation predicted the behaviour described here **under the stated assumptions**, and it **requires physical validation**.

## 1. Geometry and volumes

| Symbol | Meaning | Value |
|---|---|---|
| D | branch internal diameter | 0.008 m |
| L | branch length | 6 m (spec); 8 m (Rev-B rig as built) |
| V_pipe | ideal pipe volume | πD²L/4 = **0.3016 L** (6 m), **0.4021 L** (8 m) |
| V_up | dead volume between FT-101 and the branch inlet (manifold, meter, short tubes) | 0.040 L (ASSUMED) |
| V_fit | extra fittings volume in the branch | Monte-Carlo N(0.010, 0.005) L, ≥ 0 (ASSUMED) |

**Five volumes are kept separate in the code.** The tests check them; see `outputs/tables/validation_table.md`.

1. **True physical volume** `V_true = V_pipe + V_fit`. This is truth only (`Geometry.branch_volume_l`).
2. **Configured volume** `V_cfg`. This is what the software was told. It equals V_pipe unless a fault sets it (S06: 0.151 L).
3. **Discharged volume.** Metered: `V_dis(t) = ∫ Q_FT dt`, as seen by FT-101 with its errors. True: `∫ Q_meter dt`.
4. **Fresh volume reaching the endpoint** `∫ Q_branch (1 − f_out) dt`. This is truth only. With a diversion, Q_branch < Q_meter.
5. **Residual old-water fraction** `r(t) = (1/V_true) ∫_branch f dV`. This is truth only and is the adequacy criterion.

Volumes exchanged: `N_V = V_dis / V_cfg` (metered), and `θ = ∫Q_branch dt / V_true` (true throughput in pipe volumes).

## 2. Hydraulics (quasi-steady), [model/hydraulics.py](model/hydraulics.py)

Darcy–Weisbach with minor losses, for each path:

  h(Q) = (f(Re)·L/D + ΣK)·v²/(2g) + Δz,  with v = 4Q/(πD²) and Re = vD/ν

| Regime | Friction factor | Source |
|---|---|---|
| laminar, Re < 2000 | f = 64/Re (Hagen–Poiseuille; checked by test) | standard |
| turbulent, Re > 4000 | Blasius f = 0.316 Re^−0.25 (smooth tube) | standard |
| 2000–4000 | linear interpolation, no hysteresis | ASSUMED |

**Valve characteristic.** Ball-valve-like, `C_v ∝ x²`, so `K(x) = K_open / x⁴`. An opening of x ≤ 0.02 counts as shut (ASSUMED).

**Source curve.** The pump and bypass BV-101 are lumped and seen from the manifold:

  H = H₀ − R_s Q_total²,  with H₀ = 0.40 m and R_s = 2×10⁸ m/(m³/s)²

These two values are **ASSUMED and calibrated so the healthy branch flow is about 0.63 L/min**, the rig's nominal operating point. They are not pump data.

**Network.**
- The manifold head h_m satisfies `h_m = H₀ − R_s (Q_ref(h_m) + Q_mon(h_m))²`.
- The monitored path splits at the fault tee: `Q_meter = Q_branch + Q_div` (continuity, tested to 1e-14).
- DV-101 sits **after** FT-101, so diverted water is metered but never reaches the endpoint.

**Operating point.**
- At 0.63 L/min: v = 0.21 m/s, Re ≈ 1670, so the flow is laminar.
- Dean number De = Re·√(D/D_coil) ≈ 270 for a 0.30 m coil diameter (1670 × √(0.008/0.30)).

**Pressure.** PI-101 reads `p = ρ g h_m`, about 3–4 kPa. That is far below the resolution of the physical 0–3 bar gauge, so pressure in logic means a **virtual low-range transducer** (see [virtual_sensor_spec.md](virtual_sensor_spec.md)).

## 3. Transport

### 3.1 Why EPANET plug flow is insufficient

- EPANET 2.2 transports quality and water age by Lagrangian plug flow with no longitudinal dispersion [13], [14].
- In plug flow the branch is 100 % exchanged after exactly θ = 1.
- In laminar pipe flow the near-wall fluid moves much more slowly than the centreline (u = 2U(1 − r²/R²)), so old water lingers along the wall.
- Whether 3 volumes is enough is decided entirely by this tail, which plug flow cannot represent.
- **WNTR cross-check.** EPANET 2.2 was run through WNTR 1.5 [15] on the same branch: [model/wntr_crosscheck.py](model/wntr_crosscheck.py) and `outputs/tables/wntr_crosscheck.csv`. In the plug-flow limit it agrees with the Python model:

  | Quantity | Analytical | Python | EPANET |
  |---|---|---|---|
  | Endpoint travel time | 32.5 s | 33 s | 34 s |
  | Endpoint water age | — | 32.5 s | 32.0 s |
  | Head loss | — | 64.0 mm | 65.3 mm |

  EPANET reports at 1 s steps. Its slightly higher head loss matches its default viscosity of 1.02×10⁻⁶ m²/s versus 1.00×10⁻⁶ here.
- **EPANET-MSX 2.0** adds dispersion [14]. Its Taylor–Aris-type coefficient assumes the long-time limit t ≫ R²/D [4], [1]. Here R²/D ≈ 1.1×10⁴ s for salt, about 370 times the 29 s residence time, so that model does not apply to this branch (see 3.4).
- An MSX run through WNTR 1.5 was attempted but did not carry the initial tracer state through (the outlet read 0 from t = 0). No MSX result is reported.

### 3.2 Laminar segregated-flow bound (analytical)

**Assumptions:** Poiseuille profile, no radial mixing. Let s = 1 − r²/R². A streamline at s has travelled `2θs` pipe lengths after throughput θ. The old fraction left in the pipe is

  r(θ) = ∫₀¹ max(0, 1 − 2θs) ds = 1 − θ for θ < ½;  r(θ) = 1/(4θ) for θ ≥ ½

This is the in-pipe complement of the classical laminar step response F(θ) = 1 − 1/(4θ²) [1] (Kockmann, Eq. 8).

**Consequence.** With no radial mixing, **3 volumes leaves 1/12 = 8.3 % old water and 5 % needs 5 volumes.** This is an upper bound for a straight tube. Molecular diffusion and coil (Dean) mixing both lower it.

**Verification.** The radial model with D = 0 reproduces this bound within 0.003 (test `test_zero_diffusion_matches_laminar_bound`; Figure 8b).

### 3.3 Baseline two-region model, [model/transport.py](model/transport.py)

The branch is N equal cells. Each cell has a mobile zone (fraction 1 − β) and a near-wall slow zone (β). For any carried quantity X (old fraction f, conductivity C, temperature T, age A):

  (1 − β) dX_i/dt = (Q/V_c)(X_{i−1} − X_i) + β k (S_i − X_i)
  dS_i/dt = k (X_i − S_i)

- Wall heat loss acts on T in both zones: `dT/dt += (T_env − T)/τ_wall`.
- Age increases at `dA/dt += 1`.
- The exchange rate is `k = 1/τ`: τ = 60 s for solute, old fraction and age; τ_h = 30 s for heat.
- The upstream line is 4 tanks in series.
- Integration is explicit Euler with sub-steps: Courant ≤ 0.2 and k·h ≤ 0.1. Halving the step changes r by < 0.002 (test).

**Verification.** With β = 0, the mean old fraction in N tanks after throughput θ is the exact Erlang/Poisson result `(1/N) Σ_{k=1..N} P(Poisson(Nθ) ≤ k − 1)` (test; Figure 8a).

**Status of N, β, τ: ASSUMED.**
- No opened source gives N or the Péclet number at De ≈ 200–300 with a ≈ 30 s residence time.
- Coil data in the literature are at Re ≈ 24 and residence times of tens of minutes (Bo = 80 for a helical coil [10] via [1]). That is the Taylor regime, so not transferable.
- The literature does establish that coiling narrows the RTD relative to a straight tube [1], [11].
- The baseline is therefore bracketed rather than fitted:
  - **Upper bound:** physics with no coil mixing, i.e. the radial straight-tube model (3.4) and the segregated bound (3.2).
  - **Lower bound:** coil-enhanced mixing, i.e. the radial model with a mixing factor.
  - **Two-region parameter sweep:** N = 5 / 10 / 20; β = 0 / 0.10 / 0.20; τ = 30 / 60 / 120 s; τ_h = 10 / 30 / 60 s.
- At θ = 3 the baseline gives r ≈ 4.0 %. That lies between straight-tube physics (5.9 %) and coil mixing ×10 (0.7 %). Beyond θ ≈ 4.2 the baseline is above the straight-tube curve (`data/processed/transport_curves.csv`; Figure 6).
- **These parameters must be fitted to the saline-tracer step response on the physical rig.** That is the first physical-validation task.

### 3.4 Radially resolved laminar model (physics cross-check), [model/radial.py](model/radial.py)

- M = 20 equal-area annuli × Nz = 120 axial cells.
- Ring j carries plug flow at its Poiseuille share, `u_j = 2U(1 − s_j)` with s_j = (j + ½)/M.
- Rings exchange by radial diffusion only:

  coupling per unit ring volume: g_i = 2 D ρ_i M / (R² Δρ_i), with ρ the dimensionless radius

- Advection is first-order upwind (Courant ≤ 0.9 in the fastest ring). Radial exchange is integrated exactly per sub-step with a matrix exponential.
- **Grid convergence:** 20×120 and 40×240 differ by < 0.002 in r at θ = 3 (test).

**Diffusivities.**
- Salt: D = 1.5×10⁻⁹ m²/s (NaCl in water; order 10⁻⁹ m²/s per [1]).
- Heat: α = k/(ρc_p) = 0.598/(998·4186) ≈ 1.43×10⁻⁷ m²/s, about 100 times faster.

**Regime check.** With R²/D ≈ 10⁴ s against ≈ 30 s residence, salt transport is convective (segregated), not Taylor-dispersed [4], [1].

**Silicone wall node (per axial cell), all ASSUMED.**
- Heat capacity C_w = 40 J/(K·m), from an 8×10 mm wall with ρc_p ≈ 1.4×10⁶ J/(m³·K).
- Conduction to the outer fluid ring: G_in = 10 W/(K·m), from k ≈ 0.2 W/(m·K).
- Loss to room: G_out = (C_water + C_w)/τ_wall, which keeps the lumped tube time constant τ_wall = 875 s.

**Coil mixing (ASSUMED proxy).** `radial_mix_factor` multiplies both diffusivities to imitate Dean-vortex mixing (1 = straight tube; 10 and 100 in the sensitivity study). It is not a validated coil model.

**Key result (MODELLED).** At the healthy flow (0.63 L/min) in a straight 8 mm tube, salt residual after 3 volumes is **5.9 %** (radial) vs **8.3 %** (segregated bound) vs **4.0 %** (two-region baseline). The 3-volume / 5 % policy pair is therefore marginal for a straight tube. Section 6 explains why that matters.

## 4. Temperature

**Simple mixing model** (instantaneous, no losses):

  T_out = f_old·T_old + (1 − f_old)·T_feed

**Full model.**
- T is carried by the same transport as f, but with heat-specific exchange (two-region: τ_h; radial: α).
- Wall heat gain from the room acts with τ_wall ≈ 875 s (ASSUMED estimate for 8×10 silicone in still air).
- The radial model also includes the wall's heat capacity.
- The feed tank drifts at +0.05 °C/min (ice packs melting, ASSUMED).

**Sensor lag** (first order) for each DS18B20:

  τ dT_s/dt = T_out − T_s,  with τ_TT101 = 5 s (swept 2–10 s) and τ_TT100 = 10 s

**Normalised endpoint response** used by VeriFlush, with T₀ the pre-flush baseline mean of TT-101:

  φ(t) = (TT-101(t) − T₀) / (TT-100(t) − T₀)

**Limitation (fundamental, not a tuning issue).**
- Heat diffuses about 100 times faster than salt.
- The slow near-wall layer therefore reaches thermal equilibrium with the passing fresh water long before its old water has left.
- Wall heat gain also holds the outlet a little above feed temperature, so φ settles on a plateau below 1.
- **The endpoint temperature can show a plateau while tracer is still leaving the tail** (Figure 9).
- A temperature plateau is evidence of bulk exchange. It is not proof that the last near-wall old water has gone.
- VeriFlush therefore never stops on a temperature plateau alone. It also requires the endpoint-anchored volume count (Section 6).

## 5. Tracer truth (evaluation only)

  C_out = f_old·C_old + (1 − f_old)·C_fresh,  with C_old = 1500 µS/cm and C_fresh = 300 µS/cm (ASSUMED rig values)

- CT-101 adds 1 % noise from an independent random stream.
- Adequacy (truth): `r ≤ r_adequate`.
  - The central value is r_adequate = **5 % (ASSUMED policy threshold)**.
  - 2 % and 10 % are re-scored on the same runs: `outputs/tables/truth_threshold_rescore*.csv`.
- **The 5 % threshold and the "3 volumes" policy are assumptions.** Neither is from a standard. Both guidelines quoted in the report specify a time ("several minutes"), not a volume or residual [24], [25].

## 6. Decision methods, [model/decisions.py](model/decisions.py)

**Information each method has** (the `Known` record): `V_cfg`, `V_up,cfg`, the policy thresholds and the nominal K-factor.

**Inputs at each sample** (the `Observation` record): valve command, FT-101 pulses and flow, PI-101, TT-100, TT-101, LS-OPEN and LS-CLOSED.

### 6.1 Timer-only

- Open XV-101 at t = 2 s.
- Close after `t_run = N_target·V_cfg / Q_design`, with Q_design = 0.6 L/min, N_target = 3, so t_run = 90 s.
- Always records **Verified** ("timer elapsed").

### 6.2 Flow + configured volume

- Open, then integrate FT-101.
- **Verified** when `V_dis ≥ N_target·V_cfg`.
- **Failed** if t_max = 300 s is reached first.

### 6.3 VeriFlush

| Threshold | Value | Status |
|---|---|---|
| min_contrast | 1.5 °C | ASSUMED; swept 1.0 / 2.5 |
| φ_arrival | 0.5 | ASSUMED; swept 0.4 / 0.6 |
| φ_plateau | 0.85 | ASSUMED; swept 0.80 / 0.90 |
| plateau_hold | 10 s | ASSUMED; swept 5 / 20 |
| ratio_warn high / low | 1.4 / 0.6 | ASSUMED; high swept 1.2 / 1.6 |
| ratio_fail | 3.0 | ASSUMED; swept 2.5 / 3.5 |
| valve_confirm | 3 s | ASSUMED |
| no_flow | 0.05 L/min | ASSUMED |
| blockage_confirm | 30 s | ASSUMED |
| dropout_confirm | 10 s | ASSUMED |
| dp_draw_min | 0.15 kPa | ASSUMED |
| N_target | 3 | policy |
| t_max | 300 s | policy |

**Thresholds were set before the Monte-Carlo runs and not adjusted afterwards.** The draft values are unchanged in v1.1.

```
BASELINE   (t < 2 s): T0_101 = mean TT-101, T0_100 = mean TT-100, p0 = mean PI-101 (valid samples only)
           endpoint_ok = T0_101 and T0_100 valid ;  contrast = T0_101 - T0_100 ;  weak = |contrast| < min_contrast
OPEN XV-101 at t = 2 s ; each 1 s sample:
  V   += Q_FT * dt                                              (metered volume)
  valve_state at t = 5 s:  LS-OPEN & !LS-CLOSED -> confirmed ; LS-CLOSED -> not_open ; else pending
           pending & >= 5 flow samples: mean Q < 0.8 Q_design -> partial (warn) else switch_fault (warn)
  endpoint invalid if TT-101 in {NaN, -127, 85} or outside -10..60 degC ;
           frozen if TT-101 unchanged >= 15 samples while V > 1.5 (V_cfg + V_up,cfg) and no arrival yet
  phi = (TT-101 - T0_101) / (TT-100 - T0_101)
  ARRIVAL  first phi >= phi_arrival:  V_arr = V
           V_est = max(V_arr - V_up,cfg, 0.2 V_cfg)                (endpoint-anchored branch volume, metered litres)
           ratio = V_est / V_cfg ; ratio > 1.4 or < 0.6 -> warning (diversion / meter bias / wrong V_cfg)
  N_eff = V / V_est                                             (volumes exchanged, anchored at the endpoint)
  plateau_s counts consecutive seconds with phi >= phi_plateau
  dropout  if flow seen before, Q_FT ~ 0 for >= 10 s and (p0 - p) > dp_draw_min   (branch still drawing)
DECISIONS (first match closes XV-101):
  1 FAILED     valve not_open and no flow for 10 s
  2 no flow ever for 30 s:  pressure drawn -> UNCERTAIN (flow-sensor fault) ; else FAILED (blockage)
  3 FAILED     ratio > ratio_fail   or   V > ratio_fail (V_cfg + V_up,cfg) with no arrival (water not reaching endpoint)
  4 endpoint usable & arrived & no dropout & N_eff >= N_target & plateau_s >= plateau_hold:
               valve confirmed -> VERIFIED ; else UNCERTAIN (valve feedback inconsistent)
  5 endpoint unusable (weak / invalid / frozen) & V >= N_target V_cfg -> UNCERTAIN (never Verified without endpoint)
  6 dropout & endpoint usable & plateau & estimated volume >= N_target V_cfg -> UNCERTAIN (volume only estimated)
  7 t >= t_max: endpoint unusable or dropout -> UNCERTAIN ; no arrival -> FAILED ; else FAILED (too few volumes)
```

**Why endpoint anchoring works.**
- Diversion, a meter over-reading and a configured volume that is too small all inflate the metered volume needed for fresh water to arrive.
- Using V_est instead of V_cfg as the exchange unit makes the stop rule self-correcting for those faults.
- The ratio exposes them as warnings or failures.
- It does **not** correct for the laminar tail (Section 3). That is a property of the pipe, not of the meter.

## 7. Monte Carlo and evaluation

- Each scenario × seed defines one physical event, using `perturbed()` with seed 1000 + s.
- The perturbations are:
  - T_old ~ N(24, 1) °C;
  - feed contrast ~ N(11, 1.5) °C (weak-contrast scenario: N(0.6, 0.2));
  - H₀ ±8 %;
  - meter K-loss ±15 %;
  - fittings volume.
- All three methods see the same event and the same sensor-noise seed. They differ only in when they close the valve.
- **Outcomes against truth:**
  - Verified & adequate = true pass; Verified & inadequate = **false pass**;
  - Failed & inadequate = true failure; Failed & adequate = false failure;
  - Uncertain is counted separately.
- **Fault-detection rate** = share of runs in fault scenarios where the method gave a non-Verified verdict or a warning.

## 8. Sources of the default parameters

Default parameters and their sources (datasheets [16]–[22], or ASSUMED) are listed in [virtual_sensor_spec.md](virtual_sensor_spec.md) and in comments in [model/params.py](model/params.py).
