---
type: task
status: done
area: characters
priority: high
---

# task-469: Fear tags: per-character fears drive frightened/interrupts

**Filed:** 2026-09-23
**Related:** task-464, task-466, task-214, task-213, task-326

## Goal

Replace the global hostile notion with per-character fear tags. Characters carry fear_tags (mirroring interest_tags); meeting a co-located character/item or an area whose tags intersect them applies the existing source-gated frightened condition and raises a fear interrupt so a timeskip pauses. Fears are authorable via trigger effects (add_fear_tag/add_interest_tag) and learnable via deliberate agent verbs (fear <target> / interest <target>). Guards vs farmers vs goblins differ purely by their fear_tags, so no group panics at itself.

## Acceptance

- TODO

## Progress 2026-09-23 — core landed (review)

- [x] `Player.fear_tags` (mirrors `interest_tags`): persisted in `to_dict`, save/load and the serialization dict.
- [x] `engine/fear.py`: `fear_sources(gs, player)` finds co-located characters (by `traits` + character-node tags), items the area holds, and the area's own tags whose tags intersect `fear_tags`; `apply_frightening` applies the source-gated `frightened` condition (source name + kind, 30 game minutes → ticks).
- [x] Timeskip: meeting a feared thing applies `frightened` and **pauses** with a `fear` interrupt (players are not immune).
- [x] Trigger effects: `add_fear_tag` / `remove_fear_tag` / `add_interest_tag` / `remove_interest_tag` (`engine/effect_handlers/tags.py`, registered in `engine/effects.py`), params `{tag, target: self|target|<name>, message?}`.
- [x] Deliberate verbs: `fear <target>` / `interest <target>` resolve the target's tags (character traits / node tags) and add them (`world.fear_target` / `world.interest_target`), wired into `handle_take_action`; the normalizer accepts/emits both and the composer autocompletes them.
- [x] Guards/farmers/goblins differ only by their lists: a goblin with `fear_tags:["guard"]` is not afraid of another goblin.

## Remaining

- [ ] Wire fear into normal-play NPC behaviour (flee/avoid, task-214/354) and the attended tier's prompt, not just the timeskip.
- [ ] Awareness channels (sound) as a fear source (task-418); currently co-location only.
- [ ] Condition `frightened` tuning once real fears exist (its attack/defense mods and `ends_on`).

## Verification

`python -m pytest tests/test_fear.py -q` → 15 passed. Targeted regression (serialization, save/load, effects, triggers, identity, timeskip) → 274 passed. `tools/unit` → 130 passed. lint / typecheck / module-index clean.

## Review 2026-09-23 - core closed

Verified: `tests/test_fear.py` plus the soak-chain promotion case (`frightened` applied, order promoted, `soak_end` event). Remaining bullets: normal-play NPC fear behaviour (task-214/354), awareness channels as a fear source (task-418), and `frightened` tuning filed as **task-484**. Closing.