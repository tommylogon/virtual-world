---
type: task
status: review
area: graph
priority: medium
---

# task-460: NL editor library template editing

**Filed:** 2026-09-22
**Related:** task-289, task-317, task-457

## Goal

Let the NL editor edit library registries, not just read them: create/update character, item, area, way and trait templates with schema validation and the mature-content filter, so archetype-level changes ('all goblins have darkvision') are possible and future spawns inherit. Wires the existing POST /api/library/<type> endpoints into ToolRouter with staged review.

## Acceptance

- [x] Batch ops `library_upsert` / `library_delete`
      (`routes/graph_ops.py`: `_BATCH_PHASE` phase 4, `_apply_batch_op`), one
      reviewable op each, applied in the same single undo snapshot as the rest
      of the batch.
- [x] `routes/library_ops.py` refactored: `write_library_entry` /
      `delete_library_entry` are shared by the HTTP `POST /api/library/<type>`
      route and the batch, so there is one write path.
- [x] NL tools `upsert_library_entry` / `delete_library_entry` in
      `TOOL_DEFINITIONS` + ToolRouter (items, characters, areas, ways, traits),
      staged and previewed like every other op; ids are slug-normalised.
- [x] Schema/validation before Apply: registry must be writable, id must be a
      lowercase slug, trait templates need an object `effects`, and the
      mature-content gate refuses `mature: true` entries while mature content
      is off (reuses task-461's validator).
- [x] Agent prompt guidance (rule 10) covers archetype-vs-instance semantics:
      library edits do not touch already-spawned nodes; `link_to_library` and
      refresh push a template to the world.
- [x] Tests: `tests/test_nl_editor_validation.py` (upsert writes the registry,
      bad registry/id refused, mature gate, delete).

