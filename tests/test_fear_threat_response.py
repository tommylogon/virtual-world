"""Fear produces an action, not just a vital (task-552).

The 3-day Kraktooth soak that prompted this task recorded **zero** threat
actions with five humans living inside a goblin camp, and the conclusion drawn
was that nothing in the simulation could represent "that is not mine". The
diagnosis was half right and the half it got wrong is what this file pins:

*Right*: the background tier never called ``engine/fear.py``. The mechanic
existed and nothing asked it, so zero was structural, not a low rate.

*Wrong*: the reason nobody would ever have been afraid even if something did
ask is that ``fear_sources`` matched only on the character's *graph node* tags
- and a character node is created bare (``Node(id=..., type="character",
name=...)``) on both the add and the load path, so it never carries ``tags``.
Every shipped character puts ``"goblin"`` in ``player.tags`` instead, which
nothing was reading. Authoring ``fear_tags: ["goblin"]`` would have done
nothing. See ``engine.fear.character_tags``.

So this file tests the two halves separately: the tag plumbing, and the pass
that turns a fear into a recorded ``threat:`` action.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from player import Player

from engine import fear as fear_mod
from engine.background_social import (
    FEAR_LINES,
    FEAR_REACTIONS,
    _fear_source_for,
    choose_fear_reaction,
    run_fear_pass,
)

CAMP = "Kraktooth Pit"
ELSEWHERE = "Waste Disposal"


def _world():
    world = create_app({"TESTING": True}).world
    world.time_per_tick_minutes = 1
    world.movement.add_area(Area(CAMP, "The chieftain's pit.", []))
    world.movement.add_area(Area(ELSEWHERE, "A hole in the ground.", []))
    return world


def _character(world, name, area=CAMP, tags=None, fears=None, background=True):
    """A background character, tagged the way the shipped data tags them."""
    p = Player(name)
    p.simulation_mode = "background" if background else "active"
    p.tags = list(tags or [])
    p.fear_tags = list(fears or [])
    world.add_player(p)
    world.set_player_area(name, area)
    return p


# ── the tag plumbing ──

class TestFearSourceDetection:

    def test_a_shipped_style_tag_is_enough(self):
        """`tags` is what the character data fills; it has to be read."""
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["female", "teen", "goblin"])

        source = fear_mod.fear_sources_for_character(
            world, human, world.player_manager.get_player("Grit"))

        assert source is not None
        assert source["name"] == "Grit"
        assert source["tags"] == ["goblin"]

    def test_the_graph_node_alone_would_never_have_matched(self):
        """Even if the character node is bare, fear_sources matches on player tags."""
        world = _world()
        _character(world, "Grit", tags=["goblin"])
        node = world.graph.get_node(world._player_node_id("Grit"))
        assert node is not None
        # Explicitly strip node tags to simulate a bare node
        node.properties["tags"] = []
        human = _character(world, "Fen", fears=["goblin"])
        source = fear_mod.fear_sources_for_character(
            world, human, world.player_manager.get_player("Grit"))
        assert source is not None
        assert source["name"] == "Grit"

    def test_trait_keys_still_count(self):
        world = _world()
        human = _character(world, "Fen", fears=["beast"])
        beast = _character(world, "Wolf")
        beast.traits["beast"] = {}
        assert fear_mod.fear_sources_for_character(
            world, human, beast) is not None

    def test_a_character_that_fears_nothing_is_never_frightened(self):
        world = _world()
        calm = _character(world, "Fen")
        _character(world, "Grit", tags=["goblin"])
        assert fear_mod.fear_sources_for_character(
            world, calm, world.player_manager.get_player("Grit")) is None

    def test_a_goblin_is_not_afraid_of_goblins(self):
        """The whole point of fear being character-relative (task-469)."""
        world = _world()
        _character(world, "Grit", tags=["goblin"])       # no fear_tags
        _character(world, "Snikk", tags=["goblin"])
        goblin = world.player_manager.get_player("Grit")
        assert fear_mod.fear_sources_for_character(
            world, goblin, world.player_manager.get_player("Snikk")) is None

    def test_someone_in_another_area_is_not_a_source(self):
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", area=ELSEWHERE, tags=["goblin"])
        assert fear_mod.fear_sources_for_character(
            world, human, world.player_manager.get_player("Grit")) is None

    def test_areas_cannot_be_a_fear_source_yet(self):
        """A second dead branch, recorded rather than papered over.

        ``engine.fear.fear_sources`` looks for area ``tags``, but ``Area`` has no
        tags field and ``add_area`` writes only ``description`` and
        ``environment`` - so the branch can never fire. Wiring it needs an area
        ``tags`` property, which is a data-model change (task-550 territory), not
        something task-552 should smuggle in. Asserted so the day someone adds
        area tags, this test is the one that has to change.
        """
        world = _world()
        human = _character(world, "Fen", fears=["haunted"])
        world.movement.add_area(Area("Haunted Wood", "It watches.", []))
        world.set_player_area("Fen", "Haunted Wood")

        node = world.graph.get_node(world.area_node_id("Haunted Wood"))
        assert not (node.properties or {}).get("tags")
        assert not [s for s in fear_mod.fear_sources(world, human)
                    if s["kind"] == "area"]

    def test_the_pair_helper_agrees_with_the_list_helper(self):
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        grit = _character(world, "Grit", tags=["goblin"])
        assert _fear_source_for(world, human, grit) is not None
        assert not _fear_source_for(world, grit, human)
        assert not _fear_source_for(world, human, None)


# ── fear moves someone ──

class TestFearProducesAnAction:

    def test_a_fear_records_a_threat_action(self):
        world = _world()
        _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])

        outcomes = run_fear_pass(world, tick=0)

        assert len(outcomes) == 1
        row = outcomes[0]
        assert row["actor"] == "Fen" and row["source"] == "Grit"
        assert row["reaction"] in FEAR_REACTIONS
        assert row["why"].startswith("threat:")

    def test_the_action_is_visible_not_just_a_vital(self):
        """Acceptance: a recorded, visible action, not a silent vital."""
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])

        row = run_fear_pass(world, tick=0)[0]

        assert row["line"], "a threat action with no line is a silent vital"
        assert "Grit" in row["line"]
        assert row["area"] == CAMP
        # and it is a real memory, not just a log line
        memories = [m for m in human.memories if "threat" in (m.get("tags") or [])]
        assert memories, "the fear left no memory"
        assert any("Grit" in (m.get("text") or "") for m in memories)

    def test_fear_applies_the_frightened_condition_with_its_source(self):
        world = _world()
        _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])

        run_fear_pass(world, tick=0)

        human = world.player_manager.get_player("Fen")
        assert human.has_condition("frightened")
        sources = [i.get("source") for i in human.conditions.get("frightened") or []]
        assert "Grit" in sources

    def test_fear_costs_social_and_spikes_afraid(self):
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        social_before = human.vitals["Social"]
        afraid_before = human.emotions_map().get("afraid", 0.0)

        run_fear_pass(world, tick=0)

        assert human.vitals["Social"] < social_before
        assert human.emotions_map().get("afraid", 0.0) > afraid_before

    def test_fear_costs_closeness_toward_the_source(self):
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        human.relationships["Grit"] = {"closeness": 20, "last_interaction_tick": 0,
                                       "interaction_count": 1}

        run_fear_pass(world, tick=0)

        assert world.player_manager.get_player("Fen").relationships["Grit"]["closeness"] < 20

    def test_every_reaction_has_a_line(self):
        assert set(FEAR_LINES) == set(FEAR_REACTIONS)
        for reaction, template in FEAR_LINES.items():
            assert template.format(source="Grit")

    def test_the_reaction_is_deterministic(self):
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        assert choose_fear_reaction(human, "Grit", 42) == \
            choose_fear_reaction(human, "Grit", 42)

    def test_the_reaction_varies_by_character(self):
        """A crowd of five must not flee in lockstep."""
        world = _world()
        picks = {choose_fear_reaction(_character(world, f"F{i}"), "Grit", 7)
                 for i in range(8)}
        assert len(picks) > 1

    def test_fear_does_not_re_log_every_tick(self):
        world = _world()
        _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])

        first = run_fear_pass(world, tick=0)
        second = run_fear_pass(world, tick=1)

        assert len(first) == 1
        assert second == [], "the same flight was logged on consecutive ticks"

    def test_a_goblin_camp_of_goblins_produces_nothing(self):
        """Nobody fears goblins, so a goblin camp is quiet. The honest result."""
        world = _world()
        for name in ("Grit", "Snikk", "Rukk"):
            _character(world, name, tags=["goblin"])
        assert run_fear_pass(world, tick=0) == []


# ── the social pass yields to fear ──

class TestFearPreemptsSocial:

    def test_a_character_does_not_chat_with_what_it_fears(self):
        from engine.background_social import perform
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        grit = _character(world, "Grit", tags=["goblin"])

        assert perform(world, human, grit, "", CAMP, 0) is None

    def test_sociability_toward_anyone_else_is_unaffected(self):
        from engine.background_social import perform
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        friend = _character(world, "Tam")

        assert perform(world, human, friend, "", CAMP, 0, action="chat") is not None

    def test_the_fearing_side_is_blocked_not_the_feared_side(self):
        """A goblin may still talk to the human it frightens."""
        from engine.background_social import perform
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        grit = _character(world, "Grit", tags=["goblin"])

        assert perform(world, grit, human, "", CAMP, 0, action="chat") is not None


# ── a fear ends when its source does (task-484) ───────────────────────────

class TestFearIsReleased:

    def _frightened_of(self, world, name, source):
        player = world.player_manager.get_player(name)
        return [i.get("source") for i in player.conditions.get("frightened") or []]

    def test_a_fear_ends_when_the_source_leaves(self):
        world = _world()
        _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        run_fear_pass(world, tick=0)
        assert self._frightened_of(world, "Fen", None) == ["Grit"]

        # Grit walks off to the waste disposal
        world.set_player_area("Grit", ELSEWHERE)
        fear_mod.release_absent_fears(world, world.player_manager.get_player("Fen"))

        assert self._frightened_of(world, "Fen", None) == []
        assert not world.player_manager.get_player("Fen").has_condition("frightened")

    def test_a_fear_survives_while_the_source_stays(self):
        world = _world()
        _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        run_fear_pass(world, tick=0)

        released = fear_mod.release_absent_fears(world,
                                                  world.player_manager.get_player("Fen"))

        assert released == []
        assert self._frightened_of(world, "Fen", None) == ["Grit"]

    def test_only_the_absent_source_is_released(self):
        """Two fears, one source leaves: the other fear must survive."""
        world = _world()
        human = _character(world, "Fen", fears=["goblin", "werewolf"])
        _character(world, "Grit", tags=["goblin"])
        _character(world, "Rulf", tags=["werewolf"])
        run_fear_pass(world, tick=0)
        # force both fears to exist as separate instances
        human.conditions["frightened"] = [
            {"source": "Grit", "source_type": "character", "duration": 30},
            {"source": "Rulf", "source_type": "character", "duration": 30},
        ]
        world.set_player_area("Rulf", ELSEWHERE)

        released = fear_mod.release_absent_fears(world, human)

        assert released == ["Rulf"]
        assert self._frightened_of(world, "Fen", None) == ["Grit"]

    def test_release_reports_what_it_released(self):
        world = _world()
        _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        run_fear_pass(world, tick=0)
        world.set_player_area("Grit", ELSEWHERE)

        assert fear_mod.release_absent_fears(
            world, world.player_manager.get_player("Fen")) == ["Grit"]

    def test_releasing_nothing_is_not_an_error(self):
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        assert fear_mod.release_absent_fears(world, human) == []
        assert fear_mod.release_absent_fears(world, _character(world, "Calm")) == []

    def test_the_gate_stops_gating_once_the_fear_is_released(self):
        """The point of the fix: the stuck flag stops refusing approaches."""
        from engine.conditions import frightened_block
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        run_fear_pass(world, tick=0)

        assert frightened_block(human, "character", source_name="Grit")

        world.set_player_area("Grit", ELSEWHERE)
        fear_mod.release_absent_fears(world, human)

        assert frightened_block(human, "character", source_name="Grit") is None

    def test_react_releases_as_well_as_applying(self):
        """One entry point, so detection and cleanup cannot disagree."""
        world = _world()
        human = _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        fear_mod.react(world, human)
        assert self._frightened_of(world, "Fen", None) == ["Grit"]

        world.set_player_area("Grit", ELSEWHERE)
        assert fear_mod.react(world, human) is None
        assert self._frightened_of(world, "Fen", None) == []

    def test_the_pass_releases_stale_fears_too(self):
        """The background pass must not leave a flag nothing will ever clear."""
        world = _world()
        _character(world, "Fen", fears=["goblin"])
        _character(world, "Grit", tags=["goblin"])
        run_fear_pass(world, tick=0)
        world.set_player_area("Grit", ELSEWHERE)

        run_fear_pass(world, tick=200)

        human = world.player_manager.get_player("Fen")
        assert not human.has_condition("frightened")


# ── real simulation state mutations (bug-594) ─────────────────────────────

class TestFearStateMutations:

    def test_flee_moves_npc_through_open_exit_away_from_threat(self):
        from graph import EDGE_IN
        world = _world()
        world.movement.connect_areas(CAMP, ELSEWHERE, "east", "west", state="open")
        human = _character(world, "Fen", area=CAMP, fears=["goblin"])
        _character(world, "Grit", area=CAMP, tags=["goblin"])

        outcomes = run_fear_pass(world, tick=0, reaction="flee")

        assert len(outcomes) == 1
        assert outcomes[0]["reaction"] == "flee"
        assert outcomes[0]["moved_to"] == ELSEWHERE
        assert human.current_area == ELSEWHERE
        pid = world._player_node_id("Fen")
        in_targets = [e.target for e in world.graph.get_edges_for_source(pid, EDGE_IN)]
        assert world.area_node_id(ELSEWHERE) in in_targets

    def test_flee_prefers_safe_exit_over_area_with_another_threat(self):
        world = _world()
        SAFE_ROOM = "Quiet Alcove"
        world.movement.add_area(Area(SAFE_ROOM, "A safe niche.", []))
        world.movement.connect_areas(CAMP, ELSEWHERE, "north", "south", state="open")
        world.movement.connect_areas(CAMP, SAFE_ROOM, "south", "north", state="open")
        human = _character(world, "Fen", area=CAMP, fears=["goblin"])
        _character(world, "Grit", area=CAMP, tags=["goblin"])
        _character(world, "Snikk", area=ELSEWHERE, tags=["goblin"])

        outcomes = run_fear_pass(world, tick=0, reaction="flee")

        assert len(outcomes) == 1
        assert human.current_area == SAFE_ROOM

    def test_hide_places_npc_into_hidden_state_with_cover_edge(self):
        from graph import Node, Edge, EDGE_IN
        world = _world()
        human = _character(world, "Fen", area=CAMP, fears=["goblin"])
        _character(world, "Grit", area=CAMP, tags=["goblin"])

        crate = Node(
            id="item_supply_crate",
            type="item",
            name="Supply Crate",
            properties={"tags": ["hideable", "furniture"], "description": "A wooden crate."},
        )
        world.graph.add_node(crate)
        world.graph.add_edge(Edge(source=crate.id, target=world.area_node_id(CAMP), type=EDGE_IN))

        assert human.hidden is False
        outcomes = run_fear_pass(world, tick=0, reaction="hide")

        assert len(outcomes) == 1
        assert outcomes[0]["reaction"] == "hide"
        assert outcomes[0]["cover"] == "item_supply_crate"
        assert human.hidden is True
        assert world.player_manager.is_visible("Fen") is False
        pid = world._player_node_id("Fen")
        hidden_edges = [
            e for e in world.graph.edges
            if e.type == "hidden" and e.target == "item_supply_crate" and e.source in (pid, "Fen")
        ]
        assert len(hidden_edges) == 1

    def test_hide_without_cover_falls_back_to_flee_or_freeze(self):
        from engine.background_social import is_frozen_by_fear
        # Case 1: exposed room with an open exit -> falls back to flee
        world = _world()
        world.movement.connect_areas(CAMP, ELSEWHERE, "east", "west", state="open")
        human = _character(world, "Fen", area=CAMP, fears=["goblin"])
        _character(world, "Grit", area=CAMP, tags=["goblin"])

        outcomes = run_fear_pass(world, tick=0, reaction="hide")
        assert len(outcomes) == 1
        assert outcomes[0]["reaction"] == "flee"
        assert outcomes[0].get("fallback_from") == "hide"
        assert human.current_area == ELSEWHERE
        assert human.hidden is False

        # Case 2: exposed room with no exits -> falls back to freeze
        world2 = _world()
        human2 = _character(world2, "Fen", area=CAMP, fears=["goblin"])
        _character(world2, "Grit", area=CAMP, tags=["goblin"])

        outcomes2 = run_fear_pass(world2, tick=0, reaction="hide")
        assert len(outcomes2) == 1
        assert outcomes2[0]["reaction"] == "freeze"
        assert outcomes2[0].get("fallback_from") == "hide"
        assert human2.hidden is False
        assert is_frozen_by_fear(human2, world2, tick=0) is True

    def test_freeze_pauses_schedule_and_travel_while_keeping_vitals_and_cooldown(self):
        from engine.background_simulation import BackgroundSimulation
        from engine.background_social import is_frozen_by_fear, FEAR_FREEZE_MINUTES

        world = _world()
        world.movement.connect_areas(CAMP, ELSEWHERE, "east", "west", state="open")
        human = _character(world, "Fen", area=CAMP, fears=["goblin"])
        human.schedule = [{"start": "00:00", "activity": "work", "area": ELSEWHERE}]
        _character(world, "Grit", area=CAMP, tags=["goblin"])
        social_before = human.vitals["Social"]

        outcomes = run_fear_pass(world, tick=0, reaction="freeze")

        assert len(outcomes) == 1
        assert outcomes[0]["reaction"] == "freeze"
        assert is_frozen_by_fear(human, world, tick=0) is True
        assert human.flags.get("frozen_by_fear") is True
        # Vitals and cooldown accounting stay intact
        assert human.vitals["Social"] < social_before
        assert getattr(human, "_fear_last_tick", None) == 0
        assert human.has_condition("frightened")

        # Schedule and travel are paused while frozen
        sim = BackgroundSimulation(world)
        assert sim._pursue_schedule(human) is False
        assert sim.step_toward_area(human, ELSEWHERE) is False
        sim.process_due()
        assert human.current_area == CAMP

        # Once the freeze duration expires and the threat is gone, schedule travel resumes
        world.set_player_area("Grit", "Nowhere")
        world.time_ticks = FEAR_FREEZE_MINUTES + 5
        assert is_frozen_by_fear(human, world) is False
        assert sim._pursue_schedule(human) is True
        assert human.current_area == ELSEWHERE

    def test_shout_emits_sound_and_notifies_adjacent_listeners(self):
        world = _world()
        world.movement.connect_areas(CAMP, ELSEWHERE, "east", "west", state="open")
        _character(world, "Fen", area=CAMP, fears=["goblin"])
        _character(world, "Grit", area=CAMP, tags=["goblin"])
        ally = _character(world, "Tam", area=ELSEWHERE)

        outcomes = run_fear_pass(world, tick=0, reaction="shout")

        assert len(outcomes) == 1
        assert outcomes[0]["reaction"] == "shout"
        assert ELSEWHERE in outcomes[0].get("heard_in", [])
        assert any(
            h.get("speaker") == "Fen" and h.get("speech_level") == "shout"
            for h in getattr(ally, "recent_hearing", [])
        )

    def test_background_soak_smoke_when_no_exits_or_hideable_items_exist(self):
        from engine.background_simulation import BackgroundSimulation

        world = _world()
        for i in range(4):
            _character(world, f"Human{i}", area=CAMP, fears=["goblin"])
        _character(world, "Grit", area=CAMP, tags=["goblin"])

        sim = BackgroundSimulation(world)
        for reaction in FEAR_REACTIONS:
            for p in world.player_manager.players.values():
                p._fear_last_tick = None
            rows = run_fear_pass(world, tick=world.time_ticks, reaction=reaction)
            assert len(rows) == 4
            sim.process_due()
            world.time_ticks += 1
