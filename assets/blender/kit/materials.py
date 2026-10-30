"""Node-based material libraries for the three factions.

    mat = materials.get("covenant", "armour")

Roles every faction has:

    armour    the main plate (Covenant blackened iron, Foundries rusted plate,
              Reliquary bone ceramic)
    trim      edging and raised detail (aged gold, oxidised brass, pale gold)
    filigree  armour with a raised inlay of trim in the faction's relief
              pattern, laid out by the "Decal" UV map
    metal     joints, pistons, cables and the skeleton underneath
    hull      the paintable enamel panels (recoloured by the Company livery)
    cloth     banners, tarps and shrouds (also recoloured)
    glow      visors, furnaces, windows and eyes (emissive, never baked)
    stencil   enamel with a sprayed stencil number from the "Decal" UV map
              (not repainted, so the number stays bone-white)

Every material is one Principled BSDF fed by a stack of layers that share
the same wear masks (worn edges, grime in the cavities, dust on upward faces)
in world millimetres, so a part ages the same way whatever its size. That
single-BSDF shape is what bake.py relies on to carry the look into textures.

Materials whose names start with "hull" are recoloured in the web game. Their
colour comes from a node named "paint", which the bake sets to white, so the
texture holds the wear and the livery is multiplied in at runtime.
"""
import bpy

from . import textures

# ------------------------------------------------------------------ colours
# Linear RGB, sampled from the "Colour & Materials" swatches on Luke's boards
# (assets/art/crops.json: swatches_*), then tuned by eye in the test plates.

PALETTES = {
    "covenant": {
        "armour": dict(base=((0.014, 0.014, 0.016), (0.045, 0.042, 0.04)), edge=(0.45, 0.43, 0.40), metal=0.92, rough=(0.28, 0.6),
                       grime=(0.012, 0.008, 0.005), dust=(0.05, 0.045, 0.04), hammer=0.06),
        "trim": dict(base=((0.62, 0.40, 0.14), (0.80, 0.56, 0.24)), recess=(0.13, 0.065, 0.02), metal=1.0, rough=(0.22, 0.45)),
        "metal": dict(base=((0.03, 0.03, 0.032), (0.075, 0.072, 0.068)), edge=(0.45, 0.44, 0.42), metal=0.9, rough=(0.35, 0.6),
                      grime=(0.01, 0.008, 0.006), dust=(0.05, 0.045, 0.04)),
        "hull": dict(paint=(0.19, 0.006, 0.009), under="armour", rough=(0.35, 0.55)),
        "cloth": dict(paint=(0.17, 0.006, 0.01), rough=(0.75, 0.95)),
        "glow": dict(emit=(1.0, 0.30, 0.04), strength=2.5),
        "relief": "filigree",
    },
    "foundries": {
        "armour": dict(base=((0.030, 0.028, 0.026), (0.055, 0.050, 0.045)), edge=(0.30, 0.29, 0.27), metal=0.85, rough=(0.45, 0.8),
                       grime=(0.006, 0.005, 0.004), dust=(0.06, 0.05, 0.04), rust=((0.24, 0.045, 0.008), (0.45, 0.14, 0.03), 0.55),
                       hammer=0.04),
        "trim": dict(base=((0.11, 0.06, 0.022), (0.30, 0.18, 0.07)), recess=(0.03, 0.035, 0.02), metal=1.0, rough=(0.35, 0.65)),
        "metal": dict(base=((0.022, 0.021, 0.02), (0.05, 0.047, 0.043)), edge=(0.32, 0.31, 0.29), metal=0.9, rough=(0.3, 0.55),
                      grime=(0.004, 0.003, 0.002), dust=(0.05, 0.04, 0.03)),
        "hull": dict(paint=(0.26, 0.022, 0.012), under="armour", rough=(0.4, 0.7), chips=0.3),
        "cloth": dict(paint=(0.22, 0.03, 0.015), rough=(0.85, 1.0)),
        "glow": dict(emit=(1.0, 0.24, 0.02), strength=3.0),
        "relief": "tread",
    },
    "reliquary": {
        "armour": dict(base=((0.42, 0.33, 0.23), (0.60, 0.50, 0.38)), edge=(0.72, 0.65, 0.54), metal=0.0, rough=(0.28, 0.5),
                       grime=(0.035, 0.022, 0.012), dust=(0.36, 0.32, 0.26), crackle=0.5),
        "trim": dict(base=((0.45, 0.30, 0.13), (0.78, 0.60, 0.34)), recess=(0.09, 0.055, 0.025), metal=1.0, rough=(0.22, 0.42)),
        "metal": dict(base=((0.018, 0.025, 0.028), (0.075, 0.062, 0.05)), edge=(0.30, 0.30, 0.28), metal=0.85, rough=(0.35, 0.6),
                      grime=(0.01, 0.008, 0.006), dust=(0.12, 0.11, 0.09)),
        "hull": dict(paint=(0.035, 0.085, 0.085), under="metal", rough=(0.3, 0.5)),
        "cloth": dict(paint=(0.40, 0.38, 0.34), rough=(0.8, 0.95)),
        "glow": dict(emit=(0.15, 0.85, 0.75), strength=2.5),
        "relief": "glyphs",
    },
}

FACTIONS = tuple(PALETTES)
ROLES = ("armour", "trim", "filigree", "metal", "hull", "cloth", "glow", "stencil")

# Wear features in world millimetres. A 12 m walker stands about 50 mm tall,
# so 1 mm is about a quarter of a metre: chips are a fraction of a millimetre.
EDGE_MM = 0.08       # how far the worn-edge highlight reaches round a corner
CAVITY_MM = 0.7      # how far grime collects into recesses
BLOTCH = 0.22        # noise scale (per mm) of oil and soot blotches
CHIP = 5.0           # noise scale of edge chipping
DUST = 1.3           # noise scale of the dust pattern


class Graph:
    """A thin wrapper over a material's node tree. Arguments that are numbers
    or tuples become default values; sockets are linked."""

    def __init__(self, mat):
        self.mat = mat
        self.nt = mat.node_tree
        self.N, self.L = self.nt.nodes, self.nt.links
        self.geo = self.N.new("ShaderNodeNewGeometry")

    def _in(self, sock, v):
        if v is None:
            return
        if hasattr(v, "is_output") or isinstance(v, bpy.types.NodeSocket):
            self.L.new(v, sock)
        else:
            if isinstance(v, tuple) and len(v) == 3 and len(sock.default_value) == 4:
                v = (*v, 1.0)
            sock.default_value = v

    def node(self, kind, **props):
        n = self.N.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def noise(self, scale, detail=6.0, rough=0.55, vec=None):
        n = self.node("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        self.L.new(vec or self.geo.outputs["Position"], n.inputs["Vector"])
        return n.outputs["Fac"]

    def voronoi(self, scale, feature="F1", out="Distance"):
        n = self.node("ShaderNodeTexVoronoi", feature=feature)
        n.inputs["Scale"].default_value = scale
        self.L.new(self.geo.outputs["Position"], n.inputs["Vector"])
        return n.outputs[out]

    def range(self, v, a, b, c=0.0, d=1.0, clamp=True):
        n = self.node("ShaderNodeMapRange", clamp=clamp)
        self._in(n.inputs["Value"], v)
        for k, x in zip(("From Min", "From Max", "To Min", "To Max"), (a, b, c, d)):
            n.inputs[k].default_value = x
        return n.outputs["Result"]

    def math(self, op, a, b=0.0, clamp=True):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self._in(n.inputs[0], a)
        self._in(n.inputs[1], b)
        return n.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        """Mix two colours (3-tuples or colour sockets)."""
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_result=True)
        self._in(n.inputs[0], fac)
        self._in(n.inputs[6], a)
        self._in(n.inputs[7], b)
        return n.outputs[2]

    def mixf(self, fac, a, b):
        n = self.node("ShaderNodeMix", data_type="FLOAT")
        self._in(n.inputs[0], fac)
        self._in(n.inputs[2], a)
        self._in(n.inputs[3], b)
        return n.outputs[0]

    def rgb(self, colour, name=None):
        n = self.node("ShaderNodeRGB")
        n.outputs[0].default_value = (*colour, 1.0)
        if name:
            n.name = n.label = name
        return n.outputs[0]

    def image(self, path, uv="Decal"):
        n = self.node("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path, check_existing=True)
        n.image.colorspace_settings.name = "Non-Color"
        m = self.node("ShaderNodeUVMap", uv_map=uv)
        self.L.new(m.outputs["UV"], n.inputs["Vector"])
        return n.outputs["Color"]

    # -------------------------------------------------- wear masks

    def edges(self, mm=EDGE_MM):
        """1 on sharp convex and concave edges, from the bevel-normal trick."""
        bev = self.node("ShaderNodeBevel")
        bev.inputs["Radius"].default_value = mm
        dot = self.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        self.L.new(bev.outputs["Normal"], dot.inputs[0])
        self.L.new(self.geo.outputs["Normal"], dot.inputs[1])
        self.bevel = bev
        return self.range(dot.outputs["Value"], 0.995, 0.90)

    def cavity(self, mm=CAVITY_MM):
        """1 in the open, falling towards 0 in recesses."""
        ao = self.node("ShaderNodeAmbientOcclusion", samples=8)
        ao.inputs["Distance"].default_value = mm
        return ao.outputs["AO"]

    def upward(self):
        sep = self.node("ShaderNodeSeparateXYZ")
        self.L.new(self.geo.outputs["Normal"], sep.inputs[0])
        return sep.outputs["Z"]

    def wear(self, amount=1.0):
        """Chipped edges: the edge mask broken up with noise."""
        chips = self.range(self.noise(CHIP, 6), 0.36, 0.62)
        return self.math("MULTIPLY", self.math("MULTIPLY", self.edges(), chips), amount)

    def dust(self):
        up = self.range(self.upward(), 0.35, 0.95, 0, 0.5)
        return self.math("MULTIPLY", up, self.range(self.noise(DUST, 10), 0.4, 0.7))


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m


def _finish(g, colour, rough, metal, height=None, bump=0.05, emit=None):
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    out = g.node("ShaderNodeOutputMaterial")
    g._in(bsdf.inputs["Base Color"], colour)
    g._in(bsdf.inputs["Roughness"], rough)
    g._in(bsdf.inputs["Metallic"], metal)
    if emit:
        g._in(bsdf.inputs["Emission Color"], emit[0])
        bsdf.inputs["Emission Strength"].default_value = emit[1]
    normal = getattr(g, "bevel", None)
    if height is not None:
        b = g.node("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.05
        g._in(b.inputs["Height"], height)
        if normal is not None:
            g.L.new(normal.outputs["Normal"], b.inputs["Normal"])
        normal = b
    if normal is not None:
        g.L.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    g.L.new(bsdf.outputs[0], out.inputs["Surface"])
    return bsdf


def _metal_layers(g, spec):
    """Colour, roughness, metallic and height sockets for a worn metal or ceramic plate."""
    blot = g.noise(BLOTCH, 8)
    colour = g.mix(blot, *spec["base"])
    if "rust" in spec:
        dark, bright, amount = spec["rust"]
        # Rust blooms in recesses and in big patches, brightest at the patch centres.
        patch = g.range(g.noise(BLOTCH * 2.5, 10, 0.65), 0.62 - amount * 0.22, 0.68)
        cav = g.range(g.cavity(), 0.9, 0.5)
        rmask = g.math("MAXIMUM", patch, g.math("MULTIPLY", cav, 0.85))
        rcol = g.mix(g.noise(CHIP * 0.6, 8), dark, bright)
        colour = g.mix(rmask, colour, rcol)
    else:
        rmask = None
    colour = g.mix(g.cavity(), spec["grime"], colour)
    worn = g.wear()
    colour = g.mix(worn, colour, spec["edge"])
    dust = g.dust()
    colour = g.mix(dust, colour, spec["dust"])
    rough = g.range(blot, 0, 1, *spec["rough"])
    rough = g.mixf(worn, rough, spec["rough"][0] * 0.5)
    rough = g.mixf(dust, rough, 0.92)
    metal = spec["metal"]
    if rmask is not None:
        rough = g.mixf(rmask, rough, 0.9)
        metal = g.mixf(rmask, metal, 0.15)
    if spec["metal"] < 0.5:
        metal = g.mixf(worn, metal, 0.0)
    height = None
    if spec.get("hammer"):
        height = g.math("MULTIPLY", g.voronoi(3.0), spec["hammer"])
    if spec.get("crackle"):
        # Crazed glaze: fine voronoi cracks, dark and slightly sunken.
        crack = g.range(g.voronoi(6.0, "DISTANCE_TO_EDGE"), 0.0, 0.05, 1, 0)
        colour = g.mix(g.math("MULTIPLY", crack, spec["crackle"]), colour, spec["grime"])
        height = g.math("MULTIPLY", crack, -0.3)
    return colour, rough, metal, height


def _trim_layers(g, spec):
    """Gold or brass: bright where raised, tarnished in the recesses."""
    shine = g.mix(g.noise(BLOTCH * 2, 6), *spec["base"])
    colour = g.mix(g.range(g.cavity(CAVITY_MM * 0.6), 0.35, 1.0), spec["recess"], shine)
    colour = g.mix(g.wear(0.6), colour, tuple(min(1.0, c * 1.25) for c in spec["base"][1]))
    rough = g.range(g.noise(CHIP * 0.8, 4), 0, 1, *spec["rough"])
    g.edges()  # gives the trim the bevelled-normal highlight too
    return colour, rough, spec["metal"], None


def _relief_path(faction):
    return {"filigree": textures.filigree, "tread": textures.tread_plate, "glyphs": textures.glyphs}[PALETTES[faction]["relief"]]()


def _armour(faction, name):
    m = _new(name)
    g = Graph(m)
    _finish(g, *_metal_layers(g, PALETTES[faction]["armour"]))
    return m


def _trim(faction, name):
    m = _new(name)
    g = Graph(m)
    _finish(g, *_trim_layers(g, PALETTES[faction]["trim"]))
    return m


def _metal(faction, name):
    m = _new(name)
    g = Graph(m)
    _finish(g, *_metal_layers(g, PALETTES[faction]["metal"]))
    return m


def _filigree(faction, name):
    """Armour with a raised inlay of trim where the relief mask is white."""
    m = _new(name)
    g = Graph(m)
    c0, r0, m0, h0 = _metal_layers(g, PALETTES[faction]["armour"])
    c1, r1, m1, _ = _trim_layers(g, PALETTES[faction]["trim"])
    mask = g.range(g.image(_relief_path(faction)), 0.25, 0.6)
    colour = g.mix(mask, c0, c1)
    rough = g.mixf(mask, r0, r1)
    metal = g.mixf(mask, m0, m1)
    height = g.math("ADD", mask, h0 if h0 is not None else 0.0)
    _finish(g, colour, rough, metal, height, bump=0.35)
    return m


def _hull(faction, name, decal=None, paintable=True):
    """Enamel over the faction's plate, chipped back to metal at the edges.
    Its colour is the "paint" node (white while baking). A stencilled plate
    is not paintable: the livery would tint its number too."""
    pal = PALETTES[faction]
    spec = pal["hull"]
    m = _new(name)
    g = Graph(m)
    uc, ur, um, uh = _metal_layers(g, pal[spec["under"]])
    paint = g.rgb(spec["paint"], "paint" if paintable else "enamel")
    # Paint stays out of the chips and fades with grime and dust.
    shade = g.mix(g.range(g.noise(BLOTCH * 1.5, 8), 0.2, 0.8), (0.78, 0.78, 0.78), (1.0, 1.0, 1.0))
    coat = g.mix(1.0, shade, paint, "MULTIPLY")
    coat = g.mix(g.range(g.cavity(), 0.95, 0.45), coat, g.mix(1.0, coat, (0.35, 0.33, 0.3), "MULTIPLY"))
    coat = g.mix(g.dust(), coat, g.mix(1.0, coat, (0.75, 0.72, 0.66), "MULTIPLY"))
    if decal:
        # A sprayed bone-white stencil, worn through in places.
        dm = g.math("MULTIPLY", g.range(g.image(decal), 0.3, 0.7), g.range(g.noise(CHIP, 6), 0.25, 0.5))
        coat = g.mix(dm, coat, (0.55, 0.52, 0.46))
    chips = g.math("MULTIPLY", g.range(g.noise(CHIP * 0.7, 8), 0.5, 0.62), g.math("ADD", g.edges(EDGE_MM * 3), spec.get("chips", 0.15)))
    colour = g.mix(chips, coat, uc)
    rough = g.mixf(chips, g.range(g.noise(BLOTCH * 3, 6), 0, 1, *spec["rough"]), ur)
    metal = g.mixf(chips, 0.0, um)
    height = g.math("MULTIPLY", chips, -0.4)
    _finish(g, colour, rough, metal, height if uh is None else g.math("ADD", height, uh), bump=0.08)
    return m


def _cloth(faction, name):
    spec = PALETTES[faction]["cloth"]
    m = _new(name)
    g = Graph(m)
    paint = g.rgb(spec["paint"], "paint")
    # Weave, fading, grime soaked up from the hem and sun-bleached tops.
    weave = g.range(g.voronoi(40.0), 0.0, 0.6, 0.85, 1.0)
    fade = g.mix(g.range(g.noise(BLOTCH * 2, 10), 0.3, 0.8), (0.55, 0.52, 0.5), (1.0, 1.0, 1.0))
    colour = g.mix(1.0, g.mix(1.0, paint, fade, "MULTIPLY"), g.mix(weave, (0, 0, 0), (1, 1, 1)), "MULTIPLY")
    colour = g.mix(g.range(g.cavity(), 0.9, 0.4), colour, g.mix(1.0, colour, (0.3, 0.27, 0.25), "MULTIPLY"))
    rough = g.range(g.noise(BLOTCH * 4, 4), 0, 1, *spec["rough"])
    _finish(g, colour, rough, 0.0, g.math("MULTIPLY", weave, 0.2), bump=0.1)
    m["sheen"] = True
    return m


def _glow(faction, name):
    spec = PALETTES[faction]["glow"]
    m = _new(name)
    g = Graph(m)
    _finish(g, (0.02, 0.02, 0.02), 0.4, 0.0, emit=(spec["emit"], spec["strength"]))
    m["bake"] = False  # emissive colour exports as a plain glTF factor
    return m


BUILDERS = {
    "armour": (_armour, "armour"),
    "trim": (_trim, "trim"),
    "filigree": (_filigree, "filigree"),
    "metal": (_metal, "metal"),
    "hull": (_hull, "hull_enamel"),
    "cloth": (_cloth, "hull_cloth"),
    "glow": (_glow, "glow"),
    "stencil": (lambda f, n: _hull(f, n, textures.stencil("07"), paintable=False), "stencil"),
}


def get(faction, role):
    """The faction's material for a role, created once per file.
    Names are "<base>_<faction>", for example armour_covenant, hull_enamel_foundries."""
    if faction not in PALETTES:
        raise KeyError(f"unknown faction {faction!r}; have {', '.join(PALETTES)}")
    build, base = BUILDERS[role]
    name = f"{base}_{faction}"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = build(faction, name)
        mat["kit_role"] = role
        mat["kit_faction"] = faction
    return mat


def library(faction):
    """Every role's material for a faction, as a dict."""
    return {role: get(faction, role) for role in ROLES}


def set_paint(mat, colour):
    """Change a hull material's paint (linear RGB)."""
    node = mat.node_tree.nodes.get("paint")
    if node is not None:
        node.outputs[0].default_value = (*colour, 1.0)
