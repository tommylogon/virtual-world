---
type: task
status: todo
area: characters
priority: medium
related: ['"\'task-404\'"', '"\'task-725\'"', '"\'task-736\'"', "'task-404'", "'task-725'", "'task-736'", 'task-404', 'task-725', 'task-736', 'task-786']
---

# task-734: Knowledge is memory: fold known/recipes/known-places into one prose+data record with episodic vs semantic kinds

**Filed:** 2026-10-08
**Related:** task-685, task-690, task-404, task-724, task-366

<!-- deps:start -->
**Related:** [[task-404-character-life-experience-generator]], [[task-725-memories-carry-nothing-about-death-vitals-travel-perception-or-resurrection]], [[task-736-per-character-cognitive-map-a-belief-based-memory-of-places-and-routes-in-the-mind-panel]], [[task-786-recall-transparency-show-why-a-memory-was-recalled-automatic-and-action-driven]]
<!-- deps:end -->

## What

Unify the character's separate knowledge stores (known, crafting_known/recipes, known locations, known_way_aspects) with the memory model so one prose+data record shape carries all learned content. Keep distinct lifecycles: episodic memories tick/decay/emotion-weight; semantic and procedural knowledge are stable and do not fade on the event curve. discovered_exits and visited_areas stay derived indexes over the graph, not persisted stores.

## Grounding (measured 2026-10-07)

The memory record **already is prose + data** (`player.py:991`):

```
add_memory(text, tick, importance=5, memory_type="observation", tags=None,
           source="auto", entity_ids=None, location="", salience=0,
           category=None, confidence=None, contradicts=None)
```

`text` = prose; `entity_ids / tags / importance / category / confidence /
contradicts / tick / source / salience` = data. The structured-dynamics fields
(`category/confidence/contradicts`) are task-685's and are read by recall
(task-690).

The gap is that learned *content* lives in parallel stores, not in that model:

```
self.known = []                  self.crafting_known = ...
self.discovered_exits = set()          self.known_way_aspects = {}
self.discovered_items = set()          self.visited_areas = set()
```

## How

One knowledge/memory **record** (prose + data + `kind` + salience + rehearsal),
with a **lifecycle curve per kind** — not a binary "episodic decays, semantic
does not":

- **episodic** — an event: tick, emotion weight, decays/reinforces fast (task-685).
- **procedural** — a recipe or a skill you practiced. Decays with **disuse**, and
  rehearsal resets it: cook pancakes for 15 years then stop, and yes, you lose
  the recipe. This corrects an earlier overreach in this task ("semantic never
  fades"). The repo already counts successful uses toward a skill raise
  (`player.py`, skill uses) — decay-by-disuse is the other half.
- **semantic** — a fact about the world ("the smith is down that road"): does not
  fade on a clock; it is **invalidated by change** (the road closed, the smith
  died), not by time.

**capability** (skills/traits) is unchanged — learned ability is not a memory,
though its *practice history* is procedural.

**Derived indexes stay derived.** `discovered_exits` and `visited_areas` are a
view over the graph (what the character has perceived), not memories; task-724's
rule says a derived value is not persisted as its own store. `discovered_items`
is the same — a set of node ids already in the graph. `known_way_aspects` is the
spatial/route memory and is the one that *is* a memory (see task-736).

## Why not one flat list

One flat list forces one decay curve on everything. A recipe you have not cooked
in fifteen years and a locked door you saw yesterday are not the same fact, and
they should not age at the same rate. The model unifies the *shape*; the
*lifecycle* is per kind.

## Open questions

- Migration: existing `known`/`crafting_known`/`known_way_aspects` becomes
  semantic records; `discovered_*`/`visited_areas` are dropped as derived. What
  writes the first semantic records — a projector, or the same add path?
- Does recall (task-690) score semantic knowledge, or only episodic? A recipe
  should surface by relevance, not by recency.
- Idempotency: re-deriving semantic records from authored content must not
  duplicate (same class as task-733's biography→memories).

## Acceptance

- [ ] `known`, `crafting_known`, known locations and `known_way_aspects` are
      readable as one record shape with `kind: semantic`.
- [ ] Semantic knowledge does not decay on the episodic curve; episodic memory
      still does.
- [ ] `discovered_exits`/`visited_areas`/`discovered_items` remain derived, not
      persisted stores.
- [ ] Existing saves and scenarios round-trip.
- [ ] A targeted test proves a semantic record survives a decay pass that trims
      an episodic one.

## Browser UI and intended live verification

Intended UI home: select a character → Mind panel → Knowledge and Memories.
Known facts, recipes, places, and known ways should appear as one record model
with a visible kind; derived exploration indexes remain internal projections.

Current availability: the card describes separate knowledge and episodic
memory stores and proposes unified records with distinct lifecycles. The
unified Mind-panel record view is not claimed as implemented today.

Live steps when available:
1. In a scratch scenario, teach a character one fact about an area, one recipe,
   and add one recent episodic event memory. Open the character's Mind panel.
   - expected: the three entries are readable through the same record view and
     show semantic, procedural, and episodic kinds respectively.
2. Advance enough simulation time for the episodic memory's activation to
   decay, then reopen Mind and inspect all three entries.
   - expected: the episodic record follows its decay rule; semantic knowledge
     remains stable and the recipe follows its procedural-use lifecycle.
3. Use the learned recipe and ask the character to recall the area fact.
   - expected: rehearsal affects the procedural record as specified, and the
     semantic fact remains available without being promoted into a new store.
4. Inspect `/api/state` and reload the scenario.
   - expected: learned knowledge round-trips; `discovered_exits`,
     `visited_areas`, and `discovered_items` remain derived indexes rather than
     new persisted stores.

These steps define the intended Mind-panel view and lifecycle checks. The
unified record model remains planned.

This section is not a claim that planned UI exists or works today.

## Why

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
