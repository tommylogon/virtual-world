---
type: task
status: review
area: gameplay
priority: medium
---

# task-471: Skill-driven search finds (area resource generation)

**Filed:** 2026-09-23
**Related:** task-470, task-468, task-399, task-464, task-9

## Goal

An area need not be hand-stocked to be worth searching. What a search turns up depends on the skill used (Survival -> herbs/fruit/roots/grubs, History -> old things, Religion -> relics, Perception -> scraps/tools/coins) and the area modifies both the chance and the flavour: a forest favours Survival, a ruin favours History/Religion, and an item already present (an old religious statue in a forest) raises the weight of the matching kind of find. Finds are ordinary library items spawned as fresh copies, one skill check, and a per-area daily cap so a long soak cannot turn one wood into a loot pinata.

## Acceptance

- TODO

## Progress 2026-09-23 — core landed (review)

- [x] `engine/foraging.py`: `SKILL_TABLES` (survival / perception / history /
  religion → weighted tag entries), `AREA_SKILL_BONUS` (forest/woods/shore/ruin/
  temple/road/battlefield → skill affinity, which also lowers the search DC), and
  `find_or_spawn(gs, player, area, skill=, want_tags=, rng=)` — one skill check,
  weighted entry pick, a library item by tags, spawned as a fresh copy with an
  `in` edge to the area; `forage:found` trace + log.
- [x] **Area/item modifiers**: affinity lowers the DC (floor 6); area tags that
  match an entry and any matching item already present add weight, so a relic in
  a forest favours religious/forest finds.
- [x] **Cap**: `MAX_FINDS_PER_AREA_PER_DAY` (3) tracked per area per in-game day
  on the area node, so a long soak can't farm one wood.
- [x] **Gate**: only an area with a plausible tag (forest/shore/ruin/road/…) can
  yield; a bare interior stays barren. Template areas are tagged `exterior`, so
  existing soak behaviour is unchanged.
- [x] **Wiring**: soak forage falls back to a spawn when the area holds no food
  (`BackgroundSimulation._forage_spawn`, best coverage skill via
  `best_skill_for`); the player `find <skill>` command uses it too, while
  `find <tag>` keeps the old tag listing.
- [x] 8 library item templates (`wild_berries`, `medicinal_herb`,
  `edible_root`, `fat_grub`, `scrap_iron`, `old_coin`, `dwarf_chisel`,
  `stone_idol`) so the tables draw from real content.

## Remaining

- [ ] Explicit `find <skill>` UI affordance/help text; the verb currently takes
  the skill name as its argument.
- [ ] A per-area authoring override (node property) and a JSON library surface
  for tables, instead of the code constant.
- [ ] Hints/HUD feedback for "what could be found here" so the player learns it.

## Verification

`python -m pytest tests/test_search_loot.py -q` → 6 passed; targeted
search/soak/actions regression → 289 passed.
