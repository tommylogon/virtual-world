---
type: task
status: review
area: ui
priority: medium
---

# task-598: Scenario manager: search and filter the scenario list

**Filed:** 2026-09-30
**Related:** 

## Goal

The scenario list is unfiltered, so finding one save among many requires scrolling. Add text search over scenario name and source path, plus filters on whatever dimensions the manager already knows (area count, character count, modified state, tags). Keep it consistent with the library browser's existing search/filter affordance rather than inventing a second pattern.

## Acceptance

- [x] Text search covers scenario **name and source path** (`sc.filename`),
  multi-token, with the library browser's fuzzy fallback for close spellings
  (reuses `window.fuzzyRatio`).
- [x] Dimension filters for what the manager already knows: **Modified**
  (any/today/last 7 days/last 30 days/older), **Health** (clean/has issues/won't
  parse), **Characters** (none/has characters), **Areas** (none/has areas).
- [x] A **Reset** returns to the unfiltered list; the match count ("N of M") and
  the distinct "No scenario matches the current filters." message reflect the
  active filter.
- [x] Filter state survives a list repaint and **⟳ Refresh**.
- [x] task-641 behaviour preserved: a bare number still finds a scenario by
  exact area/character count, and typing keeps focus.
- [x] Not a second pattern: same styling/affordance as the library search.
- **Tags are deliberately omitted**: the manager has no scenario-level tag
  dimension. The `tags` keys in scenario JSON are per-node (player/area tags),
  not a scenario property, and `GET /api/scenarios` returns no tags — so there
  is nothing to filter on without inventing scenario metadata.

## Verification (live browser, 2026-10-02)

Server `VW_PORT=4463`, Playwright, `ScenarioManager.open()` then fill/select:

```
ALL                  22 scenarios
SEARCH_PINES         1 of 22  ["pines"]                       (task-641 preserved)
SEARCH_SOURCEPATH   22 of 22  ".json" matches filename, absent from names
SEARCH_COUNT23       2 of 22  ["pines","kraktooth_goblin_camp"] (count match preserved)
FILTER_AREAS_NONE    2 of 22  ["world_template","kraktooth_goblin_camp"]
FILTER_OLD           0 of 22  "No scenario matches the current filters."
AFTER_RESET         22 scenarios
```

Screenshot: `review-verify/598-scenario-filters.png` (Areas=none, 2 of 22).

## Files

- `static/js/ui/scenario-manager.js` — filter state, `scenarioSearchScore`,
  `scenarioMatchesFilters`, select controls, Reset.

