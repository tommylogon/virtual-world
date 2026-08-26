# Task-251: Restructure Character Inspector Tabs

**Status:** In Review — implemented 2026-08-16 in
`static/js/inspector/agent-view.js` + `paperdoll-view.js`.

## Goal

Reorganize the character inspector into fewer, more coherent tabs:

- **Inventory** — paperdoll/equipment on top, inventory grid below it
  (Equipment + Inventory merged).
- **Bio** — personality, appearance, **Stats/Skills/Traits** (moved from the
  old Stats tab), relationships, tags, memories, etc.
- **Advanced** — **Graph Physics** (moved from always-visible top section),
  **Behaviors** (moved from Bio), timeline, conversation memory, save/export.

## Changes

- `agent-view.js`:
  - Tabs reduced `['Stats','Equipment','Inventory','Bio','Advanced']` →
    `['Inventory','Bio','Advanced']` (default `_activeTab = 'Inventory'`).
  - `_renderStatsTab` → `_renderStatsBlocks` (no tab wrapper), included at the
    top of `_renderBioTab`.
  - Behaviors section moved from `_renderBioTab` → `_renderAdvancedTab`.
  - Graph Physics (`graphGravityControl`) moved from the always-visible top of
    `showAgent` → `_renderAdvancedTab` (via `characterNode` param).
  - `_renderInventoryTab` now renders the paperdoll first, then the carried
    inventory / containers.
- `paperdoll-view.js`: `renderPaperdollEquipmentHtml` no longer wraps itself in
  a `data-tab="Equipment"` shell (it previously owned the Equipment tab); it
  now emits just the equipment section, hosted inside the Inventory tab.

## Verification

- `node --check` passes on both files; 941 pytest pass.
- Playwright E2E files updated for the new tabs
  (`test_ui.cjs`, `test_comprehensive.cjs`, `test_all.cjs`,
  `test_full_suite.cjs`, `test_full_e2e.cjs`, `test_inspector.cjs`,
  `test_regressions.cjs`, `test_art_heist.cjs`). Browser E2E re-run pending.