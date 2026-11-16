---
type: doc
tags: [system/data]
---

# Scenario Catalogue

**Last generated:** 2026-11-13
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

- **25 JSON files** in `data/scenarios/` (23 scenarios + `world_template.json` + `autosave.json`).
- **6 legacy files** with no graph (`0` graph nodes): `apartment`, `combat_pit`, `corsair`, `heist`, `obligation_exchange`, `testapartment`.
- **Millwood / Millbrook Falls** setting files: `Millwood.json` (1,339-node high school sandbox), `science_annex_investigation.json` (chem lab hazard fixture), `pines.json` (apartment complex), `taco_bell_date.json` (fast-food date slice), `autosave.json` (live dump).
- **4 "Supers in Hiding" / Violet Parr** files, all LLM-generated except the hand-authored `violet_parr_scenario.json`: `kimi_instant`, `Qwen_…with guide`, `deepseek_thinking-with-guide_…`, `violet_parr_scenario`.
- **2 Mujeeroth (1584)** files: `world_template.json` (baseline) and `The Valerious Case.json` (same setting, 224 nodes with 96 triggers).
- **Templates / infrastructure:** `world_template.json` (canonical schema baseline), `autosave.json` (live world dump, not authored).
- **Dev sandboxes & fixtures:** `labs.json` (task-numbered test facility), `htc_fixture.json` (courtyard/crypt harness fixture), `art_heist.json` (stealth/vault test), `science_annex_investigation.json` (chem lab reagent fixture).
- **`kraktooth_goblin_camp.json` is still the largest file** - 2,364 nodes (**43% of all 5,520 nodes** across `data/scenarios/`), followed by **`Millwood.json`** at 1,339 nodes (**24%**). Together, those two files hold two-thirds of every node in `data/scenarios/`.

## Files

| File | Name | Areas | Ways | Items | Chars | Triggers | Nodes | Edges | Players | Brief & purpose |
|---|---|---|---|---|---|---|---|---|---|---|
| `kraktooth_goblin_camp.json` | kraktooth_goblin_camp | 592 | 1278 | 467 | 27 | 0 | 2364 | 5631 | 27 | **Canonical (dominant)** - Fantasy world spanning the Kraktooth goblin cave camp (Raven River, Deep Forest, Blackmarsh, dwarven ruins) and Eldenford town. Largest cast (27) and largest graph; multi-faction & world-scale stress case. |
| `Millwood.json` | Millwood | 349 | 908 | 76 | 6 | 0 | 1339 | 3571 | 6 | **Canonical (high school sandbox)** - Millwood High ("The Crimson Gel Pen Note") with the Hellmouth crew and Lulu Ashford. Full-scale multi-location teen social/school simulation and stress test. |
| `mansion.json` | mansion | 25 | 27 | 232 | 10 | 4 | 298 | 353 | 10 | **Canonical (horror mystery)** - 1891 Blackwood family disappearance in Oklahoma; investigators and teens trapped in a locked mansion with The Butcher, Ghost, and Whiskers. Flagship horror survival & multi-agent scenario. |
| `mansion2.json` | mansion2 | 24 | 27 | 178 | 5 | 64 | 298 | 355 | 5 | **Canonical (trimmed)** - Earlier/slimmer Blackwood mansion starting in the Foyer with Elena Vance, without the four teens, keeping 64 triggers. |
| `The Valerious Case.json` | The Valerious Case | 19 | 19 | 87 | 3 | 96 | 224 | 263 | 3 | **Canonical (mystery)** - Year 1584 Mujeeroth; disgraced investigator Kaelen Voss investigates Magistrate Valerious Rocheveron's locked-study disappearance from a Blizzard Forest Clearing. Cold-weather survival + investigation. |
| `pines.json` | pines | 23 | 26 | 124 | 21 | 1 | 195 | 250 | 21 | **Canonical / dev target** - Millbrook Falls, The Pines apartment complex; 30-year-old IT pro Jake checking on Erin amid conspiracy clutter. Scope manifest + 5 resident schedules (task-400). |
| `labs.json` | labs | 37 | 29 | 64 | 9 | 4 | 143 | 200 | 9 | **Dev/test sandbox** - Task-numbered facility (`Task 2`, etc.) with placeholder subjects (`John`, `Jane`, `Bob`, `Zoe`), no `world_lore`. Multi-room / multi-agent engine testbed. |
| `world_template.json` | world_template | 19 | 20 | 98 | 3 | 0 | 140 | 196 | 3 | **Template** - Mujeeroth, year 1584 (Rocheveron). Canonical schema baseline. |
| `corsair_2025.json` | corsair_2025 | 13 | 12 | 72 | 2 | 0 | 99 | 120 | 2 | **Sci-fi** - Drake Corsair DH-02 freighter that dropped out of quantum mid-jump with the crew missing. Modern graph rewrite of `corsair.json` for ship exploration. |
| `taco_bell_date.json` | taco_bell_date | 8 | 7 | 34 | 3 | 29 | 81 | 95 | 3 | **Canonical (small)** - Modern Millbrook Falls; 28-year-old Jake Halloway on an awkward late-evening fast-food date with Miki Doki at Taco Bell. Grounded social/dialogue RP slice. |
| `violet_parr_scenario.json` | violet_parr_scenario | 9 | 9 | 18 | 14 | 13 | 63 | 81 | 14 | **Supers (hand-authored)** - Millwood Public Schools chemistry class; "Supers in Hiding" under threat of government mind-wipes, featuring electromagnetic Jake Halloway and the Parr family. |
| `kimi_instant.json` | kimi_instant | 6 | 12 | 17 | 14 | 0 | 49 | 54 | 2 | **Supers (LLM, Kimi)** - Same "Supers in Hiding" premise at Millwood Public Schools from Jake's perspective; rich cast, 0 triggers. Model-generated scenario test. |
| `autosave.json` | autosave | 7 | 6 | 15 | 3 | 16 | 47 | 61 | 3 | **Infrastructure** - Live-world dump of `taco_bell_date` starting in `Taco Bell Men's Restroom`, overwritten by autosave. Not authored. |
| `morphocene.json` | morphocene | 9 | 10 | 18 | 7 | 0 | 44 | 65 | 7 | **Alt-history fantasy** - Post-emancipation "demis" society at Greenway Grocery; anxious 130cm rabbit-furry Thistle working produce opposite a wolf deli worker. Predator/prey social tension test. |
| `Qwen_json_20260811_4eevuw4hk - with guide.json` | Qwen…with guide | 11 | 10 | 8 | 9 | 3 | 41 | 60 | 4 | **Supers (LLM, Qwen)** - "Supers in Hiding" variant starting in `Halloway House Kitchen`. Model-generated scenario test using the guide. |
| `htc_fixture.json` | htc_fixture | 12 | 16 | 3 | 6 | 0 | 37 | 41 | 6 | **Test fixture** - Courtyard/crypt layout with `Explorer`, `Guard`, `Doctor Brown`, `Doc Holliday`, and `Crypt Ghoul`. Dedicated harness fixture. |
| `deepseek_thinking-with-guide_json_20260811_55aa77.json` | deepseek_thinking-with-guide… | 5 | 4 | 9 | 11 | 4 | 33 | 40 | 2 | **Supers (LLM, DeepSeek)** - "Supers in Hiding" variant at `Millwood_Public_School` from Violet Parr's perspective; empty `world_lore`. Model-generated scenario test. |
| `art_heist.json` | art_heist | 3 | 2 | 4 | 2 | 4 | 15 | 17 | 2 | **Small test** - Museum Grand Gallery with painting, locked vault, and rooftop escape (`Thief`, `Guard`). Minimal stealth/vault/escape mechanic test. |
| `science_annex_investigation.json` | science_annex_investigation | 3 | 2 | 3 | 2 | 0 | 10 | 13 | 2 | **Small test** - "Millwood Science Annex - Hazardous Reagents" in a chem lab (`Jake Halloway`, `Sammy Lopez`). Small hazard/reagent investigation fixture. |
| `corsair.json` | Drake Corsair DH-02 | - | - | - | - | - | 0 | 0 | 2 | **Legacy (no graph)** - 13 flat areas aboard the Drake Corsair; superseded by `corsair_2025.json`. |
| `testapartment.json` | testapartment | - | - | - | - | - | 0 | 0 | 0 | **Legacy (no graph)** - 7 flat areas (hallway, coat rack, moving boxes); spatial/container test stub. |
| `apartment.json` | apartment | - | - | - | - | - | 0 | 0 | 0 | **Legacy (no graph)** - 5 flat areas; early apartment layout stub. |
| `combat_pit.json` | combat_pit | - | - | - | - | - | 0 | 0 | 1 | **Legacy (no graph)** - Circular stone fighting pit with club-wielding brute `Gromm`; minimal combat test. |
| `heist.json` | heist | - | - | - | - | - | 0 | 0 | 0 | **Legacy (no graph)** - Corporate corridor with disabled security lasers; superseded by `art_heist.json`. |
| `obligation_exchange.json` | obligation_exchange | - | - | - | - | - | 0 | 0 | 2 | **Legacy (no graph)** - Stone council chamber (`Elder Mara`, `Brek`); minimal social/obligation-exchange test. |

**Totals across files:** areas 1174, ways 2424, items 1527, characters 157, triggers 238; **5,520 nodes**.

## Reading the numbers

- **Two files are two-thirds of the repo.** `kraktooth_goblin_camp` (2,364 nodes, 43%) and `Millwood` (1,339 nodes, 24%) together hold **3,703 of 5,520 nodes (67%)** across 941 areas and 2,186 ways.
- **Ways and items dominate** (2,424 ways and 1,527 items out of 5,520 nodes) - `kraktooth_goblin_camp` and `Millwood` drive the way count, while `mansion` (232) and `kraktooth` (467) lead in items.
- **Triggers are concentrated in authored mystery/test scenarios** (238 total): `The Valerious Case` (96), `mansion2` (64), `taco_bell_date` (29), `autosave` (16), and `violet_parr_scenario` (13).
- **The generated Supers set is broad but shallow**: `kimi_instant`, `Qwen`, and `deepseek` have small maps (5-11 areas) and 0-4 triggers compared to hand-authored `violet_parr_scenario` (13 triggers).
- **`pines` is the dev target** for scope/generation work (task-398/399/400): smallest canonical town with a real scope manifest.

## Related docs

- `docs/virtualWorld/ScenarioCreationGuide.md` — the authoring schema.
- `docs/virtualWorld/Scenario Workflows & UI Audit.md` — commit/import workflows.
- `docs/virtualWorld/World Building/Generated Scenario Review (2026-08).md` — the
  LLM-generated scenario review (Violet Parr prompt drives).
- `docs/virtualWorld/World Building/Millbrook Falls Town Map.md` — the setting map.
- `docs/design/worldpainter-knowledge-and-fog.md` — painting scenarios (task-495/496).

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply`  -  relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes**  -  [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]]

<!-- connected:end -->
