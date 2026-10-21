---
type: bug
status: todo
area: testing
priority: medium
horizon: now
effort: S
wiki: "[[Feature Map]]"
---

# bug-557: The precommit vault guard calls feature_pages.py --check, a flag the tool does not implement

**Filed:** 2026-10-18
**Related:** 

## What

Restore a working `--check` mode to `tools/feature_pages.py` (or drop the step from `npm run precommit`). The vault guard chain cannot pass because the step that checks every Feature Map row has a page exits on an argparse error instead of a finding.

## Why

Measured 2026-10-18: `python tools/feature_pages.py --check` exits 2 with `feature_pages.py: error: unrecognized arguments: --check`; the parser only offers `[-h] [--report]`. `npm run precommit` chains `... && python tools/feature_pages.py --check && python tools/doc_tags.py --check && python tools/doc_connected.py --check`, so once the earlier steps pass the chain dies at a usage error and the two guards after it never run. `AGENTS.md` documents `feature_pages.py --check` (and `--scaffold`) as the gate, so the docs and the tool disagree. Surrounding guards were verified working in the same run: `doc_links.py --check` (1 broken link, pre-existing: task-819 links `[[Developer Tooling]]`, a note that lives at `docs/design/`, outside the vault root), `doc_tags.py --check` exit 0, `doc_connected.py --check` exit 0.

## How

Add the `--check` mode the gate already claims: run the same comparison `--report` prints and exit non-zero on findings, so the step reports a real defect rather than a broken invocation. Decide separately whether `--scaffold` should exist (docs claim it and it never overwrites prose); if it is not coming, delete the claim from `AGENTS.md` instead of leaving a gate that points at nothing. Do not paper over the gap by removing the step from `precommit` unless the check is genuinely redundant.

## Browser UI and intended live verification

N/A: this is a repository gate, not a world feature. Observable alternative: run `npm run precommit` end to end and read which guard stops it.

## Steps to verify

1. `python tools/feature_pages.py --check`
   - expected: exits 0 on a clean vault, or exits 1 listing real findings; never exit 2 on an unrecognized argument.
   - observed: TODO
2. `npm run precommit`
   - expected: runs all four vault guards and reports the first real finding set.
   - observed: TODO

## Acceptance

- [ ] `feature_pages.py --check` exists and its exit code means a finding, not a usage error.
- [ ] `npm run precommit` reaches `doc_tags.py --check` and `doc_connected.py --check`.
- [ ] `AGENTS.md` and the tool agree on which flags exist.

## Files

- `tools/feature_pages.py`
- `package.json (the precommit script)`
- `AGENTS.md (the Vault guards table)`

## Reconciliation (2026-10-20) - STILL_VALID, re-measured

**Verdict: STILL_VALID.** Nothing newer has implemented `--check` or removed the step from `precommit`. The defect is exactly as the card describes it.

**Re-measured 2026-10-20.**
- `python tools/feature_pages.py --check` → `feature_pages.py: error: unrecognized arguments: --check`; exit 2. Unchanged.
- `python tools/feature_pages.py --help` → `usage: feature_pages.py [-h] [--report]`. Still only `--report`.
- `python tools/feature_pages.py --report` → exit 0, prints the row → deep-doc table (38 rows counted in the first page of output; the full report is longer).
- `package.json:26` - the `precommit` script still chains `... && python tools/feature_pages.py --check && python tools/doc_tags.py --check && python tools/doc_connected.py --check`. Unchanged.
- `AGENTS.md:752` - the Vault guards table still advertises `python tools/feature_pages.py --check` and `--scaffold`. Unchanged.

**Newer work checked and found not to have touched it.** `git log --oneline -10 -- tools/feature_pages.py` returns only `aabbe84d`, `476734fa`, `8cba8f2f`, all older than the card's 2026-10-18 filing. No commit between then and 2026-10-20 adds the flag.

**Counts.** `grep -c "feature_pages.py --check" package.json AGENTS.md` → 1 hit in `package.json:26`, 1 hit in `AGENTS.md:752`. Both still reference the flag the tool does not implement.

**Cited facts.** All line numbers in the card (`api.ts:24`, `timeskip.py:243-245`, `package.json` chain, `AGENTS.md` table) were re-verified against the current tree and still hold. The card is accurate as written; left in `todo`.
