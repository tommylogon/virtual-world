---
type: task
status: inprogress
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
- A character has a **fixed** per-turn allowance per tier, independent of N — decided
  2026-10-07 as `major: 1, minor: 1, free: 3, activity: 1`.
- The turn ends when the timeframe is full **or** nothing the character wants to do
  fits a remaining slot. Both constraints bind: minutes cap the total, tiers cap the
  composition.

**Position gates free actions (2026-10-07).** A free action is free in *slot*, not
in *reach*: `open`/`close`/`drop` are free, but only for something the character is
**at**. Reaching a door across the room costs `approach` (minor); crossing to another
area costs `go` (major). So a character with **no minor and no major** cannot approach
a new door to open it, even though `open` is free. And **a major slot may pay for a
minor** — spend the major on `approach` when out of minors. This is the precise
meaning of "the free tier is from where you stand": position is bought with the tiers
below, so the free tier cannot reach beyond the character's footing. Abilities are no
exception — a `free` `create flame` still needs the character to perceive/aim at its
target.

**Per-item cost override already exists (measured 2026-10-07).** `apply_action`
(`engine/tick_manager.py:384`) merges `ACTION_COSTS[verb]` with an `override_cost`
the caller passes, and `take_drop_actions.py` already passes
`item.properties.get("action_costs", {}).get("take", {})`. Today those entries carry
only `energy` (task-436 removed `time`). **352 adds `tier` to that same override:**
`action_costs: {"use": {"tier": "free"}}` on an item, so an intrinsic ability prices
its own slot as **data**. Resolver: `tier = item.action_costs.get(verb, {}).get("tier")
or VERB_TIER[verb]`.

**A trigger cannot price the slot.** The slot must be validated *before* the action
runs to know whether it fits; triggers fire in the effect pipeline *after* selection.
A trigger/condition may **gate whether the ability fires** (cooldown, target present)
— never the slot cost. If a cost must vary (free first use each turn, then major),
resolve it at validation from the item's `uses`/a condition, not from an effect.

**Default from the ability tag, override from the property (2026-10-07).** Ability-ness
is already a tag (`INTRINSIC_ABILITY_TAGS`), so the *default* tier for an intrinsic
ability's `use` is a code rule — `if _is_intrinsic_ability(item): tier = "minor"` —
and `action_costs.<verb>.tier` is the per-item, per-verb override. Do **not** invent a
`free_action`/`minor_action` **cost tag**: a tag cannot express *which verb* the cost
applies to (`use` free, `take` major), it duplicates the property, and the tag
namespace is a query vocabulary (task-98), not a scalar store. A "show me all free-use
abilities" list is derived from the property, never stored as a tag.

**Abilities have a different verb set, so a different cost table (2026-10-07).** An
intrinsic ability (`INTRINSIC_ABILITY_TAGS`) is non-physical, so it never gets
`take`/`drop`/`place` (task-737) — its verbs are `use`/`toggle` (activation) and
grant/revoke (acquisition). Its tiers therefore come from the *same* per-item
`action_costs.<verb>.tier` override, over that different verb set. Two abilities can
still cost differently (a free cantrip, a major meteor-swarm), which is exactly why
the cost is per item and per verb, not a single "ability cost".

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
| **free** | `look`, `listen`, `open`, `close`, `drop`, `toggle`, `speak`/`say`/`whisper`, `do`, `fear`, `interest`, `guess time`, `inventory`, `stats`, **`recall`**, **`alias`**, **`label`** | The free tier is the **at-a-distance** layer: what you can tell from where you stand. |
| **minor** | `grab`, `lead`, `toggle`, `release`, `stow`, `put`, **`place`**, `wear`, `remove`, **`approach`**, second and subsequent `go` in a turn | `grab`/`lead` already gate the existing chain slot. `approach` moves to a thing within the area; `go` crosses areas and is major. |
| **major** | first `go`/`dash`, **`examine`**, `take`, `use`, `eat`, `drink`, `attack`, `search`, `find`, `craft`, `combine`, `give`, `steal`, `fix`, `relieve`, `bind`/`enchant` | One per turn by default. |
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

1. ~~Slot counts, and specifically whether `major` is 1 or 2.~~ **Decided
   2026-10-07: `major: 1, minor: 1, free: 3, activity: 1`.**
2. ~~Whether the soak tier gets the same budget as the attended tiers.~~ **Decided
   2026-10-07: yes — the same budget per turn**, matching the parity requirement in
   `Simulation Model.md`. `soak.py`/`timeskip.py` `_policy_step` must be able to
   spend more than one slot.
3. ~~Whether `attack with <offhand>` and an ability verb get built here.~~ **Resolved
   2026-10-07: neither needs a new verb.** Abilities are intrinsic item nodes
   (`INTRINSIC_ABILITY_TAGS = {spell, ability, innate, intrinsic, power}`,
   `engine/equipment.py:16`) reached through `use`, priced by the per-item
   `action_costs.use.tier` (see The model). Off-hand is a **minor-tier attack**
   conditioned on "took the Attack action with a light melee weapon this turn" plus
   "holds a second light weapon" — a conditioned minor, not a verb. Only sub-question
   left: whether the off-hand *rules* (light weapon, no ability modifier unless
   Two-Weapon Fighting) ship here or with the combat work (task-537).
   **Recommendation: 352 declares the slot; the TWF rules ship with 537.**

## Related threads (2026-10-07)

- **`recall` is a free action** and is the retrieval side of **task-736** (the
  per-character cognitive map / remembered routes) and **task-734** (knowledge as
  memory). An agent that must spend a turn to remember its own knowledge will not
  ask; `recall` in the free tier is what makes self-query cheap. `alias`/`label`
  are the free-tier verbs behind **task-447** (nicknames/aliases) and the
  relationship `label` command.

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

## Landed (2026-10-07) — slice 1: the tier table

`engine/action_tiers.py`: `VERB_TIERS` (one verb, one tier — the single home the
model calls for), `tier_of(verb, item_node)` (resolves a per-item
`action_costs[verb].tier` override, then the intrinsic-ability default of `minor`,
then the table), and `DEFAULT_BUDGET`.

`tests/test_action_tiers.py` derives the dispatched verb set from
`routes/action_handlers.py` (95 tokens → 85 verbs) and fails when a command is
added without a tier — the classification's own acceptance criterion. 6 tests pass;
0 uncovered verbs.

Verbs the table above did not classify, decided here: `crawl`/`climb`/`jump` **major**
(movement); `stand`, `wake`, `flee`/`disengage`/`withdraw`, `manifest`/`vanish`
**minor**; `escape`/`struggle`, `teach` **major**; `dress`/`undress`/`strip`
**activity**; `stop`, `pick`, `pickup` **free**/**major** as listed; `toggle`
**minor** (the table above listed it in both free and minor — resolved to minor).

Remaining slices: (3) composer action list, (4) agent one-call list return,
(5) soak parity.

**Grab → move (2026-10-07).** `CHAIN_RULES.grab` gained `go` (`static/js/agent-engine.ts:18`),
matching `lead`, so a character can seize someone and drag them one area out of
danger (or into the dark) in one turn. `dash` is deliberately excluded — grab plus
a two-area dash is overpowered. The drag itself already exists —
`engine/grapple.py:drag_all` is called from `movement.py:743` on every `go`/`dash`,
carrying grappled targets — the chain simply did not offer the move after a grab.
Under this economy it becomes `grab` (minor) + `go` (major), and the chain rule is
retired with `CHAIN_RULES`. The prompt should still state the drag so the model
knows the option exists.

**Slice 2 — the per-turn budget (2026-10-07).** `Player.turn_slots` holds the
remaining allowance (`major:1, minor:1, free:3, activity:1`); `reset_slots` /
`spend_slot` in `engine/action_tiers.py` do reset and the downgrade (a higher slot
pays for a lower action — a major pays for an `approach`). A `_slot_gate` in
`handle_take_action` charges the slot after the activity/condition gates and
refuses with a tier-naming message ("You have no major action left this turn").
`tick_turn` resets every character's slots at the turn boundary. The live read
payload publishes `turn_slots`; `to_scenario_dict` strips it (a slot never survives
a turn). Charged on the attempt, not the outcome — you spent the action trying.

**Enforcement is opt-in (`enforce_slots`).** The gate runs only when a request sets
`enforce_slots`, so the *turn pipeline* is budgeted while out-of-band sends are not.
That matters because the inspector/paperdoll/craft buttons, the interjection lane
and "Speak as guest" all post through the same `runAction` global — default-on
enforcement would silently charge (and eventually refuse) those admin actions.

Landed: `ApiClient.action` and `runAction` take an `{ enforceSlots }` option
(`static/js/api.ts`), and the five agent-engine action submits pass it
(`agent-engine.ts` — human reply, final action ×2, retry, chain follow-up). The
`_speakLine` call deliberately does **not**: speech and emote are expression, not
budgeted actions.

Still open (slice 3/4):
- the human composer must show the remaining slots (`turn_slots` is in `/api/state`)
  and let the player spend several actions before ending the turn;
- the agent prompt must show remaining slots, and the decision must return a **list**
  of actions executed in order (task-352: exactly one decision call, never one per
  slot);
- `CHAIN_RULES` and the dash-burst special case retire once the list lands;
- until the loop changes, a character still takes one action per turn, so the budget
  rarely binds — the enforcement plumbing is in, the *multi-step turn* is not.

Prompt side landed: a `slots` section (`context-sections.ts`) renders
`=== ACTIONS LEFT THIS TURN === major N · minor N · free N` from `turn_slots`, and is
in the turn prompt's section lists (`turn-prompts.ts`). So the model can already
*see* its budget; it just is not yet told it may take several actions this turn.
The composer's budget readout is deliberately deferred with the loop, because
displaying "3 free" before a turn can hold several actions reads as a bug.

Tests: `tests/test_action_tiers.py` gains `reset_slots` / `spend_slot` /
downgrade / activity coverage — 10 pass; `tests/test_action_costs.py` 4 pass.
Enforcement lives only in `handle_take_action`, so the engine and soak paths are
untouched (slice 5 adds them). No test posts commands, so the unit suite is
unaffected.

## Landed (2026-10-08) — slice 3/4: budget-aware prompt + the multi-action loop

**This reverses the "one decision per turn returns a list" decision** (the
Agents section above). On 2026-10-08 the user chose to try the loop empirically
instead: hide the verbs the remaining slots cannot pay for, and loop the decide
call until the character is *done*. That is the old note's **Option B**, which
the Agents section had ruled out. It is adopted here **with an explicit
termination contract and a stated cost caveat**, and the one-call-list stays the
fallback if the loop proves too expensive.

Reconciliation with "LLM call count must never scale with turn length": the loop
is bounded by the **fixed** slot budget (`major:1, minor:1, free:3`), which does
not scale with `time_per_tick_minutes`. A character takes at most a fixed handful
of LLM-decided actions per turn regardless of the dial — N calls per *turn*, not
N calls per *minute*. On a soak that is still real cost; "exit on done" is what
keeps the average near one action, because a character who is fine stops.

**"Done" is a decision, not an empty meter.** The turn ends when the character
chooses `wait`/nothing, **or** the budget can pay for nothing, **or** the cap is
hit. The budget is a **ceiling, not a quota**: a character may take one action
and stop. Draining all five slots every turn would make everyone burn filler
(`look`, `inventory`) — the exact noise the model exists to prevent.

### Client tier mirror (the third list, made generated)

The hiding needs the tier table in the browser; the only copy was
`engine/action_tiers.py`. To avoid the "two homes" bug the module docstring warns
about, `tools/action_tiers_index.py` reads the Python table and emits
`static/js/agent/action-tiers.ts` (compiled to `.js` by `npm run build:ts`). The
mirror reproduces `tier_of` (per-item `action_costs[verb].tier` override →
intrinsic-ability default of `minor` → the table) and `spend_slot`'s downgrade
(a higher slot pays for a lower action). `--check` fails on drift. Script tag
added in `templates/index.html` before `contextual-actions.js`.

### Hiding

`computeItemActions` and `buildAvailableActionsBlock` (`contextual-actions.ts`)
take an optional `slots` and drop any verb `canAfford` says the budget cannot pay
for; `room-context.ts` feeds them `player.turn_slots`. `wait` is **exempt** — it
is the turn's exit, and hiding it would strand a character with no slots. With no
`turn_slots` published the filter is a no-op, so older callers and saves render
exactly as before. The hide is **guidance only**; the engine's `_slot_gate`
remains the enforcement.

### The loop

`agent-engine.ts` reactive mode wraps decide→act→react in a `while` (cap
`MAX_ACTIONS_PER_TURN = 5`). Iterations after the first re-`fetch()` the world and
rebuild the room context, so the prompt reflects the new position, revealed items
and spent slots; `loopLastResult` carries each result into the next prompt. The
loop exits on `choseNothing` (no action, or a NOOP verb) or an all-zero budget.
React still runs once per action, preserving per-action memory/emotion. The
turn's single `applyTurn`/`TurnQueue.advance` is unchanged — the loop is *inside*
the turn, so ticks and decay still run once per cycle, never per action.

### Verification status

**Unverified live** — the dev server was down (the user owns it), so this is
compile/unit-verified only: `npm run build:ts` clean, `node tools/unit/run.cjs`
618 passed, `tools/action_tiers_index.py --check` OK. Needs a live Kraktooth turn
to confirm: (a) after the major is spent the majors actually vanish from the
brackets; (b) the loop takes 2+ actions when the plan wants them; (c) a satisfied
character still ends at one. `MAX_ACTIONS_PER_TURN` is the kill switch — set it
to `1` to reproduce the pre-loop behaviour exactly.

Gate note: `tools/js_module_index.py --check` still lists two **pre-existing,
unrelated** Python modules without `@module`
(`engine/activities_loader.py`, `engine/effect_handlers/movement.py`); the gate
was red before this work. `engine/action_tiers.py` (untracked since slice 1)
gained its `@module` contract here.

## Related

- `docs/virtualWorld/Simulation Model.md` — the timeframe model and the
 supersession note this partially reverses.
- task-104 (review) — `/api/action/sequence`, never built; this task supersedes it.
- task-131 — stateful activities, the tier that already ships.
- task-436 (review) — task durations, the model that removed time costs.
- task-437 — resolution order, which a budget must not make worse.
