---
type: task
status: done
area: gameplay
priority: medium
---

# task-470: Skill-checked foraging in the soak tier

**Filed:** 2026-09-23
**Related:** task-468, task-469, task-399, task-464

## Goal

Finding something tucked away in the soak tier is a Perception check rather than a guarantee, so outcomes vary by character: a perceptive forager eats from a larder where a clumsy one searches, misses, and moves on. Open-area resources and carried food stay automatic (maintenance, not a puzzle); a miss costs the search time but not the item, so survival is not made flaky.

## Acceptance

- TODO

## Progress 2026-09-23 — done (review)

- [x] `BackgroundSimulation._requires_search(node)` — true only when the item sits
  inside/on another **item** (basket, larder, bush) via a reachable relation.
- [x] `_forage_check(p, kind)` — `Perception` vs `DC 10`, swapped to the acting
  character and restored after; fails **open** if the skill system is unavailable.
- [x] A miss writes a `forage:fail` trace + log line and spends a new
  `forage` task (5 min, `ACTIVITY_INTERRUPTIBLE`/`LABELS`/`SKIP_TURNS`), and the
  item is **not** consumed; `served` blocks a same-frame retry so the character
  heads elsewhere next.
- [x] Open-area resources, natural water and carried food stay automatic. This is
  deliberate: a camp that starves beside a visible stew is not the game we want,
  and it keeps the existing soak survival numbers stable.

## Design note

A world can therefore starve a poor forager *only* of hoarded food. If blanket
foraging difficulty is ever wanted, the knob is `FORAGE_SKILL` / `FORAGE_DC`.

## Verification

`python -m pytest tests/test_foraging.py -q` → 5 passed. Targeted background/soak/
timeskip regression → 133 passed.

## Review 2026-09-23 - closed

Verified: `tests/test_foraging.py` -> 5 passed, plus the 289-passed chain slice. No open bullets; the design note is intentional and the difficulty knobs (`FORAGE_SKILL` / `FORAGE_DC`) stay documented in the file. Closing.