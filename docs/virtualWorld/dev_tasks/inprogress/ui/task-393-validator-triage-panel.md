---
type: task
status: inprogress
area: ui
priority: high
---

# task-393: validator-triage-panel

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
- A node is **done** when: planner-covered (all planned trigger types present under
  `TriggerSuggestDiff.covered()`) OR `trigger_reviewed: true` OR `ignored_issues`
  covers the outstanding codes.
- Progress bar for the current filter: "trigger audit — 31/60 done". Purely
  computed, cannot drift.

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