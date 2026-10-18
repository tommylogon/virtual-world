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
