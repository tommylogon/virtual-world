---
type: task
status: done
area: graph
priority: high
revision: 3
---

# task-387: Natural-Language Editor Mode (with tool calling + multi-turn)
*(Renumbered from task-380 to avoid collision with `task-380-trigger-snippet-palette.md`)*

**Filed**: 2026-08-31
**Completed**: 2026-08-31
**Revision 2**: 2026-08-31 — flipped from "one-shot JSON plan" to a multi-turn
tool-calling loop after realizing the codebase already supports `tool_calls`
in the message array (`static/js/context-window.js:51`), the message format is
already OpenAI-compatible, and "heavily use existing library items" is the
core goal — a tool loop is what makes that discoverable.
**Revision 3**: 2026-08-31 — architectural audit & implementation:
1. **Overlay Graph View for Read Tools**: Read tools query a merged view
   (`worldState` + `staging.js` additions - staged deletions) so multi-turn
   references to uncommitted staged nodes work seamlessly.
2. **Disambiguated Undo**: Split `unstage_op` (buffer manipulation) from
   `undo_last_apply` (live graph snapshot reversal).
3. **Deterministic Staged IDs**: Client-side minted IDs ensure multi-op chains
   (create area → connect ways → attach items) resolve before backend commit.
4. **Token-budgeted search payloads**: Search tools return compact summaries;
   detail tools return full schemas.
5. **Context Window atomic tool-block pruning**: Enforce atomic preservation
   of `assistant.tool_calls` and corresponding `role: "tool"` responses.

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
   issues a `create_node` tool call. A single JSON plan forces the model to
   guess about the library *before* it has looked.

The codebase already supports `tool_calls` in the OpenAI message array
(`static/js/context-window.js:51` keeps them through pruning). The LLM
client's `chat(messages)` is already OpenAI-compatible. We just need to send
`tools:`, parse `tool_calls` from the response, and feed `role: "tool"`
results back.

## What "natural-language editor mode" is

A chat-shaped surface (Cmd-L overlay + side panel) where the user types
free-form authoring intent and an LLM agent **with tools** authors the world:

- **Search & Read tools** — find existing graph nodes, library items, library areas,
  library characters, tags. These read from an **Overlay View** (live graph +
  staged buffer) so uncommitted nodes are discoverable across multi-turn chats.
- **Mutation tools** — create_node, update_node, delete_node, attach,
  detach, connect_areas, spawn_library_item, link_to_library. These
  append operations to a local staging buffer with deterministic IDs.
- **Meta tools** — unstage_op, list_world_summary, list_library_summary,
  request_clarification. Cheap conveniences for the agent to inspect state
  and interact with the user.

The chat is genuinely multi-turn: the user can say "now do the same for
the garden", "actually change the door to a gate", "wait, undo that", and
the agent's response history is the source of truth. The agent can also
*clarify* — "Oak Street isn't an area yet, did you mean Main Street or
should I create Oak Street?" — by emitting a structured `request_clarification`
tool call (which renders interactive choice chips in the UI) or assistant prose.

The final **commit step** is a separate user action: the agent shows a
diff-like preview of everything it staged, the user approves (or rejects,
or asks for a tweak), and the mutations hit the graph. Staging is a
local buffer; nothing mutates the live world until the user clicks Apply.
This makes the loop feel safe.

## Implementation Details

The feature is implemented in `static/js/nl-editor/` and integrated into the app:
- `static/js/nl-editor/staging.js`: `StagingBuffer` class with deterministic ID generator (`mintId`) and batch topological Apply.
- `static/js/nl-editor/tools.js`: 20 tool definitions and `OverlayGraphView` merging live and staged states.
- `static/js/nl-editor/agent-loop.js`: ReAct agent loop with context pruning and library-first system prompt.
- `static/js/nl-editor/ui.js`: Side panel UI with message bubbles, tool chips, staged ops tray, and clarification options.
- `static/js/nl-editor/index.js`: Controller singleton (`window.NLEditor`) wired to `worldState`.
- `static/js/llm-client.js`: Added `tools` and `chatWithTools(messages, options)`.
- `static/js/context-window.js`: Atomic tool-block preservation during pruning.
- `static/js/ui/command-palette.js`: Added Cmd-L / Ctrl-L shortcut and palette action.
- `static/js/ui/help-center.js`: Added coach tip in HelpCenter.
