# player.py
import re
import time
import uuid


# ── Condition catalog (Phase 1 + follow-up, task-trait-condition-system-v2) ──
# One canonical definition per condition (D&D-inspired vocabulary, NOT ground
# truth — simulation realism wins). A creature can hold MULTIPLE INSTANCES of a
# condition (5 vials of poison = 5 stacked `poisoned` instances).
# Fields:
#   blocks_actions / blocks_movement / blocks_speech — hard gates (presence-based)
#   auto_fail_checks / auto_fail_saves — sense/stat checks that auto-fail
#   attack_mod / defense_mod — combat roll modifiers. `defense_mod` is YOUR
#     defense: combat applies `attack + attack_mod - target_defense_mod`, so a
#     positive defense makes you HARDER to hit; helpless conditions carry a
#     NEGATIVE defense_mod (the target's own reduction IS the attacker's +X).
#   speed_mult / movement_mode / drops_held_items — movement & inventory hooks
#   periodic — per-tick vital drains {stat: amount}; instance `periodic` overrides
#   ends_on — actions/triggers that end this condition; instance `ends_on` overrides
#   known — True: self-evident to the agent (renders physical description);
#           False: hidden (agent only ever sees `symptoms`, never the flag)
#   symptoms — {min_remaining: line}; the agent perceives the highest threshold
#              reached (or keyed by `level` for leveled diseases)
#   stack — "accumulate": re-apply appends an instance (drains sum);
#           "refresh":   re-apply extends duration / bumps level (stun, exhaustion);
#           "noop":      re-apply does nothing (can't grab a grappled person)
#   default_duration — ticks; None = until countered/removed
#   excludes — condition ids this one removes when applied
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
        "name": "Exhausted", "description": "Bone-tired. Energy drains away. Each fresh bout of exhaustion stacks a level (1–6).",
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

# Defaults for library-loaded conditions: any field a JSON file omits falls
# back to these neutral values, so a partial/truncated entry never breaks the
# engine's ``definition["field"]`` reads (e.g. BLOCKING_CONDITIONS below).
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


def _condition_library_dir():
    import os as _os
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'data', 'library', 'conditions')


def _load_condition_library():
    """Merge data-driven condition definitions from data/library/conditions/*.json.

    Runs at import time so the derived constants below (BLOCKING_CONDITIONS,
    PERIODIC_CONDITIONS, CONDITION_EXCLUSIONS, CONDITION_DEFAULT_TIMERS) and any
    module that imports them capture the post-load catalog. For a condition that
    already exists in the hardcoded catalog, the file merges over the fallback
    entry, so a partial/truncated file can't wipe start-time behavior.
    """
    import json as _json
    import os as _os
    cond_dir = _condition_library_dir()
    if not _os.path.isdir(cond_dir):
        return
    for fname in sorted(_os.listdir(cond_dir)):
        if not fname.endswith('.json'):
            continue
        cond_id = fname[:-5]
        try:
            with open(_os.path.join(cond_dir, fname), 'r', encoding='utf-8-sig') as f:
                entry = _json.load(f)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        base = CONDITION_DEFINITIONS.get(cond_id, _CONDITION_BASE)
        merged = dict(base)
        merged.update(entry)
        merged.setdefault('name', cond_id.title().replace('_', ' '))
        # JSON can't express int dict keys: symptoms (keyed by remaining
        # duration), level_periodic and level_speed_mult (keyed 1-6) reload as
        # strings. Coerce them back to ints so engine lookups by int still hit.
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
    Never overwrites existing files — the fallback-merge above keeps loaded entries
    equivalent to the hardcoded catalog, so this is safe even before Phase 2 fixes
    the tab's editor schema.
    """
    import json as _json
    import os as _os
    cond_dir = _condition_library_dir()
    try:
        _os.makedirs(cond_dir, exist_ok=True)
    except OSError:
        return
    if any(fname.endswith('.json') for fname in _os.listdir(cond_dir)):
        return
    for cond_id, definition in CONDITION_DEFINITIONS.items():
        path = _os.path.join(cond_dir, f"{cond_id}.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                _json.dump(definition, f, indent=2, ensure_ascii=False)
        except OSError:
            continue


# Condition priority order (first = most significant for display/lookup)
CONDITION_HIERARCHY = [
    "dead", "unconscious",
    "paralysed", "stunned",
    "grappled", "restrained", "prone",
    "busy", "exhausted",
    "sick", "poisoned", "blind", "deaf",
    "frightened", "charmed",
    "awake",
]

# Conditions that prevent acting (derived from the catalog)
BLOCKING_CONDITIONS = frozenset(
    cid for cid, definition in CONDITION_DEFINITIONS.items() if definition["blocks_actions"]
)

# Conditions with periodic tick effects (derived from the catalog)
PERIODIC_CONDITIONS = {
    cid: definition["periodic"]
    for cid, definition in CONDITION_DEFINITIONS.items() if definition["periodic"]
}

# Conditions that conflict (add → removes conflicting; derived from the catalog)
CONDITION_EXCLUSIONS = {
    cid: set(definition["excludes"])
    for cid, definition in CONDITION_DEFINITIONS.items()
}

# Default timers (ticks) for timed conditions (derived from the catalog)
CONDITION_DEFAULT_TIMERS = {
    cid: definition["default_duration"]
    for cid, definition in CONDITION_DEFINITIONS.items()
    if definition["default_duration"] is not None
}


def _normalize_instance(inst: dict) -> dict:
    """Normalize a serialized condition instance dict.

    Keeps the base fields (duration/source/level) plus any non-None override
    fields (periodic, ends_on, symptoms, known, and gate overrides like
    blocks_speech / drops_held_items) so they round-trip through saves.
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


class Player:
    def sync_vitals_with_tags(self):
        """Add or remove Mana vital based on 'magic' tag."""
        if "magic" in self.tags:
            if "Mana" not in self.vitals:
                self.vitals["Mana"] = 100
            if "Mana" not in self.decay_rates:
                self.decay_rates["Mana"] = 0
        else:
            self.vitals.pop("Mana", None)
            self.decay_rates.pop("Mana", None)

    def __init__(self, name="Traveler"):
        self.name = name
        # Free-form description/personality text for this character
        self.personality = ""
        # Base physical description (naked/baseline appearance — what they look like with nothing on)
        self.base_description = ""
        # Current outward-facing description (auto-generated from base + equipment, or manually set)
        self.description = ""
        # Explicit label used until another character meets this one. When empty,
        # a label is derived from `description` (task-154).
        self.unknown_name = ""
        
        # D&D Core Stats
        self.stats = {
            "STR": 10, "DEX": 10, "CON": 10,
            "INT": 10, "WIS": 10, "CHA": 10
        }
        
        # Vitals & Needs (Max 100)
        # Hunger/Thirst are DRIVES (task-337 flip): 0 = fed/hydrated,
        # 100 = starving/dehydrated. Spawn satisfied, they fill over time.
        self.vitals = {
            "HP": 100, "Max_HP": 100,
            "Hunger": 0, "Thirst": 0,
            "Hygiene": 100, "Energy": 100,
            "Social": 100,
            "Bladder": 0, "Sanity": 100,
            "Entertainment": 100, "Temperature": 37.0
        }

        # Per-character decay rate overrides (defaults match engine baseline)
        self.decay_rates = {
            "Hunger": 1, "Thirst": 1, "Energy": 1, "Social": 1,
            "Hygiene": 1, "Bladder": 1, "Sanity": 1, "Entertainment": 1
        }

        # Per-body-part numeric state (task-253 body-part taxonomy). Flat dict
        # keyed by region id from engine/body_parts.py: each region has a base
        # `sensitivity` and an `injury` slot (None until combat/conditions set
        # one). Erogenous numeric fields (hardness, wetness, flush, ...) extend
        # this per-region dict in task-207.
        from engine.body_parts import default_body_state
        self.body_state = default_body_state()
        
        # Basic Skills
        self.skills = {
            "Athletics": 1, "Acrobatics": 1,
            "Stealth": 1, "Perception": 1,
            "Survival": 1, "Persuasion": 1
        }
        # Traits: mapping trait_id -> parameter value.
        # Boolean traits use True. Parameterized traits use a string (e.g. {"allergic": "pollen"}).
        # Example: {"dark_vision": True, "hardy": True, "glutton": True}
        self.traits = {}
        # Tags: identity markers for this character, checked by items/triggers/conditions.
        # Examples: ["vampire", "faction:guard", "synthetic", "nobility"]
        self.tags = []
        # Interest tags: what this character pays attention to in a room.
        # Items matching these tags (or their keywords) surface in the prompt's
        # "Items that catch your attention" list before other items.
        # Examples: ["magic", "food", "weapon", "documents"]
        self.interest_tags = []
        # Conditions system: {condition_id: [instance, instance, ...]} — MULTIPLE
        # concurrent instances per condition (5 vials of poison = 5 `poisoned`
        # instances). Each instance: {duration, source, level, periodic, ends_on,
        # symptoms, known} where the optional fields override the catalog default.
        # duration = ticks remaining (None = until countered/removed).
        self.conditions = {"awake": [{"duration": None, "source": None, "level": 0}]}
        # Track discovered exits: set of (area_name, direction) tuples
        self.discovered_exits = set()
        # Way knowledge learned the hard way (task-333): {(area_name, direction):
        # set of aspect strings} — 'locked', 'blocked', 'needs_force'. The turn
        # panel only reveals these once discovered (examine or a failed go).
        self.known_way_aspects = {}
        # Track areas the character has visited (for Entertainment novelty bonus)
        self.visited_areas = set()
        # Track items the character has discovered (for Entertainment novelty bonus)
        self.discovered_items = set()
        # Current area location (for multi-player support)
        self.current_area = None
        # Recent speech heard: list of dicts {speaker, text, tick, timestamp}
        self.recent_hearing = []
        # === SIMPLE NPC (no LLM) ===
        self.simple_npc = False
        # Human-driven flag: autonomy False = a human player drives this
        # character (the browser agent engine skips it and surfaces the human
        # turn composer). Persisted so it survives reloads/saves.
        self.autonomy = True
        self.npc_behavior = "wander"  # wander, flee, stationary
        self.npc_action_interval = 3  # act every N ticks
        self.npc_state = "idle"        # behavior state machine
        self.state_enter_tick = 0       # tick when npc_state was entered
        self.behaviors = []             # list of behavior definitions
        self.patrol_route = []          # ordered area names for patrol mode
        self.patrol_index = 0           # current index in patrol_route

        # === ACTIVITY SYSTEM (task-131) ===
        # What the character is *doing* across turns. Purely descriptive —
        # mechanical gating comes from player.state + conditions.
        #   None | {"type": str, "started_at_tick": int, "target_item": str|None,
        #           "duration_ticks": int|None, "elapsed_ticks": int, "visible": bool}
        # Types: sleeping, resting, waiting, meditating, bathing, sitting, lying down
        self.activity = None

        # === EMOTION SYSTEM ===
        # Current emotional state from the allowed set:
        # neutral, happy, sad, angry, afraid, surprised, disgusted
        self.emotion = "neutral"
        # How strongly the current emotion is felt (0.0 to 1.0)
        # Higher = more influence on behavior
        self.emotion_intensity = 0.0
        # Multi-dimensional affect map (task-96): {dim: 0-100}, lazily
        # initialized to baselines via emotions_map(). None = untouched.
        self._emotions = None

        # === SOCIAL RELATIONSHIPS ===
        # Dict of {other_player_name: {"closeness": -100-100, "last_interaction_tick": int, "interaction_count": int}}
        # closeness: -100 = sworn enemy, -50 = rival, 0 = neutral, 50 = friend, 100 = inseparable
        self.relationships = {}

        # === EQUIPMENT ===
        # Slots mapped to lists of item node IDs. Stack order = wear order.
        # Index 0 = innermost (closest to skin), last index = outermost.
        self.equipped = {
            "head": [], "neck": [], "torso": [], "arms": [],
            "hands": [], "legs": [], "feet": [], "back": [],
            "waist": [], "accessory": [],
            "hand_left": [], "hand_right": []
        }

        # === MEMORY STORE ===
        # List of {text, tick, timestamp, importance (1-10), type, embedding (optional)}
        self.memories = []

        self.sync_vitals_with_tags()

    # ── Backward-compatible state property ──────────────────────────
    @property
    def state(self):
        """Return the most significant condition for backward compat."""
        for c in CONDITION_HIERARCHY:
            if self.has_condition(c):
                return c
        return "awake"

    @state.setter
    def state(self, value):
        """Set a state — ADDS the condition without wiping others (wake/energy-
        collapse/end-activity no longer clear poisoned, blind, etc.). Conflicts
        are resolved by the catalog exclusions."""
        self.add_condition(value)

    def has_condition(self, condition: str) -> bool:
        return bool(self.conditions.get(condition))

    def add_condition(self, condition: str, duration=None, source=None, level=None,
                      periodic=None, extra_conditions=None, ends_on=None,
                      symptoms=None, known=None, source_type=None, overrides=None):
        """Apply a condition instance (or bundle).

        Stacking (catalog `stack` field):
          - "accumulate" (poisoned/sick): appends a new instance — drains sum.
          - "refresh" (stunned/exhausted): extends the existing instance — a fresh
            stun extends the countdown; re-exhaustion bumps `level` toward 6.
          - "noop" (grappled/restrained/blind/...): does nothing when already
            present — you can't grab a grappled person or blind a blind one.
        Exclusions remove all instances of conflicting conditions.
        ``extra_conditions`` (bundled conditions) apply as separate instances.
        ``overrides`` merges arbitrary catalog gate fields onto the instance
        (``blocks_speech``, ``drops_held_items``, ``blocks_actions``, ...).
        ``source_type`` classifies the source ("way"/"area"/"item"/"character")
        so frightened gates know what to block.
        """
        if condition in CONDITION_EXCLUSIONS:
            for excluded in CONDITION_EXCLUSIONS[condition]:
                self.conditions.pop(excluded, None)

        definition = CONDITION_DEFINITIONS.get(condition, {})
        stack = definition.get("stack", "noop")
        existing = self.conditions.get(condition)

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
                instance["level"] = 1  # exhaustion ladder starts at level 1
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
            self.conditions.setdefault(condition, []).append(instance)

        if extra_conditions:
            for extra in extra_conditions:
                if isinstance(extra, str):
                    self.add_condition(extra)
                else:
                    self.add_condition(
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

    def remove_condition(self, condition: str):
        self.conditions.pop(condition, None)
        if not self.conditions:
            self.conditions["awake"] = [{"duration": None, "source": None, "level": 0}]

    def end_instances(self, action: str):
        """Remove every instance whose effective ends_on includes *action*.

        ``ends_on`` is resolved per-instance: an instance override wins, else the
        catalog default. So ``fix`` ends only the broken-leg ``prone`` instance
        while ``stand`` ends only the knock-down one.
        Returns the removed ``(condition_id, source)`` pairs.
        """
        removed = []
        for cid, instances in list(self.conditions.items()):
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
                self.conditions[cid] = keep
            else:
                self.conditions.pop(cid, None)
        if not self.conditions:
            self.conditions["awake"] = [{"duration": None, "source": None, "level": 0}]
        return removed

    @property
    def state_timer(self) -> int:
        """Backward-compat: ticks remaining on the current state condition
        (the longest finite duration across its instances; 0 when permanent)."""
        instances = self.conditions.get(self.state) or []
        finite = [i.get("duration") for i in instances if isinstance(i.get("duration"), int)]
        return max(finite) if finite else 0

    @state_timer.setter
    def state_timer(self, value):
        """Backward-compat: set the current state condition's countdown duration
        on its primary (longest-finite) instance."""
        instances = self.conditions.get(self.state)
        if not instances:
            return
        finite = [i for i in instances if isinstance(i.get("duration"), int)]
        target = max(finite, key=lambda i: i["duration"]) if finite else instances[0]
        target["duration"] = value

    def load_conditions(self, payload):
        """Replace conditions from serialized data.

        Accepts the new dict-of-lists format (``{cid: [instance, ...]}``), the
        Phase 1 dict-of-single-instance format, a legacy list/set of condition
        names, or None (keeps current state). Legacy entries without metadata
        get default timers from the catalog so timed conditions still expire.
        """
        if isinstance(payload, dict):
            self.conditions = {}
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
                    self.conditions[cid] = instances
                elif isinstance(value, dict):
                    self.conditions[cid] = [_normalize_instance(value)]
                else:
                    self.conditions[cid] = [{"duration": CONDITION_DEFAULT_TIMERS.get(cid),
                                             "source": None, "level": 0}]
        elif isinstance(payload, (list, tuple, set)):
            self.conditions = {
                cid: [{"duration": CONDITION_DEFAULT_TIMERS.get(cid), "source": None, "level": 0}]
                for cid in payload
            }
        else:
            return
        if not self.conditions:
            self.conditions = {"awake": [{"duration": None, "source": None, "level": 0}]}

    def set_emotion(self, new_emotion: str, intensity: float = 0.3):
        """Set the character's emotion with the given intensity."""
        allowed = ["neutral", "happy", "sad", "angry", "afraid", "surprised", "disgusted"]
        if new_emotion not in allowed:
            raise ValueError(f"Invalid emotion '{new_emotion}'. Must be one of {allowed}")
        self.emotion = new_emotion
        self.emotion_intensity = max(0.0, min(1.0, intensity))

    # === Multi-dimensional affect (task-96) ===

    def emotions_map(self) -> dict:
        """The full affect map, lazily initialized to baselines."""
        from engine import emotion as _emotion
        if self._emotions is None:
            self._emotions = _emotion.baseline()
        return self._emotions

    def spike_emotion(self, emotion: str, delta: float) -> None:
        """Nudge one affect dimension (clamped 0-100). Unknown dims ignored."""
        from engine import emotion as _emotion
        _emotion.spike(self.emotions_map(), emotion, delta)

    def decay_emotions(self) -> None:
        """Per-tick drift of all dimensions toward baseline (tick_manager hook)."""
        from engine import emotion as _emotion
        if self._emotions is not None:
            _emotion.decay(self._emotions)

    def emotions_description(self) -> str:
        """First-person mood paragraph for prompts ('' when near-neutral)."""
        from engine import emotion as _emotion
        if self._emotions is None:
            return ""
        return _emotion.describe(self._emotions)

    def load_emotions(self, data) -> None:
        """Restore a stored emotion map from a scenario/save dict."""
        from engine import emotion as _emotion
        self._emotions = _emotion.normalize(data)

    def get_emotion_nl(self) -> str:
        """Return a natural language description of the current emotion state."""
        if self.emotion == "neutral" or self.emotion_intensity < 0.1:
            return ""
        WORD_MAP = [
            (0.9, "extremely "),
            (0.7, "very "),
            (0.5, "quite "),
            (0.3, "slightly "),
        ]
        word = ""
        for threshold, w in WORD_MAP:
            if self.emotion_intensity >= threshold:
                word = w
                break
        return f"{self.name} is {word}{self.emotion}."

    def update_emotion_from_outcome(self, outcome: str, tick: int):
        """Update emotion based on action outcome text heuristics."""
        lower = outcome.lower()
        
        # Success patterns
        if any(word in lower for word in ["success", "succeed", "you open", "you take", "you pick up", "works", "unlock", "reveal", "find", "you pick"]):
            self.set_emotion("happy", min(1.0, self.emotion_intensity + 0.2))
        # Damage / threat patterns
        elif any(word in lower for word in ["damage", "hit you", "strike", "slash", "hurt", "injure", "pain"]):
            if self.vitals["HP"] < 30:
                self.set_emotion("afraid", 0.7)
            else:
                self.set_emotion("angry", 0.5)
        # Fear / danger patterns
        elif any(word in lower for word in ["creepy", "scary", "frighten", "terrify", "horror", "scream", "shriek", "shadow", "ghost"]):
            self.set_emotion("afraid", 0.6)
        # Sad / loss patterns
        elif any(word in lower for word in ["sad", "loss", "dead", "kill", "die", "death", "grave"]):
            self.set_emotion("sad", 0.5)
        # Surprise patterns
        elif any(word in lower for word in ["sudden", "unexpected", "surprise", "startle", "shock", "appear", "appears"]):
            self.set_emotion("surprised", 0.4)
        # Disgust patterns
        elif any(word in lower for word in ["rotten", "decay", "smell", "stench", "disgust", "mold", "filth"]):
            self.set_emotion("disgusted", 0.4)
        # Frustration / failure patterns
        elif any(word in lower for word in ["fail", "can't", "cannot", "blocked", "locked", "stop", "refuse", "error"]):
            self.set_emotion("angry", 0.3)
        # Decay towards neutral over time
        else:
            if self.emotion_intensity > 0.1:
                self.emotion_intensity = max(0.0, self.emotion_intensity - 0.1)
            if self.emotion_intensity <= 0.1 and self.emotion != "neutral":
                self.emotion = "neutral"

    def register_first_meeting(self, other_name: str, tick: int) -> bool:
        """Register that this character has met *other_name* for the first time.

        Creates the relationship entry (closeness 0, no interaction bump) and
        grants an Entertainment novelty boost. Returns True only on first meet;
        no-op afterwards, so it is safe to call on every shared-area observation.

        The new record is stamped ``first_sighting: True`` so the character's
        identity stays hidden from prompt renderers for the rest of this turn
        (the first sighting is anonymized); the flag is cleared on the next
        shared-area encounter, which is when the name is revealed.
        """
        if other_name in self.relationships:
            return False
        self.relationships[other_name] = {
            "closeness": 0,
            "last_interaction_tick": tick,
            "interaction_count": 0,
            "first_sighting": True
        }
        self._grant_meeting_entertainment()
        return True

    def has_met(self, other_name: str) -> bool:
        """True when this character has met *other_name* (a relationship exists)."""
        return other_name in self.relationships

    def knows_name(self, other_name: str) -> bool:
        """True when this character has actually learned *other_name*'s name
        (heard it spoken, or read their name tag) — task-339. Recognition
        (having seen them) is NOT name knowledge."""
        rel = self.relationships.get(other_name)
        return rel is not None and not rel.get("first_sighting")

    def learn_name(self, other_name: str, tick: int) -> bool:
        """Learn another character's NAME (heard it spoken / read their name
        tag) — task-339. Registers the relationship if new and clears the
        name-unknown flag. Returns True only when this was new knowledge."""
        self.register_first_meeting(other_name, tick)
        rel = self.relationships.get(other_name)
        if rel is None:
            return False
        was_unknown = bool(rel.get("first_sighting"))
        if was_unknown:
            rel["first_sighting"] = False
        return was_unknown

    def learn_way_aspect(self, area_name: str, direction: str, aspect: str) -> None:
        """Record that this character discovered a way's hidden aspect
        ('locked', 'blocked', 'needs_force') — task-333 scene discovery."""
        key = (str(area_name), str(direction))
        self.known_way_aspects.setdefault(key, set()).add(str(aspect))

    def knows_way_aspect(self, area_name: str, direction: str, aspect: str) -> bool:
        """True when this character has discovered the given way aspect."""
        return str(aspect) in self.known_way_aspects.get(
            (str(area_name), str(direction)), ()
        )

    def unknown_display_name(self) -> str:
        """The label others see for this character before meeting them.

        Uses the explicit `unknown_name` when set, otherwise derives a
        description-based label (first sentence, leading article stripped).
        If the character has no usable description, falls back to a label
        derived from their tags (male/female/man/woman/girl/boy/animal),
        then to a generic "the stranger".
        """
        if getattr(self, "unknown_name", "").strip():
            return self.unknown_name.strip()
        tag_label = self._tag_unknown_name()
        if tag_label != "the stranger":
            return tag_label
        desc = (self.description or self.base_description or "").strip()
        if not desc:
            return self._tag_unknown_name()
        first_sentence = re.split(r"[.!?]", desc)[0].strip()
        first_sentence = re.sub(r"^(?:a|an|the)\s+", "", first_sentence, flags=re.IGNORECASE)
        if not first_sentence:
            return self._tag_unknown_name()
        # Pronoun-starting descriptions ("She stands bare and unadorned...") —
        # map to a person label instead of producing "the she stands...".
        m = re.match(r"^(she|he|they)\b", first_sentence, flags=re.IGNORECASE)
        if m:
            person = {"she": "woman", "he": "man", "they": "person"}[m.group(1).lower()]
            rest = first_sentence[m.end():].strip()
            if rest:
                return f"the {person} who {rest}".lower()
        return f"the {first_sentence.lower()}"

    def _tag_unknown_name(self) -> str:
        """Derive a stranger label from character tags when there's no
        description to build one from. e.g. `male` → "the man", `female` →
        "the woman", `girl` → "a girl", `boy` → "a boy", `animal` → "an
        animal". Falls back to "the stranger" when no tag matches."""
        tag_map = {
            "male": "the man",
            "man": "the man",
            "female": "the woman",
            "woman": "the woman",
            "girl": "a girl",
            "boy": "a boy",
            "child": "a child",
            "animal": "an animal",
        }
        tags = getattr(self, "tags", []) or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        for tag in tags:
            label = tag_map.get(str(tag).strip().lower())
            if label:
                return label
        return "the stranger"

    def _grant_meeting_entertainment(self):
        """Entertainment boost the first time a character meets someone new."""
        if "Entertainment" not in self.vitals:
            return
        try:
            from engine.traits import TraitSystem
        except ImportError:
            base_boost = 10
        else:
            base_boost = 10
            if TraitSystem.has_effect(self, "curious"):
                base_boost = int(base_boost * 1.5)
            if TraitSystem.has_effect(self, "homebody"):
                base_boost = 0
        self.vitals["Entertainment"] = min(100, self.vitals.get("Entertainment", 50) + base_boost)

    def update_relationship(self, other_name: str, tick: int, sentiment_change: int = 0):
        """Update relationship closeness with another character.
        sentiment_change: -20 to +20 per interaction. Range: -100 to +100.

        First meeting with a character grants an Entertainment novelty boost
        (mirrors the area-visit/item-discovery boosts in task-136).
        """
        if other_name not in self.relationships:
            self.relationships[other_name] = {
                "closeness": 0,
                "last_interaction_tick": tick,
                "interaction_count": 0
            }
            self._grant_meeting_entertainment()
        rel = self.relationships[other_name]
        rel["closeness"] = max(-100, min(100, rel["closeness"] + sentiment_change))
        rel["last_interaction_tick"] = tick
        rel["interaction_count"] += 1

    def get_relationship_nl(self, other_name: str) -> str:
        """Return a natural language description of the relationship."""
        rel = self.relationships.get(other_name)
        if not rel:
            return f"{self.name} has never met {other_name}."
        closeness = rel["closeness"]
        if closeness <= -75:
            desc = "mortal enemy"
        elif closeness <= -50:
            desc = "enemy"
        elif closeness <= -25:
            desc = "rival"
        elif closeness < 0:
            desc = "unfriendly"
        elif closeness == 0:
            desc = "neutral"
        elif closeness <= 25:
            desc = "acquaintance"
        elif closeness <= 50:
            desc = "friend"
        elif closeness <= 75:
            desc = "close friend"
        else:
            desc = "inseparable"
        return f"{self.name} considers {other_name} a {desc} (closeness: {closeness}/100)."

    def add_memory(self, text: str, tick: int, importance: int = 5, memory_type: str = "observation", tags=None, source: str = "auto"):
        """Add a memory entry. Importance 1-10, higher = more significant.

        tags: list[str] — optional keyword labels for targeting via trigger effects.
        source: str — provenance label (auto/manual/trigger/...).
        """
        self.memories.append({
            "id": str(uuid.uuid4())[:8],
            "text": text,
            "tick": tick,
            "timestamp": time.time(),
            "importance": max(1, min(10, importance)),
            "type": memory_type,
            "tags": list(tags) if tags else [],
            "source": source,
            "salience_override": 0,
            "suppressions": [],
        })
        if len(self.memories) > 200:
            self.memories.pop(0)

    def suppress_memory(self, tags=None, keywords: str = "", duration: int = 1, scope: str = "self") -> list:
        """Mark matching memories as inaccessible for `duration` turns.

        Returns list of suppressed memory ids.
        duration=0 means permanent until explicitly unblocked.
        """
        tags = [t.lower() for t in (tags or []) if t]
        keywords_lower = keywords.lower().strip()
        suppressed_ids = []
        for m in self.memories:
            if m.get("suppressions"):
                continue
            mem_tags = [t.lower() for t in (m.get("tags") or [])]
            tag_match = bool(tags) and all(t in mem_tags for t in tags)
            kw_match = bool(keywords_lower) and keywords_lower in m.get("text", "").lower()
            if (tags and tag_match) or (keywords_lower and kw_match) or (not tags and not keywords_lower):
                m.setdefault("suppressions", [])
                m["suppressions"].append({"until_tick": duration if duration > 0 else None, "source": scope})
                suppressed_ids.append(m.get("id"))
        return suppressed_ids

    def unblock_memory(self, tags=None, keywords: str = "", scope: str = "self") -> list:
        """Remove active suppressions from matching memories.

        Returns list of unblocked memory ids.
        """
        tags = [t.lower() for t in (tags or []) if t]
        keywords_lower = keywords.lower().strip()
        unblocked_ids = []
        for m in self.memories:
            suppressions = m.get("suppressions", [])
            if not suppressions:
                continue
            mem_tags = [t.lower() for t in (m.get("tags") or [])]
            tag_match = bool(tags) and all(t in mem_tags for t in tags)
            kw_match = bool(keywords_lower) and keywords_lower in m.get("text", "").lower()
            if (tags and tag_match) or (keywords_lower and kw_match) or (not tags and not keywords_lower):
                m["suppressions"] = [s for s in suppressions if s.get("source") != scope]
                if not m["suppressions"]:
                    unblocked_ids.append(m.get("id"))
        return unblocked_ids

    def clear_expired_suppressions(self, current_tick: int) -> None:
        """Drop suppressions whose `until_tick` has passed."""
        for m in self.memories:
            suppressions = m.get("suppressions", [])
            m["suppressions"] = [
                s for s in suppressions
                if s.get("until_tick") is None or s["until_tick"] > current_tick
            ]

    def reset_turn_state(self, current_tick: int) -> None:
        """Call at the start of each turn: reset salience overrides and clear expired suppressions."""
        for m in self.memories:
            m["salience_override"] = 0
        self.clear_expired_suppressions(current_tick)

    def get_relevant_memories(self, query: str, max_results: int = 5) -> list:
        """Keyword-based memory retrieval respecting suppressions and salience.

        Memories with an active suppression are excluded.
        Recalled memories get a reinforce bump (+1 importance, cap 10).
        """
        if not self.memories:
            return []

        import re
        query_lower = query.lower()
        query_words = set(re.sub(r'[^\w\s]', '', query_lower).split())

        scored = []
        for m in self.memories:
            if m.get("suppressions"):
                continue
            text_clean = re.sub(r'[^\w\s]', '', m.get("text", "").lower())
            text_words = set(text_clean.split())
            word_overlap = len(query_words & text_words)
            recency_boost = max(0, 1.0 - (m.get("tick", 0) / 100))
            salience = m.get("salience_override", 0)
            score = (word_overlap * 2) + (m.get("importance", 5) * 0.5) + (recency_boost * 3) + (salience * 2)
            if word_overlap > 0 or m.get("importance", 5) >= 7 or salience > 0:
                if m.get("importance", 5) < 10:
                    m["importance"] = m["importance"] + 1
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:max_results]]

    def get_memory_context_nl(self, query: str, max_results: int = 3) -> str:
        """Build a natural language context string from relevant memories."""
        mems = self.get_relevant_memories(query, max_results)
        if not mems:
            return ""
        lines = [f"=== {self.name}'s relevant memories ==="]
        for m in mems:
            lines.append(f"[Tick {m.get('tick', '?')}] {m['text']}")
        return "\n".join(lines)

    def to_dict(self):
        """Serialize player state including emotion and relationships for API responses."""
        return {
            "name": self.name,
            "exhaustion_count": getattr(self, 'exhaustion_count', 0),
            "current_area": self.current_area,
            "state": self.state,
            "conditions": list(self.conditions),
            "condition_instances": {
                cid: [dict(inst) for inst in instances]
                for cid, instances in self.conditions.items()
            },
            "vitals": dict(self.vitals),
            "decay_rates": dict(self.decay_rates),
            "stats": dict(self.stats),
            "skills": dict(self.skills),
            "inventory": [],
            "personality": self.personality,
            "description": getattr(self, 'description', ''),
            "base_description": getattr(self, 'base_description', ''),
            "unknown_name": getattr(self, 'unknown_name', ''),
            "simple_npc": self.simple_npc,
            "autonomy": self.autonomy,
            "npc_behavior": self.npc_behavior,
            "npc_action_interval": self.npc_action_interval,
            "emotion": {
                "current": self.emotion,
                "intensity": round(self.emotion_intensity, 2),
                "description": self.get_emotion_nl()
            },
            "emotions": dict(self.emotions_map()),
            "equipped": dict(self.equipped),
            "activity": self.activity,
            "relationships": {
                name: {
                    "closeness": data["closeness"],
                    "interaction_count": data["interaction_count"]
                }
                for name, data in self.relationships.items()
            } if self.relationships else {},
            "traits": dict(self.traits),
            "tags": list(self.tags),
            "interest_tags": list(self.interest_tags),
            "visited_areas": list(self.visited_areas),
            "discovered_items": list(self.discovered_items),
            "patrol_route": list(getattr(self, "patrol_route", [])),
            "patrol_index": getattr(self, "patrol_index", 0),
        }