"""冒烟测试：无窗口（dummy 驱动）跑通主循环关键路径。运行：python test_smoke.py"""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

from main import App
from game import scenes


def main():
    app = App()
    pygame.init()
    screen = pygame.display.set_mode((app.w, app.h))
    pygame.display.set_caption("smoke")

    # 标题画面可绘制
    menu = scenes.MenuScene(app)
    menu.draw(screen)
    pygame.display.flip()

    # 点「开始」→ 进入对局
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=menu.start_rect.center)
    play = menu.handle(ev)
    assert isinstance(play, scenes.PlayScene), "标题应进入对局"
    assert play.level["id"] == app.levels[0]["id"], "默认进入第一关"
    play.draw(screen)
    pygame.display.flip()

    # 像素 ↔ 格子
    s = play.session
    assert s.arrows_left == len(s.arrows)
    assert play.view.pixel_to_cell((play.view.ox + 32, play.view.oy + 32),
                                   s.rows, s.cols) == (0, 0)

    # 点到箭 → 选中反馈；点空白 → 无选中
    a = s.arrows[0]
    cx, cy = play.view.cell_center(a["row"], a["col"])
    play.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(int(cx), int(cy))))
    assert play.selected == (a["row"], a["col"]), "点到箭应有选中反馈"
    # 空白格（取一支箭外的一格）
    empty = next((r, c) for r in range(s.rows) for c in range(s.cols)
                 if s.arrow_at(r, c) is None)
    ex, ey = play.view.cell_center(*empty)
    play.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(int(ex), int(ey))))
    assert play.selected is None, "点空白不应有选中"
    play.draw(screen)

    pygame.quit()
    print("ok: 冒烟测试通过（窗口/标题→对局/画盘/点选反馈）")


if __name__ == "__main__":
    main()
