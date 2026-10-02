---
type: task
status: review
area: docs
priority: high
---

# task-661: Document the ten user-facing features that have no note

**Filed:** 2026-10-01
**Related:** 

## Goal

Ten shipped, reachable features have no documentation at all. Enumerated and measured in docs/virtualWorld/Feature Map.md (58 features, 10 with no note): search/forage, background simulation (backsim), per-agent knowledge (fog of war), the WorldPainter editor, grid-to-graph compile, the NL editor, recent edits + undo, validator + issues, the event stream, and the soak lab. Write one note per feature, in the vault folder its subject belongs to, and flip the row in Feature Map.md from none to a link when it lands. A feature with no note is the dangerous case: for fog of war the module is complete and tested, task-499 sits in done/, and nothing calls it.

## Resolution

All ten notes written, each grounded in the code it documents and each linked
from its Feature Map row. Files:

- `Gameplay/Search & Forage.md`, `Characters/Background Simulation.md`,
  `Gameplay/Per-Agent Knowledge (Fog of War).md`
- `World Building/WorldPainter.md`, `World Building/Grid to Graph.md`
- `UI & Settings/NL Editor.md`, `UI & Settings/Recent Edits & Undo.md`,
  `UI & Settings/Validator & Issues.md`, `UI & Settings/Event Stream.md`,
  `UI & Settings/Soak Lab.md`

**The documentation corrected the map.** Two rows had been wrong:

- **Background simulation** was marked **unwired** because "the string `backsim`
  appears once". `backsim` is a nickname; the class is imported by name and
  `TickManager.tick_turn` calls `BackgroundSimulation.process_due()`
  (`engine/tick_manager.py:1097-1102`), which is the live `/api/turn/apply` path
  (`routes/action_handlers.py:1384`). Verified by instrumenting a live
  `create_app()` world: the four social passes and `plans.maybe_assign` all fire
  on one `tick_turn()`. Row changed to **wired**.
- **Per-agent knowledge (fog of war)** stayed **unwired**, but this was
  re-verified rather than assumed: `engine/fog.py`'s seven public symbols have no
  importer outside `tests/test_fog.py`, and the only runtime writer of
  `player.known` is scenario load. The note records the authored half that *is*
  live.

Also corrected the Grid-to-graph size claim (largest *non-test* Python file;
`tests/test_trigger_system.py` is larger).

## Acceptance

- [x] One note per feature, in the folder its subject belongs to.
- [x] Every Feature Map row flips from `none` to a `[[link]]`; the file reads 0
      features with no note.
- [x] `python tools/doc_links.py --check` exits 0 with all ten notes linked.
- [x] Each note cites real code (`file:line`) and states wired vs unwired from a
      measured grep/call trace, not from the module's existence.
- [x] The two corrected Feature Map claims are recorded in the map itself.
