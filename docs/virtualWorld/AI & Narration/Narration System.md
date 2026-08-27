# Narration System

The Narration System adds atmospheric flavor text to game actions and room descriptions. It operates in three modes and integrates with both the agent engine and the LLM client.

## Narration Modes

The mode is a 3-way toggle stored on `app.world.narration_mode` (backend) and `narrationUI.mode` (frontend).

| Mode | Description |
|------|-------------|
| `none` | Default — static descriptions only, no narration |
| `player` | Player is prompted to narrate actions/descriptions via a modal |
| `ai` | LLM generates narrative flavor text automatically |

### Backend Storage (`routes/settings.py:99-117`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings/narration` | Get current mode |
| POST | `/api/settings/narration` | Set mode (`none`, `player`, or `ai`) |

The mode is persisted on the world object (`app.world.narration_mode`).

### Frontend UI (`static/js/narration-ui.js`)

The `NarrationUI` singleton (`window.narrationUI`) provides:

```javascript
class NarrationUI {
    constructor()  // mode = 'none', loads saved setting
    setMode(mode)  // 'none' | 'player' | 'ai', saves to backend
    getMode()      // returns current mode
    getNarratedRoomContext(roomContext, charName)  // narrate room description
    getNarratedActionResult(actionOutput, charName, action)  // narrate action result
}
```

The mode is indicated by a badge UI element (`#narration-indicator`) with visual classes:
- `narration-none`: 🔇 No Narration
- `narration-player`: 🎭 Player Narration
- `narration-ai`: 🤖 AI Narration

## How Narration Works

### Area Narration Flow

When the agent engine calls `_buildNarratedRoomContext()` (or `PromptBuilder.buildNarratedRoomContext()`):

1. Standard room context is built
2. If mode is `player`:
   - A modal appears with pre-filled room description text
   - Player can edit the narration and submit or skip
   - The edited text replaces the room description in agent context
3. If mode is `ai`:
   - A system prompt and user prompt are sent to the LLM
   - The LLM generates 2-4 sentences of atmospheric description
   - The generated text replaces the room description
4. The narrated text is also broadcast to the room as an emote (`*narrated text*`)

### Action Narration Flow

After an agent executes an action (`agent-engine.js:275`):

```javascript
const narrationMode = window.narrationUI?.getMode();
if (narrationMode === 'ai' && config.apiKey && config.model) {
    const narrated = await window.narrationUI.getNarratedActionResult(outputText, charName, finalAction);
    if (narrated) outputText = narrated;
}
```

1. The action result text is captured
2. If mode is `player`: modal shows action + result for player to narrate
3. If mode is `ai`: LLM generates 1-3 sentences narrating the outcome
4. The narrated text replaces the raw action output in the event log

## Narrative Generation via LLM

### Area Narration Prompt (`narration-ui.js:171-196`)

System message: *"You are a narrative game master — a DM describing a scene to a player. Write in second person. Be atmospheric and vivid. Use sensory details. Keep it 2-4 sentences. Do NOT list items mechanically. Integrate notable items into the description naturally."*

User prompt includes: room name, description, notable items, characters present, and exits. Temperature is set to `0.8` for creative variation.

### Action Narration Prompt (`narration-ui.js:201-224`)

System message: *"You are a narrative game master for a game. Describe the outcome of actions atmospherically. Keep it 1-3 sentences."*

User prompt includes: character name, action description, and raw result text. Temperature `0.8`.

## Narration API Endpoints

### Area Context (`routes/narration.py:20`)

`GET /api/narration/context/room?room=<name>`

Returns structured data for narrating a room: room name, description, items, characters, exits, environment.

### Action Context (`routes/narration.py:32`)

`POST /api/narration/context/action`

Returns structured data for narrating an action: actor, action type, description, room context.

### Narration Injection (`routes/narration.py:48`)

`POST /api/narration/inject`

Inject narration text into the event log and turn events. Accepts `text`, `source` (player/ai/system), `room`, and `actor`.

## Roleplay Action Commands (Emote)

The `emote` or `do` command allows players and agents to perform narrative roleplay actions without game-mechanical effects. These are pure flavor.

### Syntax

```
do kisses Alice gently
emote sighs heavily
```

### Backend

Emotes are broadcast to the room as narrative text. They appear in the event stream with the `msg-emote` class and are visible to all characters in the room.

### Agent Usage

LLM agents can generate emotes in two modes:
- **Reactive mode (thought→act→react)**: The decision phase prompt asks for `"emote"` in the JSON response. Emotes are executed after the main action via `ApiClient.emote()`.
- **Non-reactive mode (combined)**: The reaction prompt also asks for `"emote"`. Emotes are executed asynchronously alongside the main action.

Rules that shape agent emotes:
- **`emote` is a field, not a verb** — the ACTIONS table lists it only under Rules with example JSON; the LLM must pair it with a real action (`wait`, `go`, `use_on`, ...). Using it as an action verb is rejected.
- **Emotes are speculative in the decision phase** — they only run if the action didn't fail or get rejected. A bad verb (e.g. `climb`) suppresses the emote and instead surfaces a natural in-world rejection ("You try to climb the ceiling, but you can't do that") that flows into the react phase.
- **The react prompt frames time**: only a moment passes between the agent's own action and its reaction — other characters haven't had time to respond, so silence isn't treated as being ignored.

## Integration with Agent Engine

Narration feeds into agent perception in three ways:
1. **Area context**: The narrated description replaces the default room description the agent "sees"
2. **Action results**: The narrated outcome replaces the raw system output
3. **Event log**: Narration text appears in the room event log, visible to other agents as witnessed events

The `_buildNarratedRoomContext()` method at `agent-engine.js:497` (and its extracted counterpart in `agent/prompt-builder/`) handles the narrated room context for reactive-mode agents. It:
- Calls `narrationUI.getNarratedRoomContext()` to get the narrated text
- Replaces the default description in the room context string
- Broadcasts the narration to the room as an emote

This means narrated descriptions become part of what other agents in the room observe, creating a shared narrative layer.

## Related tasks

- [[dev_tasks/review/prompting/task-39-observe_rich_description|task-39: Observe rich description]]
- [[dev_tasks/review/environment/task-43-relieve_adds_smell|task-43: Relieve adds smell]]
- [[dev_tasks/review/environment/task-49-toggle_room_context_generation|task-49: Toggle room context generation]]
