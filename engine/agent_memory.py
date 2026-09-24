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

#: Memories that must never decay: authored knowledge the character was told.
NON_DECAYING_SOURCES = ("preconceived",)
#: Memories that fade at half rate: earned on-screen, summarised off-screen.
HALF_DECAY_SOURCES = ("background",)


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
        attached). Ranked by ``importance * salience * recall_boost * urgency``,
        and filtered by the character's ``max_importance_cap`` trait when set.
        """
        player = self.player
        context = context or {}
        terms = {t for t in re.split(r"[^a-z0-9_]+", f"{query} {need or ''}".lower())
                 if len(t) > 2}
        boost = float(TraitSystem.get_first_effect(player, MEMORY_RECALL_BOOST) or 1.0)
        cap = TraitSystem.get_first_effect(player, MAX_IMPORTANCE_CAP)
        urgency = float(context.get("urgency", 1.0) or 1.0)

        scored = []
        for memory in getattr(player, "memories", []) or []:
            if not self._matches(memory, terms, need or ""):
                continue
            importance = float(memory.get("importance", 5) or 5)
            if cap is not None and importance > float(cap):
                continue
            score = importance * _default_salience(memory) * boost * urgency
            scored.append((score, memory))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [memory for _, memory in scored[:limit]]

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

    # ── background consolidation bridge ─────────────────────────────────
    def consolidation_summary(self, since_tick: int) -> str:
        """Bounded background-span summary (task-399's memory bridge)."""
        from engine import promotion
        entries = promotion.pending_span(self.player, since_tick)
        if not entries:
            return ""
        end_tick = getattr(self.gs, "time_ticks", since_tick) if self.gs else since_tick
        return promotion.summarize(self.gs, entries, since_tick=since_tick,
                                   end_tick=end_tick)

    # ── decay ───────────────────────────────────────────────────────────
    def apply_decay(self) -> int:
        """Fade memories by the character's trait-driven rate; return removed count.

        Inert without a trait that sets ``memory_decay_per_tick``, so the default
        is no behaviour change. Preconceived memories never decay; background
        memories fade at half rate.
        """
        player = self.player
        rate = TraitSystem.get_first_effect(player, MEMORY_DECAY_PER_TICK)
        if not rate:
            return 0
        reduction = float(TraitSystem.get_first_effect(player, MEMORY_DECAY_REDUCTION) or 0.0)
        rate = float(rate) * max(0.0, 1.0 - reduction)
        if rate <= 0:
            return 0

        removed = 0
        for memory in list(player.memories or []):
            source = str(memory.get("source", ""))
            if source in NON_DECAYING_SOURCES:
                continue
            step = rate * (0.5 if source in HALF_DECAY_SOURCES else 1.0)
            remaining = _default_salience(memory) - step
            memory["salience_override"] = round(max(0.0, remaining), 3)
            if remaining <= 0:
                player.memories.remove(memory)
                self._forget_index(memory.get("id"))
                removed += 1
        return removed

    def _forget_index(self, memory_id) -> None:
        index = getattr(self.player, "memory_index", None)
        if not isinstance(index, dict) or not memory_id:
            return
        for subject, mid in list(index.items()):
            if mid == memory_id:
                index.pop(subject, None)
