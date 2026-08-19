# live3D 交接单 · 下一棒（游戏集成 + 六英雄量产）

> **日期**：2026-08-19
> **你将接手**：把已验证的 Mixamo 动作 GLB 接进 `../ultraman-web` 游戏，替换现有方块人。
> **前置阅读顺序**：`README.md` → `docs/SOP_mixamo_pipeline.md` → `docs/WORKLOG.md`（三篇全读）→ 本文。
> 历史文档 `HANDOFF_GLM*.md`、`SOP_pipeline.md` 是 2D 投影路线的存档，**那条路已被
> "DG 生成 + Mixamo 绑骨"取代**，只当背景读。

---

## 0. 现状一句话

**流水线已定版并全链验证**：AI(DG)生成身体+贴图 → Mixamo 绑骨下载 →
`tools/mixamo_pipeline.py` 一条命令 → 多动作自包含 GLB（含法线修复+穿皮）。
迪迦样例：`assets/output/tiga_motions.glb`（4 动作，线上演示 `tools/tiga_motions.html`）。

## 1. 已成立，不许推翻

| 事实 | 证据/位置 |
|---|---|
| 流水线命令与参数 | `docs/SOP_mixamo_pipeline.md` §3（含 `--extra` 多动作） |
| 12 条坑与规避 | 同上 §5（蓝底通道图/绕向/单位/重复网格/蒙皮自检…） |
| 迪迦 4 动作产物 | `assets/output/tiga_motions.glb` + `tools/tiga_motions.html` |
| Mixamo 侧 SOP | `docs/SOP_mixamo.md` |
| 游戏侧现状 | `../ultraman-web`：HERO3D（Three.js）+ 2D rig 双引擎，README §虚拟人管线 |
| 版本管理 | git 已建；线上 page.sui.pics slug=`live3d-dist-06a0685f3514417e`（v19） |

## 2. 本轮任务（按序）

### 2.1 游戏集成（主任务）
在 `../ultraman-web/engine/hero3d.js`（或新增 hero3d_mixamo.js）加 GLB 分支：
- GLTFLoader 加载 `live3D/assets/output/tiga_motions.glb`（拷进游戏 assets 或跨目录引用）
- AnimationMixer + clip 按**运算符→招式**映射（参考 index.html 的 `HERO_MOVES`）：
  ＋→Punching、−→Strike Jog 斩、×→远程（现有光线特效保留）、必杀→Taunt 起手
- 攻击时的 meleeDash / hit-stop / 摄像震动逻辑沿用（clip 换源不动编排）
- 画布 620×900（1280 宽会瞎，见 SOP 坑清单）；`frustumCulled=false` 记得设
- 验收：答对出招动作正确切换、帧差>2%、线上可玩

### 2.2 六英雄量产（集成验证后）
每英雄：DG 生成 → Mixamo 绑骨一次 → 每招式下载一份 →
`mixamo_pipeline.py --extra` 打包 → 游戏侧只换 GLB 与配色参数。
产出物命名：`assets/output/<hero>_motions.glb`。

### 2.3 明确不要做
- 不要复活 2D 投影/克隆壳/自行绑骨路线（WORKLOG 有完整尸检）
- 不要动 `tools/mixamo_pipeline.py` 已验证的行为（要改先跑 Kicking 回归）
- 不要发 ultraman-web 线上（index-612e62ba966f0f98）未经用户点头——那是孩子在玩的页

## 3. 关键文件

| 路径 | 说明 |
|---|---|
| `tools/mixamo_pipeline.py` | 一键流水线（改前读内嵌 BLENDER_SCRIPT 注释） |
| `assets/output/tiga_motions.glb` | 当前唯一验证过的多动作产物 |
| `tools/tiga_motions.html` | 动作切换参考实现（1-4 键） |
| `assets/samples/*.fbx` | 用户下载的 Mixamo 动作原始件（勿删） |
| `download/DG/` | 用户 AI 生成素材（贴图目录名是中文，发布线上要排除） |
| `../ultraman-web/index.html` | 游戏主体，`HERO_MOVES`/战斗编排所在 |

## 4. 验收与协作规矩（沿用 HANDOFF_GLM_R2 的铁律）
1. agent 无直接视觉：自动验收只用像素统计，外观裁决归用户
2. 没过自检/像素门的版本不发线上
3. 截图用 agent-browser，不用 `toDataURL`
4. 每轮结束写 `docs/WORKLOG.md` 新篇（含坑与解法），交接单放 `docs/HANDOFF_*.md`
5. 改 html 前先 `cp` 进 `tools/archive/`
