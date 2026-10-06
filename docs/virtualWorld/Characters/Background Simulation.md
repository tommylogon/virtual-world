---
type: doc
tags: [system/characters]
---

# Background Simulation

The background tier is the deterministic rule layer that decides what every character
**except** the ones making their own decisions does with a turn. It runs on the same
`Player` object, the same graph and the same clock as the foreground — it differs
only in *where the decision comes from*. Three modules: `engine/background_simulation.py`
(1533 lines), `engine/background_social.py` (1294), `engine/background_plans.py` (355).

Design: `docs/design/reversibility-contract.md`, `docs/design/long-horizon-simulation-progress.md`.

> **Status correction.** The Feature Map marks this **unwired**, on the evidence that
> "the string `backsim` appears once in the whole codebase, in a comment". That
> evidence does not support the conclusion. `backsim` is a *nickname*, not an import
> path; the modules are imported by name. All three are on the live tick path — see
> "Wiring" below for the measurement.

---

## The entry point

`BackgroundSimulation.process_due()` (`background_simulation.py:200`) runs once per
`tick_turn()` and does two things in order.

**1. Fill every due character's timeframe.** A turn is a *timeframe* of T game
minutes, and a character fills it with an action flow: each action consumes its
`TASK_MINUTES` cost until the timeframe is full or nothing is due. The number of
actions is emergent — one at a 1-minute turn, four or five at 15 — not a budget
handed out per turn.

A character is skipped entirely when:

| Skip | Why |
|---|---|
| `p.soak_order` set | a declared order drives it (task-481) |
| `simulation_mode != "background"` **and** `autonomy is False` | the human's own character is never puppeted. `gs.active_player` is a registry *key* (a string), so an identity check against it never matched and the human was simulated behind the player's back |
| `p.state == "dead"` | |
| `p.activity` or unconscious | committed to a duration; nothing to spend. This is also what stops a long sleep leaving a backlog |
| `time_ticks < p.next_due_tick` | an explicit "not before" defers entirely, so a long deferral cannot bank into a burst |

A *focused* character (not background-mode) still flows — it just loses the first
minute, because its decision was that minute.

**2. Run the social passes, last.** After everyone has moved, so a conversation
happens where the characters actually ended up:

```python
run_fear_pass(self.gs)        # task-552: threat pre-empts the social pass
run_social_pass(self.gs)      # paired encounters per area
run_social_approach(self.gs)  # one-sided bids
run_theft_pass(self.gs)       # task-468: a thief reaches *after* everyone moved
```

All four are wrapped in one `try/except` (`:283`). A social failure logs a warning
and the survival pass is unaffected.

---

## The survival ladder (`_act`, `:321`)

Strict priority order. Each branch returns the minutes it spent, or `None` when
nothing is due — which is the common case, and the reason a fed, rested character
spends a whole turn doing nothing.

| Priority | Trigger | Threshold |
|---|---|---|
| 1 | sleep, **critical** | `Energy <= 15` — wins over everything, or a character chasing unreachable water never sleeps and dies of exhaustion |
| 2 | drink | `Thirst >= 45` |
| 3 | sleep | `Energy <= 30` |
| 4 | seek a bed | `Energy <= 55`, and only if no bed has been sought this timeframe |
| 5 | eat | `Hunger >= 50` |
| 6 | relieve | `Bladder >= 60` |
| 7 | wash | `Hygiene <= 40` |
| 8 | recuperate | `Sanity <= 40` |
| 9 | seek company | `Social <= 50` |
| 10 | authored plan | any stored `p.plan` |
| 11 | prepare | fill a waterskin, pocket a ration |
| 12 | work | the day's schedule (task-409) |
| 13 | recreate / travel to amusement | `Entertainment <= 40` |

Two structural rules:

- **`served` blocks a repeat within one timeframe.** A character whose meal did not
  fully clear their hunger eats once per turn, not repeatedly. **Travel is
  deliberately *not* recorded** — a walk is progress, so a forager keeps stepping
  toward food until they arrive, at one minute a step.
- **A task longer than the timeframe does not resolve instantly.** `_begin_task`
  (`:288`) starts an *activity* that spans turns, so a ten-minute meal costs ten
  game minutes whether the clock is sliced at 1 or at 15. That is what removed the
  resolution dependence.

A few branches carry their findings in comments rather than in a changelog, and they
are the ones worth knowing before changing the ladder:

- **Relief never dead-ends.** The old code ended the branch in `return None`, so a
  world with no latrine simply had characters who never went. Now: relieve here if
  it's decent or urgent, else take a step or two toward somewhere better, and
  *failing that* relieve here anyway (`:446-458`).
- **Eating uses the authored path when there is one.** `_has_authored_consume`
  (`:946`) checks for an `on_eat`/`on_eat`-style trigger and defers to it, because
  bread is destroyed and a glass empties and persists. Only an unauthored item gets
  the hardcoded count/uses/remove fallback.
- **A failed search spends the time.** An outcome of `"failed"` returns
  `TASK_MINUTES["forage"]` and marks `eat` served, so the character goes somewhere
  else next rather than re-rolling in the same empty room.
- **`_in_water_area` treats natural water as an area tag**, not an item. A river has
  no authored trigger and never had one, so `WATER_AREA_DRINK_RESTORE` is
  deliberately a separate constant from the item fallback.

---

## Skill checks swap the active player

`gs.skill_check` reads `gs.active_player`, which is a *string* key. Every background
check therefore does the same thing: set `active_player` to the character's name for
the roll, restore it in a `finally` (`:918-929`). `_travel_toward` and
`_consume_via_authored` (`:966`) use the identical trick.

Every one of them **fails open**. A missing skill system returns a pass, because
"going hungry should be the exception, not the default."

---

## The social layer (`background_social.py`)

Pairs per area — never globally, because there is no distance in this world model, so
nothing else would stop two characters on opposite sides of the camp from meeting.

| Constant | Value | Why |
|---|---|---|
| `SOCIAL_COOLDOWN_MINUTES` | 90 | spreads a day's allowance instead of a burst of consecutive ticks |
| `MEETINGS_PER_CHARACTER_PER_DAY` | 6 | **this is the bound, not a blocking activity** |
| `TIER_SCALE` | 6 tiers, −1.0 … +1.8 | failure is damped relative to success on purpose: a symmetric ladder makes a camp monotonically miserable within a week, because every bid that does not land still costs both sides |
| `WARM_BAND` | `acquaintance` | the load-bearing sign rule: a tease between friends is affection for both sides, the same tease at low closeness is an attack |

The measured justification for the cap is in the module and worth reading before
changing it: task-423 specified a ~10-game-minute `conversing` activity on both
participants, and measurement showed the *activity* broke the survival ladder at
short ticks — a blocked character cannot eat, sleep or wash, and a conversation pays
enough Entertainment that the "seek amusement" need stops firing. Camp Hygiene fell
70 → 28 and Entertainment 38 → 11 over a day at 1 min/tick. At 15 min/tick the
activity rounded to one tick and broke nothing, so the damage was invisible there.
The cap alone already holds the rate to 6-7 per character per day at both
resolutions.

---

## Assigned pursuits and short-term plans (`background_plans.py`)

The background runner now uses three separate terms:

- An actor-bound graph node with `type: "pursuit"` assigns a reusable pursuit
  template and its reason/parameters.
- `Player.active_pursuit` stores that character's ongoing undertaking.
- `Player.plan` stores the current executable steps for making progress. These
  steps can survive a normal need interruption and resume after the need action.

For example, Mikka's authored scrap pursuit is represented as:

```json
{ "type": "pursuit", "pursuit_template": "haul", "actor": "Mikka",
  "source": "Scrap Pile", "item": "scrap", "sink": "Workshop",
  "label": "scrap_run", "repeat": false }
```

`data/library/pursuit_templates/` currently contains `haul`, `gather`, and
`rally`. Selection is deterministic (pursuit nodes in id order) and the source
must be reachable. A plan never fabricates an item: if the source holds nothing
matching, `take` fails and the pursuit records failure. Step traces remain
`plan:<label>`; pursuit start/completion have their own `pursuit:<label>` trace.

This is a partial background pursuit runner. It does not yet start a persistent
`Player.activity` such as sleeping or cooking, choose pursuits from LLM motives,
or provide an active-pursuit prompt block. See [[Character Pursuits]] and
tasks 701, 702, and 704. `engine/schedule.py` remains the calendar schedule
layer; `Player.activity` remains the ongoing, visible process at a location.

---

## Wiring

`TickManager.tick_turn` holds the `BackgroundSimulation` instance and calls
`process_due()` on it, inside the `not skip_npcs` guard
(`engine/tick_manager.py:1092-1102`):

```python
if not skip_npcs:
    self.npc_behaviors.process_simple_npcs()
    try:
        if not hasattr(self, "_background_sim"):
            from engine.background_simulation import BackgroundSimulation
            self._background_sim = BackgroundSimulation(self.gs)
        self._background_sim.process_due()
```

`tick_turn()` is reached from `routes/action_handlers.py:1384`
(`handle_apply_turn_decay`, the `/api/turn/apply` handler), from `rest()` at
`tick_manager.py:1309` (with `skip_npcs=True`, so a rest does *not* run the
background pass), and from `engine/timeskip.py:120`/`:245`.

**Measured, not inferred.** Instrumenting the four social functions and
`background_plans.maybe_assign` on a live `create_app()` world and calling
`w.tick_turn()` once produced:

```
background_sim attr before tick: False after: True
social/plans calls observed: ['plans.maybe_assign', 'plans.maybe_assign',
                              'run_fear_pass', 'run_social_pass',
                              'run_social_approach', 'run_theft_pass']  count 6
```

`background_social` and `background_plans` have exactly one importer each, both
inside `background_simulation` (`:268` and `:493`) — which is why the only evidence
a grep of the module *names* produces looks like "nothing calls this". The call
chain is one hop above.

Other live entry points into the same class: `engine/soak.py:98`,
`engine/timeskip.py:217` (`take_action` / `step_toward_area` at `timeskip.py:373`,
`:385`, `:394` for a human running on a declared order), and
`engine/soak_runner.py`.

**What is genuinely narrow:** the tier's *authored* content is thin. A character
whose vitals are all satisfied does nothing at all — which is the stated design
("survival is infrastructure, not a treadmill") — so in a settled camp the visible
output is the social passes and whatever `npc_behaviors` does. The 2-day
23-character soak in `docs/design/long-horizon-simulation-progress.md` is the
measurement that the tier works; there is no comparable measurement of a week.

---

## The reversibility contract

The rule that makes "same characters, two fidelities" safe: **one state model, two
decision policies.** Promotion is "start asking the character instead of their
rulebook"; demotion is the reverse. Nothing is materialized, re-rolled, or recreated,
so nothing can contradict.

While backgrounded, the rule layer must keep updating every field the foreground
reads — `current_area` + position, all `vitals`, `conditions`, `inventory` /
`equipped`, `relationships`, `memories` / `lived_log`, `activity` / `state`, `traits`,
and `goals` / current plan. **A field frozen during background is a reversibility
violation.** Approximation is allowed (block scheduling, ETA travel, seeded
probability, whole-unit vital movement) provided the character ends at a real area at
the right tick, and never to a state the foreground could not have produced.

`engine/promotion.py` implements the handoff: `offload`, `promote`, `pending_span`
over `engine/lived_log.py`, `flush` (called from `tick_manager.py:461`),
`activate_scope`, and `summarize`.

---

## Lived log

Every decision writes a `lived_log` entry with a reason tag, so a span can be
summarized into memory on promotion. The store itself — its kinds, schema, and
retention — is defined in `docs/design/lived-log-format.md`; this section is about the `why`
vocabulary.

The reason-tag vocabulary is a **schema with an enforcement rule**:
`engine/soak_telemetry.py:75` rejects a run missing
`traversal:` / `forage:` / `schedule:` entirely, because a rejection counter that
never sees those prefixes is a counter that cannot detect the failure it exists for
(`tools/why_vocabulary.py` records why it was added). Tags in use include
`needs:drink`, `needs:hunger`, `forage:found`, `forage:fail`, `search:notice`,
`plan:<label>:start|done|failed`, `social`, `rel:<counterpart>`.

**Known gap (2026-10-06).** The promotion bridge (`engine/promotion.py`) only runs
on a fidelity change, so an event recorded while a character's tier stays the same
never reaches memory. Worse, interaction events write no lived-log entry at all:
`grab` / `escape` (`engine/grapple.py`) and attack damage (`engine/combat.py`)
record nothing. See the "Known gaps" section of `docs/design/lived-log-format.md`; task-725
owns the fix. This is why a character cannot reflect on, feel about, or later
mention an event that happened to them.

---

## Tests

| File | Covers |
|---|---|
| `tests/test_background_simulation.py` | the survival ladder and thresholds |
| `tests/test_background_social.py` | tier resolution, pairs, caps |
| `tests/test_background_agendas.py` | schedules / work |
| `tests/test_background_plans.py` | plan build, advance, abandonment |
| `tests/test_background_consumption.py` | eat / drink paths, authored vs fallback |
| `tests/test_background_preparation.py` | waterskins, rations |
| `tests/test_background_recreation.py` | entertainment, `RECREATION_TAGS` |
| `tests/test_background_relief_and_washing.py` | relief, bathing, `BATH_HYGIENE` |
| `tests/test_tick_area_resolution.py` | the tick-loop integration |
| `tests/test_foraging.py`, `tests/test_forage_reachability.py` | the soak tier's forage path — see [[Search & Forage]] |

---

## Related docs

- [[Vitals System]] — the drives this ladder answers
- [[NPC Behavior System]] — the *other* off-screen tier, and the two do not share code
- [[Relationships System]] — what the social pass accrues
- [[Emotion & Affect System]] — `TIER_EMOTION`, the strong tiers only
- [[World Scopes]] — who is observed and who is backgrounded
- [[Search & Forage]] — the background tier's forage path
- [[Activities & States]] — `foraging`, `working`, `bathing`, and the `busy` condition they share

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Read next** — [[Search & Forage#The verbs are three different things]]

**Features** — [[background-simulation|Background simulation]] (#28)

**Neighbouring notes** — [[Activities & States]], [[Character Images & Expression Packs]], [[Characters Overview]], [[Emotion & Affect System]], [[NPC Behavior System]], [[Relationships System]]

<!-- connected:end -->
