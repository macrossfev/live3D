#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mixamo_pipeline.py — Mixamo 动作 FBX → 自包含 GLB 一键流水线

输入：
  1) Mixamo 下载的 With Skin FBX（带网格+合身骨架+权重+动作）
  2) 贴图目录（至少一张基色；可选发光/法线）

处理（全部自动）：
  法线绕向重算 → 挑基色贴图(可 --base 指定) → 贴图降采样 1024 →
  材质组装(基色/发光/法线) → 动作重命名 → 导出单文件 GLB → 产物自检(bbox/贴图内嵌/动作数)
  可选 --demo 生成在线演示页

用法：
  python3 tools/mixamo_pipeline.py --fbx assets/samples/Kicking.fbx \
         --texdir download/DG/贴图 --name tiga_kick
  # 指定基色（默认自动挑：排除蓝底通道图/发光/法线）
  python3 tools/mixamo_pipeline.py --fbx ... --texdir ... --name x --base 迪迦.png

输出：assets/output/<name>.glb（+ --demo 时 tools/<name>_demo.html）
"""
import argparse, json, os, shutil, struct, subprocess, sys, tempfile
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, 'assets', 'output')
TEXSIZE = 1024

# ---------------------------------------------------------------- 贴图准备
def classify_textures(texdir):
    """分类贴图：base(基色) / emissive(发光) / normal(法线)。返回 {slot: path}"""
    cands = [f for f in os.listdir(texdir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    picked = {}
    for f in cands:
        ln = f.lower()
        if 'normal' in ln or '法线' in ln: picked.setdefault('normal', f)
        elif 'emiss' in ln or '发光' in ln or 'glow' in ln: picked.setdefault('emissive', f)
    rest = [f for f in cands if f not in picked.values()]
    # 基色启发式：排除蓝底通道图（b 均值显著高于 r），取剩余第一张
    scored = []
    for f in rest:
        im = np.array(Image.open(os.path.join(texdir, f)).convert('RGB').resize((64, 64)))
        m = im.mean(axis=(0, 1))
        scored.append((m[2] - (m[0] + m[1]) / 2, f))     # 越蓝分越高
    scored.sort()
    if scored:
        picked['base'] = scored[0][1]
        print(f"  基色自动选择: {picked['base']}（蓝度排序 {[(-round(s), f) for s, f in scored[:3]]}）")
    return picked

def prep_textures(texdir, slots, base_override, tmpdir):
    """降采样到 1024 并拷到临时目录（ASCII 名）"""
    if base_override:
        slots['base'] = base_override
    if 'base' not in slots:
        sys.exit('✗ 未找到基色贴图，用 --base 指定')
    names = {'base': 'base.png', 'emissive': 'emis.png', 'normal': 'nrm.png'}
    out = {}
    for slot, f in slots.items():
        im = Image.open(os.path.join(texdir, f)).convert('RGBA')
        if max(im.size) > TEXSIZE:
            im = im.resize((TEXSIZE, TEXSIZE), Image.LANCZOS)
        dst = os.path.join(tmpdir, names[slot])
        im.save(dst, optimize=True)
        out[slot] = dst
        print(f"  {slot}: {f} → {os.path.getsize(dst)//1024}KB")
    return out

# ---------------------------------------------------------------- Blender 段
BLENDER_SCRIPT = r'''
import bpy, os, sys
argv = dict(a.split('=', 1) for a in sys.argv[sys.argv.index('--') + 1:])
FBX, OUT, NAME = argv['fbx'], argv['out'], argv['name']
TEX = {k: v for k, v in argv.items() if k.startswith('tex_')}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')

# 法线绕向修复（AI 网格常有反向区 → 半边/头部不渲染）
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

# 动作重命名（Mixamo 默认名不可读）
for a in bpy.data.actions: a.name = NAME

# 材质
mat = bpy.data.materials.new(NAME)
mat.use_nodes = True
nt = mat.node_tree; bs = nt.nodes['Principled BSDF']
def mk(slot, file, noncolor=False):
    if slot not in TEX: return None
    img = bpy.data.images.load(filepath=TEX[slot])
    if noncolor: img.colorspace_settings.name = 'Non-Color'
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = img; return n
nb = mk('tex_base', TEX['tex_base'])
if nb: nt.links.new(nb.outputs['Color'], bs.inputs['Base Color'])
ne = mk('tex_emissive', TEX.get('tex_emissive', ''))
if ne:
    nt.links.new(ne.outputs['Color'], bs.inputs['Emission'])
    bs.inputs['Emission Strength'].default_value = 1.0
nn = mk('tex_normal', TEX.get('tex_normal', ''), noncolor=True)
if nn:
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(nn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
mesh.data.materials.clear(); mesh.data.materials.append(mat)
bpy.ops.object.shade_smooth()

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_animations=True)
print('BLENDER_DONE')
'''

def run_blender(fbx, out, name, texs):
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(BLENDER_SCRIPT); script = f.name
    argv = ['blender', '-b', '-P', script, '--',
            f'fbx={fbx}', f'out={out}', f'name={name}'] + \
           [f'{k}={v}' for k, v in texs.items()]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=900)
    os.unlink(script)
    if 'BLENDER_DONE' not in r.stdout:
        print(r.stdout[-2000:]); print(r.stderr[-1000:])
        sys.exit('✗ Blender 处理失败')
    print('  Blender: 法线修复 + 材质 + 导出 ✓')

# ---------------------------------------------------------------- 产物自检
def verify_glb(path):
    data = open(path, 'rb').read()
    pos, chunks = 12, []
    while pos < len(data):
        clen, ct = struct.unpack('<II', data[pos:pos+8])
        chunks.append(data[pos+8:pos+8+clen]); pos += 8+clen
    j = json.loads(chunks[0])
    bbox = None
    for mesh in j.get('meshes', []):
        for prim in mesh.get('primitives', []):
            acc = j['accessors'][prim['attributes']['POSITION']]
            mn, mx = acc.get('min'), acc.get('max')
            bbox = (mn, mx)
    imgs = j.get('images', [])
    anims = j.get('animations', [])
    ok = (bbox and 0 < bbox[1][1] < 3.0 and len(imgs) >= 1
          and all('bufferView' in i for i in imgs) and len(anims) >= 1)
    print(f"  自检: bbox y[{bbox[0][1]:.2f},{bbox[1][1]:.2f}]m | 贴图{len(imgs)}张全内嵌 | 动作{len(anims)}个 | {len(data)//1024}KB")
    if not ok: sys.exit('✗ 自检未过（bbox/贴图/动作异常）')
    print('  ✓ 自检通过')

# ---------------------------------------------------------------- 演示页
DEMO_TPL = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<title>__NAME__ · 动作预览</title>
<style>body{margin:0;background:#0e1118;color:#dde;overflow-x:hidden}
#hud{position:fixed;top:8px;left:8px;font:12px/1.6 monospace;color:#7ef;white-space:pre;z-index:9}
#tip{position:fixed;bottom:8px;left:8px;font:12px monospace;color:#567;z-index:9}</style>
<script type="importmap">{"imports":{
"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
}}</script></head><body><div id="hud">加载中…</div><div id="tip">拖转 · 滚轮缩放</div>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const W = 620, H = 900;
const r = new THREE.WebGLRenderer({ antialias: true });
r.setSize(W, H); document.body.appendChild(r.domElement);
const s = new THREE.Scene();
s.background = new THREE.Color(.05, .055, .07);
const cam = new THREE.PerspectiveCamera(32, W / H, .1, 80);
s.add(new THREE.AmbientLight(0xffffff, .95));
const sun = new THREE.DirectionalLight(0xffffff, 2.2); sun.position.set(2, 3, 5); s.add(sun);
s.add(new THREE.GridHelper(5, 10));
const ctl = new OrbitControls(cam, r.domElement);
ctl.target.set(0, 1.0, 0); cam.position.set(.8, 1.3, 3.8);
new GLTFLoader().load('__GLB__', g => {
  g.scene.traverse(o => { if (o.isSkinnedMesh) o.frustumCulled = false; });
  s.add(g.scene);
  const mixer = new THREE.AnimationMixer(g.scene);
  mixer.clipAction(g.animations[0]).play();
  const a = g.animations[0];
  document.getElementById('hud').textContent = '__NAME__\\n动作: ' + a.name + ' ' + a.duration.toFixed(2) + 's';
  document.title = 'OK';
  const clock = new THREE.Clock();
  (function loop(){ requestAnimationFrame(loop); mixer.update(clock.getDelta()); ctl.update(); r.render(s, cam); })();
}, ev => { if (ev.total) document.getElementById('hud').textContent = '下载… ' + Math.round(ev.loaded/ev.total*100) + '%'; },
e => { document.getElementById('hud').textContent = '失败 ' + e; document.title = 'ERR'; });
</script></body></html>'''

def make_demo(name, glb_path):
    html = DEMO_TPL.replace('__NAME__', name).replace('__GLB__', '../' + os.path.relpath(glb_path, os.path.join(ROOT, 'tools')))
    p = os.path.join(ROOT, 'tools', f'{name}_demo.html')
    open(p, 'w').write(html)
    print(f"  演示页: tools/{name}_demo.html（本地 http.server 8099 打开）")

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='Mixamo WithSkin FBX → 自包含 GLB')
    ap.add_argument('--fbx', required=True, help='Mixamo 下载的 With Skin FBX')
    ap.add_argument('--texdir', required=True, help='贴图目录')
    ap.add_argument('--name', required=True, help='产物名（动作名/文件名）')
    ap.add_argument('--base', default=None, help='基色贴图文件名（默认自动挑）')
    ap.add_argument('--out', default=None, help='输出 GLB 路径')
    ap.add_argument('--demo', action='store_true', help='生成演示页')
    a = ap.parse_args()
    out = a.out or os.path.join(OUTDIR, f'{a.name}.glb')
    os.makedirs(OUTDIR, exist_ok=True)
    print(f"== mixamo_pipeline: {a.name} ==")
    with tempfile.TemporaryDirectory() as td:
        slots = classify_textures(a.texdir)
        texs = prep_textures(a.texdir, slots, a.base, td)
        texs = {'tex_' + k: v for k, v in texs.items()}
        run_blender(os.path.abspath(a.fbx), out, a.name, texs)
    verify_glb(out)
    if a.demo: make_demo(a.name, out)
    print(f"✓ 完成: {out}")

if __name__ == '__main__':
    main()
