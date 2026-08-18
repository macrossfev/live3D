# SOP · 初代奥特曼 3D 建模（Mixamo 战斗动作）

> **仓库**：`/root/nas/SMB/Mars/ultraman-web`  
> **版本**：2026-08-18  
> **这条线是干什么的**：做出能被 Mixamo 自动绑骨的初代奥特曼单网格，下战斗 FBX，再转成游戏剪辑。  
> **不要走**：AI 图生 3D（慢、拓扑脏、常卡死）、胶囊/球体堆叠当成品、带骨骼再上传 Mixamo。

---

## 0. 何时用 / 何时停

| 情况 | 动作 |
|------|------|
| 要重出初代、改比例/红纹、补 FBX | 从 §3 一条命令重跑 |
| 要给赛文/泰罗/迪迦做同款 | 复制 SDF + 改头冠/配色，见 §7 |
| Mixamo 上传失败 / 绑骨歪 | 先对 §8 排障表，不要重写生成器 |
| 只要 2D 立绘拆件 | **停**，走 `tools/rig_sprites.py`，本 SOP 不管 |
| 要影视级雕刻 / 手指独立动画 | **停**，本管线是风格化人形，不为这个设计 |

---

## 1. 结论（先看这个）

旧模型 `Ultraman_Classic.obj` 是**多段胶囊重叠**，关节处网格互不相连。Mixamo 自动绑骨要「看得出头/躯干/两臂/两腿的一张皮」，胶囊堆会识别失败或绑歪，表现为上传转圈、骨架点对不齐。

现行做法：

```
SDF 人体（光滑并集）
  → marching cubes 抽一张水密网格
  → 最大连通块 + 拉普拉斯平滑 + 翻法线朝外
  → 按空间分区刷 Silver / Red / Eye / Timer
  → OBJ+MTL 打 zip（上传 Mixamo）
  → Blender 无头导出无骨骼 FBX（备用）
  → Mixamo 绑骨 + 下 Punch/Kick/…
  → tools/fbx_convert.html → assets/motions/*.json
```

**上传用这个**：`assets/mixamo/Ultraman_Classic.zip`（只要 OBJ+MTL）。  
FBX 是备用，不要和 zip 混在一个包里传。

现行规格（2026-08-18 初代）：

| 项 | 值 |
|----|----|
| 身高 | ≈ 1.90 m，脚在 y=0 |
| 翼展 | ≈ 1.82 m（真 T-pose，臂沿 X） |
| 朝向 | +Z，原点 XZ 居中 |
| 网格 | 单物体、水密，约 2.9 万顶点 / 5.8 万三角 |
| 姿势 | T-pose，无道具、无骨骼 |
| 材质 | Silver / Red / Eye / Timer |

---

## 2. Mixamo 硬约束（生成器必须守）

Mixamo 自动绑骨**不吃你自带的骨架**，它自己长一套。上传物只要网格对：

1. **人形可辨**：头、颈、躯干、两臂、两腿分开，肩/胯有凹口。
2. **T-pose**：双臂水平向两侧。A-pose 也能试，失败率高。
3. **单网格**：一个 `o`，不要灯/相机/空物体/分离的眼珠道具。
4. **无附件**：剑、光线、披风、过大头冠会干扰。初代小鳍可以留。
5. **脚踩地、原点居中**：`min(y) = 0`，XZ 对称。
6. **面向 +Z**（OBJ 约定：Y-up）。
7. **面数**：建议 &lt; 10 万三角；现行约 5.8 万。
8. **文件**：OBJ+MTL 打 zip，或单独 FBX；总包 &lt; 50 MB。
9. **不要带骨骼**再上传。有骨架时 Mixamo 反而容易报错。

生成器末尾会打印对照清单。缺任一项先改 SDF，不要先去 Mixamo 碰运气。

---

## 3. 一条命令重出模型

依赖：`python3` + `numpy` + `scikit-image` + `Pillow`。FBX 可选：`blender`（Debian 包 3.4 即可）。

```bash
cd /root/nas/SMB/Mars/ultraman-web
python3 tools/gen_ultraman_obj.py
```

脚本会：

1. 建 SDF 体素（默认 `cell=0.010`，约 2.4M 采样，十余秒）。
2. `skimage.measure.marching_cubes` 抽网格。
3. 只留最大连通块；平滑 4 次。
4. 脚落地、XZ 居中；前胸法线若朝里则翻转三角绕序。
5. 面质心刷材质。
6. 写 `assets/mixamo/Ultraman_Classic.obj` + `.mtl`，打 `.zip`。
7. 软件预览：`preview_front.png` / `preview_side.png` / `preview_34.png` / `preview_head.png` / `preview_turnaround.png`。
8. 若 PATH 里有 `blender`，再调 `tools/export_mixamo_fbx.py` 出 `.fbx`。

单独补 FBX / 单独出 Blender 三视图：

```bash
blender --background --python tools/export_mixamo_fbx.py
blender --background --python tools/render_ultraman.py
# 得到 blender_front.png / blender_34.png / blender_side.png
```

交互看模型（必须 HTTP，不要 `file://`）：

```bash
cd /root/nas/SMB/Mars/ultraman-web
python3 -m http.server 8080
# http://localhost:8080/tools/ultraman_preview.html
```

改完 SDF 必须先看 `preview_front.png` 和 `preview_head.png`，再上传。正面没有红 V、没有黄眼、没有计时器，就是分类或法线又翻反了。

---

## 4. 模型是怎么做出来的（改外形时读）

### 4.1 为什么用 SDF，不用胶囊堆

| 做法 | 结果 |
|------|------|
| 球/胶囊/盒子直接写进 OBJ | 多块重叠，关节处是缝不是皮，Mixamo 当破碎网格 |
| Metaball / 布尔不重网格 | 内面、非流形，自动绑骨抽风 |
| SDF + 光滑并集 `smin` + marching cubes | **一张皮**，肩肘膝自然过渡 |

肢体接到躯干时 `smin` 的 k 要**小**（约 0.014–0.018）。k 太大，腋下/裤裆糊成一块，Mixamo 认不出肩和腿。两腿之间只挖一条细胶囊缝，不要挖大方盒（正面会开一条难看的槽）。

**不要在头上做深凹陷**（眼窝大布尔）。洞会打穿后脑，侧面出现黑洞，且非流形。眼睛用贴在脸前的扁椭球加出去。

### 4.2 坐标系与比例

- 单位米。身高约 1.85–1.90。
- Y-up，面朝 +Z，T-pose 臂沿 ±X。
- 关键高度（写在 `gen_ultraman_obj.py` 顶部常量，改比例先改这里）：

| 锚点 | y（米） |
|------|---------|
| 脚底 | 0.00 |
| 踝 | 0.085 |
| 膝 | 0.50 |
| 髋 | 0.96 |
| 腰 | 1.08 |
| 彩色计时器 | 1.255 |
| 胸 | 1.34 |
| 肩 | 1.48 |
| 下颚 | 1.585 |
| 眼 | 1.705 |
| 头顶 | 1.85 |

肩半宽 `SHX ≈ 0.215`，髋半宽 `HIPX ≈ 0.105`。翼展略小于身高，Mixamo 比较认。

体素盒必须包住整个人：`x∈[-1.00,1.00]`，`y∈[-0.02,1.92]`，`z∈[-0.30,0.30]`。胸和计时器往前凸时，先确认 z 上界没切掉计时器。

### 4.3 初代外形（SDF 零件）

全在 `sdf_head` / `sdf_torso` / `sdf_neck` / `sdf_arm` / `sdf_leg`：

- **头**：略扁卵形 + 下颚卵 + 从前额翻到脑后的小鳍 + 两侧耳凸块（不挖孔）+ 一对外眼角上挑的杏仁眼。
- **躯干**：骨盆→腰→腹→胸 一段变半径胶囊，胸深、腰窄；浅胸肌；计时器是胸口正中一颗凸球；后侧补一点臀。
- **颈**：单独短胶囊，头不能直接焊在锁骨上。
- **臂（T-pose）**：肩球（三角肌/肩甲）→ 上臂 → 前臂 → 扁手掌 + 拇指凸起。掌心约向 −Y。
- **腿**：髋球 → 大腿 → 小腿 → 脚椭球朝 +Z。

### 4.4 红银纹（`classify_points`）

按**面质心世界坐标**刷四套材质，不依赖 UV。顺序有覆盖关系，眼和计时器最后写：

| 区域 | 规则要点 |
|------|----------|
| 银面 | 头前上半默认银 |
| 红下颚 / 头侧 / 后脑 | `y>1.55` 且（下颚或 `|x|` 大或 `z` 靠后） |
| 胸前大红 V | 正面三角形：两肩 `(±0.20, 1.545)` → 腰 `(0, 1.08)`，再接一条落到腰的中带，锁骨也涂红连上肩 |
| 肩甲 + 上臂环带 | T-pose 沿 X：`|x|` 在肩到肘前半 |
| 外侧大腿 | `y∈[0.56,0.97]` 且 `|x|` 偏外 |
| 胫前折线 | 小腿中段靠前一条带 |
| 黄眼 | 脸前、左右分开，不要连成一块 |
| 计时器 | 圆心橙，外圈刷回银边 |

改纹样只动 `classify_points`，不必重做拓扑。改完看 `preview_front.png`：应该是红 V 里一颗橙色计时器，不是银色整胸。

### 4.5 法线

`marching_cubes` 绕序有时朝里。生成器在居中之后测「最靠前那批面的法线 z」：均值为负就 `faces[:, ::-1]`。

**判断翻反了的方法**：正面预览整胸是银、侧面却看得到红 V 和计时器 → 你在看后背，绕序反了。

软件预览用画家算法（按深度排三角），只用来看外形和纹样，不代替 Mixamo。

### 4.6 Blender 轴向（改导出脚本时必读）

| 空间 | 上 | 角色朝向 |
|------|----|----------|
| 我们的 OBJ | +Y | +Z |
| Blender 默认导入后 | +Z | −Y |
| Mixamo / 导出 FBX | +Y | +Z |

`export_mixamo_fbx.py` 必须用 **Blender 默认 OBJ 导入**（不要手改 `axis_forward`）。导入后再 `export_scene.fbx(axis_forward='-Z', axis_up='Y')`。

曾经踩过：导入时写 `axis_forward='Z'`，角色在 Blender 里转 180°，所谓「正面渲染」其实是后脑勺；那样导出去的 FBX Mixamo 会当背对镜头。

导出只要网格：`object_types={'MESH'}`，`add_leaf_bones=False`，`bake_anim=False`。灯、相机、空物体全部删掉。多材质物体 `join` 成一个。

自检导入是否正面：Timer 材质面中心应在 Blender 的 **−Y**（约 `y ≈ -0.15`），Z 约 1.25。若 Timer 在 +Y，导入轴反了。

---

## 5. 文件地图

```
ultraman-web/
├── SOP_Mixamo建模.md          ← 本文件
├── tools/
│   ├── gen_ultraman_obj.py    ← SDF → OBJ/MTL/ZIP + 软件预览
│   ├── export_mixamo_fbx.py   ← Blender：OBJ → 无骨骼 FBX
│   ├── render_ultraman.py     ← Blender Workbench 三视图
│   ├── ultraman_preview.html  ← Three.js 轨道预览
│   ├── obj_view.html          ← 旧的加载自检页
│   └── fbx_convert.html       ← Mixamo FBX → 游戏剪辑 JSON
└── assets/mixamo/
    ├── Ultraman_Classic.zip   ← ★ 上传 Mixamo
    ├── Ultraman_Classic.obj
    ├── Ultraman_Classic.mtl
    ├── Ultraman_Classic.fbx   ← 备用上传
    ├── preview_*.png          ← 生成器软件预览
    └── blender_*.png          ← Blender 渲染
└── assets/motions/            ← 从 Mixamo 转回来的 json / 原始 fbx
```

立绘参考（只当配色/纹样，不投影到 UV）：`assets/heroes/classic.png`。

---

## 6. Mixamo 操作（人在浏览器里做）

1. 打开 https://www.mixamo.com 登录 Adobe 账号。
2. **Upload Character** → 选 `assets/mixamo/Ultraman_Classic.zip`。
3. 预览应是 T-pose、正面。若看到后脑，换 zip 不要换 fbx 再试；仍反了就回头查 §4.6。
4. 进入 Auto-Rigger：把标记对到 **下巴、左右腕、左右肘、左右膝、胯**。肩球和手掌是故意做大的，方便对点。
5. Next，等绑骨。成功后能拖旋转、播默认 pose。
6. 搜并下载战斗剪辑（每个都 **FBX、With Skin、30 fps**）：

| Mixamo 搜索词 | 游戏用途 | 建议存成 |
|---------------|----------|----------|
| Punch / Boxing | 近战连拳（＋） | `punch` |
| Kick / Roundhouse Kick | 踢 | `kick` |
| Sword Slash 或类似挥砍 | 斩波（−） | `slash` |
| Idle | 待机 | `idle` |

位移：游戏自己冲步的，下载勾 **In-Place**；要用根骨骼位移的，不勾，之后在 `fbx_convert.html` 里看 `root.tx/ty`。

7. 把 FBX 放到 `assets/motions/`（文件名自定）。
8. 转换：

```bash
cd /root/nas/SMB/Mars/ultraman-web
python3 -m http.server 8080
# 打开 http://localhost:8080/tools/fbx_convert.html
# 选 FBX，动作名选 punch/kick/slash/idle，点转换，下载 json
# 存到 assets/motions/<动作名>.json
```

朝向不对就换页面上的「朝 +Z / 已朝 +X / 朝 −Z」再转一次。预览骨架应朝画面右边出拳（和游戏一致）。

---

## 7. 做下一个奥特曼（赛文 / 泰罗 / …）

不要从零搭身体。身体 SDF 共用，只改：

1. `sdf_head` 的头冠（赛文长鳍、泰罗双角、迪迦水晶、赛罗双冠、泽塔勋章）。`engine/hero3d.js` 的 `PARAMS` 和 `tools/gen_standee.py` 的 `HERO_PRESETS` 已有 crest 类型对照。
2. `classify_points` 的主色区域（迪迦紫、赛罗银蓝等）。计时器位置可共用。
3. 输出文件名改成 `Ultraman_Seven.obj` 这类，**不要覆盖** `Ultraman_Classic.*`。
4. 仍必须 T-pose、单网格、同一套身高锚点，这样 Mixamo 下的同一套动作可以共用。

改完走 §3 → §6。绑骨点位应几乎不用重调。

---

## 8. 排障

| 现象 | 原因 | 处理 |
|------|------|------|
| Mixamo 转圈 / 识别失败 | 多物体、有洞、四肢糊在一起、不是 T-pose | 查预览：腋下和裤裆要有缝；重跑生成器，确认打印清单全 ✓ |
| 绑完手臂扭进胸 | 肩球和胸 `smin` 太大 | 减小臂接入处 k，肩再往外挪 1–2 cm |
| 绑完两腿当一条 | 裤裆没缝或盒缝太宽导致网格破 | 用细胶囊缝，k≈0.006 |
| 正面预览没红 V，侧面有 | 三角绕序朝里，看到的是后背 | 看生成日志有没有「已翻转三角绕序」；没有就检查前胸法线判断 |
| Blender「正面」是后脑 | OBJ 导入轴被改过 | 恢复默认导入，见 §4.6 |
| 眼睛连成一块黄斑 | 两眼太近或分类 `ax` 下限太小 | 眼心 `|x|≈0.058`，分类 `ax>0.022` |
| 计时器正面看不见 | 分类 `z>0.12` 太严，或体素 z 切掉凸包 | 先看包围盒 `Z[min,max]` 是否 ≥ 计时器外沿 |
| 头侧面有黑洞 | 眼窝/耳做了减法布尔 | 删 `smax` 挖洞，只加凸包 |
| FBX 上传 Mixamo 报错 | 带了骨架/多余物体，或轴向错 | 改用 zip（OBJ+MTL）；FBX 必须无骨骼 |
| `fbx_convert.html` 缺骨骼 | Mixamo 下载选了 without skin / 不是人体绑定 | 重新下载 With Skin |
| 游戏出拳朝左 | 转换页朝向差 180° | 换 facing 下拉再转 |
| 重跑后 zip 里混进 fbx | 有人手工把三件打进一个包 | 上传包只许 obj+mtl；脚本默认就是这样 |

---

## 9. 验收清单（说「做好了」之前勾完）

- [ ] `preview_front.png`：T-pose，银面、两只分开的黄眼、红下颚、头冠、胸前红 V、橙色计时器、红肩臂、外侧红大腿、脚在地面线
- [ ] `preview_side.png`：胸和计时器在 +Z，脚尖朝 +Z，没有头上破洞
- [ ] `preview_head.png`：能认出初代，不是光头胶囊
- [ ] 生成日志：单网格、T-pose、无附件、面向 +Z、原点居中、落地 y=0
- [ ] `Ultraman_Classic.zip` 内只有 `.obj` + `.mtl`
- [ ] Mixamo 上传后自动绑骨成功，抬手/抬腿不穿模
- [ ] 至少下一套 Punch，经 `fbx_convert.html` 转出的预览朝右出拳

---

## 10. 明确不做什么

- 不把 AI 图生 3D 的结果直接传 Mixamo（拓扑和姿态几乎总是不合格）。
- 不给这套管线加手指骨骼；战斗拳用掌状手即可。
- 不在本 SOP 里改 2D 立绘拆件或 `index.html` 出招逻辑。
- 不商用。角色造型是粉丝向参数化原创，纹样只参考项目内立绘。
