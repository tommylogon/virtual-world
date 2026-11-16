---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Items & Inventory/Equipment & Paperdoll]]"
related: [task-852, task-938]
---

# task-940: Clothing cleanliness, grime accumulation, hygiene coupling, and laundry change routines

**Filed:** 2026-11-09
**Related:** task-852, task-938

<!-- deps:start -->
**Related:** [[task-852-persona-ui-improvement-plan-workspace-doll-navigation-markings-state-integration]], [[task-938-bodypart-image-attachments-and-clothing-occlusion-inspection]]
<!-- deps:end -->

## What

Introduce a clothing cleanliness and grime mechanic that couples worn garment state to character body hygiene, environmental soil events, and autonomous morning change routines:

1. **Item Cleanliness & Grime Properties**:
   - Add `cleanliness` (0 to 100, default 100) and optional `stains` (list of strings, e.g. `["mud", "cooking grease"]`) to equippable garments.
   - Grime accumulates on worn layers over simulation ticks:
     - Inner layers (underwear, undershirt) absorb body sweat and grime as `player.vitals["Hygiene"]` decays.
     - Outer layers accumulate soil from physical labor, sleeping without changing into nightwear, and environmental travel.
   - Mishaps and environmental events apply instant soiling: trudging through marsh biomes, slipping in dirt, or failing cooking tasks adds stain tags and drops cleanliness sharply.
2. **Body Hygiene Coupling**:
   - Wearing soiled clothing (`cleanliness < 40`) directly penalizes or caps the character's body `Hygiene` vital. A character cannot bathe to 100% hygiene and remain clean while dressed in muddy or sweat-stained garments.
   - Severely dirty garments alter character examine prose: *"wearing a mud-spattered vest and grimy trousers"*.
3. **Laundry & Washing Actions**:
   - Interacting with wash basins, rivers, tubs, or areas carrying `BATH_TAGS` allows `wash <item>` or `wash all clothes`, restoring item cleanliness to 100% and clearing removable stain tags.
4. **Autonomous Changing & Morning Routine**:
   - In `engine/background_simulation.py`, update character need evaluation on waking:
     - If sleeping in nightwear or worn clothes are soiled (`cleanliness < 50`), the character initiates a morning routine: strip soiled clothes, wash at a hygiene fixture, and equip fresh clean clothes from an available wardrobe, chest, or dresser.

## Why

Currently, characters experience `Hygiene` vital decay and seek out wash spots, but clothes are immortal and permanently clean. A character can roll through swamp mud, sleep in a barn, and cook over a greasy hearth for weeks without their garments ever becoming dirty. Connecting item cleanliness to body hygiene grounds the simulation, gives wardrobes and dressers a real physical purpose, and makes morning routines (changing out of sleepwear and washing up) natural and observable.

## How

1. In `engine/equipment.py`:
   - Initialize `cleanliness: 100` and `stains: []` on wearable item nodes if missing.
   - When calculating character hygiene decay in `engine/vital_rates.py`, factor in worn clothing cleanliness: if worn items average cleanliness < 50, accelerate hygiene decay and cap max hygiene.
2. In `engine/items/examine_actions.py`:
   - Append stain and soil descriptors to garment descriptions when `cleanliness < 50`.
3. In `engine/activities.py` and `routes/action_handlers.py`:
   - Implement `wash <item>` action when character is in an area with washing fixtures or water sources, resetting item cleanliness to 100.
4. In `engine/background_simulation.py`:
   - Add `CLOTHING_HYGIENE_THRESHOLD = 50`.
   - On waking or low clothing cleanliness, schedule a changing task to find clean garments in nearby containers.

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Inventory / Paperdoll view and Item Inspector.

Current availability: Characters track body hygiene vitals, but items carry no cleanliness stat or stain tags, and clothing never soils.

Live steps when available:
1. Open Character Inspector for a character and inspect their equipped `Lightweight Linen Shirt`.
   - expected: Item badge displays `✨ Clean (100%)`.
2. Move the character through a muddy swamp area or simulate 24 hours of labor without washing.
   - expected: Shirt cleanliness drops to `35%` with a `mud-spattered` descriptor tag.
3. Have the character bathe at a shower or washbasin while keeping the dirty shirt equipped.
   - expected: Character washes, but their body Hygiene caps at `50%` due to wearing soiled garments.
4. Unequip the shirt, locate a washbasin, and type `wash lightweight linen shirt`.
   - expected: Cleanliness restores to `100%` and mud stains clear.
5. Store spare clean clothes in a wardrobe, advance overnight ticks, and observe character waking behavior.
   - expected: Character wakes up, strips soiled sleepwear, washes at the basin, and equips fresh clothing from the wardrobe.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser UI, inspect wearable items in the Character Inspector inventory list.
   - expected: Renders item cleanliness percentage or condition indicator.
   - observed: Items only show name, weight, and description.
2. Soil an item via command line and advance ticks.
   - expected: Character hygiene vital reflects dirty clothing cap.
   - observed: Body hygiene operates independently of clothing state.
3. Execute `wash <item>` near a water fixture.
   - expected: Item cleanliness resets to 100.
   - observed: Action not recognized or fails.
4. Run test suite: `pytest tests/test_vital_rates.py` and `pytest tests/test_equipment.py`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Wearable garments track `cleanliness` (0 to 100) and `stains`.
- [ ] Daily wear and environmental events decay clothing cleanliness.
- [ ] Soiled clothing caps or accelerates body `Hygiene` decay.
- [ ] `wash <item>` action restores garment cleanliness at water/bath fixtures.
- [ ] Background simulation drives waking characters to change out of soiled clothes.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `engine/equipment.py`
- `engine/vital_rates.py`
- `engine/background_simulation.py`
- `engine/activities.py`
- `static/js/inspector/paperdoll-view.ts`
- `tests/test_vital_rates.py`
