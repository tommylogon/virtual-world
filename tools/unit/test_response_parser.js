/** Unit tests for response-parser.js — LLM response → structured action parsing. */
'use strict';
const RP = window.ResponseParser;

test('parseReaction parses a clean structured object', () => {
    const r = JSON.stringify({
        inner_monologue: 'I should answer.',
        speech: 'Hello there!',
        volume: 'say',
        action: 'wave',
        emote: 'smiles shyly',
        memory: { text: 'Met a stranger.', importance: 6, tags: ['meeting'] },
    });
    const p = RP.parseReaction(r);
    assertEq(p.inner, 'I should answer.');
    assertEq(p.speech, 'Hello there!');
    assertEq(p.speechVolume, 'say');
    assertEq(p.emote, 'smiles shyly');
    assertEq(p.memory.text, 'Met a stranger.');
    assertFalse(p.parseError, 'no parse error');
});

test('parseReaction treats volume as the KEY not inline text', () => {
    // The classic LLM mistake: {"speech":"whisper psst"} — speech keeps the
    // word, volume falls back to default say.
    const r = JSON.stringify({ speech: 'whisper psst, over here' });
    const p = RP.parseReaction(r);
    assertTrue(p.speech.toLowerCase().includes('psst'), 'speech preserved');
    assertEq(p.speechVolume, 'say', 'volume defaults when inline');
});

test('parseReaction handles markdown-fenced JSON', () => {
    const r = '```json\n{"inner_monologue":"hmm","action":"wait"}\n```';
    const p = RP.parseReaction(r);
    assertEq(p.action, 'wait');
    assertFalse(p.parseError, 'fence stripped');
});

test('parseReaction reports parseError on garbage instead of throwing', () => {
    const p = RP.parseReaction('this is not json at all {{{');
    assertTrue(p.parseError, 'error captured');
    assertEq(p.speech, null, 'no speech on failure');
});

test('parseReaction on empty input returns the neutral shape', () => {
    const p = RP.parseReaction(null);
    assertEq(p.speechVolume, 'say');
    assertEq(p.action, '');
    assertEq(p.parseError, null);
});

test('extractMemory accepts plain strings and clamps importance', () => {
    assertEq(RP.extractMemory('a thought').text, 'a thought');
    assertEq(RP.extractMemory({ text: 'x', importance: 99 }).importance, 10);
    assertEq(RP.extractMemory({ text: 'x', importance: -3 }).importance, 1);
    assertEq(RP.extractMemory({ importance: 5 }), null, 'no text = no memory');
});

test('parseResultReaction has no action field', () => {
    const p = RP.parseResultReaction(JSON.stringify({ inner_monologue: 'ouch', emote: 'winces' }));
    assertEq(p.emote, 'winces');
    assertFalse('action' in p, 'react phase never carries an action');
});
