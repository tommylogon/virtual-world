---
group: Characters
---
# Character Interest-Tag Data Pass + Duplicate Character Cleanup (task-326, was task-322)

**Filed**: 2026-08-21  
**Priority**: High  
**Status**: In Review — implemented 2026-08-21 via tools/fix_character_interests.py;
34 characters fixed (6 full sets, 28 patches), every tag validated against item
vocabulary before write; lint `--check dead_interests` went 21 error lines → 0;
duplicate `Violet_halloway_character.json` (stale shell; richer space-named file
kept) and misplaced world-state export `labs.json` deleted after reference check;
pytest 1051 passed / 0 failed. Renumbered 322→326: parallel session claimed 322
first (task-322-system-hygiene-refactor). Reviewer note: proposal table corrected
mid-flight — lint caught dead tags in my own first draft (perfume/lipstick match
no items), and kayla.json is kayla *Jenkins* while the sister lives in
kayla-sister.json (wrong-file landmine, dodged).

---

## Summary

Bring all 44 library characters to a realistic, *matchable* interest profile:
8–14 `interest_tags` each, drawn from the 204-tag item vocabulary, mixing four
categories (2–3 mechanical, 2–3 consumables, 3–4 domain, 2–3 personal-style).
Also remove one duplicate character file and one empty junk file.

Feeds task-325 (auto-dressing) and makes NPC-relevant spawning meaningful.
Blocks task-9's interest-driven placement phase.

## Target Profile (why 8–14)

Interest tags do double duty: personality AND item-matching hooks. Verified
against the well-filled characters (miki: 13, elena: 14):

- **2–3 mechanical** (`sound_source`, `electric`, `light_source`) — drive engine spawning
- **2–3 consumables** (`candy`, `energy_drink`, `food`)
- **3–4 domain** (`occult`, `evidence`, `music`)
- **2–3 personal-style** (`jewelry`, `clothing`, `mirror`)

Under ~6 → sparse rooms; over ~15 → everything matches everything.

## Problems Found (survey 2026-08-21)

1. **7 characters with zero interests**: Gromm, Kaelen Voss, Lyrie, Viktor,
   Violet halloway, rat, plus one empty `?` file
2. **5 characters with mostly-DEAD tags** (match zero of 204 item tags):
   - satsuki 6/6 dead (`track`, `gym`, `hoodies`, `sports`, `competition`, `running`)
   - uzume-chan 6/6 dead (`farming`, `gardening`, `animals`, `livestock`, `cooking`, `produce`)
   - nia 5/6 dead (`patrol`, `suspects`, `uniform`, `gym`, `cuffs`; only `mirror` lives)
   - nina 5/6 dead (`videogames`, `strategy`, `boardgame`, `gaming`, `plush`)
   - pam 5/6 dead (`books` ≠ `book`!, `studying`, `science`, `homework`, `videogames`)
3. **Thin lists (<6)**: james(3), mamako(3), miiya(3), kayla(4), lopunny(4),
   lydia(4), koharu(4), feral goblin(5), jessie(5), kissy(5), miki takahashi(6)
4. **Dead singletons inside otherwise-fine lists**: `berry` (lopunny),
   `guitar` (brittany), `necklace` (jessie), `cigarette`/`tv`/`snack` (anna),
   `game`/`video` (amber), `sweet`/`color` (maya), `dark`/`family`/`photo`(anne ok, photo exists)
5. **Duplicate file**: two `Violet halloway*.json` entries in data/library/characters/
6. **Empty junk**: one character file named `?` with no content

## Work Plan

1. **Cleanup first**: delete duplicate Violet file (diff them first — keep the
   richer one); delete `?` file. Check world_template.json / scenarios for
   references to the removed ids before deleting.
2. **Script** `tools/fix_character_interests.py` (pattern: tools/fix_item_equipment.py):
   - Explicit per-character table (reviewed proposals below) — no silent inference
   - **Merge-not-replace**: existing live tags are kept, dead tags rewritten via
     explicit mapping, new tags appended
   - Dry-run default, `--apply` flag
   - Validates every proposed tag against the current item-tag vocabulary and
     hard-errors on unknown tags (prevents re-introducing dead tags)
3. Review dry-run output, apply.
4. Run task-323 lint to confirm zero dead interest tags remain.

## Proposal Table (drafted 2026-08-21, grounded in item vocab)

**Full sets (empty characters):**

| Character | Proposed interest_tags |
|---|---|
| Gromm | weapon, melee, meat, bone, fire, drink, wooden, heavy |
| Kaelen Voss | clue, evidence, documents, letter, key, book, journal, secret, investigation, weapon |
| Lyrie | elven, flower, linen, clothing, jewelry, candle, doll, candy |
| Viktor | weapon, armor, meat, drink, bandage, medical, money, blood |
| Violet halloway | candy, phone, music, toy, book, secret, clue, clothing |
| rat | food, cheese, warmth |

**Rewrites (dead → live):**

| Character | Rewrite |
|---|---|
| satsuki | clothing, outerwear, footwear, water, energy_drink, music, phone |
| uzume-chan | plant, vegetation, animal, food, ingredient, water, tool, meal |
| nia | weapon, clothing, evidence, clue, key, restraint, mirror, food |
| nina | candy, toy, headphones, phone, electric, energy_drink, book |
| pam | book, animal, eyewear, tea, candy, phone, knowledge |

**Top-ups (append to existing):**

| Character | Add |
|---|---|
| kayla | perfume, lipstick, jewelry, restraint, cosmetic |
| kissy | cosmetic, clothing, jewelry, flower |
| lydia | lipstick, clothing, music, drink |
| mamako | tea, soap, flower, warmth, clothing |
| miiya | toy, headphones, energy_drink, drink |
| james | tea, journal, knowledge, writing |
| jessie | bandage, drink, clothing, weapon (+ necklace→drop, jewelry already present) |
| koharu | flower, tea, doll, clothing |
| miki takahashi | food, drink, clothing, candy, knife |
| anna | wine, money, phone, clothing (+ cigarette/tv/snack→drop) |
| brittany | guitar→instrument, + leather |
| dr. eliza reed | tea, knowledge, writing |
| feral goblin | gold, key |
| lopunny | berry→honey, + plant, flower, warmth |

**Leave untouched (already 8+ and healthy):** miki, amber, angeline, anne,
audrey, elena vance, ghost, jake halloway, kayla jenkins, kyrie johansen,
maya, sammy lopez, tala, the butcher, whiskers.

## Files

- `tools/fix_character_interests.py` (new script)
- `data/library/characters/*.json` (data changes)
- duplicate Violet + `?` files (deletions)

## Verification

- `python tools/fix_character_interests.py` dry-run reviewed before apply
- `python -m pytest tests/ -q -k "not mcp and not emote"`
- Re-run survey snippet: 0 characters with dead-only lists, all counts 8–14
  (animals exempt: rat/goblin/whiskers may stay shorter)

## Gotcha: Library Fix ≠ Live World Fix

Characters are snapshot into scenarios at import time (same pattern as items —
AGENTS.md "duplicate placements snapshot the library entry at build time"). A
running scenario keeps the OLD interest tags even after this pass. Options:

1. Re-import affected characters from the library (cheap, per-scenario), or
2. Extend `POST /api/library/refresh-to-world` to cover characters
   (`routes/library_routes.py:619` currently handles items with `library_id`)

Pick option 2 if scenario characters carry meaningful runtime state (memories,
relationships) that re-importing would wipe — which they do. Fold the character
support into this task or spin a follow-up; either way, don't call this done
until a loaded scenario reflects the new tags after refresh.

## Dependencies

- None (can start immediately)
- Feeds: task-325 (auto-dress style matching), task-9 phase 2 (interest-weighted spawns)
- Pairs with: task-323 lint (regression guard)
