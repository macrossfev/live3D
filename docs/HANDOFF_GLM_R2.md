# live3D 交接单 R2 · 给 GLM 5.3（上一轮否决后）

> **仓库**：`/root/nas/SMB/Mars/live3D`  
> **日期**：2026-08-18  
> **上一轮**：`docs/acceptance/head-a1/`、`head-a2/` **用户判定失败**——「根本不是奥特曼」。  
> **本轮禁止**：在那两份样品上微调交差；禁止再请用户盲选两个失败品；禁止宣布完成。

先读：`README.md`、`docs/SOP_pipeline.md`、本文。上一份 `HANDOFF_GLM.md` 只当背景，其中「交 A1+A2 盲选」已被否决。

---

## 0. 用户要的结果（一句话）

正面截图和 `assets/refs/classic.png` 并排时，**普通人能认出是初代奥特曼**：有完整身体（胸腹胯腿），头是银面罩 + 一对大黄杏仁眼 + 头冠，不是人脸涂色，也不是红蛋。

做不到这一点 = 没做完。G5/G6 打勾不算。

---

## 1. 上一轮为什么失败（必须先承认，禁止再犯）

对照 `docs/acceptance/head-a1/compare.png` 和 `head-a2/compare.png`：

| 事实 | 原因 |
|------|------|
| 躯干、腰、胯、大腿是空洞，只剩头、红胳膊、白手套、浮空计时器、两截脚 | `rpm_ultraman.html` 把除 `Wolf3D_Body` 外的 SkinnedMesh **全部隐藏**。RPM 可见的胸/裤在 **Outfit** 上，不在 Body 上。衣服一关，人没了。 |
| G2 腰盆/大腿覆盖 = 0% | 同上。NOTES 写成「不当头差异」仍交差，违反 SOP「自动门没过不交付外观」。 |
| A1 是人头 + 红眼罩 + 两点黄 | 保留 `Wolf3D_Head` 的鼻/耳/下巴，只按世界坐标在 UV 上切银/红。奥特曼是面罩体积，不是涂色人脸。 |
| A2 是大红蛋 | `gen_helmet_a2.py` 椭球乱拼，没按立绘量形；面色判据疑反（正面全红）；眼小、冠脊像梗。 |
| 头上没有立绘 | 头没用 `classic.png` 投影或量像素，是程序色块。 |

工程上还踩过、可复用的坑（可以沿用规避，不要再踩）：

- 画布不要改成 1280 宽（vertexColors 会丢），截图用 620×900 再放大
- Boxing `t=0` 是蹲姿，摆拍必须 `mixer.stopAllAction()` 回绑定 A-pose
- 改 html 前先 `cp` 到 `tools/archive/`
- 无 GPU，禁止 Wonder3D / 扩散出头
- 截图用浏览器整页，不要 `toDataURL`

---

## 2. 本轮方案（只走这一条，不要平行开 A1）

```
S1 把身体找回来
  → 正面已能看见完整胸/腰/胯/大腿（G2 全带 ≥3%）
S2 按立绘重做头盔几何，挂 Head 骨
  → 对照板能认出初代的头
然后停，等用户看图
```

**A1（人头 UV 涂色）本轮冻结。** 不要再出 `head-a1`。鼻耳几何盖不成奥特曼。

---

## 3. 阶段 S1 —— 身体必须完整

### 3.1 先列网格（禁止猜名字）

写一个一次性脚本或在 `rpm_viewer.html` 里打印，对 `assets/rpm/avatar_full.glb` 输出每张 SkinnedMesh：

- `name`
- 顶点数
- 世界包围盒（只统计被 index 引用、且 `0<y<2.2 && |x|<1.2` 的点）
- 是否像衣服/身体/头/发/牙/眼

存成 `docs/acceptance/r2/mesh_list.json`。

### 3.2 可见性规则（替换现在的「只留 Body」）

目标：屏幕上是一个**完整站立人**，不是四肢漂浮。

按 `mesh_list.json` 执行：

| 保留并上色 | 隐藏 |
|------------|------|
| 构成躯干/骨盆/大腿体积的网格（Body **以及** Outfit / Top / Bottom / Footwear 等衣服裤） | 发、眼镜、牙、舌、眼球、胡子 |
| | **S2 完成后**再藏 `Wolf3D_Head` |

禁止：`if (skinned && o !== body) visible = false` 这种一刀切。

若 Naked Body 本身就有完整躯干，衣服可以藏，但 **G2 必须先用像素证明** 胸/腰/盆/左右大腿都有实体。证明不了就把衣服打开再上色。

### 3.3 上色

- 躯干正面：继续对 `assets/refs/classic.png` 正交投影（现有 `sampleRef` + `Z2Y` + 骨盆标定 `SX`）
- 手臂：仍按骨名（肩/上臂红，前臂+手银），**不要**对 A-pose 胳膊投 T-pose 图
- 背面：程序红银（现有 `backColor`）
- 投影打到立绘透明底时：用银/红程序色，**禁止留下 (0,0,0)**，否则深色背景上躯干会「消失」

### 3.4 S1 出门条件（没过不准做头）

冻结绑定站姿，拍 `docs/acceptance/r2/body_front.png`：

1. G2：头、肩、胸、腰、盆、左大腿、右大腿、小腿 **每一带覆盖 ≥3%**
2. 人眼：胸腹胯腿连在一起，计时器贴在胸上不是浮在空洞里
3. `compare_body.png`：左立绘右渲染，肩线/腰线/膝线能对上（允许 A-pose 胳膊下垂对不上 T-pose 平举）

过不了就修可见性和上色，**不要做头盔**。

---

## 4. 阶段 S2 —— 按立绘做头盔（唯一头部路线）

身体过门后再做。

### 4.1 形从哪来

真理：`assets/refs/classic.png`（768×1360）。打开图画布量像素，写入 `docs/acceptance/r2/head_metrics.md`，至少：

- 头宽 / 头高（含冠）
- 眼心距、单眼宽高、外眼角上挑
- 下颚红上沿相对眼的高度
- 冠脊长度（额到后）
- 耳板位置

禁止凭感觉写椭球半径。现有 `tools/gen_helmet_a2.py` **可以当脚手架改**，不能原样重导。

### 4.2 头盔必须长什么样（几何，不是贴图凑）

| 部件 | 要求 |
|------|------|
| 颅 | **扁**面罩，前后比左右短，不是圆球 |
| 前脸 | **银色**为主 |
| 下颚 / 头侧 / 后脑 | 红，边界跟立绘走，禁止整头红 |
| 眼 | 一对**大**杏仁凸起，在正前、分得开、外眼角上挑、自发光黄。侧视也能看出灯罩，不是 UV 小点 |
| 冠 | 从前额翻到脑后的小鳍，银；不是头顶 3mm 刺 |
| 耳 | 两侧深色/银色薄板，不要人耳 |
| 无 | 人鼻、人嘴缝、穿透眼窝 |

面色判据必须在 **导出后的 glTF 坐标** 下核对（上一轮 Blender `c.y` 当深度，导完正面全红）。导出后写 20 行脚本：前脸面（+Z）应以银为主，红面占比打印出来。银 < 50% 就改判据重导。

### 4.3 挂接

- 隐藏 `Wolf3D_Head`（S2 阶段）
- 头盔 GLB 挂 `Head` 骨，随头转
- 单位米；下缘接到颈，侧视不要和胸穿成一个瘤
- 输出：`assets/output/helmet_r2.glb`（不要覆盖旧 `helmet_a2.glb`，留作反面教材）

页面：`tools/rpm_ultraman.html?head=r2` 加载新盔。改文件前：

```bash
cp tools/rpm_ultraman.html tools/archive/rpm_ultraman.html.bak-before-r2
```

### 4.4 头上的纹

头盔几何分区（银/红/眼）即可。若再投影，只投 **头区立绘** 到盔的正面，不要世界坐标一刀切画在人头 UV 上。

---

## 5. 本轮交付目录

```
docs/acceptance/r2/
  mesh_list.json
  head_metrics.md
  body_front.png          ← S1 出门
  compare_body.png
  front.png back.png left.png right.png
  q34_left.png q34_right.png
  top.png bottom.png
  compare.png             ← 左立绘右全身（含新头）
  report.json             ← G2/G3/G5/G6，阈值不要为过而改
  NOTES.md                ← 改了哪些文件、网格保留名单、已知瑕疵（事实）
```

不要再写 `head-a1`。旧目录保留，勿删。

`report.json` 的 G2 必须带齐：**pelvis、左右大腿不能再是 0**。仍为 0 = S1 没做完。

---

## 6. 用户验收（你写 NOTES，他打勾）

对照 `compare.png`：

```
□ 身体完整（胸腹胯腿连着，不是漂浮四肢）
□ 头是盔不是人脸、不是红蛋
□ 银面 + 一对能看清的黄杏仁眼
□ 有头冠鳍
□ 下颚/头侧有红，且正面不是整头红
□ 计时器在胸口贴着身体
□ 没有 RPM 肤色脸
```

你 **不得** 自己勾。交包后停。

---

## 7. 明确不要做

- 不要发 page-publish
- 不要改 `../ultraman-web`
- 不要六英雄换皮
- 不要重写 Mixamo SDF 全身当本轮主线（S1 实在补不回身体时，才允许用 `assets/output` 里现成全身网格 **只当身体几何** 挂到 RPM 骨架上，须在 NOTES 写清）
- 不要复活克隆壳 / 拉普拉斯写回
- 不要为过门改 G2 阈值
- 不要在 G2 没过时做头盔

---

## 8. 建议动手顺序（按这个打勾）

1. 备份 `rpm_ultraman.html`
2. 列出 `mesh_list.json`
3. 改可见性：衣服/裤子留下，发牙眼镜藏
4. 修投影：透明底回落到银/红，禁止黑顶点
5. 出 `body_front.png`，跑 G2，腰盆大腿必须有数
6. 量 `classic.png` 头写入 `head_metrics.md`
7. 改 `gen_helmet_a2.py` → 输出 `helmet_r2.glb`，打印前脸银占比
8. `?head=r2` 挂盔，藏 `Wolf3D_Head`
9. 出 r2 八视角 + compare
10. 写 NOTES，停

本地：

```bash
cd /root/nas/SMB/Mars/live3D
python3 -m http.server 8099
# http://localhost:8099/tools/rpm_ultraman.html?head=r2
```
