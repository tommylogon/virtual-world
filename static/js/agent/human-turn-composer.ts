/**
 * human-turn-composer.js - the human turn PANEL (task-333; continuous multi-action v4, task-352)
 *
 * @module agent/human-turn-composer - the panel you play a character from
 * @contributes HumanTurnComposer: scene view, feed/digest, You strip, step composer, budget pips, react beat
 * @powers The human turn, Turn queue - actually taking a turn as a character
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
 * pip. Only the action charges `action_points`; `wait` and the free utility actionNames
 * cost a free slot. The old `dash burst` phase and its narration regex are gone.
 *
 * Contract with agent-engine.js:
 *   request(charName, opts?) → Promise<{ step: NormalizedReply } | {endTurn:true}>
 *       Opens the panel on the first call; subsequent calls refresh it and arm
 *       the next step. Never hides - the turn is one continuous panel.
 *   react(charName, results) → Promise<{speech, volume, emote, memory, target} | {endTurn:true}>
 *       The single closing beat after the turn ran (task-334 lane 1).
 *   closeTurn()              → hides the panel (call once the turn is done).
 *
 * Load AFTER response-parser.js / turn-scene-view.js / turn-you-strip.js /
 * turn-feed.js / action-tiers.js, BEFORE agent-engine.js.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const htcPanelTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);

const HumanTurnComposerModule = (() => {
    'use strict';

    let _activeResolve: ((value: TurnResult) => void) | null = null;
    let _reactResolve: ((value: ReactResult) => void) | null = null;
    let _phase: 'compose' | 'react' = 'compose';
    let _built = false;
    let _modal!: HTMLElement;
    let _overlay!: HTMLElement;
    let _charName: string | null = null;
    let _volume = 'say';
    let _pendingSpeechTarget: string | null = null;
    let _advanced = false;
    let _scene: Record<string, any> | null = null;
    let _currentPrefill: TurnPrefill | null = null;
    let _lastReactionText = '';
    let _lastCommittedAction = '';
    let _dryRun = false;

    const q = (sel: string) => {
        if (!_built || !_modal) {
            try { build(); } catch { /* headless unit stub */ }
        }
        const find = (s: string) => (
            _modal?.querySelector?.(s) ||
            document.querySelector?.(s) ||
            (s.startsWith('#') ? document.getElementById?.(s.slice(1)) : null)
        ) as HTMLElement;
        if (sel === '#htc-commit') return find('#htc-commit') || find('#htc-act');
        if (sel === '#htc-reroll') return find('#htc-reroll') || find('#htc-reroll-btn') || find('#htc-ask-director');
        return find(sel);
    };
    const qa = (sel: string): HTMLElement[] => {
        if (!_built || !_modal) {
            try { build(); } catch { /* headless unit stub */ }
        }
        const fromModal = _modal && typeof _modal.querySelectorAll === 'function'
            ? Array.from(_modal.querySelectorAll(sel))
            : [];
        if (fromModal.length) return fromModal as HTMLElement[];
        return typeof document.querySelectorAll === 'function'
            ? (Array.from(document.querySelectorAll(sel)) as HTMLElement[])
            : [];
    };

    const STYLE_ID = 'htc-styles';

    function actionTiers(): { tierOf?: (v: string) => string } | null {
        return (window as unknown as { ActionTiers?: { tierOf?: (v: string) => string } }).ActionTiers || null;
    }

    // ── styles ───────────────────────────────────────────────────────

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            #htc-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:13000; display:none; align-items:center; justify-content:center; }
            #htc-modal { background:#1e2128; color:#e6e8ee; width:min(1080px,96vw); max-height:94vh; display:flex; flex-direction:column; overflow:hidden; border-radius:14px; border:1px solid #333a45; box-shadow:0 18px 60px rgba(0,0,0,.6); font-family:inherit; font-size:13px; }
            .htc-header { padding:8px 16px; border-bottom:1px solid #333a45; display:flex; align-items:center; gap:10px; background:#1a1d24; border-radius:14px 14px 0 0; flex-shrink:0; }
            .htc-title { font-size:14px; font-weight:600; }
            .htc-spacer { flex:1; }
            #htc-meta { color:#78828e; font-size:11.5px; }
            #htc-meta b { color:#b48ce0; }
            #htc-close { background:none; border:0; color:#6b7686; cursor:pointer; font-size:15px; }

            .htc-linkbtn { background:none; border:0; color:#ffb37a; font-size:11.5px; cursor:pointer; }
            .htc-linkbtn.muted { color:#6b7686; }

            .htc-grid { display:grid; grid-template-columns: 1fr 300px; flex:1 1 auto; min-height:0; overflow:hidden; }
            #htc-scene { overflow-y:auto; min-height:0; max-height:100%; }
            .htc-feed { border-left:1px solid #333a45; padding:8px 14px; min-height:0; max-height:100%; overflow-y:auto; }
            .htc-feed h4 { margin:0 0 7px; font-size:10.5px; text-transform:uppercase; letter-spacing:1.2px; color:#6b7686; }
            .tfd-line { color:#98a3ae; font-size:12px; padding:2px 0 2px 10px; line-height:1.45; border-left:2px solid #232932; margin-bottom:3px; }
            .tfd-line.tfd-act { color:#bcd3ec; }
            .tfd-line.tfd-err { color:#e08f8f; }
            .tfd-line.tfd-sys { color:#6b7686; }
            .tfd-line.tfd-empty { color:#5b6570; font-style:italic; border-left-color:transparent; }
            @media (max-width: 940px) { .htc-grid { grid-template-columns: 1fr; } .htc-feed { border-left:0; border-top:1px solid #333a45; max-height:150px; } }

            #htc-you { flex-shrink:0; max-height:16vh; overflow-y:auto; }
            .htc-composer { border-top:1px solid #333a45; background:#1a1d24; padding:8px 16px 10px; border-radius:0 0 14px 14px; flex-shrink:0; }
            .htc-budget { display:flex; align-items:center; gap:14px; margin-bottom:6px; }
            .htc-pips { display:flex; align-items:center; gap:6px; }
            .htc-pip { width:15px; height:15px; display:inline-block; }
            .htc-pip.major { border:2px solid #d9baff; transform:rotate(45deg); border-radius:3px; }
            .htc-pip.minor { border:2px solid #4f9cf9; border-radius:3px; }
            .htc-pip.free { border-radius:50%; border:2px solid #57c98f; width:12px; height:12px; }
            .htc-pip.spent { opacity:.22; }
            .htc-budgetlab { font-size:11.5px; color:#78828e; }
            .htc-budgetlab b { color:#e6e8ee; }
            #htc-phase-note { font-size:11.5px; color:#78828e; margin-left:auto; }
            #htc-result { margin:0 0 6px 64px; font-size:12.5px; color:#98a3ae; border-left:3px solid #2c4a36; padding-left:10px; max-height:160px; overflow-y:auto; }
            #htc-result.htc-expanded { max-height:none; }
            #htc-result b { color:#57c98f; }
            .htc-res-card { margin-bottom:7px; }
            .htc-res-card:last-child { margin-bottom:0; }
            .htc-res-action { line-height:1.45; color:#cfd8dc; font-weight:500; }
            .htc-res-prose { margin-top:4px; line-height:1.45; color:#a4b1be; font-style:italic; }
            .htc-res-status { margin-top:4px; color:#f59e0b; font-size:12px; }
            .htc-res-people { margin-top:4px; font-size:11.5px; color:#81a1c1; }
            .htc-res-people .htc-res-hint { color:#5f7488; font-style:italic; font-size:11px; }
            .htc-res-details { margin-top:6px; font-size:11px; }
            .htc-res-details summary { cursor:pointer; color:#6e8498; user-select:none; }
            .htc-res-details summary:hover { color:#8ba2b8; }
            .htc-res-tail-body { margin-top:4px; padding-left:8px; border-left:1px solid #23372c; max-height:120px; overflow-y:auto; }
            .htc-res-tail-line { margin:2px 0; color:#6e8498; font-family:monospace; font-size:10.5px; white-space:pre-wrap; }
            .htc-res-toggle-expand { background:none; border:0; color:#4f9cf9; font-size:11px; cursor:pointer; padding:2px 0; margin-top:4px; display:inline-block; }
            .htc-res-toggle-expand:hover { text-decoration:underline; }

            .htc-director-bar { display:flex; gap:8px; align-items:center; margin-bottom:6px; padding:5px 9px; background:#151821; border:1px solid #2b3240; border-radius:8px; }
            .htc-director-btn { background:#6a4fb8; border:0; color:#fff; font-weight:600; border-radius:7px; padding:5px 11px; font-size:12px; cursor:pointer; flex:none; }
            .htc-director-btn:hover { background:#7b5ec9; }
            .htc-director-btn:disabled { opacity:.5; cursor:default; }
            #htc-director-note { flex:1; background:#10131a; border:1px solid #2a303b; color:#e6e8ee; border-radius:7px; padding:5px 10px; font-size:12px; outline:none; min-width:0; color-scheme:dark; }
            #htc-director-note:focus { border-color:#7c8cf8; }
            .htc-autodraft-wrap { display:inline-flex; align-items:center; gap:5px; font-size:11.5px; color:#9aa3b2; cursor:pointer; flex:none; user-select:none; }

            .htc-row, .htc-crow { display:flex; gap:8px; align-items:center; margin-bottom:5px; }
            .htc-row label, .htc-crow .lbl { width:56px; text-align:right; font-size:11.5px; color:#7d8894; flex:none; }
            .htc-row input[type=text], .htc-crow input[type=text] { flex:1; background:#141820; border:1px solid #2a303b; color:#e6e8ee; border-radius:8px; padding:6px 10px; font-size:13px; outline:none; min-width:0; color-scheme:dark; }
            .htc-row input[type=text]:focus, .htc-crow input[type=text]:focus { border-color:#4f9cf9; box-shadow:0 0 0 2px rgba(79,156,249,.22); }
            #htc-emotion { background:#1d212a; color:#c8d1dc; border:1px solid #2a303b; border-radius:8px; padding:5px 8px; font-size:12px; flex:none; color-scheme:dark; }
            #htc-thought-clear { background:none; border:0; color:#6b7686; cursor:pointer; font-size:14px; padding:2px 6px; }
            .htc-say-target { display:none; align-items:center; gap:4px; background:#2b1f42; color:#d9baff; border:1px solid #4a3570; border-radius:6px; padding:3px 8px; font-size:11.5px; flex:none; }
            .htc-say-target button { background:none; border:0; color:#d9baff; cursor:pointer; font-size:12px; padding:0 2px; line-height:1; }
            .htc-volseg { display:flex; border:1px solid #2a303b; border-radius:8px; overflow:hidden; flex:none; }
            .htc-volseg button { background:#1d212a; color:#8b95a1; border:0; padding:5px 8px; font-size:11px; border-right:1px solid #2a303b; cursor:pointer; }
            .htc-volseg button:last-child { border-right:0; }
            .htc-volseg button.on { background:#2b1f42; color:#d9baff; }
            .htc-btn-primary { background:#4f9cf9; border:0; color:#fff; font-weight:600; border-radius:8px; padding:6px 16px; flex:none; cursor:pointer; }
            .htc-btn-primary:hover { background:#61a9fa; }
            .htc-btn-primary.gold { background:#b3812f; }
            .htc-btn-primary:disabled { opacity:.45; cursor:default; }
            #htc-clear-do { background:none; border:0; color:#6b7686; cursor:pointer; font-size:12px; }

            .htc-footer-row { margin:5px 0 0 64px; display:flex; gap:14px; align-items:center; }
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

    function el(template: unknown): Element | null {
        const t = document.createElement('div');
        window.Lit.render(template, t);
        return t.firstElementChild;
    }

    // ── typed one-box parsing ────────────────────────────────────────

    const ACTIONS = [
        'look', 'go', 'approach', 'take', 'drop', 'place', 'put', 'give', 'use', 'examine',
        'attack', 'open', 'close', 'read', 'search', 'wear', 'equip', 'remove', 'unequip',
        'rest', 'sleep', 'wait', 'nothing', 'dash', 'crawl', 'climb', 'jump', 'grab',
        'steal', 'light', 'ignite', 'vanish', 'manifest', 'toggle', 'listen',
        'wake', 'meditate', 'bathe', 'stand', 'release', 'escape', 'struggle', 'lead',
        'fear', 'interest', 'eat', 'drink',
        'teach', 'kiss', 'caress', 'lick', 'suck', 'bite', 'pinch', 'blow', 'tickle',
        'text', 'message',
    ];
    const VOLUME_WORDS = ['scream', 'shout', 'whisper'];

    /** Typed input → draft parts. Unknown actionNames become speech. */
    function parseCmd(raw: string): ParsedCmd {
        const t = (raw || '').trim();
        if (!t) return {};
        const lower = t.toLowerCase();
        for (const vol of VOLUME_WORDS) {
            if (lower.startsWith(vol + ' ')) {
                return { speech: t.slice(vol.length + 1).trim(), volume: vol };
            }
        }
        const actionWord = lower.split(/\s+/)[0];
        if (!ACTIONS.includes(actionWord)) return { speech: t };
        const rest = t.slice(actionWord.length).trim();
        const out: ParsedCmd = { action: actionWord };
        if (actionWord === 'give' || actionWord === 'steal' || actionWord === 'teach') {
            const m = rest.split(/\s+(?:to|from)\s+/i);
            out.item = m[0] || '';
            out.target = m[1] || '';
        } else if (actionWord === 'use') {
            const on = rest.split(/\s+on\s+/i);
            out.item = on[0] || '';
            out.target = on[1] || '';
        } else if (rest) {
            out.item = rest;
        }
        return out;
    }

    /**
     * Feedback hint when typed text in the do field will be spoken rather than run as an action (task-878).
     *
     * When raw text has speech but no action and does not start with a deliberate volume word (scream, shout, whisper),
     * returns a warning string with suggestions. Otherwise returns null.
     */
    function doHint(raw: string): string | null {
        const t = (raw || '').trim();
        if (!t) return null;
        const lower = t.toLowerCase();
        for (const vol of VOLUME_WORDS) {
            if (lower.startsWith(vol + ' ') || lower === vol) return null;
        }
        const parsed = parseCmd(t);
        if (parsed.speech && !parsed.action) {
            const actionWord = lower.split(/\s+/)[0];
            const ALIASES: Record<string, string> = {
                walk: 'go, approach',
                run: 'dash, go',
                move: 'go',
                travel: 'go',
                head: 'go',
                grab: 'take, grab',
                pick: 'take',
                get: 'take',
                hit: 'attack',
                strike: 'attack',
                fight: 'attack',
                consume: 'eat, drink',
                ingest: 'eat, drink',
                sip: 'drink',
                quaff: 'drink',
                talk: 'say (use say box)',
                speak: 'say (use say box)',
            };
            const suggest = ALIASES[actionWord] || ACTIONS.filter((v) => v.startsWith(actionWord.slice(0, 2))).slice(0, 3).join(', ');
            return `"${t}" will be spoken aloud. (Did you mean: ${suggest || 'go, look, take, use, attack'}?)`;
        }
        return null;
    }

    /** Build the payload from the current rows. */
    function buildPayload(): TurnPayload {
        const doRaw = ((q('#htc-do') as HTMLInputElement)?.value || '');
        const parsed = parseCmd(doRaw);
        const speech = ((q('#htc-speech') as HTMLInputElement)?.value || '').trim() || parsed.speech || '';
        const emote = ((q('#htc-emote') as HTMLInputElement)?.value || '').trim();
        const memory = ((q('#htc-memory') as HTMLInputElement)?.value || '').trim();
        const p: TurnPayload = {};
        if (parsed.action) {
            p.action = parsed.action;
            if (parsed.item) p.item = parsed.item;
            if (parsed.target) p.target = parsed.target;
            const rel = ((q('#htc-relation') as HTMLSelectElement)?.value || '');
            if ((parsed.action === 'put' || parsed.action === 'place') && rel) p.relation = rel;
        }
        if (speech) {
            p.speech = speech;
            p.volume = parsed.volume || _volume;
            const toneVal = ((q('#htc-tone') as HTMLSelectElement | null)?.value || '').trim();
            if (toneVal) p.tone = toneVal;
            if (_pendingSpeechTarget && !p.target) p.target = _pendingSpeechTarget;
        }
        if (emote) p.emote = emote;
        if (memory) p.memory = memory;
        return p;
    }

    /** Same normalization an agent reply goes through. */
    function normalizeReply(p: Record<string, any> | null | undefined): NormalizedReply {
        if (!p || typeof p !== 'object') return { action: '', speech: null, speechVolume: 'say', speechTone: null, emote: null, memory: null, target: null };
        const { speech, volume, tone } = ActionNormalizer.extractSpeechVolume(p);
        return {
            action: ActionNormalizer.normalizeStructuredAction(p),
            speech,
            speechVolume: volume,
            speechTone: tone || null,
            target: (typeof p.target === 'string' && p.target.trim()) ? p.target.trim() : null,
            emote: typeof p.emote === 'string' ? p.emote : null,
            memory: ResponseParser.extractMemory(p.memory),
        };
    }

    // ── turn budget ──────────────────────────────────────────────────

    function turnSlots(): Record<string, number> | null {
        const player = _charName ? worldState.runtimePlayer(_charName) : null;
        const slots = player?.action_points;
        if (!slots || typeof slots !== 'object') return null;
        // bug-544: `Player.action_points` starts as `{}` ("not started yet" -
        // player.py), and the engine's `_slot_gate` lazily fills an empty budget.
        // So an EMPTY object means "no budget published", NOT "all slots spent".
        // Reading `{}` as spent refused the first action of a fresh turn.
        return Object.keys(slots).length ? { ...slots } : null;
    }

    function renderPips() {
        const defaultBudget = (window as unknown as { ActionTiers?: { DEFAULT_BUDGET: Record<string, number> } }).ActionTiers?.DEFAULT_BUDGET || { major: 1, minor: 1, free: 3 };
        const s = turnSlots() || { ...defaultBudget };
        const pipsEl = q('#htc-pips');
        if (!pipsEl || typeof pipsEl.replaceChildren !== 'function') return;
        pipsEl.replaceChildren();

        const majorPip = document.createElement('span');
        majorPip.className = `htc-pip major ${s.major ? '' : 'spent'}`;
        majorPip.title = `major ${s.major || 0} left`;
        pipsEl.appendChild(majorPip);

        const minorPip = document.createElement('span');
        minorPip.className = `htc-pip minor ${s.minor ? '' : 'spent'}`;
        minorPip.title = `minor ${s.minor || 0} left`;
        pipsEl.appendChild(minorPip);

        for (let i = 0; i < 3; i += 1) {
            const freePip = document.createElement('span');
            freePip.className = `htc-pip free ${i < (s.free || 0) ? '' : 'spent'}`;
            freePip.title = `free ${s.free || 0} left`;
            pipsEl.appendChild(freePip);
        }

        const budgetEl = q('#htc-budgetlab');
        if (!budgetEl || typeof budgetEl.replaceChildren !== 'function') return;
        budgetEl.replaceChildren();
        const bMajor = document.createElement('b');
        bMajor.textContent = String(s.major || 0);
        const bMinor = document.createElement('b');
        bMinor.textContent = String(s.minor || 0);
        const bFree = document.createElement('b');
        bFree.textContent = String(s.free || 0);
        budgetEl.append(bMajor, ' major · ', bMinor, ' minor · ', bFree, ' free');
    }

    function setPhase(phase: 'compose' | 'react') {
        _phase = phase;
        const react = phase === 'react';
        const doRow = q('#htc-do-row');
        if (doRow?.style) doRow.style.display = react ? 'none' : 'flex';
        const actBtn = q('#htc-act');
        if (actBtn?.style) actBtn.style.display = react ? 'none' : '';
        const rerollBtn = q('#htc-reroll-btn');
        if (rerollBtn?.style && react) rerollBtn.style.display = 'none';
        const reactBtn = q('#htc-react-btn');
        if (reactBtn?.style) reactBtn.style.display = react ? '' : 'none';
        const endBtn = q('#htc-end');
        if (endBtn?.style) endBtn.style.display = react ? 'none' : '';
        const isAuto = Boolean(typeof events !== 'undefined' && events?.isAutoDraft?.(_charName));
        const titleEl = q('#htc-title');
        if (titleEl) {
            titleEl.textContent = react
                ? `${_charName}'s reaction`
                : (isAuto ? `🎬 Directed: ${_charName}'s turn` : `${_charName}'s turn`);
        }
        const phaseNoteEl = q('#htc-phase-note');
        if (phaseNoteEl) {
            phaseNoteEl.textContent = react
                ? 'say / emote / memory - the turn already ran'
                : (isAuto
                    ? 'Review and edit the drafted turn, then press Act to commit'
                    : 'act · say · emote · memory are all free - only actions spend pips');
        }
        const doInput = q('#htc-do') as HTMLInputElement | null;
        if (doInput) {
            doInput.placeholder = react
                ? 'react to what happened…'
                : 'action - click a thing above, or type "eat berries", "open door"…';
        }
        const speechInput = q('#htc-speech') as HTMLInputElement | null;
        if (speechInput) {
            speechInput.placeholder = react
                ? 'what they say back…'
                : 'what they say - free, stacks with the action';
        }
    }

    function setBusy(on: boolean) {
        const actBtn = q('#htc-act') as HTMLButtonElement | null;
        if (actBtn) actBtn.disabled = on;
    }

    interface ParsedResult {
        actionLine: string;
        proseLines: string[];
        statusLines: string[];
        peopleSummary: string[];
        rawTailLines: string[];
        rawText: string;
    }

    function parseResultText(text: string): ParsedResult {
        const rawText = text || '';
        const lines = rawText.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
        if (!lines.length) {
            return { actionLine: '', proseLines: [], statusLines: [], peopleSummary: [], rawTailLines: [], rawText };
        }

        let actionLine = '';
        const proseLines: string[] = [];
        const statusLines: string[] = [];
        const rawTailLines: string[] = [];
        const peopleNames: string[] = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            // 1. First line is typically the action outcome (e.g. You head through... / You pick up...)
            if (i === 0 && (line.startsWith('You ') || line.startsWith('you ') || !line.startsWith('['))) {
                actionLine = line;
                continue;
            }

            // 2. Status effect alerts: [!] ...
            if (line.startsWith('[!]')) {
                statusLines.push(line.replace(/^\s*\[!\]\s*/, ''));
                continue;
            }

            // 3. Trailing way listings: [way_id] area is visible beyond... / [door_id] ...
            if (/^\[[a-zA-Z0-9_-]+\]/.test(line)) {
                rawTailLines.push(line);
                continue;
            }

            // 4. Character look paragraphs: name - description... [wearing: ...] [holding: ...]
            if (line.includes('[wearing:') || line.includes('[holding:')) {
                rawTailLines.push(line);
                const matchName = line.match(/^([a-zA-Z0-9_ -]+?)\s*[--]/);
                if (matchName && matchName[1]) {
                    peopleNames.push(matchName[1].trim());
                }
                continue;
            }

            // 5. Normal room prose / descriptions
            proseLines.push(line);
        }

        return {
            actionLine,
            proseLines,
            statusLines,
            peopleSummary: peopleNames,
            rawTailLines,
            rawText
        };
    }

    function renderStructuredResult(container: HTMLElement, parsed: ParsedResult, prefix: string) {
        const card = document.createElement('div');
        card.className = 'htc-res-card';

        // 1. Action / Movement line
        if (parsed.actionLine || prefix) {
            const actDiv = document.createElement('div');
            actDiv.className = 'htc-res-action';
            const b = document.createElement('b');
            b.textContent = prefix ? `${prefix}: ` : 'last: ';
            actDiv.appendChild(b);
            if (parsed.actionLine) {
                actDiv.appendChild(document.createTextNode(parsed.actionLine));
            }
            card.appendChild(actDiv);
        }

        // 2. Room prose
        if (parsed.proseLines.length > 0) {
            const proseDiv = document.createElement('div');
            proseDiv.className = 'htc-res-prose';
            proseDiv.textContent = parsed.proseLines.join(' ');
            card.appendChild(proseDiv);
        }

        // 3. Status effect lines ([!])
        if (parsed.statusLines.length > 0) {
            for (const st of parsed.statusLines) {
                const stDiv = document.createElement('div');
                stDiv.className = 'htc-res-status';
                stDiv.textContent = `! ${st}`;
                card.appendChild(stDiv);
            }
        }

        // 4. People summary
        if (parsed.peopleSummary.length > 0) {
            const peopleDiv = document.createElement('div');
            peopleDiv.className = 'htc-res-people';
            peopleDiv.innerHTML = `Present: <b>${parsed.peopleSummary.join(', ')}</b> <span class="htc-res-hint">(details in People chips)</span>`;
            card.appendChild(peopleDiv);
        }

        // 5. Collapsible raw tail (ways and character look lines)
        if (parsed.rawTailLines.length > 0) {
            const details = document.createElement('details');
            details.className = 'htc-res-details';
            const summary = document.createElement('summary');
            summary.textContent = `Exits & details (${parsed.rawTailLines.length})`;
            details.appendChild(summary);

            const tailBody = document.createElement('div');
            tailBody.className = 'htc-res-tail-body';
            for (const line of parsed.rawTailLines) {
                const p = document.createElement('div');
                p.className = 'htc-res-tail-line';
                p.textContent = line;
                tailBody.appendChild(p);
            }
            details.appendChild(tailBody);
            card.appendChild(details);
        }

        // Fallback for plain unparsed text
        if (!parsed.actionLine && parsed.proseLines.length === 0 && parsed.statusLines.length === 0 && parsed.rawTailLines.length === 0) {
            const fallbackDiv = document.createElement('div');
            fallbackDiv.className = 'htc-res-action';
            const b = document.createElement('b');
            b.textContent = prefix ? `${prefix}: ` : 'result: ';
            fallbackDiv.appendChild(b);
            fallbackDiv.appendChild(document.createTextNode(parsed.rawText));
            card.appendChild(fallbackDiv);
        }

        container.appendChild(card);
    }
    function showResult(text: string) {
        _lastReactionText = text || '';
        const node = q('#htc-result');
        if (!node) return;
        if (!text) { if (node.style) node.style.display = 'none'; return; }
        if (typeof node.replaceChildren === 'function') node.replaceChildren();
        node.classList?.remove?.('htc-expanded');
        const parsed = parseResultText(text);
        renderStructuredResult(node, parsed, 'last');

        if (parsed.rawTailLines.length > 0 || (parsed.proseLines.join(' ').length + parsed.actionLine.length) > 240) {
            const toggleBtn = document.createElement('button');
            toggleBtn.type = 'button';
            toggleBtn.className = 'htc-res-toggle-expand';
            toggleBtn.textContent = 'expand / clamp view';
            toggleBtn.addEventListener('click', () => {
                node.classList.toggle('htc-expanded');
            });
            node.appendChild(toggleBtn);
        }

        if (node.style) node.style.display = 'block';
    }

    function showResults(results: string[]) {
        const valid = (results || []).filter(r => r && r.trim());
        _lastReactionText = valid.join('\n');
        const node = q('#htc-result');
        if (!node) return;
        if (!valid.length) { if (node.style) node.style.display = 'none'; return; }
        if (typeof node.replaceChildren === 'function') node.replaceChildren();
        node.classList?.remove?.('htc-expanded');
        valid.forEach((text, i) => {
            const prefix = valid.length > 1 ? `${i + 1}` : 'result';
            const parsed = parseResultText(text);
            renderStructuredResult(node, parsed, prefix);
        });

        const hasTail = valid.some(r => r.includes('[wearing:') || r.includes('visible beyond') || r.includes('door]'));
        if (hasTail || valid.join(' ').length > 240) {
            const toggleBtn = document.createElement('button');
            toggleBtn.type = 'button';
            toggleBtn.className = 'htc-res-toggle-expand';
            toggleBtn.textContent = 'expand / clamp view';
            toggleBtn.addEventListener('click', () => {
                node.classList.toggle('htc-expanded');
            });
            node.appendChild(toggleBtn);
        }

        if (node.style) node.style.display = 'block';
    }

    function syncVolumeButtons() {
        for (const btn of qa('#htc-volseg button')) {
            btn.classList?.toggle?.('on', btn.dataset?.vol === _volume);
        }
    }

    function setSpeechTarget(target: string | null) {
        const clean = typeof target === 'string' && target.trim() ? target.trim() : null;
        _pendingSpeechTarget = clean;
        const chip = q('#htc-say-target');
        if (!chip) return;
        if (typeof chip.replaceChildren === 'function') chip.replaceChildren();
        else if (Array.isArray((chip as any).children)) (chip as any).children.length = 0;
        if (!clean) {
            if (chip.style) chip.style.display = 'none';
            chip.textContent = '';
            return;
        }
        if (chip.style) chip.style.display = 'inline-flex';
        const txt = document.createElement('span');
        txt.textContent = `to ${clean} `;
        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'htc-say-target-clear';
        clearBtn.title = 'Clear speech target';
        clearBtn.textContent = '×';
        clearBtn.addEventListener('click', (e) => {
            if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
            setSpeechTarget(null);
        });
        if (typeof chip.replaceChildren !== 'function') {
            chip.textContent = `to ${clean} ×`;
        }
        chip.appendChild(txt);
        chip.appendChild(clearBtn);
    }

    function renderMeta() {
        const meta = q('#htc-meta');
        if (!meta || typeof meta.replaceChildren !== 'function') return;
        meta.replaceChildren();
        const nodes: (Node | string)[] = [];
        if (typeof worldState !== 'undefined' && worldState.tick) nodes.push(`tick ${worldState.tick}`);
        let nextUp = '';
        try {
            if (config.turnBased && typeof TurnQueue !== 'undefined') {
                nextUp = TurnQueue.getCurrentCharacter?.() || '';
            }
        } catch { /* queue not initialized */ }
        if (nextUp && nextUp !== _charName) {
            const b = document.createElement('b');
            b.textContent = nextUp;
            const span = document.createElement('span');
            span.append('next up: ', b);
            nodes.push(span);
        } else if (nextUp) {
            const b = document.createElement('b');
            b.textContent = 'you';
            const span = document.createElement('span');
            span.append('next up: ', b);
            nodes.push(span);
        }
        nodes.forEach((n, idx) => {
            if (idx > 0) meta.append(' · ');
            meta.append(n);
        });
    }

    function renderDatalist() {
        const dl = q('#htc-names');
        if (!dl) return;
        dl.textContent = '';
        if (!_scene) return;
        const names = new Set<unknown>();
        for (const item of (_scene.items || []) as Array<Record<string, any>>) names.add(item.name);
        for (const p of (_scene.people || []) as Array<Record<string, any>>) names.add(p.display_name);
        for (const way of (_scene.ways || []) as Array<Record<string, any>>) { names.add(way.direction); if (way.to) names.add(way.to); }
        for (const inv of [...(_scene.you?.carrying || []), ...(_scene.you?.wearing || [])] as Array<Record<string, any>>) names.add(inv.name);
        for (const name of names) {
            const opt = document.createElement('option');
            opt.value = String(name);
            dl.appendChild(opt);
        }
    }

    /** (Re)build the scene view + You strip + minimap for *charName*. */
    function refreshScene(charName: string) {
        const sceneHost = q('#htc-scene');
        if (sceneHost) sceneHost.textContent = 'reading the room…';
        const stripHandlers = {
            onDraft: applyDraft,
            menu: (x: number, y: number, title: string, buttons: unknown[]) =>
                (htcGlobals.TurnSceneView as { menu(x: number, y: number, title: string, buttons: unknown[], onPick: (parts: any) => void): void })
                    .menu(x, y, title, buttons, applyDraft),
        };
        if (!htcGlobals.TurnSceneView || !sceneHost) return;
        const sceneView = htcGlobals.TurnSceneView;
        sceneView.fetch(charName).then((scene: any) => {
            if (!scene || scene.error || _charName !== charName) return;
            _scene = scene;
            sceneView.renderScene(sceneHost, scene, {
                onDraft: applyDraft,
                onTalkFocus: (talkOpts: any) => {
                    if (talkOpts && talkOpts.volume) {
                        _volume = talkOpts.volume;
                        syncVolumeButtons();
                    }
                    setSpeechTarget((talkOpts && talkOpts.target) ? talkOpts.target : null);
                    (q('#htc-speech') as HTMLInputElement)?.focus?.();
                },
            });
            (htcGlobals.TurnYouStrip as { render(host: HTMLElement, you: any, handlers: Record<string, unknown>): void })
                ?.render?.(q('#htc-you'), scene.you, stripHandlers);
            if (htcGlobals.TurnMinimap) {
                const feed = document.querySelector('.htc-feed') as HTMLElement | null;
                if (feed) htcGlobals.TurnMinimap.mount(feed, charName).catch(() => {});
            }
            renderDatalist();
        }).catch(() => {
            sceneHost.textContent = '';
            sceneHost.appendChild(document.createTextNode('scene unavailable.'));
        });
    }

    // ── build ────────────────────────────────────────────────────────

    function build() {
        if (_built) return;
        _built = true;
        ensureStyles();

        _overlay = el(htcPanelTag`<div id="htc-overlay" style="display:none"></div>`) as HTMLElement;
        _modal = el(htcPanelTag`<div id="htc-modal"></div>`) as HTMLElement;
        _overlay.appendChild(_modal);

        window.Lit.render(htcPanelTag`
          <div class="htc-header">
            <strong class="htc-title">✈ <span id="htc-title">Your turn</span></strong>
            <span class="htc-spacer"></span>
            <span id="htc-meta"></span>
            <button type="button" id="htc-close" title="end turn">✕</button>
          </div>
          <div class="htc-grid">
            <div id="htc-scene"></div>
            <div class="htc-feed">
              <h4>What happened</h4>
              <div id="htc-feed-lines"></div>
            </div>
          </div>
          <div id="htc-you"></div>
          <div class="htc-composer" id="htc-composer">
            <div class="htc-director-bar" id="htc-director-bar">
              <button type="button" id="htc-ask-director" class="htc-director-btn" title="Ask the AI Director to draft this turn (uses Director's Note if provided)">🎬 Ask Director</button>
              <input id="htc-director-note" type="text" autocomplete="off" placeholder="Director's note (optional) - e.g. 'act nervous, blame Sammy'" />
              <label class="htc-autodraft-wrap" title="Automatically draft with AI when this character's turn opens"><input type="checkbox" id="htc-autodraft" /> Auto-draft</label>
            </div>
            <div class="htc-budget">
              <div class="htc-pips" id="htc-pips"></div>
              <div class="htc-budgetlab" id="htc-budgetlab"></div>
              <span id="htc-phase-note"></span>
            </div>
            <div id="htc-result" style="display:none"></div>
            <div class="htc-row" id="htc-thought-row">
                <label for="htc-thought">💭 thought</label>
                <input id="htc-thought" type="text" autocomplete="off"
                    placeholder="internal monologue - what they privately think..." />
                <select id="htc-emotion" title="Character's felt emotion">
                    <option value="">emotion (keep)</option>
                    <option value="neutral">neutral</option>
                    <option value="happy">happy</option>
                    <option value="angry">angry</option>
                    <option value="afraid">afraid</option>
                    <option value="sad">sad</option>
                    <option value="surprised">surprised</option>
                    <option value="disgusted">disgusted</option>
                    <option value="anxious">anxious</option>
                    <option value="curious">curious</option>
                    <option value="determined">determined</option>
                    <option value="ashamed">ashamed</option>
                    <option value="relieved">relieved</option>
                </select>
                <button type="button" id="htc-thought-clear" title="Clear thought & emotion">×</button>
            </div>
            <div class="htc-crow" id="htc-do-row">
              <span class="lbl">⚙ do</span>
              <input id="htc-do" type="text" list="htc-names" placeholder='action - click a thing above, or type "eat berries", "open door"…' autocomplete="off">
              <button type="button" id="htc-clear-do" title="clear">✕</button>
            </div>
            <div id="htc-do-hint" style="display:none;font-size:11px;color:#c96;margin:-4px 0 6px 54px;line-height:1.3;"></div>
            <div class="htc-crow">
              <span class="lbl">🗨 say</span>
              <span id="htc-say-target" class="htc-say-target" style="display:none"></span>
              <input id="htc-speech" type="text" placeholder="what they say - free, stacks with the action" autocomplete="off">
              <select id="htc-tone" title="Optional delivery tone (leave plain for neutral speech)">
                <option value="">tone: plain</option>
                <option value="warm">warm</option>
                <option value="teasing">teasing</option>
                <option value="sarcastic">sarcastic</option>
                <option value="cold">cold</option>
                <option value="hostile">hostile</option>
                <option value="serious">serious</option>
                <option value="apologetic">apologetic</option>
                <option value="guarded">guarded</option>
              </select>
              <div class="htc-volseg" id="htc-volseg"></div>
            </div>
            <div class="htc-crow">
              <span class="lbl">🎭 emote</span>
              <input id="htc-emote" type="text" placeholder='body language - "sneaks closer to the door"' autocomplete="off">
              <button type="button" id="htc-emote-toggle" class="htc-chiptoggle" title="emote quick-pick">🎭</button>
            </div>
            <div id="htc-emote-palette" class="htc-emote-palette"></div>
            <div class="htc-crow" style="justify-content:flex-end;">
              <button type="button" id="htc-reroll-btn" class="htc-btn-primary" style="display:none;background:#6a4fb8;margin-right:6px;" title="Reroll this character's draft turn with the AI">🎲 Reroll</button>
              <button type="button" id="htc-reroll" style="display:none"></button>
              <button type="button" id="htc-act" class="htc-btn-primary">Act</button>
              <button type="button" id="htc-commit" style="display:none"></button>
            </div>
            <div class="htc-footer-row">
              <button type="button" id="htc-react-btn" class="htc-btn-primary gold" style="display:none">close turn</button>
              <span id="htc-flash" class="htc-flash"></span>
              <button type="button" id="htc-advanced-toggle" class="htc-linkbtn muted">▸ advanced</button>
              <button type="button" id="htc-timeskip" class="htc-linkbtn" title="Wait, mingle, search, explore or travel for a span - your character runs on a policy while everyone else soaks">⏩ timeskip</button>
              <button type="button" id="htc-end" class="htc-linkbtn endturn">⏭ end turn</button>
            </div>
            <div id="htc-advanced" style="display:none">
              <select id="htc-relation"><option value="">relation: -</option><option value="on">on</option><option value="under">under</option><option value="beside">beside</option><option value="behind">behind</option><option value="at">at</option><option value="in">in</option></select>
              <select id="htc-where" disabled title="reserved - region targeting lands with task-211">
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
                syncVolumeButtons();
            });
            volseg.appendChild(btn);
        }
        syncVolumeButtons();

        q('#htc-act').addEventListener('click', commitStep);
        const commitAlias = _modal.querySelector('#htc-commit');
        if (commitAlias) commitAlias.addEventListener('click', commitStep);
        q('#htc-ask-director').addEventListener('click', () => {
            EmotePicker.close(q('#htc-emote-palette'));
            askDirector();
        });
        q('#htc-director-note').addEventListener('keydown', (e: KeyboardEvent) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                askDirector();
            }
        });
        q('#htc-autodraft').addEventListener('change', () => {
            const cb = q('#htc-autodraft') as HTMLInputElement | null;
            if (_charName && cb && typeof events !== 'undefined' && typeof events?.setAutoDraft === 'function') {
                events.setAutoDraft(_charName, Boolean(cb.checked));
            }
        });
        q('#htc-thought-clear').addEventListener('click', () => {
            const thoughtEl = q('#htc-thought') as HTMLInputElement | null;
            const emotionEl = q('#htc-emotion') as HTMLSelectElement | null;
            if (thoughtEl) thoughtEl.value = '';
            if (emotionEl) emotionEl.value = '';
        });
        q('#htc-reroll-btn').addEventListener('click', () => {
            EmotePicker.close(q('#htc-emote-palette'));
            askDirector();
        });
        const rerollAlias = _modal.querySelector('#htc-reroll');
        if (rerollAlias) rerollAlias.addEventListener('click', () => {
            EmotePicker.close(q('#htc-emote-palette'));
            askDirector();
        });
        q('#htc-react-btn').addEventListener('click', () => finishReact(false));
        q('#htc-end').addEventListener('click', () => finishAct({ endTurn: true }));
        q('#htc-close').addEventListener('click', () => onOverlayDismiss());
        q('#htc-timeskip').addEventListener('click', () => {
            if (htcGlobals.Timeskip && typeof htcGlobals.Timeskip.openDialog === 'function') {
                htcGlobals.Timeskip.openDialog();
            }
        });
        const updateDoHint = () => {
            const hintEl = q('#htc-do-hint');
            if (!hintEl) return;
            const text = (q('#htc-do') as HTMLInputElement).value;
            const hint = doHint(text);
            if (hint) {
                hintEl.textContent = hint;
                hintEl.style.display = 'block';
            } else {
                hintEl.textContent = '';
                hintEl.style.display = 'none';
            }
        };
        q('#htc-do').addEventListener('input', updateDoHint);

        q('#htc-clear-do').addEventListener('click', () => {
            (q('#htc-do') as HTMLInputElement).value = '';
            updateDoHint();
        });
        q('#htc-emote-toggle').addEventListener('click', () => {
            EmotePicker.toggle(q('#htc-emote-palette'), {
                onPick: (emote: string) => {
                    const input = q('#htc-emote');
                    if (input) (input as HTMLInputElement).value = emote;
                }
            });
        });
        q('#htc-act').addEventListener('click', () => {
            EmotePicker.close(q('#htc-emote-palette'));
        });
        for (const id of ['htc-do', 'htc-speech', 'htc-emote', 'htc-memory', 'htc-thought']) {
            q('#' + id).addEventListener('keydown', (e: KeyboardEvent) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (_phase === 'react') finishReact(false);
                    else commitStep();
                }
                if (e.key === 'Escape' && _phase === 'react') finishReact(true);
            });
        }

        q('#htc-advanced-toggle').addEventListener('click', () => {
            _advanced = !_advanced;
            q('#htc-advanced').style.display = _advanced ? 'flex' : 'none';
            q('#htc-advanced-toggle').textContent = _advanced ? '▾ advanced' : '▸ advanced';
        });

        _modal.addEventListener('click', (e) => e.stopPropagation());
        _overlay.addEventListener('click', () => onOverlayDismiss());
        const closeOnEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && _overlay.style.display !== 'none') onOverlayDismiss();
        };
        document.addEventListener('keydown', closeOnEsc);
    }

    // ── resolve plumbing ─────────────────────────────────────────────

    function _commitFromInputs(): NormalizedReply {
        const norm = normalizeReply(buildPayload());
        const thoughtEl = q('#htc-thought') as HTMLInputElement | null;
        const emotionEl = q('#htc-emotion') as HTMLSelectElement | null;
        const inner = thoughtEl
            ? (thoughtEl.value.trim() || null)
            : (_currentPrefill?.inner || null);
        const emotion = emotionEl
            ? (emotionEl.value.trim() || null)
            : (_currentPrefill?.emotion || null);
        return {
            ...norm,
            inner,
            emotion,
        };
    }

    /** Stage one step and hand it to the engine. The panel stays OPEN. */
    function commitStep() {
        const stepResult = _commitFromInputs();
        if (!stepResult.action && !stepResult.speech && !stepResult.emote && !stepResult.inner && !stepResult.emotion && !stepResult.memory) return;
        if (stepResult.action) {
            const actionWord = stepResult.action.split(/\s+/)[0].toLowerCase();
            const at = actionTiers();
            const tier = at && at.tierOf ? at.tierOf(actionWord) : 'major';
            const s = turnSlots();
            const order = ['free', 'minor', 'major'];
            const affordable = (tier === 'activity')
                ? !s || (s.activity || 0) > 0
                : !s || order.slice(Math.max(0, order.indexOf(tier))).some((t) => (s[t] || 0) > 0);
            if (!affordable) { setFlash(`no ${tier} action left this turn - say / emote / memory are still free`); return; }
            _lastCommittedAction = stepResult.action;
        }
        const resolve = _activeResolve;
        _activeResolve = null;
        for (const id of ['htc-do', 'htc-speech', 'htc-tone', 'htc-emote', 'htc-memory', 'htc-thought', 'htc-emotion']) {
            const input = q('#' + id) as HTMLInputElement | HTMLSelectElement | null;
            if (input) input.value = '';
        }
        const relEl = q('#htc-relation') as HTMLSelectElement | null;
        if (relEl) relEl.value = '';
        setSpeechTarget(null);
        setBusy(true);
        _currentPrefill = null;
        if (resolve) resolve({ step: stepResult });
    }

    function finishAct(reply: TurnResult) {
        const resolve = _activeResolve;
        _activeResolve = null;
        _currentPrefill = null;
        TurnFeed.markTurnEnd();
        hidePanel();
        if (resolve) resolve(reply);
    }

    function finishReact(endTurn: boolean) {
        if (_dryRun) {
            _reactResolve = null;
            _currentPrefill = null;
            _dryRun = false;
            hidePanel();
            return;
        }
        if (typeof _reactResolve !== 'function') return;
        const resolve = _reactResolve;
        _reactResolve = null;
        let reply: ReactResult;
        if (endTurn) {
            _currentPrefill = null;
            reply = { endTurn: true };
        } else {
            const stepResult = _commitFromInputs();
            _currentPrefill = null;
            reply = {
                speech: stepResult.speech,
                volume: stepResult.speechVolume,
                tone: stepResult.speechTone || null,
                emote: stepResult.emote,
                memory: stepResult.memory,
                target: stepResult.target,
                inner: stepResult.inner || null,
                emotion: stepResult.emotion || null,
            };
        }
        TurnFeed.markTurnEnd();
        hidePanel();
        resolve(reply);
    }

    function onOverlayDismiss() {
        _currentPrefill = null;
        if (_phase === 'react') { finishReact(true); return; }
        finishAct({ endTurn: true });
    }

    function setFlash(msg: string) {
        const node = q('#htc-flash');
        if (!node) return;
        node.textContent = msg;
        window.setTimeout(() => { if (node.textContent === msg) node.textContent = ''; }, 2200);
    }

    // ── panel open/close ─────────────────────────────────────────────

    function hidePanel() {
        const ov = _overlay || q('#htc-overlay');
        if (ov?.style) ov.style.display = 'none';
        if (htcGlobals.TurnSceneView && typeof htcGlobals.TurnSceneView.closeMenu === 'function') {
            htcGlobals.TurnSceneView.closeMenu();
        }
    }

    function resetRows() {
        for (const id of ['htc-do', 'htc-speech', 'htc-tone', 'htc-emote', 'htc-memory', 'htc-thought', 'htc-emotion']) {
            const input = q('#' + id) as HTMLInputElement | HTMLSelectElement | null;
            if (input) input.value = '';
        }
        const relEl = q('#htc-relation') as HTMLSelectElement | null;
        if (relEl) relEl.value = '';
        setSpeechTarget(null);
        const hintEl = q('#htc-do-hint');
        if (hintEl) { hintEl.textContent = ''; if (hintEl.style) hintEl.style.display = 'none'; }
    }

    function applyPrefill(prefill: TurnPrefill | null | undefined) {
        if (!prefill || typeof prefill !== 'object') return;
        _currentPrefill = prefill;
        if (_phase !== 'react' && prefill.action !== undefined && prefill.action !== null) {
            const doEl = q('#htc-do') as HTMLInputElement | null;
            if (doEl) doEl.value = prefill.action;
        }
        if (prefill.speech !== undefined) {
            const speechEl = q('#htc-speech') as HTMLInputElement | null;
            if (speechEl) speechEl.value = prefill.speech || '';
        }
        if (prefill.speechVolume) {
            _volume = prefill.speechVolume;
            syncVolumeButtons();
        }
        if (prefill.speechTone !== undefined) {
            const toneEl = q('#htc-tone') as HTMLSelectElement | null;
            if (toneEl) toneEl.value = prefill.speechTone || '';
        }
        setSpeechTarget(prefill.target || null);
        if (prefill.emote !== undefined) {
            const emoteEl = q('#htc-emote') as HTMLInputElement | null;
            if (emoteEl) emoteEl.value = prefill.emote || '';
        }
        if (prefill.memory !== undefined) {
            const mem = prefill.memory as any;
            const memEl = q('#htc-memory') as HTMLInputElement | null;
            if (memEl) {
                memEl.value = !mem
                    ? ''
                    : (typeof mem === 'string' ? mem : (mem?.text || JSON.stringify(mem)));
            }
        }
        const thoughtEl = q('#htc-thought') as HTMLInputElement | null;
        if (thoughtEl) {
            thoughtEl.value = prefill.inner || '';
        }
        const emotionEl = q('#htc-emotion') as HTMLSelectElement | null;
        if (emotionEl) {
            const emoVal = typeof prefill.emotion === 'object' && prefill.emotion
                ? ((prefill.emotion as any).label || '')
                : (prefill.emotion || '');
            if (emoVal && emotionEl.options && !Array.from(emotionEl.options).some((o: any) => o.value === emoVal)) {
                const opt = document.createElement('option');
                opt.value = emoVal;
                opt.textContent = emoVal;
                emotionEl.appendChild(opt);
            }
            emotionEl.value = emoVal;
        }
    }

    async function askDirector(): Promise<TurnPrefill | null> {
        const btn = q('#htc-ask-director') as HTMLButtonElement | null;
        const noteEl = q('#htc-director-note') as HTMLInputElement | null;
        const directorNote = noteEl ? (noteEl.value || '').trim() : '';
        const charName = _charName || (typeof config !== 'undefined' ? config.controllingPlayer : null) || '';
        const doVal = ((q('#htc-do') as HTMLInputElement | null)?.value || '').trim();
        const speechVal = ((q('#htc-speech') as HTMLInputElement | null)?.value || '').trim();
        const emoteVal = ((q('#htc-emote') as HTMLInputElement | null)?.value || '').trim();
        const thoughtVal = ((q('#htc-thought') as HTMLInputElement | null)?.value || '').trim();
        const emotionVal = ((q('#htc-emotion') as HTMLSelectElement | null)?.value || '').trim();
        const memoryVal = ((q('#htc-memory') as HTMLInputElement | null)?.value || '').trim();
        const hasCurrentDraft = Boolean(doVal || speechVal || emoteVal || thoughtVal || emotionVal || memoryVal || _pendingSpeechTarget);
        const currentDraft = hasCurrentDraft ? {
            action: doVal,
            speech: speechVal,
            speechVolume: _volume || 'say',
            target: _pendingSpeechTarget || null,
            emote: emoteVal,
            inner: thoughtVal,
            emotion: emotionVal,
            memory: memoryVal,
        } : null;
        if (btn) {
            btn.textContent = '🎬 Drafting...';
            btn.disabled = true;
        }
        try {
            const draft = await (typeof VW !== 'undefined' ? VW : null)?.agent?.draftTurnForCharacter?.(charName, {
                phase: _phase,
                directorNote,
                actionResult: _lastReactionText,
                lastAction: _lastCommittedAction,
                currentDraft,
                scene: _scene,
            });
            if (draft) {
                applyPrefill(draft);
                return draft;
            }
            return null;
        } finally {
            if (btn) {
                btn.textContent = '🎬 Ask Director';
                btn.disabled = false;
            }
        }
    }

    function applyDraft(parts: Record<string, any> | null | undefined) {
        if (!parts || _phase === 'react') return;
        const doEl = q('#htc-do') as HTMLInputElement | null;
        if (doEl) {
            doEl.value = [parts.action, parts.item, parts.target]
                .filter(Boolean).join(' ');
        }
        const hintEl = q('#htc-do-hint');
        if (hintEl) { hintEl.textContent = ''; if (hintEl.style) hintEl.style.display = 'none'; }
        (q('#htc-speech') as HTMLInputElement)?.focus?.();
    }

    /** First open for a turn: full setup + show. */
    function openPanel(charName: string, opts: OpenPanelOptions = {}) {
        try { build(); } catch { /* headless unit stub */ }
        _charName = charName;
        _lastCommittedAction = '';
        resetRows();
        setPhase('compose');
        showResult(opts.lastResult || '');
        refreshScene(charName);
        const feedLines = q('#htc-feed-lines');
        if (feedLines && typeof TurnFeed !== 'undefined' && TurnFeed?.render) {
            TurnFeed.render(feedLines);
        }
        const rerollEl = q('#htc-reroll-btn');
        if (rerollEl?.style) {
            rerollEl.style.display = (opts.canReroll || opts.prefill) ? 'inline-block' : 'none';
        }
        const isAuto = Boolean(typeof events !== 'undefined' && events?.isAutoDraft?.(charName));
        const autoDraftEl = q('#htc-autodraft') as HTMLInputElement | null;
        if (autoDraftEl) autoDraftEl.checked = isAuto;
        renderMeta();
        renderPips();
        setBusy(false);
        const flashEl = q('#htc-flash');
        if (flashEl) flashEl.textContent = '';
        const ov = _overlay || q('#htc-overlay');
        if (ov?.style) ov.style.display = 'flex';
        _currentPrefill = opts.prefill || null;
        if (opts.prefill) {
            applyPrefill(opts.prefill);
        } else if (isAuto && _phase === 'compose') {
            askDirector();
        }
        (q('#htc-do') as HTMLInputElement)?.focus?.();
    }

    /** Subsequent step: refresh the open panel with the last result + budget. */
    function refreshStep(charName: string, lastResult: string, prefill?: TurnPrefill) {
        _charName = charName;
        resetRows();
        setPhase('compose');
        showResult(lastResult || '');
        refreshScene(charName);
        const isAuto = Boolean(typeof events !== 'undefined' && events?.isAutoDraft?.(charName));
        const autoDraftEl = q('#htc-autodraft') as HTMLInputElement | null;
        if (autoDraftEl) autoDraftEl.checked = isAuto;
        renderMeta();
        renderPips();
        setBusy(false);
        _currentPrefill = prefill || null;
        if (prefill) {
            applyPrefill(prefill);
        }
        (q('#htc-do') as HTMLInputElement)?.focus?.();
    }

    /**
     * The engine's per-step hook. First call opens the panel; later calls
     * refresh it. Resolves when the player Commits a step (`{step}`) or ends
     * the turn (`{endTurn:true}`). Never hides on a step.
     */
    function request(charName: string, opts: RequestOptions = {}): Promise<TurnResult> {
        if (_activeResolve) {
            return new Promise((resolve) => { _activeResolve = resolve; });
        }
        const ov = _overlay || q('#htc-overlay');
        if (!ov || ov.style?.display === 'none') openPanel(charName, opts);
        else refreshStep(charName, opts.lastResult || '', opts.prefill);
        return new Promise((resolve) => { _activeResolve = resolve; });
    }

    /**
     * The single closing react beat (task-334 lane 1): say / emote / memory
     * bound to the turn's results. Reuses the open panel, or reopens it if the
     * player already ended the turn.
     */
    function react(charName: string, results: string[]): Promise<ReactResult> {
        if (_reactResolve) {
            return new Promise((resolve) => { _reactResolve = resolve; });
        }
        const ov = _overlay || q('#htc-overlay');
        if (!_built || !ov || ov.style?.display === 'none') {
            try { build(); } catch { /* headless unit stub */ }
            _charName = charName;
            resetRows();
            setPhase('react');
            showResults(results);
            renderMeta();
            const ovAfter = _overlay || q('#htc-overlay');
            if (ovAfter?.style) ovAfter.style.display = 'flex';
        } else {
            _charName = charName;
            resetRows();
            setPhase('react');
            showResults(results);
            refreshScene(charName);
            renderMeta();
        }
        const isAuto = Boolean(typeof events !== 'undefined' && events?.isAutoDraft?.(charName));
        const autoDraftEl = q('#htc-autodraft') as HTMLInputElement | null;
        if (autoDraftEl) autoDraftEl.checked = isAuto;
        if (isAuto) {
            askDirector();
        }
        (q('#htc-speech') as HTMLInputElement)?.focus?.();
        return new Promise((resolve) => { _reactResolve = resolve; });
    }

    /** The engine calls this once the turn (and react) is done. */
    function closeTurn() {
        _activeResolve = null;
        _reactResolve = null;
        hidePanel();
        // Invalidate the scene cache so the next turn fetches fresh data.
        if (htcGlobals.TurnSceneView && typeof htcGlobals.TurnSceneView.invalidateCache === 'function') {
            htcGlobals.TurnSceneView.invalidateCache();
        }
    }

        /**
     * Dev / e2e preview affordance (task-698):
     * Opens the HTC directly in the react phase with supplied result text.
     * Closing resolves to nothing (no turn spent, no action sent, no memory saved).
     */
    function preview(charName: string, results: string | string[]): void {
        const resArr = Array.isArray(results) ? results : [results];
        _dryRun = true;
        if (!_built || !_overlay) {
            try { build(); } catch { /* headless unit stub */ }
        }
        _charName = charName;
        resetRows();
        setPhase('react');
        showResults(resArr);
        refreshScene(charName);
        renderMeta();
        if (_overlay?.style) _overlay.style.display = 'flex';
        (q('#htc-speech') as HTMLInputElement)?.focus?.();
    }

    return {
        request,
        react,
        preview,
        closeTurn,
        open: openPanel,
        openPanel,
        applyPrefill,
        setSpeechTarget,
        askDirector,
        _commitFromInputs,
        commitStep,
        parseCmd,
        doHint,
        ACTIONS,
        parseResultText,
    };
})();

(window as unknown as { HumanTurnComposer: typeof HumanTurnComposerModule }).HumanTurnComposer = HumanTurnComposerModule;

const htcGlobals = window as unknown as {
    Timeskip?: { openDialog(): void };
    TurnSceneView?: {
        menu(x: number, y: number, title: string, buttons: unknown[], onPick: (parts: any) => void): void;
        fetch(charName: string): Promise<any>;
        renderScene(host: HTMLElement, scene: any, opts: Record<string, unknown>): void;
        invalidateCache?(charName?: string): void;
        closeMenu?(): void;
    };
    TurnYouStrip?: { render(host: HTMLElement, you: any, handlers: Record<string, unknown>): void };
    TurnMinimap?: { mount(host: HTMLElement, charName: string): Promise<void> };
    CharacterArt?: { open(charName: string): void };
};

// Type declarations sit below the first value statement on purpose: TypeScript
// drops a file's leading JSDoc when the first statement is type-only, which
// would strip the `@module` header `tools/js_module_index.py` reads.

interface ParsedCmd {
    action?: string;
    item?: string;
    target?: string;
    speech?: string;
    volume?: string;
}

interface TurnPayload {
    action?: string;
    item?: string;
    target?: string;
    relation?: string;
    speech?: string;
    volume?: string;
    tone?: string;
    emote?: string;
    memory?: string;
}

interface TurnPrefill {
    action?: string;
    speech?: string | null;
    speechVolume?: string;
    speechTone?: string | null;
    emote?: string | null;
    memory?: unknown;
    emotion?: string | null;
    inner?: string | null;
    target?: string | null;
}

interface NormalizedReply {
    action: string;
    speech: string | null;
    speechVolume: string;
    speechTone?: string | null;
    emote: string | null;
    memory: unknown;
    target: string | null;
    inner?: string | null;
    emotion?: string | null;
}

/** What `request()` resolves with. */
type TurnResult = { step: NormalizedReply } | { endTurn: true } | { reroll: true };

/** What `react()` resolves with. */
type ReactResult =
    | { speech: string | null; volume: string; tone?: string | null; emote: string | null; memory: unknown; target: string | null; inner?: string | null; emotion?: string | null }
    | { endTurn: true };

interface RequestOptions {
    lastResult?: string;
    prefill?: TurnPrefill;
    canReroll?: boolean;
}

interface OpenPanelOptions extends RequestOptions {
    first?: boolean;
}

/** `EmotePicker` (shared/emote-picker.js) is declared in types/globals.d.ts. */
