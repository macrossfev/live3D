# live3D 交接单 · 给 GLM 5.3

> **仓库**：`/root/nas/SMB/Mars/live3D`  
> **线上**：https://page.sui.pics/a/live3d-dist-06a0685f3514417e/  
> **GitHub**：https://github.com/macrossfev/live3D  
> **日期**：2026-08-18  
> **你是谁**：制作 agent。按本文 + `docs/SOP_pipeline.md` 干活。  
> **谁验收外观**：只有用户。你没有可靠视觉，禁止用「我看过没问题」结案。

先读：

1. `README.md`（项目契约、三条路线、踩坑）
2. `docs/SOP_pipeline.md`（流水线 + 验收门 G1–G7 + 头部实验）
3. 本文（问题清单 + 本轮要交付什么）

不要重读整份 `docs/SOP_mixamo.md`，除非你在改 Mixamo 上传网格。

---

## 0. 一句话目标

**用 Ready Player Me 全身骨架，把初代奥特曼 T-pose 立绘做成能播 Mixamo 动画、头也像奥特曼的角色。**  
骨架和出拳已经通了。卡在头。

---

## 1. 已经成立（不要重做、不要推翻）

| 项 | 位置 / 证据 | 含义 |
|----|-------------|------|
| 输入立绘 ×6 | `assets/refs/classic.png` 等 | 正面 T-pose 透明 PNG，初代用 classic |
| RPM 底座 | `assets/rpm/avatar_full.glb` | 81 骨，A-pose，头是独立网格 |
| Mixamo 动画直通 | `assets/samples/Boxing.fbx` + `tools/rpm_ultraman.html` | 剥 `mixamorig` 前缀，Hips 位移 ×0.01 |
| 身体投影蒙皮 | 同页 | 红带落在肩/胸盾/腰盆，有像素统计 |
| SDF / Blender 网格 | `tools/gen_ultraman_obj.py`、`gen_ultraman_blender_tpose.py` | 可出 Mixamo 用单网格，是另一条线 |
| 姊妹项目 | `../ultraman-web` | 游戏消费端，不要在那边改 live3D 逻辑 |

**不要再碰：**

- 克隆壳 / 拉普拉斯把头写回局部（SOP 称 A3，炸过屏，已冻结）
- 用节点矩阵当蒙皮世界坐标（必须走 `bindMatrix` + 骨权重）
- 对整模型做包围盒/采样而不先丢掉孤立顶点（y=176 / y=-1）
- 手臂用立绘正交投影（RPM 是 A-pose，手臂只能按骨名配色）
- Debian Blender 3.4.1 的 Cycles 无头烘焙（会全黑；贴图用 numpy 光栅）
- WebGL `toDataURL` 当验收截图
- 没过自动门就 `page-publish`
- 开放式问视觉模型「效果怎么样」（会编）

---

## 2. 问题清单（按优先级）

### P0 · 头部不像奥特曼（本轮主问题）

**现象**：身体可以投影出红银分区；头仍是 RPM 人脸，或旧实验里的球体堆 / 组合盔 / 克隆壳，用户都不收。

**技术事实**：

- 头网格名：`Wolf3D_Head`（约 2123 顶点），身体 `Wolf3D_Body` **没有头**
- 衣物、毛发、眼镜、齿、眼球都是独立网格，蒙皮前必须藏掉
- 人头有鼻子耳朵，贴奥特曼面罩纹也盖不住侧光体积

**用户会看的脸部项**（任一 ✗ 就回炉）：

```
□ 盔型 / 头冠脊
□ 眼睛：大小、杏仁形、外眼角上挑、发光黄
□ 下颚红区位置和形状
□ 没有 RPM 人脸/肤色露出来
□ 不挡身体、不糊满屏
```

### P1 · 验收自动化没写

`tools/acceptance_check.py` **不存在**。SOP §3 的 G1–G7 只写在纸上。没有它，容易再发「身体没了」那种版。

### P2 · 头部两条候选还没出可对比样品

SOP §5 要求 **A1 与 A2 各一版**，同一相机、同一身体，交用户盲选。现在两版都没有可发布的验收包。

### P3 · 立绘投影在手臂上不可用

RPM 默认 A-pose，立绘是 T-pose。手臂必须按骨骼名刷色（上臂红、前臂+手银），禁止把 T-pose 图往胳膊上投。

### P4 · 泛化未做

`assets/refs/` 已有 6 英雄 T-pose。当前代码写死初代 classic。六人换皮是后话，**本轮不做**。

### P5 · 与 ultraman-web 未接通

游戏里还是旧 3D/2D 骨架。阶段 E 才集成。**本轮不做游戏接入**。

---

## 3. 本轮你要交付的东西

按顺序做。做完 3.1 再 3.2。不要先发线上。

### 3.1 必做：头部决策实验（SOP §5.3）

同一基准：

- 身体：现有 `tools/rpm_ultraman.html` 的投影蒙皮（只动头，别回退身体）
- 相机 / 灯 / 立绘：与现页一致；参考图 `assets/refs/classic.png`
- 藏掉：衣物、毛发、眼镜、齿、眼球、以及会露肤色的原头（A2 必须藏 `Wolf3D_Head`）

**样品 A1 — UV 重绘（先出，省）**

1. 从 `avatar_full.glb` 导出 `Wolf3D_Head` 的 UV 展开图（可 Blender 或 three.js 烘焙）
2. 在 UV 上画初代盔：银面、杏仁黄眼、下颚红、头侧/后脑红、小头冠纹
3. 贴回 `Wolf3D_Head`，保留人头几何
4. 已知风险：侧光看见鼻子/耳朵。样品里必须有左/右侧图，让用户自己否决

**样品 A2 — 几何替换（主力，推荐你多花时间）**

1. 隐藏 `Wolf3D_Head`
2. 用已有 Blender Skin 经验（`tools/gen_ultraman_blender_tpose.py`）单独做一颗头盔：扁脸、头冠脊、耳板、杏仁眼凸起（不要挖穿的眼窝）
3. 导出 GLB，挂到 Head 骨（挂接方式页里已验证过，跟现有骨骼走）
4. 单位米；随 Head 骨转动

**每个样品交一份验收包**（目录不要中文、不要空格）：

```
docs/acceptance/head-a1/
docs/acceptance/head-a2/
```

每包至少：

| 文件 | 内容 |
|------|------|
| `front.png` `back.png` `left.png` `right.png` | 冻结 pose t=0，约 1280×900 |
| `q34_left.png` `q34_right.png` | 左 3/4、右 3/4 |
| `top.png` `bottom.png` | 俯、仰 |
| `compare.png` | 左立绘（同高度裁）右渲染，中间眼/肩/膝参考线 |
| `report.json` | 见 §4 门禁字段；没有脚本就手写统计也行 |
| `NOTES.md` | 你改了哪些文件、怎么跑、已知瑕疵（事实，不写「看起来很好」） |

截图：**用浏览器对页面截图**，不要 `canvas.toDataURL`。

文件名不要带 `a1`/`a2` 以外的暗示性形容词，交给用户时可以说「目录 A 和目录 B」，方便盲选。

### 3.2 强烈建议顺手：验收脚本骨架

新建 `tools/acceptance_check.py` 或页内 `window.__accept()`，至少实现：

| 门 | 最低判据 |
|----|----------|
| G2 | 8 个高度带（头/胸/腰/盆/左右大腿/左右小腿）各自身体像素 ≥3% |
| G3 | 红像素：肩带>0，胸盾带>5%，腰盆带>10%，小腿带<1% |
| G5 | 类肤色像素 <0.1%（头方案过关的关键） |
| G6 | 没有单色物体占画面 >60%；全屏均亮 <120 |

输出 JSON 写进对应 `docs/acceptance/head-a*/report.json`。

G1/G4/G7 可先占位。过不了的门写明数字，**不要改阈值硬过**。

### 3.3 明确不要做

- 不要发 page-publish
- 不要改 `../ultraman-web` 游戏逻辑
- 不要给赛文/泰罗等换皮
- 不要重写 Mixamo SDF 全身（那是路线 A/B，本轮是路线 C 的头）
- 不要复活克隆壳
- 不要为了「好看」换 Mixamo 骨架

---

## 4. 关键文件（改之前先打开）

| 路径 | 作用 |
|------|------|
| `tools/rpm_ultraman.html` | 主演示：投影蒙皮 + Boxing。本轮主要改进点 |
| `tools/rpm_viewer.html` | 查网格名、骨名、权重 |
| `assets/rpm/avatar_full.glb` | 底座，只读，不要覆盖 |
| `assets/refs/classic.png` | 初代 T-pose 立绘，真理来源 |
| `assets/samples/Boxing.fbx` | 动画验收 |
| `tools/gen_ultraman_blender_tpose.py` | A2 头盔可复用的 Skin 建模 |
| `tools/archive/` | **改 html 前先 `cp` 一份进来**（曾经丢过可回退版） |

改 `rpm_ultraman.html` 之前：

```bash
mkdir -p /root/nas/SMB/Mars/live3D/tools/archive
cp /root/nas/SMB/Mars/live3D/tools/rpm_ultraman.html \
   /root/nas/SMB/Mars/live3D/tools/archive/rpm_ultraman.html.bak-before-head
```

本地预览必须 HTTP：

```bash
cd /root/nas/SMB/Mars/live3D
python3 -m http.server 8099
# http://localhost:8099/tools/rpm_ultraman.html
```

---

## 5. 实现时必须遵守的技术约束

1. 找头：只认名字 `Wolf3D_Head`，不要遍历猜。
2. 蒙皮世界坐标：

   `Σ wᵢ · (boneWorld · boneInv) · bindMatrix · v`

3. 统计 / 投影前：只统计被索引用到的顶点；丢掉 y≈176、y≈-1、以及 `y∉(0,2.2)` 或 `|x|>1.2`。
4. FBX 骨名：加载后是 `mixamorigHips` 这种，没有冒号。
5. 手臂：`LeftArm` / `RightArm` / `ForeArm` / `Hand` 用程序色，不采样立绘。
6. 水平比例用**骨盆带宽**标定，不要用肩膀（A-pose 会漂）。
7. 发布路径、验收目录：英文、无空格。

立绘参数（A1/A2 建模用，可再量一次像素核对）：

- 图：768×1360，中线约 x=386
- 银面 + 杏仁黄眼 + 下颚红 + 头侧/后脑红 + 头顶小鳍
- 胸口圆形计时器（青白芯、深色圈）在身体上，不在头上

---

## 6. 你怎么算做完

写一份 `docs/acceptance/README.md`，三句话即可：

1. A1 / A2 目录路径
2. 各门数字（过/没过）
3. 请用户打开哪两个文件夹做盲选（脸部 checklist）

**不要**宣布「头部完成」。用户盲选胜者之后才进动画精修（阶段 D）和游戏接入（阶段 E）。

若两版用户都否：根据他的 ✗ 项各再改一轮，**最多再一轮**，然后停，把否决项写回本文或 NOTES。

---

## 7. 环境

- 工作目录：`/root/nas/SMB/Mars/live3D`
- Python3 + numpy / Pillow；Blender 3.4.1 在 PATH（`blender -b -P ...`）
- **这台机器没有 NVIDIA GPU**。不要装 Wonder3D / 本地扩散出头。
- 不要为出图去跑重型渲染农场；Workbench / 软件光栅 / 浏览器截图即可。
