"""Blender Workbench 三视图。blender --background --python tools/render_ultraman.py"""
import bpy
import os
import math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBJ = os.path.join(ROOT, 'assets', 'output', 'Ultraman_Classic.obj')
OUT = os.path.join(ROOT, 'assets', 'output')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath=OBJ, use_split_objects=False, use_split_groups=False)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.studio_light = 'studio.sl'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_specular_highlight = True
scene.render.resolution_x = 720
scene.render.resolution_y = 1280
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
world = bpy.data.worlds.new('W')
scene.world = world
world.use_nodes = False
world.color = (0.04, 0.045, 0.06)

# 地面
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
# import 后角色在 Blender 里 Z-up，脚在 z=0，朝向 -Y
# 上面 axis_forward=Z 会把 OBJ +Z 映射到 Blender -Y，脚仍应在 z≈0
ground = bpy.context.active_object
mat_g = bpy.data.materials.new('Ground')
mat_g.diffuse_color = (0.07, 0.08, 0.10, 1)
ground.data.materials.append(mat_g)

cam_data = bpy.data.cameras.new('C')
cam_data.lens = 50
cam = bpy.data.objects.new('C', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

def look(eye, target=(0, 0, 0.95)):
    cam.location = eye
    direction = (target[0] - eye[0], target[1] - eye[1], target[2] - eye[2])
    cam.rotation_euler = direction_to_euler(direction)

def direction_to_euler(d):
    import mathutils
    v = mathutils.Vector(d)
    return v.to_track_quat('-Z', 'Y').to_euler()

views = {
    'blender_front.png': ((0, -4.6, 0.95), (0, 0, 0.95)),
    'blender_34.png':    ((2.8, -3.6, 1.15), (0, 0, 0.95)),
    'blender_side.png':  ((4.6, 0, 0.95), (0, 0, 0.95)),
}
for name, (eye, tgt) in views.items():
    look(eye, tgt)
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print('wrote', name)
