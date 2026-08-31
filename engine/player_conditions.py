# engine/player_conditions.py
"""Condition system — catalog, instance helpers, and derived constants.

All names formerly defined in player.py are re-exported from here so
``from player import CONDITION_DEFINITIONS`` keeps working via thin
delegates in player.py.
"""

import json
import os
from typing import Any, Dict, List, Optional

# ──────────────────────────────────────────────────────────────
# Condition catalog (Phase 1 + follow-up, task-trait-condition-system-v2)
# ──────────────────────────────────────────────────────────────

CONDITION_DEFINITIONS = {
    "awake": {
        "name": "Awake", "description": "Conscious and alert.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": [],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": ["unconscious"],
    },
    "dead": {
        "name": "Dead", "description": "Lifeless. No longer part of the living.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX", "CON"],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": True,
        "periodic": {}, "ends_on": [],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "unconscious": {
        "name": "Unconscious", "description": "Knocked out. Incapacitated until woken or revived.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": True,
        "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX"],
        "attack_mod": 0, "defense_mod": -5, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": True,
        "periodic": {}, "ends_on": ["wake", "damage", "timer"],
        "known": True, "symptoms": {}, "stack": "refresh", "default_duration": None,
        "excludes": ["awake"],
    },
    "paralysed": {
        "name": "Paralysed", "description": "Rigor locked. Can't move or act; fails STR/DEX saves. You keep your grip.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": True,
        "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX"],
        "attack_mod": 0, "defense_mod": -5, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["duration"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": 3,
        "excludes": [],
    },
    "stunned": {
        "name": "Stunned", "description": "Reeling. Can't act or move; fails STR/DEX saves. A fresh stun extends the countdown.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX"],
        "attack_mod": 0, "defense_mod": -5, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["duration"],
        "known": True, "symptoms": {}, "stack": "refresh", "default_duration": 2,
        "excludes": [],
    },
    "grappled": {
        "name": "Grappled", "description": "Held by someone. Speed 0 until you escape.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": -2, "defense_mod": 0, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["escape", "grappler_incapacitated"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "restrained": {
        "name": "Restrained", "description": "Tied or held fast. Speed 0; attacks at disadvantage.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": ["DEX"],
        "attack_mod": -2, "defense_mod": -2, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["escape"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "prone": {
        "name": "Prone", "description": "On the ground. You can only crawl and fight clumsily.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": -2, "defense_mod": -2, "speed_mult": 0.5,
        "movement_mode": "crawl", "drops_held_items": False,
        "periodic": {}, "ends_on": ["stand"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "busy": {
        "name": "Busy", "description": "Occupied with something. Interruptible.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["stop"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "exhausted": {
        "name": "Exhausted", "description": "Bone-tired. Energy drains away. Each fresh bout of exhaustion stacks a level (1-6).",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 0.5,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {"Energy": -3},
        "level_periodic": {1: {"Energy": -1}, 2: {"Energy": -2}, 3: {"Energy": -3},
                           4: {"Energy": -4}, 5: {"Energy": -4}, 6: {"Energy": -4}},
        "level_speed_mult": {1: 0.5, 2: 0.5, 3: 0.25, 4: 0.25, 5: 0.1, 6: 0.0},
        "ends_on": ["rest", "sleep"],
        "known": True, "symptoms": {}, "stack": "refresh", "default_duration": 5,
        "excludes": [],
    },
    "sick": {
        "name": "Sick", "description": "Ill. Hunger and thirst worsen.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {"Hunger": 2, "Thirst": 2}, "ends_on": ["duration", "cure"],
        "known": False, "stack": "accumulate", "default_duration": 8,
        "symptoms": {
            5: "You feel a little off.",
            3: "You ache and your stomach churns.",
            1: "Feverish and weak. You need to lie down.",
        },
        "excludes": [],
    },
    "poisoned": {
        "name": "Poisoned", "description": "Toxin in the blood. You're losing HP.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {"HP": -5}, "ends_on": ["duration", "antidote"],
        "known": False, "stack": "accumulate", "default_duration": 10,
        "symptoms": {
            6: "A queasy twist in your stomach.",
            3: "Cold sweat. Your gut cramps and your head swims.",
            1: "Everything spins. Your limbs feel wrong.",
        },
        "excludes": [],
    },
    "wet": {
        "name": "Wet", "description": "Soaked through. Wet clothing insulates far worse (and you're miserable).",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["dry", "cure"],
        "known": True, "symptoms": {}, "stack": "refresh", "default_duration": None,
        "excludes": [],
    },
    "injured": {
        "name": "Injured", "description": "A wounded body part. Light/moderate/severe (level 1-3) — needs healing.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {},
        "level_periodic": {1: {"HP": -1}, 2: {"HP": -2}, 3: {"HP": -3}},
        "level_speed_mult": {1: 1.0, 2: 0.75, 3: 0.5},
        "ends_on": ["fix", "heal", "medicine"],
        "known": True,
        "symptoms": {
            3: "The {body_part} throbs painfully.",
            2: "The {body_part} aches badly — you favour it.",
            1: "The {body_part} is badly hurt. Every move sends a spike of pain.",
        },
        "stack": "accumulate", "default_duration": None,
        "excludes": [],
    },
    "bleeding": {
        "name": "Bleeding", "description": "An open wound on a body part, losing blood each tick until treated.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {"HP": -2, "Hygiene": -1},
        "level_periodic": {1: {"HP": -1}, 2: {"HP": -2}, 3: {"HP": -3}},
        "ends_on": ["fix", "heal", "medicine"],
        "known": True,
        "symptoms": {
            5: "The {body_part} is bleeding — warm blood soaks your skin.",
            3: "Blood continues to flow from the {body_part}.",
            1: "The {body_part} keeps bleeding. You're getting light-headed.",
        },
        "stack": "accumulate", "default_duration": None,
        "excludes": [],
    },
    "hypothermia": {
        "name": "Hypothermia", "description": "Exposure. Your body is shutting down to stay warm.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": ["dexterity"], "auto_fail_saves": [],
        "attack_mod": -1, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {"Energy": -2, "HP": -1},
        "level_periodic": {1: {"Energy": -1, "HP": 0}, 2: {"Energy": -2, "HP": -1},
                           3: {"Energy": -4, "HP": -3}},
        "level_speed_mult": {1: 0.9, 2: 0.6, 3: 0.3},
        "ends_on": ["warm_up", "cure"],
        "known": True,
        "symptoms": {
            1: "Shuddering. Your fingers are clumsy.",
            2: "The shaking won't stop. Your breathing is slow.",
            3: "Warm and sleepy. That's the dangerous part.",
        },
        "stack": "accumulate", "default_duration": None,
        "excludes": [],
    },
    "suffocating": {
        "name": "Suffocating", "description": "No air. Every tick with no breath is one closer to blackout.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX"],
        "attack_mod": -3, "defense_mod": -5, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {"Energy": -3, "HP": -2}, "ends_on": ["breathe", "unblock"],
        "known": False, "stack": "refresh", "default_duration": 4,
        "symptoms": {
            3: "Chest burning. Each gasp is needles.",
            1: "Black spots swim. You need air. NOW.",
        },
        "excludes": [],
    },
    "petrified": {
        "name": "Petrified", "description": "Stone from the neck down. Seen but not felt.",
        "blocks_actions": True, "blocks_movement": True, "blocks_speech": True,
        "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX", "CON"],
        "attack_mod": 0, "defense_mod": 5, "speed_mult": 0.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["cure", "unpetrify"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "blind": {
        "name": "Blind", "description": "Can't see. Sight checks fail; attacks are clumsy.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": ["sight"], "auto_fail_saves": [],
        "attack_mod": -2, "defense_mod": -2, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["duration", "cure"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": 5,
        "excludes": [],
    },
    "deaf": {
        "name": "Deaf", "description": "Can't hear. Hearing cues are lost.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": ["hearing"], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["duration", "cure"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": 5,
        "excludes": [],
    },
    "mute": {
        "name": "Mute", "description": "Can't speak. No sound comes out.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": True,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": ["duration", "cure"],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "frightened": {
        "name": "Frightened", "description": "Terrified of something. You can't fight it off and won't go back near it.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": -2, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": [],
        "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
    "charmed": {
        "name": "Charmed", "description": "Magically compelled by someone. You can't bring yourself to hurt them.",
        "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
        "auto_fail_checks": [], "auto_fail_saves": [],
        "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
        "movement_mode": None, "drops_held_items": False,
        "periodic": {}, "ends_on": [],
        "known": False, "symptoms": {}, "stack": "noop", "default_duration": None,
        "excludes": [],
    },
}

# Defaults for library-loaded conditions
_CONDITION_BASE = {
    "name": "", "description": "",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": [],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}


# ──────────────────────────────────────────────────────────────
# Catalog loading
# ──────────────────────────────────────────────────────────────

def _condition_library_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'library', 'conditions')


def _load_condition_library():
    """Merge data-driven condition definitions from data/library/conditions/*.json.

    Runs at import time so the derived constants below and any module that
    imports them capture the post-load catalog. For a condition that already
    exists in the hardcoded catalog, the file merges over the fallback entry,
    so a partial/truncated file can't wipe start-time behavior.
    """
    cond_dir = _condition_library_dir()
    if not os.path.isdir(cond_dir):
        return
    for fname in sorted(os.listdir(cond_dir)):
        if not fname.endswith('.json'):
            continue
        cond_id = fname[:-5]
        try:
            with open(os.path.join(cond_dir, fname), 'r', encoding='utf-8-sig') as f:
                entry = json.load(f)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        base = CONDITION_DEFINITIONS.get(cond_id, _CONDITION_BASE)
        merged = dict(base)
        merged.update(entry)
        merged.setdefault('name', cond_id.title().replace('_', ' '))
        for nested_key in ('symptoms', 'level_periodic', 'level_speed_mult'):
            nested = merged.get(nested_key)
            if isinstance(nested, dict):
                rebuilt = {}
                for k, v in nested.items():
                    try:
                        rebuilt[int(k)] = v
                    except (ValueError, TypeError):
                        rebuilt[k] = v
                merged[nested_key] = rebuilt
        CONDITION_DEFINITIONS[cond_id] = merged


_load_condition_library()


def seed_condition_library():
    """Write the current catalog into data/library/conditions/*.json.

    Called once at app startup (non-TESTING) when the conditions library is empty,
    so the library browser's Conditions tab has a real, editable source of truth.
    Never overwrites existing files.
    """
    cond_dir = _condition_library_dir()
    try:
        os.makedirs(cond_dir, exist_ok=True)
    except OSError:
        return
    if any(fname.endswith('.json') for fname in os.listdir(cond_dir)):
        return
    for cond_id, definition in CONDITION_DEFINITIONS.items():
        path = os.path.join(cond_dir, f"{cond_id}.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(definition, f, indent=2, ensure_ascii=False)
        except OSError:
            continue


# ──────────────────────────────────────────────────────────────
# Derived constants
# ──────────────────────────────────────────────────────────────

CONDITION_HIERARCHY = [
    "dead", "unconscious",
    "paralysed", "stunned",
    "grappled", "restrained", "prone",
    "busy", "exhausted",
    "sick", "poisoned",
    "wet", "injured", "bleeding", "hypothermia",
    "suffocating", "petrified",
    "blind", "deaf",
    "frightened", "charmed",
    "awake",
]

BLOCKING_CONDITIONS = frozenset(
    cid for cid, definition in CONDITION_DEFINITIONS.items() if definition["blocks_actions"]
)

PERIODIC_CONDITIONS = {
    cid: definition["periodic"]
    for cid, definition in CONDITION_DEFINITIONS.items() if definition["periodic"]
}

CONDITION_EXCLUSIONS = {
    cid: set(definition["excludes"])
    for cid, definition in CONDITION_DEFINITIONS.items()
}

CONDITION_DEFAULT_TIMERS = {
    cid: definition["default_duration"]
    for cid, definition in CONDITION_DEFINITIONS.items()
    if definition["default_duration"] is not None
}


# ──────────────────────────────────────────────────────────────
# Instance helpers
# ──────────────────────────────────────────────────────────────

def _normalize_instance(inst: dict) -> dict:
    """Normalize a serialized condition instance dict.

    Keeps the base fields (duration/source/level) plus any non-None override
    fields so they round-trip through saves.
    """
    normalized = {
        "duration": inst.get("duration"),
        "source": inst.get("source"),
        "level": inst.get("level", 0),
    }
    for key, value in inst.items():
        if key in ("duration", "source", "level"):
            continue
        if value is not None:
            normalized[key] = value
    return normalized


# ──────────────────────────────────────────────────────────────
# Standalone condition helpers (instance-first arg)
# ──────────────────────────────────────────────────────────────

def condition_has_condition(player, condition: str) -> bool:
    """True when the player has at least one instance of *condition*."""
    return bool(player.conditions.get(condition))


def condition_add_condition(player, condition: str, duration=None, source=None, level=None,
                            periodic=None, extra_conditions=None, ends_on=None,
                            symptoms=None, known=None, source_type=None, overrides=None):
    """Apply a condition instance (or bundle).

    Stacking (catalog `stack` field):
      - "accumulate" (poisoned/sick): appends a new instance.
      - "refresh" (stunned/exhausted): extends the existing instance.
      - "noop" (grappled/restrained/blind/...): does nothing when already present.
    Exclusions remove all instances of conflicting conditions.
    """
    if condition in CONDITION_EXCLUSIONS:
        for excluded in CONDITION_EXCLUSIONS[condition]:
            player.conditions.pop(excluded, None)

    definition = CONDITION_DEFINITIONS.get(condition, {})
    stack = definition.get("stack", "noop")
    existing = player.conditions.get(condition)

    if existing and stack == "noop":
        return
    if existing and stack == "refresh":
        target = existing[0]
        if duration is not None:
            cur = target.get("duration")
            if cur is None or duration > cur:
                target["duration"] = duration
        if source is not None:
            target["source"] = source
        if source_type is not None:
            target["source_type"] = source_type
        if level is not None:
            cur_level = target.get("level", 0) or 0
            target["level"] = max(cur_level, level)
        elif condition == "exhausted":
            cur_level = target.get("level", 0) or 0
            target["level"] = min(6, cur_level + 1)
        if periodic is not None:
            target["periodic"] = periodic
        if ends_on is not None:
            target["ends_on"] = ends_on
        if symptoms is not None:
            target["symptoms"] = symptoms
        if known is not None:
            target["known"] = known
        if overrides:
            target.update(overrides)
    else:
        instance = {"duration": duration, "source": source, "level": level or 0}
        if source_type is not None:
            instance["source_type"] = source_type
        if condition == "exhausted" and level is None:
            instance["level"] = 1
        if periodic is not None:
            instance["periodic"] = periodic
        if ends_on is not None:
            instance["ends_on"] = ends_on
        if symptoms is not None:
            instance["symptoms"] = symptoms
        if known is not None:
            instance["known"] = known
        if overrides:
            instance.update(overrides)
        player.conditions.setdefault(condition, []).append(instance)

    if extra_conditions:
        for extra in extra_conditions:
            if isinstance(extra, str):
                condition_add_condition(player, extra)
            else:
                condition_add_condition(
                    player,
                    extra.get("condition") or extra.get("id"),
                    duration=extra.get("duration"),
                    source=extra.get("source", source),
                    level=extra.get("level"),
                    periodic=extra.get("periodic"),
                    extra_conditions=extra.get("extra_conditions"),
                    ends_on=extra.get("ends_on"),
                    symptoms=extra.get("symptoms"),
                    known=extra.get("known"),
                    overrides=extra.get("overrides"),
                )


def condition_remove_condition(player, condition: str):
    """Remove all instances of *condition*."""
    player.conditions.pop(condition, None)
    if not player.conditions:
        player.conditions["awake"] = [{"duration": None, "source": None, "level": 0}]


def condition_end_instances(player, action: str):
    """Remove every instance whose effective ends_on includes *action*.

    Returns the removed ``(condition_id, source)`` pairs.
    """
    removed = []
    for cid, instances in list(player.conditions.items()):
        definition = CONDITION_DEFINITIONS.get(cid, {})
        keep = []
        for inst in instances:
            ends_on = inst.get("ends_on")
            if ends_on is None:
                ends_on = definition.get("ends_on", [])
            if action in ends_on:
                removed.append((cid, inst.get("source")))
            else:
                keep.append(inst)
        if keep:
            player.conditions[cid] = keep
        else:
            player.conditions.pop(cid, None)
    if not player.conditions:
        player.conditions["awake"] = [{"duration": None, "source": None, "level": 0}]
    return removed


def condition_load_conditions(player, payload):
    """Replace conditions from serialized data."""
    if isinstance(payload, dict):
        player.conditions = {}
        for cid, value in payload.items():
            if isinstance(value, list):
                instances = []
                for inst in value:
                    if isinstance(inst, dict):
                        instances.append(_normalize_instance(inst))
                    elif isinstance(inst, int):
                        instances.append({"duration": inst, "source": None, "level": 0})
                    else:
                        instances.append({"duration": CONDITION_DEFAULT_TIMERS.get(cid),
                                          "source": None, "level": 0})
                player.conditions[cid] = instances
            elif isinstance(value, dict):
                player.conditions[cid] = [_normalize_instance(value)]
            else:
                player.conditions[cid] = [{"duration": CONDITION_DEFAULT_TIMERS.get(cid),
                                            "source": None, "level": 0}]
    elif isinstance(payload, (list, tuple, set)):
        player.conditions = {
            cid: [{"duration": CONDITION_DEFAULT_TIMERS.get(cid), "source": None, "level": 0}]
            for cid in payload
        }
    else:
        return
    if not player.conditions:
        player.conditions = {"awake": [{"duration": None, "source": None, "level": 0}]}


# ──────────────────────────────────────────────────────────────
# State property helpers
# ──────────────────────────────────────────────────────────────

def get_state(player) -> str:
    """Return the most significant condition for backward compat."""
    for c in CONDITION_HIERARCHY:
        if condition_has_condition(player, c):
            return c
    return "awake"


def set_state(player, value: str):
    """Set a state — ADDS the condition without wiping others."""
    condition_add_condition(player, value)


def get_state_timer(player) -> int:
    """Backward-compat: ticks remaining on the current state condition."""
    instances = player.conditions.get(get_state(player)) or []
    finite = [i.get("duration") for i in instances if isinstance(i.get("duration"), int)]
    return max(finite) if finite else 0


def set_state_timer(player, value: int):
    """Backward-compat: set the current state condition's countdown duration."""
    instances = player.conditions.get(get_state(player))
    if not instances:
        return
    finite = [i for i in instances if isinstance(i.get("duration"), int)]
    target = max(finite, key=lambda i: i["duration"]) if finite else instances[0]
    target["duration"] = value
