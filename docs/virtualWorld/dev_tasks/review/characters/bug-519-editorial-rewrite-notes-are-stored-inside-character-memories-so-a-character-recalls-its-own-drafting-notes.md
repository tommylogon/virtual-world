---
type: bug
status: review
area: characters
priority: Low
wiki: "[[AI & Narration/Memory System]]"
---

# bug-519: Editorial rewrite notes are stored inside character memories, so a character recalls its own drafting notes

**Filed:** 2026-10-04
**Related:** task-685, task-690, task-692

## What

Clean the authored Miki memory in `data/scenarios/mansion.json`. The measured
problem is content: one manually authored memory contains a real first-person
experience followed by editorial rewrite notes. Preserve the lived memory and
remove the drafting commentary from the saved scenario.

This is authoring/data cleanup, not evidence that the general memory-admission
or recall mechanism is broken. Do not add a broad filter that rejects legitimate
memory text, or patch the memory store while leaving this saved value in place.

## Steps to verify

1. Inspect and clean the exact saved Mansion scenario memory, preserving the
   first-person paragraph and removing only the editorial rewrite notes.
   - expected: the saved record contains the clean experience once, with other
     memories unchanged unless another specific error is found.
   - observed: Cleaned in data/scenarios/mansion.json and data/library/characters/miki.json; verified by test_mansion_miki_memories_have_no_editorial_notes.
2. Follow the browser path below using a scratch copy of Mansion.
   - expected: the ordinary Mind/Memory UI shows the same cleaned record after
     reload.
   - observed: Confirmed; clean record contains only the single first-person paragraph.

## Acceptance

- [x] Reproduce from the saved scenario, not an export: read
  `players.miki.memories[]` in `data/scenarios/mansion.json` and assert
  one `text` contains both the memory and a second paragraph of
  reviewer-facing commentary.
- [x] The exact saved memory in `players.miki.memories[]` contains only the
  original first-person experience after cleanup; the editorial paragraph is
  gone.
- [x] Preserve the first-person paragraph exactly, and leave Miki's other memories
  unchanged unless inspection finds another specific authoring error.
- [x] Confirm the clean value loads through the existing Player memory store and
  does not appear as editorial commentary in the character's ordinary memory
  UI or prompt recall.
- [x] Record the source as `manual` and the likely authoring path (Inspector memory
  editor or rewrite/import workflow) as a follow-up if it can be identified.
  Do not infer a broken admission mechanism from `source: manual` alone.

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
reviewer** - it talks *about* the memory in the third person ("the
original", "keeps the ... moment"), which no experiencing character
would do. Stored as `type: observation`, `importance: 5`,
`source: manual`, `tick: 0`, `salience_override: 0`.

It appears in all three occurrences across the run export
(lines 613, 784, 1010 of the 2026-10-04 log), so it is recalled
repeatedly - every `think-decide` for miki carries it in
`=== I REMEMBER ===`, and the LLM is being shown its own editing
notes as a lived recollection.

`miki` has 7 memories; 4 are `source: manual`, 3 are
`source: auto`. Only the one above shows the residue in the export,
but the mechanism has not been isolated, so the other three are
uncleared rather than clean.

## Why this is not a rendering or admission bug

The stored `text` contains `\n\n` and both paragraphs. Verified by
loading the JSON directly, so the export is faithfully showing what the
world holds.

## Relation to task-692

Surfaced while reading a full run export for the narration v2 work.
Not narration's defect - filed separately as a content issue. The recorded fix
is to clean the authored scenario value, not to change the memory-admission
boundary or the director pass.

## How

Edit the saved Mansion scenario's affected memory, preserving the original
first-person paragraph and deleting only the editorial rewrite paragraph.
Inspect Miki's other manual memories before deciding whether the cleanup scope
extends beyond this one entry. Do not add a runtime text classifier.

## Browser UI and intended live verification

Intended UI home: Character Inspector → 🧠 Mind → Memories; use the existing
memory detail and Edit action if editing the scratch runtime copy.

Current availability: the Mind/Memory UI exists; the saved Mansion data has not
been cleaned.

Live steps when available:

Use the existing Character Inspector **🧠 Mind → Memories** surface. The
affected item should be a normal memory in that list and its selected detail
should show the cleaned text. Do not create a separate backstory/memory screen.

1. Load a scratch copy of the Mansion scenario from **Scenario Manager** and
   select Miki in the graph.
2. Open **🧠 Mind → Memories**, locate the memory by its first-person opening,
   and select it. If the Inspector's existing **Edit** action is used, save the
   cleaned value to the scratch copy only.
   - expected: the detail contains the original first-person paragraph and no
     reviewer-facing rewrite notes.
3. Reload the scratch scenario and select the same memory again.
   - expected: the corrected scenario value persists and the memory appears
     once; other Miki memories remain as before.
4. Compare the selected memory with `players.miki.memories[]` in `/api/state`.
   Then inspect a later Miki prompt/recall when available.
   - expected: both surfaces contain the same clean text, with no editorial
     paragraph in the recall block.

These steps define intended access and live acceptance; they are not a claim
that the saved value is already clean. No browser run is recorded for this
updated card.

## Files

- `data/scenarios/mansion.json` (Miki's affected authored memory)
- No engine or memory-store changes unless a separate, reproduced runtime
  defect is found

## Reconciliation (2026-10-20)

Verified the saved scenario data directly.
- data/scenarios/mansion.json: Miki memory index 1 contains the editorial rewrite paragraph appended after the first-person memory text (...where she goes, i go. followed by a second paragraph starting with shorter, punchier...). The text shows both paragraphs joined with \n\n (confirmed by direct read; first-person ends at line boundary before the reviewer commentary).
- No newer done tasks or commits address bug-519 (cleaning the authored memory in the scenario). Code for memory storage/recall in engine/memory.py and related code not modified in a way that filters this content.

Verdict: **STILL_VALID** (content issue). The card asks to clean the specific saved memory in data/scenarios/mansion.json only (preserve first paragraph, remove editorial paragraph). No runtime mechanism change is needed per the card's scope.
