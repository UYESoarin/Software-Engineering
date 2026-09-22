"""规则层单元测试（不依赖 pygame）。运行：python test_rules.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import levels
from game.rules import Session, DIRS

# 参考解（用于验盘，非唯一解）
REF = {
    "L0": ["b", "a", "c"],
    "L1": ["d", "c", "a", "b", "e"],
    "L2": ["b", "c", "f", "a", "x", "d", "g"],
    "L3": ["p0", "p2", "p3", "p4", "p6", "p7", "p5", "p1", "p8"],
}


def test_dirs():
    assert DIRS["up"] == (-1, 0)
    assert DIRS["down"] == (1, 0)
    assert DIRS["left"] == (0, -1)
    assert DIRS["right"] == (0, 1)
    print("ok: 四向增量 DIRS")


def test_levels_load():
    lv = levels.load_levels()
    assert len(lv) >= 4, "至少 4 关"
    for l in lv:
        for key in ("id", "name", "rows", "cols", "moves", "arrows"):
            assert key in l, f"{l['id']} 缺字段 {key}"
        for a in l["arrows"]:
            assert 0 <= a["row"] < l["rows"], f"{l['id']} 行越界"
            assert 0 <= a["col"] < l["cols"], f"{l['id']} 列越界"
            assert a["dir"] in DIRS, f"{l['id']} 方向非法"
    print("ok: levels.json 字段与越界校验")


def test_reference_solvable():
    for lv in levels.load_levels():
        s = Session(lv)
        for rid in REF[lv["id"]]:
            a = next(x for x in s.arrows if x["id"] == rid)
            r = s.try_clear(a["row"], a["col"])
            assert r and r["type"] == "fly", f"{lv['id']} 参考序 {rid} 未飞出: {r}"
        assert s.won, f"{lv['id']} 参考序未清空"
    print("ok: 四关参考序均可通关")


def test_all_solvable():
    for lv in levels.load_levels():
        s = Session(lv)
        while s.arrows:
            a = next((a for a in s.arrows if s.can_fly(a["row"], a["col"])), None)
            if a is None:
                break
            s.try_clear(a["row"], a["col"])
        assert not s.arrows, f"{lv['id']} 无可行拆除序（死锁）"
    print("ok: 四关均存在可行拆除序（无死锁）")


def test_blocked_and_moves():
    l0 = levels.load_levels()[0]  # a(1,0)右 被 b(1,2)上 挡
    s = Session(l0)
    assert s.moves_left == 5 and s.arrows_left == 3
    r = s.try_clear(1, 0)
    assert r["type"] == "blocked" and r["blocker"]["id"] == "b"
    assert s.moves_left == 4 and s.arrows_left == 3, "受阻不消箭、扣余次"
    print("ok: 受阻判定与余次扣减（T02）")


def test_fly_and_edge():
    l0 = levels.load_levels()[0]
    s = Session(l0)
    r = s.try_clear(1, 2)  # b 朝上贴空，飞出
    assert r["type"] == "fly" and s.arrows_left == 2
    r = s.try_clear(2, 4)  # c 朝左贴边，飞出且不越界
    assert r["type"] == "fly" and s.arrows_left == 1
    print("ok: 飞出与贴边越界（T01/T03）")


def test_reset():
    l1 = levels.load_levels()[1]
    s = Session(l1)
    s.try_clear(2, 2)  # d
    s.try_clear(2, 0)  # c
    assert s.arrows_left == 3
    s.reset()
    assert s.arrows_left == 5 and s.moves_left == 3, "复位应回到开局快照"
    print("ok: 快照复位（T06）")


if __name__ == "__main__":
    test_dirs()
    test_levels_load()
    test_reference_solvable()
    test_all_solvable()
    test_blocked_and_moves()
    test_fly_and_edge()
    test_reset()
    print("\n全部规则层测试通过。")
