---
type: task
status: inprogress
area: gameplay
priority: medium
---

# task-731: Activities are entered through their object, not a bare verb (bed, chair, bath; actor-chosen duration; dreaming)

**Filed:** 2026-10-07
**Related:** task-716, task-726, task-703, task-725

## Goal

Make object interaction the entry point for activities: use <bed> to sleep, use <chair> to rest, use <bath> to bathe, via an on_use trigger to the start_activity effect. Delete the bare fish verb (the angling rod already does it) and demote the rest/sleep/bathe/sit/lie verbs to an inferior fallback so a character with no furniture can still rest anywhere. Add an actor-chosen duration channel so 'use bed for 6 hours' works, keep 'until rested' via completion:vital_full, and ground background_simulation NPC sleep in a real bed when one is present.

## Grounding (measured 2026-10-07)

Activities are data-driven: 16 defs in `data/library/activities/` (`bathing`,
`drinking`, `eating`, `fishing`, `foraging`, `lying_down`, `meditating`,
`recreating`, `recuperating`, `relieving`, `resting`, `sitting`, `sleeping`,
`waiting`, `washing`, `working`). Each carries `condition`, `regen`,
`blocks_turns`, `interruptible`, `preposition`, `no_duration_label`,
`tick.actions`, `completion`.

The object path **already exists and works**: `data/library/items/angling_rod.json`
has `on_use_on` `target_tag: water` → effect `start_activity`
`{ activity_type: "fishing", target_item: "{target_name}", duration_minutes: 120 }`,
handled by `engine/effect_handlers/activities.py:handle_start_activity`.
`activity_description` already renders `target_item` + `preposition`
("sleeping **on** the bed"). So this is not a new mechanism.

Three start paths exist today:

1. bare verbs — `routes/action_handlers.py:369` (`fish`) and `:372`
   (`rest/sleep/wait/meditate/bathe/sit/lie`).
2. object → `start_activity` trigger (the rod; the path wanted).
3. `engine/background_simulation.py` calls `activities.start_activity(..., "sleeping")`
   directly — NPC drift, no object.

No furniture exists in `data/library/items` (no bed / chair / bath / basin).

## Decision (user, 2026-10-07)

- Objects are the **entry point**; a bare fallback is **kept** so a character with
  no furniture can still rest anywhere (visibly worse — "you sleep fitfully on
  the ground"). Objects-only would turn "no bed" into "cannot sleep".
- `wait` stays a bare verb — it is a true self-action with no object.
- Actor-chosen duration **is wanted**: both humans and agents should say
  "do activity X for duration Y".
- Sleeping should ground in a real object when one is present (bedroll, tent,
  cot, bed); `background_simulation` NPC sleep should bind to a bed in the area.

## Work

- Author furniture components (bed, cot, bedroll, tent, chair, stool, bath,
  basin) with `actions: use` + `on_use → start_activity`. One object may offer
  more than one activity (a bed: sleep or lie_down; a chair: sit or rest).
- Delete `fish` (line 369) — the rod already covers it.
- Demote the rest/sleep/bathe/sit/lie block (line 372) to the fallback.
- Add an **actor-chosen duration channel** on `use` (`use_on` carries
  `text`/`amount`, task-433/196, but no time). This is the one engine change.
- `background_simulation`: pick a bed in the area when sleeping, else fallback.
- Agents already have the `use` verb, so they get activities for free — remove
  any need for bare `rest`/`sleep` in the agent vocabulary
  (`static/js/agent/action-normalizer.ts` VALID_VERBS).

## Dreaming (companion feature)

While sleeping, a random chance to fire a dream: one LLM call per character per
X hours of sleep, drawn from `lived_log` / recent memories, written as a memory;
plus a random wake chance. `tick.actions` is the natural hook (fishing already
uses `sample_biome_resource`), but the LLM call is driven client-side by the
agent engine, not pure-Python `tick_turn` — decide whether the dream call rides
the agent engine's background loop or a new hook. Needs a cost cap (one call per
character per X hours).

## Open questions

- **Furniture occupancy in the graph.** `EDGE_IN` is item/character → room/
  container; `EDGE_ON` is **item** → surface; `EDGE_AT` is item → area/object.
  A character today only has `in` → area. "Character on the bed" is not a
  defined relation, and a second `in` edge collides with the area `in` edge
  (`area_of`). The activity already records `target_item`. Decide whether to add
  an explicit occupancy relation or leave it on the activity only — do not
  overload `in` silently.
- `relieving` has no object authored either; same treatment.

## Acceptance

- [ ] `use bed` starts `sleeping` with `target_item` the bed; the narration reads
      "You start sleeping on the bed."
- [ ] `use bed for 6 hours` sets a duration; omitting it runs until
      `vital_full Energy`.
- [ ] a character with no furniture can still rest/sleep via the fallback.
- [ ] `fish` is gone; fishing works only via the rod on water.
- [ ] NPC background sleep uses a bed when one is in the area.
- [ ] Agents get activities through `use`; no bare `rest`/`sleep` verb needed.
- [ ] `npm run build:ts` and `node tools/unit/run.cjs` pass; a targeted engine
      test proves `on_use → start_activity` sets the activity and target.
- [ ] Live: use a bed in the goblin camp and observe the activity, plus a bad
      `use` on a non-furniture item doing nothing.

## Landed (2026-10-07)

- Furniture templates wired to activities via `on_use → start_activity`:
  `bed`, `cot`, `bedroll` (added the `use` action) → `sleeping`;
  `chair_stool` (added `use`) → `resting`; `large_wooden_bathtub` → `bathing`;
  `wash_basin` → `washing`. Each targets `{item_name}` (the trigger context
  already provides it, `engine/triggers/execution.py:389`). The tub/basin legacy
  one-shot `adjust_vital` on_use effects were replaced by the activity.
- Deleted the bare `fish` command (`routes/action_handlers.py`); fishing now
  works only via the angling rod on water.
- The rest/sleep/wait/… block stays as the fallback (it always was).

## Remaining

- **Actor-chosen duration**: `use bed for 6 hours`. Needs a duration channel on
  `use` (parse `for N hours/minutes` → context `duration_minutes`) and
  `handle_start_activity` to prefer `context["duration_minutes"]` over the
  trigger's static param. The rod/trigger path already accepts `duration_minutes`.
- **NPC sleep grounding**: `background_simulation` still calls `start_activity`
  directly; bind it to a bed node in the area when present.
- **Dreaming**: one LLM call per character per X hours of sleep, drawn from
  `lived_log`/recent memories, plus a random wake chance.
- **Tent** and the remaining bed/chair/basin variants (many library items) still
  lack the trigger.
- **Bed occupancy** (`at` → `on`/`in`) — the open question above.
