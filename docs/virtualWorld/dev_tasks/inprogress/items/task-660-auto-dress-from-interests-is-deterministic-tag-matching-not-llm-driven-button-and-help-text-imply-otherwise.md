---
type: task
status: inprogress
area: items
priority: medium
---

# task-660: Auto-Dress from Interests is deterministic tag matching, not LLM-driven; button and help text imply otherwise

**Filed:** 2026-10-01
**Related:** task-325, task-654

## Goal

Replace or augment engine/dressing.py auto_dress() tag-intersection selection with an LLM pass so the chosen gear fits the CHARACTER rather than merely sharing a tag, keeping the deterministic path as the fallback when no LLM is configured. Verify live in the browser.

## Problem

The inspector button `🤖 Auto-Dress from Interests`
(`static/js/inspector/agent-view.js:956`, task-325) presents as an LLM feature --
the robot emoji, the `data-help="autodress"` entry
(`static/js/ui/help-center.js:169`) describes it as picking gear. The
implementation is deterministic set intersection:

    interest = {str(t).lower().strip() for t in (player.interest_tags or [])}
    ...
    if interest:
        if not (tags & interest):
            continue

(`engine/dressing.py:62`, `:77-79`). Nothing calls an LLM. `POST /api/auto_dress`
(`routes/action.py:56`) -> `world.auto_dress_character` -> `auto_dress`
(`engine/dressing.py:54`), which hydrates each surviving candidate via
`gs.effects._hydrate_item`, adds `EDGE_CARRYING`, and equips through
`equipment.equip_item`.

The consequence is that selection is driven by the item library's tag
vocabulary, not by the character. Two measured problems:

1. **Tag overlap produces arbitrary gear.** Harren Cobb's `interest_tags` are
   `metal, tools, goblin_raids, iron, repair, temper, the_merchant, the_road`.
   None of those match clothing, so the intersection is empty and he falls to the
   no-interests branch, which accepts anything tagged
   `clothing/armor/wear/wearable` and shuffles (`engine/dressing.py:80-83`,
   `:98`). The result is a plausible but arbitrary wardrobe -- the same code
   would dress a farmer and a merchant from the same pool.
2. **The item vocabulary is noisy.** `apron` carries tags `clothing, meat,
   blood` (rawhide), so a meat-adjacent interest can pull it in for reasons that
   have nothing to do with being dressed.

Worth stating plainly: **this is not a bug report against a broken feature.**
The deterministic path works, is weather-aware (`:84-88`), and is idempotent by
construction (`:10-12`, `:103-110`). The gap is that the affordance promises
judgement and delivers a shuffle, so the honest options are to make it LLM-driven
or to stop implying otherwise.

Note the runtime asymmetry, since it bounds where the LLM can help:
`auto_dress` reads `player_manager.players[name].interest_tags` and hydrates into
the LIVE graph. There is no library-side path, so it dresses an already-imported
character and cannot author a `data/library/characters/` template.

Related but distinct: `task-654` records that `player.equipped` and the equipment
graph edges are two sources of truth and that the declared slot vocabulary
(`hand`) disagrees with the used one (`hand_right`), which is why auto-dress
passes `slot=cand["slots"][0]` and can land gear in a slot the rest of the engine
does not read.

## Live reproduction

Driven in the browser against Eldenford Blacksmith (Harren Cobb), 2026-10-01.
This is the whole failure, in six ticks:

    [Tick 2] World Refreshed "Eldenford Blacksmith" from library: memories,
             relationships, conditions, personality, description,
             base_description, stats, skills, traits, tags, interest_tags,
             current_area, emotion
    [Tick 3] World Auto-dress for Eldenford Blacksmith: 0 item(s) equipped.
    [Tick 4] LLM -> inspector/generate-interest-tags ~0.6k tok
    [Tick 5] inspector/generate-interest-tags ~35 tok
    [Tick 6] World Auto-dress for Eldenford Blacksmith: 2 item(s) equipped.
             - Guiding Cane
             - apron

Tick 3 is the empty intersection predicted above: the hand-authored tags
(`metal, tools, goblin_raids, iron, repair, temper, the_merchant, the_road`) match
no wearable, so nothing is dressed. Ticks 4-5 are `✨ Generate from Personality`
(`static/js/inspector/agent-view.js:875`, impl `:1950`), whose picks are **added**
to the hand-placed tags. Tick 6 re-runs the deterministic matcher over the widened
set and equips `guiding_cane` -- tags `sensory_aid, tool, wooden`
(`data/library/items/guiding_cane.json:10-14`), whose own description says *"a
blind traveller's best friend for finding their way"*.

So: an LLM picked a plausible smith-adjacent tag, the deterministic matcher
converted it into a white cane on a 41-year-old blacksmith, and the report
presented it as a success. The `apron` in the same run is the only defensible
pick, so 1 of 2 was right.

Two further facts this run established, both worth keeping:

1. **`equip_slots` governs equipping; the `actions` list does not gate it.**
   `guiding_cane` declares `"actions": "examine,take,drop,use"` -- no `equip` --
   yet `equipment.equip_item` accepted it and it landed in `hand_right`. So
   "not equippable" cannot be expressed by omitting `equip` from `actions`. Same
   defect class as task-292 (apron declares `equip_slots`, no `equip` action).

2. **Tick 2 confirms the refresh/import split from the browser.** The applied
   section list contains `tags` and `interest_tags` but **not** `equipped`, so a
   library refresh does not write equipment to a live player -- while
   `handle_library_import_character` (`routes/library_ops.py:489-491`) does read
   it. Same field, two code paths, opposite results.

Note also that auto-dress will not clean up after itself: it is idempotent by
construction and never replaces worn gear (`engine/dressing.py:10-12`), so the
cane stays until it is removed by hand.

## Implementation (2026-10-01) — IN PROGRESS, not verified

Implemented, gated, and **not** live-verified. Kept in `inprogress/` because
nothing has been seen working in a browser yet, which is the whole acceptance
bar for this one.

**Constraint that shaped it:** the engine cannot call a model — keys live in
the browser (`routes/action_handlers.py:195`). So the LLM pass lives in the
inspector and the engine keeps the two halves it actually owns: the candidate
list and the equip step. The established `llm_respond` convention (browser
generates, backend applies) rather than a new mechanism.

- `engine/dressing.py` — `_wearable_entries()` (all wearables, weather-gated),
  `_tag_matched()` (the original selector, unchanged), `dress_candidates()`
  (returns `matched` + a wider ranked `pool` + character context), and
  `auto_dress(..., library_ids=None)` which equips an explicit list or falls
  back to the shuffle. `None` vs `[]` is meaningful: `[]` is a real "wears
  nothing" answer and must not trigger the fallback.
- `virtual_world_engine.py` — `auto_dress_character(name, library_ids=None)`,
  `auto_dress_candidates(name, limit)`.
- `routes/action.py` — `POST /api/auto_dress` accepts `library_ids` and echoes
  `selection: 'llm' | 'tags'`; new `POST /api/auto_dress/candidates`.
- `static/js/inspector/agent-view.js` — `_autoDress` rewritten to ask for the
  pool, call the model, validate, and post back. Two pure helpers,
  `_validateAutoDressPicks` and `_parseAutoDressResponse`, are the browser-side
  trust boundary; the engine re-validates anyway.
- `static/js/ui/help-center.js`, button tooltip — now describe what it does.

**Pool is wider than the tag filter on purpose.** The model has to be able to
pick an apron that no tag matched, otherwise the same failure returns. Verified
`matched ⊆ pool` and `len(pool) > len(matched)`.

**Incidental fix:** the except branch in the equip loop referenced `node` before
it was bound whenever `_hydrate_item` raised, so the failure was swallowed by
the inner `except` and the candidate vanished with no recorded reason. `node`
is now bound to `None` first and the cleanup is guarded.

### Evidence

- `python -m pytest tests/test_auto_dress.py -q` → **10 passed** (4 original
  task-325 tests unchanged, 6 new).
- `node tools/unit/run.cjs` → **473 passed, 0 failed**, 12 of them in the new
  `tools/unit/test_auto_dress_selection.js`.
- `npm run lint`, `npm run typecheck`, `python tools/js_module_index.py --check`
  → clean.
- `POST /api/auto_dress/candidates` against the running server → **404**,
  because that server is still on the pre-change code. This is *not* evidence
  the route is wrong; it is evidence the backend half has not been exercised
  live either.

### What still blocks `review`

- [x] **The LLM selection itself has run.** Model called, ids returned, all
      validated, five items equipped, `selection: 'llm'` logged. Mechanism done.
- [ ] **Re-run the quality check on a character whose personality is correct.**
      The one run so far was dressed as the merchant (see above), so it proves
      nothing yet about whether the prompt produces sensible gear. Needs the
      cast rename resolved first.
- [ ] Confirm the `selection: 'llm'` line reaches the event log so it is visible
      that the model ran rather than the fallback — **done, confirmed in the
      browser log above**.
- [x] **Decided 2026-10-08 (user): yes — filter the pool on
      `world.mature_content`.** A general inspector button should not offer
      mature-tagged wearables (`ball_gag` is `clothing, accessory, restraint,
      wearable`) when mature content is off, even though the no-interests branch
      already reached them before. The wider pool does not introduce the class,
      but it puts it in front of the model; filter it at the candidate source.
      **Implemented:** `_wearable_entries` now carries the item's `mature` flag
      (the same field `routes/library_ops._filter_mature_entries` honours), and
      `engine/dressing._apply_mature_gate` drops mature wearables from both
      `dress_candidates` and `auto_dress` when the toggle is off. Test:
      `tests/test_auto_dress.py::test_mature_wearables_are_gated_by_mature_content`.

### Live verification (server restarted, 2026-10-01)

**`POST /api/auto_dress/candidates` → 200.** Eldenford Blacksmith, 27.6 °C:

    matched: 3   pool: 30
    interest_tags: bread, credit, goblins, information, instrument, meat,
                   metalwork, mining, orcs, price, silver, the_roads, tool, trade
      1. apron             | torso       | blood,clothing,meat
      2. gribbas_good_knife | hand_right | knife,personal,tool,weapon
      3. guiding_cane       | hand_right | sensory_aid,tool,wooden

This is the whole bug in three lines of data. The `matched` set is what the
deterministic path would have equipped, and it reached each item through tag
overlap that has nothing to do with dressing a person: the **apron** via `meat`
(it is rawhide), and the **Guiding Cane** via `tool` (as does a hammer). The
`tool` tag is why a walking stick and a smith's hammer are
indistinguishable to the filter. `pool` is 10x wider, which is the point — the
model can now reach a work shirt, trousers and boots that no tag ever matched.

**`POST /api/auto_dress` with explicit `library_ids` → 200, `selection: 'llm'`.**
The equip half of the new contract works against the real world: posted ids
become real equipped items with real `equipped` edges.

**First LLM run in a browser — the whole path works end to end.** Clicked the
button on Eldenford Blacksmith, fully undressed first:

    [Tick 16] LLM -> inspector/auto-dress ~1.2k tok
    [Tick 19] inspector/auto-dress ~23 tok
              {"items": ["apron", "gribbas_good_knife", "belt_leather",
                          "dark_cargo_pants", "coif_linen"]}
    World Auto-dress for Eldenford Blacksmith: 5 item(s) equipped.
    World Auto-dress selection (llm): apron, gribbas_good_knife, belt_leather,
                                     dark_cargo_pants, coif_linen

All five ids were real candidates, so validation passed, and the Guiding Cane
is gone. **But the run is confounded and must not be cited as evidence that the
picks are good** — see below.

### CONFOUNDED: the model was dressed as the wrong person

The prompt at Tick 16 reads:

    CHARACTER: Eldenford Blacksmith
    PERSONALITY
    You are the Eldenford merchant. You are talkative, curious, and permanently
    halfway through calculating something.
    APPEARANCE
    Human merchant. Clean clothes, many pockets, a smile that never quite reaches the eyes.

**The blacksmith node was carrying the merchant's personality and appearance.**
The earlier `✨ Generate from Personality` call (Tick 4) had the same wrong
input, so this was not a one-off.

Measured, not guessed:

- Live state *now* is correct — all five Eldenford characters have their own
  personalities and descriptions.
- So the wrong personality was transient: present through Tick 19, gone after
  the later profile switches / engine re-initialisation.
- No Eldenford node carries `library_id` or `template_ref`, so the node resolves
  its template **by name alone**, and `Eldenford Blacksmith` is no longer a
  library key: the entry is now `Harren Cobb`.
- The step immediately before was `Refreshed "Eldenford Blacksmith" from
  library`, which logged a successful apply of `personality, description`.

**This is the predicted consequence of the library-only rename**, recorded on
task-665: *"The rename cannot be completed in the library alone."* Renaming the
library file removes the key the live node resolves by, and the refresh landed
on the wrong entry. The exact fallback path inside
`resolve_template_id` (`engine/sync.py:170`, `guess="node_name"`) and
`template-sync.js:181` is **not** established here -- what is established is
that the node had no binding, the key it resolves by is gone, and the refresh
that followed produced another character's personality.

Because of that, the LLM's picks read as a *reasonable merchant's outfit* --
knife, belt, dark cargo pants, apron -- and `coif_linen` is a debatable call.
None of that is evidence for or against the prompt quality. **Re-run this after
the cast rename is resolved, and on a character whose personality is correct,
before judging the selection.**

### Bug found live and fixed during verification

Posting `['heavy_black_boots','belt_leather','quantum_harness','heavy_black_boots']`
equipped **the boots twice**:

    Auto-dress for Eldenford Blacksmith: 3 item(s) equipped.
    - heavy black boots
    - belt_leather
    - heavy black boots
    ...
    feet: heavy_black_boots, heavy_black_boots_061fbea7

`_hydrate_item(always_fresh=True)` mints a NEW node per call, so a repeated id
produced two instances of one item in one slot — violating the module's own
"one instance per name" rule. The invalid id was correctly dropped, so only the
duplication was wrong.

The browser validator already de-duplicates, so the *usual* path was safe. But
`auto_dress` is documented as the engine's re-validation boundary and has other
callers; a boundary that trusts its caller is not a boundary. Fixed in
`engine/dressing.py` and covered by
`test_repeated_ids_produce_one_instance_per_name`, which was confirmed to fail
against the unfixed code with the same `heavy_black_boots_<hex>` shape seen live.

### Also demonstrated live: task-654

Deleting the duplicate node (`DELETE /api/graph/node/heavy_black_boots_061fbea7`
→ 200) left `player.equipped['feet']` still holding the now-dangling id, with no
reconciliation in either direction. Recorded on task-654.



- [ ] An LLM pass selects the gear. Given a character's name, personality,
      `interest_tags` and a candidate list (name, tags, equip slots, insulation),
      it returns the pieces to equip; the deterministic tag intersection remains
      the fallback when no LLM is configured, so existing tests in
      `tests/test_auto_dress.py` stay meaningful.
- [ ] The candidate list sent to the LLM is bounded (top-N by tag match), and the
      response is validated against real library ids -- an unknown or malformed id
      is dropped, not equipped.
- [ ] `🤖 Auto-Dress from Interests` still never replaces worn gear and still
      respects slot stacking and the hot/cold insulation rules
      (`engine/dressing.py:84-88`).
- [ ] Re-running is still idempotent (`tests/test_auto_dress.py::test_auto_dress_is_idempotent`).
- [ ] **Verified in a live browser**, not from the code path: the button is
      clicked, the report names the items chosen, and the equipped slots and
      carrying edges are read back. A unit test alone does not close this.
- [ ] The help text (`static/js/ui/help-center.js:174`) matches what the feature
      actually does, whichever direction this goes.
- [ ] One authored end-to-end case: a character whose gear should be
      distinguishable from another character's with overlapping tags, showing the
      LLM pass picks differently.

## Proposed-outfit confirmation modal (2026-10-01)

Added because the first live run proved the real problem was not selection
quality, it was **visibility**: the model was handed the merchant's personality
and dressed the blacksmith as a trader, and every layer reported success.

`static/js/inspector/auto-dress-modal.js` puts the two things a person needs
side by side before anything is worn:

- **The context the model read** — name, personality, `base_description`. If that
  text belongs to someone else, it is now visible at the moment it matters rather
  than three layers downstream.
- **The proposal as per-slot checkboxes**, so one absurd pick is unticked rather
  than accepted wholesale or discarded entirely. Cancel equips nothing and says
  so in the event log.

`DiffModal` was considered and rejected: it is a two-payload world↔library merge
returning update/duplicate/cancel, and auto-dress has one proposal and no
"before" worth diffing. Its return vocabulary does not fit an equip.

Items are grouped under the **first** declared slot, because that is what
`auto_dress` passes to `equip_item` (`engine/dressing.py`). Filing them anywhere
else would put the paperdoll and the real loadout at odds -- the exact defect
task-654 records in a different guise.

**`description` is deliberately excluded from the prompt.** It is regenerated
*from* the equipped items on every wear/remove
(`engine/equipment.py::_update_equipment_description`, plus the frontend call at
`static/js/api.js:652`), so feeding it to a prompt that chooses equipment is
circular -- the model reads an outfit to pick an outfit. The evidence is in the
live log above: every garment removal produced a fresh
`inspector/generate-appearance` call and an "Appearance saved". The candidates
field is therefore named `base_description`, not `description`, so the reason
survives the next reader, and a test asserts the circular field is not offered
alongside it.

Unticking **everything** resolves to `[]`, which is a real answer ("wears
nothing") and does not trigger the deterministic fallback. The distinction from
"the model failed" is asserted in the JS tests.

### Evidence

- `tools/unit/test_auto_dress_modal.js` — 12 tests (grouping order, first-slot
  rule, junk input, untick semantics).
- `python -m pytest tests/test_auto_dress.py -q` → 12 passed.
- `npm run lint`, `npm run typecheck`, `js_module_index --check`,
  `feature_index --check` → clean.

### Still needs

- [ ] **Server restart** to pick up the `base_description` rename. The running
      server predates it and still returns `description`, so the modal's
      appearance panel renders empty until then. The restart also loads the new
      script tag.
- [ ] **Live check of the modal itself** — open it, confirm the personality
      panel shows the *right* character, untick one item, equip, and read the
      equipped slots back. This is the verification that would have caught the
      merchant mix-up, and it has not been run.
