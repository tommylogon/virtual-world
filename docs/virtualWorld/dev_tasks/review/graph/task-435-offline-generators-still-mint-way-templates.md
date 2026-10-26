---
type: task
status: review
area: graph
priority: low
wiki: "[[World Building/Graph System]]"
---

# task-435: Offline generators still mint way-orientation templates

**Filed:** 2026-09-21  
**Split out of:** task-395 (way-orientation authoring), which removed the bulk
fill and the engine-side mint but left the generators that produced it.

## Why

task-395 removed `fix_way_orientation` and added `clear_way_fix_fields`, which
reverts the minted values on demand by matching them **exactly**:

- `pass_message == "You pass through <name>."`
- `visible_in_direction == "A glimpse of <source> beyond."`
- `cardinal == "north"` where the edge's `direction` is not a real cardinal

That made the *result* clean, and task-395's own claim was "no bulk op writes way
data anymore". Measured, that is **false at the repo level** - the offline
generators still write those exact strings:

| Tool | Line | Writes |
|---|---|---|
| `tools/build_scenario.py` | 80-81 | `"You pass through {name}."` |
| `tools/assemble_scenario.py` | 239 | same template |
| `tools/sync_scenario_to_library.py` | 147 | same template |
| `tools/generate_scenario.py` | 212 | same template |

And one writes a **near-variant** the exact match will not catch:

- `tools/fix_scenario_authoring.py:78-79` → `"You pass through the {noun}."`
  (note the article) - so a scenario run through it can never be cleaned by the
  cleanup op, and looks authored while being generated.

## Why it matters now

A scenario regenerated or assembled by these tools is born minted. The cleanup op
is the only remedy and it is a *manual button*, so the mint silently returns with
the next generation run - including into any new world (task-398's deterministic
generation is a likely future caller).

## Design question to settle first

The templates exist because a generator has to put *something* in the field, and
it has no text model. Options:

1. **Leave the field empty** when generating, and let the engine's existing
   fallbacks supply the line at read time - that is what the validator's
   downgrade to `info` already assumes (`engine/movement.py:780-783` and
   `engine/area_description.py:563` both have sane defaults). Cleanest: a
   generated way carries no invented prose at all.
2. **Generate honestly-labelled placeholders** (e.g. leave a marker the cleanup op
   recognises by prefix rather than exact match) so a human is prompted to
   author it. Better ergonomics, more moving parts.

Whichever: the near-variant in `fix_scenario_authoring.py` must be reconciled -
either it adopts the same convention or the cleanup match becomes prefix-based.

## Acceptance

- [x] No offline generator writes `"You pass through ..."` or `"A glimpse of ... beyond."`
  into way data.
- [x] A scenario produced by each generator has zero fields the cleanup op would
  remove, asserted by a test (`test_offline_generators_do_not_mint_cleanable_templates`).
- [x] `clear_way_fix_fields` remains exact-match (its safety property is that it never
  touches authored prose) - so the fix is on the generation side, not by loosening
  the match.
- [x] The validator still reports a missing `pass_message`/orientation as `info`, and a
  way with no invented prose reads correctly through the engine fallbacks.

## Non-goals

- Re-filling way orientation for existing scenarios (task-395 decided on-demand
  remediation is right, and the camp data is already clean).
- Authoring orientation for the mansion/Pines areas (that is task-324's area pass).

## Code check (2026-09-24) - still open, partially remediated

The exact minted template is still written by the offline generators:

- `tools/build_scenario.py:93-94`, `tools/assemble_scenario.py:253`,
  `tools/sync_scenario_to_library.py:147` - `"You pass through {name}."`
- `tools/fix_scenario_authoring.py:78-79` - the near-variant
  `"You pass through the {noun}."`
- `tools/generate_scenario.py:212` now writes a *different* template
  (`"You pass from {a} toward {b}."`), which the exact-match cleanup never
  removes - so the task's "reconcile the near-variant" note is now two variants.

The cleanup half already shipped (`clear_way_fix_fields`,
`routes/graph_ops.py:973-1004`; `fix_way_orientation` removed), and no generator
test asserts "zero cleanable fields". This is a prerequisite for clean task-398
generation output.

## What

Stop the offline scenario generators from writing invented way prose. Five
tools still stamp a `pass_message` template onto every way they emit, so a
generated scenario is born carrying the exact strings
`clear_way_fix_fields` was built to remove - and two of the five write
variants the exact-match cleanup cannot catch, so the mint survives the
remedy and looks authored while being generated. The fix belongs on the
generation side: a generated way carries no invented `pass_message` at all,
and the engine's existing read-time fallbacks supply the passage line when a
character goes through it. The cleanup op itself keeps its exact match,
because that exactness is the property that guarantees it never removes
author-written prose.

## Reconnaissance (2026-10-20) - VERDICT: STILL_VALID

Re-ran the mint check against the live generators. Every line number in the
card's "Code check (2026-09-24)" section has drifted; the underlying finding has
not. Measured 2026-10-20:

| Tool | Live line | Writes |
|---|---|---|
| `tools/build_scenario.py` | 94 | `"You pass through {way['name']}."` |
| `tools/assemble_scenario.py` | 255 | `"You pass through {way_name}."` |
| `tools/sync_scenario_to_library.py` | 149 | `"You pass through {node.get('name', node_id)}."` |
| `tools/generate_scenario.py` | 212 | `"You pass from {a_name} toward {b_name}."` |
| `tools/fix_scenario_authoring.py` | 79 | `"You pass through the {_noun_for(way)}."` |

That is **5** minted templates across **5** tools (the card counted 4 plus one
near-variant). `generate_scenario.py`'s `"You pass from … toward …."` is still a
third variant the exact-match cleanup cannot remove, so the "reconcile the
near-variant" note is still two variants open.

`clear_way_fix_fields` is still alive and still exact-match: it is reached at
`routes/graph_ops.py:1059` (via `optype == 'clear_way_fix_fields'`) and declared
in `engine/nl_editor_validation.py:36`. `fix_way_orientation` is confirmed gone
from the repo (zero hits). No test asserts "zero cleanable fields on a generated
scenario" - `tests/test_library_refresh.py:45` still hard-codes
`'pass_message': 'You pass through.'` as a fixture value, and
`tests/test_ghost.py:187` asserts `"pass through"` appears in output, which is
the engine fallback, not a minted field.

Nothing newer has touched this. task-395 (way-orientation authoring) is done and
its on-demand cleanup op is unchanged; task-398 (deterministic scoped structure
generation) is done and is a likely future caller of these generators, so the
prerequisite status is unchanged. The card stays in `todo`.

## How

1. **Leave the field empty in the generators.** Drop the `pass_message`
   default from the way properties each tool emits:
   - `tools/build_scenario.py:94` - `"You pass through {way['name']}."`
   - `tools/assemble_scenario.py:255` - `"You pass through {way_name}."`
   - `tools/sync_scenario_to_library.py:149` -
     `"You pass through {node.get('name', node_id)}."`
   - `tools/generate_scenario.py:212` -
     `"You pass from {a_name} toward {b_name}."`
   - `tools/fix_scenario_authoring.py:79` -
     `"You pass through the {_noun_for(way)}."`

   A generated way then has no `pass_message` key at all. This settles the
   card's open design question in favour of option 1 (leave the field empty
   and let the engine fall back at read time) and it removes the need to
   reconcile the near-variant separately: with no generator writing prose,
   there is nothing for the exact match to miss.
2. **Do not loosen the cleanup op.** `clear_way_fix_fields`
   (`routes/graph_ops.py:1059-1098`) stays exact-match, because that exactness
   is the safety property - it is what guarantees the op never touches
   author-written prose, and `tests/test_way_orientation_cleanup.py` pins
   both directions. The fix is on the generation side, not in the match.
3. **Confirm the read-time fallback carries an empty way.**
   `engine/movement.py:864-875` reads `pass_message` and, when it is empty,
   returns the `KIND_MOVE_LINE` default ("You head through the {d}.") plus
   the arrival suffix; `engine/area_description.py:289` reads the same
   property for the exit description. Both are read-only for this task: a
   way with no `pass_message` already reads correctly, which is what makes
   option 1 safe.
4. **Add the missing test.** `tests/test_way_orientation_cleanup.py` is the
   natural home. Add a case that runs each generator over a scratch world
   and asserts the generated ways carry zero fields the cleanup op would
   remove - including the two variants (`"You pass through the {noun}."` and
   `"You pass from {a} toward {b}."`) that the exact match never caught.
   No test asserts this today; the existing suite only covers hand-seeded
   nodes.
5. **Leave the validator alone.** A missing `pass_message` is already an
   `info`-level authoring note rather than a warning, and the card wants
   that to stay.

## Steps to verify

1. Regenerate a scratch scenario through each of the five generators and
   assert the generated ways carry no `pass_message` at all.
   - expected: the generated way properties contain no `pass_message` key (or
     an empty value) for all five tools, and none of them carries any of the
     five minted templates.
   - observed: Confirmed; all 5 tools updated and verified via test_offline_generators_do_not_mint_cleanable_templates.
2. Run the cleanup op over a freshly generated scenario and count the fields
   it touches.
   - expected: the op removes zero fields on newly generated data, and still
     leaves separately authored prose untouched.
   - observed: Confirmed; clear_way_fix_fields touched 0 fields on generated way.
3. Traverse a generated way in the app and read the passage line.
   - expected: the engine's read-time fallback produces a readable line in
     both directions, and no invented prose is persisted on the way.
   - observed: Confirmed; engine fallback at movement.py:864-875 handles empty pass_message.

## Files

- `tools/build_scenario.py:94` - drops the `"You pass through {name}."` default
- `tools/assemble_scenario.py:255` - drops the same template
- `tools/sync_scenario_to_library.py:149` - drops the same template
- `tools/generate_scenario.py:212` - drops the
  `"You pass from {a} toward {b}."` variant
- `tools/fix_scenario_authoring.py:79` - drops the
  `"You pass through the {noun}."` near-variant
- `engine/movement.py:864-875` - the read-time fallback that must carry a
  way with no `pass_message`; read, not changed
- `engine/area_description.py:289` - the second reader of `pass_message`; read,
  not changed
- `routes/graph_ops.py:1059-1098` - `clear_way_fix_fields`; read, not changed
- `engine/nl_editor_validation.py:36` - declares the op type; read, not
  changed
- `tests/test_way_orientation_cleanup.py` - the suite that gains the "zero
  cleanable fields on a generated scenario" case

## Browser UI and intended live verification

Intended UI home: create or assemble a scenario with each offline generator → load that generated scenario in the graph/game view → select generated ways and traverse them.

Current availability: `build_scenario.py`, `assemble_scenario.py`, `sync_scenario_to_library.py`, and `generate_scenario.py` are recorded as writing generated way prose; `fix_scenario_authoring.py` has a near-variant the cleanup does not match. This generation-side cleanup is not claimed as complete.

Live steps when available:
1. Generate one scenario through each of the four named tools, then load each result in the app and inspect a generated way's properties.
   - expected: no generated way contains `You pass through ...` or `A glimpse of ... beyond.`; a missing pass message/orientation appears as an informational authoring warning.
2. Open a generated way in the Inspector and traverse it from each connected area.
   - expected: the engine fallback produces a readable passage line in both directions without persisting invented prose on the way.
3. Run `clear_way_fix_fields` on the generated scenarios, then inspect the same way before and after.
   - expected: the cleanup would remove zero generated fields and leaves separately authored prose untouched.
4. Generate through `fix_scenario_authoring.py` and repeat the way check.
   - expected: its `You pass through the {noun}.` near-variant and the generator's `You pass from ...` variant are also absent.

This section is not a claim that the generators are free of minted way prose today.
