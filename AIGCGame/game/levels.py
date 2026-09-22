"""关卡数据加载。数据与规则分离：改关改 levels.json，不改 rules.py。"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(_ROOT, "levels.json")


def load_levels(path=None):
    path = path or DEFAULT_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)
