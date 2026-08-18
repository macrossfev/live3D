# SOP · Mixamo 动作流水线（2D 英雄 → 会动的 3D）

> 定版于 2026-08-18（迪迦全链验证通过）。核心程序：`tools/mixamo_pipeline.py`
> 目标：后续同类项目（新英雄/新动作）**一条命令**完成处理。

---

## 1. 全景分工

```
【人工】                          【程序（一条命令）】                 【产出】
DG 等 AI 生成 FBX + 贴图   ──┐
Mixamo 上传 → 绑骨 → 存角色 ──┤→  tools/mixamo_pipeline.py   →   单文件 GLB
Mixamo 挑动作 → 下载 FBX  ──┘   (法线修复/穿皮/压缩/自检/演示页)   (+演示页)
```

## 2. 人工步骤细节

### 2.1 素材（每个英雄一次）
- AI 服务（如 DG）生成：**FBX + 贴图组**（基色/发光/法线…）
- 注意：贴图组里可能有**蓝底通道图**（如 `xxRGB.png`，整图偏蓝、非基色）——程序会自动排除，也可 `--base` 指定

### 2.2 Mixamo 绑骨（每个英雄一次）
1. 打开 [mixamo.com](https://www.mixamo.com) → **Upload Character** → 传 FBX
2. 自动绑骨界面：**下巴、双手腕、双脚踝**四个标记点拖准 → Next → 保存角色
3. 这一步生成"合身骨架 + 专业权重"——**手不脱节、装饰不钉死**的根本保证

### 2.3 下载动作（每个动作一次）
- 在角色上挑动作 → Download
- **第一份选 `With Skin`**（网格+骨架+权重，流水线输入）
- 后续动作可 `Without Skin`（文件小；骨名一致直接挂）

## 3. 程序使用（核心）

```bash
cd /root/nas/SMB/Mars/live3D

# 标准：With Skin FBX + 贴图目录 + 产物名
python3 tools/mixamo_pipeline.py \
    --fbx   assets/samples/Kicking.fbx \
    --texdir "download/DG/贴图" \
    --name  tiga_kick \
    --demo                      # 顺手生成演示页

# 基色挑错了/想指定：
#   --base 迪迦.png
# 输出到别处：
#   --out /path/to/x.glb
```

### 多动作一次打包（推荐）

```bash
python3 tools/mixamo_pipeline.py \
    --fbx   assets/samples/Punching.fbx \
    --texdir "download/DG/贴图" \
    --name  punching \
    --extra "assets/samples/Kicking.fbx,assets/samples/air-Kicking.fbx,assets/samples/strike_jog.fbx"
```

主 FBX（With Skin）出身体底版，`--extra` 里的 FBX（With/Without Skin 均可）只偷动作，
NLA 并轨导出**一个多动作 GLB**；动作名取文件名。游戏/演示页按 clip 名切换。

程序自动做六件事：
1. **挑基色**（蓝度排序排除通道图；可 `--base` 覆盖）
2. **法线绕向重算**（AI 网格反向区 → 半边/头不渲染的根治）
3. 贴图降采样 1024²、材质组装（基色/发光/法线）
4. 动作重命名为 `--name`（告别 `Armature|mixamo.com`）
5. 导出**单文件 GLB**（网格+权重+骨架+动作+贴图全内嵌，约 2-3MB）
6. **自检**：bbox 身高合理 / 贴图全内嵌 / 动作数 ≥1，不过即报错

产物：
- `assets/output/<name>.glb`
- `tools/<name>_demo.html`（本地 `python3 -m http.server 8099` 后打开验证）

## 4. 验证标准

| 层 | 判据 |
|---|---|
| 程序自检 | bbox y∈(0,3)m、贴图全内嵌、动作≥1（命令不过即失败退出） |
| 像素验证（我做） | 人物前景 >2 万 px、帧差 >2%（在动）、主色调存在 |
| **人眼（最终）** | 手不脱节 / 饰件跟随 / 贴图颜色正确 / 左右半身+头都在 |

## 5. 已知坑（历史教训，程序已内置规避）

| 坑 | 规避 |
|---|---|
| Without Skin FBX 没网格（当底版用会崩） | `--extra` 只偷动作；底版必须 With Skin |
| With Skin 的动作 FBX 带重复网格（多迪迦叠影/scale=100） | 并入时自动删多余 MESH/ARMATURE |
| Mixamo 下载单位 cm/m 不一（模型变 15cm 或 30m） | 世界身高归一化（matrix_world 校正，不 apply） |
| skinned mesh 的 bbox/缩放链自检都不可靠 | 双口径自检 + 浏览器像素实测兜底 |
| Blender 3.4.1 glTF 导入器 + 新 numpy 崩 | 流水线不回读 GLB，从 FBX 一步重建 |
| `xxRGB.png` 是蓝底通道图非基色 | 自动蓝度排序 + `--base` |
| AI 网格绕向翻转（半边/头不渲染） | Blender `normals_make_consistent` |
| 我自己绑骨（标准骨架+自动权重）→ 手脱节/饰件钉死 | **禁用**，必须 Mixamo With Skin 下载 |
| Blender(3.4.1) FBX 无法内嵌贴图 | 一律以 **GLB** 为交付格式 |
| 演示页画布 1280 宽 vertexColors 失效 | 画布固定 620×900 |
| 线上大文件偶发"慢对象"（16KB/s） | 重发一次即恢复；GLB 控制 ≤3MB |
| Boxing 等 Mixamo FBX 首帧是蹲姿 | 摆拍用 `mixer.stopAllAction()` 回绑定姿势 |

## 6. 移植到其他项目

`tools/mixamo_pipeline.py` **零项目耦合**（路径全部由参数/相对 ROOT 决定）：
拷到新项目 `tools/` 下，装好 `blender`(3.4+)、`python3-PIL/numpy` 即可用同样命令跑。
演示页模板内嵌在脚本 `DEMO_TPL` 里，随脚本走。

## 7. 端到端验收记录

- 2026-08-18 迪迦/Kicking：基色自动选中 `迪迦.png`（蓝度 -4 vs RGB 版 -135）；
  产物 2.6MB；自检过；浏览器像素验证：前景 5.6 万 px、紫 1.6%、帧差 16.9% ✓
