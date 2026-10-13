"""Pre-Apply validation for NL-editor staged ops (task-461).

A staged batch is replayed blind: a misspelled trait id, a wrong field shape or
a dangling edge endpoint currently applies as a silent no-op. This module checks
the ops against the live graph and the trait catalog first, so the editor can
show the problems and refuse to Apply until they are fixed.

Pure data: the caller supplies the node index (id -> {type, name}) and the
registered trait ids, so the same validator can back the batch route, the
pre-Apply endpoint, and tests.

Severity:
- ``error``   — the op cannot do what it says (missing node, unknown trait,
                malformed payload). A strict Apply is refused.
- ``warning`` — the op will apply but probably not as intended (id casing,
                duplicate area display name, unknown item action, deleted node
                still referenced).

@module nl_editor_validation
@contributes the pre-Apply validator for staged NL-editor ops
@docs docs/virtualWorld/UI & Settings/NL Editor.md
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from engine.traits import TRAIT_DEFINITIONS

ERROR = "error"
WARNING = "warning"

KNOWN_TYPES = {"area", "item", "way", "character", "logic_trigger"}
KNOWN_OP_TYPES = {
    "create_node", "create_character", "spawn_library_item", "connect_areas", "update_node",
    "update_matching_nodes", "link_to_library", "attach", "detach",
    "delete_node", "clear_way_fix_fields", "library_upsert", "library_delete",
    "update_player", "create_trigger", "rename_character",
}
#: Player-state patch keys the NL editor may write (task-738). These are NOT
#: graph edges — they live on the Player (memories list, relationships dict,
#: emotion pulses) — so they take a dedicated op, not `attach`.
PLAYER_PATCH_KEYS = {"memories", "relationship", "remove_relationship", "emotion", "behaviors"}
#: Registries the NL editor may write to (task-460).
WRITABLE_REGISTRIES = {"items", "characters", "areas", "ways", "traits"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")
#: Standard item actions (prompt rule 4) plus the auto-inverse verbs.
KNOWN_ITEM_ACTIONS = {
    "examine", "take", "use", "open", "close", "eat", "drink", "read",
    "light", "activate", "equip", "unequip", "throw", "break", "drop",
}
#: Triggers the NPC-behaviour runner (`npc_behaviors.process_simple_npcs`)
#: actually receives from its callers. Deliberately NOT ``TRIGGER_TYPES``: those
#: are node/item triggers, and a behaviour keyed on one of them (``on_take``,
#: ``on_night``, ``on_enter``) is fired by nobody and silently dead.
NPC_BEHAVIOUR_TRIGGERS = {
    "on_tick",
    "on_item_taken",
    "on_player_enter_area",
    "on_player_leave_area",
    "on_speech_heard",
}
#: Behaviour actions that are not effect types — the executor's own verbs
#: (`engine/triggers/behaviors.py`). An action type is valid if it is one of
#: these OR a member of ``EFFECT_TYPES`` (the executor falls back to the effect
#: registry, so the two vocabularies are one).
NPC_BEHAVIOUR_ACTIONS = {
    "go", "wait", "follow", "emote", "look", "examine", "speak", "set_npc_state",
    "set_emotion", "set_flag", "add_memory", "attack", "approach", "traverse",
    "hide_in", "hide_behind", "hide_under", "unhide", "rest", "sleep", "meditate",
    "bathe", "sit", "stand", "stop", "wake", "relieve", "listen", "carry",
    "inventory", "weigh", "hold", "stow", "place", "remove", "dress", "strip",
    "swap", "adorn", "drop_all", "take_all", "lie_down", "dash", "crawl", "climb",
    "jump", "toggle_way", "grab", "drag", "pin", "struggle", "escape", "release",
    "toggle", "teach", "cook", "push_through", "block", "introduce", "beg",
    "demand", "bribe", "trade", "manifest", "vanish", "possess", "wraith_form",
    "spawn_body_item", "carve", "gulp_down", "pinch", "help", "commands", "who",
    "time", "score", "map", "save", "quit", "version",
}
BULK_SELECTOR_KEYS = (
    "kind", "type", "tags", "tag", "area", "area_id", "name_contains",
    "query", "ids",
)


def _issue(index: int, optype: str, severity: str, message: str, field: Optional[str] = None) -> Dict[str, Any]:
    issue = {"index": index, "type": optype, "severity": severity, "message": message}
    if field:
        issue["field"] = field
    return issue


def _trait_issues(index: int, optype: str, patch: Any, trait_ids: Set[str]) -> List[Dict[str, Any]]:
    if not isinstance(patch, dict):
        return []
    traits = patch.get("traits")
    if traits is None:
        return []
    if not isinstance(traits, dict):
        return [_issue(index, optype, ERROR, "'traits' must be an object mapping trait ids to true/param.", "traits")]
    unknown = sorted(str(t) for t in traits if str(t) not in trait_ids)
    if unknown:
        return [_issue(
            index, optype, ERROR,
            f"Unknown trait id(s): {', '.join(unknown)}. Call list_library_traits for valid ids.",
            "traits",
        )]
    return []


def _action_issues(index: int, optype: str, patch: Any, valid_actions: Optional[Set[str]]) -> List[Dict[str, Any]]:
    if not valid_actions or not isinstance(patch, dict):
        return []
    actions = patch.get("actions")
    if not isinstance(actions, (list, str)):
        return []
    if isinstance(actions, str):
        actions = [a.strip() for a in actions.split(",") if a.strip()]
    unknown = sorted(str(a) for a in actions if str(a) not in valid_actions)
    if unknown:
        return [_issue(index, optype, WARNING,
                       f"Unrecognized item action(s): {', '.join(unknown)}.", "actions")]
    return []


def _id_warning(index: int, optype: str, node_id: Any) -> List[Dict[str, Any]]:
    text = str(node_id or "")
    if text and not ID_PATTERN.match(text):
        suggested = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return [_issue(index, optype, WARNING,
                       f"Id '{text}' is not the canonical lowercase form; prefer '{suggested}'.")]
    return []


def _node_index(nodes: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize a WorldGraph or a plain id->node mapping to lowercase keys."""
    index: Dict[str, Dict[str, Any]] = {}
    raw = getattr(nodes, "nodes", nodes) or {}
    if not isinstance(raw, dict):
        return index
    for nid, node in raw.items():
        if isinstance(node, dict):
            index[str(nid).lower()] = {"type": node.get("type"), "name": node.get("name")}
        else:
            index[str(nid).lower()] = {
                "type": getattr(node, "type", None),
                "name": getattr(node, "name", None),
            }
    return index


def _trigger_issues(idx: int, optype: str, props: Any) -> List[Dict[str, Any]]:
    """Validate a logic_trigger node's authored logic against the engine vocab.

    The editor can already mint an empty ``logic_trigger`` node; this is the half
    that stops it staging logic the engine will silently ignore: an unknown
    ``trigger_type``, an effect type outside ``EFFECT_TYPES``, or a condition
    tree whose operator/leaf shape is malformed.
    """
    issues: List[Dict[str, Any]] = []
    if not isinstance(props, dict):
        return issues
    try:
        from engine.triggers.constants import TRIGGER_TYPES, EFFECT_TYPES
        trigger_types = set(TRIGGER_TYPES)
        effect_types = set(EFFECT_TYPES)
    except Exception:
        return issues

    tt = props.get("trigger_type")
    if tt not in (None, "", [], {}):
        values = tt if isinstance(tt, list) else [tt]
        for v in values:
            if str(v) not in trigger_types:
                issues.append(_issue(idx, optype, ERROR, f"Unknown trigger_type '{v}'."))

    effects = props.get("effects")
    if effects is not None:
        if not isinstance(effects, list):
            issues.append(_issue(idx, optype, ERROR, "'effects' must be a list."))
        else:
            for ei, eff in enumerate(effects):
                if not isinstance(eff, dict) or not eff.get("type"):
                    issues.append(_issue(idx, optype, ERROR, f"effects[{ei}] needs a 'type'."))
                elif str(eff.get("type")) not in effect_types:
                    issues.append(_issue(idx, optype, ERROR,
                                         f"Unknown effect type '{eff.get('type')}' in effects[{ei}]."))
    legacy = props.get("effect_type")
    if legacy not in (None, "") and str(legacy) not in effect_types:
        issues.append(_issue(idx, optype, ERROR, f"Unknown effect_type '{legacy}'."))

    def _check_cond(node: Any, path: str) -> None:
        if not isinstance(node, dict):
            issues.append(_issue(idx, optype, ERROR, f"{path} must be an object."))
            return
        op = node.get("operator")
        if op is not None:
            if op not in ("and", "or", "not"):
                issues.append(_issue(idx, optype, ERROR, f"{path}.operator '{op}' must be and/or/not."))
            kids = node.get("conditions")
            if not isinstance(kids, list) or not kids:
                issues.append(_issue(idx, optype, ERROR, f"{path} needs a non-empty 'conditions' list."))
            else:
                for i, kid in enumerate(kids):
                    _check_cond(kid, f"{path}.conditions[{i}]")
            return
        if not node.get("type"):
            issues.append(_issue(idx, optype, ERROR, f"{path} is neither an operator group nor a leaf with a 'type'."))

    conditions = props.get("conditions")
    if conditions is not None:
        if isinstance(conditions, list):
            for i, leaf in enumerate(conditions):
                _check_cond(leaf, f"conditions[{i}]")
            logic = props.get("conditions_logic")
            if logic not in (None, "") and logic not in ("and", "or"):
                issues.append(_issue(idx, optype, ERROR, f"conditions_logic '{logic}' must be and/or."))
        else:
            _check_cond(conditions, "conditions")
    legacy_cond = props.get("condition")
    if legacy_cond is not None and not isinstance(legacy_cond, dict):
        issues.append(_issue(idx, optype, ERROR, "'condition' must be an object."))
    return issues


def _iter_condition_leaves(conditions: Any) -> List[Any]:
    """(path, leaf) for every condition leaf in a list (AND) or condition tree."""
    out: List[Any] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, list):
            for i, kid in enumerate(node):
                walk(kid, f"{path}.{i}" if path else str(i))
        elif isinstance(node, dict):
            if isinstance(node.get("conditions"), list):
                walk(node["conditions"], path)
            else:
                out.append((path, node))

    walk(conditions, "")
    return out


def _behaviour_issues(index: int, optype: str, behaviours: List[Any]) -> List[Dict[str, Any]]:
    """Validate a character's ``behaviors`` array against the runner's vocabulary.

    The NL editor could author behaviours in the *node/item* trigger vocabulary
    (``on_take``, ``on_night``) or with keys the engine never reads
    (``adjust_vital`` with ``vital``/``delta``, ``vital_below`` with no ``stat``,
    ``spawn_character`` with ``template``). None of those raise — they simply
    never fire — so the editor staged silently-dead behaviours (task-739).
    """
    issues: List[Dict[str, Any]] = []
    try:
        from engine.triggers.constants import EFFECT_TYPES
        effect_types = set(EFFECT_TYPES)
    except Exception:
        effect_types = set()
    valid_actions = effect_types | NPC_BEHAVIOUR_ACTIONS
    for bi, b in enumerate(behaviours):
        if not isinstance(b, dict):
            issues.append(_issue(index, optype, ERROR, f"behaviors[{bi}] must be an object."))
            continue
        trig = str(b.get("trigger") or "").strip()
        if trig and trig not in NPC_BEHAVIOUR_TRIGGERS:
            issues.append(_issue(index, optype, ERROR,
                f"behaviors[{bi}].trigger '{trig}' is not an NPC-behaviour trigger; "
                f"use one of {sorted(NPC_BEHAVIOUR_TRIGGERS)}."))
        actions = b.get("actions")
        if not isinstance(actions, list) or not actions:
            issues.append(_issue(index, optype, ERROR,
                                 f"behaviors[{bi}] needs a non-empty 'actions' list."))
            continue
        for ai, act in enumerate(actions):
            if not isinstance(act, dict) or not str(act.get("type") or "").strip():
                issues.append(_issue(index, optype, ERROR,
                                     f"behaviors[{bi}].actions[{ai}] needs a 'type'."))
                continue
            atype = str(act.get("type")).strip()
            if valid_actions and atype not in valid_actions:
                issues.append(_issue(index, optype, ERROR,
                    f"behaviors[{bi}].actions[{ai}] unknown action type '{atype}'."))
            elif atype == "adjust_vital" and ("stat" not in act or "amount" not in act):
                issues.append(_issue(index, optype, ERROR,
                    f"behaviors[{bi}].actions[{ai}] 'adjust_vital' needs 'stat' and 'amount' "
                    "(not 'vital'/'delta')."))
            elif atype == "spawn_character" and not act.get("character_id"):
                issues.append(_issue(index, optype, ERROR,
                    f"behaviors[{bi}].actions[{ai}] 'spawn_character' needs 'character_id' "
                    "(not 'template')."))
            elif atype == "start_activity" and not act.get("activity_type"):
                issues.append(_issue(index, optype, WARNING,
                    f"behaviors[{bi}].actions[{ai}] 'start_activity' reads 'activity_type', "
                    "not 'activity'."))
            elif atype == "apply_condition" and not act.get("condition"):
                issues.append(_issue(index, optype, ERROR,
                    f"behaviors[{bi}].actions[{ai}] 'apply_condition' needs 'condition'."))
        for ci, leaf in _iter_condition_leaves(b.get("conditions")):
            ctype = str(leaf.get("type") or "").strip()
            if ctype in ("vital_below", "vital_above", "vital") and not leaf.get("stat"):
                issues.append(_issue(index, optype, ERROR,
                    f"behaviors[{bi}].conditions[{ci}] '{ctype}' needs 'stat' "
                    "(it defaults to HP otherwise)."))
            if ctype == "random_chance" and leaf.get("chance") is None and leaf.get("value") is None:
                issues.append(_issue(index, optype, ERROR,
                    f"behaviors[{bi}].conditions[{ci}] 'random_chance' needs 'chance' or 'value'."))
    return issues


def validate_ops(
    ops: Iterable[Dict[str, Any]],
    *,
    nodes: Any = None,
    trait_ids: Optional[Iterable[str]] = None,
    valid_actions: Optional[Iterable[str]] = None,
    registries: Optional[Iterable[str]] = None,
    mature_content: bool = False,
    player_keys: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    """Return the issues (error/warning) in a staged op list, in op order."""
    ops = list(ops or [])
    index_map = _node_index(nodes)
    traits = {str(t) for t in (trait_ids if trait_ids is not None else TRAIT_DEFINITIONS.keys())}
    actions = {str(a) for a in valid_actions} if valid_actions is not None else set(KNOWN_ITEM_ACTIONS)
    allowed_registries = {str(r) for r in registries} if registries is not None else set(WRITABLE_REGISTRIES)

    issues: List[Dict[str, Any]] = []
    # Live ids evolve as the batch replays: creates add, deletes remove.
    known_ids: Set[str] = set(index_map)
    area_names: Dict[str, str] = {
        nid: str(meta.get("name") or "") for nid, meta in index_map.items()
        if meta.get("type") == "area"
    }
    character_names = {
        str(meta.get("name") or "").lower()
        for meta in index_map.values() if meta.get("type") == "character"
    }
    # Player REGISTRY keys, which can differ from the node display name after a
    # rename (task-447/619). A character-targeting op may name either.
    player_key_set = {str(k).strip().lower() for k in (player_keys or []) if k}

    def exists(node_id: Any) -> bool:
        return str(node_id or "").lower() in known_ids

    def player_exists(char: Any) -> bool:
        c = str(char or "").strip().lower()
        return bool(c) and (exists(c) or c in character_names or c in player_key_set)

    for idx, op in enumerate(ops):
        if not isinstance(op, dict):
            issues.append(_issue(idx, "?", ERROR, "Op must be an object."))
            continue
        optype = str(op.get("type") or "")
        payload = op.get("payload") if isinstance(op.get("payload"), dict) else {}
        if optype not in KNOWN_OP_TYPES:
            issues.append(_issue(idx, optype or "?", ERROR, f"Unknown op type '{optype}'."))
            continue

        if optype == "update_player":
            char = payload.get("character") or payload.get("character_id")
            if not player_exists(char):
                issues.append(_issue(idx, optype, ERROR,
                                     f"update_player needs a known 'character' (got {char!r})."))
            patch = payload.get("patch")
            if not isinstance(patch, dict) or not patch:
                issues.append(_issue(idx, optype, ERROR, "update_player needs a non-empty 'patch'."))
            else:
                unknown = [k for k in patch if k not in PLAYER_PATCH_KEYS]
                if unknown:
                    issues.append(_issue(idx, optype, ERROR,
                                         f"Unknown player patch key(s): {', '.join(sorted(unknown))}."))
                mems = patch.get("memories")
                if mems is not None:
                    if not isinstance(mems, list) or not mems:
                        issues.append(_issue(idx, optype, ERROR, "'memories' must be a non-empty list."))
                    else:
                        for mi, m in enumerate(mems):
                            if not isinstance(m, dict) or not str(m.get("text") or "").strip():
                                issues.append(_issue(idx, optype, ERROR,
                                                     f"memories[{mi}] needs non-empty 'text'."))
                rel = patch.get("relationship")
                if rel is not None:
                    if not isinstance(rel, dict) or not str(rel.get("target") or "").strip():
                        issues.append(_issue(idx, optype, ERROR, "'relationship' needs a 'target'."))
                    elif "closeness" in rel:
                        try:
                            int(rel.get("closeness"))
                        except (TypeError, ValueError):
                            issues.append(_issue(idx, optype, ERROR,
                                                 "'relationship.closeness' must be a number."))
                rem = patch.get("remove_relationship")
                if rem is not None and not str(rem).strip():
                    issues.append(_issue(idx, optype, ERROR, "'remove_relationship' must be a name."))
                beh = patch.get("behaviors")
                if beh is not None:
                    if not isinstance(beh, list):
                        issues.append(_issue(idx, optype, ERROR, "'behaviors' must be a list."))
                    else:
                        issues.extend(_behaviour_issues(idx, optype, beh))
                emo = patch.get("emotion")
                if emo is not None:
                    if not isinstance(emo, dict) or not str(emo.get("name") or "").strip():
                        issues.append(_issue(idx, optype, ERROR, "'emotion' needs a 'name'."))
                    else:
                        try:
                            from engine import emotion as _emotion
                            dims = set(_emotion.BASELINES)
                        except Exception:
                            dims = set()
                        if dims and str(emo.get("name")) not in dims:
                            issues.append(_issue(idx, optype, ERROR,
                                                 f"Unknown emotion dimension '{emo.get('name')}' "
                                                 f"(an unknown dim is silently ignored, so this is a no-op)."))
            continue

        if optype == "rename_character":
            char = payload.get("character") or payload.get("character_id")
            if not player_exists(char):
                issues.append(_issue(idx, optype, ERROR,
                                     f"rename_character needs a known 'character' (got {char!r})."))
            new_name = str(payload.get("new_name") or payload.get("name") or "").strip()
            if not new_name:
                issues.append(_issue(idx, optype, ERROR, "rename_character needs 'new_name'."))
            # No display-name collision check here: display names may repeat; only
            # the registry KEY must be unique, and the validator has no player keys.
            # `PlayerManager.rename_player` enforces key uniqueness at apply time.
            continue

        if optype == "create_trigger":
            owner = payload.get("owner_id")
            if not owner or not exists(owner):
                issues.append(_issue(idx, optype, ERROR,
                                     f"create_trigger needs a known 'owner_id' (got {owner!r})."))
            trig = payload.get("trigger")
            if not isinstance(trig, dict) or not trig:
                issues.append(_issue(idx, optype, ERROR,
                                     "create_trigger needs a non-empty 'trigger' definition."))
            else:
                issues.extend(_trigger_issues(idx, optype, trig))
            continue

        if optype == "create_node":
            node = payload.get("node") if isinstance(payload.get("node"), dict) else payload
            node_type = str(node.get("type") or node.get("kind") or "")
            name = node.get("name")
            nid = str(node.get("id") or "").lower()
            if not node_type or not name:
                issues.append(_issue(idx, optype, ERROR, "create_node needs 'type' and 'name'."))
            elif node_type not in KNOWN_TYPES:
                issues.append(_issue(idx, optype, ERROR, f"Unknown node type '{node_type}'."))
            if nid:
                if nid in known_ids:
                    issues.append(_issue(idx, optype, ERROR, f"Node id '{nid}' already exists."))
                known_ids.add(nid)
                issues.extend(_id_warning(idx, optype, node.get("id")))
                if node_type == "area":
                    duplicate = next((other for other, n in area_names.items()
                                      if n and n.lower() == str(name).lower() and other != nid), None)
                    if duplicate:
                        issues.append(_issue(idx, optype, WARNING,
                                             f"Another area is already named '{name}' ({duplicate})."))
                    area_names[nid] = str(name or "")
            if node_type == "logic_trigger":
                props = node.get("properties") if isinstance(node.get("properties"), dict) else node
                issues.extend(_trigger_issues(idx, optype, props))

        elif optype == "create_character":
            # A character is Player-backed (bug-527): the apply registers a
            # Player, which mints the canonical `player_<name>` node. The op
            # carries a `node` shim so ghosts/diffs read it like create_node.
            node = payload.get("node") if isinstance(payload.get("node"), dict) else payload
            name = node.get("name")
            nid = str(node.get("id") or "").lower()
            if not name:
                issues.append(_issue(idx, optype, ERROR, "create_character needs 'name'."))
            if nid:
                if nid in known_ids:
                    issues.append(_issue(idx, optype, ERROR,
                                         f"A character node '{node.get('id')}' already exists."))
                known_ids.add(nid)
            # `player_<Name>` ids are mixed case by convention (Player.node_id_for),
            # so the slug warning used for node ids does not apply here.

        elif optype == "update_node":
            nid = payload.get("node_id")
            if not nid:
                issues.append(_issue(idx, optype, ERROR, "update_node needs 'node_id'."))
            elif not exists(nid):
                issues.append(_issue(idx, optype, ERROR, f"Node '{nid}' not found."))
            patch = payload.get("patch")
            if not isinstance(patch, dict) or not patch:
                issues.append(_issue(idx, optype, ERROR, "update_node needs a non-empty 'patch'."))
            else:
                issues.extend(_trait_issues(idx, optype, patch, traits))
                issues.extend(_action_issues(idx, optype, patch, actions))
                issues.extend(_id_warning(idx, optype, payload.get("node_id")))
                if str(nid).lower() in index_map and \
                        index_map[str(nid).lower()].get("type") == "logic_trigger":
                    issues.extend(_trigger_issues(idx, optype, patch))

        elif optype == "update_matching_nodes":
            selector = payload.get("selector") if isinstance(payload.get("selector"), dict) else {}
            patch = payload.get("patch")
            if not any(k in selector and selector[k] not in (None, "", []) for k in BULK_SELECTOR_KEYS):
                issues.append(_issue(idx, optype, ERROR,
                                     "update_matching_nodes needs a non-empty selector."))
            if not isinstance(patch, dict) or not patch:
                issues.append(_issue(idx, optype, ERROR, "update_matching_nodes needs a non-empty 'patch'."))
            else:
                issues.extend(_trait_issues(idx, optype, patch, traits))
                issues.extend(_action_issues(idx, optype, patch, actions))
                if str(selector.get("kind") or selector.get("type") or "") == "logic_trigger":
                    issues.extend(_trigger_issues(idx, optype, patch))
            matched = payload.get("matched_ids")
            if matched is not None and (not isinstance(matched, list) or not matched):
                issues.append(_issue(idx, optype, ERROR,
                                     "matched_ids, when present, must be a non-empty list."))

        elif optype in ("attach", "detach"):
            for key in ("from_id", "to_id"):
                if not payload.get(key):
                    issues.append(_issue(idx, optype, ERROR, f"{optype} needs '{key}'."))
                elif not exists(payload.get(key)):
                    issues.append(_issue(idx, optype, ERROR, f"{optype} endpoint '{payload.get(key)}' not found."))

        elif optype == "delete_node":
            nid = payload.get("node_id")
            if not nid:
                issues.append(_issue(idx, optype, ERROR, "delete_node needs 'node_id'."))
            elif not exists(nid):
                issues.append(_issue(idx, optype, ERROR, f"delete_node: node '{nid}' not found."))
            else:
                known_ids.discard(str(nid).lower())

        elif optype == "connect_areas":
            for key in ("way_id", "area_a_id", "area_b_id"):
                if not payload.get(key):
                    issues.append(_issue(idx, optype, ERROR, f"connect_areas needs '{key}'."))
            a, b = payload.get("area_a_id"), payload.get("area_b_id")
            for label, area in (("area_a_id", a), ("area_b_id", b)):
                if area and not exists(area):
                    issues.append(_issue(idx, optype, ERROR, f"connect_areas {label} '{area}' not found."))
            if a and b and str(a).lower() == str(b).lower():
                issues.append(_issue(idx, optype, ERROR, "connect_areas needs two different areas."))
            way = payload.get("way_id")
            if way:
                if exists(way):
                    issues.append(_issue(idx, optype, ERROR, f"Way '{way}' already exists."))
                known_ids.add(str(way).lower())

        elif optype == "link_to_library":
            if not payload.get("node_id") or not exists(payload.get("node_id")):
                issues.append(_issue(idx, optype, ERROR, "link_to_library target node not found."))
            if not payload.get("library_id"):
                issues.append(_issue(idx, optype, ERROR, "link_to_library needs 'library_id'."))

        elif optype == "spawn_library_item":
            if not payload.get("library_id"):
                issues.append(_issue(idx, optype, ERROR, "spawn_library_item needs 'library_id'."))
            if not payload.get("parent_id"):
                issues.append(_issue(idx, optype, ERROR, "spawn_library_item needs 'parent_id'."))
            elif not exists(payload.get("parent_id")):
                issues.append(_issue(idx, optype, ERROR,
                                     f"spawn_library_item parent '{payload.get('parent_id')}' not found."))

        elif optype == "library_upsert":
            registry = str(payload.get("registry_type") or payload.get("registry") or "")
            entry_id = str(payload.get("id") or "")
            entry = payload.get("data") if isinstance(payload.get("data"), dict) else payload.get("entry")
            if registry not in allowed_registries:
                issues.append(_issue(idx, optype, ERROR,
                                     f"Library registry '{registry}' is not writable by the editor."))
            if not entry_id:
                issues.append(_issue(idx, optype, ERROR, "library_upsert needs 'id'."))
            elif not ID_PATTERN.match(entry_id):
                issues.append(_issue(idx, optype, ERROR,
                                     f"Library id '{entry_id}' must be a lowercase slug (a-z, 0-9, _)."))
            if not isinstance(entry, dict) or not entry:
                issues.append(_issue(idx, optype, ERROR, "library_upsert needs a non-empty entry object."))
            else:
                if registry == "traits":
                    effects = entry.get("effects")
                    if effects is not None and not isinstance(effects, dict):
                        issues.append(_issue(idx, optype, ERROR,
                                             "A trait template's 'effects' must be an object.", "effects"))
                entry_tags = {str(t).strip().lower() for t in (entry.get("tags") or [])}
                if "mature" in entry_tags and not mature_content:
                    issues.append(_issue(idx, optype, ERROR,
                                         "Mature library entries need mature content enabled."))

        elif optype == "library_delete":
            registry = str(payload.get("registry_type") or payload.get("registry") or "")
            if registry not in allowed_registries:
                issues.append(_issue(idx, optype, ERROR,
                                     f"Library registry '{registry}' is not writable by the editor."))
            if not payload.get("id"):
                issues.append(_issue(idx, optype, ERROR, "library_delete needs 'id'."))

    return issues


def errors_only(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [i for i in issues if i.get("severity") == ERROR]
