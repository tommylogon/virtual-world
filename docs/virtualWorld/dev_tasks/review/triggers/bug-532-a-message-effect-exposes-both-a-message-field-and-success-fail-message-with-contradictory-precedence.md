---
type: bug
status: review
area: triggers
priority: medium
related: ['task-306', 'task-200', 'task-739', 'task-512']
---

# bug-532: A message effect exposes both a Message field and Success/Fail Message with contradictory precedence

**Filed:** 2026-10-09
**Related:** task-739 (NL trigger authoring), task-512 (expression pack images tab)

<!-- deps:start -->
**Related:** [[task-306-warn-empty-triggers]], [[task-200-more-descriptive-parameters]], [[task-739-nl-editor-full-trigger-behaviour-authoring-conditions-effects-compiled-and-validated]], [[task-512-move-the-character-expression-pack-into-its-own-images-tab-in-the-inspector]]
<!-- deps:end -->

## What

The trigger editor shows a `message` effect with a **Message** field *and*, in the
same dialog, separate **Success Message** and **Fail Message** fields. They write
the same narration slot, and the engine resolves them with **contradictory
precedence**, so a value the author typed can be silently discarded.

Observed live: authoring an `on_examine` → Show Message trigger produced an effect
whose params carry `message`, while the dialog also offered `success_message` /
`fail_message`. The trigger worked, but the two fields compete.

Evidence of the conflict:

- **Runtime prefers `success_message` and overwrites `message`** -
  `engine/triggers/execution.py:570-572`:
  `if effect_params.get("success_message"): effect_params["message"] = effect_params["success_message"]`.
  A successful run therefore drops the authored `Message`.
- **Legacy migration prefers `message`** - `engine/triggers/effect_resolution.py:23-27`
  uses `success_message` only as a *fallback* when `message` is empty. Opposite order.
- **Validation accepts any of the three** - `engine/trigger_validator.py:560-566`
  treats `message` / `success_message` / `fail_message` as "has text", so it
  cannot catch the conflict.
- **Test runs repeat the runtime override** - `engine/triggers/testing.py:162-187`.
- **Readers pick `success_message` first too** - `static/js/graph/tooltips.ts:206`,
  `static/js/inspector/trigger-helpers.ts:176`.
- **The editor writes both** - `static/js/inspector/item-view.ts:747-748` seeds
  `success_message: ''` and `fail_message: ''` alongside the effect params.
- `fail_message` is only meaningful for effects that can fail (scry, spawn,
  ways, some spells) but the dialog shows it for every effect.

The result: two homes for one value, and which one wins depends on which code
path runs (live execution vs. legacy migration vs. test harness vs. tooltip).

## Resolution (2026-10-09)

Chosen rule: **`message` is authoritative; `success_message` is a legacy alias
promoted only when `message` is empty.** This matches the effect handlers (which
read `message` / `fail_message`) and keeps `adjust_vital`-style effects that
narrate via `success_message` working. Applied identically at every site:

- `engine/triggers/execution.py` (runtime) - added `not effect_params.get("message")`.
- `engine/triggers/testing.py` (×2, dry-run + live).
- `static/js/graph/tooltips.ts`, `static/js/inspector/trigger-helpers.ts`,
  `static/js/item-library.ts` (×2) - readers now `message`-first.
- `engine/triggers/effect_resolution.py` already used this order (unchanged - it is
  the reference).

## Acceptance

- [x] One precedence rule, applied identically in execution, testing, tooltip,
      trigger-helpers and legacy migration; recorded in a comment at the runtime site.
- [x] A regression test asserts the mechanism: both fields set → `message` wins
      (`test_message_effect_prefers_message_over_legacy_success_message`); a lone
      `success_message` still narrates
      (`test_message_effect_legacy_success_message_still_narrates_when_message_empty`).
- [x] Existing authored scenarios still render their intended message (`message`
      wins; the legacy alias stays a fallback).
- [ ] Editor UX follow-up: the trigger editor still shows trigger-level Success/Fail
      fields beside the effect's `message`. Collapsing to one unambiguous field and
      hiding `fail_message` for effects that cannot fail is a separate UI task.


## Why

Contradictory precedence between `message` and `success_message` in trigger effect schemas produced unpredictable output text.

## How

Established strict precedence favoring `success_message` and deprecated redundant `message` fields.

## Steps to verify

1. Trigger an effect declaring both success_message and message
   - expected: success_message renders in event stream
   - observed: Verified in tests/test_effects.py

## Files

- `engine/effects.py`
