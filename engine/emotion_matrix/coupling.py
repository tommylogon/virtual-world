"""Coupled Emotional Matrix physics (Step 2 of Section 4.2).

Shared by all four prototypes (A, B, C, and D) so that the architectural
difference under test is cleanly isolated to how each prototype appraises
world events + memories into raw multi-emotion delta vectors, while all four
run on identical coupled dynamics, regulation friction, trait/memory/witness
secondary emotions, per-target overlays, and autonomic body physics.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from engine.emotion_matrix.autonomic import (
    compute_positive_buffer,
    compute_regulation_capacity,
    compute_vulnerability_load,
    render_observer_tells,
    render_own_body_prompt,
    skill_check_penalties,
    tick_autonomic,
    update_autonomic,
)
from engine.emotion_matrix.schema import (
    EMOTION_PROFILES,
    FAMILIES,
    FAMILY_BASELINES,
    FAMILY_TO_EXPRESSION,
    CharacterEmotionState,
    EmotionEvent,
    EpisodeRecord,
    MatrixStepResult,
)

#: Sparse 13x13 cross-emotion coupling matrix W.
#: Key = source family receiving a positive delta; value = {target_family: ratio}.
#: Captures real coupled dynamics: surging negative emotions suppress happiness
#: and calm; surging anger/disgust erodes live love; jealousy co-activates fear
#: and anger; shame co-activates mild fear of rejection; happiness/love restore calm.
COUPLING_MATRIX: Dict[str, Dict[str, float]] = {
    "anger": {"happiness": -0.45, "calm": -0.55, "love": -0.25, "disgust": 0.12},
    "disgust": {"happiness": -0.35, "calm": -0.30, "love": -0.35, "arousal": -0.40},
    "envy": {"happiness": -0.30, "calm": -0.25, "anger": 0.15, "sadness": 0.10},
    "fear": {"happiness": -0.45, "calm": -0.60, "arousal": -0.25},
    "happiness": {"calm": 0.25, "sadness": -0.35, "anger": -0.20, "fear": -0.15},
    "jealousy": {"happiness": -0.40, "calm": -0.50, "fear": 0.30, "anger": 0.25},
    "love": {"happiness": 0.30, "calm": 0.25, "anger": -0.25, "fear": -0.10},
    "sadness": {"happiness": -0.55, "calm": -0.25, "arousal": -0.30},
    "shame": {"happiness": -0.45, "calm": -0.40, "fear": 0.20, "sadness": 0.18},
    "guilt": {"happiness": -0.30, "calm": -0.30, "shame": 0.12},
    "calm": {"anger": -0.25, "fear": -0.25, "jealousy": -0.15},
    "surprise": {"calm": -0.25},
    "arousal": {"calm": -0.15},
}

MAX_ACTIVE_EPISODES = 6
EXPRESSION_MARGIN = 6.0


def valence_arousal(families: Dict[str, float]) -> Tuple[float, float]:
    """Pure derived (valence -1..+1, arousal 0..1) projection over the 13 families."""
    w_sum = 0.0
    v_acc = 0.0
    a_acc = 0.0
    for fam in FAMILIES:
        over = max(0.0, families.get(fam, FAMILY_BASELINES[fam]) - FAMILY_BASELINES[fam])
        if over < 4.0:
            continue
        prof = EMOTION_PROFILES[fam]
        w_sum += over
        v_acc += over * prof["valence"]
        a_acc += over * prof["arousal"]
    if w_sum <= 0.0:
        return 0.0, 0.1
    return max(-1.0, min(1.0, v_acc / w_sum)), max(0.0, min(1.0, a_acc / w_sum))


def dominant_family_and_expression(families: Dict[str, float]) -> Tuple[str, str]:
    """Strongest family above baseline and its 12-slot portrait key."""
    best_fam = "neutral"
    best_over = 0.0
    for fam in FAMILIES:
        over = families.get(fam, FAMILY_BASELINES[fam]) - FAMILY_BASELINES[fam]
        if over > best_over and over >= EXPRESSION_MARGIN:
            best_over = over
            best_fam = fam
    if best_fam == "neutral":
        return "neutral", "neutral"
    return best_fam, FAMILY_TO_EXPRESSION.get(best_fam, "neutral")


def _disposition_tilts(families: Dict[str, float], overloaded: bool) -> Dict[str, float]:
    """Compute additive disposition tilts from all raised families."""
    raised = {
        fam: families.get(fam, FAMILY_BASELINES[fam]) - FAMILY_BASELINES[fam]
        for fam in FAMILIES
        if families.get(fam, FAMILY_BASELINES[fam]) - FAMILY_BASELINES[fam] >= 15.0
    }
    if not raised:
        return {}
    strongest = max(raised.values()) or 1.0
    scale = 1.35 if overloaded else 1.0
    out: Dict[str, float] = {}
    for fam, amt in raised.items():
        strength = min(1.0, amt / strongest) * scale
        for score_key, weight in EMOTION_PROFILES[fam]["disposition_tilts"].items():
            out[score_key] = out.get(score_key, 0.0) + weight * strength
    return out


def _extract_trait_ids(player: Any) -> set:
    raw_traits = getattr(player, "traits", None) or {}
    if isinstance(raw_traits, dict):
        tset = {str(t).strip().lower() for t in raw_traits.keys()}
    else:
        tset = {str(t).strip().lower() for t in raw_traits}
    persona = getattr(player, "persona", None)
    if isinstance(persona, dict):
        psec = persona.get("personality") or {}
        if isinstance(psec, dict):
            for t in (psec.get("traits") or []):
                if t:
                    tset.add(str(t).strip().lower())
    return tset


def _derive_calming_resistance(
    trait_ids: set,
    recalled_memories: List[Dict[str, Any]],
    state: CharacterEmotionState,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Derive calming resistance and slower decay strictly from traits + unresolved memories."""
    resistance: Dict[str, float] = {}
    decay_mult: Dict[str, float] = {}

    if trait_ids & {"protective", "stubborn", "guarded", "vengeful", "hostile"}:
        resistance["anger"] = max(resistance.get("anger", 0.0), 0.55)
        decay_mult["anger"] = min(decay_mult.get("anger", 1.0), 0.50)
    if trait_ids & {"protective", "paranoid", "vigilant", "anxious", "cautious"}:
        resistance["fear"] = max(resistance.get("fear", 0.0), 0.50)
        decay_mult["fear"] = min(decay_mult.get("fear", 1.0), 0.55)
    if trait_ids & {"possessive", "jealous", "insecure"}:
        resistance["jealousy"] = max(resistance.get("jealousy", 0.0), 0.50)
        decay_mult["jealousy"] = min(decay_mult.get("jealousy", 1.0), 0.55)

    # Active high-stakes unresolved episodes resist casual 1-turn smoothing over.
    for ep in state.episodes:
        if not ep.resolved and ep.peak_delta >= 22.0 and ep.family in ("anger", "fear", "guilt", "shame"):
            resistance[ep.family] = max(resistance.get(ep.family, 0.0), 0.45)
            decay_mult[ep.family] = min(decay_mult.get(ep.family, 1.0), 0.60)

    mem_blob = " ".join(str(m.get("text", "") or "").lower() for m in recalled_memories)
    if any(k in mem_blob for k in ("pregnant", "hospital", "icu", "reputation", "church", "gun", "glock", "bomb")):
        resistance["fear"] = max(resistance.get("fear", 0.0), 0.55)
        decay_mult["fear"] = min(decay_mult.get("fear", 1.0), 0.50)
    return resistance, decay_mult


def apply_matrix_step(
    *,
    engine_name: str,
    latency_ms: float,
    state: CharacterEmotionState,
    raw_deltas: Dict[str, float],
    event: EmotionEvent,
    player: Any,
    recalled_memories: List[Dict[str, Any]],
    gut_appraisal: str,
    explicit_suppress: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> MatrixStepResult:
    """Apply the coupled Emotional Matrix physics to a raw delta vector."""
    before = dict(state.families)
    vuln_load, vuln_factors = compute_vulnerability_load(player, state)
    pos_buffer = compute_positive_buffer(before)
    reg_cap, reg_breakdown = compute_regulation_capacity(player, vuln_load, state)

    # 1. Clean raw deltas to known families.
    clean_raw: Dict[str, float] = {
        fam: float(raw_deltas.get(fam, 0.0) or 0.0) for fam in FAMILIES
    }

    # Check if this event resolves existing unresolved episodes (e.g. checking the facts / repair).
    tags_low = {str(t).lower() for t in event.tags}
    if event.kind in ("check_facts", "repair", "reassure") or "reassure" in tags_low:
        for ep in state.episodes:
            if not ep.resolved:
                if event.kind == "check_facts" and ep.family in ("shame", "fear", "jealousy"):
                    ep.resolved = True
                if event.kind == "check_facts" and "reassure" in tags_low and ep.family == "guilt":
                    ep.resolved = True
                if event.kind == "repair" and ep.family in ("guilt", "shame", "anger"):
                    ep.resolved = True
                if (event.kind == "reassure" or "reassure" in tags_low) and ep.family in (
                    "fear",
                    "jealousy",
                    "shame",
                    "sadness",
                ):
                    ep.resolved = True

    # 2. Prior-moodiness directional bias:
    # Walking in deeply ashamed/sad turns ambiguous/hostile hits inward;
    # walking in already angry/irritated pushes them outward.
    prior_shame_sad = max(
        0.0, before["shame"] - FAMILY_BASELINES["shame"]
    ) + max(0.0, before["sadness"] - FAMILY_BASELINES["sadness"])
    prior_anger = max(0.0, before["anger"] - FAMILY_BASELINES["anger"])

    scaled: Dict[str, float] = dict(clean_raw)
    if prior_shame_sad >= 25.0 and scaled["anger"] > 0:
        shift = min(scaled["anger"] * 0.45, 18.0)
        scaled["anger"] -= shift
        scaled["shame"] += shift * 0.65
        scaled["sadness"] += shift * 0.45
    elif prior_anger >= 22.0 and (scaled["sadness"] > 0 or scaled["shame"] > 0):
        shift = min(scaled["sadness"] * 0.30, 12.0)
        scaled["sadness"] -= shift
        scaled["anger"] += shift * 0.85

    # 3. Vulnerability amplification, positive buffer cushion, & trait/memory calming resistance.
    trait_ids = _extract_trait_ids(player)
    trust_breached = bool(event.expectations) or ("betrayal" in event.tags) or (scaled["love"] <= -10.0)
    calming_resistance, _ = _derive_calming_resistance(trait_ids, recalled_memories, state)

    for fam in FAMILIES:
        d = scaled[fam]
        if abs(d) < 0.01:
            continue
        is_neg = EMOTION_PROFILES[fam]["is_negative"]
        if is_neg and d > 0:
            # Amplify by vulnerability_load.
            d *= 1.0 + vuln_load * 0.45
            # Positive buffer cushions small minor annoyances unless trust/expectation breached.
            if pos_buffer > 0 and not trust_breached and d < 22.0:
                cushion = pos_buffer * 10.0
                d = max(0.0, d - cushion)
            # Reinforcement history amplifies learned emotional escalation.
            reinf = state.reinforced_families.get(fam, 0.0)
            if reinf > 0:
                d *= 1.0 + min(0.30, reinf * 0.15)
        elif is_neg and d < 0:
            # Unresolved episodes / protective or vigilant traits resist quick calming.
            res = calming_resistance.get(fam, 0.0)
            if res > 0:
                d *= (1.0 - res)
        scaled[fam] = d

    # 4. Sparse 13x13 cross-emotion coupling matrix W.
    coupled: Dict[str, float] = dict(scaled)
    for src, delta in scaled.items():
        if delta <= 2.0:
            continue
        row = COUPLING_MATRIX.get(src)
        if not row:
            continue
        for tgt, ratio in row.items():
            # Do not double-suppress if the appraiser already explicitly shifted tgt in the same sign.
            existing = scaled.get(tgt, 0.0)
            add = delta * ratio
            if (existing * add) > 0:
                add *= 0.35
            coupled[tgt] = coupled.get(tgt, 0.0) + add

    # Apply coupled deltas to state.families with gentle saturation damping above 45
    # so multi-turn conversations build realistically instead of pegging straight to 99.9.
    for fam in FAMILIES:
        d_app = coupled[fam]
        cur_val = state.families[fam]
        if d_app > 0.0 and cur_val > 45.0:
            d_app *= max(0.22, (100.0 - cur_val) / 60.0)
            coupled[fam] = d_app
        state.families[fam] = max(0.0, min(100.0, cur_val + d_app))

    # 5. Suppression & Secondary Emotions derived from existing traits, memories, and witnesses.
    suppressed_families: List[str] = []
    secondary_triggered: List[str] = []
    secondary_records: List[Tuple[str, str, float, str]] = []  # (parent_fam, child_fam, delta, note)

    if explicit_suppress:
        dom_f, _ = dominant_family_and_expression(state.families)
        if dom_f != "neutral":
            suppressed_families.append(dom_f)

    # Distinguish true public-exposure witnesses from close confidants in a private huddle.
    rels = getattr(player, "relationships", None) or {}
    outside_witnesses = [
        w for w in (event.witnesses or [])
        if float((rels.get(w) or {}).get("closeness", 0.0) or 0.0) < 60.0
    ]
    is_exposure_event = bool({"insult", "betrayal", "exposure", "hid_mistake"} & tags_low)
    has_public_pressure = bool(outside_witnesses) or (bool(event.witnesses) and is_exposure_event)

    pers_low = str(getattr(player, "personality", "") or "").lower()
    mem_blob = " ".join(str(m.get("text", "") or "").lower() for m in recalled_memories)
    fear_tags = {str(t).lower() for t in (getattr(player, "fear_tags", None) or [])}

    is_composed_guard = bool(trait_ids & {"stoic", "composed", "guarded", "proud", "reserved"}) or any(
        w in pers_low for w in ("composed", "stoic", "armor", "sharp-tongued", "practical", "blunt")
    )
    is_guilt_honest = bool(trait_ids & {"honest", "guilt_prone", "people_pleaser", "anxious", "timid"}) or any(
        w in pers_low for w in ("apologetic", "timid", "eldest daughter", "reputation", "strict")
    )
    has_abandonment_wound = (
        any("abandon" in t for t in fear_tags)
        or any(k in mem_blob for k in ("abandon", "left behind", "left me", "stopped texting", "stranded"))
    )

    # (a) Stoic/composed/guarded character (or someone facing public exposure) clamps down on fear/sadness.
    # Fire at most one secondary shame chain per step so multiple negative families do not double-stack.
    secondary_fear_sad_fired = False
    for tf in ("fear", "sadness"):
        over = state.families[tf] - FAMILY_BASELINES[tf]
        if over >= 22.0 and (is_composed_guard or has_public_pressure):
            if tf not in suppressed_families and is_composed_guard:
                suppressed_families.append(tf)
            if not secondary_fear_sad_fired and coupled.get(tf, 0.0) >= 10.0 and (is_composed_guard or has_public_pressure):
                secondary_fear_sad_fired = True
                sec_shame = 12.0 if is_composed_guard else 8.0
                if state.families["shame"] > 50.0:
                    sec_shame *= max(0.25, (100.0 - state.families["shame"]) / 55.0)
                state.families["shame"] = min(100.0, state.families["shame"] + sec_shame)
                coupled["shame"] = coupled.get("shame", 0.0) + sec_shame
                reason = "composed/guarded trait" if is_composed_guard else "public exposure"
                secondary_triggered.append(f"{tf}->shame ({reason})")
                secondary_records.append((tf, "shame", sec_shame, f"hated showing {tf} under {reason}"))
                if is_composed_guard:
                    sec_ang = 7.0
                    state.families["anger"] = min(100.0, state.families["anger"] + sec_ang)
                    coupled["anger"] = coupled.get("anger", 0.0) + sec_ang
                    secondary_triggered.append(f"{tf}->anger ({reason})")
                    secondary_records.append((tf, "anger", sec_ang, f"defensive tension masking {tf}"))

    # (b) Guilt-prone / honest / strict-upbringing character turns raw anger or deception inward into guilt/shame.
    anger_over = state.families["anger"] - FAMILY_BASELINES["anger"]
    if anger_over >= 18.0 and coupled.get("anger", 0.0) >= 8.0 and is_guilt_honest and not is_composed_guard:
        if "anger" not in suppressed_families:
            suppressed_families.append("anger")
        state.families["guilt"] = min(100.0, state.families["guilt"] + 12.0)
        state.families["shame"] = min(100.0, state.families["shame"] + 10.0)
        coupled["guilt"] = coupled.get("guilt", 0.0) + 12.0
        coupled["shame"] = coupled.get("shame", 0.0) + 10.0
        secondary_triggered.append("anger->guilt (temperament/memories)")
        secondary_records.append(("anger", "guilt", 12.0, "felt uneasy about lashing out"))

    # (c) Lying / hiding in front of family or strict expectations triggers secondary guilt.
    if ("lied" in tags_low or "cover_lie" in tags_low or "hid_mistake" in tags_low) and is_guilt_honest:
        state.families["guilt"] = min(100.0, state.families["guilt"] + 16.0)
        coupled["guilt"] = coupled.get("guilt", 0.0) + 16.0
        secondary_triggered.append("cover_lie->guilt (honesty standard)")
        secondary_records.append(("shame", "guilt", 16.0, "hated having to lie to family"))

    # (d) Abandonment memory wound makes acute vulnerability/closeness co-activate fear.
    love_over = state.families["love"] - FAMILY_BASELINES["love"]
    if love_over >= 22.0 and coupled.get("love", 0.0) >= 8.0 and has_abandonment_wound:
        state.families["fear"] = min(100.0, state.families["fear"] + 14.0)
        coupled["fear"] = coupled.get("fear", 0.0) + 14.0
        secondary_triggered.append("love->fear (abandonment memory)")
        secondary_records.append(("love", "fear", 14.0, "closeness stirred old fear of being left behind"))

    # 5b. Per-target live emotion overlay (mirrors Player.felt_toward / bug-596).
    target_key = event.target_name or event.source_name
    if target_key and target_key != getattr(player, "name", None):
        tmap = state.target_families.setdefault(target_key, {})
        for fam in FAMILIES:
            if fam == "calm":
                continue
            delta_t = coupled.get(fam, 0.0)
            if abs(delta_t) >= 5.0:
                prev_t = float(tmap.get(fam, FAMILY_BASELINES[fam]))
                tmap[fam] = round(max(0.0, min(100.0, prev_t + delta_t)), 2)
        # Keep only targets with at least one family meaningfully away from baseline.
        active_t = {
            f: v for f, v in tmap.items() if abs(v - FAMILY_BASELINES[f]) >= 6.0
        }
        if active_t:
            state.target_families[target_key] = active_t
        else:
            state.target_families.pop(target_key, None)

    # 6. Update 8-channel Autonomic Body State (outside LLM control).
    state.autonomic = update_autonomic(
        state.autonomic,
        state.families,
        player,
        suppressed=bool(suppressed_families),
        exertion=event.exertion,
    )

    # 7. Emotional Overload check (DBT Handout 4 skills breakdown point).
    max_neg_over = max(
        (
            state.families[f] - FAMILY_BASELINES[f]
            for f in FAMILIES
            if EMOTION_PROFILES[f]["is_negative"]
        ),
        default=0.0,
    )
    auto_peak = max(
        state.autonomic.get("heart_rate", 0.0),
        state.autonomic.get("breathing", 0.0),
        state.autonomic.get("muscle_tension", 0.0),
    )
    peak_arousal = max(max_neg_over, auto_peak * 0.85)
    overloaded = peak_arousal > reg_cap

    if overloaded:
        state.overload_streak += 1
        # Sustained severe overload triggers protective emotional numbness/dissociation.
        if state.overload_streak >= 6 and peak_arousal >= 88.0:
            state.numbness_ticks = 3
            state.families["happiness"] = max(0.0, FAMILY_BASELINES["happiness"] - 25.0)
            state.families["love"] = max(0.0, FAMILY_BASELINES["love"] - 20.0)
    else:
        state.overload_streak = 0

    # 8. Update bounded Worksheet-4 causal episodes (max 6).
    # Calm returning toward steady state is not a rumination episode.
    top_shifted = sorted(
        (
            (coupled[f], f)
            for f in FAMILIES
            if f != "calm" and coupled[f] >= 10.0
        ),
        reverse=True,
    )
    primary_ep_id: Optional[str] = None
    mem_id = recalled_memories[0].get("id") if recalled_memories else None
    for idx, (delta_val, fam) in enumerate(top_shifted[:3]):
        ep_id = f"ep_{event.tick}_{fam}_{len(state.episodes) + idx + 1}"
        if idx == 0:
            primary_ep_id = ep_id
        state.episodes.append(
            EpisodeRecord(
                id=ep_id,
                tick=event.tick,
                family=fam,
                peak_delta=delta_val,
                target_name=target_key,
                prompting_event={
                    "kind": event.kind,
                    "summary": event.summary,
                    "source": event.source_name,
                    "witnesses": list(event.witnesses),
                    "memory_id": mem_id,
                },
                appraisal=gut_appraisal,
                urges=list(EMOTION_PROFILES[fam]["urges"][:3]),
                secondary_of=None,
                suppressed=(fam in suppressed_families),
                resolved=False,
                rumination_ticks=0,
            )
        )

    for parent_fam, sec_fam, sec_delta, note in secondary_records:
        ep_id = f"ep_{event.tick}_sec_{sec_fam}_{len(state.episodes) + 1}"
        state.episodes.append(
            EpisodeRecord(
                id=ep_id,
                tick=event.tick,
                family=sec_fam,
                peak_delta=sec_delta,
                target_name=target_key,
                prompting_event={
                    "kind": "secondary_emotion",
                    "summary": f"felt {parent_fam} and reacted to it",
                    "source": "self",
                    "witnesses": list(event.witnesses),
                    "memory_id": None,
                },
                appraisal=note,
                urges=list(EMOTION_PROFILES[sec_fam]["urges"][:3]),
                secondary_of=primary_ep_id,
                suppressed=(sec_fam in suppressed_families),
                resolved=False,
                rumination_ticks=0,
            )
        )

    if len(state.episodes) > MAX_ACTIVE_EPISODES:
        state.episodes = state.episodes[-MAX_ACTIVE_EPISODES:]

    # 9. Render embodied prompt, observer tells, skill penalties, and disposition tilts.
    dom_fam, portrait = dominant_family_and_expression(state.families)
    val, aro = valence_arousal(state.families)
    prompt_state = render_own_body_prompt(
        state,
        player,
        overloaded=overloaded,
        suppressed_families=suppressed_families,
    )
    obs_normal = render_observer_tells(
        state,
        player,
        lighting="normal",
        observer_insight=10,
        familiarity=0.2,
        overloaded=overloaded,
        suppressed_families=suppressed_families,
    )
    obs_dim = render_observer_tells(
        state,
        player,
        lighting="dim",
        observer_insight=10,
        familiarity=0.2,
        overloaded=overloaded,
        suppressed_families=suppressed_families,
    )
    obs_insight = render_observer_tells(
        state,
        player,
        lighting="normal",
        observer_insight=15,
        familiarity=0.8,
        overloaded=overloaded,
        suppressed_families=suppressed_families,
    )

    applied = {f: state.families[f] - before[f] for f in FAMILIES}
    meta = dict(metadata or {})
    meta["regulation_breakdown"] = reg_breakdown

    return MatrixStepResult(
        engine_name=engine_name,
        latency_ms=latency_ms,
        before_families=before,
        raw_deltas=clean_raw,
        applied_deltas=applied,
        after_families=dict(state.families),
        autonomic=dict(state.autonomic),
        vulnerability_load=vuln_load,
        vulnerability_factors=vuln_factors,
        positive_buffer=pos_buffer,
        regulation_capacity=reg_cap,
        peak_arousal=peak_arousal,
        overloaded=overloaded,
        suppressed_families=suppressed_families,
        secondary_triggered=secondary_triggered,
        dominant_family=dom_fam,
        portrait_expression=portrait,
        valence=val,
        arousal=aro,
        gut_appraisal=gut_appraisal,
        recalled_memories=[
            {"id": m.get("id"), "text": m.get("text", ""), "score": round(float(m.get("_score", 0.0)), 2)}
            for m in recalled_memories
        ],
        prompt_your_state=prompt_state,
        observer_tells_normal=obs_normal,
        observer_tells_dim=obs_dim,
        observer_tells_insight=obs_insight,
        skill_penalties=skill_check_penalties(state.autonomic, overloaded),
        disposition_tilts=_disposition_tilts(state.families, overloaded),
        episodes=[ep.to_dict() for ep in state.episodes],
        metadata=meta,
        target_families={k: dict(v) for k, v in state.target_families.items()},
    )


def apply_tick_decay(
    state: CharacterEmotionState,
    player: Any,
    ticks: int = 1,
) -> Dict[str, Any]:
    """Per-tick non-uniform decay, trait multipliers (apathetic), rumination throttling, and body inertia."""
    trait_ids = _extract_trait_ids(player)

    # Wire apathetic trait faster decay (currently described in data/library/traits/apathetic.json).
    trait_mult = 2.0 if "apathetic" in trait_ids else 1.0
    if "brooding" in trait_ids or "ruminative" in trait_ids:
        trait_mult *= 0.65

    _, decay_mult_map = _derive_calming_resistance(trait_ids, [], state)

    for _ in range(max(1, ticks)):
        if state.numbness_ticks > 0:
            state.numbness_ticks -= 1

        unresolved_fams = set()
        for ep in state.episodes:
            if not ep.resolved:
                ep.rumination_ticks += 1
                unresolved_fams.add(ep.family)

        for fam in FAMILIES:
            base = FAMILY_BASELINES[fam]
            cur = state.families[fam]
            rate = EMOTION_PROFILES[fam]["decay_per_tick"] * trait_mult
            if fam in unresolved_fams and cur > base:
                rate *= 0.50
            if fam in decay_mult_map and cur > base:
                rate *= decay_mult_map[fam]
            if cur > base:
                state.families[fam] = round(max(base, cur - rate), 2)
            elif cur < base:
                state.families[fam] = round(min(base, cur + rate), 2)

        # Drift per-target emotion overlays back toward baseline on the same decay curve.
        stale_targets: List[str] = []
        for tname, tfams in state.target_families.items():
            stale_fams: List[str] = []
            for fam, cur in tfams.items():
                base = FAMILY_BASELINES[fam]
                rate = EMOTION_PROFILES[fam]["decay_per_tick"] * trait_mult * 0.8
                if cur > base:
                    nv = round(max(base, cur - rate), 2)
                else:
                    nv = round(min(base, cur + rate), 2)
                tfams[fam] = nv
                if abs(nv - base) < 5.0:
                    stale_fams.append(fam)
            for sf in stale_fams:
                tfams.pop(sf, None)
            if not tfams:
                stale_targets.append(tname)
        for st_name in stale_targets:
            state.target_families.pop(st_name, None)

        # Autonomic body settles on its own physiological inertia curve.
        state.autonomic = tick_autonomic(state.autonomic, player)

        # Prune resolved episodes whose family returned near baseline.
        state.episodes = [
            ep
            for ep in state.episodes
            if not (ep.resolved and abs(state.families[ep.family] - FAMILY_BASELINES[ep.family]) < 6.0)
        ]

    dom_fam, portrait = dominant_family_and_expression(state.families)
    val, aro = valence_arousal(state.families)
    return {
        "families": {k: round(v, 1) for k, v in state.families.items()},
        "autonomic": {k: round(v, 1) for k, v in state.autonomic.items()},
        "dominant_family": dom_fam,
        "portrait_expression": portrait,
        "valence": round(val, 2),
        "arousal": round(aro, 2),
        "active_episodes": len(state.episodes),
        "numbness_ticks": state.numbness_ticks,
    }


def apply_observer_social_influence(
    observer_state: CharacterEmotionState,
    observer_player: Any,
    target_state: CharacterEmotionState,
    target_player: Any,
    *,
    closeness: float = 0.0,
    tick: int = 0,
) -> Dict[str, float]:
    """Handout 3 social communication loop: seeing another character's visible tells shifts observer affect.

    Example (Worksheet 2A): witnessing clear shame/guilt/sadness in someone you care
    about (non-hostile, closeness > 0) softens the observer's anger and nudges care.
    """
    raw_traits = getattr(observer_player, "traits", None) or {}
    obs_traits = set(raw_traits.keys()) if isinstance(raw_traits, dict) else {str(t) for t in raw_traits}
    hostile = "hostile" in obs_traits or closeness <= -25.0

    deltas: Dict[str, float] = {}
    t_shame = target_state.families["shame"] - FAMILY_BASELINES["shame"]
    t_guilt = target_state.families["guilt"] - FAMILY_BASELINES["guilt"]
    t_sad = target_state.families["sadness"] - FAMILY_BASELINES["sadness"]
    t_anger = target_state.families["anger"] - FAMILY_BASELINES["anger"]
    t_happy = target_state.families["happiness"] - FAMILY_BASELINES["happiness"]

    # Visible contrition/distress softens anger in non-hostile friends/roommates.
    if (t_shame >= 18.0 or t_guilt >= 18.0 or t_sad >= 22.0) and not hostile and closeness >= 10.0:
        if observer_state.families["anger"] > FAMILY_BASELINES["anger"] + 8.0:
            deltas["anger"] = -18.0
        deltas["love"] = deltas.get("love", 0.0) + 8.0
        deltas["calm"] = deltas.get("calm", 0.0) + 6.0

    # Visible hostility/rage unsettles cowardly or low-trust observers.
    if t_anger >= 30.0 and ("cowardly" in obs_traits or closeness < 15.0):
        deltas["fear"] = deltas.get("fear", 0.0) + (18.0 if "cowardly" in obs_traits else 10.0)
        deltas["calm"] = deltas.get("calm", 0.0) - 10.0

    # Bounded positive contagion among warm friends.
    if t_happy >= 25.0 and closeness >= 25.0 and not hostile:
        deltas["happiness"] = deltas.get("happiness", 0.0) + 8.0

    for fam, d in deltas.items():
        observer_state.families[fam] = round(
            max(0.0, min(100.0, observer_state.families[fam] + d)), 2
        )
    if deltas:
        observer_state.autonomic = update_autonomic(
            observer_state.autonomic, observer_state.families, observer_player
        )
    return deltas
