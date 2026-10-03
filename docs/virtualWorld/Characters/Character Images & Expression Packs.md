# Character Images & Expression Packs

A character can carry live art keyed by **emotion** or **action** — a
SillyTavern-style expression pack. Each key holds two renders: a **profile**
(bust, used as the avatar) and a **full body** (portrait / graph art).

---

## Data model

The pack lives on the character's graph node as `properties.expressions`:

```json
"expressions": {
  "neutral": { "profile": "/static/images/nodes/kaelen-profile-neutral-....png",
               "full":    "/static/images/nodes/kaelen-full-neutral-....png" },
  "happy":   { "profile": "...", "full": "..." },
  "angry":   { "profile": "..." },
  "attack":  { "full": "..." }
}
```

- **Keys** are normalised to lowercase slugs (`[a-z0-9_]`). The canonical
  emotion vocabulary is `neutral, happy, sad, angry, afraid, surprised,
  disgusted, aroused, affectionate, ashamed, envious, calm`; any other string
  is allowed and treated as a custom **action** key (`attack`, `sleeping`, ...).
- Each key may define `profile`, `full`, or both. A missing slot falls back.

**Legacy fallbacks** (kept for backward compatibility and non-character nodes):

| Property | Meaning |
| --- | --- |
| `image` | generic node image; for a character it is the **full-body neutral** |
| `profile_image` | the **profile neutral** |

Uploading a slot named `neutral` also writes the matching fallback, so nodes
and consumers that only understand the single-image model keep working.

---

## Resolution

The avatar resolver picks, in order:

```
expressions[<current emotion>].profile  ->  expressions.neutral.profile
  ->  profile_image  ->  image  ->  (icon fallback)
```

The graph node, the turn-composer "People here" chip, the agent-lens header and
the examine portrait all resolve through one module, `static/js/character-art.js`
(`CharacterArt.avatarFor` / `fullArtFor` / `artForNodeId`), so the chain cannot
drift between consumers. The full-body chain is
`expressions[emotion].full -> expressions.neutral.full -> image`.

```js
expressions[<current emotion>].profile  ->  expressions.neutral.profile
  ->  profile_image  ->  image  ->  (icon fallback)
```

- **Graph node** (`static/js/graph/network-manager.js`, Show Images mode) now
  draws this current-emotion **profile**, not the static full-body `neutral`.
  Which key counts as "current" is `player.emotion.expression` — the server's
  canonical key derived from the **affect map** (`Player.dominant_expression()` ->
  `engine.emotion.dominant_expression`, the strongest axis raised above its
  baseline, else `neutral`), so the face follows the state events and decisions
  produced rather than the legacy free-text `emotion.current`. The client
  (`CharacterArt.emotionKeyFor`) prefers `expression`, falls back to a canonical
  `current`, else `neutral`.
- **People chips** (`static/js/agent/turn-scene-view.js`) show the profile
  thumbnail; clicking it — or choosing **Examine** — opens
  `CharacterArt.open()`, the big view: current **full body** if the character has
  one, else the profile enlarged (with a Full body / Profile tab when both exist).
  The composer also auto-opens it in the **react phase** when the committed
  action was `examine <person>`.

---

## HTTP API

| Route | Body | Effect |
| --- | --- | --- |
| `POST /api/graph/node/<id>/image` | multipart `file`, `kind` (`profile`\|`full`, default `full`), `expression` (default `neutral`) | saves the file under `static/images/nodes/`, stores the slot, replaces + deletes the previous file for that slot |
| `POST /api/graph/node/<id>/image/remove` | JSON `{kind, expression}` | clears the slot (and the `image`/`profile_image` fallback when `neutral`) and deletes the file |

Handlers: `routes/graph_ops.py` (`handle_upload_node_image`,
`handle_remove_node_image`, `_expression_slug`, `_delete_managed_image`).
Files are real files, never base64 in the scenario.

Back-compat: an upload with no `kind`/`expression` behaves exactly like the old
single-image endpoint (full body, `neutral`) and sets `image`.

---

## Library round-trip

The pack travels with the character between library and world:

- **Spawn** (`engine/effect_handlers/spawn.py`, `handle_spawn_character`) copies
  `image`, `profile_image`, and `expressions` from the library data onto the
  spawned character node.
- **Import from library** (`routes/library_ops.py`,
  `handle_library_import_character`) copies the same keys.
- **Refresh from library** (`_refresh_character`) re-applies them from the entry.
- **Save to library** (`static/js/inspector/agent-view.js`,
  `_buildCharacterCard` + `_saveCharacter`) includes `expressions`, `image`, and
  `profile_image` in the diffable character card.

---

## Editor UI

The gallery renders in the character's **🖼️ Images** tab (`AV._renderImagesTab`,
task-512), as a grid of cards — one per expression key, each with a thumbnail, its
three actions, and its name. It has a **Profile / Full-body** tab switcher, an
"add expression" field for custom keys, and a **"Split sheet"** button.

**Re-filing art between expressions.** Each card has three actions: **⬆ replace
the image** (clicking the card or pressing Enter/Space), **🗑 remove the image but
keep the expression**, and **✕ delete the expression key and its image file(s)**.
Clicking the **name** re-files the expression under a new key, and the image
moves with it — that is the fix for a sheet that was sliced into the wrong
labels, since it needs no re-upload. Enter commits, Esc cancels.

The card is a `<div>` with an explicit click handler, deliberately **not** a
`<label>`. A `<label>` takes its labelled control as the first *labelable*
descendant, and a `<button>` is labelable — with the 🗑 ahead of the file input in
document order, Chrome activated the delete button, so clicking an image deleted
it instead of opening the picker. This was live-verified, not inferred: one click
produced two events, the `IMG` and a generated `BUTTON.btn-danger`.

Re-filing is a **property write, not a file move** — the image stays exactly
where it is and only the key it is filed under changes — so it reuses the generic
node `PATCH` rather than adding an endpoint, and it moves the whole slot so
renaming a profile expression does not orphan the full-body art filed under the
same key. The `neutral` slot is mirrored onto `profile_image` / `image` for the
graph thumbnail and simple avatars, so the write keeps those in step. A rename
onto a key that already holds art is **refused** with a message rather than
silently overwriting a picture. Deleting a key delegates to the existing
per-kind remove, once per kind, because a key holding both a profile and a
full-body image only disappears after the second call.

**Sheet splitting.** A character's art often arrives as one grid contact sheet.
The splitter (`static/js/inspector/sprite-sheet.js`) crops it in the browser with
a canvas and uploads each tile to its own slot through the same single-image
endpoint, so nothing new is stored server-side.

**The grid is a frame plus interior dividers, not a rows × cols count** (task-678).
A count describes exactly one shape — `width/cols × height/rows` over the whole
sheet — so it cannot fit a title banner, an outer margin, or panels of different
sizes side by side, which is what nearly every real reference sheet is. The
geometry lives in `static/js/inspector/sprite-sheet-geometry.js` as pure
functions (`cutsFromGrid`, `cellsFromCuts`, `clampCuts`, `recountCuts`,
`moveDivider`, `addDivider`, `removeDivider`, `hitDivider`, `guttersFromProfile`,
`cutsFromProfiles`, `profileRects`), and `computeCells` is now a thin wrapper
over it so the count-based entry point and the dialog cannot disagree.

**Two views, side by side.** The sheet with its overlay is on the left; on the
right is a live strip of the **actual crops** with their slot names, so a cut
that lands on an eyebrow is visible before anything is uploaded. Unnamed cells
are drawn dimmed and marked `skip`. `Fit` / `100%` scale the sheet, and the
preview pane scrolls, so a tall sheet is actually readable.

**Dragging is the primary control** (the same shape as the WorldPainter grid
adjust):

- the **frame** — 4 corners and 2 grips per edge — fits the grid onto the art and
  off a banner or footer, with no wasted cell;
- an **interior divider** makes rows or columns uneven, which is how a wide
  full-body panel sits beside a column of small detail panels in one grid;
- a press **inside a cell adds** a divider on both axes there; **double-clicking a
  divider removes** it. Rows/cols inputs still add and remove lines.
- A press near the frame boundary is a frame grip; a press away from it is a
  divider. That rule exists because an even grid puts a divider exactly where a
  midpoint handle would sit, which made the north and south frame edges
  unreachable.
- Dragging is tracked on `document`, not the canvas, so a resize can travel past
  the image — the same fix WorldPainter needed.

Moving or resizing the frame re-spaces the interior dividers over the new frame,
and excluding a banner drops the dividers that fall outside it.

**✨ Auto-fit proposes a grid from the sheet's whitespace.** It profiles the ink
per row and per column against the sheet's modal (not assumed-white) background,
trims a uniform outer margin to the content bounding box, and turns blank runs
into dividers. Two rules keep it honest on real art, both measured against a
1200×900 four-by-three expression sheet with 18px gutters:

- a gutter must have **content on both sides** within a flank, or the blank space
  below the last row of panels becomes a divider;
- a proposal of more than 16 dividers per axis is discarded as art whitespace,
  and the caller falls back to the even grid.

It proposes; it never asserts. Every value it sets stays draggable, and a sheet
with no clean whitespace falls back to the current rows × cols with a status
message saying so.

**Draw boxes** remains the escape hatch for genuinely irregular layouts, but an
existing box can now be moved and resized instead of deleted and redrawn.

`parseNames` maps tile order to slugs and leaves blank entries un-uploaded;
`defaultNames`/`defaultNameFor` prefill the canonical emotion order (then
`slotN`). Names are held parallel to the cell list, so nudging a divider never
renames a tile the author already named. Because a sheet's captions may not match
the canonical keys (for example `excited` where the UI uses `aroused`), the names
are editable before upload rather than hardcoded. The pure geometry is tested in
`tools/unit/test_sprite_sheet_geometry.js`, which includes a guard that the new
model reproduces the old `computeCells` output exactly, shape for shape.

Helpers live in
`static/js/inspector/helpers.js` (`renderExpressionSection`,
`setExpressionImage`, `clearExpressionImage`, `addExpressionKey`).

---

## Files

| Layer | File |
| --- | --- |
| Upload / remove | `routes/graph_ops.py`, `routes/graph.py` |
| Spawn copy | `engine/effect_handlers/spawn.py` |
| Library import / refresh | `routes/library_ops.py` |
| API client | `static/js/api.js` |
| Gallery + resolver | `static/js/inspector/helpers.js` |
| Sheet splitting | `static/js/inspector/sprite-sheet.js` (+ `static/js/inspector/sprite-sheet-geometry.js`, `tools/unit/test_sprite_sheet_geometry.js`) |
| Inspector placement + save card | `static/js/inspector/agent-view.js` |
| Avatar by emotion | `static/js/agent-lens.js` |
| Live art resolver + portrait viewer | `static/js/character-art.js` (+ `tools/unit/test_character_art.js`) |
| Tests | `tests/test_character_expressions.py` |

---

## Known limits

- Only the emotion keys select automatically, via the character's current
  emotion. Action keys (`attack`, `sleeping`) are stored and selectable but
  nothing sets an action as the active art yet (there is no "current action
  expression" the way `emotion.current` is set).
- Damage resistance / nonmagical-weapon immunity for incorporeal undead is not
  implemented (tracked in the character dev tasks).

## Related

- [[Characters/Emotion & Affect System|Emotion & Affect System]] — supplies the
  emotion keys the avatar follows
- [[UI & Settings/Inspector Panels|Inspector Panels]] — where the editor lives
- [[Characters/Characters Overview|Characters Overview]]
