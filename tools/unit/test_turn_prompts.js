/**
 * tools/unit/test_turn_prompts.js - prompt surfacing of dice/skill checks
 * (task-479).
 *
 * `summaryLine` condenses a previous action result into the one-line RECENTLY
 * block. Before task-479 it took the first line only, so a check result that
 * was not the first line (a trigger appends its outputs, a movement prepends a
 * pass message) never reached the model, and the narration had no roll to
 * explain. These pin the behaviour.
 */
'use strict';

const promptBuilder479 = window.PromptBuilder;

test('summaryLine returns the first line when no check is present', () => {
    assertEq(promptBuilder479.summaryLine('You climb the wall.\nThe wind bites.'), 'You climb the wall.');
});

test('summaryLine keeps a check line that is the first line', () => {
    const text = '[Skill Check] Athletics vs DC 15 (medium): roll=12 + 3 = 15 => success\nYou haul yourself over.';
    assertEq(promptBuilder479.summaryLine(text),
        '[Skill Check] Athletics vs DC 15 (medium): roll=12 + 3 = 15 => success');
});

test('summaryLine surfaces a check line that is NOT the first line', () => {
    const text = 'You search the debris.\n[Skill Check] Investigation vs DC 12 (medium): roll=18 + 2 = 20 => success';
    assertEq(promptBuilder479.summaryLine(text),
        '[Skill Check] Investigation vs DC 12 (medium): roll=18 + 2 = 20 => success - You search the debris.');
});

test('summaryLine recognises saves, generic checks and grabs', () => {
    assertEq(promptBuilder479.summaryLine('nothing happened\n[Save] DEX vs DC 12: roll 4 + 1 = 5 => failure'),
        '[Save] DEX vs DC 12: roll 4 + 1 = 5 => failure - nothing happened');
    assertEq(promptBuilder479.summaryLine('nothing happened\n[Check] attack vs DC 5 (very easy): roll=9 + 2 = 11 => success'),
        '[Check] attack vs DC 5 (very easy): roll=9 + 2 = 11 => success - nothing happened');
    assertEq(promptBuilder479.summaryLine('nothing happened\n[Grab] Athletics vs DC 14: roll 10 + 6 = 16 => success'),
        '[Grab] Athletics vs DC 14: roll 10 + 6 = 16 => success - nothing happened');
});

test('summaryLine on empty text is empty', () => {
    assertEq(promptBuilder479.summaryLine(''), '');
    assertEq(promptBuilder479.summaryLine(null), '');
});

test('bug-517: room-context.ts does not call playerSpeak', () => {
    const src = __readFile('static/js/agent/prompt-builder/room-context.ts');
    assertEq(src.includes('playerSpeak'), false, 'room-context must not invoke playerSpeak');
});

test('bug-559: available actions prompt block omits major verbs when major budget is 0', () => {
    const pb = window.PromptBuilder;
    const state = {
        players: {},
        players_in_area: [{ name: 'Belne', description: 'goblin' }]
    };
    const player = { name: 'Arix', vitals: { Energy: 80, Bladder: 10 } };
    const area = { name: 'Food Storage', ambient_light: 50, exits: {} };
    
    // With full budget: attack is present
    const fullBlock = pb.buildAvailableActionsBlock(state, 'Arix', player, area, { major: 1, minor: 1, free: 3, activity: 1 });
    assertTrue(fullBlock.includes('attack  -  fight'), 'Full budget should have attack');

    // With major: 0: attack is omitted, note is present
    const spentMajorBlock = pb.buildAvailableActionsBlock(state, 'Arix', player, area, { major: 0, minor: 1, free: 3, activity: 1 });
    assertFalse(spentMajorBlock.includes('attack  -  fight'), 'Exhausted major budget should omit attack');
    assertTrue(spentMajorBlock.includes('Major actions exhausted this turn'), 'Should explain major actions exhausted');
    assertTrue(spentMajorBlock.includes('grab  -  seize'), 'Minor action grab should remain');

    // With major: 0 and minor: 0: grab omitted, exhausted both note present
    const spentBothBlock = pb.buildAvailableActionsBlock(state, 'Arix', player, area, { major: 0, minor: 0, free: 3, activity: 1 });
    assertFalse(spentBothBlock.includes('grab  -  seize'), 'Exhausted minor budget should omit grab');
    assertTrue(spentBothBlock.includes('Major and minor actions exhausted this turn'), 'Should explain both exhausted');
    assertTrue(spentBothBlock.includes('wait  -  wait or hold still'), 'Wait should remain');
});
