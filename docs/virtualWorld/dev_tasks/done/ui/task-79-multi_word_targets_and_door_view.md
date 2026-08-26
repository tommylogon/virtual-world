# Multi-Word Targets + Way View on Open

**Filed**: 2026-07-20
**Completed**: 2026-07-20
**Priority**: High
**Status**: Done

---

## Summary

Two fixes found while testing "open swinging door" from the living room.

## Fix 1: Multi-Word Target Names

`tokenize_command()` splits on spaces, so `"open swinging door"` produced tokens `["open", "swinging", "door"]` and `tokens[1]` was `"swinging"` — broke all multi-word targets (`swinging door`, `front door`, `rusty key`, etc.) unless quoted.

**Fix:** Replaced `tokens[1]` with `' '.join(tokens[1:])` in all single-target branches. For branches with keyword separators (`use X on Y`, `attack X with Y`, `rest [N] on Y`), added keyword-index search in tokens to split at the right point.

### Branches Changed

| Branch | Old | New |
|--------|-----|-----|
| go | `tokens[1]` | `' '.join(tokens[1:])` |
| open / close | `tokens[1]` | `' '.join(tokens[1:])` |
| eat / drink | `tokens[1]` | `' '.join(tokens[1:])` |
| use | `tokens[2] == "on"` | Find `"on"` index in tokens[1:], split there |
| examine | `tokens[1]` | `' '.join(tokens[1:])` |
| take | `tokens[1]` | Join `tokens[1:-1]` if last token is digit, else `tokens[1:]` |
| drop | `tokens[1]` | `' '.join(tokens[1:])` |
| rest / sleep | `tokens[1].isdigit()`, `tokens[2]==on` | Find `"on"` index in tokens[1:], split there |
| toggle | `tokens[1]` | `' '.join(tokens[1:])` |
| attack | `tokens[2]=="with"` | Find `"with"` index in tokens[1:], split there |
| speak / say | `tokens[1]` | `' '.join(tokens[1:])` |

## Fix 2: `visible_in_direction` on Way Open

`toggle_way()` returned just `"You open the swinging door."` — the `visible_in_direction` text from the exit definition was only shown in `get_area_description()`, not in the action result. So it never appeared in `=== WHAT HAPPENED ===` for agent reactions.

**Fix:** Both `toggle_way()` and `toggle_way_by_id()` now look up the room→door connection edge's `visible_in_direction` property and append it as a second line when opening:

```
You open the swinging door.
The kitchen, with a checkered tablecloth on the table and dried herbs hanging from the ceiling.
```

## Files Changed

| File | Change |
|------|--------|
| `app.py` | All branches updated to use `' '.join(tokens[1:])` with proper keyword splitting for `use`, `attack`, `rest`, `take` |
| `virtual_world_engine.py` | `toggle_way()` saves `way_edge`; both toggle methods append `visible_in_direction` on open |

## Tests

13/13 pass (`test_tokenizer.py` + `test_emote.py`)
