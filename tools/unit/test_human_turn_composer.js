/**
 * Unit tests for HumanTurnComposer command parsing and speech feedback (task-878).
 */

const HTC = window.HumanTurnComposer;

test('parseCmd parses known action verbs with items and targets', () => {
    assertEq(HTC.parseCmd('look'), { action: 'look' }, 'simple verb');
    assertEq(HTC.parseCmd('go north'), { action: 'go', item: 'north' }, 'verb + direction');
    assertEq(HTC.parseCmd('take rusty sword'), { action: 'take', item: 'rusty sword' }, 'verb + item');
    assertEq(HTC.parseCmd('give bread to Lyrie'), { action: 'give', item: 'bread', target: 'Lyrie' }, 'give item to target');
    assertEq(HTC.parseCmd('use key on door'), { action: 'use', item: 'key', target: 'door' }, 'use item on target');
});

test('parseCmd treats volume prefixes as speech with volume', () => {
    assertEq(HTC.parseCmd('whisper hello there'), { speech: 'hello there', volume: 'whisper' }, 'whisper');
    assertEq(HTC.parseCmd('shout watch out!'), { speech: 'watch out!', volume: 'shout' }, 'shout');
    assertEq(HTC.parseCmd('scream help!'), { speech: 'help!', volume: 'scream' }, 'scream');
});

test('parseCmd treats unknown verbs as speech', () => {
    assertEq(HTC.parseCmd('walk over to the counter'), { speech: 'walk over to the counter' }, 'walk is not in VERBS');
    assertEq(HTC.parseCmd('hello friend'), { speech: 'hello friend' }, 'greetings are speech');
});

test('doHint provides warning and suggestions when text in do field will be spoken (task-878)', () => {
    // Known actions show NO hint
    assertEq(HTC.doHint('go north'), null, 'known action go has no hint');
    assertEq(HTC.doHint('take sword'), null, 'known action take has no hint');
    assertEq(HTC.doHint('attack goblin'), null, 'known action attack has no hint');
    assertEq(HTC.doHint(''), null, 'empty input has no hint');

    // Deliberate speech with volume words shows NO hint
    assertEq(HTC.doHint('whisper hello'), null, 'whisper is deliberate speech');
    assertEq(HTC.doHint('shout behind you'), null, 'shout is deliberate speech');
    assertEq(HTC.doHint('scream'), null, 'bare volume word has no hint');

    // Unknown verbs that will be spoken show warning and alias suggestions
    const walkHint = HTC.doHint('walk to the bar');
    assertTrue(walkHint !== null, 'walk shows a hint');
    assertTrue(walkHint.indexOf('will be spoken aloud') >= 0, 'hint warns that line will be spoken');
    assertTrue(walkHint.indexOf('go') >= 0, 'hint suggests "go" for walk');

    const hitHint = HTC.doHint('hit goblin with rock');
    assertTrue(hitHint !== null, 'hit shows a hint');
    assertTrue(hitHint.indexOf('attack') >= 0, 'hint suggests "attack" for hit');

    const consumeHint = HTC.doHint('consume potion');
    assertTrue(consumeHint !== null, 'consume shows a hint');
    assertTrue(consumeHint.indexOf('eat, drink') >= 0, 'hint suggests eat/drink for consume');
});

test('the human turn composer wires htc-do-hint in template and input listener (task-878)', () => {
    const src = window.__readFile('static/js/agent/human-turn-composer.js');
    assertTrue(/id="htc-do-hint"/.test(src), 'template includes htc-do-hint container');
    assertTrue(/addEventListener\('input',\s*updateDoHint\)/.test(src), 'htc-do input event updates hint');
    assertTrue(/function doHint\s*\(/.test(src), 'doHint helper function is defined');
});

// -- task-698: React phase preview affordance --

test('HumanTurnComposer exports preview for e2e and dev replay (task-698)', () => {
    assertTrue(typeof HTC.preview === 'function', 'HTC.preview is exported');
    const src = window.__readFile('static/js/agent/human-turn-composer.js');
    assertTrue(/function preview\s*\(charName,\s*results\)/.test(src), 'preview function is defined');
    assertTrue(/_dryRun\s*=\s*true/.test(src), 'preview sets dry-run flag');
    assertTrue(/if\s*\(_dryRun\)\s*\{[^}]*return;?\s*\}/.test(src), 'finishReact guards dry-run dismissal');
    assertTrue(/return\s*\{[^}]*preview/.test(src), 'preview is returned in module export');
});

// -- task-679: React-phase result parsing and formatting --

test('parseResultText separates movement, prose, exits, people and status lines (task-679)', () => {
    const raw = `You head through the grand_stairs. - you're in upstairs hall.
The light is dim - you can just make out the shapes of things here, details lost in shadow.
[grand_stairs_back] foyer is visible beyond (dimly lit, cool).
[master_bedroom_door] a large oak door with brass filigree. It is currently closed.
[guest_room1_door] a simple painted door.
kayla jenkins - a sixteen-year-old with dark hair is wearing black crop top on their torso. [wearing: black crop top, denim cut-offs] [holding: nothing] at the rug
miki - a bubbly twenty-something [wearing: oversized hoodie] [holding: phone]
[!] The air is stale and making you tired.`;

    const parsed = HTC.parseResultText(raw);

    // Movement line separated
    assertEq(parsed.actionLine, "You head through the grand_stairs. - you're in upstairs hall.");

    // Prose separated
    assertEq(parsed.proseLines.length, 1);
    assertTrue(parsed.proseLines[0].indexOf("The light is dim") >= 0);

    // Ways and character full descriptions collapsed into rawTailLines
    assertEq(parsed.rawTailLines.length, 5);
    assertTrue(parsed.rawTailLines[0].indexOf("[grand_stairs_back]") >= 0);
    assertTrue(parsed.rawTailLines[1].indexOf("[master_bedroom_door]") >= 0);
    assertTrue(parsed.rawTailLines[2].indexOf("[guest_room1_door]") >= 0);
    assertTrue(parsed.rawTailLines[3].indexOf("kayla jenkins") >= 0);
    assertTrue(parsed.rawTailLines[4].indexOf("miki") >= 0);

    // Character names summarized
    assertEq(parsed.peopleSummary.length, 2);
    assertTrue(parsed.peopleSummary.includes("kayla jenkins"));
    assertTrue(parsed.peopleSummary.includes("miki"));

    // Status effect lines parsed
    assertEq(parsed.statusLines.length, 1);
    assertEq(parsed.statusLines[0], "The air is stale and making you tired.");
});

test('parseResultText handles simple action result with no tail (task-679)', () => {
    const raw = "You pick up the iron key.";
    const parsed = HTC.parseResultText(raw);
    assertEq(parsed.actionLine, "You pick up the iron key.");
    assertEq(parsed.proseLines.length, 0);
    assertEq(parsed.rawTailLines.length, 0);
    assertEq(parsed.statusLines.length, 0);
    assertEq(parsed.peopleSummary.length, 0);
});

test('the human turn composer defines structured result styles and expand toggle (task-679)', () => {
    const src = window.__readFile('static/js/agent/human-turn-composer.js');
    assertTrue(/htc-res-action/.test(src), 'css includes htc-res-action');
    assertTrue(/htc-res-prose/.test(src), 'css includes htc-res-prose');
    assertTrue(/htc-res-details/.test(src), 'css includes htc-res-details disclosure');
    assertTrue(/htc-res-toggle-expand/.test(src), 'css includes htc-res-toggle-expand');
    assertTrue(/max-height:\s*160px/.test(src), 'htc-result has max-height clamp');
});

// -- bug-580: Fresh turn start renders full budget instead of 0 major / 0 minor / 0 free --

test('HumanTurnComposer renders full budget pips on fresh turn start, updates on partial spend, and shows 0 when genuinely spent (bug-580)', () => {
    function makeBudgetNode(id) {
        return {
            id,
            children: [],
            style: {},
            textContent: '',
            replaceChildren() {
                this.children = [];
                this.textContent = '';
            },
            appendChild(child) {
                this.children.push(child);
                return child;
            },
            append(...items) {
                for (const it of items) {
                    this.children.push(it);
                }
                this.textContent = this.children
                    .map((c) => (typeof c === 'string' ? c : (c && c.textContent) || ''))
                    .join('');
            },
        };
    }

    const pipsEl = makeBudgetNode('htc-pips');
    const budgetEl = makeBudgetNode('htc-budgetlab');
    const overlayEl = { id: 'htc-overlay', style: { display: 'none' } };
    const origQS = document.querySelector;
    const origGetById = document.getElementById;
    const origRuntimePlayer = window.worldState && window.worldState.runtimePlayer;
    let currentSlots = {};

    document.querySelector = (sel) => {
        if (sel === '#htc-pips') return pipsEl;
        if (sel === '#htc-budgetlab') return budgetEl;
        if (sel === '#htc-overlay') return overlayEl;
        return origQS ? origQS.call(document, sel) : null;
    };
    document.getElementById = (id) => {
        if (id === 'htc-pips') return pipsEl;
        if (id === 'htc-budgetlab') return budgetEl;
        if (id === 'htc-overlay') return overlayEl;
        return origGetById ? origGetById.call(document, id) : null;
    };
    window.worldState = window.worldState || {};
    window.worldState.runtimePlayer = () => ({ turn_slots: currentSlots });

    try {
        // 1. Fresh turn start: turn_slots is {} (uninitialized)
        currentSlots = {};
        HTC.open('jake halloway');
        assertEq(budgetEl.textContent, '1 major · 1 minor · 3 free', 'fresh turn ({}) renders full budget text');
        assertEq(pipsEl.children.length, 5, '5 pips rendered on fresh turn');
        const freshSpentCount = pipsEl.children.filter((c) => /\bspent\b/.test(c.className || '')).length;
        assertEq(freshSpentCount, 0, 'all 5 pips are unspent when turn_slots is {}');

        // Also verify when turn_slots is undefined/absent
        currentSlots = undefined;
        HTC.open('jake halloway');
        assertEq(budgetEl.textContent, '1 major · 1 minor · 3 free', 'absent turn_slots renders full budget text');
        assertEq(pipsEl.children.filter((c) => /\bspent\b/.test(c.className || '')).length, 0, 'all 5 pips unspent when turn_slots is absent');

        // 2. Partial spend: major spent, 1 minor and 2 free remaining
        currentSlots = { major: 0, minor: 1, free: 2 };
        HTC.open('jake halloway');
        assertEq(budgetEl.textContent, '0 major · 1 minor · 2 free', 'partial spend updates budget label dynamically');
        assertTrue(/\bspent\b/.test(pipsEl.children[0].className), 'major pip marked spent');
        assertFalse(/\bspent\b/.test(pipsEl.children[1].className), 'minor pip remains unspent');
        assertFalse(/\bspent\b/.test(pipsEl.children[2].className), 'free pip 1 remains unspent');
        assertFalse(/\bspent\b/.test(pipsEl.children[3].className), 'free pip 2 remains unspent');
        assertTrue(/\bspent\b/.test(pipsEl.children[4].className), 'free pip 3 marked spent');

        // 3. All actions genuinely spent: turn_slots is { major: 0, minor: 0, free: 0 }
        currentSlots = { major: 0, minor: 0, free: 0 };
        HTC.open('jake halloway');
        assertEq(budgetEl.textContent, '0 major · 0 minor · 0 free', 'exhausted budget renders 0 major · 0 minor · 0 free');
        const allSpentCount = pipsEl.children.filter((c) => /\bspent\b/.test(c.className || '')).length;
        assertEq(allSpentCount, 5, 'all 5 pips marked spent when budget is genuinely 0');
    } finally {
        HTC.closeTurn();
        document.querySelector = origQS;
        document.getElementById = origGetById;
        if (origRuntimePlayer !== undefined) {
            window.worldState.runtimePlayer = origRuntimePlayer;
        } else {
            delete window.worldState.runtimePlayer;
        }
    }
});
