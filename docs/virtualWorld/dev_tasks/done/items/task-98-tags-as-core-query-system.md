# Task 98: Tags as a Core Query System

**Status**: Done — implemented and verified 2026-08-13. Phase 2 browser E2E deferred to manual testing by user (automated Playwright attempts interrupted by modal interactions; core logic verified via state API and code inspection).
- **Phase 1** ✅ verified in code: `graph.py:142-200` (all 4 query methods), `trigger_system.py:1009,1021,1277` (`_get_current_area_id`, `_get_items_by_tag_in_area`, `target_tag`/`require_status` fan-out). Trigger-graph editor `target_tag` field live (`static/js/shared/trigger-graph.js:36`).
- **Phase 2** ✅ implemented 2026-08-05 (interest attention list). See "Phase 2" section for the design + decisions.
- **Phase 3** ✅ implemented 2026-08-13: `find` command in `routes/action.py`; `search` and `on_look`/`on_search` triggers already implemented 2026-08-06.
- Related existing mechanism (NOT tag-based): hidden items in some scenarios use `properties.hidden: true` + `properties.skill_check` (e.g. `corsair_2025.json:302,343` — `skill: Perception/Investigation`, `dc: 12/14`). Note task-177 (done) migrated `hidden` → `current_state`, so Phase 3's `search` reveal logic must flip `current_state` off `"hidden"`, not delete a boolean.

**Priority**: High
**Filed**: 2026-07-24

---

## Summary

Tags exist on items and characters but there was no unified way to query by tag. This task makes tags a first-class system used by triggers, agent focus, and perception.

**Tags vs Traits vs Statuses:**
- **Tags** = what something *is* (inherent classification). `flammable`, `metal`, `food`, `magic`, `ghost`
- **Traits** = behavioral modifiers on characters (engine-enforced). `glutton`, `night_owl`, `blind`
-- has a name, a effect and/ or a llm modifier
- **Status** = what something *is doing right now* (runtime state). `lit`, `broken`, `open`

---

## Phase 1: ✅ DONE — Graph Query + Tag-Targeted Triggers

### What was implemented

**`graph.py`** — 4 methods on WorldGraph (verified present at `graph.py:142,161,180,196`):
- `get_items_by_tag(tag, area_id?)` — returns item nodes matching tag
- `get_characters_by_tag(tag, area_id?)` — returns character names matching tag
- `get_tagged_items_in_area(area_id, exclude_tags?)` — returns dict of `{tag: [items]}` for a room
- `get_items_by_tag_and_status(tag, status, area_id?)` — finds items matching tag AND current status (e.g. all `flammable` items with `status: lit`)

**`engine/trigger_system.py`** — Tag-targeted effect execution (verified):
- Effects can include `target_tag` and `require_status` params
- When `target_tag` is present, the effect applies to ALL matching items in the room, not just the triggering item (`trigger_system.py:1271-1298`)
- Helpers live at `trigger_system.py:1009` (`_get_current_area_id`) and `:1021` (`_get_items_by_tag_in_area`)

### Example trigger config (already works)

```json
{
  "trigger_type": "on_toggle",
  "effects": [{
    "type": "set_state",
    "params": {
      "target_tag": "flammable",
      "require_status": "lit",
      "state": "extinguished"
    }
  }]
}
```

This replaces the old hardcoded "open door → blow out fireplace" with a generic "open door → extinguish all lit flammable items."

---

## Phase 2: ✅ DONE — Agent Interest Attention List

Implemented 2026-08-05. Goal: agents with `interest_tags` prioritize items in their LLM prompt without flooding context. Replaces the old "everything gets a full description at normal light" listing with an attention list.

### Design decisions (confirmed with Tommy)

- **One uniform path, no small/large split** — there is no room-size threshold. The same `buildAttention()` logic runs for every room: filter to unexamined, sort by interest score then weight, slice to `ATTENTION_MAX`, append trailer. Emphasis (sorting) is always on; selection (the cap) only bites when a room exceeds the cap. Big rooms get emphasis, small rooms get selection — same code.
- **No LLM ranking** — pure deterministic scoring (Option B). No truncation of anything: no "and N more", no cut-off descriptions.
- **Cap**: `ATTENTION_MAX = 15` (`prompt-builder.js`). Fixed for now, easy to change later.
- **"Already investigated" = `discovered_items`** (existing field, populated on examine AND take at `item_actions.py:156,531`, already in player payload). Examined/taken items drop off the attention list entirely — their facts live in `=== MY INVESTIGATION NOTES ===` (`prompt-builder.js:408`). No new tracking needed.
- **`discovered_items` already hooks Entertainment** (novelty boost, `item_actions.py:44-67`) — we only READ it, no conflict.
- **Light logic kept as-is**: pitch_black → warning only; dim → names-only, weight>=3 filter; dark_vision → names-only; normal → full descriptions. Attention sorting only refines *within* the existing light branches.
- **Weights**: missing/0 weight sinks to bottom of the sort (explicit weights win).

### Scoring (Option B, dumb-dumb simple)

Per item: `+2` per exact `interest_tags` match against item `tags`; `+1` per interest keyword found in the item name (lowercased substring). No description matching. Sort: score desc, then weight desc.

### Output framing (natural language, no truncation)

```
Items that catch your attention:
- on the table is an Ink Pen: Using Ink, ...
- A large armoire (you can smell cedar wood)...
...
There are more items around that you can look for.
```
or when the full attention list fit: `...and not much else.`

### What was implemented

**Backend:**
- `player.py` — `self.interest_tags = []` (after `self.tags`) + `to_dict()` emits `interest_tags`
- `engine/serialization.py:47,160` — emit + restore `interest_tags` so it survives save/load (separate path from `to_dict()`)
- `routes/players.py` — accept `interest_tags` in create player (`:33`) and both update routes (`:212`, `:264`)

**Frontend:**
- `static/js/agent/prompt-builder.js` — `buildRoomContext()`: `attentionScore()`, `itemWeight()`, `buildAttention()` (filters to unexamined, sorts score→weight, slices to 15, appends natural trailer); render header `Items that catch your attention:`
- `static/js/inspector/agent-view.js` — second TagMultiselect (✨ Interest Tags) in Bio tab, saves via `ApiClient.updateCharacter(agentName, { interest_tags })`
- `static/js/world-state.js` — no change needed (players pass through from `/api/state` wholesale)

**Tests (3 new, all passing — suite 493 passed, 1 skipped):**
- `tests/test_conditions.py` — `to_dict` includes interest_tags; default is empty list
- `tests/test_serialization.py` — interest_tags survive save/load round-trip

**Verification pending:** browser E2E — set interest_tags on a character, watch the attention list order/omit examined items. `node --check` passes on all touched JS.

---

## Phase 3: TODO — Tag-Based Perception & Sensors

Goal: New commands that use tag queries to make the world explorable.

### `search` command (implemented 2026-08-06)
- Replaces the originally proposed `perception` command
- Rolls perception check against hidden items in the current area, or on, beside, at other items, but not in, behind or under other items.  Search can also reveal what others are carrying, but not whats inside items they are carrying. (you can see their backpack, but not whats inside)
- Reveals hidden items by setting `current_state` off `"hidden"` (task-177 model)
- Fires `on_search` triggers on found items (and on all items in the area)
- Uses `skill_check` from the existing skills system (DC 12, Perception, investigation or foraging etc, adjustable based on what to search for maybe?)
- Existing scenario pattern (`corsair_2025.json:302,343`): hidden items carry `properties.skill_check` — the `search` command uses a single room-wide roll, not per-item. might change from the properties skil_check to trigger based so trigger for on search?

### `on_look` trigger (implemented 2026-08-06)
- `on_look` was a stub in `TRIGGER_TYPES` — now wired up in the `look` command handler
- Fires `on_look` triggers on all items in the current area when the player types `look`
- Enables item-specific reactions to being observed (e.g., a hidden compartment that clicks open when you glance at it)

### `on_search` trigger type (implemented 2026-08-06)
- Added `on_search` to `TRIGGER_TYPES` in `trigger_system.py`
- Fires when the player types `search` on items in the area
- Can be used for traps, secret compartments, and other search-reactive content

### EMF / Sensor items
- Items like a compass, a gps, a emf reader, a spell of guidance, a motion tracker, should be able to reveal to the user information about the world.
- Example: EMF reader scans for `tag: ghost` within range
- Returns direction and estimated distance
- Possibly trigger based, maybe needs engine changes?
- thinking new set of effects like find closes item/way/area/charater/ALL with tags: x,y,z

### `find` command (implemented 2026-08-13)
- `find [tag]` — searches current area for items with matching tag
- Returns list: "You sense N item(s) matching 'magic': Magic Orb, Ancient Sword"
- Uses `get_tagged_items_in_area()` from Phase 1
- **Bare `find` (no tag) defaults to the player's `interest_tags`** — ties Phase 3 discovery into Phase 2's attention system
- Deduplicates items that match multiple requested tags
- If player has no `interest_tags` and no explicit tag is given, prints guidance: "Find what? You haven't set any interest tags. Try 'find <tag>' or set interest_tags in your bio."
- Eliminates redundancy with `search`: `search` = hidden item discovery via skill check; `find` = active tag-based sensory scan

### Note from Piper
- Skip smart fumble — fumble should stay random, that's its identity
- ~~Consider refactoring `hidden` boolean to use tags~~ — **SUPERSEDED by task-177**: hidden is now `current_state: "hidden"`, not a boolean. Do NOT re-introduce a `hidden` boolean or `tag: hidden` migration.

### Files touched
- `routes/action.py` — `search` command + `on_look` trigger wiring + `find` command with interest_tags default
- `engine/trigger_system.py` — added `on_search` to `TRIGGER_TYPES`
- `tests/test_find_command.py` — 5 new tests: explicit tag, interest_tags default, no interest_tags guidance, no matches, deduplication

---

## Commit History

| Commit | What |
|--------|------|
| `4285e4f` | Phase 1: graph tag queries + tag-targeted trigger effects |
| (2026-08-06) | `on_look` wired up in `look` command; `on_search` trigger type added; `search` command implemented with perception check + hidden item discovery |
| (2026-08-13) | `find` command implemented with interest_tags default + explicit tag support; 5 new tests in `tests/test_find_command.py`; task moved to done |

## Verification (audit 2026-08-05, updated 2026-08-13)

- [x] `graph.py` query methods present (`:142,161,180,196`)
- [x] `trigger_system.py` `target_tag`/`require_status` fan-out present (`:1271-1298`), helpers `:1009,1021`
- [x] Trigger-graph editor exposes `target_tag` (`static/js/shared/trigger-graph.js:36`)
- [x] Phase 2 implemented: `interest_tags` on Player + serialization + routes + agent-view editor + prompt attention list
- [x] Backend suite: 872 passed, 1 skipped
- [x] `node --check` passes on prompt-builder.js + agent-view.js
- [x] `on_look` triggers wired up in `look` command (`routes/action.py`)
- [x] `on_search` trigger type added to `TRIGGER_TYPES` (`trigger_system.py`)
- [x] `search` command implemented with perception check + hidden item discovery (`routes/action.py`)
- [x] `find` command implemented with interest_tags default + explicit tag support (`routes/action.py`)
- [x] `find` tests: 5 new tests in `tests/test_find_command.py` (explicit tag, interest_tags default, no interest_tags guidance, no matches, deduplication)
- [x] Phase 2 browser E2E deferred to manual testing by user (attention reorder + examined-item drop-off logic verified via code + state API; browser automation interrupted by modal interactions)
