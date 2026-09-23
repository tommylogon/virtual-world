---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---

# Use Item with Parameters (Text/Message Passing)

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: In Review — implemented (code-verified 2026-08-11; re-audited against
current code 2026-09-21).
**Residual work**: [[dev_tasks/todo/items/task-433-character-inscription-persistent-notes|task-433]]

---

## Summary

Items support parameterized use: `use pen on paper "i wrote this"` writes text on
the paper. The intent is item-to-item communication, writing systems, and complex
interactive items.

## Current state (audited 2026-09-21)

### What works

- **Command parsing.** `use <tool> on <target> "<text>"` — `routes/action_handlers.py:382-414`
  (the `use` branch; line 393 `on_idx`, 397-405 quoted-token split), using
  `tokenize_command_detailed` at `routes/helpers.py:113-152`. Quoted tokens after
  `on`: the first becomes the target, the rest become `params`.
- **Engine entry point.** `VirtualWorld.use_item_on(item, target, params=…, amount=…)`
  at `virtual_world_engine.py:616-617` → `engine/items/use_actions.py:187`.
- **The inscription path.** `engine/items/use_actions.py:266-277` — when `params`
  is truthy, appends `\n[Inscribed: "<params>"]` to the **target node's**
  `properties["description"]`, stamps `updated`, records a `use` turn event, and
  returns early. Because it lands in `node.properties`, it is serialized with the
  graph and survives both save and scenario export; `examine` renders it for
  anyone.
- **`{params}` in trigger context.** `use_actions.py:283` seeds
  `trigger_context = {"params": params or ""}` for `on_use_on` triggers (and
  `:358` for a way target). `_render_template` (`engine/triggers/execution.py:77-139`)
  resolves it in effect values.
- **`set_description` / `append_description` effects.** Backend:
  `engine/effect_handlers/properties.py:71-109`. Authorable in the UI:
  `static/js/shared/trigger-types.js:73-74`, `trigger-editor.js:737-742, 1721-1731`,
  `static/js/shared/trigger-helpers.js:201-205`, `trigger-graph.js:175`,
  `static/js/item-library.js:839-843`. Known to prompt docs:
  `static/js/prompt-docs.js:37`, `static/js/main.js:373`, procedural generators
  (`static/js/shared/ai-generator.js:155`, `static/js/item-library/ai-generation.js`).
- **Reading.** `read` is an alias that rewrites to `examine`
  (`routes/action_handlers.py:217-220`), so any inscribed description is readable.

### What was proposed but is NOT implemented

- **`params_match` condition** — proposed in this task; no `params_match`
  implementation exists anywhere in the codebase. `params` is only reachable as
  a `{params}` template token inside an authored effect value.
- **Phase 2 built-in per-item param effects** (phone→notify, radio→tune, etc.) —
  never built; only the generic trigger path exists.
- **No test coverage** for the inscription path or the `{params}` template token.
  `tests/test_descriptive_targets.py:161` touches `use_item_on` but asserts the
  descriptive-target failure, not inscription.

### Known defects / traps

- **`params` is silently un-gated.** `use_actions.py:266-277` never checks that
  the tool is a writing implement or that the target is writable. Any tool+target
  pair inscribes if `params` is set — see task-160 / task-363, where
  `use create flame on dried flower crown` *inscribed* "flower crown" onto a
  crown.
- **Targeting is by quoted token, not structure.** `use pen on paper "text"`
  takes the quoted token as the **target**, so no inscription; only
  `use pen on "paper" "text"` works. This is ambiguous and easy for an agent or
  human to get wrong.
- **`append_description` re-appends on every fire** (fixed literal), so it is not
  idempotent as a note mechanism.
- **`set_description`/`append_description` target a literal node id**
  (`properties.py:80,100` — `"self"` does not resolve there; `set_parameter`
  does resolve `"self"` via `engine/effects.py:470-479`).

### What this task did not do

- The **LLM cannot drive it**: the structured action schema has no text field,
  the normalizer only emits `use <tool> on <target>`, and the tool path
  (`tools/game_tools.py:224`) calls `use_item_on(item_name, target)` with no
  `params`. AI narration that says "she wrote X" never persists.
- No authored pen/paper/noticeboard content exists.
- Reading back is an `examine` side effect, not a `read` behaviour.

These are scoped in **task-433**.

## Original proposed design (kept for history)

### Phase 1: Params in trigger context

When `use_item_on()` fires `on_use_on` triggers, pass the `params` text into the
trigger context so conditions and effects can reference it.

New condition type: `params_match` — checks if params match a pattern. *(never built)*

New effect type: `set_description` — changes a node's description. *(built — see above)*

### Phase 2: Built-in param effects *(never built)*

| Item | `use [item] on [target] '[text]'` | Intended effect |
|------|-----------------------------------|-----------------|
| pen | paper "Hello World" | Paper description becomes "Hello World" |
| phone | phone "Call Miki" | Notify Miki's player |
| radio | radio "tune 98.7" | Change room noise |
| note | note "Remember milk" | Note description changes |

### Phase 3: Custom param triggers *(partly built)*

Triggers may reference `{params}` in effect messages and values:

```json
{
  "trigger_type": "on_use_on",
  "effect_type": "set_description",
  "effect_params": {
    "message": "You write '{params}' on the paper.",
    "target_property": "description",
    "value": "{params}"
  }
}
```

`{params}` templating works; `target_property` is not a real field — the target
is a node id and the field is always `description`.

## Audit

**Status**: Ready to test (authoring path), superseded for the agent path by task-433.

**How to test**:
- Create a `pen` item with an `on_use_on` trigger: `set_description`, target =
  the paper item's id, value `"{params}"`.
- In-game: `use pen on "paper" "Hello World"`. Verify the paper's description
  changes and `examine paper` shows it.
- Verify a message containing `{params}` renders the text.
- Regression: `use pen on paper` (no quotes) writes nothing; `use create flame
  on dried flower crown` does not inscribe (task-363 cases).

## Files Affected

- `routes/action_handlers.py` — `use` parsing, quoted target/params split
- `routes/helpers.py` — `tokenize_command_detailed` quoted-token tracking
- `engine/items/use_actions.py` — `use_item_on`, the `params` inscription path,
  `{params}` trigger context
- `engine/effect_handlers/properties.py` — `set_description`, `append_description`
- `engine/triggers/execution.py` — `{params}` template resolution
- `virtual_world_engine.py` — `use_item_on` facade
- `static/js/item-library.js`, `static/js/shared/trigger-*.js`,
  `static/js/prompt-docs.js` — effect authoring + prompt docs
- `tests/` — **no inscription test exists yet** (task-433 adds one)
