---
type: task
status: inprogress
area: gameplay
priority: high
---

# task-464: Timeskip actions (idle / leisure / search / explore / travel)

**Filed:** 2026-09-22
**Hub for:** task-466 (interrupt & relevance evaluator), task-467 (belief-based
travel + maps), task-468 (interrupt-capable background agendas)
**Depends on:** task-436 (duration on tasks — the substrate), task-414 (server-side
batch advance + world lock — the transport), task-399/409 (soak policies),
task-466 (interrupts), task-412 (promotion + summary/memory), task-437 (deterministic
resolution order).

## Goal

Give the player **timeskip actions**: declare an intent plus a span of game time,
and the world advances through that span at maximum speed with the player's own
decisions supplied by a **scripted policy** instead of by the human. The timeskip
is interrupted the moment something relevant happens to the player, at which point
the human controller takes over again at that tick.

The player's character is **never frozen and never protected**. Vitals decay, the
environment applies, and biology fires — wait two hours in a forest with no food or
water and you can die. That is the point: the timeskip removes *decisions*, not
*consequences*.

This generalizes something already shipped: **sleep is a timeskip** (a duration task
you do nothing through, with the world ticking and interrupts possible). Timeskip
actions formalize that into a family with different policies.

Superseded: the original `protect_human` temporal-stasis proposal. There is no
stasis mode; the only dial is *what policy stands in for you*.

## One clock, one action flow, only the controller changes

Per [[Simulation Model]], the human's character runs the same action flows as
everyone else. During a skip the engine swaps the human's controller for a
deterministic policy and runs every other character at soak/background fidelity.
Nothing about the rules changes — only who chooses.

- **Zero LLM calls inside a skip.** Policies are scripted and deterministic.
- The skipped character's policy is a **valid but suboptimal** policy, so anything a
  timeskip does is reachable by normal play (cognition refines, never adds capability).
- Interrupt = **promotion boundary**; the human resumes at that tick.
- Every policy decision writes a **trace fact with a why-tag** so the human's memory
  on resume is honest ("you waited/mingled/searched", not "time passed").

## The intent family

| Intent | Agency during skip | Typical ends |
|---|---|---|
| **Idle / wait** | none — no eating, no wandering, no involuntary suppression | duration; vital/involuntary/threat interrupt |
| **Leisure / mingle** | deterministic maintenance + social: eat/drink (carried or bought), roam the current area, socialise | duration; threat/discovery interrupt |
| **Search** | systematic scan of the area and its containers for a type/tag/specific item | found; budget out; interrupt |
| **Explore** | move into the frontier (undiscovered exits), preferring unexplored areas | interest-tag match; discovery; threat; budget |
| **Travel / fast-travel** | follow a known route, or a heading + budget toward a believed destination | arrival; hazard; low vital; interesting find |

All intents share: a **duration/budget** (in in-game minutes), interrupt conditions
(task-466), and a resume summary (task-412).

## Minute resolution (non-negotiable)

A skip of `D` in-game minutes advances **1-minute ticks** regardless of the
scenario's `time_per_tick_minutes` frame dial, so interrupts land on a minute
boundary. Normal play keeps the scenario's turn length. This is the one place where
the timeskip deliberately does not follow the frame dial.

## Interrupts

Interrupts are evaluated per minute by the shared **task-466** evaluator. Minimum
set for v1:

- **Threat to me:** attack, grapple, a steal attempt (the existing `steal_item`
  path already emits a "notices" response), a hostile approach.
- **Vitals / conditions:** a meter crossing its danger threshold, a new condition, a
  hazard the character cannot passively survive.
- **Involuntary actions:** biology firing (bladder, itch, etc.) ends the skip and
  hands control back — "master of self control" is not a free pass.
- **Discovery:** an item/way/area/character matching a declared search target, an
  interest tag (`Player.interest_tags`), or a known goal.
- **Travel-specific:** an interesting item or way, an animal or enemy, a vital floor,
  or arriving at the believed destination (found or found-not-there).

On interrupt: stop at the tick boundary, keep the policy's trace, present the
situation as the normal prompt. No special state is needed — the world is simply at
that minute.

## Transport, lock and jobs

- Extend the task-414 endpoint rather than adding a second transport:
  `POST /api/world/timeskip {intent, minutes | turns, target?, heading?, interrupt_policy}`
  returning a bounded summary (clock, deaths, notable trace), never the full log.
- Long spans must not hold a request worker open: reuse the `engine/soak_runner.py`
  job/registry/progress/cancel shape as a **live-world** variant. The client polls;
  Cancel stops at a tick boundary and still returns the elapsed summary.
- Concurrency: hold the same lock the normal step path uses; reject a skip while a
  turn/step/LLM call is in flight and reject step/turn while a skip runs (queue or
  409 — pick one and document it); one active skip at a time.
- Persistence: **one autosave at the end** (or on cancel), never per tick. A page
  reload mid-skip abandons the job at the last completed tick boundary.
- Seed the RNG so a skip is reproducible.

## Per-intent detail

### Idle / wait
No policy actions at all. Vitals, environment and conditions tick normally; the
character does not eat, drink, or defend beyond what normal rules impose. Involuntary
actions fire and interrupt. Walking into a blizzard to "wait 8h" is a real decision
with real consequences.

### Leisure / mingle
A deterministic maintenance-and-social policy scoped to the current area: eat/drink
when a need crosses its drive threshold, using carried items or buying from a vendor;
roam; take part in the existing background social/relationship system (task-423). It
does **not** leave the area and does not make risky choices. Threat/discovery
interrupts still apply.

### Search
A target spec — specific item id, item type, or tag — plus an area scope. The policy
works the area and its containers using existing look/examine/item-reach rules,
respecting hidden/discovery gating and any perception requirement. Success ends the
skip (or raises an interrupt); budget-out ends it with partial findings recorded in
the trace.

### Explore
Move toward the frontier (per-player `discovered_exits`, hidden ways) preferring
unexplored areas. Stops on an interest-tag match, a discovery, a threat, or budget
exhaustion. Shares the heading/frontier primitive with belief-based travel.

### Travel / fast-travel
Two primitives:

1. **Known route** — a discovered path through the graph: duration is the sum of the
   route's task durations (task-436), not an arbitrary number of turns.
2. **Belief / heading** — "go west 2h"; the destination is a belief in memory
   (task-403), not a node. Resolve by heading + budget, discovering whatever lies
   that way, and validate the belief on arrival. Maps and directions gained from
   dialogue, items or hearsay write the knowledge that upgrades a belief into a known
   route/area.

Details in **task-467**.

## "While you waited" summary and memory

Built from the trace/turn events already written during the skip: elapsed clock,
deaths and causes, fights, arrivals/departures, items taken/consumed/spoiled,
conditions gained, search/explore results. v1 is deterministic templates over
recorded facts; an optional single-paragraph LLM narrative is one call for the whole
skip, opt-in.

The human gets exactly one bounded `Player.add_memory(source: "timeskip")` entry
built with the task-412/399 consolidation template, so the next prompt knows what
happened — including that vitals decayed. Repeated resume must not duplicate it. NPCs
get their normal consolidation.

## UI

- The intent entry points (top bar, command palette, and commands): `wait`, `mingle`,
  `search`, `explore`, `travel`.
- A real dialog per intent: duration presets (1 h, 4 h, until dawn/dusk/morning),
  custom minutes, and — for travel/explore — a heading or target, with the resolved
  clock and an estimate ("8 h ≈ 480 min · 23 characters · a few seconds").
- Progress panel with Cancel; suppress the normal turn-feed animation and post one
  summary entry instead of replaying hundreds of turns. Accessible result card.

## Edge cases

- Human mid-action or with queued actions → reject until flushed; never silently
  discard.
- Human in combat / being attacked → blocked unless the attack resolves as a
  background event, else "You can't wait now".
- Only human characters exist → the skip just advances the clock.
- Death during a skip (needs, hazard, violence) → the skip ends immediately, control
  returns, and the summary states the cause.
- An NPC the player knows dies → surfaced in the summary and the player's memory.
- Very large budgets → disclose granularity; the span is still minute-resolved.

## Acceptance

- A requested span advances the clock by exactly that span, minute-resolved.
- Vitals/conditions/environment change according to the same rules as normal play
  (assert: an idle skip over N minutes equals an N-minute plain loop with no actions).
- Involuntary-action firing interrupts the skip and returns control.
- A vital/condition danger crossing interrupts and returns control.
- A co-located theft attempt interrupts; a search/explore interest match interrupts.
- LLM client call count is **zero** during the skip; the human's character is
  re-consulted only at the next decision boundary after resume (task-412).
- Exactly one bounded memory is added; resume/idempotency adds no duplicates.
- Cancel mid-skip returns a completed-tick summary and leaves a usable world.
- Concurrent step/LLM/skip is rejected with a clear error, never interleaved.
- Save → load after a skip preserves the advanced clock, NPC changes and the memory.

## Non-goals

- Any form of player stasis / harm immunity.
- Running LLM actions inside the skip loop.
- A general offscreen economy or full combat system.
- Replay/observation UI (task-415, cancelled).

## Open questions

- Does a skip refuse to start when the character is already in a lethal hazard, or
  start and interrupt immediately? Proposed: refuse, with the reason shown.
- Explore heading: chosen by the player, or "most frontier" auto? Proposed: player
  heading optional, auto-frontier default.

## Verification

- Unit: `advance(intent, minutes, policy)` advances the clock exactly; idle equals a
  plain N-minute loop; policy decisions respect traits/schedule/vitals.
- Unit: interrupt evaluator returns the expected reasons for threat/vital/involuntary/
  discovery fixtures; stepping stops on the first one.
- Unit: cancel at minute K returns a K-minute summary and a usable world.
- Integration: `/api/world/timeskip` validation, clamping, conflict handling (409),
  summary shape.
- Manual: goblin camp, "wait until morning" — overnight deaths/arrivals in the
  summary and the next prompt reflects elapsed time and decay.

## Evidence (starting points)

- `virtual_world_engine.py:54` — `time_per_tick_minutes` (the frame dial; skip forces 1).
- `engine/tick_manager.py:173` — `tick_turn()` decay/conditions/environment for all.
- `engine/tick_manager.py:797–806` — simple-NPC + background-sim calls (the soak path).
- `engine/background_simulation.py` — due-scheduler for background characters.
- `engine/activities.py` — duration/blocking activities (sleep is the existing precedent).
- `engine/trace.py` — the fact log the summary/memory is built from.
- `engine/items/transfer_actions.py` — `steal_item` (the theft interrupt source).
- `engine/soak_runner.py` / `tools/soak_sim.py` — the job + N-tick loop to mirror.
- `routes/action_handlers.py:1129–1132` — the current `tick_turn()` call site.

## Progress 2026-09-22 — engine + HTTP slice landed (in progress)

`engine/timeskip.py`, `engine/interrupts.py`, `routes/timeskip_ops.py`,
`POST /api/world/timeskip` (registered in `routes/action.py`), 25 tests.

- [x] `advance(gs, minutes, intent=...)` for all five intents, minute-resolved
  regardless of `time_per_tick_minutes` (restored afterwards), one skip at a
  time, no stasis (vitals decay; idle can kill).
- [x] Interrupts via task-466: death / threat / vital crossing / involuntary /
  discovery / arrival hand control back at the tick boundary.
- [x] Policies ride the soak tier's own decisions (`BackgroundSimulation`),
  so a skip does what the same character would do unattended; zero LLM calls.
- [x] Exactly one bounded `source:"timeskip"` memory built from deterministic
  templates (task-412 slice); trace entry with a `timeskip:<intent>` why-tag.
- [x] `POST /api/world/timeskip {intent, minutes|hours|turns, target, heading,
  watch_tags}` returning the summary; travel derives its span from the route.
- [x] Frontend: "⏩ Wait / Timeskip…" menu item + dialog (intent, duration preset/custom, target, heading, watch tags) posts to the route, renders the summary and refreshes `worldState`.
- [x] Concurrency: one skip at a time, and `/api/action`, `/api/turn/apply` and `/api/llm_respond` return 409 while a skip runs (`timeskip.is_running()`), so nothing interleaves with the skip's clock.
- [ ] Progressive progress + Cancel while running (needs the job runner).
- [ ] Long spans via a soak-runner-style job (the route caps at 1,440 min).
- [ ] Leisure "buy from a vendor" and richer social behavior.
- [ ] Explore frontier preference tied to generation (task-398).

## Verification

Full suite: 60 failed / 3356 passed (same 60 pre-existing). `tests/test_timeskip.py` → 25 passed.
