/**
 * Unit tests for subjective near-horizon schedule framing and available actions (task-814).
 */

var PB = window.PromptBuilder;

test('buildMosiacContext frames current routine subjectively under YOUR INTENTIONS & ROUTINE', () => {
    const player = {
        name: 'Gribba',
        current_area: 'Gate',
        mosiac: {
            M: 'stay fed and safe',
            I: 'patrol the perimeter',
            S: {
                now: 480,
                step: { start: 480, activity: 'patrol', area: 'Gate' },
                day: '08:00 patrol at Gate; 12:00 eat at Mess'
            }
        }
    };
    const ctx = PB.buildMosiacContext(player);
    assertTrue(ctx.includes('=== YOUR INTENTIONS & ROUTINE ==='), 'intentions & routine header present');
    assertTrue(ctx.includes('Routine:') && ctx.includes('patrol') && ctx.includes('Gate'), 'current routine framed subjectively');
    assertFalse(ctx.includes('08:00 patrol at Gate; 12:00 eat at Mess'), 'full-day cron table not dumped into working memory');
});

test('buildMosiacContext falls back to player.schedule when mosiac is not precomputed', () => {
    const prevData = window.worldState && window.worldState.data;
    try {
        window.worldState.data = { game_time: '09:05' };
        const player = {
            name: 'Belne',
            current_area: 'Yard',
            schedule: [
                { start: 540, activity: 'wait', area: 'Camp Entrance' },
                { start: 720, activity: 'eat' }
            ]
        };
        const ctx = PB.buildMosiacContext(player);
        assertTrue(ctx.includes('Camp Entrance') && ctx.includes('wait'), 'overdue step surfaces subjectively');
        assertFalse(ctx.includes('12:00 eat'), 'distant step >60m away is not dumped');
    } finally {
        window.worldState.data = prevData;
    }
});

test('buildMosiacContext omits Routine line when schedule is empty', () => {
    const player = {
        name: 'Belne',
        mosiac: {
            M: 'wander',
            S: {
                now: 500,
                step: null,
                day: 'no schedule'
            }
        }
    };
    const ctx = PB.buildMosiacContext(player);
    assertTrue(ctx.includes('Motivation: wander'), 'motivation still rendered');
    assertFalse(ctx.includes('Routine:'), 'no empty Routine line when schedule is empty');
});
