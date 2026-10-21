---
type: bug
status: review
area: prompting
priority: high
wiki: "[[AI & Narration/Agent Engine]]"
---

# bug-523: Plan grounding facts use unmasked real names, leaking strangers and rejecting targets the room showed

**Filed:** 2026-10-07
**Related:** task-700, task-447, task-610, task-448

## What

Planning must be able to target what the prompt showed. The grounding facts currently use players_in_area[].name (the real name) while the room display masks unmet strangers via PromptBuilder.anonymousName, so a plan step 'approach the man' is rejected and the rejection prints the character's real name. Invariant: the grounder's facts must be the exact handles the prompt showed, and a real name must never appear for a character the player has not met.

## Measured 2026-10-07, from a live kraktooth_goblin_camp turn (turns 11-12)

Belne is in Side Tunnels with two characters he has never met. His room context shows
them masked:

```
People here:
  - the woman (frightened) beside the the man - A vague shape in the gloom - .
  - the man (awake) at the tunnel to mines - A vague shape in the gloom - .
```

His plan step `approach the man` is then rejected, with the reason:

```
nothing to walk up to called "the man" - here: Rikka, Thrazz; paths: deep passage, ...
```

Two defects in one message: a target he was **shown** is rejected, and the rejection
**hands him the real names** (Rikka, Thrazz) of characters the prompt says he has not met
(*"If someone is shown by appearance rather than a real name, you haven't met them"*).

## Measured 2026-10-19, from live Croak-Mother session

Croak-Mother in goblin camp attempts to eat food and feed a captive stranger:

1. `Croak-Mother plan step ungrounded: "eat woodpigeon_meat" - unknown act "eat" - use one of: go, dash, approach, crawl, climb, jump, fumble, take, drop, use, use_on, examine, search, look, listen, read, open, close, put, craft, make, combine, split, wear, remove, stow, give, steal, grab, lead, attack, escape, struggle, speak, perform, wait, stand, rest, relieve`
2. `Croak-Mother plan step ungrounded: "give woodpigeon_meat" - no one called "the woman (awake) - Human captive." here - people: Belne, Leslie, Mikka`

## Additional False-Negative Vectors in Plan Grounding

An audit of `static/js/agent/plan-grounding.ts` versus `room-context.ts` and engine action tiers reveals 6 systematic causes of false rejections:

1. **Missing core verbs (`eat`, `drink`, `sleep`, `meditate`, `bathe`):**
   `ACTS` has 38 verbs but omits `eat` and `drink` despite `Maslow` instructions in `plan-manager.ts:146` explicitly telling starving/thirsty agents to "eat your food, drink your water". It also rejects `sleep`, `meditate`, `bathe` (all valid activity-tier verbs in `engine/action_tiers.py`).
2. **Masked strangers vs unmasked fact pool (`bug-523` core):**
   `room-context.ts` renders strangers via `PromptBuilder.anonymousName()` ("the woman"), while `collectFacts()` collects raw unmasked `state.players_in_area[].name` (`Belne, Leslie, Mikka`). `matchFact()` finds 0 overlapping words between stranger description words and database names.
3. **Contained items and equipped gear:**
   `collectFacts()` inspects `worldState.getItemsInArea(areaName)` and top-level inventory names. Contained items (`getContainedItems(id)` - e.g., an item inside an open chest, bag, or carcass) are rendered in the prompt's item tree but omitted from `areaItems`, causing steps like `take dagger` from an open crate to be rejected as scenery.
4. **Door/way handles vs exit directions:**
   `room-context.ts` presents ways using authored handles from `PromptBuilder.wayHandle()` (e.g. `[iron grate]`, `[tunnel to mines]`, `[heavy oak door]`). `collectFacts()` only collects raw area exit keys and `e.direction` (`north`, `east`, `in`, `out`), missing authored door handles unless they match the direction string.
5. **Worn vs Carried segregation in action verbs:**
   `groundStep` groups `stow`, `wear`, `remove` under `[...facts.carried, ...facts.areaItems]`. If `player.inventory` does not include equipped items (which are tracked separately in `player.equipment` / `player.worn`), attempting to `remove iron helmet` or `stow shield` will fail with "carrying: (nothing)".
6. **Alias / Nickname mismatch:**
   Characters nicknamed or referred to by alias (`player.aliases`) are shown in the prompt as `Name [aka Viper]`, but `collectFacts` only tracks the canonical name, rejecting `speak to Viper` or `give food to Viper`.

## Root cause

Three layers disagree about how to name a stranger:

- **The prompt masks.** `room-context.ts` renders each person via
  `PromptBuilder.anonymousName(charName, person.name, desc)` - "the woman".
- **The matcher accepts the mask.** `engine/matching.py:683` - *"otherwise 'approach the
  woman' fails against a stranger"* - resolves the appearance label via
  `unknown_display_name()`. So `name the woman as …` and `approach the woman` resolve
  server-side.
- **The grounder does not.** `PlanGrounding.collectFacts`
  (`static/js/agent/plan-grounding.ts:109-111`) builds `people` from
  `state.players_in_area[].name` - the **real name** - so it compares against
  `Rikka, Thrazz` and rejects the masked handle the room actually showed, printing the
  real name in the reason.

## Why not route the grounder through the backend matcher

`engine/matching.py` is **backend**; `plan-grounding.ts` is **frontend**, run
synchronously per plan step during generation. Routing each step through the engine means
a round-trip per step and re-couples the client to engine internals. The minimal fix is
**not** to add a matcher call - it is to make the grounder's facts the **same handles the
prompt showed**. That is a frontend-only change with no round-trip, and it also removes
the leak (no real name is left in the facts or the rejection text). Note a matcher call
would **not** fix the leak on its own: a failed step still prints the fact list.

Fuzzy/alias/partial resolution (typos, "Vi" for Violet) is a separate, narrower concern:
the grounder should either match loosely (word-overlap, as its fact check already does) or
stop hard-rejecting a target it cannot resolve and let the backend be authoritative at act
time - which it already is.

## Acceptance (real criteria)

- **Invariant:** `collectFacts` produces the **exact handles the prompt shows** - masked
  (`anonymousName`) for a character the acting player has not met, real name once met.
- A plan step targeting a masked stranger the room showed (`approach the man`) **grounds**.
- A real name never appears in the facts or a rejection reason for an unmet character.
- **Test that runs the real `collectFacts`** against a fixture with an unmet stranger and
  asserts the masked handle is what grounds and that no real name leaks - the current
  `tools/unit/test_plan_grounding.js` hand-crafts `people: ['the woman', …]`, so it passes
  green while production diverges. The test must exercise `collectFacts`, not a
  hand-made list.

## Related, and a small adjacent artifact

`task-447` (nicknames/aliases) depends on this: a character can only nickname a target it
can address, and the only handle it has for a stranger is the one the room showed.

Adjacent cosmetic defect, same code path: with an empty person `description`, the dim-light
render (`room-context.ts:619`) yields *"A vague shape in the gloom - ."* - a dangling empty
clause. Fold the fix in if it is cheap, or file separately.

## Why

Plan grounding was created (task-700) to reject hallucinations like "use hanging meat" when hanging meat was merely prose flavor. But when the grounder's fact pool and verb set diverge from what `room-context.ts` presents to the LLM, the validator becomes a source of false rejections:
1. It rejects actions the prompt explicitly demanded ("eat your food" when starving).
2. It rejects entities the prompt presented ("the woman") and leaks database secrets in the error message.
3. It rejects valid paths and contained objects because facts were gathered too shallowly.

## How

1. **Expand `ACTS` in `plan-grounding.ts`**:
   - Add `eat`, `drink` (major tier).
   - Add `sleep`, `meditate`, `bathe` (activity tier).
   - Wire `eat` and `drink` validation in `groundStep`: like `use`, verify item is in carried or areaItems.
2. **Align Stranger Handles in `collectFacts`**:
   - In `collectFacts()`, iterate `players_in_area`. For each person, run `PromptBuilder.anonymousName(charName, p.name, desc)` or retrieve the anonymous display handle.
   - Include both the masked display handle and any nicknames/aliases (`person.aliases`) into the facts pool so the grounder checks what the prompt actually displayed.
   - Never print database names of unmet characters in rejection messages.
3. **Collect authored way handles & contained items**:
   - Query `viewerExitMap` / `PromptBuilder.wayHandle()` so door labels like "tunnel to mines", "heavy oak door" are in `exits`.
   - Include contained item names for visible open containers in `areaItems`.
4. **Mirror changes in JS bundle**:
   - Run `python tools/ts_convert.py build-one static/js/agent/plan-grounding.ts`.

## Steps to verify

1. Run unit test suite: `node tools/unit/run.cjs`
2. Run targeted test: verify `PlanGrounding.groundStep({ act: 'eat', item: 'woodpigeon_meat' }, facts, 'Goblin Camp')` returns `null` (grounds).
3. Test unmet stranger matching: verify `PlanGrounding.groundStep({ act: 'give', item: 'woodpigeon_meat', target: 'the woman' }, facts, 'Goblin Camp')` grounds when `the woman` is the masked handle in facts.
4. Verify rejection messages never contain the raw unmasked name of unmet NPCs.

## Acceptance

- [x] `eat` and `drink` are in `PlanGrounding.ACTS` and ground against carried or area items.
- [x] `collectFacts` uses masked anonymous handles (`the woman`, `the man`) for unmet characters matching `room-context.ts`.
- [x] Steps targeting masked handles ground without rejection.
- [x] Rejection reasons do not leak real names of unmet characters.
- [x] Unit tests in `tools/unit/test_plan_grounding.js` cover `eat`/`drink`, masked strangers, and way handles.

## Files

- `static/js/agent/plan-grounding.ts`
- `static/js/agent/plan-grounding.js`
- `tools/unit/test_plan_grounding.js`

## Browser UI and intended live verification

Intended UI home: load a scene with an unacquainted stranger → inspect the Human Turn scene/room context and the character's generated plan in the event stream or raw LLM view.

Current availability: the card reports that planning facts use real `players_in_area[].name` values while the prompt shows masked handles. The mismatch and real-name leak are reported; no fresh browser reproduction is recorded in this card.

Live steps when available:
1. In a scratch scene, put the controlled character beside a stranger it has not met. Inspect the visible room context and the exact handles shown to the character.
   - expected: the prompt context uses the same anonymous handle as the visible scene; the stranger's real name is absent.
2. Ask the character to approach the visible stranger using the handle from the scene.
   - expected: grounding accepts the visible target and executes the plan; it does not reject the target or reveal a hidden real name in the result.
3. Inspect raw LLM capture, grounding facts, event stream, and `/api/state` after the plan.
   - expected: the planner and grounder share the prompt-visible identifier, while authoritative graph resolution still targets the correct opaque node ID.
4. Repeat after the character has learned the stranger's name.
   - expected: the real name is available only after recognition/knowledge permits it; the masked-stranger path remains private.

This section is not a claim that planned UI exists or works today.
