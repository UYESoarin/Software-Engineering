"""表现层：像素↔格子换算、棋盘 / 箭头 / HUD / 按钮绘制。

只做「把规则层状态画出来」和「把像素换回格子」，不改规则结果。
"""
import pygame

from . import anim as anim_mod
from .rules import DIRS

# 配色：深底浅箭（见策划案 3. 流程与界面）
BG = (30, 32, 40)
BOARD_BG = (40, 44, 54)
GRID = (58, 62, 72)
ARROW = (232, 234, 240)
BLOCKED = (220, 90, 90)    # 受阻变色
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
    """程序绘制四向箭头：箭身 + 三角头。delta 为 (dr, dc)。

    tip 朝飞行方向；底边两翼垂直于朝向，构成三角箭头。
    """
    dr, dc = delta
    tip = (cx + dc * s, cy + dr * s)          # 箭头尖
    bx, by = cx - dc * s * 0.4, cy - dr * s * 0.4   # 三角底边中点
    wx, wy = -dr * s * 0.45, dc * s * 0.45          # 底边半宽（垂直朝向）
    pygame.draw.line(surf, color, (cx, cy), tip, 3)  # 箭身
    pygame.draw.polygon(surf, color, [tip, (bx + wx, by + wy), (bx - wx, by - wy)])


def draw_arrow_alpha(screen, cx, cy, delta, color, s, alpha):
    """在透明小面上画箭头并整体设 alpha，用于飞出淡出。"""
    pad = s + 8  # 留出箭头最大延伸 + 线宽
    surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    draw_arrow(surf, pad, pad, delta, color, s)
    surf.set_alpha(alpha)
    screen.blit(surf, (int(cx - pad), int(cy - pad)))


def draw_button(screen, rect, text, font):
    """通用按钮：填色 + 居中文字。"""
    pygame.draw.rect(screen, BTN, rect, border_radius=8)
    t = font.render(text, True, TEXT)
    screen.blit(t, t.get_rect(center=rect.center))


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

    def draw_board(self, screen, session, anim=None):
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
        # 箭头：受阻的那支变红晃动，其余正常
        s = int(self.cell * 0.30)
        blocked_cell = (anim.row, anim.col) if isinstance(anim, anim_mod.Blocked) else None
        for a in session.arrows:
            cx, cy = self.cell_center(a["row"], a["col"])
            if blocked_cell == (a["row"], a["col"]):
                draw_arrow(screen, cx + anim.offset_x(), cy, DIRS[a["dir"]], BLOCKED, s)
            else:
                draw_arrow(screen, cx, cy, DIRS[a["dir"]], ARROW, s)
        # 飞出动画：该箭已被规则层移除，这里单独画滑出中的那支
        if isinstance(anim, anim_mod.FlyOut):
            draw_arrow_alpha(screen, anim.x, anim.y, (anim.dr, anim.dc),
                             anim.color, anim.s, anim.alpha)

    def draw_hud(self, screen, level, session):
        font = load_font(22)
        text = f"关卡 {level['name']}   ·   余箭 {session.arrows_left}   ·   余次 {session.moves_left}"
        surf = font.render(text, True, TEXT)
        screen.blit(surf, (24, 18))
