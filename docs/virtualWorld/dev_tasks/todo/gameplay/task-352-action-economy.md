---
type: task
status: todo
area: gameplay
priority: medium
---

# task-352: Action economy — free / minor / major / activity tiers

**Filed:** 2026-07-30 (as a design note; rewritten 2026-09-27 against the current engine)
**Relates:** `engine/activities.py`, `engine/background_simulation.py`, `engine/tick_manager.py`,
`engine/matching.py`, `virtual_world_engine.py`, `static/js/agent/human-turn-composer.js`,
`static/js/agent-engine.js`, `static/js/agent/turn-queue.js`, `routes/action_handlers.py`,
`docs/virtualWorld/Simulation Model.md`.

Goal: let a character perform **several actions within a turn**, bounded by a budget,
where every verb is classified by how much of the character it really costs —
**free** (look, open, close, drop), **minor** (grab, dash, toggle, a second go),
**major** (examine, attack, use, take), **activity** (sleep, bathe, cook, undress —
already implemented, task-131).

## Scoping notes (2026-09-27, measured)

The original note was written on 2026-07-30 against an engine that has since changed
underneath it in three ways. Everything below is measured, not inferred.

**1. The design this task was arguing with no longer exists.** The old note's
"Problem" says every command costs flat `time`+`energy` and that "time costs feed
into the stateful actions system — if an action costs 1 time and the character has
no time remaining, they're out of actions." All of that is gone. `task-436` removed
the `time` key from the cost table entirely; `virtual_world_engine.py` is
now energy-only and `tests/test_action_costs.py` asserts no entry has a `time`
key. `engine/tick_manager.py` says so in as many words. The `actions_per_turn`
budget it was reacting to is gone too — `_action_credit`, `DECISION_MINUTES` and
`MAX_ACTIONS_PER_TICK` no longer appear in any executable code, and three tests
(`tests/test_background_simulation.py`) assert their absence so they
cannot come back.

**2. But the governing doc explicitly retired *budgets* — and the reason does not
forbid this.** `docs/virtualWorld/Simulation Model.md` states: "The number of
actions per turn is **emergent** — as many as fit — not a budget handed out per
turn", with a supersession note at lines 65-68. The reason given is specific: the old
`actions_per_turn = T` budget *derived slots from minutes* and "assumed one-minute
actions with no durations, which turns a 30-minute turn into thirty eat/drink/socialise
cycles". A tier budget is not that. It fixes the slot count and classifies *triviality*,
while durations keep bounding the total. So this is a **partial reversal of one line
of that doc** and must be reconciled there — but it is not a return to the model that
was retired. The invariant that makes it safe: **slot counts are fixed and do not
scale with `time_per_tick_minutes`.**

**3. The activity tier already ships.** `engine/activities.py`
(`ACTIVITY_SKIP_TURNS`) is literally "activities that consume the character's turn":
sleeping, resting, waiting, meditating, bathing, sitting, lying down, working, plus
the task-436 background durations eating/drinking/relieving/washing/recreating/
recuperating/foraging. `ACTIVITY_BLOCKING` (line 91) already makes sleeping and
bathing mutually exclusive with most other actions. One of the four tiers is done;
the work is the three *beneath* it, and making activities consume a budget slot
rather than merely skipping turns.

**4. A whitelist-gated extra slot already exists, twice — this is the precedent.**
`static/js/agent-engine.js``js
const CHAIN_RULES = {
 dash: ['go', 'wait'],
 lead: ['go', 'approach', 'release', 'wait'],
 grab: ['approach', 'release', 'wait'],
};
```

A successful `dash`/`lead`/`grab` already buys **one extra same-turn action**, from a
restricted verb list — for agents and, separately, for the human
(, the "burst" phase). The worked example in the goal — "dash (major), go
second time (minor)" — is *literally* `CHAIN_RULES.dash`, already implemented. The
tier model is the generalisation of this hardcoded whitelist, and it should replace
it rather than sit beside it.

**5. Two of the goal's minor-tier examples are not mechanics yet.** "Attack with
second weapon" has no offhand or two-weapon system anywhere; `attack <target>` is the
only attack verb (`routes/action_handlers.py`) and there is no `attack with`.
"Use ability" also has no verb: abilities are *items* — intrinsic ability nodes
(spells/talents, `engine/area_description.py` `_is_intrinsic_ability`) reached
through `use`. So the minor tier cannot be populated with those two as-is; they need
building first, or the tier ships with `grab`, `lead`, `toggle` and off-hand-later.
Decide explicitly which, because it changes the task's size a lot.

**6. The player path has no duration model at all — this is the biggest constraint.**
`routes/` contains **zero** calls to `world.tick` / `advance_clock`. A player's
individual action costs energy (`apply_action`) but **no game time**; the clock
advances only at `POST /api/turn/apply` → `tick_turn` → `advance_clock(1)`
(`engine/tick_manager.py`), once per turn cycle. So on the browser path a player
doing 1 action and a player doing 10 cost the same in game time. The background tier
is the opposite: fully duration-driven via `TASK_MINUTES`
(`engine/background_simulation.py`) filling a minute budget
(`process_due`, ).

Consequence: **a budget measured in minutes does nothing for the player.** The tier
budget has to be slot-based to work at all on the attended path. That means the tier
table is shared vocabulary but enforcement legitimately differs by controller — slots
for attended tiers, slots *and* minutes for the soak tier. Introducing per-action
durations on the player path would be a strictly larger change (it makes the clock
advance per action) and is not required by this task.

## The model

Keep the timeframe. Add composition control on top.

- A **turn** is still a timeframe of N game minutes (`Simulation Model.md`).
- Every verb gains a **tier**: `free`, `minor`, `major`, or `activity`.
- A character has a **fixed** per-turn allowance per tier, independent of N — e.g.
 `major: 1, minor: 1, free: 3, activity: 1`.
- The turn ends when the timeframe is full **or** nothing the character wants to do
 fits a remaining slot. Both constraints bind: minutes cap the total, tiers cap the
 composition.

The point of the tier system is that **duration cannot see triviality**. Today
`drink` is 2 minutes and a hypothetical one-minute look is 1 minute, so a long turn
lets a character spend itself on inconsequential actions. A tier cap makes a major
action genuinely compete for the turn against a glance.

The invariant to state in the code and pin with a test: at `T=1` and at `T=15` a
character gets **the same slots**. A 15-minute turn yields one major + one minor +
a few free — not fifteen majors. Every soak regression in the suite is written
against a fixed `time_per_tick_minutes`; slots that scaled with the dial would make
all of them move when someone drags the pace slider.

### Tier assignment (proposed, from the measured verb inventory)

| Tier | Verbs | Notes |
|------|-------|-------|
| **free** | `look`, `listen`, `open`, `close`, `drop`, `toggle`, `speak`/`say`/`whisper`, `do`, `fear`, `interest`, `guess time`, `inventory`, `stats` | The free tier is the **at-a-distance** layer: what you can tell from where you stand. |
| **minor** | `grab`, `lead`, `toggle`, `release`, `stow`, `put`, `wear`, `remove`, second and subsequent `go` in a turn | `grab`/`lead` already gate the existing chain slot. A second `go` is the goal's "go second time". |
| **major** | first `go`/`dash`/`approach`, **`examine`**, `take`, `use`, `eat`, `drink`, `attack`, `search`, `find`, `craft`, `combine`, `give`, `steal`, `fix`, `relieve`, `bind`/`enchant` | One per turn by default. |
| **activity** | `rest`, `sleep`, `wait`, `meditate`, `bathe`, and the task-436 background durations | Already modelled; consumes the whole turn. |

#### `examine` is major, and the hover card is *not* examine

This was the one apparent conflict in the tier model and it resolves cleanly. The
object model already has the three layers the tiers describe:

| Layer | What it is | Cost | Where |
|-------|-----------|------|-------|
| `name` | the label you see on entering | free | `scene_snapshot.py` (`display_name`, `name`) |
| `description` | what it looks like — readable from across the room | free | `scene_snapshot.py` — `_first_sentence(desc)` only |
| `examine` | picking it up and opening it: fires the authored `on_examine` trigger and reveals what is inside | **major** | `engine/items/examine_actions.py` (items), (areas), (ways) |

The client's hover card (`static/js/agent/turn-scene-view.js`) reads only
from the already-fetched scene payload and **fires no trigger** — it is the
`description` layer, and it is legitimately free. `examine` is a different verb on a
different path: `routes/action_handlers.py` → `get_item_desc` →
`_exec_triggers(node, "on_examine")`. `on_examine` is heavily authored (the Prized
Painting, the toilet, and ~4 triggers in `data/autosave.json` alone), so the content
that `examine` unlocks is real and authored — which is exactly why it must not be
free, and must not be reachable by hovering.

Two consequences for this task:

- **`examine` is major. The free tier does not contain it.** The hover card stays
 free and stays client-side; that is the free tier working correctly, not a loophole.
- **The UI wording is misleading and should be fixed as part of this.** The hover
 card is footed "free look · no turn cost" while the click menu on the same chip
 offers "Examine &lt;item&gt;" (`turn-scene-view.js`), which costs a turn
 and fires a trigger. Same word, two different things. Rename the hover affordance
 to the description layer ("what you can see from here") so the free/major
 distinction is legible rather than something the player discovers by being
 surprised.

This also makes the free/major split **author-dependent**: the split only holds if
authors treat `description` as the exterior of the envelope and put the contents in
`on_examine`. That convention is currently undocumented and must be written into the
scenario authoring guide, per the standing rule that non-obvious behaviour belongs in
the docs and not only in a task file.

## Live game (player)

- The composer gets an action list, not a single field. Today there is exactly one
 `#htc-do` input (`static/js/agent/human-turn-composer.js`), one verb
 , one `POST /api/action` (`static/js/agent-engine.js`), and no
 batch endpoint — `/api/action/sequence` exists only as a proposal in task-104 and
 was never built.
- Rows are tier-labelled and greyed out as slots are spent, so the budget is visible
 rather than discovered by rejection.
- **The burst phase becomes a special case, not a hack.** `agent-engine.js`
 gates it on a string prefix (`reply.action.startsWith('dash ')`) and detects failure
 by regex over the narration (`/locked|blocked|can't|could not|fail/i`) — so any
 action whose prose happens to contain "can't" silently loses the slot. Replace with
 a real minor slot.
- Hover stays free and client-side. That is the free tier working as intended.
- Fix `docs/actions_reference.md` ("One action per turn. Do not combine commands."),
 which currently contradicts `Simulation Model.md` and is player-facing.

## Agents

- **One decision per turn returns a list.** The standing rule is that each agent and
 the human gets exactly one set of decisions per turn regardless of
 `time_per_tick_minutes`, and that LLM call count must never scale with turn length.
 That rules out the old note's **Option B** (loop a prompt per remaining slot) and
 rules out any slot count that scales with the dial. It leaves **Option A/C**:
 one call returns `[{tier, command}, …]`, executed in order, each validated against
 the remaining slots.
- Validation is per action, not per plan. If action 2 fails, 3+ are dropped — the
 agent sees the failure in the react phase next turn rather than burning more calls
 re-planning. This is the old note's Option A with Option C's result-chaining.
- The existing `'chain-follow-up'` call (`agent-engine.js`) is retired in favour
 of the list; `CHAIN_RULES` becomes tier data rather than a hardcoded table.
- The prompt should show remaining slots, so the agent plans against the budget
 instead of discovering it. Old note lines 149-158 are still the right shape.

## Soak / background simulation

- The tier table is the **same** data, so a soak character and a player character
 are classified identically. That is the parity requirement in
 `Simulation Model.md` ("There is no difference between an agent and a
 player"), and it is currently violated: the background tier fills a timeframe
 (`background_simulation.py`), LLM agents get a chain follow-up, and the
 human gets one field.
- Enforce the slot cap inside the same `while remaining > 0` loop
 (`background_simulation.py`), decrementing alongside `remaining`. The check
 is a dict lookup and a decrement — cheap enough not to matter over a week soak, and
 it introduces no new order-dependence beyond what task-437 is already fixing.
- `soak.py` and `timeskip.py` issue exactly one policy step per turn
 per character and subtract exactly one timeframe each. If a soaking character is
 meant to enjoy the same budget, `_policy_step` needs to be able to spend more than
 one slot; if it is not, say so explicitly rather than leaving the tiers to apply to
 the attended tiers only. **This is a real fork and should be decided, not
 assumed.**
- Determinism and tick-independence are the two things a soak regression can break.
 Both are already pinned (`tests/test_tick_time_scaling.py`,
 `tests/test_background_simulation.py`); new slot tests belong beside them.

## Acceptance criteria

- [ ] Every verb reachable from `routes/action_handlers.py` has a tier, and there is
 a test that fails when an unclassified verb is added.
- [ ] A character spends slots across a turn: `approach` (free) + `open` (minor) +
 `examine` (major) in one turn is accepted; a second `examine` is refused with a
 message that names the tier, not a generic failure.
- [ ] At `time_per_tick_minutes` 1 and 15, the slot allowance is identical. Pinned by
 a test, since the whole soak suite is calibrated to a fixed dial.
- [ ] Activities consume the turn and are mutually exclusive with other tiers, via
 the existing `ACTIVITY_BLOCKING` / `busy` path rather than a new mechanism.
- [ ] An agent turn issues exactly one decision call and returns a list; the call
 count does not change with `time_per_tick_minutes` or with slots spent.
- [ ] The composer shows a tier-labelled action list, and the dash burst is gone as a
 special case (no `startsWith('dash ')` prefix, no failure regex).
- [ ] `CHAIN_RULES` is retired; the chain follow-up call is gone.
- [ ] `docs/actions_reference.md` and `Simulation Model.md` are reconciled
 with the shipped behaviour.
- [ ] Per the standing rule, the tier table and the fixed-slot invariant are
 documented in code comments and in the user guide / technical docs, not only
 here.
- [ ] Full suite compared against the ~60 failed / 3239 passed baseline.

## Open decisions (do not start without these)

1. **Slot counts**, and specifically whether `major` is 1 or 2. The goal's own example
 lists both `examine door (major)` and `dash (major)`; at `major: 1` that sequence
 needs two turns.
2. **Whether the soak tier gets the same budget** as the attended tiers.
3. **Whether `attack with <offhand>` and an ability verb get built here** or the
 minor tier ships without them.

(The `examine` question that used to be on this list is **resolved** — see the
examine section above. It is major, and the free tier is the at-a-distance layer.)

## Non-goals

- Reactions (parry, opportunity attack). Nothing in the engine models an off-turn
 trigger yet, and it is a separate mechanism from a within-turn budget.
- Reintroducing time costs on the player path (see scoping note 6).
- Slot counts that scale with `time_per_tick_minutes`.
- Per-character budget variation by trait. Worth doing later, but the base table
 should be settled and measured first.

## Latent issues found while scoping (not this task, but adjacent)

- `world._clock_advanced_by_task` is set `True` by `rest`
 (`engine/tick_manager.py`) and **never reset** — after one `rest`,
 `tools/game_tools.py` stops advancing the clock for the rest of the world's
 life. `tests/test_action_costs.py` sets the flag explicitly rather than
 exercising the lifecycle, so nothing covers it.
- Simultaneous mode never runs `tick_turn` at all, so the entire world pipeline is
 frozen there — not just the clock. Filed as **task-533**; that is its own task, and
 it does not need deciding together with this one.
- **Retracted, and it was my error:** an earlier draft of this list said
 `engine/background_simulation.py` still documented the retired
 `DECISION_MINUTES` credit model. It does not. Those lines explicitly describe
 the credit model as *removed* and state the one-action-per-turn rule that the
 code implements. The docstring was correct; I matched a grep for "action
 credit" against a paragraph explaining its own retirement and read it as the
 opposite claim. Nothing to fix there.
- **Retracted, and it was my error:** an earlier draft of this list said
  "`task-436` sits in `review/`, not `done/`, with an unexplained ~10-point Energy
  gap between `T=1` and `T=15` still open." **Wrong on both counts.** 436 is
  resolved: its own header says *"all residuals resolved"*, and the two dated
  sections at the *end* of that file supersede the mid-document section headed
  "Energy gap remains". The Energy gap was never an Energy bug — `process_due`
  gave a focused character `remaining = T - 1` minutes while `advance_world` never
  offloaded anyone, so at a 1-minute tick the whole camp got zero minutes of
  action and only decayed. Fixed in commit `2b608a8`
  (*"fix(timeskip): world advance soaks everyone (task-436 root cause)"*), and
  `tests/test_tick_time_scaling.py` now passes 11/11. I read a superseded section
  out of context — the same mistake as the `background_simulation.py` note above,
  and the reason this file now carries retractions rather than silent edits.
  (The one true remainder: 436's *folder* was stale, `review/` rather than
  `done/`. Now moved.)

## Related

- `docs/virtualWorld/Simulation Model.md` — the timeframe model and the
 supersession note this partially reverses.
- task-104 (review) — `/api/action/sequence`, never built; this task supersedes it.
- task-131 — stateful activities, the tier that already ships.
- task-436 (review) — task durations, the model that removed time costs.
- task-437 — resolution order, which a budget must not make worse.
