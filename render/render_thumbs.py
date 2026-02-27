"""
Blender headless script: render a GLB with vertex colours to a JPEG thumbnail.

Usage (called by render_thumbs.sh, not directly):
    blender --background --python render_thumbs.py -- <input.glb> <output.jpg>

The camera is auto-positioned to frame the model from a 3/4 front-top view.
Render size: 512x512. Output: JPEG quality 90.
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
    """Position camera at 3/4 front-top angle, framing the bounding box."""
    centre = (mins + maxs) / 2
    size = (maxs - mins).length

    # 45° elevation, 45° azimuth from front
    angle_az = math.radians(45)
    angle_el = math.radians(35)
    distance = size * 1.6

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
    """Match ModelViewer lighting: ambient + three equal directionals (front, left, right)."""
    # Ambient via world background strength (set in setup_render)

    # Sun lamps approximate the three camera-attached DirectionalLights in ModelViewer:
    # front (z:5), left (x:-5), right (x:5) — all intensity 5.0, white
    sun_energy = 3.0  # tuned for Cycles (ModelViewer intensity 5.0 is a Three.js scale)

    # Front light (from -Y toward origin)
    bpy.ops.object.light_add(type='SUN', location=(centre.x, centre.y - size * 2, centre.z))
    front = bpy.context.object
    front.data.energy = sun_energy
    front.rotation_euler = (math.radians(90), 0, 0)

    # Left light (from +X toward origin)
    bpy.ops.object.light_add(type='SUN', location=(centre.x + size * 2, centre.y, centre.z))
    left = bpy.context.object
    left.data.energy = sun_energy
    left.rotation_euler = (0, math.radians(-90), 0)

    # Right light (from -X toward origin)
    bpy.ops.object.light_add(type='SUN', location=(centre.x - size * 2, centre.y, centre.z))
    right = bpy.context.object
    right.data.energy = sun_energy
    right.rotation_euler = (0, math.radians(90), 0)



def setup_render(output_path):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 90
    scene.render.filepath = output_path
    # Transparent background -> grey instead
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']
    # Background matches ModelViewer #d6d6d6, darkened 50%: #6b6b6b
    bg.inputs['Color'].default_value = (0.42, 0.42, 0.42, 1)
    # Low strength to approximate ModelViewer's ambient intensity 0.1
    bg.inputs['Strength'].default_value = 0.1


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
    setup_render(out_path)

    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {out_path}")


main()
