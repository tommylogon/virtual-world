/**
 * task-700 — plan-grounding: typed plan steps must resolve against the facts
 * the plan prompt was built from. The Vekka regression: a plan step that
 * references room-description flavor ("use hanging meat" — the meat hangs in
 * the prose but is NOT an interactable item) is REJECTED at plan time instead
 * of burning a turn on "You don't have 'hanging meat'".
 */

const FACTS_CHIEFS_PIT = {
    areaItems: ['War Drum', 'Gold Hoop Earrings (Slightly Bent)'],
    carried: [],
    people: ['the woman', 'Krikka'],
    exits: ['east passage', 'north passage', 'west passage', 'out'],
    knownAreas: ["Chief's Pit", 'Scouting Rooms', 'Raven River'],
};


test('flavor-only step is rejected (the Vekka regression)', () => {
        const r = PlanGrounding.ground(
            [{ act: 'use', item: 'hanging meat' }], FACTS_CHIEFS_PIT, "Chief's Pit");
        assertEq(r.rejections.length, 1, 'hanging meat must be rejected');
        assertTrue(/NOT interactable/i.test(r.rejections[0].reason), 'reason names the non-interactable rule');
        assertEq(r.grounded.length, 0, 'nothing grounds');
});

test('rejection reason carries the fact list so the LLM can re-compose', () => {
        const r = PlanGrounding.groundStep(
            { act: 'take', item: 'hanging meat' }, FACTS_CHIEFS_PIT, "Chief's Pit");
        assertTrue(/War Drum/.test(r), 'reason lists the interactables');
        assertTrue(/interactable/i.test(r), 'reason explains the interactable rule');
});

test('grounded steps pass and render canonically', () => {
        const steps = [
            { act: 'speak', text: 'Anyone know where I can get water around here?' },
            { act: 'go', target: 'west passage' },
            { act: 'take', item: 'Gold Hoop Earrings (Slightly Bent)' },
            { act: 'wait', until: 'dusk' },
        ];
        const r = PlanGrounding.ground(steps, FACTS_CHIEFS_PIT, "Chief's Pit");
        assertEq(r.rejections.length, 0, JSON.stringify(r.rejections));
        assertEq(r.grounded[0].text, 'speak: "Anyone know where I can get water around here?"', 'speak renders with the line');
        assertEq(r.grounded[1].text, 'go west passage', 'go renders');
        assertEq(r.grounded[2].text, 'take Gold Hoop Earrings (Slightly Bent)', 'take renders');
        assertEq(r.grounded[3].text, 'wait until dusk', 'wait renders with until');
});

test('go to an unknown place is rejected with the visible paths', () => {
        const reason = PlanGrounding.groundStep(
            { act: 'go', target: 'the moon' }, FACTS_CHIEFS_PIT, "Chief's Pit");
        assertTrue(/no such path or known area/.test(reason), 'rejection explains');
        assertTrue(/west passage/.test(reason), 'rejection lists visible paths');
});

test('go to a KNOWN area grounds even without a visible path', () => {
        const reason = PlanGrounding.groundStep(
            { act: 'go', target: 'Raven River' }, FACTS_CHIEFS_PIT, "Chief's Pit");
        assertEq(reason, null, 'known area grounds');
});

test('carried items satisfy use/take even when absent from the area', () => {
        const facts = { ...FACTS_CHIEFS_PIT, carried: ['Waterskin'] };
        assertEq(PlanGrounding.groundStep({ act: 'use', item: 'waterskin' }, facts, "Chief's Pit"), null, 'use grounds on carried');
        assertEq(PlanGrounding.groundStep({ act: 'take', item: 'Waterskin' }, facts, "Chief's Pit"), null, 'take grounds on carried');
});

test('lenient matching resolves partial references', () => {
        assertEq(
            PlanGrounding.matchFact('gold hoop', FACTS_CHIEFS_PIT.areaItems),
            'Gold Hoop Earrings (Slightly Bent)', 'partial reference resolves');
});

test('give checks carried item AND present person', () => {
        const facts = { ...FACTS_CHIEFS_PIT, carried: ['Rusty Hatchet'] };
        assertEq(
            PlanGrounding.groundStep({ act: 'give', item: 'rusty hatchet', target: 'Krikka' }, facts, "Chief's Pit"),
            null, 'valid give grounds');
        const missing = PlanGrounding.groundStep(
            { act: 'give', item: 'rusty hatchet', target: 'Thrazz' }, facts, "Chief's Pit");
        assertTrue(/no one called/.test(missing), 'absent person rejected');
});

test('unknown act fails closed', () => {
        const reason = PlanGrounding.groundStep({ act: 'teleport', target: 'anywhere' }, FACTS_CHIEFS_PIT, "Chief's Pit");
        assertTrue(/unknown act/.test(reason), 'teleport is not a plan primitive');
});

test('use_on needs both sides grounded', () => {
        const facts = { ...FACTS_CHIEFS_PIT, carried: ['kindling'] };
        assertEq(
            PlanGrounding.groundStep({ act: 'use_on', item: 'kindling', target: 'war drum' }, facts, "Chief's Pit"),
            null, 'targets resolve against area interactables');
        const bad = PlanGrounding.groundStep({ act: 'use_on', item: 'hanging meat', target: 'war drum' }, facts, "Chief's Pit");
        assertTrue(/no interactable "hanging meat"/.test(bad), 'flavor item rejected on use_on');
});

test('perform steps carry intent without fact checks', () => {
        const r = PlanGrounding.ground(
            [{ act: 'perform', note: 'mine until ore x5', until: 'ore x5' }],
            FACTS_CHIEFS_PIT, "Chief's Pit");
        assertEq(r.rejections.length, 0, 'perform carries no world reference');
        assertTrue(/perform: mine until ore x5/.test(r.grounded[0].text), 'rendered with note');
        assertTrue(/until ore x5/.test(r.grounded[0].text), 'rendered with until');
});

// ── live-run regressions (kraktooth, Rikka's held turn) ──────────────────
const FACTS_MINE_ACCESS = {
    areaItems: [],
    carried: [],
    people: ['Thrazz'],
    exits: ['upward tunnel'],
    knownAreas: ['Mine Access'],
};

test('escape and struggle are legal plan steps (a held character must be able to plan one)', () => {
    const r = PlanGrounding.ground(
        [{ act: 'escape' }, { act: 'struggle', note: 'break free of Thrazz' }],
        FACTS_MINE_ACCESS, 'Mine Access');
    assertEq(r.rejections.length, 0, 'escape/struggle carry no world reference');
    assertEq(r.grounded[0].text, 'escape', 'escape renders');
});

test('dash targets ground exactly like go', () => {
    assertEq(PlanGrounding.groundStep({ act: 'dash', target: 'upward tunnel' }, FACTS_MINE_ACCESS, 'Mine Access'), null, 'dash grounds on a visible path');
    assertTrue(/no such path/.test(PlanGrounding.groundStep({ act: 'dash', target: 'the moon' }, FACTS_MINE_ACCESS, 'Mine Access')), 'dash to nowhere is rejected');
});

test('approach resolves people and paths (the held character walking up to someone)', () => {
    assertEq(PlanGrounding.groundStep({ act: 'approach', target: 'Thrazz' }, FACTS_MINE_ACCESS, 'Mine Access'), null, 'approach grounds on a person');
    assertEq(PlanGrounding.groundStep({ act: 'approach', target: 'upward tunnel' }, FACTS_MINE_ACCESS, 'Mine Access'), null, 'approach grounds on a path');
});

test('drop resolves carried items', () => {
    const facts = { ...FACTS_MINE_ACCESS, carried: ['Rusty Hatchet'] };
    assertEq(PlanGrounding.groundStep({ act: 'drop', item: 'rusty hatchet' }, facts, 'Mine Access'), null, 'drop grounds on carried');
    assertTrue(/no interactable "war drum"/.test(PlanGrounding.groundStep({ act: 'drop', item: 'war drum' }, facts, 'Mine Access')), 'dropping scenery is rejected');
});

test('every engine verb is a legal act', () => {
    const engineVerbs = ['go', 'dash', 'crawl', 'climb', 'jump', 'take', 'drop', 'use', 'use_on',
        'examine', 'open', 'close', 'attack', 'grab', 'lead', 'escape', 'struggle', 'read', 'search',
        'look', 'listen', 'fumble', 'stand', 'rest', 'sleep', 'meditate', 'bathe', 'wait', 'relieve',
        'stow', 'put', 'combine', 'split', 'craft', 'make', 'give', 'steal', 'speak', 'perform',
        'wear', 'remove', 'approach', 'eat', 'drink'];
    const missing = engineVerbs.filter((v) => !PlanGrounding.ACTS.has(v));
    assertEq(missing.length, 0, 'plan contract missing verbs: ' + missing.join(', '));
});

test('eat and drink ground against carried or area items', () => {
    const facts = { ...FACTS_MINE_ACCESS, carried: ['woodpigeon_meat', 'spring_water'] };
    assertEq(PlanGrounding.groundStep({ act: 'eat', item: 'woodpigeon_meat' }, facts, 'Mine Access'), null, 'eat grounds on carried');
    assertEq(PlanGrounding.groundStep({ act: 'drink', item: 'spring_water' }, facts, 'Mine Access'), null, 'drink grounds on carried');
    const missing = PlanGrounding.groundStep({ act: 'eat', item: 'roast_boar' }, facts, 'Mine Access');
    assertTrue(/no interactable "roast_boar"/.test(missing), 'missing food rejected with interactable message');
});

test('collectFacts stranger masking resolves masked handles (bug-523)', () => {
    const fakeState = {
        players_in_area: [
            { name: 'Belne' },
            { name: 'Leslie', description: 'A slender dancer with auburn hair.' },
            { name: 'Mikka', aliases: ['The Viper'] },
        ],
        players: {
            Belne: { current_area: 'Mine Access' },
            Leslie: { current_area: 'Mine Access', description: 'A slender dancer with auburn hair.', tags: ['female'] },
            Mikka: { current_area: 'Mine Access', tags: ['male'], aliases: ['The Viper'] },
        },
        areas: {
            'Mine Access': {
                exits: {
                    east: { direction: 'east', way_id: 'way_1' },
                },
            },
        },
    };
    const player = { inventory: ['bread'], known: [] };

    // With PromptBuilder available
    const oldData = worldState.data;
    worldState.data = fakeState;
    try {
        const facts = PlanGrounding.collectFacts('Belne', fakeState, player, 'Mine Access');
        assertTrue(facts.people.includes('the woman') || facts.people.includes('Leslie'), 'Leslie is in people pool');
        assertTrue(facts.people.includes('The Viper'), 'Mikka alias is in people pool');
        assertEq(PlanGrounding.groundStep({ act: 'give', item: 'bread', target: 'The Viper' }, facts, 'Mine Access'), null, 'give to alias grounds');
    } finally {
        worldState.data = oldData;
    }
});

