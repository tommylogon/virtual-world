"""Inspect and repair way connection wiring in a VirtualWorld graph.

Fixes two corruption patterns that accumulate in saved worlds:

1. Phantom edges — connection edges whose source/target does not resolve
   to any node (case-insensitively). E.g. edges referencing a legacy
   mixed-case id like ``area_Task_18_-_Room_4`` after the node id was
   normalized to ``area_task_18_-_room_4``.
2. Stale multi-side wiring — a way connected to MORE than two areas
   (leftover edges from an earlier connect that was never cleaned up).

For every way the script computes the canonical pair of areas (from the
way's ``area_from`` / ``area_to`` properties, resolved by name) and plans:
- DROP  — phantom edges and edges to areas outside the canonical pair
- REMAP — keep the edge but rewrite source/target to the canonical
  (lowercase) node id

By default it only *prints* the plan (dry run). Pass ``--apply`` to
write the changes back to a JSON world file, or ``--live`` to apply them
against a running server on port 4444 via its API.
"""
import argparse
import json
import sys
import urllib.request


def resolve_endpoint(canonical, node_id):
    """Resolve *node_id* to the stored node id (case-insensitive) or None."""
    if node_id in canonical:
        return node_id
    return canonical.get(node_id.lower())


def build_index(nodes_dict):
    """Return (canonical, names) maps from a nodes dict."""
    canonical = {}
    names = {}
    for nid, node in nodes_dict.items():
        canonical.setdefault(nid.lower(), nid)
        node_name = (node or {}).get("name") or nid
        names.setdefault(str(node_name).lower(), nid)
    return canonical, names


def plan_for_graph(nodes_dict, edges):
    """Return a list of change dicts describing edge repairs.

    Each change: {action: DROP|REMAP, edge: {...}, way: str, detail: str}
    """
    canonical, names = build_index(nodes_dict)
    changes = []

    # Group connection edges by (canonical way id).
    way_edges = {}
    for e in edges:
        if e.get("type") != "connection":
            continue
        src, tgt = e.get("source", ""), e.get("target", "")
        src_r, tgt_r = resolve_endpoint(canonical, src), resolve_endpoint(canonical, tgt)
        if src_r is None or tgt_r is None:
            changes.append({
                "action": "DROP",
                "edge": e,
                "way": src_r or tgt_r or f"{src}->{tgt}",
                "detail": f"phantom endpoint ({src} -> {tgt})",
            })
            continue
        src_node = nodes_dict.get(src_r, {})
        tgt_node = nodes_dict.get(tgt_r, {})
        if src_node.get("type") == "way":
            way_id = src_r
            other = tgt_r
        elif tgt_node.get("type") == "way":
            way_id = tgt_r
            other = src_r
        else:
            continue  # not a way connection edge
        way_edges.setdefault(way_id, []).append((e, other))

    for way_id, pairs in way_edges.items():
        way_node = nodes_dict.get(way_id, {})
        props = (way_node or {}).get("properties", {})
        from_name = props.get("area_from", "")
        to_name = props.get("area_to", "")
        from_id = names.get(str(from_name).lower()) if from_name else None
        to_id = names.get(str(to_name).lower()) if to_name else None
        desired = {from_id, to_id} if (from_id and to_id) else set()
        desired.discard(None)

        groups = {}
        for e, other in pairs:
            groups.setdefault(other, []).append((e, other))

        if len(groups) <= 2:
            # Remap endpoints of kept edges to canonical ids.
            for e, other in pairs:
                src_r = resolve_endpoint(canonical, e["source"])
                tgt_r = resolve_endpoint(canonical, e["target"])
                if src_r != e["source"] or tgt_r != e["target"]:
                    changes.append({
                        "action": "REMAP",
                        "edge": e,
                        "way": way_id,
                        "detail": f"endpoint case: {e['source']}->{e['target']} => {src_r}->{tgt_r}",
                    })
            continue

        # More than two areas — pick the canonical pair, drop the rest.
        if desired and desired.issubset(set(groups.keys())):
            keep = desired
            pair_source = "area_from/area_to props"
        else:
            def score(other):
                entries = groups[other]
                canon_area_edges = [x for x, o in entries if x["source"] == other]
                views = sum(1 for x in canon_area_edges
                            if (x.get("properties", {}).get("visible_in_direction") or "").strip())
                cards = sum(1 for x in canon_area_edges
                            if (x.get("properties", {}).get("cardinal") or "").strip())
                return (views + cards, len(entries))
            ranked = sorted(groups.keys(), key=score, reverse=True)
            keep = set(ranked[:2])
            pair_source = f"best two by view/cardinal ({', '.join(sorted(keep))})"

        for e, other in pairs:
            if other in keep:
                src_r = resolve_endpoint(canonical, e["source"])
                tgt_r = resolve_endpoint(canonical, e["target"])
                if src_r != e["source"] or tgt_r != e["target"]:
                    changes.append({
                        "action": "REMAP",
                        "edge": e,
                        "way": way_id,
                        "detail": f"endpoint case: {e['source']}->{e['target']} => {src_r}->{tgt_r}",
                    })
            else:
                changes.append({
                    "action": "DROP",
                    "edge": e,
                    "way": way_id,
                    "detail": f"stale side ({other}) — keeping {', '.join(sorted(keep))} ({pair_source})",
                })

    return changes


def apply_to_file(nodes_dict, edges, changes):
    """Rewrite edges in place; returns count applied."""
    applied = 0
    for ch in changes:
        e = ch["edge"]
        try:
            if ch["action"] == "REMAP":
                canonical, _ = build_index(nodes_dict)
                e["source"] = resolve_endpoint(canonical, e["source"])
                e["target"] = resolve_endpoint(canonical, e["target"])
            else:
                edges.remove(e)
            applied += 1
        except ValueError:
            pass
    return applied


def apply_to_live(changes, base_url):
    """Apply changes against a running server via its API."""
    applied = 0
    for ch in changes:
        e = ch["edge"]
        if ch["action"] == "REMAP":
            canonical, _ = build_index(_live_nodes(base_url))
            src_r = resolve_endpoint(canonical, e["source"])
            tgt_r = resolve_endpoint(canonical, e["target"])
            # Delete old edge first (add_edge dedupes case-insensitively, so
            # creating the canonical edge while the mixed-case one still exists
            # would be a silent no-op).
            delete_payload = json.dumps({
                "source": e["source"], "target": e["target"], "type": e["type"]
            }).encode()
            req = urllib.request.Request(
                f"{base_url}/api/graph/edge",
                data=delete_payload, headers={"Content-Type": "application/json"},
                method="DELETE")
            try:
                urllib.request.urlopen(req)
            except Exception as exc:
                print(f"  !! delete failed: {exc}")
                continue
            create_payload = json.dumps({
                "source": src_r, "target": tgt_r, "type": e["type"],
                "properties": e.get("properties", {}),
            }).encode()
            req = urllib.request.Request(
                f"{base_url}/api/graph/edge",
                data=create_payload, headers={"Content-Type": "application/json"},
                method="POST")
            try:
                urllib.request.urlopen(req)
            except Exception as exc:
                print(f"  !! recreate failed: {exc}")
                continue
        else:
            delete_payload = json.dumps({
                "source": e["source"], "target": e["target"], "type": e["type"]
            }).encode()
            req = urllib.request.Request(
                f"{base_url}/api/graph/edge",
                data=delete_payload, headers={"Content-Type": "application/json"},
                method="DELETE")
            try:
                urllib.request.urlopen(req)
            except Exception as exc:
                print(f"  !! delete failed: {exc}")
                continue
        applied += 1
    return applied


def _live_nodes(base_url):
    with urllib.request.urlopen(f"{base_url}/api/graph/nodes") as resp:
        return json.loads(resp.read().decode())


def _live_edges(base_url):
    with urllib.request.urlopen(f"{base_url}/api/graph/edges") as resp:
        return json.loads(resp.read().decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="JSON world file to analyze (autosave/scenario)")
    parser.add_argument("--live", action="store_true", help="analyze/apply against running server")
    parser.add_argument("--apply", action="store_true", help="apply changes (default: dry run)")
    parser.add_argument("--base-url", default="http://127.0.0.1:4444")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
        nodes_dict = data.get("graph", {}).get("nodes", {})
        edges = data.get("graph", {}).get("edges", [])
    elif args.live:
        nodes_dict = _live_nodes(args.base_url)
        edges = _live_edges(args.base_url)
    else:
        parser.error("Provide --file or --live")

    if not isinstance(nodes_dict, dict):
        nodes_dict = {n["id"]: n for n in nodes_dict}
    changes = plan_for_graph(nodes_dict, edges)

    if not changes:
        print("No issues found — all connection edges are healthy.")
        return

    drops = [c for c in changes if c["action"] == "DROP"]
    remaps = [c for c in changes if c["action"] == "REMAP"]
    print(f"PLAN: {len(drops)} drop(s), {len(remaps)} remap(s)\n")
    for ch in changes:
        e = ch["edge"]
        print(f"  [{ch['action']}] {e.get('source')} -> {e.get('target')} ({ch['way']})")
        print(f"        {ch['detail']}")

    if not args.apply:
        print("\nDry run — no changes written. Re-run with --apply (and --live for the server).")
        return

    if args.live:
        applied = apply_to_live(changes, args.base_url)
        print(f"\nApplied {applied} change(s) to live server at {args.base_url}.")
    else:
        applied = apply_to_file(nodes_dict, edges, changes)
        with open(args.file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nApplied {applied} change(s) to {args.file}.")
        print("NOTE: the running server won't pick this up until it reloads "
              "(restart or .py edit).")


if __name__ == "__main__":
    sys.exit(main())
