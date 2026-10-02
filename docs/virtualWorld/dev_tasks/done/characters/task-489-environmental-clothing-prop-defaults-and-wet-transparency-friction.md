---
type: task
status: done
area: characters
priority: low
---

# task-489: Environmental clothing: prop defaults and wet transparency/friction

**Filed:** 2026-09-23
**Related:** task-215

## Goal

Finish task-215: give item nodes default comfort/friction/coverage/opacity (opacity 0.8, coverage 0.8 when absent), and couple the existing wet state (condition 'wet', equipment_bonuses.py:107) to clothing opacity/friction so rain/swimming makes layers more see-through and changes friction, then triggers description regeneration. Friction->arousal trickle already ships (engine/tick_manager.py:1028) as does weather/wind/humidity.

## Acceptance

- [x] Item nodes expose `comfort`/`friction`/`coverage`/`opacity`, with
      `opacity`/`coverage` defaulting to 0.8 when absent, surfaced by
      `_equipment_detail_lines()`.
      **`coverage` is done** (one resolver, default 0.8, surfaced always).
      **`opacity` and `friction` are REFUSED** — see "The refusal" below, which
      is a decision rather than an omission.
- [x] The `wet` condition raises clothing `opacity` and changes `friction`.
      **Refused as numeric props; delivered through `current_state`**, which is
      task-215's own chosen mechanism and which task-489's "coordinate with
      task-215" invites.
- [x] The state change retriggers the equipment description when
      `world.auto_generate_descriptions` is on.
- [x] Arousal coupling stays `mature_content`-gated; **wetness itself is
      generic** and conjures no pleasure vital.
- [x] Tests for the prop defaults and the wet coupling — 16 in
      `tests/test_clothing_environment.py`, including four that pin the refusal
      so a later reader does not reinstate the cancelled props as a bug.

## The refusal: task-489 and task-215 contradict each other

This task was filed **2026-09-23**. task-215 was re-scoped the day before,
**2026-09-22**, with an explicit user decision that the numeric `opacity` and
`friction` properties are **cancelled** and layer visibility belongs on the item's
own description. task-489 asks for exactly those two properties, to be added and
surfaced, in a file whose "Related" line names task-215.

The decision is not only documented, it is **enforced by a live test**:

```python
# tests/test_equipment_system.py
def test_detail_lines_carry_description_not_opacity_or_friction(basic_setup):
    node.properties["opacity"] = 0.2
    node.properties["friction"] = 3
    ...
    assert "opacity" not in joined
    assert "friction" not in joined
```

It asserts they are not advertised **even when the item authors them**. So the
part of this task that asks for them would have had to break a standing user
decision that the repo encodes as a test. Doing that is not a scope call; it is
reversing a decision. Refused, and pinned by
`test_numeric_opacity_and_friction_are_still_not_advertised` so the next person
to read both files does not resolve the conflict the wrong way.

The rest of the task is implemented, and the *intent* behind "wet makes layers
more see-through" is delivered through the mechanism 215 kept.

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `engine/equipment.py` — `EquipmentSystem.coverage_of` (the default resolver);
  `_equipment_detail_lines` uses it and always surfaces `coverage`; the
  description **fallback** now carries an item's live state.
- `engine/effect_handlers/environment.py` — `handle_set_wet` soaks, marks
  `current_state`, and regenerates; helpers `_active_player_obj`,
  `_equipped_items`, `_mark_wet_current_state`, `_regenerate_wet_descriptions`.
- `tests/test_clothing_environment.py` — **new**, 16 tests.

### The coverage default is `body_parts.COVERAGE_EXPOSED_THRESHOLD`

0.8 is not an arbitrary midpoint — it is exactly the constant
`engine/body_parts.py` uses to decide whether a layer blocks skin contact. So an
item that says nothing is described *and* treated as a covering garment, and the
two cannot drift. A non-numeric or out-of-range value falls back to 0.8 rather
than propagating, because a garment whose coverage is `"sheer"` is written wrong.

### Wetness is a state, not a number

`WET_CURRENT_STATE = "soaked"` goes into `current_state` — the field 215 names as
kept, and the one the appearance prompt already renders. Two rules, both of which
a test forced:

* **A soak does not overwrite a state the author set.** `current_state` is a
  single field, so a coat already `"torn"` reads torn, not soaked. Wetness is
  still visible to the engine through the `wet` property, which is what the
  insulation penalty reads.
* **Drying removes only what a soak wrote**, so clearing the weather cannot
  delete `"torn"`.

### Two defects found while wiring it

1. **`set_wet` with no node named never soaked anything.** The branch read
   `game_state.active_player` — a **name string** — and passed it to
   `equipment.get_equipped_items`, which does not exist. Rain, wading and
   flooding therefore targeted nothing at all, silently, through a `except
   Exception` that swallowed the `AttributeError`. That is AGENTS.md's
   "never infer runtime behavior from existence" in its purest form: the code
   read correctly and did nothing.
2. **The description could not change even once the state was set.** The
   `ITEM DETAILS` block feeds the LLM prompt, but the *fallback* prose listed
   slot names only, so a soaked character regenerated to byte-identical text.
   "Wet -> description regenerates" looked unwired because the regeneration
   happened and produced nothing new.

### Verify

```
python -m pytest tests/test_clothing_environment.py -q                       # 16 passed
python -m pytest tests/test_equipment_system.py tests/test_clothing_environment.py \
  tests/test_auto_dress.py tests/test_armor_wear.py tests/test_body_parts.py \
  tests/test_equipment_api_edges.py -q                                       # 128 passed
```

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty — including
`test_detail_lines_carry_description_not_opacity_or_friction`, which is the test
this task refuses to break.


### Live verification — 2026-10-02, `python app.py` on `VW_PORT=4466`

```
=== 1. coverage defaults to 0.8, and the cancelled props stay absent ===
  detail line: - Waxed Coat (torso): Waxed cotton, holds off rain. [coverage 0.8]
  'opacity' advertised? False (must be False)
  'friction' advertised? False (must be False)

=== 2. a soak reaches the description ===
  wet           : True
  current_state : soaked
  description BEFORE: RainSoaker is wearing Waxed Coat on their torso.
  description AFTER : Waxed coat is soaked.
  changed? True

=== 3. drying does not wipe an authored state ===
  current_state after drying: torn (authored value preserved)
  wet after drying: False

=== 4. the soak-all path (no node named) now works ===
  coat wet: True
  hat  wet: True (was silently nothing before this change)
```

Row 1 is the refusal proved live on an item that authors both cancelled props:
they are silently absent while `coverage` defaults into view. Row 2 is the item
task-215 lists as still open — the description actually changes now. Row 4 is
the defect that made rain do nothing at all.
