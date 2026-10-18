---
type: task
status: cancelled
area: characters
priority: medium
horizon: next
goal: Nicknames (aliases) are visible in the Persona tab and survive a library and scenario round trip.
wiki: "[[Persona]]"
related: [task-865]
---

# task-871: Surface aliases in the Persona tab and round-trip them

**Filed:** 2026-10-18
**Related:** task-865

<!-- deps:start -->
**Related:** [[task-865-rename-the-persona-block-key-from-appearance-to-persona]]
<!-- deps:end -->

## What

ViWo already has aliases. `name <target> as <alias>` (`routes/action_handlers.py:1249-1309`) writes `properties["aliases"]` on a node, and `engine/matching.py:113 node_aliases()` reads them. So a nickname IS an alias and the storage exists.

The gaps: aliases are written only in-game, are absent from the Persona tab, and are absent from `_buildCharacterCard`, so a library save drops them.

## Why

Nicknames are authored character data. They must be visible at authoring time and must survive a round trip; today a Save to Library silently loses them.

## How

1. Show aliases in the Persona tab's identity fold as an editable chip list.
2. Include `aliases` in `_buildCharacterCard` (`static/js/inspector/agent-view.ts:2178-2242`, which currently omits several fields) and read them back in `handle_library_import_character` (`routes/library_ops.py:879`) onto the node.
3. Keep `node_aliases` the single reader; do not add a second alias field.

## Browser UI and intended live verification

The Persona tab's identity fold. Live steps: add an alias, Save to Library, re-import the character, confirm the alias is present; do the same across a scenario save / load.

## Steps to verify

1. Add an alias in the Persona tab, then Save to Library and re-import.
   - expected: the alias is present after re-import.
   - observed: TODO
2. Round-trip through a scenario save / load.
   - expected: `properties["aliases"]` survives.
   - observed: TODO

## Acceptance

- [ ] Aliases are editable in the Persona tab.
- [ ] Aliases round-trip through both the character library and a scenario save / load.
- [ ] `node_aliases` remains the single reader of the alias property.

## Files

- `static/js/inspector/mind-view.ts`
- `static/js/inspector/agent-view.ts`
- `routes/library_ops.py`
- `tests/test_character_appearance.py`

## Retracted 2026-10-18

Duplicate, and its premise was wrong. `task-447` (Character nicknames / aliases (authoring + resolution), inprogress) already implements this: the inspector has a 🔖 Aliases field (`renderAliasesSection`, comma/`|` separated, writes `properties.aliases`), persistence round-trips through save/load and the library card, and `node_aliases` is the reader. This card claimed aliases are "written only in-game" and "absent from the inspector"; both were false.

The one surviving delta is placement (447 puts the field in the Bio tab; the Persona tab is a nicer home) plus 447's own open items (an agent can't set an alias in practice; aliases are not displayed in the HTC). Those belong on task-447, not a parallel card.
