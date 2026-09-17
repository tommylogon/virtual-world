# Mujeeroth Scale Plan — Zoom Levels, Procedural Fill, and Background Simulation

**Filed:** 2026-09-08  
**Scope:** VirtualWorld engine — world-scale streaming for Mujeeroth

---

## 1. What already exists (verified against code)

The six `todo/world/` tasks (397–402) are **already filed and unstarted**. They are correct and I will not rewrite them. Here is the code-grounded status of each dependency:

| Task | Code status | Verdict |
|------|-------------|---------|
| **397** Scope hierarchy + projection API | `grep world_scope\|scope_id\|chunk` → 0 hits in `*.py`. `routes/graph.py` still serves `/api/graph/nodes` + `/api/graph/edges` (full dump). `routes/world_lore.py` is the only world-level route and it is CRUD-only. | Genuinely unstarted. |
| **398** Deterministic structure generation | `routes/library_ops.py:110` has `_spawn_library_item_node` (private). No `engine/population.py` exists. No generation recipe system. | Unstarted. |
| **399** Background character simulation | `engine/tick_manager.py:163` iterates **every** player every tick. No `simulation_mode` field on `Player`. No background runner. | Unstarted. |
| **400** Pines vertical slice | `saves/` has autosave + 3 scenario saves; no `pines.json` scenario exists yet. | Unstarted. |
| **401** Chunk persistence + gateway ways | `WorldGraph.load_from_dict()` clears the graph (graph.py:261). No merge/unload API. | Unstarted. |
| **402** Benchmark | No synthetic fixture generator. | Unstarted. |
| **9** Tag-chain item population | `engine/` has no population module. `routes/library_ops.py:110` `_spawn_library_item_node` exists but is route-private. | Unstarted. |
| **323** Library lint validator | `tools/lint_library.py` exists (inprogress). | In progress. |
| **324** Domain tag schema | `routes/tags.py` has `/api/tags/search`, `/api/tags/validate`, `/api/tags/stats`. 23/58 areas have tags, none domain-flavored. | Unstarted. |

**Key finding:** the dependency chain is real. 397 → 398 → 400, and 323 → 324 → 9 → 398. Nothing in the world/ chain can start before 323 lands.

---

## 2. The plan (ordered, dependency-aware)

### Phase 0 — Unblock the chain (2 tasks, can start now)
1. **task-323** (inprogress) — finish `tools/lint_library.py`. This is the gate for 324.
2. **task-324** — domain tag schema + area/furniture tagging pass. This is the gate for task-9 and task-398's tag-aware population.

### Phase 1 — Procedural fill engine (your stated #1 goal)
3. **task-9** — tag-chain population engine (`engine/population.py`). This is the reusable core: area domain tags → furniture with matching domain tag + role tag (`display`/`container`) → items with matching domain tag. Placement via existing spatial edges (`in`/`on`/`beside`/`at`). Deterministic, seedable, idempotent.
4. **task-398** — wraps task-9 into deterministic scoped structure generation (building/district/town recipes → `GenerationPatch` of normal graph nodes/edges).

### Phase 2 — Zoom / scope / projection (your stated #2 goal)
5. **task-397** — hierarchy manifest (`world_scopes`), server-side projection API (`GET /api/world/scopes/<id>` and `/graph?depth=N&include_items=...`), scope breadcrumb UI.
6. **task-401** — chunk persistence, scoped indexes, gateway ways, merge/unload APIs. This is what makes the projection API actually cheap at million-node scale.

### Phase 3 — Background simulation (your stated #3 goal)
7. **task-399** — `simulation_mode: active|background` on existing `Player`. Background runner in `engine/background_simulation.py`: deterministic schedule/needs/vitals progression, no LLM calls, structured event log, "since last full mode" memory summary on reactivation.

### Phase 4 — Proof
8. **task-400** — Pines vertical slice combining 397+398+399.
9. **task-402** — 100k+ node synthetic benchmark proving projection payload stays bounded.

---

## 3. Critical path

```
323 (inprogress) → 324 → 9 → 398 → 400
                         ↓
              397 → 401 → 402
                         ↓
              399 →───────┘
```

The **longest pole is task-324** (domain tag data pass over 58 areas + 44 furniture items + tag library). Everything downstream of it is blocked. Start there.

---

## 4. What I will do next

- Move task-323 to done if it is actually finished (verify `tools/lint_library.py` output).
- Execute task-324: register `display`, `store`, `kitchen`, `library` tags; write `tools/tag_domains.py`; backfill area + furniture tags.
- Then task-9, then task-398.

Say the word and I start with 324.