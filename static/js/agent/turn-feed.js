/**
 * turn-feed.js — "What happened" feed + since-your-turn digest for the
 *
 * @module agent/turn-feed — the human panel's feed and turn digest
 * @contributes a viewer-scoped ring buffer of log rows, digest rendering, and audio propagation
 * @powers the "since your turn" summary: your own rows, your room, and speech that carries
 * @relates subscribes to event-stream's log bus; rendered by human-turn-composer
 * @docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
 * human turn panel (task-333 full redesign; digest = task-334 lane 2).
 *
 * Subscribes to the app event bus ('log' emissions from event-stream.js)
 * and keeps a small ring buffer. The panel renders the tail as its feed;
 * entries emitted between two panel opens form the turn-start digest.
 * Interjection (lane 3) posts guest speech through the normal command
 * path without touching turn state.
 *
 * Load AFTER event-stream.js, BEFORE human-turn-composer.js.
 */

window.TurnFeed = (() => {
    'use strict';

    const MAX = 60;
    const _ring = [];
    let _seq = 0;
    let _digestMark = 0;
    let _installed = false;
    let _observerMode = true;
    let _toggleEl = null;

    function install() {
        if (_installed) return;
        if (typeof events === 'undefined' || typeof events.on !== 'function') return;
        events.on('log', (data) => {
            const text = String((data && data.text) ?? '').trim();
            if (!text) return;
            _ring.push({
                text,
                className: (data && data.className) || '',
                actor: (data && data.actor) || null,
                seq: ++_seq,
            });
            if (_ring.length > MAX) _ring.shift();
        });
        _installed = true;
    }

    /* ── viewer scoping ─────────────────────────────────────────────── */

    // The feed and the "since your turn" digest must only show what the human
    // could perceive: their own rows plus rows acted by characters standing in
    // the same area. Otherwise the panel leaks the whole world (task-333).
    function _viewerName() {
        if (typeof config !== 'undefined' && config && config.controllingPlayer) {
            return config.controllingPlayer;
        }
        if (typeof worldState !== 'undefined' && worldState && worldState.data
                && worldState.data.active_player) {
            return worldState.data.active_player;
        }
        return null;
    }

    function _areaOf(name) {
        if (!name || name === 'World') return null;
        const players = (typeof worldState !== 'undefined' && worldState && worldState.data)
            ? worldState.data.players : null;
        const p = players ? players[name] : null;
        return (p && p.current_area) || null;
    }

    // Sound model mirrored from engine/sound.py + engine/runtime_config.py.
    // Speech penetration vs accumulated way barriers decides who hears a line.
    const SOUND = {
        speech: { whisper: 0, normal: 1, sing: 1, shout: 2, scream: 3 },
        barrier: { open: 0.5, closed: 1, locked: 1, blocked: 1, hidden: 2 },
        seeThrough: 0.75,
        noise: { silent: 0, quiet: 0, normal: 1, loud: 2, chaotic: 2 },
    };

    function _barrierFor(wayProps) {
        const props = wayProps || {};
        const state = props.current_state || 'open';
        if (state === 'closed' || state === 'blocked' || state === 'locked') {
            const custom = parseFloat(props.sound_barrier);
            if (!isNaN(custom)) return custom;                 // per-door acoustic mass
        }
        if (props.see_through) return SOUND.seeThrough;        // windows/grates
        const barrier = SOUND.barrier[state];
        return barrier != null ? barrier : SOUND.barrier.open;
    }

    function _noiseLevel(areaNode) {
        const env = (areaNode && areaNode.properties && areaNode.properties.environment) || {};
        const key = String(env.noise || 'quiet').toLowerCase();
        const noiseLevel = SOUND.noise[key];
        return noiseLevel != null ? noiseLevel : 0;                              // item absorption not modelled here
    }

    /** Areas whose occupants can hear *volume* speech from *originAreaName*.
     *  Mirrors engine/sound.py propagate_sound(): BFS accumulating barriers; a
     *  neighbour hears when penetration - accumulated > 0, and the path keeps
     *  propagating with the accumulated total. */
    function _areasHearingFrom(originAreaName, volume) {
        const graph = (typeof worldState !== 'undefined' && worldState) ? worldState.graph : null;
        if (!graph || !originAreaName) return [];
        const nodes = graph.nodes || {};
        const edges = graph.edges || [];
        const norm = (s) => String(s || '').toLowerCase();
        let originId = null;
        for (const [id, n] of Object.entries(nodes)) {
            if (n && n.type === 'area' && norm(n.name) === norm(originAreaName)) { originId = id; break; }
        }
        if (!originId) return [];
        const key = volume === 'say' ? 'normal' : volume;
        const speech = SOUND.speech[key] != null ? SOUND.speech[key] : 1;
        const penetration = speech - _noiseLevel(nodes[originId]);
        if (penetration <= 0) return [];                       // sound never leaves the room
        const heard = [];
        const visited = new Set([originId]);
        const queue = [[originId, 0]];
        while (queue.length) {
            const [curId, accumulated] = queue.shift();
            for (const edge of edges) {
                if (edge.type !== 'connection' || edge.source !== curId) continue;
                const way = nodes[edge.target];
                if (!way || way.type !== 'way') continue;
                let nextId = null;
                for (const e2 of edges) {
                    if (e2.type === 'connection' && e2.source === edge.target && e2.target !== curId) {
                        nextId = e2.target;
                        break;
                    }
                }
                if (!nextId || visited.has(nextId)) continue;
                const acc = accumulated + _barrierFor(way.properties || {});
                if (penetration - acc > 0) {
                    visited.add(nextId);
                    heard.push(nodes[nextId] ? nodes[nextId].name : nextId);
                    queue.push([nextId, acc]);
                }
            }
        }
        return heard;
    }

    function _viewerContext() {
        const viewer = _viewerName();
        return { viewer, viewerArea: _areaOf(viewer), audible: new Map() };
    }

    function _actorAudibleToViewer(actorArea, volume, ctx) {
        if (!actorArea || !ctx.viewerArea) return false;
        const cacheKey = actorArea + '|' + volume;
        if (!ctx.audible.has(cacheKey)) {
            ctx.audible.set(cacheKey, _areasHearingFrom(actorArea, volume));
        }
        return ctx.audible.get(cacheKey).indexOf(ctx.viewerArea) !== -1;
    }

    function _perceivableByViewer(entry, ctx) {
        if (!entry || !entry.actor || entry.actor === 'World') return true; // engine/world rows
        ctx = ctx || _viewerContext();
        if (!ctx.viewer) return true;                                       // cannot scope
        if (entry.actor === ctx.viewer) return true;                        // your own turn
        const actorArea = _areaOf(entry.actor);
        if (!actorArea || !ctx.viewerArea) return false;
        if (actorArea === ctx.viewerArea) return true;                      // same room
        // Audio propagation: speech carries through ways per the sound model
        // (whispers are penetration 0, so they stay private).
        const parsed = parseEntry(entry);
        if (parsed && parsed.type === 'speech') {
            return _actorAudibleToViewer(actorArea, parsed.volume || 'say', ctx);
        }
        return false;
    }

    function _scopedRing() {
        const ctx = _viewerContext();
        return _ring.filter((e) => _perceivableByViewer(e, ctx));
    }

    /* ── structured parsing ─────────────────────────────────────────── */

    function _parseActor(text) {
        const m = text.match(/^\[([^\]]+)\]/);
        return m ? m[1] : null;
    }

    function parseEntry(entry) {
        const text = String(entry.text || '').trim();
        const cls = String(entry.className || '');
        if (!text) return null;

        const isSpeech = cls.includes('msg-speech');
        const isWhisper = cls.includes('msg-whisper');
        const isAction = cls.includes('msg-action');
        const isEmote = cls.includes('msg-emote');
        const isResult = cls.includes('msg-result');
        const isThought = cls.includes('msg-thought');
        const isSystem = cls.includes('system-msg') || cls.includes('msg-npc') ||
                         cls.includes('msg-reflection') || cls.includes('msg-recall') ||
                         cls.includes('msg-prune') || cls.includes('error-msg');

        if (isSpeech || isWhisper) {
            let actor = null;
            let content = text;
            let volume = 'say';
            const quoted = text.match(/^\[([^\]]+)\]\s*(?:whispers?:\s*|says?:\s*|shouts?:\s*|screams?:\s*)?["“](.+?)["”]/i);
            if (quoted) {
                actor = quoted[1];
                content = quoted[2];
                if (/whisper/i.test(text)) volume = 'whisper';
                else if (/shout/i.test(text)) volume = 'shout';
                else if (/scream/i.test(text)) volume = 'scream';
            } else {
                actor = _parseActor(text);
                content = text.replace(/^\[[^\]]+\]\s*/, '').replace(/^["“]|["”]$/g, '');
            }
            return { type: isWhisper ? 'whisper' : 'speech', actor, content, volume };
        }

        if (isAction) {
            let actor = null;
            let content = text;
            const m = text.match(/^\[Action\]\s+(.+)/i);
            if (m) {
                content = m[1];
                const named = _tryParsePrefixedName(content);
                if (named) {
                    actor = named.actor;
                    content = named.content;
                }
            } else {
                const a = _parseActor(text);
                if (a) { actor = a; content = text.replace(/^\[[^\]]+\]\s*/, ''); }
            }
            return { type: 'action', actor, content };
        }

        if (isEmote) {
            const named = _tryParsePrefixedName(text);
            return { type: 'emote', actor: named ? named.actor : null, content: named ? named.content : text };
        }

        if (isResult) {
            return { type: 'result', actor: null, content: text };
        }

        if (isThought) {
            const m = text.match(/^\[([^\]]+)\s+inner\]\s*(.*)/);
            return { type: 'thought', actor: m ? m[1] : null, content: m ? m[2] : text };
        }

        if (isSystem) {
            let actor = null;
            let content = text;
            let kind = 'system';
            if (/did nothing this turn/.test(text)) {
                const m = text.match(/^[^\w]*(\S+)\s+did nothing/);
                actor = m ? m[1] : null;
                content = 'did nothing this turn';
                kind = 'npc';
            } else if (/recalled/.test(text)) {
                const named = _tryParsePrefixedName(text);
                if (named) {
                    actor = named.actor;
                    content = named.content;
                } else {
                    content = text.replace(/^[^\W_]*\s*/, '').trim();
                }
                kind = 'recall';
            } else if (/passed|Restarting|ended|No |Char not found/.test(text)) {
                actor = 'World';
            } else {
                const named = _tryParsePrefixedName(text);
                if (named) {
                    actor = named.actor;
                    content = named.content;
                    kind = 'action';
                }
            }
            return { type: kind, actor, content };
        }

        if (text.startsWith('[Action]')) {
            return { type: 'action', actor: 'You', content: text.replace(/^\[Action\]\s*/, '') };
        }

        return { type: 'unknown', actor: null, content: text };
    }

    function _tryParsePrefixedName(text) {
        const m = text.match(/^([A-Za-z][A-Za-z .]{0,40}?)\s+(fidgets|looks|smiles|frowns|sighs|shrugs|gestures|steps|moves|turns|walks|runs|stands|sits|kneels|crouches|peeks|glances|stares|watches|listens|bites|chews|drinks|eats|holds|carries|pulls|pushes|opens|closes|takes|drops|examines|searches|attacks|grabs|hugs|kisses|slaps|kicks|punches|dodges|blocks|parries|jumps|climbs|crawls|dashes|approaches|leads|escapes|struggles|rests|sleeps|waits|stands|says|whispers|shouts|screams|thinks|remembers|notices|realizes|understands|knows|believes|hopes|wants|needs|tries|starts|begins|continues|stops|ends|finishes|completes|fails|succeeds|manages|attempts|pretends|acts|performs|plays|works|functions|operates|runs|shakes|trembles|vibrates|glows|shines|flashes|fades|appears|materializes|vanishes|ignites|burns|cools|heats|freezes|melts|breaks|shatters|cracks|splits|tears|rips|cuts|slashes|stabs|shoots|fires|launches|throws|catches|grabs|holds|carries|drags|pulls|pushes|presses|squeezes|crushes|smashes|hits|strikes|beats|defeats|wins|loses|falls|trips|stumbles|collapses|passes|faints|dies|lives|survives|escapes|flees|chases|follows|pursues|hunts|searches|looks|sees|hears|smells|tastes|feels|touches|reaches|arrives|comes|goes|leaves|departs|returns|stays|remains|waits|lingers|hovers|floats|flies|swims|sinks|dives|jumps|leaps|bounds|hops|skips|marches|parades|processes|files)\b/i);
        if (m) {
            const actor = m[1].trim();
            const content = text.slice(m[0].length).trim();
            if (actor.includes(' ') || /^[A-Z]/.test(actor)) {
                return { actor, content };
            }
        }
        return null;
    }

    function structuredEntries(rawEntries) {
        return rawEntries.map(parseEntry).filter(Boolean);
    }

    function isObserverVisible(parsed) {
        if (!parsed) return false;
        if (parsed.type === 'thought' || parsed.type === 'recall' || parsed.type === 'system') return false;
        if (parsed.type === 'action' && /^(think|observe|decide|react)/i.test(parsed.content)) return false;
        if (parsed.type === 'action' && /replanned/i.test(parsed.content)) return false;
        if (parsed.type === 'result' && /Welcome to|Available Commands:/i.test(parsed.content)) return false;
        return true;
    }

    function truncateResult(text, max = 220) {
        if (!text || text.length <= max) return text;
        return text.slice(0, max - 3).trimEnd() + '...';
    }

    function observerName(actorName) {
        if (!actorName) return 'someone';
        const activePlayer = (typeof worldState !== 'undefined' && worldState.data && worldState.data.activePlayer) ? worldState.data.activePlayer : null;
        if (!activePlayer || actorName === activePlayer) return actorName;
        const desc = (worldState.data && worldState.data.players && worldState.data.players[actorName]) ? (worldState.data.players[actorName].description || '') : '';
        if (typeof PromptBuilder !== 'undefined' && typeof PromptBuilder.anonymousName === 'function') {
            return PromptBuilder.anonymousName(activePlayer, actorName, desc) || actorName;
        }
        return actorName;
    }

    function buildConciseNarrative(rawEntries) {
        const entries = structuredEntries(rawEntries).filter(isObserverVisible);
        if (!entries.length) return '';

        const playerName = (typeof worldState !== 'undefined' && worldState.data && worldState.data.activePlayer) ? worldState.data.activePlayer : 'You';
        const sentences = [];

        for (const e of entries) {
            const actor = e.actor === playerName ? 'You' : observerName(e.actor);
            if (e.type === 'speech') {
                sentences.push(actor + ' says, "' + e.content + '"');
            } else if (e.type === 'whisper') {
                sentences.push(actor + ' whispers');
            } else if (e.type === 'action') {
                const cleaned = e.content.replace(/^(go|approach|dash|open|close|take|drop|use|examine|attack|grab|lead|steal|give|rest|wait|stand|escape|struggle)\s+/i, '').trim();
                if (cleaned) sentences.push(actor + ' ' + cleaned);
            } else if (e.type === 'emote') {
                sentences.push(e.content);
            } else if (e.type === 'result') {
                const t = truncateResult(e.content, 140);
                if (t) sentences.push(t);
            }
        }

        const text = sentences.join('. ') + (sentences.length ? '.' : '');
        return text.length > 260 ? text.slice(0, 257) + '...' : text;
    }

    /* ── summary builder ───────────────────────────────────────────── */

    function buildSummary(rawEntries) {
        const entries = structuredEntries(rawEntries);
        if (!entries.length) return '';

        const playerName = (typeof worldState !== 'undefined' && worldState.data && worldState.data.activePlayer) ? worldState.data.activePlayer : 'You';
        const actors = new Set();
        const byActor = new Map();

        for (const e of entries) {
            const key = e.actor || '???';
            actors.add(key);
            if (!byActor.has(key)) byActor.set(key, []);
            byActor.get(key).push(e);
        }

        const parts = [];
        for (const actor of actors) {
            if (actor === playerName || actor === 'World' || actor === '⚙️' || actor === 'LLM') continue;
            const list = byActor.get(actor) || [];
            const speech = list.filter(e => e.type === 'speech' || e.type === 'whisper').map(e => '"' + e.content + '"').join(', ');
            const actions = list.filter(e => e.type === 'action').map(e => e.content).join(', ');
            const emotes = list.filter(e => e.type === 'emote').slice(0, 1).map(e => e.content).join(', ');
            const bits = [];
            if (speech) bits.push('said ' + speech);
            if (emotes) bits.push(emotes);
            if (actions) bits.push(actions);
            if (bits.length) parts.push(actor + ' ' + bits.join(' while '));
        }

        const playerBits = (byActor.get(playerName) || []).filter(e => e.type === 'action').map(e => e.content).join(', ');
        if (playerBits) parts.push('You ' + playerBits);

        const text = parts.join('. ') + (parts.length ? '.' : '');
        return text.length > 220 ? text.slice(0, 217) + '...' : text;
    }

    /* ── rendering ─────────────────────────────────────────────────── */

    function ensureFeedStyles() {
        if (document.getElementById('tf-styles')) return;
        const style = document.createElement('style');
        style.id = 'tf-styles';
        style.textContent = `
            .tf-summary { color:#e8c49a; font-size:12px; line-height:1.5; padding:6px 10px 8px; background:#241a10; border:1px solid #40301c; border-radius:8px; margin-bottom:8px; }
            .tf-summary b { color:#ffb37a; }
            .tf-toggle { display:inline-flex; gap:4px; margin-left:8px; vertical-align:middle; }
            .tf-toggle button { background:#1d212a; border:1px solid #2a303b; color:#8b95a1; border-radius:6px; padding:3px 8px; font-size:10.5px; cursor:pointer; }
            .tf-toggle button.on { background:#2b1f42; color:#d9baff; border-color:#4a3668; }
            .tf-turn-marker { font-size:10.5px; text-transform:uppercase; letter-spacing:1px; color:#78828e; margin:8px 0 6px; display:flex; align-items:center; gap:8px; }
            .tf-turn-marker::after { content:""; flex:1; border-top:1px solid #232932; }
            .tf-group { margin-bottom:10px; padding-left:8px; border-left:2px solid #232932; }
            .tf-group.tf-you { border-left-color:#4f9cf9; }
            .tf-group.tf-other { border-left-color:#d9baff; }
            .tf-group.tf-world { border-left-color:#3a4350; }
            .tf-row { display:flex; gap:8px; padding:3px 0; line-height:1.45; font-size:12px; }
            .tf-icon { width:18px; text-align:center; flex:none; opacity:.9; }
            .tf-body { min-width:0; }
            .tf-actor { font-weight:600; color:#e6e8ee; margin-right:4px; }
            .tf-actor.tf-you { color:#ffb37a; }
            .tf-actor.tf-other { color:#d9baff; }
            .tf-actor.tf-world { color:#6b7686; }
            .tf-quote { color:#e8c49a; font-style:italic; }
            .tf-quote::before { content:open-quote; }
            .tf-quote::after { content:close-quote; }
            .tf-action { color:#bcd3ec; }
            .tf-emote { color:#d9c9a9; font-style:italic; }
            .tf-result { color:#98a3ae; }
            .tf-system { color:#6b7686; font-style:italic; }
            .tf-meta { font-size:10.5px; color:#55606c; margin-top:2px; }
            .tf-badge { display:inline-block; font-size:10px; padding:1px 6px; border-radius:999px; background:#1d212a; border:1px solid #2a303b; color:#8b95a1; margin-left:6px; vertical-align:middle; }
        `;
        document.head.appendChild(style);
    }

    function escapeHtml(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderStructured(host, limit = 14, entries = null) {
        install();
        host.textContent = '';
        const tail = (entries || _scopedRing()).slice(-limit);
        if (!tail.length) {
            const empty = document.createElement('div');
            empty.className = 'tfd-line tfd-empty';
            empty.textContent = 'nothing yet — the world is quiet.';
            host.appendChild(empty);
            return;
        }

        ensureFeedStyles();

        const toggle = document.createElement('div');
        toggle.className = 'tf-toggle';
        const conciseBtn = document.createElement('button');
        conciseBtn.type = 'button';
        conciseBtn.textContent = 'Concise';
        const detailedBtn = document.createElement('button');
        detailedBtn.type = 'button';
        detailedBtn.textContent = 'Detailed';
        toggle.appendChild(conciseBtn);
        toggle.appendChild(detailedBtn);
        host.appendChild(toggle);

        const useConcise = () => {
            conciseBtn.classList.add('on');
            detailedBtn.classList.remove('on');
            renderObserverFeed(host, tail);
        };
        const useDetailed = () => {
            detailedBtn.classList.add('on');
            conciseBtn.classList.remove('on');
            renderDetailedFeed(host, limit);
        };

        conciseBtn.addEventListener('click', useConcise);
        detailedBtn.addEventListener('click', useDetailed);

        if (_observerMode) useConcise();
        else useDetailed();
    }

    function renderObserverFeed(host, rawEntries) {
        host.textContent = '';
        if (!rawEntries.length) {
            const empty = document.createElement('div');
            empty.className = 'tfd-line tfd-empty';
            empty.textContent = 'nothing observable yet — the world is quiet.';
            host.appendChild(empty);
            return;
        }

        ensureFeedStyles();

        const narrative = buildConciseNarrative(rawEntries);
        if (narrative) {
            const sumEl = document.createElement('div');
            sumEl.className = 'tf-summary';
            sumEl.innerHTML = '<b>Observed:</b> ' + escapeHtml(narrative);
            host.appendChild(sumEl);
        }

        let currentTick = null;
        let lastActor = null;
        let lastType = null;

        for (const entry of rawEntries) {
            const parsed = parseEntry(entry);
            if (!parsed || !isObserverVisible(parsed)) continue;

            const tickMatch = entry.text.match(/Tick\s+(\d+)/i);
            const tick = tickMatch ? tickMatch[1] : null;
            if (tick && tick !== currentTick) {
                currentTick = tick;
                const marker = document.createElement('div');
                marker.className = 'tf-turn-marker';
                marker.textContent = 'Tick ' + tick;
                host.appendChild(marker);
                lastActor = null;
                lastType = null;
            }

            const playerName = (typeof worldState !== 'undefined' && worldState.data && worldState.data.activePlayer) ? worldState.data.activePlayer : 'You';
            const isPlayer = parsed.actor === 'You' || parsed.actor === playerName;
            const actorKey = parsed.actor || '???';
            const displayActor = isPlayer ? 'You' : observerName(parsed.actor);
            const changeActor = lastActor !== actorKey;
            const changeType = lastType !== parsed.type;
            const needGap = changeActor || changeType;

            if (needGap && lastActor !== null) {
                const spacer = document.createElement('div');
                spacer.style.height = '4px';
                host.appendChild(spacer);
            }

            const group = document.createElement('div');
            group.className = 'tf-group ' + (isPlayer ? 'tf-you' : 'tf-other');

            const row = document.createElement('div');
            row.className = 'tf-row';

            const icon = document.createElement('span');
            icon.className = 'tf-icon';
            const icons = { speech: '💬', whisper: '🔒', action: '▶️', emote: '🎭', result: '🔎', npc: '👾' };
            icon.textContent = icons[parsed.type] || '•';

            const body = document.createElement('div');
            body.className = 'tf-body';

            if (displayActor) {
                const actorEl = document.createElement('span');
                actorEl.className = 'tf-actor ' + (isPlayer ? 'tf-you' : 'tf-other');
                actorEl.textContent = displayActor;
                body.appendChild(actorEl);
            }

            const contentEl = document.createElement('span');
            if (parsed.type === 'speech') {
                contentEl.className = 'tf-quote';
                contentEl.textContent = parsed.content;
                const meta = document.createElement('div');
                meta.className = 'tf-meta';
                meta.textContent = (parsed.volume && parsed.volume !== 'say' ? 'said · ' + parsed.volume : 'said');
                body.appendChild(contentEl);
                body.appendChild(meta);
            } else if (parsed.type === 'whisper') {
                contentEl.className = 'tf-action';
                contentEl.textContent = 'whispered';
                const meta = document.createElement('div');
                meta.className = 'tf-meta';
                meta.textContent = parsed.volume && parsed.volume !== 'say' ? parsed.volume : '';
                body.appendChild(contentEl);
                if (meta.textContent) body.appendChild(meta);
            } else if (parsed.type === 'action') {
                contentEl.className = 'tf-action';
                contentEl.textContent = truncateResult(parsed.content, 180);
                body.appendChild(contentEl);
            } else if (parsed.type === 'emote') {
                contentEl.className = 'tf-emote';
                contentEl.textContent = parsed.content;
                body.appendChild(contentEl);
            } else if (parsed.type === 'result') {
                contentEl.className = 'tf-result';
                contentEl.textContent = truncateResult(parsed.content, 180);
                body.appendChild(contentEl);
            } else {
                contentEl.textContent = parsed.content;
                body.appendChild(contentEl);
            }

            row.appendChild(icon);
            row.appendChild(body);
            group.appendChild(row);
            host.appendChild(group);

            lastActor = actorKey;
            lastType = parsed.type;
        }
    }

    function renderDetailedFeed(host, limit = 14) {
        install();
        host.textContent = '';
        const tail = _scopedRing().slice(-limit);
        if (!tail.length) {
            const empty = document.createElement('div');
            empty.className = 'tfd-line tfd-empty';
            empty.textContent = 'nothing yet — the world is quiet.';
            host.appendChild(empty);
            return;
        }

        ensureFeedStyles();

        const summary = buildSummary(tail);
        if (summary) {
            const sumEl = document.createElement('div');
            sumEl.className = 'tf-summary';
            sumEl.innerHTML = '<b>Since your turn:</b> ' + escapeHtml(summary);
            host.appendChild(sumEl);
        }

        let currentTick = null;
        let lastActor = null;
        let lastType = null;

        for (const entry of tail) {
            const parsed = parseEntry(entry);
            if (!parsed) continue;

            const tickMatch = entry.text.match(/Tick\s+(\d+)/i);
            const tick = tickMatch ? tickMatch[1] : null;
            if (tick && tick !== currentTick) {
                currentTick = tick;
                const marker = document.createElement('div');
                marker.className = 'tf-turn-marker';
                marker.textContent = 'Tick ' + tick;
                host.appendChild(marker);
                lastActor = null;
                lastType = null;
            }

            const isPlayer = parsed.actor === 'You' || parsed.actor === (worldState && worldState.data && worldState.data.activePlayer);
            const actorKey = parsed.actor || '???';
            const changeActor = lastActor !== actorKey;
            const changeType = lastType !== parsed.type;
            const needGap = changeActor || changeType;

            if (needGap && lastActor !== null) {
                const spacer = document.createElement('div');
                spacer.style.height = '4px';
                host.appendChild(spacer);
            }

            const group = document.createElement('div');
            group.className = 'tf-group ' + (isPlayer ? 'tf-you' : 'tf-other');

            const row = document.createElement('div');
            row.className = 'tf-row';

            const icon = document.createElement('span');
            icon.className = 'tf-icon';
            const icons = { speech: '💬', whisper: '🔒', action: '▶️', emote: '🎭', result: '🔎', system: '⚙️', npc: '👾', recall: '🧠', thought: '💭', unknown: '•' };
            icon.textContent = icons[parsed.type] || '•';

            const body = document.createElement('div');
            body.className = 'tf-body';

            if (parsed.actor) {
                const actorEl = document.createElement('span');
                actorEl.className = 'tf-actor ' + (isPlayer ? 'tf-you' : 'tf-other');
                actorEl.textContent = parsed.actor;
                body.appendChild(actorEl);
            }

            const contentEl = document.createElement('span');
            if (parsed.type === 'speech' || parsed.type === 'whisper') {
                contentEl.className = 'tf-quote';
                contentEl.textContent = parsed.content;
                const meta = document.createElement('div');
                meta.className = 'tf-meta';
                meta.textContent = (parsed.type === 'whisper' ? 'whispered' : 'said') + (parsed.volume && parsed.volume !== 'say' ? ' · ' + parsed.volume : '');
                body.appendChild(contentEl);
                body.appendChild(meta);
            } else if (parsed.type === 'action') {
                contentEl.className = 'tf-action';
                contentEl.textContent = truncateResult(parsed.content, 180);
                body.appendChild(contentEl);
            } else if (parsed.type === 'emote') {
                contentEl.className = 'tf-emote';
                contentEl.textContent = parsed.content;
                body.appendChild(contentEl);
            } else if (parsed.type === 'result') {
                contentEl.className = 'tf-result';
                contentEl.textContent = truncateResult(parsed.content, 180);
                body.appendChild(contentEl);
            } else if (parsed.type === 'system' || parsed.type === 'npc' || parsed.type === 'recall') {
                contentEl.className = 'tf-system';
                contentEl.textContent = parsed.content;
                body.appendChild(contentEl);
            } else {
                contentEl.textContent = parsed.content;
                body.appendChild(contentEl);
            }

            row.appendChild(icon);
            row.appendChild(body);
            group.appendChild(row);
            host.appendChild(group);

            lastActor = actorKey;
            lastType = parsed.type;
        }
    }

    /** Render the last *limit* entries into *host* (plain DOM). */
    function render(host, limit = 14) {
        renderStructured(host, limit);
    }

    /** Mark the boundary for "since your turn" (call when the panel closes). */
    function markTurnEnd() {
        install();
        _digestMark = _seq;
    }

    /** Entries logged since the last markTurnEnd() — the turn-start digest. */
    function digest() {
        install();
        const ctx = _viewerContext();
        return _ring.filter((e) => e.seq > _digestMark && _perceivableByViewer(e, ctx));
    }

    function clearDigest() { _digestMark = _seq; }

    function setObserverMode(value) {
        _observerMode = !!value;
    }

    function getObserverMode() {
        return _observerMode;
    }

    return { render, markTurnEnd, digest, clearDigest, parseEntry, structuredEntries, buildSummary, setObserverMode, getObserverMode };
})();
