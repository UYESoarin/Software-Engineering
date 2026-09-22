# 一箭又一箭：扩展开发与优化实施汇总

> 用途：本文件用于将当前项目从 **I3 基础功能闭环** 推进到“可交付 + 扩展功能”版本，可直接作为 Cursor / Claude Code 的实施依据。
> 
> 当前原则：**先保证基础规则不回归，再增加扩展；新关卡仍保持“单格 + 四向直线箭头”，暂不引入不同长度箭头或转折路径。**

---

## 0. 当前项目阶段结论

### 0.1 当前阶段

当前工程已经完成基础玩法的 I1 / I2 / I3：

- I1：窗口、标题、棋盘、四向箭、点选。
- I2：射线判定、飞出/受阻、失误次数、动画、动画期间锁输入。
- I3：通关 / 失败 / 全通、下一关 / 再战、重开。
- I4 原规划：回归测试、README、截图与最终交付整理。

当前代码架构为“**状态机 + 规则/表现分离 + 关卡数据外置**”：`rules.py` 不依赖 pygame；`view.py / anim.py / scenes.py` 负责表现；`levels.json` 保存关卡数据。现有资料也明确记录了基础要求 11/11 已落地，并把 GitHub / README / 博客 / PSP 归在 I4 待完成项。

### 0.2 本轮实际核验

本次对上传文件重新拼装项目结构后：

- `test_rules.py`：**全部规则层测试通过**。
- `test_smoke.py`：上传运行环境中未安装 pygame，因此本次容器无法重新执行窗口冒烟；项目过程记录中已经记录过原开发环境的冒烟通过。

这意味着后续重点不是重写核心射线算法，而是：

> **把已有“可玩的原型”升级成“可持续加关、可回退、可评分、可保存、可观察、可打包”的完整小型游戏。**

### 0.3 一个重要架构判断

当前 `Session.try_clear()` 直接修改 `arrows / moves_left`；这是基础版最简单、最稳的实现，但扩展后会出现四个横切问题：

1. 撤销需要保存状态历史。
2. 得分需要读取“失误 + 用时”。
3. 保存需要序列化当前局状态。
4. AI 求解需要在不依赖 pygame 的情况下复制/分析状态。

因此推荐保留现有 API，同时只增加：

```text
game/
├── rules.py       # 原有规则；新增 history / snapshot / undo / restore
├── levels.py      # 原有数据加载
├── solver.py      # 新增：依赖图、自动解算、关卡验盘
├── score.py       # 新增：时间、失误、评分、星级
├── save.py        # 新增：本地 JSON 存档
├── audio.py       # 新增：音效统一入口
├── anim.py        # 原有；升级受阻动画
├── view.py        # 原有；升级主题 + 摄像机
└── scenes.py      # 原有；增加 HUD / 选择 / 保存 / 摄像机输入
```

不建议把所有扩展继续堆进 `scenes.py`。

---

# 1. 九项需求的优先级与实施顺序

## 1.1 建议优先级

| 用户编号 | 功能 | 优先级 | 原因 | 对核心风险 |
|---|---|---|---|---|
| **1** | 新难度关卡 | **P0** | 内容量直接决定游戏“是否像完整游戏”；也是后续评分/求解/保存的实际载体 | 低：继续使用原射线算法 |
| **2** | 撤销一步 | **P0** | 实际游玩中明显降低误点挫败；同时验证状态快照设计 | 中 |
| **8** | 受阻后撞击再返回 | **P0** | 当前动画只有晃动，无法完整表达“前冲→碰撞→回位” | 低 |
| **3** | 得分、计时、评级 | **P1** | 让关卡从“通关即结束”变成可重复挑战 | 低–中 |
| **4** | 保存进度 | **P1** | 让更多关卡真正有持续进度意义 | 中 |
| **6** | 拖动 / 缩放 | **P1** | 新关卡扩大到 7×8、8×9、9×10 后，当前固定 64 px 已不够 | 中 |
| **7** | 电子游戏风 UI | **P1** | 低风险但高感知提升 | 低 |
| **9** | 音效资产 | **P2** | 增强手感，但不应阻塞玩法 | 低 |
| **5** | 打包 exe | **Release** | 必须最后打，确保最终代码、assets、levels、save 路径稳定 | 中 |

### 1.2 实际开发依赖顺序

推荐执行顺序：

```text
E1 关卡 + solver
 ↓
E2 undo
 ↓
E3 blocked-return
 ↓
E4 score/time/rating
 ↓
E5 save/resume
 ↓
E6 camera pan/zoom
 ↓
E7 UI theme
 ↓
E8 audio
 ↓
E9 packaging
 ↓
E10 final regression + README + screenshots + blog
```

其中 **E1 / E2 / E3 是本轮最值得先做的三个功能**。

---

# 2. 新关卡设计：保持当前规则，增加“规模 + 依赖深度 + 分支”

## 2.1 不改算法边界

暂不加入：

- 两格以上长度箭头；
- 一支箭包含多个方向；
- 90° 转折路径；
- 旋转机关；
- 障碍物、传送点、开关等新规则。

仍然只使用：

```text
单格箭头
四方向
直线射线
遇箭阻挡
无挡出界
```

这样现有 `rules._ray()` 可以继续作为唯一核心判定。

## 2.2 新关卡应按“依赖图”设计

对于任意一支箭 `A`：

- 如果 `B` 位于 `A` 射线前方，A 被 B 挡住；
- 必须先删除 B，A 才可能飞出。

因此建立有向图：

```text
B ─────→ A
“B 必须先清除”
```

这里的边代表**依赖关系**。

当依赖图无环时，关卡必然存在通关序列。

### 核心推论

在当前规则下，**没有必要做完整 DFS / BFS 回溯求解**。

原因：删除箭头只会减少障碍，不会产生新障碍。因此：

> 如果当前存在一支可飞箭，删除它不会让其他原本可飞的箭重新变成不可飞。

所以：

- 初始有至少一个可飞箭；
- 不断删除任意当前可飞箭；
- 直到全部清空；

即为一个合法拓扑排序。

这比“枚举所有点击顺序”简单很多，也非常适合本作业展示算法思想。

---

# 3. 推荐新增关卡模型

已经额外生成并验证 4 关，全部保持“直线四向 / 单格箭头”。实际验证结果：L4–L7 的 `solution` 均可完整清空。

| 关卡 | 棋盘 | 箭头 | 失误余次 | 依赖深度 | 初始可飞 | 设计目标 |
|---|---:|---:|---:|---:|---:|---|
| L4 脉冲走廊 | 6×7 | 12 | 4 | 4 | 3 | 从小盘升级到“大盘”，首次出现明显分支 |
| L5 交错方阵 | 7×8 | 16 | 4 | 5 | 4 | 多条独立出口 + 中间链 |
| L6 深空编队 | 8×9 | 20 | 5 | 6 | 7 | 大盘观察、行列交织 |
| L7 终端迷阵 | 9×10 | 26 | 5 | 7 | 8 | 目前版本的高难度基础关 |

### L4–L7 设计指标

```text
难度 ≈ 规模 × 依赖深度 × 交叉密度 × 初始选择压缩程度
```

不要单纯用“箭头数量”代表难度。

例如：

- 20 箭但初始可飞 10 支：偏“观察型”；
- 16 箭但初始可飞 2 支、深度 7：反而更容易产生强制顺序感。

### 关于“可解”与“唯一解”

不建议强行要求唯一解。

更好的做法是：

- `solution` 保存一条参考解，只用于自动化验盘；
- 玩家可以按其他合法拓扑序通关；
- 后续可额外统计“最少失误 / 最短时间”，而不是限制唯一顺序。

---

# 4. 建议升级 `levels.json` 数据结构

当前数据只有：

```json
{"id", "name", "rows", "cols", "moves", "arrows"}
```

建议增加：

```json
{
  "id": "L4",
  "name": "脉冲走廊",
  "rows": 6,
  "cols": 7,
  "moves": 4,
  "par_time": 20,
  "arrows": [],
  "solution": [],
  "design_meta": {
    "depth": 4,
    "dependencies": 11,
    "initial_choices": 3
  }
}
```

字段意义：

| 字段 | 用途 |
|---|---|
| `par_time` | 三星/时间评价的基准时间 |
| `solution` | 自动化测试与 solver 自测，不限制玩家 |
| `design_meta.depth` | 关卡设计分析，不参与运行规则 |
| `design_meta.dependencies` | 关卡质量分析 |
| `design_meta.initial_choices` | 关卡可选分支分析 |

已有 L0–L3 也建议补 `solution` 和 `par_time`，这样以后测试文件不需要再维护一份独立 `REF` 字典。

---

# 5. E1：AI 解算器与自动验盘

建议新增：`game/solver.py`

## 5.1 可直接采用的完整代码

```python
"""关卡分析与自动解算。

只依赖规则数据，不依赖 pygame。
当前版本针对“单格 + 四向直线箭头”规则。
"""

from collections import deque

from .rules import DIRS


def build_dependency_graph(level):
    """建立 blocker -> blocked 的依赖图。

    返回：
        arrows: 原始箭头列表
        adj:    adj[i] = 删除 i 后可以继续解锁的节点集合
        indeg:  节点当前仍有多少个前置 blocker
    """
    arrows = [dict(a) for a in level["arrows"]]
    n = len(arrows)
    pos_to_idx = {
        (a["row"], a["col"]): i
        for i, a in enumerate(arrows)
    }

    adj = [set() for _ in range(n)]
    indeg = [0] * n

    for i, a in enumerate(arrows):
        dr, dc = DIRS[a["dir"]]
        r = a["row"] + dr
        c = a["col"] + dc

        while 0 <= r < level["rows"] and 0 <= c < level["cols"]:
            j = pos_to_idx.get((r, c))
            if j is not None and i not in adj[j]:
                # j 挡住 i，因此 j 必须先于 i 被清除。
                adj[j].add(i)
                indeg[i] += 1
            r += dr
            c += dc

    return arrows, adj, indeg


def solve(level):
    """返回一条合法解序；死锁返回 None。

    当前规则单调：删除箭头不会增加阻挡，因此 Kahn 拓扑排序
    就等价于“不断选择当前可飞箭”。
    """
    arrows, adj, indeg = build_dependency_graph(level)
    q = deque(i for i, d in enumerate(indeg) if d == 0)
    order = []

    while q:
        i = q.popleft()
        order.append(i)
        for j in adj[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                q.append(j)

    if len(order) != len(arrows):
        return None
    return [arrows[i]["id"] for i in order]


def analyze(level):
    """返回用于关卡质量分析的指标。"""
    arrows, adj, indeg = build_dependency_graph(level)
    solution = solve(level)
    if solution is None:
        return {
            "solvable": False,
            "depth": None,
            "dependencies": sum(len(x) for x in adj),
            "initial_choices": 0,
        }

    # Kahn 顺序上的最长路径深度。
    position = {rid: i for i, rid in enumerate(solution)}
    depth = [0] * len(arrows)
    for i in sorted(range(len(arrows)), key=lambda x: position[arrows[x]["id"]]):
        for j in adj[i]:
            depth[j] = max(depth[j], depth[i] + 1)

    return {
        "solvable": True,
        "depth": max(depth, default=0),
        "dependencies": sum(len(x) for x in adj),
        "initial_choices": sum(d == 0 for d in build_dependency_graph(level)[2]),
        "solution": solution,
    }
```

## 5.2 为什么这是比 DFS 更适合当前版本的算法

基础规则是一个**单调状态空间**：

```text
删除箭头
   ↓
障碍只会减少
   ↓
原来能飞的箭头不会重新变成被挡
```

因此可以直接转化为拓扑排序。

这也是非常适合博客/答辩解释的一点：

> “我没有暴力枚举玩家所有点击顺序，而是把‘谁必须先被移除’建模为有向依赖图，并用拓扑排序判断是否存在完整通关序列。”

---

# 6. 自动生成关卡：推荐“构造式生成”，不要完全随机

随机放箭 + 随机方向很容易生成死锁。

正确思路是：

1. 先随机生成一个目标清除顺序；
2. 随机选择 N 个不重复格子；
3. 对每支箭，只允许选择“射线上的其他箭都位于它之后”的方向；
4. 生成后重新跑 `solver.solve()`；
5. 根据 `depth / dependencies / initial_choices` 筛选难度；
6. 保存随机种子，保证可复现。

## 6.1 可直接使用的生成器骨架

```python
"""离线关卡生成器。
运行后生成 JSON；不在正式游戏运行期间使用。
"""

import json
import random

from game.rules import DIRS
from game.solver import analyze


DIR_NAMES = list(DIRS)


def valid_dirs(row, col, order_rank, occupied, rows, cols):
    result = []
    for name in DIR_NAMES:
        dr, dc = DIRS[name]
        r, c = row + dr, col + dc
        ok = True
        while 0 <= r < rows and 0 <= c < cols:
            if (r, c) in occupied:
                other_rank = order_rank[occupied[(r, c)]]
                # 射线上的 blocker 必须比当前箭更晚清除。
                if other_rank <= order_rank[occupied[(row, col)]]:
                    ok = False
                    break
            r += dr
            c += dc
        if ok:
            result.append(name)
    return result


def generate_level(level_id, name, rows, cols, count, moves, seed=1):
    rng = random.Random(seed)

    for _ in range(10000):
        cells = rng.sample(
            [(r, c) for r in range(rows) for c in range(cols)],
            count,
        )
        order = list(range(count))
        rng.shuffle(order)
        rank = {arrow_index: k for k, arrow_index in enumerate(order)}
        occupied = {cells[i]: i for i in range(count)}

        arrows = [None] * count
        failed = False

        for arrow_index in order:
            row, col = cells[arrow_index]
            choices = []
            for name_dir in DIR_NAMES:
                dr, dc = DIRS[name_dir]
                r, c = row + dr, col + dc
                ok = True
                while 0 <= r < rows and 0 <= c < cols:
                    other = occupied.get((r, c))
                    if other is not None and rank[other] <= rank[arrow_index]:
                        ok = False
                        break
                    r += dr
                    c += dc
                if ok:
                    choices.append(name_dir)

            if not choices:
                failed = True
                break

            # 更偏向产生 blocker，使高级关卡不要变成“满盘出口箭”。
            scored = []
            for d in choices:
                dr, dc = DIRS[d]
                r, c = row + dr, col + dc
                blockers = 0
                while 0 <= r < rows and 0 <= c < cols:
                    if (r, c) in occupied:
                        blockers += 1
                    r += dr
                    c += dc
                scored.append((d, blockers))

            weighted = []
            for d, blockers in scored:
                weighted.extend([d] * max(1, 1 + blockers * 2))
            chosen = rng.choice(weighted)
            arrows[arrow_index] = {
                "id": f"{level_id.lower()}_{arrow_index + 1:02d}",
                "row": row,
                "col": col,
                "dir": chosen,
            }

        if failed:
            continue

        level = {
            "id": level_id,
            "name": name,
            "rows": rows,
            "cols": cols,
            "moves": moves,
            "par_time": max(15, int(count * 1.7)),
            "arrows": arrows,
        }
        info = analyze(level)
        if info["solvable"]:
            level["solution"] = info["solution"]
            level["design_meta"] = {
                "depth": info["depth"],
                "dependencies": info["dependencies"],
                "initial_choices": info["initial_choices"],
            }
            return level

    raise RuntimeError("在指定尝试次数内未生成满足条件的关卡")


if __name__ == "__main__":
    levels = [
        generate_level("L4", "脉冲走廊", 6, 7, 12, 4, seed=104),
        generate_level("L5", "交错方阵", 7, 8, 16, 4, seed=105),
        generate_level("L6", "深空编队", 8, 9, 20, 5, seed=106),
        generate_level("L7", "终端迷阵", 9, 10, 26, 5, seed=107),
    ]
    print(json.dumps(levels, ensure_ascii=False, indent=2))
```

> 说明：上述代码用于**离线生成**，不是运行时每次随机生成。提交版本建议把已经验证过的关卡固定写入 `levels.json`，这样程序行为完全可复现。

---

# 7. E2：撤销一步

## 7.1 最合理的规则定义

“撤销一步”应撤销**最近一次有效点击结算**，包括：

- 成功飞出；
- 被阻挡并消耗失误次数。

即：

```text
点击前
  ↓
记录快照
  ↓
规则结算
  ↓
播放表现
```

撤销后：

- 箭头恢复；
- 余次恢复；
- 计分状态恢复；
- **计时不倒退**。

计时不倒退是必要的，否则玩家可以通过“撤销 + 重试”同时获得无限时间重试和时间作弊。

## 7.2 `rules.py` 可直接增加

```python
from copy import deepcopy


class Session:
    def __init__(self, level):
        self.level = level
        self.rows = level["rows"]
        self.cols = level["cols"]
        self._initial_arrows = [dict(a) for a in level["arrows"]]
        self._initial_moves = level["moves"]
        self._history = []
        self._max_history = 20
        self.reset()

    def reset(self):
        """恢复进入本关时快照，同时清空撤销栈。"""
        self.arrows = [dict(a) for a in self._initial_arrows]
        self.moves_left = self._initial_moves
        self.arrows_left = len(self.arrows)
        self._history.clear()

    def _snapshot(self):
        return {
            "arrows": deepcopy(self.arrows),
            "moves_left": self.moves_left,
        }

    def _restore(self, state):
        self.arrows = [dict(a) for a in state["arrows"]]
        self.moves_left = int(state["moves_left"])
        self.arrows_left = len(self.arrows)

    @property
    def can_undo(self):
        return bool(self._history)

    def undo(self):
        """撤销最近一次结算；无历史返回 False。"""
        if not self._history:
            return False
        state = self._history.pop()
        self._restore(state)
        return True

    def try_clear(self, row, col):
        """原有代码基础上，在真正结算前保存一次状态。"""
        res = self._ray(row, col)
        if res is None:
            return None

        before = self._snapshot()

        can, blocker = res
        idx = self.arrow_at(row, col)
        arrow = self.arrows[idx]

        if not can:
            self.moves_left -= 1
            result = {
                "type": "blocked",
                "arrow": arrow,
                "blocker": self.arrows[blocker],
            }
        else:
            self.arrows.pop(idx)
            self.arrows_left = len(self.arrows)
            result = {
                "type": "fly",
                "arrow": arrow,
            }

        self._history.append(before)
        if len(self._history) > self._max_history:
            del self._history[0]

        return result
```

## 7.3 注意

动画播放期间仍然不能撤销，因为当前架构明确规定“一次结算对应一段动画”。

场景层应：

```python
if self.anim is not None:
    return None

if self.undo_rect.collidepoint(event.pos):
    if self.session.undo():
        self.last_feedback = "已撤销"
    return None
```

按钮没有历史时建议降低透明度 / 禁用态，而不是让点击空转。

---

# 8. E3：受阻箭头“前冲 → 碰撞 → 返回原位”

当前 `Blocked` 只有左右晃动；建议保留原规则，但把表现升级。

## 8.1 动画时序

推荐总时长：约 **0.55–0.65 s**。

```text
0.00 ───── 0.18s     前冲
0.18 ───── 0.25s     碰撞停顿 + 闪烁
0.25 ───── 0.58s     缓动回原位
```

并且：

- 前冲方向 = 箭头方向；
- 碰撞点 = blocker 前方安全距离；
- 回位使用 ease-out / ease-in；
- blocker 短暂闪烁；
- 输入保持锁定。

## 8.2 `anim.py` 推荐替换为

```python
import math


class FlyOut:
    """成功飞出：沿方向移动并淡出。"""

    def __init__(self, x, y, delta, s, color):
        self.x = x
        self.y = y
        self.dr, self.dc = delta
        self.s = s
        self.color = color
        self.alpha = 255
        self.t = 0.0

    def advance(self, dt):
        self.t += dt
        speed = 560
        self.x += self.dc * speed * dt
        self.y += self.dr * speed * dt
        self.alpha = max(0, 255 - int(self.t * 430))

    @property
    def done(self):
        return self.t >= 0.50


class BlockedReturn:
    """受阻：前冲到障碍 → 碰撞 → 返回原位。"""

    def __init__(self, start_x, start_y, impact_x, impact_y, delta,
                 arrow_size, duration=0.58):
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.impact_x = impact_x
        self.impact_y = impact_y
        self.dr, self.dc = delta
        self.arrow_size = arrow_size
        self.duration = duration
        self.t = 0.0
        self.flash = 0.0

    @staticmethod
    def _ease_out_cubic(x):
        x = max(0.0, min(1.0, x))
        return 1 - (1 - x) ** 3

    @staticmethod
    def _ease_in_out(x):
        x = max(0.0, min(1.0, x))
        return x * x * (3 - 2 * x)

    def advance(self, dt):
        self.t += dt

        forward_t = 0.18
        impact_t = 0.25

        if self.t <= forward_t:
            p = self._ease_out_cubic(self.t / forward_t)
            self.x = self.start_x + (self.impact_x - self.start_x) * p
            self.y = self.start_y + (self.impact_y - self.start_y) * p
            self.flash = 0.0
            return

        if self.t <= impact_t:
            self.x = self.impact_x
            self.y = self.impact_y
            self.flash = 1.0 - (self.t - forward_t) / (impact_t - forward_t)
            return

        p = self._ease_in_out(
            (self.t - impact_t) / (self.duration - impact_t)
        )
        self.x = self.impact_x + (self.start_x - self.impact_x) * p
        self.y = self.impact_y + (self.start_y - self.impact_y) * p
        self.flash = 0.0

    @property
    def done(self):
        return self.t >= self.duration
```

## 8.3 `scenes.py` 中启动动画

原来：

```python
self.anim = anim.Blocked(a["row"], a["col"])
```

改为：

```python
ax, ay = self.view.cell_center(a["row"], a["col"])
b = result["blocker"]
bx, by = self.view.cell_center(b["row"], b["col"])

dr, dc = DIRS[a["dir"]]

# 留一点安全距离，避免两个箭头绘制区域完全重叠。
safe = self.view.cell * 0.34 * self.view.zoom
impact_x = bx - dc * safe
impact_y = by - dr * safe

self.anim = anim.BlockedReturn(
    ax, ay,
    impact_x, impact_y,
    (dr, dc),
    int(self.view.cell * 0.30 * self.view.zoom),
)
```

## 8.4 `view.py` 绘制

不再通过 `isinstance(Blocked)` 后自己算偏移，而是直接读 `anim.x / anim.y`：

```python
if isinstance(anim, anim_mod.BlockedReturn):
    draw_arrow(
        screen,
        anim.x,
        anim.y,
        DIRS[a["dir"]],
        BLOCKED,
        anim.arrow_size,
    )
```

碰撞闪烁建议额外画一个短促圆环：

```python
if isinstance(anim, anim_mod.BlockedReturn) and anim.flash > 0:
    radius = int(10 + 18 * (1 - anim.flash))
    alpha = int(180 * anim.flash)
    # 用独立 SRCALPHA Surface 绘制扩散圆环。
```

---

# 9. E4：计时、得分、星级

## 9.1 游戏设计建议

评分不要让“速度”压倒“解谜”。建议：

```text
总分 = 70% 准确度 + 30% 时间表现
```

其中：

- 通过关卡前提：全部箭头清空；
- 失误会影响准确度；
- 时间在达到 `par_time` 后才开始额外扣分；
- 不因为超时直接失败；
- 撤销不回退时间。

## 9.2 `game/score.py` 完整实现

```python
"""关卡评分：纯逻辑，不依赖 pygame。"""


def evaluate(level, elapsed, mistakes):
    moves = max(1, int(level["moves"]))
    par_time = max(1.0, float(level.get("par_time", 30)))

    accuracy = max(0.0, 1.0 - mistakes / moves)

    if elapsed <= par_time:
        time_factor = 1.0
    else:
        overtime = elapsed - par_time
        # 允许最多额外 2× par_time 的时间评分区间。
        time_factor = max(0.0, 1.0 - overtime / (par_time * 2.0))

    score = int(round(700 * accuracy + 300 * time_factor))
    score = max(0, min(1000, score))

    if score >= 900:
        stars = 3
    elif score >= 700:
        stars = 2
    else:
        stars = 1

    return {
        "score": score,
        "stars": stars,
        "mistakes": mistakes,
        "time": round(float(elapsed), 2),
        "accuracy": round(accuracy, 3),
        "time_factor": round(time_factor, 3),
    }
```

## 9.3 PlayScene 增加计时

```python
self.elapsed = 0.0
```

在 `update(dt)` 中，无论是否有动画都累计：

```python
self.elapsed += dt
```

不过建议区分“正在对局”和“结果画面”：

```python
if self.anim is not None:
    self.anim.advance(dt)
```

`ResultScene` 创建时计算：

```python
from .score import evaluate

mistakes = self.level["moves"] - self.session.moves_left
stats = evaluate(self.level, self.elapsed, mistakes)
return ResultScene(
    self.app,
    kind,
    self.level_index,
    stats=stats,
)
```

## 9.4 HUD 建议

对局顶部从当前：

```text
关卡 教程 · 余箭 3 · 余次 5
```

升级为：

```text
┌───────────────────────────────────────────────────────────┐
│ L4 脉冲走廊      ◆ 余箭 12      ⚠ 余次 4      ◷ 00:12.4 │
└───────────────────────────────────────────────────────────┘
```

结果画面：

```text
本关通过

★★★

得分       923
用时       18.7 s
失误       0

[ 下一关 ]   [ 重玩 ]   [ 回标题 ]
```

---

# 10. E5：保存进度

## 10.1 保存内容

推荐存储：

```json
{
  "version": 1,
  "current_level": "L6",
  "unlocked_level": "L7",
  "in_progress": {
    "level_id": "L6",
    "arrows": [],
    "moves_left": 4,
    "elapsed": 17.42
  },
  "best": {
    "L0": {"score": 1000, "time": 5.2, "stars": 3}
  }
}
```

不要把存档写入 exe 所在目录。

推荐：

```text
%APPDATA%/YiJianYouYiJian/save.json
```

原因：打包后的程序目录可能不可写，而且 one-file bundle 的资源目录是运行时展开目录。

## 10.2 `game/save.py` 完整代码

```python
"""本地进度存档。只依赖标准库。"""

import json
import os
from pathlib import Path


APP_DIR_NAME = "YiJianYouYiJian"
SAVE_VERSION = 1


def get_save_path():
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home()))
    elif os.name == "posix":
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    else:
        base = Path.home()
    folder = base / APP_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "save.json"


def default_data():
    return {
        "version": SAVE_VERSION,
        "current_level": "L0",
        "unlocked_level": "L0",
        "in_progress": None,
        "best": {},
    }


class ProgressStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else get_save_path()
        self.data = default_data()
        self.load()

    def load(self):
        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if raw.get("version") != SAVE_VERSION:
                self.data = default_data()
            else:
                self.data = raw
        except (OSError, ValueError, TypeError):
            self.data = default_data()
        return self.data

    def save(self):
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        temp.replace(self.path)

    def save_in_progress(self, level_id, arrows, moves_left, elapsed):
        self.data["current_level"] = level_id
        self.data["in_progress"] = {
            "level_id": level_id,
            "arrows": [dict(a) for a in arrows],
            "moves_left": int(moves_left),
            "elapsed": round(float(elapsed), 2),
        }
        self.save()

    def clear_in_progress(self):
        self.data["in_progress"] = None
        self.save()

    def complete_level(self, level_id, next_level_id=None, stats=None):
        self.data["current_level"] = next_level_id or level_id
        if next_level_id:
            self.data["unlocked_level"] = next_level_id

        self.data["in_progress"] = None

        if stats is not None:
            old = self.data["best"].get(level_id)
            if old is None or stats["score"] > old["score"]:
                self.data["best"][level_id] = {
                    "score": stats["score"],
                    "time": stats["time"],
                    "stars": stats["stars"],
                }
        self.save()

    @property
    def has_resume(self):
        return self.data.get("in_progress") is not None
```

## 10.3 保存时机

不要只在退出时保存。建议：

- 每次完成一笔结算后自动保存；
- 通关时保存；
- 失败时保存解锁进度；
- `QUIT` 再补存一次。

菜单增加：

```text
[ 继续游戏 ]
[ 新游戏 ]
```

有 `in_progress` 才显示“继续游戏”。

---

# 11. E6：棋盘拖动与缩放

这是 L4–L7 必须引入的基础设施。

## 11.1 操作定义

推荐：

| 输入 | 行为 |
|---|---|
| 鼠标中键拖拽 | 平移棋盘 |
| 鼠标滚轮 | 以鼠标位置为中心缩放 |
| Home | 重置到适合窗口 |
| 重开按钮 | 不改变视角；只恢复对局状态 |

不建议用左键拖动，因为左键已经承担箭头点击语义。

## 11.2 `BoardView` 核心改造

推荐把当前固定 `origin + cell` 升级成：

```python
class BoardView:
    def __init__(self, screen_w, screen_h, base_cell=64):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.base_cell = base_cell
        self.zoom = 1.0
        self.min_zoom = 0.45
        self.max_zoom = 2.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.dragging = False
        self.drag_last = None

    def viewport_rect(self):
        # 顶部 HUD + 底部操作栏预留。
        return pygame.Rect(0, 76, self.screen_w, self.screen_h - 150)

    def scaled_cell(self):
        return self.base_cell * self.zoom

    def fit(self, rows, cols):
        vp = self.viewport_rect()
        sx = (vp.width - 32) / (cols * self.base_cell)
        sy = (vp.height - 32) / (rows * self.base_cell)
        self.zoom = max(self.min_zoom, min(1.0, sx, sy))
        self.pan_x = 0.0
        self.pan_y = 0.0

    def _base_origin(self, rows, cols):
        cell = self.scaled_cell()
        w = cols * cell
        h = rows * cell
        vp = self.viewport_rect()
        return (
            vp.centerx - w / 2 + self.pan_x,
            vp.centery - h / 2 + self.pan_y,
        )

    def cell_center(self, row, col, rows, cols):
        ox, oy = self._base_origin(rows, cols)
        cell = self.scaled_cell()
        return (
            ox + (col + 0.5) * cell,
            oy + (row + 0.5) * cell,
        )

    def pixel_to_cell(self, pos, rows, cols):
        x, y = pos
        ox, oy = self._base_origin(rows, cols)
        cell = self.scaled_cell()
        col = int((x - ox) // cell)
        row = int((y - oy) // cell)
        if 0 <= row < rows and 0 <= col < cols:
            return row, col
        return None

    def zoom_at(self, mouse_pos, wheel, rows, cols):
        old_zoom = self.zoom
        new_zoom = max(
            self.min_zoom,
            min(self.max_zoom, old_zoom * (1.12 ** wheel)),
        )
        if new_zoom == old_zoom:
            return

        mx, my = mouse_pos
        old_ox, old_oy = self._base_origin(rows, cols)
        world_x = (mx - old_ox) / old_zoom
        world_y = (my - old_oy) / old_zoom

        self.zoom = new_zoom
        # 先以当前平移为基础得到新的中心原点，再修正 pan，
        # 保证鼠标下的世界坐标仍位于鼠标位置。
        vp = self.viewport_rect()
        cell = self.scaled_cell()
        w = cols * cell
        h = rows * cell
        centered_x = vp.centerx - w / 2
        centered_y = vp.centery - h / 2

        self.pan_x = mx - centered_x - world_x * new_zoom
        self.pan_y = my - centered_y - world_y * new_zoom

    def begin_pan(self, pos):
        self.dragging = True
        self.drag_last = pos

    def update_pan(self, pos):
        if not self.dragging or self.drag_last is None:
            return
        x, y = pos
        lx, ly = self.drag_last
        self.pan_x += x - lx
        self.pan_y += y - ly
        self.drag_last = pos

    def end_pan(self):
        self.dragging = False
        self.drag_last = None
```

> 注意：如果采用这版 `BoardView`，`cell_center()` 接口参数会增加 `rows, cols`。为了减少全项目修改，也可以在构造函数中保存当前 rows / cols；但从可维护性角度，显式传入更清楚。

## 11.3 事件层

```python
if event.type == pygame.MOUSEWHEEL:
    if self.view.viewport_rect().collidepoint(pygame.mouse.get_pos()):
        self.view.zoom_at(
            pygame.mouse.get_pos(),
            event.y,
            self.session.rows,
            self.session.cols,
        )
    return None

if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
    self.view.begin_pan(event.pos)
    return None

if event.type == pygame.MOUSEMOTION and self.view.dragging:
    self.view.update_pan(event.pos)
    return None

if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
    self.view.end_pan()
    return None
```

### 可选快捷键

```python
if event.type == pygame.KEYDOWN and event.key == pygame.K_HOME:
    self.view.fit(self.session.rows, self.session.cols)
    return None
```

---

# 12. E7：电子游戏风 UI / 美术风格

## 12.1 推荐风格：Neon Arcade Puzzle

不建议一开始导入大量位图。

当前箭头已经是程序几何绘制；这一点继续保留，优点是：

- 不依赖外部素材；
- 缩放不会糊；
- 箭头方向完全统一；
- 修改颜色和状态效果很快。

### 视觉关键词

```text
深色背景
霓虹网格
圆角 HUD 面板
高亮描边
发光箭头
数字芯片式信息框
悬停反馈
碰撞闪光
成功粒子
轻量扫描线
```

## 12.2 配色建议

示例：

```python
BG       = (10, 14, 24)
PANEL    = (18, 24, 40)
GRID     = (36, 52, 72)
ARROW    = (80, 220, 255)
ARROW2   = (150, 110, 255)
BLOCKED  = (255, 92, 106)
TEXT     = (236, 244, 255)
MUTED    = (145, 161, 184)
SUCCESS  = (80, 240, 172)
```

不需要全部一次性使用，先把层次拉开即可。

## 12.3 箭头视觉升级

当前：

```text
箭身 + 三角头
```

建议：

```text
暗色阴影
   ↓
发光外轮廓
   ↓
主箭头
   ↓
轻微高亮线
```

选中时：

```text
箭头周围圆环 pulse
```

受阻时：

```text
变红
+ 前冲
+ 碰撞圆环
```

成功时：

```text
飞出
+ fade
+ 2~4 个小粒子
```

## 12.4 HUD 布局

推荐改为：

```text
┌──────────────────────────────────────────────────────────┐
│  一箭又一箭    L6 深空编队     ◆20  ⚠5  ◷ 00:16.8   ⚙ │
└──────────────────────────────────────────────────────────┘

                    [ 棋盘区域 ]

┌─────────────────────── 操作区 ──────────────────────────┐
│   [撤销]       [提示]       [重开]       [居中]          │
└──────────────────────────────────────────────────────────┘
```

“提示”虽然不在用户当前九项里，但当前规则层已经存在 `can_fly()`，属于非常便宜的扩展：点击后高亮一支当前可飞箭即可。

---

# 13. E8：音效资产方案

## 13.1 推荐不要先依赖大包音乐

先加入 6 个极短 SFX：

| 文件 | 触发 | 建议时长 |
|---|---|---:|
| `click.wav` | 点击箭 | 0.04–0.08s |
| `fly.wav` | 成功飞出 | 0.15–0.25s |
| `blocked.wav` | 撞击 | 0.10–0.18s |
| `undo.wav` | 撤销 | 0.10–0.18s |
| `clear.wav` | 本关通关 | 0.4–0.8s |
| `fail.wav` | 失败 | 0.3–0.6s |

背景音乐后加。

## 13.2 优先方案：自制 / 程序生成短音效

本项目完全可以用简单波形合成生成 WAV：

```text
click    = 轻短高频 blip
fly      = 上扬 sweep
blocked  = 低频 thump + 短噪声
undo     = 反向短 sweep
clear    = 三音上行
fail     = 两音下行
```

这样：

- 不需要复制商业游戏音效；
- 不需要额外音效库；
- 可以在仓库中完整说明来源为自制；
- 也适合展示 AIGC 参与“声音设计”。

## 13.3 `game/audio.py`

```python
"""音效统一入口；音频加载失败时游戏仍应正常运行。"""

from pathlib import Path

import pygame


class Audio:
    def __init__(self, asset_dir):
        self.enabled = True
        self.sounds = {}
        self.asset_dir = Path(asset_dir)

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            self.enabled = False
            return

        for name in (
            "click", "fly", "blocked", "undo", "clear", "fail"
        ):
            path = self.asset_dir / f"{name}.wav"
            try:
                self.sounds[name] = pygame.mixer.Sound(path)
            except (pygame.error, OSError):
                pass

    def play(self, name, volume=1.0):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        sound.set_volume(max(0.0, min(1.0, volume)))
        sound.play()
```

使用：

```python
self.app.audio.play("fly")
self.app.audio.play("blocked")
self.app.audio.play("undo")
```

长时间背景音乐再考虑 `pygame.mixer.music`；短促事件音效使用 `pygame.mixer.Sound` 更合适。

---

# 14. E9：打包可执行文件

## 14.1 推荐：PyInstaller + `.spec`

不要只靠一次性的：

```text
pyinstaller main.py
```

因为后续有：

- `levels.json`
- `assets/`
- 可能的字体
- 音效
- 图标

应使用 `.spec` 固定资源清单。

## 14.2 推荐项目结构

```text
AIGCGame/
├── main.py
├── levels.json
├── game/
│   ├── __init__.py
│   ├── rules.py
│   ├── levels.py
│   ├── solver.py
│   ├── score.py
│   ├── save.py
│   ├── audio.py
│   ├── anim.py
│   ├── view.py
│   └── scenes.py
├── assets/
│   ├── sfx/
│   │   ├── click.wav
│   │   ├── fly.wav
│   │   ├── blocked.wav
│   │   ├── undo.wav
│   │   ├── clear.wav
│   │   └── fail.wav
│   ├── fonts/
│   │   └── NotoSansSC-Regular.otf   # 仅在确认许可证后加入
│   └── icon.ico
├── build/
├── dist/
├── requirements.txt
├── yi_jian.spec
└── build.bat
```

## 14.3 资源路径不要再写死

当前 `view.py` 的字体路径是：

```python
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
```

开发环境可用，但打包版本不建议依赖系统路径。

新增：

```python
# game/pathing.py

import sys
from pathlib import Path


def resource_path(relative):
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[1]
    return base / relative
```

然后：

```python
FONT_PATH = resource_path("assets/fonts/NotoSansSC-Regular.otf")
```

`levels.py` 也改成：

```python
from .pathing import resource_path

DEFAULT_PATH = resource_path("levels.json")
```

## 14.4 `yi_jian.spec`

```python
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("game")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("levels.json", "."),
        ("assets", "assets"),
    ],
    hiddenimports=hiddenimports,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="YiJianYouYiJian",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
)
```

如果尚未准备字体 / 音效 / icon，先删除对应资源行再构建；资源准备后再恢复。

## 14.5 `requirements.txt`

为了复现你当前已测试环境，可以先锁定：

```text
pygame==2.6.1
pyinstaller==6.22.3
```

PyInstaller 官方当前文档显示 6.22.3，并明确支持 spec 文件管理数据文件；one-file 模式会把打包资源在运行时展开到临时目录，因此**不要把用户存档写到打包资源目录**。

## 14.6 `build.bat`

```bat
@echo off
setlocal

python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean yi_jian.spec

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Build success: dist\YiJianYouYiJian.exe
```

开发期推荐先使用 `onedir` 验证资源；最终提交再使用 `onefile`。

---

# 15. 测试方案：从 T01–T06 升级成自动回归

## 15.1 保留原测试

必须继续保证：

```text
T01 无挡飞出
T02 有挡扣余次
T03 边缘朝外
T04 清空通关
T05 余次耗尽失败
T06 重开恢复
```

## 15.2 新增测试

### T07 撤销成功飞出

```python
def test_undo_fly():
    lv = levels.load_levels()[0]
    s = Session(lv)
    before = [(a["id"], a["row"], a["col"]) for a in s.arrows]
    s.try_clear(1, 2)  # b
    assert s.arrows_left == 2
    assert s.can_undo
    assert s.undo()
    assert s.arrows_left == 3
    assert [(a["id"], a["row"], a["col"]) for a in s.arrows] == before
```

### T08 撤销失误

```python
def test_undo_blocked_restores_move():
    lv = levels.load_levels()[0]
    s = Session(lv)
    assert s.moves_left == 5
    s.try_clear(1, 0)  # a 被 b 挡
    assert s.moves_left == 4
    assert s.undo()
    assert s.moves_left == 5
    assert s.arrows_left == 3
```

### T09 Solver 所有线上关卡可解

```python
from game.solver import solve


def test_solver_all_levels():
    for lv in levels.load_levels():
        solution = solve(lv)
        assert solution is not None, f"{lv['id']} deadlock"
        assert len(solution) == len(lv["arrows"])
```

### T10 `solution` 和运行规则一致

```python
def test_level_reference_solution():
    for lv in levels.load_levels():
        s = Session(lv)
        for rid in lv["solution"]:
            a = next(a for a in s.arrows if a["id"] == rid)
            result = s.try_clear(a["row"], a["col"])
            assert result and result["type"] == "fly"
        assert s.won
```

### T11 存档 round-trip

```python
def test_save_roundtrip(tmp_path):
    path = tmp_path / "save.json"
    store = ProgressStore(path)
    store.save_in_progress(
        "L2",
        [{"id": "a", "row": 1, "col": 1, "dir": "up"}],
        2,
        12.34,
    )
    other = ProgressStore(path)
    data = other.data
    assert data["in_progress"]["level_id"] == "L2"
    assert data["in_progress"]["moves_left"] == 2
```

### T12 Camera 缩放中心稳定

验证鼠标滚轮缩放时，鼠标指向的棋盘区域不跳飞。

### T13 受阻返回动画

验证：

```text
开始位置 == 结束位置
碰撞位置 != 开始位置
动画结束后 done == True
```

### T14 exe 清洁环境运行

最终必须在一台**没有 Python / pygame 开发环境**的 Windows 环境测试：

```text
双击 exe
→ 标题
→ 开始
→ L0
→ L7
→ 退出
```

并检查：

```text
levels.json 能加载
音效可加载
字体正常
存档可写
```

---

# 16. 关卡与扩展的“开发验收标准”

## 16.1 关卡

一关进入 `levels.json` 前必须满足：

```text
[ ] 坐标不重复
[ ] 四向合法
[ ] 未越界
[ ] solver.solve() != None
[ ] 参考 solution 可完整执行
[ ] 实际手玩至少 1 次
[ ] 记录 par_time
[ ] 检查初始可选箭数量
[ ] 检查依赖深度不异常
```

## 16.2 Undo

```text
[ ] 成功飞出可撤销
[ ] 失误扣次可撤销
[ ] 撤销后箭头完全恢复
[ ] 撤销后余次完全恢复
[ ] 时间不倒退
[ ] 动画中不可撤销
[ ] 重开后撤销栈清空
```

## 16.3 Save

```text
[ ] 中途关闭后可继续
[ ] 通关更新解锁关
[ ] 最佳分数不被低分覆盖
[ ] 损坏 save.json 不导致游戏启动失败
[ ] exe 目录不作为用户数据目录
```

---

# 17. 推荐增加“提示”功能

虽然不是本次九项必须功能，但投入非常低。

规则层已有：

```python
Session.can_fly(row, col)
```

因此 `Hint` 不需要任何新算法：

```python
def first_hint(session):
    for a in session.arrows:
        if session.can_fly(a["row"], a["col"]):
            return a["id"]
    return None
```

表现层将它 pulse 高亮 1 秒即可。

建议：**提示不扣失误次数，但可以计入评分中的“提示使用次数”**，例如每次提示扣 50 分。这样既有辅助功能，又保留挑战性。

---

# 18. AI 自动求解的完整产品化方案

最终可以提供两个入口：

### 玩家提示

```text
[提示]
→ 高亮当前任意可飞箭
```

### AI 自动求解

```text
[AI 求解]
→ 显示：“推荐顺序：B → A → C ...”
→ 可选：逐步自动播放
```

建议不要直接让 AI 模型在运行时思考。

本项目规则明确、状态空间可结构化，因此真正的“AI 求解”应由**确定性算法**完成；AIGC 在项目中的作用放在：

- 设计 solver；
- 设计生成器；
- 生成关卡候选；
- 解释求解结果；
- 代码测试 / 调试。

这比“调用大模型告诉玩家下一步”更可靠，也更符合软件工程作业的算法实现价值。

---

# 19. 给 Cursor / Claude Code 的实施总提示（可直接回送）

下面这段可以作为下一轮 Coding Agent 的主任务说明：

```text
项目：一箭又一箭（Python + Pygame 2）

当前基线：
1. I1/I2/I3 已完成；rules.py / levels.py / view.py / anim.py / scenes.py / main.py 已可运行。
2. 规则是：单格箭头、上/下/左/右四向、直线射线；无挡飞出并删除；有挡不删除且扣一次 moves；清空通关；moves<=0 失败。
3. rules.py 不允许 import pygame。
4. levels.json 为关卡数据源，不要把坐标写死到 rules.py。
5. 当前已有 test_rules.py / test_smoke.py，必须保持原测试通过。

本轮目标：做扩展，不重写基础逻辑。

实施顺序：
E1 新关卡 + solver
E2 undo
E3 blocked-return 动画
E4 score/time/rating
E5 save/resume
E6 pan/zoom camera
E7 neon arcade UI
E8 audio
E9 PyInstaller

E1：
- 新增 game/solver.py
- 将“谁必须先被清除”建模为 blocker -> blocked 的依赖图
- 使用 Kahn 拓扑排序求解，不做无必要 DFS
- levels.json 新增 solution / par_time / design_meta
- 将 L4/L5/L6/L7 加入现有 levels.json
- 自动测试全部线上关卡 solve()!=None

E2：
- rules.Session 增加 history stack
- try_clear 在真正结算前保存 snapshot
- undo() 恢复 arrows + moves_left
- undo 不回退 elapsed
- reset() 清空 undo history
- 动画播放期间禁止 undo

E3：
- 用 BlockedReturn 替换旧 Blocked
- 前冲→碰撞停顿→返回原位
- 碰撞点取 blocker 前方安全距离
- 动画由 dt 驱动，不能使用固定帧数
- 动画期间锁输入

E4：
- 新增 game/score.py
- elapsed 在 PlayScene 内累计
- mistakes = initial_moves - moves_left
- 评分 0~1000
- 3 星 >=900，2 星 >=700，否则 1 星
- 不因超时失败，只影响评分

E5：
- 新增 game/save.py
- 使用 APPDATA/YiJianYouYiJian/save.json
- 存 current_level/unlocked_level/in_progress/best
- 每次有效结算后自动保存
- 菜单增加“继续游戏”
- 存档损坏必须安全回退到默认值
- 不把用户存档写到 exe/资源目录

E6：
- BoardView 增加 zoom/pan
- 中键拖动，滚轮缩放，Home 重置
- zoom 以鼠标位置为中心
- 必须支持 9×10 甚至更大的棋盘

E7：
- 视觉升级为 dark + neon arcade
- HUD chips / rounded panels / hover / selected pulse
- 箭头继续程序绘制，避免不必要位图
- 成功增加少量粒子，碰撞增加 flash ring

E8：
- 新增 game/audio.py
- 统一管理 click/fly/blocked/undo/clear/fail
- 音频加载失败不能导致游戏启动失败
- 优先 WAV 短音效；后续再考虑背景音乐

E9：
- 增加 resource_path()，禁止写死资源绝对路径
- 维护 yi_jian.spec
- bundle levels.json + assets/
- 开发先 onedir，最终 onefile
- console=False
- 打包完成后在无 Python/pygame 环境的 Windows 机器验证

代码要求：
- 不要把新功能全部塞进 scenes.py
- 新增功能尽量纯逻辑模块化
- 每个新增功能补自动化测试
- 修改后运行 test_rules.py
- 能运行 pygame 时再运行 test_smoke.py
- 给出修改文件清单、关键设计说明、测试结果
- 不改变原始 L0-L3 的基础规则语义
```

---

# 20. 最终推荐的项目版本号与里程碑

建议不要把这一轮继续叫 I4，因为原 `planning.md` 已将 I4 定义为“可交付稳定化”。可以在过程记录中增加：

```text
I4  基础版本最终交付
E1  扩展：关卡 + Solver
E2  扩展：Undo
E3  扩展：高级碰撞动画
E4  扩展：计时 / 得分 / 星级
E5  扩展：保存进度
E6  扩展：摄像机
E7  扩展：UI
E8  扩展：音效
E9  Release：PyInstaller
E10 Final：回归 + README + 博客 + PSP
```

这样在过程记录里能够清楚体现：

```text
基础功能完成
→ 代码复核
→ 扩展开发
→ 回归测试
→ 打包
→ 最终提交
```

也更容易写进博客的“软件工程过程”部分。

---

# 21. 本轮文件产物

- `levels_extension.json`：L4–L7 四个已验证的新关卡，可直接追加到现有 `levels.json`。
- `extension_development_summary.md`：本文件，包含设计、优先级、核心代码、测试、生成器、Solver、打包与 Coding Agent 总提示。

---

# 22. 参考依据

本文件综合当前项目的：

- `job_description.md`：作业基本要求、AIGC / GitHub / 测试 / 扩展功能 / 打包要求；
- `planning.md`：规则、状态机、数据 / 表现分离、增量架构；
- `levels.md`：当前 L0–L3 难度曲线与关卡约束；
- `process.md`：I1/I2/I3 实际开发时间线、测试与交付状态；
- `rules.py` / `view.py` / `anim.py` / `scenes.py` / `main.py`：当前实际实现。

PyInstaller 部分按其当前官方文档采用 spec 文件 + datas 的方案；Pygame 音频部分采用 `pygame.mixer.Sound` 处理短音效、`pygame.mixer.music` 处理长音乐的分工。
