/**
 * help-center.js — Help, coach tips and guided tours (HelpCenter).
 *
 * A contextual learning layer: a curated tip registry, event/click-driven
 * "smart" triggers, a spotlight that physically highlights the UI the tip
 * talks about, guided tours (ordered tip chains), and a Help index modal
 * (❓ top bar / F1).
 *
 * Triggers:
 *   - appEvents 'inspector:view' (area/item/way/agent views)
 *   - clicks on elements carrying [data-help] (settings, game menu, run…)
 *   - first 'state:updated' after load (welcome)
 *
 * State: per-tip seen flags stored in localStorage (key vw_help_seen_v1),
 * plus a session-scoped set so tips can re-appear on the next run but not
 * while you're clicking around.
 *
 * Load AFTER event-bus.js (mandatory), any time before user interaction.
 *
 * @module ui/help-center — help, coach tips, and guided tours
 * @contributes HelpCenter: tip registry, smart triggers, spotlight, tours, and the Help index modal
 * @powers the contextual onboarding layer (❓ top bar / F1)
 * @relates listens on appEvents 'inspector:view' + [data-help] clicks; seen flags in localStorage
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */

window.HelpCenter = (() => {
    'use strict';

    const STORAGE_KEY = 'vw_help_seen_v1';

    // ─────────────────────── Tip registry ───────────────────────
    // event: 'inspector:view' | 'data-help' | 'state:updated'
    // match: optional (detail) => bool gate
    // target: optional CSS selector for the [Show me] spotlight
    // tour: optional tour id (which ordered chain this tip belongs to)
    // once: 'session' (default — re-shows next session) | 'global'
    const TIPS = [
        {
            id: 'welcome',
            tour: 'hello',
            event: 'state:updated',
            once: 'session',
            group: 'Beginner',
            title: 'Welcome to VirtualWorld',
            body: 'This is your world. <b>▶</b> runs the sim for the agent you have selected — it thinks, speaks and acts, turn after turn. Switch on <b>Turn-Based Mode</b> (Agent Settings) and every character rotates in initiative order instead. <b>F1</b> (or ❓ up top) reopens this Help Center.',
            target: '#sim-play',
        },
        {
            id: 'run-sim',
            tour: 'hello',
            event: 'data-help',
            match: d => d === 'run',
            group: 'Beginner',
            title: 'Running the simulation',
            body: 'By default <b>▶</b> runs only the <b>selected</b> agent, one turn at a time (click an agent in the left panel to choose who). <b>Turn-Based Mode</b> in Agent Settings rotates <i>every</i> character in initiative order — the left panel shows who is up. Either way: click any agent to inspect its vitals, thoughts and gear.',
            target: '#sim-play',
        },
        {
            id: 'agent-settings',
            tour: 'hello',
            event: 'data-help',
            match: d => d === 'settings',
            group: 'Beginner',
            title: 'Agent settings live here',
            body: 'The fun switches: <b>🔁 Auto-Retry Invalid Actions</b>, <b>🌊 Simultaneous Mode</b> (experimental, chaos by design), ghost mode, models, and rate limits. Save persists per profile.',
            target: '#settings-modal',
        },
        {
            id: 'game-menu',
            tour: 'hello',
            event: 'data-help',
            match: d => d === 'game-menu',
            group: 'Beginner',
            title: 'The Game menu',
            body: '<b>Commit Scenario</b> writes your live world into the scenario source so <b>Restart</b> keeps your work. Save/Load, Import, and New Scenario (the wizard) all live here too.',
        },
        {
            id: 'inspector-agent',
            event: 'inspector:view',
            match: d => d && d.type === 'agent',
            group: 'Beginner',
            title: 'The character inspector',
            body: 'Inventory (paperdoll + carry load + gear totals), Bio (personality, appearance, relationships, <b>🧪 Recipes</b>), Advanced (skills, behaviors, knowledge). Vitals are clickable for natural-language details.',
            target: '.inspector-tabs',
        },
        {
            id: 'inspector-area',
            tour: 'scenario',
            event: 'inspector:view',
            match: d => d && d.type === 'area',
            group: 'World building',
            title: 'Room inspector',
            body: 'Environment (light/temp/air/smell/noise), description, and the items here. Area <b>tags</b> drive what spawns in it (store, restaurant, haunted…).',
        },
        {
            id: 'inspector-item',
            tour: 'triggers',
            event: 'inspector:view',
            match: d => d && d.type === 'item',
            once: 'session',
            group: 'Items & triggers',
            title: 'Items grow with their tags',
            body: 'Add <b>armor/clothing</b> → the Defense field appears; <b>weapon</b> → damage fields; <b>food</b> → eat; <b>container</b> → capacity; <b>toggleable</b> → its controls. Newer mechanics: set <b>max_uses</b> for durability (weight scales), <b>perishable</b> for freshness, <b>proximity_effect</b> for EMF-style reads. <b>Consumables spend themselves</b>: eating or drinking auto-decrements <b>uses</b> after its triggers fire, so authored food/drink content must not spend a use by hand — leave the counter to the engine or it double-decrements.',
        },
        {
            id: 'inspector-way',
            event: 'inspector:view',
            match: d => d && d.type === 'way',
            group: 'World building',
            title: 'Way inspector — doors and special paths',
            body: 'State (open/closed/locked/blocked), see-through views, <b>requires</b> (crawl/climb/jump), <b>max_size</b>, and the new <b>requires_item</b> gate — write "bike" or "tag:fly" and only the right gear gets through.',
        },
        {
            id: 'overlays',
            event: 'data-help',
            match: d => d === 'overlays',
            group: 'World building',
            title: 'Overlays show the invisible',
            body: '<b>Light / Heat / Sound / Triggers / Cardinal</b> paint environment data straight onto the map — great for debugging why a room is dark or a rumor got heard.',
            target: '#btn-overlays',
        },
        {
            id: 'more-tools',
            tour: 'triggers',
            event: 'data-help',
            match: d => d === 'more',
            group: 'World building',
            title: 'The More menu',
            body: 'Rarely-used tools: <b>📋 Templates</b> (the {param:…} reference), 🌍 Lore, graph Legend, Tags panel, Sync to Library, and printing the world.',
            target: '[title="More graph tools"]',
        },
        {
            id: 'trigger-system',
            tour: 'triggers',
            event: 'data-help',
            match: d => d === 'triggers',
            group: 'Items & triggers',
            title: 'The trigger system is the engine of surprise',
            body: '<b>trigger_type</b> decides when (on_use, on_speech, on_break…), <b>conditions</b> gate it (uses, tags, has_item…), <b>effects</b> do the work (spawn, set_state, scry, llm_respond…). And <b>every effect has a template item</b> — search the library for "Template:" to see one live.',
        },
        {
            id: 'snippets',
            tour: 'triggers',
            event: 'data-help',
            match: d => d === 'snippets',
            group: 'Items & triggers',
            title: 'Trigger snippets',
            body: 'In the trigger editor, <b>snippets</b> fill a whole trigger in one click — Chest, Light Source, Heat Source, First Aid, Whispering Door, Recorder. Ctrl+K finds anything.',
        },
        {
            id: 'nl-editor',
            event: 'data-help',
            match: d => d === 'nl-editor',
            group: 'World building',
            title: 'Natural-Language Editor Mode (Cmd+L / Ctrl+L)',
            body: 'Author and modify the world conversationally. The agent searches the library first, inspects the live world, stages all mutations into a local buffer for review, and applies everything in one undo-safe transaction.',
            target: '[data-tab="nl-editor"]',
        },
        {
            id: 'simultaneous',
            event: 'data-help',
            match: d => d === 'simultaneous',
            group: 'Advanced',
            title: '⚠️ The simultaneous turn modes are experimental',
            body: '<b>Sequential</b> / <b>Random</b> / <b>Initiative</b> walk the turn queue in that order (Turn-Based Mode). <b>Simultaneous</b> ignores the queue entirely: every autonomous character acts on its own countdown — <b>Social</b> speeds it up, exhaustion and patient/sprinter traits shift it. <b>Simultaneous per room</b> applies that per area: rooms resolve independently, while characters inside a room still act in order. The human never auto-acts — you play manually while NPCs run on their own cadence. Expect chaos, overlapping drama, and happy accidents.',
        },
        // ── newer systems (task-521) ────────────────────────────────────────
        {
            id: 'turn-model',
            event: 'data-help',
            match: d => d === 'turn-model',
            group: 'Advanced',
            title: 'Time, turns and travel',
            body: 'One <b>turn</b> is roughly one in-game minute, and a character gets <b>one decision set per turn</b> no matter how the clock is configured — <b>time_per_tick_minutes</b> changes how much world time a tick advances, never how many actions you get. Travelling from one area to the next costs at least one turn per cell crossed, so a long road is a real cost. Ticks and decay run <b>once per cycle</b>, when the last actor of a round passes — not inside each action.',
            target: '[data-help="turn-model"]',
        },
        {
            id: 'background-sim',
            event: 'data-help',
            match: d => d === 'background-sim',
            group: 'Advanced',
            title: 'The world keeps moving without you',
            body: 'Characters you are not watching still act on their own schedule: hunger, moods and NPC decisions advance off-screen as the clock ticks. Scopes let you decide what is <b>attended</b> — promote a scope to load its characters into the live rotation, or leave it demoted and quiet. The agent card shows whom the sim is currently running; <b>Turn-Based Mode</b> is the only thing that pauses everyone to wait for you.',
            target: '[data-help="background-sim"]',
        },
        {
            id: 'auto-description',
            event: 'data-help',
            match: d => d === 'auto-description',
            group: 'Advanced',
            title: 'Descriptions regenerate from gear',
            body: 'The visible description is <b>derived</b> from the base description plus what the character is wearing, so it refreshes on its own after an equip/unequip or a body-state change. This button forces a fresh one. If you hand-write a description, remember the next equipment change can overwrite it — put lasting facts in the <b>Base Description</b> instead.',
            target: '[data-help="auto-description"]',
        },
        {
            id: 'autodress',
            event: 'data-help',
            match: d => d === 'autodress',            group: 'Items & triggers',
            title: 'Auto-Dress from Interests',
            body: 'The character\'s LLM picks an outfit for them from the wearable items in the library, judging who they are rather than which tags overlap. Weather-aware, and never replaces gear they are already wearing. Without an LLM configured it falls back to matching <b>interest_tags</b> only — which often picks nothing sensible, since it cannot tell a blacksmith from a farmer. Empty interests? Use <b>✨ Generate from Personality</b> in Bio to let the character pick its own tags.',
        },
        {
            id: 'crafting',
            event: 'data-help',
            match: d => d === 'craft',
            group: 'Items & triggers',
            title: 'Crafting recipes',
            body: 'Recipes are graph nodes (type: <b>recipe</b>). Use/make <b>&lt;recipe&gt;</b> once learned: global, skill:, item:, or discoverable on first craft — and <b>teach</b> them to others.',
        },
        {
            id: 'duplicate',
            tour: 'scenario',
            event: 'data-help',
            match: d => d === 'duplicate',
            group: 'World building',
            title: 'Duplicate clones children — not parents',
            body: 'Duplicating the table also clones the salt <i>on</i> it, but the kitchen it sits in stays shared. Parents are never cloned; attached children are.',
        },
        {
            id: 'worldpainter',
            tour: 'world',
            event: 'data-help',
            match: d => d === 'worldpainter',
            group: 'World building',
            title: '🗺️ WorldPainter — paint a world, then compile it',
            body: '<b>Root then zone</b>: the first scope you create is the world root; add a child zone (a forest, town, or floor) and drill in to detail it. Paint the <b>biome</b>, <b>road</b> and <b>floor</b> layers — drag to paint, or use the <b>🧭 Route</b> tool (1 cell = 1 turn, so 240 cells = 4&nbsp;h). <b>Floor is a storey number</b>: 0 is ground, 1 one up, -1 one down, and it goes as far as you like (3 for a room three storeys up, 80 for a tower, -900 for a hole to hell). Load a map image as a reference with <b>▦ match</b>. <b>⚙ Generate is per scope</b>: compile the root and each zone separately, so the root stays coarse and zones hold the detail — no single generate mints thousands of rooms at once. <b>Two things the painter will not tell you</b>: every painted cell is a place but it must be <b>named</b> to be addressable (right-click → name), and a scope made with <b>🪜 Make this a scope…</b> is baked and can never be generated — <b>➕ Add feature…</b> is the one that makes a paintable scope. Open the painter and press <b>📋 what next</b> for the order your scope needs.',
            target: '[data-help="worldpainter"]',
            tour: 'world',
        },
        {
            id: 'scope-filter',
            tour: 'world',
            event: 'data-help',
            match: d => d === 'scope-filter',
            group: 'World building',
            title: '🌍 Load one scope at a time',
            body: 'A densely painted world is thousands of rooms, which freezes the graph. Pick a <b>world scope</b> here to load only that zone into the canvas (its rooms, ways and characters). <b>Whole world</b> restores everything, and switching scenarios rebuilds the list.',
            target: '#graph-scope-filter',
        },

        // ── WorldPainter, in-editor (task-521) ─────────────────────────────
        // The launcher tip above explains the system. These explain the
        // controls, and — more usefully — the things the controls will not tell
        // you: which layer a wall goes on, why a name matters, what a scope made
        // by promoting areas can never do, and in what order a town is painted.
        {
            id: 'help',
            event: 'data-help',
            match: d => d === 'help',
            group: 'Beginner',
            title: '❓ Help, coach tips and tours',
            body: 'This is the whole learning layer. Coach cards appear by themselves as you touch things for the first time, and <b>F1</b> reopens this index at any time. Every tip can be re-shown individually with <b>again</b>, and <b>Reset all</b> forgets every seen-flag so the tour runs again from the start. The <b>guided tours</b> at the top chain the cards into a walkthrough — <i>Painting a town</i> is the WorldPainter one.',
            target: '[data-help="help"]',
        },
        {
            id: 'wp-checklist',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-checklist',
            group: 'WorldPainter',
            title: '📋 What next',
            body: 'The order a scope of this <b>mode</b> needs, with live progress — a <b>world</b> is coarse ground and roads, a <b>town</b> is ground → streets → walls → gates → buildings → <b>names</b>, an <b>interior</b> is rooms → doors → storeys → names. The ticks are read off your actual paint, not remembered, so they cannot claim something is done when it is not.',
            target: '[data-help="wp-checklist"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-blockers',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-blockers',
            group: 'WorldPainter',
            title: '⚠ Why this scope will not compile',
            body: 'Everything here is a condition <b>⚙ Generate</b> refuses, listed with the fix <i>before</i> you press it. The common one: a scope made with <b>🪜 Make this a scope…</b> is <b>baked</b> — it was promoted from areas you had already written, so it is authored rather than painted and has nothing to compile. Delete it and use <b>➕ Add feature…</b>, which starts empty; the promoted areas are released back to unplaced and keep their contents. The other: a scope sitting on an <b>unpainted</b> cell of its parent will never get a gateway, so paint that cell or move it.',
            target: '[data-help="wp-blockers"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-grid',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-grid',
            group: 'WorldPainter',
            title: '▦ Grid — one cell is one minute',
            body: 'The grid size <b>is</b> the size of the place: a cell is a minute of walking, and a journey costs one cell per step however you travel. So 30×20 means crossing the place takes ~20 turns. Width is what you choose and height follows the reference image\'s aspect. <b>Shrinking the grid prunes</b> paint and placed areas that fall outside it, so the count is confirmed first.',
            target: '[data-help="wp-grid"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-layer',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-layer',
            group: 'WorldPainter',
            title: 'The four layers',
            body: '<b>biome</b> — what the place <i>is</i>: terrain, and also buildings, rooms, walls and doors. <b>road</b> — road, bridge, ford, gate, tunnel. A road cell <b>replaces</b> the biome rather than layering over it, and the biome survives underneath as description context. <b>floor</b> — a <i>storey number</i>, not a material: 0 ground, 1 up, -1 down, unbounded. <b>climate</b> — compiles on <b>world</b> scopes only.',
            target: '[data-help="wp-layer"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-value',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-value',
            group: 'WorldPainter',
            title: 'There is no building layer',
            body: 'Buildings are <b>biomes</b> — <i>Inn</i>, <i>Tavern</i>, <i>Smithy</i>, <i>Cottage</i>, <i>Town Hall</i> — one cell each in the Buildings section of this list, as are <i>Wall</i>, <i>Door</i> and <i>Window</i>. <b>Walls and doors are structure</b>: they never become places, and that is exactly what makes a wall a wall. A building cell also gets an <b>in</b> way from every side that already has a way, so you type <i>in</i> rather than stepping onto the doorstep.',
            target: '[data-help="wp-value"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-brush',
            event: 'data-help',
            match: d => d === 'wp-brush',
            group: 'WorldPainter',
            title: 'Brush size',
            body: 'Each click paints an N×N block. A big brush is the difference between a forest taking 8 clicks and 800 — use it for ground, and 1×1 for buildings, where a single stray cell is a house.',
            target: '[data-help="wp-brush"]',
        },
        {
            id: 'wp-add-feature',
            event: 'data-help',
            match: d => d === 'wp-add-feature',
            group: 'WorldPainter',
            title: '➕ Add feature — it makes, it does not place',
            body: 'Asks for a name, then creates an <b>empty child scope</b> and selects it. It does <b>not</b> put it anywhere: pick <b>🏠 Feature</b> and click the cell it belongs on. The mode follows the parent — a child of a <i>town</i> is an <i>interior</i> — and the grid starts at 8×8, which you then resize. This is also the <b>only</b> way to make a scope you can paint: <b>🪜 Make this a scope…</b> promotes areas you already wrote and gives you a scope that can never be generated.',
            target: '[data-help="wp-add-feature"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-generate',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-generate',
            group: 'WorldPainter',
            title: '⚙ Generate — per scope, parent first',
            body: 'Turns <b>this scope\'s</b> painted cells into real areas and ways. Do it <b>last</b>, and generate the <b>parent before its children</b>: the gateway between a scope and its parent is minted by whichever of the two compiles second. A scope that is already generated asks before redoing it, and a redo replaces anything edited by hand afterwards. Do not paint a scope after generating it — see the blockers tip.',
            target: '[data-help="wp-generate"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-ungenerate',
            event: 'data-help',
            match: d => d === 'wp-ungenerate',
            group: 'WorldPainter',
            title: '🧹 Ungenerate',
            body: 'Deletes this scope\'s generated nodes but <b>keeps</b> its paint, reference and placements, so you can change the paint and generate a clean slate. Refused on a scope that was authored rather than generated — there is nothing of the compiler\'s there to remove.',
            target: '[data-help="wp-ungenerate"]',
        },
        {
            id: 'wp-merge',
            event: 'data-help',
            match: d => d === 'wp-merge',
            group: 'WorldPainter',
            title: 'merge same-biome — a default, not the rule',
            body: 'On, a run of like cells becomes <b>one</b> place: a street is one road, a field is one field. But this is only the <b>default</b> — <b>buildings never merge</b> (a terrace stays a terrace) and <b>corridors and hallways always do</b>, so turning it off to separate cottages does not shred a hallway into ten rooms.',
            target: '[data-help="wp-merge"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-estimate',
            event: 'data-help',
            match: d => d === 'wp-estimate',
            group: 'WorldPainter',
            title: 'What this grid will compile to',
            body: 'The node cost, so painting 5,000 cells cannot surprise you with a 15,000-node graph. <b>🔗 n linked</b> means n painted islands with no painted neighbour; each is joined to the nearest painted cell with a single way rather than being walled off. It is an order-of-magnitude warning, not a promise — it does not model walls or the merge rules, so it counts cells that will not become places.',
            target: '[data-help="wp-estimate"]',
        },
        {
            id: 'wp-paint-interior',
            event: 'data-help',
            match: d => d === 'wp-paint-interior',
            group: 'WorldPainter',
            title: '🏠 Paint an interior',
            body: 'Paints a building type\'s stock floor plan in as cells — a tavern gets a tap room, kitchen and cellar. It is a <b>draft</b>: edit the cells, move the walls, then <b>⚙ Generate</b> this scope. Only on an <i>interior</i> scope, deliberately: rooms painted onto a world map is a thing a wall grid already says.',
            target: '[data-help="wp-paint-interior"]',
        },
        {
            id: 'wp-reference',
            event: 'data-help',
            match: d => d === 'wp-reference',
            group: 'WorldPainter',
            title: 'The reference image is a guide, not data',
            body: 'The art never reaches the graph — only your painted cells do. Load one, then <b>▦ match</b> so the grid takes the image\'s aspect and a cell means the same place in both. The slider next to <b>match</b> is the <i>paint</i> opacity, so the art reads through your colour; the slider after it dims the art itself. Changing the image later resets the adjust rect, so re-match it.',
            target: '[data-help="wp-reference"]',
        },
        {
            id: 'wp-reference-adjust',
            event: 'data-help',
            match: d => d === 'wp-reference-adjust',
            group: 'WorldPainter',
            title: '✥ adjust — nudge the picture onto the grid',
            body: 'Drag to move, corners to resize, edges to crop. The rectangle is stored in <b>cell units</b>, so the graph map lays out with the same geometry. Use it when the art is offset from the cells you have already painted rather than re-matching and re-painting.',
            target: '[data-help="wp-reference-adjust"]',
        },
        {
            id: 'wp-tool-select',
            event: 'data-help',
            match: d => d === 'wp-tool-select',
            group: 'WorldPainter',
            title: '⬚ Select — the one that makes the others bulk',
            body: 'Click, shift-click, drag for a marquee, Ctrl+A for all. With cells selected, <b>Paint</b> and <b>Erase</b> apply to the whole selection in a single request — which is how a hundred cells get changed without a hundred undos.',
            target: '[data-help="wp-tool-select"]',
        },
        {
            id: 'wp-tool-paint',
            event: 'data-help',
            match: d => d === 'wp-tool-paint',
            group: 'WorldPainter',
            title: '🖌 Paint',
            body: 'Paints the current <b>layer</b> and <b>value</b> where you drag. The observer view: <b>every painted cell is a place</b>, so an unpainted cell simply is not there, and a road-only cell is a road just as much as a forest cell is a forest.',
            target: '[data-help="wp-tool-paint"]',
        },
        {
            id: 'wp-tool-erase',
            event: 'data-help',
            match: d => d === 'wp-tool-erase',
            group: 'WorldPainter',
            title: '🧽 Erase',
            body: 'Clears the <b>current layer</b> on a cell — so erasing while a biome layer is active leaves any road underneath, which is usually what you want. It does not touch names, so a place can lose its paint and keep its name until you clear that too.',
            target: '[data-help="wp-tool-erase"]',
        },
        {
            id: 'wp-tool-move',
            event: 'data-help',
            match: d => d === 'wp-tool-move',
            group: 'WorldPainter',
            title: '✥ Move',
            body: 'Shifts the selected cells\' contents one cell, with arrow keys, WASD or the nudge buttons. One request, one undo — this is the tool for nudging a mis-placed cell rather than erasing and repainting it.',
            target: '[data-help="wp-tool-move"]',
        },
        {
            id: 'wp-tool-route',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-tool-route',
            group: 'WorldPainter',
            title: '🧭 Route — a road in a few clicks',
            body: 'Click waypoints, then <b>✓ Paint route</b> to fill the current layer along the line, widened by the brush. The status line reports the result as distance too, because <b>1 cell = 1 turn = 1 minute</b>: 240 cells is 4&nbsp;h on foot. Use it for a long street rather than dragging along it.',
            target: '[data-help="wp-tool-route"]',
            tour: 'paint-a-town',
        },
        {
            id: 'wp-tool-feature',
            event: 'data-help',
            match: d => d === 'wp-tool-feature',
            group: 'WorldPainter',
            title: '🏠 Feature — a sub-zone, not a road',
            body: 'Places a child scope on a cell: a town inside a world, a room inside a town. Roads, bridges and gates are <b>painted on the road layer</b> and are not features. One child per cell, and a cell already holding a hand-placed area refuses one.',
            target: '[data-help="wp-tool-feature"]',
        },
        {
            id: 'wp-tool-area',
            event: 'data-help',
            match: d => d === 'wp-tool-area',
            group: 'WorldPainter',
            title: '📍 Area — park somewhere you already wrote',
            body: 'Puts an area that exists in the graph (a hand-written district, a named ruin) onto a cell of this map. <b>Generate will not put a second area on that cell</b>, so the two never collide. Only hand-authored areas can be moved this way — a generated one belongs to its Generate.',
            target: '[data-help="wp-tool-area"]',
        },
        {
            id: 'wp-tool-inspect',
            tour: 'paint-a-town',
            event: 'data-help',
            match: d => d === 'wp-tool-inspect',
            group: 'WorldPainter',
            title: '🔍 Inspect — and right-click does this on any tool',
            body: 'Reads a cell without changing it: what is painted on each layer, which area or child scope sits there, and its <b>name</b> field. Right-click works the same panel from <b>any</b> tool, so you can name a cell without switching. A place with no name compiles to coordinates like "Inn (Eldenford 12,7)" and cannot be asked for by name — "go inn" has nothing to match.',
            target: '[data-help="wp-tool-inspect"]',
            tour: 'paint-a-town',
        },
    ];

    // Guided tours: ordered chains of tip ids.
    const TOURS = {
        hello: { title: 'First five minutes', group: 'Beginner', steps: ['welcome', 'run-sim', 'agent-settings', 'game-menu'] },
        triggers: { title: 'Triggers & effects', group: 'Items & triggers', steps: ['inspector-item', 'trigger-system', 'snippets', 'more-tools'] },
        scenario: { title: 'Scenario workflow', group: 'World building', steps: ['game-menu', 'duplicate', 'inspector-area'] },
        world: { title: 'Painting a world', group: 'World building', steps: ['worldpainter', 'scope-filter', 'inspector-area'] },
        'paint-a-town': { title: 'Painting a town', group: 'WorldPainter', steps: ['wp-checklist', 'wp-grid', 'wp-layer', 'wp-tool-route', 'wp-value', 'wp-tool-inspect', 'wp-blockers', 'wp-generate'] },
    };

    // ─────────────────────── State ───────────────────────
    let _seen = new Set();
    try {
        _seen = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'));
    } catch (e) { /* fresh */ }
    const _sessionSeen = new Set();
    let _current = null;        // active tip object
    let _tourQueue = [];        // remaining tips of a running tour
    let _timer = null;

    // ─────────────────────── Storage ───────────────────────
    function _markSeen(id) {
        _sessionSeen.add(id);
        const tip = TIPS.find(t => t.id === id);
        if (tip && tip.once === 'global') {
            _seen.add(id);
            try { localStorage.setItem(STORAGE_KEY, JSON.stringify([..._seen])); } catch (e) { /* ignore */ }
        }
    }

    function _isSeen(id) {
        return _seen.has(id) || _sessionSeen.has(id);
    }

    // ─────────────────────── Spotlight ───────────────────────
    let _spot = null;
    function _clearSpotlight() {
        if (_spot) { _spot.remove(); _spot = null; }
    }
    function spotlight(selector) {
        _clearSpotlight();
        let el = null;
        try { el = document.querySelector(selector); } catch (e) { el = null; }
        if (!el) return false;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const rect = el.getBoundingClientRect();
        _spot = document.createElement('div');
        _spot.style.cssText = 'position:fixed;inset:0;z-index:2147483000;pointer-events:none;';
        // dim mask with a cut-out around the element (box-shadow trick)
        const mask = document.createElement('div');
        mask.style.cssText = `position:absolute;left:${rect.left - 8}px;top:${rect.top - 8}px;width:${rect.width + 16}px;height:${rect.height + 16}px;border-radius:8px;
            box-shadow:0 0 0 200vmax rgba(0,0,0,0.55), 0 0 0 3px var(--accent, #79c0ff), 0 0 28px rgba(121,192,255,0.55);`;
        _spot.appendChild(mask);
        document.body.appendChild(_spot);
        return true;
    }

    // ─────────────────────── Coach card ───────────────────────
    let _card = null, _cardHost = null;
    function _ensureStyles() {
        if (document.getElementById('hc-styles')) return;
        const style = document.createElement('style');
        style.id = 'hc-styles';
        style.textContent = `
            .hc-card { position:fixed; right:18px; bottom:18px; z-index:2147483001; width:min(360px, calc(100vw - 36px));
                background:#171b22; border:1px solid #333a45; border-left:3px solid #79c0ff; border-radius:10px;
                padding:12px 14px; box-shadow:0 14px 44px rgba(0,0,0,.6); font-size:12.5px; color:#e6e8ee; line-height:1.5; }
            .hc-card h4 { margin:0 0 6px; font-size:13px; color:#79c0ff; }
            .hc-card .hc-body { color:#c4ccd6; }
            .hc-card .hc-body b, .hc-card .hc-body i { color:#e6e8ee; }
            .hc-card .hc-actions { display:flex; gap:6px; margin-top:10px; align-items:center; }
            .hc-card button { font-size:11px; padding:3px 10px; border-radius:6px; border:1px solid #444c58; background:#20252e; color:#e6e8ee; cursor:pointer; }
            .hc-card button:hover { border-color:#79c0ff; color:#79c0ff; }
            .hc-card .hc-showme { background:#1a2c42; border-color:#2a5580; color:#9cd0ff; }
            .hc-card .hc-dismiss { margin-left:auto; background:transparent; border:none; color:#5b6570; }
            .hc-modal { position:fixed; inset:0; z-index:2147483002; background:rgba(0,0,0,.55); display:flex; align-items:center; justify-content:center; }
            .hc-modal-inner { width:min(560px, 94vw); max-height:86vh; overflow:auto; background:#171b22; border:1px solid #333a45; border-radius:12px; padding:18px 20px; color:#e6e8ee; font-size:13px; }
            .hc-modal h3 { margin:0 0 4px; }
            .hc-modal .hc-tour { border:1px solid #333a45; border-radius:8px; padding:10px 12px; margin:8px 0; background:#1b2028; }
            .hc-modal .hc-tour button { float:right; }
            .hc-modal .hc-tiprow { display:flex; justify-content:space-between; gap:8px; padding:4px 2px; border-bottom:1px solid #262c36; font-size:12px; }
            .hc-modal .hc-tiprow .done { color:#3fb950; }
            .hc-modal button { font-size:11px; padding:3px 10px; border-radius:6px; border:1px solid #444c58; background:#20252e; color:#e6e8ee; cursor:pointer; margin-left:6px; }
            .hc-reset { color:#f85149; }
        `;
        document.head.appendChild(style);
    }

    function _closeCard() {
        if (_timer) { clearTimeout(_timer); _timer = null; }
        if (_card) { _card.remove(); _card = null; }
    }

    function _nextTourStep() {
        const id = _tourQueue.shift();
        if (!id) return;
        const tip = TIPS.find(t => t.id === id);
        if (tip) {
            _show(tip, true);
        } else {
            _nextTourStep();
        }
    }

    function _show(tip, fromTour) {
        if (!tip || (tip.once === 'global' && _seen.has(tip.id))) return;
        if (_sessionSeen.has(tip.id)) return;
        _closeCard();
        _ensureStyles();
        _markSeen(tip.id);

        _card = document.createElement('div');
        _card.className = 'hc-card';
        const hasTarget = !!tip.target;
        _card.innerHTML = `
            <h4>💡 ${tip.title}</h4>
            <div class="hc-body">${tip.body}</div>
            <div class="hc-actions">
                ${hasTarget ? '<button class="hc-showme">Show me</button>' : ''}
                <button class="hc-gotit">${fromTour ? 'Next' : 'Got it'}</button>
                <button class="hc-dismiss" title="Don\'t show this tip again">✕</button>
            </div>`;
        _card.addEventListener('click', (e) => {
            if (e.target.classList.contains('hc-showme')) {
                spotlight(tip.target);
            } else if (e.target.classList.contains('hc-gotit')) {
                _closeCard();
                if (fromTour && _tourQueue.length) _nextTourStep();
            } else if (e.target.classList.contains('hc-dismiss')) {
                _seen.add(tip.id);
                try { localStorage.setItem(STORAGE_KEY, JSON.stringify([..._seen])); } catch (err) { /* ignore */ }
                _closeCard();
            }
        });
        document.body.appendChild(_card);
        // gentle auto-hide (not during tours)
        if (!fromTour) {
            _timer = setTimeout(() => { if (_card && !_card.matches(':hover')) _closeCard(); }, 16000);
        }
        if (fromTour && tip.target) spotlight(tip.target);
    }

    // ─────────────────────── Triggers ───────────────────────
    function maybe(eventName, detail) {
        if (_tourQueue.length) return; // tours own the screen
        for (const tip of TIPS) {
            if (tip.event !== eventName) continue;
            if (_isSeen(tip.id)) continue;
            if (tip.match && !tip.match(detail)) continue;
            // de-dupe: at most one coach card at a time
            _show(tip, false);
            return;
        }
    }

    function startTour(tourId) {
        const tour = TOURS[tourId];
        if (!tour) return;
        _closeCard();
        _clearSpotlight();
        _tourQueue = tour.steps.filter(id => !_sessionSeen.has(id));
        if (!_tourQueue.length) { _tourQueue = [...tour.steps]; }
        _nextTourStep();
    }

    // modal close helper (used by inline buttons)
    function _closeModal() {
        const m = document.getElementById('hc-modal');
        if (m) m.remove();
    }

    function openIndex() {
        _closeCard();
        _ensureStyles();
        const m = document.createElement('div');
        m.className = 'hc-modal';
        m.id = 'hc-modal';
        const toursHtml = Object.entries(TOURS).map(([id, t]) => `
            <div class="hc-tour"><b>${t.title}</b> <span style="color:#5b6570;">(${t.steps.length} steps)</span>
                <button onclick="HelpCenter.startTour('${id}');HelpCenter._closeModal()">▶ Start</button>
            </div>`).join('');
        const tipsHtml = TIPS.map(t => `
            <div class="hc-tiprow"><span>${t.group} — ${t.title} ${_isSeen(t.id) ? '<span class="done">✓</span>' : ''}</span>
                <span><button onclick="HelpCenter._resetTip('${t.id}')">again</button></span>
            </div>`).join('');
        m.innerHTML = `<div class="hc-modal-inner">
            <h3>❓ Help &amp; Guides</h3>
            <div style="font-size:11px;color:#5b6570;margin-bottom:10px;">Coach tips appear as you touch things. F1 reopens this. Reset restores every tip.</div>
            <b>Guided tours</b>
            ${toursHtml}
            <div style="margin:10px 0 4px;"><b>All tips</b> <button class="hc-reset" onclick="HelpCenter._resetAll()">Reset all</button></div>
            ${tipsHtml}
            <div style="margin-top:12px;text-align:right;"><button onclick="HelpCenter._closeModal()">Close</button></div>
        </div>`;
        document.body.appendChild(m);
        m.addEventListener('click', (e) => { if (e.target === m) _closeModal(); });
    }

    // ─────────────────────── Initialization ───────────────────────
    function init() {
        _ensureStyles();
        if (window.appEvents) {
            appEvents.on('state:updated', () => maybe('state:updated', null));
            appEvents.on('inspector:view', (d) => maybe('inspector:view', d));
        }
        document.addEventListener('click', (e) => {
            const el = e.target.closest && e.target.closest('[data-help]');
            if (el) maybe('data-help', el.dataset.help);
        }, true);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F1') { e.preventDefault(); openIndex(); }
            if (e.key === 'Escape') { _closeCard(); _clearSpotlight(); _closeModal(); }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    return { TIPS, TOURS, maybe, startTour, openIndex, init, _closeModal, _resetTip, _resetAll };

    // ── exports for inline buttons ──
    function _resetTip(id) {
        _sessionSeen.delete(id);
        _seen.delete(id);
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify([..._seen])); } catch (e) { /* ignore */ }
        _closeModal();
        openIndex();
    }
    function _resetAll() {
        _seen.clear();
        _sessionSeen.clear();
        try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
        _closeModal();
    }
})();
