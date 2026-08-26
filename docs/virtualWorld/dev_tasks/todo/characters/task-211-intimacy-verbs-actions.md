---
group: Pleasure System
---

# Intimacy Verbs, Interact/Attack Distinction & Body-Part Targeting

**Filed**: 2026-08-11
**Priority**: Medium
**Status**: Todo

---

## Problem

The command parser (`routes/action.py`) has no intimacy verbs and no `where` body-part targeting. Actions are either item/movement/etc. or fall through to `process_emote` (flavor-only, no mechanical effect).

## Design

- **Verb collision check (verified):** `grab` → grapple (`routes/action.py:689`), `grope`/`grope around`/`feel around` → `fumble_around()` blind-nav (`routes/action.py:33` dispatch, handler at `:589`). New intimacy verbs (kiss, lick, suck, caress, pinch, tickle, etc.) must not collide — pick fresh tokens or extend the parser carefully.
- Add `where`/`intensity` to the action schema (frontend → backend): action struct becomes `{action, type, target, where, intensity, emote}`. `type` ∈ `interact` (no damage) vs `attack` (existing `combat.py` path). Default `type: interact` so plain `kiss lydia` is non-combat.
- **Agent path**: LLM agents emit actions through `_normalizeStructuredAction()` (`static/js/agent-engine.js:752`) → `/api/action`. The normalizer + `prompt-builder.js` must learn the new verbs/fields or agents can't use them.
- Implement `_resolve_body_part()` in `engine/pleasure_actions.py` — checks accessibility via paperdoll layered stacks (outer layers of the relevant slot, `player.equipped`).
- When `mature_content = false`, intimacy verbs reject with a flavor message instead of silently emoting.

## Files

- `routes/action.py` — new verb branches (existing dispatch chain, lines 186-727)
- `static/js/agent-engine.js` — `_normalizeStructuredAction()` (line 752)
- `static/js/agent/prompt-builder.js` — action examples + allowed verbs
- `engine/pleasure_actions.py` — NEW: `_resolve_body_part()`, DC calculation, accessibility

## Testing

- [ ] `kiss lydia` (no `where`) → default to lips/likely body part, interact type
- [ ] `kiss lydia on neck` → resolved body part, not swallowed by emote fallback
- [ ] `grab`/`grope` still do their existing behaviors (no regression)
- [ ] `attack` continues through combat; `interact` never damages
- [ ] Mature toggle off → intimacy verbs blocked

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §3, Phase 4
- `task-4 grapple` (`grab`), `task-160 structured actions` (schema)

## Gap found 2026-08-23 (human-panel mockup work)

**Removing clothing from ANOTHER character doesn't exist today:**
`EquipmentSystem.unequip_item()` is hardwired to the active player
(engine/equipment.py:232-240), `strip/undress` routes are self-only.
Steal DOES scan equipped edges, so snatching an equipped accessory works
today. This task's `_resolve_body_part()` outer-layer accessibility check
is the natural home: extend it with forced-removal verbs (pull off / strip
target) gated by grapple/restraint state + mature toggle. The human-turn
panel mockup (task-333) already renders this as a disabled menu entry with
reason "self-only today" and will consume the new verbs automatically once
they exist (menus are data-driven from actions+state).
