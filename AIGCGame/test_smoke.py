"""冒烟测试：无窗口（dummy 驱动）跑通 I2/I3 + P0/P1 关键路径。运行：python test_smoke.py"""
import os
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

from main import App
from game import anim, scenes


def click_cell(play, cell):
    """在格子中心模拟左键点击。"""
    cx, cy = play.view.cell_center(*cell)
    play.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(int(cx), int(cy))))


def click_rect(scene, rect):
    """在矩形中心模拟左键点击，返回 handle 的返回值。"""
    return scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))


def button_rect(scene, text):
    for rect, t, _ in scene.buttons:
        if t == text:
            return rect
    raise KeyError(text)


def arrow_by_id(session, rid):
    return next(x for x in session.arrows if x["id"] == rid)


def main():
    tmp = tempfile.mkdtemp()
    app = App(save_path=os.path.join(tmp, "save.json"))
    pygame.init()
    screen = pygame.display.set_mode((app.w, app.h))
    pygame.display.set_caption("smoke")

    # 标题 → 选关 → 第 1 关
    menu = scenes.MenuScene(app)
    menu.draw(screen)
    sel = click_rect(menu, button_rect(menu, "选关"))
    assert isinstance(sel, scenes.LevelSelectScene)
    assert sel.level_rects[0][2] is True, "第 1 关应解锁"
    play = click_rect(sel, sel.level_rects[0][0])
    assert isinstance(play, scenes.PlayScene) and play.level_index == 0
    play.draw(screen)
    s = play.session  # L0

    # I2 飞出 + 锁输入
    b = arrow_by_id(s, "b")
    click_cell(play, (b["row"], b["col"]))
    assert isinstance(play.anim, anim.FlyOut) and s.arrows_left == 2
    click_cell(play, (arrow_by_id(s, "a")["row"], arrow_by_id(s, "a")["col"]))
    assert s.arrows_left == 2, "动画期间锁输入"
    play.update(0.5)

    # E2 撤销成功飞出
    click_rect(play, play.undo_rect)
    assert s.arrows_left == 3, "撤销应恢复 b"

    # I3 重开恢复快照（撤销栈也清空）
    click_rect(play, play.restart_rect)
    assert s.arrows_left == 3 and s.moves_left == 5 and not s.can_undo

    # E3 受阻 → BlockedReturn 前冲返回动画
    a = arrow_by_id(s, "a")
    click_cell(play, (a["row"], a["col"]))
    assert isinstance(play.anim, anim.BlockedReturn), "受阻应触发 BlockedReturn"
    assert s.moves_left == 4
    play.update(0.3)
    assert play.anim is not None
    play.update(0.4)
    assert play.anim is None

    # E2 撤销失误扣次
    click_rect(play, play.undo_rect)
    assert s.moves_left == 5, "撤销应恢复余次"

    # I3 失败：耗尽余次
    result = None
    for _ in range(5):
        a = arrow_by_id(s, "a")
        click_cell(play, (a["row"], a["col"]))
        result = play.update(0.6)
    assert isinstance(result, scenes.ResultScene) and result.kind == "fail" and result.stats is None

    # I3 清空 L0 → 通过 + 评分
    p = scenes.PlayScene(app, 0)
    result = None
    for rid in ["b", "a", "c"]:
        a = arrow_by_id(p.session, rid)
        click_cell(p, (a["row"], a["col"]))
        result = p.update(0.5)
    assert isinstance(result, scenes.ResultScene) and result.kind == "pass" and result.stats is not None
    # E5 通关解锁下一关 + 记录最佳
    assert app.store.data["unlocked_level"] == "L1"
    assert app.store.data["best"]["L0"]["stars"] == 3

    # 末关（L7）清空 → 全通
    last = scenes.PlayScene(app, len(app.levels) - 1)
    result = None
    for rid in last.level["solution"]:
        a = arrow_by_id(last.session, rid)
        click_cell(last, (a["row"], a["col"]))
        result = last.update(0.5)
    assert isinstance(result, scenes.ResultScene) and result.kind == "win" and result.stats is not None

    pygame.quit()
    print("ok: 冒烟测试通过（I2/I3 + P0/P1：选关 / 撤销 / 受阻返回 / 评分 / 存档 / 全通）")


if __name__ == "__main__":
    main()
