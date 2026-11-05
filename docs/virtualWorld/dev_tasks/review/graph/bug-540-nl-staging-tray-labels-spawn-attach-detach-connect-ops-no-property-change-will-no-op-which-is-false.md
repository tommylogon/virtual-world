---
type: bug
status: todo
area: graph
priority: medium
wiki: "[[World Building/Graph System]]"
---

# bug-540: NL staging tray labels spawn/attach/detach/connect ops '(no property change - will no-op)', which is false

**Filed:** 2026-10-10
**Related:** 

## What

In the NL editor staging tray, every staged op that is not an update_node / create_node / delete / library_* / bulk op renders '(no property change - will no-op)'. Observed live 2026-10-10 in scenario labs: 16 spawn_library_item ops each showed that string, though a spawn plainly adds a node. Root: static/js/nl-editor/diff.ts opDiff() returns {kind:'other', changes:[]} for any op type it does not model (spawn_library_item, attach, detach, connect_areas, populate_area, create_trigger, ...), and summaryLines() maps empty changes to that string. It is display-only - Apply still runs the ops, since nothing filters on the label - but it is alarming and hides what the op will do. Fix: give each op type a real one-line summary (e.g. '+ spawn glass_beaker into Task 1', '+ attach glass_vial -> player_Bob (carrying)', '+ connect A-B via Oak Door') and reserve '(no-op)' for a patch that genuinely changes nothing. Related task-461 (the apply-time diff), which modelled property changes and no-op PATCHES but not these op kinds.

## Why

The staging tray is the last thing an author sees before Apply. If every
non-property op is labelled "(no property change - will no-op)", the tray stops
being a preview of the batch and becomes a wall of false alarms. That is worse
than no preview: an author who sees 16 rows all claiming to be no-ops either
ignores the tray entirely or distrusts every row in it, including the real
property diffs that task-461 added and that do work.

The label is also wrong on the merits. Most of these ops do not change
properties because they do not change *properties* - they add nodes, add or
remove edges, or write player state. The empty `changes` array means "this op
has no property diff", not "this op does nothing".

## How

`opDiff()` in `static/js/nl-editor/diff.ts` models seven op types and returns
`{kind:'other', changes:[]}` for everything else (`diff.ts:111`).
`summaryLines()` then maps an empty change list to the misleading string
(`diff.ts:146`).

The modelled set is (`diff.ts:81-110`): `create_node` / `create_character`,
`delete_node`, `update_node`, `update_matching_nodes`, `library_upsert`,
`library_delete`.

The op types that fall through, and which of those actually change the world
when applied:

| Op type | Mutating | Current label |
|---|---|---|
| `attach` | yes | "(no property change - will no-op)" |
| `detach` | yes | "(no property change - will no-op)" |
| `connect_areas` | yes | "(no property change - will no-op)" |
| `populate_area` | yes | "(no property change - will no-op)" |
| `create_trigger` | yes | "(no property change - will no-op)" |
| `rename_character` | yes | "(no property change - will no-op)" |
| `update_player` | yes | "(no property change - will no-op)" |
| `spawn_library_item` | yes | "(no property change - will no-op)" |
| `link_to_library` | yes | "(no property change - will no-op)" |
| `upsert_library_entry` | yes | "(no property change - will no-op)" |
| `delete_library_entry` | yes | "(no property change - will no-op)" |
| `compile_behaviours` | yes | "(no property change - will no-op)" |
| `clear_staged`, `unstage_op`, `request_clarification` | no | same string, but arguably correct for `clear_staged` / `unstage_op` |

Measured: 12 mutating op types have no modelled diff, and 15 op types in total
fall through to `kind:'other'`. `spawn_library_item` is the one the card saw
live, and it is in the list.

Note the op-type naming: the staged op type is `library_upsert` /
`library_delete` (`staging.ts:356-357`), while the *tool* the model calls is
`upsert_library_entry` / `delete_library_entry`. Both spellings are live, so a
fix has to model the staged op types.

The fix is to give each op type a real one-line summary from its payload
(source id, target id, edge kind) and to reserve the no-op string for a patch
whose property diff is genuinely empty.

## Steps to verify

1. Confirm the fallback for unmodelled op types.
   - expected: an op type with no modelled diff does not get the no-op label.
   - observed: FAILS. `diff.ts:111` returns `{kind:'other', changes:[]}` for 15
     op types, and `diff.ts:146` renders `'(no property change - will no-op)'`
     for any empty change list.
2. Confirm `spawn_library_item` is among the unmodelled types.
   - expected: the op the card saw live is not in the unmodelled set.
   - observed: FAILS. `spawn_library_item` is not in the seven modelled types at
     `diff.ts:81-110`, so it renders the no-op label.
3. Confirm the label is display-only and Apply still runs the ops.
   - expected: the ops execute; only the label is wrong.
   - observed: unchanged from the card. Nothing filters on the label; the
     `kind` value is consumed only for rendering in `ui.ts:484`.
4. Re-run the live `labs` case and read the tray rows.
   - expected: each row describes its actual effect and source/target.
   - observed: not re-run in this turn. The static findings above are what the
     code shows, not a fresh live reproduction.

## Acceptance

- [ ] `opDiff()` models the mutating op types, or `summaryLines()` gives each
      op type a real one-line summary from its payload: `+ spawn glass_beaker
      into Task 1`, `+ attach glass_vial -> player_Bob (carrying)`, `+ connect
      A-B via Oak Door`.
- [ ] The "(no property change - will no-op)" string is reserved for a patch
      whose property diff is genuinely empty, and the two cases are visually
      distinct.
- [ ] An op type with no meaningful summary says so explicitly ("unknown
      operation") rather than reusing the empty-property-diff label.
- [ ] A live `labs` run staging `spawn_library_item`, `attach`, `detach` and
      `connect_areas` shows four distinct, accurate row summaries.

## Browser UI and intended live verification

Intended UI home: NL editor → stage a `spawn_library_item`, `attach`, `detach`, or `connect_areas` operation → inspect that operation's summary in the staging tray before Apply.

Current availability: the card records a live case where 16 `spawn_library_item` rows were labeled “no property change - will no-op” even though Apply still spawned items. Re-checked 2026-10-20: the misleading label is still what the code produces, and the set of op types that get it is larger than the card recorded - 12 mutating op types, not just the four named. The defect is display-only; the operations execute.

Live steps when available:
1. In scenario `labs`, stage one `spawn_library_item`, one `attach`, one `detach`, and one `connect_areas` operation. Count the tray rows and read each row's summary.
   - expected: each row describes its actual effect and relevant source/target; none is labeled as a no-op merely because `opDiff()` does not model its properties.
2. Apply the batch and inspect the graph and containment/connection edges.
   - expected: each displayed summary corresponds to the operation that ran; spawned nodes and changed edges are visible.
3. Stage an unsupported or invalid operation and inspect its row before Apply.
   - expected: the UI identifies an actual validation failure or unknown operation explicitly; it does not reuse the empty-property-diff label for an operation that will execute.

This section is not a claim that planned UI exists or works today.

## Files

- `static/js/nl-editor/diff.ts` - `opDiff()` (the seven modelled op types,
  lines 81-110; the `kind:'other'` fallback at 111) and `summaryLines()` (the
  no-op string at 146)
- `static/js/nl-editor/staging.ts` - the staged op type names (`library_upsert`,
  `library_delete` at 356-357)
- `static/js/nl-editor/ui.ts` - the tray rendering that calls `summaryLines()`
  (line 484)
- `static/js/nl-editor/tools.ts` - the tool definitions, which name the ops the
  model can stage

## Reconnaissance (2026-10-20) - still valid

Re-checked the cited code on 2026-10-20 against the newer NL editor work
(task-461 apply-time diff, task-422 budget, the task-425/461 validation gate).
The card's root cause is unchanged and its scope is wider than recorded.

- `opDiff()` still models seven op types and still returns
  `{kind:'other', changes:[]}` for the rest (`diff.ts:111`).
- `summaryLines()` still maps any empty change list to
  `'(no property change - will no-op)'` (`diff.ts:146`).
- 15 op types fall through to `kind:'other'`, of which **12 mutate the world**:
  `attach`, `detach`, `connect_areas`, `populate_area`, `create_trigger`,
  `rename_character`, `update_player`, `spawn_library_item`, `link_to_library`,
  `upsert_library_entry`, `delete_library_entry`, `compile_behaviours`. The card
  named four; the other eight are the same defect.

Verdict: STILL_VALID. The card stays in todo, with the widened op-type list
recorded above.
