---
type: feature
feature_id: 22
status: wired
section: in-game
tags: [status/wired, surface/in-game, system/memory]
---

# Memory

**What you can do:** What a character remembers, recall by need, and natural-language memory weaving & backdating in the Mind dashboard

## How it works

- [[Memory System]] - unified `Player.memories[]` store, REST API, and emotional residue
- [[Memory Dynamics]] - activation, confidence, reinforcement, decay, reflection 2.0, contradiction detection, and the **🧠 Mind** dashboard
- [[Memory Weaver]] - user guide and how-to for natural-language opinion asking, relative-time backdating, interpersonal relationship deltas, live previews, and underlying record / lived-log evidence inspection

## Where it lives

- `player.py` (`Player.memories[]`)
- `engine/memory_dynamics.py`
- `engine/derive.py`
- `routes/memories.py`
- `static/js/inspector/mind-view.ts`
- `static/js/inspector/memory-view.ts`
- `static/js/agent/memory-manager.ts`

## Connected

- Feature Map: [[Feature Map|row 22]] (In a game)
- Sibling features: [[look-around]], [[examine]], [[move]], [[open-close]], [[take-drop-give]], [[use-use-on]]
- All features: [[Features Overview]]

> [!note] Status - `wired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-05 and updated with the Memory Mind dashboard and Memory Weaver (`task-730`, `task-785`).
