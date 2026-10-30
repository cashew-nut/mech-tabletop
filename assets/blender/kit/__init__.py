"""The war-walker kit: everything a part script needs to build a part in
headless Blender and ship it to the web game. Read README.md in this folder
for the conventions and a worked example.

    import bpy                      # before bmesh, always
    import kit
    kit.reset_scene()
    mats = kit.materials.library("covenant")
    frame = kit.skeleton.build_frame("covenant", "titan")
    ...
    kit.publish(root)               # bake, export GLB, update the manifest

Modules:
    core       names, scene and object helpers
    materials  the three faction material libraries
    textures   generated relief and stencil masks
    shapes     plates, trim, rivets, spires, lancets, pipes and the Shell
    skeleton   the four frames, their joints, sockets and mounts
    bake       node materials to base colour, ORM and normal textures
    export     GLB export and manifest updates
    render     Cycles review renders and art comparisons
"""
from . import core, materials, shapes, textures  # noqa: F401
from .core import *  # noqa: F401,F403
from . import bake, skeleton, export, render  # noqa: F401,E402
from .export import publish  # noqa: F401,E402
