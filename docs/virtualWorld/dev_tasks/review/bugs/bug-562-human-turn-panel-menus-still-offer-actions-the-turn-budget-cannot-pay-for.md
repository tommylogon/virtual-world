---
type: bug
status: review
area: bugs
priority: medium
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-352, bug-544]
---

# bug-562: Human turn panel menus still offer actions the turn budget cannot pay for

**Filed:** 2026-10-21
**Related:** task-352, bug-544

<!-- deps:start -->
**Related:** [[task-352-action-economy]], [[bug-544-disabling-turn-based-mode-does-not-reset-the-controlled-character-s-action-slots]]
<!-- deps:end -->

## What

The scene menus in the Human Turn Composer are not gated on the character's remaining turn budget. Exactly one row is gated: Dash, through `canInitiateDash()` in `static/js/agent/turn-scene-view.ts`. Every other budgeted row stays enabled even when the budget cannot pay for it - Examine and Go on a way menu, and the person and item verbs. The action is refused only later, at commit time, by `commitStep` in `static/js/agent/human-turn-composer.ts`, which flashes `no major action left this turn - say / emote / memory are still free`.

Measured on 2026-10-21 (labs scenario, character `Jane two`, browser at http://localhost:4444). The major slot was spent by a real action (`POST /api/action` with `examine Task 18 - door 3` and `enforce_slots: true`); the server then reported `turn_slots = {activity: 1, free: 3, major: 0, minor: 1}` and the panel's pips read `0 major - 1 minor - 3 free`:

- the menu for `Task 18 - ventilation shaft to Task 18 - Room 3` held Examine (enabled), Go southwest (enabled), Dash (disabled, `needs a major and a minor action`) and Open (enabled). `examine` and `go` are both major-tier verbs.
- selecting the enabled Go row filled the draft with `go southwest`; pressing Act flashed `no major action left this turn - say / emote / memory are still free` and left the draft in place.
- the other two way menus behaved the same way.

So the refusal exists, but only after the player has picked the action. The menu never shows that the budget is the reason, so the player selects an action the turn cannot pay for and only learns about it from a transient flash after committing.

Source enumeration: `rg` over `static/js/agent/turn-scene-view.ts` finds exactly one budget check, `canInitiateDash` (line 215, used at line 263). `buildWayMenu`, `buildPersonMenu` and `buildItemMenu` contain none. The live scene held no other characters, so the person and item menus were read in source only, not exercised in the browser.

## Why

The budget is the panel's central promise: the pips tell the player what is left, and the engine enforces it (`routes/action_handlers.py::_slot_gate` refuses with `You have no major action left this turn.`). A menu that offers a Go the character cannot pay for sends the player into a dead end: they pick the action, commit it, and only then learn that the turn cannot pay for it. Dash already shows the intended pattern - a disabled row with a reason beside it - so the fix extends an existing convention rather than inventing a mechanism.

The engine gate is not the hole here. It refuses correctly and the panel's commit-time check refuses correctly. The hole is the affordance: the selection surface, which is the thing the player actually chooses from, does not know about the budget.

## How

Gate every budgeted scene-menu row on the remaining slots, using the shared tier mirror `static/js/agent/action-tiers.ts` (generated from `engine/action_tiers.py`): resolve the tier with `ActionTiers.tierOf(verb)` and ask `ActionTiers.canPay(slots, tier)`. When the budget is published and cannot pay, render the row disabled with a reason (for example `no major action left`), exactly as the Dash row does today. `commitStep`'s refusal stays as the enforcement; the menu gate is the affordance in front of it.

Three details the implementation must preserve:

1. An unpublished budget (`turn_slots` is `{}`) means no budget published and must disable nothing (bug-544). The existing `turnSlots()` helper in the composer already makes that distinction; the menu gate must use the same reading.
2. The tier must resolve the way the engine gate resolves it. `engine/action_tiers.py::apply_action_gate` calls `tier_of(verb)` with no item node, so a per-item `action_costs` override does not apply at the gate. The panel must not silently apply an override the engine ignores, or the panel and the gate will disagree about what a verb costs.
3. A higher slot pays for a lower action (`canPay` walks free, minor, major upward), so a spent minor must not disable a free row, and a spent free slot must not disable a minor row.

The typed `do` row is the other half of the same gap: a typed verb that cannot be paid is refused only when Act is pressed. The hint area under the row (`#htc-do-hint`) can say the same thing while the player types.

## Browser UI and intended live verification

Intended UI home: the Human Turn Composer panel - the budget pips in the composer header and the scene chip rows ('Ways out', 'People here', 'Things you can see'); click a chip to open its context menu

Current availability: Present and driven live on 2026-10-21 (labs scenario, character 'Jane two', browser at http://localhost:4444). The panel, the pips and the context menus all work. The defect is present: with the major slot spent, the way menus still offer Examine and Go as enabled rows and only Dash is disabled.

Live steps when available:
1. Open the Human Turn Composer for a character and spend the major slot with a real action (for example examine), then watch the major pip turn spent and read the label `0 major - 1 minor - 3 free`.
2. Click a way chip and read every row of its context menu: every row whose verb the budget cannot pay for must be disabled and must carry a reason.
3. Click an enabled row for a major-tier verb (Examine or Go) and press Act: the commit must still be refused with `no major action left this turn`, because the engine gate remains the enforcement.
4. Read `GET /api/state` for the character's `turn_slots` and compare it with the pips before judging any row, so the panel is compared against the server's own budget.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Spend the major slot with a real action and confirm the panel and the server agree on the budget.
   - expected: the pips read `0 major - 1 minor - 3 free` and `/api/state` reports `turn_slots.major = 0`.
   - observed: both agreed - pips `0 major - 1 minor - 3 free`, server `turn_slots = {activity: 1, free: 3, major: 0, minor: 1}`.
2. Open each scene chip menu and record which rows are enabled.
   - expected: no row for a verb the budget cannot pay for is enabled.
   - observed: Examine (major) and Go (major) were enabled on all three way menus; only Dash was disabled, with `needs a major and a minor action`. The person and item menus could not be exercised (no other characters were present in the scene) and carry no budget check in source.
3. Select the enabled Go row and press Act.
   - expected: the commit is refused with `no major action left this turn` and the draft survives.
   - observed: exactly that - the flash read `no major action left this turn - say / emote / memory are still free` and the draft still read `go southwest`. The refusal exists; the defect is the selection affordance.
4. Regression test: a client-side test that builds the way menu with slots `{major: 0, minor: 1, free: 3}` and asserts that Go and Examine are disabled with a reason while Open (free) stays enabled, plus a case with an unpublished budget (`{}`) where nothing is disabled (bug-544).
   - expected: the test passes.

## Acceptance

- [x] Every budgeted scene-menu row is gated on the remaining turn slots, using the tier table the engine gate uses.
- [x] A row the budget cannot pay for renders disabled with a reason, the way the Dash row already does.
- [x] A row the budget can pay for stays enabled, and a free verb is never disabled by the budget.
- [x] An unpublished budget (turn_slots is an empty object) disables nothing.
- [x] The panel and the engine gate resolve a verb's tier the same way, so the menu never blocks a verb the gate would allow.
- [x] The commit-time refusal in commitStep stays as the enforcement and its flash text is unchanged.
- [x] A targeted regression test covers the spent-major case and the unpublished-budget case.

## Files

- `static/js/agent/turn-scene-view.ts`
- `static/js/agent/turn-scene-view.js`
- `static/js/agent/human-turn-composer.ts`
- `static/js/agent/action-tiers.ts`
- `engine/action_tiers.py`
- `routes/action_handlers.py`
