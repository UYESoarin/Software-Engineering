# Pygame 2 · 接口参考

安装：`pip install pygame`。文档：https://www.pygame.org/docs/

规则判定不调用本库。窗口、事件、绘制、字体、动画时间只出现在入口、场景与表现层。

---

## 1. 接口分表

下列为对局会用到的核心接口。`使用详述`只写本项目用得到的约定。

### 1.1 生命周期

| 接口 | 功能概述 | 使用详述 |
|---|---|---|
| `pygame.init()` | 打开显示、字体等子系统 | 创建窗口前调用一次；返回成功/失败计数，一般可忽略 |
| `pygame.quit()` | 关闭子系统 | 主循环结束后调用，避免退出后字体/音频残留 |
| `pygame.display.set_mode(size)` | 创建窗口，返回屏幕 Surface | `size=(w,h)` 像素；本项目固定分辨率，棋盘在窗口内居中 |
| `pygame.display.set_caption(title)` | 窗口标题 | 启动时设一次 |
| `pygame.display.flip()` | 把绘制结果送到屏幕 | 每帧在全部 `blit`/`draw` 之后调用一次 |
| `pygame.display.update(rectlist=None)` | 按脏矩形更新 | 全屏重绘时用 `flip` 即可，不必混用 |

### 1.2 时间

| 接口 | 功能概述 | 使用详述 |
|---|---|---|
| `pygame.time.Clock()` | 帧率控制器 | 主循环持有一个实例 |
| `Clock.tick(framerate)` | 限帧，返回上一帧毫秒 | `dt = tick(60) / 1000.0` 得到秒；位移用 `速度 * dt`，不要写死每帧像素 |

### 1.3 事件与指针

| 接口 | 功能概述 | 使用详述 |
|---|---|---|
| `pygame.event.get()` | 取出并清空事件队列 | 每帧必须抽干，否则窗口会假死；点选、退出都走这里 |
| `pygame.QUIT` | 用户点关闭 | 收到后结束主循环 |
| `pygame.MOUSEBUTTONDOWN` | 某一鼠标键按下 | 点箭、点按钮；看 `event.button == 1` 表示左键 |
| `event.pos` | 该事件的窗口坐标 `(x, y)` | 命中格子或 `Rect.collidepoint` |
| `pygame.event.wait()` | 阻塞直到下一事件 | 对局循环里不要用，动画会停 |
| `pygame.mouse.get_pressed()` | 当前是否按住 | **不要用来点选**：只反映这一帧状态，短按可能漏、长按会连发 |

### 1.4 Surface 与几何

| 接口 | 功能概述 | 使用详述 |
|---|---|---|
| `Surface.fill(color)` | 用纯色填满 | 每帧先填背景，再画棋盘，避免残影 |
| `Surface.blit(source, dest)` | 把另一块图贴上来 | HUD 文字、箭头图、按钮；`dest` 为左上角或 Rect |
| `Surface.set_alpha(value)` | 整图透明度 0–255 | 飞出淡出；在独立小 Surface 上设，再 blit 到屏幕 |
| `pygame.Rect(x, y, w, h)` | 轴对齐矩形 | 按钮、格子框、箭头占位 |
| `Rect.collidepoint(x, y)` | 点是否落在矩形内 | 按钮命中；格子命中也可用除法换算行列（见下文代码） |

坐标系：原点窗口左上，`x` 向右，`y` 向下。与关卡「行向下、列向右」一致：`x = ox + col * cell`，`y = oy + row * cell`。

### 1.5 绘制

| 接口 | 功能概述 | 使用详述 |
|---|---|---|
| `pygame.draw.rect(surface, color, rect, width=0)` | 矩形 | `width=0` 填充：按钮、HUD 底；`width=1` 描边：格子线 |
| `pygame.draw.polygon(surface, color, points)` | 多边形 | 箭头头部；`points` 为三个顶点，随朝向旋转 |
| `pygame.draw.line(surface, color, start, end, width)` | 线段 | 箭身；四向各画一短线接到三角底边 |
| `pygame.draw.circle(surface, color, center, radius)` | 圆 | 可选：选中高亮点 |

颜色为 RGB 元组，如 `(30, 32, 40)`。

### 1.6 字体

| 接口 | 功能概述 | 使用详述 |
|---|---|---|
| `pygame.font.Font(path, size)` | 从文件加载字体 | 中文用系统字体文件，例如 `C:/Windows/Fonts/msyh.ttc` |
| `pygame.font.SysFont(name, size)` | 按族名取字体 | 本机 pygame 2.6.1 扫描 Windows 注册表字体时可能抛 `TypeError`，不可当回退；中文一律用 `Font(path)` 直取 `msyh.ttc` |
| `Font.render(text, antialias, color)` | 文字生成 Surface | `antialias=True`；再 `blit` 到顶栏或飘字 |

### 1.7 Sprite（可选）

| 接口 | 功能概述 | 使用详述 |
|---|---|---|
| `pygame.sprite.Sprite` | 带 `image`/`rect` 的可绘制对象 | 只表示「正在飞出」的表现体 |
| `pygame.sprite.Group` | Sprite 容器 | `group.update(dt)`、`group.draw(screen)` |
| `Group.update(*args)` | 调用每个 Sprite.update | **不要**在这里做射线或改余次 |
| `Group.draw(surface)` | 按 `image`/`rect` 绘制 | 规则层不参与 |
| `pygame.sprite.spritecollide` | 像素矩形碰撞 | 本游戏阻挡不走它，走网格射线 |

---

## 2. 框架：主循环

Pygame 不代管循环，需要自己维持「取事件 → 更新 → 绘制 → 呈现」。

```python
import pygame

pygame.init()
screen = pygame.display.set_mode((960, 640))
pygame.display.set_caption("一箭又一箭")
clock = pygame.time.Clock()
scene = MenuScene()  # 当前场景；对局中换成 PlayScene
running = True

while running:
    dt = clock.tick(60) / 1000.0          # 秒；动画与帧率解耦
    for event in pygame.event.get():      # 必须抽干队列
        if event.type == pygame.QUIT:
            running = False
        else:
            nxt = scene.handle(event)     # 点选、切场景；返回新场景或 None
            if nxt is not None:
                scene = nxt
    scene.update(dt)                      # 只推进动画时间，不改规则结果
    screen.fill((30, 32, 40))
    scene.draw(screen)
    pygame.display.flip()

pygame.quit()
```

---

## 3. 模块：场景封装

每个画面同一套三个方法，主循环不关心里面是标题还是棋盘。动画未结束时丢掉点击。

```python
class PlayScene:
    def __init__(self, session):
        self.session = session            # 规则会话：盘面 / 余次 / 快照
        self.anim = None                  # 当前飞出或受阻；None 表示可点
        self.view = BoardView(origin=(180, 80), cell=64)

    def handle(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.anim:                     # 锁输入：一次结算对应一段动画
            return None
        if self.view.hit_restart(event.pos):
            self.session.restart()
            return None
        cell = self.view.pixel_to_cell(event.pos)
        if cell is None:
            return None
        result = self.session.try_clear(cell)  # 纯逻辑，无 pygame
        if result:
            self.anim = Animation.from_result(result)
        return None                       # 胜负时由 update 末尾切 ResultScene

    def update(self, dt):
        if self.anim:
            self.anim.advance(dt)
            if self.anim.done:
                self.anim = None

    def draw(self, screen):
        self.view.draw_board(screen, self.session, self.anim)
        self.view.draw_hud(screen, self.session)
```

---

## 4. 本项目关键片段

### 4.1 像素 ↔ 格子

```python
def pixel_to_cell(pos, ox, oy, cell, rows, cols):
    x, y = pos
    col = (x - ox) // cell
    row = (y - oy) // cell
    # 先丢盘外点击，再去规则层；避免负索引进网格
    if 0 <= row < rows and 0 <= col < cols:
        return int(row), int(col)
    return None
```

### 4.2 四向箭头（程序绘制）

```python
# d: 上(-1,0) 下(1,0) 左(0,-1) 右(0,1)
def draw_arrow(surf, cx, cy, d, color, s=18):
    dr, dc = d
    tip = (cx + dc * s, cy + dr * s)          # 箭头尖朝飞行方向
    bx, by = cx - dc * s * 0.4, cy - dr * s * 0.4
    # 底边垂直于朝向，得到左右两翼
    wx, wy = -dr * s * 0.45, dc * s * 0.45
    pygame.draw.line(surf, color, (cx, cy), tip, 3)
    pygame.draw.polygon(surf, color, [tip, (bx + wx, by + wy), (bx - wx, by - wy)])
```

### 4.3 用 dt 做飞出与受阻

```python
class FlyOut:
    def __init__(self, row, col, d, cell):
        self.x = (col + 0.5) * cell
        self.y = (row + 0.5) * cell
        self.d = d
        self.alpha = 255
        self.t = 0.0

    def advance(self, dt):
        self.t += dt
        speed = 420                         # 像素/秒
        self.x += self.d[1] * speed * dt
        self.y += self.d[0] * speed * dt
        self.alpha = max(0, 255 - int(self.t * 400))

    @property
    def done(self):
        return self.t >= 0.45


class Blocked:
    def __init__(self, cx, cy):
        self.cx, self.cy = cx, cy
        self.t = 0.0

    def advance(self, dt):
        self.t += dt

    def offset_x(self):
        # 短时左右晃；结束条件用时长而不是帧数
        return int(6 * (1 - self.t / 0.25) * ((self.t * 40) % 2 and 1 or -1))

    @property
    def done(self):
        return self.t >= 0.25
```

---

## 5. 选用关系

| 需求 | 走哪组接口 |
|---|---|
| 打开窗口、限 60 帧 | `init` / `set_mode` / `Clock.tick` / `flip` |
| 点箭、点按钮、关窗 | `event.get` + `MOUSEBUTTONDOWN` / `QUIT` |
| 网格、HUD、自绘箭 | `draw.*` + `Font.render` + `blit` |
| 飞出淡出、受阻变色 | 独立 Surface 的 `set_alpha` + `dt` 位移 |
| 判定能否飞出 | 不在本库；见策划案射线规则 |
