"""The starting room must reach the minimap.

`_observed_by_location` (routes/player_ops.py) builds the map from memories
of ``kind == "area"``. `Player.record_observation` updates a subject's
observation IN PLACE, but originally set ``kind`` only on the create branch.
A subject whose index slot was first claimed by an unlabelled memory (a
"did go grand_stairs (foyer, tick 5)" trace) therefore kept ``kind: None``
forever, and the room the character is standing in — the one it started in —
never appeared on the map.
"""
from player import Player


def _area_trace(p, subject_id="area_foyer", tick=5):
    """An unlabelled trace that claims the observation index slot."""
    entry = p.add_memory(
        f"did go grand_stairs (foyer, tick {tick})", tick,
        memory_type="turn_event", source="auto",
        entity_ids=[subject_id], location="foyer",
    )
    p.memory_index[str(subject_id)] = entry["id"]
    return entry


def test_kind_is_carried_onto_an_existing_observation():
    p = Player("jake halloway")
    _area_trace(p)

    p.record_observation("area_foyer", "You have been in the foyer.", 11,
                         kind="area", location="foyer")

    entry = p.observation_memory("area_foyer")
    assert entry is not None
    assert entry["kind"] == "area", "kind describes the subject, not the visit"
    assert entry["text"] == "You have been in the foyer."
    assert entry["visits"] == 2


def test_an_empty_kind_does_not_wipe_a_labelled_observation():
    """The update must not clear a kind when the caller supplies none."""
    p = Player("jake halloway")
    p.record_observation("area_foyer", "You have been in the foyer.", 1,
                         kind="area", location="foyer")

    p.record_observation("area_foyer", "You have been in the foyer.", 2,
                         kind="", location="foyer")

    assert p.observation_memory("area_foyer")["kind"] == "area"


def test_the_starting_room_is_reported_as_visited():
    """End-to-end shape: what the map endpoint filters on."""
    from routes.player_ops import _observed_by_location

    p = Player("jake halloway")
    p.current_area = "foyer"
    _area_trace(p)
    p.record_observation("area_foyer", "You have been in the foyer.", 11,
                         kind="area", location="foyer")

    areas, _items, _people = _observed_by_location(p)
    assert "area_foyer" in areas, "the room you are standing in must be on the map"
    assert areas["area_foyer"]["name"] == "foyer"


def test_several_visits_stay_one_row():
    p = Player("jake halloway")
    p.current_area = "foyer"
    _area_trace(p)
    for tick in (11, 12, 13):
        p.record_observation("area_foyer", "You have been in the foyer.", tick,
                             kind="area", location="foyer")

    from routes.player_ops import _observed_by_location
    areas, _items, _people = _observed_by_location(p)
    assert list(areas) == ["area_foyer"]
    assert p.observation_memory("area_foyer")["visits"] == 4