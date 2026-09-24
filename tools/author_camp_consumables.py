"""Author data-driven consumption for the camp's consumables (task-424).

The five items inside ``kraktooth_goblin_camp.json`` did not reliably author their
own consumption: berries and dried meat had no trigger at all, and bread,
mushrooms and the water skin carried **legacy positive** ``adjust_vital`` amounts
that, under the current *drive* semantics (Hunger/Thirst rise), would increase the
need instead of relieving it. They only "worked" because the background consume
path silently fell back to ``MEAL_RESTORE``/``DRINK_RESTORE``; once the authored
path is live, the data itself must be right.

This gives each one its authored trigger:

* every food item: ``on_eat`` → ``adjust_vital`` Hunger (the fallback amount, so
  camp survival is unchanged);
* the water skin: ``on_drink`` → ``adjust_vital`` Thirst, and ``on_depleted`` →
  ``set_state empty`` so it **empties and persists** instead of vanishing on the
  last charge (the acceptance's "glass" case).

Depletion is **not** authored: since task-508 the engine spends ``uses`` on
consume exactly as it does for ``use``, so a hand-written ``adjust_uses`` would
double-spend the charge.

Deterministic and idempotent: stable trigger ids, and an existing trigger of the
same type is rewritten in place, so re-running changes nothing and the scenario
diff stays small. Edits the raw JSON surgically (never
``world.to_scenario_dict()``, which rewrites every character) — dry-run by default.

    python tools/author_camp_consumables.py            # show the plan
    python tools/author_camp_consumables.py --write    # apply it

The restore amounts mirror ``background_simulation.MEAL_RESTORE`` /
``DRINK_RESTORE`` on purpose: this change moves the restore from a constant into
authored data *without* changing how long the camp's finite larder lasts.
Differentiating the items (a berry is not a steak; mushrooms can make you sick) is
a later tuning pass and would need its own soak.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.background_simulation import MEAL_RESTORE, DRINK_RESTORE  # noqa: E402

#: Food items and the vital they relieve.
FOOD_ITEMS = ("item_berries", "item_bread", "item_dried_meat", "item_mushrooms")
#: Drink items and the vital they relieve.
DRINK_ITEMS = ("item_water_skin",)


def _food_effects(item_id):
    # task-508: the engine spends `uses` on consume (as it does for `use`), so
    # the trigger owns only the restore. Hand-writing adjust_uses here would
    # double-spend the charge.
    return [
        {"params": {"amount": -MEAL_RESTORE, "stat": "Hunger", "target": "self"},
         "type": "adjust_vital"},
    ]


def _drink_effects(item_id):
    # task-508: depletion is the engine's, not the trigger's (see _food_effects).
    return [
        {"params": {"amount": -DRINK_RESTORE, "stat": "Thirst", "target": "self"},
         "type": "adjust_vital"},
    ]


def _empties_effects():
    return [
        {"params": {"message": "The water skin is empty.", "state": "empty"},
         "type": "set_state"},
    ]


def _node_map(nodes):
    return nodes if isinstance(nodes, dict) else {n.get("id"): n for n in nodes}


def _add_node(nodes, node):
    if isinstance(nodes, dict):
        nodes[node["id"]] = node
    else:
        nodes.append(node)


def _trigger_of(data, item_id, trigger_type):
    """The trigger node id on *item_id* for *trigger_type*, or None.

    Reads the edge's ``trigger_type`` first (that is what the engine filters on),
    then the trigger node's own property as a fallback for hand-authored data.
    """
    node_map = _node_map(data["graph"]["nodes"])
    for edge in data["graph"]["edges"]:
        if edge.get("source") != item_id or edge.get("type") != "triggers":
            continue
        edge_tt = (edge.get("properties") or {}).get("trigger_type")
        node = node_map.get(edge.get("target"))
        node_tt = (node or {}).get("properties", {}).get("trigger_type")
        for tt in (edge_tt, node_tt):
            if isinstance(tt, (list, tuple)):
                if trigger_type in tt:
                    return edge.get("target")
            elif tt == trigger_type:
                return edge.get("target")
    return None


def _props(trigger_type, effects):
    return {"effects": effects, "once": False, "trigger_type": trigger_type}


def _author(data, item_id, trigger_type, effects, stable_id, log):
    """Create or rewrite the item's single trigger of *trigger_type*.

    Returns True when a node was created, False when an existing one was updated.
    """
    existing = _trigger_of(data, item_id, trigger_type)
    if existing:
        node_map = _node_map(data["graph"]["nodes"])
        node = node_map.get(existing)
        if node is not None:
            node["properties"] = _props(trigger_type, effects)
        for edge in data["graph"]["edges"]:
            if edge.get("source") == item_id and edge.get("target") == existing \
                    and edge.get("type") == "triggers":
                edge["properties"] = {"trigger_type": trigger_type}
        log(f"  = {item_id:<20} {trigger_type:<12} updated {existing}"
            f" ({len(effects)} effect(s))")
        return False

    node = {
        "id": stable_id,
        "type": "logic_trigger",
        "name": f"{trigger_type} -> {effects[0]['type']}",
        "properties": _props(trigger_type, effects),
    }
    _add_node(data["graph"]["nodes"], node)
    data["graph"]["edges"].append({
        "source": item_id, "target": stable_id, "type": "triggers",
        "properties": {"trigger_type": trigger_type},
    })
    log(f"  + {item_id:<20} {trigger_type:<12} created {stable_id}"
        f" ({len(effects)} effect(s))")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario",
                    default=os.path.join("data", "scenarios", "kraktooth_goblin_camp.json"))
    ap.add_argument("--write", action="store_true", help="save the scenario (otherwise dry run)")
    args = ap.parse_args()

    path = args.scenario if os.path.isabs(args.scenario) else os.path.join(ROOT, args.scenario)
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)

    node_map = _node_map(data["graph"]["nodes"])
    before = len(node_map)
    created = updated = missing = 0

    def log(msg):
        print(msg)

    for item_id in FOOD_ITEMS:
        if item_id not in node_map:
            log(f"  ! no such item: {item_id}")
            missing += 1
            continue
        if _author(data, item_id, "on_eat", _food_effects(item_id),
                   f"trigger_{item_id}_on_eat", log):
            created += 1
        else:
            updated += 1

    for item_id in DRINK_ITEMS:
        if item_id not in node_map:
            log(f"  ! no such item: {item_id}")
            missing += 1
            continue
        for trigger_type, effects, stable in (
            ("on_drink", _drink_effects(item_id), f"trigger_{item_id}_on_drink"),
            ("on_depleted", _empties_effects(), f"trigger_{item_id}_on_depleted"),
        ):
            if _author(data, item_id, trigger_type, effects, stable, log):
                created += 1
            else:
                updated += 1

    after = len(_node_map(data["graph"]["nodes"]))
    print()
    print(f"authored {created} trigger(s), updated {updated}, missing {missing}; "
          f"graph {before} -> {after} nodes")
    if missing:
        return 1
    if not args.write:
        print("dry run — rerun with --write to save")
        return 0
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print("wrote", os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
