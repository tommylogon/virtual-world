# Design Document: Event Stream Visual Evolution (The Commons Influence)

**Date**: 2026-10-21  
**Status**: Proposal / Design  
**Author**: Juno & Tommy  
**Context**: Visual refinement of the live Event Stream based on architectural learnings from The Commons without losing the stream's technical and spatial precision.

---

## 1. Executive Summary

The Event Stream (`static/js/event-stream.js`) is the primary live temporal narrative and telemetry feed in VirtualWorld. A recent review of the stream against The Commons highlighted two key findings:

1. **What works well and must stay**:
   - High data density and chronological precision (`[Tick 302 | 08:05]`).
   - Clear icon hierarchy (speech bubble, action mask, lightning bolt, result status).
   - Real-time LLM telemetry pills (`think-decide ~4.1k tok`, `DECIDE · DECIDING`).
   - Inline failure feedback (`❌ There's no 'mikka' here to approach.`).
   - Area scoping (clicking an area node filters the stream to that room's events).

2. **What needs improvement (inspired by The Commons)**:
   - **Monologue Differentiation**: Private internal thoughts are currently rendered as plain italic text in the public event column, blurring the boundary between internal cognition and physical acts.
   - **Turn Beat Cohesion**: An actor's full turn cycle (Decide -> Thought -> Speech -> Emote -> Act -> Result) is currently presented as 7-8 disconnected horizontal rows separated by identical dividers.
   - **Dialogue Prominence**: Spoken conversation lines should stand out clearly when scanning a dense log.
   - **Character Attribution**: Relying solely on a colored text name misses the quick visual recognition provided by character portrait chips.

---

## 2. Visual Enhancements

### 2.1. Dedicated Internal Monologue Styling

**Problem**: Tick 302 in the current stream renders Vekka's private reasoning (*"Hungry. That boar is shouting..."*) as a standard text row with a thought icon. To an observer, it visually blends with physical descriptions.

**Solution**:
- Render internal thoughts inside a distinct **cognition block**:
  - Softer background tint (e.g. `rgba(255, 255, 255, 0.03)` or subtle purple/indigo aura).
  - Subtle left border accent (`border-left: 2px solid var(--accent-thought, #a855f7)`).
  - Softer text color with clear indication of private state (e.g. badge: `THOUGHT`).
  - Distinguishes private character thoughts from words that echoed into the room.

### 2.2. Spoken Dialogue Callout

**Problem**: Spoken dialogue (Tick 303: `says: "Mikka. You wouldn't happen to know..."`) uses standard monospace text with quotes on the dark background.

**Solution**:
- Dialogue rows receive enhanced typographic hierarchy:
  - Slight font weight adjustment or quote callout styling.
  - Border-left accent matching the actor's theme color or speech tier (e.g., green for normal speech, orange for shout, blue for whisper).
  - Quoted text displayed with high contrast so dialogue is immediately legible during fast playback.

### 2.3. Turn Grouping (Turn Beat Cards)

**Problem**: When an agent takes a turn, 6 to 8 rows fire in sequence:
- `Tick 301 [DECIDE]`
- `Tick 302 [Thought]`
- `Tick 303 [Speech]`
- `Tick 304 [Emote]`
- `Tick 305 [ACT]`
- `Tick 306 [Command]`
- `Tick 307 [Result]`
- `Tick 308 [REACT]`

Reading them as isolated rows across full-width horizontal rules makes it difficult to perceive the turn as a single unified action beat.

**Solution**:
- Group rows belonging to the same actor and turn sequence into a **Turn Beat Container**:
  - Connected by a faint vertical spine along the left margin.
  - The first row establishes the turn header with the actor portrait chip and name.
  - Subsequent rows (thoughts, words, actions, results) nest within the turn's visual flow.
  - Keeps the terminal feel while adding narrative grouping.

### 2.4. Portrait Chips / Mini-Avatars

**Problem**: Every row identifies the actor purely by colored text (`Vekka` in pink).

**Solution**:
- Introduce a 20x20px or 24x24px round avatar thumbnail next to the actor name at the start of a turn group.
- Leverages the existing avatar/portrait assets (`character-art.js` and Commons image assets).
- Falls back to initials or role icons when no custom portrait is authored.

---

## 3. Interaction & Spatial Integration

### 3.1. Area POV Filtering
- Maintain the current behaviour: selecting an area node in the graph scopes the Event Stream to events that occurred in that specific area.
- Add clear visual breadcrumbs at the top of the stream: e.g. `[Scattering Cavern (Scope: Goblin Camp)]` with a toggle to reset to `[Whole World (Omniscient)]`.

### 3.2. Private Sensory & Trigger Feedback
- As established in perception analysis, sensations that only one character feels (e.g., item curse, hunger pangs, sensory checks) appear in that character's monologue block or private result strip, never as ambient room events.

---

## 4. Implementation Plan

1. **CSS Component Updates (`static/css/`)**:
   - `.event-row-monologue`: Styling for internal cognitive reasoning.
   - `.event-row-speech`: Distinct speech styling with accent borders.
   - `.turn-group`: Vertical connector styling for rows within the same actor turn.
   - `.actor-portrait-chip`: Small circular avatar next to actor handles.

2. **Stream Formatter Refinement (`static/js/stream/` / `static/js/event-stream.ts`)**:
   - Detect turn start/end boundaries from SSE event payloads.
   - Wrap related tick rows within a cohesive turn container when rendering to DOM.
   - Attach portrait URLs from `worldState.data.players[actor].avatar`.

3. **Verification & Testing**:
   - Verify that all existing unit tests in `tools/unit/test_turn_feed_scope.js` and `tests/test_commons.py` continue to pass.
   - Test in both Scoped POV (selected area) and World Log modes.

---

## 5. Non-Goals

- **Not replacing the Event Stream with The Commons**: The Event Stream remains the technical, scrollable, timestamped record of reality.
- **Not hiding debug info**: Token counts, prompt labels, and execution diagnostics remain visible or collapsible.
