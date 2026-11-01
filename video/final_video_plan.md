# One-minute video: final plan (presenter + digital prototype, rig runs at the end)

**Concept:** one presenter stands behind the still rig and talks. The digital prototype carries the evidence through screen cut-ins. In the last 10 s the rig runs live to show the hardware works.

**Template rules:**
- 60 s maximum, including the title and credits.
- MP4 (H.264), 1920 × 1080, 16:9, under 100 MB.
- Burned-in English subtitles (`subtitles.srt`).
- A team member on camera.
- No Khalifa University, UNESCO or UN logos.
- Only credited royalty-free music, or none.
- The key numbers match the report (37 % / 31 % / 0 %).

**Labels:**
- "SIMULATED" lower-third on every digital cut-in.
- "Physical prototype" on the live rig shot.
- Never say "measured" about 37 / 31 / 0.

| Time | On screen | Narration (about 120 words) |
|---|---|---|
| 0:00–0:05 | Title card: *Smart Verification of Water Exchange in Building Plumbing Systems*, CMAT-00196, Theme 3 | (voice over the card) "Hotel rooms and school wings sit empty for days. Before they're reused, their pipes get flushed." |
| 0:05–0:15 | **Presenter behind the still rig**, medium shot | "But a flush log only says a timer ran out. It never proves the stagnant water was actually replaced. That's the gap VeriFlush closes." |
| 0:15–0:35 | **Digital prototype cut-ins**, SIMULATED: 3D flush animation `3d/renders/S01_healthy_flush.mp4` (6 s), then the dashboard in S05 diversion with the verdict panel (8 s), then the EPANET map stills (6 s). The presenter's voice continues over them. | "VeriFlush is a digital twin and controller. It tracks flow, volume and the temperature at the end of the pipe, then decides: Verified, Failed, or Uncertain. Here, half the water escapes through a side branch. The timer says done. VeriFlush keeps going until the branch is really exchanged." |
| 0:35–0:46 | Numbers animate in: **Timer 37 % · Flow meter 31 % · VeriFlush 0 %**, SIMULATED, 520 flushes | "Across 520 simulated flushes, timers passed stale water 37 percent of the time, flow meters 31. VeriFlush: zero." |
| 0:46–0:56 | **Presenter switches the pump on**; the rig runs, water moves through the coil, the Serial Monitor counts on the laptop. Label: *Physical prototype*. | "And this is our physical prototype: the same sensors, logging live. Dubai already requires weekly flushing; VeriFlush turns that log into evidence." |
| 0:56–1:00 | End card: Team Gurt · Khalifa University · member names · music credit | "Team Gurt. Making every flush count." |

## Shooting tips
- **Setting:** tripod or a phone propped up at chest height, with the rig in front of the presenter. Move the laptop off the wet board (on a chair beside it is fine) so the "wet/dry separation" in the report is visible. Keep the home background out of frame.
- **Rig run:** fill and prime the rig before filming, close the bypass, and turn the pump on at 0:46. Hide or tape any leaking joint out of shot, but never fake a run.
- **Digital cut-ins (screen-record):**
  - Offline dashboard: open `outputs/veriflush_dashboard.html#s=4&m=VeriFlush&t=end`.
  - 3D clip: `3d/renders/S01_healthy_flush.mp4`.
  - EPANET stills: `outputs/epanet_gui/S05_diversion_map_t15s/30s/45s.png`.
  - Verdict grid: `outputs/figures/fig03_verdict_grid.png`.
- **Audio:** record the narration in one take with the phone close, or record it separately and lay it over.

## Export
1920 × 1080, 30 fps, H.264, about 8–12 Mbps. Burn in `subtitles.srt` (white on a dark box, bottom centre). Name the file `CMAT-00196_3_<Team Leader Name>_Video.mp4`.
