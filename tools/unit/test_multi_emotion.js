/**
 * test_multi_emotion.js
 *
 * Verifies multi-emotion and multi-target affect support across StructuredFormats,
 * PromptBuilder.JSON_FIELDS, ResponseParser, ActionInterpreter, and AgentEngine (bug-596).
 */
'use strict';

test('StructuredFormats.agentAction and agentReact allow null, single object, and array emotion', () => {
    for (const fmt of [StructuredFormats.agentAction, StructuredFormats.agentReact]) {
        const js = fmt.json_schema;
        const emoSchema = js.schema.properties.emotion;
        assertTrue(Array.isArray(emoSchema.anyOf), `${js.name} emotion schema uses anyOf`);
        const hasNull = emoSchema.anyOf.some((s) => s.type === 'null');
        const hasObj = emoSchema.anyOf.some((s) => s.type === 'object');
        const hasArr = emoSchema.anyOf.some((s) => s.type === 'array' && s.items && s.items.type === 'object');
        assertTrue(hasNull, `${js.name} allows null emotion`);
        assertTrue(hasObj, `${js.name} allows single emotion object`);
        assertTrue(hasArr, `${js.name} allows array of emotion objects`);
    }
    assertTrue(PromptBuilder.JSON_FIELDS.emotion.includes('['), 'JSON_FIELDS.emotion shows array example');
    assertTrue(PromptBuilder.JSON_FIELDS.emotion_toward.includes('['), 'JSON_FIELDS.emotion_toward shows array example');
});

test('ResponseParser normalizes both single-emotion objects and multi-target arrays', () => {
    const single = ResponseParser.parseReaction(JSON.stringify({
        inner_monologue: 'Stay calm.',
        action: 'wait',
        emotion: { label: 'Afraid', intensity: 6, toward: 'Stranger' }
    }));
    assertEq(single.emotion, { label: 'afraid', intensity: 6, toward: 'Stranger' }, 'single emotion object preserved');

    const multi = ResponseParser.parseReaction(JSON.stringify({
        inner_monologue: 'Too much at once.',
        action: 'wait',
        emotion: [
            { label: 'Terrified', intensity: 9, toward: 'Attacker A' },
            { label: 'Furious', intensity: 8, toward: 'Betrayer B' },
            { label: 'Uneasy', intensity: null, toward: null }
        ]
    }));
    assertEq(multi.emotion, [
        { label: 'terrified', intensity: 9, toward: 'Attacker A' },
        { label: 'furious', intensity: 8, toward: 'Betrayer B' },
        { label: 'uneasy', intensity: 5, toward: null }
    ], 'multi-emotion array normalized with intensity fallback');

    const reactMulti = ResponseParser.parseResultReaction(JSON.stringify({
        inner_monologue: 'That hurt.',
        emotion: [
            { label: 'hurt', intensity: 7, toward: 'Guard' },
            { label: 'relieved', intensity: 4, toward: null }
        ]
    }));
    assertEq(reactMulti.emotion.length, 2, 'parseResultReaction preserves multi-emotion array');
    assertEq(ResponseParser.extractEmotion([]), null, 'empty array normalizes to null');
});

test('ActionInterpreter preserves structured emotion objects and arrays in ResponseParser and fallback paths', async () => {
    const prevConfig = window.config;
    const prevParser = window.ResponseParser;
    try {
        const mixedPayload = [
            { label: 'terrified', intensity: 9, toward: 'Person A' },
            { label: 'furious', intensity: 7, toward: 'Person B' }
        ];
        window.config = {
            getInterpreterLLMClient: () => ({
                async chat() {
                    return JSON.stringify({
                        inner_monologue: 'Trapped between them.',
                        action: 'wait',
                        item: null,
                        target: null,
                        speech: null,
                        volume: 'say',
                        emote: 'backs away',
                        emotion: mixedPayload
                    });
                }
            })
        };

        const viaParser = await ActionInterpreter.interpretProseToAction({
            prose: 'She backs away, terrified of Person A and furious at Person B.',
            charName: 'Lyrie'
        });
        assertEq(viaParser.emotion, mixedPayload, 'ResponseParser path preserves multi-emotion array');

        // Force fallback JSON branch by temporarily removing ResponseParser
        window.ResponseParser = null;
        const viaFallback = await ActionInterpreter.interpretProseToAction({
            prose: 'She backs away, terrified of Person A and furious at Person B.',
            charName: 'Lyrie'
        });
        assertEq(viaFallback.emotion, mixedPayload, 'Fallback branch preserves multi-emotion array without [object Object]');
        assertTrue(Array.isArray(viaFallback.emotion), 'Fallback emotion is an array, not a string');
        assertFalse(JSON.stringify(viaFallback.emotion).includes('[object Object]'), 'No [object Object] corruption');
    } finally {
        window.config = prevConfig;
        window.ResponseParser = prevParser;
    }
});

test('AgentEngine._applyFeltEmotion dispatches all impulses and preserves opaque identity', async () => {
    const prevAgent = window.agent;
    const prevRateLimiter = window.RateLimiter;
    window.RateLimiter = window.RateLimiter || class {};
    const AgentEngineCtor = new Function(window.__readFile('static/js/agent-engine.js') + '; return AgentEngine;')();
    window.agent = prevAgent;
    const engine = Object.create(AgentEngineCtor.prototype);
    const prevWorldState = window.worldState;
    const prevApiClient = window.ApiClient;
    const calls = [];
    try {
        window.worldState = { players: { 'player_opaque_1': { name: 'Lyrie' } } };
        window.ApiClient = {
            getPlayerEmotions(charName, body) {
                calls.push({ charName, body });
                return Promise.resolve({ ok: true });
            }
        };

        await engine._applyFeltEmotion('player_opaque_1', [
            { label: 'terrified', intensity: 9, toward: 'player_opaque_2' },
            { label: 'furious', intensity: 7, toward: 'Betrayer B' },
            { label: 'uneasy', intensity: 4 }
        ]);

        assertEq(calls.length, 3, 'All 3 emotion impulses dispatched');
        assertEq(calls[0], {
            charName: 'player_opaque_1',
            body: { emotion: 'terrified', intensity: 9, toward: 'player_opaque_2' }
        }, 'Target-directed impulse 1 preserves opaque identity');
        assertEq(calls[1], {
            charName: 'player_opaque_1',
            body: { emotion: 'furious', intensity: 7, toward: 'Betrayer B' }
        }, 'Target-directed impulse 2 preserved');
        assertEq(calls[2], {
            charName: 'player_opaque_1',
            body: { emotion: 'uneasy', intensity: 4, delta: 6 }
        }, 'Global impulse computes delta');

        // Backward compatibility: single object
        calls.length = 0;
        await engine._applyFeltEmotion('player_opaque_1', { label: 'calm', intensity: 3 });
        assertEq(calls.length, 1, 'Single emotion object dispatches once');
        assertEq(calls[0].body, { emotion: 'calm', intensity: 3, delta: 4.5 }, 'Single emotion delta preserved');
    } finally {
        window.worldState = prevWorldState;
        window.ApiClient = prevApiClient;
        window.RateLimiter = prevRateLimiter;
    }
});
