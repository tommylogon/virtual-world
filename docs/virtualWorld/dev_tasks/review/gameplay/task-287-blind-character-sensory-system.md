---
id: 287
title: Blind Character Sensory System (blindness = pitch-black, not "pretend")
status: review
priority: high
created: 2026-08-17
tags: [gameplay, conditions, blind, prompt, movement, sensory]
---

# Blind Character Sensory System

## Summary

A character under the `blind` condition is treated as **pitch black regardless of light**, and their
observation is **gated at the source** — the visual data is not handed to the LLM at all, instead of
being shipped wholesale and asking the model to "pretend you can't see" (the paralysis pitfall). Combines
a sensory-aware prompt rewrite, a blind-aware `fumble`, a `<sensory_aid>` cane, stumble-prone blind
movement, a `listen` verb, and a cooperative `lead` (guide) mechanic.

## Design decisions (locked 2026-08-17, user's call)

1. **Blind = pitch-black sensory mode.** `room-context.js` branches on `player.conditions.blind`: strips
   visual description, emits smell/noise/temp + people by audio/scent, and filters `WHAT HAPPENED` to
   speech events only (hear what people *say*, not see what they *do*).
2. **Item knowledge.** A blind character remembers what they saw before going blind, and anything they
   locate while blind stays known — `take`/`drop`/`use`/`examine` work on located items ("found it once →
   can find it again"). Room context lists only *known/discovered* items.
3. **Movement allowed, but risky.** Blind `go` has a fail chance → **stumble → `prone`** (DC 12,
   Perception + cane). Blind `climb`/`jump` get a steeper DC offset by the cane. `dash` deferred to the
   future disadvantage system.
4. **Fumble is already skill-based** (`min(2d20) + Perception` vs DC 12, `engine/narration.py`).
   A `<sensory_aid>` item (the cane) adds its `sensory_bonus` to the roll → higher success finding ways/items.
5. **`listen` verb** — focused audio scan (ambient noise + recent heard speech/sounds, incl. adjacent).
   Primary sense for blind; available to everyone.
6. **`lead` = cooperative grab** — target consents, no resist roll, positioned *beside* the guide, and
   dragged by the guide's movement. `stand` recovers from the stumble-prone.

## Files Changed

- `static/js/agent/prompt-builder/room-context.js` — `isBlind` branch (framing, sensed exits, known items,
  audio/scent people, speech-only witnessed).
- `engine/narration.py` — `fumble_around` bypasses light/dark-vision early-outs when blind; adds
  `_sensory_aid_bonus()` (carried/equipped `sensory_aid` items); new `listen()` audio scan.
- `data/library/items/guiding_cane.json` — new `<sensory_aid>` item with `sensory_bonus: 3`.
- `engine/movement.py` — blind `go` stumble→prone (unless cane/led); blind climb/jump DC penalty.
- `routes/action.py` — `listen` and `lead` commands; `escape`/`struggle` added to `_ACTION_BLOCK_ALLOWED`
  (fixes `grappled`'s `blocks_actions` blocking escape via the condition action-gate).
- `engine/grapple.py` — new `lead()` cooperative grab (no resist).
- `virtual_world_engine.py` — `listen()` facade.
- `static/js/agent/action-normalizer.js` — `stand`, `listen`, `lead` verbs + normalization.
- `static/js/agent/prompt-builder/system-prompt.js` — `listen`/`fumble`/`stand`/`lead` action rows + verb list.
  (Inspector condition-editor tooling — `/api/conditions`, full-payload `add_condition`, `api.js`,
  `agent-view.js` modal — is split out into **task-288**.)

## Testing

- [x] `node --check` on all edited JS; `py_compile` on all edited Python — clean.
- [x] Full suite: 955 passed, 1 skipped, 71 deselected; same 4 pre-existing failures
  (`test_npc_behaviors::test_rat_template_behaviors_parse`, `test_trigger_system` spawn/give-item) —
  unrelated and fail with the changes stashed too.
- [x] Live smoke (server :4444): blind `fumble` returns a fumble result (no "you can see fine").
- [x] Live smoke: `listen` returns an audio scan.
- [x] Live smoke: `lead john four` (by Bob) grapples+beside and `release` clears it.
- [ ] Browser E2E: blind character's room context renders as the sensory block (Ctrl+R).
  (Condition-editor smoke — `/api/conditions` catalog + full-payload add/remove — lives in **task-288**.)

## Status

**In Review — implemented 2026-08-17, static checks + live API smoke pass**; pending a browser pass of the
blind prompt and a live blind-run in a scenario with exits/people to confirm the stumble/lead feel right.

## Remaining / deferred

- `dash` blind penalty → real advantage/disadvantage dice mechanic, deferred (no dedicated task yet;
  see `task-trait-condition-system-v2`).
- Cane bonus on the `search` command (currently only `fumble`) — easy follow-up.
- Task docs + `my-thoughts-about-virtual-world.md` wrap-up if this becomes a keeper.
