---
group: Gameplay
---
# Auto-Dressing Characters from Interest Tags

**Filed**: 2026-08-21  
**Priority**: Medium  
**Status**: Planned â€” blocked by task-326 (needs healthy interest tags)

---

## Summary

Procedurally assemble and equip a coherent outfit on a character: walk their
`interest_tags` (style/domain signals) plus context (weather/temperature,
setting), select clothing from the library per slot-coverage rules, layer it
underwearâ†’baseâ†’outer, and equip through the existing EquipmentSystem.

## Current State (verified 2026-08-21)

- âœ… All 60 wearable library items have `equip_slots` (tools/fix_item_equipment.py)
- âœ… EquipmentSystem supports layered slot stacks with max_depth
  (engine/equipment.py:23 â€” torso 5 deep, legs 4, feet 3...) â€” layering is just
  stack order; Miki's saved `equipped` dict proves the model works
- âœ… `is_exposed()` / coverage logic exists in engine/body_parts.py (outer layer,
  coverage â‰¥ 0.8 = covered)
- âœ… `insulation` item tag + Temperature vital + heat system exist â†’
  weather-appropriate dressing is feasible now
- âœ… strip/undress â†’ clothing_pile, dress reverses it (AGENTS.md gotcha)
- âŒ No outfit assembly logic: no "which slots must be filled", no layering
  order rules, no interestâ†’clothing selection

## Design

### Slot coverage rules

Minimum complete outfit (per gender-tag where relevant):

| Slot | Required | Example fill |
|------|----------|--------------|
| legs | underwear + bottom | panties â†’ trousers |
| torso | top (+bra where character implies) | bra â†’ tank top |
| feet | footwear optional but common | socks â†’ boots |
| outerwear | optional, weather-driven | coat if cold |

Layering = stack order per slot: first equipped = innermost. Selection picks
items by subcategory tag (`underwear` â†’ first, `top`/`bottom` â†’ middle,
`outerwear` â†’ last).

### Selection pipeline

1. Candidate pool: library items tagged `clothing` whose tags âˆ© character's
   style-relevant interests â‰  âˆ… (`jewelry`, `occult`, `elven`, `punk`-flavored
   via `leather`, ...)
2. Fill required slots first (nearest tag match), then accessories with leftover
   interest budget (`accessory`, `jewelry`, `hair_accessory` are cheap wins)
3. Weather gate: area temperature / forecast below threshold â†’ require
   `insulation`-tagged outer layer (ties into task-215 environmental clothing
   effects â€” coordinate, don't duplicate)
4. Deterministic option: seedable RNG; seed stored so an outfit can be regenerated

### Fit limits (honest scope)

"Fit" = slot compatibility only. No body measurements (three-sizes live as prose
in personality text), no garment size matching against `size_*` traits yet.
Size-tier gating (tiny characters shouldn't wear normal clothes) is a stretch
goal using engine/size.py tiers.

## Work Plan

1. `engine/dressing.py` (new, <600 lines):
   - `plan_outfit(character, candidates, weather, rng) -> {slot: [lib_id, ...]}`
   - `apply_outfit(...)` â†’ build items + equip in layer order via EquipmentSystem
     (respect task-146's takeâ†’hands flow once it lands)
2. Route `POST /api/dress/<player_id>` (params: formality? seed? weather override)
   + MCP tool `dress_character`
3. Editor affordance later (character inspector button) â€” separate commit
4. Tests: fixture character + library subset; assert slot coverage, layer order,
   insulation gating, idempotency (dressing twice doesn't double-stack)

## Files

- `engine/dressing.py` (new module)
- `routes/*.py` (one thin route), `mcp_server.py` (one tool)
- `tests/test_dressing.py` (new)

## Verification

- pytest suite green
- Manual: dress miki from a cold-area context â†’ underwear+top+outer present in
  correct stack order; `look` description reflects layers; undressâ†’dress round-trips

## Dependencies

- Blocked by: task-326 (interests feed style selection)
- Uses: equipment system as-is; coordinates with task-146 (equip flow changes)
  and task-215 (environmental clothing effects share the weather signal)
- Optional synergy: task-9 population can dress mannequins/rack displays using
  the same planner
