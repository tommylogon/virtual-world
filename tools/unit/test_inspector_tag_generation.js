/**
 * tools/unit/test_inspector_tag_generation.js
 *
 * Three contracts for "✨ / 😨 Generate from Personality":
 *
 *   1. It ADDS. A tag someone typed into the multiselect is authoring and the
 *      LLM has no way to know it mattered, so generation unions its picks into
 *      what is already there. The bug this guards: the generators used to POST
 *      the picks as the whole field, so one click silently destroyed every
 *      hand-placed tag.
 *
 *   2. The model is NOT shown a tag menu. The vocabulary is grounding material
 *      on this side of the boundary, not prompt material: the menu was 660 ids
 *      and cost more tokens than the character description, and the model
 *      picked from it by resemblance rather than by what the character wanted.
 *
 *   3. Resolution is deterministic and reports what will actually work. A tag
 *      nothing carries looks identical to a live one in the multiselect, so the
 *      live / idle split is stated when the tags are created.
 *
 * The union deliberately lives in the generator and NOT in the REST field
 * write (`routes/player_ops.py` assigns the posted list verbatim), otherwise
 * a tag could never be removed by hand.
 */

const AV = window.InspectorAgentView;

// ─────────────────────────── the union itself ───────────────────────────────

test('merge keeps hand-placed tags and appends the new picks', () => {
    assertEq(
        AV._mergeGeneratedTags(['ruins', 'silver'], ['books', 'magic']),
        ['ruins', 'silver', 'books', 'magic'],
        'hand-placed tags survive a generate'
    );
});

test('merge preserves the existing order and spelling', () => {
    assertEq(
        AV._mergeGeneratedTags(['Ruins', 'SILVER'], ['books']),
        ['Ruins', 'SILVER', 'books'],
        'existing entries keep position and casing'
    );
});

test('merge does not duplicate a pick the human already placed', () => {
    assertEq(
        AV._mergeGeneratedTags(['goblins'], ['Goblins', 'ruins']),
        ['goblins', 'ruins'],
        'case-insensitive dedupe: one goblins entry, not two'
    );
});

test('merge drops blanks and copes with a missing list', () => {
    assertEq(AV._mergeGeneratedTags(['ruins', '  ', ''], ['', 'books']), ['ruins', 'books'], 'blanks dropped');
    assertEq(AV._mergeGeneratedTags(undefined, ['books']), ['books'], 'no existing list is not an error');
    assertEq(AV._mergeGeneratedTags(['ruins'], undefined), ['ruins'], 'no picks is not an error');
});

// ───────────────────── id normalization: known ids pass through ────────────
//
// The real data contains ids outside [a-z0-9_-]: faction:goblin,
// held_by:goblin, taco bell. An earlier normalizer rewrote them to
// faction-goblin, and the prompt then offered the model ids that cannot match
// anything while claiming they were in use.

test('a known id is passed through untouched, punctuation and all', () => {
    const known = new Set(['faction:goblin', 'held_by:goblin', 'taco bell']);
    assertEq(AV._normalizeGeneratedTag('Faction:Goblin', known), 'faction:goblin', 'colon id survives');
    assertEq(AV._normalizeGeneratedTag('held_by:goblin', known), 'held_by:goblin', 'underscore id survives');
    assertEq(AV._normalizeGeneratedTag('Taco Bell', known), 'taco bell', 'spaced id survives');
});

test('an invented id is reshaped into a usable one', () => {
    const known = new Set(['tool']);
    assertEq(AV._normalizeGeneratedTag('The Dark!', known), 'the-dark', 'capitalised and punctuated');
    assertEq(AV._normalizeGeneratedTag('  Old   Tomes  ', known), 'old-tomes', 'whitespace collapses');
    assertEq(AV._normalizeGeneratedTag('!!!', known), '', 'nothing usable left is dropped');
});

// ───────────────────── grounding concepts onto real ids ─────────────────────

const VOCAB = {
    live: new Set(['tool', 'coin', 'metal', 'shiny', 'food', 'goblin', 'chief', 'worg', 'trap']),
    library: new Set(['book', 'jewelry', 'mechanism', 'creature', 'danger']),
    known: null
};
VOCAB.known = new Set([...VOCAB.live, ...VOCAB.library]);

test('a plural resolves to the singular that actually exists', () => {
    assertEq(AV._resolveConcept('tools', VOCAB).map(r => r.id), ['tool'], 'tools -> tool');
    assertEq(AV._resolveConcept('mechanisms', VOCAB).map(r => r.id), ['mechanism'], 'mechanisms -> mechanism');
});

test('a concept with nothing real becomes a new id, not a guess', () => {
    const hit = AV._resolveConcept('weapons', VOCAB);
    assertEq(hit.map(r => [r.id, r.status]), [['weapons', 'new']],
        'nothing matches, so it is kept as a new id and the caller reports it as carrying nothing');
});

test('a noun phrase resolves to its head noun', () => {
    assertEq(AV._resolveConcept('worn iron tools', VOCAB).map(r => r.id), ['tool'], 'adjective dropped');
    assertEq(AV._resolveConcept('a good blade', VOCAB).map(r => r.id), ['blade'], 'unmatched head kept as a new id');
});

test('one concept naming two real things yields both ids', () => {
    assertEq(AV._resolveConcept('a goblin chief', VOCAB).map(r => r.id), ['goblin', 'chief'],
        '"a goblin chief" names two things that are both real');
});

test('an id with no singular is never mangled into a similar one', () => {
    // difflib at cutoff 0.6 suggests wanderer -> underwear and fear -> footwear.
    // Resolution must not repeat that mistake.
    const vocab = { live: new Set(['underwear', 'footwear']), library: new Set(), known: new Set(['underwear', 'footwear']) };
    assertEq(AV._resolveConcept('wanderer', vocab).map(r => r.id), ['wanderer'], 'wanderer stays wanderer');
    assertEq(AV._resolveConcept('fear', vocab).map(r => r.id), ['fear'], 'fear stays fear');
});

test('resolution reports live, library-only and new', () => {
    assertEq(AV._resolveConcept('shiny', VOCAB).map(r => r.status), ['live'], 'carried right now');
    assertEq(AV._resolveConcept('jewelry', VOCAB).map(r => r.status), ['library'], 'a real id nothing carries');
    assertEq(AV._resolveConcept('wyrm scales', VOCAB).map(r => r.status), ['new'], 'nothing real at all');
});

test('an empty concept resolves to nothing rather than to a blank id', () => {
    assertEq(AV._resolveConcept('', VOCAB), [], 'empty');
    assertEq(AV._resolveConcept('   ', VOCAB), [], 'whitespace');
    assertEq(AV._resolveConcept(undefined, VOCAB), [], 'missing');
});

// ───────────────────────────── the live split ───────────────────────────────

test('a character tag is live for a fear and idle for an interest', () => {
    // The two fields are matched against different things, so "live" is
    // computed from different vocabularies. This is the whole reason
    // _collectItemTags exists.
    const itemTags = new Set(['tool', 'coin']);
    const library = new Set([...VOCAB.library, 'goblin']);   // a real id, no item carries it
    const known = new Set([...itemTags, ...VOCAB.live, ...library]);
    const asInterest = AV._resolveConcept('goblin', { live: itemTags, library, known });
    const asFear = AV._resolveConcept('goblin', { live: VOCAB.live, library, known });
    assertEq(asInterest.map(r => r.status), ['library'], 'no item is tagged goblin, so the interest cannot surface');
    assertEq(asFear.map(r => r.status), ['live'], 'goblins are present, so the fear bites');
});

test('item tags are read from the id-keyed object the endpoint actually returns', async () => {
    // GET /api/library/items answers {acorn: {...}, adze: {...}, ...}, not a
    // list. The original generator read it as an array, silently got an empty
    // set, and fell through to its graph fallback — so for a while the
    // "library vocabulary" it offered the model was never the library at all.
    window.fetch = (url) => {
        if (url === '/api/library/items') {
            return Promise.resolve({ json: () => Promise.resolve({
                acorn: { tags: ['food', 'plant'] },
                adze: { tags: ['Tool', 'scrap'] }
            }) });
        }
        if (url === '/api/tags/search') {
            return Promise.resolve({ json: () => Promise.resolve([{ id: 'food' }]) });
        }
        throw new Error(`unexpected fetch: ${url}`);
    };
    assertEq([...(await AV._collectItemTags())].sort(), ['food', 'plant', 'scrap', 'tool'],
        '439 item tags in the real library, not zero');
});

// ───────────────── the write that follows an LLM round-trip ─────────────────

/**
 * Drive a full generate with fake llmClient / ApiClient and report what was
 * POSTed, plus the prompt the model was shown.
 */
async function runGenerate(opts) {
    const sent = [];
    const toasts = [];
    let prompt = '';
    const live = new Set(opts.live || []);
    const library = new Set(opts.library || []);
    const known = new Set([...live, ...library]);
    // This helper replaces module singletons on the shared sandbox. Every test
    // file runs in ONE vm context and load order is alphabetical, so without a
    // restore a later file inherits the fake — which is exactly how
    // test_llm_truncation.js ended up asserting against a stub with no methods.
    const saved = {};
    for (const key of ['worldState', 'AIGenerator', 'llmClient', 'ApiClient', 'toastSuccess', 'toastWarning', 'toastError', 'VW']) {
        saved[key] = window[key];
    }
    try {
        window.worldState.players = { Test: { personality: 'wary and desperate', description: 'a hardened traveller' } };
        window.worldState.data = { graph: { nodes: {} } };
        window.worldState.fetch = () => Promise.resolve();
        window.AIGenerator = { isConfigured: () => true };
        window.llmClient = {
            chat: (messages) => { prompt = messages[0].content; return Promise.resolve(JSON.stringify({ tags: opts.concepts })); }
        };
        window.ApiClient = {
            updateCharacter: (name, data) => { sent.push({ name, data }); return Promise.resolve(); }
        };
        window.toastSuccess = (m) => toasts.push(m);
        window.toastWarning = () => {};
        window.toastError = () => {};
        window.VW = undefined;                       // skip the inspector re-open

        await opts.run('Test', { live, library, known });
        return { sent, toasts, get prompt() { return prompt; } };
    } finally {
        for (const key of Object.keys(saved)) window[key] = saved[key];
    }
}

test('generate posts hand-placed tags alongside the picks', async () => {
    const { sent } = await runGenerate({
        live: ['tool', 'coin'],
        library: ['book'],
        concepts: ['iron tools', 'coarse bread'],
        run: (name, vocab) => {
            // RETURNED, not fired-and-forgotten: runGenerate restores the
            // sandbox globals in a finally block, so an un-awaited generate
            // would emit its toast after the stubs are gone.
            return window.InspectorAgentView._generateTagsFromPersonality({
                charName: name, field: 'interest_tags', vocab, limit: 8,
                contextNote: 'items', ask: 'what would they seek?', toastPrefix: 'Interest tags'
            });
        }
    });
    assertEq(sent.length, 1, 'exactly one write');
    assertEq(sent[0].data.interest_tags, ['tool', 'bread'], 'hand-placed tool kept, bread added as new');
});

test('the prompt carries no tag menu at all', async () => {
    const { prompt } = await runGenerate({
        live: ['tool'], library: ['book', 'jewelry', 'mechanism'], concepts: ['tool'],
        run: (name, vocab) => {
            // RETURNED, not fired-and-forgotten: runGenerate restores the
            // sandbox globals in a finally block, so an un-awaited generate
            // would emit its toast after the stubs are gone.
            return window.InspectorAgentView._generateTagsFromPersonality({
                charName: name, field: 'interest_tags', vocab, limit: 8,
                contextNote: 'items', ask: 'what would they seek?', toastPrefix: 'Interest tags'
            });
        }
    });
    assertFalse(prompt.includes('jewelry'), 'a library id that was not picked is absent from the prompt');
    assertFalse(prompt.includes('ALREADY IN USE'), 'no vocabulary listing');
    assertFalse(prompt.includes('mechanism'), 'another unused library id is absent too');
    assertTrue(prompt.includes('wary and desperate'), 'the character still leads the prompt');
    assertTrue(/short, plain noun phrases/.test(prompt), 'the model is asked for concepts, not menu ids');
});

test('the toast says which picks cannot work yet', async () => {
    const { sent, toasts } = await runGenerate({
        live: ['tool'], library: ['book'], concepts: ['tools', 'jewelry', 'wyrm scales'],
        run: (name, vocab) => {
            // RETURNED, not fired-and-forgotten: runGenerate restores the
            // sandbox globals in a finally block, so an un-awaited generate
            // would emit its toast after the stubs are gone.
            return window.InspectorAgentView._generateTagsFromPersonality({
                charName: name, field: 'interest_tags', vocab, limit: 8,
                contextNote: 'items', ask: 'what would they seek?', toastPrefix: 'Interest tags'
            });
        }
    });
    assertEq(sent[0].data.interest_tags, ['tool', 'jewelry', 'scales'], 'plural grounded, then two new ids');
    const said = toasts.join(' | ');
    assertTrue(/1 matches something here/.test(said), 'the live one is reported as live');
    assertTrue(/2 nothing carries yet: jewelry, scales/.test(said), 'the idle ones are named');
});

// ─────────────────────────── the fear generator ─────────────────────────────

test('fear generate keeps hand-placed fears and grounds against the world', async () => {
    const { sent, toasts } = await runGenerate({
        live: ['goblin', 'chief'], library: ['creature'],
        concepts: ['a goblin chief', 'the dark'],
        run: (name, vocab) => {
            // RETURNED, not fired-and-forgotten: runGenerate restores the
            // sandbox globals in a finally block, so an un-awaited generate
            // would emit its toast after the stubs are gone.
            return window.InspectorAgentView._generateTagsFromPersonality({
                charName: name, field: 'fear_tags', vocab, limit: 8,
                contextNote: 'characters and areas', ask: 'what frightens them?', toastPrefix: 'Fear tags'
            });
        }
    });
    assertEq(sent[0].data.fear_tags, ['goblin', 'chief', 'dark'], 'one concept yielded two live ids, then a new one');
    const said = toasts.join(' | ');
    assertTrue(/2 match something here/.test(said), `both grounded ids are live — got: ${said}`);
    assertTrue(/1 nothing carries yet: dark/.test(said), 'and the new one is named');
});

test('a word the world has no tag for is reported, not silently guessed away', async () => {
    // No prefix guessing: there is no `chief` to match "chieftain" by, and
    // guessing is exactly what produced underwear/footwear in /api/tags/validate.
    const { sent, toasts } = await runGenerate({
        live: ['goblin'], library: [],
        concepts: ['the deep wyrm'],
        run: (name, vocab) => {
            // RETURNED, not fired-and-forgotten: runGenerate restores the
            // sandbox globals in a finally block, so an un-awaited generate
            // would emit its toast after the stubs are gone.
            return window.InspectorAgentView._generateTagsFromPersonality({
                charName: name, field: 'fear_tags', vocab, limit: 8,
                contextNote: 'characters and areas', ask: 'what frightens them?', toastPrefix: 'Fear tags'
            });
        }
    });
    assertEq(sent[0].data.fear_tags, ['wyrm'], 'nothing real, so the head noun is kept');
    assertTrue(toasts.join(' ').includes('nothing carries yet: wyrm'), 'and it is reported as carrying nothing');
});

test('a phrase that resolves yields only the resolved ids, not the filler words', async () => {
    // By design: once a phrase resolves, its remaining words are dropped rather
    // than each becoming a new id, or "worn iron tools" would add `worn` and
    // `iron`. An unresolvable phrase still falls back to its head noun.
    assertEq(AV._resolveConcept('a goblin chieftain', VOCAB).map(r => r.id), ['goblin'],
        'goblin resolves, so chieftain is not guessed at or added');
    assertEq(AV._resolveConcept('the deep wyrm', VOCAB).map(r => [r.id, r.status]), [['wyrm', 'new']],
        'nothing resolves, so the head noun becomes a reported new id');
});

test('generation still works when the vocabulary cannot be read', async () => {
    const { sent } = await runGenerate({
        live: [], library: [], concepts: ['iron tools'],
        run: (name, vocab) => {
            // RETURNED, not fired-and-forgotten: runGenerate restores the
            // sandbox globals in a finally block, so an un-awaited generate
            // would emit its toast after the stubs are gone.
            return window.InspectorAgentView._generateTagsFromPersonality({
                charName: name, field: 'interest_tags', vocab, limit: 8,
                contextNote: 'items', ask: 'what would they seek?', toastPrefix: 'Interest tags'
            });
        }
    });
    assertEq(sent[0].data.interest_tags, ['tools'], 'an empty vocabulary degrades to a new id, not a failure');
});
