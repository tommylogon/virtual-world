# Event Stream Design Recommendation — Analysis & Brainstorm

**Date**: 2026-08-18
**Status**: Design exploration — no code changes

---

## 1. Current State: What Works

The real event stream (`event-stream.js` + `style.css` + `index.html`) has solid bones:

- **Universal log**: 234 callsites across 27 files feed it. It is the single source of truth for everything that happens.
- **Live streaming feedback**: `startStreaming` / `appendStream` / `finishStreaming` gives "it's alive" token-by-token output.
- **Filtering infrastructure**: Checkboxes for thoughts/speech/actions/system/raw-LLM + actor dropdown + tick toggle. All wired to config persistence.
- **Theming**: Dark / Disco Elysium / Linear / Terminal — already plumbed through `data-style`.
- **State backbone**: `_characterState` and `_areaEventLog` are consumed by prompts and inspectors. The visual bubbles are a *projection* of state.
- **Persistence**: IndexedDB restore of last 500 bubbles survives refresh.
- **Actor names prepended**: Character names appear at the start of bubbles (`jake halloway think observing`, `LLM → qwen3.5-2b...`), so you can always see who did what.
- **Turn-based execution**: Agents act one at a time in sequence, so the stream is naturally readable without simultaneity concerns.

---

## 2. Current State: What Hurts

### 2.1 Flat density — no visual hierarchy

Every event is a single `msg-bubble` row with `[Tick X | HH:MM] icon actor text`. In a long session, the stream becomes an undifferentiated wall. You cannot quickly distinguish thoughts from actions from results.

### 2.2 Actor filter is broken

The actor dropdown (`#stream-agent_filter`) exists in the HTML and has an `onchange` handler, but **`updateAgentFilterDropdown()` is never called anywhere**. The dropdown stays empty. This is a dead feature that needs to be wired up.

### 2.3 No area-based filtering

`_areaEventLog` is populated and consumed by the inspector's area view (`inspector/area-view.js:68`), but the event stream has no way to filter or highlight events by area. If you click an area in the inspector, the stream keeps showing everything.

### 2.4 LLM raw output order is wrong

In the real export, the raw LLM request/response appears *before* the resolved action/result:

```
📤 LLM request (system prompt)
🤖 LLM response (JSON action)
▶️ examine Panel 17        ← actual outcome
```

The LLM bloat itself is **not the problem** — you have the `filterRawLLM` checkbox and can toggle it off. The problem is that when raw LLM *is* shown, the ordering buries the outcome. You want to see what happened first, then how the agent decided it.

### 2.5 Narration is invisible

`narration-ui.js` substitutes AI/player narration for area descriptions and action results, but the stream shows no indicator. You see the result text but not that it was *narrated* vs raw engine output.

### 2.6 Memory/reflection events are not styled

`🧠 reflected on N memories` exists in the category map but has no dedicated `.msg-reflection` style. It falls through as a generic system message.

### 2.7 Phase markers are visible but subtle

`logPhase` emits `👁️ observe`, `💭 think`, `🎯 decide`, `⚡ act`, `🔄 react` as emoji-prefixed bubbles. They appear in the stream but blend in with other rows. They could be more visually distinct (background tint, separator line, etc.).

### 2.8 World results could be clearer

Action results are rendered as plain text in `.msg-result`. There's no visual distinction between:
- A successful action ("You pick up the matches.")
- A failed skill check ("You don't notice anything else.")
- A system constraint ("You can't do that while grappled.")
- A trigger effect (the door speaks to you)

These are all the same color and weight in the stream.

### 2.9 No compact/dense mode toggle

The current stream is fixed-density. Turn cards exist in the code (`turn-card` classes in `style.css`) but are not actively used in the flat bubble mode. There's no toggle between a compact single-line mode and a expanded card mode.

### 2.10 XSS risk

`logThought` and `_addBubble` interpolate LLM text into `innerHTML` without escaping. Only `rawLLM` paths escape. This is a security hole.

---

## 3. Demo vs. Real: Where They Diverge

| Aspect | Demo (event-stream-demo.html) | Real (event-stream.js) |
|--------|------------------------------|----------------------|
| **LLM payload** | Compact 3-line mockups | 200-500 line system prompts repeated per phase |
| **Grouping** | Turn cards with semantic rows | Flat bubbles, no grouping |
| **Actor identity** | Color-coded borders + names | Monochrome, same font for all |
| **Phase visibility** | Not modeled (demo is post-hoc) | Visible but subtle emoji prefixes |
| **Skill checks** | Beautiful `.skill-badge` chips | String-matched, rendered inline |
| **Flat events** | Separate section, clearly labeled | Mixed into the same flat stream |
| **Narration** | Not present | Invisible substitution |
| **Memory events** | Not present | `🧠 reflected on N memories` |
| **Area filtering** | Not present | `_areaEventLog` exists but not exposed to stream |
| **Actor filter** | Not present | Dropdown exists but is broken (never populated) |

**The demo solves the *narrative* problem well. The real stream has more data but less structure.**

---

## 4. What's Missing / What to Add

### 4.1 Area filter — click area, see only that area's events

**This is the #1 requested feature.** The data already exists in `_areaEventLog`. The inspector already shows it. The stream just needs a filter mode:

- Add an area dropdown/filter bar (or make the stream react to inspector selection)
- When area "foyer" is selected, only show events where `data-area="foyer"` or where the actor is currently in "foyer"
- Highlight area-change events (entering/leaving) so you can see transitions

**UI pattern**: When you click an area in the inspector, the stream gets a "scoped to: foyer" banner and filters. Click "clear" to show all again.

### 4.2 Fix the actor filter

`updateAgentFilterDropdown()` exists but is **never called**. Wire it up:
- Call it after every new actor is seen (in `_addBubble`, `logPhase`, etc.)
- Call it on stream restore
- The dropdown then actually works for filtering by character

### 4.3 Reorder: outcome before LLM detail

When raw LLM is visible, change the order within a turn:

```
💭 jake halloway think observing
▶️ examine matches
↳ You pick up a small box of matches...
📤 LLM → qwen3.5-2b-polaris-highiq-instruct-i1 [collapsed]
🤖 LLM Response [collapsed]
```

This way the *result* is always visible first. The LLM detail is secondary context, not the primary content.

### 4.4 More filters

Add filter toggles for:
- **Area** (dropdown, "all areas" default)
- **Result type** (success / failure / neutral — inferred from text or structured data)
- **Narration** (show/hide AI-narrated events separately)
- **Phase** (show/hide observe/think/decide/act/react markers)
- **Skill checks** (show/hide skill badges separately from actions)

Keep the existing ones (thoughts, speech, actions, system, raw-LLM, tick, actor).

### 4.5 Clearer world results

Style action results differently based on outcome:
- **Success**: green left-border or subtle green tint
- **Failure**: red left-border or subtle red tint  
- **Neutral/system**: no tint, default text
- **Trigger/effect**: purple left-border (existing `.msg-trigger` style)

Add a result type badge: `✓ success`, `✕ failure`, `⚠ partial`, `ℹ info` — small, inline, before the result text.

### 4.6 Narration indicator

When `narration-ui.js` substitutes narration, emit a small badge:

```
🎭 [AI Narration] The oak door groans as it opens...
```

Or add a `data-narrated="true"` attribute and style it with a subtle gold left-border.

### 4.7 Memory/reflection styling

Add `.msg-reflection`:

```
🧠 jake halloway reflected on 3 memories (tags: fear, escape)
```

Style it distinct from system messages — maybe purple tint, similar to `.msg-trigger`.

### 4.8 Phase marker styling

Make `logPhase` visually distinct even in flat mode:
- Background tint (subtle, matching phase color)
- Phase label in a small badge/pill shape
- Left border color matching phase (observe=blue, think=purple, decide=orange, act=green, react=teal)

### 4.9 Compact mode toggle

A toggle between:
- **Card mode** (demo style): turn cards with semantic rows, more vertical space, easier to read
- **Compact mode** (current style): single-line bubbles, max density, fast scanning

Default to compact (current behavior) since that's what the user is used to.

### 4.10 XSS fix

Escape LLM-derived text in `logThought` + `_addBubble` via existing `_escapeHtml()`. Must-do regardless of other changes.

---

## 5. What's in the Wrong Order

### 5.1 LLM raw output appears before the resolved action

In the real export:

```
📤 LLM request (system prompt)
🤖 LLM response (JSON action)
▶️ examine matches
↳ You pick up the matches.
```

**Fix**: Reorder so action + result appear first, then LLM detail:

```
▶️ examine matches
↳ You pick up the matches.
📤 LLM · think-decide [expandable]
🤖 LLM Response [expandable]
```

### 5.2 Turn cards close on system messages

In `_closeTurnCard()`, any non-agent event immediately closes the current turn card. A `⚠️ replanned` system message mid-turn breaks card grouping. System messages that fire during an agent's turn should stay *inside* the turn card, not close it.

---

## 6. Brainstorming: Ideas to Consider

### 6.1 Result significance levels

Not all results are equal:
- **Critical**: death, scenario end, condition change, combat hit
- **Normal**: picked up item, moved to room, opened door
- **Minor**: "You don't notice anything else", "Nothing unusual happened"

Style them with different weights or left-border colors. Critical results get a thicker border or bold text.

### 6.2 Event provenance tags

When a trigger fires, show the source node:

```
⚡ [front_door] The massive oak front door groans...
```

Clickable → opens inspector on that node. This bridges the stream to the graph editor.

### 6.3 Stream scope indicator

When the stream is filtered by area or actor, show a persistent banner:

```
📌 Scoped to: foyer (jake halloway)  [× clear]
```

So you never forget you're in a filtered view.

### 6.4 Action verb highlighting

Color the action verb differently from the target:

```
▶️ examine matches
```

`examine` in accent color, `matches` in default text. Makes actions scannable at a glance.

### 6.5 Tick dividers for major events

Keep the existing tick markers but add *area transition* dividers:

```
─── foyer → library ───
```

When an agent moves between areas, show a transition line. This makes spatial movement visible in the stream.

---

## 7. Recommended Implementation Order

### Phase 1: Fix broken things + reorder (quick wins)

1. **Fix actor filter** — call `updateAgentFilterDropdown()` so the dropdown populates
2. **XSS fix** — escape `logThought` + `_addBubble`
3. **Reorder**: action/result before LLM detail within a turn
4. **Fix turn card closing** — system messages during a turn shouldn't close the card

### Phase 2: Filtering + clarity (medium effort)

5. **Area filter** — dropdown + scoped view, uses existing `_areaEventLog`
6. **More filters** — narration, phase, skill checks, result type
7. **Clearer world results** — success/failure styling, result badges
8. **Narration indicator** — badge or border for AI/player-narrated events

### Phase 3: Visual polish

9. **Memory/reflection styling** — `.msg-reflection` distinct from system
10. **Phase marker styling** — tinted background, pill badges, color-coded borders
11. **Action verb highlighting** — accent color on verb, default on target
12. **Compact mode toggle** — card vs dense mode

### Phase 4: Nice-to-haves

13. **Stream scope indicator** — banner when filtered
14. **Area transition dividers** — show movement between rooms
15. **Event provenance tags** — clickable node IDs on triggers
16. **Result significance levels** — critical/normal/minor visual weight

---

## 8. Decisions Needed

| # | Decision | Options |
|---|----------|---------|
| 1 | **LLM ordering**: reorder so action/result comes before raw LLM? | Yes / No |
| 2 | **Turn cards**: keep current flat mode, add card mode toggle, or switch default? | Flat-only / Toggle / Card-default |
| 3 | **Area filter**: dropdown in stream header, or auto-scope when area clicked in inspector? | Dropdown / Inspector-linked / Both |
| 4 | **Result styling**: color-code by success/failure/neutral? | Yes / No |
| 5 | **Narration**: inline badge or separate filter toggle? | Badge / Filter / Both |
| 6 | **Phase markers**: subtle styling overhaul, or keep as-is? | Overhaul / Keep |

---

## 9. What the Demo Does Well (to preserve)

- Turn card layout with actor color border
- Semantic message rows (thought, speech, action, result, trigger, heard, env)
- Skill badges as visual chips
- LLM request/response chips with expand
- Tick dividers for temporal structure
- Flat non-agent events (user commands, graph edits, saves) separated from agent turns
- Hover states and clickable actor names
- Density mode concept (cards vs compact)

---

## 10. Risk: The Stream is State, Not Just UI

Any redesign must keep these intact:

- `events.trackAction(charName, inner, speech, action, result)` → populates `_characterState.actionHistory`
- `events.logThought(charName, thought)` → populates `_characterState.lastThought`
- `events.logAreaEvent(area, charName, action, result)` → populates `_areaEventLog`
- `events.trackPhase(charName, phase, data)` → populates `detailedTimeline`
- `events.emit('log', {text, className})` → pub/sub subscribers exist
- `events.restoreLog()` / `_persistLog()` → IndexedDB round-trip

The visual redesign is a *projection layer* on top of this state. We can re-skin the DOM, add metadata attributes, and change ordering, but the state-population methods must keep working exactly as they do.

---

## 11. Verified Facts from Code + Logs

- **Actor filter dropdown**: defined in HTML (`#stream-agent_filter`), `updateAgentFilterDropdown()` exists in `event-stream.js:111` but is **never called** — dropdown stays empty.
- **Area event log**: `_areaEventLog` populated by `trackAction` → `logAreaEvent`, consumed by `inspector/area-view.js:68` and `prompt-builder/room-context.js:396`. Not exposed to stream.
- **Raw LLM filter**: `config.filterRawLLM` checkbox exists and is wired to `applyFilters()`. LLM bloat is toggleable.
- **Turn execution**: agents run sequentially (one at a time), not simultaneously — confirmed from `agent-engine.js` turn queue logic and user feedback.
- **Real log format**: `data/exports/Untitled-1.txt` and `data/scenarios/logs/event_stream_from_18082026.txt` show the actual stream output — flat bubbles, actor names prepended, raw LLM dumps inline.

---

*End of design recommendation.*
