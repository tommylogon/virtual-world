---
type: task
status: inprogress
area: characters
priority: low
---

# task-534: Missing body reaction — sneeze

**Filed:** 2026-09-27
**Related:** task-213 (done), task-166 (done)

## Correction (2026-09-27) — the task was two-thirds wrong

This task was filed claiming **goosebumps, sneeze and itch** were all missing.
Re-measured before implementing: **only `sneeze` was missing.**

| | condition | emote trigger | test | status |
|---|---|---|---|---|
| `itch` | `CONDITION_DEFINITIONS` in `player_conditions.py`, `data/library/conditions/itch.json` | `EMOTE_TRIGGERS` in `involuntary.js` | `test_involuntary.js` (pre-existing) | **already done** |
| `goosebumps` | `CONDITION_DEFINITIONS` in `player_conditions.py` | `EMOTE_TRIGGERS` in `involuntary.js` | — | **already done** |
| `sneeze` | — | — | — | **genuinely missing** |

The original claim rested on a bad regex search that missed
`engine/player_conditions.py` entirely and matched "pitch"/"switch" inside
`pitch_black` and `switch` statements. Both reactions are complete: condition
definition, tiered `symptoms`, non-mature catalog entry, emote pool, and for
`itch` a unit test. `goosebumps` also has a body-state descriptor at
`engine/equipment.py`.

The "do not create two sources of truth" concern in the old draft applies to
`goosebumps`: the `equipment.py` string and the condition are the same state
described twice, but that is pre-existing and consistent (one is a narration
descriptor, the other a mechanical condition) — so it was left alone.

## What shipped

**`sneeze`** added as the third body-reaction condition, matching its two
siblings exactly:

- `data/library/conditions/sneeze.json` — catalog entry. `"mature": false`, so it
  is never gated behind `mature_content`; `ends_on: ["blow_nose", "cure",
  "duration"]`; short `default_duration: 3`, `stack: "refresh"`.
- `engine/player_conditions.py` — the runtime definition, under the same
  "Involuntary body-reaction flavor conditions (task-166)" comment block as
  `itch` and `goosebumps`.
- `static/js/agent/involuntary.js` — added to **both** tables:
  - `SPEECH_TRIGGERS`: `{ type: 'sneeze', chance: 0.55 }` — a sneeze is an onset
    rather than a pause, but it is spliced the same way as a cough: the line
    survives and the sound interrupts it.
  - `EMOTE_TRIGGERS`: three suffixes.
  - The module header, which **enumerated the delivered set** and would
    otherwise have become the next stale comment, now lists the full body-reaction
    set and states that these conditions are non-erotic, `mature: false`, and
    applied by content rather than by this module.

**Deliberately not added:** a driver. `itch` and `goosebumps` are applied by
triggers or actions in content; `sneeze` follows the same pattern. Inventing an
environment rule (dust, allergens) would have been content design, not this task.
A condition nothing applies simply never fires, which is the same as its
siblings today.

## Tests added — `tools/unit/test_involuntary.js`

- a sneeze interrupts speech **without replacing the line**
- a sneeze emote is pronoun-rendered, no unrendered `{they}`
- **regression** guard: `goosebumps` still drives an emote, so a future rework of
  the body-reaction table cannot silently break the two that predate this task
- a conditioned sneeze **always** fires, and **never** appears in the random
  baseline at any roll — a sneeze is a state, not a tic

> The last test records a non-obvious property worth knowing: condition-driven
> **emotes have no chance roll at all** (`involuntary.js`, the `EMOTE_TRIGGERS`
> loop) — the condition's presence fires the pool unconditionally. Only the
> *speech* path and the random baseline roll. An earlier draft of this test
> assumed otherwise and was wrong.

## Acceptance criteria

- [x] `sneeze` reachable as a reaction, matching the `itch`/`goosebumps` pattern.
- [x] `sneeze` present in **both** `SPEECH_TRIGGERS` and `EMOTE_TRIGGERS`.
- [x] Non-erotic: `"mature": false` in the catalog entry, so it is never gated
      behind `mature_content`.
- [x] Each new reaction has tests in task-166's existing style.
- [x] The module header lists the new types and the set is no longer stale.
- [x] Regressions guarded for `goosebumps` (and `itch` already had one).
- [x] Documented in the user guide / technical docs per the standing rule:
      `docs/virtualWorld/Rules Engine/Conditions System.md` (catalog table) and
      `docs/virtualWorld/AI & Narration/Agent Engine.md` (new "Involuntary
      Reactions" section covering the full body-reaction set and the
      no-roll-on-conditioned-emotes rule).
- [ ] Tests run — **the user asked to hold test runs**, so the four new
      `test_involuntary.js` cases are written but unrun. `node tools/unit/run.cjs`
      must be run before this closes.
- [ ] Full suite compared against the baseline.

## Non-goals

- The mature traits — task-487 and task-488 own `exhibitionist` and `single_track`.
- Any new vitals or conditions beyond what `sneeze` needs.
- Deciding what *applies* `sneeze` in content — that belongs to whoever authors
  the scenario, exactly as for `itch` and `goosebumps`.
- Reworking the chance / `NERVOUS_BOOST` tuning — task-166 settled it.

## Related

- task-213 (done) — origin; its body-reaction accounting listed all three as
  missing, which was wrong for `itch` and `goosebumps`
- task-166 (done) — the involuntary-action system this extends
