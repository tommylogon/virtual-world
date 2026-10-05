---
type: task
status: review
area: emotions
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

- [x] A new inspector tab (**Images**) for character nodes holds the Expression Pack card grid (`InspectorHelpers.renderExpressionSection`) and the sheet splitter.
- [x] The character overview no longer renders the Expression Pack inline under the name; the existing behaviour (upload by click/drag-drop, `NOW` badge, per-expression profile/full) is unchanged once the tab is open.
- [x] Tab is character-only (agent-view is character-only; other node types have their own tab sets) and the inspector remembers the selected tab across selection changes.
- [x] `templates/index.html` script tags and the inspector tab registration stay consistent; JS unit tests (`node tools/unit/run.cjs`), `npm run lint`, and `npm run typecheck` stay green.

## Outcome (2026-10-02)

`static/js/inspector/agent-view.js`: `TABS = ['Inventory','Bio','Images','Advanced']`;
the inline Expression Pack under the header is removed and replaced by
`AV._renderImagesTab` (a `data-tab="Images"` div calling
`InspectorHelpers.renderExpressionSection`). `_activeTab` is module-level, so a
chosen tab survives a re-render. Docs updated in
`docs/virtualWorld/UI & Settings/Inspector Panels.md`.

Live check (server `VW_PORT=4463`, Playwright, `showAgent` then click Images):

```
TABS ["Inventory","Bio","Images","Advanced"]
BEFORE {"exprExists":true,"visibleOnOverview":false,"imagesTabDivExists":true}
AFTER  {"visible":true,"cards":12,"splitter":true,"addBtn":true,
        "tabStyles":[... Images display:"" ...]}
PERSIST_ACROSS_RERENDER {"imagesVisibleAgain":true}
```

Screenshot: `review-verify/512-images-tab.png`.


