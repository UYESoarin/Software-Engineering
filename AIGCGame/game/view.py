"""表现层：像素↔格子换算（含缩放/平移）、棋盘 / 箭头 / HUD / 按钮绘制。

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
    """程序绘制四向箭头：箭身 + 三角头。delta 为 (dr, dc)。"""
    dr, dc = delta
    tip = (cx + dc * s, cy + dr * s)
    bx, by = cx - dc * s * 0.4, cy - dr * s * 0.4
    wx, wy = -dr * s * 0.45, dc * s * 0.45
    pygame.draw.line(surf, color, (cx, cy), tip, 3)
    pygame.draw.polygon(surf, color, [tip, (bx + wx, by + wy), (bx - wx, by - wy)])


def draw_arrow_alpha(screen, cx, cy, delta, color, s, alpha):
    """在透明小面上画箭头并整体设 alpha，用于飞出淡出。"""
    pad = s + 8
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
    """棋盘视口：缩放 / 平移 + 像素↔格子换算 + 绘制。"""

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
        # 顶部 HUD + 底部操作栏预留
        return pygame.Rect(0, 76, self.screen_w, self.screen_h - 150)

    def scaled_cell(self):
        return self.base_cell * self.zoom

    def fit(self, rows, cols):
        """缩放至能放下整盘（不放大超过 1.0），并归中。"""
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
        return (vp.centerx - w / 2 + self.pan_x, vp.centery - h / 2 + self.pan_y)

    def cell_center(self, row, col, rows, cols):
        ox, oy = self._base_origin(rows, cols)
        cell = self.scaled_cell()
        return (ox + (col + 0.5) * cell, oy + (row + 0.5) * cell)

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
        """以鼠标位置为中心缩放。"""
        old_zoom = self.zoom
        new_zoom = max(self.min_zoom, min(self.max_zoom, old_zoom * (1.12 ** wheel)))
        if new_zoom == old_zoom:
            return
        mx, my = mouse_pos
        old_ox, old_oy = self._base_origin(rows, cols)
        world_x = (mx - old_ox) / old_zoom
        world_y = (my - old_oy) / old_zoom
        self.zoom = new_zoom
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

    def draw_board(self, screen, session, anim=None):
        rows, cols = session.rows, session.cols
        ox, oy = self._base_origin(rows, cols)
        cell = self.scaled_cell()
        w = cols * cell
        h = rows * cell
        pygame.draw.rect(screen, BOARD_BG, (ox, oy, w, h))
        # 网格线
        for c in range(cols + 1):
            x = ox + c * cell
            pygame.draw.line(screen, GRID, (x, oy), (x, oy + h))
        for r in range(rows + 1):
            y = oy + r * cell
            pygame.draw.line(screen, GRID, (ox, y), (ox + w, y))
        # 箭头：受阻动画中被挡的箭随 anim.x/y 移动，其余正常
        s = int(cell * 0.30)
        blocked_cell = (anim.row, anim.col) if isinstance(anim, anim_mod.BlockedReturn) else None
        for a in session.arrows:
            cx, cy = self.cell_center(a["row"], a["col"], rows, cols)
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
