"""Company-aware Social need (task: decay must care about company).

Being alone drains Social FASTER than baseline; company feeds it. The
`social_gain` trait effect (extrovert: 2, introvert: 0) scales both
directions. Built on a VirtualWorld() plus a real area node so the whole
per-tick environment block runs.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player

AREA = "Blizzard Forest Clearing"


def _world():
    from app import create_app
    app = create_app({"TESTING": True})
    return app.world


def _place(world, name, area=AREA):
    """Get (or create) a player and put them in ``area``."""
    if name in world.player_manager.players:
        p = world.player_manager.players[name]
    else:
        p = Player(name)
        world.add_player(p)
    p.current_area = area
    world.set_player_area(name, area)
    return p


def _decay_one_tick(world):
    world.tick_turn()


def test_alone_social_decays_faster_than_baseline():
    world = _world()
    p1 = _place(world, "Kaelen Voss")
    # Make sure nobody else is in the area for this test.
    for other in world.player_manager.players.values():
        if other is not p1 and other.current_area == AREA:
            other.current_area = "Kitchen"
            world.set_player_area(other.name, "Kitchen")
    p1.vitals["Social"] = 50
    _decay_one_tick(world)
    # baseline -1 (Social is a resource) + alone -1 = -2 net.
    assert p1.vitals["Social"] == 48


def test_company_social_is_fed_every_tick():
    world = _world()
    p1 = _place(world, "Kaelen Voss")
    p2 = _place(world, "Other", AREA)
    p1.vitals["Social"] = 50
    p2.vitals["Social"] = 50
    _decay_one_tick(world)
    # baseline -1 + company +1 = net 0 for both.
    assert p1.vitals["Social"] == 50
    assert p2.vitals["Social"] == 50


def test_extrovert_alone_craves_company_more():
    world = _world()
    p1 = _place(world, "Kaelen Voss")
    p1.traits["extrovert"] = True
    for other in world.player_manager.players.values():
        if other is not p1 and other.current_area == AREA:
            other.current_area = "Kitchen"
            world.set_player_area(other.name, "Kitchen")
    p1.vitals["Social"] = 50
    _decay_one_tick(world)
    # baseline -1 + alone penalty -2 (social_gain=2) = -3 net.
    assert p1.vitals["Social"] == 47


def test_extrovert_company_gains_extra():
    world = _world()
    p1 = _place(world, "Kaelen Voss")
    p2 = _place(world, "Other", AREA)
    p1.traits["extrovert"] = True
    p1.vitals["Social"] = 50
    _decay_one_tick(world)
    # baseline -1 + company +2 = +1 net.
    assert p1.vitals["Social"] == 51


def test_introvert_alone_keeps_only_baseline():
    world = _world()
    p1 = _place(world, "Kaelen Voss")
    p1.traits["introvert"] = True
    for other in world.player_manager.players.values():
        if other is not p1 and other.current_area == AREA:
            other.current_area = "Kitchen"
            world.set_player_area(other.name, "Kitchen")
    p1.vitals["Social"] = 50
    _decay_one_tick(world)
    # baseline -1 only; social_gain=0 means no company bonus AND no alone penalty.
    assert p1.vitals["Social"] == 49


def test_alone_log_line_reports_cause_for_active_player():
    world = _world()
    p1 = _place(world, "Kaelen Voss")
    world.set_active_player("Kaelen Voss")
    for other in world.player_manager.players.values():
        if other is not p1 and other.current_area == AREA:
            other.current_area = "Kitchen"
            world.set_player_area(other.name, "Kitchen")
    p1.vitals["Social"] = 50
    _decay_one_tick(world)
    log_blob = "\n".join(world.game_logger.game_log)
    assert "Social -1" in log_blob
    assert "alone in Blizzard Forest Clearing" in log_blob
