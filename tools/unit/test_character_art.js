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
