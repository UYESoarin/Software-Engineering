"""入口：初始化 pygame，运行「取输入 → 推进 → 画一帧」主循环。"""
import pygame

from game import audio, levels, pathing, save, scenes


class App:
    """应用容器：窗口尺寸 + 关卡表 + 进度存档 + 音效，供各场景读取。"""

    WIDTH = 960
    HEIGHT = 640

    def __init__(self, save_path=None):
        self.w = self.WIDTH
        self.h = self.HEIGHT
        self.levels = levels.load_levels()
        self.store = save.ProgressStore(save_path)
        self.audio = audio.Audio(pathing.resource_path("assets/sfx"))


def main():
    pygame.init()
    app = App()
    screen = pygame.display.set_mode((app.w, app.h))
    pygame.display.set_caption("一箭又一箭")
    clock = pygame.time.Clock()
    scene = scenes.MenuScene(app)
    running = True
    while running:
        dt = clock.tick(60) / 1000.0          # 秒；动画与帧率解耦
        for event in pygame.event.get():      # 必须抽干队列，否则窗口假死
            if event.type == pygame.QUIT:
                running = False
            else:
                nxt = scene.handle(event)     # 点选 / 切场景；返回新场景或 None
                if nxt is not None:
                    scene = nxt
        nxt = scene.update(dt)                # 推进动画；对局胜负也在这里切场景
        if nxt is not None:
            scene = nxt
        scene.draw(screen)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
