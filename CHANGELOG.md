# Changelog

All notable changes to VirtualWorld. See `docs/virtualWorld/Scenario Workflows & UI Audit.md` for the long-term plan this release follows.

---

## 1.5.0 — "Tender Magic & Graph Forge" (2026-09-02)

A sweeping working-tree day: environment/time/weather engine plumbing, trigger-graph viewport and compile-honesty overhaul, broadened NPC behavior vocabulary, character/schema cleanup, and a 15-spell Lyrie spellbook design task. **Suite at 2507 passing**; no regressions in the core scenario/turn flow.

### 🌦 Environment & Time (engine)

- **Area status engine** (`engine/area_statuses.py`): data-driven area status definitions, persistence, and save/load round-trip.
- **Environment propagation** (`engine/environment_propagation.py`): temperature/light decay and adjacency propagation wired into the tick loop.
- **Effect handlers** (`engine/effect_handlers/environment.py`): `set_environment`, `adjust_environment`, `set_weather`, `set_time`, `set_date`, `forecast_override`, `adjust_forecast`, `apply_area_status`, `clear_area_status`, `set_wet` implemented as item/trigger effects.
- **Tick integration** (`engine/tick_manager.py`): area status + environment updates execute each tick.
- **Trigger validator** (`engine/trigger_validator.py`): new catalog entries for the expanded environment/time effect set.

### 🧠 NPC Behaviors

- **`engine/triggers/behaviors.py`** (+899 lines): new action types `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `hide_behind`, `hide_under`. NPCs can now leave memories, change mood, set runtime flags, and take cover.

### 🎨 Trigger Graph Editor

- **Viewport**: pan, zoom-to-cursor, Fit, dot-grid background, per-graph viewport persistence.
- **Wires**: left-in/right-out socket layout, YES/NO branch coloring, arrowheads, wire selection + delete, cycle/duplicate guards.
- **Compile honesty**: badges/warnings for fan-out drop, behavior NO-branch drop, and Y-position priority override.
- **Catalog parity**: trigger node now supports multi-select trigger types from the shared registry; condition node grouped dropdown covers all 27 conditions; effect node covers the full 42-effect catalog plus save-gate branches, `llm_respond`, `scry`, memory effects, and environment presets.
- **Interaction fixes**: field commits on `input`, selection class-toggle instead of rebuild, Escape/close guard, draft autosave.
- **Tests**: `tools/test_trigger_graph_viewport.cjs` (19/19), `tools/test_behavior_action_cards.cjs` (119 action types).

### 🧍 Characters

- **Lyrie** (`data/library/characters/Lyrie.json`): equipment slots normalized from string refs to full item objects; memory schema unified (`salience_override`, tick normalization, text formatting cleanup); vitals corrected (`Hunger 94→6`, `Thirst 94→6`); stray markdown artifact removed from `personality`.
- **Whiskers** (`data/library/characters/whiskers.json`): character data update.

### 🗺 Scenario & World Template

- **`data/scenarios/mansion.json`**: migrated to the current scenario schema (`players` map, `current_area`, `area_presence`, equipment objects).
- **`world_template.json`**: refreshed to match the new schema.
- **`virtual_world_engine.py`**: small schema/plumbing updates to keep live state aligned with the migrated format.

### 📚 Library Items & Triggers

- **New templates**: `template_adjust_forecast`, `template_apply_area_status`, `template_clear_area_status`, `template_forecast_override`, `template_set_date`, `template_set_time`, `template_set_weather`, `template_set_wet`.
- **New scratch trigger**: `data/library/triggers/untitled.json`.
- **New reference**: `docs/Trigger-Condition-Effect-Cheat-Sheet.md`.

### 🛠 Fixes

- **Behavior form editor crash**: `weighItem`/`inventoryItem` undeclared consts fixed; all 119 behavior action cards now build without throwing.
- **Graph field persistence**: inline handlers now reference `TriggerGraph` correctly; id substitution no longer mangles quoted ids.
- **Behavior graph layout**: re-layout from single tall column to priority-ordered row-major grid; fit zoom improved on dense behavior sets.
- **Wire rendering after reopen**: wires now redraw after viewport settle, preventing offset/scattered wires on open.

### 🧰 Gotchas in this release

- **Restart your server** — engine, routes, and frontend all changed.
- The mansion scenario file is large and structurally different from older scenarios; inspect via the Scenario Manager before mixing with older templates.
- `llm_respond` remains blocked in trigger contexts without a host-side LLM provider decision.
- Some new effect types (`polymorph_target`, `create_illusory_companion`, `broadcast_emotion`, `repair_item`, `ward_area`, etc.) are proposed in `task-391` but not yet implemented in the engine.

### 🧪 Behind the scenes

- New modules: `engine/area_statuses.py`, `engine/environment_propagation.py`, `engine/effect_handlers/environment.py`, `static/js/shared/env-presets.js`.
- New tests: `tests/test_area_statuses.py`, `tools/test_trigger_graph_viewport.cjs`, `tools/test_behavior_action_cards.cjs`, `tools/_probe_parity.cjs`.
- New tasks: `task-388` (trigger-graph overhaul), `task-389`/`task-390` (NPC behavior phases), `task-391` (Lyrie spell items + engine effect proposals).
- Task vault reorganized: 10 environment tasks moved to `done/environment/` or `cancelled/`; sequence doc bumped to 392.
- Full suite at **2507 passing**.

---

## 1.4.0 — "Body Language" (2026-09-01)

The mature-content pleasure system (vitals, intimacy verbs, arousal conditions, release loop,
mature traits), a company-aware Social overhaul, vitals-driven emotions, involuntary actions,
invisible undead-ghost NPCs, and the identity foundation for id-backed characters. Everything
adult is opt-in behind a single 🔞 toggle and leaves the base game untouched. **2589 passing**
(69 MCP tests deselected — pre-existing harness breakage, see Gotchas).

### 🔞 Mature content toggle (task-206)

- **World flag** `mature_content` mirroring ghost_mode end-to-end: `GET/POST /api/settings/mature_content`,
  world attribute, save/load round-trip, settings-modal toggle (🔞 Content group), IndexedDB persistence.
- Everything below is gated on it: toggle off → no pleasure vitals exist, intimacy verbs reject with a
  flavor message, adult traits vanish from library pickers, arousal conditions strip themselves.

### 💗 Pleasure vitals & release loop (tasks 207/208)

- **Three new vitals** — Arousal (slow ebb), Stimulation (medium drain), Pleasure (fast fade) — appear
  only in mature worlds, self-healing via `Player.sync_pleasure_vitals()`, with baseline decay rates.
- **Clothing friction** (task-208): equipped items' `friction` property trickles Arousal (0–3/tick).
- **Edging**: Stimulation 50–64 stacks the `sensitized` condition and feeds Arousal.
- **Release**: Stimulation ≥ 65 ∧ Arousal ≥ 40 fires the cascade — Energy −20, Entertainment +30,
  Hygiene −10, Sanity +15, meters reset, `satisfied` + `overstimulated` applied, log line for the
  active player.

### 💘 Intimacy verbs (tasks 211/212)

- **New module** `engine/pleasure_actions.py`: 8 verbs (kiss, caress, lick, suck, bite, pinch, blow,
  tickle) with a `VERB_BASE` pressure/pleasure/pain table.
- **Body-part targeting**: `kiss lydia on neck`, `pinch her on the left nipple` — same region resolver
  as task-253 combat. Omitted `where` defaults per verb (kiss → lips). Covered regions land
  *through clothing* (damped ×0.4).
- **Multiplier pipeline** (task-212): intensity (light/normal/firm — leading "firmly kiss…" and
  trailing "…gently" both parse) × region sensitivity (paperdoll `body_state`) × trait
  `body_part_multipliers` (e.g. `wired_differently`: nipples ×3.0, genitals ×0.1) × closeness bonus.
- **Pain flips**: `pain_potential` verbs (bite, pinch) can drive Pleasure negative → `overstimulated`.
- **Interact-type**: never damages, recorded as `interact` turn events, no weapon/roll path — a clean
  `interact` vs `attack` split in the dispatch.
- **Frontend** (`action-normalizer.js`): mature worlds accept/emits
  `{action:"kiss", target, where, intensity}`; the system prompt gains an intimacy schema section.
  Non-mature worlds never accept or advertise the verbs.

### 🧬 Arousal conditions & mature traits (tasks 209/213)

- **13 new conditions**: `warming_up` / `aroused` / `highly_aroused` / `frantic` (threshold-driven
  from the Arousal vital, applied/removed automatically each tick), `overstimulated`, `nipple_hard`,
  `blushing`, `wetness`, `sensitized` (edging stacks), `satisfied` (afterglow), plus base-game
  `itch`, `goosebumps`, and `social_breakdown`.
- **Guard**: condition periodic effects can no longer CREATE vitals — an arousal condition on a
  non-mature world can't leak an Arousal key into `player.vitals`.
- **7 mature traits** (`wired_differently`, `quick_recovery`, `sensory_memory`, `sex_addict`,
  `attention_seeker`, `exhibitionist`, `single_track`) — marked `mature: True` and hidden from
  library listings unless the toggle is on. Wired hooks: `quick_recovery` halves the
  overstimulated bout, `sensory_memory` leaves lingering sensitivity after release, `sex_addict`
  doubles Entertainment decay at low Arousal.

### 🪞 Body-state descriptions (task-210)

- **Equipment description enrichment**: the appearance prompt now carries per-item detail properties
  (opacity / coverage / current_state / friction) plus a visible-physical-state section (flush, hard
  nipples, trembling, desperation…) — woven into the prose in both the LLM and fallback paths.
- **Agent prompts** gain first-person body-state lines derived from the arousal conditions.

### 👻 Undead ghost NPCs (task-309 MVP)

- Tag a character `ghost`/`undead`: invisible to room listings and social presence, skips ALL vital
  processing (no hunger/cold/fatigue), untargetable ("the blow passes straight through"), and
  **phases through locked/blocked/one-way/item-gated ways** — perfect for atmospheric stalkers.

### 🗼 Emotion from vitals (task-142)

- `engine/emotion.derive_from_vitals()`: when no explicit emotion has been set (or the affect map
  decayed back to neutral), mood is derived from actual physical state — starving → craving/anxious,
  frozen → uneasy, exhausted → irritated/melancholic, injured → afraid, dying → deep calm (ghosts),
  asleep → silent. Explicit emotions always win; vitals only fill the silence.

### 👥 Company-aware Social overhaul (task-353)

- **Isolation timer**: after 5 consecutive alone-ticks, Social decay accelerates (extra −1/tick);
  introverts exempt, **loners reverse it** (+1/tick in solitude).
- **Physical ≠ social** (task-353 §2): humid air and `humidity: humid` now sap **Hygiene** (not
  Social); perfume boosts **Entertainment** (not Social). A lone character in a perfumed room is
  still alone.
- **GROUP_ENERGY_DRAIN** is now consumed: crowds of 3+ sap Energy per the trait value.
- **Self-talk**: speaking with no living listeners in the room gives +1 Social instead of +5.
- **chatty trait**: +2 per exchange (speaker +7, chatty listeners +5).
- **Behavioral gates** (§5): prompt flags (`social_need: moderate/desperate`) at Social < 50/25 and a
  `social_breakdown` condition below 10 (Sanity drain, removed once Social recovers ≥ 15).
- New traits: `loner`, `chatty` (conflict-correct, library-seeded).
- **Fixed 5 pre-existing `test_social_company.py` failures** (the humid-area Social double-drain).

### 💬 Involuntary actions (task-166)

- **`static/js/agent/involuntary.js`**: condition-driven speech/emote interruptions — frightened →
  stutter ("W-what did you say?"), freezing → chattering stutter, sick/poisoned → coughs,
  social_breakdown → hollow muttering, itch/goosebumps → scratch/shiver emotes, plus a low random
  baseline (hiccup/burp/yelp). Pronoun-aware, never blocks the intended action, injected before the
  text is sent so the room and event stream both see it.

### 🛠 Fixes

- **Mana vital leak** — non-magic characters showed a Mana bar because saves/scenarios hardcode
  `"Mana": 0` and every hydration path overwrote vitals after the tag sync. All five hydration
  paths (save load, library spawn, template load, library import, player import + graph copy) now
  re-run `sync_vitals_with_tags()`.
- **Latent `AttributeError`** in the NPC hunter facade (`_get_nearest_player_to` /
  `_get_path_to_area` called non-existent undecorated names on `npc_behaviors`).
- **TickManager ghost check** — `TickManager.player_manager` is actually the engine; the undead-ghost
  decay skip went through a facade that resolved to `None` (found by the new tests).
- **Release cascade** — `satisfied`/`overstimulated` no longer exclude each other (refractory
  overload + afterglow coexist).

### 🧪 Behind the scenes

- New test file: `tests/test_pleasure_system.py` (21 tests) covering the toggle gating, multiplier
  pipeline, dispatch (incl. the leading-adverb form), friction/edging/release, quick_recovery,
  ghost NPC behavior, phasing through locked ways, and id round-trips.
- **task-316 foundation** (safe subset): stable opaque `Player.id` (uuid8, serialized/restored) and
  `graph.add_node` no longer silently overwrites duplicate **character** nodes. The full
  registry/relationship re-key remains a dedicated follow-up.
- Task vault: 142/166/206/207/208/209/210/211/212/213-lite/309-MVP/316-foundation/353 — implemented
  in this session.
- Full suite at **2589 passing** (+21 new; 69 MCP tests deselected).

### 🧰 Gotchas in this release

- **Restart your server** — the engine, routes, and frontend all changed.
- **Mature content is opt-in and off by default.** Toggle it in settings (🔞 Content group) or
  `POST /api/settings/mature_content`. Toggling mid-session strips/creates the three vitals and
  their conditions automatically — nothing leaks into clean scenarios.
- **Item `friction` / `opacity` / `coverage` properties** drive the new description + arousal
  behavior but no library items have them yet — set them in the inspector/library and they work.
- **Ghost NPCs** need the `ghost` or `undead` **tag** on the character. They're fully invisible:
  no room listing, no social presence, no tick processing. Include them in queries with
  `include_ghosts=True`.
- **MCP test modules** (`tests/test_mcp_*.py`) are broken by a pre-existing harness issue
  (`'function' object has no attribute 'fn'`) that predates this release — 69 tests deselected
  until that harness is fixed.
- The 4 remaining mature traits (attention_seeker, exhibitionist, single_track, sex_addict's
  perception side) are defined but await the NPC-perception framework (task-214) for their hooks.

---

## 1.3.0 — "Weather Eye & Wild Words" (2026-08-31)

A forecast schedule engine, game calendar, moon phases, wind/humidity, a triple-feature NL Editor
power-up (ghost previews, populate_area, selective apply, mechanic inference, lore-aware prompts,
palette shortcut), a sky widget driven by live state, trigger effects for time/weather, and
moonlight descriptions. **2633 passing**.

### 🌦 Weather & Sky (engine)

- **Forecast engine** (`engine/weather_forecast.py`): authored (hourly/weekly/yearly), deterministic
  state-machine, random, or hybrid modes. Zero authored entries = strict no-op — existing scenarios
  are unaffected. GM/trigger `forecast_override` with duration countdown & auto-revert.
- **Calendar** (task-228): `game_day/month/year` derived from ticks + `calendar_config`
  (`minutes_per_day`, `days_per_month`, `months_per_year`), exposed in `/api/state`. `set_game_time`
  / `set_game_date` effects.
- **Moon phases** (task-229): deterministic 30-day cycle (`new → crescent → quarter → gibbous →
  full → waning`). Outdoor night areas add the moon's `light_bonus` to ambient light (full moon
  +25, stormy nullifies it, foggy halves it). `blood_moon` override stains the sky red (+30).
  Moonlight lines in area descriptions.
- **Wind** (task-231): `none/breeze/wind/gale/storm/hurricane` — accelerates heat propagation
  (stronger wind wins), wind chill resisted by `wind_resistance%`, extiguishes lit items on
  gale+ (10%–60% chance/tick), drains Energy on exterior moves. New item properties
  `wind_resistance`, `water_resistance`.
- **Humidity** (task-232): `dry/humid/wet/flooding` — affects effective temperature (hot +2/+3/+4,
  cold -1/-2/-3), saps Social in humid air, flooding adds +1 Energy cost to movement.
- **`effective_temperature`** now accepts `wind_level` + `humidity` kwargs (backward-compatible).
- **Trigger effects** (task-234): `set_time`, `set_date`, `set_weather`, `forecast_override`,
  `adjust_forecast`. `set_environment`/`adjust_environment` extended with `weather`, `wind`,
  `humidity`, `transparent` keys + cycling. New trigger types: `on_turn_start`, `on_turn_end`,
  `on_dawn`, `on_dusk`, `on_day`, `on_night`, `on_full_moon`, `on_blood_moon` (one-shot per
  game-day via last-fired cache). New conditions: `date_equals`, `moon_phase_equals`, `weather`.
- **Settings**: `GET/POST /api/settings/forecast`, `POST /api/settings/forecast-override`,
  `/api/state` exposes `game_day/month/year`, `moon_phase`, `forecast_schedule`, `forecast_override`.
- **Engine Config**: `forecast.apply_scope` (exterior/all), `heat.base_rate`/`heat.max_delta` now
  apply wind multiplier.

### 🌠 Sky Clock widget (GUI)

- **Top-bar live widget** (`static/js/sky-scape.js`): `🕐 09:40 · Jan Day 1 · 🌑 new moon · ☀️ clear
  · rain in 2h` — replaces the bare `#ui-time` clock. Driven by engine state, clickable → opens the
  **World Sky panel**.
- **World Sky panel** (modal): animated sky stage (gradient, sun arc, moon arc with v2 realistic
  moonrise/set, seasonal hill colors, weather layers with clouds/rain/snow/fog). Time skips
  (+15m/+1h/+1 day), weather override dropdown + duration + Set/Clear, forecast next-change
  indicator, GM override indicator. Ported from the qwen/GLM mockups and wired to engine APIs.
- **Design note** reconciling mockups + roadmap + implementation: `docs/design/sky-widget-reconciled.md`.

### ✨ NL Editor power-up (9 features)

- **Ghost-node canvas** — staged entities appear as translucent dashed nodes on the graph in real
  time; updates/deletes tint the live node amber/red; attach/detach get dashed ghost edges.
  Re-applies after every graph reload.
- **Auto-pan spotlight** — when a turn finishes with fresh staged ops, the camera gently pans to
  the newest staged target ("here's what I just drafted").
- **Selection-aware prompting** — the system prompt reports the currently-selected node as the
  default "this room/node"; `update_node`/`delete_node`/`get_node`/`spawn_library_item` auto-fill
  a missing id from the selection.
- **Inline staged property tweaker** — ✎ on any staged row → editable JSON payload, save/cancel.
- **Selective partial apply** — checkbox per op + **Apply Selected (n)**; unchecked ops stay staged.
- **`populate_area(area_id, theme)`** — one call stages a whole themed pass: 9 theme packs
  (apothecary, kitchen, garden, study, smithy, warehouse, shrine, bedroom, generic), each with an
  NPC, items, attachments, and area ambience.
- **Smart mechanic inference** — glowing crystal → `light_source`/`dim`/`lit`; roast chicken →
  `eat` action; plus sound/heat/weapon/armor/read/drink rules — all automatic from the name.
- **Lore & style awareness** — system prompt injects scenario name, theme, up to 6 world-lore
  entries, and the selection; rule 6 enforces style consistency.
- **`>` palette route** — Ctrl+K → `> make the tavern darker and add a violin` → Enter → NL Editor
  opens, input filled, agent runs in the background.

### 🛠 Fixes

- **`POST /api/graph/batch`** — NL Editor's Apply now sends all staged ops as one server-side
  batch, recording exactly ONE undo snapshot. A single Undo reverts an entire Apply. (Previously
  each per-op API call pushed its own snapshot, and several op types hit wrong routes giving 405 or
  silent no-ops.)
- **`update_node` flat patch** — the agent hands `{description: "..."}` and the PATCH route now
  accepts it (was silently ignored).
- **`link_to_library`** — `template_id` now correctly lands in `properties`.
- **`connect_areas`** — connection edges now carry `direction` + `visible_in_direction` props so
  exits actually resolve.
- **`search_library_areas`** — now searches `description` too (matching the items search).

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — the running process needs to pick up the new engine code
  (calendar, forecast, moon, wind, humidity, trigger effects, routes).
- Weather forecast scenarios: **zero authored entries = no behavioral change** — existing scenarios
  are unaffected. To use weather, author a forecast schedule via `/api/settings/forecast` or set
  a GM override via `/api/settings/forecast-override`.
- Moon/turn/time triggers fire only on nodes with attached trigger nodes of the matching type.
- The Sky widget's time skips (+15m/+1h/+1 day) adjust the clock display but do NOT run engine
  ticks — they're visual helpers. Use `/api/turn/apply` for actual world-time advancement.
- `wind_resistance`/`water_resistance` are item properties set via the inspector or library; no
  library items have them yet. They work as soon as set.
- The after-request hook's post-state snapshot push for simple graph edits (PATCH `/api/graph/node/`)
  still makes the first Undo a no-op — the batch endpoint is exempt but the per-edit quirk remains.

### 🧪 Behind the scenes

- New test file: `tests/test_graph_batch.py` (6 tests), `tests/test_engine_config.py` baseline
  updated for `forecast.apply_scope`.
- Task vault: 227/228/229/231/232/234/378/379/387 — all implemented in this session.
- Full suite at **2633 passing**.

Items stopped being cardboard props. Uses, durability, weight, freshness, stacking, crafting,
teaching, auto-dressing, gated shortcuts — and a pile of the item/gameplay todo queue landed in
one pass, tested with **2615 passing**.

### 🧰 Items grew up

- **`max_uses` + weight reconciliation**: a half-eaten loaf weighs what's left
  (`base_weight × uses/max_uses`); infinite-use items stay static; `combine` merges two
  identical stacks (uses summed, clamped at max, source destroyed), `split <item>` divides one
  into parts — capacity re-checked, "stackable twins" ignore the auto-renamed copy suffix.
- **Armor & equipment wear on hit**: outermost armor/clothing decrements uses; at 0 it breaks —
  back to carrying + `on_break` trigger. **No raw numbers anywhere**: prompts read
  `[pristine/worn/battered/about to break/broken]`, the HTC chips and paperdoll modal show
  plain words, the item inspector has a durability bar.
- **`on_use_progressive`** trigger type — fires on every use; gate thresholds with the existing
  `uses_reached`/`uses_above` conditions.
- **Freshness**: `perishable` food decays per tick → `spoiled` (fires `on_spoil`), cooking —
  use fresh food on an oven/stove/heat source → `cooked`, decay halts. Examine and prompts say
  it in plain words: `(fresh)`, `(cooked)`, `(spoiled)`.

### 🗺 Gated paths & movement

- **`requires_item` on ways** — a bike lane needs a bike, a fly path needs an item tagged `fly`:
  visible-but-blocked without the gear, open with it. Prompt exit lines show `(needs: bike)`.
- **Over-encumbrance = one size larger**: ≥50% load bumps your effective size tier — narrow
  passages stop fitting.
- **Chain follow-ups (task-104)**: the dash→go chain generalized — `lead` → go/approach/
  release, `grab` → approach/release. One same-turn follow-up, agent-decided.

### ⚒ Crafting & knowledge

- **Full recipe system**: recipe graph nodes + `engine/crafting.py` — inputs (consumed or not),
  conditions (`state_equals`/`has_item`/`random_chance`/`skill_check`), outputs hydrated from the
  library, learning via `global` / `skill:<name>` / `item:<name>` / discover-on-first-craft,
  persisted `crafting_known`. Commands: `craft`/`make`. 🧪 Recipes panel in the agent inspector.
- **`teach <recipe | skill:NAME> to <character>`** — teacher must know it, student must be
  present; recipes transfer, skills +1.
- **`use N items on target`** — structured `amount` on use_on (`use 2 eggs on pan`) validates
  against tracked uses and consumes N; prompt shows the syntax.

### 🧍 Characters dress themselves

- **🤖 Auto-Dress from Interests** (Inventory tab): scans the item library for wearable pieces
  matching `interest_tags`, equips through the normal stacking rules, weather-aware
  (hot → skips heavy insulation, cold → wants it), idempotent by construction.
- **✨ Generate from Personality** (Bio tab): the character's LLM gets the full system tag list
  and answers with JSON/CSV tags → sets `interest_tags` in one click.
- **🌊 Simultaneous Mode (experimental)** — every autonomous character acts on its own
  countdown derived from Social/traits/Energy (high-Social acts more, exhausted slower).
  Chaos by design; sequential mode untouched; off by default.

### 👁 Senses & health

- **`scry` effect**: a frozen distant-area view (rendered description + ambient light + exits) —
  the shared observer path is untouched. Editor entry with area picker + lead-in/fail text.
- **`proximity_effect` items** (EMF-style): BFS room-distance readings on examine — sharp when
  they're right here, needle-jumps adjacent, faint blip beyond, prose only.
- **Context-aware vitals**: isolated-wording only when you're actually alone and quiet; company,
  addressed-to-you, noisy rooms, and visible food/drink all change the lines. Sanity is now a
  neutral stress curve — no more "the shadows seem to watch you" in a bright Taco Bell.
- **Encumbrance in the prompt + HTC** — natural language ("at the edge of your capacity"),
  never numbers.

### 💬 Input & feedback

- **Invalid-action auto-retry** (setting, off by default): one same-turn retry with the error
  fed back for rejected and engine-failed actions.
- **Appearance grammar guardrail**: third-person directives + few-shots, validator catching
  `you is`/`body is who` leaks, one silent repair pass, safe fallback — broken text never
  persists (it re-sends into every prompt forever).
- **Carried/worn prompt lines**: full untruncated description + allowed actions +
  (known / not yet examined) + durability + freshness.
- **Gear totals strip** in the Inventory: armor / best weapon / insulation / resistances as
  pills with "from: …" contributor tooltips — one place, no per-item duplication, same
  aggregation rules as the engine.

### 🧪 Trigger-effect templates

- **42 library items** — `template_<effect>` (e.g. `Template: Scry`), each with a wired
  `on_use` trigger demonstrating that effect; generator at `tools/gen_effect_templates.py`
  (re-run after new effect types, a coverage test guards it) + index in
  `docs/virtualWorld/Templates/trigger-effect-template-items.md`. Scenario-ending/room-spawning
  ones are loudly flagged ⚠️.

### 🎓 Help, tips & guided tours

- **❓ Help Center** (top bar or **F1**): a coach-tip system that fires *when you touch the
  thing* — welcome tip on first load, inspector tips per view type (area/item/way/agent),
  button-triggered tips for Settings, the Game menu, Overlays ▾, More ▾, Triggers, ▶ run,
  auto-dress, crafting, and a ⚠️ warning when Simultaneous Mode flips on.
- **Spotlights**: "Show me" physically highlights the UI element the tip describes (the card
  stays put; ESC/✕ clears).
- **Guided tours**: *First five minutes*, *Triggers & effects*, *Scenario workflow* — ordered
  chains with Next steps.
- **State**: tips remember themselves (localStorage per-id) with session re-shows; the index
  lists every tip with one-click replay and Reset all. No second system — tips point at the
  real UI, and the registry is one easy-to-extend array.

### 🛠 Fixes

- **⋯ More ▾ and Overlays ▾ dropdowns** were opening *invisibly* — the toolbar's
  `overflow-y:hidden` clipped them; now visible.
- **`take` puts everything in a hand first** (generic held; hands full → one item auto-stowed
  to carrying, then pick up, same turn; `two_handed` needs both hands; intrinsic abilities skip
  to carrying). New **`stow`** verb.
- **Saved worlds are graph-only** — no more redundant per-room `exits`/`exits_authoring` in
  scenario files (runtime `/api/state` payload still computes exits live).

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — engine + route changes need the fresh process; static
  JS/UI is reload-only.
- The **mature-tags → inspection reveal** discussion stays open: newer item mechanics
  (freshness/proximity/max_uses) aren't yet wired into the tag-reveal pattern in the item
  inspector — say the word and they get the same treatment.

---

## 1.1.0 — "The World Is Yours" (2026-08-30)

The big one: authoring stops fighting you. Everything below shipped in one working session, tested with 2500+ automated tests.

### 🌍 Scenario workflows — no more losing work

- **Scenario status chip** (top bar): `📦 <scenario> ●` lights up the moment the live world drifts from its source, with **💾 Commit** and **🌀 Restart** right there. Commit writes your live world into the scenario source so Restart keeps your changes — the old "I built it and the restart ate it" trap is dead.
- **Honest Save menu**: `💾 Commit Scenario` (server-side, updates the source you're working on) vs `📤 Export Scenario File…` (download), no more pretending a download saved your scenario.
- **Import preview**: before `Load JSON…` touches your world you see rooms/items/ways/characters, format, and sanity notes (dangling exits, players in missing rooms) — then **Apply (Undo protects)** or **Cancel**.
- **🔬 Deep audit** (import preview + Scenario Manager): the full trigger validator runs against a file *before* you load it — "3 errors · 2 warnings · 4 info" with the top issues.
- **🗂 Scenario Manager**: every `data/scenarios/*` file listed with stats — Open (undo-protected), Audit, Copy, Rename, Delete, Refresh.
- **Changes-since-source diff** endpoint: structural diff (rooms/players/env/exits) between live world and source — the backend for reviewable commit/discard.
- **Restart stays undo-safe**; undo now shows **labels** via the visible **📜 history dropdown**.

### ⚡ Authoring speed

- **Ctrl+K command palette**: type `kitchen`, jump to it. Type `save`, run it. Nodes, system actions, panel tabs — one fuzzy search.
- **🧩 Trigger snippets**: one click fills an entire trigger — Chest, Light Source, Heat Source, Recorder (captures recent speech!), First Aid, Book, Whispering Door.
- **Spawn item** editor fields for **Place into (area/container)** and **Capture recent speech** — the recorder/chest recipes survive saving.
- **📋 Duplicate room** (with items, contents, triggers — `"Kitchen (2)"`) and **duplicate item** (`"Lantern (copy)"`, placement preserved).
- **🕘 Recently-edited rail**: last 10 nodes you touched, click to jump back.
- **Keyboard map**: **Ctrl+S** commit, **Ctrl+Z / Ctrl+Shift+Z** undo/redo (typing-safe).

### 🧲 Trigger system — way more toys

- **New effect types**: `spawn_way` (runtime doors, one-way supported), `spawn_area` (runtime rooms), `set_way_target` (portals/elevators — repoint a door at runtime), `set_way_view` (see-through / view text).
- **New condition**: `item_relationship` ("does this item have anything inside?" by edge type, with target filter).
- **New template params**: `{uses}`, `{weight}`, `{current_state}`, `{name}` and **`{vital:Thirst}`** readouts in messages.
- **Result**: recorded during authoring — the spread of "flavor" engines you can build with effect-composition is dramatically wider.

### 🩺 Conditions — six new ways to be in danger

- **wet** — soaked clothing keeps only 20–60% of its insulation (levels 1–3).
- **injured** / **bleeding** — body-part wounds, level-scaled HP drain, ends on fix/bandage/medicine.
- **hypothermia** — level-scaled Energy/HP drain, dexterity auto-fails, staged symptoms (shuddering → shaking → warm and sleepy).
- **suffocating** — blocks actions + movement, drains, staged symptoms, ends on breathe.
- **petrified** — stone: blocks everything, +5 defense, STR/DEX/CON saves auto-fail.
- All six live in the data-driven condition library — **browser-editable**, like every other condition.

### 🗺 World creation

- **✨ Scenario from Text**: one premise sentence → AI drafts rooms, doors, items, characters, lore → review cards (accept per room, regenerate a room, prune items) → apply, undo-safe. TemplateLoader now carries item tags + light/heat props and a supporting `characters` cast.
- **Save/Load modal**: autosave slot (pinned AUTO), per-save stats (time/turn/player/room counts/size), overwrite-in-place, rename, delete, and **app version** stamped on every save.

### 🛠 Fixes & honesty

- **Temperature rounding**: no more `-10.452438125°C` anywhere — stored and displayed at 0.1°.
- **Honest defaults**: the Light Level field says "— unset (engine uses Dim) —" instead of pretending; heat-source inputs show real placeholders; Issues panel gets an **⚙ quick-fix** and info-level notes for defaulted mechanics (light/heat) instead of false broken-tag warnings.
- **`go to the doorway` now walks you up to the door and stops** — crossing is explicit (`go through`, `go <room>`, `dash`); new **`approach`** verb everywhere (MCP + prompts + GUI).
- **Character knowledge** moved into a proper modal (Advanced tab → Knowledge): category tabs, search, bulk select, stale-ref cleanup — and the per-entity "Known by" panels removed from items/areas/ways.

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — the running process needs to pick up the new engine code.
- `give`/`steal` item matching is still strict (bug-35 filed — typos like `jumptuit` fail); take/equip no-op wording is being reworked (bug-25 reopened).
- `llm_respond` (trigger-driven chat) is **blocked** — the engine has no LLM provider; needs a host-side decision.

### 🧪 Behind the scenes

- New test files: `test_template_loader`, `test_trigger_effect_ways` (12), `test_more_conditions` (11), `test_scenario_commit` (5), `test_undo_history` (5), `test_duplicate` (4), `test_scenarios` (7), `test_scenario_diff` (4) + validator tests — suite at **2507 passing**.
- Task vault restructured: 20 new tasks (367–386) from the workflow audit; duplicate numbers resolved; sequence doc accurate.
