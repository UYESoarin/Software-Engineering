# 一箭又一箭

> 基于 Python + Pygame 开发的四向箭头点击解谜小游戏。
> 本项目用于软件工程课程第二次个人作业，使用 AIGC / Coding Agent 辅助完成需求分析、程序开发、测试与优化。

## 1. 项目简介

玩家观察棋盘中箭头的方向与阻挡关系，选择合适的顺序点击箭头：

- 前方没有其他箭头 → 箭头沿自身方向飞出棋盘并消失
- 前方存在箭头 → 本次操作失败，消耗一次失误次数，并播放「前冲 → 碰撞 → 回位」反馈
- 清空全部箭头 → 当前关卡通关
- 失误次数归零 → 当前关卡失败，可重新开始

当前版本采用矩形网格、单格箭头、上下左右四个方向和直线射线检测。

## 2. 功能特性

| 类别 | 功能 |
|---|---|
| 基础 | 开始 / 对局 / 结果三画面；四向箭头；点击选箭；射线阻挡判断；飞出 / 受阻动画；失误次数；重开 |
| 关卡 | 教程 + 正式 + 扩展共 **8 关**（L0–L7），难度逐级上升 |
| 扩展 | 撤销一步、计时 / 得分 / 星级、保存进度 + 继续游戏、选关界面、棋盘缩放 / 拖动、自制音效、AI 自动求解（solver） |
| 交付 | 规则层单元测试 + 冒烟测试、PyInstaller 打包配置 |

## 3. 开发环境

```text
Python: 3.11.9
Pygame: 2.6.1
IDE: PyCharm
AIGC / Coding Agent: Cursor、Claude Code、ChatGPT
操作系统: Windows
```

## 4. 安装与运行

```bash
# 安装依赖
pip install pygame

# 运行
python main.py
```

打包（可选）：

```bash
python -m pip install -r requirements.txt
build.bat        # 或：python -m PyInstaller --noconfirm --clean yi_jian.spec
```

## 5. 操作说明

| 输入 | 行为 |
|---|---|
| 左键 · 箭头 | 结算该箭（飞出或受阻扣次） |
| 左键 · 撤销 | 回退最近一次结算（无历史时禁用） |
| 左键 · 重开 | 恢复本关开局快照 |
| 鼠标滚轮 | 以鼠标位置为中心缩放棋盘 |
| 鼠标中键拖拽 | 平移棋盘 |
| Home | 缩放归位到适合窗口 |
| 标题 · 继续游戏 | 恢复上次未完成的关卡 |

## 6. 项目结构

```text
AIGCGame/
├── main.py                # 入口 + 主循环
├── levels.json            # 关卡数据（8 关）
├── game/
│   ├── rules.py           # 规则层：盘面/射线/余次/快照/撤销（不 import pygame）
│   ├── solver.py          # 规则层：依赖图 + 拓扑排序求解
│   ├── score.py           # 规则层：评分 / 星级
│   ├── save.py            # 数据层：本地进度存档
│   ├── levels.py          # 数据层：读 levels.json
│   ├── pathing.py         # 工具：资源路径（兼容打包）
│   ├── audio.py           # 表现层：音效入口
│   ├── view.py            # 表现层：摄像机 + 绘制
│   ├── anim.py            # 表现层：飞出 / 受阻动画
│   └── scenes.py          # 表现层：标题 / 选关 / 对局 / 结果
├── assets/sfx/            # 自制音效
├── tools/gen_sfx.py       # 音效生成脚本
├── test_rules.py          # 规则层单元测试
├── test_smoke.py          # 冒烟测试
├── notes/                 # 策划 / 过程文档
└── README.md
```

## 7. 实现思路

### 7.1 分层

采用「状态机 + 规则 / 表现分离」：规则层（rules/solver/score/save）不 import pygame，表现层（view/anim/scenes）只把规则层结果画出来，关卡坐标只进 levels.json。

### 7.2 路径检测（核心）

```python
DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

def _ray(self, row, col):
    idx = self.arrow_at(row, col)
    if idx is None:
        return None
    arrow = self.arrows[idx]
    dr, dc = DIRS[arrow["dir"]]
    r, c = row + dr, col + dc
    # 关键：先判断格子在不在盘内，再读占用，
    # 否则 Python 负索引会绕到网格另一头，边缘朝外箭会判错
    while 0 <= r < self.rows and 0 <= c < self.cols:
        j = self._blocked_by(r, c, idx)
        if j is not None:
            return False, j      # 先碰到箭 → 阻挡
        r += dr
        c += dc
    return True, None            # 一路空到边界 → 可飞
```

### 7.3 AI 求解（依赖图 + 拓扑排序）

删除箭头只会减少阻挡、不会产生新阻挡，所以「不断选当前可飞箭」即等价于拓扑排序，无需暴力 DFS：

```python
def solve(level):
    arrows, adj, indeg = build_dependency_graph(level)  # j 挡 i → 边 j→i
    q = deque(i for i, d in enumerate(indeg) if d == 0)  # 入度 0 = 当前可飞
    order = []
    while q:
        i = q.popleft()
        order.append(i)
        for j in adj[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                q.append(j)
    return None if len(order) != len(arrows) else [arrows[i]["id"] for i in order]
```

## 8. 关卡

| ID | 名称 | 棋盘 | 箭头 | 余次 | 目标 |
|---|---|---:|---:|---:|---|
| L0 | 教程 | 3×5 | 3 | 5 | 认识飞出与阻挡 |
| L1 | 顺序入门 | 4×4 | 5 | 3 | 先清除挡路箭头 |
| L2 | 交叉 | 5×5 | 7 | 3 | 行列交叉阻挡 |
| L3 | 收束 | 5×6 | 9 | 3 | 较长依赖关系 |
| L4 | 脉冲走廊 | 6×7 | 12 | 4 | 大盘 + 明显分支 |
| L5 | 交错方阵 | 7×8 | 16 | 4 | 多出口 + 中间链 |
| L6 | 深空编队 | 8×9 | 20 | 5 | 大盘观察、行列交织 |
| L7 | 终端迷阵 | 9×10 | 26 | 5 | 高难度基础关 |

## 9. 测试

| 编号 | 内容 | 结果 |
|---|---|---|
| T01 | 无阻挡箭头正常飞出 | ✅ 自动化 |
| T02 | 有阻挡箭头不消失且扣次 | ✅ 自动化 |
| T03 | 边缘朝外箭头正常消失 | ✅ 自动化 |
| T04 | 清空关卡进入通关流程 | ✅ 冒烟 |
| T05 | 失误次数耗尽进入失败流程 | ✅ 冒烟 |
| T06 | 重开恢复本关初始状态 | ✅ 冒烟 |
| T07 | 撤销成功飞出 | ✅ 规则层 |
| T08 | 撤销恢复余次 | ✅ 规则层 |
| T09 | solver 找到通关序 | ✅ 规则层 |
| T10 | solution 与规则一致 | ✅ 规则层 |
| T11 | 存档 round-trip | ✅ 规则层 |

运行测试：`python test_rules.py`、`python test_smoke.py`。

## 10. 项目展示

完整的开始界面、游戏过程、通关 / 失败界面截图与演示见博客：

👉 [利用 AIGC 完成「一箭又一箭」小游戏（博客）](https://www.cnblogs.com/UYESoarin/p/23085977)

## 11. AIGC 协作记录

| 子任务 | 工具 | AI 提供内容 | 效果 | 人工修改 |
|---|---|---|---|---|
| 策划与架构 | Cursor | 玩法拆解、增量、分层 | 可作骨架 | 按策划案重写、关卡外置 |
| 规则 / 关卡 / 扩展分析 | Claude Code / ChatGPT | 射线规则、关卡可解性、扩展优先级与方案 | 可直接实施 | 修正参考序、SysFont 坑 |
| 编码与测试 | Claude Code | rules/solver/score/save/audio/view/scenes 实现 | 测试全过 | 待 ChatGPT 审查 |

## 12. 资源说明

| 资源 | 来源 | 说明 |
|---|---|---|
| 音效 | 自制（tools/gen_sfx.py 程序合成） | 无版权问题 |
| 字体 | Windows 微软雅黑（系统字体） | 开发环境自带 |

本项目为课程作业，未使用原商业游戏的代码、美术、音效或关卡。

## 13. 已知问题

| 问题 | 严重程度 | 处理 |
|---|---|---|
| 音效依赖 pygame.mixer，无音频设备时静默跳过 | 低 | audio.py 已容错 |
| exe 打包尚未在无 Python 环境实测 | 中 | 待验证 |
