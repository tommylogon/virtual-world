"""
One-off migration: rename the Kraktooth placeholder human to Jake Halloway.

The scenario carried a machine-named NPC, `player_human_explorer`, whose node
carried a generic traveler personality. It is Jake Halloway -- the character in
`data/library/characters/jake.json` -- and Kiala's card makes the link explicit:
as a child her tribe was saved from orc raiders by a human adventurer she has
spent years tracking down. She is standing in the camp he walked into.

A rename here is invasive because a player is referenced three ways and all
three must move together:

  1. the `players` dict key            -> `"Jake Halloway"`
  2. the player's own `name` field     -> `"Jake Halloway"`
  3. the graph node id, which is        `"player_player_human_explorer"`
     `player_` + the old name underscored, and every edge endpoint naming it

`engine/character_identity.anchor_node_id` derives the anchor from the players
dict key, so leaving the node id alone does not merely orphan the edges -- the
collapse at load finds no anchor to merge into and the world keeps two
character nodes for one person. Renaming the key and the node together is the
only form that survives `reindex()`.

Relationships are keyed by display name, so any relationship pointing at the
old name has to move too. The old data contains one that points at itself
("Human Explorer"), which is dropped rather than renamed -- a character does not
have a relationship with their own name.

Idempotent: re-running finds nothing to do.
"""

import argparse
import json
import sys
from pathlib import Path

OLD_NAME = "player_human_explorer"
OLD_NODE_ID = "player_player_human_explorer"

# The saved data is not internally consistent about this character's name. The
# players key and node name use the machine name; the one self-reference
# inside `relationships` uses a hand-typed display form ("Human Explorer") that
# is not a case or underscore variant of it. All of these resolve to the same
# person, so all of them must be recognized here or the rename leaves a dangling
# key behind. Compare on a squashed lowercase form.
OLD_NAME_VARIANTS = {
    OLD_NAME,
    OLD_NAME.replace("_", " "),
    OLD_NAME.title().replace("_", " "),
    "Human Explorer",
}


def _squash(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


OLD_SQUASHED = {_squash(v) for v in OLD_NAME_VARIANTS}
NEW_NAME = "Jake Halloway"
NEW_NODE_ID = "player_Jake_Halloway"

SCENARIO = Path("data/scenarios/kraktooth_goblin_camp.json")
LIBRARY = Path("data/library/characters")


def canonical_node_id(name: str) -> str:
    """Mirror engine/character_identity.canonical_character_node_id."""
    return f"player_{name}".replace(" ", "_")


def _rename_references(doc, new: str) -> int:
    """Move every display-name reference to this character over to `new`.

    Relationships are keyed by display name in both directions, so a rename
    orphans anyone still pointing at the old name. This walks *every* player's
    relationship map rather than only the renamed player's own.
    """
    moved = 0
    new_squashed = _squash(new)
    for player_name, player in (doc.get("players") or {}).items():
        rels = player.get("relationships")
        if not isinstance(rels, dict):
            continue
        # Inside this character's own map, any alias of their name is a
        # self-reference -- the machine name and the hand-typed display form
        # are the same person pointing at themselves, not two people. Renaming
        # such a key onto the new name would leave a character in a
        # relationship with themselves, so it is dropped instead.
        own_aliases = OLD_SQUASHED if _squash(player_name) in OLD_SQUASHED else {new_squashed}
        for key in [k for k in rels if _squash(k) in own_aliases]:
            del rels[key]
            moved += 1
        for key in [k for k in rels if _squash(k) in OLD_SQUASHED]:
            record = rels.pop(key)
            if new in rels:
                # Two records for one person: keep the more developed one
                # rather than dropping a bond a soak already advanced.
                for field in ("closeness", "interaction_count", "last_interaction_tick"):
                    if record.get(field, 0) > rels[new].get(field, 0):
                        rels[new][field] = record[field]
                moved += 1
                continue
            rels[new] = record
            moved += 1
    return moved


def migrate_scenario(path: Path, write: bool = False) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    players = doc.get("players") or {}

    if OLD_NAME not in players:
        print(f"{path}: '{OLD_NAME}' not present -- already migrated.")
        return {"changed": False}

    # 1/2. players dict key + the player's own name field.
    doc["players"][NEW_NAME] = players.pop(OLD_NAME)
    doc["players"][NEW_NAME]["name"] = NEW_NAME

    # 3. graph node id + its name field, then every edge endpoint.
    nodes = doc.get("graph", {}).get("nodes", {})
    edges = doc.get("graph", {}).get("edges", [])
    if OLD_NODE_ID not in nodes:
        raise SystemExit(
            f"{path}: expected graph node '{OLD_NODE_ID}'. Refusing to guess -- "
            "the node id and the players key must move together."
        )
    nodes[NEW_NODE_ID] = nodes.pop(OLD_NODE_ID)
    nodes[NEW_NODE_ID]["id"] = NEW_NODE_ID
    nodes[NEW_NODE_ID]["name"] = NEW_NAME

    rewired = 0
    for edge in edges:
        for end in ("source", "target"):
            if edge.get(end) == OLD_NODE_ID:
                edge[end] = NEW_NODE_ID
                rewired += 1

    rels_moved = _rename_references(doc, NEW_NAME)

    if canonical_node_id(NEW_NAME) != NEW_NODE_ID:
        raise SystemExit(
            f"canonical id for {NEW_NAME!r} is {canonical_node_id(NEW_NAME)!r}, "
            f"not {NEW_NODE_ID!r} -- the anchor rule changed; re-check this tool."
        )

    print(f"{path}:")
    print(f"  players key       {OLD_NAME!r} -> {NEW_NAME!r}")
    print(f"  graph node id     {OLD_NODE_ID!r} -> {NEW_NODE_ID!r}")
    print(f"  edges rewired     {rewired}")
    print(f"  relationships     {rels_moved} key(s) resolved to {NEW_NAME!r}")

    if write:
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"  written to {path}")
    return {"changed": True, "rewired": rewired, "rels": rels_moved}


def rename_library_entry(write: bool = False) -> None:
    """The library already holds a richer `player_human_explorer.json` stub.

    Left alone, it becomes a second, contradicting entry for the same person
    under a name nothing refers to. It is removed here and re-authored
    separately from the scenario, which is the source of truth.
    """
    stale = LIBRARY / f"{OLD_NAME}.json"
    if not stale.exists():
        return
    if stale.exists() and write:
        stale.unlink()
        print(f"{stale}: removed (superseded by {NEW_NAME}.json)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help="write changes; default is a dry run")
    args = ap.parse_args()
    migrate_scenario(SCENARIO, write=args.write)
    rename_library_entry(write=args.write)
    return 0


if __name__ == "__main__":
    sys.exit(main())