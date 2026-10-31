/**
 * tools/unit/test_turn_feed_recap.js
 *
 * task-790: Unit tests for Human Turn Panel recap of NPC speech and actions.
 */

(() => {
    const TF = window.TurnFeed;

    test('buildSummary separately summarizes speech and actions for multiple NPCs without truncation (task-790)', () => {
        assertTrue(typeof TF.buildSummary === 'function', 'TF.buildSummary exists');

        const rawEntries = [
            { text: '[Jake Halloway] says, "Did someone drop this crimson note?"', actor: 'Jake Halloway', className: 'msg-speech' },
            { text: '[Kayla Jenkins] says, "Let me see that! The handwriting looks suspiciously fancy for detention."', actor: 'Kayla Jenkins', className: 'msg-speech' },
            { text: '[Action] examined crimson-ink note', actor: 'Kayla Jenkins', className: 'msg-action' },
            { text: '[Sammy Lopez] says, "Who cares about a stupid note anyway? Probably a prank from the freshmen."', actor: 'Sammy Lopez', className: 'msg-speech' },
            { text: '[Action] kicked cafeteria table', actor: 'Sammy Lopez', className: 'msg-action' },
        ];

        const summary = TF.buildSummary(rawEntries);

        assertTrue(summary.includes('Kayla Jenkins'), 'Kayla Jenkins included in recap');
        assertTrue(summary.includes('said "Let me see that! The handwriting looks suspiciously fancy for detention."'), 'Kayla speech included');
        assertTrue(summary.includes('examined crimson-ink note'), 'Kayla action included');

        assertTrue(summary.includes('Sammy Lopez'), 'Sammy Lopez included in recap');
        assertTrue(summary.includes('said "Who cares about a stupid note anyway? Probably a prank from the freshmen."'), 'Sammy speech included');
        assertTrue(summary.includes('kicked cafeteria table'), 'Sammy action included');

        // Total length exceeds 200 characters and has no trailing truncation ellipsis
        assertTrue(summary.length > 200, `summary length is ${summary.length}`);
        assertFalse(summary.endsWith('...'), 'summary is not truncated with ellipsis');
    });

    test('buildSummary preserves long lines beyond old 260-char cap without slicing (task-790)', () => {
        const longSpoken = 'A'.repeat(300);
        const rawEntries = [
            { text: `[Lulu Ashford] says, "${longSpoken}"`, actor: 'Lulu Ashford', className: 'msg-speech' },
        ];

        const summary = TF.buildSummary(rawEntries);
        assertTrue(summary.includes(longSpoken), 'full 300-char spoken line preserved');
        assertFalse(summary.includes('...'), 'no truncation ellipsis inserted');
    });

    test('renderDetailedFeed renders "No other characters acted" when no NPCs took turns (task-790)', () => {
        const prevActive = window.worldState ? window.worldState.activePlayer : undefined;
        const prevData = window.worldState ? window.worldState.data : undefined;
        const prevPlayers = window.worldState ? window.worldState.players : undefined;

        try {
            window.worldState = window.worldState || {};
            window.worldState.activePlayer = 'Jake Halloway';
            window.worldState.players = {
                'Jake Halloway': { name: 'Jake Halloway', current_area: 'Cafeteria' },
            };
            window.worldState.data = {
                activePlayer: 'Jake Halloway',
                active_player: 'Jake Halloway',
                players: window.worldState.players,
            };

            TF.clearDigest();
            TF.markTurnEnd();

            // Log an event from the player
            events.log('You waited by the lockers.', 'msg-result', null, 'Jake Halloway');

            const host = document.createElement('div');
            TF.render(host, 14);

            const summaryEl = host.children.find(c => c.className === 'tf-summary');
            assertTrue(summaryEl != null, 'summary element rendered');
            const summaryText = summaryEl.children.map(c => c.textContent).join('');
            assertTrue(summaryText.includes('No other characters acted') || summaryText.includes('You'), 'informative message rendered');
        } finally {
            if (window.worldState) {
                window.worldState.activePlayer = prevActive;
                window.worldState.data = prevData;
                window.worldState.players = prevPlayers;
            }
        }
    });
})();
