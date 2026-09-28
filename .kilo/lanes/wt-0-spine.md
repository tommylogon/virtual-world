# WT-0 — Spine: hub files and world scale

**You are the only lane allowed to edit the eight hub files.** Everything else in the
project routes through you. Work your queue in order; this is a queue, not a parallel set.

## Critical path — strict order, do not reorder

| Order | Task | Title | Blocked by |
|---|---|---|---|
| 1 | task-416 | Area-major tick iteration | — |
| 2 | task-397 | World scopes, hierarchy manifest, server graph | — |
| 3 | task-418 | Awareness channels — audibility replaces `radius_hops` | 416 |
| 4 | task-419 | Relational spatial model — one `at` per character | 416 |
| 5 | task-398 | Deterministic scoped structure generation | 397 |
| 6 | task-400 | Pines vertical slice for grouped generation | 397, 398 |
| 7 | task-401 | Chunk persistence, scoped indexes, gateway ways | 397, 400 |
| 8 | task-402 | Large-world projection and indexing benchmark | 397 |

Start at 416 or 397 — they are independent of each other, but everything else hangs off
one of them.

## The rest of the hub queue

Work these after the critical path, still one at a time, still hub-only.

`engine/tick_manager.py` — 54, 215, 352, 404, 430, 440, 488, 489, 533, 538, 545, 546
`engine/serialization.py` — 429, 439, 446, 447, 453, 537
`virtual_world_engine.py` — 83, 99, 555
`routes/library_ops.py` — 289, 317, 442, 450, 487, 514, 519, 571
`routes/action_handlers.py` — 414, 433, 448, 491, 556
`player.py` — 549 · `routes/action.py` — 299 · `app.py` — 83

## Also yours

- **task-446** is `inprogress` and touches `serialization.py` and `virtual_world_engine.py`.
  It is the id-first identity work; check whether it has already moved before starting
  anything that assumes ids.
- Three queued tasks are blocked by things outside this queue and need promoting first:
  **task-407** (graph edge indexing) blocks three others, **task-553** (per-area
  temperature) blocks task-556, **task-53** (in `review`) blocks one.

## Owns exclusively

```
engine/tick_manager.py            engine/serialization.py
virtual_world_engine.py           routes/library_ops.py
routes/action_handlers.py         routes/action.py
player.py                         app.py
```

## May also edit freely

Anything not owned by WT-A, WT-B or WT-C. Check `.kilo/lanes/README.md` before assuming
a file is yours.

## Rules

- Full rules in `.kilo/lanes/README.md`. In short: never `git stash`; claim each task with
  `tools/tasks.py move`; clear the gate before proposing a merge; post to the board when
  you start and when you finish.
- **You merge last.** Rebase onto `master` after each arm lands, and expect to resolve
  conflicts here rather than in the arm.
- Arms will hand you hub changes. When one arrives, either do it yourself or say so on the
  board so the arm can proceed.
- Your changes to `engine/serialization.py` and `virtual_world_engine.py` are the ones most
  likely to invalidate a queued task. After each one, check whether anything in
  `.kilo/lanes/` assumed the old behaviour and say so on the board.
