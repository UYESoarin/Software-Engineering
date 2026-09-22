"""场景状态机：标题 / 选关 / 对局 / 结果。

每个画面同一套 handle / update / draw，主循环不关心里面是哪个。
handle / update 返回「新场景或 None」，由主循环接管切换。
"""
import pygame

from . import anim, view
from .rules import DIRS, Session
from .score import evaluate


class MenuScene:
    """标题画面：继续游戏（有存档时）/ 新游戏 / 选关。"""

    def __init__(self, app):
        self.app = app
        self.title_font = view.load_font(46)
        self.body_font = view.load_font(20)
        self.buttons = []   # [(rect, 文案, 点击后构造的新场景)]
        specs = []
        if app.store.has_resume:
            specs.append(("继续游戏", self._resume))
        specs.append(("新游戏", lambda: PlayScene(self.app, 0)))
        specs.append(("选关", lambda: LevelSelectScene(self.app)))
        cx = app.w // 2
        for i, (text, make) in enumerate(specs):
            rect = pygame.Rect(0, 0, 200, 48)
            rect.center = (cx, app.h // 2 + 40 + i * 64)
            self.buttons.append((rect, text, make))

    def _resume(self):
        st = self.app.store.data.get("in_progress")
        if not st:
            return PlayScene(self.app, 0)
        idx = next((i for i, l in enumerate(self.app.levels) if l["id"] == st["level_id"]), 0)
        return PlayScene(self.app, idx, resume_state=st)

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
        title = self.title_font.render("一箭又一箭", True, view.TEXT)
        screen.blit(title, title.get_rect(center=(self.app.w // 2, self.app.h // 2 - 150)))
        lines = ["点箭，让它沿箭头方向飞出棋盘", "前方有箭则被挡回，扣一次失误", "清空全部箭头即过关"]
        for i, line in enumerate(lines):
            s = self.body_font.render(line, True, view.HUD)
            screen.blit(s, s.get_rect(center=(self.app.w // 2, self.app.h // 2 - 70 + i * 32)))
        for rect, text, _ in self.buttons:
            view.draw_button(screen, rect, text, self.body_font)


class LevelSelectScene:
    """选关画面：按解锁进度显示可选关卡与最佳星级。"""

    def __init__(self, app):
        self.app = app
        self.title_font = view.load_font(36)
        self.body_font = view.load_font(20)
        self.back_rect = pygame.Rect(0, 0, 120, 40)
        self.back_rect.center = (app.w // 2, app.h - 40)
        ids = [l["id"] for l in app.levels]
        unlocked_idx = app.store.unlocked_index(ids)
        self.level_rects = []   # [(rect, level_index, unlocked)]
        cols, cw, ch, gap = 4, 190, 64, 18
        start_x = (app.w - (cols * cw + (cols - 1) * gap)) // 2
        start_y = 90
        for i in range(len(app.levels)):
            rect = pygame.Rect(start_x + (i % cols) * (cw + gap),
                               start_y + (i // cols) * (ch + gap), cw, ch)
            self.level_rects.append((rect, i, i <= unlocked_idx))

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_rect.collidepoint(event.pos):
                return MenuScene(self.app)
            for rect, idx, unlocked in self.level_rects:
                if unlocked and rect.collidepoint(event.pos):
                    return PlayScene(self.app, idx)
        return None

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(view.BG)
        t = self.title_font.render("选择关卡", True, view.TEXT)
        screen.blit(t, t.get_rect(center=(self.app.w // 2, 40)))
        for rect, idx, unlocked in self.level_rects:
            lv = self.app.levels[idx]
            if unlocked:
                text = f"{lv['id']} {lv['name']}"
                best = self.app.store.data["best"].get(lv["id"])
                if best:
                    text += "  " + "★" * best["stars"]
                view.draw_button(screen, rect, text, self.body_font)
            else:
                view.draw_button(screen, rect, "未解锁", self.body_font, disabled=True)
        view.draw_button(screen, self.back_rect, "回标题", self.body_font)


class PlayScene:
    """对局画面：棋盘（可缩放/平移）+ 顶栏 + 撤销/重开 + 结算 + 动画 + 计时 + 存档。

    结算发生在规则层（try_clear），动画只表现已经发生的结果；
    动画播放期间锁输入，避免一次按下打出两次结算。
    """

    def __init__(self, app, level_index, resume_state=None):
        self.app = app
        self.level_index = level_index
        self.level = app.levels[level_index]
        self.session = Session(self.level)
        self.anim = None        # 当前飞出 / 受阻；None 表示可点
        self.elapsed = 0.0      # 本关累计用时（秒）；撤销不回退
        if resume_state and resume_state.get("level_id") == self.level["id"]:
            self.session.load_state(resume_state["arrows"], resume_state["moves_left"])
            self.elapsed = float(resume_state.get("elapsed", 0.0))
        # 摄像机：自动适配整盘（大盘缩小），支持滚轮缩放 + 中键平移
        self.view = view.BoardView(app.w, app.h)
        self.view.fit(self.level["rows"], self.level["cols"])
        self.undo_rect = pygame.Rect(0, 0, 100, 40)
        self.undo_rect.center = (app.w // 2 - 80, app.h - 40)
        self.restart_rect = pygame.Rect(0, 0, 100, 40)
        self.restart_rect.center = (app.w // 2 + 80, app.h - 40)

    def handle(self, event):
        # 摄像机输入（缩放 / 平移 / 归中）
        if event.type == pygame.MOUSEWHEEL:
            if self.view.viewport_rect().collidepoint(pygame.mouse.get_pos()):
                self.view.zoom_at(pygame.mouse.get_pos(), event.y,
                                  self.session.rows, self.session.cols)
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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_HOME:
            self.view.fit(self.session.rows, self.session.cols)
            return None
        # 左键点选
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.anim is not None:  # 锁输入：一次结算对应一段动画
            return None
        if self.restart_rect.collidepoint(event.pos):
            self.session.reset()   # 重开：恢复进入本关时的快照
            self._save_progress()
            return None
        if self.undo_rect.collidepoint(event.pos):
            if self.session.undo():
                self.app.audio.play("undo")
            self._save_progress()
            return None
        cell = self.view.pixel_to_cell(event.pos, self.session.rows, self.session.cols)
        if cell is None:
            return None
        if self.session.arrow_at(*cell) is not None:
            self.app.audio.play("click")
        result = self.session.try_clear(*cell)  # 纯逻辑结算，无 pygame
        if result is None:  # 点空白
            return None
        self._save_progress()
        a = result["arrow"]
        if result["type"] == "fly":
            self.app.audio.play("fly")
            cx, cy = self.view.cell_center(a["row"], a["col"], self.session.rows, self.session.cols)
            self.anim = anim.FlyOut(cx, cy, DIRS[a["dir"]],
                                    int(self.view.scaled_cell() * 0.30), view.ARROW)
        else:  # blocked：前冲 → 碰撞 → 回位
            self.app.audio.play("blocked")
            ax, ay = self.view.cell_center(a["row"], a["col"], self.session.rows, self.session.cols)
            b = result["blocker"]
            bx, by = self.view.cell_center(b["row"], b["col"], self.session.rows, self.session.cols)
            dr, dc = DIRS[a["dir"]]
            safe = self.view.scaled_cell() * 0.34
            impact_x = bx - dc * safe
            impact_y = by - dr * safe
            self.anim = anim.BlockedReturn(
                a["row"], a["col"], ax, ay, impact_x, impact_y,
                (dr, dc), int(self.view.scaled_cell() * 0.30))
        return None

    def _save_progress(self):
        self.app.store.save_in_progress(
            self.level["id"], self.session.arrows,
            self.session.moves_left, self.elapsed)

    def update(self, dt):
        self.elapsed += dt      # 计时不因动画 / 撤销倒退
        if self.anim is not None:
            self.anim.advance(dt)
            if self.anim.done:
                self.anim = None
                return self._check_end()  # 动画结束再判胜负，切结果画面
        return None

    def _check_end(self):
        """依据对局状态切结果画面；正常进行中返回 None。"""
        if self.session.won:
            self.app.audio.play("clear")
            kind = "win" if self.level_index == len(self.app.levels) - 1 else "pass"
            mistakes = self.level["moves"] - self.session.moves_left
            stats = evaluate(self.level, self.elapsed, mistakes)
            next_id = None if kind == "win" else self.app.levels[self.level_index + 1]["id"]
            self.app.store.complete_level(self.level["id"], next_id, stats)
            return ResultScene(self.app, kind, self.level_index, stats=stats)
        if self.session.lost:
            self.app.audio.play("fail")
            self.app.store.clear_in_progress()
            return ResultScene(self.app, "fail", self.level_index)
        return None

    def draw(self, screen):
        screen.fill(view.BG)
        self.view.draw_board(screen, self.session, anim=self.anim)
        self.view.draw_hud(screen, self.level, self.session, elapsed=self.elapsed)
        font = view.load_font(22)
        view.draw_button(screen, self.undo_rect, "撤销", font, disabled=not self.session.can_undo)
        view.draw_button(screen, self.restart_rect, "重开", font)


class ResultScene:
    """结果画面：通过 / 全通 / 失败，带跳转按钮；通过时显示评分与星级。"""

    def __init__(self, app, kind, level_index, stats=None):
        self.app = app
        self.kind = kind          # "pass" 通过（有后关） / "win" 全通 / "fail" 失败
        self.level_index = level_index
        self.stats = stats        # 通过/全通时有评分；失败为 None
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
        screen.blit(t, t.get_rect(center=(self.app.w // 2, self.app.h // 2 - 100)))
        if self.stats is not None:
            stars = "★" * self.stats["stars"] + "☆" * (3 - self.stats["stars"])
            s = self.title_font.render(stars, True, view.STAR)
            screen.blit(s, s.get_rect(center=(self.app.w // 2, self.app.h // 2 - 50)))
            info = (f"得分 {self.stats['score']}    用时 {self.stats['time']}s"
                    f"    失误 {self.stats['mistakes']}")
            h = self.body_font.render(info, True, view.HUD)
            screen.blit(h, h.get_rect(center=(self.app.w // 2, self.app.h // 2 - 5)))
        else:
            h = self.body_font.render(self.hint, True, view.HUD)
            screen.blit(h, h.get_rect(center=(self.app.w // 2, self.app.h // 2 - 30)))
        for rect, text, _ in self.buttons:
            view.draw_button(screen, rect, text, self.body_font)
