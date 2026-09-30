"""`tools/lint_library.py` — the dead-fear check.

`engine/fear.py::character_tags` builds what a character *presents* to somebody's
`fear_tags` out of their `tags`, their `traits` keys, and their graph node's
tags; `fear_sources` additionally reads the area's own tags and the tags of the
items the area holds. A fear tag outside that vocabulary cannot fire — the
character is never frightened and nothing says why, which is bug-552's failure
mode arriving through a different door.

These tests pin the *rules*, not the library's current contents (no library
character authors `fear_tags` at all today, so a content-agnostic test is the
only kind that can say anything yet).

The rules most likely to be got wrong, each pinned below:

1. The vocabulary spans **items, areas AND characters** — a fear of "goblin" is
   live because a *character* carries that tag. Checking items alone (the shape
   its sibling `dead_interests` uses) would report every inter-character fear
   as dead.
2. **Trait keys** are a fear source as well as `tags`, and they are a dict
   rather than a list, so they are missed by any tags-shaped scan.
3. It is a **warning, not an error**. The inspector's "Generate from
   Personality" is deliberately allowed to invent ids, so a fear for something
   that does not exist here yet is a legitimate authoring intent and must not
   fail the lint.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lint_library  # noqa: E402


def _character(name, tags=(), fears=(), traits=None):
    return {"name": name, "tags": list(tags), "fear_tags": list(fears),
            "traits": traits or {}}


def _entry(name, tags=()):
    return {"name": name, "tags": list(tags)}


def _warnings(items=None, characters=None, areas=None):
    report = lint_library.Report()
    lint_library.check_dead_fears(items or {}, characters or {}, areas or {}, report)
    return [message for check, message in report.warnings if check == "dead_fears"]


# ── the vocabulary spans every fear source ─────────────────────────────────


def test_a_fear_carried_by_a_character_is_live():
    characters = {
        "snarl": _character("Snarl", tags=["goblin"]),
        "farmer": _character("Farmer", fears=["goblin"]),
    }
    assert _warnings(characters=characters) == []


def test_a_fear_carried_by_an_item_is_live():
    items = {"spider": _entry("giant spider", tags=["spider"])}
    characters = {"farmer": _character("Farmer", fears=["spider"])}
    assert _warnings(items=items, characters=characters) == []


def test_a_fear_carried_by_an_area_is_live():
    areas = {"camp": _entry("goblin camp", tags=["ruins"])}
    characters = {"farmer": _character("Farmer", fears=["ruins"])}
    assert _warnings(characters=characters, areas=areas) == []


def test_a_fear_matched_only_by_a_trait_key_is_live():
    """character_tags unions trait keys, so 'guard' is live on a character whose
    traits dict carries it even though their tags list does not."""
    characters = {
        "captain": _character("Captain", tags=["human"], traits={"guard": True}),
        "farmer": _character("Farmer", fears=["guard"]),
    }
    assert _warnings(characters=characters) == []


# ── the negative case ──────────────────────────────────────────────────────


def test_a_fear_nothing_carries_is_reported():
    characters = {"farmer": _character("Farmer", fears=["wyrm"])}
    warnings = _warnings(characters=characters)
    assert len(warnings) == 1
    assert "characters/farmer" in warnings[0]
    assert "wyrm" in warnings[0]


def test_only_the_dead_ones_are_named():
    characters = {
        "snarl": _character("Snarl", tags=["goblin"]),
        "farmer": _character("Farmer", fears=["goblin", "wyrm", "the dark"]),
    }
    warnings = _warnings(characters=characters)
    assert len(warnings) == 1
    listed = warnings[0].split(": ")[-1]
    assert "wyrm" in listed and "the dark" in listed
    assert "goblin" not in listed, "the live fear is not named as dead"


def test_a_character_with_no_fears_is_never_reported():
    characters = {"farmer": _character("Farmer", fears=[])}
    assert _warnings(characters=characters) == []


def test_matching_is_case_insensitive():
    characters = {
        "snarl": _character("Snarl", tags=["Goblin"]),
        "farmer": _character("Farmer", fears=["GOBLIN"]),
    }
    assert _warnings(characters=characters) == []


# ── the level, and why it is not an error ──────────────────────────────────


def test_a_dead_fear_warns_but_does_not_fail_the_lint():
    characters = {"farmer": _character("Farmer", fears=["wyrm"])}
    report = lint_library.Report()
    lint_library.check_dead_fears({}, characters, {}, report)
    assert report.errors == [], "an aspirational fear must not fail the lint"
    assert len(report.warnings) == 1


def test_the_check_is_registered_as_a_warning_tier_check():
    assert "dead_fears" in lint_library.WARNING_CHECKS
    assert "dead_fears" not in lint_library.ERROR_CHECKS
    assert "dead_fears" in lint_library.ALL_CHECKS


def test_the_check_is_reachable_by_name_on_the_command_line():
    """`--check dead_interests` is how every other check is selected; a check the
    runner's argparse choices omit cannot be run on its own at all."""
    assert "dead_fears" in lint_library.CHECKS
    assert lint_library.CHECKS["dead_fears"].__code__.co_argcount == 2


def test_the_real_library_has_no_dead_fears_to_report():
    """The shipped library authors no fear_tags at all, so this must stay quiet —
    a lint that cries wolf on day one gets ignored."""
    lib = ROOT / "data" / "library"
    items = lint_library.load_registry(str(lib), "items")
    characters = lint_library.load_registry(str(lib), "characters")
    areas = lint_library.load_registry(str(lib), "areas")
    authored = sum(len(c.get("fear_tags") or []) for c in characters.values())
    if authored:
        return  # a content pass landed; the rules above already cover it
    assert _warnings(items=items, characters=characters, areas=areas) == []
