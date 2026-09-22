"""关卡数据加载。数据与规则分离：改关改 levels.json，不改 rules.py。"""
import json

from .pathing import resource_path

DEFAULT_PATH = resource_path("levels.json")


def load_levels(path=None):
    path = path or DEFAULT_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)
