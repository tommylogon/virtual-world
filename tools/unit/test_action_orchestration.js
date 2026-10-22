/**
 * The five orchestration defects a live mansion run exposed:
 *
 *   1. the action schema was corrupted ({"action":{"action":"take",...}}),
 *      which stringified to "[object Object]" and reached the world as a
 *      command;
 *   2. the planner and the executor disagreed about what exists (a door is a
 *      PATH, not an item, so "open dining_room_door" was rejected);
 *   3. plan repair replaced the whole plan instead of only the rejected steps;
 *   4. an engine-side failure was reported to the character as a world
 *      refusal, so they invented supernatural barriers to explain a
 *      malformed JSON payload;
 *   5. the LLM trace filed one character's prompt under another character's
 *      name.
 *
 * These tests pin the mechanisms, not the wording.
 */
'use strict';

// Every test file shares one vm context, so these names are namespaced to
// avoid colliding with the other suites' top-level bindings.
const ORCH_AN = window.ActionNormalizer;
const ORCH_RP = window.ResponseParser;
const ORCH_PG = window.PlanGrounding;

const ORCH_FACTS_FOYER = {
    areaItems: ['chandelier', 'rug', 'coat_rack', 'matches', 'dust', 'vase', 'calling_cards', 'dusty overcoat'],
    carried: ['lighter', 'hair_tie', 'lip_gloss'],
    people: ['jake halloway', 'kyrie johansen', 'sammy lopez'],
    exits: ['dining_room_door', 'front_door', 'grand_stairs', 'library_door'],
    knownAreas: ['foyer'],
};

// --- 1. action schema ---------------------------------------------------

test('a nested action object is unwrapped, not stringified', () => {
    // The exact payload from the mansion log.
    const cmd = ORCH_AN.normalizeStructuredAction({
        action: { action: 'take', item: 'lighter' },
    });
    assertEq(cmd, 'take lighter', 'nested action recovers the command');
    assertFalse(/\[object Object\]/.test(cmd), 'no stringified object reaches the command');
});

test('a nested action object keeps its own item and target', () => {
    const cmd = ORCH_AN.normalizeStructuredAction({
        action: { action: 'use_on', item: 'lighter', target: 'candle' },
    });
    assertEq(cmd, 'use lighter on candle', 'nested fields are used');
});

test('a nested action object with no verb yields no command at all', () => {
    const cmd = ORCH_AN.normalizeStructuredAction({ action: { item: 'lighter' } });
    assertEq(cmd, '', 'an unreadable action produces no command');
});

test('classifyAction separates a malformed payload from an unknown verb', () => {
    const malformed = ORCH_AN.classifyAction('[object Object]');
    assertFalse(malformed.ok, 'a stringified object is not a valid action');
    assertEq(malformed.category, 'schema_invalid', 'malformed payload is its own category');

    const unknown = ORCH_AN.classifyAction('teleport to the moon');
    assertFalse(unknown.ok, 'unknown verb is not valid');
    assertEq(unknown.category, 'unknown_verb', 'unknown verb is its own category');

    const good = ORCH_AN.classifyAction('take lighter');
    assertTrue(good.ok, 'a real command is valid');
});

test('classifyAction refuses prose masquerading as a command', () => {
    const v = ORCH_AN.classifyAction('take the command from your master');
    assertFalse(v.ok, 'prose is refused');
    assertEq(v.category, 'schema_invalid', 'prose is a schema problem, not a world problem');
});

test('parseReaction recovers a nested action without a parse error', () => {
    const raw = JSON.stringify({
        inner_monologue: 'I need the lighter.',
        action: { action: 'take', item: 'lighter' },
    });
    const p = ORCH_RP.parseReaction(raw);
    assertEq(p.action, 'take lighter', 'the command is recovered');
    assertFalse(p.parseError, 'a recoverable nesting is not an error');
});

test('parseReaction flags an unreadable action as a schema error', () => {
    const raw = JSON.stringify({ inner_monologue: 'hmm', action: { item: 'lighter' } });
    const p = ORCH_RP.parseReaction(raw);
    assertTrue(p.parseError, 'the schema error surfaces');
    assertTrue(/schema_invalid/.test(p.parseError), 'the category is named');
    assertEq(p.action, '', 'no command is produced from an unreadable action');
});

// --- 2. typed target grounding -------------------------------------------

test('a door is a PATH, so open/close ground against the exit list', () => {
    // The exact rejection from the mansion log: the prompt listed the door
    // under "paths", the validator only consulted the item pool.
    assertEq(
        ORCH_PG.groundStep({ act: 'open', target: 'dining_room_door' }, ORCH_FACTS_FOYER, 'foyer'),
        null,
        'opening a listed door grounds',
    );
    assertEq(
        ORCH_PG.groundStep({ act: 'close', target: 'front_door' }, ORCH_FACTS_FOYER, 'foyer'),
        null,
        'closing a listed door grounds',
    );
});

test('open still refuses a door that is not here', () => {
    // The matcher is deliberately lenient (it resolves "gold hoop" to "Gold
    // Hoop Earrings"), so the probe here shares NO word with a real path.
    const reason = ORCH_PG.groundStep({ act: 'open', target: 'cellar_hatch' }, ORCH_FACTS_FOYER, 'foyer');
    assertTrue(reason !== null, 'an unlisted door is rejected');
    assertTrue(/paths from here/.test(reason), 'the rejection names the path list');
});

test('search needs a thing, and the reason teaches the go-then-look route', () => {
    const reason = ORCH_PG.groundStep({ act: 'search', area: 'dining room door' }, ORCH_FACTS_FOYER, 'foyer');
    assertTrue(reason !== null, 'a place is not a searchable thing');
    assertTrue(/go.*there first/i.test(reason), 'the reason teaches the correct route');
});

test('search still grounds on a real item', () => {
    assertEq(
        ORCH_PG.groundStep({ act: 'search', item: 'coat_rack' }, ORCH_FACTS_FOYER, 'foyer'),
        null,
        'searching a listed item grounds',
    );
});

test('room-description scenery stays unsearchable', () => {
    const reason = ORCH_PG.groundStep({ act: 'search', item: 'dining table' }, ORCH_FACTS_FOYER, 'foyer');
    assertTrue(reason !== null, 'a described-but-unlisted table is rejected');
    assertTrue(/NOT interactable/i.test(reason), 'the reason states the rule');
});

test('take still refuses a path', () => {
    const reason = ORCH_PG.groundStep({ act: 'take', item: 'front_door' }, ORCH_FACTS_FOYER, 'foyer');
    assertTrue(reason !== null, 'a door is not takeable');
});

// --- 3. plan repair is constrained ---------------------------------------

test('ground reports the index of every step, so a repair can be positional', () => {
    const r = ORCH_PG.ground(
        [
            { act: 'go', target: 'dining_room_door' },
            { act: 'search', item: 'dining table' },
        ],
        ORCH_FACTS_FOYER,
        'foyer',
    );
    assertEq(r.grounded.length, 1, 'one step grounds');
    assertEq(r.grounded[0].index, 0, 'the grounded step knows its position');
    assertEq(r.rejections[0].index, 1, 'the rejected step knows its position');
});

test('the plan verb list cannot drift from the executor registry', () => {
    // Every plan verb the executor does not know would be a command the
    // engine rejects at action time.
    const registry = window.ActionVerbs;
    if (!registry) return; // registry not loaded in this sandbox - nothing to compare
    const known = registry.VALID_SET || new Set(registry.VALID_VERBS || []);
    const drifting = [...ORCH_PG.ACTS].filter((v) => v !== 'perform' && !known.has(v));
    assertEq(drifting.length, 0, 'plan verbs missing from the executor registry: ' + drifting.join(', '));
});

test('a repair keeps the steps that already grounded', () => {
    // The mansion failure: the plan was "approach the dining room / search
    // the table", the repair produced "take lighter / go west passage", and
    // the character abandoned a verified step.
    const original = [
        { act: 'go', target: 'dining_room_door' },
        { act: 'search', item: 'dining table' },
    ];
    const originalResult = ORCH_PG.ground(original, ORCH_FACTS_FOYER, 'foyer');
    assertEq(originalResult.grounded.length, 1, 'one step grounds');
    assertEq(originalResult.rejections.length, 1, 'one step is rejected');

    // A repair that ignores the contract and returns something else entirely.
    const repaired = [
        { act: 'take', item: 'lighter' },
        { act: 'go', target: 'front_door' },
    ];
    const repairedResult = ORCH_PG.ground(repaired, ORCH_FACTS_FOYER, 'foyer');

    const merged = window.PlanManager._mergeWithPreserved(
        repairedResult.grounded,
        original,
        originalResult.grounded,
        ORCH_PG,
        ORCH_FACTS_FOYER,
        'foyer',
    );
    const texts = merged.map((m) => m.text);
    assertTrue(texts.includes('go dining_room_door'),
        'the verified step survives a repair that ignored the contract');
});

test('a repair fills a rejected position with a step that grounds', () => {
    const original = [
        { act: 'go', target: 'dining_room_door' },
        { act: 'search', item: 'dining table' },
    ];
    const originalResult = ORCH_PG.ground(original, ORCH_FACTS_FOYER, 'foyer');
    const repaired = [
        { act: 'go', target: 'dining_room_door' },
        { act: 'examine', item: 'coat_rack' },
    ];
    const repairedResult = ORCH_PG.ground(repaired, ORCH_FACTS_FOYER, 'foyer');
    const merged = window.PlanManager._mergeWithPreserved(
        repairedResult.grounded,
        original,
        originalResult.grounded,
        ORCH_PG,
        ORCH_FACTS_FOYER,
        'foyer',
    );
    const texts = merged.map((m) => m.text);
    assertEq(texts.length, 2, 'the plan keeps its length');
    assertTrue(texts.includes('go dining_room_door'), 'the verified step is kept');
    assertTrue(texts.includes('examine coat_rack'), 'the rejected position is filled with a grounded step');
});

test('a repair cannot introduce a step that does not ground', () => {
    const original = [
        { act: 'go', target: 'dining_room_door' },
        { act: 'search', item: 'dining table' },
    ];
    const originalResult = ORCH_PG.ground(original, ORCH_FACTS_FOYER, 'foyer');
    // The repair invents scenery again.
    const repaired = [
        { act: 'go', target: 'dining_room_door' },
        { act: 'search', item: 'dining table' },
    ];
    const repairedResult = ORCH_PG.ground(repaired, ORCH_FACTS_FOYER, 'foyer');
    const merged = window.PlanManager._mergeWithPreserved(
        repairedResult.grounded,
        original,
        originalResult.grounded,
        ORCH_PG,
        ORCH_FACTS_FOYER,
        'foyer',
    );
    for (const m of merged) {
        assertEq(ORCH_PG.groundStep(m.step, ORCH_FACTS_FOYER, 'foyer'), null, 'every merged step grounds: ' + m.text);
    }
});

test('the repair prompt shows the model which steps to keep', () => {
    const original = [
        { act: 'go', target: 'dining_room_door' },
        { act: 'search', item: 'dining table' },
    ];
    const result = ORCH_PG.ground(original, ORCH_FACTS_FOYER, 'foyer');
    const prompt = window.PlanManager._buildRepairPrompt(
        ORCH_PG, original, result.grounded, result.rejections, ORCH_FACTS_FOYER);
    assertTrue(/\[KEEP\]/.test(prompt), 'the prompt marks the steps to keep');
    assertTrue(/\[REJECTED\]/.test(prompt), 'the prompt marks the steps to replace');
    assertTrue(/go dining_room_door/.test(prompt), 'the prompt shows the kept step verbatim');
    assertTrue(/dining table/.test(prompt), 'the prompt shows the rejected step');
    assertTrue(/Reproduce every \[KEEP\] step EXACTLY/.test(prompt), 'the prompt states the contract');
});

// --- 4. the failure text tells the character the truth --------------------

test('a malformed command is reported as a malformed command', () => {
    const text = ORCH_AN.rejectionText('schema_invalid', '[object Object]');
    assertTrue(/malformed/i.test(text), 'the character is told the command was malformed');
    assertFalse(/you can't do that/i.test(text), 'the world is not blamed');
    assertTrue(/never reached the world/i.test(text), 'the truth is that nothing happened');
});

test('an unknown verb is reported as an unknown verb', () => {
    const text = ORCH_AN.rejectionText('unknown_verb', 'teleport to the moon');
    assertTrue(/not something you know how to do/i.test(text), 'the verb is named as unknown');
    assertFalse(/malformed/i.test(text), 'not confused with a malformed command');
});

test('the rejection text never invents a world obstruction', () => {
    for (const cat of ['schema_invalid', 'unknown_verb']) {
        const text = ORCH_AN.rejectionText(cat, 'x');
        assertFalse(/blocked|barrier|forbid|won't let|cannot go through/i.test(text),
            'category ' + cat + ' must not read as a world obstruction');
    }
});

test('every failure category has a text', () => {
    for (const cat of ['schema_invalid', 'unknown_verb', 'empty']) {
        const text = ORCH_AN.rejectionText(cat, 'x');
        assertTrue(typeof text === 'string' && text.length > 0, 'category ' + cat + ' has text');
    }
});

// --- 5. trace correlation -------------------------------------------------

test('the export carries the actor the LLM call was actually for', () => {
    // The bug: the chip took its actor from "whose turn is it", so a prompt
    // written for one character was filed under another one's name. The
    // export has to carry the real actor, not just the display label.
    const E = window.EventLogExport;
    assertTrue(E, 'the export module is loaded');

    const bubble = {
        tagName: 'DIV',
        children: [],
        style: {},
        dataset: {},
        textContent: 'LLM -> think-decide',
        classList: (() => {
            const s = new Set(['msg-bubble', 'msg-bubble-rawllm']);
            s.contains = (c) => s.has(c);
            return s;
        })(),
        _attrs: {
            'data-seq': '3',
            'data-actor': 'jake halloway',
            'data-actor-id': 'kayla jenkins',
            'data-request-id': 'think-decide-123-abc',
            'data-phase': 'think-decide',
            'data-tick': '0',
            'data-type': 'rawllm',
            'data-stream-area': 'foyer',
        },
        getAttribute(n) { return n in this._attrs ? this._attrs[n] : null; },
        setAttribute(n, v) { this._attrs[n] = String(v); },
        querySelector(sel) {
            if (sel === '.rawllm-chip-header') {
                return { textContent: 'LLM -> think-decide ~1.8k tok' };
            }
            return null;
        },
    };
    const stream = {
        tagName: 'DIV',
        children: [bubble],
        style: {},
        dataset: {},
        textContent: '',
        classList: (() => { const s = new Set(); s.contains = () => false; return s; })(),
        getAttribute() { return null; },
        setAttribute() {},
        querySelector() { return null; },
    };

    const rows = E.projectStreamRows(stream, {});
    assertEq(rows.length, 1, 'one row projected');
    assertEq(rows[0].actor_id, 'kayla jenkins', 'the real actor is carried');
    assertEq(rows[0].request_id, 'think-decide-123-abc', 'the request id is carried');
    assertEq(rows[0].phase, 'think-decide', 'the phase is carried');
    assertEq(rows[0].actor, 'jake halloway', 'the display label is unchanged');
});
