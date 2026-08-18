# -*- coding: utf-8 -*-
"""gen_ultraman_blender_tpose.py — 按 T-pose 立绘生成初代奥特曼（assets/refs/classic.png）

v3 要点（相对 v2）：
  - 骨架比例全部按 T-pose 立绘实测锚点重排（长腿型：裆位 62% 身高，膝在 ±.115）
  - 手臂改 T-pose（微下垂 5°），正面手臂也用立绘投影（T-pose 图手臂完全展开有图可用）
  - 腿仍程序配色（参考图分腿站姿，投影会串色）
  - 本构建坑位全数规避：bake 全黑→numpy 软件光栅化；save 全黑→先 pack；
    像素缓冲自底向上→翻转；逐面 UV 是零面积点→逐顶点 UV；多 UV 层抢 active→清理

用法: blender -b -P tools/gen_ultraman_blender_tpose.py
输出: assets/output/blender/{Ultraman_Blender.fbx,.obj,.mtl,.zip,Ultraman_Bake.png,preview_*.png}
"""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'output', 'blender')
REF = os.path.join(ROOT, 'assets', 'refs', 'classic.png')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------- T-pose 立绘标定（像素实测）
IMG_W, IMG_H = 768, 1360
CX = 386.0          # 人物中线
SX = 472.0          # px / 世界单位（按身高 851px ↔ 1.80m）
# z → 图片y 分段锚点（透明 bbox + 关键行扫描实测）
Z2Y = [(0.00, 1119), (0.10, 1019), (0.186, 931), (0.686, 795), (0.902, 693),
       (1.118, 591), (1.209, 548), (1.298, 506), (1.370, 472), (1.455, 430),
       (1.545, 361), (1.640, 336), (1.715, 310), (1.800, 268)]

def z_to_imgy(z):
    if z <= Z2Y[0][0]: return Z2Y[0][1]
    for (z0, y0), (z1, y1) in zip(Z2Y, Z2Y[1:]):
        if z <= z1:
            return y0 + (y1 - y0) * (z - z0) / max(z1 - z0, 1e-6)
    return Z2Y[-1][1]

def proj_uv(x, z):
    u = (CX + x * SX) / IMG_W
    v = 1.0 - z_to_imgy(z) / IMG_H
    return (min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0))

# ---------------------------------------------------------------- 骨架（T-pose 实测比例）
J = {
    'hips':   ((0,     .01, 1.16), .085),
    'chest':  ((0,     .03, 1.38), .135),
    'neck':   ((0,     .015, 1.545), .046),
    'headB':  ((0,     .008, 1.650), .108),
    'headM':  ((0,     .015, 1.715), .102),
    'headT':  ((0,     .020, 1.780), .068),
    'jaw':    ((0,    -.050, 1.640), .048),
    # 头冠脊线：前额→头顶→后脑
    'cF':     ((0,    -.078, 1.700), .017),
    'cT':     ((0,     .015, 1.790), .019),
    'cB':     ((0,     .088, 1.745), .016),
    # 胸肌 + 斜方肌
    'pecL':   ((-.060, -.075, 1.435), .060),
    'pecR':   (( .060, -.075, 1.435), .060),
    'trapL':  ((-.110,  .005, 1.500), .050),
    'trapR':  (( .110,  .005, 1.500), .050),
    # T-pose 手臂（微下垂 5°）
    'shL':    ((-.205, 0, 1.455), .068),
    'elL':    ((-.475, 0, 1.425), .044),
    'wrL':    ((-.720, 0, 1.385), .036),
    'hdL':    ((-.775, 0, 1.365), .041),
    'he2L':   ((-.815, 0, 1.345), .027),
    'shR':    (( .205, 0, 1.455), .068),
    'elR':    (( .475, 0, 1.425), .044),
    'wrR':    (( .720, 0, 1.385), .036),
    'hdR':    (( .775, 0, 1.365), .041),
    'he2R':   (( .815, 0, 1.345), .027),
    # 长腿（膝 .69、裆 1.12、踝 .10 实测）
    'hpL':    ((-.105, .01, 1.14), .072),
    'knL':    ((-.115, .01,  .69), .055),
    'anL':    ((-.115, 0,    .10), .041),
    'heL':    ((-.115, .055, .050), .038),
    'toL':    ((-.115, -.105, .050), .035),
    'hpR':    (( .105, .01, 1.14), .072),
    'knR':    (( .115, .01,  .69), .055),
    'anR':    (( .115, 0,    .10), .041),
    'heR':    (( .115, .055, .050), .038),
    'toR':    (( .115, -.105, .050), .035),
}
E = [('hips','chest'),('chest','neck'),('neck','headB'),('headB','headM'),
     ('headM','headT'),('headB','jaw'),
     ('headM','cF'),('cF','cT'),('cT','cB'),
     ('chest','pecL'),('chest','pecR'),
     ('neck','trapL'),('neck','trapR'),
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
    r = J[n][1]
    sv.data[i].radius = (r, r)
    if n == 'hips':
        sv.data[i].use_root = True
bpy.ops.object.modifier_apply(modifier='Skin')
bpy.ops.object.modifier_apply(modifier='Subsurf')

# ---------------------------------------------------------------- 材质
def mat(name, color, metallic, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = rough
    return m

m_tex = mat('Tex', (1, 1, 1), .45, .45)
img = bpy.data.images.load(REF)
tex_node = m_tex.node_tree.nodes.new('ShaderNodeTexImage')
tex_node.image = img
m_tex.node_tree.links.new(tex_node.outputs['Color'],
                          m_tex.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
m_red    = mat('Red',    (.78, .10, .12), .15, .45)
m_silver = mat('Silver', (.74, .77, .84), .75, .32)
m_dark   = mat('Dark',   (.12, .12, .13), .3, .6)
IDX_TEX, IDX_RED, IDX_SILVER, IDX_DARK = 0, 1, 2, 3
for m in (m_tex, m_red, m_silver, m_dark):
    ob.data.materials.append(m)

# 耳坑：头侧小暗盘
for s in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, radius=.019,
                                         location=(s * .098, .008, 1.700))
    e = bpy.context.active_object
    e.scale = (.35, 1, 1)
    e.data.materials.append(m_dark)

bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.join()
bpy.ops.object.shade_smooth()

# ---------------------------------------------------------------- 面分配（T-pose 版）
Z_SH, Z_CROTCH = 1.455, 1.16

def zone_arm(p):
    """手臂背面/侧面：肩帽+上臂上半红，其余银（正面走立绘投影）"""
    x, y, z = p
    dsh = math.hypot(abs(x) - .205, z - Z_SH)
    if dsh < .095: return IDX_RED
    if z > 1.30 and .095 < dsh < .30: return IDX_RED
    return IDX_SILVER

def zone_leg(p):
    """腿（像素实测）：大腿正面上段红（外低内高的斜边），膝/小腿/脚银"""
    x, y, z = p
    a = abs(x)
    if .72 < z < 1.14:
        if (y < .03 and z > .80) or (a > .135 and z > .72): return IDX_RED
        return IDX_SILVER
    return IDX_SILVER

def zone_back(p):
    """背面：银底 + 红脊线/肩胛带/颈后红/盆骨红"""
    x, y, z = p
    a = abs(x)
    if 1.53 < z < 1.60: return IDX_RED
    if z >= 1.60:
        if z < 1.655 and a < .07: return IDX_RED
        return IDX_SILVER
    if Z_CROTCH <= z <= 1.49:
        w = .125 if 1.38 <= z <= 1.47 else (.075 if 1.26 <= z < 1.38 else .115)
        if a < w * .48: return IDX_RED
        if 1.42 <= z <= 1.49 and a < .16: return IDX_RED
        return IDX_SILVER
    if .72 <= z < Z_CROTCH:
        return IDX_RED if a > .148 else IDX_SILVER
    return IDX_SILVER

bm = bmesh.new()
bm.from_mesh(ob.data)
uvl = bm.loops.layers.uv.new('proj')

def planar_uv(x, z):
    return (0.5 + (x + .85) / 1.7 * .49 + .005, min(max(1 - z / 1.82, 0), 1) * .95 + .025)

def vert_uv(v):
    """逐顶点 UV：腿/背侧 → 右半平面；臂正面/躯干/头正面 → 左半立绘投影"""
    x, y, z = v.co.x, v.co.y, v.co.z
    if z < 1.20 or y >= 0.0:
        return planar_uv(x, z)
    u, vv = proj_uv(x, z)
    return (u * .48 + .01, vv * .92 + .04)

for f in bm.faces:
    p = f.calc_center_median()
    x, y, z = p
    a = abs(x)
    if z < Z_CROTCH:                                  # 腿：程序配色
        f.material_index = zone_leg(p)
    elif a > .155:                                    # 手臂：正面投影 / 背面程序
        f.material_index = IDX_TEX if f.normal.y < .05 else zone_arm(p)
    elif f.normal.y < .05:                            # 正面躯干/头：立绘投影
        f.material_index = IDX_TEX
    else:                                             # 背面：程序配色
        f.material_index = zone_back(p)
    for l in f.loops:
        l[uvl].uv = vert_uv(l.vert)
bm.to_mesh(ob.data)
bm.free()

# ---------------------------------------------------------------- 软件烘焙（numpy 光栅化）
BAKE_PNG = os.path.join(OUT, 'Ultraman_Bake.png')
import numpy as np
BS = 2048
bake_img = bpy.data.images.new('bake', BS, BS, alpha=True)
bake_img.filepath = BAKE_PNG
bake_img.file_format = 'PNG'

ref = bpy.data.images.load(REF, check_existing=True)
RW, RH = int(ref.size[0]), int(ref.size[1])
refpx = np.zeros((RH, RW, 4), dtype=np.float32)
ref.pixels.foreach_get(refpx.ravel())
refpx = np.ascontiguousarray(refpx[::-1])      # Blender 缓冲自底向上 → 翻转
assert refpx[..., :3].mean() > 0.01, '参考图像素读取为空'

def sample_ref(u, v):
    px = min(max(int(u * RW), 0), RW - 1)
    py = min(max(int((1 - v) * RH), 0), RH - 1)
    c = refpx[py, px]
    if c[3] < .5:
        return (.72, .75, .82, 1.0)             # 透明区兜底银灰
    return (float(c[0]), float(c[1]), float(c[2]), 1.0)

FLAT = {IDX_RED: (.78, .10, .12, 1), IDX_SILVER: (.74, .77, .84, 1), IDX_DARK: (.12, .12, .13, 1)}
buf = np.zeros((BS, BS, 4), dtype=np.float32)

def fill_poly(pts, color, grow=1.6):
    import math as _m
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    scaled = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        L = _m.hypot(dx, dy) or 1
        k = (L + grow) / L
        scaled.append((cx + dx * k, cy + dy * k))
    ys = [p[1] for p in scaled]
    y0, y1 = max(0, int(min(ys))), min(BS - 1, int(max(ys)) + 1)
    n = len(scaled)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            (ax, ay), (bx, by) = scaled[i], scaled[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                xs.append(ax + (y - ay) / (by - ay) * (bx - ax))
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            buf[y, max(0, int(a)):min(BS, int(b) + 1)] = color

bm2 = bmesh.new()
bm2.from_mesh(ob.data)
uvl2 = bm2.loops.layers.uv['proj']
for f in bm2.faces:
    mid = f.material_index
    if mid == IDX_TEX:
        p = f.calc_center_median()
        u, v = proj_uv(p.x, p.z)
        color = sample_ref(u, v)
    else:
        color = FLAT[mid]
    pts = [(l[uvl2].uv.x * BS, (1 - l[uvl2].uv.y) * BS) for l in f.loops]
    fill_poly(pts, color)
bm2.to_mesh(ob.data)
bm2.free()

# 渲染 UV 层必须唯一且 active
me_uv = ob.data
me_uv.update()
for l in list(me_uv.uv_layers):
    if l.name != 'proj':
        try:
            me_uv.uv_layers.remove(l)
        except RuntimeError:
            pass
me_uv.uv_layers.active = me_uv.uv_layers.get('proj')

# 黑背景填中性银灰（防 MIP 混黑）
gap = buf[..., 3] < .5
buf[gap] = (0.55, 0.57, 0.62, 1.0)
bake_img.pixels.foreach_set(buf.ravel())
bake_img.pack()                                  # 本构建必须 pack 再 save，否则写黑
bake_img.save()
print('PAINTED', BAKE_PNG, 'ref均值%.3f buf均值%.3f' % (refpx[..., :3].mean(), buf[..., :3].mean()))

# 全部面归单一材质
for f in ob.data.polygons:
    f.material_index = 0
while len(ob.data.materials) > 1:
    ob.data.materials.pop(index=1)
tex_node.image = bake_img
bsdf = m_tex.node_tree.nodes['Principled BSDF']
bsdf.inputs['Metallic'].default_value = 0.1
bsdf.inputs['Roughness'].default_value = 0.5

# ---------------------------------------------------------------- 校验 + 落地
bpy.context.view_layer.update()
me = ob.data
bm4 = bmesh.new(); bm4.from_mesh(me)
non_manifold = sum(1 for e in bm4.edges if len(e.link_faces) != 2)
bm4.free()
zmin = min(v.co.z for v in me.vertices)
ztop = max(v.co.z for v in me.vertices)
xmin = min(v.co.x for v in me.vertices)
xmax = max(v.co.x for v in me.vertices)
ob.location.z -= zmin
bpy.context.view_layer.update()
print('VERIFY', {'verts': len(me.vertices), 'faces': len(me.polygons),
                 'non_manifold_edges': non_manifold,
                 'bbox_x': (round(xmin, 3), round(xmax, 3)),
                 'height': round(ztop - zmin, 3),
                 'span': round(xmax - xmin, 3)})

# ---------------------------------------------------------------- 导出
ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Ultraman_Blender.fbx'),
                         use_selection=True, object_types={'MESH'})
bpy.ops.export_scene.obj(filepath=os.path.join(OUT, 'Ultraman_Blender.obj'),
                         use_selection=True, axis_forward='-Z', axis_up='Y')
print('EXPORTED to', OUT)

# ---------------------------------------------------------------- 预览渲染
try:
    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'
    scn.cycles.device = 'CPU'
    scn.cycles.samples = 32
    scn.cycles.use_denoising = False
    scn.render.resolution_x, scn.render.resolution_y = 640, 920
    scn.world = bpy.data.worlds.new('w')
    scn.world.use_nodes = True
    scn.world.node_tree.nodes['Background'].inputs[0].default_value = (.05, .055, .07, 1)
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
    for tag, loc in [('front', (0, -4.4, .95)), ('side', (-4.0, 0, .95)),
                     ('34', (-3.0, -3.0, 1.05)), ('back', (0, 4.4, .95))]:
        cam.location = loc
        bpy.context.view_layer.update()
        scn.render.filepath = os.path.join(OUT, f'preview_{tag}.png')
        bpy.ops.render.render(write_still=True)
    print('RENDERS done')
except Exception as ex:
    print('RENDER FAIL:', ex)
print('ALL DONE')
