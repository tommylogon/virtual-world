---
type: task
status: todo
area: characters
priority: medium
---

# task-742: Faction-scoped hostility and group-aware fear; wire or retire the hostile trait

**Filed:** 2026-10-08
**Related:** task-390, task-550, task-619

## What

Make hostility group-scoped and fear group-aware. Today the real aggro engine is the slasher/is_slasher trait (engine/traits.py:394-407) -> npc_behaviors.slasher_hunt (npc_behaviors.py:747) -> target filter not is_slasher (npc_behaviors.py:824-830), tick hook tick_manager.py:599, combat bonus combat.py:383-404; the mansion uses it. The hostile trait (traits.py:408-414) is documented as dangerous flee or fight but only tints social tone and the fear shout weight (background_social.py:325 and 1278); its HOSTILE effect constant is read nowhere else. Replace the boolean trait exclusion with a group/faction relation so a creature is hostile to a set of groups (everyone except my faction), hostility exemption is same-faction so lich-A undead fight lich-B undead while each ignores its own, and fear exemption is same-group (undead do not fear undead) as a separate criterion. Goblins fear zombies via the goblin fear_tags, independent of whether the zombie is hostile. Decide whether to wire the hostile trait to this relation or deprecate it, since two names for dangerous is the confusion. Acceptance: the zombie/lich/goblin cases; the mansion slasher behaviour must not regress. Relates to task-390 (faction logic, done), task-550 (faction tags, done), task-619 (fear writes relationships).

## Acceptance

- Hostility is a **relation between groups**, not a per-character boolean trait.
  A creature declares the groups it hunts (or "everyone except my faction").
- Same-faction creatures ignore each other: two `faction:lich_a` zombies do not
  target each other, while `lich_a` and `lich_b` undead are hostile to each
  other. `slasher_hunt._get_nearest_player_to` filters on the relation instead of
  `not is_slasher(target)`.
- Fear is **group-aware** and independent of hostility: a character does not fear
  a source in its own group (undead do not fear undead), by a criterion separate
  from the hostility exemption.
- A goblin with a matching `fear_tag` (`undead`) reacts to a zombie (flee / hide
  / shout) with no `hostile` on the zombie — the reaction comes from the
  goblin's tags, not the zombie's.
- The `hostile` trait is either wired to the relation (its documented "flee or
  fight" becomes real) or deprecated; the two names for "dangerous" do not both
  remain half-wired.
- The mansion's `slasher` behaviour is unchanged (regression test).
- Tests: a mechanism test for target selection + fear-source grouping, and a
  micro-scenario exercising each of the zombie / lich-a-vs-lich-b / goblin
  cases.

## Notes

- Real aggro engine today: `slasher`/`is_slasher` trait (`engine/traits.py:394-407`)
  -> `npc_behaviors.slasher_hunt` (`npc_behaviors.py:747`) -> target filter
  `not is_slasher` (`npc_behaviors.py:824-830`); tick hook `tick_manager.py:599`;
  combat bonus `combat.py:383-404`. The mansion uses it.
- `hostile` trait (`traits.py:408-414`): effect constant `HOSTILE` is read only
  by `background_social._traits` (`:325`, `:1278`) for social tone and the fear
  "shout" weight.
- Fear path that writes relationships for non-characters (the `Water Skin`
  case) is task-619's other half.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: author faction/group relations and fear tags on the
characters' existing definition surfaces, then run the scratch encounter from
the game view and inspect the event stream and character Mind state. Hostility
and fear remain separate criteria in the simulation.

Current availability: the card documents the existing mansion slasher hunt and
the current `hostile` trait's limited consumers. Group-scoped hostility and
same-group fear exemption are planned; this card does not claim those rules are
live.

Live steps when available:
1. Load a scratch encounter with two zombies in `faction:lich_a`, one zombie in
   `faction:lich_b`, and one goblin with `fear_tags: [undead]`. Start the sim
   and inspect the event stream after a hunt tick.
   - expected: each lich-a zombie ignores the other lich-a member but may
     target lich-b; the target decision follows the group relation, not a
     blanket `is_slasher` exclusion.
2. Let the goblin encounter a zombie whose hostility relation does not target
   the goblin. Observe the goblin's action and event.
   - expected: the goblin flees, hides, or shouts due to its own `undead` fear
     tag, independently of whether the zombie targets it.
3. Add a same-group undead fear source and repeat the encounter.
   - expected: the goblin/undead same-group exemption follows the separately
     configured fear-group rule; it does not change hostility targets.
4. Inspect authored character values and the event stream after the run.
   - expected: faction hostility, fear-group membership, and `fear_tags` are
     read from their intended sources; the old `hostile` trait is either wired
     to the relation or absent as a competing half-rule.

These steps describe the intended encounter and observable branches. They do
not claim faction-scoped hostility is implemented today.

This section is not a claim that planned UI exists or works today.
