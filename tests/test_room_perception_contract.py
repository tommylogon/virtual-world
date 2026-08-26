"""Contract test: the agent perception path and the panel perception path
must AGREE on what a character can see (task-341).

Two renderers exist by design — area_description.py builds prompt prose
for LLM agents, scene_snapshot.py builds JSON for the human turn composer.
The ONLY allowed difference is presentation. Whenever one path
re-implemented a shared rule it drifted (task-333 crash, bug-23 hidden-way
leak, bug-24 requires:"none" gate, bug-26 empty panel). This test pins
the agreement so drift fails here instead of in a playtest.
"""
from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CONNECTION
from player import Player
from engine.area_description import AreaDescription
from engine.scene_snapshot import build_scene
from engine.room_perception import normalize_requires, resolve_area_node


def build_shared_world():
    """One world exercising every invariant: non-canonical area ids with
    apostrophe names, a hidden (undiscovered) way, a discovered hidden way,
    a requires:"none" way, hidden + visible items, a met friend and an
    unmet stranger."""
    g = WorldGraph()
    # non-canonical ids (apostrophes stripped by the author)
    mens = Node(id="area_tb_mens", type="area", name="TB Men's Restroom",
                properties={"environment": {"light": 90},
                            "description": "one toilet, one sink."})
    dining = Node(id="area_tb_dining", type="area", name="TB Dining Room",
                  properties={"environment": {"light": 90},
                              "description": "booths and tables."})
    g.add_node(mens)
    g.add_node(dining)

    def way(way_id, name, direction, props):
        n = Node(id=way_id, type="way", name=name,
                 properties=dict({"current_state": "closed",
                                  "direction": direction}, **props))
        g.add_node(n)
        return n

    def connect(area_id, w, direction):
        g.add_edge(Edge(source=area_id, target=w.id, type=EDGE_CONNECTION,
                        properties={"direction": direction}))
        g.add_edge(Edge(source=w.id, target="area_tb_dining",
                        type=EDGE_CONNECTION))

    connect("area_tb_mens", way("way_out", "Door", "out", {}), "out")
    connect("area_tb_mens", way("way_secret", "Secret Passage", "down",
                                {"current_state": "hidden"}), "down")
    connect("area_tb_mens", way("way_found", "Found Hatch", "up",
                                {"current_state": "hidden"}), "up")
    connect("area_tb_mens", way("way_none", "Open Arch", "west",
                                {"current_state": "open",
                                 "requires": "none"}), "west")

    toilet = Node(id="item_toilet", type="item", name="Toilet",
                  properties={"description": "porcelain",
                              "current_state": "normal"})
    ring = Node(id="item_ring", type="item", name="Lost Ring",
                properties={"description": "gold", "current_state": "hidden"})
    g.add_node(toilet)
    g.add_node(ring)
    g.add_edge(Edge(source="item_toilet", target="area_tb_mens", type=EDGE_IN))
    g.add_edge(Edge(source="item_ring", target="area_tb_mens", type=EDGE_IN))

    friend = Node(id="player_miki", type="character", name="miki doki",
                  properties={"description": "Anxious. Chews her thumbnail.",
                              "tags": ["female"]})
    g.add_node(friend)
    g.add_edge(Edge(source="player_miki", target="area_tb_mens", type=EDGE_IN))

    jake = Player("jake halloway")
    jake.current_area = "TB Men's Restroom"
    jake.discovered_exits.add(("TB Men's Restroom", "up"))  # found hatch
    jake.relationships["miki doki"] = {"closeness": 10, "interaction_count": 3}

    pm = MagicMock()
    pm.players = {"jake halloway": jake, "miki doki": MagicMock()}
    pm.active_player = "jake halloway"
    pm.current_area = MagicMock()
    pm.current_area.name = "TB Men's Restroom"
    pm.is_slasher = MagicMock(return_value=False)

    return g, pm, jake


def test_agent_and_panel_paths_agree():
    g, pm, jake = build_shared_world()

    lighting = MagicMock()
    lighting.get_ambient_light = MagicMock(return_value=90)
    ad = AreaDescription(g, lighting, pm, item_actions=None)

    world = MagicMock()
    world.graph = g
    world.player_manager = pm
    world.area_node_id = lambda name: f"area_{name.lower().replace(' ', '_')}"
    world.lighting = lighting
    world.area_description = ad
    world._get_available_actions = MagicMock(return_value=[])
    world.name_matcher.way_handle = MagicMock(
        side_effect=lambda way, d, area: d or way.name)

    # ── agent path ──
    agent_items = set(ad.get_area_items())
    agent_exits = ad.build_exits_for_area("TB Men's Restroom")

    # ── panel path ──
    scene = build_scene(world, "jake halloway")
    panel_items = {i["name"] for i in scene["items"]}
    panel_ways = {w["direction"] for w in scene["ways"]}

    # 1. same visible items — hidden ring out, toilet in
    assert agent_items == panel_items == {"Toilet"}

    # 2. same visible ways — undiscovered "down" hidden in BOTH,
    #    discovered "up" visible in BOTH, requires:"none" west visible
    agent_dirs = set(agent_exits.keys())
    assert "down" not in agent_dirs and "down" not in panel_ways
    assert "up" in agent_dirs and "up" in panel_ways
    assert "out" in agent_dirs and "out" in panel_ways
    assert "west" in agent_dirs and "west" in panel_ways
    assert agent_dirs == panel_ways

    # 3. requires:"none" is no gate anywhere — the panel normalizes it;
    #    the agent path never gates on it (movement reads the node via
    #    normalize_requires, pinned by test_normalize_requires)
    west = next(w for w in scene["ways"] if w["direction"] == "west")
    assert west["requires"] == ""


def test_resolve_area_node_handles_noncanonical_ids():
    g, pm, _ = build_shared_world()
    node = resolve_area_node(g, "TB Men's Restroom")
    assert node is not None and node.id == "area_tb_mens"
    # canonical construction also resolves when ids match it
    assert resolve_area_node(g, "TB Dining Room").id == "area_tb_dining"
    assert resolve_area_node(g, "Nowhere At All") is None


def test_normalize_requires():
    assert normalize_requires("none") == ""
    assert normalize_requires("None") == ""
    assert normalize_requires("nothing") == ""
    assert normalize_requires("no") == ""
    assert normalize_requires("") == ""
    assert normalize_requires("crawl") == "crawl"
    assert normalize_requires(None) == ""
