# Persona + Body Systems — Design Document

Compiled 2026-10-16 from the VirtualWorld repo (cards in `docs/virtualWorld/dev_tasks/`,
code, and live verification on :4444). Status per item: **shipped** (in review),
**open** (todo/inprogress).

---

## 1. Persona schema (task-828, shipped)

One structured block per character node (`properties["appearance"]`), four sections.
Prose-only (no block) stays the default — a character without a block is normal, not broken.

- **identity**: pronouns, age, gender, species, occupation, sexuality
- **appearance**: overview, height_cm, weight_kg, build, hair{color,length,style,accessories},
  eyes{color,shape,special}, skin{tone,condition,distinguishing_features},
  face{shape,features,makeup}, body{chest,waist,hips,legs,butt,modifications[]},
  voice{pitch,accent,mannerisms}, scent, style{clothing,accessories,footwear}
- **personality**: likes, dislikes, fears, interests, kinks, turn_ons, turn_offs,
  traumas, boundaries, traits, aspirations, quirks, habits, speech_pattern{}, experience
- **narrative**: biography{}, secrets{}, example_dialogues[], role_in_town, arc

Rules: the block is **state**; description/tags/voice are **projections** refreshed by one
explicit Compile (`POST /record/compile`, preview-before-clobber). Secrets never compile.
What "record is the sole source of truth" means in practice: if the block and the prose
disagree, the block wins — Compile overwrites prose, never the reverse, and no second
store (a sidecar file, a parallel blob) may claim to describe the same character.
`mbti`/`alignment`/`media` were initially left out as readerless; per review they return
only with named consumers (task-850). Every field carries a consumer hint served by
`GET /record`.

## 2. Growth wiring (task-829, shipped)

Every persona field is mutable at runtime via `set_persona_field` / `add_persona_id` /
`remove_persona_id` / `advance_age` — ordinary trigger effects (lens item, tattoo kit,
passing year). Tag mirrors update additively. Lifecycle `advance_age` shifts birth tick
(task-735 hook).

## 3. Persona tab UI (task-830 + sheet pass task-844, shipped; import task-843, shipped)

Mind dashboard → Persona tab. **Two-column grid** (`1fr 1fr`), wide groups span both.
Identity + Appearance folds open; Personality, Narrative one click away. Badge header
(pronouns · age · species · occupation). Tag fields are chips (fears red, interests teal).
Intimacy fields fold separately (dashed); secrets blurred until clicked. Sticky bar:
import (card .json / prose .md/.txt → sheet via LLM, deterministic pre-parse + dry-run
preview), save block, compile. Dirty dot, stale banner ("block changed since the last
compile"), Codex live-preview fold (dry-run, stores/broadcasts nothing).

## 4. Body systems (pre-existing, audited — all wired)

- **Body parts** (`engine/body_parts.py`): one flat region catalog — `injury` / `erogenous` /
  `both` zones, damage thresholds (injury ≥ 5, bleed ≥ 10 slashing/piercing), per-region
  `base_sensitivity`. Bodies are NOT nodes: `Player.body_state` (flat
  `{region: {sensitivity}}`), injury lives as `body_part`-tagged conditions.
- **Paperdoll** (`paperdoll-view.ts`, 44KB): equipment slot figure (BACK/HEAD/NECK/ARMS/
  TORSO/HANDS/WAIST/LEGS/FEET + held), coverage/exposure readout, equip/unequip/layers,
  🩺 per-slot body-region modal (sensitivity / injury / bleeding / covered per region).
- **Sensitivity** (`pleasure_actions.py` + `affect_for_stimulus` + `stimulation_from_path`
  read live in `tick_manager`): kinks → arousal, turn-offs → disgust, stimulus-gated.
  105 tests green across body/pleasure/equipment. Sensitivity itself is a responsiveness
  dial, 0..1 per region: how much a touch *lands* there (verb base × intensity ×
  sensitivity). Not pain (injury levels), not exposure (clothing), not willingness
  (kinks/boundaries) — the raw gain knob between contact and felt response.
- **Injury** (distributed, no dedicated module — correct): combat applies region-scoped
  `injured`/`bleeding` conditions at thresholds (`combat.py:630`) + per-region wound
  sentences; exposure gates it. Conditions live in `data/library/conditions/`.
  CORRECTION (review): starting injuries ARE authorable — a broken leg, a hook hand are
  legitimate authoring, and withholding that was not an engineering call to make.
  Design: seed the *same* condition instances combat makes (no parallel store); a hook
  is `modifications[]` (exists); a missing limb needs representation (task-851).

## 5. Body navigator (task-847, shipped) → doll modes + baseline (task-848, shipped*)

- 847: region chips atop Appearance reading the paperdoll's own `AREA_TO_REGIONS`,
  side panel with live status + linked schema summary + markings, ⤴ jumps to the real
  input. No duplicate editors.
- 848: **one doll, two modes** — `renderPaperdollFigureHtml({mode:'equip'|'navigate'})`.
  Inventory equips through it unchanged; Persona reads through it (slots dispatch
  `onNavigate`, never equip; hurt glows red, sens ≥ .75 runs warm, selection rings blue).
  Side panel adds **per-region sensitivity sliders** → new `PUT /api/players/<name>/body`
  (`handle_set_body_baseline`): catalog-validated, 0..1, 400s otherwise; same value
  pleasure reads; persisted via existing ON_PLAYER serialization. **Injury unwritable in
  this pass only — starting wounds seed the same instances (task-851); the earlier
  "never editable" line was overreach, corrected in §4.
- *848 asterisk: slider live-write needs a server restart (new route; backend proven,
  4/4 `test_body_baseline.py` green). Filled-slot equip path not exercisable live
  (nobody geared; branch is verbatim moved code).

## 6. Lifecycle link (task-735 shipped; pregnancy split to task-846, open)

`engine/lifecycle.py`: age from birth_tick, life stages, mortality; `set_game_date` runs
`on_clock` (date jumps are time travel); DELETE /record clears derived clock state
(prose-only is fully prose-only again). 846 (pregnancy/birth mechanics) is filed, unstarted.

## 7. Decisions (load-bearing, do not re-litigate casually)

1. Record is the sole source of truth for description; Player owns runtime state.
2. No second doll, no duplicate editors — one template, two modes; one map, two readers.
3. Sensitivity = authorable **state** (Player), not prose — numbers don't compile.
4. Injury is sim state, but starting injuries are legitimate authoring (task-851):
   seed the same instances, never a parallel store. The "never editable" call was
   overreach — corrected on review.
5. `exists ≠ wired`: schema entries without consumers don't ship; every field names a reader.

## 8. Where it lives

| Piece | Files |
|---|---|
| Schema/compile/mutators | `engine/character_appearance.py`, `engine/effect_handlers/persona.py`, `engine/pronouns.py` |
| Record/body routes | `routes/player_ops.py`, `routes/players.py` |
| Persona tab / doll / navigator | `static/js/inspector/mind-view.ts`, `static/js/inspector/paperdoll-view.ts`, `static/css/style.css` |
| Simulation | `engine/body_parts.py`, `engine/pleasure_actions.py`, `engine/combat.py`, `engine/lifecycle.py`, `engine/equipment.py` |
| Tests | `tests/test_character_appearance.py`, `tests/test_persona_growth.py`, `tests/test_body_parts.py`, `tests/test_pleasure_system.py`, `tests/test_body_baseline.py`, `tests/test_lifecycle.py` |
| Docs/cards | `docs/virtualWorld/Characters/Persona.md`, tasks 735, 828, 829, 830, 843, 844, 846, 847, 848, 849, 850, 851, 852 |

## 9. Planned / open

- **task-849**: narrative authoring feeds memories + goals (biography/arc/role seed or
  link runtime entries; one store per fact — unstarted).
- **task-850**: identity additions — mbti (reader: prompt voice), alignment (reader:
  disposition weights or prompts, to be named before shipping), birthday (calendar
  semantics; drives display vs age resolution, to be decided — unstarted).
- **task-846**: pregnancy & birth mechanics (split from 735; unstarted).
- **task-852** (PERSONA UI PLAN, the big one — parked at inprogress): P1 workspace +
  header started (full-width pane, header, badges, state chips live on :4444;
  dirty/stale toggling + polish NOT done). P2-P5 unstarted (doll nav front/back,
  region-linked markings, body-state integration, personality/narrative polish).
  Blueprint doc lives in the task card. Do not mix 846/850 into this card.
- **851 remainder**: missing-limb travel/movement integration (filed on card).
- **848 remainder**: live slider write after restart; filled-slot equip path re-verify when someone is geared.
- **Deliberately unbuilt**: inline schema-text editing in the side panel (would duplicate
  editors; jumps suffice pending a sync design).

## 10. Session state — where the work is parked (2026-10-16)

In **review** (all verified + gates green where applicable):
735, 546, 828, 829, 830, 843, 844, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840,
841, 842, 847, 848, 851.

**Inprogress / partially wired:**
- **852** (workspace redesign — P1 partial, see §9)
- **bug-545** (paint perf cache — box deliberately open)
- **755** (narrow-panel autogrow screenshot open)

**Needs a server restart to feel live** (backend-only; nothing restarts under an
unsaved world): `PUT /body` (sensitivity + seeded injuries + missing), `set_game_date`
lifecycle hook, DELETE-clears-clock, autosave-skip, save-validation.

**Authorable body state now covers:** sensitivity per region (0..1, validated),
seeded injuries (`injuries[]`, same instances combat makes), missing anatomy
(`missing[]` → `missing` condition, ✖ in UI).

**Testing status:** 237 green across crafting/lifecycle/persona/activity/background
(+113 body/pleasure/equipment, +8 baseline, +105 body-parts suite). ts gate green
(175 files). recipe gate 105 clean. Known pre-existing (not ours): jessica.json
`cha` spelling in test_abilities, 15 scenario-tag baseline drifts, broken
`[[Developer Tooling]]` in task-819.
