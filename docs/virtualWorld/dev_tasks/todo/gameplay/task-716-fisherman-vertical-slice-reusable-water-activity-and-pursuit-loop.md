---
type: task
status: todo
area: gameplay
priority: high
---

# task-716: Fisherman — step-by-step authoring and implementation checklist

**Filed:** 2026-10-05
**Related:** task-90, task-321, task-409, task-504, task-569, task-591, task-650, task-701, task-702, task-703, task-704, task-705, task-714

## Missing code features and required data additions

This is the implementation inventory. The numbered steps below give the authoring order and the complete playable flow.

### New/changed engine and editor behavior

- [ ] **Add a generic `start_activity` trigger effect.** The existing `on_use_on` event dispatches; the effect is missing from the 58-type effect vocabulary. It should start an Activity for the active actor using the trigger's target place and tool, after validating the authored requirements. Expose it in the trigger editor.
- [ ] **Target entrants in area-trigger effects; add a graph-aware `push_actor` effect (working name).** `on_enter` and the `save` effect's `on_fail`/`on_success` branches already exist. However, effects on an area trigger currently target the trigger's area node before they consider the character that walked in. **Design correction (user, 2026-10-05): wetness is a condition, not a bespoke effect.** A `wet` condition already exists (`data/library/conditions/wet.json`) and `engine/traversal.py` already applies it on failed crossings. The water-entry path should use generic `apply_condition` with an explicit **entrant** target; `set_wet` is offered in the UI but is not the requested path. Make `push_actor` move that entrant along a configured connected downstream Way using normal movement/entry handling, not teleporting. Reconcile with `engine/traversal.py`'s existing rapids check so the entrant makes one check, not two. No new trigger event or skill-check system is needed.
- [ ] **Extend Activities from descriptive records into reusable activity definitions/resolvers.** `ActivitySystem` already starts records and advances elapsed time, but per-Activity outcomes are hard-coded for sleep/bathing and activity behavior is spread across type sets. Add a reusable definition/resolver seam for start checks, tool/place binding, per-interval effects, completion conditions, turn occupancy, and interruption. Fishing is authored data for that seam.
- [ ] **Resolve catches at runtime from the painted area's biome distribution.** `engine/world/spawner.py` currently consumes `resource_distribution` only during generation; the live audit found no fish tags authored in any current distribution. Reuse the weighted biome tag sets during an Activity interval, apply any separate no-catch/skill/weather/season modifiers, resolve tags to real item definitions, and add pooled catch quantities to the creel. Do not create a second independent fish/junk loot table.
- [ ] **Extend pursuit execution with an Activity step and completion/progress.** The template validator currently permits only `travel`, `take`, and `drop`, and the runner executes only those kinds. Add an `activity` step that starts/continues the selected Activity and can finish on a bound catch quantity or time cutoff; preserve the pursuit when conversation interrupts the immediate plan. **Design correction (user, 2026-10-05): pursuits are JSON data, not hardcoded Python.** The step vocabulary is a data-declared contract (task-701/702) — the `activity` step is added there, not as a new hardcoded branch in `engine/background_plans.py`; authoring a new pursuit must require no new Python.
- [ ] **Connect danger to the existing threat/replan path.** The LLM `ThreatDetector` already detects hostile actors and feeds `PlanTracker` replanning; background simulation also has its fear pass. Do not build threat detection. Ensure the fisherman can stop/leave the Activity and choose a safe response while the Pursuit remains available.
- [ ] **Connect pursuit controls, structured LLM context, and the existing Mind UI.** The actor-bound pursuit/template groundwork exists, but the active pursuit is not yet sent to the LLM as its own structured block. Add controls to the selected-character UI for binding/assigning/pausing/replacing/clearing this pursuit, and show its reason, current plan, Activity, progress, and interruptions in the existing Mind panel using their runtime sources.
- [ ] **Optional: add proactive greeting behavior** with a cooldown if the “Nice day for fishing” encounter remains in the slice. Reuse existing perception/presence; this is a social choice, not a new threat or witness system.

### Required authored data (not new engine features)

- [ ] Add distinct WorldPainter biome records for riverbank, walkable shallows, quiet/deep pools, and rapids/current, with tags and descriptions. `engine/biomes.py` is data-driven; new biome IDs are JSON entries, not new compiler code. Do not reuse `bank`, which is already a commercial bank.
- [ ] Add weighted fish, scrap, trash, and other water-resource tags under the matching biome keys in `resource_distribution`, plus real matching item definitions. The generic runtime resolver above is the new code that makes these generation tables affect catches during play.
- [ ] Author downstream direction/target and the check/DC on each current-bearing reach, along with fishing eligibility and outcome modifiers. Reuse existing trigger events (`on_enter`, `on_use_on`) and the existing `save` effect branches.

### Existing vocabulary to reuse or expose

- The backend already has **41 trigger events**, including `on_enter`, `on_use_on`, and `on_tick`; no new event name is needed for the first slice.
- The condition evaluator already has **39 condition branches** for tags, equipment/items, counts, time/weather, and checks. The trigger editor exposes **25 named condition choices** plus “Always”; it omits useful existing backend conditions including `target_has_tag` and `contains_count`. Expose `target_has_tag` so the rod's `on_use_on` trigger can validate a water target. A new condition evaluator has not been shown to be necessary; use the existing `save` effect's failure branch for the current check.
- `engine/traversal.py` already maps `river`, `rapids`, `ford`, and `flooded` to Athletics and marks failed crossings wet. That behavior turns a failed crossing back; it does **not** push someone downstream after arrival. Add the requested post-arrival response without also rolling the traversal check a second time.
- Same-area Activity descriptions/witness perception already exist. Keep using that path for “James is fishing”; extend its payload only if the new Activity definition needs additional visible detail.
- Character creation and live inventory/equipment controls already exist. Starting gear is authored/assigned through those controls; a character-item save/load change is not a requirement for this slice.

## The model

- **Pursuit:** the character’s longer undertaking and reason. It can be assigned, chosen, changed, or refused.
- **Plan:** the character’s current approach. An interruption can change the plan without erasing the pursuit.
- **Activity:** the visible thing happening over time at a place, such as fishing or sleeping.
- **Schedule:** a time/calendar reminder that may make a pursuit relevant; it is not the pursuit or Activity.
- **Recipe:** rules for transforming inputs into an output, such as cooking fish. Fishing is not a recipe.

## Step-by-step checklist

### 1. Work in the current world

- [ ] Continue in the existing `kraktooth_goblin_camp` world. Do **not** make a duplicate scenario for this slice.
- [ ] Do not regenerate already-baked scopes such as Eldenford; make the new regional scopes and content where needed.

### 2. Expand Abandoned Farms and Raven River in WorldPainter — complete for this regional slice; full river remains

- [x] Open **Build → WorldPainter** and use the supplied Abandoned Farms map as the reference image (`▦ Match`). Start from the existing `world` root.
- [x] Create a paintable **Abandoned Farms region** child scope with **➕ Add feature…**. Do not use **🪜 Make this a scope…** for a scope that must be painted/generated.
- [x] Paint the world-scale region first: river corridor, roads, terrain, and north-to-south route. Named the addressable places Raven River — Farms Reach, Old Stone Bridge, Mill Pond, Blackmarsh Pond, and Abandoned Farm Fields.
- [x] Make the continuous north-to-south route across the authored Abandoned Farms region take **at least five in-game hours on foot**. The live pass measured a 363-cell trail at approximately six hours under the active setting (1 cell = 1 turn).
- [ ] Expand Raven River from the authored Farms Reach into a continuous, multi-day shoreline geography. Add connected, distinct named reaches (upper river, farm reach, ford, landing, shallow banks, deep pools, rapids); the total shore walk must take several in-game days. **Blocked on B1:** distinct names in one merged region require distinct biome records. The Abandoned Farms map is one reach, not the entire river.
- [ ] Add the farm settlement as a paintable child scope at its location in Abandoned Farms. Then author its buildings/interiors inside that settlement; the fisherman's hut is one interior. Follow **world region → settlement → interiors**, rather than making the hut a world-scale area. The regional scope and hut interior are authored; a separate settlement child scope remains to be established if the content hierarchy requires it.
- [x] Generate the new region and connect it to the existing world. The live pass generated 27 areas + 54 ways and verified a world gateway after parent regeneration; the hut is reachable through the generated chain. See B2 for compile/regeneration behavior.

### 3. Author the fisherman's home, water places, and contents — hut complete; water authoring remains

- [x] Author the small hut interior with a bed, stove, storage, and door/exit. The live pass created a 6×6 `Fisherman's Hut` with 16 interior areas and placed `bed`, `stove`, and `barrel`. Cooking behavior is outside this fishing slice.
- [ ] In the river region, make separate addressable bank/shore, walkable shallows, deep water, rapids/current, ford/crossing, and fishing access places wherever their traversal or fishing rules differ.
- [x] Use existing `angling_rod`, `creel`, and optional `bait_tin` item templates; do not create duplicates. James carries a rod and creel suitable for pooled catch quantities.
- [ ] Add distinct WorldPainter biome records for riverbank, walkable shallows, pools, and rapids/current, with tags and descriptions. **Blocked on B1:** WorldPainter caches biome taxonomy; restart the server after adding records. One merged region gets one authored name, so use distinct biome IDs where separate named reaches are required.
- [ ] Add weighted fish, scrap, trash, and other water-resource tags plus matching item definitions under the relevant biome keys. Current `river`/`lake` distributions have no fish tags (live audit); the generic Activity resolver must sample them at runtime.
- [ ] Decide and author: bait requirement; no-catch/fish/junk weights; stock depletion; season/weather/time/skill modifiers; catch target and return cutoff. Proposed first value: **10 fish or dusk**. Keep settings editable by habitat/reach.

### 4. Create and equip the fisherman — complete

- [x] Open **Build → Library → Characters → ➕ New**; author James's identity, appearance, personality, and hut as default location; save to Library and import to World.
- [x] Set James as a Simple NPC. Add angling rod, creel, bait tin, and clothes; equip tunic, trousers, and boots through the paperdoll slot controls.
- [x] Assign Knowledge of the hut areas, river reach, bridge, fields, and gear through **🎛 Manage**. The live pass also recorded the editor's LLM auto-draft/DiffModal “Update Selected” pitfall; see the authoring log below.

### 5. Implement water movement rules

- [ ] Add an `on_enter` trigger to each wadeable-shallows area. Apply the existing `wet` condition to the **entrant** via generic `apply_condition` (user correction 2026-10-05: no bespoke `set_wet` on this path). The live audit measured `set_wet` in the editor, but area-trigger effects currently target the area node; the effect context needs an explicit entrant target.
- [ ] Decide which check applies: proposed split is Dexterity/footing for balance and Athletics for swimming/strong currents.
- [ ] Author each current-bearing reach's downstream Way and save/check DC. Attach an `on_enter` trigger using the existing `save` effect with `on_fail` → `push_actor`; settle the interaction with the existing traversal check so there is one check per arrival.
- [ ] The new `push_actor` effect must use that connected downstream Way, handle blocked routes, and run normal entry effects. Do not shove every tick in this first slice.
- [ ] Reuse the existing river/rapids Athletics hazard and its `wet` condition behavior where they match (`traversal.py` already applies the condition on failed crossings). The missing behavior is the post-arrival downstream current response; `bank` in the biome list is a commercial bank.

### 6. Implement fishing as a persistent Activity

- [ ] Author a rod `on_use_on` trigger/action for eligible water places. The generic `on_use_on` dispatch already exists in `engine/items/use_actions.py`; do not add a second trigger event. Validate actor state, held/carried rod, target habitat, gear suitability, and bait if required.
- [ ] Successful use starts a persistent, observable `fishing` Activity; it does not immediately award a fish.
- [ ] Add a generic, data-driven Activity resolver contract for start requirements, place/tool binding, elapsed progress, interval effects, completion, and interruption. Fishing is one authored Activity definition; do not build a fishing-only progress engine.
- [ ] Resolve outcomes from the current water area's biome/reach `resource_distribution`, with editable attempt interval, weighted catch/no-catch results, quantities, bait, modifiers, and stock rules. Author at least river and lake cases through the same resolver.
- [ ] On each game-time interval, resolve one outcome and put catches in the character’s creel using pooled quantity/containment rules (task-504). Recheck actor/tool/place before resolving so interruption or theft cannot create a catch.
- [ ] Store the Activity on the actor with target/place and tool. Reuse the existing same-area witness/perception path so another character in the area can receive a witnessed entry such as **“James is fishing.”** Add fields to the Activity description/state only where the existing witness payload needs them.
- [ ] Define what talking, leaving, losing the rod, incapacitation, and death do to the Activity. A stolen rod remains usable by the player through the same interaction.
- [ ] **Code needed:** `start_activity` effect, generic Activity definition/resolver, runtime sampling of biome resource distributions, and catch-to-creel handling. `on_use_on`, `on_enter`, and `on_tick` already exist; do not add duplicate event names.

### 7. Implement pursuit and interruption behavior

- [ ] Add a reusable `fish-and-bring-home` pursuit template with prose purpose and parameterized home, fishing place, route, gear, time window, catch target, progress source, and stop/return rules — **as a JSON library entry** (user correction 2026-10-05: pursuits are JSON data, not hardcoded Python; see task-701/702).
- [ ] Bind it to the character with a personal reason, for example: “The family is short on food; I want to bring home a catch.” Fish quantity and household outcomes are world state, not an artificial reward token.
- [ ] Use the existing pursuit work: task-701 templates, task-702 plan/activity execution, task-704 choice, and task-705 requirements. Schedules use the existing clock as reminders; they do not replace pursuits.
- [ ] Simple NPC rules: travel, start fishing, return at quota/dusk, and respond to the existing threat signal when a safe route exists. LLM characters receive the same world facts and can continue, adapt, pause, or refuse.
- [ ] Connect pursuit progress to real creel contents and Activity state; preserve/re-evaluate the pursuit after conversation or danger interrupts the current plan. Use the existing threat detector/replan path; do not add another detector.
- [ ] Optional: add a simple-NPC greeting choice with a cooldown when another character is perceived nearby, such as “Nice day for fishing, ain't it?” Speech response remains on the existing speech path; conversation can interrupt the immediate plan without erasing the pursuit.

### 8. Add assignment and Mind UI

- [ ] Add controls on the selected character to choose a template, bind its places/gear/target, assign, replace, pause, and clear the pursuit.
- [ ] Extend Mind to show motive, pursuit, schedule cue, immediate plan, Activity, progress, interruptions, and related memories from their runtime sources.
- [ ] The **🧠 Mind** button already opens the Memory Mind dashboard. Task-714 expands that display; it does not provide pursuit assignment. Assignment needs a separate UI task.
- [ ] Optional: use **✨ NL Editor** to draft the character/content once a model is configured; validate all names/ids and mechanics before applying. NL generation cannot implement a missing engine feature.

### 9. Play through the complete slice

- [ ] Assign the pursuit at home and advance the simple-NPC simulation.
- [ ] Confirm the fisherman follows actual known ways, reaches the shallows, and starts fishing through normal rod-use dispatch.
- [ ] Advance game time; observe no-catch and catch/junk outcomes; confirm catches enter the creel and progress updates from its quantity.
- [ ] Interrupt with conversation and separately with danger. Confirm the chosen social rule, flee route, and that the pursuit survives unless abandoned.
- [ ] Reach 10 fish or dusk; confirm the fisherman returns home with the catch.
- [ ] Take the rod and use it as the player. Confirm the same Activity/profile loop works for the player.
- [ ] Repeat at a second habitat using its different profile. This is the proof the feature is reusable.

## Current status at a glance

| Exists now | Missing or incomplete |
|---|---|
| **Authored and verified live:** Abandoned Farms WorldPainter region (160×100; 27 areas + 54 ways); north-to-south trail ≈6 hours at the measured active setting; world gateway; Fisherman's Hut (6×6, 16 areas, bed/stove/barrel, gateway); James as a Simple NPC with fishing gear/clothes equipped and relevant Knowledge; existing world clock/weather/seasons; generic Activity records/elapsed tick and same-area witness support; trigger dispatch; 58 engine effects/41 trigger events and live editor's 40 events/49 labeled effects; weighted `resource_distribution` at generation; river/rapids Athletics/Wet crossing; existing LLM threat detection/replan; pursuit/template groundwork in tasks 701–705. | **Content still to author:** separate settlement child scope if required by final hierarchy; new distinct water biome records (B1); fish/scrap/trash tags and matching items; named connected river reaches spanning several in-game days; habitat-specific current directions/DCs and fishing settings. **Code/editor still needed:** entrant-targeted generic `apply_condition`; graph-aware downstream `push_actor`; `start_activity` effect; reusable Activity definition/resolver and runtime distribution sampling/catch-to-creel; pursuit Activity step/progress/completion/interruption integration; pursuit assignment and structured LLM/Mind display (inspector measured at 29 sections/32 controls, no pursuit controls); optional greeting. B2: first large-grid compile took 282.5 s and API regeneration requires `region_merge: true`; behavior/cost remains unexplained. B3: feature-tool placement via click needs human check; `/grid/place` works. |

## Live authoring pass — 2026-10-05 (no code changes; everything below was done through the running app and its endpoints)

Verified **working live**, on `kraktooth_goblin_camp` with the existing server:

- **Step 2 (region)** — Built a paintable `Abandoned Farms` child scope via ➕ Add feature… ( lands as `mode: town`; switched to `world` in the 📦 Grid… dialog), resized to **160×100** ("region" preset is sized in turns), loaded `abandoned farms.png` as the ▦ reference and matched it. Painted 16,000 biome cells + 496 road cells (river corridor, dense forest, farmland, sparse fill, a 363-cell winding north–south trail ≈ **6 h at 1 cell = 1 turn** — clears the 5-hour bar — plus a 36-cell bridge and the South Road). Named Raven River — Farms Reach, Old Stone Bridge, Mill Pond, Blackmarsh Pond, Abandoned Farm Fields. ⚙ Generate minted **27 areas + 54 ways**; after regenerating the parent, `way_gateway_world_abandoned_farms` ("Road (world 13,7) → enter abandoned farms") makes the region reachable. All of it persists in `data/autosave.json`.
- **Step 3 (complete)** — Painted a `cottage` building cell and created **Fisherman's Hut** (mode `interior`, 6×6, walls + bedroom/kitchen/storeroom, three named corners); generated it (16 interior areas) and placed `bed`, `stove`, `barrel` in the three corners. The hut gateway (`way_gateway_abandoned_farms_fisherman_s_hut`, "Cottage (Abandoned Farms 104,62) → Hut Sleeping Corner, enter fisherman's hut") minted on a `region_merge: true` regenerate — the full walkable chain is **world → enter abandoned farms → region → enter fisherman's hut**. See blocker B2 for why the first regenerate attempts failed.
- **Step 4 (character)** — Full UI flow works: Library → Characters → ➕ New → Save to Library → Import to World. Authored **James** (fisherman personality/appearance, default area = hut), placed him via the import room picker, gave him angling_rod + creel + bait_tin + tunic/trousers/boots (graph `carrying` edges), equipped the three clothes through the paperdoll slot pickers, set `simple_npc: true`, and assigned Knowledge (13 hut areas + reach + bridge + fields + the three gear items) through 🎛 Manage. **Gotcha hit twice:** the character editor's LLM auto-draft filled the "empty" form and saved a Doctor-James-Torrens record under my new id; the DiffModal is where authored values win — resolve it with "Update Selected" rather than re-saving.

Verified **missing**, with counts (task claims re-measured, not assumed):

- **Step 5 blocked (engine + UI).** Engine `EFFECT_TYPES` = 58, `TRIGGER_TYPES` = 41; the live Add-Trigger editor exposes **40 events / 49 labeled effects**. `save` ("🎲 Save Gate") and `set_wet` ("💧 Set Wet") **are** offered in the UI dropdown — but `start_activity` and `push_actor` exist in neither the engine's 58 nor the editor's 49. Also per task: `set_wet` on an area trigger still wets the area node, not the entrant.
- **Step 6 blocked (engine + data).** Live rod test as James standing in "Raven River — Farms Reach": the rod's actions are `examine, take, drop` only — `use angling_rod on river` answers "can't figure out what to do with it", and `fish` "succeeds" as a no-op with `activity: null`. No `start_activity` effect, no Activity resolver, no runtime sampling of `resource_distribution` (spawner consumes it at generation only; the authored `river`/`lake` weights are herb/food/junk — **no fish tags authored anywhere**).
- **Steps 7–8 blocked (engine + UI).** Pursuit groundwork exists (`engine/pursuit_templates.py` + authored `gather`/`haul`/`rally` templates) but the executor (`background_plans.py`) runs only `travel`/`take`/`drop` — no `activity` step, no quota/time completion. No `fish-and-bring-home` template. The agent inspector (29 sections, 32 controls, counted with all tabs/disclosures) has **no pursuit bind/assign/pause/clear controls**, and the 🧠 Mind dashboard shows memory views only — no motive/pursuit/plan/Activity/progress/interruption blocks.

**New blockers found during this pass:**

- **B1 — biome vocabulary needs a restart.** Step "required authored data" wants riverbank/shallows/pools/rapids biome records. They are JSON entries in `data/worldpainter/biomes.json`, but the painter vocabulary endpoint serves a cached taxonomy (`engine/biomes.py` `_cache`), so new records only appear in the palette after a server restart. Related: one merged region carries one name (`_region_authored_name`), so distinct named reaches within one continuous `river` biome are impossible until the new biome records exist.
- **B2 — scope regenerate scaling, and the merge flag is UI-only.** First measured as a hang (one core pegged); reproduced offline with stack samples: `compile_grid` progresses through region scan → way blocking → reachability and **terminated in 282.5 s** for the 16k-cell grid (the 53-cell world grid compiles in 1.4 s). Two distinct traps compounded it: (a) the compile itself is minutes-slow at region scale, and queued regenerates hold the WorldPainter write path; (b) regenerating via the API without `"region_merge": true` compiles **unmerged** — ~105k nodes for this grid → rejected by the 20k-node cap (`400 "merge same-biome or generate a smaller scope"`) after the full minutes-long compile. The UI's ⚙ Generate passes its checkbox state; the endpoint body is `{region_merge?, seed?, allow_regenerate?, tick?, entry_area_id?}` — scripts must pass the flag. (With `region_merge: true` a subsequent regenerate returned 200 in ~20 s, so the 282 s cost is first-compile/diff-dependent — unexplained, both measurements real.)
- **B3 — reference ⚦ note.** The Feature-tool placement click never registered under automation (dropdown → 🏠 Feature tool → click cell); the same POST the button issues (`/grid/place`) works. Needs a human-hand check before calling it a UI bug.

## Design boundaries

- Fishing, sleeping, cooking, bathing, and similar processes are **Activities**, not Pursuits.
- A **Pursuit** can lead the character to an area and give them a reason to start an Activity. It is not a forced instruction for an LLM.
- A **Plan** is replaceable when something interrupts the character; the Pursuit can remain.
- A **Schedule** is a calendar cue. Use existing time, sun/moon, seasons, and weather.
- Cooking fish is a separate Activity plus world recipe (task-703), outside the minimum fishing loop.
- No fishing-specific code branch may depend on the character’s name, one area id, or one fish id.
