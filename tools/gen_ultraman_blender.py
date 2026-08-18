# -*- coding: utf-8 -*-
"""gen_ultraman_blender.py — 用 Blender Skin 修改器生成初代奥特曼（Mixamo 用）

路线与 SDF 版不同：关节骨架 → Skin 修改器（有机融合、天生无缝）→ Subsurf 光滑
→ 红银分色（按面部中心位置分区）→ 水密校验 → FBX/OBJ 导出 → Cycles 预览渲染。

Blender 3.4 Skin 实测约束（隔离实验确认）：
  - 半径只作用在管子横截面，叶子端点不外扩半球 → 圆端（头顶/手）需显式延伸顶点
  - 分支顶点（带 2+ 子边）是斜接面不是球 → 头骨必须做成链式穹顶弧
  - 眼/计时器 join 前须 DESELECT 全部再选齐（否则 join 不生效）

用法: blender -b -P tools/gen_ultraman_blender.py
输出: assets/mixamo/blender/{Ultraman_Blender.fbx,.obj,.mtl,preview_*.png}
约定: Blender Z 朝上、人物面向 -Y；A-pose（臂下垂 35°）；身高 ~1.81m；脚底 z=0。
"""
import bpy, bmesh, math, os
from mathutils import Vector

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'assets', 'output', 'blender')
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------- 骨架（关节+半径）
# (x, y深度[-Y=脸前], z高度), 半径
J = {
    'hips':   ((0,     .01,  .94), .088),
    'chest':  ((0,     .03, 1.26), .130),
    'neck':   ((0,     .015, 1.505), .048),
    # 头骨：链式穹顶弧（分支点无球，端点无帽）
    'headB':  ((0,     .008, 1.645), .118),
    'headM':  ((0,     .015, 1.72),  .112),
    'headT':  ((0,     .020, 1.79),  .072),
    'jaw':    ((0,    -.055, 1.625), .050),
    'shL':    ((-.215, 0,   1.45), .072),
    'elL':    ((-.436, 0,   1.295), .046),
    'wrL':    ((-.649, 0,   1.146), .038),
    'hdL':    ((-.703, 0,   1.114), .043),
    'he2L':   ((-.742, 0,   1.092), .028),   # 手端延伸（叶子不封帽）
    'shR':    (( .215, 0,   1.45), .072),
    'elR':    (( .436, 0,   1.295), .046),
    'wrR':    (( .649, 0,   1.146), .038),
    'hdR':    (( .703, 0,   1.114), .043),
    'he2R':   (( .742, 0,   1.092), .028),
    'hpL':    ((-.105, .01,  .93), .075),
    'knL':    ((-.115, .01,  .50), .057),
    'anL':    ((-.115, 0,    .09), .043),
    'heL':    ((-.115, .055, .045), .040),
    'toL':    ((-.115, -.105, .045), .037),
    'hpR':    (( .105, .01,  .93), .075),
    'knR':    (( .115, .01,  .50), .057),
    'anR':    (( .115, 0,    .09), .043),
    'heR':    (( .115, .055, .045), .040),
    'toR':    (( .115, -.105, .045), .037),
}
E = [('hips','chest'),('chest','neck'),('neck','headB'),('headB','headM'),
     ('headM','headT'),('headB','jaw'),
     ('neck','shL'),('shL','elL'),('elL','wrL'),('wrL','hdL'),('hdL','he2L'),
     ('neck','shR'),('shR','elR'),('elR','wrR'),('wrR','hdR'),('hdR','he2R'),
     ('hips','hpL'),('hpL','knL'),('knL','anL'),('anL','heL'),('anL','toL'),
     ('hips','hpR'),('hpR','knR'),('knR','anR'),('anR','heR'),('anR','toR')]

me = bpy.data.meshes.new('skel')
names = list(J)
me.from_pydata([J[n][0] for n in names],
               [[names.index(a), names.index(b)] for a, b in E], [])
ob = bpy.data.objects.new('UltramanClassic', me)
bpy.context.collection.objects.link(ob)
bpy.context.view_layer.objects.active = ob
ob.select_set(True)

skin = ob.modifiers.new('Skin', 'SKIN')
skin.use_smooth_shade = True
sub = ob.modifiers.new('Subsurf', 'SUBSURF')
sub.levels = sub.render_levels = 2
bpy.context.view_layer.update()
sv = me.skin_vertices[0]
for i, n in enumerate(names):
    d = sv.data[i]
    r = J[n][1]
    d.radius = (r, r)
    if n == 'hips':
        d.use_root = True
bpy.ops.object.modifier_apply(modifier='Skin')
bpy.ops.object.modifier_apply(modifier='Subsurf')

# ---------------------------------------------------------------- 材质
def mat(name, color, metallic, rough, emiss=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = rough
    if emiss:
        bs.inputs['Emission'].default_value = (*emiss, 1)
        bs.inputs['Emission Strength'].default_value = 3.0
    return m

m_silver = mat('Silver', (.74, .77, .84), .75, .32)
m_red    = mat('Red',    (.78, .10, .12), .15, .45)
m_eye    = mat('Eye',    (1.0, .92, .55), 0, .3, emiss=(1.0, .88, .40))
m_timer  = mat('Timer',  (1.0, .45, .15), 0, .3, emiss=(1.0, .35, .08))
ob.data.materials.append(m_silver)   # 0
ob.data.materials.append(m_red)      # 1

# 眼睛（杏仁透镜）+ 彩色计时器：独立闭球嵌入，join 成单物体
for s in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=.05,
                                         location=(s * .048, -.099, 1.703))
    e = bpy.context.active_object
    e.scale = (.92, .30, .48)
    e.rotation_euler = (0, 0, s * math.radians(-16))
    e.data.materials.append(m_eye)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=.036,
                                     location=(0, -.135, 1.235))
bpy.context.active_object.data.materials.append(m_timer)

# join：必须先清选择，把身体+眼+计时器全部选中，身体为 active
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.join()
bpy.ops.object.shade_smooth()

# ---------------------------------------------------------------- 红银分区（面部中心位置）
def zone(p):
    x, y, z = p
    a = abs(x)
    if z > 1.60:                                    # 头
        if z < 1.665 and y < .01 and a < .10:       # 下颚/面颊下沿红
            return 1
        return 0
    if z > 1.49:                                    # 颈银
        return 0
    # 手臂分区先于躯干带（否则手臂面被躯干 return 拦截——肩帽曾因此不红）
    if a > .16 and z > 1.0:
        dsh = math.hypot(a - .215, z - 1.45)        # 肩帽
        if dsh < .092: return 1
        if z > 1.23 and .12 < dsh < .33: return 1   # 上臂中段红环
        return 0
    if .94 <= z <= 1.49:                            # 躯干：中央红盾（胸宽腰窄盆宽）
        w = .125 if 1.30 <= z <= 1.46 else (.075 if 1.07 <= z < 1.30 else .115)
        return 1 if a < w else 0
    if .50 <= z < .94:                              # 大腿外侧红
        return 1 if a > .124 else 0
    if .10 < z < .50:                               # 小腿前侧红
        return 1 if y < -.025 else 0
    return 0

bm = bmesh.new()
bm.from_mesh(ob.data)
for f in bm.faces:
    if f.material_index == 0:                       # 只重排本体面（眼/计时器已定）
        f.material_index = zone(f.calc_center_median())
bm.to_mesh(ob.data)
bm.free()

# ---------------------------------------------------------------- 校验 + 落地
bpy.context.view_layer.update()
me = ob.data
bm = bmesh.new(); bm.from_mesh(me)
non_manifold = sum(1 for e in bm.edges if len(e.link_faces) != 2)
bm.free()

zmin = min(v.co.z for v in me.vertices)
ztop = max(v.co.z for v in me.vertices)
xmin = min(v.co.x for v in me.vertices)
xmax = max(v.co.x for v in me.vertices)
ob.location.z -= zmin                               # 脚底精确贴地
bpy.context.view_layer.update()
rep = {
    'verts': len(me.vertices), 'faces': len(me.polygons),
    'non_manifold_edges': non_manifold,
    'bbox_x': (round(xmin, 3), round(xmax, 3)),
    'height': round(ztop - zmin, 3),
    'scene_mesh_objects': len([o for o in bpy.context.scene.objects if o.type == 'MESH']),
    'mats': [m.name for m in me.materials],
}
print('VERIFY', rep)

# ---------------------------------------------------------------- 导出
ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Ultraman_Blender.fbx'),
                         use_selection=True, object_types={'MESH'})
bpy.ops.export_scene.obj(filepath=os.path.join(OUT, 'Ultraman_Blender.obj'),
                         use_selection=True, axis_forward='-Z', axis_up='Y')
print('EXPORTED to', OUT)

# ---------------------------------------------------------------- 预览渲染（Cycles CPU，无 OIDN 不去噪）
try:
    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'
    scn.cycles.device = 'CPU'
    scn.cycles.samples = 32
    scn.cycles.use_denoising = False
    scn.render.resolution_x, scn.render.resolution_y = 640, 920
    scn.world = bpy.data.worlds.new('w')
    scn.world.use_nodes = True
    bg = scn.world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (.05, .055, .07, 1)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    scn.collection.objects.link(sun)
    fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'SUN'))
    fill.data.energy = 1.0
    fill.rotation_euler = (math.radians(120), math.radians(30), math.radians(200))
    scn.collection.objects.link(fill)
    target = bpy.data.objects.new('target', None)
    target.location = (0, 0, .95)
    scn.collection.objects.link(target)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.lens = 60
    scn.collection.objects.link(cam)
    scn.camera = cam
    con = cam.constraints.new('TRACK_TO')
    con.target = target
    for tag, loc in [('front', (0, -3.4, 1.0)), ('side', (-3.4, 0, 1.0)),
                     ('34', (-2.5, -2.5, 1.15))]:
        cam.location = loc
        bpy.context.view_layer.update()
        scn.render.filepath = os.path.join(OUT, f'preview_{tag}.png')
        bpy.ops.render.render(write_still=True)
    print('RENDERS done')
except Exception as ex:
    print('RENDER FAIL:', ex)
print('ALL DONE')
