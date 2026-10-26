"""Structured appearance and personality, one slice (task-507).

Two authoring modes must both work: prose-only, and fully structured. The tests
are written so that the *default* case is the prose-only one - a library
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
    IDENTITY_FIELDS,
    NARRATIVE_FIELDS,
    PERSONALITY_FIELDS,
    StructuredError,
    affect_for_stimulus,
    appearance,
    clear_record,
    compile_persona,
    get_record,
    identity,
    is_structured,
    knows_personality_id,
    narrative,
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

    def test_legacy_appearance_key_shim_resolves_on_read(self):
        """A node carrying the old 'appearance' block reads through get_record."""
        world = _world()
        _character(world)
        node = _node(world)
        # Write via the shim key directly (simulates an old save file)
        node.properties[ca._LEGACY_KEY] = {"identity": {"age": 12}}
        rec = get_record(node)
        assert "identity" in rec and rec["identity"]["age"] == 12

    def test_legacy_key_migrates_on_set_and_survives_reload(self):
        """Legacy -> load -> write saves under persona; reload sees persona."""
        world = _world()
        _character(world)
        node = _node(world)
        # Pre-load with legacy key
        node.properties[ca._LEGACY_KEY] = {"identity": {"age": 12}}
        # Write via new API - should evict legacy and write persona
        set_record(node, {"identity": {"age": 13}})
        assert ca.RECORD_KEY in node.properties
        assert ca._LEGACY_KEY not in node.properties
        assert node.properties[ca.RECORD_KEY]["identity"]["age"] == 13
        # Also clear_record removes both keys
        node2 = _node(world)
        node2.properties.update({ca.RECORD_KEY: {}, ca._LEGACY_KEY: {}})
        clear_record(node2)
        assert ca.RECORD_KEY not in node2.properties
        assert ca._LEGACY_KEY not in node2.properties

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
            "overview", "height_cm", "weight_kg", "build", "hair", "eyes",
            "skin", "face", "body", "voice", "scent", "style"}
        assert set(PERSONALITY_FIELDS) == {
            "likes", "dislikes", "fears", "interests", "kinks", "turn_ons",
            "turn_offs", "traumas", "boundaries", "traits", "aspirations",
            "quirks", "habits", "speech_pattern", "experience"}
        assert set(IDENTITY_FIELDS) == {
            "pronouns", "age", "gender", "species", "occupation", "sexuality",
            "mbti", "alignment", "birthday", "potential_storylines"}
        assert set(NARRATIVE_FIELDS) == {
            "biography", "secrets", "example_dialogues", "role_in_town",
            "arc", "media"}

    def test_the_excluded_catalog_fields_are_absent(self):
        """The task says grow per-feature, not dump the graph-editor catalog.

        ``media``, ``mbti`` and ``alignment`` are no longer excluded: they land
        under identity (task-850). ``faction`` is still banned from appearance /
        personality and has not been promoted to identity either.
        """
        blob = " ".join(list(APPEARANCE_FIELDS) + list(PERSONALITY_FIELDS)).lower()
        assert "faction" not in blob

    def test_every_personality_field_names_its_mechanic(self):
        for field, mechanic in PERSONALITY_FIELDS.items():
            assert mechanic.strip(), f"{field} has no stated mechanic"

    def test_the_schema_covers_every_field(self):
        schema = schema_for_llm()
        assert set(schema["properties"]) == {
            "identity", "appearance", "personality", "narrative"}
        assert set(schema["properties"]["appearance"]["properties"]) == \
            set(APPEARANCE_FIELDS)
        assert set(schema["properties"]["personality"]["properties"]) == \
            set(PERSONALITY_FIELDS)
        assert set(schema["properties"]["identity"]["properties"]) == \
            set(IDENTITY_FIELDS)
        assert set(schema["properties"]["narrative"]["properties"]) == \
            set(NARRATIVE_FIELDS)

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


# ── task-828: expanded schema + compile ──

RICH = {
    "identity": {
        "pronouns": "she/her",
        "age": 34,
        "species": "human",
        "occupation": "blacksmith",
        "sexuality": "bisexual",
    },
    "appearance": {
        "overview": "A broad-shouldered smith with soot in the creases",
        "hair": {"color": "black", "length": "cropped", "style": "swept-back",
                 "accessories": ["iron pin"]},
        "eyes": {"color": "grey", "shape": "narrow"},
        "skin": {"tone": "tan", "distinguishing_features": ["burn scar"]},
        "body": {"modifications": ["anchor tattoo", "hook prosthetic"]},
        "voice": {"pitch": "low", "accent": "northern"},
        "scent": "coal-smoke",
        "style": {"clothing": ["leather apron"], "footwear": ["steel boots"]},
    },
    "personality": {
        "traits": ["brave", "blunt"],
        "interests": ["smithing"],
        "fears": ["drowning"],
        "traumas": ["mine-collapse"],
        "likes": ["dark-ale"],
        "quirks": ["hums_while_working"],
        "speech_pattern": {"style": "terse", "catchphrases": ["mind the sparks"]},
        "experience": "apprenticed ten years",
    },
    "narrative": {
        "biography": {"current_situation": "holds the forge alone"},
        "secrets": {"deepest_secret": "sold a cursed blade",
                    "known_by": ["Old Maren"]},
        "example_dialogues": ["Steel remembers."],
        "role_in_town": "smith",
    },
}


class TestExpandedSchema:

    def _rich_node(self, world, name="Arix"):
        _character(world, name)
        node = _node(world, name)
        set_record(node, RICH)
        return node

    def test_identity_and_narrative_validate(self):
        cleaned = validate(RICH)
        assert cleaned["identity"]["age"] == 34
        assert cleaned["identity"]["pronouns"] == "she/her"
        assert cleaned["narrative"]["role_in_town"] == "smith"
        assert identity(_node) is not None  # reader exists

    def test_prose_lists_take_free_text(self):
        node_record = validate({"narrative": {"example_dialogues": ["Brave", "soft spoken"]}})
        assert node_record["narrative"]["example_dialogues"] == ["Brave", "soft spoken"]

    def test_id_lists_still_reject_display_names(self):
        with pytest.raises(StructuredError):
            validate({"personality": {"fears": ["Not An Id"]}})
        with pytest.raises(StructuredError):
            validate({"personality": {"traits": ["Not An Id"]}})
        with pytest.raises(StructuredError):
            validate({"personality": {"quirks": ["Not An Id"]}})
        with pytest.raises(StructuredError):
            validate({"personality": {"habits": ["Not An Id"]}})
        with pytest.raises(StructuredError):
            validate({"personality": {"aspirations": ["Not An Id"]}})

    def test_negative_age_is_rejected(self):
        with pytest.raises(StructuredError):
            validate({"identity": {"age": -3}})

    def test_compile_projects_prose_and_tags(self):
        world = _world()
        node = self._rich_node(world)
        compiled = compile_persona(node)
        assert "34-year-old" in compiled["base_description"]
        assert "blacksmith" in compiled["base_description"]
        assert "anchor tattoo" in compiled["base_description"]
        assert "smithing" in compiled["interest_tags"]
        assert "dark-ale" in compiled["interest_tags"]
        assert "drowning" in compiled["fear_tags"]
        assert "mine-collapse" in compiled["fear_tags"]
        assert "brave" in compiled["traits"]
        assert "mind the sparks" in compiled["personality"]
        assert "holds the forge alone" in compiled["description"]
        assert "bisexual" in compiled["personality"]
        assert "Steel remembers." in compiled["personality"]

    def test_compile_region_linked_markings(self):
        # task-852 P3: "area::text" in modifications[] projects to readable prose.
        world = _world()
        _character(world, "Marked")
        node = _node(world, "Marked")
        set_record(node, {
            "appearance": {
                "body": {"modifications": ["torso::anchor tattoo", "legacy scar"]},
            },
        })
        compiled = compile_persona(node)
        prose = compiled["base_description"].lower()  # sentence-initial clause is capitalised
        assert "bearing anchor tattoo on the torso" in prose
        assert "bearing legacy scar" in prose
        assert "torso::" not in prose

    def test_compile_of_prose_only_is_empty(self):
        world = _world()
        _character(world)
        compiled = compile_persona(_node(world))
        assert compiled["base_description"] == ""
        assert compiled["interest_tags"] == []
        assert compiled["fear_tags"] == []

    def test_explicit_pronouns_win_over_tags(self):
        from engine.pronouns import pronouns_for
        world = _world()
        player = _character(world)
        player.tags = ["male"]
        node = self._rich_node(world)
        assert pronouns_for(player, get_record(node))["subject"] == "she"
        assert pronouns_for(player)["subject"] == "he"

    def test_record_readers_cover_all_sections(self):
        world = _world()
        node = self._rich_node(world)
        assert identity(node)["species"] == "human"
        assert narrative(node)["role_in_town"] == "smith"
        assert appearance(node)["scent"] == "coal-smoke"
        assert personality(node)["traits"] == ["brave", "blunt"]

    def test_group_fields_declare_object_type(self):
        """The tab renders groups from decl.type/properties; a group
        without the type renders as String(object) (caught live)."""
        schema = schema_for_llm()["properties"]
        for section in ("appearance", "narrative"):
            for field, decl in schema[section]["properties"].items():
                if isinstance(decl, dict) and "properties" in decl:
                    assert decl.get("type") == "object", f"{section}.{field}"

    def test_every_field_names_its_consumer(self):
        from engine.character_appearance import CONSUMER_HINTS
        schema = schema_for_llm()["properties"]
        paths = set()
        for section, block in schema.items():
            for field in block["properties"]:
                paths.add(f"{section}.{field}")
        missing = sorted(p for p in paths if p not in CONSUMER_HINTS)
        assert not missing, f"fields with no consumer hint: {missing}"


class TestCompileRoutes:

    def _client(self):
        return create_app({"TESTING": True}).test_client()

    def test_compile_preview_writes_nothing(self):
        client = self._client()
        client.put("/api/players/Lyrie/record", json={"record": RICH})
        response = client.post("/api/players/Lyrie/record/compile", json={})
        assert response.status_code == 200
        body = response.get_json()
        assert "34-year-old" in body["compiled"]["base_description"]
        assert "smithing" in body["compiled"]["interest_tags"]
        # Lyrie ships library hand prose, so the default path previews.
        assert body.get("needs_confirm") is True
        assert "compiled" in body["preview"]["base_description"]
        before = client.get("/api/state").get_json()["players"]["Lyrie"]
        assert "34-year-old" not in (before.get("base_description") or "")

    def test_compile_applies_to_empty_prose(self):
        client = self._client()
        client.put("/api/players/Lyrie/record", json={"record": RICH})
        body = client.post("/api/players/Lyrie/record/compile",
                           json={"force": True}).get_json()
        assert body.get("applied") is True
        state = client.get("/api/state").get_json()
        lyrie = state["players"]["Lyrie"]
        assert "34-year-old" in lyrie["base_description"]
        assert "smithing" in lyrie["interest_tags"]
        assert "mine-collapse" in lyrie["fear_tags"]

    def test_compile_needs_confirm_over_hand_prose(self):
        app = create_app({"TESTING": True})
        desc = "A goblin someone described by hand."
        app.world.player_manager.get_player("Lyrie").base_description = desc
        node = app.world.graph.get_node(app.world._player_node_id("Lyrie"))
        if node:
            node.properties["base_description"] = desc
        client = app.test_client()
        client.put("/api/players/Lyrie/record", json={"record": RICH})
        body = client.post("/api/players/Lyrie/record/compile",
                           json={}).get_json()
        assert body.get("needs_confirm") is True
        assert "goblin someone described" in \
            body["preview"]["base_description"]["current"]
        assert "applied" not in body
        forced = client.post("/api/players/Lyrie/record/compile",
                             json={"force": True}).get_json()
        assert forced.get("applied") is True
        assert "34-year-old" in forced["compiled"]["base_description"]

    def test_put_compile_true_projects_tags(self):
        client = self._client()
        body = client.put("/api/players/Lyrie/record",
                          json={"record": RICH, "compile": True,
                                "force": True}).get_json()
        assert body.get("applied") is True
        assert "mine-collapse" in body["compiled"]["fear_tags"]

    def test_compile_unknown_player_is_404(self):
        client = self._client()
        assert client.post("/api/players/Nobody/record/compile",
                           json={}).status_code == 404

    def test_compile_dry_run_compiles_without_storing(self):
        client = self._client()
        body = client.post("/api/players/Lyrie/record/compile",
                           json={"record": RICH}).get_json()
        assert "34-year-old" in body["compiled"]["base_description"]
        assert "smithing" in body["compiled"]["interest_tags"]
        assert body.get("applied") is not True
        assert client.get("/api/players/Lyrie/record").get_json() \
            ["record"] == {}

    def test_compile_dry_run_rejects_bad_fields(self):
        client = self._client()
        response = client.post(
            "/api/players/Lyrie/record/compile",
            json={"record": {"personality": {"fears": ["Not An Id"]}}})
        assert response.status_code == 400
        assert "ids" in response.get_json()["error"]

    def test_compile_beats_node_prose_in_state(self):
        """State reads node props first: the compile must write the node.

        A library character carries authored prose on the node. Applying
        only the Player would leave that prose shadowing the fresh
        compile in every `/api/state` payload (caught live on Arix).
        """
        app = create_app({"TESTING": True})
        world = app.world
        node = world.graph.get_node(world._player_node_id("Lyrie"))
        node.properties["base_description"] = "Hand prose on the node."
        client = app.test_client()
        client.put("/api/players/Lyrie/record", json={"record": RICH})
        preview = client.post("/api/players/Lyrie/record/compile",
                              json={}).get_json()
        assert preview.get("needs_confirm") is True
        assert "Hand prose on the node" in \
            preview["preview"]["base_description"]["current"]
        forced = client.post("/api/players/Lyrie/record/compile",
                             json={"force": True}).get_json()
        assert forced.get("applied") is True
        state = client.get("/api/state").get_json()
        assert "34-year-old" in state["players"]["Lyrie"]["base_description"]


# -- identity pick-lists (task-852) --

class TestIdentitySuggestions:
    """The Persona tab offers a pick-list next to each identity text input.

    The list is a suggestion only: the stored value stays a free string.
    """

    def _client(self):
        return create_app({"TESTING": True}).test_client()

    def test_every_pronoun_suggestion_is_one_the_engine_resolves(self):
        # An option the narration side cannot act on would be a readerless
        # choice: engine.pronouns falls back to tags/neutral for it.
        from engine.pronouns import _explicit_pronouns
        for option in ca.identity_suggestions()["pronouns"]:
            assert _explicit_pronouns({"identity": {"pronouns": option}}) \
                is not None, option

    def test_suggestions_only_name_identity_text_fields(self):
        sug = ca.identity_suggestions()
        assert set(sug) <= set(IDENTITY_FIELDS)
        assert "age" not in sug and "occupation" not in sug
        for field, values in sug.items():
            assert values, field
            assert len(values) == len(set(values)), field

    def test_species_suggestions_come_from_the_species_table(self):
        from engine.species import SPECIES_PROFILES
        assert ca.identity_suggestions()["species"] == sorted(SPECIES_PROFILES)

    def test_get_record_serves_the_suggestions(self):
        body = self._client().get("/api/players/Lyrie/record").get_json()
        assert body["suggestions"] == ca.identity_suggestions()

    def test_value_outside_the_list_is_stored_unchanged(self):
        client = self._client()
        custom = {"identity": {"pronouns": "xe/xem", "gender": "demiboy",
                               "sexuality": "omnisexual"}}
        assert client.put("/api/players/Lyrie/record",
                          json={"record": custom}).status_code == 200
        stored = client.get("/api/players/Lyrie/record").get_json()["record"]
        assert stored["identity"] == custom["identity"]

    def test_birthday_standardises_to_dd_mm_yyyy_and_rejects_invalid_dates(self):
        from engine.character_appearance import (
            StructuredError,
            normalize_birthday,
            parse_birthday,
            validate,
        )

        assert parse_birthday("14.03.1998") == (14, 3, 1998)
        assert normalize_birthday("5.3.1998") == "05.03.1998"
        assert normalize_birthday("14/03/1998") == "14.03.1998"
        assert normalize_birthday("1998-03-14") == "14.03.1998"
        assert validate({"identity": {"birthday": "5.3.1998"}})["identity"]["birthday"] == "05.03.1998"

        for bad in ("unknown", "32.01.1998", "14.13.1998", "14.03.98", "not-a-date"):
            with pytest.raises(StructuredError):
                validate({"identity": {"birthday": bad}})

