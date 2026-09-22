"""冒烟测试：无窗口（dummy 驱动）跑通 I2/I3 关键路径。运行：python test_smoke.py"""
import os

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


def arrow_by_id(session, rid):
    return next(x for x in session.arrows if x["id"] == rid)


def main():
    app = App()
    pygame.init()
    screen = pygame.display.set_mode((app.w, app.h))
    pygame.display.set_caption("smoke")

    # 标题 → 对局
    menu = scenes.MenuScene(app)
    menu.draw(screen)
    play = click_rect(menu, menu.start_rect)
    assert isinstance(play, scenes.PlayScene)
    play.draw(screen)
    s = play.session  # L0：b(1,2)朝上可飞；a(1,0)朝右被 b 挡；c(2,4)朝左可飞

    # I2 飞出 + 锁输入
    b = arrow_by_id(s, "b")
    click_cell(play, (b["row"], b["col"]))
    assert isinstance(play.anim, anim.FlyOut) and s.arrows_left == 2
    a = arrow_by_id(s, "a")
    click_cell(play, (a["row"], a["col"]))  # 动画期间锁输入
    assert s.arrows_left == 2
    play.update(0.5)
    assert play.anim is None

    # I3 重开恢复快照
    click_rect(play, play.restart_rect)
    assert s.arrows_left == 3 and s.moves_left == 5, "重开应恢复开局快照"

    # I2 受阻
    a = arrow_by_id(s, "a")
    click_cell(play, (a["row"], a["col"]))
    assert isinstance(play.anim, anim.Blocked) and s.moves_left == 4
    play.update(0.3)

    # I3 耗尽余次 → 失败画面
    result = None
    for _ in range(4):  # 余次 4→3→2→1→0
        a = arrow_by_id(s, "a")
        click_cell(play, (a["row"], a["col"]))
        result = play.update(0.3)
    assert isinstance(result, scenes.ResultScene) and result.kind == "fail"
    result.draw(screen)

    # 失败「再战」→ 回到本关
    again = click_rect(result, result.buttons[0][0])
    assert isinstance(again, scenes.PlayScene) and again.level_index == 0

    # I3 清空 L0 → 通过画面（非末关）
    p = scenes.PlayScene(app, 0)
    result = None
    for rid in ["b", "a", "c"]:
        a = arrow_by_id(p.session, rid)
        click_cell(p, (a["row"], a["col"]))
        result = p.update(0.5)
    assert isinstance(result, scenes.ResultScene) and result.kind == "pass"
    result.draw(screen)

    # 通过「下一关」→ 第 2 关
    nxt = click_rect(result, result.buttons[0][0])
    assert isinstance(nxt, scenes.PlayScene) and nxt.level_index == 1

    # I3 末关清空 → 全通
    last = scenes.PlayScene(app, 3)  # L3 末关
    result = None
    for rid in ["p0", "p2", "p3", "p4", "p6", "p7", "p5", "p1", "p8"]:
        a = arrow_by_id(last.session, rid)
        click_cell(last, (a["row"], a["col"]))
        result = last.update(0.5)
    assert isinstance(result, scenes.ResultScene) and result.kind == "win"
    result.draw(screen)

    pygame.quit()
    print("ok: 冒烟测试通过（I2 飞出/受阻/锁输入；I3 重开/失败/通过/全通）")


if __name__ == "__main__":
    main()
