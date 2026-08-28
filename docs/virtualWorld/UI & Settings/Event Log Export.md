# Event Log Export & Stream Rendering

This documents the **Markdown event-log export** (`ui/world-export.js`) and the related stream
rendering/ordering improvements that were bundled with it.

---

## Event log export (📥)

The **Export** button (`WorldExport.exportEventLog()`) writes the visible event stream to a
Markdown file. Two distinct "tick" concepts live in the stream, and the export keeps them honest:

- **Event sequence (`[Tick N]`)** — a global per-line counter (`_nextLineLabel()` → `_lineSeq++`).
  This is the *run sequence id*, used in the filename.
- **World turn** — from each turn card's `[Turn N | HH:MM]` header. This is the *in-game* turn.

### Filename & header

`<scenario>_tick_<maxEventTick>_event_log_<ts>.md`. The `tick` value is the **highest `[Tick N]`
sequence id present in the stream** (scanning each row's `.bubble-tick`), falling back to the world
clock (`worldState.tick`, i.e. `time_ticks`) if the stream has no sequence labels. The header reads:

```
> Run tick <N> · final turn <M> · exported <ts>
```

So the filename matches the log's own sequence, and the world turn is called out explicitly.

### Filters are respected

The export walks the **actual bubbles/rows** (each `.msg-bubble`), not `element.textContent` of the
whole turn card. This matters because turning off a filter (e.g. **LLM logs**) hides a row with
`display: none` — and `.textContent` of a card would **still include hidden rows**. The export skips
any row whose `style.display === 'none'`, so an unchecked LLM-log filter genuinely strips the raw
prompt dumps from the file.

### Grouping & formatting

- Events are grouped under **`## Turn N — actor · HH:MM`** headings (read from each turn card's
  header), rather than the old `## Tick N` derived from a first-`[Tick]` match (which never matched
  its own content and produced non-monotonic headings).
- Each event is **one bullet** (`- icon actor — text`), with newlines preserved (grabs the
  `.bubble-text` / phase-pill text, not glued `.textContent`). No more `Use🎭[Tick 14]`-style glue.
- System rows / area transitions that sit directly in the stream get a `## Setup` section or their own
  bullets rather than being swallowed into a card.

---

## Stream rendering changes

### Newlines preserved (`static/css/style.css`)

`.bubble-text` now uses `white-space: pre-wrap`. Room descriptions and other multi-line output carry
real `\n` (the engine renders them, JSON preserves them, `_escapeHtml` keeps them) — the browser was
collapsing them into one wall of text. `pre-wrap` renders the line/section breaks.

### Act emote before result (`static/js/agent-engine.js`)

The emote a character declares alongside an action is now executed/logged **before** the action
result, so the turn reads **gesture → outcome** instead of **outcome → gesture**. This applies to both
the agent decide phase and the human-turn reply path. It was previously logged after the result.

---

## Export source

| File | Role |
|------|------|
| `static/js/ui/world-export.js` | `exportEventLog`, `buildMarkdownLog`, filename/header, `saveFileWithDialog` |
| `static/css/style.css` | `.bubble-text { white-space: pre-wrap }` |
| `static/js/agent-engine.js` | emote-before-result ordering |
| `static/js/event-stream.js` | `_nextLineLabel`, `_addBubble`, `_escapeHtml` (sequence labels, per-row text) |

## Related

- [[dev_tasks/review/ui/task-340-event-stream-v2|task-340: Event stream v2]]
- [[dev_tasks/todo/testing/task-347-export-log-lint-guards|task-347: Export log lint guards]]
