"""关卡分析与自动解算。

只依赖规则数据，不依赖 pygame。
当前版本针对「单格 + 四向直线箭头」规则：删除箭头只会减少阻挡，
不会产生新阻挡，因此「不断选当前可飞箭」即等价于拓扑排序，
无需暴力 DFS 枚举点击顺序。
"""
from collections import deque

from .rules import DIRS


def build_dependency_graph(level):
    """建立 blocker -> blocked 的依赖图。

    返回 (arrows, adj, indeg)：
        adj[i]   = 清除 i 后可继续解锁的节点集合
        indeg[i] = 节点 i 仍有多少个前置 blocker
    """
    arrows = [dict(a) for a in level["arrows"]]
    n = len(arrows)
    pos_to_idx = {(a["row"], a["col"]): i for i, a in enumerate(arrows)}

    adj = [set() for _ in range(n)]
    indeg = [0] * n

    for i, a in enumerate(arrows):
        dr, dc = DIRS[a["dir"]]
        r, c = a["row"] + dr, a["col"] + dc
        while 0 <= r < level["rows"] and 0 <= c < level["cols"]:
            j = pos_to_idx.get((r, c))
            if j is not None and i not in adj[j]:
                # j 挡住 i，因此 j 必须先于 i 被清除
                adj[j].add(i)
                indeg[i] += 1
            r += dr
            c += dc

    return arrows, adj, indeg


def solve(level):
    """返回一条合法解序（箭 id 列表）；死锁返回 None。

    Kahn 拓扑排序：不断取出入度为 0（当前可飞）的箭。
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
    """返回关卡质量指标（依赖深度 / 依赖数 / 初始可选数 / 解序）。"""
    arrows, adj, indeg = build_dependency_graph(level)
    solution = solve(level)
    if solution is None:
        return {
            "solvable": False,
            "depth": None,
            "dependencies": sum(len(x) for x in adj),
            "initial_choices": 0,
        }

    # 拓扑序上的最长路径 = 依赖深度
    position = {rid: i for i, rid in enumerate(solution)}
    depth = [0] * len(arrows)
    for i in sorted(range(len(arrows)), key=lambda x: position[arrows[x]["id"]]):
        for j in adj[i]:
            depth[j] = max(depth[j], depth[i] + 1)

    return {
        "solvable": True,
        "depth": max(depth, default=0),
        "dependencies": sum(len(x) for x in adj),
        "initial_choices": sum(d == 0 for d in indeg),
        "solution": solution,
    }
