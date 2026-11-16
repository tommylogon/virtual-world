"""Tests for timeskip follow-ups (task-482).

1. Vendor leisure buying.
2. Explore frontier preference.
"""

from graph import Node, Edge, EDGE_IN, EDGE_CARRYING
from engine import timeskip


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _hero(w):
    p = w.get_active_player_obj()
    if p is None:
        p = next(iter(w.players.values()))
    for other in w.players.values():
        if other is not p:
            other.autonomy = True
    return p


def _safe(p):
    p.vitals.update({
        "HP": 100, "Thirst": 0, "Hunger": 0, "Bladder": 0,
        "Energy": 100, "Hygiene": 100, "Sanity": 100,
        "Social": 100, "Entertainment": 100,
    })
    p.conditions.clear()
    p.state = "idle"
    return p


def test_vendor_leisure_buying_from_merchant_character():
    w = _world()
    hero = _safe(_hero(w))
    area_name = hero.current_area
    area_id = w.area_node_id(area_name)
    hero_id = w._player_node_id(hero.name)

    # Add a merchant character in the same area
    from player import Player
    merchant = Player(name="Bob The Trader")
    merchant.role = "merchant"
    merchant.current_area = area_name
    merchant_id = w._player_node_id("Bob The Trader")
    w.players["Bob The Trader"] = merchant
    m_node = Node(id=merchant_id, type="character", name="Bob The Trader",
                  properties={"name": "Bob The Trader", "role": "merchant", "tags": ["merchant"]})
    w.graph.add_node(m_node)

    # Merchant carries a valid item
    scarf = Node(id="item_silk_scarf", type="item", name="silk scarf",
                 properties={"name": "silk scarf", "tags": ["clothing", "luxury"], "weight": 0.5})
    w.graph.add_node(scarf)
    w.graph.add_edge(Edge(source=scarf.id, target=merchant_id, type=EDGE_CARRYING))

    # Hero carries a coin
    coin = Node(id="item_gold_coin_hero", type="item", name="gold coin",
                properties={"name": "gold coin", "tags": ["coin", "currency"], "weight": 0.1})
    w.graph.add_node(coin)
    w.graph.add_edge(Edge(source=coin.id, target=hero_id, type=EDGE_CARRYING))

    # Timeskip with leisure intent
    res = timeskip.advance(w, 10, intent="leisure")

    assert res.ok
    assert res.elapsed_minutes >= 1

    # Item is now carried by hero
    hero_carried = [e.source for e in w.graph.get_edges_for_target(hero_id, EDGE_CARRYING)]
    assert scarf.id in hero_carried, "hero did not acquire the purchased item"

    # Coin was paid to merchant
    merchant_carried = [e.source for e in w.graph.get_edges_for_target(merchant_id, EDGE_CARRYING)]
    assert coin.id in merchant_carried, "merchant did not receive the coin payment"

    # Timeskip summary lines name the purchase
    summary_text = " ".join(res.lines)
    assert "bought silk scarf from Bob The Trader" in summary_text

    # Game log contains entry
    log_text = " ".join(w.game_log)
    assert f"[{hero.name}] bought silk scarf from Bob The Trader" in log_text


def test_vendor_leisure_buying_from_shop_area():
    w = _world()
    hero = _safe(_hero(w))
    area_name = hero.current_area
    area_id = w.area_node_id(area_name)
    hero_id = w._player_node_id(hero.name)

    # Tag the current area as a shop
    area_node = w.graph.get_node(area_id)
    area_node.properties["tags"] = ["shop", "commercial"]

    # Add an item in the shop
    apple = Node(id="item_candied_apple", type="item", name="candied apple",
                 properties={"name": "candied apple", "tags": ["food", "sweet"], "weight": 0.2})
    w.graph.add_node(apple)
    w.graph.add_edge(Edge(source=apple.id, target=area_id, type=EDGE_IN))

    res = timeskip.advance(w, 10, intent="leisure")
    assert res.ok

    hero_carried = [e.source for e in w.graph.get_edges_for_target(hero_id, EDGE_CARRYING)]
    assert apple.id in hero_carried, "hero did not purchase item from shop area"


def test_explore_prefers_generation_frontier():
    w = _world()
    hero = _safe(_hero(w))
    start_area = hero.current_area
    start_id = w.area_node_id(start_area)

    # Set up world scopes with an unmade scope connected as frontier
    frontier_scope_id = "scope_frontier_wilds"
    w.world_scopes = {
        "scope_town": {"id": "scope_town", "state": "materialized"},
        frontier_scope_id: {
            "id": frontier_scope_id,
            "state": "materialized",
        },
    }

    # Area 1: Regular explored area
    area_reg = Node(id="area_regular_lane", type="area", name="Regular Lane",
                    properties={"name": "Regular Lane", "world_scope_id": "scope_town"})
    w.graph.add_node(area_reg)

    # Area 2: Frontier area generated in frontier scope
    area_front = Node(id="area_frontier_outpost", type="area", name="Frontier Outpost",
                      properties={"name": "Frontier Outpost", "world_scope_id": frontier_scope_id,
                                  "generated": True})
    w.graph.add_node(area_front)

    # Connect start_area to Regular Lane (alphabetically first: e.g. "a_door")
    w.connect_areas(start_area, "Regular Lane", "a_path", "back_path")
    # Connect start_area to Frontier Outpost (alphabetically later: e.g. "z_gate")
    w.connect_areas(start_area, "Frontier Outpost", "z_gate", "back_gate")

    # Ensure start area has scope_town
    start_node = w.graph.get_node(start_id)
    start_node.properties["world_scope_id"] = "scope_town"

    # Explore step should PREFER Frontier Outpost even though a_path is alphabetically earlier
    res = timeskip.advance(w, 5, intent="explore")
    assert res.ok
    assert hero.current_area == "Frontier Outpost", f"Expected Frontier Outpost, got {hero.current_area}"
    assert getattr(hero, "last_explored_destination", None) == "Frontier Outpost"

    # Lived log records frontier exploration
    summary_text = " ".join(res.lines)
    assert "explored into Frontier Outpost on the frontier" in summary_text


def test_explore_when_no_frontier_does_not_invent_one():
    w = _world()
    hero = _safe(_hero(w))
    start_area = hero.current_area

    # No world scopes
    w.world_scopes = {}

    exits = w.build_exits_for_area(start_area)
    if not exits:
        w.connect_areas(start_area, "Side Room", "east", "west")

    res = timeskip.advance(w, 5, intent="explore")
    assert res.ok
    assert hero.current_area != start_area
    assert not hasattr(hero, "last_explored_destination") or hero.last_explored_destination != hero.current_area
