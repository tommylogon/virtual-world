# BUGBOT.md

Repository rules for Bugbot / Agent Review. Kept short and specific — this
file is loaded into the reviewer's context, so every line must change what it
does.

## Do not report these as findings

These are **known, pre-existing** and are not caused by the change under
review. If a change *touches* one of them, the finding is valid.

- `tests/test_mcp_*.py` failing with `'function' object has no attribute 'fn'`
  (FastMCP tool-wrapper mismatch in the environment).
- Failures in `tests/test_social_company.py` and `tests/test_tick_time_scaling.py`.
- Roughly **60 failed / 3239 passed** is the suite baseline. Compare against
  it rather than expecting green.
- 13 pre-existing JS unit failures in `test_plan_tracker.js` (stale
  expectations). Fix or delete them, but they are not a regression.
- `python tools/tasks.py validate` reports one `duplicate id bug-54` error and
  ~28 warnings, mostly frontmatter `status` drift against the folder. The
  folder is authoritative; the frontmatter is advisory.
- Mojibake in task markdown (e.g. `â€”` for an em-dash) from double-encoded
  UTF-8. `tools/fix_docs_mojibake.py` exists. Do not flag incidental
  occurrences.

## Project invariants a change must not break

1. **One copy of every truth.** Nodes are keyed by id, never by display name
   (`task-446`). One dice path (`engine/checks.py`). Map art position is
   derived from the scope grid plus the scope offset, never hand-nudged. A
   second implementation of a rule is a bug, not a style issue.
2. **Scale is bounded by attention, never by turn length.** The cheap tier
   must always be a *valid but suboptimal* policy, and LLM call count must
   never scale with `time_per_tick_minutes`. Violating this is a correctness
   regression, not polish.
3. **Names are not storage keys.** Names resolve to ids through
   `engine/matching.py` at the boundary.

## Conventions worth checking

- Routes follow the `*_ops.py` + thin registrar split; a new JS module needs a
  `<script>` tag in `templates/index.html`.
- `docs/design/js-module-index.md` is **generated** — regenerate with
  `python tools/js_module_index.py --write`. Never hand it into a commit that
  does not include the modules it names.
- JS unit tests (`node tools/unit/run.cjs`) are **not** part of `npm run lint`.
  A front-end change needs both.
- Ignore `.kilo/worktrees/` when searching.
- `docs/virtualWorld/dev_tasks/` — the **folder** under `<status>/<area>/` is
  authoritative for status. Some task files carry a UTF-8 BOM on purpose.

## Reviewing a change in this repo

- `git status` frequently shows **unrelated in-flight work** (a dirty working
  tree mid-session). Confirm which files the change is actually about and say
  which you excluded.
- Design intent lives in `docs/virtualWorld/*.md` and `docs/design/`. A change
  that contradicts a design doc is a finding; quote the doc.
- `docs/virtualWorld/dev_tasks/critical-review-scale-2026-09-08.md` is the
  reference for how thorough a review here is expected to be.
