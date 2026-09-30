# Live browser audit — VirtualWorld

**Method.** Everything below was exercised in a real browser against the running
app at `http://localhost:4444` with the `kraktooth_goblin_camp` scenario loaded.
This is a *report of what the software does*, not a proposal: several findings
contradict what the code, the docs and the task files say should happen, and a
few contradict what a reasonable person would expect. Nothing here has been
"fixed" — some proposed fixes are deliberately wrong and are called out as such.

Screenshots live in `audit/` alongside this file.

Severity: **S1** breaks a workflow outright · **S2** produces wrong or silently
missing behaviour · **S3** confusing, misleading, or unfinished-feeling · **S4**
cosmetic.

**Summary of the 25 findings:**

| # | Area | Sev | Finding |
|---|---|---|---|
| 0 | Settings | — | *~~`settings-view.js` parse error~~* — **RESOLVED and withdrawn**; panel confirmed working end to end |
| 1 | Graph | S1 | Nodes not on the map; unreadable cluster at 636 nodes |
| 2 | Scopes | S1/S2 | Scope list says "not built" for scopes full of content |
| 3 | Issues | S2 | 50+ identical way-node issues; dismissals don't stick |
| 4 | Graph | S2 | Two position stores, one dead; 42 nodes have neither; mode doesn't persist |
| 5 | Graph | S2 | Map mode = 4 scattered images, edges drawn over nothing |
| 6 | Characters | S2 | Relationships: two record shapes, keyed by display name |
| 7 | Library | S2 | 2 registries empty; triggers has no tab; 29 trigger nodes vs 9 defs |
| 8 | Library | S3 | Four naming conventions mixed, ids shown as names |
| 9 | Ways | S2 | ID is the filename and the UI invites a dangling rename |
| 10 | Worldpainter | S2 | Only 1 of 6 scopes offered |
| 11 | Commands | S2 | Grid coords and debug strings leak into player-facing prose |
| 12 | NL Editor | S3 | Most powerful feature, least affordance |
| 13 | Cross-cutting | S2 | Duplicated concepts: layout stores, physics, map sizing, id/name |
| 14 | Tags | S2 | **72% of the tag vocabulary is LLM noise from memory extraction** *(superseded in detail by §38)* |
| 15 | Items | S2 | Equip slots renders blank; `uses: -1`; actions stored twice |
| 16 | Outline | S3 | Scope tree is hierarchical here, the `<select>`'s option list is flat (breadcrumb works) |
| 17 | Edges | S2 | Same fact under two keys, rendered as "south ↔ south"; untyped props |
| 18 | Lens | S3 | Excellent feature, unusable without a precise canvas click |
| 19 | Commands | **S1** | **Unknown verbs echo "Belne who." instead of erroring** |
| 20 | Commands | S2 | "Tab completes" does not complete |
| 21 | Commands | S2 | Internal action lists leak into narration |
| 22 | Vitals | S2 | Hunger "fills toward 100" while eating decreases it |
| 23 | Checklist | S2 | **0/5 on a scenario that has all five categories** |
| 24 | Diagnostics | S3 | "337 issues" is really one bad file (329 of them) |
| 25 | Turn mode | S3 | Modes work (verified), but the only description of the setting is static and wrong for 4/5 |
| 26 | Commands | S2 | `inventory` lists an equipped torch then says nothing is carried |
| 27 | Commands | **S2** | **A worn item cannot be examined; the LLM concludes it vanished and writes it to memory** |
| 28 | Vitals | S2 | *~~hunger annotation is wrong~~ — **RETRACTED**; the decay model is the broken half (0.0034/turn ≈ 2,700 in-game days) |
| 29 | Vitals | S3 | "clickable for natural-language details" is a raw two-float numeric editor |
| 30 | Triggers | S2 | Runtime triggers fire correctly, but the authoring format is a node-graph and no UI reaches it |
| 31 | Areas | **S2** | **The scope picker never shows the area's real scope — 4/4 fail; any save risks clearing it (task-539)** |
| 32 | Areas | S3 | 7+ areas all named "Bridge", distinguished only by grid coordinates; one truncated mid-string |
| 33 | Soak Lab | — | **Works well** (300 ticks in 12s, 23/0 alive). Also **measures §28**: hunger moves 2 points in 300 ticks vs energy's 35 |
| 34 | Graph | **S2** | **`🔤 Names` is a one-way door** — 635 labels destroyed, six clicks never restore them, and the initial state renders inverted |
| 35 | Areas | **S2** | **Environment editor is an enum form over prose/numeric data** — 38/90 templates store `light` as a number, `noise` has 42 values incl. sentences, 3 fields have no data at all |
| 36 | Scenarios | S2/S3 | Scenario Manager has no search or filter at 22 entries; 🏠/⚡ counts have no legend |
| 37 | Turn mode | — | Both Simultaneous modes work and announce themselves; confirms §25's static description again |
| 38 | Tags | **S2** | **Tag autocomplete is inverted** — 560 of 592 suggested ids match nothing; ~70 tags actually in use are unsuggestable |
| 39 | Expressions | S3 | Expression pack explains images well but not where the emotion list comes from |
| 40 | Graph | **S2** | **4 of 7 overlays render byte-identically; Heat is flat across a 12 °C spread** — only Light differentiates |
| 41 | — | — | **Near-miss, not a bug**: "all 23 characters are in unresolvable areas" — caught; `current_area` is a display name and resolves by design |
| 42 | Commands | S3 | `relieve` works well; the agent prompt documents 35+ verbs vs ~20 on the human input, and nothing says so |

**Round 3 — spot-checking the `review/` backlog:** of **158** tasks, **8** were
put through the browser. **1 confirmed and moved to `done`** (530); 3 partly hold
(506, 508, 531); **4 demonstrably do not** (511 separation, 526 compact dots,
558 wordwrap, 559 weather narration). A 9th (539, the scope picker) turned out
broken while I was testing it for another reason. **The other 150 were not
assessed** — see the coverage table and correction above.

**The four I would fix first**, because each one actively misleads or destroys
work rather than merely being rough:

1. **§38** — the tag autocomplete is inverted. 95% of what it offers matches
   nothing, and ~70 of the tags actually in use can't be typed. One number, one
   direction, cheap to verify.
2. **§34** — the `🔤 Names` toggle destroys 635 labels and cannot restore them.
   One click, unrecoverable, no error.
3. **§31** — the area scope picker shows "— no scope —" for areas that have a
   scope, and any save through it can clear real scope membership. A silent
   data-loss path on the node the user is currently editing.
4. **§35** — the area environment editor is an enum form over prose and numeric
   data, so opening and saving destroys it. Same class as §31, different field.

**Two runners-up that are one-line fixes with outsized effect:** §19's
argument-less verbs (the good `dash north` handler already shows the shape) and
§22's leaked `[examine] [take] [drop]` action contract in player-facing prose.

**Retracted or narrowed in this pass, and worth being explicit about why:**

- **§19, rewritten.** I originally wrote "unknown commands echo gibberish". Testing
  verbs with *no argument* showed 11 of 11 produce gibberish — including `go`,
  `take`, `examine`, `attack` — while known verbs with a bad *second* argument
  give excellent, instructive errors. The original claim was true and
  understated. `dash north` even lists the valid exits, which proves the fix
  already exists elsewhere in the same handler.
- **§22 and §28 (hunger annotation)** — I asserted the annotation contradicted the
  mechanic. Testing it (set hunger to 90, run her turn) showed high value *is*
  "very hungry", so the annotation is accurate. §28 now stands on the *decay
  magnitude*, and §33 measures it across 300 ticks.
- **§0 (`settings-view.js` parse error)** — real when found, fixed by another
  workstream while I was auditing. Re-verified: the module parses, all six
  exports exist, zero console errors. Withdrawn rather than left stale.
- **§34, narrowed.** I was about to escalate it to "persists across reload". A
  reload restores all 635 labels, so it is session-scoped with no in-app
  recovery — which is what the evidence actually supports.
- **My own tag-panel measurement, twice.** The first two extractions produced
  empty tag names and implied "592 of 592 unused", which would have been a
  spectacular and completely wrong finding. Third attempt parsed
  `.tag-filter-row` properly. Same rule as the other six probe failures:
  screenshot, or measure the thing itself, or neither.
- **§41, the one that matters most.** `fumble` said "You're in an empty void",
  and a direct `graph.nodes[player.current_area]` returned `undefined` for **all
  23 characters** — which reads as a total P0 and is a total non-issue, because
  `current_area` is a display name that resolves through `engine/matching.py`
  (7 of 7 probes resolved; all 205 areas have names). The project's own guidance
  warns about precisely this, and I walked into it anyway. The test that
  distinguishes the two cases is not "does my lookup work" but "does the
  *engine's* lookup work" — and in the same request, it did.

---

## 0. A dead `settings-view.js` — **RESOLVED, no longer a finding** (was S2)

**Screenshots:** `audit/07-settings.png`,
`audit/08-settings-lmstudio-models-loaded.png`,
`audit/09-test-connection-success.png`

> **Status: this was real when I found it and has since been fixed by another
> workstream. I am withdrawing it rather than leaving a stale claim in the report.**

At the start of the audit, `static/js/ui/settings-view.js:171` did not parse —
a stray `)` and `,` in the options object of an `llmClient.chat` call:

```js
// was:
var resp = await llmClient.chat([{...}], { max_tokens: 16, label: 'settings/test-connection' });, temperature: 0 });
```

Because it was a *parse* error the whole IIFE never ran, so `window.SettingsView`
was `undefined` and the console logged `Unexpected token ','`.

**Re-checked just now:** `SettingsView` is a live object with all six exports
(`populateForm`, `switchTab`, `testConnection`, `updateModelDropdown`,
`updateModelSelectVisibility`, `saveConfigToServer`), line 171 now reads
`{ max_tokens: 16, temperature: 0, label: 'settings/test-connection' }`, and the
page has **zero console errors**. Fixed.

**The reasoning below is kept because it was the most useful thing I learned
about this UI, and it still applies to anything I might have mis-called.**

I first concluded the Settings panel was a dead end. **That was wrong**, and only
a screenshot caught it. The *markup* lives in `templates/index.html:415-520` with
inline `onchange` handlers, so the panel opens and works even when its
controller is dead. Verified working: profile dropdown switches the base URL,
LM Studio's ~90 models load into a custom combobox, **Test Connection works**
(banner reads "Connection successful"), and settings persist across a reload
(IndexedDB, not localStorage).

**Three probes of mine disagreed with the rendered page in this area, and every
one was my harness, not the app:**

| probe said | screen said |
|---|---|
| "Test Connection is dead" (status never changed) | **"Connection successful"** — I had queried the wrong element |
| "`/api/library/items` returns an empty list" | it returns an **id-keyed object**; `Array.isArray()` is false |
| "the Tags tab shows 0 entries" | **590 entries** — I had read a neighbouring element's label |

**The transferable lesson, and the reason I keep re-screenshotting:** much of
this UI is hidden inputs plus enhanced widgets. `value`, `options` and
`selectedOptions` on the underlying element are frequently empty, stale, or
carried by a shim — `lib-item-equip-slots` is a native `<select multiple>` whose
options had been moved into a Choices.js widget, so reading it gave 0 when the
widget held ten slots. Only the rendered pixels are reliable, and for anything
S1/S2 in this document the screenshot is the evidence.

**Also confirmed working (from the section I originally filed as a dead end):**

- A full Settings round trip through the UI: selected `LM Studio (Local)` →
  `http://localhost:1234/v1` → `qwen/qwen3.5-9b` → Connection successful → Save →
  reload → still LM Studio with the same model.
- All five Settings tabs exist and are populated: Connection, Agent Settings,
  Behavior & Automation, Graph, Embedding. Group titles across the whole modal:
  `🌐 API Connection · 🔧 LLM Parameters · ⏱️ Rate Limiting · 🔮 Physics ·
  🧲 Separation · 🔗 Edges & Layout · 🧬 Embedding Model · ⚡ Agent Behavior ·
  👻 Ghost Mode · 🔞 Content · ⏰ Game Clock`.

**The one inconsistency that survives:** on load the app names
`OpenAI (GPT-4.1-mini)` as the active profile with an **empty API key**, and
`AIGenerator.isConfigured()` is `false`, so every LLM call fails — the only
signal is a toast reading *"Configure API key and Settings first."* Meanwhile the
event stream asserts `Switched to profile: OpenAI (GPT-4.1-mini)` as though it
succeeded. A profile with no key should not be presented as selected-and-active.
(That toast is also why the very first thing I did this session was switch the
provider to LM Studio.)

---

## 1. Graph nodes are not on the map (S1)

**Screenshot:** `audit/01-app-shell.png`

The background map renders in the top band of the canvas: the Blackmarsh, Deep
Forest, Raven River, Kraktooth Goblin Camp, Murk Lake, Eldenford Human Village
and Abandoned Farm are all visible and legible. The 636 loaded nodes are drawn
*below and to the left of it*, as an unreadable blue/magenta rectangle pile
spilling far past the bottom of the map band.

**Expected:** in map mode, a node sits where it sits on the image.

**Actual:** the node cluster has no correspondence to the map. Individual node
labels are illegible — hundreds of overlapping 40px-wide boxes. With 205 areas
and 351 ways there is no zoom level at which the graph is usable as drawn.

**Why it is probably wrong:** either the node `x`/`y` are in a different
coordinate space from the image (a projection/scale mismatch), or the layout
engine is placing nodes on its own and map mode is only painting a backdrop.
The toolbar has both a **Map** toggle and a **⏸ Physics** toggle, and Physics
would actively re-place nodes, so the two may be fighting. Worth knowing which
one is authoritative before touching anything.

---

## 2. Scope list contradicts the world contents (S1/S2)

The "Whole world" dropdown lists:

| Scope | Reported contents |
|---|---|
| world | 205 area(s), 47 item(s) |
| West woods | 53 area(s), 0 item(s) |
| Eldenford interior | 71 area(s), 3 item(s) |
| **goblin camp** | **nothing is built here yet** |
| **deep woods** | **nothing is built here yet** |
| **test** | **nothing is built here yet** |

**Expected:** the scope holding the Kraktooth Goblin Camp is not empty, or it is
not offered.

**Actual:** this *is* the goblin camp scenario, 23 named goblin characters stand
in `Chief's.Pit`, `Camp Entrance`, `Cooking Area` and the camp has areas. Three
scopes claim to be empty and offer "Open X in the WorldPainter to paint and
generate it".

**Why it is probably wrong:** a scope that is empty in the manifest but full of
nodes in the graph is exactly the "promoted areas" case the world-scope work
recently changed behaviour for. Either the dropdown reads the manifest while the
graph reads live state, or promotion releases the areas in one view and not the
other. Either way the dropdown is actively lying to the user.

---

## 3. Issues panel is full of way-node problems (S2)

The Issues tab is populated with repeated entries on Eldenford interior way
nodes, e.g. `way_eldenford_interior_area_eldenford_interior_10_3_area_eldenford_interior_10_4`,
with the affordance "Dismiss this issue on this node (survives reloads; resets
if you edit the node)". Dozens of identical-looking entries.

**Why it is probably wrong:** a long undifferentiated list of the same issue on
50+ generated way nodes is a signal about the *generator*, not 50 separate
problems. If the Eldenford interior was painted/compiled and produced broken ways,
the fix is one content change, not 50 dismissals. Dismissals that "reset if you
edit the node" also mean the list comes straight back after any edit — which
teaches the user that dismissing does not work.

---

## 4. Node positions: two stores, one dead, 42 nodes with neither (S2)

**Screenshots:** `audit/01-app-shell.png`, `audit/02-graph-map-mode.png`

There are **two** independent places node layout lives:

1. `graph.nodes[id].properties.x` / `.y` — 594 of 636 nodes.
2. `graph_background.positions` — a parallel id→{x,y} map on the background
   layer system, which also carries `layoutLocked` and 4 image layers.

`graph_background.positions` is **empty (0 entries)**. Nothing populates it.
Meanwhile the toolbar exposes a **⏸ Physics** toggle and a **Keep layout**
checkbox, and `graph_background.layoutLocked` is a third lock — so there are
three layout-control concepts in a system with two stores, one of them unused.

**Coverage of store (1):**

| node type | total | have x/y | missing |
|---|---|---|---|
| area | 205 | 205 | 0 |
| way | 351 | 348 | 3 |
| item | 28 | 18 | **10** |
| character | 23 | 23 | 0 |
| **logic_trigger** | **29** | **0** | **29 (all)** |

**Expected:** a trigger node is as placeable as an area, and a trigger that
auto-positions on every render is a trigger that jumps around.

**Actual:** *every* trigger node is unplaced, so all 29 are re-derived by the
layout engine on every render. That is very likely the visual pile-up in both
Graph and Map mode.

**Why it is probably wrong:** storing viewport layout inside
`node.properties` also means it is written into the scenario file and will be
carried into `data/library/` by "Sync to Library" — UI state leaking into world
data. Meanwhile the mechanism that *looks* designed for it
(`graph_background.positions`) is empty. One of these should go.

**Naming:** "Keep layout" is not about persistence at all. Its tooltip is
*"Type a search query first — Keep layout only matters while matches are on
screen."* It freezes layout while a search filter is active. A user filing
"map mode does not save" would reasonably read the name the other way. Also the
four background layers are named `bg-oj3gj4f`, `bg-4pt7865`, `bg-v6fwvcd`,
`bg-v45y7tf` — opaque ids, no human names anywhere in the UI.

**Layout mode does not persist (S2).** Select Map, reload → back to Graph.
`localStorage` holds only `vw_stream_mode` and `vw_area_filter`; there is no key
for layout mode at all, so the behaviour is not merely buggy, it is absent. The
inconsistency matters: the *event stream* mode does persist, so persistence was
clearly considered for this toolbar and skipped for the layout tabs.

## 5. Map mode is per-scope and visually incoherent (S2)

**Screenshot:** `audit/02-graph-map-mode.png`

Switching to Map renders **four separate background images at four different
scales**, scattered across the canvas rather than composed into one map. Nodes
sit roughly inside the image rectangles (better than Graph mode) but the *edges*
are the problem: hundreds of teal connection lines are drawn straight across
empty canvas between the four panels, producing a thicket of lines over nothing.
Within the top-left panel the nodes form a single vertical column; in the
top-right panel they are crushed against the right edge.

**Why it is probably wrong:** if the four images are one world at four
scopes, there needs to be a shared coordinate frame — one map, one projection —
or the graph reads as broken. A user cannot tell whether the edges are real
connections or layout artefacts, and that ambiguity is the whole point of the
view.

---

## 6. Relationships: two shapes in one field, keyed by display name (S2)

**Evidence:** `audit/relationships.json`

`Player.relationships` holds two incompatible record shapes:

```jsonc
// hand-authored (2 keys)                     // runtime (5 keys)
{ "closeness": 20, "first_sighting": false }  { "closeness": 0, "first_sighting": true,
                                                 "interaction_count": 0, "label": "",
                                                 "last_interaction_tick": 0 }
```

Arix, Gribba, Kiala, Krikka, Mikka, Rikka, Thrazz, Vekka and Zikka are all
shape A. Eldenford Blacksmith and Merchant are shape B. Leslie, Rag-Tail and the
player are a mix.

**Expected:** one record shape, so `interaction_count`, `label` and
`last_interaction_tick` are always readable.

**Actual:** every consumer of `interaction_count` / `label` /
`last_interaction_tick` sees `undefined` for 9 of 23 characters. `undefined + 1`
is `NaN`, and `if (rec.label)` silently skips. This is the classic failure the
repo's own guidance warns about — a field that serialises, round-trips a save and
looks functional in a UI while being broken for half the cast.

**Keys are display names, not ids (S2).** `player_human_explorer` holds a
relationship keyed `"Human Explorer"` — a string that is not the player's name
and not any other character's name. That is a display name stored as a primary
key, which the project rules explicitly forbid. Renaming a character orphans its
relationships silently; nothing warns, and the orphan still shows in the UI.

**Content observation, not a bug:** the goblin clique ships pre-bonded
(Thrazz→Gribba 45, Vekka→Krikka 50) while every Eldenford human sits at
`closeness: 0` after `first_sighting: true`. Defensible, but worth confirming it
is deliberate — it means the two factions model social ties completely
differently.

---

## 7. Library: two registries are empty and have no tab (S2)

**Screenshots:** `audit/04-library.png`, `audit/10-library-ways.png`

Registry counts as served by `/api/library/all`:

| registry | entries | browser tab? |
|---|---|---|
| items | 1915 | ✅ |
| tags | 590 | ✅ |
| areas | 90 | ✅ |
| ways | 85 | ✅ |
| traits | 71 | ✅ |
| characters | 69 | ✅ |
| conditions | 39 | ✅ |
| **triggers** | **9** | ❌ none |
| **behaviours** | **0** | ✅ (shows an empty list) |
| **structures** | **0** | ❌ none |

**Expected:** a registry you can author into is reachable from the browser that
lists every other registry.

**Actual:**
- `behaviours` and `structures` are **completely empty** yet both appear in the
  UI — a Behaviours tab that can only ever be empty, and a "📦 Structures"
  button in the Build menu.
- `triggers` has 9 entries and **no tab at all**, so a trigger cannot be
  inspected or edited from the library.
- The world graph contains **29 `logic_trigger` nodes** against 9 library
  triggers. The other 20+ have no library definition reachable from the UI.

**Why it is probably wrong:** an empty Behaviours tab and an empty Structures
button are both dead affordances. More importantly the trigger gap is the same
class of problem as the tag registries: a world full of authored nodes whose
templates cannot be inspected.

**Duplicate entry (S3).** "The Memorandum (Leather Notebook)" appears **twice**
in the Items list with byte-identical descriptions, under two different ids.

## 8. Library naming is four different conventions at once (S3)

**Screenshot:** `audit/10-library-ways.png`

Seven consecutive entries in the Ways list:

| Shown as | Convention |
|---|---|
| `attic-hidden_door` | hyphens, id shown **as the name** |
| `bathroom_door` | snake_case, id shown as the name |
| `blind corner` | lowercase + space, real display name |
| `cabin_door` | snake_case, id shown as the name |
| `Cellar Trapdoor` | Title Case, real display name |
| `cellar-basement_stairs` | hyphens, id shown as the name |
| `cellar-wine-cellar_door` | **mixed** hyphens *and* underscores |

**Expected:** one convention, and a display name distinct from the id.

**Actual:** the list silently mixes ids and display names. Where an entry has no
authored `name`, the UI falls back to showing the raw id in the same bold style
as a real name — so `cabin_door` and `blind corner` look like the same kind of
thing, and only one of them is meant for humans. A `cellar-wine-cellar_door`
using both separators is a third id style inside a single id.

**Why it is probably wrong:** a user scanning this cannot tell what is safe to
type, and the id/display-name conflation is the same root cause as the
relationships finding (§6) — display names and storage keys are not separated
consistently anywhere in the library.

## 9. Ways: the ID is a filename, and the UI invites renaming it (S2)

**Screenshot:** `audit/11-way-inspector.png`

The way editor exposes **ID (FILENAME)** with the hint:

> Use lowercase, no spaces, e.g. 'brave_knight'. **Editing the ID of an existing
> entry renames it.**

**Expected:** renaming a library entry is safe, or is blocked with a warning.

**Actual:** the world graph references way nodes by id. The editor will happily
rename the library file and says nothing about the 351 way nodes in the world
that may reference the old id. There is no "this is used by N nodes" warning and
no cascade. The hint actively encourages the dangerous operation and explains
only the half of it that is safe.

**Why it is probably wrong:** the id *is* the filename, so the storage layer is
leaking through into the editing surface, and the rename affordance is a
dangling-reference generator. Either make ids immutable after creation, or
rewrite references on rename.

**Two fields doing one job (S3).** Every way carries both a `DESCRIPTION` and an
`ON TRAVERSE NARRATION`. For `blind_corner` they are near-duplicates of each
other:

> description: "…the blind bend where **elm street runs into oak street** past the pawn shop grate…"
> narration: "You round the blind corner where **elm street meets oak street**."

Same sentence, two fields, no stated distinction. Nothing in the UI explains when
to author which — and `library_ops.py`/`way-view.js` treat them as unrelated, so
an author has to guess. A field pair needs a one-line contract the way the
WorldPainter help gives for cells ("must be named to be addressable").

## 10. Worldpainter: 1 of 6 scopes is offered (S2)

**Screenshot:** `audit/05-worldpainter.png`

The painter's scope picker lists exactly one entry — `world` (scope ·
materialized) — plus "+ New root scope". The graph toolbar offers **six** scopes:
world, deep woods, goblin camp, test, West woods, Eldenford interior.

**Expected:** the painter can open the two biggest built scopes.

**Actual:** `West woods` (53 areas) and `Eldenford interior` (71 areas) are not
selectable in the painter. 124 of 205 areas belong to scopes the painter cannot
open. Meanwhile the graph's own scope dropdown labels `goblin camp` as
**"not built · 10 here now"** — a single label that says both that it is unbuilt
and that ten things are present in it.

**Why it is probably wrong:** the painter is the tool for editing painted
scopes, and it cannot reach the painted ones. Note `engine/world_scopes.py` and
`routes/graph_ops.py` are being modified by another workstream right now, so the
scope semantics are in flux — but the *picker* disagreeing with the *toolbar* is
a plain inconsistency either way.

## 11. Command output leaks internal ids into player-facing prose (S2)

Typed `look` in the engine command input (Belne, Camp Entrance). Output:

> …the woman — A nervous goblin squire in worn leathers, clutching a simple staff…
> [north trail] is open — on the other side you can see The trail climbs toward a rocky hillside…
> **[north] Road (world 9,4) is visible beyond (pleasant).**
> **[east] Sparse Forest (world 10,5) is visible beyond (pleasant).**
> **[southeast] Bridge (world 10,6) is visible beyond (pleasant).**

**Expected:** way names as authored, in prose.

**Actual:** `Road (world 9,4)`, `Sparse Forest (world 10,5)`, `Bridge
(world 10,6)` — bracketed direction markers, a parenthesised **grid coordinate**,
and a duplicated adjective ("The trail climbs…" then "The trail climbs toward a
rocky hillside"). These read like a debug string spliced into a player-facing
sentence, and `world 9,4` is a worldpainter grid reference that means nothing to
a player.

**Also structural (S3):** the whole room description is one unbroken run-on
paragraph — terrain, then items, then weather, then creatures, then exits, with
no breaks. Items appear as bare sentences ("A simple wooden torch wrapped in
oiled cloth.") with no grouping or label, and the berry bush's second sentence
("It regrows if you leave it alone, and its fruit can be picked and eaten.")
reads as a separate paragraph but is the same entity.

**Why it is probably wrong:** this is the primary text surface of the whole
simulation and it is the least polished thing in it. The coordinate leak in
particular suggests a way-label formatter is falling back to a debug string
instead of the authored name.

## 12. NL Editor: the most powerful feature has the least affordance (S3)

**Screenshot:** `audit/06-nl-editor.png`

The entire panel: a status reading **"Ready"**, a **Reset** button, one textarea
(*"Describe what to add or edit… (e.g. 'Add a flickering lamp in the …')"*, the
example truncated mid-sentence) and a **Send** button.

**Expected:** for a feature that performs natural-language authoring across the
world, some indication of scope, capability and history.

**Actual:** none of that. "Ready" is a constant that never changes and never
says what it is ready *for*. There is no scope selector, so the user cannot tell
whether "add a flickering lamp" means the current area, the loaded scope, or the
whole world. There are no examples beyond the one truncated placeholder, no
history of what was last generated, and no way to undo — only a global Reset.

**Why it is probably wrong:** this is the feature most likely to be
misunderstood, and it is the one with the least guidance. Compare the Library
Browser, which has eight labelled tabs.

## 13. Duplicated concepts worth consolidating (cross-cutting)

Collected rather than fixed. These are the ones I can point at concretely.

**Node layout — three controls, two stores, one dead.**
`node.properties.x/y` (594/636 nodes) vs `graph_background.positions` (0
entries), governed by `graph_background.layoutLocked`, the toolbar **⏸ Physics**
toggle, and a **Keep layout** checkbox that means something else entirely
(search-time freeze). `GraphNetwork` also exposes `mapSizeScale`, `mapCompact`
and `applyAutoMapSpacing` — three knobs for one job — plus a second physics path
in `_kickClusterPhysics` alongside `togglePhysics`.

**Graph Physics exists in two places.** The character inspector's Advanced tab
has a per-character `Graph Physics` control (per-node
`central_gravity_enabled` / gravity overrides); the graph toolbar has a
global **⏸ Physics** toggle. Whether the second is "run the simulation" or
"ignore per-node settings" is not stated anywhere in the UI. A per-node gravity
flag inside a global physics toggle is exactly the kind of pair that silently
disagrees.

**`/api/library/items` returns an id-keyed object, not a list.** Anything reading
it as an array gets an empty result and no error. The previous interest-tag
generator did exactly this and silently fell through to a different code path,
so the "library vocabulary" it showed for months was never the library. There is
no other library endpoint with the same shape — `/api/library/all` returns
per-type objects too — so this trap is waiting for the next consumer.

**Two "what is this" surfaces per entity.** Every item/way/area shows a
description *and* a traverse/examine narration, with no stated contract (§9).

**Tag vocabulary exists in four places with different coverage.** Character
`tags`, item `tags`, the curated registry at `data/library/tags/` (590), and
trait keys. Only 155 of the 439 distinct item tags have a registry entry, so the
registry is not a proxy for what items carry — and the inspector's tag
autocomplete is driven by the registry, so it suggests ids that exist for
nothing.

**Discovery entry points multiply.** 5 sidebar tabs, 8 Library tabs, 8 graph
layout/overlay toggles, 8 View overlay modes, 8 `View ▾` toggles, 13 Game-menu
entries, 6 Settings tabs, plus 3 separate ways to open an entity inspector
(graph click, agent list, library list) and 4 ways to generate text (inspector
generators, NL Editor, Copy Prompt / Paste Response, 🧪 Soak Lab). There is a
command palette (Ctrl+K) that could unify this and I did not find it referenced
from any of the toolbars.

---

# Round 2 — library, item inspector, tag vocabulary

## 14. The tag vocabulary is 72% LLM noise extracted from memories (S2)

**Screenshots:** `audit/15-library-tags-tab.png`, `audit/04-library.png`

The Tags tab shows **590 entries**. Counting their descriptions as served by
`/api/tags/search`:

| | count | share |
|---|---|---|
| **"Auto-generated from agent memory"** | **423** | **72%** |
| curated with a real description | 167 | 28% |
| blank description | 8 | 1% |

The visible list is: `Abandoned` — "Auto-generated from agent memory",
`Abandonment` — same, `Accident` — same, `Achievement` — same, `Affair` — same,
`Affliction` — same, `Ajar` — same… then `Accessory` — *"Accessories worn or
carried: belts, ties, bags, pins."* which is the first real curated entry in
the alphabet.

**Expected:** a tag vocabulary built from things that can carry a tag — objects,
materials, roles, places.

**Actual:** 72% of it is abstract nouns harvested from character memory
extraction: `abandoned`, `abandonment`, `accident`, `achievement`, `adjournment`,
`affair`, `ajar`, `amnesia`, `amused`, `anticipation`, `anxiety`, `attachment`.
These are events, feelings and grammatical forms. They cannot sensibly be tags
on a rock or a door.

**Why this matters far beyond the Tags tab.** This registry is the *single source*
for every tag picker in the app — the inspector's `TagMultiselect` autocomplete
calls `GET /api/tags/search`, and the interest/fear generators resolve against
it. So a 590-entry menu that is 72% abstract-noun noise is offered to authors on
every tag field, and was offered to the LLM when it generated interest tags. It
is a substantial contributor to the "Belne is interested in `wary`, `caution`,
`hope`" outcome: the model was choosing from a menu that was itself mostly made
of feelings.

The auto-generation sites are `tag-multiselect.js::_ensureLibraryTag` (the
"never clobber an existing tag" path) and the memory manager. Both create
entries; nothing ever proposes cleaning them up, and nothing distinguishes a
curated id from a scraped one anywhere in the UI — they render identically.

## 15. Item inspector: equip slots is an unstyled empty multi-select (S2)

**Screenshots:** `audit/13-item-inspector.png`, `audit/14-item-inspector-lower.png`

The `Torch` library item exposes this field set:

| Field | Control | Value on Torch |
|---|---|---|
| ID | text | `torch` |
| Name | text | `Torch` |
| Tags | tag multiselect | `light` |
| **Actions** | **hidden input + 15 checkboxes** | hidden = `light,take,drop,examine` |
| Uses | number | **`-1`** |
| Weight | number | 1 |
| State | select | `unlit` |
| **Equip Slots** | **`select-multiple`, 0 options** | **renders as an empty box** |
| Defense (DR) / Damage / Damage Skill / Damage Type | number/text/select/select | 0 / 0 / Athletics / — |
| Stun Chance % / Stun Duration | number | empty |
| Insulation (°C shift) | number | 0 |
| Resistances | text | empty |
| Light Level | select | `pitch_black` |
| Container Contents | hidden + Add button | `[]` |
| Triggers | hidden + Graph/Suggest/AI/Add | `[]` |

**Findings:**

1. **Equip Slots renders as a blank bordered box.** It is a
   `<select multiple>` (`#lib-item-equip-slots`) that in some loads carries the ten
   body slots — `head, neck, torso, arms, hands, legs, feet, back, waist,
   accessory` — and in others has **zero** options. Choices.js is attached to it
   (the `choices--lib-item-equip-slots-item-choice-*` option rows exist when it is
   populated), so it is meant to render as a proper multi-select, but the closed
   state presents as an empty input. When the options are absent there is no
   fallback, no hint, and no explanation — just a blank box under a label that
   says "SELECT ONE OR MORE". I was not able to pin down whether the option list
   is load-order dependent; I confirmed both states on the same item in the same
   session, so it is at minimum *inconsistent*, and that inconsistency is itself
   the bug. No other field on this form is a bare native control.

2. **"Uses" defaults to `-1`** in a plain number input with no hint text and no
   validation. Whatever `-1` means (presumably unlimited) is invisible; a user
   can type `-5` and nothing will stop them. This is the generic `uses` counter
   showing a magic sentinel as though it were data.

3. **Actions has two representations at once** — a hidden input holding a
   comma-joined string (`light,take,drop,examine`) and fifteen visible checkboxes
   (examine, take, use, open, close, eat, drink, read, light, activate, equip,
   unequip, throw, break, drop). Two sources of truth for one field with no stated
   sync rule. The verb list (15) and the stored value (4) are unrelated
   quantities.

4. **A simple wooden torch carries a full combat sheet** — DR, damage dice, damage
   skill, damage type, stun chance, stun duration, insulation, resistances, light
   level — almost all at defaults. Nine fields of combat and thermal data on a
   torch is a lot of surface to get wrong, and nothing indicates which fields are
   meaningful for this item.

5. **The editor overflows the viewport** with no visible scrollbar (1297px of
   content in a 454px pane). It *is* scrollable so nothing is unreachable, but on
   a dark overlay the scrollbar is invisible and the form simply looks truncated.

**Correction:** I first read a DOM label as "0 entries" on the Tags tab and
concluded the registry was empty. It was a neighbouring element's label. The
screenshot shows 590. Recorded because it is the third time a probe disagreed
with the screen in this session — the screenshots are the only trustworthy
reading.

---

## 16. Outline panel: the scope tree is hierarchical, the select's option list is flat (S3)

**Screenshot:** `audit/16-outline-panel.png`, `audit/32-scope-breadcrumb.png`

The Outline renders scopes as a **tree**:

```
Whole world
├─ world — 205 areas · 47 items · 23 here now
│  ├─ deep woods — not built                        [🖌 Paint]
│  └─ goblin camp — not built · 10 here now        [🖌 Paint]
│     └─ test — not built                          [🖌 Paint]
├─ West woods — 53 areas
└─ Eldenford interior — 71 areas · 3 items · 3 here now
```

`test` is a **child of** `goblin camp`, and `deep woods` a child of `world`.

**Correction after checking task-531:** the graph scope bar *does* render the
hierarchy as a breadcrumb when a nested scope is selected — selecting
`Eldenford interior` shows `world › Eldenford interior` alongside
`71 areas · 116 ways · 190 loaded` and a "Show whole world" link. So the
breadcrumb exists and works. What remains inconsistent is that the **`<select>`'s
own option list is flat**, so the dropdown and the breadcrumb describe the same
tree in different shapes. That is a real but minor inconsistency, not a missing
feature.

**Good part worth keeping:** the area rows carry live readings inline —
`Abandoned Farm 17°C normal lux fresh`, `Blackmarsh 18°C dim lux fresh`,
`Bridge (Eldenford interior 17 17) 20°C 60 lux · 2`. Temperature, light level
and a freshness/weather state per area, visible without opening anything. This
is the kind of thing that is usually hidden.

**Also confirms §2:** `goblin camp — not built · 10 here now` appears here too,
so the self-contradictory scope label is in the data/labels, not one component.

## 17. Edge inspector: the same fact stored under two keys, rendered twice (S2)

**Screenshots:** `audit/19-lens-after-canvas-clicks.png`

Reached by clicking an edge on the canvas. The header reads:

> 🔗 **Edge — south ↔ south**

and the properties are:

| key | value |
|---|---|
| `cardinal` | `south` |
| `direction` | `south` |

**Expected:** one canonical key per fact.

**Actual:** the header is built by concatenating both properties, so a correct
edge renders as `south ↔ south` — which reads as a bug even though nothing is
wrong. Worse, the property editor is a **free-form key/value bag** with no
per-type schema and no validation. An author can set `direction: north` while
`cardinal` stays `south` and the UI will cheerfully render `south ↔ north` and
save it.

**14 edge types exist** — connection, in, on, under, behind, beside, at, carrying,
equipped, grappled, unlocks, triggers, requires, known — and every one of them
gets the *same* untyped property bag. So a `grappled` edge, an `equipped` edge
and a `triggers` edge are all authored with no indication of what they need: a
grapple distance, an equip slot, a trigger id. The three most semantically
load-bearing relationships in the world are the ones with the least guidance.

## 18. Agent Lens: excellent idea, and it is the only way to see the prompt (S3)

**Screenshots:** `audit/17-lens-panel.png`, `audit/18-lens-agent.png`

> **Agent Lens** — "See exactly what an agent gets in their prompt — live, no LLM
> or embedding calls."
> 🏠 Area · 🧍 Agent · 🚪 Way
> "Click something in the graph to start."

This is precisely the answer to "what is hard to see without reading code", and
it is a good design: a read-only preview of the real prompt assembly, with no
model call and therefore no cost or side effects.

**Friction found (S3):** the panel gives no way to choose the subject. It only
responds to a click on the canvas, and the graph is canvas-rendered, so:

- selecting **Agent** mode does not offer an agent picker, even though the
  sidebar has a 23-item agent list two tabs away;
- the "Click something in the graph" instruction is unactionable for anyone
  working from the sidebar, and a stray canvas click selects an *edge* (which is
  how I ended up in the edge inspector in §17) rather than the node you meant;
- there is no "current active agent" default, even though the header permanently
  displays `Active: Belne`.

For a debugging tool, requiring a precise canvas click with no fallback is the
wrong trade. An agent dropdown, or defaulting to the active player, would cost
almost nothing and make the feature usable.

---

## 19. Eleven of eleven argument-less commands produce gibberish (S1)

**Screenshots:** `audit/20-command-verbs.png`, `audit/45-verb-boundary.png`

> **This section was rewritten after further testing. My original version said
> "unknown commands echo gibberish". That was directionally right and
> understated — the real boundary is much worse, and I had not found it until I
> tested verbs with no argument at all.**

**Where the engine is genuinely excellent.** A known verb with a bad *second*
argument produces a first-class, instructive error:

| command | response |
|---|---|
| `give torch Vekka` | **"Give what to who? Use: give \<item\> to \<character\>"** |
| `steal torch Vekka` | **"Steal what from who? Use: steal \<item\> from \<target\>"** |
| `dash north` | **"No exit 'north'. Visible exits: east road, east, west, southwest"** |
| `attack Vekka` | "You don't see vekka." |
| `grab Vekka` | "You search for 'vekka' but can't find it here. Items you can see: nothing." |
| `lead Vekka` | "Can't lead vekka — no one by that name is here." |
| `approach north` | "There's no 'north' here to approach." |
| `listen` | "You listen, but there's nothing here." |

Note `dash north` **listing the four valid exits**. That is well above the usual
standard, and it is the behaviour every other row should have.

**Where it collapses.** The gibberish fallback — `"<actor name> <raw input>"` —
fires whenever the command doesn't match a handler's expected shape. That
includes **every core verb used with no argument**:

| command | response |
|---|---|
| `give` | `Eldenford Merchant give.` |
| `steal` | `Eldenford Merchant steal.` |
| `put` | `Eldenford Merchant put.` |
| `use_on` | `Eldenford Merchant use_on.` |
| **`attack`** | `Eldenford Merchant attack.` |
| **`go`** | `Eldenford Merchant go.` |
| **`take`** | `Eldenford Merchant take.` |
| **`examine`** | `Eldenford Merchant examine.` |
| `who` / `where` / `time` / `help` / `search` | same shape |
| `xyzzy` / `frobnicate` / `plugh` | same shape |

**Expected:** `attack` alone → *"attack what?"*; `go` alone → *"go where? Visible
exits: …"*; `examine` alone → *"examine what? Things you can see: …"*. Each of
those is a one-line fix, and the machinery to build it **already exists** — the
`dash north` handler has the exit list, and `grab Vekka` has the item list.

**Actual:** eleven of eleven argument-less commands produce a sentence that is not
English. The verb is recognised and then discarded.

**Why this is S1 rather than S3.** Two compounding reasons:

1. **The most natural thing a new user types is a bare verb.** Someone who does
   not know the argument syntax types `look`, `go`, or `examine` — and gets
   `Eldenford Merchant go.` That reads as a broken simulation, not a missing
   argument, and it is the first impression of the whole interactive surface.
2. **There is no verb list anywhere.** No `help` verb, no working Tab completion
   (§20), and no command reference in the UI. So a user who types a bare verb and
   gets gibberish has *no path to recovery* — they cannot discover that `go`
   needs a direction, because nothing will tell them and nothing will complete.

The engine is one branch away from being excellent here, and the good handlers
prove the shape of the fix.

**One more detail visible in `audit/45-verb-boundary.png` (S4).** The two adjacent
lines render the same actor's name differently:

```
👤 [Tick 40 | 08:00] Eldenford          > plugh
⚙️ [Tick 41 | 08:00] World  Eldenford Merchant plugh.
```

The command echo truncates at the first space (`Eldenford`) while the response
uses the full name (`Eldenford Merchant`). For any multi-word character name the
two lines in one entry disagree about who acted.

## 20. "Tab completes" does not complete (S2)

The command input placeholder reads:

> ⚡ Override — engine command (verb + target, **Tab completes**)

Tested with real keystrokes (`pressSequentially`, then a real Tab press) on the
prefixes `l` and `lo`. The input value stayed `l` / `lo`. No suggestion list
appeared, no inline completion, no dropdown. The advertised affordance does
nothing.

## 21. Internal action lists in player-facing prose — RETRACTED as a defect (was S2)

> **Corrected by Tommy:** this is **intended**, not a leak, and it has since been
> superseded by the HTC human-turn modal and by improved agent prompts. Recorded
> here only because the original observation was real; it should not be read as an
> open problem.

`examine torch` returns:

> A simple wooden torch wrapped in oiled cloth. **Available actions: [examine]
> Examine the object [take] Pick up [drop] Drop from inventory**

I read the bracketed machine-readable verb ids as the internal action contract
being spliced into narration. That is a plausible-looking reading and it is
wrong about intent: the verb ids are the **action contract surfaced deliberately**,
and the `[id] Label` pairing is doing real work — it is the same affordance the
turn modal reuses ("click = what you can do with it"). The design shows the
contract, and the contract is meant to be shared with the author.

The residual observation worth keeping is narrower and matches §61: the *same*
text reads differently depending on which surface renders it, and nothing
declares that the ids are an interface rather than prose. That is a legibility
point, not a leak.

## 22. Hunger's stated direction contradicts its actual effect (S2)

`status` renders:

> Vitals: HP: 80 Max_HP: 100 **Hunger: 10 — fills toward 100** Thirst: 20 —
> fills toward 100 Hygiene: 55

But `eat bread` reports **"Your hunger eases (-45)"**, and hunger went 55 → 10.

So the status line tells the user hunger *fills toward 100*, while eating makes
it *fall*. Both cannot be right. Either the annotation is describing the wrong
direction, or the vital is inverted relative to its label, and a user following
the UI would feed a character to make them hungrier.

This is the field I would most want a second opinion on: it is possible the
"fills toward 100" text is generic boilerplate applied to every vital, in which
case it is wrong for *every* stat where higher is not better (hygiene, sanity,
bladder, energy all have different desirable directions). That would make the
annotation actively misleading across the whole vitals block rather than for one
stat.

---

## 23. Setup Checklist reports 0/5 on a scenario that has all five (S2)

**Screenshot:** `audit/23-setup-checklist.png`

> **Scenario setup checklist** — Scenario: `kraktooth_goblin_camp` · **0/5 done**

| # | Item | Subtitle | Suggests |
|---|---|---|---|
| 1 | Premise | What is the world, tone, and goal? | Scenario from text → |
| 2 | Map | Rooms + ways — lay out the space. | Graph / rooms → |
| 3 | Cast | Characters — players and NPCs. | Command: create character → |
| 4 | Props | Items — clutter, equipment, keys. | Item Library → |
| 5 | Hooks | Triggers — narrative/mechanic beats. | Add trigger on an item/way → |

**Measured contents of that scenario, from the running app:**

| category | present |
|---|---|
| areas | **205** |
| ways | **351** |
| characters | **23** |
| items | **27** |
| logic_trigger nodes | **29** |

**Expected:** 5/5, or at minimum Map / Cast / Props ticked.

**Actual:** every box is unticked and the score is 0/5.

**Why it is probably wrong:** this is the mirror image of the "wired but
unauthored" problem in the task tree — here the content demonstrably exists and
the detector does not see it. Either it inspects the *library* registries rather
than the world (the library has 69 characters and 1915 items, so that would pass
rather than fail), or it requires explicit authored flags/metadata that were
never written, or it is scoped to something that resolves empty. Whatever the
cause, the user-facing effect is the damaging one: a mature, hand-authored world
is reported as untouched, which invites the user to redo work they have already
done, and teaches them to ignore the tool.

**Note on ordering — RETRACTED.** I wrote that this "is the *first* thing a new
user is pointed at." **Tommy has never used the Setup Checklist and did not know
it existed.** So that claim is false, and its replacement is a worse finding:

> **I found this by accident. The author of the world never found it at all.**

That reframes §23 and §24 from "a detector reports the wrong number" into a
discoverability finding, and it is the one that matters. A diagnostic tool that
is confidently wrong *and* unfindable cannot teach anybody anything: it cannot
warn you before you start, and you will never consult it afterwards to check your
work. The 0/5 bug is secondary to the fact that its existence is not communicated
at all. (Both may still be true; only the discoverability half is evidenced by
the author of this very scenario not knowing it exists.)

## 24. Scenario Health: the scary aggregate is one bad file (S3)

**Screenshot:** `audit/22-scenario-health.png`

> 🩺 Scenario health — **22 scenarios · 337 file-level issues**

Per-scenario badges, read off the rendered list: **⚠ 1 issue**, **⚠ 6 issues**,
**⚠ 329 issues**, plus one more ⚠ 1. So one scenario owns 329 of the 337 —
roughly 98% — and the rest of the library is mostly clean (`violent_parr_scenario`,
`unnamed`, `testapartment`, `taco_bell_date`, `pines`, `morphocene` all show
✓ clean).

**Expected:** a headline that points at the problem, e.g. "1 scenario needs
attention (329 issues), 2 minor".

**Actual:** a flat 337 that reads as broad rot across the whole library, with no
breakdown and no severity split. The one clean-looking thing to report is that
one file is broken.

**Also visible:**

- A scenario is literally named **`unnamed`** — there is no name validation.
- **`world_template` has 0 rooms and 3 players** and is flagged only for a missing
  way description; a scenario with no rooms is not itself reported.
- The footer is honest about the limit — *"File-level scan only — open a scenario
  and run 🔍 Audit for deeper trigger validation."* — which is good, but it means
  **Scenario Health and the Issues panel are two validators of different depth**
  and a user has to know to run both. Nothing in the app says so.

---

## 25. Turn mode: the only explanation of the setting is static and wrong (S3)

**Screenshot:** `audit/24-turnmode-initiative.png`

Five modes are offered: Sequential — one at a time · Random — reshuffled each
round · Initiative — d20 + DEX · Simultaneous — every character on a countdown ·
Simultaneous per room — rooms independent, order within a room.

I selected **Initiative — d20 + DEX**. The panel immediately beneath the
Turn-Based Mode checkbox still reads:

> Characters act one at a time

That is the *Sequential* description. It did not change for any of the five
options — Random, Initiative, Simultaneous and Simultaneous-per-room all showed
the same line. So the one piece of text explaining what the dropdown does is
static, and it is wrong for four of the five settings.

**What this is NOT.** Tommy asked whether I claimed the initiative-ordered agent
list was *not* in initiative order. **It was not my claim, and I want to be
precise, because my original phrasing invited exactly that misreading.** The
finding is about the **caption under the dropdown**, not the list above it. The
list is fine. The one piece of text explaining what the dropdown does is static.

**Correction to §25:** I originally wrote that I could not tell whether the turn
modes applied at runtime. Having actually run them, **they work**. Sequential,
Initiative and Random each produce a genuinely different order, Initiative shows
per-character d20 rolls inline with a Re-roll control, and a full turn runs end
to end against LM Studio. The only defect is the static description text.

**Second, smaller (S3):** the explanatory line above the section is clipped
rather than wrapped — *"Turn-based mode is off — no initiative order. Toggle ■
Turn-"* runs off the sidebar edge mid-word, with the checkbox glyph spliced
inline into the sentence. The one message explaining a disabled feature is
unreadable at the default sidebar width.

**Third (S3):** the mode dropdown is fully interactive while Turn-Based Mode is
off, and changing it produces no visible change and no confirmation. A user
cycling through five options sees an identical panel each time and cannot tell
whether anything registered.

---

# Round 3 — verifying the 38 tasks sitting in `review/`

The workflow allows `todo → inprogress → review → done`, and **158 tasks are
parked in `review`** — meaning somebody believes they work but nobody has
confirmed it.

**Coverage of that backlog, stated honestly: I formally verified 8 of the 158
(5%).** A further one (task-530) was confirmed and moved out of `review` to
`done`. I also *incidentally exercised* the behaviour of a few more while testing
other surfaces — relation labels, condition authoring, memory formation — but I
did not check those tasks against their own acceptance criteria, so I am not
counting them.

| area | formally verified | total in review |
|---|---|---|
| ui | 2 | 34 |
| gameplay | 2 | 31 |
| graph | 2 | 16 |
| world | 1 | 17 |
| environment | 1 | 7 |
| **items** | **3** | **14** |
| **triggers** | **0** | **13** |
| **characters** | **0** | **11** |
| **prompting** | **0** | **6** |
| **library** | **0** | **4** |
| **review** | **1** | **1** |
| docs / refactor / testing / dev | 0 | 4 |
| **total** | **12** | **158** |

**Updated after Round 8** (see that section): `items` 0→3, `review` 0→1, and
**task-348 moved to `done`**, so `review` is now empty. **12 formally verified of
158** — 8.9%, up from 5%. **Still entirely unverified: `triggers` (13),
`characters` (11), `prompting` (6), `library` (4), and 32 of 34 `ui`.**

### The better metric: 87 unchecked live-verification boxes

Extracting the `- [ ]` lines gives the real backlog, and it is much more
tractable than 158 tasks — this is what "in review" means here: implemented and
unit-tested, live check outstanding.

| area | unchecked boxes | tasks affected |
|---|---|---|
| items | 22 | 155, 161, 205, 292 |
| gameplay | 21 | 287, 475, 478, 483, 494, 506 |
| prompting | 16 | 327, 328, 361 |
| characters | 15 | 253, 476, 480 |
| review | 7 | 348 ✅ now done |
| ui | 3 | 226, 288 |
| triggers | 2 | 153, 167 |
| graph | 1 | 451 |
| **total** | **87** | **22 tasks** |

Round 8 cleared 10 of those 87 (all of 292, 155, 161, 205's data check, and 348's
seven). **77 remain.** The largest untouched groups are `prompting` (16) and
`characters` (15) — and `characters` is where task-253's single browser E2E
(`attack jake on the head`) and task-288's condition-editor modal both live, so
that is where I would go next.

## What I did not reach

> **Correction to an earlier version of this section.** I first wrote "of the 8
> tasks whose claims are testable in a running browser", having counted the
> backlog as 38. That count was wrong — it came from misreading the `list`
> output, and the real number is **158**. So the framing was worse than the
> number: it implied the other 150 were untestable, when in truth I had simply
> not assessed them. **Five of fourteen areas have had no task verified at all**,
> including `triggers` (13) and `items` (14), which is where the most consequential
> unwired behaviour in this document lives (§7, §30). Anyone planning follow-up
> work should treat "not tested" here as "not looked at", not "looked at and
> fine".

The tasks below are the eight I did put through the browser, with what happened.

## Review-task verdicts

| task | claim | verdict |
|---|---|---|
| **530** | Graph toolbar two-tier redesign; labels fixed; already-selected tab is a no-op | ✅ **CONFIRMED — moved to `done`** |
| 508 | `uses: -1` never spent or destroyed | ✅ partially confirmed (1 of 3 criteria) |
| 531 | Contextual scope bar: breadcrumb, counts, WorldPainter | ✅ confirmed (softens §16) |
| 506 | Consumables author a relieving `adjust_vital` | ✅ consumption works at runtime |
| 511 | Short-range separation pushes overlapping items/characters apart | ❌ **not holding** |
| 526 | Areas become compact dots below a 140px/cell pitch | ❌ **not holding** |
| 558 | Wordwrap way and edge labels | ❌ **not holding at all** |
| 559 | Weather is narrated ("in `rainy`, say it is raining") | ❌ **not holding** |

### 530 — confirmed, and better than the task claimed ✅

Screenshots: `audit/29-settings-graph-tab.png`, `audit/31-graph-toggles-on.png`

Every acceptance item holds in the browser:

- All three layout tabs keep **fixed labels** — `🔮 Graph`, `🗺️ Map`, `🌳 Levels`
  — with `aria-selected` tracking correctly.
- **Clicking the already-selected Graph tab is a genuine no-op**: node counts and
  scope filter are byte-identical before and after.
- `#btn-overlays` keeps the text `👁 View ▾` permanently.

**Bonus, beyond what the task asked for:** selecting `Levels` *disables* `Map`
with an explanatory tooltip — *"Map is unavailable while Levels owns the layout —
pick Graph first, then Map."* That is a correct interlock, correctly explained.
The tab tooltips are also unusually honest: Graph is described as *"nodes sit
where you put them (or wherever physics settles them)"* and Levels as
*"nodes sit by relation level, physics off"*. Moved to `done`.

### 511 — separation settings exist, but the criterion does not hold ❌

Screenshots: `audit/30-settings-graph-scrolled.png`

The **🧲 Separation** group is real and every claimed default is present:

| control | claimed | actual |
|---|---|---|
| Separate Overlapping Nodes (on) | enabled | ✅ `graphRepelEnabled: true` |
| Repel Distance | 55 | ✅ 55 |
| Ignore Beyond | 220 | ✅ 220 |
| strength | 0.6 | ✅ `graphRepelStrength: 0.6` (no slider — config only) |
| Parent Pull | 0.12 | ✅ 0.12 |

**But the acceptance criterion fails.** Measuring *rendered* positions on the live
network, excluding edge-joined pairs as the spec requires:

| elapsed | unjoined item/character pairs closer than 55px |
|---|---|
| t=0 | **27** |
| t=3s | **27** |
| t=6s | **27** |
| t=10s | **27** |

Stable, so not a settling artefact. Closest offenders: `item_broken_shield` ↔
`item_spear` at **18px**, `item_club` ↔ `player_Eldenford_Merchant` at **17px**,
`item_broken_shield` ↔ `player_Zikka` at **28px**.

**Why I think the two systems are fighting rather than the pass being absent.**
Toggling the checkbox off and on moves every node (`item_berries` at 150,-71 →
200,-10 → 138,-33 within seconds) and the violation count drifts 27 → 24 → 17
with no convergence. The global physics solver continuously repositions
everything, so the local 55px constraint is re-violated as fast as it is
enforced. `graphLayoutMode` is `"free"` and **`graphImprovedLayout` is `false`** —
so on a fresh load the "better initial node placement" is *off*, and the free
solver is what you see. That is the mechanism behind §1.

**Also worth noting for whoever picks this up:** `Levels` mode turns physics
*off*. It is currently the only way to get a layout that holds still.

### 526 — compact dots never trigger ❌

Acceptance: *"Compact dots below `MAP_CARD_MIN_PITCH` (140px/cell). An area
becomes a `dot` sized from the cell."*

Measured in the `Eldenford interior` scope — the tightest pitch available:

| | value |
|---|---|
| areas in scope | 71 |
| nearest-neighbour pitch (min / p10 / median / p90) | **40 / 40 / 40 / 40** |
| areas below the 140px threshold | **71 of 71** |
| areas rendered as `dot` | **0** |
| areas rendered as `box` | **71** |

Every single area sits at a 40px pitch — less than a third of the threshold —
and not one became a dot. This is the direct cause of the unreadable cluster in
§1: full-size boxes, 40px apart, each carrying a 60-character label.

### 558 — wordwrap is entirely absent ❌

vis-network only wraps text when a label's `font` carries `multi` / `breakWord`.
Counted across the live network:

| | labelled | carrying a wrap directive |
|---|---|---|
| node labels | 116 | **0** |
| edge labels | 230 | **0** |

Not one label in the graph can wrap. And the labels it was meant to make legible
are the worst in the app — every way node is:

> `?\nSparse Forest (Eldenford interior 10,3) to Road (Eldenford interior 10,4)`

A two-ended name with **two** worldpainter grid coordinates, 60+ characters, on
116 nodes at a 40px pitch. This is the third place the `world R,C` leak appears
(§11 prose, §17 edge label, here on the canvas).

### 559 — weather is still not narrated ❌

Acceptance: *"Standing outside in `rainy` says it is raining; in `stormy` says
something worse."*

Live header: `🕐 08:00 · Jan Day 1 · 🌑 new moon · ☀️ overcast · 🌧️ in 4h: rain`

Live `look` output, standing outside:

> A worn track cut through the land. A road along the forest line, the trees
> close on the southeast. It runs east, north, northwest and southeast from here.
> **Pleasant.** [northwest] Road (world 8,3) is visible beyond (pleasant). …
> [south] Camp Entrance Trail is visible beyond (cool). [northeast] Deep Forest is
> visible beyond (dimly lit, cool).

**Not one word about the overcast sky or the rain in four hours.** The output
covers terrain, exits, light level and temperature, and stops. The weather is
mechanically present in the header and narratively absent from the world, which is
precisely the gap the task describes — so it is genuinely unfinished rather than
regressed.

## 26. `inventory` contradicts itself (S2)

Live, as Belne holding an equipped torch:

> ⚙️ [Tick 76 | 08:00] World **[Right Hand] Torch [WORN] You are not carrying anything.**

An item is listed, equipped, and then the same sentence says nothing is carried.
The equipped slot and the carry list are evidently different collections and the
summary counts only the latter. A user cannot tell from this whether they are
holding anything.

## 27. A worn item cannot be examined, and the character believes she lost it (S2)

Captured from Arix's first live turn (LM Studio, `qwen/qwen3.5-9b`):

1. Her prompt states `Wearing: Shiny Coin [drop] (known)`.
2. She acts `examine Shiny Coin`.
3. The engine answers: **"✕You look for 'shiny coin' but don't see it here."**
   and lists what *is* examinable (War Drum, Vekka, the passages).
4. That failure is fed back to her as fact, and she reasons:
   *"Wait, where did my shiny coin go? Stupid cave!"*
5. She writes a **memory**: *"The shiny coin vanished from my hand, leaving only
   the gnawing hunger to guide my next move."* — importance 8, tagged
   `["hunger","desperation"]`.

**Expected:** examining something you are wearing examines it.

**Actual:** the action resolves against the room's item list only, so a carried or
worn item is invisible to it. The engine then hands the LLM a confident false
negative, and the LLM does exactly what a person would: concludes the item is
gone and commits it to long-term memory. One bad resolution rule becomes a
permanent, self-authored false belief, and the memory survives the item.

**Related, smaller:** her response contained `"learned_names":["War Drum"]` — an
**item** name. `learned_names` is the mechanism for "someone you have seen by
appearance, now you know their name". Feeding it a drum means Arix now treats a
prop as a person she has met.

## 28. ~~Hunger: the status annotation is definitively wrong~~ — WITHDRAWN, see below

This finding was **wrong and is withdrawn in place**; the corrected version is the
second §28 further down ("the annotation is right, the decay model is wrong"). It
is left as a tombstone rather than deleted because the sequence is the point:
I asserted the mechanic was incoherent from two printouts, then tested it and
found the mechanic was fine and a *different* thing was wrong. Kept so the
correction is auditable.

The reasoning error was specific and worth naming: I read `status` printing
`"Hunger: 10 — fills toward 100"` and the agent prompt printing *"You are very
hungry"* at high hunger, treated the two as contradictory, and never checked which
one the engine actually acts on. They agree.
generic boilerplate then it is wrong for hygiene, bladder, sanity and every other
vital where high is not good. That makes it misleading across the whole vitals
block rather than for one stat.

## A note on what I could not test

The remaining 30 tasks in `review/` are overwhelmingly WorldPainter and
world-scope work (task-495, 496, 520, 523, 524, 528, 535, 536, 539, 540, 541,
557, 560, 561, 562, 563, 564, 567, 568, 575) plus behaviour-mode compile
(503), soak telemetry (542, 543), climate (553, 554), place-seeking (566), a
polymorph item (572), a vitals panel (573) and the LLM inspector labels (593).
Most of those need a painted scope to exist, and **the WorldPainter currently
offers 1 of 6 scopes** (§10) — so most of that work is currently untestable
through the UI even by its author. That coupling is itself worth surfacing: the
WorldPainter scope picker is now a bottleneck for verifying a third of the
review backlog.

## 28. Hunger: RETRACTED — the annotation is right, the decay model is wrong (S2)

**This replaces my earlier §22 and §28, both of which were wrong. I have
withdrawn them.**

I previously claimed the `— fills toward 100` annotation contradicted the
mechanic. I tested it instead of reasoning about it, by setting Belne's hunger to
90 through the vital modal and running her turn:

> **Hunger 90** → `=== YOUR STATE === You are very hungry and it is draining you.
> FIND SOMETHING TO EAT NOW.`

**High value = very hungry.** So `fills toward 100` is *correct* — hunger is
supposed to climb as time passes — and `eat bread` correctly pushing 55 → 10 is
correct too (eating sates). The mechanic is coherent and the annotation describes
it accurately. My claim was wrong.

**The real problem is the decay model, and it is worse.** The vital modal for
hunger reports:

| | |
|---|---|
| Decay rate (per turn) | **0.0034** |
| Base / Override | 0.0034 / 0.0034 |
| Time to empty | **2941.2 turns** |

At 0.0034 per turn, going from 0 to 100 takes **~26,500 turns — roughly 2,700
in-game days**. Meanwhile the engine is shouting `FIND SOMETHING TO EAT NOW` at
90 and calling it *draining*, and the modal presents the figure as
**"TIME TO EMPTY"**, i.e. it models the value as draining *away* rather than
filling *up*.

**Expected:** a stat the engine reports as urgent should move on a timescale a
character can experience, and the modal should describe the direction it actually
moves.

**Actual:** the urgency is effectively a permanent alarm. It cannot be relieved by
waiting — only by eating — and on any human timescale hunger never changes, so
every character is permanently "very hungry" and permanently being told to find
food, from the first tick onward. The modal compounds it by labelling the
quantity "decay" and "time to empty", which is the opposite of the direction the
status annotation and the state prompt both describe.

**Secondary (S3):** the modal shows `Base: 0.0034 | Override: 0.0034`. No override
is set, but the UI presents base and override identically with no indication of
which is active or how to clear one.

### Vitals legibility — where the disagreement actually lands (S3, not a bug)

Tommy on the naming: *hunger, thirst and bladder rising should read as "you feel
more hungry, more thirsty, bladder is more full."*

**The encoding already carries that.** Vitals rise **0 → 100** and are rendered on
a **green → red spectrum**, so "higher number = worse" is legible from colour
alone without reading a label. That is a real and effective channel, and my
framing under-credited it — I argued from the *words* on a stat that is mostly
read by its *colour*.

So this is a naming question, not a defect, and the suggestions are cheap:

- **`Bladder` is the odd one out.** Hunger and Thirst are naturally "more is
  worse". Bladder at 100 reads as *more full*, which is right, but the name
  describes a body part rather than a state. `Fullness` or `Bladder Full` states
  the variable, so the axis label matches what the bar means.
- **Label the axis once, not per-stat.** Since the colour band already means
  "worse", a single caption — *"higher = more urgent"* — removes the need to
  re-derive direction from six different nouns.
- **`TIME TO EMPTY` in the modal is the one genuinely wrong label**, because
  hunger fills rather than empties. That is the §28 finding above and it stands
  independently of any naming preference.

Nothing here needs the mechanic changed. It is the smallest of the findings in
this document and the only one I would call optional.

## 29. The vital modal is a raw numeric editor, not "natural-language details" (S3)

**Screenshot:** `audit/33-vital-modal.png`

The inspector help advertises:

> "Advanced (skills, behaviors, knowledge, **Vitals are clickable for
> natural-language details**)."

Clicking Hunger **does** work — a modal opens, and **the write path is sound** (I
set 90, saved, and the panel updated). But the contents are:

> **Belne's Hunger** — 10 / 100 · 10% · VALUE (0–100) · DECAY RATE (PER TURN)
> 0.0034 · Base 0.0034 | Override 0.0034 · TIME TO EMPTY 2941.2 turns ·
> Conditions Affecting — *No active conditions affect this vital.*

There is no natural language anywhere: it is two number inputs and a derived
figure. The affordance works and the help describes a different, better feature
than the one that exists. The one genuinely useful part — **"Conditions Affecting:
No active conditions affect this vital"** — is exactly the kind of thing that is
impossible to get any other way, and it is buried under two raw floats.

## 30. Triggers fire correctly, but the two trigger representations don't meet (S2)

**Positive first:** the runtime trigger system **works, and I verified it
end-to-end.** The world's 29 `logic_trigger` nodes are flat and compiled:

```jsonc
// graph.nodes["logic_trigger_drink_water"]
{ "effects": [{ "type": "adjust_vital",
                "params": { "stat": "Thirst", "amount": -50, "target": "self" } }],
  "once": false, "trigger_type": "on_drink" }

// graph.nodes["logic_trigger_eat_bread"]
{ "effects": [{ "type": "adjust_vital",
                "params": { "stat": "Hunger", "amount": -45, "target": "self" } }],
  "once": false, "trigger_type": "on_eat" }
```

And the observed output matches those numbers **exactly**: `drink` → *"Your
thirst eases (-50)"*, `eat bread` → *"Your hunger eases (-45)"*. The trigger type,
the effect, the stat and the amount all line up. Whatever consumes these nodes
works.

**The problem is that the authoring format is a different shape entirely.** The
9 library `triggers` entries are node-graphs, not compiled effects:

```jsonc
// library trigger "monster_crossing"
{ "name": "Monster Crossing",
  "graph": {
    "nodes": [ { "id":"n0", "type":"trigger",   "props":{"trigger_type":"on_enter","target_tag":""} },
               { "id":"n1", "type":"condition", "props":{"condition_type":"has_item",
                                                          "item":"crushed monster can","target":"player"} },
               { "id":"n2", "type":"effect",    "props":{"effect_type":"message","message":"…"} } ],
    "wires": [ {"from":["n0","output"],"to":["n1","input"]},
               {"from":["n1","output_yes"],"to":["n2","input"]} ] } }
```

**So there are two trigger languages** — a visual node-graph with wires, and a
flat compiled `effects[]` — and **I could not find any UI that converts one into
the other.** The Library Browser has no Triggers tab (§7), so the authoring
format cannot be opened, edited, or compiled from the UI at all. Someone must be
compiling these by hand or by script.

**Two further problems with the shipped library:**

- **Two of the nine are junk placeholders**: `my_trigger` and `untitled`. These are
  test scaffolding sitting in a content library, and nothing flags them.
- **The library triggers reference entities that do not exist in this world** —
  `monster_crossing` needs a *"crushed monster can"* held by the player, and
  `on_tick_warm_room` / `on_use_message` are clearly authored for the
  `taco_bell_date` / `pines` worlds. So the trigger library is not a library for
  *this* scenario, and nothing in the UI says which world a trigger targets.

**Why it is probably wrong:** the world-side triggers work and are almost
certainly the fixture-based ones (task-506 declares 26 fixtures, and 29 world
triggers against 9 authored ones is close to that ratio). So the authoring path
exists somewhere and simply is not reachable from the interface — which means the
feature is "wired but unreachable" in the same way as the structured personality
fields in task-542's neighbourhood.

## 31. The area scope picker never shows the area's actual scope (S2) — task-539 not working

**Screenshots:** `audit/35-area-inspector.png`, `audit/34-outline-areas.png`

The area inspector is genuinely rich — description with an ✨ Improve button, and
a 🌡 **ENVIRONMENT** block with eight fields: `LIGHT` (pitch black / dim /
normal / bright / blinding), `TEMP °C`, `AIR` (Fresh / Stale / Humid / Toxic /
Smoky / Fragrant), `SMELL`, `NOISE` (Quiet / Dripping / Humming / Windy / Loud /
Chaotic / Silent), `WEATHER`, `WIND` (none / breeze / wind / gale / storm /
hurricane), `HUMIDITY` (dry / humid / wet / flooding), plus 🎛 **PRESETS** with
an `APPLY TO` scope of *This area* / *Area + connected (open ways)* / *All
areas*, and 🔊 **SOUNDS**. This is well designed and worth saying.

**The bug is the Scope picker.** Every one of the 205 areas carries a real
`properties.world_scope_id` — and the distribution is exactly what the scope
dropdown reports:

| scope | areas |
|---|---|
| world | 60 |
| goblin_camp | 21 |
| eldenford_interior | 71 |
| west_woods | 53 |
| **total** | **205** |

So the *counts* everywhere in the UI are right. But the per-area `<select>` does
not preselect the value. Four areas, two different scopes, four identical
failures:

| area | actual `world_scope_id` | what the picker shows |
|---|---|---|
| Abandoned Farm | `world` | **— no scope —** |
| Animal Pens | `goblin_camp` | **— no scope —** |
| Armory | `goblin_camp` | **— no scope —** |
| Blackmarsh | `world` | **— no scope —** |

**Expected:** the current value selected. task-539's own acceptance text names
this exact hazard — *"an orphan option so a scope id with no record still shows as
the current value **instead of the select lying**"*. The select has a full, correct
option list (`— no scope —, world, deep woods, goblin camp, test, West woods,
Eldenford interior`), so the fetch works and only the *selection* is broken.

**Why this is worse than a cosmetic slip.** The control looks correct — right
options, plausible default — so nothing signals a problem. And task-539 also
specifies that choosing "— no scope —" posts to the area's *current* scope. Since
the control already reads "no scope" when the area actually has one, **any save
that includes this field can clear a real scope membership.** I did **not**
test that write path, because doing so on a live scenario with no UI undo is not a
reversible experiment, and this audit does not modify data. Flagging it as a
data-loss risk that follows directly from the read-side bug rather than claiming
it as measured.

**Correction to my own process, twice in this area:** I first read
`properties.scope` and concluded *"all 205 areas have no scope"* — wrong key. It
is `properties.world_scope_id`. I then read `properties.weather` and started to
call the area's `clear` a duplicate source of truth against the world's
`overcast` — also wrong: environment is nested under `properties.environment`,
and `clear` is a deliberate, rare override (11 of 205 areas set it; the other 194
inherit, which is what the `— area default —` option is for). Both were caught by
checking the actual key before writing anything down.

**Also confirmed working:** the per-area `world_scope_id` counts, the environment
block (all eight fields populate from real data), the `APPLY TO` preset scope,
and `SOUNDS` reporting *"quiet — no active sound sources."*

**A bulk-edit worth guarding (S3):** an environment preset can be applied to
**"All areas"** — one click rewriting the environment of all 205 areas, with no
confirmation and no undo offered in the panel.

## 32. Many areas are named after grid coordinates, and "Bridge" is used 7+ times (S3)

**Screenshot:** `audit/34-outline-areas.png`

The Outline lists, consecutively:

```
Bridge (Eldenford interior 17,17)   20°C · 60 lux · ?
Bridge (Eldenford interior 7,16)    20°C · 60 lux · ?
Bridge (Eldenford interior 8,15)    20°C · 60 lux · ?
Bridge (Eldenford interior 8,16)    20°C · 60 lux · ?
Bridge (Eldenford interior 9,15)    20°C · 60 lux · ?
Bridge (world 10,6)                 20°C · 60 lux · ?
Bridge (world 12,3                  20°C · 60 lux · ?     ← truncated mid-string
```

**Three things wrong at once.** (a) At least seven distinct areas are all called
`Bridge` and are told apart only by their coordinate suffix. (b) The coordinate
suffix is the **fourth** place the worldpainter `world R,C` convention leaks into
a user-facing surface (prose §11, edge labels §17, canvas labels Round 3, now area
names). (c) The last one is **truncated mid-parenthesis** — `Bridge (world 12,3`
with no closing bracket — so the name is clipped by the panel, not merely long.

**Why it is probably wrong:** these are generated Eldenford-interior way/area
names. A name that must carry a coordinate to be unique is a name that cannot be
typed, matched by voice, or read aloud, and a set of seven identical names is not
something a user can navigate by. This is the same root cause as §8: the id and
the display name are not separated, so the coordinate ends up in the name.

## 33. Soak Lab works, and it measures §28 precisely (positive finding + hard numbers)

**Screenshots:** `audit/37-soak-lab.png`, `audit/38-soak-running.png`, `audit/39-soak-complete.png`

Soak Lab is a **separate page** (`/soak`, "long-horizon experiments"), reached from
Game ▾ Soak Lab. It is the most substantial single tool in the app and it works
end to end. I ran one.

**What it offers:** scenario picker, tick count, minutes/tick, horizon presets
(1 day / 1 week / 1 month) with a live readout ("23 chars · 7d00h00m (10,080
ticks @ 1 min/tick)"), a **seed**, a sample interval, an optional label, and six
documented options — Engine decay, Neutral environment, All background, Mature
systems, Debug HP drops, Record per-character series — **each with a one-line
explanation of what it does**. Then **nine presets** (Authored baseline, Engine
decay, Neutral environment, No decay (immortal), Mature systems on, All background,
Starve them out, Debug HP drops, One game week, One game month). The empty state
names the two most useful presets inline, which is a nice touch.

**Results surface:** nine tabs — Overview, Vitals, Survival, Space-time, Growth,
Characters, Events, Compare, Export — plus **six exports** (Report JSON, Report +
samples JSON, Samples CSV, Deaths CSV, Characters CSV, Growth CSV) and Copy /
Copy link.

**The run I did** (authored baseline, 300 ticks, seed 1234):

| | |
|---|---|
| progress | 100.0%, tick 300 / 300, 0d05h00m of 0d05h00m |
| rate | **26 ticks/s** |
| elapsed | 12s (projected wall 56s) |
| **alive / dead** | **23 / 0** |
| extras | ETA countdown, "finished" timestamp, extrapolation to 1d/1w/1mo |

Live progress streamed into the chart as it ran, which is what the empty state
promised. This is genuinely good tooling.

### And it measures the §28 bug exactly

The Overview tab's "Vitals over time" chart, averaged across living characters,
over 300 ticks (~5 in-game hours) with **no overrides** — authored baseline, so
this is the shipping configuration:

| vital | start | end | net change over 300 ticks |
|---|---|---|---|
| **HP** | ~84 | ~86 | **+2** |
| **Energy** | ~74 | ~39 | **−35** |
| **Thirst** | ~52 | ~60 | **+8** |
| **Hunger** | ~52 | ~54 | **+2** |

**Expected:** the four core survival vitals to move at comparable rates, since
they are peers in the same panel and the same character sheet.

**Actual:** they differ by more than an order of magnitude. Energy moves 35
points, thirst 8, and **hunger moves 2** — about **1/4 the rate of thirst and
1/17 the rate of energy**. The orange hunger line in the chart is visually flat.

**Why it matters.** The engine tells every character *"You are very hungry and it
is draining you. FIND SOMETHING TO EAT NOW"* — and over five in-game hours that
stat moves two points. So the urgency is a permanent alarm attached to a
near-frozen number: it can only be silenced by eating, never by waiting, and it
never escalates. The modal's `0.0034 / turn` and "2941.2 turns to empty" (§28) are
the same fact seen up close; this is the same fact seen across a whole simulated
day, and it is the clearest evidence in the audit.

**The directions are all correct** — thirst and hunger rise (high = more needy),
energy and HP fall. So this is a magnitude problem in the authored decay rates,
not a sign error, and not the annotation being wrong. That distinction matters:
§22 and §28 were retracted earlier for claiming the opposite.

## 34. The `🔤 Names` graph toggle is a one-way door (S2)

**Screenshots:** `audit/40-view-overlays.png`, `audit/41-names-toggle-latched-off.png`

The View menu (`👁 View ▾`) is well organised — **seven overlay modes** (None, 💡
Light, 🌡️ Heat, 🔊 Sound, ⚡ Triggers, 🧭 Way directions, 🏘 Inhabited) and **six
display toggles** (🖼 Images, 🔩 Trigger nodes, 👁 Item nodes, 🏢 Floors, 🏷 Edge
labels, 🔤 Names, 📖 Legend), plus zoom and font steppers. Good structure.

**But `🔤 Names` cannot be turned back on.** Measured on the live network,
counting labelled nodes, clicking it six times:

| click | button shows | labelled nodes |
|---|---|---|
| 0 (on page load) | **inactive** | **635** |
| 1 | **active** | **0** |
| 2 | inactive | 0 |
| 3 | active | 0 |
| 4 | inactive | 0 |
| 5 | active | 0 |

Two separate faults:

1. **The displayed state is inverted on load.** The button renders *inactive*
   while all **635** nodes are labelled — 351 ways and 205 areas among them. So
   the control's initial appearance contradicts reality, and the very first click
   appears to *enable* something that was already on while actually switching
   every label off.
2. **Once off, it latches.** Six clicks, the `active` class alternates correctly
   every time, and the labelled count never leaves 0. There is no click that
   brings the names back.

**Expected:** a boolean display toggle. Press it again, labels return.

**Actual:** the labels can be destroyed but not restored, in a session, with no
undo and no error.

**Why this compounds §1 and §32.** The unreadable node cluster is *mostly* the
absence of any way to manage it: task-526's compact dots never fire (Round 3),
task-558's wordwrap is absent (Round 3), and now the one control that could hide
the labels is a one-way door. The `🔤 Names` tooltip is itself honest about a
related behaviour — *"Names auto-hide at overview zoom on a dense painted map
(toggle off to force-hide)"* — which tells the user the toggle is a way to
*remove* labels and never mentions that it cannot restore them.

**Mitigating, and worth stating so this isn't overstated:** a page reload
restores all 635 labels. So the damage is session-scoped, and `localStorage` has
no `vw_show_names` key. The fault is that there is **no in-app recovery** and no
indication that the state is latched — not that the user's profile is corrupted.

Note the trigger-node cluster is clearly visible in
`audit/41-names-toggle-latched-off.png`: the ~29 magenta ellipses are force-piled
into a tight blob at the centre of the canvas, which is the visual signature of
the 29 trigger nodes that have no stored x/y at all (§4).

## 37. Both Simultaneous modes work, and both announce themselves

**Screenshot:** `audit/42-simultaneous-mode.png`

The two remaining turn modes are real and correctly wired:

```
⚙️ [Tick 2 | 08:00] World  🔄 Simultaneous mode enabled (experimental — chaos by design)
🏠 [Tick 3 | 08:00] World  Simultaneous per room enabled (rooms resolve independently)
```

Each mode posts a clear, correctly-worded event to the stream, and the
per-room variant explains its own semantics. That is good practice — the two
"experimental" modes are the ones a user is most likely to distrust, and the app
tells them what they just turned on.

This also re-confirms **§25**: with *Simultaneous per room* selected, the panel
still describes the behaviour as **"Characters act one at a time"**. So the
static description is now demonstrably wrong for a mode whose entire purpose is
that characters do *not* act one at a time.

**Correction to my own probe, for the record:** my `innerText` read of the
sidebar reported `Turn mode | Sequential` while the select's `value` was
`simultaneous_room`. The screenshot shows the select correctly displaying
"Simultaneous per room". `innerText` on a `<select>` is not a reliable read of
its current selection — that is the sixth time a DOM probe disagreed with the
screen in this audit, and the same rule applies: screenshot or nothing.

## 35. The area environment editor is an enum form over free-text and numeric data (S2)

**Screenshots:** `audit/44-new-room-template.png`, `audit/35-area-inspector.png`

Opened `New Room from Template` (90 library area templates) and the entry for
**Upstairs Hallway** showed its temperature raw:

> `Upstairs Hallway (upstairs_hallway)` … 2 items · light · dim ·
> **0.7788746603906249°C**

Every other entry shows a clean integer or one decimal. That led me to count
what the 90 templates actually store in each environment field, against what the
area inspector's dropdowns offer:

| field | editor offers | what the 90 templates actually contain |
|---|---|---|
| **LIGHT** | 5 string enums: `pitch black, dim, normal, bright, blinding` | **4 strings + 13 distinct NUMBERS** |
| **AIR** | 6 enums: `Fresh, Stale, Humid, Toxic, Smoky, Fragrant` | **18 distinct values + 7 empty** |
| **NOISE** | 7 enums: `Quiet, Dripping, Humming, Windy, Loud, Chaotic, Silent` | **42 distinct values, most of them prose** |
| WEATHER | 8 enums incl. `— area default —` | **`undefined` for all 90** |
| WIND | 6 enums | **`undefined` for all 90** |
| HUMIDITY | 4 enums | **`undefined` for all 90** |
| TEMP °C | number input | 84 clean integers, **6 unrounded 16-digit floats** |

**LIGHT is the clearest type violation.** 38 of 90 templates store a *number*:
`5`(×5) `10`(×2) `15` `20`(×5) `25`(×2) `30`(×8) `50`(×3) `55` `60`(×3) `65`
`70`(×4) `75` `80`(×2). The rest use `normal`/`dim`/`bright`/`pitch_black`. So
the field is simultaneously an enum and a 0–100 scale, and the editor can only
represent the enum half. `blinding` is offered but never used.

**NOISE is being used as free text.** 42 distinct values, including whole
sentences:

> `"silent except for an occasional creak of straining timbers"`
> `"distant traffic, the taco bell sign buzzing"`
> `"kiosk beeps, soda machine hiss, drive-thru speaker"`
> `"surprisingly quiet, the sound of running water deep down the toilet"`

The editor shows a seven-option dropdown. **Every one of those prose values
would be destroyed by opening the area in the inspector and pressing save.**

**Expected:** a form that round-trips the values already in the data — or a
migration that brings the data into the form's vocabulary first.

**Actual:** the form is enum-only and the data is enum-and-prose-and-numbers.
`WEATHER`, `WIND` and `HUMIDITY` have no template data whatsoever, so three of
the eight environment dropdowns cannot represent a single library template.

**Related, smaller:**

- **80 of 90 area templates have no authored `name`** and the library falls back to
  the id with underscores replaced by spaces — so `attic`, `balcony`, `basement`
  render lowercase while `Abandoned Farm`, `Bathroom`, `Blackmarsh` render as
  authored names. That is a *third* naming convention on top of §8's four.
- `upstairs_hallway` (authored name, 2 items, `air: cold`) and `upstairs_hall`
  (fallback name, 5 items, `air: drafty`, `light: 30`) are different rooms with
  different contents — **not** duplicates, though they read as one in the list.
  Both of their `air` values are outside the editor's vocabulary.

### The pattern, which matters more than any one instance

This is the **third** field in this audit where an editor renders a value it
cannot round-trip:

| finding | the mismatch |
|---|---|
| §15 | `Uses` shows a magic `-1` sentinel in a plain number box |
| §31 | the Scope select shows "— no scope —" for areas that have a scope |
| **§35** | enum dropdowns over prose/numeric/absent data |

So it is not three coincidences. **Anything opened in an inspector and saved is
at risk of silent data loss**, and the risk is invisible because the form renders
a plausible-looking control rather than an error. If you want to prioritise
auditing rather than fixing, the highest-yield question is: *for every field in
every inspector, can it read back every value that already exists in the data?*
I would expect several more failures from that question, and the answer is cheap
to check per field.

## 36. Scenario Manager has no search or filter, and unlabelled count icons (S2/S3)

**Screenshot:** `audit/43-scenario-manager.png`

`Game ▾ Scenario Manager…` opens a **Scenarios** modal with a card per scenario,
each showing name, then two icon-counts, size and age, and five actions:

```
world_template        🏠 0 · ⚡ 3 · 368.0 KB · 18h ago
violent_parr_scenario 🏠 9 · ⚡ 14 · 123.5 KB · 6d ago
unnamed               🏠 6 · ⚡ 2 · 71.0 KB · 6d ago
testapartment         🏠 7 · ⚡ 1 · 23.9 KB · 34d ago
taco_bell_date        🏠 8 · ⚡ 3 · 156.6 KB · 6d ago
pines                 🏠 23 · ⚡ 21 · 376.3 KB · 1d ago
      [▶ Open] [🔍 Audit] [📋 Copy] [✏️ Rename] [🗑 Delete]      ⟳ Refresh
```

**No search box, no sort control, no filter** — across 22 scenarios. This is
exactly the gap already noted in `developer ideas.md` ("scenario manager search
and filter"), so this confirms a filed idea rather than discovering a new one.

**Neither 🏠 nor ⚡ is explained anywhere.** 🏠 is presumably rooms and ⚡
presumably triggers, but the footer only documents the destructive part:
*"Opening a scenario REPLACES the current world (⌘/Ctrl Undo restores)."* — which
is good, and is the kind of warning usually missing. A user has to guess what
⚡3 means. `world_template` shows `🏠 0 · ⚡ 3`, which is also the degenerate
scenario from §24.

**Credit where due:** the footer warning, the per-row Audit action, the relative
timestamps, and the `Rename` action are all good. The gap is discovery at 22+
entries, and a legend for two icons.

---

# Round 6 — the tag panel, and what it revealed about §14

## 38. The tag autocomplete is inverted: 95% of what it suggests is unused (S2)

**Screenshots:** `audit/46-tag-panel.png`

`⋯ More ▸ 🏷️ Tags` opens a **tag panel** — and this is a good piece of design.
It is headed *"🏷️ Tags (click to filter)"* and lists every tag present in the
loaded world **with the number of nodes carrying it**:

```
🏷️ adult (16)   🐾 animal (6)   🏷️ animals (1)   ⛡ armor (1)
🏷️ bathing (2)  🏷️ bear (1)     🏷️ bird (1)     🏷️ blacksmith (1)
...
road (101)   forest (85)   woods (83)   goblin_camp (21)   held_by:goblin (21)   cave (20)
```

So the "which tags can actually match anything" question I raised in the tag
generator section **has an answer in the product already** — a per-tag node
count, clickable to filter. Good work.

**But comparing that panel against the tag registry produces the sharpest version
of §14 in this audit:**

| | count |
|---|---|
| tags in the loaded world (the panel) | **102** |
| tags in the curated registry (`/api/tags/search`) | **592** |
| registry tags that **any node in the world actually carries** | **32** |
| **registry tags that carry nothing at all** | **560 (95%)** |
| auto-generated-from-memory tags | **425** |
| …of those, appearing on any node | **9** |
| tags in active use that are **absent from the registry** | **~70** |

`adult`, `animals`, `bathing`, `bear`, `bird`, `blacksmith`, `blunt`, `boar`,
`bridge`, `building`, `captive`, `cave` are all in daily use on the graph and
**none of them is in the registry.**

**Expected:** the tag picker suggests ids that are in use, or at worst a curated
vocabulary that mostly is.

**Actual — the two sets are nearly disjoint, in both directions:**

- The inspector's `TagMultiselect` autocompletes from `/api/tags/search`, so it
  offers 592 ids of which **560 match nothing** — `abandoned`, `amnesia`, `anger`,
  `ajar`, `affair`. Applying one produces a tag that no item, area or character
  will ever match.
- And **69% of the tags actually in use cannot be suggested at all**, because they
  were never registered. `bear`, `bridge`, `cave`, `blacksmith` — the tags that
  would make a fear or an interest *work* — are untypable except by free text.

**Why this is the most actionable finding in the document.** It is one number
(95% unused) and one direction (the useful ones aren't offered), it is cheap to
verify (`/api/tags/search` vs the tag panel), and it explains the earlier
observation in one stroke: the generators were offered a 592-id menu that was
72% memory-scraped abstract nouns, while the tags that would actually have made
the character's interests and fears *fire* were not in the menu at all.

**Note also:** `held_by:goblin` appears as a filterable row in this panel — the
fifth surface where the `colon` tag convention (§ tag charset, Round 4) shows up,
after prose, edge labels, node labels and area names.

**A second-order observation (S4):** the panel is built from the *loaded scope*,
so the counts change with the scope filter — which is correct behaviour, but it
means "how many tags does this world use" has no single answer in the UI.

## 39. Expression pack and conditions: the fields exist, the affordance is thin (S3)

**Screenshot:** `audit/35-area-inspector.png`, `audit/03-inspector-bio.png`

The character inspector's **EXPRESSION PACK** offers three modes — `Profile`,
`Full body`, `Split sheet` — a sprite frame, a named emotion (`neutral`), an
emotion text input (*"add expression (happy, attack…)"*) with an `Add` button, a
`+` to add a new profile, and this help text:

> "Profile is the character's avatar and follows their current emotion; full body
> is the portrait art. The 'neutral' slot is the fallback. Drag an image onto any
> card to set it."

That is clear, complete, and answers the question I would have had. The one gap
is that it explains the *image* workflow but not the **emotion list** — where
`happy`, `attack`, `fear` etc. come from, whether they must match an engine
emotion, or what happens to a character whose current emotion has no slot.

The adjacent `+ Add Condition` control and the emotion row (`neutral` with an
intensity slider at 0.00) are present and correctly laid out. I did not submit
either, since both write to the live scenario.

---

# Round 7 — the graph overlays

## 40. Four of the seven overlay modes render identically, and Heat does not encode heat (S2)

**Screenshots:** `audit/47-heat-overlay.png`, `audit/48-light-overlay.png`

The `👁 View ▾` menu is well organised into **OVERLAY** (None, 💡 Light, 🌡️
Heat, 🔊 Sound, ⚡ Triggers, 🧭 Way directions, 🏘 Inhabited), **SHOW ON CANVAS**
(Images, Trigger nodes, Item nodes, Floors), **LABELS & LEGEND** (Edge labels,
Names, Legend, font size `− 8 auto +`) and **MAP GRID** (`− 40 auto +`, helpfully
annotated *"Only used by the 🗺 Map layout."*). Each overlay change is announced
in the event stream with a timing — `Heat overlay applied (28ms)`,
`Light overlay applied (25ms)` — which is a nice touch.

**I had only confirmed this menu existed. Testing what the modes actually do:**

| overlay | nodes given a colour | distinct colours |
|---|---|---|
| None | 351 | — |
| 💡 **Light** | 556 | amber family — **visibly differentiated** |
| 🌡️ Heat | 556 | **one colour for all 205 areas** |
| 🔊 Sound | 556 | **byte-identical to Heat** |
| 🧭 Way directions | 585 | **byte-identical to Heat** |
| 🏘 Inhabited | 585 | **byte-identical to Heat** |
| ⚡ Triggers | 585 | distinct (dark) |

**Four of the seven modes produce byte-identical rendering.** The full colour
distribution for all four is:

```
{ "#2d333b": 205,  "none": 46,  "#1a1a1a": 33,  "#1a3a2a": 351 }
```

**And Heat is not encoding heat.** The 205 world areas span **11.4 °C to 23.2 °C**
— a 12-degree range with a dozen-plus distinct values (11.4, 12, 12.3, 12.9, 13,
13.9, 14.5, 15, 15.1, 16, 16.1, 16.8 …) — and under Heat **every single one
receives the identical colour `#2d333b`**. `audit/47-heat-overlay.png` shows a
visibly flat field. That is not a wide-ramp artifact; a 12 °C spread should
produce at least a few bands.

**Expected:** four different overlays producing four different pictures — a
temperature gradient, a noise-level gradient, direction arrows on the ways, and
highlighting for areas that currently contain someone.

**Actual:** one of them (Light) works. The other three are indistinguishable from
each other and from Heat, and Heat is flat.

**Why it is probably wrong.** The areas *do* carry the data these overlays need —
`noise` has seven distinct values in the world graph (`quiet`, `busy`, `lively`,
`dripping water`, `flowing water`, `loud`, and some with none at all). So Sound
is not failing for want of input. The likeliest reading is that the four modes
share one fallback path, and at most one of them is doing real work. I am **not**
claiming to know which — the measurement is that they are indistinguishable, not
why.

**This also strengthens §35 into live data.** The 205 *world* areas have the same
defects as the 90 library templates:

- `light` has five distinct values — `normal`, `dim`, `bright`, `pitch_black`
  and **`"60"`** — a number-as-string in live world data, not just templates.
- `noise` includes **`busy`** and **`lively`**, neither of which is in the
  editor's seven-option list, plus free-text values like `dripping water`.

So the "enum form over free-text and numeric data" problem is not confined to the
library. Any of the 205 areas opened in the inspector and saved is at risk.

## 41. The near-miss I am most glad I caught: "all 23 characters are nowhere" (not a bug)

**No screenshot is attached, deliberately — there is nothing to see, because
there is no defect.** This is the most valuable thing in the audit that is *not*
a finding, and it is recorded because I nearly filed it as the opposite.

`fumble` returned:

> ⚙️ [Tick 60 | 08:00] World  **"You're in an empty void."**

That reads like a character with no resolvable location. So I checked. Every one
of the 23 characters has a `current_area`, and **not one of them is a node id**:

```jsonc
Arix    → "Chief's Pit"        Belne   → "Camp Entrance Trail"
Merchant→ "Eldenford"          Thrazz  → "Cooking Area"
```

A direct `graph.nodes[current_area]` lookup returns **undefined for all 23**. By
the letter of the project's own rules — *"Backend data operations key nodes by
id; names are user-facing and resolve to ids through `engine/matching.py`"* — that
is a textbook violation, and I was about to write it up as a P0.

**It is not a bug.** `current_area` stores a display name *by design*, and it
resolves correctly through the matching layer. Verified by building the name→id
map from the graph and probing:

| display name | resolves to |
|---|---|
| `Chief's Pit` | `area_chiefs_pit` |
| `Eldenford` | `area_eldenford_village` |
| `Camp Entrance Trail` | `area_camp_entrance_trail` |
| `Cooking Area` | `area_cooking_area` |
| `Prison Pens` | `area_prison_pens` |
| `Deep Forest` | `area_deep_forest` |
| `Raven River` | `area_raven_river` |

7 of 7 resolve, and all 205 area nodes carry a name. The engine's own behaviour
corroborates it: `look` narrated Belne's area correctly, and `relieve` reported
*"where 2 others can see"*, which requires a resolved area with occupants.

**This is the project's own documented trap, and I walked into it anyway.** The
guidance exists precisely because a direct lookup finds nothing while the game
works fine. The distinguishing test is not "does my lookup work" but "does the
*engine's* lookup work" — and the engine's did, in the same request.

**Left unexplained, and honestly so:** `fumble`'s *"You're in an empty void."*
I could not determine what `fumble` means or why that string is its answer. It may
be a legitimate message about having nothing to fumble, or a fallback I have not
identified. **I am not claiming it is a bug** — only that I did not understand it,
and that it was the thread that produced this near-miss.

## 42. Remaining verbs: three work, nine are §19 (S3)

Continuing the verb sweep from §19. The **human command input** accepts:

| command | response |
|---|---|
| `relieve` | ✅ **"You relieve yourself where 2 others can see. That is going to stink up the…"** |
| `read torch` | ⚠️ "You look for 'torch' but don't see it here. Things you can examine rig…" — `read` appears to alias `examine` rather than read |
| `fumble` | ⚠️ "You're in an empty void." (see §41 — unexplained, not claimed as a bug) |
| `stow torch` | ✅ "You don't have 'torch'." (correct — wrong character) |
| `climb`, `jump`, `craft`, `make`, `combine`, `split`, `crawl`, `flee` | gibberish echo — the §19 no-argument branch |

`relieve` deserves credit: it is task-551's feature and it reports **both** the
audience and the social consequence, which is exactly the behaviour that task
promised. That is a well-implemented mechanic.

**The pattern across all three rounds of verb testing** is worth stating as a
single conclusion: the human command input accepts **~20 verbs**, of which the
majority either produce an excellent instructive error or fall into §19's
gibberish. Meanwhile the **agent prompt documents 35+** (`go, dash, crawl, climb,
jump, take, drop, use, use_on, open, close, attack, grab, lead, escape, struggle,
read, search, look, listen, fumble, stand, rest, wait, inventory, stats, relieve,
stow, put, combine, split, craft, make, ask, accept, decline, agree, disagree,
leave, give, steal, examine, stop`). So **the agent and the human have different
command surfaces and nothing in the UI says so.** Mapping those two lists
against each other would be a cheap, high-value task — and the engine already
knows the answer for the *agent*, since that path demonstrably works.

---

# Round 8 — working the review backlog properly

## How I scoped this

**87 unchecked boxes across 22 tasks** — that is the real live-verification
backlog, extracted from the `- [ ]` lines in each task's `## Testing` section.
Far more tractable than 158 tasks, and it is what "in review" actually means
here: implemented and unit-tested, with the live check still outstanding. Some
are marked *"Live-verify when convenient"* in the author's own words.

I worked the **items** and **review** groups first, because they had the most
unchecked boxes and I had claimed `triggers` mattered most — so it is worth being
clear that `triggers` has only **2** unchecked items and both are "live-verify if
needed" style. My earlier claim that triggers was the biggest unverifiable area
was about *reachability*, not about outstanding work, and those are different
things.

## 49. task-348 ✅ CONFIRMED — moved to `done`

**Screenshot:** `audit/49-placement-picker.png`

Every acceptance line holds:

- `GET /api/search/placement-targets?q=wood` → **200**, returning 50 live-world
  areas with `{id, name, type, icon, description}`.
- **All six dead references are gone** from the live DOM: `item-target-area`,
  `item-target-container`, `item-target-character`, `move-item-area-select`,
  `move-item-container-select`, `move-item-character-select` — none present.
- The replacement renders correctly: `📦 PLACE ON / IN` as three radio buttons
  (📦 ITEM / 🧍 CHARACTER / 🏠 AREA), a search box reading *"Search items,
  characters, or areas…"*, and a `Relation` select (`in, on, under, behind,
  beside, at`) with the helper text *"where inside/on the target item sits"*.

Moved to `done`.

**One correction to my own probe:** I read `item-target-type` as a `<select>` and
got zero options, which looked like a failure. The screenshot shows it is a radio
group. Seventh time a DOM probe has disagreed with the screen.

## 50. task-292 ❌ FAILS both criteria — and the two item editors disagree (S2)

Tested with **real checkbox clicks** in the create modal (I first used a synthetic
`change` event, which would have been a false reading — noted because that is the
failure mode I keep hitting).

| step | `equip` | `unequip` | `take` | `drop` |
|---|---|---|---|---|
| initial | false | false | true | **absent** |
| click `equip` | **true** | **false** ❌ | true | absent |
| click `equip` again | false | false | true | absent |
| click `take` | false | false | false | absent |

**Both acceptance lines fail:**

1. *"enable `equip` on an item → `unequip` auto-checks"* — `equip` went true,
   `unequip` **stayed false**.
2. *"enable `take` → `drop` appears in the item's available actions"* — **`drop`
   does not exist in this editor at all.**

**And this exposes a second, unfiled problem.** The create modal's action list is
14 verbs — *examine, take, use, open, close, eat, drink, read, light, activate,
equip, unequip, throw, break*. The **library** item editor (§15) has **15** — the
same list **plus `drop`**. So the same field is edited by two different controls
with two different vocabularies, and an author who ticks `take` in one editor is
not offered the `drop` the other editor would record. That is a data-loss-shaped
divergence, not a cosmetic one: create an item with `take` in the modal and it is
un-droppable-by-action in a way the library editor's own model says it should not
be.

## 51. task-155 ❌ CANNOT BE EXERCISED — the precondition field does not exist (S2)

> Acceptance: *"Bread with 4 uses at 0.5kg → after eating 1 use, weight =
> 0.375kg"* and *"Bread with 4/4 uses → weight = full `base_weight`"*.

The formula is anchored on **`base_weight`**. Measured across both registries:

| | items | with `uses` | with `base_weight` | with `max_uses` |
|---|---|---|---|---|
| library | 1915 | 1910 | **0** | 53 |
| this world | 28 | 17 | **0** | 0 |

**Not one item in the entire library has a `base_weight`.** The library does have
breads (`bread` uses=1 weight=1, `baker's_bread` uses=3 weight=0.3), but none
carries the field the scaling is defined against. So the stated behaviour is
unreachable with any item that exists — the mechanic is unit-tested against
fixtures and **no content can produce it**.

`max_uses` is better covered (53 library items), so `combine`/`split` are
theoretically exercisable; I did not reach them.

## 52. task-161 ⚠️ authored in the library, absent from the world

> Acceptance: *"Armor uses decrease when the wearer is hit"*, *"Armor breaks at 0
> uses and is removed from equipment"*.

| | armor items | of which have `uses` |
|---|---|---|
| library | 2 | **2** |
| this world | 1 (`Broken Shield`) | **0** |

So the data precondition *is* authored — both library armor pieces have `uses` —
but **the world contains no usable armor**, so the behaviour cannot occur in play
without first spawning one. Different verdict from task-155: reachable, just not
present.

## 53. task-205 ⚠️ one acceptance line is unexercisable

> Acceptance includes *"`strong_backed` trait doubles capacity, raising thresholds
> proportionally"*.

**No character has `strong_backed`.** Across all 23 characters the only trait key
present anywhere is `high_metabolism` (on one character). So that line cannot be
demonstrated without authoring the trait first.

## 54. Six tasks are wired end to end and authored by nobody (S2, systemic)

This is the pattern that mattered most in this round, and it spans a whole class.

| task | data file | present? | authored anywhere? |
|---|---|---|---|
| 476 (roles → skill biases) | `data/library/roles.json` ✅ 2637 bytes | yes | **0 of 69** library characters, **0** scenario characters have `roles` |
| 480 (skill packs, proficiency) | `data/library/skill_packs.json` ✅ 848 bytes | yes | **`proficiency` and `skill_progress`: 0 occurrences in the scenario** |
| 483 (forage tables, findable-here) | engine tables | yes | **`forage_tables`: 0 occurrences in the scenario** |

**Expected:** a data file plus an engine that reads it, exercised by at least one
character, so the feature can be seen working.

**Actual:** the file exists, the engine reads it, the unit tests pass, and **not
one character or area in the repository uses any of it.** There is no way to
observe these mechanics at runtime, and no lint or check that would notice.

**Why this is the most important thing in this round.** These tasks are *in
review* and will presumably reach `done` on the strength of their unit tests,
which is exactly how a mechanic stays invisible forever: the test passes, the
file is present, the code path is correct, and nothing in the product ever
exercises it. Combined with §14 (72% of the tag registry is unauthored
memory-scraped noise) and §30 (two trigger formats, no compiler in the UI), there
is a recognisable house pattern here — and the review queue is where it hides,
because a task with 12 passing tests and no content looks finished from the
outside.

**The cheap systemic check**, and the one I would run across the whole backlog:
for every `data/library/*.json` and every mechanic-specific node property,
*does anything in `data/` actually set it?* `base_weight` → 0. `roles` → 0.
`proficiency` → 0. `forage_tables` → 0. `world_scope_id` → 205 (works). It takes
one grep per field and it would have caught four of the six failures in this
round before any of them reached `review`.

## Verdict table for this round

| task | verdict |
|---|---|
| **348** | ✅ confirmed — **moved to `done`** |
| 292 | ❌ both criteria fail; plus a 14-vs-15 verb divergence between the two item editors |
| 155 | ❌ unreachable — `base_weight` exists on 0 of 1943 items |
| 161 | ⚠️ authored in the library, absent from the world |
| 205 | ⚠️ one line unexercisable — `strong_backed` on 0 of 23 characters |
| 476 / 480 / 483 | ⚠️ wired, authored by nobody — 0 users of `roles`, `proficiency`, `skill_progress`, `forage_tables` |

---

# Round 9 — six combat and scale findings, six tasks filed

Triggered by Tommy from the live combat output, then widened to armor and then
to scale. These are design findings rather than pass/fail task verdicts, so they
are recorded as findings and mirrored into the dev-task tree.

## Tasks filed

| id | area | title |
|---|---|---|
| **602** | items | Aimed attacks silently ignore the region when the phrase carries an article |
| **603** | gameplay | Combat adds raw ability scores to the d20 instead of `ability_mod` |
| **604** | items | Split `defense` into two anti-correlated axes: damage reduction and evasion |
| **605** | characters | Make size a real character property tied to the graph editor character form |
| **606** | characters | Author scale-correct ability scores per size tier so a leviathan is not STR 9 |
| **607** | items | Damage reduction must be percentage, not flat subtraction |

`python tools/tasks.py validate` → **698 files, 0 errors** (28 pre-existing
frontmatter warnings on old `review/` tasks).

## What I did not reach

Listed honestly rather than implied. Round 2 covered: the item inspector field
set, the Tags/Ways library tabs, the Outline and Lens panels, the edge
inspector, 13 engine command verbs, Scenario Health, the Setup Checklist, all
five turn modes, and the Game menu itself.

**Still untested, and why:**

- **Export Scenario, Commit Scenario, "Changes since source…"** — all three write
  to `data/`. Deliberately not exercised; this audit does not modify project data.
  Same for item/area **Save to Library**, **Duplicate**, the Library Browser's
  **Save**, and **equip/unequip** (a live-world mutation with no in-app undo).
  The equip *render* path was verified instead: `inventory` shows
  `[Right Hand] Torch [WORN]`, which is where §26's contradiction lives.
- **The write side of §31.** Whether saving an area with the broken scope picker
  actually clears `world_scope_id` is a data-loss test with no in-app undo, so I
  flagged it as a consequence rather than measuring it.
- **Trigger and behaviour authoring** — the runtime half is confirmed working
  (§30); the authoring half has no reachable UI at all.
- PNG export; Print (both open system dialogs). The `⋯ More` menu contents were
  confirmed: `Canvas · Templates · Lore · Tags · Sync to Library · Print · Copy
  Prompt · Paste Response`.
- Embeddings and semantic memory; the Embedding tab's controls.
- Settings tabs 2–4 controls individually (all five tabs exist and are populated;
  I read the Physics / Separation / Edges groups and exercised the Separation
  checkbox).
- Levels layout mode as a working layout — tab, interlock and physics-off
  description confirmed; I did not judge whether the hierarchical layout is more
  readable than the graph it replaces.

**Correction to my own todo list:** I had assumed an "Ensure Tag Library" menu
item existed, from reading the tag-module code. It does not — the graph's
`⋯ More` menu is `Canvas · Templates · Lore · Tags · Sync to Library · Print ·
Copy Prompt · Paste Response`. `_ensureLibraryTag` is internal to tag
autocomplete, not a user action. Recording it so the "still untested" list above
isn't chasing a feature that isn't there.

**One structural blocker worth naming, with a number on it.** A large share of the
158 review tasks are WorldPainter and world-scope work, and the WorldPainter
offers 1 of 6 scopes (§10). Some of that backlog is therefore *hard* to test
through the UI. But that is an explanation for a low rate, not a justification for
one: I did not count the blocked tasks, and 5 areas — including `triggers` and
`items` — have had **zero** tasks verified. **Read the table in Round 3 as the
measure of what this audit did and did not reach.**

**Methodological note.** Four of my DOM probes disagreed with the rendered page
in this session — the "Test Connection is dead" claim (§0), the
`/api/library/items` shape (§13), a "0 entries" reading of the Tags tab (§15),
and the equip-slots option count (§15). Every one was caught by a screenshot and
corrected in place. The recurring lesson is specific to this app: much of its UI
is built as hidden inputs plus enhanced widgets, so `value`/`options` on the
underlying element is frequently empty or stale, and only the rendered pixels are
truthful. Every S1 and S2 claim above is screenshot-backed.

---

# Round 9 — two S1 combat findings

## 55. task-253 ❌ FAILS the live E2E — and it fails on its own acceptance phrasing (S1)

**Screenshot:** `audit/50-aimed-attack-head.png`

The single unchecked box is *"Browser E2E: `attack jake on the head` through
`/api/action`"*. There is no `jake` in this world (23 characters, all goblins and
Eldenford folk), so I walked **Eldenford Merchant** seven areas from
`Road (world 16,4)` to `Camp Entrance Trail` — northwest, west, west, west,
southwest, southwest, west — and used **Belne** as the target.

**The command dispatches, resolves the fight, rolls the hit, and then throws the
aimed region away.**

```
> attack Belne on the head
Eldenford Merchant attacks Belne with bare hands!
  Attack: d20(15) + 9 STR + 0 mod = 24 vs d20(1) + 11 DEX = 12 → HIT
  Result: a glancing hit lands in the torso.      <-- not the head
```

`body_state.head` was `{sensitivity: 0.2}` before and after — unchanged. `head`
*is* a valid region: the catalog initializes all 21 regions on every character,
and `resolve_region('head')` returns `'head'`.

### Root cause — the article is never stripped

`routes/action_handlers.py:890` takes the text after the region marker and hands
it straight to the resolver:

```python
region_text = cmd[region_marker_idx + len(matched_marker):].strip()   # "the head"
if region_text:
    attack_where = resolve_region(region_text) or region_text         # -> "the head"
```

`engine/combat.py:141` then resolves it a *second* time:

```python
region = resolve_region(where) if where else None     # resolve_region("the head") -> None
```

so `region` is `None` and the attack falls through to the **un-aimed d20
hit-location roll** — that "lands in the torso" line is the roll's own output,
not a redirect or a coverage block.

Measured directly:

| input | `resolve_region` |
|---|---|
| `'head'` | `'head'` |
| `'torso'` | `'torso'` |
| `'chest'` | `'torso'` |
| **`'the head'`** | **`None`** |
| `'the torso'` | `None` |
| `'the face'` | `None` |

### The control that isolates it

Same target, same weapon, same area — only the article differs:

| command | outcome |
|---|---|
| `attack Belne on the head` ×3 | torso, MISS, MISS |
| `attack Belne on head` ×3 | MISS, **head**, **head** |

**Dropping the word "the" makes the mechanic work.** The feature is fully
implemented, wired, and correct — the natural phrasing its own acceptance
criterion names is the one phrasing that fails. The normalizer emits
`attack ${obj} on ${where}` (`static/js/agent/action-normalizer.js:109-111`), so
the LLM's structured `where:"head"` reaches the engine intact and works; only the
article-bearing natural form degrades. **That is why every unit test passes** —
they call `player_attack(where="head")` and never go through the parser.

This is the `AGENTS.md` "guard's lookup can never match what the caller passes"
failure exactly: `resolve_region` is a working function, the caller hands it the
wrong shape, and the result is a silent no-op instead of an error.

## 56. Combat adds raw ability scores to the dice instead of modifiers, so DEX beats STR and armor is inert (S1)

### Retraction of my own first analysis

I first proposed removing the defender's die and comparing against a flat DEX
threshold, and showed that going 95–100%. **That analysis was wrong and I am
retracting it.** I fed **raw STR 9** into the flat comparison, so it was not
"flat DEX vs flat DEX" at all — it was a raw stat against a raw stat, which is
the same mistake the engine is already making. Tommy's correction is the right
frame: this is a D&D-style **contest**, and the defect is not the presence of a
defensive die.

### The actual defect: raw ability scores are added to the dice, not modifiers

`engine/checks.py:74` already defines the right helper:

```python
def ability_mod(score, default: int = 10) -> int:
    """5e ability modifier: ``(score - 10) // 2``. Never clamped."""
```

**`engine/combat.py` never calls `ability_mod`.** Instead:

```python
combat.py:212   attack_roll  = roll_dice(1, 20, attacker.stats.get("STR", 10) + attack_mod)
combat.py:213   defense_roll = roll_dice(1, 20, target.stats.get("DEX", 10))
```

Raw **STR 9** goes on as a **+9 bonus** and raw **DEX 11** goes on as **+11**.
That is roughly ten points of free bonus on each side, and it is why the
defender wins the contest. When combat *does* compute a real modifier it is
inline, clamped, and used only for the display string:

```python
combat.py:218   str_mod_display = max(0, (attacker.stats.get("STR", 10) - 10) // 2)   # display only
combat.py:237   stat_mod        = max(0, (stat_value - 10) // 2)
combat.py:364   str_bonus       = max(0, (attacker.stats.get("STR", 10) - 10) // 2)
```

`max(0, …)` also means a below-average stat can never be *negative* — STR 9 gives
`0`, never `−1` — which is the opposite of what `ability_mod`'s "never clamped"
docstring intends. The live log's `+ 9 STR + 0 mod` is exactly this: raw 9 on the
die, and a clamped 0 displayed next to it.

### What the contest should produce — worked example

The live matchup: **Eldenford Merchant (STR 9, DEX 11) vs Belne (DEX 11, STR 9)**.
Both characters happen to have DEX 11 and STR 9, so this is a clean comparison.

**Today** — raw scores on the dice:

| | roll | range |
|---|---|---|
| Merchant attacks | `d20 + 9` (raw STR) | **10–29** |
| Belne defends | `d20 + 11` (raw DEX) | **12–30** |

Belne's floor (12) sits above Merchant's floor (10), and its middle is higher
too. Merchant needs a 19+ *and* Belne needs a 1–2 to win. That is the coin flip.

**With `ability_mod` on both sides** — `STR 9 → −1`, `DEX 11 → 0`, so Belne's
defense is a fixed `10 + 0 (+ armor)`:

| situation | attack | defense | result |
|---|---|---|---|
| bare hands, unarmored | `d20(14) + (−1)` = **13** | `10 + 0` = **10** | **HIT** |
| Belne in `field_jacket` (+3) | **13** | `10 + 0 + 3` = **13** | **HIT** (exactly) |
| Merchant with `iron_shortsword` | **13 + 0** = 13 | **13** | HIT — same as bare hands |
| same, sword had `+2 to hit` | **15** | **13** | solid HIT |
| same, `club` at `−1` | **12** | **13** | **MISS** |

The defender's number stops moving and becomes a fixed wall; the attacker's die
does all the swinging. 13 vs 10 hits, 13 vs 13 hits, 12 vs 13 misses.

**The last three rows are why "weapon hit modifiers" in the proposed formula is
load-bearing rather than decorative.** `iron_shortsword`, `knife`, `club` and
`crossbow` all swing identically today, because not one of the 1915 items defines
a hit modifier. `iron_shortsword` carries `damage: "1d6"`, `gribbas_good_knife`
carries `"1d4+2"` — what they *deal* is authored; how accurately they *land* is
`[]`.

### Armor is currently inert against hit chance (S1, independent of the above)

This is the part that makes it a data problem as well as an engine one.

`equipment_bonuses.py:77` aggregates a `defense` property off equipped items
(`defense += int(props.get("defense", 0))`) and `_get_target_defense()` returns
it — but `combat.py:250` spends it on **damage reduction after the hit lands**:

```python
damage = max(1, damage - target_defense)
```

So a +4 apron changes the defender's hit rate by **exactly nothing**: 73.8% with
it, 73.8% without. In the current model armor only ever reduces damage, and the
"defense" property name is misleading about that.

**The data for the defense half of the contest is already authored** — 14 of 1915
library items carry a non-zero `defense`, so nothing needs inventing:

| item | defense | | item | defense |
|---|---|---|---|---|
| `apron` | 4 | | `green_tunic` | 2 |
| `dark_cargo_pants` | 3 | | `sneakers` | 2 |
| `field_jacket` | 3 | | `jumpsuit` | 2 |
| `heavy_fur_lined_coat` | 3 | | `grey_tank_top` | 2 |
| `eva_suit` | 3 | | `broken_shield` | 1 |
| `distressed_denim_shorts` | 1 | | `short_forest_cape` | 1 |

**The attacker half has no authored data at all.** Of 1915 items, **zero** define
any hit modifier — no `hit_bonus`, `attack_mod`, `hit_mod`, `to_hit`, or
`attack_bonus`. 1355 items carry `damage`/`damage_type`, so weapons are fully
modelled for *what they deal* and completely unmodelled for *how accurately they
land*. So "weapon hit modifiers" in the proposed formula is a field that would
have to be created **and** authored, or the attacker's side will silently
contribute nothing and every weapon will feel identical to swing.

That is the fourth appearance of this audit's house pattern (§14, §30, §54):
the mechanic is specified, the helper exists, and the content that would drive
it is `[]`.

## 57. The D&D AC model cannot be expressed by the item schema (S2, data)

Supplied by Tommy as the target rule set:

| rule | |
|---|---|
| No armor | `AC = 10 + DEX mod` |
| Light armor | armor base AC **+ full DEX mod** |
| Medium armor | armor base AC **+ DEX mod, max +2** |
| Heavy armor | **fixed** base AC, DEX ignored |
| Shield | **flat +2** |
| Barbarian unarmored | `10 + DEX mod + CON mod` |
| Monk unarmored | `10 + DEX mod + WIS mod` |
| Mage Armor | `13 + DEX mod` |

**None of this is representable today.** Checked across all **1915** library
items:

| requirement | finding |
|---|---|
| armor category (light / medium / heavy) | **0** items have `light_armor`, `medium_armor`, `heavy_armor`, `armor_class`, `armor_type`, or `armor_category` |
| shield (+2) | **0** items tagged `shield`; the entire library has one shield-shaped object and it cannot be equipped |
| base AC distinct from a flat bonus | there is exactly **one** integer, `defense`, and it is applied as damage reduction |
| class-based unarmored AC | **0 of 69** library characters have a `class` key; `player.py` has no `class_` attribute |

104 items carry `armor`/`clothing`/`outerwear`/`shield` tags. Only **13** of them
give `defense` a non-zero value, and **3 is not a base AC** — D&D bases are 11
(light), 13/14/15 (medium), 16/17/18 (heavy), and a shield is +2. The authored
numbers are bespoke values that happen to sort armor-ish, so *"what does
`field_jacket`'s `3` mean"* has no answer in the data:

| defense | items |
|---|---|
| 4 | `apron` |
| 3 | `eva_suit`, `field_jacket`, `heavy_fur_lined_coat`, `dark_cargo_pants` |
| 2 | `jumpsuit`, `sneakers`, `green_tunic`, `grey_tank_top` |
| 1 | `short_forest_cape`, `distressed_denim_shorts`, `broken_shield`, `faded_green_tank_top` |

Worth noting how close this is to the shape D&D needs: the inventory is already
right *in kind* — clothing and armor exist, they are slotted (`equip_slots:
["torso"]`, `["legs"]`, `["feet"]`, `["back"]`), and the insulation/insulation-
tagged garments are exactly the light/medium/heavy split in embryo. It is the
**one missing axis** (category + base AC) that blocks it.

### Two sharp edges in the same data

**`broken_shield` cannot be held.** `actions: "take,drop,examine"` — no `equip`,
no `equip_slots`. It is the only shield-shaped item in the library, tagged
`armor`, weight 5, and carrying `uses: -1` (infinite-use, which is exactly what
task-161's armor-durability acceptance lines target). It contributes nothing to
any stat, because it can never be equipped. **task-161 has no exercisable target
in the entire library.**

**`apron` cannot be picked up, let alone worn.** `equip_slots: ["torso"]` is
authored and `defense: 4` is the highest in the library — but its `actions` are
`examine,use`. No `take`, no `equip`, no `drop`. The slot is authored and
unreachable, and the item is not obtainable at all. This is a `AGENTS.md`
"authored but unwired" case at the item level: the data says equippable, the
action list says otherwise, and nothing reconciles them.

**So the order of work is not "fix the combat math."** With §56, the engine fix
is small — call `ability_mod` instead of adding raw stats. But doing that alone
changes DEX's contribution while leaving `defense` still spent on damage instead
of AC, which means **the armor half of Tommy's AC table still would not work.**
Both the schema axis (category + base AC + shield) and the engine axis (use
`ability_mod`; spend `defense` on AC rather than damage) have to land together,
or the result is a contest with no armor in it.

## 58. The intended model is two anti-correlated axes, and only one of them exists (S1 design gap)

Tommy clarified the target after §56/§57: **not D&D's single AC**, but two
separate axes that run in *opposite* directions.

> A plate armor is **easier to hit**, but **way harder to kill someone in**. A
> light armor is **harder to hit**, but **does not reduce damage as much.**

This is a better model than AC, and the reason is structural: in D&D one number
carries both meanings, so better armor is simply better. Decoupling them makes
heavy armor a genuine **trade the defender chooses** — bigger target, safer per
hit — instead of a strict upgrade.

### What exists today

The damage-reduction half is fully implemented and consumed in exactly three
places, all identical in shape:

```python
combat.py:250 / 260 / 367    damage = max(1, damage - target_defense)
combat.py:251                 ... f" = {damage} total, -{target_defense} armor"
```

**The evasion half does not exist.** No `evasion`, `dodge`, `cover`, or
hit-modifier concept appears anywhere in `engine/` or `routes/`. So the model is
currently one axis with a misleading name: `defense` is displayed to the player
as *"armor"* while doing only damage reduction.

### The two axes, re-cut onto the 13 authored items

| item | `defense` today | → DR | → evasion | why |
|---|---|---|---|---|
| `distressed_denim_shorts` | 1 | 1 | **+1** | light, easy to move in |
| `short_forest_cape` | 1 | 1 | **+1** | |
| `grey_tank_top` | 2 | 2 | 0 | thin |
| `jumpsuit` | 2 | 2 | **+1** | close-fitting, hard to catch |
| `field_jacket` | 3 | 3 | 0 | |
| `dark_cargo_pants` | 3 | 3 | **−1** | |
| `heavy_fur_lined_coat` | 3 | 3 | **−2** | bulky |
| `eva_suit` | 3 | 3 | **−3** | sealed, loud, large target |
| plate armor | *absent* | high | very negative | the archetype |

The evasion field must be **signed** for plate to exist at all — "easier to hit"
is a negative contribution.

### Two of the 13 appear authored on the wrong axis

`sneakers` has `defense: 2`. Sneakers are not armor; that value is **mobility**,
which belongs on the evasion axis as `+2`, not as `−2` damage. `apron` is the
library's DR leader at `defense: 4`, which is a strange thing for a cooking
apron to be. Under a two-axis model both need moving across.

### A cliff to settle before plate exists

Damage reduction is **flat subtraction, not a percentage**:

```python
damage = max(1, damage - target_defense)
```

`gribbas_good_knife` deals `1d4+2` → 3–6 damage. Against anything with
`defense ≥ 2` that is `max(1, 3−3) = 1`. **Every knife attack against armor
becomes a guaranteed minimum-damage hit** — there is no gradient between "armor
helped a bit" and "armor erased the weapon." Whether DR is flat, percentage, or
damage-type-specific decides whether heavy armor is a *trade* or is simply
**strictly better**, because a flat reduction large enough to blunt a plate
armor will also erase a short sword, and then the evasion penalty is the only
thing standing between plate and being a no-brainer.

**Scope.** This is the smallest coherent shape of the mechanic: one new signed
item field (`evasion`), one subtraction on the attack side, `defense` relabelled
as DR, and the 13 existing items re-authored across both axes. It needs no new
armor-category taxonomy — the insulation-tagged garments already form the
light/medium/heavy continuum in embryo, and §57's category field is only needed
if the model later wants D&D's *exact* AC arithmetic rather than Tommy's
two-axis version.

## 59. Size exists as a trait — authored by nobody, and wired to exactly one thing (S1)

Tommy widened the frame past armor: *"think a tanks, a car, a dragon, a giant, a
spaceship, a worldconsuming leviathan, a fairy, a mouse, a 1cm long spider."*
That range is ~10 orders of magnitude, and it is the assumption D&D quietly
makes and this simulation breaks hardest: **every creature in 5e is roughly human
sized, which is why DEX/STR/AC can be small integers compared directly.**

### Correction to my own first reading

I first recorded this section as *"there is no scale axis anywhere."* **That was
wrong.** `engine/size.py` (task-187) already implements it:

```python
SIZE_TIERS = ["tiny", "small", "normal", "huge", "giant", "titanic"]
SIZE_DEFAULT = "normal"
def size_tier(player) -> int:      # from the player's size_* trait
```

Ways carry a `max_size` gate, and `movement.py:441-462` compares it against the
player's tier. Tommy was right that size is already a mechanical tag with a size
filter. The real problem is narrower and worse than "missing":

| question | answer |
|---|---|
| size tiers defined | **6** — tiny, small, normal, huge, giant, titanic |
| library characters carrying a `size_*` trait | **0 of 69** |
| world characters carrying a `size_*` trait | **0** |
| places `size_tier()` is called | **1** — `movement.py:453`, the way passage gate |
| size used in combat | **nowhere** |
| is the size authored anywhere at all | **no** |

So the scale axis is **built, documented, and consumed by passage gating — and
authored by nobody.** Every character in the repository silently resolves to
`normal`, which means the way `max_size` gate compares `2` against everything and
the tier system is inert in practice. That is the fifth appearance of this
audit's house pattern (§14 tags, §30 triggers, §54 roles/proficiency, §57 armor
categories, and now size).

### What the tiers are missing for combat

The tier list is a sound basis; it just stops at passage width. Two gaps:

**Size is a `trait`, not a character property.** `size_tier()` reaches into
`player.traits` and prefix-matches `size_`. That means size cannot be seen,
filtered, or authored from the character form — Tommy has already identified
where it should go: *"size might get a proper property on characters tied to the
graph editor character form work."* That is the right layer: a property is
visible and filterable, a prefixed trait key is neither.

**Nothing derives combat stats from size**, which is the point of the exercise.

### The stat scales already have canonical answers

D&D 5e publishes stat blocks that map almost exactly onto the six existing
tiers, so this is **authoring, not architecture**:

| tier | 5e example | STR | CON | HP |
|---|---|---|---|---|
| tiny | Rat, Sprite | 2–3 | 9–10 | 1–2 |
| small | Goblin | 8 | 10 | 7 |
| normal | Human commoner | 10–13 | 10–12 | 4–40 |
| huge | Ogre, Troll | 18–19 | 14–16 | 59–70 |
| giant | Hill Giant, Giant Ape | 21–23 | 16–21 | 105–157 |
| titanic | Ancient Black Dragon 27, **Tarrasque 45** | 27–45 | 22–25 | 256–675 |

So to Tommy's question — no, a leviathan should not be STR 9. A titanic-tier
creature is STR 27–45 and CON 22–25 with hundreds of HP.

**Nothing in the engine prevents that today.** There is no clamp on ability
scores anywhere: `engine/vitals.py:81 clamp()` bounds *vitals* (drives, 0–100),
not abilities. The only clamp in combat is on the derived *modifier*
(`combat.py:218,364` use `max(0, (STR-10)//2)`), which costs a high stat nothing —
STR 35 still yields +12. **STR 35 is storable today.** The gap is that no
character carries a size trait *or* a matching stat block, so every creature in
the repository is a 10-stat humanoid no matter how it is described.

### How this composes with §58

With a size axis, §58's two axes become scale-correct for free:

| | 1cm spider | mouse | fairy | human | giant | dragon | tank | leviathan |
|---|---|---|---|---|---|---|---|---|
| tier | tiny | tiny | small | normal | giant | titanic | huge | titanic |
| evasion (derived) | very high | high | medium | 0 | −1 | −3 | −1 | −3 |
| HP | 1 | 4 | 20 | 40 | 157 | 675 | 200 | 10⁴–10⁶ |
| attack damage | 0 | 0 | 1 | 3 | 12 | 60 | — | 10⁴ |

Two properties fall out, and both are reasons to want this:

**Evasion should be *derived* from size, not authored.** A 1cm spider should
carry no hand-written evasion value — it follows from being tiny. That removes
the authoring burden §58 would otherwise impose on every future creature and
every future garment.

**Damage and HP stay absolute, and that is what makes the extremes work.** A
mouse's 1 damage against a leviathan's 10⁶ HP is automatically and correctly
irrelevant — same code, same numbers, no special case. The 1cm spider becomes a
nuisance rather than a fight (unhittable *and* its damage rounds to nothing),
and a fairy against a mouse becomes a real fight, neither special-cased.

**The flat-DR problem from §58 becomes fatal at this scale.**
`damage = max(1, damage - target_defense)` has no scale-invariant answer:
subtracting `3` from a tank shell is noise, while subtracting `3` from a
1-damage spider bite hits the `max(1, …)` floor and does nothing. **Percentage
is the scale-invariant form** — 40% DR blunts a knife and a cannon equally.

**The one thing that still does not scale is the ability score itself.** `STR 9`
on a goblin and `STR 9` on a leviathan cannot both mean *can lift a car*. The
6 tiers and the 5e stat blocks solve this for 5e-sized differences, but a
leviathan vs a mouse is a larger gap than any published stat block covers, and
beyond `titanic` the model has no vocabulary left. That is the limit worth
naming before the tier list is treated as sufficient.

## 60. Correction, then three defects in the human-turn modal (S1)

### What I got wrong

Asked how an agent interacts with the world, I reasoned that the human player's
turn **was a no-op by design** — I selected `player_human_explorer`, clicked Step
Once, and the event stream grew by zero characters.

**That inference was wrong.** The turn happened. Its UI is not the event stream.
Stepping the human opens a full **compose modal** (`#htc-overlay` →
`#htc-modal`, z-index 1200, full-viewport, `pointer-events: auto`), which is
exactly why it swallowed the click and why the stream looked unchanged. I also
told Tommy the human has "no turn of its own," which is false.

**Why I didn't know:** because for the entire session I used `#command-input` —
the *"⚡ Override — engine command (verb + target, Tab completes)"* box. That is
**how I interact with the world**, and it bypasses the human-turn UI completely.
Everything I verified this session is the **engine's verb layer**, which the
human and NPC paths share. I exercised **zero** NPC turns — never watched the LLM
choose an action, never saw what a prompt contains, never saw the normalizer
mangle anything. The layer above the verb layer is the bulk of the simulation
and I had no evidence about it at all.

### What the modal actually is

`✈ player_human_explorer's turn` — area, description, then three clickable
lists, then vitals, then a composer:

> one turn = **do + say + emote together** · menus fill the draft

with `⚙ do` (action), `🗨 say` (say / whisper / shout / scream), `🎭 emote`
(body language), `🧠 memory`, `Act`, `interject ↩` ("quick reply… doesn't use
your turn"), `⏩ timeskip`, `⏭ end turn`, plus `▸ what you know`,
`▸ advanced`, `▸ raw json`.

The raw JSON field shows the shape it emits: `{"action":"take","item":"flour
sack"}`. **So the structured `where` that §55's fix depends on is authorable
here** — a human can target a body part through this modal in a way the ⚡
override's parser broke.

### Defect 1 — RETRACTED. Anonymous strangers are the design, not a bug

I originally wrote this as *"PEOPLE HERE resolves no names at all"* and called it a
defect. **That was wrong, and Tommy caught it.** These people are strangers to
`player_human_explorer`, so rendering them as `the woman` / `the man` is correct
— names are learned by talking to someone, which is what the `② react to the
result` phase and `interject ↩` exist for.

The gender mapping is verifiably **correct**, driven off the `male`/`female` tag:

| person | tag | rendered |
|---|---|---|
| Belne | `female` | the woman ✓ |
| Kiala | `female` | the woman ✓ |
| Eldenford Merchant | `male` | the man ✓ |

The error was mine and it is a specific one worth recording: the Agents sidebar
*does* render names, and the Alerts panel renders names ("Belne: Starving (90)"),
so I assumed the modal's gender-only labels were a failure to resolve. They are
the same information deliberately shown at a lower trust level. **I called a
mechanism broken without first establishing what it was for** — which is the
`AGENTS.md` discipline restated the hard way.

### Defect 1 (real) — three sources disagree on who is in the room

Once the anonymity question was settled, a genuine discrepancy remains:

| source | occupants of `Camp Entrance Trail` |
|---|---|
| `state.area_presence` | **2** — Belne, Eldenford Merchant |
| `Player` model `current_area` | **3** others — Belne, Kiala, Eldenford Merchant (+ self = 4) |
| human-turn modal | **5** buttons |

And the wider shape suggests which one is stale: **`area_presence` holds 5 entries
total for 23 players**, while **all 23 players carry a `current_area`**. Occupancy
counted from the `Player` model gives a coherent world (Cooking Area 3, Chief's
Pit 2, Eldenford 2, Deep Forest 2, Camp Entrance Trail 4, and 11 areas of 1–3).
So `area_presence` looks stale or vestigial — an occupancy index that no longer
tracks the `Player` records it shadows.

The modal's **5** is still unexplained: 2 women + 3 men against 2 women + 1 man
actually present. That is the open question, and it is worth chasing because the
modal is what the player acts on.

### Defect 2 — way labels leak raw way-node names, coordinates included

```
Camp Entrance Trail to Road (world 9,4)      north
Camp Entrance Trail to Road (world 9,6)      south
Camp Entrance Trail to Sparse Forest (world 10,5)   east
```

Six exits, and **every one is labelled with the raw `A to B` way-node name
including world coordinates**, with the usable cardinal on a second line. This is
the same defect as §11 — coordinates baked into a name — but in the *primary
movement UI* of a human turn rather than in a peripheral list, so it is the worse
instance. Tommy has already flagged §11 as a mistake; this is the same mistake
in the place it costs the most. The player reads `north`; they should never have
to read `Road (world 9,4)`.

### Also observed

`CARRYING —` and `WEARING —` are both empty for `player_human_explorer`, with
`⚖️ barely carrying anything`. Consistent with §57/§58: the human has no
equipment, so the armor and evasion work has no live subject on the player side
either.

## 61. The mistake is the finding: derived values render indistinguishably from authoritative ones (S1, design)

Defect 1 above was a false positive — strangers correctly render as `the woman`
/ `the man`. That retraction is the more useful result, and the reason is worth
stating plainly rather than filing as a closed error.

**A competent reader, who had just worked out how to play the game, read the
primary human-facing screen as broken.** That is not an isolated lapse. It is
evidence that the UI states a fact without stating its *epistemic status*.

The modal renders five strangers as `the woman` / `the man` and signals
**nothing** about any of this:

- that these are people you have not met
- that their names exist and you do not know them
- that talking to them will reveal them
- that the knowledge persists and will render differently next turn

So anonymity is indistinguishable from a failed name lookup. A player cannot tell
"working as intended" from "this system did not load the names" — **and neither
could I, from the screen, until asked.**

### The generalisation

This is the same class as the eight DOM-vs-pixel disagreements already recorded
in this audit. Every one of those is also a legibility failure: the DOM said one
thing, the rendered page another, and nothing indicated which to believe. One
root cause covers both:

> **A derived value is rendered indistinguishably from an authoritative one.**

That is the presentation-layer twin of the `AGENTS.md` rule that a runtime-derived
value must not become persisted authoring data. The leak runs the other way
here: a *derived* display — "the woman", resolved from a `female` tag and
filtered by presence — is presented with the same authority as a resolved
identity, so nothing tells the player which layer is speaking.

It runs through the whole turn modal:

| rendered | actually derived from | tells the player |
|---|---|---|
| `the woman` (×2) | `female` tag + presence, **two different people** | nothing |
| `the man` (×3) | `male` tag + presence | nothing |
| `Camp Entrance Trail to Road (world 9,4)` | raw way-node name | that this is generated, not a name |
| `CARRYING —` | inventory that may be stale | nothing |
| `⚖️ barely carrying anything` | derived weight band | nothing |

Contrast this with a surface that *does* declare itself: the graph editor shows
node ids and display names as separate fields, and `AGENTS.md` insists that node
identity is opaque with names as a resolution layer. **The data model is careful
about this distinction. The UI mostly is not.**

### What the fix actually is

Not a label on every field. Each derived surface should **declare itself** — a
"people you haven't met" heading, a marker on unresolved people, an indicator
that a way label is generated. That is the same discipline as naming a source of
truth, applied to pixels instead of code.

### Why this is the most useful finding in the audit

It is the only one that **predicts** rather than records. Every surface I
misread this session — the eight DOM disagreements, the "no-op turn", the
"broken names" — was a surface showing a fact without showing where the fact
came from. That is a testable prediction about surfaces I have not reached yet:
Scenario Manager, Soak Lab, Timeskip, the remaining Settings tabs, tag
management, embeddings. Filed as **task-608** precisely so the next audit pass
checks that prediction rather than rediscovering it.


