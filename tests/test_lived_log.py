"""Objective per-character record of what was lived (engine.lived_log) —
see docs/design/lived-log-format.md. Renamed from `trace` by task-542."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import lived_log as T
from player import Player


def test_record_appends_expected_shape():
    p = Player("Gribba")
    T.record(p, 10, "act", "took a ration", why="needs:hunger",
             area="Food Storage", tags=["need"], salient=True)
    log = T.ensure(p)
    assert len(log) == 1
    e = log[0]
    assert e["tick"] == 10
    assert "t" not in e, "the cryptic 't' key must not be written any more"
    assert e["kind"] == "act"
    assert e["what"] == "took a ration"
    assert e["why"] == "needs:hunger"
    assert e["area"] == "Food Storage"
    assert e["salient"] is True
    assert e["tags"] == ["need"]


def test_record_tolerates_player_without_lived_log():
    class Bare:
        pass
    b = Bare()
    T.record(b, 1, "move", "went north")
    assert len(b.lived_log) == 1


def test_cap_prefers_salient_and_newest():
    p = Player("Rag-Tail")
    T.record(p, 1, "need", "oldest", salient=True)          # salient, kept
    for i in range(2, T.MAX_ENTRIES + 50):
        T.record(p, i, "act", f"routine {i}")
    log = T.ensure(p)
    assert len(log) == T.MAX_ENTRIES
    whats = [e["what"] for e in log]
    assert "oldest" in whats                                 # salient survived
    assert whats[-1] == f"routine {T.MAX_ENTRIES + 49}"      # newest survived
    assert "routine 2" not in whats                          # oldest routine trimmed


def test_rollup_collapses_runs_but_keeps_salient():
    p = Player("Tusker")
    T.record(p, 1, "act", "paced the tunnel", why="plan:patrol", area="Mine Access")
    T.record(p, 2, "act", "paced the tunnel", why="plan:patrol", area="Mine Access")
    T.record(p, 3, "act", "paced the tunnel", why="plan:patrol", area="Mine Access")
    T.record(p, 4, "act", "paced the tunnel", why="plan:patrol", area="Mine Access")
    T.record(p, 5, "act", "paced the tunnel", why="plan:patrol", area="Mine Access")
    T.record(p, 6, "death", "died of hypothermia", salient=True)
    removed = T.rollup(p, min_run=5)
    assert removed >= 4
    log = T.ensure(p)
    assert any(e.get("rolled") == 5 for e in log)
    assert any(e["what"] == "died of hypothermia" and e["salient"] for e in log)


def test_since_and_summarize_window():
    p = Player("Kiala")
    T.record(p, 100, "move", "entered Food Storage", why="goal:eat", area="Food Storage")
    T.record(p, 200, "act", "ate", why="goal:eat", area="Food Storage")
    assert len(T.since(p, 150)) == 1
    lines = T.summarize_window(p, since_tick=150)
    assert len(lines) == 1
    assert "ate" in lines[0]
    assert "goal:eat" in lines[0]


def test_load_and_to_list_roundtrip():
    src = Player("Belne")
    T.record(src, 7, "observe", "saw a fire", area="Gathering Pit")
    data = T.to_list(src)
    dst = Player("Belne")
    T.load(dst, data)
    assert T.to_list(dst) == data
    assert T.to_list(Player("Empty")) == []


def test_load_migrates_the_legacy_t_key():
    """Task-542 back-compat. The failure this guards is silent, not loud: if
    `load()` copies entries verbatim, a legacy entry keeps `t`, every reader
    falls back to 0, `rollup`'s sort scrambles them and `since()` finds nothing.
    Nothing raises, so only an assertion catches it."""
    legacy = [{"t": 41, "kind": "move", "what": "went north", "why": "",
               "area": "Tunnel", "tags": [], "salient": False}]
    p = Player("Grub")
    T.load(p, legacy)
    assert p.lived_log[0]["tick"] == 41
    assert "t" not in p.lived_log[0]
    # The readers must see the migrated tick, not 0.
    assert len(T.since(p, 40)) == 1
    assert len(T.since(p, 42)) == 0
    assert "t=41" in T.summarize_window(p)[0]


def test_load_survives_garbage_entries():
    p = Player("Grub")
    T.load(p, [None, "nope", {"tick": 3, "what": "ok"}])
    assert len(p.lived_log) == 1
    assert p.lived_log[0]["what"] == "ok"


def test_player_to_dict_includes_lived_log():
    p = Player("Croak-Mother")
    T.record(p, 3, "need", "Thirst crossed 75", why="needs:thirst")
    d = p.to_dict()
    assert "lived_log" in d
    assert d["lived_log"][0]["why"] == "needs:thirst"
    assert d["lived_log"][0]["tick"] == 3
