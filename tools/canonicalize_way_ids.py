#!/usr/bin/env python3
"""canonicalize_way_ids.py — make every way's endpoints the area NODE ID.

A way's ``properties.area_from`` / ``area_to`` may hold either an area node id
or an area display name, because the engine resolves both. Strict-id pathfinding
resolves only the id, and the folder-authoring compiler
(``tools/build_scenario.normalize_way``) *rejects* a name outright, so a
name-addressed way silently loses strict-id pathfinding and cannot be compiled.

This rewrites the two properties to the canonical area id, resolved through
``tools/scenario_refs.AreaResolver`` (id, then exact name, then normalized
name; an ambiguous reference is an error, not a guess). The ``connection``
edges are left alone: the graph is already the truth about which areas a way
touches, so changing them could move a way onto the wrong side of the camp.

Usage:
    python tools/canonicalize_way_ids.py data/scenarios/kraktooth_goblin_camp.json
    python tools/canonicalize_way_ids.py --all --write
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scenario_refs import (  # noqa: E402
    AmbiguousRef,
    AreaResolver,
    load_json,
    save_json,
    way_area_refs,
    way_connection_pairs,
)

DEFAULT_TARGET = "data/scenarios/kraktooth_goblin_camp.json"


def canonicalize(data: dict) -> dict:
    """Rewrite way endpoints to area ids in *data*. Returns a report."""
    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or {}
    edges = graph.get("edges") or []
    resolver = AreaResolver(nodes)
    graph_sides = way_connection_pairs(nodes, edges)
    changes = []
    unresolved = []
    ambiguous = []
    disagreements = []
    for way_id, field, value in way_area_refs(nodes):
        try:
            resolved = resolver.resolve(value)
        except AmbiguousRef as error:
            ambiguous.append((way_id, field, str(error)))
            continue
        if resolved is None:
            unresolved.append((way_id, field, value))
            continue
        # The connection edges are the truth about which areas a way touches.
        # A name that resolves to an area the graph does not connect means the
        # authored claim and the graph genuinely disagree — report, do not
        # silently point the property at the graph's version.
        sides = graph_sides.get(way_id) or set()
        if sides and resolved not in sides:
            disagreements.append((way_id, field, value, resolved, sorted(sides)))
        if resolved != value:
            nodes[way_id]["properties"][field] = resolved
            changes.append((way_id, field, value, resolved))
    return {
        "rewritten": changes,
        "unresolved": unresolved,
        "ambiguous": ambiguous,
        "disagreements": disagreements,
    }


def _targets(paths, use_all):
    if paths:
        return [ROOT / p if not Path(p).is_absolute() else Path(p) for p in paths]
    if use_all:
        return sorted((ROOT / "data" / "scenarios").glob("*.json"))
    return [ROOT / DEFAULT_TARGET]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="Scenario files (default: the camp)")
    parser.add_argument("--all", action="store_true", help="every data/scenarios/*.json")
    parser.add_argument("--write", action="store_true", help="Apply the rewrite to disk")
    args = parser.parse_args()

    total = 0
    for path in _targets(args.paths, args.all):
        if not path.exists():
            print(f"skip {path}: not found", file=sys.stderr)
            continue
        data = load_json(path)
        report = canonicalize(data)
        count = len(report["rewritten"])
        total += count
        for way_id, field, value, resolved in report["rewritten"]:
            print(f"  {way_id}.{field}: {value!r} -> {resolved}")
        for way_id, field, value in report["unresolved"]:
            print(f"  UNRESOLVED {way_id}.{field}: {value!r}", file=sys.stderr)
        for way_id, field, value, resolved, sides in report["disagreements"]:
            print(
                f"  DISAGREES {way_id}.{field}: {value!r} resolves to {resolved} but "
                f"the graph connects {', '.join(sides)}",
                file=sys.stderr,
            )
        for way_id, field, message in report["ambiguous"]:
            print(f"  AMBIGUOUS {way_id}.{field}: {message}", file=sys.stderr)
        if report["disagreements"] or report["unresolved"] or report["ambiguous"]:
            print(
                f"  skipped {path.relative_to(ROOT)}: "
                f"{len(report['unresolved'])} unresolved, "
                f"{len(report['ambiguous'])} ambiguous, "
                f"{len(report['disagreements'])} disagreeing with the graph",
                file=sys.stderr,
            )
            total -= count
            continue
        if count and args.write:
            save_json(path, data)
        label = "rewrote" if (count and args.write) else ("would rewrite" if count else "ok")
        print(f"  {label}: {path.relative_to(ROOT)} ({count} endpoints)")
    print(f"\n[canonicalize_way_ids] {total} way endpoints rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
