---
type: task
status: todo
area: refactor
priority: medium
---

# task-744: Equipment and body: one edge truth for worn gear, layered coverage, body marks, body-centric UI

**Filed:** 2026-10-08
**Related:** task-654, task-450, task-161, task-660, task-724, task-457, task-619

## Goal

Unify equipment and the body into one edge-backed model and kill the duplicate stores. First deliverable is a design doc in the shape of docs/design/character-entity-refactor-plan.md; this task is filed to be scoped later. MEASURED 2026-10-08: (1) player.equipped is a runtime view of the equipped edges - serialization.py:769 _sync_equipped_from_graph rebuilds it from edges - yet it is ALSO persisted (player.py:1329 to_dict emits equipped; to_scenario_dict does not strip it) and read back on load (serialization.py:406), and on load the persisted dict mints a THIRD representation, EDGE_CONNECTION edges (serialization.py:756-765). Its sibling region_exposed and body_region_names are already stripped as derived (serialization.py:267-268), so keeping equipped is inconsistent. (2) body_parts.is_exposed reads the dict and infers layers from array order (outer = last, body_parts.py:250); equipment_bonuses reads the edges (equipment_bonuses.py:17-19) - same gear, two readers, two homes. (3) the client already derives inventory from carrying/equipped edges (static/js/world-state.ts:209, task-632), so equipped can be derived the same way. (4) layers are not declared: stack order is positional. TARGET: equipped edges are the single truth; slot lives on the edge; order is either an edge property (layer/order int) or an item-to-item under edge for partial-order layering (diagram: character <-equipped- shirt <-under- bra), decided up front; player.equipped becomes a non-serialized derived view; stop persisting it; drop the load-time connection minting. SLICES: 0 stop persisting derived equipment state (mirrors region_exposed, no behavior change); 1 one writer (finish task-654/450); 2 declared layers plus coverage recomposition; 3 derive damage, sensitivity and pleasure from coverage (body_parts, combat is_exposed, body_state sensitivity); 4 body marks - scars, piercings, body hair as per-region authored data whose description composes into appearance prose and feeds mechanics; 5 body-centric UI where the paperdoll IS the region x layer model (click a region for coverage layers, effective sensitivity, marks, composed description). NAMING BLOCKER: EDGE_UNDER already means item to furniture/object hidden beneath (graph.py:836, in SPATIAL_EDGE_TYPES) and cannot also mean garment layering - settle which keeps the name.

## Acceptance

Design doc first, in the shape of `docs/design/character-entity-refactor-plan.md`:
north star, the stores to collapse (the `equipped` dict, the `connection` edge, the
persisted array), the layer model (edge property vs `under` edge), the marks model,
the UI, and the phased slices below each with its own acceptance.

Then, per slice:

- [ ] **Slice 0 — stop persisting derived equipment state.** `player.equipped` is
      dropped from `to_dict`/`to_scenario_dict` (mirroring `region_exposed` /
      `body_region_names` at `serialization.py:267-268`); the load-time
      `EDGE_CONNECTION` minting (`serialization.py:756-765`) is removed; the array
      is a derived, non-serialized view. No behavior change.
- [ ] **Slice 1 — one writer.** Equip/unequip/import/API all write the same edges
      (finish task-654/450). `set_equipped_payload` stops being a dual write.
- [ ] **Slice 2 — declared layers.** Order is explicit and reorder-proof (an edge
      `layer`/`order` property, or an item→item `under` edge for partial-order
      layering — decided up front). `is_exposed` composes the stack instead of
      reading "last in the array".
- [ ] **Slice 3 — derive the body effects.** Damage, effective sensitivity and
      pleasure read one `effective_coverage`/`effective_sensitivity(region)`, not
      the flat `body_state` scalar plus a boolean exposure.
- [ ] **Slice 4 — body marks.** Scars, piercings and body hair are per-region
      authored data; the appearance prose is composed from them and mechanics read
      them. No prose duplicated by hand.
- [ ] **Slice 5 — body-centric UI.** The paperdoll IS the region × layer model:
      click a region for its coverage layers, effective sensitivity, marks, and
      the composed description; a wardrobe/outfit concept; one model, no second
      editor.

## Open decisions before slice 2

- **`under` naming.** `EDGE_UNDER` currently means item → furniture/object hidden
  beneath (`graph.py:836`, in `SPATIAL_EDGE_TYPES`). It cannot also mean garment
  layering; decide which concept keeps the name (or rename the spatial one).
- **partial order or not.** If layering is always a single chain per slot, an
  edge `order` property is the lighter edges-only answer; the `under` edge is
  worth it only if garments genuinely form a partial order (belt and scarf both
  over a shirt).
