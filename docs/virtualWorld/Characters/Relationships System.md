# Relationships System

> Type: system · area: characters · status: accurate as-of 2026-09 · source: engine/relationships.py, player.py, engine/speech.py, engine/combat.py, engine/items/transfer_actions.py, engine/background_social.py, static/js/agent/prompt-builder/character-state.js

Relationships are the social state each character tracks toward every other character they've met. They drive **display labels**, **behavioral guidance injected into the prompt**, a **grapple modifier**, and — since task-423 — **whether two characters will socialise, and how it lands**. They are *not* automatically derived from memories — they are mutated by authored *events*.

## Data model (Player.relationships, player.py)

```text
relationships = {
    "<other_player_name>": {
        "closeness": -100..100,   # -100 sworn enemy - 0 neutral - 100 inseparable
        "last_interaction_tick": int,
        "interaction_count": int,
        "label": str,             # authored declaration ("my brother"); never decayed
        "first_sighting": bool    # "name unknown" - stranger/masked label until met/spoken
    }
}
```

- **closeness** clamps to [-100, +100] — in **one** place, `clamp_closeness`.
- **first_sighting** is set True when seen but not yet introduced; it flips off once the name is known (via speech / name-tag read). It drives the stranger label (area_description.py, scene_snapshot.py).
- **label** is a *declaration*, not a measurement, so nothing decays it and the `label` command writes it directly without touching closeness.

## The one mutation path — engine/relationships.py (task-420)

Every gameplay writer used to touch this dict itself (combat, the foreground loop,
first-meeting registration, the `label` command), so no **cause** was recorded — a
delta from a beating looked identical to one from a shared meal — and the two
fidelity tiers could disagree about how the scalar evolves, which is how a value
could jump at a promotion/demotion.

`apply_relationship_delta(player, other, delta, cause, tick, area_id)` is now the
only writer of `closeness`:

```text
rel["closeness"] = clamp_closeness(rel["closeness"] + delta)
rel["last_interaction_tick"] = tick
rel["interaction_count"] += 1
trace: kind="relationship", why="social:<cause>", delta={closeness, cause, with}
```

- `apply_symmetric_delta(a, b, delta, cause)` makes symmetry a property of the
  *call*, so a meeting cannot be applied to one side by accident. Each side still
  gets its own trace entry, because each side's history is its own.
- `ensure_relationship(player, other, tick) -> (record, created)` — creating a
  record is not the same as *feeling* something: it moves no closeness and grants
  no novelty.
- `closeness_band` / `band_at_least` / `BAND_LABELS` — the band ladder (mortal
  enemy → inseparable) lives here and `Player.get_relationship_nl` calls it, so
  band-gated rules cannot disagree with the prompt's wording about the edges.
- The doctrine is pinned by a test that scans `engine/`, `routes/` and `player.py`
  for `relationships[...] = ` and allows exactly two elsewhere, both payload
  imports in `routes/player_ops.py` (deserialization, not a mutation).

## What actually affects relationships

| Event | File | Delta | Cause |
|-------|------|-------|-------|
| **Speak to someone** (a directed line) | engine/speech.py | +2 both directions | `dialogue` |
| **Give an item** | engine/items/transfer_actions.py | +5 — only the *recipient* grows toward the giver | `dialogue` |
| **Attack / damage** someone | engine/combat.py | −30 — only the *target's* closeness toward the attacker drops | `combat` |
| **Background social action** | engine/background_social.py | per action and tier, **per side** | the action name |
| **`label <person> <relationship>`** | routes/action_handlers.py | none — writes `label` only | — |

## Background social interactions (task-423)

Two co-present background characters pick an action, and **each side records its
own outcome**: Rikka teases Vekka and Rikka's memory reads "I teased Vekka" with
closeness up, while Vekka's reads "Rikka teased me" with closeness down.

- **The gate:** same area (there is no distance in this world model, so nothing
  else would stop two characters on opposite sides of the camp from meeting),
  both `simulation_mode == "background"`, both conscious and not mid-activity.
  **An attended character is never paired** — their social life belongs to the LLM
  loop.
- **Cap:** `MEETINGS_PER_CHARACTER_PER_DAY` 6, rolled over on the in-game day, plus
  a `SOCIAL_COOLDOWN_MINUTES` 90 cooldown between one character's interactions.
  The cap is the bound; there is deliberately no blocking "conversation" activity
  (task-423's outcome explains the measurement that removed it).
- **Selection** is a weighted draw, never argmax: from traits (`social_gain`,
  `impatient`, `patient`, `hostile`, `attention_seeker`), the closeness band and
  need pressure. `ignore` is the separate "they don't engage" draw and costs
  nothing, not even the cap.
- **Outcome** is a d20 + Persuasion + band modifier against the action's DC,
  mapped to six tiers, seeded per `(actor, target, tick, action)` so a replay
  reproduces the same history.
- **The sign rule** is load-bearing: a `tease` between friends reads positive for
  both sides, the same tease at low closeness is an attack on the target, and
  `bully` is never warm however well it lands.
- Both sides get a **templated memory** (`engine/social_text.py`) tagged with
  `entity_ids = [actor, target, area]` — which is what makes "every memory Vekka
  has about Rikka" a lookup rather than a keyword search.

## Meeting novelty

A first meeting grants Entertainment through the **shared novelty curve**
(task-434), keyed on the other character's node id (`Player.node_id_for`). It both
*reads* and *records* the observation, which is what makes it idempotent in either
order with perception — walking into a room holding a stranger and having one walk
in later both pay exactly once. It used to be a separate flat +10 that double-paid.

## Natural-language labels (two parallel systems — slight drift)

**Backend** get_relationship_nl() (player.py:443): mortal enemy (<=-75) - enemy (<=-50) - rival (<=-25) - unfriendly (<0) - neutral (0) - acquaintance (<=25) - friend (<=50) - close friend (<=75) - **inseparable** (>75).

**Frontend** relationshipTypeName() (character-state.js:39): same tiers, except the top is **"inseparable friend"** (minor name drift). Inline label via buildRelationshipLabel() (character-state.js:54) renders as `a close friend` (no numeric score).

## Behavioral guidance — relationshipGuidance(closeness) (task-94, character-state.js:87)

Injected into the prompt as a per-character behavioral directive:

| closeness | directive |
|-----------|-----------|
| <= -50 | "you want them gone; refuse help, keep replies hostile or silent" |
| <= -25 | "keep interactions cold and minimal; never turn your back on them" |
| < 0 | "you keep your guard up; brief, wary replies" |
| <= 25 | "polite but reserved; courtesy without warmth" |
| <= 50 | "you are friendly; chat openly and help when asked" |
| <= 75 | "you are glad they are here; engage warmly, share news, watch out for them" |
| **> 75** | "you trust them completely; prioritize their safety, share secrets, stay close" |

## Relationship-driven mechanics (readers)

- **Grapple** (engine/grapple.py:61-69,305): DC = 10 + grabber Athletics + relationship modifier (+ extra-target penalty). Modifier = -(closeness // 25) * GRAPPLE_REL_PER_LEVEL — a friend is *harder* to grapple (higher DC), an enemy easier. Clamped.
- **Prompt label** per "People here" line (room-context): inline type label, no score.
- **Name-known / stranger mask**: first_sighting -> anonymous label (`the man`, `the woman`) until name known.

## Serialization (player.py:621-627)

to_dict() emits **only** {closeness, interaction_count} per relationship.

> Warning: **first_sighting and last_interaction_tick are NOT persisted.** They are dropped on save, so recency-based guidance can't work across a save, and the stranger/unmasked state may reset on load.

---

## What's missing / broken (gaps found in this audit)

> Status: audited against task-349. Items marked **[fixed]** are resolved; **[not-a-bug]** verified safe; the rest are open design follow-ups.

1. **Closeness barely responds to social texture.** Only speech (+2), give (+5), and combat (-30) move it. Flirting, helping, comforting, banter, shared activities, emotional beats, and even negative social friction (cold, dismissive, insulting) do not change closeness unless they happen to be a speech line.
2. **No time decay.** Nothing lowers closeness over time or from neglect — only an outright attack does. Relationships are monotonic upward (or crater from one attack). The -20..+20 docstring range is unused; real deltas are +2/+5/-30.
3. **No affect/valence weighting.** Speech tone, volume, and emotion are scored not at all — a whispered compliment and a shouted insult both move closeness by the same +2.
4. **[fixed]** **Asymmetric give.** Give updates only the recipient's closeness toward the giver; the giver's toward the recipient is unchanged. (Now symmetric — task-349.)
5. **[fixed]** **Serialization drops first_sighting and last_interaction_tick** — recency/stranger state not durable across saves. (to_dict now emits both — task-349.)
6. **[not-a-bug]** Originally flagged: relationshipGuidance returns undefined for closeness > 75. Verified the code already returns a "trust them completely" directive; the >75 tier exists. (Also now explicitly aligned — task-349.)
7. **[fixed]** **Two label systems drift** — backend get_relationship_nl ("inseparable") vs frontend relationshipTypeName ("inseparable friend"). (Frontend aligned to "inseparable" + article fixed — task-349.)
8. **Relationships are not derived from memories.** Seeded closeness:0 / interaction_count:0 can contradict authored memories of prior acquaintance (e.g. miki<->jake had prior banter memories but 0 closeness). Authoring must keep the two in sync; nothing computes one from the other.
9. **[fixed]** **Guidance tier boundaries don't match label tier boundaries** (guidance: -50/-25 vs label: -75/-50/-25). (relationshipGuidance tiers now mirror the label tiers — task-349.)
10. **[not-a-bug]** **First meeting may double-count.** Sight uses register_first_meeting(), which returns False if the relationship already exists and never calls update_relationship(), so interaction_count isn't bumped twice. Verified safe.

## Related
- [[Characters/Characters Overview]]
- [[AI & Narration/Agent Engine]] (closeness gates behavior, task-94)
- [[Gameplay/Character Spatial Position]]
