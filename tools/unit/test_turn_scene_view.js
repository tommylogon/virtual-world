/**
 * Unit tests for TurnSceneView and way menus (bug-561, bug-562).
 */
'use strict';

test('buildWayMenu offers Approach when character is not at the way and omits it when at the way (bug-561)', () => {
    const TSV = window.TurnSceneView;
    assertTrue(!!TSV, 'TurnSceneView is available');
    assertTrue(typeof TSV.buildWayMenu === 'function', 'buildWayMenu is a function');

    const way = {
        id: 'way_door_1',
        way_id: 'way_door_1',
        name: 'Oak Door',
        direction: 'north',
        to: 'Hall',
        state: 'open',
    };

    // 1. Character not standing at the way -> Approach offered
    const menuAway = TSV.buildWayMenu(way, [], 'way_door_other', false);
    const approachEntry = menuAway.find((m) => m.label && m.label.startsWith('Approach'));
    assertTrue(!!approachEntry, 'Approach entry exists when character is not at the way');
    assertEq(approachEntry.label, 'Approach north');

    // 2. Character standing at the way -> Approach omitted
    const menuAt = TSV.buildWayMenu(way, [], 'way_door_1', false);
    const approachAt = menuAt.find((m) => m.label && m.label.startsWith('Approach'));
    assertTrue(!approachAt, 'Approach entry omitted when character is already at the way');

    // 3. Approach with way.id fallback when way_id missing
    const wayNoId = { id: 'way_door_2', name: 'Arch', direction: 'east', state: 'open' };
    const menuFallback = TSV.buildWayMenu(wayNoId, [], 'way_door_other', false);
    const approachFallback = menuFallback.find((m) => m.label && m.label.startsWith('Approach'));
    assertTrue(!!approachFallback, 'Approach offered with id fallback');
});

test('scene menus gate budgeted rows on remaining turn slots (bug-562)', () => {
    const TSV = window.TurnSceneView;
    assertTrue(!!TSV, 'TurnSceneView is available');

    const way = {
        id: 'way_door_3',
        way_id: 'way_door_3',
        name: 'Sturdy Gate',
        direction: 'southwest',
        to: 'Courtyard',
        state: 'closed',
    };

    // 1. Spent major slot: { major: 0, minor: 1, free: 3 }
    const spentMajorSlots = { major: 0, minor: 1, free: 3 };
    const wayMenuSpent = TSV.buildWayMenu(way, [], 'way_other', false, spentMajorSlots);

    const examineRow = wayMenuSpent.find((m) => m.label && m.label.startsWith('Examine'));
    assertTrue(!!examineRow, 'Examine row exists');
    assertEq(examineRow.enabled, false, 'Examine is disabled when major is spent');
    assertEq(examineRow.reason, 'no major action left', 'Examine has reason');

    const goRow = wayMenuSpent.find((m) => m.label && m.label.startsWith('Go'));
    assertTrue(!!goRow, 'Go row exists');
    assertEq(goRow.enabled, false, 'Go is disabled when major is spent');
    assertEq(goRow.reason, 'no major action left', 'Go has reason');

    const dashRow = wayMenuSpent.find((m) => m.label && m.label.startsWith('Dash'));
    assertTrue(!!dashRow, 'Dash row exists');
    assertEq(dashRow.enabled, false, 'Dash is disabled when major is spent');
    assertEq(dashRow.reason, 'needs a major and a minor action', 'Dash requires major and minor');

    const approachRow = wayMenuSpent.find((m) => m.label && m.label.startsWith('Approach'));
    assertTrue(!!approachRow, 'Approach row exists');
    assertTrue(approachRow.enabled !== false, 'Approach (minor) is enabled');

    const openRow = wayMenuSpent.find((m) => m.label && m.label.startsWith('Open'));
    assertTrue(!!openRow, 'Open row exists');
    assertTrue(openRow.enabled !== false, 'Open (free) is enabled');

    // 2. Unpublished budget (turn_slots is empty object): nothing is disabled (bug-544)
    const emptySlots = {};
    const wayMenuUnpublished = TSV.buildWayMenu(way, [], 'way_other', false, emptySlots);
    for (const row of wayMenuUnpublished) {
        assertTrue(row.enabled !== false, `Row "${row.label}" should be enabled with unpublished budget`);
    }

    // 3. Null slots: nothing disabled
    const wayMenuNull = TSV.buildWayMenu(way, [], 'way_other', false, null);
    for (const row of wayMenuNull) {
        assertTrue(row.enabled !== false, `Row "${row.label}" should be enabled with null slots`);
    }

    // 4. Item menu budget gating
    const item = {
        name: 'Brass Key',
        available_actions: [
            { action: 'take', label: 'Take Brass Key', enabled: true },
            { action: 'drop', label: 'Drop Brass Key', enabled: true },
            { action: 'toggle', label: 'Turn Key', enabled: true },
        ],
    };
    const itemMenuSpent = TSV.buildItemMenu(item, false, spentMajorSlots);
    const itemExamine = itemMenuSpent.find((m) => m.label && m.label.startsWith('Examine'));
    assertEq(itemExamine.enabled, false, 'Item examine is disabled when major is spent');
    assertEq(itemExamine.reason, 'no major action left');

    const itemTake = itemMenuSpent.find((m) => m.label && m.label.startsWith('Take'));
    assertEq(itemTake.enabled, false, 'Take is disabled when major is spent');
    assertEq(itemTake.reason, 'no major action left');

    const itemToggle = itemMenuSpent.find((m) => m.label && m.label.startsWith('Turn Key'));
    assertTrue(itemToggle.enabled !== false, 'Toggle (minor) is enabled');

    const itemDrop = itemMenuSpent.find((m) => m.label && m.label.startsWith('Drop'));
    assertTrue(itemDrop.enabled !== false, 'Drop (free) is enabled');

    // 5. Person menu budget gating
    const person = { display_name: 'Cullen', name: 'Cullen' };
    const scene = { you: { conditions: [], carrying: [{ name: 'Sword' }], known_abilities: ['Heal'] } };
    const personMenuSpent = TSV.buildPersonMenu(person, scene, spentMajorSlots);

    const personExamine = personMenuSpent.find((m) => m.label && m.label.startsWith('Examine'));
    assertEq(personExamine.enabled, false, 'Person examine is disabled when major is spent');
    assertEq(personExamine.reason, 'no major action left');

    const personAttack = personMenuSpent.find((m) => m.label && m.label.startsWith('Attack'));
    assertEq(personAttack.enabled, false, 'Attack (major) is disabled when major is spent');
    assertEq(personAttack.reason, 'no major action left');

    const personWhisper = personMenuSpent.find((m) => m.label && m.label.startsWith('Whisper'));
    assertTrue(personWhisper.enabled !== false, 'Whisper (free) is enabled');

    const personGrab = personMenuSpent.find((m) => m.label && m.label.startsWith('Grab'));
    assertTrue(personGrab.enabled !== false, 'Grab (minor) is enabled');

    const personLead = personMenuSpent.find((m) => m.label && m.label.startsWith('Lead'));
    assertTrue(personLead.enabled !== false, 'Lead (minor) is enabled');

    const personGive = personMenuSpent.find((m) => m.label && m.label.startsWith('Give'));
    assertEq(personGive.enabled, false, 'Give (major) is disabled when major is spent');
    assertEq(personGive.reason, 'no major action left');

    const personTeach = personMenuSpent.find((m) => m.label && m.label.startsWith('Teach'));
    assertEq(personTeach.enabled, false, 'Teach (major) is disabled when major is spent');
    assertEq(personTeach.reason, 'no major action left');
});
