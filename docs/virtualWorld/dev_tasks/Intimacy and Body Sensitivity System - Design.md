# Nipple & Erogenous Zone System - Design Document v3

## 1. Generalized Erogenous Zone System

### Body Part Structure

**CORRECTION:** Body parts do NOT need to be graph nodes. The paperdoll system already exists as a layered equipment grid. Body state data should be stored as **conditions on the player** with per-body-part metadata, augmented by a lightweight `body_state` dict for quick numeric lookups.

```python
# Player class extension - quick numeric state for calculations
self.body_state = {
    "nipples": {
        "left": {
            "hardness": 0.0,      # 0-1, erectness
            "puffiness": 0.0,     # 0-1, areola swelling
            "flush": 0.0,         # 0-1, redness
            "sensitivity": 0.9,   # base sensitivity (0.0-1.0+)
            "injury": null,
            "pierced": False
        },
        "right": {
            "hardness": 0.0,
            "puffiness": 0.0,
            "flush": 0.0,
            "sensitivity": 0.7,
            "injury": null,
            "pierced": False
        }
    },
    "cheeks": {
        "flush": 0.0             # blushing level
    },
    "genitals": {
        "erection": 0.0,         # penis/clitoris hardness (0-1)
        "wetness": 0.0,          # vaginal lubrication (0-1)
        "sensitivity": 0.8,
        "injury": null
    },
}

# Body part SENSITIVITY as a condition (multi-instance support)
# Multiple condition instances can stack on the same body part
player.conditions["bodypart_sensitive"] = [
    {
        "duration": 30,           # 30 ticks of heightened sensitivity
        "source": "lydia",        # Who caused it
        "body_part": "left_nipple",
        "sensitivity_mult": 1.5,  # Multiplicative
    },
    {
        "duration": 15,
        "source": "cold_weather",
        "body_part": "left_nipple",
        "sensitivity_mult": 1.2,
    }
]
```

### Existing Paperdoll System (Layered Equipment)

A full paperdoll system exists with 13 visual areas mapped to equipment slots:

| Visual Area | Slot | Label | Max Depth |
|---|---|---|---|
| `head` | `head` | Head | 3 |
| `neck` | `neck` | Neck | 2 |
| `larm`/`rarm` | `arms` | Arms | 2 |
| `torso` | `torso` | Torso | 5 |
| `lhand`/`rhand` | `hands` | Hands | 2 |
| `waist` | `waist` | Waist | 2 |
| `hand_l`/`hand_r` | `hand_left`/`hand_right` | Held items | 1 |
| `back` | `back` | Back | 2 |
| `feet` | `feet` | Feet | 3 |
| N/A | `accessory` | Accessory | None |

**Stacking:** Items stack from **innermost (index 0)** to **outermost (last index)** in `player.equipped` lists. This is already tracked and displayed with `+N more` badges in the UI.

**Body Part Accessibility:** The paperdoll knows which slots items occupy. To check if a body part is accessible, check the outer layers of the relevant slot stack.

---

## 2. Involuntary Behavior System

### Existing Engine Triggers (Already Working)

Vital threshold triggers already exist in `tick_manager.py`:

| Threshold | Effect | Location |
|---|---|---|
| `Energy <= 0` | Applies `unconscious`, drops held items | `tick_turn()` line 184-199 |
| `Bladder >= 100` | `Hygiene -= 30` | `tick_turn()` line 211-213 |
| `Hunger <= 0` | `HP -= 1` per tick | `tick_turn()` line 202-203 |
| `Thirst <= 0` | `HP -= 2` per tick | `tick_turn()` line 204-205 |
| `Sanity <= 0` | `HP -= 1` per tick | `tick_turn()` line 206-207 |
| `HP <= 0` | Death, spawn body item | `tick_turn()` line 226-242 |
| `Temperature < 35` | `HP -= 3` per tick | `tick_turn()` line 329-330 |
| `Temperature > 40` | `HP -= 3` per tick | `tick_turn()` line 335-336 |

### Planned Behaviors (as Conditions)

These are modeled as **conditions with symptoms and periodic effects:**

```python
# In player.py CONDITION_DEFINITIONS
"nipple_hard": {
    "name": "Hard Nipples",
    "description": "Your nipples are visibly erect.",
    "symptoms": {
        None: "Your nipples are prominent and sensitive."
    },
    "periodic": {"Arousal": 1},  # Hard nipples feed back into arousal
    "known": True,  # Visible to anyone looking
},

"blushing": {
    "name": "Blushing",
    "description": "Your cheeks are flushed red.",
    "symptoms": {
        None: "You're blushing deeply."
    },
    "periodic": {},  # Just visual - no vitals effect
    "known": True,
},

"wetness": {
    "name": "Wetness",
    "description": "You're physically aroused and wet.",
    "symptoms": {
        None: "You're wet and ready."
    },
    "periodic": {"Arousal": 2},  # Wetness feeds arousal
    "known": False,  # Not visible unless exposed
},
```

**Triggers:**
- **Nipple hardening:** Cold temperature, arousal spike, fear, random
- **Penis erection:** Arousal > 30, random during sleep, morning
- **Vaginal wetness:** Arousal > 20, direct stimulation
- **Blushing:** Embarrassment, arousal > 40, Exhibitionist trait

**Implementation:** Check conditions in `tick_turn()` each tick and apply/remove as needed.

---

## 3. Stimulation Action System

### Existing Verb System (Already Working)
- Verb variations: whisper/say/shout/scream with penetration values
- Movement verbs: go/dash/crawl/climb/jump
- "use item on" and "target" actions exist

### New Intimacy Verbs
- grab, touch, rub, caress, pinch, pull, squeeze, kiss, lick, suck, bite, blow, tickle

### Action Type Distinction

| Type | Example | Effect |
|---|---|---|
| `attack` | punch to face | Does damage (`combat.py` handles this) |
| `interact` | slap on ass | No damage, just triggers interaction effects |

**Action Structure:**
```json
{
    "action": "kiss",
    "type": "interact",
    "target": "lydia",
    "where": "lips",
    "intensity": "gentle",
    "emote": "He leans in and kisses her lips"
}
```

**Combat Example:**
```json
{
    "action": "punch",
    "type": "attack",
    "target": "jake",
    "where": "face",
    "emote": "Lydia punches Jake in the face so hard her hand hurts"
}
```

### DC Calculations

DC calculations need to consider multiple factors:

- **What action:** Kissing (easy) vs punching (hard) vs grope (medium)
- **Where:** Lips (easy) vs breast through clothing (medium) vs under clothing (hard) vs genitals (very hard)
- **Who:** Partner (easy) vs stranger (hard) vs enemy (very hard)
- **Social context:** Private (easy) vs public with onlookers (hard) vs crowded train (medium)
- **NPC relationship:** High trust (DC -5), low trust (DC +10), negative (DC +15)
- **NPC mood:** Relaxed (easy), stressed (hard), angry (very hard)
- **Current situation:** Saying goodbye (DC -5), couple in bed (DC -10), angry partner (DC +15)

**Target Accessibility:**
- You CAN grab someone's breast through a shirt and bra (clothing layers present but accessible)
- You CANNOT grab someone's nipple through a shirt and bra (needs direct skin contact)
- You CAN kick someone's balls unless they're wearing body armor with crotch protection
- Clothing with `coverage` property blocks access to certain body parts

---

## 4. Three-Vital Pleasure System (Using Conditions)

### New Vitals

```python
# Add to player.vitals dict initialization
vitals = {
    # ... existing vitals ...
    
    # NEW VITALS:
    "Arousal": 0,        # 0-100, "I'm getting turned on"
    "Stimulation": 0,    # 0-100, "I'm getting closer"
    "Pleasure": 0,       # 0-100, "How good I feel right now"
}
```

### Arousal
- **Range:** 0-100
- **Decay:** Slowly decays over time when not stimulated (in `tick_turn()`)
- **Thresholds:**
  - 0-15: baseline/uninterested
  - 15-30: warming up → triggers `warming_up` condition
  - 30-50: actively turned on → triggers `aroused` condition
  - 50-90: highly aroused → triggers `highly_aroused` condition
  - 90-100: frantic → triggers `frantic` condition

### Conditions for Arousal States

```python
# In player.py CONDITION_DEFINITIONS
"warming_up": {
    "name": "Warming Up",
    "description": "You feel a pleasant warmth spreading through you.",
    "symptoms": {
        None: "You're starting to feel warm and tingly."
    },
    "periodic": {"Stimulation": 1},
    "known": True,
},
"aroused": {
    "name": "Aroused",
    "description": "You're actively turned on.",
    "symptoms": {
        50: "You're warm and restless, skin more sensitive.",
        30: "Your breathing is getting heavier, you feel flushed."
    },
    "periodic": {"Stimulation": 2},
    "attack_mod": -2,
    "defense_mod": -2,
    "auto_fail_checks": ["perception", "concentration"],
    "known": True,
},
"highly_aroused": {
    "name": "Highly Aroused",
    "description": "You can barely focus on anything but the feeling.",
    "symptoms": {
        70: "Every touch sends electricity through you.",
        50: "You're trembling, desperate for more."
    },
    "periodic": {"Stimulation": 3, "Energy": -2},
    "attack_mod": -3,
    "defense_mod": -3,
    "auto_fail_checks": ["perception", "concentration", "willpower"],
    "known": True,
},
"frantic": {
    "name": "Frantic",
    "description": "You need release. Now.",
    "symptoms": {
        None: "You can't think straight. You need to come."
    },
    "periodic": {"Stimulation": 4, "Energy": -3, "Sanity": -2},
    "attack_mod": -5,
    "defense_mod": -5,
    "auto_fail_checks": ["perception", "concentration", "willpower", "self_control"],
    "known": True,
},
```

### Stimulation
- **Purpose:** "I'm getting closer" meter
- **Builds from:** Direct erogenous zone stimulation actions
- **Decay:** Drops when stimulation stops (non-linear curve)
- **Release threshold:** When stimulation hits target window → triggers release event

### Pleasure
- **Purpose:** Immediate sensation feedback
- **Feeds into stimulation:** High pleasure actions build stimulation faster
- **Target window:** Dynamic, based on arousal, mood, traits
- **Overstimulation:** If pleasure exceeds current comfort threshold → flips to discomfort/pain

### Overstimulation as a Condition

```python
"overstimulated": {
    "name": "Overstimulated",
    "description": "Every touch is too much.",
    "periodic": {"Pleasure": -3, "Energy": -1},
    "symptoms": {
        5: "You flinch at every touch, oversensitive.",
        3: "Your skin feels raw and overworked.",
        1: "You need it to stop — now."
    },
    "excludes": ["satisfied", "numb"],
    "blocks_actions": False,
    "attack_mod": -3,
    "defense_mod": -3,
    "known": True,
},
```

### Release Event (in `tick_turn()`)

```python
def _check_release_threshold(self, player):
    """Check if stimulation + arousal meet release criteria."""
    stimulation = player.vitals.get("Stimulation", 0)
    arousal = player.vitals.get("Arousal", 0)
    
    # Release threshold: stimulation > 65 AND arousal > 40
    if stimulation >= 65 and arousal >= 40:
        self._trigger_release_event(player)
        
def _trigger_release_event(self, player):
    """Release event cascade."""
    # Vital changes
    player.vitals["Energy"] = max(0, player.vitals["Energy"] - 20)
    player.vitals["Entertainment"] = min(100, player.vitals["Entertainment"] + 30)
    player.vitals["Hygiene"] = max(0, player.vitals["Hygiene"] - 10)
    player.vitals["Sanity"] = min(100, player.vitals["Sanity"] + 15)
    player.vitals["Stimulation"] = 5
    player.vitals["Arousal"] = max(0, player.vitals["Arousal"] - 30)
    
    # Apply conditions
    player.add_condition("satisfied", duration=20)
    player.add_condition("overstimulated", duration=5)
    
    # Update description
    if self.world.auto_generate_descriptions:
        self._update_equipment_description(player)
```

### Edging Mechanic

When stimulation is high but doesn't trigger release:
- **Decay curve:** Slow at first (tick +0-2), then faster
- **Sensitivity increases:** Each near-miss adds a `sensitized` condition
- **Threshold lowers slightly:** Release becomes easier

```python
def _apply_edging_effect(self, player):
    """Apply edging effects when stimulation is high but below threshold."""
    stimulation = player.vitals.get("Stimulation", 0)
    if 50 <= stimulation < 65:
        # Add sensitized condition stacks
        player.add_condition("sensitized", duration=10, level=1)
        # Slight arousal increase from edging
        player.vitals["Arousal"] = min(100, player.vitals["Arousal"] + 1)
```

---

## 5. Mood & Context Modifiers

### Existing Mood System

Mood is already tracked via `vitals`:
- `Social` affects mood (lonely → sad)
- `Sanity` affects mental state
- `Entertainment` affects boredom
- Temperature, Hunger, Thirst, Energy all affect mood

### Sensitivity Modifiers (via Conditions)

```python
"relaxed": {
    "name": "Relaxed",
    "description": "You feel calm and comfortable.",
    "periodic": {"Arousal": 1, "Stimulation": 1},
    "known": False,
},
"stressed": {
    "name": "Stressed",
    "description": "You're anxious and on edge.",
    "periodic": {"Arousal": -1, "Stimulation": -1},
    "known": False,
},
"embarrassed": {
    "name": "Embarrassed",
    "description": "You're blushing and mortified.",
    "periodic": {"Arousal": 2, "Sanity": -2},
    "known": True,
},
"depressed": {
    "name": "Depressed",
    "description": "You feel hollow and disconnected.",
    "periodic": {"Arousal": -3, "Stimulation": -2, "Pleasure": -3},
    "known": False,
},
```

### Relationship Value Integration

`player.relationships` already exists. Use `closeness` value:
- High trust/relationship: Sensitivity increases, pleasure ceiling goes up
- Low relationship: Sensitivity reduced
- Negative relationship: Mood penalties or reduced effect

---

## 6. Clothing & Friction System

### Clothing Comfort & Friction Properties

Add to item node properties (graph nodes are fine for items):

```python
item.properties = {
    "comfort": 0.8,      # 0-1, how nice it feels against skin
    "friction": 0.3,     # 0-1, how much micro-stimulation it causes
    "coverage": 0.9,     # 0-1, how much it covers/obscures
    "opacity": 0.8,      # 0-1, how see-through it is
}
```

### Friction → Arousal Trickle

In `tick_turn()`:
```python
def _apply_clothing_friction(self, player):
    """Apply arousal trickle from clothing friction."""
    friction_total = 0
    equipped = self.equipment.get_full_equipment(player.name)
    for slot, items in equipped.items():
        for item_name in items:
            node = self.graph.get_node_by_name(item_name)
            if node:
                friction = node.properties.get("friction", 0)
                friction_total += friction * 0.5  # Half effect per item
    # Apply minimal arousal trickle (0-3 per tick)
    if friction_total > 0:
        player.vitals["Arousal"] = min(100, player.vitals["Arousal"] + friction_total)
```

### Environmental Interaction

Environment tracking exists (`area_node.properties.environment`). Extend with:

```python
# Area environment
environment = {
    "temperature": 21,
    "humidity": 0.5,
    "weather": "rain",  # 'rain', 'snow', 'sunny', 'windy'
    "wind_speed": 15,   # km/h
}
```

**Wet clothing:**
- If weather is 'rain' or player is swimming → clothing becomes wet
- Wet clothing: opacity increases (becomes transparent), friction changes
- Trigger `_update_equipment_description()` when wetness changes

### Layer Visibility (Description Enrichment)

**The real fix:** Enrich the LLM prompt with item descriptions + body state.

**Current prompt:**
```
CURRENT EQUIPMENT:
- torso: bra → loose_shirt (innermost to outermost)
```

**Improved prompt:**
```
CURRENT EQUIPMENT:
- torso: black lace bra with shoulder straps (opaque, coverage: 0.8) → 
         sheer pale pink blouse, unbuttoned (opacity: 0.3, coverage: 0.4)

BODY STATE:
- Nipples: hard (arousal-induced)
- Cheeks: flushed
- Skin: slightly sweaty
- Conditions: highly_aroused, sensitized
```

Now the LLM can reason about what's visible through layers.

---

## 7. Trait System

### Trait Definitions (Add to `engine/traits.py`)

```python
"wired_differently": {
    "name": "Wired Differently",
    "description": "Genital stimulation minimal, nipple stimulation enhanced",
    "multipliers": {
        "body_part:nipple": 3.0,   # Nipple actions ×3.0
        "body_part:genital": 0.1,  # Genital actions ×0.1
    },
    "effects": ["nipple_focused"],
},

"attention_seeker": {
    "name": "Attention Seeker",
    "description": "Being looked at raises arousal",
    "effects": ["aroused_by_attention"],
    "condition_triggers": {
        "on_look": "aroused"  # Being looked at triggers arousal
    },
},

"exhibitionist": {
    "name": "Exhibitionist",
    "description": "Being topless/nude in public raises arousal",
    "effects": ["aroused_by_public_nudity"],
    "behavior_prompt": "You are an exhibitionist who enjoys being seen.",
    "condition_triggers": {
        "on_exposure": "aroused"
    },
},

"quick_recovery": {
    "name": "Quick Recovery",
    "description": "Overstimulation phase shorter",
    "effects": ["faster_recovery"],
    "duration_modifiers": {
        "overstimulated": 0.5  # Half duration
    },
},

"sensory_memory": {
    "name": "Sensory Memory",
    "description": "Phantom sensations linger after release",
    "effects": ["lingering_sensitivity"],
    "condition_triggers": {
        "on_release": "lingering_sensitivity"  # Release triggers lingering condition
    },
},
```

### Applying Trait Multipliers

The action already knows the body part, so multiplier application is straightforward:

```python
def apply_stimulation(player, body_part, base_gain):
    """Apply trait multipliers based on body_part."""
    gain = base_gain
    for trait in player.traits:
        multiplier = TRAIT_DEFINITIONS.get(trait, {}).get("multipliers", {})
        # Check for body_part-specific multiplier
        if f"body_part:{body_part}" in multiplier:
            gain *= multiplier[f"body_part:{body_part}"]
        # Check for generic multiplier
        if "all_actions" in multiplier:
            gain *= multiplier["all_actions"]
    return gain
```

---

## 8. NPC Perception & Reaction

### NPC Awareness

NPCs already "notice" things via the LLM seeing character descriptions. For mechanical perception:

```python
def _calculate_perception_difficulty(self, npc, player, condition):
    """Calculate difficulty for NPC to notice something."""
    base = 10
    
    # NPC traits
    if "observant" in npc.traits:
        base -= 5
    if "oblivious" in npc.traits:
        base += 5
    if "perverted" in npc.traits and condition == "aroused":
        base -= 5
    
    # Lighting
    light = self.lighting.get_ambient_light(npc.current_area)
    if light < 20:
        base += 10
    elif light > 80:
        base -= 5
    
    # Distance (simplified)
    # NPCs in same room → no penalty; nearby rooms → +5; etc.
    
    # Clothing layers
    if condition in ["nipple_hard", "blushing", "sweating"]:
        # Check coverage/opacity of outer layers
        outer_coverage = self._get_outer_coverage(player)
        base += outer_coverage * 10
    
    return base
```

### NPC Reaction Framework

```python
def process_npc_reaction(self, npc, player, stimulus_type, stimulus_data):
    """Generate NPC reaction to player state/actions."""
    # 1. Determine if NPC noticed
    perception_dc = self._calculate_perception_difficulty(npc, player, stimulus_type)
    if not self._check_perception(npc, perception_dc):
        return None
    
    # 2. Determine reaction based on NPC traits and context
    reaction_type = "ignore"
    
    if "prudish" in npc.traits and stimulus_type in ["aroused", "nipple_hard"]:
        reaction_type = "disapprove"
    elif "open_minded" in npc.traits:
        reaction_type = "approach" if npc.vitals["Social"] > 50 else "ignore"
    elif "attracted" in npc.traits and stimulus_type in ["aroused", "wetness"]:
        reaction_type = "approach"
    
    # 3. Execute reaction
    if reaction_type == "disapprove":
        self._npc_disapprove(npc, player)
    elif reaction_type == "approach":
        self._npc_approach(npc, player)
    elif reaction_type == "comment":
        self._npc_comment(npc, player, stimulus_type)
    # etc.
```

---

## 9. Dynamic Description Regeneration

### Current Description System

`_update_equipment_description()` (`equipment.py:524-573`) already:
1. Takes `base_description` (static text) + current equipment
2. Calls LLM with prompt
3. Stores result in `player.description`

**What it DOESN'T do:**
- Include dynamic body state (arousal, nipple hardness, flush)
- Include item descriptions (only item names)
- Update description on state changes

### Fix: Description Enrichment

**Step 1:** Add dynamic state to prompt:
```python
def _get_body_state_description(self, player):
    """Generate body state text from conditions and body_state."""
    lines = []
    
    # Check conditions
    if player.has_condition("nipple_hard"):
        lines.append("- Nipples: hard")
    if player.has_condition("aroused"):
        lines.append("- Arousal level: high, flushed skin")
    if player.has_condition("blushing"):
        lines.append("- Cheeks: flushed red")
    if player.has_condition("wetness"):
        lines.append("- Genitals: visibly aroused")
    
    # Check body_state numeric values
    if player.body_state["cheeks"]["flush"] > 0.5:
        lines.append("- Face: deeply flushed")
    
    return "\n".join(lines)
```

**Step 2:** Include item descriptions:
```python
def _get_enriched_equipment_text(self, player):
    """Get equipment text WITH item descriptions."""
    full = self.get_full_equipment(player.name)
    equip_lines = []
    for slot, items in full.items():
        if items:
            item_details = []
            for item_name in items:
                node = self.graph.get_node_by_name(item_name)
                if node:
                    desc = node.properties.get("description", "")
                    opacity = node.properties.get("opacity", 0.8)
                    coverage = node.properties.get("coverage", 0.8)
                    item_details.append(f"{item_name}: {desc} (opacity: {opacity}, coverage: {coverage})")
            equip_lines.append(f"- {slot}: {' over '.join(item_details)}")
    return "\n".join(equip_lines)
```

**Step 3:** Enhanced prompt:
```python
prompt = (
    "You are writing a visual appearance description for a character in a fantasy RPG.\n\n"
    f"BASELINE APPEARANCE (naked physical traits):\n{base}\n\n"
    f"CURRENT EQUIPMENT:\n{equip_text}\n\n"
    f"BODY STATE:\n{body_state_text}\n\n"
    "Write a vivid, natural 3rd-person description of how this character looks right now. "
    "Merge their baseline physical traits with what they're wearing AND their current physical state. "
    "Describe only visible appearance — no backstory, no personality. "
    "Be accurate about what's visible through clothing layers."
)
```

**Step 4:** Trigger regeneration on state changes:
```python
def _update_state_description(self, player):
    """Update description when body state changes."""
    if self.world.auto_generate_descriptions:
        self._update_equipment_description(player)
```

### Description Caching (Future Optimization)

Cache generated descriptions per state hash:
```python
def _get_state_hash(self, player):
    """Generate hash of current body state + equipment."""
    import hashlib
    import json
    
    state = {
        "equipment": self.get_full_equipment(player.name),
        "conditions": list(player.conditions.keys()),
        "body_state": player.body_state
    }
    return hashlib.md5(json.dumps(state, sort_keys=True).encode()).hexdigest()

# In _update_equipment_description():
state_hash = self._get_state_hash(player)
if state_hash in player.description_cache:
    player.description = player.description_cache[state_hash]
    return
# ... generate new description ...
player.description_cache[state_hash] = player.description
```

---

## 10. Implementation Priority

### Phase 1: Foundation (Minor Changes)
1. Add `body_state` dict to Player class
2. Add new vitals (Arousal, Stimulation, Pleasure) to `player.vitals`
3. Add decay rates for new vitals to `player.decay_rates`
4. Add release threshold logic to `tick_turn()`
5. Add arousal trickle from clothing friction to `tick_turn()`

### Phase 2: Conditions (Minor Changes)
1. Add condition definitions to `player.py`: `warming_up`, `aroused`, `highly_aroused`, `frantic`, `overstimulated`, `satisfied`, `nipple_hard`, `blushing`, `wetness`, `sensitized`
2. Add condition logic in `tick_turn()`: check arousal thresholds → apply/remove conditions
3. Add condition → vital feedback loops (conditions affect vitals)

### Phase 3: Description (Minor Changes)
1. Enrich `_update_equipment_description()` prompt with item descriptions
2. Enrich prompt with body state data from conditions
3. Add `_update_equipment_description()` calls on state changes

### Phase 4: Actions (Minor Changes)
1. Add `type: interact` vs `type: attack` to action schema
2. Add intimacy verbs to command parser
3. Add `where` parameter to action schema
4. Implement `_resolve_body_part()` to check accessibility via paperdoll
5. Add action → body part → multiplier pipeline

### Phase 5: Traits (Minor Changes)
1. Add trait definitions to `engine/traits.py`
2. Implement trait multiplier application in action handler
3. Add trait condition triggers

### Phase 6: NPC Perception (Medium)
1. Add perception stat to NPCs
2. Add traits: `observant`, `perverted`, `oblivious`
3. Implement perception difficulty calculation
4. Implement NPC reaction framework

### Phase 7: Environmental Effects (Medium)
1. Add weather/wetness tracking
2. Add wet clothing → transparency logic
3. Add environmental condition triggers

---

## 11. Key Notes & Corrections

### What's Already Working

| System | Status | Location |
|---|---|---|
| Paperdoll with layered slots | ✅ Exists | `paperdoll-view.js`, `equipment.py` |
| Stack order tracking | ✅ Exists | `player.equipped[slot]` ordered list |
| Vital threshold triggers | ✅ Exists | `tick_turn()` in `tick_manager.py` |
| LLM description generation | ✅ Exists | `_update_equipment_description()` |
| Trait system | ✅ Exists | `engine/traits.py` |
| Grapple as contact framework | ✅ Exists | `engine/grapple.py` |
| Relationship tracking | ✅ Exists | `player.relationships` |
| Environment/lighting | ✅ Exists | `area_node.properties.environment` |
| Multi-instance conditions | ✅ Exists | `player.conditions` with condition system |
| Condition periodics | ✅ Exists | `conditions.process_tick()` |
| Condition symptoms/perception | ✅ Exists | `conditions.symptom_for()` |

### What Needs Adding

| Feature | Difficulty | Approach |
|---|---|---|
| Body part data structure | Minor | `body_state` dict + conditions |
| New vitals (Arousal/Stim/Pleasure) | Minor | Add keys to `player.vitals` |
| Clothing friction → arousal | Minor | Per-tick sum in `tick_turn()` |
| Release event cascade | Minor | New `if` block + condition application |
| Intimacy verbs in parser | Minor | Add to `routes/action.py` |
| `type: interact` distinction | Minor | Schema change + check in `combat.py` |
| `where` parameter for targeting | Minor | Add to action schema + resolver |
| Rich description prompt | Minor | Include item descriptions + conditions |
| Involuntary behaviors as conditions | Minor | New condition definitions + triggers |
| Condition threshold triggers | Minor | More `if` blocks in `tick_turn()` |
| Trait multipliers | Minor | 20-line multiplier function in action handler |
| Mood/sanity modifiers | Minor | Use existing vitals + conditions |
| Overstimulation edging curves | Minor | Non-linear decay math in `tick_turn()` |
| **Mechanical NPC perception** | **Medium** | New perception stat + calculation |
| **NPC social reaction framework** | **Medium** | New behavior system extension |

---

## 12. Summary

**The key insight:** The condition system already handles everything we need — multi-instance state tracking, duration-based fading, periodic effects, perception via symptoms, exclusivity, and hierarchy. We just need to:

1. **Add new condition definitions** (`aroused`, `nipple_hard`, `overstimulated`, etc.)
2. **Add new vitals** (`Arousal`, `Stimulation`, `Pleasure`)
3. **Add threshold checks** to `tick_turn()` to apply/remove conditions based on vitals
4. **Enrich the description prompt** with condition data and item descriptions
5. **Add action → body part → multiplier** pipeline using existing trait system

**The paperdoll already tracks layering.** We just need to feed that data to the LLM properly so it can reason about visibility through layers.

**Per-source multipliers are trivial** because the action already knows the body part. Just multiply based on traits + body part.

**Everything is incremental on existing infrastructure.** No new architecture needed.



additions:
Great questions! Let me unpack each point so we’re on the same page, then I’ll show how to fold everything back into the design.

---

## 1. What I meant by “per‑verb mechanical properties”

The original V1 explicitly assigned **base numbers** to each intimacy verb, like:

| Verb | Pressure | Pleasure mult | Pain potential | Stim type |
|------|----------|---------------|----------------|-----------|
| Caress | Light (0.3) | 1.5 | 0.1 | Sustained |
| Pinch | Firm (0.8) | 1.2 | 0.6 | Spike |
| Kiss | Light (0.2) | 1.8 | 0.0 | Rhythmic |
| Bite | Firm (0.9) | 0.8 | 0.9 | Spike |

V2 listed the same verbs and added an `intensity` field, but **didn’t pre‑define base values** – it’s silent on whether a “gentle kiss” has a multiplier of 1.8 or 0.5. Without those defaults the action system can’t calculate how much stimulation a verb generates *before* intensity modifiers.

**To bring that back**, we’ll add a small constants table to the stimulation action handler. I’ll show exactly where later.

---

## 2. Single‑Track as a trait (not a base mechanic)

Agreed – if it appears, it’s purely a trait. V2 omitted it, but we can reinstate it exactly as a trait that gates release. I’ll add its definition back in.

---

## 3. Non‑erotic involuntary body responses (goosebumps, shivers, cough, sneeze, hiccup, itch)

You want **all** involuntary body things, whether sexual or not. We can call them **Body Reactions** (conditions with triggers in `tick_turn()`). I’ll include a list of the classic ones and note they can be expanded.

---

## 4. Sex Addict trait: high entertainment decay when arousal is low

This is a great detail – it gives a direct gameplay hook. We’ll build it into a trait’s `periodic` or `decay_modifiers` so that low arousal causes the character to get bored faster, nudging them to seek stimulation.

---

## 5. Keep the “any legal kink or fetish” wording

I’ll add a small “Design Philosophy” note that the system is built to accommodate any legal kink or fetish via trait/multiplier customization.

---

## 6. Configuration toggle for mature content

Absolutely necessary. We’ll add a global `ENABLE_MATURE_CONTENT` flag (default `False`) that:
- Completely disables arousal/stimulation/pleasure vitals and their tick effects
- Hides erogenous zone sensitivity, intimacy verbs, and adult traits
- Prevents NPC perception/reaction to sexual states
- Leaves the framework inactive unless the player opts in

This can live in a `config.toml` or a game settings flag and be checked everywhere.

---

# Updated Design v3.1 – What gets added back

I’ll now list the concrete additions to V2, so you have everything in one place.

### ✅ Verb‑base‑multiplier table

Add to the stimulation action handler (a new file `engine/pleasure_actions.py` or inline):

```python
VERB_BASE = {
    "caress":  {"pressure": 0.3, "pleasure_mult": 1.5, "pain_potential": 0.1, "stim_type": "sustained"},
    "pinch":   {"pressure": 0.8, "pleasure_mult": 1.2, "pain_potential": 0.6, "stim_type": "spike"},
    "kiss":    {"pressure": 0.2, "pleasure_mult": 1.8, "pain_potential": 0.0, "stim_type": "rhythmic"},
    "lick":    {"pressure": 0.2, "pleasure_mult": 1.7, "pain_potential": 0.0, "stim_type": "sustained"},
    "suck":    {"pressure": 0.5, "pleasure_mult": 2.0, "pain_potential": 0.2, "stim_type": "rhythmic"},
    "bite":    {"pressure": 0.9, "pleasure_mult": 0.8, "pain_potential": 0.9, "stim_type": "spike"},
    "blow":    {"pressure": 0.1, "pleasure_mult": 0.5, "pain_potential": 0.0, "stim_type": "sustained"},
    "tickle":  {"pressure": 0.2, "pleasure_mult": 0.7, "pain_potential": 0.0, "stim_type": "spike"},
    # ... etc.
}
```

These get multiplied by the `intensity` modifier (light/normal/firm) and then run through body‑part and trait multipliers. The `pain_potential` can flip to negative pleasure if it exceeds comfort.

---

### ✅ Single‑Track trait

```python
"single_track": {
    "name": "Single-Track",
    "description": "You can only reach release through one type of stimulation.",
    "blocked_release": True,  # flag checked in release logic
    "allowed_path": None,      # set dynamically (e.g., "nipple", "oral")
    "multipliers": {
        "other_paths": 0.05    # all other stimulation types give only 5% effect
    },
},
```

The release check will skip the event unless the character’s `allowed_path` matches the current action’s body part category.

---

### ✅ Body Reactions (goosebumps, shivers, cough, sneeze, hiccup, itch)

Add them as simple conditions with triggers:

```python
"goosebumps": {
    "name": "Goosebumps",
    "description": "Your skin is covered in goosebumps.",
    "symptoms": { None: "You have goosebumps." },
    "periodic": {},
    "known": True,
    "triggers": ["temperature_drop", "fear", "random"]
},
"shiver": {
    "name": "Shivering",
    "symptoms": { None: "You're shivering." },
    "periodic": {"Temperature": -0.5},
    "known": True,
    "triggers": ["cold", "wet"]
},
"cough": { ... },
"sneeze": { ... },
"hiccup": { ... },
"itch": {
    "name": "Itch",
    "body_part": "varies",
    "periodic": {"Entertainment": -1},
    "symptoms": { None: "You have an annoying itch." },
    "known": False,
    "triggers": ["random", "insect_bite", "allergy"]
},
```

These get added/removed by `tick_turn()` based on vitals/environment just like the erotic ones, but they’re always active (no mature toggle needed for these).

---

### ✅ Sex Addict trait with boredom decay

```python
"sex_addict": {
    "name": "Sex Addict",
    "description": "You crave sexual stimulation; boredom hits hard when unaroused.",
    "decay_modifiers": {
        "Entertainment": lambda vitals: 2.0 if vitals.get("Arousal", 0) < 15 else 1.0
    },
    "condition_triggers": {
        "low_arousal": "bored"  # adds bored condition when arousal < 15
    },
},
```

In `tick_turn()`, if the player has this trait, the Entertainment decay rate is doubled while arousal is below 15. Additionally, the `bored` condition can further penalize sanity or mood.

---

### ✅ Design philosophy note (legal kinks)

Add a comment in the trait/multiplier section:

> *The multiplier system is intentionally open‑ended. By defining body‑part categories, fetish traits, and custom sensitivity multipliers, the framework can accommodate virtually any legal kink or fetish without hard‑coding them. The design avoids explicit judgment of specific preferences, focusing instead on a numeric, consent‑aware layer that modders and content creators can configure.*

---

### ✅ Mature content toggle

Add to `config.toml` or `settings.py`:

```toml
[game]
mature_content = false   # set to true to enable arousal, stimulation, pleasure, and adult interactions
```

Then, in every place the erotic system touches:

```python
if not config.mature_content:
    return  # skip arousal ticks, hide sensitive body parts, prevent intimacy actions
```

Specifically:
- `tick_turn()`: skip arousal/stimulation/pleasure decay and threshold checks.
- `routes/action.py`: disable intimacy verbs entirely.
- `conditions.py`: never apply `aroused`, `nipple_hard`, `wetness`, etc.
- NPC perception: ignore sexual states.
- Character creation: adult traits are hidden or greyed out.

This ensures the base game is a standard survival RPG, with mature themes as a deliberate opt‑in.

---

## Summary of changes to V2 to incorporate all of the above

1. **Add verb base stats table** → used in action resolution
2. **Add `single_track` trait** to trait definitions
3. **Add body reactions** (goosebumps, cough, etc.) as conditions with environmental/vital triggers
4. **Add `sex_addict` trait** with Entertainment decay scaling on low arousal
5. **Include design philosophy note** about legal kinks
6. **Implement `mature_content` toggle** – gate everything behind it

