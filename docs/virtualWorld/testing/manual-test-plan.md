# Manual test plan — one scratch world per phase
**Supersedes:** `dev_tasks/done/testing/test-plan-100-items.md` (225 presence checks, never run to a result).
Each step declares six fields so a human and a Playwright script can run the same line:

| Field | Values |
|---|---|
| `id` | stable `phase.index`, referenced by the `.cjs` harnesses |
| `pre` | `scratch` (fresh this phase) / `continue` (previous step's world) |
| `action` | one user-visible action, or one API call |
| `expect` | the observable that must be true — an assertion |
| `may-write` | `nothing` / `scratch-only` / `scratch+assets` |
| `evidence` | the log line, screenshot or JSON path that proves it |

**Gate:** after every phase run `node tools/test_plan_gate.cjs` — it fails if `git status --porcelain` shows anything outside `data/saves/<run-id>/` and the scratch assets directory. A phase that trips it voids the run and names the step.

Every phase starts a new scratch world under `data/saves/<run-id>/` (never `data/scenarios/`) and the runner boots with `_scenario_source` unset so a stray commit fails loudly. See the phase table below.
## Phases
| Phase | Subject | Notes |
|---|---|---|
| 0 | Boot & shell | server starts, no console errors, tabs present, **no file written by boot alone** |
| 1 | Empty scenario | **no such route exists today** — see Blind spots; phase 2 starts from `duplicate` of a hand-made empty file |
| 2 | Graph editor: empty -> one area | add, tag, light, save, reload, persisted |
| 3 | Two areas + a way | areas hard-error on duplicate id; items/ways/characters get suffixed (`graph.py:167-172`) |
| 4 | Items | library item into an area, takeable per declared actions, container, `uses` charge |
| 5 | Characters | add from the editor skeleton, traits, identity; resolve `data/graph_editor_character_template.json` |
| 6 | Triggers | create, fire on a turn, one undo snapshot per `POST /api/graph/batch` |
| 7 | Play a turn | movement, vitals, log lines, export the log, `node tools/log_lint.cjs` |
| 8 | Persistence round-trip | save -> reload -> assert equality, incl. two same-named areas in different scopes (task-446) |
| 9 | Painted world | compile a WorldPainter world, areas carry `world_scope_id`, open-sky/light (bug-54) |
| 10 | Changes panel | `GET /api/scenario/diff` -> apply / discard, apply is a single commit |
## Phase 0 — Boot & shell
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 1.1 | scratch | Server starts without Python errors | `GET /` returns 200, no traceback in logs | nothing | `evidence/step-1.1.txt` |
| 1.2 | continue | Page title exists | `<title>` tag has content, not empty | nothing | `evidence/step-1.2.txt` |
| 1.3 | continue | Command input exists | `#command-input` text field present and visible | nothing | `evidence/step-1.3.txt` |
| 1.4 | continue | Inspector panel exists | `#inspector-panel` element present | nothing | `evidence/step-1.4.txt` |
| 1.5 | continue | Graph canvas exists | `#graph-canvas` element present | nothing | `evidence/step-1.5.txt` |
| 1.6 | continue | Event stream exists | `.event-stream` or `#event-stream` present | nothing | `evidence/step-1.6.txt` |
| 1.7 | continue | Agent list renders | Agent items visible (`.agent-item` or agent list) | nothing | `evidence/step-1.7.txt` |
| 1.8 | continue | Settings/controls exist | Play/Pause/Step buttons visible | nothing | `evidence/step-1.8.txt` |
| 1.9 | continue | API state endpoint responds | `GET /api/state` returns JSON with `areas`, `players`, `graph` | nothing | `evidence/step-1.9.txt` |
| 1.10 | continue | No console errors on page load | `page.on('console', ...)` captures zero errors | nothing | `evidence/step-1.10.txt` |
| 20.1 | continue | Tab key moves between form fields | Tab through inputs → focus moves correctly | scratch-only | `evidence/step-20.1.txt` |
| 20.2 | continue | Enter key submits commands | Type command → press Enter → executes | scratch-only | `evidence/step-20.2.txt` |
| 20.3 | continue | Escape key closes modals | Modal open → press Escape → modal closes | scratch-only | `evidence/step-20.3.txt` |
| 20.4 | continue | Scroll in long content areas | Long inspector content → scroll works | nothing | `evidence/step-20.4.txt` |
| 20.5 | continue | Responsive layout at 1024px width | Narrower window → no overlapping elements | nothing | `evidence/step-20.5.txt` |
| 20.6 | continue | Dark theme colors are consistent | All panels use same bg/text colors | scratch-only | `evidence/step-20.6.txt` |
| 20.7 | continue | Loading states show feedback | Slow operation → spinner or "Loading..." | nothing | `evidence/step-20.7.txt` |
| 20.8 | continue | Error messages are user-friendly | API error → readable message, not raw JSON | nothing | `evidence/step-20.8.txt` |
| 20.9 | continue | Tooltips appear on hover | Hover item → tooltip with description | nothing | `evidence/step-20.9.txt` |
| 20.10 | continue | Toast notifications appear for actions | Save → toast "Saved successfully" | scratch-only | `evidence/step-20.10.txt` |
## Phase 2 — Graph editor: empty -> one area
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 5.1 | scratch | Click room in graph → opens room view | Inspector shows room name, description | scratch-only | `evidence/step-5.1.txt` |
| 5.2 | continue | Area name editable | Change name, save → persists | scratch-only | `evidence/step-5.2.txt` |
| 5.3 | continue | Area description editable | Change description, save → persists | scratch-only | `evidence/step-5.3.txt` |
| 5.4 | continue | Environment (light, temp, air, smell, noise) editable | Change light level → room environment updates | scratch-only | `evidence/step-5.4.txt` |
| 5.5 | continue | Exits section shows all connected areas | List of exits with direction + target room | nothing | `evidence/step-5.5.txt` |
| 5.6 | continue | Items in room section shows items | List of items present in this room | nothing | `evidence/step-5.6.txt` |
| 5.7 | continue | Characters/agents in room section shows agents | List of agents currently in this room | nothing | `evidence/step-5.7.txt` |
| 5.8 | continue | Area event log shows recent events | Events for this room displayed | nothing | `evidence/step-5.8.txt` |
| 5.9 | continue | Click exit → navigates to target room | Area inspector switches to target | scratch-only | `evidence/step-5.9.txt` |
| 5.10 | continue | Floor input editable | Change floor number → persists | scratch-only | `evidence/step-5.10.txt` |
| 8.1 | continue | Graph renders nodes and edges | Rooms, items, ways, characters visible | nothing | `evidence/step-8.1.txt` |
| 8.2 | continue | Area nodes are distinct color | Rooms have different color from items/ways | nothing | `evidence/step-8.2.txt` |
| 8.3 | continue | Drag node repositions it | Node position updates, persists | scratch-only | `evidence/step-8.3.txt` |
| 8.4 | continue | Right-click room → context menu | Menu shows Inspect, Add Item, Move Character etc. | scratch-only | `evidence/step-8.4.txt` |
| 8.5 | continue | Right-click item → context menu | Menu shows Inspect, Edit Item, Save to Library, etc. | scratch-only | `evidence/step-8.5.txt` |
| 8.6 | continue | Right-click door → context menu | Menu shows Inspect, Edit Way, etc. | scratch-only | `evidence/step-8.6.txt` |
| 8.7 | continue | Right-click character → context menu | Menu shows Inspect, Edit Character, etc. | scratch-only | `evidence/step-8.7.txt` |
| 8.8 | continue | Physics toggle works | Enable/disable physics → nodes freeze/unfreeze | scratch-only | `evidence/step-8.8.txt` |
| 8.9 | continue | Search/filter works | Type query → matching nodes highlighted | nothing | `evidence/step-8.9.txt` |
| 8.10 | continue | Legend displays node type meanings | Legend shows room/item/door/character icons | scratch-only | `evidence/step-8.10.txt` |
| 18.1 | continue | Dark room blocks examine | Area light < 20 → "too dark" | scratch-only | `evidence/step-18.1.txt` |
| 18.2 | continue | Light source illuminates room | `light torch` → room light increases | scratch-only | `evidence/step-18.2.txt` |
| 18.3 | continue | Toggleable item affects environment | Toggle lamp on → room brighter | nothing | `evidence/step-18.3.txt` |
| 18.4 | continue | Blind character has limited perception | Blind condition → examine fails | nothing | `evidence/step-18.4.txt` |
| 18.5 | continue | Area temperature affects body temp | Cold room → body temp drifts down | nothing | `evidence/step-18.5.txt` |
| 18.6 | continue | Fireplace warms adjacent room | Light fireplace → temperature rises | scratch-only | `evidence/step-18.6.txt` |
| 18.7 | continue | Air quality affects breathing | Toxic air → HP damage over time | nothing | `evidence/step-18.7.txt` |
| 18.8 | continue | Noise prevents restful sleep | Loud room → sleep doesn't restore energy | scratch-only | `evidence/step-18.8.txt` |
| 18.9 | continue | Light spills through open ways | Next room with open door gets dim light | scratch-only | `evidence/step-18.9.txt` |
| 18.10 | continue | Environment persists across reload | Change light → save → load → light still changed | scratch-only | `evidence/step-18.10.txt` |
## Phase 3 — Two areas + a way
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 6.1 | scratch | Click door in graph → opens door view | Inspector shows door name, state | scratch-only | `evidence/step-6.1.txt` |
| 6.2 | continue | Way state dropdown works | Change open → closed → locked → persists | nothing | `evidence/step-6.2.txt` |
| 6.3 | continue | Way description editable | Change description → persists | scratch-only | `evidence/step-6.3.txt` |
| 6.4 | continue | Cardinal direction editable | Change direction → persists | scratch-only | `evidence/step-6.4.txt` |
| 6.5 | continue | Trigger section on door shows triggers | Way triggers visible and editable | nothing | `evidence/step-6.5.txt` |
| 17.1 | continue | Open a closed door | `open north` → door state becomes "open" | scratch-only | `evidence/step-17.1.txt` |
| 17.2 | continue | Close an open door | `close north` → door state becomes "closed" | scratch-only | `evidence/step-17.2.txt` |
| 17.3 | continue | Go through a door | `go north` → player in new room | nothing | `evidence/step-17.3.txt` |
| 17.4 | continue | Locked door blocks movement | `go north` (locked) → "it's locked" | nothing | `evidence/step-17.4.txt` |
| 17.5 | continue | Unlock door with key | `use key on door` → door unlocked | scratch-only | `evidence/step-17.5.txt` |
| 17.6 | continue | Hidden door discovered via fumble | `fumble` → discover hidden exit | scratch-only | `evidence/step-17.6.txt` |
| 17.7 | continue | Auto-close door after passing | Walk through auto-close door → door closes behind | scratch-only | `evidence/step-17.7.txt` |
| 17.8 | continue | Skill-check door | `go north` with skill door → check roll | nothing | `evidence/step-17.8.txt` |
| 17.9 | continue | Blocked door cannot be opened | `open north` (blocked) → "cannot open" | scratch-only | `evidence/step-17.9.txt` |
| 17.10 | continue | Way state visible in inspector | Click door node → state dropdown shows current | nothing | `evidence/step-17.10.txt` |
## Phase 4 — Items
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 4.1 | scratch | Click item in graph → opens item view | Inspector shows item name, description | scratch-only | `evidence/step-4.1.txt` |
| 4.2 | continue | Item actions grid checkable/uncheckable | Toggle examine/take/use/read etc. | scratch-only | `evidence/step-4.2.txt` |
| 4.3 | continue | Properties (state, uses, weight) editable | Change values, save, refresh → persists | scratch-only | `evidence/step-4.3.txt` |
| 4.4 | continue | Tags editable and addable | Add tag "magic" → tag appears | scratch-only | `evidence/step-4.4.txt` |
| 4.5 | continue | Two-handed checkbox works | Check → item is two-handed in data | nothing | `evidence/step-4.5.txt` |
| 4.6 | continue | Equip slots multi-select works | Select "head" → item can be equipped to head | scratch-only | `evidence/step-4.6.txt` |
| 4.7 | continue | Triggers section shows existing triggers | List of triggers with type + effect summary | nothing | `evidence/step-4.7.txt` |
| 4.8 | continue | "➕ Add" trigger button opens modal | Overlay appears with trigger type select | scratch-only | `evidence/step-4.8.txt` |
| 4.9 | continue | Add effect row works | Click "➕ Add Effect" → new effect row appears | scratch-only | `evidence/step-4.9.txt` |
| 4.10 | continue | Save trigger → persists | Fill trigger form, save → trigger appears in list | scratch-only | `evidence/step-4.10.txt` |
| 7.1 | continue | Paperdoll renders 12 slots | Grid shows head, neck, torso, arms, hands, legs, feet, back, waist, hand_left, hand_right, accessory | nothing | `evidence/step-7.1.txt` |
| 7.2 | continue | Filled slot has accent border | Equipped slot shows different border color | nothing | `evidence/step-7.2.txt` |
| 7.3 | continue | Click + button → equip picker opens | Modal with items filtered by slot | scratch-only | `evidence/step-7.3.txt` |
| 7.4 | continue | Equip item → appears in slot | Item name shown in paperdoll slot | scratch-only | `evidence/step-7.4.txt` |
| 7.5 | continue | ✕ button → unequips item | Item removed from slot, back in inventory | nothing | `evidence/step-7.5.txt` |
| 7.6 | continue | Right-click slot → context menu | Menu shows Inspect / Unequip / Open Container | scratch-only | `evidence/step-7.6.txt` |
| 7.7 | continue | +N more badge on stacked slots | Slot with 2+ items shows "+N more" badge | nothing | `evidence/step-7.7.txt` |
| 7.8 | continue | Click +N more → stack popup opens | Popup shows inner layers with ✕ buttons | scratch-only | `evidence/step-7.8.txt` |
| 7.9 | continue | Accessory items listed below paperdoll | Accessory grid shows all equipped accessories | nothing | `evidence/step-7.9.txt` |
| 7.10 | continue | "Equip from Inventory" button works | Opens picker filtered for all items | scratch-only | `evidence/step-7.10.txt` |
| 11.1 | continue | Open Library button → modal opens | Item library modal visible | scratch-only | `evidence/step-11.1.txt` |
| 11.2 | continue | Library items list renders | Items shown with name, type icon, description | nothing | `evidence/step-11.2.txt` |
| 11.3 | continue | Click item → editor opens | Right panel shows item editor form | scratch-only | `evidence/step-11.3.txt` |
| 11.4 | continue | Create new item button works | New item form with empty fields | scratch-only | `evidence/step-11.4.txt` |
| 11.5 | continue | Save new item → appears in list | Library list updates with new item | scratch-only | `evidence/step-11.5.txt` |
| 11.6 | continue | AI generate item → populates form | Type prompt, click Generate → fields filled | scratch-only | `evidence/step-11.6.txt` |
| 11.7 | continue | Delete item → removed from list | Confirmation → item disappears | scratch-only | `evidence/step-11.7.txt` |
| 11.8 | continue | Filter/search items | Type in filter → list narrows | scratch-only | `evidence/step-11.8.txt` |
| 11.9 | continue | Container contents editable | Add items to container → contents list updates | scratch-only | `evidence/step-11.9.txt` |
| 11.10 | continue | Add Trigger in library editor | Same trigger editor as item inspector | scratch-only | `evidence/step-11.10.txt` |
| 13.1 | continue | Equip item from inventory via right-click | Right-click item in inventory → "Equip" → item moves to slot | scratch-only | `evidence/step-13.1.txt` |
| 13.2 | continue | Unequip via right-click on paperdoll slot | Right-click filled slot → "Unequip" → item back in inventory | scratch-only | `evidence/step-13.2.txt` |
| 13.3 | continue | Equip with wrong slot type | Equip boots to "head" slot → error message | scratch-only | `evidence/step-13.3.txt` |
| 13.4 | continue | Two-handed weapon frees both hands on unequip | Equip greatsword → both hands filled → unequip → both free | scratch-only | `evidence/step-13.4.txt` |
| 13.5 | continue | Stack badge shows "+N more" with 3 items | Equip 3 accessories → badge reads "+2 more" | nothing | `evidence/step-13.5.txt` |
| 13.6 | continue | Stack popup shows inner layers | Click +N more → popup lists inner items with ✕ buttons | nothing | `evidence/step-13.6.txt` |
| 13.7 | continue | Click ✕ in stack popup → unequips inner layer | Remove inner item → outer item stays | scratch-only | `evidence/step-13.7.txt` |
| 13.8 | continue | Drop equipped item → auto-unequips | Equip helmet → drop helmet → slot empty | scratch-only | `evidence/step-13.8.txt` |
| 13.9 | continue | "Generate from Equipment" button works | Click → description textarea updates with LLM-generated text | scratch-only | `evidence/step-13.9.txt` |
| 13.10 | continue | Self-examine shows equipped items | `examine self` → narrative includes worn items | nothing | `evidence/step-13.10.txt` |
| 13.11 | continue | Other-examine shows visible equipment | `examine [other player]` → shows their equipment | nothing | `evidence/step-13.11.txt` |
| 13.12 | continue | Edit base_description → persists | Change base text, save → re-open shows changed text | scratch-only | `evidence/step-13.12.txt` |
| 13.13 | continue | Container equipment (backpack) opens on click | Equip backpack → click → shows container contents | scratch-only | `evidence/step-13.13.txt` |
| 13.14 | continue | Multiple items in same slot → visual layering | 3 items in torso → top item visible, +2 badge | nothing | `evidence/step-13.14.txt` |
| 13.15 | continue | Undress command removes outer layer | `undress` → outermost item from each slot removed | scratch-only | `evidence/step-13.15.txt` |
## Phase 5 — Characters
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 3.1 | scratch | Click agent in list → opens Stats tab | Inspector shows agent name, stats, vitals | scratch-only | `evidence/step-3.1.txt` |
| 3.2 | continue | Stats tab shows STR/DEX/CON/INT/WIS/CHA | Six stat fields with values | nothing | `evidence/step-3.2.txt` |
| 3.3 | continue | Vitals display shows HP/Energy/Hunger etc. | Vital bars or values visible | nothing | `evidence/step-3.3.txt` |
| 3.4 | continue | Click Equipment tab → paperdoll renders | 12 body slots visible (head, neck, torso, etc.) | scratch-only | `evidence/step-3.4.txt` |
| 3.5 | continue | Empty slot shows "—" or empty state | Unfilled slots show empty indicator | nothing | `evidence/step-3.5.txt` |
| 3.6 | continue | Click Inventory tab → carried items grid | Grid of inventory items with name + weight | scratch-only | `evidence/step-3.6.txt` |
| 3.7 | continue | Click Bio tab → personality + appearance | Personality textarea + description textarea | scratch-only | `evidence/step-3.7.txt` |
| 3.8 | continue | Click Relationships tab → relationship list | Shows relationships with closeness values | scratch-only | `evidence/step-3.8.txt` |
| 3.9 | continue | Click Advanced tab → timeline + commands | Timeline viewer + manual command input | scratch-only | `evidence/step-3.9.txt` |
| 3.10 | continue | Edit personality → save → persists | Change text, save, re-open, text is changed | scratch-only | `evidence/step-3.10.txt` |
| 3.11 | continue | Edit description → save → persists | Same as above | scratch-only | `evidence/step-3.11.txt` |
| 3.12 | continue | Kill character → state = "dead" | Kill button works, HP=0, state="dead" | scratch-only | `evidence/step-3.12.txt` |
| 3.13 | continue | State dropdown changes state | "awake" → "sleeping" → "unconscious" etc. | scratch-only | `evidence/step-3.13.txt` |
| 3.14 | continue | Current room dropdown changes room | Selecting a new room moves the character | scratch-only | `evidence/step-3.14.txt` |
| 3.15 | continue | Emotion dropdown changes mood | Neutral → happy → sad → angry etc. | scratch-only | `evidence/step-3.15.txt` |
| 3.16 | continue | Emotion intensity slider updates | Dragging slider changes intensity value | scratch-only | `evidence/step-3.16.txt` |
| 3.17 | continue | Skills are visible and editable | Skills list with +/- for each skill | nothing | `evidence/step-3.17.txt` |
| 3.18 | continue | World knowledge textarea editable | Can add world knowledge text | scratch-only | `evidence/step-3.18.txt` |
| 3.19 | continue | Export character downloads JSON | Click export → file saved/offered | scratch+assets | `evidence/step-3.19.txt` |
| 3.20 | continue | Import character restores state | Import a previously exported character card | scratch-only | `evidence/step-3.20.txt` |
## Phase 6 — Triggers
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 9.1 | scratch | Add Trigger from item inspector | Click "➕ Add" → modal opens with trigger type select | scratch-only | `evidence/step-9.1.txt` |
| 9.2 | continue | Select trigger type | Choose on_examine → target field hidden, target_state hidden | scratch-only | `evidence/step-9.2.txt` |
| 9.3 | continue | Select on_use_on → target field appears | Target input + datalist shown | scratch-only | `evidence/step-9.3.txt` |
| 9.4 | continue | Select on_state_enter → target_state appears | Target state input shown | scratch-only | `evidence/step-9.4.txt` |
| 9.5 | continue | Add effect row with type | Select effect type (damage) → parameter fields appear | scratch-only | `evidence/step-9.5.txt` |
| 9.6 | continue | Add condition row with type | Select condition (has_item) → parameter field appears | scratch-only | `evidence/step-9.6.txt` |
| 9.7 | continue | Success/fail message fields | Type messages → saved with trigger | scratch-only | `evidence/step-9.7.txt` |
| 9.8 | continue | Save trigger → appears in list | New trigger shown in trigger list on item | scratch-only | `evidence/step-9.8.txt` |
| 9.9 | continue | Edit trigger → pre-populates existing data | Click edit → modal opens with existing values | scratch-only | `evidence/step-9.9.txt` |
| 9.10 | continue | Delete trigger → removed from list | Click ✕ → trigger disappears | scratch-only | `evidence/step-9.10.txt` |
## Phase 7 — Play a turn
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 2.1 | scratch | `look` command | Returns room description, items, exits | nothing | `evidence/step-2.1.txt` |
| 2.2 | continue | `inventory` command | Shows carried items or "nothing" | nothing | `evidence/step-2.2.txt` |
| 2.3 | continue | `i` alias | Same as inventory | nothing | `evidence/step-2.3.txt` |
| 2.4 | continue | `examine self` | Shows player description + equipment narrative | nothing | `evidence/step-2.4.txt` |
| 2.5 | continue | `stats` command | Shows vitals (HP, Hunger, Thirst, etc.) | nothing | `evidence/step-2.5.txt` |
| 2.6 | continue | `help` or `commands` | Returns list of available commands | nothing | `evidence/step-2.6.txt` |
| 2.7 | continue | `go north` (if exit exists) | Moves to next room, returns new description | nothing | `evidence/step-2.7.txt` |
| 2.8 | continue | `go [invalid]` | Returns error "You can't go that way" | nothing | `evidence/step-2.8.txt` |
| 2.9 | continue | `look at [item in room]` | Returns item description | nothing | `evidence/step-2.9.txt` |
| 2.10 | continue | `take [item]` | Adds item to inventory | scratch-only | `evidence/step-2.10.txt` |
| 2.11 | continue | `drop [item]` | Removes item from inventory | scratch-only | `evidence/step-2.11.txt` |
| 2.12 | continue | `use [item]` | Fires on_use trigger if exists, else message | scratch-only | `evidence/step-2.12.txt` |
| 2.13 | continue | `toggle [toggleable item]` | Toggles item state | scratch-only | `evidence/step-2.13.txt` |
| 2.14 | continue | `rest 1` | Advances time, restores energy | scratch-only | `evidence/step-2.14.txt` |
| 2.15 | continue | Ambiguous command → LLM suggestion | If enabled, returns suggested command | nothing | `evidence/step-2.15.txt` |
| 10.1 | continue | Event stream shows "Initialized" message | Log shows engine initialization | nothing | `evidence/step-10.1.txt` |
| 10.2 | continue | Command output appears in stream | Typing a command → output in stream | nothing | `evidence/step-10.2.txt` |
| 10.3 | continue | Turn events show after command | Events display with tick count | nothing | `evidence/step-10.3.txt` |
| 10.4 | continue | Agent step button triggers agent action | Click step → agent thinks/decides/acts | scratch-only | `evidence/step-10.4.txt` |
| 10.5 | continue | Agent thought appears in stream | 💭 bubble with agent's thinking | nothing | `evidence/step-10.5.txt` |
| 10.6 | continue | Agent action appears in stream | ⚡ bubble with agent's action | nothing | `evidence/step-10.6.txt` |
| 10.7 | continue | Agent speech appears in stream | 💬 bubble with agent's speech | nothing | `evidence/step-10.7.txt` |
| 10.8 | continue | Stream auto-scrolls to newest event | New events visible at bottom | nothing | `evidence/step-10.8.txt` |
| 10.9 | continue | Clear log button works | Clears event stream | nothing | `evidence/step-10.9.txt` |
| 10.10 | continue | Filters show/hide event types | Toggle thought/speech/action visibility | scratch-only | `evidence/step-10.10.txt` |
| 14.1 | continue | Empty command returns usage hint | Just press Enter → shows "Invalid command" or help | nothing | `evidence/step-14.1.txt` |
| 14.2 | continue | Unknown command shows suggestion | Type "flarg" → "Did you mean...?" or "Unknown command" | nothing | `evidence/step-14.2.txt` |
| 14.3 | continue | Take nonexistent item | `take unicorn` → "You don't see that" | scratch-only | `evidence/step-14.3.txt` |
| 14.4 | continue | Drop nonexistent item | `drop unicorn` → "You don't have that" | scratch-only | `evidence/step-14.4.txt` |
| 14.5 | continue | Use item not in inventory | `use unicorn` → "You don't have that" | scratch-only | `evidence/step-14.5.txt` |
| 14.6 | continue | Examine nonexistent target | `examine unicorn` → "You don't see that" | nothing | `evidence/step-14.6.txt` |
| 14.7 | continue | Go to nonexistent direction | `go unicorn` → "You can't go that way" | nothing | `evidence/step-14.7.txt` |
| 14.8 | continue | REST API returns 400 for missing command | `POST /api/action {}` → 400 "Missing command" | scratch-only | `evidence/step-14.8.txt` |
| 14.9 | continue | REST API returns 404 for unknown route | `GET /api/unicorn` → 404 | scratch-only | `evidence/step-14.9.txt` |
| 14.10 | continue | Server handles malformed JSON | `POST /api/action "not json"` → 400 Bad Request | nothing | `evidence/step-14.10.txt` |
| 14.11 | continue | Kill already dead character | Kill dead character → error or "already dead" | scratch-only | `evidence/step-14.11.txt` |
| 14.12 | continue | Sleep while already sleeping | `sleep` while sleeping → "already asleep" | scratch-only | `evidence/step-14.12.txt` |
| 14.13 | continue | Move while unconscious | Move unconscious player → "cannot move" | scratch-only | `evidence/step-14.13.txt` |
| 14.14 | continue | Use item with 0 uses | Use depleted item → "item has no more uses" | scratch-only | `evidence/step-14.14.txt` |
| 14.15 | continue | Open locked door without key | Go through locked door → "it's locked" / skill check | scratch-only | `evidence/step-14.15.txt` |
| 15.1 | continue | Turn applies vital decay | `rest 1` → Hunger decreases, Energy recovers | scratch-only | `evidence/step-15.1.txt` |
| 15.2 | continue | Time advances with rest | Game time increases after rest | scratch-only | `evidence/step-15.2.txt` |
| 15.3 | continue | Starvation causes HP loss | Hunger stays 0 for multiple ticks → HP decreases | nothing | `evidence/step-15.3.txt` |
| 15.4 | continue | Temperature affects thirst | Hot room → thirst increases faster | nothing | `evidence/step-15.4.txt` |
| 15.5 | continue | Sleeping restores energy | `sleep` → energy recovers per tick | scratch-only | `evidence/step-15.5.txt` |
| 15.6 | continue | Unconscious from zero energy | Energy hits 0 → state becomes "unconscious" | nothing | `evidence/step-15.6.txt` |
| 15.7 | continue | Death from extreme vitals | HP hits 0 → state becomes "dead" | nothing | `evidence/step-15.7.txt` |
| 15.8 | continue | Body spawns on death | Dead character → "body" item appears in room | nothing | `evidence/step-15.8.txt` |
| 15.9 | continue | Ghost mode allows limited actions | Dead character in ghost mode → can look but not take | nothing | `evidence/step-15.9.txt` |
| 15.10 | continue | Shelter from extreme temperature | Indoor room vs outdoor → vitals decay differently | nothing | `evidence/step-15.10.txt` |
| 16.1 | continue | Create second player | `POST /api/players` → new player added | scratch-only | `evidence/step-16.1.txt` |
| 16.2 | continue | Switch active player | Click agent list → active player changes | scratch-only | `evidence/step-16.2.txt` |
| 16.3 | continue | Two players in same room can interact | Player A speaks → Player B hears | nothing | `evidence/step-16.3.txt` |
| 16.4 | continue | Players in different areas are isolated | Area A's events not visible in Area B | nothing | `evidence/step-16.4.txt` |
| 16.5 | continue | Turn queue initializes correctly | Agents ordered by initiative | nothing | `evidence/step-16.5.txt` |
| 16.6 | continue | Dead characters are skipped in turn queue | Dead → not processed in step | nothing | `evidence/step-16.6.txt` |
| 16.7 | continue | Agent stops after max steps | `config.maxSteps` → agent stops automatically | nothing | `evidence/step-16.7.txt` |
| 16.8 | continue | Agent memory persists | Agent remembers past events → visible in context | nothing | `evidence/step-16.8.txt` |
| 16.9 | continue | Emotion affects behavior | High anger → different narrative choices | nothing | `evidence/step-16.9.txt` |
| 16.10 | continue | Relationships track interactions | Player talks to NPC → relationship value changes | scratch-only | `evidence/step-16.10.txt` |
## Phase 8 — Persistence round-trip
| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 12.1 | scratch | Save game creates file | `POST /api/save-game` → file in saves/ | scratch-only | `evidence/step-12.1.txt` |
| 12.2 | continue | Load game restores state | `POST /api/load-game/` → state restored | nothing | `evidence/step-12.2.txt` |
| 12.3 | continue | Reset scenario reloads world | `POST /api/reset` → fresh world from template | scratch-only | `evidence/step-12.3.txt` |
| 12.4 | continue | Settings toggle (ghost mode, narration) | Toggle on/off → setting persists | scratch-only | `evidence/step-12.4.txt` |
| 12.5 | continue | LLM profile switch works | Switch provider/model → config updates | nothing | `evidence/step-12.5.txt` |
| 19.1 | continue | Save game creates valid JSON | `GET /api/save` → valid JSON with all required keys | scratch-only | `evidence/step-19.1.txt` |
| 19.2 | continue | Load game restores player position | Save → move player → load → player back in original room | scratch-only | `evidence/step-19.2.txt` |
| 19.3 | continue | Equipped items survive save/load | Equip → save → load → equipment still present | scratch-only | `evidence/step-19.3.txt` |
| 19.4 | continue | Player vitals survive save/load | Take damage → save → load → HP still lowered | scratch-only | `evidence/step-19.4.txt` |
| 19.5 | continue | Area environment survives save/load | Change light → save → load → light still changed | scratch-only | `evidence/step-19.5.txt` |
| 19.6 | continue | Memories survive save/load | Add memory → save → load → memory present | scratch-only | `evidence/step-19.6.txt` |
| 19.7 | continue | Relationships survive save/load | Change relationship → save → load → value preserved | scratch-only | `evidence/step-19.7.txt` |
| 19.8 | continue | Scenario save strips runtime artifacts | Save scenario → no game_log or turn_events | scratch-only | `evidence/step-19.8.txt` |
| 19.9 | continue | Reset scenario reloads from template | Make changes → reset → original state restored | scratch-only | `evidence/step-19.9.txt` |
| 19.10 | continue | Toggleable item state survives reload | Toggle lamp on → save → load → lamp still on | scratch-only | `evidence/step-19.10.txt` |
## Phase 1 — Empty scenario (a finding, not a test)

There is **no "new empty scenario" route** today: `/api/scenarios` offers
list/duplicate/rename/delete/get and `/api/scenario` offers
name/commit/append/diff/diff/apply/status. Starting from nothing is not a
supported journey.

| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 1.1 | scratch | Decide: add a `POST /api/scenarios/empty` route, or accept that phase 2 starts from `duplicate` of a hand-made empty file | the decision is recorded here before phase 2 is written | nothing | this section |
| 1.2 | scratch | `POST /api/scenarios/duplicate` of a hand-made empty scenario | a new scratch scenario exists under `data/saves/<run-id>/` | scratch-only | `evidence/step-1.2.json` |

## Phase 9 — Painted world

| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 9.1 | scratch | `POST /api/world/scopes`, then `/grid` and `/grid/paint_batch` | the scope has a grid; `validate` reports no unknown ids | scratch-only | `evidence/step-9.1.json` |
| 9.2 | continue | `POST /api/world/scopes/<id>/grid/generate` | no `unknown id` note; the scope is `materialized` | scratch-only | `evidence/step-9.2.json` |
| 9.3 | continue | Read every generated area's `world_scope_id` | all carry the scope id; no foreign scope id is returned (task-402 guard) | nothing | `evidence/step-9.3.json` |
| 9.4 | continue | Load the painted world and `look` | compiled areas carry the open-sky/light behaviour — **bug-54**'s missing open-sky tag would show here | nothing | `evidence/step-9.4.png` |

## Phase 10 — Changes panel

| id | pre | action | expect | may-write | evidence |
|---|---|---|---|---|---|
| 10.1 | scratch | Make an edit, then `GET /api/scenario/diff` | the diff names the edit | scratch-only | `evidence/step-10.1.json` |
| 10.2 | continue | `POST /api/scenario/diff/apply` | the edit is applied as **one** commit and the diff empties | scratch-only | `evidence/step-10.2.json` |
| 10.3 | continue | Make an edit, then discard it | the world returns to the pre-edit state | scratch-only | `evidence/step-10.3.json` |

## Blind spots (what is NOT covered, and why)

- **All 215 migrated steps carry `may-write` by inference**, not by measurement:
  the old plan never declared it, so `nothing` / `scratch-only` is read from the
  step's verbs. A step whose action mutates through a side door would be
  mislabelled.
- **The migrated steps have not been executed to a result.** Only the gate and a
  representative subset were run (below). The plan is executable; its per-step
  results are not yet recorded.
- **`--phase` browser execution does not exist yet.** `tools/test_plan_gate.cjs`
  enforces the world/write gate; a runner that executes a phase's steps is
  task-444's `tools/test_runner.cjs` and the `.cjs` harnesses, keyed by step id.
- **Phase 1** is unresolved by design (no empty-scenario route).
- **task-574's** WorldPainter entries belong here and are linked, not restated.

## First run (2026-10-02)

- Host: `VW_PORT=4470`, `python app.py` against the shipped template.
- `node tools/test_plan_gate.cjs` before and after the run: **clean**.
- Executed live via `tools/test_runner.cjs --suite full`: **11/11 passed**
  (boot, description persistence, narration, ghost mode, trigger delete,
  equip/paperdoll, move, mocked 500 x2, malformed). Those cover representative
  steps from phases 0, 4, 5 and 8.
- `git status` after the run: clean once the temporary save slot and autosave
  were removed.
- **Not run:** phases 1/2/3/6/7/9/10 remain unexecuted; recorded as the honest
  state, not as passes.
