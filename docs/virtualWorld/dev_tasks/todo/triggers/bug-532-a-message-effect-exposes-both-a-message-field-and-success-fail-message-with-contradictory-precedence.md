---
type: bug
status: todo
area: triggers
priority: medium
---

# bug-532: A message effect exposes both a Message field and Success/Fail Message with contradictory precedence

**Filed:** 2026-10-09
**Related:** task-739 (NL trigger authoring), task-512 (expression pack images tab)

## Goal

The trigger editor shows a `message` effect with a **Message** field *and*, in the
same dialog, separate **Success Message** and **Fail Message** fields. They write
the same narration slot, and the engine resolves them with **contradictory
precedence**, so a value the author typed can be silently discarded.

Observed live: authoring an `on_examine` → Show Message trigger produced an effect
whose params carry `message`, while the dialog also offered `success_message` /
`fail_message`. The trigger worked, but the two fields compete.

Evidence of the conflict:

- **Runtime prefers `success_message` and overwrites `message`** —
  `engine/triggers/execution.py:570-572`:
  `if effect_params.get("success_message"): effect_params["message"] = effect_params["success_message"]`.
  A successful run therefore drops the authored `Message`.
- **Legacy migration prefers `message`** — `engine/triggers/effect_resolution.py:23-27`
  uses `success_message` only as a *fallback* when `message` is empty. Opposite order.
- **Validation accepts any of the three** — `engine/trigger_validator.py:560-566`
  treats `message` / `success_message` / `fail_message` as "has text", so it
  cannot catch the conflict.
- **Test runs repeat the runtime override** — `engine/triggers/testing.py:162-187`.
- **Readers pick `success_message` first too** — `static/js/graph/tooltips.ts:206`,
  `static/js/inspector/trigger-helpers.ts:176`.
- **The editor writes both** — `static/js/inspector/item-view.ts:747-748` seeds
  `success_message: ''` and `fail_message: ''` alongside the effect params.
- `fail_message` is only meaningful for effects that can fail (scry, spawn,
  ways, some spells) but the dialog shows it for every effect.

The result: two homes for one value, and which one wins depends on which code
path runs (live execution vs. legacy migration vs. test harness vs. tooltip).

## Acceptance

- [ ] One narration slot per message effect. Either drop `success_message` in
      favour of the effect's `message` (+ an explicit `fail_message`), or make
      `success_message` the single field and migrate.
- [ ] One precedence rule, applied identically in execution, testing, tooltip,
      trigger-helpers and legacy migration; recorded in a comment at the
      resolution site.
- [ ] The trigger editor shows a single, unambiguous field (or labels clearly
      which field wins).
- [ ] `fail_message` is only shown for effect types that can fail.
- [ ] A regression test asserts the mechanism: a trigger with both fields set
      yields the chosen value on success and on failure.
- [ ] Existing authored scenarios still render their intended message.
