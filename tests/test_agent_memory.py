"""AgentMind (task-403 slice 2): preconceived knowledge, need-driven recall and
trait-driven memory decay."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from player import Player
from engine.agent_memory import AgentMind


def _world():
    return create_app({"TESTING": True}).world


def _player(world, name="Scout", **kwargs):
    p = Player(name)
    for key, value in kwargs.items():
        setattr(p, key, value)
    return p


# ── preconceived knowledge ───────────────────────────────────────────────


class TestPreconceived:
    def test_injects_memories_areas_and_ways(self):
        world = _world()
        p = _player(world)
        pdata = {
            "preconceived_knowledge": {
                "memories": [
                    {"text": "The food cache is behind the kitchen.",
                     "tags": ["food", "camp"], "importance": 6, "location": "kitchen"},
                ],
                "known_areas": ["kitchen", "pantry"],
                "known_items": ["item_dried_meat"],
                "known_ways": {"way_kitchen_to_pantry": ["hidden", "behind_shelf"]},
            }
        }
        added = AgentMind(p, world.graph).load_preconceived(pdata)

        assert added == 1
        memory = p.memories[0]
        assert memory["source"] == "preconceived"
        assert memory["location"] == "kitchen"
        assert AgentMind(p, world.graph).knows_area("kitchen")
        assert AgentMind(p, world.graph).knows_area("item_dried_meat")
        assert "hidden" in p.known_way_aspects[("way_kitchen_to_pantry", "")]

    def test_is_idempotent(self):
        world = _world()
        p = _player(world)
        pdata = {"preconceived_knowledge": {"memories": [{"text": "Once told.", "tags": ["x"]}]}}
        mind = AgentMind(p, world.graph)
        assert mind.load_preconceived(pdata) == 1
        assert mind.load_preconceived(pdata) == 0
        assert len(p.memories) == 1


# ── recall ───────────────────────────────────────────────────────────────


class TestRecall:
    def _mind_with_memories(self, world):
        p = _player(world)
        p.add_memory("The pantry holds dried meat.", 0, importance=8, tags=["food", "pantry"])
        p.add_memory("A shiny coin was on the floor.", 0, importance=3, tags=["coin"])
        return AgentMind(p, world.graph), p

    def test_matches_by_need_tag_and_text(self):
        world = _world()
        mind, _ = self._mind_with_memories(world)
        hits = mind.recall(query="where is food", need="food")
        assert hits and "pantry" in hits[0]["text"].lower()

    def test_ranks_importance_times_salience(self):
        world = _world()
        mind, _ = self._mind_with_memories(world)
        hits = mind.recall(query="coin pantry food")
        assert hits[0]["importance"] >= hits[-1]["importance"]

    def test_returns_nothing_when_no_match(self):
        world = _world()
        mind, _ = self._mind_with_memories(world)
        assert mind.recall(query="dragon hoard treasure") == []

    def test_poor_memory_caps_surfacing_importance(self):
        world = _world()
        mind, p = self._mind_with_memories(world)
        p.traits = {"poor_memory": True}
        hits = mind.recall(query="pantry food")
        # The importance-8 memory exceeds the poor_memory cap of 6.
        assert all(h["importance"] <= 6 for h in hits)

    def test_perfect_memory_boosts_score_order_not_membership(self):
        world = _world()
        mind, p = self._mind_with_memories(world)
        p.traits = {"perfect_memory": True}
        hits = mind.recall(query="pantry food")
        assert hits and hits[0]["text"].startswith("The pantry")


# ── need-driven recall ───────────────────────────────────────────────────


class TestNeedRecall:
    def test_surfaces_a_recall_memory_once_per_day(self):
        world = _world()
        p = _player(world)
        mind = AgentMind(p, world.graph)
        p.add_memory("The river is west of camp.", 0, importance=6, tags=["thirst", "water"])

        first = mind.surface_need_memory("thirst", tick=10, day_key="day1")
        assert first is not None
        assert first["source"] == "need_recall"
        # Same day, same need: already surfaced.
        assert mind.surface_need_memory("thirst", tick=11, day_key="day1") is None
        # A new day may surface it again.
        assert mind.surface_need_memory("thirst", tick=20, day_key="day2") is not None

    def test_never_fabricates_when_nothing_matches(self):
        world = _world()
        p = _player(world)
        mind = AgentMind(p, world.graph)
        assert mind.surface_need_memory("thirst", tick=1, day_key="day1") is None


# ── decay ────────────────────────────────────────────────────────────────


class TestDecay:
    def test_inert_without_a_decay_trait(self):
        world = _world()
        p = _player(world)
        p.add_memory("Fresh.", 0, importance=5)
        before = len(p.memories)
        assert AgentMind(p, world.graph).apply_decay() == 0
        assert len(p.memories) == before
        assert p.memories[0].get("salience_override", 0) == 0

    def test_poor_memory_decays_and_removes_faded_memories(self):
        world = _world()
        p = _player(world)
        p.traits = {"poor_memory": True}
        p.add_memory("Strong memory.", 0, importance=8, tags=["x"])
        p.memories[0]["salience_override"] = 5.0
        p.add_memory("Faint memory.", 0, importance=5, tags=["y"])
        p.memories[1]["salience_override"] = 0.01

        removed = AgentMind(p, world.graph).apply_decay()
        assert removed == 1
        assert p.memories[0]["salience_override"] < 5.0
        assert all("Faint" not in m["text"] for m in p.memories)

    def test_preconceived_memories_never_decay(self):
        world = _world()
        p = _player(world)
        p.traits = {"poor_memory": True}
        p.add_memory("Told at the start of the world.", 0, importance=5, source="preconceived")
        p.memories[0]["salience_override"] = 0.001
        assert AgentMind(p, world.graph).apply_decay() == 0
        assert len(p.memories) == 1


# ── serialization integration ────────────────────────────────────────────


class TestSerialization:
    def test_preconceived_knowledge_survives_a_world_load(self):
        world = _world()
        payload = {
            "players": {
                "Scout": {
                    "name": "Scout",
                    "current_area": "kitchen",
                    "preconceived_knowledge": {
                        "memories": [{"text": "The cache is in the pantry.",
                                      "tags": ["food"], "importance": 6}],
                        "known_areas": ["kitchen", "pantry"],
                    },
                }
            }
        }
        world.load_from_dict(payload)
        scout = world.players.get("Scout")
        assert scout is not None
        assert any(m["source"] == "preconceived" for m in scout.memories)
        assert any(str(k).lower() == "pantry" for k in scout.known)
