# VeriFlush: digital prototype

VeriFlush is a virtual testbed for checking whether flushing a low-use plumbing branch really exchanged the water at the endpoint. It is a Python simulation of the Rev-B rig design (6 m × 8 mm spec branch by default; the 8 m as-built branch is a sensitivity case) and includes:

- the hydraulics, laminar transport, temperature and tracer truth of the rig;
- virtual sensors and the 12 fault scenarios;
- three verification methods: timer-only, flow + configured volume, and VeriFlush;
- **EPANET 2.2 models of the rig** (`epanet/*.inp`, open in the EPA desktop app), matching the Python hydraulics within 0.6 %;
- **the real Arduino firmware**, compiled on the host and replay-tested against the Python engine (13/13 identical verdicts), plus a **Wokwi** virtual-circuit project (`wokwi/`);
- **a Blender 3D model of the rig** (`3d/`) whose coil water colour, valve and outlet tank are animated from the simulation data;
- report figures and tables; a Streamlit / offline HTML viewer for the data.

**All outputs are SIMULATED.** VeriFlush verifies hydraulic exchange only; it makes no health or potability claim.

Built for the Khalifa University–UNESCO Global Water Hackathon 2026, Theme 3 (Team Gurt).

## Setup

Python 3.11–3.12 is recommended (tested with 3.12.4). Use a virtual environment.

**Windows (PowerShell):**

```bash
py -3.12 -m venv $HOME\.venvs\veriflush
```

```bash
$HOME\.venvs\veriflush\Scripts\python -m pip install -r requirements.txt
```

> On Windows, keep the venv at a **short path** such as the one above. Inside a deeply nested folder, Pillow's DLL fails to load because of the 260-character path limit.

**macOS / Linux:**

```bash
python3 -m venv ~/.venvs/veriflush && ~/.venvs/veriflush/bin/pip install -r requirements.txt
```

Commands below use `python` for the venv's interpreter.

## Run

| What | Command |
|---|---|
| Tests (42) | `python -m pytest tests -q` |
| Everything (tests → validation table, experiments, water saving, figures, offline dashboard, screenshots) | `python run_all.py` (about 7 min; `--quick` for a smoke run) |
| Experiments only | `python run_experiments.py` (`--quick` for 8 seeds) |
| Figures only | `python make_figures.py` |
| Interactive dashboard | `streamlit run dashboard/app.py` |
| Offline dashboard (no server, data embedded) | `python dashboard/export_html.py`, then open `outputs/veriflush_dashboard.html` |
| Screenshots of every scenario | `python dashboard/screenshots.py` (uses an installed Edge or Chrome, headless) |
| EPANET rig models + comparison | `python epanet/build_epanet.py`, then open `epanet/VeriFlush_S01_healthy.inp` in EPANET 2.2 |
| Firmware replay test (needs g++) | `python firmware/hil/run_replay.py` |
| 3D model, stills, animation | `blender -b -P 3d/build_rig.py -- --stills` and `-- --anim` (Blender 5.1) |

**Offline dashboard deep links.** Append `#s=<0-12>&m=VeriFlush&t=end`. Also accepted:
- `m=Timer-only`;
- `m=Flow + configured volume`;
- `b=radial`;
- `play=1`;
- `speed=15`.

## Layout

```
model/          params, hydraulics, transport (two-region), radial (laminar cross-check),
                sensors (Observation vs Truth), decisions (3 methods), simulate, wntr_crosscheck
scenarios/      S01-S12 (+ S09a/S09b) and Monte-Carlo perturbation
dashboard/      app.py (Streamlit), template.html (player), payload.py, export_html.py, screenshots.py
tests/          test_model.py (28 from the draft), test_extended.py (12 new)
firmware/       veriflush/veriflush.ino (Arduino), logger.py (pyserial), hil/ (host compile + replay test)
epanet/        rig as EPANET 2.2 .inp files (5 scenarios) + build/compare script
wokwi/         Wokwi project: sketch, diagram, rig-emulator custom chip
3d/            Blender build script, renders/, veriflush_rig.blend, assets/ (CC0 HDRI)
data/raw/       seed-0 time series per scenario x method x transport model (CSV, 'data_status' column)
data/processed/ Monte-Carlo, sensitivity, transport curves, WNTR curves
outputs/        figures/ (PNG 300 dpi + SVG + captions.md), tables/, screenshots/, veriflush_dashboard.html
references/     references.md (IEEE, with check status), research_notes.md (evidence per source)
report_assets/  report_evidence.md      video/  one_minute_script.md
```

Documents:
- [assumptions_and_equations.md](assumptions_and_equations.md)
- [virtual_sensor_spec.md](virtual_sensor_spec.md)
- [software_comparison.md](software_comparison.md)
- [STATUS.md](STATUS.md)

## What works / what is unverified

See [STATUS.md](STATUS.md). In short:
- **Works and tested:** the simulation, the 3 methods, the scenarios, all 42 tests, the WNTR cross-check, both dashboards (browser-checked) and the figures.
- **Unverified:** every number against a physical rig; the transport parameters (assumed, bracketed); the firmware on a real Uno and in Wokwi (host-compiled and replay-tested only); the UAE per-capita figure (reported only).
