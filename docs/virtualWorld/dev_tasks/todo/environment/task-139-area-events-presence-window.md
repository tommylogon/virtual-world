---
group: Graph & Area UX
---
# Area Events: Presence-Scoped Window

**Filed**: 2026-07-30  
**Priority**: Medium  
**Status**: Design  

---

## Summary

Area events are scoped to a character's presence in the room. Events only appear in a character's prompt if the character was physically in the same room when the event happened. Entering a room does not let you see events that happened before you arrived. Leaving a room means you don't see events that happen after you left.

---

## Current Broken Behaviour

The frontend `_areaEventLog` accumulates up to **50 events per area** and never clears during gameplay. The prompt builder falls back to this log when backend `turn_events` is empty (start of turn cycle). This means characters see events from many cycles ago, including events that happened before they entered the room or after they left.

---

## Design: Presence-Scoped Event Window

### Concept

Each character carries a **room entry tick** — the game tick when they last entered their current area. Only events with a tick >= that entry tick are injected into the character's prompt.

When a character moves to a new area, their entry tick resets to the current tick. Events from the previous room are no longer injected.

### Layer 2: Sensory Perception Filtering

On top of presence-scoping, each event carries a **sensory channel** tag. A character's state determines which channels they can perceive.

#### Sensory Channels

| Channel | Tag | What it covers | Example events |
|---------|-----|----------------|----------------|
| Visual | `visual` | Things you see | Reading, examining, expressions, gestures, item appearances |
| Auditory | `auditory` | Things you hear | Speech, footsteps, door sounds, item clatter, combat noise |
| Tactile | `tactile` | Things you feel (same room contact) | Being touched, temperature shifts, wind, shoving |

Most events are `["visual", "auditory"]` — both sight and sound register them. Some are one or the other:
- Speaking = `["auditory"]` (only heard, not seen)
- Examining a book = `["visual"]` (only seen, no sound)
- Picking a lock = `["auditory"]` (hearing the click) — but could also be `["visual", "auditory"]`

#### Character State → Available Senses

| State | Visual | Auditory | Tactile | Notes |
|-------|--------|----------|---------|-------|
| Normal | ✅ | ✅ | ✅ | Full perception |
| Blind (condition/trait) | ❌ | ✅ | ✅ | Hears sounds, feels touch |
| Deaf (condition) | ✅ | ❌ | ✅ | Sees actions, no speech |
| Sleeping | ❌ | ✅ (only loud/distinct) | ❌ | Wakes on loud noises |
| Unconscious | ❌ | ❌ | ❌ | Perceives nothing |
| Dead / Ghost | ❌ | ❌ | ❌ | Perceives nothing (ghosts see/speak separately) |

#### Event Filtering

An event is only injected into the prompt if the character possesses **at least one** of the event's sensory channels.

**Example with the Bookshop scenario:**

```
TICK 3 — Library, same tick and same presence:
  Jake: examines a bookshelf carefully    → event: senses=["visual"], area=Library
  Butcher (still in Library):             → Butcher is present, sees this
  → Butcher is blind:                     → Butcher has no "visual" channel → BLOCKED

TICK 5 — Kitchen:
  Jake: says "I found a key"              → event: senses=["auditory"], area=Kitchen
  Butcher (in Kitchen, deaf):             → Butcher has no "auditory" channel → BLOCKED
  Butcher sees Jake's lips move           → That's a separate visual observation
  → Events can have dual channels: "I found a key" → ["auditory"] only (pure speech)
```

#### Event Data Model

```python
# Each turn event stored in logging_events.py:
{
    "tick": 5,
    "area": "Kitchen",
    "actor": "Jake",
    "action": "speak",
    "description": "Jake says 'I found a key'",
    "senses": ["auditory"],            # NEW — which senses perceive this
    "initiative": 21                   # NEW — for same-tick ordering
}

# Movement events:
{
    "tick": 2,
    "area": "Library",
    "actor": "Jake",
    "action": "move",
    "description": "Jake enters the Library from the Kitchen",
    "senses": ["visual", "auditory"],  # both sight and sound
    "initiative": 21
}
```

#### Determining Event Senses

Each action type maps to default senses:

| Action type | Default senses | Notes |
|-------------|----------------|-------|
| `speak`, `say`, `shout`, `whisper` | `["auditory"]` | Pure audio |
| `move`, `walk`, `run` | `["visual", "auditory"]` | Seen moving + heard footsteps |
| `examine`, `read`, `look` | `["visual"]` | Only visual |
| `take`, `drop`, `use` | `["visual", "auditory"]` | Motion + item sounds |
| `attack`, `hit` | `["visual", "auditory"]` | Visual action + impact sounds |
| `emote` (non-verbal) | `["visual"]` | Expression/gesture (unless described with sound) |
| `open`, `close` | `["auditory"]` | Door sounds — creak, click |
| Default / unknown | `["visual", "auditory"]` | Both senses assumed |

Overridable per-event in the action code if the action generates a specific sensory profile.

### Full Filter Function

```js
function getVisibleEvents(events, charName, currentArea, entryTick, senses) {
    return events.filter(evt => {
        if (evt.actor === charName) return false;                 // not your own
        if (evt.area !== currentArea) return false;                // not this room
        if (evt.tick < entryTick) return false;                    // before you arrived

        // Sensory check: does observer have at least one sense the event provides?
        const evtSenses = evt.senses || ['visual', 'auditory'];   // default both
        const canPerceive = evtSenses.some(s => senses.includes(s));
        if (!canPerceive) return false;                            // can't sense it

        return true;
    });
}
```

### Detailed Example: Presence + Senses

**Setup:**
- Rooms: Kitchen, Library
- Characters: Jake (normal), Butcher (blind), Elena (deaf)
- Initiative order: Jake → Butcher → Elena
- 1 cycle = 3 actions = 1 tick

**Turn-by-turn trace (presence + senses):**

```
TICK 1 — Cycle start
  Jake (Kitchen, normal): says "hello"
    → event: tick=1, area=Kitchen, actor=Jake, action="hello", senses=["auditory"], init=21
  Butcher (Library, blind): reads a book
    → event: tick=1, area=Library, actor=Butcher, action="reading", senses=["visual"], init=20
  Elena (Kitchen, deaf): examines a knife
    → event: tick=1, area=Kitchen, actor=Elena, action="examining knife", senses=["visual"], init=19

TICK 2 — Queue wraps, new cycle
  Jake (Kitchen, normal): moves to Library
    → Jake.entry_tick[Kitchen] cleared, Library entry set to tick=2
    → event: tick=2, area=Kitchen→Library, actor=Jake, action="moved to Library", senses=["visual","auditory"], init=21
    Butcher still in Library → Butcher sees Jake enter (auditory) ← Butcher is blind, hears footsteps
  Butcher (Library, blind): moves to Kitchen
    → Butcher.entry_tick[Library] cleared, Kitchen entry set to tick=2
    → event: tick=2, area=Library→Kitchen, actor=Butcher, action="moved to Kitchen", senses=["visual","auditory"], init=20
    Jake just entered Library → Jake sees Butcher leave (both visual+auditory)
  Elena (Kitchen, deaf): stays in Kitchen, says "nice knife"
    → event: tick=2, area=Kitchen, actor=Elena, action="nice knife", senses=["auditory"], init=19
    Butcher entered Kitchen this same tick (after moving) → Butcher did NOT hear Elena (he arrived after she spoke, initiative 19 < 20)
    Jake left Kitchen → doesn't see this

TICK 3 — New cycle
  Butcher (Kitchen, blind): examines counter by touch
    → event: tick=3, area=Kitchen, actor=Butcher, action="examining counter", senses=["tactile"], init=21
    Elena (Kitchen, deaf): sees Butcher's hands moving → senses=["visual"] picks it up? 
    No — the event is tagged senses=["tactile"]. Elena has visual, not tactile → BLOCKED for Elena
  Elena (Kitchen, deaf): says "there's flour here"
    → event: tick=3, area=Kitchen, actor=Elena, action="there's flour here", senses=["auditory"], init=20
    Butcher is blind but has auditory → Butcher HEARS Elena → visible
  Jake (Library, normal): examines a bookshelf
    → event: tick=3, area=Library, actor=Jake, action="examining bookshelf", senses=["visual"], init=19
    (Alone in Library, sees own event → filtered)

TICK 4 — New cycle
  Jake (Library, normal): takes a book
    → event: tick=4, area=Library, actor=Jake, action="took a book", senses=["visual","auditory"], init=21
  Butcher (Kitchen, blind): leaves to Library
    → Butcher.entry_tick[Kitchen] cleared, Library entry set to tick=4
    → event: tick=4, area=Kitchen→Library, actor=Butcher, action="moved to Library", senses=["visual","auditory"], init=20
    Jake in Library: sees Butcher enter (both visual+auditory)
  Elena (Kitchen, deaf): stays in Kitchen, lights a lamp
    → event: tick=4, area=Kitchen, actor=Elena, action="lit a lamp", senses=["visual"], init=19
    (Alone in Kitchen, sees own event → filtered)
```

**Per-character prompt injection for each turn:**

| Turn | Character | Room | State | Events in prompt | Reasoning |
|------|-----------|------|-------|-----------------|-----------|
| T1 | Jake | Kitchen | normal | (none) | First turn in Kitchen |
| T1 | Butcher | Library | blind | (none) | First turn in Library |
| T1 | Elena | Kitchen | deaf | (none) | First turn in Kitchen |
| T2 | Jake | Library | normal | `[tick=1] Butcher reading`? No — Jake entered Library at tick=2. Butcher's tick=1 event was before Jake arrived → BLOCKED by presence. Jake sees nothing. | |
| T2 | Butcher | Kitchen | blind | `[tick=1] Elena examined a knife`? No — Butcher entered Kitchen at tick=2, Elena's tick=1 event was before arrival → BLOCKED by presence. Also senses=["visual"] → Butcher is blind → BLOCKED by senses anyway. Butcher sees nothing. | |
| T2 | Elena | Kitchen | deaf | `[tick=1] Jake said "hello"` → senses=["auditory"] → Elena is deaf → BLOCKED by senses. Also tick=1 < entry_tick=1 (Elena started in Kitchen at tick=0? Actually entry_tick starts at 0 for starting area). So tick=1 >= 0 → PRESENT → but BLOCKED by deafness. Elena sees nothing. | |
| T3 | Butcher | Kitchen | blind | `[tick=2] Elena said "nice knife"` → tick=2 >= entry_tick=2 → PRESENT (barely). senses=["auditory"] → Butcher has auditory ✅. But wait — initiative: Elena (19) acted BEFORE Butcher moved (20). Butcher wasn't in Kitchen when Elena spoke → BLOCKED by presence (sub-tick ordering). Sees nothing. `[tick=2] Butcher moved to Kitchen` (self → filtered). | |
| T3 | Elena | Kitchen | deaf | `[tick=3] Butcher examined counter` → senses=["tactile"] → Elena has visual+auditory only → BLOCKED by senses. `[tick=2] Elena said "nice knife"` (self → filtered). Sees nothing. | |
| T3 | Jake | Library | normal | `[tick=2] Butcher moved to Kitchen` → senses=["visual","auditory"] → Jake has both ✅. tick=2 >= entry_tick=2 → PRESENT ✅. Butcher was in Library, Jake was entering Library same tick. How did Jake see Butcher leave? Jake arrived in Library at tick=2 (his move action). Butcher was already there at the START of tick 2 (before moving). Jake's entry_tick=2 for Library. Butcher's "move to Kitchen" event has tick=2 and happened when Butcher acted (init=20). Jake entered Library at init=21 (his move). So Butcher leaves at init 20, Jake enters at init 21 — Jake arrives AFTER Butcher left. BLOCKED by presence (sub-tick). Jake sees nothing. | |
| T4 | Jake | Library | normal | `[tick=3] Jake examined bookshelf` (self → filtered). `[tick=4] Butcher moved to Library` → senses=["visual","auditory"] ✅. tick=4 >= entry_tick=2 → PRESENT ✅. But Jake and Butcher both in Library at different sub-ticks? Butcher's move at init 20, Jake's "took a book" at init 21. Jake's action happened first (init higher). Butcher's event at tick=4 happened AFTER Jake took the book (init 20 < 21). Jake is still in Library → PRESENT → sees Butcher enter. ✅ | |
| T4 | Butcher | Library | blind | `[tick=4] Jake took a book` → Butcher entered Library at tick=4, Jake's "took a book" happened at init=21 (before Butcher's init=20). Butcher was in Kitchen when Jake took the book → BLOCKED by presence. Sees nothing. | |
| T4 | Elena | Kitchen | deaf | `[tick=3] Butcher examined counter` → BLOCKED by senses (tactile). `[tick=3] Elena said "there's flour"` (self → filtered). `[tick=4] Elena lit a lamp` (self → filtered). Sees nothing. | |

**Key insight from the trace:** Presence-scoping + sub-tick ordering + sensory filtering means characters often see very little. That's correct — characters should only know what they can actually perceive. The prompt should include "You don't notice anything unusual" rather than fabricating knowledge.

**Wait — this is too strict.** Butcher arrived at tick=4 and Jake's tick=4 event happened "at the same tick" (same cycle). Which comes first?

**Resolution:** Events within the same tick are ordered by initiative. If Butcher arrives at the END of his action (after moving), and Jake's "takes a book" happened EARLIER in the initiative order (Jake acts before Butcher), then:
- Jake's tick=4 event: `Jake took a book` (happened when Jake acted, initiative 21)
- Butcher's tick=4 event: `Butcher moved to Library` (happened when Butcher acted, initiative 20)

Butcher's entry tick for Library = 4. Jake's event at tick=4 happened in the same tick but at an earlier initiative position. Since Butcher was NOT in Library when Jake acted (he was still in Kitchen), Butcher should NOT see it.

**Key rule:** An event is only visible if the character was in the same area at the time the event occurred. "At the time" = same tick, same area, and the character hasn't moved yet.

### Implementation: Event Tick + Entry Tick

```python
# On player:
player.area_entry_tick = {}  # {"Kitchen": 1, "Library": 2}

# When a character moves to a new area:
def move_to_area(player, new_area, current_tick):
    old_area = player.current_area
    # Freeze entry tick for old area (no more events visible from there)
    player.area_entry_tick[old_area] = None  # or just leave as-is, no longer queried
    # Set entry tick for new area
    player.area_entry_tick[new_area] = current_tick
    player.current_area = new_area
```

```js
// In prompt-builder.js, filter events by presence:
function getVisibleEvents(events, charName, currentArea, entryTick) {
    return events.filter(evt => {
        if (evt.actor === charName) return false;          // never see own events
        if (evt.area !== currentArea) return false;         // different room
        if (evt.tick < entryTick) return false;             // happened before we arrived
        // If same tick, check initiative: if the actor acted before we entered
        // this tick, we shouldn't see it. Requires initiative ordering.
        return true;
    });
}
```

### Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Character stays in room for 5 ticks | Sees all events in that room from entry tick → current tick, filtered by available senses |
| Character leaves and re-enters same room | Entry tick resets to re-entry tick. Misses events between leaving and re-entering. |
| Two characters in same room, one leaves | Leaver stops seeing events. Stay-er continues seeing events (if they can sense them). |
| Character enters room, someone else acts same tick | If entrant moves first (lower initiative), they arrive after the action → don't see it. If entrant moves last, they miss actions that happened before they arrived in the same tick. |
| Blind character enters room | Can only hear auditory events — visual events (examining, reading, gestures) are invisible |
| Deaf character enters room | Can see visual events but misses all speech |
| Sleeping character in room | Perceives nothing unless a loud auditory event occurs (needs a loudness threshold on events) |
| Unconscious/dead character in room | Perceives nothing regardless of event type — all events filtered out |
| Character goes blind mid-game (condition applied) | Stops seeing visual events from that tick forward. Prior events unaffected (already perceived). |
| Queue wraps, new cycle begins | No special behaviour — same presence + sense rules apply. Entry ticks survive cycle boundaries. |
| New game / restart | All entry ticks reset to 0. All character states reset to normal. |

### Data Storage

**Backend** (source of truth):
- `player.area_entry_tick: dict[str, int]` — area name → tick when character entered
- Serialized in `player.to_dict()` and sent in `/api/state`
- Events are stored as `{tick, area, actor, action, description}` in `logging_events.py`

**Frontend**:
- `_areaEventLog` becomes a **temporary per-cycle log** OR is replaced entirely by filtering backend events
- No more indefinite accumulation — the frontend log is a fallback that gets pruned per-cycle, or removed entirely

### Migration

1. Add `area_entry_tick` to `player.py`
2. Update `move_to_area()` in `engine/movement.py` to set the entry tick
3. Update `prompt-builder.js` to filter events by entry tick + area match
4. Decide: keep `_areaEventLog` as a UI display log only (not a prompt data source), or prune it per-cycle
5. Remove the fallback in prompt-builder that reads `_areaEventLog` — or keep it but filter by presence
