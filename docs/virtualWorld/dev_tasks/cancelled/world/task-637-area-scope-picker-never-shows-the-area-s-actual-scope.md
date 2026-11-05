---
type: task
status: todo
area: world
priority: high
related: [task-539, task-541]
wiki: "[[Rooms & Areas]]"
---

# task-637: Recheck the area scope picker mismatch report

**Filed:** 2026-09-30
**Reframed:** 2026-10-15

<!-- deps:start -->
**Related:** [[task-539-reassign-an-area-to-a-scope-membership-only-plus-a-scope-picker-on-the-node]], [[task-541-worldpainter-area-picker-show-what-is-placed-here-and-what-belongs-to-this-scope-only]]
<!-- deps:end -->

## What

A report says the area scope picker does not show the area's actual scope and
that task-539 is not working. The report does not name the scenario, area ID,
scope ID, displayed option, or API value, so the mismatch has not been
reproduced from this card alone.

There is contrary live evidence in task-539: selecting **goblin camp**
(`deep_woods_2`) for `area_training_pit` put that area into the camp's own
level; selecting **— no scope —** put it back. Recheck the current UI and data
before changing working code. If the behavior still matches task-539, retract
this report in place with that evidence. If not, record the exact failing area,
scope, displayed value, and authoritative value before proposing a fix.

## Acceptance

- A fresh browser reproduction records the scenario, area node ID, current
  `properties.world_scope_id`, scope name, picker value, and the result after
  reload.
- If the picker matches the authoritative node property and the membership
  view, cancel this task with the verification evidence and reason; do not make
  a speculative fix.
- If there is a mismatch, preserve the failing example and write a concrete
  expected-versus-observed result before implementing a correction.
- Any verified fix preserves task-539's membership behavior and does not move
  an area's painted cell unless the scope-placement contract requires it.

## Steps to verify

1. Reproduce the report using the browser path below and record the scenario,
   area ID, selected option, node property, and membership result.
   - expected: the UI selection agrees with the authoritative scope property;
     any mismatch is specific enough to investigate.
   - observed: not run; report lacks a concrete example.
2. If current behavior matches task-539, record that and retract this report
   instead of changing code.
   - expected: the task is cancelled with the recheck evidence, or updated with
     an exact failing case.
   - observed: not run.

## Browser UI and intended live verification

Intended UI home: area Inspector → 🗺️ Scope, beside the map placement.

Current availability: the scope picker exists; task-637's original mismatch
has not been freshly reproduced.

Live steps when available:

The scope control belongs in the existing area Inspector under **🗺️ Scope**.
The picker is rendered as `area-scope-<area-node-id>` in the Inspector. Keep
scope membership visible beside the area's map placement; do not introduce a
separate scope-membership screen.

1. Run the app and open the scenario that contains the reported area. Select
   the area node and open the Inspector's **🗺️ Scope** section.
2. Record the area's node ID, displayed selected option, and map placement.
   Compare the selection with that node's `properties.world_scope_id` in
   `/api/state` and the matching scope record in `/api/world/scopes?flat=1`.
   - expected: the selected scope name resolves to the node's actual scope ID;
     the scope's membership list includes the area.
3. On a scratch copy, change the picker to another existing scope, wait for the
   update, and reload the area Inspector. Then use **— no scope —** and reload.
   - expected: each selected value survives reload and the two scopes' area
     membership changes agree with the area node. Record any mismatch with the
     exact IDs and values.
4. Repeat the original task-539 case: set `area_training_pit` to **goblin camp**
   (`deep_woods_2`), then return it to **— no scope —**.
   - expected: the camp's own-level view gains the area after assignment and
     loses it after removal.

These steps define intended access and live acceptance; they are not a claim
that the reported mismatch is current or that a fresh browser check has been
performed for this card.

## Why

Task-539's live evidence already demonstrates that the same picker can assign
and remove an area. Task-637 currently lacks the data needed to tell whether its
report is a regression, a different scenario, or an incorrect interpretation.
The next action is measurement, not implementation.

## Files

- No implementation file until a current mismatch is reproduced
- `static/js/inspector/area-view.ts` is the existing scope picker surface
- `docs/virtualWorld/dev_tasks/review/world/task-539-reassign-an-area-to-a-scope-membership-only-plus-a-scope-picker-on-the-node.md` is the prior live evidence
