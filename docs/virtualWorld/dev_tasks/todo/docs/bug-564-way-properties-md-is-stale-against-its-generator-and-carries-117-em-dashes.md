---
type: bug
status: todo
area: docs
priority: low
effort: S
wiki: "[[World Building/Way Properties]]"
related: [bug-529, bug-530]
---

# bug-564: Way Properties.md is stale against its generator and carries 117 em-dashes

**Filed:** 2026-10-21
**Related:** bug-529, bug-530

<!-- deps:start -->
**Related:** [[bug-529-worldpainter-compiled-ways-carry-no-tags-so-every-generated-way-reads-tags-none]], [[bug-530-compiled-open-outdoor-ways-miss-prevent-close-so-a-road-into-the-forest-can-be-hand-closed]]
<!-- deps:end -->

## What

The committed generated page `docs/virtualWorld/World Building/Way Properties.md` no longer matches its generator, and it carries 117 em-dash (U+2014) characters. `tests/test_way_property_index.py::test_generated_page_is_current` fails on a clean checkout because the generator now emits plain hyphens. Both the page and `tools/way_property_index.py` are unmodified in the working tree, so this is committed drift, not a local edit. Regenerate the page and keep the em-dash ban true in the generated output.

## Why

Two separate problems in one artifact: (1) the repo-wide em-dash ban is violated in a committed doc, which is the exact character that has corrupted files under PowerShell and edit-tool surgery; (2) the generated page is stale, so a reader is looking at punctuation the generator no longer produces, and a pytest gate is red for everyone. `tools/way_property_index.py --check` exits 0, so the usual gate does not catch it: only the pytest currency test does.

## How

1. Run `python tools/way_property_index.py --write` and inspect the diff: it should change punctuation only, no property rows. 2. Confirm the file contains zero U+2014. 3. Re-run `python -m pytest tests/test_way_property_index.py` and `python tools/way_property_index.py --check`. 4. Decide whether page currency belongs in the documented gate list next to `--check` (today only the pytest test enforces it), and record whichever answer is chosen where the gates are listed. Do not hand-edit the generated page.

## Browser UI and intended live verification

Intended UI home: Not applicable

Current availability: The page exists and renders in Obsidian today with the stale punctuation.

Why no browser UI: This is a generated vault page and a pytest gate. There is no app surface; the reader meets it as a document.

Alternative verification steps:
1. Run `python -m pytest tests/test_way_property_index.py` and confirm it fails on `test_generated_page_is_current` before the fix.
2. Read the generated page and search it for U+2014; count 117 before the fix.
3. After `--write`, re-run the test (green) and recount the character (zero).

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] `python tools/way_property_index.py --write` regenerates `Way Properties.md` and the file contains 0 U+2014.
- [ ] The regenerated page differs from the committed one in punctuation/normalisation only: the property rows and their baselined consumers are unchanged.
- [ ] `python -m pytest tests/test_way_property_index.py` passes.
- [ ] `python tools/way_property_index.py --check` still exits 0 after the regeneration.
- [ ] The split between what `--check` verifies (declaration/consumer drift) and what the pytest test verifies (page currency) is written down where the gates are listed, so the next agent does not read `--check` as covering the page.

## Files

- `docs/virtualWorld/World Building/Way Properties.md`
- `tools/way_property_index.py`
- `tests/test_way_property_index.py`
