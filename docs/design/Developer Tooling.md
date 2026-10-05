# Developer Tooling

What an agent or a person needs on this machine to work on VirtualWorld, and
why. Measured against the repo at 2026-10-02; every "verified" claim was run
here, not inferred from a package listing.

## The machine, as measured

| | |
|---|---|
| git | 2.37.3 — old; `git maintenance` and newer clone/shallow features are missing |
| node / npm | 24.5.0 / 11.7.0 |
| python | 3.10.11, via the WindowsApps shim (`python` is not a real interpreter entry) |
| uv | 0.6.12 |
| editors | VS Code (`code` CLI works), Cursor |
| package managers | winget, chocolatey. No scoop. |
| **shell PATH defect** | the process PATH is a truncated copy of `HKCU\Environment`. `rg` reported "not recognized" while being installed and working. **Prefix commands with `$env:PATH = (Get-ItemProperty "HKCU:\Environment" -Name Path).Path`.** |

Already present and fine — do not reinstall: `rg fd bat fzf jq git-delta tokei
sqlite3 ruff uv node npm code obsidian nmap docker wget gh`.

## What the repo needs, measured

| | |
|---|---|
| Python | 468 files, 94,385 code lines, 23,603 complexity |
| JavaScript | 250 files, 64,084 code lines, 18,383 complexity |
| JSON | 2,927 files, **278,030 lines** — the real currency, not the code |
| Markdown | 894 notes, 277,840 lines |
| HTML | 19 files, **183,414 lines** — generated mega-files (`docs/dev_tasks.html`) |
| tests | 214 pytest files; suite takes minutes and one file hangs |
| live graph | 658 nodes / 207 areas / 361 ways / 35 items / 23 characters |
| `GET /api/state` | **2.48 MB, p50 756 ms, p99 876 ms** at 10 connections — and the client polls it every 1.5 s |
| secrets surface | LLM keys are read client-side; `.env` is gitignored |

The last two rows are why profiling and load tooling are on this list rather
than a wishlist. A 756 ms poll that hands back 2.48 MB to rebuild 1470 DOM
nodes is the single biggest latency fact in the app.

---

# Tier 1 — verified installed today, with the measurement that justifies each

Installed via `uv tool install` (isolated, no venv pollution) or `winget`.

### 1. `tools/doc_links.py` — wikilink and URL checker (already in the repo)
```
python tools/doc_links.py --count     # 0 broken, 0 distinct
python tools/doc_links.py --check     # exit 1 when any link is broken
python tools/doc_links.py --orphans   # curated notes nothing links to
```
Implemented on `wt/docs-contract`. Implements Obsidian's real resolution rules
— basename, `\|`-escaped alias, `#Heading`, `^block` — because `tools/tasks.py
move` relocates task files with `git mv` and rots inbound links.

`--orphans [--min-inbound N] [--all-notes]` was added 2026-10-05 and is the
**opposite** query: not "does this link go anywhere" but "does anything link
here". The vault had 885 notes, 688 of them with zero inbound links, and no way
to tell a note nobody was meant to find from one that is a destination. It is
deliberately a report and not a gate — an orphan is often legitimate. What makes
it useful is the number staying at 0 for curated notes: a *new* orphan is a note
that was added without being reachable.

**I installed `lychee` for this and it was the wrong tool.** It reported 23
broken wikilinks; all 23 were false positives from lychee not understanding
`\|` alias escaping inside markdown tables, the most common link form in this
vault. `doc_links.py` reports **0**. Kept installed and recorded here as a
negative result — do not reach for it.

### 1b. The three vault gates that keep the graph from rotting back

Added 2026-10-05, all three wired into `npm run precommit` with
`tests/test_feature_pages.py`, `tests/test_doc_tags.py` and
`tests/test_doc_connected.py` as their pytest mirrors.

| Tool | The failure it exists for | Measured before → after |
|---|---|---|
| `tools/feature_pages.py --check` | a Feature Map row with no page; a page that lost a section; a page whose `feature_id` drifted from its row; 76 pages with no index | 2 rows reading `none` → **76 pages for 76 rows** |
| `tools/doc_tags.py --check` | a tag set that is not a set — 75 tokens of which 70 appeared exactly once, which makes Obsidian's tag pane worthless | 75 loose tokens → **28 controlled tags, 0 untagged of 157** |
| `tools/doc_connected.py --check` | notes that describe a system and record nothing about what they touch | 21 curated notes nothing linked to → **0**, and 0 stale empty blocks |

`doc_connected.py --apply` is safe to re-run: it rewrites only the block between
its own `<!-- connected:start/end -->` markers. It draws on four relations the
repo already asserts (Feature Map rows, the 96 task files with `wiki:`
frontmatter, module `@docs` headers, same-folder neighbours) and a hand-kept
`SECTION_REFS` table of heading-level links — `--check` fails when one of those
headings is renamed, because a section link that lands at the top of a page is a
promise the note does not keep.

One rule the tools cannot enforce for you: **a new curated note must be
reachable**. Add it to `docs/virtualWorld/_Index.md` or link it from a sibling.


### 2. vulture — dead Python code
`uv tool install vulture`
```
vulture engine/ --min-confidence 80
```
**Ran it: exactly 2 findings** — `engine/skills.py:206` and
`engine/logging_events.py:175`, both unreachable code after a bare `return`.
**Both are already known and ticketed**: they are the parked LLM-logging stubs
(`task-88-llm_logging`, in review; documented in `Skills System.md`), and
`engine/equipment.py:849` still calls one of them. So a green run means nothing,
not "two bugs to fix". Use 80, not 60 — at 60 it fills with dispatch noise.

### 3. py-spy — sampling profiler, attaches to a running process
`uv tool install py-spy`
```
py-spy top --pid $(Get-CimInstance Win32_Process -Filter "Name like '%python%'" | ? { $_.CommandLine -match 'app\.py' } | Select-Object -First 1 -Expand ProcessId)
py-spy record -o profiles/tick.svg --pid <PID> --duration 30
```
Zero code changes, ~5% overhead. For finding out why a tick costs 756 ms.
**Attaching to another process on Windows needs an elevated shell** — the
install does not, the attach does.

### 4. pyinstrument — call-stack profiler
`uv tool install pyinstrument`
```
pyinstrument -m pytest tests/test_tick_time_scaling.py --ignore-glob='*never*'
```
Pairs with py-spy: pyinstrument when you can reproduce under a debugger,
py-spy when you cannot. py-spy answers *which function*, pyinstrument answers
*which line inside it*.

### 5. pip-audit — dependency CVE scanner
`uv tool install pip-audit`
```
pip-audit -r requirements.txt
```
`requirements.txt` pins only 9 packages with **no version constraints**, and
that includes `fastmcp`, `httpx` and `flask`. AGENTS.md already records an MCP
incident caused by a library major version. This is the tool that sees the next
one before it does.

### 6. gitleaks — secret scanner
`winget install Gitleaks.Gitleaks`
```
gitleaks detect --source . --no-git --redact
```
**Ran it: 2.59 GB scanned in 27 s, 63 hits.** Triaged them: 59 are inside
`.kilo/worktrees/` (gitignored), and all 4 outside are **false positives** —
synthetic example records in `docs/virtualWorld/dev_tasks/todo/ui/task-405-*`
where `"authorization": "Bearer sk-or-..."` is elided and the sample `key`
matches its own `ts`. No live credential. Worth knowing before wiring it into
pre-commit: it will block commits on those task files until allowlisted.

### 7. jq — JSON query
Already installed. The single highest-leverage tool for this repo, because the
data *is* the product.
```
jq -r -f filter.jq state.json     # PS 5.1 strips quotes from native args; always use -f
```
Cross-check against the live API: 658 nodes, 207 areas, 361 ways, 35 items,
23 characters — matches the browser exactly.

### 8. yq — YAML query
`winget install MikeFarah.yq`. For `.kilo/agent-manager.json` and the MCP
config. Note: do **not** hand-edit `agent-manager.json`; this is for reading it.

### 9. oha — HTTP load generator
`winget install hatoo.oha`
```
oha -n 150 -c 10 --no-tui http://localhost:4444/api/state
```
**Ran it against the live app: p50 756 ms, p95 850 ms, p99 876 ms, 150/150
200s.** Measured, not guessed. Prefer it to `wrk`/`hey`: live TUI, proper
percentiles, and `--latency-correction` for coordinated omission, which `wrk`
gets wrong by default.

### 10. scc — line counter
`winget install BenBoyter.scc`. Fast, and it counts comments/blanks/complexity
separately, which is how the table above was produced. Ignore `tokei` for this.

### 11. hyperfine — benchmark runner
`winget install sharkdp.hyperfine`
```
hyperfine --warmup 3 "python -m pytest tests/test_auto_dress.py -q" "npm run typecheck"
```
For "is this change actually faster", across repeated runs with outlier
detection. `time` gives you one sample and lies to you.

### 12. zoxide — smarter `cd`
`winget install ajeetdsouza.zoxide`. 110 engine modules, 894 notes, plus
`.kilo/worktrees/` — `z foo` beats typing paths.

### 13. just — task runner
`winget install Casey.Just`. `tools/` holds 90+ loose one-off scripts, ~30 of
them `test_*.cjs` end-to-end scripts that duplicate what Playwright does
properly. A `justfile` turns that into `just e2e inspector`.

### 14. lazygit — TUI git
`winget install JesseDuffield.lazygit`. Multi-worktree is core here; the
worktree list, per-worktree status and path-limited staging are all much faster
than remembering `git worktree list` every time.

### 15. pyright — Python type checker
`uv tool install pyright`
```
pyright engine/ routes/ tools/
```
The repo typechecks its JavaScript (`npm run typecheck`) and its Python not at
all, across 94k lines. Start non-blocking on `engine/` only.

### 16. ruff-lsp — the language server
`uv tool install ruff-lsp`. `ruff` the linter is installed; this is what makes
VS Code actually use it.

### 17. pre-commit — hook runner
`uv tool install pre-commit`. There are **no hooks at all** in this repo
today, and six custom guards in `tools/` that only run if a human remembers.
This is how they stop being optional.

### 18. hypothesis — property-based testing
`uv tool install hypothesis`
```
@given(stints=st.integers(min_value=0, max_value=500))
def test_no_tick_exceeds_horizon(stints): ...
```
AGENTS.md is built on invariants — pool ownership, containment vs ownership,
tick-once-per-cycle. Those are exactly what property tests are for, and right
now they are asserted case by case.

---

# Tier 2 — not installed, needs a repo change or a failed build

### 19. pytest-xdist
`requirements.txt`. `python -m pytest -n auto`. AGENTS.md reports the suite at
187 s to 18 min depending on machine; xdist is the cheapest available win.
Always keep `--ignore=tests/test_tick_time_scaling.py` — that file hangs.

### 20. pytest-cov
`requirements.txt`. There is no coverage measurement anywhere in the repo.

### 21. time-machine
`requirements.txt`. The sim is tick-based with a `game_time` string. Tests that
depend on the wall clock cannot be deterministic; this makes them so.

### 22. memray
`pip install memray` — **failed to build on this box** (Python 3.10.11,
Windows). Wants tracking of a 2.48 MB `jsonify` response and the graph
serialiser; retry if Python moves to 3.12+.

### 23. duckdb
`requirements.txt` (`pip install duckdb`; the PyPI wheel ships no CLI, so it
does not work via `uv tool install`). Lets you answer "which areas have no
exits, which edges point at non-existent nodes" with SQL over the scenario
files instead of hand-written Python each time.

### 24. knip — unused JS files, exports, dependencies
`npm i -D knip`. **Not ESLint.** ESLint cannot see a file nothing imports; knip
finds dead files, unused exports and undeclared deps. With 250 JS files and
`npm run lint` already green, this finds a different class of problem.
Requires an `entry`/`project` config — plan one commit for that.

### 25. @axe-core/playwright
`npm i -D @axe-core/playwright`. The character inspector's tab bar is three
`<div onclick>` with no `role` and `tabIndex: -1` — measured. axe turns that
into a gate. Works with the plain `playwright` package this repo already has.
(`pytest-playwright-axe` needs Python 3.12; this box is 3.10.)

### 26. madge — circular imports
`npm i -D madge && npx madge --circular static/js`. `templates/index.html` has
183 `<script>` tags in load order, and one module gaining an import of another
is a load-order bug that no bundler catches for you.

### 27. mitmproxy
`pip install mitmproxy`. `GET /api/state` returned
`{"error": "unhashable type: 'dict'"}` for several minutes this session and the
only diagnostics were Flask's one-line error string. `mitmweb` shows the actual
request and response bodies.

### 28. respx — httpx mocking
`requirements.txt`. `httpx` is already a dependency, so route-level mocking
works without standing up the app. Makes route tests fast and deterministic.

### 29. vitest
`npm i -D vitest`. `tools/unit/run.cjs` is a bespoke Node sandbox with a manual
module list at the top of the file — adding a browser-global module means
editing that list or the test silently does not see it. Vitest solves discovery
properly. **This is a migration, not an install**; scope it separately.

### 30. editorconfig-checker + `.editorconfig`
No `.editorconfig` exists, and every commit I made warned
`LF will be replaced by CRLF`. With 2,927 JSON files and 894 notes, mixed line
endings produce diff noise that buries real changes. The `.editorconfig` is a
one-file change; the checker runs in pre-commit.

### 31. `.pre-commit-config.yaml`
Not a tool, but the missing half of #17. Wire the six existing guards
(`js_module_index.py --check`, `feature_index.py --check`,
`character_loadout_check.py --check`, `way_property_index.py --check`, plus
lint and typecheck) so they cannot be skipped.

### 32. vale — prose linter
`winget install vale`. AGENTS.md insists on precise claim language
(implemented / wired / authored / tested / planned) across 894 notes and every
task card. Vale enforces it mechanically. Expect a large first run — scope it
to new files.

### 33. markdownlint-cli2
`npm i -D markdownlint-cli2`. 894 notes, no style enforcement.

### 34. mise — toolchain pinning
No winget package; use the official installer. `python` here is the
WindowsApps shim, which silently breaks anything that spawns a real
interpreter. `mise use python@3.12 node@24 uv` makes the interpreter explicit
and repo-local.

### 35. gitleaks allowlist (config, not install)
`.gitleaks.toml` with the four documented false positives from #6. Without it a
pre-commit hook blocks on task files that contain no secrets.

---

## Deliberately not recommended

- **A bundler (vite/esbuild/rollup).** The highest-leverage architectural tool
  available — it would fix load order, enable knip and tree-shaking, and let the
  inspector stop shipping one 178 KB HTML string. It is also a rewrite of
  `templates/index.html`'s 183 script tags. Worth doing; not a tool to install
  alongside everything else.
- **mypy.** pyright is faster and the JS side already runs `tsc`; one type
  checker, not two.
- **pylint / prospector.** Ruff covers it and is orders of magnitude faster.
- **Obsidian.** Already installed, and `docs/virtualWorld` is a working vault —
  use it rather than adding a note linter that duplicates its link resolution.
- **Postman / Bruno / Insomnia.** `httpie` plus `pytest` client fixtures cover
  the same ground with no GUI state to maintain.

## First five to do

1. `just` + `.pre-commit-config.yaml` — turns 90 loose scripts and 6
   forgettable guards into one entry point.
2. `lychee` — turns task-662's estimate into a number.
3. `knip` — the only thing on this list that finds a whole class of bug the
   existing lint gate structurally cannot see.
4. `pytest-xdist` + `--ignore` for the hanging file — the cheapest test-suite
   win available.
5. `py-spy` + `oha` — 756 ms per poll, 2.48 MB per response, still unexplained.