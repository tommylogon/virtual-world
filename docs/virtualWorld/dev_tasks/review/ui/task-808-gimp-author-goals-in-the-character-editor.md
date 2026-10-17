---
type: task
status: review
area: ui
priority: medium
wiki: "[[Character Pursuits]]"
related: ["'task-691'", "'task-714'", "'task-820'", "'task-821'", 'task-807', 'task-820', 'task-821']
blocked_by: [task-807]
---

# task-808: GIMP: author goals in the character editor

**Filed:** 2026-10-12
**Related:** task-714

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-820-mind-panel-one-tabbed-mind-surface-and-one-entry-point]], [[task-821-mind-panel-relocate-the-gimp-goal-editor-out-of-the-bio-tab]], [[task-807-gimp-the-goal-model-and-its-serialization]]
<!-- deps:end -->

## What

Add, remove and edit a character's goals in the graph editor's character form.

## Why

Goals must be authorable per character, not only at runtime.

## How

Extend the character form schema with a goals block (target, motivation, intention, status). Write through the existing graph/props path.

## Steps to verify

1. In the character inspector's Bio tab, add, edit and remove a goal.
   - expected: each change persists and re-renders from state; the personality field is untouched.
   - observed: VERIFIED 2026-10-12, live on localhost:4445. Added "Keep the eastern gate repaired" (with motivation) via "➕ Add goal", changed a row's status and its `what`, and removed a row via ✕. Each landed in `/api/state`, and the goal survived a full page reload and re-rendered in the editor. `inspector-personality` was present and unchanged throughout.

## Acceptance

- [x] A goal can be added, edited and removed from the editor.
- [x] The prose personality field is untouched.

## Files

- `static/js/inspector/agent-view.ts` (the Goals section plus `_addGoal` / `_deleteGoal` / `_saveGoals`)
- `routes/player_ops.py` (`goals` in `handle_update_player`)
- `engine/goals.py` (the model it writes)

## Browser UI and intended live verification

Intended UI home: Character Inspector → 🧠 Mind → Mind tab → Goals editor. The older Bio-tab goal editor from this card was moved by task-821; Bio is no longer the current authoring home.

Current availability: This card records a live add/edit/remove round-trip in Bio on localhost:4445 on 2026-10-12. Task-821 later moved the editor to Mind and records a separate live round-trip there on 2026-10-13.

Live steps when available:
1. Select a character, open 🧠 Mind → Mind, click “➕ Add goal”, enter “Keep the eastern gate repaired” and a motivation, then blur the edited field.
   - expected: exactly one goal row appears and the character's `Player.goals` field contains the new goal after state refresh.
2. Change the goal's status and `what`, reload, then remove the goal.
   - expected: the edits persist across reload; removing it leaves no goal entry; the character's personality text remains unchanged.
3. Return to Bio and inspect its sections.
   - expected: Bio no longer contains a Goals editor; the Mind editor remains the only goal-authoring home.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Progress (2026-10-12)

- A "🎯 Goals" `inspector-section` in the Bio tab, after Personality: one row per goal (what, status, motivation, intention), a ✕ remove, and a "➕ Add goal" button. Fields save on blur/change via `ApiClient.updateCharacter(name, { goals })`.
- `handle_update_player` accepts `goals` and normalises through `engine/goals.normalize`, so a malformed form entry cannot enter the character's mind.
- Authoring path complete end to end: the editor writes `Player.goals`, and the Mind panel (`InspectorMindView`, task-714) and `GET /api/state` read it.
