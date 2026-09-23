/**
 * Unit tests for the Soak Lab's pure front-end helpers.
 * Loaded by tools/unit/run.cjs; see AGENTS.md ("JS unit tests").
 */
'use strict';

test('soak: fmtDuration formats h/m/s', () => {
    assertEq(SoakFormat.fmtDuration(0), '0s');
    assertEq(SoakFormat.fmtDuration(59), '59s');
    assertEq(SoakFormat.fmtDuration(61), '1m01s');
    assertEq(SoakFormat.fmtDuration(3661), '1h01m');
    assertEq(SoakFormat.fmtDuration(-5), '0s');
});

test('soak: esc neutralises angle brackets and quotes', () => {
    assertEq(SoakFormat.esc('<a href="x">&\''),
        '&lt;a href=&quot;x&quot;&gt;&amp;&#39;');
    assertEq(SoakFormat.esc(null), '');
});

test('soak: configToQuery/queryToConfig round-trips booleans and numbers', () => {
    const cfg = {
        scenario: 'data/scenarios/combat_pit.json', ticks: 77, engine_decay: true,
        seed: 42, label: 'deep-link', decay_overrides: { Energy: 0, Thirst: 1.5 },
        track_vitals: ['Hunger', 'Thirst'], mature: false,
    };
    const qs = SoakFormat.configToQuery(cfg);
    const back = SoakFormat.queryToConfig('?' + qs);
    assertEq(back.scenario, cfg.scenario);
    assertEq(back.ticks, 77);
    assertEq(back.engine_decay, true);
    assertEq(back.seed, 42);
    assertEq(back.decay_overrides, 'Energy=0,Thirst=1.5');
    assertEq(back.track_vitals, ['Hunger', 'Thirst']);
    assertEq(SoakFormat.queryToConfig(''), null);
});

test('soak: vitalColor has known colours and a deterministic fallback', () => {
    assertEq(SoakFormat.vitalColor('HP'), '#f85149');
    assertEq(SoakFormat.vitalColor('Mystery'), SoakFormat.PALETTE[0]);
    assertEq(SoakFormat.vitalColor('Mystery', 1), SoakFormat.PALETTE[1]);
});

test('soak: niceTicks stay inside the domain and are monotonic', () => {
    const ticks = SoakCharts.niceTicks(0, 100, 5);
    assertTrue(ticks.length >= 2, 'at least two ticks');
    for (let i = 1; i < ticks.length; i++) assertTrue(ticks[i] > ticks[i - 1], 'monotonic');
    assertTrue(ticks[0] >= 0 && ticks[ticks.length - 1] <= 100, 'within domain');
});

test('soak: histogram preserves the sample count across bins', () => {
    const values = [690, 700, 710, 715, 730, 749, 750, 762];
    const bins = SoakCharts.histogram(values, 4);
    const total = bins.reduce((n, b) => n + b.value, 0);
    assertEq(total, values.length);
    assertEq(bins.length, 4);
});

test('soak: line chart renders axes and series, and an empty state', () => {
    const svg = SoakCharts.renderLineChart({
        series: [{ name: 'HP', color: '#f85149', points: [[0, 100], [10, 20]] }],
        xDomain: [0, 10], yDomain: [0, 120],
    });
    assertTrue(svg.indexOf('<svg') === 0, 'svg root first');
    assertTrue(svg.indexOf('</svg>') > 0, 'svg closed');
    assertTrue(svg.includes('#f85149'), 'series colour used');
    const empty = SoakCharts.renderLineChart({ series: [] });
    assertTrue(empty.includes('soak-chart-empty'), 'empty state rendered');
});

test('soak: sparkline tolerates short series', () => {
    assertTrue(SoakCharts.renderSparkline([]).includes('<svg'));
    assertTrue(SoakCharts.renderSparkline([5]).includes('<svg'));
    assertTrue(SoakCharts.renderSparkline([1, 2, 3, 4]).includes('<path'));
});

test('soak: donut reports a total and escapes labels', () => {
    const svg = SoakCharts.renderDonut({
        slices: [{ label: '<bad>', value: 3, color: '#f85149' }],
    });
    assertTrue(svg.includes('&lt;bad&gt;'), 'label escaped');
    assertTrue(svg.includes('>3<'), 'total rendered');
});
