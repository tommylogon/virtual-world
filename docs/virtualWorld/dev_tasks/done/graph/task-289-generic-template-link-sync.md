# Task 289 — Generic Template-Link & Sync System for All Node Types

## Status

**Library → World half DONE (2026-10-01).** Done together with **task-317** — the
two cards describe the same remaining work from two directions, and splitting it
was how `library_id` ended up with three different id-resolution behaviours. See
"Result" below.

World → Library half is task-317's, and its safety rules were already shipped
2026-08-20 and are preserved.

## Goal

Generalize the existing `refresh-from-library` item sync into a first-class template-link system that works for **areas, ways, items, and characters**. Authors can bind a placed node to a library template, sync changes from that template, and break the link to make the node standalone.

## Why

- `labs.json` currently has 36 rooms with many near-duplicates (e.g., `Task 3 - area 1 closed door` / `open door`). Drift between them is already happening.
- Only items have a partial `library_id` + `refresh-from-library` endpoint. Areas, ways, and characters have no equivalent.
- Without a template link, updating a canonical room/way/item/character requires manually editing every placed copy.

## Design Decisions

1. **`library_id` on every node** — a string field storing the source library file stem (e.g., `lab_table`, `blackout_goggles`). Absent or empty = standalone.
2. **`POST /api/nodes/<node_id>/sync-from-library`** — generic endpoint that:
   - reads the current library file by `library_id`
   - overwrites mutable fields on the node to match the library definition
   - returns a diff of what changed
3. **`POST /api/nodes/<node_id>/break-template-link`** — strips `library_id` and marks the node as standalone. Does not alter node data.
4. **Mutable field whitelist per node type** — not everything should sync. Example:
   - **items**: `name`, `description`, `tags`, `triggers`, `equip_slots`, `defense`, `damage`, `insulation`
   - **areas**: `name`, `description`, `environment`, `properties.tags`
   - **ways**: `name`, `description`, `properties`
   - **characters**: `name`, `description`, `stats`, `skills`, `traits`, `behaviors`
   - Never sync: `id`, `type`, spatial edges (`in`, `on`, `beside`, `connection`), `current_state`, `position`, player-specific data
5. **Frontend UX**:
   - Inspector panel shows "Linked to library: `<name>`" with a **Sync** button and a **Break Link** button.
   - Library browser shows "X placed instances" next to each entry.
   - Sync produces a toast with "Updated N fields" or "Already up to date."

## Implementation Steps

1. **Backend: generic sync endpoint**
   - Add `POST /api/nodes/<node_id>/sync-from-library` in `routes/nodes.py` (or equivalent).
   - Add `POST /api/nodes/<node_id>/break-template-link`.
   - Extract mutable-field logic into `engine/sync.py` with a registry per node type.
   - Reuse the existing item `refresh-from-library` logic as the template.

2. **Backend: `library_id` on all node types**
   - Ensure `area`, `way`, `character`, and `item` nodes all accept and persist `library_id`.
   - World serialization/deserialization must preserve it.

3. **Frontend: inspector integration**
   - Show template-link status and action buttons in the area/way/item/character inspector panels.
   - Wire buttons to the new endpoints.

4. **Frontend: library browser**
   - Show instance count for each library entry.
   - Allow bulk "Sync all instances" from the library view.

5. **Testing**
   - Unit tests for sync diff, break-link, and mutable-field whitelisting.
   - Smoke test: place an item from library, edit its description, sync, verify description reverts; break link, edit, sync again, verify no change.

## Out of Scope

- Template inheritance / variants (design #3 from earlier discussion). That is a follow-up task once basic sync is stable.
- Override tracking (design #2). Can be added later if authors need partial sync.

## Result (2026-10-01)

Every remaining item on this card is implemented, and the three claims in the old
Status were re-measured first rather than trusted: `refresh-to-world` did already
dispatch all four types, and `break-template-link` and `engine/sync.py` did
genuinely not exist anywhere.

### What was actually broken

The card framed the gap as "break-link endpoint + a per-type whitelist". The
whitelist was real but was not the interesting part. Measuring the four
`_refresh_*` handlers showed the **link itself** had no single definition:

| Node type | How it guessed its template before |
|---|---|
| item | never — explicit id only |
| way | slugified the node's name |
| area | stripped an `area_` node-id prefix, then fell back to the name |
| character | fell back to its display name |

So the same operation on four node types could resolve to three different
templates, or to none. And there was no way to unbind any of them, so "this copy
is mine now" was unexpressible — an author's hand-fix was one stray Refresh away
from being undone, with nothing to say otherwise.

### Changes

- **`engine/sync.py`** (new) — the contract. `TemplateSpec` per type (registry,
  mutable-field whitelist, how it resolves an id, whether it syncs onto the node
  or its `Player`), `resolve_template_id`, `link`, `break_template_link`,
  `locked_fields`, `changed_fields`, and `NEVER_SYNCED`.
- **`routes/library_ops.py`** — the four handlers now call
  `sync.resolve_template_id` instead of each doing its own fallback, and
  `handle_break_template_link` is new.
- **`routes/library_routes.py`** — `POST /api/library/break-template-link`.
- **`static/js/shared/template-sync.js`** — a **🔗 Break Link** button, rendered
  only when the node actually has a link (on an unlinked node it could only ever
  report "nothing to break"), with a confirm that says the data is kept, plus a
  "was linked to `<id>`" provenance line after a break.
- **`static/js/api.js`** — `ApiClient.breakTemplateLink`.

The per-type *apply* bodies stayed in the handlers on purpose. They genuinely
differ — a character's fields land on its `Player` through a coercion table, a
way's are coerced booleans — and folding them into one loop would have been a
refactor for its own sake. What was unified is the part that had drifted.

### Two decisions taken rather than assumed

**A guessed sync now records the link.** A character with no link would guess a
template from its own name, sync from it, and *not* write `library_id` — so the
node kept reading as unlinked while plainly having a template, and Break Link had
nothing to break. All four handlers now record the template they actually synced
from, and `refresh-to-world` returns `template_id` and `linked`.

**Breaking a link does not lock the node's fields.** It is tempting to protect
every mutable field on break. That would alter the node (this card says a break
changes no data) and would make a later deliberate re-link + refresh silently
apply nothing, which reads as a broken button. A break removes the link and
records `template_broken_from`; an author who wants fields spared names them in
`locked_fields` themselves.

### `current_state` — a real disagreement, recorded not resolved

This card's design says never sync `current_state`. The code syncs it for both
items and ways. For a **way** the card is right: `open`/`closed`/`locked` is
runtime state, so a sync re-opens a door an NPC closed. For an **item** it
carries authored content (`"hidden"` vs `"normal"`), and it has shipped that way
since the item sync was written. Unifying changes what an existing refresh does,
so it is a decision to make deliberately. It is recorded in
`engine/sync.py::NEVER_SYNCED` and pinned by a test in
`tests/test_template_links.py` so the disagreement cannot drift unnoticed.

### Live browser verification

Drove the real UI on a fresh instance, not the API alone:

1. `way_bathroom_door` had no link. Refreshed from `bathroom_door` →
   `linked: true`, `library_id: "bathroom_door"`, and the template's description
   appeared in the inspector.
2. Opened the way inspector. The footer read **💾 Save to Library · 🔄 Refresh
   from Library · 🔗 Break Link**.
3. Clicked **🔗 Break Link** (it is below the fold — the panel had to be
   scrolled, and the row is only rendered once the panel is scrolled to its
   bottom). Confirm read: *"Stop syncing "bathroom door" from library template
   "bathroom_door"? The node keeps everything it has now. It will simply stop
   taking updates from the template."*
4. After: the **Break Link button is gone** (nothing left to break), the panel
   reads **"was linked to bathroom_door — this copy no longer syncs"**,
   `library_id` is null, `template_broken_from` is set, and the description is
   **unchanged**. The event stream logged
   `Unlinked "bathroom door" from library template "bathroom_door". Data kept.`

### Tests

`tests/test_template_links.py` (26 tests): the spec contract, the
identity-never-syncs invariant, resolution per type, lock parsing, break-link
preserving data, the refusal to auto-lock, and the `changed_fields` diff.

Gates: `npm run lint` clean · `node tools/unit/run.cjs` 465 passed · full pytest
**12 failed / 6570 passed**, the identical 12 names a clean `master` worktree
fails, so none are mine.

### Still open

- **task-290** — variants and override tracking (`template_ref`). Deliberately
  not started: a field whitelist is not a variant system, and `290` scopes itself
  as the layer above `locked_fields`.
- **The `current_state` ruling** above.
- **Library browser instance counts** ("X placed instances" per entry) — part of
  this card's UX list, untouched; it belongs with task-290's authoring surface.
- Filed separately: **task-658** — `python tools/js_module_index.py --check` fails
  on `room-context.js` despite a complete header. Verified pre-existing on a clean
  `master` worktree (same message, exit 1), so not caused by this work.
