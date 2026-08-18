# -*- coding: utf-8 -*-
"""gen_helmet_r2.py — R2 头盔：按 classic.png 像素量制（docs/acceptance/r2/head_metrics.md）

按 docs/HANDOFF_GLM.md §3.1 样品 A2：扁脸穹顶 + 头冠脊 + 耳板 + 杏仁眼凸起。
Skin 修改器分支处斜接不可控（首版下巴下垂/头顶压扁），改椭球组合+面级分区。

坐标约定：本表 (x=左右, v=纵向, d=深度前正)；Blender 是 Z 朝上 → 写入时换轴
(x, d, v)。导出 glTF 自动转 Y 朝上。
用法: blender -b -P tools/gen_helmet_a2.py   输出: assets/output/helmet_a2.glb
"""
import bpy, bmesh, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'output', 'helmet_r2.glb')
bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------- 部件表：(x, v纵向, d深度), 半径, 三轴缩放 ----------------
# 意图轮廓：纵向 -0.13(下巴)..+0.13(冠脊顶) | 左右 ±0.102 | 深度 -0.12..+0.105
# 缩放元组同样按 (x, 深度, 纵向) —— Blender 的 y=深度、z=纵向
# 尺寸全部来自 head_metrics.md（472px/m 实测）：半宽.1135/半高.0875/半深.095
PARTS = [
    ('skull',  (0, .010, -.010),  .100, (1.135, .875, .95)),   # 颅：扁面罩，前后短
    ('face',   (0, -.005,  .045), .090, (1.00, .80, .50)),     # 前脸面板（更扁）
    ('jaw',    (0, -.055,  .015), .055, (1.05, .60, .85)),     # 下颚（红区）
    ('crest',  (0, .095,  -.020), .085, (.09, .22, 1.15)),     # 冠脊：额→脑后薄刃
]

def add_sphere(name, loc_vxd, r, scale):
    x, v, d = loc_vxd
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=r,
                                         location=(x, d, v))          # (x, y=depth, z=up)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    return o

objs = []
for name, loc, r, sc in PARTS:
    objs.append(add_sphere(name, loc, r, sc))
for sd in (-1, 1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.016, depth=.014,
                                        location=(sd * .108, .000, .000))
    ear = bpy.context.active_object
    ear.name = 'ear' + ('L' if sd < 0 else 'R')
    ear.rotation_euler[1] = math.pi / 2                     # 轴向 → 左右
    objs.append(ear)

# 合并为单网格（应用缩放）
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.join()
helmet = bpy.context.active_object
helmet.name = 'UltramanHelmetR2'
bpy.ops.object.shade_smooth()

# ---------------- 材质分区（面级：前脸银 / 侧后红 / 下颚红 / 冠脊银） ----------------
def mat(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = .1
    bs.inputs['Roughness'].default_value = .5
    return m
m_sil = mat('Silver', (.75, .81, .88))
m_red = mat('Red', (.78, .10, .12))
me = helmet.data
for m in (m_sil, m_red):
    me.materials.append(m)

bm = bmesh.new()
bm.from_mesh(me)
for f in bm.faces:
    c = f.calc_center_median()          # Blender: y=深度(前+), z=纵向
    red = (c.y < -.03) or (abs(c.x) > .080) or (c.z < -.055 and c.y > -.03)
    f.material_index = 1 if red else 0
bm.to_mesh(me)
bm.free()

# ---------------- 杏仁眼凸起（独立件，发光黄） ----------------
for sd in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=.035,
                                         location=(sd * .038, .093, .005))
    e = bpy.context.active_object
    e.name = 'EyeL' if sd < 0 else 'EyeR'
    e.scale = (1.05, .45, .45)    # 量测: 单眼宽.074 高~.065(贴脸后纵径压半)
    e.rotation_euler = (0, 0, sd * .26)
    em = bpy.data.materials.new(e.name)
    em.use_nodes = True
    bs = em.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (1, .95, .72, 1)
    bs.inputs['Emission'].default_value = (1, .92, .6, 1)
    bs.inputs['Emission Strength'].default_value = 2.5
    e.data.materials.append(em)

# ---------------- 导出 GLB ----------------
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = helmet
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB')

# ---------------- 数值自检 ----------------
xs = [v.co.x for v in me.vertices]; ds = [v.co.y for v in me.vertices]; vs = [v.co.z for v in me.vertices]
bm2 = bmesh.new(); bm2.from_mesh(me)
nm = sum(1 for e in bm2.edges if len(e.link_faces) != 2)
bm2.free()
red_n = sum(1 for f in me.polygons if f.material_index == 1)
print('VERIFY', {'verts': len(me.vertices), 'faces': len(me.polygons), 'non_manifold': nm,
                 'red_faces': f'{red_n}/{len(me.polygons)}',
                 'bbox_x': (round(min(xs),3), round(max(xs),3)),
                 'bbox_v': (round(min(vs),3), round(max(vs),3)),
                 'bbox_d': (round(min(ds),3), round(max(ds),3))})
print('EXPORTED', OUT, os.path.getsize(OUT), 'bytes')
