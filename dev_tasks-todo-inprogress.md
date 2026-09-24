# todo
(95 files)

---

## todo/bugs/bug-28-conversation-echo-strips-apostrophes-and-case.md

# Bug 28 — === CONVERSATION === echoes characters' own speech mangled (apostrophes stripped, lowercased)

**Status**: Todo — investigated 2026-09-22, not reproducible from current code.
Needs a live repro before any fix; likely obsolete after the conversation-context
refactor.

## Found

Taco Bell session, decide-phase prompt (`=== CONVERSATION ===` block):

```
You recently said: "fun?? me?? that s— okay that s so nice of you to say
and i m going to be normal about it, watch me be normal..."
```

The original speech event (same log, tick 19) was:

```
"fun?? me?? that's— okay that's so nice of you to say and I'm going to be
normal about it..."
```

So somewhere between the speech event store and prompt-building, `'` is
removed as whitespace ("that's" → "that s", "I'm" → "i m") and the line is
lowercased.

Suspect: the anti-repeat conversation-history builder in the JS agent side
(`static/js/agent/` — likely context-sections / memory-context area) or a tag/
sanitizer applied to stored turn_events server-side. Trace where the
conversation section text is sourced.

## Impact

- ANTI-REPEAT instruction tells the model not to repeat lines it already
  said — but the reference lines are corrupted versions of its own words.
- Voice degradation leaks back: models sometimes mirror the corrupted forms.
- Same sanitizer probably touches other logged text (check WITNESSED rendering
  for identical mangling).

## Fix sketch

Locate the strip/lowercase pass; keep lowercasing decisions only where they're
intentional (speaker-name prefixing), preserve apostrophes in quoted speech.
Add a unit test: store `I'm — that's`, build conversation section, assert
apostrophes survive.

## Verify

New play session, speak a line containing apostrophes + capitals → next
decide-phase CONVERSATION block matches the spoken text verbatim.

## Investigation — 2026-09-22 (code trace, no repro)

Traced the whole path and found **no transform that strips apostrophes or
lowercases**:

- `engine/speech.py:207-215` builds the hearing event with `"text": speech_text`
  verbatim; `:272` copies `dict(event)` into each listener's `recent_hearing`.
- `static/js/agent/prompt-builder/conversation-context.js:117-131`
  (`ownRecentSpeech`) only trims + dedupes (`toLowerCase` is used solely as the
  dedupe key, never written back).
- Involuntary speech (`static/js/agent/involuntary.js`) only stutters the first
  letter or splices `*hic*` fragments — it does not lowercase or strip `'`.

So the mangled text in the report must have been the text actually broadcast at
that tick, not a corruption introduced while building the prompt. Two candidate
explanations: (a) the refactor since 2026-08-27 removed the old builder that did
this, making the bug obsolete; (b) the model emitted the mangled line itself and
the "original" quoted in the report came from a different source.

**Related oddity:** the same taco_bell log shows a *different* corruption shape —
`please don't` → `pleas edont`, `normal` → `cnormal` (bug-29's local line). That
is letter scrambling, not apostrophe/lowercase normalisation, and no such pass
exists in the code either. If either corruption is still live, capture the raw
`/api/action` request body and the `recent_hearing` entry side by side — that
separates an upstream text bug from a prompt-builder bug.




---

## todo/bugs/bug-29-witnessed-speech-double-attribution.md

# Bug 29 — Same witnessed speech appears twice with different attributions

**Status**: Todo — investigated 2026-09-22. The filed evidence does **not** show
duplication (the two lines are different utterances), so this is most likely a
false alarm. Keep open only pending a repro that pins a single event id twice.

## Found

Taco Bell session. Jake's opening compliment was said ONCE (tick 4). In a
later turn's `=== WITNESSED ===` it appears two ways simultaneously:

```
[the man → to you] said: "pleas edont try to be cnormal, i like your whole chaos thing..."
[the man] jake halloway he winks as he answers her.
[Heard → to you] a man's voice said: "so miki, you know you are really fun to hang out with, right?"
```

Line 1 is the NEW unacknowledged line (turn-local), line 3 is the OLDER line
rendered through the stranger/anonymized path ("a man's voice") rather than
"[the man]". Two candidates:

a) Deliberate: an unanswered direct address lingers one extra turn so the ball
   stays visibly in the character's court — but then attribution flipping
   between "[the man]" and "[Heard → to you]" between renders of the SAME
   event is inconsistent.
b) Duplicate posting: the speech got recorded into both this-turn events and a
   "pending conversation" carry-over list.

## Investigation — 2026-09-22 (code trace)

`room-context.js` builds WITNESSED from two separate sources and dedupes them:

- local `turn_events` (same area, other actors) → `witnessedLines`,
- `player.recent_hearing` → `heardSpeech`, filtered by a `seenSpeechKeys` set
  keyed `${speaker}|${text.toLowerCase()}` and a contains-match against local
  narration (`room-context.js:603-693`).

The two lines in the repro have **different text** ("...i like your whole chaos
thing" vs "...you are really fun to hang out with, right?"), so they are two
distinct utterances by the same speaker, not one event rendered twice. Different
attribution per source (local event → `[the man]`; `recent_hearing` → `[Heard
→ to you] a man's voice`) is expected behaviour.

**Verdict:** the "double attribution" premise is unproven. To make this a real
bug we need a repro where the *same* line (ideally same tick) appears under two
attributions; the dedupe already keys on speaker+text, so the gap would be
speaker-label instability (e.g. "the man" vs "jake halloway" vs "a man's voice"
for one speaker), not duplicate posting.

## Also noticed

Line 1 shows the letter-scrambling corruption from bug-28's log
("pleas edont", "cnormal"); same unexplained source, tracked there.

## Why investigate

If (b), every directed-but-unanswered line double-charges prompt attention and
can nudge models into answering stale content. If (a), we should at least keep
attribution stable for the same event across turns.

## Action

Trace how WITNESSED entries are built per turn (room_perception /
scene_snapshot + client context-sections): find where an event can enter twice,
or confirm the carry-over design and document it. Then either dedupe by event
id or pin one attribution form for carried-over balls.

## Verify

Two-agent room: A says X to B; B's next TWO prompts contain exactly one entry
for X each turn, attributed identically both times.




---

## todo/bugs/bug-40-save-list-renders-auto-and-version-badges-as-literal-html.md

---
type: bug
status: todo
area: bugs
priority: high
---

# bug-40: Save list renders AUTO and version badges as literal HTML

**Filed:** 2026-09-22
**Related:** task-365

## Symptom

Reported from a screenshot of the Save / Load Game modal. The autosave row's title
rendered as raw markup instead of a badge:

```
<span style="background:var(--accent,#4a9eff);color:#fff;border-radius:3px;padding:1px 5px;font-size:9px;margin-right:5px;"> AUTO </span>Autosave<span style="font-size:9px;color:var(--text-muted);margin-left:4px;">v1.3.0</span>
```

Every row also showed its version tag as the same literal `<span style="font-size:9px;...">v1.3.0</span>`
text. The storage is fine — `save.name` is `Autosave` and the metadata is correct; only
the rendering is wrong.

## Root cause

`static/js/ui/saveload-view.js:462-471` builds `badge` and `versionBadge` as **HTML
strings**, then interpolates them into a Lit template:

```js
var badge = isAuto
    ? '<span style="...">AUTO</span>'
    : '';
...
<strong>${badge}${save.name || save.filename}</strong>${versionBadge}
```

Those interpolations are Lit **text** bindings, so Lit escapes the markup and the user
sees it verbatim. `save.name` and `save.filename` are also text-bound, which is correct
and should stay escaped.

## Fix

Preferred: stop pre-building markup as strings. Emit the badges as real elements in the
template (e.g. a conditional badged span before the name, a small muted span after it),
so the row no longer depends on an escaping opt-in.

If the minimal change is wanted first, wrap the two values in the escaping escape hatch
already used elsewhere in the repo — `window.Lit.unsafeHTML(badge)` /
`window.Lit.unsafeHTML(versionBadge)` (precedent: `static/js/event-stream.js:493`).
Do not route `save.name`/`save.filename` through `unsafeHTML`; those are user text.

Whichever path is taken, the extracted row template from task-456 is the natural home
for it.

## Acceptance

- [ ] The autosave row shows a styled `AUTO` badge, not raw `<span ...>` text.
- [ ] Every row shows `v<version>` as a muted badge, not raw markup.
- [ ] A save whose display name contains `<`, `>`, `&`, or a quote renders those
      characters literally (name stays escaped).
- [ ] No badge markup is visible in the rendered list for any row.

## Files

- `static/js/ui/saveload-view.js` — list template, badge construction (lines ~462-471)



---

## todo/bugs/bug-41-loading-a-savegame-keeps-the-previous-scenario-source-so-commit-can-write-into-the-wrong-file.md

---
type: bug
status: todo
area: bugs
priority: high
---

# bug-41: Loading a savegame keeps the previous scenario source so Commit can write into the wrong file

**Filed:** 2026-09-22
**Related:** task-365, task-368

## Symptom

Load savegame **B** while scenario **A** is open. The world contents become B, but the
save/load model is now internally inconsistent:

- `world._scenario_source` still points at scenario A's file.
- `world._scenario_name` is overwritten from B's payload.
- The scenario chip (task-367) and `GET /api/scenario/status` therefore report one name
  while the commit target is a different scenario.
- `POST /api/scenario/commit` (or an editor "Commit Scenario") then writes **B's
  runtime state** into **A's scenario file**, destroying A's authored content.
- `_edit_seq`/`_commit_seq` are not synced, so the chip's dirty dot is unreliable.
- The boot autosave slot is not refreshed, so a server restart can restore pre-load
  state.

## Root cause

`POST /api/load-game/<filename>` (`routes/saveload.py:331-344`) only does
`_push_undo_snapshot` + `app.world.load_from_dict(data)`.

`load_from_dict` (`engine/serialization.py:440-450`) sets `_scenario_name` from the
payload but never touches `_scenario_source`; the attribute is only changed by
`set_scenario_source` (`virtual_world_engine.py:781-793`).

Compare the savegame branch of `POST /api/load` (`routes/saveload.py:92-118`), which
deliberately sets `app.world._scenario_source = None` when `_save_metadata` is present,
and syncs `_commit_seq`. That route got the semantics right; the dedicated load-game
route did not, and the two have drifted apart.

## Fix

Extract one helper (e.g. `_adopt_loaded_world(app, data)`) that both routes call after
`load_from_dict`, so the two paths cannot diverge again. A savegame is a runtime
snapshot, not a scenario source, so the load-game path should:

1. Clear `world._scenario_source = None` (do not inherit the previously open scenario).
2. Set `world._scenario_name` from the save payload, and do not imply a writable
   source.
3. Set `world._commit_seq = getattr(world, '_edit_seq', 0)`.
4. Persist the autosave slot (`save_autosave`) so a restart matches the loaded state,
   unless `TESTING`.

Keep `/api/load`'s existing `persist:true` scenario-load branch unchanged.

## Acceptance

- [ ] Load a savegame while a scenario is open: `_scenario_source` is `None` and the
      chip reflects the loaded world, not the stale scenario.
- [ ] With a stale source previously attached, Commit after a savegame load cannot
      overwrite any scenario file.
- [ ] `_commit_seq == _edit_seq` after load, so the dirty dot starts clean.
- [ ] Restarting the server after a savegame load restores the loaded state.
- [ ] `POST /api/load` with a `_save_metadata` payload keeps its current behavior
      (source cleared), and the `persist:true` scenario-load branch is untouched.

## Files

- `routes/saveload.py` — `load_game` (331-344), `load_world` (75-124), new shared helper
- `engine/serialization.py` — `load_from_dict` name handling (440-450)
- `tests/test_saveload.py` — regression coverage for the load-game path



---

## todo/bugs/bug-43-save-filenames-collide-and-clobber-and-non-ascii-names-are-stripped.md

---
type: bug
status: todo
area: bugs
priority: medium
---

# bug-43: Save filenames collide and clobber, and non-ASCII names are stripped

**Filed:** 2026-09-22
**Related:** bug-31

## Symptom

Two data-loss / nameless-file problems in save filename generation:

1. **Collision clobbers.** `_save_game` names a new save
   `<safe_name>_YYYYMMDD_HHMMSS.json` with a second-resolution timestamp and no
   uniqueness guard. Saving twice with the same name inside the same second writes the
   second state over the first file with no warning. The current `saves/` list already
   holds several distinct runs all named `test save`, so the pattern is real.
2. **Non-ASCII stripped.** The sanitizer
   `''.join(c if c.isalnum() or c in ' _-' else '_' for c in name)` replaces every
   character outside ASCII alphanumerics/space/underscore/hyphen with `_`. A name like
   `Ærø kysten` or `Draghál` loses its letters — ids/filenames become rows of
   underscores. `str.isalnum()` is Unicode-aware, so the filter is stricter than it
   needs to be for a filesystem name.

Note: `bug-31` covers path *validation* (traversal). This is filename *generation*.

## Root cause

- `routes/helpers.py:293` — sanitizer drops non-ASCII letters.
- `routes/helpers.py:310` — `filename = f"{safe_name}_{ts}.json"`, no collision check.
- Same sanitizer is duplicated in the rename route (`routes/saveload.py:312`), the
  scenario-name route (`saveload.py:793`), and the scenario path helper
  (`saveload.py:638`), so a fix must be applied consistently or the sites will drift.

## Fix

1. Resolve a free filename: if the target exists, append a numeric/disambiguating
   suffix (`..._2`, `..._3`) — never silently overwrite a different save. Slot
   overwrites (`slot=` / autosave) stay the one intentional in-place overwrite.
2. Normalize names (NFKD) and keep Unicode letters/digits, folding only characters
   that are genuinely unsafe on Windows (`<>:"/\|?*`, control chars). Fall back to a
   stable placeholder only if the result is empty.
3. Factor the sanitizer into one shared helper so `_save_game`, rename, and scenario
   naming use the same rules.

## Acceptance

- [ ] Saving two different states with the same name in the same second yields two
      files; neither overwrites the other.
- [ ] A save named with non-ASCII letters keeps those letters in the filename (or at
      least does not become all underscores), and the save still loads.
- [ ] Overwriting an existing slot via 💾 still replaces that same file in place.
- [ ] Path traversal remains rejected (`_safe_save_path`); add cases for the new
      unicode/normalization path.

## Files

- `routes/helpers.py` — `_save_game` sanitizer + filename (282-326)
- `routes/saveload.py` — rename sanitizer (312), scenario name (793), `_safe_scenario_name` (638)
- `tests/test_saveload.py` — collision and unicode coverage



---

## todo/bugs/bug-44-edge-in-is-inverted-for-authored-container-contents.md

---
type: bug
status: todo
area: bugs
priority: medium
---

# bug-44: EDGE_IN is inverted for authored container contents

**Filed:** 2026-09-23
**Related:** task-485

## Goal

Container contents authored in the item library land as container -> contained (item_Backpack -> item_Ink), but EDGE_IN is canonically contained -> container (place_actions.py:79, take_drop_actions.py:685, activities.py:505) and every reader looks up get_edges_for_target(container, EDGE_IN) (equipment.py:113, item_actions.py:141, matching.py:304, activities.py:466/541, item_reach.py:148). Autosave has 21 such inverted item->item edges (Backpack -> Ink/Book/Oil/..., grandfather_clock -> brass_key, medicine_cabinet -> antiseptic/bandages), so those contents are invisible to take/examine/search/lighting/reach. Fix the authoring path (or migrate the saves) so the item is the source; the graph layout works either way because it resolves by depth.

## Acceptance

- TODO



---

## todo/characters/task-214-npc-perception.md

---
group: Pleasure System
---

# NPC Perception & Reaction Framework

**Filed**: 2026-08-11
**Priority**: Low
**Status**: Todo

---

## Problem

NPCs can't mechanically "notice" another character's state (hard nipples, blushing, arousal) or react to it (disapprove, approach, comment). Perception is currently LLM-flavor only.

## Design

- **Verified gap:** `engine/npc_behaviors.py:23` `process_npcs_on_combat()` is a stub (`pass`). Simple NPCs get `process_simple_npcs()` on tick; the reaction framework is genuinely new.
- `_calculate_perception_difficulty(npc, player, condition)` — base DC 10, modified by NPC traits (observant/oblivious), ambient light (`engine/lighting.py` `get_ambient_light`, verified), distance, and outer clothing coverage/opacity of the target.
- `process_npc_reaction(npc, player, stimulus_type, stimulus_data)` — roll perception → reaction type (`ignore`/`disapprove`/`approach`/`comment`) driven by NPC traits (prudish, open_minded, attracted).
- Reactions emit via existing event-stream/emote paths (log entry + area description) — reuse `logging_events.py`, don't invent a new channel.
- Only runs when `mature_content` on for sexual stimuli; generic (non-sexual) reactions always active.

## Files

- `engine/npc_behaviors.py` — new perception/reaction methods
- `engine/lighting.py` — reuse `get_ambient_light()` for DC calc
- `engine/pleasure_actions.py` — stimulus event entry points

## Testing

- [ ] High light + observant NPC notices exposed state; dark room hides it
- [ ] Prudish NPC disapproves, open-minded approaches (per social)
- [ ] Reactions appear in event stream / area description
- [ ] Mature toggle off → no sexual perception

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §8, Phase 6
- `task-213 mature traits` (observant/oblivious/prudish traits)



---

## todo/characters/task-354-pack-logic-for-simple-npcs.md

---
group: Characters
---
# Pack Logic for Simple NPCs

**Filed**: 2026-08-19
**Priority**: Low
**Status**: Idea

---

## Idea

Pack logic for simple NPCs so multiple of the same type can coordinate together via code. Examples: rats, wolves, and other such animals. the idea is that they can hear or smell others of their kind over larger areas to call or warn each other to go away or approach. pack creatures might move or follow each other to areas, attack in groups etc.

## Notes

- Exploratory — flagged "maybe not, we'll see". The idea is recorded for later evaluation. 
- MVP if it ever gets picked up: a shared `pack` tag/property on group members, packmate awareness (detect nearby packmates in the same area), and a coordinated-target behavior rule ("attack the same target as the nearest packmate").
- Full pack AI (formation, flanking, role assignment) is intentionally out of scope for the MVP.

## Related

- `developer ideas.md` line 1
- NPC behavior system (`engine/npc_behaviors.py`)



---

## todo/characters/task-389-npc-behavior-phase1-memory-emotion-hide.md

---
group: Characters
---

# NPC Behavior Phase 1: Memory, Emotion, Flags, Universal Hide

**Filed**: 2026-09-02
**Priority**: High
**Status**: Idea

---

## Summary

Simple NPCs (behavior tree) currently have only 10 action types and cannot write to their own character data. This task adds the foundational actions and conditions that enable NPCs to form memories, track emotions, set flags, and hide — closing the gap with agent/player characters.

Hiding is a **universal action** available to all characters (players, agents, and simple NPCs). Items that can be hidden in/behind/under are marked with a `hideable` tag.

## Current State

`engine/triggers/behaviors.py` (`_execute_behavior_actions`) supports only: `message`, `speak`, `llm_respond`, `set_npc_state`, `damage`, `heal`, `set_environment`, `spawn_item`, `teleport`, `go`.

Characters already have `memories`, `emotion`, `tags`, `npc_state` fields — but no behavior actions write to them.

## New Behavior Actions

### `add_memory`
Append to the character's `memories` array.
```json
{ "type": "add_memory", "text": "player fed me", "importance": 6, "tags": ["player", "food"] }
```
- Writes to `player.memories` (same field agents/players use)
- `importance` 1-10 (default 5)
- `tags` array of single-word strings

### `set_emotion`
Set the character's `emotion` field.
```json
{ "type": "set_emotion", "emotion": "curious", "intensity": 0.7 }
```
- `emotion`: string (calm, alert, fearful, aggressive, curious, angry, etc.)
- `intensity`: 0.0-1.0 (default 0.5)

### `set_flag`
Set a persistent key-value flag on the character.
```json
{ "type": "set_flag", "key": "player_fed_me", "value": true }
```
- Writes to `player.flags` dict (new field, `{}` default)
- Value can be any JSON-serializable type

### Hiding via Edge Relationships

Hiding uses the same spatial edge system as item placement (`in`, `on`, `under`, `behind`). A hidden character has a special `hidden` edge to the container/furniture item.

### `hide_in`
Hide inside a container item.
```json
{ "type": "hide_in", "target": "wardrobe" }
```
- Creates a `hidden` edge from character to item with `relation: "in"`
- Target must be in the same area and have `hideable` tag
- Sets `player.hidden = true`

### `hide_behind`
Hide behind furniture.
```json
{ "type": "hide_behind", "target": "curtain" }
```
- Creates a `hidden` edge with `relation: "behind"`

### `hide_under`
Hide under furniture.
```json
{ "type": "hide_under", "target": "bed" }
```
- Creates a `hidden` edge with `relation: "under"`

### `unhide`
Make the character visible again.
```json
{ "type": "unhide" }
```
- Removes the `hidden` edge
- Sets `player.hidden = false`

## New Behavior Conditions

### `npc_emotion_is`
Check the NPC's current emotion.
```json
{ "type": "npc_emotion_is", "emotion": "angry", "operator": "gte", "value": 0.6 }
```
- `operator`: `eq`, `gte`, `lte` (default `eq`)
- `value`: 0.0-1.0 intensity threshold

### `npc_is_hidden`
Check if the NPC is currently hidden.
```json
{ "type": "npc_is_hidden", "value": true }
```
- Checks `player.hidden` boolean OR presence of `hidden` edge

### `character_has_tag`
Check if a character has a specific tag.
```json
{ "type": "character_has_tag", "tag": "guard", "target": "triggering" }
```
- `target`: `self`, `player`, `triggering` (default `self`)
- Checks `tags` field on the target character

## Required Changes

### Backend (`engine/triggers/behaviors.py`)

Add action handlers for `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `unhide` in `_execute_behavior_actions`.

Add condition evaluators for `npc_emotion_is`, `npc_is_hidden`, `character_has_tag` in `engine/triggers/condition_tree.py`.

### Data Model (`player.py`)

Ensure all Player objects have:
- `flags: dict` (default `{}`)
- `hidden: bool` (default `False`)

Hiding itself is stored as a **graph edge** (`hidden` type) from character to item — consistent with existing spatial edges (`in`, `on`, `under`, `behind`). The `player.hidden` boolean is a fast lookup flag; the edge is the source of truth.

### Hideable Items (new tag)

Items that characters can hide in/behind/under get a `hideable` tag:
```json
{ "name": "Wardrobe", "tags": ["hideable", "furniture", "container"] }
```

When a character hides, the engine:
1. Validates target is in same area
2. Validates target has `hideable` tag
3. Creates `hidden` edge with relation (`in`/`behind`/`under`)
4. Sets `player.hidden = true`

When a character unhides:
1. Removes `hidden` edge
2. Sets `player.hidden = false`

Add new action types to the behavior editor dropdown with appropriate parameter fields.

Add new condition types to the behavior condition editor dropdown.

## Examples

### Cat follows player with fish
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "player_has_tag", "tag": "food" },
    { "type": "npc_emotion_is", "emotion": "curious", "operator": "gte", "value": 0.5 }
  ],
  "actions": [
    { "type": "go", "area": "{player_area}" },
    { "type": "speak", "text": "*meows and rubs against your leg*" }
  ]
}
```

### NPC hides from hostile player
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "character_has_tag", "tag": "hostile", "target": "triggering" },
    { "type": "npc_emotion_is", "emotion": "fearful", "operator": "gte", "value": 0.6 }
  ],
  "actions": [
    { "type": "hide_in", "target": "wardrobe" },
    { "type": "add_memory", "text": "hid from hostile player", "importance": 7, "tags": ["player", "fear"] }
  ]
}
```

### Cat hides under bed when scared
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "sound_above", "threshold": 0.7 },
    { "type": "npc_emotion_is", "emotion": "fearful", "operator": "gte", "value": 0.5 }
  ],
  "actions": [
    { "type": "hide_under", "target": "bed" },
    { "type": "add_memory", "text": "hid under bed from loud noise", "importance": 5, "tags": ["sound", "fear"] }
  ]
}
```

### Player hides behind curtain from guard
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "character_has_tag", "tag": "guard", "target": "triggering" }
  ],
  "actions": [
    { "type": "hide_behind", "target": "curtain" }
  ]
}
```

## Issues to Consider

- Hidden characters: can they be found by `search`? Can they `attack` from hiding? (Recommendation: yes to both — hiding is visual stealth, not invincibility)
- Edge persistence: `hidden` edges must survive save/load via `serialization.py`
- Capacity: should we limit how many characters can hide in one item? (Recommendation: not v1 — tag-based only)
- Hidden edge vs spatial edge: can a character hide in an item that also has spatial edges? (Recommendation: yes — `hidden` is a separate edge type)
- Search interaction: `search wardrobe` should reveal hidden characters inside (Recommendation: yes — search examines contents + hidden edges)

## Audit

**Status**: Ready to implement
**How to test**:
- Create a simple NPC with a behavior using `add_memory` action. Trigger it. Verify the memory appears in the NPC's memory inspector.
- Create a behavior with `set_emotion`. Verify the emotion field updates.
- Create a behavior with `hide_in`. Verify the NPC disappears from the area view.
- Create a behavior with `character_has_tag` condition. Verify it only fires for matching characters.

## Files Affected

- `engine/triggers/behaviors.py` — new action handlers (hide_in, hide_behind, hide_under, unhide, add_memory, set_emotion, set_flag)
- `engine/triggers/condition_tree.py` — new condition evaluators (npc_emotion_is, npc_is_hidden, character_has_tag)
- `graph.py` — ensure `hidden` edge type is supported alongside `in`/`on`/`under`/`behind`
- `player.py` — ensure `flags` dict and `hidden` bool fields exist
- `engine/serialization.py` — persist `hidden` edges and `flags` dict
- `static/js/inspector/behaviors-view.js` — UI for new actions/conditions
- `engine/npc_behaviors.py` — edge cleanup on character death/relocation



---

## todo/characters/task-390-npc-behavior-phase2-sensory-faction-attack.md

---
group: Characters
---

# NPC Behavior Phase 2: Sensory Triggers, Faction Logic, Attack

**Filed**: 2026-09-02
**Priority**: High
**Status**: Idea
**Depends**: Phase 1 (task-xxx-npc-behavior-phase1-memory-emotion-hide)

---

## Summary

Builds on Phase 1 to add sensory awareness (smell, sight, sound), tag-based faction logic, and the `attack` behavior action. This enables NPCs to react to what they sense, form factions, and engage in combat — all without LLM agents.

## Current State

Phase 1 adds `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `unhide` + conditions. Phase 2 adds sensory triggers, `player_has_tag`, `flag_equals`, `attack`, and schedule support.

## New Behavior Actions

### `attack`
Make the NPC attack a target.
```json
{ "type": "attack", "target": "player" }
```
- Delegates to `CombatSystem.attack(char_name, target_name)`
- Uses existing combat resolution (skill checks, damage, equipment)
- `target`: `player`, `self`, or specific character name

## New Behavior Conditions

### `player_has_tag`
Check if the player has an item with a specific tag in inventory.
```json
{ "type": "player_has_tag", "tag": "food" }
```
- Scans `player.inventory` + `player.equipped` for items where `tags` includes the value
- Works on the active player

### `flag_equals`
Check a flag value on any character.
```json
{ "type": "flag_equals", "key": "player_fed_me", "value": true, "target": "self" }
```
- `target`: `self`, `player`, or character name
- Reads from `player.flags` dict (added in Phase 1)

### `sound_above`
Check if a sound's strength exceeds a threshold.
```json
{ "type": "sound_above", "threshold": 0.6 }
```
- Reads `player.recent_hearing` or a sound event in context
- Only valid during `on_tick` or sound-related triggers

## New Triggers

### `on_tick`
Already exists. Used for all sensory/polling checks.

### `schedule_tick` (new)
Fires on a time-based schedule for routines.
```json
{ "trigger": "schedule_tick", "time": "09:00" }
```
- `time`: HH:MM string
- Fires once per day at the specified time
- Alternative: `schedule` array on NPC with `{time, area, activity}` entries

## Sensory Model

### Smell Detection

NPCs detect items with specific tags in their current area.

**Condition** (polled via `on_tick`):
```json
{ "type": "smell_detected", "tag": "food", "range": 0 }
```
- `tag`: item tag to detect (e.g. "food", "blood", "smoke")
- `range`: 0 = same area, 1 = adjacent areas, etc.
- Checks items in area (and adjacent areas if range > 0) for matching tags

### Sight Detection

NPCs detect what the player is holding or wearing.

**Condition**:
```json
{ "type": "sight_holds", "tag": "weapon" }
```
- Checks if the active player has an equipped/carried item with the tag
- Same-area only (NPC must "see" the player)
- Hidden players are NOT visible — returns false if target player is hidden

### Sound Detection

NPCs react to sounds above a threshold.

**Condition**:
```json
{ "type": "sound_above", "threshold": 0.5 }
```
- Fires when a sound event occurs in the same/adjacent area
- Threshold filters minor sounds (footsteps) from major ones (screams, explosions)

## Faction Logic Example

Guard NPC attacks non-faction characters:
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "character_has_tag", "tag": "faction_guards", "target": "triggering" }
  ],
  "actions": [
    { "type": "message", "text": "Halt! You're not one of us." },
    { "type": "add_tag", "tag": "hostile", "target": "self" },
    { "type": "attack", "target": "triggering" }
  ]
}
```

## Routine/Schedule Example

Shopkeeper opens at 9, closes at 6:
```json
{
  "trigger": "schedule_tick",
  "time": "09:00",
  "conditions": [],
  "actions": [
    { "type": "go", "area": "Shop" },
    { "type": "speak", "text": "The shop is now open!" }
  ]
}
```

## Required Changes

### Backend

1. `engine/triggers/behaviors.py` — add `attack` action handler
2. `engine/triggers/condition_tree.py` — add `player_has_tag`, `flag_equals`, `sound_above`, `smell_detected`, `sight_holds` evaluators
3. `engine/triggers/constants.py` — add new condition types to `CONDITION_TYPES`
4. `engine/npc_behaviors.py` — add schedule evaluation (check time, fire behaviors)
5. Sound propagation — ensure sounds reach adjacent areas for `sound_above`

### Frontend

1. `static/js/inspector/behaviors-view.js` — add new action/condition types to editor dropdowns
2. `static/js/shared/trigger-types.js` — expose new conditions in JS editor

### Data Model

1. `player.py` — ensure `recent_hearing` or sound event infrastructure exists
2. `engine/scene_snapshot.py` — expose sound data for condition evaluation

## Issues to Consider

- **Sound propagation**: How far do sound travel? Through closed doors? Need clear rules.
- **Smell range**: Checking adjacent areas requires iterating edges — keep performance in mind.
- **Attack from hidden**: Can a hidden NPC `attack`? (Recommendation: yes — hiding is stealth, not pacifism)
- **Schedule precision**: `schedule_tick` fires once per day at the time. What if the NPC is in combat/sleeping? (Recommendation: skip if busy)
- **Faction tags on players**: Players need a way to gain faction tags. This could be via triggers (e.g., `add_tag` when wearing a uniform) or manual assignment.

## Audit

**Status**: Ready to implement after Phase 1
**How to test**:
- Create a guard NPC with faction logic. Have a player with/without faction tag enter. Verify reaction differs.
- Create a cat NPC with `smell_detected` condition for "food" tag. Give player a food item. Verify cat approaches.
- Create an NPC with `schedule_tick` at a specific time. Advance time. Verify routine fires.
- Create an NPC with `attack` action. Trigger it. Verify combat initiates.

## Files Affected

- `engine/triggers/behaviors.py` — `attack` action
- `engine/triggers/condition_tree.py` — new conditions
- `engine/triggers/constants.py` — register new conditions
- `engine/npc_behaviors.py` — schedule evaluation
- `static/js/inspector/behaviors-view.js` — UI for new types
- `static/js/shared/trigger-types.js` — JS condition definitions
- `player.py` — ensure sound/faction infrastructure



---

## todo/characters/task-403-unified-agent-memory-and-knowledge.md

---
type: task
status: todo
area: characters
priority: high
---

# task-403: Unified agent memory and knowledge system

**Filed:** 2026-09-17  
**Depends on:** task-324 (domain tags feed population queries), task-399
(background simulation needs memory consolidation)

## Progress

**Slice 1 — observation memories (done, 2026-09-21).** The prerequisite
task-425 was blocked on (`entity_ids` populated — was 0/17 — plus a per-subject
index) now exists:

- `engine/observation.py` records one **live observation memory per subject**:
  the area the character stands in and each item it can see there. Perception is
  not re-implemented — it reuses `engine/room_perception` (the shared
  prompt/panel source of truth), and the area itself is recorded
  unconditionally while its *contents* need light
  (`can_perceive`: dead/unconscious/asleep see nothing, darkvision counts).

  **People are deliberately not observed here** (changed 2026-09-21, task-434): a
  character is claimed by `Player.register_first_meeting`, which is also what
  pays for meeting them. If arrival stamped them too, the meeting grant would read
  a tick this had just refreshed and pay nothing — and paying on *sight* saturated
  Entertainment, because a crowded camp re-observes five to ten people on every
  arrival and they go stale again within the novelty window.
- `Player.record_observation` refreshes that memory **in place** rather than
  appending, so the store is bounded by *subjects*, not by visits. Measured:
  **908 memories after 10,080 ticks (1 min/tick) vs 912 after 672 ticks
  (15 min/tick)** — fifteen times the game time, the same number of memories.
- `Player.memory_index` (`subject_id -> memory_id`) takes "which memory is about
  this subject?" out of the memory list entirely, so it does not have to be found
  by scanning for a matching `entity_ids` entry. `has_seen` /
  `observation_tick` / `supersede_observation` read it; `observation_memory`
  returns `None` and falls back to a scan when the index has no usable entry, and
  the scan **repairs** the index — so the index can never silently disagree with
  the store. (Resolving the id back to the entry is still one pass; that is
  cheap next to the subject scan it removes, and a second id→entry map would be
  another structure to keep in sync with three writers.)
- `add_memory` now accepts `entity_ids` / `location` / `salience` and returns
  the entry; the index, `superseded_by` and an evicted subject's index entry all
  round-trip (`engine/serialization.py`) and are rebuilt on load.
- `superseded_by` retires a belief that was replaced (the bread was eaten) so
  recall stops surfacing it. Sightings *refresh*; they do not chain.
- Wired: on area entry (`engine/movement.py`, which the background tier also
  passes through — `_travel_toward` swaps `gs.active_player`) and once per
  character at load, since nothing is observed without a move and the starting
  area must not be the one place a character can never remember.
- Cost: **~5%** of a background week (measured by alternating A/B with warm-up;
  cProfile agrees). A first measurement of 43% was a cold-start artifact — the
  first run paid import/parse costs.
- Tests: `tests/test_observation_memory.py` (14), plus round-trip and load-time
  cases in `tests/test_serialization.py`. Soak unchanged: 23/23 alive, vitals
  identical to baseline at 1 and 15 min/tick.

Still open below (the `AgentMind` facade, preconceived knowledge, need-driven
retrieval, memory traits, memory decay).

## Goal

Collect the scattered knowledge systems already present in the codebase into
one coherent "mind" per agent, and add the missing pieces: pre-conceived
knowledge at scenario start, need-driven memory retrieval, and memory traits.

Current state: knowledge is spread across `Player.memories`,
`SpatialMemory`, `VectorStore`, `known_way_aspects`, `investigation_statuses`,
`traits`, `emotion` recall, and trigger `add_memory`. None of these share a
query interface. An agent cannot answer "where is food?" because that question
touches spatial memory, item tags, visited areas, and stored memories — and
there is no layer that joins them.

This task does not replace any existing system. It defines the unified model
and the seams between them.

## Unified memory model

Add `engine/agent_memory.py` with one class, `AgentMind`. It owns and
delegates to the existing subsystems:

```python
class AgentMind:
    def __init__(self, player, graph, vector_store=None):
        self.player = player
        self.spatial = SpatialMemory(graph)
        self.vectors = vector_store or VectorStore(...)
        self.traits = player.traits or {}

    def recall(self, query: str, need: str = None, context: dict = None) -> list[Memory]:
        """Return ranked memories relevant to query + optional need."""

    def remember(self, event: dict, tags: list[str] = None):
        """Store a structured event as a normal memory + embed it."""

    def know_area(self, area_name: str):
        """Mark an area as visited/known."""

    def knows_way(self, way_id: str, aspect: str = None):
        """Record a known way or way aspect."""

    def set_investigation(self, item_id: str, status: str):
        """Track investigation state on an item."""

    def consolidation_summary(self, since_tick: int) -> str:
        """Produce the bounded background-summary string task-399 requires."""
```

`AgentMind` is a facade. It does not reimplement storage. It calls through to
`player.memories`, `spatial.build_known_routes`, `vector_store.top_k`,
`player.known_way_aspects`, and `player.investigation_statuses`.

## Pre-conceived knowledge (scenario bootstrap)

Add `preconceived_knowledge` to scenario player entries and character templates:

```json
{
  "name": "goblin_scout",
  "memories": [
    {
      "text": "The camp food cache is in the pantry behind the kitchen.",
      "tags": ["food", "camp", "pantry"],
      "importance": 6,
      "salience": 7,
      "location": "kitchen",
      "tick": 0,
      "source": "preconceived"
    }
  ],
  "known_areas": ["camp_entrance", "kitchen", "pantry", "dining_area"],
  "known_items": ["item_dried_meat_01", "item_water_skin_01"],
  "known_ways": {
    "way_kitchen_to_pantry": ["hidden", "behind_shelf"]
  },
  "investigation_statuses": {
    "item_dried_meat_01": "seen"
  },
  "starting_route": {
    "from": "camp_entrance",
    "to": "kitchen",
    "via": ["way_camp_entrance_to_hallway", "way_hallway_to_kitchen"]
  }
}
```

At scenario load, `AgentMind.load_preconceived(player_data)` injects these
into the live player fields before the first tick. They are indistinguishable
from earned knowledge except for `source: "preconceived"` on memories.

**Design rule:** preconceived knowledge is not omniscient. A goblin camp scout
knows the pantry route because they were told; they do not know the locked
cellar unless it is listed. Their `known_areas` depth is authored, not
auto-derived from the whole graph.

## Need-driven memory retrieval

When a vital crosses a threshold, call `AgentMind.recall()` with the need as
query:

```python
needs = player.vitals.get_needs()
for need, urgency in needs.items():
    if urgency > THRESHOLD:
        memories = mind.recall(query=need, need=need, context={"area": player.current_area})
        if memories:
            player.add_memory({
                "text": f"While hungry, you recall: {memories[0].text}",
                "tags": [need, "recall"],
                "importance": memories[0].importance,
                "salience": memories[0].salience,
                "source": "need_recall"
            })
```

`recall()` uses three signals in order:
1. **Tag match** against `player.memories` and `implies` chains from tag files.
2. **Spatial match** via `SpatialMemory.build_known_routes` for the current
   area, filtered by visited-area set.
3. **Semantic match** via `VectorStore.top_k` for the query string.

The result is ranked by `importance * salience * urgency`. Needs that match
no memory produce a generic "you don't know where X is" prompt hint, not a
fabricated location.

## Memory traits

Add to `engine/traits.py`:

```json
{
  "name": "Perfect Memory",
  "category": "cognitive",
  "effects": {
    "memory_recall_boost": 2.0,
    "memory_decay_reduction": 0.0,
    "max_importance_cap": null
  }
}
```

```json
{
  "name": "Poor Memory",
  "category": "cognitive",
  "effects": {
    "memory_recall_boost": 0.5,
    "memory_decay_per_tick": 0.02,
    "max_importance_cap": 6
  }
}
```

`AgentMind.recall()` reads these effects before ranking. `Poor Memory` both
reduces recall chance and caps the importance of memories that can surface.

## Memory decay

Add `memory_decay_per_tick` to `engine/tick_manager.py` player update loop.
For each memory in `player.memories`:

- If `source == "preconceived"`: no decay unless the agent personally
  experiences a contradiction.
- If `source == "background"`: decay is halved; the structured event log
  remains regardless.
- Apply `memory_decay_per_tick` from traits to `memory["salience"]`.
- When `salience <= 0`: remove from `player.memories`, but keep a compressed
  summary in `player.compressed_memories` if `importance >= 7`.

## Files

- `engine/agent_memory.py` (new — the `AgentMind` facade; still to do)
- `engine/observation.py` (new — slice 1: perception → observation memories)
- `player.py` (slice 1: `memory_index`, `record_observation`,
  `observation_memory`, `observation_tick`, `has_seen`,
  `supersede_observation`, `add_memory` entity_ids/location/salience)
- `engine/movement.py` (slice 1: observe on area entry)
- `engine/serialization.py` (slice 1: `memory_index` + `superseded_by`
  round-trip, index rebuild, load-time perception pass)
- `engine/traits.py` (add cognitive traits)
- `engine/tick_manager.py` (add memory decay pass)
- `data/library/traits/*.json` (new trait files)
- `docs/virtualWorld/Systems/Memory System.md` (new)

## Scenario authoring contract

A scenario author adds preconceived knowledge by writing the six keys above
into a player or character template. No code changes are needed beyond the
bootstrap loader in `AgentMind.load_preconceived()`. The keys are optional;
absence means "blank slate."

## Verification

- Load a scenario with preconceived knowledge. Verify the agent's first active
  prompt includes the injected memory and can name the known area/way.
- Starve a preconceived-knowledge agent. Verify `recall()` surfaces the food
  memory and the route to it, and that a `Poor Memory` agent has a lower
  recall chance.
- Run task-399 background simulation. Verify `consolidation_summary()` returns
  a bounded string that `Player.add_memory()` accepts unchanged.
- Save/load a character with preconceived memories, known ways, and
  investigation statuses. Verify they round-trip through
  `engine/serialization.py`.
- Run `python tools/lint_library.py` — trait files must validate.

## Non-goals

- A full world-knowledge graph or ontology.
- Automatic generation of preconceived knowledge from world topology.
- Replacing `VectorStore` or `SpatialMemory` with a single backend.



---

## todo/characters/task-404-character-life-experience-generator.md

---
type: task
status: todo
area: characters
priority: high
---

# task-404: Character life experience generator

**Filed:** 2026-09-17  
**Depends on:** task-403 (unified memory/knowledge system), task-324
(domain tags)

## Goal

Generate substantial life experience for characters — events, outcomes, fears,
hopes, dreams, wants, likes, dislikes, trauma, and everything that makes people
feel real — beyond what a personality summary can convey.

Aura/Diary (`F:\AI\Aura\Diary`) is the closest reference implementation and
should inform the design, but the goal is a VirtualWorld-native system, not a
Neo4j integration.

## What Aura/Diary teaches us

From `readme.md` and `diary_core.py`:

- Day-by-day simulation with LLM-driven choices and tiered outcomes
- 169+ events across life stages, milestones, and random events
- Emotional dimensions: happiness, anxiety, loneliness, energy,
  social_battery, confidence
- Relationships with quality/decay over time
- Location history (`LIVED_AT`)
- First-person diary entries via `memory_utils.generate_memory`
- RAG-based semantic memory retrieval from past events
- Event outcomes range from critical success to critical failure
- Memories incorporate emotional impact, not just factual recall

The valuable patterns to import:
1. **Events as structured choices**, not prose generation — each event has
   options with defined outcome ranges
2. **Emotional impact as first-class data**, not flavor text
3. **Memory as first-person reflection**, not third-person summary
4. **Traits that evolve** from experiences, not static character card data
5. **Relationship history** as a series of recorded interactions, not a number

## What NOT to import

- Neo4j dependency — VirtualWorld uses JSON files and in-memory graph
- The Diary simulation loop running inside VirtualWorld runtime
- Two-way sync between Diary and VirtualWorld state
- Real-time backstory generation during gameplay

## VirtualWorld-native life experience system

### Data model

Add to `engine/agent_memory.py` (task-403):

```python
class LifeExperience:
    """One recorded life event for a character."""
    def __init__(self, event_id, age_days, event_type, description,
                 choices, outcome, emotional_impact, location, tags,
                 participants, memory_text, source="generated"):
        self.event_id = event_id
        self.age_days = age_days
        self.event_type = event_type  # milestone, random, relationship, trauma, achievement
        self.description = description
        self.choices = choices        # [{text, weight, risk}]
        self.outcome = outcome        # {result, success, emotional_impact}
        self.location = location
        self.tags = tags              # ["childhood", "injury", "school"]
        self.participants = participants  # ["mother", "best_friend"]
        self.memory_text = memory_text  # first-person inner monologue
        self.source = source          # "generated", "preconceived", "background"
```

### Event tables

Create `data/life_events/` with JSON tables, modeled on Aura/Diary's
`events.json` but lighter:

```
data/life_events/
  milestones.json      # guaranteed events by age (first steps, puberty, etc.)
  childhood.json       # ages 0-12
  adolescence.json     # ages 13-17
  adulthood.json       # ages 18+
  trauma_events.json   # cross-age, high-impact negative events
  achievement_events.json  # cross-age, high-impact positive events
  relationship_events.json # meeting, bonding, conflict, loss
```

Each event entry:
```json
{
  "id": "childhood_fell_from_tree",
  "event_type": "accident",
  "age_min": 5,
  "age_max": 12,
  "prerequisites": [],
  "choices": [
    {"text": "Cry and run to parent", "risk": "low", "outcome_tables": ["comforted", "scolded"]},
    {"text": "Brush it off and keep playing", "risk": "medium", "outcome_tables": ["infection", "proud"]}
  ],
  "emotional_impact": {"anxiety": [0, 5], "confidence": [-3, 0]},
  "tags": ["childhood", "injury", "outdoors"],
  "location_contexts": ["home", "park", "schoolyard"]
}
```

### Generator script

Create `tools/generate_backstory.py` — a standalone script that:

1. Reads a character template or creates one from scratch
2. Rolls through ages 0 to current_age using milestone tables + random events
3. For each event, selects options based on character traits (risk tolerance,
   personality modifiers)
4. Resolves outcomes using seeded RNG + trait modifiers
5. Generates first-person memory text via LLM (or template fallback if no LLM)
6. Writes the result as a VirtualWorld preconceived-knowledge payload to
   `data/backstories/<name>.json`

Output format (consumed by task-403's `AgentMind.load_preconceived`):
```json
{
  "name": "miki",
  "backstory_source": "life_experience_generator",
  "emotional_state": {
    "base_happiness": 45, "base_anxiety": 60, "base_loneliness": 30,
    "base_energy": 50, "base_social_battery": 40, "base_confidence": 35
  },
  "memories": [
    {
      "text": "I remember falling off the oak tree in our backyard when I was 8. I scraped my knee badly and cried until Mom came running. She cleaned it up and told me I was brave, but I wasn't brave — I was scared and hurting. That's when I learned that brave doesn't mean not being afraid.",
      "tags": ["childhood", "injury", "mother", "outdoors"],
      "importance": 7,
      "salience": 8,
      "location": "childhood_home_backyard",
      "tick": 0,
      "source": "preconceived",
      "emotional_impact": {"anxiety": 5, "confidence": -2},
      "age_days": 2920,
      "participants": ["mother"]
    }
  ],
  "known_areas": ["childhood_home", "elementary_school", "high_school", "first_apartment"],
  "known_items": ["item_moms_locket", "item_childhood_diary"],
  "relationships": [
    {
      "name": "mother",
      "type": "family",
      "quality": 75,
      "history": ["nurturing", "strict", "supportive", "protective"],
      "key_events": ["childhood_fell_from_tree", "high_school_graduation"]
    }
  ],
  "fears": ["heights", "abandonment", "failure"],
  "hopes": ["become_asmr_artist", "find_stable_relationship", "overcome_anxiety"],
  "trauma": [
    {
      "event_id": "childhood_fell_from_tree",
      "severity": 3,
      "trigger": "heights",
      "description": "Fell 3 meters from an oak tree, scraped knee badly"
    }
  ],
  "diary_entries": [
    {
      "age_days": 2920,
      "entry": "Today I fell out of the oak tree again. Third time this month. Mom says I need to be more careful but the branches look so climbable. I don't want to tell her I was showing off for Jake from next door. My knee hurts but I think he was impressed. Worth it? Maybe.",
      "emotional_state": {"anxiety": 40, "happiness": 55, "confidence": 30},
      "location": "childhood_home_backyard",
      "tags": ["childhood", "injury", "crush"]
    }
  ],
  "personality_deltas": {
    "clingy": +2,
    "anxious": +1,
    "creative": +1
  },
  "traits": ["clingy", "anxious", "creative", "awkward"]
}
```

### LLM integration

The generator calls the same LLM provider VirtualWorld already uses. The prompt
asks for a first-person memory of the event, grounded in the character's
personality and the event's emotional impact. No new LLM plumbing is needed.

If no LLM is available, the generator falls back to template-based memories:
"I was [age] when [event]. I felt [emotion]. [One-sentence reflection.]"

### Determinism

All RNG is seeded from character name + event id + age. The same character
generated twice produces identical memories, relationships, and emotional
state. This is required for save/load consistency and for the editor to show
stable backstories.

### Scenario authoring workflow

1. Option A: Author a character template with `backstory_generation` block:
   ```json
   {
     "name": "goblin_scout",
     "backstory_generation": {
       "current_age": 22,
       "events": ["childhood_fell_from_tree", "adolescence_bullied"],
       "custom_memories": ["The camp food cache is in the pantry behind the kitchen."]
     }
   }
   ```
2. Option B: Run `python tools/generate_backstory.py --template goblin_scout.json`
   → outputs `data/backstories/goblin_scout.json`
3. In scenario player/character entry: `"backstory": "data/backstories/goblin_scout.json"`
4. At scenario load, `AgentMind.load_preconceived()` reads and injects

## Files

- `data/life_events/*.json` (new event tables)
- `tools/generate_backstory.py` (new generator script)
- `engine/agent_memory.py` — add `LifeExperience`, `diary_entries`, `fears`,
  `hopes`, `trauma`, `personality_deltas` fields
- `engine/tick_manager.py` — apply `personality_deltas` at load
- `docs/virtualWorld/Systems/Memory System.md` — document the authoring workflow

## Verification

- Generate backstory for Miki using `tools/generate_backstory.py`
- Load Pines scenario with her backstory attached
- Verify her first active prompt references a childhood memory with emotional
  weight, not just personality summary
- Verify fears/hopes/trauma affect behavior: a goblin with `fears: ["fire"]`
  avoids fire sources; one with `trauma: [{trigger: "heights"}]` refuses to
  cross high bridges
- Generate twice with same seed → identical output
- Save/load round-trip: life experience data survives serialization
- Run without LLM → template fallback produces valid memories

## Non-goals

- Running Aura/Diary inside VirtualWorld runtime
- Real-time backstory generation during gameplay
- Two-way sync between an external graph and VirtualWorld state
- Full Neo4j event graph import



---

## todo/characters/task-409-background-schedules-work-and-coarse-social.md

---
type: task
status: todo
area: characters
priority: high
---

# task-409: Background schedules, daily reflection, and coarse social behaviour

**Filed:** 2026-09-19  
**Depends on:** task-399 (background runner), task-408 (clean scenario data).  
**Spec:** task-399 §"Background runner (v1)"; `docs/design/reversibility-contract.md`.

## Progress (slice 1)

**The schedule model and the planner are implemented and tested; the schedule
DATA is deliberately not shipped, because measurement showed it degrades the camp.**

Engine landed (`engine/schedule.py`, `tests/test_schedule.py` — 39 tests):

- Steps are `{start: "HH:MM", activity, area, fallback}`, sorted, wrapping at
  midnight; before the first step the *last* step stays in force, so a day
  starting at 06:00 does not leave anyone idle or wandering from midnight.
- Malformed steps are **dropped, not guessed** — a step with no usable start
  cannot be placed in a day, and inventing one would make a character behave in a
  way nobody authored. An unknown activity degrades to `wait` rather than freeing
  the character to wander. An empty schedule is a valid state: exactly how every
  character behaved before this task.
- `minutes_of_day` reads the engine's own clock (`total_game_minutes`), so a step
  at 07:00 happens at 07:00 at any tick length.
- `normalize` also runs on load, so a hand-edited or legacy file cannot put a bad
  step into somebody's day.
- `background_simulation._pursue_schedule` walks to the step's area — reusing
  `_target_step`, which gains an explicit `areas` override for a *named*
  destination — then starts a short `working` block. It runs **after every
  survival need and before boredom**, so a character works with time no need
  claims and still breaks off to eat. `working` is registered in all five activity
  registries including `ACTIVITY_INTERRUPTIBLE` (the omission that once made
  `conversing` never expire), and the block is deliberately short
  (`WORK_MINUTES = 30`) because `_act` skips anyone mid-activity — the duration is
  the longest a character can go without eating or relieving itself.
- `tools/add_schedules.py` authors schedules idempotently (dry-run default) from a
  per-role table: 16 of 23 characters have a role, derived from the area each
  already starts in. The 6 animals and the player character get none on purpose.

**Why the data is not shipped.** Authored and measured over 3 days at 15 min/tick,
schedules on vs off, same seed:

| vital | avg on | avg off | min on | min off |
|---|---|---|---|---|
| Hygiene | 48.8 | **69.2** | 0.0 | 45.0 |
| Social | 40.3 | **61.6** | 0.0 | 4.0 |
| Entertainment | 19.8 | **42.2** | 0.0 | 8.0 |
| Energy | **72.3** | 55.4 | 40.0 | 31.0 |
| Hunger / Thirst / Sanity | same | same | same | same |

Schedules genuinely work — traces show Thrazz at the Chief's Den working at 09:30,
Mikka at the Workshop, and `schedule:work` firing — and Energy is *better* with
them, because the night step puts characters in the Sleeping Halls so they sleep
properly. But Hygiene, Social and Entertainment collapse: **388 schedule-travels
against 53 work blocks.** Schedule travel competes for the same action budget as
the need ladder and drags characters to work sites that hold **no facilities**, so
the lower-priority needs never get their turn. Priority starvation via travel, not
a broken schedule — and not a regression worth shipping.

**Next, in the order the evidence suggests:**

1. **Co-locate facilities with work.** The work sites (Workshop, Scouting Rooms,
   Training Pit, Chief's Den, Scrap Pile, Cooking Area) have no food, water,
   latrine, wash spot or recreational fixture, so every need is a cross-camp round
   trip. `tools/add_renewable_sources.py` already places fixtures by tag, so this
   is a data pass with an existing tool and the most likely fix.
2. **Only yield to a pressing need.** The ladder interrupts for any need past its
   threshold, so a working character abandons the job for a top-up; a work block
   should ignore non-critical needs and finish.
3. Re-measure, then author the data into the scenario (one idempotent command).

Slice 2 (the capped daily reflection) is unaffected and still open.

**Second round — both attempted fixes failed, and the reason is arithmetic.**

1. **Committing the errand.** Hypothesis: journeys are walked one hop per decision
   and every routine need crossing restarts them, so characters never arrive. Added
   `CRITICAL_*` levels and a committed-journey guard (a scheduled errand runs to
   arrival unless a need is critical). **Result: 388 → 381 travels, 53 → 45 work
   blocks.** No effect — the hypothesis was wrong, and the change was reverted
   rather than kept as unproven complexity.

2. **Co-locating facilities with work.** Hypothesis: work sites have no food,
   water, latrine or wash, so every need is a cross-camp round trip. Added
   `latrine`/`water`/`recreation` area tags to 11 work areas and 4 wash basins
   (`tools/add_workplace_facilities.py`). **This made things worse, including the
   no-schedule baseline** — Hygiene 69.2 → **24.4** with schedules *disabled*, and
   48.8 → **7.9** with them on, and two characters died of exhaustion. Reverted.

   The lesson is worth more than the change: **area tags are not neutral.** They
   are what `_areas_with` consults for *every* need search, so tagging the work
   areas `water` and `latrine` changed where the entire camp travels for every
   need — not just where workers drink. A "co-locate the facilities" pass cannot
   be evaluated as a local data tweak.

**The actual blocker is the action budget.** A background character takes one
action per `DECISION_MINUTES` (10 game minutes), so a day is about **96 actions**
per character. Survival need service is not cheap in actions: each is a *journey*
of one hop per action, and the camp's food, water, latrine and wash are in
different corners. A working day of twelve 30-minute blocks cannot fit beside
those errands — and once schedule travel competes for the same budget, the
errands slow down too, which is exactly what the numbers show (Hygiene and
Entertainment collapse; `schedule:work` fires about once per character per day).

So this is a **design decision, not a data tweak**:

- **(a) More actions per day** — shorten `DECISION_MINUTES` or raise
  `MAX_ACTIONS_PER_TICK`. Straightforward, but multiplies tick CPU across 23+
  characters, and it treats the symptom: it makes the character *finer*-grained
  when the goal is "supercharged simple NPCs".
- **(b) Coarser need service** — bundle the errands. At 10-minute granularity a
  character should not walk to the river, drink, walk back, then walk to the
  latrine as three separate decisions; it makes **one "chores" trip** to a service
  area and services several needs in a single action. This is what a coarse
  simulation should already be doing, and it collapses roughly five errands into
  one, freeing the budget for work. The camp's existing latrine/wash/food/water
  areas already identify where a chores trip would go.
- **(c) Drop the working day** — keep schedules only for *placement* (where a
  character is by day and night, which is already an improvement and measured as
  Energy-positive) and accept no work blocks.

(b) is the recommended one: it fits 409's own "supercharged simple NPCs" framing,
it is the change that makes the budget arithmetic work, and it does not trade CPU
for the problem. It is also a change to the *survival model's granularity*, so it
should be decided rather than assumed. Until then the schedule data stays out of
the scenario and the engine remains as committed in slice 1.

## Goal

Background characters behave like **supercharged simple NPCs**: a deterministic,
action-oriented planner pursues their goals every tick, with **one local LLM
reflection call per character per in-game day** to check direction and set what
to reach toward.

## Division of labour (decided)

- **Deterministic backend (non-LLM)** does the action planning and execution:
  schedule steps, work, travel, consume, coarse meetings — goal-directed, no
  LLM, seeded and reproducible.
- **Local LLM, ≤1 call/character/in-game day** answers a reflection prompt:
  *"Am I doing what I should? What do I want to reach toward?"* and proposes
  goals/adjustments. It runs through the local LM Studio provider only, never
  decides an individual action, and its output is written as goals/plan/memory
  so the deterministic planner is what acts.

This keeps cost proportional to population × game-days, not ticks, and keeps
behaviour auditable.

## Changes

1. **Schedule model.** Authored per character
   (`{start, activity, destination_scope_or_area, fallback, vital_policy}`),
   serialized, with `fallback: wait`. The due scheduler advances schedule steps
   as well as needs.
2. **Goal-directed planner (deterministic).** Given schedule + goals + needs +
   traits + relationships, pick the next step (work/wait/travel/consume/social)
   and execute coarsely, reusing existing movement/item rules where exact
   resolution is needed.
3. **Daily reflection (local LLM, capped).** Once per in-game day per background
   character, one call to the local model over a bounded context (goals,
   relationships, recent trace). Output updates goals/plan; it never chooses the
   immediate action. Hard cap enforced and logged; failures fall back to the
   existing goal unchanged.
4. **Coarse meetings.** Deterministic from relationships + traits + vitals +
   seeded RNG; apply symmetric relationship deltas; never fabricate items.
   **Amended by task-417:** the pairing pass runs **per area over co-present
   characters**. As written here the rule has no spatial constraint and would
   pair characters in different areas. task-417 is authoritative for this step.
   Deltas are written through `apply_relationship_delta` (task-420).
5. **Deferral rules.** Combat, ambiguous theft/trade, a blocked/locked route, a
   trigger needing precise surroundings, or an encounter marked
   `requires_active` stop and request scope activation.

## Acceptance

- A fixed seed replays a schedule/plan span identically **with reflection
  disabled**.
- At most one reflection LLM call per character per in-game day, local provider
  only; with no local model configured the sim runs unchanged.
- Reflection writes goals/plan/memory and never a direct action.
- Meetings produce symmetric relationship deltas on both sides.
- Deferred outcomes never invent facts; they surface as activation requests.
- Save/load preserves schedules, goals, `next_due_tick`, and seeded RNG state.
- Background characters visibly move through distinct day activities over a
  multi-day soak (not just eat/drink/sleep loops).

## Non-goals

- A general economy, relationship simulation, or full offscreen combat.
- Replacing the existing foreground LLM loop.

## Verification

- Extend `tests/test_background_simulation.py`: seed determinism (reflection
  off), reflection cap, goal-planner selection, deferral, symmetric
  relationships, schedule serialization.
- A multi-day soak report showing distinct activities per character.



---

## todo/characters/task-412-promotion-demotion-and-trace-consolidation.md

---
type: task
status: todo
area: characters
priority: high
---

# task-412: Promotion/demotion and trace→memory consolidation

**Filed:** 2026-09-19  
**Depends on:** task-399 (background runner), task-411 (attention tiers),
task-418 (attended set), task-420 (one relationship write path).
Without task-420 the foreground and background tiers write relationship state
through different paths, so a tier change can jump the value.  
**Spec:** `docs/design/reversibility-contract.md`, `docs/design/trace-format.md`.

## Goal

Implement the promote/offload handoffs so a character can switch fidelity
without ever becoming a different person or rewriting their past.

## Changes

1. **Promotion handoff.** Build a catch-up summary from
   `engine/trace.summarize_window` since the character was last foreground;
   inject it as a **bounded** subjective memory (`source: "background"`); restore
   the standing goal/plan so promotion resumes rather than reinvents.
2. **Demotion handoff.** Roll the foreground span into the trace as facts +
   reasons; keep live memories in the memory store; mark the span consolidated
   so repeated activation is idempotent.
3. **Atomic transitions.** Activate/offload is atomic at its tick — no action is
   resolved twice.
4. **Invariants.** Enforce position continuity, object conservation, vital
   continuity, relationship symmetry, stable opaque id (task-316),
   determinism, and no orphan nodes (guards the duplicate-character-node class
   of bug).

## Acceptance

- Activate/offload twice at the same tick, then save/reload: no duplicate
  action, character, item, or summary memory.
- A character receives no duplicate background memory after repeated activation.
- A span with a fixed seed replays identically.
- The v1 summary is a deterministic template over trace facts (no LLM); an
  optional LLM summary comes later and only reads the trace.
- Save/load mid-transition is safe because transitions land on tick boundaries.

## Non-goals

- LLM-written catch-up summaries in v1 (template first).
- Editing past memories (the contract forbids rewriting history).

## Verification

- Unit: idempotent activation, no duplicate memory, determinism, invariant
  checks, save/load mid-span.
- Contract test: an item taken in background is neither duplicated nor lost
  across promote → demote.



---

## todo/characters/task-447-character-nicknames-and-aliases.md

---
type: task
status: todo
area: characters
priority: medium
---

# task-447: Character nicknames / aliases (authoring + resolution)

**Filed:** 2026-09-22
**Related:** task-446 (id-first node identity), task-448 (ambiguous target prompt),
`engine/matching.py` (character alias tier), `engine/serialization.py`

## Why

A character can go by a short name the game must resolve: "Vi" for *Violet
Halloway*. Nicknames are a **resolution-layer** concern — they map spoken input
to an identity; the data stays id-keyed. The engine already has a character
**alias tier** (`matching.py` `_match_character_name` step 2b, reading the node's
`aliases` property via `node_aliases`), but there is no way to author it and it
does not persist.

Note: "Vi" is *not* a substring of "Violet" (matching is word-boundary aware), so
a nickname cannot be inferred — it must be declared.

## Problem

1. **No authoring surface.** Character nodes in scenarios carry only
   `personality`; the inspector/library has no nicknames field.
2. **Aliases do not survive save/load.** On load a character's graph node is
   recreated bare — `Node(id, type="character", name=pname)` with no properties
   (`serialization.py`) — so an authored alias on the node would be lost. The
   alias must live where player state round-trips (the player payload) or be
   re-applied on load.

## Scope

- Add a **nicknames/aliases** field for characters in the inspector and library
  editor (list, or comma/`|`-separated like other alias fields).
- Persist it: store on the player payload (or a node-properties map that
  serialization restores) so it survives save/load and library import/export.
- Resolve it: the existing character alias tier already returns **candidates**
  when several characters share an alias — keep that (it feeds task-448).
- Consider surfacing aliases in autocomplete and in the target prompt.

## Acceptance

- Author can add "Vi" to Violet Halloway; `look`, `approach`, `talk to vi`
  resolve to that character.
- Alias survives a save → load and a library round-trip.
- Two characters sharing an alias return an ambiguous candidate set (not a silent
  pick).

## Non-goals

- Duplicate **display** names (task-446).
- The disambiguation prompt UX (task-448).



---

## todo/characters/task-457-character-nodes-are-the-canonical-character-record-human-agent-simple-npc.md

---
type: task
status: todo
area: characters
priority: high
---

# task-457: Character nodes are the canonical character record (human, agent, simple NPC)

**Filed:** 2026-09-22
**Related:** task-446, task-316

## Goal

Make the character graph node the single source of truth for a character's full definition (stats, skills, vitals, traits, tags, interest_tags, personality, descriptions, emotion, conditions, simple_npc/autonomy/behaviour fields; inventory/equipped via edges). The Player object becomes a runtime view derived from and synced with the node: load seeds node properties from the players section (additive migration), node writes are authoritative, and no defining field lives only on the Player. Uniform for human, agent, soak and simple NPCs.

## Acceptance

- TODO



---

## todo/characters/task-468-interrupt-capable-background-agendas-theft-and-social-approach.md

---
type: task
status: todo
area: characters
priority: medium
---

# task-468: Interrupt-capable background agendas: theft and social approach

**Filed:** 2026-09-22
**Related:** task-464, task-466, task-409, task-399, task-214

## Goal

Give background/soak policies the actor-driven agendas timeskip interrupts depend on:
theft (reuse `steal_item`) and deliberate social approach toward the player. Agenda
selection is deterministic, driven by traits, relationships, needs and schedule;
actions target co-located characters and write trace facts. Without this, waits and
fast-travels can never be meaningfully interrupted by other characters; the interrupt
evaluator (task-466) has nothing actor-driven to react to.

> **"Stalking" was a typo for "talking"** (the original ask was "steal from them,
> talk to them, or find something"). The social-approach half is done — see below.

## Acceptance

- [x] Deliberate social approach: `background_social.run_social_approach()` lets a
  co-located background character initiate a `chat` toward the active player, writes
  a `social_approach` turn event, and gives the player the memory; the timeskip
  interrupts with kind `social`. [[done in task-469 slice, tests/test_social_approach.py]]
- [ ] Theft agenda: a trait/need-driven background character attempts `steal_item`
  on a co-located target (theft already emits a "notices" line the evaluator reads).
- [ ] Approach variety beyond `chat` (compliment/tease/confide by relationship band);
  currently forced to `chat` so the first touch is neutral.
- [ ] Agenda selection from traits/relationships (a bully, a thief, a flirt), not
  only the social pass's weighted draw.



---

## todo/characters/task-476-npc-skill-profiles-from-traits-and-roles.md

---
type: task
status: todo
area: characters
priority: medium
---

# task-476: NPC skill profiles from traits and roles

**Filed:** 2026-09-23
**Related:** task-472, task-474, task-475, task-213

## Goal

Make checks differ per character without an LLM: role/trait skill biases (hunter -> Survival/Nature/Animal Handling, guard -> Perception/Insight/Intimidation, thief -> Sleight of Hand/Stealth, healer -> Medicine/Insight, scholar -> History/Religion/Arcana, smith -> Athletics/craft), feeding the existing TraitSystem.get_skill_check_mods seam so a goblin trapper out-forages a child in the same wood.

## Acceptance

- TODO



---

## todo/characters/task-480-skill-growth-abilities-as-mutable-stats-and-proficiency.md

---
type: task
status: todo
area: characters
priority: low
---

# task-480: Skill growth, abilities as mutable stats, and proficiency

**Filed:** 2026-09-23
**Related:** task-472, task-474

## Goal

Give characters a progression model: use-based skill advancement (rolling a skill can raise it), abilities as mutable stats changed by play, and an optional proficiency term so the sheet expresses trained + ability separately. Also define setting skill packs so a new setting can grant its own skills to the relevant characters on top of the base list.

## Acceptance

- TODO



---

## todo/characters/task-484-tune-the-frightened-condition-once-real-fears-exist.md

---
type: task
status: todo
area: characters
priority: medium
---

# task-484: Tune the frightened condition once real fears exist

**Filed:** 2026-09-23
**Related:** task-469; task-472

## Goal

Deferred from task-469: give 'frightened' real attack/defense modifiers and an ends_on once authored fears are common enough to calibrate against.

## Acceptance

- TODO



---

## todo/characters/task-486-auto-regenerate-description-on-body-state-change.md

---
type: task
status: todo
area: characters
priority: medium
---

# task-486: Auto-regenerate description on body-state change

**Filed:** 2026-09-23
**Related:** task-210

## Goal

Regenerate the stored player.description when conditions/body_state change, not only on equip/unequip: add an _update_state_description() hook (guarded by world.auto_generate_descriptions) and optionally _get_state_hash() caching skipped when mature_content is off. Tracked from task-210.

## Acceptance

- `player.description` refreshes when a visible condition/body-state change is applied or removed (e.g. `nipple_hard`, `blushing`, `wetness`), not only on equip/unequip.
- Guarded by `world.auto_generate_descriptions` (off → no regeneration) and respects the `world.mature_content` gate on the body-state block (`engine/equipment.py:_body_state_description_lines`).
- Optional per design: `_get_state_hash()` (equipment + conditions + body_state) prevents redundant regeneration when nothing changed.
- `engine/pleasure_actions.py`-style matures stay off in non-mature worlds.
- Test coverage added; `python -m pytest tests/test_<name>.py -q` green.



---

## todo/characters/task-487-exhibitionist-trait-effect-arousal-from-being-seen.md

---
type: task
status: todo
area: characters
priority: low
---

# task-487: Exhibitionist trait effect: arousal from being seen

**Filed:** 2026-09-23
**Related:** task-213

## Goal

Wire the exhibitionist trait effect, which is currently defined but inert (effects: {exhibitionist: true}, no consumer): grant arousal/pleasure when the character is publicly exposed or being looked at, and add a behavior_prompt. Tracked from task-213.

## Acceptance

- `exhibitionist` gains a live consumer (`TraitSystem.has_effect(p, "exhibitionist")`), granting arousal/pleasure when the character is publicly exposed or being looked at.
- A `behavior_prompt` is added so the agent references the trait.
- Only active when `world.mature_content` is on; the trait stays hidden from pickers when off (`routes/library_ops.py:195-205`).
- Test asserting the effect fires (and does not fire for non-carriers).



---

## todo/characters/task-488-single-track-trait-effect-gate-release-to-one-path.md

---
type: task
status: todo
area: characters
priority: low
---

# task-488: Single Track trait effect: gate release to one path

**Filed:** 2026-09-23
**Related:** task-213

## Goal

Wire the single_track trait effect, which is currently defined but inert (effects: {single_track: true}, no consumer): gate the release path to a single predefined route so other stimulation only builds frustration. Tracked from task-213.

## Acceptance

- `single_track` gains a live consumer that gates release to one designated path; other stimulation builds frustration/edging instead of triggering release.
- Only active when `world.mature_content` is on.
- Test asserting a non-designated path does not release, and the designated path does.



---

## todo/characters/task-489-environmental-clothing-prop-defaults-and-wet-transparency-friction.md

---
type: task
status: todo
area: characters
priority: low
---

# task-489: Environmental clothing: prop defaults and wet transparency/friction

**Filed:** 2026-09-23
**Related:** task-215

## Goal

Finish task-215: give item nodes default comfort/friction/coverage/opacity (opacity 0.8, coverage 0.8 when absent), and couple the existing wet state (condition 'wet', equipment_bonuses.py:107) to clothing opacity/friction so rain/swimming makes layers more see-through and changes friction, then triggers description regeneration. Friction->arousal trickle already ships (engine/tick_manager.py:1028) as does weather/wind/humidity.

## Acceptance

- Item nodes expose `comfort`/`friction`/`coverage`/`opacity`, with `opacity`/`coverage` defaulting to 0.8 when absent, surfaced by `_equipment_detail_lines()` (`engine/equipment.py:645`).
- The `wet` condition raises clothing `opacity` (more see-through) and changes `friction`.
- The state change retriggers the equipment description when `world.auto_generate_descriptions` is on (coordinate with task-486).
- Arousal coupling stays `mature_content`-gated; wetness/transparency itself is generic.
- Tests for the prop defaults and the wet coupling.



---

## todo/characters/task-490-incorporeal-undead-damage-resistance-and-condition-immunities.md

---
type: task
status: todo
area: characters
priority: low
---

# task-490: Incorporeal undead: damage resistance and condition immunities

**Filed:** 2026-09-23
**Related:** task-309

## Goal

Complete the still-open part of task-309: D&D-style damage resistance/immunity for incorporeal undead (resistance to nonmagical weapons, immunity to cold/necrotic/poison) and condition immunities (grappled/restrained/prone/exhausted/...). Engine hooks: engine/combat.py damage resolution and engine/conditions.py application.

## Acceptance

- Incorporeal undead take reduced or no damage from nonmagical weapons and are immune to cold/necrotic/poison.
- Condition immunities: grappled/restrained/prone/exhausted (and the rest of the 5e ghost list) cannot be applied to them.
- Keyed off the incorporeal/undead identity from task-309 (`engine/combat.py`, `engine/conditions.py`).
- Tests covering resistance/immunity and condition application.



---

## todo/docs/task-338-turn-queue-documentation.md

# Task 338 — Document turn-queue & human-turn gating architecture

**Status:** Todo — filed 2026-08-23 after Tommy corrected a wrong
assumption in the panel redesign work (task-333/334)

## Why

The turn system EXISTS and is real — `static/js/agent/turn-queue.js`
manages character ordering (sequential / random / **initiative** with d20
+ DEX rolls, re-roll support) consumed by AgentEngine as
`.turnQueue` / `.currentTurnIndex` / `.turnNumber`. The human turn panel
is gated to the controlled character's slot in that queue. Meanwhile the
always-available command line / guest-speaker path in the event stream is
a **deliberate godmode-level override**, not a missing scheduler.

None of this was understood during the panel redesign until Tommy
corrected it — the architecture lives in code + Tommy's head, not docs.
That's a documentation gap: future work (react phases, digests, dash
two-action turns, multi-human tables) all builds on these semantics.

## What to document (AGENTS.md section + guide chapter)

1. **Turn queue** (`turn-queue.js`): order modes, initiative rolls,
   re-roll, how currentTurnIndex advances, what happens on
   join/leave/death mid-queue.
2. **Human turn gating**: how the panel knows it's "your turn"; what the
   world does while waiting (autopilot paused? ticks continue?); what
   happens if the human idles.
3. **Godmode override semantics**: the free-typing command line /
   guest-speaker event-stream path — always available by design, bypasses
   the queue, when to use vs when it breaks scene logic.
4. **Interaction rules**: override actions vs queued turns (does an
   override consume the character's queued slot?), digest/react
   implications (task-334 builds on this).
5. Where the panel's "next up" indicator reads from.

## Files

- `AGENTS.md` — new "Turn system" gotcha block
- `docs/virtualWorld/` — architecture chapter (or extend an existing
  engine doc)
- Cross-link from task-333/334

## Verification

- A fresh agent (or human) can explain whose turn it is and why the
  command line still works, purely from the docs.



---

## todo/docs/task-492-item-action-model-reference-reach-take-gate-depletion-components.md

---
type: task
status: todo
area: docs
priority: medium
---

# task-492: Item & action model reference (reach, take-gate, depletion, components)

**Filed:** 2026-09-23
**Related:** task-491

## Goal

Write the canonical technical page for the item/action model so these rules are discoverable without reading code: the actions list as the capability gate (take_item raises when 'take' absent, take_drop_actions.py:388-393), reach rules (engine/item_reach.py), depletion branching (generic use detaches; lit carried -> unlit + on_depleted; lit area -> burned out + removed; armor -> broken; food -> consume path), container nesting, and the planned part/component contract. Patterns to imitate: the item_reach.py module docstring and engine/item_actions.py facade docstring.

## Acceptance

- One technical page under `docs/virtualWorld/` documents: actions-as-capability-gate (with the `take_item` example), the `item_reach` rules, every depletion branch, container nesting, and the part/component contract (once task-493 lands).
- It is registered in the docs index.
- Claims are anchored with `file:line` pointers and covered by a linked test where one exists.



---

## todo/gameplay/task-299-long-distance-communication.md

---
group: Gameplay
---
# Long-Distance Communication (Phones, Walkie-Talkies, Radios)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Design (2026-09-23) — approach agreed, not started

---

## Idea

Triggers/mechanics to allow long-distance communication — phones, walkie-talkies, radios or magic like message. some being audio only, some being with visible data

## Notes

- New channel system: speech routed through an item property instead of area adjacency. `speak`/`whisper`/`shout` currently broadcast to the area (+adjacent rooms through open doors).
- Suggested MVP: items with a `comms_channel` tag/property; `speak` while using/holding the item relays to everyone holding an item on the same channel, regardless of distance.
- alternative approach of item like phone having a subitem that is contacts like call James, so you should do "use phone - call james" that then would call that person, initating a activity of being on the phone, but we should sometimes be allowed to talk and do other actions, some items might now allow it.  how it handles on the othe rend too, in the phone example the target should on their turn get "your phone is calling" and as such the phone should have a subitem like answer phone" or something like that

## Design decisions (2026-09-23 discussion)

- **Composition over verbs.** A device (phone/radio) is a parent item whose capabilities are *child part items*, each with its own triggers/state/`uses`. No per-item named verbs — the verb set stays the fixed engine enum (see task-491).
- **No `power` property.** Charge/degradation is the generic `uses` (+ `on_depleted`); no device-type-specific fields on the base item (see task-493).
- **Non-portable parts.** A part omits `take` in `actions`, so it cannot be taken/dropped/put while staying reachable/usable (the gate already exists at `take_drop_actions.py:388-393`). No new edge type required.
- **A call is a directed channel, not area propagation.** Only the caller's directed utterance relays to the partner endpoint; the caller's room still hears them *physically* (muffled unless `speakerphone`). A `speakerphone` state is the explicit opt-in that captures room audio. Ringing already works via `sound_source` + `current_state: "ringing"`; the `on_speech` relay (`engine/speech.py:362-390`) needs extending to **carried** items.
- **An ongoing call** is an activity/condition that does **not** skip turns — talking and other actions coexist.
- **Open:** default speech isolation (muffled vs speakerphone), and whether individual parts are separately addressable (`use phone battery`).

## Related

- `task-491` — action-verb single source of truth
- `task-493` — item part/component model
- `task-494` — container examine reveal + chained action
- `task-352` — action economy (concurrency while on a call)
- `developer ideas.md` line 6
- `engine/sound.py`, `routes/action.py` speech verbs (`speak`/`shout`/`whisper`/`scream`)



---

## todo/gameplay/task-313-relative-facing-map.md

---
group: Gameplay
---
# Relative Facing Map (Forward/Left/Right/Back)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Idea

---

## Idea

Map forward, left, right, and back relative to a character, based on cardinal directions and origin ways (where someone is at?)(using the suggested transit tags on areas).

Example (from the ideas doc): if you come from the south, "right" is east and "left" is west; if you come from the west, "right" is south and "left" is north.

## Notes

- Gives the character an orientation derived from the last way/area they entered, so "to your left" resolves to a real direction.
- Builds on the existing cardinal-axis work for areas/ways (`map_editor` cardinal layout) and the character spatial system (`engine/character_spatial.py`).
- Owner note: user believes this is not that hard — likely because the cardinal infrastructure already exists; the remaining work is per-character facing state + direction resolution.

## Related

- `developer ideas.md` lines 20–21
- `engine/character_spatial.py`, map editor cardinal layout, way transit/tags



---

## todo/gameplay/task-352-action-economy.md

---
group: Agent AI & Behavior
---
# Action Economy

**Filed**: 2026-07-30  
**Priority**: Low  
**Status**: Design  

---

## Summary

Add a flexible action economy system where characters have configurable numbers of actions per turn (action, bonus action, free action, reaction). Different characters can have different budgets — some might get 3 actions with no reactions, others 1 action with 2 bonus actions. Map all valid verbs to default action tiers.

---

## Problem

Currently every command costs flat time+energy (`move: {time:1, energy:1}`). There's no distinction between major actions (attacking, using an item) and trivial ones (opening an unlocked door, speaking). A character can attack, move, open a door, pick up an item, and talk all in one turn with no budget constraints. The economy is purely time-based, not action-slot-based.

---

## Complete Action Inventory

Below is every valid action in the game, organized by category, with proposed default action tier and time/energy costs.

### Movement
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `go` | `go [exit]` | **Action** | 1 | 1 | Moving to another area |
| `open` (unforced) | `open [exit]` | **Free action** | 0 | 1 | Unlocked/unforced door — trivial |
| `open` (forced/locked) | `open [exit]` | **Action** | 1 | 2 | Requires force — significant |
| `close` | `close [exit]` | **Free action** | 0 | 1 | Same as unforced open |

### Item Interaction
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `take` | `take [item]` | **Action** | 1 | 1 | Picking something up |
| `drop` | `drop [item]` | **Free action** | 1 | 0 | Dropping is quick |
| `use` | `use [item]` | **Action** | 1 | 1 | Activating/consuming an item |
| `use [item] on [target]` | | **Action** | 1 | 1 | Combined interaction |
| `eat` | `eat [item]` | **Action** | 1 | 0 | Consuming food |
| `drink` | `drink [item]` | **Action** | 1 | 0 | Consuming drink |
| `examine` | `examine [target]` | **Bonus action** | 1 | 0 | Quick inspection |
| `put [item] in [container]` | | **Bonus action** | 1 | 1 | Stowing item |
| `toggle` | `toggle [item]` | **Free action** | 0 | 0 | Flicking a switch, lighting a candle |

### Equipment
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `wear` / `equip` | `wear [item]` | **Bonus action** | 1 | 1 | Equipping one item |
| `remove` / `unequip` | `remove [item]` | **Bonus action** | 1 | 0 | Unequipping one item |
| `undress` | `undress` | **See task-131** | — | — | Stateful multi-turn action |
| `strip` | `strip` | **See task-131** | — | — | Stateful multi-turn action |

### Information
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `look` | `look` | **Free action** | 1 | 0 | Glancing around |
| `inventory` | `inventory` / `i` / `inv` | **Free action** | 0 | 0 | Checking your gear |
| `stats` | `stats` / `status` | **Free action** | 0 | 0 | Checking your condition |
| `examine` | `examine [target]` | **Free action** | 1 | 0 | Inspecting something |

### Social
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `speak` / `say` | `say [text]` | **Free action** | 0 | 0 | Speaking a few sentences |
| `yell` / `shout` | `yell [text]` | **Free action** | 0 | 1 | Loud speech costs energy |
| `whisper` | `whisper [text]` | **Free action** | 0 | 0 | Quiet speech |
| `do` | `do [description]` | **Free action** | 0 | 0 | Emote/narrative |

### Combat
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `attack` | `attack [target]` | **Action** | 1 | 2 | Standard attack |
| `attack with [weapon]` | | **Action** | 1 | 2 | Weapon attack |
| (off-hand attack) | | **Bonus action** | 1 | 1 | Off-hand weapon |
| (opportunity attack) | | **Reaction** | 0 | 1 | Triggers on enemy movement |
| (parry / dodge) | | **Reaction** | 0 | 1 | Triggered defensive action |

### Vitals / Self
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `rest` / `sleep` | `rest [min]` | **Action → stateful** | — | — | See task-131 |
| `fumble` | `fumble around` | **Action** | 2 | 3 | Blind search in darkness |
| `relieve` | `relieve` | **Action** | 1 | 0 | Bathroom break |

### Ghost
| Verb | Syntax | Proposed tier | Time | Energy | Notes |
|------|--------|---------------|------|--------|-------|
| `manifest` | `manifest` | **Bonus action** | 0 | 1 | Become visible |
| `vanish` | `vanish` | **Bonus action** | 0 | 1 | Become invisible |

### Default (unlisted actions)
Any verb not listed defaults to **Action** with `{time: 0, energy: 0}`.

---

## Action Economy Model

### Per-character configuration

Action budget is a per-character trait/config, not hardcoded:

```python
player.action_budget = {
    "action": 1,       # major actions per turn
    "bonus": 1,        # minor quick actions per turn
    "free": 3,         # trivial actions per turn (capped, but rarely hit)
    "reaction": 1,     # reactive actions per turn (resets on turn start)
}
```

These can vary by character:
- **Standard**: 1 action, 1 bonus, 3 free, 1 reaction
- **Veteran fighter**: 2 actions, 1 bonus, 3 free, 1 reaction
- **Quick / DEX-based**: 1 action, 2 bonus, 3 free, 1 reaction
- **Sluggish / exhausted**: 1 action, 0 bonus, 2 free, 0 reaction
- **Panicked**: 1 action, 1 bonus, 3 free, 0 reaction (can't react)

Traits can modify budgets:
- `slow`: -1 action per turn
- `quick_reflexes`: +1 reaction per turn
- `indecisive`: -1 bonus action per turn

### Tier definitions

| Tier | Used for | Capped per turn | Resets |
|------|----------|-----------------|--------|
| **Action** | Major activities (attack, cast, use item, move, take) | Configurable (default 1) | Start of character's turn |
| **Bonus action** | Quick secondary activities (toggle, equip, off-hand attack) | Configurable (default 1) | Start of character's turn |
| **Free action** | Trivial activities (speak, examine, drop, look) | Configurable (default unlimited / soft cap 3) | Start of character's turn |
| **Reaction** | Response to others' actions (parry, opportunity attack, dodge) | Configurable (default 1) | Start of character's turn |

### Interaction with existing time/energy costs

The action economy is an **additional layer** on top of time/energy:

- An action still costs its `time` and `energy` values
- BUT if the character has no **Action** slots remaining, they can't take an action-tier verb even if they have energy
- A **Free action** that costs 1 time still takes game time but doesn't consume a budget slot
- Reactions can happen off-turn — they consume a reaction slot and reset at the start of the character's next turn

### Prompt injection

The agent prompt should include remaining action budget:

```
=== ACTION BUDGET ===
Actions remaining: 1/1
Bonus actions remaining: 1/1
Reactions available: 1/1 (used off-turn)

Choose ONE action from the list above.
```

Low-action-budget agents should be prompted to prioritize ("You only have 1 action left this turn — make it count.")

### Time cost ties to stateful actions (task-131)

Time costs feed into the stateful actions system — if an action costs 1 time and the character has no time remaining, they're out of actions for the turn. Time is the bridge between the action budget and the turn cycle.

---

## Agent Multi-Action: Design Decision

If a character has budget for e.g. 1 action + 1 bonus + 1 free, how does the agent execute them?

### Option A: Single prompt, sequence of actions

Agent generates all actions in one LLM response with a multi-part JSON schema:

```json
{
  "action": "attack Butcher",
  "bonus": "examine bookshelf",
  "free": "say 'take that!'"
}
```

- **One LLM call** per turn — fast, cheap
- **Coherent plan** — actions can reference each other
- **Simpler turn queue** — one cycle per character
- **Con:** Complex validation — if the action fails, what happens to the bonus and free? Do they still execute?
- **Con:** Larger prompt, more tokens per call
- **Con:** Can't adapt mid-turn based on action results

### Option B: Multiple prompts, loop per character

Agent generates one action at a time. After each action resolves, if budget remains, prompt again for the next action:

```
→ Prompt 1: "You have 1 action + 1 bonus + 3 free remaining. What do you do?"
  → Agent: {"action": "attack Butcher"}
  → Action resolves, budget = 0 action / 1 bonus / 3 free
→ Prompt 2: "Action resolved. You have 1 bonus + 3 free remaining. Bonus action?"
  → Agent: {"bonus": "examine bookshelf"}
  → Bonus resolves, budget = 0 bonus / 3 free
→ Prompt 3: "Bonus resolved. You have 3 free actions. Free action?"
  → Agent: {"free": "'take that!'"}
  → Free resolves, turn ends
```

- **Adaptive** — each action sees the result of the previous one
- **Simpler schema** — one action type per response
- **Smaller prompts** — per-action context
- **Con:** Multiple LLM calls (3× slower, 3× cost per character turn)
- **Con:** Actions may lose coherence — agent might change its mind mid-turn based on results
- **Con:** Turn queue becomes more complex (sub-cycles per character)

### Option C: Hybrid — single prompt, sequential execution

Agent generates all planned actions at once, but they're executed sequentially with result chaining:

```json
{
  "action": "attack Butcher",
  "expected_result": "Butcher takes damage and retaliates",
  "bonus_if_possible": "examine bookshelf",
  "free": "say 'take that!'"
}
```

- One LLM call for planning
- Each action still resolves independently
- If action fails (Butcher dodged), bonus is skipped or replaced
- **Con:** More complex schema, harder for LLM to predict outcomes

### Recommendation

Start with **Option A** for simplicity — single prompt, multi-part response. If the action sequence is interrupted, remaining actions are lost (the character only gets to act out what they planned). Can evolve to Option B later if adaptive behavior is worth the extra cost.

- Add `player.action_budget` dict (configurable, with defaults)
- Reset budgets at the start of each character's turn in `turn-queue.js`
- Check budget in `routes/action.py` before executing the command
- Return an error if budget is exhausted: "You're out of actions this turn."
- Free actions have a soft cap (log a warning but don't block unless over ~5+)
- Reactions are checked in the agent loop when processing other characters' actions
- `engine/tick_manager.py` resets budgets via `apply_turn()`

## Related

- [[todo/gameplay/task-131-stateful-actions-over-time|task-131: Stateful actions]] — rest/sleep become stateful
- `engine/tick_manager.py` — existing time/energy costs
- `static/js/agent/turn-queue.js` — turn cycle management
- `routes/action.py` — verb dispatch



---

## todo/gameplay/task-410-food-renewal-foraging-and-week-scale-supply.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-410: Food renewal, foraging, and week-scale consumable supply

**Filed:** 2026-09-19  
**Depends on:** task-399 (background runner); task-408 (clean scenario data);
**task-406** (standing-item `on_tick` — see below).

## Goal

A settled camp can feed 23 characters for a week without supply collapse, via
**plant items that grow resources on a timer**.

## Mechanism (decided)

A plant is an item (bush, nut tree, mushroom log) with a growth counter:

1. `on_tick` on the plant adds +1 to its growth counter.
2. When growth reaches 100, spawn a related item (berries / nuts / mushrooms)
   **contained in the plant** ("relation is on the bush").
3. Reset growth to 0.
4. Cap: the plant stops spawning while it already holds ≥10 of its produce.

### Important: use `parameters.growth`, not `uses`

The original idea used the item's `uses`, but `uses` is **remaining charges /
durability**, not a counter:

- `handle_drain` / burn-out treat `uses` reaching 0 as depleted
  (`engine/effect_handlers/equipment.py:105–126`, `engine/tick_manager.py:650–692`).
- `handle_consume_item` and `crafting` **remove the node** at `uses <= 0`
  (`equipment.py:167–173`, `engine/crafting.py:131–136`).
- examine/stacking/carry-weight read `uses`/`max_uses` as durability
  (`engine/items/examine_actions.py:275`, `engine/items/stacking.py:18`,
  `engine/items/carry_weight.py:82–86`).

Using `uses` 0→100 would make the bush look "broken/empty" and risk removal
paths. Instead use the existing generic counter effect:
`adjust_parameter` / `set_parameter` on `parameters` (`engine/effect_handlers/properties.py:32–60`),
which is purpose-built for gauges and works on any node type. `uses` stays what
it is for actual consumables.

### Dependency on task-406 — SATISFIED

A plant standing in a room is not carried and not lit/on, so it used to never be
ticked (`tick_manager` only ticked carried/equipped and lit/on items). **task-406
landed**: `engine/tick_manager.py:745-757` now fires standing-item `on_tick`
triggers exactly once, skipping anything the carried/equipped and lit/on loops
already handled, so there is no double-fire. The growth trigger is buildable now.

### Tag trap: the plant must not be tagged as food

Consumption mechanics do **not** consult tags — `_consume_here`
(`engine/background_simulation.py`) decrements `count` if >1, else `uses` if >1,
and otherwise **removes the node**; `handle_consume_item` and crafting remove at
`uses <= 0`. Tags only decide how consumption *finds* a target
(`FOOD_TAGS`/`DRINK_TAGS`).

So if the bush itself carried a `food` tag, a hungry character would try to eat
the bush and the plant would be deleted. The **plant stays untagged**; only its
**produce** carries the food tags, and produce stacks as `count: N` (a handful
consumed one at a time, the node removed on the last one).

### Gating conditions (added 2026-09-21)

The mechanism needed two condition types that did not exist:

- `parameter_reached` — compares a gauge in the node's `parameters` dict
  (`key`, `value`, `op`, default `gte`). There was only `uses_reached`, which keys
  on `uses` — the very field that must not hold the counter.
- `contains_count` — counts what a container holds, optionally filtered by
  name/id. `op: "lt"` is the produce cap.

Both are implemented in `engine/triggers/condition_tree.py`, registered in
`engine/trigger_validator.py`, and covered by
`tests/test_gauge_trigger_conditions.py`.

## Slices (widened 2026-09-21: this is renewable world sources, not only food)

A **spawner is a renewable source that produces entities without consuming
itself.** Two independent axes — trigger (`on_tick` passive vs `on_use` active)
and product (item vs character):

|  | produces an item | produces a character |
|---|---|---|
| `on_tick` | berry bush, mushroom log | rabbit hole, deer trail |
| `on_use` | fishing spot, snare → caught rabbit | — |

1. **Passive item sources** — plants. **DONE** (see below): no engine work beyond
   the two conditions and the `per: "minute"` mode.
2. **Active item sources** — fishing spot, snare: `on_use` + `skill_check` →
   `spawn_item`. No new engine work; data only.
3. **`tagged_count` condition** — count tagged entities in an area. Required for
   slice 4: `contains_count` counts items *inside* a node, but a rabbit hole's
   rabbits are loose, so nothing caps them and an `on_tick` spawner floods the map.
4. **Character sources** — library creature templates (rabbit, deer), spawn cap,
   and a **death path that yields a carcass**. A cap without a death path is a
   dead end: the fourth rabbit ends the population forever. Kill/hunt resolves on
   the creature; the carcass is what a dead creature drops — do **not** give a
   trail a direct "survival check → carcass" shortcut, or the node becomes a meat
   dispenser the moment the player watches it.

## Changes

1. Implement the plant pattern with `parameters.growth` + `adjust_parameter`
   (+1 per tick), a `growth >= 100` condition (`parameter_reached`), `spawn_item`
   into the plant (`into: "container"`), `set_parameter growth 0`, and a
   `< 10 produce` cap (`contains_count` with `op: "lt"`). The plant itself carries
   **no** food tags; only its produce does.
2. Reconcile consumption against per-minute need rates (`vital_rates.py`): a
   character at Hunger ~3 weeks needs only a small amount per day.
3. Renewal uses existing spawn/consume rules, is capped, deterministic under a
   seed, and visible in the trace.
4. Ship at least a few authored plants in the goblin camp so the camp is
   sustainable.

## Acceptance

- A **7-day** background-only soak of the goblin camp ends with all 23 alive, or
  every death is attributable to an authored cause and documented — not supply
  collapse.
- Food counts stabilize instead of monotonically falling to zero.
- A plant never exceeds 10 produce and never grows past its cap; growth resets
  cleanly at 100.
- Deterministic under a fixed seed; spawned food is trace-visible.
- Plant items remain intact (not removed) as their counters move.

## Slice 1 result (2026-09-21)

Five berry bushes authored into the camp via `tools/add_renewable_sources.py`
(3 in Deep Forest, 1 at the Water Source, 1 on the Camp Entrance Trail). Each is
an untagged standing item with `parameters.growth`, a `parameter_reached` gate at
100, a `contains_count` cap of 10, and `per: "minute"` on the increment so growth
measures game time rather than ticks.

```
                 before plants      after
 1 min/tick:   23/23 alive        23/23 alive
15 min/tick:   21/23 (2 starved)  23/23 alive
 food over a week:  4 -> 0           4 -> 50
 hungriest alive:   100              49
```

Identical at 1 and 15 min/tick, which is the point.

Two blockers found and fixed on the way, both broader than plants:

- **`_find_consumable` only saw items with an `in` edge to the area**, so food in
  any container was unreachable and the background tier could starve beside a full
  store. It now traverses every spatial relation (`in`/`on`/`under`/`behind`/
  `beside`/`at`) plus one level of nesting, and `_areas_with` (which decides where
  a forager *travels*) does the same — otherwise nobody walks to the forest.
- **`_is_consumable`'s action fallback accepted `eat` OR `drink`**, so a hungry
  character ate a water skin and Hunger was satisfied. Intent is now threaded
  from the need/consume kind, so food is not drink.

Also: `_spawn_library_item_node` was dropping `parameters` entirely, so any
gauge-carrying item lost its counter at placement, and it now accepts an explicit
`node_id` so authored placement gets stable, re-runnable ids.

## Non-goals

- A market economy, trade pricing, or detailed nutrition.
- Repurposing `uses` for anything but remaining charges.

## Verification

- Extend `tools/soak_sim.py` reporting with food/drink counts over time.
- A 7-day soak run with the supply curve recorded in the progress doc.
- Unit test: growth ticks to 100, spawns, resets, and respects the 10-item cap.



---

## todo/gameplay/task-414-batch-time-advance-and-nonblocking-human.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-414: Server-side batch time advance and non-blocking human

**Filed:** 2026-09-19  
**Related:** task-464 (player-facing Fast-forward / Wait mode) builds the UX, human
freeze, and "while you waited" summary on top of this transport.  
**Depends on:** task-399 / task-409 (deterministic plan layer), task-411
(attended set), task-412 (promotion boundary).  
**Evidence:** `static/js/agent-engine.js:862–869`, `static/js/agent/turn-queue.js:151–158`,
`routes/action_handlers.py:1129–1132`, `tools/soak_sim.py:232`.

## Goal

Let the **server** advance N in-game minutes in one request, so a long run does
not need the browser as metronome — without changing turn ordering or action
rules.

## Why (the real bottleneck)

The browser drives the whole world today:

1. `agent-engine.js:862–869` — `while (config.running)` calls `step()` for one
   character, then `await setTimeout(2000)` (800 ms in simultaneous mode).
2. `turn-queue.js:151–158` — `advance()` increments the index; wrapping to 0
   calls `endTurn()`.
3. `endTurn()` → `POST /api/turn/apply` → `handle_apply_turn_decay` →
   `world.tick_turn()` (`routes/action_handlers.py:1129–1132`).

So one `tick_turn()` = one in-game minute **and** only fires once all ~23
characters have acted, with a hardcoded pause per step. A week is
10,080 wraps × 23 steps × 2 s ≈ 128 h of wall clock *before any LLM call*.
That, not model cost, is why a week cannot run interactively.

Two loops are currently fused:

| Loop | Owner | Cost | Contents |
|---|---|---|---|
| **Time** — `tick_turn()` | server | cheap | decay, vitals, environment, triggers, conditions, background sim |
| **Action** — decide + act | browser today | expensive | LLM / human / simple_npc action |

## Model (decided)

Add `POST /api/world/advance {ticks: N}` that runs `tick_turn()` N times
server-side in one request and returns a **bounded summary** (clock, deaths,
notable trace), not the full log. `soak_sim.py:232` already proves the
library-level loop; this lifts it into the app.

- **Backgrounded characters** are run by the deterministic plan/schedule layer
  (task-399 / task-409) — no LLM.
- **Attended characters continue their current server-side plan** during the
  batch (decided). The plan executor acts; the LLM is consulted only at the next
  decision boundary or on promotion (task-412). No LLM call per tick.
- The interactive per-character loop is unchanged; batch is an additional path.

## Pacing

The 2000 ms step sleep (`agent-engine.js:868`) is **legacy UI pacing**, present
since the initial public release (`170d5f1`); the 800 ms simultaneous branch was
added in `314d74b` (1.2.0, off by default) with no design note. It is separate
from the real throttle, `static/js/agent/rate-limiter.js`, enforced inside
`step()` at `agent-engine.js:412–425` from `config.rpmLimit`. Keep it for
readability, but make it **configurable**; the batch path uses no delay rather
than removing the sleep. It is **not needed** for correctness (each `step()` is
awaited) or for rate limiting. Two refinements: skip the delay when the step
already took longer than it (an LLM call is its own pacing), and expose it as a
setting (default ~2s, `0` = fast-forward).

## Non-blocking human

`HumanTurnComposer.request()` (`agent-engine.js:270`) waits indefinitely for
input. A batch needs a no-human roster option or a turn timeout that
resolves/defers the human turn.

## Changes

1. `POST /api/world/advance {ticks: N}` with a bounded summary response.
2. Attended-character **plan continuation** during batch (LLM only at
   boundaries).
3. Configurable step delay (interactive default keeps 2 s; batch uses 0).
4. Non-blocking human policy (no-human roster or timeout).
5. Do not change clock, `turn_number`, or `tick_turn` semantics.

## Acceptance

- `advance(N)` advances the clock by N ticks and returns a bounded summary.
- With attended characters, their current plan continues through the batch; no
  LLM call per tick, and the LLM is re-consulted at the next decision boundary.
- A present human does not stall a batch beyond the chosen timeout/no-human
  policy.
- Clock, `turn_number`, and `tick_turn` semantics unchanged (one tick = one
  in-game minute, all characters processed).
- Background and foreground characters behave consistently before/after a batch.

## Non-goals

- Running LLM actions inside the batch loop.
- A UI for replay/observation (task-415).

## Verification

- Unit: `advance(N)` advances the clock by N and processes each character the
  expected number of times; attended plan continuation with no LLM call; human
  timeout resolves.
- Perf: a multi-thousand-tick `advance` runs in seconds with no browser.



---

## todo/gameplay/task-424-data-driven-consumption-in-background.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-424: Background consumption uses the authored path (bread vs glass)

**Filed:** 2026-09-21  
**Depends on:** task-410 (renewable sources — the same `_find_consumable` path).  
**Relates:** `engine/items/consume_actions.py`, `engine/background_simulation.py`.

## Scoping notes (2026-09-21, measured)

Two things this task did not know, both of which change its shape. It is **three
pieces, not one**, and the first piece on its own is invisible.

**1. Almost nothing authors its own consumption.** Of ~40 edible/drinkable library
items, only six have an `on_eat`/`on_drink` trigger (`rations_of_dried_meat`,
`water_pitcher`, `wheel_of_cheese`, and three Taco Bell items). The rest are
tag-only, and `_consume_item` accepts them on the tag alone — so with the authored
path they would fire no effect and never deplete: an infinite loaf. The hardcoded
depletion is currently the *only* thing making camp food finite.

**2. The camp places five consumables**, not a sprawling inventory:
`item_berries`, `item_bread`, `item_dried_meat`, `item_mushrooms` (food) and
`item_water_skin` (drink) — and none of them has a trigger today. So the data pass
is small and tractable, and it is what makes the change *visible*; the code half
alone would leave the camp on the fallback and change nothing observable.

**3. "A glass empties and persists" needs a mechanism that does not exist yet.**
`uses` reaching 0 is handled generically in the *use* path
(`items/use_actions.py`, which detaches the item from its area) and for **lit**
items (`tick_manager` fires `on_depleted` under `if is_lit`) — but **not** in the
consume path. `_consume_item` relies on the item calling `adjust_uses`. So a
drinkable container cannot currently author "at 0 charges, become empty and stay
in the world" through consumption: that generic depletion hook is part of this
task, and the acceptance item about the empty glass depends on it.

Suggested order: the code delegation (a) → the generic `uses == 0 → on_depleted /
set_state` hook (c) → the data pass on the five camp consumables (b). Only then
retire `MEAL_RESTORE`/`DRINK_RESTORE`, and the soak should be unchanged because
until (b) lands every camp item is still on the fallback.

## Problem

Consumption has two mechanisms that disagree:

- **Player path** (`engine/items/consume_actions.py:consume_item`) is **data-driven**.
  It fires the item's `on_eat`/`on_drink` triggers, applies the action cost, records
  a turn event, and then **stops** — depletion is the item's own business via
  `adjust_uses`, `set_state`, or `rename`. So bread can be destroyed, a glass can
  *empty and persist*, and a container can be refillable, because the item authors it.
- **Background path** (`background_simulation._consume_here`) is **hardcoded**:
  `count - 1` → `uses - 1` → **remove the node**. It ignores authored triggers
  entirely.

So the background tier cannot empty a container, destroys anything with
`uses == -1` that it consumes, and forced the wash-spot fixture (task-410) to avoid
the `water` tag purely to escape deletion.

## Goal

One consumption path. The background tier calls the authored one, with the active
player swapped in for the decision (the same trick `_travel_toward` already uses
for movement), so a glass empties, a skin keeps its charges, and bread is eaten.

## Changes

1. `_consume_here` delegates to the item-consume path instead of hardcoding
   depletion. Keep the current behaviour only as a degenerate fallback for items
   with **no** authored consumption triggers, and log when it is taken.
2. **Data pass:** consumables must author their own effect, because the vital
   restore currently comes from the background hardcode
   (`MEAL_RESTORE = 45`, `DRINK_RESTORE = 50`). Each food/drink item gains an
   `on_eat`/`on_drink` trigger with `adjust_vital` (Hunger/Thirst), plus
   `adjust_uses` and an empty/finished state where it should persist.
3. Add the missing pattern: a **drinkable container** authors
   `uses_reached 0 → set_state empty` (+ optional `rename`), so it survives being
   drunk from. `uses` is charges/durability, never a gauge (task-410).
4. Only then retire `MEAL_RESTORE`/`DRINK_RESTORE` from the background tier.

## Acceptance

- Drinking from a glass leaves an empty glass in the world; eating bread removes it.
- An item with `uses: -1` is never destroyed by being consumed.
- A refillable container can be refilled and drunk again.
- Authored `on_eat`/`on_drink` triggers fire for background characters exactly as
  they do for the player, and the trace shows the same reason tags.
- Camp food supply behaviour is unchanged from task-410 (still 23/23 over a week).

## Non-goals

- New consumption verbs or nutrition detail.
- Changing what counts as food/drink (`FOOD_TAGS`/`DRINK_TAGS`).
- Refill mechanics beyond making them possible in data.

## Verification

- Unit: `_consume_here` on a container item that authors an empty state leaves the
  node; on an item with no triggers it falls back and says so.
- Unit: background eat fires the item's `adjust_vital` (Hunger drops by the
  authored amount, not by a constant).
- Soak: a week at 1 and 15 min/tick, survival and food counts unchanged vs
  task-410's result.



---

## todo/gameplay/task-426-plan-archetypes-and-group-goals.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-426: Plan archetypes and group goals (hunt, raid, gather, haul)

**Filed:** 2026-09-21  
**Depends on:** task-409 (deterministic planner + schedule model), task-403
(knowledge base — a plan can only use facts the character knows), task-417
(co-presence).  
**Relates:** task-425 (novelty), task-410 (sources to gather from).

## Gap

task-409 specifies a **per-step** goal-directed planner: given schedule + goals +
needs + traits + relationships, pick the next step (work/wait/travel/consume/
social) and execute it. That covers a *timetable* and a *reactive chooser*.

It does **not** cover either of the two things that make the world feel alive:

1. **Multi-step plans** — "go to the area with X → take X → go to the target area
   → drop X". Three or four steps to reach a state, not one.
2. **Group goals** — a leader's goal *assigned* to members with a shared rally
   point and time. A raid, a hunting party, a work gang.

## Design: authored templates, algorithmic selection

The plan is **data**, not reasoning: a small library of templates, each a short
ordered step list with preconditions. Selection is the algorithmic part — who can
do it, when, with whom, where — scored from needs, traits, relationships, role,
and *known* facts.

| archetype | shape |
|---|---|
| `haul` | here → take target item → travel to sink → drop |
| `gather` | travel to a source (task-410) → take/forage → return |
| `hunt` | travel to known game → hunt (skill check) → take carcass → return |
| `raid` | recon → gather participants → march → strike → carry loot → disperse |
| `build`, `cook` | fetch inputs → combine at a station |

Author the first two well (`haul` = Mikka's scrap run, `gather` = the
foragers) rather than sketching all six.

**Group goals** are a record, not a plan: `{leader, goal, participants[],
rally_area, rally_time}`. The leader's plan assigns members a goal ("be at the
rally area by T"); each member plans *locally* to satisfy it. Emergence comes
from goal propagation plus shared knowledge, not from the planner being clever —
most of the interesting behaviour falls out of one participant starving mid-march
and peeling off.

## Constraints

- **Plans are stored and executed, not recomputed per tick.** Plan once (or on
  invalidation), advance a step each action. Replan on completion, a broken
  precondition, or a critical need. This is what keeps it affordable at scale.
- **Determinism**: seeded selection, reproducible replay.
- **Bounded**: max steps per plan, max participants, and a hard fallback to the
  task-409 per-step planner if a plan cannot be built or completed.
- **Knowledge-gated**: a plan may only use facts the character knows (task-403) —
  you cannot raid a place you have never seen, or fetch from an area you do not
  know holds the thing.
- **Own the set-pieces.** A raid is a story beat and must be reliable; do not let
  it be fully emergent. Search/templates for the small stuff, authored shape for
  the big stuff.

## Acceptance

- Mikka's scrap run works end to end as a `haul`: plan → travel → take → travel →
  drop, visible in the trace with the plan's identity.
- A plan survives a *repeated* need interruption (eat, then resume) rather than
  being lost.
- A plan is abandoned cleanly when its precondition breaks (the item is gone),
  with a replan, not a freeze.
- A group goal produces several characters converging on a rally area, and the
  party degrades visibly when one participant drops out.
- Same seed → same plans and same sequence.

## Non-goals

- Full GOAP search over the whole action set. Templates first; search only if a
  goal genuinely cannot be expressed as a template.
- LLM-authored plans in the tick loop.
- Negotiation, politics, or multi-faction strategy.



---

## todo/gameplay/task-427-creature-spawners-and-population-caps.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-427: Creature spawners, population caps, and a death path

**Filed:** 2026-09-21  
**Depends on:** task-410 (source/fixture pattern, and slice 2 for active sources).  
**Relates:** `spawn_character` (`engine/effect_handlers/spawn.py:195`), combat.

## Gap

task-410 covers **item** sources (plants) and, in slice 2, active item sources
(fishing spot, snare). It records character sources as slice 4 without a task of
their own — and they need three things item sources do not.

A rabbit hole should either breed rabbits or be snared; a deer trail should
produce a deer you can hunt. Those are **character** spawns, and:

1. **Nothing caps them.** `contains_count` counts items *inside* a node, but a
   rabbit hole's rabbits are loose in the world. Without a live count of tagged
   entities an `on_tick` spawner floods the map in a week.
2. **Nothing kills them.** A cap only works if creatures also leave: hunted,
   starved, eaten, old. Without a death path the fourth rabbit ends the
   population forever.
3. **Killing has to yield something.** A carcass is what a dead creature *drops*.
   Do **not** shortcut a trail to "survival check → carcass" — that is a meat
   dispenser the moment the player watches it, which is the background/foreground
   seam we have been careful about all along.

## Design

- **`tagged_count` condition** — count tagged entities in an area (or the world):
  `{"type":"tagged_count","target_has_tag":"rabbit","area":"current","value":4,"op":"lt"}`.
  Generic beyond creatures: "how many goblins are in this room". Register in
  `CONDITION_TYPES` and document with the other conditions.
- **Creature templates** — a library character per species (`rabbit`, `deer`) with
  species tags, vitals, and the behaviour needed to wander/graze. Spawned with
  `spawn_character {character_id, area}`.
- **Spawners are sources, not characters**: an untagged standing fixture with the
  growth-counter pattern (`parameter_reached` + `tagged_count` + `spawn_character`),
  so a burrow is not edible and cannot be hunted.
- **Death yields a carcass** — a loot/drop-on-death hook in the combat/death path,
  producing a food item. Audit `engine/combat.py` first: it is not confirmed today
  that death drops anything.
- **Lifetime** — creatures age/die, and starvation via task-409's needs so the
  population self-limits rather than needing a cull.

## Acceptance

- A burrow spawns a rabbit only while the area holds fewer than N tagged rabbits.
- Killing a creature yields a carcass item that then behaves as ordinary food
  (consumption via task-424's path).
- Population reaches a stable band over a week rather than 0 or unbounded.
- A creature spawner is never itself edible or huntable.
- Deterministic under a fixed seed.

## Non-goals

- Ecology, predator/prey modelling, breeding genetics, or taming.
- Multi-species food webs.
- Generated creature lineages (task-404 is life *experiences*, not species).



---

## todo/gameplay/task-429-housekeeping-template-data-and-asset-weight.md

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



---

## todo/gameplay/task-430-retire-visited-areas-and-discovered-items.md

---
type: task
status: todo
area: gameplay
priority: low
---

# task-430: Retire `visited_areas` and `discovered_items`

**Filed:** 2026-09-21  
**Follows:** task-425 (novelty recovery and recreation), task-403 (observation
memories).

## Why this exists

task-425 replaced both sets as the *novelty* source — novelty now reads the
observation memory (`player.observation_tick`). But the sets were left in place
because they still have consumers, and both are still written so those consumers
keep working. Two structures describing the same thing (what a character has
experienced) is exactly the drift task-425 set out to remove, so this finishes
the job:

| consumer | what it reads | should read instead |
|---|---|---|
| `engine/spatial_memory.py` `build_known_routes(current_area, visited_areas)` | area **names** the character has been in | live `kind == "area"` observations (`observation_memory` / `memory_index`) |
| `engine/tick_manager.py:~313` `adventurous` micro-modifier | "is the current area new?" | `player.has_seen(area_id)` — but see the ordering note below |
| `engine/items/take_drop_actions.py` | bookkeeping only (novelty no longer reads it) | drop entirely |
| `routes/memories.py` `.../memories/spatial` | `player.visited_areas` → `build_known_routes` | same derivation as spatial memory |
| `static/js/agent/prompt-builder/room-context.js`, `memory-context.js`, `contextual-actions.js` | `player.discovered_items` for prompt context | `memory_index` / observation memories, or a server-rendered list |
| `engine/serialization.py` | round-trips both | drop, keeping the tolerant read |

## The one real snag

`visited_areas` is **area names**, while observation subjects are **area node
ids**, and `location` on an observation is also the area name. So "areas I have
been in" derives as either

- `{m["location"] for m in player.memories if m.get("kind") == "area" and not m.get("superseded_by")}`
  — a scan over memories, fine for the prompt path (`/api/...memories/spatial`)
  but not in the tick loop; or
- resolve each `kind == "area"` subject id to its node and take the name, via
  `memory_index` — no scan, but needs the graph.

Prefer the second where the graph is reachable.

**Ordering note on `adventurous`:** today `visited_areas.add()` happens *before*
the `adventurous` check, so the bonus is for the first-ever entry only, and
`observe_area` has already stamped the observation by then, so `has_seen` is
`True` on that first entry — a naive swap inverts the behaviour. Either read the
freshness `observe_area` returns (it is pre-refresh and already available in
`movement.py`) or accept the change deliberately.

## Acceptance

- `grep -rn "visited_areas\|discovered_items"` returns only the tolerant
  legacy read in `engine/serialization.py`.
- An old save carrying both sets loads without error and its known-route block
  is non-empty for areas the character has actually been in.
- The `adventurous` trait still pays on a first entry and not on a repeat.
- The turn composer's prompt still lists previously-seen items (or the reason it
  no longer needs to is recorded).
- A background week at 1 and 15 min/tick is unchanged in survival, with
  Entertainment still above 0 and settling.

## Non-goals

- Any change to the novelty curve or the observation model.
- Replacing `SpatialMemory` — only its input.



---

## todo/gameplay/task-436-task-durations-and-remove-action-cost-time.md

# task-436 — Task durations, and removing `ACTION_COSTS.time`

**Status:** done, except one measured residual. The per-turn action budget is
replaced by the timeframe-and-flow model, `ACTION_COSTS.time` is gone, and tasks
longer than their timeframe now span turns as minute-authored activities. T=1 and
T=15 agree on survival and Hunger and within ~2.5 points on five further vitals;
**Energy remains ~10 apart and its cause is not identified** (see the final
sections). Two earlier gating attempts measured worse and were reverted — do not
repeat them.
**Area:** gameplay / time
**Depends on:** [[Simulation Model]] (the timeframe-and-flow model)
**Related:** task-352 (action economy), task-414 (batch advance), task-131 (stateful actions over time), task-244 (human turn parameters)

## Why

[[Simulation Model]] commits to two things:

1. **Delete `ACTION_COSTS.time`** and `_action_time_consumed`. Atomic actions
   (look, take, hit, open) are one minute; arbitrary per-action time multipliers
   are legacy.
2. **Duration belongs on tasks** — travelling a route, sleeping, working, waiting —
   not on atomic actions. This is the seam where a player's ~20–40 actions absorb
   the world's 1,440 minutes, and it is what makes a day pass in a believable
   number of turns without any decay rate changing.

## What `time` actually does today (verified)

`ACTION_COSTS` (`virtual_world_engine.py:110-117`) gives each action a `time` and
one or more vital costs. `apply_action` (`engine/tick_manager.py:140-153`) uses
`time` for **two different jobs**:

```python
time_ticks = int(cost.get("time", 0))
...
total_delta = delta * (time_ticks if time_ticks > 0 else 1)   # job 1: multiplier
target.vitals[key] = max(0, min(100, target.vitals[key] - total_delta))
if time_ticks > 0:
    self.player_manager._action_time_consumed = True           # job 2: flag
else:
    self.player_manager._action_time_consumed = False
```

- **Job 1 — drain multiplier.** The `energy` values are *per-minute rates*, not
  totals. `move: {time: 1, energy: 1}` → 1 energy, but `fumble: {time: 2,
  energy: 3}` → **6** energy.
- **Job 2 — time-consumed flag.** `open`/`close` have `time: 0` and so
  deliberately consume no clock time. Read at `tools/game_tools.py:101`
  (`if not getattr(world, '_action_time_consumed', False)`), also reset at
  `routes/action_handlers.py:212` and set at `engine/tick_manager.py:993` (rest).
  Declared at `virtual_world_engine.py:119`.

## `time: 0` is a call-site idiom, and may be in the data

`time` is not only a table field. Because `apply_action` treats it as
`cost.get("time", 0)`, an **absent or zero** `time` means *absolute cost, no clock
advance*, while `time >= 1` means *multiply the cost, and advance*. Call sites rely
on that:

- `engine/movement.py:754` — `{"energy": encumbrance_cost, "time": 0}`
- `engine/movement.py:830` — `{"energy": 4, "time": 0}`
- `tests/test_traits.py:134` — `{"energy": 2, "time": 0}`
- `engine/movement.py:1029` — passes `way_node.properties.get("cost", {})` through,
  so **way cost blocks in scenario data may carry `time`** and need auditing

So the removal is: fold the multiplier into absolute costs, introduce an explicit
`consumes_time` field (default preserving today's absent-means-false behaviour),
update those call sites, and sweep `cost` blocks in `data/scenarios/*.json`.

## Therefore

Deleting `time` is **not** a mechanical removal:

- Every multi-tick action's vital cost silently halves unless the magnitudes are
  folded into the cost table (e.g. `fumble` becomes `energy: 6`, not `3`).
- Which actions consume clock time changes. Under the new model every atomic
  action takes one minute, so `_action_time_consumed` becomes uniformly true and
  the flag is meaningless — it should be deleted and the caller should advance
  unconditionally, **but that is a clock-semantics change and must be verified
  against `rest`/sleep**, which sets the flag deliberately at `:993`.

## Progress — steps 5–6 done (the flow model)

`actions_per_turn` (the per-turn action *budget*) is replaced by `minutes_in_turn`
(the timeframe) plus `TASK_MINUTES` (each action's duration). `process_due` fills
the timeframe: each action consumes its duration until the timeframe is full or
`_act` reports nothing to do. `TASK_MINUTES["travel"]` is 1, so a walk repeats and
fills a timeframe; every other task is longer and is recorded in `served`, so a
task is done **once per timeframe**. The `_action_credit` banking machinery is
gone entirely: nothing accumulates.

### Correction: this task overstated the bug

Steps 1–4 were motivated by "a 30-minute turn becomes thirty meals, ~1,440 actions
per character per day". **That was wrong.** `_act` returns early when no need is
past its threshold, so the old budget burned `T` *passes through the need ladder*
but produced roughly the same *actions*. The 1,440 figure was passes, not actions.
Measured over one game week at 15 min/turn, the old model gave 23/23 alive with
the same average Hunger (34.2) as the new one.

The old model was therefore not broken so much as **incoherent**: it granted
actions per turn rather than filling a duration, and it re-ran the whole ladder
once per game minute whether or not anything was due.

### Measured effect (one game week, Kraktooth camp, `--background-all`)

Vitals at 15 min/turn, old vs new: Energy 69.8 → **77.3**, Sanity 80.4 → **85.9**,
Social 75.8 → **81.0**, Hygiene 72.0 → **74.3**, Entertainment 40.2 → **42.5**.
Better across the board at equal survival (23/23). A long timeframe can chain
*different* tasks within one turn instead of repeatedly re-checking one need.

Resolution independence, new model, T=1 vs T=15 over the same game week: survival
23/23 both, Hunger 34.2 both, Thirst 17.3 / 16.5, HP 96.8 / 97.7.

### Resolution dependence — root cause fixed; Energy gap remains

**Fixed.** The overdraft is gone: a task longer than what is left of the timeframe
now starts an activity authored in **minutes** (`_begin_task`), so a ten-minute
meal costs ten minutes of game time and occupies ten turns at a T=1 clock, most of
one turn at T=15. `ActivitySystem` gained `elapsed_minutes` / `duration_minutes`
alongside the legacy tick-based fields, and the task activity types were added to
`ACTIVITY_INTERRUPTIBLE` and `ACTIVITY_SKIP_TURNS` — the former being mandatory,
since a type missing from it never expires and strands the character busy.

Two traps hit while doing it, both worth knowing:

- `_begin_task` must not overwrite an activity a helper already opened.
  `_recuperate` starts a `resting` block with its duration correctly converted
  from minutes, and clobbering it broke `test_a_low_sanity_character_rests`.
- `duration_ticks` is a **turn** count and is the same unit trap this task exists
  to remove. `_recuperate` divides `SANITY_REST_MINUTES` by the tick length to get
  ticks, which is correct; anything else authoring `duration_ticks` directly is not.

**Measured, one game week, T=1 against T=15** (23/23 alive at both):

| | T=1 | T=15 |
| --- | --- | --- |
| Hunger | 34.2 | 34.2 |
| HP | 96.8 | 96.2 |
| Sanity | 83.3 | 82.0 |
| Entertainment | 39.2 | 40.5 |
| Social | 77.6 | 75.2 |
| Thirst | 17.5 | 15.0 |
| Hygiene | 78.4 | 72.9 |
| **Energy** | **65.8** | **76.1** |

Five of eight agree within ~2.5 points. **Energy is consistently ~10 apart across
every variant tried** (67.1/77.3, 61.9/73.7, 65.8/76.1), so it is a real remaining
mechanism rather than run-to-run noise — but its cause is **not** identified, and
the two earlier guesses about this area were both wrong. Do not repeat them. Sleep
is already open-ended (it ends at Energy 100, not on a duration), so the next
suspect is condition-based wake granularity: a wake test evaluated once per turn
oversleeps by up to T minutes, which a coarse clock cannot avoid without moving the
check inside the timeframe.

`served` remains the shipping intra-turn rule: best-measured of the three gating
schemes tried, and the simplest to reason about.

### The two gating experiments that failed (do not repeat)

Both were attempts to fix the resolution gap *before* it was understood, by
changing how a task is gated rather than how it is timed. Both measured worse and
were reverted:

1. **Gate on the action's own duration instead of `served`.** Energy 64.0 / 75.6,
   Thirst 17.6 / 12.1. Far too permissive — it lets a character above the thirst
   threshold drink every two minutes.
2. **A `TASK_COOLDOWN_MINUTES` routine table** (eat 240, drink 45, wash 480, …).
   Energy 60.7 / 80.3, Hygiene 55.8 / 69.3, against 67.1 / 77.3 and 77.8 / 74.3 for
   `served`. More "realistic" intervals, worse convergence, and plausibly worse
   play (goblins washing twice a day sit at Hygiene 56).

The gap was never a gating problem: at T=1 the timeframe is one minute, `eat`
reports 10, and the loop spent it anyway — so a character performed fifteen whole
tasks in fifteen minutes at T=1 while T=15 admitted only the two or three that fit.
The binding constraint at T=15 was the timeframe, which is why no cooldown value
could reconcile them.

### Cost

Coarser turns are much cheaper for the same game time: one game week took 17s at
15 min/turn against 2m43s at 1 min/turn (~2s/day vs ~23s/day), because the flow is
entered once per timeframe instead of once per game minute.

## Progress — steps 1–4 done

**Step 4 corrected this task's own premise.** The plan said to delete
`_action_time_consumed` because it would become uniformly true and therefore
meaningless. That was wrong. The flag had **two** sources, and only one was the
`time` field:

- `apply_action` set it from `cost["time"]` — the part that made *which* actions
  moved the clock an accident of the cost table. Removed.
- `rest()` sets it because `rest` loops `tick_turn` once per minute **itself**. It
  is the guard that stops the per-action layer adding a second minute on top of
  the hours just spent. Deleting it would have made a 60-minute rest cost 61.

So it was renamed `_clock_advanced_by_task` — its name now describes what it
guards rather than its old source — and it survives. Making `_ensure_tick`
unconditional (the obvious reading of "delete the flag") would have been a
silent off-by-one on every sleep. Caught by reading `rest()` before editing it,
and pinned by `test_rest_advances_the_clock_itself_and_is_marked_as_having_done_so`.

`ACTION_COSTS` entries are now bare `{"energy": N}`; the `consumes_time` field
this task added in step 1 was **also** removed, since it existed only to feed the
flag.

Full suite: 3186 passed. The 6 failures in `test_social_company.py` and
`test_tick_time_scaling.py` are pre-existing and order-dependent — they fail with
and without these changes, and a different subset fails each run.

## Progress — steps 1–3 done

`ACTION_COSTS` no longer carries `time`. Energy costs are absolute (`fumble` is
`energy: 6`, the 6 it always cost as 3 x `time: 2`), and "does this action take a
minute" is now the explicit `consumes_time` field, defaulting to false when absent
— matching the old absent-or-zero-`time` behaviour.

Verified **behaviour-preserving** by running a probe across `move`, `fumble`,
`open`, `take` and `look` against both the working tree and `HEAD`: identical
energy deltas and identical flag values in every case.

Two things the probe settled that this task had guessed at:

- `engine/movement.py`'s two overrides became `{"energy": N, "consumes_time":
  False}`, and `tests/test_traits.py` followed.
- **The data audit came back negative** — no `cost` block in `data/scenarios/*.json`
  or `data/library/**` carries `time`, so there is no data migration.
- The flag is read from the **world** (`world._action_time_consumed`), not from
  `PlayerManager`, despite `apply_action` assigning through
  `self.player_manager`. Worth clearing up when the flag is deleted.

New: `tests/test_action_costs.py` pins the split, including a structural check
that no cost entry regains a `time` key.

## Plan

1. Fold the multiplier into the cost table so vital costs are **absolute**:
   `move {energy: 1}`, `look {energy: 0}`, `use {energy: 1}`, `take {energy: 1}`,
   `drop {energy: 0}`, `fumble {energy: 6}`, `open`/`close` `{energy: 1}` (open/close
   now cost the minute they always took narratively).
2. Delete `time` from every `ACTION_COSTS` entry and drop the multiplier at
   `engine/tick_manager.py:140-149`.
3. Delete `_action_time_consumed` (declaration, both setters, the reader) and have
   the caller advance the clock unconditionally — **after** confirming `rest()`
   still advances exactly once for a sleep of N minutes.
4. Add **duration to tasks**, which is the actual feature: `travel` (a route),
   `sleep`/`rest`, `work` (a shift), `wait`. Duration is a property of the task,
   not a fudge factor on an atomic action.
5. Replace the per-turn action *budget* (`actions_per_turn = T` in
   `engine/background_simulation.py`) with the flow model: a turn is a timeframe,
   an action flow fills it, and the number of actions is emergent.

## Acceptance

- A soak at 1, 5 and 15 minutes-per-turn produces the same character behaviour at
  the same **game-day** — same meals, same sleeps, same deaths (if any).
- `rest(60)` advances the clock by exactly 60 game minutes, once.
- No character takes ~1,440 actions per game day.

## Notes

`docs/virtualWorld/dev_tasks/cancelled/task-14-action_costs_to_time.md` shows this
was intuited before and never landed.



---

## todo/gameplay/task-437-turn-order-source-of-truth-and-modes.md

# task-437 — One turn order, owned by the engine, with simultaneous as a mode

**Status:** todo
**Area:** gameplay / time / engine
**Depends on:** task-436 (timeframe-and-flow model — done)
**Absorbs:** task-310 (reroll initiative / random order), task-101 (simultaneous room turns)
**Related:** task-244 (human turn parameters), task-241, task-338 (turn queue docs)

## Why

There is no single answer to "who acts first", and the order that matters most is
the only one nobody chose.

Four orders exist today:

| Where | Order | Chosen by |
| --- | --- | --- |
| Frontend turn queue (`static/js/agent/turn-queue.js`) | sequential (alphabetical) / random / initiative | the player, via `config.turnOrder` |
| `BackgroundSimulation.process_due` | **dict insertion order** | nobody — an accident |
| `run_social_pass` | its own per-area order | nobody |
| `process_simple_npcs` | its own order | nobody |

So a character can be 3rd in the queue the UI shows and 19th in the order the
world actually resolves them — and the world's order is the one that decides who
gets the last food, the bed, or the clear path.

`turn_order` is also **dead data**: `tools/build_scenario.py:261` stamps
`"sequential"` into every scenario and **no Python reads it**.

### Measured evidence

Reversing the roster order in `process_due`, changing nothing else, moved a
one-game-week soak at T=15 as follows (survival unchanged at 23/23):

| | normal | reversed |
| --- | --- | --- |
| Energy | 76.1 | 80.1 |
| Thirst | 15.0 | 18.4 |
| Sanity | 82.0 | 78.3 |
| Entertainment | 40.5 | 38.2 |
| HP | 96.2 | 96.9 |

Insertion order is therefore a **material, invisible determinant** of outcomes.
That is the thing to remove: not because a metric drifted, but because the world
is quietly cheating in favour of whoever was registered first.

## The dial

One setting, four modes, answering one question — *how does a timeframe resolve?*

- **sequential** — one fixed order, applied serially.
- **random** — a fresh seeded sequence each timeframe, applied serially.
- **initiative** — a seeded d20+DEX sequence each timeframe, applied serially.
- **simultaneous** — no sequence: resolve against a snapshot, commit together.

Three share an implementation shape; `simultaneous` does not. That is a difference
in mechanism, not in kind, so it belongs on the same dial — which also means any
two modes can be A/B'd against each other, which is how the "does order actually
matter to how this feels" question gets answered.

**Simultaneous is not a reason to skip contention work**: handling only *contended*
resources (the last item, one bed, a shared door) is a legitimate internal
optimisation of the mode, not a different mode.

## Design

1. **The engine resolves and stores.** At the start of a timeframe the engine
   resolves the order once — seeded — and **stores the resolved list for that
   timeframe** as a fact. The simulation reads it, the API exposes it, the UI reads
   it.
   - Do **not** let both sides compute it. If the server shuffles and the client
     shuffles independently you get the current divergence plus non-determinism.
     **Share the data, not the logic.**
2. **Ids, not names.** The queue is name-based today, which contradicts
   `[[Simulation Model]]` (`id_backed_character_identity`, task-316) and breaks the
   moment two characters share a name.
3. **Read `turn_order` for real.** The engine reads it from the scenario/engine
   config, so the setting stops being dead data and the client-side value stops
   being the authority.
4. **Frontend keeps the cursor, loses the ordering.** `currentTurnIndex`,
   `advance()`, the turn panel: presentation, stays. `initialize()`'s sorting,
   `reshuffleRandom()`, `rerollInitiatives()`: deleted, replaced by reading the
   server's list. `config.turnOrder` becomes a display of the server's mode, not a
   client-side decision.
5. **`simultaneous` implementation, in two stages.**
   - **Stage 1 — snapshot decisions, serial deterministic commit.** Each
     character's flow reads the world as it stood at timeframe start, then effects
     apply in a fixed commit order. Cheap, removes the *information* advantage
     (which is what the measurement above is measuring). Does **not** make
     contention fair: the commit order still decides who gets the last item.
   - **Stage 2 — intent/effect separation with explicit conflict resolution.**
     `_act` emits what the character *tries* to do; a commit step applies it and
     resolves collisions deterministically. This is the real thing, and it is what
     makes the mode's contract true.
6. **The contract, stated once, tested:** in `simultaneous`, the outcome does not
   depend on processing order. That is checkable — reverse the roster and the
   result must not move.
7. **Determinism is mandatory.** Conflict resolution, shuffles and initiative
   rolls must all be seeded, or soaks and tests stop being reproducible.

## The payoff beyond fairness

Intent/effect separation makes **"a player is an agent with a different
controller"** structurally true rather than merely asserted: human, agent, simple
NPC and soak NPC all emit the same kind of thing into the same resolver. Today
`_act` mutates the world directly, which is why the four levels *look* like four
different systems even though the model says they are one.

It also unifies the human turn with the timeframe: the player's action becomes an
intent folded into the same commit, instead of a special path.

## Acceptance

- The order the UI shows **is** the order the world resolves in.
- Reversing the roster changes nothing observable in `simultaneous` mode.
- Same seed + same scenario ⇒ identical outcomes, in every mode.
- `turn_order` is read by the engine and is no longer dead scenario data.
- No character is identified by name in the resolved order.

## Notes

`task-310` is already implemented on the frontend (`reshuffleRandom`,
`rerollInitiatives`) and sits in `review/` as though it were not. Its remaining
work is exactly step 1–4 above — moving the decision to the server. `task-101` is
step 5.



---

## todo/gameplay/task-453-save-format-schema-version-and-load-time-compatibility-migration.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-453: Save-format schema version and load-time compatibility/migration

**Filed:** 2026-09-22
**Related:** task-439, task-446, task-365

## Goal

Give the save/scenario payload an explicit **format schema version** and make load
check it, so a file written before a breaking format change can never load silently
wrong.

`_save_metadata.version` (from `APP_VERSION`, `routes/helpers.py:321`) is the **saving
app's** version, not a format marker. There is no compatibility check on either load
path (`POST /api/load`, `POST /api/load-game`). With `task-446` (id-first node
identity, in progress) and `task-439` (canonical area identity) changing how players
and areas are keyed, an old name-keyed save file already in `saves/` can be read
through new code and produce colliding or mis-attributed entries.

## Proposed shape

- Add `SCHEMA_VERSION` (single source, e.g. alongside `version.py`), stamped into
  `_save_metadata` / `_autosave_meta` and into scenario payloads written by
  `to_scenario_dict`/commit.
- On load, compare the file's schema version against the current one:
  - equal → load as today;
  - older and a registered migration exists → migrate in memory, load, and report
    "migrated from vN" to the caller/UI;
  - older with no migration, or newer than the app → refuse with a clear error
    (do not partially load).
- Keep `version` (app build) for display; keep it separate from `schema_version`.
- Migrations must be read-old/write-new and must not rewrite the source file unless a
  save/commit happens.

## Acceptance

- [ ] New saves carry an explicit `schema_version` distinct from the app `version`.
- [ ] Loading a save/scenario with a missing or older schema version either migrates
      (with a visible notice) or is refused with a specific error — never silently
      loaded as current.
- [ ] A save produced by a newer schema version than the running app is refused rather
      than misread.
- [ ] Existing autosave/scenario boot behavior is unchanged for same-version files.
- [ ] Migration of a legacy name-keyed payload cooperates with task-439/task-446
      (keys and display names both survive).

## Files

- `version.py` — schema version constant
- `routes/helpers.py` — `_save_game` metadata, `save_autosave` meta
- `routes/saveload.py` — `/api/load` and `/api/load-game` compatibility gate
- `engine/serialization.py` — migration hook in the load path
- `tests/test_saveload.py` — schema gate, migration, refusal coverage



---

## todo/gameplay/task-467-belief-based-travel-heading-budget-maps-and-hearsay.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-467: Belief-based travel: heading + budget, maps and hearsay

**Filed:** 2026-09-22
**Related:** task-464, task-466, task-403, task-398, task-9

## Goal

Travel to a destination held as a belief rather than a known node: heading plus time budget ('go west 2h') moves the character through the world, resolves whatever lies that way (including generated content, task-398/task-9) and validates the belief on arrival. Maps and directions gained from dialogue or items write knowledge (task-403) that upgrades a belief into a known route/area. Shares the heading + frontier primitive with Explore, and interrupts via task-466 (hazard, vital, interesting find).

## Acceptance

- TODO

## Progress 2026-09-22 — partial (route duration + heading step)

- [x] `engine/timeskip.route_hops()` / `travel_minutes()` — a known route's
  duration from hop count × `TASK_MINUTES["travel"]`, so travel is a real span
  rather than an arbitrary turn count. The HTTP route derives the span from the
  route when `minutes` is omitted (`POST /api/world/timeskip {intent:"travel",
  target:"..."}`).
- [x] Heading step (`_move_heading`) — "go west" moves through an exit whose
  label matches the heading.
- [ ] Belief destination: resolve a described/unknown target (task-403 knowledge)
  and validate it on arrival (found / found-not-there).
- [ ] Maps and hearsay writing knowledge that upgrades a belief to a known route.
- [ ] Generation-on-discovery at the frontier (task-398/task-9).

## Verification

`python -m pytest tests/test_timeskip.py::test_route_helpers_report_hop_duration -q` → passed.



---

## todo/gameplay/task-473-item-stacks-and-relational-piles-grouped-world-items.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-473: Item stacks and relational piles (grouped world items)

**Filed:** 2026-09-23
**Related:** task-471, task-470, task-424, task-9

## Goal

Group world items so a camp can hold a 50-use pile of raw meat or a herb pile of distinct herbs without hundreds of nodes. Two models: (a) HOMOGENEOUS STACK - one node carrying N uses; taking spawns one discrete item into the taker's inventory and decrements; placing a matching item (same key tags) adds a use and removes the node. (b) RELATIONAL PILE - a container holding distinct child items, so different herbs with different effects coexist and can be taken individually. Uses drive crafting/cooking (raw_meat + campfire -> cooked_meat, spending a use), reduce wild-item count, and keep soak search/forage output tidy. Needs: an explicit stack marker in the item schema, take-from-stack and merge-on-put in the item actions, capacity/weight interaction with containers, and save/load of uses.

## Acceptance

- TODO



---

## todo/gameplay/task-477-put-combat-and-grapple-on-the-central-check-system.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-477: Put combat and grapple on the central check system

**Filed:** 2026-09-23
**Related:** task-472, task-475

## Goal

Migrate attack rolls and grapple onto engine/checks.resolve and checks.opposed so combat inherits ability modifiers, condition-driven advantage/disadvantage and the degree/critical ladder, replacing the bespoke rolling in engine/combat.py and engine/grapple.py; expose the d20 breakdown in the combat log.

## Acceptance

- TODO



---

## todo/gameplay/task-478-perception-vs-investigation-nature-investigation-and-arcana-search-tables.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-478: Perception vs Investigation; Nature, Investigation and Arcana search tables

**Filed:** 2026-09-23
**Related:** task-471, task-472, task-474

## Goal

Separate noticing from searching: Perception spots something easy to miss, Investigation works out where to look and what it means (a two-step notice-then-search). Add search loot tables and forage-tagged content for Nature (reagents, tracks, safe plants), Investigation (documents, mechanisms, hidden caches) and Arcana (arcane items, anomalies), plus a small Medicine table for recognising a useful plant, so the skill list has content beyond Survival/Perception/History/Religion.

## Acceptance

- TODO



---

## todo/gameplay/task-482-timeskip-follow-ups-long-spans-leisure-vendors-explore-frontier.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-482: Timeskip follow-ups: long spans, leisure vendors, explore frontier

**Filed:** 2026-09-23
**Related:** task-464; task-467; task-398

## Goal

Deferred from task-464: spans beyond the 1,440-min route cap (soak-runner-style job), leisure buying from a vendor, and explore frontier preference tied to generation (task-398).

## Acceptance

- TODO



---

## todo/gameplay/task-483-search-affordance-findable-here-hints-per-area-forage-tables.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-483: Search affordance, findable-here hints, per-area forage tables

**Filed:** 2026-09-23
**Related:** task-471; task-470; task-473

## Goal

Deferred from task-471: a 'find <skill>' help/UI affordance, HUD hints for what could be found in an area, and a per-area override + JSON library surface for the forage tables instead of the code constant.

## Acceptance

- TODO



---

## todo/gameplay/task-494-container-examine-reveals-contents-and-chains-a-follow-up-action.md

---
type: task
status: todo
area: gameplay
priority: medium
---

# task-494: Container examine reveals contents and chains a follow-up action

**Filed:** 2026-09-23
**Related:** task-352, task-493

## Goal

Make container contents an explicit reveal and allow a two-step single turn: examine <container> marks its contents discovered (they render 'known' and become usable), and the examine can be followed by one item action (take/use) in the same turn, mirroring the dash multi-step precedent (engine/movement.py dash_to_area, tick_manager.py move/dash handling) and governed by action_costs. Decide whether carried-container contents stop being auto-listed before an examine. Belongs with the task-352 action-economy work.

## Acceptance

- `examine <container>` marks its contents discovered so they render as known (and, if decided, are only listed after the examine).
- One follow-up item action (take/use) may occur in the same turn as the examine, governed by `action_costs`, mirroring the dash multi-step path.
- Single-action turns are unchanged when no follow-up is taken.
- Tests cover: the reveal, a chained take/use, and no chaining when the follow-up is disallowed.



---

## todo/gameplay/task-99-room-grids-and-movement.md

---
group: Graph & Area UX
wiki: "[[World Building/Rooms & Areas]]"
---
# Task 99: Area Grids — Movement Costs, Size/Shape, and Pathfinding

**Status**: todo
**Priority**: Medium
**Filed**: 2026-07-24

## Summary

Currently areas are dimensionless nodes — you're either *in* a room or you're not. This task adds a 2D grid to areas, allowing movement costs, item positioning, and NPC pathfinding within areas.

## What Already Exists

- Rooms have `exits` with `blocked` state
- Movement is handled by `engine/movement.py` (directional, door-checking)
- Player manager tracks which room each character is in
- Some areas have environment properties (light, temp, etc.)

## What's Missing

### 1. Area Grid Data Model

Add a grid field to areas:
```python
room.grid = {
    "width": 10,
    "height": 10,
    "tiles": [
        ["floor", "floor", "wall", "floor", "floor", ...],
        ...
    ],
    "costs": {
        "floor": 1,
        "wall": 99,  # impassable
        "rubble": 3,
        "water": 2,
        "carpet": 1,
        "stairs": 0  # exit point
    },
    "items": {
        "item_rusty_key": {"x": 3, "y": 5},
        "item_candle": {"x": 1, "y": 1}
    },
    "characters": {
        "player_traveler": {"x": 0, "y": 0}
    },
    "exits": {
        "north": {"x": 5, "y": 0},
        "south": {"x": 5, "y": 9}
    }
}
```

### 2. Movement Within Rooms

- `move_to [x] [y]` — move to specific grid coordinate within current room
- `move_to [item]` — move adjacent to specified item
- Movement cost depends on tile type (walking on rubble costs 3 AP)
- Items/characters have positions within the grid

### 3. Pathfinding (A*)

- NPCs can pathfind across room grids to reach exits, items, or other characters
- `engine/pathfinding.py` — A* implementation using tile costs
- Consider diagonal movement (optional, user-configurable)

### 4. Area Size/Shape

- Area dimensions defined in `room.grid.width` and `room.grid.height`
- Shape defined by tile types (walls define boundaries)
- Exits positioned at specific grid edges
- Procedural room generation from templates

### 5. UI Considerations

- Area grid view in inspector (toggleable)
- Character/item positions visible on grid, draggable
- Movement cost feedback (e.g. "Moving there costs 3 energy")

## Implementation Order

1. **Phase 1**: Area grid data model + basic `move_to` command (engine + room.py)
2. **Phase 2**: A* pathfinding (new engine module)
3. **Phase 3**: Grid visualization in inspector (frontend)
4. **Phase 4**: NPC pathfinding + procedural generation

## Files Affected

- `room.py` — add grid field with tile data, item/character positions, exit coords
- `engine/movement.py` — `move_to` coordinate handler, add movement cost calculation
- `engine/pathfinding.py` — new A* module
- `engine/npc_behaviors.py` — use pathfinding for NPC movement
- `virtual_world_engine.py` — wire new movement costs
- `static/js/inspector/room-view.js` — grid visualization
- `static/js/graph/` — optional grid overlay on areas
- `world_template.json` / library areas — grid data

## Tests
- A* pathfinding on various grid layouts (open, obstacles, mazes)
- Movement cost calculation
- NPC pathfinding integration
- Serialization (grid + positions survive save/load)


---

## todo/graph/task-290-template-variants-and-override-tracking.md

# Task 290 — Template Variants & Override Tracking

## Status

Todo — follow-up to task-289, not started.
The "don't clobber protected data" intent already exists in the **World→Library**
direction as an automatic guard (empty world values never erase library data in the
sync modal, diff-modal shows protected fields un-checked) — added 2026-08-20.
task-290 makes this an author-declared `overrides` feature for Library→World.
See **task-317**.

## Goal

Add two optional layers on top of the basic template-link system from task-289:

1. **Template variants** — let a library file define a base template plus named variants (e.g., `Task 3 - main area` is base; `closed door` and `open door` are variants with `parent_template`).
2. **Override tracking** — let a node declare which fields it has customized, so sync only refreshes non-overridden fields.

## Why

- `labs.json` has near-duplicate rooms that are really state variants of the same base space (e.g., `Task 3 - area 1 closed door` / `open door`). Variants make this intentional and maintainable.
- Authors sometimes want to localize a room (custom description) but still receive mechanical updates (new triggers, tags). Override tracking enables partial sync without breaking the template link.

## Design Decisions

1. **Variants are first-class in the library**
   - A library file can declare a `base` block plus a `variants` map.
   - Each variant has `name`, optional `parent_template`, and a partial definition that overrides the base.
   - When placing from library, the author picks either the base or a named variant.
   - Syncing a variant first applies the base sync, then re-applies the variant's overrides on top.

2. **`template_ref` replaces flat `library_id`**
   - Node stores:
     ```
     "template_ref": {
       "library_id": "task_3_area",
       "variant": "closed_door",   // null or omitted = base
       "linked_fields": ["name", "triggers", "properties.tags"],
       "overrides": {
         "description": "Custom flavor text that shouldn't be clobbered."
       }
     }
     ```
   - `linked_fields` is optional; if absent, all mutable fields sync.
   - `overrides` is optional; if present, those fields are excluded from sync unless the author explicitly chooses "force sync overrides."

3. **Sync behavior with variants + overrides**
   - Sync order: base definition → variant overrides → node overrides excluded.
   - If a node has `overrides`, sync returns a warning: "3 fields protected by overrides, skipped."
   - Break-link removes the entire `template_ref` block and converts overridden fields back to plain node fields.

4. **Frontend UX**
   - Library browser shows a tree: base → variants. Author can click "Place Base" or "Place Variant: Closed Door."
   - Inspector shows: "Linked to `task_3_area` (variant: closed_door). 2 fields overridden." with links to view/edit overrides.
   - Sync dialog offers: "Sync all linked fields" vs "Force sync (include overrides)."

## Implementation Steps

1. **Library schema extension**
   - Add `base` + `variants` support to library loader.
   - Variants resolve against their parent at load time; placed nodes store the resolved `library_id` + `variant`.

2. **Backend: `template_ref` structure**
   - Replace flat `library_id` with `template_ref` dict on nodes.
   - Migration: existing `library_id` fields are wrapped into `template_ref` on first read.

3. **Backend: override-aware sync**
   - `engine/sync.py` respects `linked_fields` and `overrides` during sync.
   - Returns structured diff: `{ updated: [...], skipped_overrides: [...], already_current: true }`.

4. **Frontend: variant picker + override editor**
   - Library browser: variant tree + place buttons.
   - Inspector: override list with edit/delete per field.

5. **Testing**
   - Variant sync: base changes propagate to variant nodes, variant-specific fields preserved.
   - Override sync: protected fields skip, unprotected fields update.
   - Break-link with overrides: overrides flatten into plain node fields.

## Out of Scope

- Bulk variant creation from existing near-duplicate nodes (could be a later migration tool).
- Conflict resolution when base and variant edit the same field (variant wins by design).



---

## todo/graph/task-376-draw-a-door-wizard.md

---
type: task
status: todo
area: graph
priority: medium
---

# task-376: draw-a-door-wizard

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P3 — Draw-a-door wizard: select two areas → creates way node + 4 connection edges (connect_areas behavior) with name/cardinal/hidden/one-way options.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.




---

## todo/graph/task-407-graph-edge-indexing-case-normalization-and-exits-cache.md

---
type: task
status: todo
area: graph
priority: high
---

# task-407: Graph edge indexing, boundary case normalization, cached exits

**Filed:** 2026-09-19  
**Depends on:** nothing. Additive; keeps the public graph API.  
**Evidence:** goblin soak profile (`graph.py:98–155`; `engine/legacy_compat.py:57`).

## Goal

Make edge lookup and exit building cheap and predictable, and lowercase ids
**once at the boundary** instead of on every call.

## Problem

- `get_edges_for_source` (`graph.py:130`) and `get_edges_for_target` (`:140`)
  scan the entire edge list and call `.lower()` on both endpoints of every
  edge per call. `add_edge` (`:98`) and `remove_edge` (`:107`) do the same to
  dedupe/remove.
- `build_exits_for_area` is recomputed on demand, reached through the
  `current_area` property (`engine/legacy_compat.py:57`).
- Measured over 100 ticks in the goblin soak: ~876 exit rebuilds and ~1M
  `str.lower()` calls **per tick**. Nodes already have a case-insensitive
  `_id_index` (`graph.py:57`); edges do not, and the existing lowercase index is
  not used by the hot lookups.

## Changes

1. **Edge indexes.** Maintain edges keyed by lowercased `source` and `target`
   (and by type), updated in `add_edge` / `remove_edge` / `load_from_dict` /
   `clear`. `get_edges_for_*` consult the index instead of scanning
   `self.edges`.
2. **Normalize at the boundary.** Normalize id case once on insert/load/save so
   hot paths compare pre-normalized keys and never call `.lower()` per edge.
3. **Exits cache.** Cache `build_exits_for_area(area)` results, invalidated on
   any mutation that can change exits (node/edge add/remove/load).

## Acceptance

- `get_edges_for_source` / `_target` no longer iterate `self.edges` or call
  `.lower()` per edge.
- Indexes and the exits cache stay correct across add/remove/load; save/load
  round-trips equal.
- The exits cache invalidates on every mutation that changes exits (test with a
  deliberately mutated edge).
- Per-tick `.lower()` calls drop by orders of magnitude, with profiler
  evidence.

## Non-goals

- Changing edge types, spatial-edge semantics, or trigger behaviour.
- Removing the `current_area` property from the public API (task-411/task-401
  own the longer-term decision).

## Verification

- Unit: index correctness after add/remove/load; exits-cache invalidation.
- Profile: same 100-tick run before/after (ranking only).
- Full suite excluding `test_mcp_*`.

## Progress — 2026-09-19

Implemented.

- `graph.py`: `_edges_by_source` / `_edges_by_target` / `_spatial_edges` indexes
  keyed on lowercased endpoints; `get_edges_for_source` / `get_edges_for_target`
  consult them and never call `.lower()` per edge. A `_indexed_edge_count`
  length check forces a lazy rebuild if external code mutates `self.edges`
  directly (a few effect handlers still do). `_revision` is bumped on every
  mutation for cache invalidation.
- `engine/area_description.py`: `build_exits_for_area(..., include_hidden=True)`
  is cached and invalidated on graph revision. **The game-facing default
  (`include_hidden=False`) is deliberately not cached**, because it depends on
  per-player discovery state (`Player.discovered_exits`) that changes without a
  graph mutation.

Verified: full suite 2835 passed (excluding pre-existing `test_mcp_*`); the
trigger/exit cost that dominated the old profile is gone from the hot path.

### Second pass — 2026-09-19 (lighting + edge moves)

- `remove_edge` / `remove_edges_for_node` now unindex only the removed edges
  (`_unindex_edge`) instead of rebuilding every index; `triggers` edges still
  rebuild because the trigger index is a set of sources.
- `retarget_edge(edge, new_type, new_target, properties)` added: one operation
  for a pure move. Unequip uses it (`equipped` → `carrying`) instead of
  remove + add.
- `engine/items/take_drop_actions.py`: direct `self.graph.edges.remove(...)`
  calls replaced with `graph.remove_edge(...)` so the indexes stay correct.
- `engine/lighting.py`: effective light is `max(base, best_item)` (the summed
  form was dead arithmetic the ceiling discarded), and every area's light is
  recomputed once per tick into a revision-keyed stamp read by the hot paths.
- Measured: one-week soak **56s → 181 ticks/s** (was 9m49s / 17.1 t/s), 23/23
  alive, identical vitals/trace (behaviour unchanged). Suite runtime 78s → ~25s.
- **Done (third pass):** take/drop now capture and retarget their placement
  edge in place, and their capacity/hand checks run before any mutation so a
  failed take cannot orphan the item. `logging_events.record_turn_event` was
  also rebuilding the whole turn-event list per append (O(n²) headless); it now
  prunes only on turn change and caps at 2,000.



---

## todo/graph/task-422-nl-editor-llm-budget-controls.md

---
type: task
status: todo
area: graph
priority: medium
---

# task-422: NL editor LLM budget controls and context readout

**Filed:** 2026-09-20  
**Depends on:** task-387 (NL editor). Builds on the context-accounting fix landed
2026-09-20 in `static/js/context-window.js` (identity-keyed metadata, bounded
critical retention, array-measured pruning).  
**Relates:** `static/js/nl-editor/agent-loop.js`, `static/js/nl-editor/index.js`,
`static/js/nl-editor/ui.js`, `static/js/config.js`.

## Goal

Make the NL editor's LLM budget visible and adjustable from the NL editor tab,
instead of being hard-coded constants. The user asked for this directly: "set
max tokens to 60000, or even adjustable in the NL editor tab".

## Current state

The knobs exist but are buried and unadjustable:

| Knob | Where | Value |
|------|-------|-------|
| `maxIterations` | `agent-loop.js` — `this.maxIterations` | 100 |
| `maxTokens` | `ContextWindowManager` (NL editor) | 6000 |
| `maxMessages` | `ContextWindowManager` (NL editor) | 30 |
| `recentTurnCount` | `ContextWindowManager` (NL editor) | 8 |
| `maxCriticalMessages` | `ContextWindowManager` | 10 |

`ContextWindowManager.getStats()` already reports
`{totalMessages, totalTokens, maxTokens, maxMessages, utilization, isOverLimit}`
and **nothing consumes it**. `agent.maxIterations` is already read by
`index.js` for the status string, so the loop cap is exposed to the UI.

Missing, and worth fixing in the same pass: when the iteration cap is hit the
loop simply exits. If the model's last message had no text,
`finalAssistantResponse` is empty and the UI shows nothing — a silent stop.

## Design

1. **Knobs, in the NL editor panel.** A compact collapsed "⚙ Budget" row in the
   panel header (next to Reset), expanding to a small form:
   - Max rounds (iterations)
   - Max context tokens
   - Max messages retained
   - Recent turns kept
   Keep it out of the chat stream; the panel is narrow and the chat is the point.

2. **Persistence** via the existing helper pattern —
   `storage.setConfig('nl_max_iterations', ...)` / `storage.getConfig(...)`
   (see `config.js` for the established shape). Defaults reproduce today's
   behaviour exactly when nothing is saved: 100 / 6000 / 30 / 8 / 10.

3. **Model-aware default for `maxTokens`.** 60000 is only safe if the active
   provider/model actually has that window; a local LM Studio model with an 8k
   context would overflow. Derive the default from the active model's known
   context length and clamp, falling back to a conservative value when the model
   is unknown. **This needs a model → context-length lookup that does not exist
   yet** — a small table keyed by the same model names used in
   `getFallbackModels`, with an explicit "unknown → conservative" path. Scope
   this sub-piece carefully; do not guess large windows for unknown models.

4. **Readout.** Show `context 4.2k/6k · round 12/100` in the status area using
   `getStats()`. This is the observability that would have made the pruning bug
   obvious; keep it live per iteration.

5. **Report a capped stop.** If the loop exits because `currentIteration` reached
   `this.maxIterations`, emit it — set the turn-end payload with a flag and have
   the UI append a visible note such as "Stopped at the 100-round limit; the
   edit may be incomplete." Do not end silently with an empty response.

6. **Apply to the next turn without a reload.** Read the knobs at `runUserTurn`
   start and construct/update the `ContextWindowManager` options there, so a
   changed value takes effect on the next prompt.

## Acceptance

- Changing any knob persists across a reload and takes effect on the next turn
  with no code change.
- Defaults with nothing saved reproduce current behaviour (100 / 6000 / 30 / 8).
- The status area shows the live context window and round counter.
- Hitting the round cap produces a visible message in the chat, never a silent
  stop.
- `maxTokens` default is clamped to the active model's window; unknown models get
  a conservative default rather than an assumed large one.
- The **main agent engine's** own `ContextWindowManager`
  (`agent-engine.js:39`, `maxTokens: 9500`) is unaffected — its options are not
  driven by these NL-editor settings.

## Non-goals

- Changing pruning semantics or retention policy (that fix already landed).
- Dollar cost accounting or prompt caching.
- Per-scenario or per-character budget overrides.
- Making the same knobs adjustable for the foreground agent engine.

## Verification

- Unit: options round-trip through `storage` config; clamp/fallback logic for
  known, unknown, and absurd values (0, negative, 10x the model window).
- Unit: `getStats()` reporting matches the window actually sent.
- Manual: set max rounds to 20, run a long multi-tool edit, confirm it stops at
  round 20 and says so in the chat.
- Regression: `npm run lint`, `npm run typecheck`, and the existing pytest suite
  stay green.



---

## todo/graph/task-435-offline-generators-still-mint-way-templates.md

---
type: task
status: todo
area: graph
priority: low
---

# task-435: Offline generators still mint way-orientation templates

**Filed:** 2026-09-21  
**Split out of:** task-395 (way-orientation authoring), which removed the bulk
fill and the engine-side mint but left the generators that produced it.

## Problem

task-395 removed `fix_way_orientation` and added `clear_way_fix_fields`, which
reverts the minted values on demand by matching them **exactly**:

- `pass_message == "You pass through <name>."`
- `visible_in_direction == "A glimpse of <source> beyond."`
- `cardinal == "north"` where the edge's `direction` is not a real cardinal

That made the *result* clean, and task-395's own claim was "no bulk op writes way
data anymore". Measured, that is **false at the repo level** — the offline
generators still write those exact strings:

| Tool | Line | Writes |
|---|---|---|
| `tools/build_scenario.py` | 80-81 | `"You pass through {name}."` |
| `tools/assemble_scenario.py` | 239 | same template |
| `tools/sync_scenario_to_library.py` | 147 | same template |
| `tools/generate_scenario.py` | 212 | same template |

And one writes a **near-variant** the exact match will not catch:

- `tools/fix_scenario_authoring.py:78-79` → `"You pass through the {noun}."`
  (note the article) — so a scenario run through it can never be cleaned by the
  cleanup op, and looks authored while being generated.

## Why it matters now

A scenario regenerated or assembled by these tools is born minted. The cleanup op
is the only remedy and it is a *manual button*, so the mint silently returns with
the next generation run — including into any new world (task-398's deterministic
generation is a likely future caller).

## Design question to settle first

The templates exist because a generator has to put *something* in the field, and
it has no text model. Options:

1. **Leave the field empty** when generating, and let the engine's existing
   fallbacks supply the line at read time — that is what the validator's
   downgrade to `info` already assumes (`engine/movement.py:780-783` and
   `engine/area_description.py:563` both have sane defaults). Cleanest: a
   generated way carries no invented prose at all.
2. **Generate honestly-labelled placeholders** (e.g. leave a marker the cleanup op
   recognises by prefix rather than exact match) so a human is prompted to
   author it. Better ergonomics, more moving parts.

Whichever: the near-variant in `fix_scenario_authoring.py` must be reconciled —
either it adopts the same convention or the cleanup match becomes prefix-based.

## Acceptance

- No offline generator writes `"You pass through …"` or `"A glimpse of … beyond."`
  into way data.
- A scenario produced by each generator has zero fields the cleanup op would
  remove, asserted by a test.
- `clear_way_fix_fields` remains exact-match (its safety property is that it never
  touches authored prose) — so the fix is on the generation side, not by loosening
  the match.
- The validator still reports a missing `pass_message`/orientation as `info`, and a
  way with no invented prose reads correctly through the engine fallbacks.

## Non-goals

- Re-filling way orientation for existing scenarios (task-395 decided on-demand
  remediation is right, and the camp data is already clean).
- Authoring orientation for the mansion/Pines areas (that is task-324's area pass).



---

## todo/graph/task-438-nl-editor-region-decomposition.md

---
type: task
status: todo
area: graph
priority: high
---

# task-438: NL editor region decomposition — add child areas to, and split, a region node

**Filed:** 2026-09-21
**Depends on:** task-439 (canonical area identity in save + lookups — hard prerequisite),
task-387 (NL editor + staging), task-9 (`engine/population.py`)
**Related:** task-397 (world scopes), task-398 (deterministic structure generation),
task-393 (validator triage), task-324 (domain tags), task-427 (population caps),
task-410 (food renewal), task-411 (attention budget / fidelity tiers), task-422 (NL editor budget)

## Goal

Type this into the NL editor and get a reviewable staged graph patch:

> "Add a creek margin, a rocky rise, and a deeper interior to the Deep Forest."
>
> "Split the Deep Forest into: forest edge, undergrowth, deep interior, creek margin,
> rocky rise — instead of one node."

The LLM interprets the request and authors the **content** (names, descriptions,
features, tags, ambience). The **topology** — node creation, way minting, boundary
retargeting, id casing, contents migration — is deterministic code. This is task-398's
generator contract applied to an *existing* region instead of an unmade scope.

## Problem

`area_deep_forest` is one node with six outbound ways (Raven River, Old Dwarven Ruins,
Northern Hills, Human Road, Abandoned Farm, Murk Lake) and seven inbound
(`kraktooth_goblin_camp.json:2539+`). Six regions have this shape — `northern_hills`,
`murk_lake`, `blackmarsh`, `raven_river`, `eldenford`, `human_road` — and the library
`data/library/areas/eldenford.json` is 15 lines with `"exits": []`, its contents
("farms, houses, livestock, a smithy, an inn, a market, and guards") left as prose.

The camp interior, by contrast, is correctly decomposed: `area_chiefs_pit` is a hub with
`way_pit_to_*` passage nodes to ~20 leaf areas. The exterior was never decomposed.

The NL editor already has the mutation primitives — `create_node`, `connect_areas`,
`attach`, `spawn_library_item`, `link_to_library` (`static/js/nl-editor/tools.js:291-441`)
— and a staging buffer with deterministic minted IDs, so chains
*create → connect → attach* resolve before commit. What it does **not** have is a
*topology operation*: one intent → N areas + internal ways + boundary re-homing, planned
deterministically. Asking a small local model to hand-assemble six areas and ten ways
through 25 individual tool calls is how `Generated Scenario Review (2026-08).md` ended
with 9 broken scenarios out of 13.

## Two verbs, two phases

### slice 1 — `add_areas` (ships first; no retargeting)

Append N child areas to a region and connect them to it. The region node is **retained**
as the hub, so all six existing boundary ways keep pointing at it, unchanged. Nothing
dangles, no save key churns. The result mirrors `area_chiefs_pit` + `way_pit_to_*` —
the precedent already exists in the same scenario file.

### slice 2 — `split_area` (the hard half)

Decompose the region: create children, connect them internally, **re-home every boundary
way** to the correct child, then demote the region node to a grouping anchor. Requires a
gateway-assignment rule and a rollback-safe atomic create+update Apply.

## Non-negotiable properties (task-398 generator contract)

Deterministic · seedable · reviewable before Apply · idempotent (a second run must not
duplicate) · provenance on every generated node · never overwrite manual edits ·
**report** unresolved assignments, never silently substitute.

## Design

### Anchor rule (v1): never delete the region node

On `split_area`, retag the region node `region` and keep its id. Deleting it would dangle
every `way_*` edge and every spatial relation, and — given task-439 — would also churn the
save's area keys. The retained node becomes the grouping anchor, forward-compatible with
task-397's `properties.world_scope_id`.

### Children: authored inline or pulled from the library

```jsonc
"children": [
  { "name": "Creek Margin", "approach": "east",
    "description": "...", "tags": ["forest", "water_margin"],
    "features": ["creek", "reeds"] },
  { "library_area": "frozen_thicket", "name": "Thicket", "approach": "north" }
]
```

A library child imports `description` / `environment` / `tags` / `features` but **not its
`exits`** — the planner mints the ways, so `frozen_thicket`'s hardcoded exits to
`Snowbound Hollow` do not drag in a dead winter sub-graph. The library already holds the
right vocabulary (`weeping_willow_hollow`, `frozen_thicket`, `frozen_stream_crossing`,
`frozen_lake_clearing`, `marsh_trail`, `stream_bank`, `rocky_slope`, `willow_gap`), so
"a hollow / a thicket / a crossing / a rocky rise" can be reused rather than invented.

### Gateway assignment (slice 2)

Each child may declare `approach` / `cardinal`. A boundary way is re-homed to the child
whose `approach` matches the way's `cardinal` / `direction`. Anything unmatched is
**reported** as an unresolved pool in the preview (task-398: "may not substitute
unrelated items silently") — the author assigns it in the tray or re-declares `approach`.

### Connectivity modes

- `hub` — all children off the region node (slice 1 default, matches `area_chiefs_pit`).
- `linear` — a chain; right for a river as a sequence of banks.
- `mesh` — children adjacent per declared `approach`.

Bidirectional ways get four `connection` edges via `MovementSystem.connect_areas`
(`engine/movement.py:96`), matching the existing corpus.

### Boundary-way retarget + contents migration (slice 2)

- Every `way_*` connected to the region is patched (`update_node`) to target the assigned
  child. This is an update to an existing node, so it rides the existing staging buffer;
  Apply must be atomic across creates **and** updates, with rollback.
- Items and characters with an `in` edge to the region are re-homed to a child via
  `attach`, or stay if the anchor is retained.
- A character must never be left in an area that no longer exists; `at` stays 1:1.

### Proxy resource nodes (opt-in)

For each new child, optionally clone one representative stateful proxy — e.g. the existing
berry-bush node (`on_tick` grow, then `spawn_item {into: "container"} `capped by
`contains_count berries < 10`; `kraktooth_goblin_camp.json:1466-1531`). One node per child,
described **plural** ("berry bushes"), so resource yield scales with child count without
authoring individual plants. Co-ordinate caps with task-427 (population caps) and task-410
(food renewal).

### Interim region representation

`properties.region: "<region_id>"` on every child, plus `tags: ["region"]` on the anchor.
No engine change; superseded by task-397's `world_scopes` manifest when it lands.

## Tool contract

Add to `static/js/nl-editor/tools.js`, mirroring the existing schema shape (`tools.js:341-357`):

```jsonc
{ "name": "add_areas",
  "parameters": { "region_id": "string", "children": "array",
                  "connect": "hub|linear|mesh", "populate": "boolean",
                  "replicate_proxies": "array", "seed": "string" } }

{ "name": "split_area",
  "parameters": { "region_id": "string", "children": "array",
                  "connect": "hub|linear|mesh", "gateways": "object",
                  "populate": "boolean", "replicate_proxies": "array",
                  "preserve_region_node": "boolean (default true)", "seed": "string" } }
```

Planning lives in a pure, framework-free module — `engine/decompose.py`, modelled on
`engine/population.py`: `plan_*(...)` is pure and deterministic; `apply_*(plan, spawn,
relate, ...)` takes callables so the engine never imports Flask or a route-private helper.
The NL editor tool stages the returned patch; `tools/generate_scenario.py` may consume the
same planner offline.

## Work plan

1. **Phase 0 — prerequisites.** task-439 (`rooms_serialized[node.name]` →
   id-keyed, and name-based exit/`current_area` lookups made unambiguous). Split areas
   share names ("hollow", "clearing", "crossing") **by design**, so this is not optional.
2. **Phase 1 — `engine/decompose.py` (slice 1).**
   `plan_add_areas(graph, region_id, children, seed) -> DecompositionPatch`
   (nodes, edges, region assignments, unresolved, report, provenance). Deterministic,
   region-scoped id minting: `area_deep_forest_creek_margin`,
   `way_deep_forest_to_creek_margin`. Tests: same seed → same patch; re-run is a no-op.
3. **Phase 2 — `add_areas` tool + staging tray (slice 1).** Wire through
   `static/js/nl-editor/tools.js`, `staging.js`, `ghosts.js`; ghost preview of the new
   cluster; Apply.
4. **Phase 3 — `split_area` + gateway retarget (slice 2).** Boundary-way patching,
   contents migration, unresolved-gateway report, atomic create+update Apply, rollback.
5. **Phase 4 — population wiring.** Point the editor's `populate_area` at
   `engine/population.py`. **It currently is not:** `tools.js:344` describes nine
   hardcoded theme packs (`apothecary, kitchen, garden, study, smithy, warehouse, shrine,
   bedroom, generic`) with canned item lists and NPCs (`tools.js:552-660`); it never reads
   the area's tags, is not seedable, and has no forest/hollow/marsh vocabulary. No
   `populate` route exists in `routes/`. Without this the split produces empty areas.
   Gated on task-324 (23/58 areas tagged, none domain-flavoured; `eldenford.json` is
   `tags: []`).
6. **Phase 5 — validation gate.** Reuse the validator (task-393) before Apply: every edge
   endpoint exists, no duplicate area names, id casing, region coherence, every child
   reachable from the anchor. Refuse to split an already-split region unless `--variant`.

## Acceptance

- "Add a creek margin and a rocky rise to Deep Forest" stages exactly two areas and two
  ways with four connection edges each, ghosts visible, nothing applied until Apply.
- "Split Deep Forest into …" retargets all six boundary ways; the preview shows a table of
  old way → new child; unmatched gateways are listed, not guessed.
- Same seed + same children + clean graph yields an identical patch; a second run creates
  nothing.
- No character is orphaned; `look` resolves; movement to river / ruins / hills / road /
  farm / murk still works end-to-end.
- `python -m pytest tests/ -q -k "not mcp and not emote"`; new `tests/test_decompose.py`
  covers determinism, idempotency, retarget, unresolved gateway, contents migration.
- Reload preserves every generated node and its provenance; a later manual edit to a
  generated child survives a re-run.

## Non-goals

- Replacing task-397's `world_scopes` manifest (this is the interim `region` property).
- Generating wilderness *grids* or district road layouts (task-398's non-goal stands).
- Chunk unloading / projection endpoints (task-401, task-402).
- Re-filling way orientation prose for existing scenarios (task-395 / task-435).
- Unsupervised LLM topology — the LLM never mints ids or picks way endpoints.

## Risks

- **Name collisions** — why task-439 is a hard prerequisite and not a nice-to-have.
- **Travel depth** — `background_simulation._target_step` BFSes exits and returns one hop
  (`engine/background_simulation.py:735-742`), so decomposition needs no new travel code,
  but a region four hops deep costs four turns to reach food. Interacts with
  `minutes_in_turn` (task-436 / task-437). Verify a hungry goblin still eats.
- **Sanitized-id shim** — `background_simulation.py:703-706` documents ways referencing
  `area_chiefs_pit` while the node id keeps the apostrophe. Graph-level case resolution
  now exists (`graph.py:70-77`), but adding 30-40 areas multiplies the surface area for
  this class of mismatch.
- **Budget** — one child with furniture, items, an NPC and a way is a large slice of the
  NL editor's hard-coded 6000-token context (`static/js/nl-editor/agent-loop.js:23`;
  task-422 is still unstarted). Prefer several small `add_areas` calls over one giant
  `split_area`.



---

## todo/items/task-391-lyrie-spell-items.md

---
type: task
status: todo
area: items
priority: medium
---

# task-391: Lyrie's Spellbook — Life-Bonded Spell Items

**Filed**: 2026-09-02  
**Status**: Todo  
**Source**: Character backstory from `data/library/characters/Lyrie.json` — memories, personality, and current Frozen Thicket situation.

## Summary

Create 12 spell items for Lyrie, each tied to a specific life memory or enduring situation. Spells should reflect her personality: well-intentioned, slightly chaotic, deeply kind, and occasionally catastrophic. Some should be implementable with existing engine effects; others should propose new trigger/effect types that would meaningfully expand the engine.

Each spell below includes a full item JSON spec (library-ready), suggested trigger wiring, and a note on whether it uses existing engine machinery or proposes a new effect.

## Spells

### 1. Hearth Ember
**Life memory**: *The Present* (Age 79) — freezing in the Frozen Thicket.  
**Trigger**: `on_use`  
**Effect tier**: Existing engine effects only.

```json
{
  "name": "Hearth Ember",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "A pocket of warmth Lyrie learned out of necessity. She cups her hands and a soft heat blooms between her palms, curling up her arms and toes. It's the only spell that behaves exactly like she wants — probably because she's cast it a thousand times in the snow.",
  "tags": ["spell", "magic", "fire", "warmth"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "remove_condition",
          "params": {
            "condition": "hypothermia",
            "target": "self",
            "message": "The deep cold lets go."
          }
        },
        {
          "type": "heal",
          "params": {
            "amount": 20,
            "stat": "Temperature",
            "target": "self",
            "message": "Warmth spreads all the way to your toes."
          }
        },
        {
          "type": "adjust_environment",
          "params": {
            "temperature": 5,
            "target_node": "self",
            "message": "The air around Lyrie turns comfortably warm."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

### 2. Tongue of the Little Folk
**Life memory**: *The Squirrel Incident* (Age 31) — tried to comfort a squirrel in animal tongue; it screamed for twenty minutes.  
**Trigger**: `on_use`  
**Effect tier**: Existing + `llm_respond` for animal dialogue.

```json
{
  "name": "Tongue of the Little Folk",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "The elven tongue for beasts. Lyrie knows it well — she learned it the hard way. Animals still don't quite understand her, but she never stops trying. She leaves acorns out as apologies.",
  "tags": ["spell", "magic", "beast", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "add_tag",
          "params": {
            "node_id": "self",
            "tag": "animal_tongue",
            "message": "Your ears crackle and pop in a way beasts seem to recognize."
          }
        },
        {
          "type": "llm_respond",
          "params": {
            "instructions": "You are a small forest creature (bird, squirrel, rabbit, or fox) that has been addressed in animal tongue by Lyrie. Reply in a single short sentence of animal-speak: chitters, chirps, huffs, or clicks. Never full sentences. Sometimes you are annoyed, sometimes curious, sometimes indifferent.",
            "fallback_message": "*A small creature stares at Lyrie, then darts away.*"
          }
        },
        {
          "type": "message",
          "params": {
            "message": "Lyrie chirrups a wumbling greeting. Something small and alive considers her seriously from the underbrush."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

### 3. Whisper of Green
**Life memory**: *The Grapevine* (Age 45) — talked to a grapevine named Vincent for three days. "He never talked back, but he listened."  
**Trigger**: `on_use`  
**Effect tier**: Existing + proposed `plant_whisper` effect (plants can `llm_respond` as slow, patient speakers).

```json
{
  "name": "Whisper of Green",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "Named for Vincent the grapevine. Plants speak slowly, in rustles and sap, and they remember everything. This spell lets her ask them small questions — where water hides, which way is safe, whether a storm is coming.",
  "tags": ["spell", "magic", "plant", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "surface_memory",
          "params": {
            "text": "Vincent the grapevine. You talked for three days. He never talked back, but he listened.",
            "importance": 5,
            "message": "A slow, green warmth rises in your chest. You can almost hear leaves rustling."
          }
        },
        {
          "type": "heal",
          "params": {
            "amount": 5,
            "stat": "Sanity",
            "target": "self",
            "message": "The forest feels like an old friend."
          }
        },
        {
          "type": "llm_respond",
          "params": {
            "instructions": "You are a nearby plant (bush, vine, tree, or flower) addressed by Lyrie through plant-whisper magic. Reply in one short, slow, earthy sentence full of rustle, sap, root, and leaf imagery. Be patient. Be ancient. Be kind.",
            "fallback_message": "*A branch brushes your arm. The plant has nothing important to say right now.*"
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

### 4. Bloom of the Well
**Life memory**: *The Exile Scare* (Age 62) — tried to make the well prettier with flowers. Turned it into a fountain of blossoms; water unusable for a week. This is the incident that got her almost exiled.  
**Trigger**: `on_use`  
**Effect tier**: Existing + proposed `area_transformation` visual state.

```json
{
  "name": "Bloom of the Well",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "What the Exile Scare taught her: beauty has consequences. This spell makes flowers bloom from almost anything, but the result is always a little too much. The well ran for a week. Her hands still shake when she thinks about it.",
  "tags": ["spell", "magic", "flower", "plant", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "spawn_item",
          "params": {
            "item_id": "flowers",
            "into": "area",
            "message": "Blossoms erupt from the ground in a glorious, messy cascade."
          }
        },
        {
          "type": "adjust_environment",
          "params": {
            "light": 10,
            "air": "sweet",
            "target_node": "self",
            "message": "The air turns sweet and the light softens."
          }
        },
        {
          "type": "message",
          "params": {
            "message": "Lyrie watches the flowers bloom and smiles, then winces. 'Not too much... not too much...'"
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

### 5. Transfigure: Poultry
**Life memory**: *The Chicken Cart* (Age 22) — tried to fix a cart wheel with magic. "I made it better — it turned into a chicken."  
**Trigger**: `on_use_on` (cast on an object)  
**Effect tier**: **Proposes new effect**: `polymorph_target` — transforms a target item/NPC into another template for a duration.

```json
{
  "name": "Transfigure: Poultry",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "The Chicken Cart. She tried to fix a wheel and made it into a chicken. She still apologizes to poultry. The spell is theoretically about transmutation, but in practice it just turns things into birds.",
  "tags": ["spell", "magic", "transmutation", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use_on",
      "effects": [
        {
          "type": "message",
          "params": {
            "message": "Lyrie squints, mutters a word that sounds like 'chicken,' and —"
          }
        },
        {
          "type": "polymorph_target",
          "params": {
            "target_template": "chicken",
            "duration": 50,
            "message": "The object clucks, feathers bursting from its surface, and struts away."
          }
        },
        {
          "type": "apply_condition",
          "params": {
            "condition": "amused",
            "target": "self",
            "duration": 5,
            "message": "Well. That was embarrassing."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `polymorph_target` — takes `target_template` (library item/NPC id), `duration` in ticks, optional `revert_after`. Should work on items and simple NPCs. Reverts automatically after duration.

### 6. Conjure Fluffy
**Life memory**: *The Lost Sheep* (Age 70) — found a rock that looked like a sheep. Convinced herself it was Fluffy. "It never moved. I still visit sometimes."  
**Trigger**: `on_use`  
**Effect tier**: **Proposes new effect**: `create_illusory_companion` — spawns a temporary, interactable NPC with custom dialogue and behavior.

```json
{
  "name": "Conjure Fluffy",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "A rock that looks like a sheep. Lyrie named him Fluffy. He never moved, but he was good company in the snow. This spell conjures something that isn't quite real but feels true — useful when you're lost and the trees all look the same.",
  "tags": ["spell", "magic", "illusion", "companion", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "message",
          "params": {
            "message": "Lyrie closes her eyes and holds out her hands. When she opens them, there's a small, fuzzy shape sitting in her palms. It looks like a sheep made of down and wishful thinking. It blinks at her."
          }
        },
        {
          "type": "create_illusory_companion",
          "params": {
            "name": "Fluffy",
            "description": "A small, fuzzy sheep made of down and wishful thinking. It has kind eyes and no discernible mass. It does not move unless you believe very hard.",
            "duration": 100,
            "dialogue": [
              "Fluffy blinks slowly. You feel strangely comforted.",
              "Fluffy chews on nothing. It is a very peaceful nothing."
            ],
            "message": "Fluffy materializes. He is very quiet and very warm."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `create_illusory_companion` — spawns an NPC with a limited lifespan, custom dialogue snippets, and no collision/physics. Vanishes after duration or if the caster stops concentrating (e.g., moves to a new area).

### 7. Siren's Lullaby
**Life memory**: *The Singing Fish* (Age 75) — sang to a sad fish for two hours. It died. She doesn't sing near water anymore.  
**Trigger**: `on_use`  
**Effect tier**: **Proposes new effect**: `broadcast_emotion` — shifts the `emotion` state of all characters within an area radius.

```json
{
  "name": "Siren's Lullaby",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "The Singing Fish. She sang to cheer it up. It died. She hasn't sung near water since. The lullaby still soothes, but there's something about it that unnerves living things just a little.",
  "tags": ["spell", "magic", "song", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "message",
          "params": {
            "message": "Lyrie hums a soft, wordless tune. The tension in the air eases. A bird nearby tilts its head, then flies away a little faster than before."
          }
        },
        {
          "type": "broadcast_emotion",
          "params": {
            "emotion": "soothed",
            "intensity": 0.3,
            "radius_areas": 1,
            "duration": 5,
            "message": "Your song drifts through the area. Living things feel strangely comforted, then vaguely unsettled."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `broadcast_emotion` — shifts `emotion.current` for all characters in range. Could also `adjust_vital` for Social or Sanity as a secondary effect.

### 8. Spark of the Baking Incident
**Life memory**: *The Great Baking Incident* (Age 14) — used fire salts instead of flour. Kitchen exploded. Elder Caelum's eyebrows never grew back.  
**Trigger**: `on_use`  
**Effect tier**: Existing + proposed `spawn_fire_source` persistent hazard.

```json
{
  "name": "Spark of the Baking Incident",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "Fire salts instead of flour. The kitchen exploded. Elder Caelum's eyebrows never grew back. This spell creates a sudden burst of flame — not a controlled one, but a passionate, enthusiastic one. She still bakes him a cake every year. She buys it now.",
  "tags": ["spell", "magic", "fire", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "spawn_item",
          "params": {
            "item_id": "candle",
            "into": "area",
            "current_state": "lit",
            "message": "A shower of sparks erupts from Lyrie's hands. One candle ignites. The curtains are fine. Probably."
          }
        },
        {
          "type": "adjust_environment",
          "params": {
            "temperature": 8,
            "light": 40,
            "target_node": "self",
            "message": "The room brightens and warms rapidly."
          }
        },
        {
          "type": "surface_memory",
          "params": {
            "text": "The Great Baking Incident. Elder Caelum's eyebrows. The kitchen.",
            "importance": 5,
            "message": "For a moment, you smell burnt sugar and regret."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

### 9. Apology to Chickens
**Life memory**: *The Chicken Cart* (Age 22) — the aftermath. She apologizes to chickens. This spell makes skittish creatures calm down around her.  
**Trigger**: `on_use_on` (cast on a character/NPC)  
**Effect tier**: Existing, but extends `apply_condition` to non-self targets in a spell-item context.

```json
{
  "name": "Apology to Chickens",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "The Chicken Cart incident left her with a lifelong habit: she apologizes to chickens. This spell extends that apology into a subtle pacification — fowl (and sometimes other skittish creatures) calm down around her.",
  "tags": ["spell", "magic", "beast", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use_on",
      "effects": [
        {
          "type": "apply_condition",
          "params": {
            "condition": "charmed",
            "target": "target",
            "duration": 5,
            "message": "Lyrie looks at the creature with big, earnest eyes. It seems to relax."
          }
        },
        {
          "type": "message",
          "params": {
            "message": "'I'm sorry about the cart,' she whispers."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**Dev note**: `on_use_on` with `target: "target"` already exists for items; validating it works from spell items with `target: "target"` is the main QA task here.

### 10. Vincent's Embrace
**Life memory**: *The Grapevine* (Age 45) — three days of talking to a vine. "I named him Vincent. He never talked back, but he listened."  
**Trigger**: `on_use`  
**Effect tier**: Existing + proposed `reveal_hidden` effect (nature exposes what is concealed).

```json
{
  "name": "Vincent's Embrace",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "Named for a grapevine who listened for three days. This spell lets her ask the green world for small favors — a hidden path, a safe resting place, something to eat. Plants oblige, slowly.",
  "tags": ["spell", "magic", "plant", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "surface_memory",
          "params": {
            "text": "Vincent the grapevine. The forest keeps secrets if you ask nicely.",
            "importance": 4,
            "message": "The leaves rustle. A path reveals itself, half-hidden by brambles."
          }
        },
        {
          "type": "heal",
          "params": {
            "amount": 10,
            "stat": "Sanity",
            "target": "self",
            "message": "The forest seems to lean in, protective."
          }
        },
        {
          "type": "reveal_hidden",
          "params": {
            "radius_areas": 1,
            "duration": 20,
            "message": "Through the undergrowth, you see what was hidden: a narrow trail, a cache of berries, a safe place to rest."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `reveal_hidden` — temporarily sets `hidden: false` on items/NPCs/ways within an area radius. Re-hides after duration.

### 11. Fountain of Blossoms
**Life memory**: *The Exile Scare* (Age 62) — turned the village well into a fountain of blossoms. Water unusable for a week.  
**Trigger**: `on_use`  
**Effect tier**: Existing + proposed `transform_area_theme` (area appearance override).

```json
{
  "name": "Fountain of Blossoms",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "The spell that almost got her exiled. Turns any water source into a geyser of blossoms. Beautiful, fragrant, and absolutely catastrophic for water quality. She casts it only when she's very sure the water doesn't matter.",
  "tags": ["spell", "magic", "flower", "water", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "spawn_item",
          "params": {
            "item_id": "flowers",
            "into": "area",
            "message": "A fountain of blossoms erupts from the ground, glorious and overwhelming."
          }
        },
        {
          "type": "adjust_environment",
          "params": {
            "light": 15,
            "temperature": 2,
            "air": "sweet",
            "target_node": "self",
            "message": "The area is drenched in floral sweetness and soft light."
          }
        },
        {
          "type": "transform_area_theme",
          "params": {
            "theme": "blossoming",
            "duration": 100,
            "message": "The world turns pink and white. The elders are definitely going to notice."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `transform_area_theme` — applies a temporary visual/audio/smell overlay to the current area. Themes could include `blossoming`, `frost`, `autumn`, `starlight`. Duration-based revert.

### 12. Ember Companion
**Life memory**: *The Present* (Age 79) — she talks to the little flame like a friend. "oh, please stay lit... i need you to keep me warm."  
**Trigger**: `on_use`  
**Effect tier**: Existing + proposed `bind_companion` (persistent summoned entity that follows caster).

```json
{
  "name": "Ember Companion",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "The little ember she talks to in the Frozen Thicket. She learned to give it a shape, a voice, a tiny flickering personality. It follows her, keeps her warm, and never argues.",
  "tags": ["spell", "magic", "fire", "companion", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "spawn_item",
          "params": {
            "item_id": "everflame_ember",
            "into": "inventory",
            "current_state": "lit",
            "message": "A tiny ember wakens in your palm. It hums contentedly and hovers near your shoulder."
          }
        },
        {
          "type": "bind_companion",
          "params": {
            "item_id": "everflame_ember",
            "follow_distance": 1,
            "duration": 300,
            "message": "The ember settles beside you, a quiet warm presence."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `bind_companion` — marks a spawned item/NPC as a persistent companion of the caster. It follows the caster across area transitions within duration, retains its own triggers/behaviors, and can be interacted with by other characters. Vanishes if caster dies or duration expires.

### 13. Mending Touch
**Life memory**: *The Chicken Cart* (Age 22) — the original intent was fixing the wheel.  
**Trigger**: `on_use`  
**Effect tier**: **Proposes new effect**: `repair_item` — restores durability/uses to a broken item in inventory or on the ground.

```json
{
  "name": "Mending Touch",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "The spell she tried to use on the chicken cart. She wanted to fix the wheel. It turned the cart into a chicken. But the principle was right — mending. If she concentrates very hard, she can make broken things whole again. Mostly.",
  "tags": ["spell", "magic", "mending", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use_on",
      "effects": [
        {
          "type": "message",
          "params": {
            "message": "Lyrie presses her hands to the broken thing and closes her eyes. Her brow furrows with effort. For a moment nothing happens. Then — a soft green glow. The cracks knit together."
          }
        },
        {
          "type": "repair_item",
          "params": {
            "target": "target",
            "repair_amount": 5,
            "message": "The item feels stronger in your hands."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `repair_item` — restores `uses` or a new `durability` field on a target item. If no durability system exists yet, this effect seeds the schema discussion for one.

### 14. Glimpse of the Lost Path
**Life memory**: *The Present* (Age 79) — three days lost in the woods. "I think I'm going the right way. I'm probably not."  
**Trigger**: `on_use`  
**Effect tier**: Existing (`scry`) + proposed `set_way_hint` (way metadata update).

```json
{
  "name": "Glimpse of the Lost Path",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "Three days lost in the woods. She learned to ask the forest for directions. Not a map — just a feeling, a pull, a sense of which way leads home. It's not always right, but it's always hopeful.",
  "tags": ["spell", "magic", "navigation", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "scry",
          "params": {
            "target": "nearest_way_out",
            "message": "You catch a glimpse of a familiar landmark — the village, the well, the tree with the low branch. You think you know which way to go."
          }
        },
        {
          "type": "set_way_hint",
          "params": {
            "way_id": "nearest_way_out",
            "hint": "This way feels like it leads toward something familiar.",
            "duration": 30,
            "message": "An exit nearby seems to hum with a faint, welcoming pull."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `set_way_hint` — adds a temporary narrative hint to a way/node. Displayed in look/examine outputs and way tooltips for `duration` ticks.

### 15. Hearth Ward
**Life memory**: *The Exile Scare* (Age 62) aftermath — she did chores for everyone to make amends. Learned that protection is quieter than beauty.  
**Trigger**: `on_use`  
**Effect tier**: **Proposes new effect**: `ward_area` — grants a defensive bonus or condition resistance within an area for a duration.

```json
{
  "name": "Hearth Ward",
  "actions": "examine,use",
  "current_state": "normal",
  "description": "A protective blessing learned from watching the village elders. Lyrie doesn't have the precision for grand wards, but she can make a small, wobbling circle of safety around herself. It's not much, but it's home.",
  "tags": ["spell", "magic", "ward", "protection", "elven"],
  "triggers": [
    {
      "trigger_type": "on_use",
      "effects": [
        {
          "type": "ward_area",
          "params": {
            "radius_areas": 1,
            "duration": 50,
            "defense_bonus": 2,
            "resistance": "cold",
            "message": "A warm, fuzzy feeling settles around you. The cold softens at the edges of your senses."
          }
        },
        {
          "type": "adjust_environment",
          "params": {
            "temperature": 3,
            "light": 10,
            "target_node": "self",
            "message": "A small, warm circle of light surrounds you."
          }
        }
      ]
    }
  ],
  "uses": -1,
  "weight": 0.1
}
```

**New feature proposal**: `ward_area` — grants a buff to all friendly characters within `radius_areas`. Supports `defense_bonus`, `resistance` (element/status), and `auto_fail_saves` suppression.

## Companion Items / NPCs Needed

| Name | Type | Purpose | Source |
|------|------|---------|--------|
| `fluffy` | Item or simple NPC | The rock sheep from *The Lost Sheep*. Conjured by *Conjure Fluffy*. | New |
| `vincent` | Environmental NPC | The grapevine from *The Grapevine*. Responds to *Whisper of Green*. | New |
| `chicken` | Simple NPC | Transmutation target for *Transfigure: Poultry*. | New |
| `everflame_ember` | Item (existing) | Persistent flame companion for *Ember Companion*. | `data/library/items/everflame_ember.json` |
| `flowers` | Item (existing) | Spawned by *Bloom of the Well* and *Fountain of Blossoms*. | `data/library/items/flowers.json` |
| `white_feather` | Item (existing) | Comedy residue from failed *Transfigure: Poultry*. | `data/library/items/white_feather.json` |

## New Feature Proposals (Summary)

| Effect | Spells | Description |
|--------|--------|-------------|
| `polymorph_target` | Transfigure: Poultry | Transform a target item/NPC into another library template for `duration` ticks, then revert. |
| `create_illusory_companion` | Conjure Fluffy | Spawn a temporary NPC with custom dialogue, follows caster, vanishes on duration/area leave. |
| `broadcast_emotion` | Siren's Lullaby | Shift `emotion.current` for all characters within `radius_areas`. |
| `repair_item` | Mending Touch | Restore `uses` or `durability` on a target item. Seeds durability schema if absent. |
| `reveal_hidden` | Vincent's Embrace | Temporarily set `hidden: false` on nearby items/NPCs/ways. |
| `transform_area_theme` | Fountain of Blossoms | Temporary area overlay (visual/scent/sound theme) with auto-revert. |
| `bind_companion` | Ember Companion | Persistent summoned entity that follows caster across areas, retains its own triggers. |
| `set_way_hint` | Glimpse of the Lost Path | Temporary narrative hint on an exit, shown in look/examine outputs. |
| `ward_area` | Hearth Ward | Area-of-effect buff: defense bonus, elemental resistance, duration-based. |
| `plant_whisper` | Whisper of Green | Plants can `llm_respond` as slow, patient entities with memory of prior interactions. |

## Implementation Plan

1. **Implement new effects** in `engine/trigger_system.py` (or new `engine/spell_effects.py` if volume warrants) — prioritize by spell count: `polymorph_target`, `repair_item`, and `ward_area` are the highest-value because they unlock entire gameplay loops.
2. **Create companion items/NPCs**: `fluffy`, `vincent`, `chicken` in `data/library/items/` and `data/library/characters/`.
3. **Create spell item JSONs** in `data/library/items/` using the specs above.
4. **Assign spells to Lyrie**: add the completed item `library_id`s to `inventory` in `data/library/characters/Lyrie.json`.
5. **QA**: run `python -m pytest tests/ -q -k "trigger"` and manual playtest of each spell in a test scenario.

## Verification

- All 15 spells import cleanly from the library browser.
- Existing-effect spells fire correctly on first manual test.
- New-effect spells compile through the trigger validator and fail gracefully if the effect is not yet implemented.
- Lyrie's character file loads without JSON errors after spell inventory assignment.



---

## todo/items/task-433-character-inscription-persistent-notes.md

---
type: task
status: todo
area: items
priority: medium
---

# task-433: Agent-reachable inscription (task-53 follow-up)

**Filed:** 2026-09-21
**Builds on:** [[dev_tasks/review/items/task-53-use_item_with_parameters|task-53]]
(Use Item with Parameters — `use pen on paper "text"` → `on_use_on` →
`set_description`/`append_description`, `{params}` templating; **implemented,
In Review**).
**Relates:** task-160 / task-363 (structured actions; stopping *accidental*
inscription), task-299 (long-distance communication — letters), task-423
(background social interactions), task-403 (unified memory/knowledge).

## Why this exists

task-53 built the **engine half**: a quoted `use <tool> on <target> "<text>"`
carries `params` into the `on_use_on` trigger context, and effects can render
`{params}` (plus the hardcoded `[Inscribed: …]` description append at
`engine/items/use_actions.py:266-277`). That works for an authored human-driven
pair.

What task-53 does **not** cover is everything needed for characters to do it on
their own, intentionally, in a world that can then read it back. Verified
2026-09-21:

1. **No agent can reach it.** The LLM emits a structured action
   `{action, item, target, speech, emote, …}` with **no text field**
   (`static/js/agent/prompt-builder/system-prompt.js`,
   `agent/action-normalizer.js`), so it can only produce `use <tool> on
   <target>` — never a `params`. The tool path
   (`tools/game_tools.py:224`) calls `use_item_on(item_name, target)` with no
   `params` either.
2. **It is un-gated and accidental.** task-160/363 document
   `use create flame on dried flower crown` *inscribing* "flower crown" onto a
   crown because `"flower crown"` was quoted. Nothing checks that a tool is a
   writing implement or a target is writable. task-53's path inherits this.
3. **`{params}` only works where a trigger exists — none does.** No authored
   `ink_pen`, `parchment`, `pencil`, `journal`, `notebook`, `letter`
   (`data/library/items/`) or the Ink Pen/Parchment in `The Valerious Case.json`
   carries an `on_use_on` trigger. The capability has no content using it.
4. **`set_description` overwrites, and targets a literal node id.**
   `engine/effect_handlers/properties.py:71-109` — the value is rendered, but
   the target is a literal node id ("self" fails), so generic "the paper in my
   hand" is not expressible. Overwriting `description` is also lossy: no
   author, no tick, no structure, mixed with authored prose.
5. **Reading back is unaddressed.** `read` is still an `examine` alias
   (`routes/action_handlers.py:217-220`); there is no inscription block or
   `read`-prioritises-note behaviour.
6. **Narration does not persist, and should not.** When the LLM narrates "she
   scribbles 'DONT GO HERE' on the paper", that prose is browser-only
   (`static/js/narration-ui.js:209-232`, `static/js/agent-engine.js:650-663`,
   IndexedDB in `static/js/stream/stream-persistence.js`) — never POSTed, never
   serialized.

## Design (the delta only)

1. **Agent reachability.** Add a `text` field to the structured action schema,
   teach it in the system prompt, and have the normalizer emit an
   unambiguous inscription form (an `inscribe`/`write` verb, or
   `use <tool> on <target>` carrying `text`). Forward it on the tool path.
2. **Gating, so it is deliberate.** Require the target to be writable
   (`writable`/`paper`/`book`/`sign`/`wall`) and the tool to be a writing
   implement (`pen`/`pencil`/`quill`/`charcoal`/`chalk`). Ordinary
   `use X on Y` must never inscribe (keeps task-363 fixed).
3. **Authoring parity + content.** Ship real pen/paper/noticeboard items with
   the trigger, so the mechanism has something to drive.
4. **Structured store.** Prefer `properties.inscriptions: [{by, tick, text}]`
   over overwriting `description`; render a "Written here:" block on
   `examine`. Keep the legacy `[Inscribed: …]` string readable (or migrate it).
5. **Read-back.** Decide whether `read` stays an alias with an inscription
   block, or becomes a first-class verb that surfaces notes first.
6. **Limits.** Max length, control-char stripping, cap per item, author+tick.
7. **Narration stays flavor** — never commit world state from narrated prose.

## Acceptance

- An LLM agent inscribes chosen text onto a writable item with a writing tool;
  it persists in `Node.properties` and survives save/load.
- A different character `examine`/`read`s it and sees text, author, and tick.
- Non-writable target / non-writing tool reject gracefully.
- Ordinary `use X on Y` never inscribes (task-363 regression stays green).
- An authored pen+paper pair works end to end (task-53 path retained).

## Non-goals

- Re-implementing task-53's params/trigger plumbing.
- Rich text, images, forgery, signatures.
- A world-wide message board (task-299).



---

## todo/items/task-450-duplicate-item-instances-and-carry-equipped-invariant.md

---
type: task
status: todo
area: items
priority: medium
---

# task-450: Duplicate item instances and the carried+equipped invariant

**Filed:** 2026-09-22, split out of bug-25. (Renumbered from 445 to avoid the
id collision with `done/characters/task-445-character-expression-packs.md`.)

## Why

bug-25 (take/wear no-op messaging) was closed by the engine-side wording fix, but
its live repro only happens when one character holds **two same-named item
instances** (one carried, one worn) — or a single instance carries both a
`CARRYING` and an `EQUIPPED` edge. The messages are then technically correct
(`take` → "already carrying", `equip` → "already wearing") yet read as a
contradiction, and the LLM spirals.

Evidence: playtest "John two / Jane three" (2026-08-30), plus the original
taco_bell case where miki spawned wearing one Blue Butterfly Earring and carrying
a second. Scenario names suggest population/dressing duplication; `equip_item`
removes the `CARRYING` edge, so a single node normally cannot hold both — the
both-edge state comes from load/legacy/test paths that add `CARRYING` without
removing `EQUIPPED` (`serialization_legacy.py`, `routes/library_ops.py`,
`engine/dressing.py` + `equip_item` when seeding).

## Goal

1. **Find the duplication source.** Identify where a character can end up with
   two same-named item nodes (dressing, library population, scenario assembly,
   or the `kraktooth` character duplication tracked in task-408) and stop it at
   the source rather than deleting copies after the fact.
2. **Enforce the invariant at the engine boundary.** An item node must never
   hold both `EDGE_CARRYING` and `EDGE_EQUIPPED` to the same character. Audit
   every `EDGE_CARRYING` add site (grep `type=EDGE_CARRYING`) and make
   equip/transfer/load converge on exactly one edge per item→owner; add a
   load-time normalizer/validator warning when both are present in a save or
   scenario.
3. **Expose the state, don't paper over it.** With the invariant enforced, the
   bug-25-class confusion disappears; no new user-facing string is needed.

## Acceptance

- A save or scenario that contains an item with both edges loads with exactly
  one (equipped wins) and logs a single warning.
- Dressing/population a character who already wears an item does not create a
  second same-named node; a test asserts one node per equipped item.
- `take`/`equip` on any legitimate state never produce the carrying-vs-wearing
  contradiction.

## Non-goals

- Changing the bug-25 take/equip wording (already shipped).
- Character-node dedup (tracked separately in task-408).



---

## todo/items/task-493-item-part-component-model-for-devices.md

---
type: task
status: todo
area: items
priority: medium
---

# task-493: Item part/component model for devices

**Filed:** 2026-09-23
**Related:** task-299

## Goal

Define and implement the 'device assembled from items' model agreed in the task-299 discussion: parts are child items of a parent (non-takeable by default by omitting 'take' from actions, so no new edge type is required), each part carries its own triggers/state/uses, charge is the generic 'uses' rather than a new 'power' property, and depletion uses the existing patterns (carried lit -> unlit + on_depleted; detach/break per part). Cover addressing/naming, and align prompt visibility with engine/item_reach (single-level, state-blind today vs any-depth, state-gated). No per-item named verbs.

## Acceptance

- A device is a parent item with child part items; a part with no `take` in `actions` cannot be taken/dropped/stolen/put (tested), while staying reachable/usable via `item_reach`.
- Charge uses the generic `uses`; no new per-device-type property (no `power`/`charge` field) is added to the base item.
- Part depletion has an explicit, chosen semantic (e.g. carried lit → `unlit` + `on_depleted`) and does not silently detach unless intended (tested).
- Prompt visibility agrees with `item_reach`: depth and container-state gating match (fix the single-level, state-blind client listing).
- A worked example (e.g. a phone with a battery part) is authored in the library and exercised in a test.



---

## todo/refactor/task-218-agent-engine-clean-code-extraction.md

# Task 218 — agent-engine.js clean-code extraction

## Status
Done — implemented 2026-08-12

## Summary
Split `agent-engine.js` (892 lines) into focused modules following the existing modularization plan.

## Files changed
- `static/js/agent/action-normalizer.js` — new
- `static/js/agent/response-parser.js` — new
- `static/js/agent/threat-detector.js` — new
- `static/js/agent/agent-state.js` — new
- `static/js/agent/plan-tracker.js` — new
- `static/js/agent-engine.js` — slimmed from 892 to ~480 lines
- `static/js/agent/plan-manager.js` — updated to use PlanTracker
- `static/js/shared/json-utils.js` — added `repairJSON()`
- `static/js/event-stream.js` — raw LLM bubbles inside turn cards + filter recursion
- `templates/index.html` — added script tags for 5 new modules

## What was extracted

| Module | Methods moved | Lines saved |
|--------|--------------|-------------|
| `action-normalizer.js` | `_validateAction`, `_normalizeStructuredAction`, `_extractSpeechVolume`, `_volVerb` | ~80 |
| `response-parser.js` | `_parseObservation`, `_parseReaction`, `_parseResultReaction`, `_parseDecisionWithSpeech`, `_extractMemory` | ~120 |
| `threat-detector.js` | `_getThreatAlert` | ~50 |
| `agent-state.js` | `_isBusy`, resting/unconscious maps | ~60 |
| `plan-tracker.js` | `_trackPlanStep`, `_shouldReplan`, plan state maps | ~60 |

## agent-engine.js now owns
- `step()` orchestrator (reactive + non-reactive)
- `_runDashFollowUp`
- `_callLLM` / `_callLLMMessages` / `_showManualPrompt`
- `start()` / `stop()` / `reset()` / `stepOnce()`
- `getHistory` / `nudge`
- `_surfaceRejectedAction`
- `_checkCancel`

## Verification
- `node --check` passes on all 8 modified/new JS files
- Backend pytest: 856 passed (11 pre-existing trigger_system failures, unrelated)
- Frontend LLM tests: 16/19 passed (3 failures need running server, pre-existing)



---

## todo/refactor/task-332-migrate-legacy-item-effect-props-to-triggers.md

---
id: 332
title: Migrate Legacy Item Effect Props to Triggers, Then Remove Support
status: todo
priority: medium
created: 2026-08-23
updated: 2026-08-23
tags: [refactor, engine, items, deprecation, data-migration]
---

# Migrate Legacy Item Effect Props to Triggers, Then Remove Support

## Summary

The legacy consumable shortcut `effect_stat` / `effect_amount` / `effect_target` must be
**migrated to trigger-based functionality** across all scenario/library data (especially
the mansion scenarios), after which engine support is removed. Not a blind nuke — every
functional use gets an equivalent `on_use`/`on_eat`/`on_drink` trigger first.

## Survey (2026-08-23)

461 items across 15 files carry at least one of the three keys:

| File | Items | Notes |
|---|---|---|
| `scenarios/mansion2.json` | **172** | the real migration target — mostly `inv_*` character inventory items |
| `scenarios/pines.json` | 97 | |
| `scenarios/world_template.json` | 62 | incl. `item_hand_lamp` light variant |
| `scenarios/testapartment.json` | 47 | |
| `scenarios/labs.json` | 31 | |
| others (morphocene, corsair, deepseek dump, apartment, art_heist, heist) | 38 | |
| `scenarios/mansion.json` | 1 | effectively clean |
| `library/items/*.json` | 3 | photograph, portrait_e2e1ec7b, table_35eb71c1 |

Breakdown by content:
- **315 items: keys present but `effect_stat: None`** — pure save pollution, safe to strip.
- **~132 functional vital items** — `hunger`/`Hunger` (27), `thirst` (11), `energy` (25),
  mixed casing; `target: "player"`; e.g. `inv_Elena Vance_protein_bar` (Hunger 35),
  `inv_Miki_portable_charger` (Energy 5). All fire via `action: "use"`.
- **14 light items** — `effect_stat: "light"`, `effect_target: "room"` (e.g.
  `item_hand_lamp` amount 60, `pines` miki phone amount 35): legacy room-light change.

## Implementation

### 1. One-off migration script: `tools/migrate_legacy_item_effects.py`

Runs over `data/scenarios/*.json`, root `world_template.json`, and
`data/library/items/*.json`. Rules, in order:

| Condition | Action |
|---|---|
| keys present, `effect_stat` falsy | strip keys (no behavior lost) |
| stat ∈ {hunger, thirst, energy} any casing, target player/self | normalize casing to vitals key (`Hunger`/`Thirst`/`Energy`), append inline `properties.triggers` entry `{trigger_type:"on_use", effects:[{adjust_vital {stat, -amount? sign-preserving}, target self}]}` — for graph-format scenario nodes, emit `logic_trigger` node + `triggers` edge instead (guide §20.6) |
| stat == `"light"`, target room | DEAD DATA today — nothing reads it for items (`item_actions.py:1552–1570` only matches vitals keys). Native system = `light_source` tag + `light_level` + `current_state` lit/unlit (`lighting.py:78` sums lit items' `light_level`; `toggleable_items.py:62` flips states). Migration per item: ensure `light_source` tag exists, set `light_level` from `effect_amount` **if the item has no explicit `light_level`**, ensure a `toggle`/`light` action exists — THEN strip the legacy props. Items already carrying an explicit `light_level`: strip directly |
| anything else | leave untouched + report for manual review |

Script must be idempotent, dry-run by default (`--apply` to write), and print a
per-file before/after count.

### 2. Engine removal (after migration lands)

- Delete legacy read block `engine/item_actions.py:1552–1570`.
- Audit `engine/item_actions.py:1730–1732` (`effect_target == "connection"` on ways) —
  separate variant; confirm zero data hits before removing.
- Stop persisting the three keys in save serialization; scrub-on-load for old saves.

### 3. Docs

ScenarioCreationGuide §2.3 DEPRECATED banner → flip wording to "removed"; §20.6 stays as
the canonical pattern.

## Acceptance Criteria

- [ ] `rg "effect_stat|effect_amount|effect_target"` over `data/scenarios/`,
      `data/library/`, `engine/`, `static/js/` returns zero production hits.
- [ ] mansion2.json inventory items still restore vitals when used (spot-check 5).
- [ ] hand_lamp-style lights still work natively.
- [ ] Old saves containing the props load cleanly post-removal (scrub path).
- [ ] pytest green (`not mcp and not emote`).



---

## todo/refactor/task-440-split-the-backend-runner-up-files.md

---
type: task
status: todo
area: refactor
priority: low
---

# task-440: Split the backend runner-up files

**Filed:** 2026-09-21
**Supersedes:** task-314's backend scope (which was measured 2026-09-21 and is now closed)
**Related:** task-83 (code readability), task-218 (the module-per-concern shape this follows)

## Goal

Extract focused modules from the backend files that outgrew single-file ergonomics.
**One file per commit, no behaviour change** — extraction only, public imports and APIs
stable, suite green after each.

## Measured targets (2026-09-21)

| File | Lines | Suggested seam |
|------|------:|----------------|
| `routes/graph_ops.py` | 1355 | second pass: split by operation family (node CRUD / edges / batch / import-export) |
| `routes/action_handlers.py` | 1301 | second pass: split by verb family |
| `engine/tick_manager.py` | 1101 | extract the tick phases (vitals / environment propagation / triggers / activities) from the orchestrator |
| `engine/movement.py` | 1098 | split traversal rules from area/way construction |
| `engine/traits.py` | 1096 | split the definition catalog from event dispatch |
| `routes/library_ops.py` | 1084 | second pass |
| `engine/matching.py` | 697 | lower priority — resolve only if it keeps growing |
| `engine/equipment.py` | 754 | lower priority |
| `engine/trigger_validator.py` | 821 | lower priority (also touched by task-393) |

Also carried over from task-314's wave reports: `triggers/testing.py` duplicates the
template-context block from `triggers/execution.py` — de-duplicate while splitting.

**Tracked but not to split:** `engine/serialization.py` (509) already imports
`serialization_template` + `serialization_legacy`; `engine/player_conditions.py` (841)
was already extracted from `player.py`.

## Approach

1. **One file at a time.** Start with the smallest target that has a clean seam, as the
   proof of pattern, then move up. Do not batch.
2. **No behaviour change.** Extraction only. Keep public imports/API stable, move public
   API re-exports up to the host module.
3. **Record what moved** in the task file as a table (module → lines → what moved), the
   shape task-314's wave-1 table used.
4. Verify per extraction: `python -m pytest tests/ -q -k "not mcp and not emote"`.

## Acceptance

- Each split lands with the host file's line count materially reduced and the package
  existing, verified by measuring both.
- No test file changes required beyond `mock.patch` targets that moved (record them).
- The suite stays green per extraction.

## Non-goals

- Behaviour changes, renames of public APIs, or architectural redesign.
- Chasing a line-count target — a file that is cohesive at 900 lines stays 900 lines.
- The frontend/JS and test splits (task-441).



---

## todo/refactor/task-441-split-frontend-giants-and-trigger-tests.md

---
type: task
status: todo
area: refactor
priority: low
---

# task-441: Split the frontend giants and the trigger test module

**Filed:** 2026-09-21
**Supersedes:** task-314's frontend and test scope
**Related:** task-216 (trigger editor inspector work), task-218 (the module-per-concern shape)

## Goal

Extract focused modules from the oversized JS files, and split the single trigger test
module so failures isolate cleanly. **One file per commit, no behaviour change.**

## Measured targets (2026-09-21)

| File | Lines | Suggested seam |
|------|------:|----------------|
| `static/js/inspector/agent-view.js` | 2276 | sub-views: memory, plans, vitals, relationships, paperdoll (task-314's wave-2 attempt produced `inspector/agent/agent-header.js` and was **abandoned** — that orphan was deleted 2026-09-21; restart from the live file, do not resurrect the snapshot) |
| `static/js/shared/trigger-graph.js` | 2116 | layout/rendering from node/edge editing |
| `static/js/shared/trigger-editor.js` | 2022 | rendering vs validation vs serialization |
| `static/js/item-library.js` | 1401 | list/editor/import from rendering |
| `static/js/main.js` | 1060 | init wiring and cross-module event subscriptions |
| `tests/test_trigger_system.py` | 2724 | split by subsystem (evaluation, effects, conditions, scheduling) — 14 classes in one module |

`static/js/library-browser.js` overlaps `item-library.js` — decide ownership before
splitting either.

## Approach

1. **One file at a time.** Pick the smallest target first as the proof of pattern.
2. **No behaviour change.** Keep `window.Foo` namespaces and re-export moved members as
   thin delegates where call sites use them (the `graph/projector.js` pattern in
   task-314's wave 1).
3. **Add the `<script>` tag in the same commit.** Task-314's wave 2 left
   `way-view-triggers.js` / `way-view-connections.js` unloaded and threw on open for two
   files; the orphan above is the other half of that failure mode. Verify with
   `node --check` on every touched file.
4. **Record what moved** as a table in this file.

## Acceptance

- Each split lands with the host file's line count materially reduced, the new module
  loaded by `templates/index.html` (if browser-global), and no orphan left behind.
- `node --check` clean on all touched JS; `node tools/unit/run.cjs` still green except
  known pre-existing failures.
- For the test split: each new test module runs standalone, and the total test count is
  unchanged.

## Non-goals

- Behaviour changes or UI redesign.
- `static/js/graph/network-manager.js` — already split in task-314 wave 1
  (`projector` / `overlays` / `tooltips` / `focus`).
- Backend splits (task-440).



---

## todo/refactor/task-454-save-list-must-not-parse-every-save-file-on-each-modal-open.md

---
type: task
status: todo
area: refactor
priority: medium
---

# task-454: Save list must not parse every save file on each modal open

**Filed:** 2026-09-22
**Related:** task-401, task-402

## Goal

Make `GET /api/save-games` cheap regardless of how big the saved worlds get.

`list_save_games` (`routes/saveload.py:248-283`) walks `saves/` and **fully
`json.load`s every file** to read `_save_metadata` and to count
`len(data['players'])` / `len(data['areas'])`. That is an O(total bytes) parse of the
whole saves directory on every modal open. The list already carries saves in the
hundreds of KB; `task-401`/`task-402` are explicitly moving toward large worlds where
one save is megabytes and the directory holds many.

## Options

1. **Metadata sidecar / index.** Write a small `<file>.meta.json` (or one
   `saves/index.json`) at save time holding filename, name, scenario, timestamps,
   tick/turn/player, version, schema_version, players, areas, size. List reads only
   those; invalidate by comparing mtime+size.
2. **Extend the in-file metadata.** Store `players`/`areas` counts in `_save_metadata`
   at save time, then list only needs the metadata. A full parse is still required to
   reach it unless combined with a small header read, so combine with (1) or (3).
3. **Lazy per-row detail.** Return filename + cheap `os.stat` fields for the list and
   fetch metadata only for rows the user expands. Bigger UI change.

Prefer (1) with (2): a metadata index keyed by filename, verified against
`mtime`+`size`, falling back to a parse only when the index is missing/stale. A stale
or corrupt entry must self-heal, never crash the list.

## Acceptance

- [ ] Opening the modal with N large saves does not read the full body of every file;
      a benchmark or log makes the difference visible (ties to task-402).
- [ ] The rendered list is unchanged for existing saves (stats, autosave pinned top).
- [ ] Adding/overwriting/renaming/deleting a save updates or invalidates its index
      entry; an out-of-band file edit (external agent, git checkout) is detected and
      refreshed.
- [ ] A malformed save or index entry degrades gracefully (row still appears, no 500).

## Files

- `routes/saveload.py` — `list_save_games` (248-283)
- `routes/helpers.py` — write the index/metadata at save/autosave time
- `tests/test_saveload.py` — index hit/miss/stale coverage



---

## todo/refactor/task-456-split-saveload-view-concerns-and-extract-the-save-row-template.md

---
type: task
status: todo
area: refactor
priority: low
---

# task-456: Split saveload-view concerns and extract the save-row template

**Filed:** 2026-09-22
**Related:** task-441, bug-40

## Goal

`static/js/ui/saveload-view.js` is 648 lines and mixes four unrelated concerns:

1. **Savegame CRUD** — `saveGame`, `saveGameToSlot`, `doRenameSave`,
   `loadGameList`, `doLoadGame`, `doDeleteSave`, `confirmDeleteAllSaves`.
2. **Scenario import/export** — `downloadWorld`, `uploadWorld`, `inspectImport`,
   `openImportPreview`, `saveScenarioToFile`, `persistScenarioName`,
   `initScenarioNameEditor`.
3. **World settings toggles** — `toggleSpectator`, `updateTimePerTick`,
   `updateClockStart`, `restartScenario` — these are not save/load at all.
4. **The list template** — a single large Lit expression with per-row inline styles
   and `window.SaveLoadView` global refs.

Two concrete extractions:

- Move the settings toggles (3) to their own module (e.g. a world/settings view).
  `restartScenario` may belong with the world toolbar rather than either.
- Extract `renderSaveRow(save)` as a small sub-template returning a Lit template,
  using CSS classes instead of the inline style string. This is also the natural home
  for bug-40's badge fix and for task-455's row interactions, so land those together
  if the timing allows.

Follow the repo module conventions: keep the `@module`/`@contributes` header current
(`python tools/js_module_index.py --write`), add the `<script>` tag in
`templates/index.html` for any new module, and check `tools/unit/run.cjs`'s module list
if portable logic is introduced.

## Acceptance

- [ ] `saveload-view.js` contains only save/load concerns; spectator/time/clock
      moved out and still reachable from wherever they are rendered today.
- [ ] `renderSaveRow` is a named function; the list render no longer builds badge/row
      markup as concatenated HTML strings.
- [ ] Behavior is unchanged apart from the bug-40 badge fix: autosave pinned top,
      stats line, 💾/✏️/🗑 buttons.
- [ ] `node tools/unit/run.cjs` passes, `npm run lint` passes, and
      `python tools/js_module_index.py --check` passes.
- [ ] No new lines added to `templates/index.html` script list unless a new module was
      actually created.

## Files

- `static/js/ui/saveload-view.js` — split
- `static/js/ui/<new settings view>.js` — extracted toggles
- `templates/index.html` — script tags
- `static/css/style.css` — `.save-game-item` row classes



---

## todo/refactor/task-491-single-source-of-truth-for-action-verbs-scoped-registry.md

---
type: task
status: todo
area: refactor
priority: medium
---

# task-491: Single source of truth for action verbs (scoped registry)

**Filed:** 2026-09-23
**Related:** task-299

## Goal

Consolidate the action-verb definitions that currently drift across engine/triggers/ui.py:_get_available_actions, static/js/agent/action-normalizer.js VALID_VERBS/MATURE_VERBS, static/js/agent/prompt-builder/contextual-actions.js BRACKET_ORDER, static/js/agent/prompt-builder/system-prompt.js prose, routes/action_handlers.py dispatch, and engine/autocomplete.py. One scoped registry (id, aliases, scope command/item/meta/social/movement/mature, target_schema, cost_key, mature_gate, bracket_order) that the dispatcher, UI buttons, agent normalizer, bracket builder, prompt prose and autocomplete all read. Generate the LLM verb list instead of hand-maintaining prose; add a drift guard test.

## Acceptance

- A verb is declared in exactly one place; the dispatcher (`routes/action_handlers.py`), `engine/triggers/ui.py`, `action-normalizer.js`, `contextual-actions.js`, `system-prompt.js` and `engine/autocomplete.py` all derive their sets from the registry.
- The registry carries scope + metadata (`aliases`, `scope`, `target_schema`, `cost_key`, `mature_gate`, `bracket_order`).
- The LLM verb list is generated from the registry; mature verbs are gated by the same flag as today's `MATURE_VERBS`.
- A drift guard test fails when a surface declares a verb the registry doesn't (or omits one its scope should expose).
- Behaviour is unchanged: every verb the command surface accepts today still resolves.



---

## todo/refactor/task-83-code_readability_refactor.md

---
group: Tech Debt & Testing
wiki: "[[UI & Settings/Inspector Panels]]"
---
# Code Readability Refactor — Variable Naming & Comments

**Priority**: Low (ongoing)
**Status**: Ongoing — apply boy-scout rule when touching files for other reasons
**Note**: Not a blocker for merge. Deferred to post-merge cleanup passes.

---

## Summary

Large parts of the codebase, especially `virtual_world_engine.py` (~4600 lines), use cryptic single-letter variable names (`tn`, `ep`, `ef`, `rn`, `dn`, `sn`, `nid`, `v`, `ct`, `cv`, `tp`, `ns`, `lw`, `ni`) with no comments explaining intent. This makes the code harder to read, debug, and maintain.

## Goal

Improve readability without breaking anything. No functional changes.

## Approach

**Boy-scout rule** — clean up code as you touch it for features/bugfixes:

1. When modifying a function, rename its single-letter variables to descriptive names
2. Add a brief comment explaining what non-obvious blocks do
3. Never rename in isolation — always paired with a functional change to that area

## Worst Offenders (for reference when touching)

### `virtual_world_engine.py`

| Pattern | Example | Better Name |
|---------|---------|-------------|
| `tn` (target node) | `tn = self.graph.get_node(node_id)` | `target_node` |
| `ep` (effect params) | `ep = effect_params` | `params` |
| `ef` (effect type) | `ef === 'set_state'` | `effect_type` |
| `rn` (room node) | `rn = self.graph.get_node(target_id)` | `area_node` |
| `dn` (door node) | `dn = self.graph.get_node(way_id)` | `way_node` |
| `sn` (spawn node) | `sn = self.graph.get_node(spawn_id)` | `spawn_node` |
| `nid` (node id) | `nid = effect_params.get(...)` | `node_id` |
| `ct` (condition type) | `ct = condition.get("type")` | `cond_type` |
| `cv` (condition value) | `cv = condition.get("value")` | `cond_value` |
| `tp` (trigger type) | `tp = edge.properties...` | `trigger_type` |
| `ns` (new state) | `ns = effect_params...` | `new_state` |
| `lw` (locked with) | `lw = target_node...` | `required_key` |
| `ni` (normalized item) | `ni = item_node.name...` | `item_name` |

### `inspector.js` / `item-library.js`

| Pattern | Better Name |
|---------|-------------|
| `q('cls')` helper (single-letter query) | Keep as convention but comment at definition |
| `ef`, `ep`, `tp`, `ct`, `cv` (same as Python) | match engine naming |

## Guidelines for New Code

- No single-letter variable names (except loop indices `i`, `j`)
- Function-local temp vars are fine short (`key`, `door`, `item`) but not opaque (`tn`, `ep`)
- Add a comment for any block that isn't immediately obvious — especially trigger dispatch, effect execution, condition evaluation
- No action-at-a-distance: if a function depends on a subtle side effect, document it

## Verification

No functional changes — verify by:
1. Run `pytest tests/` before and after — same results
2. Reload the game and play through a basic interaction loop (look, move, take, use)
3. No change in behavior, only readability

## Files

- `virtual_world_engine.py` — primary target
- `app.py` — secondary target  
- `static/js/inspector.js` — tertiary
- `static/js/item-library.js` — tertiary
- Any other file touched during feature work


---

## todo/testing/task-413-simulation-tick-performance-baseline-and-guard.md

---
type: task
status: todo
area: testing
priority: medium
---

# task-413: Simulation tick performance baseline and regression guard

**Filed:** 2026-09-19  
**Depends on:** task-406, task-407 (the fixes this guards).  
**Related:** task-402 (world-scale projection benchmark) — different layer.

## Goal

Make per-tick simulation throughput measurable and protect it against
regressions.

## Problem

The hot-path cost was only discovered by profiling (trigger/exit plumbing, not
LLM). task-402 benchmarks **projection payload**, not the per-tick simulation
loop, and there is no committed baseline for ticks/sec, per-tick node/edge
visits, exit rebuilds, or `.lower()` calls.

## Changes

1. A repeatable benchmark command (extend `tools/soak_sim.py` or add
   `tools/bench_ticks.py`) that prints, with a fixed seed and scenario:
   ticks/s, nodes/edges visited per tick, exit rebuilds, `.lower()` calls, and
   character count.
2. A checked-in baseline report (date, host, counts).
3. A **marked** test that fails loudly when a scoped hot path regresses past an
   agreed factor.

## Acceptance

- One documented command reproduces the numbers.
- The baseline is published in the report.
- The guard fails on a deliberately reverted fix (prove it bites), then passes
  again when restored.
- It is not part of the ordinary unit suite; it runs explicitly.

## Non-goals

- Universal wall-clock targets before a host budget is chosen.
- Browser rendering benchmarks.

## Verification

- Run the command before/after task-406/task-407 and record the delta.
- Temporarily revert one fix to confirm the guard trips.

## Baseline — 2026-09-19 (after tasks 406/407)

- Command: `python tools/soak_sim.py --ticks 10080 --background-all --progress-seconds 1`
- Result (first pass): 10,080 ticks (7 in-game days) in 9m49s → 17.1 ticks/s.
- Result (second pass: lighting stamp/max + cheap edge moves): **10,080 ticks in
  ~56s → 181 ticks/s**, 23/23 alive, 0 deaths. Trace 4,459 entries; memories 17;
  graph 130 nodes. Survivor vitals identical to the slower run.
- Rate decline was diagnosed: `GameLogger.record_turn_event` rebuilt the whole
  `turn_events` list per append (O(n²) headless, ~17k entries). Fixed with
  turn-change pruning + a 2,000 cap. After the fix, profile call counts are flat
  early vs late (~2%); `record_turn_event` is out of the top 12.
- Absolute timings vary with host load (a week measured 56s one session, 71s in
  another where every early figure was ~2× slower) — compare call counts, not
  just wall time.

## Progress — 2026-09-19

Guard built as `tests/test_perf_guards.py` (9 tests). It asserts *shape*, not
wall time:

- `GameLogger.turn_events` stays capped and prunes on turn change (the O(n²)
  buffer fix).
- `remove_edge` unindexes one edge and does **not** call `_rebuild_indexes`.
- A direct `graph.edges.append(...)` is still found by the indexed lookups
  (lazy rebuild), so effect handlers that bypass `add_edge` stay correct.
- `_fire_turn_triggers` executes **zero** nodes when nothing owns the trigger,
  and exactly the owner when something does.
- Lighting: many dim sources do not stack (brightest wins), and the per-tick
  stamp is used until a graph mutation invalidates it.

Verified the guard bites: with the cap disabled, `turn_events` reaches 5,000 and
`test_turn_events_are_capped` fails. Full suite: **2840 passing**.
- Pre-fix reference: ~6–9 ticks/s, with the trigger/exit path responsible for
  ~187s of 247s in a 100-tick profile (~876 exit rebuilds and ~1M `str.lower()`
  per tick).
- Post-fix profile top costs: `lighting.get_ambient_light` (trimmed),
  `get_edges_for_target` call volume, background `move_to_area`,
  `Player.state`. The trigger/exit cost is gone from the hot path.
- Full suite: 2831 passing (0 failures) excluding pre-existing `test_mcp_*`.

Follow-ups spotted by the profile (candidates for a next pass): memoise
`_item_light_stats`/`get_ambient_light` with explicit lit-state invalidation,
reduce `Player.state` cost, and stop `remove_edge` from triggering a full edge
index rebuild.



---

## todo/testing/task-444-playwright-persistence-and-error-boundaries.md

---
type: task
status: todo
area: testing
priority: medium
---

# task-444: Playwright persistence, error-boundary and CI-runner suites

**Filed:** 2026-09-21
**Supersedes:** task-358 Phases 3–5 (Phases 1–2 shipped; that task is closed)
**Related:** `tools/test_helpers.cjs`, `tools/test_regressions.cjs`, `tools/test_all.cjs`

## Goal

The Playwright suite currently checks **presence and API responses**, not that the UI
persists state or degrades gracefully. Finish the three unstarted phases.

## Verified state (2026-09-21)

- Phases 1–2 landed: `tools/test_helpers.cjs` (103 lines) exports `startSession`,
  `checkConsoleErrors`, `switchTab`, `showAgent`, `api`, `getState`, `gameCmd`;
  `tools/test_regressions.cjs` (181 lines) covers the ten filed bugs.
- **Phase 3 (persistence): not started** — `grep 'page.reload' tools/` → 0 hits.
- **Phase 4 (error boundaries): not started** — `grep 'page.route' tools/` → 0 hits.
- **Phase 5 (runner): not started** — no `--suite` flag, no JUnit output.
- Corrected counts: `tools/` holds **28** `.cjs` files (not 12), and the helper is adopted
  by **2** of them (`test_regressions.cjs`, `test_trigger_search_select.cjs`); ~15 files
  have their own inline `pageerror` capture and ~10 have none. `tools/test_ways.cjs`
  **does not exist** (task-358 named it).

## Phase 3 — persistence (edit → save → reload → verify)

Cover the paths that actually lose data: edit a description field and reload; change a
dropdown; toggle a checkbox and confirm the backend changed; delete a trigger and confirm
it is gone; equip an item and confirm the paperdoll slot; move a character and confirm the
room changed. Pattern is already written in task-358's Phase 3 block — a test must fail
when persistence breaks, not merely exercise the handler.

## Phase 4 — error boundaries

Use `page.route()` to return 500s and assert the user sees a readable message rather than
a raw traceback; kill the server mid-session and assert a "connection lost" state rather
than an infinite spinner; send malformed data and assert client-side validation catches it.

## Phase 5 — CI runner

`--suite` (smoke / regression / full) plus JUnit XML. The smoke suite should cover the
critical paths in under 30 seconds.

## Acceptance

- At least one persistence test per Phase-3 bullet, and it fails if the save/reload path is
  broken.
- A mocked 500 produces a friendly message — the assertion explicitly rejects `Traceback`
  or `File "` in user-visible text.
- `--suite smoke` completes in <30s and writes JUnit XML.
- Any file the helper is wired into still passes.

## Non-goals

- **Wiring the helper into the remaining ~26 `.cjs` files.** Task-358 itself called this
  "mechanical, low value"; do it only where a file is being touched for another reason, or
  delete the file if it is dead. The two adopters are the ones that matter.
- Re-running the historical `153/153` / `14/14` counts — point-in-time, nothing contradicts
  them.



---

## todo/triggers/task-406-trigger-event-index-and-lazy-context.md

---
type: task
status: todo
area: triggers
priority: high
---

# task-406: Trigger dispatch by event index, standing-item ticks, lazy context

**Filed:** 2026-09-19  
**Depends on:** nothing. Additive; must not change trigger semantics.  
**Evidence:** goblin soak profile; `virtual_world_engine.py:971`/`:984`;
`engine/tick_manager.py:635–692`; `engine/triggers/execution.py:277`;
`engine/legacy_compat.py:57`.

## Goal

Make trigger dispatch **event-driven across every node type**, give standing
items a real tick path, and stop paying for triggers that do not exist — without
changing what any trigger does.

## Problem

1. `_fire_turn_triggers` (`virtual_world_engine.py:971`) and
   `_fire_time_triggers` (`:984`) iterate **every** node and skip
   `node.type not in ("area", "way", "character")`. Two consequences:
   - Every tick visits ~106 nodes even when **zero** carry a tick/time trigger
     (the goblin scenario has 0; its 11 triggers are `on_drink` / `on_eat` / …),
     so the whole sweep is waste.
   - `on_turn_start` / `on_turn_end` / time-of-day / moon triggers on an
     **item** never fire — only area/way/character are swept.
2. **Item `on_tick` is inconsistent, not absent** (corrects an earlier claim).
   `engine/tick_manager.py` fires `on_tick` for exactly two item states:
   - carried or equipped items (`:635–643`);
   - items sitting in an area with `current_state` in `("lit", "on")`
     (`:665–692`, the burn-down path).

   A **standing** item — a bush, nest, shrine — that is neither carried nor lit
   is never ticked, so an `on_tick` growth/regrowth trigger on it does nothing.
   Carried and lit items keep working and must not be double-fired.
3. `_execute_triggers` (`engine/triggers/execution.py:277`) builds the full
   template context (lines 323–375) **before** it fetches trigger edges
   (line 378). On the common no-match path all of that work is discarded.
4. Two context keys read the expensive `game_state.current_area` legacy
   property (`:341`, `:371`), which rebuilds an `Area` and its exits on every
   access (`engine/legacy_compat.py:57`) — so building a discarded context can
   rebuild the exits of the active area.

## Changes

1. **Event index.** Maintain a map from trigger event/type → set of source node
   ids, built from trigger edges (`trigger_type`, scalar or list), covering
   **all** node types. Owner: `graph.py`. Rebuild on
   `add_edge` / `remove_edge` / `load_from_dict` / `clear`.
2. **Index-driven sweep.** `_fire_turn_triggers` / `_fire_time_triggers` iterate
   the ids registered for the requested type(s) instead of
   `graph.nodes.values()`. Empty index → no work.
3. **Standing-item tick.** Register items carrying an `on_tick` trigger so they
   are ticked regardless of carry/lit state, without double-firing items already
   served by the carried/equipped or lit/on paths (dedupe by node id per tick).
4. **Short-circuit + lazy context.** In `_execute_triggers`, fetch and filter
   matching trigger edges first; return `[]` if none match. Build the context
   only when something will execute, and only fill keys referenced by the
   matched triggers' templates/effects.
5. **Cheap area in context.** Replace both `current_area` property reads with
   the already-resolved area id/name/environment (e.g. `_get_current_area_id()`
   + `graph.get_node`), so trigger context never rebuilds exits.

## Acceptance

- A standing, non-lit, non-carried item with an `on_tick` trigger is ticked
  exactly once per tick.
- Carried/equipped and lit/on items keep firing exactly as today (no double
  fire) — `test_carried_item_fires_on_tick` still passes.
- An item carrying an `on_turn_start`/`on_turn_end` or time-of-day trigger now
  fires.
- No behaviour change for area/way/character triggers; existing trigger tests
  pass unchanged.
- With the goblin scenario, a tick performs no trigger-context construction;
  the trigger path shows ~0 in the profiler.
- `_execute_triggers` on a node with no matching edge does not read
  `game_state.current_area`.

## Non-goals

- Changing the trigger authoring format, condition trees, or effect handlers.
- Removing or globally reworking the `current_area` property (see task-407).

## Verification

- Unit: standing-item `on_tick`; no double-fire when also carried/lit; item
  turn/time trigger; no-match `_execute_triggers` returns `[]` without context;
  index stays correct across add/remove/load.
- Profile: before/after `cProfile` over 100 ticks (ranking only, not timing).

## Progress — 2026-09-19

Implemented.

- `graph.py`: trigger-event index (`_trigger_index`, `get_trigger_sources`) built
  from `triggers` edges that carry a non-empty `trigger_type`; maintained on
  add/remove/load/clear. Faithful to `_execute_triggers`, so legacy-shape edges
  that never matched still do not match.
- `virtual_world_engine.py`: `_fire_turn_triggers` / `_fire_time_triggers` are
  now index-driven (visit only trigger owners, any node type) instead of
  sweeping every node.
- `engine/tick_manager.py`: standing items (not carried/equipped, not lit/on)
  now get `on_tick`, exactly once, without disturbing the carried/equipped and
  lit/on paths (`test_carried_item_fires_on_tick` still green).
- `engine/triggers/execution.py`: `_execute_triggers` fetches trigger edges and
  applies a cheap type pre-filter before building context; the expensive
  `current_area` property is replaced by area-id/node resolution with a
  duck-typed fallback.

Verified: 255 targeted tests + full suite (2835 passed, excluding pre-existing
`test_mcp_*`). One-week background soak: 10,080 ticks in 9m49s (17.1 t/s),
23/23 alive.



---

## todo/triggers/task-442-trigger-blueprint-runtime-compile-and-browser.md

---
type: task
status: todo
area: triggers
priority: high
---

# task-442: Trigger blueprint runtime compile + blueprint browser

**Filed:** 2026-09-21
**Supersedes:** task-351 Phases 2–3 (Phase 1 shipped; that task is closed)
**Related:** task-388 (trigger graph editor overhaul — defects #9–#11 are the compile-honesty findings to fix here)

## Goal

Make a saved trigger **blueprint** something the engine can actually run, and give
blueprints a real browser. Today a blueprint is a JSON document the editor can load and
compile to a graph patch, but **no Python code has ever heard of a blueprint** — nothing
materialises a blueprint into `logic_trigger` nodes + `triggers` edges at runtime.

## Verified state (2026-09-21)

- Phase 1 (node renderer, sockets, wires, inline editing, blueprint save/load/export/
  import, compile-to-engine, inspector + library integration) is **done** in
  `static/js/shared/trigger-graph.js` — `_serializeGraph` `:1622`, `compileToEngine`
  `:1984`, `compileToBehaviors` `:1832`, blueprint I/O `:1667-1765`.
- Blueprint storage is real: `POST /api/library/triggers`
  (`routes/library_routes.py:48-60`, `triggers` in `REGISTRY_TYPES`
  `routes/library_ops.py:16`) writes per-entry files under `data/library/triggers/`.
- **`grep blueprint *.py` → 0 hits.** Phase 3 is unstarted.
- Phase 2's two unticked boxes (directory exists, templates seeded) are actually
  satisfied — nine files in `data/library/triggers/`. What is missing is the **browser**:
  today only the in-editor `_loadBlueprint` picker (`trigger-graph.js:1714-1750`), a raw
  floating div.

## Slice 1 — blueprint → engine nodes (the point of the task)

Define the compile as a documented JSON contract plus a runtime materialiser, so
attaching a blueprint to a node creates ordinary `logic_trigger` nodes and `triggers`
edges — no parallel format, same as task-398's `GenerationPatch` principle.

## Slice 2 — condition branching must stop losing data

Two known dishonest compiles to fix (also tracked as task-388 defects #9–#11):

- `_traceGraph` (`trigger-graph.js:2082-2113`) **AND-folds every condition and keeps only
  a NO-branch message as `fail_message`**, dropping every other NO-branch effect.
- `compileToEngine` (`:1996`) **always emits `{operator:'and'}`** — there is no OR/NOT.

A branch's NO path must compile to engine conditions / effects, or the editor must refuse
to save it rather than silently discard it.

## Slice 3 — blueprint browser

A searchable picker over `data/library/triggers/` (the six seeded templates plus
user-saved ones), in the shape the item library already uses — not a floating div.

## Acceptance

- A blueprint with a condition branch round-trips into `logic_trigger` nodes + `triggers`
  edges and behaves correctly in the engine.
- No effect is silently dropped on save or compile: a NO branch with two effects produces
  two effects (or a visible refusal).
- OR/NOT conditions survive the round trip.
- The browser lists and searches `data/library/triggers/*.json`, and attaching a
  blueprint from it materialises the nodes.
- `node --check` clean on touched JS; `python -m pytest tests/ -q -k "not mcp and not emote"` green.

## Non-goals

- The editor's UI/UX overhaul (pan/zoom, wire deletion, undo) — that is task-388, and
  pan/zoom already exists (`trigger-graph.js:1113-1219`).
- Re-introducing `reduce_uses`: it does not exist in the effect registry
  (`engine/effect_handlers/equipment.py:182` has `adjust_uses`, which accepts a negative
  delta). Task-351's Phase-1 checkbox claiming it was added is false and has been
  corrected there.



---

## todo/ui/bug-42-delete-all-saves-also-deletes-the-autosave-slot.md

---
type: bug
status: todo
area: ui
priority: medium
---

# bug-42: Delete All saves also deletes the autosave slot

**Filed:** 2026-09-22
**Related:** task-365

## Symptom

The modal tells the user "🔄 Autosave is always current (pinned top)". The **🗑 All**
button contradicts that: after two confirms it deletes **every** file in `saves/`,
including `autosave.json`. The safety net the messaging promises is gone, and there is
no undo.

Two smaller problems in the same path:

- It issues one `DELETE /api/save-game/<filename>` per save — an N+1 round trip that
  also re-lists on each failure and can stop half-way, leaving a partial wipe.
- The double `confirm()` cannot be cancelled differentially (no "keep autosave"
  option), and deleting the autosave slot is not surfaced as its own choice.

## Root cause

`confirmDeleteAllSaves` (`static/js/ui/saveload-view.js:524-537`) lists all saves and
loops `api.deleteSaveGame(saves[i].filename)` with no exclusion for
`save.autosave === true`.

## Fix

1. Exclude the autosave slot from Delete All (`saves.filter(s => !s.autosave)`), and
   make that explicit in the confirm text ("Delete all N saves? Autosave is kept.").
2. Add a single bulk endpoint (e.g. `POST /api/save-games/delete-all` with an
   `include_autosave` flag) so the wipe is one request and can't half-complete.
3. Deleting the autosave specifically, if it should be possible at all, belongs on the
   autosave row itself (see task-455), not in the global wipe.

## Acceptance

- [ ] Delete All removes user saves but leaves `saves/autosave.json` in place and
      visible after the list refreshes.
- [ ] The confirm text states the count and that autosave is kept.
- [ ] A bulk delete is a single request; a mid-way failure does not leave a silently
      partial wipe.
- [ ] Cancelling either confirm deletes nothing.

## Files

- `static/js/ui/saveload-view.js` — `confirmDeleteAllSaves` (524-537)
- `routes/saveload.py` — save-game routes (new bulk endpoint)
- `static/js/api.js` — client method for the bulk endpoint
- `tests/test_saveload.py` — bulk-delete + autosave-retention coverage



---

## todo/ui/task-388-trigger-graph-editor-overhaul.md

---
group: UI
---

# Trigger/Behavior Graph Editor Overhaul: Pan, Zoom, Wire Clarity, Editing Power

**Filed**: 2026-09-02
**Priority**: High
**Status**: **Phase 1 implemented & tested** (2026-09-02) — Option A chosen; viewport rework live
in `trigger-graph.js`, verified by `tools/test_trigger_graph_viewport.cjs` (19/19 PASS).
**Predecessor**: [[task-351-trigger-graph-editor]] built the editor itself (in progress — its
Phase 2 blueprint browser and Phase 3 engine-side runtime compile are still open; this doc's
compile-honesty findings in defects #9–#11 feed directly into that Phase 3).

---

## Summary

`static/js/shared/trigger-graph.js` (the 🧠 Behavior Graph / 🔀 Trigger Graph modal) is a hand-rolled
node editor: absolutely-positioned `<div>` nodes + one SVG layer for wires. It has **no pan and no
zoom** (the Fit button is the only viewport control, and it corrupts the coordinate model), **wires
cannot be deleted or told apart** (all render as identical blue, including YES vs NO branches), and
several compile paths **silently drop user-wired data** on save. This doc is the research: current
state, defect list with line references, three enhancement options, a recommendation, and a phased plan.

## Current State

- Single IIFE `window.TriggerGraph`, ~1,520 lines, no build step (script tag in `templates/index.html:991`).
- Nodes are DOM `<div class="tg-node">` with live form fields inside (lit-html templates per node type
  in `NODE_DEFS`). Wires are cubic beziers in `#tg-svg`, positioned via `getBoundingClientRect()` math.
- Two modes sharing one editor:
  - `trigger` (⚡ Trigger → ❓ Condition → ⚡ Effect), compiled by `TG.compileToEngine`, with
    server-side Test/Validate (`/api/triggers/test`, `/api/triggers/validate-definition`).
  - `behavior` (🧠 Behavior → ❓ Condition → 🛠 Action / 🎭 State), compiled by
    `TG.compileToBehaviors`; **priority is derived from node Y position** on save, not from the
    Priority field shown in the node.
- Callers: `trigger-editor.js` ("🧩 Graph" button hands off / back), `behaviors-view.js`
  `openGraphEditor()` (all behaviors of a character at once).
- Graph format `{nodes:[{id,type,x,y,w,props}], wires:[{id,from:[node,socket],to:[node,socket]}]}`
  is persisted in blueprint library + character behaviors. It is fine and worth keeping.

## Defects Found (research audit)

### A. Viewport (the user-facing blockers)

1. **No pan.** Only `⊞ Fit` sets one CSS transform on `#tg-canvas` (`_fitView`, line ~800). Empty-canvas
   drag just deselects (`_onCanvasMouseDown`). No way to move the view.
2. **No zoom.** No wheel handler anywhere. Fit computes a scale the user cannot control or change.
3. **No grid/background.** Plain dark canvas — with no visual anchor, panning/zooming (once added)
   would feel floaty; today it just makes large graphs unreadable.
4. **Coordinate model breaks under any non-identity transform.** Fit is not just missing features —
   it actively corrupts interactions:
   - Node drag uses raw screen deltas (`n.x = sx + e.clientX - mx`, line ~1004) without dividing by
     scale → at Fit scale 0.6, nodes move 40% slower than the cursor.
   - `_getSocketCenter` returns *post-transform visual* coords, but SVG path coords are interpreted in
     *pre-transform canvas-space* and get the canvas transform applied again → any wire redrawn after
     Fit (node move, resize) detaches from its sockets. Fit looks right only until you touch anything.
   - Right-click node creation uses `clientX - rect.left` without inverse transform → new nodes spawn
     far from the cursor at zoom ≠ 1.
   - Root cause: screen space and world space are conflated. There is no `screenToWorld()`.

### B. Wires (clarity + the biggest functional gap)

5. **Wires cannot be deleted.** `Del` only deletes the selected node (`_onKeyDown`); the SVG layer has
   `pointer-events:none` and paths have no handlers; the context menu only opens on bare canvas.
   A single mis-wire forces deleting whole nodes.
6. **All wires are identical blue `#58a6ff`.** Condition nodes expose green ✓ / red ✗ sockets, but
   wires from both render the same — in the screenshot you cannot tell which branch a wire leaves.
   No arrowheads either; direction is guesswork on long wires.
7. **No cycle prevention.** `_onCanvasMouseUp` accepts any side-differing socket pair; the recursive
   tracers (`_traceGraph`, `_traceBehavior`) would infinitely recurse on save → stack overflow.
8. **Duplicate/reversed wires accepted.** Wiring input→output stores the reversed direction which the
   tracers then silently ignore; double-wiring the same pair creates two identical wires.

### C. Silent data loss on save (compile honesty)

9. **Fan-out is dropped.** `_traceGraph`/`_traceBehavior` follow only the *first* wire from an output
   (`wires.find(...)`). If a user wires one output to two actions, the second branch vanishes on save
   with no warning.
10. **Behavior-mode NO branches are discarded.** `_traceBehavior` explicitly ignores NO-branch actions
    (comment ~line 1317: "we don't fold NO actions into the YES path") — the editor happily renders
    and saves graphs that compile to less than they show. Trigger mode keeps only a NO-branch
    `message` as `fail_message`; all other NO effects are dropped.
11. **Behavior priority: UI lies.** The node shows an editable Priority field, but
    `compileToBehaviors` overwrites priority from sorted Y position (`count - rank`). Moving a behavior
    node vertically silently changes gameplay order; typing a priority does nothing.

### D. Interaction/rendering quality

12. **Full DOM rebuild on every click.** Node mousedown calls `_rerenderCanvas()` → all node DOM is
    destroyed and recreated (focus loss, flicker, O(n) per interaction). Selection should be a class
    toggle, not a rebuild.
13. **Field values commit on `onchange` only** — the model can be stale when Test/Validate/Save runs
    right after typing without blurring in the "right" order; combined with #12's rebuild-on-click
    this is race-prone.
14. **Escape closes the editor with no unsaved-changes guard** (`_onKeyDown` → `_close()`). Work lost.
15. **Missing editor power tools:** no multi-select / box-select, no copy/paste/duplicate, no
    undo/redo, no node collapse (`_expanded` is stored but never used), no snap-to-grid or alignment,
    no minimap, no canvas-wide node search (only the add-node menu has search), 16px socket targets,
    no touch support, no keyboard nudge, `prompt()`/`alert()`/`confirm()` for blueprint names.
16. Minor: `_collectBehaviorStates` builds a throwaway `entry` with a placeholder priority (dead code);
    node width fixed at 260px with no text overflow strategy.

## Options Considered

### Option A — Incremental overhaul of trigger-graph.js  ✅ Recommended

Keep the DOM-nodes + SVG architecture, node schemas, and compile pipeline. Add a real viewport layer
and wire interaction model.

- **Viewport**: one `#tg-world` container (nodes + svg inside) transformed by `{panX, panY, zoom}`;
  canvas stays untransformed. All pointer math goes through `screenToWorld()/worldToScreen()`.
  Wheel = zoom-to-cursor (0.25–2.0), empty-canvas or middle/space drag = pan, Fit = F, +/- buttons,
  zoom % indicator, dot-grid background sized by zoom, per-graph saved viewport.
- **Wires**: color per source socket (✓ green / ✗ red / gold trigger-behavior / blue action), arrowhead
  markers, invisible fat hit-path per wire → hover highlight, click-select, Del/right-click to delete.
  Reject cycles + duplicates at creation time with a toast.
- **Honesty**: badge or gutter warning on wires/branches that will not compile (fan-out beyond first
  wire, behavior NO-branch actions, reversed wires). Either warn or make the engine support them —
  but stop saving less than what is shown.
- **Rendering**: incremental updates (selection = class toggle; pan/zoom = one transform update;
  only wires recompute on node drag). Commit field values on `input` (debounced) instead of `change`.
- **Guard rails**: unsaved-changes guard on Esc/close, `localStorage` draft autosave, replace
  `prompt/alert/confirm` with the app's modal/toast helpers.
- **Layout**: keep authored positions, add a "✨ Tidy" button (simple layered column layout per
  behavior chain), snap-to-grid, align-selected.

Effort: ~700–1,000 lines changed/added, zero new dependencies, blueprint format untouched.
Risk: low-medium; the compile/trace code is only touched to add warnings, not to change semantics.

### Option B — Adopt a graph library

**vis-network** (already loaded for the world map) was evaluated first since it ships pan/zoom,
clickable edges, and a hierarchical LR layout for free — but it is a graph *viewer*, not a
blueprint *editor*: no port/socket model (edges bind node-to-node, so YES/NO branch attachment
points are lost unless socket nodes are faked and kept in sync during drags), no drag-to-connect
gesture (edge creation is data-driven only), and nodes are canvas-painted so the inline form
fields — a deliberate task-351 Phase 1 goal — cannot live inside nodes. Using DOM overlays glued
via `canvasToDOM` rebuilds the current architecture on top of vis with two systems to keep in
sync. A vis-based redesign is only attractive if the product moves to compact summary nodes +
a details panel (Unreal-style), giving up inline editing.

Other candidates:

- **Drawflow** — DOM-based like ours, HTML content inside nodes (fits the field-heavy nodes), built-in
  pan/zoom/wire deletion. Downside: effectively unmaintained; we'd still keep all compile code; styling
  to match the app is work; LGPL-ish MIT fine.
- **Rete.js v2** — excellent architecture (area plugin = pan/zoom/minimap, undo plugin, rearrange
  plugin), renderer-agnostic in theory. Downside: CDN/ESM-only integration in a no-build globals
  codebase is awkward (needs Vue render plugin for stock rendering); steepest learning curve.
- **LiteGraph.js** — the ComfyUI engine; canvas-rendered, insanely feature-complete (subgraphs, minimap,
  multi-select). Downside: canvas nodes make our rich HTML forms (datalists, periodic-drain grids,
  textareas) a fight; visual restyle is hard.
- React Flow / Baklava / JointJS / GoJS — wrong framework or license/commercial constraints.

Verdict: every option still requires keeping `compileToEngine`/`compileToBehaviors` and re-implementing
the field forms in the library's node format. We'd pay migration cost + dependency risk to get a
subset of Option A's list. Not worth it unless the editor grows subgraphs/macros.

### Option C — Full custom canvas engine (PIXI/LiteGraph-style)

Overkill for graphs of this size (dozens of nodes, not thousands). DOM nodes give us forms, datalists,
and Bootstrap styling for free. Rejected.

## Phased Plan (Option A)

### Phase 1 — Viewport: pan, zoom, fit, grid (the big visible win)
- Viewport state `{x, y, k}` + single transform container; `screenToWorld` used by every handler
  (fixes node-drag speed, wire geometry, and context-menu spawn positions in one sweep).
- Wheel zoom-to-cursor, drag/Middle/space pan, Fit (recompute + recenter), zoom controls + % badge,
  dot-grid background, persist viewport per graph in `localStorage`.
- Acceptance: after Fit, dragging a node keeps wires attached and tracks the cursor 1:1; new nodes
  appear under the mouse; smooth at 60fps with ~100 nodes.

### Phase 2 — Wires: clarity, deletion, safety
- Per-source-socket colors + arrowheads + animated dash on hover; fat invisible hit paths.
- Wire selection, Del deletion, right-click wire menu (delete); cycle & duplicate rejection with toast.
- Compile-honesty warnings (fan-out drop, behavior NO-branch drop, reversed wire) as badges in-canvas
  plus entries in the existing test/validate panel.
- Acceptance: every wire visible on screen can be identified by color and deleted without deleting nodes.

### Phase 3 — Editing power
- Undo/redo (serialize snapshot stack — cheap because the graph is already plain JSON).
- Multi-select (shift-click, box-select), group-drag, copy/paste/duplicate (Ctrl+C/V/D).
- Node collapse (`_expanded` finally used → header-only summary card), canvas node search (Ctrl+F),
  snap-to-grid + align, keyboard nudge (arrows), unsaved-changes guard, draft autosave.
- Field commits on debounced `input`; kill rebuild-on-click (class-toggle selection).
- Replace `prompt/alert/confirm` with app modals/toasts.

### Phase 4 — Scale & polish
- Minimap (bottom-right, click-to-jump), zoom-based LOD (collapse fields to summary line below ~0.6
  zoom, ComfyUI-style), render only nodes intersecting the viewport.
- Touch gestures (pinch zoom), node width auto-fit, state panel polish.

### Phase 5 — Behavior-mode UX (design decision needed)
- Replace priority-from-Y with an explicit, visible mechanism (drag-reorder lane or rank badges +
  authoritative Priority field), since silent Y-position priority is a gameplay footgun (#11).
- Consider a "Tidy" auto-layout per behavior chain (columns: behavior → conditions → actions).

## References

- Editor: `static/js/shared/trigger-graph.js`
- Form editor hand-off: `static/js/shared/trigger-editor.js:573-600`
- Behavior entry: `static/js/inspector/behaviors-view.js:1410-1427`
- Engine semantics: `engine/triggers/behaviors.py` (NO-branch/fan-out limits are engine model, not editor)
- World-map graph (separate system, vis-network, already has pan/zoom): `static/js/graph-manager.js`

---

# Part 2 — Form Editors, Interop, Saving, Testing (research round 2)

Scope added after round 1: the form editors, form↔graph conversion, saving flows, test
animation, dialogs, and socket direction conventions.

## The four catalogs (the structural problem)

The engine's trigger/behavior vocabulary exists in **four drifting copies**:

| Catalog | Triggers | Conditions | Effects | Behavior actions | Source |
|---|---|---|---|---|---|
| Engine | 33 | 27 + 11 behavior | 42 + 5 | ~100 | `constants.py`, `engine/triggers/behaviors.py` |
| `TriggerTypes` registry (form editor dropdowns) | 33 | 20 | 41 | — | `static/js/shared/trigger-types.js` |
| Trigger form editor | ← registry | nested AND/OR/NOT tree UI | ← registry + save-gate branches + snippets | — | `static/js/shared/trigger-editor.js` |
| Graph editor (`NODE_DEFS`) | **17** | **20** | **24** | **11** | hardcoded in `trigger-graph.js` |
| Behavior form editor | — | 12 behavior | — | **~100** | `static/js/inspector/behaviors-view.js` |

The graph editor is the *least* capable of the four, yet it writes the same saved data.
The cheat sheet (`docs/Trigger-Condition-Effect-Cheat-Sheet.md`) is the authoritative catalog.

### New defects (continuing round-1 numbering)

17. **Behavior graph save is destructive for ~89% of actions.** `behaviorsToGraph` maps *every*
    action to an `action` node, but `NODE_DEFS.action` knows only 11 types and
    `_buildActionFromNode` re-emits only recognized params — saving from the graph editor strips
    all params of any of the other ~89 action types (e.g. `kiss` → `{type:'kiss'}`, losing
    target/where/intensity). Worse, the Type dropdown shows "message" for unknown types (no
    matching `<option>`), so they're mislabeled on screen too.
18. **Behavior-only conditions don't round-trip.** `npc_emotion_is`, `npc_is_hidden`,
    `character_has_tag` etc. exist in the behavior form editor but not in the graph's condition
    fields; `_conditionToGraphProps`/`_buildConditionFromNode` keep only generic keys — `emotion`
    and friends are lost on graph save.
19. **Form→graph conversion is lossy by design.** `triggerToGraph` keeps only `conditions[0]`
    (drops the rest of the tree), only `trigger_type[0]` (multi-type triggers lose the rest),
    cannot express OR/NOT groups (graph conditions chain = AND only), and the `save` effect's
    `on_success`/`on_fail` branches have no node representation. Opening a rich form trigger in
    the graph and applying destroys structure with no warning.
20. **Blueprints are under-specified.** Saved blueprints store `{name, description, graph}` only:
    no mode marker (a behavior blueprint loads into the trigger editor as garbage and vice
    versa), no form-level name/success_message/fail_message, silent overwrite when the id
    collides, no tags/search, and the load picker is a raw floating div.
21. **No visual execution trace on Test.** `/api/triggers/test` already returns per-condition
    `passed` flags and ordered `outputs` — everything needed to animate the graph — but both
    editors render it as a flat text panel. The graph doesn't even scroll to / highlight the
    nodes that fired.
22. **Native `prompt()`/`alert()`/`confirm()`** for blueprint save/load, apply-anyway, and
    close-without-save across `trigger-graph.js` (the app has modal + toast patterns to reuse,
    e.g. `shared/diff-modal.js`, `toastInfo`).
23. **Condition YES/NO sockets both exit the bottom** (45%/55% positions) — wires leave
    downward then hook around, producing the awkward S-curves visible in practice; violates
    left-in/right-out dataflow convention; 16px dots are small targets; ✓/✗ labels only exist
    as `title` tooltips.
24. **Both editors write the same data with no interlock.** Behavior form modal and graph
    editor both end in `ApiClient.updateCharacter({behaviors})` — last writer wins, no
    dirty-checking, no diff preview (the diff-modal exists but isn't used here).

### What's good (keep)

- Trigger form editor is genuinely strong: nested condition tree with ALL/ANY groups, grouped
  effect registry with icons, snippet recipes (task-380), SearchSelect/TagMultiselect pickers
  with library + world data, live dry-run test with fireability hints.
- `TriggerTypes` was built (per its header) to be the single source of truth — the graph editor
  just never adopted it.

### Recommendations

- **One registry to rule them all:** extend `shared/trigger-types.js` into a full catalog —
  every trigger/condition/effect/action with its param schema (label, input type, datalist,
  default, applies-to mode). Generate: form editor rows, graph `NODE_DEFS` fields, behavior
  form cards, and the validate dropdowns from it. New engine types then appear everywhere at
  once. This is the prerequisite for defect #17/#18 to even stay fixed.
- **Conversion honesty:** `triggerToGraph`/`behaviorsToGraph` must round-trip or refuse —
  when a trigger/behavior contains anything the graph can't represent (OR groups, extra
  trigger types, unknown actions), show a modal listing what will be lost with
  "Edit in form instead" / "Convert anyway" options. Never silently degrade.
- **Graph→form is the safe direction** (graph ⊂ form). "📝 Form" button should work in
  behavior mode too (currently bridge is trigger-mode only).
- **Left-in / right-out everywhere:** move condition YES/NO outputs from bottom to the right
  edge (✓ top-right, ✗ bottom-right); input left. Every wire then flows left→right, chains
  read naturally, and layered auto-layout becomes trivial. Bottom edge stays free for future
  (else-branch, subgraph ports). Socket dots: 20px+, visible ✓/✗ labels beside the dot.
- **Test animation:** on Test in the graph, walk the compile trace: pulse the trigger node,
  animate the wire dash downstream (SVG `stroke-dashoffset` transition), light each condition
  node green/red per the API's per-condition results (staggered ~200ms), then flash effect
  nodes in `outputs` order. Pure CSS/JS on the existing DOM; no new deps. The text panel
  stays as the detailed log. Later (bigger): a behavior *simulation* mode reusing the same
  animation against a live or dry-run engine context.
- **Proper dialogs:** blueprint save dialog (name, description, tags, mode badge, overwrite
  warning), load browser (searchable list, mode filter — this is task-351 Phase 2, reuse it),
  unsaved-changes confirm on Esc/close, and apply-with-errors confirm. All in-app modals.

### Revised phased plan (supersedes Part 1 plan)

| Phase | Scope |
|---|---|
| 1 — Viewport | pan/zoom/fit/grid + `screenToWorld` (unchanged from Part 1) |
| 2 — Wires & flow | colored typed wires, deletion, cycle guard, **left-in/right-out socket layout** (#23), compile-honesty badges (#9–#11) |
| 3 — Registry | unify catalogs into `trigger-types.js` param schemas; generate graph node fields + behavior form cards from it; fixes #17/#18 structurally |
| 4 — Interop | lossless-or-warned form↔graph conversion (#19), blueprint mode marker + metadata + proper save/load dialogs (#20, #22), graph→form bridge in behavior mode |
| 5 — Editing power | undo/redo, multi-select, copy/paste, collapse, unsaved guard, autosave (Part 1 Phase 3) |
| 6 — Test animation | execution-trace animation in graph test (#21); later behavior simulation |
| 7 — Scale & polish | minimap, LOD, culling, touch (Part 1 Phase 4); behavior priority UX (Part 1 Phase 5) |

## Implementation Log

### Phase 1 — Viewport (DONE, 2026-09-02)

Architecture: `#tg-canvas` is now an untransformed viewport; a single `#tg-world` child
(nodes + wires SVG) carries the one transform `translate(pan) scale(k)`. All gesture math runs in
world coordinates via `_screenToWorld()`. The wires SVG uses `overflow:visible` so world-space
paths work without a giant SVG box, and wire geometry no longer needs re-rendering on pan/zoom/resize.

- **Pan**: drag empty canvas, middle-mouse anywhere (incl. over nodes), space+drag; grab/grabbing cursors.
- **Zoom**: wheel zoom-to-cursor (0.25×–2.0× clamp, exponential factor so trackpads feel even),
  bottom-left control cluster (− / % badge / + / ⤢ Fit; badge click = reset 100%), keyboard
  `+`/`-`/`F`. Fit and button zooms animate (CSS transition class); gestures stay immediate.
- **Grid**: dot grid drawn on the viewport, position+size synced to the transform each frame.
- **Fixed by the new coordinate model**: node drag now tracks the cursor 1:1 at any zoom (was
  screen-delta at world speed), wires stay glued to sockets after Fit (was: double-transformed),
  context-menu nodes spawn under the cursor at any zoom, and **the add-node-after-search-filter
  bug** (menu re-render passed 0,0 as spawn position) is fixed.
- **Wires** now inherit their source socket's color (YES green, NO red, trigger/behavior gold,
  action blue) — first slice of Phase 2's wire clarity work, effectively free during the rewrite.
- **Selection** is a class toggle (`.tg-sel` via injected stylesheet + `--tg-c`/`--tg-glow` custom
  props) instead of a full canvas DOM rebuild per click — no more focus loss/flicker on select.
- **Drags are document-scoped** while active (fast mouse / release outside the canvas can't strand
  a drag; previously a mouseup outside the canvas stuck the editor in drag state).
- **Viewport persistence**: per-mode `localStorage` key, debounced; restored on open only if it
  still shows part of the graph, otherwise auto-Fit (also auto-Fit after loading a blueprint).
- **Fixed en route — id-collision corruption (pre-existing, defect #25)**: loading a graph never
  seeded `nodeIdCounter`/`wireIdCounter`, so the first node/wire added reused `n0`/`w0` and
  silently *replaced* existing ones. `_seedCounters()` runs on load/blueprint-import and id
  generation now skips taken ids. Also: right-button no longer starts node drags.
- **Compile pipelines verified intact** (`triggerToGraph`→`compileToEngine`,
  `behaviorsToGraph`→`compileToBehaviors` round-trips re-checked after the rewrite). This probe
  re-exposed defect #19's family: `_conditionToGraphProps` drops the `skill` param of
  `skill_check` (form→graph loses DEX/STR etc., silently defaults to Athletics).

**Test**: `tools/test_trigger_graph_viewport.cjs` (Playwright, headless, client-side only — no
backend writes). 19 checks: auto-fit bounds, grid sync, badge, cursor-anchored zoom, 1:1 drag at
zoom, wire glue + color after zoom+drag, three pan modes, pan/world separation, context-menu
spawn-at-cursor after filtering, zoom clamps, Fit, viewport persistence, zero page errors.
Note for future test authoring: the help-center tip cards (`.hc-card`) float above everything and
eat mouse events — dismiss them before interacting.

### Follow-up fixes (2026-09-02, same day)

- **Behavior form editor was broken for ALL behavior edits** — `weighItem is not defined` thrown
  while building any action card (the hold/weigh/inventory/carry field group at
  `behaviors-view.js:690` referenced `weighItem`/`inventoryItem`, which were never declared next
  to their `holdItem`/`carryItem` siblings; the template literal evaluates every `${}` at build
  time, so any edit-behavior click crashed). Both consts added.
- **New regression test**: `tools/test_behavior_action_cards.cjs` — calls
  `buildBehaviorActionCard` for all **119** action types with a kitchen-sink param object and
  fails on any throw. This is the net that would have caught the above.
- **behaviorsToGraph re-layout**: was one tall column (all behaviors at x=50, 180px apart) with
  chains overflowing their slot into the next behavior — the rat's 14 behaviors opened as a
  25%-zoom smear. Now a priority-ordered row-major **grid** (≤3 columns, 920px cells,
  behavior → conditions column → actions column, per-block heights, 150px chain spacing).
  Result on the same 14-behavior set: fit zoom 0.38 (was 0.25), zero overlapping node rects,
  priority round-trip exact (14→1 in order — grid rows share Y and `compileToBehaviors`'s stable
  Y-sort keeps load order for ties). Chain wire semantics unchanged.

- **Scattered/detached wires on open (Phase 1 regression, fixed 2026-09-02)**: wires are
  world-space paths computed against the live viewport, but `_show()` drew them *before*
  applying the saved viewport / auto-fit — every path baked in the previous session's transform
  and was left offset (often far off-content) once the view moved. `_applyBlueprint` had the
  same latent bug (render, then animated Fit). Fix: redraw wires after the viewport settles in
  `_fitView()` and at the end of `_show()`. Regression check #20 added to
  `test_trigger_graph_viewport.cjs`: all wires glued to sockets immediately after reopen,
  no interaction (20/20 PASS).
- **Trigger form editor had no Escape** (2026-09-02): `trigger-editor.js` gained a capture-phase
  Escape handler (works while a field is focused) + backdrop-click cancel, cleaned up in
  `close()` so it can't double-fire against the graph editor's own Escape.
- **Field type-ahead + condition socket layout (2026-09-02, first Phase 2 slice)**:
  - Graph node fields were plain free-text; they now carry `list=` datalists fed from world
    state + libraries (areas, world+library items, character names *and* character library ids,
    traits, tags, vitals, skills, NPC states, node states, env stats, weather, conditions) —
    refreshed every open, library lists loaded async. Still free-form (unknown values keep
    working); full SearchSelect retrofit stays in Phase 3's registry work.
  - Condition ✓/✗ sockets moved from their ambiguous bottom 45%/55% pair to the dataflow split:
    **✓ YES exits the right edge** (upper, flow continues sideways), **✗ NO drops from
    bottom-center** — with visible color-coded labels (`✓ yes` / `✗ no`) so branches read
  without hovering. Socket ids and wire topology unchanged, so saved graphs and the compile
  pipeline are untouched; a side effect of the move is that nonsense same-side connections
  (e.g. behavior output → condition YES) are now rejected by the existing side-differing rule.

### Form↔graph catalog parity + two editor-killing bugs (2026-09-02, later)

Full sweep against the cheat sheets and the trigger form editor's `_collectData`:

- **CRITICAL pre-existing bug: graph field edits never persisted.** Two stacked defects:
  1. Every field's inline handler referenced `TG._onFieldChange` — but `TG` lives only inside the
     module closure, so every `change` event threw "TG is not defined" and the value never reached
     node props. All 141 inline handlers now reference the global `TriggerGraph`.
  2. `_renderNode`'s id substitution `replace(/'NODEID'/g, node.id)` matched *including the
     quotes* and substituted the bare id — `('NODEID')` became `(e2)` — so type-switch re-renders
     threw "e2 is not defined" too. Now replaces with `'/id/'` quoted.
  Net effect of the two: in the original editor, **typing into a node and saving silently
  compiled stale values, and switching a node's type always crashed its re-render.**
- **Trigger node = form parity**: full 33-type catalog pulled from `window.TriggerTypes`
  (same source as the form), **Ctrl+click multi-select** (props store an array, engine accepts
  it), and the `target_state` field for on_state_enter/exit (compiled through).
- **Condition node = catalog parity +**: grouped dropdown (General/Character/Item/Area/NPC) now
  includes `item_relationship`, `vital_above/below`, `temperature_above/below` and the
  behavior-only trio `npc_emotion_is` / `npc_is_hidden` / `character_has_tag`, each with proper
  fields and compile branches (`_buildConditionFromNode` + `_conditionToGraphProps` round-trip).
- **Effect node = full form catalog and beyond**: grouped dropdown with the form's 41-effect
  list. New param blocks: **save gate** (ability/skill + DC + per-branch on_success/on_fail
  editors: none/message/apply_condition(+duration/source/source_type)/damage + advanced JSON,
  compiled to the exact `on_success`/`on_fail` arrays `_buildSaveBranchEffect` produces),
  schedule_trigger, llm_respond (max_words/cooldown/name), scry, consume_item, remove_item,
  rename, unlock_way (way datalist), set/append_description, spawn into/capture, add/remove_tag
  message, environment presets (light/air/noise selects, smell, target_node), memory effects
  (surface/suppress/unblock — the form has these in its dropdown with *no* fields; the graph
  edits them), and spawn_way/set_way_target/set_way_view/spawn_area (also fieldless in the form).
  Key fixes to match `_collectData` exactly: spawn `display_name` (was `name`), damage target
  self/other (was player/self), adjust_vital target, `_normalizeEffectParams` mirrors the form's
  serialization (target_by normalization, boolean coercion for hidden/see_through/param, empty
  strings dropped, symptoms/extra_conditions JSON parsed, `effect_type` stripped).
- Verified: 10-check compile parity probe (save gate structure, multi-type, normalize, key
  parity) + DOM probes (field blocks render, type-switch re-renders, a real change event lands
  in props and survives the save path) + both suites green (20-check viewport, 119-type cards).



---

## todo/ui/task-405-llm-raw-request-response-inspector.md

---
type: task
status: todo
area: ui
priority: medium
---

# task-405: LLM raw request/response inspector

**Filed:** 2026-09-17  
**Depends on:** none

## Goal

Show the complete raw HTTP exchange with the LLM provider in the UI, not just
the extracted assistant text. Users need to verify what is actually sent and
received — headers, status, full JSON body, usage, reasoning tokens, tool
calls, errors — for debugging providers like OpenRouter, LM Studio, Ollama,
OpenAI, etc.

## Current state

`static/js/shared/dataset-collector.js` already captures `{ messages, response,
label, model, parsed_ok, repaired }` to IndexedDB, and a floating panel exports
JSONL for fine-tuning. But `response` is only the extracted text content. The
full HTTP response object — status, headers, raw JSON body, usage breakdown,
reasoning/output token counts — is discarded after `_captureDataset` reads
`completion.choices[0].message.content`.

`static/js/llm-client.js` already logs requests to the event stream via
`VW.events.logRawLLMRequest(label, messages, est)` and responses via
`VW.events.logRawLLMResponse(label, content)`. The event stream UI shows these
as expandable chips. But the stream view is designed for gameplay narration,
not raw API inspection.

## What to build

### 1. Extend DatasetCollector with full payload capture

Add a `captureRaw(label, requestBody, rawResponse, status, headers)` overload
to `dataset-collector.js`. It stores an additional entry under a separate
IndexedDB store, e.g. `llm_raw_exchanges`, with this shape:

```json
{
  "key": "r_1789684764_cpReQMjsVHdo4a1jnm9H",
  "ts": 1789684764000,
  "label": "think-decide",
  "model": "inclusionai/ling-3.0-flash-sante:free",
  "request": {
    "url": "https://openrouter.ai/api/v1/chat/completions",
    "method": "POST",
    "headers": {
      "content-type": "application/json",
      "authorization": "Bearer sk-or-...",
      "x-model": "inclusionai/ling-3.0-flash-sante:free"
    },
    "body": { "model": "...", "messages": [...], "temperature": 0.7, ... }
  },
  "response": {
    "status": 200,
    "statusText": "OK",
    "headers": { "x-ratelimit-remaining": "49", ... },
    "body": {
      "id": "gen-1789684764-cpReQMjsVHdo4a1jnm9H",
      "object": "response",
      "created_at": 1789684764,
      "model": "inclusionai/ling-3.0-flash-sante:free",
      "status": "incomplete",
      "completed_at": 1789684767,
      "output": [ { "type": "reasoning", "content": [...], "summary": [] } ],
      "error": null,
      "incomplete_details": { "reason": "max_output_tokens" },
      "usage": {
        "input_tokens": 2314,
        "input_tokens_details": { "cached_tokens": 0 },
        "output_tokens": 200,
        "output_tokens_details": { "reasoning_tokens": 194 },
        "total_tokens": 2514,
        "cost": 0,
        "cost_details": { "upstream_inference_cost": 0, ... }
      }
    }
  },
  "duration_ms": 3120,
  "parsed_ok": true,
  "repaired": false
}
```

**Redaction:** strip `authorization` header value before storing. Replace with
`"Bearer sk-or-...REDACTED"` so the user can see the header exists without
exposing the key in IndexedDB.

**Non-blocking:** capture is fire-and-forget. Failure to write to IndexedDB
must not affect the game loop or LLM call result.

### 2. Hook capture points in `llm-client.js`

After `const completion = await resp.json()` (line 164), before any extraction:

```javascript
this._captureRawExchange(label, requestBody, completion, resp.status, resp.headers);
```

For streaming, hook after `_handleStream` resolves. `_handleStream` already
assembles the full streamed object; pass that plus the original request body.

For errors (`resp.ok` is false), also capture the error response body so users
can see provider error shapes.

### 3. Build the inspector UI

Add a new panel: **LLM Inspector** (separate from the Dataset Collector panel,
or merge into it with a tab).

The panel shows a scrollable list of recent exchanges. Each entry expands to:

```
┌─ think-decide · inclusionai/ling-3.0-flash-sante:free · 3.1s ─┐
│ Request: POST https://openrouter.ai/api/v1/chat/completions     │
│ Headers: content-type: application/json                         │
│          authorization: Bearer sk-or-...REDACTED                │
│ Body: { model: "inclusionai/ling-3.0-flash-sante:free", ... }  │
│                                                                │
│ Response: 200 OK · 2,514 tokens · $0.00                        │
│ Body: { id: "gen-...", status: "incomplete",                   │
│         incomplete_details: { reason: "max_output_tokens" },   │
│         output: [ { type: "reasoning", content: [...] } ],     │
│         usage: { input_tokens: 2314, output_tokens: 200,       │
│                   reasoning_tokens: 194, total: 2514 } }       │
└────────────────────────────────────────────────────────────────┘
```

Features:
- **Copy request** / **Copy response** buttons per entry
- **Filter by label** (`think-decide`, `result-reaction`, `plan`, etc.)
- **Filter by status** (200, 429, 500, etc.)
- **Clear all** button
- **Search** across request body and response body text
- JSON is syntax-highlighted and collapsible for large `output` arrays

### 4. Persist inspector state

The panel remembers its open/closed state and last scroll position across
turns. Entries survive page reload because they live in IndexedDB.

### 5. Opt-in toggle

Add `showRawLLM` to the Settings UI. Default: `false`. When enabled, the
capture overhead is negligible (IndexedDB writes are async and fire-and-forget).

## Files

- `static/js/shared/dataset-collector.js` — add `captureRaw`, `getAllRaw`,
  `clearRaw`, `buildRawPanelUI`
- `static/js/llm-client.js` — call `_captureRawExchange` after every response
- `static/js/ui/llm-inspector.js` (new) — inspector panel UI
- `static/css/llm-inspector.css` (new) — syntax highlighting, layout
- `templates/index.html` or command palette — entry point for the inspector

## Verification

- Make an LLM call with `showRawLLM` enabled
- Open inspector, verify request headers + body + response status + full body
  + usage stats are visible
- Verify `authorization` header is redacted
- Verify streaming calls are captured
- Verify failed calls (429, 500) are captured with error body
- Verify entries survive page reload
- Verify panel toggle doesn't break existing event stream or dataset collector

## Non-goals

- Server-side proxy or MITM capture (this is browser-only)
- Automatic request replay or modification
- Token cost tracking across sessions
- Exporting raw exchanges as a training dataset format

## Progress — 2026-09-19

Implemented (browser-only, opt-in).

- `storage.js`: DB version 3 → 4, added the `llm_raw_exchanges` store.
- `shared/dataset-collector.js`: `captureRaw` / `getAllRaw` / `clearRaw` /
  `countRaw`. Redacts `authorization` / `api-key` / `x-api-key` to
  `Bearer xxxxxx…REDACTED`, caps the store at 200 entries (trimmed every 25th
  capture), and only records when `config.showRawLLM` is on.
- `llm-client.js`: `_captureRawExchange(...)` plus hooks after `resp.json()`,
  after `_handleStream` (captures `{ streamed: true, content }` — a stream has
  no provider envelope), and in the `!resp.ok` branch so error bodies are kept.
- `ui/llm-inspector.js` (new): floating panel with expand-per-entry, usage line
  (prompt/completion/in/out/**reasoning**/total/cost), Copy request / Copy
  response via `navigator.clipboard`, label + status filters, body search, and
  Clear. Bodies are JS-serialized and truncated at 200k chars per block.
- Settings: new **🔬 Show Raw LLM** checkbox (`agent-show-raw-llm`), wired
  through `config` load/save/saveFromForm **and** `populateForm()` restore.

Verified: `node --check` clean on all six touched JS files, `npm run lint`
passes, and the settings-checkbox audit reports all 14 covered.

Not done / caveats: no syntax highlighting or collapsible nested arrays (JSON is
pretty-printed in a scrollable `<pre>`); no export of raw exchanges; the button
and panel sit alongside the 🧪 dataset panel (both float bottom-right, so they
can overlap if both are open).



---

## todo/ui/task-443-validator-mismatch-recalibration-and-info-section.md

---
type: task
status: todo
area: ui
priority: medium
---

# task-443: Validator mismatch recalibration, info section, and mark-as-intended

**Filed:** 2026-09-21
**Supersedes:** the unimplemented residuals of task-393 (the triage mechanics shipped; that task is closed)
**Related:** task-393 (design sections E/F), task-324 (domain tags — feeds `mechanical_tag_missing_props`)

## Goal

Finish the three pieces of the validator triage panel that were specified but never
built, so the mansion run's noise floor drops.

## What is missing (verified 2026-09-21)

1. **`library_mismatch` recalibration — not done, and task-393's claim about it was false.**
   The panel was supposed to fire `library_mismatch` only on **mechanical** field drift
   (vitals / triggers / actions / uses) and not on `light_level` / `contents`, because
   instance divergence on those is the *normal* authoring flow. It still includes them:
   `LIBRARY_SYNC_PROPS` (`engine/trigger_validator.py:147-151`) carries `light_level`,
   `target_temperature`, `heating_rate`, `contents` and `aliases`; the severity is still
   `warning` (`:728`); and `tests/test_trigger_validator.py:428-439` asserts a
   `light_level` mismatch **is** reported. Note `DEFAULTED_MECHANICAL_DEFAULTS`
   (`:135-139`) already declares the first three as engine-defaulted → they belong with
   `mechanical_tag_missing_props` (info), not `library_mismatch` (warning).
2. **No "mark instance as intended" action.** Task-393 design section E calls for batch
   "mark instance as intended" (set an explicit override) rather than resync. No such
   action exists anywhere — no route, no property, no UI.
3. **No default-collapsed `info` section.** Grouping sorts by worst severity
   (`static/js/validator-panel.js:293-300`) but info rows render inline.

Also owed: the **manual browser pass** task-393 never had (grouping UI, scroll,
dismiss-until-touched persistence across reload).

## Design notes

- **Recalibrate by moving props, not by loosening the check.** Keep `library_mismatch`
  for the props where divergence is a real bug; route `light_level` /
  `target_temperature` / `heating_rate` to the existing `mechanical_tag_missing_props`
  (info) path, and decide `contents` / `aliases` explicitly (they are structural, so
  likely stay — but then the message should say why).
- **Mark-as-intended is a node override**, not a library edit: a property on the placed
  node that suppresses its own mismatch until the node is edited again — the same
  dismiss-until-edited shape `ignored_issues` / `_ignored_at` already uses
  (`engine/trigger_validator.py:184-219`). Reuse it rather than inventing a second
  mechanism.
- **The info section is grouping, not filtering** — it must not hide info rows from the
  count in the pinned header.

## Acceptance

- A mansion-style run's ~40 `library_mismatch` warnings on trivial fields fall to ~0,
  and no real mechanical drift is lost (a vitals/uses/actions mismatch still reports as
  a warning).
- "Mark instance as intended" suppresses a mismatch on that node only, survives reload,
  and expires when the node is edited after the mark.
- Info rows sit in a default-collapsed section; the pinned count still reflects them.
- Manual browser pass recorded in this file (grouping, scroll, dismissal persistence).
- `python -m pytest tests/ -q -k "not mcp and not emote"` green, with
  `tests/test_trigger_validator.py` updated for the recalibration.

## Non-goals

- The triage mechanics themselves (grouping, scroll, empty-trigger collapse, dismiss,
  fix-all, progress bar) — those shipped with task-393.
- Changing the derived-progress definition — task-393 settled it on the shipped
  formula; see that task's Outcome block.



---

## todo/ui/task-448-disambiguate-ambiguous-target-names.md

---
type: task
status: todo
area: ui
priority: medium
---

# task-448: Disambiguate an ambiguous target name/nickname

**Filed:** 2026-09-22
**Related:** task-446 (id-first node identity), task-447 (character nicknames),
`engine/matching.py` (`_match_character_name` returns `(None, candidates)`),
`routes/action_handlers.py`, `static/js/agent/human-turn-composer.js`

## Why

When a spoken name matches more than one character — two people called "Violet",
or two sharing the nickname "Vi" — the engine must **ask**, not guess. The matcher
already detects this and returns candidates (`name is None, candidates=[...]`),
but the prompt lists bare names (or internal keys), so "Violet or Violet?" is
unanswerable.

This is normal authoring, not an edge case: families share surnames and nicknames,
and populated worlds reuse generic names (task-357, task-446).

## Scope

- When `_match_character_name` (and item/exit equivalents) reports ambiguity,
  render a **chooser** that shows, per candidate: display name **plus a
  distinguishing detail** — description / `unknown_display_name()` / current
  area / a visible item — using the identity key as the value.
- Accept the choice and resolve it to the identity key so the action targets the
  chosen character (relationships, grapple, give/take, attack all use the key).
- Works in both the text command path and the human turn composer / inspector.
- Never auto-pick when the candidate set is ambiguous.

## Acceptance

- Two "Violet"s in one room: `talk to violet` lists both with a distinguishing
  detail; picking one targets the right identity (verified via a relationship or
  a grapple hitting only the chosen character).
- Two characters sharing an alias behave the same.
- An unambiguous name still resolves directly (no chooser).

## Non-goals

- Authoring the nicknames themselves (task-447).
- Duplicate-name storage (done, task-446).



---

## todo/ui/task-455-save-load-dialog-ux-in-modal-rename-and-confirms-autosave-row-actions.md

---
type: task
status: todo
area: ui
priority: medium
---

# task-455: Save-load dialog UX: in-modal rename and confirms, autosave row actions

**Filed:** 2026-09-22
**Related:** task-369, bug-40, bug-42

## Goal

Bring the Save / Load modal in line with the rest of the UI: it is the last major
surfacestill using native browser dialogs.

Current behavior in `static/js/ui/saveload-view.js`:

- **Rename** is `prompt()` (`doRenameSave`, line 413) — blocking, unstyled, and it
  cannot show validation (empty name, name already taken, filename stays for slot
  saves).
- **Load** confirms with `confirm('Load game "<filename>"? ...')` (line 492) even
  though the row shows a display name; the user is asked to approve a filename.
- **Delete** is `confirm()` (line 511).
- **Delete All** is two `confirm()`s (lines 525-526) — see bug-42 for the behavioral
  bug in the same code.
- The **autosave row** exposes ✏️ rename and 🗑 delete, but a rename of the autosave
  label is overwritten on the next autosave, and deleting the slot contradicts the
  "always current" promise (bug-42).

## Proposal

- Rename becomes an **in-place row edit** (click ✏️ → the title becomes an input;
  Enter commits, Escape cancels) — the top-bar scenario chip already does exactly
  this (`initScenarioNameEditor`), so reuse that interaction.
- Load/delete get a small in-modal confirmation (display name, timestamp, one line of
  stats), matching the import-preview pattern in `openImportPreview` (task-369).
- On the autosave row, keep **load** and the **overwrite** 💾; hide ✏️ and 🗑 (or make
  delete-autosave an explicit, separately-worded action if it should exist at all).
- Surface rename/delete failures via the existing toasts with the server's message.

## Acceptance

- [ ] No native `confirm()`/`prompt()` remains in the save/load flow.
- [ ] Renaming a save works from the row, is keyboard-cancellable, and reflects the
      server's returned filename/name.
- [ ] Loading and deleting confirm with the save's **display name** and timestamp, not
      the raw filename.
- [ ] The autosave row offers load + overwrite only; no rename/delete control that
      silently does not stick.
- [ ] Empty/duplicate rename input is rejected with a visible message.

## Files

- `static/js/ui/saveload-view.js` — `doRenameSave`, `doLoadGame`, `doDeleteSave`,
      `confirmDeleteAllSaves`, `loadGameList`
- `templates/index.html` — modal markup if new in-modal elements are added
- `static/css/style.css` — row/confirm styling



---

## todo/ui/task-479-surface-skill-dc-band-and-dice-breakdown-in-prompts-and-narration.md

---
type: task
status: todo
area: ui
priority: medium
---

# task-479: Surface skill, DC band and dice breakdown in prompts and narration

**Filed:** 2026-09-23
**Related:** task-472, task-475

## Goal

Show the player what they are rolling and how it went: the skill, the DC band, advantage/disadvantage and the d20 breakdown in the prompt and narration, plus why an auto-fail happened and what could be found in a given area (a light hint), so checks are legible rather than hidden numbers.

## Acceptance

- TODO



---

## todo/world/task-398-deterministic-structure-generation.md

---
type: task
status: todo
area: world
priority: high
---

# task-398: Deterministic scoped structure generation

**Filed:** 2026-09-08  
**Depends on:** task-397; task-323 and task-324 for tag-validated library
population; task-9 for reusable item-population planning.

## Goal

Generate an unmade world scope into normal VirtualWorld graph nodes: real
areas, real ways, relevant furniture/items, and optionally inhabitants. The
generator must be deterministic, reviewable, editable after generation, and
safe to invoke exactly once. AI assistance is optional and may enrich a plan;
it is never required for topology or baseline item placement.

## Generator contract

Each generation recipe returns a **graph patch**, not a parallel world format:

```python
GenerationPatch(
    nodes: list[Node],
    edges: list[Edge],
    area_scope_assignments: dict[str, str],
    generated_manifest_updates: dict,
    report: GenerationReport,
)
```

Applying the patch must use the existing graph node/edge conventions:

- areas use `type="area"`;
- passages use normal `way` nodes and four connection edges where bidirectional;
- items use normal library-spawned item nodes and spatial edges;
- triggers remain normal logic-trigger nodes/edges;
- generated node ids are stable, scoped, and collision checked, e.g.
  `area_pines_3b_bedroom` and `way_pines_hall_3_to_3b`.

Every generated node receives provenance:

```json
{
  "generated": {
    "scope_id": "pines_apartment_3b",
    "recipe_id": "apartment.v1",
    "seed": "pines:3b:v1",
    "generated_at_tick": 0
  }
}
```

Once applied, a scope changes from `unmade` to `materialized`. Re-running must
be rejected by default; an explicit future regenerate/variant flow must never
overwrite manual edits.

## First recipe: Pines Apartment 3B

Use one small, authored apartment recipe as the proof:

- entry/living-kitchen area, bedroom, bathroom;
- an external way from Hallway 3 and internal ways between rooms;
- a minimal domain-tagged furniture set;
- a tag-aware population pass for furniture contents and loose items;
- either `vacant` or one explicitly requested resident seed. Do not silently
  manufacture an LLM character.

The recipe should use the existing profile as authored context, but profile
text is input data, not executable instruction.

## Tag-aware population rules

Task-9 already owns the reusable area → furniture → item tag-chain engine.
This task must call a stable planning/apply API from that task rather than
duplicate library selection in a building generator. The engine must not call
route-private helpers such as `_spawn_library_item_node`; extract a public
library/graph materialization service usable by both the route and generator.

For this prototype, create a deliberately small approved tag vocabulary, for
example `residential`, `bedroom`, `bathroom`, `kitchen`, `storage`, and
`display`, and a matching fixture/template inventory. Candidate selection must
also use room archetype, furniture `placement_roles`, weights, exclusion tags,
and per-archetype budgets/capacities; raw tag intersection alone would put
plausible-but-wrong things in rooms. Pre-index library candidates by tag/role
instead of scanning the full library for every placement. Pines currently has no
area-domain tags, so demonstrating "relevant items" without this data would
be fake. The generator report must say when a requested tag has no eligible
library candidates; it may not substitute unrelated items silently.

## Editor workflow

1. Select an unmade scope.
2. Preview: recipe, seed, proposed area/way/item counts, unresolved tag pools,
   and boundary ways.
3. Apply after user confirmation.
4. Show a generation report and focus the new graph projection.

AI enrichment, if later enabled, produces a staged proposal using the existing
natural-language editor; deterministic validation and user apply remain the
authority.

## Acceptance

- Generating Apartment 3B creates a walkable three-area interior from Hallway
  3 using normal movement and way rules.
- Generated items are physically placed through normal spatial edges and can
  be looked at/taken/used.
- Same seed + recipe version + clean fixture yields the same patch.
- A second generation attempt makes no duplicate nodes/ways/items.
- Missing tag candidates are visible in the preview/report.
- Save/reload preserves generated nodes, provenance, and scope state.
- A later manual edit to a generated item survives reload and cannot be erased
  by a second generator invocation.

## Non-goals

- Generating all of Millbrook, district road layout, or wilderness grids.
- LLM-only generation or unreviewed mutation.
- Chunk unloading (task-401).



---

## todo/world/task-399-background-character-simulation-and-reactivation.md

---
type: task
status: todo
area: world
priority: high
---

# task-399: Background character simulation and reactivation memory

**Filed:** 2026-09-08  
**Depends on:** task-397 for scope activation. Uses existing Player memories,
activities, vitals, movement, and serialization.

## Goal

Let any existing character live cheaply while their scope is not actively
observed, without changing who that character is. This is an execution mode,
not a new character type and not a synonym for `simple_npc`.

```text
controller:       human | llm | simple_npc       (existing identity/control)
simulation_mode:  active | background           (new runtime fidelity)
```

An LLM-controlled character in background mode makes no LLM requests. A
simple-NPC-controlled character may also use background mode. The character's
name, traits, relationships, inventory, current area, vitals, activity, and
memories remain authoritative `Player` data.

## Background runner (v1)

Add a small deterministic module, e.g. `engine/background_simulation.py`.
It processes only due background characters, not every character every minute.
Persist `next_due_tick`, schedule/intent, seeded RNG state, and an append-only
facts log; browser-local LLM plans cannot be the source of truth after an
offload.
Each character has an authored/supplied schedule of high-level steps:

```json
{
  "start": "08:00",
  "activity": "work",
  "destination_scope_or_area": "daily_grind",
  "fallback": "wait",
  "vital_policy": "eat_when_hungry"
}
```

V1 operations are intentionally limited: sleep/rest, travel to an existing
target, work/wait, consume an explicitly eligible carried/reachable item, and
simple resource production/consumption. They must use existing movement/item
rules where exact resolution is needed, or record a structured deferred result
when the target scope is unmade/unloaded.

Cheap background meetings resolve from authored policies, relationships,
traits, vitals, and seeded randomness. They never trigger LLM conversation.
Combat, ambiguous theft/trade, a blocked/locked route, a trigger requiring
precise surroundings, or an encounter explicitly marked `requires_active`
must stop/background-defer and request scope activation instead of inventing
an outcome.

## Event and memory bridge

Record structured background events, not only prose:

```json
{
  "character": "miki",
  "start_tick": 10,
  "end_tick": 70,
  "kind": "sleep|travel|work|consume|meeting|deferred",
  "areas": ["apartment 1b"],
  "facts": ["drank item_energy_drink_01"],
  "importance": 1
}
```

On activation, consolidate the interval into at most one or a small bounded
set of normal `Player.add_memory()` entries with `source: "background"`.
Summaries are deterministic templates over recorded facts in v1; no LLM call
is permitted. Retain the structured event log for inspector/debugging, then
mark it consolidated so activation is idempotent.

Background events are private to the actor unless an existing perception,
communication, or explicit meeting rule gives another character knowledge.

## Pines proof

Create authored schedules for five existing Pines residents. Offload them,
advance eight in-game hours, then activate Miki by opening The Pines scope.
Verify no LLM calls occurred, Miki's location/vitals/item changes are real, and
her next active prompt receives a bounded subjective background memory.

Scope observation is an activation boundary: background residents inside the
opened scope become active before their next due action; residents outside it
remain background. An activate/offload transition must be atomic at its tick
so no action is resolved twice.

## Acceptance

- `simple_npc` and `autonomy` retain their present meaning and serialization.
- Background state/schedules/events survive save/load.
- Due scheduling avoids one global per-character/per-tick scan.
- A character receives no duplicate background memory after repeated activate.
- Meeting resolution is deterministic for a fixed seed and makes no LLM call.
- Exact/unsafe outcomes defer rather than fabricate facts.
- Activate/offload twice at the same tick, then save/reload: neither produces a
  duplicate action, character, item, nor summary memory.

## Non-goals

- A general economy, relationship simulation, or full offscreen combat system.
- Replacing existing LLM or simple-NPC loops.
- Background simulation across physically unloaded graph chunks (task-401).

## Progress — 2026-09-19

Foundation landed (see `docs/design/long-horizon-simulation-progress.md`):

- **The append-only facts log exists** as `engine/trace.py` (`record / recent /
  since / summarize_window / rollup / load / to_list`), bounded at 200 entries
  with salient-first retention. It round-trips through `Player.to_dict` /
  `_deserialize_player` and is wired to need tier crossings, deaths, and
  resolved actions. This is the objective substrate the "bounded subjective
  background memory" is summarized from — code writes the trace, the LLM writes
  memory, never the reverse (see `docs/design/trace-format.md`).
- **`docs/design/reversibility-contract.md`** defines what must stay live while
  backgrounded, the promote/demote handoffs, and the invariants across the seam.
- Vitals were recalibrated to a true per-minute scale (`vital_rates.py`) so a
  multi-day background span is survivable and needs actually move.

Still to build for this task:

1. `engine/background_simulation.py` — process only **due** characters
   (`next_due_tick`), deterministic/seeded over schedule + needs + traits,
   writing the trace with reasons. Survival behaviors (eat/drink/sleep/work).
2. `simulation_mode: active | background`, with atomic activate/offload at a
   tick; `trace.summarize_window` builds the promotion catch-up summary.



---

## todo/world/task-400-pines-world-scale-vertical-slice.md

---
type: task
status: todo
area: world
priority: high
---

# task-400: Pines vertical slice for grouped generation and background life

**Filed:** 2026-09-08  
**Depends on:** task-397, task-398, task-399; task-323/task-324/task-9 for
tag-aware furnishing.

## Goal

Make `data/scenarios/pines.json` the first end-to-end proof of the scalable
world model. This is deliberately small: it proves semantics and authoring
workflow, not million-node performance.

## Scenario changes

1. Add a Millbrook Falls scope manifest with Downtown and The Pines hierarchy.
2. Assign existing Pines areas to their floor/building scopes.
3. Add an unmade `Apartment 3B` scope with recipe `apartment.v1` and a stable
   seed.
4. Add only the tag fixtures and library entries necessary for a credible
   residential apartment population test. Do not attempt a global library
   backfill in this scenario task. This is mandatory: the current Pines areas
   have no domain tags, so an untagged population demo would not validate the
   intended feature.
5. Add background schedules for five existing Pines characters, chosen for
   different outcomes: sleeping at home, working remotely, walking to work,
   consuming food/drink, and waiting/meeting.

## Demonstration script

1. Load Pines and open the Millbrook → Downtown → The Pines scope path.
2. Confirm the graph view returns only that projection; default UI does not
   reveal contained items.
3. Put five residents in background mode and advance eight hours.
4. Inspect their compact logs: location, activity, vitals, resource changes,
   and any deferred result.
5. Generate Apartment 3B from preview and walk from Hallway 3 into all its
   new areas.
6. Activate Miki; inspect her new `background` memory and full active prompt.
7. Save/reload; repeat scope navigation and prove no duplicate generated nodes
   or duplicate summary memories.

## Success criteria

The demo is successful only if generation, ordinary movement/item interaction,
background progression, and reactivation all use existing canonical data.
Hard-coded UI-only counts, narrative-only generated rooms, or direct mutation
that bypasses normal graph edges do not count.

## Explicitly not demonstrated

- Whole Millbrook generation.
- Multiple loaded chunks or disk eviction.
- Long road grids, fast travel, or cross-town route materialization.
- More than five background residents.



---

## todo/world/task-401-chunk-persistence-and-gateway-ways.md

---
type: task
status: todo
area: world
priority: medium
---

# task-401: Chunk persistence, scoped indexes, and gateway ways

**Filed:** 2026-09-08  
**Depends on:** task-397 through task-400.

## Goal

Turn the proven scope model into real scale: materialized scopes can be loaded
and evicted independently while remaining part of one persistent world.

## Requirements

- Store graph subsets by scope/chunk plus a small global index for scope ids,
  area ownership, character location, unique item location, boundary ways, and
  scheduled/due work.
- Load a destination chunk before the existing movement system resolves a way.
- A boundary/gateway way identifies its remote `target_area_id` and
  `target_scope_id`; it is not a dead UI shortcut.
- Replace global node/edge scans with indexes for loaded chunks before claiming
  large-world support.
- Define cross-chunk ownership/transaction rules for characters, carried and
  equipped items, triggers, and delayed events.
- Preserve direct/fast-travel ways and route/grid ways as authored choices.

## Critical constraints

`WorldGraph.load_from_dict()` clears the current graph, so it cannot be used as
the chunk loader. Add explicit merge/unload APIs with ownership checks and
tests. Similarly, the current editor fetches all graph nodes/edges and must
use task-397's projection endpoints once chunks exist.

Characters are authoritative in the serialized `players` block as well as
having graph anchors. Chunk movement must update both consistently; a chunk
cannot independently serialize a stale copy of a character. Before unloading,
introduce stable area IDs and one authoritative character/item-location rule:
many current systems still use display-name `current_area`, which is unsafe
when separate chunks can contain duplicate human-readable names.

Delayed events targeting unloaded nodes must be globally indexed and either
load the relevant scope when due or resolve through an explicit safe deferred
policy. Silently dropping them is forbidden.

## Acceptance

- Load two adjacent chunks, move an agent/item across a gateway, unload and
  reload both, and retain exactly one authoritative location.
- A save/load round-trip preserves gateway links and due events.
- An editor scope request never returns the whole world graph.
- Benchmark/report node/edge counts loaded for the requested scope.

## Non-goal

This task is not required to prove task-400. It is the first step that makes a
million-node world technically credible.



---

## todo/world/task-402-world-scale-projection-benchmark.md

---
type: task
status: todo
area: testing
priority: medium
---

# task-402: Large-world projection and indexing benchmark

**Filed:** 2026-09-08  
**Depends on:** task-397. Extend after task-401 when real chunk loading exists.

## Goal

Prove the scale claims with generated fixture data before treating a
million-node world as supported. A passing Pines slice proves user semantics;
it does not test transport, memory, or asymptotic behavior.

## Benchmark fixture

Build a deterministic synthetic world generator for tests/tools, not a browser
render test. It should create at least 100,000 nodes across many scopes with
areas, ways, ordinary items, and a small number of characters. It must support
later expansion toward one million nodes without changing test semantics.

## Measurements

- Projection endpoint payload size and response time at world, settlement, and
  building scope depths.
- Number of nodes/edges loaded or returned for every request.
- Index lookup versus full-edge-list scans for scope-local queries.
- Memory use and elapsed time for save/load or chunk-load operations that are
  actually implemented at the time of the test.
- Confirmation that the browser does not request/render the complete fixture
  when navigating a small scope.

## Guardrails

- Run this as an explicit benchmark/marked test, not the ordinary unit suite.
- Use fixed seeds and publish fixture counts in the output so regressions are
  comparable.
- Do not call external LLMs.
- A benchmark must fail loudly if a scoped endpoint returns out-of-scope graph
  nodes, even if its latency happens to be acceptable.

## Acceptance

The task produces a repeatable command and a checked-in baseline report. It
does not set arbitrary universal performance targets before the host budget is
chosen, but it must establish bounded-payload behavior and catch accidental
whole-world graph responses.




---

## todo/world/task-408-goblin-scenario-node-dedup-and-data-integrity.md

---
type: task
status: todo
area: world
priority: high
---

# task-408: Goblin scenario consolidation, dedupe, and folder authoring

**Filed:** 2026-09-19  
**Depends on:** nothing (data task).  
**Evidence:** measured against `data/scenarios/`, 2026-09-19.

## Goal

Keep **one** goblin scenario, fix its duplicate character nodes and way ids,
attach the intended traits, and introduce a folder-based authoring format that
compiles to a single JSON — because asking an LLM to emit one huge scenario JSON
has proven unreliable.

**Decision:** do not archive the bad files — **delete** the four byproducts and
keep the best one.

## Findings (measured)

| File | KB | players | areas | ways | chars | items | triggers | dup char names |
|---|---|---|---|---|---|---|---|---|
| `kraktooth_goblin_camp.json` | 436 | **23** | 30 | 30 | 46 | 18 | 11 | 22 |
| `kraktooth_goblin_camp_assembled.json` | 1281 | 67 | 30 | 112 | 68 | 474 | 11 | 1 |
| `kraktooth_populated.json` | 205 | 1 | 20 | 20 | 1 | 98 | 0 | 0 |
| `kraktooth_generated_connected.json` | 83 | 1 | 25 | 25 | 0 | 27 | 0 | 0 |
| `kraktooth_generated.json` | 47 | 1 | 18 | 9 | 0 | 20 | 0 | 0 |

The other four are generator/assembly byproducts with no real roster (1 or 67
players), so `kraktooth_goblin_camp.json` is the keeper. All five are valid
UTF-8.

Other verified facts:

- `kraktooth_goblin_camp.json` duplicates every character: 46 nodes for 23
  players; 22 names appear exactly twice.
- Way edges previously referenced sanitized ids (`area_chiefs_pit`) while area
  node ids kept punctuation (`area_chief's_pit`); `tools/repair_way_links.py`
  symmetrized links and connected Side Tunnels ↔ Water Source, but the authored
  data should be correct at source.
- Goblin characters have empty `traits`; `data/library/traits/high_metabolism.json`
  (Hunger ×2, Thirst ×1.5, Energy ×1.3) exists but is unattached.
- **The 11 authored triggers are dead data.** They are written in a legacy
  shape: an edge `logic_trigger_X → area_Y` (type `triggers`, no properties)
  with `event` on the logic_trigger node. The runtime only matches edges whose
  **own** properties carry `trigger_type`, with the owner as the edge source.
  Nothing consumes `logic_trigger.properties["event"]` and nothing flips these
  edges at load, so none of the camp's on_enter / on_examine / on_eat / on_drink
  triggers fire. The folder-authoring compiler must emit the modern shape
  (source = owner node, target = logic_trigger, `trigger_type` on the edge).
- **Raw JSON node keys do not match their `id` fields**, and the 46→23 dedupe
  has a wrinkle: 22 duplicates are bare-named orphans (node id equals the display
  name, 0 edges, referenced nowhere) and can be deleted; the surplus is a
  `player_human_explorer` / `player_player_human_explorer` artifact. Because
  keys and ids disagree, dedupe must load through `WorldGraph` and prove each
  orphan (0 edges, not referenced by any player/edge) before removing it —
  raw JSON surgery is unsafe.
- Four generated byproducts were already deleted (2026-09-19):
  `kraktooth_goblin_camp_assembled.json`, `kraktooth_populated.json`,
  `kraktooth_generated_connected.json`, `kraktooth_generated.json`.

## Changes

1. **Consolidate.** Delete `kraktooth_goblin_camp_assembled.json`,
   `kraktooth_populated.json`, `kraktooth_generated_connected.json`, and
   `kraktooth_generated.json`; keep `kraktooth_goblin_camp.json` as the single
   goblin scenario. Remove or repoint any tool/README references to the deleted
   files (the generator/assembler can still produce them on demand).
2. **Dedupe.** Find and fix the assembly/generation step that duplicates
   character nodes (scenario created in `f928350`, assembled in `ee18a9c`) so 23
   players produce 23 character nodes; de-duplicate the checked-in file keeping
   the node each player references; verify edges, containment, inventory, and
   relationships after.
3. **Canonicalize way/area ids** so strict-id pathfinding works without the
   normalized-name fallback in `engine/background_simulation.py`.
4. **Attach `high_metabolism`** to the goblin characters (or document why not,
   if it makes a one-week survival target unreachable).
5. **Folder authoring → compiled JSON** (side quest). Author a scenario as a
   directory (`scenario.json` manifest + `rooms/*.json`, `characters/*.json`,
   `items/*.json`, `ways/*.json`), and compile to the single JSON the runtime
   already loads. Rationale: a whole-scenario JSON is too complex for an LLM to
   emit reliably in one shot; per-entity files are small, reviewable, and
   individually generatable. The runtime loader stays single-file at first, so
   this is a build step, not a runtime change.

## Acceptance

- Exactly one goblin scenario file remains in `data/scenarios/`.
- Character node count equals player count; no duplicated character names.
- Strict-id BFS reaches water/food from every area (30/30) **without** the
  name-normalizing fallback.
- The scenario loads and validates; existing assembly/validation tests pass.
- A 2-day soak still ends 23/23 alive after the change.
- Folder authoring compiles deterministically to a byte-identical JSON on
  repeated runs, and the compiled file loads through the normal path.

## Non-goals

- Inventing new areas, items, or population.
- Changing weather or decay calibration (already landed).
- Changing the runtime loader to read folders directly (compiler only, for now).

## Verification

- A data test asserting node counts per type and no duplicate character names.
- A reachability test using strict ids only.
- `tools/soak_sim.py` 2-day check.
- Compile-twice-equals test for the folder authoring format.

## Progress — 2026-09-20 (authoring fixes)

The trigger validator went from **78 issues / 45 nodes → 0 issues**, and the 11
dead triggers now fire. Applied with `tools/fix_scenario_authoring.py`
(dry-run by default):

- **Triggers**: inverted the 11 legacy `logic_trigger -> owner` edges to
  `owner -> logic_trigger` with `trigger_type` on the edge; migrated flat
  `message` / `spawn_items` / `grant_memory` into `effects[]`.
- **Ways**: filled the missing reverse-side `cardinal` / `direction` /
  `visible_in_direction` (the cause of the backwards exit labels) and the one
  missing `pass_message`.
- **Weapons**: added `damage` (mirrored from `damage_dice`) to Club, Knife,
  Rusty Hatchet, Spear.
- **Effect aliases**: `decrement_uses` → `adjust_uses {delta:-1}`,
  `roll_condition` → `save` (list branches).
- **Engine**: new `grant_memory` effect + `once` fire-once gate (both were
  needed to make the discovery triggers safe — without `once` they duplicated
  their spawned items on every examine).
- **Tests**: `tests/test_camp_trigger_wiring.py`.

Still open in this task: dedupe the 46→23 character nodes, canonicalize
way/area endpoint ids at authoring time, attach `high_metabolism`, add a
`name`/`meta.title` (the app currently labels the file `world_template`), and
the folder-authoring → compiled-JSON format.

## Progress — 2026-09-23 (folder-authoring compiler, side quest)

Change 5 (folder authoring → compiled JSON) has a first working slice:

- `tools/compile_scenario.py` — compiles a folder to one scenario JSON.
  - Layout: `scenario.json` manifest + `rooms/` (alias `areas/`), `ways/`,
    `items/`, `characters/`, `triggers/`.
  - Manifest runtime keys pass through; `name` → `_scenario_name`.
  - Characters compile to a `players` block **and** a canonical `player_<Name>`
    node; authored area ids are translated to the area display name for
    `players[].current_area` (engine convention).
  - Deterministic: sorted file order + `sort_keys=True` → byte-identical compiles.
- `tools/build_scenario.py` — reusable graph builder now accepts alternate
  folder names (`dir_names`) and bare/unprefixed filenames (id prefixed from the
  name when the stem lacks `area_`/`way_`/`item_`/`logic_trigger_`). Existing
  prefixed components behave exactly as before.
- `tests/test_compile_scenario.py` (4) — determinism, ids/players, way edges,
  and a full `/api/load` round-trip asserting no duplicate characters.
- Docs: `tools/scenario-folder-authoring.md`.
- Full suite: 3455 passed, 6 known pre-existing failures.

Still open in this task: migrate the goblin scenario into a folder under this
format, dedupe 46→23 at source (respecting the task-316 alias contract — see the
2026-09-23 note above), canonicalize way/area ids, attach `high_metabolism`, add
`name`/`meta.title`, and resolve the re-introduced validator issues.

## Progress — 2026-09-23 (re-validation; trigger fixes not in the committed file)

Re-checking the committed `data/scenarios/kraktooth_goblin_camp.json` today shows
**76 validator issues**, not 0:

```
python tools/validate_scenario.py --input data/scenarios/kraktooth_goblin_camp.json
→ 76 issues
  - 23x  Character player_* missing description   (runtime player anchors)
  - 53x  Trigger ... missing target / no incoming triggers edge
```

The same 76 issues are present in a pre-edit backup, so they are pre-existing.
This means the 2026-09-20 authoring fixes (78 → 0) are **not** in the current
file. Most likely cause: the scenario has `persist: true`, so loading it in the
editor rewrites the file from the live world and re-introduces runtime artifacts
(player anchors with no description, triggers whose `triggers` edges were not
restored). Filed as bug-47 and folded in here — the folder-authoring compiler
(change 5) should also define whether persist may ever write a scenario file,
and if so, strip runtime-only artifacts first.

Character identity note: `tests/test_character_identity.py` requires the legacy
`character_*` aliases to remain in the file so `collapse_character_identity`
(task-316) can merge them idempotently on load. Do **not** satisfy this task's
"46→23" by deleting the `character_*` nodes outright — that breaks the alias
contract. Dedupe must mean: one node per character *after load*, with the file
keeping aliases that collapse cleanly.



---

## todo/world/task-411-attention-budget-and-fidelity-tiers.md

---
type: task
status: todo
area: world
priority: medium
---

# task-411: Attention budget and fidelity tiers

**Filed:** 2026-09-19  
**Depends on:** task-407 (graph indexes); conceptually on task-397 (scopes).  
**Spec:** `docs/design/long-horizon-simulation-progress.md` §1;
`docs/design/reversibility-contract.md`.

> **Amended by task-418.** `radius_hops` is superseded. In a text/graph world
> a hop radius is an arbitrary spatial fiction whose only real job is bounding
> cost; attendance now derives from **awareness channels** (sound first,
> reusing `engine/sound.py`'s per-way barriers), plus co-presence, recency and
> hooks. Keep the anchors, cap, and eviction determinism from this task;
> treat `radius_hops` / `hysteresis` as retired. task-418 is authoritative for
> the attended-set selection.

## Where this sits (not the timeskip simulator)

Three separate things, easy to conflate:

- **task-411 (this) = the selector.** Decides *who* is attended (full fidelity)
  vs backgrounded, from player/editor focus + anchors + radius + cap. It does
  not simulate anyone.
- **task-399 / task-409 = the non-focus runner.** The deterministic
  supercharged-simple-NPC sim that actually lives out time for everyone *outside*
  the attended set.
- **task-414 = time advance ("timeskip").** Running many ticks in a batch.

Status changes (focus moves) are the promote/demote seam: 411 names the set,
412 does the handoff, 399/409 carries the off-screen time.

## Design

- **Anchors:** the focused character, the human player, pinned locations/items.
- **Radius:** graph-hop distance from anchors; within X rooms counts as attended.
- **Cap:** global maximum on attended characters, with deterministic eviction.
- **Hysteresis:** no flapping on a boundary; promote on approach and on
  trajectory for roamers.
- Multiple spread-out humans each get a set; the shared cap is the knob.

## Concrete shape

```json
{
  "cap": 8,
  "radius_hops": 2,
  "hysteresis": {"enter": 2, "exit": 3},
  "anchors": [
    {"kind": "character", "id": "player_gribba"},
    {"kind": "human", "id": "player_human"},
    {"kind": "item", "id": "item_water_skin"}
  ],
  "attended": ["player_gribba", "player_human", "player_krikka"]
}
```

**Selection algorithm** (uses task-407 indexes, no full scan):

1. Multi-source BFS from anchors over exits, bounded to `max(enter, exit)` hops.
2. Candidate priority (high → low): anchor, human, pinned, then proximity by
   hop, then recency of last foreground tick, then id.
3. Fill to `cap` in priority order.
4. Hysteresis: a character already attended is kept while within `exit` hops;
   a new character enters only within `enter` hops.
5. Evict the lowest priority when over cap; ties broken by id for determinism.

Proposed defaults (configurable): `cap 8`, `enter 2`, `exit 3`.

**Worked example.** 23 goblins, cap 8, a human at `Chief's Pit`, following
Gribba. BFS radius 2 from those two anchors reaches ~7 characters → all
attended, everyone else backgrounded. Move the human to `Blackmarsh`: Gribba
stays attended (anchor), the old pit neighbours cross the `exit` radius and
demote, Blackmarsh neighbours enter. Two humans far apart each get a radius but
share the cap, so the nearest/high-priority win and the rest stay background.

## Changes

1. Compute the attended set over the graph without a per-tick full scan (reuse
   task-407 indexes).
2. Promote on approach/trajectory; demote on distance with hysteresis.
3. Deterministic eviction ordering; anchors serialized.
4. Feed the attended set into the tick loop so only attended characters run the
   foreground policy; everyone else stays background (task-399).

## Acceptance

- Attended-set size stays ≤ cap regardless of population (fixture test).
- Two humans far apart each get a set; total ≤ cap and deterministic for a
  fixed state.
- No flapping across a boundary (hysteresis test).
- Attended set and anchors survive save/load.
- Promotion here feeds task-412's catch-up handoff, not a second state model.

## Non-goals

- Physical chunk unloading / cross-chunk simulation (task-401).
- Changing per-character decision rules.
- Simulating or advancing time (that is 399/409 and 414).

## Verification

- Unit: cap enforcement, eviction determinism, hysteresis, serialization.
- A populated fixture (e.g. 200 characters) proving the set stays bounded.



---

## todo/world/task-416-area-major-tick-iteration.md

---
type: task
status: todo
area: world
priority: high
---

# task-416: Area-major tick iteration

**Filed:** 2026-09-20  
**Depends on:** task-407 (graph indexes).  
**Enables:** task-417 (meeting gate), task-419 (positional fidelity), task-411
(attendance).  
**Spec:** `docs/design/long-horizon-simulation-progress.md`.

## Goal

Restructure the per-tick sweep from entity-major to **area-major**:

```
for area in areas (sorted):
    for character in characters_in(area):
        ...
    for item in on_tick_items_in(area):
        ...
```

Co-presence stops being a repeated ad-hoc filter and becomes the loop
structure. Today `engine/tick_manager.py` iterates
`player_manager.players.items()` and reconstructs "who else is here" inline
(`:449` does exactly this: `op.current_area == player_area_name`). That is O(n)
per character with a linear scan per site, and there are several sites
(`:197`, `:205`, `:449`, `:851`).

## Non-negotiable constraint

**Do not conflate iteration order with turn order.** These are two different
things and only one of them is currently a contract:

- **Area-major iteration** decides the order in which area-scoped evaluation
  runs: building the co-presence index, standing-item / `on_tick` trigger
  evaluation, ambient effects, presence lists.
- **Turn order / the queue** decides who *acts*, and includes the human slot
  blocking round completion. That behaviour is user-verified and must not
  change.

If area-major iteration reorders who acts, the change is wrong. Keep the acting
queue exactly as-is and use area grouping only for scoped evaluation, unless a
separate task explicitly renegotiates turn order.

## Changes

1. Build an **area → [character]** index once per tick from
   `player.current_area` (and the graph `in` edges for items). Reverse index,
   not a scan per character.
2. Iterate areas in **sorted id order**; characters within an area in the
   existing queue order. Determinism must be provable: a fixed seed and fixed
   state must replay identically.
3. Standing-item / `on_tick` trigger evaluation moves inside the area loop so
   an area's items fire together with its characters.
4. Replace the ad-hoc co-presence scans (`tick_manager.py:449` and siblings) with
   a lookup into the index.
5. Skip empty areas cheaply; do not visit areas with no characters and no
   on-tick items.

## Acceptance

- Identical simulation outcome for a fixed seed vs. the current implementation
  on the camp fixture (same events, same order).
- Co-presence lookups are O(1) per character after the index build.
- Human turn-slot blocking behaviour is unchanged.
- Standing-item `on_tick` triggers fire exactly once per tick, in a
  deterministic area order.
- Perf: no regression on the 10,080-tick week soak (currently ~181 ticks/s).

## Non-goals

- Changing turn order, action costs, or the action-resolution rules.
- Chunk unloading (task-401) or scope projection (task-397).
- Multi-minute ticks (that is config: `time_per_tick_minutes`).

## Verification

- Fixture test: characters in the same area share one index entry; characters in
  different areas never appear in each other's co-present set.
- Determinism test: two runs, same seed, identical trace.
- Regression: `tests/test_perf_guards.py` extended to assert the tick loop does
  not scan all characters per character.



---

## todo/world/task-418-awareness-channels-audibility-over-radius.md

---
type: task
status: todo
area: world
priority: high
---

# task-418: Awareness channels — audibility replaces `radius_hops`

**Filed:** 2026-09-20  
**Amends:** task-411 (attention budget), specifically the `radius_hops` /
`hysteresis` design.  
**Depends on:** task-416 (area index), task-407 (indexes), `engine/sound.py`.  
**Related:** bug-30 (sound propagation path selection).

## Problem

task-411 selects the attended set using `radius_hops: 2` — graph-hop distance
from anchors. In a text/graph world with no Euclidean space, hop radius is an
arbitrary spatial fiction. Its only actual job is **bounding cost**: it is a
cheap proxy for "co-present at one remove."

That proxy is now unnecessary, because the world already has a principled
cross-area channel: **sound**. Sound is the only way characters interact through
a way. It is already implemented with per-way barriers (open 0.5 / see-through
0.75 / closed 1 / locked·blocked 1 / hidden 2) in `engine/sound.py` — which is exactly the sober
form of "one hop away," with the advantage that a locked door demotes someone
for a *physical* reason instead of an arbitrary `enter: 2`.

## Design

**Awareness is a set of channels, each answering one question: from this origin
area, what else can be perceived, and how strongly?**

```python
class AwarenessChannel:
    def propagate(self, graph, origin_area_id) -> dict[str, float]:
        """area_id -> strength (0..1), including the origin."""
```

Priority order for the attended set (highest first):

1. **Anchors** — the focused character, the human, pinned items/locations.
2. **Co-present** — same area as an anchor.
3. **Aware** — reachable through any channel above its threshold.
4. **Recency** — recency of last foreground activity.
5. **Hooks** — mid-plan, mid-quest, or inside a trigger's scope.

Fill to `cap`, evict deterministically by `(tier, recency, id)`.

### Channels

| Channel | Source | Notes |
|---------|--------|-------|
| `sound` | `engine/sound.py` propagation | Implement now. |
| `comms` | communication items (radio, phone) | Later; item-scoped, not area-scoped. |
| `magic` | scrying / sending spells | Later. |
| `sight` | spyglass / telescope, line-of-sight | Later; needs a sight model, not just barriers. |

`Radius_hops` is retired. Hysteresis, if kept at all, applies to a channel
threshold (avoid flapping when a door opens/closes), not to a hop count.

### Caching

Sound propagation is a graph walk. Cache the per-area aware set on **graph and
door-state revision**, exactly as `engine/lighting.py`'s
`recompute_area_lights()` caches on the graph revision. Never recompute per
character or per tick.

## Interaction with bug-30 — read before implementing

bug-30 notes that `engine/sound.py` uses a FIFO BFS that returns the *first*
path rather than the *least-damped* path, and the dev note on that bug argues
sound should behave like a **shockwave** (any surviving amplitude), not a
single cheapest route.

For attention this distinction is small: the question here is "is any route
audible above threshold," which is closer to the shockwave reading than to
shortest-path. Do not let this task silently depend on bug-30 being fixed — pick
the semantics deliberately and state which one the threshold means. If a
locked door must be able to cut a character out of attention, that requires the
route *not* being reachable by a cheap alternate path, which the current FIFO
walk may or may not give.

## Acceptance

- Attended set is derived without any hop-radius parameter.
- A character separated from all anchors by a locked/closed door sequence is
  **not** attended (barrier test with a fixture).
- Awareness results are cached and not recomputed per character per tick.
- The set stays ≤ cap and is deterministic for a fixed state.
- Removing `radius_hops` does not change which characters are *co-present*.
- Channel interface has one implemented channel (`sound`) and a test double for
  a second, proving the seam works without implementing comms/magic.

## Non-goals

- Implementing communication items, magic, or scrying (those are their own
  tasks; this task only defines the channel seam).
- Changing per-character decision rules.
- Simulating or advancing time (task-399/409, task-414).

## Verification

- Unit: fixture with A–B open, B–C locked → sound from A reaches B, not C.
- Unit: cap enforcement, eviction determinism, serialization of anchors.
- Perf: awareness cached; a 200-character fixture proves no per-tick full scan.



---

## todo/world/task-419-relational-spatial-model-and-anchor-budget.md

---
type: task
status: todo
area: world
priority: high
---

# task-419: Relational spatial model — one `at` per character, positional fidelity, anchor budget

**Filed:** 2026-09-20  
**Depends on:** task-416 (area index).  
**Relates:** task-411/418 (attendance), task-9 / task-398 (population and
generation), `engine/character_spatial.py`, `graph.py:465-470`.

## Position is a relation, not a coordinate

There is no metric space inside an area. A character's position is the set of
spatial edges it holds: `in`, `on`, `under`, `behind`, `beside`, `at`. Space
between areas is real and ordered, but it is measured in **time** (way travel
cost × `time_per_tick_minutes`), not in hops — hops are only a cached proxy.

## Invariant: at most one `at` per character

A character holds **exactly one** `at` edge at a time, or none. Not one per
target — one total. This means the whole world holds at most
`population` `at` edges, not O(n²), and a crowded area cannot blow up the edge
set.

`engine/character_spatial.py:114` (`clear_character_position_edges`) already
exists for this reason. This task makes the invariant explicit and enforced.

## Positional fidelity = attendance tier

This is what keeps `at` cheap. Positional detail is allocated by the same
attendance decision as everything else:

| Tier | Edges written | Count |
|------|---------------|-------|
| Background / co-present only | `in <area>` | population |
| Attended | `in <area>` + `at <anchor>` | ≤ cap |

So 40 characters in an area produce 40 `in` edges and at most 8 `at` edges. The
other 32 are simply "in the area." This removes the per-pair `at` churn and
removes any need for an anchor per character.

## Proximity = relational hop distance

`at` alone is binary, but composed with `beside`/`on` it yields an ordered,
discrete proximity:

```
you --at--> boulder --beside--> old oak
```

- **1 hop** — you are at it (the boulder).
- **2 hops** — a neighbour of your anchor (the oak).
- **unreachable** — elsewhere in the area; the prose says "across the room."

No coordinates. The `beside` chain *is* the coordinate system.

## Anchor vocabulary and budget

An anchor is a node that is an interaction target. Two shapes, both already
expressible:

- **Pooled resource** — "gravel on the ground": one node, described as a
  quantity, and on use/take it spawns a handful of real items bounded by the
  pool. Same model as the berry thicket: one bush, described as many, spawns
  berries.
- **Landmark cluster** — "boulder by the old oak": two nodes joined by
  `beside`, either of which can be the `at` target.

**Budget:** 3–8 anchors per wilderness area, chosen deterministically from the
area's anchor candidates (seeded, per task-398's generator contract). A forest
does not need 500 rocks; it needs a few pooled/landmark anchors that the prose
layer expands into "rocks", "undergrowth", "fallen oak."

## Acceptance

- No character ever holds two `at` edges (invariant test, and a validator).
- Background characters hold no `at` edge; attended characters hold exactly one.
- Proximity phrases are *derived* from the relation path, never stored.
- A wilderness fixture area has ≤ 8 anchors and still reads as populated.
- A pooled-resource anchor spawns a bounded handful on interaction and depletes.
- Save/load preserves the `at` edge and the anchor budget.

## Non-goals

- Room grids / intra-area coordinates (task-99) — explicitly not this model.
- Changing movement, `approach`, or sound rules.
- Authoring every anchor for every existing area.

## Verification

- Unit: invariant — attempt a second `at` edge, assert the first is cleared.
- Unit: proximity derivation returns 1 / 2 / unreachable for the three cases.
- Unit: pooled anchor spawns ≤ N items and decrements on depletion.
- Fixture: attended vs background positional edge counts on the camp.



---

## todo/world/task-421-light-barrier-parity-with-sound.md

---
type: task
status: todo
area: world
priority: medium
---

# task-421: Light propagation barrier parity with sound

**Filed:** 2026-09-20  
**Relates:** `engine/lighting.py`, `engine/sound.py`, task-418 (awareness
channels), bug-30.

## Problem

The world now has two propagation systems with **different barrier semantics**:

- **Sound** (`engine/sound.py`) respects way state: open 0.5 / see-through 0.75
  / closed 1 / locked·blocked 1 / hidden 2.
- **Light** (`engine/lighting.py`) does not. `_neighbour_light` /
  `_best_spill` / `recompute_area_lights` spill light to neighbour areas with no
  check on the connecting way.

So a lit room bleeds a full light contribution through a **closed, locked**
door. That is physically wrong, it makes the light level of a corridor
depend on rooms it cannot actually see into, and it will quietly break any
future stealth or darkness mechanic that trusts area light level.

## Design

1. Apply the same barrier table to light spill as to sound. A locked door should
   produce approximately zero spill; a closed door a small fraction; an
   open or see-through way most of it.
2. Put the barrier table in **one** place and have both modules import it, so the
   two systems cannot drift apart again. If sound and light genuinely need
   different values, that is fine — but it must be two named tables side by
   side, not one hard-coded and one absent.
3. Keep the existing caching behaviour: `recompute_area_lights()` stamps on the
   graph revision. Barrier state (door open/closed) must therefore be part of the
   revision or the cache key, or the stamp will be stale when a door moves.
4. Preserve the "effective light = highest single source, not the sum" rule from
   the lighting work. This task changes *spill*, not the aggregation rule.

## Acceptance

- Light spill through a locked/closed way is gated by the same barrier values as
  sound, with a fixture test: two areas joined by one door, door open vs closed
  vs locked → three distinct spill results.
- A single shared barrier table exists; changing a value changes both systems.
- Light recomputation still happens on the revision stamp, and opening/closing a
  door invalidates it.
- No change to the per-area "highest single active source" aggregation.

## Non-goals

- Line-of-sight / shadow casting within an area (that would be a sight channel,
  task-418, and is not needed now).
- Changing how light is authored on items or areas.
- Fixing bug-30 (sound path selection) — separate concern.

## Verification

- Unit: barrier gating for open / see-through / closed / locked.
- Unit: cache invalidation on a door state change.
- Regression: existing lighting tests still pass with the aggregation rule
  unchanged.



---

## todo/world/task-439-canonical-area-identity-in-save-and-lookups.md

---
type: task
status: todo
area: world
priority: high
---

# task-439: Canonical area identity in the save and in area lookups

**Filed:** 2026-09-21
**Blocks:** task-438 (NL editor region decomposition), task-397 (world scopes), task-401 (chunk persistence)
**Related:** task-407 (graph edge indexing + case normalization), task-393 (validator triage), task-222 (serialize exits graph-only), `engine/serialization.py`, `docs/virtualWorld/World Building/Rooms & Areas.md`

## Goal

Make an area's **id** the canonical key everywhere it is persisted or looked up, so two
areas may share a display name without one silently overwriting, re-homing, or
mis-resolving the other.

This is the prerequisite for any world decomposition: splitting Deep Forest, Hills, Murk
Lake and the rest into sub-areas **guarantees** display-name reuse. `data/library/areas/`
already contains `weeping_willow_hollow`, `snowbound_hollow`, `frozen_hollow`,
`frozen_lake_clearing` and `blizzard_forest_clearing`; a decomposed world will have many
"hollows", "clearings" and "crossings" at once.

## Problem

The graph layer is already id-keyed and case-safe — `WorldGraph` resolves ids through
`_id_index` (`graph.py:70-77`), keys `self.nodes` by id (`graph.py:137-138`), and treats an
area **id** collision as a hard error while auto-suffixing items/ways/characters
(`graph.py:126-136`). The **save and lookup** layer is not:

1. **The save dict is keyed by display name.**
   `engine/serialization.py:191`:
   ```python
   rooms_serialized[node.name] = { ... }
   ```
   Two areas named "Hollow" collapse to one entry. This is silent data loss, not a
   performance problem — and it is the documented behaviour today
   (`docs/virtualWorld/World Building/Rooms & Areas.md:51-60`).

2. **Exits are resolved by display name.**
   `engine/serialization.py:197`:
   ```python
   "exits": self.player_manager.build_exits_for_area(node.name),
   ```
   Ambiguous once two areas share a name.

3. **`current_area` is compared by display name, first match wins.**
   `engine/serialization.py:77`:
   ```python
   if node.type == "area" and node.name == player.current_area:
   ```
   On a duplicate name this silently picks the wrong area, so a character can get the
   wrong area's temperature/environment. `Player.current_area` is a display-name string
   in 47+ references across 10 files
   (`docs/virtualWorld/dev_tasks/critical-review-scale-2026-09-08.md:48-57`).

4. **The save format carries two aliases for the same data.** `load_from_dict` reads both
   `areas` and `rooms` keys, so any change must touch both paths or they diverge
   (`critical-review-scale-2026-09-08.md:32-34`).

## Design

### Key by id, keep name as a field

- `rooms_serialized[node.id] = { "id": node.id, "name": node.name, ... }`.
- Apply the same change to every alias of the `areas`/`rooms` path in both
  `_serialize_world` and `load_from_dict`.
- `build_exits_for_area` takes the node id (or the node), not the display name.

### Ambiguity must be loud, not silent

Where a lookup genuinely only has a name (notably `Player.current_area`), resolution must
be **deterministic and reported**:

- resolve by id first when the stored value resolves to an area id
  (`graph._resolve_id`), otherwise by name;
- if a name matches more than one area, log a warning and pick by a stable rule
  (sorted id) **and** surface it in the validator — never silently take iteration order;
- de-duplicate on load as well as on save (a legacy save with colliding name keys has
  already lost data; do not compound it).

### Backward-compatible load

Legacy saves are name-keyed. On load, normalize name keys to ids. If two keys would
normalize onto the same id, or a name is ambiguous, record it in the load report rather
than dropping the entry silently.

### Interim authoring constraint

Until `current_area` is structurally id-based (see Non-goals), **display names must be
unique within a scenario**. Task-438's `split_area` therefore mints scenario-unique names
(e.g. "Deep Forest — Creek Margin") rather than bare "Creek Margin". This is also better
authoring practice.

### Validator rule

Add a duplicate-display-name diagnostic to the validator (task-393) and the library lint
(task-323): duplicate **ids** are already an error; duplicate **names** become legal at
the graph level but must be visible, so a scenario never ships with an ambiguity nobody
can see.

## Work plan

1. `engine/serialization.py`: key the serialized area map by `node.id` (include both `id`
   and `name` in the payload); update every `areas`/`rooms` alias path.
2. `build_exits_for_area`: resolve by id; update the `:197` call site.
3. `:77` temperature resolution: resolve by id, then unambiguous name; warn on ambiguity.
4. `load_from_dict`: normalize legacy name-keyed saves to id keys; produce a load report
   for collisions/ambiguities instead of silently collapsing.
5. Validator (task-393) + library lint (task-323): duplicate-display-name diagnostic.
6. Tests: round-trip a graph with two same-named areas in different regions and assert
   both survive save/load, both keep distinct exits, and each character's environment
   resolves to the correct area.

## Acceptance

- A graph containing two areas both named "Hollow" (ids `area_a_hollow`, `area_b_hollow`)
  round-trips through save/load with **both** present, distinct exits, and distinct
  environment/temperature resolution.
- Legacy name-keyed saves still load, with a report naming any entry that could not be
  normalized unambiguously.
- No regression: `python -m pytest tests/ -q -k "not mcp and not emote"`; add a
  serialization fixture covering the duplicate-name case.
- The validator flags a scenario holding two areas with the same display name.

## Non-goals

- **The `Player.current_area` string → id refactor.** That is 47+ references across 10
  files and is its own task (it gates task-401). This task only makes lookups
  unambiguous and loud, and its interim constraint is unique display names.
- Changing the graph node model — `WorldGraph` is already id-keyed; no change needed.
- Removing `exits` from the serialized area payload (that is task-222's question, tracked
  separately in `review/gameplay/task-222-serialize-exits-graph-only.md`).

## Risks

- **Legacy saves already lost data.** A save written while two areas shared a name cannot
  recover the overwritten entry; the load report can only surface that ambiguity existed.
- **`areas` *and* `rooms` aliases.** Touching one path and not the other makes the save
  and load disagree; assert both in the round-trip test.
- **Scope creep into the `current_area` refactor.** Keep the string-value change out of
  this task or it becomes unlandable; the interim constraint (unique names) is what makes
  the deferral safe.



---

## todo/world/task-495-worldpainter-recursive-scope-grids-and-3-mode-editor.md

---
type: task
status: todo
area: world
priority: medium
---

# task-495: WorldPainter: recursive scope grids and 3-mode editor

**Filed:** 2026-09-24
**Related:** task-397, task-398, task-400

## Goal

Authoring layer: every world scope owns a bounded grid at its own resolution, with three modes - world (zones as cells, no interiors), town (paint settlement grid: walls, gates, roads, markets, buildings), interior (building/floor grid: rooms, doors, windows, tags). Zones ARE world_scopes (engine/world_scopes.py); select a zone to set its scale and open its drawn grid. Paint layers: biome/feature/road/elevation. Features are child scopes placed at a cell (e.g. a village inside a forest) that can be moved/added/deleted. Data model: per-scope grid_w/grid_h, cell_scale, layers, child placements; stable frames so references survive moves; a rule for move-overlap. UI renders each scope's grid.

## Acceptance

- A scope can be selected; its grid (`grid_w`/`grid_h`, `cell_scale`, layers) opens in the matching mode (world/town/interior).
- A feature (child scope) can be placed at a cell, moved, added and deleted; the parent's placements update.
- Grids are recursive: a parent cell can hold a child scope whose own grid opens in the next mode.
- Moving a feature over occupied cells follows a documented rule (forbid / displace / merge) and preserves ids/references.
- The scope manifest + child placements serialize and round-trip, covered by tests.



---

## todo/world/task-496-worldpainter-grid-to-graph-compiler-cells-to-areas-and-ways.md

---
type: task
status: todo
area: world
priority: high
---

# task-496: WorldPainter: grid-to-graph compiler (cells to areas and ways)

**Filed:** 2026-09-24
**Related:** task-495, task-398, task-400

**Overlaps task-398.** task-398 already owns the deterministic generation contract (the `GenerationPatch` shape, provenance, apply-once, "a manual edit survives a second run"). This task is the *painted-grid recipe* — wilderness/road/biome tiles + region-merge — that should emit a `GenerationPatch` through 398's contract rather than a parallel generator. Decide whether to fold it into 398 or keep it as the grid recipe.

## Goal

Compile a painted scope grid into the existing area/way node+edge format: cells become areas (optionally region-merged by biome via flood-fill), adjacent cells get ways (direction, open/see_through, floor), and areas get tags, environment, floor and world_scope_id. Descriptions are deterministic templates over (own tile + 4 neighbours + exits/directions), reusing visible_in_direction (engine/area_description.py); no LLM at lattice scale. Emit into the scenario/library formats so the engine is unchanged. Decide grid-canonical vs baked-and-hand-edited per zone to avoid the task-289/290/317 clobber trap.

## Acceptance

- A painted grid compiles to areas + ways in the existing scenario/library formats, loadable with **no engine change**.
- Optional region-merge collapses contiguous same-biome cells into one area (flood-fill); a test shows fewer nodes with identical topology.
- Ways carry `direction`/open/`see_through`/`floor`; areas carry tags, `environment`, `floor`, `world_scope_id`.
- Descriptions are deterministic from (own tile + 4 neighbours + exits) with **no LLM call** — sample: "a road running east and west, sparse forest to the north".
- Grid-canonical vs baked-and-hand-edited is decided and enforced (edit-after-bake is not silently clobbered; see task-289/290/317).



---

## todo/world/task-497-worldpainter-biome-feature-taxonomy-and-distribution-layers.md

---
type: task
status: todo
area: world
priority: medium
---

# task-497: WorldPainter: biome/feature taxonomy and distribution layers

**Filed:** 2026-09-24
**Related:** task-496, task-398, task-9

## Goal

Define the tile taxonomy and its mapping to engine tags: roads (gravel/dirt/paved/cobblestone), forests (sparse/dense/leaf/mixed/pine), hills, mountains, cliffs, ravines, chasms, beach, lake, river, deep water, ocean, stream, spring, farmland; features (bridges, tunnels, towns, buildings, ruins). Provide per-biome description fragments and distribution layers for resources (tie to the engine/foraging.py tag->yield map, which already keys off road/forest/ruin tags) and hostiles (predators/bandits/monsters by biome and distance from settlement). Data-first so the vocabulary can grow.

## Acceptance

- A data file defines biomes and features with tags + description fragments; each biome maps to engine tags usable by `engine/foraging.py`.
- Resource distribution rules exist (biome → likely items), reusing the existing foraging tag→yield map.
- Hostile distribution rules exist (biome + distance from settlement → spawn likelihood).
- Adding a new biome requires data only, no code change.



---

## todo/world/task-498-elevation-gated-chained-sightlines-across-ways.md

---
type: task
status: todo
area: world
priority: low
---

# task-498: Elevation-gated chained sightlines across ways

**Filed:** 2026-09-24
**Related:** task-496, task-418, task-421

## Goal

Extend beyond-visibility from per-adjacent-way to a chained line of sight: an observer sees along a run of open/see_through ways as long as the floor property does not change; a floor step (or the run turning) breaks the chain. Build on see_through and visible_in_direction and floor (engine/lighting.py, engine/area_description.py, engine/movement.py, engine/room_perception.py). Decide the range/depth cap and whether a sighted cell reveals room contents or only the area name/description. Must not regress tests/test_beyond_visibility.py.

## Acceptance

- An observer sees along a run of open/`see_through` ways whose `floor` is unchanged; a floor delta or a direction change breaks the chain (tests).
- The range/depth cap is configurable and documented.
- The "contents vs name/description only" question is decided and recorded.
- `tests/test_beyond_visibility.py` and the lighting tests still pass.



---

## todo/world/task-499-per-agent-fog-of-war-and-map-knowledge-transfer.md

---
type: task
status: todo
area: world
priority: medium
---

# task-499: Per-agent fog of war and map knowledge transfer

**Filed:** 2026-09-24
**Related:** task-495, task-403

## Goal

Add an area/scope-level known set per character. player.known already gates hidden ways and items through viewer-aware perception (engine/room_perception.py; tests/test_known.py), and EDGE_KNOWN is abilities-only. Unknown cells/zones are fog on the map; walking, examining, or finding a map item reveals them - a map's use/read teaches known entries (reuse the existing teach path). Rendering: the map view shows only known cells/zones. Keep perception honest in agent prompts (an unaware agent is not told about unknown areas).

## Acceptance

- Areas/scopes can be marked known per character; unknown ones are fog on the map.
- Walking and examining reveal them; a map item's use/read teaches `known` entries via the existing teach path.
- Agent prompts never disclose unknown areas (perception stays honest).
- Tests cover the reveal, the fog-rendering data, and map-item knowledge transfer.



---

## todo/world/task-500-zone-driven-fidelity-and-lazy-zone-materialisation.md

---
type: task
status: todo
area: world
priority: medium
---

# task-500: Zone-driven fidelity and lazy zone materialisation

**Filed:** 2026-09-24
**Related:** task-399, task-495, task-401, task-411, task-418

**Overlaps task-401 and task-411.** task-401 already owns chunk load/evict (the actual materialisation), and task-411 (selector) + task-418 (awareness channels) own fidelity-tier selection. This task's only unique delta is using *zones* as the selection key and keeping WorldPainter-side zone records — consider folding it into 401/411 rather than tracking it separately.

## Goal

Use zones (world_scopes) as the spatial key for the existing fidelity tiers (task-399 background fidelity; engine/soak.py promote/demote; engine/trace.py records promote/demote). Distant zones should exist as scope records only and materialise their areas/ways on approach (lazy instantiation), so a 500-zone world does not hold every area/way node at once - this is the actual offloading win. Tie to task-411/412/418 attention tiers and task-407 graph edge-indexing/perf.

## Acceptance

- Fidelity-tier selection can key off a character's zone/scope (in addition to attention).
- Distant zones hold only scope records; their areas/ways are materialised on approach and can be released — a test proves node count stays bounded as the world grows.
- Promotion/demotion records survive materialise/release (`engine/trace.py`).


# inprogress
(9 files)

---

## inprogress/characters/task-210-description-enrichment.md

---
group: Pleasure System
status: inprogress
---

# Description Enrichment (Body State + Item Details)

**Filed**: 2026-08-11
**Priority**: Medium
**Status**: In progress — shipped except auto-regen on body-state change; remaining work: task-486

---

## Problem

`_update_equipment_description()` (`engine/equipment.py:524`) feeds only item names to the LLM, so it can't reason about body state or visibility through clothing layers (a hard nipple under a sheer blouse, flushed cheeks, etc.).

## Design

- Enrich `_update_equipment_description()` prompt with:
  - `_get_body_state_description(player)` — text derived from conditions (`nipple_hard`, `aroused`, `blushing`, `wetness`) + `body_state` numeric values (e.g. cheeks flush > 0.5)
    - **Shipped** as `_body_state_description_lines()` (`engine/equipment.py:617`): mature-gated map of visible conditions → phrases, injected as a `VISIBLE PHYSICAL STATE` prompt block (`:690-701`).
  - `_get_enriched_equipment_text(player)` — item names + description + `opacity`/`coverage` props (nodes from `graph.get_node_by_name()`)
    - **Shipped** as `_equipment_detail_lines()` (`engine/equipment.py:645`): per-item `opacity`/`coverage`/`current_state`/`friction`.
- Trigger regeneration on state changes via `_update_state_description()` (guarded by `world.auto_generate_descriptions` — existing flag, see `routes/settings.py:109`).
  - **Gap:** `_maybe_update_equipment_description()` (`:611`, guarded by `auto_generate_descriptions`) is only called from equip/unequip paths (`:213,297,299,318,320,347`) and a manual route (`routes/player_ops.py:723`). Nothing regenerates the stored `player.description` when conditions/body-state change; `_update_state_description()` was never added.
- Optional caching: `_get_state_hash()` (equipment + conditions + body_state) → cache dict on player, skipped when `mature_content` is off.
  - **Not implemented** (design marked optional) — no `_get_state_hash` in the codebase.
- **Frontend prompt note**: agent appearance flows through `static/js/agent/prompt-builder.js` — body state should also surface there so LLM agents see the same info as description generation.
  - **Shipped** in `static/js/agent/prompt-builder/character-state.js:478-492`, mature-gated, emitting first-person body-state lines (e.g. `nipple_hard`, `wetness`).

## Files

- `engine/equipment.py` — `_body_state_description_lines()` (`:617`), `_equipment_detail_lines()` (`:645`), prompt injection in `_update_equipment_description()` (`:671`)
- `static/js/agent/prompt-builder/character-state.js` — mature-gated body-state lines (`:478-492`)

## Testing

- [x] Description includes "hard nipples"/"flushed" when conditions present — visible-condition map in `_body_state_description_lines()`
- [x] Sheer/opaque layer distinction shows in output — `opacity`/`coverage` in `_equipment_detail_lines()`
- [ ] Description regenerates on body-state change, not just equip/unequip — **not wired** (see Gap above); tracked as task-486
- [x] Gated off when `mature_content = false` — `_body_state_description_lines()` returns `[]` unless `world.mature_content`

## Related

- `task-486` — auto-regenerate description on body-state change (the unmet acceptance item above)
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §9, Phase 3
- `task-179 event stream redesign` (if description updates need to surface visually)



---

## inprogress/characters/task-213-mature-traits.md

---
group: Pleasure System
status: inprogress
---

# Mature Traits & Body Reactions (folded from design v3.1)

**Filed**: 2026-08-11
**Priority**: Low
**Status**: In progress — 7 traits shipped, `exhibitionist`/`single_track` effects inert; remaining work: task-487, task-488

---

## Problem

The design calls for personality traits that modulate the pleasure system (`wired_differently`, `attention_seeker`, `exhibitionist`, `quick_recovery`, `sensory_memory`, `single_track`, `sex_addict`) plus a set of non-erotic "body reactions" (goosebumps, shivers, cough, sneeze, hiccup, itch).

## Design

### Traits

- Add to `TRAIT_DEFINITIONS` (`engine/traits.py:90`), respecting the **existing schema** — `name`, `description`, `category`, `params`, `effects` (VITAL_MULTIPLIER etc.), `conflicts`. New pleasure traits need a parallel `body_part_multipliers` key (consumed by task-212) since the stock `effects` dict doesn't know about body parts:
  - `wired_differently` — nipple ×3.0, genital ×0.1 — **shipped**; `body_part_multipliers` consumed by `engine/pleasure_actions.py:97-108`
  - `attention_seeker` — arousal on being looked at — **shipped**; consumed in `engine/background_social.py:227,271,304`
  - `exhibitionist` — arousal on public nudity, behavior_prompt — **inert**: effect flag defined but no consumer (`has_effect(...,"exhibitionist")` appears nowhere)
  - `quick_recovery` — halves overstimulated duration — **shipped**; `engine/tick_manager.py:1066-1068`
  - `sensory_memory` — lingering sensitivity after release — **shipped**; `engine/tick_manager.py:1071-1072`
  - `single_track` — release gated to one path — **inert**: effect flag defined but no consumer
  - `sex_addict` — Entertainment decay ×2 when Arousal < 15 — **shipped**; `engine/tick_manager.py:322-325`
- All hidden from trait pickers unless `mature_content` on (task-206). **Shipped** via the registry filter in `routes/library_ops.py:195-205` (drops `mature: true` entries when the toggle is off).

### Body Reactions (non-erotic)

- **NOTE: task-166 already covers involuntary actions** (hiccups, burps, yelps, stutters, `static/js/agent-engine.js` speech post-processing). Goosebumps/shivers/cough/sneeze/itch overlap heavily — extend task-166 rather than duplicating. Only add what task-166 misses (itch, goosebumps as condition-driven).
- These are always active, independent of `mature_content`.

## Files

- `engine/traits.py` — 7 mature trait definitions (`:210-276`), each `"mature": True`
- `engine/pleasure_actions.py` — `body_part_multipliers` consumption (`:97-108`)
- `engine/tick_manager.py` — `quick_recovery`/`sensory_memory`/`sex_addict` effects
- `engine/background_social.py` — `attention_seeker`
- `routes/library_ops.py` — mature gating for the traits/conditions registries (`:195-205`)

## Testing

- [ ] Each trait's effect applies (e.g. wired_differently nipple actions ×3) — 5 of 7 wired; `exhibitionist` (task-487) and `single_track` (task-488) have no consumer
- [x] `sex_addict` Entertainment decay doubles at low arousal — `engine/tick_manager.py:322-325`
- [ ] Body reactions from task-166 work without mature toggle — deferred to task-166 (design note); itch/goosebumps not verified here
- [x] Adult traits invisible when mature_content off — registry filter `routes/library_ops.py:195-205`

## Related

- `task-487` — exhibitionist trait effect (inert here)
- `task-488` — single_track trait effect (inert here)
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §7, §Additions #2/#4
- `task-166 involuntary actions` (in review — covers body reactions), `task-212 verb multipliers`



---

## inprogress/characters/task-215-environmental-clothing-effects.md

---
group: Pleasure System
status: inprogress
---

# Environmental & Clothing Effects (Wet/Transparency/Friction)

**Filed**: 2026-08-11
**Priority**: Low
**Status**: In progress — environment + friction trickle shipped; prop defaults and wet transparency missing (task-489)

---

## Problem

Clothing needs `comfort`/`friction`/`coverage`/`opacity` properties so the LLM can reason about layer visibility, and wet clothing should become more transparent + change friction. Environment needs weather/humidity to drive wetness.

## Design

- **Item props** (graph nodes, verified item property pattern): add `comfort`, `friction`, `coverage`, `opacity` to `item.properties`. Defaults `opacity: 0.8`, `coverage: 0.8` when absent.
  - **Gap:** no defaults are applied and no `data/library/items/*.json` defines them; `_equipment_detail_lines()` only reads the props when present (`engine/equipment.py:645`). → task-489.
- **Clothing friction → arousal trickle:** per-tick sum of equipped `friction` in `tick_turn()` (`engine/tick_manager.py:83`), small Arousal gain (0-3/tick). Already designed in task-208 — keep the friction read here, hook the trickle there.
  - **Shipped** in `engine/tick_manager.py:1028-1045`, mature-gated (`:1020-1023`).
- **Environment:** extend `area_node.properties.environment` (verified, used by `engine/area_description.py` + `lighting.py`) with `weather`/`wind_speed`; humidity tracked under task-232 (task-195 was cancelled — humidity lives there).
  - **Shipped:** `weather`/`wind`/`humidity` flow through `engine/weather_forecast.py`, `engine/environment_propagation.py`, `engine/effect_handlers/weather.py`.
- **Wet clothing:** rain/swimming → clothing wet → `opacity` up (more transparent), `friction` changes, trigger `_update_equipment_description()` (`engine/equipment.py:524`). Gated by `mature_content` for the arousal-coupling parts; wetness/transparency itself is generic.
  - **Partial:** a `wet` condition exists and dampens insulation (`engine/equipment_bonuses.py:107-115`), but nothing couples wetness to `opacity`/`friction` or retriggers the description. → task-489.
- **Layer visibility** is the real fix — enrichment lands in task-210.
  - **Shipped** for reading props (task-210); the props themselves are still missing (above).

## Files

- `engine/equipment.py` — reads `opacity`/`coverage`/`friction` in `_equipment_detail_lines()` (`:645`)
- `engine/tick_manager.py` — friction trickle (`:1028-1045`)
- `engine/equipment_bonuses.py` — wet-clothing insulation loss (`:107-115`)
- `engine/weather_forecast.py` — weather/wind/humidity environment
- **missing:** prop defaults + wet→opacity/friction coupling (no `engine/item_actions.py` exists)

## Testing

- [ ] Clothing without props defaults to opacity/coverage 0.8 — **not implemented** (task-489)
- [ ] Rain → clothing wet → opacity increases, description regenerates — **not implemented**; wetness only affects insulation (`engine/equipment_bonuses.py:107`) (task-489)
- [x] Friction sum feeds arousal trickle only when mature content on — `engine/tick_manager.py:1020-1045`

## Related

- `task-489` — prop defaults + wet transparency/friction (the unmet items above)
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §6, Phase 7
- `task-232 humidity`, `task-210 description enrichment`, `task-208 release/edging/friction`



---

## inprogress/characters/task-309-invisible-ghost-character.md

---
group: Characters
status: inprogress
---
# Invisible Ghost NPC / Undead Traits

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: In progress — NPC ghost base shipped (v1.4.0); 3-axis visibility split not on master (lives on `foil-stranger`, commit 8039509, unmerged); resistance/immunity follow-ups filed as task-490

---

## Shipped / Gap

- **On master (v1.4.0):** NPC ghost base. `player_manager.is_undead_ghost` (`engine/player_manager.py:361`) makes a spectral entity skip vitals and be untargetable by normal attacks (`engine/combat.py:131`); ghost actions/`manifest` are handled by `engine/ghost.py` + `routes/action_handlers.py:847`.
- **Not on master:** the 5e-style three-axis split — `is_undead` / `is_incorporeal` / `is_visible`, a persisted `manifested` state, `get_players_in_area()` visibility gating, and `tests/test_ghost_visibility.py`. That work is on `foil-stranger` (commit 8039509) and needs merging/porting.
- **Still open (task-490):** incorporeal damage resistance/immunity (nonmagical weapons, cold/necrotic/poison) and condition immunities (grappled/restrained/prone/exhausted/...).

## Idea

Make the ghost in the mansion an invisible/ghost character — a "dead ghost" — with traits like undead.

## Notes

- Ghost mode (dead players acting) already exists via the ghost system; this is about an **NPC** that is a ghost: invisible, not attackable by normal means, carrying undead traits.
- Medium scope: an NPC-side ghost state (invisibility to agents/room lists, `undead` tag, phasing through ways) rather than a whole new system.
- Flavorful for the mansion scenario and reuses `docs/virtualWorld/Characters/` ghost/condition machinery.

## Related

- `task-490` — incorporeal damage resistance and condition immunities (still open)
- `developer ideas.md` line 16
- `engine/ghost.py`, `engine/conditions.py`, trait system (`data/library/traits/*.json`)



---

## inprogress/graph/task-289-generic-template-link-sync.md

# Task 289 — Generic Template-Link & Sync System for All Node Types

## Status

In progress — `refresh-to-world` now dispatches **item, way, area and character**
(`routes/library_ops.py:750-769` → `_refresh_item`/`_refresh_way`/`_refresh_area`/
`_refresh_character`; the old `routes/library_routes.py:482` 400 is gone), covered by
`tests/test_library_refresh.py` and `tests/test_events_and_perentry.py`.
Remaining: `break-template-link` endpoint + inspector UI, and the designed per-type
mutable-field whitelist — fields are still handled inline per `_refresh_*`, there is
no `engine/sync.py`. See **task-317** for the World→Library half.

## Goal

Generalize the existing `refresh-from-library` item sync into a first-class template-link system that works for **areas, ways, items, and characters**. Authors can bind a placed node to a library template, sync changes from that template, and break the link to make the node standalone.

## Why

- `labs.json` currently has 36 rooms with many near-duplicates (e.g., `Task 3 - area 1 closed door` / `open door`). Drift between them is already happening.
- Only items have a partial `library_id` + `refresh-from-library` endpoint. Areas, ways, and characters have no equivalent.
- Without a template link, updating a canonical room/way/item/character requires manually editing every placed copy.

## Design Decisions

1. **`library_id` on every node** — a string field storing the source library file stem (e.g., `lab_table`, `blackout_goggles`). Absent or empty = standalone.
2. **`POST /api/nodes/<node_id>/sync-from-library`** — generic endpoint that:
   - reads the current library file by `library_id`
   - overwrites mutable fields on the node to match the library definition
   - returns a diff of what changed
3. **`POST /api/nodes/<node_id>/break-template-link`** — strips `library_id` and marks the node as standalone. Does not alter node data.
4. **Mutable field whitelist per node type** — not everything should sync. Example:
   - **items**: `name`, `description`, `tags`, `triggers`, `equip_slots`, `defense`, `damage`, `insulation`
   - **areas**: `name`, `description`, `environment`, `properties.tags`
   - **ways**: `name`, `description`, `properties`
   - **characters**: `name`, `description`, `stats`, `skills`, `traits`, `behaviors`
   - Never sync: `id`, `type`, spatial edges (`in`, `on`, `beside`, `connection`), `current_state`, `position`, player-specific data
5. **Frontend UX**:
   - Inspector panel shows "Linked to library: `<name>`" with a **Sync** button and a **Break Link** button.
   - Library browser shows "X placed instances" next to each entry.
   - Sync produces a toast with "Updated N fields" or "Already up to date."

## Implementation Steps

1. **Backend: generic sync endpoint**
   - Add `POST /api/nodes/<node_id>/sync-from-library` in `routes/nodes.py` (or equivalent).
   - Add `POST /api/nodes/<node_id>/break-template-link`.
   - Extract mutable-field logic into `engine/sync.py` with a registry per node type.
   - Reuse the existing item `refresh-from-library` logic as the template.

2. **Backend: `library_id` on all node types**
   - Ensure `area`, `way`, `character`, and `item` nodes all accept and persist `library_id`.
   - World serialization/deserialization must preserve it.

3. **Frontend: inspector integration**
   - Show template-link status and action buttons in the area/way/item/character inspector panels.
   - Wire buttons to the new endpoints.

4. **Frontend: library browser**
   - Show instance count for each library entry.
   - Allow bulk "Sync all instances" from the library view.

5. **Testing**
   - Unit tests for sync diff, break-link, and mutable-field whitelisting.
   - Smoke test: place an item from library, edit its description, sync, verify description reverts; break link, edit, sync again, verify no change.

## Out of Scope

- Template inheritance / variants (design #3 from earlier discussion). That is a follow-up task once basic sync is stable.
- Override tracking (design #2). Can be added later if authors need partial sync.



---

## inprogress/graph/task-317-bidirectional-template-link-sync.md

# Task 317 — Bidirectional Template-Link & Sync (World↔Library, unified)

## Status

In progress — both halves partly live. World→Library: `world-sync.js` `_isEmpty`/
`_mergeEntry` (`:243-257`) + `diff-modal.js` clobber flag (`:267-330`). Library→World:
`refresh-to-world` now covers item/way/area/character (`routes/library_ops.py:750-769`).
Remaining: `break-template-link` endpoint + inspector UI (task-289), and variants /
override tracking (task-290, not started — `template_ref` is absent from the code).

## Goal

Make template linking a coherent, safe system in BOTH directions across all node
types (item, way, area, character):

- **Library → World** (task-289/290): link a node to a template, refresh template
  changes down, break the link; variants + override protection (task-290).
- **World → Library** (this task's new half): push a world copy up to the library
  WITHOUT clobbering richer template data with bare world instances.

## Why

The two directions were built independently and behave inconsistently:

- `refresh-to-world` (Library→World) used to support only **items and ways**
  (the old `routes/library_routes.py:482` returned 400 for areas/characters); it now
  covers all four types (`routes/library_ops.py:765-768`).
- The sync modal (World→Library) originally did a **full overwrite**: a bare world
  copy (empty description, no triggers) nuked the curated template — the `brass_key`
  incident. Fixed 2026-08-20 with a merge guard (empty world values no longer erase
  library data) + diff-modal clobber protection.
- task-289/290 describe the Library→World half; nothing tracks the World→Library half.

## Design Decisions

1. **Two directions, one mental model**: library = templates; world = unique linked
   instances. `library_id` (or task-290's `template_ref`) is the link in both directions.
2. **World→Library safety rules** (already implemented, must be preserved):
   - `_silentSave` merges: non-empty world values win; empty world values ("" / [] / {})
     never erase library data (world-sync.js `_mergeEntry`).
   - Diff modal: a field where the library has data but the world copy is empty shows
     as a guarded "clobber" — not pre-checked, amber ⚠, hover warning
     (diff-modal.js `clobber` flag).
3. **Library→World generalization** (pull from 289/290): extend `refresh-to-world`
   to areas and characters; add `break-template-link`; per-type mutable-field whitelist.
4. **Override tracking (290)** is the author-visible layer of the same "don't clobber"
   rule: `template_ref.overrides` protects fields from sync in Library→World, just as
   the merge guard protects them in World→Library.

## Scope

World→Library (implemented 2026-08-20 — verify + keep):
- world-sync.js `_mergeEntry` + `_isEmpty` guard on bulk sync
- diff-modal.js clobber detection / uncheck-by-default on empty-world-over-library

Library→World (from 289/290):
- ~~extend `refresh-to-world` to area + character~~ — done (`routes/library_ops.py:765-768`)
- `break-template-link` endpoint + inspector UI — **not done** (no code matches)
- per-type mutable-field whitelist — **not done** (inline per `_refresh_*`; no `engine/sync.py`)
- variants + override tracking, `template_ref` migration (task-290) — **not started**

## Verification

- Unit tests: both sync directions; empty-world-never-clobbers; refresh works on all
  4 types; break-link preserves node data; overrides skip on sync.
- E2E: sync a bare world item to a rich template → template fields survive; refresh
  a linked area/character from template → updates apply.



---

## inprogress/graph/task-461-nl-editor-validation-gate-and-apply-time-property-diff.md

---
type: task
status: inprogress
area: graph
priority: medium
---

# task-461: NL editor validation gate and apply-time property diff

**Filed:** 2026-09-22
**Related:** task-438, task-422, task-458

## Goal

Validate staged ops before Apply (known fields and registered trait ids, edge endpoints exist, id casing, no duplicate area names) and show a property-level diff per op instead of generic ghost nodes, so a misspelled trait or wrong shape cannot silently no-op. Add per-op undo for an applied batch. Shares the validator with task-438 phase 5.

## Acceptance

- [x] Shared validator `engine/nl_editor_validation.py:validate_ops` — one
      definition used by the batch route and the pre-Apply endpoint. Checks:
      op structure/type, node existence (tracking creates/deletes as the batch
      replays), unknown trait ids (error), unknown item actions (warning), id
      casing (warning), duplicate area display names (warning), dangling
      attach/detach endpoints, bulk selector/patch emptiness, library registry
      + id slug + mature gate.
- [x] `POST /api/graph/batch/validate` dry-run endpoint (`handle_graph_validate`).
- [x] Apply gate: `handle_graph_batch` validates first; with
      `strict_validation: true` it returns 422 and applies nothing when there
      are errors. Other callers keep the previous permissive behaviour and just
      receive `validation` as advisory data.
- [x] The NL editor sends `strict_validation`, keeps every op staged on a 422,
      and shows the findings (`staging.js`, `index.js`,
      `ui.js:showValidationIssues`).
- [x] Property-level diff per op: `static/js/nl-editor/diff.js`
      (`opDiff`/`diffPairs`/`summaryLines`) renders "traits.dark_vision: — → true"
      under each staged row, flags a no-op patch, and lists each bulk target.
- [x] Tests: `tests/test_nl_editor_validation.py` (9) and
      `tools/unit/test_nl_editor_diff.js` (8).

## Remaining

- [ ] Per-op undo for an applied batch (the batch still undoes as ONE snapshot;
      undoing a single applied op is not yet offered).




---

## inprogress/refactor/task-446-id-first-node-identity.md

---
type: task
status: inprogress
area: refactor
priority: high
---

# task-446: id-first node identity — data by id, names resolve at the boundary

**Filed:** 2026-09-22 (from task-357 design review).

## Principle

Backend data operations on nodes are keyed by **id**. Names are user-facing: a
matcher resolves user text ("steal from Jon", "take the knife") to an id, and
the id is what every data operation consumes. Ids are stable across renames, so a
rename never dangles a reference and two nodes may share a display name.

`engine/matching.py` is the name→id seam. Storage must not use names as identity.

## Measured blast radius (2026-09-22, non-test)

| Violation | Sites |
|---|---|
| `players` dict keyed by name | 24 direct `players[...]` + 69 `.items()/.values()/.keys()` |
| `Player.node_id_for(name)` anchor id from name | 192 (`node_id_for`/`player_node_id`) |
| `relationships` keyed by name | 6 |
| `current_area` stores an area **name** | 445 |
| `find_item_node` / exit resolution by name as identity | small (mostly `matching.py`) |

## Slices

### Slice A — player identity (points 1, 2, 3) *in progress*

- `Player.uid` is the stable identity (existing opaque `Player.id`, task-316).
- `PlayerManager.players` becomes **id-keyed**, with a name index. Duplicate
  display names are allowed; ambiguous name lookups return candidates and the
  resolver picks.
- Anchor node ids stay `player_<slug(name)>` for a **unique** name (saves and
  tests keep working) and get a stable suffix from the uid when the name is
  duplicated (`player_jon__<uid>`).
- Save format: `players` written keyed by id with `name` inside; **read** accepts
  legacy name-keyed files (key falls back to the payload's `name`).
- Migrate the ~93 access sites: iteration for display uses `p.name`; identity
  uses the key/uid.
- Relationship keys move to uid (point 3) with name resolution for prompts.### Slice B — location by id (point 4) *last, behind a compat accessor*

- `current_area` holds an area id; `Player.area_name`/resolver provide the name
  at the display/prompt boundary. 445 sites, so a compatibility accessor first,
  then mechanical migration.
- **Already tracked as task-439** ("Canonical area identity in the save and in
  area lookups") — do that work there, not here. 439 is the prerequisite for
  scopes/decomposition.

### Slice C — resolver boundary (point 5)

- Formalize `matching.py` as the only name→id seam; no engine code consumes a
  name as a key. Mostly a cleanup once A/B land.

## Why this order

A is the core of the stated goal (500 "Jon"s; template population). B is the
widest change, so it goes last. C is cleanup. A+B+C in one pass would leave the
tree half-migrated and break the suite; each slice must keep the suite green.

## Compatibility / migration rules

- Never break a name-keyed save: read old, write new.
- A unique name keeps its derived anchor id (no churn on existing worlds).
- `players[name]` continues to work for a unique name; ambiguous access logs /
  returns the primary candidate and the resolver surfaces the alternatives.
- Rename must remain reference-safe: only the display name changes.

## Acceptance

- Two characters named "Jon" can coexist end-to-end (create, save, load, act,
  be targeted unambiguously via `matching`).
- `players` storage and `node_id_for` are id-keyed; no data operation keys on a
  name.
- Old saves load unchanged; new saves round-trip.
- Full test suite green apart from the known pre-existing failures.

## Implemented — Slice A, steps 1–3 (2026-09-22)

Functional duplicate display names, non-breaking:

- `PlayerManager` (`engine/player_manager.py`): a name is now a **lookup key**,
  not the identity. `_unique_key` gives a duplicate a stable id-derived registry
  key (`Jon` → `Jon__<id6>`) while `p.name` stays free; `add_player` gives such a
  player a unique anchor (`player_Jon__<id6>`). Unique names keep the exact legacy
  key and anchor, so existing worlds/saves do not churn. Added `uid_of`,
  `get_by_id`, `find_by_name`, `resolve`, `reindex`, `relationship_key`,
  `display_name_of`; `get_player` / `get_player_node_id` / `set_active_player`
  accept key, name or id; `get_players_in_area` / `get_all_*_players` report
  `p.name` (display). Registered players are given a `player_manager`
  back-reference so identity can be resolved from anywhere.
- `virtual_world_engine.py`: `player_node_id` / `_player_node_id` delegate to
  `PlayerManager.get_player_node_id`, so a registry key resolves to its own anchor.
- `engine/serialization.py`: `_deserialize_player` restores `p.name` from the
  payload (fixes a latent bug that would set the display name to the key), and
  `load_from_dict` calls `reindex()` so duplicate keys get unique anchors.
- `engine/matching.py` (`_match_character_name`): name tiers compare the
  **display** name, so two characters named "Jon" return an **ambiguous**
  candidate list (keys) instead of silently resolving to the first.
- **Relationships keyed by identity (point 3).** `engine/relationships.py` gains
  `resolve_key` / `display_name` / `get_relationship`; every writer and reader
  (`ensure_relationship`, `apply_relationship_delta`, `apply_symmetric_delta`,
  `describe`, and the migrated reads in `derive`, `area_description`,
  `background_social`, `grapple`, `pleasure_actions`, `movement`, `player_ops`)
  resolves the other party to the unique key. Records carry a denormalized
  `name` for prose/prompts; `Player._rel_key` backs `has_met` / `knows_name` /
  `learn_name` / `register_first_meeting`; `_relationships_to_dict` emits display
  names. For a unique name the key IS the name, so nothing churns.
- **Display-name usage in iteration (step 4).** Label sites that printed or
  matched the loop key as a name now use the display name: `narration.py`
  character listing, `logging_events.py` debug export, `routes/settings.py`
  player dump, `routes/player_ops.py` player lists + target candidates + learned
  list, `engine/autocomplete.py` character suggestions, `engine/movement.py`
  feared-room check, `engine/effects.py` / `engine/triggers/evaluation.py`
  target resolution. Sites where the key is genuinely an identity (edge/condition
  keys, notification keys, counts, hash keys) were left as-is.
- Tests: `tests/test_player_identity.py` (7) — unique-name compatibility,
  duplicate coexistence, save/load round-trip, resolve by name/key/id, in-area
  listing, duplicate-target ambiguity, and **per-identity relationships** (two
  "Jon"s keep separate records; a rename does not drop the record).
- Regression: full suite unchanged (same 60 pre-existing MCP/social/tick
  failures; no new ones).

### Remaining in Slice A

- Duplicate-target disambiguation UX → **task-448**.
- Character nicknames/alias authoring + persistence → **task-447**.
- Grapple identity mixup (functional) + log-string label leaks → **task-449**.
- Add duplicate-name round-trip coverage at the route/autosave layer (small,
  folded into a later pass).
- `node_id_for` is still name-derived for the unique case by design (compat);
  a pure-uid anchor migration is a later step.
- Slice B (location by id) is **task-439**, not this task.




---

## inprogress/world/task-397-world-scope-hierarchy-and-projection.md

---
type: task
status: inprogress
area: world
priority: high
---

# task-397: World scopes, hierarchy manifest, and server graph projection

**Filed:** 2026-09-08  
**Prototype:** Millbrook Falls / The Pines

## Goal

Add a hierarchy *over* the existing area/way/item graph so the editor and
runtime can address a world, settlement, building, or room group without
inventing a second spatial model. A scope is a durable grouping and load/view
boundary; its leaf areas remain normal `area` nodes and all existing movement,
trigger, item, and character rules continue to use them.

The first deliverable is a scoped API response. It must not send every node and
edge to the browser merely to hide them client-side.

## Why this is needed

`GraphNetwork.loadGraphData()` currently fetches all graph nodes and all graph
edges, then `GraphProjector` hides most of them locally. The inhabited/items
toggles are useful presentation controls but cannot make a million-node world
cheap. `WorldGraph` is also one in-memory node dict plus one edge list, so
scope metadata must be introduced before chunk persistence can be added safely.

## Data model (v1)

Persist a top-level `world_scopes` manifest, separate from graph nodes:

```json
{
  "millbrook_falls": {
    "id": "millbrook_falls",
    "kind": "settlement",
    "name": "Millbrook Falls",
    "parent_id": null,
    "children": ["downtown", "the_pines"],
    "state": "materialized",
    "generation": null
  },
  "the_pines": {
    "id": "the_pines",
    "kind": "building",
    "name": "The Pines Apartment Complex",
    "parent_id": "downtown",
    "children": ["pines_floor_1", "pines_floor_2", "pines_floor_3"],
    "state": "materialized"
  }
}
```

Each materialized area gains `properties.world_scope_id`. Scope children may
be other scopes, or the manifest may list `area_ids` at the leaf. Scope records
may exist with `state: "unmade"`; no graph nodes are required until task-398
generates them.

Do not add fake `area` nodes for continents, buildings, or floors. A character
always remains in a real area, as today.

## API and editor

1. Add serialization/load support for `world_scopes` on `VirtualWorld`.
2. Add a read-only `GET /api/world/scopes/<scope_id>` endpoint returning only:
   - direct child scope cards: id, name, kind, state, area/character/item
     counts, and whether any character is present;
   - direct leaf area summaries when the selected scope is a leaf;
   - boundary-way summaries, never every contained item.
3. Add `GET /api/world/scopes/<scope_id>/graph` with explicit `depth` and
   `include_items` limits. It is the future replacement for full-graph editor
   loading; v1 may read the current in-memory graph but must return only the
   requested projection.
4. Add a scope breadcrumb/tree UI above or beside the graph. Clicking a card
   changes the requested scope. Existing item reveal and inhabited filters keep
   working inside the returned projection.
5. An unmade scope card shows `Generate` only when it has a generation recipe
   (task-398); it must not fabricate nodes merely by being rendered.

## Pines acceptance

- The root view shows `Millbrook Falls`, `Downtown District`, and `The Pines`.
- Opening The Pines shows floors/apartments or the existing leaf areas, without
  dumping unrelated Pines items into the graph canvas.
- `Apartment 3B` can appear as an unmade scope even before it has areas.
- Existing `pines.json` loads unchanged when it has no manifest.
- Save/load preserves the manifest and every existing test scenario remains
  backward-compatible.

## Non-goals

- No physical graph unloading yet (task-401).
- No procedural generation here (task-398).
- No change to `simple_npc`, `autonomy`, action commands, or turn ordering.

## Existing work and risks

- task-303 and task-319 are client-side visibility filters, not server-side
  scale solutions. Preserve their UX but do not extend their all-node dataset
  approach.
- task-357 is a useful raw graph-bundle/import design, but its current import
  model is not a scope manifest or streaming model. Do not couple this task to
  structure import.

## Verification

- Pytest serialization fixture: absent, materialized, and unmade manifests.
- Route tests prove an endpoint response excludes nodes outside the requested
  scope.
- Browser test: scope navigation preserves current camera/filter behavior.

## Progress — 2026-09-23 (backend slice)

Landed (uncommitted):

- `VirtualWorld.world_scopes` manifest attribute (`virtual_world_engine.py`).
- Serialization round-trip in `engine/serialization.py` (`_serialize_world`
  writes `world_scopes`; `load_from_dict` restores a dict or `{}`), so
  `to_scenario_dict` carries it and legacy scenarios without a manifest are
  unchanged.
- `engine/world_scopes.py` — pure helpers: `normalise_manifest`,
  `root_scope_ids`, `direct_child_ids`, `area_ids_in_scope` (recursive),
  `scope_summary` (area/character/item counts, state, child ids),
  `boundary_ways`, and `project(manifest, graph, players, scope_id, depth,
  include_items)`.
- `routes/world_scopes.py` + `routes/world_scopes_ops.py`:
  - `GET /api/world/scopes` — top-level scope cards.
  - `GET /api/world/scopes/<scope_id>` — child scope cards, or leaf area
    summaries + boundary ways.
  - `GET /api/world/scopes/<scope_id>/graph?depth=&include_items=` — projection;
    items/edges included only when requested.
- `tests/test_world_scopes.py` (12) — recursion, cardinality, boundary ways,
  leaf vs building projections, manifest round-trip through `/api/load`, and
  backward compatibility with no manifest. Full suite: 3451 passed, 6 known
  pre-existing failures.

Still open in this task:

- Scope breadcrumb/tree UI above the graph (work plan step 4) and the
  unmade-scope `Generate` affordance (step 5, depends on task-398).
- `task-398` recipe/generation flow over `world_scopes`.


