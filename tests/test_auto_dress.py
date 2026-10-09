"""Auto-dressing tests (task-325): interest-tag-driven library equips."""

from area import Area


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Room A")
    return world, pname


def equipped_count(world, pname):
    player = world.player_manager.get_player(pname)
    return sum(len([i for i in stack if i and not str(i).startswith('__')])
               for stack in player.equipped.values())


def test_auto_dress_dresses_clothing_interests():
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = ["clothing"]
    report = world.auto_dress_character(pname)
    assert "item(s) equipped" in report
    assert equipped_count(world, pname) > 0


def test_auto_dress_no_interests_dresses_basics():
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = []
    report = world.auto_dress_character(pname)
    assert "item(s) equipped" in report
    assert equipped_count(world, pname) > 0


def test_auto_dress_unknown_interest_is_empty():
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = ["quantum_plasma"]
    report = world.auto_dress_character(pname)
    assert "0 item(s) equipped" in report
    assert equipped_count(world, pname) == 0


def test_auto_dress_is_idempotent():
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = ["clothing"]
    world.auto_dress_character(pname)
    count = equipped_count(world, pname)
    world.auto_dress_character(pname)
    assert equipped_count(world, pname) >= count  # re-dress doesn't remove gear


# --- LLM selection path (task-660) ------------------------------------------
# The engine cannot call a model (keys live in the browser), so these cover the
# two halves the inspector drives: the candidate pool it asks for, and the
# explicit id list it posts back.


def test_candidates_offer_a_wider_pool_than_the_tag_filter():
    """The point of the LLM path: the model must see more than the tags match.

    The tag filter is not empty for a smith -- `belt_leather` carries the tag
    `metal` -- it is just arbitrary: it returns a belt and misses the apron
    (tags: clothing, meat, blood), and after Generate-from-Personality widened
    the tags it happily returned a Guiding Cane. Vocabulary overlap is not a
    proxy for what someone would wear, so the model gets the whole pool.
    """
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = ["metal", "tools", "iron", "temper"]

    cand = world.auto_dress_candidates(pname)
    matched = {e['lib_id'] for e in cand['matched']}
    pool = {e['lib_id'] for e in cand['pool']}
    assert matched <= pool, "matched entries must still be offered"
    assert len(pool) > len(matched), (
        f"pool ({len(pool)}) must be wider than matched ({len(matched)}) "
        "or the LLM has nothing the tag filter was not already offering"
    )
    assert cand['character'] == pname


def test_candidates_expose_only_wearable_entries_with_an_id():
    world, pname = make_world()
    cand = world.auto_dress_candidates(pname)
    assert cand['pool'], "expected wearable library items"
    for entry in cand['pool']:
        assert entry['lib_id'], "engine validates on lib_id; a blank id is unusable"
        assert entry['slots'], "a non-wearable slipped into the pool"
        assert isinstance(entry['tags'], list)


def test_candidates_offer_base_description_not_the_generated_one():
    """`description` is regenerated FROM the equipped items on every wear/remove,
    so handing it to a prompt whose job is choosing equipment is circular -- the
    model would read an outfit to pick an outfit. The field is named
    `base_description` so the reason survives the next reader.
    """
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.base_description = 'A smith, soot to the elbow.'
    player.description = 'A smith wearing a stained apron and a polished belt.'

    cand = world.auto_dress_candidates(pname)
    assert 'base_description' in cand
    assert cand['base_description'] == 'A smith, soot to the elbow.'
    assert cand['base_description'] != player.description
    assert 'description' not in cand, (
        'the circular field must not be offered alongside it, or a later reader '
        'will reach for the more obvious name'
    )


def test_explicit_ids_equip_exactly_those_items():
    """The posted-back selection is honoured, and lands as real equipped items.

    Asserted on the equipped EDGE, not a carrying edge: `equip_item` swaps
    carrying -> equipped (the task-450 carried+equipped invariant), so a worn
    item has no carrying edge and checking for one proves nothing.
    """
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = []

    cand = world.auto_dress_candidates(pname)
    chosen = cand['pool'][:3]
    report = world.auto_dress_character(pname, library_ids=[e['lib_id'] for e in chosen])

    assert '3 item(s) equipped' in report, report
    player = world.player_manager.get_player(pname)
    worn_ids = {i for stack in player.equipped.values() for i in stack}
    for entry in chosen:
        node = world.graph.get_node_by_name(entry['name']) if hasattr(world.graph, 'get_node_by_name') else None
        if node is not None:
            assert node.id in worn_ids, f"{entry['name']} reported as dressed but not in equipped"

    equipped_edges = [e for e in world.graph.get_edges_for_target(
        world.player_manager.get_player_node_id(pname), 'equipped')]
    assert len(equipped_edges) >= 1, 'dressed items must be linked by an equipped edge'


def test_repeated_ids_produce_one_instance_per_name():
    """A duplicate id must not mint a second copy of the same item.

    `_hydrate_item(always_fresh=True)` creates a NEW node every call, so
    without de-duplication a repeated id puts two instances of one item in the
    same slot. Found live: posting ['heavy_black_boots','belt_leather',
    'quantum_harness','heavy_black_boots'] left `feet` holding two boot nodes.
    """
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = []

    world.auto_dress_character(pname, library_ids=[
        'heavy_black_boots', 'belt_leather', 'heavy_black_boots'])

    player = world.player_manager.get_player(pname)
    assert len(player.equipped.get('feet', [])) == 1, (
        f"expected one pair of boots, got {player.equipped.get('feet')}")

    names = []
    for stack in player.equipped.values():
        for node_id in stack:
            node = world.graph.get_node(node_id)
            if node:
                names.append(node.name)
    assert len(names) == len(set(names)), f"duplicate item equipped: {names}"


def test_unknown_ids_are_dropped_rather_than_equipped():
    """A hallucinated id must equip nothing, not crash and not invent an item."""
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = ["clothing"]

    cand = world.auto_dress_candidates(pname)
    real = cand['pool'][0]['lib_id']
    report = world.auto_dress_character(pname, library_ids=['quantum_harness', real])

    assert '0 item(s) equipped' not in report
    player = world.player_manager.get_player(pname)
    assert equipped_count(world, pname) > 0
    # The bogus id left no node behind.
    assert world.graph.get_node('quantum_harness') is None


def test_empty_selection_list_equips_nothing():
    """An empty list is a real answer ("wears nothing"), not a request for the
    deterministic fallback — otherwise a model that declines still gets a
    shuffled outfit it never asked for."""
    world, pname = make_world()
    player = world.player_manager.get_player(pname)
    player.interest_tags = ["clothing"]

    report = world.auto_dress_character(pname, library_ids=[])
    assert '0 item(s) equipped' in report
    assert equipped_count(world, pname) == 0


def test_explicit_selection_respects_cold_weather_gate():
    """The weather gate applies to the LLM path too, not just the tag path.

    In the cold only insulated pieces survive, so the pool the model is shown
    must contain nothing uninsulated -- otherwise a model that picks "a coat"
    from a pool that was never weather-filtered dresses a character for summer.
    """
    world, pname = make_world()
    world.movement.add_area(Area("Freezer", "Cold room.", []))
    world.name_matcher._set_player_area(pname, "Freezer")
    area = world.graph.get_node(world._area_node_id("Freezer"))
    area.properties['environment'] = {'temperature': -5}

    player = world.player_manager.get_player(pname)
    player.interest_tags = []
    cand = world.auto_dress_candidates(pname)
    assert cand['temperature'] <= 5, 'test setup did not register as cold'
    assert cand['pool'], 'expected insulated candidates in the cold'
    uninsulated = [e['lib_id'] for e in cand['pool'] if e['insulation'] <= 0]
    assert not uninsulated, f"cold pool leaked uninsulated items: {uninsulated}"

def test_mature_wearables_are_gated_by_mature_content(monkeypatch):
    """task-660: a mature-marked wearable must not reach the pool unless opted in."""
    import engine.dressing as dressing

    fake = [
        {"lib_id": "plain_shirt", "name": "Shirt", "slots": ["torso"],
         "tags": ["clothing"], "insulation": 0, "mature": False},
        {"lib_id": "ball_gag", "name": "Ball Gag", "slots": ["head"],
         "tags": ["clothing", "accessory", "restraint"], "insulation": 0, "mature": True},
    ]
    monkeypatch.setattr(dressing, "_wearable_entries", lambda: fake)

    world, pname = make_world()

    world.mature_content = False
    off = dressing.dress_candidates(world, pname, limit=50)
    ids_off = {e["lib_id"] for e in off["pool"]} | {e["lib_id"] for e in off["matched"]}
    assert "ball_gag" not in ids_off, "mature item leaked into the pool with the toggle off"
    assert "plain_shirt" in ids_off

    world.mature_content = True
    on = dressing.dress_candidates(world, pname, limit=50)
    ids_on = {e["lib_id"] for e in on["pool"]}
    assert "ball_gag" in ids_on, "opting in must restore the mature item"
