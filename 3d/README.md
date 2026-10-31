# VeriFlush rig: 3D model (Blender 5.1)

**What this is:** a 3D model of the **planned Rev-B assembly**, built from the parts the team has bought. The rig has **not been assembled yet**, so the layout is a design proposal, not a photograph of a real build.

**How the animation works:**
- The water colour in the coil is driven by the simulation (`data/raw/S01_healthy__veriflush__seed0.csv`, SIMULATED): **amber = old water, blue = fresh** (tracer truth).
- The XV-101 lever and servo horn, and the TK-103 water level, are also driven by the simulation.
- 1 simulated second = 4 frames at 24 fps.

**Rebuild:**
- `blender -b -P 3d/build_rig.py -- --stills`, or `-- --anim` for the animation.
- Add `--labels` for tag labels.
- Output goes to `3d/renders/` and `3d/veriflush_rig.blend`.

All geometry is modelled parametrically in `build_rig.py`; no third-party meshes are used. Lighting uses the Poly Haven "Studio Small 09" HDRI (CC0) in `assets/`.

## Parts: model vs purchased item (`reference_photos/`)

| Rig tag | Modelled as | Purchased item it follows |
|---|---|---|
| P-101 | black rectangular 12 V DC pump, side inlet, top outlet barb, red/black leads | small DC water pump (photo) |
| PI-101 | 40 mm gauge with black case and 0–3 bar dial (green / yellow / red bands); needle at ≈ 0 because the rig runs at a few kPa | MK 0–3 bar / 0–45 psi gauge |
| — | zinc ¼"–8 mm hose-barb adapter and worm-drive hose clamp under the gauge | AEP1053 hose-barb connector kit |
| Y manifold, gauge tee, TT-101 tee | barbed brass Y and T fittings | brass Y / T 8 mm barbs |
| HV-101, HV-201, BV-101, XV-101 | white push-fit ball valves with blue collet clips and blue lever | push-fit ball valves |
| DV-101 | white push-fit **tee** valve | push-fit tee valve |
| FT-101 | white YF-S401-type flow sensor (round body, 3 screws, side barbs, red/black/yellow leads) | water flow sensor |
| TT-100, TT-101 | 6 × 50 mm stainless DS18B20 probes on black cable | DS18B20 waterproof probes |
| XV-101 actuator | MG996R (black, brown/red/orange lead) coupled to the valve stem | MG996R digital servo |
| LS-OPEN / LS-CLOSED | ANDELI V-153 lever microswitches | ANDELI V-153-1C25 microswitches |
| Controller | blue Uno (CH340 clone), red screw shield with green terminal blocks | Uno clone + Screw Shield 1.0 |
| Buck converter | XL4015 module: toroid, two 220 µF capacitors, blue trimpot, heatsink | XL4015 |
| Enclosure | white IP65 box, 150 × 110 × 70 mm, with cable glands; lid set aside | Xider IP65 150 × 110 × 70 |
| Power | rocker switch on the box, inline blade-fuse holder, 12 V brick | rocker switch, fuse holders, 12 V adapter |
| Tubing | clear 8 mm ID tube; the coil is held to the former with black nylon cable ties | clear tubing, 3.6 × 300 mm cable ties |

## Assumed (not in the photos, or not yet decided)

- **Tanks and supports:**
  - TK-101 feed tank, TK-102 and TK-103: clear acrylic boxes;
  - the kitchen scale under TK-103;
  - the coil former (a dark drum, 0.29 m diameter);
  - the acrylic backing board for XV-101.
- **Pump position:** inline on the bench beside the tank. If it is used as a submersible pump inside TK-101, move it in `build_rig.py`.
- **Layout:** the positions and routing of all parts.
- **Not modelled:** the breadboard, jumper wires, resistors, capacitors and heat-shrink. These are inside or under the build, or not visible.

Once the rig is assembled, take one photo per side. The layout can then be matched in `build_rig.py`; all positions are plain coordinates in metres.
