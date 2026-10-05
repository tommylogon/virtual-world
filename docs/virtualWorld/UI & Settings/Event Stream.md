---
type: doc
tags: [system/ui]
---

# Event Stream

The event stream is the turn-by-turn log shown on every turn (Feature Map row 56: "The turn-by-turn log with filters and search"). Its *export* is documented separately — see [[Event Log Export]].

## Architecture

The stream lives in `static/js/event-stream.js` as the `EventBus` singleton (`events`). It is the single public surface; v2 (task-340) extracted six collaborators into `static/js/stream/`:
- **stream-filters.js** — kind filters, actor/area scoping, live text search, persisted area filter
- **stream-turn-cards.js** — collapsible turn cards grouping rows by actor and phase
- **stream-scrubber.js** — timeline minimap with coloured segments and click-to-jump
- **stream-persistence.js** — IndexedDB round-trip (2000-row cap, per-world)
- **stream-control-mode.js** — Human / LLM / NPC control cycling per character
- **stream-raw-llm.js** — collapsed LLM payload chips with token meters

The `EventBus` delegates to these collaborators and emits a `'log'` event on `appEvents` (`static/js/event-bus.js`) which `turn-feed.js` subscribes to for the "since your turn" digest in the human turn panel.

## Row kinds & turn cards

Rows are classified by `className` into types: `action`, `speech`, `whisper`, `emote`, `result` (with outcome badges), `narrated`, `thought`, `reflection`, `recall`, `npc`, `crisis`, `prune`, `system`, `error`, `phase` (pills: observe/think/decide/act/react), `area-transition` (movement dividers), and `time-gap` (≥30 unlogged minutes). The `_routeToStream` method maps engine classes to these stream types and assigns actors: explicit `actor` wins, then the open turn card's actor, with system/error/recall/npc rows going to "World".

Turn cards (`StreamTurnCards`) open on `beginActorTurn` (human turns) or `logPhase('observe'|'think')` (NPC turns) and close on `user-msg`, `msg-error`, or `error-msg`. Phase markers log as pills inside the card; they do not fragment the card.

## Filters, search & area scoping

`StreamFilters.applyFilters()` hides/shows existing bubbles by:
- **Kind toggles** (`config.filterThoughts`, `filterSpeech`, `filterActions`, `filterRecalls`, `filterNpc`, `filterSystem`, `filterRawLLM`)
- **Actor dropdown** — populated from `_knownActors` as characters appear
- **Area filter** — persisted in `localStorage` (`vw_area_filter`), shows a scope banner and an empty-state note when no events match
- **Text search** — `stream-search` input filters card/row text; shows match count

The `StreamScrubber` builds a minimap of up to 120 coloured segments (teal=speech/thought, red=error/crisis, blue=action) from the current DOM, with a purple head tracking scroll position. Click anywhere to jump. Debounced rebuild on every log append.

## Persistence

`StreamPersistence` saves the stream HTML to IndexedDB (`storage.saveEventLog`) on `persist()` and restores on load. Cap is 2000 rows (DOM keeps 5000). The stream is keyed by world (`_worldKey` from scenario name or source); switching worlds drops the old log. Restore rebuilds `_lineSeq` from bubble-tick labels, rebinds card toggles, re-populates the actor dropdown, and restores the area filter.

## Stream modes

Three density modes persisted in `localStorage` (`vw_stream_mode`):
- **cards** (default) — turn cards with headers
- **compact** — same rows, no card chrome
- **story** — prose-only: strips `[wearing:…]` / `[holding:…]` gear brackets from `result`/`narrated` rows on the fly (raw text retained in `dataset.rawText` for cards/compact/export)

## Turn-queue strip

`renderQueueStrip` reads `VW.agent.turnQueue` and `currentTurnIndex`, shows the next 5 actors with the human slot marked `🎤 YOU (...)`. Positioned above the scrubber.

## SSE & backend link

The backend `engine/logging_events.py` (`GameLogger`) maintains `turn_events` (capped at 2000 per turn) and `game_log` (50 entries). `record_turn_event` writes per-turn events; `clear_turn_events` advances `turn_number`. The frontend stream is UI-side; SSE `world_changed` triggers a state poll (`GET /api/state`), and `turn-feed.js` consumes the `'log'` event for the human digest, applying viewer-scoping (same area + sound propagation from `engine/sound.py` mirrored in JS).

## Key code references

| File | Role |
|------|------|
| `static/js/event-stream.js` | `EventBus` — core, delegates, row routing, turn cards, phases, time gaps, area transitions |
| `static/js/stream/stream-filters.js` | `StreamFilters` — kind/actor/area/search, persisted area filter |
| `static/js/stream/stream-turn-cards.js` | `StreamTurnCards` — card open/close, bodyFor, collapse |
| `static/js/stream/stream-scrubber.js` | `StreamScrubber` — minimap segments, click-to-jump, scroll head |
| `static/js/stream/stream-persistence.js` | `StreamPersistence` — IndexedDB save/restore, world-keyed |
| `static/js/stream/stream-control-mode.js` | `StreamControlMode` — Human/LLM/NPC cycling via `ApiClient.updateCharacter` |
| `static/js/stream/stream-raw-llm.js` | `StreamRawLLM` — LLM request/response chips, token meters |
| `static/js/event-bus.js` | `appEvents` — tiny pub/sub for `'log'` event |
| `static/js/agent/turn-feed.js` | `TurnFeed` — viewer-scoped ring buffer, digest, sound propagation |
| `engine/logging_events.py` | `GameLogger` — backend turn_events, game_log, save_run_log |

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[event-stream|Event stream]] (#64)

**Neighbouring notes** — [[Engine Config]], [[Event Log Export]], [[Inspector Panels]], [[NL Editor]], [[Recent Edits & Undo]], [[Rendering & UI Modules]]

<!-- connected:end -->
