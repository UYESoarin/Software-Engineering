"""规则层：盘面、射线判定、余次、关卡快照。

本模块不 import pygame，任何显示库都不应出现在这里。
点选结算返回「结果字典」，表现层只负责把已经发生的结果画出来。
"""

DIRS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


class Session:
    """一局对局的规则会话。

    只读 level（rows/cols/moves/arrows 字段），不修改它；
    所有可变状态（箭头列表、余次）都留在 Session 内。
    """

    def __init__(self, level):
        self.level = level
        self.rows = level["rows"]
        self.cols = level["cols"]
        self._initial_arrows = [dict(a) for a in level["arrows"]]
        self._initial_moves = level["moves"]
        self.reset()

    def reset(self):
        """恢复进入本关时的快照（不是上一次点击前）。"""
        self.arrows = [dict(a) for a in self._initial_arrows]
        self.moves_left = self._initial_moves
        self.arrows_left = len(self.arrows)

    def arrow_at(self, row, col):
        """返回该格箭头在 self.arrows 中的下标，无则 None。"""
        for i, a in enumerate(self.arrows):
            if a["row"] == row and a["col"] == col:
                return i
        return None

    def _blocked_by(self, row, col, ignore):
        """(row, col) 上是否有一支「别的」箭，返回其下标或 None。"""
        for i, a in enumerate(self.arrows):
            if i != ignore and a["row"] == row and a["col"] == col:
                return i
        return None

    def _ray(self, row, col):
        """沿该格箭头朝向做格子射线。

        返回 (可飞?, 阻挡下标或 None)；空格返回 None。
        先问格子在不在盘内、再读占用，避免负行/负列绕到网格另一头。
        """
        idx = self.arrow_at(row, col)
        if idx is None:
            return None
        arrow = self.arrows[idx]
        dr, dc = DIRS[arrow["dir"]]
        r, c = row + dr, col + dc
        while 0 <= r < self.rows and 0 <= c < self.cols:
            j = self._blocked_by(r, c, idx)
            if j is not None:
                return False, j
            r += dr
            c += dc
        return True, None

    def can_fly(self, row, col):
        """该格是否可飞出（不改变状态）；提示 / 求解 / 验盘用。"""
        res = self._ray(row, col)
        return res is not None and res[0]

    def try_clear(self, row, col):
        """点选结算。

        空白格返回 None；否则返回
        {"type": "fly"|"blocked", "arrow": {...}}，
        blocked 额外带 "blocker": {...}。
        """
        res = self._ray(row, col)
        if res is None:
            return None
        can, blocker = res
        idx = self.arrow_at(row, col)
        arrow = self.arrows[idx]
        if not can:
            self.moves_left -= 1
            return {"type": "blocked", "arrow": arrow, "blocker": self.arrows[blocker]}
        self.arrows.pop(idx)
        self.arrows_left = len(self.arrows)
        return {"type": "fly", "arrow": arrow}

    @property
    def won(self):
        return self.arrows_left == 0

    @property
    def lost(self):
        return self.moves_left <= 0
