---
type: doc
tags: [system/data]
---

# Scenario Catalogue

**Last generated:** 2026-10-12
**Source of truth:** the JSON files in `data/scenarios/` (this doc is a snapshot).

Every scenario file is a serialized `VirtualWorld`. Counts below are graph nodes
by type; **Area / Way / Item / Char / Trigger** are `graph.nodes` types
(`logic_trigger` counts as Trigger). **Legacy** means the file predates the
graph schema — it has no `graph.nodes` and only the flat `areas` mirror, so it
loads through a migration path rather than directly.

Regenerate the counts with:

```
python tools/scenario_stats.py                # markdown table to stdout
python tools/scenario_stats.py --json         # machine readable
```

Do **not** point `--out` at this file: the raw table would overwrite this
curated one. It is a snapshot to compare against, not a generated artifact.

The **Theme / status** column is hand-assigned (the tool cannot infer it); the
numeric columns are reproducible.

## At a glance

- **22 JSON files** in `data/scenarios/` (21 scenario-ish + `world_template`).
- **5 legacy files** with no graph: `apartment`, `combat_pit`, `corsair`, `heist`, `testapartment`.
- **3 Millbrook Falls**-setting files: `autosave` (live dump), `pines`, `taco_bell_date`.
- **5 "Supers in Hiding" / Violet Parr** files, all LLM-generated except the hand-authored `violet_parr_scenario`: `kimi_instant`, `unnamed`, `Qwen_…with guide`, `deepseek_thinking-with-guide_…`, `violet_parr_scenario`.
- **2 Mujeeroth (1584)** files: `world_template` (baseline) and `The Valerious Case` (same graph, 224 nodes).
- **Templates / infrastructure:** `world_template.json` (canonical schema baseline), `autosave.json` (live world dump, not authored).
- **Dev sandbox:** `labs.json` is task-numbered test rooms, not a story.
- **`kraktooth_goblin_camp.json` is the outlier** — 2,763 nodes, which is **57% of every node in `data/scenarios/`**. It was 142 nodes when this page was last generated in September; it has grown roughly twentyfold and is now the stress case, not `mansion`.

## Files

| File | Name | Areas | Ways | Items | Chars | Triggers | Nodes | Edges | Players | Theme / status |
|---|---|---|---|---|---|---|---|---|---|---|
| `kraktooth_goblin_camp.json` | kraktooth_goblin_camp | 629 | 1391 | 471 | 27 | 245 | 2763 | 6340 | 27 | **Canonical (dominant)** — fantasy goblin tribe camp between the Raven River, Deep Forest and Black…. Largest cast (27 characters) and by far the largest graph; grew from 142 nodes in September. |
| `mansion.json` | mansion | 25 | 27 | 230 | 9 | 183 | 474 | 581 | 9 | **Canonical (rich)** — modern US mansion (Oklahoma). Densest trigger/item scenario; the trigger stress case. |
| `mansion2.json` | mansion2 | 24 | 27 | 178 | 5 | 64 | 298 | 355 | 5 | **Canonical (trimmed)** — slimmer mansion; 4 fewer characters, ~1/3 the triggers. |
| `pines.json` | pines | 23 | 26 | 124 | 21 | 1 | 195 | 250 | 21 | **Canonical / dev target** — Millbrook Falls, The Pines apartment complex. Scope manifest + 5 resident schedules (task-400). |
| `labs.json` | labs | 36 | 16 | 63 | 9 | 49 | 173 | 195 | 9 | **Dev/test sandbox** — areas are task-numbered ("Task 18 - Room 5…"), no `world_lore`. Most areas of any file except kraktooth. |
| `The Valerious Case.json` | The Valerious Case | 19 | 19 | 87 | 3 | 96 | 224 | 278 | 3 | **Canonical** — 1584 Mujeeroth investigation (unexplained disappearance). Same graph as the template, plus authored lore. |
| `world_template.json` | world_template | 19 | 20 | 98 | 3 | 99 | 239 | 296 | 3 | **Template** — Mujeeroth, year 1584 (Rocheveron). Canonical schema baseline. |
| `taco_bell_date.json` | taco_bell_date | 8 | 7 | 34 | 3 | 29 | 81 | 111 | 3 | **Canonical (small)** — Millbrook Falls slice; a Taco Bell date scene. |
| `corsair_2025.json` | corsair_2025 | 13 | 12 | 72 | 2 | 0 | 99 | 120 | 2 | **Sci-fi** — Drake Corsair DH-02 multi-crew freighter. Modern rewrite of `corsair.json`, item-heavy, no triggers. |
| `autosave.json` | autosave | 7 | 6 | 15 | 3 | 16 | 47 | 61 | 3 | **Infrastructure** — live-world dump (Millbrook Falls), overwritten by autosave. Not authored. |
| `kimi_instant.json` | kimi_instant | 6 | 12 | 17 | 14 | 0 | 49 | 54 | 2 | **Supers (LLM, Kimi)** — rich cast, no triggers, top-level `players` registry incomplete. |
| `morphocene.json` | morphocene | 9 | 10 | 18 | 7 | 0 | 44 | 65 | 7 | **Alt-history fantasy** — demihumans ("demis") won legal personhood 70 years ago. 0 triggers. |
| `Qwen_json_20260811_4eevuw4hk - with guide.json` | Qwen…with guide | 11 | 10 | 8 | 9 | 3 | 41 | 60 | 4 | **Supers (LLM, Qwen)** — structurally sound generated attempt. |
| `violet_parr_scenario.json` | violet_parr_scenario | 9 | 9 | 18 | 14 | 13 | 63 | 81 | 14 | **Supers (hand-authored)** — Violet Parr / "Supers in Hiding" set. Most characters; clearest of the Supers files. |
| `deepseek_thinking-with-guide_json_20260811_55aa77.json` | deepseek_thinking-with-guide… | 5 | 4 | 9 | 11 | 4 | 33 | 40 | 2 | **Supers (LLM, DeepSeek)** — character-heavy, small map; empty `world_lore`. |
| `art_heist.json` | art_heist | 3 | 2 | 4 | 2 | 4 | 15 | 17 | 2 | **Small test** — art heist; trigger-per-node ratio is high because the graph is tiny. |
| `unnamed.json` | unnamed | 4 | 3 | 4 | 5 | 0 | 16 | 21 | 0 | **Supers (LLM)** — a 16-node fragment with no players. **No longer the `kimi_instant` duplicate it was in September** (that file is 49 nodes); do not delete it on the old reasoning. |
| `corsair.json` | Drake Corsair DH-02 | — | — | — | — | — | 0 | 0 | 2 | **Legacy (no graph)** — 13 areas in the flat mirror; superseded by `corsair_2025.json`. |
| `apartment.json` | apartment | — | — | — | — | — | 0 | 0 | 0 | **Legacy (no graph)** — 5 flat areas. |
| `testapartment.json` | testapartment | — | — | — | — | — | 0 | 0 | 0 | **Legacy (no graph)** — 7 flat areas; test. |
| `combat_pit.json` | combat_pit | — | — | — | — | — | 0 | 0 | 1 | **Legacy (no graph)** — 1 flat area; combat test. |
| `heist.json` | heist | — | — | — | — | — | 0 | 0 | 0 | **Legacy (no graph)** — 2 flat areas; superseded by `art_heist.json`. |

**Totals across files:** areas 850, ways 1601, items 1450, characters 147, triggers 806; 4,854 nodes.

## Reading the numbers

- **One file is most of the repo.** `kraktooth_goblin_camp` holds 2,763 of 4,854
  nodes — 57% — across 629 areas and 1,391 ways. Any measurement taken over
  "the scenarios" is really a measurement over Kraktooth plus noise. It grew from
  142 nodes in September, so every figure quoted before then is obsolete.
- **Items still dominate** (1,450 of 4,854, ~30%) because library-spawned
  furniture and loose items are `item` nodes; `mansion` alone holds 230.
- **Triggers are the second-biggest group** (806) and are concentrated in
  `kraktooth` (245), `mansion` (183), `world_template` (99), `The Valerious Case`
  (96) and `labs` (49) — authored systems, not generated filler.
- **The generated Supers set is broad but shallow**: `kimi_instant` is 6 areas /
  12 ways with **zero triggers**, and `unnamed` collapsed from a 49-node
  duplicate of it to a 16-node fragment. Against a 2,763-node hand-authored file
  the gap is now stark. That is the "generated scenario review" finding, not a
  schema problem.
- **`pines` is the current dev target** for the scope/generation work
  (task-398/399/400): smallest canonical town with a real scope manifest.
- **`mansion` lost edges** (617 → 581) while gaining nodes (472 → 474) — the
  graph got slightly denser in nodes and slightly looser in links. Worth a look
  before trusting either number.

## Related docs

- `docs/virtualWorld/ScenarioCreationGuide.md` — the authoring schema.
- `docs/virtualWorld/Scenario Workflows & UI Audit.md` — commit/import workflows.
- `docs/virtualWorld/World Building/Generated Scenario Review (2026-08).md` — the
  LLM-generated scenario review (Violet Parr prompt drives).
- `docs/virtualWorld/World Building/Millbrook Falls Town Map.md` — the setting map.
- `docs/design/worldpainter-knowledge-and-fog.md` — painting scenarios (task-495/496).

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]]

<!-- connected:end -->
