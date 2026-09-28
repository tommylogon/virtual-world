#!/usr/bin/env python3
"""migrate_scope_id.py — one-off rename of a world scope's id (task-565).

A scope's id is minted once, as a slug of its name at creation, and the rename
route only ever touches the **display name**. The project's rule is the opposite:
ids change and display names do not, so a scope renamed "goblin camp" kept the id
``deep_woods_2`` forever. Scope ids are immutable by design — an id is a reference
in a dozen places and a silent half-rename is worse than a stale one — so this is
a one-off migration rather than a route.

Renamed everywhere the id can hide:

* the ``world_scopes`` key;
* every scope's ``children`` list and ``parent_id``;
* ``world_scope_id`` on every graph node;
* ``placements`` keys, and any placement record naming the scope;
* ``area_ids`` that referenced the old scope key.

Anything that still mentions the old id after the rename is **reported**, not
silently left: an unrecognised reference that happens to be a substring of
something else is the failure mode this script exists to avoid.

Idempotent, and **dry-run by default**.

Usage:
    python tools/migrate_scope_id.py
    python tools/migrate_scope_id.py --write
    python tools/migrate_scope_id.py --from deep_woods_2 --to goblin_camp --write
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scenario_refs import load_json, save_json  # noqa: E402

DEFAULT_TARGET = "data/scenarios/kraktooth_goblin_camp.json"

#: The pair task-565 asks for, and the argparse defaults. Both live here so the
#: module, the CLI and the tests cannot drift apart. The OUTER `deep_woods` scope
#: is deliberately absent: it is a genuinely painted 45x30 forest zone whose id and
#: name both agree, and renaming it would churn a scope nobody asked about.
DEFAULT_FROM = "deep_woods_2"
DEFAULT_TO = "goblin_camp"


def migrate(data: dict, old: str, new: str) -> dict:
    """Rename scope *old* to *new* throughout *data*. Returns a report."""
    scopes = data.get("world_scopes")
    if not isinstance(scopes, dict):
        return {"error": "no world_scopes on this scenario", "changes": [],
                "leftovers": []}
    if old not in scopes:
        # Already migrated is a *success*, not a failure. Saying so matters: a
        # re-run of a migration is the normal way to confirm it took, and an
        # error there would teach people to ignore the output.
        if new in scopes:
            return {"error": None, "changes": [], "leftovers": [],
                    "already": f"{new!r} is already the scope (no {old!r})"}
        return {"error": f"no scope {old!r} to rename (have: "
                          f"{', '.join(sorted(scopes))})",
                "changes": [], "leftovers": []}
    if new in scopes:
        return {"error": f"{new!r} already exists; refusing to merge two scopes",
                "changes": [], "leftovers": []}

    changes = []

    # 1. The scope record itself, under its new key.
    record = scopes.pop(old)
    record["id"] = new
    scopes[new] = record
    changes.append(("world_scopes", old, new))

    # 2. Every reference from another scope: children lists and parent ids.
    for scope_id, scope in scopes.items():
        children = scope.get("children")
        if isinstance(children, list) and old in children:
            scope["children"] = [new if c == old else c for c in children]
            changes.append((f"{scope_id}.children", old, new))
        if scope.get("parent_id") == old:
            scope["parent_id"] = new
            changes.append((f"{scope_id}.parent_id", old, new))
        placements = scope.get("placements")
        if isinstance(placements, dict) and old in placements:
            scope["placements"] = {new if k == old else k: v
                                   for k, v in placements.items()}
            changes.append((f"{scope_id}.placements", old, new))

    # 3. The nodes themselves. `world_scope_id` is the one the compiler writes and
    #    the one `scope_areas()` in the tests reads back.
    nodes = (data.get("graph") or {}).get("nodes") or {}
    rekeyed = {}
    renamed_nodes = {}
    for node_id, node in nodes.items():
        props = node.get("properties")
        if not isinstance(props, dict):
            rekeyed[node_id] = node
            continue
        for key in ("world_scope_id", "scope_id", "parent_scope_id"):
            if props.get(key) == old:
                props[key] = new
                changes.append((f"{node_id}.{key}", old, new))
        # A node's own id may be minted from the scope id, as a compiled grid's
        # cell areas are (`area_<scope>_<x>_<y>`). Both the record's `id` AND the
        # dict key it sits under have to follow: rekeying only one of the two is
        # the half-rename this script exists to prevent, and the graph looks
        # perfectly healthy while every reference to that node dangles.
        key = node_id
        if node_id.startswith(f"area_{old}_"):
            key = node_id.replace(f"area_{old}_", f"area_{new}_", 1)
            node["id"] = key
            renamed_nodes[node_id] = key
            changes.append(("node id", node_id, key))
        rekeyed[key] = node
    if len(rekeyed) != len(nodes):
        # Two nodes collided on the new key; that is data loss, not a rename.
        return {"error": f"renaming {old!r} collides node ids ({len(nodes)} -> "
                          f"{len(rekeyed)}); resolve the duplicate first",
                "changes": [], "leftovers": []}
    if data.get("graph"):
        data["graph"]["nodes"] = rekeyed

    # 3b. `area_ids` on every scope are node ids, so they follow the rekey. A
    #     scope whose list still names a node that is no longer there looks fine
    #     and fails at load, which is the worst place to find out.
    if renamed_nodes:
        for scope_id, scope in scopes.items():
            area_ids = scope.get("area_ids")
            if not isinstance(area_ids, list):
                continue
            moved = [a for a in area_ids if a in renamed_nodes]
            if not moved:
                continue
            scope["area_ids"] = [renamed_nodes.get(a, a) for a in area_ids]
            changes.append((f"{scope_id}.area_ids", moved[0], renamed_nodes[moved[0]]))

    # 4. Anything left that still says the old id, so an unrecognised reference
    #    is a report rather than a silent breakage.
    leftovers = _find_leftovers(data, old)

    return {"error": None, "changes": changes, "leftovers": leftovers,
            "old": old, "new": new}


def _find_leftovers(data: dict, old: str) -> list:
    """Paths that still contain the old id, so nothing is missed silently.

    Deliberately a *substring* search rather than an equality search: the point
    is to notice a reference in a shape this script did not anticipate, and a
    reference in an unknown shape is exactly what a substring catches.
    """
    found = []

    def walk(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if old in str(key):
                    found.append(f"{path}.<key {key}>")
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str) and old in value:
            found.append(f"{path} = {value!r}")

    walk(data, "$")
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="Scenario files (default: the camp)")
    parser.add_argument("--from", dest="old", default=DEFAULT_FROM,
                        help="Scope id to migrate (default: deep_woods_2)")
    parser.add_argument("--to", dest="new", default=DEFAULT_TO,
                        help="Scope id to migrate to (default: goblin_camp)")
    parser.add_argument("--write", action="store_true", help="Apply to disk")
    args = parser.parse_args()

    paths = ([ROOT / p if not Path(p).is_absolute() else Path(p) for p in args.paths]
             or [ROOT / DEFAULT_TARGET])
    failed = False
    for path in paths:
        if not path.exists():
            print(f"skip {path}: not found", file=sys.stderr)
            continue
        data = load_json(path)
        report = migrate(data, args.old, args.new)
        if report.get("already"):
            print(f"  already migrated: {path.relative_to(ROOT)}")
            continue
        if report["error"]:
            print(f"  {report['error']}", file=sys.stderr)
            failed = True
            continue
        for where, before, after in report["changes"]:
            print(f"  {where}: {before} -> {after}")
        if report["leftovers"]:
            print(f"  WARNING: {len(report['leftovers'])} place(s) still say "
                  f"{args.old!r}:", file=sys.stderr)
            for item in report["leftovers"][:10]:
                print(f"    {item}", file=sys.stderr)
        if report["changes"] and args.write and not report["leftovers"]:
            save_json(path, data)
        label = ("migrated" if (report["changes"] and args.write
                               and not report["leftovers"])
                 else "would migrate" if report["changes"] else "ok")
        print(f"  {label}: {path.relative_to(ROOT)} "
              f"({len(report['changes'])} references, "
              f"{len(report['leftovers'])} leftover)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
