# VeriFlush in Wokwi (virtual Arduino)

This folder runs the **real VeriFlush firmware** on a simulated Arduino Uno R3. The board is wired like the Rev-B rig:

| Rig part | Wokwi part | Arduino pin |
|---|---|---|
| TT-100 feed probe | DS18B20 | D4 (1-Wire, 4.7 kΩ pull-up) |
| TT-101 endpoint probe | DS18B20, wired through an "unplug" slide switch | D4 |
| XV-101 valve | MG996R-style servo | D9 |
| START button | pushbutton | D7 |

The rest of the rig is played by a **custom chip, `rig-emulator`**:
- it reads the servo signal and moves a virtual ball valve;
- it drives LS-OPEN (D5) and LS-CLOSED (D6);
- it sends FT-101 flow pulses (D2) at 5880 pulses per litre.

All data in Wokwi are SIMULATED.

| File | What it is |
|---|---|
| `sketch.ino` | copy of `../firmware/veriflush/veriflush.ino`; keep them identical |
| `diagram.json` | parts and wiring |
| `libraries.txt` | OneWire, DallasTemperature, Servo |
| `rig-emulator.chip.json` / `.chip.c` | the rig-emulator chip: pins and sliders, and its C code (Wokwi Chips API) |

## Load it (about 3 minutes)

1. Go to https://wokwi.com and start a new **Arduino Uno** project. Signing in lets you save it.
2. Replace the contents of `sketch.ino` and `diagram.json` with the files from this folder.
3. Click the tab menu (▾), choose **New file…**, create `libraries.txt` and paste the three library names.
4. Tab menu, then **New file…** again: create `rig-emulator.chip.json`, then `rig-emulator.chip.c`, and paste both. The diagram already uses the part type `chip-rig-emulator`.
5. Press ▶. The serial monitor prints both temperatures, then `VeriFlush Rev-B ready`.
   - If TT-100 shows 24 °C and TT-101 shows 13 °C, the sensor order is swapped. Swap `TT100_INDEX` and `TT101_INDEX` at the top of the sketch.

## Demo script

1. **Healthy flush.**
   - Press **START**. The servo turns, LS-OPEN closes and CSV lines stream (`t_s, cmd, pulses, q_lpm, v_l, …`).
   - After about 30 s (fresh water reaching the endpoint), click TT-101 and drag its temperature from 24 °C to 13 °C.
   - About 60 s later: `VERDICT,Verified,…`.
2. **Diversion or wrong meter.** Set the chip's *FT-101 bias* to 1.9, or wait until about 0.6 L has been metered before cooling TT-101. You get `WARN … branch volume estimate high`, and Failed above 3×.
3. **Dead endpoint sensor.** Flip the TT-101 slide switch mid-flush: −127 °C, then **Uncertain**.
4. **Weak contrast.** Set TT-100 to 23.5 °C before START. The verdict is **Uncertain** and never Verified.
5. **Blockage.** Set *Branch flow* to 0. After 30 s: **Failed**.
6. **Partial valve.** Set *XV-101 jams at* 0.35. LS-OPEN never closes, so you get a "partly open" warning, and the verdict is never Verified.
7. **Broken limit switch.** Set *LS-OPEN wire broken* to 1. You get a switch-fault warning and **Uncertain**.

Pressure plausibility is off in this build (`VF_HAVE_PRESSURE 0`), as on the rig without a low-range transducer. A flow-sensor dropout therefore ends as Uncertain or Failed through the endpoint and time rules, not through pressure.

## What was verified, and what was not

- **Verified here.**
  - The firmware compiles with g++ 16 (`-Wall`) against small stand-ins for Arduino, OneWire, DallasTemperature and Servo (`../firmware/hil/`).
  - Fed the Python simulation's sensor traces for all 13 scenarios, it reached **the same verdict at the same second with the same metered volume as the Python engine in 13/13** (`outputs/tables/firmware_vs_python.csv`; test `test_firmware_matches_python_engine`).
- **Loaded into Wokwi (31 Oct 2026, built-in browser).** All five files load and the circuit renders: Uno, two DS18B20s, START button, servo and the rig-emulator chip.
  - The first Wokwi compile found a real bug the host build could not: the Arduino IDE inserts auto-generated function prototypes **above** the `Verdict` enum, so `finish(Verdict, …)` did not compile for the Uno.
  - Fixed by taking `int` instead. The host replay still matches 13/13.
  - Later compiles failed with "Failed to fetch": the build requests to wokwi.com timed out on the network (QUIC idle timeout). So the fixed sketch and the custom chip have **not yet completed a Wokwi build or run**.
- **Not verified here.**
  - Wokwi itself: wokwi.com could not be opened from the build session, so the diagram and the custom chip have **not been run in Wokwi yet**.
  - The AVR compile for the real Uno. Check both on the first load.
  - The chip's flow-vs-opening curve, an approximation of the Python valve model.
