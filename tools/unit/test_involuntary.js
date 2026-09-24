/** Unit tests for Involuntary — involuntary speech/emote flavor (task-166). */
'use strict';
const INV = window.Involuntary;

/** Run `fn` with Math.random pinned to `value`, restoring it afterwards. */
function withRandom(value, fn) {
    const original = Math.random;
    Math.random = () => value;
    try { return fn(); } finally { Math.random = original; }
}

const FEMALE = { tags: ['female'], conditions: {} };
const MALE = { tags: ['male'], conditions: {} };

test('speech/emote return null when nothing fires', () => {
    assertEq(INV.speech('Hello there.', FEMALE), null, 'no speech trigger');
    assertEq(INV.emote('*she waves*', FEMALE), null, 'no emote trigger');
});

test('frightened stutters the first word of speech', () => {
    const frightened = { tags: ['female'], conditions: { frightened: [{ duration: 3 }] } };
    const out = withRandom(0.0, () => INV.speech('What did you say?', frightened));
    assertEq(out, 'W-what did you say?', 'stutter');
});

test('speech never replaces the intended line', () => {
    const frightened = { tags: ['female'], conditions: { frightened: [{}] } };
    const out = withRandom(0.0, () => INV.speech("I can't do that.", frightened));
    assertTrue(out.includes("can't do that."), 'original words survive');
});

test('a startle splices a yelp without replacing the line', () => {
    const out = withRandom(0.0, () => INV.speech("I'm fine.", FEMALE, { startled: true }));
    assertTrue(out.startsWith("I'm fine."), 'line preserved');
    assertTrue(out.includes('yelp'), 'yelp injected');
});

test('a startle appends a strong emote, pronoun-rendered', () => {
    const out = withRandom(0.0, () => INV.emote('*she looks up*', FEMALE, { startled: true }));
    assertTrue(out.startsWith('*she looks up*'), 'emote preserved');
    assertTrue(out.includes('flinch hard'), 'startle emote used');
    assertTrue(out.includes('a sharp yelp escaping'), 'rendered text present');
    assertTrue(!out.includes('{they}'), 'no unrendered placeholder');
});

test('condition emotes use the character pronouns', () => {
    const itchy = { tags: ['male'], conditions: { itch: [{}] } };
    const out = withRandom(0.0, () => INV.emote('*he waits*', itchy));
    assertTrue(out.startsWith('*he waits*'), 'emote preserved');
    assertTrue(out.includes('scratch at an itch'), 'itch flavor used');
});

test('jittery raises the involuntary chance', () => {
    const plain = { tags: [], conditions: {} };
    const jittery = { tags: [], conditions: {}, traits: { jittery: true } };
    // 0.09 is above the 0.06 baseline but below the boosted 0.06 * 1.8.
    assertEq(withRandom(0.09, () => INV.speech('Steady now.', plain)), null, 'plain no fire');
    const out = withRandom(0.09, () => INV.speech('Steady now.', jittery));
    assertTrue(out && out.includes('*hic*'), 'jittery fires');
});

test('startle only fires when the flag enables it', () => {
    // 0.9 is above both the startle (0.70) and random (0.04) chances.
    assertEq(withRandom(0.9, () => INV.emote('*she waits*', FEMALE)), null, 'no random flavor');
    assertEq(withRandom(0.9, () => INV.emote('*she waits*', FEMALE, { startled: true })), null, 'roll missed');
    const out = withRandom(0.0, () => INV.emote('*she waits*', FEMALE, { startled: true }));
    assertTrue(out.includes('flinch hard'), 'flag unlocks the startle pool');
});
