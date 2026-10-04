/**
 * prompt-builder/memory-context.js — Memory retrieval + investigation notes.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). This is the one
 * part of the prompt builder that does async fetches and its own local
 * scoring/parsing pipeline (the investigation-notes logic is a mini-subsystem),
 * so it earns a standalone file. Exports merge into window.PromptBuilder.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/memory-context — memory retrieval + investigation notes
 * @contributes buildMemoryContext: async recall scoring, keyword/semantic/recent mix, investigation notes
 * @powers Memory — the "=== I REMEMBER ===" block and the discovery-note pipeline
 * @relates the only async module here; uses memory-manager + shared/embedding-client
 * @docs docs/virtualWorld/AI & Narration/Memory System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    /**
     * "What I've already done" block — the anti-repeat guard for agents that
     * get stuck re-examining the same object. Sources, deliberately NOT the
     * memory store:
     *   - player.discovered_items (backend, persistent, Entertainment task):
     *     items this character has already examined/taken.
     *   - browser-side actionHistory (last 20 tracked actions): verb+target
     *     counts so repeated attempts surface as explicit warnings.
     */
    function buildAlreadyKnownContext(charName: string): string {
        if (!charName) return '';
        const player = worldState.data?.players?.[charName];
        const discovered: string[] = Array.isArray(player?.discovered_items)
            ? player.discovered_items.filter(Boolean)
            : [];
        const actionHistory: ActionHistoryEntry[] = (VW?.events?.getCharacterState?.(charName)?.actionHistory || [])
            .filter((entry: ActionHistoryEntry) => entry && typeof entry.action === 'string' && entry.action.trim() && entry.result);

        if (discovered.length === 0 && actionHistory.length === 0) return '';

        const lines: string[] = [];

        if (discovered.length > 0) {
            lines.push('=== ALREADY KNOWN ===');
            lines.push(`You have already examined or taken: ${discovered.join(', ')}.`);
            lines.push('');
        }

        // Count repeated verb+target combos from the live action history.
        const counts = new Map<string, number>();
        const normalizeTarget = (target: unknown) => String(target || '').toLowerCase().replace(/^the\s+/, '').replace(/[_\s]+/g, ' ').trim();
        for (const entry of actionHistory) {
            const words = String(entry.action).trim().split(/\s+/);
            const verb = (words.shift() || '').toLowerCase();
            if (words.length === 0 || !verb) continue;
            const key = `${verb}::${normalizeTarget(words.join(' '))}`;
            counts.set(key, (counts.get(key) || 0) + 1);
        }

        const repeatableVerbs = new Set(['examine', 'read', 'search', 'look', 'take', 'use', 'use_on', 'open', 'close', 'wear']);
        const repeats = [...counts.entries()]
            .filter(([key, count]) => repeatableVerbs.has(key.split('::')[0]) && count >= 2)
            .sort((entryA, entryB) => entryB[1] - entryA[1]);

        if (repeats.length > 0) {
            const [key, count] = repeats[0];
            const [verb, target] = key.split('::');
            const pastTense: Record<string, string> = { examine: 'examined', read: 'read', search: 'searched', look: 'looked at', take: 'taken', use: 'used', use_on: 'used', open: 'opened', close: 'closed', wear: 'worn' };
            const pastTenseText = pastTense[verb] || (verb + 'd');
            const nudge = verb === 'examine' || verb === 'read' || verb === 'search' || verb === 'look'
                ? ' Stop examining — actually take, wear, or use the things here.'
                : ' Pick a different action.';
            lines.push(`⚠️ You have ${pastTenseText} "${target}" ${count} times now and nothing changed.${nudge}`);
            lines.push('');
        }

        return '\n' + lines.join('\n');
    }

    /**
     * Emotional residue (task-96): when emotionally-tagged memories surface in
     * recall, re-feel a fraction of what they carried. "We remember, therefore
     * we feel." Fire-and-forget; scaled by the emotion.recall_spike_scale
     * engine tunable server-side is NOT applied here — we scale client-side so
     * one build never stacks more than a whisper of affect.
     */
    const _respikeTickGuard: Record<string, number> = {};
    async function _respikeFromMemories(charName: string, topMemories: ScoredMemory[]): Promise<void> {
        const raw = worldState.data?.players?.[charName];
        if (!raw) return;
        const now = Date.now();
        if (now - (_respikeTickGuard[charName] || 0) < 5000) return;

        // Collect every attached emotion (plural memory_emotions list, or the
        // single legacy emotion field), so all of them can re-feel, not just the
        // strongest.
        const emotions: EmotionTag[] = [];
        for (const entry of topMemories) {
            const list: EmotionTag[] = Array.isArray(entry.memory_emotions) && entry.memory_emotions.length
                ? entry.memory_emotions
                : (entry.emotion ? [entry.emotion] : []);
            for (const e of list) {
                if (e && e.label) emotions.push(e);
            }
        }
        if (emotions.length === 0) return;

        // Resolve each label to an affect dimension (semantic embedding fallback
        // for novel labels; keyword otherwise) and accumulate dimension deltas.
        const mapped: Record<string, number> = {};
        const scale = 1.7;
        const emotionMapper = (window as unknown as {
            EmotionMapper?: { resolve(label: unknown): Promise<{ dimension?: string } | null> };
        }).EmotionMapper;
        for (const e of emotions) {
            let dim: string | null = null;
            if (emotionMapper) {
                const r = await emotionMapper.resolve(e.label);
                if (r && r.dimension) dim = r.dimension;
            } else if (typeof e.label === 'string') {
                dim = e.label;
            }
            if (!dim) continue;
            const intensity = Math.max(1, Math.min(10, Number(e.intensity) || 5));
            mapped[dim] = (mapped[dim] || 0) + intensity * scale;
        }
        if (Object.keys(mapped).length === 0) return;

        _respikeTickGuard[charName] = now;
        // N6: send the triggering memory as `reason` — the backend writes
        // "Remembered: 'X' — it made me feel this way toward Y." instead of
        // a contentless placeholder. Full text; no truncation.
        const firstWithEmotion = topMemories.find((m: ScoredMemory) => {
            const list = Array.isArray(m.memory_emotions) && m.memory_emotions.length
                ? m.memory_emotions
                : (m.emotion ? [m.emotion] : []);
            return list.length > 0;
        });
        const reason = firstWithEmotion
            ? String(firstWithEmotion.text || '').replace(/^\[[^\]]*\]\s*/, '').trim()
            : '';
        fetch(`/api/players/${encodeURIComponent(charName)}/emotions/map`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reason ? { mapped, reason } : { mapped })
        }).catch(() => {});
    }

    /**
     * Build memory context for a character — retrieves relevant memories,
     * scores them by relevance, and builds investigation notes.
     * @param {string} charName - Character name
     * @param {Object} [opts] - Options: `report` streams turn-only recall
     *   feedback; `preview` (Agent Lens) skips the embedding server and all
     *   side effects (`_respikeFromMemories`, semantic recall) — a preview must
     *   never mutate the character or hammer the embedding API.
     * @returns {Promise<string>} Formatted memory context string or empty string
     */
    async function buildMemoryContext(charName: string, opts: MemoryOpts = {}): Promise<string> {
        if (!charName) return '';
        const preview = !!opts.preview;
        const player = worldState.data?.players?.[charName];
        const currentArea = player?.current_area;
        const parts: string[] = [];

        // 1. Spatial context from backend (KNOWN ROUTES FROM HERE)
        try {
            const resp = await fetch(`/api/players/${encodeURIComponent(charName)}/memories/spatial`, {
                headers: { 'Accept': 'application/json' }
            });
            if (resp.ok) {
                const data = await resp.json();
                if (data.spatial) parts.push(data.spatial);
            }
        } catch (e) {
            // Spatial context is best-effort — ignore failures
        }

        // 1b. "What I've already done" — repeat-loop guard. Fed from the
        // backend discovered_items list (Entertainment task) + the live
        // browser actionHistory, deliberately NOT from the memory store.
        const alreadyKnown = buildAlreadyKnownContext(charName);
        if (alreadyKnown) parts.push(alreadyKnown);

        // 2. Build query from current area + last thought + what was just heard
        // (the retrieval trigger should be explainable: area + own latest
        // thought + the last lines spoken around the character).
        const characterState = VW?.events?.getCharacterState?.(charName);
        const lastThought = (characterState?.lastThought || '');
        const heardLines: string[] = (player?.recent_hearing || [])
            .filter((h: { type?: unknown; speaker?: unknown; text?: unknown }) => h.type !== 'sound_source' && h.speaker !== charName && h.text)
            .slice(-2)
            .map((h: { text?: unknown }) => String(h.text).trim()).filter(Boolean);
        const queryParts = [currentArea || '', lastThought, ...heardLines];
        const query = queryParts.join(' ').trim() || (currentArea || '');
        const queryWords = new Set<string>(query.toLowerCase().split(/\s+/).filter(Boolean));

        // 3. Collect and score memories from both sources
        const MEM_ICONS: Record<string, string> = {observation:'👁️',discovery:'💡',conversation:'💬',item:'📦',combat:'⚔️',exploration:'🗺️',failure:'⚠️',success:'✅',reflection:'🔄',action:'▶️',speech:'💬',thought:'🤔',reaction:'💭',location:'📍'};
        const memIcon = (memoryType: unknown) => MEM_ICONS[String(memoryType)]||'📝';

        // Helper: infer type from text for old-format memories
        const inferIcon = (textValue: unknown) => {
            const lowerText = String(textValue || '').toLowerCase();
            if (lowerText.startsWith('[') && lowerText.includes(']')) return lowerText.substring(1, lowerText.indexOf(']')).trim();
            if (lowerText.startsWith('💬') || lowerText.includes('said:') || lowerText.includes('says:')) return 'speech';
            if (lowerText.startsWith('💭') || lowerText.includes('thought')) return 'thought';
            if (lowerText.startsWith('▶️') || lowerText.startsWith('⚙️')) return 'action';
            if (lowerText.includes('attack') || lowerText.includes('damage') || lowerText.includes('killed')) return 'combat';
            return '📝';
        };

        let scored: ScoredMemory[] = [];

        // Score memories from the unified backend store. `reinforce: !preview`
        // (task-686): retrieval reinforces what it recalls, but a preview must
        // never mutate the character.
        try {
            const resp = await fetch(`/api/players/${encodeURIComponent(charName)}/memories/retrieve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    max_results: 10,
                    entity_boost: true,
                    reinforce: !preview,
                    current_area_id: currentArea ? `area_${currentArea.toLowerCase().replace(/\s+/g, '_')}` : ''
                })
            });
            if (resp.ok) {
                const data = await resp.json();
                for (const mem of (data.memories || [])) {
                    // A5: never render "undefined" — skip textless entries
                    const memText = String((typeof mem === 'object' && mem?.text) || '').trim();
                    if (!memText) continue;
                    // Backend now includes score directly on the memory object.
                    const backendScore = typeof mem.score === 'number' ? mem.score : null;
                    const icon = memIcon(mem.type);
                    scored.push({ text: `[${events.tickToRelative(mem.tick)}] ${icon} ${memText}`, score: backendScore !== null ? backendScore : 1.0, tick: mem.tick, emotion: mem.emotion || null, source: 'retrieved', category: mem.category, type: mem.type, confidence: typeof mem.confidence === 'number' ? mem.confidence : undefined, contradicts: Array.isArray(mem.contradicts) ? mem.contradicts : [] });
                }
            }
        } catch (e) {
            // Retrieval is best-effort — fall through to player.memories scoring
        }

        // Score player.memories[] entries
        const rawMemories: RawMemory[] = player?.memories || [];
        for (const raw of rawMemories) {
            const textContent: string = typeof raw === 'string' ? raw : (raw as RawMemoryObject).text || '';
            const tickValue = typeof raw === 'object' ? (raw as RawMemoryObject).tick || 0 : 0;
            if (!textContent) continue;
            const textLower = textContent.toLowerCase();
            let overlap = 0;
            for (const word of queryWords) {
                if (textLower.includes(word)) overlap++;
            }
            const keywordScore = queryWords.size > 0 ? overlap / queryWords.size : 0;
            const icon = memIcon(inferIcon(textContent));
            // A8: stopwords never explain a match ("keyword match on (in,i,a)")
            const STOPWORDS = new Set(['a','an','the','in','on','of','to','for','and','or','but','if','so','then','there','their','them','they','this','that','with','from','just','now','really','about','when','what','where','how','why','is','are','was','were','be','been','it','its','at','as','by','my','me','i','we','you','your','not','no','yes','oh','well','much','nice','very','too','will','would','can','could','shall','should','am','get','got','go','one','two','three','after','before']);
            const matchedWords: string[] = [];
            for (const word of queryWords) {
                if (STOPWORDS.has(word)) continue;
                if (textLower.includes(word)) matchedWords.push(word);
            }
            // Include if it has keyword overlap OR we haven't collected enough candidates yet
            if (keywordScore > 0 || scored.length < 8) {
                scored.push({ text: `[${events.tickToRelative(tickValue)}] ${icon} ${textContent}`, score: keywordScore, tick: tickValue, emotion: (typeof raw === 'object' && (raw as RawMemoryObject).emotion) || null, source: 'keyword', kb: keywordScore, matchedWords, memTags: ((typeof raw === 'object' && Array.isArray((raw as RawMemoryObject).tags)) ? (raw as RawMemoryObject).tags : []) });
            }
        }

        // Semantic recall (task-91): embed the query, ask the backend vector
        // store for this character's top-k memories, and merge them into the
        // candidate pool scored by cosine similarity. Silent no-op when the
        // embedding settings are off or the call fails. Skipped entirely in
        // preview mode (Agent Lens) — previews must not hit the embedding
        // server on every state poll.
        if (!preview && (window as unknown as { EmbeddingClient?: { configured(): boolean } }).EmbeddingClient?.configured()) {
            try {
                const queryVector = await EmbeddingClient.embed(query);
                if (queryVector) {
                    const resp = await fetch('/api/memory/embeddings/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ character: charName, vector: queryVector, k: 5 })
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        const hitIds: string[] = [];
                        for (const hit of (data.results || [])) {
                            if (hit.score < 0.35) continue;
                            const memEntry = rawMemories.find((m: RawMemory) => (typeof m === 'object' && (m as RawMemoryObject).id === hit.memory_id));
                            const textContent = typeof memEntry === 'object' ? ((memEntry as RawMemoryObject)?.text || '') : '';
                            if (!textContent) continue;
                            hitIds.push(String(hit.memory_id));
                            const tickValue = (memEntry as RawMemoryObject).tick || 0;
                            const icon = memIcon((memEntry as RawMemoryObject).type);
                            scored.push({ text: `[${events.tickToRelative(tickValue)}] ${icon} ${textContent}`, score: 2.0 * hit.score, tick: tickValue, emotion: (memEntry as RawMemoryObject).emotion || null, source: 'vector', kb: hit.score, category: (memEntry as RawMemoryObject).category, type: (memEntry as RawMemoryObject).type, confidence: typeof ((memEntry as RawMemoryObject) as { confidence?: unknown }).confidence === 'number' ? ((memEntry as RawMemoryObject) as { confidence?: number }).confidence : undefined, contradicts: Array.isArray(((memEntry as RawMemoryObject) as { contradicts?: unknown }).contradicts) ? ((memEntry as RawMemoryObject) as { contradicts?: unknown[] }).contradicts : [] });
                        }
                        // task-686: semantic hits were recalled, so they reinforce
                        // — the scoring endpoint can't stamp them (it never saw
                        // them). Fire-and-forget; previews skip entirely.
                        if (hitIds.length > 0) {
                            fetch(`/api/players/${encodeURIComponent(charName)}/memories/reinforce`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ ids: hitIds, tick: worldState?.data?.time_ticks || 0 })
                            }).catch(() => {});
                        }
                    }
                }
            } catch (e) {
                // Semantic recall is best-effort — keyword scoring already ran.
            }
        }

        // Dedup by normalized text BEFORE picking the top-k. The three
        // retrieval pipelines (backend /retrieve, player.memories keyword, and
        // vector recall) can each return the SAME memory, so without this a
        // single memory showed 2-3x in "I REMEMBER" (task-350/. task-339 debug).
        const seenText = new Set<string>();
        const deduped: ScoredMemory[] = [];
        for (const entry of scored) {
            // A7: dedupe on the TEXT with the [timestamp] AND the leading icon
            // stripped — the same memory carries a different icon per pipeline
            // (🗺️ vector vs 📝 keyword), which used to defeat the dedupe.
            const bare = String(entry.text || '')
                .replace(/^\s*\[[^\]]*\]\s*/, '')
                .replace(/^[^A-Za-z0-9]+\s*/, '');
            const key = bare.replace(/\s+/g, ' ').toLowerCase();
            if (seenText.has(key)) continue;
            seenText.add(key);
            deduped.push(entry);
        }
        scored = deduped;

        // Sort by score desc, then recency
        scored.sort((entryA, entryB) => entryB.score - entryA.score || (entryB.tick || 0) - (entryA.tick || 0));
        const MAX_RECALL = 10;
        const MIN_RECALL_SCORE = 0.3;
        // Keep the top 3 always, then extend toward 10 for any memory within a
        // relevance floor, so recall is richer but never drops in noise.
        const topMemories = scored.slice(0, MAX_RECALL)
            .filter((m: ScoredMemory, i: number) => i < 3 || (m.score || 0) >= MIN_RECALL_SCORE);
        // N8: score picks WHAT is remembered; the ordering shown/injected is
        // recency-first so the prompt reads newest-first instead of interleaved.
        topMemories.sort((a: ScoredMemory, b: ScoredMemory) => (b.tick || 0) - (a.tick || 0));

        // Feed the EXISTING recall pipe (stream-raw-llm reads `_lastRecallStats`
        // to show \"recalled: N\" on the LLM request chip). We set it here so the
        // header note appears AND the expanded chip body can list WHAT + WHY.
        try {
            (window as unknown as { _lastRecallStats: unknown })._lastRecallStats = {
                at: Date.now(),
                count: topMemories.length,
                semantic: topMemories.filter((m: ScoredMemory) => m.source === 'vector').length,
                query: String(query || '').slice(0, 120),
                memories: topMemories.map((m: ScoredMemory) => ({
                    text: String(m.text || '').replace(/^\[[^\]]*\]\s*/, ''),
                    source: m.source,
                    score: m.score || 0,
                    matchedWords: m.matchedWords || [],
                    memTags: m.memTags || [],
                    kb: m.kb || 0,
                })),
            };
        } catch (e) { /* feedback is best-effort */ }

        // Turn-only recall feedback (opts.report): one stream line (no per-memory
        // ticks), showing WHAT was retrieved and WHY (incl. the query context).
        // Never runs from the inspector/agent-lens (which also calls this builder),
        // and never enters the LLM prompt.
        try {
            if (opts.report && typeof events?.log === 'function' && topMemories.length) {
                const lines = topMemories.map((m: ScoredMemory) => {
                    let why: string;
                    if (m.source === 'keyword') {
                        const words = (m.matchedWords?.length ? m.matchedWords.join(', ') : 'phrase');
                        const tags = (m.memTags?.length ? m.memTags.join(', ') : '');
                        why = `keyword (${words})${tags ? ` · tags ${tags}` : ''}`;
                    } else if (m.source === 'vector') {
                        why = `semantic ${Math.round((m.kb || 0) * 100) / 100}`;
                    } else {
                        // backend /retrieve — real score rides the entry (default 1.0 is a floor)
                        const score = (m.score || 0) > 1 ? ` (score ${Math.round(m.score * 100) / 100})` : '';
                        why = `recent${score}`;
                    }
                    const short = String(m.text || '').replace(/^\[[^\]]*\]\s*/, '');
                    return `  • ${short} — ${why}`;
                });
                const n = topMemories.length;
                const kw = topMemories.filter((m: ScoredMemory) => m.source === 'keyword').length;
                const vec = topMemories.filter((m: ScoredMemory) => m.source === 'vector').length;
                const rec = n - kw - vec;
                const queryShort = String(query || '').replace(/\s+/g, ' ');
                events.log(`🧠 recalled ${n} memor${n === 1 ? 'y' : 'ies'} · query "${queryShort}" (${kw} keyword · ${vec} semantic · ${rec} recent): \n${lines.join('\n')}`, 'system-msg', null, charName);
            }
        } catch (e) { /* feedback is best-effort */ }

        if (topMemories.length > 0) {
            parts.push('');
            parts.push('=== I REMEMBER ===');
            // task-690: the recall block is a character model, not event soup.
            // Sectioned when any conclusion-type memory is present; a character
            // with only episodes gets the plain list it always had.
            const categoryOf = (m: ScoredMemory): string => {
                const cat = m.category ? String(m.category) : '';
                if (cat) return cat;
                if (String(m.type || '') === 'reflection') return 'belief';
                const tags = (m.memTags || []).map((t: unknown) => String(t).toLowerCase());
                if (tags.some((t: string) => t.startsWith('rel:'))) return 'social';
                return 'episodic';
            };
            const certaintySuffix = (m: ScoredMemory): string => {
                const flags: string[] = [];
                if (Array.isArray(m.contradicts) && m.contradicts.length > 0) {
                    flags.push('⚡ this conflicts with another memory');
                }
                if (typeof m.confidence === 'number' && m.confidence < 0.5) {
                    flags.push('you are not sure of this');
                }
                return flags.length > 0 ? ` (${flags.join('; ')})` : '';
            };
            const sections: Array<[string, ScoredMemory[]]> = [
                ['EVENTS — what happened', []],
                ['WHAT I BELIEVE', []],
                ['HOW I SEE PEOPLE', []],
                ['WHAT I EXPECT', []]
            ];
            for (const memoryEntry of topMemories) {
                const cat = categoryOf(memoryEntry);
                if (cat === 'belief' || cat === 'semantic') sections[1][1].push(memoryEntry);
                else if (cat === 'social') sections[2][1].push(memoryEntry);
                else if (cat === 'procedural') sections[3][1].push(memoryEntry);
                else sections[0][1].push(memoryEntry);
            }
            const hasModel = sections.slice(1).some(([, list]) => list.length > 0);
            for (const [header, list] of sections) {
                if (list.length === 0) continue;
                if (hasModel) parts.push(header);
                for (const memoryEntry of list) {
                    parts.push(memoryEntry.text + certaintySuffix(memoryEntry));
                }
            }
            if (!preview) _respikeFromMemories(charName, topMemories);
        } else {
            parts.push('');
            parts.push('=== I REMEMBER ===');
            parts.push("You don't remember anything relevant right now.");
        }

        // ── Parse action memories into investigation notes ──
        const actionInfo: ActionInfo[] = [];
        const actionCounts: Record<string, number> = {};

        for (const raw of rawMemories) {
            const textContent: string = typeof raw === 'string' ? raw : (raw as RawMemoryObject).text || '';
            if (!textContent) continue;
            
            // Try arrow first, then colon for backward compatibility
            let separatorIdx = textContent.indexOf(' → ');
            let separatorLen = 3;
            if (separatorIdx === -1) {
                separatorIdx = textContent.indexOf(':');
                separatorLen = 1;
            }
            if (separatorIdx === -1) continue;
            
            // Strip leading emoji/icon from actionPart
            const actionPart = textContent.substring(0, separatorIdx).replace(/^[^\w]+/, '').trim().toLowerCase();
            const resultText = textContent.substring(separatorIdx + separatorLen).trim();
            if (!resultText) continue;

            const knownVerbs = ['examine', 'use', 'take', 'open', 'close', 'read', 'drink', 'eat', 'light', 'go', 'approach'];
            const verb = actionPart.split(/\s+/)[0];
            const target = actionPart.substring(verb.length).trim();
            if (!knownVerbs.includes(verb)) continue;

            const key = actionPart.replace(/\s+/g, '_');
            actionCounts[key] = (actionCounts[key] || 0) + 1;
            const actionCount = actionCounts[key];
            const failed = /can'?t|cannot|don'?t have|doesn'?t have|no purchase|purely decorative|nothing happens|isn'?t|not a|can'?t find|full|doesn'?t budge|part of the scenery|not valid|you look for|don'?t see it/.test(resultText.toLowerCase());

            let fact = resultText.replace(/^(you\s+)?(use[d]?|examine[d]?|open[ed]?|close[d]?|rea[d]?|drink?|eat[en]?|light[ed]?|t[ao]ke?)\s+/i, '');
            fact = fact.replace(/^you\s+/, '');
            const dotIdx = fact.indexOf('.');
            if (dotIdx > 15) fact = fact.substring(0, dotIdx + 1);
            else if (dotIdx === -1 && fact.length > 100) fact = fact.substring(0, 100) + '...';

            if (fact.trim()) {
                actionInfo.push({ verb, target, fact: fact.trim(), count: actionCount, key, failed });
            }
        }

        // ── Build Investigation Notes ──
        if (actionInfo.length > 0) {
            const findings: string[] = [];
            const seenTargets = new Set<string>();

            // Examine findings grouped by unique target
            for (const actionItem of actionInfo) {
                if (actionItem.verb !== 'examine') continue;
                if (seenTargets.has(actionItem.target)) continue;
                seenTargets.add(actionItem.target);
                const repeatCount = actionItem.count;
                const repeatNote = repeatCount >= 2 ? ` (examined ${repeatCount}x)` : '';
                findings.push(`- ${actionItem.target}: ${actionItem.fact}${repeatNote}`);
            }

            // Way/movement findings
            for (const actionItem of actionInfo) {
                if (actionItem.verb === 'go' || actionItem.verb === 'open' || actionItem.verb === 'close') {
                    if (actionItem.fact && !findings.some((finding: string) => finding.includes(actionItem.target))) {
                        findings.push(`- ${actionItem.target}: ${actionItem.fact}`);
                    }
                }
            }

            // Repeat warnings — any verb, and failure-aware so impossible
            // attempts (e.g. "use create flame on dry leaves") get flagged
            // instead of re-attempted forever.
            const repeatedFails = actionInfo.filter((actionItem: ActionInfo) => actionItem.failed && actionItem.count >= 3);
            if (repeatedFails.length > 0) {
                const r = repeatedFails[0];
                findings.push(`⚠️ You've tried "${r.key.replace(/_/g, ' ')}" ${r.count} times and it failed each time. Pick a different approach.`);
            } else {
                const repeats = actionInfo.filter((actionItem: ActionInfo) => actionItem.verb === 'examine' && actionItem.count >= 3);
                if (repeats.length > 0) {
                    findings.push(`⚠️ You've examined "${repeats[0].target}" ${repeats[0].count} times with no new information. Move on.`);
                }
            }

            // What still needs doing
            const doneKeys = new Set(actionInfo.map((actionItem: ActionInfo) => actionItem.key));
            const playerState = worldState.data?.players?.[charName];
            const curRoom = playerState?.current_area;
            const areaData = curRoom ? worldState.areas?.[curRoom] : null;
            const areaItems: ({ name?: unknown } | string)[] = curRoom ? worldState.getItemsInArea(curRoom) : [];
            const areaExits: Record<string, { hidden?: unknown }> = areaData?.exits || {};

            const suggestions: string[] = [];
            const goTargets = actionInfo.filter((actionItem: ActionInfo) => actionItem.verb === 'go').map((actionItem: ActionInfo) => actionItem.target.toLowerCase().trim());
            const examineTargets = actionInfo.filter((actionItem: ActionInfo) => actionItem.verb === 'examine').map((actionItem: ActionInfo) => actionItem.target.toLowerCase().trim());
            const takeTargets = actionInfo.filter(actionItem => actionItem.verb === 'take').map(actionItem => actionItem.target.toLowerCase().trim());
            for (const [dir, exitData] of Object.entries(areaExits)) {
                if (exitData.hidden) continue;
                const exitName = dir.replace(/_/g, ' ').toLowerCase();
                const alreadyMoved = goTargets.some((goTarget: string) => goTarget === exitName || goTarget.includes(exitName) || exitName.includes(goTarget));
                const alreadyExamined = examineTargets.some((examineTarget: string) => examineTarget === exitName || examineTarget.includes(exitName) || exitName.includes(examineTarget));
                if (!alreadyMoved && !alreadyExamined) {
                    suggestions.push(`Go through "${dir}"`);
                }
            }
            for (const item of areaItems) {
                const itemName = String(typeof item === 'string' ? item : (item.name || '')).toLowerCase();
                if (itemName && !doneKeys.has(`examine_${itemName}`) && !doneKeys.has(`take_${itemName}`)) {
                    suggestions.push(`Examine or take "${itemName}"`);
                }
            }

            parts.push('=== MY INVESTIGATION NOTES ===');
            parts.push(`Location: ${curRoom || 'Unknown'}`);
            parts.push('');
            if (findings.length > 0) {
                parts.push('Findings:');
                parts.push(...findings);
                parts.push('');
            }
            if (suggestions.length > 0) {
                parts.push("What I haven't done yet:");
                parts.push(...suggestions.slice(0, 5).map((suggestion: string) => `  ❓ ${suggestion}`));
                parts.push('');
            }
            parts.push('Decision: Pick ONE from the list above and do it now.');
            parts.push('No more examining the same items — take action.');
        }

        return parts.length > 0 ? '\n' + parts.join('\n') : '';
    }

    Object.assign(window.PromptBuilder, {
        buildMemoryContext
    });
})();

// Declared below the first value statement on purpose: TypeScript drops a
// file's leading JSDoc block when the first statement is type-only, which would
// strip the `@module` header tools/js_module_index.py reads.
interface EmotionTag {
    label?: unknown;
    intensity?: unknown;
}

interface ScoredMemory {
    text: string;
    score: number;
    tick?: number;
    emotion?: unknown;
    source: string;
    kb?: number;
    matchedWords?: string[];
    memTags?: unknown[];
    memory_emotions?: EmotionTag[];
    category?: unknown;
    type?: unknown;
    confidence?: number;
    contradicts?: unknown[];
}

interface RawMemoryObject {
    text?: string;
    tick?: number;
    type?: unknown;
    emotion?: unknown;
    tags?: unknown[];
    id?: unknown;
    category?: unknown;
    confidence?: unknown;
    contradicts?: unknown;
}

type RawMemory = string | RawMemoryObject;

interface ActionHistoryEntry {
    action?: string;
    result?: unknown;
}

interface ActionInfo {
    verb: string;
    target: string;
    fact: string;
    count: number;
    key: string;
    failed: boolean;
}

interface MemoryOpts {
    report?: boolean;
    preview?: boolean;
}
