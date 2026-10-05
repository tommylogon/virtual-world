---
group: Characters
---

# Character Expression Packs (profile + full body per emotion/action)

**Filed**: 2026-09-22
**Priority**: Medium
**Status**: Done — implemented 2026-09-22

## Shipped

A character node carries live art keyed by emotion or action — a
SillyTavern-style pack:

```
"expressions": {
  "neutral": { "profile": "...", "full": "..." },
  "angry":   { "profile": "...", "full": "..." },
  "attack":  { "full": "..." }
}
```

`image` (full-body neutral) and `profile_image` (profile neutral) remain the
legacy fallbacks, so single-image characters and non-character nodes are
unchanged.

- **API** (`routes/graph_ops.py`, `routes/graph.py`): `POST
  /api/graph/node/<id>/image` takes `kind` (`profile`|`full`) + `expression`;
  `POST /api/graph/node/<id>/image/remove` clears a slot and deletes the file.
  Real files under `static/images/nodes/`, never base64.
- **Resolver**: `expressions[emotion].profile → neutral → profile_image → image
  → icon`. Graph thumbnail keeps `image`.
- **Library round-trip**: spawn (`engine/effect_handlers/spawn.py`), library
  import/refresh (`routes/library_ops.py`), and the save card
  (`_buildCharacterCard` + `_saveCharacter`) all carry the pack.
- **Editor** (`static/js/inspector/helpers.js` + `agent-view.js`): gallery in
  the character header **under the name** (moved out of Advanced), Profile /
  Full-body tabs, one row per expression with upload/clear + "add expression".
- **Avatar** (`static/js/agent-lens.js`): the header avatar follows the
  character's current emotion.
- **Tests**: `tests/test_character_expressions.py` (10).
- **Docs**: [[Characters/Character Images & Expression Packs]] (technical),
  [[UI & Settings/Inspector Panels]] (user guide),
  [[ScenarioCreationGuide]] §2.4 Character.

## Follow-ups (not done)

- Action keys (`attack`, `sleeping`) are stored and selectable but nothing
  drives them at runtime yet — a "current expression" hook is needed, analogous
  to `emotion.current`.
- The graph thumbnail still uses the full-body `neutral` rather than the
  current emotion.

## Related

- [[Characters/Emotion & Affect System]]
