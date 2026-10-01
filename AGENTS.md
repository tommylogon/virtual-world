# AGENTS.md

Project guidance for automated agents working in this repo.

## STOP — read this before you touch a UI

This section is a **gate**, not advice. It exists because a live audit of this
repo retracted **seven findings** for the same reason: judging a surface from a
partial view and reporting it as a defect. Advice about this did not work. These
are the checks that do.

### 1. Never report absence without proving it

You may not write "there is no X", "it is unlabelled", "it does not work", or
"nothing happens" until you have **run a count and shown the number**. If you
cannot produce a count, you do not have a finding — you have an untested guess.

    const controls = [...panel.querySelectorAll('button, select, input')]
      .filter(e => e.offsetParent);
    return { count: controls.length,
             labels: controls.map(e => (e.innerText || e.title || '').trim()) };

### 2. Count the WHOLE container, not a fragment of it

The single worst error available here. These are all the same mistake:

```js
// WRONG — a filtered list, then take one arbitrary member
const panels = [...document.querySelectorAll('aside, .inspector, ...')]
  .filter(e => e.offsetParent && e.innerText.length > 50);
const panel = panels[panels.length - 1];     // <- one SUB-panel, silently
```

Two filters plus an arbitrary pick and you are reading one section of a
26-section inspector. Fix it by **walking up to the real root and proving its
size** before reading anything:

```js
let el = document.getElementById('known-section-id');
while (el && el.querySelectorAll('.inspector-section').length < 3) el = el.parentElement;
// now report el's section count and control count BEFORE drawing any conclusion
```

If the count is larger than what you expected, you have found the real surface.
Read that number, not your assumption.

### 3. One screenshot is not a surface

A screenshot is one viewport. A panel can be 2613px tall. Before you judge a
scrollable container you must:

1. screenshot the top,
2. **scroll it to the bottom**,
3. screenshot again,
4. and if it has internal tabs or disclosures, open each one.

The equipment UI I claimed "did not exist" was two sections below where the first
screenshot happened to be scrolled.

### 4. Check the selector points at the thing you said

Before trusting a probe, confirm it is pointed where you think. `memory-section-x`
is not the inspector. A `select` at `0x0` may be an *enhanced* widget with a
visible chip. An `A <-> B` string may not be in the data at all.

### 5. Read the surface's own hint text

This app says what it wants: the turn modal says *"hover = free look · click =
what you can do with it"*, and a vignette says *"hover a cell to read it"*. Both
had been on screen for several exchanges before I acted on them.

### 6. When told you are wrong, go look again

Do not re-derive. Do not defend. Open the thing, look at it, and report what is
there. I asserted "the character inspector has no equipment UI" three separate
times while it was rendered two sections below my viewport.

### 7. Do not fix, or file, what you have not reproduced

A task whose acceptance criteria you could not demonstrate live is not ready to
close. Say so and record what blocked it.

### 8. Content before instrumentation

If a mechanic has nothing exercising it, **author the content** — do not write a
test to stand in for it and do not declare it undemonstrable. A test proves the
mechanism; a fixture makes it real. Both, in that order, and the fixture is what
survives.

---

## Prime directive

VirtualWorld is a simulation, not a collection of isolated features.

**Make the requested behavior true in the simulation with the smallest coherent
change.** Preserve existing invariants, reuse existing systems, and do not create
a second source of truth when the current model can represent the behavior.

Task files describe intent. Code shows current behavior. Tests provide evidence.
The simulation's invariants outrank all three. When they disagree, investigate the
discrepancy instead of assuming one of them is correct.

## Never infer runtime behavior from existence

This is the first principle, and it is a distilled lesson from three real bugs in
this repo. A mechanic that exists, works, and is never called looks *exactly* like
a mechanic with a low event rate. Three separate instances turned up in one pass,
so check all of the following before concluding anything from a telemetry table or
a soak:

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
4. **Can the guard's lookup ever match what the caller passes?**
   `is_undead_ghost` takes a *name*; a call site passing the `Player` object
   compiles, runs, and always returns False, so the guard silently never fires.
   When two similar guards disagree, one of them is a no-op — check the
   signature rather than assuming both are right.

A field that serializes correctly, a function that exists, or a test that passes
is **not** evidence that a mechanic is wired into live simulation. Do not add
behavior until all of the four above are checked.

### Never enumerate a property set from one of its members

The four checks above are about a mechanic. This is the same failure against a
**vocabulary**: reading one property and then describing what the system can express.

A session did this three times in a row on ways, each time being confidently wrong:

- grepped `see_through`, concluded transparency was one boolean — missed `prevent_close`,
  which `world_compile.py` already writes and `movement.py` already reads
- read `requires: crawl/climb/jump` off a dropdown, called it a label — missed three
  climb systems, including one gated by the `floor` layer that no property declares
- read `max_size` off a dropdown, called it a size — missed that carrying >= 50% of
  capacity adds a tier and locks you out of a gap you walked through unloaded

Each answer was plausible, cited, and wrong. The mechanical rule:

**Before asserting what a property set can or cannot express, enumerate the whole
set from one place and state the count.** If you cannot produce the count, you have
a guess. `python tools/way_property_index.py --report` is the worked example — the
property set is declared once in `tools/way_properties.py` and rendered from it.

The general form: *grep for one member of a vocabulary and you have learned exactly
one member.* `rg` is a starting point for a search, never the evidence for a claim
about a set.

## Never judge a UI surface without interacting with it

**The operative rules for this are the gate at the top of this file
("STOP -- read this before you touch a UI").** They are numbered, they are
mechanical, and they are the version to follow. This section keeps only the
evidence for why they exist.

A live audit retracted seven findings for judging a surface without using it:
stranger names that "failed to resolve" (they are strangers -- the hover says
"recognized -- but you do not know their name yet"), a names toggle that was a
"one-way door" (it round-trips), an `area_presence` index called stale (it is
a movement ledger, written only from `movement.py`), and vital decay called a
"permanent alarm" (`vital_rates.py` documents the intent and every figure
matches). Each looked completely convincing from a screenshot or a DOM read.

**What is invisible without interaction:**

- **Hover** -- tooltips, free-look panels, "recognized -- but you do not know
  their name yet", cost disclosures like `free look - no turn cost`
- **Click** -- verb menus, confirmation modals, context actions
- **Collapse** -- `advanced`, `raw json`, `what you know`
- **Typed input** -- autocomplete, and a bare verb answered with a real error

**Two more that are cheap to get wrong:**

- **A hidden element is not a closed one.** `#htc-overlay` is `display: none`
  while its child `#htc-modal` stays in the DOM at `0x0` with a stale
  `innerText`. Test visibility with `getBoundingClientRect()` and
  `offsetParent`, **never** with `element exists`.
- **canvas-rendered views have no DOM.** vis.js draws to a `<canvas>`, so
  `document.querySelectorAll('.vis-node')` returns **zero** and every
  DOM-derived count of them is a fabrication. Screenshot or ask the API.

**Before filing a UI finding, name the interaction you performed.** If the
answer is "I read the markup" or "I took a screenshot", it is not yet
evidence.

## Turn system — it exists, and "stuck" is usually the gate working

There is a real turn scheduler. Do not build a second one, and do not report
it as missing.

- State lives **client-side on the AgentEngine instance**:
  `VW.agent.turnQueue` / `.currentTurnIndex` / `.turnNumber` /
  `.initiativeRolls`, ordered by `config.turnOrder` — sequential (default),
  random, or initiative (d20 + DEX). Logic: `static/js/agent/turn-queue.js`.
  Full chapter: `docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md`.
- **`Turn: 0` with the human turn modal open is correct, not a hang.** The sim
  is waiting for a human to commit. An NPC turn needs the human's slot
  resolved first. This exact reading cost me a session once — screenshot
  before concluding the loop is dead.
- Advancing past the last actor is what ends a cycle: `turnNumber++` plus one
  `ApiClient.applyTurn()`. Ticks and decay run **once per cycle**, never inside
  individual commands.
- **The always-available command line / "Speak as guest…" is a deliberate
  override.** It bypasses the queue and does **not** consume the character's
  queued slot. Don't "fix" it to respect turns, and don't make the turn panel
  appear outside the controlled character's slot — both are the design.
- **Three views answer "whose turn is it"**, all reading the same client-side
  state: the turn modal header (gated on `config.turnBased`, names only the
  current slot via `TurnQueue.getCurrentCharacter()`), the event-stream
  `⏭ up next:` strip (`queue.slice(idx, idx + 5)`, marks your slots `🎤 YOU`),
  and the Turn Order panel (whole round, rolls, per-slot `done`/`ACTING…`).
  They agree on the head of the order — measured, not assumed. Don't merge or
  "fix" one into another.
- The queue is **runtime-derived**. Do not promote it to persisted authoring
  data; it is rebuilt by `initialize()`/`reconcile()`.

## Agent operating rules

### Before editing

For any non-trivial change:

1. Read the task/bug and identify its acceptance criteria.
2. Find the existing implementation, caller(s), and tests for the behavior.
3. Trace the data flow: authored data / input -> runtime state -> engine rule ->
   observable result.
4. Identify the actual source of truth for every value involved.
5. Check whether the requested mechanic already exists but is unwired, incorrectly
   addressed, or unauthored (see above).
6. Only then choose the implementation point.

Do not start by adding code because a task says a capability is missing.

### Simulation invariants

Preserve these unless a task explicitly changes the architecture:

- Node identity is an opaque ID. Display names are a resolution layer.
- Character definition/state belongs to the `Player` model; a bare character graph
  node is not authoritative for traits, tags, or behavior.
- The graph is the authoritative world model. Scopes, zones, fog, and UI
  hierarchies augment it; they are not alternate spatial models.
- Quantity is a pooled resource, not one node per unit.
- Ownership is a property; containment is a containment edge; a component is a
  containment edge plus an action contract. Charge is the generic `uses` counter.
  These are different concepts — do not collapse them into one mechanic.
- Scope is a grouping / load boundary, not alternate geography.
- Do not duplicate state for convenience when an existing property, edge, or
  derived index is sufficient.
- A runtime-derived value must not become persisted authoring data unless
  persistence is part of the intended behavior.
- Reuse existing generic movement, action, trigger, matching, serialization, and
  condition machinery rather than bypassing it.
- A new rule must not silently invalidate unrelated existing scenarios.

### Engine vs data vs authoring

Classify the failure before fixing it, and do not solve one category by adding
code to another:

| Category | Meaning |
|---|---|
| **Engine** | the runtime logic is wrong or unwired |
| **Data** | the engine is correct but the stored/generated data is wrong |
| **Authoring** | engine and data model both support it, but no content invokes it |
| **Test** | the system is correct; the test targets an obsolete API or wrong object |
| **Tooling** | the application is correct; developer/test infrastructure is stale |

If the engine supports a mechanic and the scenario has no authored data, fix the
scenario/content layer. If data serializes correctly but runtime never consumes
it, fix the wiring, not the scenario. If both are correct but behavior is wrong,
trace the runtime path before changing either.

### Testing rules

A passing test is only useful if it proves the intended mechanism. Prefer tests
that establish which source of truth was read, which branch ran, which state
changed, and that the negative case stays blocked.

Do not obtain green tests by weakening assertions, bypassing the normal dispatch
path, adding special-case fixtures, or asserting incidental text produced by some
other subsystem.

For new mechanics, test both:

- the smallest direct engine behavior, and
- a minimal end-to-end scenario proving the mechanic is actually wired and can
  occur.

A soak or scenario result does not replace a wiring test, and a wiring test does
not prove authored content can trigger the mechanic. **Unit-test the mechanism,
micro-scenario the emergence.**

### Regression discipline

Compare the changed behavior against the existing baseline, comparing failure
*names* rather than counts (see the baseline section below).

- Do not remove or loosen a failing test because it conflicts with the requested
  behavior.
- Do not update the known-failure baseline without re-measuring on a clean
  checkout of `master`.
- Do not declare a mechanic complete because its module exists or its unit tests
  pass.
- Do not call a newly discovered failure "pre-existing" until it has been
  reproduced independently.
- When a failure is genuinely unrelated, record why it is unrelated rather than
  silently ignoring it.

**The A/B that satisfies the rule above.** `git stash push -- <the files you
touched>`, re-run the same selection, then `git stash pop`. Identical failure
*names* both ways is the proof. In this session that check turned six
`test_scenario_data_integrity` / `test_ownership` failures from "possibly mine"
into "demonstrably not mine" in one command, and it is the only evidence that
counts — a plausible story about which lane owns a failure is not.

### Filing discipline

The task tree is for work that is **not yet understood**, not for findings. A
ticket whose fix the filer already knows how to write is work deferred, not
work described, and it makes the backlog lie about its own size.

- **Verify before filing.** A filed finding names the interaction or measurement
  that produced it. "I read the markup" and "I took a screenshot" are not
  evidence for a UI claim — see the principle above.
- **Retract in place, and say why.** When a finding does not survive
  verification, move the task to `cancelled` and append what disproved it. Do not
  delete it and do not quietly leave it. A retraction with a measurement is
  worth more than the finding was.
- **Retracting is a success, not a failure.** Four of eight findings filed in the
  live audit were retracted, and the rate that matters is not the ratio but
  whether an unverified finding reaches `done`. A tree where nothing is ever
  retracted is a tree where nothing was ever checked.
- **Half-right findings get corrected, not cancelled.** "No flee or wait verb
  exists" was half wrong — `wait` existed. Rewriting the goal to the half that
  survived keeps the real half actionable.
- **Don't batch-fix from an unverified list.** Verify three, fix three, then
  re-verify. Fixing thirty findings read off a single pass reproduces exactly the
  error that made the retractions necessary.

### Scope control

Prefer the smallest change that makes the invariant true. Do not refactor
neighboring systems without a concrete need, introduce a new abstraction when an
existing seam already represents the concept, add compatibility layers for
obsolete callers unless compatibility is explicitly required, rewrite working
behavior because a newer implementation looks cleaner, or add scenario-specific
logic to generic engine code.

If a task exposes a deeper architectural problem, fix the required root cause
and file the larger cleanup as its own task.

### Definition of done

Before moving a task to `review`, be able to state:

- **What behavior changed?**
- **Why is this the correct layer?**
- **What is the source of truth?**
- **What proves the behavior is wired?** (a caller, not just a unit test)
- **What regression test proves the mechanism?**
- **What existing behavior was intentionally preserved?**
- **Is there authored content that exercises the feature?**
- **What remains intentionally unimplemented?**

If the last three answers are unknown, investigate before declaring the feature
complete. "The code exists" is not "the feature shipped".

### Documentation and changelog

Update documentation only after behavior has been verified, and use precise
language:

- **implemented** — executable behavior exists and is exercised
- **wired** — the runtime path reaches it
- **authored** — at least one scenario/content definition invokes it
- **tested** — a regression test proves the intended mechanism
- **planned** — design/task exists but runtime behavior is not yet present

Do not describe a mechanic as complete when only its data model or implementation
seam exists.

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
  module lacks its `@module`/`@contributes` header, **and** when a new `@docs` target is a
  folder or a dead path — a folder satisfies the contract while pointing at nothing readable,
  which is how 26 declarations used to "resolve"; regenerate the index with `--write`.
- Feature coverage guard: `python tools/feature_index.py --check` fails when a new module's
  `@powers` names no feature in `docs/virtualWorld/Feature Map.md` — the canonical list of what a
  person can do in a game and in the editor, and the denominator for documentation coverage.
  `--report` prints the join from features to the modules that claim them (and the features
  nothing claims); `--write` regenerates `docs/design/feature-index.md`;
  `--update-baseline` accepts today's debt. A feature is **not** a module: `attention.py` is a
  mechanism, and auditing per module answers the wrong question — see `Feature Map.md` for why
  three earlier attempts to measure this failed.
- Way property index: `python tools/way_property_index.py --check` fails when a hand-maintained
  list of way properties drifts from `tools/way_properties.py`; `--write` regenerates
  `docs/virtualWorld/World Building/Way Properties.md`, `--report` shows per-list coverage.
- Character loadout check: `python tools/character_loadout_check.py --check` fails on a
  character entry whose `equipped`/`inventory` shape the engine cannot read — a dict in an
  `equipped` slot **500s `GET /api/state`** once that character is refreshed from the
  library, a non-list slot is dropped by import, and an id with no inventory entry resolves
  to nothing. `--report` groups every finding with the reason; `--update-baseline` accepts
  today's debt. Run it after editing anything under `data/library/characters/`. Authoring a
  character is a data-shape problem, and this is the shape gate for it.
- JS lint: `npm run lint`. JS typecheck: `npm run typecheck` (see
  `docs/design/typescript-migration.md`).
- Export-log lint (regression guards over play sessions, no server needed):
  `node tools/log_lint.cjs data/exports/<log>.txt` (or `npm run loglint -- <path>`).
  Run it on the latest export before tagging/committing a release.
- Run the app: `python app.py` — **it serves on port 4444**, not 5000. Use
  `http://localhost:4444` for Playwright and for manual checks. Set
  `VW_PORT` to run a second copy elsewhere — parallel worktrees each need their
  own port or they fight over 4444 and the failure looks like a hang.

### Known pre-existing failures (NOT caused by your change)

`tests/test_tick_time_scaling.py` **hangs** — it does not fail, it never finishes. Always
`--ignore` it or the suite never returns:

```
python -m pytest --ignore=tests/test_tick_time_scaling.py
```

Baseline was **5 failed / 4274 passed** on `master` (2026-09-28). Four of those five
are gone as of 2026-09-29; the tree now measures **1 failed / 5025 passed** (18m14s
on this machine). The test count has drifted a long way, so compare names, not
totals. The only remaining failure:

| Test | Nature |
|---|---|
| `test_templates.py::test_generator_covers_every_effect_type` | `data/library/items/template_polymorph_target.json` is missing |

**That "1 failed" figure is itself stale — re-measured 2026-09-30 at `0a8e829`,
the suite is 12 failed / 6446 passed** (187s on this machine, not 18 minutes). All
twelve fail identically on a clean `master` worktree, verified by A/B, so treat
this list as the floor and not something you caused:

| Test | Nature |
|---|---|
| `test_character_identity.py::test_collapse_is_idempotent` | canonical-node problem (task-457) — the two "unconfirmed fixed" failures below |
| `test_character_identity.py::test_kraktooth_loads_as_one_node_per_character` | same |
| `test_ownership.py` (3 tests) | ownership vs scope-tree disagreement over unheld need-resources |
| `test_pines_slice.py::TestGenerationEndToEnd::test_the_recipe_reachable_from_the_api_generates_the_apartment` | end-to-end generation |
| `test_promotion.py::test_observe_route_queues_residents_and_404s_unknown_scope` | scope promotion |
| `test_scenario_data_integrity.py` (4 tests) | `world_template` labelling, authored character nodes, Eldenford interior way endpoints and split scope |
| `test_templates.py::test_generator_covers_every_effect_type` | `template_polymorph_target.json` missing |

Re-measure before you trust this table — it is a snapshot, not a contract.

Both of the `create_app()`-isolation failures were bug-55, and the diagnosis in that
file was wrong in an instructive way:

- `test_social_company.py` was **not** measuring a leak. A seeded probe shows repeated
  `create_app()` calls agree exactly; the tests were running *full* turns, so the cast
  wandered out of the "alone" area and the measured character picked up the company gain
  (75 or 100 depending on the run). They now tick with `skip_npcs=True`, which keeps the
  per-character decay block and drops the wander.
- `test_scenario_name.py::test_clearing_the_source_leaves_the_name_alone` was a
  test-premise bug and failed in **isolation** too: `create_app()` boots with
  `_scenario_name` already set, and `set_scenario_source()` documents that an existing
  name beats the filename. No leak is involved.

The two `test_character_identity.py` failures (`test_collapse_is_idempotent`,
`test_kraktooth_loads_as_one_node_per_character`) were task-457's canonical-node
problem. They pass in the 2026-09-29 full-suite run, but nobody reproduced them
independently here, so read that as *unconfirmed fixed* — not as task-457 shipping.

**The old baseline was ~60 failed, and 55 of those were the MCP tests** — which made the
"compare to baseline" rule nearly blind. Those are fixed (see below), so a lane that
reports "at baseline" is now reporting against 1 real failure, not 60.

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

Both `create_app()`-isolation failures listed in the baseline table above turned out to
be test bugs rather than engine leaks — read the bug-55 file before re-diagnosing them.

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

`task says X -> code X -> tests X -> "done"` is not the workflow. Before
`inprogress` -> `review`, see **Definition of done** above: find the source of
truth, trace the path, prove the wiring, prove the behavior, verify authored
content. A task is not done because the requested code exists.

## Conventions

- **Backend data operations key nodes by id.** Names are user-facing and resolve
  to ids through `engine/matching.py`. Do not use a display name as a storage
  key. Player identity: `engine/player_manager.py` (`task-446`).
- Follow the existing `*_ops.py` + thin registrar split when adding routes, and
  add the `<script>` tag in `templates/index.html` when adding a JS module.
- Do not edit `.kilo/agent-manager.json` directly; it is managed UI/recovery
  state, not an API.
- Only commit when explicitly asked.

The same "never infer runtime behavior from existence" checks apply to code
written by an agent, and the corollary for tests is worth repeating: a test that
passes for the wrong reason is worse than no test. Prefer asserting the
*mechanism* (which value was read, which branch ran) over asserting a substring
that some other layer could also produce.

