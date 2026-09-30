---
type: bug
status: todo
area: library
priority: high
---

# bug-512: /api/tags/validate returns nonsense fuzzy suggestions for unknown tags

**Filed:** 2026-09-30
**Related:** 

## Goal

Measured against the live Kraktooth world, GET /api/tags/validate proposes: wanderer -> underwear, fear -> footwear, silence -> evidence, hostile -> hosiery, master -> water, chaos -> ghost, attention -> mansion. Only tools -> tool and mechanisms -> mechanism are correct. difflib get_close_matches at cutoff 0.6 is far too permissive for two-to-ten character ids, and a caller that trusts a suggestion will silently write a worse tag than the one it rejected. Raise the cutoff and/or require the match to share a length, and verify no caller depends on the current loose behaviour. Consumers should be able to distinguish 'near miss worth suggesting' from 'no idea'.

## Acceptance

- TODO
