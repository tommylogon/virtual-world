# Task: Move Output Clarity — Arrival Area Name

**Status**: Implemented (verified 2026-08-06) — destination area name is already included in move output via `arrival_suffix` in `engine/movement.py` `move_to_area()`: `target_display = target_area_node.properties.get("display_name") or target_area_node.name; arrival_suffix = f" — you're in {target_display}."`. Move output now reads e.g. "You head through the north door. — you're in the Kitchen." The task goal (name the destination) is met. Should be moved to `done/` once a Playwright assertion (see Files Modified) is added.

## Goal

Make move results name the destination so the agent doesn't have to guess where
it ended up. Currently `routes/action.py:96-108` builds the "You move" message
from the exit's `action_text` and the (often bare) area `description` line, but
**never includes the destination area's name** — the name is only in the first
sentence of the description, which is inconsistent.

Evidence from `event_log_2026-08-02T12-00-06.txt`:
- Kaelen: `"You move to ..."` then `"You have arrived at ..."` where the second
  line is the area description without a name prefix — the model has to infer the
  room name from prose (`The first thing that hits you...`).
- After a successful move the model's own narration said "she stepped into the
  kitchen" without a ground-truth name to confirm against, contributing to vague
  area references.

## Changes

### 1. `routes/action.py` — move handler (lines 96-108)
- Add the destination area name explicitly. Prefer:
  - `to_area.get_property("display_name")` if present, else `to_area.get_property("name")`.
- Render: `"You move {direction} — {destination name}. {description first sentence}"`.
  Keep `action_text`/`arrival` prefix handling so old format consumers (obsidian
  docs, tests) aren't broken — append the name rather than replace.

### 2. Verify the message reaches the agent prompt
- Confirm `move` messages flow into the player's `system_messages` / history that
  `agent-engine.js` observe reads (they do via the same message pipeline as other
  actions — just verify in the log that the name now shows up).

### 3. (Nice-to-have) `You have arrived at <name>`
- Keep the existing `"You have arrived at..."` line but prefix the name:
  `"You have arrived at the Kitchen."` — trivial but high value for the model's
  spatial grounding.

## Files Modified
- `routes/action.py`
- `tools/test_all.cjs` (assert destination name present in move output)
- `docs/virtualWorld/` (if move format is documented anywhere)
