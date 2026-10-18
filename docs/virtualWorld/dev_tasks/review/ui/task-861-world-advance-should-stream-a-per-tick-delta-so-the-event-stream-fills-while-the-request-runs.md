---
type: task
status: review
area: ui
priority: high
horizon: now
effort: M
wiki: "[[UI & Settings/Event Stream|Event Stream]]"
related: [task-860]
---

# task-861: World advance should stream a per-tick delta so the event stream fills while the request runs

**Filed:** 2026-10-18
**Related:** task-860

<!-- deps:start -->
**Related:** [[task-860-pursuit-drive-harness-one-tick-http-driver-world-share-facts-for-the-timeskip-lane]]
<!-- deps:end -->

## What

A world advance runs its whole tick loop inside one blocking POST and tells the client nothing until it returns, so a 60-minute jump is 30 seconds of dead air followed by one 9 MB state fetch. Make the advance publish a compact per-tick delta on the live hub so the event stream fills turn by turn while the request is still in flight, and keep exactly one state fetch at the end to settle the graph.

## Why

Measured 2026-10-17 on the live :4444 world: `POST /api/world/timeskip {minutes:60, world:true}` returned in 30138 ms across 12 ticks (about 2.5 s per tick), zero LLM calls. The only signal the client gets is the `after_request` hook publishing a single `world_changed` (`app.py:252-270`), which triggers one `/api/state` fetch. That fetch costs 9.09 MB / 4892 ms, and even `?lite=1` costs 3.72 MB / 4219 ms, so refetching state per tick is not an option: 12 of them would add roughly 50 s and re-render graph plus inspector twelve times. The data for a fast-forward already exists and is small: `turn_events` entries carry `tick`, `actor`, `action`, `description` and `area` (`logging_events.py:96-103`), and `engine/world_events.py` already exposes a process-global `hub` with a non-blocking `publish()` and an SSE route (`routes/events.py:15-34`) that the client holds open unconditionally (`world-state.ts:540-576`). What is missing is the wiring from the tick loop to that hub, and a client branch that consumes it.

## How

Engine: give `timeskip.advance_world` an optional `on_tick` callback and call it after each `tick_turn` with a delta `{tick, clock, events, truncated}`; `events` is the `turn_events` slice past a cursor held across the loop (a buffer that shrank under the cursor is handed over whole, so a prune cannot skip a fact), capped at `TICK_FRAME_MAX_EVENTS` = 60 so one busy tick cannot overflow the 256-deep SSE queue, and the callback is wrapped in try/except so a dead listener can never break an advance. The cursor is seeded to the buffer's existing size, not 0, so a chunked long span never replays the previous chunk.

Route: the world branch of `routes/timeskip_ops.py` passes `_publish_tick`, which publishes `{'type': 'world_tick', ...}` on `engine.world_events.hub`.

Client: `world-state.ts` `connectLiveEdits` handles `world_tick` by appending each event as an actor-attributed `msg-action` row through the existing EventBus, with a `⏩ Fast-forwarding the world` marker on the first frame and `⏩ Fast-forward complete.` when the settle signal arrives. There is deliberately no state fetch on that path: `/api/state` remains the single source of truth for clock and graph, and the frames are only a projection of `turn_events`.

## Browser UI and intended live verification

Intended UI home: the event stream, which now fills during the advance. Live path: Ctrl+K, "Advance World", 60 minutes; rows arrive per tick, attributed to the character who acted, then the toast and one settle fetch. Verified on a scratch worktree instance on :4445 (the live :4444 needs a restart to load the new engine and route code).

## Steps to verify

1. Run a 60-minute Advance World against an instance carrying the new code, with a MutationObserver on `#event-stream` and the POST unresolved.
   - expected: rows arrive progressively during the request, and the advance still reports `mode: world` with 12 ticks.
   - observed: row count climbed 9 -> 70 at ms 64, 109, 111, 112, 116, 120, 123 and 124 while the POST did not resolve until ms 224. Response: `mode "world"`, `ticks 12`, `elapsed_minutes 60`, `clock_after "09:15:00"`. Rows were attributed (`rat :: entered the Upstairs Hallway through the hallway`, `Kaelen Voss :: left the Living Room through the stairs`), opened by `⏩ Fast-forwarding the world` and closed by `⏩ Fast-forward complete.`, after which the clock widget read `🕐 09:15`.
2. `python -m pytest tests/test_timeskip.py` and `python tools/ts_convert.py check`.
   - expected: all pass, including the new per-tick callback tests; the front-end gate passes.
   - observed: `62 passed`. Gate: `build:ts` ok, `typecheck` ok, `lint` ok, `header survival` ok (175 files), `window guards` ok (18 reviewed). `module:check` and `unit` fail only on the pre-existing names (the 7 engine modules with no `@module`; `736 passed, 4 failed` - the two `test_turn_prompts.js` em-dash expectations, `test_worldpainter.js` dash, `test_graph_tuning.js` node size), identical to the HEAD baseline.

## Acceptance

- [x] A world advance publishes a per-tick delta on the existing hub; no new event store and no per-tick state fetch.
- [x] The event stream fills while the request is in flight, and one state fetch at the end still settles clock and graph.
- [x] A subscriber that is slow, full or absent cannot break or stall the advance (`hub.publish` is `put_nowait` with the drop swallowed; the listener call is wrapped; pinned by `test_a_failing_tick_listener_cannot_break_a_world_advance`).
- [x] `advance_world` stays callable without a listener (the parameter is keyword-only and defaulted), and the existing world/character/soak modes are unchanged (`test_the_world_flag_forces_a_world_advance_with_an_active_character` still passes).

## Files

- `engine/timeskip.py` (`advance_world`: `on_tick`, `_tick_delta`, `TICK_FRAME_MAX_EVENTS`)
- `routes/timeskip_ops.py` (`_publish_tick`; world branch passes `on_tick`)
- `static/js/world-state.ts` + emitted `.js` (`connectLiveEdits`: consume `world_tick`)
- `tests/test_timeskip.py` (three new tests)
