---
group: Triggers
---
# Trigger Effect: Create Item Inside Another on Use

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Idea

---

## Idea

Trigger effect to create a new item inside another item on use. Examples:
- A camera taking a photo of a target → spawns a photo item inside the camera.
- A voice recorder that records what has been said in the area.
- An EVP device that on use has a random chance to play static noise or a spooky voice.

## Notes

- The mechanics half exists: `spawn_item` with `into: container` already places a fresh copy inside a container item.
- The novel 30% is capture: recording recent area speech/events (recent `turn_events`) into the spawned item's `description` so a recorder contains what was actually said.
- EVP flavor = `random_chance` condition + a static/spooky message.

## Related

- `developer ideas.md` line 5
- `engine/effects.py` `handle_spawn_item` (fresh-copy semantics, task-294+), `engine/trigger_system.py` (`random_chance`, `speech_matches`, `sound_heard`)
