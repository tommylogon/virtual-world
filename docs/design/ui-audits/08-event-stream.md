# Event Stream & Live Feed UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Event Stream (`static/js/stream/`, `event-stream.ts`) - 1,200+ lines
- Stream Filters (`static/js/stream/stream-filters.ts`) - 214 lines
- Stream Scrubber (`static/js/stream/stream-scrubber.ts`) - 280 lines
- Turn Cards (`static/js/stream/stream-turn-cards.ts`) - 350 lines
**Rendering Tech:** Direct DOM append to `#event-stream` container with CSS filter classes.

---

## 1. Measured Ground Truth & Architecture

The Event Stream provides the chronological story feed of everything occurring in the simulation:
- Dialogue (`say`, `whisper`, `shout`)
- Physical Actions (`strike`, `take`, `move`, `open`)
- Cognitive Events (`thought`, `reflection`, `recall`)
- Environmental Events (`tick decay`, `temperature shift`, `spoilage`)

### The 15 Filter Categories
`StreamFilters.applyFilters()` (lines 33-49) gates 15 distinct event kinds:
`thought`, `speech`, `action`, `emote`, `result`, `whisper`, `reflection`, `recall`, `npc`, `narrated`, `crisis`, `prune`, `system`, `error`, `rawllm`.

---

## 2. Usability & Layout Critique

### A. The Endless DOM Pileup
- Events are appended directly as DOM nodes (`<div class="turn-card">`).
- In a 1,000-tick soak simulation, the container accumulates thousands of heavy DOM nodes with nested avatars and roll chips.
- Memory usage skyrockets, and scrolling through past turns stutters violently due to layout recalibration.

### B. HTML String Persistence (task-779)
- Historical runs are stored in browser localStorage or exported as concatenated raw HTML strings rather than structured JSONL records.
- Searching or filtering past events requires reparsing raw text off DOM nodes (`child.textContent`).

### C. Narrative Bleed (bug-517)
- AI room narration was historically broadcast into the stream as if spoken by the character, causing nearby NPC listeners to record the GM's narration as audible speech in their memory banks.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: The Virtual World Chronicle

```
+----------------------------------------------------------------------------------------------------+
| 📜 SIMULATION CHRONICLE                                     [ Live Auto-Scroll: ON ] [ Export ▾ ]  |
+----------------------------------------------------------------------------------------------------+
| TIMELINE SCRUBBER: Round 12 (Tick 142)  [ ◄ Step ] [ ▶ Play 1x ] [ ⏸ Pause ] [ ⏭ Step ]          |
| ──|──────────|──────────|──────────▲──────────────────|                                            |
| Tick 0     Tick 40    Tick 80   Tick 142 (NOW)     Tick 200                                        |
+----------------------------------------------------------------------------------------------------+
| FILTER STRIP:                                                                                      |
| [ 🔍 Search stream... ]  Actor: [ All Characters ▾ ]  Scope: [ Current Area Only ▾ ]               |
| Tags: [x] Dialogue  [x] Combat/Actions  [ ] Internal Thoughts  [ ] NPC Ticks  [ ] System Log      |
+----------------------------------------------------------------------------------------------------+
| VIRTUALIZED FEED (Smooth 60fps Scrolling)                                                          |
|                                                                                                    |
| 14:02:11 · TICK 142                                                                                |
| 👤 Thorne Ironbark (Player)                                                                        |
|    Action: Attacks Goblin Scout with Iron Broadsword                                               |
|    Roll:   d20 (17) + 3 = 20 vs AC 14  -> HIT! (8 Slashing damage)                                |
|    Speech: "Stand down or be cut down!" (Spoken firmly)                                            |
|                                                                                                    |
| 14:02:08 · TICK 141                                                                                |
| 👤 Goblin Scout (NPC · Hostile)                                                                    |
|    Action: Lunges at Thorne with Crude Dagger                                                      |
|    Roll:   d20 (8) vs AC 16  -> MISS!                                                              |
|    Thought: [ Frightened: HP < 30%, considering flight toward Woods ]                              |
|                                                                                                    |
| 14:01:55 · TICK 140                                                                                |
| 🌍 Environment · Eldenford Valley                                                                  |
|    Dusk falls. Ambient light drops to Dim. Temperature decreases to 14°C.                          |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Virtual DOM Windowing**
   - Replace raw DOM node appending with a virtualized list container (rendering only the 30 items currently visible in the viewport).

2. **Structured JSONL Event Store**
   - Persist events as typed JSON objects `{ tick, timestamp, actor_id, type, payload, area_id }`, keeping presentation decoupled from data.
