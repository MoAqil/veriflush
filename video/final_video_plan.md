# One-minute video: final plan (template storyboard)

**Hard rules from the template:**
- 60 s maximum, including the title and credits.
- MP4 (H.264), 1920 × 1080, 16:9, under 100 MB.
- Burned-in English subtitles (use `subtitles.srt`).
- A team member appears on camera or narrates.
- No Khalifa University, UNESCO or UN logos.
- Only royalty-free music, credited at the end.
- Everyone shown has consented.
- The title and key numbers match the report (37 % / 31 % / 0 %).

**Labelling:**
- Any simulation, 3D or dashboard shot gets a small "SIMULATED" lower-third.
- Real rig footage is labelled "Physical prototype".
- Never say "measured" about a simulated number.

| Time | Segment | Shot | Narration (about 135 words total) |
|---|---|---|---|
| 0:00–0:05 | Title and hook | Title card: *Smart Verification of Water Exchange in Building Plumbing Systems*, CMAT-00196, Theme 3. Fade to the rig, wide. | "Hotel rooms and school wings sit unused for days. Before they're used again, their pipes get flushed." |
| 0:05–0:15 | Problem | A team member on camera beside the rig, or 3D still `S01_healthy_wide_t0.png` with old water shown amber | "But the record only says a timer ran out. It never shows whether the stagnant water in that branch was actually replaced." |
| 0:15–0:35 | Solution | (a) Rig running (dry side, no visible leaks), 4 s. (b) Close-up of the flow sensor plus the Arduino serial monitor counting, 4 s. (c) 3D flush animation `S01_healthy_flush.mp4`, 6 s, SIMULATED. (d) Dashboard verdict panel, 6 s, SIMULATED. | "This is our physical prototype. A flow sensor counts every litre into the branch. In our digital twin, a probe at the end of the pipe shows when fresh water arrives, and the controller decides: Verified, Failed, or Uncertain. It never passes a flush it can't prove." |
| 0:35–0:48 | Evidence | Figure 3 verdict grid, or the EPANET GUI stills `outputs/epanet_gui/S05_diversion_map_t*.png`, SIMULATED | "Across 520 simulated flushes, a fixed timer passed stale water 37 percent of the time, a flow meter 31 percent. VeriFlush: zero. When a sensor failed, it said Uncertain instead of guessing." |
| 0:48–0:56 | Impact and scale | A team member on camera, or the Table 7 targets graphic | "Dubai already requires weekly flushing of empty hotel rooms. VeriFlush turns that log into evidence, supporting SDG 6.4. Next: a pilot with a facility-management partner." |
| 0:56–1:00 | Close | Card: Team Gurt · Khalifa University · member names · music credit | "Team Gurt. Making every flush count." |

## Filming the rig with leaks

- Film only the dry side, or film after a fix. Don't show water near the electronics, and don't fake a run.
- The flow-sensor and serial-monitor shot proves the prototype works without the whole rig running.
- If the rig isn't ready in time, use 0:15–0:20 for a slow pan over the assembled rig with the pump off, and keep the rest of the segment SIMULATED.

## Edit settings (CapCut, DaVinci or Clipchamp)

- Export: 1920 × 1080, 30 fps, H.264, about 12 Mbps (roughly 90 MB for 60 s is the ceiling; aim for 40–60 MB).
- Import `subtitles.srt` and burn it in: white text on a dark box, bottom centre, about 42 px.
- File name: `CMAT-00196_3_<Team Leader Name>_Video.mp4`.
