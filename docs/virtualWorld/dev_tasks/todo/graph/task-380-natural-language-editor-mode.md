---
type: task
status: redesign
area: graph
priority: high
revision: 2
---

# task-380: Natural-Language Editor Mode (with tool calling + multi-turn)

**Filed**: 2026-08-31
**Revision 2**: 2026-08-31 — flipped from "one-shot JSON plan" to a multi-turn
tool-calling loop after realizing the codebase already supports `tool_calls`
in the message array (`static/js/context-window.js:51`), the message format is
already OpenAI-compatible, and "heavily use existing library items" is the
core goal — a tool loop is what makes that discoverable.

**Sister docs**: task-9 (procedural placement), task-376 (draw-a-door wizard),
task-378 (bulk selection), task-324 (domain tags), item-library/ai-generation.js
(per-item "Improve" pattern), `static/js/shared/ai-generator.js:81`
(`buildItemSystem`).

## Problem

The editor today is *form-driven*: every create flow is a modal with discrete
fields. For power users who already know the schema, that's fine. For anyone
authoring a scenario from imagination — "add a flickering streetlight to Oak
Street", "give Mira a worried personality and a locket she won't let go of",
"connect the attic to a hidden library behind a bookshelf" — the gap between
intent and form is the bottleneck.

The first revision of this doc assumed a one-shot `classify → plan → preview →
apply` flow with a strict JSON plan schema. That was wrong for two reasons:

1. **The user wants multi-turn.** "Find me a lantern in the library and put a
   candle inside." is a *follow-up* to "the library is too dark, give it some
   mood lighting" — not a fresh request. The agent should remember that we
   just added a chandelier, and which library it was.
2. **The user wants library reuse, not raw generation.** The core workflow
   is: *search* the library, *pick* a fitting entry, *adapt* it, *place* it.
   That is exactly what tool calling is for — the model issues a `search_library`
   tool call, sees the result, decides "actually I'll make a new variant", and
   issues a `create_item` tool call. A single JSON plan forces the model to
   guess about the library *before* it has looked.

The codebase already supports `tool_calls` in the OpenAI message array
(`static/js/context-window.js:51` keeps them through pruning). The LLM
client's `chat(messages)` is already OpenAI-compatible. We just need to send
`tools:`, parse `tool_calls` from the response, and feed `role: "tool"`
results back.

## What "natural-language editor mode" is

A chat-shaped surface (Cmd-L overlay + side panel) where the user types
free-form authoring intent and an LLM agent **with tools** authors the world:

- **Search tools** — find existing graph nodes, library items, library areas,
  library characters, tags. These are *read-only* and let the model discover
  what already exists before it decides what to do.
- **Mutation tools** — create_node, update_node, delete_node, attach,
  detach, connect_areas, spawn_library_item, link_to_library. These
  change the world. Every mutation goes through the existing routes, so
  undo, save, schema validation, and library linting all keep working.
- **Meta tools** — undo, redo, list_world, list_library. Cheap conveniences
  the agent uses to orient itself without re-reading everything.

The chat is genuinely multi-turn: the user can say "now do the same for
the garden", "actually change the door to a gate", "wait, undo that", and
the agent's response history is the source of truth. The agent can also
*clarify* — "Oak Street isn't an area yet, did you mean Main Street or
should I create Oak Street?" — by emitting text without tool calls and
waiting for the user.

The final **commit step** is a separate user action: the agent shows a
diff-like preview of everything it staged, the user approves (or rejects,
or asks for a tweak), and the mutations hit the graph. Staging is a
local buffer; nothing mutates the live world until the user clicks Apply.
This makes the loop feel safe.

### End-to-end example (multi-turn + tool calling)

```
USER:    add a flickering streetlight to Oak Street
AGENT:   [tool] search_library_items("streetlight")       → 0 results
         [tool] search_graph_nodes("Oak Street")           → 1 result
         [tool] search_library_tags(["light_source","toggleable","electric"])
                                                      → 3 tag ids
         I'll create a new streetlight. It's a tag-driven item:
         a furniture with `light_source` + `toggleable` so the engine
         treats it as a lamp, and an `on_toggle_on` trigger that
         adjusts the area's light to 35.
         [stage: 1 create_item (streetlight) → attach(at) → area:oak_street]
         Apply? (y/n)
USER:    y
AGENT:   applied. ready for the next one.

USER:    give the streetlight a slight bulb-flicker so it feels alive
AGENT:   [tool] get_node("item_streetlight")               → current state
         [tool] search_library_items("flicker", tags:["trigger"])
                                                      → 0 results
         I'll add an `on_tick` trigger that nudges the light ±5 with
         a 12% chance each tick — that reads as a dying bulb.
         [stage: 1 update_node(item_streetlight, add trigger)]
         Apply? (y/n)

USER:    undo the flicker and instead make it a gas-lamp with a steady warm glow
AGENT:   [tool] undo()                                      → reverts
         [tool] search_library_items("gas lamp")           → 1 result: "antique_gas_lamp"
         [tool] get_library_item("antique_gas_lamp")       → full schema
         There's a library match. Want to (a) place the library
         item as-is, (b) place it and customize, or (c) make a
         new variant inspired by it?
USER:    a — but call it a "wrought-iron streetlight"
AGENT:   [tool] spawn_library_item(antique_gas_lamp, parent: area_oak_street,
                                  rename: "wrought-iron streetlight")
         [tool] get_node("item_wrought-iron_streetlight")  → check rename
         placed from the library and renamed. [1 op, 1 name change]
         Apply? (y/n)
```

Note the **library-first default**: the agent searched the library before
generating, found a fitting entry the second time, and reused it. The
"create new" path is the fallback, not the default.

## Design

### Surface

Same as revision 1 — two small entry points sharing one controller:

1. **Command-palette sibling**: `Cmd-L` (or `>` prefix in the existing
   `Cmd-K` at `static/js/ui/command-palette.js:18`)
2. **Side panel**: a "NL Editor" tab in the left panel (next to Agents /
   Outline / Lens / Issues)

Both share one `NaturalLanguageEditor` controller (new module
`static/js/nl-editor/index.js` + `tools.js` + `staging.js` + `agent-loop.js`).

### Architecture

```
                    user text
                        │
                        ▼
              ┌──────────────────┐
              │ agent-loop.js    │   single LLM chat() per turn, with `tools:`
              │ (ReAct-style)    │   ◀── tool_calls from LLM
              │                  │   ──▶ tool results feed back into messages
              └──────────────────┘
                  │              ▲
                  │              │
                  ▼              │
        ┌──────────────┐   ┌────────────┐
        │ tools.js     │   │ messages[] │   persistent chat history, pruned
        │ (router)     │   │ (window)   │   by context-window.js
        └──────────────┘   └────────────┘
                  │
        ┌─────────┴─────────────────────────────────┐
        │            │             │                │
   search_*    create_*    update_*    delete_*    link_*
   (read)      (staged)    (staged)    (staged)    (staged)
        │            │             │                │
        └────────────┴─────────────┴────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ staging.js   │   local buffer of pending mutations
                       │              │   (one undo snapshot on Apply)
                       └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ live graph   │   via existing routes
                       └──────────────┘
```

The agent loop is the same idea as the **agent-engine.js** LLM loop already
in the codebase (`static/js/agent-engine.js:1096` calls `llmClient.chat`),
but driven by *user intent* instead of *character observation*, and with
editor tools instead of action tools.

### The tool catalog (v1)

| Tool | Reads / Writes | Purpose |
|---|---|---|
| `search_graph_nodes(query, kind?, tags?)` | read | find existing area/item/way/character by name or alias |
| `get_node(node_id)` | read | full schema incl. properties, triggers, contents |
| `search_library_items(query, tags?)` | read | find existing library items to reuse |
| `get_library_item(item_id)` | read | full library entry |
| `search_library_areas(query, tags?)` | read | find existing areas to clone or place into |
| `get_library_area(area_id)` | read | full library area |
| `search_library_characters(query, tags?)` | read | find existing characters |
| `get_library_character(char_id)` | read | full library character |
| `search_library_tags(query)` | read | find tag ids and metadata |
| `list_world_summary()` | read | small world summary (type/name triples + area tag list) |
| `list_library_summary(registry?)` | read | small library summary, same shape |
| `create_node(kind, name, properties?, tags?, triggers?)` | staged | the workhorse for new entities |
| `update_node(node_id, patch)` | staged | partial patch, only the changed fields |
| `delete_node(node_id)` | staged | with cascade confirmation |
| `attach(from_id, to_id, relation)` | staged | spatial edge (in/on/under/behind/beside/at) |
| `detach(edge_id)` | staged | remove an edge |
| `connect_areas(area_a_id, area_b_id, way_name, options?)` | staged | composite: way node + 4 connection edges (reuses task-376 machinery) |
| `spawn_library_item(library_id, parent_id, rename?, overrides?)` | staged | place a library item; defaults to "place as-is" |
| `link_to_library(node_id, library_id)` | staged | point a live node at a library entry (template sync) |
| `preview_staged()` | read | the staging buffer as a human list, no LLM needed |
| `undo()` / `redo()` | action | the existing app-level undo (uses `_push_undo_snapshot`) |
| `request_clarification(question, options?)` | action | a special tool: emits a question to the user, waits for the answer, the next agent turn sees the answer in the message history |

That last one is the key to **library-first behavior**. The agent *can* call
`create_node` for a brand-new streetlight, but the system prompt *steers* it
toward `search_library_items` first; the model picks a library match when one
exists, and the `request_clarification` tool is the way it asks "use the
library match, or do you want a brand-new one?" without leaking a free-form
chat side-channel.

### Library-first is the default, not a path

The system prompt explicitly says: **before calling `create_node` for a kind
that has a library, call the corresponding `search_library_*` first.** The
model has to either:
- pick a library item and call `spawn_library_item` / `get_library_item`
  + `create_node` (cloned), or
- explain in the assistant text *why* nothing in the library fits

This is enforced by prompt, not by the tool layer — but the search results
get sent back to the model as `role: "tool"` messages, so the model has the
information it needs. (See "Why this works" below.)

### Staging and Apply

`staging.js` is a local buffer. Each mutation tool returns a small JSON
result (`{ staged: true, op_id, summary, warnings: [...] }`) and appends
to the buffer. The live graph is *not* touched.

When the user clicks **Apply**:

1. Push one `_push_undo_snapshot` (existing `routes/saveload.py`)
2. Replay the staged ops in order: creates → updates → edges → deletes
3. Run the existing trigger validator against any new/modified triggers
4. Log the LLM call and the apply action via `game_logger.log_llm_call`
5. Refresh `worldState`
6. Clear the staging buffer

**This is the only place the live world is touched.** The agent can iterate
fifty turns of "actually, change this" without any side effects, because
each iteration only mutates the staging buffer.

**Reject** discards the buffer. **Edit** drops the user back into the chat
with the buffer intact and a reminder of what's currently staged. **Apply**
is a single confirmation, not a per-op confirmation — the agent's preview
text at the end of the previous turn is the per-op review.

### Multi-turn message history

- One `messages[]` array per NL editor session, kept on the
  `NaturalLanguageEditor` controller.
- The system message is built once per session and includes: world
  summary, library summary, the tool catalog, the library-first rule,
  and the "tag enums only, never invent a tag" rule (mirrored from
  `static/js/shared/ai-generator.js:81`).
- Every user turn is appended.
- Every agent turn appends: assistant message (text + `tool_calls` if
  any), then for each tool call a `role: "tool"` message with the
  function result.
- **Pruned** by the existing `ContextWindowManager` (`static/js/context-window.js`),
  which already keeps `tool_calls` and their paired `tool` results
  together (line 51–55). No new pruning logic.
- A **clear-chat** button on the panel resets the session (and the
  staging buffer is dropped or kept per the user's choice).

### Token budget

Same budget as before (~4k tokens target, summarized context), but
now also the message history participates. The pruning is the existing
`ContextWindowManager`, which is already correct for this case.

`list_world_summary` and `list_library_summary` exist specifically so
the agent can re-orient cheaply without re-reading the full dumps.

### Prompt construction

A single system message with these blocks, in order:

1. **Role** — "you are a world-authoring assistant with tools"
2. **Tool catalog** — names, parameters, when to call each
3. **Library-first rule** — must `search_library_*` before
   `create_node` for any kind that has a library
4. **Tag enums** — only registered tags, only `ITEM_ACTIONS` verbs,
   only `ITEM_STATES` states, only known trigger types — same
   restrictions as `buildItemSystem`
5. **Staging rule** — every mutation tool stages, never mutates
6. **Domain guidance** — `area` is *what a place is for* (kitchen,
   garden, attic), `setting` is *what world it's in* (fantasy,
   modern) — pulled from task-324
7. **World summary** — small (≤1k tokens), refreshed after every
   Apply
8. **Library summary** — same shape, refreshed rarely

The system message is rebuilt when the world summary changes (i.e.
after an Apply), not per turn.

### Failure modes

- LLM returns prose without tool calls and without an answer → treat as
  a clarification: the user is asked a focused question (the model
  *should* have used `request_clarification` but didn't)
- Tool call has a bad parameter (e.g. unknown tag) → the tool returns
  `{ error: "unknown tag 'foo', did you mean ...?" }` as a `role: "tool"`
  message; the model self-corrects on the next turn
- LLM call fails / times out / rate-limit → existing
  `AIGenerator.generate` error toast pattern; staging buffer untouched
- Apply fails (e.g. duplicate id) → the failing op is rolled back,
  the others stay applied, a toast names the failure. The undo
  snapshot covers the whole Apply, so one undo reverts everything.
- Agent goes in circles → visible in the chat history; the user can
  press "Reset chat" or pick up the conversation

### Out of scope (v1)

- Editing triggers with a *visual* builder in the chat surface — the
  chat is text + tools, not a form. v1 is good enough for the 80% case
  (create/update with simple triggers); complex multi-effect triggers
  are best done in the existing trigger UI after the chat creates the
  shell node.
- Auto-commit to library (writing new entries to `data/library/`).
  Library promotion stays a manual decision via the existing library
  UI. v1 only writes to the live world.
- Multi-user / collaborative editing. v1 is single-user; the staging
  buffer is local.
- Per-area "style" memory ("this scenario is Victorian"). Could be a
  v2 thing where a per-scenario note becomes part of the system
  message. For now, the user says "and keep it Victorian" once and
  the chat history carries it.

## Work plan

1. **Tool-calling plumbing in `llmClient`** — add `tools` and
   `tool_choice` to the chat-completions body, parse `tool_calls` from
   the response, expose a `chatWithTools(messages, {tools})` helper
   that returns `{ content, tool_calls }`. The existing `chat()`
   stays as the text-only path. Smallest possible change.
2. **Tool router + search tools** — new `static/js/nl-editor/tools.js`
   with the read-only search/get tools wired to existing endpoints
   (`/api/graph/nodes`, `/api/library/<type>`, `/api/tags/search`,
   `worldState`). At this point the LLM can *read* the world.
3. **Staging buffer** — `staging.js`, the local mutation buffer, the
   Apply/Reject/Edit UI, and the single undo snapshot. No agent
   involved — the user can stage manually if they want, like a more
   powerful version of the existing per-form modal flow.
4. **Mutation tools** — `create_node`, `update_node`, `delete_node`,
   `attach`, `detach`, `connect_areas`, `spawn_library_item`,
   `link_to_library`. Each tool is a thin wrapper around an existing
   route.
5. **Agent loop** — `agent-loop.js` runs the ReAct loop: send
   `messages` with `tools`, on `tool_calls` execute them, append
   `role: "tool"` results, re-call. Bounded by max iterations (10)
   and max tool calls per turn (5). Mirrors the bounds in
   `static/js/agent-engine.js`.
6. **Surface wiring** — Cmd-L overlay (extend
   `static/js/ui/command-palette.js:18`) and side panel tab.
7. **`request_clarification` tool** — last, because it depends on the
   panel being there to render the question.

## Verification

- `python -m pytest tests/ -q -k "not mcp and not emote"` (no
  regressions)
- New `tests/test_nl_editor.py` with:
  - library-first: typed "add a lantern" against a world that has
    a `lantern` library item → agent calls `search_library_items`
    before `create_node`, and the apply creates one item (not two)
  - multi-turn: second turn references a node from the first turn
    → agent uses the prior turn's tool result, not a new search
  - staging safety: agent calls `delete_node` for a node with
    children → the tool result flags the cascade, the user is
    asked before any live mutation
  - undo safety: apply a 5-op plan, then `undo()` → graph is
    exactly as it was before apply
- Manual: ten hand-written scenarios including the
  streetlight/flicker/rewrite chain, a "delete a broken radio"
  with cascade confirmation, a multi-node compound
  ("connect attic to a hidden library behind a bookshelf"), and a
  deliberately ambiguous one (the resolver asks a question, the
  user picks).

## Dependencies

- Blocked by: nothing hard. The Improve buttons and the
  resolver-friendly `worldState` already exist, and the
  `tool_calls` message format is already understood by the
  context window manager.
- Soft dependencies worth landing first:
  - task-324 (domain tags) — improves LLM prompt quality, not
    required
  - task-323 (library lint) — needed for the staging lint step
  - task-376 (draw-a-door wizard) — confirms the `connect_areas`
    composite behavior we want to expose as a single tool
- Blocks: nothing. The editor stays fully usable without it.

## Open questions

1. Should the tool catalog be sent in *every* call (cleaner, more
   tokens) or only on the first turn? (Leaning every call — most
   providers cache system blocks; pruning is only the
   messages.)
2. Should the staging buffer be visible *as a list* in the panel,
   not just at Apply time? (Leaning yes — a small "staged: 3 ops"
   badge that expands to the list on click. Lets the user catch
   surprises before the agent finishes its turn.)
3. Does the agent need a "self-critique" tool to check its own
   plan before staging the first op? (Defer; v1 lets the user
   reject/edit, which is the same affordance.)
4. Per-scenario style memory (the "keep it Victorian" idea)?
   Defer to v2.
