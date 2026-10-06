"""lived_log -> first-person memory bridge (engine/lived_log_memory, task-727)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import lived_log, lived_log_memory
from player import Player


def test_phrase_covers_death_relationship_pursuit():
    assert (lived_log_memory.phrase({"kind": "death", "what": "died of hypothermia"})
            == "I died \u2014 hypothermia.")
    assert "closer to Belne" in lived_log_memory.phrase(
        {"kind": "relationship",
         "delta": {"with": "Belne", "closeness": 5, "cause": "tease"}})
    assert (lived_log_memory.phrase({"kind": "pursuit", "what": "started scouting"})
            == "Started scouting.")


def test_bridge_writes_once_then_marks_through():
    p = Player("Vekka")
    lived_log.record(p, 5, "relationship", "closeness toward Belne +5",
                     why="social:tease", area="Camp",
                     delta={"with": "Belne", "closeness": 5, "cause": "tease"})
    lived_log.record(p, 6, "death", "died of hypothermia",
                     why="cause:death", salient=True)

    assert lived_log_memory.bridge(p) == 2
    texts = [m["text"] for m in p.memories]
    assert any("closer to Belne" in t for t in texts)
    assert any("I died" in t for t in texts)

    # Idempotent: a second pass writes nothing and does not duplicate.
    assert lived_log_memory.bridge(p) == 0
    assert len([m for m in p.memories if m.get("source") == "lived_log"]) == 2


def test_bridge_skips_kinds_covered_elsewhere_but_advances_the_mark():
    p = Player("Thrazz")
    lived_log.record(p, 1, "social", "chat with Belne: friend", why="social:chat")
    lived_log.record(p, 2, "threat", "backs away from Belne",
                     why="threat:flee", salient=True)
    lived_log.record(p, 3, "need", "hunger crossed 50", why="needs:hunger")

    assert lived_log_memory.bridge(p) == 0        # these have their own writers
    assert p.memories == []
    assert p.lived_log_memorized_through == 3      # still marked so no rescan


def test_bridge_all_over_a_world():
    class _World:
        def __init__(self, players):
            self.players = players

    a = Player("A")
    b = Player("B")
    lived_log.record(a, 1, "death", "died of cold", salient=True)
    lived_log.record(b, 2, "pursuit", "started foraging")
    assert lived_log_memory.bridge_all(_World({"A": a, "B": b})) == 2
