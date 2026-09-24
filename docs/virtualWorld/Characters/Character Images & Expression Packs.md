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

The gallery renders **in the character inspector header, directly under the
name** — not in a tab. It has a **Profile / Full-body** tab switcher and one row
per expression key with a thumbnail, an upload control, and a clear button, plus
an "add expression" field for custom keys, and a **"Split sheet"** button.

**Sheet splitting.** A character's art often arrives as one grid contact sheet.
The splitter (`static/js/inspector/sprite-sheet.js`) crops it in the browser with
a canvas and uploads each tile to its own slot through the same single-image
endpoint, so nothing new is stored server-side. Two modes handle different
layouts: **Even grid** (rows x cols over the whole sheet — a clean 4x3 face
sheet) and **Draw boxes** (drag one rectangle per panel, for art packs that mix a
large turnaround or magic pose beside smaller expressions, where no even grid
fits); `clampBox` normalises and clamps each dragged box. `computeCells`
partitions the sheet into rows x cols so the tiles cover it exactly (no
gaps/overlap, rounding remainder absorbed by the last row/column), and
`labelTrim` drops a fraction off the bottom of every cell for the caption banner
(grid mode only — in box mode you simply box the art and leave the caption out).
`parseNames` maps tile order to slugs and leaves blank entries un-uploaded;
`defaultNames`/`defaultNameFor` prefill the canonical emotion order (then
`slotN`), so a drawn box gets a sensible name you can edit. Because a sheet's captions may not match the canonical keys (for
example `excited` where the UI uses `aroused`), the names are editable before
upload rather than hardcoded. The pure geometry/naming helpers are tested in
`tools/unit/test_sprite_sheet.js`.

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
| Sheet splitting | `static/js/inspector/sprite-sheet.js` (+ `tools/unit/test_sprite_sheet.js`) |
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
