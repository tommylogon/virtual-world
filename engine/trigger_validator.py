"""Trigger validation — find broken trigger references in the world graph.

Scans every ``triggers`` edge plus the ``logic_trigger`` nodes they point
at and reports issues that would silently break at runtime:

* dangling trigger edges (target node deleted),
* stale trigger copies (a trigger created for a renamed/duplicated item),
* effect params that reference graph nodes / library items that don't exist
  (``spawn_item``, ``unlock_way``, ``set_state``, ``teleport``, ...),
* condition params that reference items or tags no node in the world has
  (``has_item``, ``has_tag``, ``state_equals``, ...),
* unknown condition / effect / trigger types.

Each issue is a dict with a ``source_node_id`` so the frontend can render a
clickable "open node" button that jumps the inspector + graph to the owner
of the broken trigger.
"""

import json
import os
from typing import Any, Dict, Iterator, List, Optional

from graph import Node, EDGE_CONNECTION, EDGE_TRIGGERS
from .trigger_system import TRIGGER_TYPES, EFFECT_TYPES

# Condition types the engine actually evaluates (union of the flat
# ``_evaluate_trigger_condition`` and tree ``_evaluate_conditions`` paths).
CONDITION_TYPES = {
    "uses_reached",
    "uses_above",
    "has_item",
    "has_items",
    "state_equals",
    "random_chance",
    "skill_check",
    "save_throw",
    "temperature_below",
    "temperature_above",
    "area_temp",
    "vital",
    "vital_above",
    "vital_below",
    "is_equipped",
    "time_of_day",
    "weather",
    "has_trait",
    "has_tag",
    "target_has_tag",
    "eq",
    "in_area",
    "tick_since_state",
    "proximity",
    "sound_heard",
    "speech_matches",
}

# Effect params that hard-reference a graph node by id. ``self`` means the
# triggering node and is a valid no-op target.
NODE_ID_EFFECTS = {
    "set_state": "node_id",
    "set_hidden": "node_id",
    "rename": "node_id",
    "adjust_uses": "node_id",
    "add_tag": "node_id",
    "remove_tag": "node_id",
    "set_parameter": "node_id",
    "adjust_parameter": "node_id",
}

# Effects that reference a node by a differently-named param.
NODE_REF_EFFECTS = {
    "set_environment": "node_id",      # area node (falls back to current area)
    "unlock_way": "way_id",            # "target"/"" = the used-on door
    "set_description": "target",       # node id
    "append_description": "target",    # node id
}

# Effects that reference an item (graph node OR library file).
ITEM_EFFECTS = {
    "spawn_item": "item_id",
    "give_item": "item_id",
    "remove_item": "item_id",
}

# Effects that reference a character (graph node OR library file).
CHARACTER_EFFECTS = {
    "spawn_character": "character_id",
}

# Effects/conditions that reference an item by name/id (substring match).
ITEM_NAME_KEYS = {
    "has_item": ("value",),
    "is_equipped": ("item",),
    "consume_item": ("item",),
}

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

# Mechanical tags the engine reads and the properties they require to work.
# Backend truth — see engine/lighting.py (light_source→light_level),
# environment_propagation.py (heat_source→target_temperature/heating_rate),
# sound.py (sound_source→sound_level/sound_pattern), toggleable_items.py
# (toggleable→current_state, electric), equipment_bonuses.py (weapon→damage,
# clothing/armor→equip_slots, insulation→insulation value),
# item_actions.py (container→max_weight_capacity), player.py (magic→Mana).
MECHANICAL_REQUIREMENTS = {
    "light_source": ("light_level",),
    "heat_source": ("target_temperature", "heating_rate"),
    "sound_source": ("sound_level", "sound_pattern"),
    "toggleable": ("current_state",),
    "insulation": ("insulation",),
    "weapon": ("damage",),
    "clothing": ("equip_slots",),
    "armor": ("equip_slots",),
    "container": ("max_weight_capacity",),
    "electric": (),
    "exterior": (),
    "magic": (),
    "transit": (),
}

# Mechanical props the engine silently defaults when missing — see
# lighting.py (light_level→"dim") and environment_propagation.py
# (target_temperature→30, heating_rate→0.5). Missing these is an authoring
# nudge (info), not a broken tag: the engine still applies the effect at the
# default value. Props NOT listed here have no engine fallback → warning.
DEFAULTED_MECHANICAL_DEFAULTS = {
    "light_level": "the 'dim' default",
    "target_temperature": "a 30°C default",
    "heating_rate": "a 0.5°C/tick default",
}

# Node properties every way should carry for the map/narration to work
# (cardinal + view direction live on the connection edges, not the node).
WAY_NODE_FIELDS = ("description", "pass_message")

# Item properties that should stay in sync with the library entry after
# placement (bug_14 — refresh-to-world resyncs these).
LIBRARY_SYNC_PROPS = (
    "name", "description", "tags", "actions", "uses", "weight",
    "equip_slots", "current_state", "light_level", "target_temperature",
    "heating_rate", "contents", "aliases",
)


class TriggerValidator:
    """Static validation of all trigger wiring in a ``WorldGraph``."""

    def __init__(self, graph, library_dir: str = None):
        self.graph = graph
        self.library_dir = library_dir or os.path.join("data", "library")

    # ─────────────────── Public API ───────────────────

    def validate(self, node_id: Optional[str] = None) -> List[dict]:
        """Return every issue in the graph, optionally filtered to *node_id*.

        Covers trigger wiring plus authoring problems: empty triggers/effects,
        ways missing cardinal/view/description/pass_message, mechanical tags
        missing the values the engine reads, and instances drifted from their
        library entry.
        """
        issues: List[dict] = []
        trigger_edges = self.graph.get_edges_by_type(EDGE_TRIGGERS)
        for edge in trigger_edges:
            if node_id and edge.source.lower() != node_id.lower():
                continue
            issues.extend(self._validate_trigger_edge(edge))
        issues.extend(self._validate_way_authoring(node_id))
        issues.extend(self._validate_mechanical_items(node_id))
        issues.extend(self._validate_library_sync(node_id))
        issues.sort(key=lambda i: SEVERITY_ORDER.get(i.get("severity"), 9))
        return issues

    def validate_trigger_props(
        self,
        trigger_props: dict,
        source_node_id: str = "",
        trigger_node_id: str = "",
    ) -> List[dict]:
        """Validate a trigger definition dict directly (used by the editor's
        Run button / trigger tests)."""
        source_id = source_node_id or trigger_props.get("source_node_id", "") or ""
        issues: List[dict] = []
        self._check_trigger_type(trigger_props, source_id, trigger_node_id, issues)
        self._check_conditions(trigger_props, source_id, trigger_node_id, issues)
        self._check_effects(trigger_props, source_id, trigger_node_id, issues)
        if not any(True for _ in self._iter_effects(trigger_props)):
            issues.append(self._issue(
                "warning", "empty_trigger",
                "Trigger has no effects — it will do nothing.",
                source_node_id=source_id,
                trigger_node_id=trigger_node_id,
            ))
        return issues

    # ─────────────────── Per-edge validation ───────────────────

    def _validate_trigger_edge(self, edge) -> List[dict]:
        issues: List[dict] = []
        source_node = self.graph.get_node(edge.source)
        if source_node is None:
            issues.append(self._issue(
                "info", "orphan_trigger_edge",
                f"Trigger edge points from missing node '{edge.source}'.",
                source_node_id=edge.source,
                trigger_node_id=edge.target,
            ))
            return issues

        source_id = source_node.id
        trigger_node = self.graph.get_node(edge.target)
        if trigger_node is None:
            issues.append(self._issue(
                "error", "dangling_trigger_edge",
                f"Trigger on {self._label(source_node)} points to a missing "
                f"trigger node '{edge.target}' (deleted or never created).",
                source_node_id=source_id,
                trigger_node_id=edge.target,
                target_node_id=edge.target,
            ))
            return issues

        if trigger_node.type != "logic_trigger":
            issues.append(self._issue(
                "error", "trigger_edge_wrong_target_type",
                f"Trigger on {self._label(source_node)} points to "
                f"'{edge.target}' which is a {trigger_node.type}, not a "
                f"logic_trigger.",
                source_node_id=source_id,
                trigger_node_id=edge.target,
                target_node_id=edge.target,
            ))
            return issues

        # Stale copy detection: conventional trigger ids embed the parent
        # node ("trigger_item_button_18_on_use_..."). A trigger id that embeds
        # a different node prefix (item_/way_/area_/player_) but NOT the source
        # is a leftover from a renamed/duplicated node.
        self._check_stale_trigger(source_node, trigger_node, issues)

        props = trigger_node.properties or {}
        # Runtime prefers edge properties, then the node copy — validate the
        # union so a stale edge copy is caught even when the node is current.
        edge_props = edge.properties or {}
        merged = {**props, **edge_props}
        merged.setdefault("source_node_id", source_id)
        issues.extend(self.validate_trigger_props(
            merged,
            source_node_id=source_id,
            trigger_node_id=trigger_node.id,
        ))
        return issues

    def _check_stale_trigger(self, source_node: Node, trigger_node: Node, issues: List[dict]) -> None:
        trigger_id = str(trigger_node.id).lower()
        source_id = source_node.id.lower()
        if not trigger_id.startswith("trigger_"):
            return
        
        if self._is_shared_trigger(trigger_node):
            return
        
        embeds_node_prefix = any(
            token in trigger_id for token in ("item_", "way_", "area_", "player_")
        )
        if embeds_node_prefix and source_id not in trigger_id:
            embedded = trigger_id[len("trigger_"):]
            issues.append(self._issue(
                "warning", "stale_trigger_copy",
                f"Trigger '{trigger_node.id}' looks like a stale copy from a "
                f"renamed/duplicated node (id embeds '{embedded}' or similar) "
                f"but is attached to {self._label(source_node)} — it may fire "
                f"on the wrong object.",
                source_node_id=source_node.id,
                trigger_node_id=trigger_node.id,
            ))
    
    def _is_shared_trigger(self, trigger_node: Node) -> bool:
        incoming = [
            e for e in self.graph.edges
            if e.target == trigger_node.id and e.type == "triggers"
        ]
        distinct_sources = {e.source for e in incoming}
        return len(distinct_sources) > 1

    # ─────────────────── Trigger type ───────────────────

    def _check_trigger_type(self, props: dict, source_id: str, trigger_id: str, issues: List[dict]) -> None:
        raw = props.get("trigger_type") or props.get("trigger_types")
        if raw is None:
            return
        types = raw if isinstance(raw, (list, tuple)) else [raw]
        for t in types:
            t = str(t).strip()
            if not t:
                continue
            if t not in TRIGGER_TYPES:
                issues.append(self._issue(
                    "warning", "unknown_trigger_type",
                    f"Trigger type '{t}' is not a known engine trigger type "
                    f"({', '.join(TRIGGER_TYPES)}). It will never fire.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                ))

    # ─────────────────── Conditions ───────────────────

    def _iter_condition_leaves(self, conditions: Any) -> Iterator[dict]:
        if not conditions:
            return
        if isinstance(conditions, list):
            for c in conditions:
                yield from self._iter_condition_leaves(c)
            return
        if not isinstance(conditions, dict):
            return
        if conditions.get("operator"):
            for c in conditions.get("conditions", []) or []:
                yield from self._iter_condition_leaves(c)
            return
        yield conditions

    def _check_conditions(self, props: dict, source_id: str, trigger_id: str, issues: List[dict]) -> None:
        raw = props.get("conditions")
        if raw is None:
            raw = props.get("condition")
        for cond in self._iter_condition_leaves(raw):
            self._check_condition(cond, source_id, trigger_id, issues)

    def _check_condition(self, cond: dict, source_id: str, trigger_id: str, issues: List[dict]) -> None:
        if not isinstance(cond, dict):
            return
        ctype = cond.get("type", "")
        if ctype not in CONDITION_TYPES:
            issues.append(self._issue(
                "warning", "unknown_condition_type",
                f"Condition type '{ctype}' is not recognized by the engine "
                f"and will always evaluate false.",
                source_node_id=source_id,
                trigger_node_id=trigger_id,
            ))
            return

        if ctype in ("has_tag", "target_has_tag"):
            values = cond.get("value") or []
            if isinstance(values, str):
                values = [values]
            for tag in values:
                tag = str(tag).strip()
                if not tag:
                    continue
                if not self._tag_exists(tag):
                    issues.append(self._issue(
                        "warning", "tag_not_in_world",
                        f"No node in the world has the tag '{tag}' — this "
                        f"has_tag condition can never fire.",
                        source_node_id=source_id,
                        trigger_node_id=trigger_id,
                    ))

        elif ctype in ("has_item", "is_equipped"):
            needle = cond.get("value") if ctype == "has_item" else cond.get("item", "")
            if needle and not self._item_exists(needle) and not self._library_item_exists(needle):
                issues.append(self._issue(
                    "warning", "condition_missing_item",
                    f"Condition '{ctype}' references item '{needle}' but no "
                    f"item node in the world (or the item library) matches it.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                ))

        elif ctype == "has_items":
            for needle in cond.get("value", []) or []:
                if needle and not self._item_exists(needle) and not self._library_item_exists(needle):
                    issues.append(self._issue(
                        "warning", "condition_missing_item",
                        f"Condition 'has_items' references item '{needle}' but "
                        f"no item node in the world (or the item library) "
                        f"matches it.",
                        source_node_id=source_id,
                        trigger_node_id=trigger_id,
                    ))

        elif ctype == "state_equals":
            target_name = cond.get("target", "")
            node_ref = None
            if target_name:
                node_ref = target_name
            elif "=" in str(cond.get("value", "")):
                node_ref = str(cond.get("value", "")).split("=", 1)[0].strip()
            if node_ref and not self._node_name_matches(node_ref):
                issues.append(self._issue(
                    "warning", "condition_missing_node",
                    f"Condition 'state_equals' references node '{node_ref}' "
                    f"but no node in the world matches that name or id.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                ))

    # ─────────────────── Effects ───────────────────

    def _iter_effects(self, props: dict) -> Iterator[tuple]:
        """Yield (effect_type, params) from modern or legacy effect shapes."""
        effects = props.get("effects")
        if isinstance(effects, list):
            for eff in effects:
                if not isinstance(eff, dict):
                    continue
                etype = eff.get("type", "")
                params = eff.get("params") or {}
                if not isinstance(params, dict):
                    params = {}
                yield etype, params
        elif props.get("effect_type"):
            params = props.get("effect_params") or {}
            if not isinstance(params, dict):
                params = {}
            yield props.get("effect_type", ""), params

    def _check_effects(self, props: dict, source_id: str, trigger_id: str, issues: List[dict]) -> None:
        for etype, params in self._iter_effects(props):
            self._check_effect(etype, params, source_id, trigger_id, issues)

    def _check_effect(self, etype: str, params: dict, source_id: str, trigger_id: str, issues: List[dict]) -> None:
        if etype not in EFFECT_TYPES:
            issues.append(self._issue(
                "warning", "unknown_effect_type",
                f"Effect type '{etype}' is not a known engine effect type — "
                f"it will do nothing.",
                source_node_id=source_id,
                trigger_node_id=trigger_id,
            ))
            return

        if etype == "message":
            msg = str(params.get("message") or params.get("success_message")
                      or params.get("fail_message") or "").strip()
            if not msg:
                issues.append(self._issue(
                    "warning", "empty_effect_message",
                    f"Trigger {trigger_id} on {source_id} has a message effect "
                    f"with no text (message/success_message/fail_message all "
                    f"empty) — nothing will be narrated.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                ))
            return

        if etype in NODE_ID_EFFECTS:
            node_id = params.get(NODE_ID_EFFECTS[etype], "")
            if node_id and node_id != "self" and not self.graph.get_node(node_id):
                issues.append(self._issue(
                    "error", "missing_effect_node",
                    f"Effect '{etype}' points to missing node '{node_id}' — "
                    f"it will silently do nothing.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                    target_node_id=node_id,
                ))

        elif etype in NODE_REF_EFFECTS:
            key = NODE_REF_EFFECTS[etype]
            node_id = params.get(key, "")
            if etype == "unlock_way" and node_id in ("", "target"):
                node_id = ""
            if node_id and node_id != "self" and not self.graph.get_node(node_id):
                issues.append(self._issue(
                    "error", "missing_effect_node",
                    f"Effect '{etype}' points to missing node '{node_id}' — "
                    f"it will silently do nothing.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                    target_node_id=node_id,
                ))

        elif etype == "teleport":
            area_name = str(params.get("area", "")).strip()
            if area_name and not self._area_matches(area_name):
                issues.append(self._issue(
                    "warning", "teleport_missing_area",
                    f"Teleports to area '{area_name}' but no area with that "
                    f"name exists — the player won't move.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                ))

        elif etype in ITEM_EFFECTS:
            item_id = str(params.get(ITEM_EFFECTS[etype], "")).strip()
            if not item_id:
                return
            missing = not self._item_exists(item_id) and not self._library_item_exists(item_id)
            if not missing:
                return
            severity = "warning" if etype == "remove_item" else "error"
            verb = {
                "spawn_item": "Spawns",
                "give_item": "Gives",
                "remove_item": "Removes",
            }[etype]
            issues.append(self._issue(
                severity, "missing_effect_item",
                f"{verb} item '{item_id}' which is neither in the world graph "
                f"nor the item library — "
                f"{'nothing will be removed' if etype == 'remove_item' else 'the effect will no-op'}.",
                source_node_id=source_id,
                trigger_node_id=trigger_id,
                target_node_id=item_id,
            ))

        elif etype in CHARACTER_EFFECTS:
            char_id = str(params.get(CHARACTER_EFFECTS[etype], "")).strip()
            if not char_id:
                return
            missing = not self._character_exists(char_id) and not self._library_character_exists(char_id)
            if not missing:
                return
            issues.append(self._issue(
                "error", "missing_effect_character",
                f"Spawns character '{char_id}' which is neither in the world graph "
                f"nor the character library — the effect will no-op.",
                source_node_id=source_id,
                trigger_node_id=trigger_id,
                target_node_id=char_id,
            ))

        elif etype == "consume_item":
            needle = str(params.get("item", "")).strip()
            if needle and not self._item_exists(needle) and not self._library_item_exists(needle):
                issues.append(self._issue(
                    "warning", "missing_effect_item",
                    f"Consumes item '{needle}' but no item node in the world "
                    f"matches it.",
                    source_node_id=source_id,
                    trigger_node_id=trigger_id,
                    target_node_id=needle,
                ))

        elif etype == "save":
            for branch in ("on_fail", "on_success"):
                for sub in params.get(branch) or []:
                    if not isinstance(sub, dict):
                        continue
                    sub_type = sub.get("type", "")
                    sub_params = sub.get("params") or {}
                    if not isinstance(sub_params, dict):
                        sub_params = {}
                    self._check_effect(sub_type, sub_params, source_id, trigger_id, issues)

    # ─────────────────── Authoring / data checks ───────────────────

    def _validate_way_authoring(self, node_id: Optional[str] = None) -> List[dict]:
        """Warn on ways missing description / pass message / cardinal / view
        direction — the fields the map editor and narration rely on.

        Cardinal + view direction live on the area→way connection edges; the
        reverse way→area "enter" edges only carry the direction command, so
        only ``edge.target == node.id`` edges are validated."""
        issues: List[dict] = []
        for node in self.graph.nodes.values():
            if node.type != "way":
                continue
            if node_id and node.id.lower() != node_id.lower():
                continue
            props = node.properties or {}
            label = self._label(node)
            for field in WAY_NODE_FIELDS:
                if not str(props.get(field) or "").strip():
                    issues.append(self._issue(
                        "warning", f"way_missing_{field}",
                        f"Way {label} has no {field.replace('_', ' ')}.",
                        source_node_id=node.id,
                    ))
            for edge in self.graph.edges:
                if edge.type != EDGE_CONNECTION or edge.target != node.id:
                    continue
                eprops = edge.properties or {}
                if not str(eprops.get("cardinal") or "").strip():
                    issues.append(self._issue(
                        "warning", "way_missing_cardinal",
                        f"Way {label} side '{edge.source}->{node.id}' has no "
                        f"cardinal direction — the map can't orient it.",
                        source_node_id=node.id,
                    ))
                if not str(eprops.get("visible_in_direction") or "").strip():
                    issues.append(self._issue(
                        "warning", "way_missing_view_direction",
                        f"Way {label} side '{edge.source}->{node.id}' has no "
                        f"view direction (visible_in_direction).",
                        source_node_id=node.id,
                    ))
        return issues

    def _validate_mechanical_items(self, node_id: Optional[str] = None) -> List[dict]:
        """Warn on items carrying a mechanical tag but missing the values the
        engine reads for it (task-307)."""
        issues: List[dict] = []
        for node in self.graph.nodes.values():
            if node.type != "item":
                continue
            if node_id and node.id.lower() != node_id.lower():
                continue
            tags = [str(t).lower() for t in (node.properties.get("tags") or [])]
            props = node.properties or {}
            for mech_tag, required in MECHANICAL_REQUIREMENTS.items():
                if mech_tag not in tags:
                    continue
                missing = [p for p in required if not props.get(p)]
                if not missing:
                    continue
                strict = [p for p in missing if p not in DEFAULTED_MECHANICAL_DEFAULTS]
                defaulted = [p for p in missing if p in DEFAULTED_MECHANICAL_DEFAULTS]
                if strict:
                    issues.append(self._issue(
                        "warning", "mechanical_tag_missing_props",
                        f"Item {self._label(node)} has mechanical tag "
                        f"'{mech_tag}' but no {', '.join(strict)} — the "
                        f"engine can't apply its effect.",
                        source_node_id=node.id,
                    ))
                if defaulted:
                    defaults = " and ".join(
                        DEFAULTED_MECHANICAL_DEFAULTS[p] for p in defaulted)
                    issues.append(self._issue(
                        "info", "mechanical_tag_missing_props",
                        f"Item {self._label(node)} has mechanical tag "
                        f"'{mech_tag}' but no {', '.join(defaulted)} — "
                        f"the engine uses {defaults}; set it explicitly "
                        f"for clarity.",
                        source_node_id=node.id,
                    ))
        return issues

    def _validate_library_sync(self, node_id: Optional[str] = None) -> List[dict]:
        """Warn on instanced items drifted from their library template
        (bug_14 — refresh-to-world resyncs)."""
        issues: List[dict] = []
        for node in self.graph.nodes.values():
            if node.type != "item":
                continue
            if node_id and node.id.lower() != node_id.lower():
                continue
            lib_id = str(node.properties.get("library_id") or "").strip()
            if not lib_id:
                continue
            lib_path = os.path.join(self.library_dir, "items", f"{lib_id}.json")
            if not os.path.isfile(lib_path):
                issues.append(self._issue(
                    "warning", "library_entry_missing",
                    f"Item {self._label(node)} references library entry "
                    f"'{lib_id}' but no file exists at "
                    f"data/library/items/{lib_id}.json.",
                    source_node_id=node.id,
                ))
                continue
            try:
                with open(lib_path, "r", encoding="utf-8-sig") as f:
                    lib = json.load(f)
            except Exception:
                continue
            if not isinstance(lib, dict):
                continue
            differing = []
            for key in LIBRARY_SYNC_PROPS:
                inst = node.properties.get(key)
                if key == "name":
                    inst = node.name
                template = lib.get(key)
                if template is None:
                    continue
                if not self._props_match(inst, template):
                    differing.append(key)
            if differing:
                issues.append(self._issue(
                    "warning", "library_mismatch",
                    f"Item {self._label(node)} differs from its library "
                    f"entry '{lib_id}' ({', '.join(differing)}) — "
                    f"refresh-to-world to resync.",
                    source_node_id=node.id,
                ))
        return issues

    @staticmethod
    def _props_match(inst: Any, template: Any) -> bool:
        """Compare an instance prop to its library template, tolerating the
        hydration normalization (library ``actions`` string → node list)."""
        if isinstance(template, str) and isinstance(inst, list):
            template = [t.strip() for t in template.split(",") if t.strip()]
        if isinstance(inst, str) and isinstance(template, list):
            inst = [t.strip() for t in inst.split(",") if t.strip()]
        return inst == template

    # ─────────────────── Lookup helpers ───────────────────

    def _tag_exists(self, tag: str) -> bool:
        tag = str(tag).lower()
        for node in self.graph.nodes.values():
            tags = node.properties.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            for t in tags:
                if str(t).lower() == tag:
                    return True
        return False

    def _item_exists(self, needle: str) -> bool:
        needle = str(needle).lower()
        for node in self.graph.nodes.values():
            if node.type != "item":
                continue
            if needle in (node.name or "").lower() or needle in (node.id or "").lower():
                return True
        return False

    def _node_name_matches(self, needle: str) -> bool:
        needle = str(needle).lower()
        for node in self.graph.nodes.values():
            if needle in (node.name or "").lower() or needle in (node.id or "").lower():
                return True
        return False

    def _area_matches(self, name: str) -> bool:
        name = str(name).lower()
        for node in self.graph.nodes.values():
            if node.type != "area":
                continue
            if (node.name or "").lower() == name or node.id.lower() == name:
                return True
        return False

    def _library_item_exists(self, item_id: str) -> bool:
        """True when a library item file exists for *item_id* (spawn/give can
        hydrate from it at runtime)."""
        if not self.library_dir:
            return False
        path = os.path.join(self.library_dir, "items", f"{item_id}.json")
        return os.path.isfile(path)

    def _character_exists(self, needle: str) -> bool:
        needle = str(needle).lower()
        for node in self.graph.nodes.values():
            if node.type != "character":
                continue
            if needle in (node.name or "").lower() or needle in (node.id or "").lower():
                return True
        return False

    def _library_character_exists(self, char_id: str) -> bool:
        """True when a library character file exists for *char_id* (spawn_character
        can hydrate from it at runtime)."""
        if not self.library_dir:
            return False
        path = os.path.join(self.library_dir, "characters", f"{char_id}.json")
        return os.path.isfile(path)

    @staticmethod
    def _label(node: Node) -> str:
        return f"{node.name or node.id} ({node.id})"

    @staticmethod
    def _issue(severity: str, code: str, message: str, **kwargs) -> dict:
        issue = {
            "severity": severity,
            "code": code,
            "message": message,
        }
        issue.update({k: v for k, v in kwargs.items() if v is not None})
        return issue
