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

The graph thumbnail continues to use `image` (full-body neutral). Frontend
implementation: `InspectorHelpers.expressionImageFor()` and
`AgentLens._expressionAvatar()`.

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
an "add expression" field for custom keys. Helpers live in
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
| Inspector placement + save card | `static/js/inspector/agent-view.js` |
| Avatar by emotion | `static/js/agent-lens.js` |
| Tests | `tests/test_character_expressions.py` |

---

## Known limits

- Only the emotion keys select automatically, via the character's current
  emotion. Action keys (`attack`, `sleeping`) are stored and selectable but
  nothing drives them at runtime yet — a hook would set the "current
  expression" the way `emotion.current` is set.
- The graph thumbnail uses full-body `neutral`, not the current emotion.
- Damage resistance / nonmagical-weapon immunity for incorporeal undead is not
  implemented (tracked in the character dev tasks).

## Related

- [[Characters/Emotion & Affect System|Emotion & Affect System]] — supplies the
  emotion keys the avatar follows
- [[UI & Settings/Inspector Panels|Inspector Panels]] — where the editor lives
- [[Characters/Characters Overview|Characters Overview]]
