---
group: UI
---

# Event Stream Redesign — Turn Cards, Structured Events, LLM Chips

**Filed**: 2026-08-05
**Priority**: Medium
**Status**: Design — demo built, not implemented

---

## Goal

The event stream currently renders every event as a flat, emoji-prefixed `innerHTML` bubble — a rigid chat room, no visual hierarchy, no grouping, no interaction. This task turns it into a structured timeline UI component while preserving what the current system does well: **density, global-time ordering, live streaming feedback, and universal logging**.

## Working Demo

`docs/design/event-stream-demo.html` — standalone HTML mockup grounded in REAL engine data (actors + trigger strings from `data/scenarios/mansion.json`, skill-check format from `engine/skills.py`, hearing narration from `engine/sound.py`). Run: `python -m http.server 8765 --directory docs/design` → `http://127.0.0.1:8765/event-stream-demo.html`.

## ⚠️ The stream is a UNIVERSAL LOG, not just an agent feed

**234 `events.log()`/`logPhase()`/`logThought()` callsites across 27 files** feed the stream. The demo only modeled the LLM agent turn flow. Any redesign must account for ALL of these, or it will lose/break them:

### Category map of what flows in (from full audit 2026-08-05)

| Category | Emitters | Examples |
|----------|----------|----------|
| **Agent turns** | `agent-engine.js` | phase markers, thoughts, speech, action, result, emote, raw LLM, plan/replan, invalid-action, LLM errors |
| **User commands** | `main.js:771-777`, `main.js:545` | `> command` (user-msg), command output, system_messages |
| **Manual mode** | `main.js:655-660` | "Manual response injected!", clipboard warnings |
| **Guest speech** | `main.js:606` | `[Name] says: "..."` (msg-speech) |
| **NPC turns** | `agent-engine.js:140,150` | "👾 X's turn — acting autonomously", NPC action logs |
| **Rest / unconscious / dead** | `agent-engine.js:160-187` | ⏳ resting, 💤 unconscious, 🌅 woke up, ⏭️ dead |
| **Graph editing** | `graph-manager.js`, `graph/node-operations.js`, `graph/event-handlers.js`, `graph/context-menu.js`, `graph/network-manager.js` | create/move/delete/duplicate nodes+edges, edge type change, overlays |
| **Character CRUD** | `main.js:92-127`, `inspector/agent-view.js` | created/deleted/active character, kill, remove |
| **Item/library ops** | `item-library.js`, `library-browser.js`, `inspector/item-view.js`, `item-library/placement.js`, `item-library/contents-editor.js` | placed items, moved into container, refreshed from library, saved to library |
| **Way/area save** | `inspector/way-view.js`, `inspector/area-view.js` | saved/updated/duplicated way, AI-improved area |
| **Save/load/reset** | `ui/saveload-view.js` | world loaded, scenario saved, game saved/loaded/deleted, reset, time-per-tick |
| **AI generation** | `main.js:214,324,394-396`, `inspector/agent-view.js:894`, `item-library/ai-generation.js` | "AI generated personality/item/area/way", mock fallback, failures |
| **Narration** | `narration-ui.js:189,217` | `[AI Narration] ...` |
| **Memory/reflection** | `agent/memory-manager.js:68` | 🧠 reflected on N memories |
| **Settings/streaming toggles** | `ui-controller.js:250,257` | LLM logs ON/OFF, Streaming ON/OFF |
| **Settings/config saves** | `config.js` | "Settings saved.", profile operations |
| **API output passthrough** | `api.js:393` | raw `data.output` as system-msg |
| **Event log tools** | `ui/world-export.js` | copied/exported stream, prompt copy |
| **Ghost mode** | `main.js:800` | "👻 Ghost mode activated/deactivated" |
| **Init** | `main.js:835` | "VirtualWorld Engine initialized" |

### className variants in use (from grep of all emitters)
`'system-msg'`, `'error-msg'`, `'msg-speech'`, `'msg-action'`, `'msg-thought'`, `'msg-emote'`, `'user-msg'`, `'agent-msg'` — plus `logPhase` (phase markers) and `logThought`.

## 🔑 Critical constraint: the stream is the DATA BACKBONE, not just display

`EventBus` maintains internal state consumed by prompts and inspectors. A redesign must keep this state machinery intact:

- **`_characterState`** — `lastThought`, `lastSpeech`, `lastAction`, `actionHistory` (20 cap), `detailedTimeline` (100 cap), `lastActionResult`. Consumed by:
  - `prompt-builder.js:223` — agent's own last thought feeds its prompt
  - `plan-manager.js:49` — lastThought for plan context
  - `inspector/agent-view.js:43,521,692,1160` — decision trace + detailed timeline UI
  - `main.js:563-564` — actionHistory detail view
- **`_areaEventLog`** — per-area event list (50 cap). Consumed by:
  - `prompt-builder.js:765` — witnessed events in the LLM prompt (`getAreaEvents`)
  - `inspector/area-view.js:72` — room events in area inspector
- **`log()` emits a pub/sub event** (`this.emit('log', {text, className})`, event-stream.js:84) — external subscribers exist; must not break.
- **`restoreLog()`/`_persistLog()`** — IndexedDB round-trip of last 500 bubbles every 5s; survives refresh.

**Design implication:** the visual bubbles are a *projection* of state that is ALSO used for prompts and inspectors. We can re-skin the DOM and add metadata, but `trackAction`/`logThought`/`logAreaEvent`/`_recordPhase` must keep populating the same structures — the LLM prompt and inspector depend on them.

## Current Architecture (code audit)

- `EventBus` (static/js/event-stream.js) — `log(text, className)` emits raw strings; every bubble is self-built `innerHTML`, classname doubles as type + filter key.
- `_routeToStream()` (186-217) maps classnames → types; `_addBubble()` (225) builds DOM.
- Streaming: `startStreaming(id)`/`appendStream(id, chunk)`/`finishStreaming(id)` — per-call spans (task-117 fix).
- `logPhase(charName, phase)` = turn boundary anchor — **reactive mode only** (`agent-engine.js:203,251,273,340`); **non-reactive mode emits no phase markers**.
- No click handlers on bubbles. No `data-node-id`/`data-turn-id`. No search. DOM capped `MAX_LINES = 5000`; IndexedDB last 500.
- **XSS bug**: `logThought` (:129) + `_addBubble` (:233) interpolate LLM text into `innerHTML` unescaped. Only rawLLM paths escape (:293, :320). Must fix regardless.
- `tickToRelative()` used by memory system (`memory-manager.js:36`, `prompt-builder.js:259,281`) — NOT dead; just unused in stream UI.

## Proposed Design

### 1. Turn Cards (grouping) — for AGENT turns only
- Group agent turn events into a `turn-card` (actor color border + header, clickable name, timestamp).
- Anchor: `logPhase('think')` = turn start (reactive). **Add non-reactive anchor** (none today).
- **Editor/ops/system events (graph edits, saves, settings, commands) do NOT belong in cards** — they're actor-less and interleaved. They stay flat rows. Design must branch: card-worthy (agent turns) vs flat (everything else).

### 2. Message rows (semantic classes)
- `.msg-thought` · `.msg-speech` · `.msg-action` · `.msg-result` · `.msg-error` · `.msg-emote` · `.msg-user` · `.msg-system` · `.msg-heard` · `.msg-env` · `.msg-trigger`.
- **Skill badges**: parse `[Skill Check] ... => success/failure` from `data.output` into `.skill-badge` chips. (Structured API result would be more robust — decision needed.)
- **Density mode toggle**: cards for review, PLUS a compact single-line mode (current look) for live monitoring. Cards cost 2-3x vertical space; a 9-char sim needs the dense option.

### 3. LLM chips (request + response)
- Two collapse-to-expand chips: `📤 LLM Request · think-decide` + `🤖 LLM Response · 450 tokens`, replacing the live raw stream bubble + rawLLM bubble.
- Keep a live "🧠 X is thinking..." pulsing chip during streaming.
- **Trade-off to preserve**: current version shows raw tokens ticking out live = "it's alive" feedback. Chips hide that. Consider: chips auto-expand during the active stream, collapse after.

### 4. Interactivity bridges (APIs already exist)
- `VW.inspector.showNode(nodeId)` / `showAgent(name)` / `selectAgent(name)` — click actor → inspector (pattern exists in graph-manager vtree).
- Requires embedding `data-node-id`/`data-actor` on bubbles at render time.

### 5. XSS fix (must-do regardless)
- Escape LLM-derived text in `logThought` + `_addBubble` via existing `_escapeHtml()`.

### 6. Ordering toggle
- Flat-chronological (current, default — preserves global sim order) vs group-by-actor cards. Multi-agent simultaneity is real; cards can misrepresent it. Keep both, toggleable.

### 7. Search & scroll (optional / follow-up)
- Text search box. Auto-scroll stays manual toggle (no scroll-up detection today). Reconsider 5000-node cap.

## Files to touch (implementation)

- `static/js/event-stream.js` — renderer rework (cards, chips, badges, escaping, metadata attrs); KEEP `_characterState`/`_areaEventLog`/pub-sub/restore-persist machinery
- `static/js/agent-engine.js` — non-reactive turn anchor; pass actor/phase metadata
- `static/js/llm-client.js` — expose request messages for chips (already logged via `logRawLLMRequest`)
- `static/css/style.css` — new card/chip/badge/dense-mode classes
- `templates/index.html` — filter bar + density/ordering toggles + search box

## Decisions to confirm with Tommy

- [ ] Aesthetic reference (Disco Elysium / Linear / terminal hybrid — he picks)
- [ ] Raw LLM: auto-expand during stream then collapse, or hidden always?
- [ ] Skill badge parsing: string-match `data.output` vs structured API result?
- [ ] Card grouping: only agent turns in cards, all editor/ops flat — agree?
- [ ] Density + ordering toggles: both default to current behavior?
- [ ] Search box: now or later?
- [ ] 5000-node cap acceptable, or virtualize for full back-scroll?

## Verification (when implemented)

- [ ] `node --check` on touched JS
- [ ] Backend suite passes (no engine changes expected)
- [ ] All 27 emitter files still render correctly (spot-check each category above)
- [ ] Prompts + inspector timeline unchanged (getCharacterState/getAreaEvents still populated)
- [ ] Browser E2E: 2 agents reactive — turns grouped, chips toggle, actor click opens inspector, editor ops render flat, no console errors
- [ ] Manual XSS test: inject `<img onerror>` in a thought → must render escaped
- [ ] Refresh mid-run: IndexedDB restore still works with new bubble structure
