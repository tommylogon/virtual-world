# NPC behaviour, binding, and memory — design Q&A

**Date:** 2026-10-05 · **Status:** design record, not a spec · **Author:** working
conversation between the designer and the implementing agent.

This file records questions that were asked, the answers that were verified
against the codebase, and the questions still open. It exists because several
answers were **wrong on the first pass** and the correction is the useful part.

Verified claims carry a `file:line`. Claims marked **OPEN** were never tested.

---

## 1. Pursuits, schedules, plans, and activities — corrected 2026-10-05

The design reference is now **[`Character Pursuits.md`](../virtualWorld/design/Character%20Pursuits.md)**. The previous draft used “schedule” as the umbrella and “activity” for a reusable intention; that blurred two game concepts and is superseded.

### The designer's own phrasing, for the record

> "my idea is that schedules are pretty much a recipe of behaviours. who to do
> what when because of reason"

> "schedule Sleep-home vekka, vekkas bed, from 22 to 06 unless not tired"

> "think an agent can go 'hmm i probably need 3 days of water…'"

**Correction (2026-10-05):** A **Goal** is the character's desired outcome and why they care. A **Mission** is an external request that may become a pursuit if accepted. A **Pursuit** is the longer undertaking, such as Vekka scouting north because she remembers tracks and wants to warn Zikka. A **Schedule** is the calendar cue or recurring routine that can make something timely, such as a 22:00 reminder to go to bed if tired. A **short-term plan** is the immediate approach to a pursuit. An **Activity** is the observable process in a place over time: the sleep pursuit can take James home, and the sleeping Activity then starts on a specific bed, changes his state, and can be witnessed or interrupted. A **world recipe** defines a transformation such as turning raw fish into cooked fish.

The reason is character prose, not a reward token. “I want good grades because Mom may be nicer to me” is the character's belief about why an outcome matters; the simulation determines what actually happens.

### Correction worth recording

§4 below presents "the leash is a suggestion engine" as a new insight. **The
designer had already described pursuits as non-forcing suggestions**: an agent
may accept, adapt, or decline. This remains a character-choice rule, not a new
engine feature. The earlier design note overstated the discovery.

### Current behavior and planned wiring

- `engine/activities.py:184-225` stores `Player.activity`, applies conditions such as unconsciousness for sleep, and produces an activity description. `static/js/agent/prompt-builder/context-sections.ts:66` includes that description in `=== YOUR STATE ===`.
- `static/js/agent/prompt-builder/character-state.ts:608-627` renders the immediate `=== YOUR PLAN ===` step list.
- `engine/schedule.py` is the HH:MM clock routine layer. The partial background pursuit runner is `engine/background_plans.py`; its active pursuit and short-term plan are distinct.
- The pursuit is not yet part of the LLM prompt. A search for `active_pursuit` in `static/js/agent/prompt-builder/` returns **0 matches**. A proposed structured-plus-prose prompt block is documented as planned, not implemented.
- The background runner does not yet start a persistent Activity from a pursuit or bind a sleeping character to a particular bed relation. Those are explicit task-702 follow-ups.

The detailed terms, Vekka example, and proposed prompt format live in
[[Character Pursuits]]. Do not infer that a mechanic is wired merely because its
data or module exists; use the measured implementation boundary above.

---

## 2. Binding — walls and leashes

**Answered:** leash / wall / free is the correct top-level distinction, and the
two are different *kinds* of thing rather than settings on one axis.

| Kind | Mechanism | Mechanism exists? |
|---|---|---|
| **Wall** (immobile) | `apply_condition` `restrained`; `movement.py:376` refuses the move | **Yes** |
| **Wall** (bound to a place) | condition carries a location | **No** |
| **Leash** | planner proposes returning home; actor may decline | Needs pursuit selection |
| **Free** | no constraint (goblins with agentic minds) | Yes |

Why they are different kinds: a behaviour is trigger → conditions → actions,
which makes an NPC *do* something. A wall makes a move *refused*, so it cannot be
a behaviour — it has to gate movement.

The designer rejected "leash/wall as a property with a strength." **Confirmed:
that was wrong.** It is physics vs persuasion, and they do not share a
mechanism.

The designer also rejected "three distinct item roles" (bind / reveal /
resolve). **Confirmed wrong** — that taxonomy was invented from theory. The
mansion's actual data: 183 `logic_trigger` nodes, of which **145 effects are
`message`** and conditions total `uses_above` 6, `skill_check` 2, `state_equals`
2. There is one role: an item has triggers, and the triggers fire. The
distinction that actually exists is between *what a trigger does*, not between
kinds of item.

---

## 3. Perceptions the engine already supports

Available as trigger **conditions**, usable inside a behaviour:

`sight_holds` · `sound_heard` · `sound_above` · `smell_detected` · `proximity` ·
`speech_matches` (with `mode: not_contains` for negation) · `in_area` ·
`state_equals` · `flag_equals` · `random_chance` · `skill_check` · `save_throw`

Available as trigger **types** (40 total, `engine/triggers/constants.py`):
`on_use_on` · `on_speech` · `on_delayed` · `on_dawn` · `on_dusk` · `on_day` ·
`on_night` · `on_full_moon` · `on_blood_moon` · `on_state_enter` · `on_state_exit` ·
`on_tick` · `on_turn_start` · `on_turn_end`

**OPEN:** a behaviour of the form *"move toward my home item unless a non-undead
is perceived."* The conditions exist and the shape is right, but
`_resolve_area_name` (`engine/npc_behaviors.py:620`) filters
`node.type == "area"` — **an NPC cannot path to an item.** Either home is
authored as an area, or navigate-to-item is new work. Three undead in one crypt
would all path to the same room rather than their own sarcophagus.

---

## 4. The planner is a suggestion engine

From the designer's own framing:

> "GOSP is just a calendar reminder. 'Hey, you meant to scout the woods today.'
> And the goblin can go 'yeah no I'm hungry, I'm stealing Rikka's sandwich
> instead.'"

> "they get the prompt, if you see it in the text i shared … and if the LLM
> focuses its attention on the needs over their surroundings, they might decide
> to say yeah fuck that plan, i need to steal rikka's sandwich"

The word “GOSP” in that earlier quote used the calendar-reminder metaphor
loosely. The corrected terms are: the reminder is a **Schedule**; “scout the
woods” is a **Pursuit**; hunger is a **Need**; stealing the sandwich is one
possible short-term **Plan**; eating it is an **Activity** if it runs over time.
The pursuit may be suggested by a schedule cue, but it is not the cue itself.

**This was the agent's second-worst error of the session.** It had been treating
leash as "a property with a strength," which would have required engine work.
Under the suggestion-engine model the leash needs **no gate at all** — the undead
is *proposed* a return home and may decline when something more urgent happens.
The wall is the only case that needs engine work.

**Kept in `task-704` as two acceptance criteria:**

1. The selector proposes; the actor may reject its own proposal. When two needs
   conflict the selector does **not** resolve it.
2. **A rejection costs nothing** — no retry pressure, no penalty, no re-proposal
   of the same goal in the same cycle.

The second is load-bearing. If rejection is expensive, the selector is a
controller with deniability and the entire framing above is false. Note the
pre-existing criterion only covered sovereignty over *other* characters, never
over oneself.

---

## 5. Memory — should anything ever be deleted?

Designer: **no**, except manually or via triggers. "people can forget something,
but usually when reminded we will go oh yeah right, that — unless you have very
clearly totally forgotten it altogether … unless it's about not having perceived
the thing in the first place?"

### What the code does

Decay deletes. `engine/memory_dynamics.py:241`:

```python
if memory["activation"] <= ACTIVATION_FLOOR and _removable(memory):
    player.memories.remove(memory)
```

`_removable` (line 206) permits removal for anything not `manual`/`preconceived`,
importance < 6, zero reinforcements.

### Why deletion is not justified

**Context budget does not justify it.** `MAX_RECALL = 10`
(`static/js/agent/prompt-builder/memory-context.ts:341`) is applied after
scoring. Only ten memories reach a prompt regardless of stored count. Deletion
buys storage, not context.

**The retrieval layer already implements the designer's model.** Recall is
keyword + semantic vector + recency. There is no strength threshold in that
pipeline. A memory's chance of returning depends entirely on whether the moment
resembles it — which is the "walk into the kitchen" case exactly.

**Activation is inert.** Every reader of `activation`, whole codebase:

```
memory_dynamics.py:164   written (boost)
memory_dynamics.py:240   written (decay)
memory-view.ts:87        displayed
mind-view.ts:69          displayed
```

**Nothing reads it to decide anything.** task-687's docstring claims memories
"fade toward irrelevance." They do not. Decay changes how a memory looks in the
inspector, and is used only as the deletion test.

**Therefore deletion is the only mechanism in this system that makes anything
permanently unforgettable.** Everything else is suppression. For the memories
that scored low, the kitchen brings nothing back — not because the character
forgot, but because it is no longer there to remind them.

### The principle

> Decay changes how loudly a memory answers a cue. It never decides whether the
> memory still exists.
>
> A character who never perceived something has no memory of it, and that is the
> only kind of absence the world contains.

The second line is the design statement — it is the distinction between *losing*
knowledge and *never acquiring* it, and only the first needs a rule.

**Task:** `task-707`. It blocks `task-687`, whose first acceptance criterion
asserts the opposite ("the plain one is removed first") and must be **replaced**,
not weakened.

### Known exception

Reflection consolidation (`task-688`) writes "memories folded; originals
removed". Deliberate, opt-in, summary survives. Named in task-707 so it cannot
become a back door. **OPEN:** whether consolidation should also retain originals.

---

## 6. The two real gaps

| Gap | Evidence | Task |
|---|---|---|
| **Despawn** | `spawn_character` in `EFFECT_TYPES`, no removal counterpart; no handler in `engine/effect_handlers/` touches `players.pop` | `task-708` |
| **Condition bound to a place** | zero hits for `restricted_area`/`confined_to`/`bound_area` across `engine/` | not filed — see §7 |

Despawn is small: `engine/companions.py:40` already performs the full four-step
teardown and its docstring says *"There is no engine-level despawn API (nothing
else needed one before task-391)."* The task promotes private working code to an
effect.

---

## 7. What already exists — do not rebuild it

Recorded because the agent proposed building all of it:

- `on_use_on` trigger type + `apply_condition` effect → **"use handcuffs on
  James"**, working today
- `schedule_trigger` (`delay_ticks`) + `on_delayed` → **delayed outcomes**
- `random_chance` condition → the fishing roll
- `in_area` condition → "am I in water"
- `llm_respond` effect with an `instructions` prompt → **items as conversational
  characters** (`encounter_radio`, `talking_mirror`)
- `speech_matches` condition → items reacting to what the player says
- `unlock` verb (`engine/autocomplete.py:160`)
- Time triggers: `on_dawn`/`on_dusk`/`on_day`/`on_night`/`on_full_moon`/`on_blood_moon`

**The fishing scenario is authorable in full today:** `on_use` → `in_area` →
`schedule_trigger` → `on_delayed` → `random_chance` → `spawn_item`.

The Haunted House story is authorable **except the ending**: the elder's
dialogue (`llm_respond`), the ring reveal, and the delayed appearance all work.
Only "the ghost ascends" has no expressible form.

---

## 8. Scope engine as precedent

Ruins-as-dungeon is authoring, not engineering. Existing: `task-535` (promote a
selection into a child scope with a gateway, review), `task-398` (deterministic
scoped generation, done), `task-528` (place areas onto painted cells, review),
`task-495` (recursive scope grids, review). Live precedent: the `test` scope has
`mode: interior` and `parent_id: goblin_camp`.

Desired nesting: **ruins** (settlement — entrance, treasury, prisoner pens,
forges, housing, kitchens, throne room, bathhouses) → **Hall of Death** (a
building, i.e. a child scope) → crypts, mausoleums, sarcophagi (rooms / anchors).

---

## 9. Referent note — Star Citizen

Observed on RSI's public Progress Tracker (v1.0, updated 2026-09-09, Alpha 4.10.0):

- Teams are organised **per archetype**, not as a monolith: `AI - Commuter`,
  `AI - Hawker`, `AI - Janitor`, `AI - Leisure`, `AI - Medical`,
  `AI - Illegal Goods Dealer`, `AI - Utility`.
- **`Off Duty Activities` are siblings, not fields.** `AI - Off Duty Activities -
  Sleeping` and `- Hygiene` sit at the same hierarchy level as the archetypes,
  owned separately. Sleeping is not a property of the Janitor.

**Why it matters here:** it argues for building the archetype and letting the
general system emerge from what repeats, rather than designing the shared
containment abstraction first. Also: `AI Tech and Feature Team` exists but its
contents were not read (list is virtualised); do not assume anything about it.

---

## 10. Open questions

1. Does the pursuit selector learn from a decline, and if so how, without
   becoming a controller? (`task-704` criterion 2 is the guard rail)
2. Should an ascended ghost leave a trace — memory, object, empty chair? Not a
   mechanic; a design call about what the ending is worth. **Undecided, and it
   should be decided before `task-708` ships.**
3. Should reflection consolidation retain originals? (§5)
4. Is home an area or an item? (§3)
5. Undead as *dwarves* rather than generic zombies — `INT 2` reads as a shambling
   corpse; a dwarf buried alive is a different read. Authoring, not code.
6. The Old Dwarven Ruins room has **zero** trigger/encounter/trap/mechanism nodes
   attached and one exit, while its description promises "traps, unstable
   passages, or residual dangers" and its tags say `dangerous`. Either author the
   danger or stop promising it.

---

## 11. Corrections made this session

Recorded because the pattern, not the individual errors, is the lesson.

| Claimed | Reality |
|---|---|
| Zombies placed in Old Dwarven Ruins, verified in autosave | On `Road (world 8,6)`; autosave was later overwritten by a different world entirely |
| The ring binds the ghost; unbinding frees her | It resolves her grief; she *ascends*, she is not freed |
| Items need new machinery for use-on, conditions, delays, fishing | All exist — §7 |
| Conditions-with-source is the missing piece | Partly: `apply_condition` exists; conditions genuinely do not reach the agent prompt |
| File size ranks interesting items | The largest files are large because of prose, not complexity |
| ~10 assertions presented with equal confidence | Only 1 was ever confirmed by the designer |

**The recurring failure:** proposing an abstraction before checking what the
library already demonstrates. The mansion's 145 `message` effects would have
answered the "three item roles" question in one read.
