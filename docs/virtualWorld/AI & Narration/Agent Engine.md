# Agent Engine

The Agent Engine drives LLM-powered character agents — autonomous NPCs that observe the world, think, speak, and act through the same `/api/action` endpoint as human players.

## Architecture

The engine lives in `static/js/agent-engine.js` as the `AgentEngine` class (`window.VW.agent`, global `agent`). It coordinates several sub-modules:

| Module | File | Role |
|--------|------|------|
| `AgentEngine` | `agent-engine.js` | Main loop, turn orchestration, action normalization |
| `PromptBuilder` | `agent/prompt-builder/` (index) | Pure functions for building LLM prompts (split into submodules — see below) |
| `TurnQueue` | `agent/turn-queue.js` | Turn ordering and advancement |
| `AgentMemory` | `agent/memory-manager.js` | Memory storage + reflection (backend `Player.memories`) |
| `PlanManager` | `agent/plan-manager.js` | Multi-step plan generation |
| `RateLimiter` | `agent/rate-limiter.js` | API rate limiting |
| `ContextWindowManager` | `static/js/context-window.js` | Token budget and context pruning |
| `ResponseParser` | `agent/response-parser.js` | Parse/validate LLM JSON out, surface parse errors |
| `ActionNormalizer` | `agent/action-normalizer.js` | Normalize structured actions into `/api/action` commands |
| `ThreatDetector` | `agent/threat-detector.js` | Flag nearby threats for replanning |
| `HumanTurnComposer` | `agent/human-turn-composer.js` | Human-turn (composer) drive path |
| `TurnSceneView` | `agent/turn-scene-view.js` | Render current turn scene for the event stream |

## Agent Loop

### Step Cycle (`step()`)

Each agent step processes one character's turn:

1. **Rate limit check** — waits if RPM limit is exceeded
2. **Turn queue** — determines whose turn it is (turn-based mode)
3. **Simple NPC check** — skips LLM work for `simple_npc` characters (they act via backend `tick_turn` / `process_simple_npcs`). Simple NPCs are still **in the turn queue**; their turn just advances without an LLM call. NPC actions are logged to the event stream via `record_turn_event()`.
4. **Rest/Sleep check** — skips if character is resting or unconscious
5. **Reflection** — every 5 turns, triggers memory summarization (reactive mode)
6. **Threat/needs-aware replan** — before think-decide, `PlanTracker.shouldReplan()` checks for new threats, blocked paths, or vitals crossing a critical threshold; if needed, regenerates the plan via `PlanManager.generate()`
7. **Reactive mode** (2 LLM calls — the conversation-loop design, task-176):
   - **Think-decide** (`buildReactionPrompt`): one call produces inner monologue + structured action + speech/volume + emote. This is a single combined call (no separate observe/decide prompts — those exports are dead).
   - **Act**: execute the normalized action via `ApiClient.action()`, optional AI narration, then the emote (gated on the action not failing or being rejected). Invalid verbs become a natural in-world rejection ("You try to climb the ceiling, but you can't do that") that flows into the react phase instead of vanishing silently.
   - **React** (`buildResultReactionPrompt`): character reacts to the action outcome with inner monologue, speech/volume, emote, and the **LLM-generated memory** field. The prompt makes clear only a moment has passed since the character's own action — others haven't had time to respond, so silence isn't a snub.
8. **Non-reactive mode** (1 LLM call): single `buildReactionPrompt` with `includeMemory=true` produces everything in one response; action executed asynchronously.
9. **Turn advancement** — advances the turn queue

### Conversation history is retained across turns

`characterHistories[charName]` (agent-engine.js) persists per character and is **not** reset
each turn — the think-decide and react phases both append to the same array. This prevents the
agent from contradicting itself between phases (e.g. changing a favorite color). The
`ContextWindowManager` prunes when over 30 messages / 9500 tokens (keeping system + last ~18
messages). History is cleared only on `start()`/`reset()`.

## Character Control Modes & Autonomy (task-244)

Every character resolves to a control mode via `events.getControlMode(charName)`
(`event-stream.js`):

| Mode | Condition | Who drives |
|------|-----------|------------|
| `'npc'` | `player.simple_npc` | Backend `tick_turn` — scripted behaviors, no LLM |
| `'human'` | `player.autonomy === false` | The human, via commands; the engine **skips their turn** |
| `'llm'` | default | Agent engine — full autonomous LLM turns |

- The `autonomy` flag is **persisted on the player** in the backend graph, so a human stays
  human across reloads. Toggle it from the agent inspector.
- A human-mode turn pauses only that character's progression (agent-engine.js ~301) — the rest
  of the roster keeps cycling when it's their turn.

## Per-Turn State Tracking & Instincts

- **Character state** — `events.getCharacterState(charName)` tracks `lastThought`,
  `lastSpeech`, `lastAction`, `actionHistory` (last 20 with tick + result), `currentArea`,
  `lastActionResult`. Consumers: plan manager (`lastThought`), prompt memory context
  (`actionHistory` → recent-actions block), agent lens, inspector.
- **Needs/threat-driven replanning (task-92)** — `PlanTracker.shouldReplan()`
  (`agent/plan-tracker.js`) regenerates the plan when vitals **cross** a critical threshold or
  a new threat appears, re-nudging at most every 5 turns to avoid churn.
- **Closeness gates behavior (task-94)** — `relationshipGuidance(closeness)`
  (`prompt-builder/character-state.js`) turns each relationship score into a behavioral
  directive on the People-here line ("you want them gone; refuse help…" at ≤ −50).
- **Speech salience + conversation instinct** — `prompt-builder/conversation-context.js`
  labels heard lines as *addressed to you* vs *overheard* (salience), and
  `buildConversationInstinct()` nudges characters to join ongoing conversations they're part of.
- **Parse-error inspection (task-238)** — malformed LLM responses are stored in an EventBus
  ring buffer (`events.logParseError`, last 20) and surface as clickable bubbles that expand
  the raw response, so bad outputs are debuggable from the stream itself.

## Structured Actions (task-160)

The LLM emits a **structured action object** instead of free-text commands:

```json
{
  "inner_monologue": "...",
  "action": "use_on",
  "item": "rusty_key",
  "target": "front_door",
  "speech": "Please fit, please fit.",
  "volume": "whisper",
  "emote": "slides the key into the lock"
}
```

- **`volume`** is `whisper | say | shout | scream` (default `say`). The volume word is the
  **key**, never a value inside speech — `{"speech":"whisper psst"}` is explicitly wrong in
  the prompt. `speak`/`talk` normalize → `say`. Legacy top-level `say`/`whisper` keys still
  work as a fallback.
- **`_normalizeStructuredAction()`** (`agent-engine.js`) converts `{action, item, target,
  relation}` into a command string for `/api/action`:
  - `use rusty_key on front_door` (multi-word names stay whole)
  - `use create flame` (use ALONE for self-use items)
  - `put ink_pen on table` (spatial placement, `relation` = on/under/beside/behind/at/in)
  - `give rusty_key to Lyrie` (hand to a same-area character)
  - `steal key from Miki`, `go north`, `rest 30`, etc.
  - Free-text fallback for anything unsupported / legacy plain strings
- **`_validateAction()`** whitelist is synced 1:1 with the verbs the normalizer can emit
  (includes `place`, `give`, `hand`). Rejections are surfaced via `_surfaceRejectedAction()`
  into `config.lastActionResult` (shown as `=== LAST ACTION RESULT ===` next turn) — never a
  stored memory.

### Action verbs the LLM is told about (ACTIONS table)

`go, dash, crawl, climb, jump, open, close, take, drop, use, use_on, put/place, give, steal,
examine, read/search, wear/equip, remove/unequip, attack, grab, escape/struggle, rest, wait,
inventory, stats, look, fumble, relieve` — plus ghost-only `manifest`/`vanish`.

- `crawl <dir>` / `climb <dir>` / `jump <dir>` are the passage-movement verbs (task-187):
  `go` auto-crawls tight (one tier over `max_size`) and crawl-only ways; climb/jump ways need
  the matching verb and roll an Athletics check that can fail.
- `grab <character>` is a grapple attempt (falls back to `take` for items); `escape`/`struggle`
  break a grapple with a STR save (task-4).
- The player-state block injects **size context** when a `size_*` trait is present ("You are
  huge. Some passages are too tight for you...") via `buildSizeContext()` in `agent/prompt-builder/`.

## Prompt Building

All prompt construction lives in `static/js/agent/prompt-builder/` (pure functions, no side effects). Submodules: `system-prompt.js`, `turn-prompts.js`, `character-state.js`, `conversation-context.js`, `memory-context.js`, `context-sections.js`, `schema-fragments.js`, `helpers.js`, `room-context.js`, `contextual-actions.js`.

### System Prompt (`buildCharacterSystemPrompt()`)

- World lore (common knowledge shared by all agents)
- ACTIONS table (structured-object examples, one action per response)
- Rules (multi-word names stay whole, `use` vs `use_on`, put needs a `relation`, give/steal need a same-area target)
- Ghost/death instructions when applicable
- Items vs flavor distinction

**Character identity** ("You are X. Personality: Y.") is injected as the first line of every user message via `buildCharacterPreamble()`.

### Prompt Templates

All templates share the same **user-message layout** (assembled from `buildRoomContextParts()` + `assembleMessageHead()`, reordered 2026-08-18):

```text
[Tick N]
You are X. Personality: ...
=== YOUR STATE ===        ← vitals, emotion, insanity, traits, size, activity, grappled, ghost/dead
=== I REMEMBER ===        ← own block, right after YOUR STATE
Your appearance / Carrying
Room description → paths → items → People here (with inline relationship labels)
=== AVAILABLE ACTIONS ===
=== WITNESSED ===
[=== YOUR PLAN ===]
<phase section>
```

- **Relationships are NOT in `=== YOUR STATE ===`** — each "People here" line carries an inline
  type label when known (`jake halloway - a close friend - (awake)`), no scores.
- **Memory context is its own `=== I REMEMBER ===` block** right after YOUR STATE, not a state
  fragment.
- The react template keeps its minimal `[Tick N] You are still in ...` context, then
  `=== YOUR STATE ===` → `=== I REMEMBER ===` → `=== WHAT HAPPENED ===`.

| Template | Phase | Memory field | Output |
|----------|-------|--------------|--------|
| `buildReactionPrompt` | Think-decide / combined | ❌ (reactive), ✅ (non-reactive) | `{"inner_monologue","action","item","target","speech","volume","emote"[,"memory"]}` |
| `buildResultReactionPrompt` | React | ✅ | `{"inner_monologue","speech","volume","emote","memory":{"text","importance","tags"}}` |

`buildObservationPrompt`/`buildDecisionPrompt` are **dead exports** — defined and exported but never called. Not maintained.

### Room Context & the Attention List (`buildRoomContext()`)

`buildRoomContext()` (line 582) builds the area description injected into the agent's user message. Since the interest system landed (2026-08-05, task-98 Phase 2), room items render as an **"Items that catch your attention"** list instead of the old "everything gets a full description" block:

- **Unexamined only** — items already examined or taken (in `player.discovered_items`) are omitted; their facts live in `=== MY INVESTIGATION NOTES ===`.
- **Interest-sorted** — items matching `player.interest_tags` (exact tag +2, keyword-in-name +1) surface first; then the rest.
- **Weight-ordered** — within each tier, heavier items first (bigger = easier to see; missing/0 weight sinks).
- **Capped at 15** (`ATTENTION_MAX`) — one uniform path for all room sizes, no small/large threshold. Emphasis (sorting) is always on; the cap just bites when a room has more than 15 unexamined items.
- **Natural trailer, no truncation** — ends with `There are more items around that you can look for.` when the cap bit, or `...and not much else.` when everything visible fit.
- **Light logic unchanged** — pitch black/dim/dark-vision filtering is untouched; attention sorting only refines within each light branch.

### People here + spatial position (task-135)

Each person line can include a **position suffix** from `spatial_position` / `at_way_id`:

```text
  - the woman (awake) beside the piano — A musician…
  - the stranger at the north — A tall figure…
```

- **Stranger labels** — unmet characters show `unknown_display_name()` (`the man`, `the woman`), not database names. The suffix uses the same anonymous label for character anchors.
- **Relationship labels** — met characters get an inline type label (`- a close friend -`) before
  `(state)`, from `buildRelationshipLabel()` (no `(65/100)` scores).
- **Targeting** — combines appearance handle + location (`attack the man`, `go north`). Backend `_match_character_name()` also resolves description words in the same area.
- **Physical actions walk you there** — open/go/give/grab/attack set position automatically; `examine room` steps back. See [[Gameplay/Character Spatial Position]] and `system-prompt.js` Rules.

## Memory in the agent

See [[AI & Narration/Memory System]]. Key points:

- **One memory per turn** — the react phase's `memory` field (subjective takeaway, importance + tags chosen by the LLM).
- `_extractMemory()` parses `{text, importance, tags}`; tags auto-register into the tag library.
- `storeMemory()` POSTs to backend `/memories/entry` (with `entity_ids` = current area node).
- Speech/emotes/thoughts are log-only, not memories.

## Agent Configuration

| Property | Type | Description |
|----------|------|-------------|
| `personality` | string | Core personality prompt |
| `description` | string | Appearance |
| `state` | string | `awake`, `sleeping`, `dead`, `unconscious` |
| `simple_npc` | boolean | Skip LLM calls, act via backend NPC tick |
| `npc_behavior` | string | `wander`, `still`, `patrol`, `flee`, `guard` |
| `npc_action_interval` | int | Ticks between autonomous NPC actions |
| `npc_state` | string | `idle`, `curious`, `hostile`, etc. |
| `behaviors` | array | Event-driven behavior definitions |
| `emotion` | object | `{current, intensity, description}` |
| `traits` | object | `dark_vision`, `slasher`, etc. |
| `equipped` | object | Worn items by slot |

Settings panel controls: API key/base/model/temperature, turn-based mode + order, reactive mode, ghost mode, manual mode, streaming, RPM/TPM limits.

## Difference Between LLM Agents and Simple NPCs

- **LLM agents** (`simple_npc: false`): full LLM decision-making, retained conversation history, unified memory + reflection, multi-step plans, structured actions. 2 LLM calls/turn in reactive mode.
- **Simple NPCs** (`simple_npc: true`): no LLM calls, behavior driven by `behaviors[]` + `npc_behavior` pattern, controlled by backend `tick_turn`. Suitable for animals, minor NPCs, environmental entities.

## Related

- [[dev_tasks/done/prompting/task-160-parameterized-actions-in-prompts|task-160: Parameterized actions]]
- [[dev_tasks/done/characters/task-178-unify-memory-systems|task-178: Unified memory]]
- [[Gameplay/Character Spatial Position]]
- [[AI & Narration/Memory System]]
- [[AI & Narration/Turn-Based System]]
