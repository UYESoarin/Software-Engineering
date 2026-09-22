"""场景状态机：标题 / 对局 / 结果。

每个画面同一套 handle / update / draw，主循环不关心里面是哪个。
handle / update 返回「新场景或 None」，由主循环接管切换。
"""
import pygame

from . import anim, view
from .rules import DIRS, Session


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
        view.draw_button(screen, self.start_rect, "开始", self.body_font)


class PlayScene:
    """对局画面：棋盘 + 顶栏 + 重开 + 点选结算 + 飞出 / 受阻动画。

    结算发生在规则层（try_clear），动画只表现已经发生的结果；
    动画播放期间锁输入，避免一次按下打出两次结算。
    """

    def __init__(self, app, level_index):
        self.app = app
        self.level_index = level_index
        self.level = app.levels[level_index]
        self.session = Session(self.level)
        self.anim = None  # 当前飞出 / 受阻；None 表示可点
        cell = 64
        bw = self.level["cols"] * cell
        self.view = view.BoardView(origin=((app.w - bw) // 2, 90), cell=cell)
        self.restart_rect = pygame.Rect(0, 0, 120, 40)
        self.restart_rect.center = (app.w // 2, app.h - 40)

    def handle(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.anim is not None:  # 锁输入：一次结算对应一段动画
            return None
        if self.restart_rect.collidepoint(event.pos):
            self.session.reset()   # 重开：恢复进入本关时的快照
            return None
        cell = self.view.pixel_to_cell(event.pos, self.session.rows, self.session.cols)
        if cell is None:
            return None
        result = self.session.try_clear(*cell)  # 纯逻辑结算，无 pygame
        if result is None:  # 点空白
            return None
        a = result["arrow"]
        if result["type"] == "fly":
            cx, cy = self.view.cell_center(a["row"], a["col"])
            self.anim = anim.FlyOut(cx, cy, DIRS[a["dir"]],
                                    int(self.view.cell * 0.30), view.ARROW)
        else:  # blocked
            self.anim = anim.Blocked(a["row"], a["col"])
        return None

    def update(self, dt):
        if self.anim is not None:
            self.anim.advance(dt)
            if self.anim.done:
                self.anim = None
                return self._check_end()  # 动画结束再判胜负，切结果画面
        return None

    def _check_end(self):
        """依据对局状态切结果画面；正常进行中返回 None。"""
        if self.session.won:
            kind = "win" if self.level_index == len(self.app.levels) - 1 else "pass"
            return ResultScene(self.app, kind, self.level_index)
        if self.session.lost:
            return ResultScene(self.app, "fail", self.level_index)
        return None

    def draw(self, screen):
        screen.fill(view.BG)
        self.view.draw_board(screen, self.session, anim=self.anim)
        self.view.draw_hud(screen, self.level, self.session)
        view.draw_button(screen, self.restart_rect, "重开", view.load_font(22))


class ResultScene:
    """结果画面：通过 / 全通 / 失败，带跳转按钮。"""

    def __init__(self, app, kind, level_index):
        self.app = app
        self.kind = kind          # "pass" 通过（有后关） / "win" 全通 / "fail" 失败
        self.level_index = level_index
        self.title_font = view.load_font(40)
        self.body_font = view.load_font(22)
        self.title, self.hint = {
            "pass": ("本关通过", "点击下一关继续"),
            "win": ("全部通关！", "已完成所有关卡"),
            "fail": ("本关失败", "失误次数耗尽，再试一次"),
        }[kind]
        self.buttons = self._make_buttons()

    def _make_buttons(self):
        """按结果类型生成按钮列表 [(rect, 文案, 点击后构造的新场景)]。"""
        if self.kind == "pass":
            specs = [("下一关", lambda: PlayScene(self.app, self.level_index + 1)),
                     ("回标题", lambda: MenuScene(self.app))]
        elif self.kind == "fail":
            specs = [("再战", lambda: PlayScene(self.app, self.level_index)),
                     ("回标题", lambda: MenuScene(self.app))]
        else:  # win
            specs = [("回标题", lambda: MenuScene(self.app))]
        n = len(specs)
        buttons = []
        for i, (text, make) in enumerate(specs):
            rect = pygame.Rect(0, 0, 160, 48)
            rect.center = (self.app.w // 2 - (n - 1) * 90 + i * 180, self.app.h // 2 + 60)
            buttons.append((rect, text, make))
        return buttons

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, _, make in self.buttons:
                if rect.collidepoint(event.pos):
                    return make()
        return None

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(view.BG)
        t = self.title_font.render(self.title, True, view.TEXT)
        screen.blit(t, t.get_rect(center=(self.app.w // 2, self.app.h // 2 - 70)))
        h = self.body_font.render(self.hint, True, view.HUD)
        screen.blit(h, h.get_rect(center=(self.app.w // 2, self.app.h // 2 - 20)))
        for rect, text, _ in self.buttons:
            view.draw_button(screen, rect, text, self.body_font)
