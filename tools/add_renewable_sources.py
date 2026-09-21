"""Place renewable world sources into a scenario (task-410).

Adds the library's plant items to a scenario as standing nodes, wired through the
**real** library placement path (`_spawn_library_item_node`) so the node's
properties and its trigger graph are exactly what the app would produce — no
second implementation to drift.

Dry-run by default; `--write` saves the scenario back.

    python tools/add_renewable_sources.py                      # show the plan
    python tools/add_renewable_sources.py --write              # apply it

A plant is a *renewable source*: an untagged standing item that grows a counter,
and at 100 spawns its produce into itself, capped. It deliberately carries no
`food` tag — consumption finds targets by tag, and `_consume_here` deletes a node
it consumes, so a tagged bush would simply be eaten.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from routes.helpers import _save_scenario
from routes.library_ops import _spawn_library_item_node, _lookup_library_item

#: (library item, area name, how many). Wilderness and water margins are where a
#: camp would actually forage; the pen and the pit are not.
DEFAULT_PLANTS = [
    ("bush_of_berries", "Deep Forest", 3),
    ("bush_of_berries", "Water Source", 1),
    ("bush_of_berries", "Camp Entrance Trail", 1),
]

#: Service fixtures — items that provide an action rather than produce anything.
#: A wash spot is `use`d to clean up and never depletes (`uses: -1`). Tagged
#: `bathing`, NOT `water`: `DRINK_TAGS` contains "water" and `_consume_here`
#: deletes a node it consumes, so a thirsty goblin would drink the fixture and
#: destroy it. The water AREAS already carry `water` for drinking.
DEFAULT_FIXTURES = [
    ("wash_spot", "Water Source", 1),
    ("wash_spot", "Raven River", 1),
]

#: Tags that give a place a service. The camp has an area named "Waste Disposal"
#: but nothing marked it usable, so `relieve` treated it as open ground — and the
#: background tier had no relief step at all, which pinned everyone's Hygiene at 0.
DEFAULT_AREA_TAGS = {
    "Waste Disposal": ["latrine"],
}


def area_node_id(name):
    return "area_" + name.lower().replace("'", "").replace(" ", "_")


def remove_source(app, node_id):
    """Delete a placed source, its trigger nodes and anything it was holding.

    Needed because a source's triggers are copied at placement time: editing the
    library item does nothing to copies already in the scenario, so re-running
    with --replace is how a definition change reaches an authored world.
    """
    graph = app.world.graph
    if graph.get_node(node_id) is None:
        return False
    trigger_ids = [e.target for e in graph.get_edges_for_source(node_id)
                   if e.type == "triggers"]
    held_ids = [e.source for e in graph.get_edges_for_target(node_id, "in")]
    for hid in held_ids:            # produce the plant was holding
        graph.remove_node(hid)
    for tid in trigger_ids:
        graph.remove_node(tid)
    graph.remove_node(node_id)      # remove_node also severs its edges
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default=os.path.join("data", "scenarios", "kraktooth_goblin_camp.json"))
    ap.add_argument("--write", action="store_true", help="save the scenario (otherwise dry run)")
    ap.add_argument("--replace", action="store_true",
                    help="re-place sources that already exist, picking up library changes")
    args = ap.parse_args()

    stem = os.path.splitext(os.path.basename(args.scenario))[0]
    app = create_app()
    with open(args.scenario, encoding="utf-8") as fh:
        app.world.load_from_dict(json.load(fh))
    app.world._scenario_name = stem

    before = len(app.world.graph.nodes)

    # Service tags on areas (a latrine, a river) come first: a fixture with no
    # place to belong is just clutter.
    for area_name, tags in DEFAULT_AREA_TAGS.items():
        aid = area_node_id(area_name)
        node = app.world.graph.get_node(aid)
        if node is None:
            print("  ! no such area for tags: %s" % area_name)
            continue
        current = list(node.properties.get("tags") or [])
        added = [t for t in tags if t not in current]
        if added:
            node.properties["tags"] = current + added
            print("  # tagged %-22s +%s" % (area_name, ",".join(added)))
        else:
            print("  = %-28s already tagged" % area_name)

    placed = 0
    for item_id, area_name, count in DEFAULT_PLANTS + DEFAULT_FIXTURES:
        aid = area_node_id(area_name)
        if app.world.graph.get_node(aid) is None:
            print("  ! no such area: %s (%s)" % (area_name, aid))
            continue
        entry = _lookup_library_item(app, item_id)
        if not entry:
            print("  ! no such library item: %s" % item_id)
            continue
        for n in range(1, count + 1):
            # Deterministic id: the tool is re-runnable and the scenario file
            # stays diffable.
            stable_id = "%s_%s_%d" % (
                item_id,
                area_node_id(area_name)[len("area_"):],
                n,
            )
            if app.world.graph.get_node(stable_id) is not None:
                if not args.replace:
                    print("  = %-28s already present (use --replace)" % stable_id)
                    continue
                remove_source(app, stable_id)
                print("  ~ %-28s replaced" % stable_id)
            _spawn_library_item_node(
                app, item_id, entry, container_id=aid, node_id=stable_id
            )
            placed += 1
            print("  + %-28s in %s" % (stable_id, area_name))

    print()
    print("placed %d renewable source(s); graph %d -> %d nodes"
          % (placed, before, len(app.world.graph.nodes)))
    if not placed:
        return 1
    if not args.write:
        print("dry run — rerun with --write to save")
        return 0
    _save_scenario(app.world, name=stem)   # writes data/scenarios/<stem>.json
    print("wrote", os.path.join("data", "scenarios", stem + ".json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
