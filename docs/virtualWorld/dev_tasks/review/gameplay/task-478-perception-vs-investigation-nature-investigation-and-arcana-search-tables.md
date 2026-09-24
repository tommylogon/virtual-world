---
type: task
status: review
area: gameplay
priority: medium
---

# task-478: Perception vs Investigation; Nature, Investigation and Arcana search tables

**Filed:** 2026-09-23
**Related:** task-471, task-472, task-474

## Goal

Separate noticing from searching: Perception spots something easy to miss, Investigation works out where to look and what it means (a two-step notice-then-search). Add search loot tables and forage-tagged content for Nature (reagents, tracks, safe plants), Investigation (documents, mechanisms, hidden caches) and Arcana (arcane items, anomalies), plus a small Medicine table for recognising a useful plant, so the skill list has content beyond Survival/Perception/History/Religion.

## Acceptance

- [ ] New search tables and display names exist for **Nature, Investigation,
  Arcana and Medicine**, each naming real skills and drawing on the item-tag
  vocabulary that already exists (no new library content required for the tables
  to work).
- [ ] Area tags raise those skills in `AREA_SKILL_BONUS`: forest → Nature/
  Medicine, ruin → Investigation/Arcana, temple/shrine → Arcana, road/
  battlefield → Investigation. **No new area tags are introduced**, so the
  existing "can this area yield a find" gate is unchanged.
- [ ] **Two-step notice-then-search.** `notice()` (Perception) spots that there
  is something worth searching for and remembers it on the area;
  `find_or_spawn(require_notice=True)` / `search_hidden()` find nothing without a
  successful notice — even on an excellent roll.
- [ ] A failed notice means no search happens at all (the character walks past);
  a success is remembered, so a later search does not pay for the notice again.
- [ ] Plain, non-hidden searches are unchanged; adding a table entry or area
  bonus is data.
- [ ] Deterministic: no RNG outside the seeded pick, no LLM.

## Progress — 2026-09-24

Implemented and tested; moving to review.

- **`engine/foraging.py`** — `SKILL_TABLES` + `SKILL_DISPLAY` gain `nature`,
  `investigation`, `arcana`, `medicine` (reusing existing tags: plant/herb/root/
  bug, tool/metal/scrap/antique, relic/idol, herb/plant). `AREA_SKILL_BONUS`
  raises them on the existing area tags. New `NOTICE_PROPERTY`, `_area_noticed`,
  `notice()` and `search_hidden()`, plus a `require_notice` guard on
  `find_or_spawn`. Perception is the gate; the search skill is the find.
- **`tests/test_search_skills.py`** (11) — tables/display/area bonuses, best
  skill for a plant, notice marks the area only on success and not twice, a
  hidden search finds nothing without a notice even on a great roll, a failed
  notice means no search, notice-then-search lands a real node in the area, and
  plain searches are not gated.

Remaining for this task: the richer content pass the task names — documents,
mechanisms, hidden caches and arcane items/anomalies as their own library
entries/tags (today the tables reuse the existing tag vocabulary), which is a
data-authoring follow-up rather than a mechanic.
