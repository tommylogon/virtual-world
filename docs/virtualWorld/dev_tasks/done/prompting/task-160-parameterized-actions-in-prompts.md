---
id: 160
title: Parameterized Actions in Agent Prompts
status: done
priority: medium
created: 2026-08-02
tags: [prompting, agent-engine, actions]
---

# Parameterized Actions in Agent Prompts

## Summary

Enhance the agent prompts so the LLM emits parameterized, structured action commands instead of loose natural-language actions — e.g. `use item: key, target: door1, speech: "lets see if this works", emote: "i turn the key and..."`.

## Problem

The agent emits a free-text `action` field in its JSON (prompt-builder.js:722,786). The command parser then has to guess intent from arbitrary phrasing. Parameterized actions would make agent output deterministic, testable, and far less likely to fail.

## Implementation

### Agent action schema (folded in from DeepSeek parameterized-JSON proposal)

The agent's existing `_parseDecisionWithSpeech` output already has `action`/`speech`/`emote`
fields. This task makes the `action` field **structured** with explicit `item`/`target`
parameters instead of free-text like `use key on front door`:

```json
{
  "action": "use_on",
  "item": "rusty_key",
  "target": "front_door",
  "speech": "Please fit. Please fit.",
  "emote": "slides the key into the lock",
  "modifiers": { "stealth": "quiet", "intensity": 8, "urgency": "high" }
}
```

Core fields:

| Field | Meaning | Applies to |
|---|---|---|
| `action` | verb enum (see below) | all |
| `item` | the item being used/placed | `use`, `use_on`, `place` |
| `target` | the thing acted on / spoken to | `use_on`, `take`, `place`, `go`, `whisper` |
| `speech` | dialogue (may combine with any action) | optional |
| `emote` | physical description (may combine) | optional |
| `modifiers` | `intensity 1-10`, `stealth loud/normal/quiet`, `speed`, `tone`, `body_language` | optional, v2 |

Verb enum to advertise in the prompt: `use`, `use_on`, `take`, `drop`, `place`, `go`,
`examine`, `say`, `whisper`, `shout`, `scream`, `attack`, `open`, `close`, `speak`,
`emote`, `read`, `search`, `look`.

### Prompt guidance

Update prompt-builder.js decision/reaction prompts to instruct the agent to structure
actions with the fields above, and show 3-4 worked examples in the "allowed actions"
block:

- `use` alone: `{"action":"use","item":"candle"}` → toggleable items light up on their own
- `use_on`: `{"action":"use_on","item":"create flame","target":"dry leaves"}` → target is
  the **full multi-word name**, never split
- `take`/`place`: `{"action":"place","item":"tiny_key","target":"desk_drawer"}`
- speech-only: `{"action":"whisper","target":"Sammy","speech":"..."}`

Why this matters: item/target names in this world are multi-word (`Short Forest Cape`,
`Dried Flower Crown (Crushed)`, `Stovepipe Leather Boots (Pair)`). Structured fields
eliminate the parser ambiguity that caused `use create flame on dried flower crown` to
*inscribe* text (see `task-181-command-parser-multiwindow-targets`). The `use` vs `use_on`
distinction also fixes the Create Flame case — it should be `use` alone, not
`use_on <something>`.

### Agent engine

- Normalize emitted `action` strings into the parameterized form before sending to
  `/api/action`: if the model emits structured fields, serialize to
  `use_on <item> on <target>` (item + target joined as full names — no truncation);
  keep the existing free-text fallback for unsupported commands.
- The verb enum must stay in sync with `_validateAction`'s whitelist
  (`agent-engine.js:617`) and the COMMANDS table — one source of truth (see
  `task-186-agent-validation-and-feedback`).
- Optionally: add a validation step in agent-engine.js that flags malformed actions
  for retry (ties into task-150 auto-retry).

### Backend

- `routes/action.py` / `tokenize_command`: the free-text parser still exists for human
  players — the structured agent path serializes to full-remainder targets, so no new
  endpoint is required in v1. Verify `use_on <item> on <full target>` resolves via the
  (already-fixed) name matcher (`task-183-name-matching-aliases`).
- `modifiers` are accepted but **ignored by the engine in v1** — keep them in the prompt
  for future use (action economy task-132, stealth) rather than implementing now.

## Files to Modify

1. `static/js/agent/prompt-builder.js` — prompt instructions + action examples
2. `static/js/agent-engine.js` — action normalization/validation
3. `routes/action.py` — verify all parameterized forms parse correctly

## Testing

- [x] Agent emits structured `action`/`item`/`target` fields for use/target cases
- [x] `use_on <item> on <multi-word target>` executes correctly (no "invalid action", no inscribe side-effect)
- [x] `use` alone toggles light sources / spawns items (Create Flame → lit ember)
- [x] Speech and emote from action params are broadcast correctly (volume = whisper/say/shout/scream)
- [x] Fallback to free-text still works (legacy `say`/`whisper` keys + plain action strings)
- [x] `_validateAction` whitelist and verb enum match 1:1
- [x] Spatial placement + give covered by tests (`tests/test_item_actions.py`, 9 new)

## Implementation Notes (completed 2026-08-04)

### Backend
- `engine/item_actions.py` — new `place_item()` (writes EDGE_ON/UNDER/BEHIND/BESIDE/AT/IN
  with capacity check for `in`) and `give_item()` (moves carrying edge to same-area target).
  `take_item()` now also clears spatial edges when grabbing an item off a surface.
- `virtual_world_engine.py` — delegators `place_item()`/`give_item()`.
- `routes/action.py` — `put <item> <prep> <target>` (on/under/beside/behind/at/in),
  `place <item> <prep> <target>`, and `give <item> to <character>`.
- **Reachability surprise**: `get_edges_for_target(area, EDGE_IN)` already expands spatial
  edges (graph.py:98-103), so items placed on/under surfaces are automatically findable by
  `take_item` — no reachability code change needed beyond a clarifying comment in
  `matching.py:_is_item_reachable`.

### Frontend
- `static/js/agent-engine.js` — `_normalizeStructuredAction()` converts `{action, item,
  target, relation}` into a command string (e.g. `use rusty_key on front_door`,
  `put ink_pen on table`, `give rusty_key to Lyrie`). `_extractSpeechVolume()` reads the
  unified `speech` + `volume` fields (legacy keys still accepted). `_validateAction`
  whitelist gained `place`, `give`, `hand`. `_extractMemory()` parses `tags`.
- `static/js/agent/prompt-builder.js` — ACTIONS table rewritten as structured-object
  examples (full verb list restored: equip/wear, unequip/remove, fumble, close, stats +
  put/place/give/steal). `buildReactionPrompt`/`buildResultReactionPrompt` emit the unified
  schema with `volume`-is-the-key guidance and a `memory` field (react prompt + non-reactive).
- `static/js/agent/memory-manager.js` — `storeMemory()` passes `tags` to the backend and
  auto-registers new single-word tags in the id-keyed tag library (dedupes naturally).
- `static/js/inspector/memory-view.js` — memory editor uses the shared `TagMultiselect`
  component (searchable + create-on-the-fly); memory list shows importance-colored border,
  SEED badge for `source: manual`, and tag chips.

### Tests
- `tests/test_item_actions.py` — 9 new: place on/under/in, non-container `in` rejection,
  missing target, give success/area check, spatial reachability.
- Full suite: 481 passed, 1 skipped (472 → 481).

## Related

- [[todo/prompting/task-150-invalid-action-auto-retry|task-150: Invalid action auto-retry]]
- [[todo/gameplay/task-181-command-parser-multiwindow-targets|Command parser: multi-word targets]] (parser fix this builds on)
- [[todo/prompting/task-186-agent-validation-and-feedback|Agent validation & feedback]] (verb whitelist sync, no silent drops)
- [[todo/items/task-184-stove-implementation|Stove implementation]] — `use kindling on stove` needs structured target to survive
- [[todo/environment/task-174-fire-mechanic-heat-source|Fire mechanic]] — Create Flame should be `use` alone

## Design Decisions (confirmed 2026-08-04)

While working task-178 (unified memory) it became clear this task and the speech-volume
system overlap. **Decision: unify speech volume INTO the action schema** — one structured
action object, no separate `say`/`whisper`/`shout`/`scream` top-level keys.

### Unified schema (no `modifiers`)

```json
{
  "inner_monologue": "...",
  "action": "use_on",
  "item": "rusty_key",
  "target": "front_door",
  "speech": "Please fit, please fit.",
  "volume": "whisper",
  "emote": "slides the key into the lock",
  "memory": { "text": "...", "importance": 7, "tags": ["door"] }
}
```

- `volume`: `whisper | say | shout | scream` (default `say`); `speak`/`talk` normalize → `say`.
  **The volume word is the JSON KEY name `volume`, never a value inside `speech`** — fixes
  the `{"say":"whisper psst"}` bug structurally (prompt explicitly shows this).
- `modifiers` object: **rejected** for now (stealth/intensity/urgency). Keep schema lean;
  add when task-132/stealth has something to act on it.
- `memory`: only in the **react prompt** (`buildResultReactionPrompt`), and in
  `buildReactionPrompt` only when `includeMemory=true` (non-reactive single-step mode).
  Observe/decide never carry memory. Tags: single-word lowercase; auto-added to the
  tag library (id-keyed → dedupes naturally).
- Speech-only turns omit `action` and provide `speech` + `volume`. No whisper-as-verb pathway.

### Per-prompt field matrix

| Prompt | inner_monologue | action | item/target | speech/volume | emote | memory |
|---|---|---|---|---|---|---|
| `buildReactionPrompt` (reactive think-decide) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `buildReactionPrompt` (non-reactive, includeMemory) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `buildResultReactionPrompt` (react) | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |

`buildObservationPrompt`/`buildDecisionPrompt` are dead exports — NOT updated.

### Spatial placement & give (added 2026-08-04)

The scenario data (e.g. `data/scenarios/labs.json`) already models furniture with spatial
edges: `on` (ink pen on table), `under` (rug under table), `behind` (painting behind table),
`beside` (toy box beside table), `in` (soldiers in box). The engine DEFINES these edge types
(`graph.py:218-233`) and READS them when examining a surface (`item_actions.py:190-215`), but
there is NO way to place an item onto a surface or take an item OFF one — `take_item`
reachability (`matching.py:386-411`) only handles area-direct / inventory / `in`-containers.

**Decision: make furniture spatial relations a first-class placement mechanic**, unified into
the same structured action schema:

```json
{"action":"place","item":"ink_pen","target":"table","relation":"on"}
{"action":"place","item":"rug","target":"table","relation":"under"}
{"action":"place","item":"key","target":"box","relation":"in"}
{"action":"give","item":"key","target":"Lyrie"}
```

- **`place` / `put`** — move a carried item onto/under/beside/behind/at a target surface in
  the same area. Verb mapping: `place` and `put` are synonyms. Relation inferred from the
  preposition in the free-text form (`put X on Y`, `put X under Y`, `put X beside Y`,
  `put X behind Y`, `put X at Y`, `put X in Y`) or the `relation` field in structured form.
- **`give`** — hand a carried item to another character in the same area (moves the
  `carrying` edge from player to target).
- **Backend**: `engine/item_actions.py` gains `place_item_on` (writes `EDGE_ON`/`EDGE_UNDER`/
  `EDGE_BEHIND`/`EDGE_BESIDE`/`EDGE_AT`/`EDGE_IN`) and `give_item` (moves carrying edge).
  `routes/action.py` parses the free-text command forms for human players.
- **Reachability**: `matching._is_item_reachable` and `take_item` container scan extended to
  treat spatial edges as findable surfaces (an item `on`/`under`/`beside`/`behind` a surface
  is reachable once the surface is in the area — visibility via `examine`).
- **Prompts**: ACTIONS table advertises `put`/`place` (with `relation`) and `give`.

### Prompt ACTIONS table — restore dropped verbs (added 2026-08-04)

The rework accidentally dropped valid verbs from the ACTIONS table that `_validateAction` and
the normalizer still support. Restore: `equip`/`wear`, `unequip`/`remove`, `fumble`, and give
`close` + `stats` their own example rows (they were folded into combined rows with only one
example each). Keep the table lean but complete — the LLM can only emit verbs it sees.
