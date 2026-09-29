"""Backsim sleep economics (task-399).

A loud room used to apply a raw ``-1`` Energy per tick while sleeping — at a
1-minute tick that is -1.0/min against a +0.30/min sleep regen, so a character
that slept in a training pit spiralled to 0 Energy and died of exhaustion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vital_rates import ENV_LOUD_ENERGY, SLEEP_ENERGY_REGEN

BASELINE_ENERGY_DECAY = 0.104  # vital_rates.BASELINE_DECAY["Energy"]


def test_loud_noise_energy_is_per_minute_scaled():
    # Guards against the legacy raw value (>= 1) creeping back in
    assert 0 < ENV_LOUD_ENERGY < 1.0


def test_sleep_in_a_loud_room_is_still_net_positive():
    net = SLEEP_ENERGY_REGEN - BASELINE_ENERGY_DECAY - ENV_LOUD_ENERGY
    assert net > 0, f"sleeping in noise would drain energy (net {net:.3f}/min)"


AREA = "Blizzard Forest Clearing"


def test_sleeping_in_a_loud_room_regenerates_over_a_tick_run():
    """The wake-before-regen ordering bug: a sleeper woken by noise every tick
    used to lose that tick's regen and drain to 0 (the training-pit death)."""
    from app import create_app
    from player import Player

    w = create_app({"TESTING": True}).world
    p = Player("BgGoblin")
    w.add_player(p)
    p.current_area = AREA
    w.set_player_area("BgGoblin", AREA)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    p.vitals["Energy"] = 10
    p.vitals["Thirst"] = 5
    p.vitals["Hunger"] = 5

    area_node = w.graph.get_node(w.area_node_id(AREA))
    assert area_node is not None
    area_node.properties.setdefault("environment", {})["noise"] = "loud"

    w.activities.start_activity("BgGoblin", "sleeping")
    start = p.vitals["Energy"]
    for _ in range(10):
        w.tick_turn()
    assert p.vitals["Energy"] >= start, "sleeping in a loud room drained Energy"
