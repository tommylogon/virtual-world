# Relationships System

> Type: system · area: characters · status: accurate as-of 2026-08 · source: player.py, engine/speech.py, engine/combat.py, engine/items/transfer_actions.py, static/js/agent/prompt-builder/character-state.js

Relationships are the social state each character tracks toward every other character they've met. They drive **display labels**, **behavioral guidance injected into the prompt**, and a **grapple modifier**. They are *not* automatically derived from memories — they are mutated by a small set of authored *events*, or seeded manually.

## Data model (Player.relationships, player.py:134)

```text
relationships = {
    "<other_player_name>": {
        "closeness": -100..100,   # -100 sworn enemy - 0 neutral - 100 inseparable
        "last_interaction_tick": int,
        "interaction_count": int,
        "first_sighting": bool    # "name unknown" - stranger/masked label until met/spoken
    }
}
```

- **closeness** clamps to [-100, +100] (player.py:439).
- **first_sighting** is set True when seen but not yet introduced; it flips off once the name is known (via speech / name-tag read). It drives the stranger label (area_description.py:282-287, scene_snapshot.py:112-114).

## The mutation method — update_relationship(other, tick, sentiment_change) (player.py:424)

The single write-path for closeness. On first contact it creates the entry and grants an **Entertainment novelty boost** (_grant_meeting_entertainment(), mirrored from area/item-discovery boosts, task-136). Then:

```text
rel["closeness"] = clamp(-100, 100, rel["closeness"] + sentiment_change)
rel["last_interaction_tick"] = tick
rel["interaction_count"] += 1
```

The docstring documents sentiment_change: -20..+20 per interaction, but that full range is **never used** — see the call sites below.

## What actually affects relationships (the only mutation call-sites)

| Event | File | Delta | Symmetric? |
|-------|------|-------|-----------|
| **Speak to someone** (a directed speech line) | engine/speech.py:217,220 | **+2** both directions | yes |
| **Give an item** to a character | engine/items/transfer_actions.py:65 | **+5** | **no** - only the *recipient* grows (+5 toward giver); the giver's sentiment is unchanged |
| **Attack / damage** someone | engine/combat.py:110 | **-30** (min -100) | no - only the *target's* closeness toward the attacker drops |

That's the whole set — **three mutation points**. Everything else only *reads* closeness (grapple modifier engine/grapple.py:61-69, prompt guidance, labels).

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
