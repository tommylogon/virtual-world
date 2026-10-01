/**
 * tools/unit/test_auto_dress_selection.js
 *
 * Contracts for the LLM half of "🤖 Auto-Dress from Interests" (task-660).
 *
 * The engine cannot call a model — the keys live in the browser — so the
 * inspector runs it and posts the picks back to /api/auto_dress. That makes the
 * browser the trust boundary, and these two functions are the only thing
 * standing between a hallucinated id and an equip call.
 *
 *   1. Unvalidated picks reach the engine. The model is handed a list of
 *      library ids and will sometimes echo a display name, invent an id, or
 *      repeat itself. Every one of those is dropped rather than coerced.
 *
 *   2. The wire format is not reliable. Providers disagree about structured
 *      output, so the parser accepts the object contract, a bare array, and
 *      bracket extraction — and returns null (meaning "fall back to the
 *      deterministic path") when there is nothing parseable at all. Returning
 *      [] instead would be a lie: it means "this character wears nothing", and
 *      the caller would silently skip the fallback that would have dressed them.
 *
 * The engine re-validates against the wearable set; this is the first gate, not
 * the only one.
 */

// The runner evaluates every test file in one shared VM context, so a bare
// top-level `const` here would collide with the same binding in
// test_inspector_tag_generation.js. Scoped to keep the globals clean.
(function () {
const AV = window.InspectorAgentView;

const POOL = [
    { lib_id: 'apron', name: 'apron', tags: ['clothing'], slots: ['torso'] },
    { lib_id: 'stained_work_shirt', name: 'stained work shirt', tags: ['clothing'], slots: ['torso'] },
    { lib_id: 'hand_hammer_small', name: 'hand_hammer_small', tags: ['tool'], slots: ['hand_right'] },
];

// ──────────────────────── _validateAutoDressPicks ──────────────────────────

test('validation keeps the ids that are really in the pool', () => {
    assertEq(
        AV._validateAutoDressPicks(POOL, ['apron', 'hand_hammer_small']),
        ['apron', 'hand_hammer_small'],
        'a clean pick list passes through unchanged'
    );
});

test('validation drops an invented id', () => {
    assertEq(
        AV._validateAutoDressPicks(POOL, ['apron', 'quantum_harness']),
        ['apron'],
        'a hallucinated id is dropped, not coerced into the nearest match'
    );
});

test('validation drops display names, which are not ids', () => {
    // The model sees "apron | apron | tags | slots" and "stained_work_shirt |
    // stained work shirt | ...". A name with a space is the likeliest mistake
    // and the one that would silently equip the wrong thing.
    assertEq(
        AV._validateAutoDressPicks(POOL, ['stained work shirt']),
        [],
        'a display name is not a library id'
    );
});

test('validation de-duplicates without reordering', () => {
    assertEq(
        AV._validateAutoDressPicks(POOL, ['hand_hammer_small', 'apron', 'hand_hammer_small', 'apron']),
        ['hand_hammer_small', 'apron'],
        'the model asked for a hammer and an apron, once each, in that order'
    );
});

test('validation survives a missing or malformed pool', () => {
    assertEq(AV._validateAutoDressPicks(null, ['apron']), [], 'no pool means nothing is valid');
    assertEq(AV._validateAutoDressPicks(POOL, null), [], 'no picks is an empty answer');
    assertEq(AV._validateAutoDressPicks(POOL, [null, undefined, '']), [], 'blank entries are not ids');
});

test('an entirely invalid pick list yields empty, not a guess', () => {
    // The caller treats an empty result as "fall back to interest tags". It
    // must not substitute a nearest match: the whole failure this guards is a
    // plausible-looking wrong answer.
    assertEq(
        AV._validateAutoDressPicks(POOL, ['guiding_cane', 'ball_gag']),
        [],
        'nothing valid means nothing equipped'
    );
});

// ───────────────────────── _parseAutoDressResponse ──────────────────────────

test('parser reads the documented object contract', () => {
    assertEq(
        AV._parseAutoDressResponse('{"items": ["apron", "hand_hammer_small"]}'),
        ['apron', 'hand_hammer_small'],
        'the contract the prompt asks for'
    );
});

test('parser accepts a bare array', () => {
    assertEq(
        AV._parseAutoDressResponse('["apron"]'),
        ['apron'],
        'older model output is a raw array'
    );
});

test('parser extracts an array out of surrounding prose', () => {
    assertEq(
        AV._parseAutoDressResponse('Sure! Here you go: ["apron"] — that should work.'),
        ['apron'],
        'a chatty provider still yields its list'
    );
});

test('parser recovers from malformed JSON inside the brackets', () => {
    assertEq(
        AV._parseAutoDressResponse("['apron', hand_hammer_small]"),
        ['apron', 'hand_hammer_small'],
        'single quotes and bare words still parse'
    );
});

test('parser returns null for an unparseable response', () => {
    // null means "use the deterministic path". [] would mean "wears nothing".
    assertEq(AV._parseAutoDressResponse('I could not decide.'), null, 'prose only is not a decision');
    assertEq(AV._parseAutoDressResponse(''), null, 'empty output is not a decision');
    assertEq(AV._parseAutoDressResponse(null), null, 'a failed call is not a decision');
});

test('parser ignores an empty items object rather than inventing a fallback', () => {
    assertEq(
        AV._parseAutoDressResponse('{"items": []}'),
        [],
        'the model declined: a real answer, so no fallback'
    );
});

})();
