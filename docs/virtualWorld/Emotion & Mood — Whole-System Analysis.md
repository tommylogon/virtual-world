# Emotion & Mood — Whole-System Analysis

A survey of every mood- and emotion-related thing in the repository, gathered on
2026-09-30 from four passes over the engine, the data, the frontend and the task
tree. It is a **map, not a proposal**: what exists, where it is, who writes it,
who reads it, and which copies can disagree.

Read `[[Characters/Emotion & Affect System|Emotion & Affect System]]` first for
*how it works*. This document is *how much of it there is*, and which parts of it
are two things.

Every claim carries `file:line`. Counts marked **verified** were measured
directly rather than read from a comment; see [Method](#method) at the foot.

---

## The finding

**There are two emotion models in this application, they write to different
fields, and nothing synchronises them.**

| | legacy | current |
|---|---|---|
| field | `Player.emotion` (a string) + `emotion_intensity` | `Player._emotions` (a dict of 36 floats) |
| shape | `"afraid", 0.8` | `{"afraid": 62.0, "anxious": 20.0, ...}` |
| vocabulary | **7** labels | **36** dimensions, 70 keyword aliases |
| written by | `set_emotion()` | `spike_emotion()`, `decay_emotions()` |
| decays | **no** — set outright, forever | drifts to per-dimension baselines |
| serialised at | `engine/serialization.py:157-168` | same call, alongside |
| selects the face | no | **yes** — `dominant_expression()` |
| live? | yes | yes |

`set_emotion("afraid", 0.8)` writes the legacy field. `spike_emotion("afraid", 20)`
writes the affect map. A character can be `afraid: 90` on the map and `"happy"`
in the string, and every downstream reader takes one or the other.

This is not a plan that changed. task-96 built the affect map to *replace* the
single slot, and the replacement's read paths shipped while the write paths kept
calling the old one. `Emotion & Affect System.md:42` says so in as many words —
*"The map is much richer than the old 7"* — and
`Characters/Characters Overview.md:171-178` still documents the superseded
seven-value model without saying it is superseded.

---

## The vocabulary ladder

One concept, **six vocabularies**, of five different sizes. This table is the
single most useful thing in this document.

| size | vocabulary | defined at | used for |
|---|---|---|---|
| **7** | `neutral happy sad angry afraid surprised disgusted` | `player.py` allowlist (see `set_emotion`) | the behaviour-editor dropdowns: `set_emotion` action and `npc_emotion_is` condition, `inspector/behaviors-view.js:486-494, :962-969` |
| **11** | `happy sad angry afraid surprised disgusted aroused affectionate ashamed envious calm` | `engine/emotion.py:71-76` `AXIS_TO_EXPRESSION` | the art keys the engine picks between |
| **12** | the same 11 **plus `neutral`** | `character-art.js` `CANONICAL`, `inspector/helpers.js:379-386` `EXPRESSION_ORDER` | expression-pack slots an author fills |
| **36** | affect dimensions | `engine/emotion.py:28-51` `BASELINES` | the affect map's keys |
| **70** | keyword labels → dimension | `engine/emotion.py:138-159` and `static/js/shared/emotion-mapper.js:26-47` | resolving free text from an LLM, a memory or a trigger |
| **~50** | grouped free-text labels | `inspector/memory-view.js:17-26` `EMOTION_GROUPS` | the memory editor's picker, and the vocabulary fed to the memory generator's prompt |

**Verified:** the 11 and the 12 are equivalent, and the difference is exactly
`neutral` — which is the client's *fallback* art key, correctly not something the
engine has to name as an emotion. That pair is fine.

**Not fine:** the 7 is what an author picks from when scripting behaviour, and the
36 is what the character actually feels. A `set_emotion` action can only reach 7 of
36, and it sets the field that does not select the face.

---

## How emotion is produced

| path | what it writes | where |
|---|---|---|
| behaviour action `set_emotion` | **legacy** field | `triggers/behaviors.py:269-273` |
| social outcome tiers | **legacy** field, on both parties | `background_social.py:525-528` |
| heuristic outcome text matching | **legacy** field | `Player.update_emotion_from_outcome()` `player.py:508-541` |
| `/emotions/map` route | affect map + mental vitals + relationship drives | `routes/player_ops.py:92-204` |
| fear reaction | affect map (`afraid` spike, +6…+11) | `background_social.py:1115-1142`, `engine/fear.py` |
| `broadcast_emotion` | affect map | task-391, in review |
| per-tick decay | drifts every dimension toward its baseline | `emotion.decay()` `:293-304` ← `tick_manager.py:622-623` |
| derived from vitals | builds a whole affect map when nothing is set | `emotion.derive_from_vitals()` `:317-380` |
| **from an LLM** | — | — |

**`felt_from_llm()` exists at `engine/emotion.py:618` and is called by nothing but
two tests.** It is the function that would take a model's `{"label", "intensity"}`
and resolve it to a dimension and a spike — the natural bridge from narration to
the affect map — and it is unwired. `task-537:219` records the same gap from the
other end: *"there is no effect that sets a character's canonical `emotion` string
outright. emotins are in need of a bigger rework."*

**Verified:** of the six production write paths, **five write the legacy field**
and one writes the map. The face follows the map. So the most common way to change
a character's emotion does not change their face.

---

## How it is read

**The face the player sees follows the affect map**, not the legacy label:

```
dominant_expression()                     engine/emotion.py:79-110
  → player.emotion.expression            serialization.py:163-164
    → CharacterArt.emotionKeyFor()       character-art.js:83-90   (expression first,
                                                                      then `current` if
                                                                      canonical, else neutral)
      → avatarFor()                      character-art.js:38-58
        → agent-lens.js:83-94 · turn-scene-view.js:359-376
```

**The legacy label is shown as text** in the world export
(`world-export.js:89`) and as memory-emotion badges
(`memory-view.js:53-57`). It does not select art.

**Prompts and behaviour:**

- `emotions_description()` `player.py:467-484` — a first-person mood paragraph,
  from the explicit map if it is deviant, else derived from vitals. This is what
  an LLM reads about how a character feels.
- `engine/derive.py:38-48, :184-200` — an interpersonal affect profile
  (trust, fear, attraction, disgust, respect, familiarity) reduced to `consent`,
  `moodToward`, `role` and a summary. **`moodToward` is the only thing in the
  codebase called a mood**, and it is a derived number for the relationship UI, not
  a state.
- `conditions.frightened_block` `engine/conditions.py:133` gates combat
  (`combat.py:157-158`), movement (`movement.py:433,634`) and item use
  (`items/take_drop_actions.py:598`, `items/use_actions.py:80,270`).

**"Mood" as a word** means the *derived narrative state* — the paragraph, the
dominant expression, `moodToward`. **There is no stored `mood` field anywhere.**

---

## The duplication register

Four copies of the same fact. Status **verified** by measurement, not by reading.

| # | what is duplicated | server | client | in sync? | guarded by a test? |
|---|---|---|---|---|---|
| 1 | keyword label → dimension | `emotion.py:138-159` | `emotion-mapper.js:26-47` | **yes — 70/70 labels, 0 divergent** | **no** — `tests/test_emotion_semantic_bridge.py:278-282` compares only the 36 *dimension* set, never the 70 labels |
| 2 | semantic anchor phrase per dimension | `emotion.py:445-465` | `emotion-mapper.js:50-65` | **yes — 36/36** | yes, same test |
| 3 | which emotion an axis shows | `emotion.py:71-76` | `character-art.js` `CANONICAL` | **yes** (11 vs 11 + `neutral`) | no |
| 4 | expression key order for authoring | — | `helpers.js:379-386`, `sprite-sheet.js:30-32` | client only, two copies | no |

Entries 1 and 3 are the same bug waiting for a reason to disagree, and nothing
would notice. The honest framing: **these are in sync today by luck and by
discipline, not by construction.** One label added to the Python map and not the
JS one resolves differently in the browser than on the server, silently.

Entries 1–2 are commented as mirroring each other (`emotion.py:442-444`,
`emotion-mapper.js:5-6, :19`) — the intent is documented, the enforcement is not.

---

## Contradictions already written down

Not found by this survey — these are in the repository's own files.

- **36 vs 35 dimensions.** `Emotion & Affect System.md:42` says 36; `task-537:87`
  says "35 affect dimensions". **Verified: 36.** The task file is stale.
- **12 vs 11 expression keys.** `Character Images & Expression Packs.md:24-25`
  says 12, `Inspector Panels.md:115-116` says 11. **Verified: 11 engine, 12
  client, difference is `neutral`.** Both are defensible; neither says so.
- **"there is no effect that sets a character's canonical `emotion` string
  outright. emotins are in need of a bigger rework"** — `task-537:219`.
- **"The emotion vocabulary is slated for a reword/expansion pass … written
  against a moving target"** — `task-537:89-90, :384-385`, echoed at
  `task-391:861-862`. **No task file owns this pass.**
- **"`set_emotion` allows only 7 emotions"** — `task-391:822`, against the 36-dim
  map.
- **"`npc_emotion_is` doesn't round-trip in the graph editor"** — `task-388:238-240`.
- **"does not explain … the emotion list — where `happy`, `attack`, `fear` etc.
  come from, whether they must match an engine emotion, or what happens to a
  character whose current emotion has no slot"** —
  `live-audit/README.md:2049-2051` (audit §39, not yet filed).
- **"Does the prose `personality` field stay? … what happens when they disagree"**
  — `task-600:62-66`.
- **"nothing to tune against yet: no fears are being generated at all"** —
  `task-484:14-15`, closed as un-tuneable after a 4,320-tick soak produced zero
  threats. That is an emotion system with no negative input in the wild.
- **task-333 / task-334 (review):** humans have no felt-emotion update and no
  mood line, unlike agents. `Characters/Characters Overview.md` is a **human**
  overview, which is the likeliest reason it still documents the legacy model.

---

## What is planned

| task | proposes |
|---|---|
| task-600 | author the structured personality shape (`likes`/`dislikes`/`fears`/`kinks`/`turn_offs`) — five shipped mechanics are unreachable because nothing writes them. Blocked on task-601. |
| task-512 | move the Expression Pack into its own Images tab |
| task-445 follow-ups | the action keys are stored but **nothing drives them**; the graph thumbnail is still a static `neutral` |
| task-537 §G, task-391 | the vocabulary reword/expansion pass — **referenced as a plan by two cards and owned by none** |
| task-545 / 546 / 487 / 488 | stimulation path tracking, frustration, exhibitionist, single-track — all sit downstream of `Stimulation`, and all are `todo` |
| task-404 | emotional impact and `personality_deltas` as first-class data — and its six most evocative fields are silently dropped by the only loader it names |

---

## What I would do, in order

1. **Decide which model is the one.** Not "fix the sync" — decide. The affect map
   is strictly richer, decays, drives the face, and 36 > 7. The legacy field
   survives because four production write paths still call it. Pick one, then
   route the four to it. Everything below depends on this answer.
2. **Put a test on the two maps.** Compare all 70 label→dimension pairs, not just
   the 36 dimension names. It is the cheapest guard in this document: one assertion
   that reads both files and diffs them, and it converts a latent split into a
   caught one.
3. **Wire `felt_from_llm`.** It is written, tested, and called by nothing. It is
   the bridge from what a model says a character felt to the map that decides the
   face — which is why emotion is currently set by string-matching an outcome
   (`Player.update_emotion_from_outcome`) rather than by anything the model said.
4. **Widen the behaviour dropdowns, or say why not.** Seven reachable emotions out
   of thirty-six is the seam an author actually touches, and it writes the field
   that does not select art.
5. **Then** the vocabulary reword pass — and give it a card, because two other
   cards are blocked waiting for it.

**Deliberately not recommended:** deleting `Characters Overview.md`'s legacy
description. If humans have no felt emotion (task-333/334), the legacy field is
currently the *only* emotion state a human has, and the document is right about
the model that is actually running for them.

---

## Method

Four read-only passes, then every number that mattered measured directly:

- engine, Python: emotion model, drives, decay, fear, the LLM bridge;
- engine, JavaScript: art selection, mappers, inspector authoring, display;
- `data/`: expression packs, shipped characters, the vocabulary in data;
- `docs/` and the task tree: what is planned, and what contradicts what.

**Verified by measurement** (not read from a comment): the 36 dimensions, 70
labels and 11/12 art keys above; and the server/client map comparison, which found
**zero** divergence — a correction to the expectation that these two copies had
already drifted. They have not, and nothing enforces that they cannot.

**Not established, and said so rather than guessed:** the runtime presence of
`Comfort` and `Satisfaction` (they appear in the polarity registry and nowhere
else); and whether any world actually exercises the fear path, which task-484's
4,320-tick soak says it does not.
