---
type: task
status: review
area: docs
priority: high
---

# task-661: Document the ten user-facing features that have no note

**Filed:** 2026-10-01
**Related:** 

## What

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

## Why

Undocumented features lead to developer confusion, false defect reports, divergent implementations, and invisible mechanics that are completed in code but unwired in runtime. Authoring dedicated documentation notes grounded in source code and tracking them in Feature Map.md ensures codebase visibility and establishes accurate wired vs unwired status.

## How

1. Write 10 comprehensive markdown documentation notes in their respective vault folders: Gameplay/Search & Forage.md, Characters/Background Simulation.md, Gameplay/Per-Agent Knowledge (Fog of War).md, World Building/WorldPainter.md, World Building/Grid to Graph.md, UI & Settings/NL Editor.md, UI & Settings/Recent Edits & Undo.md, UI & Settings/Validator & Issues.md, UI & Settings/Event Stream.md, UI & Settings/Soak Lab.md.
2. Update docs/virtualWorld/Feature Map.md rows to link each feature note.
3. Verify wiring and callers via python tools/doc_links.py --check.

## Steps to verify

1. Run doc links verification CLI (python tools/doc_links.py --check).
   - expected: Tool exits 0; all ten documented feature notes resolve without broken links.
   - observed: 0 broken links; all ten notes linked.
2. Inspect docs/virtualWorld/Feature Map.md.
   - expected: Zero features listed as lacking notes; rows contain active wiki links.
   - observed: Feature Map updated with all 10 links.
3. Validate source citations in created notes.
   - expected: Every note cites real file and line locations with verified wired/unwired status.
   - observed: All 10 notes cite exact symbols and call chains.

## Files

- docs/virtualWorld/Feature Map.md
- docs/virtualWorld/Gameplay/Search & Forage.md
- docs/virtualWorld/Characters/Background Simulation.md
- docs/virtualWorld/Gameplay/Per-Agent Knowledge (Fog of War).md
- docs/virtualWorld/World Building/WorldPainter.md
- docs/virtualWorld/World Building/Grid to Graph.md
- docs/virtualWorld/UI & Settings/NL Editor.md
- docs/virtualWorld/UI & Settings/Recent Edits & Undo.md
- docs/virtualWorld/UI & Settings/Validator & Issues.md
- docs/virtualWorld/UI & Settings/Event Stream.md
- docs/virtualWorld/UI & Settings/Soak Lab.md
- 	ools/doc_links.py

## Browser UI and intended live verification

Intended UI home: Not applicable - this task adds conceptual feature notes and Feature Map links; it does not add or change the ten already-shipped product surfaces.

Current availability: the task records ten features with no note in a 58-feature map and requires a note per feature, correct folders, and zero missing-note rows. The documentation coverage is the deliverable.

Why no browser UI: browser checks could demonstrate each existing feature but cannot prove the ten note links, source citations, or measured wired/unwired claims are complete.

Alternative verification steps:
1. Open Feature Map.md and check each of the ten named features: search/forage, backsim, fog-of-war knowledge, WorldPainter, grid-to-graph compile, NL editor, recent edits/undo, validator/issues, event stream, and soak lab.
   - expected: each row links to one note in the folder that owns its subject; no row is left `none`.
2. Follow each note and inspect its source references and wired/unwired claims against actual callers.
   - expected: every note distinguishes implemented, wired, authored, tested, and planned behavior accurately.
3. Run `python tools/doc_links.py --check`.
   - expected: all ten links resolve and Feature Map reports zero features with no note.

This section is not a claim that new product UI was added by this documentation task.
