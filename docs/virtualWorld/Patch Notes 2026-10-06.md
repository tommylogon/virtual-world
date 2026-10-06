---
type: doc
tags: [surface/docs]
---

**Written to be read cold by anyone who has never seen this project.** No code, no
file names, no jargon. If you know nothing about how VirtualWorld works, you can
still read all of this.

A companion technical version — the same work, described the way a programmer
would write it — is in `CHANGELOG.md` under *A Day in the Life*. This one is
the same news told differently.

---

## The short version

The last update was about things that were disappearing. This one is about
**putting the world back together** — painting it, splitting its library, and
giving you a fog-of-war minimap so you can see where you’ve been.

Here is what that means concretely. You can now paint a world and actually see
what you’re doing: the brush shows where it will paint, the checklist stays
visible, and the panel scrolls smoothly. The item library is split into
biome, activity, and feature JSONs so a new biome cannot ship with nothing in
it. And for the first time, you have a minimap that shows where you’ve
explored, not just where you are.

---

## The painter finally shows you what it’s doing

If you used the WorldPainter before this update, you were painting blind. The
brush didn’t show where it would land, the checklist hid behind the map, and
scrolling the panel jumped you back to the top.

Now you can see what you’re doing:

- **Brush hover outline renders** — the brush shows exactly where it will
  paint before you click.
- **Checklist below the map** — the WorldPainter checklist is no longer hidden
  behind the map; it’s visible and usable.
- **Per-tool brush options** — each tool’s options live under it in the rail,
  so you don’t have to hunt for them.
- **Live preview on grid handles** — as you drag a grid handle, you see what
  the change will look like before you release.
- **Panel scroll stays put** — scrolling the WorldPainter panel no longer jumps
  you back to the top.
- **Painted art stays aligned with scope drags** — if you drag a scope in the
  graph, its painted map art moves with it instead of being left behind.

---

## The library is split and browsable

The item library used to be one giant JSON. Now it’s split into bite-sized
pieces so you can work on one part without touching the others.

- **Resource and hostile loot tables are separate JSONs** — 57 resource
  distributions and 24 hostile distributions live in their own files.
- **Biome, activity, and feature library split** — 106 biomes, 16 activities,
  and 9 features (a new registry) are now separate JSONs.
- **Pursuit templates and tags** — 4 pursuit templates and 599 tags (8 new)
  are also in their own files.
- **The library is browsable** — instead of dumping the entire library at
  once, you can now browse it page by page.
- **Importing a duplicate is refused** — if you try to import an item that’s
  already in the library, the game says so instead of silently merging it.
- **Refresh exists and is wired** — the `WorldPainterLibrarySync.refresh()`
  function exists and is called by the four places that needed it.

The library count holds at **1,999 items** — this update is about splitting
what was already there, not adding new items.

---

## Character art and expression packs work

If you tried to use an expression pack before this update, you might have
noticed missing expressions or a broken preview.

Now expression packs just work:

- **Adaptive sheet slicing** — the expression pack slicer looks at the actual
  sheet and adapts to its layout instead of assuming a fixed grid.
- **Live preview** — as you adjust the slicer, you see a live preview of the
  resulting expressions.
- **Rikka’s pack is updated** — her expression pack was re-sliced onto the
  current 30-name vocabulary, so all 30 expressions are present and correct.

You can also now upload expression art from the game, and the Kraktooth
scenario saves are committed so they won’t be overwritten by accident.

---

## You have a fog-of-war minimap

For the first time, you can see where you’ve explored.

- **A compact minimap at the top** — shows the areas you’ve visited or seen.
- **Scope-aware** — it respects the current scope and shows only what’s
  relevant.
- **Matches the human-fog-of-war design** — placement, sizing, and behavior
  match the design doc.
- **Updates as you explore** — as you visit new areas, they appear on the
  minimap.

---

## The library is cached for the session

If you were working in the WorldPainter library and noticed delays or stale
results, that’s fixed.

- **Biome/feature library scan is cached** — the scan that builds the library
  UI is cached for the session.
- **Dropped on commit** — when you commit your changes, the cache is dropped
  so the next session gets a fresh scan.
- **No more stale scans** — you won’t see outdated library results because of
  a lingering cache.

---

## Memory now reinforces, decays, and reflects

If you were using the memory system and noticed it felt static or
unresponsive, that’s changed.

- **Reinforcement** — using a memory makes it stronger and more likely to be
  recalled.
- **Decay** — if a memory isn’t used, it fades over time.
- **Reflection** — when a memory contradicts new information, the system
  reflects on it to resolve the conflict.
- **Importance score is a legacy precursor** — the old importance score is
  treated as a starting point for the proper memory system, not the final
  word on what’s important.

---

## UI and tooling improvements

Several small quality-of-life improvements landed:

- **Visual in-app bug report workflow** — click the bug report button to
  capture the current state and file a structured report.
- **Chat transcript preserved** — the chat transcript survives the
  Apply-commit flow that was wiping it.
- **Scene controls and narration aligned** — the human-turn composer’s
  controls and narration now match the actual world state.
- **Orphaned person context menu scrim documented** — the scrim that appears
  when the person context menu is orphaned is now documented.
- **Completed task-388 planning document removed** — cleanup.

---

## Vault docs and task records

The Obsidian vault got a lot of new pages and integrity guards:

- **Feature-indexed pages** — 86 new `Features/` pages, one for each feature
  row in the Feature Map.
- **Integrity guards** — the four vault guards (doc links, feature pages, doc
  tags, doc connected) now run on precommit to keep the vault healthy.
- **Task records filed** — findings from the plan, UI, and library passes are
  filed as task records.
- **Task records reorganized** — emotion and design task records are now
  under the correct status folders.
- **Typed plan contract grounded** — the typed plan contract is now grounded
  in the actual data model, and truncated steps are salvaged.

---

## Known gap: module:check failures

Three Python modules are missing `@module`/`@contributes` headers, so the
`module:check` gate fails on them:

- `engine/activities_loader.py`
- `engine/effect_handlers/activities.py`
- `engine/effect_handlers/movement.py`

This is disclosed here; it is not fixed in this window. Fixing it is filed as
its own task.

---

## Known state of the suite at this commit

If you run the test suites, here’s what you’ll see:

- **JS unit tests**: 613 passed / 0 failed (was 533). All 158 modules are
  converted from TypeScript to JavaScript.
- **Python suite**: 35 failed / 7,569 passed / 1 skipped (about 4 minutes
  49 seconds). This is against a documented floor of 12 known pre-existing
  failures. The delta from the previous window (84 → 35) is explained by the
  working-tree changes in this window (AGENTS.md rewrite,
  `data/engine_config.json` physics flip, kraktooth scenario edit) and the
  MCP cluster now passing on `fastmcp 3.4.7`. Verify the installed `fastmcp`
  version before suspecting `mcp_server.py`.

---

## Two things you should know

**`data/engine_config.json` has a physics setting flip in the working tree.**
Map mode now respects the user's physics setting instead of forcing it off —
the flip is deliberate, but it means a fresh load from the authored file will
differ from the running app's persisted config.

**The server is still up on `:4444`.** The `AGENTS.md`,
  `data/engine_config.json`, and the *Pursuit Assignment and Progress UI Mockup*
  PNG remain deliberately dirty — do not commit them. The four new biome
  palette mockups are part of this release.

---

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Emotion & Mood — Whole-System Analysis]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]], [[Patch Notes 2026-09-28]], [[Patch Notes 2026-09-30]]

<!-- connected:end -->
