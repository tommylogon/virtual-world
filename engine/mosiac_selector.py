"""The MOSIAC Selector - Pursuit selection from goals, needs, memory, and world state (task-704).

The Choice step of MOSIAC (Motivation, Obligations, Schedules, Intentions, Attention, Choice).
Ranks candidate pursuits using the score formula:
    score(action) = disposition_weights . action_features + goal_alignment(action, active_goal) + need_pressure

Key rules:
- Goal alignment connects GIMP goals to pursuit selection via active_goal's achieve refs.
- Priority is 1-is-highest; choosing which goal is active is this selector's job.
- Only targets and facts supported by the actor's knowledge and authoritative world are bound.
- Rejection is a choice, not a failure: no retry penalty or forced re-proposal in the same cycle.
- Simple NPCs choose deterministically; LLM agents receive structured + prose context.

@module mosiac_selector
@contributes get_active_goal, goal_alignment, score_pursuit_candidate, bind_candidate_parameters, select_pursuit, decline_pursuit
@docs docs/virtualWorld/Characters/Activities & States.md
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from engine import goals, disposition, pursuit_templates


# Feature tags mapping pursuit templates / activities to disposition dimensions
TEMPLATE_FEATURES: Dict[str, Dict[str, float]] = {
    "meal": {"sustenance": 4.0, "comfort": 1.5, "self_preservation": 2.0},
    "gather": {"order": 2.0, "achievement": 2.0, "sustenance": 1.5},
    "haul": {"order": 3.0, "achievement": 2.0, "affiliation": 1.0},
    "rally": {"affiliation": 4.0, "aggression": 1.5, "dominance": 2.0},
    "scout-and-report": {"curiosity": 3.0, "achievement": 2.0, "safety": 1.5},
    "sleep-at-venue": {"comfort": 4.0, "safety": 2.0, "rest": 4.0},
    "fish-and-bring-home": {"sustenance": 3.0, "achievement": 2.5, "patience": 2.0},
}


def get_active_goal(player) -> Optional[dict]:
    """Return the primary active goal for *player* (1-is-highest priority).

    If multiple active goals exist, sorts by priority (ascending), then
    opened_tick (earliest first), then stable id.
    """
    player_goals = getattr(player, "goals", None) or []
    active_goals = [g for g in player_goals if isinstance(g, dict) and g.get("status") == "active"]
    if not active_goals:
        return None

    def sort_key(g):
        prio = g.get("priority", 10)
        try:
            prio = int(prio)
        except (TypeError, ValueError):
            prio = 10
        tick = g.get("opened_tick", 0)
        try:
            tick = int(tick)
        except (TypeError, ValueError):
            tick = 0
        return (prio, tick, str(g.get("id", "")))

    active_goals.sort(key=sort_key)
    return active_goals[0]


def goal_alignment(candidate: Dict[str, Any], active_goal: Optional[Dict[str, Any]]) -> float:
    """Calculate how much *candidate* advances *active_goal* via its achieve refs.

    Returns a float score bonus (positive for advancing, 0 for neutral, negative for blocking).
    """
    if not active_goal or not isinstance(active_goal, dict):
        return 0.0

    priority = int(active_goal.get("priority", 1) or 1)
    priority_multiplier = max(1.0, 4.0 - min(priority, 3))

    alignment = 0.0
    template_id = str(candidate.get("template_id") or candidate.get("id") or "").lower()
    candidate_tags = {str(t).lower() for t in (candidate.get("tags") or [])}
    candidate_text = f"{template_id} {candidate.get('purpose', '')} {candidate.get('label', '')}".lower()

    # Goal description and intention matching
    goal_text = f"{active_goal.get('what', '')} {active_goal.get('why', '')} {active_goal.get('intention', '')}".lower()
    if template_id in goal_text or any(t in goal_text for t in candidate_tags):
        alignment += 4.0 * priority_multiplier

    # Check achieve refs
    achieve_refs = active_goal.get("achieve", []) or []
    for item in achieve_refs:
        ref = item.get("ref", "") if isinstance(item, dict) else str(item)
        ref_clean = ref.strip().lower()
        if not ref_clean:
            continue

        prefix, _, target = ref_clean.partition(":")
        target = target.strip() or prefix

        # Conceptual synonyms (e.g. clan/group for rally; food/eat for meal)
        synonyms = {target}
        if target in ("clan", "group", "social", "rally"):
            synonyms.update(["clan", "group", "rally", "gathering"])
        if target in ("food", "eat", "meal", "hunger"):
            synonyms.update(["food", "meal", "eat", "eating"])

        if any(s in candidate_text or s in candidate_tags for s in synonyms):
            alignment += 6.0 * priority_multiplier
            continue

        # Check step targets or specs
        steps = candidate.get("steps") or []
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_area = str(step.get("area") or "").lower()
            step_item = str(step.get("target_item") or "").lower()
            step_recipe = str(step.get("recipe") or "").lower()
            spec = step.get("spec") or {}
            spec_name = str(spec.get("name") or "").lower() if isinstance(spec, dict) else ""
            spec_tags = {str(t).lower() for t in spec.get("tags", [])} if isinstance(spec, dict) else set()

            if any(s in step_item or s in spec_name or s in spec_tags or s in step_recipe for s in synonyms):
                alignment += 5.0 * priority_multiplier
                break
            if any(s in step_area for s in synonyms):
                alignment += 4.0 * priority_multiplier
                break

    # Check if candidate is blocked by active goal's blocks
    block_refs = active_goal.get("blocks", []) or []
    for item in block_refs:
        b_ref = item.get("ref", "") if isinstance(item, dict) else str(item)
        b_target = b_ref.partition(":")[2].strip().lower()
        if b_target and (b_target in candidate_text or b_target in candidate_tags):
            alignment -= 10.0

    return alignment


def score_pursuit_candidate(
    player,
    template: Dict[str, Any],
    active_goal: Optional[Dict[str, Any]],
    bindings: Dict[str, Any],
) -> float:
    """Compute score for a pursuit candidate using disposition, goal alignment, and needs."""
    template_id = str(template.get("id") or "").lower()

    # 1. Check value gates
    action_name = "rest" if "sleep" in template_id else ("eat" if "meal" in template_id else "take")
    if hasattr(disposition, "is_gated") and disposition.is_gated(player, action_name):
        return -float("inf")

    # 2. Base disposition score
    disposition_score = 0.0
    if hasattr(disposition, "character_weights"):
        char_weights = disposition.character_weights(player)
        features = TEMPLATE_FEATURES.get(template_id, {})
        for dim, feat_val in features.items():
            weight = char_weights.get(f"utility.{dim}", char_weights.get(dim, 1.0))
            disposition_score += float(weight) * float(feat_val)

    # 3. Goal alignment score
    bound_candidate = dict(template)
    bound_candidate["bindings"] = bindings
    align_score = goal_alignment(bound_candidate, active_goal)

    # 4. Live need pressure
    vitals = getattr(player, "vitals", {}) or {}
    need_score = 0.0
    if template_id == "meal":
        hunger = float(vitals.get("Hunger", 0) or 0)
        if hunger >= 50:
            need_score += (hunger - 50.0) * 0.3
    elif "sleep" in template_id:
        energy = float(vitals.get("Energy", 100) or 100)
        if energy <= 40:
            need_score += (40.0 - energy) * 0.3
    elif template_id == "rally":
        social = float(vitals.get("Social", 50) or 50)
        if social <= 40:
            need_score += (40.0 - social) * 0.25

    return disposition_score + align_score + need_score


def bind_candidate_parameters(
    player,
    world,
    template: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Ground parameters for *template* using only known, authoritative facts."""
    template_id = str(template.get("id") or "").lower()
    bindings: Dict[str, Any] = {}

    current_area = getattr(player, "current_area", "CampfireClearing")
    home_area = getattr(player, "home", None) or current_area

    if template_id == "meal":
        bindings["home"] = home_area
        bindings["food_spec"] = {"tags": ["food"]}
    elif template_id == "sleep-at-venue":
        bindings["venue"] = home_area
        bindings["bed_id"] = "item_bed"
    elif template_id == "rally":
        bindings["rally_area"] = current_area
    elif template_id == "haul":
        bindings["source"] = current_area
        bindings["sink"] = home_area
        bindings["item_spec"] = {"tags": ["supplies"]}
    elif template_id == "gather":
        bindings["source_tags"] = ["supplies"]
        bindings["home"] = home_area
        bindings["item_spec"] = {"tags": ["food"]}
    elif template_id == "fish-and-bring-home":
        bindings["fishing_place"] = current_area
        bindings["home"] = home_area
    elif template_id == "scout-and-report":
        bindings["scout_area"] = current_area
        bindings["report_area"] = home_area
    else:
        # Generic parameter passthrough
        params = template.get("parameters", {}) or {}
        for p_name in params:
            bindings[p_name] = current_area

    # Validate binding through pursuit_templates.instantiate
    inst = pursuit_templates.instantiate(template_id, bindings)
    if inst is None:
        return None
    return bindings


def select_pursuit(
    player,
    world,
    candidate_ids: Optional[List[str]] = None,
    trigger: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Run MOSIAC Choice step to choose and bind a pursuit for *player*.

    Runs on meaningful triggers (needs, goal change, completion, etc.).
    Returns bound pursuit dict ready for Player.active_pursuit, or None.
    """
    if player.state in ("dead", "unconscious"):
        return None

    # Do not reselect if character already has an active, valid pursuit
    if getattr(player, "active_pursuit", None) and getattr(player, "plan", None):
        return None

    active_goal = get_active_goal(player)
    catalog = pursuit_templates.load()

    if candidate_ids:
        templates_to_evaluate = [catalog[cid] for cid in candidate_ids if cid in catalog]
    else:
        templates_to_evaluate = list(catalog.values())

    declined_cycle = getattr(player, "_declined_pursuits_cycle", set()) or set()

    scored_candidates = []
    for template in templates_to_evaluate:
        t_id = template.get("id")
        if not t_id or t_id in declined_cycle:
            continue

        # Check calendar, clock, and weather timing
        if not pursuit_templates.timing_matches(template, world):
            continue

        # Attempt to bind candidate parameters
        bindings = bind_candidate_parameters(player, world, template)
        if bindings is None:
            continue

        score = score_pursuit_candidate(player, template, active_goal, bindings)
        if score > -100.0:
            scored_candidates.append((score, template, bindings))

    if not scored_candidates:
        return None

    # Deterministic pick: highest score wins, tie-break by template id
    scored_candidates.sort(key=lambda item: (item[0], item[1].get("id", "")), reverse=True)
    best_score, best_template, best_bindings = scored_candidates[0]

    if best_score <= 0.0:
        return None

    # Construct bound pursuit record
    t_id = best_template["id"]
    time_ticks = getattr(world, "time_ticks", 0) or 0
    assignment_id = f"pursuit_{t_id}_{time_ticks}"
    reason = (
        f"Serving {active_goal['what']}" if active_goal
        else f"Driven by personal need ({best_template.get('purpose', t_id)})"
    )

    inst = pursuit_templates.instantiate(t_id, best_bindings)
    return {
        "assignment_id": assignment_id,
        "template_id": t_id,
        "template_version": best_template.get("version", 1),
        "label": best_template.get("name", t_id),
        "purpose": best_template.get("purpose", ""),
        "reason": reason,
        "bindings": best_bindings,
        "steps": inst["steps"] if inst else [],
        "requirements": best_template.get("requirements", []),
        "supplies": best_template.get("supplies", []),
        "progress": best_template.get("progress", []),
        "timing": best_template.get("timing", {}),
    }


def decline_pursuit(player, template_id: str, reason: str = "personal choice") -> None:
    """Record that *player* declined *template_id* in the current selection cycle.

    A rejection is a choice, not a failure. No retry penalty or forced re-proposal.
    """
    declined = getattr(player, "_declined_pursuits_cycle", None)
    if declined is None:
        declined = set()
        player._declined_pursuits_cycle = declined
    declined.add(template_id)


def reset_selection_cycle(player) -> None:
    """Clear declined candidates at the start of a fresh selection cycle."""
    if hasattr(player, "_declined_pursuits_cycle"):
        player._declined_pursuits_cycle = set()
