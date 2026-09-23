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

test('timeskip travel to a target derives its span from the route', () => {
    const g = window.Timeskip._internals;
    assertEq(g.buildPayload({ intent: 'travel', customMinutes: 0, preset: '2h', target: 'Water Source' }),
        { intent: 'travel', target: 'Water Source' }, 'no minutes sent for route travel');
});

test('timeskip travel with a heading keeps its duration', () => {
    const g = window.Timeskip._internals;
    assertEq(g.buildPayload({ intent: 'travel', customMinutes: 0, preset: '2h', heading: 'west' }),
        { intent: 'travel', minutes: 120, heading: 'west' });
});

test('timeskip wait uses the preset, custom overrides preset', () => {
    const g = window.Timeskip._internals;
    assertEq(g.buildPayload({ intent: 'idle', customMinutes: 0, preset: '2h' }),
        { intent: 'idle', minutes: 120 });
    assertEq(g.buildPayload({ intent: 'idle', customMinutes: 45, preset: '8h' }),
        { intent: 'idle', minutes: 45 });
});

test('timeskip watch tags split and trim', () => {
    const g = window.Timeskip._internals;
    assertEq(g.buildPayload({ intent: 'explore', customMinutes: 0, preset: '1h', tags: 'relic, treasure' }),
        { intent: 'explore', minutes: 60, watch_tags: ['relic', 'treasure'] });
});

test('timeskip until-dawn omits minutes and sends until', () => {
    const g = window.Timeskip._internals;
    assertEq(g.buildPayload({ intent: 'idle', customMinutes: 0, preset: 'until:dawn' }),
        { intent: 'idle', until: 'dawn' });
});

test('timeskip an explicit duration beats an until preset', () => {
    const g = window.Timeskip._internals;
    assertEq(g.buildPayload({ intent: 'idle', customMinutes: 30, preset: 'until:dawn' }),
        { intent: 'idle', minutes: 30 });
});
