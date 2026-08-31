# Changelog

All notable changes to VirtualWorld. See `docs/virtualWorld/Scenario Workflows & UI Audit.md` for the long-term plan this release follows.

---

## 1.2.0 — "Craft & Carry" (2026-08-31)

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
