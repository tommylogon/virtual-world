---
type: bug
status: todo
area: characters
priority: high
---

# bug-519: Editorial rewrite notes are stored inside character memories, so a character recalls its own drafting notes

**Filed:** 2026-10-04
**Related:** task-685, task-690, task-692

## Goal

Reject second-person editorial commentary at the memory-admission boundary so a memory can only contain first-person experience.

## Acceptance

- Reproduce from the saved scenario, not an export: read
  `players.miki.memories[]` in `data/scenarios/mansion.json` and assert
  one `text` contains both the memory and a second paragraph of
  reviewer-facing commentary. It does today.
- A memory entering the store is rejected or stripped when it contains
  second-person editorial register ("shorter, punchier", "the original
  had", "reads like", "typo soup", "keeps the ... moment"). Assert with
  a fixture using the exact residue above.
- Assert the *first-person memory itself survives* — this must not
  become a filter that silently drops the good half.
- Assert a character cannot later recall the residue: the
  `=== I REMEMBER ===` block (`memory-context.ts`) contains no
  editorial text.
- Establish **how it got in** before fixing: the memory is
  `source: manual`, which `memory-view.ts` sets on inspector-authored
  memories — so either the authoring UI accepted pasted LLM revision
  notes, or a rewrite step wrote through that path. Name the writer.
  Do not patch the store and leave the writer in place.
- Check whether `miki`'s other manual memories are clean before
  declaring the scope; only one of seven was visibly affected.

## Measured 2026-10-04, in saved state (not an export artifact)

`data/scenarios/mansion.json` → `players.miki.memories[].text`, one
memory's full value:

    okay this place is like heaven for ambiance! ... where she goes,
    i go.

    shorter, punchier, still sounds like miki rambling. keeps the
    asmr-brain moment, the fear, and the clinginess to elena all in one
    breath. the original had the right energy just needed the spelling
    fixed and the run-on tightened so it reads like nervous excitement
    instead of a typo soup.

The first paragraph is a memory. The second is a **rewrite note to a
reviewer** — it talks *about* the memory in the third person ("the
original", "keeps the ... moment"), which no experiencing character
would do. Stored as `type: observation`, `importance: 5`,
`source: manual`, `tick: 0`, `salience_override: 0`.

It appears in all three occurrences across the run export
(lines 613, 784, 1010 of the 2026-10-04 log), so it is recalled
repeatedly — every `think-decide` for miki carries it in
`=== I REMEMBER ===`, and the LLM is being shown its own editing
notes as a lived recollection.

`miki` has 7 memories; 4 are `source: manual`, 3 are
`source: auto`. Only the one above shows the residue in the export,
but the mechanism has not been isolated, so the other three are
uncleared rather than clean.

## Why this is not a rendering bug

The stored `text` contains `\n\n` and both paragraphs. Verified by
loading the JSON directly, so the export is faithfully showing what the
world holds.

## Relation to task-692

Surfaced while reading a full run export for the narration v2 work.
Not narration's defect — filed separately because it is a memory-integrity
bug and the fix belongs at the memory-admission boundary, not in the
director pass.
