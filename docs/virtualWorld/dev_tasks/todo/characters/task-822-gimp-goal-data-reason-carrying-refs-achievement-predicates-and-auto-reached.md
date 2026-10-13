---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
---

# task-822: GIMP: goal data - the full mission record, achievement predicates, and auto-reached

**Filed:** 2026-10-13
**Related:** task-807, task-810, task-811, task-705, task-704, task-714

## What

A goal is a **personal mission**, so its record is a mission record. Today it carries ids and a status and little else; that is too thin to read, rank, or complete. The record is these fifteen fields (grouped), plus the task-811 log:

**Want and drive**
| # | field | means | today |
|---|---|---|---|
| 1 | `id` | stable key | exists |
| 2 | `what` | the want, one line ("become chief") | exists |
| 3 | `why` | the drive (GIMP **M**otivation) | exists as `motivation` |
| 4 | `intention` | the commitment / tenor (GIMP **I**ntention) | exists |
| 5 | `hoped_for` | prose: what they expect to get ("the chief's staff") | **new** |

**Provenance and standing**
| # | field | means | today |
|---|---|---|---|
| 6 | `source` | where it came from: `self` / `obligation:<id>` / `schedule:<id>` / `need:<name>` / `event:<id>` | **new** |
| 7 | `opened_tick` | since when (age feeds salience and replay) | **new** |
| 8 | `priority` | how much they care, against their *other* goals - what selects the active one | **new** |
| 9 | `visibility` | `known` / `private` / `secret` - the thing they are not saying | **new** |

**Shape: gate, target, relation**
| # | field | means | today |
|---|---|---|---|
| 10 | `blocks[]` | gates; each ref carries a `note` saying *why* | exists (+ `note`) |
| 11 | `achieve[]` | success predicates; each ref carries a `note` saying what reaching it means | **new** |
| 12 | `links[]` | related goals (chaining) | exists |
| 13 | `deadline` | tick at which an un-reached goal fails | **new** |

**State**
| # | field | means | today |
|---|---|---|---|
| 14 | `status` | proposed / active / blocked / reached / dropped (`engine/goals.GOAL_STATUSES`) | exists |
| 15 | `progress` | **projection** over the world - which `achieve` refs are met, partial counts - never stored | **new** |

plus `Player.goal_log` (task-811): the transition history.

**Stored versus projected.** `status` is stored. `blocked` (from task-810), `progress`, and any "is it met" answer are **projections computed on read**, the same rule `blocked_by` already follows. Do not store a derived value.

**Not fields, and why.** The **grant** (task-823: a reached goal raises an event; a *trigger* grants the item). The **how** (that is the Pursuit, bound by `intention` - the goal says *what*, the pursuit says *how*). Per-character numeric weights (those are the **disposition**, derived from traits - task-802). `achieve`/`blocks` reuse the `prefix:value` ref language the record already speaks.

## Why

A goal that reads "become chief" plus a bare `character:Croak-Mother` is a boolean, not a mission: you cannot tell whether she blocks, enables or is the target, whether the goal is even *about* her, how much the character cares, where it came from, or what "done" looks like. Task-704's own acceptance asks for a "readable character reason and structured objective", and both halves are missing. Without `achieve` there is no target for `goal_alignment(action, goal)` to align to and a goal can never complete itself; without `priority` there is no way to choose which of a character's goals is the active one.

## How

- `engine/goals.normalize`: accept a ref as a bare string (`"character:Croak-Mother"`, back-compat) or `{"ref": ..., "note": "she will not approve an outsider"}`; keep `blocks`/`links` as lists and add `achieve` as a list of the same shape.
- Add `source`, `opened_tick`, `priority`, `visibility`, `deadline`, `hoped_for` as validated scalar fields (defaults: `source="self"`, `priority=0`, `visibility="known"`, `deadline=None`). Malformed values fall back like `status` does today.
- `reached(goal, resolvers)` - true iff every `achieve` ref resolves true; `sync_reached(player, resolvers, tick, log)` flips met active goals to **`reached`** and appends to `goal_log`. Call it from the per-turn pass the soak already runs (`engine/background_simulation.py`) and from the player-update path, so both tiers see the flip.
- `achieve` needs an explicit combinator - `all` (default) or `any`, declared per goal. A goal with two alternative successes ("responsibilities agreed" **or** "a joint operation succeeds") is unreachable under `all`.
- `achieve` leaves are **task-705's** (`tag:`, `state:`/`at:`, quantity, area-function, knowledge, ownership); `item:` / `character:` / `goal:` already resolve in `world_resolvers`. No second condition language.
- **Every prefix needs a subject.** `tag:meaningful_challenge` is meaningless until it says a tag on *what* - the holder, a named entity, or the world. Task-705 declares the subject per leaf; this card consumes that declaration.
- **Every ref must be a fact the world can flip.** `event:thrazz_acknowledges_skill` is a sentence and is unqueryable, so the goal can never complete. `flag:thrazz_acknowledged` (a stored fact a trigger or action sets) or `tag:character:Thrazz:respects_zikka` is checkable. Prefer the flippable form.
- `world_resolvers.character` is *node existence*, which is permanently true and useless as a gate. Co-location is a different predicate (`present:character:X`).
- `priority` is **1 = highest**, declared here and load-bearing in task-704.
- `deadline` (tick) - un-reached at the tick becomes **`dropped`**.
- Serialize in the players block; strip in `lite`; render `note`, target, priority and visibility in the Mind panel.
- `hoped_for` is prose only. The actual consequence is **not** here; it is task-823.

## Steps to verify

1. Author an active goal whose `achieve` is a satisfiable ref (e.g. `item:item_chiefs_staff` held), satisfy the world, run a turn.
   - expected: the goal's `status` becomes `reached`, `goal_log` gains a `reached` entry at the tick, and no `goal complete` verb was called.
   - observed: TODO
2. Open the goal in the Mind panel.
   - expected: each ref renders with its `note`; the target reads "achieved when ..."; a blocked ref reads why; priority and visibility show.
   - observed: TODO

## Acceptance

- [ ] The record round-trips all fifteen fields (`id`, `what`, `why`, `intention`, `hoped_for`, `source`, `opened_tick`, `priority`, `visibility`, `blocks`, `achieve`, `links`, `deadline`, `status`, and the projected `progress`) through normalize + serialization + a save.
- [ ] A goal carries `achieve` refs; `reached()` is true iff all resolve true against live world state.
- [ ] An active goal flips to `reached` when the world satisfies `achieve`, with `goal_log` recording the transition - no verb required.
- [ ] `blocks`/`links`/`achieve` refs may carry a `note`; a bare string still loads, and the note renders.
- [ ] `source`, `priority`, `visibility`, `deadline` validate with a safe default; a malformed value is corrected, not guessed.
- [ ] `achieve` leaves come from task-705's vocabulary; `item`/`character`/`goal` reuse `world_resolvers`; no parallel predicate language.
- [ ] Every prefix declares its subject, and every `achieve` ref is a fact the world can flip (no `event:<sentence>`).
- [ ] `dormant` is a valid status (`engine/goals.GOAL_STATUSES`): held but not worked, distinct from `proposed`, and excluded from `active()`.
- [ ] A `deadline` moves an un-reached goal to `dropped` at its tick.
- [ ] `achieve` declares `all` or `any`; a goal with alternative successes is reachable.
- [ ] `progress` and `blocked` are projections on the payload, never persisted.
- [ ] Deterministic: the same state yields the same `reached` verdict (no RNG).

## Files

- `engine/goals.py` (fields, `achieve`, `reached`, `sync_reached`, ref `note`)
- `engine/serialization.py` (payload shape, lite strip)
- `engine/background_simulation.py` (the per-turn `sync_reached` call)
- `static/js/inspector/mind-view.ts` (render `note`, target, priority, visibility)
- `tests/test_goals.py`
