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
