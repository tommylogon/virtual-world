---
type: bug
status: done
area: library
priority: high
related: ['task-750', 'task-291', 'task-206']
---

# bug-512: /api/tags/validate returns nonsense fuzzy suggestions for unknown tags

**Filed:** 2026-09-30
**Related:** 

<!-- deps:start -->
**Related:** [[task-750-migrate-the-mature-boolean-to-a-mature-content-tag-registered-and-scanned-across-node-types]], [[task-291-unified-library-api-and-data-driven-catalogs]], [[task-206-mature-content-toggle]]
<!-- deps:end -->

## What

Measured against the live Kraktooth world, GET /api/tags/validate proposes: wanderer -> underwear, fear -> footwear, silence -> evidence, hostile -> hosiery, master -> water, chaos -> ghost, attention -> mansion. Only tools -> tool and mechanisms -> mechanism are correct. difflib get_close_matches at cutoff 0.6 is far too permissive for two-to-ten character ids, and a caller that trusts a suggestion will silently write a worse tag than the one it rejected. Raise the cutoff and/or require the match to share a length, and verify no caller depends on the current loose behaviour. Consumers should be able to distinguish 'near miss worth suggesting' from 'no idea'.

## Acceptance

- [x] The matcher is strict enough to reject every reported nonsense pair.
- [x] Real inflections (`tools` -> `tool`, `mechanisms` -> `mechanism`) still suggest.
- [x] `null` is returned when there is no confident match, so a caller can tell
      "near miss worth suggesting" from "no idea".
- [x] No caller depended on the loose behaviour: `validate_tags_on_save` only
      logs/warns, and the `/api/tags/validate` consumer already handles `null`.

## What was done 2026-10-02

`routes/helpers.py` now owns `closest_tag_match(tag, candidates)` - difflib at
cutoff **0.8** plus a length guard (`|len(a)-len(b)| <= max(2, len(a)//3)`), which
keeps plural/singular pairs and short typos while rejecting the reported pairs.
`validate_tags_on_save` and `routes/tags.py` both use it, so the save path and the
endpoint agree.

Evidence:

- `python -m pytest tests/test_tags_validate.py -q` - 6 passed.
- The endpoint returns `suggestion: null` for `wanderer`/`fear` and the correct
  singular for `tools`/`mechanisms` (asserted through `create_app().test_client()`).

## Verified 2026-10-21

Re-measured on the working tree, both the mechanism and the live route:

- `python -m pytest tests/test_tags_validate.py` - 6 passed.
- `GET /api/tags/validate` through `create_app().test_client()` against the real
  `data/library/tags` registry, all nine reported ids in one request:

  ```
  wanderer -> None      fear -> None        silence -> None
  hostile -> None       master -> None      chaos -> None
  attention -> None     tools -> 'tool'     mechanisms -> 'mechanism'
  ```

  All seven nonsense pairs return `suggestion: null`; both real inflections
  still suggest. `valid: []` because none of the nine ids is registered, which
  is the fixture's premise, not a defect.
- Both callers share `routes/helpers.py:closest_tag_match` (`routes/tags.py:50`,
  `validate_tags_on_save` at `routes/helpers.py:399`), so the endpoint and the
  save path cannot disagree.

## Why

difflib.get_close_matches with default 0.6 cutoff generated unrelated fuzzy suggestions (e.g. `wanderer` -> `underwear`, `fear` -> `footwear`), which risked corrupting tag metadata when callers accepted suggestions.

## How

Implemented `closest_tag_match` in `routes/helpers.py` with cutoff 0.8 and a strict length difference guard (`abs(len(a) - len(b)) <= max(2, len(a) // 3)`). Returning None when no confident match exists.

## Steps to verify

1. Run tag validation unit tests
   - expected: pytest tests/test_tags_validate.py passes
   - observed: 6 passed in tests/test_tags_validate.py
2. Verify fuzzy suggestion behavior on unknown tags
   - expected: Unrelated tags return suggestion null; inflections like tools -> tool still match
   - observed: Verified on test client requests

## Files

- `routes/helpers.py`
- `routes/tags.py`
- `tests/test_tags_validate.py`
