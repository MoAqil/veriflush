# One-minute video: storyboard and voice-over

**Sources (in order of screen time):**
- `3d/renders/S01_healthy_flush.mp4`: Blender model of the rig, coil water colour driven by the simulation;
- the EPANET 2.2 desktop app with `epanet/VeriFlush_S05_diversion.inp`: captured stills are in `outputs/epanet_gui/` (`S05_diversion_map_t15s/30s/45s.png`, `S05_diversion_TT101_graph.png`); Figure 10 is the fallback;
- Wokwi running the real firmware (see `wokwi/README.md`);
- Figure 3 (verdict grid).

The web dashboard is **not** used as a hero shot.

**Mandatory labelling.** Every simulation shot carries a small lower-third "SIMULATED", added in the editor (CapCut, DaVinci Resolve or Clipchamp). The 3D colour key is stated once: "amber = old water, blue = fresh (tracer truth)".

**Voice-over:** about 150 words, calm.

| Time | Shot | On screen | Voice-over |
|---|---|---|---|
| 0:00–0:08 | 3D wide shot, frame 1 (`S01_healthy_wide_t0.png`), slow push-in | Rig at rest; coil amber = stagnant water | "Hotel rooms, hospital wings, schools after the holidays: their pipes sit still for days. Before they're used again, they get flushed." |
| 0:08–0:16 | EPANET GUI stills `S05_diversion_map_t15s` → `t30s` → `t45s` (crossfade, about 2.5 s each), then `S05_diversion_TT101_graph` | Fresh front in EPANET; DV-101 open, endpoint still old at 45 s. Note: in EPANET, **red = fresh** (100 % feed) and blue = old, which is the opposite of the 3D key, so add a small "red = fresh" tag | "Today the record says 'done' because a timer ran out, or a meter counted enough litres. Here half the water leaves before the branch, and the timer still says verified." |
| 0:16–0:32 | 3D animation, `S01_healthy_flush.mp4` (17 s, play at 1×) | Blue front climbs the coil; old water collects amber in TK-103; servo closes XV-101 | "VeriFlush watches the end of the pipe. When the endpoint temperature swings toward the feed temperature, it knows fresh water has arrived, and how many litres that took. Then it keeps flushing until enough of the branch has been exchanged, and closes the valve itself." |
| 0:32–0:44 | Wokwi screen recording: press START, drag TT-101 to 13 °C, serial shows `VERDICT,Verified`; flip the TT-101 switch: `Uncertain` | Real firmware on a virtual Arduino | "This is the actual controller code running on a simulated Arduino. Unplug the endpoint sensor and it says Uncertain, never Verified." |
| 0:44–0:54 | Figure 3 (verdict grid) | Red false passes for timer and meter; none for VeriFlush | "Across 520 simulated flushes, timers wrongly passed 37 %, meters 31 %, VeriFlush none. And it tells us where it is still blind: the last old water near the pipe wall." |
| 0:54–1:00 | Closing card over `S01_healthy_coil_t22.png` | "VeriFlush: evidence that the water was actually exchanged. Simulated; physical validation on the Rev-B rig next. Team Gurt · Khalifa University" | "VeriFlush: evidence that the water really changed. Next, we prove it on the rig." |

## Wording rules for the voice-over

- Say "simulated", never "measured". Make no health claims: say "exchange", never "safe", "clean" or "Legionella-free".
- Every figure quoted must match `outputs/tables/method_comparison_overall.csv`:
  - 194/520 is 37 %;
  - 160/520 is 31 %;
  - 0/520 VeriFlush false passes.

## Notes on capture

- The 3D shots are rendered by Blender (`blender -b -P 3d/build_rig.py -- --anim`), 1280×720 at 24 fps, where 1 simulated second is 4 frames.
- Record Wokwi and the EPANET app with OBS or the Windows Game Bar.
- The web dashboard is only a data viewer; leave it out of the video.
