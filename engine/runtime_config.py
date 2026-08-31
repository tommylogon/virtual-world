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
    "sound.way_locked": 2,
    "sound.way_blocked": 2,
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
    # engine/weather_forecast.py
    "forecast.apply_scope": "exterior",
    # engine/emotion.py (task-96)
    "emotion.decay_per_tick": 1.5,
    "emotion.llm_spike_max": 15.0,
    "emotion.recall_spike_scale": 0.25,
    # Graph visualization defaults
    "graph.physics_enabled": True,
    "graph.show_items": False,
    "graph.show_only_inhabited": True,
}

#: Consuming modules read values at call time via config.get(); no module
#: patching is needed — keep this file purely storage + persistence.
_SECTION_DESCRIPTIONS: dict[str, str] = {
    "sound": "Sound propagation — speech penetration, door/sound barriers, ambient-noise levels",
    "heat": "Temperature propagation — per-tick heat exchange rate and max single-tick delta",
    "light": "Lighting — fraction of a lit neighbor area's light that spills through an open door",
    "emotion": "Character affect (task-96) — per-tick drift toward baseline, LLM-declared feeling cap, memory-recall re-spike scaling",
    "graph": "Graph visualization — physics simulation, item visibility, area filtering",
    "forecast": "Weather forecast — scope of areas the schedule baseline is applied to (exterior | all)",
}

#: Default config file location, relative to this module file.
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONFIG_FILE = os.path.join(_DATA_DIR, "engine_config.json")


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
                # Coerce to the default's type so a bad hand-edit can't
                # crash consumption down-stream (int/default-float strings).
                try:
                    if isinstance(DEFAULTS[key], bool):
                        coerced = bool(value)
                    elif isinstance(DEFAULTS[key], int):
                        coerced = int(value)
                    else:
                        coerced = float(value)
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

        Only known keys are accepted. Returns the merged values dict.
        """
        for key, value in values.items():
            if key not in DEFAULTS:
                logger.warning("Ignoring unknown engine_config key '%s'", key)
                continue
            try:
                if isinstance(DEFAULTS[key], bool):
                    coerced = bool(value)
                elif isinstance(DEFAULTS[key], int):
                    coerced = int(value)
                else:
                    coerced = float(value)
            except (ValueError, TypeError):
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
    "emotion.decay_per_tick": {"section": "emotion", "label": "Mood drift toward baseline per tick", "type": "float"},
    "emotion.llm_spike_max": {"section": "emotion", "label": "Max spike from a declared feeling", "type": "float"},
    "emotion.recall_spike_scale": {"section": "emotion", "label": "Memory-recall re-feel scaling", "type": "float"},
    "graph.physics_enabled": {"section": "graph", "label": "Enable physics simulation", "type": "bool"},
    "graph.show_items": {"section": "graph", "label": "Show items in graph", "type": "bool"},
    "graph.show_only_inhabited": {"section": "graph", "label": "Show only inhabited areas", "type": "bool"},
    "forecast.apply_scope": {"section": "forecast", "label": "Baseline-applied areas (exterior | all)", "type": "string"},
}