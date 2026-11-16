/**
 * tools/unit/test_mind_history.js
 *
 * task-862: Unit tests for character lived_log history surface on MindView.
 */

(() => {
    const MV = window.InspectorMindView;

    test('lived-log rollup collapses consecutive identical non-salient entries (task-862)', () => {
        assertTrue(typeof MV._rollupLivedLog === 'function', 'MV._rollupLivedLog exists');

        const entries = [
            { tick: 1, kind: 'move', what: 'walked north', why: 'patrol', area: 'Courtyard', salient: false },
            { tick: 2, kind: 'act', what: 'drank water', why: 'needs:thirst', area: 'Kitchen', salient: false },
            { tick: 3, kind: 'act', what: 'drank water', why: 'needs:thirst', area: 'Kitchen', salient: false },
            { tick: 4, kind: 'act', what: 'drank water', why: 'needs:thirst', area: 'Kitchen', salient: false },
            { tick: 5, kind: 'act', what: 'drank water', why: 'needs:thirst', area: 'Kitchen', salient: false },
            { tick: 6, kind: 'act', what: 'drank water', why: 'needs:thirst', area: 'Kitchen', salient: true },
            { tick: 7, kind: 'act', what: 'read note', why: 'curiosity', area: 'Bedroom', salient: false },
        ];

        const rolled = MV._rollupLivedLog(entries);
        assertEq(rolled.length, 4, 'rolled entries length');
        assertEq(rolled[0].what, 'walked north', 'first single entry');
        assertEq(rolled[1].what, 'drank water (x4)', 'collapsed run of 4');
        assertEq(rolled[1].count, 4, 'count property on collapsed entry');
        assertEq(rolled[2].what, 'drank water', 'salient entry kept separate');
        assertEq(rolled[3].what, 'read note', 'last entry intact');
    });

    test('lived-log history renders newest first with kind chips, why tags and area badges (task-862)', () => {
        assertTrue(typeof MV._historyHtml === 'function', 'MV._historyHtml exists');

        const oldPlayers = window.worldState ? window.worldState.players : undefined;
        try {
            window.worldState = window.worldState || {};
            window.worldState.players = Object.assign({}, oldPlayers, {
                test_char: {
                    name: 'test_char',
                    lived_log: [
                        { tick: 10, kind: 'act', what: 'Hygiene fell to 50', why: 'needs:hygiene', area: "Chief's Pit" },
                        { tick: 15, kind: 'move', what: 'moved to Cafeteria', why: 'social', area: 'Cafeteria' },
                    ],
                },
            });

            const html = MV._historyHtml('test_char');
            assertTrue(html.includes('Lived Log (2 recorded)'), 'header count');
            assertTrue(html.includes('moved to Cafeteria'), 'entry 1 text');
            assertTrue(html.includes('Hygiene fell to 50'), 'entry 2 text');
            assertTrue(html.includes('why: needs:hygiene'), 'why reason tag');
            assertTrue(html.includes("Chief&#39;s Pit") || html.includes("Chief's Pit"), 'area badge');
            assertTrue(html.includes('[t15]'), 'tick tag');

            // Verify newest first: t15 must appear before t10 in rendered HTML
            const idx15 = html.indexOf('[t15]');
            const idx10 = html.indexOf('[t10]');
            assertTrue(idx15 < idx10, 'newest entry (t15) rendered before older entry (t10)');
        } finally {
            if (window.worldState) {
                window.worldState.players = oldPlayers;
            }
        }
    });

    test('formatTickWithWorldTime formats positive calendar ticks, negative relative ticks, and age (task-973)', () => {
        assertTrue(typeof MV.formatTickWithWorldTime === 'function', 'MV.formatTickWithWorldTime exists');

        const ws = { time_per_tick_minutes: 5, clock_start_hour: 8, clock_start_minute: 0, time_ticks: 0 };
        assertEq(MV.formatTickWithWorldTime(12, ws), 'tick 12 (Day 1, 09:00)', 'positive tick calendar time');
        assertEq(MV.formatTickWithWorldTime(-5000, ws), 'tick -5000 (~17d ago)', 'negative tick relative days');
        assertEq(
            MV.formatTickWithWorldTime(-2102400, ws, 25),
            'tick -2102400 (~20y ago, age ~5)',
            'negative tick with playerAge shows approximate age'
        );
        assertEq(
            MV.formatTickWithWorldTime(12, { time_per_tick_minutes: 10, clock_start_hour: 6, clock_start_minute: 30 }, 30),
            'tick 12 (Day 1, 08:30, age ~30)',
            'respects custom time_per_tick_minutes and clock_start'
        );
    });
})();
