#!/usr/bin/env python3
"""gen_ultraman_obj.py — 初代奥特曼 Mixamo 用 T-pose 单网格

与旧版「胶囊堆」不同：SDF 光滑并集 + marching cubes，得到一张水密网格。
按 Mixamo 自动绑骨要求：
  人形可辨、T-pose、四肢与躯干分界清楚、无道具、单物体、
  脚踩 y=0、原点居中、面向 +Z。

输出（assets/mixamo/）：
  Ultraman_Classic.obj / .mtl / .zip
  preview_front.png / preview_side.png / preview_34.png

用法: python3 tools/gen_ultraman_obj.py
"""
from __future__ import annotations

import os
import zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from skimage import measure


# ---------------------------------------------------------------------------
# 数学
# ---------------------------------------------------------------------------
def _norm(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


def sd_sphere(P, c, r):
    return np.linalg.norm(P - c, axis=1) - r


def sd_ellipsoid(P, c, rad):
    """近似椭球 SDF（对 marching cubes 足够）。"""
    p = (P - c) / rad
    k0 = np.linalg.norm(p, axis=1)
    k1 = np.linalg.norm(p / rad, axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def sd_capsule_taper(P, a, b, ra, rb):
    pa = P - a
    ba = b - a
    baba = float(ba @ ba) or 1e-12
    h = np.clip((pa @ ba) / baba, 0.0, 1.0)
    r = ra + (rb - ra) * h
    return np.linalg.norm(pa - ba * h[:, None], axis=1) - r


def sd_capsule(P, a, b, r):
    return sd_capsule_taper(P, a, b, r, r)


def sd_box(P, c, half):
    q = np.abs(P - c) - half
    return np.linalg.norm(np.maximum(q, 0.0), axis=1) + np.minimum(np.max(q, axis=1), 0.0)


def sd_cylinder(P, c, axis, r, half_h):
    """有限长圆柱。axis 单位向量。"""
    axis = np.asarray(axis, np.float64)
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    pa = P - c
    along = pa @ axis
    radial = np.linalg.norm(pa - along[:, None] * axis, axis=1) - r
    hh = np.abs(along) - half_h
    out = np.sqrt(np.maximum(radial, 0.0) ** 2 + np.maximum(hh, 0.0) ** 2)
    inn = np.minimum(np.maximum(radial, hh), 0.0)
    return out + inn


def near_capsule(P, a, b, r):
    return sd_capsule(P, a, b, r) < 0.0


def smin(d1, d2, k):
    h = np.clip(0.5 + 0.5 * (d2 - d1) / max(k, 1e-8), 0.0, 1.0)
    return d2 * (1.0 - h) + d1 * h - k * h * (1.0 - h)


def smax(d1, d2, k):
    return -smin(-d1, -d2, k)


def rot_z(P, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    return np.stack([c * x - s * y, s * x + c * y, z], axis=1)


def rot_x(P, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    return np.stack([x, c * y - s * z, s * y + c * z], axis=1)


def rot_y(P, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    return np.stack([c * x + s * z, y, -s * x + c * z], axis=1)


def sd_ellipsoid_ori(P, c, rad, rz=0.0, rx=0.0, ry=0.0):
    p = P - c
    if rz:
        p = rot_z(p, -rz)
    if rx:
        p = rot_x(p, -rx)
    if ry:
        p = rot_y(p, -ry)
    return sd_ellipsoid(p + c, c, rad)


# ---------------------------------------------------------------------------
# 初代奥特曼 SDF（单位：米，身高约 1.85，T-pose，面朝 +Z）
# ---------------------------------------------------------------------------
# 关键高度（对照 assets/refs/classic_apose.png）
Y_FOOT, Y_ANKLE, Y_KNEE = 0.00, 0.085, 0.50
Y_HIP, Y_WAIST, Y_TIMER = 0.96, 1.08, 1.268
Y_CHEST, Y_SHOULDER, Y_NECK = 1.35, 1.50, 1.56
Y_CHIN, Y_EYE, Y_TOP = 1.605, 1.718, 1.92

SHX = 0.225
HIPX = 0.118


def sdf_head(P):
    """头盔形：扁脸、银下颚、两侧耳板、额上翻到脑后的头冠、外眼角上挑的杏仁眼。"""
    # 压扁头盔：立绘是面罩不是圆球
    d = sd_ellipsoid(P, np.array([0.0, 1.715, 0.005]), np.array([0.118, 0.148, 0.088]))
    d = smin(d, sd_ellipsoid(P, np.array([0.0, 1.698, 0.078]), np.array([0.098, 0.118, 0.042])), 0.014)
    d = smin(d, sd_ellipsoid(P, np.array([0.0, 1.598, 0.072]), np.array([0.066, 0.048, 0.048])), 0.012)
    d = smin(d, sd_capsule_taper(P, np.array([0.0, 1.735, 0.095]),
                                np.array([0.0, 1.905, 0.015]), 0.022, 0.013), 0.010)
    d = smin(d, sd_capsule_taper(P, np.array([0.0, 1.905, 0.015]),
                                np.array([0.0, 1.855, -0.095]), 0.013, 0.009), 0.008)
    d = smin(d, sd_ellipsoid(P, np.array([0.0, 1.78, 0.055]), np.array([0.014, 0.055, 0.048])), 0.008)
    for s in (-1.0, 1.0):
        d = smin(d, sd_ellipsoid(P, np.array([s * 0.128, 1.685, 0.008]),
                                np.array([0.014, 0.032, 0.026])), 0.006)
    for s in (-1.0, 1.0):
        lens = np.array([s * 0.057, Y_EYE, 0.152])
        d = smin(d, sd_ellipsoid_ori(P, lens, np.array([0.048, 0.017, 0.016]), rz=s * 22), 0.002)
    return d


def sdf_torso(P):
    """倒三角：宽胸窄腰、胸肌分开、红短裤胯、扁圆计时器。"""
    d = sd_capsule_taper(P, np.array([0.0, 0.97, 0.00]), np.array([0.0, 1.08, 0.00]), 0.155, 0.118)
    d = smin(d, sd_capsule_taper(P, np.array([0.0, 1.08, 0.00]), np.array([0.0, 1.20, 0.012]), 0.100, 0.128), 0.022)
    d = smin(d, sd_capsule_taper(P, np.array([0.0, 1.20, 0.020]), np.array([0.0, 1.40, 0.055]), 0.155, 0.205), 0.024)
    d = smin(d, sd_capsule_taper(P, np.array([0.0, 1.40, 0.048]), np.array([0.0, 1.525, 0.010]), 0.198, 0.128), 0.020)
    for s in (-1.0, 1.0):
        d = smin(d, sd_ellipsoid(P, np.array([s * 0.078, 1.348, 0.138]),
                                np.array([0.095, 0.072, 0.062])), 0.016)
    d = smin(d, sd_cylinder(P, np.array([0.0, Y_TIMER, 0.175]),
                           np.array([0.0, 0.0, 1.0]), 0.048, 0.015), 0.005)
    d = smin(d, sd_sphere(P, np.array([0.0, Y_TIMER, 0.195]), 0.030), 0.003)
    d = smin(d, sd_ellipsoid(P, np.array([0.0, 0.955, 0.008]), np.array([0.158, 0.078, 0.112])), 0.024)
    d = smin(d, sd_ellipsoid(P, np.array([0.0, 0.935, -0.055]), np.array([0.132, 0.072, 0.068])), 0.020)
    return d


def sdf_neck(P):
    return sd_capsule_taper(P, np.array([0.0, 1.515, 0.010]), np.array([0.0, 1.615, 0.022]), 0.048, 0.042)


def sdf_arm(P, side):
    s = float(side)
    sh = np.array([s * SHX, Y_SHOULDER, 0.0])
    el = np.array([s * 0.52, Y_SHOULDER - 0.005, 0.0])
    wr = np.array([s * 0.78, Y_SHOULDER - 0.008, 0.0])
    hd = np.array([s * 0.875, Y_SHOULDER - 0.008, 0.0])
    d = sd_ellipsoid(P, sh + np.array([s * 0.012, 0.0, 0.0]), np.array([0.062, 0.058, 0.055]))
    d = smin(d, sd_capsule_taper(P, sh, el, 0.056, 0.048), 0.014)
    d = smin(d, sd_capsule_taper(P, el, wr, 0.046, 0.038), 0.010)
    d = smin(d, sd_ellipsoid(P, hd, np.array([0.052, 0.032, 0.042])), 0.008)
    d = smin(d, sd_ellipsoid(P, np.array([s * 0.835, Y_SHOULDER - 0.032, 0.026]),
                            np.array([0.020, 0.016, 0.016])), 0.006)
    return d


def sdf_leg(P, side):
    s = float(side)
    hp = np.array([s * HIPX, Y_HIP, 0.01])
    kn = np.array([s * 0.122, Y_KNEE, 0.0])
    an = np.array([s * 0.122, Y_ANKLE, 0.0])
    ft = np.array([s * 0.122, 0.032, 0.078])
    d = sd_capsule_taper(P, hp, kn, 0.098, 0.062)
    d = smin(d, sd_ellipsoid(P, np.array([s * 0.128, 0.74, 0.040]),
                            np.array([0.064, 0.130, 0.055])), 0.018)
    d = smin(d, sd_capsule_taper(P, kn, an, 0.056, 0.042), 0.012)
    d = smin(d, sd_ellipsoid(P, np.array([s * 0.122, 0.30, -0.012]),
                            np.array([0.042, 0.095, 0.048])), 0.012)
    d = smin(d, sd_ellipsoid(P, ft, np.array([0.048, 0.034, 0.118])), 0.010)
    d = smin(d, sd_sphere(P, hp, 0.056), 0.016)
    return d


def sdf_body(P):
    d = sdf_torso(P)
    d = smin(d, sdf_neck(P), 0.016)
    d = smin(d, sdf_head(P), 0.014)
    d = smin(d, sdf_arm(P, -1), 0.024)
    d = smin(d, sdf_arm(P, +1), 0.024)
    for s in (-1.0, 1.0):
        d = smin(d, sd_capsule_taper(
            P, np.array([s * 0.12, Y_SHOULDER, 0.0]),
            np.array([s * 0.25, Y_SHOULDER, 0.0]), 0.060, 0.054), 0.016)
    d = smin(d, sdf_leg(P, -1), 0.016)
    d = smin(d, sdf_leg(P, +1), 0.016)
    # 腿间只开细缝，正面仍是完整人形
    gap = sd_capsule(P, np.array([0.0, 0.52, 0.0]), np.array([0.0, 0.90, 0.0]), 0.007)
    d = smax(d, -gap, 0.006)
    return d


# ---------------------------------------------------------------------------
# 材质分区（初代红银纹：胸 V、肩臂、外侧大腿、小腿折线、下颚/头侧）
# ---------------------------------------------------------------------------
MATS = {
    'Silver': dict(Kd=(0.76, 0.79, 0.85), Ks=(0.48, 0.50, 0.55), Ns=95, Ke=(0, 0, 0)),
    'Red':    dict(Kd=(0.82, 0.10, 0.12), Ks=(0.24, 0.06, 0.06), Ns=45, Ke=(0, 0, 0)),
    'Eye':    dict(Kd=(1.00, 0.92, 0.40), Ks=(0.60, 0.52, 0.20), Ns=140, Ke=(0.70, 0.50, 0.10)),
    'Timer':  dict(Kd=(0.55, 0.95, 1.00), Ks=(0.40, 0.70, 0.80), Ns=100, Ke=(0.25, 0.55, 0.65)),
    'Ear':    dict(Kd=(0.16, 0.16, 0.18), Ks=(0.12, 0.12, 0.14), Ns=30, Ke=(0, 0, 0)),
}
MAT_ORDER = ['Silver', 'Red', 'Eye', 'Timer', 'Ear']


def _in_tri(x, y, ax, ay, bx, by, cx, cy):
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    w1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
    w2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
    w3 = 1.0 - w1 - w2
    return (w1 >= 0) & (w2 >= 0) & (w3 >= 0)


def classify_points(P):
    """对照 classic.png：银面+银下巴、红头罩两侧、胸甲 V 停在计时器、红短裤、外侧大腿、胫前折线。"""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax = np.abs(x)
    label = np.zeros(len(P), dtype=np.int32)          # 0 Silver

    head = y > 1.56
    # 头罩红：两侧 + 后脑 + 头冠后半。脸和下巴保持银。
    side_cowl = head & (ax > 0.068) & (z < 0.055)
    back_cowl = head & (z < -0.015)
    crest_back = head & (y > 1.80) & (z < -0.02) & (ax < 0.045)
    label[side_cowl | back_cowl | crest_back] = 1
    face = head & (z > 0.040) & (ax < 0.095) & (y < 1.84)
    chin = head & (y < 1.640) & (z > 0.030) & (ax < 0.075)
    crest_front = head & (y > 1.76) & (z > 0.00) & (ax < 0.040)
    label[face | chin | crest_front] = 0

    front = z > 0.018
    # 胸甲大红 V：两肩连到计时器，不再往肚脐拉红带
    chest_v = front & _in_tri(x, y, -0.205, 1.54, 0.205, 1.54, 0.0, 1.20)
    clav = front & (y > 1.46) & (y < 1.56) & (ax < 0.20)
    label[chest_v | clav] = 1

    # 红短裤：整个胯/髋
    trunks = (y > 0.88) & (y < 1.07) & (ax < 0.20)
    label[trunks] = 1

    # 肩甲 + 上臂（T-pose 沿 X）
    shoulder = (y > 1.42) & (y < 1.58) & (ax > 0.15) & (ax < 0.36)
    upper_arm = (y > 1.43) & (y < 1.57) & (ax > 0.30) & (ax < 0.56)
    label[shoulder | upper_arm] = 1

    # 外侧大腿，连上红短裤
    outer_thigh = (y > 0.54) & (y < 0.95) & (ax > 0.095) & (ax < 0.24)
    label[outer_thigh] = 1

    # 胫前折线：两条斜带合成 V
    for s in (-1.0, 1.0):
        apex = np.array([s * 0.122, 0.20, 0.045])
        w1 = np.array([s * 0.122 - 0.045, 0.34, 0.030])
        w2 = np.array([s * 0.122 + 0.045, 0.34, 0.030])
        chev = (sd_capsule(P, apex, w1, 0.016) < 0) | (sd_capsule(P, apex, w2, 0.016) < 0)
        label[chev] = 1

    # 耳板
    ear = (y > 1.65) & (y < 1.72) & (ax > 0.112) & (ax < 0.150) & (np.abs(z) < 0.04)
    label[ear] = 4

    # 眼：扁杏仁、左右分开
    # 杏仁眼：按旋转椭圆刷，避免刷成黄方块
    for s in (-1.0, 1.0):
        ang = np.radians(-s * 22.0)
        dx = x - s * 0.057
        dy = y - Y_EYE
        xr = dx * np.cos(ang) - dy * np.sin(ang)
        yr = dx * np.sin(ang) + dy * np.cos(ang)
        in_eye = (xr / 0.050) ** 2 + (yr / 0.018) ** 2 < 1.0
        label[in_eye & (z > 0.100)] = 2

    # 计时器：内芯青白，外圈银边
    dxy = np.hypot(x, y - Y_TIMER)
    timer = (dxy < 0.034) & (z > 0.12) & (y > 1.22) & (y < 1.33)
    rim = (dxy < 0.055) & (dxy >= 0.034) & (z > 0.11) & (y > 1.21) & (y < 1.34)
    label[rim] = 0
    label[timer] = 3
    return label


# ---------------------------------------------------------------------------
# 网格处理
# ---------------------------------------------------------------------------
def largest_component(verts, faces):
    n = len(verts)
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra

    for a, b, c in faces:
        union(a, b)
        union(b, c)
    roots = np.array([find(i) for i in range(n)])
    counts = np.bincount(roots)
    keep_root = int(np.argmax(counts))
    keep_v = roots == keep_root
    remap = -np.ones(n, dtype=np.int64)
    remap[keep_v] = np.arange(keep_v.sum())
    fmask = keep_v[faces[:, 0]] & keep_v[faces[:, 1]] & keep_v[faces[:, 2]]
    return verts[keep_v], remap[faces[fmask]]


def laplacian_smooth(verts, faces, iters=5, lam=0.38):
    n = len(verts)
    adj = [[] for _ in range(n)]
    for a, b, c in faces:
        adj[a] += [b, c]
        adj[b] += [a, c]
        adj[c] += [a, b]
    nbrs = [np.unique(a) for a in adj]
    v = verts.copy()
    for _ in range(iters):
        nv = v.copy()
        for i, nb in enumerate(nbrs):
            if len(nb) == 0:
                continue
            nv[i] = (1.0 - lam) * v[i] + lam * v[nb].mean(axis=0)
        v = nv
    return v


def vertex_normals(verts, faces):
    nrm = np.zeros_like(verts)
    t0, t1, t2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    fn = np.cross(t1 - t0, t2 - t0)
    for i in range(3):
        np.add.at(nrm, faces[:, i], fn)
    return _norm(nrm)


# ---------------------------------------------------------------------------
# OBJ / MTL / ZIP
# ---------------------------------------------------------------------------
def write_mtl(path):
    with open(path, 'w') as f:
        for name in MAT_ORDER:
            m = MATS[name]
            kd, ks, ke = m['Kd'], m['Ks'], m['Ke']
            f.write(f"newmtl {name}\n")
            f.write(f"Kd {kd[0]:.3f} {kd[1]:.3f} {kd[2]:.3f}\n")
            f.write(f"Ks {ks[0]:.3f} {ks[1]:.3f} {ks[2]:.3f}\n")
            f.write(f"Ke {ke[0]:.3f} {ke[1]:.3f} {ke[2]:.3f}\n")
            f.write(f"Ns {m['Ns']}\nillum 2\n\n")


def write_obj(path, verts, faces, normals, face_mat):
    with open(path, 'w') as f:
        f.write(f"mtllib {os.path.basename(path).replace('.obj', '.mtl')}\n")
        f.write("o UltramanClassic\n")
        f.write("s 1\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for n in normals:
            f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
        for mi, name in enumerate(MAT_ORDER):
            idx = np.where(face_mat == mi)[0]
            if len(idx) == 0:
                continue
            f.write(f"usemtl {name}\n")
            for i in idx:
                a, b, c = faces[i] + 1
                f.write(f"f {a}//{a} {b}//{b} {c}//{c}\n")


# ---------------------------------------------------------------------------
# 软件预览（z-buffer）
# ---------------------------------------------------------------------------
PREVIEW_RGB = {
    0: np.array([194, 201, 214], np.float32),
    1: np.array([210,  28,  34], np.float32),
    2: np.array([255, 232,  92], np.float32),
    3: np.array([120, 230, 255], np.float32),
    4: np.array([ 42,  42,  48], np.float32),
}


def look_at(eye, target, up):
    f = _norm((target - eye)[None, :])[0]
    r = _norm(np.cross(f, up)[None, :])[0]
    u = np.cross(r, f)
    return r, u, f


def render_view(verts, faces, normals, face_mat, eye, target, W=420, H=760, fov=28.0):
    """画家算法三角面预览（足够看外形与红纹，秒级出图）。"""
    eye = np.asarray(eye, np.float64)
    target = np.asarray(target, np.float64)
    r, u, f = look_at(eye, target, np.array([0.0, 1.0, 0.0]))
    fl = 0.5 * H / np.tan(np.radians(fov) * 0.5)
    cam = verts - eye
    x, y, z = cam @ r, cam @ u, cam @ f
    px = (x / np.maximum(z, 1e-4)) * fl + W * 0.5
    py = H * 0.5 - (y / np.maximum(z, 1e-4)) * fl
    c0, c1, c2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    fn = _norm(np.cross(c1 - c0, c2 - c0))
    view = _norm(eye[None, :] - (c0 + c1 + c2) / 3.0)
    front = (fn * view).sum(axis=1) > 0.0
    depth = ((c0 + c1 + c2) / 3.0 - eye) @ f
    order = np.where(front)[0]
    order = order[np.argsort(-depth[order])]
    key = _norm(np.array([[0.45, 0.75, 0.48]]))[0]
    img = Image.new('RGB', (W, H), (10, 12, 18))
    dr = ImageDraw.Draw(img)
    dr.line([(16, H - 34), (W - 16, H - 34)], fill=(40, 48, 62), width=1)
    for fi in order:
        ids = faces[fi]
        if z[ids].min() < 0.2:
            continue
        pts = [(float(px[ids[0]]), float(py[ids[0]])),
               (float(px[ids[1]]), float(py[ids[1]])),
               (float(px[ids[2]]), float(py[ids[2]]))]
        ndl = max(0.0, float(fn[fi] @ key))
        mid = int(face_mat[fi])
        base = PREVIEW_RGB[mid]
        col = np.clip(base * (0.22 + 0.78 * ndl), 0, 255).astype(np.int32)
        if mid >= 2:
            col = np.clip(col * 0.45 + base * 0.60, 0, 255).astype(np.int32)
        dr.polygon(pts, fill=tuple(int(c) for c in col))
    return np.array(img)


def stamp(img, text):
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, im.width, 28], fill=(8, 10, 16))
    dr.text((10, 6), text, fill=(220, 226, 236))
    return im


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build_mesh(cell=0.009):
    x0, x1 = -1.02, 1.02
    y0, y1 = -0.02, 1.96
    z0, z1 = -0.32, 0.40
    xs = np.arange(x0, x1 + cell * 0.5, cell, dtype=np.float32)
    ys = np.arange(y0, y1 + cell * 0.5, cell, dtype=np.float32)
    zs = np.arange(z0, z1 + cell * 0.5, cell, dtype=np.float32)
    nx, ny, nz = len(xs), len(ys), len(zs)
    print(f"  SDF 网格 {nx}×{ny}×{nz} = {nx*ny*nz/1e6:.2f}M  cell={cell}")
    XX, YY, ZZ = np.meshgrid(xs, ys, zs, indexing='ij')
    P = np.stack([XX.ravel(), YY.ravel(), ZZ.ravel()], axis=1)
    D = sdf_body(P).reshape(nx, ny, nz).astype(np.float32)
    print(f"  SDF 范围 [{D.min():.3f}, {D.max():.3f}]")
    verts, faces, nrm, _ = measure.marching_cubes(
        D, level=0.0, spacing=(cell, cell, cell),
        gradient_direction='ascent', allow_degenerate=False, method='lewiner')
    verts = verts + np.array([x0, y0, z0], dtype=np.float64)
    print(f"  marching cubes  顶点 {len(verts)}  三角 {len(faces)}")
    verts, faces = largest_component(verts, faces)
    verts = laplacian_smooth(verts, faces, iters=3, lam=0.28)
    # 先落地，在 SDF 坐标系里刷材质（XZ 居中会把计时器/眼睛的 z 阈值打乱）
    verts[:, 1] -= verts[:, 1].min()
    cents = verts[faces].mean(axis=1)
    face_mat = classify_points(cents)
    verts[:, 0] -= 0.5 * (verts[:, 0].min() + verts[:, 0].max())
    verts[:, 2] -= 0.5 * (verts[:, 2].min() + verts[:, 2].max())
    c0, c1, c2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    fn = np.cross(c1 - c0, c2 - c0)
    front = cents[:, 2] > np.quantile(cents[:, 2], 0.85)
    if front.any() and float(fn[front, 2].mean()) < 0:
        faces = faces[:, ::-1]
        print("  已翻转三角绕序（法线朝外）")
    normals = vertex_normals(verts, faces)
    return verts, faces, normals, face_mat


def print_report(verts, faces):
    mn, mx = verts.min(0), verts.max(0)
    print("  包围盒 "
          f"X[{mn[0]:.3f},{mx[0]:.3f}] "
          f"Y[{mn[1]:.3f},{mx[1]:.3f}] "
          f"Z[{mn[2]:.3f},{mx[2]:.3f}]")
    print(f"  身高 {mx[1]-mn[1]:.3f} m  翼展 {mx[0]-mn[0]:.3f} m  落地 y={mn[1]:.4f}")
    span = mx[0] - mn[0]
    if span < 1.3:
        print(f"  ⚠ 翼展 {span:.3f}m 过窄，胳膊可能没接到身上")
    print("  Mixamo：人形✓  单网格✓  T-pose(臂沿X)✓  无附件✓  面向+Z✓  原点居中✓")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, 'assets', 'output')
    os.makedirs(out, exist_ok=True)
    print("生成初代奥特曼 T-pose 单网格…")
    verts, faces, normals, face_mat = build_mesh(cell=0.009)
    print_report(verts, faces)

    obj_p = os.path.join(out, 'Ultraman_Classic.obj')
    mtl_p = os.path.join(out, 'Ultraman_Classic.mtl')
    write_mtl(mtl_p)
    write_obj(obj_p, verts, faces, normals, face_mat)
    zip_p = os.path.join(out, 'Ultraman_Classic.zip')
    with zipfile.ZipFile(zip_p, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(obj_p, 'Ultraman_Classic.obj')
        z.write(mtl_p, 'Ultraman_Classic.mtl')

    print("渲染三视图…")
    views = {
        'preview_front.png': (np.array([0.0, 0.96, 4.55]), np.array([0.0, 0.95, 0.0]), 'FRONT  +Z'),
        'preview_side.png':  (np.array([4.55, 0.96, 0.0]), np.array([0.0, 0.95, 0.0]), 'SIDE   +X'),
        'preview_34.png':    (np.array([2.70, 1.15, 3.20]), np.array([0.0, 0.95, 0.0]), '3/4'),
        'preview_head.png':  (np.array([0.18, 1.70, 0.95]), np.array([0.0, 1.70, 0.08]), 'HEAD'),
    }
    thumbs = []
    for name, (eye, look, title) in views.items():
        img = render_view(verts, faces, normals, face_mat, eye, look)
        im = stamp(img, f'Ultraman Classic  T-pose  {title}')
        im.save(os.path.join(out, name))
        thumbs.append(im)
        print(f"  {name}")

    # 三视图拼图（不含头部特写）
    trio = thumbs[:3]
    board = Image.new('RGB', (trio[0].width * 3, trio[0].height), (10, 12, 18))
    for i, im in enumerate(trio):
        board.paste(im, (i * im.width, 0))
    board.save(os.path.join(out, 'preview_turnaround.png'))

    print(f"✓ {obj_p}")
    print(f"✓ {zip_p}   ← 上传 Mixamo 用这个（OBJ+MTL）")
    print(f"  顶点 {len(verts)}  三角 {len(faces)}  "
          f"红 {int((face_mat==1).sum())}  眼 {int((face_mat==2).sum())}  "
          f"计时器 {int((face_mat==3).sum())}  耳 {int((face_mat==4).sum())}")
    import shutil, subprocess
    blender = shutil.which('blender')
    if blender:
        exp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'export_mixamo_fbx.py')
        print('导出 FBX…')
        subprocess.check_call([blender, '--background', '--python', exp])
        print(f"✓ {os.path.join(out, 'Ultraman_Classic.fbx')}")
    # 同步到用户整理的 classcial ultraman 目录
    dest = os.path.join(out, 'classcial ultraman')
    os.makedirs(dest, exist_ok=True)
    for n in ('Ultraman_Classic.obj', 'Ultraman_Classic.mtl', 'Ultraman_Classic.zip',
              'Ultraman_Classic.fbx', 'preview_front.png', 'preview_side.png',
              'preview_34.png', 'preview_head.png', 'preview_turnaround.png'):
        src = os.path.join(out, n)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, n))
    print(f"✓ 已同步 {dest}")


if __name__ == '__main__':
    main()
