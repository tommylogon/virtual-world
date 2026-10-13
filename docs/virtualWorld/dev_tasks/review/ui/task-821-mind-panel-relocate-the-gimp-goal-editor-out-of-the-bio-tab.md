---
type: task
status: review
area: ui
priority: medium
wiki: "[[Inspector Panels]]"
related: [task-714, task-787, task-808]
---

# task-821: Mind panel: relocate the GIMP goal editor out of the Bio tab

**Filed:** 2026-10-13
**Related:** task-714, task-787, task-808

<!-- deps:start -->
**Related:** [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-787-mind-panel-migrate-the-remaining-mind-surfaces-out-of-the-bio-and-advanced-tabs]], [[task-808-gimp-author-goals-in-the-character-editor]]
<!-- deps:end -->

## What

Move the GIMP goal editor out of the character editor's Bio tab and into the Mind panel's Mind tab. `Player.goals` stays the single source of truth and writes keep going through `ApiClient.updateCharacter(name, { goals })`. The Bio tab no longer renders a Goals section.

## Why

task-808 authored the goal editor inside the character editor; the Mind panel is becoming the single mind surface (task-714 display; task-729 / task-787 relocation). Goal display already lives in the panel (task-714); only its editing half is still split, so today a designer reads goals in the Mind panel and writes them in the Bio tab. One mind, one editor — same rule task-756 applies to emotions and task-729 to relationships.

## How

`mind-view.ts` now renders editable goal rows (`_goalRowHtml`, `_goalsHtml`, `_collectGoals`, `_saveGoals`) and wires them by **event delegation** on `#mind-goals`: `focusout` / `change` save, and a delegated `click` handles add and remove. Delegation means a row added after a render is still wired and no handler binds twice. The old `AV._goalRowHtml` / `_renderGoalsSection` / `_goalList` / `_collectGoals` / `_saveGoals` / `_addGoal` / `_deleteGoal` and the `AV._renderGoalsSection(player, escName)` call were removed from `agent-view.ts`.

## Steps to verify

1. Add a goal in the Mind panel, then reload the page.
   - expected: the goal persists and re-renders from `worldState`.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. One click on "➕ Add goal" adds exactly one row; typing a `what` and blurring persisted it to `Player.goals`; a reload re-rendered it. (Probe goal reverted.)
2. Edit and delete the goal in the Mind panel; the Bio tab no longer shows the editor.
   - expected: `updateCharacter({ goals })` fires; Bio has no Goals editor.
   - observed: VERIFIED 2026-10-13. `InspectorAgentView._renderGoalsSection` is `undefined`, and `_renderBioTab`'s HTML no longer contains "🎯 Goals"; the panel sends `updateCharacter` with the collected goals.

## Acceptance

- [x] The goal editor lives in the Mind panel and writes `Player.goals` through `updateCharacter({ goals })`.
- [x] The Bio tab no longer renders the Goals editor.
- [x] Add round-trips across a reload.
- [x] `python tools/ts_convert.py check` green.

## Files

- `static/js/inspector/mind-view.ts` (the goal editor)
- `static/js/inspector/agent-view.ts` (the Bio-tab editor removed)
