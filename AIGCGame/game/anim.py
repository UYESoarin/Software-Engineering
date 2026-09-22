"""表现层动画：飞出淡出 / 受阻晃动（I2 启用，I1 仅占位）。"""


class FlyOut:
    """沿朝向滑出并淡出；结束用时长而非帧数。"""

    def __init__(self, row, col, d, cell):
        self.x = (col + 0.5) * cell
        self.y = (row + 0.5) * cell
        self.d = d
        self.alpha = 255
        self.t = 0.0

    def advance(self, dt):
        self.t += dt
        speed = 420  # 像素/秒
        self.x += self.d[1] * speed * dt
        self.y += self.d[0] * speed * dt
        self.alpha = max(0, 255 - int(self.t * 400))

    @property
    def done(self):
        return self.t >= 0.45


class Blocked:
    """受阻短时左右晃。"""

    def __init__(self, cx, cy):
        self.cx, self.cy = cx, cy
        self.t = 0.0

    def advance(self, dt):
        self.t += dt

    def offset_x(self):
        return int(6 * (1 - self.t / 0.25) * (-1 if int(self.t * 40) % 2 else 1))

    @property
    def done(self):
        return self.t >= 0.25
