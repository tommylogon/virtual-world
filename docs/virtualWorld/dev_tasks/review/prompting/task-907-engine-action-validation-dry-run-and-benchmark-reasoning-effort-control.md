---
type: task
status: review
area: prompting
priority: high
wiki: "[[AI & Narration/Agent Engine]]"
---

# task-907: engine action validation dry run and benchmark reasoning effort control

**Filed:** 2026-10-26
**Related:** 

## What

Replace benchmark.js ad-hoc validation with a read-only engine action validation endpoint, and add reasoning effort control to the Benchmark Lab UI and proxy.

## Why

benchmark.js currently implements a disconnected 40-line string check that rejects valid actions (examine library, examine the bookshelf) and accepts invalid bare verbs (bare examine). Moving action validation to the real engine enforces single-source-of-truth MVC principles. In addition, reasoning effort cannot currently be configured or tested in benchmark sweeps.

## How

1. In routes/action_handlers.py, implement POST /api/action/validate that evaluates action syntax, _VERBS_NEEDING_TARGET, and target resolution against characters, areas, items (matching._match_item_name with difflib), and exits without mutating world state.
2. In static/js/benchmark/benchmark.js, use ActionNormalizer.normalizeStructuredAction and query /api/action/validate for ground-truth verification.
3. In templates/benchmark.html, add Reasoning Effort select dropdown.
4. In routes/benchmark.py and benchmark.js, forward reasoning_effort, extra_body, and reasoning parameters to upstream chat completions.
5. Verify live in browser via Playwright and run pytest suite.

## Browser UI and intended live verification

Intended UI home: /bench

Current availability: benchmark lab is live, action validation endpoint and reasoning effort control in development

Live steps when available:
1. Open http://localhost:4444/bench
   - expected: Benchmark Lab loads with new Reasoning Effort dropdown.
2. Run a model that outputs examine library or examine bookshelf
   - expected: Action is validated through /api/action/validate and passes ground-truth check.
3. Change Reasoning Effort to low or high and verify payload sent to upstream
   - expected: Reasoning Effort is sent in /api/bench/chat request and recorded in export JSON.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Benchmark Lab loads with new Reasoning Effort dropdown; action validation passes examine library and examine the bookshelf, while rejecting bare examine.
   - observed: Verified live in browser with Playwright on http://localhost:4444/bench. Reasoning Effort dropdown options confirmed; bare examine returned valid=False (missing_target); examine library returned valid=True (area); examine the bookshelf returned valid=True (item: bookshelf_item).
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Navigate to /bench, select reasoning effort 'high', load past run, evaluate actions against /api/action/validate, click Export JSON.
   - observed: Selected option 'high' on #bench-reasoning-effort, loaded past run, verified action chips and engine-grounded flags, clicked #bench-export-json and verified config.reasoning_effort == 'high'.
3. Run the targeted regression test for the mechanism.
   - expected: Pytest test_benchmark_routes.py passes with 12 tests, npm run build:ts compiles clean.
   - observed: python -m pytest tests/test_benchmark_routes.py passed 12/12 in 7.00s; npm run build:ts exited 0.

## Acceptance

- [x] POST /api/action/validate correctly validates verbs needing target and resolves targets using engine matching
- [x] examine library, examine room, and examine the bookshelf validate as passing in /bench
- [x] bare examine without a target fails with clear missing target category
- [x] Reasoning Effort dropdown is present in /bench sidebar and forwarded in /api/bench/chat payload
- [x] Export JSON records reasoning_effort and engine-validated flags
- [x] Zero em-dashes and tests pass

## Files

- `routes/action_handlers.py`
- `routes/benchmark.py`
- `templates/benchmark.html`
- `static/js/benchmark/benchmark.js`
- `tests/test_benchmark_routes.py`
