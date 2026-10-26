---
type: feature
feature_id: 41
status: wired
section: in-game
tags: [status/wired, surface/in-game, system/memory]
---

# Memory pipeline

**What you can do:** What an agent's recall is built from, including structured dynamics retrieval, embeddings over stored memory, and non-mutating context grounding for the Memory Weaver

## How it works

- [[Memory System]] - unified `Player.memories[]` schema, embeddings, and recall residue
- [[Memory Dynamics]] - structured four-section retrieval (`EVENTS`, `BELIEFS`, `SOCIAL MODEL`, `EXPECTATIONS`), effective importance scoring, and reinforcement
- [[Memory Weaver]] - non-reinforcing context grounding (`POST /api/players/<name>/memories/context`), live `derive.py` relationship previews, and contradiction checks

## Where it lives

- `routes/memories.py` (`/memories/retrieve`, `/memories/reflect`, `/memories/context`, `/memories/reinforce`)
- `engine/memory_dynamics.py`
- `engine/derive.py`
- `static/js/agent/memory-context.ts`
- `static/js/agent/memory-manager.ts`
- `static/js/inspector/mind-view.ts`
- `static/js/inspector/memory-view.ts`

## Connected

- Feature Map: [[Feature Map|row 41]] (In a game)
- Sibling features: [[look-around]], [[examine]], [[move]], [[open-close]], [[take-drop-give]], [[use-use-on]]
- All features: [[Features Overview]]

> [!note] Status - `wired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-05 and updated with structured dynamics retrieval and the Memory Weaver context pipeline (`task-730`).
