# Search & Forage

Searching an area is a **weighted draw over skill tables**, not a lookup of what is
lying there. What a search turns up depends on the *skill* it is made with and on the
*area* it is made in; a failed check finds nothing, a bare success mostly finds
sticks, and a strong pass delivers what was asked for. Source of truth:
`engine/foraging.py` (629 lines), tables in `data/library/foraging.json`.

Tasks: [[dev_tasks/done/gameplay/task-410-food-renewal-foraging-and-week-scale-supply|task-410]] (renewable sources) ·
[[dev_tasks/review/gameplay/task-483-search-affordance-findable-here-hints-per-area-forage-tables|task-483]] (data surface + per-area tables)

---

## The verbs are three different things

| Verb | What it does | Where |
|---|---|---|
| `search` | A **Perception** check at a hardcoded DC 12 that unhides every `hidden` item in the room. No skill tables, no spawning, no cap. | `routes/action_handlers.py:458` |
| `find <skill>` | The real forage draw — draws from the skill's table and spawns a find. | `routes/action_handlers.py:571`, calls `foraging.find_or_spawn` at `:580` |
| `find <tag>` | A *sense* verb, not a forage: lists items already in the room carrying that tag. Nothing spawns. | `routes/action_handlers.py:589-619` |
| bare `find` | The same sense verb, driven by `player.interest_tags`. | `routes/action_handlers.py:593` |

Two consequences worth stating plainly:

- **`forage` is not a verb.** `engine/autocomplete.py:219` accepts `'forage'` as a
  *prefix trigger* and offers the skill names after it, but nothing dispatches it.
  Measured live through `handle_take_action`: `forage Survival` returns
  `'Kaelen Voss forage survival.'` — the emote catch-all. `find Survival` returns
  `'You search with survival but find nothing new.'` (a bare success in the
  template forest, which is the documented outcome, not a failure).
- **`find <skill>` is case-insensitive at the gate and case-preserving in prose.**
  `is_loot_skill` lowercases (`foraging.py:183`), and `find_or_spawn` re-lowercases
  at `:429`, but the echo line prints the raw input — hence "search with survival"
  in lower case above.

`findable_here()` / `findable_hint()` (`foraging.py:530`, `:548`) are the intended
"findable here" affordance — a side-effect-free list and one-line hint of the skills
that could pay out in an area. **They have no caller.** See "Unwired" below.

---

## Where the tables live

`data/library/foraging.json` holds three keys and is authoritative; the literals in
`foraging.py:50-136` are a fallback for a missing or malformed file, so an
unpackaged run still searches (`_load_forage_data`, `:150`; the precedence at
`:163-170`).

| Key | Count | Meaning |
|---|---|---|
| `skill_tables` | 8 skills | `{tags: [...], weight: n}` per skill. Weighted **type** tags, not item ids |
| `skill_display` | 8 | The name the skill sheet knows (skills are case-sensitive there) |
| `area_skill_bonus` | 27 area tags | `area tag -> {skill: bonus}`. Tilts both the weights and the DC |

The eight skills: survival, perception, history, religion, nature, investigation,
arcana, medicine. Biome preference lives **here**, never on the items.

`engine/biomes.py` closes the loop with WorldPainter: `forage_skill_bonus()`
(`:264`) merges a biome's tags over `AREA_SKILL_BONUS`, and `_forage_vocabulary()`
(`:303`) builds the tag vocabulary the biome validator checks `resource_distribution`
entries against — a biome whose resource tags are not in the forage tables is a
validation error (`biomes.py:421`), not a silent no-op.

---

## The `forage` tag

`FORAGE_TAG = "forage"` (`foraging.py:176`) is a **mechanics** tag on the item:
"this can turn up when someone searches the wilds." It is additive — an item keeps
every other tag that is true of it.

`_pick_item` (`:378`) scores candidate library items by tag overlap with the drawn
entry, and **when any candidate carries `forage` it restricts the draw to the tagged
set**. So the tables name types (`fruit`, `tool`, `coin`, `relic`) but the pool stays
curated: without the tag, a "tool" draw could return a nail-polish kit. A library
with nothing tagged still works and falls back to the plain tag match.

Measured: **146 of the shipped library items carry `forage`** — `rg -l '"forage"' data/library/items/`
→ 146 files, spanning herbs, mushrooms, seeds, eggs, fish, game meat, pelts,
fibres, fuel and salt.

---

## The draw, step by step (`find_or_spawn`, `foraging.py:401`)

1. **Cap first.** `_cap_ok` (`:260`) reads the area's `search_finds` property
   `{day, count}`; `MAX_FINDS_PER_AREA_PER_DAY = 3` (`:40`), **shared across every
   searcher**. The day is derived from `time_ticks / minutes-per-tick` (`_day`,
   `:251`) — no wall clock. This is the anti-loot-piñata bound.
2. **Area gate.** An area yields a find only if its tags intersect
   `AREA_SKILL_BONUS` (`:426`). A bare interior with no recognised tag stays
   **barren**, so search never turns every room into a resource dispenser — unless
   the area authors `forage_tables` (below), which is explicit intent.
3. **DC.** `affinity` (the area bonus for this skill) plus up to 3 for tags already
   present in the room; `dc = max(MIN_DC=6, SEARCH_DC=10 - check_bonus)` (`:433-437`).
4. **One check.** `_search_check` (`:275`) swaps `gs.active_player` so the check
   reads the *searcher*, not whoever happens to be active. **It fails open** — with
   no skill system it returns a strong pass, so going hungry is the exception
   rather than the default.
5. **Strong vs bare.** `strong = (total - dc) >= 5` (`:446`). Strong: only entries
   satisfying `want_tags`. Bare: the skill's table **plus `JUNK_ENTRY`** — "the
   wilds are not a pantry, and an unskilled searcher mostly finds sticks" (`:318`).
6. **Weights.** `_weight` (`:360`) adds the area bonus, +1 when an area tag is also
   an entry tag, **+3 when the entry matches what the searcher needs**, and +1 per
   tag already present in the room (an old religious statue in a forest raises the
   weight of a relic).
7. **Spawn.** `_spawn_into_area` (`:598`) first looks for a **standing pool** in the
   area that yields this item and charges one unit against it (`_find_pool_for`,
   `_draw_from_pool`, `:558`/`:576`), so a forest with one berry thicket draws from
   *that thicket* instead of quietly growing a second bush. Then it hydrates a fresh
   copy and puts an `EDGE_IN` edge on the area.

The find is an ordinary library item node, so take / eat / give / ignore all work on
it with no special case.

---

## Per-area tables

An area node may carry `forage_tables`: `{skill_key: [entries]}` (`AREA_TABLES_PROPERTY`,
`:147`). Those entries are **appended** to the global table for that area
(`extra_entries` through `_candidate_entries`, `:337`), and the presence of the
property makes an otherwise unrecognised area searchable at all (`:426`).

```json
{ "tags": ["cellar"],
  "forage_tables": { "history": [ { "tags": ["antique"], "weight": 2 } ] } }
```

Adding a table entry or an area override is JSON. No shipped scenario or library
area currently authors one — `rg "forage_tables"` outside `engine/` and `tests/`
returns nothing.

---

## Notice, then search (the hidden two-step)

`notice()` (`:484`) is a Perception check that records `search_noticed` on the area
when it passes. `search_hidden()` (`:513`) requires that notice before searching —
a failed notice means **no search happens at all**, because the character never saw
there was anything to look for. A success is remembered on the area, so returning
later does not pay for the notice twice.

The division is deliberate: **Perception is the gate; the search skill is the find.**
A perceptive but untrained character notices the cache and cannot open it; a trained
but unobservant one never sees it.

---

## Regrowth is authored, not engine code

The "renewable source" pattern is [[dev_tasks/done/gameplay/task-410-food-renewal-foraging-and-week-scale-supply|task-410]],
and it is pure trigger data on the item:

```json
// data/library/items/bush_of_berries.json
"parameters": { "growth": 0 },
"triggers": [
  { "trigger_type": "on_tick",
    "condition": { "type": "parameter_reached", "key": "growth", "value": 100, "op": "lt" },
    "effect_type": "adjust_parameter",
    "effect_params": { "key": "growth", "delta": 1, "per": "minute" } },
  { "trigger_type": "on_tick",
    "conditions": [ { "type": "parameter_reached", "key": "growth", "value": 100 },
                    { "type": "contains_count", "value": 10, "op": "lt", "target": "berries" } ],
    "effects": [ { "type": "spawn_item", "params": { "item_id": "berries",
                                                     "into": "container" } },
                 { "type": "set_parameter", "params": { "key": "growth", "value": 0 } } ] }
]
```

Three decisions the task fixed:

1. **`parameters.growth`, never `uses`.** `uses` is remaining charges; depletion,
   consumption and crafting all delete the node at 0, so a 0→100 growth counter on
   `uses` would make the bush look broken and get it removed. `adjust_parameter` /
   `set_parameter` work on any node type.
2. **`per: "minute"`**, so growth measures *game* time and not tick count — a
   1-minute and a 15-minute world reach maturity at the same wall-clock minute.
3. **The plant carries no `food` tag.** Consumption does not consult tags, so a
   hungry character would eat the bush and delete it. Only the produce is food.

A standing bush is not carried and not lit, so `tick_manager._sweep_area_items`
(`:292`, task-406/416) is what fires its `on_tick` at all — once, skipping anything
the carried/equipped loop already handled.

Harvesting a standing pool is a separate, *skill-gated* verb —
`engine/items/take_drop_actions.py:288-300`. Its check **scales the yield rather
than gating the attempt**: a failure still nets one unit. Contrast the search, where
a failed check finds nothing at all.

---

## Unwired

Three things in this feature exist, are tested, and have no runtime caller.

| Symbol | Tests | Callers outside `engine/foraging.py` and `tests/` |
|---|---|---|
| `findable_here` / `findable_hint` | `tests/test_forage_tables.py:80-102` (4) | **none** |
| `notice` / `search_hidden` | `tests/test_search_skills.py:62-116` (6) | **none** |
| `forage_tables` on a shipped area | `tests/test_forage_tables.py:59-77` (2) | **no authored instance** |

Evidence (`rg "findable_hint\|findable_here" -g '!docs/**' -g '!engine/**' -g '!tests/**'`
and the same for `search_hidden`) returns **no matches**. task-483 says so itself:
*"Remaining for this task: the actual HUD display of `findable_hint`."*

What *is* wired, and to what:

| Caller | Line | What it uses |
|---|---|---|
| `routes/action_handlers.py:580` | `find <skill>` | `find_or_spawn` |
| `engine/background_simulation.py:938` | the soak tier | `find_or_spawn` + `best_skill_for` |
| `engine/autocomplete.py:222` | `find`/`forage` prefix | `SKILL_TABLES`, `SKILL_DISPLAY` |
| `engine/biomes.py:32` | biome validation | `AREA_SKILL_BONUS`, `SKILL_TABLES` |
| `engine/soak_telemetry.py:98` | trace schema | the `forage:` / `search:` reason tags |

The background tier is the heavier consumer: a hungry character whose area has no
reachable food calls `_forage_spawn` (`background_simulation.py:931`), which picks
`best_skill_for` — the searcher's best skill whose table covers what they need
(`foraging.py:296`) — and searches. That is the path the task-410 soak measured
(`tests/test_search_loot.py:168`).

---

## Tests

| File | Count | Covers |
|---|---|---|
| `tests/test_search_skills.py` | 11 | table/display coverage, `best_skill_for`, notice-then-search |
| `tests/test_search_loot.py` | 10 | the draw, junk on a bare success, strong-result delivery, `forage` curation, the area cap, an untagged interior staying barren, the soak path |
| `tests/test_forage_tables.py` | 9 | the JSON file is authoritative, missing-file fallback, per-area override, findable hints |
| `tests/test_foraging.py` | 5 | a failed forage leaves the character hungry (soak tier) |
| `tests/test_renewable_plants.py` | 4 | growth → spawn → reset, the 10-produce cap, the plant is not food |
| `tests/test_forage_reachability.py` | 9 | food on / under / behind / in a container is still found |
| `tests/test_biomes.py` | — | the shipped biome taxonomy maps to the forage vocabulary |

---

## Related docs

- [[Items Overview]] — pooled resource nodes, `harvest`, `quantity`
- [[Rooms & Areas]] — where area tags come from
- [[WorldPainter]] — biomes and the grid
- [[Tags System]] — the `forage` mechanics tag
- [[Vitals System]] — Hunger / Thirst, the drives the soak tier answers
- [[World Scopes]] — who is observed and who is backgrounded
