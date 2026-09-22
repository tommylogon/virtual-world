---
type: task
status: review
area: world
priority: high
---

# task-466: Interrupt & relevance evaluator (shared by timeskip, fidelity, soak)

**Filed:** 2026-09-22
**Related:** task-464, task-411, task-418, task-399, task-403

## Goal

One deterministic relevance/interrupt evaluator shared by timeskip actions (task-464), attention/fidelity tiers (task-411/418), soak deferral (task-399) and memory salience (task-403). Given a character and a tick's world deltas plus trace events, decide what they notice and must react to: threat (attack/steal/grapple/hostile approach), vital or condition threshold crossings, involuntary-action firing, discoveries matching interest tags or known goals, arrivals and sounds carried by awareness channels. Emits structured interrupt reasons (why-tags) and never calls an LLM. Stopping at a tick boundary means the post-interrupt state is an ordinary world state.

## Acceptance

- TODO

## Progress 2026-09-22 — engine evaluator landed (review)

`engine/interrupts.py` + `tests/test_timeskip.py` (pure-unit cases).

- [x] `snapshot(gs, player)` / `evaluate(before, after, events, watch_tags, target, intent)` and struct `Interrupt(kind, why, detail, salient)`.
- [x] Death; threat (hostile condition or theft/attack marker in log + turn events); vital danger-band **crossings only** (drives above / resources below / HP); involuntary bladder; discovery by interest tag or name; arrival on travel.
- [x] Consumed by `engine/timeskip.advance` as the interrupt that hands control back.
- [ ] Wire the same evaluator into the attention/fidelity tiers (411/418) and soak deferral (399) — the reason it is shared.
- [x] Events are filtered to the character's area and exclude their own actions; global log lines only count when they name the character, and `HOSTILE_ACTIONS` labels count without a marker. (Otherwise a fight elsewhere could interrupt a skip.)
- [ ] Sound/awareness-channel inputs (task-418) beyond log/turn events.
- [ ] A `salience` consumer for task-403 memory ranking.

## Verification

`python -m pytest tests/test_timeskip.py -q` → 41 passed (11 pure evaluator cases incl. area/actor filtering).
