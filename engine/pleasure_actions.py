"""Pleasure/intimacy action system (tasks 211 + 212).

Everything here is gated behind ``world.mature_content``: the caller (the
``/api/action`` dispatch) rejects intimacy verbs with a flavor message when
the toggle is off, and the mechanical pipeline below is a no-op unless the
target actually carries the pleasure vitals (Arousal/Stimulation/Pleasure,
which only exist when the toggle is on — task-207).

Pipeline (task-212):
    VERB_BASE → x intensity modifier → x body-part sensitivity (body_state)
    → x trait body_part multiplier → Stimulation/Arousal/Pleasure gains,
    with pain_potential flipping into negative pleasure (overstimulation).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# ──────────────────────────────────────────────────────────────
# Verb base table (task-212, design §Additions #1)
# ──────────────────────────────────────────────────────────────

#: verb → mechanical base properties. ``pressure`` is the raw intensity of
#: the contact, ``pleasure_mult`` scales sensitivity into stimulation,
#: ``pain_potential`` is how easily the verb hurts (flips to negative
#: pleasure), ``stim_type`` describes the rhythm for future use (LLM hints).
VERB_BASE: Dict[str, Dict[str, Any]] = {
    "kiss":   {"pressure": 2, "pleasure_mult": 1.0, "pain_potential": 0, "stim_type": "sustained"},
    "caress": {"pressure": 1, "pleasure_mult": 0.8, "pain_potential": 0, "stim_type": "sustained"},
    "lick":   {"pressure": 1, "pleasure_mult": 1.2, "pain_potential": 0, "stim_type": "sustained"},
    "suck":   {"pressure": 3, "pleasure_mult": 1.5, "pain_potential": 0, "stim_type": "rhythmic"},
    "bite":   {"pressure": 4, "pleasure_mult": 1.0, "pain_potential": 3, "stim_type": "spike"},
    "pinch":  {"pressure": 3, "pleasure_mult": 1.2, "pain_potential": 2, "stim_type": "spike"},
    "blow":   {"pressure": 1, "pleasure_mult": 0.9, "pain_potential": 0, "stim_type": "sustained"},
    "tickle": {"pressure": 1, "pleasure_mult": 0.7, "pain_potential": 0, "stim_type": "rhythmic"},
}

#: The verbs the /api/action dispatch routes here. Kept clear of every
#: existing command verb (grab → grapple, grope/feel around → fumble,
#: release → grapple release, strip/undress → self-only undress).
INTIMACY_VERBS: Tuple[str, ...] = tuple(VERB_BASE.keys())

#: intensity word → multiplier
INTENSITY_MODIFIERS: Dict[str, float] = {
    "light": 0.5, "normal": 1.0, "firm": 1.5,
}

#: adverbs parsed out of the free-text command → intensity
INTENSITY_ADVERBS = {
    "gently": "light", "lightly": "light", "softly": "light",
    "firmly": "firm", "hard": "firm", "roughly": "firm", "tightly": "firm",
}

#: verb → body part used when the command carries no explicit ``where``
DEFAULT_REGIONS = {
    "kiss": "lips", "lick": "neck", "suck": "neck", "bite": "neck",
    "caress": "torso", "pinch": "torso", "blow": "neck", "tickle": "torso",
}

#: overall scale so a normal kiss lands a few points on the 0-100 vital
STIM_SCALE = 6.0

#: through-clothing damping when the target region is covered
COVERED_MULT = 0.4

_REACTION_STRONG = (
    "{target} shudders, breath catching audibly.",
    "{target}'s knees visibly weaken for a moment.",
)
_REACTION_MILD = (
    "{target} draws a slow breath.",
    "A visible flush creeps over {target}.",
    "{target} goes very still under the touch.",
)
_PAIN_LINES = (
    "{target} yelps — that one stung.",
    "{target} flinches away from the sharpness of it.",
)


def parse_intensity(text: str) -> Tuple[str, str]:
    """Pull an intensity adverb out of the command tail.

    Returns ``(intensity, remaining_text)``. Unknown text passes through
    unchanged; missing adverb → ``normal``.
    """
    words = (text or "").split()
    for word in words:
        key = word.strip(",.!").lower()
        if key in INTENSITY_ADVERBS:
            remaining = " ".join(w for w in words if w != word)
            return INTENSITY_ADVERBS[key], remaining
    return "normal", text


def body_part_multiplier(target, region_id: str) -> float:
    """Product of every trait ``body_part_multipliers`` entry matching the
    region (exact id, or any ancestor via the region chain — task-212/213)."""
    mult = 1.0
    traits = getattr(target, "traits", None) or {}
    if not traits:
        return mult
    from engine.traits import TRAIT_DEFINITIONS
    from engine.body_parts import region_chain
    chain = set(region_chain(region_id) or [region_id])
    for trait_id in traits:
        definition = TRAIT_DEFINITIONS.get(trait_id) or {}
        table = (definition.get("effects") or {}).get("body_part_multipliers")
        if not isinstance(table, dict):
            continue
        for part, value in table.items():
            if part in chain:
                try:
                    mult *= float(value)
                except (TypeError, ValueError):
                    continue
    return mult


def resolve_body_part(target, where_text: Optional[str], graph,
                      verb: str = "") -> Dict[str, Any]:
    """task-211 ``_resolve_body_part``: resolve + accessibility-check a body part.

    Returns ``{region, covered, accessible, default}``. ``region`` is None when
    the text names no known region. Coverage comes from the paperdoll layers
    (``is_exposed``); a covered region is still reachable — the contact just
    lands through clothing (damped), so ``accessible`` stays True unless the
    region does not exist.
    """
    from engine.body_parts import resolve_region, is_exposed
    region = resolve_region(where_text) if where_text else None
    default = False
    if region is None and not where_text:
        region = resolve_region(DEFAULT_REGIONS.get(verb, "torso"))
        default = True
    if region is None:
        return {"region": None, "covered": False, "accessible": False, "default": default}
    covered = not is_exposed(target, region, graph)
    return {"region": region, "covered": covered, "accessible": True, "default": default}


def apply_stimulation(actor, target, verb: str, region_id: str,
                      intensity: str = "normal", covered: bool = False,
                      closeness: float = 0.0) -> Dict[str, Any]:
    """task-212 multiplier pipeline. Mutates the target's pleasure vitals when
    they exist and returns a report dict for the caller's message.

    Never raises: a target without the vitals (mature toggle off) yields a
    zero-delta report so the action degrades to pure flavor.
    """
    base = VERB_BASE.get(verb)
    if base is None:
        return {"stim": 0, "arousal": 0, "pleasure": 0, "pain": 0, "region": region_id}
    intensity_mod = INTENSITY_MODIFIERS.get(intensity, 1.0)

    body_state = getattr(target, "body_state", None) or {}
    sensitivity = 0.5
    if isinstance(body_state, dict):
        sensitivity = float(body_state.get(region_id, {}).get("sensitivity", 0.5))

    trait_mult = body_part_multiplier(target, region_id)
    covered_mult = COVERED_MULT if covered else 1.0
    closeness_mult = 1.0 + (0.1 if closeness > 50 else 0.0)

    raw = (base["pressure"] * base["pleasure_mult"] * intensity_mod
           * (sensitivity / 0.5) * trait_mult * covered_mult * closeness_mult)
    stim_gain = int(round(raw * STIM_SCALE / 4.0))
    arousal_gain = int(round(stim_gain * 0.35)) + (2 if not covered else 0)
    pleasure_gain = int(round(stim_gain * 0.5))
    pain = int(round(base["pain_potential"] * intensity_mod))
    if pain:
        pleasure_gain -= pain * 2

    report = {"stim": stim_gain, "arousal": arousal_gain,
              "pleasure": pleasure_gain, "pain": pain, "region": region_id}

    vitals = getattr(target, "vitals", None) or {}
    if not any(v in vitals for v in ("Stimulation", "Arousal", "Pleasure")):
        # Mature toggle off (or legacy character): flavor-only, no mechanics.
        return {"stim": 0, "arousal": 0, "pleasure": 0, "pain": 0,
                "region": region_id, "overstimulated": False}
    overstim = False
    if "Stimulation" in vitals:
        vitals["Stimulation"] = max(0, min(100, vitals.get("Stimulation", 0) + stim_gain))
    if "Arousal" in vitals:
        vitals["Arousal"] = max(0, min(100, vitals.get("Arousal", 0) + arousal_gain))
    if "Pleasure" in vitals and pleasure_gain:
        new_p = vitals.get("Pleasure", 0) + pleasure_gain
        if new_p < 0:
            new_p = 0
            overstim = True
        vitals["Pleasure"] = max(0, min(100, new_p))
    report["overstimulated"] = overstim
    if overstim and hasattr(target, "add_condition"):
        target.add_condition("overstimulated", duration=3)
    return report


def _reaction_line(target_name: str, stim_gain: int, pain: int) -> str:
    import random
    name = target_name
    if pain > 0:
        return random.choice(_PAIN_LINES).replace("{target}", name)
    if stim_gain >= 15:
        return random.choice(_REACTION_STRONG).replace("{target}", name)
    return random.choice(_REACTION_MILD).replace("{target}", name)


def _verb3(verb: str) -> str:
    """Third-person singular: kiss→kisses, pinch→pinches, lick→licks."""
    if verb.endswith(("s", "x", "z", "ch", "sh")):
        return verb + "es"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    return verb + "s"


def execute_intimacy_action(world, actor_name: str, verb: str, target_name: str,
                            where_text: Optional[str] = None,
                            intensity: str = "normal") -> str:
    """task-211 entry point: run one intimacy verb and return the output text.

    Assumes the mature-content gate already passed (the dispatch checks it).
    """
    from engine.body_parts import region_name

    actor = world.players.get(actor_name)
    if actor is None:
        return "You can't do that."
    if target_name == actor_name:
        return f"You can't {verb} yourself."

    target = world.players.get(target_name)
    if target is None:
        resolved, candidates = world._match_character_name(target_name)
        if resolved:
            target_name = resolved
            target = world.players[resolved]
        elif candidates:
            return f"You don't know exactly who that is. Do you mean: {', '.join(candidates)}?"
    if target is None:
        return f"You don't see {target_name}."
    if target.current_area != actor.current_area:
        return f"{target_name} isn't here."
    if getattr(target, "state", None) == "dead":
        return f"{target_name} doesn't react."

    part = resolve_body_part(target, where_text, world.graph, verb)
    if not part["accessible"]:
        return f"You can't find that body part on {target_name}."

    region_label = (region_name(part["region"]) or (part["region"] or "").replace("_", " ")).lower()
    through = " through the clothing" if part["covered"] else ""
    closeness = 0.0
    rel = (getattr(actor, "relationships", None) or {}).get(target_name) or {}
    try:
        closeness = float(rel.get("closeness", 0))
    except (TypeError, ValueError):
        closeness = 0.0

    report = apply_stimulation(actor, target, verb, part["region"],
                               intensity=intensity, covered=part["covered"],
                               closeness=closeness)

    prefix = {"light": "gently ", "firm": "firmly "}.get(intensity, "")
    line = f"{actor_name} {prefix}{_verb3(verb)} {target_name} on the {region_label}{through}."
    if report["stim"] > 0 or report["pain"] > 0:
        line += " " + _reaction_line(target_name, report["stim"], report["pain"])
    if report.get("overstimulated"):
        line += f" {target_name} is overwhelmed — it's too much."
    return line
