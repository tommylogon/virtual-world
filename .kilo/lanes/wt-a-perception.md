# WT-A — Perception and world presentation

**Parallel arm.** You touch no hub file. Merge first.

## Your queue — 11 tasks

| Task | Priority | Title |
|---|---|---|
| task-569 | high | Biome resource distribution consumer |
| task-550 | high | Faction and ownership as tags: a camp's water is the camp's |
| task-411 | medium | Attention budget and fidelity tiers |
| task-421 | medium | Light propagation barrier parity with sound |
| task-499 | medium | Per-agent fog of war and map knowledge transfer |
| task-500 | medium | Zone-driven fidelity and lazy zone materialisation |
| task-522 | medium | Way blocking pass: outdoor ways can't be hand-closed; seed-picked blockers |
| task-408 | high | Goblin scenario consolidation, dedupe, and folder authoring |
| task-498 | low | Elevation-gated chained sightlines across ways |
| task-565 | medium | Migrate the goblin camp scope id off `deep_woods_2` |
| task-570 | medium | Hostile distribution consumer |

Suggested order: 569, 408, 550, 421, 522, 570, then the fidelity cluster
(411, 499, 500, 498) and 565 last, since the scope-id migration is fiddly and benefits
from the others landing first.

## Primary files

```
engine/sound.py          engine/lighting.py        engine/room_perception.py
engine/area_description.py                       engine/biomes.py
engine/world_grid.py     data/worldpainter/biomes.json
```

Watch `engine/area_description.py` — several tasks across all lanes mention it. Keep your
edits in their own region and rebase before merging.

## Also yours

**task-418, task-419, task-400, task-401, task-402 are NOT yours** — they depend on
WT-0's task-416 / task-397 and belong to the spine.

## Cross-lane

- **task-408 blocks task-409** (WT-C, background schedules) and **task-414** (WT-0).
  Ship it early — it is gating two other lanes.
- **task-569 depends on task-504** (WT-B, item quantity). Coordinate on the board; if
  504 is not started, do the other nine tasks first.

## Rules

- Full rules in `.kilo/lanes/README.md`.
- Do not edit any of the eight hub files. If you need one, note it on the board and move on.
- `templates/index.html` and `tools/unit/run.cjs` are shared append-only — add your lines,
  do not reorganise.
