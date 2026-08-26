# Generated Scenario Review — "Complex Stories" Prompt Drives

**Date:** 2026-08-16
**Scope:** LLM-generated scenario attempts in `data/scenarios/generated prompt examples from complex stories/`
**Question:** What do these scenarios call for, what's good, what's missing, what's broken?

---

## 1. What the generator was asked to produce

All 13 files are outputs from different chat/agent LLMs (Gemini 3.6 Flash, ChatGPT, DeepSeek, Kimi, Qwen, Zhipu GLM-5.2) told to generate a **complete VirtualWorld scenario** for the same source story. That story (also the reference the engine already runs) is known from the live `world_template.json`:

- **Setting:** Millwood Public Schools, rural Oklahoma. A tiny PK-12 school.
- **Central pair:** **Violet Parr** — supers-in-hiding teen; invisibility triggers **involuntarily on anxiety**, violet-hued forcefields; flirty/conflicted "good girl" facade. **Jake Halloway** — fellow super in hiding, met in **chemistry class** (the shared-secret origin point, scans as electromagnetism / wears glasses).
- **Cast:** Parr family (Bob, Helen, Dash, Jack-Jack), Halloway family (Vi, Erin, Leah, Marcus), school peers (Chelsea, Maddie), dog **Brutus**.
- **Antagonist:** **The Amalgam** — Project CHIMERA creation; the attack that ruined the Parr house front.
- **Locations:** chemistry classroom/school, The Woods, The Old Steel Mill (contains a railgun hole / deep metal shaft = CHIMERA lab remnants), Halloway House, Parr House (ruined front from the amalgam attack).

A correct scenario is expected to encode all of that as **engine-compatible state**, not prose.

---

## 2. The canonical schema (what "correct" means here)

Borrowed from `data/scenarios/world_template.json` (the only known-working baseline):

- Top-level: `active_player`, `clock_start_hour`, `clock_start_minute`, `current_area`, `game_time`, `ghost_mode`, `narration_mode`, `time_per_tick_minutes`, `time_ticks`, `turn_number`, `world_lore`, **`graph`**, plus denormalized `players`, `areas`/`rooms`, `ways`, `players_in_area`, `item_registry`.
- `graph.nodes` keyed by lowercase id, each `{id, type, name, properties}`. Types: `area`, `way`, `item`, `character`, `trigger`.
- `graph.edges` typed; spatial/containment (`in`, `on`, `under`, `behind`, `beside`, `at`, `carrying`, `equipped`) and `connection` for area↔way links, `triggers` for trigger→owner. **No `unlock` edges** (obsolete — must not be emitted).
- `players[charName]`: `current_area`, `personality`, `description` (first sentence = first impression), `stats`, `skills`, `vitals`, `traits`, `tags` (male/female/...), `memories` (structured), `relationships`, `autonomy`, `simple_npc`.

Hard constraints the engine relies on (from project memory): **node/target ids are always lowercase** with case-insensitive reuse; generated ids lowercase; no `unlock` edges.

---

## 3. File-by-file findings

| File | Valid JSON | Has `graph` | Nodes (A/W/I/C/T) | Edges | Story beats | Top-level `players` | `world_lore` | Verdict |
|---|---|---|---|---|---|---|---|---|
| ai_studio_code_gemini3-6-flash.json | ✅ | ❌ legacy | N/A | N/A | Full | 12 (legacy) | ✅ populated | **BROKEN** — legacy flat schema, no graph |
| ai_studio_code_gemini3-6-flash-with-guide.txt | ✅ | ✅ | 36 (10/9/8/7/2) | ~38 | Full | 7 | ✅ populated | **GOOD** — best of set |
| chatgpt-guide and exampel scenario.json | ✅ | ✅ | 29 (7/6/5/4/7) | 27 | Partial (no Parr/Amalgam) | 4 | ✅ 5 entries | **GOOD** — solid but small cast |
| chatgpt-withguide-no example scenario.txt | ✅ | ✅ | 19 (7/6/0/4/2) | 26 | Partial | **1** (Jake only) | ✅ 4 entries | **OK** — mixed/unprefixed ids, incomplete |
| deepseek_json_20260811_b25f3d.json | ✅ | ❌ custom | N/A | 4 custom | Prose only | ❌ none | ❌ | **BROKEN** — custom `characters/locations/connections/items` schema |
| deepseek_thinking_json_20260811_55aa77.json | ✅ | ✅ | 13 (5/4/5/2/0) | 16 | Missing Amalgam | 2 | ❌ empty | **BROKEN** — triggers missing, lore empty |
| deepseek_thinking-with-guide_json_20260811_55aa77.json | ✅ | ✅ | 33 (5/4/9/11/4) | 27 | Missing Amalgam | 2 | ❌ empty | **BROKEN** — Marcus alive contrary to canon |
| kimi_instant - with guide.json | ✅ | ✅ | 60 (6/12/17/14/11) | 48 | Full | ❌ none | ✅ 7 strings | **BROKEN** — richest content, no top-level players, no autonomy |
| kimi_instant.json | ✅ | ✅ | 49 (6/12/17/14/0) | 54 | Full | 2/14 | ✅ 7 strings | **BROKEN** — 0 triggers, players registry incomplete |
| Qwen_json_..._4eevuw4hk.json | ✅ | ❌ custom | N/A | 4 custom | Partial | 6 (custom) | ✅ 5 strings | **BROKEN** — custom schema, wrong time/state fields |
| Qwen_json_...with-guide.json | ✅ | ✅ | 41 (11/10/8/9/3) | 60 | Full incl. Amalgam | 4/9 | ✅ 5 entries | **GOOD** — structurally sound, way registry incomplete |
| zai-glm52_...with-guide.json | ✅ | ✅ | 30 (5/5/5/14/1) | 40 | Partial (no shaft) | 14 | ❌ empty | **BROKEN** — 5 dangling way refs, Title-Case ids |
| zai-glm52_..._114734.json | ✅ | ✅ | 34 (5/10/5/14/0) | 39 | Partial (no shaft) | 14 | ❌ empty | **BROKEN** — 0 triggers, Title-Case ids, lore empty |

---

## 4. The good stuff (what several got right)

- **Every file is valid JSON** — none were truncated or malformed. That's non-trivial for ~80KB structured output.
- **"With-guide" beats "no-guide"** almost universally (more nodes, graph present, richer content). The guide is doing real work.
- **Top performers:**
  - `ai_studio_code_gemini3-6-flash-with-guide.txt` — full 36-node graph, 7 characters with complete fields, populated world_lore, bidirectional connectivity, triggers wired to items. Engine-loadable.
  - `Qwen_json_...with-guide.json` — 41 nodes, 60 edges, all story beats *and* The Amalgam present, populated world_lore, no dangling refs. Strongly if slightly divergent registries.
  - `chatgpt-guide and exampel scenario.json` — clean 29-node graph, 7 triggers, populated lore, good connectivity.
  - `kimi_instant - with guide.json` — the **richest content** (17 items, 11 triggers, deep shaft, full cast) even though its top-level `players` is missing entirely.
- **Content quality varies with model** but the shared intent (chemistry origin, steel mill w/ shaft, woods ambush, ruined Parr house, antagonist) is present in most.
- **`connection` + `in` + `triggers`** are the edge vocab most models converged on — matching the engine's real types (and nobody emitted obsolete `unlock` edges).

---

## 5. What's broken / missing across the corpus

These are the repeat offenders — any single one breaks loading or causes silent misbehavior:

**Structural / schema divergence**
1. **No `graph` at all** (legacy or invented custom schema): `ai_studio_code_gemini3-6-flash.json`, `deepseek_b25f3d.json`, `Qwen_...4eevuw4hk.json`. The engine reads `graph.nodes`/`graph.edges`; these are inert scripts, not scenarios.
2. **Top-level registries diverge from `graph.nodes`.** `players`, `ways`, `areas`/`rooms` are supposed to back the same content, but models drop half the characters/ways: `players` has 1 of 4 (chatgpt-no-example), 2 of 14 (kimi-no-guide), 4 of 9 (Qwen-guide), 2 of 11 (deepseek-guide); `ways` has 3 of 10 (Qwen-guide) or `{}` (deepseek, kimi, zai).
3. **Empty stubs passed off as complete** — `world_lore: []`, `rooms: {}`, `item_registry: {}`, `ways: {}` while the "real" data lives elsewhere or nowhere (deepseek-thinking, zai, kimi-no-guide).

**ID / naming violations (worst category — the engine lowercases *everything*)**
4. **Title Case with spaces** in ids: `player_Jake Halloway`, `player_Jack-Jack Parr` (zai both versions). Guaranteed mismatch on any node/target lookup.
5. **Mixed prefixes**: `player_Jake_Halloway` vs unprefixed `Violet_Parr`/`Chelsea`/`Maddie` in one file (chatgpt-no-example) — a `player_*` lookup fails for half the cast.
6. **Key case mismatch** between node ids (`player_violet_parr`) and `players` keys (`Violet Parr`) (kimi-no-guide, deepseek). The engine's case-insensitive matching should survive some, but the *prefixed/unprefixed* and *Title-Case-with-spaces* ones do not.
7. **Hyphen vs snake_case** (`jack-jack_parr`, deepseek_b25f3d).

**Graph integrity**
8. **Dangling references** — edges pointing at way nodes that don't exist in `graph.nodes` (zai-with-guide: 5 of them). Lead to broken exits / "No exit" errors in play.
9. **Missing trigger graphs** — `trigger` node count is 0 for deepseek-thinking, kimi-no-guide, zai-no-guide, gemini-no-guide. Even the rich kimi-with-guide has only 1 `triggers` edge for 11 trigger nodes.

**Story/canon gaps**
10. **The Amalgam absent** despite being the central antagonist (deepseek-thinking both, chatgpt-guide). No encounter node, no ambush.
11. **Deep metal shaft / railgun hole** missing (zai both, chatgpt-guide) — the CHIMERA climax location.
12. **Contradictions with canon**: Marcus alive (`state: awake`, Halloway_House) in deepseek-with-guide although the story has him killed; several place characters with no `players_in_area` entry (gemini-no-guide).

**Per-character model**
13. **`autonomy` / `simple_npc` often missing** (kimi, zai, deepseek). The engine seeds control mode from these; absence can flip a "human" to LLM or back unexpectedly.
14. **Memories as plain strings** instead of structured `{text, importance, tags}` (chatgpt-guide). The memory manager and prompt-builder expect the structured shape.
15. **`relationships` populated in graph but empty `{}`** in the `players` map (Qwen-guide) — the engine reads the `players` copy.

---

## 6. What the "correct" scenario still needs

Distilled from what all 13 got right/wrong, a passing scenario must have, all together:

1. **One source of truth in `graph.nodes`/`graph.edges`** with lowercase ids (`player_violet_parr`, `way_chem_to_hall`, `item_chemistry_lab_table`, `area_the_old_steel_mill`), and the **denormalized top-level `players`/`ways`/`areas` kept in sync** with it (every character and way represented in the same case/prefix).
2. **Fully populated `world_lore`** — not `[]` (the prompt/builders render `[general] undefined` when it's empty, which is noise in every turn).
3. **A real trigger/behavior graph** — `trigger` nodes wired via `triggers` edges to items/ways/areas, since the editor and narration rely on them (and the graph editor now supports behaviors + state machines, which none of these emit).
4. **Complete cast + antagonist + climax locations**: Amalgam node, deep shaft/railgun hole, ruined Parr front — with `current_area` and `relationships` consistent.
5. **Correct per-character fields**: `stats`, `skills`, `vitals`, `traits`, `tags`, `autonomy`, `simple_npc`, structured `memories` (not strings).
6. **No obsolete edges** (`unlock`) and **no dangling edge endpoints**.

---

## 7. Recommendation

- **Best starting point to hand-fix into a canonical scenario:** `ai_studio_code_gemini3-6-flash-with-guide.txt` (cleanest full graph) merged with `Qwen_json_...with-guide.json` (adds the Amalgam and the full cast/world_lore) and the **content depth** of `kimi_instant - with guide.json` (17 items, 11 triggers, deep shaft).
- **Before trusting any of them:** run a validation pass that checks (a) every `graph.edges[].source/target` exists in `graph.nodes`, (b) every `players`/`ways` key exists in graph and matches case/prefix, (c) no Title-Case/space/hyphen ids, (d) `world_lore` non-empty, (e) `autonomy` present on every character. These are all automated checks the generator clearly isn't doing.
- Feed the fix list in §5 back into the guide so subsequent generation runs avoid the same seven failure modes.