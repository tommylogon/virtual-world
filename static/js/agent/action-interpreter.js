"use strict";
/**
 * action-interpreter.ts - Action interpretation layer between narrative prose and engine actions
 *
 * Extracts structured action fields (inner_monologue, action, target, item, speech,
 * speechVolume, emote, emotion) from unconstrained or semi-structured character prose.
 * Powers the two-stage cognition pipeline (task-943) allowing creative models
 * to write natural prose while this service translates intention to simulation schema.
 *
 * Load AFTER shared/json-utils.js, BEFORE agent-engine.js.
 *
 * @module agent/action-interpreter
 * @contributes ActionInterpreter: translate character prose into engine actions
 * @powers two-stage cognition, prose-to-action translation, director interpretation
 * @relates depends on shared/json-utils.js, config.js, and llm-client.js
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
window.ActionInterpreter = (() => {
    'use strict';
    function buildExtractionPrompt(params) {
        const { prose, charName, context, directorNote } = params;
        const systemPrompt = `You are a strict narrative action interpreter for a virtual world simulation.
Your job is to read a creative roleplay prose passage written from ${charName}'s perspective and translate their immediate intent into the simulation engine's exact turn schema.

RULES:
1. Extract what ${charName} privately thinks or feels into "inner_monologue".
2. Extract spoken dialogue into "speech". Set "volume" to "say", "whisper", "shout", or "scream" based on context.
3. Extract bodily gestures or physical demeanor into "emote".
4. Identify the ONE primary mechanical action ${charName} immediately attempts:
   - "action": a single engine action (e.g. "go", "take", "drop", "use", "use_on", "examine", "open", "close", "wait", "relieve", "attack", "rest").
   - "item": object or item used/held, or null.
   - "target": target entity, exit, or person acted on, or null.
   - If they only speak, think, or make gestures without moving or interacting with an object, set "action": null, "item": null, "target": null.
   - Do NOT invent actions that are not described in the prose.
5. If emotions are expressed, specify "emotion" as an array of { "label": "...", "intensity": 1-10, "toward": "person or null" } (or a single label/object, or null).

Output ONLY a valid JSON object matching the engine's canonical turn schema:
{
  "inner_monologue": "private thoughts/feelings or null",
  "action": "single action or null",
  "item": "interacted item or null",
  "target": "target entity/exit/person or null",
  "speech": "spoken words without quotes or null",
  "volume": "say" | "whisper" | "shout" | "scream",
  "emote": "physical body language or null",
  "emotion": [{"label": "uneasy", "intensity": 6, "toward": "person or null"}]
}`;
        let contextBlock = '';
        if (context) {
            const lines = [];
            if (context.waysOut?.length) {
                lines.push('EXITS: ' + context.waysOut.map(w => `${w.name} (${w.direction || 'way'} -> ${w.destination})`).join(', '));
            }
            if (context.thingsVisible?.length) {
                lines.push('THINGS VISIBLE: ' + context.thingsVisible.join(', '));
            }
            if (context.peopleHere?.length) {
                lines.push('PEOPLE HERE: ' + context.peopleHere.join(', '));
            }
            if (context.inventory?.length) {
                lines.push('INVENTORY: ' + context.inventory.join(', '));
            }
            if (lines.length) {
                contextBlock = `\n=== ROOM AFFORDANCES ===\n${lines.join('\n')}\n`;
            }
        }
        const noteBlock = directorNote ? `\nDirector's guidance was: "${directorNote}"\n` : '';
        const userPrompt = `${noteBlock}${contextBlock}
=== CHARACTER PROSE (${charName}) ===
${prose.trim()}

Extract the structured turn JSON for ${charName}:`;
        return { systemPrompt, userPrompt };
    }
    function normalizeSingleEmotion(raw) {
        if (typeof raw === 'string') {
            const label = raw.trim().toLowerCase();
            return label ? { label, intensity: 5, toward: null } : null;
        }
        if (!raw || typeof raw !== 'object' || Array.isArray(raw))
            return null;
        const rec = raw;
        const label = String(rec.label || '').trim().toLowerCase();
        if (!label)
            return null;
        const rawInt = rec.intensity;
        const intensity = (rawInt === null || rawInt === undefined || rawInt === '')
            ? 5
            : parseFloat(String(rawInt));
        if (!Number.isFinite(intensity))
            return null;
        const toward = typeof rec.toward === 'string' ? rec.toward.trim() : '';
        return { label, intensity: Math.max(1, Math.min(10, intensity)), toward: toward || null };
    }
    function normalizeEmotionPayload(raw) {
        if (!raw)
            return null;
        if (typeof raw === 'string') {
            const trimmed = raw.trim();
            return trimmed || null;
        }
        if (Array.isArray(raw)) {
            const list = raw.map(normalizeSingleEmotion).filter((e) => e !== null);
            return list.length ? list : null;
        }
        return normalizeSingleEmotion(raw);
    }
    async function interpretProseToAction(params) {
        const { prose, charName } = params;
        if (!prose || !prose.trim())
            return null;
        const win = window;
        const config = win.config;
        const client = config?.getInterpreterLLMClient ? config.getInterpreterLLMClient() : window.llmClient;
        if (!client) {
            console.warn('[ActionInterpreter] No LLM client available for interpretation.');
            return null;
        }
        const { systemPrompt, userPrompt } = buildExtractionPrompt(params);
        try {
            const raw = await client.chat([
                { role: 'system', content: systemPrompt },
                { role: 'user', content: userPrompt }
            ], {
                label: 'action-interpreter',
                actor: charName,
                temperature: 0.2 // Low temperature for deterministic translation
            });
            if (!raw)
                return null;
            // Delegate directly to ResponseParser for canonical parsing, repair, and normalization
            const parser = window.ResponseParser;
            if (parser && typeof parser.parseReaction === 'function') {
                const parsedReaction = parser.parseReaction(raw);
                if (parsedReaction) {
                    const actRaw = typeof parsedReaction.action === 'string' ? parsedReaction.action.trim() : '';
                    const normAction = actRaw && actRaw.toLowerCase() !== 'none' ? actRaw : null;
                    const memVal = typeof parsedReaction.memory === 'object' && parsedReaction.memory
                        ? parsedReaction.memory.text || null
                        : (parsedReaction.memory || null);
                    const emoVal = parsedReaction.emotion
                        ? normalizeEmotionPayload(parsedReaction.emotion)
                        : null;
                    // Extract raw json to preserve action target/item and string emotion labels
                    let rawItem = null;
                    let rawTarget = parsedReaction.target || null;
                    let rawEmotion = emoVal;
                    try {
                        const parsedObj = JSON.parse(typeof raw === 'string' ? raw : JSON.stringify(raw));
                        if (parsedObj.item)
                            rawItem = String(parsedObj.item).trim();
                        if (parsedObj.target)
                            rawTarget = String(parsedObj.target).trim();
                        if (!rawEmotion && parsedObj.emotion) {
                            rawEmotion = normalizeEmotionPayload(parsedObj.emotion);
                        }
                    }
                    catch (_) { /* fallback to parsedReaction */ }
                    return {
                        action: normAction,
                        item: rawItem,
                        target: rawTarget,
                        speech: parsedReaction.speech || null,
                        speechVolume: parsedReaction.speechVolume || 'say',
                        emote: parsedReaction.emote || null,
                        inner_monologue: parsedReaction.inner || null,
                        emotion: rawEmotion,
                        memory: memVal,
                        rawProse: prose
                    };
                }
            }
            let text = typeof raw === 'string' ? raw : (raw.content || raw.text || '');
            if (typeof win.repairJSON === 'function') {
                text = win.repairJSON(text);
            }
            // Extract JSON object block
            const match = text.match(/\{[\s\S]*\}/);
            if (!match) {
                console.warn('[ActionInterpreter] Failed to locate JSON in response:', text);
                return null;
            }
            const parsed = JSON.parse(match[0]);
            const volumeVal = (parsed.volume || 'say').toLowerCase();
            const speechVolume = ['whisper', 'shout', 'scream'].includes(volumeVal) ? volumeVal : 'say';
            // Support canonical engine keys with legacy/fallback keys
            const innerVal = parsed.inner_monologue || parsed.thought || null;
            const speechVal = parsed.speech || parsed.say || parsed.text || null;
            const memVal = parsed.memory || null;
            return {
                action: parsed.action ? String(parsed.action).trim() : null,
                item: parsed.item ? String(parsed.item).trim() : null,
                target: parsed.target ? String(parsed.target).trim() : null,
                speech: speechVal ? String(speechVal).trim() : null,
                speechVolume,
                emote: parsed.emote ? String(parsed.emote).trim() : null,
                inner_monologue: innerVal ? String(innerVal).trim() : null,
                emotion: normalizeEmotionPayload(parsed.emotion),
                memory: memVal ? String(memVal).trim() : null,
                rawProse: prose
            };
        }
        catch (err) {
            console.error('[ActionInterpreter] Error parsing interpretation result:', err);
            return null;
        }
    }
    return {
        interpretProseToAction,
        buildExtractionPrompt
    };
})();
