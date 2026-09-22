"""表现层动画：飞出淡出 / 受阻前冲返回。

动画只表现规则层已经发生的结果，不在这里改盘面、余次。
坐标均为屏幕像素；结束用时长而非帧数，与帧率解耦。
"""


class FlyOut:
    """沿朝向滑出并淡出。"""

    def __init__(self, x, y, delta, s, color):
        self.x = x              # 屏幕坐标（箭心）
        self.y = y
        self.dr, self.dc = delta  # 飞行方向增量（行、列）
        self.s = s              # 箭头尺寸（像素）
        self.color = color
        self.alpha = 255        # 透明度，随时间衰减
        self.t = 0.0            # 已播放时长（秒）

    def advance(self, dt):
        self.t += dt
        speed = 420             # 像素/秒
        self.x += self.dc * speed * dt
        self.y += self.dr * speed * dt
        self.alpha = max(0, 255 - int(self.t * 400))  # 线性淡出

    @property
    def done(self):
        return self.t >= 0.45


class BlockedReturn:
    """受阻：前冲 → 碰撞停顿（闪烁）→ 缓动回原位。"""

    def __init__(self, row, col, start_x, start_y, impact_x, impact_y,
                 delta, arrow_size, duration=0.58):
        self.row = row          # 被挡箭的格子（用于在盘上定位它）
        self.col = col
        self.start_x = start_x
        self.start_y = start_y
        self.impact_x = impact_x
        self.impact_y = impact_y
        self.x = start_x        # 当前绘制位置
        self.y = start_y
        self.dr, self.dc = delta
        self.arrow_size = arrow_size
        self.duration = duration
        self.t = 0.0
        self.flash = 0.0        # 碰撞闪烁强度 1 → 0

    @staticmethod
    def _ease_out_cubic(x):
        x = max(0.0, min(1.0, x))
        return 1 - (1 - x) ** 3

    @staticmethod
    def _ease_in_out(x):
        x = max(0.0, min(1.0, x))
        return x * x * (3 - 2 * x)

    def advance(self, dt):
        self.t += dt
        forward_t = 0.18        # 前冲段时长
        impact_t = 0.25         # 碰撞停顿结束时刻

        if self.t <= forward_t:
            p = self._ease_out_cubic(self.t / forward_t)
            self.x = self.start_x + (self.impact_x - self.start_x) * p
            self.y = self.start_y + (self.impact_y - self.start_y) * p
            self.flash = 0.0
        elif self.t <= impact_t:
            self.x = self.impact_x
            self.y = self.impact_y
            self.flash = 1.0 - (self.t - forward_t) / (impact_t - forward_t)
        else:
            p = self._ease_in_out((self.t - impact_t) / (self.duration - impact_t))
            self.x = self.impact_x + (self.start_x - self.impact_x) * p
            self.y = self.impact_y + (self.start_y - self.impact_y) * p
            self.flash = 0.0

    @property
    def done(self):
        return self.t >= self.duration
