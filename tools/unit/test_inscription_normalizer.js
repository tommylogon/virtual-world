/**
 * Unit tests for the task-433 inscription form in the action normalizer.
 *
 * A `text` payload must become the two-quoted-token command the backend parser
 * carries as `params`; without a text it must stay an ordinary use_on.
 */

test('use_on with text emits quoted target and text', () => {
    const an = window.ActionNormalizer;
    assertEq(
        an.normalizeStructuredAction({
            action: 'use_on', item: 'ink pen', target: 'parchment', text: 'Meet at dawn',
        }),
        'use ink pen on "parchment" "Meet at dawn"'
    );
});

test('write verb is an alias for the inscription form', () => {
    const an = window.ActionNormalizer;
    assertEq(
        an.normalizeStructuredAction({
            action: 'write', item: 'pencil', target: 'journal', text: 'day 3',
        }),
        'use pencil on "journal" "day 3"'
    );
});

test('embedded quotes in the payload are neutralised', () => {
    const an = window.ActionNormalizer;
    assertEq(
        an.normalizeStructuredAction({
            action: 'use_on', item: 'ink pen', target: 'paper', text: 'say "hi"',
        }),
        `use ink pen on "paper" "say 'hi'"`
    );
});

test('use_on without text is unchanged', () => {
    const an = window.ActionNormalizer;
    assertEq(
        an.normalizeStructuredAction({
            action: 'use_on', item: 'brass key', target: 'locked door',
        }),
        'use brass key on locked door'
    );
});

test('write and inscribe are valid verbs', () => {
    const an = window.ActionNormalizer;
    assertTrue(an.isValidAction('write'), 'write');
    assertTrue(an.isValidAction('inscribe'), 'inscribe');
});
