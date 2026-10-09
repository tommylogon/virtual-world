---
type: task
status: todo
area: characters
priority: medium
---

# task-742: Faction-scoped hostility and group-aware fear; wire or retire the hostile trait

**Filed:** 2026-10-08
**Related:** task-390, task-550, task-619

## Goal

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
