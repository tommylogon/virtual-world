---
group: Pleasure System
---

# NPC Perception & Reaction Framework

**Filed**: 2026-08-11
**Priority**: Low
**Status**: Done (2026-09-22) — simple-NPC tier

---

## Status — implemented (2026-09-22)

**Live game, simple-NPC tier.** Simple NPCs have no LLM, so "the LLM sees the
description" never applied to them; this gives them a mechanical floor for
noticing state/action. LLM agents and humans already perceive through their own
prompts, so they are deliberately **not** double-handled here. Sexual stimuli are
mature-gated; generic stimuli are always active.

### Shipped
- **Traits** (`engine/traits.py` + `data/library/traits/*.json`):
  `observant` / `oblivious` (perception DC −5 / +5, `perception_dc_mod`),
  `prudish` (`npc_reaction: disapprove`), `open_minded` (`approach`),
  `attracted` (mature: `approach` + sharper arousal reading).
- **`engine/npc_behaviors.py`**:
  - `calculate_perception_difficulty(npc, target, stimulus_type)` — base DC 10
    ± trait mods, ambient light (<20 → +10, >80 → −5), and the target's
    outer-layer `coverage` over the relevant region (covered skin reads harder).
  - `check_perception(npc, dc)` — d20 + WIS mod + Perception trait mods, silent
    (no `[Save]` log spam on every reaction).
  - `process_npc_reaction(npc, target, stimulus_type)` — perception roll, then
    reaction from traits: prudish → disapprove, attracted/open_minded →
    approach (open_minded only when Social > 50), generic → comment.
  - `process_bystander_reactions(actor, target, stimulus_type)` — simple NPCs in
    the actor's area react, capped at one line per stimulus so a crowd does not
    flood the log. Dead and undead-ghost NPCs never react.
  - `process_npcs_on_combat(context)` — the old `pass` stub now routes
    `combat_actors` through the generic stimulus path (combat passes it in
    `engine/combat.py:219`).
- **Hook**: `engine/pleasure_actions.execute_intimacy_action()` calls the
  bystander path after resolving an intimacy verb and appends any reaction line.
- **Emissions** reuse the existing channels — `add_log_entry` +
  `record_turn_event(..., "npc_reaction")` — no new event stream.
- **Tests**: `tests/test_npc_perception.py` (20) — DC modifiers, reaction
  selection, mature gate, bystander filtering (agent excluded, other area
  excluded, actor/target excluded), crowd cap, and the intimacy integration.

### Not done / future
- Only simple NPCs react mechanically. If agent characters should also get a
  mechanical perception floor, extend `process_bystander_reactions` past the
  `simple_npc` filter — but keep it advisory (a turn event the LLM can read),
  not a decision override.
- "Nearby rooms → +5" distance penalty from the design is not implemented; v1
  considers only characters in the same area.
- `aroused` / `nipple_hard` / `wetness` are accepted as stimulus types (with
  coverage modifiers) but nothing currently *generates* them per tick; v1 is
  event-driven (intimacy action, combat).

---

## Original problem

NPCs can't mechanically "notice" another character's state (hard nipples, blushing, arousal) or react to it (disapprove, approach, comment). Perception is currently LLM-flavor only.

## Related

- [[Intimacy and Body Sensitivity System - Design]] §8 (Phase 6)
- `task-213 mature traits`, `task-211 intimacy verbs`, `task-208 friction`
