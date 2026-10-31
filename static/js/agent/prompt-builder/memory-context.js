"use strict";
/**
 * prompt-builder/memory-context.js  -  Memory retrieval + investigation notes.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). This is the one
 * part of the prompt builder that does async fetches and its own local
 * scoring/parsing pipeline (the investigation-notes logic is a mini-subsystem),
 * so it earns a standalone file. Exports merge into window.PromptBuilder.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/memory-context  -  memory retrieval + investigation notes
 * @contributes buildMemoryContext: async recall scoring, keyword/semantic/recent mix, investigation notes
 * @powers Memory  -  the "=== I REMEMBER ===" block and the discovery-note pipeline
 * @relates the only async module here; uses memory-manager + shared/embedding-client
 * @docs docs/virtualWorld/AI & Narration/Memory System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';
    /**
     * "What I've already done" block - the anti-repeat guard for agents that
     * get stuck re-examining the same object. Sources:
     *   - player observation memories (kind === 'item'): items this character
     *     has already examined or taken (task-430).
     *   - browser-side actionHistory (last 20 tracked actions): verb+target
     *     counts so repeated attempts surface as explicit warnings.
     */
    function buildAlreadyKnownContext(charName) {
        if (!charName)
            return '';
        const player = worldState.data?.players?.[charName];
        const discoveredSet = new Set();
        const absenceList = [];
        if (Array.isArray(player?.memories)) {
            for (const m of player.memories) {
                if (m && m.kind === 'item' && m.name) {
                    discoveredSet.add(String(m.name).trim());
                }
                else if (m && m.kind === 'absence') {
                    const target = m.target || m.data?.expected_item || m.name || '';
                    const loc = m.location || m.data?.subject || '';
                    if (target && loc) {
                        absenceList.push(`${target} in ${loc}`);
                    }
                    else if (target) {
                        absenceList.push(String(target));
                    }
                    else if (m.text) {
                        absenceList.push(String(m.text));
                    }
                }
            }
        }
        const discovered = Array.from(discoveredSet).filter(Boolean);
        const actionHistory = (VW?.events?.getCharacterState?.(charName)?.actionHistory || [])
            .filter((entry) => entry && typeof entry.action === 'string' && entry.action.trim() && entry.result);
        if (discovered.length === 0 && absenceList.length === 0 && actionHistory.length === 0)
            return '';
        const lines = [];
        if (discovered.length > 0 || absenceList.length > 0) {
            lines.push('=== ALREADY KNOWN ===');
            if (discovered.length > 0) {
                lines.push(`You have already examined or taken: ${discovered.join(', ')}.`);
            }
            if (absenceList.length > 0) {
                lines.push(`You already confirmed absent or empty: ${absenceList.join(', ')}.`);
            }
            lines.push('');
        }
        // Count repeated verb+target combos from the live action history.
        const counts = new Map();
        const normalizeTarget = (target) => String(target || '').toLowerCase().replace(/^the\s+/, '').replace(/[_\s]+/g, ' ').trim();
        for (const entry of actionHistory) {
            const words = String(entry.action).trim().split(/\s+/);
            const verb = (words.shift() || '').toLowerCase();
            if (words.length === 0 || !verb)
                continue;
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
            const pastTense = { examine: 'examined', read: 'read', search: 'searched', look: 'looked at', take: 'taken', use: 'used', use_on: 'used', open: 'opened', close: 'closed', wear: 'worn' };
            const pastTenseText = pastTense[verb] || (verb + 'd');
            const nudge = verb === 'examine' || verb === 'read' || verb === 'search' || verb === 'look'
                ? ' Stop examining  -  actually take, wear, or use the things here.'
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
     * engine tunable server-side is NOT applied here  -  we scale client-side so
     * one build never stacks more than a whisper of affect.
     */
    const _respikeTickGuard = {};
    async function _respikeFromMemories(charName, topMemories) {
        const raw = worldState.data?.players?.[charName];
        if (!raw)
            return;
        const now = Date.now();
        if (now - (_respikeTickGuard[charName] || 0) < 5000)
            return;
        // Collect every attached emotion (plural memory_emotions list, or the
        // single legacy emotion field), so all of them can re-feel, not just the
        // strongest.
        const emotions = [];
        for (const entry of topMemories) {
            const list = Array.isArray(entry.memory_emotions) && entry.memory_emotions.length
                ? entry.memory_emotions
                : (entry.emotion ? [entry.emotion] : []);
            for (const e of list) {
                if (e && e.label)
                    emotions.push(e);
            }
        }
        if (emotions.length === 0)
            return;
        // Resolve each label to an affect dimension (semantic embedding fallback
        // for novel labels; keyword otherwise) and accumulate dimension deltas.
        const mapped = {};
        const scale = 1.7;
        const emotionMapper = window.EmotionMapper;
        for (const e of emotions) {
            let dim = null;
            if (emotionMapper) {
                const r = await emotionMapper.resolve(e.label);
                if (r && r.dimension)
                    dim = r.dimension;
            }
            else if (typeof e.label === 'string') {
                dim = e.label;
            }
            if (!dim)
                continue;
            const intensity = Math.max(1, Math.min(10, Number(e.intensity) || 5));
            mapped[dim] = (mapped[dim] || 0) + intensity * scale;
        }
        if (Object.keys(mapped).length === 0)
            return;
        _respikeTickGuard[charName] = now;
        // N6: send the triggering memory as `reason`  -  the backend writes
        // "Remembered: 'X'  -  it made me feel this way toward Y." instead of
        // a contentless placeholder. Full text; no truncation.
        const firstWithEmotion = topMemories.find((m) => {
            const list = Array.isArray(m.memory_emotions) && m.memory_emotions.length
                ? m.memory_emotions
                : (m.emotion ? [m.emotion] : []);
            return list.length > 0;
        });
        const reason = firstWithEmotion
            ? String(firstWithEmotion.text || '').replace(/^\[[^\]]*\]\s*/, '').trim()
            : '';
        ApiClient.mapPlayerEmotions(charName, reason ? { mapped, reason } : { mapped }).catch(() => { });
    }
    /**
     * Build memory context for a character  -  retrieves relevant memories,
     * scores them by relevance, and builds investigation notes.
     * @param {string} charName - Character name
     * @param {Object} [opts] - Options: `report` streams turn-only recall
     *   feedback; `preview` (Agent Lens) skips the embedding server and all
     *   side effects (`_respikeFromMemories`, semantic recall)  -  a preview must
     *   never mutate the character or hammer the embedding API.
     * @returns {Promise<string>} Formatted memory context string or empty string
     */
    async function buildMemoryContext(charName, opts = {}) {
        if (!charName)
            return '';
        const preview = !!opts.preview;
        const player = worldState.data?.players?.[charName];
        const currentArea = opts.area || player?.current_area;
        const parts = [];
        // 1. Spatial context from backend (KNOWN ROUTES FROM HERE)
        try {
            const data = await ApiClient.getPlayerSpatialMemories(charName);
            if (data?.spatial)
                parts.push(data.spatial);
        }
        catch (e) {
            // Spatial context is best-effort - ignore failures
        }
        // 1b. "What I've already done" - repeat-loop guard. Fed from the
        // observation memories (kind === 'item') + the live browser actionHistory.
        const alreadyKnown = buildAlreadyKnownContext(charName);
        if (alreadyKnown)
            parts.push(alreadyKnown);
        // 2. Resolve true area node ID
        function resolveAreaId(areaName) {
            if (!areaName)
                return '';
            const nodes = worldState.graph?.nodes || {};
            for (const [nodeId, node] of Object.entries(nodes)) {
                if (node.type === 'area' && (node.name === areaName || nodeId === areaName || (node.name && node.name.toLowerCase() === areaName.toLowerCase()))) {
                    return nodeId;
                }
            }
            return `area_${areaName.toLowerCase().replace(/\s+/g, '_')}`;
        }
        const currentAreaId = resolveAreaId(currentArea || '');
        // 3. Multi-facet perceptual cues
        const characterState = VW?.events?.getCharacterState?.(charName);
        const lastThought = (characterState?.lastThought || '');
        const heardLines = (player?.recent_hearing || [])
            .filter((h) => h.type !== 'sound_source' && h.speaker !== charName && h.text)
            .slice(-2)
            .map((h) => String(h.text).trim()).filter(Boolean);
        const dialogueLines = [];
        if (opts.stimulus) {
            dialogueLines.push(String(opts.stimulus).trim());
        }
        for (const line of heardLines) {
            dialogueLines.push(line);
        }
        const sceneActors = [];
        const allPlayers = worldState.data?.players || {};
        for (const [pname, pdata] of Object.entries(allPlayers)) {
            if (pname !== charName && pdata?.current_area && currentArea && pdata.current_area.toLowerCase() === currentArea.toLowerCase()) {
                sceneActors.push(pname);
            }
        }
        const sceneItems = [];
        if (currentArea) {
            const items = (typeof worldState.getItemsInArea === 'function') ? (worldState.getItemsInArea(currentArea) || []) : [];
            for (const it of items) {
                const iname = typeof it === 'string' ? it : (it.name || '');
                if (iname)
                    sceneItems.push(String(iname));
            }
        }
        const inventoryItems = [];
        for (const it of (player?.inventory || [])) {
            const iname = typeof it === 'string' ? it : (it.name || '');
            if (iname)
                inventoryItems.push(String(iname));
        }
        const needs = [];
        const vitals = player?.vitals || {};
        if ((Number(vitals.Hunger) || 0) > 50)
            needs.push('need:food');
        if ((Number(vitals.Thirst) || 0) > 50)
            needs.push('need:drink');
        if ((Number(vitals.Energy) || 100) < 30 || (Number(vitals.Exhaustion) || 0) > 50)
            needs.push('need:rest');
        if (opts.needStimulus) {
            const n = String(opts.needStimulus).trim();
            if (n && !needs.includes(n))
                needs.push(n.startsWith('need:') ? n : `need:${n}`);
        }
        const currentEmotion = player?.emotion?.label || player?.current_emotion || '';
        const cues = {
            actors: sceneActors,
            items: sceneItems,
            inventory: inventoryItems,
            dialogue: dialogueLines,
            needs: needs,
            emotion: currentEmotion,
            area_id: currentAreaId
        };
        const queryParts = [currentArea || '', lastThought, ...dialogueLines];
        const query = queryParts.join(' ').trim() || (currentArea || '');
        const queryWords = new Set(query.toLowerCase().split(/\s+/).filter(Boolean));
        // 4. Collect and score memories from both sources
        const MEM_ICONS = { observation: '👁️', discovery: '💡', conversation: '💬', item: '📦', combat: '⚔️', exploration: '🗺️', failure: '⚠️', success: '✅', reflection: '🔄', action: '▶️', speech: '💬', thought: '🤔', reaction: '💭', location: '📍' };
        const memIcon = (memoryType) => MEM_ICONS[String(memoryType)] || '📝';
        // Helper: infer type from text for old-format memories
        const inferIcon = (textValue) => {
            const lowerText = String(textValue || '').toLowerCase();
            if (lowerText.startsWith('[') && lowerText.includes(']'))
                return lowerText.substring(1, lowerText.indexOf(']')).trim();
            if (lowerText.startsWith('💬') || lowerText.includes('said:') || lowerText.includes('says:'))
                return 'speech';
            if (lowerText.startsWith('💭') || lowerText.includes('thought'))
                return 'thought';
            if (lowerText.startsWith('▶️') || lowerText.startsWith('⚙️'))
                return 'action';
            if (lowerText.includes('attack') || lowerText.includes('damage') || lowerText.includes('killed'))
                return 'combat';
            return '📝';
        };
        let scored = [];
        const strategy = opts.strategy || 'associative';
        let openQuestions = [];
        let retrievalExplanation = null;
        // Score memories from the unified backend store. `reinforce: !preview`
        // (task-686): retrieval reinforces what it recalls, but a preview must
        // never mutate the character.
        try {
            const data = await ApiClient.retrievePlayerMemories(charName, {
                strategy,
                query,
                cues,
                max_results: 10,
                entity_boost: true,
                reinforce: !preview,
                current_area_id: currentAreaId,
                min_score: 1.0,
                explain: true
            });
            retrievalExplanation = data?.cues_extracted || null;
            if (Array.isArray(data?.questions)) {
                openQuestions = data.questions;
            }
            else if (Array.isArray(data?.open_questions)) {
                openQuestions = data.open_questions;
            }
            for (const mem of (data?.memories || [])) {
                const memText = String((typeof mem === 'object' && mem?.text) || '').trim();
                if (!memText)
                    continue;
                const backendScore = typeof mem.score === 'number' ? mem.score : null;
                const icon = memIcon(mem.type);
                scored.push({
                    text: `[${events.tickToRelative(mem.tick)}] ${icon} ${memText}`,
                    score: backendScore !== null ? backendScore : 1.0,
                    tick: mem.tick,
                    emotion: mem.emotion || null,
                    source: 'retrieved',
                    category: mem.category,
                    type: mem.type,
                    confidence: typeof mem.confidence === 'number' ? mem.confidence : undefined,
                    contradicts: Array.isArray(mem.contradicts) ? mem.contradicts : [],
                    details: mem.details || null,
                    facets_hit: mem.facets_hit || [],
                    _provenance: mem._provenance || mem.provenance || null,
                    provenance: mem._provenance || mem.provenance || null,
                    primary_signal: mem.primary_signal || mem._provenance?.primary_signal || null,
                    percent_match: mem.percent_match || mem._provenance?.percent_match || null,
                });
            }
        }
        catch (e) {
            // Retrieval is best-effort - fall through
        }
        const rawMemories = player?.memories || [];
        if (strategy === 'legacy') {
            for (const raw of rawMemories) {
                const textContent = typeof raw === 'string' ? raw : raw.text || '';
                const tickValue = typeof raw === 'object' ? raw.tick || 0 : 0;
                if (!textContent)
                    continue;
                const textLower = textContent.toLowerCase();
                let overlap = 0;
                for (const word of queryWords) {
                    if (textLower.includes(word))
                        overlap++;
                }
                const keywordScore = queryWords.size > 0 ? overlap / queryWords.size : 0;
                const icon = memIcon(inferIcon(textContent));
                const STOPWORDS = new Set(['a', 'an', 'the', 'in', 'on', 'of', 'to', 'for', 'and', 'or', 'but', 'if', 'so', 'then', 'there', 'their', 'them', 'they', 'this', 'that', 'with', 'from', 'just', 'now', 'really', 'about', 'when', 'what', 'where', 'how', 'why', 'is', 'are', 'was', 'were', 'be', 'been', 'it', 'its', 'at', 'as', 'by', 'my', 'me', 'i', 'we', 'you', 'your', 'not', 'no', 'yes', 'oh', 'well', 'much', 'nice', 'very', 'too', 'will', 'would', 'can', 'could', 'shall', 'should', 'am', 'get', 'got', 'go', 'one', 'two', 'three', 'after', 'before']);
                const matchedWords = [];
                for (const word of queryWords) {
                    if (STOPWORDS.has(word))
                        continue;
                    if (textLower.includes(word))
                        matchedWords.push(word);
                }
                if (keywordScore > 0 || scored.length < 8) {
                    scored.push({ text: `[${events.tickToRelative(tickValue)}] ${icon} ${textContent}`, score: keywordScore, tick: tickValue, emotion: (typeof raw === 'object' && raw.emotion) || null, source: 'keyword', kb: keywordScore, matchedWords, memTags: ((typeof raw === 'object' && Array.isArray(raw.tags)) ? raw.tags : []) });
                }
            }
            if (!preview && window.EmbeddingClient?.configured()) {
                try {
                    const queryVector = await EmbeddingClient.embed(query);
                    if (queryVector) {
                        const data = await ApiClient.searchMemoryEmbeddings({ character: charName, vector: queryVector, k: 5 });
                        const hitIds = [];
                        for (const hit of (data?.results || [])) {
                            if (hit.score < 0.35)
                                continue;
                            const memEntry = rawMemories.find((m) => (typeof m === 'object' && m.id === hit.memory_id));
                            const textContent = typeof memEntry === 'object' ? (memEntry?.text || '') : '';
                            if (!textContent)
                                continue;
                            hitIds.push(String(hit.memory_id));
                            const tickValue = memEntry.tick || 0;
                            const icon = memIcon(memEntry.type);
                            scored.push({ text: `[${events.tickToRelative(tickValue)}] ${icon} ${textContent}`, score: 2.0 * hit.score, tick: tickValue, emotion: memEntry.emotion || null, source: 'vector', kb: hit.score, category: memEntry.category, type: memEntry.type, confidence: typeof memEntry.confidence === 'number' ? memEntry.confidence : undefined, contradicts: Array.isArray(memEntry.contradicts) ? memEntry.contradicts : [] });
                        }
                        if (hitIds.length > 0) {
                            ApiClient.reinforcePlayerMemories(charName, { ids: hitIds, tick: worldState?.data?.time_ticks || 0 }).catch(() => { });
                        }
                    }
                }
                catch (e) {
                    // Semantic recall is best-effort
                }
            }
        }
        // Dedup by normalized text BEFORE picking the top-k
        const seenText = new Set();
        const deduped = [];
        for (const entry of scored) {
            const bare = String(entry.text || '')
                .replace(/^\s*\[[^\]]*\]\s*/, '')
                .replace(/^[^A-Za-z0-9]+\s*/, '');
            const key = bare.replace(/\s+/g, ' ').toLowerCase();
            if (seenText.has(key))
                continue;
            seenText.add(key);
            deduped.push(entry);
        }
        scored = deduped;
        // Sort by score desc, then recency
        scored.sort((entryA, entryB) => entryB.score - entryA.score || (entryB.tick || 0) - (entryA.tick || 0));
        const MAX_RECALL = 10;
        const MIN_RECALL_SCORE = 0.3;
        // Zero-padding eliminated for Associative 3.0:
        // Legacy keeps top 3 always (i < 3). Associative ONLY keeps score >= 1.0.
        const topMemories = scored.slice(0, MAX_RECALL)
            .filter((m, i) => (strategy === 'legacy' ? (i < 3 || (m.score || 0) >= MIN_RECALL_SCORE) : (m.score || 0) >= 1.0));
        topMemories.sort((a, b) => (b.tick || 0) - (a.tick || 0));
        // Feed recall pipe for UI inspection
        try {
            window._lastRecallStats = {
                at: Date.now(),
                strategy,
                count: topMemories.length,
                questionsCount: openQuestions.length,
                semantic: topMemories.filter((m) => m.source === 'vector').length,
                query: String(query || '').slice(0, 120),
                cues,
                explanation: retrievalExplanation,
                memories: topMemories.map((m) => ({
                    text: String(m.text || '').replace(/^\[[^\]]*\]\s*/, ''),
                    source: m.source,
                    score: m.score || 0,
                    matchedWords: m.matchedWords || [],
                    memTags: m.memTags || [],
                    kb: m.kb || 0,
                    facets_hit: m.facets_hit || [],
                    details: m.details || null,
                    _provenance: m._provenance || null,
                    provenance: m.provenance || m._provenance || null,
                    primary_signal: m.primary_signal || m._provenance?.primary_signal || null,
                    percent_match: m.percent_match || m._provenance?.percent_match || null,
                })),
                questions: openQuestions
            };
        }
        catch (e) { /* feedback is best-effort */ }
        // Turn-only recall feedback (opts.report)
        try {
            if (opts.report && typeof events?.log === 'function' && topMemories.length) {
                const lines = topMemories.map((m) => {
                    let why;
                    const prov = m._provenance || m.provenance;
                    if (prov && prov.primary_signal) {
                        const sigIcons = {
                            spatial: '📍 spatial',
                            social: '👥 social',
                            conversational: '💬 dialogue',
                            emotional: '💭 mood',
                            need: '🥩 need',
                            recency: '⏱️ recency',
                            semantic: '🧠 semantic',
                        };
                        const sigLabel = sigIcons[prov.primary_signal] || prov.primary_signal;
                        const pct = prov.percent_match ? ` [Match: ${prov.percent_match}%]` : '';
                        why = `${sigLabel}${pct} (score ${Math.round((m.score || 0) * 100) / 100})`;
                    }
                    else if (m.source === 'keyword') {
                        const words = (m.matchedWords?.length ? m.matchedWords.join(', ') : 'phrase');
                        const tags = (m.memTags?.length ? m.memTags.join(', ') : '');
                        why = `keyword (${words})${tags ? ` · tags ${tags}` : ''}`;
                    }
                    else if (m.source === 'vector') {
                        why = `semantic ${Math.round((m.kb || 0) * 100) / 100}`;
                    }
                    else {
                        const score = (m.score || 0) > 1 ? ` (score ${Math.round(m.score * 100) / 100})` : '';
                        why = `associative${score}`;
                    }
                    const short = String(m.text || '').replace(/^\[[^\]]*\]\s*/, '');
                    return `  • ${short} - ${why}`;
                });
                const n = topMemories.length;
                const kw = topMemories.filter((m) => m.source === 'keyword').length;
                const vec = topMemories.filter((m) => m.source === 'vector').length;
                const rec = n - kw - vec;
                const queryShort = String(query || '').replace(/\s+/g, ' ');
                events.log(`🧠 recalled ${n} memor${n === 1 ? 'y' : 'ies'} · query "${queryShort}" (${kw} keyword · ${vec} semantic · ${rec} associative): \n${lines.join('\n')}`, 'system-msg', null, charName);
            }
        }
        catch (e) { /* feedback is best-effort */ }
        if (topMemories.length > 0) {
            parts.push('');
            parts.push('=== I REMEMBER ===');
            const categoryOf = (m) => {
                const cat = m.category ? String(m.category) : '';
                if (cat)
                    return cat;
                if (String(m.type || '') === 'reflection')
                    return 'belief';
                const tags = (m.memTags || []).map((t) => String(t).toLowerCase());
                if (tags.some((t) => t.startsWith('rel:')))
                    return 'social';
                return 'episodic';
            };
            const certaintySuffix = (m) => {
                const flags = [];
                if (Array.isArray(m.contradicts) && m.contradicts.length > 0) {
                    flags.push('⚡ this conflicts with another memory');
                }
                if (typeof m.confidence === 'number' && m.confidence < 0.5) {
                    flags.push('you are not sure of this');
                }
                return flags.length > 0 ? ` (${flags.join('; ')})` : '';
            };
            const sections = [
                ['EVENTS - what happened', []],
                ['WHAT I BELIEVE', []],
                ['HOW I SEE PEOPLE', []],
                ['WHAT I EXPECT', []]
            ];
            for (const memoryEntry of topMemories) {
                const cat = categoryOf(memoryEntry);
                if (cat === 'question') {
                    const text = String(memoryEntry.text || '').replace(/^\s*\[[^\]]*\]\s*/, '').replace(/^[^A-Za-z0-9]+\s*/, '');
                    if (!openQuestions.some(q => q.question === text)) {
                        openQuestions.push({ question: text });
                    }
                }
                else if (cat === 'belief' || cat === 'semantic')
                    sections[1][1].push(memoryEntry);
                else if (cat === 'social')
                    sections[2][1].push(memoryEntry);
                else if (cat === 'procedural')
                    sections[3][1].push(memoryEntry);
                else
                    sections[0][1].push(memoryEntry);
            }
            const hasModel = sections.slice(1).some(([, list]) => list.length > 0);
            for (const [header, list] of sections) {
                if (list.length === 0)
                    continue;
                if (hasModel)
                    parts.push(header);
                for (const memoryEntry of list) {
                    parts.push(memoryEntry.text + certaintySuffix(memoryEntry));
                }
            }
            if (!preview)
                _respikeFromMemories(charName, topMemories);
        }
        else {
            parts.push('');
            parts.push('=== I REMEMBER ===');
            parts.push("You don't remember anything relevant right now.");
        }
        if (openQuestions.length > 0) {
            parts.push('');
            parts.push('=== OPEN QUESTIONS / SUSPICIONS ===');
            for (const q of openQuestions.slice(0, 2)) {
                const hyp = q.hypothesis ? ` (Hypothesis: ${q.hypothesis})` : '';
                parts.push(`- ${q.question}${hyp}`);
            }
        }
        // ── Parse action memories into investigation notes ──
        const actionInfo = [];
        const actionCounts = {};
        for (const raw of rawMemories) {
            const textContent = typeof raw === 'string' ? raw : raw.text || '';
            if (!textContent)
                continue;
            // Try arrow first, then colon for backward compatibility
            let separatorIdx = textContent.indexOf(' → ');
            let separatorLen = 3;
            if (separatorIdx === -1) {
                separatorIdx = textContent.indexOf(':');
                separatorLen = 1;
            }
            if (separatorIdx === -1)
                continue;
            // Strip leading emoji/icon from actionPart
            const actionPart = textContent.substring(0, separatorIdx).replace(/^[^\w]+/, '').trim().toLowerCase();
            const resultText = textContent.substring(separatorIdx + separatorLen).trim();
            if (!resultText)
                continue;
            const knownVerbs = ['examine', 'use', 'take', 'open', 'close', 'read', 'drink', 'eat', 'light', 'go', 'approach'];
            const verb = actionPart.split(/\s+/)[0];
            const target = actionPart.substring(verb.length).trim();
            if (!knownVerbs.includes(verb))
                continue;
            const key = actionPart.replace(/\s+/g, '_');
            actionCounts[key] = (actionCounts[key] || 0) + 1;
            const actionCount = actionCounts[key];
            const failed = /can'?t|cannot|don'?t have|doesn'?t have|no purchase|purely decorative|nothing happens|isn'?t|not a|can'?t find|full|doesn'?t budge|part of the scenery|not valid|you look for|don'?t see it/.test(resultText.toLowerCase());
            let fact = resultText.replace(/^(you\s+)?(use[d]?|examine[d]?|open[ed]?|close[d]?|rea[d]?|drink?|eat[en]?|light[ed]?|t[ao]ke?)\s+/i, '');
            fact = fact.replace(/^you\s+/, '');
            const dotIdx = fact.indexOf('.');
            if (dotIdx > 15)
                fact = fact.substring(0, dotIdx + 1);
            else if (dotIdx === -1 && fact.length > 100)
                fact = fact.substring(0, 100) + '...';
            if (fact.trim()) {
                actionInfo.push({ verb, target, fact: fact.trim(), count: actionCount, key, failed });
            }
        }
        // ── Build Investigation Notes ──
        if (actionInfo.length > 0) {
            const findings = [];
            const seenTargets = new Set();
            // Examine findings grouped by unique target
            for (const actionItem of actionInfo) {
                if (actionItem.verb !== 'examine')
                    continue;
                if (seenTargets.has(actionItem.target))
                    continue;
                seenTargets.add(actionItem.target);
                const repeatCount = actionItem.count;
                const repeatNote = repeatCount >= 2 ? ` (examined ${repeatCount}x)` : '';
                findings.push(`- ${actionItem.target}: ${actionItem.fact}${repeatNote}`);
            }
            // Way/movement findings
            for (const actionItem of actionInfo) {
                if (actionItem.verb === 'go' || actionItem.verb === 'open' || actionItem.verb === 'close') {
                    if (actionItem.fact && !findings.some((finding) => finding.includes(actionItem.target))) {
                        findings.push(`- ${actionItem.target}: ${actionItem.fact}`);
                    }
                }
            }
            // Repeat warnings  -  any verb, and failure-aware so impossible
            // attempts (e.g. "use create flame on dry leaves") get flagged
            // instead of re-attempted forever.
            const repeatedFails = actionInfo.filter((actionItem) => actionItem.failed && actionItem.count >= 3);
            if (repeatedFails.length > 0) {
                const r = repeatedFails[0];
                findings.push(`⚠️ You've tried "${r.key.replace(/_/g, ' ')}" ${r.count} times and it failed each time. Pick a different approach.`);
            }
            else {
                const repeats = actionInfo.filter((actionItem) => actionItem.verb === 'examine' && actionItem.count >= 3);
                if (repeats.length > 0) {
                    findings.push(`⚠️ You've examined "${repeats[0].target}" ${repeats[0].count} times with no new information. Move on.`);
                }
            }
            // What still needs doing
            const doneKeys = new Set(actionInfo.map((actionItem) => actionItem.key));
            const playerState = worldState.data?.players?.[charName];
            const curRoom = playerState?.current_area;
            const areaData = curRoom ? worldState.areas?.[curRoom] : null;
            const areaItems = curRoom ? worldState.getItemsInArea(curRoom) : [];
            const areaExits = areaData?.exits || {};
            const suggestions = [];
            const goTargets = actionInfo.filter((actionItem) => actionItem.verb === 'go').map((actionItem) => actionItem.target.toLowerCase().trim());
            const examineTargets = actionInfo.filter((actionItem) => actionItem.verb === 'examine').map((actionItem) => actionItem.target.toLowerCase().trim());
            for (const [dir, exitData] of Object.entries(areaExits)) {
                if (exitData.hidden)
                    continue;
                const exitName = dir.replace(/_/g, ' ').toLowerCase();
                const alreadyMoved = goTargets.some((goTarget) => goTarget === exitName || goTarget.includes(exitName) || exitName.includes(goTarget));
                const alreadyExamined = examineTargets.some((examineTarget) => examineTarget === exitName || examineTarget.includes(exitName) || exitName.includes(examineTarget));
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
                parts.push(...suggestions.slice(0, 5).map((suggestion) => `  ❓ ${suggestion}`));
                parts.push('');
            }
            parts.push('Decision: Pick ONE from the list above and do it now.');
            parts.push('No more examining the same items  -  take action.');
        }
        return parts.length > 0 ? '\n' + parts.join('\n') : '';
    }
    Object.assign(window.PromptBuilder, {
        buildMemoryContext,
        buildAlreadyKnownContext
    });
})();
