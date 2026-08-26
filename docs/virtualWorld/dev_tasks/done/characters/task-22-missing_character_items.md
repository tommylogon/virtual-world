# Missing Character Items (Phone, Granola Bar, Flashlight, Water Bottle)

**Filed**: 2026-07-18
**Priority**: Medium
**Status**: Todo — verified still missing on 2026-08-03 (full data audit). Implementation is design work, owner: Tommy.

## Summary

Several characters in `data/scenarios/mansion.json` lack items they're supposed to have. Originally filed against the old players-section `inventory` array (which no longer exists — mansion.json is fully graph/edge-based now, so that data-integrity symptom is obsolete). The **missing item instances are still absent** from the graph edges.

## Missing Items (re-verified 2026-08-03 in `data/scenarios/mansion.json`)

| Character | Missing Items | Currently carries |
|-----------|--------------|-------------------|
| Kayla Jenkins | phone, granola_bar | hair_tie, lighter, lip_gloss |
| Kyrie Johansen | phone, water_bottle | ace_bandage, protein_bar, wrench |
| Sammy Lopez | phone, flashlight, 2nd granola_bar | granola_bar, sneakers, water_bottle |

Evidence:
- Carrying edges at mansion.json:4165-4218 confirm the "currently carries" lists above.
- `item_phone` (mansion.json:4221) and `item_flashlight` (mansion.json:4239) are carried/equipped by **Jake Halloway only**.
- No `item_phone_kayla` / `item_granola_bar_kayla` / `item_water_bottle_kyrie` / etc. nodes exist anywhere in `data/`.
- Note: the same per-character fix pattern WAS applied to **different characters** in `mansion2.json` (`inv_Miki_phone`, Elena Vance's flashlight) — that scenario has no Kayla/Kyrie/Sammy. Likely source of "this was done" confusion.

## Fix (design decision — up to owner)

Two approaches:

- **A. Unique nodes per character** (original task design): create `item_phone_kayla`, `item_granola_bar_kayla`, `item_water_bottle_kyrie`, `item_phone_kyrie`, `item_phone_sammy`, `item_flashlight_sammy` (+ 2nd granola) with character-flavored descriptions, `carrying` edges to the player node, and per-instance triggers.
- **B. Reuse shared nodes**: add extra `carrying` edges from the existing shared `item_phone` / `item_flashlight` / `item_granola_bar` / `item_water_bottle` nodes to the other characters. Cheaper, but all copies share one description/state and the shared on_use triggers fire per-use regardless of owner.

Existing trigger nodes worth mirroring for food/water instances: `trigger_item_granola_bar_on_use_1784402362_7`, `trigger_item_protein_bar_on_use_1784402362_9`, `trigger_item_water_bottle_on_use_1784402362_10` (mansion.json:4468-4513).

## Note

The original "inventory array vs graph edges must be kept in sync" validation concern is moot now that mansion.json is fully edge-based — no array to drift. If per-character instances are created (Option A), consider a quick sanity check that no character's `carrying`+`equipped` edges are empty by design.
