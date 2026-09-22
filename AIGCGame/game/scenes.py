"""场景状态机：标题 / 对局（结果画面在 I3 接入）。

每个画面同一套 handle / update / draw，主循环不关心里面是哪个。
"""
import pygame

from . import view
from .rules import Session


class MenuScene:
    """标题画面：名字、三行规则、开始。"""

    def __init__(self, app):
        self.app = app
        self.title_font = view.load_font(46)
        self.body_font = view.load_font(20)
        self.start_rect = pygame.Rect(0, 0, 160, 48)
        self.start_rect.center = (app.w // 2, app.h // 2 + 130)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.start_rect.collidepoint(event.pos):
                return PlayScene(self.app, 0)
        return None

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(view.BG)
        title = self.title_font.render("一箭又一箭", True, view.TEXT)
        screen.blit(title, title.get_rect(center=(self.app.w // 2, self.app.h // 2 - 70)))
        lines = [
            "点箭，让它沿箭头方向飞出棋盘",
            "前方有箭则被挡回，扣一次失误",
            "清空全部箭头即过关",
        ]
        for i, line in enumerate(lines):
            s = self.body_font.render(line, True, view.HUD)
            screen.blit(s, s.get_rect(center=(self.app.w // 2, self.app.h // 2 + 10 + i * 28)))
        pygame.draw.rect(screen, view.BTN, self.start_rect, border_radius=8)
        t = self.body_font.render("开始", True, view.TEXT)
        screen.blit(t, t.get_rect(center=self.start_rect.center))


class PlayScene:
    """对局画面：棋盘 + 顶栏 + 点选反馈（结算在 I2 接入）。"""

    def __init__(self, app, level_index):
        self.app = app
        self.level_index = level_index
        self.level = app.levels[level_index]
        self.session = Session(self.level)
        self.selected = None  # (row, col) 或 None
        cell = 64
        bw = self.level["cols"] * cell
        self.view = view.BoardView(origin=((app.w - bw) // 2, 90), cell=cell)

    def handle(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        cell = self.view.pixel_to_cell(event.pos, self.session.rows, self.session.cols)
        # I1 只做选中反馈；点到箭才高亮，点空白清空选中
        self.selected = cell if cell is not None and self.session.arrow_at(*cell) is not None else None
        return None

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(view.BG)
        self.view.draw_board(screen, self.session, selected=self.selected)
        self.view.draw_hud(screen, self.level, self.session)
