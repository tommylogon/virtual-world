---
type: task
status: review
area: ui
priority: medium
---

# task-521: HelpCenter coverage: hint the newer systems and audit for gaps

**Filed:** 2026-09-24
**Related:** task-495, task-496, task-397, task-520, task-508, task-486, task-436, task-399

## Goal

The coach-tip registry (window.HelpCenter in static/js/ui/help-center.js) only covers a fraction of the UI; extend it so every notable system added recently has a tip and a matching data-help hook, and audit the app for un-hinted controls.

## Acceptance

- [x] Every listed gap below is either given a tip + `data-help` hook, or
  explicitly recorded as deliberately un-hinted with a reason.
- [x] Each new tip has a unique `id`, a `group`, a `title`, a `body`, and a
  `target` selector that the spotlight can reach.
- [x] The `data-help` key on each hooked element matches its tip's `match`
  exactly (case-sensitive), and the element is reachable in the state the tip
  fires (verified live, below).
- [x] An in-editor control tip (if added) uses a `data-help` on the control built
  by `static/js/worldpainter/editor.js`, not just the toolbar launcher.
- [x] The Help index (`F1` / ❓) lists the new tips and any new tour renders and
  runs end to end; `Reset all` restores them.
- [x] No tip references a control that no longer exists, and no two tips share an
  id.
- [x] JS checked with `node --check`, `npm run lint`, `npm run typecheck`; JS
  units stay green (`486 passed, 0 failed`).

## Gap-by-gap disposition (2026-10-02)

- **WorldPainter in-editor controls** — DONE in task-575 (21 hooks, `paint-a-town`
  tour, registry guard). The launcher `worldpainter` tip already covers
  `⚙ Generate` per-scope; no further work here.
- **Scope tree / unmade-scope Generate** — **deferred to task-580**, which owns
  that affordance. It is outside this lane's files (`static/js/graph/scope-tree.js`
  is in-progress under task-592, which *deliberately* replaced a scope-row
  Generate with a Paint jump). task-580 must add its own `data-help="scope-generate"`
  hook + tip when it lands; recorded here so the gap is not silently dropped. The
  painter's own `⚙ Generate` is already hinted by `wp-generate`.
- **Consume/depletion contract** — folded into the existing `inspector-item` tip
  (now: "Consumables spend themselves … authored food/drink must not spend a use
  by hand").
- **Auto-regenerating descriptions** — new tip `auto-description`, hooked on the
  `🤖 Generate from Equipment` button (`data-help="auto-description"`), explaining
  the derived description, auto-refresh, and Base Description as the durable home.
- **Turn/time model** — new tip `turn-model`, hooked on `#agent-turn-based`
  (`data-help="turn-model"`).
- **Background simulation** — new tip `background-sim`, hooked on `#agent-list`
  (`data-help="background-sim"`).
- **Audit** — the registry guard (`tools/unit/test_help_center.js`) already
  sweeps every `data-help=` / `_help('…')` key in `static/js` + `templates` and
  fails on an orphan hook; extended with a targeted test for the three new tips.

## Verification (live browser, 2026-10-02)

`VW_PORT=4463`, Playwright, real clicks:

```
TURN_TIP          "💡 Time, turns and travel"
BACKGROUND_TIP    "💡 The world keeps moving without you"
AUTO_DESC_BTN_PRESENT true
AUTO_DESC_TIP     "💡 Descriptions regenerate from gear"
HELP_INDEX {"tipCount":45,"tours":["First five minutes","Triggers & effects",
  "Scenario workflow","Painting a world","Painting a town"],
  "hasTurn":true,"hasBg":true,"hasAuto":true}
AFTER_RESET {"stored":null,"cards":0}
Help index scrolled to bottom: SCROLL_REMAINING 0
```

Screenshots: `review-verify/521-turn-tip.png`,
`review-verify/521-autodesc-tip.png`, `review-verify/521-help-index.png`,
`review-verify/521-help-index-bottom.png`.


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
  **DONE in task-575** (2026-09-28): 21 `data-help` hooks and matching tips under
  a `WorldPainter` group, a `paint-a-town` tour, and `tools/unit/test_help_center.js`
  guarding the registry — which also found the ❓ Help button itself unhinted.
  Note task-575 added a **second** layer this task did not scope: preflight
  blockers in the editor, because a tip cannot tell an author that *this* scope
  cannot be compiled.
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
