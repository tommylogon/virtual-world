---
type: task
status: done
area: ui
priority: high
---

# task-393: validator-triage-panel

## Outcome (verified 2026-09-22) — closed; residuals re-filed as task-443

The triage mechanics this task exists for are **landed and in use**, and the two open
questions are now decided rather than deferred.

**Decision 1 — derived progress: keep the shipped formula (amend section G).**
The file specified planner-covered / `trigger_reviewed: true` / `ignored_issues`. But
`trigger_reviewed` appears nowhere in source, and planner-covered needs the trigger-plan
API. What shipped is
`audited − distinct source_node_ids with issues` (`static/js/validator-panel.js:356-379`) —
purely computed, cannot drift, which was the actual requirement. Section G is amended
below; the richer definition stays available as a future enhancement, not an open loop.

**Decision 2 — the unimplemented pieces are re-filed as task-443.**
`library_mismatch` recalibration, the "mark instance as intended" action, the
default-collapsed `info` section, and the manual browser pass are all absent. This file's
claim that the recalibration was done was **false** — task-443 carries the corrected
facts and the acceptance criteria.

**The unsupported verification claim is now backed by a test.**
This file claimed the `ignored_issues` filter and resurfacing were "verified via ad-hoc
run" with no committed test. Added here:
`tests/test_trigger_validator.py::TestIgnoredIssues` — 7 tests covering hide, expiry on
edit, non-ignored codes, missing source node, a malformed `_ignored_at`, and an
end-to-end `validate()` case. File: 48 passed.

**Landed (unchanged from the note below):** group-by-node / group-by-code with a
persisted toggle (`static/js/validator-panel.js:257-291`, `:348-349`); scrollable list with
a pinned count (`:309-310`, `:312-320`, markup `templates/index.html:139,142`);
`empty_trigger` collapsing plus batched "Remove all empty" (`:423-448`, `:144-166`,
button `:397-400`); dismiss-until-edited via per-node `ignored_issues` with engine filter
and resurfacing (`engine/trigger_validator.py:184-219`, route `routes/triggers.py:24-51`,
UI `:127-137`); mechanical-default fix-all (`:232-255`, button `:468-469`) and way
delegation to task-395; a progress bar (`:356-379`).

### Prior state (2026-09-21) — partial, not closable

Core triage mechanics are genuinely landed; three deliverables are absent and
three claims in this file no longer match the code.

**Landed:** group-by-node / group-by-code with a persisted toggle
(`static/js/validator-panel.js:257-291`, `:348-349`); scrollable list with a
pinned count (`:309-310`, count updated `:312-320`, markup
`templates/index.html:139,142`); `empty_trigger` collapsing plus a batched
"Remove all empty" (`:423-448`, `:144-166`, button `:397-400`); dismiss-until-edited
via per-node `ignored_issues` with the engine filter and resurfacing
(`engine/trigger_validator.py:184-219`, route `routes/triggers.py:24-51`, UI
`:127-137`); mechanical-default fix-all (`:232-255`, button `:468-469`) and the
way delegation to task-395 (`:202-229,465-467`); a progress bar (`:356-379`).

**Not done:**
1. **`library_mismatch` "mark instance as intended"** — no such action exists
   anywhere.
2. **The `library_mismatch` recalibration is not done, and this file's claim about
   it is false.** It says the code fires "only on mechanical field drift … not
   `light_level`/`contents`", but `LIBRARY_SYNC_PROPS` still includes
   `light_level`, `target_temperature`, `heating_rate`, `contents` and `aliases`
   (`engine/trigger_validator.py:147-151`), the severity is still `warning`
   (`:728`), and a test explicitly asserts a `light_level` mismatch is reported
   (`tests/test_trigger_validator.py:428-439`).
3. **The derived-progress definition does not match.** The file specifies
   planner-covered / `trigger_reviewed: true` / `ignored_issues`; the shipped bar
   is `audited − distinct source_node_ids with issues` (`:356-379`).
   `trigger_reviewed` appears nowhere in source. Either implement the intended
   definition or amend this section to the one that shipped.
4. No separate default-collapsed `info` section (grouping sorts by worst severity
   `:293-300`, but info rows render inline).
5. Manual browser pass.

**Also unsupported:** the verification claim that the `ignored_issues` filter and
resurfacing were "verified via ad-hoc run" — no committed test references
`ignored_issues` or `_ignored_at`.

**Filed**: 2026-09-07
**Status**: In Progress — backend ignore filtering + route + panel rewrite landed 2026-09-07; manual browser pass pending.

## Source

Conversation 2026-09-07 (authoring workflow). Mansion run reports **254 world
issues**: ~180 way-orientation warnings (cardinal/view/pass × 2 sides × ~30 ways),
~24–30 `empty_trigger` (several *duplicate* rows for the same node — candy_jar ×4,
water_pitcher ×3, energy_drink ×2), ~40 `library_mismatch` on trivial fields
(`light_level`, `contents`), ~30 `mechanical_tag_missing_props` info-nudges (half
already have a working ⚙ quick-fix), and **1 real error** (`missing_effect_item`).

The panel currently dumps all 254 rows in one flat unscrollable list, so the signal
is buried. Goal: convert the Issues tab from "wall of 254" into a triage tool whose
working set is small and always current.

## Why (user's constraints)

- Instance-first authoring: fixes happen on placed nodes, not templates. Library
  sync exists and is good — the pain is **finding** what's unfinished.
- "Done" must be derived from data, not memory: the graph reloads/moves/shifts, so
  external checklists rot. Any progress state must live in the nodes themselves.
- The user already uses the Issues tab (left panel) daily.

## Design

### A. Grouping (two views of the same list)
- **Node view**: one row per logical node. A way with 6 side-warnings collapses to
  one expandable row ("way_kitchen_cellar_door — 6 issues"). An item with 4 empty
  trigger stubs collapses to one row ("item_candy_jar — 4 empty trigger nodes").
- **Code view**: one row per issue code ("way_missing_cardinal ×58",
  "empty_trigger ×24", "library_mismatch ×40"), collapsible to the underlying nodes.
- Toggle buttons **By node / By code**.

### B. Scroll + sticky summary
- `.validator-list` gets `overflow-y:auto` + a max-height (panel already overflows).
- Header count row stays pinned; shows grouped counts, not raw rows.

### C. `empty_trigger` dedupe + collapse
- Multiple empty logic_trigger edges on one node group to a single row.
- Per-node action: **"Remove all empty"** (batched via `/api/graph/batch`, one undo).

### D. Dismiss-until-touched (survives reloads)
- Row context action "Dismiss on this node" (or for the whole code class within a
  node) writes `ignored_issues: ["<code>", ...]` into the **node's properties**.
- Validator skips dismissed codes for that node; dismissed issues resurface if the
  node is edited after dismissal (bump a `_issue_dismiss_epoch` stamp).

### E. Bulk-fix by class
- Per-code rows get "Fix all" where the fix is mechanical:
  - `way_missing_cardinal` / `way_missing_view_direction` → see task-395.
  - `mechanical_tag_missing_props` (info) → write engine defaults in one batch
    (reuse the existing `quickFix` patch shape).
  - `library_mismatch` on trivial fields → batch "mark instance as intended"
    (set an explicit override) rather than resync.

### F. Severity recalibration
- `info` = nudges → collapsed section by default.
- `library_mismatch` fires only on **mechanical** field drift (vitals/triggers/
  actions/uses), not `light_level`/`contents` (instance-divergence is the normal
  flow per user).

### G. Derived progress (layer-2)
> **AMENDED 2026-09-22 — this is the definition that shipped, not the original one.**
> The bar below was originally specified as planner-covered / `trigger_reviewed` /
> `ignored_issues`; `trigger_reviewed` was never implemented and planner-covered needs the
> trigger-plan API. The live definition is the shipped one — see the Outcome block.

- A node is **done** when it has no undismissed issue:
  `clean = total − distinct source_node_ids with issues`, computed live in
  `static/js/validator-panel.js:356-379`.
- Progress bar for the current filter: "trigger audit — 31/60 done". Purely
  computed, cannot drift.
- *Original (unshipped) definition, kept for reference:* planner-covered (all planned
  trigger types present under `TriggerSuggestDiff.covered()`) OR `trigger_reviewed: true`
  OR `ignored_issues` covers the outstanding codes. Revisit only if the shipped bar proves
  too coarse.

## Implementation notes

- Files: `static/js/validator-panel.js` (rewrite render + grouping + dismiss),
  `static/js/api.js` (small batch helper exists: `batchGraph`), `static/js/
  item-library/consumable-triggers.js` (plan exposure — already done).
- `ignored_issues` and `trigger_reviewed` are plain node properties (no schema
  changes).
- Dismiss epoch: store `last_epoch` with the dismissal; any node change (state:
  updated → node.updated timestamp) clears it.

## Verification

- `node --check` on all touched JS files.
- Manual: open mansion, Issues tab → rows collapse, scroll works, dismiss survives
  reload, dedupe removes empty stubs, progress bar reflects real covered count.
- Pytest unchanged (JS-only).

## Files changed

- `engine/trigger_validator.py` — `_filter_ignored(issues)` in `validate()`: skips
  issues whose `code` is in the owning node's `ignored_issues`, unless the node was
  edited (`node.updated > _ignored_at`) after dismissal → resurfacing. Dismissals
  are per-node properties, survive reloads.
- `routes/triggers.py` — new `POST /api/triggers/ignore` (`{node_id, code,
  ignore}`): appends/removes `code` in `node.properties.ignored_issues`, writes
  `_ignored_at` = `node.updated` (single request, so the pair is always
  consistent), bumps `world._edit_seq`.
- `static/js/validator-panel.js` — rewritten render:
  - Group By node / By code toggle (persisted in localStorage).
  - Node view = one expandable `<details>` per way/item/area (duplicate rows like
    candy_jar ×4 collapse into one row); Code view = one row per class with
    per-code counts.
  - Row actions: 🔍 jump, ⚙ quick-fix (mechanical info), 🧹 remove-all-empty
    (batch `delete_node`), 🚫/🔓 dismiss/restore (`/api/triggers/ignore`).
  - "⚡ Fix all" for mechanical info nudges (batch `update_node`) + "⚡ Fix all
    ways" for way-orientation (see task-395).
  - `.validator-list` max-height 45vh + `overflow-y:auto`; sticky header count.
  - Derived progress bar: clean/total item+way+area nodes with no undismissed
    issue (computed, cannot drift).
- `tests/test_trigger_validator.py` — unchanged; verified `ignored_issues` filter +
  resurfacing via ad-hoc run (dismiss → hidden, node edit → resurfaced).

## Verification

- `node --check` on all touched JS files — pass.
- Repo gate `python -m pytest tests/ -q -k "not mcp and not emote"` — 2632 passed.
- Live route test: `/api/triggers/ignore` round-trip (dismiss hides the code,
  restore re-shows; `_ignored_at` set in props).
- Manual browser pass still TODO (grouping UI, scroll, dismiss-until-touched
  persistence across reload).