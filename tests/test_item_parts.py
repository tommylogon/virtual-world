"""Item parts: a device assembled from items (task-493).

The model agreed in the task-299 discussion, implemented here:

- a **part is a child item of a parent** — no new edge type, no ``is_part``
  flag. The only thing that says "this is a component" is that it does not
  declare ``take`` in its own ``actions``;
- each part carries its own triggers, state and ``uses``;
- **charge is the generic ``uses``** — there is deliberately no ``power`` or
  ``charge`` property on the base item;
- depletion follows an existing pattern, and a part never detaches silently.

And the two halves that were drifting: every verb that *moves* an item now
honours the action list (``take`` was the only one that did), and the client's
item listing walks containment the way ``engine/item_reach`` does — any depth,
sealed by container state — through one shared module.

The worked example is a phone with a battery part: ``data/library/items/
phone.json`` holds ``contents: ["phone_battery"]`` and no charge of its own;
the battery holds the charge.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN, Edge, Node
from engine.items.action_contract import (
    is_part,
    is_portable,
    item_allows,
    item_actions,
    parent_of,
)

LIB = Path(__file__).parent.parent / "data" / "library" / "items"
AREA = "A Forest Clearing"


def _lib(item_id):
    return json.loads((LIB / f"{item_id}.json").read_text(encoding="utf-8-sig"))


def _world():
    from virtual_world_engine import VirtualWorld
    w = VirtualWorld()
    w.movement.add_area(Area(AREA, "Open ground, low brush.", []))
    w.name_matcher._set_player_area(w.active_player, AREA)
    return w


def _place(w, library_id):
    node, _lib = w.effects._hydrate_item(library_id, {}, always_fresh=True)
    w.graph.add_edge(Edge(source=node.id, target=w.get_current_area_id(), type=EDGE_IN))
    return node


def _carry(w, node):
    """Put *node* in the player's hands, the way a take would."""
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    w.graph.add_edge(Edge(source=node.id, target=player_id, type=EDGE_EQUIPPED))
    return node


def _phone_with_battery(w):
    """The worked example, placed the way the library route places it:
    the parent first, then each ``contents`` entry as a child ``in`` edge."""
    phone = _place(w, "phone")
    for child_id in _lib("phone").get("contents") or []:
        child = w.effects._hydrate_item(child_id, {}, always_fresh=True)[0]
        w.graph.add_edge(Edge(source=child.id, target=phone.id, type=EDGE_IN))
    battery = w.graph.get_node(
        next(e.source for e in w.graph.get_edges_for_target(phone.id, EDGE_IN)
             if e.source.startswith("phone_battery")))
    return phone, battery


# ── the declaration is the whole model ───────────────────────────────────────

def test_a_part_is_not_takeable_and_a_thing_is():
    assert is_part(_node(_lib("phone_battery")))
    assert not is_part(_node(_lib("phone")))
    assert is_portable(_node(_lib("phone")))


def test_the_action_list_is_the_authority():
    node = _node({"actions": "examine,use"})
    assert item_actions(node) == ["examine", "use"]
    assert item_allows("use", node)
    assert not item_allows("take", node)
    assert not item_allows("drop", node)


def test_an_action_list_may_be_a_list_or_a_string():
    assert item_actions(_node({"actions": ["examine", "use"]})) == ["examine", "use"]
    assert item_actions(_node({"actions": "examine, use"})) == ["examine", "use"]


def test_a_declared_drop_would_author_take_right_back_in():
    """``normalize_item_actions`` adds each action's inverse, so a part has to
    omit BOTH halves of the take/drop pair. Worth pinning: the obvious
    half-fix is silently undone by hydration."""
    from engine.item_actions import normalize_item_actions

    assert "take" in normalize_item_actions("drop")
    assert "take" not in normalize_item_actions(["examine", "use"])


def test_parent_of_finds_the_device():
    w = _world()
    phone, battery = _phone_with_battery(w)
    assert parent_of(w.graph, battery) is phone
    assert parent_of(w.graph, phone) is None


def _node(props, name="thing", node_id="item_thing"):
    return Node(id=node_id, type="item", name=name, properties=dict(props))


# ── no new per-device property (criterion 2) ────────────────────────────────

def test_charge_is_the_generic_uses_not_a_new_property():
    """The whole point of "no `power` property": a part's charge is `uses`."""
    battery = _lib("phone_battery")
    assert battery["uses"] == 24
    assert "power" not in battery
    assert "charge" not in battery


def test_the_device_body_carries_no_charge_of_its_own():
    """``uses: -1`` on the phone — the body is permanent, the cell is not."""
    assert _lib("phone")["uses"] == -1


def test_no_library_item_invents_a_device_charge_field():
    for path in LIB.glob("*.json"):
        entry = json.loads(path.read_text(encoding="utf-8-sig"))
        assert "power" not in entry, f"{path.name} adds a `power` field"
        assert "charge_level" not in entry, f"{path.name} adds a `charge_level` field"


# ── a part cannot be moved, by any verb (criterion 1) ───────────────────────

def test_a_part_cannot_be_taken():
    w = _world()
    _phone, battery = _phone_with_battery(w)
    try:
        w.take_item("phone battery")
    except ValueError as exc:
        assert "battery" in str(exc)
    else:
        raise AssertionError("a part must not be takeable")


def test_a_part_cannot_be_dropped():
    w = _world()
    _phone, battery = _phone_with_battery(w)
    _carry(w, battery)
    try:
        w.drop_item("phone battery")
    except ValueError as exc:
        assert "battery" in str(exc)
    else:
        raise AssertionError("a part must not be droppable")
    assert w.graph.get_node(battery.id) is not None
    assert any(e.source == battery.id for e in w.graph.get_edges_for_target(
        w.player_manager.get_player_node_id(w.player_manager.active_player),
        (EDGE_CARRYING, EDGE_EQUIPPED)))


def _miki(w, phone):
    from player import Player
    miki = Player("miki doki")
    miki.current_area = AREA
    miki_id = w.player_manager.get_player_node_id("miki doki")
    if phone is not None:
        w.graph.add_edge(Edge(source=phone.id, target=miki_id, type=EDGE_CARRYING))
    return miki


def test_a_part_cannot_be_stolen():
    """The battery is placed straight on miki's carrying edge.

    Nested, `steal` never finds it at all — which is a refusal, but the wrong
    one to rely on: it would silently become stealable the moment anything
    widened the roster scan. Placed on the edge, the action list is the only
    thing standing in the way, which is what is being tested.
    """
    w = _world()
    _phone, battery = _phone_with_battery(w)
    miki = _miki(w, None)
    w.player_manager.players["miki doki"] = miki
    miki_id = w.player_manager.get_player_node_id("miki doki")
    w.graph.add_edge(Edge(source=battery.id, target=miki_id, type=EDGE_CARRYING))

    try:
        w.steal_item("phone battery", "miki doki")
    except ValueError as exc:
        assert "battery" in str(exc)
    else:
        raise AssertionError("a part must not be stealable")
    assert any(e.source == battery.id and e.target == miki_id
               for e in w.graph.get_edges_for_target(miki_id, EDGE_CARRYING))


def test_a_part_cannot_be_handed_over():
    w = _world()
    _phone, battery = _phone_with_battery(w)
    w.player_manager.players["miki doki"] = _miki(w, None)
    w.name_matcher._set_player_area("miki doki", AREA)
    try:
        w.give_item("phone battery", "miki doki")
    except ValueError as exc:
        assert "battery" in str(exc)
    else:
        raise AssertionError("a part must not be handed over")


def test_a_part_cannot_be_put_away():
    w = _world()
    key = _place(w, "iron_key")
    _phone, battery = _phone_with_battery(w)
    box = _place(w, "drawer")
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    w.graph.add_edge(Edge(source=battery.id, target=player_id, type=EDGE_CARRYING))
    w.graph.add_edge(Edge(source=box.id, target=player_id, type=EDGE_CARRYING))
    for verb in (lambda: w.put_item_in_container("phone battery", "drawer"),
                 lambda: w.place_item("phone battery", "drawer", EDGE_IN)):
        try:
            verb()
        except ValueError as exc:
            assert "battery" in str(exc)
        else:
            raise AssertionError("a part must not be put away")
    assert not any(e.source == battery.id and e.target == box.id for e in w.graph.edges)
    assert key is not None


def test_an_ordinary_item_is_still_put_and_taken():
    """The gates must not have been bought at the price of normal verbs.

    Exercises put → take as its own path; the take → drop counterpart (the
    bug-509 shape, where `take` lands an item in a hand/`equipped` edge) is
    covered directly in `tests/test_item_actions.py::TestDropItem`.
    """
    w = _world()
    key = _place(w, "iron_key")
    bag = _place(w, "satchel")
    box = _place(w, "drawer")
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    w.graph.add_edge(Edge(source=key.id, target=player_id, type=EDGE_CARRYING))
    w.graph.add_edge(Edge(source=box.id, target=player_id, type=EDGE_CARRYING))

    w.put_item_in_container("iron key", "drawer")
    assert any(e.source == key.id and e.target == box.id and e.type == EDGE_IN
               for e in w.graph.edges)

    w.take_item("iron key")
    assert any(e.source == key.id and e.target == player_id
               for e in w.graph.get_edges_for_target(player_id, (EDGE_CARRYING, EDGE_EQUIPPED)))
    assert bag is not None


# ── a part is still reachable and usable (criterion 1, second half) ──────────

def test_a_part_inside_a_carried_device_is_reachable():
    """Non-portable and reachable are not opposites. This is the whole reason
    `item_reach` walks any depth instead of stopping at the device."""
    from engine.item_reach import find_reachable, reachable_items

    w = _world()
    phone, battery = _phone_with_battery(w)
    _carry(w, phone)

    found = find_reachable(w.graph, w.name_matcher, w, "phone battery")
    assert found is not None and found.id == battery.id
    assert battery.id in [n.id for n in reachable_items(w.graph, w)]


def test_a_part_is_usable():
    w = _world()
    phone, battery = _phone_with_battery(w)
    _carry(w, phone)
    before = battery.properties["uses"]
    w.use_item("phone battery")
    assert battery.properties["uses"] == before - 1


# ── depletion: an explicit semantic, never a silent detach (criterion 3) ─────

def test_a_depleted_part_does_not_detach_from_its_device():
    w = _world()
    phone, battery = _phone_with_battery(w)
    _carry(w, phone)
    battery.properties["uses"] = 1

    w.use_item("phone battery")
    assert w.graph.get_node(battery.id) is not None, "the part must stay in the phone"
    assert any(e.source == battery.id and e.target == phone.id and e.type == EDGE_IN
               for e in w.graph.edges), "the part's place in the device must survive"
    assert battery.properties["uses"] == 0


def test_a_depleted_part_goes_unlit():
    w = _world()
    phone, battery = _phone_with_battery(w)
    _carry(w, phone)
    battery.properties["uses"] = 1
    w.use_item("phone battery")
    assert battery.properties["current_state"] == "unlit"


def test_a_depleted_part_fires_on_depleted():
    w = _world()
    phone, battery = _phone_with_battery(w)
    _carry(w, phone)
    battery.properties["uses"] = 1

    fired = []

    class _Triggers:
        def _execute_triggers(self, node, trigger_type, **kwargs):
            fired.append((node.id, trigger_type))
            return []

    # ItemActions captured the trigger system at construction, so the stub
    # goes there rather than on the world.
    w.item_actions.trigger_system = _Triggers()
    w.use_item("phone battery")
    assert (battery.id, "on_depleted") in fired


def test_an_ordinary_used_up_item_still_leaves_the_scene():
    """The pre-existing semantic is unchanged: a spent throwaway is cut loose,
    not parked in an 'unlit' state where the next person trips over it."""
    w = _world()
    w.item_actions.trigger_system = _NoTriggers()
    thing = _place(w, "iron_key")
    thing.properties["uses"] = 1
    w.graph.add_edge(Edge(
        source=thing.id,
        target=w.player_manager.get_player_node_id(w.player_manager.active_player),
        type=EDGE_CARRYING))
    w.use_item("iron key")
    assert not any(e.source == thing.id and e.type == EDGE_IN for e in w.graph.edges)


class _NoTriggers:
    def _execute_triggers(self, node, trigger_type, **kwargs):
        return []

    def _get_available_actions(self, node):
        return []

    def _contextual_failure(self, verb, name, available):
        return f"You can't {verb} the {name}."


# ── the worked example is really authored (criterion 5) ──────────────────────

def test_the_phone_authors_its_battery():
    assert "phone_battery" in (_lib("phone").get("contents") or [])


def test_the_battery_names_no_take_or_drop():
    actions = _lib("phone_battery").get("actions")
    assert "take" not in actions
    assert "drop" not in actions


def test_the_battery_still_declares_what_it_does_do():
    """Not takeable is not inert — a part states its own verbs, as the project
    rule is that an item declares its valid actions."""
    actions = _lib("phone_battery").get("actions")
    assert "examine" in actions
    assert "use" in actions


def test_the_battery_is_a_tagged_part():
    assert "part" in _lib("phone_battery").get("tags", [])


def test_the_worked_example_survives_a_round_trip():
    from virtual_world_engine import VirtualWorld

    w = _world()
    phone, battery = _phone_with_battery(w)
    data = w.to_scenario_dict()

    w2 = VirtualWorld()
    w2.load_from_dict(data)
    restored = w2.graph.get_node(battery.id)
    assert restored is not None
    assert restored.properties["uses"] == _lib("phone_battery")["uses"]
    assert parent_of(w2.graph, restored) is not None
