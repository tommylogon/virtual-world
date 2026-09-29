---
type: task
status: todo
area: library
priority: high
related: [task-291, task-586]
supersedes: "Library 2.0 - Unified Library Design.md §1.3 'Behaviours tab — Remove the tab/type'"
---

# task-590: Make the Behaviours tab real — load `data/library/behaviours/*.json` into the engine

**Filed:** 2026-09-29
**Related:** task-291, task-586
**Supersedes:** `docs/virtualWorld/Library System/Library 2.0 - Unified Library Design.md` §1.3, the "Behaviours tab" row, which says "Remove the tab/type"

## Goal

The shipped Behaviours tab can search, create and save behaviour entries into `data/library/behaviours/`, and `engine/npc_behaviors.py:486` reads only `player.behaviors[]`. So the UI has a **live authoring path that produces files the engine ignores** — the exact divergence the same design doc records for traits, where the chosen fix was unify rather than remove. Fix the engine side instead of deleting a working editor.

## Verified state (2026-09-29)

- **The tab is fully built, not a stub.** `templates/index.html:568` (`data-tab="behaviours"`), pane `#lib-pane-behaviours` at `:697-714` with a search box, `VW.libraryBrowser.newEntry('behaviours')` and `saveEntry('behaviours')`. The `behaviours` type is in `REGISTRY_TYPES` (`library_ops.py:17`).
- **Storage already works.** `load_registry`/`save_registry` (`routes/helpers.py:201-248`) map `behaviours` to `data/library/behaviours/` and write one file per entry, so a save from the tab really lands on disk. The directory is absent only because nothing has been saved yet.
- **The engine never reads it.** `npc_behaviors.py:486` takes `getattr(player, 'behaviors', [])`, sorts by `priority` (`:505`), filters on `trigger` (`:507`), throttles by `interval` in game minutes (`_interval_ticks`, `:59`; used at `:512`), evaluates `conditions` through the trigger system (`:516`) and runs `_execute_behavior_actions` (`:522`).
- **A behaviour record is therefore** `{trigger, interval, conditions, actions, priority}` — and the boot template already ships 11 of them on `rat` (`tests/test_npc_behaviors.py:74-83`).
- **The precedent is one table row above.** Traits had the identical shape of problem — `data/library/traits/*.json` read only by UI pickers while the engine used a hardcoded `TRAIT_DEFINITIONS` — and was fixed by loading the library files into the engine at startup, with the hardcoded dict as fallback.

## Why the doc's recommendation is the wrong fix

The doc's reasoning ("behaviours are per-character data; no blueprint registry exists") is factually right about the engine and wrong about the conclusion. "No registry" is the **defect**, not the argument for deletion: the UI already lets an author create one. Deleting the tab removes the authoring surface and leaves the engine exactly as unable to consume a reusable behaviour as it is today — and two characters with the same patrol still mean copy-pasted JSON. Unify keeps the tab, makes what it writes meaningful, and removes the divergence instead of hiding it.

## Open questions

1. **Reference or inline-merge?** Options: a character carries `behavior_refs: [id]` and the engine resolves them at load; or library behaviours are merged into `player.behaviors` as the traits catalog merges over `TRAIT_DEFINITIONS`. The second keeps the evaluator untouched but makes provenance unclear; the first is explicit and cheap. Pick one and say why.
2. **What does a character do with a ref that does not resolve?** It must be reported, not silently dropped — the same rule `world_compile` follows for an unknown biome id (`biomes.py:74-79`). Startup report or tick-time warning?
3. **Do the 11 `rat` behaviours migrate?** They are the only authored set in the tree and the natural first content. If they stay inline, the engine supports both and the question is which one the tab writes.
4. **Reload on save.** `npc_behaviors` holds no registry cache today, so a save can be picked up on the next character load — confirm that, and if a cache appears, wire the invalidation the way conditions do (`reload_condition_library`).

## Acceptance

- A behaviour saved from the Behaviours tab **runs**. The regression test: write an entry, attach it to a character, tick, assert the action fired — and assert the negative, that an unresolvable ref is reported rather than ignored.
- Every file in `data/library/behaviours/` is either consumed or reported at startup. A library folder the engine silently ignores is the failure mode this task exists to remove, and the test must fail if one reappears.
- The `rat` behaviours in `world_template.json` are either migrated to `data/library/behaviours/` or documented as deliberately inline, and `tests/test_npc_behaviors.py:74-83` is updated to match.
- `task-291`'s Phase 3 line and the design doc's §1.3 row are corrected to point here, so nobody executes "remove the tab/type" from a six-week-old plan.
