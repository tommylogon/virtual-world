#!/usr/bin/env python3
"""migrate_decay_rates.py — re-bake per-player decay_rates to the calibrated
per-minute scale (vital_rates.BASELINE_DECAY).

Scenarios and world_template.json serialize each player's full ``decay_rates``
dict, and ``WorldSerializer._deserialize_player`` treats those as overrides.
That means the calibrated engine defaults in vital_rates are ignored for any
already-saved world: a scenario baked before the 2026-09 recalibration keeps
the old "1/tick" feel forever.

This tool rewrites the canonical keys (Energy, Hunger, Thirst, Social,
Hygiene, Sanity, Entertainment, Mana, Bladder) to the calibrated defaults
while leaving any other keys (e.g. mature-content Arousal/Stimulation/
Pleasure) untouched. Writes only files that actually changed.

Usage:
    python tools/migrate_decay_rates.py                # world_template + goblin
    python tools/migrate_decay_rates.py --all          # every data/scenarios/*.json
    python tools/migrate_decay_rates.py path/a.json path/b.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vital_rates import BASELINE_DECAY, BLADDER_FILL  # noqa: E402

CANONICAL = {**BASELINE_DECAY, "Bladder": BLADDER_FILL}


def migrate_file(path: Path) -> int:
    """Rewrite decay_rates for every player. Returns players changed."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    players = data.get("players") or {}
    changed = 0
    for pdata in players.values():
        if not isinstance(pdata, dict):
            continue
        current = pdata.get("decay_rates") or {}
        merged = dict(current)
        merged.update(CANONICAL)
        if merged != current:
            pdata["decay_rates"] = merged
            changed += 1
    if changed:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="explicit files to migrate")
    ap.add_argument("--all", action="store_true", help="migrate every data/scenarios/*.json")
    args = ap.parse_args()

    if args.files:
        targets = [ROOT / f for f in args.files]
    else:
        targets = [ROOT / "world_template.json"]
        if args.all:
            targets += sorted((ROOT / "data" / "scenarios").glob("*.json"))
        else:
            targets.append(ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json")

    total = 0
    for path in targets:
        if not path.exists():
            print(f"  skip (missing): {path}")
            continue
        changed = migrate_file(path)
        total += changed
        mark = "updated" if changed else "already current"
        print(f"  {mark:>15}: {path.relative_to(ROOT)} ({changed} players)")

    print(f"\n[migrate] {total} player records rewritten across {len(targets)} files")


if __name__ == "__main__":
    main()
