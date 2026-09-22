/**
 * Unit tests for the timeskip UI's pure helpers (task-464).
 * The POST/refresh path needs a DOM + server, so only preset mapping is tested.
 */

test('timeskip presetMinutes maps known presets to minutes', () => {
    const g = window.Timeskip._internals;
    assertEq(g.presetMinutes('30m'), 30, '30m');
    assertEq(g.presetMinutes('2h'), 120, '2h');
    assertEq(g.presetMinutes('8h'), 480, '8h');
});

test('timeskip presetMinutes rejects unknown keys', () => {
    const g = window.Timeskip._internals;
    assertTrue(g.presetMinutes('nope') === null, 'unknown key is null');
});
