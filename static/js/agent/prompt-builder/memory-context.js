/**
 * prompt-builder/memory-context.js — Memory retrieval + investigation notes.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). This is the one
 * part of the prompt builder that does async fetches and its own local
 * scoring/parsing pipeline (the investigation-notes logic is a mini-subsystem),
 * so it earns a standalone file. Exports merge into window.PromptBuilder.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 */

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
    function buildAlreadyKnownContext(charName) {
        if (!charName) return '';
        const player = worldState.data?.players?.[charName];
        const discovered = Array.isArray(player?.discovered_items)
            ? player.discovered_items.filter(Boolean)
            : [];
        const actionHistory = (VW?.events?.getCharacterState?.(charName)?.actionHistory || [])
            .filter(entry => entry && typeof entry.action === 'string' && entry.action.trim() && entry.result);

        if (discovered.length === 0 && actionHistory.length === 0) return '';

        const lines = [];

        if (discovered.length > 0) {
            lines.push('=== ALREADY KNOWN ===');
            lines.push(`You have already examined or taken: ${discovered.join(', ')}.`);
            lines.push('');
        }

        // Count repeated verb+target combos from the live action history.
        const counts = new Map();
        const normalizeTarget = (target) => String(target || '').toLowerCase().replace(/^the\s+/, '').replace(/[_\s]+/g, ' ').trim();
        for (const entry of actionHistory) {
            const words = entry.action.trim().split(/\s+/);
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
            const pastTense = { examine: 'examined', read: 'read', search: 'searched', look: 'looked at', take: 'taken', use: 'used', use_on: 'used', open: 'opened', close: 'closed', wear: 'worn' }[verb] || (verb + 'd');
            const nudge = verb === 'examine' || verb === 'read' || verb === 'search' || verb === 'look'
                ? ' Stop examining — actually take, wear, or use the things here.'
                : ' Pick a different action.';
            lines.push(`⚠️ You have ${pastTense} "${target}" ${count} times now and nothing changed.${nudge}`);
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
    const _respikeTickGuard = {};
    function _respikeFromMemories(charName, topMemories) {
        const raw = worldState.data?.players?.[charName];
        if (!raw) return;
        const now = Date.now();
        if (now - (_respikeTickGuard[charName] || 0) < 5000) return;
        let strongest = null;
        for (const entry of topMemories) {
            const emo = entry.emotion;
            if (emo?.label && (!strongest || (emo.intensity || 0) > strongest.intensity)) {
                strongest = emo;
            }
        }
        if (!strongest) return;
        _respikeTickGuard[charName] = now;
        fetch(`/api/players/${encodeURIComponent(charName)}/emotions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                emotion: strongest.label,
                delta: Math.max(1, Math.min(10, strongest.intensity || 5)) * 2.5
            })
        }).catch(() => {});
    }

    /**
     * Build memory context for a character — retrieves relevant memories,
     * scores them by relevance, and builds investigation notes.
     * @param {string} charName - Character name
     * @returns {Promise<string>} Formatted memory context string or empty string
     */
    async function buildMemoryContext(charName) {
        if (!charName) return '';
        const player = worldState.data?.players?.[charName];
        const currentArea = player?.current_area;
        const parts = [];

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

        // 2. Build query from current area + last thought
        const characterState = VW?.events?.getCharacterState?.(charName);
        const lastThought = (characterState?.lastThought || '');
        const query = `${currentArea || ''} ${lastThought}`.trim() || currentArea || '';
        const queryWords = new Set(query.toLowerCase().split(/\s+/).filter(Boolean));

        // 3. Collect and score memories from both sources
        const memIcon = (memoryType) => ({observation:'👁️',discovery:'💡',conversation:'💬',item:'📦',combat:'⚔️',exploration:'🗺️',failure:'⚠️',success:'✅',reflection:'🔄',action:'▶️',speech:'💬',thought:'🤔',reaction:'💭',location:'📍'}[memoryType]||'📝');

        // Helper: infer type from text for old-format memories
        const inferIcon = (textValue) => {
            const lowerText = textValue?.toLowerCase() || '';
            if (lowerText.startsWith('[') && lowerText.includes(']')) return lowerText.substring(1, lowerText.indexOf(']')).trim();
            if (lowerText.startsWith('💬') || lowerText.includes('said:') || lowerText.includes('says:')) return 'speech';
            if (lowerText.startsWith('💭') || lowerText.includes('thought')) return 'thought';
            if (lowerText.startsWith('▶️') || lowerText.startsWith('⚙️')) return 'action';
            if (lowerText.includes('attack') || lowerText.includes('damage') || lowerText.includes('killed')) return 'combat';
            return '📝';
        };

        const scored = [];

        // Score memories from the unified backend store
        try {
            const resp = await fetch(`/api/players/${encodeURIComponent(charName)}/memories/retrieve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    max_results: 10,
                    entity_boost: true,
                    current_area_id: currentArea ? `area_${currentArea.toLowerCase().replace(/\s+/g, '_')}` : ''
                })
            });
            if (resp.ok) {
                const data = await resp.json();
                for (const memoryEntry of (data.memories || [])) {
                    const icon = memIcon(memoryEntry.type);
                    scored.push({ text: `[${events.tickToRelative(memoryEntry.tick)}] ${icon} ${memoryEntry.text}`, score: 1.0, tick: memoryEntry.tick, emotion: memoryEntry.emotion || null });
                }
            }
        } catch (e) {
            // Retrieval is best-effort — fall through to player.memories scoring
        }

        // Score player.memories[] entries
        const rawMemories = player?.memories || [];
        for (const raw of rawMemories) {
            const textContent = typeof raw === 'string' ? raw : raw.text || '';
            const tickValue = typeof raw === 'object' ? raw.tick || 0 : 0;
            if (!textContent) continue;
            const textLower = textContent.toLowerCase();
            let overlap = 0;
            for (const word of queryWords) {
                if (textLower.includes(word)) overlap++;
            }
            const keywordScore = queryWords.size > 0 ? overlap / queryWords.size : 0;
            const icon = memIcon(inferIcon(textContent));
            // Include if it has keyword overlap OR we haven't collected enough candidates yet
            if (keywordScore > 0 || scored.length < 8) {
                scored.push({ text: `[${events.tickToRelative(tickValue)}] ${icon} ${textContent}`, score: keywordScore, tick: tickValue, emotion: (typeof raw === 'object' && raw?.emotion) || null });
            }
        }

        // Semantic recall (task-91): embed the query, ask the backend vector
        // store for this character's top-k memories, and merge them into the
        // candidate pool scored by cosine similarity. Silent no-op when the
        // embedding settings are off or the call fails.
        if (window.EmbeddingClient?.configured()) {
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
                        for (const hit of (data.results || [])) {
                            if (hit.score < 0.35) continue;
                            const memEntry = rawMemories.find(m => (typeof m === 'object' && m.id === hit.memory_id));
                            const textContent = typeof memEntry === 'object' ? (memEntry?.text || '') : '';
                            if (!textContent) continue;
                            const tickValue = memEntry.tick || 0;
                            const icon = memIcon(memEntry.type);
                            scored.push({ text: `[${events.tickToRelative(tickValue)}] ${icon} ${textContent}`, score: 2.0 * hit.score, tick: tickValue, emotion: memEntry.emotion || null });
                        }
                    }
                }
            } catch (e) {
                // Semantic recall is best-effort — keyword scoring already ran.
            }
        }

        // Sort by score desc, then recency
        scored.sort((entryA, entryB) => entryB.score - entryA.score || (entryB.tick || 0) - (entryA.tick || 0));
        const topMemories = scored.slice(0, 3);

        if (topMemories.length > 0) {
            parts.push('');
            parts.push('=== I REMEMBER ===');
            for (const memoryEntry of topMemories) {
                parts.push(memoryEntry.text);
            }
            _respikeFromMemories(charName, topMemories);
        } else {
            parts.push('');
            parts.push('=== I REMEMBER ===');
            parts.push("You don't remember anything relevant right now.");
        }

        // ── Parse action memories into investigation notes ──
        const actionInfo = [];
        const actionCounts = {};

        for (const raw of rawMemories) {
            const textContent = typeof raw === 'string' ? raw : raw.text || '';
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

            const knownVerbs = ['examine', 'use', 'take', 'open', 'close', 'read', 'drink', 'eat', 'light', 'go'];
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
            const findings = [];
            const seenTargets = new Set();

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
                    if (actionItem.fact && !findings.some(finding => finding.includes(actionItem.target))) {
                        findings.push(`- ${actionItem.target}: ${actionItem.fact}`);
                    }
                }
            }

            // Repeat warnings — any verb, and failure-aware so impossible
            // attempts (e.g. "use create flame on dry leaves") get flagged
            // instead of re-attempted forever.
            const repeatedFails = actionInfo.filter(actionItem => actionItem.failed && actionItem.count >= 3);
            if (repeatedFails.length > 0) {
                const r = repeatedFails[0];
                findings.push(`⚠️ You've tried "${r.key.replace(/_/g, ' ')}" ${r.count} times and it failed each time. Pick a different approach.`);
            } else {
                const repeats = actionInfo.filter(actionItem => actionItem.verb === 'examine' && actionItem.count >= 3);
                if (repeats.length > 0) {
                    findings.push(`⚠️ You've examined "${repeats[0].target}" ${repeats[0].count} times with no new information. Move on.`);
                }
            }

            // What still needs doing
            const doneKeys = new Set(actionInfo.map(actionItem => actionItem.key));
            const playerState = worldState.data?.players?.[charName];
            const curRoom = playerState?.current_area;
            const areaData = curRoom ? worldState.areas?.[curRoom] : null;
            const areaItems = curRoom ? worldState.getItemsInArea(curRoom) : [];
            const areaExits = areaData?.exits || {};

            const suggestions = [];
            const goTargets = actionInfo.filter(actionItem => actionItem.verb === 'go').map(actionItem => actionItem.target.toLowerCase().trim());
            const examineTargets = actionInfo.filter(actionItem => actionItem.verb === 'examine').map(actionItem => actionItem.target.toLowerCase().trim());
            const takeTargets = actionInfo.filter(actionItem => actionItem.verb === 'take').map(actionItem => actionItem.target.toLowerCase().trim());
            for (const [dir, exitData] of Object.entries(areaExits)) {
                if (exitData.hidden) continue;
                const exitName = dir.replace(/_/g, ' ').toLowerCase();
                const alreadyMoved = goTargets.some(goTarget => goTarget === exitName || goTarget.includes(exitName) || exitName.includes(goTarget));
                const alreadyExamined = examineTargets.some(examineTarget => examineTarget === exitName || examineTarget.includes(exitName) || exitName.includes(examineTarget));
                if (!alreadyMoved && !alreadyExamined) {
                    suggestions.push(`Go through "${dir}"`);
                }
            }
            for (const item of areaItems) {
                const itemName = (typeof item === 'string' ? item : item.name || '').toLowerCase();
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
                parts.push(...suggestions.slice(0, 5).map(suggestion => `  ❓ ${suggestion}`));
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
