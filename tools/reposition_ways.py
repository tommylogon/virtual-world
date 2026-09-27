"""Reposition hand-authored ways to sit between the areas they join.

A way's canvas position is authored data, but it is stored once, absolutely, and
nothing recomputes it when either endpoint moves. Areas move whenever their grid
is repainted (a compile) or their scope's `map_offset` changes (task-523), so
every hand-authored way is *guaranteed* to go stale eventually — and in the
Kraktooth scenario all 31 of them had: drift of 1,235 to 1,850 canvas units, with
stored y values as low as -1653, i.e. off the top of the canvas.

That is what "the ways are not between the painted areas" is. The fix is to put
them back, once. It is deliberately NOT an automatic behaviour: removing or
silently relocating an author's way is their call, and the graph view is where
that decision belongs. This is a repair tool you run on purpose.

Generated ways are left alone — the compiler derives those from their own cells
and they cannot drift.

Usage:
    python tools/reposition_ways.py                 # dry run, reports what would change
    python tools/reposition_ways.py --write         # apply to the scenario
    python tools/reposition_ways.py --scenario X    # a different scenario
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO = "data/scenarios/kraktooth_goblin_camp.json"

#: A way this far from the midpoint of its endpoints is treated as stale. Not
#: zero, because a hand-placed way a hair off is still a hand-placed way and the
#: author may have meant it.
STALE_UNITS = 1.0


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def positioned(node):
    props = (node or {}).get("properties") or {}
    x, y = props.get("x"), props.get("y")
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return float(x), float(y)
    return None


def endpoints_of(graph):
    """way id -> distinct area ids it joins.

    Every connection is stored in both directions, so a way joining two areas
    lists each of them more than once. Distinct is what matters.
    """
    nodes = graph.get("nodes") or {}
    found = {}
    for edge in graph.get("edges") or []:
        if edge.get("type") != "connection":
            continue
        source, target = edge.get("source"), edge.get("target")
        source_kind = (nodes.get(source) or {}).get("type")
        target_kind = (nodes.get(target) or {}).get("type")
        if source_kind == "area" and target_kind == "way":
            bucket, area_id = found.setdefault(target, []), source
        elif source_kind == "way" and target_kind == "area":
            bucket, area_id = found.setdefault(source, []), target
        else:
            continue
        if area_id not in bucket:
            bucket.append(area_id)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--write", action="store_true",
                        help="apply the change (default is a dry run)")
    parser.add_argument("--include-generated", action="store_true",
                        help="also touch compiler-generated ways (off by default; "
                             "they derive their position from their own cells)")
    args = parser.parse_args()

    path = ROOT / args.scenario
    data = load(path)
    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or {}

    moved, skipped = [], []
    for way_id, area_ids in sorted(endpoints_of(graph).items()):
        way = nodes.get(way_id) or {}
        props = way.get("properties") or {}
        if props.get("generated") and not args.include_generated:
            skipped.append((way.get("name"), "generated"))
            continue
        places = [p for p in (positioned(nodes.get(a)) for a in area_ids) if p]
        if len(places) != 2:
            skipped.append((way.get("name"), f"{len(area_ids)} areas, {len(places)} placed"))
            continue
        here = positioned(way)
        if here is None:
            skipped.append((way.get("name"), "way has no x/y"))
            continue
        want = ((places[0][0] + places[1][0]) / 2.0, (places[0][1] + places[1][1]) / 2.0)
        drift = ((here[0] - want[0]) ** 2 + (here[1] - want[1]) ** 2) ** 0.5
        if drift <= STALE_UNITS:
            continue
        moved.append((drift, way_id, way.get("name"), here, want, area_ids))

    moved.sort(reverse=True)
    print(f"{args.scenario}")
    print(f"  {len(moved)} way(s) are not between the areas they join")
    print(f"  {len(skipped)} left alone\n")
    for drift, _way_id, name, here, want, area_ids in moved:
        ends = " ".join(str(nodes.get(a, {}).get("name", a)) for a in area_ids)
        print(f"  {str(name)[:34]:34} drift {drift:7.1f}  "
              f"({here[0]:7.1f},{here[1]:8.1f}) -> ({want[0]:6.1f},{want[1]:6.1f})  [{ends}]")
    if not moved:
        print("  nothing to do")
        return 0

    if not args.write:
        print("\ndry run — pass --write to apply")
        return 0

    for _drift, way_id, _name, _here, want, _areas in moved:
        props = nodes[way_id]["properties"]
        props["x"] = want[0]
        props["y"] = want[1]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nrepositioned {len(moved)} way(s) in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
