---
type: task
status: todo
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

Move the `🎯 Goals` editor out of the character editor's Bio tab and into the Mind panel's Mind tab. The editor is `_goalRowHtml`, `_renderGoalsSection`, `_goalList`, `_collectGoals`, `_saveGoals`, `_addGoal`, `_deleteGoal` in `static/js/inspector/agent-view.ts` (lines ~821-889), authored in task-808. `Player.goals` stays the single source of truth and writes keep going through `ApiClient.updateCharacter(name, { goals })`. The Bio tab sheds the section.

## Why

task-808 authored the goal editor inside the character editor; the Mind panel is becoming the single mind surface (task-714 display; task-729 / task-787 relocation). Goal display already lives in the panel (task-714); only its editing half is still split, so today a designer reads goals in the Mind panel and writes them in the Bio tab. One mind, one editor — same rule task-756 applies to emotions and task-729 to relationships.

## How

Lift the goal editor functions from `agent-view.ts` into `mind-view.ts` (or a shared helper both can call) and mount it in the Mind tab under the read-only Goals block, or replace the read-only block with an editable one that still reads `worldState.players[name].goals`. Keep the same `updateCharacter({ goals })` write path — no new endpoint, no UI-only copy of state. Remove `AV._renderGoalsSection(player, escName)` from `_renderBioTab` (line 911).

## Steps to verify

1. Add a goal in the Mind panel, then reload the page.
   - expected: the goal persists and re-renders from `worldState`.
   - observed: TODO
2. Edit and delete the goal in the Mind panel.
   - expected: `updateCharacter({ goals })` fires; the Mind panel reflects it; the Bio tab no longer shows the editor.
   - observed: TODO

## Acceptance

- [ ] The goal editor lives in the Mind panel and writes `Player.goals` through `updateCharacter({ goals })`.
- [ ] The Bio tab no longer renders the Goals editor.
- [ ] Round-trip verified: add + edit + delete persist across a reload.
- [ ] `python tools/ts_convert.py check` green.

## Files

- `static/js/inspector/agent-view.ts` (`_renderGoalsSection` and helpers; `_renderBioTab`)
- `static/js/inspector/mind-view.ts` (destination)
- `static/js/api-client` (`updateCharacter`)
