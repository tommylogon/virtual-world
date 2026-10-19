/**
 * Unit tests for HumanTurnComposer command parsing and speech feedback (task-878).
 */

const HTC = window.HumanTurnComposer;

test('parseCmd parses known action verbs with items and targets', () => {
    assertEq(HTC.parseCmd('look'), { action: 'look' }, 'simple verb');
    assertEq(HTC.parseCmd('go north'), { action: 'go', item: 'north' }, 'verb + direction');
    assertEq(HTC.parseCmd('take rusty sword'), { action: 'take', item: 'rusty sword' }, 'verb + item');
    assertEq(HTC.parseCmd('give bread to Lyrie'), { action: 'give', item: 'bread', target: 'Lyrie' }, 'give item to target');
    assertEq(HTC.parseCmd('use key on door'), { action: 'use', item: 'key', target: 'door' }, 'use item on target');
});

test('parseCmd treats volume prefixes as speech with volume', () => {
    assertEq(HTC.parseCmd('whisper hello there'), { speech: 'hello there', volume: 'whisper' }, 'whisper');
    assertEq(HTC.parseCmd('shout watch out!'), { speech: 'watch out!', volume: 'shout' }, 'shout');
    assertEq(HTC.parseCmd('scream help!'), { speech: 'help!', volume: 'scream' }, 'scream');
});

test('parseCmd treats unknown verbs as speech', () => {
    assertEq(HTC.parseCmd('walk over to the counter'), { speech: 'walk over to the counter' }, 'walk is not in VERBS');
    assertEq(HTC.parseCmd('hello friend'), { speech: 'hello friend' }, 'greetings are speech');
});

test('doHint provides warning and suggestions when text in do field will be spoken (task-878)', () => {
    // Known actions show NO hint
    assertEq(HTC.doHint('go north'), null, 'known action go has no hint');
    assertEq(HTC.doHint('take sword'), null, 'known action take has no hint');
    assertEq(HTC.doHint('attack goblin'), null, 'known action attack has no hint');
    assertEq(HTC.doHint(''), null, 'empty input has no hint');

    // Deliberate speech with volume words shows NO hint
    assertEq(HTC.doHint('whisper hello'), null, 'whisper is deliberate speech');
    assertEq(HTC.doHint('shout behind you'), null, 'shout is deliberate speech');
    assertEq(HTC.doHint('scream'), null, 'bare volume word has no hint');

    // Unknown verbs that will be spoken show warning and alias suggestions
    const walkHint = HTC.doHint('walk to the bar');
    assertTrue(walkHint !== null, 'walk shows a hint');
    assertTrue(walkHint.indexOf('will be spoken aloud') >= 0, 'hint warns that line will be spoken');
    assertTrue(walkHint.indexOf('go') >= 0, 'hint suggests "go" for walk');

    const hitHint = HTC.doHint('hit goblin with rock');
    assertTrue(hitHint !== null, 'hit shows a hint');
    assertTrue(hitHint.indexOf('attack') >= 0, 'hint suggests "attack" for hit');

    const consumeHint = HTC.doHint('consume potion');
    assertTrue(consumeHint !== null, 'consume shows a hint');
    assertTrue(consumeHint.indexOf('eat, drink') >= 0, 'hint suggests eat/drink for consume');
});

test('the human turn composer wires htc-do-hint in template and input listener (task-878)', () => {
    const src = window.__readFile('static/js/agent/human-turn-composer.js');
    assertTrue(/id="htc-do-hint"/.test(src), 'template includes htc-do-hint container');
    assertTrue(/addEventListener\('input',\s*updateDoHint\)/.test(src), 'htc-do input event updates hint');
    assertTrue(/function doHint\s*\(/.test(src), 'doHint helper function is defined');
});
