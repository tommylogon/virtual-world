"""Associative multi-facet memory retrieval (task-908).

Replaces flat single-query retrieval with structured perceptual cues:
- Scene actors (player IDs and display names present in the room)
- Visible items and containers in the room
- Carried inventory items
- Spoken dialogue (recent hearing lines) and own last thought
- Bodily need cues (need:food, need:drink, need:rest)
- Current emotion / affect
- Temporal validity window (invalid_at <= current_tick drops from active recall)
- Multi-facet intersection boost (e.g. Jake present + olives mentioned)
- Zero-padding prompt lane partitioning (no fake top-3 when score is 0)

@module engine/memory_retrieval
@contributes retrieve_associative_memories, score_memory, extract_cues
@docs docs/virtualWorld/memory_architecture.md
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from engine import memory_dynamics

logger = logging.getLogger(__name__)

STOPWORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "of", "to", "for", "and", "or", "but",
    "if", "so", "then", "there", "their", "them", "they", "this", "that", "with",
    "from", "just", "now", "really", "about", "when", "what", "where", "how", "why",
    "is", "are", "was", "were", "be", "been", "it", "its", "by", "my", "me", "i",
    "we", "you", "your", "not", "no", "yes", "oh", "well", "much", "very", "too",
    "will", "would", "can", "could", "shall", "should", "am", "get", "got", "go",
    "he", "she", "him", "her", "his", "hers", "said", "says", "like", "one", "two"
}

NEED_TAG_MAP: Dict[str, Set[str]] = {
    "need:food": {"food", "snack", "eat", "eating", "meal", "cook", "cooking", "hunger", "hungry", "rations", "bread", "fruit", "meat", "pizza", "berries", "apple", "takis"},
    "need:drink": {"drink", "drinking", "water", "beverage", "thirst", "thirsty", "fountain", "stream", "river", "bottle", "cup", "tea", "potion"},
    "need:rest": {"rest", "sleep", "sleeping", "bed", "fatigue", "tired", "exhausted", "bench", "cot", "bunk"},
}


def normalize_tokens(text: Any) -> Set[str]:
    """Extract lowercase alphanumeric tokens, stripping punctuation."""
    return set(re.findall(r"[a-z0-9']+", str(text or "").lower()))


def extract_cues(data: Dict[str, Any], world: Any = None) -> Dict[str, Any]:
    """Assemble structured situation cues from request payload and world context."""
    actor_ids: Set[str] = set()
    actor_names: Set[str] = set()
    item_ids: Set[str] = set()
    item_names: Set[str] = set()
    dialogue_tokens: Set[str] = set()
    needs: Set[str] = set()

    # Raw actors
    for a in (data.get("actors") or []):
        s = str(a).strip().lower()
        if not s:
            continue
        if s.startswith("player_"):
            actor_ids.add(s)
        else:
            actor_names.add(s)
            actor_ids.add(f"player_{s.replace(' ', '_')}")

    # Raw items
    for it in (data.get("items") or []):
        s = str(it).strip().lower()
        if not s:
            continue
        if s.startswith("item_"):
            item_ids.add(s)
        else:
            item_names.add(s)
            item_ids.add(f"item_{s.replace(' ', '_')}")

    # Carried inventory
    for inv in (data.get("inventory") or []):
        s = str(inv).strip().lower()
        if not s:
            continue
        if s.startswith("item_"):
            item_ids.add(s)
        else:
            item_names.add(s)
            item_ids.add(f"item_{s.replace(' ', '_')}")

    # Dialogue lines + last thought
    dialogue_raw = list(data.get("dialogue") or [])
    if data.get("last_thought"):
        dialogue_raw.append(str(data["last_thought"]))
    if data.get("query"):
        dialogue_raw.append(str(data["query"]))

    for line in dialogue_raw:
        tokens = normalize_tokens(line) - STOPWORDS
        dialogue_tokens.update(tokens)

    # Needs
    for n in (data.get("needs") or []):
        ns = str(n).strip().lower()
        if ns:
            needs.add(ns if ns.startswith("need:") else f"need:{ns}")

    # Explicit entity IDs passed by caller
    for eid in (data.get("entities") or []):
        s = str(eid).strip().lower()
        if s.startswith("player_"):
            actor_ids.add(s)
        elif s.startswith("item_"):
            item_ids.add(s)
        elif s:
            actor_ids.add(s)

    # Emotion
    emotion = str(data.get("emotion") or "").strip().lower()

    # Area ID
    area_id = str(data.get("current_area_id") or data.get("area_id") or "").strip().lower()

    return {
        "actor_ids": actor_ids,
        "actor_names": actor_names,
        "item_ids": item_ids,
        "item_names": item_names,
        "dialogue_tokens": dialogue_tokens,
        "needs": needs,
        "emotion": emotion,
        "area_id": area_id,
        "raw_query": str(data.get("query") or "").strip(),
    }


def is_active_memory(m: Dict[str, Any], tick: int) -> Tuple[bool, str]:
    """Check whether a memory is currently active and valid.

    Returns (is_active, rejection_reason).
    """
    text = str(m.get("text") or "").strip()
    if not text:
        return False, "empty_text"

    if m.get("superseded_by"):
        return False, f"superseded_by_{m['superseded_by']}"

    # Temporal invalidation window (Graphiti-style invalid_at)
    inv_at = m.get("invalid_at")
    if inv_at is not None:
        try:
            if int(inv_at) <= tick:
                return False, f"invalid_at_tick_{inv_at}"
        except (TypeError, ValueError):
            pass

    for s in (m.get("suppressions") or []):
        until = s.get("until_tick")
        try:
            if until is None or int(until or 0) > tick:
                return False, "suppressed"
        except (TypeError, ValueError):
            return False, "suppressed"

    return True, "active"


def score_memory(
    memory: Dict[str, Any],
    cues: Dict[str, Any],
    current_tick: int,
    half_life: float = 300.0,
) -> Tuple[float, Dict[str, Any]]:
    """Score a single memory against multi-facet situation cues.

    Returns (total_score, explanation_breakdown).
    """
    active, reason = is_active_memory(memory, current_tick)
    if not active:
        return 0.0, {"active": False, "reason": reason}

    mem_tokens = normalize_tokens(memory.get("text", ""))
    mem_tags = {str(t).lower() for t in (memory.get("tags") or []) if t}
    mem_eids = {str(e).lower() for e in (memory.get("entity_ids") or []) if e}

    breakdown: Dict[str, Any] = {
        "active": True,
        "facets_hit": [],
        "keyword_score": 0.0,
        "entity_score": 0.0,
        "need_score": 0.0,
        "emotion_score": 0.0,
        "intersection_boost": 0.0,
        "importance_weight": 0.0,
        "recency_weight": 0.0,
    }

    # 1. Dialogue / Keyword overlap
    dialogue_cues = cues.get("dialogue_tokens") or set()
    matched_words = (mem_tokens & dialogue_cues) - STOPWORDS
    kw_score = 0.0
    if dialogue_cues:
        overlap = len(matched_words)
        kw_score = (overlap / max(1, min(len(dialogue_cues), 8))) * 3.0
    breakdown["keyword_score"] = round(kw_score, 3)
    breakdown["matched_words"] = sorted(matched_words)
    if matched_words:
        breakdown["facets_hit"].append("dialogue")

    # 2. Entity match: Scene actors and items
    entity_score = 0.0
    matched_entities: List[str] = []

    # Direct ID match
    actor_ids = cues.get("actor_ids") or set()
    matched_actors = mem_eids & actor_ids
    if matched_actors:
        entity_score += 2.5 * len(matched_actors)
        matched_entities.extend(matched_actors)
        breakdown["facets_hit"].append("actor")

    # Actor name match in text/tags (fallback for unlinked mentions)
    actor_names = cues.get("actor_names") or set()
    for aname in actor_names:
        aname_tokens = normalize_tokens(aname)
        if aname_tokens and aname_tokens.issubset(mem_tokens):
            if "actor" not in breakdown["facets_hit"]:
                entity_score += 2.0
                matched_entities.append(aname)
                breakdown["facets_hit"].append("actor")

    # Visible items match
    item_ids = cues.get("item_ids") or set()
    matched_items = mem_eids & item_ids
    if matched_items:
        entity_score += 2.0 * len(matched_items)
        matched_entities.extend(matched_items)
        breakdown["facets_hit"].append("item")

    item_names = cues.get("item_names") or set()
    for iname in item_names:
        iname_tokens = normalize_tokens(iname)
        if iname_tokens and iname_tokens.issubset(mem_tokens):
            if "item" not in breakdown["facets_hit"]:
                entity_score += 1.5
                matched_entities.append(iname)
                breakdown["facets_hit"].append("item")

    # Current area match
    area_id = cues.get("area_id")
    if area_id and area_id in mem_eids:
        entity_score += 1.5
        matched_entities.append(area_id)
        breakdown["facets_hit"].append("area")

    breakdown["entity_score"] = round(entity_score, 3)
    breakdown["matched_entities"] = matched_entities

    # 3. Bodily need probe
    need_score = 0.0
    matched_needs: List[str] = []
    active_needs = cues.get("needs") or set()
    for need_key in active_needs:
        vocabulary = NEED_TAG_MAP.get(need_key, set())
        # Tag match is highest signal
        if mem_tags & vocabulary:
            need_score += 3.0
            matched_needs.append(need_key)
            breakdown["facets_hit"].append("need")
            break
        # Text token match
        elif mem_tokens & vocabulary:
            need_score += 2.0
            matched_needs.append(need_key)
            breakdown["facets_hit"].append("need")
            break
    breakdown["need_score"] = round(need_score, 3)
    breakdown["matched_needs"] = matched_needs

    # 4. Emotion congruence
    emotion_score = 0.0
    cue_emotion = cues.get("emotion")
    if cue_emotion:
        mem_emotions = []
        if isinstance(memory.get("emotion"), dict) and memory["emotion"].get("label"):
            mem_emotions.append(str(memory["emotion"]["label"]).lower())
        for me in (memory.get("memory_emotions") or []):
            if isinstance(me, dict) and me.get("label"):
                mem_emotions.append(str(me["label"]).lower())
        if cue_emotion in mem_emotions or cue_emotion in mem_tags:
            emotion_score += 1.5
            breakdown["facets_hit"].append("emotion")
    breakdown["emotion_score"] = round(emotion_score, 3)

    # 5. Multi-facet intersection boost
    # A memory that hits multiple distinct buckets (e.g. Actor + Dialogue)
    # gets an exponential lift over single-facet noise.
    unique_facets = set(breakdown["facets_hit"])
    intersection_boost = 0.0
    if len(unique_facets) >= 2:
        intersection_boost = (len(unique_facets) - 1) * 2.5
    breakdown["intersection_boost"] = round(intersection_boost, 3)

    # 6. Recency (exponential half-life)
    try:
        mem_tick = int(memory.get("tick", 0) or 0)
    except (TypeError, ValueError):
        mem_tick = 0
    age = max(0, current_tick - mem_tick)
    recency = (0.5 ** (age / half_life)) * 2.0 if half_life > 0 else 0.0
    breakdown["recency_weight"] = round(recency, 3)

    # 7. Effective importance (activation * confidence)
    memory_dynamics.ensure_dynamics(memory)
    eff_imp = memory_dynamics.effective_importance(memory) / 10.0
    importance_weight = eff_imp * 2.0
    breakdown["importance_weight"] = round(importance_weight, 3)

    # Total score calculation:
    # Situational relevance (cues present in the room/dialogue/needs/emotion)
    # is the gating trigger. Pure recency and routine importance do not surface
    # un-cued memories unless importance is exceptionally high (trauma/core identity >= 9).
    situational_score = kw_score + entity_score + need_score + emotion_score + intersection_boost
    breakdown["situational_score"] = round(situational_score, 3)
    base_salience = (recency * 0.5) + (importance_weight * 0.5)

    if situational_score > 0:
        total = situational_score + base_salience
    else:
        # Idle drift: un-cued memories fade to near-zero unless importance >= 9
        total = base_salience if eff_imp >= 0.9 else (base_salience * 0.2)

    breakdown["total_score"] = round(total, 3)
    return total, breakdown


def is_open_question_match(memory: Dict[str, Any], cues: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Determine if an open question's watch targets match current perception."""
    cat = memory.get("category") or memory_dynamics.category_for(memory)
    if cat != memory_dynamics.QUESTION and str(memory.get("type", "")) != "question":
        return False, []

    # Answered questions do not trigger active suspicion
    if memory.get("answered_by") or memory.get("status") == "resolved":
        return False, []

    # Watch references can be entity IDs, concept tags, or person names
    watch_refs = set()
    for r in (memory.get("watch_refs") or []):
        watch_refs.add(str(r).lower())
    for a in (memory.get("about") or []):
        watch_refs.add(str(a).lower())
    for t in (memory.get("tags") or []):
        watch_refs.add(str(t).lower())

    if not watch_refs:
        # Fallback to tokens in question text
        watch_refs = normalize_tokens(memory.get("text", "")) - STOPWORDS

    matched: List[str] = []
    # Match against active cues
    actor_ids = {a.lower() for a in cues.get("actor_ids") or []}
    actor_names = {a.lower() for a in cues.get("actor_names") or []}
    item_ids = {i.lower() for i in cues.get("item_ids") or []}
    item_names = {i.lower() for i in cues.get("item_names") or []}
    dialogue = cues.get("dialogue_tokens") or set()

    for ref in watch_refs:
        if ref in actor_ids or ref in actor_names:
            matched.append(ref)
        elif ref in item_ids or ref in item_names:
            matched.append(ref)
        elif ref in dialogue:
            matched.append(ref)
        elif ref.startswith("concept:") and ref[8:] in dialogue:
            matched.append(ref)
        elif ref.startswith("item:") and ref[5:] in item_names:
            matched.append(ref)

    return len(matched) > 0, matched


def retrieve_associative_memories(
    player: Any,
    payload: Dict[str, Any],
    world: Any = None,
    tick: Optional[int] = None,
    max_results: int = 6,
    min_score: float = 1.2,
    explain: bool = False,
    do_reinforce: bool = True,
) -> Dict[str, Any]:
    """Execute associative retrieval 3.0 across structured situation cues.

    Partitions memories into clean prompt lanes with zero fake padding:
    - lane_associative: 0 to 6 scored associative matches above min_score
    - lane_questions: 0 to 2 open questions matching active perception tripwires
    - lane_beliefs: guaranteed seat time for conclusions/beliefs matching entities
    """
    memories: List[Dict[str, Any]] = list(getattr(player, "memories", []) or [])
    if not memories:
        return {
            "memories": [],
            "lanes": {
                "associative": [],
                "open_questions": [],
                "beliefs": [],
            },
            "stats": {"total_candidates": 0, "recalled_count": 0},
        }

    current_tick = int(tick if tick is not None else getattr(world, "time_ticks", 0) or 0)
    cues = extract_cues(payload, world=world)

    scored_candidates: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
    open_questions: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for m in memories:
        # Check open question category first
        is_q, q_matches = is_open_question_match(m, cues)
        if is_q:
            q_entry = dict(m)
            q_entry["matched_refs"] = q_matches
            open_questions.append(q_entry)
            continue

        score, breakdown = score_memory(m, cues, current_tick)
        if not breakdown.get("active"):
            if explain:
                rejected.append({"id": m.get("id"), "text": m.get("text", "")[:60], "reason": breakdown.get("reason")})
            continue

        # Zero-padding floor: must clear min_score
        if score >= min_score:
            scored_candidates.append((score, m, breakdown))
        elif explain:
            rejected.append({"id": m.get("id"), "text": m.get("text", "")[:60], "score": round(score, 3), "reason": "below_min_score"})

    # Sort candidates by total score descending, then recency
    scored_candidates.sort(key=lambda x: (x[0], int(x[1].get("tick", 0) or 0)), reverse=True)

    # Lane 1: Associative recall (0..max_results, no forced top-3 padding)
    picked_ids: Set[str] = set()
    associative_lane: List[Dict[str, Any]] = []

    for s, m, b in scored_candidates[:max_results]:
        entry = dict(m)
        entry["score"] = round(s, 3)
        if explain:
            entry["explanation"] = b
        associative_lane.append(entry)
        picked_ids.add(str(entry.get("id")))

    # Lane 2: Belief seat-time guarantee (from task-690)
    # If the character holds strong beliefs about the active actors, ensure they get seat time
    beliefs_lane: List[Dict[str, Any]] = []
    active_actor_ids = cues.get("actor_ids") or set()
    if active_actor_ids:
        for s, m, b in scored_candidates:
            if str(m.get("id")) in picked_ids:
                continue
            cat = m.get("category") or memory_dynamics.category_for(m)
            if cat in (memory_dynamics.BELIEF, memory_dynamics.SOCIAL):
                eids = {str(e).lower() for e in (m.get("entity_ids") or [])}
                if eids & active_actor_ids:
                    entry = dict(m)
                    entry["score"] = round(s, 3)
                    if explain:
                        entry["explanation"] = b
                    beliefs_lane.append(entry)
                    picked_ids.add(str(entry.get("id")))
                    if len(beliefs_lane) >= 2:
                        break

    # Limit open questions to top 2
    active_questions = open_questions[:2]

    # Reinforce recalled memories on write path
    if do_reinforce:
        all_recalled = associative_lane + beliefs_lane
        for r in all_recalled:
            mid = r.get("id")
            stored = next((orig for orig in memories if orig.get("id") == mid), None)
            if stored is not None:
                memory_dynamics.reinforce(stored, tick=current_tick)

    # Flat memories list for backward compatibility with existing consumers
    combined_memories = associative_lane + beliefs_lane

    result: Dict[str, Any] = {
        "memories": combined_memories,
        "lanes": {
            "associative": associative_lane,
            "beliefs": beliefs_lane,
            "open_questions": active_questions,
        },
        "stats": {
            "total_candidates": len(memories),
            "recalled_count": len(combined_memories),
            "open_questions_count": len(active_questions),
        },
    }

    if explain:
        result["rejected"] = rejected[:10]
        result["cues"] = {
            "actors": list(cues["actor_ids"]),
            "items": list(cues["item_ids"]),
            "needs": list(cues["needs"]),
            "dialogue_tokens": list(cues["dialogue_tokens"])[:15],
            "area_id": cues["area_id"],
        }

    return result
