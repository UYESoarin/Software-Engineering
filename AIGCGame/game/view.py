"""表现层：像素↔格子换算、棋盘 / 箭头 / HUD / 按钮绘制。

只做「把规则层状态画出来」和「把像素换回格子」，不改规则结果。
"""
import pygame

from . import anim as anim_mod
from .rules import DIRS

# 配色：深色底 + 霓虹（见 GPT E7 Neon Arcade Puzzle）
BG = (10, 14, 24)
BOARD_BG = (18, 24, 40)
GRID = (36, 52, 72)
ARROW = (80, 220, 255)
BLOCKED = (255, 92, 106)    # 受阻变色
BTN = (24, 34, 56)
BTN_DISABLED = (16, 22, 36)
TEXT = (236, 244, 255)
TEXT_DISABLED = (90, 105, 130)
HUD = (145, 161, 184)
STAR = (240, 200, 80)
SUCCESS = (80, 240, 172)

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


def draw_flash_ring(screen, cx, cy, radius, alpha):
    """碰撞闪光：扩散圆环。"""
    size = radius * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, BLOCKED, (size // 2, size // 2), radius, 2)
    surf.set_alpha(alpha)
    screen.blit(surf, (int(cx - size // 2), int(cy - size // 2)))


def draw_button(screen, rect, text, font, disabled=False):
    """通用按钮：填色 + 居中文字；disabled 呈现禁用态。"""
    color = BTN_DISABLED if disabled else BTN
    tcolor = TEXT_DISABLED if disabled else TEXT
    pygame.draw.rect(screen, color, rect, border_radius=8)
    t = font.render(text, True, tcolor)
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
        # 箭头：受阻动画中被挡的箭随 anim.x/y 移动，其余正常
        s = int(self.cell * 0.30)
        blocked_cell = None
        if isinstance(anim, anim_mod.BlockedReturn):
            blocked_cell = (anim.row, anim.col)
        for a in session.arrows:
            cx, cy = self.cell_center(a["row"], a["col"])
            if blocked_cell == (a["row"], a["col"]):
                draw_arrow(screen, anim.x, anim.y, DIRS[a["dir"]], BLOCKED, anim.arrow_size)
            else:
                draw_arrow(screen, cx, cy, DIRS[a["dir"]], ARROW, s)
        # 飞出动画：该箭已被规则层移除，单独画滑出中的那支
        if isinstance(anim, anim_mod.FlyOut):
            draw_arrow_alpha(screen, anim.x, anim.y, (anim.dr, anim.dc),
                             anim.color, anim.s, anim.alpha)
        # 碰撞闪光圆环
        if isinstance(anim, anim_mod.BlockedReturn) and anim.flash > 0:
            radius = int(10 + 18 * (1 - anim.flash))
            draw_flash_ring(screen, anim.impact_x, anim.impact_y, radius, int(180 * anim.flash))

    def draw_hud(self, screen, level, session, elapsed=None):
        font = load_font(22)
        text = f"{level['name']}    余箭 {session.arrows_left}    余次 {session.moves_left}"
        if elapsed is not None:
            text += f"    用时 {elapsed:.1f}s"
        surf = font.render(text, True, TEXT)
        screen.blit(surf, (24, 18))
