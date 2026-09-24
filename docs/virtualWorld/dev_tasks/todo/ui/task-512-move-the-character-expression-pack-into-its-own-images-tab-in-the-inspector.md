---
type: task
status: todo
area: ui
priority: medium
---

# task-512: Move the character Expression Pack into its own Images tab in the inspector

**Filed:** 2026-09-24
**Related:** task-445

## Goal

The Expression Pack (profile/full-body art per emotion, plus the ✂️ sheet
splitter) currently renders inside the character inspector directly under the
name, so it pushes the actual stats/relations down and clutters the panel. Give
character art its own **Images** tab in the inspector so the overview stays
about who the character is, and art/upload/split live one click away.

## Acceptance

- [ ] A new inspector tab (e.g. **🖼️ Images**) for character nodes holds the Expression Pack card grid (`InspectorHelpers.renderExpressionSection`) and the sheet splitter.
- [ ] The character overview no longer renders the Expression Pack inline under the name; the existing behaviour (upload by click/drag-drop, `NOW` badge, per-expression profile/full) is unchanged once the tab is open.
- [ ] Tab is character-only (hidden/absent for other node types) and the inspector remembers the selected tab across selection changes where it makes sense.
- [ ] `templates/index.html` script tags and the inspector tab registration stay consistent; JS unit tests (`node tools/unit/run.cjs`), `npm run lint`, and `npm run typecheck` stay green.

