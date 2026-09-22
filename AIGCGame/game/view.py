"""表现层：像素↔格子换算、棋盘 / 箭头 / HUD 绘制。

只做「把规则层状态画出来」和「把像素换回格子」，不改规则结果。
"""
import pygame

from .rules import DIRS

# 配色：深底浅箭（见策划案 3. 流程与界面）
BG = (30, 32, 40)
BOARD_BG = (40, 44, 54)
GRID = (58, 62, 72)
ARROW = (232, 234, 240)
ACCENT = (120, 210, 170)   # 选中反馈
BTN = (52, 58, 74)
TEXT = (235, 238, 244)
HUD = (200, 205, 215)

FONT_PATH = "C:/Windows/Fonts/msyh.ttc"

_fonts = {}


def load_font(size):
    """带缓存的字体加载。中文优先直取 msyh.ttc（SysFont 在本机不可靠）。"""
    if size not in _fonts:
        try:
            _fonts[size] = pygame.font.Font(FONT_PATH, size)
        except (OSError, FileNotFoundError):
            _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]


def draw_arrow(surf, cx, cy, delta, color, s=18):
    """程序绘制四向箭头：箭身 + 三角头。delta 为 (dr, dc)。"""
    dr, dc = delta
    tip = (cx + dc * s, cy + dr * s)
    bx, by = cx - dc * s * 0.4, cy - dr * s * 0.4
    wx, wy = -dr * s * 0.45, dc * s * 0.45
    pygame.draw.line(surf, color, (cx, cy), tip, 3)
    pygame.draw.polygon(surf, color, [tip, (bx + wx, by + wy), (bx - wx, by - wy)])


class BoardView:
    """棋盘视口：持有原点与格宽，负责像素↔格子与绘制。"""

    def __init__(self, origin, cell):
        self.ox, self.oy = origin
        self.cell = cell

    def pixel_to_cell(self, pos, rows, cols):
        x, y = pos
        col = (x - self.ox) // self.cell
        row = (y - self.oy) // self.cell
        # 先丢盘外点击，避免负索引进网格
        if 0 <= row < rows and 0 <= col < cols:
            return int(row), int(col)
        return None

    def cell_center(self, row, col):
        return (self.ox + (col + 0.5) * self.cell,
                self.oy + (row + 0.5) * self.cell)

    def draw_board(self, screen, session, selected=None):
        rows, cols = session.rows, session.cols
        w = cols * self.cell
        h = rows * self.cell
        pygame.draw.rect(screen, BOARD_BG, (self.ox, self.oy, w, h))
        # 网格线
        for c in range(cols + 1):
            x = self.ox + c * self.cell
            pygame.draw.line(screen, GRID, (x, self.oy), (x, self.oy + h))
        for r in range(rows + 1):
            y = self.oy + r * self.cell
            pygame.draw.line(screen, GRID, (self.ox, y), (self.ox + w, y))
        # 箭头
        s = int(self.cell * 0.30)
        for a in session.arrows:
            cx, cy = self.cell_center(a["row"], a["col"])
            if selected == (a["row"], a["col"]):
                self._highlight(screen, a["row"], a["col"])
            draw_arrow(screen, cx, cy, DIRS[a["dir"]], ARROW, s)

    def _highlight(self, screen, row, col):
        r = pygame.Rect(self.ox + col * self.cell, self.oy + row * self.cell,
                        self.cell, self.cell)
        pygame.draw.rect(screen, ACCENT, r, 3)

    def draw_hud(self, screen, level, session):
        font = load_font(22)
        text = f"关卡 {level['name']}   ·   余箭 {session.arrows_left}   ·   余次 {session.moves_left}"
        surf = font.render(text, True, TEXT)
        screen.blit(surf, (24, 18))
