---
group: Environment & Climate
---
# Task 149: Sound Propagation System

**Filed**: 2026-07-31  
**Priority**: High  
**Status**: Review  

---

## Summary

Implement a graph-based sound propagation system where speech and sound sources travel through connected areas based on penetration values, door states, and ambient noise levels.

---

## Design

### Speech Levels (4 tiers)

| Level | Penetration | Description | Range Example (all-open chain) |
|-------|-------------|-------------|-------------------------------|
| Whisper | 0 | Only current area | 0 areas |
| Normal | 1 | Default speech | 1 area through open doors |
| Shout | 2 | Loud voice | 4 areas through open doors |
| Scream | 3 | Maximum volume | 6 areas, alerts NPCs |

### Sound Barriers Values

| Way State | Barrier | Notes |
|-----------|---------|-------|
| Open | 0.5 | Open doorways attenuate sound — a chain of opens lets a normal voice reach only the adjacent room |
| See-through (window/grate) | 0.75 | Partial obstruction, more than an open doorway |
| Closed | 1 | Door shut, not locked |
| Locked/Blocked/Hidden | 2 | All treated as "closed" for sound |

### Propagation Rule

Sound travels while `penetration > accumulated_barriers`

Examples:
- Normal speech (pen=1) through open door (bar=0.5): 1 > 0.5 ✓ (reaches next area)
- Normal speech (pen=1) through 2 open doors (bar=1): 1 = 1 ✗ (stops)
- Normal speech (pen=1) through closed door (bar=1): 1 = 1 ✗ (stops)
- Shout (pen=2) through closed door (bar=1): 2 > 1 ✓ (continues)
- Shout (pen=2) through 2 closed doors (bar=2): 2 = 2 ✗ (stops)
- Scream (pen=3) through 2 closed doors + 1 open (bar=2.5): 3 > 2.5 ✓ (continues)

### Ambient Noise

Areas have `environment.noise` property (already exists):
- silent/quiet: 0 (no dampening)
- normal: 1 (reduces effective penetration by 1)
- loud/chaotic: 2 (reduces effective penetration by 2)

Formula: `effective_penetration = speech_level - ambient_noise`

Example: Shout (pen=2) in loud tavern (noise=2) → effective_pen=0 → only reaches current area

### Sound-Dampening Items

Items with `sound_absorbing` tag reduce ambient noise in their area:
- Each item has `sound_absorption` property (default 1)
- Total absorption = sum of all sound_absorbing items in area
- Reduces area's effective noise level

### Sound Sources (Items)

New tag: `sound_source`

Items with this tag emit sound continuously:
- `sound_level`: penetration value (1-3)
- `sound_pattern`: description (e.g., "ringing phone", "blaring alarm")
- `sound_range`: max areas (optional, defaults to sound_level)

Examples:
- Air horn: sound_level=3, pattern="deafening blast"
- Phone ringing: sound_level=2, pattern="insistent ringing"
- Alarm: sound_level=3, pattern="piercing siren"
- Speaker playing music: sound_level=1, pattern="muffled music"

Sound sources propagate like speech but:
- Always active (checked each tick)
- Can trigger NPC awareness/alerts
- May have duration or be toggleable

---

## Implementation — Complete

### Phase 1: Core Sound Propagation (Backend) ✅

1. ✅ Created `engine/sound.py` with full propagation system:
   - `get_way_barrier(way_node)` — returns barrier value based on state
   - `get_area_noise_level(area_node, graph)` — calculates effective noise with absorption
   - `get_effective_penetration(speech_level, ambient_noise)` — applies noise dampening
   - `propagate_sound(origin_area_id, penetration, graph, areas)` — BFS through graph
   - `get_areas_hearing_speech(origin_area_id, speech_level, graph, areas)` — returns list
   - `get_areas_hearing_sound_source(origin_area_id, sound_level, graph, areas)` — returns list
   - `get_sound_sources_in_area(area_id, graph)` — finds active sound sources
   - `format_heard_narration(sound_pattern, direction, is_speech)` — formats narration

2. ✅ Added speech level commands:
   - `speak <text>` / `say <text>` — normal (default)
   - `whisper <text>` — whisper
   - `shout <text>` — shout
   - `scream <text>` — scream

3. ✅ Integrated with narration system:
   - Modified `broadcast_speech()` to accept `speech_level` parameter
   - Propagates sound to adjacent areas based on penetration
   - Characters in hearing areas get narration: "You hear someone speaking from the [direction]"
   - Added to `recent_hearing` with `heard_from` direction

4. ✅ Created tag definitions:
   - `data/library/tags/sound_source.json`
   - `data/library/tags/sound_absorbing.json`

5. ✅ Created comprehensive tests:
   - `tests/test_sound.py` — 21 tests covering barriers, propagation, noise, sound sources

### Phase 2: Sound Sources (Items) ✅

1. ✅ Added sound source processing to `tick_manager.py`:
   - `_process_sound_sources()` method scans areas for items with `sound_source` tag
   - Propagates sound from each active source each tick
   - Notifies characters in hearing areas via `recent_hearing`
   - Logs narration for active player: "You hear [pattern] from the [direction]"
   - Deduplication tracking to avoid duplicate notifications

2. ✅ Added `sound_heard` condition type to `trigger_system.py`:
   - Checks if character has heard a specific sound pattern recently
   - Works with both sound sources and speech
   - Can be used in NPC triggers (e.g., "if sound_heard alarm, investigate")
   - Added to both NPC and item-trigger condition evaluation paths

### Phase 3: Ambient Noise & Dampening ✅

1. ✅ Area environment integration:
   - `noise` property already exists (silent/quiet/normal/loud/chaotic)
   - `get_area_noise_level()` calculates effective noise from environment + items
   - Sound-absorbing items reduce area's effective noise level

2. ✅ Sound propagation applies dampening:
   - `get_effective_penetration()` reduces speech level by ambient noise
   - Loud rooms muffle speech appropriately

### Phase 4: Frontend Visualization ✅

1. ✅ Sound overlay in graph view:
   - `_applySoundOverlay()` in `network-manager.js` colors areas by noise level
   - Uses existing `_noiseColors()` function for color mapping
   - Integrated with overlay view buttons in `templates/index.html`

2. ✅ Sample items created:
   - `alarm_clock.json` — sound_source item with piercing alarm
   - `ringing_phone.json` — sound_source item with insistent ringing
   - `heavy_curtains.json` — sound_absorbing item with absorption value 2

---

## Files Created/Modified

### New Files
- `engine/sound.py` — core sound propagation logic ✅
- `data/library/tags/sound_source.json` — tag definition ✅
- `data/library/tags/sound_absorbing.json` — tag definition ✅
- `tests/test_sound.py` — unit tests (21 tests) ✅
- `data/library/items/alarm_clock.json` — sample sound source ✅
- `data/library/items/ringing_phone.json` — sample sound source ✅
- `data/library/items/heavy_curtains.json` — sample sound absorber ✅

### Modified Files
- `engine/narration.py` — added speech_level parameter, sound propagation ✅
- `virtual_world_engine.py` — pass through speech_level ✅
- `routes/action.py` — added whisper/shout/scream commands ✅
- `engine/tick_manager.py` — added `_process_sound_sources()` method ✅
- `engine/trigger_system.py` — added `sound_heard` condition type ✅
- `static/js/graph/network-manager.js` — sound overlay (already existed) ✅

---

## Verification

### All Tests Passing (21/21)
1. ✅ Whisper in area A → only characters in A hear it
2. ✅ Normal speech in area A → characters in adjacent area B (open door) hear it
3. ✅ Normal speech in area A → characters in area B (closed door) don't hear it
4. ✅ Shout in area A → characters in areas B, C, D, E (4 open doors, bar 0.5 each) hear it
5. ✅ Scream in area A → characters up to 6 open doors away hear it (bar 0.5 each)
6. ✅ Scream through 2 closed doors + 1 open → reaches 3rd area but not 4th
7. ✅ Loud tavern (noise=2) → shout (pen=2) only reaches current area
8. ✅ Normal noise reduces speech range appropriately
9. ✅ Sound sources propagate through graph
10. ✅ Sound sources in loud rooms are muffled
11. ✅ Open doors cost 0.5 barrier — normal speech reaches only the adjacent room
12. ✅ See-through ways have partial obstruction (0.75 barrier)
13. ✅ Locked/blocked/hidden doors all have barrier 2

### Integration Points
- ✅ Speech commands work with all 4 levels
- ✅ Sound sources tick each turn and notify nearby characters
- ✅ `sound_heard` condition can trigger NPC behaviors
- ✅ Graph overlay shows noise levels
- ✅ Recent hearing tracks both speech and sound sources

---

## Usage Examples

### Speech Commands
```
speak Hello everyone!        # Normal speech (pen=1)
whisper Psst, over here...   # Whisper (pen=0, only current area)
shout Hey! Can you hear me?  # Shout (pen=2, through closed doors)
scream Help!                 # Scream (pen=3, alerts 3 areas away)
```

### Creating a Sound Source Item
```json
{
  "id": "blaring_radio",
  "name": "blaring radio",
  "type": "item",
  "tags": ["sound_source", "toggleable"],
  "properties": {
    "current_state": "on",
    "sound_level": 2,
    "sound_pattern": "loud music",
    "weight": 1.0
  }
}
```

### Creating a Sound-Absorbing Item
```json
{
  "id": "acoustic_panels",
  "name": "acoustic panels",
  "type": "item",
  "tags": ["sound_absorbing"],
  "properties": {
    "sound_absorption": 2,
    "weight": 10.0
  }
}
```

### NPC Trigger with sound_heard
```json
{
  "trigger_type": "on_tick",
  "conditions": {
    "operator": "and",
    "conditions": [
      { "type": "sound_heard", "pattern": "alarm" }
    ]
  },
  "effects": [
    { "type": "message", "params": { "text": "The guard investigates the alarm!" } },
    { "type": "move", "params": { "destination": "alarm room" } }
  ]
}
```

---

## Dependencies

- Task 100 (graph overlays) — for sound visualization ✅ (already existed)
- Task 141 (lighting system) — similar graph-scan pattern ✅

---

## Notes

- Followed the lighting system pattern from task-141 (graph-scan approach) ✅
- Sound sources can be toggleable items (use existing toggleable system)
- Consider adding "sound_echo" for caves/large halls (future enhancement)
- NPCs could have "hearing" trait (good/poor hearing) affecting perception (future)
- Sound propagation is deterministic — same setup always produces same results
- Deduplication prevents spam when sound sources tick continuously
