"""Blender CPU：给现成网格拆 UV，不改顶点位置。

blender --background --python tools/unwrap_ultraman.py
"""
import bpy
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets', 'output', 'Ultraman_Classic.obj')
DST = os.path.join(ROOT, 'assets', 'output', '_unwrap.obj')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(
    filepath=SRC, use_smooth_groups=True, use_split_objects=False,
    use_split_groups=False, use_image_search=False)

meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()

obj = bpy.context.view_layer.objects.active
obj.name = 'UltramanClassic'
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
# 智能拆岛：角度够分、岛之间留边，避免贴图互染
bpy.ops.uv.smart_project(angle_limit=1.047, island_margin=0.024)
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.export_scene.obj(
    filepath=DST,
    use_selection=True,
    use_uvs=True,
    use_normals=True,
    use_materials=False,
    keep_vertex_order=True,
    axis_forward='-Z',
    axis_up='Y',
)
print('UNWRAP', DST, 'verts', len(obj.data.vertices), 'faces', len(obj.data.polygons))
