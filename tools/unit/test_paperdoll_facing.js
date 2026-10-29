/**
 * tools/unit/test_paperdoll_facing.js
 *
 * task-852 P2: the navigate-mode doll shows one face at a time. The face filter
 * is declared once (AREA_FACE in paperdoll-view.ts) and read by both the figure
 * renderer and the Persona tab's keyboard logic. These pin that the two cannot
 * disagree, that the filter is a view of the existing AREA_TO_REGIONS catalog
 * (no second one), and that equip mode is untouched.
 */

const PD = window.InspectorPaperdoll;
window.worldState = { getNode: () => null };
const ident = (s) => String(s == null ? '' : s);

function areasIn(html) {
    return [...html.matchAll(/class="paperdoll-slot[^"]*" data-area="([a-z_]+)"/g)].map((m) => m[1]);
}
function figure(mode, facing, selected) {
    return PD.renderPaperdollFigureHtml('Mira', { equipped: {} }, ident, 'Mira',
        { mode, facing, selectedArea: selected || null });
}

test('front face shows the back-less set, back face shows back and no held/waist slots', () => {
    const front = PD.areasForFacing('front');
    const back = PD.areasForFacing('back');
    assertFalse(front.includes('back'), 'front hides the back slot');
    assertTrue(back.includes('back'), 'back face has the back slot');
    for (const a of ['waist', 'lhand', 'rhand', 'hand_l', 'hand_r']) {
        assertTrue(front.includes(a), `front shows ${a}`);
        assertFalse(back.includes(a), `back hides ${a}`);
    }
    for (const a of ['head', 'neck', 'larm', 'rarm', 'torso', 'legs', 'feet']) {
        assertTrue(front.includes(a) && back.includes(a), `${a} is on both faces`);
    }
});

test('an unknown facing is the front face', () => {
    assertEq(PD.areasForFacing(undefined), PD.areasForFacing('front'), 'undefined');
    assertEq(PD.areasForFacing('sideways'), PD.areasForFacing('front'), 'junk');
});

test('the face filter is a view of AREA_TO_REGIONS, never a second catalog', () => {
    for (const face of ['front', 'back']) {
        for (const area of PD.areasForFacing(face)) {
            assertTrue((PD.AREA_TO_REGIONS[area] || []).length > 0, `${face}/${area} has regions`);
        }
    }
    const union = new Set([...PD.areasForFacing('front'), ...PD.areasForFacing('back')]);
    assertEq([...union].sort(), Object.keys(PD.AREA_TO_REGIONS).sort(),
        'every catalogued area is reachable from one face or the other');
});

test('the rendered navigate doll draws exactly the areas the filter names', () => {
    for (const face of ['front', 'back']) {
        const html = figure('navigate', face);
        assertTrue(html.includes(`data-facing="${face}"`), `${face} marker`);
        assertEq(areasIn(html).sort(), PD.areasForFacing(face).sort(),
            `${face}: renderer and keyboard logic agree`);
    }
});

test('equip mode ignores facing and keeps every slot', () => {
    const html = figure('equip', 'back');
    assertEq(areasIn(html).length, 13, 'all 13 grid slots in equip mode');
    assertFalse(html.includes('data-facing="back"'), 'equip output is not face-marked back');
});

test('the selected area is marked selected, once, and announced', () => {
    const html = figure('navigate', 'front', 'torso');
    assertEq((html.match(/ pd-sel/g) || []).length, 1, 'one selected slot');
    assertTrue(/data-area="torso" role="button" aria-pressed="true"/.test(html), 'aria-pressed on the selection');
    assertTrue(/data-area="head" role="button" aria-pressed="false"/.test(html), 'others are not pressed');
});

test('paperdoll damage parsing handles strings, dice strings, and arrays without doubling d (task-655)', () => {
    assertEq(PD.parseDamage('1d6'), [1, 6, 0], '1d6 standard dice');
    assertEq(PD.parseDamage('1d8'), [1, 8, 0], '1d8 standard dice');
    assertEq(PD.parseDamage('2d6+3'), [2, 6, 3], '2d6+3 bonus dice');
    assertEq(PD.parseDamage('d8'), [1, 8, 0], 'bare d8');
    assertEq(PD.parseDamage('1d4-1'), [1, 4, -1], 'negative bonus');
    assertEq(PD.parseDamage([1, 6, 2]), [1, 6, 2], 'array notation');
    assertEq(PD.parseDamage('8'), [0, 0, 8], 'flat damage string');
    assertEq(PD.parseDamage(8), [0, 0, 8], 'flat damage number');
    assertEq(PD.parseDamage(null), [0, 0, 0], 'null damage');
});

test('paperdoll formatDamage formats dice and type cleanly without doubling d (task-655)', () => {
    assertEq(PD.formatDamage('1d6', [1, 6, 0], 'slashing'), '1d6 slashing', '1d6 slashing');
    assertEq(PD.formatDamage('1d8', [1, 8, 0], 'piercing'), '1d8 piercing', '1d8 piercing - no 1dd+8');
    assertEq(PD.formatDamage('2d6+3', [2, 6, 3], null), '2d6+3', '2d6+3 with no type');
    assertEq(PD.formatDamage('8', [0, 0, 8], 'bludgeoning'), '8 bludgeoning', 'flat damage with type');
});

test('paperdoll computeEquipmentTotals parses string damage_dice correctly (task-655)', () => {
    const fakePlayer = {
        equipped: { hand_right: ['hatchet_1'] }
    };
    const savedGetNode = window.worldState.getNodeByIdentifier;
    window.worldState.getNodeByIdentifier = (id) => {
        if (id === 'hatchet_1') {
            return {
                id: 'hatchet_1',
                name: 'Rusty Hatchet',
                properties: {
                    tags: ['weapon'],
                    damage: '1d6',
                    damage_dice: '1d6',
                    damage_type: 'slashing'
                }
            };
        }
        return null;
    };
    try {
        const totals = PD.computeEquipmentTotals(fakePlayer);
        assertEq(totals.bestDamage.dice, [1, 6, 0], 'parsed dice array');
        assertEq(PD.formatDamage(totals.bestDamage.damage, totals.bestDamage.dice, totals.bestDamage.type), '1d6 slashing', 'clean 1d6 slashing formatting');
    } finally {
        window.worldState.getNodeByIdentifier = savedGetNode;
    }
});
