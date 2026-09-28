# WT-C — Characters and social

**Parallel arm.** You touch no hub file. Merge first.

## Your queue — 11 tasks

| Task | Priority | Title |
|---|---|---|
| task-547 | high | Observation signal: who saw whom this turn |
| task-552 | high | Fear response: humans should fear goblins |
| task-457 | high | Character nodes are the canonical character record |
| task-409 | high | Background schedules, daily reflection, coarse social behavior |
| task-505 | medium | Embedding bridge: resolve novel emotion/emote labels to affect dimensions |
| task-507 | medium | Structured appearance & personality fields for characters |
| task-484 | medium | Tune the frightened condition once real fears exist |
| task-490 | low | Incorporeal undead: damage resistance and condition immunities |
| task-354 | — | Pack logic for simple NPCs |
| bug-28 | — | `=== CONVERSATION ===` echoes characters' own speech mangled |
| bug-29 | — | Same witnessed speech appears twice with different attributions |

Suggested order: **bug-28 and bug-29 first** — both are cheap, both are in
`engine/speech.py` and `static/js/agent/prompt-builder/`, and both are currently blocked
on finding a live repro rather than on design. Then 547 (observation) and 505 (emotion
bridge), which the fear work builds on, then 552 → 484, then 409, 457, 507, 490, 354.

## Primary files

```
engine/npc_behaviors.py    engine/background_social.py    engine/speech.py
engine/relationships.py    engine/emotion.py
static/js/agent/prompt-builder/conversation-context.js
static/js/agent/prompt-builder/room-context.js
static/js/agent/involuntary.js
```

## Warnings

- **task-457** ("character nodes are the canonical record") is close to
  `engine/serialization.py` and `player.py` — both hubs. Do the parts that do not need
  them, then hand the rest to WT-0.
- **task-409 is blocked by task-408** (WT-A, goblin scenario consolidation). Do not start
  it until WT-A says it has landed.
- **task-426** is blocked by 409 and is not otherwise assigned — pick it up after 409, or
  hand it back to the coordinator.
- **bug-28 and bug-29** may be obsolete: the task files say the filed evidence does not
  reproduce against current code and suspect the conversation-context refactor. A live
  repro is required before any fix. If you cannot produce one, say so on the board and
  recommend closing them — that is a valid outcome.

## Rules

- Full rules in `.kilo/lanes/README.md`.
- Do not edit any of the eight hub files.
- `templates/index.html` and `tools/unit/run.cjs` are shared append-only.
