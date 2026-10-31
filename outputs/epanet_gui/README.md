# EPANET 2.2 desktop app captures (MODELLED)

These are screenshots from EPA's EPANET 2.2 GUI (`epanet2w.exe`) on 31 Oct 2026. The inputs are the rig models `epanet/VeriFlush_S01_healthy.inp` and `VeriFlush_S05_diversion.inp`.

**Settings**
- Quality: TRACE FEED, where the percentage is the share of water that came from TK-101.
- Colour key: **red = fresh** and blue = old. This is the reverse of the 3D render key.
- Steps: 1 s hydraulic, quality, pattern and report steps.

| File | What it shows |
|---|---|
| `S01_healthy_map_t15s.png`, `_t30s`, `_t45s` | Healthy flush. The front is mid-coil at 15 s and near the end at 30 s. By 45 s the whole branch and TT101 are fresh. |
| `S01_healthy_TT101_graph.png` | TT101 TRACE FEED against time. The 50 % crossing is at about 0.0095 h, which is about 34 s. |
| `S05_diversion_map_t15s.png`, `_t30s`, `_t45s` | DV-101 is open and the diversion line is fresh, so about half the flow leaves before the coil. At 45 s the front is still short of TT101. |
| `S05_diversion_TT101_graph.png` | The 50 % crossing is at about 0.0145 h, which is about 52 s. |

Both crossings match `epanet/epanet_vs_python.csv`, where `epanet_t50_endpoint_s` is 34 s and 52 s.

**How to reproduce**
- The GUI shows time in h:mm, so it reads the file's 1 s steps as `0:00`. Runs then either give a single period or hang.
- Before running, open Options → Times and type `0:00:01` into the Hydraulic, Quality, Pattern and Reporting time steps. Do not save these settings back over the `.inp`.
- The time list labels every step `0:00 Hrs`. Open it, press Home, then press Down N times to reach second N.
- Images are full-window screenshots at 1389 px wide, with the Windows taskbar cropped off.
