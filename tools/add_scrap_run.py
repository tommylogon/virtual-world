"""Author Mikka's scrap pursuit into kraktooth (task-426).

Adds the one inert prop the run needs — a Scrap item at the Scrap Pile — and a
``pursuit`` node declaring the haul: Scrap Pile -> take scrap -> Workshop -> drop.

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
ACTOR = "player_Mikka"      # id, not display name (AGENTS: data keys by id)
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

    if PURSUIT_ID not in nodes:
        nodes[PURSUIT_ID] = {
            "id": PURSUIT_ID, "type": "pursuit", "name": LABEL,
            "properties": {
                "pursuit_template": "haul",
                "actor": ACTOR,
                "source": SOURCE,
                "item": "scrap",
                "sink": SINK,
                "label": LABEL,
                "repeat": False,
            },
        }
        added.append(f"node {PURSUIT_ID}")

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
