#!/usr/bin/env python3
"""author_character_aliases.py — restore the authored ``character_*`` node.

task-408's dedupe is **one character node per person after load**, not one node
in the file. ``engine/character_identity.collapse_character_identity`` merges an
authored ``character_<slug>`` node into the runtime ``player_<Name>`` anchor at
load time, rewrites that node's edges, and keeps the retired id resolvable as a
graph alias. That is what ``tests/test_character_identity.py`` asserts.

A file collapsed *on disk* (``tools/migrate_character_identity.py --write``) has
the authored nodes removed, so the alias is gone and the identity tests fail
even though the graph is otherwise clean. This tool puts the authored node back
from the ``players`` block — which is the single place the prose lives — so the
file carries identity, not just content.

Idempotent and dry-run by default.

Usage:
    python tools/author_character_aliases.py data/scenarios/kraktooth_goblin_camp.json
    python tools/author_character_aliases.py --all --write
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.character_identity import (  # noqa: E402
    authored_character_node_id,
    canonical_character_node_id,
)
from tools.scenario_refs import (  # noqa: E402
    AreaResolver,
    load_json,
    save_json,
)

DEFAULT_TARGET = "data/scenarios/kraktooth_goblin_camp.json"

#: Copied onto the authored node; ``collapse_character_identity`` merges the rest
#: of the node's properties across, and its prose keys win over the anchor's.
PROSE_KEYS = ("description", "base_description", "personality")


def author_alias(data: dict) -> dict:
    """Ensure every player has an authored node. Returns a report."""
    graph = data.get("graph") or {}
    nodes = graph.setdefault("nodes", {})
    edges = graph.setdefault("edges", [])
    players = data.get("players") or {}
    resolver = AreaResolver(nodes)
    existing_in = {
        str(edge.get("source"))
        for edge in edges
        if isinstance(edge, dict) and edge.get("type") == "in"
    }

    added = []
    skipped = []
    for key, player in sorted(players.items()):
        if not isinstance(player, dict):
            continue
        name = str(player.get("name") or key)
        authored_id = authored_character_node_id(name)
        anchor_id = canonical_character_node_id(name)
        if authored_id in nodes:
            continue
        if anchor_id not in nodes:
            # An alias with no anchor to collapse into is not worth writing.
            skipped.append((name, f"no {anchor_id} anchor to collapse into"))
            continue

        props = {}
        for prose in PROSE_KEYS:
            if player.get(prose):
                props[prose] = player[prose]
        props["tags"] = list(player.get("tags") or [])
        if player.get("traits"):
            props["traits"] = dict(player["traits"])

        nodes[authored_id] = {
            "id": authored_id,
            "type": "character",
            "name": name,
            "properties": props,
        }

        area = player.get("current_area")
        if area and authored_id not in existing_in:
            area_id = resolver.resolve(area)
            if area_id:
                edges.append({
                    "source": authored_id, "target": area_id,
                    "type": "in", "properties": {},
                })
            else:
                skipped.append((name, f"unresolved current_area {area!r}"))
        added.append((authored_id, anchor_id))

    return {"added": added, "skipped": skipped}


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
    parser.add_argument("--write", action="store_true", help="Apply the authoring to disk")
    args = parser.parse_args()

    total = 0
    for path in _targets(args.paths, args.all):
        if not path.exists():
            print(f"skip {path}: not found", file=sys.stderr)
            continue
        data = load_json(path)
        report = author_alias(data)
        count = len(report["added"])
        total += count
        for authored_id, anchor_id in report["added"]:
            print(f"  {authored_id} -> {anchor_id}")
        for name, reason in report["skipped"]:
            if reason:
                print(f"  SKIP {name}: {reason}", file=sys.stderr)
        if count and args.write:
            save_json(path, data)
        label = "authored" if (count and args.write) else ("would author" if count else "ok")
        print(f"  {label}: {path.relative_to(ROOT)} ({count} alias nodes)")
    print(f"\n[author_character_aliases] {total} authored alias nodes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
