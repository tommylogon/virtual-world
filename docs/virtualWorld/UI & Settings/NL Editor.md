# NL Editor

**Task:** [[dev_tasks/done/graph/task-387-natural-language-editor-mode|task-387]] · validation/diff: [[dev_tasks/inprogress/graph/task-461-nl-editor-validation-gate-and-apply-time-property-diff|task-461]]

Describe a change to the world in prose; see the plan before it is applied. The NL
editor is a left-hand tab (✨ NL Editor, `templates/index.html:106`) holding a
tool-calling conversation, a staged-operations tray, and a diff of what will
change. **Nothing touches the graph until you press Apply** — the whole cluster
lives in `static/js/nl-editor/` and buffers every mutation locally.

---

## The flow

    prompt → ReAct tool loop → staged ops + ghost previews → diff → Apply → graph

1. **Prompt.** `index.js:99` `send()` hands the text to the agent loop.
2. **Plan / staged ops.** The model calls tools; every *write* tool lands in the
   `StagingBuffer` (`staging.js:17`) as an op `{id, type, payload, summary, timestamp}`.
   Read tools see staged entities immediately, because `tools.js` merges the live
   `worldState` with an `OverlayGraphView` built from the uncommitted ops — so
   "where did you put the lantern?" is answered from the plan, not the world.
3. **Diff preview.** Each tray row renders `NLEditorDiff.summaryLines()` —
   leaf-level property changes (`traits.dark_vision: — → true`) computed against
   the live/staged pre-state (`diff.js:37` `baseProps()`, `diff.js:127`).
   An op with no property change is labelled *"(no property change — will no-op)"*.
4. **Apply.** `index.js:112` → `staging.js:186` → one `POST /api/graph/batch`.

### Nothing reaches the graph before Apply

The system prompt states it as rule 2, the "staging firewall"
(`agent-loop.js:91-94`), and it is enforced by construction: the write tools call
`staging.addOp()` and nothing else. The graph is only touched inside the batch
route, after validation.

---

## Opening it

`Cmd-L` / `Ctrl-L` (`static/js/ui/command-palette.js:239`) calls
`window.NLEditor.openPanel()`, which switches the left tab and focuses `#nl-input`
(`index.js:156`). The adjacent `Cmd-K` is the command palette; `Ctrl-Z` / `Ctrl-Shift-Z`
are undo/redo (`command-palette.js:259`).

## The tool catalog

29 tools in `tools.js` (`TOOL_DEFINITIONS`). Reads: `search_graph_nodes`, `get_node`,
`list_nodes`, `list_world_summary`, `get_background_map`. Library reads:
`search_library_items`, `get_library_item`, `search_library_tags`, `list_library_traits`,
`search_library_areas`, `get_library_area`, `search_library_characters`,
`get_library_character`, `list_library_summary`. Writes: `create_node`,
`spawn_library_item`, `populate_area`, `update_node`, `update_matching_nodes`,
`delete_node`, `attach`, `detach`, `connect_areas`, `link_to_library`,
`upsert_library_entry`, `delete_library_entry`. Session control: `unstage_op`,
`clear_staged`, `request_clarification`.

The system prompt carries two hard rules: **library-first** (search before
inventing a node) and **bulk over loops** (`update_matching_nodes` with a selector
rather than N × `update_node`) — `agent-loop.js:86-90` and `:104`.

## Ghost previews

`ghosts.js` renders uncommitted ops onto the vis.js graph: created/connected
entities as fixed dashed "ghost nodes" labelled *(staged)*, updated live nodes
with a dashed amber outline, deleted ones dashed red, attach/detach as dashed
ghost edges. When a turn ends with fresh ops the camera auto-pans to them
(`index.js:70`). Ghosts re-apply after every graph reload because they hook
`GraphNetwork.loadGraphData`.

## Apply is one undoable transaction

`routes/graph_ops.py:1207` `handle_graph_batch` is the only write path:

- **Validation first.** `_validate_batch_ops()` runs
  `engine/nl_editor_validation.validate_ops()` *before* anything is touched. With
  `strict_validation: true` (which the editor sends) any `error`-severity finding
  returns **422** with `status: "invalid"` and **nothing is applied**; every op
  stays staged (`staging.js:197`). Findings render as a ⛔ bubble in the panel
  (`ui.js:183` `showValidationIssues`).
- **One snapshot.** `_push_undo_snapshot(app, label="NL editor batch (N ops)")`
  — a single Undo reverts the whole Apply (`routes/saveload.py:25`).
- **Topological replay.** Ops are sorted by `_BATCH_PHASE` (creates → updates/links →
  edges → deletes) and replayed by `_apply_batch_op()`. Failures are reported per
  index and the response is **207 partial**; the client removes *only* the ops the
  server reports as applied, so the rest stay staged for fixing (`staging.js:218`).

`connect_areas` also back-fills `world_scope_id`/`area_from` via `_infer_way_facts`
(`graph_ops.py:1023`) so a hand-made way belongs to a scope like a library one.

### What the Apply gate checks

`engine/nl_editor_validation.py` — unknown op type, missing/malformed payloads,
unknown node type, duplicate node id, duplicate area display name, non-existent
targets and edge endpoints, unknown trait ids (against `engine/traits.py`),
unknown item actions, non-empty bulk selector, lowercase-slug library ids,
non-writable registries, and a **mature gate** on `mature` entries. Severity:
`error` blocks a strict Apply, `warning` does not.

### Selective apply

Every tray row has a checkbox; `Apply Selected (n)` calls `index.js:134`
`applySelected(ids)`, which posts only the checked ops. Unchecked ops stay staged.

---

## Code map

| Module | Role |
|--------|------|
| `static/js/nl-editor/index.js` | `window.NLEditor` singleton; wires staging → UI, agent events → UI |
| `static/js/nl-editor/agent-loop.js` | Multi-turn ReAct loop (`maxIterations: 100`), system prompt, clarification suspension, XML tool-call fallback |
| `static/js/nl-editor/tools.js` | 29 tool definitions + `OverlayGraphView` (live ⊕ staged) |
| `static/js/nl-editor/staging.js` | `StagingBuffer`; batch apply + per-op replay fallback for stale servers |
| `static/js/nl-editor/diff.js` | Pure property-level diff for the tray |
| `static/js/nl-editor/ghosts.js` | Dashed previews on the graph canvas |
| `static/js/nl-editor/ui.js` | Chat stream, staged tray, clarification buttons, validation bubble |
| `engine/nl_editor_validation.py` | Pre-Apply op validator (`validate_ops`, `errors_only`) |
| `routes/graph_ops.py:1174-1268` | `_validate_batch_ops`, `handle_graph_validate` (dry-run), `handle_graph_batch` |
| `routes/graph.py:122-127` | `/api/graph/batch`, `/api/graph/batch/validate` |

---

## Related docs

- [[Graph System]] — the model being edited
- [[Library System Overview]] — the library-first mandate
- [[Doors & Connections]] — what `connect_areas` writes
- [[UI & Settings/Recent Edits & Undo|Recent Edits & Undo]] — where the Apply lands in history
- [[Scenario Workflows & UI Audit]] — how this sits in the authoring workflow