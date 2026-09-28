#!/usr/bin/env python3
"""claim_areas.py — declare who holds which areas, and who belongs to whom.

task-550: an area with a need-resource and no claimant is a shared resource
that everybody converges on, which is how 4 of 5 humans ended up living in the
goblin camp. This stamps the two symmetric tags that make a claim:

* ``held_by:<faction>`` on the area
* ``faction:<faction>`` on the character

Both halves come from one table, because a claim whose membership nobody carries
is only half a claim, and the two drifting apart is the failure this task is
about. Unclaimed areas are left alone on purpose: an area with no ``held_by``
tag is a **commons**, not an error, so a road or the wilderness needs no row.

Areas are selected by the tag an author already gave them (``goblin_camp``), not
by name, so a new camp area is claimed by tagging it correctly rather than by
editing a list here.

Idempotent, and **dry-run by default**.

Usage:
    python tools/claim_areas.py
    python tools/claim_areas.py --write
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.character_identity import authored_character_node_id  # noqa: E402
from engine.ownership import FACTION_PREFIX, HELD_BY_PREFIX  # noqa: E402
from tools.scenario_refs import load_json, save_json  # noqa: E402

DEFAULT_TARGET = "data/scenarios/kraktooth_goblin_camp.json"

#: faction -> (area tags that mark its holdings, character tags that mark members)
#
#: The Kraktooth camp. `goblin` holds the 21 areas tagged `goblin_camp`;
#: `human` holds Eldenford, the road and the farm the humans actually live on
#: or work. The Murk Lake, the Raven River and the wilds are deliberately NOT
#: claimed: they are commons, and that is the interesting case — a goblin can
#: drink from the Raven River without anybody minding, and nobody has to author
#: that anywhere.
CLAIMS = {
    "goblin": {
        "areas": ("goblin_camp",),
        "members": ("goblin",),
    },
    "human": {
        "areas": ("village",),
        "members": ("human",),
    },
}


def _area_tag(tag: str) -> str:
    return f"{HELD_BY_PREFIX}{tag}"


def _faction_tag(tag: str) -> str:
    return f"{FACTION_PREFIX}{tag}"


def _add_tag(tags, new):
    """Append *new* unless it is already there, case-insensitively."""
    lowered = {str(t).lower() for t in tags}
    if str(new).lower() in lowered:
        return False
    tags.append(new)
    return True


def claim(data: dict, claims) -> dict:
    """Stamp the faction/holding tags onto *data*. Returns a report."""
    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or {}
    players = data.get("players") or {}
    report = {"areas": [], "characters": []}

    for faction, spec in sorted(claims.items()):
        area_tags = {str(t).lower() for t in spec.get("areas", ())}
        for node_id, node in sorted(nodes.items()):
            if node.get("type") != "area":
                continue
            props = node.setdefault("properties", {})
            tags = props.setdefault("tags", [])
            node_tags = {str(t).lower() for t in tags}
            if area_tags and not (area_tags & node_tags):
                continue
            if _add_tag(tags, _area_tag(faction)):
                report["areas"].append(
                    (node.get("name", node_id), _area_tag(faction))
                )

        member_tags = {str(t).lower() for t in spec.get("members", ())}
        for key, player in sorted(players.items()):
            if not isinstance(player, dict):
                continue
            tags = player.setdefault("tags", [])
            if member_tags and not ({str(t).lower() for t in tags} & member_tags):
                continue
            added = _add_tag(tags, _faction_tag(faction))
            authored = nodes.get(authored_character_node_id(
                str(player.get("name") or key)
            ))
            if isinstance(authored, dict):
                node_tags = authored.setdefault("properties", {}).setdefault("tags", [])
                added = _add_tag(node_tags, _faction_tag(faction)) or added
            if added:
                report["characters"].append(
                    (player.get("name", key), _faction_tag(faction))
                )

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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
        report = claim(data, CLAIMS)
        count = len(report["areas"]) + len(report["characters"])
        total += count
        for name, tag in report["areas"]:
            print(f"  area  {name}: {tag}")
        for name, tag in report["characters"]:
            print(f"  char  {name}: {tag}")
        if count and args.write:
            save_json(path, data)
        label = "claimed" if (count and args.write) else ("would claim" if count else "ok")
        print(f"  {label}: {path.relative_to(ROOT)} "
              f"({len(report['areas'])} areas, {len(report['characters'])} characters)")
    print(f"\n[claim_areas] {total} tags added")
    return 0


if __name__ == "__main__":
    sys.exit(main())
