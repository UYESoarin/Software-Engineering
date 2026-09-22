"""表现层动画：飞出淡出 / 受阻晃动。

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


class Blocked:
    """受阻短时左右晃；所指向的箭仍留在盘上。"""

    def __init__(self, row, col):
        self.row = row          # 用于在盘上定位那支被挡的箭
        self.col = col
        self.t = 0.0

    def advance(self, dt):
        self.t += dt

    def offset_x(self):
        # 幅度随时间衰减，方向按 40Hz 交替 → 左右短晃
        return int(6 * (1 - self.t / 0.25) * (-1 if int(self.t * 40) % 2 else 1))

    @property
    def done(self):
        return self.t >= 0.25
