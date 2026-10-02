---
type: task
status: done
area: characters
priority: low
---

# task-487: Exhibitionist trait effect: arousal from being seen

**Filed:** 2026-09-23
**Related:** task-213, task-547

## Blocked (2026-09-27) — no "being seen" signal exists

Re-measured before implementing: this is not a one-line trait consumer. Nothing in
the engine records that one character *observed* another, and nothing distinguishes
a public observation from a covert one.

- `engine/background_social.py` reads `attention_seeker` in exactly two places —
  `action_weights()` boosts `chat`/`joke`/`flirt` ×1.3 and `ignore_weight()` drops
  the ignore weight ×0.6. That is *seeking* attention, not *receiving* it.
- The nearest existing signal is `process_bystander_reactions()` in
  `engine/npc_behaviors.py`, which already runs perception checks, but returns only
  reaction **strings**, skips every non-`simple_npc` character, and is capped by
  `max_reactions` (default 1) — so the observer set is never actually available.
- "Publicly exposed" has no meaning today: `is_exposed()` in
  `engine/body_parts.py` answers *is this body part covered*, not *is anyone
  present to see it*.

Build task-547 first, then this task becomes a consumer over the observation
record. The mature gating and picker hiding already in place
(`routes/library_ops.py` filters traits while `mature_content` is off) do not need
to change.

## Goal

Wire the exhibitionist trait effect, which is currently defined but inert (effects: {exhibitionist: true}, no consumer): grant arousal/pleasure when the character is publicly exposed or being looked at, and add a behavior_prompt. Tracked from task-213.

## Acceptance

- [x] **`exhibitionist` gains a live consumer** — `TraitSystem.has_effect(p,
      "exhibitionist")` is read by `apply_exhibitionism`, which grants
      arousal/pleasure when the character has been seen.
- [x] **It needs an *audience*** — an unseen touch grants nothing. The trait's
      whole meaning is the being-seen, not the sensation, and this is the
      negative case it turns on.
- [x] **Public beats covert** — a public sighting is worth full, a covert one
      half. `is_exposed` cannot answer this (it answers "is this body part
      covered"), which is exactly why task-547 had to exist.
- [x] **A `behavior_prompt` is added** so the agent references the trait, in both
      the runtime definition and the library entry.
- [x] **Only active when `world.mature_content` is on** — the effect returns on
      the first missing pleasure vital, creating nothing; the picker hiding is
      untouched because the trait already declared `mature: true`.
- [x] **Tests**: 11 in `tests/test_exhibitionist.py`, including that a non-carrier
      is byte-identical, that the toggle-off path creates nothing (including no
      path record), and that the effect is **reached from the real intimacy
      action** rather than merely callable.

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `engine/pleasure_actions.py` — `apply_exhibitionism`, called from
  `execute_intimacy_action` right after the observation pass.
- `engine/traits.py` — `behavior_prompt` on `exhibitionist`.
- `data/library/traits/exhibitionist.json` — the same prompt, so the library
  entry and the runtime definition cannot drift (a test checks it).
- `tests/test_exhibitionist.py` — **new**, 11 tests.

### The blocker was already gone, and already in the right place

The "Blocked" note above says task-547 has to exist first. It does, and — worth
recording because it is the good case — the record it built is written **at
exactly the point this effect needs it**:

```
execute_intimacy_action
  -> process_bystander_reactions        (task-214)
     -> record_observations             (task-547)  -> the signal log
  -> apply_exhibitionism                (task-487)  -> reads that log
```

So this is a consumer over a record written a few lines above it, and no new
perception pass was needed.

### The decisions

1. **Reads the record; never re-rolls perception.** `public_observers_of` /
   `observers_of` on the process-wide log. Task-547's whole point was that
   "was there an audience" is answered once, by the pass that rolled it.
2. **A sighting is not a path.** It is filed under `observed_publicly` /
   `observed` (task-545), so a path gate (task-488) can tell "you were watched"
   apart from "you were touched". Without that, `single_track` would be unable
   to express what it means.
3. **Small numbers.** `EXHIBITION_AROUSAL = 4` per public sighting. A glance
   should not become a dominant drive; a large number would make the trait read
   as a malfunction rather than a preference.
4. **The `behavior_prompt` matters on its own**, not just as acceptance
   bookkeeping: it is what makes the *behaviour* the trait implies possible even
   where the arithmetic does not fire, because an agent told nothing about being
   an exhibitionist cannot act like one in an empty room.

### Verify

```
python -m pytest tests/test_exhibitionist.py -q                              # 11 passed
```

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty.


### Live verification — 2026-10-02, `python app.py` on `VW_PORT=4466`

Each case: one `exhibitionist` (or not), one seeded sighting, then the effect.

```
=== task-487: the effect, in both directions ===
  public sighting : arousal +4  | 'Tpublic catches someone watching and leans into it rather '
  covert sighting : arousal +2  | 'Tcovert realises they were being watched.'
  unseen touch    : arousal +0  | ''
  public, no trait: arousal +0  | ''

=== reached from the real intimacy action ===
  arousal +7
  line: Act firmly caresses Tgt on the torso. A visible flush creeps over Tgt.Tgt catches someone watching a
```

The +7 on the real path is the touch itself (+3) plus the public sighting (+4),
and the exhibitionist's line is in the action's own output — so the effect is
reached from the intimacy path, not merely callable.

Note the fourth row: a public sighting with **no trait** grants nothing and says
nothing, which is the non-carrier acceptance criterion in one line.
