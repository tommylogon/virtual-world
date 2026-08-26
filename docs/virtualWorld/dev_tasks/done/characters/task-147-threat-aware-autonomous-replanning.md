---
group: Agent AI & Behavior
wiki: "[[Characters/NPC Behavior System]]"
---
# Threat-Aware Autonomous Replanning

**Filed**: 2026-07-30
**Priority**: High
**Status**: Complete — all 7 changes done

---

## Summary

## Summary

NPCs ignore active lethal threats in their room. When The Butcher (a killer with a cleaver) enters the Foyer, teenagers keep executing stale plans like `examine coat_rack` instead of fleeing, hiding, or fighting. This is the threat-side counterpart to task-92 (vitals-driven replanning).

Three root causes:
1. **No replan trigger for threats** — Plans are followed for up to 10 turns. A soft prompt line ("if a threat appeared, ignore the plan") fails because the LLM treats standing threats differently from changes.
2. **No code-level threat injection in the DECIDE prompt** — The prompt says "Your plan guides you" without awareness of the killer in the room.
3. **Ambiguous emote wording in memory** — Emotes like "slides into the sewer passage" describe departure, causing other NPCs to believe the threat has left.

---

## Related

- **task-92**: Needs-driven replanning (vitals). Same mechanism, different trigger.
- **`.kilo/plans/1785445107697-threat-aware-replanning.md`**: Full implementation plan with code blocks.

---

## Prerequisite: `hostile` trait (DONE)

A new `hostile` trait was added as the threat marker, separate from the existing `is_slasher`/`slasher` traits which control undead/slasher mechanics (no vital decay, slasher hunt AI, dark vision, special combat).

**Backend:**
- `engine/traits.py` — Added `HOSTILE = "hostile"` constant and `"hostile"` trait definition
- `data/scenarios/mansion.json` — Added `"hostile": true` to The Butcher's traits

**Design decisions:**
- `hostile` is purely for AI threat detection — no gameplay side effects
- `is_slasher` remains for undead mechanics (no vital decay, slasher hunt, etc.)
- A character can have both, either, or neither
- Threat detection logic checks `traits.hostile` first, then directional relationships, then recent attack events
- Hidden/stealthed characters are skipped regardless of traits

---

## Changes

### 1. Add `_getThreatAlert()` to AgentEngine (`agent-engine.js`) ✅ DONE

Scans `state.players_in_area` and checks for each other player:
- **Hidden/stealthed** — skip (assassin not yet revealed)
- **`traits.hostile`** — immediate threat
- **Directional relationship** — `other.relationships[charName].closeness < -20`
- **Recent attack** — `turn_events` where `actor === otherName && action === 'attack'`

Returns a prepend string: `"⚠️ IMMEDIATE DANGER: {names}..."` or `null`.

### 2. Add `_shouldReplan()` to AgentEngine ✅ DONE

Unified replan triggger — checks threats, critical vitals, and stale plan (10-turn cycle):

### 3. Wire into `step()` before DECIDE phase ✅ DONE

Insert replan check **after** observation resolves, **before** decision prompt is built. Removed the old end-of-turn plan generation block (now handled by `_shouldReplan`).

Prepends `threatAlert` to the DECIDE prompt if present.

### 4. Add threat detection to PlanManager.generate() ✅ DONE

Adds threat scan before the plan prompt. Injects threat warning into the prompt if hostile actors are detected.

### 5. Update prompt-builder.js ✅ DONE (external prepend)

Threat alert is prepended externally in `agent-engine.js` rather than passed as a parameter. Cleaner separation: the prompt builders remain pure, the threat alert is injected as a system-level override above the prompt.

### 6. Fix emote memory storage ✅ DONE

When storing emotes from movement actions (`go ...`), prefixes with `"arrives: "` so other characters read it as arrival, not departure.

### 7. Auto-decrement relationships on attack (backend, `engine/combat.py`) ✅ DONE

When character A attacks character B, drops `B.relationships[A].closeness` by 30 points (capped at -100). Also increments `interaction_count` and sets `last_interaction_tick`. Fixed a separate bug where the method was named `_player_attack` but called as `player_attack` — renamed to `player_attack` to match.

---

## Sequence Flow

```
Agent's turn starts
    ↓
Fetch state, build context
    ↓
Check: _shouldReplan()?
    ├── No → continue with current plan
    └── Yes → call PlanManager.generate()
                ↓
         New plan replaces _plans[charName]
                ↓
    ↓
Build DECIDE prompt with threatAlert prepended
    ↓
LLM decides action
    ↓
Execute action, store emote with arrival prefix if movement
    ↓
REACT phase (unchanged)
```

---

## Test

1. Hard reload, load mansion scenario
2. Start agent mode, advance until The Butcher enters the Foyer
3. Verify: Kyrie replans, action is survival (flee/hide/fight/warn) NOT examine
4. Verify: Sammy also reacts to threat, NOT examine rug
5. Test edge cases:
   - Set a character to `hidden` state — verify undetected
   - Trigger attack event — verify target replans
   - Friendly NPC with high relationship — verify no false positive
