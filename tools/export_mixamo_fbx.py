"""Blender 后台：OBJ → Mixamo 用 FBX（仅网格，无灯/相机/骨骼）。

blender --background --python tools/export_mixamo_fbx.py
"""
import bpy
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBJ = os.path.join(ROOT, 'assets', 'output', 'Ultraman_Classic.obj')
FBX = os.path.join(ROOT, 'assets', 'output', 'Ultraman_Classic.fbx')

bpy.ops.wm.read_factory_settings(use_empty=True)
# 默认 OBJ 导入：文件 Y-up/+Z 朝向 → Blender Z-up / -Y 朝向（再导出成 Mixamo 的 Y-up/+Z）
bpy.ops.import_scene.obj(filepath=OBJ, use_smooth_groups=True, use_split_objects=False,
                         use_split_groups=False, use_image_search=False)

# 只留网格，合并成一个物体
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
if meshes:
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = 'UltramanClassic'
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    # 法线
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.export_scene.fbx(
    filepath=FBX,
    use_selection=True,
    object_types={'MESH'},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    axis_forward='-Z',
    axis_up='Y',
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',
    path_mode='COPY',
    embed_textures=True,
)
print('FBX', FBX, 'bytes', os.path.getsize(FBX))
