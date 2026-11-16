---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Items & Inventory/Equipment & Paperdoll]]"
related: [task-852, task-937]
---

# task-938: Bodypart image attachments and clothing occlusion rules for anatomy inspection

**Filed:** 2026-11-09
**Related:** task-852, task-937

<!-- deps:start -->
**Related:** [[task-852-persona-ui-improvement-plan-workspace-doll-navigation-markings-state-integration]], [[task-937-agentic-playwright-image-generation-authoring-pipeline]]
<!-- deps:end -->

## What

Extend the character body region model (`player.body_state[region]`) with optional per-bodypart image attachments, and establish clothing occlusion rules that realistic hide bare skin, wounds, sensitivity, and art beneath equipped layers:

1. **Per-Bodypart Image Storage & Inspection**:
   - Allow authors and players to attach optional image assets to individual body regions (e.g. detailed wound photo, scar, tattoo, cybernetic prosthetic, or anatomical illustration).
   - Stored in `player.body_state[region].image` (or character node properties).
   - In Persona View (`static/js/inspector/persona-view.ts`), clicking a bodypart on the interactive doll displays its image thumbnail alongside live sensitivity, markings, and injury levels.
2. **Clothing Occlusion Mapping**:
   - Establish a declarative mapping between equipment slots and covered anatomy regions:
     - `torso` covers `chest`, `belly`, `back`.
     - `legs` covers `groin`, `left_thigh`, `right_thigh`, `left_shin`, `right_shin`.
     - `feet` covers `left_foot`, `right_foot`.
     - `hands` covers `left_hand`, `right_hand`.
     - `head` covers `head`, `hair`, `ears` (helmets/hoods).
     - `arms` covers `left_arm`, `right_arm`.
3. **In-World Perception & Examination Rules**:
   - When an actor executes `examine <character>'s <bodypart>`:
     - If the targeted bodypart is covered by one or more equipped garments, the observer receives: *"Covered by [Outer Item Name]"* (e.g. *"Covered by Heavy Fur-Lined Coat"*).
     - Bare skin descriptions, scars, tattoos, sensitivity ratings, wound details, and bodypart image previews are completely occluded.
     - If the character is unclothed/stripped on that slot, or if the action is self-examination in private (`examine my chest`), the full anatomical description, injury level, sensitivity, and bodypart image are displayed.

## Why

Currently, `persona-view.ts` allows viewing and editing sensitivity and injuries on the paperdoll, but there is no way to attach visual depictions (such as prosthetics, scars, or tattoos) to specific bodyparts. More critically, the simulation lacks clothing occlusion: an external observer examining a character can read raw body state regardless of whether the character is wearing heavy plate armor or a thick winter coat. Physical reality dictates that clothing blocks direct observation of underlying anatomy and wounds unless the garment is removed or penetrated.

## How

1. In `engine/equipment.py`:
   - Declare `SLOT_OCCLUSION_MAP` mapping each equipment slot to the anatomical body regions it covers.
   - Implement `is_body_region_covered(player, region_id) -> Tuple[bool, Optional[str]]` returning whether any equipped item covers that region and the topmost covering item's name.
2. In `engine/items/examine_actions.py`:
   - In character bodypart examine handler (`examine <character>'s <bodypart>`):
     - Resolve the target bodypart token to a canonical region id.
     - Check `is_body_region_covered()`. If covered and observer is not self, return `"You cannot see <character>'s <region>, as it is covered by <item>."`
     - If exposed, return the body description, visible markings, injury severity, and image URL.
3. In `static/js/inspector/persona-view.ts`:
   - In `renderRegionDetail()`, add an image preview container and upload/URL input for `bs.image`.
   - Display a status badge: `🛡️ Covered by <Item>` (warning badge) or `🌿 Exposed` (neutral badge) based on `player.equipped`.

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Persona View (the interactive body doll) and in-game Event Stream / HTC examine output.

Current availability: Persona View displays body regions, injuries, and sensitivity sliders. No image attachment field exists, and clothing does not occlude bodypart inspection.

Live steps when available:
1. Open Character Inspector for Kaelen Voss and switch to Persona View.
   - expected: Interactive body doll renders with regions.
2. Click on the `Left Leg` region.
   - expected: Detail panel opens showing sensitivity, injury, and an Image attachment field.
3. Set the image URL to a prosthetic sketch (e.g. `/static/assets/images/clockwork_leg.png`) and equip `Stovepipe Leather Boots` and `Wool Trousers`.
   - expected: Detail panel shows thumbnail preview and marks the region as `🛡️ Covered by Wool Trousers`.
4. Switch perspective to another character (e.g. Gribba) and type `examine kaelen's left leg`.
   - expected: Result reads: *"Kaelen's left leg is covered by Wool Trousers."* The clockwork prosthetic art and wound data are hidden.
5. Unequip Kaelen's trousers and re-examine.
   - expected: Result displays the exposed left leg, clockwork prosthetic details, and portrait art link.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser UI, click a bodypart in Persona View and check fields.
   - expected: Shows image upload/URL field and clothing coverage indicator.
   - observed: Only sensitivity slider and injury text exist.
2. Equip a coat on a character and have another actor examine their torso.
   - expected: Reports covered by coat; conceals underlying skin and wounds.
   - observed: Raw body description or generic character look returned.
3. Run test suite: `pytest tests/test_equipment.py` and `pytest tests/test_examine.py`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Body regions in `player.body_state` accept an optional `image` asset reference.
- [ ] Persona View renders image previews and allows setting art per body region.
- [ ] Equipment slots declaratively map to covered anatomical regions.
- [ ] Examining a clothed character's covered bodypart reports the covering item and hides bare skin, wounds, sensitivity, and images.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `engine/equipment.py`
- `engine/items/examine_actions.py`
- `static/js/inspector/persona-view.ts`
- `static/js/inspector/paperdoll-view.ts`
- `tests/test_equipment.py`
