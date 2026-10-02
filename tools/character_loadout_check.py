#!/usr/bin/env python3
"""Validate character loadouts in the library against what the engine can read.

The library is a WIP and the character `equipped` field has no declared shape, so
bad data is silent. Three separate failures were found by hand in one session,
and each one looked fine until something read it:

- **A dict entry in `equipped` crashes the whole state endpoint.**
  `POST /api/library/refresh-to-world` writes the template value verbatim
  (`_refresh_character`, `routes/library_ops.py`, `'equipped': ('equipped', 'dict')`),
  so the dicts land on the live player. `is_exposed` then calls
  `graph.get_node(outer_id)` with a dict (`engine/body_parts.py:260`) and
  `TypeError: unhashable type: 'dict'` takes down `GET /api/state`. Import is
  safe -- it rewrites to node-id strings -- which is why this only fires on
  refresh, and only for characters somebody has refreshed.

- **A non-list slot is dropped silently.** Import reads
  `for slot, stack in equipped.items(): if not isinstance(stack, list): continue`
  (`routes/library_ops.py:567`), so the slot vanishes with no error.

- **A reference with no inventory entry resolves to nothing.** Import matches an
  equipped reference against the loaded inventory by node id, library id and
  name, so a reference it cannot match simply leaves the slot empty. An
  inventory entry may be a plain library id string or a dict carrying
  `node_id`/`library_id`, and its properties may live in the template.

None of these are hypothetical: this file was written the same day one of them
took down the running app. This checker exists so the next one is caught by a
command rather than by a stack trace.

Deliberately NOT checked, because it is not a loadout defect:

- Whether the *items* are sensible for the character. That is judgement, and the
  LLM path in `engine/dressing.py` is the answer to it, not a regex.
- Whether `inventory` survives a refresh. It does not -- refresh ignores the
  field entirely while import honours it -- but that is bug-516, a code defect,
  and flagging every affected character would be noise rather than a signal.

Usage:
    python tools/character_loadout_check.py --report          # every finding, grouped
    python tools/character_loadout_check.py --check           # fail on NEW findings
    python tools/character_loadout_check.py --update-baseline # accept today's debt

`--check` compares against a baseline of known findings so the existing debt in
a WIP library does not block work, and a regression still fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CHAR_DIR = Path("data/library/characters")
ITEM_DIR = Path("data/library/items")
BASELINE_PATH = Path("docs/virtualWorld/World Building/character-loadout-baseline.txt")

# The rules are declared once, in tools/character_loadout_rules.py, the way
# tools/way_properties.py feeds way_property_index.py. Imported rather than
# inlined so the checker and its contract test read the same table.
from character_loadout_rules import CHECKS, ERROR, WARN  # noqa: E402


def _load(path: Path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def _normalise_identity(text: str) -> str:
    """Fold the differences that are spelling, not identity.

    `Miki.json` / "miki", `miki-takahashi.json` / "miki takahashi" and
    `jake.json` / "jake halloway" style differences are the same character, and
    flagging them would bury the finding that matters: a file renamed to a
    personal name whose `name` field still holds the old role. Compare on
    alphanumerics only, lowercased.
    """
    return "".join(ch for ch in str(text or "").lower() if ch.isalnum())


def check_character(path: Path, data: dict, library_items) -> list:
    """Return (check_id, detail) pairs for one character entry.

    ``library_items`` maps a library item id to its template dict. A plain set of
    ids is also accepted (older callers/tests): templates then resolve to empty
    and only the id-existence checks run.
    """
    found = []

    if isinstance(library_items, dict):
        templates = library_items
    else:
        templates = {str(k): {} for k in (library_items or ())}
    known_ids = set(templates)

    # Both forms of inventory entry resolve to a reference key: a string entry
    # keys by its library id, a dict entry by its node id (falling back to the
    # library id). `inventory_declared` maps that key to the item's equip_slots
    # so slot placement can be checked whether the props are inline or from the
    # template.
    inventory_node_ids = set()
    inventory_lib_ids = set()
    inventory_names = {}
    inventory_declared = {}

    for entry in data.get("inventory") or []:
        if isinstance(entry, str):
            lib_id = entry.strip()
            if not lib_id:
                continue
            if lib_id not in known_ids:
                found.append(("unknown_library_id", lib_id))
            template = templates.get(lib_id) or {}
            inventory_lib_ids.add(lib_id)
            inventory_declared[lib_id] = template.get("equip_slots") or []
            name = template.get("name") or lib_id
            inventory_names[str(name).lower()] = lib_id
            continue
        if not isinstance(entry, dict):
            continue
        node_id = entry.get("node_id")
        lib_id = entry.get("library_id")
        if node_id:
            inventory_node_ids.add(node_id)
        else:
            found.append(("missing_node_id", entry.get("name", "<unnamed>")))
        props = entry.get("properties") or {}
        # task-519: a library-id-backed entry materializes from its template, so
        # absent inline properties are not a defect while the id resolves.
        if not props and not (lib_id and lib_id in known_ids):
            found.append(("missing_properties", entry.get("name", "<unnamed>")))
        if lib_id:
            if lib_id not in known_ids:
                found.append(("unknown_library_id", str(lib_id)))
            else:
                inventory_lib_ids.add(lib_id)
        declared = props.get("equip_slots")
        if declared is None and lib_id and lib_id in known_ids:
            declared = (templates.get(lib_id) or {}).get("equip_slots") or []
        key = node_id or lib_id
        if key:
            inventory_declared[key] = declared or []
        name = entry.get("name") or (templates.get(lib_id) or {}).get("name")
        if name:
            inventory_names[str(name).lower()] = key or str(name).lower()

    equipped = data.get("equipped")
    if isinstance(equipped, dict):
        for slot, stack in equipped.items():
            if not isinstance(stack, list):
                found.append(("equipped_slot_not_list", slot))
                continue
            for item in stack:
                if isinstance(item, dict):
                    found.append(("equipped_dict_entry", f"{slot}: {json.dumps(item)[:60]}"))
                    continue
                if item and str(item).startswith("__"):
                    continue  # runtime marker, not a node id
                key = str(item)
                if key in inventory_node_ids or key in inventory_lib_ids:
                    lookup_key = key
                elif key.lower() in inventory_names:
                    lookup_key = inventory_names[key.lower()]
                else:
                    found.append(("equipped_id_not_in_inventory", f"{slot}: {item}"))
                    continue
                declared = inventory_declared.get(lookup_key) or []
                if declared and slot not in declared:
                    found.append((
                        "slot_not_declared",
                        f"{slot}: {item} declares {declared}",
                    ))

    stem = path.stem
    internal = (data.get("name") or "").strip()
    if internal and _normalise_identity(internal) != _normalise_identity(stem):
        found.append(("name_does_not_match_file", f"file '{stem}' vs name '{internal}'"))

    return found


def scan() -> dict:
    """Every finding, keyed by check id -> list of (filename, detail)."""
    library_items = {p.stem: (_load(p) or {}) for p in ITEM_DIR.glob("*.json")}
    results = {cid: [] for cid in CHECKS}
    scanned = 0
    for path in sorted(CHAR_DIR.glob("*.json")):
        data = _load(path)
        if not isinstance(data, dict):
            results.setdefault("unparseable", []).append((path.name, "not a JSON object"))
            continue
        scanned += 1
        for check_id, detail in check_character(path, data, library_items):
            results.setdefault(check_id, []).append((path.name, detail))
    return {"scanned": scanned, "findings": results}


def _signature(check_id: str, filename: str) -> str:
    """Stable identity for baselining: a check plus the file it fired in.

    Per-check + per-file rather than per-detail, so a new *kind* of problem in a
    file already known to be broken still registers, while the same problem
    re-reported after an unrelated edit does not churn the baseline.
    """
    return f"{check_id}|{filename}"


def _read_baseline() -> set:
    if not BASELINE_PATH.exists():
        return set()
    return {
        line.strip()
        for line in BASELINE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _write_baseline(signatures: set) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Known character-loadout findings, accepted as-is.\n"
        "# Regenerate: python tools/character_loadout_check.py --update-baseline\n"
        "# Lines are check_id|filename. --check fails only on NEW lines.\n"
    )
    BASELINE_PATH.write_text(header + "\n".join(sorted(signatures)) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="list every finding, grouped by check")
    ap.add_argument("--check", action="store_true", help="fail if any finding is not in the baseline")
    ap.add_argument("--update-baseline", action="store_true", help="write the current findings as the baseline")
    args = ap.parse_args()

    result = scan()
    findings = result["findings"]
    all_sigs = {
        _signature(cid, fname)
        for cid, entries in findings.items()
        for fname, _detail in entries
    }

    if args.update_baseline:
        _write_baseline(all_sigs)
        print(f"Baseline written: {len(all_sigs)} known finding(s) across {result['scanned']} characters.")
        return 0

    errors = sum(len(v) for k, v in findings.items() if CHECKS.get(k, (WARN,))[0] == ERROR)
    warns = sum(len(v) for k, v in findings.items() if CHECKS.get(k, (WARN,))[0] == WARN)

    if args.report:
        print(f"{result['scanned']} character entries scanned. {errors} error(s), {warns} warning(s).\n")
        for cid, entries in findings.items():
            if not entries:
                continue
            sev, label, why = CHECKS.get(cid, (WARN, cid, ""))
            print(f"[{sev}] {cid} -- {label}  ({len(entries)})")
            print(f"    why: {why}")
            for fname, detail in entries[:12]:
                print(f"      {fname}: {detail}")
            if len(entries) > 12:
                print(f"      ... and {len(entries) - 12} more")
            print()
        return 0

    if args.check:
        baseline = _read_baseline()
        new = sorted(all_sigs - baseline)
        stale = sorted(baseline - all_sigs)
        if new:
            print(f"character loadout: {len(new)} NEW finding(s) not in the baseline:")
            for sig in new[:20]:
                cid, _, fname = sig.partition("|")
                print(f"  [{CHECKS.get(cid, (WARN,))[0]}] {cid}: {fname}")
            if len(new) > 20:
                print(f"  ... and {len(new) - 20} more")
            print("Run --report for detail, --update-baseline to accept them.")
            return 1
        note = f" ({len(stale)} baseline entr{'y is' if len(stale) == 1 else 'ies are'} now fixed)" if stale else ""
        print(f"character loadout OK: {result['scanned']} entries, no new findings{note}.")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
