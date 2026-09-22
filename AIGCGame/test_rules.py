"""规则层单元测试（不依赖 pygame）。运行：python test_rules.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import levels
from game.rules import Session, DIRS
from game.solver import solve, analyze
from game.score import evaluate
from game.save import ProgressStore


def test_dirs():
    assert DIRS["up"] == (-1, 0)
    assert DIRS["down"] == (1, 0)
    assert DIRS["left"] == (0, -1)
    assert DIRS["right"] == (0, 1)
    print("ok: 四向增量 DIRS")


def test_levels_load():
    lv = levels.load_levels()
    assert len(lv) >= 8, "至少 8 关（含扩展 L4–L7）"
    for l in lv:
        for key in ("id", "name", "rows", "cols", "moves", "arrows", "solution"):
            assert key in l, f"{l['id']} 缺字段 {key}"
        for a in l["arrows"]:
            assert 0 <= a["row"] < l["rows"], f"{l['id']} 行越界"
            assert 0 <= a["col"] < l["cols"], f"{l['id']} 列越界"
            assert a["dir"] in DIRS, f"{l['id']} 方向非法"
    print("ok: levels.json 字段与越界校验（含 solution）")


def test_reference_solution():
    """每关的 solution 字段必须按真实规则完整清空。"""
    for lv in levels.load_levels():
        s = Session(lv)
        for rid in lv["solution"]:
            a = next(x for x in s.arrows if x["id"] == rid)
            r = s.try_clear(a["row"], a["col"])
            assert r and r["type"] == "fly", f"{lv['id']} 参考解 {rid} 未飞出: {r}"
        assert s.won, f"{lv['id']} 参考解未清空"
    print("ok: 八关 solution 均按规则通关")


def test_solver_all_levels():
    """solver 对每个线上关卡都能给出完整解序。"""
    for lv in levels.load_levels():
        solution = solve(lv)
        assert solution is not None, f"{lv['id']} 死锁"
        assert len(solution) == len(lv["arrows"]), f"{lv['id']} 解序长度不符"
        assert analyze(lv)["solvable"], f"{lv['id']} analyze 判定不可解"
    print("ok: solver 八关可解 + analyze 指标")


def test_blocked_and_moves():
    l0 = levels.load_levels()[0]
    s = Session(l0)
    assert s.moves_left == 5 and s.arrows_left == 3
    r = s.try_clear(1, 0)
    assert r["type"] == "blocked" and r["blocker"]["id"] == "b"
    assert s.moves_left == 4 and s.arrows_left == 3, "受阻不消箭、扣余次"
    print("ok: 受阻判定与余次扣减（T02）")


def test_fly_and_edge():
    l0 = levels.load_levels()[0]
    s = Session(l0)
    assert s.try_clear(1, 2)["type"] == "fly" and s.arrows_left == 2
    assert s.try_clear(2, 4)["type"] == "fly" and s.arrows_left == 1
    print("ok: 飞出与贴边越界（T01/T03）")


def test_reset():
    l1 = levels.load_levels()[1]
    s = Session(l1)
    s.try_clear(2, 2)
    s.try_clear(2, 0)
    s.reset()
    assert s.arrows_left == 5 and s.moves_left == 3
    assert not s.can_undo, "重开应清空撤销栈"
    print("ok: 快照复位（T06）")


def test_undo_fly():
    l0 = levels.load_levels()[0]
    s = Session(l0)
    before = [(a["id"], a["row"], a["col"]) for a in s.arrows]
    s.try_clear(1, 2)  # b 飞出
    assert s.arrows_left == 2 and s.can_undo
    assert s.undo()
    assert s.arrows_left == 3
    assert [(a["id"], a["row"], a["col"]) for a in s.arrows] == before
    print("ok: 撤销成功飞出（T07）")


def test_undo_blocked():
    l0 = levels.load_levels()[0]
    s = Session(l0)
    s.try_clear(1, 0)  # a 被 b 挡，扣次
    assert s.moves_left == 4
    assert s.undo()
    assert s.moves_left == 5 and s.arrows_left == 3
    print("ok: 撤销失误扣次（T08）")


def test_score():
    lv = levels.load_levels()[0]
    r = evaluate(lv, elapsed=5.0, mistakes=0)
    assert r["stars"] == 3 and r["score"] == 1000, "无失误且不超时应满分 3 星"
    r = evaluate(lv, elapsed=100.0, mistakes=5)
    assert r["stars"] == 1 and 0 <= r["score"] <= 1000, "超时+失误满应 1 星且不越界"
    print("ok: 评分边界（满分 / 超时 / 失误）")


def test_save_roundtrip():
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "save.json")
    store = ProgressStore(path)
    store.save_in_progress("L2", [{"id": "a", "row": 1, "col": 1, "dir": "up"}], 2, 12.34)
    other = ProgressStore(path)
    assert other.data["in_progress"]["level_id"] == "L2"
    assert other.data["in_progress"]["moves_left"] == 2
    store.complete_level("L2", "L3", {"score": 950, "time": 10.0, "stars": 3})
    assert store.data["unlocked_level"] == "L3"
    assert store.data["best"]["L2"]["stars"] == 3
    print("ok: 存档 round-trip + 解锁 + 最佳分（T11）")


if __name__ == "__main__":
    test_dirs()
    test_levels_load()
    test_reference_solution()
    test_solver_all_levels()
    test_blocked_and_moves()
    test_fly_and_edge()
    test_reset()
    test_undo_fly()
    test_undo_blocked()
    test_score()
    test_save_roundtrip()
    print("\n全部规则层测试通过。")
