"""
Blender headless script: render a GLB with vertex colours to a PNG thumbnail.

Usage (called by pipeline.sh or render_thumbs.sh, not directly):
    blender --background --python render_thumbs.py -- <input.glb> <output.png>

Camera faces the model front (-Y, as oriented by positioning.py UZY algorithm)
with slight elevation. Renders with a shadow-catcher plane and transparent
background so the drop shadow composites naturally in the browser/Omeka.
Render size: 512x512. Output: PNG RGBA.
"""

import bpy
import sys
import math
from mathutils import Vector


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=True)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)


def import_glb(filepath):
    bpy.ops.import_scene.gltf(filepath=filepath)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        raise RuntimeError(f"No mesh objects found in {filepath}")
    return meshes


def get_bounding_box(objects):
    """Return world-space min/max corners across all given mesh objects."""
    all_corners = []
    for obj in objects:
        for corner in obj.bound_box:
            all_corners.append(obj.matrix_world @ Vector(corner))
    mins = Vector((min(v.x for v in all_corners),
                   min(v.y for v in all_corners),
                   min(v.z for v in all_corners)))
    maxs = Vector((max(v.x for v in all_corners),
                   max(v.y for v in all_corners),
                   max(v.z for v in all_corners)))
    return mins, maxs


def setup_vertex_colour_material(obj):
    """Assign a material that renders vertex colours (Col attribute)."""
    mat = bpy.data.materials.new(name="VertexColour")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    vc_node = nodes.new('ShaderNodeVertexColor')
    vc_node.layer_name = 'Col'

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.8
    bsdf.inputs['Specular IOR Level'].default_value = 0.1

    output = nodes.new('ShaderNodeOutputMaterial')

    links.new(vc_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    obj.data.materials.clear()
    obj.data.materials.append(mat)


def setup_camera(mins, maxs):
    """Position camera facing the model front (-Y axis), with slight elevation.

    After positioning.py (UZY), the face of the artifact is toward -Z in glTF
    space, which Blender imports as -Y. Camera sits at azimuth 0° (straight
    ahead along -Y) with a small elevation to show some top surface.
    """
    centre = (mins + maxs) / 2
    size = (maxs - mins).length

    # 0° azimuth (straight -Y), 20° elevation
    angle_az = math.radians(0)
    angle_el = math.radians(20)
    distance = size * 1.3

    cam_x = centre.x + distance * math.cos(angle_el) * math.sin(angle_az)
    cam_y = centre.y - distance * math.cos(angle_el) * math.cos(angle_az)
    cam_z = centre.z + distance * math.sin(angle_el)

    bpy.ops.object.camera_add(location=(cam_x, cam_y, cam_z))
    cam_obj = bpy.context.object
    bpy.context.scene.camera = cam_obj

    # Point camera at bounding box centre
    direction = Vector((centre.x - cam_x, centre.y - cam_y, centre.z - cam_z))
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    cam_obj.data.type = 'PERSP'
    cam_obj.data.lens = 50
    return cam_obj


def setup_lighting(centre, size):
    """Directional lighting to match GLTFViewer: dominant key from upper-left-front,
    weak fill from right, minimal rim. Gives contrast and preserves vertex colour warmth."""

    # Key light: upper-left-front (strong, warm amber)
    bpy.ops.object.light_add(type='SUN', location=(
        centre.x - size * 1.5, centre.y - size * 1.5, centre.z + size))
    key = bpy.context.object
    key.data.energy = 2.5
    key.data.color = (1.0, 0.90, 0.75)  # warm amber
    key.rotation_euler = (math.radians(75), 0, math.radians(-45))

    # Fill light: right side, very dim (deep shadows)
    bpy.ops.object.light_add(type='SUN', location=(
        centre.x + size * 2, centre.y - size, centre.z + size * 0.3))
    fill = bpy.context.object
    fill.data.energy = 0.15
    fill.data.color = (0.8, 0.9, 1.0)  # slightly cool to contrast key
    fill.rotation_euler = (math.radians(20), 0, math.radians(60))

    # Rim light: from behind-above to separate model from background
    bpy.ops.object.light_add(type='SUN', location=(
        centre.x, centre.y + size * 2, centre.z + size * 0.5))
    rim = bpy.context.object
    rim.data.energy = 0.15
    rim.data.color = (1.0, 1.0, 1.0)
    rim.rotation_euler = (math.radians(-30), 0, math.radians(180))



def add_shadow_catcher(mins, centre, size):
    """Add a horizontal plane just below the model that catches shadows only."""
    z = mins.z - size * 0.02
    bpy.ops.mesh.primitive_plane_add(size=size * 3, location=(centre.x, centre.y, z))
    plane = bpy.context.object
    plane.is_shadow_catcher = True
    mat = bpy.data.materials.new(name="ShadowCatcher")
    mat.use_nodes = True
    plane.data.materials.append(mat)
    return plane


def setup_render(output_path):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    # Use transparent film so shadow catcher composites onto background colour
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.compression = 9
    scene.render.filepath = output_path
    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.42, 0.42, 0.42, 1)
    bg.inputs['Strength'].default_value = 0.05
    # AgX gives better colour saturation than Filmic; bump exposure slightly
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0.3
    scene.view_settings.gamma = 1.0


def main():
    argv = sys.argv
    try:
        sep = argv.index('--')
    except ValueError:
        print("ERROR: pass arguments after --", file=sys.stderr)
        sys.exit(1)

    args = argv[sep + 1:]
    if len(args) < 2:
        print("Usage: blender --background --python render_thumbs.py -- <input.glb> <output.jpg>",
              file=sys.stderr)
        sys.exit(1)

    glb_path, out_path = args[0], args[1]

    clear_scene()
    meshes = import_glb(glb_path)

    for obj in meshes:
        if obj.data.vertex_colors:
            setup_vertex_colour_material(obj)

    mins, maxs = get_bounding_box(meshes)
    centre = (mins + maxs) / 2
    size = (maxs - mins).length

    setup_camera(mins, maxs)
    setup_lighting(centre, size)
    add_shadow_catcher(mins, centre, size)
    setup_render(out_path)

    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {out_path}")


main()
