"""Server-side involuntary speech/emote flavor (Phase 3, task-1003).

Ports ``static/js/agent/involuntary.ts`` to Python: non-blocking flavor
(stutter, shiver, cough, sneeze, yelp) driven by active character conditions,
nervous traits, and situational startle. Never replaces the intended action.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

NERVOUS_TRAITS = frozenset({"jittery", "nervous", "clumsy"})

SPEECH_TRIGGERS: Dict[str, tuple[str, float]] = {
    "frightened": ("stutter", 0.50),
    "hypothermia": ("shiver", 0.40),
    "sick": ("cough", 0.35),
    "poisoned": ("cough", 0.40),
    "paranoid": ("stutter", 0.40),
    "sneeze": ("sneeze", 0.55),
}

EMOTE_TRIGGERS: Dict[str, List[str]] = {
    "frightened": [
        "*a small gasp escapes*",
        "*an involuntary shudder runs through them*",
    ],
    "hypothermia": [
        "*they shiver violently, teeth chattering*",
    ],
    "sick": [
        "*a rattling cough escapes*",
    ],
    "poisoned": [
        "*a wracking cough doubles them over*",
    ],
    "sneeze": [
        "*a sharp sneeze catches them off guard*",
    ],
}


def _has_nervous_trait(player: Any) -> bool:
    traits = getattr(player, "traits", None) or {}
    if isinstance(traits, dict):
        keys = {str(k).lower() for k in traits.keys()}
    elif isinstance(traits, (list, set, tuple)):
        keys = {str(k).lower() for k in traits}
    else:
        keys = set()
    return bool(keys & NERVOUS_TRAITS)


def apply_involuntary_speech(
    text: str,
    player: Any,
    *,
    startled: bool = False,
    rng: Optional[random.Random] = None,
) -> str:
    """Optionally inject non-blocking involuntary flavor into a spoken line."""
    if not text or not text.strip():
        return text
    r = rng or random
    boost = 1.8 if _has_nervous_trait(player) else 1.0
    if startled and r.random() < 0.35 * boost:
        return f"Ah-! {text}"

    conds = list((getattr(player, "conditions", None) or {}).keys())
    for cid in conds:
        trig = SPEECH_TRIGGERS.get(str(cid).lower())
        if not trig:
            continue
        kind, chance = trig
        if r.random() < min(0.95, chance * boost):
            if kind == "stutter":
                words = text.split()
                if words and len(words[0]) >= 2:
                    return f"{words[0][0]}-{text}"
            elif kind == "cough":
                return f"*cough* {text}"
            elif kind == "sneeze":
                return f"*achoo!* {text}"
            elif kind == "shiver":
                return f"{text} *shivers*"
    return text


def apply_involuntary_emote(
    emote: Optional[str],
    player: Any,
    *,
    startled: bool = False,
    rng: Optional[random.Random] = None,
) -> Optional[str]:
    """Optionally append an involuntary body-reaction cue to an emote."""
    r = rng or random
    boost = 1.8 if _has_nervous_trait(player) else 1.0
    if startled and r.random() < 0.70 * boost:
        cue = "*flinches sharply*"
        return f"{emote} {cue}".strip() if emote else cue

    conds = list((getattr(player, "conditions", None) or {}).keys())
    for cid in conds:
        cues = EMOTE_TRIGGERS.get(str(cid).lower())
        if cues and r.random() < min(0.95, 0.40 * boost):
            cue = r.choice(cues)
            return f"{emote} {cue}".strip() if emote else cue
    return emote
