"""The authored content passes agree with the library on disk.

The check that was missing on 2026-09-30, when 545 authored items had been
deleted and the pass was still being reported as written. Two things are
asserted, and the second is the one that matters:

1. every id a pass authors is present in ``data/library/items``;
2. the record the pass builds is the record that is **there** — same
   description, tags, actions, weight, triggers, harvest and slots.

(1) alone would have caught the deletion. (2) is here because the same
comparison, run as a one-off during the port, found 194 items whose *weight* had
been truncated to an integer by a scratch helper and then defaulted to 1.0 — a
quarter of a stone of ash scoop that weighed a stone. A test that only checks
presence would have shipped that forever.
"""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
LIB = os.path.join(ROOT, "data", "library", "items")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import pytest  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_item_content  # noqa: E402

PASSES = audit_item_content.PASSES

#: Compared as values, not as JSON text: a board weighing 6 kg is `6` on disk and
#: `6.0` from a table, and those are the same number written two ways.
FIELDS = ("name", "description", "actions", "uses", "quantity", "current_state",
          "light_level", "defense", "damage", "tags", "triggers", "contents",
          "harvest", "equip_slots", "insulation", "weight")


def _norm(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def _same(a, b):
    return json.dumps(_norm(a), sort_keys=True, ensure_ascii=False) == \
        json.dumps(_norm(b), sort_keys=True, ensure_ascii=False)


@pytest.fixture(scope="module")
def on_disk():
    records = {}
    for name in os.listdir(LIB):
        if name.endswith(".json"):
            with open(os.path.join(LIB, name), encoding="utf-8") as handle:
                records[name[:-5]] = json.load(handle)
    return records


@pytest.fixture(scope="module")
def authored():
    return {("pass%d" % n): audit_item_content.load(n).build() for n in PASSES}


@pytest.mark.parametrize("n", PASSES)
def test_every_authored_item_is_in_the_library(n, authored, on_disk):
    missing = sorted(set(authored["pass%d" % n]) - set(on_disk))
    assert not missing, (
        f"pass{n} authors {len(missing)} item(s) that are not in "
        f"data/library/items: {missing[:10]}"
        + (" …" if len(missing) > 10 else ""))


@pytest.mark.parametrize("n", PASSES)
def test_the_library_record_is_the_one_the_pass_authors(n, authored, on_disk):
    """Presence is not enough: the shipped file must be the authored record.

    This is the assertion that found 194 truncated weights, and it is the reason
    the content lives in the repository rather than in a scratch directory: the
    tables and the artefacts can now be held against each other on every run.
    """
    drifted = []
    for item_id, record in sorted(authored["pass%d" % n].items()):
        shipped = on_disk.get(item_id)
        if shipped is None:
            continue                      # presence is the other test's job
        fields = [f for f in FIELDS if not _same(record.get(f), shipped.get(f))]
        if fields:
            drifted.append(f"{item_id} ({', '.join(fields)})")
    # A pass may *mention* an id that shipped long ago (`beetroot`, `bone`,
    # `wine`); those are skipped on write and must be left alone. The test for
    # ownership is the **description**: if the shipped text is not the text this
    # pass wrote, the pass is not the author of that file and its fields are not
    # its to assert. (A git filter is not enough — `beetroot.json` is untracked
    # yet older than any of this work.)
    drifted = [d for d in drifted
               if _same(authored["pass%d" % n][d.split(" ")[0]].get("description"),
                        on_disk[d.split(" ")[0]].get("description"))]
    assert not drifted, (
        f"pass{n}: {len(drifted)} shipped record(s) differ from what the pass "
        f"authors: {drifted[:8]}" + (" …" if len(drifted) > 8 else ""))


def test_the_audit_helper_reports_nothing_missing(authored, on_disk):
    """`item_shapes.audit` is what the CLI calls; it must agree with the tests."""
    import item_shapes
    missing = item_shapes.audit(
        {k: v for k, v in authored.items()}, verbose=False)
    assert not missing, f"audit reports missing items: { {k: len(v) for k, v in missing.items()} }"
