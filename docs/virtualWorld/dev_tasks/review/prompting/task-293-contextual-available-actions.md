# task-293: Contextual "Available Actions" prompts

**Status** — In Review — implemented (contextual-actions.js wired into room-context.js); verified live render 2026-08-21. Moved from todo/ 2026-08-21.

## Summary

Replace the static 30-row ACTIONS table in the character system prompt with a compact
static core plus a per-turn `=== AVAILABLE ACTIONS ===` block built from each character's
current context (room, exits, items, people, vitals, conditions, light). Add per-item
action brackets to the "Items that catch your attention:" list and the "Carrying:" line so
the agent sees exactly what it can do right now instead of a wall of verbs.

## What was implemented

- New `static/js/agent/prompt-builder/contextual-actions.js`:
  - `computeItemActions(item, player, carry)` — the allowed verbs for an item, mirroring
    the backend `_get_available_actions` (engine/trigger_system.py) client-side from
    `properties.actions` (string-or-array), `tags`, `current_state`, and `triggers` edges.
    `examine` is shown **unless** the character has already examined/discovered the item
    (per design decision).
  - `formatActionBrackets(verbs)` — `[take, use]` bracket, `''` when empty.
  - `buildAvailableActionsBlock(state, charName, player, currentArea)` — the per-turn
    `=== AVAILABLE ACTIONS ===` text with concrete targets, gated by context.
  - `carriedItemNodes(charName)` — carried/equipped item nodes for the Carrying brackets.
- `static/js/agent/prompt-builder/helpers.js`: moved `wayHandle` out of `room-context.js`
  into a shared `PromptBuilder.wayHandle(exitData, doorNode, areaName)`.
- `static/js/agent/prompt-builder/room-context.js`:
  - Inserts `=== AVAILABLE ACTIONS ===` before the WITNESSED block (agent framing only).
  - Adds item action brackets to the attention list + dim/dark + blind known-item lists.
  - Adds brackets to the "Carrying:" line.
- `static/js/agent/prompt-builder/system-prompt.js`:
  - Deleted `ACTIONS_TABLE` (the ~700-token wall). Replaced with a compact `ACTIONS_CORE`
    that points at `=== AVAILABLE ACTIONS ===` and keeps the essential static rules.
  - Kept `GHOST_ACTIONS`, `ACTION_STRUCTURE` (verb-list line kept as a safety net),
    `SPEECH_VOLUME`, `JSON RULES`; refreshed `ITEMS_VS_FLAVOR` to match the real header
    and mention item brackets.
- `static/js/agent/prompt-builder/turn-prompts.js`: reaction prompt now points at
  `=== AVAILABLE ACTIONS ===`.
- `templates/index.html` + `static/js/agent/prompt-builder/index.js`: registered the new
  `contextual-actions.js` module.

## How verified

- `node --check` on all touched JS files.
- Browser smoke via the inspector / agent-lens reaction prompt (gates per room content:
  empty room → no take/attack; takeable item → `take — <name>`; person present →
  give/steal/attack/grab/lead; grappled → escape; dark → fumble; crawl/climb/jump way →
  matching verb; low energy → rest; high bladder → relieve).

## Notes

- Gating is **guidance, not enforcement** — the backend still resolves verbs leniently, so
  a missed gate only hides a verb from the prompt, never breaks resolution.
- The system prompt is cached per character (`agent-engine.js:26`) — a page reload rebuilds
  it so the trimmed prompt applies.
- `docs/design/*` are stale design snapshots; not in scope to sync.