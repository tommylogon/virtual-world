# Character Inner Life — Thread Map

A working note consolidating one long design conversation (2026-10-07) about what a
character *knows*, *remembers*, *is*, and *can do*. Six tasks turned out to be one
system seen from six angles. This exists so the threads and their dependencies are
not re-derived.

## The dependency picture

```
task-734  knowledge is memory (record shape: prose + data + kind)
   │
   ├──▶ task-736  the cognitive map (belief-based) + route retrieval + the `recall` action
   │        │
   │        └──▶ task-352  `recall` as a free action (an agent won't pay a turn to
   │                 think; cheap self-query is what makes 736 usable)
   │
   ├──▶ task-733  the character sheet (authoring form → primitives; biography→memories)
   │        │
   │        └──▶ task-735  age / pronouns / life stages / pregnancy (the clock)
   │
   └──▶ task-724  where authored definition lives (node vs Player; one home)
```

## Threads

### A. Character definition / data model
- **bug-524** (review) — personality/description were read from the `Player` while
  authored on the **node**. Fixed: node is the persisted home, the live read payload
  publishes it, `to_scenario_dict` strips the duplicate, an edit mirrors to the node.
  Verified live.
- **task-724** (todo) — authored definition still lives in multiple homes
  (location ×3, tags/traits ×2). Decision recorded: node = authored definition,
  Player = runtime, derived = not persisted. First landing done; the location and
  tags/traits de-dup remain. Rewrites the AGENTS invariant accordingly.
- **task-447** (inprogress) — nicknames/aliases. Agents cannot set them (no `name`
  verb in the action vocabulary); aliases are not shown in the HTC or the agent's
  people block.
- **relationship `label`** (unfiled) — the `label <person> <relationship>` command is
  human-only; agents have no verb for "X is my friend". Subjective (`relationships[].
  label`) vs objective (`properties.aliases`) is a real distinction. Sibling of 447.
- **task-733** (todo) — a full-page WorldGraph-style person form that **compiles**
  into ViWo primitives (personality, appearance, interest/fear tags, traits, skills,
  memories, known, relationships). Requires `pronouns` and `age`, which do not exist
  yet. One source of truth: the sheet is authored, the primitives are a projection.

### B. Knowledge / memory / mind
- **task-734** (todo) — fold `known`/recipes/known-places into one prose+data record
  with lifecycles per kind: episodic (fast decay), procedural (decay with **disuse**,
  rehearsal resets — the pancake rule), semantic (invalidated by change, not time).
  `discovered_exits`/`visited_areas`/`discovered_items` stay **derived**.
- **task-736** (todo) — a per-character **cognitive map**: belief-based, not
  truth-based; a projection of `known_way_aspects`/`discovered_exits`/`visited_areas`;
  routes are computed within the *known* subgraph ("how do I get to X" is a path, not
  a stored string). Spoken directions and the visible map are the same data.
- **task-714** (todo) — the Mind panel (display): emotional state + its cause,
  general memories, recipes, world-knowledge map.
- **task-729** (todo) — move relationship / emotional-state / memory add-edit-generate
  controls into the Mind panel (the editing half of 714).
- **task-730** (todo) — chat-based interactive memory creation: the character reacts
  in voice to author a memory.
- **task-691** (review), **task-685** (review, memory dynamics),
  **task-725** (blocked, death/vitals/travel/resurrection memories).

### C. Activity system
- **task-731** (inprogress) — activities are entered through their **object**
  (`use bed` → sleeping), not a bare verb. Furniture templates wired, bare `fish`
  deleted. Deferred: actor-chosen duration ("use bed for 6 hours"), NPC sleep
  grounded in a bed, dreaming.

### D. Lifecycle
- **task-735** (todo) — age (birth tick + elapsed), life stages, fertility →
  pregnancy → birth → the child becoming a character, death by old age. The clock a
  10-year soak needs; supplies 733's `age`.

### E. UI / tooling
- **bug-526** (review) — Sync All now scopes to the active tab and skips generated
  areas (fixed); items/ways provenance marker and an overwrite confirm remain.
- **task-732** (inprogress) — collapse item instances into templates; a meaningful
  review queue (partial).
- **task-673/674/675/676** (todo) — full-surface entity editors (frame / item /
  character / area).

### F. Action economy
- **task-352** (todo, was blocked on decisions) — free / minor / major / activity
  tiers. Decided 2026-10-07: `major:1, minor:1, free:3, activity:1`; soak gets the
  **same** budget. **Position gates free actions**: `open` is free but only for
  something you are *at*; reaching it costs `approach` (minor) or `go` (major), and a
  major may pay for a minor. `recall`/`alias`/`label` added to the free tier.
  Remaining decision: whether off-hand / ability verbs are built here (recommend no).

## The convergence

`734` (what a character knows) → `736` (how it queries and shows it) → `352`'s free
`recall` (so querying costs no turn) → `733` (how it is authored) → `724` (where it
is stored) → `735` (the clock that makes knowledge and bodies age). One system, six
views.

## Decisions locked in this conversation

- Authored character definition lives on the **node**; the Player reads it — one home
  (bug-524 fix, task-724, AGENTS invariant rewritten).
- `personality`/`description`/`base_description` are published on the live read
  payload and stripped from a saved file.
- Activities are entered through their object; the bare activity verbs are a fallback.
- Action economy: `1 major / 1 minor / 3 free`; soak parity; position gates free
  actions; recall is free.
