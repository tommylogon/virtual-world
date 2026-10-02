"""task-518: ranged weapons and ammunition.

A ranged weapon (`ranged`/`bow` tag) needs ammunition (`ammo` tag): a shot
spends one use even when it misses, and an empty quiver is a clean failure with
no roll and no damage. The ammo item is never auto-selected as a melee weapon.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_CARRYING
from player import Player


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.add_player(Player("Archer"))
    world.add_player(Player("Target"))
    return world


def add_item(world, owner, node_id, name, props):
    node = Node(id=node_id, type="item", name=name, properties={
        "name": name, "weight": 1, "current_state": "normal",
        "actions": ["examine", "take", "drop"], "tags": [],
        **props,
    })
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=world._player_node_id(owner),
                              type=EDGE_CARRYING))
    return node


def add_bow(world, owner="Archer", node_id="item_bow", damage="1d6"):
    return add_item(world, owner, node_id, "Yew Bow", {
        "damage": damage, "damage_type": "piercing",
        "tags": ["weapon", "ranged", "bow"],
    })


def add_ammo(world, owner="Archer", node_id="item_quiver", uses=5):
    return add_item(world, owner, node_id, "Quiver of Arrows", {
        "uses": uses, "max_uses": uses, "base_weight": 1, "weight": 1,
        "stackable": True, "tags": ["ammo", "projectile"],
    })


def force_hit(world):
    """First d20 (attack) high, second (defence) low, damage dice minimal."""
    calls = {"n": 0}

    def fake(n, sides, bonus=0):
        if sides == 20:
            calls["n"] += 1
            return (20 + bonus) if calls["n"] == 1 else 1
        return 1
    world.skills.roll_dice = fake


def force_miss(world):
    calls = {"n": 0}

    def fake(n, sides, bonus=0):
        if sides == 20:
            calls["n"] += 1
            return (1 + bonus) if calls["n"] == 1 else 20
        return 1
    world.skills.roll_dice = fake


class TestRangedAttack:
    def test_bow_attack_consumes_an_arrow(self):
        world = make_world()
        add_bow(world)
        quiver = add_ammo(world, uses=5)
        force_hit(world)
        target = world.player_manager.get_player("Target")
        before = target.vitals["HP"]

        result = world.combat.player_attack("Archer", "Target")

        assert "bow" in result.lower()
        assert quiver.properties["uses"] == 4, "one arrow spent"
        assert target.vitals["HP"] < before, "the bow dealt its damage"

    def test_bow_without_ammo_fails_cleanly(self):
        world = make_world()
        add_bow(world)
        target = world.player_manager.get_player("Target")
        before = target.vitals["HP"]

        result = world.combat.player_attack("Archer", "Target")

        assert "none" in result.lower() or "not taken" in result.lower()
        assert target.vitals["HP"] == before, "no damage without an arrow"

    def test_ammo_is_spent_even_on_a_miss(self):
        world = make_world()
        add_bow(world)
        quiver = add_ammo(world, uses=5)
        force_miss(world)
        target = world.player_manager.get_player("Target")
        before = target.vitals["HP"]

        result = world.combat.player_attack("Archer", "Target")

        assert "miss" in result.lower()
        assert quiver.properties["uses"] == 4
        assert target.vitals["HP"] == before

    def test_single_arrow_is_removed_when_spent(self):
        world = make_world()
        add_bow(world)
        add_ammo(world, node_id="item_single_arrow", uses=1)
        force_hit(world)

        world.combat.player_attack("Archer", "Target")

        assert world.graph.get_node("item_single_arrow") is None

    def test_ammo_is_never_auto_selected_as_a_weapon(self):
        world = make_world()
        add_item(world, "Archer", "item_broadhead", "broadhead_arrow", {
            "damage": 0, "tags": ["ammo", "projectile", "weapon"],
        })
        assert world.combat._best_weapon_node("Archer") is None

    def test_best_weapon_prefers_bow_over_ammo(self):
        world = make_world()
        add_item(world, "Archer", "item_broadhead", "broadhead_arrow", {
            "damage": 0, "tags": ["ammo", "projectile", "weapon"],
        })
        add_bow(world)
        best = world.combat._best_weapon_node("Archer")
        assert best is not None and best.id == "item_bow"


class TestAuthoredRangedContent:
    def test_vekka_bow_is_a_ranged_weapon(self):
        import json
        p = Path(__file__).parent.parent / "data" / "library" / "items" / "vekka_hunting_bow.json"
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        assert "ranged" in d["tags"]
        assert d["damage"] and d["damage_type"] == "piercing"

    def test_arrows_carry_the_ammo_tag(self):
        import json
        base = Path(__file__).parent.parent / "data" / "library" / "items"
        for name in ("arrow.json", "broadhead_arrow.json", "quiver_of_arrows.json"):
            d = json.loads((base / name).read_text(encoding="utf-8-sig"))
            assert "ammo" in d["tags"], name

    def test_quiver_is_a_stack(self):
        import json
        p = Path(__file__).parent.parent / "data" / "library" / "items" / "quiver_of_arrows.json"
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        assert d["uses"] > 1 and d.get("stackable") is True

    def test_vekka_carries_bow_and_arrows(self):
        import json
        p = Path(__file__).parent.parent / "data" / "library" / "characters" / "Vekka.json"
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        assert "vekka_hunting_bow" in d["inventory"]
        assert any("arrow" in str(i) for i in d["inventory"])
