#!/usr/bin/env python3
"""Migrate legacy item effect props (effect_stat, effect_amount, effect_target) to triggers.

Task-332:
- Null/None keys are stripped as save pollution.
- Vitals (Hunger, Energy, Thirst, Hygiene, HP) are converted to on_use triggers with adjust_vital.
- Light items are converted to native light_source tags and light_level properties.
- Connection item in heist.json is converted to on_use_on set_state trigger.
- Idempotent and dry-run by default (--apply to write).
"""

import argparse
import glob
import json
import os
import sys

VITAL_CANONICAL = {
    "hunger": "Hunger",
    "energy": "Energy",
    "thirst": "Thirst",
    "hygiene": "Hygiene",
    "hp": "HP",
}


def migrate_item_props(props, item_id="item"):
    """Migrate legacy effect keys on an item property dict. Returns True if modified."""
    if not isinstance(props, dict):
        return False

    has_stat = "effect_stat" in props
    has_amt = "effect_amount" in props
    has_tgt = "effect_target" in props

    if not (has_stat or has_amt or has_tgt):
        return False

    stat = props.get("effect_stat")
    amt = props.get("effect_amount")
    tgt = props.get("effect_target")

    # 1. Null / falsy stat -> strip keys directly
    if not stat:
        props.pop("effect_stat", None)
        props.pop("effect_amount", None)
        props.pop("effect_target", None)
        return True

    stat_str = str(stat).strip()
    stat_lower = stat_str.lower()

    # 2. Vital stats
    if stat_lower in VITAL_CANONICAL:
        canonical_stat = VITAL_CANONICAL[stat_lower]
        try:
            amt_int = int(amt)
        except (ValueError, TypeError):
            amt_int = 0

        triggers = props.setdefault("triggers", [])
        if not isinstance(triggers, list):
            triggers = [triggers] if isinstance(triggers, dict) else []
            props["triggers"] = triggers

        trigger_id = f"trigger_{item_id}_vital_{stat_lower}"
        if not any(isinstance(t, dict) and t.get("id") == trigger_id for t in triggers):
            triggers.append({
                "id": trigger_id,
                "trigger_type": "on_use",
                "effects": [{
                    "type": "adjust_vital",
                    "params": {
                        "stat": canonical_stat,
                        "amount": amt_int,
                        "target": "self",
                    },
                }],
            })

        props.pop("effect_stat", None)
        props.pop("effect_amount", None)
        props.pop("effect_target", None)
        return True

    # 3. Light items
    if stat_lower == "light":
        try:
            amt_int = int(amt)
        except (ValueError, TypeError):
            amt_int = 40

        if amt_int > 0:
            tags = props.setdefault("tags", [])
            if isinstance(tags, list):
                if "light_source" not in tags:
                    tags.append("light_source")
            if "light_level" not in props or not props.get("light_level"):
                props["light_level"] = amt_int

            actions = props.get("actions")
            if isinstance(actions, list):
                if "toggle" not in actions and "light" not in actions:
                    actions.append("toggle")
            elif isinstance(actions, str):
                if "toggle" not in actions and "light" not in actions:
                    props["actions"] = f"{actions}, toggle"
            elif actions is None:
                props["actions"] = ["examine", "take", "toggle"]

            if "current_state" not in props:
                props["current_state"] = "unlit"

        props.pop("effect_stat", None)
        props.pop("effect_amount", None)
        props.pop("effect_target", None)
        return True

    # 4. Connection / way toggle (heist.json c4_explosive)
    if tgt == "connection" or stat_lower == "broken":
        triggers = props.setdefault("triggers", [])
        if not isinstance(triggers, list):
            triggers = []
            props["triggers"] = triggers
        trigger_id = f"trigger_{item_id}_set_state"
        if not any(isinstance(t, dict) and t.get("id") == trigger_id for t in triggers):
            triggers.append({
                "id": trigger_id,
                "trigger_type": "on_use_on",
                "effects": [{
                    "type": "set_state",
                    "params": {
                        "target": "target",
                        "state": stat_str,
                    },
                }],
            })
        props.pop("effect_stat", None)
        props.pop("effect_amount", None)
        props.pop("effect_target", None)
        return True

    # 5. Unknown stat: strip and report
    print(f"  [WARN] Unknown effect_stat '{stat}' on {item_id}; stripping keys")
    props.pop("effect_stat", None)
    props.pop("effect_amount", None)
    props.pop("effect_target", None)
    return True


def migrate_item_container(it, default_id="item"):
    """Handle item dict that may either hold props directly or in it['properties']."""
    if not isinstance(it, dict):
        return False
    modified = False
    iid = it.get("name") or it.get("node_id") or it.get("id") or default_id
    if migrate_item_props(it, iid):
        modified = True
    if "properties" in it and isinstance(it["properties"], dict):
        if migrate_item_props(it["properties"], iid):
            modified = True
    return modified


def migrate_file(fpath, apply_changes=False):
    """Scan and migrate one JSON file. Returns count of modified items."""
    try:
        with open(fpath, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Skipping {fpath}: {e}")
        return 0

    if not isinstance(data, dict):
        return 0

    modified_count = 0

    # Shape 0: root item dict (library/items/*.json)
    if migrate_item_container(data, data.get("name", "item")):
        modified_count += 1

    # Shape 1: graph nodes
    raw_nodes = (data.get("graph", {}) or {}).get("nodes", {})
    if isinstance(raw_nodes, dict):
        for nid, node in raw_nodes.items():
            if isinstance(node, dict) and "properties" in node:
                if migrate_item_props(node["properties"], nid):
                    modified_count += 1
    elif isinstance(raw_nodes, list):
        for node in raw_nodes:
            if isinstance(node, dict) and "properties" in node:
                nid = node.get("id", "item")
                if migrate_item_props(node["properties"], nid):
                    modified_count += 1

    # Shape 2: template areas
    areas = data.get("areas", {})
    if isinstance(areas, dict):
        for aname, adata in areas.items():
            if isinstance(adata, dict):
                for it in adata.get("items", []):
                    if isinstance(it, dict) and migrate_item_container(it, it.get("name", "item")):
                        modified_count += 1
    elif isinstance(areas, list):
        for adata in areas:
            if isinstance(adata, dict):
                for it in adata.get("items", []):
                    if isinstance(it, dict) and migrate_item_container(it, it.get("name", "item")):
                        modified_count += 1

    # Shape 3: item registry
    for iid, it in (data.get("item_registry", {}) or {}).items():
        if isinstance(it, dict) and migrate_item_container(it, iid):
            modified_count += 1

    # Shape 4: wrapped item definition
    if "item" in data and isinstance(data["item"], dict):
        if migrate_item_container(data["item"], data["item"].get("name", "item")):
            modified_count += 1

    # Shape 5: characters inventory (library/characters/*.json)
    for it in data.get("inventory", []):
        if isinstance(it, dict) and migrate_item_container(it, it.get("name", "item")):
            modified_count += 1

    # Shape 6: players block (scenarios/corsair.json etc)
    players = data.get("players", {})
    if isinstance(players, dict):
        for pname, pdata in players.items():
            if isinstance(pdata, dict):
                for it in pdata.get("inventory", []):
                    if isinstance(it, dict) and migrate_item_container(it, it.get("name", "item")):
                        modified_count += 1
    elif isinstance(players, list):
        for pdata in players:
            if isinstance(pdata, dict):
                for it in pdata.get("inventory", []):
                    if isinstance(it, dict) and migrate_item_container(it, it.get("name", "item")):
                        modified_count += 1

    for p in ("player", "character"):
        if p in data and isinstance(data[p], dict):
            for it in data[p].get("inventory", []):
                if isinstance(it, dict) and migrate_item_container(it, it.get("name", "item")):
                    modified_count += 1

    if modified_count > 0 and apply_changes:
        with open(fpath, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return modified_count


def main():
    parser = argparse.ArgumentParser(description="Migrate legacy item effect props to triggers.")
    parser.add_argument("--apply", action="store_true", help="Apply changes to files (default is dry-run)")
    args = parser.parse_args()

    patterns = [
        "data/scenarios/*.json",
        "data/library/**/*.json",
        "tests/fixtures/*.json",
        "world_template.json",
    ]

    files = set()
    for p in patterns:
        for f in glob.glob(p, recursive=True):
            files.add(f.replace("\\", "/"))

    total_modified = 0
    total_files = 0

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Running legacy item effect migration ({mode}) ===")

    for fpath in sorted(files):
        count = migrate_file(fpath, apply_changes=args.apply)
        if count > 0:
            total_modified += count
            total_files += 1
            print(f"  {fpath}: {count} item(s) migrated")

    print(f"\nTotal: {total_modified} item(s) across {total_files} file(s).")
    if not args.apply and total_modified > 0:
        print("Run with --apply to commit these changes to disk.")


if __name__ == "__main__":
    main()
