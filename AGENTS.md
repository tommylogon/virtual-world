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

`tests/test_tick_time_scaling.py` **hangs** — it does not fail, it never finishes. Always
`--ignore` it or the suite never returns:

```
python -m pytest --ignore=tests/test_tick_time_scaling.py
```

Baseline is **5 failed / 4274 passed**, measured on `master` on 2026-09-28 (~7m30s).
The five:

| Test | Nature |
|---|---|
| `test_character_identity.py::test_collapse_is_idempotent` | canonical-node problem, task-457's |
| `test_character_identity.py::test_kraktooth_loads_as_one_node_per_character` | same |
| `test_scenario_name.py::test_clearing_the_source_leaves_the_name_alone` | scenario source leaks between `create_app()` calls |
| `test_social_company.py::test_extrovert_company_gains_extra` | `create_app()` isolation, bug-55 |
| `test_templates.py::test_generator_covers_every_effect_type` | `data/library/items/template_polymorph_target.json` is missing |

The three in the middle are one bug: **a second `create_app()` in a process does not behave
like the first** (bug-55). The last is a missing data file. The first two are task-457's.

**The old baseline was ~60 failed, and 55 of those were the MCP tests** — which made the
"compare to baseline" rule nearly blind. Those are fixed (see below), so a lane that
reports "at baseline" is now reporting against 5 real failures, not 60.

### The MCP tests were fixed, do not "restore" them

`mcp_server.py` was never broken. **FastMCP >= 3 returns the plain function from
`@mcp.tool()`**, not a wrapper exposing `.fn`, and 62 test call sites still used `.fn()`.
All 69 MCP tests now pass. If they regress en masse, check the installed `fastmcp` version
before suspecting the server.

**Compare the failure *names*, not the counts.** The counts drift as tests are
added, so a matching total proves nothing; a matching set does. Save both
outputs and diff the `FAILED` lines:

```powershell
python -m pytest -q --tb=no 2>&1 | Tee-Object -FilePath mine.txt
git worktree add --detach "$env:TEMP\vw-baseline" master   # a clean checkout
python -m pytest -q --tb=no 2>&1 | Tee-Object -FilePath baseline.txt  # in that worktree
Compare-Object (Get-Content baseline.txt | ? { $_ -like 'FAILED*' } | Sort-Object) `
              (Get-Content mine.txt      | ? { $_ -like 'FAILED*' } | Sort-Object)
```

The two `test_character_identity.py` failures (`test_collapse_is_idempotent`,
`test_kraktooth_loads_as_one_node_per_character`) are the canonical-node
problem task-457 describes; going green there is its natural acceptance.

### Gotchas in a managed worktree

- **Never `git stash`.** Stashes are shared across worktrees, so a stash here is
  visible to every other lane. Rebase or merge `master` in instead.
- **Never `npm install` / run the JS gates in a worktree without checking
  `git status` afterwards.** npm rewrites `package-lock.json`'s `"name"` field to
  the worktree directory name. Revert it: `git checkout -- package-lock.json`.

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
- `python tools/tasks.py index [--clear]` (derived frontmatter cache; only
  needed after an external tool rewrote many files at once)

Areas: `bugs`, `characters`, `conditions`, `docs`, `gameplay`, `graph`, `items`,
`library`, `refactor`, `testing`, `triggers`, `ui`, `world`.

Frontmatter is read as **real YAML** — a list value stays a list, and a value
may contain a colon if it is quoted. `validate` fails on a block that does not
parse rather than quietly ignoring it. Dependency keys are `related`, `blocks`,
`blocked_by`, `supersedes`, `parent`, `children`, `depends_on`; each takes a
list or a bare id:

```yaml
---
status: todo
area: world
blocks: [task-570, task-572]
blocked_by: [task-446]
---
```

Note: some task files carry a UTF-8 BOM; the reader strips it, but a new file
should be written without one.

Workflow: `new` when filing a task, `move` it as it progresses
(`todo` -> `inprogress` -> `review` -> `done`), and `validate` after filing or
moving several. `validate` also flags dangling dependency references.

## Conventions

- **Backend data operations key nodes by id.** Names are user-facing and resolve
  to ids through `engine/matching.py`. Do not use a display name as a storage
  key. Player identity: `engine/player_manager.py` (`task-446`).
- Follow the existing `*_ops.py` + thin registrar split when adding routes, and
  add the `<script>` tag in `templates/index.html` when adding a JS module.
- Do not edit `.kilo/agent-manager.json` directly; it is managed UI/recovery
  state, not an API.
- Only commit when explicitly asked.

### Is this mechanic actually wired?

A mechanic that exists, works, and is never called looks *exactly* like a
mechanic with a low event rate. Three separate instances turned up in one pass,
so check all three before concluding anything from a telemetry table or a soak:

1. **Is anything calling it?** A working `fear_sources` with no caller is
   indistinguishable from "no fears arose". `rg` the function name outside its
   own module.
2. **Is it reading the right object?** A character graph node is created *bare*
   — `Node(id=..., type="character", name=...)` — and carries no `tags`,
   `traits` or any other definition. Anything looking a character up by its
   **node** sees nothing; the data lives on the `Player`. `engine/fear.py`
   spent a long time matching against the node before this was caught.
3. **Has anyone authored any?** A field can be serialized, round-trip a save and
   look entirely functional while every value in every scenario is `[]`. Nothing
   in a soak will move until data exists, and no code change fixes that.

A fourth, quieter one: **a guard whose lookup can never match.** `is_undead_ghost`
takes a *name*; a call site passing the `Player` object compiles, runs, and
always returns False, so the guard silently never fires. When two similar guards
disagree, one of them is a no-op — check the signature rather than assuming both
are right.

Corollary for tests: a test that passes for the wrong reason is worse than no
test. Prefer asserting the *mechanism* (which value was read, which branch ran)
over asserting a substring that some other layer could also produce.

