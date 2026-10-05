---
type: doc
tags: [system/ui, topic/validation]
---

# Validator & Issues

**Task:** [[dev_tasks/done/library/task-323-library-lint-validator|task-323]] · [[dev_tasks/done/ui/task-393-validator-triage-panel|task-393]] · pending: [[dev_tasks/todo/ui/task-443-validator-mismatch-recalibration-and-info-section|task-443]]

Scenario lint, mismatches, and authoring blockers. There is **no single validator** —
there are four independent instruments, and only one of them is wired to a UI:

| Instrument | Scope | Runs | UI |
|---|---|---|---|
| `engine/trigger_validator.py` (`TriggerValidator`) | the live world graph | `GET /api/triggers/validate` | **yes** — Validator panel |
| `engine/nl_editor_validation.py` | staged NL-editor ops, pre-Apply | inside `POST /api/graph/batch` | yes — the Apply gate bubble |
| `tools/lint_library.py` | `data/library/**.json` on disk | CLI | no |
| `tools/validate_scenario.py` | one scenario JSON file, offline | CLI | indirectly — scenario Audit button |

---

## 1. TriggerValidator — the live world

`engine/trigger_validator.py` (825 lines) walks the graph and returns
`{severity, code, message, source_node_id}`. `validate()` composes four passes:

    _validate_trigger_edge()  +  _validate_way_authoring()
    _validate_mechanical_items() + _validate_library_sync()  →  _filter_ignored()

Issues are sorted error → warning → info (`SEVERITY_ORDER`).

**Trigger wiring**

| Code | Severity |
|---|---|
| `empty_trigger` (no effects — will do nothing) | warning |
| `orphan_trigger_edge` (edge from a missing node) | info |
| `dangling_trigger_edge` (target node missing) | error |
| `trigger_edge_wrong_target_type` | error |
| `stale_trigger_copy` (a trigger copy left behind) | warning |

**Trigger semantics** — `unknown_trigger_type`, `unknown_condition_type`,
`unknown_effect_type`, `empty_effect_message`, `tag_not_in_world`,
`condition_missing_item`, `condition_missing_node`, `missing_effect_node`,
`missing_effect_item`, `missing_effect_character`, `teleport_missing_area`.
Lookups are tolerant by design: `_item_exists` / `_node_name_matches` / `_area_matches`
/ `_library_item_exists` / `_library_character_exists` accept either a node id or a
display name, because spawn and give hydrate from the library at runtime.

**Way authoring** (all `info`, explicitly optional — the engine has defaults):
`way_missing_description`, `way_missing_pass_message` (`WAY_NODE_FIELDS`), plus
per-side `way_missing_cardinal` and `way_missing_view_direction` on the area→way
connection edges. Only edges where `edge.target == way.id` are checked, because the
reverse way→area edges carry the direction command only.

**Mechanical items** — `mechanical_tag_missing_props` (warning, or info when
`DEFAULTED_MECHANICAL_DEFAULTS` applies). `MECHANICAL_REQUIREMENTS` maps the tags
the engine reads to the properties it needs: `light_source→light_level`,
`heat_source→target_temperature, heating_rate`, `sound_source→sound_level, sound_pattern`,
and so on.

**Library drift** — `library_entry_missing` (warning) and `library_mismatch`
(warning) compare an instanced node against its template over `LIBRARY_SYNC_PROPS`
(name, description, tags, actions, uses, weight, equip_slots, current_state,
light_level, target_temperature, heating_rate, contents, aliases). `_props_match`
tolerates the library `actions` string → node list hydration normalization.

### Dismissals expire on edit

`POST /api/triggers/ignore` writes the code into the node's `ignored_issues` list
plus `_ignored_at` (`routes/triggers.py:24`). `_filter_ignored` hides the code
**until the node is touched again** — if `node.updated > _ignored_at` the issue
resurfaces, so "I dismissed it, then I changed the node" cannot silently hide a
fresh problem.

## 2. Where issues surface in the UI

`static/js/validator-panel.js` (488 lines) is the triage surface, exposed as
`window.ValidatorPanel` and `VW.validatorPanel`. It mounts into
`#validator-list` / `#validator-count` (`templates/index.html:155-158`) and:

- **Groups two ways** — by node (one expandable row per way/item/area) or by code,
  so "254 issues" visibly collapses to piles like `way_missing_cardinal ×58`. Mode
  persists in `localStorage['vp-group']`.
- **Per-row actions** — 🔍 jump (`graphManager.showNodeAndFocus`), ⚙ quick-fix for
  `mechanical_tag_missing_props` (writes `light_level:'dim'`, `target_temperature:30`,
  `heating_rate:0.5`), 🧹 remove empty trigger stubs (one `ApiClient.batchGraph`, so
  one Undo), 🚫/🔓 dismiss / restore.
- **Fix all** — batches a mechanical fix across a code as a single undo; way
  orientation instead runs `clear_way_fix_fields` and then hands off to the way
  inspector's per-node ✨ Improve, one at a time (`fixAllWayOrientation`, task-395).
- **A derived progress bar** — recomputed each render from live graph + live issues
  (`_progressHtml`): `audited` = every item/way/area node, `clean` = one with no
  undismissed issue. It cannot drift.
- **Inline in the inspector** — `validateNodeInline()` renders the flat one-line
  list for a single node, and "No broken references ✅" when clean.
- **Auto-refresh** is debounced 2s off `appEvents 'state:updated'`.

Two more routes use the same validator: `POST /api/triggers/validate-definition`
(an unsaved trigger definition from the editor) and `POST /api/import/audit`
(builds a throwaway `VirtualWorld`, runs the validator against an **unloaded**
payload, and returns grouped severity counts — the backend of import preview).

## 3. Library lint — `tools/lint_library.py`

Ten named checks over `data/library/`, split by exit code:

**Errors (exit 1):** `dead_interests` (character interest_tags matching zero item
tags), `missing_slots` (clothing/armor without `equip_slots`), `tag_case_drift`,
`broken_contents` (item contents referencing missing library ids),
`unauthored_consumables` (edible/drinkable whose consume trigger restores nothing),
`resource_pools` (pooled-resource nodes that cannot be harvested correctly).

**Warnings (exit 0):** `singleton_tags`, `tag_id_charset`, `area_tag_gaps`,
`dead_fears` (fear_tags no item/area/character/trait key carries, so
`engine/fear.py` can never match them).

`--check <name>` selects checks; `--data-dir` points at a fixture. Nothing runs it
automatically.

## 4. Scenario file lint — `tools/validate_scenario.py`

Offline, one file, six pass families: `validate_areas` (environment keys present),
`validate_ways` (`pass_message`, resolvable `area_from`/`area_to`, an incoming
connection edge), `validate_items` (weapon → damage, armor → `equip_slots`,
container → `max_weight_capacity`), `validate_characters` (description),
`validate_triggers` (target present, incoming `triggers` edge), `validate_players`
(`current_area` resolvable). `_area_keys()` deliberately accepts **both** area ids
and display names, matching runtime resolution.

## 5. NL-editor Apply gate — `engine/nl_editor_validation.py`

Documented in [[UI & Settings/NL Editor|NL Editor]]; it validates staged ops
against the live graph before the batch route touches anything. Unknown trait ids,
edge endpoints, duplicate area names, non-slug library ids, non-writable
registries, and a mature-content gate are `error`; id casing and unknown item
actions are `warning`.

---

## Pending

[[dev_tasks/todo/ui/task-443-validator-mismatch-recalibration-and-info-section|task-443]]
records what task-393 specified but never built, and its first item is a
correction of task-393's own claim:

1. **`library_mismatch` is not recalibrated.** It was meant to fire only on
   *mechanical* drift and to leave `light_level` / `contents` alone, since
   diverging on those is the normal authoring flow. `LIBRARY_SYNC_PROPS` still
   carries them and the severity is still `warning`.
2. **No "mark instance as intended" action** — no route, property, or UI.
3. **No default-collapsed info section** — grouping sorts by worst severity but
   info rows render inline, so the noise floor stays high.
4. The manual browser pass task-393 never had.

---

## Code map

| Module / route | Role |
|---|---|
| `engine/trigger_validator.py` | `TriggerValidator.validate()`, `_filter_ignored()`, `validate_trigger_props()` |
| `routes/triggers.py:8` | `GET /api/triggers/validate` (`?node_id=` filter) |
| `routes/triggers.py:24` | `POST /api/triggers/ignore` — dismissal + `_ignored_at` |
| `routes/triggers.py:87` | `POST /api/triggers/validate-definition` |
| `routes/triggers.py:102` | `POST /api/import/audit` — validate an unloaded payload |
| `static/js/validator-panel.js` | triage panel: grouping, quick-fix, dismiss, fix-all, progress |
| `tools/lint_library.py` | 10 library checks, error/warning exit codes |
| `tools/validate_scenario.py` | offline scenario-file lint |
| `engine/nl_editor_validation.py` | staged-op pre-Apply gate |
| `tools/character_loadout_check.py` | separate shape gate on character `equipped`/`inventory` |

---

## Related docs

- [[Triggers & Effects]] — what the trigger checks are about
- [[Library System Overview]] — templates the drift check compares against
- [[UI & Settings/NL Editor|NL Editor]] — the pre-Apply gate
- [[Tags System]] · [[Domain & Role Tags]] — mechanical tags and what they require
- [[Doors & Connections]] · [[Way Properties]] — the way authoring checks

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[validator-issues|Validator & issues]] (#63)

**Neighbouring notes** — [[Engine Config]], [[Event Log Export]], [[Event Stream]], [[Inspector Panels]], [[NL Editor]], [[Recent Edits & Undo]]

<!-- connected:end -->
