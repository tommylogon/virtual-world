# Human Turn Controller (HTC) UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Human Turn Composer (`static/js/agent/human-turn-composer.ts`) - 745 lines
- Turn Scene View (`static/js/agent/turn-scene-view.ts`) - 520 lines
- Turn Feed (`static/js/agent/turn-feed.ts`) - 380 lines
- Turn Queue (`static/js/agent/turn-queue.ts`) - 410 lines
**Rendering Tech:** Lit-html mounted into `#htc-modal` inside `#htc-overlay`.

---

## 1. Measured Ground Truth & Architecture

The HTC controls the active turn loop for human-controlled characters.

### Action Budget Model
- Continuous multi-action model (task-352):
  - **Major Action:** ◆ (1 slot) - Attack, Dash, Cast Spell, Complex Interact.
  - **Minor Action:** ◇ (1 slot) - Equip, Draw Weapon, Drink Potion, Open Door.
  - **Free Action:** ●●● (3 slots) - Drop item, Speak, Emote, Glance.
- When an action is submitted via `_submitAction()`, it sends `POST /api/player/command` or `ApiClient.applyTurn()`.
- The result appends to `.htc-feed` without closing the modal.

### Inventory of Controls
- **Header:** Actor portrait, character name, active tick sequence, "up next" queue preview.
- **Scene View (`turn-scene-view.ts`):** Clickable entity chips (Characters present, Items on the floor, Exits/Doors).
- **Feed (`turn-feed.ts`):** Chronological log of recent actions, combat rolls, system messages, and environmental reactions.
- **Composer (`human-turn-composer.ts`):**
  - Typed input box (`#htc-do`) with verb parser (lines 149-160).
  - Speech input (`#htc-say`) with volume selector (`whisper`, `say`, `shout`, `scream`).
  - Emote palette button (`#htc-emote-btn`).
  - Action button (`[Act]`) and End Turn button (`[⏭ End Turn]`).

---

## 2. Usability & Layout Critique

### A. The "Ghost Modal" Phenomenon (bug-613)
- When the turn ends, `#htc-overlay` is set to `display: none`, but its child `#htc-modal` remains in the DOM with stale `innerText` and event handlers attached.
- In automated testing or fast clicks, keypresses intended for the main canvas are swallowed by invisible input fields inside the hidden modal.

### B. Natural Language vs Strict Verbs Cognitive Dissonance
- The composer advertises a natural language text box (`#htc-do`), but internally it relies on a hardcoded array of 58 verbs (line 149).
- If a user types *"walk over to the counter and inspect the mug"*, the parser fails to match and treats the entire sentence as speech (`_volume: say`), causing the character to literally blurt out the command in spoken dialogue.
- Users are left baffled why their character is speaking their intentions instead of moving.

### C. Scene Chips vs Free-Look Information Asymmetry
- `turn-scene-view.ts` renders items and actors in the room as small text chips.
- Hovering an item displays *"hover = free look · click = what you can do with it"*.
- However, clicking a chip immediately populates the text field with a default command (e.g. clicking a sword types `take sword`), bypassing the verb menu unless the user right-clicks or knows the hidden key combinations.

### D. Budget Pips Obscurity
- The budget is shown as abstract geometric icons: `◆ major ◇ minor ●●● free`.
- When an action fails on the server (e.g. out of stamina or invalid target), the pip flips to `spent` temporarily, flashes red, and then restores. There is no inline explanation of *why* an action costs a major vs minor slot before committing.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: The Tactical Turn Console

```
+----------------------------------------------------------------------------------------------------+
| ✈ THORNE'S TURN  ·  Round 4, Tick 142               Queue: [YOU] -> Goblin Scout -> Brother Peter  |
+----------------------------------------------------+-----------------------------------------------+
| CURRENT SCENE: Tavern Taproom                      | TURN LOG & FEED                               |
| Location: [Eldenford Tavern (Interior)]            |                                               |
|                                                    | 14:02: Thorne strikes Goblin with Longsword!  |
| CHARACTERS HERE:                                   |        Hit! (d20: 17 + 3 = 20 vs AC 14)       |
| [ Thorne (You) ] [ Bartender Jerry ] [ Goblin (Hostile) ] | Damage: 8 Slashing damage.            |
|                                                    | 14:01: Goblin misses Thorne (d20: 8 vs AC 16) |
| OBJECTS & FIXTURES:                                | 14:00: You entered through Oak Door.          |
| [ Heavy Oak Bar ] [ Clay Jug ] [ Iron Candlestick ]|                                               |
|                                                    |                                               |
| EXITS:                                             |                                               |
| [ North: Kitchen ] [ East: Street ] [ Down: Cellar ]                                               |
+----------------------------------------------------+-----------------------------------------------+
| ACTION COMPOSER                                                                                    |
| Budget: [ ◆ Major: 1 ]  [ ◇ Minor: 1 ]  [ ● Free: 3 ]                                              |
|                                                                                                    |
| Action:  [ Attack Goblin with Longsword                          | ▾ Verbs ]  Cost: ◆ Major        |
| Spoken:  [ "Stand down or be cut down!"                          | Say ▾ ]    Target: Goblin       |
| Emote:   [ eyes narrowing with fierce determination             ]                                  |
|                                                                                                    |
| [  COMMIT ACTION (Enter)  ]                          [  END TURN (Space)  ]                        |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Intelligent Command Suggestion / Autocomplete**
   - Replace the blind text field with a dual-mode input:
     - Type to autocomplete real scene entities and supported verbs (`look`, `attack`, `take`, `go`).
     - Plain english hints when an unrecognized verb is about to be converted to spoken dialogue.

2. **Pre-flight Action Cost Estimation**
   - As soon as the user selects a verb and target, visually highlight which pip will be spent (`◆ Major` lights up for attack, `◇ Minor` lights up for drink potion).

3. **True Modal Teardown**
   - When closing the HTC modal, completely unbind listeners and purge `#htc-modal` from the active DOM to prevent ghost input capture.
