# engine/traits.py
"""Trait system — registered trait definitions and runtime processing.

Each player has a ``traits`` dict mapping ``trait_id → param_value``.
The param_value is ``True`` for boolean traits, a string for parameterized
traits (e.g. ``"allergic": "pollen"``), or a number.

``TraitSystem`` looks up the definition from ``TRAIT_DEFINITIONS`` and
resolves the effects at runtime so engine code never hard-codes trait
names outside this module.
"""

from typing import Any, Dict, List, Optional, Set

# ──────────────────────────────────────────────────────────────
# Effect keys recognised by the engine
# ──────────────────────────────────────────────────────────────

#: additive modifiers applied in ``apply_action``
#: ``{"energy": -1, "time": 1}``
ACTION_COST_MOD = "action_cost_mod"

#: multiplied into baseline decay in ``tick_turn``
#: ``{"Hunger": 2.0}``
VITAL_MULTIPLIER = "vital_multiplier"

#: flat per-tick adjustment applied in ``tick_turn``
#: ``{"Energy": -1}``
VITAL_MOD_PER_TICK = "vital_mod_per_tick"

#: boolean — player can see in total darkness
DARK_VISION = "dark_vision"

#: boolean — horror monster, exempt from vitals decay
IS_SLASHER = "is_slasher"

#: boolean — threat marker for AI: considers this character a danger to others
HOSTILE = "hostile"

#: tag string — when near a matching tag, apply a condition
ALLERGIC_TO = "allergic_to"

#: list of conditions this trait grants immunity to
IMMUNE_TO_CONDITION = "immune_to_condition"

#: sense to block: "sight" or "hearing"
BLOCK_SENSE = "block_sense"

#: slot to disable: "hand_left", "hand_right" etc.
DISABLE_SLOT = "disable_slot"

#: multiplier on natural HP regen (default 1/tick when conditions met)
HP_REGEN_MULTIPLIER = "hp_regen_multiplier"

#: dict with ``peak_hour`` (0-23) and ``off_peak_mod`` (energy per tick)
ENERGY_CURVE = "energy_curve"

#: per-tick energy drain when more than N others are in the same area
GROUP_ENERGY_DRAIN = "group_energy_drain"

#: per-tick social gain from being near others
SOCIAL_GAIN = "social_gain"

#: boolean — skip entertainment decay entirely
NO_ENTERTAINMENT_DECAY = "no_entertainment_decay"

#: minimum noise level required to wake (1=whisper, 5=scream)
WAKE_THRESHOLD = "wake_threshold"

# ──────────────────────────────────────────────────────────────
# Trait schema v2 effect keys (Phase 2)
# ──────────────────────────────────────────────────────────────

#: additive per-skill bonuses on skill checks: {"Perception": 2} or a flat int
SKILL_CHECK_MOD = "skill_check_mod"

#: additive bonus on saving throws: a flat int, or {"WIS": 2} per stat
SAVE_BONUS = "save_bonus"

#: additive movement-cost modifiers (moves/dashes): {"energy": -1, "time": 1}
MOVE_COST_MOD = "move_cost_mod"

#: multiplier on the player's carry-weight capacity (default 1.0)
CARRY_CAPACITY_MOD = "carry_capacity_mod"

# ──────────────────────────────────────────────────────────────
# Trait definitions
# ──────────────────────────────────────────────────────────────

TRAIT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "glutton": {
        "name": "Glutton",
        "description": "Hunger decays twice as fast.",
        "category": "physical",
        "params": None,
        "effects": {VITAL_MULTIPLIER: {"Hunger": 2.0}},
    },
    "cleanfreak": {
        "name": "Clean Freak",
        "description": "Hygiene decays faster.",
        "category": "physical",
        "params": None,
        "effects": {VITAL_MULTIPLIER: {"Hygiene": 1.5}},
    },
    "night_owl": {
        "name": "Night Owl",
        "description": "Energy curve shifted to night hours. Lose more energy during the day.",
        "category": "physical",
        "params": None,
        "effects": {ENERGY_CURVE: {"peak_hour": 22, "off_peak_mod": -2}},
        "conflicts": ["morning_person"],
    },
    "morning_person": {
        "name": "Morning Person",
        "description": "Energy curve shifted to morning hours. Lose more energy at night.",
        "category": "physical",
        "params": None,
        "effects": {ENERGY_CURVE: {"peak_hour": 6, "off_peak_mod": -2}},
        "conflicts": ["night_owl"],
    },
    "fast_healer": {
        "name": "Fast Healer",
        "description": "Natural HP regeneration is doubled.",
        "category": "physical",
        "params": None,
        "effects": {HP_REGEN_MULTIPLIER: 2.0},
        "conflicts": ["slow_healer"],
    },
    "slow_healer": {
        "name": "Slow Healer",
        "description": "Natural HP regeneration is halved.",
        "category": "physical",
        "params": None,
        "effects": {HP_REGEN_MULTIPLIER: 0.5},
        "conflicts": ["fast_healer"],
    },
    "one_armed": {
        "name": "One-Armed",
        "description": "One hand slot is disabled.",
        "category": "physical",
        "params": None,
        "effects": {DISABLE_SLOT: "hand_right"},
    },
    "small_bladder": {
        "name": "Small Bladder",
        "description": "Bladder decays faster.",
        "category": "physical",
        "params": None,
        "effects": {VITAL_MULTIPLIER: {"Bladder": 1.5}},
    },
    "big_bladder": {
        "name": "Big Bladder",
        "description": "Bladder decays slower.",
        "category": "physical",
        "params": None,
        "effects": {VITAL_MULTIPLIER: {"Bladder": 0.5}},
    },
    "blind": {
        "name": "Blind",
        "description": "Cannot see. Perception checks auto-fail. Narrate without sight.",
        "category": "physical",
        "params": None,
        "effects": {BLOCK_SENSE: "sight"},
        "grants_conditions": ["blind"],
    },
    "deaf": {
        "name": "Deaf",
        "description": "Cannot hear. Narrate without audio cues.",
        "category": "physical",
        "params": None,
        "effects": {BLOCK_SENSE: "hearing"},
        "grants_conditions": ["deaf"],
    },
    "introvert": {
        "name": "Introvert",
        "description": "Energy drains faster when in groups.",
        "category": "mental",
        "params": None,
        "effects": {GROUP_ENERGY_DRAIN: -2, SOCIAL_GAIN: 0},
        "conflicts": ["extrovert"],
    },
    "extrovert": {
        "name": "Extrovert",
        "description": "Gains energy from socialising.",
        "category": "mental",
        "params": None,
        "effects": {GROUP_ENERGY_DRAIN: 0, SOCIAL_GAIN: 2},
        "conflicts": ["introvert"],
    },
    "loner": {
        "name": "Loner",
        "description": "Solitude recharges you. Being alone restores your social well-being.",
        "category": "mental",
        "params": None,
        "effects": {GROUP_ENERGY_DRAIN: 0, SOCIAL_GAIN: 0},
        "conflicts": ["extrovert", "chatty"],
    },
    "chatty": {
        "name": "Chatty",
        "description": "You talk easily. Conversations come naturally and leave you feeling connected.",
        "category": "mental",
        "params": None,
        "effects": {SOCIAL_GAIN: 1},
        "conflicts": ["loner", "mute"],
    },
    # ── Mature traits (task-213) — hidden from pickers unless mature_content ──
    # ``mature: True`` marks them for UI filtering. ``body_part_multipliers``
    # rides inside the standard ``effects`` dict and is consumed by the
    # pleasure pipeline (task-212).
    "wired_differently": {
        "name": "Wired Differently",
        "description": "Your body's map of pleasure is unusual — some places overwhelm, others barely register.",
        "category": "physical",
        "params": None,
        "effects": {"body_part_multipliers": {"nipple_left": 3.0, "nipple_right": 3.0, "genitals": 0.1}},
        "mature": True,
        "conflicts": [],
    },
    "quick_recovery": {
        "name": "Quick Recovery",
        "description": "Overstimulation passes quickly — you bounce back fast.",
        "category": "physical",
        "params": None,
        "effects": {"quick_recovery": True},
        "mature": True,
        "conflicts": [],
    },
    "sensory_memory": {
        "name": "Sensory Memory",
        "description": "Your skin remembers. Sensitivity lingers long after a release.",
        "category": "physical",
        "params": None,
        "effects": {"sensory_memory": True},
        "mature": True,
        "conflicts": [],
    },
    "sex_addict": {
        "name": "Sex Addict",
        "description": "When the need goes unmet, nothing else holds your interest.",
        "category": "mental",
        "params": None,
        "effects": {"sex_addict": True},
        "mature": True,
        "conflicts": [],
    },
    "attention_seeker": {
        "name": "Attention Seeker",
        "description": "Being looked at lights you up. Eyes on you are their own reward.",
        "category": "social",
        "params": None,
        "effects": {"attention_seeker": True},
        "mature": True,
        "conflicts": [],
    },
    "exhibitionist": {
        "name": "Exhibitionist",
        "description": "Being seen at your most vulnerable thrills you.",
        "category": "social",
        "params": None,
        "effects": {"exhibitionist": True},
        "mature": True,
        "conflicts": [],
    },
    "single_track": {
        "name": "Single Track",
        "description": "One path to release and one only — anything else just frustrates.",
        "category": "physical",
        "params": None,
        "effects": {"single_track": True},
        "mature": True,
        "conflicts": [],
    },
    "apathetic": {
        "name": "Apathetic",
        "description": "No entertainment decay. Emotional intensity drifts to neutral faster.",
        "category": "mental",
        "params": None,
        "effects": {NO_ENTERTAINMENT_DECAY: True},
    },
    "allergic": {
        "name": "Allergic",
        "description": "Takes damage or gains a condition when near items/areas with a matching tag.",
        "category": "physical",
        "params": {"type": "string", "label": "Allergen tag", "placeholder": "e.g. pollen, dust"},
        "effects": {ALLERGIC_TO: None},  # value filled from player.traits[trait_id]
    },
    "light_sleeper": {
        "name": "Light Sleeper",
        "description": "Wakes easily from loud noises.",
        "category": "physical",
        "params": None,
        "effects": {WAKE_THRESHOLD: 3},
        "conflicts": ["heavy_sleeper"],
    },
    "heavy_sleeper": {
        "name": "Heavy Sleeper",
        "description": "Hard to wake from noise.",
        "category": "physical",
        "params": None,
        "effects": {WAKE_THRESHOLD: 1},
        "conflicts": ["light_sleeper"],
    },
    "immortal": {
        "name": "Immortal",
        "description": "Cannot die. HP stops at 1.",
        "category": "physical",
        "params": None,
        "effects": {IMMUNE_TO_CONDITION: "dead"},
    },
    "dark_vision": {
        "name": "Dark Vision",
        "description": "Can see in complete darkness.",
        "category": "physical",
        "params": None,
        "effects": {DARK_VISION: True},
    },
    "darkvision": {
        "name": "Dark Vision (Alternate)",
        "description": "Can see in complete darkness. Alternate spelling of dark_vision.",
        "category": "physical",
        "params": None,
        "effects": {DARK_VISION: True},
    },
    "slasher": {
        "name": "Slasher",
        "description": "Horror monster — exempt from vital decay and can see in the dark.",
        "category": "physical",
        "params": None,
        "effects": {IS_SLASHER: True, DARK_VISION: True},
    },
    "is_slasher": {
        "name": "Is Slasher (Alternate)",
        "description": "Horror monster flag. Alternate spelling of slasher.",
        "category": "physical",
        "params": None,
        "effects": {IS_SLASHER: True, DARK_VISION: True},
    },
    "hostile": {
        "name": "Hostile",
        "description": "Threat marker — other characters should consider this person dangerous and flee or fight.",
        "category": "social",
        "params": None,
        "effects": {HOSTILE: True},
    },
    "hardy": {
        "name": "Hardy",
        "description": "Tough and resilient. Action costs are reduced.",
        "category": "physical",
        "params": None,
        "effects": {ACTION_COST_MOD: {"energy": -1}},
    },
    # ── Exploration / novelty traits (task-136) ──
    "curious": {
        "name": "Curious",
        "description": "+50% Entertainment from new places and things. More likely to examine items and explore exits.",
        "category": "exploration",
        "params": None,
        "effects": {"curious": True},
    },
    "adventurous": {
        "name": "Adventurous",
        "description": "Entertainment doesn't decay in unfamiliar areas. More willing to take risks and go somewhere unknown.",
        "category": "exploration",
        "params": None,
        "effects": {"adventurous": True, NO_ENTERTAINMENT_DECAY: True},
    },
    "homebody": {
        "name": "Homebody",
        "description": "No Entertainment boost from new places or things; slower decay in home area.",
        "category": "exploration",
        "params": None,
        "effects": {"homebody": True},
    },
    "wanderlust": {
        "name": "Wanderlust",
        "description": "Gains Entertainment from moving between areas even if visited before. Prefers to keep moving.",
        "category": "exploration",
        "params": None,
        "effects": {"wanderlust": True},
    },
    "impatient": {
        "name": "Impatient",
        "description": "Faster Entertainment decay when inactive. Acts before considering consequences.",
        "category": "exploration",
        "params": None,
        "effects": {"impatient": True},
    },
    "patient": {
        "name": "Patient",
        "description": "Slower Entertainment decay; tolerates repetitive activities longer.",
        "category": "exploration",
        "params": None,
        "effects": {"patient": True},
    },
    # ── Phase 2 — trait schema v2 example traits ──
    "paranoid": {
        "name": "Paranoid",
        "description": "Permanently frightened — trusts no one and watches everything for threats.",
        "category": "mental",
        "params": None,
        "effects": {},
        "behavior_prompt": "You trust no one. Watch everyone and everything for threats — assume hidden motives.",
        "grants_conditions": [{"condition": "frightened"}],
    },
    "chronically_ill": {
        "name": "Chronically Ill",
        "description": "A permanent, mild sickness — hunger and thirst worsen faster.",
        "category": "physical",
        "params": None,
        "effects": {},
        "grants_conditions": [{"condition": "sick", "periodic": {"Hunger": -1, "Thirst": -1}}],
    },
    "narcoleptic": {
        "name": "Narcoleptic",
        "description": "Waves of exhaustion come and go.",
        "category": "physical",
        "params": None,
        "effects": {},
        "grants_conditions": [{"condition": "exhausted", "duration": 3}],
    },
    "sprinter": {
        "name": "Sprinter",
        "description": "Movement costs 1 less energy.",
        "category": "physical",
        "params": None,
        "effects": {MOVE_COST_MOD: {"energy": -1}},
    },
    "strong_backed": {
        "name": "Strong-Backed",
        "description": "Carries twice the weight.",
        "category": "physical",
        "params": None,
        "effects": {CARRY_CAPACITY_MOD: 2.0},
    },
    "sharp_eyed": {
        "name": "Sharp-Eyed",
        "description": "+2 on Perception checks.",
        "category": "mental",
        "params": None,
        "effects": {SKILL_CHECK_MOD: {"Perception": 2}},
    },
    "iron_will": {
        "name": "Iron Will",
        "description": "+2 on WIS saves.",
        "category": "mental",
        "params": None,
        "effects": {SAVE_BONUS: {"WIS": 2}},
    },
    "jittery": {
        "name": "Jittery",
        "description": "-1 on all skill checks — nervous hands.",
        "category": "mental",
        "params": None,
        "effects": {SKILL_CHECK_MOD: -1},
    },
    # ── Phase 3 — save_on event-hook example traits ──
    "claustrophobic": {
        "name": "Claustrophobic",
        "description": "Tight, enclosed spaces make you panic.",
        "category": "mental",
        "params": None,
        "effects": {},
        "behavior_prompt": "You feel your chest tighten in small, enclosed spaces. You need open air and an escape route nearby.",
        "save_on": [
            {"event": "crawl_tight_way", "source_type": "way", "stat": "WIS", "dc": 12,
             "on_fail": [{"condition": "frightened", "duration": 3},
                         {"vital": "Sanity", "amount": -10}],
             "fail_message": "The walls close in around you. Your heart pounds."},
        ],
    },
    "acrophobic": {
        "name": "Acrophobic",
        "description": "Heights terrify you.",
        "category": "mental",
        "params": None,
        "effects": {},
        "save_on": [
            {"event": "climb_way", "source_type": "way", "stat": "WIS", "dc": 12,
             "on_fail": [{"condition": "frightened", "duration": 3},
                         {"vital": "Sanity", "amount": -8}],
             "fail_message": "Your stomach lurches at the height. You freeze for a moment."},
            {"event": "jump_way", "source_type": "way", "stat": "WIS", "dc": 12,
             "on_fail": [{"condition": "frightened", "duration": 3},
                         {"vital": "Sanity", "amount": -8}],
             "fail_message": "The gap below makes your head spin."},
        ],
    },
    "hemophobic": {
        "name": "Hemophobic",
        "description": "The sight of blood or death makes you queasy.",
        "category": "mental",
        "params": None,
        "effects": {},
        "save_on": [
            {"event": "see_item", "source_type": "item", "item_tags": ["blood", "corpse"],
             "stat": "WIS", "dc": 12,
             "on_fail": [{"condition": "frightened", "duration": 3, "source_type": "item"},
                         {"vital": "Sanity", "amount": -5}],
             "fail_message": "The sight of it makes your stomach turn."},
        ],
    },
    "agoraphobic": {
        "name": "Agoraphobic",
        "description": "Wide-open spaces set you on edge.",
        "category": "mental",
        "params": None,
        "effects": {},
        "conflicts": ["claustrophobic"],
        "save_on": [
            {"event": "enter_area", "source_type": "area", "area_tags": ["open"],
             "stat": "WIS", "dc": 12,
             "on_fail": [{"condition": "frightened", "duration": 3},
                         {"vital": "Sanity", "amount": -10}],
             "fail_message": "The open space stretches out too far. You feel exposed."},
        ],
    },
    "nyctophobic": {
        "name": "Nyctophobic",
        "description": "Darkness and solitude terrify you.",
        "category": "mental",
        "params": None,
        "effects": {},
        "save_on": [
            {"event": "alone_in_dark", "stat": "WIS", "dc": 12,
             "on_fail": [{"condition": "frightened", "duration": 2},
                         {"vital": "Sanity", "amount": -5}],
             "fail_message": "The dark presses in around you. You aren't alone."},
        ],
    },
    "cowardly": {
        "name": "Cowardly",
        "description": "Getting hurt shakes your nerve.",
        "category": "mental",
        "params": None,
        "effects": {},
        "save_on": [
            {"event": "takes_damage", "source_type": "character", "stat": "WIS", "dc": 12,
             "on_fail": [{"condition": "frightened", "duration": 2}],
             "fail_message": "Pain flashes through you and your courage drains."},
        ],
    },
    # ── Phase 4 — acquired (dynamic) traits ──
    "scarred": {
        "name": "Scarred",
        "description": "Bears the marks of a brush with death.",
        "category": "mental",
        "params": None,
        "effects": {"scarred": True},
        "behavior_prompt": "You've been close to death before. You take dangers seriously — and you know what pain costs.",
    },
    "frail": {
        "name": "Frail",
        "description": "Worn thin by hunger. Needs more food to stay strong.",
        "category": "physical",
        "params": None,
        "effects": {VITAL_MULTIPLIER: {"Hunger": 1.5}},
    },
}

# ──────────────────────────────────────────────────────────────
# Data-driven trait catalog
# ──────────────────────────────────────────────────────────────

_TRAIT_BASE = {
    "name": "", "description": "", "category": "custom", "params": None,
    "effects": {}, "conflicts": [], "behavior_prompt": "",
    "grants_conditions": [], "save_on": [], "immune_to_condition": [],
}


def _trait_library_dir():
    import os as _os
    return _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'data', 'library', 'traits')


def _trait_is_active(defn: dict) -> bool:
    return bool(defn.get("effects") or defn.get("grants_conditions") or defn.get("save_on"))


def _merge_trait_definition(tid: str, entry: dict):
    base = TRAIT_DEFINITIONS[tid] if tid in TRAIT_DEFINITIONS else dict(_TRAIT_BASE)
    merged = base
    merged.update(entry)
    merged.setdefault('name', merged.get('name') or tid.title().replace('_', ' '))
    TRAIT_DEFINITIONS[tid] = merged


def _load_trait_library():
    """Merge data-driven trait definitions from data/library/traits/*.json.

    Runs at import time so TraitSystem reads the post-load catalog. A file that
    names an existing engine trait merges over the hardcoded fallback (so a
    partial/truncated file can't wipe behavior). A brand-new id is accepted only
    if it declares real effects / grants_conditions / save_on — UI-only marker
    traits (e.g. size_*) stay out of the engine catalog.
    """
    import json as _json
    import os as _os
    trait_dir = _trait_library_dir()
    if not _os.path.isdir(trait_dir):
        return
    for fname in sorted(_os.listdir(trait_dir)):
        if not fname.endswith('.json'):
            continue
        tid = fname[:-5]
        try:
            with open(_os.path.join(trait_dir, fname), 'r', encoding='utf-8-sig') as f:
                entry = _json.load(f)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        if tid in TRAIT_DEFINITIONS or _trait_is_active(entry):
            _merge_trait_definition(tid, entry)


_load_trait_library()


def seed_trait_library():
    """Migrate data/library/traits/*.json to the full engine trait schema.

    Rewrites any file that is missing the active fields the code catalog defines
    (the old params-only format) to the canonical full definition. Leaves
    already-canonical and user-edited files, and UI-only marker traits (size_*),
    untouched.
    """
    import json as _json
    import os as _os
    trait_dir = _trait_library_dir()
    try:
        _os.makedirs(trait_dir, exist_ok=True)
    except OSError:
        return
    for tid, definition in TRAIT_DEFINITIONS.items():
        path = _os.path.join(trait_dir, f"{tid}.json")
        if _os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    existing = _json.load(f)
            except Exception:
                existing = {}
            if _trait_is_active(existing):
                continue
        try:
            with open(path, 'w', encoding='utf-8') as f:
                _json.dump(definition, f, indent=2, ensure_ascii=False)
        except OSError:
            continue


# ──────────────────────────────────────────────────────────────
# TraitSystem
# ──────────────────────────────────────────────────────────────

class TraitSystem:
    """Resolves trait definitions into engine-readable effect values.

    Usage::

        ts = TraitSystem()
        ts.has_effect(player, "dark_vision")          # True/False
        ts.get_effects(player, "action_cost_mod")     # [{"energy": -1}]
        ts.get_vital_multipliers(player)               # {"Hunger": 2.0, ...}
        ts.process_tick_effects(player, tick, area_node)  # log entries
    """

    @staticmethod
    def get_definition(trait_id: str) -> Optional[Dict[str, Any]]:
        """Return the trait definition dict, or None if unknown."""
        return TRAIT_DEFINITIONS.get(trait_id)

    @staticmethod
    def has_trait(player, trait_id: str) -> bool:
        """Check if a player has a specific trait by ID."""
        return trait_id in (player.traits or {})

    @staticmethod
    def get_trait_param(player, trait_id: str):
        """Return the parameter value for a parameterized trait."""
        return (player.traits or {}).get(trait_id, True)

    # ── Effect queries ────────────────────────────────────────

    @staticmethod
    def has_effect(player, effect_key: str) -> bool:
        """Check if any of the player's traits grant a specific effect."""
        traits = player.traits or {}
        for trait_id in traits:
            if trait_id not in TRAIT_DEFINITIONS:
                continue
            effects = TRAIT_DEFINITIONS[trait_id].get("effects", {})
            if effect_key in effects:
                val = effects[effect_key]
                if val is not None:
                    return bool(val)
                param = traits.get(trait_id)
                if param:
                    return True
        return False

    @staticmethod
    def get_effects(player, effect_key: str) -> List[Any]:
        """Collect all values for a given effect key from the player's traits.

        Returns a list of effect values (one per trait that provides that effect).
        For parameterized traits the player's param value is substituted.
        """
        results = []
        traits = player.traits or {}
        for trait_id in traits:
            if trait_id not in TRAIT_DEFINITIONS:
                continue
            effects = TRAIT_DEFINITIONS[trait_id].get("effects", {})
            if effect_key not in effects:
                continue
            val = effects[effect_key]
            if val is None:
                val = traits[trait_id]
            results.append(val)
        return results

    @staticmethod
    def get_first_effect(player, effect_key: str):
        """Return the *first* effect value for a given key (or None)."""
        results = TraitSystem.get_effects(player, effect_key)
        return results[0] if results else None

    # ── Convenience helpers ───────────────────────────────────

    @staticmethod
    def get_vital_multipliers(player) -> Dict[str, float]:
        """Merge all vital_multiplier effects into a single dict."""
        merged: Dict[str, float] = {}
        for m in TraitSystem.get_effects(player, VITAL_MULTIPLIER):
            for vital, mult in m.items():
                merged[vital] = merged.get(vital, 1.0) * mult
        return merged

    @staticmethod
    def get_action_cost_mods(player) -> Dict[str, int]:
        """Merge all action_cost_mod effects (modifiers are additive)."""
        merged: Dict[str, int] = {}
        for m in TraitSystem.get_effects(player, ACTION_COST_MOD):
            for stat, mod in m.items():
                merged[stat] = merged.get(stat, 0) + mod
        return merged

    @staticmethod
    def get_sense_blocked(player) -> Optional[str]:
        """Return which sense is blocked (if any): 'sight' or 'hearing'."""
        return TraitSystem.get_first_effect(player, BLOCK_SENSE)

    @staticmethod
    def get_disabled_slots(player) -> Set[str]:
        """Return set of equipment slot names that are disabled."""
        return set(TraitSystem.get_effects(player, DISABLE_SLOT))

    @staticmethod
    def get_allergen_tag(player) -> Optional[str]:
        """Return the tag this player is allergic to (if any)."""
        return TraitSystem.get_first_effect(player, ALLERGIC_TO)

    @staticmethod
    def get_energy_curve(player) -> Optional[Dict]:
        """Return energy curve config, or None."""
        return TraitSystem.get_first_effect(player, ENERGY_CURVE)

    # ── Trait schema v2 helpers ───────────────────────────────

    @staticmethod
    def get_skill_check_mods(player) -> Dict[str, int]:
        """Merge all skill_check_mod effects.

        Per-skill dicts add together; a flat int applies to every skill
        (keyed ``"*"``).
        """
        merged: Dict[str, int] = {}
        for m in TraitSystem.get_effects(player, SKILL_CHECK_MOD):
            if isinstance(m, dict):
                for skill, mod in m.items():
                    merged[skill] = merged.get(skill, 0) + int(mod)
            else:
                merged["*"] = merged.get("*", 0) + int(m)
        return merged

    @staticmethod
    def get_save_bonus(player) -> tuple:
        """Return ``(flat_bonus, {stat: bonus})`` from save_bonus effects."""
        flat = 0
        per_stat: Dict[str, int] = {}
        for m in TraitSystem.get_effects(player, SAVE_BONUS):
            if isinstance(m, dict):
                for stat, bonus in m.items():
                    per_stat[stat] = per_stat.get(stat, 0) + int(bonus)
            else:
                flat += int(m)
        return flat, per_stat

    @staticmethod
    def get_move_cost_mods(player) -> Dict[str, int]:
        """Merge all move_cost_mod effects (additive, like action_cost_mod)."""
        merged: Dict[str, int] = {}
        for m in TraitSystem.get_effects(player, MOVE_COST_MOD):
            for stat, mod in m.items():
                merged[stat] = merged.get(stat, 0) + int(mod)
        return merged

    @staticmethod
    def get_carry_capacity_mod(player) -> float:
        """Return the combined carry-capacity multiplier (default 1.0)."""
        result = 1.0
        for m in TraitSystem.get_effects(player, CARRY_CAPACITY_MOD):
            result *= float(m)
        return result

    @staticmethod
    def get_save_on_entries(player, event: str, context: Optional[dict] = None) -> List[dict]:
        """All ``save_on`` entries on the player's traits matching *event*.

        Entries may filter on ``area_tags`` / ``item_tags`` — the entry only
        matches when one of its tags is present in the context tag lists — and
        on ``source_type`` (way/area/item/character), matching only events that
        originate from that kind of source (see_item = "item",
        takes_damage from combat = "character", crawl/climb/jump = "way",
        enter_area / loud_noise = "area").
        """
        context = context or {}
        entries = []
        for trait_id in (player.traits or {}):
            definition = TRAIT_DEFINITIONS.get(trait_id, {})
            for entry in definition.get("save_on", []):
                if entry.get("event") != event:
                    continue
                source_type = entry.get("source_type")
                if source_type and context.get("source_type") != source_type:
                    continue
                area_tags = entry.get("area_tags") or []
                if area_tags and not any(
                    t in context.get("area_tags", []) for t in area_tags
                ):
                    continue
                item_tags = entry.get("item_tags") or []
                if item_tags and not any(
                    t in context.get("item_tags", []) for t in item_tags
                ):
                    continue
                entries.append(entry)
        return entries

    @staticmethod
    def conflicting_traits(player, trait_id: str) -> List[str]:
        """Traits the player currently has that *conflict* with *trait_id*."""
        conflicts = set(TRAIT_DEFINITIONS.get(trait_id, {}).get("conflicts", []))
        return [tid for tid in (player.traits or {}) if tid in conflicts]

    @staticmethod
    def sync_granted_conditions(player) -> None:
        """Reconcile conditions granted by the player's traits.

        Every trait with ``grants_conditions`` keeps its granted condition
        active (added with ``source: "trait:<id>"`` if missing); trait-sourced
        conditions whose trait is gone are dropped. Self-healing — call on
        trait add/remove and once per turn so any path that mutates
        ``player.traits`` reconciles within a tick.
        """
        expected: Dict[str, List[str]] = {}
        for trait_id in (player.traits or {}):
            definition = TRAIT_DEFINITIONS.get(trait_id, {})
            for grant in definition.get("grants_conditions", []):
                if isinstance(grant, str):
                    cid = grant
                elif isinstance(grant, dict):
                    cid = grant.get("condition")
                else:
                    continue
                if cid:
                    expected.setdefault(cid, []).append(trait_id)

        for cid, trait_ids in expected.items():
            if not player.has_condition(cid):
                params = {}
                for trait_id in trait_ids:
                    definition = TRAIT_DEFINITIONS.get(trait_id, {})
                    for grant in definition.get("grants_conditions", []):
                        if isinstance(grant, dict) and grant.get("condition") == cid:
                            params = {k: v for k, v in grant.items() if k != "condition"}
                            break
                player.add_condition(cid, source=f"trait:{trait_ids[0]}", **params)

        for cid, instances in list(player.conditions.items()):
            keep = []
            changed = False
            for inst in instances:
                source = inst.get("source")
                if isinstance(source, str) and source.startswith("trait:"):
                    trait_id = source.split(":", 1)[1]
                    if trait_id not in expected.get(cid, []):
                        changed = True
                        continue
                keep.append(inst)
            if changed:
                if keep:
                    player.conditions[cid] = keep
                else:
                    player.conditions.pop(cid, None)
        if not player.conditions:
            player.conditions["awake"] = [{"duration": None, "source": None, "level": 0}]

    @staticmethod
    def check_scripted_acquisitions(player) -> List[str]:
        """Grant acquired traits from life events (Phase 4).

        - Near-death (HP at/below 10% and still alive) → ``scarred``
        - Starvation (Hunger at 0) → ``frail``
        - Long confinement (5+ consecutive ticks restrained/grappled) → ``claustrophobic``

        Returns the ids of newly gained traits. Called once per turn per player;
        acquisitions are one-way (a healed phobia is removed via the
        ``remove_trait`` trigger effect).
        """
        gained = []
        if player.traits is None:
            player.traits = {}
        traits = player.traits
        vitals = player.vitals or {}
        if "scarred" not in traits:
            hp = vitals.get("HP", 100)
            max_hp = vitals.get("Max_HP", 100)
            if 0 < hp <= max(1, int(max_hp * 0.1)):
                traits["scarred"] = True
                gained.append("scarred")
        if "frail" not in traits:
            # Hunger is a drive (task-337): maxed out = starving
            if vitals.get("Hunger", 0) >= 100:
                traits["frail"] = True
                gained.append("frail")
        if "claustrophobic" not in traits:
            confined = player.has_condition("restrained") or player.has_condition("grappled")
            if confined:
                player._confinement_ticks = getattr(player, "_confinement_ticks", 0) + 1
                if player._confinement_ticks >= 5:
                    traits["claustrophobic"] = True
                    gained.append("claustrophobic")
            else:
                player._confinement_ticks = 0
        return gained

    # ── Per-tick processing ───────────────────────────────────

    @staticmethod
    def process_tick_effects(player, tick: int, area_node=None) -> List[str]:
        """Apply per-tick trait effects to a player.

        Returns a list of log entry strings.
        """
        logs = []
        traits = player.traits or {}
        if not traits:
            return logs

        # Vital multipliers are applied in tick_turn via the decay rate system.
        # This method handles effects that aren't multiplier-based.

        # ── Allergic reaction ──────────────────────────────────
        allergen = TraitSystem.get_allergen_tag(player)
        if allergen and area_node:
            area_env = area_node.properties.get("environment", {})
            area_tags = area_node.properties.get("tags", [])
            item_tags = _collect_item_tags_in_area(area_node)
            if allergen in area_env.get("air", "") or allergen in area_tags or allergen in item_tags:
                player.vitals["HP"] = max(0, player.vitals.get("HP", 100) - 3)
                logs.append(f"[{player.name}] Allergic reaction to {allergen}! -3 HP.")

        # ── Energy curve (night_owl / morning_person) ─────────
        curve = TraitSystem.get_energy_curve(player)
        if curve:
            peak = curve.get("peak_hour", 12)
            off_mod = curve.get("off_peak_mod", -2)
            current_hour = (tick // 60) % 24  # approximate
            if abs(current_hour - peak) > 4:
                player.vitals["Energy"] = max(0, player.vitals.get("Energy", 50) + off_mod)

        return logs

    @staticmethod
    def get_hp_regen_multiplier(player) -> float:
        """Return the combined HP regen multiplier (default 1.0)."""
        mults = TraitSystem.get_effects(player, HP_REGEN_MULTIPLIER)
        result = 1.0
        for m in mults:
            result *= m
        return result

    @staticmethod
    def is_immune_to_condition(player, condition: str) -> bool:
        """Check if a player is immune to a given condition."""
        for immune in TraitSystem.get_effects(player, IMMUNE_TO_CONDITION):
            if immune == condition:
                return True
        return False


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _collect_item_tags_in_area(area_node) -> Set[str]:
    """Gather all tags from items located in a area node.
    Placeholder — real implementation would query graph edges.
    """
    tags: Set[str] = set()
    items = area_node.properties.get("items", [])
    for item in items:
        if isinstance(item, dict):
            tags.update(item.get("tags", []))
    return tags
