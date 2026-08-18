## 2026-08-18 深夜 · R2：身体找回 + 立绘量制头盔（HANDOFF_GLM_R2.md 执行轮）

**任务来源**：`docs/HANDOFF_GLM_R2.md`——上一轮 A1/A2 双否（身体被掏空/A1 涂色人脸/A2 红蛋），本轮只走 S1→S2，十步执行，交包即停。

### 十步打勾
1. ✅ 备份 `tools/archive/rpm_ultraman.html.bak-before-r2`
2. ✅ `docs/acceptance/r2/mesh_list.json`——实证 R1 失败根因：**躯干/裤/脚体积在 Outfit 网格上**（Body 只到 y1.17，Top 补 0.75-1.37、Bottom 补裤、Footwear 补脚）
3. ✅ 可见性重写：保留 Body+三件 Outfit 并上色；只藏发/镜/齿/眼球（禁止一刀切）
4. ✅ 上色扩到 kept 全体（zCenter/SX 用全体重标定，SX 485→423）；透明底回落银/红，无黑顶点
5. ✅ `body_front.png` + G2：**八带全过（盆 23.0% 腿 17.6%，上轮为 0）**，G3 全过（盆红 16.1%）
6. ✅ `head_metrics.md`——classic.png 像素量测：头高 17.4cm/头宽 22.7cm/**单眼宽 7.4cm 双眼几乎贴中线**/眼在头高 40% 处
7. ✅ `tools/gen_helmet_r2.py` → `helmet_r2.glb`（1512 顶点 0 非流形）；**导出后 glTF 前脸银 54% ✓**（新增导出后判据检查脚本段）
8. ✅ `?head=r2` 挂盔 + 藏 Wolf3D_Head
9. ✅ `docs/acceptance/r2/` 八视角 + compare_body/compare 对照板 + report.json
10. ✅ NOTES.md 交包，停（未发线上）

### 门禁（front，阈值未改）
G2 全过 | G3 全过 | G6 过 | G5 ✗0.245%（非人脸：head=none 同值的暖色身体像素检测误报，已在 report.notes 记录）| top/bottom 视角 G2 口径限制

### 本轮新增工程事实
- RPM 可见人体 = Body(四肢+下躯) + Outfit_Top(上胸肩) + Outfit_Bottom(盆腿) + Footwear(脚)——**隐藏任何一件就缺一段**
- glTF 导出后分区判据核查法：按 primitive 分材质数前向面（normal.z>0.3）占比，20 行 python，已用于头盔出厂检查
- 立绘双眼特征：单眼 7.4cm、内缘几乎贴中线、外眼角上挑 ~15°——灯罩眼是初代辨识度核心

### 状态
交包等用户看图（`docs/acceptance/r2/compare.png`）。十步完成即停，未做：page-publish、游戏接入、六英雄换皮（交接单 §7 禁项）。

---
# live3D 工作日志

> 按轮次记录：任务来源、交付物、门禁数字、踩坑与解法。新条目加在最上面。

---

## 2026-08-18 晚 · 头部决策实验（HANDOFF_GLM.md 执行轮）

**任务来源**：`docs/HANDOFF_GLM.md` §3——产出 A1/A2 两个头部样品 + 验收脚本骨架，
交用户盲选；不发布未过门版本、不宣布"头部完成"。

### 交付物

| 交付 | 说明 |
|---|---|
| `tools/gen_helmet_a2.py` + `assets/output/helmet_a2.glb` | A2 头盔生成器（Blender 无头，椭球组合法）：颅球/后脑/扁脸/下颚/下巴/矢状冠脊薄刃/眉骨拼合 + 面级分区（前脸银/侧后红/下颚红）+ 杏仁眼凸起（发光黄）+ 耳板。2598 顶点、0 非流形、包络 x±0.107 / v -0.137..0.121 / d ±0.13 米 |
| `tools/rpm_ultraman.html`（v7） | 以验证过的 v5 归档为底座（v6 全新重写栽在渲染玄学上，弃）：`?head=a1\|a2\|none` 切头、8 视角固定机位 API（`__setcam`）、`__freeze` 停动作回**绑定站姿** + 同步补帧、摆拍时隐藏 HUD/参考图 |
| `tools/acceptance_check.py` | G2/G3/G5/G6 门禁脚本：前景检测=相对画面主导色（WebGL 背景双重色彩管理后渲染为 (63,66,75)，固定阈值失效）；G6 单色占比只在人像掩码内统计（背景占帧不算遮挡物） |
| `docs/acceptance/head-a1/`、`head-a2/` | 盲选包 ×2：front/back/left/right/q34×2/top/bottom（1240×1800）+ compare.png 对照板（立绘vs渲染+眼/肩/膝黄线）+ report.json 门禁数字 + NOTES.md 已知瑕疵 |
| `docs/acceptance/index.html` + 线上 v4 | 盲选导航页，发布于 https://page.sui.pics/a/live3d-dist-06a0685f3514417e/docs/acceptance/index.html |
| 提交 | `27fd17d`（实验主体）、盲选页（v4 同步），均已推 GitHub |

### 门禁数字（front 视图，阈值未调）

| 门 | A1 | A2 | 备注 |
|---|---|---|---|
| G5 人脸清除 | ✅ 0% | ✅ 0% | |
| G6 无遮挡 | ✅ | ✅ | |
| G3 胸盾红>5% | 9.5% ✅ | 9.2% ✅ | |
| G3 腰盆红>10% | ✗ 0% | ✗ 0% | 两包同源身体蒙皮瑕疵 |
| G2 腰盆带≥3% | ✗ 0% | ✗ 0.1% | 同上，下一轮单独修 |

G1/G4/G7 未实现（占位），按交接单允许。

### 本轮踩坑与解法（工程资产）

1. **画布 1280 宽时 vertexColors 材质不渲染**（620 正常）——本机无头浏览器/软渲染的未解玄学。规避：画布固定 620×900，截图后软件放大。v6 全新重写即栽在此，回退 v5 底座才通
2. **Boxing 剪辑 t=0 是深度蹲伏**（腿折进躯干高度带，人像只占 1/3 画幅）——冻结改 `mixer.stopAllAction()` 回绑定姿势（RPM A-pose 站立）
3. **Skin 修改器分支斜接不可控**：首版头盔下巴垂到 -0.167、头顶压扁到 +0.084（分支顶点横截面⊥平均分支方向）——改椭球组合法（缩放可精确控制扁脸/薄刃）
4. **Blender 轴序坑 ×2**：关节表 (x,纵向,深度) 传入前必须换轴成 (x,深度,纵向)；**缩放元组同理**（首版冠脊的 1.30 纵向缩放落到深度轴，立成莫西干鳍）
5. **page.sui.pics/lib 无 CORS 头**：本地开发（跨源）import 会被拦，只能 jsdelivr；同源（线上页面）可用——上线后可切换治 CDN 挂
6. **无头浏览器 RAF 节流**：requestAnimationFrame 可能停摆——`__freeze/__setcam` 内同步 `r.render()`；v5 底座的 `placeCam()` 每帧覆盖摆拍机位，加 frozen 守卫
7. **普通截图只有 633px 视口**：膝盖以下天然裁掉（曾误判"腿没渲染"）——验收截图必须 `--full`
8. **验收前景检测**：WebGL 背景 `Color(.05,.055,.07)` 经输出色彩管理渲染为 (63,66,75)（lum≈68），任何固定亮度阈值都会把背景当前景——改为相对画面主导色距离

### 状态与下一步

- **当前**：等用户盲选 A1/A2（脸部 checklist：盔型/眼/下颚红/无肤色/不挡身）；两版都否→按 ✗ 项各再改一轮（上限一轮）
- 胜者 → 阶段 D 动画精修；随后阶段 E 游戏接入
- 遗留：身体蒙皮腰盆/大腿偏暗（同源瑕疵单独修）；A2 头盔"前脸分区疑反"一行可修；G1/G4/G7 补全；验收脚本未跑 CI 化

---
