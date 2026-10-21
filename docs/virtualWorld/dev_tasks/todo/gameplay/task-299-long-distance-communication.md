---
area: gameplay
type: task
status: todo
priority: medium
wiki: "[[Gameplay/The Commons]]"
---

# Long-Distance Communication (Phones, Walkie-Talkies, Radios)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Design (2026-09-23) - approach agreed, not started

---

## What

Triggers and mechanics to allow long-distance communication - phones,
walkie-talkies, radios, or magic messages; some audio only, some carrying
visible data. Speech is routed through an item property instead of area
adjacency: `speak`/`whisper`/`shout` currently broadcast to the area (plus
adjacent rooms through open doors), and a device channel would reach people by
channel membership rather than proximity.

The suggested MVP: items with a `comms_channel` tag or property; `speak` while
using or holding the item relays to everyone holding an item on the same
channel, regardless of distance.

The alternative approach is a device parent item with contact subitems, so you
"use the phone to call James rather than speaking to a channel. That would
initiate an activity of being on the phone; talking should sometimes be allowed
alongside other actions, and some items should permit that. The far end needs
handling too: in the phone example the target should, on their turn, get "your
phone is calling", and the phone should have an "answer phone" subitem or
similar.

## Notes

- New channel system: speech routed through an item property instead of area adjacency. `speak`/`whisper`/`shout` currently broadcast to the area (+adjacent rooms through open doors).
- Suggested MVP: items with a `comms_channel` tag/property; `speak` while using/holding the item relays to everyone holding an item on the same channel, regardless of distance.
- alternative approach of item like phone having a subitem that is contacts like call James, so you should do "use phone - call james" that then would call that person, initating a activity of being on the phone, but we should sometimes be allowed to talk and do other actions, some items might now allow it.  how it handles on the othe rend too, in the phone example the target should on their turn get "your phone is calling" and as such the phone should have a subitem like answer phone" or something like that

## Design decisions (2026-09-23 discussion)

- **Composition over verbs.** A device (phone/radio) is a parent item whose capabilities are *child part items*, each with its own triggers/state/`uses`. No per-item named verbs - the verb set stays the fixed engine enum (see task-491).
- **No `power` property.** Charge/degradation is the generic `uses` (+ `on_depleted`); no device-type-specific fields on the base item (see task-493).
- **Non-portable parts.** A part omits `take` in `actions`, so it cannot be taken/dropped/put while staying reachable/usable (the gate already exists at `take_drop_actions.py:388-393`). No new edge type required.
- **A call is a directed channel, not area propagation.** Only the caller's directed utterance relays to the partner endpoint; the caller's room still hears them *physically* (muffled unless `speakerphone`). A `speakerphone` state is the explicit opt-in that captures room audio. Ringing already works via `sound_source` + `current_state: "ringing"`; the `on_speech` relay (`engine/speech.py:362-390`) needs extending to **carried** items.
- **An ongoing call** is an activity/condition that does **not** skip turns - talking and other actions coexist.
- **Open:** default speech isolation (muffled vs speakerphone), and whether individual parts are separately addressable (`use phone battery`).

## Related

- `task-491` - action-verb single source of truth
- `task-493` - item part/component model
- `task-494` - container examine reveal + chained action
- `task-352` - action economy (concurrency while on a call)
- `developer ideas.md` line 6
- `engine/sound.py`, `routes/action.py` speech verbs (`speak`/`shout`/`whisper`/`scream`)

## Why

Current speech (engine/speech.py, routes/action.py) broadcasts to the area and adjacent rooms through open doors only. The design (2026-09-23) establishes composition over verbs (device as parent with child part items, no per-item named verbs), use of generic `uses` for charge/degradation (no device-specific power field), non-portable parts, and a directed channel model where only the caller's directed utterance relays to the paired endpoint while the caller's room still hears them physically (muffled unless speakerphone). This enables phones/walkie-talkies/radios/magic messaging without expanding the verb enum and without duplicating power systems. Reconnaissance confirms no comms_channel relay for carried devices exists yet.

## How

Follow the agreed design, extend existing systems.

1. **Composition/parts**: model devices as parent items with child part items (using existing item part/component model, task-493). Parts omit `take` in `actions` to remain non-portable/usable. No new edge type required.
2. **Channel system**: add support for `comms_channel` on devices/parts (or equivalent property). When speaking while using/holding a device on a channel, relay directed utterance to endpoints on same channel regardless of distance.
3. **Directed call model**: implement call initiation/answering via existing actions on device parts (e.g. "use phone - call james", "answer phone"). An ongoing call is an activity/condition that does not skip turns (coexists with other actions). Caller room still hears physical utterance; relayed room audio only when `speakerphone` state is enabled.
4. **Relay extension**: extend engine/speech.py `on_speech` to handle carried/comms devices and directed routing to paired endpoints. Use generic `uses` for charge; depleted device cannot relay. Ringing already uses `sound_source` + `current_state: "ringing"`.
5. **Integration**: wire through routes/action.py speech verbs without adding new verbs; respect task-491 (action-verb single source of truth). Ensure parts are addressable as needed and follow task-494 for chained actions where applicable.

## Steps to verify

1. After the runtime exists, load the paired-radio scratch scenario described
   in Browser UI and intended live verification; send Alice's message to Bob,
   then reply from Bob's disconnected area.
   - expected: delivery is directed to the paired endpoint and the reply
     returns over that connection; characters on another channel receive
     nothing.
   - observed: not run - this card is design-only and has no runtime path yet.
2. Repeat with speakerphone disabled and enabled, then with the radio part
   depleted.
   - expected: local room audio follows the speakerphone setting and a depleted
     device cannot relay; no device-specific power field is introduced.
   - observed: not run - this is a future acceptance recipe, not current
     behavior.

## Acceptance

- [ ] Devices are composed as parent items with child part items; parts non-portable/usable via existing gates; no device-specific power property.
- [ ] Speech while using/holding device on `comms_channel` relays directed to endpoints on same channel regardless of distance.
- [ ] Caller room hears physical utterance; relayed room audio only when speakerphone enabled. Ongoing call does not skip turns.
- [ ] Depleted device cannot relay; charge uses generic `uses`/`on_depleted`. No new verbs added.

## Files

- `engine/speech.py` - extend on_speech relay for comms_channel and carried devices; directed routing and speakerphone handling
- `engine/sound.py` - reuse sound_source/current_state for ringing
- `routes/action.py` - integrate speech verbs with device/part actions
- Item models and action system - support device composition (child parts), non-portable parts (omit take), uses for charge/depletion
- Scenario/library data - paired-radio/phone examples for testing (as needed)
- `engine/item_actions.py`, related action resolution per task-491/task-493/task-494 as required

## Browser UI and intended live verification

Intended UI home: Game view → selected character's command input and the
resulting event stream; device-specific actions should be presented through the
existing item/action interaction.

Current availability: Design only. The task's notes settle device composition
and directed relay behavior, but no long-distance communication runtime or live
browser flow is implemented yet.

Live steps when available:
1. Load a scratch scenario with Alice and Bob in disconnected areas. Give each
   a working radio device with matching channel parts, and give Cara a radio on
   a different channel. Select Alice and use the action offered for her radio
   to address Bob, then send “meet at the east gate”.
   - expected: Alice's local room hears only the physical utterance; Bob gets
     the directed message while Cara gets none.
2. Reply as Bob from the other area, then repeat with the radio's speakerphone
   state enabled and disabled.
   - expected: Alice receives Bob's reply over the same directed connection;
     local bystanders hear the relayed room audio only when speakerphone is
     explicitly enabled.
3. Leave the paired device depleted or remove its communication part and
   attempt the same send again.
   - expected: the item/action system reports the unavailable device state and
     does not deliver a remote message.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.


## Reconnaissance (2026-10-20)
- Measured: speech uses area adjacency (engine/speech.py). No comms_channel relay for carried devices found.
- Count: 0 references to comms_channel in code.
- Verdict: STILL_VALID. Design-only, no runtime wiring. Status remains todo.
