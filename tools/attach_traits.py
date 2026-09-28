#!/usr/bin/env python3
"""attach_traits.py — attach library traits to the characters that should have them.

A scenario can ship the trait in ``data/library/traits/`` and never attach it, so
the authored intent ("goblins burn through food and water") is present in the repo
and absent from the world. Selection is by **tag**, not by name: a roster of
hand-picked names is stale the moment somebody joins.

Traits are written to the ``players`` block, which is where
``engine/traits.TraitSystem`` reads them, and to the authored character node so
the two agree before the loader collapses them. Existing values are kept unless
``--replace`` is given — a scenario that already parameterised the trait should
not be silently reset to ``True``.

Usage:
    python tools/attach_traits.py high_metabolism --tag goblin
    python tools/attach_traits.py high_metabolism --tag goblin --write
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.character_identity import authored_character_node_id  # noqa: E402
from tools.scenario_refs import load_json, save_json  # noqa: E402

DEFAULT_TARGET = "data/scenarios/kraktooth_goblin_camp.json"


def known_traits() -> set:
    library = ROOT / "data" / "library" / "traits"
    if not library.is_dir():
        return set()
    return {path.stem for path in library.glob("*.json")}


def attach(data: dict, trait_id: str, tags, replace: bool) -> dict:
    """Attach *trait_id* to every player carrying one of *tags*. Returns a report."""
    players = data.get("players") or {}
    nodes = (data.get("graph") or {}).get("nodes") or {}
    wanted = {str(t).lower() for t in tags}

    attached = []
    skipped = []
    for key, player in sorted(players.items()):
        if not isinstance(player, dict):
            continue
        player_tags = {str(t).lower() for t in (player.get("tags") or [])}
        if not (player_tags & wanted):
            continue
        name = str(player.get("name") or key)
        existing = player.get("traits")
        if not isinstance(existing, dict):
            existing = {}
            player["traits"] = existing
        if trait_id in existing and not replace:
            skipped.append((name, existing[trait_id]))
            continue
        existing[trait_id] = True
        node = nodes.get(authored_character_node_id(name))
        if isinstance(node, dict):
            node_props = node.setdefault("properties", {})
            node_traits = node_props.get("traits")
            if not isinstance(node_traits, dict):
                node_traits = {}
                node_props["traits"] = node_traits
            if trait_id in node_traits and not replace:
                node_traits[trait_id] = existing[trait_id]
            else:
                node_traits[trait_id] = True
        attached.append(name)

    return {"attached": attached, "skipped": skipped, "matched": len(attached) + len(skipped)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("trait", help="Trait id from data/library/traits/")
    parser.add_argument("--tag", action="append", default=[], required=True,
                        help="Player tag to select by (repeatable)")
    parser.add_argument("paths", nargs="*", help="Scenario files (default: the camp)")
    parser.add_argument("--write", action="store_true", help="Apply to disk")
    parser.add_argument("--replace", action="store_true",
                        help="Overwrite an already-attached trait")
    args = parser.parse_args()

    library = known_traits()
    if library and args.trait not in library:
        print(
            f"error: {args.trait!r} is not in data/library/traits/ "
            f"(known: {', '.join(sorted(library))})",
            file=sys.stderr,
        )
        return 2

    paths = ([ROOT / p if not Path(p).is_absolute() else Path(p) for p in args.paths]
             or [ROOT / DEFAULT_TARGET])
    total = 0
    for path in paths:
        if not path.exists():
            print(f"skip {path}: not found", file=sys.stderr)
            continue
        data = load_json(path)
        report = attach(data, args.trait, args.tag, args.replace)
        count = len(report["attached"])
        total += count
        for name in report["attached"]:
            print(f"  {name}: {args.trait}")
        for name, value in report["skipped"]:
            print(f"  kept {name}: {args.trait}={value!r}")
        if report["matched"] == 0:
            print(f"  no player carries tag(s) {', '.join(args.tag)}", file=sys.stderr)
        if count and args.write:
            save_json(path, data)
        label = "attached" if (count and args.write) else ("would attach" if count else "ok")
        print(f"  {label}: {path.relative_to(ROOT)} ({count}/{report['matched']})")
    print(f"\n[attach_traits] {total} characters gained {args.trait}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
