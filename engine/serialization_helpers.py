"""Serialization helpers: pure payload/projection helpers used by WorldSerializer
and the routes layer.

Owner of the small, stateless transforms that fold mixed-case vitals, compute
per-region exposure, derive goal ``blocked_by`` lists, assemble the MOSIAC
decision context, build trait-behavior prose lines, coerce personality dials,
and project the disposition payload. ``engine.serialization`` re-exports every
name here so existing import paths stay stable.
"""

import logging

logger = logging.getLogger(__name__)

#: Lowercase keys that need a non-trivial canonical form (not just capitalize).
_VITAL_KEY_ALIASES = {"hp": "HP", "max_hp": "Max_HP", "mp": "Mana", "max_mp": "Max_Mana"}


def _body_region_catalog():
    """Lazy-import the body-region catalog to avoid a hard import cycle."""
    from engine.body_parts import BODY_REGIONS
    return BODY_REGIONS


def canonical_vitals(vitals) -> dict:
    """Fold mixed-case vital keys into their canonical form.

    Library character files have historically carried BOTH cases ("Social"
    and "social") - the lowercase duplicates leak into the runtime vitals
    dict, where lowercase readers (talkinessHint reads ``vitals.social``)
    pick them up and misread character state. Capitalized/aliased wins.
    """
    if not isinstance(vitals, dict):
        return dict(vitals or {})
    out = {}
    for k, v in vitals.items():
        key = str(k)
        if key in _VITAL_KEY_ALIASES:
            key = _VITAL_KEY_ALIASES[key]
        elif key and key[0].islower():
            key = key[0].upper() + key[1:]
        out[key] = v
    return out


def _region_exposure_map(player, graph):
    """Computed per-region exposure for a player (single source of truth)."""
    from engine.body_parts import BODY_REGIONS, is_exposed
    return {
        region_id: is_exposed(player, region_id, graph)
        for region_id in BODY_REGIONS
    }


def _goals_payload(graph, player_manager, player, pname):
    """A character's goals with a derived ``blocked_by`` (task-810).

    A projection for the payload and the UI: the stored goal keeps only its
    authored ``blocks``. Resolution is skipped when there are no goals, so the
    common case pays nothing.
    """
    from engine import goals as _goals
    stored = getattr(player, 'goals', []) or []
    if not stored:
        return []
    try:
        holder = player_manager._player_node_id(pname)
        resolvers = _goals.world_resolvers(graph, holder, stored)
    except Exception:
        resolvers = {"goal": _goals.goal_resolver(stored)}
    return _goals.with_blockers(stored, resolvers)


def _mosiac_payload(gs, player):
    """A character's MOSIAC decision context (task-812) - a projection, not state.

    Returns None if assembly fails, so a state fetch never 500s on it.
    """
    try:
        from engine.mosiac import assemble
        return assemble(gs, player)
    except Exception:
        return None


def _trait_behavior(player) -> list:
    """Prose lines for the LLM prompt: trait `behavior_prompt`s + disposition whispers.

    The prompt builder reads `player.trait_behavior`
    (`static/js/agent/prompt-builder/character-state.ts`) and nothing wrote it
    before task-805, so the trait schema-v2 behavior_prompt never reached a prompt.
    This is the writer: each trait's own prose, then task-805's `disposition.whispers`
    derived from the same traits, so soak and LLM share one vocabulary.
    """
    try:
        from engine import disposition
        from engine.traits import TraitSystem
        lines = list(TraitSystem.behavior_prompts(player))
        lines += list(disposition.whispers(player))
    except Exception:
        return []
    seen: set = set()
    out: list = []
    for line in lines:
        if line and line not in seen:
            seen.add(line)
            out.append(line)
    return out


def normalize_dials(raw) -> dict:
    """Coerce a saved personality-dial map to ``{trait_id: float in 0..1}``.

    An unreadable value is dropped (the dial then reads neutral), never a crash -
    so an old save with no dials loads to `{}` and an existing character is
    unchanged (task-806).
    """
    out: dict = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            try:
                out[str(key)] = max(0.0, min(1.0, float(value)))
            except (TypeError, ValueError):
                continue
    return out


def _disposition_payload(player) -> dict:
    """The character's decision weights, for the Mind panel and debugging.

    Each weight carries its registry `kind` / `base` / range alongside the value
    (task-800), so the panel can label it without a second lookup; `dials` are the
    authored inputs (task-806). The whispers ride on `trait_behavior` (task-805).
    Nothing here is stored - it is a live read, rebuilt on every serialize.
    """
    try:
        from engine import disposition
        index = disposition.by_name()
        weights = []
        for name, value in disposition.character_weights(player).items():
            score = index.get(name)
            weights.append({
                "name": name,
                "value": value,
                "kind": score.kind if score else "",
                "base": score.base if score else 0.0,
                "lo": score.lo if score else 0.0,
                "hi": score.hi if score else 0.0,
            })
        return {
            "weights": weights,
            "dials": dict(getattr(player, "personality_dials", {}) or {}),
            "gated": sorted(disposition.gated_verbs(player)),
            # The soak candidate verbs and the score each contributes (task-801),
            # so the panel can show what the character can choose and what it feeds.
            "actions": [
                {"verb": verb, "scores": sorted(disposition.features_of(verb).keys())}
                for verb in disposition.SOAK_VERBS
            ],
        }
    except Exception:
        return {"weights": [], "dials": {}, "gated": [], "actions": []}