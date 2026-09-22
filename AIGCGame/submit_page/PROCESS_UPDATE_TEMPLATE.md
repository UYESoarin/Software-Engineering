# process.md 后续扩展记录

> 本文件承接基础版本（I1/I2/I3）的过程记录；扩展阶段（E1–E9）追加于此，不覆盖历史。
> E 编号与 GPT 文档《extension_development_summary.md》一致。

---

## 8. 扩展阶段总览

| 阶段 | 时间 | 目标 | 状态 |
|---|---|---|---|
| E1 | 09-22 | 关卡 + Solver | ✅ |
| E2 | 09-22 | 撤销一步 | ✅ |
| E3 | 09-22 | 碰撞返回动画 | ✅ |
| E4 | 09-22 | 得分 / 计时 / 星级 | ✅ |
| E5 | 09-22 | 保存进度 | ✅ |
| E6 | 09-22 | 视口拖动 / 缩放 | ✅ |
| E7 | 09-22 | UI / 美术优化 | ✅ |
| E8 | 09-22 | 音效 | ✅ |
| E9 | 09-22 | exe 打包 | 配置就绪（待实测） |
| I4 | 进行中 | 最终回归 / README / 博客 / 发布 | ⏳ |

---

## 9. 每次扩展开发记录

### E1 关卡 + Solver

**目标**：关卡扩至 8 关（L0–L7），新增自动求解与验盘。

**修改文件**：`levels.json`、`game/solver.py`、`test_rules.py`

**设计**：把「谁必须先被清除」建模为 blocker→blocked 依赖图；单调空间下 Kahn 拓扑排序等价于「不断选可飞箭」，无需 DFS。

**测试**：`test_solver_all_levels`、`test_reference_solution` 通过。

### E2 撤销一步

**目标**：误点后可回退最近一次结算。

**修改文件**：`game/rules.py`、`game/scenes.py`

**设计**：结算前快照入栈（上限 20）；撤销回退盘面 + 余次，计时不回退。

**测试**：`test_undo_fly`、`test_undo_blocked` 通过。

### E3 碰撞返回动画

**目标**：完整表达「前冲 → 碰撞 → 回位」。

**修改文件**：`game/anim.py`、`game/view.py`、`game/scenes.py`

**设计**：前冲 0.18s（ease-out）→ 停顿 0.18–0.25s（碰撞圆环闪烁）→ 回位 0.25–0.58s（ease-in-out）。

**测试**：冒烟 `BlockedReturn` 通过。

### E4 得分 / 计时 / 星级

**目标**：通关后按准确度与用时评分。

**修改文件**：`game/score.py`、`game/scenes.py`

**设计**：总分 = 700×准确度 + 300×时间分；`par_time` 内满分，超时线性衰减；≥900 三星。

**测试**：`test_score` 通过。

### E5 保存进度

**目标**：解锁关、最佳分、进行中快照可持久化。

**修改文件**：`game/save.py`、`game/scenes.py`

**设计**：写入 `%APPDATA%/YiJianYouYiJian/save.json`；损坏回退默认；每次结算后自动保存。

**测试**：`test_save_roundtrip` 通过。

### E6 视口拖动 / 缩放

**目标**：大盘（如 9×10）可完整观察与操作。

**修改文件**：`game/view.py`、`game/scenes.py`

**设计**：`BoardView` 维护 zoom/pan；滚轮以鼠标为中心缩放，中键平移，Home 归中，`fit` 自动适配。

**测试**：冒烟通过（点选坐标随摄像机换算正确）。

### E7 UI / 美术优化

**目标**：霓虹 Arcade 风格，提升观感。

**修改文件**：`game/view.py`

**设计**：深色底 + 霓虹（青箭头 / 红受阻 / 金星级）；HUD 显示关卡 / 余箭 / 余次 / 用时；程序绘制箭头。

**测试**：冒烟通过。

### E8 音效

**目标**：结算 / 撤销 / 胜负音效反馈。

**修改文件**：`game/audio.py`、`assets/sfx/*.wav`、`tools/gen_sfx.py`、`game/scenes.py`

**设计**：程序合成 6 个自制 WAV；`Audio` 统一入口，加载失败静默跳过不阻塞。

**测试**：冒烟通过（dummy 音频驱动）。

### E9 exe 打包

**目标**：无开发环境可运行。

**修改文件**：`game/pathing.py`、`yi_jian.spec`、`requirements.txt`、`build.bat`

**设计**：`resource_path` 兼容 onefile；spec 打包 levels.json + assets；`console=False`。

**测试**：配置就绪，待无 Python 环境实测。

---

## 10. 回归测试

每次修改规则层后运行 `python test_rules.py`，修改表现层后运行 `python test_smoke.py`。

### 回归记录

| 日期 | 修改 | test_rules | test_smoke | 手工试玩 |
|---|---|---|---|---|
| 09-22 | E1–E9 全部落地 | ✅ 11 项 | ✅ | 待本人 |

---

## 11. 版本里程碑

### v0.1 基础版本

I1/I2/I3 完成：窗口、棋盘、四向箭、射线判定、飞出/受阻、余次、关卡闭环、重开。历史记录不修改。

### v0.2 扩展版本

时间：09-22

完成：

- E1 关卡 8 关 + solver
- E2 撤销
- E3 碰撞动画
- E4 评分 / 星级
- E5 存档
- E6 摄像机
- E7 霓虹 UI
- E8 音效
- E9 打包配置

### v1.0 最终提交版本

时间：[待定]

完成：

- 回归测试
- README
- 博客
- exe 实测
- GitHub 发布

---

## 12. 问题追踪

| ID | 问题 | 发现阶段 | 严重程度 | 处理 | 状态 |
|---|---|---|---|---|---|
| BUG-001 | L1/L3 参考解与盘面不符 | E1 | 高 | 独立脚本核验可解性，修正参考序 | 已修复 |
| BUG-002 | pygame SysFont 抛 TypeError | 策划收尾 | 中 | 改用 Font(path) 直取 msyh.ttc | 已修复 |
| BUG-003 | L7 大盘超出窗口 | E1 | 中 | 自适应 cell + 摄像机缩放 | 已修复 |
| BUG-004 | exe 未在无 Python 环境实测 | E9 | 中 | 待实测 | 待验证 |
