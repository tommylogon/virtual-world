---
type: bug
status: review
area: library
priority: high
---

# bug-512: /api/tags/validate returns nonsense fuzzy suggestions for unknown tags

**Filed:** 2026-09-30
**Related:** 

## Goal

Measured against the live Kraktooth world, GET /api/tags/validate proposes: wanderer -> underwear, fear -> footwear, silence -> evidence, hostile -> hosiery, master -> water, chaos -> ghost, attention -> mansion. Only tools -> tool and mechanisms -> mechanism are correct. difflib get_close_matches at cutoff 0.6 is far too permissive for two-to-ten character ids, and a caller that trusts a suggestion will silently write a worse tag than the one it rejected. Raise the cutoff and/or require the match to share a length, and verify no caller depends on the current loose behaviour. Consumers should be able to distinguish 'near miss worth suggesting' from 'no idea'.

## Acceptance

- [x] The matcher is strict enough to reject every reported nonsense pair.
- [x] Real inflections (`tools` -> `tool`, `mechanisms` -> `mechanism`) still suggest.
- [x] `null` is returned when there is no confident match, so a caller can tell
      "near miss worth suggesting" from "no idea".
- [x] No caller depended on the loose behaviour: `validate_tags_on_save` only
      logs/warns, and the `/api/tags/validate` consumer already handles `null`.

## What was done 2026-10-02

`routes/helpers.py` now owns `closest_tag_match(tag, candidates)` — difflib at
cutoff **0.8** plus a length guard (`|len(a)-len(b)| <= max(2, len(a)//3)`), which
keeps plural/singular pairs and short typos while rejecting the reported pairs.
`validate_tags_on_save` and `routes/tags.py` both use it, so the save path and the
endpoint agree.

Evidence:

- `python -m pytest tests/test_tags_validate.py -q` — 6 passed.
- The endpoint returns `suggestion: null` for `wanderer`/`fear` and the correct
  singular for `tools`/`mechanisms` (asserted through `create_app().test_client()`).
