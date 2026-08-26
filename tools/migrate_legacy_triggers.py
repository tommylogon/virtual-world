"""Migrate legacy trigger fields to the modern ``effects[]`` format.

Legacy triggers store flat ``effect_type`` + ``effect_params`` on trigger
edges (and duplicated ``logic_trigger`` nodes). The engine now accepts both
at runtime, but this script rewrites JSON world files to the canonical shape:

    "effects": [{"type": "message", "params": {"success_message": "...", ...}}]

By default it only prints a plan (dry run). Pass ``--apply`` to write files.

Examples::

    python tools/migrate_legacy_triggers.py --all-mansion
    python tools/migrate_legacy_triggers.py --file data/scenarios/mansion.json --apply
    python tools/migrate_legacy_triggers.py --file data/autosave.json --apply --keep-legacy
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.trigger_system import _legacy_effects_from_properties  # noqa: E402

DEFAULT_MANSION_FILES = (
    ROOT / "data" / "scenarios" / "mansion.json",
    ROOT / "data" / "scenarios" / "mansion2.json",
    ROOT / "data" / "library" / "rooms" / "mansion.json",
)


def _typed_effects(props: dict) -> List[dict]:
    effects = props.get("effects")
    if not isinstance(effects, list):
        return []
    return [effect for effect in effects if isinstance(effect, dict) and effect.get("type")]


def _normalize_trigger_type(trigger_type: Any) -> Any:
    if trigger_type is None or trigger_type == "":
        return trigger_type
    if isinstance(trigger_type, list):
        return trigger_type
    return [str(trigger_type)]


def _canonicalize_effects(effects: List[dict]) -> List[dict]:
    """Normalize stored effects to the editor-friendly shape."""
    canonical: List[dict] = []
    for effect in effects:
        effect_type = effect.get("type", "message")
        params = dict(effect.get("params") or {})
        if effect_type == "message":
            message = params.pop("message", None) or params.get("success_message") or ""
            params["success_message"] = message
            params.setdefault("fail_message", "")
        canonical.append({"type": effect_type, "params": params})
    return canonical


def _build_effects(props: dict) -> Optional[List[dict]]:
    existing = _typed_effects(props)
    if existing:
        return _canonicalize_effects(existing)
    legacy = _legacy_effects_from_properties(props)
    if legacy:
        return _canonicalize_effects(legacy)
    return None


def _needs_migration(props: Optional[dict]) -> bool:
    if not isinstance(props, dict):
        return False
    has_legacy = bool(props.get("effect_type")) or bool(props.get("effect_params"))
    existing = _typed_effects(props)
    if existing and not has_legacy:
        return False
    if existing and has_legacy:
        return True
    return bool(_legacy_effects_from_properties(props))


def _migrate_properties(props: dict, strip_legacy: bool) -> Tuple[dict, str]:
    """Return updated props and a short change label."""
    if not _needs_migration(props):
        return props, ""

    before_legacy = bool(props.get("effect_type"))
    before_effects = bool(_typed_effects(props))
    effects = _build_effects(props)
    if not effects:
        return props, ""

    updated = dict(props)
    updated["effects"] = effects
    updated["trigger_type"] = _normalize_trigger_type(updated.get("trigger_type"))

    if strip_legacy:
        updated.pop("effect_type", None)
        updated.pop("effect_params", None)

    if before_effects and before_legacy:
        label = "strip-legacy"
    else:
        label = f"convert-{effects[0]['type']}"
        if len(effects) > 1:
            label += f"+{len(effects) - 1}"
    return updated, label


def plan_file(data: dict) -> List[dict]:
    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or {}
    edges = graph.get("edges") or []
    changes: List[dict] = []
    seen_nodes: set[str] = set()

    for edge in edges:
        if edge.get("type") != "triggers":
            continue
        props = edge.get("properties") or {}
        if not _needs_migration(props):
            continue
        _, label = _migrate_properties(props, strip_legacy=True)
        changes.append(
            {
                "kind": "edge",
                "id": f"{edge.get('source')} -> {edge.get('target')}",
                "target_node": edge.get("target"),
                "label": label,
                "trigger_type": props.get("trigger_type"),
                "effect_type": props.get("effect_type"),
            }
        )
        target = edge.get("target")
        if target:
            seen_nodes.add(target)

    if isinstance(nodes, dict):
        node_items = nodes.items()
    else:
        node_items = ((node.get("id"), node) for node in nodes)

    for node_id, node in node_items:
        if not node or node.get("type") != "logic_trigger":
            continue
        props = node.get("properties") or {}
        if not _needs_migration(props):
            continue
        _, label = _migrate_properties(props, strip_legacy=True)
        changes.append(
            {
                "kind": "node",
                "id": node_id,
                "target_node": node_id,
                "label": label,
                "trigger_type": props.get("trigger_type"),
                "effect_type": props.get("effect_type"),
            }
        )

    return changes


def apply_file(data: dict, strip_legacy: bool) -> int:
    graph = data.setdefault("graph", {})
    nodes = graph.get("nodes") or {}
    edges = graph.get("edges") or []
    applied = 0

    for edge in edges:
        if edge.get("type") != "triggers":
            continue
        props = edge.get("properties")
        if not isinstance(props, dict) or not _needs_migration(props):
            continue
        edge["properties"], _ = _migrate_properties(props, strip_legacy=strip_legacy)
        applied += 1

    if isinstance(nodes, dict):
        for node in nodes.values():
            if not node or node.get("type") != "logic_trigger":
                continue
            props = node.get("properties")
            if not isinstance(props, dict) or not _needs_migration(props):
                continue
            node["properties"], _ = _migrate_properties(props, strip_legacy=strip_legacy)
            applied += 1
    else:
        for node in nodes:
            if not node or node.get("type") != "logic_trigger":
                continue
            props = node.get("properties")
            if not isinstance(props, dict) or not _needs_migration(props):
                continue
            node["properties"], _ = _migrate_properties(props, strip_legacy=strip_legacy)
            applied += 1

    return applied


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", help="Scenario/world JSON file to migrate")
    parser.add_argument(
        "--all-mansion",
        action="store_true",
        help="Migrate mansion.json, mansion2.json, and library/rooms/mansion.json",
    )
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    parser.add_argument(
        "--keep-legacy",
        action="store_true",
        help="Keep effect_type/effect_params after writing effects[]",
    )
    args = parser.parse_args()

    files: List[Path] = []
    if args.all_mansion:
        files.extend(DEFAULT_MANSION_FILES)
    if args.file:
        files.extend(Path(value) for value in args.file)
    if not files:
        parser.error("Provide --file and/or --all-mansion")

    strip_legacy = not args.keep_legacy
    total_changes = 0
    total_applied = 0

    for path in files:
        if not path.exists():
            print(f"SKIP missing file: {path}")
            continue

        data = _load_json(path)
        changes = plan_file(data)
        if not changes:
            print(f"\n{path}: no legacy triggers found.")
            continue

        print(f"\n{path}: {len(changes)} trigger object(s) to update")
        for change in changes[:20]:
            trigger_type = change.get("trigger_type")
            effect_type = change.get("effect_type")
            print(
                f"  [{change['label']}] {change['kind']} {change['id']} "
                f"(trigger_type={trigger_type!r}, legacy_effect={effect_type!r})"
            )
        if len(changes) > 20:
            print(f"  ... and {len(changes) - 20} more")
        total_changes += len(changes)

        if args.apply:
            applied = apply_file(data, strip_legacy=strip_legacy)
            _save_json(path, data)
            print(f"  Applied {applied} update(s).")
            total_applied += applied

    if not args.apply and total_changes:
        print(
            f"\nDry run — {total_changes} trigger object(s) would be updated. "
            "Re-run with --apply to write."
        )
    elif args.apply and total_applied:
        print(f"\nDone — wrote {total_applied} trigger update(s) across {len(files)} file(s).")
        print("Restart the server or reload the scenario to pick up file changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
