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

test('timeskip a soak order summarizes the order, never elapsed figures', () => {
    const g = window.Timeskip._internals;
    const text = g.summarize({
        ok: true, mode: 'soak',
        order: { intent: 'idle', declared_minutes: 30, remaining_minutes: 30,
                 target: null, heading: null, watch_tags: [] },
    }).join('\n');
    assertTrue(text.indexOf('undefined') === -1, 'no undefined in: ' + text);
    assertTrue(/30 min/.test(text), 'names the span: ' + text);
    assertTrue(/Soak order/.test(text), 'names the mode: ' + text);
});

test('timeskip a soak order with a target and watch tags reports both', () => {
    const g = window.Timeskip._internals;
    const text = g.summarize({
        ok: true, mode: 'soak',
        order: { intent: 'travel', declared_minutes: 120, target: 'Water Source',
                 heading: null, watch_tags: ['relic', 'treasure'] },
    }).join('\n');
    assertTrue(/Water Source/.test(text), 'names the target: ' + text);
    assertTrue(/relic, treasure/.test(text), 'names the watch tags: ' + text);
});

test('timeskip a blocking advance still reports elapsed minutes and the clock', () => {
    const g = window.Timeskip._internals;
    const text = g.summarize({
        ok: true, mode: 'character', elapsed_minutes: 120, ticks: 40,
        clock_after: '10:00', vitals_before: { hunger: 50 }, vitals_after: { hunger: 62 },
    }).join('\n');
    assertTrue(/Elapsed: 120 min \(40 ticks\)/.test(text), 'elapsed line: ' + text);
    assertTrue(/10:00/.test(text), 'clock line: ' + text);
    assertTrue(/hunger 50→62/.test(text), 'vitals line: ' + text);
});

test('timeskip world mode prints only the world-advance line and never undefined (task-858)', () => {
    const g = window.Timeskip._internals;
    const lines = g.summarize({ ok: true, mode: 'world' });
    const text = lines.join('\n');
    assertEq(lines.length, 1, 'world mode has exactly one summary line: ' + text);
    assertEq(lines[0], 'No active character - the world advances.', 'world line matches');
    assertTrue(text.indexOf('undefined') === -1, 'no undefined in: ' + text);
    assertTrue(text.indexOf('Elapsed:') === -1, 'no elapsed line in: ' + text);
});

test('timeskip a soak order promoted before it runs reports ended with its reason (task-859)', () => {
    const g = window.Timeskip._internals;
    const text = g.summarize({
        ok: true, mode: 'soak', ended: true, reason: 'Your bladder is critical.',
        order: { intent: 'explore', declared_minutes: 120, remaining_minutes: 120,
                 ended: true, reason: 'Your bladder is critical.' },
    }).join('\n');
    assertTrue(/ended: Your bladder is critical\./.test(text), 'reports ended and reason: ' + text);
    assertTrue(text.indexOf('Control comes back early') === -1, 'no control comes back placeholder in: ' + text);
});

test('timeskip isDeadNoGhost detects dead character gated on ghost mode (task-857)', () => {
    const g = window.Timeskip._internals;
    const oldWs = window.worldState;
    try {
        window.worldState = {
            data: {
                active_player: 'Hero',
                players: { Hero: { state: 'dead' } },
                ghost_mode: false,
            },
        };
        assertTrue(g.isDeadNoGhost(), 'dead player and ghost mode off is blocked');

        window.worldState.data.ghost_mode = true;
        assertTrue(!g.isDeadNoGhost(), 'ghost mode on allows ghost');

        window.worldState.data.ghost_mode = false;
        window.worldState.data.players.Hero.state = 'awake';
        assertTrue(!g.isDeadNoGhost(), 'awake player is not blocked');
    } finally {
        window.worldState = oldWs;
    }
});
