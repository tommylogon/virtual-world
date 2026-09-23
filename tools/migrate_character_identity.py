#!/usr/bin/env python3
"""Collapse the dual character identity in existing scenarios and saves.

Authored scenario/save files may carry two graph nodes for one person: an
authored ``character_<slug>`` node (description + ``in``/``carrying`` edges)
and the runtime ``player_<Name>`` anchor (``x``/``y`` + ``at``/``equipped``/
``grappled`` edges). The loader collapses them at load time (task-463); this
tool performs the same collapse on the file itself so the data stops shipping
the duplication.

Usage:
    python tools/migrate_character_identity.py data/scenarios/*.json
    python tools/migrate_character_identity.py saves --write
    python tools/migrate_character_identity.py data/scenarios/kraktooth_goblin_camp.json --json

Without ``--write`` it is a dry run and changes nothing. The migration is
idempotent: a file with a single character node per person reports zero
collapses.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.character_identity import (  # noqa: E402
    collapse_character_identity,
    normalize_known_lists,
)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def migrate_payload(data):
    """Collapse *data* in place; returns a report, or None when inapplicable."""
    if not isinstance(data, dict):
        return None
    graph = data.get("graph")
    if not isinstance(graph, dict):
        return None
    players = data.get("players") or {}
    report = collapse_character_identity(graph, players)
    report["known_rewritten"] = normalize_known_lists(
        players, report.get("aliases") or {}
    )
    return report


def _collect(paths):
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
        else:
            files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", help="Scenario/save files or directories")
    parser.add_argument("--write", action="store_true", help="Apply the migration to disk")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args()

    reports = {}
    total_collapsed = 0
    for path in _collect(args.paths):
        if not path.exists():
            print(f"skip {path}: not found", file=sys.stderr)
            continue
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError) as error:
            print(f"skip {path}: {error}", file=sys.stderr)
            continue
        report = migrate_payload(data)
        if report is None:
            continue
        collapsed = len(report["collapsed"])
        total_collapsed += collapsed
        reports[str(path)] = report
        if collapsed and args.write:
            save_json(path, data)
        if not args.json:
            verb = "migrated" if (collapsed and args.write) else (
                "would migrate" if collapsed else "ok"
            )
            print(
                f"{verb} {path}: {collapsed} collapsed, "
                f"{report['edges_rewritten']} edges rewritten, "
                f"{report['edges_deduped']} deduped, "
                f"{report['known_rewritten']} known refs"
            )

    if args.json:
        print(json.dumps({"files": reports, "total_collapsed": total_collapsed}, indent=2))
    else:
        print(f"total collapsed: {total_collapsed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
