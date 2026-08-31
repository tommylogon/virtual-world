---
type: bug
status: review
area: gameplay
---

# bug-34: "go to the <way>" silently crosses the doorway

**Filed**: 2026-08-30
**Status**: In Review â€” fixed 2026-08-30, engine + prompt tests green; agent
E2E playtest pending.

## Observed

Agents said `go to the door` / `go toward the hidden tunnel` intending to
REACH the doorway; `go` resolved the way and walked them through.

## Fix

- `engine/movement.py`: approach semantics â€” `go to <way>` / `go toward` /
  `approach X` walk UP TO the way and stop (positioned at it);
  crossing is explicit (`go <handle>`, `go <room>`, `go through <X>`, dash).
- New `approach` verb: HTTP handler, MCP tool, action normalizer, prompt
  examples, AV actions, scene view, type-ahead.
- Slug-tolerant way resolution ("hidden tunnel" â†’ hidden_tunnel name or id).
- Tests: `tests/test_movement.py` (approach suite); full suite 1274 passed.


