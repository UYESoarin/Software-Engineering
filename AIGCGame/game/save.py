"""本地进度存档。只依赖标准库。

存档写入用户数据目录（Windows 为 %APPDATA%/YiJianYouYiJian），
不写 exe / 资源目录，避免打包后目录不可写。
"""
import json
import os
from pathlib import Path

APP_DIR_NAME = "YiJianYouYiJian"
SAVE_VERSION = 1


def get_save_path():
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home()))
    elif os.name == "posix":
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    else:
        base = Path.home()
    folder = base / APP_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "save.json"


def default_data():
    return {
        "version": SAVE_VERSION,
        "current_level": "L0",
        "unlocked_level": "L0",
        "in_progress": None,
        "best": {},
    }


class ProgressStore:
    """进度存档：解锁关、最佳分、进行中快照。损坏时安全回退默认值。"""

    def __init__(self, path=None):
        self.path = Path(path) if path else get_save_path()
        self.data = default_data()
        self.load()

    def load(self):
        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            self.data = raw if raw.get("version") == SAVE_VERSION else default_data()
        except (OSError, ValueError, TypeError):
            self.data = default_data()
        return self.data

    def save(self):
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        temp.replace(self.path)

    def save_in_progress(self, level_id, arrows, moves_left, elapsed):
        self.data["current_level"] = level_id
        self.data["in_progress"] = {
            "level_id": level_id,
            "arrows": [dict(a) for a in arrows],
            "moves_left": int(moves_left),
            "elapsed": round(float(elapsed), 2),
        }
        self.save()

    def clear_in_progress(self):
        self.data["in_progress"] = None
        self.save()

    def complete_level(self, level_id, next_level_id=None, stats=None):
        self.data["current_level"] = next_level_id or level_id
        if next_level_id:
            self.data["unlocked_level"] = next_level_id
        self.data["in_progress"] = None
        if stats is not None:
            old = self.data["best"].get(level_id)
            if old is None or stats["score"] > old["score"]:
                self.data["best"][level_id] = {
                    "score": stats["score"],
                    "time": stats["time"],
                    "stars": stats["stars"],
                }
        self.save()

    @property
    def has_resume(self):
        return self.data.get("in_progress") is not None

    def unlocked_index(self, level_ids):
        """返回已解锁到第几关（0-based 下标）。"""
        unlocked = self.data.get("unlocked_level", level_ids[0])
        if unlocked in level_ids:
            return level_ids.index(unlocked)
        return 0
