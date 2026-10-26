---
type: task
status: review
area: prompting
priority: high
wiki: "[[AI & Narration/Agent Engine]]"
---

# task-906: retry-after rate-limit backoff across app and benchmark reroll history

**Filed:** 2026-10-26
**Related:** 

## What

Respect upstream Retry-After headers during HTTP 429 rate-limiting in both the primary LLM client and benchmark proxy, and add per-model reroll buttons with multi-roll history and JSON export to the Benchmark Lab.

## Why

When testing models against cloud providers like OpenRouter or local hosts under rapid invocation, 429 rate limit responses cause immediate hard failures if Retry-After is ignored. Furthermore, testing temperature variance and non-determinism currently requires re-running entire benchmark suites rather than rerolling individual models while preserving roll history.

## How

1. In static/js/llm-client.ts: read resp.headers.get('Retry-After') on 429/5xx and pause for the requested duration (bounded to 30s) before retrying.
2. In routes/benchmark.py: wrap /api/bench/chat upstream calls in a 3-attempt retry loop that respects upstream Retry-After headers on 429/502/503/504.
3. In static/js/benchmark/benchmark.js: add per-model Reroll button, maintain state.modelHistory with roll tabs, and execute isolated single-model lifecycles.
4. In static/css/benchmark.css: style reroll button and roll tabs.
5. In benchmark JSON export: include full roll history per model.
6. Recompile TypeScript and verify in live browser on /bench.

## Browser UI and intended live verification

Intended UI home: /bench

Current availability: benchmark lab is live, reroll button and Retry-After backoff are in development

Live steps when available:
1. Navigate to http://localhost:4444/bench.
   - expected: Model card renders Reroll button and roll history tabs.
2. Run a model in benchmark, then click Reroll.
   - expected: Card re-executes cleanly, saves previous roll, and renders Roll #1 / Roll #2 switcher.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Model card renders Reroll button and roll history tabs, switching tabs swaps card content, export JSON has roll history.
   - observed: Verified live in browser using Playwright on http://localhost:4444/bench. Reroll button and roll switcher tabs #1 and #2 rendered and interactive. Export JSON verified to contain rolls_count: 2 and full history array.
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Click Load on past run, click #1 tab, click #2 tab, click Export JSON.
   - observed: Navigated to /bench, loaded past run, clicked Tab #1 (verified active class and roll 1 metrics), clicked Tab #2 (verified active class and roll 2 prose), clicked #bench-export-json and verified download payload.
3. Run the targeted regression test for the mechanism.
   - expected: Pytest test_benchmark_routes.py passes with 9 tests, npm run build:ts compiles clean.
   - observed: python -m pytest tests/test_benchmark_routes.py passed 9/9 in 6.74s, npm run build:ts compiled with exit code 0.

## Acceptance

- [x] Primary llm-client inspects Retry-After header on 429 and delays accordingly
- [x] Benchmark /api/bench/chat retries on 429/5xx respecting Retry-After up to 3 attempts
- [x] Per-model Reroll button re-runs single model through lifecycle (load/generate/unload)
- [x] Card preserves past rolls with selectable roll tabs
- [x] Export JSON includes complete roll history for each model
- [x] Zero em-dashes and TypeScript cleanly recompiled

## Files

- `static/js/llm-client.ts`
- `static/js/llm-client.js`
- `routes/benchmark.py`
- `static/js/benchmark/benchmark.js`
- `static/css/benchmark.css`
- `tests/test_benchmark_routes.py`
