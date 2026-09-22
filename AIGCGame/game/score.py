"""关卡评分：纯逻辑，不依赖 pygame。

总分 = 70% 准确度 + 30% 时间表现（0–1000）。
准确度只受失误影响；超时只影响时间分，不直接判失败。
撤销不回退时间，避免「撤销 + 重试」刷时间。
"""


def evaluate(level, elapsed, mistakes):
    moves = max(1, int(level["moves"]))
    par_time = max(1.0, float(level.get("par_time", 30)))

    # 准确度：失误越多越低，到 0 为止
    accuracy = max(0.0, 1.0 - mistakes / moves)

    # 时间分：par_time 内满分；超时最多再给 2×par_time 的线性衰减区间
    if elapsed <= par_time:
        time_factor = 1.0
    else:
        overtime = elapsed - par_time
        time_factor = max(0.0, 1.0 - overtime / (par_time * 2.0))

    score = int(round(700 * accuracy + 300 * time_factor))
    score = max(0, min(1000, score))

    if score >= 900:
        stars = 3
    elif score >= 700:
        stars = 2
    else:
        stars = 1

    return {
        "score": score,
        "stars": stars,
        "mistakes": mistakes,
        "time": round(float(elapsed), 2),
        "accuracy": round(accuracy, 3),
        "time_factor": round(time_factor, 3),
    }
