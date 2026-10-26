---
type: doc
tags: [system/ui, topic/validation]
---

# Event Log Export & Stream Rendering

## What you can do

Take the log with you. The event stream exports to **Markdown**, **plain text**,
**JSON** and **JSONL** — all four projected from the same DOM rows and all driven
by one export modal, so what you read on screen is what lands in the file. Use
Markdown or plain text to hand a session to someone; use JSON/JSONL to feed a
tool.

The event stream exports to **Markdown**, **plain text**, **JSON** and **JSONL**, all projected from
the same DOM rows and all driven by one export modal. The projection, the four renderers and the
modal live in `ui/event-log-export.js`; `ui/world-export.js` keeps `saveFileWithDialog` and delegates
the three header buttons into it, so the `WorldExport.*` surface is unchanged.

---

## The three buttons and the modal (📥 ⏩ 📋)

All three header buttons open the same modal, pre-set:

| Button | Opens the modal as |
|---|---|
| 📥 **Export event log to file** | whole log · destination *Save to file* |
| ⏩ **Export a range** | range controls focused |
| 📋 **Copy event stream** | whole log · destination *Copy to clipboard* |

The modal owns: **unit** (Tick sequence — the default — or Turn), **From / To** bounded by what the
stream actually contains, an **actor** multi-select (fed from the roster of names the stream has
seen), an **area** select (fed from the areas present in the stream), a **format** (Markdown / Plain /
JSON / JSONL), a **destination** (Save to file / Copy to clipboard), an **Ignore stream filters**
escape hatch, and a live summary line — for example:

```
ticks 12–340 | Lyrie | Goblin Camp | 412 events | jsonl | filters applied
```

The summary is the point: it names the unit, the bounds, the scope and the active filters *before*
you click, so an export can never silently drop the LLM payloads, an actor or a whole area.

A clipboard copy over ~2 MB prompts first — some browsers refuse a write that large.

### Three "tick" concepts, kept honest

- **Run sequence id** — `data-seq`, stamped on every bubble by `_tickLabel()`.
  This is the *run sequence id* and the default **range unit**. It is an
  attribute, not a visible label: the export and the persistence restore read
  it directly, never re-parse the label string.
- **World clock tick** (`[Tick N]`) — the visible label on every row, from
  `VW.state.tick`. It is a per-row field (`tick`); it is *not* a range unit.
- **World turn** — from each turn card's `[Turn N | HH:MM]` header. Selectable as the range unit.

### Filename

`<scenario>_<unit>_<from>-<to>_event_log_<ts>.{md,txt,json,jsonl}`.

---

## The event record

Every exported event is one record:

```
{ seq, tick, time, day, turn, actor, area, type, text, icon?, outcome?, payload?, actor_id?, request_id?, phase? }
```

- `seq` — the tick-sequence id (the range key), stamped as `data-seq` on the row when its label is
  emitted; the projection falls back to parsing `[Tick N]` for rows saved before task-777.
- `tick` — the world clock (`data-tick`); `time` and `day` come from the row's label and its turn card.
- `turn` — the enclosing turn card's number, or `null` for a loose row (a system row, a time gap, an
  area transition).
- `actor` / `area` — `data-actor` / `data-stream-area`.
- `type` — `data-type` (`speech`, `action`, `thought`, `result`, `rawllm`, `error`, `phase`,
  `stream`, …) or a synthetic `scope` / `scope-empty` / `system`.
- `text` — the **raw** text (`dataset.rawText`), not the story-mode-stripped `.bubble-text`.
- `outcome` — from the `outcome-*` class on a result row. `payload` — `{ header, body }` on a raw-LLM
  chip; the collapsed body is read regardless of its `display: none`, which is a *collapse*, not a
  filter.
- `actor_id` / `request_id` / `phase` — trace correlation, present on LLM rows and absent elsewhere.
  `actor_id` is the character the call was **for** (`data-actor-id`), which is not always the same as
  the `actor` display label: a prompt written for one character used to be filed under whichever
  character held the turn. `request_id` (`data-request-id`) is shared by a request chip and its
  response chip, so a pair can be correlated without relying on ordering. `phase` (`data-phase`) is
  the turn phase that produced the call (`plan`, `think-decide`, `result-reaction`, …).

Rows with no tick — the scope banner, a scope-empty note, a time gap, an area transition — carry
`seq: -1` and appear in Markdown/Plain only; JSON and JSONL are the ticked events alone.

### Markdown & Plain

Markdown groups events under `## Turn N — actor · HH:MM · Day D, …` and emits one bullet per event
(`- icon actor — text`); a raw-LLM chip becomes a `<details>` payload block. Plain is the bare lines.
The scope banner is its own message (`> **📌 Scoped to: …**`): the projection reads the banner's label
span, never its container `textContent`, so the clear button's `×` is not glued on, and a turn heading
ends with the game time, not a stray `]`.

### JSON & JSONL

**JSONL** is one record per line with no envelope, so `jq` works directly:

```
jq 'select(.actor=="Lyrie")' run.jsonl
jq -s 'group_by(.actor) | map({actor: .[0].actor, n: length})' run.jsonl
```

**JSON** is an envelope, so a reader can detect shape drift instead of guessing:

```json
{
  "schema": 1,
  "scenario": "goblin_camp",
  "exported_at": "2026-10-11T19:40:00.000Z",
  "world_tick": 42,
  "range": { "unit": "tick", "from": 12, "to": 340 },
  "filters": { "actor": "Lyrie", "area": null, "search": "", "ignored": false, "kinds": {} },
  "counts": { "events": 412, "turns": 6, "actors": 3, "areas": 4 },
  "events": []
}
```

---

## Filters are respected

The projection walks the actual rows (each `.msg-bubble`), not a container's `textContent`. Rows the
stream filters hide (`display: none` — the kind chips, the actor dropdown, the area filter, the search
box) are skipped, and the modal's summary names them. The **Ignore stream filters** checkbox is the
explicit escape hatch. The `timeline-scrubber` and `turn-queue-strip` are stream chrome (a live status
widget, not a message) and are skipped; the scope banner is a message and is kept.

---

## Play Mode is a boundary, not a filter

Stopping Play Mode reverts the world to its authored snapshot. The stream follows: the moment Play
Mode starts, the authored rows are parked and the stream starts empty for the run. Everything logged
while playing (turns, results, LLM payload chips, area dividers) belongs to a world that Stop throws
away, so Stop discards those rows and puts the parked log back exactly as it was - same rows, same
open turn card, same scroll position. The "Stopped Play Mode" line is written after the restore, so it
lands in the authored log rather than in the run being discarded.

The parked log is a client-side snapshot (the detached DOM nodes, not re-rendered HTML, which keeps
turn-card collapse handlers, raw-LLM chips and choice buttons alive). Two consequences:

- Reloading the page while still in Play Mode loses the parked log, because the browser owns it and
  the server does not. The run's rows are then what you have; Stop still reverts the world.
- A world load or a "new scenario" inside Play Mode discards the parked log deliberately
  (`clearAll()` calls `StreamSandbox.discard()`); restoring the old world's rows into a new world
  would be a lie.

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

---

## Standalone CLI reader (`tools/stream_read.cjs`)

Query an exported event-stream JSON or JSONL run without running the app or server (task-778).

```bash
# Timeline output (default)
node tools/stream_read.cjs run.jsonl

# Filter by actor, area, type, and tick sequence range
node tools/stream_read.cjs run.jsonl --actor Lyrie --area "Camp Entrance" --type action --from 0 --to 50

# Output matching events as JSON
node tools/stream_read.cjs run.jsonl --actor Lyrie --from 0 --to 50 --json

# Summary mode: per-actor, per-area, and per-type event counts
node tools/stream_read.cjs run.jsonl --mode summary
node tools/stream_read.cjs run.jsonl --mode summary --json

# Raw JSONL mode: stream matching JSON lines
node tools/stream_read.cjs run.jsonl --actor Lyrie --mode raw
```

Options:
- `--actor <name>`: Filter by actor name (case-insensitive)
- `--area <name>`: Filter by area name (case-insensitive)
- `--type <type>`: Filter by event type (`speech`, `action`, `system`, `thought`, etc.)
- `--from <seq>`: Minimum tick-sequence number (inclusive)
- `--to <seq>`: Maximum tick-sequence number (inclusive)
- `--mode <mode>`: Output mode: `timeline` (default), `summary`, `raw`
- `--json`: Output results in JSON format
- `--help`, `-h`: Show usage instructions

Exit codes: `0` = success, `2` = usage or file I/O error.

---

## Export source

| File | Role |
|------|------|
| `static/js/ui/event-log-export.js` | projection (`projectStreamRows`), renderers (Markdown/Plain/JSON/JSONL), the export modal, range/scope honesty |
| `static/js/ui/world-export.js` | `saveFileWithDialog`; delegates `exportEventLog` / `copyEventLogToClipboard` / `showRangeExport` into the module |
| `static/js/event-stream.js` | `_tickLabel` (stamps `data-seq`, shows the world tick), `_addBubble`, `_escapeHtml` (per-row text) |
| `static/js/stream/stream-persistence.js` | restore reads `data-seq` (with a `[Tick N]` fallback for pre-task-777 saves) |
| `static/css/style.css` | `.bubble-text { white-space: pre-wrap }` |
| `static/js/agent-engine.js` | emote-before-result ordering |

## Where it lives

- `static/js/ui/event-log-export.js` (projection, four renderers, export modal, range/scope controls)
- `static/js/ui/world-export.js` (`saveFileWithDialog`, header button delegation)
- `static/js/event-stream.js` (`_tickLabel` stamps `data-seq` and shows the world tick, `_addBubble`, `_escapeHtml`)
- `static/js/stream/stream-persistence.js` (restore reads `data-seq` with `[Tick N]` fallback)
- `static/js/stream/stream-sandbox.js` (parks/restores the authored stream across a Play Mode run)
- `static/css/style.css` (`.bubble-text { white-space: pre-wrap }` preserves newlines)
- `static/js/agent-engine.js` (emote-before-result ordering in agent decide phase and human-turn reply)
- `templates/index.html` (event stream header buttons: 📥 ⏩ 📋)

## Related

- [[task-340-event-stream-v2|task-340: Event stream v2]]
- [[dev_tasks/todo/testing/task-347-export-log-lint-guards|task-347: Export log lint guards]]

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[export|Export]] (#65)

**Neighbouring notes** — [[Engine Config]], [[Event Stream]], [[Inspector Panels]], [[NL Editor]], [[Recent Edits & Undo]], [[Rendering & UI Modules]]

<!-- connected:end -->
