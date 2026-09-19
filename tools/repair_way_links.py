#!/usr/bin/env python3
"""repair_way_links.py — make every way traversable from BOTH sides.

A way node should have an ``area -> way`` connection edge for each area it
touches, because the engine builds an area's exits from edges where the area
is the SOURCE (``AreaDescription.build_exits_for_area``). Scenarios generated
with only the ``way -> area`` half leave those areas with zero exits, so both
players and background characters get stranded.

This tool finds every way and adds the missing ``area -> way`` edge (empty
direction — the engine derives the exit handle from the way's own name). It
does not invent new ways or move anything. Existing directed edges are left
untouched.

Usage:
    python tools/repair_way_links.py data/scenarios/kraktooth_goblin_camp.json
    python tools/repair_way_links.py --all
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def repair(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or {}
    edges = graph.get("edges") or []

    existing = {(e.get("source"), e.get("target"))
                for e in edges if e.get("type") == "connection"}

    added = 0
    for nid, node in list(nodes.items()):
        if node.get("type") != "way":
            continue
        area_ids = set()
        for e in edges:
            if e.get("type") != "connection":
                continue
            if e.get("target") == nid and (nodes.get(e.get("source")) or {}).get("type") == "area":
                area_ids.add(e["source"])
            if e.get("source") == nid and (nodes.get(e.get("target")) or {}).get("type") == "area":
                area_ids.add(e["target"])
        for aid in sorted(area_ids):
            # area -> way  (the side the exit builder reads)
            if (aid, nid) not in existing:
                edges.append({"source": aid, "target": nid,
                              "type": "connection", "properties": {}})
                existing.add((aid, nid))
                added += 1
            # way -> area  (needed for the builder to name the destination)
            if (nid, aid) not in existing:
                edges.append({"source": nid, "target": aid,
                              "type": "connection", "properties": {}})
                existing.add((nid, aid))
                added += 1

    if added:
        graph["edges"] = edges
        data["graph"] = graph
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return added


def _slug(text):
    out = "".join(ch if ch.isalnum() else "_" for ch in text.lower())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def connect_areas(path: Path, a_name, a_dir, b_name, b_dir, way_name):
    """Add a new bidirectional way between two existing areas."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    graph = data["graph"]
    nodes = graph["nodes"]
    edges = graph["edges"]

    by_name = {n.get("name"): nid for nid, n in nodes.items() if n.get("type") == "area"}
    if a_name not in by_name or b_name not in by_name:
        raise SystemExit(f"Unknown area(s): {a_name!r} / {b_name!r}")

    way_id = f"way_{_slug(way_name)}"
    if way_id in nodes:
        return 0
    nodes[way_id] = {
        "id": way_id, "type": "way", "name": way_name,
        "properties": {"current_state": "open",
                       "description": f"A passage between {a_name} and {b_name}."},
    }
    a_id, b_id = by_name[a_name], by_name[b_name]
    for src, dst, direction in ((a_id, way_id, a_dir), (way_id, b_id, ""),
                                (b_id, way_id, b_dir), (way_id, a_id, "")):
        edges.append({"source": src, "target": dst, "type": "connection",
                      "properties": ({"direction": direction} if direction else {})})
    graph["edges"] = edges
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true", help="every data/scenarios/*.json")
    ap.add_argument("--connect", default="",
                    help="add a way: 'AreaA|dirA|AreaB|dirB' (needs an explicit file)")
    args = ap.parse_args()

    if args.files:
        targets = [ROOT / f for f in args.files]
    elif args.all:
        targets = sorted((ROOT / "data" / "scenarios").glob("*.json"))
    else:
        targets = [ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"]

    if args.connect:
        parts = [p.strip() for p in args.connect.split("|")]
        if len(parts) != 4:
            raise SystemExit("--connect expects 'AreaA|dirA|AreaB|dirB'")
        a, da, b, db = parts
        way_name = f"passage between {a} and {b}"
        for path in targets:
            added = connect_areas(path, a, da, b, db, way_name)
            state = f"connected {a} <-> {b}" if added else "already connected"
            print(f"  {state}: {path.relative_to(ROOT)}")
        return

    total = 0
    for path in targets:
        if not path.exists():
            print(f"  skip (missing): {path}")
            continue
        added = repair(path)
        total += added
        mark = "repaired" if added else "ok"
        print(f"  {mark:>9}: {path.relative_to(ROOT)} (+{added} edges)")
    print(f"\n[repair] {total} missing area->way edges added")


if __name__ == "__main__":
    main()
