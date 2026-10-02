---
type: task
status: done
area: characters
priority: high
---

# task-606: Author scale-correct ability scores per size tier so a leviathan is not STR 9

**Filed:** 2026-09-30
**Related:** 

## Goal

**DECIDED 2026-09-30 by Tommy:** use the **D&D numbers until D&D stops making
sense**, and the result has to work across **fantasy, modern, sci-fi, horror and
romance** -- anything.

So 5e is the *baseline curve*, not the ceiling:

| tier | 5e reference | STR | CON |
|---|---|---|---|
| tiny | Rat, Sprite | 2-3 | 9-10 |
| small | Goblin | 8 | 10 |
| normal | Human commoner | 10-13 | 10-12 |
| huge | Ogre, Troll | 18-19 | 14-16 |
| giant | Hill Giant, Giant Ape | 21-23 | 16-21 |
| titanic | Ancient Black Dragon 27, **Tarrasque 45** | 27-45 | 22-25 |

The requirement that decides the work: a sci-fi hull or a horror entity must fit
the same curve, and a romance scene must not need a leviathan. So the tiers are
the spine and the values inside a tier are the authoring surface -- a starship
is `giant`, a ghost is `small` and takes no space (see task-652), a housecat is
`tiny`.

Nothing clamps ability scores today, so STR 35 is storable immediately. This
task is authoring plus whatever the curve still cannot express.

5e has canonical stat blocks matching the existing 6 tiers (tiny rat STR2, small goblin STR8, normal human 10-13, huge ogre 19, giant hill-giant 21, titanic ancient-black-dragon 27 / tarrasque 45). No ability score is clamped, so STR 35 is storable today -- the gap is purely authored data.

## Acceptance

- [x] **The 5e curve exists as data**, per size tier, as reference points plus a
      tolerance — `engine/abilities.py::SIZE_TIER_REFERENCE`, matching the
      decided table exactly (tiny 2-3, small 8, normal 10-13, huge 18-19, giant
      21-23, titanic 27-45 for STR; and the CON values beside them).
- [x] **It is not a clamp.** A leviathan at STR 9 was storable before and still
      is; what is new is that the authoring API **reports** it
      (`scale_warnings` in the update response) and that the curve is **readable**
      (`GET /api/abilities/curve`) so an author never picks a number blind.
- [x] **The library is authored.** 67 of 70 characters now carry a `size` and 35
      a `species`, derived from tags they already had. Five tiers are in use
      (tiny 3, small 18, normal 41, huge 4, giant 1) instead of one.
- [x] **No character contradicts its own size**, and no character with a size is
      missing STR/CON unless it is inanimate.
- [x] **No authored number was lost** — checked against `git show HEAD:<file>`
      for every one of the 67 rewritten files, not against a hand-written list.
- [x] **The two stat-key vocabularies are one.** 31 files wrote `str`/`dex`,
      37 wrote `STR`/`DEX`, and a lowercase block left the character with **no
      readable STR at all**. `normalize_stat_block` folds either case at all six
      writers and is the only spelling the library now stores.
- [x] Tests in `tests/test_abilities.py` (35 tests) including the curve's own
      self-consistency and the API wiring.

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `engine/abilities.py` — **new**. `SIZE_TIER_REFERENCE`, `SIZE_TIER_DEFAULTS`,
  `MASS_SCALED_ABILITIES`, `TOLERANCE`, `ABILITIES`, `stats_for_size`,
  `ability_range`, `tolerance_band`, `scale_issues`, `is_scale_correct`,
  `is_inanimate`, `normalize_stat_block`, `describe_curve`.
- `engine/effects.py`, `engine/serialization.py`, `routes/player_ops.py` (×3),
  `routes/library_ops.py` — the six stat writers, all folding.
- `routes/player_ops.py` — `scale_warnings` on the update response.
- `routes/players.py` — `GET /api/abilities/curve`.
- `data/library/characters/*.json` — 67 files authored.
- `tests/test_abilities.py` — **new**, 35 tests.

### The bug underneath the task

`the butcher` is authored `str: 18, con: 20`. The loader did
`p.stats = lib_data.get("stats", {})`, which replaced the uppercase defaults and
then failed every `stats.get("STR", 10)` in the engine — so it fought at **STR
10**, and its CON 20 never reached the engine either.

31 of the 70 library files spell abilities in lowercase and 37 in uppercase, with
no overlap. So the task's premise — "the gap is purely authored data" — was
half right: it was *also* a vocabulary bug in shipped data, and the honest form
of "a leviathan is not STR 9" is that several characters were **no** STR at all.
33 characters had no readable STR or CON when the pass started.

### The decisions

1. **Reference points plus a tolerance, not exclusive boxes.** A tier is a
   *bucket*: 5e's `small` contains both a goblin (STR 8) and an imp. Encoding the
   goblin as a range flagged every wolf in the category — a wolf at STR 12 is not
   a wolf that fails to be a wolf. The band is the reference widened by a factor
   of two, so the check fires on a `titanic` at STR 9 and on a creature with no
   stat block, and stays quiet on everything 5e itself would place there. **A
   flag is only worth having if it is rare and true.**
2. **No clamping, ever.** A clamp silently destroys the information that the
   block was wrong. The write is accepted and the author is told, which is why
   the acceptance criterion is "reported, not refused".
3. **Inanimate things are exempt.** The Straw Practice Dummy is `giant` with
   `STR 1` **on purpose** — the whole point of it is that it cannot fight back.
   The curve describes what a *body* can do, and checking a training frame
   against it reported deliberate authoring as a defect.
4. **Only STR and CON scale.** The mental abilities have nothing to do with how
   much of you there is. A band on INT is an invitation to author a dragon at
   INT 3.
5. **Authored data beats inference, everywhere in the pass.** A stat block is a
   number somebody wrote; a size derived from a tag is a guess about the same
   fact. Where they disagreed (`Croak-Mother`: tagged `frog`, STR 10/CON 14) the
   numbers won. And a creature whose tags say only "animal" — `rat`,
   `whiskers`, `Shadow-Pelt` — got **no size at all** rather than a guessed one.
6. **The library files were rewritten in the canonical spelling.** The pass was
   casing-aware precisely because it was not: a naive fill added `STR: 11` beside
   an author's `str: 18` and, since the engine prefers the canonical spelling, the
   *fill* would have won and the author's number would have been thrown away. One
   spelling of one fact is the only way that cannot happen.

### Not done here

- **No stat block was rewritten** where one existed. A character whose stats
  disagree with its size is reported, and fixing it is the author's call — the
  library has none left.
- **`size_from_stats` is a tooling choice, not engine behaviour.** The engine
  never infers a size from stats; that was only ever this one-off authoring pass.
- **task-605's `size_*` trait fallback** is untouched and still read first.

### Verify

```
python -m pytest tests/test_abilities.py -q                          # 35 passed
python -m pytest tests/test_abilities.py tests/test_species.py \
  tests/test_size_property.py tests/test_library_character_import.py \
  tests/test_character_loadout_check.py tests/test_combat.py \
  tests/test_occupancy.py tests/test_health_model.py -q              # 198 passed
```

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty — across a 67-file data change, so the
authoring moved nothing that anything else notices.

`test_species.py::test_every_library_character_still_loads_and_behaves_identically`
was updated by this task and is worth reading: it originally asserted that *no*
library character declares a species, which was true when task-549 landed and
false the moment this pass set 35. Its actual point — that declaring a species
denies nothing by accident — is unchanged and still asserted.

### Live verification — 2026-10-02, `python app.py` on `VW_PORT=4466`

**1. The curve is readable** — an author picking a size no longer guesses:

```
GET /api/abilities/curve
  tiers      : tiny, small, normal, huge, giant, titanic
  titanic STR: reference 27-45   tolerated 13.5-90
```

**2. The task's own sentence, through the authoring API** — a leviathan at STR 9
is *reported, not refused*:

```
POST /api/players/LiveLeviathan {"size":"titanic","stats":{"STR":9,"CON":9,...}}
  -> 200 {"status": "updated",
          "scale_warnings": [
            "STR 9 is far from what a titanic creature should have
             (reference 27-45, tolerated 13.5-90)",
            "CON 9 is far from what a titanic creature should have
             (reference 22-25, tolerated 11-50)"]}
```

**3. Counter-case**, so the warning is not simply always-on: the same write for
a `huge` ogre at STR 19 / CON 15 returns `status: updated` with **no**
`scale_warnings` key at all.

**4. The shipped bug is gone.** `the butcher` is authored `str: 18, con: 20`
(lowercase). Before this task the engine read **STR 10** for it, because the
block replaced the uppercase defaults and then failed every
`stats.get("STR", 10)`. Written through the API in lowercase and read back from
`/api/state`:

```
authored lower-case str:18 -> engine reads STR=18 CON=20 attack_bonus=3
```

Live world returned to its prior state afterwards (probe characters removed).


