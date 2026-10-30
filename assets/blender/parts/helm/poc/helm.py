"""Proof of concept: an Iron Covenant great-helm modelled and rendered in headless Blender.

    python helm.py OUT_DIR [samples] [angle_deg]
"""
import math
import sys
from pathlib import Path

import bpy  # noqa: F401  (must load before bmesh)
import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

OUT = Path(sys.argv[1])
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 96
ANGLE = float(sys.argv[3]) if len(sys.argv) > 3 else 32
FILIGREE = str(OUT / "filigree.png")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ------------------------------------------------------------------ materials

def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def iron_material():
    """Blackened, oiled plate: near-black base, polished worn edges, grime in the cavities."""
    m, nt, out = node_mat("armour_iron")
    N, L = nt.nodes, nt.links
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0.92
    coord = N.new("ShaderNodeTexCoord")
    # Large blotchy oil/soot variation.
    blot = N.new("ShaderNodeTexNoise")
    blot.inputs["Scale"].default_value = 3.0
    blot.inputs["Detail"].default_value = 8
    L.new(coord.outputs["Object"], blot.inputs["Vector"])
    # Edge mask: where the bevelled normal departs from the true normal.
    bev = N.new("ShaderNodeBevel")
    bev.inputs["Radius"].default_value = 0.012
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L.new(bev.outputs["Normal"], dot.inputs[0])
    L.new(geo.outputs["Normal"], dot.inputs[1])
    edge = N.new("ShaderNodeMapRange")
    edge.inputs["From Min"].default_value = 0.995
    edge.inputs["From Max"].default_value = 0.90
    L.new(dot.outputs["Value"], edge.inputs["Value"])
    # Break the edge wear up with noise so it reads as chipping, not an outline.
    chip = N.new("ShaderNodeTexNoise")
    chip.inputs["Scale"].default_value = 40
    chip.inputs["Detail"].default_value = 6
    L.new(coord.outputs["Object"], chip.inputs["Vector"])
    chipr = N.new("ShaderNodeMapRange")
    chipr.inputs["From Min"].default_value = 0.36
    chipr.inputs["From Max"].default_value = 0.62
    L.new(chip.outputs["Fac"], chipr.inputs["Value"])
    wear = N.new("ShaderNodeMath")
    wear.operation = "MULTIPLY"
    wear.use_clamp = True
    L.new(edge.outputs["Result"], wear.inputs[0])
    L.new(chipr.outputs["Result"], wear.inputs[1])
    # Cavity grime from ambient occlusion.
    ao = N.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.08
    base = N.new("ShaderNodeMix")
    base.data_type = "RGBA"
    base.inputs[6].default_value = (0.010, 0.010, 0.012, 1)
    base.inputs[7].default_value = (0.032, 0.028, 0.026, 1)
    L.new(blot.outputs["Fac"], base.inputs[0])
    grime = N.new("ShaderNodeMix")
    grime.data_type = "RGBA"
    grime.inputs[6].default_value = (0.012, 0.008, 0.005, 1)
    L.new(ao.outputs["AO"], grime.inputs[0])
    L.new(base.outputs[2], grime.inputs[7])
    worn = N.new("ShaderNodeMix")
    worn.data_type = "RGBA"
    worn.inputs[7].default_value = (0.42, 0.40, 0.37, 1)
    L.new(wear.outputs[0], worn.inputs[0])
    L.new(grime.outputs[2], worn.inputs[6])
    # Dust and soot settle on the upward faces.
    up = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], up.inputs[0])
    dn = N.new("ShaderNodeTexNoise")
    dn.inputs["Scale"].default_value = 9
    dn.inputs["Detail"].default_value = 10
    L.new(coord.outputs["Object"], dn.inputs["Vector"])
    dmask = N.new("ShaderNodeMath")
    dmask.operation = "MULTIPLY"
    dmask.use_clamp = True
    upr = N.new("ShaderNodeMapRange")
    upr.inputs["From Min"].default_value = 0.35
    upr.inputs["From Max"].default_value = 0.95
    upr.inputs["To Max"].default_value = 0.45
    L.new(up.outputs["Z"], upr.inputs["Value"])
    dnr = N.new("ShaderNodeMapRange")
    dnr.inputs["From Min"].default_value = 0.4
    dnr.inputs["From Max"].default_value = 0.7
    L.new(dn.outputs["Fac"], dnr.inputs["Value"])
    L.new(upr.outputs["Result"], dmask.inputs[0])
    L.new(dnr.outputs["Result"], dmask.inputs[1])
    dusty = N.new("ShaderNodeMix")
    dusty.data_type = "RGBA"
    dusty.inputs[7].default_value = (0.05, 0.045, 0.04, 1)
    L.new(dmask.outputs[0], dusty.inputs[0])
    L.new(worn.outputs[2], dusty.inputs[6])
    L.new(dusty.outputs[2], bsdf.inputs["Base Color"])
    rough = N.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.40
    rough.inputs["To Max"].default_value = 0.74
    L.new(blot.outputs["Fac"], rough.inputs["Value"])
    rmix = N.new("ShaderNodeMix")
    rmix.inputs[3].default_value = 0.18
    L.new(wear.outputs[0], rmix.inputs[0])
    L.new(rough.outputs["Result"], rmix.inputs[2])
    rdust = N.new("ShaderNodeMix")
    rdust.inputs[3].default_value = 0.92
    L.new(dmask.outputs[0], rdust.inputs[0])
    L.new(rmix.outputs[0], rdust.inputs[2])
    L.new(rdust.outputs[0], bsdf.inputs["Roughness"])
    # Fine hammer marks and scratches as bump.
    ham = N.new("ShaderNodeTexVoronoi")
    ham.inputs["Scale"].default_value = 28
    L.new(coord.outputs["Object"], ham.inputs["Vector"])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    L.new(ham.outputs["Distance"], bump.inputs["Height"])
    L.new(bev.outputs["Normal"], bump.inputs["Normal"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    L.new(bsdf.outputs[0], out.inputs["Surface"])
    return m


def gold_material(name="trim_gold", mask=None):
    """Aged gold: bright on the raised edges, tarnished brown in the recesses."""
    m, nt, out = node_mat(name)
    N, L = nt.nodes, nt.links
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 1.0
    coord = N.new("ShaderNodeTexCoord")
    ao = N.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.05
    col = N.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = (0.16, 0.08, 0.025, 1)
    col.inputs[7].default_value = (0.86, 0.60, 0.26, 1)
    aor = N.new("ShaderNodeMapRange")
    aor.inputs["From Min"].default_value = 0.35
    L.new(ao.outputs["AO"], aor.inputs["Value"])
    L.new(aor.outputs["Result"], col.inputs[0])
    L.new(col.outputs[2], bsdf.inputs["Base Color"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18
    L.new(coord.outputs["Object"], noise.inputs["Vector"])
    rough = N.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.22
    rough.inputs["To Max"].default_value = 0.48
    L.new(noise.outputs["Fac"], rough.inputs["Value"])
    L.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    shader = bsdf.outputs[0]
    if mask:
        img = N.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(mask)
        img.image.colorspace_settings.name = "Non-Color"
        L.new(coord.outputs["UV"], img.inputs["Vector"])
        bump = N.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.6
        bump.inputs["Distance"].default_value = 0.004
        L.new(img.outputs["Color"], bump.inputs["Height"])
        L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        cut = N.new("ShaderNodeMath")
        cut.operation = "GREATER_THAN"
        cut.inputs[1].default_value = 0.35
        L.new(img.outputs["Color"], cut.inputs[0])
        transp = N.new("ShaderNodeBsdfTransparent")
        mix = N.new("ShaderNodeMixShader")
        L.new(cut.outputs[0], mix.inputs[0])
        L.new(transp.outputs[0], mix.inputs[1])
        L.new(bsdf.outputs[0], mix.inputs[2])
        shader = mix.outputs[0]
    L.new(shader, out.inputs["Surface"])
    return m


def emission_material(name, colour, strength):
    m, nt, out = node_mat(name)
    N, L = nt.nodes, nt.links
    em = N.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = colour
    em.inputs["Strength"].default_value = strength
    # Flicker the furnace light across the surface a little.
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.45
    mr.inputs["To Max"].default_value = 1.4
    L.new(noise.outputs["Fac"], mr.inputs["Value"])
    mul = N.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = strength
    L.new(mr.outputs["Result"], mul.inputs[0])
    L.new(mul.outputs[0], em.inputs["Strength"])
    L.new(em.outputs[0], out.inputs["Surface"])
    return m


IRON = iron_material()
GOLD = gold_material()
FILI = gold_material("trim_filigree", FILIGREE)
GLOW = emission_material("glow_visor", (1.0, 0.16, 0.0, 1), 0.9)
WINDOW = emission_material("glow_window", (1.0, 0.22, 0.02, 1), 1.4)


# ------------------------------------------------------------------ helpers

def link(obj):
    scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def mod(ob, kind, **kw):
    m = ob.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def direction(az_deg, el_deg):
    """Unit vector: azimuth 0 faces -Y (the walker's front), elevation up from the horizon."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def curve_obj(name, pts, radius, mat, cyclic=False, flat=1.0):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts):
        p.co = (*v, 1)
    sp.use_cyclic_u = cyclic
    ob = link(bpy.data.objects.new(name, cu))
    ob.data.materials.append(mat)
    return ob


# ------------------------------------------------------------------ helm shell

SHELL_SCALE = Vector((0.80, 0.94, 1.0))


def shell_point(d):
    return Vector((d.x * SHELL_SCALE.x, d.y * SHELL_SCALE.y, d.z * SHELL_SCALE.z))


def squarish(c, p=0.78):
    return math.copysign(abs(c) ** p, c)


bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=40, radius=1.0)
for v in bm.verts:
    x, y, z = v.co
    # Flatten the sides and squarer cheeks, like an armet rather than an egg.
    x, y = squarish(x), squarish(y, 0.9)
    x, y, z = x * SHELL_SCALE.x, y * SHELL_SCALE.y, z * SHELL_SCALE.z
    if y < 0:
        # The beaked faceplate: a sharp vertical keel down the face, strongest at the visor.
        face = max(0.0, 1 - ((z + 0.18) / 0.62) ** 2)
        y -= 0.26 * max(0.0, 1 - abs(x) / 0.52) * face
    v.co = Vector((x, y, z))
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, -0.74), plane_no=(0, 0, 1), clear_inner=True)
shell = mesh_obj("helm_shell", bm, IRON)
mod(shell, "SOLIDIFY", thickness=0.05, offset=-1)
mod(shell, "SUBSURF", levels=2, render_levels=2)


def visor_top(az):
    return -2 + 20 * (1 - min(1, abs(az) / 30)) ** 0.7


# The visor opening: a gothic pointed arch cut through the face.
def visor_outline(n=72):
    pts = []
    for i in range(n):
        t = i / n
        if t < 0.25:
            az, el = -30 + 60 * (t / 0.25), -26
        elif t < 0.40:
            az, el = 30, -26 + 24 * ((t - 0.25) / 0.15)
        elif t < 0.85:
            s = 1 - 2 * (t - 0.40) / 0.45
            az, el = 30 * s, visor_top(30 * s)
        else:
            az, el = -30, -2 - 24 * ((t - 0.85) / 0.15)
        pts.append((az, el))
    return pts


VISOR = visor_outline()
bm = bmesh.new()
inner = [bm.verts.new(direction(a, e) * 0.2) for a, e in VISOR]
outer = [bm.verts.new(direction(a, e) * 2.0) for a, e in VISOR]
n = len(VISOR)
for i in range(n):
    j = (i + 1) % n
    bm.faces.new((inner[i], inner[j], outer[j], outer[i]))
bm.faces.new(list(reversed(inner)))
bm.faces.new(outer)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
cutter = mesh_obj("visor_cutter", bm, IRON)
cutter.hide_render = True
bvh = BVHTree.FromObject(shell, bpy.context.evaluated_depsgraph_get())  # uncut surface for laying trim
mod(shell, "BOOLEAN", object=cutter, operation="DIFFERENCE", solver="EXACT")
mod(shell, "BEVEL", width=0.012, segments=3, limit_method="ANGLE", angle_limit=math.radians(40))


def on_surface(az, el, lift=0.0):
    d = direction(az, el)
    hit, normal, _, _ = bvh.ray_cast(d * 3.0, -d)
    if hit is None:
        return shell_point(d) * (1 + lift), d
    return hit + normal * lift, normal


# ------------------------------------------------------------------ layered plates

def plate(name, az0, az1, el0, el1, lift, thick, mat=IRON, gold=0.016, fili=None, nu=36, nv=14, lip=0.0):
    """An armour plate laid over the shell: a patch between two azimuths whose
    lower and upper edges may vary with azimuth, thickened, bevelled and edged in gold."""
    lo = el0 if callable(el0) else (lambda a, v=el0: v)
    hi = el1 if callable(el1) else (lambda a, v=el1: v)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            az = az0 + (az1 - az0) * i / nu
            el = lo(az) + (hi(az) - lo(az)) * j / nv
            # A lip makes the lower edge flare out, so stacked lames overlap visibly.
            row.append(bm.verts.new(on_surface(az, el, lift + lip * (1 - j / nv) ** 3)[0]))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (di, dj) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                loop[uv].uv = ((i + di) / nu, (j + dj) / nv)
    ob = mesh_obj(name, bm, mat)
    mod(ob, "SOLIDIFY", thickness=thick, offset=1)
    mod(ob, "BEVEL", width=thick * 0.35, segments=2, limit_method="ANGLE")
    if gold:
        edge = [(az0 + (az1 - az0) * i / nu, lo(az0 + (az1 - az0) * i / nu), 1 - 0) for i in range(nu + 1)]
        edge = [(az0 + (az1 - az0) * i / nu, lo(az0 + (az1 - az0) * i / nu), lip) for i in range(nu + 1)]
        edge += [(az1, lo(az1) + (hi(az1) - lo(az1)) * j / nv, lip * (1 - j / nv) ** 3) for j in range(1, nv + 1)]
        edge += [(az1 - (az1 - az0) * i / nu, hi(az1 - (az1 - az0) * i / nu), 0) for i in range(1, nu + 1)]
        edge += [(az0, hi(az0) - (hi(az0) - lo(az0)) * j / nv, lip * (j / nv) ** 3) for j in range(1, nv)]
        pts = [on_surface(a, e, lift + l + thick * 0.9)[0] for a, e, l in edge]
        curve_obj(name + "_gold", pts, gold, GOLD, cyclic=True)
    if fili:
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new()
        m, k = 0.12, 1 - 0.24
        g = [[bm.verts.new(on_surface(az0 + (az1 - az0) * (m + k * i / nu), lo(az0) + (hi(az0) - lo(az0)) * (m + k * j / nv), lift + thick + 0.004)[0]) for i in range(nu + 1)] for j in range(nv + 1)]
        for j in range(nv):
            for i in range(nu):
                f = bm.faces.new((g[j][i], g[j][i + 1], g[j + 1][i + 1], g[j + 1][i]))
                for loop, (di, dj) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    loop[uv].uv = ((i + di) / nu * fili[0], (j + dj) / nv * fili[1])
        mesh_obj(name + "_fili", bm, FILI)
    return ob


# Visor surround: a thick iron frame with a heavy gold lip.
pts = [on_surface(a * 1.07, e + (2.5 if e > -26 else -2.5), 0.03)[0] for a, e in VISOR]
curve_obj("visor_frame", pts, 0.055, IRON, cyclic=True)
pts = [on_surface(a * 1.07, e + (2.5 if e > -26 else -2.5), 0.075)[0] for a, e in VISOR]
curve_obj("visor_frame_gold", pts, 0.024, GOLD, cyclic=True)

# Heavy overhanging brow that follows the pointed arch, with filigree.
plate("brow", -44, 44, lambda a: visor_top(a * 0.75) + 4, lambda a: visor_top(a * 0.75) + 20, 0.03, 0.05, gold=0.02, fili=(3.0, 0.6), lip=0.07)

# Stacked cheek lames either side of the visor, lower ones flaring over the upper.
for side in (-1, 1):
    for k, (e0, e1) in enumerate(((-6, 12), (-22, -2), (-38, -18))):
        a0, a1 = (34, 100) if side > 0 else (-100, -34)
        plate(f"cheek_{side}_{k}", a0, a1, e0, e1, 0.02 + 0.016 * k, 0.035, gold=0.014, fili=(2.2, 0.6) if k == 1 else None, lip=0.05)

# Chin plate (bevor) under the visor, riding over the lowest cheek lames.
plate("bevor", -40, 40, -46, -27, 0.07, 0.045, gold=0.02, fili=(2.5, 0.5), lip=0.06)

# Crown: gold-edged segments between ribs, the front pair carrying gothic tracery.
for i, (a0, a1) in enumerate(((-34, -8), (8, 34))):
    plate(f"crown_front_{i}", a0, a1, lambda a: visor_top(a * 0.75) + 26, 66, 0.012, 0.025, gold=0.014, fili=(0.8, 1.2))
for i, (a0, a1) in enumerate(((-100, -44), (44, 100))):
    plate(f"crown_side_{i}", a0, a1, 18, 58, 0.012, 0.025, gold=0.014)

# Keel crest over the crown: an iron fin with a gold spine.
bm = bmesh.new()
rows = []
for i in range(41):
    el = 14 + i * (190 - 14) / 40
    az = 0 if el <= 90 else 180
    e = el if el <= 90 else 180 - el
    p, nrm = on_surface(az, e, 0.0)
    h = 0.22 * math.sin(math.pi * min(1, (el - 14) / 150)) ** 0.6 + 0.03
    rows.append((p, nrm, h))
fin_top = []
for k, (p, nrm, h) in enumerate(rows):
    side = Vector((1, 0, 0)) * 0.04
    vs = [bm.verts.new(p - side), bm.verts.new(p + nrm * h - side * 0.3), bm.verts.new(p + nrm * h + side * 0.3), bm.verts.new(p + side)]
    fin_top.append(p + nrm * (h + 0.006))
    rows[k] = vs
for a, b2 in zip(rows, rows[1:]):
    for i in range(3):
        bm.faces.new((a[i], a[i + 1], b2[i + 1], b2[i]))
fin = mesh_obj("crest_fin", bm, IRON)
mod(fin, "SOLIDIFY", thickness=0.012)
mod(fin, "BEVEL", width=0.006, segments=2)
curve_obj("trim_crest", fin_top, 0.016, GOLD)
for k in range(1, 9):
    # Gold studs down the crest's flanks.
    p, nrm, _ = None, None, None
    el = 20 + k * 18
    az = 0 if el <= 90 else 180
    e = el if el <= 90 else 180 - el
    for sx in (-1, 1):
        q, nq = on_surface(az + sx * 4, e, 0.01)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.016, location=q, segments=12, ring_count=8)
        bpy.context.object.data.materials.append(GOLD)
        bpy.ops.object.shade_smooth()

# Gold fluting ribs over the back of the skull.
for az in (-150, -125, 125, 150, 180):
    pts = [on_surface(az + (0 - az) * 0.12 * (k / 20) ** 2, -30 + 105 * k / 20, 0.0)[0] for k in range(21)]
    curve_obj(f"flute_{az}", pts, 0.024, IRON)
    curve_obj(f"flute_gold_{az}", [on_surface(az + (0 - az) * 0.12 * (k / 20) ** 2, -30 + 105 * k / 20, 0.022)[0] for k in range(21)], 0.009, GOLD)

# Gold band round the bottom edge, with rivets.
pts = [on_surface(i * 360 / 120, -40, 0.0)[0] for i in range(120)]
curve_obj("trim_rim", [Vector((p.x * 1.03, p.y * 1.03, -0.72)) for p in pts], 0.04, GOLD, cyclic=True)
for i in range(32):
    az = i * 360 / 32
    if -104 < ((az + 180) % 360 - 180) < 104:
        continue
    p, nrm = on_surface(az, -30, 0.0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.02, location=p, segments=12, ring_count=8)
    bpy.context.object.data.materials.append(GOLD)
    bpy.ops.object.shade_smooth()

# ------------------------------------------------------------------ visor grille and glow

for i in range(15):
    az = -28 + i * 56 / 14
    top = visor_top(az) + 2
    pts = [on_surface(az, -28 + (top + 28) * k / 14, -0.03)[0] for k in range(15)]
    curve_obj(f"grille_{i}", pts, 0.011, IRON)
pts = [on_surface(-32 + 64 * k / 24, -10, -0.035)[0] for k in range(25)]
curve_obj("grille_eye", pts, 0.016, IRON)

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(0, 0.08, -0.12), segments=32, ring_count=16)
bpy.context.object.data.materials.append(GLOW)
bpy.ops.object.light_add(type="POINT", location=(0, -0.55, -0.15))
lamp = bpy.context.object
lamp.data.energy = 4
lamp.data.color = (1.0, 0.45, 0.12)
lamp.data.shadow_soft_size = 0.2

# ------------------------------------------------------------------ collar and shoulders

def lathe(name, prof, a0, a1, seg, mat, sx=1.0, sy=1.0):
    bm = bmesh.new()
    rings = []
    for s in range(seg + 1):
        a = math.radians(a0 + (a1 - a0) * s / seg)
        rings.append([bm.verts.new((math.sin(a) * r * sx, -math.cos(a) * r * sy, z)) for r, z in prof])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(len(prof) - 1):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
    return mesh_obj(name, bm, mat)


# A high flared collar round the back and sides, open at the front.
collar_prof = [(0.70, -1.25), (0.80, -0.95), (0.95, -0.62), (1.06, -0.38)]
col = lathe("collar", collar_prof, 105, 255, 64, IRON, 1.0, 1.08)
mod(col, "SOLIDIFY", thickness=0.05)
mod(col, "SUBSURF", levels=1, render_levels=2)
mod(col, "BEVEL", width=0.01, segments=2)
rim_pts = [Vector((math.sin(math.radians(a)) * 1.09, -math.cos(math.radians(a)) * 1.09 * 1.08, -0.375)) for a in range(105, 256, 3)]
curve_obj("collar_gold", rim_pts, 0.028, GOLD)
for a in range(110, 255, 18):
    # Vertical gold ribs on the collar.
    pts = [Vector((math.sin(math.radians(a)) * (r + 0.04), -math.cos(math.radians(a)) * (r + 0.04) * 1.08, z)) for r, z in collar_prof]
    curve_obj(f"collar_rib_{a}", pts, 0.012, GOLD)

# Neck, mostly hidden.
bpy.ops.mesh.primitive_cylinder_add(radius=0.42, depth=0.8, location=(0, 0.05, -1.05))
bpy.context.object.data.materials.append(IRON)

# Pauldron domes at the frame's edges, out of focus, as in the concept crop.
for sx in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(sx * 1.75, 0.15, -1.45), segments=48, ring_count=24)
    pd = bpy.context.object
    pd.scale = (0.95, 1.05, 0.75)
    pd.data.materials.append(IRON)
    bpy.ops.object.shade_smooth()
    for k, r in enumerate((0.98, 0.78)):
        pts = [Vector((sx * 1.75 + math.cos(math.radians(a)) * r * 0.95 * 1.01, 0.15 + math.sin(math.radians(a)) * r * 1.05 * 1.01, -1.45 + math.sqrt(max(0, 1 - r * r)) * 0.75 + 0.01)) for a in range(0, 360, 4)]
        curve_obj(f"pauldron_gold_{sx}_{k}", pts, 0.03, GOLD, cyclic=True)

# ------------------------------------------------------------------ cathedral canopy behind

def pinnacle(x, y, h, w=0.22):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2 - 0.9))
    t = bpy.context.object
    t.scale = (w, w, h)
    t.data.materials.append(IRON)
    mod(t, "BEVEL", width=0.01, segments=2)
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=w * 0.78, depth=0.9, location=(x, y, h - 0.9 + 0.45))
    bpy.context.object.data.materials.append(IRON)
    mod(bpy.context.object, "BEVEL", width=0.008, segments=2)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(x, y, h - 0.9 + 0.92))
    bpy.context.object.data.materials.append(GOLD)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, y - w / 2 - 0.002, h - 1.3))
    win = bpy.context.object
    win.rotation_euler = (math.pi / 2, 0, 0)
    win.scale = (w * 0.32, 0.24, 1)
    win.data.materials.append(WINDOW)
    for dx in (-w * 0.45, w * 0.45):
        for dy in (-w * 0.45, w * 0.45):
            bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.035, depth=0.28, location=(x + dx, y + dy, h - 0.9 + 0.14))
            bpy.context.object.data.materials.append(IRON)
    hw = w / 2 + 0.006
    for z in (h - 0.9, h - 1.55, h - 2.1):
        curve_obj("band", [Vector((x + hw * cx, y + hw * cy, z)) for cx, cy in ((-1, -1), (1, -1), (1, 1), (-1, 1))], 0.012, GOLD, cyclic=True)


pinnacle(-0.95, 0.6, 1.7)
pinnacle(0.95, 0.6, 1.7)
pinnacle(-0.55, 1.05, 2.3)
pinnacle(0.55, 1.05, 2.3)
pinnacle(0.0, 1.35, 2.9, 0.26)

# A pointed arch between the rear pinnacles, with a lit rose of tracery inside.
arch_pts = []
for i in range(41):
    s = -1 + 2 * i / 40
    arch_pts.append(Vector((0.44 * s, 1.0, 0.55 + 0.85 * (1 - abs(s) ** 1.7))))
curve_obj("canopy_arch", arch_pts, 0.05, IRON)
curve_obj("canopy_arch_gold", [p + Vector((0, -0.05, 0)) for p in arch_pts], 0.018, GOLD)
bpy.ops.mesh.primitive_circle_add(vertices=48, radius=0.2, fill_type="NGON", location=(0, 1.04, 0.95))
rose = bpy.context.object
rose.rotation_euler = (math.pi / 2, 0, 0)
rose.data.materials.append(WINDOW)
for k in range(8):
    a = k * math.pi / 4
    curve_obj(f"rose_spoke_{k}", [Vector((0, 1.0, 0.95)), Vector((math.cos(a) * 0.2, 1.0, 0.95 + math.sin(a) * 0.2))], 0.01, GOLD)
curve_obj("rose_ring", [Vector((math.cos(a / 24 * 2 * math.pi) * 0.21, 1.0, 0.95 + math.sin(a / 24 * 2 * math.pi) * 0.21)) for a in range(24)], 0.016, GOLD, cyclic=True)

# Embers drifting far behind, to bloom into bokeh.
EMBER = emission_material("glow_ember", (1.0, 0.3, 0.05, 1), 6)
for k in range(18):
    x = math.sin(k * 12.9898) * 4.5
    z = math.sin(k * 78.233) * 3.0 + 0.5
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03 + 0.03 * abs(math.sin(k * 3.7)), location=(x, 9 + 3 * abs(math.sin(k * 5.1)), z), segments=8, ring_count=6)
    bpy.context.object.data.materials.append(EMBER)

# ------------------------------------------------------------------ world, lights, camera

world = bpy.data.worlds.new("smoke")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
bg = wn["Background"]
grad = wn.new("ShaderNodeTexGradient")
coord = wn.new("ShaderNodeTexCoord")
ramp = wn.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.008, 1)
ramp.color_ramp.elements[1].color = (0.05, 0.05, 0.06, 1)
sep = wn.new("ShaderNodeSeparateXYZ")
world.node_tree.links.new(coord.outputs["Generated"], sep.inputs[0])
mr = wn.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = -0.2
mr.inputs["From Max"].default_value = 0.8
world.node_tree.links.new(sep.outputs["Z"], mr.inputs["Value"])
world.node_tree.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
world.node_tree.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0


def area(name, loc, energy, colour, size):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.data.energy = energy
    l.data.color = colour
    l.data.size = size
    direction_ = Vector((0, 0, 0.1)) - Vector(loc)
    l.rotation_euler = direction_.to_track_quat("-Z", "Y").to_euler()
    return l


area("key", (-3.2, -3.0, 2.2), 520, (1.0, 0.86, 0.70), 2.0)   # warm overcast key, high left
area("rim", (3.0, 3.0, 1.6), 1400, (0.75, 0.82, 1.0), 1.0)      # cool rim from behind right
area("fill", (3.0, -4.0, -1.2), 70, (0.6, 0.65, 0.8), 3.0)     # faint bounce under the jaw
area("top", (0, 1.0, 4.5), 90, (0.9, 0.9, 1.0), 1.5)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 60
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 2.2
cam = link(bpy.data.objects.new("cam", cam_data))
a = math.radians(ANGLE)
cam.location = Vector((math.sin(a) * 8.0, -math.cos(a) * 8.0, -0.2))
target = Vector((0, 0, 0.25))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_data.dof.focus_distance = (target - cam.location).length - 0.9
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x = 720
scene.render.resolution_y = 1100
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Punchy"
scene.render.filepath = str(OUT / f"helm-raw-{int(ANGLE)}.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "helm.blend"))
