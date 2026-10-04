/**
 * Unit tests for CharacterArt's pure art-resolution chain.
 *
 * The DOM half (open/close) cannot run in this Node sandbox; these tests pin the
 * fallback order shared by the graph node avatar, the composer people chips and
 * the examine portrait viewer.
 */
'use strict';
const Art = window.CharacterArt;

const PROPS = {
    expressions: {
        neutral: { profile: '/p/neutral.png', full: '/f/neutral.png' },
        happy: { profile: '/p/happy.png' },
        angry: { full: '/f/angry.png' },
    },
    profile_image: '/legacy/profile.png',
    image: '/legacy/full.png',
};

test('avatarFor prefers the emotion profile, then neutral, then legacy', () => {
    assertEq(Art.avatarFor(PROPS, 'happy'), '/p/happy.png', 'emotion profile wins');
    // 'sad' has no slot -> neutral profile
    assertEq(Art.avatarFor(PROPS, 'sad'), '/p/neutral.png', 'falls back to neutral profile');
    // 'angry' has only a full -> neutral profile
    assertEq(Art.avatarFor(PROPS, 'angry'), '/p/neutral.png', 'no step into full for avatar');
});

test('avatarFor falls through to legacy fields when no pack art exists', () => {
    const noNeutral = { expressions: { happy: { profile: '/p/happy.png' } }, profile_image: '/legacy/profile.png', image: '/legacy/full.png' };
    assertEq(Art.avatarFor(noNeutral, 'sad'), '/legacy/profile.png', 'profile_image before image');
    const bare = { image: '/legacy/full.png' };
    assertEq(Art.avatarFor(bare, 'happy'), '/legacy/full.png', 'image last resort');
    assertEq(Art.avatarFor({}, 'happy'), '', 'nothing -> empty');
});

test('fullArtFor prefers the emotion full, then neutral full, then image', () => {
    assertEq(Art.fullArtFor(PROPS, 'angry'), '/f/angry.png', 'emotion full wins');
    assertEq(Art.fullArtFor(PROPS, 'sad'), '/f/neutral.png', 'falls back to neutral full');
    assertEq(Art.fullArtFor({ image: '/only.png' }, 'sad'), '/only.png', 'legacy image');
    assertEq(Art.fullArtFor({ profile_image: '/only.png' }, 'sad'), '', 'profile is not a full body');
});

test('artFor returns both renders and defaults emotion to neutral', () => {
    assertEq(Art.artFor(PROPS), { profile: '/p/neutral.png', full: '/f/neutral.png' }, 'default neutral');
    assertEq(Art.artFor(PROPS, 'happy').full, '/f/neutral.png', 'happy has no full -> neutral full');
});

test('emotionKeyFor prefers the server-resolved expression key', () => {
    // The affect-map-derived key wins even when `current` is legacy free text.
    assertEq(Art.emotionKeyFor({ emotion: { current: 'relieved but vigilant', expression: 'calm' } }), 'calm',
        'expression key preferred over free text');
});

test('emotionKeyFor falls back to a canonical current, else neutral', () => {
    assertEq(Art.emotionKeyFor({ emotion: { current: 'sad' } }), 'sad', 'canonical current used');
    assertEq(Art.emotionKeyFor({ emotion: { current: 'anxious and hopeful' } }), 'neutral',
        'free-text current -> neutral');
    assertEq(Art.emotionKeyFor({ emotion: {} }), 'neutral', 'no key -> neutral');
    assertEq(Art.emotionKeyFor(null), 'neutral', 'no player -> neutral');
});

test("the engine's expression key resolves to authored art via the alias", () => {
    // engine/emotion.py:AXIS_TO_EXPRESSION emits its own vocabulary (`afraid`,
    // `ashamed`) which is not the authored art vocabulary. emotionKeyFor
    // returns that key unconditionally, so the slot lookup has to bridge the
    // two or a fearful character falls back to the neutral portrait.
    window.InspectorHelpers = { EXPRESSION_ART_ALIASES: { afraid: 'fearful', ashamed: 'embarrassed' } };
    try {
        const authored = { expressions: {
            neutral: { profile: '/p/neutral.png', full: '/f/neutral.png' },
            fearful: { profile: '/p/fearful.png', full: '/f/fearful.png' },
        } };
        const player = { emotion: { expression: 'afraid' } };
        assertEq(Art.avatarFor(authored, Art.emotionKeyFor(player)), '/p/fearful.png',
            'engine `afraid` renders the `fearful` art');
        assertEq(Art.fullArtFor(authored, Art.emotionKeyFor(player)), '/f/fearful.png',
            'engine `afraid` renders the `fearful` full art');
    } finally {
        window.InspectorHelpers = undefined;
    }
});

test('a direct engine-named slot still wins over the alias', () => {
    // Packs that already store the engine's names (mansion.json) must not be
    // rerouted: the alias is only a fallback for a missing direct hit.
    window.InspectorHelpers = { EXPRESSION_ART_ALIASES: { afraid: 'fearful' } };
    try {
        const both = { expressions: {
            afraid: { profile: '/p/afraid.png' },
            fearful: { profile: '/p/fearful.png' },
        } };
        assertEq(Art.avatarFor(both, 'afraid'), '/p/afraid.png', 'direct slot wins');
    } finally {
        window.InspectorHelpers = undefined;
    }
});

test('an engine key with no authored art falls back to neutral', () => {
    // `aroused` has no counterpart in the authored 30; it must go neutral
    // rather than borrow another expression's face.
    window.InspectorHelpers = { EXPRESSION_ART_ALIASES: { afraid: 'fearful' } };
    try {
        assertEq(Art.avatarFor(PROPS, 'aroused'), '/p/neutral.png', 'unmapped engine key -> neutral');
    } finally {
        window.InspectorHelpers = undefined;
    }
});
