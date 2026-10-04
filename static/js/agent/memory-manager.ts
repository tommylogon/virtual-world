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
 *
 * @module agent/memory-manager — the agent memory write path
 * @contributes AgentMemory.storeMemory() + reflect() (LLM summarization into reflection memories)
 * @powers Memory — what characters remember, and when they reflect on it
 * @relates writes the backend Player.memories[]; read back by prompt-builder/memory-context.js
 * @docs docs/virtualWorld/AI & Narration/Memory System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const AgentMemory = (() => {
    'use strict';

    /**
     * Perform memory reflection for a character (task-688).
     *
     * Queries raw-experience memories (importance ≥ 6 or reinforced ≥ 2,
     * reflection_depth 0 only — the client half of the recursion guard),
     * asks the LLM for structured conclusions that change the character
     * (belief + confidence + optional emotional association, behaviour
     * expectation and relationship delta), and POSTs them to the reflect
     * endpoint with the source memory ids so the backend can stamp
     * provenance and enforce the depth guard server-side.
     *
     * @param {string} charName - Character name to reflect for
     */
    async function reflect(charName: string): Promise<void> {
        if (!charName) return;
        try {
            const allMemories = await fetch(`/api/players/${encodeURIComponent(charName)}/memories`, {
                headers: { 'Accept': 'application/json' }
            }).then(resp => resp.json()).catch(() => ({ memories: [] }));
            const memories: MemoryRecord[] = allMemories.memories || [];
            const candidates = memories.filter((m: MemoryRecord) =>
                ((Number(m.importance) || 0) >= 6 || (Number(m.reinforcements) || 0) >= 2)
                && !(Number(m.reflection_depth) >= 1)
            ).slice(0, 10);
            if (candidates.length < 3) return;
            const memoryText = candidates.map((m: MemoryRecord) =>
                `- [memory_id: ${m.id}] [${events.tickToRelative(m.tick)}] ${m.text}`).join('\n');
            const prompt = [
                `You are the memory of the character "${charName}". Below are things they experienced.`,
                'Form 1-3 conclusions that CHANGE how the character sees the world or acts — not a summary of the events.',
                'For each insight provide:',
                '- belief: one first-person sentence the character now holds (e.g. "Anna is probably lying about the cellar.")',
                '- about: names of people/places/things the belief is about (empty array if none)',
                '- confidence: 0-1, how sure the character is (lower it when the memories conflict)',
                '- emotional: optional {label, intensity 1-10} — the feeling attached to this conclusion',
                '- behavior: optional one-sentence change to future behaviour (e.g. "Verify Anna\'s claims independently.")',
                '- relationship: optional {who, dim, delta} — dim is one of trust|fear|attraction|disgust|respect|familiarity, delta -5..+5',
                'Use null for fields that do not apply. Respond ONLY with a JSON object: {"insights": [...]}',
                '',
                'MEMORIES:',
                memoryText
            ].join('\n');
            const response = await llmClient.chat([{ role: 'user', content: prompt }], { temperature: 0.7, max_tokens: 400, streaming: false, label: 'reflect', responseFormat: (window as unknown as { StructuredFormats?: { insights?: unknown } }).StructuredFormats?.insights });
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
                // Keep the usable shapes: strings (legacy) and objects with a
                // real belief. Nulls from the strict schema are dropped here.
                const insights = parsedList.filter((i: unknown) =>
                    (typeof i === 'string' && i.length > 10)
                    || (typeof i === 'object' && i !== null && String((i as { belief?: unknown }).belief || '').length > 10));
                if (insights.length > 0) {
                    await fetch(`/api/players/${encodeURIComponent(charName)}/memories/reflect`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            insights,
                            tick: currentTick,
                            source_memory_ids: candidates.map((m: MemoryRecord) => m.id)
                        })
                    }).catch(() => {});
                }
                events.log(`🧠 ${charName} reflected on ${candidates.length} memories`, 'system-msg');
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
    function _sanitizeTags(tags: unknown): string[] {
        if (!Array.isArray(tags)) return [];
        // Entity names we never want as memory tags (people, items, areas)
        const entityNames = new Set<string>();
        const g = worldState?.data || {};
        for (const name of Object.keys(g.players || {})) entityNames.add(name.toLowerCase());
        for (const node of Object.values<{ name?: unknown }>(worldState?.graph?.nodes || {})) {
            if (node?.name) entityNames.add(String(node.name).toLowerCase());
        }
        const singleWord = /^[a-z0-9_]+$/;
        const seen = new Set<string>();
        const out: string[] = [];
        for (const raw of tags as unknown[]) {
            const t = String(raw || '').trim().toLowerCase();
            if (!t) continue;
            if (!singleWord.test(t)) continue;              // multi-word / hyphenated → drop
            if (entityNames.has(t)) continue;               // person/item/area name → drop
            if (seen.has(t)) continue;                      // dedupe
            seen.add(t);
            out.push(t);
        }
        return out;
    }

    function storeMemory(charName: string, text: string, importance: number, type: string,
                      tick: number | null = null, entity_ids: string[] = [],
                      tags: string[] = [], emotion: { label?: string; intensity?: number } | null = null,
                      emotions: Record<string, unknown> | null = null): void {
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
                cleanTags.forEach((tagId: string) => _ensureLibraryTag(tagId));
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
    function _embedAndStoreVector(charName: string, memoryId: string | undefined, text: string): void {
        if (!memoryId || !(window as unknown as { EmbeddingClient?: { configured(): boolean } }).EmbeddingClient?.configured()) return;
        EmbeddingClient.embed(text).then((vector: number[]) => {
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
    const _checkedTagIds = new Set<string>();
    function _ensureLibraryTag(tagId: string): void {
        if (_checkedTagIds.has(tagId)) return;
        _checkedTagIds.add(tagId);
        try {
            fetch("/api/tags/search?q=" + encodeURIComponent(tagId))
                .then(r => r.json())
                .then((tags: { id?: string }[]) => {
                    const exists = Array.isArray(tags) && tags.some((t: { id?: string }) => (t.id || '').toLowerCase() === tagId.toLowerCase());
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

(window as unknown as { AgentMemory: typeof AgentMemory }).AgentMemory = AgentMemory;

// Declared below the first value statement on purpose: TypeScript drops a
// file's leading JSDoc block when the first statement is type-only, which would
// strip the `@module` header tools/js_module_index.py reads.
interface MemoryRecord {
    id?: string;
    text?: string;
    tick?: number;
    importance?: number;
    reinforcements?: number;
    reflection_depth?: number;
    [key: string]: unknown;
}
