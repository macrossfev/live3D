#!/usr/bin/env python3
"""acceptance_check.py — live3D 验收门 G2/G3/G5/G6（对浏览器页面截图跑）

用法:
  python3 tools/acceptance_check.py <screenshot.png> [--view front] [--json out.json]

门禁（docs/SOP_pipeline.md §3，阈值不得为过关而改）：
  G2 渲染存在性: 8 个身体高度带各有实体像素 ≥3%
  G3 空间落位(front): 肩带红>0% 胸盾带红>5% 腰盆带红>10% 小腿带红<1%
  G5 人脸清除: 类肤色像素 <0.1%
  G6 无遮挡异常: 最宽单色连通占比<60% 用直方图众数近似; 全屏均亮<120
"""
import sys, json, argparse
import numpy as np
from PIL import Image

# 身体带（占人物高度的比例，自头顶 0 → 脚底 1；来自立绘锚点）
BANDS = [
    ('head',   .00, .13), ('shoulder', .13, .22), ('chest', .22, .35),
    ('waist', .35, .45), ('pelvis', .45, .55),
    ('thigh', .55, .72), ('shin', .72, .93), ('foot', .93, 1.0),
]

def analyze(path, view='front', cropx=0):
    im = np.array(Image.open(path).convert('RGB')).astype(int)
    if cropx: im = im[:, :cropx]
    h, w = im.shape[:2]
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    lum = im.mean(-1)
    # WebGL 背景(lum≈68)高于旧阈值：前景 = 离画面主导色足够远的像素
    q = (im // 16 * 16).reshape(-1, 3)
    vals, cnts = np.unique(q, axis=0, return_counts=True)
    bgc = vals[cnts.argmax()].astype(int)
    fg = (np.abs(im - bgc).sum(-1) > 60)
    ys, xs = np.where(fg)
    out = {'file': path, 'view': view, 'size': f'{w}x{h}', 'gates': {}}
    if len(ys) < 500:
        out['gates']['G2'] = {'pass': False, 'err': '前景不足（模型没渲染？）'}
        return out
    y0, y1 = ys.min(), ys.max()
    out['figure_bbox'] = [int(y0), int(y1)]
    fh = y1 - y0
    red = (r > 90) & (r > g * 1.7) & (r > b * 1.7) & fg
    sil = (r > 120) & (g > 120) & (b > 120) & fg
    # G2: 各带实体覆盖
    g2 = {}
    for name, a, bnd in BANDS:
        ya, yb = int(y0 + fh * a), max(int(y0 + fh * bnd), int(y0 + fh * a) + 1)
        cov = fg[ya:yb].mean()
        g2[name] = round(float(cov), 3)
    out['gates']['G2'] = {'pass': bool(all(v >= .03 for v in g2.values())), 'bands': g2}
    # G3: 红的空间落位（仅正面视图判定）
    if view == 'front':
        def band_red(a, bnd):
            ya, yb = int(y0 + fh * a), int(y0 + fh * bnd)
            return float(red[ya:yb].mean())
        m = {'shoulder': band_red(.13, .22), 'chest': band_red(.22, .35),
             'pelvis': band_red(.45, .55), 'shin': band_red(.72, .93)}
        ok = m['shoulder'] > 0 and m['chest'] > .05 and m['pelvis'] > .10 and m['shin'] < .01
        out['gates']['G3'] = {'pass': bool(ok), 'red_by_band': {k: round(v, 4) for k, v in m.items()}}
    # G5: 肤色残留
    skin = (r > 130) & (g > 85) & (g < 175) & (b < 130) & (r > g) & (g > b) & fg \
           & ~((r > 200) & (g > 200))          # 排除高光白
    out['gates']['G5'] = {'pass': bool(skin.mean() < .001), 'skin_pct': round(float(skin.mean()), 5)}
    # G6: 众数色占比 + 均亮
    q = (im // 24 * 24).reshape(-1, 3)
    vals, cnts = np.unique(q, axis=0, return_counts=True)
    mode_share = float(cnts.max()) / q.shape[0]
    # G6：画面级均亮 + 人像区内单色占比（背景占帧不算遮挡）
    fig_q = (im[fg] // 24 * 24)
    if len(fig_q):
        fv, fc = np.unique(fig_q, axis=0, return_counts=True)
        fig_mode = float(fc.max()) / len(fig_q)
    else:
        fig_mode = 0.
    out['gates']['G6'] = {'pass': bool(fig_mode < .6 and lum.mean() < 120),
                          'figure_mode_share': round(fig_mode, 3),
                          'mean_lum': round(float(lum.mean()), 1)}
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('png'); ap.add_argument('--view', default='front')
    ap.add_argument('--json', default=None)
    ap.add_argument('--cropx', type=int, default=0, help='只分析画布区（右缘 x）')
    a = ap.parse_args()
    rep = analyze(a.png, a.view, a.cropx)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    if a.json:
        json.dump(rep, open(a.json, 'w'), ensure_ascii=False, indent=1)
