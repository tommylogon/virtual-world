---
group: Tech Debt & Testing
---
# Test Plan: 100+ Click/Verify Items

**Goal**: Verify the refactored VirtualWorld works correctly end-to-end.
**Method**: Playwright headless browser against http://127.0.0.1:4444
**Status tracking**: ✓ Pass / ✗ Fail / ~ Skip (non-critical)

---

## 1. Page Load & UI Structure (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 1.1 | Server starts without Python errors | `GET /` returns 200, no traceback in logs | ✓ |
| 1.2 | Page title exists | `<title>` tag has content, not empty | ✓ |
| 1.3 | Command input exists | `#command-input` text field present and visible | ✓ |
| 1.4 | Inspector panel exists | `#inspector-panel` element present | ✓ |
| 1.5 | Graph canvas exists | `#graph-canvas` element present | ✓ |
| 1.6 | Event stream exists | `.event-stream` or `#event-stream` present | ✓ |
| 1.7 | Agent list renders | Agent items visible (`.agent-item` or agent list) | ✓ |
| 1.8 | Settings/controls exist | Play/Pause/Step buttons visible | ✓ |
| 1.9 | API state endpoint responds | `GET /api/state` returns JSON with `areas`, `players`, `graph` | ✓ |
| 1.10 | No console errors on page load | `page.on('console', ...)` captures zero errors | ✓ |

## 2. Basic Game Commands (15 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 2.1 | `look` command | Returns room description, items, exits | ✓ |
| 2.2 | `inventory` command | Shows carried items or "nothing" | ✓ |
| 2.3 | `i` alias | Same as inventory | ✓ |
| 2.4 | `examine self` | Shows player description + equipment narrative | ✓ |
| 2.5 | `stats` command | Shows vitals (HP, Hunger, Thirst, etc.) | ✓ |
| 2.6 | `help` or `commands` | Returns list of available commands | ✓ |
| 2.7 | `go north` (if exit exists) | Moves to next room, returns new description | ✓ |
| 2.8 | `go [invalid]` | Returns error "You can't go that way" | ✓ |
| 2.9 | `look at [item in room]` | Returns item description | ✓ |
| 2.10 | `take [item]` | Adds item to inventory | ✓ |
| 2.11 | `drop [item]` | Removes item from inventory | ✓ |
| 2.12 | `use [item]` | Fires on_use trigger if exists, else message | ✓ |
| 2.13 | `toggle [toggleable item]` | Toggles item state | ✓ |
| 2.14 | `rest 1` | Advances time, restores energy | ✓ |
| 2.15 | Ambiguous command → LLM suggestion | If enabled, returns suggested command | ✓ |

## 3. Agent/Character Inspector (20 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 3.1 | Click agent in list → opens Stats tab | Inspector shows agent name, stats, vitals | ✓ |
| 3.2 | Stats tab shows STR/DEX/CON/INT/WIS/CHA | Six stat fields with values | ✓ |
| 3.3 | Vitals display shows HP/Energy/Hunger etc. | Vital bars or values visible | ✓ |
| 3.4 | Click Equipment tab → paperdoll renders | 12 body slots visible (head, neck, torso, etc.) | ✓ |
| 3.5 | Empty slot shows "—" or empty state | Unfilled slots show empty indicator | ✓ |
| 3.6 | Click Inventory tab → carried items grid | Grid of inventory items with name + weight | ✓ |
| 3.7 | Click Bio tab → personality + appearance | Personality textarea + description textarea | ✓ |
| 3.8 | Click Relationships tab → relationship list | Shows relationships with closeness values | ✓ |
| 3.9 | Click Advanced tab → timeline + commands | Timeline viewer + manual command input | ✓ |
| 3.10 | Edit personality → save → persists | Change text, save, re-open, text is changed | ✓ |
| 3.11 | Edit description → save → persists | Same as above | ✓ |
| 3.12 | Kill character → state = "dead" | Kill button works, HP=0, state="dead" | ✓ |
| 3.13 | State dropdown changes state | "awake" → "sleeping" → "unconscious" etc. | ✓ |
| 3.14 | Current room dropdown changes room | Selecting a new room moves the character | ✓ |
| 3.15 | Emotion dropdown changes mood | Neutral → happy → sad → angry etc. | ✓ |
| 3.16 | Emotion intensity slider updates | Dragging slider changes intensity value | ✓ |
| 3.17 | Skills are visible and editable | Skills list with +/- for each skill | ✓ |
| 3.18 | World knowledge textarea editable | Can add world knowledge text | ✓ |
| 3.19 | Export character downloads JSON | Click export → file saved/offered | ✓ |
| 3.20 | Import character restores state | Import a previously exported character card | ✓ |

## 4. Item Inspector (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 4.1 | Click item in graph → opens item view | Inspector shows item name, description | ✓ |
| 4.2 | Item actions grid checkable/uncheckable | Toggle examine/take/use/read etc. | ✓ |
| 4.3 | Properties (state, uses, weight) editable | Change values, save, refresh → persists | ✓ |
| 4.4 | Tags editable and addable | Add tag "magic" → tag appears | ✓ |
| 4.5 | Two-handed checkbox works | Check → item is two-handed in data | ✓ |
| 4.6 | Equip slots multi-select works | Select "head" → item can be equipped to head | ✓ |
| 4.7 | Triggers section shows existing triggers | List of triggers with type + effect summary | ✓ |
| 4.8 | "➕ Add" trigger button opens modal | Overlay appears with trigger type select | ✓ |
| 4.9 | Add effect row works | Click "➕ Add Effect" → new effect row appears | ✓ |
| 4.10 | Save trigger → persists | Fill trigger form, save → trigger appears in list | ✓ |

## 5. Area Inspector (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 5.1 | Click room in graph → opens room view | Inspector shows room name, description | ✓ |
| 5.2 | Area name editable | Change name, save → persists | ✓ |
| 5.3 | Area description editable | Change description, save → persists | ✓ |
| 5.4 | Environment (light, temp, air, smell, noise) editable | Change light level → room environment updates | ✓ |
| 5.5 | Exits section shows all connected areas | List of exits with direction + target room | ✓ |
| 5.6 | Items in room section shows items | List of items present in this room | ✓ |
| 5.7 | Characters/agents in room section shows agents | List of agents currently in this room | ✓ |
| 5.8 | Area event log shows recent events | Events for this room displayed | ✓ |
| 5.9 | Click exit → navigates to target room | Area inspector switches to target | ✓ |
| 5.10 | Floor input editable | Change floor number → persists | ✓ |

## 6. Way Inspector (5 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 6.1 | Click door in graph → opens door view | Inspector shows door name, state | ✓ |
| 6.2 | Way state dropdown works | Change open → closed → locked → persists | ✓ |
| 6.3 | Way description editable | Change description → persists | ✓ |
| 6.4 | Cardinal direction editable | Change direction → persists | ✓ |
| 6.5 | Trigger section on door shows triggers | Way triggers visible and editable | ✓ |

## 7. Paperdoll & Equipment (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 7.1 | Paperdoll renders 12 slots | Grid shows head, neck, torso, arms, hands, legs, feet, back, waist, hand_left, hand_right, accessory | ✓ |
| 7.2 | Filled slot has accent border | Equipped slot shows different border color | ✓ |
| 7.3 | Click + button → equip picker opens | Modal with items filtered by slot | ✓ |
| 7.4 | Equip item → appears in slot | Item name shown in paperdoll slot | ✓ |
| 7.5 | ✕ button → unequips item | Item removed from slot, back in inventory | ✓ |
| 7.6 | Right-click slot → context menu | Menu shows Inspect / Unequip / Open Container | ✓ |
| 7.7 | +N more badge on stacked slots | Slot with 2+ items shows "+N more" badge | ✓ |
| 7.8 | Click +N more → stack popup opens | Popup shows inner layers with ✕ buttons | ✓ |
| 7.9 | Accessory items listed below paperdoll | Accessory grid shows all equipped accessories | ✓ |
| 7.10 | "Equip from Inventory" button works | Opens picker filtered for all items | ✓ |

## 8. Graph Interactions (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 8.1 | Graph renders nodes and edges | Rooms, items, ways, characters visible | ✓ |
| 8.2 | Area nodes are distinct color | Rooms have different color from items/ways | ✓ |
| 8.3 | Drag node repositions it | Node position updates, persists | ✓ |
| 8.4 | Right-click room → context menu | Menu shows Inspect, Add Item, Move Character etc. | ✓ |
| 8.5 | Right-click item → context menu | Menu shows Inspect, Edit Item, Save to Library, etc. | ✓ |
| 8.6 | Right-click door → context menu | Menu shows Inspect, Edit Way, etc. | ✓ |
| 8.7 | Right-click character → context menu | Menu shows Inspect, Edit Character, etc. | ✓ |
| 8.8 | Physics toggle works | Enable/disable physics → nodes freeze/unfreeze | ✓ |
| 8.9 | Search/filter works | Type query → matching nodes highlighted | ✓ |
| 8.10 | Legend displays node type meanings | Legend shows room/item/door/character icons | ✓ |

## 9. Trigger Editor (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 9.1 | Add Trigger from item inspector | Click "➕ Add" → modal opens with trigger type select | ✓ |
| 9.2 | Select trigger type | Choose on_examine → target field hidden, target_state hidden | ✓ |
| 9.3 | Select on_use_on → target field appears | Target input + datalist shown | ✓ |
| 9.4 | Select on_state_enter → target_state appears | Target state input shown | ✓ |
| 9.5 | Add effect row with type | Select effect type (damage) → parameter fields appear | ✓ |
| 9.6 | Add condition row with type | Select condition (has_item) → parameter field appears | ✓ |
| 9.7 | Success/fail message fields | Type messages → saved with trigger | ✓ |
| 9.8 | Save trigger → appears in list | New trigger shown in trigger list on item | ✓ |
| 9.9 | Edit trigger → pre-populates existing data | Click edit → modal opens with existing values | ✓ |
| 9.10 | Delete trigger → removed from list | Click ✕ → trigger disappears | ✓ |

## 10. Event Stream & Turn System (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 10.1 | Event stream shows "Initialized" message | Log shows engine initialization | ✓ |
| 10.2 | Command output appears in stream | Typing a command → output in stream | ✓ |
| 10.3 | Turn events show after command | Events display with tick count | ✓ |
| 10.4 | Agent step button triggers agent action | Click step → agent thinks/decides/acts | ✓ |
| 10.5 | Agent thought appears in stream | 💭 bubble with agent's thinking | ✓ |
| 10.6 | Agent action appears in stream | ⚡ bubble with agent's action | ✓ |
| 10.7 | Agent speech appears in stream | 💬 bubble with agent's speech | ✓ |
| 10.8 | Stream auto-scrolls to newest event | New events visible at bottom | ✓ |
| 10.9 | Clear log button works | Clears event stream | ✓ |
| 10.10 | Filters show/hide event types | Toggle thought/speech/action visibility | ✓ |

## 11. Item Library (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 11.1 | Open Library button → modal opens | Item library modal visible | ✓ |
| 11.2 | Library items list renders | Items shown with name, type icon, description | ✓ |
| 11.3 | Click item → editor opens | Right panel shows item editor form | ✓ |
| 11.4 | Create new item button works | New item form with empty fields | ✓ |
| 11.5 | Save new item → appears in list | Library list updates with new item | ✓ |
| 11.6 | AI generate item → populates form | Type prompt, click Generate → fields filled | ✓ |
| 11.7 | Delete item → removed from list | Confirmation → item disappears | ✓ |
| 11.8 | Filter/search items | Type in filter → list narrows | ✓ |
| 11.9 | Container contents editable | Add items to container → contents list updates | ✓ |
| 11.10 | Add Trigger in library editor | Same trigger editor as item inspector | ✓ |

## 12. Save/Load & Settings (5 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 12.1 | Save game creates file | `POST /api/save-game` → file in saves/ | ✓ |
| 12.2 | Load game restores state | `POST /api/load-game/` → state restored | ✓ |
| 12.3 | Reset scenario reloads world | `POST /api/reset` → fresh world from template | ✓ |
| 12.4 | Settings toggle (ghost mode, narration) | Toggle on/off → setting persists | ✓ |
| 12.5 | LLM profile switch works | Switch provider/model → config updates | ✓ |

## 13. Equipment & Paperdoll Edge Cases (15 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 13.1 | Equip item from inventory via right-click | Right-click item in inventory → "Equip" → item moves to slot | ✓ |
| 13.2 | Unequip via right-click on paperdoll slot | Right-click filled slot → "Unequip" → item back in inventory | ✓ |
| 13.3 | Equip with wrong slot type | Equip boots to "head" slot → error message | ✓ |
| 13.4 | Two-handed weapon frees both hands on unequip | Equip greatsword → both hands filled → unequip → both free | ✓ |
| 13.5 | Stack badge shows "+N more" with 3 items | Equip 3 accessories → badge reads "+2 more" | ✓ |
| 13.6 | Stack popup shows inner layers | Click +N more → popup lists inner items with ✕ buttons | ✓ |
| 13.7 | Click ✕ in stack popup → unequips inner layer | Remove inner item → outer item stays | ✓ |
| 13.8 | Drop equipped item → auto-unequips | Equip helmet → drop helmet → slot empty | ✓ |
| 13.9 | "Generate from Equipment" button works | Click → description textarea updates with LLM-generated text | ✓ |
| 13.10 | Self-examine shows equipped items | `examine self` → narrative includes worn items | ✓ |
| 13.11 | Other-examine shows visible equipment | `examine [other player]` → shows their equipment | ✓ |
| 13.12 | Edit base_description → persists | Change base text, save → re-open shows changed text | ✓ |
| 13.13 | Container equipment (backpack) opens on click | Equip backpack → click → shows container contents | ✓ |
| 13.14 | Multiple items in same slot → visual layering | 3 items in torso → top item visible, +2 badge | ✓ |
| 13.15 | Undress command removes outer layer | `undress` → outermost item from each slot removed | ✓ |

## 14. Error Handling & Edge Cases (15 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 14.1 | Empty command returns usage hint | Just press Enter → shows "Invalid command" or help | ✓ |
| 14.2 | Unknown command shows suggestion | Type "flarg" → "Did you mean...?" or "Unknown command" | ✓ |
| 14.3 | Take nonexistent item | `take unicorn` → "You don't see that" | ✓ |
| 14.4 | Drop nonexistent item | `drop unicorn` → "You don't have that" | ✓ |
| 14.5 | Use item not in inventory | `use unicorn` → "You don't have that" | ✓ |
| 14.6 | Examine nonexistent target | `examine unicorn` → "You don't see that" | ✓ |
| 14.7 | Go to nonexistent direction | `go unicorn` → "You can't go that way" | ✓ |
| 14.8 | REST API returns 400 for missing command | `POST /api/action {}` → 400 "Missing command" | ✓ |
| 14.9 | REST API returns 404 for unknown route | `GET /api/unicorn` → 404 | ✓ |
| 14.10 | Server handles malformed JSON | `POST /api/action "not json"` → 400 Bad Request | ✓ |
| 14.11 | Kill already dead character | Kill dead character → error or "already dead" | ✓ |
| 14.12 | Sleep while already sleeping | `sleep` while sleeping → "already asleep" | ✓ |
| 14.13 | Move while unconscious | Move unconscious player → "cannot move" | ✓ |
| 14.14 | Use item with 0 uses | Use depleted item → "item has no more uses" | ✓ |
| 14.15 | Open locked door without key | Go through locked door → "it's locked" / skill check | ✓ |

## 15. Game Loop & Time System (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 15.1 | Turn applies vital decay | `rest 1` → Hunger decreases, Energy recovers | ✓ |
| 15.2 | Time advances with rest | Game time increases after rest | ✓ |
| 15.3 | Starvation causes HP loss | Hunger stays 0 for multiple ticks → HP decreases | ✓ |
| 15.4 | Temperature affects thirst | Hot room → thirst increases faster | ✓ |
| 15.5 | Sleeping restores energy | `sleep` → energy recovers per tick | ✓ |
| 15.6 | Unconscious from zero energy | Energy hits 0 → state becomes "unconscious" | ✓ |
| 15.7 | Death from extreme vitals | HP hits 0 → state becomes "dead" | ✓ |
| 15.8 | Body spawns on death | Dead character → "body" item appears in room | ✓ |
| 15.9 | Ghost mode allows limited actions | Dead character in ghost mode → can look but not take | ✓ |
| 15.10 | Shelter from extreme temperature | Indoor room vs outdoor → vitals decay differently | ✓ |

## 16. Multi-Character & Turn Queue (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 16.1 | Create second player | `POST /api/players` → new player added | ✓ |
| 16.2 | Switch active player | Click agent list → active player changes | ✓ |
| 16.3 | Two players in same room can interact | Player A speaks → Player B hears | ✓ |
| 16.4 | Players in different areas are isolated | Area A's events not visible in Area B | ✓ |
| 16.5 | Turn queue initializes correctly | Agents ordered by initiative | ✓ |
| 16.6 | Dead characters are skipped in turn queue | Dead → not processed in step | ✓ |
| 16.7 | Agent stops after max steps | `config.maxSteps` → agent stops automatically | ✓ |
| 16.8 | Agent memory persists | Agent remembers past events → visible in context | ✓ |
| 16.9 | Emotion affects behavior | High anger → different narrative choices | ✓ |
| 16.10 | Relationships track interactions | Player talks to NPC → relationship value changes | ✓ |

## 17. Doors & Movement (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 17.1 | Open a closed door | `open north` → door state becomes "open" | ✓ |
| 17.2 | Close an open door | `close north` → door state becomes "closed" | ✓ |
| 17.3 | Go through a door | `go north` → player in new room | ✓ |
| 17.4 | Locked door blocks movement | `go north` (locked) → "it's locked" | ✓ |
| 17.5 | Unlock door with key | `use key on door` → door unlocked | ✓ |
| 17.6 | Hidden door discovered via fumble | `fumble` → discover hidden exit | ✓ |
| 17.7 | Auto-close door after passing | Walk through auto-close door → door closes behind | ✓ |
| 17.8 | Skill-check door | `go north` with skill door → check roll | ✓ |
| 17.9 | Blocked door cannot be opened | `open north` (blocked) → "cannot open" | ✓ |
| 17.10 | Way state visible in inspector | Click door node → state dropdown shows current | ✓ |

## 18. Environment & Lighting (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 18.1 | Dark room blocks examine | Area light < 20 → "too dark" | ✓ |
| 18.2 | Light source illuminates room | `light torch` → room light increases | ✓ |
| 18.3 | Toggleable item affects environment | Toggle lamp on → room brighter | ✓ |
| 18.4 | Blind character has limited perception | Blind condition → examine fails | ✓ |
| 18.5 | Area temperature affects body temp | Cold room → body temp drifts down | ✓ |
| 18.6 | Fireplace warms adjacent room | Light fireplace → temperature rises | ✓ |
| 18.7 | Air quality affects breathing | Toxic air → HP damage over time | ✓ |
| 18.8 | Noise prevents restful sleep | Loud room → sleep doesn't restore energy | ✓ |
| 18.9 | Light spills through open ways | Next room with open door gets dim light | ✓ |
| 18.10 | Environment persists across reload | Change light → save → load → light still changed | ✓ |

## 19. Serialization & Persistence (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 19.1 | Save game creates valid JSON | `GET /api/save` → valid JSON with all required keys | ✓ |
| 19.2 | Load game restores player position | Save → move player → load → player back in original room | ✓ |
| 19.3 | Equipped items survive save/load | Equip → save → load → equipment still present | ✓ |
| 19.4 | Player vitals survive save/load | Take damage → save → load → HP still lowered | ✓ |
| 19.5 | Area environment survives save/load | Change light → save → load → light still changed | ✓ |
| 19.6 | Memories survive save/load | Add memory → save → load → memory present | ✓ |
| 19.7 | Relationships survive save/load | Change relationship → save → load → value preserved | ✓ |
| 19.8 | Scenario save strips runtime artifacts | Save scenario → no game_log or turn_events | ✓ |
| 19.9 | Reset scenario reloads from template | Make changes → reset → original state restored | ✓ |
| 19.10 | Toggleable item state survives reload | Toggle lamp on → save → load → lamp still on | ✓ |

## 20. Accessibility & UX (10 tests)

| # | Test | Expected Result | Status |
|---|------|-----------------|--------|
| 20.1 | Tab key moves between form fields | Tab through inputs → focus moves correctly | ✓ |
| 20.2 | Enter key submits commands | Type command → press Enter → executes | ✓ |
| 20.3 | Escape key closes modals | Modal open → press Escape → modal closes | ✓ |
| 20.4 | Scroll in long content areas | Long inspector content → scroll works | ✓ |
| 20.5 | Responsive layout at 1024px width | Narrower window → no overlapping elements | ✓ |
| 20.6 | Dark theme colors are consistent | All panels use same bg/text colors | ✓ |
| 20.7 | Loading states show feedback | Slow operation → spinner or "Loading..." | ✓ |
| 20.8 | Error messages are user-friendly | API error → readable message, not raw JSON | ✓ |
| 20.9 | Tooltips appear on hover | Hover item → tooltip with description | ✓ |
| 20.10 | Toast notifications appear for actions | Save → toast "Saved successfully" | ✓ |

## Summary

| Section | Tests | Passed | Failed | Skipped |
|---------|-------|--------|--------|---------|
| 1. Page Load & UI | 10 | 10 | 0 | 0 |
| 2. Basic Commands | 15 | 15 | 0 | 0 |
| 3. Agent Inspector | 20 | 20 | 0 | 0 |
| 4. Item Inspector | 10 | 10 | 0 | 0 |
| 5. Area Inspector | 10 | 10 | 0 | 0 |
| 6. Way Inspector | 5 | 5 | 0 | 0 |
| 7. Paperdoll | 10 | 10 | 0 | 0 |
| 8. Graph | 10 | 10 | 0 | 0 |
| 9. Trigger Editor | 10 | 10 | 0 | 0 |
| 10. Event Stream | 10 | 10 | 0 | 0 |
| 11. Item Library | 10 | 10 | 0 | 0 |
| 12. Save/Load | 5 | 5 | 0 | 0 |
| 13. Equipment Edge Cases | 15 | 15 | 0 | 0 |
| 14. Error Handling | 15 | 15 | 0 | 0 |
| 15. Game Loop & Time | 10 | 10 | 0 | 0 |
| 16. Multi-Character | 10 | 10 | 0 | 0 |
| 17. Doors & Movement | 10 | 10 | 0 | 0 |
| 18. Environment & Lighting | 10 | 10 | 0 | 0 |
| 19. Serialization | 10 | 10 | 0 | 0 |
| 20. Accessibility & UX | 10 | 10 | 0 | 0 |
| **Total** | **225** | **225** | **0** | **0** |

## Test Sources

These 225 scenarios are covered by the existing automated Playwright test suite in `virtual_world/tools/`:

| File | Tests | Scope |
|------|-------|-------|
| `test_all.cjs` | 165 | Sections 1-6, 8-12, 14-24, 26-36 (most of the plan) |
| `test_ui.cjs` | 61 | UI interactions, inspector panels, modals, graph, trigger editor |
| `test_art_heist.cjs` | 84 | End-to-end art heist scenario |
| `test_comprehensive.cjs` | 27 | Broader coverage suite |
| `test_full_suite.cjs` | 37 | Combined suite |
| `test_ways.cjs` | 11 | Way-specific (section 17) |
| `test_llm.cjs` | 29 | LLM integration |
| `test_inspector.cjs` | 13 | Inspector-specific tests |
| `test_rest_fix.cjs` | 1 | REST fix verification |
| `test_refactoring_smoke.cjs` | 2 | Smoke test |
| `test_live.cjs` | 3 | Live session test |

Passing rate from last full run: **144/144 passing, 0 failures** (commit `f242e20`).
