"""Runtime engine constants — the user-facing "Engine Config" menu.

Task-304: centralize the constants that previously needed a code edit to tune
(sound propagation, heat propagation, light spill) behind a single editable
JSON file, surfaced in the Settings → Engine Config tab.

Design:
  - ``DEFAULTS`` is the source of truth for the current values.
  - ``data/engine_config.json`` (optional) holds overrides on top of the
    defaults; an empty/missing file means "use the stock values".
  - Engine modules read tunables at call time via ``config.get(key)`` instead
    of bare literals, but keep their own module-level constants as the natural
    fallback so existing tests and imports behave unless an override is set.
  - ``RuntimeConfig.save(values)`` merges overrides and writes the JSON file.
    The consuming engine modules read config live, so a saved value takes
    effect on the next call with no restart.

The JSON schema is a flat ``{key: value}`` map. Keys namespaced by domain:
  - ``sound.speech_*`` / ``sound.way_*`` / ``sound.noise_*``
  - ``heat.base_rate`` / ``heat.max_delta``
  - ``light.spill_factor``
Unknown keys in the file are ignored, so pruning an old key never crashes.
"""

from __future__ import annotations

import json
import logging
import os

from typing import Optional

logger = logging.getLogger(__name__)

#: Default tunable values, keyed by dotted name. The engine modules also carry
#: their own defaults; these mirror them so config.get() can back a value
#: without the consumer needing to know about the store.
DEFAULTS: dict = {
    # engine/sound.py
    "sound.speech_whisper": 0,
    "sound.speech_normal": 1,
    "sound.speech_shout": 2,
    "sound.speech_scream": 3,
    "sound.way_open": 0.5,
    "sound.way_closed": 1,
    "sound.way_locked": 1,
    "sound.way_blocked": 1,
    "sound.way_hidden": 2,
    "sound.way_see_through": 0.75,
    "sound.noise_silent": 0,
    "sound.noise_quiet": 0,
    "sound.noise_normal": 1,
    "sound.noise_loud": 2,
    "sound.noise_chaotic": 2,
    # engine/environment_propagation.py
    "heat.base_rate": 0.05,
    "heat.max_delta": 2.0,
    # engine/lighting.py
    "light.spill_factor": 0.5,
    # engine/barriers.py (task-421) — light's TRANSMISSION per way state. Sound
    # has a matching `sound.way_*` set; the two share one state ladder, not one
    # number, because a cost and a fraction run in opposite directions.
    "light.way_open": 1.0,
    "light.way_see_through": 0.75,
    "light.way_closed": 0.25,
    "light.way_locked": 0.1,
    "light.way_blocked": 0.0,
    "light.way_hidden": 0.0,
    # engine/beyond_visibility.py (task-498) — how many ways a sightline runs
    # through. A taste decision, so it lives where it can be argued with.
    "sightline.depth": 3,
    # engine/weather_forecast.py
    "forecast.apply_scope": "exterior",
    # engine/emotion.py (task-96)
    "emotion.decay_per_tick": 1.5,
    "emotion.llm_spike_max": 15.0,
    "emotion.recall_spike_scale": 0.25,
    # engine/emotion.py (task-505) — resolve emotion labels the curated keyword
    # map has never seen, by nearest affect-dimension anchor. Off by default: the
    # keyword map is the fast path, and a semantic miss costs an embedding call.
    "emotion.semantic_labels": False,
    # Graph visualization defaults
    "graph.physics_enabled": True,
    "graph.show_items": False,
    "graph.show_only_inhabited": True,
    # player.py — per-character memory retention
    "memory.max_per_character": 0,
    # player.py — relationship drift toward neutral when unmaintained
    "relationship.decay_per_day": 0.5,
    # engine/novelty.py — Entertainment from fresh places/things/people
    "entertainment.novelty_recovery_minutes": 120,
    # engine/combat.py (task-607) — how an equipped `defense`/`damage_reduction`
    # expression is applied to incoming damage. ``flat`` is the historical
    # behaviour (subtract the value) and is the default so no scenario changes
    # silently. ``dice`` strips damage dice instead of points; ``percentage``
    # treats the value as a percent of the incoming blow (scale-invariant).
    "combat.damage_reduction_mode": "flat",
}

#: Consuming modules read values at call time via config.get(); no module
#: patching is needed — keep this file purely storage + persistence.
_SECTION_DESCRIPTIONS: dict[str, str] = {
    "sound": "Sound propagation — speech penetration, door/sound barriers, ambient-noise levels",
    "heat": "Temperature propagation — per-tick heat exchange rate and max single-tick delta",
    "light": "Lighting — fraction of a lit neighbor area's light that spills through an open door",
    "emotion": "Character affect (task-96) — per-tick drift toward baseline, LLM-declared feeling cap, memory-recall re-spike scaling, semantic resolution of unknown labels (task-505)",
    "graph": "Graph visualization — physics simulation, item visibility, area filtering",
    "forecast": "Weather forecast — scope of areas the schedule baseline is applied to (exterior | all)",
    "memory": "Character memories — retention cap (0 = keep everything)",
    "relationship": "Relationships — closeness drift toward neutral when nobody maintains the bond",
    "entertainment": "Entertainment — how long a place, thing or person stays familiar before it is fresh (and entertaining) again",
    "combat": "Combat defence (task-604/607) — how worn damage-reduction is applied to incoming damage",
}

#: Default config file location, relative to this module file.
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONFIG_FILE = os.path.join(_DATA_DIR, "engine_config.json")

#: How a **string** spelling of a boolean is read. A hand-edit of a JSON file
#: writes `"true"`, and ``bool("false")`` is ``True`` — so a config that *looks*
#: like it turned something off actually turned it on. Listed explicitly rather
#: than with a truthiness test, because a typo has to be a refusal, not a guess.
_TRUE_SPELLINGS = {"true", "1", "yes", "on"}
_FALSE_SPELLINGS = {"false", "0", "no", "off"}


def _coerce_like_default(default: object, value: object) -> object:
    """Coerce *value* to the type of *default*, or raise.

    The type is taken from the **default**, never from the value. A setting is
    declared by its default, and a value that cannot be read as that type is a bad
    edit the author needs told about — not something to reshape into whatever
    happens to parse.

    - ``bool`` accepts a real bool, and the string and number spellings people
      actually write in a hand-edited file; anything else is refused.
    - ``int`` / ``float`` accept their own type and a numeric string.
    - ``str`` accepts a string. A number for a string setting is a bad edit, and
      is refused rather than becoming ``"2"``.
    - Any other default type has no rule here, and says so by refusing: the table
      gaining a type this function cannot read is a bug in the function, and
      coercing it to float would hide it.
    """
    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            text = value.strip().lower()
            if text in _TRUE_SPELLINGS:
                return True
            if text in _FALSE_SPELLINGS:
                return False
            raise ValueError(f"{value!r} is not a yes/no value")
        raise ValueError(f"{value!r} is not a yes/no value")
    if isinstance(default, int):
        if isinstance(value, bool):
            # A bool IS an int in Python, and `int(True)` is 1 — so a hand-edited
            # `"graph.physics_enabled": true` for a count would silently become 1.
            raise ValueError(f"{value!r} is a bool, not a number")
        return int(value)
    if isinstance(default, float):
        if isinstance(value, bool):
            raise ValueError(f"{value!r} is a bool, not a number")
        return float(value)
    if isinstance(default, str):
        if isinstance(value, str):
            return value
        raise ValueError(f"{value!r} is not a string")
    raise ValueError(f"no coercion rule for default type {type(default).__name__}")


def _refuse_if_not_a_choice(key: str, value: object) -> Optional[str]:
    """A reason to refuse *value* for *key*, or ``None`` when it is allowed.

    A key may declare ``"choices"`` in :data:`SCHEMA`, which is how a *string*
    setting says which strings it means. Without it the value is taken on trust,
    and a consumer whose default branch is "anything else" turns a typo into a
    silently different behaviour — ``forecast.apply_scope`` reads "not exterior"
    as "apply to every area", so ``"exteriorr"`` would have quietly widened the
    weather to interiors. Declaring the set is one line per key; a mistake in it
    becomes a message instead of a change nobody asked for.
    """
    allowed = (SCHEMA.get(key) or {}).get("choices")
    if not allowed or value in allowed:
        return None
    return f"{value!r} is not one of {', '.join(str(c) for c in allowed)}"


class RuntimeConfig:
    """Load/save/apply the tunable engine constants."""

    def __init__(self, config_file: str = CONFIG_FILE) -> None:
        self._config_file = config_file
        self._values: dict[str, object] = dict(DEFAULTS)
        self._load()

    # -- loading ---------------------------------------------------------

    def _load(self) -> None:
        """Merge overrides from JSON on top of DEFAULTS, ignoring unknown keys."""
        if not os.path.exists(self._config_file):
            return
        try:
            with open(self._config_file, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                logger.warning("engine_config.json must be a JSON object; ignoring file.")
                return
            for key, value in loaded.items():
                if key not in DEFAULTS:
                    logger.warning("Ignoring unknown engine_config key '%s'", key)
                    continue
                # Coerce to the default's own type so a bad hand-edit can't
                # crash consumption down-stream. The type comes from the
                # **default**, not from the value: coercing by the value's shape
                # is how a string setting quietly becomes a number.
                #
                # Every arm of this ladder used to be bool → int → `else: float`,
                # so a **string**-defaulted key had no arm at all and fell into
                # the float one — `float("exterior")` raised, and
                # `forecast.apply_scope` was therefore *unsettable*: the only
                # string-defaulted key warned "Ignoring bad value" on every load
                # and silently kept the default, so the operator could not change
                # it however they edited the file. One key, one warning, one
                # setting that did nothing.
                #
                # The final `else` now refuses rather than guessing: a type with
                # no coercion rule is a bug in this table, and coercing it to
                # float would hide it.
                try:
                    coerced = _coerce_like_default(DEFAULTS[key], value)
                except (ValueError, TypeError):
                    logger.warning("Ignoring bad value for '%s'", key)
                    continue
                self._values[key] = coerced
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Failed to load engine_config.json: %s", exc)

    # -- access ----------------------------------------------------------

    @property
    def values(self) -> dict[str, object]:
        """Live merged values (defaults + overrides)."""
        return dict(self._values)

    def get(self, key: str, default=None):
        return self._values.get(key, default)

    # -- persistence -----------------------------------------------------

    def save(self, values: dict) -> dict[str, object]:
        """Merge ``values`` over the current state, persist, apply live.

        Only known keys are accepted, and a value is coerced to its default's type
        by the same rule the loader uses (:func:`_coerce_like_default`) — the two
        used to have separate copies of that ladder, so a string-defaulted key
        failed on the *file* path with a warning and on the *API* path in silence.
        Returns the merged values dict.
        """
        for key, value in values.items():
            if key not in DEFAULTS:
                logger.warning("Ignoring unknown engine_config key '%s'", key)
                continue
            try:
                coerced = _coerce_like_default(DEFAULTS[key], value)
                refused = _refuse_if_not_a_choice(key, coerced)
            except (ValueError, TypeError):
                continue
            if refused is not None:
                logger.warning("Ignoring bad value for '%s': %s", key, refused)
                continue
            self._values[key] = coerced

        payload = {key: self._values[key] for key in DEFAULTS if key in self._values}
        try:
            with open(self._config_file, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except OSError as exc:
            logger.error("Failed to write engine_config.json: %s", exc)

        return self.values

    def reset(self) -> dict[str, object]:
        """Restore all tunables to the built-in defaults and persist."""
        self._values = dict(DEFAULTS)
        try:
            with open(self._config_file, "w", encoding="utf-8") as handle:
                json.dump(dict(DEFAULTS), handle, indent=2)
        except OSError as exc:
            logger.error("Failed to write engine_config.json: %s", exc)
        return self.values


#: Single shared config instance loaded once at import.
config = RuntimeConfig()


#: Human-readable label + input kind for each key, used by the Engine Config
#: UI to render the editor without hardcoding the key list in the frontend.
SCHEMA: dict[str, dict] = {
    "memory.max_per_character": {"section": "memory", "label": "Max memories per character (0 = unlimited)", "type": "number"},
    "relationship.decay_per_day": {"section": "relationship", "label": "Closeness lost per unmaintained day", "type": "float"},
    "entertainment.novelty_recovery_minutes": {"section": "entertainment", "label": "Minutes before a place/thing/person is novel again", "type": "number"},
    "sound.speech_whisper": {"section": "sound", "label": "Whisper penetration", "type": "number"},
    "sound.speech_normal": {"section": "sound", "label": "Normal speech penetration", "type": "number"},
    "sound.speech_shout": {"section": "sound", "label": "Shout penetration", "type": "number"},
    "sound.speech_scream": {"section": "sound", "label": "Scream penetration", "type": "number"},
    "sound.way_open": {"section": "sound", "label": "Open door barrier", "type": "float"},
    "sound.way_closed": {"section": "sound", "label": "Closed door barrier", "type": "float"},
    "sound.way_locked": {"section": "sound", "label": "Locked door barrier", "type": "float"},
    "sound.way_blocked": {"section": "sound", "label": "Blocked door barrier", "type": "float"},
    "sound.way_hidden": {"section": "sound", "label": "Hidden door barrier", "type": "float"},
    "sound.way_see_through": {"section": "sound", "label": "See-through (window) barrier", "type": "float"},
    "sound.noise_silent": {"section": "sound", "label": "Silent ambient noise", "type": "number"},
    "sound.noise_quiet": {"section": "sound", "label": "Quiet ambient noise", "type": "number"},
    "sound.noise_normal": {"section": "sound", "label": "Normal ambient noise", "type": "number"},
    "sound.noise_loud": {"section": "sound", "label": "Loud ambient noise", "type": "number"},
    "sound.noise_chaotic": {"section": "sound", "label": "Chaotic ambient noise", "type": "number"},
    "heat.base_rate": {"section": "heat", "label": "Heat exchange rate per tick", "type": "float"},
    "heat.max_delta": {"section": "heat", "label": "Max °C change per tick", "type": "float"},
    "light.spill_factor": {"section": "light", "label": "Light spill fraction", "type": "float"},
    "light.way_open": {"section": "light", "label": "Open door light transmission", "type": "float"},
    "light.way_see_through": {"section": "light", "label": "See-through (window) light transmission", "type": "float"},
    "light.way_closed": {"section": "light", "label": "Closed door light transmission", "type": "float"},
    "light.way_locked": {"section": "light", "label": "Locked door light transmission", "type": "float"},
    "light.way_blocked": {"section": "light", "label": "Blocked passage light transmission", "type": "float"},
    "light.way_hidden": {"section": "light", "label": "Hidden panel light transmission", "type": "float"},
    "sightline.depth": {"section": "light", "label": "Sightline depth (ways a view runs through)", "type": "int"},
    "emotion.decay_per_tick": {"section": "emotion", "label": "Mood drift toward baseline per tick", "type": "float"},
    "emotion.llm_spike_max": {"section": "emotion", "label": "Max spike from a declared feeling", "type": "float"},
    "emotion.recall_spike_scale": {"section": "emotion", "label": "Memory-recall re-feel scaling", "type": "float"},
    "emotion.semantic_labels": {"section": "emotion", "label": "Resolve unknown emotion labels by embedding (needs an embedding provider)", "type": "bool"},
    "graph.physics_enabled": {"section": "graph", "label": "Enable physics simulation", "type": "bool"},
    "graph.show_items": {"section": "graph", "label": "Show items in graph", "type": "bool"},
    "graph.show_only_inhabited": {"section": "graph", "label": "Show only inhabited areas", "type": "bool"},
    # `choices` is what makes a *string* setting say which strings it means. Its
    # consumer reads "not exterior" as "apply to every area", so without the set a
    # typo would widen the weather to interiors in silence.
    "forecast.apply_scope": {"section": "forecast", "label": "Baseline-applied areas", "type": "string", "choices": ["exterior", "all"]},
    # task-607: the DR grammar is the one weapon damage already uses, so an author
    # types `20` or `d8`. The mode decides what that value *does*.
    "combat.damage_reduction_mode": {"section": "combat", "label": "Damage reduction mode", "type": "string", "choices": ["flat", "dice", "percentage"]},
}