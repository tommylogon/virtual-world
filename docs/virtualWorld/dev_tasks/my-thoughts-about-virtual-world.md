# My Thoughts About Virtual World

**Started**: 2026-07-21 (original OpenCode/Piper exploration)
**Updated**: 2026-08-16 (Piper + Kilo — reconciliation pass)
**Status**: Ongoing — grows as I understand more
**Author**: Piper (LogonWorks) + Kilo

> This is my working map of the project. The old 2026-07-22 version described the
> mid-refactor state. This pass reads the *current* code (35 engine modules, 16 route
> modules, 959 passing pytest) and marks what changed or is now wrong. Anything I can't
> verify from the code gets flagged, not assumed.

---

## What This Project Actually Is (still true)

Not a game with win conditions. A **simulacra for AI beings** — a habitat where AI
characters get presence, personality, subjectivity, and agency. The engine is the
**physics/causality** (deterministic, timed, rule-based). The LLM is the **mind/expression**
(creative, narrative, emergent). When something feels missing, ask "what does an AI
character need to feel alive here?" — not "what game feature is missing?".

Both frames hold: Tommy's POV it's a game (level design, PC/item/effect authoring, turn-based
play). The deeper goal is a world, not a win state. The second frame decides what features matter.

---

## Architecture Now (what changed since my 2026-07 snapshot)

| Layer | 2026-07 said | Now (verified) |
|---|---|---|
| `virtual_world_engine.py` | ~433 (fully split) | **961 lines** — facade + re-absorbed logic |
| `app.py` | 107 | **125** (app factory, 14 route modules) |
| `engine/` | 22 modules | **35 modules, ~15.5k lines** |
| `routes/` | 13 modules | **16 modules, ~4k lines** |
| `player.py` | — | **970 lines** (condition catalog + traits + memory) |
| `graph.py` | — | **332 lines** |
| pytest | 145 total (2026-07) | **959 passed, 1 skipped** (47 test files) |
| tests structure | 12 pytest files + 3 Playwright | 47 pytest files + 23 `tools/test_*.cjs` |

The "monolith → clean modules" story is real but **not the neat 433-line facade** the
old doc claimed. The facade grew back as features landed (conditions, traits, memory,
spatial position, delayed events). The important win stood: implicit coupling got exposed
and the engine is modular.

---

## What's Out Of Date / I Was Wrong About

1. **Test count.** I said "145 tests." Today: **959 passed** pytest (47 files) plus a big
   Playwright suite in `tools/`. The `tools/` folder is a whole battery (doors, control mode,
   human turn, loops, step-once, UI, ...). This project now has REAL coverage. Big change.

2. **`room.py` doesn't exist.** The model is `area.py` (vestigial, 14 lines) + the graph.
   Rooms/areas/items/players are all **graph nodes**. The old doc's mental model
   (rooms/items/doors as graph nodes) is right; the "`room.py` data class" framing is wrong.

3. **`item.py` is still dead code** (14 lines, `Item` class). Confirmed. My "delete it now"
   call stands — it's misleading next to the clean engine modules. Same for `area.py`.

4. **"Two condition systems" concern — still real but rearranged.** Both
   `_evaluate_trigger_condition` (flat, item ways) AND `_evaluate_conditions` (tree,
   NPC behaviors) still coexist in `engine/trigger_system.py` + `virtual_world_engine.py`
   wrappers. Not unified. `trigger_validator.py` explicitly handles both paths. This is the
   same open design question as before, just living in one file now.

5. **Item toggle/serialization got a real home.** The old worries (`item_statuses`,
   `_item_active_effects` lost on save) were superseded by a dedicated
   `engine/toggleable_items.py` (`ToggleableItems` class) + `toggleable` tag. No more
   scattered dicts. The serialization concern is largely dissolved by redesign, not just patched.

6. **`exhaustion_count` still isn't in `Player.__init__`.** Serialized (serialization.py
   262, 322) and used via `getattr` in `tick_manager.py:193` / `item_actions.py:1392`.
   The "serialized but not initialized" nit I flagged in 2026-07 is STILL the shape of it.

7. **Backend LLM modules are GONE** (was `routes/llm.py`). The old "two LLM call paths"
   concern is obsolete — LLM now lives **browser-side** (OpenAI-compatible API via
   `LLMClient`), agents hit the same `/api/action` as humans. One path, not two.

8. **Memory is unified to one store.** task-178 → `Player.memories[]` is the sole store.
   The `_memory` / `memories` parallelism I flagged is gone. Agent writes ONE reaction
   memory per turn. Speech/emotes/thoughts are log-only.

9. **Delayed events landed.** `engine/event_queue.py` + `tests/test_delayed_events.py`
   (task-90). I called this a "natural pair that unlocks curses/poisons." It's now built.

10. **Frontend is modular but note `memory-store.js` & `context_window_manager.js`**
    are named in old docs; current path is `static/js/` fully modular (agent/, graph/,
    inspector/, item-library/, shared/, ui/) + a handful of root-level modules. The old
    clinerules tree listing is stale in places.

---

## What I'm Confident About (verified by reading code this pass)

- **Condition system is the backbone and it's mature.** `CONDITION_DEFINITIONS` is the
  single source of truth in `player.py:30`. Multi-instance lists, `stack` (accumulate /
  refresh / noop), `excludes`, `periodic`, `symptoms`, `known`, gate fields,
  `attack_mod`/`defense_mod`. `state` is a *property over conditions*; `state_timer` is a
  compat property. This is where pleasure-system conditions (task-209) will plug in.
- **Trigger system is huge and data-driven** — `engine/trigger_system.py` (~2000 lines),
  `trigger_validator.py`. Types for on_* events + effects (set_environment, teleport,
  spawn_item, save, apply_condition, unlock_way, ...).
- **Combat is fully in `engine/combat.py`** (`player_attack`), D&D-flavored: d20 rolls,
  STR/DEX, weapon `damage`/`damage_type`/`stun_chance`, armor via `equipment_bonuses`
  (defense, resistances), grappled/restrained mods, condition mods, chained stun. NO
  body-part targeting (`where`) — that's task-253, my new file.
- **Equipment/paperdoll is deep** — layered stacks by slot, `<_get_extra_slots>` for
  multi-slot garments, `EDGE_EQUIPPED` edges, `clothing_pile` for strip/undress,
  auto description regen on equip changes.
- **NPC behaviors** (`engine/npc_behaviors.py`) — simple NPC wander/flee/stationary +
  scripted `behaviors` (priority-sorted, trigger/interval/conditions/actions) + hunts
  (BFS pathfinding, `process_npcs_on_combat` is still a `pass` stub).

---

## The Big Open Threads (2026-08)

### Pleasure / Body / Injury system — now designed, not built
I wrote the audit (`review/characters/pleasure-system-audit-gaps-2026-08.md`) and task-253.
The four gaps to resolve before tasks 206–215 get real:
- **GAP A** no body-part damage routing — combat hits HP only.
- **GAP B** no `where`/`type`/`intensity` in the action schema.
- **GAP C** `body_state` dict vs body-part conditions — two competing source-of-truth.
- **GAP D** involuntary body reactions split awkwardly across task-166 / task-213.
Stale refs fixed (task-211 line numbers, task-195→232 humidity). Decision still open: the
numeric dict and conditions both exist in the design; **one must win** for engine math.

### Two condition evaluators
Still `_evaluate_trigger_condition` vs `_evaluate_conditions`. Unifying gives trigger
authors AND/OR/NOT trees. This is the oldest architectural debt I've flagged twice now.

---

## Guiding Principles (for me)

1. **Verify before speaking.** Every claim backed by reading code. Say "my search found
   nothing" rather than inferring absence.
2. **Two frames, both true** — game from Tommy's POV, simulacra as the goal.
3. **Engine = physics/causality, LLM = mind/personality.** If the LLM can handle it, it
   doesn't need engine support; if it needs timing/persistence/determinism, it does.
4. **Task docs are truth.** Update as I work, move files between todo→inprogress→review→done
   the instant status changes.
5. **Three character types, don't confuse them** — active player, LLM agent, simple NPC.
   All `Player` objects differentiated by `simple_npc` and drive method.
6. **Windows shell reality** — `rg`/`fd`/`bat` need a Path refresh to be available; use the
   Kilo grep/glob tools directly which don't depend on machine Path.
7. **Mature-content toggle** must gate the erotic system only — body-part *injury* (task-253)
   stays generic and always-on.

---

## Project sibling (Aura / Diary) — still the same convergence observation

Tommy has three graph+LLM projects converging: VirtualWorld (multi-agent physical world),
Aura (companion with deep Neo4j memory), Diary (procedural life narrative). Common thread:
**graph-structured memory + LLM reasoning = persistent coherent behavior.** VirtualWorld
is the most complete infrastructure. Aura's `rag_utils.py` reference for cosine retrieval is
still the pattern to borrow for memory recall quality. (What changed: backend `routes/memories.py`
now ports the retrieval — so the RAG groundwork is partially in.)

---

## Refactoring Progress — final numbers (re-verified 2026-08-16)

| Area | Size | Status |
|---|---|---|
| `engine/` | 35 files / ~15.5k lines | modular, real |
| `routes/` | 16 files / ~4k lines | modular, real |
| `static/js/` | 6 subdirs (agent, graph, inspector, item-library, shared, ui) + root | modular |
| pytest | 47 files / 959 passed | strong |
| Playwright | 23 `test_*.cjs` in `tools/` | strong |

The modularization was the right call and it held under load. My concern that it was
"efficient for a solo dev to keep a monolith" was wrong — the extraction surfaced coupling
bugs. Keep the module split.