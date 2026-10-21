# Reading MOSIAC & GIMP first

Before the design doc, the parts of those two docs that change the memory design:

## What they give the memory system for free

**`known:<kind>:<id>` is already the semantic memory store.** GIMP's ref registry says `known:place:food_storage`, `known:recipe:stew`, `known:item:bacon_rasher` are facts the world can flip and goals can gate on. That is *precisely* the semantic memory kind from the previous thread. The task doc calls this "fold known/recipes/known-places into one prose+data record" — GIMP has already reserved the namespace for it. This is a big deal: semantic memory is not a new store to invent, it's a **resolver backed by the memory records** that the `known:` prefix already expects. -dev notes: but we do want to retire the seperate storeage places for memories and keepeverythign memory related in the memory.

**`source: memory:<id>` on GIMP goals is the prospective-memory wire.** A goal can be spawned from a memory. So "remember to go back for the cheese" doesn't need a new subsystem — it needs the memory record to become a goal with `source: memory:<scene_id>` and a `blocks[]` / trigger condition. The memory is the *seed*; the goal is the *lifecycle*.

**`blocks[]` and `achieve[]` refs are the negative-knowledge wire.** "I checked the food storage and it was empty" is a fact the world can hold (`flag:food_storage_empty_at_<tick>` or a semantic record), and it can *block* a goal ("find food here"). Absence memory therefore has a home: it's a semantic record whose `known:` ref is a negative assertion.

**MOSIAC's A (Attention) is the recall filter.** The doc says: "A is where needs and vitals enter — a need is a signal, not an aspiration, so it belongs in the salience filter." That is *exactly* where mood-congruent recall plugs in. Recall is not a separate step before MOSIAC; **recall is A**. Threat memories fire under fear because they raise the salience score that MOSIAC's A reads.

**MOSIAC's "disposition ranks it" is the LLM/soak seam.** "Soak and LLM share one context and one action set, and differ only in how well they choose." So the memory system must produce **one** ranked recall context that both actors consume — same salience scores, same provenance, rendered as words for the LLM and as numbers for the soak. That fixes something the task doc quietly leaves open.

## What they don't cover, and the questions I still have

- **Q1: tick → wall-clock.** Arix's `decay_rates` are per-something, and the doc references tick numbers, but I don't see a canonical conversion. Every decay curve needs `(ticks_per_hour, ticks_per_day)`. Please confirm the constants or where they live.
- **Q2: does re-observation reinforce or create?** If Arix sees the bacon at tick 1 and again at tick 50, is that one scene memory with `reinforcements: 2`, or two scene memories with `contradicts: []`? GIMP's `opened_tick: null = authored, predates the log` and the `visits` counter on the existing area memory suggest **reinforce-in-place**, but the `contradicts[]` field suggests **parallel records**. The design doc picks one (I pick reinforce-in-place for identical scenes, parallel for changed scenes) — flag if the code already does otherwise.
- **Q3: theory of mind scope.** Arix's file has `known_by: ["no_one"]` on her secret. Is *belief about other characters' knowledge* in scope for this task, or a later one? If in scope, the memory model needs `about:<character_id>` memories that are *asserted, not verified* — belief about belief. Big. I'd defer, but the doc should say so explicitly.
- **Q4: does the LLM actor receive raw memories or a rendered context?** MOSIAC says "same context, rendered as words." So probably rendered — but then the **data** field must survive rendering, or the LLM loses the ability to compare ("the bacon was there at tick 1, gone now"). Worth a line.
- **Q5: meta-memory.** "I remember that I know where the coin is." Needed for "I don't remember where X is" — which is a *behaviour trigger* (search). Not in the doc. I'll add it.
- **Q6: false memory vs false belief.** You agreed on #9 (belief vs truth). But false *memory* — "I remember putting the coin in the left pocket" — is a distinct corruption mechanism. Distinguish in the doc.

## Additional ideas I want to fold in

- **Write-side salience filter.** Currently 13 item sightings = 13 memories because *every* perception is logged. There needs to be a *write* gate (novelty, attention, mood), not just a read gate. This is what stops the explosion at the source.
- **Recall is reconsolidation.** Recalling a memory reinforces it. Well-established, cheap to model: `reinforcements += 1`, `activation` bump, small `confidence` drift toward later evidence. This is the mechanism the "rehearsal" acceptance criterion is asking for.
- **Inference / the "aha".** Two semantic records + a rule = a third derived record. "Smith has gold" + "smith is at forge" + "forge is south" → "there is gold south." Your #6 mention of "critical thinking" lives here. Needs a `derived_from: [ids]` field on semantic records.
- **Memory as learned body model.** "When I ate the honey, my Hunger went 60→10." Vitals memories are how the character learns food → satiation. For Arix with `high_metabolism`, this is behavioural.
- **Group / collective memory.** Goblin camp has shared knowledge. Is memory always individual, or is there a faction-tier store? Defer, but say so.
- **Recalled memory drives expression.** You said this: angry memory → angry profile image. That's the pipeline `recall → emotion state → expression`. The emotion system already exists (`player.emotion`) — this doc wires memory into it. Add a section.
- **Rehearsal strength by modality.** Recalling vs telling someone vs dreaming have different reinforcement weights. The task doc's acceptance says "rehearsal resets [procedural decay]" but not *how* — pick numbers.

Now the design doc.

---

# Memory Dynamics — Design Document

**Status:** design / pre-implementation
**Supersedes:** the flat-memory model implied by `Player.memories[]` and the parallel `known` / `crafting_known` / `known_way_aspects` stores
**Related:** task-685 (structured dynamics), task-690 (recall), task-724 (derived values), task-725 (memory & death/vitals/travel/resurrection), task-734 (this unification), task-736 (cognitive map), task-786 (recall transparency)

---

## 0. Scope and non-goals

**In scope.** One record shape for all learned and remembered content; per-kind lifecycles; confidence, contradiction and provenance; mood-congruent and context-cued recall; consolidation; downtime; belief vs truth; negative knowledge; integration with GIMP and MOSIAC.

**Out of scope (explicitly deferred).** Theory of mind across characters (Q3); collective/faction memory; resurrection and death-adjacent memory (task-725 owns that); the Mind-panel UI itself (task-786 owns transparency, this doc defines what it reads).

---

## 1. Design principles

1. **One record shape, many kinds.** Prose + data + kind + lifecycle. The *shape* is unified; the *curve* is per kind.
2. **Prose is derived from data.** `text` is rendered from the structured payload at write time; never hand-authored alongside it. If they can drift, they will.
3. **Memory is a claim, not a fact.** Every record is "the character believes X, with confidence c, because of source s." Truth is the world's job, not the memory's.
4. **Perception is cheap; memory is selective.** Writing is gated. Reading is ranked. Both use salience.
5. **Memory feeds decision.** A memory that never reaches MOSIAC's **A** or GIMP's `source: memory:<id>` is inert. Integration is not optional.
6. **Derived stays derived.** `discovered_exits`, `discovered_items`, `visited_areas` remain projections over the graph (task-724). Only memories are persisted.

---

## 2. The record

```json
{
  "id": "mem_<ulid>",
  "kind": "episodic | semantic | procedural | prospective | absence | self",
  "category": "episodic | social | threat | resource | ...",   // existing field, kept for back-compat
  "type": "observation | social | reaction | threat | ...",   // existing field, kept
  "text": "prose, rendered from data",
  "data": { /* kind-specific structured payload */ },

  "tick": 1792576376,
  "timestamp": 1792576376.6229725,
  "location": "area_food_storage",
  "observed_at": 1792576376.6229725,
  "valid_until": null,
  "invalidated_at": null,

  "importance": 5,
  "confidence": 0.7,
  "salience_override": 0,
  "activation": 1.0,
  "reinforcements": 0,
  "last_recalled_tick": null,
  "rehearsal": { "last": 1792576376, "count": 0, "modality": null },

  "source": "observation | told:<char_id> | inferred | authored | dream",
  "source_trust": 1.0,
  "source_memory_ids": ["mem_..."],
  "derived_from": ["mem_..."],
  "contradicts": ["mem_..."],
  "suppressions": [],
  "entity_ids": ["item_bacon_rasher_1791213342775_651"],
  "tags": ["observed", "area:food_storage"],

  "emotion": { "dominant": null, "valence": 0, "arousal": 0 },

  "embedding": null,
  "reflection_depth": 0
}
```

**Field notes.**

| Field | Purpose | Notes |
|---|---|---|
| `data` | the structured payload (kind-specific) | new field; everything the code needs to query without parsing prose |
| `kind` | lifecycle family | new; drives decay curve and consolidation |
| `observed_at` / `valid_until` / `invalidated_at` | the temporal envelope | `invalidated_at` is set *by a later memory*, not by decay |
| `source` | epistemic origin | extended beyond `auto/manual/background` to include `told:<char>`, `inferred`, `dream` |
| `source_trust` | multiplier from relationship | `told:Krikka` × closeness/trust |
| `derived_from` | inference provenance | for "aha" records and consolidations |
| `contradicts` | explicit conflict | used by recall to demote the loser |
| `entity_ids` | **linkage only, not truth** | see §10 |
| `emotion` | mood tag | used by mood-congruent recall (§7) and expression (§22) |
| `rehearsal` | recall-modality history | drives procedural decay and reconsolidation (§12) |

The existing field set is preserved; `data`, `kind`, `observed_at`, `valid_until`, `invalidated_at`, `source_trust`, `derived_from`, `rehearsal`, `emotion` are additive.

---

## 3. The kinds

### 3.1 Episodic — "it happened"

An event at a time in a place. **Decays fast** on the event curve; reinforced by recall.

```json
{
  "kind": "episodic",
  "data": {
    "event": "scene_observed",
    "area": "area_food_storage",
    "environment": { "light": "dim", "smell": "dried meat, mushrooms, spices; urine", "temperature": 17.9 },
    "items_seen": ["item_bacon_rasher_...", "..."],
    "exits_seen": [{ "direction": "south passage", "target": "Cooking Area" }],
    "mood_at_observation": "neutral"
  }
}
```

Decay curve: fast, power-law (§15). Rehearsal: strong reinforcement. Consolidation target: `semantic` (§9).

### 3.2 Semantic — "I know that"

A fact about the world or self, with an *observed* confidence. **Does not decay on a clock; invalidated by change.**

```json
{
  "kind": "semantic",
  "data": {
    "ref": "known:place:food_storage",
    "claim": "food_storage is reached from cooking_area by the south passage",
    "subject": "area_food_storage",
    "predicate": "adjacent_to",
    "object": "area_cooking_area",
    "polarity": "affirm",
    "certainty_basis": "observed",
    "invalidated_by": ["flag:passage_collapsed"]
  }
}
```

The `ref` field is the GIMP `known:<kind>:<id>` key. **This is the same store GIMP resolves against** — no second registry. Backs: `known:place:*`, `known:recipe:*`, `known:item:*` (class-level, not instance), `known:character:*` (who they are), `known:self:*`.

### 3.3 Procedural — "I can"

A skill or recipe. **Decays by disuse; rehearsal resets.**

```json
{
  "kind": "procedural",
  "data": {
    "ref": "known:recipe:stew",
    "skill": "cooking",
    "steps": ["...", "..."],
    "proficiency": 0.6,
    "last_practised_tick": 1790000000,
    "successful_uses": 12
  }
}
```

Decay curve: slower than episodic, faster than semantic; **fully resets on rehearsal** (the task's acceptance criterion). Backs `crafting_known`.

### 3.4 Prospective — "I mean to"

An intention to do something later. **Promotes to a GIMP goal when its trigger fires.**

```json
{
  "kind": "prospective",
  "data": {
    "intent": "return to food_storage for cheese",
    "trigger": { "vital": "Hunger", "op": ">", "value": 40 },
    "target_area": "area_food_storage",
    "target_item_class": "cheddar_cheese",
    "spawn_goal": "goal_find_cheese_when_hungry",
    "status": "pending | fired | expired | abandoned"
  }
}
```

Lifecycle: created by a scene observation when the character notices something they *want but aren't acting on now* ("note to self: cheese"). Fires when MOSIAC's **A** (Attention) matches the trigger (§18). On fire: emits a GIMP goal with `source: memory:<id>` and `status: active`; the prospective record becomes `fired` and stops recalling. On expiry (deadline passed): `expired`, recall suppressed.

### 3.5 Absence — "it wasn't there"

Negative knowledge. **Semantic by lifecycle, but distinct by payload** so recall can rank it separately and so GIMP can gate on it.

```json
{
  "kind": "absence",
  "data": {
    "ref": "known:absence:food_storage:bacon_rasher",
    "subject": "area_food_storage",
    "expected_item": "item_bacon_rasher",
    "polarity": "absent",
    "checked_at": 1792576376,
    "as_of_prior_memory": "mem_scene_earlier"
  }
}
```

This is the record that stops a character searching forever, and it's what `blocks[]` in GIMP can gate on ("goal: find food here is blocked because I checked and it was empty at tick T").

### 3.6 Self — "I am"

Identity-forming facts. **Non-decaying unless contradicted by strong evidence.** Backs the narrative arc.

```json
{
  "kind": "self",
  "data": {
    "ref": "known:self:trait:runaway",
    "claim": "I am a runaway from Chief Gruk's tribe",
    "arc_anchor": "narrative.arc",
    "confidence": 0.9
  }
}
```

Populated from authored `narrative` / `biography` / `identity` at seed time (§24) — this is your "button to turn persona narrative into memories."

---

## 4. Lifecycle per kind

| Kind | Trigger to write | Decay | Reinforced by | Invalidated by | Consolidates into |
|---|---|---|---|---|---|
| episodic | perception, event | fast, power-law | recall, re-observation, rehearsal | later contradictory observation | semantic (on repetition) |
| semantic | observation, told, inference | none (clock) | use in reasoning, re-observation | world change (`invalidated_by`), strong contradiction | — |
| procedural | practice, taught recipe | by disuse | rehearsal, successful use | repeated failure, long disuse | — (may lose steps, lower proficiency) |
| prospective | noticed-but-deferred | until trigger / deadline | (no rehearsal; salience from importance) | trigger fires / deadline / abandonment | GIMP goal on fire |
| absence | observed non-presence | like semantic | re-check that confirms absence | re-observation of presence | — |
| self | authored seed, defining event | none | narrative reinforcement | world contradiction (rare) | — |

This is the "curve per kind, shape per kind" the task asks for; the shape constants live in `engine/memory_curves.py`.

---

## 5. Confidence, contradiction, and truth

**Confidence** is written at creation from three inputs and decays slowly:

```
confidence = base(source) × source_trust × certainty_of_perception
```

- `base`: `observation=0.9`, `told=0.6`, `inferred=0.7`, `authored=1.0`, `dream=0.3`.
- `source_trust`: from the relationship's `closeness` normalised to `[0.5, 1.0]` — Krikka at `closeness=26` might be `0.7`; a stranger `0.5`.
- `certainty_of_perception`: from `environment.light` (`dim` → `0.85`), `air` (`stale` → `0.95`), and perception-level tags.

**Contradiction resolution.** When a new record `contradicts` an old one:

1. If sources differ in *epistemic rank* (observed > told > inferred > dream), the higher-ranked wins; the loser gets `invalidated_at = now`, `confidence *= 0.3`, and stays for diffing.
2. If sources tie, **newer wins** (`observed_at`), loser invalidated as above.
3. If the contradiction is *about a moving entity* (entity_id overlap, different location), **both are kept**; neither invalidates; a `delta` record is emitted (§17).
4. Losses never delete — they become inputs to §17 diffing and §14 suppression.

---

## 6. Provenance and trust

`source` carries the *epistemic* origin, not the system tag:

| source string | meaning |
|---|---|
| `observation` | saw/heard/felt directly |
| `told:<char_id>` | another character said it |
| `inferred` | derived from other memories (`derived_from` set) |
| `authored` | seeded from character sheet (narrative, secrets) |
| `dream` | produced by downtime (§11) |

`source_trust` is the snapshot of relationship trust at the time of telling. If the relationship later changes (Krikka caught lying), **past told-memories do not retroactively lose confidence** — but a `told-by-liar` flag on the relationship causes future recall to *highlight* them for re-evaluation ("did Krikka lie to me about X?"). This is a small mechanism with big narrative payoff, and it costs one lookup.

The `via:<char_id>` tag is added on every told record so recall transparency (task-786) can say "recalled because: told by Krikka."

---

## 7. Mood-congruent recall and emotion weighting

Every record carries `emotion: { dominant, valence, arousal }`. On recall, the score gains:

```
mood_bonus = cos(current_emotion_vector, record_emotion_vector) × W_mood
```

Where `W_mood` is `0.2` for soak NPCs and part of the same disposition weights the LLM prompt renders as adjectives. So:

- Arix is **angry** → angry/threat memories surface. If Krikka stole her trophy, the `rel:Krikka` threat memories get the highest activation, MOSIAC's **A** (Attention) fires on "Krikka", and the disposition ranks aggressive verbs higher.
- Arix is **hungry** → food memories and prospective `find food` intents surface, food-location scene memories outrank honey memories (sweeter is not hungrier).
- Arix is **scared** → `threat:hide` and Water Skin memories surface regardless of recency.

**Emotion writes are not just at recall time.** When a record is created *during* an emotional state, the dominant emotion is stored; when the character's state changes, **no retroactive re-tagging** (that would be mood-congruent recall, not mood-congruent encoding). Both encoding and retrieval biases are modelled, separately — the first is a tag at write, the second is the `mood_bonus` at read.

**The profile-image wiring.** `player.emotion.current` is set by the highest-scoring recalled record's dominant emotion, capped by the current dominant vital signal (fear > anger > sadness > neutral). The existing `expressions` block on the character file renders the image. That means the pipeline is:

```
recall → scored context → dominant emotion (capped by vitals) → player.emotion → expression profile image
```

No new subsystem — one hook from `disposition.rank()` into the emotion state setter. (See §22.)

---

## 8. Context cues: location, sense, mood

Recall scores gain cue bonuses when the current context matches a record's context:

| cue | bonus | how |
|---|---|---|
| `location` matches `record.location` | +0.15 | Arix walks into Food Storage → scene memories formed there rise |
| `environment.smell` substring overlap | +0.10 | "dried meat" in the room's smell vs. the memory's stored smell |
| `environment.noise` match | +0.05 | quiet vs quiet |
| `environment.light` match | +0.05 | dim vs dim |
| `mood` match | +0.20 (see §7) | cosine |
| `presence` — a `present:<char_id>` matches a `rel:<char_id>` tag | +0.25 | Krikka walks in → memories of Krikka fire |

These bonuses are the difference between "a mind" and "a lookup table." The room data you pasted already carries the smell/light/air/noise triples — they were authored to be *cues*; wire them up.

---

## 9. Consolidation and summarisation

**Goal.** Repeated similar episodic records compress into one semantic record, preserving provenance in `source_memory_ids`, without losing the ability to recall the specific event.

**Rule.** On write, bucket existing episodic records by `(location, sorted(entity_class_set))`. If ≥ N (config: 3) records share the key and their `text` similarity is above τ, emit a consolidation candidate:

```json
{
  "kind": "semantic",
  "data": {
    "ref": "known:place:food_storage:stocked",
    "claim": "food_storage is usually well-stocked with meat, cheese and preserves",
    "supporting_scenes": 7,
    "first_observed": 1792576376,
    "last_observed": 1793000000
  },
  "derived_from": ["mem_scene_1", "...", "mem_scene_7"]
}
```

**What consolidation does to children:** none. Children are *not* deleted and *not* suppressed; they simply stop being independently salient because the semantic record is now the higher-importance one. This avoids losing the "which specific visit" answerable question. (The earlier thread suggested suppressing children; consolidation replaces suppression because the child may still be needed for diffing.)

**Consolidation targets by kind:** episodic → semantic; procedural episodes → procedural proficiency bump; prospective → fires / expires; nothing consolidates *into* episodic.

**Anti-duplication** (the task's "idempotency" open question): consolidation is keyed by `ref`. Re-running the consolidator updates the existing semantic record in place (`reinforcements += 1`, `derived_from` extended) rather than creating a second one.

---

## 10. Interference, entity resolution, and the entity_ids question

**Your concern is correct and it's a real bug risk.** Storing `entity_ids` on a memory suggests the memory *is about* that instance and invites "you remember this exact item, which is now over here" — which is wrong when the item has moved.

**Resolution.** `entity_ids` is **provenance, not truth**. It exists to:

1. Link two observations of the *same instance* (reinforcement, diffing).
2. Link a memory to a relationship (`rel:Krikka`) or an area (`area:food_storage`).
3. Back `known:item:<class>` refs at the **class** level, not the instance level.

It is **not** used to assert current location. The truth of "the bacon is in the food storage" is `data.area == food_storage` and `observed_at`, not `entity_ids` contains the bacon's node id. A recall that needs current location must check the world (the engine's job, not the memory's).

**Class vs instance.** GIMP refs are `known:item:<id>` — the `<id>` there is the *class* (`bacon_rasher`), not the runtime instance (`item_bacon_rasher_1791213342775_651`). Make this explicit: semantic `known:item:*` refs use **class ids**; episodic `entity_ids` may use **instance ids**. Two different namespaces, two different jobs.

**Interference.** Two memories with overlapping `entity_ids` but different `location` or `observed_at` are **not contradictions** — they are successive observations. On recall, apply a `recency_bonus` to the newer one and let the older one still surface at lower rank. When comparing ("was the bacon there?"), the engine runs a diff (§17) rather than picking one.

---

## 11. Downtime: decay, sleep, dreams

**Decay.** Applied on a scheduled pass (every N ticks) and lazily on read (`activation = activation * decay_curve(kind, ticks_since_last_recall)`), whichever is cheaper for the current engine. Constants in `engine/memory_curves.py`:

| kind | shape | half-life (ticks) | floor |
|---|---|---|---|
| episodic | power-law | `~250` (tune to `ticks_per_day/4`) | 0.05 |
| procedural | power-law, reset on rehearsal | `~1500` | 0.1 |
| semantic | none | ∞ | — |
| prospective | n/a | until trigger/deadline | — |
| absence | none | ∞ | — |
| self | none | ∞ | — |

**Sleep.** A sleeping character (`state: sleep`) does not act, so recall does not fire — but the **downtime pass** runs once at wake:

1. Apply decay for the sleep duration.
2. Rehearse: every episodic record with `activation > 0.5` gets `reinforcements += 1` (the "it was important enough to survive a night" bump).
3. Dream: sample 1–3 episodic records weighted by `importance × arousal`, optionally **recombine** (mix two scenes into a single dream record with `source: dream` and low `confidence`). This is the mechanism that turns a locked door from yesterday into a `prospective` note ("go back and try it") without the character having consciously decided.
4. Prune: records below the floor with `importance < 2` and no `contradicts` links are dropped (§13 optional suppression).
5. Emit **one dream memory** with a short rendered `text` so the player can see what happened; a dream is an *episodic* record with `source: dream`, `confidence: 0.3`, and tags `["dream"]`.

Dreams are already a thing you considered — this is the concrete pass.

---

## 12. Recall mechanics: automatic vs active, cost, budget

**Two recall modes:**

- **Automatic recall** — fired by MOSIAC's **A** (Attention) each turn. This is the background filter: top-K by score, K small (config: 3–5), always free.
- **Active recall** — a deliberate verb the character can take ("think about X", "try to remember"). This is a *choice* in MOSIAC's **C**. It costs a turn, and it returns more depth: top-K larger, with reasoning traces. It also produces a `last_recalled_tick` bump on the returned records (reconsolidation, §13).

**The active-recall question you weren't sure how to put into words:** the split is exactly the one above. Auto recall is the *filter* that shapes attention; active recall is the *search* the character consciously does. Different budgets, different return depth, and only one of them is a verb. The GIMP record's `visibility` field maps onto it: active recall can surface `private`/`secret` records that auto recall hides; telling a secret requires a *choice*.

**Budget under stress.** Under threat (`threat:*` tag active, `HP < 50`, or `Energy < 20`), automatic recall is capped at K=2 and semantic lookups are skipped. A starving, terrified Arix does not do deep reasoning — she acts. This is where the "omniscient lookup table" failure mode is prevented.

**Reconsolidation.** Every successful recall (auto or active) writes:

```
record.last_recalled_tick = now
record.reinforcements += 1
record.activation = min(1.0, record.activation + 0.1)
record.rehearsal = { last: now, count: +1, modality: "recall" }
```

Rehearsal by *telling someone* is a stronger bump (`+0.2`, `modality: "told"`), by *dreaming* a weaker one (`+0.05`, `modality: "dream"`). That's the modality-weight mechanism the task doc asks for.

---

## 13. Suppression, trauma, motivated forgetting

**Suppression** is a *recall* modifier, not a *decay* modifier.

- A suppressed record keeps its `activation` (or even gains it, trauma is sticky) but is excluded from auto recall unless a *trigger* fires.
- Trigger is a `tags ∩ current_context` match (e.g. `threat:Water Skin` fires when Water Skin is present).
- Suppression *strength* decays as `closeness` to the suppressor changes — Arix stops suppressing Water Skin memories once she feels safe.

**Trauma.** Records tagged `trauma:*` (from `player.traits.traumas`) get:
- `importance` floored at 7,
- decay slowed ×0.5,
- `contradicts` allowed to re-evoke them (the "you were wrong about X" reset).

**Motivated forgetting** is *active* suppression: a choice verb that adds the record to `suppressions` with a `suppressed_at` and a `reason`. This is something Arix's `cunning` trait might actually do when she doesn't want to face something. It's the moral inverse of reconsolidation, and it costs a turn.

---

## 14. Self-defining memory and narrative salience

**Two sub-kinds of self:**

1. **Authored self** — seeded from `narrative.biography`, `identity`, `secrets` (§24). High `importance`, non-decaying.
2. **Earned self** — a defining event promotes an episodic record to `self` when: `importance ≥ 8` **and** the event's `emotion.arousal` is high **and** it ties to an existing `self` anchor (a `narrative.arc` milestone).

The promotion is:

```json
{
  "kind": "self",
  "data": {
    "ref": "known:self:event:krikka_helped_me",
    "claim": "Krikka once shared her food with me when I had none",
    "arc_anchor": "narrative.arc",
    "promoted_from": "mem_episodic_..."
  },
  "importance": 9,
  "confidence": 0.9
}
```

**This is the mechanism that makes the narrative arc a *thing the character remembers*, not a string in their file.** It also gives you the "button to turn persona narrative into memories" — a bulk seed pass over `narrative.*` fields (§24).

---

## 15. Individual differences and curve shape

Every decay curve is `(rate, shape, trait_modifier)`:

```
activation(Δt) = exp(-rate * Δt^shape) * trait_modifier
```

- `shape = 1.0` is exponential; `shape < 1` is power-law (closer to human forgetting; **use this** for episodic).
- `trait_modifier` from `traits`: `high_metabolism` → `×1.3` on episodic rate (forgets faster), `traits.traumas` → `×0.5` (clings to threat memories), low `INT` → `×1.2` (slower encoding).

**Arix specifically:**

| trait | effect |
|---|---|
| `high_metabolism` | episodic decay ×1.3; procedural ×1.1 |
| `traumas: [harsh_training, emotional_neglect]` | threat memories ×0.5 decay, importance floor 7 |
| `WIS 9` | `certainty_of_perception` ×0.9 (less careful observer) |
| `INT 12` | consolidation threshold τ raised (needs more repeats) |
| `proud`, `lonely` | weight on `headpats`/`hugs` memories +0.3 (emotion retrieval) |

Parameterising `(rate, shape, trait_modifier)` now matters because re-migrating after saves exist is painful, and because the trait vector on the character file already invites it.

---

## 16. Belief vs truth, false memory, and the about-someone-else case

**Three distinct failure modes**, each with its own field:

1. **Outdated belief** — "there is cheese in the pantry" (was true, world moved on). Handled by `invalidated_at` set on contradiction and by staleness (§17). Not a bug: it's the mechanism that makes checking worthwhile.
2. **False belief** — "Krikka is trustworthy" even after Krikka lied. Handled by `source_trust` not being retroactively updated on a single lie, but by `contradicts` and an `investigation` verb that lets the character *re-examine* told memories and downgrade them.
3. **False memory** — "I remember putting the coin in the left pocket" when she put it in the right. Handled by a corruption chance on `source: dream` recombination (§11) and on high-`arousal` records (stress impairs encoding). Corruption lowers `confidence` and *adds* a competing semantic record — the mind is allowed to be wrong.

**Theory of mind** — *deferred*. The `about:<character_id>` field on records exists (e.g. `about:player_Krikka` on a "Krikka is angry with me" record), but belief-about-belief (`belief:about:Krikka:knows_my_stash`) is **not implemented in this task**. Flag it as a follow-up; the `known_by` field on Arix's secret is a placeholder for it.

**Active investigation.** A verb ("investigate X") reads all records whose `entity_ids`/`tags` overlap X, ranks by `confidence × importance`, and returns a *reasoned* summary with citations to `source_memory_ids`. This is what makes critical thinking possible — you can't get it by re-reading one memory, you get it by diffing several. Ties directly into §17.

---

## 17. Item state staleness, diffing, and critical thinking

**Staleness.** Every scene memory that names items carries `observed_at` per item. On recall, if `now - observed_at > staleness_threshold(kind_of_item)` (food `~1 day`, tools `~1 week`, places `∞`), the rendered prose softens: "I saw bacon there last time," not "there is bacon there." Same data, different rendering.

**Diffing.** When a new scene memory is created for a location the character has an older scene for, and the item sets differ, emit a **delta** record:

```json
{
  "kind": "episodic",
  "data": {
    "event": "scene_delta",
    "area": "area_food_storage",
    "prior_scene": "mem_scene_earlier",
    "current_scene": "mem_scene_now",
    "added": ["item_honeycomb"],
    "removed": ["item_bacon_rasher"],
    "changed": ["item_cheddar_cheese (uses 3→1)"]
  }
}
```

The delta is what the "investigate" verb and the "critical thinking" prompt consume. It is also the input to `absence` records (§3.5): every `removed` item generates an `absence` record.

**This is the mechanism that answers your #6 concern directly.** You don't need to remember the exact instance and chase it; you need to remember that *something was here and is not now*. Entity ids make the diff cheap; they do not assert location.

---

## 18. Integration with MOSIAC

The letters that memory touches:

| Letter | Memory's job |
|---|---|
| **M** Motivation | read-only from GIMP; memory does not write it |
| **O** Obligations | `source: told:<char>` records with a promise shape feed obligations; memory of "I promised X" is a prospective record that *proposes* an obligation |
| **S** Schedules | recurring episodic memories with a time-of-day pattern ("I always eat at noon") consolidate to a `procedural`/`semantic` routine; feeds schedules |
| **I** Intentions | memory seeds goals (`source: memory:<id>`); the goal's `intention` is read by MOSIAC; memory does not write MOSIAC's I directly |
| **A** Attention | **memory is A** — the automatic recall pass is the salience filter; threat memories, mood-congruent memories, and presence-cued memories all enter here |
| **C** Choices | "active recall" and "investigate" are verbs; available recall depth is a choice input; a locked door in memory suggests "go back and try again" as a candidate action |

**Assembly order per turn:**

```
1. GIMP reads (M, I from active goals)
2. Player reads (O, S from obligations/schedule)
3. Memory auto-recall (A) — score, top-K, mood + location + presence cues
4. Disposition ranks (A∪C) using recalled context
5. LLM or soak picks
6. If pick is an active-recall/investigate verb → run active recall, bump rehearsal
```

This matches the MOSIAC doc's "assembled per character, per turn, and handed to whichever actor is driving."

---

## 19. Integration with GIMP

Three wires:

1. **`source: memory:<id>`** — prospective memory fires → creates a goal. This is the whole "remember to come back for the cheese" path.
2. **`known:<kind>:<id>`** — GIMP's ref registry resolves against semantic memory. Implement `resolve_ref(ref)` in the memory store; the GIMP goal gating (`blocks[]`, `achieve[]`) calls it.
3. **`blocks[]` gating** — an `absence` record can block a goal ("find food here" is blocked because "checked and it was empty"). A later presence observation unblocks it (newer wins per §5).

**Goal lifecycle ↔ memory:**

| GIMP event | memory effect |
|---|---|
| goal created from memory | `prospective.status = fired`; new episodic "I decided to X" |
| goal `reached` | episodic "I achieved X"; possibly `self` promotion if high importance |
| goal `blocked` | `absence` / `threat` record on the blocker |
| goal `dropped` | episodic "I gave up on X"; prospective `status = abandoned` |
| goal `dormant` | prospective record re-sleeps (still recalls at low salience) |

The GIMP achievement log and the memory's `source_memory_ids` cross-link so task-736's cognitive map and task-786's transparency can both trace "why did I do X?"

---

## 20. Integration with derived indexes

The task is explicit and I agree: `discovered_exits`, `discovered_items`, `visited_areas` are **derived projections**, not persisted stores. They are computed by projecting over `entity_ids` and `location` across episodic memories:

```python
def discovered_items(player):
    return {eid for m in player.memories if m.kind == "episodic"
            for eid in m.entity_ids if eid.startswith("item_")}

def visited_areas(player):
    return {m.location for m in player.memories if m.kind == "episodic"}
```

The Mind panel and the cognitive map (task-736) render from these projections. Nothing new is persisted; the source of truth is memory.

**`known_way_aspects`** is different — it's the route/spatial memory, and the task says it *is* a memory. It maps to `semantic` records with `ref: known:way:<a>_<b>`:

```json
{ "kind": "semantic",
  "data": { "ref": "known:way:cooking_area:food_storage",
            "claim": "south passage from cooking_area reaches food_storage",
            "hops": [{"direction": "south passage", "target": "area_food_storage"}],
            "travel_time_ticks": 12 } }
```

Pathfinding is graph search over these — task-736's cognitive map.

---

## 21. Integration with relationships

**Two directions:**

- **Memory → relationship.** Recalled memories tagged `rel:<char>` raise `closeness` on successful positive interaction; threat memories lower it. The write is in the disposition layer, not the memory layer — memory *reports* the emotion, the disposition *applies* the delta.
- **Relationship → memory.** `closeness` feeds `source_trust` for `told:<char>` (§6) and the `presence` cue bonus (§8). A character you're close to speaks with more weight and their arrival cues more memories.

The existing `relationships` dict stays; memory does not duplicate it. The link is via `tags: ["rel:Krikka"]` on records and `entity_ids` overlap.

---

## 22. Integration with expressions and images

You explicitly asked for angry memory → angry profile image. The pipeline:

```
recall → scored context → dominant_emotion = argmax(record.emotion.dominant × record.activation)
                        ∩ caps from vitals (fear > anger > sadness > neutral)
       → player.emotion.current = dominant_emotion
       → player.emotion.expression = player.expressions[dominant_emotion].profile
```

Caps from vitals matter because a starving character can't be `amused`; a `HP < 20` character is `fearful` regardless of recalled emotion. The existing `emotion` block on the character file already has `current`, `description`, `expression`, `intensity` — memory writes `current` and `intensity`, the expression index is looked up on render.

**Mood as a *persistent* modifier.** The dominant emotion lingers for N ticks after the last recall (config: `emotion_hold = 60`). During the hold, the `mood_bonus` in §7 keeps working; after the hold, decay pulls the state back toward the vitals baseline.

---

## 23. Write-side salience filter

Currently every perception is logged (13 items → 13 memories). This is the bug. The write gate:

```
write_salience = novelty(item_class in known)
               × importance_bias(item tags)
               × mood_congruence(current_emotion, item_emotion)
               × presence_of_characters(relevant entities)
               × attention_budget
```

Only records above `write_threshold` are persisted as **individual** item memories. The rest are folded into the **scene** record (one per area-visit) with `data.items_seen: [...]`. This gives you the scene memory you actually want, and keeps the item-level record only for **novel** or **salient** things (first time seeing a coin, a threat, a shiny thing — Arix's `pockets_anything_shiny` habit makes coins novel forever).

The threshold is per character: Arix's `high_metabolism` and `cunning` raise the bar for food (she sees food a lot) but the `shiny` tag *lowers* it (she never gets tired of coins).

**This is the single most important change for scaling.** Without it, the memory store grows linearly with ticks × visible entities and the recall pass degrades.

---

## 24. Migration and authored-content seeding

**Existing stores → new kinds:**

| old store | new kind | migration |
|---|---|---|
| `known` (list of strings) | semantic | wrap each as `{ref: known:fact:<slug>, claim: <string>, confidence: 0.8, source: authored}` |
| `crafting_known` | procedural | one record per recipe, `proficiency` from skill level |
| `known_way_aspects` | semantic (`known:way:*`) | one record per adjacency |
| `discovered_exits` | **drop** | derived projection (§20) |
| `visited_areas` | **drop** | derived projection |
| `discovered_items` | **drop** | derived projection |
| `memories` (flat) | episodic, but **re-bucketed by (location, timestamp)** | one scene per (location, timestamp) with children linked via `source_memory_ids`; legacy `category`/`type` preserved |
| `narrative.*` / `biography.*` / `identity.*` | `self` (via seed pass) | one record per narrative line, `source: authored` |

**The seed pass ("turn my persona into memories").** A one-shot projector over `narrative.*` fields:

```python
def seed_self_memories(player):
    for field in ["narrative.biography.early_life",
                  "narrative.biography.adulthood",
                  "narrative.biography.current_situation",
                  "identity.occupation",
                  "identity.species"]:
        text = read_field(player, field)
        if text:
            emit(self_memory(text, ref=f"known:self:{field}",
                             importance=8, confidence=1.0, source="authored"))

    for fact in player.secrets.hidden_facts:
        emit(semantic_memory(fact, ref=f"known:self:secret:{slug(fact)}",
                             importance=9, confidence=1.0, source="authored",
                             tags=["secret", "self"]))

    for trauma in player.traits.traumas:
        emit(self_memory(trauma, ref=f"known:self:trauma:{trauma}",
                         importance=9, confidence=1.0, source="authored",
                         tags=["trauma", "self"]))
```

**Idempotency.** Key each seed by `ref`. Re-running updates `text`/`confidence` in place, doesn't duplicate. This is the task's "same class as task-733's biography→memories" concern.

**Back-compat.** Existing saves round-trip: `memories` list is read, re-bucketed on first load, and written back under the new shape. The legacy `category`/`type`/`tags` survive so task-690's recall keeps working during the transition. A `schema_version` field on the player record gates the upgrade.

---

## 25. Data shape examples

**A scene memory (the case from the original thread):**

```json
{
  "id": "mem_scene_fs_1792576376",
  "kind": "episodic",
  "category": "episodic",
  "type": "observation",
  "text": "I checked the Food Storage. Stone shelves, hanging racks, sealed pots. The smell of dried meat and mushrooms, a hint of something worse. Still stocked: bacon, dried meats, a wheel of cheddar, honey, cod, apples, acorn meal, a beef roast. Way out runs south to the Cooking Area. A shiny coin sat on the shelf — for now.",
  "data": {
    "event": "scene_observed",
    "area": "area_food_storage",
    "environment": { "light": "dim", "air": "stale", "noise": "quiet",
                     "smell": "dried meat, mushrooms, spices; urine" },
    "items_seen": [
      { "id": "item_bacon_rasher_...", "class": "bacon_rasher", "uses": 3 },
      { "id": "item_shiny_coin",       "class": "shiny_coin",     "uses": null,
        "salience": "high", "reason": "shiny" }
    ],
    "exits_seen": [{ "direction": "south passage", "target": "Cooking Area" }]
  },
  "tick": 1792576376,
  "timestamp": 1792576376.6229725,
  "location": "area_food_storage",
  "observed_at": 1792576376.6229725,
  "importance": 5,
  "confidence": 0.85,
  "activation": 1.0,
  "source": "observation",
  "source_trust": 1.0,
  "source_memory_ids": ["c81c24a0","b52da826","...","90f6b827"],
  "entity_ids": ["area_food_storage", "item_bacon_rasher_...", "item_shiny_coin"],
  "tags": ["observed", "area:food_storage", "scene"],
  "emotion": { "dominant": "neutral", "valence": 0.1, "arousal": 0.2 }
}
```

**A prospective record (the "come back for cheese" case):**

```json
{
  "id": "mem_pros_cheese",
  "kind": "prospective",
  "text": "Next time I'm hungry, there's cheddar in the Food Storage.",
  "data": {
    "intent": "return to food_storage for cheddar",
    "trigger": { "vital": "Hunger", "op": ">", "value": 40 },
    "target_area": "area_food_storage",
    "target_item_class": "cheddar_cheese",
    "status": "pending",
    "created_from": "mem_scene_fs_1792576376"
  },
  "importance": 4,
  "confidence": 0.85,
  "source": "observation",
  "tags": ["prospective", "food", "rel:self"]
}
```

**The fire:**

```
MOSIAC A sees Hunger=45 → trigger matches → GIMP creates:
{ "id": "goal_find_cheese", "what": "get the cheddar from the food storage",
  "why": "I am hungry", "intention": "I want to eat",
  "source": "memory:mem_pros_cheese", "status": "active", "priority": 2,
  "achieve": [ { "ref": "item:cheddar_cheese", "note": "have it in hand" } ],
  "blocks":  [ { "ref": "known:place:food_storage:reachable", "note": "get there" } ] }
→ prospective.status = "fired"
→ new episodic: "I decided to go get the cheese."
```

---

## 26. Acceptance criteria (expanded from the task)

- [ ] One record shape (prose + data + kind) carries `known`, `crafting_known`, `known_way_aspects`, and `memories`.
- [ ] Semantic and self records survive a decay pass that trims an episodic record (task's own test).
- [ ] Procedural records decay by disuse and reset on rehearsal; a recipe cooked after 15 years of disuse is *gone*, not just faded.
- [ ] A prospective record fires into a GIMP goal with `source: memory:<id>` and updates `status: fired`.
- [ ] An `absence` record is emitted on scene-diff for a removed item, and `blocks[]` on a GIMP goal resolves it.
- [ ] Recall scores include mood, location, presence and smell cues; a threat memory outranks a neutral memory under fear even at lower recency.
- [ ] The dominant recalled emotion sets `player.emotion.current` and the expression profile image updates.
- [ ] `discovered_exits` / `visited_areas` / `discovered_items` are computed, not stored (task-724 rule).
- [ ] Seed pass over `narrative.*` emits `self` records, idempotent on re-run.
- [ ] A write-side salience filter prevents non-novel items from generating individual memories; a scene record carries them instead.
- [ ] `resolve_ref("known:place:food_storage")` returns a semantic record and is the same resolver GIMP uses for `blocks[]`/`achieve[]`.
- [ ] Recall transparency (task-786) can render "why": `source`, `source_memory_ids`, cue matches, mood match, rehearsal count.
- [ ] Existing saves round-trip; legacy `memories` re-bucketed on first load.

---

## 27. Open questions to settle against the codebase

1. **Tick → wall-clock constants** (Q1) — where do they live? Needed for every curve.
2. **Reinforce-in-place vs parallel** for re-observation (Q2) — I propose reinforce-in-place for identical scenes, parallel-with-diff for changed; confirm code doesn't already do otherwise.
3. **LLM actor gets raw data or rendered context** (Q4) — propose rendered prose *plus* a compact `data` sidecar, because "the bacon was there at tick 1, gone now" needs the data.
4. **Theory of mind scope** (Q3) — defer, or include `about:<char>` asserted-belief records now? I defer.
5. **Collective / faction memory** — out of scope, but the `faction:goblin` tag on Arix and the `held_by:goblin` tag on the room suggest a tier is expected. Defer.
6. **Dream recombination policy** — how aggressive? I propose 1–3 samples weighted by `importance × arousal`, mix-two. Tune later.
7. **Entity id namespace separation** — confirm `known:item:<class>` uses class ids and episodic `entity_ids` use instance ids. Right now both look like `item_...`; the migration should disambiguate.
8. **Reconsolidation cost** — every recall bumps `reinforcements`; on a soak NPC with ~5000 memories this is fine, but confirm the pass frequency (per turn vs per N turns).
9. **Memory of death and resurrection** (task-725) — I didn't touch it; confirm this doc doesn't block that task's forward work.

---

**TL;DR.** The doc your codebase should match: **one record shape, five-plus-one kinds, per-kind lifecycles, confidence and provenance as first-class fields, mood and context as recall cues, consolidation as the episodic→semantic bridge, diffing as the "critical thinking" mechanism, absence as first-class, prospective memory as the wire into GIMP's `source: memory:<id>`, semantic memory as the store GIMP's `known:` refs already resolve against, auto-recall as MOSIAC's **A**, active-recall as a **C** verb, and a write-side salience gate so 13 items don't become 13 memories.** Everything else in the two docs already points at this shape; the design just makes the wiring explicit.