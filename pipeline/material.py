"""The glTF material every pipeline GLB carries. Standard library only, so the patch script can
run outside the container.

A primitive with no material gets glTF's default, which is fully metallic: it shows no diffuse
colour and only reflects its surroundings, so viewers that light a model with lamps alone
(Babylon.js without an environment) render the stone dark. This is a plain non-metallic material
with a white base colour, so the vertex colours alone set the colour. Roughness matches the
thumbnail render's material (render/render_thumbs.py).
"""

MATERIAL = {"name": "Stone", "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 0.8}}


def add_material(tree):
    """Use MATERIAL for every primitive of a glTF JSON tree, in place. Also serves as a trimesh
    export tree_postprocessor."""
    tree["materials"] = [MATERIAL]
    for mesh in tree["meshes"]:
        for primitive in mesh["primitives"]:
            primitive["material"] = 0


def has_material(tree):
    """Whether every primitive has an explicitly non-metallic material."""
    for mesh in tree["meshes"]:
        for primitive in mesh["primitives"]:
            if "material" not in primitive:
                return False
            pbr = tree["materials"][primitive["material"]].get("pbrMetallicRoughness", {})
            if pbr.get("metallicFactor", 1.0) != 0:
                return False
    return True
