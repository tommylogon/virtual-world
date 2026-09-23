---
type: task
status: todo
area: items
priority: medium
---

# task-433: Agent-reachable inscription (task-53 follow-up)

**Filed:** 2026-09-21
**Builds on:** [[dev_tasks/review/items/task-53-use_item_with_parameters|task-53]]
(Use Item with Parameters — `use pen on paper "text"` → `on_use_on` →
`set_description`/`append_description`, `{params}` templating; **implemented,
In Review**).
**Relates:** task-160 / task-363 (structured actions; stopping *accidental*
inscription), task-299 (long-distance communication — letters), task-423
(background social interactions), task-403 (unified memory/knowledge).

## Why this exists

task-53 built the **engine half**: a quoted `use <tool> on <target> "<text>"`
carries `params` into the `on_use_on` trigger context, and effects can render
`{params}` (plus the hardcoded `[Inscribed: …]` description append at
`engine/items/use_actions.py:266-277`). That works for an authored human-driven
pair.

What task-53 does **not** cover is everything needed for characters to do it on
their own, intentionally, in a world that can then read it back. Verified
2026-09-21:

1. **No agent can reach it.** The LLM emits a structured action
   `{action, item, target, speech, emote, …}` with **no text field**
   (`static/js/agent/prompt-builder/system-prompt.js`,
   `agent/action-normalizer.js`), so it can only produce `use <tool> on
   <target>` — never a `params`. The tool path
   (`tools/game_tools.py:224`) calls `use_item_on(item_name, target)` with no
   `params` either.
2. **It is un-gated and accidental.** task-160/363 document
   `use create flame on dried flower crown` *inscribing* "flower crown" onto a
   crown because `"flower crown"` was quoted. Nothing checks that a tool is a
   writing implement or a target is writable. task-53's path inherits this.
3. **`{params}` only works where a trigger exists — none does.** No authored
   `ink_pen`, `parchment`, `pencil`, `journal`, `notebook`, `letter`
   (`data/library/items/`) or the Ink Pen/Parchment in `The Valerious Case.json`
   carries an `on_use_on` trigger. The capability has no content using it.
4. **`set_description` overwrites, and targets a literal node id.**
   `engine/effect_handlers/properties.py:71-109` — the value is rendered, but
   the target is a literal node id ("self" fails), so generic "the paper in my
   hand" is not expressible. Overwriting `description` is also lossy: no
   author, no tick, no structure, mixed with authored prose.
5. **Reading back is unaddressed.** `read` is still an `examine` alias
   (`routes/action_handlers.py:217-220`); there is no inscription block or
   `read`-prioritises-note behaviour.
6. **Narration does not persist, and should not.** When the LLM narrates "she
   scribbles 'DONT GO HERE' on the paper", that prose is browser-only
   (`static/js/narration-ui.js:209-232`, `static/js/agent-engine.js:650-663`,
   IndexedDB in `static/js/stream/stream-persistence.js`) — never POSTed, never
   serialized.

## Design (the delta only)

1. **Agent reachability.** Add a `text` field to the structured action schema,
   teach it in the system prompt, and have the normalizer emit an
   unambiguous inscription form (an `inscribe`/`write` verb, or
   `use <tool> on <target>` carrying `text`). Forward it on the tool path.
2. **Gating, so it is deliberate.** Require the target to be writable
   (`writable`/`paper`/`book`/`sign`/`wall`) and the tool to be a writing
   implement (`pen`/`pencil`/`quill`/`charcoal`/`chalk`). Ordinary
   `use X on Y` must never inscribe (keeps task-363 fixed).
3. **Authoring parity + content.** Ship real pen/paper/noticeboard items with
   the trigger, so the mechanism has something to drive.
4. **Structured store.** Prefer `properties.inscriptions: [{by, tick, text}]`
   over overwriting `description`; render a "Written here:" block on
   `examine`. Keep the legacy `[Inscribed: …]` string readable (or migrate it).
5. **Read-back.** Decide whether `read` stays an alias with an inscription
   block, or becomes a first-class verb that surfaces notes first.
6. **Limits.** Max length, control-char stripping, cap per item, author+tick.
7. **Narration stays flavor** — never commit world state from narrated prose.

## Acceptance

- An LLM agent inscribes chosen text onto a writable item with a writing tool;
  it persists in `Node.properties` and survives save/load.
- A different character `examine`/`read`s it and sees text, author, and tick.
- Non-writable target / non-writing tool reject gracefully.
- Ordinary `use X on Y` never inscribes (task-363 regression stays green).
- An authored pen+paper pair works end to end (task-53 path retained).

## Non-goals

- Re-implementing task-53's params/trigger plumbing.
- Rich text, images, forgery, signatures.
- A world-wide message board (task-299).
