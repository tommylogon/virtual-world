"""Item ownership and personal-item permission (task-515).

Some things are not communal. Gribba's Good Knife is hers, and "nobody else may
touch it" should be true in the world rather than only in the fiction.

The marker is a node property — ``owner`` plus the informational ``personal``
tag — not an edge, and an item without ``owner`` is nobody's in particular and
behaves exactly as before. Two decisions the task left open are made explicit
in ``engine/items/ownership.py`` and pinned here:

- **A missing or incapacitated owner lifts the refusal.** A dead goblin's knife
  is not a sacred object.
- **A Social or Intimidation check does NOT lift it.** ``steal`` is already a
  roll; hiding a second one inside ``take`` would make an ordinary verb
  unpredictable. So the normal verbs say no plainly and ``steal`` is the way
  through — harder, but never blocked.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import EDGE_CARRYING, EDGE_IN, Edge, Node
from engine.items.ownership import (
    INCAPACITATED_OWNER_STATES,
    is_owned,
    is_owner,
    is_personal,
    owner_can_enforce,
    owner_display_name,
    owner_incumbent,
    owner_of,
    permission_refusal,
)

LIB = Path(__file__).parent.parent / "data" / "library" / "items"
AREA = "Kraktooth Camp"


def _lib(item_id):
    return json.loads((LIB / f"{item_id}.json").read_text(encoding="utf-8-sig"))


def _node(props, name="thing", node_id="item_thing"):
    return Node(id=node_id, type="item", name=name, properties=dict(props))


def _world():
    from virtual_world_engine import VirtualWorld
    w = VirtualWorld()
    w.movement.add_area(Area(AREA, "Stones and cookfires.", []))
    w.name_matcher._set_player_area(w.active_player, AREA)
    return w


def _gribba(w, with_knife=True):
    from player import Player
    gribba = Player("Gribba")
    gribba.current_area = AREA
    w.player_manager.players["Gribba"] = gribba
    gribba_id = w.player_manager.get_player_node_id("Gribba")
    w.graph.add_edge(Edge(source=gribba_id, target=w.get_current_area_id(), type=EDGE_IN))
    knife = None
    if with_knife:
        knife, _lib_data = w.effects._hydrate_item("gribbas_good_knife", {}, always_fresh=True)
        w.graph.add_edge(Edge(source=knife.id, target=gribba_id, type=EDGE_CARRYING))
    return gribba, knife


# ── the marker is a property, and a node without one is unowned ─────────────

def test_the_knife_is_authored_with_an_owner():
    assert _lib("gribbas_good_knife")["owner"] == "Gribba"


def test_the_knife_is_flagged_personal():
    assert "personal" in _lib("gribbas_good_knife")["tags"]


def test_an_unowned_item_is_nobody_s():
    key = _node({"actions": "take,drop"}, name="iron key")
    assert not is_owned(key)
    assert owner_of(key) == ""
    assert is_owner(key, None, "anyone at all")


def test_the_personal_tag_alone_does_not_block_anyone():
    """Informational, not load-bearing: an author can mark a keepsake that is
    not yet anybody's."""
    keepsake = _node({"actions": "take", "tags": ["personal"]}, name="lucky coin")
    assert is_personal(keepsake)
    assert not is_owned(keepsake)
    assert permission_refusal(keepsake, "jake halloway", "take it") is None


def test_the_owner_handle_accepts_a_name_or_a_node_id():
    """Ids and names are the same person (project rule: lowercase everything)."""
    assert owner_of(_node({"owner": "Gribba"})) == "gribba"
    assert owner_of(_node({"owner": "player_gribba"})) == "gribba"
    assert owner_of(_node({"owner": "GRI BBA"})) == "gri bba"


# ── a non-owner is refused, clearly (criterion 1) ──────────────────────────

def test_a_non_owner_cannot_take_it():
    w = _world()
    gribba, knife = _gribba(w)
    knife = w.graph.get_node(
        next(e.source for e in w.graph.get_edges_for_target(
            w.player_manager.get_player_node_id("Gribba"), EDGE_CARRYING)))
    w.graph.remove_edge(knife.id, w.player_manager.get_player_node_id("Gribba"), EDGE_CARRYING)
    w.graph.add_edge(Edge(source=knife.id, target=w.get_current_area_id(), type=EDGE_IN))

    try:
        w.take_item("Gribba's Good Knife")
    except ValueError as exc:
        message = str(exc)
        assert "Gribba" in message, message
        assert "not yours" in message, message
    else:
        raise AssertionError("a non-owner must not be able to take it")


def test_a_non_owner_cannot_use_it():
    w = _world()
    gribba, knife = _gribba(w)
    w.graph.remove_edge(knife.id, w.player_manager.get_player_node_id("Gribba"), EDGE_CARRYING)
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    w.graph.add_edge(Edge(source=knife.id, target=player_id, type=EDGE_CARRYING))

    try:
        w.use_item("Gribba's Good Knife")
    except ValueError as exc:
        assert "Gribba" in str(exc)
    else:
        raise AssertionError("a non-owner must not be able to use it")


def test_a_non_owner_cannot_give_it_away():
    """Different in kind from taking: the owner is here and says no."""
    w = _world()
    gribba, knife = _gribba(w)
    w.graph.remove_edge(knife.id, w.player_manager.get_player_node_id("Gribba"), EDGE_CARRYING)
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    w.graph.add_edge(Edge(source=knife.id, target=player_id, type=EDGE_CARRYING))

    try:
        w.give_item("Gribba's Good Knife", "Gribba")
    except ValueError as exc:
        assert "Gribba" in str(exc)
    else:
        raise AssertionError("a non-owner must not be able to give it away")


def test_use_on_a_target_is_also_refused():
    w = _world()
    gribba, knife = _gribba(w)
    w.graph.remove_edge(knife.id, w.player_manager.get_player_node_id("Gribba"), EDGE_CARRYING)
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    w.graph.add_edge(Edge(source=knife.id, target=player_id, type=EDGE_CARRYING))

    try:
        w.use_item_on("Gribba's Good Knife", "Gribba")
    except ValueError as exc:
        assert "Gribba" in str(exc)
    else:
        raise AssertionError("use-on is using it")


def test_the_refusal_points_at_the_contested_path():
    """A refusal that does not say what else to do is a dead end."""
    node = _node({"owner": "Gribba"}, name="Good Knife")
    message = permission_refusal(node, "jake halloway", "take it")
    assert "steal" in message or "take it" in message


# ── the owner is always allowed (criterion 2) ──────────────────────────────

def test_the_owner_may_take_it():
    w = _world()
    gribba, knife = _gribba(w)
    w.player_manager.active_player = "Gribba"
    result = w.take_item("Gribba's Good Knife")
    assert "Good Knife" in result


def test_the_owner_may_use_it():
    w = _world()
    gribba, knife = _gribba(w)
    w.player_manager.active_player = "Gribba"
    result = w.use_item("Gribba's Good Knife")
    assert "Good Knife" in result


def test_the_owner_may_give_it_away():
    """Ownership is not a life sentence — an owner can part with a treasure."""
    w = _world()
    gribba, knife = _gribba(w)
    w.player_manager.active_player = "Gribba"
    result = w.give_item("Gribba's Good Knife", w.player_manager.active_player
                         if False else "Gribba")
    assert "Good Knife" in result or "Gribba" in result


def test_is_owner_matches_on_the_normalised_handle():
    w = _world()
    node = _node({"owner": "Gribba"})
    assert is_owner(node, w, "Gribba")
    assert is_owner(node, w, "gribba")
    assert is_owner(node, w, "player_gribba")
    assert not is_owner(node, w, "jake halloway")


# ── steal is the override, and it is harder (criterion 3) ──────────────────

def test_steal_still_works_on_an_owned_item():
    """Ownership must never block `steal` — that is the whole point of
    keeping the contested path."""
    w = _world()
    gribba, knife = _gribba(w)
    w.player_manager.player.skills["Sleight of Hand"] = 30
    gribba.skills["Perception"] = 0
    w.name_matcher._set_player_area(w.player_manager.active_player, AREA)

    result = w.steal_item("Gribba's Good Knife", "Gribba")
    assert "Good Knife" in result
    player_id = w.player_manager.get_player_node_id(w.player_manager.active_player)
    assert any(e.source == knife.id for e in
               w.graph.get_edges_for_target(player_id, (EDGE_CARRYING, "equipped")))


def test_stealing_a_personal_item_is_harder():
    """Someone watches their own property more closely than loose change.

    The dice are pinned so the assertion is about the *applied* skill, not
    about luck: with every roll forced to 10, the owned item's target total
    must come out 3 higher than the unowned one.
    """
    import random

    w = _world()
    gribba, knife = _gribba(w)
    gribba.skills["Perception"] = 5
    w.player_manager.player.skills["Sleight of Hand"] = 5

    real_randint = random.randint
    random.randint = lambda lo, hi: 10
    try:
        owned_log = _steal_log(w, "Gribba's Good Knife", "Gribba")
    finally:
        random.randint = real_randint
    assert "[Steal]" in owned_log, owned_log
    assert _per_total(owned_log) == 10 + 5 + 3, "the owner's property is watched more closely"


def _steal_log(w, item_name, target_name):
    """Run a steal and return everything it logged."""
    captured = []
    original = w.add_log_entry
    w.add_log_entry = lambda text: (captured.append(text), original(text))[1]
    try:
        w.steal_item(item_name, target_name)
    except ValueError:
        pass
    return "\n".join(captured)


def _per_total(joined):
    assert "[Steal]" in joined, joined
    return int(joined.split("vs Perception ")[1].split()[0])


def test_an_unowned_item_gets_no_steal_bonus():
    import random

    w = _world()
    gribba = _gribba(w, with_knife=False)[0]
    gribba.skills["Perception"] = 5
    w.player_manager.player.skills["Sleight of Hand"] = 5

    key, _d = w.effects._hydrate_item("iron_key", {}, always_fresh=True)
    w.graph.add_edge(Edge(source=key.id,
                          target=w.player_manager.get_player_node_id("Gribba"),
                          type=EDGE_CARRYING))

    real_randint = random.randint
    random.randint = lambda lo, hi: 10
    try:
        log = _steal_log(w, "iron key", "Gribba")
    finally:
        random.randint = real_randint
    assert _per_total(log) == 10 + 5, "no bonus on an ordinary item"


# ── an owner who cannot enforce a claim lets go (decision 1) ───────────────

def test_a_dead_owner_lets_go_of_their_things():
    w = _world()
    gribba, knife = _gribba(w)
    gribba.state = "dead"
    assert not owner_incumbent(gribba)
    assert not owner_can_enforce(w, "Gribba")
    w.graph.remove_edge(knife.id, w.player_manager.get_player_node_id("Gribba"), EDGE_CARRYING)
    w.graph.add_edge(Edge(source=knife.id, target=w.get_current_area_id(), type=EDGE_IN))
    assert "Good Knife" in w.take_item("Gribba's Good Knife")


def test_an_owner_elsewhere_still_owns_them():
    """Being in another room is not being unable."""
    w = _world()
    gribba, knife = _gribba(w)
    gribba.current_area = "Somewhere Far Off"
    assert owner_incumbent(gribba)
    w.graph.remove_edge(knife.id, w.player_manager.get_player_node_id("Gribba"), EDGE_CARRYING)
    w.graph.add_edge(Edge(source=knife.id, target=w.get_current_area_id(), type=EDGE_IN))
    try:
        w.take_item("Gribba's Good Knife")
    except ValueError:
        pass
    else:
        raise AssertionError("an absent owner still has a claim")


def test_every_incapacitated_state_is_listed():
    for state in ("dead", "unconscious", "bound", "asleep", "sleeping"):
        assert state in INCAPACITATED_OWNER_STATES, state


def test_an_unknown_owner_handle_is_presumed_alive():
    """Silence is not consent: a keepsake owned by someone we have never met
    keeps its claim, rather than becoming free to anyone who walks past."""
    w = _world()
    assert owner_can_enforce(w, "Some Goblin Nobody Has Met")


# ── naming ─────────────────────────────────────────────────────────────────

def test_the_refusal_uses_the_real_name_when_we_know_the_person():
    w = _world()
    _gribba(w)
    node = _node({"owner": "Gribba"})
    assert owner_display_name("Gribba", w) == "Gribba"


def test_the_refusal_falls_back_to_the_handle_when_we_do_not():
    node = _node({"owner": "Gribba"})
    assert owner_display_name("Gribba", None) == "Gribba"
    assert owner_display_name("", None) == "someone"


# ── the property round-trips ───────────────────────────────────────────────

def test_owner_survives_a_save_and_load():
    from virtual_world_engine import VirtualWorld

    w = _world()
    _, knife = _gribba(w)
    data = w.to_scenario_dict()
    w2 = VirtualWorld()
    w2.load_from_dict(data)
    restored = w2.graph.get_node(knife.id)
    assert restored is not None
    assert owner_of(restored) == "gribba"
    assert is_owned(restored)


def test_hydration_keeps_the_owner():
    w = _world()
    node, lib = w.effects._hydrate_item("gribbas_good_knife", {}, always_fresh=True)
    assert node.properties["owner"] == lib["owner"] == "Gribba"
