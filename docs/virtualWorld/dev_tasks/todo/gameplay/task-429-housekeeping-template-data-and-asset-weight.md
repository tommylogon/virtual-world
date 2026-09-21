---
type: task
status: todo
area: gameplay
priority: low
---

# task-429: Housekeeping — template data, asset weight, and the open data decisions

**Filed:** 2026-09-21  
**Relates:** task-408 (goblin scenario dedup/integrity), `world_template.json`.

Small, independent, and each one was noticed and deliberately deferred rather
than overlooked. Bundled so they are not lost.

## 1. `world_template.json` carries junk items

The boot template ships generated items with ids *and names* mangled together —
`item_bread_b4080839` named `Bread_b4080839`, `current_state: None`. They leaked
from a library-placement pass (`item_{name}_{timestamp}_{random}`). Any item in
the world can be found by a `FOOD_TAGS` search, so these make foraging tests and
searches ambiguous (they were what exposed the "identity, not id" note in
`tests/test_forage_reachability.py`).

Fix: audit the template for `_<8 hex/timestamp>` suffixed ids, either clean them
to authored ids or confirm they are intended, and check `current_state` is set.
Also worth a guard so a placement pass can never write generated ids into a
template again.

## 2. Template `mature_content`

`world_template.json` ships `mature_content: false` (the camp was flipped to true
on request). `player.py` documents that the arousal vitals only exist while the
toggle is on "so the base game never shows them", which reads as deliberate — but
the decision was never recorded. Decide: is mature off the intended default for a
new world, or should the template match the camp?

## 3. Savegames still carry the duplicate bulk

Scenario files dropped ~28% (`areas`/`rooms`/`ways`/`item_registry`) because they
are graph-only now. `_save_game` still uses `to_dict()`, so saves keep the full
projection. Deliberate so far — a savegame may be meant to be a complete snapshot
— but unrecorded. Decide and, if wanted, it's a one-line switch.

## 4. The 4.1 MB background PNG

`static/images/backgrounds/ChatGPT_Image_….png` is committed because the camp
scenario references it. At 3613×2408 it should be ~300–500 KB as JPEG or WebP.
Git history does not shrink without a rewrite, so the cheap moment is **now**,
while it is one commit deep rather than twenty.

## Acceptance

- No generated-id items in `world_template.json`; ids are authored and stable.
- A recorded decision on template `mature_content` and on savegame payload size.
- The background image re-encoded, or an explicit decision to keep it as is.

## Non-goals

- The goblin scenario's own data integrity (task-408).
- Any change to how scenarios or saves are *structured* — this is cleanup and
  decisions, not a format change.
