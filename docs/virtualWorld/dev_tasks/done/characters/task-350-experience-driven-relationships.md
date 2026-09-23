---
type: task
status: done
area: characters
priority: high
---

# task-350: Experience-driven relationships

## Outcome (verified 2026-09-21)

Closed. **This file is a work log, not a spec** — it was filed with no
frontmatter, a stray orphaned bullet as line 1, and outcomes written in the past
tense rather than deliverables. Every artifact it names exists:

- `_resolve_other` alias/description resolver: `routes/player_ops.py:203`,
  used at `:43` and `:166`, with the drop-rather-than-mis-attribute guard at
  `:162-170`; tested at `tests/test_derive.py:84-112`.
- `engine/derive.py` (`:1` names this task) — the memory → multi-dimensional
  profile reducer (`:159-180`), with `resolve`/`derive_person_profile`.
- Turn-start judge via `includeFeelings`: `static/js/agent/prompt-builder/turn-prompts.js:103,117-118`,
  called for real at `static/js/agent-engine.js:572`.
- `felt_toward` bridge: `player.py:380-383`; response plumbing
  (`learnedNames` / `learned_names` / `emotion_toward`) in
  `static/js/agent/response-parser.js:98,123` and `schema-fragments.js:69-70`.
- Grapple reads the derived profile: `engine/grapple.py:64,77-78`; tested at
  `tests/test_grapple.py:363-367`.

**Relationship to task-420:** task-350 derives a profile *from* the scalar store
(reading `closeness`/`interaction_count`), so the later single-write-path refactor
does not contradict it. Note for future work: the derived profile is keyed by
character **name** via the relationships dict — see the id-not-name convention
(identity_by_id_never_by_name) and task-316 for the id-backed re-key.

## Original work log (kept for the reasoning)

### Aliases (the LLM names people by the handle it SEES)
Heard-name learning was already alias-aware (`engine/speech.py` uses
`node_aliases`). The NEW `/names` and `toward` paths were NOT — they did a raw
`candidate in players`, so `toward:"the man"` would create a bogus relationship
keyed by the label. Fixed with a per-character resolver `_resolve_other` in
`routes/player_ops.py`: exact name -> name-substring -> node alias -> description
word, scoped to the acting character`s own area. Unresolved/ambiguous handles
are DROPPED (the bogus-guard) rather than mis-attributed, so no phantom record.

### The recipient-judge belongs at turn-start, not the react phase
Per the earlier rule, react = react to your OWN action outcome. A feeling *about*
a person is decided when you process what they did/said at the START of the turn
(the `=== WITNESSED ===` block). In the current loop `buildObservationPrompt`/
`buildDecisionPrompt` are defined but NOT called — the real turn-start call is
`buildReactionPrompt`. So the judge lives THERE:
  - non-reactive: already had `emotion_toward` + `learned_names`.
  - reactive: added them (via `includeFeelings`, WITHOUT forcing `memory`, which
    reactive already emits separately) to the think+decide turn-start call.
The react-after-action prompt keeps `emotion` for own-outcome mood; `toward`
there is only secondary (own action involving them).

## Files touched (all phases)
- `engine/derive.py` (new), `engine/grapple.py`
- `player.py`, `routes/player_ops.py`, `routes/players.py`
- `static/js/agent-engine.js`, `static/js/agent/response-parser.js`
- `static/js/agent/prompt-builder/{schema-fragments,turn-prompts,character-state}.js`
- `tests/test_derive.py` (new), `tests/test_grapple.py`