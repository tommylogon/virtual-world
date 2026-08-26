# Narrative Actions (Emote / `do` System) — Design

Date: 2026-07-20

## Summary

Add support for narrative roleplay actions — actions a character performs that have no
game-mechanical effect but add flavor, emotion, and social depth. These are the equivalent
of a D&D player saying "I lean against the wall and light my pipe" — no dice, no mechanics,
just character.

The system adds an optional `emote` field alongside `action` and `speech` in agent responses,
a `do` verb for human players, and posts all emotes as room events so other characters
witness and react to them naturally.

## Approaches Considered

### Approach 1 (Recommended): Separate `emote` / `do` field

Agent returns `{"action": "go north", "emote": "kisses Alice gently"}` — mechanical and
narrative in one turn. Human players type `do kisses Alice gently`. Unrecognized commands
also auto-fallthrough to emote.

**Pros:** Clean separation; both action types in one turn; full creative freedom.
**Cons:** More API calls; agent prompt changes needed.

### Approach 2: Unrecognized verbs fall through

No special agent field. `{"action": "kiss Alice"}` goes unrecognized → becomes narrative.

**Pros:** Simplest; no new fields.
**Cons:** Agent must choose mechanical vs narrative each turn; risk of accidental triggers.

### Approach 3: Dedicated `emote` verb

Add `emote` as a recognized verb. Agent writes `{"action": "emote kisses Alice"}`.

**Pros:** Explicit intent; consistent with existing command structure.
**Cons:** Clunky; agent can't do mechanical + narrative in same turn.

---

## Phase 1: Quoted Parameter Parsing

### Problem

Commands like `put brass key in backpack` fail because the parser splits on spaces —
"brass" and "key" become separate tokens. Multi-word item names (`front door`, `brass key`,
`wooden chest`) are unreliable.

### Solution

Replace simple `command.split()` with a tokenizer that respects double-quoted strings:

```
"go front door"        → tokens: ["go", "front door"]
"take 'brass key'"     → tokens: ["take", "brass key"]
"put 'brass key' in 'wooden chest'" → tokens: ["put", "brass key", "in", "wooden chest"]
"use key on chest"     → tokens: ["use", "key", "on", "chest"]
```

**Rules:**
- Single quotes `'...'` and double quotes `"..."` both create a single token.
- Unquoted tokens split on spaces as before (backwards compatible).
- This lives in a helper function `tokenize_command(cmd)` in `app.py`.

### Impact

Every `if/elif` branch in `take_action()` that parses positional arguments gets updated
to use the new tokenizer. Existing commands continue to work identically for
single-word arguments.

---

## Phase 2: `do` Verb (Human Players)

### Syntax

```
do kisses Alice gently
do stands by the window, watching the rain
do "leans against the wall and lights a pipe"
```

### Processing

1. `take_action()` recognizes `do` as a verb token.
2. Everything after `do` is the emote text.
3. Calls `process_emote(actor, emote_text)`.

### Auto-fallthrough

If a command goes through all existing parsing layers and none match (including LLM
reinterpretation), it becomes an emote instead of returning "Unknown command."

**Priority order (unchanged from existing, except last):**
```
verb aliases → movement → door open/close → eat/drink → relieve →
use X [on Y] → examine → take → drop → inventory → rest/sleep →
fumble → look → stats → manifest/vanish → toggle → attack → speak →
LLM reinterpretation → EMOTE (new)
```

This ensures `kiss Alice` (no recognized verb) becomes an emote, while
`take sword` still executes `take`.

---

## Phase 3: Agent `emote` Field

### Agent Response Format

Extend the existing JSON response:

```json
{
  "inner_monologue": "I want to be affectionate...",
  "speech": "You look lovely today.",
  "emote": "gently strokes Alice's cheek with a soft smile",
  "action": "look"
}
```

### System Prompt Updates

Add to the character's system prompt (both `_buildCharacterSystemPrompt` and
`getSystemPrompt`):

```
EMOTE (optional): Describe a roleplay action your character performs.
  This is pure flavor — it does NOT change the game state.
  Examples: "kisses Alice's forehead", "paces nervously",
  "fiddles with a ring", "winks at Bob", "curtsies deeply"

  You may include an emote alongside your regular action in the same turn.
  The emote is visible to everyone in the room.
```

### Execution Flow

In `AgentEngine._executeAction()` (reactive mode) or the combined flow (legacy mode):

```
1. Execute mechanical action: POST /api/action { command: action }
2. If emote is present:       POST /api/emote { actor, emote }
3. Combine both results into the reaction phase context
```

### Action Validation

The `_validateAction()` method adds `emote` as a valid top-level field (not a verb).
The `action` field still gets validated against the known verb list as before.

---

## Phase 4: Backend `process_emote()` Engine Method

### Location

New method in `virtual_world_engine.py`:

```python
def process_emote(self, actor_name, emote_text):
```

### Processing Steps

1. **LLM parsing** — Send emote text to LLM to extract:
   - `description`: vivid 1-3 sentence narrative of the action
   - `targets`: character names directly involved
   - `context`: room name, other characters present

2. **Area event logging** — Store the emote as a room event:

```python
{
    "type": "emote",
    "actor": "Alice",
    "description": "Alice leans in and gently kisses Bob on the cheek.",
    "targets": ["Bob"],
    "turn": current_turn
}
```

3. **Return** description text for display.

### API Endpoint

```
POST /api/emote
{ "actor": "Alice", "emote": "kisses Bob gently" }
→ { "description": "...", "targets": ["Bob"] }
```

### LLM Prompt for Emote Parsing

```
You are parsing a narrative roleplay action in a text-based virtual world.

Action text: "{emote_text}"
Performed by: {actor_name}
Current room: {area_name}
Characters present: {character_list}

Return JSON with:
- "description": A 1-3 sentence narrative of the action as seen by an observer.
  Write in present tense, third person. Make it vivid but concise.
  Do NOT invent outcomes for other characters — only describe the actor's actions.
  Example: "Alice steps close to Bob, rises on her toes, and gently kisses his cheek."
- "targets": An array of character names directly involved in the action.
  Empty array if no specific target.

Return ONLY valid JSON, no other text.
```

---

## Display & Event Flow

### Client-side (event-stream.js)

New message type `msg-emote` with distinct styling:

- Icon: `🎭` (or text marker)
- Label: `[Emote]` prefix
- Filter toggle: bundled with actions or standalone

### Area Event Integration

Emotes are stored alongside other room events in the event log. When agents
observe their surroundings, they see emotes as witnessed events. The agent
naturally decides how to feel/react on their next turn.

**No immediate reactions** — the receiving character's LLM processes the emote
on their next turn, deciding their emotional response and relationship effects
organically. This avoids the complexity of auto-generating reactions.

---

## File Changes Summary

| File | Change |
|------|--------|
| `app.py` | Add `tokenize_command()`, `do` verb handling, auto-fallthrough to emote, `POST /api/emote` endpoint |
| `virtual_world_engine.py` | Add `process_emote()` method, LLM emote parsing integration |
| `agent-engine.js` | Add `emote` field to response format, execution flow, prompt updates |
| `event-stream.js` | Add `msg-emote` display type, filter toggle, room event integration |
| `mcp_server.py` | Add `emote(text)` tool |
