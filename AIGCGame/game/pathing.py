"""资源路径解析：兼容源码运行与 PyInstaller 打包（onefile 展开目录）。"""
import sys
from pathlib import Path


def resource_path(relative):
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[1]
    return base / relative
