---
type: task
status: todo
area: ui
priority: medium
---

# task-521: HelpCenter coverage: hint the newer systems and audit for gaps

**Filed:** 2026-09-24
**Related:** task-495, task-496, task-397, task-520, task-508, task-486, task-436, task-399

## Goal

The coach-tip registry (window.HelpCenter in static/js/ui/help-center.js) only covers a fraction of the UI; extend it so every notable system added recently has a tip and a matching data-help hook, and audit the app for un-hinted controls.

## Acceptance

- Every listed gap below is either given a tip + `data-help` hook, or
  explicitly recorded as deliberately un-hinted with a reason.
- Each new tip has a unique `id`, a `group`, a `title`, a `body`, and (where a
  physical control exists) a `target` selector that the spotlight can reach.
- The `data-help` key on each hooked element matches its tip's `match` exactly
  (case-sensitive), and the element is reachable in the state the tip fires.
- An in-editor control tip (if added) uses a `data-help` on the control built by
  `static/js/worldpainter/editor.js`, not just the toolbar launcher.
- The Help index (`F1` / ❓) lists the new tips and any new tour renders and runs
  end to end; `Reset all` restores them.
- No tip references a control that no longer exists, and no two tips share an id.
- JS checked with `node --check`, `npm run lint`, `npm run typecheck`; JS units
  (`node tools/unit/run.cjs`) stay at baseline (currently 226 passed, 13
  pre-existing `test_plan_tracker` failures).

## How the system works (so the additions fit it)

`static/js/ui/help-center.js` defines `TIPS` (registry) and `TOURS` (ordered tip
chains). A tip fires from one of three events: `inspector:view` (match on the
view type), `state:updated`, or a **click on any element carrying `data-help`**
(the tip's `match` compares against `dataset.help`). `target` is a CSS selector
for the "Show me" spotlight. `once: 'global'` persists the seen flag to
localStorage; the default re-shows next session.

## Known gaps to cover

- **WorldPainter in-editor controls** (`static/js/worldpainter/**`): `⚙ Generate`
  (per-scope once-only compile + 409 `allow_regenerate`), `➕ Add feature`
  (creates a child scope but does **not** auto-place it), `🧭 Route` (cells →
  turns → hours), `▦ Grid…` presets/shrink-prune, reference image + `▦ match`,
  and the merge-same-biome toggle. The launcher button is hinted; the controls
  inside the overlay are not.
- **World scopes / graph view** (task-397, task-400): beyond the shipped
  `scope-filter` tip — the scope *tree* is only a flat picker today, and an
  unmade-scope `Generate` affordance (task-398) has no hint yet.
- **Consume/depletion contract** (task-508): eat/drink auto-decrement `uses`
  after triggers; item-authored content must not hand-spend. Fits the
  `inspector-item` tip or a new item tip.
- **Auto-regenerating descriptions** (task-486, task-210): description refreshes
  on body-state change.
- **Turn/time model** (task-436): 1 turn = 1 in-game minute, one decision set per
  turn regardless of `time_per_tick_minutes`, travel ≥1 turn per cell — a
  "Time & travel" tip.
- **Background simulation** (task-399): off-screen characters act on their own
  schedule; promote/demote, attended scope.
- **Audit the rest**: most toolbar buttons, inspector tabs, modal actions and
  menu items still have `title` tooltips but no `data-help`; sweep them and add
  tips where a system deserves a coach card rather than a hover string. Also
  consider a lightweight guard so a `data-help` with no matching tip (or a tip
  with a dead `target`) is caught — a small unit test over the registry.

## Verification

- Manual: trigger each new tip (click the hooked control; inspect an area/item)
  and confirm the card, the spotlight, and the Help-index row.
- `node --check` + `npm run lint` + `npm run typecheck` clean; JS units at
  baseline.
- Optional guard test: every `TIPS` entry has a unique id, a `group`, and either
  no `target` or a selector string; every `TOURS` step references a real tip id.
