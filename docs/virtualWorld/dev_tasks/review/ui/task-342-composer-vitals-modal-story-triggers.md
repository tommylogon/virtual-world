# Task 342 — Composer you-strip: full vitals + vital detail modal + story triggers

**Status:** In Review — implemented 2026-08-24, full suite 1130 passed,
scenario audit H=0 M=0. Browser E2E pending.

## Why

2026-08-24 playtest feedback (Tommy): the turn composer's YOU strip
showed only 6 hardcoded vitals with pre-task-337 identity colors (Hunger
72 rendered GREEN — misleading for a drive), and there was no way to
open the vital detail modal from the panel. Second point: native engine
verbs (take/open/search) don't NEED triggers, but flavor triggers give
items story — the audit's "no triggers" flags were opportunities, not bugs.

## Implementation

- `static/js/shared/vital-color.js` (new) — ONE polarity-aware
  bar-color/percent/suffix implementation reading `vital_polarity` from
  world state. Inspector `agent-view.js` refactored onto it (was a local
  copy); composer `turn-you-strip.js` now uses it too — the strip's
  fixed identity colors are gone, Hunger/Thirst/Bladder go red when high
  exactly like the inspector.
- `turn-you-strip.js` — renders ALL vitals (preferred order + any
  extras, `Max_*` skipped), Temperature shows °C with the 25–45 window
  mapping, every vital is clickable → the shared `openVitalModal`
  (task-113 modal, already global in index.html).
- `engine/scene_snapshot.py` — `scene.you.name` added so the strip can
  address the modal (test: `test_you_strip_carries_character_name`).
- taco_bell scenario: 5 story triggers on native-action items —
  earring/monster can/phone `on_examine`, cash register `on_open`
  (Tyler's stare), register drawer `on_search` (the DO NOT COUNT post-it).

## Verification

- pytest 1130 passed; `node --check` on all three touched JS files
- Scenario audit: HIGH 0, MED 0 (was H=1 M=14 after the wardrobe pass)
- Browser: composer strip shows all vitals with inspector-matching
  colors; click a vital → detail modal; examine the earring → flavor.
