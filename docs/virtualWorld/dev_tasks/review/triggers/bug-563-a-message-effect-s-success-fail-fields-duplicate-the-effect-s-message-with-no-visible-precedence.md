---
type: bug
status: review
area: triggers
priority: medium
wiki: "[[Triggers & Effects]]"
related: [bug-532]
---

# bug-563: A message effect's Success/Fail fields duplicate the effect's Message with no visible precedence

**Filed:** 2026-10-21
**Related:** bug-532

<!-- deps:start -->
**Related:** [[bug-532-a-message-effect-exposes-both-a-message-field-and-success-fail-message-with-contradictory-precedence]]
<!-- deps:end -->

## What

For one `message` effect the trigger editor renders a trigger-level Success Message and Fail Message beside the effect's own Message. Since bug-532 made `message` authoritative, a value typed into the trigger-level Success Message is silently discarded whenever the effect also carries a message, and Fail Message is offered for every effect although only effects that can fail read it. Collapse the editor to one narration field per effect, keep reading the legacy `success_message` alias, and only offer a fail branch for effect types whose handler actually reads `fail_message`.

## Why

Two editable fields write one narration slot, so an author can type prose that never appears. bug-532 fixed the precedence (`message` wins, `success_message` is a fallback) at execution, testing, tooltips and trigger-helpers, but the editor is the one surface that still seeds both (`static/js/inspector/item-view.ts:761`, `trigger-helpers.ts:352`, `way-view-triggers.ts:45`). Precedence is settled; the confusing form is not.

## How

1. Keep the effect's `message` as the only editable narration slot and stop seeding `success_message` / `fail_message` in the trigger editor call sites. 2. Enumerate the effect types whose handler reads `fail_message` from the handler table in `engine/effect_handlers/` (do not infer the list from the current dropdown) and render a fail branch only for those. 3. Leave `engine/triggers/execution.py` precedence alone: the reader must keep promoting a legacy `success_message` when `message` is empty, so existing authored triggers keep narrating. 4. Round-trip check: save a message effect, reload the node, and confirm the text lands in `params.message`.

## Browser UI and intended live verification

Intended UI home: Inspector -> an item or way node -> Triggers -> edit a Show Message effect

Current availability: Present today: the trigger dialog renders both the effect's Message and the trigger-level Success/Fail fields, and the editor seeds `success_message`/`fail_message`.

Live steps when available:
1. Open the trigger editor on a node with an on_examine Show Message trigger and read every narration field in the dialog.
2. expected: one editable narration field per effect; no trigger-level Success Message competing with it.
3. Type prose into that field, save, reopen the trigger.
4. expected: the text is in `params.message` and survives the reopen.
5. Author a legacy trigger carrying only `success_message`, run it, and read the event stream.
6. expected: it still narrates, because the reader keeps the alias as a fallback.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: One editable narration field per effect; no trigger-level Success Message competing with it. Saving round-trips into params.message.
   - observed: Trigger editor renders .eff-msg-text for message effect; te-success-msg is removed from the form; fail branch is conditionally visible for condition groups and fail-reading effects.
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Trigger dialog rendered via TriggerEditor.show with single message effect row.
   - observed: Verified via DOM/form unit tests in tools/unit/test_trigger_editor_message.js and typecheck.
3. Run the targeted regression test for the mechanism.
   - expected: All targeted trigger and unit tests pass cleanly.
   - observed: 880 passed in node tools/unit/run.cjs (with test_trigger_editor_message.js passing both tests); 223 passed in tests/test_trigger_system.py, tests/test_trigger_validator.py, tests/test_trigger_authoring.py.

## Acceptance

- [x] The trigger editor shows exactly one narration field for a message effect, and saving it round-trips into `params.message`.
- [x] The editor no longer seeds `success_message` or `fail_message` for a message effect.
- [x] A legacy trigger whose `success_message` is authored still narrates when `message` is empty (reader unchanged, covered by the existing bug-532 tests).
- [x] A fail branch is offered only for effect types whose handler reads `fail_message`, enumerated from `engine/effect_handlers/`.
- [x] A unit test asserts the editor writes `message` and does not write `success_message`.

## Files

- `static/js/inspector/item-view.ts`
- `static/js/inspector/trigger-helpers.ts`
- `static/js/inspector/way-view-triggers.ts`
- `static/js/shared/trigger-editor.ts`
- `static/js/shared/trigger-graph.ts`
- `engine/effect_handlers/ (source of the fail_message effect list)`
- `tools/unit/test_trigger_editor_message.js`
