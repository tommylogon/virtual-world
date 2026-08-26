# Regression Testing: Programmable Agent Script (Live Test Runner)

**Filed**: 2026-07-15
**Priority**: High
**Status**: Todo (moved back from done 2026-08-03 — the documented scripted runner was never built; a separate Playwright harness exists in tools/test_all.cjs etc., but not the spec'd scenario.json + expect_contains flow)

---

## Summary

Create a programmable agent test runner that plays through the default scenario automatically, following a script of actions, to verify the happy flow works end-to-end. This is a live test (against the real engine, not mocked) that catches regressions.

## Design

### Concept

A test script defines a sequence of actions an agent should take, along with expected results. The test runner executes these actions against the world engine and reports pass/fail for each step.

### Script Format

```json
{
  "name": "mansion_happy_flow",
  "description": "Play through the mansion scenario main quest line",
  "scenario": "scenarios/mansion2.json",
  "steps": [
    { "action": "look", "expect_contains": "Foyer" },
    { "action": "go east", "expect_contains": "Kitchen" },
    { "action": "take iron_key", "expect_contains": "taken" },
    { "action": "go west", "expect_contains": "Foyer" },
    { "action": "use iron_key on garden_way", "expect_contains": "unlocked" },
    { "action": "go south", "expect_contains": "Garden" }
  ]
}
```

### Assertions

Each step can have:
- `expect_contains`: output must contain this string
- `expect_not_contains`: output must NOT contain this string
- `expect_state`: check world state after action (e.g., player room, item in inventory)
- `expect_error`: action is expected to fail with this error message

### Implementation

Create a `test_runner.py` script that:
1. Loads the scenario
2. Creates the engine
3. For each step:
   - Executes the action against the engine
   - Checks assertions
   - Reports pass/fail
4. Outputs a summary

### Integration

These scripts should be runnable from the command line:
```
python test_runner.py scenarios/mansion_happy_flow.json
```

Or better, store the test scripts alongside the code so they can be run as unit tests:
```
pytest tests/test_scenarios.py
```

### Test Coverage (Happy Flow)

The default scenario should have a script covering:
- Look around
- Move between areas (via ways)
- Take items
- Use items (eat food, drink water)
- Use item on target (unlock door with key)
- Examine items
- Open/close ways
- Talk (player speech)
- Character state changes (sleep, rest)

## Files Affected

- `opencode_tools/test_runner.py` — new test runner script
- `tests/test_scenarios.py` — or new test file
- Scenario test scripts: one per scenario
