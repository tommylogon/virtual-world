/**
 * Unit tests for the fear/interest verbs in the action normalizer (task-469).
 */

test('fear normalizes to a bare command with its target', () => {
    const an = window.ActionNormalizer;
    assertEq(an.normalizeStructuredAction({ action: 'fear', target: 'Snarl' }), 'fear Snarl');
});

test('interest normalizes with its target from item or target', () => {
    const an = window.ActionNormalizer;
    assertEq(an.normalizeStructuredAction({ action: 'interest', item: 'old ruins' }), 'interest old ruins');
});

test('fear without a target degrades to the bare verb', () => {
    const an = window.ActionNormalizer;
    assertEq(an.normalizeStructuredAction({ action: 'fear' }), 'fear');
});

test('fear and interest are valid verbs', () => {
    const an = window.ActionNormalizer;
    assertTrue(an.isValidAction('fear Snarl'), 'fear');
    assertTrue(an.isValidAction('interest ruins'), 'interest');
});
