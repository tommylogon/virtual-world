---
type: task
status: review
area: ui
priority: medium
---

# task-448: Disambiguate an ambiguous target name/nickname

**Filed:** 2026-09-22
**Related:** task-446 (id-first node identity), task-447 (character nicknames),
`engine/matching.py` (`_match_character_name` returns `(None, candidates)`),
`routes/action_handlers.py`, `static/js/agent/human-turn-composer.js`

## Why

When a spoken name matches more than one character — two people called "Violet",
or two sharing the nickname "Vi" — the engine must **ask**, not guess. The matcher
already detects this and returns candidates (`name is None, candidates=[...]`),
but the prompt lists bare names (or internal keys), so "Violet or Violet?" is
unanswerable.

This is normal authoring, not an edge case: families share surnames and nicknames,
and populated worlds reuse generic names (task-357, task-446).

## Scope

- When `_match_character_name` (and item/exit equivalents) reports ambiguity,
  render a **chooser** that shows, per candidate: display name **plus a
  distinguishing detail** — description / `unknown_display_name()` / current
  area / a visible item — using the identity key as the value.
- Accept the choice and resolve it to the identity key so the action targets the
  chosen character (relationships, grapple, give/take, attack all use the key).
- Works in both the text command path and the human turn composer / inspector.
- Never auto-pick when the candidate set is ambiguous.

## Acceptance

- [x] When `_match_character_name` reports ambiguity, the action route emits a
  **chooser**: a readable list where each candidate is its display name plus a
  **distinguishing detail** (appearance label `unknown_display_name()`, else a
  short description, else the current area), plus a structured `choices` payload
  `{verb, options:[{key,label,detail}]}` on the `/api/action` response.
- [x] Picking a candidate resolves to the **identity key**. The chooser dispatches
  `verb key:<key>`; `_match_character_name` has an explicit `key:` tier so a
  duplicate whose key equals its display name ("Violet") is still targetable
  without making a bare "violet" unambiguous. An unknown `key:` resolves to no
  match, never a guess.
- [x] Works in the **text command path** (route + matcher) and the **event
  stream / human turn**: `EventStream.logChoices()` renders one button per
  candidate and the click re-runs the corrected action; `agentEngine` renders it
  after a human action and the HTC interject path renders it too.
- [x] **Never auto-picks** while the set is ambiguous — the bare name still
  returns `(None, candidates)`.
- [x] Ambiguity is now also detected for `grab` and `lead` (previously `grab`
  silently fell through to item-taking, `lead` said "no one by that name").

## Non-goals (unchanged)

- Authoring the nicknames themselves (task-447).
- Duplicate-name storage (done, task-446).

## Verification (2026-10-02)

Backend integration (`create_app` + two same-display-name "Violet"s):

```
python -m pytest tests/test_ambiguous_target.py tests/test_matching.py -q -> 71 passed
  test_ambiguous_attack_returns_a_chooser_not_a_pick:
    choices[0].verb == "attack"; options' keys == both Violet keys;
    all labels "Violet", all details present; output contains "Do you mean".
  test_key_target_from_the_chooser_hits_exactly_that_character (monkeypatch):
    "attack key:Violet" (the first duplicate, key == display) -> no choices,
    _player_attack received exactly that key.
```
Targeted regression (matching/actions/grapple/skills/checks): 188 passed.

Live browser (`VW_PORT=4463`, Playwright; chooser logged then buttons clicked):

```
CHOOSER buttons ["Violet — a woman in a green cloak", "Violet — a woman in a red dress"]
        titles  ["Target Violet", "Target Violet__d4e5f6"]
click 2 -> ApiClient.action "attack key:Violet__d4e5f6"
click 1 -> ApiClient.action "attack key:Violet"
```

Screenshot: `review-verify/448-chooser.png` (two labelled buttons in the stream).
JS units 491 passed; `npm run lint` / `npm run typecheck` clean.

## Files

- `engine/matching.py` — `key:` identity tier, `character_candidate_details`.
- `virtual_world_engine.py` — forward `character_candidate_details`.
- `routes/action_handlers.py` — `note_ambiguity` (attack/grab/lead/intimacy),
  `choices` on the response.
- `static/js/event-stream.js` — `logChoices`.
- `static/js/agent-engine.js`, `static/js/agent/human-turn-composer.js` — render
  the chooser.
- `tests/test_matching.py`, `tests/test_ambiguous_target.py`.

## Follow-up (2026-10-02): `lead` was a broken verb

Review caught that the ambiguity guard I added to `lead` was incomplete: it set
`lead_ambiguous` and left `target_player` as `None`, then fell through to
`elif target_player.current_area`, so `lead violet` raised `AttributeError` and
the route returned **500 with the chooser discarded** — the exact opposite of
"ask, never guess". `attack`/`grab` were guarded; `lead` was not, and my
integration test only covered `attack`.

Now the null check owns the whole branch, so an ambiguous `lead` returns the
chooser like every other verb. Two regression tests
(`test_ambiguous_lead_offers_the_chooser_instead_of_erroring`,
`test_lead_by_key_reaches_the_chosen_character`) pin both the non-500 and the
key-target path; `tests/test_ambiguous_target.py -> 4 passed`.


