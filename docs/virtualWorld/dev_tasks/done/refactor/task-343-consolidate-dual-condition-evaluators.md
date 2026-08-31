# task-343 â€” Consolidate the two divergent condition evaluators into one

**Status**: Todo â€” filed 2026-08-27 from code review. Priority: do BEFORE the
16-condition sweep (todo/conditions/*) â€” otherwise every new condition must be
implemented twice to behave consistently.

## Found

Two near-complete parallel implementations of trigger-condition evaluation:

1. `engine/triggers/condition_tree.py::_evaluate_conditions` â€” ~25 leaf types,
   string-keyed if/elif chain. Used by the main trigger system.
2. `engine/triggers/evaluation.py:91` `_evaluate_trigger_condition`
   (EvaluationMixin) â€” duplicates nearly all leaves; used ONLY by
   movement.py:328 (`requires_open`).

They already disagree: `random_chance` always Ã·100 in evaluation.py:216 vs
heuristic handling in condition_tree.py:111-118.

Dead copy-paste inside condition_tree.py itself: `sound_heard`
(:180-201) and `speech_matches` (:203-220) are re-implemented VERBATIM later
in the same elif chain (:454-494) â€” unreachable branches that will rot first.

## Goal

One evaluator, one leaf registry:

- Deletable: evaluation.py's duplicated leaves (delegate to condition_tree or
  a shared leaf-dispatch table), and the dead :454-494 block.
- New conditions register once (ideally data-driven like effect_handlers â€”
  10 modules + registry merge pattern is proven here).
- `random_chance` semantics pinned by unit test so the divergence can't
  silently return.
- movement.requires_open keeps behavior: same results on a mansion-style
  scenario before/after (golden compare over test_world scenarios).

## Verify

pytest suite green; new test asserting both call paths give identical answers
for a fixture matrix of every leaf type incl. random_chance (seeded).


