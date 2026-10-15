---
type: task
status: done
area: ui
priority: medium
---

# Task 339 — Stranger naming & acquaintance mechanism

**Status:** In Review — designed with Tommy 2026-08-24, implemented same
day. Names are learned ONLY by hearing them spoken (or a name tag);
sight is recognition and never reveals a name.

## The decided design (Tommy's call)

"Hi, my name is X" is the human way, and the old sighting-reveal was
unrealistic ("how do you SEE someone's name?"). Decided:

- **A name spoken aloud in earshot teaches that name.** One mechanism
  covers self-intros ("hi, I'm rosa"), direct address ("hey Miki, look
  over here"), and third-party mentions ("order up for rosa!") — no
  phrase parsing, just word-boundary matching against the real names +
  aliases of characters present in the area. Same-area only: muffled
  speech through a wall teaches nothing. Directed whispers never teach
  (the content was private).
- **Sight = recognition, not knowledge.** Seeing someone registers the
  relationship (stable masked label, closeness/entertainment anchor) but
  the `first_sighting` flag — now semantically "name unknown" — is only
  cleared by learning the name. Re-looking never reveals anything.
- **Examine doesn't mind-read.** An unmet character's examine output
  masks their real name and aliases (replaced by
  `unknown_display_name()`), UNLESS they wear an item tagged `nametag`
  → "A name tag reads \"rosa\"". Authors use the nametag prop for
  intentional description-based reveals.
- The full room description also gates the full-description prose on
  name knowledge (descriptions may name people in text).

## How

- `Player.learn_name(other, tick)` / `Player.knows_name(other)` — the
  name-knowledge primitives (`first_sighting` = name unknown).
- `SpeechBroadcaster._teach_names_from_speech` — the scan, hooked into
  `broadcast_speech` after same-area hearing entries; logs
  "[listener] learns that the woman is called \"rosa\"." per actual
  learning; idempotent.
- `area_description.py` — recognition-only sighting; name_known gates
  the label AND the full-description prose.
- `scene_snapshot.py` — same contract for the panel (`knows_name`).
- `examine_actions.py` — `_mask_character_name_for_viewer` +
  `_wears_nametag` on both character-examine branches.
- Panel hover foot reads "recognized/stranger — you don't know their
  name yet".

## Steps to verify

`tests/test_name_learning.py` (8): self-intro teaches, third-party
mention teaches, non-matching speech doesn't, speaker doesn't learn own
name, idempotent + logged once, scene never reveals by re-sighting but
flips after learning, examine masks, nametag reveals. Updated two
`test_area_description.py` tests that pinned the old sighting-reveal.
Full suite 1108 green.

## What

TODO

## Why

TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Human Turn scene → People chips / hover card; Game command
input or public speech action → Event Stream; observer's scene updates after
hearing a name.

Current availability: Name learning is implemented on same-area audible
speech; sight only registers recognition. Examine masks unknown names unless a
visible `nametag` item reveals one. The card records mechanism tests but no
browser path through the integrated Human Turn panel.

Live steps when available:
1. In a scratch scenario, put Rosa, Alice, and an observer in one room; use the
   observer's scene and hover card before Rosa speaks.
   - expected: the observer recognizes Rosa but sees a stable masked label and
     the hint that her name is not known.
2. Have Rosa use public speech that contains her name, then refresh the
   observer's People chips and inspect the Event Stream.
   - expected: a same-room listener learns “Rosa”; the label changes to the
     real name and one learning event is logged.
3. Repeat with a directed whisper and with Rosa speaking from behind a closed
   wall; also examine an unknown person wearing a `nametag` item.
   - expected: neither private nor muffled speech teaches the name; the tag
     explicitly reveals the written name on examine.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
