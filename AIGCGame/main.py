"""入口：初始化 pygame，运行「取输入 → 推进 → 画一帧」主循环。"""
import pygame

from game import levels, scenes


class App:
    """应用容器：窗口尺寸 + 关卡表，供各场景读取。"""

    WIDTH = 960
    HEIGHT = 640

    def __init__(self):
        self.w = self.WIDTH
        self.h = self.HEIGHT
        self.levels = levels.load_levels()


def main():
    app = App()
    pygame.init()
    screen = pygame.display.set_mode((app.w, app.h))
    pygame.display.set_caption("一箭又一箭")
    clock = pygame.time.Clock()
    scene = scenes.MenuScene(app)
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                nxt = scene.handle(event)
                if nxt is not None:
                    scene = nxt
        scene.update(dt)
        scene.draw(screen)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
