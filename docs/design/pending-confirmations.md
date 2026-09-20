# Pending confirmations

Decisions and findings from the `static/js` documentation sweep. Each item
records the **decision** and **what was done**. Anything still open is listed at
the bottom.

Created 2026-09-20.

---

## A. Prompt / vitals — resolved

| # | Item | Decision | Status |
|---|---|---|---|
| A1 | Unreachable `Social` tier in `character-state.js` | **Keep the fix** | ✅ done — `SOCIAL_MILD = 65`, the `[social_need: moderate]` cue now fires at 50–65 |
| A2 | `voiceLabel()` ignored the `known` registry | *"if you know someone you know their voice"* → use their name | ✅ done — shared `isKnownToViewer()` now backs both `anonymousName` and `voiceLabel` |
| A3 | `includeMemory` accepted but never wired | Wire it **as optional**, not removed — memories now come at turn *start* | ✅ done — `config.endOfTurnMemory` (Settings → 🧠 End-of-turn Memory), **off by default** |
| A4 | `MEMORY_INSTRUCTION_REACTION` vs `_REACT` drift | Combine them | ✅ done — one `MEMORY_INSTRUCTION_REACT` |
| A5 | Tier numbers hardcoded outside `vital-thresholds.js` | *see explanation below* | ⏳ open |
| A6 | `decide` recomputed `relationshipNL` | *"unification thing"* — but see below | ✅ done differently — it was **dead code**, removed |

### A5 — what it actually means

`agent/vital-thresholds.js` declares itself "the ONE source for vitals tier
boundaries". The *numbers* for Hunger/Thirst/Energy/Sanity/Social/Bladder all
live there. But `character-state.js` still hardcodes other tier numbers inline:

- **Entertainment** prose tiers: `10`, `25`, `50` (lines ~395–398)
- **Sanity** has one stray `< 75` alongside the named tiers
- **Temperature** prose: `33 / 35 / 36` and `38 / 40 / 42` (these are *now*
  band-driven for the species work — see B3 — but the warm-blooded defaults are
  still written inline at the call site)

The risk is drift: change the "bored" threshold in one file and the other file
still uses the old number, so the UI and the prompt disagree.

**Options:** (a) move them into `vital-thresholds.js` (`ENTERTAINMENT_*`,
`SANITY_STRAINED`) and read them in `character-state.js`; (b) accept that
prose-local numbers are fine and fix the file's header to say so.
**My recommendation:** (a) for Entertainment + Sanity (cheap, removes the drift);
(b) is defensible for the temperature prose now that it is band-driven.

### A6 — resolved as "delete the dead code"

`buildObservationPrompt` and `buildDecisionPrompt` are documented dead exports
(never called) in three places — `Agent Engine.md`, `task-160`, and `task-350`,
which states the real turn-start call is `buildReactionPrompt`. Rather than
"unify the calling convention" of code nothing calls, both builders and their
exports were **deleted** (82 lines). `git log` has them if the phase split is
ever revived.

---

## B. Carried over

### B1 — Graph map + layout — partly fixed, still needs your visual pass

Right-click empty canvas → 🗺 Add background image; drag / corner-resize /
top-dot rotate / crop. Resize is scale-about-centre.

**Search was wrecking hand-made layouts — fixed.** Two causes:
1. `focus.js _clusterResults()` called `network.moveNode()` on *every* match,
   ignoring that the node was frozen (`physics: false`). It now excludes frozen
   nodes from the cluster grid.
2. `focus.js _kickClusterPhysics()` switched **global** physics on and ran
   `stabilize(60)` even when physics was off — re-settling the whole layout. It
   now returns immediately when `graphManager._physicsEnabled === false`.

**Node positions now persist to the world.** 🗺 → **💾 Save layout to world**
(and locking) writes every node's `properties.x` / `properties.y` through
`ApiClient.batchGraph` — one atomic request, one undo step. `buildNodeConfig()`
seeds `x`/`y` from those properties on load, so a layout survives reloads,
travels with the scenario file, and can be committed. The browser-local
IndexedDB copy remains as a fallback.

**Backgrounds are per-scenario (fixed).** Two bugs made a map leak between
worlds: the module never reset when a scenario loaded (the previous world's map
stayed on screen), and the IndexedDB fallback keyed unnamed scenarios to one
shared `default` slot. The **world is now authoritative**: every `state:updated`
re-derives the background from the loaded world, and a world with no background
of its own clears the overlay. The IndexedDB fallback is consulted only for a
**named** scenario, and the physics freeze is tracked so a new scenario doesn't
inherit the previous one's locked layout.

**The background map travels with the file too.** It is uploaded as a **file**
(`POST /api/graph/background/image` → `static/images/backgrounds/…`, mirroring
the existing node-image flow) and the scenario keeps only the **path** plus the
transform in a new top-level `graph_background` block — serialized exactly like
`world_lore`. Base64-in-the-JSON was rejected: a 2 MB map would add ~2.7 MB of
text to every commit.

Caveats: positions only *hold* while physics is off/locked, and saving touches
~130 nodes, so the scenario JSON grows slightly and the next Save/Commit
includes them.

**`x`/`y` are excluded from library sync** (done): `handle_library_create_or_update`
strips presentation-only properties via `_strip_presentation_properties`, so a
laid-out world can't leak its coordinates into an archetype. The reverse is safe
by construction — the template-refresh paths build explicit key whitelists, so
they never clear a node's saved position.
`tests/test_library_presentation_keys.py` covers the helper and the route.

### B2 — Scenario name field — ✅ done

The top-left chip already looked editable ("Click to rename scenario") but the
handler only wrote `document.body.dataset.scenarioName` — it **never called the
server**, so the name was cosmetic, vanished on reload, and even fed the
graph-background cache key.

Now:
- **`POST /api/scenario/name`** sets `world._scenario_name` and — when the
  current source has a different basename — **repoints the save target** to
  `data/scenarios/<name>.json`, so a world booted from the boot template commits
  into its own file instead of overwriting `world_template.json`. An existing
  file is **never** clobbered (the previous target is kept and a warning is
  returned). Names are sanitised.
- The click-to-edit handler POSTs the new name, updates the chip, the body
  dataset and `worldState.data._scenario_name`, and **reverts on failure** (the
  server is the source of truth).
- `tests/test_scenario_name.py` (5 tests): name set, target repointed, unsafe
  characters sanitised, existing target untouched, missing name rejected.

### B3 — Cold/hot-blooded species — ✅ engine + prompt/alert done
You asked for **cold-blooded (reptilians)**, **hot-blooded (dragonoids)**, and
**warm-blooded as the default humanoid**.

Done:
- `data/library/traits/cold_blooded.json`, `hot_blooded.json`
  (`effects.temperature_band`); absence ⇒ warm-blooded.
- `engine/traits.py`: `TEMPERATURE_BANDS` + `TraitSystem.get_temperature_band()`
  (a trait may name a band **or** override individual keys).
- `engine/tick_manager.py`: drift, cold/heat damage bands, and death-cause
  attribution all read the band. Warm-blooded defaults reproduce the old
  numbers exactly.
- `character-state.js` (temperature prose) + `ui-controller.js` (the
  "Critical body temp" alert) are band-aware, so **Croak-Mother at 20 °C is no
  longer flagged critical**.
- `Croak-Mother` now carries `cold_blooded`.
- `tests/test_temperature_bands.py` (5 tests).

Still to do: `shared/vital-color.js` bar/percent colours still use the warm
scale (they receive only `vitals`, so they need the band threaded through their
call sites).

### B4 — what it actually means
The scenario file contains **46 character nodes for 23 players**. The extras are
zero-edge orphans (node id equals the display name, e.g. a stray `Arix` beside
the real `player_Arix`), plus a `player_human_explorer` /
`player_player_human_explorer` naming artifact. Two wrinkles make it unsafe to
fix with a text edit:
1. the JSON object **keys don't match the `id` fields**, and
2. there is no `name`/`meta.title` on the scenario (B2).

So the dedupe has to load the file through `WorldGraph`, prove each candidate
has zero edges and no references, and only then remove it — which is why it is
queued as a tool rather than a find-and-replace. Practical effect today: mostly
invisible (orphans have no edges), but it doubles some per-node work and can
surface duplicate names in lists.

---

## Still open

1. **A5** — move Entertainment/Sanity tier numbers into `vital-thresholds.js`.
2. **B1** — your visual pass on the graph map.
3. **B2** — editable scenario name field (top-left).
4. **B3 remainder** — band-aware colours in `shared/vital-color.js`.
