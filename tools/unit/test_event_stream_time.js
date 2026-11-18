/**
 * tools/unit/test_event_stream_time.js
 *
 * bug-591: Unit tests for EventBus.tickToTime() and EventBus.tickToRelative()
 * with integer and fractional time_per_tick_minutes.
 */
'use strict';

(() => {
    function withEventBus(fn) {
        const stubNames = [
            'StreamTurnCards',
            'StreamFilters',
            'StreamRawLLM',
            'StreamPersistence',
            'StreamScrubber',
            'StreamControlMode',
            'StreamSandbox',
        ];
        const savedGlobals = {};
        for (const name of stubNames) {
            savedGlobals[name] = window[name];
            window[name] = function StubCollaborator() {};
        }
        const savedEvents = window.events;
        const savedVW = window.VW;
        const savedEventBus = window.EventBus;
        try {
            eval(__readFile('static/js/event-stream.js'));
            fn(window.events);
        } finally {
            window.events = savedEvents;
            window.VW = savedVW;
            if (savedEventBus === undefined) delete window.EventBus;
            else window.EventBus = savedEventBus;
            for (const name of stubNames) {
                if (savedGlobals[name] === undefined) delete window[name];
                else window[name] = savedGlobals[name];
            }
        }
    }

    test('tickToTime formats integer time_per_tick_minutes as HH:MM', () => {
        withEventBus((bus) => {
            window.VW = { state: { data: { time_per_tick_minutes: 5, clock_start_hour: 8, clock_start_minute: 0 } } };
            assertEq(bus.tickToTime(0), '08:00', 'tick 0 at 5m/tick');
            assertEq(bus.tickToTime(10), '08:50', 'tick 10 at 5m/tick');
            assertEq(bus.tickToTime(12), '09:00', 'tick 12 at 5m/tick');

            window.VW = { state: { data: { time_per_tick_minutes: 1, clock_start_hour: 23, clock_start_minute: 58 } } };
            assertEq(bus.tickToTime(2), '00:00', 'midnight wrap at 1m/tick');
        });
    });

    test('tickToTime formats 0.25 and 0.1 fractional time_per_tick_minutes as HH:MM:SS without decimal minutes', () => {
        withEventBus((bus) => {
            window.VW = { state: { data: { time_per_tick_minutes: 0.25, clock_start_hour: 8, clock_start_minute: 0 } } };
            assertEq(bus.tickToTime(0), '08:00:00', '0.25m/tick tick 0');
            assertEq(bus.tickToTime(1), '08:00:15', '0.25m/tick tick 1');
            assertEq(bus.tickToTime(2), '08:00:30', '0.25m/tick tick 2');
            assertEq(bus.tickToTime(4), '08:01:00', '0.25m/tick tick 4');
            assertEq(bus.tickToTime(17), '08:04:15', '0.25m/tick tick 17');

            window.VW = { state: { data: { time_per_tick_minutes: 0.1, clock_start_hour: 8, clock_start_minute: 0 } } };
            assertEq(bus.tickToTime(1), '08:00:06', '0.1m/tick tick 1');
            assertEq(bus.tickToTime(3), '08:00:18', '0.1m/tick tick 3');
            assertEq(bus.tickToTime(43), '08:04:18', '0.1m/tick tick 43 must not emit 08:4.3');
            assertFalse(bus.tickToTime(43).includes('.'), 'formatted time never contains a decimal point');

            window.VW = { state: { data: { time_per_tick_minutes: 2.5, clock_start_hour: 8, clock_start_minute: 0 } } };
            assertEq(bus.tickToTime(1), '08:02:30', '2.5m/tick tick 1 shows :SS');
            assertEq(bus.tickToTime(2), '08:05', '2.5m/tick tick 2 omits :00 when tpm >= 1');
        });
    });

    test('tickToRelative distinguishes sub-minute second offsets and reserves just now for diffTicks === 0', () => {
        withEventBus((bus) => {
            window.VW = { state: { data: { time_ticks: 10, time_per_tick_minutes: 5 } } };
            assertEq(bus.tickToRelative(null), 'a while ago', 'null tick');
            assertEq(bus.tickToRelative(10), 'just now', 'same tick');
            assertEq(bus.tickToRelative(9), '5 minutes ago', '1 tick at 5m/tick');
            assertEq(bus.tickToRelative(0), '50 minutes ago', '10 ticks at 5m/tick');

            window.VW = { state: { data: { time_ticks: 20, time_per_tick_minutes: 0.25 } } };
            assertEq(bus.tickToRelative(20), 'just now', '0.25m/tick diff 0');
            assertEq(bus.tickToRelative(19), '15 seconds ago', '0.25m/tick diff 1');
            assertEq(bus.tickToRelative(18), '30 seconds ago', '0.25m/tick diff 2');
            assertEq(bus.tickToRelative(16), '1 minute ago', '0.25m/tick diff 4');
            assertEq(bus.tickToRelative(15), '1 minute ago', '0.25m/tick diff 5 floors fractional minutes');

            window.VW = { state: { data: { time_ticks: 50, time_per_tick_minutes: 0.1 } } };
            assertEq(bus.tickToRelative(50), 'just now', '0.1m/tick diff 0');
            assertEq(bus.tickToRelative(49), '6 seconds ago', '0.1m/tick diff 1');
            assertEq(bus.tickToRelative(47), '18 seconds ago', '0.1m/tick diff 3');
            assertEq(bus.tickToRelative(40), '1 minute ago', '0.1m/tick diff 10');

            window.VW = { state: { data: { time_ticks: 10, time_per_tick_minutes: 1 / 60 } } };
            assertEq(bus.tickToRelative(9), '1 second ago', 'singular 1 second ago');
        });
    });
})();
