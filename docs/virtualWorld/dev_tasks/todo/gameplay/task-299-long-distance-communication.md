---
group: Gameplay
---
# Long-Distance Communication (Phones, Walkie-Talkies, Radios)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Idea

---

## Idea

Triggers/mechanics to allow long-distance communication — phones, walkie-talkies, radios.

## Notes

- New channel system: speech routed through an item property instead of area adjacency. `speak`/`whisper`/`shout` currently broadcast to the area (+adjacent rooms through open doors).
- Suggested MVP: items with a `comms_channel` tag/property; `speak` while using/holding the item relays to everyone holding an item on the same channel, regardless of distance.
- Thematically strong for the mansion/horror setting (radios, walkie-talkies, intercoms).
- Medium-large scope — a new speech routing path, not a tweak.

## Related

- `developer ideas.md` line 6
- `engine/sound.py`, `routes/action.py` speech verbs (`speak`/`shout`/`whisper`/`scream`)
