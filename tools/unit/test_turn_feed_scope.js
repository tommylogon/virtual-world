/**
 * The human panel's "What happened" feed is fed by TurnFeed's ring, which
 * subscribes to the WHOLE app event log. Save/load, library, graph and loadout
 * operations report themselves there too, and those are console output, not
 * things that happened in the fiction.
 *
 * The leak was not the obvious rows: isObserverVisible already drops a parsed
 * `system` type, so "Scenario saved to foo" was already filtered. The rows that
 * escaped were the ones parseEntry re-labels as an action whenever
 * _tryParsePrefixedName matches — any operational line that happened to read
 * "<Name> <verb>". Filtering at the ring push closes the whole class.
 *
 * The one system row that IS a turn row — an NPC doing nothing — must survive.
 */

'use strict';

test('system-msg console chatter never enters the turn feed', () => {
    TurnFeed.clearDigest();
    TurnFeed.markTurnEnd();

    events.log('Scenario saved to Autumn House', 'system-msg');
    events.log('💾 Game saved: autosave.json', 'system-msg');
    events.log('Saved "brass key" to library.', 'system-msg');
    events.log('Settings saved.', 'system-msg');
    events.log('🗺 That scope has no painted grid to fit to.', 'system-msg');
    events.log('Auto-dress cancelled; nothing was equipped.', 'system-msg');
    events.log('kyrie johansen opens the vase', 'system-msg');

    assertEq(TurnFeed.digest().length, 0,
        'no operational row reaches the digest');
});

test('the NPC did-nothing row is a turn row and survives', () => {
    TurnFeed.clearDigest();
    TurnFeed.markTurnEnd();

    events.log('👾 kyrie johansen did nothing this turn.', 'system-msg');

    const digest = TurnFeed.digest();
    assertEq(digest.length, 1, 'an idle NPC is something that happened');
    assertTrue(/did nothing this turn/.test(digest[0].text), 'text preserved');
});

test('real turn rows are unaffected', () => {
    TurnFeed.clearDigest();
    TurnFeed.markTurnEnd();

    events.log('[kyrie johansen] says, "water in the vase?"', 'msg-speech');
    events.log('kyrie johansen unwraps the protein bar.', 'msg-emote');
    events.log('You use the protein_bar.', 'msg-result');

    const digest = TurnFeed.digest();
    assertEq(digest.length, 3, 'speech, emote and result all kept');
});

test('an NPC line is attributed to its actor, not to You', () => {
    // record_turn_event stamps the actor on the event; parseEntry used to throw
    // that away and re-derive it from a closed verb list, so an unlisted verb
    // ("unwraps") fell through to a null actor and rendered as "You".
    const parsed = TurnFeed.parseEntry({
        text: 'kyrie johansen unwraps the protein bar and takes a dry bite.',
        className: 'msg-emote',
        actor: 'kyrie johansen',
        seq: 1,
    });
    assertEq(parsed.actor, 'kyrie johansen', 'actor read structurally');
    assertEq(parsed.content, 'kyrie johansen unwraps the protein bar and takes a dry bite.',
        'the text is not mangled into an action');
});

test('bug-518: an NPC result row is attributed to its actor, not to You', () => {
    // The emitter stamps the acting character on the result row. parseEntry's
    // result branch used to hardcode actor:null, so an NPC's row fell through
    // to isPlayer and rendered as "You".
    const parsed = TurnFeed.parseEntry({
        text: 'You eat the granola_bar.',
        className: 'msg-result',
        actor: 'sammy lopez',
        seq: 1,
    });
    assertEq(parsed.type, 'result', 'still a result row');
    assertEq(parsed.actor, 'sammy lopez', 'the carried actor is kept');
});

test('an actor-less result row still reads as the player', () => {
    const parsed = TurnFeed.parseEntry({
        text: 'You use the protein_bar.',
        className: 'msg-result',
        actor: null,
        seq: 2,
    });
    assertEq(parsed.actor, null, 'no actor means the player, rendered as You');
});