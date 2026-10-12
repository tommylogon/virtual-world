---
type: task
status: todo
area: ui
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-691, task-714]
blocked_by: [task-807]
---

# task-808: GIMP: author goals in the character editor

**Filed:** 2026-10-12
**Related:** task-714

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Add, remove and edit a character's goals in the graph editor's character form.

## Why

Goals must be authorable per character, not only at runtime.

## How

Extend the character form schema with a goals block (target, motivation, intention, status). Write through the existing graph/props path.

## Steps to verify

1. In the graph editor's character form, add, edit and remove a goal.
   - expected: the change persists on reload and appears under the character's goals in the 🧠 Mind panel (`InspectorMindView`) (goals section is task-714).
   - observed: TODO

## Acceptance

- [ ] A goal can be added, edited and removed from the editor.
- [ ] The prose personality field is untouched.

## Files

- `static/js/inspector/`
- `templates/index.html`
