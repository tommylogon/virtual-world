---
type: bug
status: done
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
- [x] The rest of the stream uses the world tick too. `_nextLineLabel()` was renamed to `_tickLabel()` and now returns `Tick ${VW.state.tick} | ${tickToTime(tick)}` everywhere it is called (event-stream.ts:376, :595, :698 and stream-raw-llm.ts:53, :166), so the raw chip and its neighbours all say the same thing. The line sequence id still lives on `data-seq` and is read by the export and the persistence restore, never parsed out of the label string.

## Fixed 2026-10-21

`static/js/event-stream.ts` `_nextLineLabel` → `_tickLabel`:

```ts
// before: stamped the line sequence number into the visible label, so every
//         row said "Tick <line number>" while the raw chip said "Tick <world tick>"
// after: the visible label is the world clock tick; the sequence id is the
//        data-seq attribute, which the export and the restore read directly
_tickLabel(bubble?: HTMLElement) {
    const tick = VW?.state?.tick || 0;
    if (bubble) bubble.setAttribute('data-seq', String(this._lineSeq++));
    const time = this.tickToTime(tick);
    return `Tick ${tick} | ${time}`;
}
```

The rename is a contract, not a cosmetic one: `stream-raw-llm.ts` declares
`_nextLineLabel(bubble?: HTMLElement): string` on its `EventBusLike` interface
and calls it twice, so the old name had to go everywhere or the build failed.
Updated: the three call sites in `event-stream.ts`, the two in
`stream-raw-llm.ts`, and the interface. The persistence restore's legacy
fallback (`stream-persistence.ts:101-104`) still matches `/\[Tick\s+(\d+)\|/`,
which now means "world tick" — correct, and it only runs for pre-task-777 saves
that carry no `data-seq`.

Docs that named the old method are updated to match the new behaviour:
`docs/virtualWorld/UI & Settings/Event Log Export.md` (the "tick concepts"
section now lists three, not two, and the file/role table), and
`docs/virtualWorld/Features/export.md`.

Measured live on port 4444, `kraktooth_goblin_camp` loaded: `_tickLabel` returns
`Tick 0 | 08:00`, stamps `data-seq` 4, and all 4 `.bubble-tick` bubbles in the
stream read `[Tick 0 | 08:00]` — one meaning of "Tick" across the whole stream.

## Verified 2026-10-21 (working tree, uncommitted)

- Actor and area: `stream-raw-llm.ts:77-88` resolves the actor from
  `VW.agent.getCurrentTurnCharacter()` (falling back to
  `config.controllingPlayer`), and looks up `current_area` the same way
  `event-stream.ts:372/:693` already do. Both land on the bubble at `:47` and
  `:50` (`data-actor`, `data-stream-area`), which is what `stream-filters.ts:106-113`
  filters on.
- Tick: `_chipBubble`'s header renders `[Tick ${tick} | ${tickToTime(tick)}]`
  with `tick = VW?.state?.tick` (`:74`, `:56`), and every other row now renders
  the same thing through the renamed `_tickLabel` — see the "Fixed 2026-10-21"
  section. The line sequence id is on `data-seq` and is read by the export and
  the restore, never parsed out of the label.
- Export: `event-log-export.ts:219` sets `icon: isRaw ? undefined : ...`, so a raw
  chip's 📤 appears once, inside the header text, not twice.

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

