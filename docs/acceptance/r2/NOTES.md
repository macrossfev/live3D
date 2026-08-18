# R2 轮交付说明（按 HANDOFF_GLM_R2.md 十步执行）

## 改了哪些文件
| 文件 | 变更 |
|---|---|
| `tools/rpm_ultraman.html` | ①可见性规则重写：保留 Body+Outfit_Top/Bottom/Footwear 并全部上色，只藏发/镜/齿/眼球/(r2 时)头 ②上色管线从 body-only 扩到 kept 全体（含 zCenter 重标定用全体顶点）③新增 `?head=r2` 分支挂 helmet_r2.glb ④SX 重标定 485→423（骨盆带用全体衣服宽度） |
| `tools/gen_helmet_r2.py` | 新建（脚手架改自 gen_helmet_a2.py），尺寸全部来自 `head_metrics.md` 像素量测 |
| `assets/output/helmet_r2.glb` | 新头盔（1512 顶点，0 非流形，红面 37%）；**导出后 glTF 坐标前脸银占比 54% ✓≥50%** |
| `tools/gen_helmet_a2.glb` 等旧件 | 未动（反面教材保留） |

## 网格保留名单（mesh_list.json）
- 保留并上色：`Wolf3D_Body` + `Wolf3D_Outfit_Top`(y0.75-1.37 上胸肩) + `Wolf3D_Outfit_Bottom`(y0.22-0.89 裤/盆/腿) + `Wolf3D_Outfit_Footwear`(脚)
- 隐藏：Hair / Glasses / Teeth / EyeLeft / EyeRight；`Wolf3D_Head` 仅在 r2 模式藏

## 怎么跑
```
python3 -m http.server 8099
# http://localhost:8099/tools/rpm_ultraman.html?head=r2   （空格冻结, 1-8 视角）
# S1 出门照: docs/acceptance/r2/body_front.png (?head=none 拍摄, 头未藏)
```

## 门禁数字（report.json，阈值未改）
- **G2 八带全过**：头 7.8% 肩 19.2% 胸 33.4% 腰 29.7% **盆 23.0%** **腿 17.6%** 小腿 18.0% 脚 4.2%（上一轮盆/腿=0）
- **G3 全过**：肩红 7.0% 胸盾 13.6% **盆红 16.1%** 小腿红 0.03%
- G6 过（人像内单色 9.9%）
- G5 ✗ 0.245%：**非人脸**——head=none（人头可见）与 r2（人头已藏）同值，来源是身体暖色投影像素的检测误报；q34 视角同因
- top/bottom 视角 G2 ✗：极端俯仰角下高度带与画面带错位，属口径限制非缺件

## 已知瑕疵（事实，不辩解）
1. 头盔挂点用头网格质心，眼高未在页内二次校准（生成器已按 head_metrics 的 40% 头高放置）
2. 冠脊为 1.15:1 薄刃，凸出颅顶约 1.5cm，未做立绘那种更宽的鳍——量测无法从正视图定鳍宽
3. 下颚红区边界是水平线（z<-0.045 判据），非立绘曲线
4. 耳板为圆柱薄片，无凹坑
5. 脖颈与头盔下缘的接缝在侧视可能可见
6. 手臂仍是骨权重程序配色（A-pose 不能投影），边界直线
7. compare.png 中 A-pose 垂臂与立绘 T-pose 平举天然对不上肩线以外区域（交接单已允许）

## 验收
对照 `compare.png`（左立绘右 R2 全身，黄线=眼/肩/膝）按 §6 checklist 打勾。**制作方不打勾，交包即停。**
