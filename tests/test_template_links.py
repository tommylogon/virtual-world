"""Template links (task-289 + task-317 decided as one).

The two cards describe the same remaining work from two directions, so this file
tests the shared contract rather than either card's half. Three things were
genuinely broken and are pinned here:

1. **Resolution drifted.** Four handlers, four different ways of guessing which
   template a node refers to, so the same operation on four node types could
   land on three different templates or none.
2. **There was no unlink.** Any of the four types could be re-synced and none
   could be unlinked, so "this copy is mine now" was unexpressible.
3. **A guessed sync left the node reading as unlinked** — it synced from a
   template and then did not record it, so the link was invisible and
   unbreakable while plainly existing.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine import sync


class _Node:
    """The slice of Node that sync.py actually reads."""

    def __init__(self, id, type, name="", properties=None):
        self.id = id
        self.type = type
        self.name = name
        self.properties = dict(properties or {})


class TestTheContract:
    def test_every_linkable_type_has_a_spec(self):
        for t in ("item", "way", "area", "character"):
            assert sync.spec_for(t) is not None, t

    def test_a_type_with_no_library_has_no_spec(self):
        assert sync.spec_for("trigger") is None
        assert sync.spec_for("") is None
        assert sync.spec_for(None) is None

    def test_identity_and_runtime_state_can_never_be_synced(self):
        """The invariant, as a property rather than a habit: if a whitelist
        ever grows an id or a spatial field, this fails."""
        for t, spec in sync.SPECS.items():
            leaked = set(spec.mutable) & sync.NEVER_SYNCED
            assert not leaked, f"{t} would sync identity/runtime state: {leaked}"

    def test_current_state_is_a_named_open_question_not_a_silent_inconsistency(self):
        """task-289 says never sync it; items and ways both do. Rather than
        quietly pick a side, the disagreement is recorded in sync.py and pinned
        here so it cannot drift unnoticed."""
        assert "current_state" not in sync.NEVER_SYNCED, (
            "if current_state was ruled never-syncable, remove it from the item "
            "and way whitelists too, not just from NEVER_SYNCED"
        )
        assert "current_state" in sync.SPECS["way"].mutable
        assert "current_state" in sync.SPECS["item"].mutable

    def test_the_link_marker_is_never_itself_a_synced_field(self):
        for spec in sync.SPECS.values():
            assert sync.LINK_FIELD not in spec.mutable
            assert sync.LOCKED_FIELD not in spec.mutable

    def test_each_type_names_its_own_registry(self):
        assert sync.SPECS["item"].registry == "items.json"
        assert sync.SPECS["way"].registry == "ways.json"
        assert sync.SPECS["area"].registry == "areas.json"
        assert sync.SPECS["character"].registry == "characters.json"

    def test_a_character_syncs_onto_its_player_not_the_node(self):
        """Documents a real asymmetry rather than hiding it: a character's
        template fields are Player fields, the other three are node properties."""
        assert sync.SPECS["character"].target == "player"
        for t in ("item", "way", "area"):
            assert sync.SPECS[t].target == "node"


class TestResolution:
    def test_explicit_beats_everything(self):
        n = _Node("n", "item", properties={"library_id": "existing"})
        assert sync.resolve_template_id(n, "explicit") == "explicit"

    def test_the_link_beats_a_guess(self):
        n = _Node("n", "character", name="Guard", properties={"library_id": "town_guard"})
        assert sync.resolve_template_id(n) == "town_guard"

    def test_an_item_never_guesses(self):
        """A placed copy's library key is opaque; a name-derived guess would
        silently attach it to a template the author never chose."""
        n = _Node("item_1", "item", name="Brass Key", properties={})
        assert sync.resolve_template_id(n) == ""

    def test_a_way_guesses_from_its_name(self):
        n = _Node("way_1", "way", name="Vault Door", properties={})
        assert sync.resolve_template_id(n) == "vault_door"

    def test_an_area_guesses_from_its_node_id(self):
        n = _Node("area_ruined_hall", "area", name="Ruined Hall", properties={})
        assert sync.resolve_template_id(n) == "ruined_hall"

    def test_an_area_falls_back_to_its_name_when_the_prefix_says_nothing(self):
        n = _Node("area_", "area", name="Ruined Hall", properties={})
        assert sync.resolve_template_id(n) == "ruined_hall"

    def test_a_character_guesses_from_its_display_name(self):
        n = _Node("n", "character", name="Kaelen Voss", properties={})
        assert sync.resolve_template_id(n) == "Kaelen Voss"

    def test_whitespace_and_case_are_normalised(self):
        n = _Node("n", "item", properties={"library_id": "  brass_key  "})
        assert sync.linked_template_id(n) == "brass_key"
        assert sync.is_linked(n) is True

    def test_an_empty_link_is_standalone(self):
        for value in ({}, {"library_id": ""}, {"library_id": None}, {"library_id": "   "}):
            n = _Node("n", "item", properties=value)
            assert sync.is_linked(n) is False


class TestLocking:
    def test_locked_fields_are_read_as_a_set(self):
        n = _Node("n", "item", properties={"locked_fields": ["description", "weight"]})
        assert sync.locked_fields(n) == {"description", "weight"}

    def test_absent_locked_fields_is_not_an_error(self):
        assert sync.locked_fields(_Node("n", "item")) == set()


class TestBreakLink:
    def test_breaking_removes_the_link_and_nothing_else(self):
        n = _Node("n", "item", name="Brass Key",
                  properties={"library_id": "brass_key", "description": "A small brass key.",
                              "weight": 0.05})
        report = sync.break_template_link(n)
        assert report["was_linked"] is True and report["changed"] is True
        assert "library_id" not in n.properties
        # The whole point: the author's copy is untouched.
        assert n.properties["description"] == "A small brass key."
        assert n.properties["weight"] == 0.05

    def test_breaking_remembers_where_it_came_from(self):
        n = _Node("n", "area", properties={"library_id": "ruined_hall"})
        sync.break_template_link(n)
        assert n.properties[sync.BROKEN_FIELD] == "ruined_hall"

    def test_breaking_an_unlinked_node_says_so_and_changes_nothing(self):
        n = _Node("n", "way", properties={"description": "A door."})
        report = sync.break_template_link(n)
        assert report["was_linked"] is False and report["changed"] is False
        assert n.properties == {"description": "A door."}

    def test_breaking_does_not_silently_lock_the_node(self):
        """A break changes no data. Auto-locking every mutable field would both
        alter the node and make a later deliberate re-link + sync do nothing,
        which reads as a broken button."""
        n = _Node("n", "item", properties={"library_id": "brass_key", "description": "d"})
        sync.break_template_link(n)
        assert "locked_fields" not in n.properties

    def test_a_broken_node_no_longer_resolves_a_template(self):
        n = _Node("n", "area", name="Ruined Hall", properties={"library_id": "ruined_hall"})
        assert sync.resolve_template_id(n) == "ruined_hall"
        sync.break_template_link(n)
        # A way or character would still *guess* here by design; an area's guess
        # comes from its node id, which is not a template name.
        assert sync.is_linked(n) is False

    def test_relinking_clears_the_break_marker(self):
        n = _Node("n", "item", properties={"library_id": "brass_key"})
        sync.break_template_link(n)
        sync.link(n, "iron_key")
        assert n.properties["library_id"] == "iron_key"
        assert sync.BROKEN_FIELD not in n.properties


class TestChangedFields:
    def test_only_real_moves_are_reported(self):
        before = {"description": "a", "weight": 1.0, "tags": ["x"]}
        after = {"description": "a", "weight": 2.0, "tags": ["x"]}
        assert sync.changed_fields(before, after) == {"weight": {"from": 1.0, "to": 2.0}}

    def test_a_re_sync_that_changes_nothing_reports_nothing(self):
        same = {"description": "a", "weight": 1.0}
        assert sync.changed_fields(same, dict(same)) == {}

    def test_a_field_appearing_or_disappearing_counts(self):
        assert "new" in sync.changed_fields({}, {"new": 1})
        assert "gone" in sync.changed_fields({"gone": 1}, {})
