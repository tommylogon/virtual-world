"""Structured appearance and personality, one slice (task-507).

Two authoring modes must both work: prose-only, and fully structured. The tests
are written so that the *default* case is the prose-only one — a library
character with no structured block is a normal character, not a half-configured
one, and the feature must not change how it reads or renders.

The curated-schema discipline is also pinned: every field in
``APPEARANCE_FIELDS`` / ``PERSONALITY_FIELDS`` must have a mechanic that reads
it, and the ones the task explicitly excludes (media, mbti, alignment) must be
absent. A field nobody reads is a field that rots.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from area import Area
from graph import Node
from player import Player

from engine import character_appearance as ca
from engine.character_appearance import (
    AFFECT_AXES,
    APPEARANCE_FIELDS,
    PERSONALITY_FIELDS,
    StructuredError,
    affect_for_stimulus,
    appearance,
    clear_record,
    get_record,
    is_structured,
    knows_personality_id,
    personality,
    render_prose,
    resolve_ids,
    schema_for_llm,
    set_record,
    validate,
)

AREA = "Verdant Hollow"

FULL = {
    "appearance": {
        "height_cm": 183,
        "weight_kg": 70,
        "build": "lean and wiry",
        "hair": {"color": "white", "length": "long", "style": "braided"},
        "eyes": {"color": "green"},
        "skin": {"tone": "pale green"},
    },
    "personality": {
        "likes": ["shiny-things"],
        "dislikes": ["mundane-chores"],
        "fears": ["goblin"],
        "kinks": ["teasing"],
        "turn_offs": ["coercion"],
    },
}


def _world():
    world = create_app({"TESTING": True}).world
    world.movement.add_area(Area(AREA, "A hollow.", []))
    return world


def _character(world, name="Arix"):
    player = Player(name)
    world.add_player(player)
    world.set_player_area(name, AREA)
    return player


def _node(world, name="Arix"):
    return world.graph.get_node(world._player_node_id(name))


# ── prose-only is the default ──

class TestProseOnlyIsTheDefault:

    def test_a_fresh_character_has_no_record(self):
        world = _world()
        _character(world)
        assert get_record(_node(world)) == {}
        assert is_structured(_node(world)) is False
        assert appearance(_node(world)) == {}
        assert personality(_node(world)) == {}

    def test_a_prose_only_character_renders_nothing(self):
        world = _world()
        _character(world)
        assert render_prose(_node(world)) == ""

    def test_a_prose_only_character_reacts_to_nothing(self):
        world = _world()
        _character(world)
        for stimulus in AFFECT_AXES:
            assert affect_for_stimulus(_node(world), stimulus) == {}

    def test_a_missing_node_is_not_an_error(self):
        assert get_record(None) == {}
        assert render_prose(None) == ""
        assert affect_for_stimulus(None, "teasing") == {}
        assert is_structured(None) is False

    def test_existing_library_characters_are_untouched(self):
        """Prose-only authoring keeps working exactly as before."""
        world = _world()
        player = _character(world)
        player.base_description = "A smug, cheerful young goblin."
        assert get_record(_node(world)) == {}
        assert player.base_description


# ── validation ──

class TestValidation:

    def test_a_full_record_validates(self):
        assert validate(FULL) == FULL

    def test_none_and_empty_are_empty(self):
        assert validate(None) == {}
        assert validate({}) == {}

    def test_unknown_top_level_keys_are_rejected(self):
        with pytest.raises(StructuredError) as exc:
            validate({"media": {"x": 1}})
        assert "media" in str(exc.value)

    def test_a_non_object_is_rejected(self):
        with pytest.raises(StructuredError):
            validate("lean and wiry")

    def test_appearance_must_be_an_object(self):
        with pytest.raises(StructuredError) as exc:
            validate({"appearance": "tall"})
        assert "appearance" in str(exc.value)

    def test_a_group_must_be_an_object(self):
        with pytest.raises(StructuredError) as exc:
            validate({"appearance": {"hair": "white"}})
        assert "appearance.hair" in str(exc.value)

    def test_unknown_group_subfields_are_dropped(self):
        out = validate({"appearance": {"hair": {"colour": "white", "color": "red"}}})
        assert out["appearance"]["hair"] == {"color": "red"}

    def test_a_non_numeric_height_is_rejected(self):
        with pytest.raises(StructuredError) as exc:
            validate({"appearance": {"height_cm": "tall"}})
        assert "height_cm" in str(exc.value)

    def test_an_implausible_height_is_rejected(self):
        with pytest.raises(StructuredError) as exc:
            validate({"appearance": {"height_cm": 5}})
        assert "plausible" in str(exc.value)

    def test_an_implausible_weight_is_rejected(self):
        with pytest.raises(StructuredError):
            validate({"appearance": {"weight_kg": 2000}})

    def test_blanks_are_dropped_not_stored_as_empty_strings(self):
        out = validate({"appearance": {"build": "   ", "hair": {"color": ""}}})
        assert out == {}

    def test_a_zero_height_is_kept(self):
        """0 is falsy but is not 'absent' -- though it is implausible anyway."""
        with pytest.raises(StructuredError):
            validate({"appearance": {"height_cm": 0}})


class TestReferencesMustBeIds:

    def test_display_names_are_rejected(self):
        with pytest.raises(StructuredError) as exc:
            validate({"personality": {"kinks": ["Teasing Jokes"]}})
        assert "ids" in str(exc.value)

    def test_the_rejection_names_what_it_refused(self):
        with pytest.raises(StructuredError) as exc:
            validate({"personality": {"likes": ["good", "Shiny Things"]}})
        assert "Shiny Things" in str(exc.value)

    def test_a_single_string_is_accepted_as_a_one_item_list(self):
        assert validate({"personality": {"kinks": "teasing"}}) == \
            {"personality": {"kinks": ["teasing"]}}

    def test_a_bad_entry_does_not_silently_drop_the_good_ones(self):
        """Rejecting the whole field is the point; partial acceptance is not."""
        with pytest.raises(StructuredError):
            validate({"personality": {"kinks": ["teasing", "Not An Id"]}})

    def test_ids_are_deduplicated(self):
        out = validate({"personality": {"kinks": ["teasing", "teasing"]}})
        assert out["personality"]["kinks"] == ["teasing"]

    def test_a_non_list_is_rejected(self):
        with pytest.raises(StructuredError) as exc:
            validate({"personality": {"kinks": {"a": 1}}})
        assert "list" in str(exc.value)

    def test_a_fear_id_uses_the_same_vocabulary_as_fear_tags(self):
        assert set(PERSONALITY_FIELDS) >= {"fears"}


# ── storage ──

class TestStorage:

    def test_set_then_read(self):
        world = _world()
        _character(world)
        node = _node(world)
        assert set_record(node, FULL) == FULL
        assert is_structured(node) is True
        assert appearance(node)["height_cm"] == 183
        assert personality(node)["kinks"] == ["teasing"]

    def test_set_replaces_rather_than_merges(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, FULL)
        set_record(node, {"appearance": {"build": "stocky"}})
        assert appearance(node) == {"build": "stocky"}

    def test_an_empty_block_removes_the_key(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, FULL)
        set_record(node, {})
        assert is_structured(node) is False
        assert ca.RECORD_KEY not in node.properties

    def test_clear_restores_prose_only(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, FULL)
        clear_record(node)
        assert is_structured(node) is False
        assert render_prose(node) == ""

    def test_storing_does_not_touch_the_player(self):
        """The record lives on the node; the Player is untouched (no hub edit)."""
        world = _world()
        player = _character(world)
        set_record(_node(world), FULL)
        assert not hasattr(player, ca.RECORD_KEY)

    def test_a_node_without_properties_is_rejected(self):
        class Bare:
            properties = None
        with pytest.raises(StructuredError):
            set_record(Bare(), FULL)


# ── prose ──

class TestRenderProse:

    def test_a_full_appearance_renders(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, FULL)
        prose = render_prose(node)
        assert "6 feet" in prose
        assert "lean and wiry" in prose
        assert "white" in prose and "green eyes" in prose
        assert "pale green skin" in prose
        assert prose.endswith(".")

    def test_a_partial_appearance_renders(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, {"appearance": {"build": "stocky"}})
        assert render_prose(node) == "Stocky."

    def test_personality_alone_renders_nothing(self):
        """Personality is not appearance; it must not leak into the look."""
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, {"personality": {"kinks": ["teasing"]}})
        assert render_prose(node) == ""

    def test_hair_length_alone_renders(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, {"appearance": {"hair": {"length": "long"}}})
        assert "long" in render_prose(node).lower()

    def test_ids_resolve_to_display_names(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, {"appearance": {"hair": {"style": "shiny-things"}}})
        prose = render_prose(node, resolve=lambda v: f"<{v}>")
        assert "<shiny-things>" in prose

    def test_an_unresolvable_id_stays_visible(self):
        """A kink that quietly vanishes is a bug with no cause."""
        assert resolve_ids(["nope"], lambda v: None) == ["nope"]
        assert resolve_ids(["a"], lambda v: (_ for _ in ()).throw(RuntimeError())) == ["a"]

    def test_height_rounds_to_whole_inches(self):
        world = _world()
        _character(world)
        node = _node(world)
        set_record(node, {"appearance": {"height_cm": 183.5}})
        assert "6 feet" in render_prose(node)


# ── the mechanic ──

class TestAffectForStimulus:

    def _structured(self, world, personality_block):
        _character(world)
        node = _node(world)
        set_record(node, {"personality": personality_block})
        return node

    def test_a_kink_raises_arousal(self):
        world = _world()
        node = self._structured(world, {"kinks": ["teasing"]})
        affect = affect_for_stimulus(node, "teasing")
        assert affect["aroused"] > 0

    def test_a_turn_off_raises_disgust_and_lowers_arousal(self):
        world = _world()
        node = self._structured(world, {"turn_offs": ["coercion"]})
        affect = affect_for_stimulus(node, "coercion")
        assert affect["disgusted"] > 0
        assert affect["aroused"] < 0

    def test_an_unknown_stimulus_is_nothing(self):
        world = _world()
        node = self._structured(world, {"kinks": ["teasing"]})
        assert affect_for_stimulus(node, "trombone") == {}

    def test_a_neutral_stimulus_is_nothing(self):
        world = _world()
        node = self._structured(world, {"kinks": ["teasing"]})
        assert affect_for_stimulus(node, "dominance") == {}

    def test_a_turn_off_wins_over_a_kink_on_the_same_id(self):
        """A character cannot be both drawn to and repelled by one thing here."""
        world = _world()
        node = self._structured(world, {"kinks": ["coercion"],
                                        "turn_offs": ["coercion"]})
        affect = affect_for_stimulus(node, "coercion")
        assert affect["disgusted"] > 0
        assert affect["aroused"] < 0

    def test_an_id_with_no_axis_table_still_moves_arousal(self):
        """A kink the engine has no axes for is still a kink."""
        world = _world()
        node = self._structured(world, {"kinks": ["interpretive-dance"]})
        assert affect_for_stimulus(node, "interpretive-dance")["aroused"] > 0

    def test_every_affect_axis_is_a_real_emotion_dimension(self):
        from engine.emotion import BASELINES
        for stimulus, axes in AFFECT_AXES.items():
            for axis in axes:
                assert axis in BASELINES, f"{stimulus} uses unknown axis {axis}"

    def test_the_axes_reach_the_affect_map(self):
        """End to end: the deltas a trigger applies really move the character."""
        from engine import emotion as em
        world = _world()
        player = _character(world)
        node = self._structured(world, {"turn_offs": ["cruelty"]})
        before = player.emotions_map()["disgusted"]
        for axis, delta in affect_for_stimulus(node, "cruelty").items():
            em.spike(player.emotions_map(), axis, delta)
        assert player.emotions_map()["disgusted"] > before

    def test_knows_personality_id(self):
        world = _world()
        node = self._structured(world, {"likes": ["shiny-things"],
                                        "dislikes": ["mundane-chores"]})
        assert knows_personality_id(node, "likes", "shiny-things") is True
        assert knows_personality_id(node, "likes", "mundane-chores") is False
        assert knows_personality_id(node, "dislikes", "mundane-chores") is True
        assert knows_personality_id(node, "kinks", "teasing") is False


# ── the curated-set discipline ──

class TestCuratedSet:

    def test_the_task_named_fields_are_present(self):
        assert set(APPEARANCE_FIELDS) == {
            "height_cm", "weight_kg", "build", "hair", "eyes", "skin"}
        assert set(PERSONALITY_FIELDS) == {
            "likes", "dislikes", "fears", "kinks", "turn_offs"}

    def test_the_excluded_catalog_fields_are_absent(self):
        """The task says grow per-feature, not dump the graph-editor catalog."""
        blob = " ".join(list(APPEARANCE_FIELDS) + list(PERSONALITY_FIELDS)).lower()
        for banned in ("media", "mbti", "alignment", "faction"):
            assert banned not in blob

    def test_every_personality_field_names_its_mechanic(self):
        for field, mechanic in PERSONALITY_FIELDS.items():
            assert mechanic.strip(), f"{field} has no stated mechanic"

    def test_the_schema_covers_every_field(self):
        schema = schema_for_llm()
        assert set(schema["properties"]) == {"appearance", "personality"}
        assert set(schema["properties"]["appearance"]["properties"]) == \
            set(APPEARANCE_FIELDS)
        assert set(schema["properties"]["personality"]["properties"]) == \
            set(PERSONALITY_FIELDS)

    def test_the_schema_forbids_extra_keys(self):
        schema = schema_for_llm()
        assert schema["additionalProperties"] is False
        assert schema["properties"]["appearance"]["additionalProperties"] is False

    def test_the_schema_declares_id_patterns_for_personality(self):
        props = schema_for_llm()["properties"]["personality"]["properties"]
        assert "pattern" in props["kinks"]["items"]

    def test_every_appearance_field_is_rendered(self):
        """A field that cannot reach the prose is a field with no purpose."""
        world = _world()
        _character(world)
        node = _node(world)
        for field, (kind, subfields) in APPEARANCE_FIELDS.items():
            value = ({sub: f"x-{sub}" for sub in subfields} if kind == "group"
                     else "lean" if kind == "text" else 170)
            set_record(node, {"appearance": {field: value}})
            assert render_prose(node), f"{field} rendered nothing"


# ── the routes ──

class TestRoutes:

    def _client(self):
        return create_app({"TESTING": True}).test_client()

    def test_get_reports_prose_only(self):
        response = self._client().get("/api/players/Lyrie/record")
        assert response.status_code == 200
        body = response.get_json()
        assert body["structured"] is False
        assert body["record"] == {}
        assert body["schema"]["properties"]

    def test_put_stores_and_renders(self):
        client = self._client()
        response = client.put("/api/players/Lyrie/record", json={"record": FULL})
        assert response.status_code == 200
        body = response.get_json()
        assert body["structured"] is True
        assert "6 feet" in body["prose"]

    def test_put_rejects_a_bad_record_with_400(self):
        response = self._client().put(
            "/api/players/Lyrie/record", json={"record": {"personality": {"kinks": ["Not An Id"]}}})
        assert response.status_code == 400
        assert "ids" in response.get_json()["error"]

    def test_put_without_render_leaves_the_prose_alone(self):
        client = self._client()
        response = client.put("/api/players/Lyrie/record",
                              json={"record": FULL, "render": False})
        assert response.status_code == 200
        assert "prose" not in response.get_json()

    def test_a_hand_written_base_description_is_not_clobbered(self):
        """A route should not silently replace a paragraph someone wrote."""
        world = create_app({"TESTING": True}).world
        world.player_manager.get_player("Lyrie").base_description = "A goblin."
        client = create_app({"TESTING": True}).test_client()
        client.put("/api/players/Lyrie/record", json={"record": FULL})
        assert "base_description" not in client.put(
            "/api/players/Lyrie/record", json={"record": FULL}).get_json()

    def test_delete_restores_prose_only(self):
        client = self._client()
        client.put("/api/players/Lyrie/record", json={"record": FULL})
        response = client.delete("/api/players/Lyrie/record")
        assert response.status_code == 200
        assert response.get_json()["structured"] is False

    def test_affect_endpoint(self):
        client = self._client()
        client.put("/api/players/Lyrie/record",
                   json={"record": {"personality": {"kinks": ["teasing"]}}})
        body = client.get("/api/players/Lyrie/affect?stimulus=teasing").get_json()
        assert body["affect"]["aroused"] > 0
        body = client.post("/api/players/Lyrie/affect",
                           json={"stimulus": "trombone"}).get_json()
        assert body["affect"] == {}

    def test_unknown_player_is_404(self):
        client = self._client()
        assert client.get("/api/players/Nobody/record").status_code == 404
        assert client.put("/api/players/Nobody/record",
                          json={"record": {}}).status_code == 404
        assert client.get("/api/players/Nobody/affect").status_code == 404
