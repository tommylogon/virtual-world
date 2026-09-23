---
type: task
status: todo
area: graph
priority: low
---

# task-435: Offline generators still mint way-orientation templates

**Filed:** 2026-09-21  
**Split out of:** task-395 (way-orientation authoring), which removed the bulk
fill and the engine-side mint but left the generators that produced it.

## Problem

task-395 removed `fix_way_orientation` and added `clear_way_fix_fields`, which
reverts the minted values on demand by matching them **exactly**:

- `pass_message == "You pass through <name>."`
- `visible_in_direction == "A glimpse of <source> beyond."`
- `cardinal == "north"` where the edge's `direction` is not a real cardinal

That made the *result* clean, and task-395's own claim was "no bulk op writes way
data anymore". Measured, that is **false at the repo level** — the offline
generators still write those exact strings:

| Tool | Line | Writes |
|---|---|---|
| `tools/build_scenario.py` | 80-81 | `"You pass through {name}."` |
| `tools/assemble_scenario.py` | 239 | same template |
| `tools/sync_scenario_to_library.py` | 147 | same template |
| `tools/generate_scenario.py` | 212 | same template |

And one writes a **near-variant** the exact match will not catch:

- `tools/fix_scenario_authoring.py:78-79` → `"You pass through the {noun}."`
  (note the article) — so a scenario run through it can never be cleaned by the
  cleanup op, and looks authored while being generated.

## Why it matters now

A scenario regenerated or assembled by these tools is born minted. The cleanup op
is the only remedy and it is a *manual button*, so the mint silently returns with
the next generation run — including into any new world (task-398's deterministic
generation is a likely future caller).

## Design question to settle first

The templates exist because a generator has to put *something* in the field, and
it has no text model. Options:

1. **Leave the field empty** when generating, and let the engine's existing
   fallbacks supply the line at read time — that is what the validator's
   downgrade to `info` already assumes (`engine/movement.py:780-783` and
   `engine/area_description.py:563` both have sane defaults). Cleanest: a
   generated way carries no invented prose at all.
2. **Generate honestly-labelled placeholders** (e.g. leave a marker the cleanup op
   recognises by prefix rather than exact match) so a human is prompted to
   author it. Better ergonomics, more moving parts.

Whichever: the near-variant in `fix_scenario_authoring.py` must be reconciled —
either it adopts the same convention or the cleanup match becomes prefix-based.

## Acceptance

- No offline generator writes `"You pass through …"` or `"A glimpse of … beyond."`
  into way data.
- A scenario produced by each generator has zero fields the cleanup op would
  remove, asserted by a test.
- `clear_way_fix_fields` remains exact-match (its safety property is that it never
  touches authored prose) — so the fix is on the generation side, not by loosening
  the match.
- The validator still reports a missing `pass_message`/orientation as `info`, and a
  way with no invented prose reads correctly through the engine fallbacks.

## Non-goals

- Re-filling way orientation for existing scenarios (task-395 decided on-demand
  remediation is right, and the camp data is already clean).
- Authoring orientation for the mansion/Pines areas (that is task-324's area pass).
