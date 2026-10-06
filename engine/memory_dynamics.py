"""Memory dynamics (task-685): the arithmetic that makes memories do things.

@module memory_dynamics
@contributes ensure_dynamics defaults, effective_importance scoring, reinforcement, activation decay with per-memory resistance, contradiction linking, consolidation
@powers Memory — what characters remember, and when they reflect on it
@docs docs/virtualWorld/AI & Narration/Memory Dynamics.md

``Player.memories[]`` entries gain optional dynamics fields — ``category``,
``activation``, ``confidence``, ``reinforcements``, ``last_recalled_tick``,
``reflection_depth``, ``source_memory_ids``, ``contradicts`` — and this module
owns every mutation of them. The fields are additive and defaulted lazily by
:func:`ensure_dynamics`, so a save from any era loads, recalls and re-saves
correctly (serialization round-trips the list verbatim).

What each function is for:

- :func:`ensure_dynamics` — fill missing dynamics fields in place; the only
  place defaults live.
- :func:`effective_importance` — the derived scorer (importance modulated by
  activation and confidence). Computed, never persisted.
- :func:`reinforce` — stamp recall/re-encounter; bounded and idempotent where
  the old "+1 importance" ratchet was neither.
- :func:`decay_resistance` / :func:`apply_decay` — non-uniform decay of
  ``activation``; removal only for unimportant, unreinforced memories.
- :func:`detect_contradiction` — link assert/deny pairs; marks, never resolves.
- :func:`consolidate` — compress stale low-importance same-entity episodes
  into one semantic trace memory.

Nothing here calls an LLM and nothing here knows about the graph.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional

# ── categories ───────────────────────────────────────────────────────────
EPISODIC = "episodic"      # things that happened
SEMANTIC = "semantic"      # generalized knowledge / consolidation traces
PROCEDURAL = "procedural"  # how to behave; expectations of oneself
SOCIAL = "social"          # about a person (rel:<name> tag convention)
BELIEF = "belief"          # a conclusion the character holds; may be wrong

#: Surface ``type`` -> memory ``category``. Types not listed are episodic.
CATEGORY_FOR_TYPE: Dict[str, str] = {
    "reflection": BELIEF,
    "belief": BELIEF,
    "expectation": PROCEDURAL,
    "procedure": PROCEDURAL,
}

#: Sources whose memories never decay (authored knowledge the character
#: was told) — shared with AgentMind, which used to own these constants.
NON_DECAYING_SOURCES = ("preconceived",)
#: Sources that fade at half rate: earned on-screen, summarised off-screen.
HALF_DECAY_SOURCES = ("background",)

#: A memory whose activation decays below this is a removal candidate
#: (and only removed if :func:`_removable` agrees).
ACTIVATION_FLOOR = 0.01

#: runtime_config keys owned by this module.
DECAY_RATE_KEY = "memory.decay_per_tick"
CONSOLIDATE_KEY = "memory.consolidate"

_NEGATION_WORDS = {
    "never", "not", "no", "didn't", "didnt", "don't", "dont", "doesn't",
    "doesnt", "isn't", "isnt", "aren't", "arent", "wasn't", "wasnt",
    "weren't", "werent", "won't", "wont", "can't", "cant", "couldn't",
    "couldnt", "denied", "denies", "deny", "denying", "lied", "lying",
    "longer",
}

#: Words that never count as shared content between two memories.
_CONTENT_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "to", "of",
    "in", "on", "at", "by", "for", "with", "from", "about", "as", "is",
    "are", "was", "were", "be", "been", "being", "am", "do", "does", "did",
    "have", "has", "had", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "it", "its", "they", "them", "their", "this", "that",
    "these", "those", "there", "here", "what", "when", "where", "how",
    "why", "who", "which", "again", "just", "very", "really", "some",
    "any", "all", "her", "his", "him", "she", "he",
} | _NEGATION_WORDS

_WORD_RE = re.compile(r"[a-z0-9']+")


# ── category ─────────────────────────────────────────────────────────────
def category_for(memory: Dict[str, Any]) -> str:
    """The memory's category, derived from ``type`` and tags when absent.

    ``rel:<name>`` tags make a memory social (the derive.py convention), but
    never override a more specific kind: a reflection about a person is a
    belief, not merely social.
    """
    explicit = memory.get("category")
    if explicit:
        return str(explicit)
    mapped = CATEGORY_FOR_TYPE.get(str(memory.get("type", "")), EPISODIC)
    if mapped is EPISODIC:
        if any(str(t).lower().startswith("rel:")
               for t in (memory.get("tags") or [])):
            return SOCIAL
    return mapped


# ── defaults ─────────────────────────────────────────────────────────────
def ensure_dynamics(memory: Dict[str, Any]) -> Dict[str, Any]:
    """Fill missing dynamics fields in place; returns the memory.

    Idempotent and tolerant: only *absent* fields are defaulted, so an entry
    written by an older version of the engine (or by hand in the editor)
    picks up exactly what it lacks.
    """
    memory.setdefault("category", category_for(memory))
    memory.setdefault("activation", 1.0)
    if memory.get("confidence") is None:
        source = str(memory.get("source", ""))
        memory["confidence"] = 1.0 if source in ("manual", "preconceived") else 0.7
    memory.setdefault("reinforcements", 0)
    memory.setdefault("last_recalled_tick", None)
    memory.setdefault("source_memory_ids", [])
    memory.setdefault("contradicts", [])
    if memory.get("reflection_depth") is None:
        # A pre-dynamics reflection was already a first-order conclusion.
        memory["reflection_depth"] = 1 if memory.get("type") == "reflection" else 0
    return memory


# ── scoring ──────────────────────────────────────────────────────────────
def effective_importance(memory: Dict[str, Any]) -> float:
    """Base importance modulated by how available and how sure we are.

    ``importance × (0.6 + 0.4×activation) × (0.75 + 0.25×confidence)`` — a
    faded memory presses less; a doubted memory weighs less. Field-less
    memories (old saves) score exactly their base importance.
    """
    importance = float(memory.get("importance", 5) or 5)
    activation = _unit(memory.get("activation", 1.0))
    confidence = _unit(memory.get("confidence", 1.0))
    return importance * (0.6 + 0.4 * activation) * (0.75 + 0.25 * confidence)


def _unit(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 1.0


# ── reinforcement ────────────────────────────────────────────────────────
def reinforce(memory: Dict[str, Any], tick: Optional[int] = None,
              activation_boost: float = 0.15,
              confidence_boost: float = 0.02) -> None:
    """Stamp one act of recall or re-encounter onto a memory.

    Thinking about something keeps it available: activation rises, confidence
    creeps up, and the count of reinforcements grows. All bounded; calling
    twice is twice the stamp, never a state corruption.
    """
    ensure_dynamics(memory)
    memory["reinforcements"] = int(memory.get("reinforcements", 0)) + 1
    memory["activation"] = round(min(1.0, _unit(memory.get("activation")) + activation_boost), 4)
    memory["confidence"] = round(min(1.0, _unit(memory.get("confidence")) + confidence_boost), 4)
    if tick is not None:
        memory["last_recalled_tick"] = int(tick)


def reinforce_all(memories: Iterable[Dict[str, Any]], tick: Optional[int] = None) -> None:
    """Reinforce every memory in ``memories`` (the retrieval-path helper)."""
    for memory in memories:
        reinforce(memory, tick=tick)


# ── decay ────────────────────────────────────────────────────────────────
def decay_resistance(memory: Dict[str, Any]) -> float:
    """How slowly this memory fades, as a multiplier on the decay step.

    The father's-death clause: important, emotionally encoded, repeated and
    concluded memories resist decay; an ordinary breakfast does not.
    """
    ensure_dynamics(memory)
    resistance = 1.0
    importance = float(memory.get("importance", 5) or 5)
    if importance >= 8:
        resistance *= 0.4
    elif importance >= 6:
        resistance *= 0.7
    emotions = list(memory.get("memory_emotions") or [])
    if memory.get("emotion"):
        emotions.append(memory["emotion"])
    for emotion in emotions:
        try:
            if float((emotion or {}).get("intensity", 0) or 0) >= 7:
                resistance *= 0.6
                break
        except (TypeError, ValueError):
            continue
    resistance *= 1.0 - 0.1 * min(int(memory.get("reinforcements", 0) or 0), 6)
    if memory.get("category") in (SEMANTIC, BELIEF, PROCEDURAL):
        resistance *= 0.3
    return max(0.05, resistance)


def _removable(memory: Dict[str, Any]) -> bool:
    """Decay may delete only what nothing would miss."""
    if str(memory.get("source", "")) in ("manual", "preconceived"):
        return False
    if float(memory.get("importance", 5) or 5) >= 6:
        return False
    if int(memory.get("reinforcements", 0) or 0) > 0:
        return False
    return True


def apply_decay(player, rate: float, tick: Optional[int] = None) -> int:
    """Fade every memory's activation by ``rate`` per call; return 0.

    One writer for activation decay. Preconceived memories never decay;
    background memories at half rate; everything else scaled by
    :func:`decay_resistance`.

    **Activation is a recall signal, not a lifespan.** Decay lowers how likely a
    memory is to be recalled; it never removes one. Memories are kept for life —
    nothing is forgotten, at any floor. (The former removal-at-floor behaviour
    was removed by request, 2026-10-06; it matches the intent of task-707.)

    Returns 0; the return value is kept only so existing callers that expected a
    "removed count" keep working.

    Note: this deliberately decays ``activation`` and not
    ``salience_override`` — the turn reset zeroes salience_override every
    turn, which used to erase trait-driven decay before it could compound.
    """
    if rate <= 0:
        return 0
    for memory in list(getattr(player, "memories", []) or []):
        ensure_dynamics(memory)
        source = str(memory.get("source", ""))
        if source in NON_DECAYING_SOURCES:
            continue
        step = rate * (0.5 if source in HALF_DECAY_SOURCES else 1.0)
        step *= decay_resistance(memory)
        memory["activation"] = round(max(0.0, _unit(memory.get("activation")) - step), 4)
    return 0


def _forget_index(player, memory_id: Optional[str]) -> None:
    """Drop a forgotten memory's observation-index entries, if any."""
    index = getattr(player, "memory_index", None)
    if not isinstance(index, dict) or not memory_id:
        return
    for subject, mid in list(index.items()):
        if mid == memory_id:
            index.pop(subject, None)


# ── contradiction ────────────────────────────────────────────────────────
def _content_tokens(text: str) -> set:
    """Lowercase content words: stopwords and negation markers excluded."""
    return {t for t in _WORD_RE.findall(str(text or "").lower())
            if t not in _CONTENT_STOPWORDS}


def _has_negation(text: str) -> bool:
    tokens = set(_WORD_RE.findall(str(text or "").lower()))
    return bool(tokens & _NEGATION_WORDS)


#: First-person affect statements ("I do not trust Anna…") express an
#: attitude, not a factual claim, so they never take part in factual
#: contradiction linking — the derive.py sentiment dimensions are what
#: handles conflicting feelings.
_SENTIMENT_VERBS = {
    "trust", "distrust", "like", "dislike", "love", "hate", "fear",
    "doubt", "admire", "respect", "despise", "adore", "loathe",
}


def _is_attitude_statement(text: str) -> bool:
    tokens = _WORD_RE.findall(str(text or "").lower())
    return bool(tokens) and tokens[0] == "i" and any(t in _SENTIMENT_VERBS for t in tokens)


def link(a: Dict[str, Any], b: Dict[str, Any]) -> None:
    """Record a contradicts link between two memories, symmetrically and idempotently."""
    a_id, b_id = a.get("id"), b.get("id")
    if not a_id or not b_id or a_id == b_id:
        return
    a.setdefault("contradicts", [])
    b.setdefault("contradicts", [])
    if b_id not in a["contradicts"]:
        a["contradicts"].append(b_id)
    if a_id not in b["contradicts"]:
        b["contradicts"].append(a_id)


def detect_contradiction(new_memory: Dict[str, Any],
                         pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Link ``new_memory`` to pool memories it asserts the opposite of.

    Conservative by construction — a link requires ALL of:
      * shared entity (``entity_ids`` overlap),
      * shared content (≥ 2 content words in common, or Jaccard ≥ 0.4),
      * negation asymmetry (one side asserts what the other denies).

    The older memory's confidence drops ×0.9 per link. Nothing is resolved,
    deleted or rewritten; the editor can remove a wrong link.
    Returns the list of memories newly linked to ``new_memory``.
    """
    ensure_dynamics(new_memory)
    new_entities = {str(e) for e in (new_memory.get("entity_ids") or []) if e}
    if not new_entities:
        return []
    new_tokens = _content_tokens(new_memory.get("text", ""))
    if not new_tokens:
        return []
    new_text = str(new_memory.get("text", ""))
    new_negated = _has_negation(new_text)
    new_is_attitude = _is_attitude_statement(new_text)
    linked: List[Dict[str, Any]] = []
    for other in pool:
        if other is new_memory:
            continue
        other_id = other.get("id")
        if not other_id or other_id == new_memory.get("id"):
            continue
        if not new_entities & {str(e) for e in (other.get("entity_ids") or []) if e}:
            continue
        other_text = str(other.get("text", ""))
        # an attitude never contradicts a fact, and two attitudes have the
        # sentiment dimensions — not this linker
        if new_is_attitude or _is_attitude_statement(other_text):
            continue
        other_tokens = _content_tokens(other_text)
        if not other_tokens:
            continue
        shared = len(new_tokens & other_tokens)
        union = len(new_tokens | other_tokens)
        jaccard = shared / union if union else 0.0
        if shared < 2 and jaccard < 0.4:
            continue
        if _has_negation(other_text) == new_negated:
            continue  # both assert or both deny — not a contradiction
        link(new_memory, other)
        other["confidence"] = round(max(0.05, _unit(other.get("confidence")) * 0.9), 4)
        linked.append(other)
    return linked


# ── consolidation ────────────────────────────────────────────────────────
def consolidation_pressure(player) -> bool:
    """True when the store is crowded enough to warrant consolidation."""
    try:
        from player import MEMORY_LIMIT_KEY
        from engine.runtime_config import config
        limit = int(config.get(MEMORY_LIMIT_KEY, 0) or 0)
    except Exception:
        return False
    if limit <= 0:
        return False
    return len(getattr(player, "memories", []) or []) >= int(limit * 0.8)


def consolidate(player, tick: Optional[int] = None, min_group: int = 3,
                max_importance: float = 4.0) -> Dict[str, int]:
    """Fold stale, low-importance, same-entity episodes into trace memories.

    The deterministic half of "50 episodes → 8 episodes → 3 beliefs" (the LLM's
    reflect() does the belief half). A group is ≥ ``min_group`` episodic
    memories that share a primary entity, are old (at least 100 ticks),
    unimportant (< ``max_importance``), unreinforced, and not observation
    memories (live beliefs refresh in place; they are not episodes).
    Each group becomes one ``semantic`` trace memory whose
    ``source_memory_ids`` records exactly what was folded.

    Returns ``{"groups": G, "folded": F}``.
    """
    memories = getattr(player, "memories", []) or []
    current_tick = int(tick or 0)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for memory in memories:
        ensure_dynamics(memory)
        if memory.get("category") != EPISODIC:
            continue
        if str(memory.get("source", "")) in ("manual", "preconceived"):
            continue
        if memory.get("type") == "observation" or memory.get("kind"):
            continue
        if float(memory.get("importance", 5) or 5) >= max_importance:
            continue
        if int(memory.get("reinforcements", 0) or 0) > 0:
            continue
        if current_tick - int(memory.get("tick", 0) or 0) < 100:
            continue
        entities = [str(e) for e in (memory.get("entity_ids") or []) if e]
        key = entities[0] if entities else "_unplaced"
        groups.setdefault(key, []).append(memory)

    folded = 0
    traces = 0
    for key, members in groups.items():
        if len(members) < min_group:
            continue
        members.sort(key=lambda m: int(m.get("tick", 0) or 0))
        first_tick = int(members[0].get("tick", 0) or 0)
        last_tick = int(members[-1].get("tick", 0) or 0)
        label = key if key != "_unplaced" else "the world"
        trace = {
            "id": f"mem_cons_{first_tick}_{last_tick}_{folded}",
            "text": (f"Between ticks {first_tick} and {last_tick}: "
                     f"{len(members)} small moments involving {label}."),
            "tick": current_tick,
            "timestamp": 0.0,
            "importance": 2,
            "type": "reflection",
            "category": SEMANTIC,
            "tags": ["consolidated"],
            "source": "consolidation",
            "entity_ids": [key] if key != "_unplaced" else [],
            "location": "",
            "salience_override": 0,
            "suppressions": [],
            "activation": 1.0,
            "confidence": 0.9,
            "reinforcements": 0,
            "last_recalled_tick": None,
            "reflection_depth": 1,
            "source_memory_ids": [m.get("id") for m in members if m.get("id")],
            "contradicts": [],
        }
        for member in members:
            player.memories.remove(member)
            _forget_index(player, member.get("id"))
        player.memories.append(trace)
        folded += len(members)
        traces += 1
    return {"groups": traces, "folded": folded}
