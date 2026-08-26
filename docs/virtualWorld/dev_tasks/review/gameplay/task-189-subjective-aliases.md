---
id: 189
title: Subjective Aliases — Command Resolution by Alternative Names
status: review
priority: medium
created: 2026-08-10
updated: 2026-08-10
tags: [gameplay, matching, aliases, commands, inspector]
---

# Subjective Aliases — Command Resolution by Alternative Names

**Status**: In Review — implemented 2026-08-10. Items already resolved aliases via `properties.aliases`; extended the same mechanism to ways, areas, and characters plus an editable 🔖 Aliases field in the inspector for all four node types. 7 new tests in `tests/test_matching.py` (`TestAliasMatching`); `test_matching.py` = 63 passed, 1 skipped. Live-verified against the running server: PATCHed `way_Foyer_library_door` → `"go the study"` moved Jake to Library; PATCHed `player_The_Butcher` → `"examine the meat man"` resolved to The Butcher (distinctive alias, not a name substring); inspector Aliases field renders + saves on all four views (item/way/area/character), save round-trip confirmed via `GET /api/graph/nodes`.

## Summary

Let every item, way, area, and character resolve by one or more alternative names in commands — "go the study", "attack the butcher", "take the ghost detector". Aliases live on the node's `properties.aliases` (list or comma/`|`-separated string) and are editable in the inspector.

## Problem

Items could already be targeted by aliases, but ways, areas, and characters could only be matched by their exact display name. Subjective names (pet names, alternate titles, player-typed shorthand) failed: `go the study` fell through to fuzzy/description matching or just missed.

## Implementation

### Backend (`engine/matching.py`)

- `node_aliases(node)` helper — normalizes `properties.aliases` to a lowercase list (accepts list or comma/`|`-separated string). Refactored the existing item alias tier to use it.
- `NameMatching.resolve_exit`: new alias tier inserted after name-boundary matching, before description/fuzzy tiers. Matches way-node aliases OR target-area-node aliases; returns `(edge, way_node, handle)` and sets `_fuzzy_match_note` with "(alias match)".
- `_match_character_name`: new alias tier — resolves the graph character node via `gs._player_node_id(p)`, matches `node_aliases`; ambiguous aliases (shared by multiple characters) return the candidates list for the caller to disambiguate.

### Frontend (inspector)

- `static/js/inspector/helpers.js`: shared `InspectorHelpers.renderAliasesSection(nodeId, aliases)` + `InspectorHelpers.saveAliases(nodeId, value)` (comma-separated input; saves via `api.updateNode(nodeId, { properties: { aliases } })` on Enter/blur, then `worldState.fetch()`).
- Wired into `item-view.js` (after tags), `way-view.js` (after tags), `area-view.js` (after tags), and `agent-view.js` (after Tags; character node id `player_<name with spaces→underscores>` looked up via `worldState.getNode`).

## Testing

- [x] 7 tests in `tests/test_matching.py` `TestAliasMatching`: item alias, comma-string alias, way alias, area alias via exit (fixture ways needed a `connection` edge added), character alias, ambiguous character alias, area alias with no exit stays unmatched — 63 passed, 1 skipped
- [x] Live: `go the study` → Library (way alias)
- [x] Live: `examine the meat man` → The Butcher (character alias, distinctive non-substring)
- [x] Live: Aliases field renders on item/way/area/character views; blur-save persisted `["EMF reader","ghost detector"]` to `inv_Elena Vance_emf_reader` (verified via `GET /api/graph/nodes`)
- [x] All 5 edited JS files pass `node --check`
- [x] Re-run full suite after commit: 824 passed, 1 skipped, 71 deselected, 13 failed (same pre-existing set as baseline — no new regressions)

## Related

- [[todo/gameplay/...|idea #7 — Subjective alias system]] in `developer ideas.md`
