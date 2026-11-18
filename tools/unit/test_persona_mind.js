/**
 * tools/unit/test_persona_mind.js
 *
 * task-852: Persona workspace unit tests covering markings parsing/formatting,
 * personality chip tones, and multi-line textarea coverage for narrative fields.
 */

const MV = window.InspectorMindView;

test('markings parse and format round-trip with canonical area prefix (task-852 P3)', () => {
    assertTrue(typeof MV._parseMark === 'function', 'MV._parseMark exists');
    assertTrue(typeof MV._formatMark === 'function', 'MV._formatMark exists');

    const formatted = MV._formatMark('torso', 'anchor tattoo');
    assertEq(formatted, 'torso::anchor tattoo', 'formatted mark with separator');

    const parsedPrefixed = MV._parseMark(formatted);
    assertEq(parsedPrefixed.area, 'torso', 'parsed area');
    assertEq(parsedPrefixed.text, 'anchor tattoo', 'parsed text');

    const parsedUnprefixed = MV._parseMark('legacy battle scar');
    assertEq(parsedUnprefixed.area, null, 'unprefixed area is null');
    assertEq(parsedUnprefixed.text, 'legacy battle scar', 'unprefixed text kept');

    const parsedEmpty = MV._parseMark('');
    assertEq(parsedEmpty.area, null, 'empty mark area is null');
    assertEq(parsedEmpty.text, '', 'empty mark text is empty');
});

test('persona chip tones map positive tags to info and adverse tags to danger (task-852 P5)', () => {
    const tones = MV._PERSONA_TONES;
    assertTrue(tones != null, '_PERSONA_TONES exists');
    assertEq(tones.likes, 'info', 'likes tone');
    assertEq(tones.interests, 'info', 'interests tone');
    assertEq(tones.dislikes, 'danger', 'dislikes tone');
    assertEq(tones.fears, 'danger', 'fears tone');
    assertEq(tones.traumas, 'danger', 'traumas tone');
    assertEq(tones.turn_offs, 'danger', 'turn_offs tone');
});

test('persona narrative and overview fields render as multi-line textareas (task-852 P5)', () => {
    const textareas = MV._PERSONA_TEXTAREAS;
    assertTrue(textareas instanceof Set, '_PERSONA_TEXTAREAS is a Set');

    const expected = [
        'appearance.overview',
        'narrative.arc',
        'narrative.role_in_town',
        'narrative.biography.early_life',
        'narrative.biography.adulthood',
        'narrative.biography.current_situation',
        'narrative.secrets.deepest_secret',
    ];
    for (const path of expected) {
        assertTrue(textareas.has(path), `${path} is in _PERSONA_TEXTAREAS`);
    }
    assertFalse(textareas.has('identity.pronouns'), 'identity.pronouns is not textarea');
    assertFalse(textareas.has('appearance.height_cm'), 'appearance.height_cm is not textarea');
});

test('InspectorPersonaView is exposed and wired (task-441)', () => {
    const PV = window.InspectorPersonaView;
    assertTrue(PV != null, 'InspectorPersonaView exists on window');
    assertTrue(typeof PV.bind === 'function', 'PV.bind is a function');
    assertTrue(typeof PV.unbind === 'function', 'PV.unbind is a function');
    assertTrue(typeof PV.fetch === 'function', 'PV.fetch is a function');
    assertTrue(typeof PV.html === 'function', 'PV.html is a function');
    assertTrue(typeof PV.wire === 'function', 'PV.wire is a function');
    assertTrue(typeof PV.syncFromForm === 'function', 'PV.syncFromForm is a function');
    assertTrue(typeof PV.repaint === 'function', 'PV.repaint is a function');
    assertEq(PV._parseMark('a::b').text, MV._parseMark('a::b').text, 'parseMark behavior preserved');
    assertEq(PV._formatMark('a', 'b'), MV._formatMark('a', 'b'), 'formatMark behavior preserved');
    assertEq(PV._PERSONA_TONES, MV._PERSONA_TONES, 'PERSONA_TONES identity preserved');
    assertEq(PV._PERSONA_TEXTAREAS, MV._PERSONA_TEXTAREAS, 'PERSONA_TEXTAREAS identity preserved');
});

test('InspectorPersonaView structured languages normalize, render, and collect cleanly (task-966)', () => {
    const PV = window.InspectorPersonaView;
    assertTrue(typeof PV._normalizeLanguageEntry === 'function', '_normalizeLanguageEntry exists');
    assertTrue(typeof PV._languageRowHtml === 'function', '_languageRowHtml exists');
    assertTrue(typeof PV._collectPersona === 'function', '_collectPersona exists');

    const legacy = PV._normalizeLanguageEntry('Common');
    assertEq(legacy.language, 'common', 'legacy common slug');
    assertEq(legacy.fluency, 'native', 'legacy common defaults to native');
    assertEq(legacy.literate, true, 'legacy common defaults to literate');

    const structured = PV._normalizeLanguageEntry({
        language: 'English',
        fluency: 'broken',
        literate: false,
        known_words: ['bathroom', 'wait', 'hungry'],
    });
    assertEq(structured.language, 'english', 'structured language slug');
    assertEq(structured.fluency, 'broken', 'structured fluency');
    assertEq(structured.literate, false, 'structured literate');
    assertEq(structured.known_words.join(','), 'bathroom,wait,hungry', 'structured known_words');

    const container = document.createElement('div');
    const hostState = {
        charName: 'Aoi',
        escName: 'Aoi',
        tab: 'persona',
        persona: {
            structured: true,
            record: {
                capabilities: {
                    languages: [structured],
                },
            },
            schema: {
                properties: {
                    capabilities: {
                        properties: {
                            languages: { type: 'array', description: 'known languages' },
                        },
                    },
                },
            },
            hints: {},
            suggestions: {},
            dirty: false,
            msg: '',
            prose: '',
            prose_stale: false,
            warnings: [],
            openSections: ['capabilities'],
        },
    };
    PV.bind(hostState, null);
    const html = PV.html();
    assertTrue(html.includes('data-lang-list="capabilities.languages"'), 'renders language list container');
    assertTrue(html.includes('data-lang-row'), 'renders language row');
    assertTrue(html.includes('data-lang-field="language"'), 'renders language id input');
    assertTrue(html.includes('value="english"'), 'renders normalized language value');
    assertTrue(html.includes('data-lang-field="fluency"'), 'renders fluency select');
    assertTrue(html.includes('<option value="broken" selected>broken</option>'), 'selects broken fluency');
    assertTrue(html.includes('data-lang-field="literate"'), 'renders literate checkbox');
    assertTrue(html.includes('data-chip-new="capabilities.languages.known_words"'), 'renders known_words chip input');
    assertTrue(html.includes('bathroom') && html.includes('wait') && html.includes('hungry'), 'renders known_words chips');
    assertTrue(html.includes('id="mind-persona-add-lang"'), 'renders add language button');

    const mockRow = {
        querySelector(sel) {
            if (sel === '[data-lang-field="language"]') return { value: 'English' };
            if (sel === '[data-lang-field="fluency"]') return { value: 'broken' };
            if (sel === '[data-lang-field="literate"]') return { checked: false };
            if (sel === '.pf-chips') {
                return {
                    querySelector(s) {
                        if (s === 'input[type="hidden"]') return { value: 'bathroom\nwait\nhungry' };
                        return null;
                    },
                };
            }
            return null;
        },
    };
    const mockLangList = {
        querySelectorAll(sel) {
            return sel === '[data-lang-row]' ? [mockRow] : [];
        },
    };
    const mockContainer = {
        querySelector(sel) {
            return sel === '[data-lang-list="capabilities.languages"]' ? mockLangList : null;
        },
        querySelectorAll() { return []; },
    };
    PV.bind(hostState, mockContainer);
    const collected = PV._collectPersona();
    assertTrue(Array.isArray(collected.capabilities?.languages), 'collected capabilities.languages is array');
    assertEq(collected.capabilities.languages.length, 1, 'collected 1 language');
    assertEq(collected.capabilities.languages[0].language, 'english', 'collected language');
    assertEq(collected.capabilities.languages[0].fluency, 'broken', 'collected fluency');
    assertEq(collected.capabilities.languages[0].literate, false, 'collected literate');
    assertEq(collected.capabilities.languages[0].known_words.join(','), 'bathroom,wait,hungry', 'collected known_words');

    PV.unbind();
});
