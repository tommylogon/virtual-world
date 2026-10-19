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
