---
type: task
status: done
area: characters
priority: medium
---

# task-423: Background social interactions (NPC ↔ NPC, deterministic)

**Filed:** 2026-09-21  
**Depends on:** task-417 (co-presence gate), task-420 (one relationship write
path), task-409 (background runner).  
**Amends:** task-409 §4 — this is the mature form of "coarse meetings".  
**Reference implementation:** the author's own `Aura/Diary`
(`github.com/tommylogon/Aura`, `Diary/`) — the same design already proven at
day granularity. Borrow the machinery, replace the chooser.

## Outcome (2026-09-21)

Done, together with task-417 (the gate is a component of this pass, not a
separate deliverable). `engine/background_social.py`, plus
`engine/social_text.py` for the templated prose, and a `run_social_pass` call at
the end of `BackgroundSimulation.process_due` so conversations happen where the
characters actually ended up.

**Measured, one week, 23 background characters, 23/23 alive at both tick
lengths:**

| | 1 min/tick | 15 min/tick |
|---|---|---|
| Social | **78.9** (11–100) | **78.6** (4–100) |
| Hygiene | 79.3 | 75.4 |
| Entertainment | 44.7 | 46.1 |

Social was 0 before task-431 and 37 with company-maintenance alone; interactions
are now the thing that fills it, which is the decision task-431 recorded.

### Design correction: the blocking `conversing` activity is gone

§4 specified "a short activity on both participants (a conversation, default ~10
game minutes) that consumes their action credit and blocks other actions",
because "without this a character takes ~1,000 interactions a week and the
memory/relationship churn is meaningless".

The daily cap (task-417) already does that job — measured at 6.2 social
memories/character/day at 15 min/tick and 6.7 at 1 min/tick — while the activity
**broke the survival ladder at short ticks**:

| 1 day, 1 min/tick | with activity | without |
|---|---|---|
| Hygiene | **28.0** | 70.3 |
| Entertainment | **11.3** | 38.1 |

A 10-game-minute conversation is 10 ticks at 1 min/tick, and a blocked character
cannot eat, sleep or wash; worse, a conversation pays enough Entertainment that
the "seek amusement" need stops firing (`needs:entertainment` 68 → 6 in a day),
so the camp slowly stopped looking after itself. At 15 min/tick the duration
rounded to **one tick** and never blocked a decision — the damage was completely
invisible there, which is exactly how it first showed up as unexplained
Hygiene 13.7 in a short-tick soak.

So the **cap is the bound** and the spreader is a `SOCIAL_COOLDOWN_MINUTES = 90`
game-minute cooldown, which is tick-length independent by construction. Both are
tested: the cooldown blocks an immediate second interaction and spaces the day's
allowance out instead of letting it burst.

**Trap worth remembering:** `ACTIVITY_INTERRUPTIBLE` is the set `_tick` calls
`_maybe_end_by_duration` for. A type missing from it never expires —
`elapsed_ticks` runs past `duration_ticks` forever and the character is stuck
`busy`. Adding `conversing` without it made every character permanently busy and
they died of exhaustion inside two in-game days. `activities.py` now says so at
the set.

### What is implemented

- `ACTIONS` — `chat`, `joke`, `compliment`, `tease`, `confide`, `flirt`,
  `apologise`, `bully`, each with a DC, a band gate, per-side vital bases, and a
  `hostile_variant` for the cold-band reading.
- `action_weights` — from traits (`social_gain`, `impatient`, `patient`,
  `hostile`, `attention_seeker`), the closeness band and need pressure.
  `ignore_weight` is the separate "they don't engage" draw; **`ignore` costs
  nothing**, not even the cap, because charging for it would spend an introvert's
  budget on the behaviour that defines them.
- `resolve_tier` — d20 + Persuasion + band modifier vs the DC, mapped to the six
  Diary tiers, with natural 1 and 20 pinned to the ends. Seeded per
  `(actor, target, tick, action)`, so a replay reproduces the same history.
- `_reading` — the load-bearing sign rule: a `tease` between friends reads
  positive for both sides, the same tease at low closeness is an attack on the
  target, and `bully` is never warm however well it lands.
- Failure tiers are damped relative to success (`TIER_SCALE`), or a camp becomes
  monotonically miserable because every bid that misses still costs both sides.
- One event → **two memories** ("I teased Vekka…" / "Rikka teased me…"), both with
  `entity_ids = [actor, target, area]` and `source="background"`, plus a trace
  entry per side with `why="social:<action>"`, and relationship deltas through
  `apply_relationship_delta` (task-420).
- `perform(..., action=...)` can force an action — for scripted interactions and
  for tests that must not depend on the seed.

### Not done here

**`_grant_meeting_entertainment` still double-pays.** It is a second Entertainment
path for meeting someone, and since task-425 pays character novelty through
perception, a character walking into a room pays twice. Folding it into the
novelty curve needs a stable name → character-node-id mapping on `Player` (the
pass here populates `entity_ids` with node ids, but the novelty call site cannot
resolve one from a bare name). Filed as **task-434**. Invisible in a background
soak — the rendering paths that call it only fire for the attended player — so it
matters for a human session, not for these numbers.

Also still true, and not this task's business: a character walking into a room the
*player* is already in is not perceived by the player, because `observe_area` only
runs for the mover (task-425's deferred perception trigger).

## Status notes (2026-09-21)

- **task-420 is done** — `engine/relationships.py` is the one write path, and
  `band_at_least()` / `closeness_band()` exist for this task's outcome table and
  its `flirt`/`confide` gates.
- **task-417 is absorbed here.** Its gate (same area, both background, capped per
  in-game day, deterministic pairing) is a *component* of this task, not a
  separate deliverable — building it standalone would mean implementing pairing
  twice, since the mature form replaces the "symmetric meeting" with an action and
  an outcome. Do them together.
- **Blocked on task-431.** The scenario bakes `decay_rates.Social = 0.050` against
  an engine default of `0.020` and a company gain of `0.030`, so Social falls even
  in constant company: a week soak ends with all 23 characters in
  `social_breakdown` + `hallucinating`. With `--engine-decay`, Social pegs at
  99.2. Either way the passive gain currently dominates this task's Social deltas
  — one way they land on an impossible vital, the other on a capped one. task-431
  decides that balance; this task's *relationship*, *memory* and *trace* work is
  independent of it and can proceed.
- **Fold `_grant_meeting_entertainment` in.** It is a second Entertainment path
  for meeting someone, and since task-425 pays character novelty through
  perception it double-pays when a character walks into a room. This task
  populates `entity_ids` with `[actor_id, target_id, area_id]`, which is where the
  name → character-node-id mapping it needs gets settled. (Related known gap:
  a character walking into a room the *player* is already in is not perceived by
  the player, because `observe_area` only runs for the mover — a perception
  trigger, deferred by task-425's non-goals.)

## Goal

Two co-present background characters pick a social action; rules, relationship
and traits decide which one and how it lands; **each side records its own
outcome and its own memory**. Rikka teases Vekka → Rikka's memory is *"I teased
Vekka in the Scouts Room"* with Social↑ Entertainment↑ closeness↑, while Vekka's
is *"Rikka teased me in the Scouts Room"* with Social↓ Entertainment↓
closeness↓. One event, two participants, two asymmetric consequences.

No LLM in the tick. Deterministic, seeded, replayable.

## What to borrow from Diary (wheel), and what to change

| Diary | ViWo |
| --- | --- |
| `event_selector` 6-tier outcomes | **keep** — d20 + modifier vs a per-action DC → critical failure … critical success |
| `outcomes[tier].emotional_impact` map | **keep** — apply a *map* of deltas, per tier |
| `prerequisites` incl. `has_relationship: {type, min_quality}` | **keep** — becomes co-presence + closeness-band + trait gates |
| weighted random selection, LEADS_TO boosts | **keep** — becomes trait/need-weighted action bands |
| `RELATIONSHIP_TYPES.decay_per_year` + time-since-last-event decay | **keep** — see the decay gap below |
| `decision_utils.call_llm_for_choice` | **replace** — a weighted band draw; the background tier never calls an LLM |
| Neo4j, day granularity, milestone hazard functions, 1.3MB event tables | **do not import** |

## Design

### 1. Action vocabulary and per-character weights

Actions (extensible): `tease`, `chat`, `compliment`, `flirt`, `confide`,
`bully`, `apologise`, `joke`, `ignore`. Each character carries a **weight per
action**, derived from traits + vitals + personality, not authored per
character:

- `chatty`/`extrovert` → `chat`, `joke` up; `ignore` down
- `introvert`/`loner` → `ignore` up sharply, social actions down
- `impatient` → `tease` up, `confide` down; `patient` the reverse
- high `closeness` band → `confide`/`flirt` unlocked, `bully` weighted ~0
- low `closeness` band → `tease`/`joke` become hostile variants, `apologise` up

**Selection is a weighted draw, not argmax** — argmax makes every character
repeat one action forever. The draw is a second roll; the outcome is computed,
not drawn (see below), so dispositions stay stable instead of random-walking.

### 2. Outcome resolution (borrow the Diary ladder)

Per action, a `success_dc`, modified by the actor's skill/stat against the
*target's* resistance (use the existing `Persuasion`/`CHA` vs `WIS` and the
closeness band — do not invent a second social stat). Roll d20 + modifier,
mapped to the same six tiers:

1 critical failure · 2 major failure · 3 minor failure · 4 success ·
5 major success · 6 critical success

Each tier carries an **outcome map**: per-side vital deltas
(Social/Entertainment, sometimes Energy) *and* emotion deltas from the player's
existing emotion dict. Asymmetry is the point: a `tease` landed on a friend is
success for the actor and mild success for the target; the same tease on
someone in a low closeness band is success for the actor and **failure** for the
target.

**Sign rule (load-bearing):** the outcome's *sign* depends on the relationship
band and traits — a tease between friends reads positive for both; a bully drops
closeness regardless of how it lands. A fixed "teaser +, target −" makes the
camp monotonically miserable within a week.

### 3. Gates

- **Co-presence** (task-417) — same area, no exceptions.
- **Closeness band** — `flirt`/`confide` require a minimum band, which is
  exactly the Diary's `has_relationship: {type, min_quality}` gate.
- **Not already busy** — an interaction is a short activity (see §4).
- **Need pressure** — Social/Entertainment low raises the odds of seeking
  company; this is what makes interactions respond to survival state.

### 4. Time cost

An interaction starts a short **activity** on both participants (a
conversation, default ~10 game minutes) that consumes their action credit and
blocks other actions. Without this a character takes ~1,000 interactions a week
and the memory/relationship churn is meaningless. `ignore` is the **absence**
of an action: no activity, no memory, no relationship change.

### 5. Trace, memory, and `entity_ids`

- **Trace is the authoritative record** (task: `engine/trace.py`) — one entry per
  side, with `why="social:<action>"`, the counterpart, area and tick.
- **Memory is the subjective layer** — one templated first-person entry per side,
  tagged from the **existing narrative tag vocabulary** already in the camp data
  (`rivalry`, `fun`, `chaos`, `trade`, `secret`, `prestige`, `debt`), with
  `source="background"` so it is distinguishable from authored memories.
- **Populate `entity_ids`** with `[actor_id, target_id, area_id]`. The field
  exists in the schema and is **currently 0/17 used** — it is what makes "every
  memory Vekka has about Rikka" a lookup instead of keyword search.
- On promotion, the background trace span is summarized into a richer narrative
  memory by the LLM (the established trace→memory direction). Background text is
  templated; the LLM enriches later.

### 6. Determinism

Seed every roll from `(actor_id, target_id, tick, action)` so a replay
reproduces the same camp history, in the style already used by
`background_simulation._interval`.

## Memory retention (done — no longer a blocker)

`player.add_memory` used to drop the oldest memory past 200. It is now
`memory.max_per_character` (default 0 = unlimited) and, when a limit is set,
eviction skips `source: "manual"` so authored backstory survives. Nothing to do
here beyond tagging generated interaction memories with a distinct `source`.

## Prerequisite: the relationship decay gap

`player.py:196` already declares
`{closeness, last_interaction_tick, interaction_count}`, but **nothing reads
`last_interaction_tick` and nothing decays closeness** — the camp's data only
carries `closeness` and a stale `first_sighting`. So today a pair that never
interacts keeps its value forever, and a week of social simulation would only
ever ratchet.

Borrow the Diary's rule: decay by **time since last interaction**, scaled per
band (a `rival`/`enemy` relationship should decay toward neutral slowly or not
at all; a `friend` band decaying fastest). Apply it through
`apply_relationship_delta` (task-420) so the cause is recorded. Note the
existing closeness ladder at `player.py:594-616`
(enemy/-50 rival/…/inseparable) already defines the bands — reuse it as the
outcome table's input rather than inventing new thresholds.

## Acceptance

- Two co-present characters produce **two different memories with two different
  outcome deltas** from one event.
- Outcome sign depends on the closeness band: the same action lands positively
  between friends and negatively at low closeness.
- Traits shift the *action distribution* measurably (an introvert picks `ignore`
  far more often than an extrovert over N interactions).
- Selection is a weighted draw, not argmax — over 100 events a character shows
  more than one action.
- Actions write trace entries with `why="social:<action>"` and populate
  `entity_ids`; memory `importance` and tags are set.
- A 1-week background soak at 1 min/tick and at 15 min/tick produce the
  **same number of interactions per game hour** (task-417/credit invariant).
- Replaying with the same seed reproduces the same interaction sequence.
- The world stays survivable: social outcomes must not replace food/water as the
  dominant death cause in a week soak.

## Non-goals

- Real dialogue text. Actions are mechanical; prose is the promotion summary.
- LLM calls in the background tier.
- Full GOAP/planning. This is a scored, weighted chooser.
- Multi-party (3+) interactions, groups, or overheard conversations.
- Fertility/children, romance trees, or family structures beyond closeness.

## Verification

- Unit: weighted draw respects trait modifiers over N seeded samples.
- Unit: outcome tiers map to the expected per-side deltas; the sign rule holds
  for friend vs low-closeness bands.
- Unit: co-presence gate — no interaction across areas.
- Unit: `_action_credit` is consumed and the activity blocks a second action.
- Unit: trace + memory written per side, `entity_ids` populated, tags from the
  existing vocabulary.
- Unit: decay moves closeness by band and never below the floor; no decay
  without a prior interaction.
- Soak: week at 1 and at 15 min/tick, identical interactions-per-hour; survival
  unchanged (task-410 remains the food-limited constraint).
