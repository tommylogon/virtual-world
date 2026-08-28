---
type: task
status: inprogress
area: characters
priority: high
---

# task-349: Relationship system hardening

Audit of the relationship system (see [[Characters/Relationships System]]). Closeness only moves via
speech (+2), give (+5), and combat (-30); several save/label/guidance defects found.

## Code fixes (this task)

- [x] **Serialize full relationship record** — `player.py` `to_dict()` (line ~621) emits only `{closeness, interaction_count}`. Add `first_sighting` and `last_interaction_tick` so recency + stranger state survive save/load. (#5)
- [x] **verified not-a-bug** — `relationshipGuidance()` DOES return a directive for > 75 ("trust them completely"). No change needed. (#6, corrected)
- [x] **Align label tiers** — frontend `relationshipTypeName()` -> `"inseparable"` (+ article fix in buildRelationshipLabel/Context). (#7)
- [x] **Align guidance tiers to label tiers** — `relationshipGuidance()` now mirrors `relationshipTypeName()` (-75/-50/-25/0/25/50/75, incl. mortal-enemy + neutral tiers). (#10)
- [x] **Symmetric give** — `engine/items/transfer_actions.py:65` updates only the recipient's closeness (+5 toward giver). Make it symmetric (giver +5 toward recipient too), matching speech. (#4)

## Verified NOT a bug

- **First-meeting double-count (#9)** — sight uses `register_first_meeting()` which returns `False` if the relationship already exists and never calls `update_relationship()`, so `interaction_count` isn't bumped twice. Confirmed safe.

## Design follow-ups (not in this task)

- **Richer closeness deltas per social action (#1)** — flux: flirt/help/comfort/banter/activities/emotion don't move closeness. Would need per-action sentiment values.
- **Time decay (#2)** — nothing lowers closeness over time; add a decay term in the tick.
- **Affect/valence weighting (#3)** — speech tone/volume/emotion not scored; a compliment and an insult are both +2.
- **Derive relationships from memories (#8)** — seeded `closeness:0` can contradict authored memories of prior acquaintance; deicde whether to auto-derive or keep as an authoring invariant.

## Related
- [[Characters/Relationships System]]
- [[AI & Narration/Agent Engine]] (task-94 closeness gates behavior)
