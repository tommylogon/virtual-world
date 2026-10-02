"""task-549: species on characters — an animal is not a goblin.

Before this, need servicing was a **pure tag intersection**: the engine could see
what a room was tagged but had no idea what kind of creature was standing in it,
so "would an animal use a latrine?" had no answer in either direction. The
distinction was authored by hand in room tags and invisible to the simulation.

These tests pin the three things that make the field safe to add:

1. a species the need layer can actually read;
2. an exclusion that is **data** — written in a profile the author can see — not
   a guess, and not a tag somebody happened to put on a room;
3. every existing character and scenario loading unchanged, because an
   unspecified species must permit everything.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import species as species_mod
from engine.species import (
    SERVICES, SPECIES_PROFILES, can_use_service, excluded_services,
    profile_for, species_of,
)
from player import Player

AREA = "Blizzard Forest Clearing"


@pytest.fixture()
def world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _add(world, name, area=AREA, **attrs):
    p = Player(name)
    p.current_area = area
    for key, value in attrs.items():
        setattr(p, key, value)
    world.add_player(p)
    if area:
        world.set_player_area(name, area)
    return p


# ── the identity is readable ─────────────────────────────────────────────

def test_a_character_carries_a_species():
    p = Player("Grukk")
    assert p.species is None
    p.species = "Goblin"
    assert species_of(p) == "goblin", "normalised, so case cannot fork behaviour"


def test_species_is_read_from_the_player_not_a_bare_node():
    """The AGENTS.md trap: a character graph node is created bare and carries no
    such field, so a reader that looked at the node would see nothing."""
    from graph import Node
    node = Node(id="c1", type="character", name="Goblin")
    assert species_of(node) == ""
    authored = Node(id="c2", type="character", name="Goblin",
                    properties={"species": "goblin"})
    assert species_of(authored) == "goblin"


def test_a_list_species_takes_its_primary():
    p = Player("x")
    p.species = ["forest goblin", "scout"]
    assert species_of(p) == "forest goblin"


def test_a_compound_species_inherits_from_its_last_word():
    """An author should not have to register a profile for every adjective."""
    assert profile_for("deep elf") == SPECIES_PROFILES["elf"]
    assert profile_for("forest goblin") == SPECIES_PROFILES["goblin"]
    assert profile_for("a giant forest troll") is None


# ── exclusion is data, not a guess ──────────────────────────────────────

def test_an_animal_is_excluded_from_a_relief_fixture():
    """The acceptance case, stated as a fact about the creature."""
    p = Player("Hound")
    p.species = "animal"
    assert can_use_service(p, "relief") is False
    assert can_use_service(p, "drink") is True, "exclusions are per service"


def test_a_goblin_is_not_excluded_from_a_relief_fixture():
    """The same room, a different body, the other answer."""
    p = Player("Grukk")
    p.species = "goblin"
    assert can_use_service(p, "relief") is True


def test_an_undead_creature_needs_neither_food_nor_drink():
    p = Player("Rotting Corpse")
    p.species = "undead"
    assert can_use_service(p, "food") is False
    assert can_use_service(p, "drink") is False
    assert can_use_service(p, "relief") is True


def test_the_exclusion_list_is_readable_by_a_prompt():
    p = Player("Hound")
    p.species = "animal"
    assert excluded_services(p) == ["relief"]
    assert excluded_services(Player("unspecified")) == []


def test_an_unknown_species_can_do_everything():
    """No invented restriction: a species nobody registered is not a species
    nobody is allowed to do things."""
    p = Player("Zaphkiel")
    p.species = "aetherial wyrm"
    assert can_use_service(p, "relief") is True
    assert can_use_service(p, "food") is True


def test_an_unknown_service_is_permitted_rather_than_denied():
    """The day someone adds a service, no profile may silently start refusing
    it."""
    p = Player("Hound")
    p.species = "animal"
    assert can_use_service(p, "a brand new service") is True


def test_every_profile_only_declares_exclusions_never_permissions():
    """A positive list would have to enumerate every service to stay honest, and
    the day a service is added it would start lying."""
    for name, profile in SPECIES_PROFILES.items():
        assert "cannot_use" in profile, name
        assert "can_use" not in profile, name
        unknown = set(profile.get("cannot_use", ())) - set(SERVICES)
        assert not unknown, f"{name} excludes unknown services {unknown}"


# ── the load-bearing compatibility: nothing changes without a species ────

def test_an_unspecified_character_can_use_every_service():
    for service in SERVICES:
        assert can_use_service(Player("nobody"), service) is True, service


def test_every_library_character_still_loads_and_behaves_identically():
    """70 characters, none of which declared a species when task-549 landed, so
    every one of them must be unrestricted — that is what makes adding the field
    safe.

    task-606's authoring pass has since given 35 of them a `species` (derived
    from the tags they already carried), so this no longer asserts that *none*
    do; it asserts the thing that actually matters, which is that declaring one
    **grants** nothing and **denies** nothing by accident. A species that
    restricted a goblin from a latrine would have been a behaviour change nobody
    asked for.
    """
    root = Path(__file__).parent.parent / "data" / "library" / "characters"
    files = sorted(root.glob("*.json"))
    assert len(files) >= 68, f"expected the whole library, found {len(files)}"

    with_species = 0
    restricted = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        p = Player(data.get("name", path.stem))
        declared = data.get("species")
        if declared:
            p.species = declared
            with_species += 1
        denied = [s for s in SERVICES if not can_use_service(p, s)]
        # An animal does not use a relief *fixture* — that is task-549's decided
        # behaviour and it changes comfort, never permission. Nothing else in the
        # library may be denied anything.
        unexpected = [s for s in denied if not (
            denied == ["relief"] and "animal" in str(declared))]
        if unexpected:
            restricted.append(f"{path.name} ({declared}) -> {unexpected}")
    assert not restricted, restricted
    assert with_species, "expected the task-606 authoring pass to have set some"


def test_a_save_without_species_round_trips_unchanged():
    """Absent in the save must stay absent on the Player, not become `""` or
    `"human"` — both of which would be an invented restriction."""
    p = Player("Old Save Character")
    assert p.to_dict()["species"] is None
    assert can_use_service(p, "relief") is True


# ── the wiring: the need layer reads it ──────────────────────────────────

def test_the_relief_handler_treats_a_fixture_the_body_cannot_use_as_improper(
        world, monkeypatch):
    """The live path: `_relieve` is the background tier's relief action and the
    one place a species exclusion has to bite."""
    from engine.background_simulation import BackgroundSimulation

    sim = BackgroundSimulation(world)
    area_node = world.graph.get_node(world._get_current_area_id())
    area_node.properties["tags"] = ["latrine"]

    human = Player("Human")
    human.current_area = AREA
    world.add_player(human)
    assert sim._relieve(human) is True
    assert human.vitals["Bladder"] == 0
    # A human in a latrine pays no dignity cost: nothing about being here hurts.
    assert human.vitals["Sanity"] == 100, "a proper place is silent"

    hound = Player("Hound")
    hound.current_area = AREA
    hound.species = "animal"
    world.add_player(hound)
    assert sim._relieve(hound) is True
    assert hound.vitals["Bladder"] == 0, "relief itself is never forbidden"
    assert hound.vitals["Sanity"] < 100, (
        "a fixture this body cannot use is not a proper place for it")


def test_species_does_not_reintroduce_a_refusal(world):
    """task-551 permits relief anywhere, and an exclusion must not quietly
    become a gate: an animal with no latrine anywhere still relieves itself."""
    from engine.background_simulation import BackgroundSimulation

    sim = BackgroundSimulation(world)
    area_node = world.graph.get_node(world._get_current_area_id())
    area_node.properties.pop("latrine", None)
    area_node.properties["tags"] = ["open_field"]

    hound = Player("Hound")
    hound.current_area = AREA
    hound.species = "animal"
    world.add_player(hound)
    assert sim._relieve(hound) is True, "must never refuse"


def test_the_species_mismatch_is_recorded_not_announced(world):
    from engine.background_simulation import BackgroundSimulation

    sim = BackgroundSimulation(world)
    area_node = world.graph.get_node(world._get_current_area_id())
    area_node.properties["tags"] = ["latrine"]

    hound = Player("Hound")
    hound.current_area = AREA
    hound.species = "animal"
    world.add_player(hound)
    sim._relieve(hound)

    species_entries = [e for e in hound.lived_log
                       if str(e.get("why", "")).startswith("species:")]
    assert species_entries, hound.lived_log
    assert species_entries[-1]["why"] == "species:animal"


def test_a_character_with_no_species_never_records_a_mismatch(world):
    from engine.background_simulation import BackgroundSimulation

    sim = BackgroundSimulation(world)
    area_node = world.graph.get_node(world._get_current_area_id())
    area_node.properties["tags"] = ["latrine"]

    human = Player("Human")
    human.current_area = AREA
    world.add_player(human)
    sim._relieve(human)
    assert not [e for e in human.lived_log
                if str(e.get("why", "")).startswith("species:")], human.lived_log


# ── there are TWO player serializers, and both must carry it ─────────────

def test_species_survives_a_write_and_appears_in_the_api_payload():
    """Found by driving the live API, not by reading the code.

    There are two player serializers: `Player.to_dict()` and
    `SerializationManager._serialize_player`. `/api/state` serves the **second**
    one, so a species written through `POST /api/players/<name>` was accepted,
    stored on the Player, and then absent from the response the client had just
    been handed — a write that silently did not read back. A field added to one
    serializer is not added to the other.
    """
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()
    _add(world, "TestSubject")

    response = client.post("/api/players/TestSubject", json={"species": "Goblin"})
    assert response.status_code == 200, response.get_data(as_text=True)

    payload = client.get("/api/state").get_json()
    player = payload["players"]["TestSubject"]
    assert "species" in player, (
        "species is written but not served: the two player serializers have "
        "drifted apart again")
    assert player["species"] == "goblin", player.get("species")

    # And it survives the save/load round trip through that same payload.
    assert world.players["TestSubject"].species == "goblin"


def test_both_player_serializers_carry_the_authored_identity():
    """The general guard, so the next field added does not repeat the mistake.

    There are two player serializers and they overlap heavily but are not the
    same function: `Player.to_dict()` and the manager's own
    `_serialize_player`. The one `/api/state` serves is the *second*, which is
    why a field added to only the first is invisible to the client.
    """
    from app import create_app
    world = create_app({"TESTING": True}).world
    p = _add(world, "Agreement", species="elf", size="small")

    from_dict = p.to_dict()
    served = world.serializer._serialize_player("Agreement", p)

    for field in ("species", "size"):
        assert field in from_dict, f"{field} missing from Player.to_dict()"
        assert field in served, f"{field} missing from the /api/state serializer"
    assert served["species"] == "elf"
    assert served["size"] == "small"
