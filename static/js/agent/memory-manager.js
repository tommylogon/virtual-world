/**
 * memory-manager.js — Memory storage and reflection
 *
 * Handles all memory-related operations for character agents, backed by
 * the unified backend `Player.memories[]` store:
 *   - `storeMemory()` — POST a memory to the character's backend memories
 *   - `reflect()` — LLM-driven summarization into reflection memories
 *
 * Usage: AgentMemory.reflect(charName)
 *        AgentMemory.storeMemory(charName, text, importance, type, tick, entity_ids)
 *
 * Load this AFTER agent-engine.js in index.html (references VW.agent and globals).
 */

window.AgentMemory = (() => {
    'use strict';

    /**
     * Perform memory reflection for a character.
     *
     * Queries high-importance memories (≥6) from the unified backend store,
     * asks the LLM to summarize them into 1-2 insight statements, and stores
     * those insights as new 'reflection' memories via the reflect endpoint.
     *
     * @param {string} charName - Character name to reflect for
     */
    async function reflect(charName) {
        if (!charName) return;
        try {
            const allMemories = await fetch(`/api/players/${encodeURIComponent(charName)}/memories`, {
                headers: { 'Accept': 'application/json' }
            }).then(resp => resp.json()).catch(() => ({ memories: [] }));
            const memories = allMemories.memories || [];
            const importantMemories = memories.filter(m => (m.importance || 0) >= 6).slice(0, 10);
            if (importantMemories.length < 3) return;
            const memoryText = importantMemories.map(m => `[${events.tickToRelative(m.tick)}] ${m.text}`).join('\n');
            const prompt = `Summarize these memories into 1-2 insights:\n${memoryText}\n\nRespond ONLY with a JSON object: {"insights": ["insight 1"]}`;
            const response = await llmClient.chat([{ role: 'user', content: prompt }], { temperature: 0.7, max_tokens: 200, streaming: false, label: 'reflect', responseFormat: window.StructuredFormats?.insights });
            if (!response) return;
            let cleaned = response.trim();
            const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
            if (codeBlockMatch) cleaned = codeBlockMatch[1].trim();

            // Safer JSON parsing — LLMs often add text around the array or trailing commas
            let parsed;
            try {
                parsed = JSON.parse(cleaned);
            } catch (e) {
                const arrayMatch = cleaned.match(/\[[\s\S]*\]/);
                if (arrayMatch) {
                    try { parsed = JSON.parse(arrayMatch[0]); }
                    catch (e2) { return; }
                } else {
                    return;
                }
            }

            // Structured output wraps in {"insights":[...]}; the old raw-array
            // contract stays accepted for providers on the plain-prompt path.
            const parsedList = Array.isArray(parsed) ? parsed
                : (parsed && typeof parsed === 'object' && Array.isArray(parsed.insights) ? parsed.insights : null);

            if (Array.isArray(parsedList)) {
                const currentTick = worldState?.data?.time_ticks || 0;
                const insights = parsedList.filter(i => typeof i === 'string' && i.length > 10);
                if (insights.length > 0) {
                    await fetch(`/api/players/${encodeURIComponent(charName)}/memories/reflect`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ insights, tick: currentTick })
                    }).catch(() => {});
                }
                events.log(`🧠 ${charName} reflected on ${importantMemories.length} memories`, 'system-msg');
            }
        } catch (error) {
            // Reflection errors are non-critical — swallow silently
        }
    }

    /**
     * Store a memory entry for a character.
     *
     * POSTs to the unified backend `Player.memories[]` store.
     *
     * @param {string} charName - Character name
     * @param {string} text - Memory text content
     * @param {number} importance - Importance level (1-10, higher = more significant)
     * @param {string} type - Memory type ('thought', 'action', 'speech', 'reflection', 'backstory', etc.)
     * @param {number} [tick=null] - Optional tick this memory occurred. Defaults to the
     *        current world tick. Pass a past tick (or negative value) to seed backstory
     *        memories when a character is first created.
     * @param {string[]} [entity_ids=[]] - Optional graph entity IDs linked to this memory
     */
    /**
     * Sanitize LLM-generated memory tags down to single-word conceptual ones.
     *
     * Memory tags are meant to be categories/themes for later retrieval (fear,
     * trust, amnesia, danger) — NOT specifics. So we drop:
     *   - multi-word / hyphenated tags ("silent-stranger", "sealed-room")
     *   - names of people, items, or areas (real entities the world tracks)
     * Keeps only lowercase single words that aren't an entity name.
     * @param {string[]} tags - Raw tags from the LLM
     * @returns {string[]} Cleaned single-word conceptual tags
     */
    function _sanitizeTags(tags) {
        if (!Array.isArray(tags)) return [];
        // Entity names we never want as memory tags (people, items, areas)
        const entityNames = new Set();
        const g = worldState?.data || {};
        for (const name of Object.keys(g.players || {})) entityNames.add(name.toLowerCase());
        for (const node of Object.values(worldState?.graph?.nodes || {})) {
            if (node?.name) entityNames.add(String(node.name).toLowerCase());
        }
        const singleWord = /^[a-z0-9_]+$/;
        const seen = new Set();
        const out = [];
        for (let t of tags) {
            t = String(t || '').trim().toLowerCase();
            if (!t) continue;
            if (!singleWord.test(t)) continue;              // multi-word / hyphenated → drop
            if (entityNames.has(t)) continue;               // person/item/area name → drop
            if (seen.has(t)) continue;                      // dedupe
            seen.add(t);
            out.push(t);
        }
        return out;
    }

    function storeMemory(charName, text, importance, type, tick = null, entity_ids = [], tags = [], emotion = null, emotions = null) {
        try {
            if (!text) return;
            const memoryTick = (tick !== null && tick !== undefined) ? tick : (worldState.data?.time_ticks || 0);
            const cleanTags = _sanitizeTags(tags);
            const payload = {
                text,
                tick: memoryTick,
                importance: Math.max(1, Math.min(10, importance || 5)),
                type: type || 'observation',
                entity_ids: entity_ids || [],
                source: 'auto',
                tags: cleanTags,
                emotion: (emotion && typeof emotion === 'object') ? { label: emotion.label, intensity: emotion.intensity } : null,
                emotions: (emotions && typeof emotions === 'object') ? emotions : null
            };
            fetch(`/api/players/${encodeURIComponent(charName)}/memories/entry`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }).then(resp => resp.ok ? resp.json() : null).then(data => {
                _embedAndStoreVector(charName, data?.entry?.id, text);
            }).catch(() => {});
            // Register any new single-word tags into the tag library (id-keyed → dedupes)
            if (cleanTags.length > 0) {
                cleanTags.forEach(tagId => _ensureLibraryTag(tagId));
            }
        } catch (error) {
            // Store errors are non-critical
        }
    }

    /**
     * Fire-and-forget: embed a stored memory's text and upsert the vector into
     * the backend store (task-91). Any failure is silent — semantic recall just
     * degrades to keyword-only for that memory.
     */
    function _embedAndStoreVector(charName, memoryId, text) {
        if (!memoryId || !window.EmbeddingClient?.configured()) return;
        EmbeddingClient.embed(text).then(vector => {
            if (!vector) return;
            fetch('/api/memory/embeddings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    items: [{ key: `${charName}::${memoryId}`, vector }],
                    model: config.embedModel,
                    dims: vector.length
                })
            }).catch(() => {});
        }).catch(() => {});
    }

    /**
     * Fire-and-forget register a single-word tag in the library ONLY if it doesn't
     * already exist. The library is id-keyed, but re-posting an existing tag would
     * OVERWRITE a curated entry (description/color/examples) with the generic
     * auto-generated blob — so check the library first and never clobber existing tags.
     */
    const _checkedTagIds = new Set();
    function _ensureLibraryTag(tagId) {
        if (_checkedTagIds.has(tagId)) return;
        _checkedTagIds.add(tagId);
        try {
            fetch("/api/tags/search?q=" + encodeURIComponent(tagId))
                .then(r => r.json())
                .then(tags => {
                    const exists = Array.isArray(tags) && tags.some(t => (t.id || '').toLowerCase() === tagId.toLowerCase());
                    if (exists) return;
                    const tagData = {
                        id: tagId,
                        name: tagId.charAt(0).toUpperCase() + tagId.slice(1),
                        description: "Auto-generated from agent memory",
                        category: "custom",
                        color: "#888888",
                        icon: "🎗️",
                        applies_to: [],
                        examples: []
                    };
                    fetch("/api/library/tags", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(tagData)
                    }).catch(() => {});
                })
                .catch(() => {});
        } catch (error) {
            // Non-critical
        }
    }

    return {
        reflect,
        storeMemory
    };
})();
