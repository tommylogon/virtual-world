/**
 * Unit tests for schedule in prompt context and available actions (task-814).
 */

var PB = window.PromptBuilder;

test('buildMosiacContext includes complete routine, current step, and edit commands', () => {
    const player = {
        name: 'Gribba',
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
    assertTrue(ctx.includes('=== YOUR MIND ==='), 'mind header present');
    assertTrue(ctx.includes('Schedule: 08:00 patrol at Gate; 12:00 eat at Mess (current: patrol at Gate)'), 'routine and current step formatted');
    assertTrue(ctx.includes('schedule add HH:MM <activity> [at <area>]'), 'add syntax explained');
    assertTrue(ctx.includes('schedule remove HH:MM'), 'remove syntax explained');
});

test('buildMosiacContext falls back to player.schedule if mosiac is not precomputed', () => {
    const player = {
        name: 'Belne',
        schedule: [
            { start: 540, activity: 'wait', area: 'Camp Entrance' },
            { start: 720, activity: 'eat' }
        ]
    };
    const ctx = PB.buildMosiacContext(player);
    assertTrue(ctx.includes('Schedule: 09:00 wait at Camp Entrance; 12:00 eat'), 'fallback formats steps');
    assertTrue(ctx.includes('schedule add HH:MM'), 'fallback includes edit syntax');
});

test('buildMosiacContext shows no schedule message when schedule is empty', () => {
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
    assertTrue(ctx.includes('Schedule: no schedule'), 'empty schedule reported');
    assertTrue(ctx.includes('schedule add HH:MM'), 'edit syntax still taught');
});
