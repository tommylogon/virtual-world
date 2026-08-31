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
            event: 'state:updated',
            once: 'session',
            group: 'Beginner',
            title: 'Welcome to VirtualWorld',
            body: 'This is your world. <b>▶</b> runs the sim for the agent you have selected — it thinks, speaks and acts, turn after turn. Switch on <b>Turn-Based Mode</b> (Agent Settings) and every character rotates in initiative order instead. <b>F1</b> (or ❓ up top) reopens this Help Center.',
            target: '#sim-play',
        },
        {
            id: 'run-sim',
            event: 'data-help',
            match: d => d === 'run',
            group: 'Beginner',
            title: 'Running the simulation',
            body: 'By default <b>▶</b> runs only the <b>selected</b> agent, one turn at a time (click an agent in the left panel to choose who). <b>Turn-Based Mode</b> in Agent Settings rotates <i>every</i> character in initiative order — the left panel shows who is up. Either way: click any agent to inspect its vitals, thoughts and gear.',
            target: '#sim-play',
        },
        {
            id: 'agent-settings',
            event: 'data-help',
            match: d => d === 'settings',
            group: 'Beginner',
            title: 'Agent settings live here',
            body: 'The fun switches: <b>🔁 Auto-Retry Invalid Actions</b>, <b>🌊 Simultaneous Mode</b> (experimental, chaos by design), ghost mode, models, and rate limits. Save persists per profile.',
            target: '#settings-modal',
        },
        {
            id: 'game-menu',
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
            event: 'inspector:view',
            match: d => d && d.type === 'area',
            group: 'World building',
            title: 'Room inspector',
            body: 'Environment (light/temp/air/smell/noise), description, and the items here. Area <b>tags</b> drive what spawns in it (store, restaurant, haunted…).',
        },
        {
            id: 'inspector-item',
            event: 'inspector:view',
            match: d => d && d.type === 'item',
            once: 'session',
            group: 'Items & triggers',
            title: 'Items grow with their tags',
            body: 'Add <b>armor/clothing</b> → the Defense field appears; <b>weapon</b> → damage fields; <b>food</b> → eat; <b>container</b> → capacity; <b>toggleable</b> → its controls. Newer mechanics: set <b>max_uses</b> for durability (weight scales), <b>perishable</b> for freshness, <b>proximity_effect</b> for EMF-style reads.',
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
            event: 'data-help',
            match: d => d === 'more',
            group: 'World building',
            title: 'The More menu',
            body: 'Rarely-used tools: <b>📋 Templates</b> (the {param:…} reference), 🌍 Lore, graph Legend, Tags panel, Sync to Library, and printing the world.',
            target: '[title="More graph tools"]',
        },
        {
            id: 'trigger-system',
            event: 'data-help',
            match: d => d === 'triggers',
            group: 'Items & triggers',
            title: 'The trigger system is the engine of surprise',
            body: '<b>trigger_type</b> decides when (on_use, on_speech, on_break…), <b>conditions</b> gate it (uses, tags, has_item…), <b>effects</b> do the work (spawn, set_state, scry, llm_respond…). And <b>every effect has a template item</b> — search the library for "Template:" to see one live.',
        },
        {
            id: 'snippets',
            event: 'data-help',
            match: d => d === 'snippets',
            group: 'Items & triggers',
            title: 'Trigger snippets',
            body: 'In the trigger editor, <b>snippets</b> fill a whole trigger in one click — Chest, Light Source, Heat Source, First Aid, Whispering Door, Recorder. Ctrl+K finds anything.',
        },
        {
            id: 'simultaneous',
            event: 'data-help',
            match: d => d === 'simultaneous',
            group: 'Advanced',
            title: '⚠️ Simultaneous Mode is experimental',
            body: 'Every autonomous character acts on its own countdown — <b>Social</b> speeds it up, exhaustion and patient/sprinter traits shift it. Expect chaos, overlapping drama, and happy accidents. Sequential mode stays the safe default.',
        },
        {
            id: 'autodress',
            event: 'data-help',
            match: d => d === 'autodress',
            group: 'Items & triggers',
            title: 'Auto-Dress from Interests',
            body: 'Scans the item library for wearable pieces matching the character\'s <b>interest_tags</b> (weather-aware, never replaces worn gear). Empty interests? Use <b>✨ Generate from Personality</b> in Bio to let the character pick its own tags.',
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
            event: 'data-help',
            match: d => d === 'duplicate',
            group: 'World building',
            title: 'Duplicate clones children — not parents',
            body: 'Duplicating the table also clones the salt <i>on</i> it, but the kitchen it sits in stays shared. Parents are never cloned; attached children are.',
        },
    ];

    // Guided tours: ordered chains of tip ids.
    const TOURS = {
        hello: { title: 'First five minutes', group: 'Beginner', steps: ['welcome', 'run-sim', 'agent-settings', 'game-menu'] },
        triggers: { title: 'Triggers & effects', group: 'Items & triggers', steps: ['inspector-item', 'trigger-system', 'snippets', 'more-tools'] },
        scenario: { title: 'Scenario workflow', group: 'World building', steps: ['game-menu', 'duplicate', 'inspector-area'] },
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
