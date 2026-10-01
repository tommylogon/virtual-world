"""The way-property index must stay true to the engine.

This exists because the property set is copied by hand in four places and had already
drifted. `tools/way_property_index.py --check` is the gate; these tests pin the parts a
gate alone would not catch — that the declaration itself is well formed, that each
guarded list is actually found (a silently-empty extraction reads as "no drift"), and
that the generated page is current.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from way_properties import PROPERTIES, SPAWN_LISTS  # noqa: E402
import way_property_index as index  # noqa: E402


def _run(*flags):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "way_property_index.py"), *flags],
        capture_output=True, text=True, cwd=ROOT)


def test_every_list_is_actually_extracted():
    """A marker that no longer matches yields an empty set, which reads as no drift."""
    lists = index.collect_lists()
    for label, rel, _s, _e, _m in SPAWN_LISTS:
        assert lists[label], (
            f"{label} ({rel}) extracted nothing — the source markers moved. The gate "
            f"would pass silently."
        )


def test_each_list_carries_the_properties_it_is_known_to():
    """Pins the four real lists so a re-extraction cannot quietly return a subset."""
    lists = index.collect_lists()
    expected = {
        "engine/sync.py (mutable)": {"current_state", "see_through", "prevent_close",
                                     "requires", "max_size"},
        "routes/library_ops.py (library spawn)": {"current_state", "see_through",
                                                   "prevent_close", "requires"},
        "engine/effect_handlers/ways.py (trigger spawn)": {"see_through", "prevent_close",
                                                            "requires", "max_size",
                                                            "insulation"},
        "routes/library_ops.py (refresh)": {"see_through", "prevent_close", "max_size",
                                            "current_state"},
    }
    for label, keys in expected.items():
        got = lists[label]
        assert keys <= got, f"{label} is missing {keys - got}"


def test_declaration_has_no_duplicate_or_blank_names():
    names = [p.name for p in PROPERTIES]
    assert len(names) == len(set(names)), "duplicate property in the declaration"
    assert all(n and n == n.strip() for n in names)


def test_every_property_is_on_a_declared_axis():
    from way_properties import AXES
    for p in PROPERTIES:
        assert p.axis in AXES, f"{p.name} is on unknown axis {p.axis!r}"


def test_declared_values_cover_every_value_the_inspector_offers():
    """`broken` is offered by the State dropdown but is missing from WAY_STATES.

    Pinned here so the known gap cannot quietly become an undocumented behaviour, and
    so adding it to one place without the other fails visibly.
    """
    current_state = next(p for p in PROPERTIES if p.name == "current_state")
    assert "broken" in current_state.values
    assert current_state.caveat, "a known gap must carry a caveat explaining it"


def test_check_passes_on_the_current_tree():
    result = _run("--check")
    assert result.returncode == 0, (
        f"--check failed:\n{result.stdout}\n{result.stderr}\n"
        f"Run --update-baseline only if the drift is already known."
    )


def test_generated_page_is_current():
    """The page is generated; a stale one is the exact failure this tooling prevents."""
    assert index.PAGE.exists(), f"{index.PAGE} was never generated"
    expected = index.build_page()
    assert index.PAGE.read_text(encoding="utf-8") == expected, (
        f"{index.PAGE} is stale — run python tools/way_property_index.py --write"
    )


def test_baseline_only_contains_current_drift():
    """A resolved drift left in the baseline would mask a future regression of it."""
    if not index.BASELINE_PATH.exists():
        return
    recorded = {ln for ln in index.BASELINE_PATH.read_text(encoding="utf-8").splitlines()
                if ln.strip()}
    current = set(index.drift())
    assert not (recorded - current), (
        f"baseline lists resolved drift: {recorded - current}\n"
        f"Re-run --update-baseline"
    )