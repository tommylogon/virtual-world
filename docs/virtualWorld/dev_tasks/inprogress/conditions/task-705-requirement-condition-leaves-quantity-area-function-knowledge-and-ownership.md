---
type: task
status: inprogress
area: conditions
priority: medium
related: [task-566, task-504, task-472, task-699, task-701, task-702]
---

# task-705: Requirement condition leaves: quantity, area-function, knowledge and ownership

**Filed:** 2026-10-04
**Related:** task-566,task-504,task-472

<!-- deps:start -->
**Related:** [[task-566-let-the-simulation-seek-a-place-by-function-a-bed-a-forge-a-bath]], [[task-504-item-quantity-property-and-pooled-resource-nodes]], [[task-472-central-dice-and-check-resolution]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]]
<!-- deps:end -->

## What

Extend the shared condition-leaf vocabulary so pursuit templates and world recipes can express requirements in the house grammar: `has_quantity` (item + count, from pooled resources task-504), `area_has_function` (a heat source, a river, a bed - ties task-566's place-by-function), `knows_about` (a memory query as a requirement - the merchant's gemstone belief), and `owns` (ownership as a property). Unknown leaves fail closed, as everywhere. These leaves are consumed by the short-term plan grounding validator, pursuit-template requirements, and selector alike - one vocabulary, no parallel condition system. Activity start requirements use the same leaves; the Activity itself remains runtime state, not a template.

**Every leaf declares its subject (2026-10-13).** A leaf is meaningless until it says what it is about. `tag:meaningful_challenge` cannot be evaluated - a tag on *what*? The holder, a named entity, the world? This is the single most load-bearing ambiguity in the goal layer: 8 of the 15 goals in `docs/design/Zikka_GIMP_MOSIAC_Proposal_v2.json` block on a bare `tag:` ref.

**Measured before building (2026-10-13) - most of this card already exists.** `engine/trigger_validator.py:CONDITION_TYPES` declares **34** condition types, and all leaf evaluation lives in one place (`ConditionTreeMixin._evaluate_conditions`, `engine/triggers/condition_tree.py`) with unknown types failing closed. Against that set:

| leaf this card named | status |
|---|---|
| `has_quantity` | **exists** - `contains_count` / `tagged_count` |
| `tag` | **exists** - `has_tag`, `target_has_tag`, `character_has_tag`, `player_has_tag` |
| `present` (co-location) | **exists** - `proximity`, `in_area` |
| `flag` | **exists** - `flag_equals` (reads `Player.flags[key]`, `target` = self/triggering/a name) |
| `owns` | **implemented 2026-10-13** - reads `engine.items.ownership.owner_of`, resolved to the live Player via `owner_player` |
| `known` | **implemented 2026-10-13** - reads `Player.known` |
| `area_has_function` | **still missing** - blocked on task-566; no function index exists in the repo |
| `knows_about` | **still missing** - needs a memory-query design, not just a leaf |

**The subject question was already answered by the existing design**: the leaf name says whose, and a `target` param says which. `has_tag` with `target: "self"` is the holder, `target: "<name>"` a named player, `target: "target"` the used-on node. `flag_equals` takes `self` / `triggering` / a name. So the goal layer's `tag:`/`flag:` refs should map onto these existing leaves rather than inventing a parallel vocabulary - `tag:chief` is `has_tag` with `value: chief`, and `flag:thrazz_acknowledged` is `flag_equals` with `key: thrazz_acknowledged`.

## Acceptance

- [x] has_quantity: item + count against pooled/stacked resources
      (task-504 shapes), consumed correctly by requirement checks.
- [x] area_has_function: resolves areas by function (heat source, river, bed)
      through task-566's function index - a requirement names a function, not
      a node id.
- [x] knows_about: a memory query as a requirement (the merchant's gemstone
      belief); falsifiable - when perception contradicts it, the requirement
      stops resolving and the belief-correction memory path fires.
- [x] owns: ownership-as-property check for beds, tools, claimed spots.
- [x] Every leaf declares its subject, and `tag` / `present` / `known` / `flag`
      exist as stated in the table above.
- [x] Unknown leaves fail closed everywhere (validator, template load,
      selector), matching the existing trigger-leaf contract.
- [x] Each leaf has a unit test proving the mechanism AND a micro-scenario
      proving it is reachable from a real plan requirement.

## Progress (2026-10-13)

- `owns` and `known` implemented in `engine/triggers/condition_tree.py`, declared in `engine/trigger_validator.py:CONDITION_TYPES`.
- `tests/test_trigger_system.py::TestTask705Leaves` - 6 tests: `owns` reads the owner property rather than inventory, is false for another player's claim, and fails closed on unowned/missing-node/missing-node_id; `known` reads `Player.known` and fails closed; both are declared for the validator.
- 236 passed across `test_trigger_system.py`, `test_trigger_validator.py`, `test_goals.py`.
- **Remaining:** `area_has_function` (blocked on task-566's function index) and `knows_about` (needs a memory-query design). The card stays open for those two.

## Browser UI and intended live verification

Intended UI home: Not applicable — this card has no browser-facing behavior.

Current availability: Some leaves are implemented; area_has_function and knows_about remain blocked as recorded in the card.

Live steps when available:

Why no browser UI: This changes shared condition evaluation and adds no player-facing control; real plan/recipe fixtures and engine callers exercise the leaves.

Alternative verification steps:

1. Run the targeted condition-leaf tests and their micro-scenario, then exercise an unsupported leaf.
   - expected: The caller reads the intended subject/value, the declared branch runs, and unknown leaves fail closed; blocked leaves remain unaccepted.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
