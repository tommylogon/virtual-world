#!/usr/bin/env python3
"""set_scenario_title.py — stamp a human title onto a scenario file.

The app labels a scenario from ``_scenario_name``, and the frontend's
``_scenarioIdentity()`` reads that too, so a file with no title shows up as
``world_template`` in the picker. This writes the three places a title belongs:
``name``, ``meta.title``, and ``_scenario_name`` (the last only when the file
has none, so a deliberate internal id is never clobbered).

Scope warning: ``engine/serialization.py`` round-trips ``_scenario_name`` but
NOT ``name``/``meta``, so saving the scenario from the editor drops the title
again (bug-47). Until that hub file preserves the keys, re-run this after a save.

Usage:
    python tools/set_scenario_title.py "Kraktooth Goblin Camp"
    python tools/set_scenario_title.py "Kraktooth Goblin Camp" --write
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scenario_refs import load_json, save_json  # noqa: E402

DEFAULT_TARGET = "data/scenarios/kraktooth_goblin_camp.json"


def set_title(data: dict, title: str) -> dict:
    """Stamp *title* onto *data*. Returns a report of what changed."""
    changes = []
    if data.get("name") != title:
        changes.append(("name", data.get("name"), title))
    data["name"] = title
    meta = data.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        data["meta"] = meta
    if meta.get("title") != title:
        changes.append(("meta.title", meta.get("title"), title))
    meta["title"] = title
    if not data.get("_scenario_name"):
        data["_scenario_name"] = title
        changes.append(("_scenario_name", None, title))
    return {"changes": changes}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("title", help="Human-readable scenario title")
    parser.add_argument("paths", nargs="*", help="Scenario files (default: the camp)")
    parser.add_argument("--write", action="store_true", help="Apply to disk")
    args = parser.parse_args()

    paths = ([ROOT / p if not Path(p).is_absolute() else Path(p) for p in args.paths]
             or [ROOT / DEFAULT_TARGET])
    total = 0
    for path in paths:
        if not path.exists():
            print(f"skip {path}: not found", file=sys.stderr)
            continue
        data = load_json(path)
        report = set_title(data, args.title)
        for key, before, after in report["changes"]:
            print(f"  {key}: {before!r} -> {after!r}")
        if report["changes"] and args.write:
            save_json(path, data)
        total += len(report["changes"])
        print(f"  {'stamped' if (report['changes'] and args.write) else 'checked'}: "
              f"{path.relative_to(ROOT)}")
    print(f"\n[set_scenario_title] {total} title keys written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
