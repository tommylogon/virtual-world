- `tests/test_grapple.py`
## Aliases + judge-locus (impl. today)

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