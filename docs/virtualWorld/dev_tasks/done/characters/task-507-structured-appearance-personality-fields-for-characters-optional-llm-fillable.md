---
type: task
status: done
area: characters
priority: medium
---

# task-507: Structured appearance & personality fields for characters (optional, LLM-fillable)

**Filed:** 2026-09-24
**Related:** task-96, task-505

## Goal

Add OPTIONAL structured appearance/personality fields to characters, alongside the existing prose. Two authoring modes must both work: (a) prose-only (personality + base_description), or (b) full structured fields. Curated, mechanic-backed set only: appearance {height_cm, weight_kg, build, hair{color,length,style}, eyes{color}, skin{tone}} and personality {likes, dislikes, fears, kinks, turn_offs}. Reference other entities by id (never display name). After fields are set, run 'generate description' ONCE to render prose (description already auto-generates from base_description + equipment, so structured fields feed it); structured is source of truth where present, prose is the narrative layer and stays the LLM voice. LLM-fill flow: send the model the JSON schema of all fields plus the character card/personality/description and have it populate them; the rest hand-authored. Mechanics to unlock: contact lenses set hair/eyes, haircut, weight gain/loss (Hunger/traits/items), kinks -> arousal spike, turn_offs -> disgust / negative arousal (maps to engine.emotion axes), likes/dislikes/fears -> targeting by gifts/threats/dialogue. Reuse graph-editor (WorldGraph) field names where they overlap so authored persons import cleanly. Fields optional + defaulted, so existing prose-only library characters and saves are unaffected (migration). Grow per-feature; do not dump the full editor catalog (media/mbti/alignment have no runtime mechanic).

## Acceptance

- TODO

## First slice — 2026-09-28 (WT-C)

The task says "grow per-feature; do not dump the full editor catalog", so this
is the first slice: the schema, the optionality, the render-prose-once flow, and
**one** mechanic proven end to end. Everything else stays unbuilt on purpose.

### Where it lives, and why

**On the character graph node**, not on the `Player`. Adding a Player attribute
means `player.py`, a hub file. The node is also where task-457 wants the
character definition to end up, so the two tasks point the same way — the
structured block lands on the node and 457's migration carries it for free
instead of it becoming a third place to look.

Consequence, stated plainly: **the library/scenario import path will not carry
this until WT-0 wires it** (`routes/library_ops.py` is a hub). Today the feature
is reachable through the API, not through scenario authoring.

### Files

- `engine/character_appearance.py` — **new**. Schema, validation, storage, prose,
  the mechanic, and the LLM schema.
- `routes/player_ops.py` + `routes/players.py` — four routes (below).
- `tests/test_character_appearance.py` — **new**, 61 tests.

| route | purpose |
|---|---|
| `GET /api/players/<n>/record` | the block, plus the schema, plus rendered prose |
| `PUT /api/players/<n>/record` | validate and store, then render once |
| `DELETE /api/players/<n>/record` | drop the block, restoring prose-only |
| `GET|POST /api/players/<n>/affect` | affect deltas for a stimulus id |

### Decisions worth naming

- **References are ids, never display names**, enforced by a slug pattern.
  A display name is a presentation choice: a rename silently orphans every
  reference, and two characters may share a name. Ids resolve to names only at
  the display edge, and an id that will not resolve **stays visible** rather than
  disappearing — a kink that quietly vanishes is a bug report with no cause.
- **Rejection beats silent dropping.** A bad entry fails the whole field with a
  400 naming the offender. A character who mysteriously does not respond to a
  kink is far harder to notice than a rejected request.
- **Prose-only is the normal case, not a half-configured one.** No record means
  `{}`, empty prose, no affect — a library character reads and renders exactly as
  before. A test pins that.
- **The route will not clobber a hand-written `base_description`.** The task
  makes structured the source of truth, but replacing a paragraph someone wrote
  by hand is not a decision a PUT endpoint gets to make silently.
- **A structured *personality* renders no prose.** Personality is not appearance,
  and a kink must not end up in a visual description.

### The one mechanic

`affect_for_stimulus(node, stimulus_id)` — a kink raises arousal, a turn-off
raises disgust/anger/fear and pushes arousal down, mapping onto real
`engine.emotion` axes. Returns `{}` for an unknown stimulus, a prose-only
character, or a character who is simply neutral, so a trigger can apply the
result unconditionally. A test drives the deltas through `emotion.spike` and
asserts the character actually moves.

**A sign bug worth recording.** The first cut had one `AFFECT_AXES` table and
applied turn-offs with a negated sign. Negating turns "disgust up, arousal down"
into "disgust down, arousal up" — the exact opposite of a turn-off — because the
sign of an axis is *semantic* here, not an arithmetic consequence of which list
it came from. Now two tables, `KINK_AXES` and `TURN_OFF_AXES`, with no sign
flipping. A test pins that a turn-off raises disgust and lowers arousal.

`fears` shares its id vocabulary with task-552's `fear_tags`; `likes` /
`dislikes` are present with their stated mechanic (gift and dialogue targeting)
but no consumer is wired yet, which is the honest state of a per-feature slice.

### Handed to WT-0

- **`routes/library_ops.py`** — import and export the structured block, so a
  scenario can author it. Until then the feature is API-only.

### Not built, deliberately

The rest of the task's list — contact lenses / haircut / weight-change as
mechanics, the likes/dislikes targeting consumer, and a graph-editor field-name
alignment — each needs its own slice. `media` / `mbti` / `alignment` are absent
and a test asserts they stay absent.

### Verify

`python -m pytest tests/test_character_appearance.py -q` — 61 tests. Prose-only
is the default and is pinned; validation rejects display names, unknown keys,
implausible numbers and non-object groups; storage sets/replaces/clears without
touching the Player; prose renders every appearance field (a field that cannot
reach the prose has no purpose, and there is a test per field); the mechanic
raises arousal for a kink and disgust for a turn-off and reaches the affect map;
the schema covers exactly the curated set; and the four routes round-trip.
