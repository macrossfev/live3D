# live3D — 2D 立绘 → Mixamo 可用 3D 模型

> 从 `ultraman-web` 的虚拟人管线拆分而来 · 2026-08-18 建项
> 定位：**输入一张 2D 角色立绘（T-pose 透明 PNG），输出能上传 Mixamo 自动绑骨、
> 并被 Mixamo 动画库驱动的 3D 模型（FBX/GLB）**。

---

## 1. 输入 / 输出契约

| | 规格 |
|---|---|
| **输入** | 正面 T-pose 站姿透明 PNG（≥768×1360，人物完整、双脚落地、参照 `assets/refs/*.png`） |
| **输出** | FBX（首选）+ OBJ/MTL/贴图 ZIP；要求：单一人形网格、水密、A/T-pose、原点居中、脚踩 y=0、（可选）烘焙贴图 |
| **验收** | 上传 [mixamo.com](https://www.mixamo.com) 自动绑骨成功 + 任选动画预览无破面，即为合格 |

## 2. 三条已探路线（均有可运行产物）

| 路线 | 工具 | 产物 | 结论 |
|---|---|---|---|
| **A. SDF 符号距离场** | `tools/gen_ultraman_obj.py`（numpy SDF + marching cubes） | `assets/output/Ultraman_Classic.*` | 几何质量最高（水密单网格）；造型靠手调 SDF 参数 |
| **B. Blender Skin 修改器** | `tools/gen_ultraman_blender_tpose.py`（现役）/ `_v1/_v2`（存档） | `assets/output/blender/` | 快速有机人形；**贴图烘焙链已修通**（numpy 软件光栅化，绕过该构建的 Cycles 烘焙黑屏 bug） |
| **C. RPM 换体 + 投影蒙皮** | `tools/rpm_ultraman.html`（演示）/ `rpm_viewer.html`（探针） | 浏览器实时 | **骨架/动画已验证可用**（81 骨 Mixamo 同源 + Mixamo FBX 直通）；外观待头部方案落地（见 SOP §5） |
| 辅助 | `tools/obj_view.html`（OBJ 检视）/ `ultraman_preview.html`、`render_ultraman.py`（预览渲图）/ `unwrap_ultraman.py`（UV 展开）/ `export_mixamo_fbx.py`（OBJ→FBX） | | |

## 3. 快速开始

```bash
# 路线 A：SDF 生成（零依赖，仅需 numpy）
python3 tools/gen_ultraman_obj.py

# 路线 B：Blender Skin + 立绘投影烘焙（本机 blender 3.4.1）
blender -b -P tools/gen_ultraman_blender_tpose.py

# 路线 C：RPM 演示页（需本地起 http 服务，工具目录的相对路径基于 web 根）
python3 -m http.server 8099   # 然后开 http://localhost:8099/tools/rpm_ultraman.html

# 检视产物
python3 -m http.server 8099 && 打开 tools/obj_view.html
```

## 4. 关键技术事实（踩坑沉淀，改代码前先读）

1. **RPM 模型结构**：头是独立网格 `Wolf3D_Head`（身体无头）；衣物/毛发/眼镜/齿/眼球全是独立网格；全身像默认 **A-pose**（与 T-pose 立绘的手臂不可直接投影）
2. **SkinnedMesh 世界坐标** = `Σ wᵢ·(boneWorld·boneInv)·bindMatrix·v`——用节点矩阵直变换是错的
3. **GLB 孤立垃圾顶点**（y=176 / y=-1）：一切范围统计必须按索引引用过滤
4. **FBXLoader 吃冒号**：`mixamorig:Hips` → `mixamorigHips`；Mixamo 厘米制，Hips 位置轨 ×0.01
5. **Blender(Debian 3.4.1) 三坑**：Cycles 无头烘焙全黑（用 numpy 软件光栅化替代）；`img.save()` 必须先 `pack()`；像素缓冲自底向上（要 `[::-1]` 翻转）
6. **验收方法论**：agent 无直接视觉；视觉模型描述会虚构。自动验收只用像素统计（空间带分布），视觉裁决归人类。截图用 agent-browser 页面截图，不用 WebGL `toDataURL`

## 5. 当前状态与路线图

- ✅ 骨架与动画直通（路线 C 底座，Mixamo FBX 已验证驱动）
- ✅ 身体投影蒙皮管线（像素实证：红盾/大腿红带落位）
- ⏳ **头部方案决策实验**（`docs/SOP_pipeline.md` §5）：A1 UV 重绘 vs A2 几何替换，盲选出线；克隆壳路线已冻结
- ⏳ 泛化：参数化"任意 2D 角色 → 模型"（当前以初代奥特曼为样例；`assets/refs/` 已有 6 英雄 T-pose 图）
- ⏳ 验收门 G1-G7 脚本化（`tools/acceptance_check.py` 待建）

## 6. 目录结构

```
live3D/
├── README.md                 ← 本文档
├── docs/
│   ├── SOP_制作与验收.md      ← 制作流水线 + 验收门 G1-G7 + 头部决策实验（必读）
│   └── SOP_Mixamo建模.md      ← Blender 建模操作规程（Mixamo 侧）
├── tools/                    ← 全部生成/检视/转换工具（§2 表）
├── assets/
│   ├── refs/                 ← 输入立绘（T-pose ×6 + A-pose 样例）
│   ├── rpm/                  ← Ready Player Me 全身 GLB ×2
│   ├── samples/              ← 示例动作 FBX（Boxing）
│   └── output/               ← 生成产物（OBJ/FBX/贴图/预览图）
```

## 7. 关联项目

- **`../ultraman-web`**（消费端）：游戏本体。Mixamo 下载的动画 FBX 用其
  `tools/fbx_convert.html` 转成游戏剪辑 JSON；RPM 骨架复用其 `engine/hero3d.js` 渲染层
- 部署：`page-publish`（同一 ccc-pages 体系），ultraman 线上页
  `https://page.sui.pics/a/index-612e62ba966f0f98/`

## 8. License

MIT（工具代码）。立绘为粉丝向素材，产物仅供个人学习，不得商用。
