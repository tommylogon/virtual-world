"""AgentMind (task-403 slice 2): one facade over a character's knowledge.

Knowledge is scattered across ``Player.memories``, ``SpatialMemory``,
``VectorStore``, ``known_way_aspects``, ``known``, ``flags`` and trait effects.
None of them share a query interface, so an agent cannot answer "where is food?"
— that question touches several stores at once. ``AgentMind`` does not
reimplement any storage: it delegates to the existing fields and defines the
seams between them. Nothing here calls an LLM.

Scope of this slice: the facade, scenario-bootstrap *preconceived knowledge*,
need-driven recall, and trait-driven memory decay. It deliberately does not
replace ``VectorStore``/``SpatialMemory`` or build a world ontology.
"""
import re
from typing import Any, Dict, List, Optional

from engine.traits import (
    TraitSystem,
    MEMORY_RECALL_BOOST,
    MEMORY_DECAY_PER_TICK,
    MEMORY_DECAY_REDUCTION,
    MAX_IMPORTANCE_CAP,
)
from engine.memory_dynamics import DECAY_RATE_KEY, CONSOLIDATE_KEY
# decay-source rules (preconceived never / background half) live in
# engine.memory_dynamics, the one writer of decay — not duplicated here.


def _default_salience(memory: Dict[str, Any]) -> float:
    override = memory.get("salience_override")
    if override:
        return float(override)
    salience = memory.get("salience")
    if salience:
        return float(salience)
    return float(memory.get("importance", 5) or 5)


class AgentMind:
    """A facade over one character's memories, knowledge and cognitive traits."""

    def __init__(self, player, graph=None, game_state=None, vector_store=None):
        self.player = player
        self.graph = graph
        self.gs = game_state
        self.vectors = vector_store

    # ── recall ──────────────────────────────────────────────────────────
    def recall(self, query: str = "", need: str = None, context: dict = None,
               limit: int = 3) -> List[Dict[str, Any]]:
        """Return memories relevant to *query*/*need*, best first.

        Matching is tag/keyword based (no embeddings unless a vector store is
        attached). Ranked by ``effective_importance * salience * recall_boost *
        urgency`` (task-685: availability and confidence modulate the base
        importance), and filtered by the character's ``max_importance_cap``
        trait when set. Recalled memories are reinforced — thinking about
        something keeps it available.
        """
        player = self.player
        context = context or {}
        terms = {t for t in re.split(r"[^a-z0-9_]+", f"{query} {need or ''}".lower())
                 if len(t) > 2}
        boost = float(TraitSystem.get_first_effect(player, MEMORY_RECALL_BOOST) or 1.0)
        cap = TraitSystem.get_first_effect(player, MAX_IMPORTANCE_CAP)
        urgency = float(context.get("urgency", 1.0) or 1.0)

        from engine.memory_dynamics import effective_importance, reinforce
        tick = getattr(self.gs, "time_ticks", None) if self.gs is not None else None

        scored = []
        for memory in getattr(player, "memories", []) or []:
            if not self._matches(memory, terms, need or ""):
                continue
            importance = float(memory.get("importance", 5) or 5)
            if cap is not None and importance > float(cap):
                continue
            score = effective_importance(memory) * _default_salience(memory) * boost * urgency
            scored.append((score, memory))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        recalled = [memory for _, memory in scored[:limit]]
        for memory in recalled:
            reinforce(memory, tick=tick)
        return recalled

    @staticmethod
    def _matches(memory: Dict[str, Any], terms: set, need: str) -> bool:
        tags = {str(t).lower() for t in (memory.get("tags") or [])}
        if need and str(need).lower() in tags:
            return True
        text = str(memory.get("text", "")).lower()
        return any(term in tags or term in text for term in terms)

    # ── writing ─────────────────────────────────────────────────────────
    def remember(self, text: str, tick: int = 0, importance: int = 5,
                 tags: Optional[List[str]] = None, source: str = "mind",
                 location: str = "", entity_ids: Optional[List[str]] = None):
        return self.player.add_memory(
            text, tick, importance=importance, tags=tags, source=source,
            entity_ids=entity_ids, location=location,
        )

    def know_area(self, name: str) -> bool:
        """Mark an area as known. Returns True when it was newly learned."""
        if not name:
            return False
        known = self.player.known
        if any(str(k).lower() == str(name).lower() for k in known):
            return False
        known.append(str(name))
        return True

    def knows_area(self, name: str) -> bool:
        return any(str(k).lower() == str(name).lower() for k in self.player.known)

    def knows_way(self, way_id: str, aspect: str = None) -> None:
        """Record a known way (optionally a discovered aspect of it)."""
        bucket = self.player.known_way_aspects.setdefault((str(way_id), ""), set())
        if aspect:
            bucket.add(str(aspect))

    # ── preconceived knowledge (scenario bootstrap) ──────────────────────
    def load_preconceived(self, pdata: Dict[str, Any], tick: int = 0) -> int:
        """Inject authored starting knowledge. Idempotent; returns memories added.

        Accepts the six optional keys either at the top level or under
        ``preconceived_knowledge``. Knowledge is not omniscient — only what is
        authored here is known.
        """
        block = pdata.get("preconceived_knowledge")
        if not isinstance(block, dict):
            block = pdata
        existing = {str(m.get("text", "")) for m in self.player.memories or []}
        added = 0
        for memory in block.get("memories") or []:
            if not isinstance(memory, dict) or not memory.get("text"):
                continue
            if str(memory["text"]) in existing:
                continue
            self.remember(
                memory["text"], tick=memory.get("tick", tick),
                importance=memory.get("importance", 5),
                tags=memory.get("tags"), source="preconceived",
                location=memory.get("location", ""),
                entity_ids=memory.get("entity_ids"),
            )
            existing.add(str(memory["text"]))
            added += 1
        for area in block.get("known_areas") or []:
            self.know_area(area)
        for item in block.get("known_items") or []:
            self.know_area(item)
        for way_id, aspects in (block.get("known_ways") or {}).items():
            for aspect in aspects or []:
                self.knows_way(way_id, aspect)
        return added

    # ── need-driven recall ──────────────────────────────────────────────
    def surface_need_memory(self, need: str, tick: int, urgency: float = 1.0,
                            day_key: Optional[str] = None) -> Optional[dict]:
        """Recall a memory for a pressing need and surface it once per *day_key*.

        Writes a normal memory (``source: need_recall``); it never fabricates a
        location. Returns the new entry, or None when nothing matched or it was
        already surfaced this day.
        """
        stamp = "_need_recall_days"
        seen = getattr(self.player, stamp, None)
        if seen is None:
            seen = set()
            setattr(self.player, stamp, seen)
        key = f"{need}:{day_key if day_key is not None else tick}"
        if key in seen:
            return None
        matches = self.recall(query=need, need=need,
                              context={"area": self.player.current_area,
                                       "urgency": urgency})
        seen.add(key)
        if not matches:
            return None
        best = matches[0]
        return self.remember(
            f"While {need}, you recall: {best.get('text', '')}",
            tick=tick, importance=min(7, int(best.get("importance", 5) or 5)),
            tags=[str(need).lower(), "recall"], source="need_recall",
            location=self.player.current_area,
        )


    # ── decay ───────────────────────────────────────────────────────────
    def apply_decay(self) -> int:
        """Fade memories and consolidate when pressured; return removed count.

        Delegates to ``memory_dynamics.apply_decay`` (task-687): activation
        decays with per-memory resistance, not a flat salience subtraction.
        The rate is the character's ``memory_decay_per_tick`` trait value when
        it has one (trait semantics unchanged, including the reduction trait);
        otherwise the ``memory.decay_per_tick`` runtime-config default, so
        ordinary characters finally forget and ``0`` freezes everyone.

        Preconceived memories never decay; background memories fade at half
        rate. Consolidation (task-688) runs after decay only under pressure —
        a retention cap nearly full, or ``memory.consolidate`` enabled.
        """
        player = self.player
        from engine.memory_dynamics import apply_decay, consolidate, consolidation_pressure
        trait_rate = TraitSystem.get_first_effect(player, MEMORY_DECAY_PER_TICK)
        if trait_rate:
            reduction = float(TraitSystem.get_first_effect(player, MEMORY_DECAY_REDUCTION) or 0.0)
            rate = float(trait_rate) * max(0.0, 1.0 - reduction)
        else:
            from engine.runtime_config import config
            rate = float(config.get(DECAY_RATE_KEY, 0) or 0)
        removed = apply_decay(player, rate)

        try:
            from engine.runtime_config import config
            consolidate_enabled = bool(config.get(CONSOLIDATE_KEY, False))
        except Exception:
            consolidate_enabled = False
        if consolidate_enabled or consolidation_pressure(player):
            tick = getattr(self.gs, "time_ticks", 0) if self.gs is not None else 0
            consolidate(player, tick=tick)
        return removed
