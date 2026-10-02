#!/usr/bin/env python3
"""Lint interest/fear tags in scenario and save files (bug-513).

`tools/lint_library.py` runs `check_dead_interests` and `check_dead_fears`
against `data/library/` only, so a scenario save can carry any number of tags
that can never match and nothing reports it. Kraktooth is the live example:
Belne's and the Eldenford Farmer's `interest_tags` name tags no item carries, so
the room attention list and the auto-dress path ignore them silently.

This tool closes that gap without changing the library lint's input. It reuses
the *same* rule semantics — interests match item tags; fears match item, area or
character tags plus trait keys, because that is what `engine/fear.py` reads — but
runs them over `data/scenarios/*.json`, which the library lint never opens.

A scenario is a different input source, not a different rule, so the vocabulary
is the library registries PLUS the tags the scenario's own nodes and players
carry. Comparing a scenario tag against the library alone would report a live
tag as dead; comparing it against the scenario alone would report every library
item reference as dead.

Usage:
    python tools/scenario_tag_check.py --report          # every finding, grouped
    python tools/scenario_tag_check.py --check           # fail on NEW findings
    python tools/scenario_tag_check.py --update-baseline # accept today's debt

`--check` compares against a baseline of known findings so existing authored
debt does not block work, and a newly authored dead tag still fails. Signatures
are per tag, not per file: adding a brand-new dead tag to an already-dirty
character must still register.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = ROOT / "data" / "library"
SCENARIO_DIR = ROOT / "data" / "scenarios"
BASELINE_PATH = ROOT / "docs" / "virtualWorld" / "World Building" / "scenario-tag-baseline.txt"

#: check id -> (label, why)
CHECKS = {
    "dead_interests": (
        "interest tag no item carries, so the attention list and auto-dress ignore it",
        "interests are matched against item tags only "
        "(static/js/agent/prompt-builder/room-context.js:299, engine/dressing.py:100). "
        "A tag no item carries can never score.",
    ),
    "dead_fears": (
        "fear tag nothing a fear source can carry, so the character is never frightened",
        "engine/fear.py::character_tags unions a character's tags and trait keys; "
        "fear_sources adds the area's tags and the area's items. A tag outside that "
        "vocabulary cannot fire and nothing says why (bug-552's failure mode).",
    ),
}


def _load(path: Path):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except Exception:
        return None


def _tags(entry) -> set:
    """Lowercased tags from a library entry or graph node properties dict."""
    if not isinstance(entry, dict):
        return set()
    raw = entry.get("tags")
    if raw is None and isinstance(entry.get("properties"), dict):
        raw = entry["properties"].get("tags")
    return {str(t).strip().lower() for t in (raw or []) if str(t).strip()}


def _trait_keys(entry) -> set:
    traits = entry.get("traits") if isinstance(entry, dict) else None
    if not isinstance(traits, dict):
        return set()
    return {str(k).strip().lower() for k in traits if str(k).strip()}


def _registry(dir_name: str) -> dict:
    out = {}
    for path in glob.glob(os.path.join(LIB_DIR, dir_name, "*.json")):
        data = _load(Path(path))
        if isinstance(data, dict):
            out[os.path.splitext(os.path.basename(path))[0]] = data
    return out


def _library_vocab():
    """(item_tag_vocab, fear_vocab) from the shipped library registries."""
    items = _registry("items")
    areas = _registry("areas")
    characters = _registry("characters")

    item_tags = set()
    fear_tags = set()
    for entry in items.values():
        item_tags |= _tags(entry)
        fear_tags |= _tags(entry)
    for entry in areas.values():
        fear_tags |= _tags(entry)
    for entry in characters.values():
        fear_tags |= _tags(entry)
        fear_tags |= _trait_keys(entry)
    return item_tags, fear_tags


def _scenario_vocab(payload: dict):
    """Tags the scenario's own nodes and players carry, by the same rules."""
    item_tags = set()
    fear_tags = set()

    nodes = (payload.get("graph") or {}).get("nodes") or {}
    if isinstance(nodes, dict):
        for node in nodes.values():
            if not isinstance(node, dict):
                continue
            node_tags = _tags(node)
            if node.get("type") == "item":
                item_tags |= node_tags
            if node.get("type") in ("item", "area", "character"):
                fear_tags |= node_tags

    players = payload.get("players") or {}
    if isinstance(players, dict):
        for player in players.values():
            fear_tags |= _tags(player)
            fear_tags |= _trait_keys(player)
    return item_tags, fear_tags


def scan_scenario(path: Path, lib_item_tags: set, lib_fear_tags: set) -> list:
    """Return (check_id, player_key, tag) findings for one scenario file."""
    payload = _load(path)
    if not isinstance(payload, dict):
        return []
    players = payload.get("players")
    if not isinstance(players, dict):
        return []

    scenario_item_tags, scenario_fear_tags = _scenario_vocab(payload)
    item_tags = lib_item_tags | scenario_item_tags
    fear_tags = lib_fear_tags | scenario_fear_tags

    found = []
    for key, player in players.items():
        if not isinstance(player, dict):
            continue
        interests = player.get("interest_tags") or []
        for tag in interests:
            low = str(tag).strip().lower()
            if low and low not in item_tags:
                found.append(("dead_interests", str(key), low))
        for tag in player.get("fear_tags") or []:
            low = str(tag).strip().lower()
            if low and low not in fear_tags:
                found.append(("dead_fears", str(key), low))
    return found


def scan() -> dict:
    lib_item_tags, lib_fear_tags = _library_vocab()
    results = {cid: [] for cid in CHECKS}
    scanned = 0
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        scanned += 1
        for cid, key, tag in scan_scenario(path, lib_item_tags, lib_fear_tags):
            results.setdefault(cid, []).append((path.name, key, tag))
    return {"scanned": scanned, "findings": results}


def _signature(check_id: str, filename: str, key: str, tag: str) -> str:
    return f"{check_id}|{filename}|{key}|{tag}"


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
        "# Known scenario/save dead-tag findings, accepted as-is.\n"
        "# Regenerate: python tools/scenario_tag_check.py --update-baseline\n"
        "# Lines are check_id|scenario|player|tag. --check fails only on NEW lines.\n"
    )
    BASELINE_PATH.write_text(header + "\n".join(sorted(signatures)) + "\n", encoding="utf-8")


def _all_signatures(findings: dict) -> set:
    return {
        _signature(cid, filename, key, tag)
        for cid, entries in findings.items()
        for filename, key, tag in entries
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="list every finding, grouped by check")
    ap.add_argument("--check", action="store_true", help="fail if any finding is not in the baseline")
    ap.add_argument("--update-baseline", action="store_true", help="write the current findings as the baseline")
    args = ap.parse_args()

    result = scan()
    findings = result["findings"]
    all_sigs = _all_signatures(findings)

    if args.update_baseline:
        _write_baseline(all_sigs)
        print(f"Baseline written: {len(all_sigs)} known finding(s) across {result['scanned']} scenarios.")
        return 0

    total = sum(len(v) for v in findings.values())

    if args.report:
        print(f"{result['scanned']} scenario files scanned. {total} dead-tag finding(s).\n")
        for cid, entries in findings.items():
            if not entries:
                continue
            label, why = CHECKS.get(cid, (cid, ""))
            print(f"[{cid}] {label}  ({len(entries)})")
            print(f"    why: {why}")
            for filename, key, tag in entries[:20]:
                print(f"      {filename}: {key}: {tag}")
            if len(entries) > 20:
                print(f"      ... and {len(entries) - 20} more")
            print()
        return 0

    if args.check:
        baseline = _read_baseline()
        new = sorted(all_sigs - baseline)
        stale = sorted(baseline - all_sigs)
        if new:
            print(f"scenario tags: {len(new)} NEW finding(s) not in the baseline:")
            for sig in new[:20]:
                print(f"  {sig}")
            if len(new) > 20:
                print(f"  ... and {len(new) - 20} more")
            print("Run --report for detail, --update-baseline to accept them.")
            return 1
        note = f" ({len(stale)} baseline entr{'y is' if len(stale) == 1 else 'ies are'} now fixed)" if stale else ""
        print(f"scenario tags OK: {result['scanned']} scenarios, no new findings{note}.")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
