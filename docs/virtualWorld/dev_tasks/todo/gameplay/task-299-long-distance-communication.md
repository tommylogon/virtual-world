---
group: Gameplay
---
# Long-Distance Communication (Phones, Walkie-Talkies, Radios)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Design (2026-09-23) — approach agreed, not started

---

## Idea

Triggers/mechanics to allow long-distance communication — phones, walkie-talkies, radios or magic like message. some being audio only, some being with visible data

## Notes

- New channel system: speech routed through an item property instead of area adjacency. `speak`/`whisper`/`shout` currently broadcast to the area (+adjacent rooms through open doors).
- Suggested MVP: items with a `comms_channel` tag/property; `speak` while using/holding the item relays to everyone holding an item on the same channel, regardless of distance.
- alternative approach of item like phone having a subitem that is contacts like call James, so you should do "use phone - call james" that then would call that person, initating a activity of being on the phone, but we should sometimes be allowed to talk and do other actions, some items might now allow it.  how it handles on the othe rend too, in the phone example the target should on their turn get "your phone is calling" and as such the phone should have a subitem like answer phone" or something like that

## Design decisions (2026-09-23 discussion)

- **Composition over verbs.** A device (phone/radio) is a parent item whose capabilities are *child part items*, each with its own triggers/state/`uses`. No per-item named verbs — the verb set stays the fixed engine enum (see task-491).
- **No `power` property.** Charge/degradation is the generic `uses` (+ `on_depleted`); no device-type-specific fields on the base item (see task-493).
- **Non-portable parts.** A part omits `take` in `actions`, so it cannot be taken/dropped/put while staying reachable/usable (the gate already exists at `take_drop_actions.py:388-393`). No new edge type required.
- **A call is a directed channel, not area propagation.** Only the caller's directed utterance relays to the partner endpoint; the caller's room still hears them *physically* (muffled unless `speakerphone`). A `speakerphone` state is the explicit opt-in that captures room audio. Ringing already works via `sound_source` + `current_state: "ringing"`; the `on_speech` relay (`engine/speech.py:362-390`) needs extending to **carried** items.
- **An ongoing call** is an activity/condition that does **not** skip turns — talking and other actions coexist.
- **Open:** default speech isolation (muffled vs speakerphone), and whether individual parts are separately addressable (`use phone battery`).

## Related

- `task-491` — action-verb single source of truth
- `task-493` — item part/component model
- `task-494` — container examine reveal + chained action
- `task-352` — action economy (concurrency while on a call)
- `developer ideas.md` line 6
- `engine/sound.py`, `routes/action.py` speech verbs (`speak`/`shout`/`whisper`/`scream`)
