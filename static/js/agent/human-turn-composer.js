/**
 * human-turn-composer.js — the human turn PANEL (task-333 full redesign)
 *
 * Scene-first three-zone layout matching
 * docs/design/human-turn-panel-v2-mockup.html (v2.7):
 *
 *   ┌ header: ✈ <char>'s turn · tick · next up ┐
 *   │ scene view (clickable chips) │ what happened (feed) │
 *   │ You strip: vitals · conditions · carrying · wearing · known │
 *   │ composer: ⚙ do · 🗨 say(+volume) · 🎭 emote · 🧠 memory      │
 *   └ phase bar · advanced (relation/where/confirm) · raw json ┘
 *
 * One turn = do + say + emote TOGETHER in a single structured payload.
 * Menu picks and typed input only FILL the draft — nothing fires until
 * Act (compose-then-commit). After Act resolves, react() opens the react
 * phase (say/emote/memory bound to the result — task-334 lane 1); a dash
 * grants one extra action slot before react (the burst phase).
 *
 * Contract with agent-engine.js:
 *   request(charName, opts?) → Promise<{action, speech, speechVolume,
 *       emote, memory} | {endTurn:true}>
 *   react(charName, lastResult) → Promise<same shape (action empty)>
 *
 * Load AFTER response-parser.js / turn-scene-view.js / turn-you-strip.js /
 * turn-feed.js, BEFORE agent-engine.js.
 */

// Lazy lit-html tag: window.Lit is only available at call time (deferred
// module bootstrap). Unique per file so top-level consts never collide.
const htcPanelTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.HumanTurnComposer = (() => {
    'use strict';

    let _activeResolve = null;   // compose/burst phase resolver
    let _reactResolve = null;    // react phase resolver
    let _built = false;
    let _modal = null;
    let _overlay = null;
    let _charName = null;
    let _phase = 'compose';      // 'compose' | 'burst' | 'react'
    let _lastResult = '';
    let _volume = 'say';
    let _confirmBeforeAct = true;
    let _advanced = false;
    let _jsonMode = false;
    let _jsonText = '';
    let _scene = null;
    let _pendingConfirm = null;

    const STYLE_ID = 'htc-styles';

    // ── styles ───────────────────────────────────────────────────────

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) return;
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

            .htc-digest { margin:10px 16px 0; background:#241a10; border:1px solid #40301c; border-radius:10px; padding:8px 12px; }
            .htc-digest .dt { font-size:10.5px; text-transform:uppercase; letter-spacing:1.1px; color:#ffb37a; margin-bottom:4px; }
            .htc-digest .di { font-size:12px; color:#e8c49a; padding:1px 0; }
            .htc-digest .drow { display:flex; gap:6px; margin-top:6px; }
            #htc-interject { flex:1; background:#141820; border:1px solid #40301c; color:#e6e8ee; border-radius:6px; padding:4px 9px; font-size:12px; outline:none; }
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
            .htc-phasebar { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
            #htc-phase { font-size:11.5px; padding:3px 11px; border-radius:999px; background:#14231a; color:#57c98f; border:1px solid #2c4a36; }
            #htc-phase.burst { background:#2b1f42; color:#d9baff; border-color:#4a3668; }
            #htc-phase.react { background:#241a10; color:#ffd28f; border-color:#40301c; }
            #htc-phase-note { font-size:11.5px; color:#78828e; }
            #htc-result { margin:0 0 8px 64px; font-size:12.5px; color:#98a3ae; border-left:3px solid #2c4a36; padding-left:10px; }
            #htc-result b { color:#57c98f; }

            .htc-crow { display:flex; gap:8px; align-items:center; margin-bottom:7px; }
            .htc-crow .lbl { width:56px; text-align:right; font-size:11.5px; color:#7d8894; flex:none; }
            .htc-crow input[type=text] { flex:1; background:#141820; border:1px solid #2a303b; color:#e6e8ee; border-radius:8px; padding:8px 11px; font-size:13px; outline:none; min-width:0; color-scheme:dark; }
            .htc-crow input[type=text]:focus { border-color:#4f9cf9; box-shadow:0 0 0 2px rgba(79,156,249,.22); }
            .htc-crow textarea { flex:1; background:#141820; border:1px solid #2a303b; border-radius:8px; color:#d9c9a9; font:inherit; resize:none; outline:none; padding:6px 11px; color-scheme:dark; }
            .htc-volseg { display:flex; border:1px solid #2a303b; border-radius:8px; overflow:hidden; flex:none; }
            .htc-volseg button { background:#1d212a; color:#8b95a1; border:0; padding:7px 8px; font-size:11px; border-right:1px solid #2a303b; cursor:pointer; }
            .htc-volseg button:last-child { border-right:0; }
            .htc-volseg button.on { background:#2b1f42; color:#d9baff; }
            .htc-btn-primary { background:#4f9cf9; border:0; color:#fff; font-weight:600; border-radius:8px; padding:8px 18px; flex:none; cursor:pointer; }
            .htc-btn-primary:hover { background:#61a9fa; }
            .htc-btn-primary.gold { background:#b3812f; }
            .htc-btn-primary:disabled { opacity:.45; cursor:default; }
            #htc-clear-do { background:none; border:0; color:#6b7686; cursor:pointer; font-size:12px; }

            #htc-preview { margin:4px 0 0 64px; font-family:Consolas,monospace; font-size:11px; color:#79e6a8; background:#0d1712; border:1px solid #1c3527; border-radius:8px; padding:5px 10px; white-space:pre-wrap; }
            .htc-footer-row { margin:7px 0 0 64px; display:flex; gap:14px; align-items:center; }
            .htc-linkbtn.endturn { color:#e08f8f; }
            #htc-advanced { margin:6px 0 0 64px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
            #htc-advanced select { background:#1d212a; color:#9aa3b2; border:1px solid #2a303b; border-radius:7px; padding:5px 8px; font-size:11.5px; color-scheme:dark; }
            #htc-advanced select:disabled { color:#55606c; }
            .htc-togglelbl { display:inline-flex; align-items:center; gap:5px; font-size:11.5px; color:#8b95a1; cursor:pointer; user-select:none; }
            #htc-json textarea { width:100%; min-height:110px; background:#141820; border:1px solid #2a303b; border-radius:8px; color:#79e6a8; font-family:Consolas,monospace; font-size:12px; padding:8px 11px; outline:none; resize:vertical; color-scheme:dark; }

            .htc-confirm-scrim { position:fixed; inset:0; z-index:1500; background:rgba(0,0,0,.6); }
            .htc-confirm-box { position:fixed; z-index:1501; left:50%; top:36%; transform:translate(-50%,-50%); width:min(480px,92vw); background:#1e2128; border:1px solid #333b47; border-radius:14px; padding:15px 17px; box-shadow:0 18px 60px rgba(0,0,0,.8); }
            .htc-confirm-box h5 { margin:0 0 9px; color:#e6e8ee; font-size:13.5px; }
            .htc-confirm-box pre { max-height:220px; overflow:auto; font-family:Consolas,monospace; font-size:11.5px; color:#79e6a8; background:#0d1712; border:1px solid #1c3527; border-radius:8px; padding:8px 10px; white-space:pre-wrap; margin:0 0 11px; }
            .htc-confirm-actions { display:flex; gap:10px; justify-content:flex-end; }
            .htc-btn-plain { background:none; border:1px solid #333a45; color:#9aa3b2; border-radius:6px; padding:6px 12px; cursor:pointer; }
            .htc-btn-danger { color:#e05a4e !important; }

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
    ];
    const VOLUME_WORDS = ['scream', 'shout', 'whisper'];

    /** Typed input → draft parts. Unknown verbs become speech. */
    function parseCmd(raw) {
        const t = (raw || '').trim();
        if (!t) return {};
        const lower = t.toLowerCase();
        for (const vol of VOLUME_WORDS) {
            if (lower.startsWith(vol + ' ')) {
                return { speech: t.slice(vol.length + 1).trim(), volume: vol };
            }
        }
        const verb = lower.split(/\s+/)[0];
        if (!VERBS.includes(verb)) return { speech: t };
        const rest = t.slice(verb.length).trim();
        const out = { action: verb };
        if (verb === 'give' || verb === 'steal') {
            const m = rest.split(/\s+(?:to|from)\s+/i);
            out.item = m[0] || '';
            out.target = m[1] || '';
        } else if (verb === 'use') {
            const on = rest.split(/\s+on\s+/i);
            out.item = on[0] || '';
            out.target = on[1] || '';
        } else if (rest) {
            out.item = rest;
        }
        return out;
    }

    /** Build the structured payload from the current rows. */
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
            if (parsed.item) p.item = parsed.item;
            if (parsed.target) p.target = parsed.target;
            const rel = m.querySelector('#htc-relation').value;
            if ((parsed.action === 'put' || parsed.action === 'place') && rel) p.relation = rel;
        }
        if (speech) {
            p.speech = speech;
            p.volume = parsed.volume || _volume;
        }
        if (emote) p.emote = emote;
        if (memory) p.memory = memory;
        return p;
    }

    /** Same normalization an agent reply goes through. */
    function normalizeReply(p) {
        if (!p || typeof p !== 'object') return { action: '', speech: null, speechVolume: 'say', emote: null, memory: null };
        const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
        return {
            action: ActionNormalizer.normalizeStructuredAction(p),
            speech,
            speechVolume: volume,
            emote: typeof p.emote === 'string' ? p.emote : null,
            memory: ResponseParser.extractMemory(p.memory),
        };
    }

    function updatePreview() {
        const node = _modal.querySelector('#htc-preview');
        if (_jsonMode || _phase === 'react') { node.style.display = 'none'; return; }
        const p = buildPayload();
        if (!Object.keys(p).length) { node.style.display = 'none'; return; }
        node.style.display = 'block';
        node.textContent = JSON.stringify(p, null, 1);
    }

    // ── build ────────────────────────────────────────────────────────

    function build() {
        if (_built) return;
        _built = true;
        ensureStyles();

        _overlay = el(htcPanelTag`<div id="htc-overlay" style="display:none"></div>`);
        _modal = el(htcPanelTag`<div id="htc-modal"></div>`);
        _overlay.appendChild(_modal);

        window.Lit.render(htcPanelTag`
          <div class="htc-header">
            <strong class="htc-title">✈ <span id="htc-title">Your turn</span></strong>
            <span class="htc-spacer"></span>
            <span id="htc-meta"></span>
          </div>
          <div id="htc-digest" style="display:none">
            <div class="dt">since your turn</div>
            <div id="htc-digest-lines"></div>
            <div class="drow">
              <input id="htc-interject" type="text" placeholder="quick reply… doesn't use your turn" autocomplete="off">
              <button type="button" id="htc-interject-btn" class="htc-linkbtn">interject ↩</button>
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
            <div class="htc-phasebar">
              <span id="htc-phase">① compose</span>
              <span id="htc-phase-note">one turn = do + say + emote together · menus fill the draft</span>
            </div>
            <div id="htc-result" style="display:none"></div>
            <div class="htc-crow" id="htc-do-row">
              <span class="lbl">⚙ do</span>
              <input id="htc-do" type="text" list="htc-names" placeholder='action — click things above or type "take burrito", "open door"…' autocomplete="off">
              <button type="button" id="htc-clear-do" title="clear">✕</button>
            </div>
            <div class="htc-crow">
              <span class="lbl">🗨 say</span>
              <input id="htc-speech" type="text" placeholder="what they say — stacks with the action" autocomplete="off">
              <div class="htc-volseg" id="htc-volseg"></div>
            </div>
            <div class="htc-crow">
              <span class="lbl">🎭 emote</span>
              <input id="htc-emote" type="text" placeholder='body language — "sneaks closer to the door"' autocomplete="off">
              <button type="button" id="htc-emote-toggle" class="htc-chiptoggle" title="emote quick-pick">🎭</button>
              <button type="button" id="htc-act" class="htc-btn-primary">Act</button>
            </div>
            <div id="htc-emote-palette" class="htc-emote-palette"></div>
            <div class="htc-crow">
              <span class="lbl">🧠 memory</span>
              <textarea id="htc-memory" rows="1" placeholder="optional — what you'll personally remember from this"></textarea>
              <button type="button" id="htc-skip-react" class="htc-linkbtn" style="display:none">skip react, end turn</button>
            </div>
            <div id="htc-preview" style="display:none"></div>
            <div class="htc-footer-row">
              <button type="button" id="htc-advanced-toggle" class="htc-linkbtn muted">▸ advanced</button>
              <button type="button" id="htc-json-toggle" class="htc-linkbtn muted">▸ raw json</button>
              <button type="button" id="htc-end" class="htc-linkbtn endturn">⏭ end turn</button>
            </div>
            <div id="htc-advanced" style="display:none">
              <select id="htc-relation"><option value="">relation: —</option><option value="on">on</option><option value="under">under</option><option value="beside">beside</option><option value="behind">behind</option><option value="at">at</option><option value="in">in</option></select>
              <select id="htc-where" disabled title="reserved — region targeting lands with task-211">
                <option>where: body region (task-211)</option>
              </select>
              <label class="htc-togglelbl"><input type="checkbox" id="htc-confirm-toggle" checked> confirm before Act</label>
            </div>
            <div id="htc-json" style="display:none">
              <textarea id="htc-json-text" rows="5" spellcheck="false" placeholder='{"action":"take","item":"flour sack"} — full structured payload'></textarea>
              <div class="htc-crow"><span class="lbl">{ }</span>
                <button type="button" id="htc-json-act" class="htc-btn-primary">Act (json)</button>
              </div>
            </div>
          </div>
          <datalist id="htc-names"></datalist>
        `, _modal);

        document.body.appendChild(_overlay);

        // volume segment
        const volseg = _modal.querySelector('#htc-volseg');
        for (const vol of ['say', 'whisper', 'shout', 'scream']) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = vol;
            btn.dataset.vol = vol;
            btn.addEventListener('click', () => {
                _volume = vol;
                syncVolumeButtons();
                updatePreview();
            });
            volseg.appendChild(btn);
        }
        syncVolumeButtons();

        // composer actions
        _modal.querySelector('#htc-act').addEventListener('click', onActButton);
        _modal.querySelector('#htc-end').addEventListener('click', () => finishAct({ endTurn: true }));
        _modal.querySelector('#htc-skip-react').addEventListener('click', () => finishReact({ endTurn: true }));
        _modal.querySelector('#htc-clear-do').addEventListener('click', () => {
            _modal.querySelector('#htc-do').value = '';
            updatePreview();
        });
        _modal.querySelector('#htc-do').addEventListener('input', updatePreview);
        _modal.querySelector('#htc-speech').addEventListener('input', updatePreview);
        _modal.querySelector('#htc-emote').addEventListener('input', updatePreview);
        _modal.querySelector('#htc-emote-toggle').addEventListener('click', () => {
            const wrap = _modal.querySelector('#htc-emote-palette');
            EmotePicker.toggle(wrap, {
                onPick: (emote) => {
                    const input = _modal.querySelector('#htc-emote');
                    if (input) input.value = emote;
                    updatePreview();
                }
            });
        });
        _modal.querySelector('#htc-act').addEventListener('click', () => {
            EmotePicker.close(_modal.querySelector('#htc-emote-palette'));
        });
        _modal.querySelector('#htc-memory').addEventListener('input', updatePreview);
        for (const id of ['htc-do', 'htc-speech', 'htc-emote']) {
            _modal.querySelector('#' + id).addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    onActButton();
                }
            });
        }

        // advanced / json
        _modal.querySelector('#htc-advanced-toggle').addEventListener('click', () => {
            _advanced = !_advanced;
            _modal.querySelector('#htc-advanced').style.display = _advanced ? 'flex' : 'none';
            _modal.querySelector('#htc-advanced-toggle').textContent = _advanced ? '▾ advanced' : '▸ advanced';
        });
        _modal.querySelector('#htc-confirm-toggle').addEventListener('change', (e) => {
            _confirmBeforeAct = e.target.checked;
        });
        _modal.querySelector('#htc-json-toggle').addEventListener('click', () => {
            _jsonMode = !_jsonMode;
            if (_jsonMode) _jsonText = JSON.stringify(buildPayload() || {}, null, 1);
            syncJsonMode();
        });
        _modal.querySelector('#htc-json-text').addEventListener('input', (e) => { _jsonText = e.target.value; });
        _modal.querySelector('#htc-json-act').addEventListener('click', () => {
            let parsedRaw;
            try {
                parsedRaw = JSON.parse(_jsonText || '{}');
            } catch (err) {
                events.log(`⚠️ Human turn JSON error: ${err.message}`, 'error-msg');
                return;
            }
            tryResolveAct(normalizeReply(parsedRaw));
        });

        // digest / interject (task-334 lanes 2+3, client-side)
        _modal.querySelector('#htc-interject-btn').addEventListener('click', interject);
        _modal.querySelector('#htc-interject').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') interject();
        });
        _modal.querySelector('#htc-digest-dismiss').addEventListener('click', () => {
            TurnFeed.clearDigest();
            _modal.querySelector('#htc-digest').style.display = 'none';
        });

        _modal.addEventListener('click', (e) => e.stopPropagation());
        _overlay.addEventListener('click', () => onOverlayDismiss());
        const closeOnEsc = (e) => {
            if (e.key === 'Escape' && _overlay.style.display !== 'none') onOverlayDismiss();
        };
        document.addEventListener('keydown', closeOnEsc);
    }

    function syncVolumeButtons() {
        if (!_modal) return;
        for (const btn of _modal.querySelectorAll('#htc-volseg button')) {
            btn.classList.toggle('on', btn.dataset.vol === _volume);
        }
    }

    function syncJsonMode() {
        const m = _modal;
        m.querySelector('#htc-json').style.display = _jsonMode ? 'block' : 'none';
        const rows = m.querySelectorAll('.htc-crow, #htc-preview, .htc-footer-row');
        for (const row of rows) row.style.display = _jsonMode ? 'none' : '';
        m.querySelector('#htc-json-toggle').textContent = _jsonMode ? '▾ raw json' : '▸ raw json';
        if (_jsonMode) m.querySelector('#htc-json-text').value = _jsonText;
        if (!_jsonMode) updatePreview();
    }

    async function interject() {
        const input = _modal.querySelector('#htc-interject');
        const text = (input.value || '').trim();
        if (!text || !_charName) return;
        input.value = '';
        events.log(`💬 ${_charName} interjected (turn not used): "${text}"`, 'msg-action');
        try {
            const data = await ApiClient.action('say ' + text, _charName);
            if (data?.output) {
                events.log(data.output, 'system-msg');
            } else if (data?.error) {
                events.log(`❌ ${data.error}`, 'error-msg');
            }
        } catch (err) {
            events.log(`❌ Interjection failed: ${err.message}`, 'error-msg');
        }
        TurnFeed.clearDigest();
        _modal.querySelector('#htc-digest').style.display = 'none';
    }

    // ── phase / resolve plumbing ─────────────────────────────────────

    function setPhase(phase) {
        _phase = phase;
        const m = _modal;
        const pill = m.querySelector('#htc-phase');
        pill.classList.remove('burst', 'react');
        if (phase === 'burst') { pill.textContent = '⚡ dash burst — one more action'; pill.classList.add('burst'); }
        else if (phase === 'react') { pill.textContent = '② react to the result'; pill.classList.add('react'); }
        else pill.textContent = '① compose';
        m.querySelector('#htc-phase-note').textContent = phase === 'react'
            ? 'say / emote / note only — the world already answered'
            : 'one turn = do + say + emote together · menus fill the draft';
        m.querySelector('#htc-do-row').style.display = phase === 'react' ? 'none' : 'flex';
        m.querySelector('#htc-result').style.display = phase === 'react' ? 'block' : 'none';
        const actBtn = m.querySelector('#htc-act');
        actBtn.textContent = phase === 'react' ? 'close turn' : (phase === 'burst' ? 'Act (last one)' : 'Act');
        actBtn.classList.toggle('gold', phase === 'react');
        m.querySelector('#htc-skip-react').style.display = phase === 'react' ? '' : 'none';
        m.querySelector('#htc-end').style.display = phase === 'react' ? 'none' : '';
        m.querySelector('#htc-speech').placeholder = phase === 'react'
            ? 'react to what just happened…'
            : 'what they say — stacks with the action';
    }

    function showResult(text) {
        const node = _modal.querySelector('#htc-result');
        node.textContent = '';
        const b = document.createElement('b');
        b.textContent = 'result: ';
        node.appendChild(b);
        node.appendChild(document.createTextNode(text || ''));
        node.style.display = 'block';
    }

    function renderDigest() {
        const entries = TurnFeed.digest().slice(-4);
        const box = _modal.querySelector('#htc-digest');
        if (_phase === 'react' || !entries.length) { box.style.display = 'none'; return; }
        const lines = _modal.querySelector('#htc-digest-lines');
        lines.textContent = '';
        for (const entry of entries) lines.appendChild(el(htcPanelTag`<div class="di"></div>`));
        lines.textContent = '';
        for (const entry of entries) {
            const line = document.createElement('div');
            line.className = 'di';
            line.textContent = '• ' + entry.text;
            lines.appendChild(line);
        }
        box.style.display = 'block';
    }

    function renderMeta() {
        const meta = _modal.querySelector('#htc-meta');
        const bits = [];
        if (typeof worldState !== 'undefined' && worldState.tick) bits.push(`tick ${worldState.tick}`);
        let nextUp = '';
        try {
            if (config.turnBased && typeof TurnQueue !== 'undefined') {
                nextUp = TurnQueue.getCurrentCharacter?.() || '';
            }
        } catch { /* queue not initialized */ }
        if (nextUp && nextUp !== _charName) bits.push(`next up: <b>${nextUp}</b>`);
        else if (nextUp) bits.push('next up: <b>you</b>');
        meta.innerHTML = bits.join(' · ');
    }

    function renderDatalist() {
        const dl = _modal.querySelector('#htc-names');
        dl.textContent = '';
        if (!_scene) return;
        const names = new Set();
        for (const item of _scene.items || []) names.add(item.name);
        for (const p of _scene.people || []) names.add(p.display_name);
        for (const way of _scene.ways || []) { names.add(way.direction); if (way.to) names.add(way.to); }
        for (const inv of [...(_scene.you?.carrying || []), ...(_scene.you?.wearing || [])]) names.add(inv.name);
        for (const name of names) {
            const opt = document.createElement('option');
            opt.value = name;
            dl.appendChild(opt);
        }
    }

    /** Draft fill entry point for scene menus + the You strip. */
    function applyDraft(parts) {
        const m = _modal;
        if (!parts) return;
        if (_phase === 'react') return; // menus are compose-phase only
        m.querySelector('#htc-do').value = [parts.action, parts.item, parts.target]
            .filter(Boolean).join(' ');
        updatePreview();
        m.querySelector('#htc-speech').focus();
    }

    function onActButton() {
        if (_phase === 'react') { closeTurn(); return; }
        const payload = buildPayload();
        if (!payload.action && !payload.speech && !payload.emote) return;
        if (_confirmBeforeAct && !_pendingConfirm) {
            _pendingConfirm = payload;
            showConfirm(payload);
            return;
        }
        _pendingConfirm = null;
        hideConfirm();
        tryResolveAct(normalizeReply(payload));
    }

    function closeTurn() {
        const m = _modal;
        const payload = {
            speech: (m.querySelector('#htc-speech').value || '').trim(),
            volume: _volume,
            emote: (m.querySelector('#htc-emote').value || '').trim(),
            memory: (m.querySelector('#htc-memory').value || '').trim(),
        };
        if (!payload.speech && !payload.emote && !payload.memory) {
            finishReact({ endTurn: true });
            return;
        }
        finishReact(normalizeReply(payload));
    }

    function tryResolveAct(reply) {
        if (typeof _activeResolve !== 'function') return;
        const resolve = _activeResolve;
        _activeResolve = null;
        TurnFeed.markTurnEnd();
        hidePanel();
        resolve(reply);
    }

    function finishAct(reply) { tryResolveAct(reply); }

    function finishReact(reply) {
        if (typeof _reactResolve !== 'function') return;
        const resolve = _reactResolve;
        _reactResolve = null;
        TurnFeed.markTurnEnd();
        hidePanel();
        resolve(reply);
    }

    function onOverlayDismiss() {
        if (_pendingConfirm) { _pendingConfirm = null; hideConfirm(); return; }
        if (typeof _reactResolve === 'function') { finishReact({ endTurn: true }); return; }
        finishAct({ endTurn: true });
    }

    // ── confirm overlay ──────────────────────────────────────────────

    function showConfirm(payload) {
        hideConfirm();
        const scrim = document.createElement('div');
        scrim.className = 'htc-confirm-scrim';
        scrim.addEventListener('click', hideConfirm);
        const box = document.createElement('div');
        box.className = 'htc-confirm-box';
        const h = document.createElement('h5');
        h.textContent = 'commit this turn?';
        const pre = document.createElement('pre');
        pre.textContent = JSON.stringify(payload, null, 1);
        const actions = document.createElement('div');
        actions.className = 'htc-confirm-actions';
        const cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'htc-btn-plain';
        cancel.textContent = '✕ cancel';
        cancel.addEventListener('click', hideConfirm);
        const go = document.createElement('button');
        go.type = 'button';
        go.className = 'htc-btn-primary';
        go.textContent = '✔ confirm & act';
        go.addEventListener('click', () => {
            _pendingConfirm = null;
            hideConfirm();
            tryResolveAct(normalizeReply(payload));
        });
        actions.appendChild(cancel);
        actions.appendChild(go);
        box.appendChild(h);
        box.appendChild(pre);
        box.appendChild(actions);
        document.body.appendChild(scrim);
        document.body.appendChild(box);
        _confirmNodes = [scrim, box];
    }

    let _confirmNodes = null;
    function hideConfirm() {
        if (_confirmNodes) {
            for (const node of _confirmNodes) node.remove();
            _confirmNodes = null;
        }
    }

    // ── panel open/close ─────────────────────────────────────────────

    function hidePanel() {
        if (_overlay) _overlay.style.display = 'none';
        hideConfirm();
    }

    function resetRows() {
        for (const id of ['htc-do', 'htc-speech', 'htc-emote', 'htc-memory']) {
            _modal.querySelector('#' + id).value = '';
        }
        _modal.querySelector('#htc-relation').value = '';
        _jsonText = '';
        updatePreview();
    }

    /**
     * Shared panel open for both phases. phase: 'compose' | 'burst' | 'react'.
     * compose/burst resolve via _activeResolve; react via _reactResolve.
     */
    function openPanel(charName, phase, opts = {}) {
        build();
        _charName = charName;
        _lastResult = opts.lastResult || '';
        _pendingConfirm = null;
        hideConfirm();
        resetRows();

        const m = _modal;
        m.querySelector('#htc-title').textContent = charName + "'s turn";
        if (phase === 'burst') {
            m.querySelector('#htc-do').placeholder = 'second action — your dash bought you one more…';
        } else {
            m.querySelector('#htc-do').placeholder = 'action — click things above or type "take burrito", "open door"…';
        }

        setPhase(phase);
        if (phase === 'react') showResult(_lastResult);

        // scene + feed + you strip + meta + datalist
        const sceneHost = m.querySelector('#htc-scene');
        sceneHost.textContent = 'reading the room…';
        const stripHandlers = {
            onDraft: applyDraft,
            menu: (x, y, title, buttons) =>
                window.TurnSceneView.menu(x, y, title, buttons, applyDraft),
        };
        if (window.TurnSceneView) {
            window.TurnSceneView.fetch(charName).then((scene) => {
                if (!scene || scene.error || _charName !== charName) return;
                _scene = scene;
                window.TurnSceneView.renderScene(sceneHost, scene, {
                    onDraft: applyDraft,
                    onTalkFocus: () => m.querySelector('#htc-speech').focus(),
                });
                window.TurnYouStrip.render(m.querySelector('#htc-you'), scene.you, stripHandlers);
                renderDatalist();
            }).catch(() => {
                sceneHost.textContent = '';
                sceneHost.appendChild(document.createTextNode('scene unavailable.'));
            });
        }
        TurnFeed.render(m.querySelector('#htc-feed-lines'));
        renderMeta();
        renderDigest();

        m.querySelector('#htc-json').style.display = 'none';
        _jsonMode = false;
        syncJsonMode();
        _overlay.style.display = 'flex';
        (phase === 'react' ? m.querySelector('#htc-speech') : m.querySelector('#htc-do')).focus();
    }

    /**
     * Compose (or burst) phase. Resolves with the normalized act reply
     * or {endTurn:true}. opts: { burst:boolean, lastResult:string }.
     */
    function request(charName, opts = {}) {
        if (_activeResolve) {
            return new Promise((resolve) => { _activeResolve = resolve; });
        }
        openPanel(charName, opts.burst ? 'burst' : 'compose', opts);
        return new Promise((resolve) => { _activeResolve = resolve; });
    }

    /**
     * React phase (task-334 lane 1): say/emote/memory bound to lastResult.
     * Resolves with the normalized react reply or {endTurn:true}.
     */
    function react(charName, lastResult) {
        if (_reactResolve) {
            return new Promise((resolve) => { _reactResolve = resolve; });
        }
        openPanel(charName, 'react', { lastResult });
        return new Promise((resolve) => { _reactResolve = resolve; });
    }

    return { request, react };
})();
