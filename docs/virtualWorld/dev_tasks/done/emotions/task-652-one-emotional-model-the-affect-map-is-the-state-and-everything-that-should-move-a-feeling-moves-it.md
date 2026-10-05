---
type: task
status: done
area: emotions
priority: high
---

# task-652: One emotional model: the affect map is the state, and everything that should move a feeling moves it

**Filed:** 2026-09-30
**Related:** 

## Goal

Every input that should affect a character's emotional state does affect it, in the one model, and that state surfaces memories, steers behaviour and shapes social interaction

## Acceptance

- [x] **One normaliser for a declared feeling.** `felt_from_llm` is no longer
      dead code and the route no longer uses the loose one — a declared feeling is
      resolved by the same function everywhere.
- [x] **No authored alias is dropped.** Every one of the ~70 entries in
      `LABEL_TO_DIM` now resolves, and the eleven `AXIS_TO_EXPRESSION` names are
      authored into `LABEL_TO_DIM` rather than inherited by accident.
- [x] **A coincidental substring does not resolve.** `hangry` stays un-resolved
      (it does not become `angry`), which is what task-505 was filed for and what
      the old route path violated.
- [x] **An invented word is still ignored** — an LLM cannot invent a dimension.
- [x] **The affect map is readable as a set of feelings**, not just a leader:
      `engine.emotion.raised_axes`, sharing the one label threshold so the label a
      reader sees and the axes behaviour reads cannot disagree.
- [x] **The feeling steers behaviour.** `action_weights` now takes the actor's
      raised affect axes into account, so a frightened or furious character draws
      a different social action from a calm one.
- [x] **The steering is a modifier, never a gate.** A gated action stays gated
      however strongly you feel; the band and the traits still dominate.
- [x] Every affinity names a real dimension — two of the first eight did not, and
      those rules could never have fired.
- [x] Mechanism tests *and* an emergence test (the distribution actually shifts),
      in `tests/test_affect_model.py` (23 tests).

## Implementation — 2026-10-02 (WT-characters-engine)

### What was already true, and was checked rather than assumed

The model itself is good and widely written to. Before changing anything, the
four AGENTS.md wiring checks were run on the obvious candidates:

| check | result |
|---|---|
| is anything calling it? | `frightened` → affect map **yes** (`engine/conditions.py` → 10.0). `spike_emotion` → 10+ callers. `felt_from_llm` → **zero production callers**. |
| reading the right object? | the map is on `Player`, read via `emotions_map()` — consistent |
| has anyone authored data? | yes, extensively |
| can the guard's lookup ever match? | see the two defects below |

So the model did not need building. Two things did, and both were provable
without reading a file end to end.

### Defect 1: a declared feeling was normalised two different ways

`handle_spike_emotion` used `map_label`, which **substring-matches**.
`felt_from_llm` existed specifically to avoid that — its docstring says so — and
had no production caller at all.

```
label       felt_from_llm (strict)   map_label (what the route used)
hangry      None                      angry        <- coincidence
terrified   None                      afraid       <- declared alias, dropped
furious     None                      angry        <- declared alias, dropped
tired       None                      melancholic  <- declared alias, dropped
```

Two failures from one cause: the live path invented a feeling from a typo, and
the strict path rejected the module's own authored vocabulary. `felt_from_llm`
consulted only `BASELINES` and never `LABEL_TO_DIM` — which is why
`set_emotion("terrified")` worked (it reads the alias table) while the LLM route
refused the same word.

Fixed by consulting `LABEL_TO_DIM` before the semantic bridge, and by routing
the endpoint through the strict normaliser. `hangry` is now ignored rather than
read as `angry`, which is the behaviour task-505 asked for and the loose path
has been silently defeating since.

The eleven axis names (`sadness`, `anger`, `shame`, …) were also added to
`LABEL_TO_DIM`. `map_label` has always resolved them — but only by inverting
`AXIS_TO_EXPRESSION`, the **expression art** table, which is a different concern
that happens to share eleven names. Those names now sit next to `terrified`,
where an author can see them.

### Defect 2: the feeling never caused behaviour

The goal says the state "steers behaviour and shapes social interaction".
Measured: **eleven** systems write the affect map and **one** reads it
(`engine/derive.py`, for consent). `background_social.py` writes emotions —
`TIER_EMOTION`, `TIER_TARGET_EMOTION`, `FEAR_COSTS` — and read none. A character
who had just been frightened drew from an identical table to one who had just
been complimented: the feeling was a *consequence* of behaviour and never a
*cause* of it.

`action_weights` already modulates by band, traits and vitals, so it is the right
seam and the change is a few lines in a table that already exists. Each action now
declares the affect axes it **expresses**, and a character feels their way to the
draw.

### The three constraints on the steering

1. **A feeling re-weights what is on offer; it never opens a gate.** A frightened
   character does not become willing to flirt with a stranger — `confide` and
   `flirt` stay at 0.0 however strongly the matching axes are raised. This is what
   keeps social behaviour readable rather than mood-contingent.
2. **Only a *raised* axis counts**, and the bar is the same
   `emotion.expression_margin` that decides a label counts as a feeling — so the
   label a reader sees and the axes behaviour reads cannot disagree, and a
   baseline that sits above zero does not make a character permanently feel it.
3. **The strongest matching axis decides, not the union.** A character 20 angry
   and 60 afraid gets `afraid`'s full tilt on `apologise` and only a quarter of
   `angry`'s on `bully`, rather than both at full strength.

### A rule that could never have fired

The first draft of `AFFECT_AFFINITY` named `amused`, `hopeful`, `defiant` and
`mischievous`. `defiant` and `mischievous` are **labels** that map into
`angry`/`excited`; `amused` and `hopeful` are neither dimensions nor declared
labels anywhere. Two of the eight affinities were dead on arrival, and nothing
would have said so. `test_every_affinity_names_a_real_dimension` now does.

### The honest magnitude

An angry character bullies **10.6% → 15.2%** of draws (1.44×), not 2×: `bully`
competes against seven other actions, so multiplying its weight by `AFFECT_TILT`
moves its share by less than that factor. The test asserts 1.3×, which is the
measurement, and the docstring says why it is not 2 — asserting a stronger
mechanic than the one that ships would be asserting something untrue.

### Not done here

- **`background_plans` was left alone.** It is the other obvious place a feeling
  could steer behaviour, and the plan layer is **entirely unexercised** — there
  is not one authored `plan` node in `data/`. Wiring a behaviour modifier into a
  layer with no content would have produced a rule that could not be observed, and
  per AGENTS.md §8 the content comes first.
- **Narration and expression art** were already reading the map
  (`dominant_expression`, `character-art.js`) and are untouched.
- **No new affect dimensions.** This task is about the model being *one* model and
  *used*, not about there being more axes.

### Verify

```
python -m pytest tests/test_affect_model.py -q                             # 23 passed
python -m pytest tests/test_emotion.py tests/test_emotion_semantic_bridge.py -q
                                                                          # 83 passed
python -m pytest tests/test_background_social.py tests/test_social_approach.py \
  tests/test_social_company.py tests/test_background_simulation.py \
  tests/test_background_agendas.py tests/test_background_plans.py \
  tests/test_background_recreation.py tests/test_background_relief_and_washing.py \
  tests/test_background_consumption.py tests/test_background_preparation.py -q
                                                                          # 122 passed
```

The 122 social/background tests passing **with** the new behaviour is the point:
the change is invisible to a character who is not feeling anything, and every
existing expectation about one who is still met.

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty.

### Live verification — 2026-10-02, `python app.py` on `VW_PORT=4466`

**1. A declared alias now lands.** It was dropped before:

```
POST /api/players/Kaelen%20Voss/emotions {"emotion":"terrified","intensity":8,"delta":40}
GET  /api/state   ->  afraid 10.0 -> 50.0
```

`terrified` is a declared alias of `afraid` in `LABEL_TO_DIM`;
`set_emotion("terrified")` had always worked, and the LLM route refused the same
word.

**2. And the coincidence is refused.** Same endpoint, same character:

```
POST /api/players/Kaelen%20Voss/emotions {"emotion":"hangry","intensity":8,"delta":40}
  -> {"ignored": "hangry"}
GET  /api/state   ->  angry 8.0 -> 8.0   (unchanged)
```

Before this change that same request moved `angry` by +40, because the route
substring-matched "hangry" containing "angry" — the exact failure task-505 was
filed to prevent.

**3. The feeling reaches behaviour.** Same seed, only the affect map differs, 600
draws each from `choose_action`:

```
  calm    bully=0.083  apologise=0.090
  angry   bully=0.135  apologise=0.077
  afraid  bully=0.080  apologise=0.125
```

Angry raises bullying and lowers apologising; afraid raises apologising and leaves
bullying alone. Neither is a switch — the calm character still bullies 8% of the
time, because the relationship band and the traits still decide.

Live world returned to its prior state afterwards (`afraid` restored to its
baseline 10.0).


