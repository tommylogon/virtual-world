"use strict";
/**
 * human-turn-composer.js — the human turn PANEL (task-333; continuous multi-action v4, task-352)
 *
 * @module agent/human-turn-composer — the panel you play a character from
 * @contributes HumanTurnComposer: scene view, feed/digest, You strip, step composer, budget pips, react beat
 * @powers The human turn, Turn queue — actually taking a turn as a character
 * @relates uses turn-feed + turn-scene-view + api (action submit) + agent-engine state + action-tiers
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 *
 * A turn is a budget you spend in a continuous loop, in ONE panel that stays
 * open (v4, task-352):
 *
 *   ┌ header: ✈ <char>'s turn · tick · next up ┐
 *   │ scene view (clickable chips) │ what happened (feed) │
 *   │ You strip · budget pips ◆ major ◇ minor ●●● free     │
 *   │ ⚙ do · 🗨 say(+volume) · 🎭 emote · 🧠 memory  [Act]  │
 *   │ [⏭ end turn]                                          │
 *   └ advanced (relation) · timeskip                      ┘
 *
 * act → the result lands in the feed, pips drop, the scene refreshes → act
 * again … or End. There is no per-action react modal: your reaction to an
 * outcome is the NEXT step's say/emote/memory (composed after you saw the
 * result), and one optional closing beat when you End. This mirrors the agent
 * loop (decide → act → react) without N modal round-trips.
 *
 * Say / emote / memory are EXPRESSION, unbudgeted (task-352): they never cost a
 * pip. Only the action charges `turn_slots`; `wait` and the free utility verbs
 * cost a free slot. The old `dash burst` phase and its narration regex are gone.
 *
 * Contract with agent-engine.js:
 *   request(charName, opts?) → Promise<{ step: NormalizedReply } | {endTurn:true}>
 *       Opens the panel on the first call; subsequent calls refresh it and arm
 *       the next step. Never hides — the turn is one continuous panel.
 *   react(charName, results) → Promise<{speech, volume, emote, memory, target} | {endTurn:true}>
 *       The single closing beat after the turn ran (task-334 lane 1).
 *   closeTurn()              → hides the panel (call once the turn is done).
 *
 * Load AFTER response-parser.js / turn-scene-view.js / turn-you-strip.js /
 * turn-feed.js / action-tiers.js, BEFORE agent-engine.js.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const htcPanelTag = (strings, ...values) => window.Lit.html(strings, ...values);
const HumanTurnComposerModule = (() => {
    'use strict';
    let _activeResolve = null;
    let _reactResolve = null;
    let _phase = 'compose';
    let _built = false;
    let _modal;
    let _overlay;
    let _charName = null;
    let _volume = 'say';
    let _pendingSpeechTarget = null;
    let _advanced = false;
    let _scene = null;
    const q = (sel) => _modal.querySelector(sel);
    const qa = (sel) => Array.from(_modal.querySelectorAll(sel));
    const STYLE_ID = 'htc-styles';
    function actionTiers() {
        return window.ActionTiers || null;
    }
    // ── styles ───────────────────────────────────────────────────────
    function ensureStyles() {
        if (document.getElementById(STYLE_ID))
            return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            #htc-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1200; display:none; align-items:center; justify-content:center; }
            #htc-modal { background:#1e2128; color:#e6e8ee; width:min(1080px,96vw); max-height:94vh; overflow:auto; border-radius:14px; border:1px solid #333a45; box-shadow:0 18px 60px rgba(0,0,0,.6); font-family:inherit; font-size:13px; }
            .htc-header { padding:10px 16px; border-bottom:1px solid #333a45; display:flex; align-items:center; gap:10px; background:#1a1d24; border-radius:14px 14px 0 0; }
            .htc-title { font-size:14px; font-weight:600; }
            .htc-spacer { flex:1; }
            #htc-meta { color:#78828e; font-size:11.5px; }
            #htc-meta b { color:#b48ce0; }
            #htc-close { background:none; border:0; color:#6b7686; cursor:pointer; font-size:15px; }

            .htc-digest { margin:10px 16px 0; background:#241a10; border:1px solid #40301c; border-radius:10px; padding:8px 12px; }
            .htc-digest .dt { font-size:10.5px; text-transform:uppercase; letter-spacing:1.1px; color:#ffb37a; margin-bottom:4px; }
            .htc-digest .di { font-size:12px; color:#e8c49a; padding:1px 0; }
            .htc-digest .drow { display:flex; gap:6px; margin-top:6px; }
            .htc-linkbtn { background:none; border:0; color:#ffb37a; font-size:11.5px; cursor:pointer; }
            .htc-linkbtn.muted { color:#6b7686; }

            .htc-grid { display:grid; grid-template-columns: 1fr 300px; }
            .htc-feed { border-left:1px solid #333a45; padding:10px 14px; max-height:340px; overflow-y:auto; }
            .htc-feed h4 { margin:0 0 7px; font-size:10.5px; text-transform:uppercase; letter-spacing:1.2px; color:#6b7686; }
            .tfd-line { color:#98a3ae; font-size:12px; padding:2px 0 2px 10px; line-height:1.45; border-left:2px solid #232932; margin-bottom:3px; }
            .tfd-line.tfd-act { color:#bcd3ec; }
            .tfd-line.tfd-err { color:#e08f8f; }
            .tfd-line.tfd-sys { color:#6b7686; }
            .tfd-line.tfd-empty { color:#5b6570; font-style:italic; border-left-color:transparent; }
            @media (max-width: 940px) { .htc-grid { grid-template-columns: 1fr; } .htc-feed { border-left:0; border-top:1px solid #333a45; max-height:180px; } }

            .htc-composer { border-top:1px solid #333a45; background:#1a1d24; padding:11px 16px 13px; border-radius:0 0 14px 14px; }
            .htc-budget { display:flex; align-items:center; gap:14px; margin-bottom:9px; }
            .htc-pips { display:flex; align-items:center; gap:6px; }
            .htc-pip { width:15px; height:15px; display:inline-block; }
            .htc-pip.major { border:2px solid #d9baff; transform:rotate(45deg); border-radius:3px; }
            .htc-pip.minor { border:2px solid #4f9cf9; border-radius:3px; }
            .htc-pip.free { border-radius:50%; border:2px solid #57c98f; width:12px; height:12px; }
            .htc-pip.spent { opacity:.22; }
            .htc-budgetlab { font-size:11.5px; color:#78828e; }
            .htc-budgetlab b { color:#e6e8ee; }
            #htc-phase-note { font-size:11.5px; color:#78828e; margin-left:auto; }
            #htc-result { margin:0 0 8px 64px; font-size:12.5px; color:#98a3ae; border-left:3px solid #2c4a36; padding-left:10px; }
            #htc-result b { color:#57c98f; }

            .htc-crow { display:flex; gap:8px; align-items:center; margin-bottom:7px; }
            .htc-crow .lbl { width:56px; text-align:right; font-size:11.5px; color:#7d8894; flex:none; }
            .htc-crow input[type=text] { flex:1; background:#141820; border:1px solid #2a303b; color:#e6e8ee; border-radius:8px; padding:8px 11px; font-size:13px; outline:none; min-width:0; color-scheme:dark; }
            .htc-crow input[type=text]:focus { border-color:#4f9cf9; box-shadow:0 0 0 2px rgba(79,156,249,.22); }
            .htc-volseg { display:flex; border:1px solid #2a303b; border-radius:8px; overflow:hidden; flex:none; }
            .htc-volseg button { background:#1d212a; color:#8b95a1; border:0; padding:7px 8px; font-size:11px; border-right:1px solid #2a303b; cursor:pointer; }
            .htc-volseg button:last-child { border-right:0; }
            .htc-volseg button.on { background:#2b1f42; color:#d9baff; }
            .htc-btn-primary { background:#4f9cf9; border:0; color:#fff; font-weight:600; border-radius:8px; padding:8px 18px; flex:none; cursor:pointer; }
            .htc-btn-primary:hover { background:#61a9fa; }
            .htc-btn-primary.gold { background:#b3812f; }
            .htc-btn-primary:disabled { opacity:.45; cursor:default; }
            #htc-clear-do { background:none; border:0; color:#6b7686; cursor:pointer; font-size:12px; }

            .htc-footer-row { margin:8px 0 0 64px; display:flex; gap:14px; align-items:center; }
            .htc-linkbtn.endturn { color:#e08f8f; margin-left:auto; }
            #htc-advanced { margin:6px 0 0 64px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
            #htc-advanced select { background:#1d212a; color:#9aa3b2; border:1px solid #2a303b; border-radius:7px; padding:5px 8px; font-size:11.5px; color-scheme:dark; }
            #htc-advanced select:disabled { color:#55606c; }
            .htc-flash { color:#e08f8f; font-size:11.5px; }

            .htc-chiptoggle { background:#1d212a; border:1px solid #2a303b; color:#d9c9a9; border-radius:8px; padding:7px 10px; font-size:12px; flex:none; cursor:pointer; }
            .htc-chiptoggle:hover { border-color:#4f9cf9; color:#e6e8ee; }
            .htc-emote-palette { display:none; margin:3px 0 9px 64px; background:#15181f; border:1px solid #333a45; border-radius:10px; padding:8px 10px; }
            .htc-emote-palette.open { display:block; }
        `;
        document.head.appendChild(style);
    }
    function el(template) {
        const t = document.createElement('div');
        window.Lit.render(template, t);
        return t.firstElementChild;
    }
    // ── typed one-box parsing ────────────────────────────────────────
    const VERBS = [
        'look', 'go', 'approach', 'take', 'drop', 'place', 'put', 'give', 'use', 'examine',
        'attack', 'open', 'close', 'read', 'search', 'wear', 'equip', 'remove', 'unequip',
        'rest', 'sleep', 'wait', 'nothing', 'dash', 'crawl', 'climb', 'jump', 'grab',
        'steal', 'light', 'ignite', 'vanish', 'manifest', 'toggle', 'listen',
        'wake', 'meditate', 'bathe', 'stand', 'release', 'escape', 'struggle', 'lead',
        'fear', 'interest', 'eat', 'drink',
        'teach', 'kiss', 'caress', 'lick', 'suck', 'bite', 'pinch', 'blow', 'tickle',
    ];
    const VOLUME_WORDS = ['scream', 'shout', 'whisper'];
    /** Typed input → draft parts. Unknown verbs become speech. */
    function parseCmd(raw) {
        const t = (raw || '').trim();
        if (!t)
            return {};
        const lower = t.toLowerCase();
        for (const vol of VOLUME_WORDS) {
            if (lower.startsWith(vol + ' ')) {
                return { speech: t.slice(vol.length + 1).trim(), volume: vol };
            }
        }
        const verb = lower.split(/\s+/)[0];
        if (!VERBS.includes(verb))
            return { speech: t };
        const rest = t.slice(verb.length).trim();
        const out = { action: verb };
        if (verb === 'give' || verb === 'steal' || verb === 'teach') {
            const m = rest.split(/\s+(?:to|from)\s+/i);
            out.item = m[0] || '';
            out.target = m[1] || '';
        }
        else if (verb === 'use') {
            const on = rest.split(/\s+on\s+/i);
            out.item = on[0] || '';
            out.target = on[1] || '';
        }
        else if (rest) {
            out.item = rest;
        }
        return out;
    }
    /** Build the payload from the current rows. */
    function buildPayload() {
        const m = _modal;
        const doRaw = m.querySelector('#htc-do').value;
        const parsed = parseCmd(doRaw);
        const speech = (m.querySelector('#htc-speech').value || '').trim() || parsed.speech || '';
        const emote = (m.querySelector('#htc-emote').value || '').trim();
        const memory = (m.querySelector('#htc-memory').value || '').trim();
        const p = {};
        if (parsed.action) {
            p.action = parsed.action;
            if (parsed.item)
                p.item = parsed.item;
            if (parsed.target)
                p.target = parsed.target;
            const rel = m.querySelector('#htc-relation').value;
            if ((parsed.action === 'put' || parsed.action === 'place') && rel)
                p.relation = rel;
        }
        if (speech) {
            p.speech = speech;
            p.volume = parsed.volume || _volume;
            if (p.volume === 'whisper' && _pendingSpeechTarget)
                p.target = _pendingSpeechTarget;
        }
        if (emote)
            p.emote = emote;
        if (memory)
            p.memory = memory;
        return p;
    }
    /** Same normalization an agent reply goes through. */
    function normalizeReply(p) {
        if (!p || typeof p !== 'object')
            return { action: '', speech: null, speechVolume: 'say', emote: null, memory: null, target: null };
        const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
        return {
            action: ActionNormalizer.normalizeStructuredAction(p),
            speech,
            speechVolume: volume,
            target: (volume === 'whisper' && typeof p.target === 'string' && p.target.trim()) ? p.target.trim() : null,
            emote: typeof p.emote === 'string' ? p.emote : null,
            memory: ResponseParser.extractMemory(p.memory),
        };
    }
    // ── turn budget ──────────────────────────────────────────────────
    function turnSlots() {
        const players = worldState.players;
        const slots = players && _charName ? players[_charName]?.turn_slots : null;
        return slots && typeof slots === 'object' ? { ...slots } : null;
    }
    function anySlotLeft(s) {
        return Object.keys(s).some((k) => (s[k] || 0) > 0);
    }
    function renderPips() {
        const s = turnSlots() || { major: 0, minor: 0, free: 0 };
        const pips = [];
        pips.push(`<span class="htc-pip major ${s.major ? '' : 'spent'}" title="major ${s.major || 0} left"></span>`);
        pips.push(`<span class="htc-pip minor ${s.minor ? '' : 'spent'}" title="minor ${s.minor || 0} left"></span>`);
        for (let i = 0; i < 3; i += 1)
            pips.push(`<span class="htc-pip free ${i < (s.free || 0) ? '' : 'spent'}" title="free ${s.free || 0} left"></span>`);
        q('#htc-pips').innerHTML = pips.join('');
        q('#htc-budgetlab').innerHTML = `<b>${s.major || 0}</b> major · <b>${s.minor || 0}</b> minor · <b>${s.free || 0}</b> free`;
    }
    function setPhase(phase) {
        _phase = phase;
        const react = phase === 'react';
        q('#htc-do-row').style.display = react ? 'none' : 'flex';
        q('#htc-act').style.display = react ? 'none' : '';
        q('#htc-react-btn').style.display = react ? '' : 'none';
        q('#htc-end').style.display = react ? 'none' : '';
        q('#htc-title').textContent = react ? `${_charName}'s reaction` : `${_charName}'s turn`;
        q('#htc-phase-note').textContent = react
            ? 'say / emote / memory — the turn already ran'
            : 'act · say · emote · memory are all free — only actions spend pips';
        q('#htc-do').placeholder = react
            ? 'react to what happened…'
            : 'action — click a thing above, or type "eat berries", "open door"…';
        q('#htc-speech').placeholder = react
            ? 'what they say back…'
            : 'what they say — free, stacks with the action';
    }
    function setBusy(on) {
        q('#htc-act').disabled = on;
    }
    function showResult(text) {
        const node = q('#htc-result');
        if (!text) {
            node.style.display = 'none';
            return;
        }
        node.textContent = '';
        const b = document.createElement('b');
        b.textContent = 'last: ';
        node.appendChild(b);
        node.appendChild(document.createTextNode(text));
        node.style.display = 'block';
    }
    function showResults(results) {
        const node = q('#htc-result');
        if (!results.length) {
            node.style.display = 'none';
            return;
        }
        node.textContent = '';
        results.forEach((text, i) => {
            const b = document.createElement('b');
            b.textContent = results.length > 1 ? `${i + 1}. ` : 'result: ';
            node.appendChild(b);
            node.appendChild(document.createTextNode(text || ''));
            node.appendChild(document.createElement('br'));
        });
        node.style.display = 'block';
    }
    function syncVolumeButtons() {
        if (!_modal)
            return;
        for (const btn of qa('#htc-volseg button')) {
            btn.classList.toggle('on', btn.dataset.vol === _volume);
        }
    }
    function renderMeta() {
        const meta = q('#htc-meta');
        const bits = [];
        if (typeof worldState !== 'undefined' && worldState.tick)
            bits.push(`tick ${worldState.tick}`);
        let nextUp = '';
        try {
            if (config.turnBased && typeof TurnQueue !== 'undefined') {
                nextUp = TurnQueue.getCurrentCharacter?.() || '';
            }
        }
        catch { /* queue not initialized */ }
        if (nextUp && nextUp !== _charName)
            bits.push(`next up: <b>${nextUp}</b>`);
        else if (nextUp)
            bits.push('next up: <b>you</b>');
        meta.innerHTML = bits.join(' · ');
    }
    function renderDatalist() {
        const dl = q('#htc-names');
        dl.textContent = '';
        if (!_scene)
            return;
        const names = new Set();
        for (const item of (_scene.items || []))
            names.add(item.name);
        for (const p of (_scene.people || []))
            names.add(p.display_name);
        for (const way of (_scene.ways || [])) {
            names.add(way.direction);
            if (way.to)
                names.add(way.to);
        }
        for (const inv of [...(_scene.you?.carrying || []), ...(_scene.you?.wearing || [])])
            names.add(inv.name);
        for (const name of names) {
            const opt = document.createElement('option');
            opt.value = String(name);
            dl.appendChild(opt);
        }
    }
    function renderDigest() {
        const entries = TurnFeed.digest().slice(-4);
        const box = q('#htc-digest');
        if (!entries.length) {
            box.style.display = 'none';
            return;
        }
        const lines = q('#htc-digest-lines');
        lines.textContent = '';
        for (const entry of entries) {
            const line = document.createElement('div');
            line.className = 'di';
            line.textContent = '• ' + entry.text;
            lines.appendChild(line);
        }
        box.style.display = 'block';
    }
    /** (Re)build the scene view + You strip + minimap for *charName*. */
    function refreshScene(charName) {
        const sceneHost = q('#htc-scene');
        sceneHost.textContent = 'reading the room…';
        const stripHandlers = {
            onDraft: applyDraft,
            menu: (x, y, title, buttons) => htcGlobals.TurnSceneView
                .menu(x, y, title, buttons, applyDraft),
        };
        if (!htcGlobals.TurnSceneView)
            return;
        const sceneView = htcGlobals.TurnSceneView;
        sceneView.fetch(charName).then((scene) => {
            if (!scene || scene.error || _charName !== charName)
                return;
            _scene = scene;
            sceneView.renderScene(sceneHost, scene, {
                onDraft: applyDraft,
                onTalkFocus: (talkOpts) => {
                    if (talkOpts && talkOpts.volume) {
                        _volume = talkOpts.volume;
                        syncVolumeButtons();
                    }
                    _pendingSpeechTarget = (talkOpts && talkOpts.volume === 'whisper' && talkOpts.target) ? talkOpts.target : null;
                    q('#htc-speech').focus();
                },
            });
            htcGlobals.TurnYouStrip
                .render(q('#htc-you'), scene.you, stripHandlers);
            if (htcGlobals.TurnMinimap) {
                const feed = document.querySelector('.htc-feed');
                if (feed)
                    htcGlobals.TurnMinimap.mount(feed, charName).catch(() => { });
            }
            renderDatalist();
        }).catch(() => {
            sceneHost.textContent = '';
            sceneHost.appendChild(document.createTextNode('scene unavailable.'));
        });
    }
    // ── build ────────────────────────────────────────────────────────
    function build() {
        if (_built)
            return;
        _built = true;
        ensureStyles();
        _overlay = el(htcPanelTag `<div id="htc-overlay" style="display:none"></div>`);
        _modal = el(htcPanelTag `<div id="htc-modal"></div>`);
        _overlay.appendChild(_modal);
        window.Lit.render(htcPanelTag `
          <div class="htc-header">
            <strong class="htc-title">✈ <span id="htc-title">Your turn</span></strong>
            <span class="htc-spacer"></span>
            <span id="htc-meta"></span>
            <button type="button" id="htc-close" title="end turn">✕</button>
          </div>
          <div id="htc-digest" style="display:none">
            <div class="dt">since your turn</div>
            <div id="htc-digest-lines"></div>
            <div class="drow">
              <button type="button" id="htc-digest-dismiss" class="htc-linkbtn muted" title="dismiss">✕</button>
            </div>
          </div>
          <div class="htc-grid">
            <div id="htc-scene"></div>
            <div class="htc-feed">
              <h4>What happened</h4>
              <div id="htc-feed-lines"></div>
            </div>
          </div>
          <div id="htc-you"></div>
          <div class="htc-composer">
            <div class="htc-budget">
              <div class="htc-pips" id="htc-pips"></div>
              <div class="htc-budgetlab" id="htc-budgetlab"></div>
              <span id="htc-phase-note"></span>
            </div>
            <div id="htc-result" style="display:none"></div>
            <div class="htc-crow" id="htc-do-row">
              <span class="lbl">⚙ do</span>
              <input id="htc-do" type="text" list="htc-names" placeholder='action — click a thing above, or type "eat berries", "open door"…' autocomplete="off">
              <button type="button" id="htc-clear-do" title="clear">✕</button>
            </div>
            <div class="htc-crow">
              <span class="lbl">🗨 say</span>
              <input id="htc-speech" type="text" placeholder="what they say — free, stacks with the action" autocomplete="off">
              <div class="htc-volseg" id="htc-volseg"></div>
            </div>
            <div class="htc-crow">
              <span class="lbl">🎭 emote</span>
              <input id="htc-emote" type="text" placeholder='body language — "sneaks closer to the door"' autocomplete="off">
              <button type="button" id="htc-emote-toggle" class="htc-chiptoggle" title="emote quick-pick">🎭</button>
            </div>
            <div id="htc-emote-palette" class="htc-emote-palette"></div>
            <div class="htc-crow">
              <span class="lbl">🧠 memory</span>
              <input id="htc-memory" type="text" placeholder="optional — what you'll personally remember from this" autocomplete="off">
              <button type="button" id="htc-act" class="htc-btn-primary">Act</button>
            </div>
            <div class="htc-footer-row">
              <button type="button" id="htc-react-btn" class="htc-btn-primary gold" style="display:none">close turn</button>
              <span id="htc-flash" class="htc-flash"></span>
              <button type="button" id="htc-advanced-toggle" class="htc-linkbtn muted">▸ advanced</button>
              <button type="button" id="htc-timeskip" class="htc-linkbtn" title="Wait, mingle, search, explore or travel for a span — your character runs on a policy while everyone else soaks">⏩ timeskip</button>
              <button type="button" id="htc-end" class="htc-linkbtn endturn">⏭ end turn</button>
            </div>
            <div id="htc-advanced" style="display:none">
              <select id="htc-relation"><option value="">relation: —</option><option value="on">on</option><option value="under">under</option><option value="beside">beside</option><option value="behind">behind</option><option value="at">at</option><option value="in">in</option></select>
              <select id="htc-where" disabled title="reserved — region targeting lands with task-211">
                <option>where: body region (task-211)</option>
              </select>
            </div>
          </div>
          <datalist id="htc-names"></datalist>
        `, _modal);
        document.body.appendChild(_overlay);
        const volseg = q('#htc-volseg');
        for (const vol of ['say', 'whisper', 'shout', 'scream']) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = vol;
            btn.dataset.vol = vol;
            btn.addEventListener('click', () => {
                _volume = vol;
                if (vol !== 'whisper')
                    _pendingSpeechTarget = null;
                syncVolumeButtons();
            });
            volseg.appendChild(btn);
        }
        syncVolumeButtons();
        q('#htc-act').addEventListener('click', commitStep);
        q('#htc-react-btn').addEventListener('click', () => finishReact(false));
        q('#htc-end').addEventListener('click', () => finishAct({ endTurn: true }));
        q('#htc-close').addEventListener('click', () => onOverlayDismiss());
        q('#htc-timeskip').addEventListener('click', () => {
            if (htcGlobals.Timeskip && typeof htcGlobals.Timeskip.openDialog === 'function') {
                htcGlobals.Timeskip.openDialog();
            }
        });
        q('#htc-clear-do').addEventListener('click', () => {
            q('#htc-do').value = '';
        });
        q('#htc-emote-toggle').addEventListener('click', () => {
            EmotePicker.toggle(q('#htc-emote-palette'), {
                onPick: (emote) => {
                    const input = q('#htc-emote');
                    if (input)
                        input.value = emote;
                }
            });
        });
        q('#htc-act').addEventListener('click', () => {
            EmotePicker.close(q('#htc-emote-palette'));
        });
        for (const id of ['htc-do', 'htc-speech', 'htc-emote', 'htc-memory']) {
            q('#' + id).addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (_phase === 'react')
                        finishReact(false);
                    else
                        commitStep();
                }
                if (e.key === 'Escape' && _phase === 'react')
                    finishReact(true);
            });
        }
        q('#htc-advanced-toggle').addEventListener('click', () => {
            _advanced = !_advanced;
            q('#htc-advanced').style.display = _advanced ? 'flex' : 'none';
            q('#htc-advanced-toggle').textContent = _advanced ? '▾ advanced' : '▸ advanced';
        });
        q('#htc-digest-dismiss').addEventListener('click', () => {
            TurnFeed.clearDigest();
            q('#htc-digest').style.display = 'none';
        });
        _modal.addEventListener('click', (e) => e.stopPropagation());
        _overlay.addEventListener('click', () => onOverlayDismiss());
        const closeOnEsc = (e) => {
            if (e.key === 'Escape' && _overlay.style.display !== 'none')
                onOverlayDismiss();
        };
        document.addEventListener('keydown', closeOnEsc);
    }
    // ── resolve plumbing ─────────────────────────────────────────────
    /** Stage one step and hand it to the engine. The panel stays OPEN. */
    function commitStep() {
        const norm = normalizeReply(buildPayload());
        if (!norm.action && !norm.speech && !norm.emote)
            return;
        if (norm.action) {
            const verb = norm.action.split(/\s+/)[0].toLowerCase();
            const at = actionTiers();
            const tier = at && at.tierOf ? at.tierOf(verb) : 'major';
            const s = turnSlots();
            const order = ['free', 'minor', 'major'];
            const affordable = (tier === 'activity')
                ? !s || (s.activity || 0) > 0
                : !s || order.slice(Math.max(0, order.indexOf(tier))).some((t) => (s[t] || 0) > 0);
            if (!affordable) {
                setFlash(`no ${tier} action left this turn — say / emote / memory are still free`);
                return;
            }
        }
        const resolve = _activeResolve;
        _activeResolve = null;
        for (const id of ['htc-do', 'htc-speech', 'htc-emote', 'htc-memory']) {
            q('#' + id).value = '';
        }
        q('#htc-relation').value = '';
        _pendingSpeechTarget = null;
        setBusy(true);
        if (resolve)
            resolve({ step: norm });
    }
    function finishAct(reply) {
        const resolve = _activeResolve;
        _activeResolve = null;
        TurnFeed.markTurnEnd();
        hidePanel();
        if (resolve)
            resolve(reply);
    }
    function finishReact(endTurn) {
        if (typeof _reactResolve !== 'function')
            return;
        const resolve = _reactResolve;
        _reactResolve = null;
        let reply;
        if (endTurn) {
            reply = { endTurn: true };
        }
        else {
            const norm = normalizeReply(buildPayload());
            reply = { speech: norm.speech, volume: norm.speechVolume, emote: norm.emote, memory: norm.memory, target: norm.target };
        }
        TurnFeed.markTurnEnd();
        hidePanel();
        resolve(reply);
    }
    function onOverlayDismiss() {
        if (_phase === 'react') {
            finishReact(true);
            return;
        }
        finishAct({ endTurn: true });
    }
    function setFlash(msg) {
        const node = q('#htc-flash');
        node.textContent = msg;
        window.setTimeout(() => { if (node.textContent === msg)
            node.textContent = ''; }, 2200);
    }
    // ── panel open/close ─────────────────────────────────────────────
    function hidePanel() {
        if (_overlay)
            _overlay.style.display = 'none';
        if (_scene && typeof _scene.closeMenu === 'function')
            _scene.closeMenu();
    }
    function resetRows() {
        for (const id of ['htc-do', 'htc-speech', 'htc-emote', 'htc-memory']) {
            q('#' + id).value = '';
        }
        q('#htc-relation').value = '';
        _pendingSpeechTarget = null;
    }
    function applyDraft(parts) {
        if (!parts || _phase === 'react')
            return;
        q('#htc-do').value = [parts.action, parts.item, parts.target]
            .filter(Boolean).join(' ');
        q('#htc-speech').focus();
    }
    /** First open for a turn: full setup + show. */
    function openPanel(charName, opts = {}) {
        build();
        _charName = charName;
        resetRows();
        setPhase('compose');
        showResult(opts.lastResult || '');
        refreshScene(charName);
        TurnFeed.render(q('#htc-feed-lines'));
        renderMeta();
        renderDigest();
        renderPips();
        setBusy(false);
        q('#htc-flash').textContent = '';
        _overlay.style.display = 'flex';
        q('#htc-do').focus();
    }
    /** Subsequent step: refresh the open panel with the last result + budget. */
    function refreshStep(charName, lastResult) {
        _charName = charName;
        setPhase('compose');
        showResult(lastResult || '');
        refreshScene(charName);
        renderMeta();
        renderDigest();
        renderPips();
        setBusy(false);
        q('#htc-do').focus();
    }
    /**
     * The engine's per-step hook. First call opens the panel; later calls
     * refresh it. Resolves when the player Commits a step (`{step}`) or ends
     * the turn (`{endTurn:true}`). Never hides on a step.
     */
    function request(charName, opts = {}) {
        if (_activeResolve) {
            return new Promise((resolve) => { _activeResolve = resolve; });
        }
        if (!_overlay || _overlay.style.display === 'none')
            openPanel(charName, opts);
        else
            refreshStep(charName, opts.lastResult || '');
        return new Promise((resolve) => { _activeResolve = resolve; });
    }
    /**
     * The single closing react beat (task-334 lane 1): say / emote / memory
     * bound to the turn's results. Reuses the open panel, or reopens it if the
     * player already ended the turn.
     */
    function react(charName, results) {
        if (_reactResolve) {
            return new Promise((resolve) => { _reactResolve = resolve; });
        }
        if (!_built || !_overlay || _overlay.style.display === 'none') {
            build();
            _charName = charName;
            resetRows();
            setPhase('react');
            showResults(results);
            renderMeta();
            renderDigest();
            _overlay.style.display = 'flex';
        }
        else {
            _charName = charName;
            resetRows();
            setPhase('react');
            showResults(results);
            refreshScene(charName);
            renderMeta();
            renderDigest();
        }
        q('#htc-speech').focus();
        return new Promise((resolve) => { _reactResolve = resolve; });
    }
    /** The engine calls this once the turn (and react) is done. */
    function closeTurn() {
        hidePanel();
    }
    return { request, react, closeTurn };
})();
window.HumanTurnComposer = HumanTurnComposerModule;
const htcGlobals = window;
/** `EmotePicker` (shared/emote-picker.js) is declared in types/globals.d.ts. */
