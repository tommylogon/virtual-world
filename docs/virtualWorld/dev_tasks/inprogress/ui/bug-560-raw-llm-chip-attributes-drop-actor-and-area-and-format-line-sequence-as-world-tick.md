---
type: bug
status: inprogress
area: ui
priority: medium
related: ['task-777', 'task-779']
wiki: "[[Features/event-stream]]"
---

# bug-560: raw llm chip attributes drop actor and area and format line sequence as world tick

**Filed:** 2026-10-21  
**Area:** ui / stream  
**Priority:** Medium  

## What

Raw LLM request chips created in `StreamRawLLM.logRequest` (`static/js/stream/stream-raw-llm.ts`) hardcode `actorLabel` to `'LLM'` and `areaName` to `''`. When filtering the Event Stream by an active character or area, all raw prompt chips disappear. In addition, `_nextLineLabel()` formats the chip header with `seq` (the stream line number) as `[Tick <seq>]`, displaying e.g. `[Tick 12]` when `world_tick` is actually 1. Finally, JSON log export duplicates the send icon as `📤 📤`.

## Steps to Reproduce

1. Trigger an agent turn for Arix in Food Storage.
2. Filter the Event Stream by actor "Arix" or area "Food Storage".
3. Observe that raw LLM chips are hidden because `data-actor="LLM"` and `data-stream-area=""`.
4. Export event log: observe double icons (`📤 📤`) and label showing `Tick 12` on world tick 1.

## Acceptance

- [x] `StreamRawLLM.logRequest` receives and records the active character name and area on the bubble elements.
- [x] JSON export normalizes icon extraction so chips do not double-dip icons.
- [x] The raw request chip header uses `VW.state.tick`, not `seq`.
- [ ] The rest of the stream: `_nextLineLabel()` (`static/js/event-stream.ts:340-344`) still returns `Tick ${seq}` from the line counter, and the thought, action/result, phase and parse-error rows all use it. So a raw chip now shows the world tick while every neighbouring row shows a line number labelled "Tick". One of the two must change.

## Verified 2026-10-21 (working tree, uncommitted)

- Actor and area: `stream-raw-llm.ts:77-88` resolves the actor from
  `VW.agent.getCurrentTurnCharacter()` (falling back to
  `config.controllingPlayer`), and looks up `current_area` the same way
  `event-stream.ts:372/:693` already do. Both land on the bubble at `:47` and
  `:50` (`data-actor`, `data-stream-area`), which is what `stream-filters.ts:106-113`
  filters on.
- Tick: `_chipBubble`'s header now renders `[Tick ${tick} | ${tickToTime(tick)}]`
  with `tick = VW?.state?.tick` (`:74`, `:56`), instead of `_nextLineLabel`.
- Export: `event-log-export.ts:219` sets `icon: isRaw ? undefined : ...`, so a raw
  chip's 📤 appears once, inside the header text, not twice.
- The inconsistency above is measurable in the same file: `_nextLineLabel` is
  still called by `event-stream.ts:376`, `:595`, `:698` and
  `stream-raw-llm.ts:166`.
- **Remaining:** the `_nextLineLabel` decision (rename the label, or make it show
  the world tick everywhere), and a committed change. No live agent turn was run.

## Browser UI and intended live verification

UI home: the `📤` request and `🤖` response chips in the event stream, the actor
dropdown in the stream toolbar, the area scoping that opening an area applies,
and the `📥` event-log export.

1. Settings -> Agent Settings -> enable `🔬 Show Raw LLM`; make one LLM call.
2. Read the `📤` chip header. It is `[Tick <n> | <game time>] LLM → <phase>`;
   the actor is not displayed, it lives in `data-actor` (the phase is the visible
   label). The chip must stay visible when the actor dropdown
   (`#stream-agent-filter`, "All actors") is set to the acting character.
   - check `data-actor` with the console dump in step 6. If it reads `LLM`, the
     `getCurrentTurnCharacter()` / `config.controllingPlayer` fallback missed and
     the actor filter will hide the chip. That is the failure this card is about.
3. Click the character's area node in the graph to open it in the inspector.
   Opening an area scopes the stream to it (`area-view.ts:171`).
   - expected: the raw chip for that area stays visible. Before the fix its
     `data-stream-area` was empty, so area scoping hid it.
4. Compare the tick label with its neighbours. The raw chip prints the world
   tick; the thought/action/system rows still print `Tick <line number>` from
   `_nextLineLabel()`.
   - expected: one meaning for `Tick` across both.
5. Click `📥`, open the exported JSON, and find the raw record.
   - expected: `actor` and `area` are populated, `payload.header`/`payload.body`
     carry the request, and the icon is not duplicated.
6. Read-only console dump of the last three raw chips:
   ```js
   [...document.querySelectorAll('.msg-bubble-rawllm')].slice(-3).map(b => ({
     actor: b.dataset.actor,
     area: b.dataset.streamArea,
     tick: b.dataset.tick,
     header: b.querySelector('.rawllm-chip-header').innerText
   }))
   ```

