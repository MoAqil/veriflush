# Water-saving estimate (MODELLED)

Fixed-duration weekly flushing of unoccupied guest-room outlets vs an adaptive stop at the required number of pipe volumes, verified at the endpoint. One example 300-room hotel. Not a measured saving.

## Inputs

| input | low saving | central | high saving | unit | source |
|---|---|---|---|---|---|
| rooms | 300 | 300 | 300 | rooms | ASSUMED example: one 300-room hotel |
| unoccupied_fraction | 0.15 | 0.25 | 0.35 | - | ASSUMED share of rooms unoccupied >= 7 days in a given week |
| outlets_per_room | 3 | 4 | 5 | outlets | ASSUMED (basin, shower, bath, bidet spray / kitchenette) |
| fixed_flush_min | 2.0 | 3.0 | 5.0 | min | ASSUMED reading of 'several minutes' weekly [DM-HSD-GU44 v6 s.12-1; HSG274-2 para 2.78] |
| outlet_flow_lpm | 6.0 | 8.0 | 9.0 | L/min | ASSUMED low-flow fixture flows (UAE green-code limits NOT VERIFIED) |
| branch_length_m | 12.0 | 6.0 | 3.0 | m | ASSUMED riser-to-outlet run in a guest room |
| branch_id_mm | 16.0 | 15.0 | 13.0 | mm | ASSUMED 1/2-inch class pipe internal diameter |
| volumes_needed | 5.0 | 3.0 | 3.0 | pipe volumes | policy: 3 volumes; low case uses 5 = laminar 1/(4 theta) <= 5 % bound (this work) |
| adaptive overhead factor | 1.065 | 1.065 | 1.065 | - | SIMULATED: median VeriFlush water used / (3 x branch volume), S01 Monte Carlo |

## Results

| case | branch volume (L) | fixed per outlet (L) | adaptive per outlet (L) | fixed (m³/yr) | adaptive (m³/yr) | saving (m³/yr) | saving (%) |
|---|---|---|---|---|---|---|---|
| low saving | 2.413 | 12.0 | 12.85 | 84.2 | 90.2 | 0.0 | 0.0 |
| central | 1.06 | 24.0 | 3.39 | 374.4 | 52.8 | 321.6 | 85.9 |
| high saving | 0.398 | 45.0 | 1.27 | 1228.5 | 34.7 | 1193.8 | 97.2 |

## Reading the numbers

- The saving comes from stopping when the branch has been exchanged instead of running a fixed time. If a branch is long or the flow is low, the adaptive stop can need **more** water than the fixed time; the column `fixed_time_sufficient` in the CSV flags that case (the fixed policy would then under-flush).
- The adaptive volume assumes the endpoint verification works on that outlet. Where VeriFlush returns Uncertain (for example weak temperature contrast in summer, Proctor et al. 2020), the outlet falls back to the fixed policy and saves nothing.
- Person-days equivalent uses about 550 L/person/day for the UAE (MOCCAE 2015 as reported by the UAE Government Portal; seen in search results only, treat as indicative).
- The adaptive volume counts only the outlet branch. If the riser or floor main is also stagnant (whole floor unoccupied), fresh water must first reach the branch inlet and the adaptive volume grows; the large percentage savings in the central and high cases then shrink. Treat them as an upper range.
- The central case uses the 3-volume policy. The simulation shows 3 volumes can leave more than 5 % old water when the laminar tail is heavy (assumptions_and_equations.md, Section 3); the low case uses 5 volumes.
- Requires physical validation: real branch volumes, fixture flows and occupancy patterns must be measured in the target building.
