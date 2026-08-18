# -*- coding: utf-8 -*-
"""gen_ultraman_blender2.py — 按立绘细化的初代奥特曼（参考 assets/refs/classic_apose.png）

v1 是纯位置分区配色（色带生硬、形状靠猜）。v2 改为：
  正面躯干/头/腿 → 立绘正交投影纹理（红盾曲线/眼睛/计时器形状直接来自原图）
  背面/手臂      → 按参考描述精调的程序分区
  几何新增        → 头冠脊线（前额→头顶→后脑）、胸肌、斜方肌、耳坑
  垂直映射        → 分段锚点（参考图是长腿比例，裆位 60% 身高，线性映射会错位）

用法: blender -b -P tools/gen_ultraman_blender2.py
输出: assets/output/blender/{Ultraman_Blender.fbx,.obj,.mtl,.zip,preview_*.png}
"""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'output', 'blender')
REF = os.path.join(ROOT, 'assets', 'refs', 'classic_apose.png')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------- 参考图映射标定
IMG_W, IMG_H = 408, 720
CX = 250.0          # 人物中线（px）
SX = 430.0          # px / 世界单位
# z → 图片y 分段锚点（上下两端 + 各关节，来自透明bbox行扫描）
Z2Y = [(0.00, 713), (0.50, 465), (0.88, 288), (1.07, 218), (1.30, 161),
       (1.45, 133), (1.53, 90), (1.63, 69), (1.70, 48), (1.80, 27)]

def z_to_imgy(z):
    if z <= Z2Y[0][0]: return Z2Y[0][1]
    for (z0, y0), (z1, y1) in zip(Z2Y, Z2Y[1:]):
        if z <= z1:
            return y0 + (y1 - y0) * (z - z0) / max(z1 - z0, 1e-6)
    return Z2Y[-1][1]

def proj_uv(x, z):
    """正面正交投影 → UV（UV 原点在左下，图片 y 向下）"""
    u = (CX + x * SX) / IMG_W
    v = 1.0 - z_to_imgy(z) / IMG_H
    return (min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0))

# ---------------------------------------------------------------- 骨架（关节+半径）
J = {
    'hips':   ((0,     .01,  .94), .088),
    'chest':  ((0,     .03, 1.26), .140),
    'neck':   ((0,     .015, 1.505), .048),
    'headB':  ((0,     .008, 1.645), .118),
    'headM':  ((0,     .015, 1.72),  .112),
    'headT':  ((0,     .020, 1.79),  .072),
    'jaw':    ((0,    -.055, 1.625), .050),
    # 头冠脊线：前额→头顶→后脑（参考图：额发际延伸到后脑的纵脊）
    'cF':     ((0,   -.080, 1.722), .019),
    'cT':     ((0,    .015, 1.788), .021),
    'cB':     ((0,    .090, 1.738), .018),
    # 胸肌 + 斜方肌（参考：健美倒三角）
    'pecL':   ((-.062, -.078, 1.335), .064),
    'pecR':   (( .062, -.078, 1.335), .064),
    'trapL':  ((-.117,  .005, 1.492), .055),
    'trapR':  (( .117,  .005, 1.492), .055),
    'shL':    ((-.215, 0,   1.45), .072),
    'elL':    ((-.436, 0,   1.295), .046),
    'wrL':    ((-.649, 0,   1.146), .038),
    'hdL':    ((-.703, 0,   1.114), .043),
    'he2L':   ((-.742, 0,   1.092), .028),
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
     ('headM','cF'),('cF','cT'),('cT','cB'),            # 头冠脊线
     ('chest','pecL'),('chest','pecR'),                 # 胸肌
     ('neck','trapL'),('neck','trapR'),                 # 斜方肌
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
def mat(name, color, metallic, rough, emiss=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = rough
    if emiss:
        bs.inputs['Emission'].default_value = (*emiss, 1)
        bs.inputs['Emission Strength'].default_value = 2.5
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

# 耳坑：头侧小暗盘（参考：耳位是圆形浅坑）
for s in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, radius=.02,
                                         location=(s * .104, .008, 1.700))
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

# ---------------------------------------------------------------- 面分配：投影纹理 / 程序分区
def zone_arm(p):
    """手臂（参考：肩红延到上臂上半、斜切过渡，前臂+手银）"""
    x, y, z = p
    a = abs(x)
    dsh = math.hypot(a - .215, z - 1.45)
    if dsh < .095: return IDX_RED                       # 三角肌帽
    if z > 1.20 and .095 < dsh < .28: return IDX_RED    # 上臂上半（斜向切口）
    return IDX_SILVER

def zone_leg(p):
    """腿（像素实测：近腿大腿正面红=132,28,25；膝盖/小腿/脚全银；远腿整条银）
    → 大腿正面+外侧红，内侧/后侧/膝/小腿/脚银"""
    x, y, z = p
    a = abs(x)
    if .46 < z < .93:
        if (y < .03 and z > .53) or (a > .135 and z > .46): return IDX_RED
        return IDX_SILVER
    return IDX_SILVER

def zone_back(p):
    """背面（参考：银底 + 红脊线/红肩胛带/盆骨红，颈后红）"""
    x, y, z = p
    a = abs(x)
    if 1.49 < z < 1.60: return IDX_RED                  # 颈后红
    if z >= 1.60:
        if z < 1.66 and a < .07: return IDX_RED         # 下颚红绕到后侧
        return IDX_SILVER                               # 头后银
    if .94 <= z <= 1.49:
        w = .125 if 1.30 <= z <= 1.46 else (.075 if 1.07 <= z < 1.30 else .115)
        if a < w * .48: return IDX_RED                  # 红脊线（前盾宽度一半）
        if 1.36 <= z <= 1.48 and a < .16: return IDX_RED  # 肩胛红带连肩帽
        return IDX_SILVER
    if .50 <= z < .94:
        return IDX_RED if a > .148 else IDX_SILVER      # 大腿外侧红条绕背
    return IDX_SILVER

bm = bmesh.new()
bm.from_mesh(ob.data)
uvl = bm.loops.layers.uv.new('proj')

def planar_uv(x, z):
    """程序分区区的烘焙 UV：右半区平面投影（平色重叠无害）。
    x 范围必须覆盖 ±.8（手臂最远 .74+.03），否则 u>1 回卷采样到左半立绘区"""
    return (0.5 + (x + .8) / 1.6 * .49 + .005, min(max(1 - z / 1.82, 0), 1) * .95 + .025)

def vert_uv(v):
    """逐顶点 UV：正面躯干/头 → 左半立绘投影；臂/腿/背侧 → 右半平面。
    （曾按整面赋同一 UV → 多边形退化为零面积点，扫描线涂不出任何东西）"""
    x, y, z = v.co.x, v.co.y, v.co.z
    if (abs(x) > .155 and z > 1.0) or z < .94 or y >= 0.0:
        return planar_uv(x, z)
    u, vv = proj_uv(x, z)
    return (u * .48 + .01, vv * .92 + .04)

def assign_uv(f):
    for l in f.loops:
        l[uvl].uv = vert_uv(l.vert)

for f in bm.faces:
    p = f.calc_center_median()
    x, y, z = p
    a = abs(x)
    if a > .155 and z > 1.0:                            # 手臂：程序分区
        f.material_index = zone_arm(p)
        assign_uv(f)
    elif z < .94:                                       # 腿：像素实测程序分区
        f.material_index = zone_leg(p)                  # （参考图分腿站姿，投影必错位）
        assign_uv(f)
    elif f.normal.y < .05:                              # 正面躯干/头：立绘投影
        f.material_index = IDX_TEX
        assign_uv(f)
    else:                                               # 背面：程序分区
        f.material_index = zone_back(p)
        assign_uv(f)
bm.to_mesh(ob.data)
bm.free()

# ---------------------------------------------------------------- 软件烘焙：numpy 光栅化
# 本构建 Cycles 无头 bake 全黑（隔离试验证实），改自己画：
#   每个面按其材质取色（Tex→参考图采样 / 红、银、暗→平色），扫描线填充其 UV 多边形。
BAKE_PNG = os.path.join(OUT, 'Ultraman_Bake.png')
import numpy as np
BS = 2048
bake_img = bpy.data.images.new('bake', BS, BS, alpha=True)
bake_img.filepath = BAKE_PNG
bake_img.file_format = 'PNG'

ref = bpy.data.images.load(REF, check_existing=True)
RW, RH = int(ref.size[0]), int(ref.size[1])
refpx = np.zeros((RH, RW, 4), dtype=np.float32)
ref.pixels.foreach_get(refpx.ravel())          # 只读，不写回
refpx = np.ascontiguousarray(refpx[::-1])      # Blender 像素缓冲自底向上，翻成自顶向下
assert refpx[..., :3].mean() > 0.01, '参考图像素读取为空'

def sample_ref(u, v):
    """proj_uv 的 (u,v)（v 上正）→ 参考图像素色；透明区兜底银灰"""
    px = min(max(int(u * RW), 0), RW - 1)
    py = min(max(int((1 - v) * RH), 0), RH - 1)
    c = refpx[py, px]
    if c[3] < .5:
        return (.72, .75, .82, 1.0)
    return (float(c[0]), float(c[1]), float(c[2]), 1.0)

FLAT = {IDX_RED: (.78, .10, .12, 1), IDX_SILVER: (.74, .77, .84, 1), IDX_DARK: (.12, .12, .13, 1)}
buf = np.zeros((BS, BS, 4), dtype=np.float32)

def fill_poly(pts, color, grow=1.6):
    """扫描线填充 UV 多边形（像素坐标），按质心外扩 grow 像素消缝"""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    import math as _m
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

# 渲染用 UV 层必须是 'proj'——耳球 join 可能带入自己的 UVMap 抢占 active 位，
# 导致渲染采样到全零 UV（贴图色岛一个都采不到，模型渲成灰黑）
me_uv = ob.data
me_uv.update()
for l in list(me_uv.uv_layers):
    if l.name != 'proj':
        try:
            me_uv.uv_layers.remove(l)
        except RuntimeError:
            pass
me_uv.uv_layers.active = me_uv.uv_layers.get('proj')
print('UV layers:', [(l.name, l.active) for l in me_uv.uv_layers])
# 黑背景填中性银灰：稀疏色岛 + 黑底在 MIP/线性过滤下会把整体颜色拉黑
gap = buf[..., 3] < .5
buf[gap] = (0.55, 0.57, 0.62, 1.0)
bake_img.pixels.foreach_set(buf.ravel())
# 本构建 img.save() 直接写全黑，必须先 pack() 进内存再落盘（隔离试验证实）
bake_img.pack()
bake_img.save()
print('PAINTED', BAKE_PNG, 'ref均值%.3f buf均值%.3f' % (refpx[..., :3].mean(), buf[..., :3].mean()))

# 全部面归到单一材质（贴图里已含所有颜色），降金属度保查看器兼容
for f in ob.data.polygons:
    f.material_index = 0
while len(ob.data.materials) > 1:
    ob.data.materials.pop(index=1)
tex_node.image = bake_img
bsdf = m_tex.node_tree.nodes['Principled BSDF']
bsdf.inputs['Metallic'].default_value = 0.1
bsdf.inputs['Roughness'].default_value = 0.5

# ---------------------------------------------------------------- 审计：法线 + 采样一致性
bm3 = bmesh.new()
bm3.from_mesh(ob.data)
uv3 = bm3.loops.layers.uv['proj']
targets = {'胸': (0, -.12, 1.30), '额': (0, -.09, 1.73), '大腿': (.115, -.05, .70),
           '小腿': (.115, -.05, .30), '上臂': (.35, -.03, 1.33), '背': (0, .12, 1.20)}
for tag, tp in targets.items():
    best, bd = None, 1e9
    for f in bm3.faces:
        c = f.calc_center_median()
        d = (c.x-tp[0])**2 + (c.y-tp[1])**2 + (c.z-tp[2])**2
        if d < bd: bd, best = d, f
    n = best.normal
    uvc = best.loops[0][uv3].uv
    px = buf[min(BS-1, int((1-uvc.y)*BS)), min(BS-1, int(uvc.x*BS))]
    corners = [(round(l[uv3].uv.x, 3), round(l[uv3].uv.y, 3)) for l in best.loops]
    row, col = int((1-uvc.y)*BS), int(uvc.x*BS)
    win = buf[max(0,row-30):row+30, max(0,col-30):col+30, :3]
    import collections
    hist = collections.Counter(map(tuple, (win[win.sum(-1) > .05]*1).tolist() if win.size else []))
    print(f"AUDIT {tag}: 法线=({n.x:+.2f},{n.y:+.2f},{n.z:+.2f}) 角UV={corners} 采样=({px[0]:.2f},{px[1]:.2f},{px[2]:.2f}) 邻域色={hist.most_common(3)}")
# 外向法线比例（以骨盆中心 (0,0,.95) 判内外）
outw = sum(1 for f in bm3.faces
           if (f.calc_center_median() - Vector((0, 0, .95))).dot(f.normal) > 0)
print(f"AUDIT 外向法线 {outw}/{len(bm3.faces)}")
bm3.free()
bpy.context.view_layer.update()
me = ob.data
bm = bmesh.new(); bm.from_mesh(me)
nm_loc = [(round((e.verts[0].co.x + e.verts[1].co.x) / 2, 1),
           round((e.verts[0].co.y + e.verts[1].co.y) / 2, 1),
           round((e.verts[0].co.z + e.verts[1].co.z) / 2, 1))
          for e in bm.edges if len(e.link_faces) != 2]
non_manifold = len(nm_loc)
if nm_loc:
    import collections
    print('NM_CLUSTERS', collections.Counter(nm_loc).most_common(8))
bm.free()
zmin = min(v.co.z for v in me.vertices)
ztop = max(v.co.z for v in me.vertices)
ob.location.z -= zmin
bpy.context.view_layer.update()
tex_faces = sum(1 for f in me.polygons if f.material_index == IDX_TEX)
print('VERIFY', {'verts': len(me.vertices), 'faces': len(me.polygons),
                 'non_manifold_edges': non_manifold,
                 'height': round(ztop - zmin, 3), 'tex_faces': tex_faces,
                 'scene_mesh_objects': len([o for o in bpy.context.scene.objects if o.type == 'MESH'])})

# ---------------------------------------------------------------- 导出
ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Ultraman_Blender.fbx'),
                         use_selection=True, object_types={'MESH'},
                         path_mode='AUTO', embed_textures=True)
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
