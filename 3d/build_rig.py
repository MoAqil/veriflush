"""Blender model of the VeriFlush Rev-B rig, animated from the simulation.

    blender -b -P 3d/build_rig.py -- [--scenario S01_healthy] [--stills] [--anim] [--samples 128]

Builds the rig at real scale (metres) from parametric parts: feed tank with ice packs, pump,
bypass, PI-101 gauge, Y manifold, HV-101, FT-101 (YF-S401 body), DV-101 tee, 6 m x 8 mm silicone coil
on a former, R-101 clamp, TT-101 probe tee, XV-101 ball valve + MG996R servo + limit switches,
TK-103 on a kitchen scale, Arduino Uno, buck converter, wiring.

Animation is driven by data/raw/<scenario>__veriflush__seed0.csv (SIMULATED):
  * water colour in 20 coil segments  <- truth_profile_00..19 (tracer truth: brown = old, clear blue = fresh)
  * outlet line colour                <- truth_f_old_outlet
  * XV-101 lever / servo horn          <- truth_valve_pos
  * TK-103 level                       <- integral of truth_q_branch_lpm
1 simulated second = 4 frames at 24 fps (6x real time). Outputs go to 3d/renders/ and 3d/veriflush_rig.blend.
Lighting: Poly Haven "Studio Small 09" HDRI (CC0).
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SCEN = argv[argv.index("--scenario") + 1] if "--scenario" in argv else "S01_healthy"
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128
FPS, FPSIM = 24, 4
OUT = HERE / "renders"
OUT.mkdir(exist_ok=True)

OLD = (0.85, 0.36, 0.0)         # amber: stagnant old water (tracer truth)
MID = (0.42, 0.42, 0.40)        # neutral midpoint, so mixtures never read as a third colour
FRESH = (0.06, 0.38, 0.95)     # blue: fresh feed water

# ------------------------------------------------------------------ helpers
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


def mat(name, color=(0.8, 0.8, 0.8), metal=0.0, rough=0.5, trans=0.0, ior=1.45, alpha=1.0, coat=0.0, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = trans
    b.inputs["IOR"].default_value = ior
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1)
        b.inputs["Emission Strength"].default_value = emit[1]
    return m


def link(obj, m=None, parent=None):
    col.objects.link(obj)
    if m:
        obj.data.materials.append(m)
    if parent:
        obj.parent = parent
    return obj


def box(name, size, loc, m, bevel=0.0, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width, b.segments = bevel, 3
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    if parent:
        o.parent = parent
    return o


def cyl(name, r, depth, loc, m, rot=(0, 0, 0), verts=48, bevel=0.0, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width, b.segments = bevel, 3
        b.limit_method = "ANGLE"
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    if parent:
        o.parent = parent
    return o


def smooth_path(pts, n=12):
    """Catmull-Rom through control points."""
    P = [Vector(p) for p in pts]
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def tube(name, pts, r, m, smooth=True, caps=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = caps
    path = smooth_path(pts) if smooth else [Vector(p) for p in pts]
    sp = cu.splines.new("POLY")
    sp.points.add(len(path) - 1)
    for p, q in zip(sp.points, path):
        p.co = (*q, 1)
    o = bpy.data.objects.new(name, cu)
    return link(o, m)


def water_line(name, pts, smooth=True):
    """silicone tube (8x10 mm) + water core with its own material."""
    tube(name + "_silicone", pts, 0.005, M["silicone"], smooth)
    wm = mat(name + "_water", FRESH, rough=0.15, trans=0.05, ior=1.33)
    tube(name + "_water", pts, 0.0038, wm, smooth)
    return wm


LABELS = "--labels" in argv


def text(body, loc, size, m, rot=(math.radians(90), 0, 0), align="LEFT", parent=None, force=False):
    if not (LABELS or force):
        return None
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    o = bpy.data.objects.new("txt_" + body[:10], cu)
    o.location, o.rotation_euler = loc, rot
    return link(o, m, parent)


# ------------------------------------------------------------------ materials
M = dict(
    bench=mat("bench", (0.30, 0.17, 0.09), rough=0.45),
    backdrop=mat("backdrop", (0.012, 0.012, 0.014), rough=0.95),
    acrylic=mat("acrylic", (0.95, 0.97, 1.0), rough=0.02, trans=1.0, ior=1.49),
    tankwater=mat("tank_water", (0.70, 0.86, 0.98), rough=0.02, trans=1.0, ior=1.33),
    ice=mat("icepack", (0.10, 0.35, 0.85), rough=0.35, coat=0.6),
    silicone=mat("silicone", (0.98, 0.98, 1.0), rough=0.10, trans=1.0, ior=1.41),
    blackplastic=mat("black_plastic", (0.02, 0.02, 0.022), rough=0.35, coat=0.2),
    greyplastic=mat("grey_plastic", (0.62, 0.63, 0.64), rough=0.4),
    whiteplastic=mat("white_plastic", (0.88, 0.88, 0.86), rough=0.35),
    blue=mat("blue_lever", (0.05, 0.22, 0.75), rough=0.3),
    red=mat("red", (0.75, 0.05, 0.04), rough=0.35),
    steel=mat("steel", (0.75, 0.76, 0.78), metal=1.0, rough=0.25),
    brass=mat("brass", (0.80, 0.60, 0.25), metal=1.0, rough=0.3),
    pcb=mat("pcb_uno", (0.0, 0.42, 0.45), rough=0.35, coat=0.5),
    pcbblue=mat("pcb_blue", (0.02, 0.12, 0.45), rough=0.35, coat=0.5),
    gold=mat("gold", (1.0, 0.77, 0.34), metal=1.0, rough=0.2),
    pvc=mat("pvc_former", (0.045, 0.047, 0.05), rough=0.5),
    lcd=mat("lcd", (0.05, 0.08, 0.06), rough=0.2, emit=((0.35, 0.9, 0.55), 1.5)),
    gaugeface=mat("gauge_face", (0.95, 0.95, 0.93), rough=0.5),
    glass=mat("glass", (1, 1, 1), rough=0.0, trans=1.0, ior=1.5),
    wire_r=mat("wire_red", (0.7, 0.03, 0.03), rough=0.45),
    wire_k=mat("wire_black", (0.02, 0.02, 0.02), rough=0.45),
    wire_y=mat("wire_yellow", (0.85, 0.65, 0.02), rough=0.45),
    wire_b=mat("wire_blue", (0.05, 0.2, 0.8), rough=0.45),
    label=mat("label", (0.08, 0.08, 0.08), rough=0.6),
    zinc=mat("zinc", (0.62, 0.64, 0.66), metal=1.0, rough=0.45),
    copper=mat("copper", (0.85, 0.45, 0.25), metal=1.0, rough=0.3),
    maroon=mat("pcb_maroon", (0.13, 0.012, 0.018), rough=0.35, coat=0.5),
    terminal=mat("terminal_green", (0.05, 0.45, 0.25), rough=0.4),
    frosted=mat("frosted_white", (0.92, 0.93, 0.95), rough=0.35, trans=0.35, ior=1.5),
    sticker=mat("sticker", (0.85, 0.12, 0.10), rough=0.5),
    enclosure=mat("enclosure_abs", (0.90, 0.91, 0.92), rough=0.3, coat=0.3),
    wire_o=mat("wire_orange", (0.95, 0.45, 0.02), rough=0.45),
    wire_n=mat("wire_brown", (0.25, 0.12, 0.05), rough=0.45),
    acrylic_board=mat("acrylic_board", (0.92, 0.94, 0.96), rough=0.15, trans=0.6, ior=1.49),
)

def wood(m):
    nt = m.node_tree
    tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0, 40.0, 2.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 4.0
    nz.inputs["Detail"].default_value = 10.0
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.06, 0.03, 0.015, 1)
    cr.color_ramp.elements[1].color = (0.20, 0.10, 0.045, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])


wood(M["bench"])
# ------------------------------------------------------------------ bench + backdrop
box("bench", (2.4, 1.2, 0.04), (0, 0.1, -0.02), M["bench"], bevel=0.004)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.75, 0.6), rotation=(math.radians(90), 0, 0))
bd = bpy.context.active_object
bd.scale = (4, 1.6, 1)
bd.data.materials.append(M["backdrop"])

# ------------------------------------------------------------------ TK-101 feed tank with ice packs
TX, TW, TD, TH, WT = -0.75, 0.30, 0.22, 0.22, 0.004
for nm, s, l in [("tk101_bottom", (TW, TD, WT), (TX, 0, WT / 2)),
                 ("tk101_front", (TW, WT, TH), (TX, -TD / 2, TH / 2)), ("tk101_back", (TW, WT, TH), (TX, TD / 2, TH / 2)),
                 ("tk101_left", (WT, TD, TH), (TX - TW / 2, 0, TH / 2)), ("tk101_right", (WT, TD, TH), (TX + TW / 2, 0, TH / 2))]:
    box(nm, s, l, M["acrylic"], bevel=0.001)
box("tk101_water", (TW - 2 * WT - 0.001, TD - 2 * WT - 0.001, 0.16), (TX, 0, WT + 0.08), M["tankwater"])
box("icepack1", (0.12, 0.07, 0.025), (TX - 0.06, -0.03, 0.15), M["ice"], bevel=0.008, rot=(0.15, 0.1, 0.4))
box("icepack2", (0.11, 0.07, 0.025), (TX + 0.07, 0.04, 0.152), M["ice"], bevel=0.008, rot=(-0.1, 0.12, -0.3))
text("TK-101 FEED", (TX - 0.12, -TD / 2 - 0.003, 0.195), 0.018, M["label"])

# ------------------------------------------------------------------ pump P-101 (12 V DC pump: side inlet, top outlet)
PX = -0.47
box("pump_body", (0.040, 0.030, 0.034), (PX, 0, 0.019), M["blackplastic"], bevel=0.003)
for k in (-1, 1):
    box(f"pump_rib{k}", (0.0408, 0.0308, 0.0015), (PX, 0, 0.019 + k * 0.009), M["blackplastic"], bevel=0.0005)
cyl("pump_inlet", 0.0045, 0.018, (PX - 0.029, 0, 0.012), M["blackplastic"], rot=(0, math.radians(90), 0))
cyl("pump_outlet", 0.0045, 0.018, (PX + 0.010, 0, 0.045), M["blackplastic"])
box("pump_label", (0.020, 0.0004, 0.013), (PX - 0.004, -0.0153, 0.019), M["whiteplastic"])


def brass_fitting(name, loc, arms, rot=(0, 0, 0)):
    """barbed brass Y/T: hub + one barbed stub per arm direction (local frame)."""
    g = bpy.data.objects.new(name, None)
    g.location, g.rotation_euler = loc, rot
    link(g)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0062, location=(0, 0, 0))
    h = bpy.context.active_object
    h.name, h.parent = name + "_hub", g
    h.data.materials.append(M["brass"])
    bpy.ops.object.shade_smooth()
    for k, d in enumerate(arms):
        d = Vector(d).normalized()
        e = Vector((0, 0, 1)).rotation_difference(d).to_euler()
        cyl(f"{name}_arm{k}", 0.0042, 0.018, tuple(d * 0.012), M["brass"], rot=e, parent=g)
        for j, t in enumerate((0.008, 0.013, 0.018)):
            cyl(f"{name}_barb{k}{j}", 0.0050, 0.0022, tuple(d * t), M["brass"], rot=e, verts=32, parent=g)
    return g


def valve(name, loc, axis_rot, lever_m=None, lever_angle=0.0, body=None, branch=False):
    """push-fit ball valve (white body, blue collet clips, blue lever). Local x = pipe axis.
    Returns the lever pivot (rotate about local z to animate)."""
    g = bpy.data.objects.new(name, None)
    g.location, g.rotation_euler = loc, axis_rot
    link(g)
    box(name + "_body", (0.020, 0.017, 0.017), (0, 0, 0), M["whiteplastic"], bevel=0.003, parent=g)
    ends = [(1, 0, 0), (-1, 0, 0)] + ([(0, 1, 0)] if branch else [])
    for k, d in enumerate(ends):
        d = Vector(d)
        e = Vector((0, 0, 1)).rotation_difference(d).to_euler()
        cyl(f"{name}_collet{k}", 0.0078, 0.016, tuple(d * 0.017), M["whiteplastic"], rot=e, bevel=0.0015, parent=g)
        cyl(f"{name}_clip{k}", 0.0081, 0.0018, tuple(d * 0.0255), M["blue"], rot=e, parent=g)
    cyl(name + "_handle_base", 0.0072, 0.006, (0, 0, 0.0115), M["blue"], bevel=0.001, parent=g)
    piv = bpy.data.objects.new(name + "_pivot", None)
    piv.location = (0, 0, 0.016)
    piv.parent = g
    link(piv)
    box(name + "_lever", (0.034, 0.012, 0.0032), (0.014, 0, 0), M["blue"], bevel=0.0012, parent=piv)
    piv.rotation_euler = (0, 0, lever_angle)
    return piv


# ------------------------------------------------------------------ PI-101 gauge (40 mm, 0-3 bar) on a brass tee
GX, GZ = -0.32, 0.135
cyl("gauge_hose_clamp", 0.0063, 0.005, (GX, 0, 0.083), M["steel"])
cyl("gauge_barb_adapter", 0.0034, 0.014, (GX, 0, 0.097), M["zinc"])
cyl("gauge_hex", 0.0078, 0.016, (GX, 0, 0.110), M["zinc"], verts=6)
cyl("gauge_stem", 0.0035, 0.006, (GX, 0, 0.1155), M["brass"])
cyl("gauge_case", 0.0205, 0.017, (GX, 0, GZ), M["blackplastic"], rot=(math.radians(90), 0, 0), bevel=0.002)
cyl("gauge_face", 0.0182, 0.001, (GX, -0.0086, GZ), M["gaugeface"], rot=(math.radians(90), 0, 0))
cyl("gauge_glass", 0.0192, 0.0015, (GX, -0.0098, GZ), M["glass"], rot=(math.radians(90), 0, 0))
band_g = mat("band_green", (0.10, 0.60, 0.15), rough=0.5)
band_y = mat("band_yellow", (0.95, 0.80, 0.05), rough=0.5)
band_r = mat("band_red", (0.70, 0.05, 0.05), rough=0.5)


def dial_angle(bar):
    return math.radians(-135 + 270 * bar / 3.0)


for nm, b0, b1, m in (("g", 0.0, 0.6, band_g), ("y", 0.6, 1.0, band_y), ("r", 1.0, 3.0, band_r)):
    n = max(3, int((b1 - b0) * 14))
    for k in range(n):
        a = dial_angle(b0 + (b1 - b0) * (k + 0.5) / n)
        box(f"band_{nm}{k}", (0.0155 * 4.71 / 3 * (b1 - b0) / n + 0.0004, 0.0004, 0.0022),
            (GX + 0.0155 * math.sin(a), -0.0089, GZ + 0.0155 * math.cos(a)), m, rot=(0, a, 0))
for k in range(13):
    a = dial_angle(3.0 * k / 12)
    box(f"tick{k}", (0.0006, 0.0004, 0.0028), (GX + 0.0125 * math.sin(a), -0.0089, GZ + 0.0125 * math.cos(a)),
        M["label"], rot=(0, a, 0))
a = dial_angle(0.02)                                   # honest reading: a few kPa is ~0 on a 0-3 bar dial
box("needle", (0.0008, 0.0004, 0.014), (GX + 0.006 * math.sin(a), -0.0093, GZ + 0.006 * math.cos(a)), M["label"], rot=(0, a, 0))
cyl("needle_cap", 0.0018, 0.001, (GX, -0.0095, GZ), M["label"], rot=(math.radians(90), 0, 0))
text("PI-101 0-3 bar", (GX - 0.035, -0.012, 0.205), 0.009, M["label"])

# ------------------------------------------------------------------ fixed plumbing (always fresh feed water)
Z = 0.03
fresh_lines = []
fresh_lines.append(water_line("suction", [(TX + 0.06, 0, 0.02), (TX + 0.06, 0, 0.25), (TX + 0.13, 0, 0.27),
                                          (-0.56, 0, 0.15), (-0.53, 0, 0.02), (-0.516, 0, 0.012), (-0.508, 0, 0.012)]))
fresh_lines.append(water_line("pump_out", [(PX + 0.010, 0, 0.053), (PX + 0.010, 0, 0.068), (-0.43, 0, 0.06), (-0.38, 0, Z),
                                           (GX - 0.02, 0, Z), (GX + 0.02, 0, Z), (-0.26, 0, Z), (-0.236, 0, Z)]))
brass_fitting("gauge_tee", (GX, 0, Z), [(1, 0, 0), (-1, 0, 0), (0, 0, 1)])
fresh_lines.append(water_line("gauge_tap", [(GX, 0, Z + 0.02), (GX, 0, 0.06), (GX, 0, 0.092)]))
# bypass BV-101 back to the tank
fresh_lines.append(water_line("bypass", [(-0.38, 0.0, Z), (-0.39, 0.06, 0.05), (-0.45, 0.09, 0.12), (-0.55, 0.09, 0.24),
                                         (TX + 0.10, 0.07, 0.27), (TX + 0.10, 0.07, 0.16)]))
valve("bv101", (-0.47, 0.09, 0.15), (0, math.radians(70), math.radians(15)), None, math.radians(45))
text("BV-101 bypass", (-0.53, 0.09, 0.19), 0.009, M["label"])
# Y manifold
brass_fitting("manifold_y", (-0.22, 0, Z), [(-1, 0, 0), (0.64, 0.77, 0), (0.64, -0.77, 0)])
# reference branch HV-201 -> 2 m -> TK-102 (behind the coil)
fresh_lines.append(water_line("reference", [(-0.208, 0.016, Z), (-0.18, 0.06, Z), (-0.12, 0.25, Z), (0.30, 0.30, Z + 0.002),
                                            (0.50, 0.36, Z), (0.58, 0.42, 0.17), (0.60, 0.43, 0.20)]))
valve("hv201", (-0.15, 0.17, Z + 0.003), (0, math.radians(90), math.radians(72)), M["blue"])
# monitored branch head: HV-101 -> FT-101 -> DV-101 tee
fresh_lines.append(water_line("mon_head", [(-0.208, -0.016, Z), (-0.17, -0.05, Z), (-0.14, -0.06, Z), (-0.07, -0.06, Z),
                                           (0.04, -0.06, Z), (0.10, -0.06, Z), (0.135, -0.03, Z), (0.15, 0.0, Z)]))
valve("hv101", (-0.125, -0.06, Z), (0, math.radians(90), 0), M["blue"])
text("HV-101", (-0.15, -0.075, 0.075), 0.009, M["label"])
# FT-101 (YF-S401 class): black body + barbs + cable
FX, FY = -0.065, -0.06
cyl("ft101_body", 0.0165, 0.014, (FX, FY, Z), M["frosted"], verts=64, bevel=0.0015)
cyl("ft101_lid", 0.0168, 0.002, (FX, FY, Z + 0.0075), M["whiteplastic"], verts=64)
cyl("ft101_sticker", 0.0095, 0.0004, (FX, FY, Z + 0.0087), M["whiteplastic"], verts=48)
cyl("ft101_ring", 0.0098, 0.0003, (FX, FY, Z + 0.0085), M["sticker"], verts=48)
for k in range(3):
    a = math.radians(90 + 120 * k)
    cyl(f"ft101_screw{k}", 0.0018, 0.0012, (FX + 0.0135 * math.cos(a), FY + 0.0135 * math.sin(a), Z + 0.0088), M["steel"], verts=16)
for k in (-1, 1):
    cyl(f"ft101_barb{k}", 0.0032, 0.016, (FX + k * 0.022, FY, Z), M["frosted"], rot=(0, math.radians(90), 0))
box("ft101_jst", (0.007, 0.005, 0.004), (FX, FY - 0.018, Z + 0.003), M["whiteplastic"])
text("FT-101", (-0.085, -0.075, 0.06), 0.009, M["label"])
valve("dv101", (0.03, -0.06, Z), (0, 0, 0), None, math.radians(90), branch=True)   # tee valve, closed
text("DV-101", (0.01, -0.075, 0.09), 0.009, M["label"])
water_line("diversion", [(0.03, -0.034, Z), (0.03, -0.01, Z + 0.01), (0.10, 0.12, 0.14), (0.45, 0.40, 0.16), (0.64, 0.43, 0.20)])

# TK-102 collection tank (reference + diversion), back right
for nm, s, l in [("tk102_bottom", (0.20, 0.16, WT), (0.62, 0.43, WT / 2)),
                 ("tk102_front", (0.20, WT, 0.16), (0.62, 0.35, 0.08)), ("tk102_back", (0.20, WT, 0.16), (0.62, 0.51, 0.08)),
                 ("tk102_left", (WT, 0.16, 0.16), (0.52, 0.43, 0.08)), ("tk102_right", (WT, 0.16, 0.16), (0.72, 0.43, 0.08))]:
    box(nm, s, l, M["acrylic"], bevel=0.001)
box("tk102_water", (0.19, 0.15, 0.05), (0.62, 0.43, 0.03), M["tankwater"])
text("TK-102", (0.54, 0.349, 0.13), 0.014, M["label"])

# ------------------------------------------------------------------ the coil (6 m x 8 mm on a former)
CX, CY, CR, Z0, PITCH = 0.32, 0.03, 0.15, 0.03, 0.021
L = 6.0
turns = L / (2 * math.pi * CR)
cyl("former", CR - 0.0055, 0.17, (CX, CY, 0.085), M["pvc"], verts=96, bevel=0.003)
cyl("former_cap", CR - 0.0055, 0.004, (CX, CY, 0.172), M["pvc"], verts=96)
N_SEG, PTS_PER = 20, 40
coil_mats = []
a0 = math.pi                                    # inlet faces -x
total = N_SEG * PTS_PER
helix = [(CX + CR * math.cos(a0 + 2 * math.pi * turns * k / total),
          CY + CR * math.sin(a0 + 2 * math.pi * turns * k / total),
          Z0 + PITCH * turns * k / total) for k in range(total + 1)]
tube("coil_silicone", helix, 0.005, M["silicone"], smooth=False)
for j in range(N_SEG):
    wm = mat(f"coil_water_{j:02d}", OLD, rough=0.15, trans=0.05, ior=1.33)
    tube(f"coil_water_{j:02d}", helix[j * PTS_PER: (j + 1) * PTS_PER + 1], 0.0038, wm, smooth=False, caps=False)
    coil_mats.append(wm)
text("6 m x 8 mm silicone coil", (CX - 0.11, CY - CR - 0.012, 0.19), 0.011, M["label"])
for k in range(6):                                  # nylon cable ties holding the coil to the former
    a = math.radians(30 + 60 * k)
    box(f"cable_tie{k}", (0.0036, 0.0014, 0.158), (CX + (CR + 0.0056) * math.cos(a), CY + (CR + 0.0056) * math.sin(a), 0.098),
        M["blackplastic"], rot=(0, 0, a - math.pi / 2))
    box(f"cable_tie_head{k}", (0.006, 0.004, 0.007), (CX + (CR + 0.0075) * math.cos(a), CY + (CR + 0.0075) * math.sin(a), 0.17),
        M["blackplastic"], rot=(0, 0, a - math.pi / 2))
end = Vector(helix[-1])
d_end = (Vector(helix[-1]) - Vector(helix[-2])).normalized()

# ------------------------------------------------------------------ endpoint: R-101, TT-101, XV-101, outlet
p1 = end + d_end * 0.03
ex = [tuple(end), tuple(p1), (0.52, -0.06, 0.16), (0.56, -0.09, 0.15), (0.70, -0.09, 0.15), (0.80, -0.09, 0.15),
      (0.84, -0.09, 0.12), (0.84, -0.09, 0.09)]
out_mat = water_line("endpoint", ex)
# R-101 hose clamp
cyl("r101_band", 0.0062, 0.008, (0.575, -0.09, 0.15), M["steel"], rot=(0, math.radians(90), 0))
box("r101_screw", (0.008, 0.012, 0.008), (0.575, -0.09, 0.161), M["steel"], bevel=0.001)
text("R-101", (0.56, -0.105, 0.175), 0.009, M["label"])
# TT-101 probe tee
brass_fitting("tt101_tee", (0.62, -0.09, 0.15), [(1, 0, 0), (-1, 0, 0), (0, 0, 1)])
cyl("tt101_probe", 0.003, 0.05, (0.62, -0.09, 0.185), M["steel"])
tube("tt101_cable", [(0.62, -0.09, 0.21), (0.62, -0.10, 0.25), (0.55, -0.20, 0.18), (0.20, -0.30, 0.02), (-0.30, -0.27, 0.012)],
     0.0022, M["wire_k"])
text("TT-101", (0.60, -0.105, 0.215), 0.009, M["label"])
# XV-101 push-fit ball valve, MG996R coupled to the stem, ANDELI lever microswitches, on an acrylic backing board
box("xv_board", (0.20, 0.006, 0.24), (0.70, -0.055, 0.12), M["acrylic_board"], bevel=0.002)
xv_piv = valve("xv101", (0.70, -0.09, 0.15), (0, 0, 0), None, 0.0)
cyl("xv_coupler", 0.0035, 0.006, (0.70, -0.09, 0.1705), M["steel"])
servo = box("mg996r_body", (0.0405, 0.020, 0.037), (0.710, -0.09, 0.200), M["blackplastic"], bevel=0.0015)
box("mg996r_tabs", (0.054, 0.020, 0.0025), (0.710, -0.09, 0.190), M["blackplastic"], bevel=0.0005)
box("mg996r_label", (0.020, 0.0004, 0.010), (0.712, -0.1003, 0.204), M["sticker"])
for k in (-1, 1):
    box(f"servo_bracket{k}", (0.004, 0.035, 0.004), (0.710 + k * 0.025, -0.075, 0.190), M["steel"])
horn_piv = bpy.data.objects.new("servo_horn_pivot", None)
horn_piv.location = (0.70, -0.09, 0.1795)
link(horn_piv)
cyl("horn_hub", 0.0055, 0.004, (0, 0, 0), M["blackplastic"], parent=horn_piv)
box("horn_arm", (0.028, 0.006, 0.002), (0.011, 0, -0.001), M["blackplastic"], bevel=0.001, parent=horn_piv)
for k, (nm, loc, rz) in enumerate((("ls_open", (0.745, -0.09, 0.166), 0.0), ("ls_closed", (0.70, -0.135, 0.166), math.pi / 2))):
    sw = bpy.data.objects.new(nm, None)
    sw.location, sw.rotation_euler = loc, (0, 0, rz)
    link(sw)
    box(nm + "_body", (0.0278, 0.0103, 0.0159), (0.012, 0, 0), M["blackplastic"], bevel=0.0008, parent=sw)
    box(nm + "_lever", (0.045, 0.0045, 0.0004), (-0.004, -0.007, 0.004), M["steel"], rot=(0, 0, -0.12), parent=sw)
    for j in range(3):
        box(f"{nm}_tab{j}", (0.0005, 0.003, 0.006), (0.004 + 0.008 * j, 0, -0.010), M["brass"], parent=sw)
text("XV-101", (0.675, -0.115, 0.13), 0.009, M["label"])
# TK-103 outlet tank on kitchen scale
SX = 0.84
box("scale_base", (0.20, 0.20, 0.018), (SX, -0.09, 0.009), M["whiteplastic"], bevel=0.004)
box("scale_lcd", (0.05, 0.002, 0.012), (SX, -0.191, 0.009), M["lcd"])
for nm, s, l in [("tk103_bottom", (0.16, 0.16, WT), (SX, -0.09, 0.018 + WT / 2)),
                 ("tk103_front", (0.16, WT, 0.13), (SX, -0.17, 0.018 + 0.065)), ("tk103_back", (0.16, WT, 0.13), (SX, -0.01, 0.083)),
                 ("tk103_left", (WT, 0.16, 0.13), (SX - 0.08, -0.09, 0.083)), ("tk103_right", (WT, 0.16, 0.13), (SX + 0.08, -0.09, 0.083))]:
    box(nm, s, l, M["acrylic"], bevel=0.001)
tk103_mat = mat("tk103_water", FRESH, rough=0.02, trans=0.9, ior=1.33)
tk103_w = box("tk103_water", (0.15, 0.15, 0.001), (SX, -0.09, 0.0225), tk103_mat)
text("TK-103 on scale", (SX - 0.075, -0.192, 0.11), 0.011, M["label"])

# ------------------------------------------------------------------ electronics: IP65 enclosure, Uno + screw shield, XL4015, power
EX, EY = -0.27, -0.28
bpy.ops.mesh.primitive_cube_add(size=1, location=(EX, EY, 0.035))
enc = bpy.context.active_object
enc.name, enc.scale = "enclosure_150x110x70", (0.150, 0.110, 0.070)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.mesh.primitive_cube_add(size=1, location=(EX, EY, 0.038))
cav = bpy.context.active_object
cav.scale = (0.142, 0.102, 0.070)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bm = enc.modifiers.new("cavity", "BOOLEAN")
bm.operation, bm.object = "DIFFERENCE", cav
bpy.context.view_layer.objects.active = enc
bpy.ops.object.modifier_apply(modifier="cavity")
bpy.data.objects.remove(cav)
bv = enc.modifiers.new("bevel", "BEVEL")
bv.width, bv.segments, bv.limit_method = 0.003, 3, "ANGLE"
enc.data.materials.append(M["enclosure"])
for k in range(3):                                                   # cable glands on the rig side
    gx = EX - 0.045 + 0.045 * k
    for j, (r, d) in enumerate(((0.0105, 0.004), (0.0092, 0.003), (0.0082, 0.003), (0.0072, 0.003), (0.006, 0.003))):
        cyl(f"gland{k}_{j}", r, d, (gx, EY + 0.055 + 0.002 + 0.0032 * j, 0.032), M["whiteplastic"],
            rot=(math.radians(90), 0, 0), bevel=0.0006)
lid = box("enclosure_lid", (0.150, 0.110, 0.012), (EX - 0.20, EY - 0.04, 0.006), M["enclosure"], bevel=0.003,
          rot=(0, 0, math.radians(14)))
box("lid_label", (0.030, 0.012, 0.0005), (EX - 0.20, EY - 0.04, 0.0123), M["whiteplastic"], rot=(0, 0, math.radians(14)))
# blue Uno (CH340 clone) + red screw shield
uno = bpy.data.objects.new("arduino_uno", None)
uno.location = (EX - 0.022, EY, 0.003)
link(uno)
box("uno_pcb", (0.0686, 0.0534, 0.0016), (0, 0, 0.012), M["pcbblue"], parent=uno)
for k in range(4):
    cyl(f"uno_standoff{k}", 0.0025, 0.011, (0.03 * (1 if k % 2 else -1), 0.023 * (1 if k < 2 else -1), 0.0055),
        M["brass"], parent=uno)
box("uno_usb", (0.016, 0.012, 0.011), (-0.030, 0.013, 0.0185), M["steel"], bevel=0.0005, parent=uno)
box("uno_jack", (0.014, 0.009, 0.011), (-0.030, -0.018, 0.0185), M["blackplastic"], bevel=0.0005, parent=uno)
box("uno_mcu", (0.007, 0.007, 0.0012), (0.004, 0.0, 0.0134), M["blackplastic"], parent=uno)
for k, x in enumerate((-0.014, -0.006)):
    cyl(f"uno_cap{k}", 0.003, 0.006, (x, -0.020, 0.016), M["steel"], parent=uno)
box("shield_pcb", (0.0686, 0.0534, 0.0016), (0, 0, 0.0265), M["maroon"], parent=uno)
for k in range(10):
    for j in range(8):
        cyl(f"shield_hole{k}{j}", 0.0005, 0.0018, (-0.010 + 0.00254 * k, -0.009 + 0.00254 * j, 0.0266), M["gold"], verts=8,
            parent=uno)
for y in (-0.0225, 0.0225):
    box(f"shield_terminals{y}", (0.052, 0.0075, 0.0095), (0.006, y, 0.032), M["terminal"], bevel=0.0005, parent=uno)
    for k in range(10):
        cyl(f"shield_screw{y}{k}", 0.0013, 0.001, (-0.017 + 0.005 * k, y, 0.0368), M["steel"], verts=12, parent=uno)
for k in range(4):
    cyl(f"shield_post{k}", 0.0012, 0.013, (0.03 * (1 if k % 2 else -1), 0.023 * (1 if k < 2 else -1), 0.019),
        M["blackplastic"], parent=uno)
# XL4015 buck converter
xl = bpy.data.objects.new("xl4015", None)
xl.location = (EX + 0.045, EY - 0.01, 0.003)
xl.rotation_euler = (0, 0, math.radians(90))
link(xl)
box("xl4015_pcb", (0.051, 0.026, 0.0016), (0, 0, 0.004), M["pcbblue"], parent=xl)
for k, x in enumerate((-0.018, 0.018)):
    cyl(f"xl4015_cap{k}", 0.0042, 0.010, (x, 0.003, 0.0098), M["steel"], parent=xl)
    cyl(f"xl4015_captop{k}", 0.0041, 0.0006, (x, 0.003, 0.0151), M["label"], parent=xl)
bpy.ops.mesh.primitive_torus_add(major_radius=0.0052, minor_radius=0.0024, location=(-0.006, 0.004, 0.0105),
                                 rotation=(math.radians(90), 0, 0))
tor = bpy.context.active_object
tor.name, tor.parent = "xl4015_toroid", xl
tor.data.materials.append(M["copper"])
bpy.ops.object.shade_smooth()
box("xl4015_pot", (0.0095, 0.0045, 0.0095), (-0.004, -0.007, 0.0095), M["blue"], parent=xl)
for k in range(4):
    box(f"xl4015_fin{k}", (0.0012, 0.009, 0.006), (0.007 + 0.0025 * k, 0.004, 0.0085), M["steel"], parent=xl)
# rocker switch on the side wall, inline blade fuse, 12 V brick
cyl("rocker_bezel", 0.0105, 0.003, (EX + 0.0765, EY, 0.040), M["blackplastic"], rot=(0, math.radians(90), 0), bevel=0.0008)
box("rocker", (0.003, 0.012, 0.014), (EX + 0.078, EY, 0.040), M["blackplastic"], bevel=0.001, rot=(0, 0.15, 0))
box("psu_brick", (0.12, 0.05, 0.032), (-0.62, -0.30, 0.016), M["blackplastic"], bevel=0.004, rot=(0, 0, math.radians(-8)))
box("psu_label", (0.05, 0.03, 0.0004), (-0.62, -0.30, 0.0322), M["label"], rot=(0, 0, math.radians(-8)))
tube("psu_dc", [(-0.56, -0.305, 0.014), (-0.50, -0.33, 0.006), (-0.44, -0.33, 0.006), (EX - 0.08, EY, 0.03)], 0.0018, M["wire_k"])
box("fuse_holder", (0.036, 0.012, 0.012), (-0.47, -0.332, 0.008), M["blackplastic"], bevel=0.002, rot=(0, 0, math.radians(-3)))
tube("psu_ac", [(-0.68, -0.29, 0.014), (-0.74, -0.27, 0.006), (-0.95, -0.33, 0.006), (-1.15, -0.30, 0.006)], 0.0025, M["wire_k"])
# sensor / actuator leads into the glands
GL = [(EX - 0.045, EY + 0.072, 0.032), (EX, EY + 0.072, 0.032), (EX + 0.045, EY + 0.072, 0.032)]
for k, (m, dx) in enumerate(((M["wire_r"], -0.003), (M["wire_k"], 0.0), (M["wire_y"], 0.003))):
    tube(f"w_ft{k}", [(FX + dx, FY - 0.022, Z + 0.003), (FX + dx, -0.12, 0.012), (GL[0][0] + 0.02 + dx, -0.17, 0.02),
                      (GL[0][0] + dx, GL[0][1], GL[0][2])], 0.0011, m)
for k, (m, dx) in enumerate(((M["wire_n"], -0.002), (M["wire_r"], 0.0), (M["wire_o"], 0.002))):
    tube(f"w_servo{k}", [(0.69 + dx, -0.10, 0.205), (0.62, -0.18, 0.12), (0.30, -0.26, 0.01), (GL[1][0] + 0.03, -0.19, 0.015),
                         (GL[1][0] + dx, GL[1][1], GL[1][2])], 0.0010, m)
tube("w_tt101", [(0.62, -0.09, 0.21), (0.62, -0.10, 0.25), (0.55, -0.20, 0.18), (0.20, -0.25, 0.01),
                 (GL[2][0] + 0.03, -0.19, 0.015), GL[2]], 0.0022, M["wire_k"])
tube("w_tt100", [(TX + 0.12, 0.06, 0.02), (TX + 0.12, 0.06, 0.25), (-0.58, -0.10, 0.20), (-0.40, -0.16, 0.02),
                 (GL[0][0] - 0.01, -0.17, 0.02), (GL[0][0] - 0.004, GL[0][1], GL[0][2] + 0.004)], 0.0022, M["wire_k"])
for k, m in enumerate((M["wire_r"], M["wire_k"])):
    tube(f"w_pump{k}", [(PX + 0.02, -0.012 + 0.004 * k, 0.012), (PX + 0.06, -0.10, 0.004), (-0.36, -0.18, 0.006),
                        (GL[0][0] - 0.012 + 0.003 * k, GL[0][1], GL[0][2] - 0.004)], 0.0012, m)
cyl("tt100_probe", 0.003, 0.05, (TX + 0.12, 0.06, 0.045), M["steel"])

# ------------------------------------------------------------------ simulation-driven animation
def load(scn):
    f = ROOT / "data" / "raw" / f"{scn}__veriflush__seed0.csv"
    with open(f, newline="") as fh:
        return list(csv.DictReader(fh))


def mixc(fo):
    fo = min(1.0, max(0.0, fo))
    if fo >= 0.5:
        w = (fo - 0.5) * 2
        return tuple(o * w + m * (1 - w) for o, m in zip(OLD, MID))
    w = fo * 2
    return tuple(m * w + n * (1 - w) for m, n in zip(MID, FRESH))


def key_color(m, c, frame):
    inp = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
    inp.default_value = (*c, 1)
    inp.keyframe_insert("default_value", frame=frame)


rows = load(SCEN)
vol_b, vol_old = 0.0, 0.0
area = 0.15 * 0.15
for r in rows:
    t = float(r["obs_t_s"])
    fr = 1 + int(round(t * FPSIM))
    for j, m in enumerate(coil_mats):
        key_color(m, mixc(float(r[f"truth_profile_{j:02d}"])), fr)
    key_color(out_mat, mixc(float(r["truth_f_old_outlet"])), fr)
    pos = float(r["truth_valve_pos"])
    xv_piv.rotation_euler = (0, 0, -math.radians(90) * (1 - pos))
    xv_piv.keyframe_insert("rotation_euler", frame=fr)
    horn_piv.rotation_euler = (0, 0, -math.radians(90) * (1 - pos))
    horn_piv.keyframe_insert("rotation_euler", frame=fr)
    q = float(r["truth_q_branch_lpm"]) / 60.0                  # L/s
    vol_b += q
    vol_old += q * float(r["truth_f_old_outlet"])
    h = max(0.001, vol_b / 1000 / area)
    tk103_w.scale = (1, 1, h / 0.001)
    tk103_w.location.z = 0.018 + WT + h / 2
    tk103_w.keyframe_insert("scale", frame=fr)
    tk103_w.keyframe_insert("location", frame=fr)
    key_color(tk103_mat, mixc(vol_old / vol_b if vol_b > 0 else 1.0), fr)
for m in fresh_lines:
    key_color(m, FRESH, 1)
scene.frame_start, scene.frame_end = 1, 1 + int(round(float(rows[-1]["obs_t_s"]) * FPSIM))
scene.render.fps = FPS
t_close = next((float(r["obs_t_s"]) for r in rows if r["ctrl_cmd_next"] == "0" and float(r["obs_t_s"]) > 3), None)

# ------------------------------------------------------------------ world, lights, camera
world = bpy.data.worlds.new("studio")
scene.world = world
world.use_nodes = True
nt = world.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(str(HERE / "assets" / "studio_small_09_2k.hdr"))
bg = nt.nodes["Background"]
bg.inputs["Strength"].default_value = 0.55
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
for nm, loc, energy, size in [("key", (-0.7, -0.9, 1.2), 320, 0.9), ("rim", (1.1, 0.8, 0.9), 260, 0.6), ("fill", (0.4, -1.4, 0.5), 60, 1.5)]:
    ld = bpy.data.lights.new(nm, "AREA")
    ld.energy, ld.size = energy, size
    lo = bpy.data.objects.new(nm, ld)
    lo.location = loc
    lo.rotation_euler = (Vector((0.05, 0.05, 0.1)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    link(lo)


def camera(name, loc, target, lens, fstop=None, focus=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = (Vector(focus or target) - Vector(loc)).length
    co = bpy.data.objects.new(name, cd)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return link(co)


cams = dict(
    wide=camera("cam_wide", (-0.42, -1.30, 1.02), (0.06, 0.02, 0.04), 33, 6.3),
    coil=camera("cam_coil", (0.55, -0.62, 0.42), (0.40, -0.02, 0.12), 50, 3.2, (0.60, -0.09, 0.15)),
    elec=camera("cam_elec", (-0.16, -0.50, 0.26), (-0.27, -0.28, 0.02), 50, 4.0, (-0.27, -0.28, 0.03)),
    valve=camera("cam_valve", (0.58, -0.36, 0.30), (0.71, -0.10, 0.17), 60, 3.5, (0.70, -0.10, 0.17)),
)
scene.camera = cams["wide"]

# ------------------------------------------------------------------ render settings
r = scene.render
r.resolution_x, r.resolution_y = 1920, 1080
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.9


def use_cycles():
    r.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = dev
                prefs.get_devices()
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = "GPU"
                print("Cycles device:", dev)
                break
            except TypeError:
                continue
    except Exception as e:  # noqa: BLE001
        print("GPU setup failed, CPU render:", e)


def render_still(cam, frame, name):
    scene.camera = cams[cam]
    scene.frame_set(frame)
    r.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "veriflush_rig.blend"))
if "--preview" in argv:
    use_cycles()
    render_still("wide", 1 + 22 * FPSIM, f"{SCEN}_preview_wide")
    render_still("coil", 1 + 22 * FPSIM, f"{SCEN}_preview_coil")
    render_still("elec", 1 + 22 * FPSIM, f"{SCEN}_preview_elec")
    render_still("valve", 1 + 22 * FPSIM, f"{SCEN}_preview_valve")
if "--stills" in argv:
    use_cycles()
    mid = 1 + int(round(22 * FPSIM))
    endf = 1 + int(round((t_close or 90) * FPSIM))
    render_still("wide", 1, f"{SCEN}_wide_t0")
    render_still("wide", mid, f"{SCEN}_wide_t22")
    render_still("wide", endf, f"{SCEN}_wide_end")
    render_still("coil", mid, f"{SCEN}_coil_t22")
    render_still("elec", endf, f"{SCEN}_electronics")
    render_still("valve", endf, f"{SCEN}_valve_closed")
if "--anim" in argv:
    use_cycles()
    scene.cycles.samples = max(16, SAMPLES // 4)
    tgt = bpy.data.objects.new("anim_target", None)
    tgt.location = (0.12, 0.0, 0.08)
    link(tgt)
    ca = camera("cam_anim", (-0.42, -1.30, 1.02), (0.12, 0.0, 0.08), 33, 6.3)
    tc = ca.constraints.new("TRACK_TO")
    tc.target, tc.track_axis, tc.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    ca.keyframe_insert("location", frame=scene.frame_start)
    ca.location = (0.02, -0.98, 0.66)
    ca.keyframe_insert("location", frame=scene.frame_end)
    scene.camera = ca
    r.resolution_x, r.resolution_y = 1280, 720
    r.image_settings.media_type = "VIDEO" if hasattr(r.image_settings, "media_type") else None
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format = "MPEG4"
    r.ffmpeg.codec = "H264"
    r.ffmpeg.constant_rate_factor = "HIGH"
    r.filepath = str(OUT / f"{SCEN}_flush_")
    bpy.ops.render.render(animation=True)
print("done", SCEN, "frames", scene.frame_start, scene.frame_end, "t_close", t_close)
