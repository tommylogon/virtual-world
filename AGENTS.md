# AGENTS.md

Project guidance for automated agents working in this repo.

## Where things live

- **Backend**: `app.py` (Flask factory `create_app`), `engine/` (game systems),
  `routes/` (`*_ops.py` holds the logic; thin `routes/<x>.py` files only register
  URLs), `graph.py`, `virtual_world_engine.py`, `player.py`, `area.py`.
- **Frontend**: `static/js/` (plain-DOM helpers and Lit modules),
  `templates/index.html` (script tags and modals live here, not `static/`).
- **Content**: `data/` (saves, scenarios, `data/library/<type>/` registries),
  `docs/virtualWorld/` (design docs and the dev-task tree).
- `tools/` holds one-off scripts and the dev-task helper below.
- Ignore `.kilo/worktrees/` (managed git worktrees) when searching.

## Commands

- Tests: `python -m pytest -q` (full suite, a few minutes).
  Targeted: `python -m pytest tests/test_<name>.py -q`.
- JS unit tests, browser-global modules in a Node sandbox (no server needed):
  `node tools/unit/run.cjs` (or `npm run unit`). Drop a `tools/unit/test_<name>.js`
  next to the others and it is discovered automatically; the runner's module list
  at the top is where a module under test gets loaded. **Run this before committing
  a front-end change** - it is not part of `npm run lint`.
- JS module contract guard: `python tools/js_module_index.py --check` fails when a new
  module lacks its `@module`/`@contributes` header; regenerate the index with `--write`.
- JS lint: `npm run lint`. JS typecheck: `npm run typecheck` (see
  `docs/design/typescript-migration.md`).
- Export-log lint (regression guards over play sessions, no server needed):
  `node tools/log_lint.cjs data/exports/<log>.txt` (or `npm run loglint -- <path>`).
  Run it on the latest export before tagging/committing a release.
- Run the app: `python app.py`.

### Known pre-existing failures (NOT caused by your change)

- `tests/test_mcp_*.py` fail with `'function' object has no attribute 'fn'`
  (FastMCP tool-wrapper mismatch in the environment).
- `tests/test_social_company.py` and `tests/test_tick_time_scaling.py` have known
  failures.

Baseline is roughly **60 failed / 3239 passed**. Do not try to "fix" these unless
explicitly asked; compare against the baseline instead.

## Dev tasks (todo / inprogress / review / done / cancelled)

Task and bug files live under `docs/virtualWorld/dev_tasks/<status>/<area>/`.
The **folder is authoritative** for status; the `status:` frontmatter is
advisory. Filenames are `task-NNN-slug.md` / `bug-NN-slug.md`.

Do not hand-number, hand-move, or hand-check these. Use the helper:

- `python tools/tasks.py next-id [--kind task|bug]`
- `python tools/tasks.py new --area <area> --title "..." [--kind task|bug] [--priority medium] [--status todo] [--related "..."] [--goal "..."]`
- `python tools/tasks.py move --id N [--kind task|bug] --status review`
- `python tools/tasks.py list [--status ...] [--area ...] [--kind ...]`
- `python tools/tasks.py validate`

Areas: `bugs`, `characters`, `conditions`, `docs`, `gameplay`, `graph`, `items`,
`library`, `refactor`, `testing`, `triggers`, `ui`, `world`.

Workflow: `new` when filing a task, `move` it as it progresses
(`todo` -> `inprogress` -> `review` -> `done`), and `validate` after filing or
moving several. `validate` also flags dangling `Related:`/`Blocks:` references.

## Conventions

- **Backend data operations key nodes by id.** Names are user-facing and resolve
  to ids through `engine/matching.py`. Do not use a display name as a storage
  key. Player identity: `engine/player_manager.py` (`task-446`).
- Follow the existing `*_ops.py` + thin registrar split when adding routes, and
  add the `<script>` tag in `templates/index.html` when adding a JS module.
- Do not edit `.kilo/agent-manager.json` directly; it is managed UI/recovery
  state, not an API.
- Only commit when explicitly asked.
