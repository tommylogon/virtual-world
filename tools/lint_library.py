"""Library lint: scan data/library/ JSON files for data-quality problems.

Checks (errors exit 1):
  1. dead_interests   — character interest_tags matching zero item tags
  2. missing_slots    — items tagged clothing/armor without equip_slots
  3. tag_case_drift   — same tag in multiple casings within a registry
  5. broken_contents  — item contents referencing missing library ids
  7. unauthored_consumables — edible/drinkable items whose consume trigger
     restores nothing (task-506)
  8. resource_pools   — pooled-resource nodes authored so they cannot be
     harvested correctly (task-504)
Warnings (exit 0):
  4. singleton_tags   — item tags appearing on exactly one item
  6. area_tag_gaps    — library areas with no tags
  9. dead_fears       — character fear_tags that no item, area, character or
     trait key carries, so engine/fear.py can never match them
 10. biome_coverage   — a biome's resource_distribution entry whose tags match
      no library item, so a search there would turn up nothing (task-573)
 11. stray_library_dirs — a data/library/ subdirectory that is not a registry
      type, so a runtime save parked there is invisible (not read, not reported)
      rather than mistaken for authored content (task-645)

Usage:
  python tools/lint_library.py                  # all checks against default data dir
  python tools/lint_library.py --check dead_interests --check missing_slots
  python tools/lint_library.py --data-dir path/to/library   # for fixture testing

Exit code: 1 if any ERROR-level check fires, else 0.
"""

import argparse
import glob
import json
import os
import re
import sys

DEFAULT_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "library")

#: The registries this check reports on. Every registry is keyed by filename and
#: so is equally subject to the hazard; this tuple is the set the check has always
#: covered, kept explicit so widening it is a deliberate change to the output
#: rather than an accident. `routes/library_ops.REGISTRY_TYPES` is the canonical
#: list of registry types (see `_known_registry_types`).
_CHARSET_REGISTRIES = ("items", "characters", "areas", "tags", "ways")

ERROR_CHECKS = ("dead_interests", "missing_slots", "tag_case_drift", "broken_contents",
                "unauthored_consumables", "resource_pools")
WARNING_CHECKS = ("singleton_tags", "area_tag_gaps", "dead_fears", "tag_id_charset",
"duplicate_area_names", "biome_coverage", "stray_library_dirs")
ALL_CHECKS = ERROR_CHECKS + WARNING_CHECKS

#: Items that carry `food`/`drink` (or an `eat`/`drink` action) because they sit
#: *near* food rather than being it — a barrel, a platter, a kettle. They are
#: fixtures, and the task-506 authoring pass un-tags them instead of authoring a
#: nonsense `on_eat`. Listed here so the lint does not demand the impossible and
#: so a new one of these is a deliberate, visible line rather than a silent tag.
#:
#: This list is the honest exception set. It exists because
#: `ConsumeActionsMixin._is_valid_for` accepts a consumable by *tag alone*, so a
#: mistagged fixture is not a cosmetic problem: a background character will
#: cheerfully eat the barrel.
FOOD_ADJACENT_FIXTURES = frozenset({
    "apple_tree", "barrel", "boxed_shell_cases", "bread_plate", "candy_jar",
    "cauldron", "cheese_shred", "coffee_grinder", "dairy_case", "flour",
    "hanging_dried_meats", "meat_hooks", "mystery_cream_sauce",
    "seasoned_beef_pan", "spice_rack", "baja_blast_cup", "taco_bell_drink_cup",
    "teacup", "thermos", "water_carboy", "water_glass", "water_jug",
    "wine_case", "wine_cask", "frozen_berries_7dtx",
})


def load_registry(lib_dir, name):
    pattern = os.path.join(lib_dir, name, "*.json")
    entries = {}
    for path in sorted(glob.glob(pattern)):
        file_id = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, "r", encoding="utf-8") as handle:
                entries[file_id] = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"ERROR {name}/{file_id}: unparseable JSON ({exc})")
    return entries


def check_stray_library_dirs(lib_dir, report):
    """A ``data/library/`` subdirectory that is not a registry type (task-645).

    ``data/library/`` is the authored tree, but it can accumulate a directory
    that is not a registry — ``rooms/`` held 526 KB of stale *save state* for a
    while. Nothing reads it, so nothing reports it: the only signal it ever
    produced was a 400 on ``GET /api/library/rooms``. This makes the stray
    directory visible (a warning, exit 0) so the set cannot grow unnoticed, and
    leaves the decision to remove it to whoever owns the migration.

    Hidden directories (``_``-prefixed) are ignored: that is the convention for
    deliberately parked non-content.
    """
    known = _known_registry_types()
    if not known or not os.path.isdir(lib_dir):
        return
    strays = sorted(
        name for name in os.listdir(lib_dir)
        if os.path.isdir(os.path.join(lib_dir, name))
        and not name.startswith("_")
        and name not in known
    )
    if strays:
        report.warn("stray_library_dirs",
                    f"data/library/ has {len(strays)} directory(ies) that are not registry "
                    f"types and nothing reads (runtime saves parked in the authored tree?): "
                    f"{', '.join(strays)}")


def _known_registry_types():
    """The canonical registry list, owned by the library API.

    Imported lazily so a hard dependency on Flask is not created for the one
    check that needs it; if it cannot be imported the check stays silent rather
    than guessing at the list.
    """
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from routes.library_ops import REGISTRY_TYPES
        return set(REGISTRY_TYPES)
    except Exception:
        return set()


def load_biomes(lib_dir):
    """Load ``<data>/worldpainter/biomes.json`` for the biome-coverage check.

    The file lives beside the library (``data/worldpainter``), not inside it, so
    a fixture ``--data-dir`` still resolves a sibling ``worldpainter/``.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(lib_dir)), "worldpainter", "biomes.json")
    if not os.path.isfile(path):
        return {}
    try:
        # utf-8-sig, matching engine/biomes.py: the engine reads this same file
        # and the two must not disagree about whether it is readable. The plain
        # codec hands json a stray U+FEFF on a BOM'd file, and the check then
        # silently reports nothing.
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"ERROR worldpainter/biomes.json: unparseable JSON ({exc})")
        return {}


def content_ref_id(ref):
    """Match routes/library_routes._content_ref_id: string or {id: ...}."""
    if isinstance(ref, str):
        return ref.strip() or None
    if isinstance(ref, dict):
        return ref.get("id") or None
    return None


def check_dead_interests(items, characters, report):
    """Character interest tags that match no item tag (case-insensitive)."""
    item_tag_vocab = set()
    for item in items.values():
        for tag in item.get("tags", []):
            item_tag_vocab.add(str(tag).strip().lower())

    for char_id, char in sorted(characters.items()):
        interests = char.get("interest_tags") or []
        dead = [t for t in interests if str(t).strip().lower() not in item_tag_vocab]
        if dead and interests:
            report.error("dead_interests",
                         f"characters/{char_id}: dead interest tags: {', '.join(dead)}")


def check_dead_fears(items, characters, areas, report):
    """Character fear tags that match nothing any fear source could carry.

    `engine/fear.py::character_tags` builds what a character *presents* to
    somebody's `fear_tags` out of their `tags`, their `traits` keys, and their
    graph node's tags; `fear_sources` additionally reads the area's own tags and
    the tags of the items the area holds. So the vocabulary a fear can possibly
    match is every tag on every item, area and character in the library, plus
    every trait key.

    A tag outside that set cannot fire. The character is simply never
    frightened and nothing says why — bug-552's failure mode ("`fear_tags:
    ["goblin"]` did nothing") arriving through a different door, and the one the
    inspector's "Generate from Personality" can now walk through, since it is
    deliberately allowed to invent ids.

    **A warning, not an error**, unlike its sibling `dead_interests`. A fear for
    something that does not exist here yet — "afraid of dragons" — is a
    legitimate authoring intent that the generator is explicitly told it may
    produce. Name it so an author can confirm it was deliberate; do not fail the
    lint over it.
    """
    vocab = set()

    def add(entry):
        for tag in entry.get("tags") or []:
            low = str(tag).strip().lower()
            if low:
                vocab.add(low)

    for registry in (items, areas, characters):
        for entry in registry.values():
            if isinstance(entry, dict):
                add(entry)
    # Trait keys are a fear source too (character_tags unions them), and they
    # are the one tag carrier that is a dict rather than a list.
    for character in characters.values():
        traits = character.get("traits") if isinstance(character, dict) else None
        if isinstance(traits, dict):
            vocab.update(str(k).strip().lower() for k in traits if str(k).strip())

    for char_id, char in sorted(characters.items()):
        fears = char.get("fear_tags") or []
        if not fears:
            continue
        dead = [t for t in fears if str(t).strip().lower() not in vocab]
        if dead:
            report.warn("dead_fears",
                        f"characters/{char_id}: fear tags nothing in the library carries, so they "
                        f"can never fire: {', '.join(dead)}")


def check_missing_slots(items, report):
    """Items tagged clothing/armor must declare equip_slots."""
    for item_id, item in sorted(items.items()):
        tags = {str(t).strip().lower() for t in item.get("tags", [])}
        if ("clothing" in tags or "armor" in tags) and not (item.get("equip_slots") or []):
            report.error("missing_slots", f"items/{item_id}: wearable but equip_slots empty")


def _case_drift(entries, get_tags, label, report):
    casing_map = {}
    for entry_id, entry in sorted(entries.items()):
        for tag in get_tags(entry):
            low = str(tag).strip().lower()
            if not low:
                continue
            casing_map.setdefault(low, {})
            casing_map[low].setdefault(str(tag), []).append(entry_id)
    for low, variants in sorted(casing_map.items()):
        if len(variants) > 1:
            detail = "; ".join(f"'{v}' on {label}/{', '.join(ids)}" for v, ids in sorted(variants.items()))
            report.error("tag_case_drift", f"{low}: mixed casing — {detail}")


def check_broken_contents(items, report):
    """Item contents referencing library item ids that do not exist."""
    known_ids = set(items.keys())
    # Library filenames may differ from the 'id' field; accept both.
    for entry_id, entry in sorted(items.items()):
        if isinstance(entry, dict) and entry.get("id"):
            known_ids.add(entry["id"])
    for item_id, item in sorted(items.items()):
        refs = item.get("contents") or []
        for ref in refs:
            child_id = content_ref_id(ref)
            if child_id and child_id not in known_ids:
                report.error("broken_contents",
                             f"items/{item_id}: contents references missing library item '{child_id}'")


def check_unauthored_consumables(items, report):
    """Edible/drinkable items whose consume trigger restores nothing (task-506).

    `ConsumeActionsMixin._is_valid_for` accepts a consumable by *tag alone*, and
    `BackgroundSimulation._consume_here` used to fall back to a hardcoded
    `MEAL_RESTORE`/`DRINK_RESTORE` when an item authored nothing — so a tag was
    enough to make an item edible and a hardcoded number was enough to make it
    nourishing. That fallback is the thing being retired, and this check is what
    stops it creeping back: an item that claims to be food and restores nothing
    is either a data bug or a fixture that has been mistagged.

    Two shapes are accepted, because both exist in the data: the modern
    `effects: [{type, params}]` list and the older flat
    `effect_type`/`effect_params` pair. `trigger_type` may be a string **or a
    list** (`apple.json` has `["on_eat"]`) — missing that is how 64 items came to
    look authored when they were not.

    Hunger and Thirst are *drives*: they fill upward, so relief is a **negative**
    `adjust_vital` amount. Checking the sign the other way round reports every
    correctly-authored item as broken. The **stat must match the drive being
    relieved** — an `on_eat` whose only `adjust_vital` is `Sanity -10` is not a
    meal, and accepting it would leave the item starving with a green lint.
    """
    drive_for = {"on_eat": "hunger", "on_drink": "thirst"}
    for item_id, item in sorted(items.items()):
        if not isinstance(item, dict):
            continue
        tags = {str(t).strip().lower() for t in (item.get("tags") or [])}
        actions = item.get("actions") or []
        if isinstance(actions, str):
            actions = [a.strip() for a in actions.split(",")]
        actions = {str(a).strip().lower() for a in actions}
        eatable = "food" in tags or "eat" in actions
        drinkable = "drink" in tags or "drink" in actions
        if not (eatable or drinkable):
            continue
        if item_id in FOOD_ADJACENT_FIXTURES:
            continue  # deliberately un-tagged rather than authored; see the constant

        relieved = {"on_eat": False, "on_drink": False}
        for trigger in (item.get("triggers") or []):
            if not isinstance(trigger, dict):
                continue
            raw = trigger.get("trigger_type")
            types = ([str(t) for t in raw] if isinstance(raw, list)
                     else [str(raw)] if raw else [])
            effects = trigger.get("effects")
            if not effects and trigger.get("effect_type"):
                effects = [{"type": trigger.get("effect_type"),
                            "params": trigger.get("effect_params") or {}}]
            for effect in effects or []:
                if not isinstance(effect, dict) or str(effect.get("type")) != "adjust_vital":
                    continue
                params = effect.get("params") or {}
                stat = str(params.get("stat", "")).strip().lower()
                try:
                    amount = float(params.get("amount"))
                except (TypeError, ValueError):
                    continue
                if amount >= 0:
                    continue  # a drive is relieved downward, never upward
                for trigger_type in types:
                    if trigger_type in relieved and stat == drive_for[trigger_type]:
                        relieved[trigger_type] = True

        missing = []
        if eatable and not relieved["on_eat"]:
            missing.append("on_eat -> adjust_vital Hunger (negative)")
        if drinkable and not relieved["on_drink"]:
            missing.append("on_drink -> adjust_vital Thirst (negative)")
        if missing:
            report.error("unauthored_consumables",
                         f"items/{item_id}: claims to be consumable but authors no "
                         f"{'; '.join(missing)}")


def check_tag_id_charset(registries, report):
    """Registry ids outside ``[a-z0-9_]`` -- task-601.

    ``load_registry`` keys every entry by its **filename verbatim**
    (``routes/helpers.py``), so an id is whatever the file is called. Both forms
    resolve by their exact id, but only the exact form: ``blackwood_mansion``
    does NOT find ``blackwood mansion.json``. An author writing the conventional
    form gets a silent miss, and ``tag_case_drift`` cannot see it because that
    check only compares casing, not separators.

    Reported as a warning rather than an error: renaming a spaced id is a
    cross-registry migration (task-646), not a lint fix. The point of the check
    is to stop the set growing silently. As of 2026-10-02 the 15 spaced **tag**
    ids and the ``hidden door``/``hidden_door`` collision are resolved (task-646);
    the remaining offenders are the 37 characters and one item owned by the
    character/item library lane.
    """
    for name, entries in (registries or {}).items():
        offenders = [k for k in entries if not re.match(r"^[a-z0-9_]+$", str(k))]
        if not offenders:
            continue
        detail = ", ".join(sorted(offenders))
        report.warn("tag_id_charset",
                    f"{name}: {len(offenders)} id(s) outside [a-z0-9_] do not resolve "
                    f"by their snake_case form: {detail}")
        # Collision: two ids that normalise to the same key.
        seen = {}
        for k in entries:
            norm = re.sub(r"[^a-z0-9]+", "_", str(k).lower()).strip("_")
            seen.setdefault(norm, []).append(str(k))
        for norm, group in sorted(seen.items()):
            if len(group) > 1:
                report.warn("tag_id_charset",
                            f"{name}: normalising would MERGE {group} into '{norm}' -- "
                            f"decide whether they are the same tag before renaming")


def check_singleton_tags(items, report):
    """Item tags appearing on exactly one item — typo or under-connected."""
    counts = {}
    owner = {}
    for item_id, item in items.items():
        for tag in set(str(t).strip().lower() for t in item.get("tags", [])):
            if not tag:
                continue
            counts[tag] = counts.get(tag, 0) + 1
            owner.setdefault(tag, []).append(item_id)
    singles = [t for t in sorted(counts) if counts[t] == 1]
    if singles:
        detail = ", ".join(f"{t} (items/{owner[t][0]})" for t in singles)
        report.warn("singleton_tags", f"{len(singles)} single-use tags: {detail}")


def check_resource_pools(items, report):
    """Pooled resource nodes (task-504) must declare a yield that exists.

    A pool is one node standing for many of a kind in the world, emptied by
    taking from it. Three ways to author one wrong, all silent at runtime:
    a ``quantity`` with no ``harvest`` spec (takeable whole, which is the bug
    the model exists to fix), a ``harvest`` naming a library id that is not
    there (taking yields nothing), and a ``harvest`` yielding the pool itself.
    """
    for item_id, item in sorted(items.items()):
        harvest = item.get("harvest")
        quantity = item.get("quantity")

        if isinstance(harvest, dict):
            yield_id = content_ref_id(harvest.get("item"))
            if not yield_id:
                report.error("resource_pools", f"items/{item_id}: harvest spec names no item")
            elif yield_id == item_id:
                report.error("resource_pools",
                             f"items/{item_id}: harvest yields itself — that is an infinite pool")
            elif yield_id not in items:
                report.error("resource_pools",
                             f"items/{item_id}: harvest yields '{yield_id}', which is not in the library")
            if harvest.get("size") is not None:
                try:
                    if int(harvest["size"]) < 1:
                        raise ValueError
                except (TypeError, ValueError):
                    report.error("resource_pools",
                                 f"items/{item_id}: harvest size must be a positive whole number")
            if "quantity" not in item:
                report.warn("resource_pools",
                            f"items/{item_id}: harvest spec but no quantity — it will pool exactly one")
            continue

        if quantity is not None and not isinstance(harvest, dict):
            report.error("resource_pools",
                         f"items/{item_id}: quantity {quantity!r} with no harvest spec — "
                         f"it would be takeable whole")
        elif quantity is not None:
            report.error("resource_pools",
                         f"items/{item_id}: harvest must be an object, got {type(harvest).__name__}")


def check_duplicate_area_names(areas, report):
    """Library areas sharing a display name (task-439).

    A duplicate name is legal — ids are the identity — but a name-only lookup
    then resolves by rule rather than by intent, so the author should confirm it
    was deliberate. Seeds the duplicate-name diagnostic the library needs before
    a decomposed world ships many "Hollow"s.
    """
    by_name = {}
    for area_id, area in areas.items():
        if not isinstance(area, dict):
            continue
        name = str(area.get("name") or area_id).strip().lower()
        by_name.setdefault(name, []).append(area_id)
    for name, ids in sorted(by_name.items()):
        if len(ids) > 1:
            report.warn("duplicate_area_names",
                        f"areas share display name '{name}': {', '.join(sorted(ids))}")


def check_biome_coverage(items, biomes_data, report):
    """A biome's resource_distribution must resolve to a library item (task-573).

    task-569's consumer picks a find by tag intersection, the way
    ``engine/foraging.py::_pick_item`` does: an entry whose tags match no item
    yields nothing at all. Nothing reports that today, so a biome can be painted
    as forageable and silently produce an empty search.

    The rule is the consumer's: ``engine/foraging.py::_pick_item`` scores every
    item that shares a tag with the entry, and only then prefers the
    ``forage``-tagged subset of *those* matches when that subset is non-empty.
    So it narrows the candidate pool but never turns a non-empty match set into
    nothing -- an entry matching only an untagged item is still found. The gap
    condition is therefore a plain empty intersection, and intersecting a global
    ``forage`` set here would report entries the engine happily spawns.

    A warning, not an error -- coverage can legitimately be authored after the
    biome, and the count is the point.
    """
    tag_index = {}
    for item_id, item in items.items():
        if not isinstance(item, dict):
            continue
        tags = item.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        for tag in tags:
            low = str(tag).strip().lower()
            if low:
                tag_index.setdefault(low, []).append(item_id)

    for biome_id, entries in sorted((biomes_data.get("resource_distribution") or {}).items()):
        dead = []
        for entry in entries:
            etags = {str(t).strip().lower() for t in (entry.get("tags") or [])}
            hits = set()
            for tag in etags:
                hits.update(tag_index.get(tag, []))
            if not hits:
                dead.append("/".join(sorted(etags)))
        if dead:
            report.warn("biome_coverage",
                        f"biomes/{biome_id}: resource_distribution entries resolve to no "
                        f"library item, so a search turns up nothing: {', '.join(dead)}")


def check_area_tag_gaps(areas, report):
    """Library areas carrying no tags at all (informational)."""
    untagged = [area_id for area_id, area in sorted(areas.items())
                if not (area.get("tags") or [])]
    if untagged:
        report.warn("area_tag_gaps",
                    f"{len(untagged)} areas have no tags: {', '.join(untagged)}")


CHECKS = {
    "dead_interests": lambda ctx, r: check_dead_interests(ctx["items"], ctx["characters"], r),
    "dead_fears": lambda ctx, r: check_dead_fears(ctx["items"], ctx["characters"], ctx["areas"], r),
    "missing_slots": lambda ctx, r: check_missing_slots(ctx["items"], r),
    "tag_case_drift": lambda ctx, r: (
        _case_drift(ctx["items"], lambda e: e.get("tags", []), "items", r),
        _case_drift(ctx["areas"], lambda e: e.get("tags", []), "areas", r),
    ),
    "broken_contents": lambda ctx, r: check_broken_contents(ctx["items"], r),
    "unauthored_consumables": lambda ctx, r: check_unauthored_consumables(ctx["items"], r),
    "resource_pools": lambda ctx, r: check_resource_pools(ctx["items"], r),
    "singleton_tags": lambda ctx, r: check_singleton_tags(ctx["items"], r),
    # Explicit registry keys: the context also carries `biomes` (a taxonomy dict)
    # and `lib_dir` (a string), and passing the whole context made this check
    # iterate a path string character by character.
    "tag_id_charset": lambda ctx, r: check_tag_id_charset(
        {k: ctx[k] for k in _CHARSET_REGISTRIES if isinstance(ctx.get(k), dict)}, r),
    "area_tag_gaps": lambda ctx, r: check_area_tag_gaps(ctx["areas"], r),
"duplicate_area_names": lambda ctx, r: check_duplicate_area_names(ctx["areas"], r),
    "biome_coverage": lambda ctx, r: check_biome_coverage(ctx["items"], ctx["biomes"], r),
    "stray_library_dirs": lambda ctx, r: check_stray_library_dirs(ctx["lib_dir"], r),
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, check, message):
        self.errors.append((check, message))
        print(f"[ERROR] ({check}) {message}")

    def warn(self, check, message):
        self.warnings.append((check, message))
        print(f"[WARN ] ({check}) {message}")


def main():
    parser = argparse.ArgumentParser(description="Lint the virtual world data library.")
    parser.add_argument("--data-dir", default=None,
                        help="library dir override (for fixture testing)")
    parser.add_argument("--check", action="append", choices=ALL_CHECKS, dest="checks",
                        help="run only these checks (repeatable); default: all")
    args = parser.parse_args()

    lib_dir = os.path.abspath(args.data_dir) if args.data_dir else os.path.abspath(DEFAULT_LIB_DIR)
    selected = tuple(args.checks) if args.checks else ALL_CHECKS

    ctx = {
        "items": load_registry(lib_dir, "items"),
        "characters": load_registry(lib_dir, "characters"),
        "areas": load_registry(lib_dir, "areas"),
        # task-601: the tag registry is where the space-separated ids actually
        # live (15 of them), so the charset check needs it in context.
        "tags": load_registry(lib_dir, "tags"),
        "ways": load_registry(lib_dir, "ways"),
        # task-573: the compiler vocabulary lives next to the library, not in it.
        "biomes": load_biomes(lib_dir),
        "lib_dir": lib_dir,
    }
    print(f"linting {lib_dir} — items={len(ctx['items'])} "
          f"characters={len(ctx['characters'])} areas={len(ctx['areas'])}")

    report = Report()
    for check in selected:
        CHECKS[check](ctx, report)

    print(f"\n{len(report.errors)} errors, {len(report.warnings)} warnings")
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
