---
type: doc
tags: [system/ui]
---

# Recent Edits & Undo

**Task:** [[dev_tasks/done/ui/task-371-undo-history-dropdown-labels|task-371]] · [[dev_tasks/review/ui/task-372-recently-edited-rail|task-372]] · [[dev_tasks/done/ui/task-373-changes-since-source-panel|task-373]] · [[dev_tasks/review/ui/task-384-per-edit-undo-feed|task-384]]

"What changed, and undoing it" is **four separate surfaces** over one primitive.
The primitive is a server-side stack of whole-world snapshots in `app._undo_stack`;
the surfaces are a history dropdown, a live event feed, a per-browser "recently
edited" rail, and a live-vs-source diff panel. They do not share state — the
dropdown and feed read the server stack, the rail reads `localStorage`, and the
diff panel reads the scenario file.

---

## The primitive: a label-per-snapshot undo stack

`routes/saveload.py:25` `_push_undo_snapshot(app, label)` stores
`(world.to_dict(), scenario_source, label)` and **clears the redo stack**. Depth is
capped at `_MAX_UNDO_DEPTH`, and the oldest entry drops off. Snapshots are pushed
by the mutating routes (create/update/delete graph ops, `/api/load`, `/api/reset`,
scenario discard) and by the NL editor's batch Apply.

`POST /api/undo` (`saveload.py:212`) takes `{"steps": n}`, pops `n` snapshots,
pushes the current state onto the redo stack, and **rebuilds the world from the
snapshot dict** (`_restore_snapshot`, `saveload.py:41`). Undo is therefore
whole-world, not diff-based, and it also autosaves. `GET /api/undo/list` returns
labels only — newest first, index 0 = what a single Undo restores.

## 1. Undo history dropdown — `static/js/ui/undo-history.js`

The 📜 button in the graph toolbar (`templates/index.html:203`) opens a menu that
lists every labeled snapshot with its depth (`(next undo)` / `+N undos`). Clicking
row *i* posts `steps: i + 1`, so it restores to that exact point by multi-step undo
(`undo-history.js:59`). Empty stack says "No undo history yet."

## 2. "World edited" feed — `static/js/ui/edit-feed.js`

Subscribes to the same `/api/events` bus `world-state.js` uses and renders a
toast-style row per `world_changed` event: a method icon (`✚ POST`, `✎ PATCH`, `🗑 DELETE`)
plus a path label (`graph node edited`, `world loaded`, `library edited`, …). Each
row has a `↩ Undo` button posting `{"steps": 1}`. Capped at 8 rows and each fades
out after 12s.

**Honest limitation (stated in the module header, `edit-feed.js:10-12`):** the Undo
button pops the **newest** snapshot, not the one that produced that row. The feed
is per-edit *labels* for visibility; ordering discipline is the undo stack's job.
So the feed's per-row undo is only truthful for the newest edit — the dropdown is
the surface to trust when you want a specific point.

## 3. Recently-edited rail — `static/js/ui/recent-edits.js`

A floating 🕘 button (bottom-left) holding up to **10** entries in
`localStorage['vw_recent_edits']`. It monkey-patches `ApiClient.updateNode` and
`ApiClient.duplicateNode` to record the node id, then clicking a row calls
`graphManager.showNodeAndFocus()`. This is a **jump list, not an undo** — nothing
here changes state.

**Scope limits, from the code:** only `updateNode` and `duplicateNode` are hooked,
so creates, deletes, edge changes, NL-editor batches and library edits do **not**
appear in the rail. The list is per-browser and survives a reload but is wiped by
clearing site data; it is not tied to the undo stack at all.

## 4. Changes since source — `static/js/ui/changes-panel.js`

A different question: not "what changed" but "what is not yet in the scenario
file". `GET /api/scenario/diff` returns the live-vs-source diff grouped into
`added/changed/removed` × `areas / items / ways / players` (`changes-panel.js:23`).
Each group offers **Commit** (merge live → source) or **Discard** (restore source →
live, undo-protected — `saveload.py:604` pushes a snapshot for it). Entered from
the 🌀 Changes button.

## Keyboard

`Ctrl/⌘-Z` and `Ctrl/⌘-Shift-Z` (`command-palette.js:259`) call `graphEditor.undo()` /
`redo()`, and are suppressed while typing in a field.

---

## What is scoped vs pending

- **Scoped and shipped:** the snapshot stack with labels, the dropdown, the feed, the
  rail, the per-group commit/discard, Ctrl-Z/Ctrl-Shift-Z.
- **Known rough edge:** per-row undo in the feed is really "undo the newest edit".
- **Out of scope by design:** the rail does not observe creates/deletes/edges; the
  stack is in-process memory, so undo history does not survive a server restart
  (the restored world is autosaved, but the stack is not persisted); `undo/list`
  exposes labels only, so the dropdown cannot show *what* changed at each point.

---

## Code map

| Module / route | Role |
|---|---|
| `routes/saveload.py:20-51` | `_snapshot`, `_push_undo_snapshot`, `_unpack_stack_entry`, `_restore_snapshot` |
| `routes/saveload.py:212` | `POST /api/undo` (`steps`), pushes redo, autosaves |
| `routes/saveload.py:242` | `GET /api/undo/list` (labels, newest first) |
| `static/js/ui/undo-history.js` | 📜 dropdown + multi-step restore |
| `static/js/ui/edit-feed.js` | `world_changed` feed, cap 8, 12s fade, `↩ Undo` |
| `static/js/ui/recent-edits.js` | localStorage rail, cap 10, hooks `ApiClient` |
| `static/js/ui/changes-panel.js` | live-vs-source diff, per-group Commit/Discard |
| `static/js/ui/command-palette.js:256-265` | Ctrl+S commit, Ctrl+Z / Ctrl+Shift+Z |
| `static/js/ui/scenario-status.js:52` | the dirty dot the Changes panel clears |

---

## Related docs

- [[UI & Settings/NL Editor|NL Editor]] — an Apply lands here as **one** snapshot
- [[Scenario Workflows & UI Audit]] — commit / discard workflow
- [[Rendering & UI Modules]] — module map for the whole front end

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[recent-edits-undo|Recent edits / undo]] (#62)

**Neighbouring notes** — [[Engine Config]], [[Event Log Export]], [[Event Stream]], [[Inspector Panels]], [[NL Editor]], [[Rendering & UI Modules]]

<!-- connected:end -->
