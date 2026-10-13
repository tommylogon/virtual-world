"""Author Mikka's scrap pursuit into kraktooth (task-426, updated by task-818).

Adds the one inert prop the run needs — a Scrap item at the Scrap Pile — and the
pursuit **assignment on Mikka herself** (``Player.active_pursuit``): Scrap Pile ->
take scrap -> Workshop -> drop. A pursuit is character data, not a world node
(task-818), so this writes the player block, not a graph node.

Idempotent; dry-run by default, ``--write`` saves. The scrap item carries no
food/water/recreation tag, so it cannot change which areas any survival need
travels to — the failure mode that made the 2026 task-409 co-location pass
degrade the camp. This adds one pursuit for a single character and nothing else.

    python tools/add_scrap_run.py            # show what would change
    python tools/add_scrap_run.py --write    # apply it
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIO = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"

SCRAP_ID = "item_scrap"
PURSUIT_ID = "pursuit_mikka_scrap_run"
SCRAP_PILE = "area_scrap_pile"
ACTOR = "Mikka"             # the players block is keyed by display name
SOURCE = "Scrap Pile"
SINK = "Workshop"
LABEL = "scrap_run"


def main():
    ap = argparse.ArgumentParser(description="Author Mikka's scrap run (task-426)")
    ap.add_argument("--write", action="store_true", help="save the scenario")
    args = ap.parse_args()

    data = json.loads(SCENARIO.read_text(encoding="utf-8"))
    graph = data["graph"]
    nodes = graph["nodes"]
    edges = graph["edges"]
    players = data.get("players") or {}
    added = []

    if SCRAP_ID not in nodes:
        nodes[SCRAP_ID] = {
            "id": SCRAP_ID, "type": "item", "name": "Scrap",
            "properties": {
                "name": "Scrap",
                "tags": ["scrap", "tool", "oddment"],
                "weight": 1.0,
                "uses": -1,
                "actions": [],
            },
        }
        added.append(f"node {SCRAP_ID}")
    if not any(e.get("source") == SCRAP_ID and e.get("target") == SCRAP_PILE
               and e.get("type") == "in" for e in edges):
        edges.append({"source": SCRAP_ID, "target": SCRAP_PILE, "type": "in",
                      "properties": {}})
        added.append(f"edge {SCRAP_ID} -in-> {SCRAP_PILE}")

    mikka = players.get(ACTOR)
    if mikka is None:
        print(f"error: no player {ACTOR!r} in the scenario's players block")
        return
    if not mikka.get("active_pursuit"):
        mikka["active_pursuit"] = {
            "assignment_id": PURSUIT_ID,
            "template_id": "haul",
            "label": LABEL,
            "reason": "Move scrap to the workshop for repairs.",
            "bindings": {"source": SOURCE, "item": "scrap", "sink": SINK},
            "step_index": 0,
            "repeat": False,
        }
        added.append(f"active_pursuit on {ACTOR} ({LABEL})")

    if not added:
        print("nothing to do — the scrap run is already authored")
        return
    for item in added:
        print("add:", item)
    if args.write:
        # The scenario ships with CRLF and no trailing newline; json.dumps emits
        # LF, so convert explicitly and write bytes to avoid newline translation
        # (Path.write_text would rewrite every line and bury the real change).
        text = json.dumps(data, indent=2, ensure_ascii=False).replace("\n", "\r\n")
        SCENARIO.write_bytes(text.encode("utf-8"))
        print(f"written to {SCENARIO}")
    else:
        print("(dry run — pass --write to save)")


if __name__ == "__main__":
    main()
