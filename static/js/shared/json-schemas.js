/**
 * json-schemas.js — Structured output schemas for LLM calls (task: structured output).
 *
 * Every call that expects JSON back declares its shape here. Two tiers:
 *   - Strict json_schema shapes (closed fields, provider-enforced) for the
 *     agent turn loop, plan, reflection, personality, and interest tags.
 *   - A plain { type: 'json_object' } format for the dynamic/recursive shapes
 *     (item/world/room generation) where a closed schema cannot express the
 *     depth — still guarantees valid JSON, parsing stays as-is.
 *
 * Strict-mode rules honored here: root must be an object, every object sets
 * additionalProperties:false, every property is listed in required (optional
 * fields become nullable via type arrays). Nulls are stripped downstream by
 * the parsers, which already treat absent and falsy identically.
 *
 * Load AFTER shared/json-utils.js, BEFORE llm-client users (agent-engine.js,
 * plan-manager.js, memory-manager.js, ai-generator.js, inspector files).
 */

window.StructuredFormats = (() => {
    'use strict';

    const NULLABLE_STR = { type: ['string', 'null'] };

    /** emotion.data — closed set of relationship deltas (engine/emotion.py). */
    const EMOTION_DATA = {
        type: ['object', 'null'],
        additionalProperties: false,
        properties: {
            fear: { type: ['number', 'null'] },
            affection: { type: ['number', 'null'] },
            disgust: { type: ['number', 'null'] },
            anger: { type: ['number', 'null'] },
            trust: { type: ['number', 'null'] },
            envy: { type: ['number', 'null'] },
            familiarity: { type: ['number', 'null'] },
            respect: { type: ['number', 'null'] },
            closeness: { type: ['number', 'null'] }
        },
        required: ['fear', 'affection', 'disgust', 'anger', 'trust', 'envy', 'familiarity', 'respect', 'closeness']
    };

    const EMOTION = {
        type: ['object', 'null'],
        additionalProperties: false,
        properties: {
            label: NULLABLE_STR,
            intensity: { type: ['number', 'null'] },
            toward: NULLABLE_STR
        },
        required: ['label', 'intensity', 'toward']
    };

    const MEMORY = {
        type: ['object', 'null'],
        additionalProperties: false,
        properties: {
            text: NULLABLE_STR,
            importance: { type: ['integer', 'null'] },
            tags: { type: ['array', 'null'], items: { type: 'string' } },
            emotions: {
                anyOf: [
                    { type: 'null' },
                    {
                        type: 'object',
                        additionalProperties: false,
                        properties: { who: NULLABLE_STR, why: NULLABLE_STR, data: EMOTION_DATA },
                        required: ['who', 'why', 'data']
                    }
                ]
            }
        },
        required: ['text', 'importance', 'tags', 'emotions']
    };

    /** think-decide / combined / auto-retry / chain-follow-up — full action turn. */
    const agentAction = {
        name: 'agent_action',
        strict: true,
        schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
                inner_monologue: NULLABLE_STR,
                action: NULLABLE_STR,
                item: NULLABLE_STR,
                target: NULLABLE_STR,
                speech: NULLABLE_STR,
                volume: NULLABLE_STR,
                emote: NULLABLE_STR,
                memory: MEMORY,
                emotion: EMOTION,
                learned_names: { type: ['array', 'null'], items: { type: 'string' } }
            },
            required: ['inner_monologue', 'action', 'item', 'target', 'speech', 'volume', 'emote', 'memory', 'emotion', 'learned_names']
        }
    };

    /** result-reaction — react phase, no action fields. */
    const agentReact = {
        name: 'agent_react',
        strict: true,
        schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
                inner_monologue: NULLABLE_STR,
                speech: NULLABLE_STR,
                volume: NULLABLE_STR,
                emote: NULLABLE_STR,
                memory: MEMORY,
                emotion: EMOTION,
                learned_names: { type: ['array', 'null'], items: { type: 'string' } }
            },
            required: ['inner_monologue', 'speech', 'volume', 'emote', 'memory', 'emotion', 'learned_names']
        }
    };

    /** plan — strict schemas require an object root, hence the steps wrapper. */
    const plan = {
        name: 'plan',
        strict: true,
        schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
                steps: { type: 'array', items: { type: 'string' } }
            },
            required: ['steps']
        }
    };

    /** memory reflect — same wrapper reasoning as plan. */
    const insights = {
        name: 'memory_insights',
        strict: true,
        schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
                insights: { type: 'array', items: { type: 'string' } }
            },
            required: ['insights']
        }
    };

    /** character personality generation. */
    const personality = {
        name: 'personality',
        strict: true,
        schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
                personality: NULLABLE_STR,
                description: NULLABLE_STR
            },
            required: ['personality', 'description']
        }
    };

    /** interest-tag picking — wrapper because the old contract was a raw array. */
    const tags = {
        name: 'interest_tags',
        strict: true,
        schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
                tags: { type: 'array', items: { type: 'string' } }
            },
            required: ['tags']
        }
    };

    /** Fallback tier for dynamic shapes (item/world/room generation): valid
     *  JSON guaranteed, schema not enforced. Requires the word "json" in the
     *  messages — every caller here already says it. */
    const jsonObject = { type: 'json_object' };

    /** Wrap a bare {name, strict, schema} into a chat-completions
     *  response_format payload. */
    const sch = (def) => ({ type: 'json_schema', json_schema: { name: def.name, strict: def.strict !== false, schema: def.schema } });

    return {
        agentAction: sch(agentAction),
        agentReact: sch(agentReact),
        plan: sch(plan),
        insights: sch(insights),
        personality: sch(personality),
        tags: sch(tags),
        jsonObject
    };
})();
