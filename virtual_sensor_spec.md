# Virtual sensor specification

*VeriFlush virtual testbed, model v1.1.0. Every value below is a modelling input. "Source" is a datasheet or paper that has been opened (numbers in brackets refer to [references/references.md](references/references.md)), or **ASSUMED**. Code: [model/sensors.py](model/sensors.py) and [model/params.py](model/params.py) (`SensorSpec`).*

**Decision input?** says whether a decision engine can read the signal. Truth signals live in the `Truth` record. That record is never passed to a controller, and two tests enforce this: `test_truth_not_visible_to_methods` and `test_decision_module_never_touches_truth`.

## Summary

| Tag | Quantity | Unit | Sample rate | Resolution | Accuracy / noise | Bias | Delay / dynamics | Failure states | Range | Decision input? |
|---|---|---|---|---|---|---|---|---|---|---|
| **FT-101** | flow (pulses) | pulses per 1 s window, converted to L/min | 1 Hz (pulse count per `dt_s`) | 1 pulse = 1/5880 L ≈ 0.17 mL | ±1 pulse window jitter; unit K-factor error 3 % (1σ) | `flow_bias` multiplier (fault S07: ×1.40) | none (count per window) | dropout to 0 pulses (S08); under-reads linearly below 0.30 L/min; 0 below 0.10 L/min | 0.3–6 L/min specified [20], [21] | **yes** |
| **TT-100** | feed temperature | °C | 1 Hz | 0.0625 °C (12-bit) [16] | noise 0.03 °C (1σ, ASSUMED) | per-unit bias N(0, 0.15 °C), clipped to ±0.5 °C [16] | first-order lag τ = 10 s (ASSUMED, tank) | −127 if disconnected (DallasTemperature library constant [17]) | −55…+125 °C; ±0.5 °C only for −10…+85 °C [16] | **yes** |
| **TT-101** | endpoint temperature | °C | 1 Hz | 0.0625 °C | noise 0.03 °C (1σ, ASSUMED) | as TT-100 | first-order lag τ = 5 s (still-water test gave 6.2–6.9 s [18]; moving water ASSUMED faster; swept 2–10 s) | frozen value (S09a), −127 disconnected (S09b), 85 °C power-on value rejected [16] | as TT-100 | **yes** |
| **PI-101 (virtual)** | manifold gauge pressure | kPa | 1 Hz | 0.01 kPa | noise 0.05 kPa (1σ) | none | none | none modelled | 0–10 kPa | **yes** (dropout and blockage plausibility only) |
| **LS-OPEN** | XV-101 open limit switch | 0/1 | 1 Hz | binary | — | — | asserts at ≥ 95 % travel | wire broken: never asserts (S11) | — | **yes** |
| **LS-CLOSED** | XV-101 closed limit switch | 0/1 | 1 Hz | binary | — | — | asserts at ≤ 5 % travel | — | — | **yes** |
| **XV-101 cmd** | valve command | 0/1 | 1 Hz | binary | — | — | — | — | — | **yes** (the controller's own output) |
| XV-101 position | true valve travel | 0–1 | 1 Hz | continuous | — | — | slew 2.0 travel/s, i.e. 90° in 0.5 s (ASSUMED loaded; unloaded spec 0.14 s/60° at 6 V [22]) | stuck partly open (S03), stuck closed | 0–1 | no: **TRUTH** |
| CT-101 | endpoint conductivity (saline tracer) | µS/cm | 1 Hz | continuous | 1 % multiplicative noise, independent RNG stream | none | none | none | 300–1500 µS/cm in use | no: **TRUTH** |
| f_old | old-water fraction in outflow / in branch | – | 1 Hz | continuous | exact (model state) | — | — | — | 0–1 | no: **TRUTH** |
| Q_branch, Q_div | true branch and diverted flow | L/min | 1 Hz | continuous | exact | — | — | — | — | no: **TRUTH** |

## Notes per sensor

### FT-101: Hall-effect turbine flow sensor (YF-S401 class)

- The K-factor of 5880 pulses/L (≈ 98 Hz per L/min) is the vendor figure [20], [21]. One vendor page lists an inconsistent `F = 43·Q` and is ignored. The rig must calibrate K with a measuring jug.
- The specified range is 0.3–6 L/min, with ±5 % [20] or ±10 % [21] accuracy. **No source documents behaviour below 0.3 L/min.** The linear under-reading between 0.10 and 0.30 L/min and the stall below 0.10 L/min are **ASSUMED**.
- Consequence: the restricted-flow scenario S02 (about 0.27 L/min) sits at the bottom of the specified range. The meter under-reads there, so Flow + configured volume often times out and reports Failed even when exchange was adequate. Those runs are false failures.
- Pulses are counted per 1 s window. The fractional carry and ±1 count jitter reproduce counting quantisation.

### TT-100 / TT-101: DS18B20 on a shared 1-Wire bus (D4, 4.7 kΩ pull-up)

- Datasheet [16]:
  - ±0.5 °C accuracy from −10 to +85 °C;
  - 12-bit resolution, 0.0625 °C;
  - 750 ms conversion at 12 bit, so 1 Hz logging is feasible for two sensors on one bus;
  - +85 °C is the power-on reset value.
- −127 °C is `DEVICE_DISCONNECTED_C` in the DallasTemperature library [17], not a datasheet value. VeriFlush treats −127 °C, 85 °C, NaN and anything outside −10…60 °C as invalid.
- **Probe lag.** A stainless-sheathed waterproof probe measured 6.2 s (heating) and 6.9 s (cooling) in still water [18]. The default endpoint lag is 5 s in moving water (ASSUMED) and the sensitivity study covers 2 and 10 s.
- **Bias.** Each probe gets its own bias, drawn once per run. VeriFlush works on the *contrast* TT-101 − TT-100 measured at baseline. Biases therefore mostly cancel in φ, but they still add to the contrast check.
- **Frozen reading (S09a).** This is detected as no change for ≥ 15 samples while the metered volume exceeds 1.5 × the expected arrival volume.

### PI-101: pressure

- **The physical PI-101 is a 0–3 bar mechanical gauge.** This rig works at about 3–4 kPa at the manifold (0.03–0.04 bar), roughly 1 % of that gauge's full scale. **The gauge cannot resolve the signal VeriFlush uses.**
- Any pressure signal used in logic is therefore a **virtual low-range transducer** (0–10 kPa, 0.01 kPa resolution, 0.05 kPa noise). It stands for a part the rig does not yet have, for example a 0–10 kPa differential or gauge transducer read by the Arduino ADC.
- VeriFlush uses pressure only as a plausibility input:
  - distinguishing a flow-sensor dropout (pressure still drawn) from a blockage (no pressure drop);
  - confirming that the branch is drawing water.
- **Without a low-range transducer:**
  - dropout (S08) becomes indistinguishable from blockage in the first seconds;
  - S04/S08 would rely on the endpoint temperature alone.
- Requires physical validation once a transducer is fitted.

### XV-101 + LS-OPEN / LS-CLOSED

- MG996R speed:
  - spec sheet: 0.17 s/60° at 4.8 V and 0.14 s/60° at 6 V [22];
  - retailers: 0.19 and 0.15 s;
  - with the push-fit ball valve's breakaway torque, a 0.5 s quarter-turn is ASSUMED.
- The servo runs from 6 V via the XL4015 buck converter.
- The switches are microswitches on D5/D6 with INPUT_PULLUP: a pressed switch reads LOW, and the model reports 1 for "made".

### CT-101: tracer truth

- This is a conductivity probe in the outlet line, read **only after the verdict**. In the code it is part of `Truth`, computed from the transport state with its own random stream (seed + 10 000). Changing it therefore cannot alter any decision random draw.
