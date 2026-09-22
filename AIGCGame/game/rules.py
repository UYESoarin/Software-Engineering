"""规则层：盘面、射线判定、余次、关卡快照、撤销历史。

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
    所有可变状态（箭头列表、余次、撤销历史）都留在 Session 内。
    """

    def __init__(self, level):
        self.level = level
        self.rows = level["rows"]
        self.cols = level["cols"]
        self._initial_arrows = [dict(a) for a in level["arrows"]]
        self._initial_moves = level["moves"]
        self._history = []        # 撤销栈：每笔结算前的快照
        self._max_history = 20
        self.reset()

    def reset(self):
        """恢复进入本关时的快照（不是上一次点击前），并清空撤销栈。"""
        self.arrows = [dict(a) for a in self._initial_arrows]
        self.moves_left = self._initial_moves
        self.arrows_left = len(self.arrows)
        self._history.clear()

    def load_state(self, arrows, moves_left):
        """从存档恢复盘面与余次（撤销栈清空）。"""
        self.arrows = [dict(a) for a in arrows]
        self.moves_left = int(moves_left)
        self.arrows_left = len(self.arrows)
        self._history.clear()

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

    # ---- 撤销 ----
    def _snapshot(self):
        return {"arrows": [dict(a) for a in self.arrows],
                "moves_left": self.moves_left}

    def _restore(self, state):
        self.arrows = [dict(a) for a in state["arrows"]]
        self.moves_left = int(state["moves_left"])
        self.arrows_left = len(self.arrows)

    @property
    def can_undo(self):
        return bool(self._history)

    def undo(self):
        """撤销最近一次结算（含飞出与失误扣次）；无历史返回 False。"""
        if not self._history:
            return False
        self._restore(self._history.pop())
        return True

    def try_clear(self, row, col):
        """点选结算。

        空白格返回 None；否则返回
        {"type": "fly"|"blocked", "arrow": {...}}，
        blocked 额外带 "blocker": {...}。
        真正结算前保存快照，供撤销。
        """
        res = self._ray(row, col)
        if res is None:
            return None
        before = self._snapshot()
        can, blocker = res
        idx = self.arrow_at(row, col)
        arrow = self.arrows[idx]
        if not can:
            self.moves_left -= 1
            result = {"type": "blocked", "arrow": arrow, "blocker": self.arrows[blocker]}
        else:
            self.arrows.pop(idx)
            self.arrows_left = len(self.arrows)
            result = {"type": "fly", "arrow": arrow}
        self._history.append(before)
        if len(self._history) > self._max_history:
            del self._history[0]
        return result

    @property
    def won(self):
        return self.arrows_left == 0

    @property
    def lost(self):
        return self.moves_left <= 0
