/** Unit tests for conversation-context.js — speech salience + anti-repeat (task-321). */
'use strict';
const CC = window.PromptBuilder;

// ── classifySpeechType ──

test('name call is addressed_to_you', () => {
    assertEq(CC.classifySpeechType('Hey Lyrie, watch out!', 'Lyrie', {}), 'addressed_to_you');
});

test('name match is case-insensitive', () => {
    assertEq(CC.classifySpeechType('HELLO LYRIE I AM MIKI', 'Lyrie', {}), 'addressed_to_you');
});

test('player.name acts as alias', () => {
    assertEq(CC.classifySpeechType('Are you there, Lyra?', 'Lyrie', { name: 'Lyra' }), 'addressed_to_you');
});

test('group wording is to_group', () => {
    assertEq(CC.classifySpeechType('Does everyone have a lantern?', 'Lyrie', {}), 'to_group');
    assertEq(CC.classifySpeechType('Can anyone hear me?', 'Lyrie', {}), 'to_group');
});

test('second-person pronoun is to_you', () => {
    assertEq(CC.classifySpeechType('Do you have a name?', 'Lyrie', {}), 'to_you');
    assertEq(CC.classifySpeechType('I like your hair', 'Lyrie', {}), 'to_you');
});

test('plain chatter stays overheard', () => {
    assertEq(CC.classifySpeechType("That's really pretty", 'Lyrie', {}), 'overheard');
    assertEq(CC.classifySpeechType('He said he is fine', 'Lyrie', {}), 'overheard');
    assertEq(CC.classifySpeechType('', 'Lyrie', {}), 'overheard');
});

// ── markSpeechLine ──

test('marker inserted after leading bracket for heard lines', () => {
    assertEq(
        CC.markSpeechLine('[Heard] a voice said: "hey Lyrie, look!"', 'hey Lyrie, look!', 'Lyrie', {}),
        '[Heard → addressed to you] a voice said: "hey Lyrie, look!"'
    );
});

test('group lines marked to the group', () => {
    assertEq(
        CC.markSpeechLine('[Heard] a voice said: "everyone stay here"', 'everyone stay here', 'Lyrie', {}),
        '[Heard → to the group] a voice said: "everyone stay here"'
    );
});

test('overheard lines unchanged', () => {
    const line = '[Heard] a voice said: "pretty tree"';
    assertEq(CC.markSpeechLine(line, 'pretty tree', 'Lyrie', {}), line);
});

test('local anon speaker lines get the marker too', () => {
    assertEq(
        CC.markSpeechLine('[Miki] said: "Hello Lyrie! I am Miki"', 'Hello Lyrie! I am Miki', 'Lyrie', {}),
        '[Miki → addressed to you] said: "Hello Lyrie! I am Miki"'
    );
});

// ── ownRecentSpeech (anti-repeat) ──

test('own recent speech dedupes and excludes others', () => {
    const player = { recent_hearing: [
        { type: 'speech', speaker: 'Lyrie', text: 'Hello?' },
        { type: 'speech', speaker: 'Miki', text: 'Hi!' },
        { type: 'speech', speaker: 'Lyrie', text: 'Hello?' },
        { type: 'speech', speaker: 'Lyrie', text: 'Is someone there?' },
    ] };
    assertEq(CC.ownRecentSpeech(player, 'Lyrie'), ['"Hello?"', '"Is someone there?"']);
});

// ── talkinessHint + buildConversationInstinct ──

test('talkiness hint appears at social extremes only', () => {
    assertTrue(CC.talkinessHint({ vitals: { social: 90 } }).length > 0, 'high social hints');
    assertFalse(CC.talkinessHint({ vitals: { social: 50 } }), 'neutral silent');
});

test('buildConversationInstinct includes anti-repeat rule when own speech exists', () => {
    const player = { recent_hearing: [{ type: 'speech', speaker: 'Lyrie', text: 'Hello?' }] };
    const block = CC.buildConversationInstinct(player, 'Lyrie');
    assertTrue(block.includes('CONVERSATION'), 'section header');
    assertTrue(block.includes('"Hello?"'), 'own line quoted');
    assertTrue(block.toLowerCase().includes('do not repeat'), 'anti-repeat rule');
});

test('buildConversationInstinct empty when nothing notable', () => {
    assertEq(CC.buildConversationInstinct({ vitals: { social: 50 } }, 'Lyrie'), '');
});
