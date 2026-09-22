"""音效统一入口；音频加载失败时游戏仍应正常运行。"""
from pathlib import Path

import pygame


class Audio:
    """管理 click / fly / blocked / undo / clear / fail 短音效。

    任一音效加载失败只跳过该音效，不影响游戏启动。
    """

    def __init__(self, asset_dir):
        self.enabled = True
        self.sounds = {}
        self.asset_dir = Path(asset_dir)
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            self.enabled = False
            return
        for name in ("click", "fly", "blocked", "undo", "clear", "fail"):
            path = self.asset_dir / f"{name}.wav"
            try:
                self.sounds[name] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                pass

    def play(self, name, volume=1.0):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        sound.set_volume(max(0.0, min(1.0, volume)))
        sound.play()
