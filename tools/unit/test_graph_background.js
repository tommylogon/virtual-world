/**
 * Unit tests for the graph background's pure logic (task-451, bug-39).
 *
 * These cover exactly the parts that were previously only verifiable by hand in a
 * browser: the legacy-block migration, the "is there a background at all?"
 * predicate that bug-39 turned on, hit sorting, snapping, and the screen→graph
 * conversion that alt-click cycling depends on.
 */
'use strict';
const GB = window.GraphBackground;

const LAYER = {
    id: 'bg-one',
    label: 'Ground floor',
    image: '/static/images/backgrounds/floor-1.png',
    rect: { x: 0, y: 0, width: 100, height: 80 },
    rotation: 0,
    crop: { x: 0, y: 0, w: 1, h: 1 },
    opacity: 0.5,
    locked: false,
    visible: true,
};

test('legacy single-image block migrates to a one-layer list', () => {
    const block = GB._internals._normalizeBlock({
        image: '/static/images/backgrounds/old.png',
        rect: { x: -10, y: -20, width: 200, height: 100 },
        rotation: 15,
        crop: { x: 0.1, y: 0, w: 0.8, h: 1 },
        opacity: 0.4,
        locked: true,                 // old meaning: the NODE-LAYOUT freeze
        positions: { area_a: { x: 1, y: 2 } },
    });
    assertEq(block.layers.length, 1, 'one layer');
    assertEq(block.layers[0].imagePath, '/static/images/backgrounds/old.png', 'path kept');
    assertEq(block.layers[0].rect.width, 200, 'rect kept');
    assertEq(block.layers[0].rotation, 15, 'rotation kept');
    assertEq(block.layers[0].opacity, 0.4, 'opacity kept');
    assertFalse(block.layers[0].locked, 'a layer starts unlocked');
    assertTrue(block.layoutLocked, 'legacy locked became layoutLocked');
    assertEq(block.positions, { area_a: { x: 1, y: 2 } }, 'positions kept');
});

test('migration ignores nonsense and keeps a data URL local', () => {
    assertEq(GB._internals._normalizeBlock(null), null, 'null block');
    assertEq(GB._internals._normalizeBlock({}).layers.length, 0, 'empty block');
    // A record with neither an image nor a rect is not a layer.
    assertEq(GB._internals._normalizeBlock({ image: 'x' }).layers.length, 0, 'image without rect');
    assertEq(GB._internals._normalizeBlock({ rect: LAYER.rect }).layers.length, 0, 'rect without image');
    const dataUrl = GB._internals._normalizeLayer({ id: 'd', image: 'data:image/png;base64,AAAA', rect: LAYER.rect });
    assertEq(dataUrl.imagePath, null, 'data URLs have no server path');
    assertEq(dataUrl.imageSrc, 'data:image/png;base64,AAAA', 'source preserved');
});

test('the list form normalizes per-layer fields and filters junk', () => {
    const block = GB._internals._normalizeBlock({
        layers: [1, null, 'x', LAYER, { id: 'broken' }],
        positions: 'nope',
        layoutLocked: 'yes',
    });
    assertEq(block.layers.map(l => l.id), ['bg-one'], 'only real layers survive');
    assertEq(block.layers[0].visible, true, 'visible defaults to true');
    assertEq(block.positions, {}, 'non-object positions become {}');
    assertTrue(block.layoutLocked, 'truthy layoutLocked');
    // opacity 0 and visible:false must not be swallowed by falsy checks.
    const zero = GB._internals._normalizeBlock({ layers: [{ ...LAYER, opacity: 0, visible: false }] });
    assertEq(zero.layers[0].opacity, 0, 'opacity 0 survives');
    assertEq(zero.layers[0].visible, false, 'visible:false survives');
});

test('bug-39: "no background" is distinguishable from "a background with nothing in it"', () => {
    const has = GB._internals._hasBackground;
    assertFalse(has({}), 'empty block is not a background');
    assertFalse(has({ layers: [] }), 'empty list is not a background');
    assertFalse(has({ layers: [{ id: 'x', image: null, rect: null }] }), 'imageless layers are not a background');
    assertFalse(has(null), 'null is not a background');
    assertTrue(has({ layers: [LAYER] }), 'a real layer is a background');
    assertTrue(has({ layers: [], positions: { area_a: { x: 0, y: 0 } } }), 'positions alone count');
    assertTrue(has({ layers: [], layoutLocked: true }), 'a lock alone counts');
    // The legacy shape has to count too, or migration never runs.
    assertTrue(has({ image: '/static/images/backgrounds/old.png', rect: LAYER.rect }), 'legacy single image counts');
});

test('hit sorting returns the topmost layer first', () => {
    const state = GB._state;
    const saved = state.layers;
    try {
        state.layers = [
            { ...LAYER, id: 'under', rect: { x: 0, y: 0, width: 100, height: 100 } },
            { ...LAYER, id: 'over', rect: { x: 0, y: 0, width: 100, height: 100 } },
        ];
        assertEq(GB._internals._layersAt(50, 50).map(l => l.id), ['over', 'under'], 'later layers are on top');
        assertEq(GB._internals._layersAt(500, 500).length, 0, 'a point outside every layer hits nothing');
        state.layers[0].visible = false;
        assertEq(GB._internals._layersAt(50, 50).map(l => l.id), ['over'], 'hidden layers are skipped');
    } finally {
        state.layers = saved;
    }
});

test('point-in-layer accounts for rotation', () => {
    const inLayer = GB._internals._pointInLayer;
    const square = { rect: { x: 0, y: 0, width: 100, height: 100 }, rotation: 45 };
    assertTrue(inLayer(square, 50, 50), 'centre is inside');
    assertTrue(inLayer(square, 50, 90), 'the rotated square reaches further down the middle');
    // A corner of the axis-aligned box falls outside the diamond.
    assertFalse(inLayer(square, 4, 4), 'a corner is outside once rotated 45°');
    assertTrue(inLayer({ rect: { x: 0, y: 0, width: 100, height: 100 }, rotation: 0 }, 4, 4), 'inside when unrotated');
});

test('snapping pulls an edge onto a neighbour and leaves distant rects alone', () => {
    const state = GB._state;
    const saved = state.layers;
    try {
        state.layers = [{ ...LAYER, id: 'anchor', rect: { x: 0, y: 0, width: 100, height: 100 } }];
        const moving = { id: 'moving' };
        const near = GB._internals._snapRect({ x: 102, y: 0, width: 50, height: 50 }, moving);
        assertEq(near.x, 100, 'left edge snapped to the anchor right edge');
        assertEq(near.y, 0, 'y already aligned');
        const far = GB._internals._snapRect({ x: 400, y: 400, width: 50, height: 50 }, moving);
        assertEq(far.x, 400, 'out of tolerance is untouched');
        assertEq(far.y, 400, 'out of tolerance is untouched (y)');
        // The layer being dragged must not snap to itself.
        const self = GB._internals._snapRect({ x: 100, y: 0, width: 100, height: 100 }, state.layers[0]);
        assertEq(self.x, 100, 'a layer never snaps to itself');
    } finally {
        state.layers = saved;
    }
});

test('screen→graph conversion inverts the transform the layers are drawn with', () => {
    // A 400x300 graph area at (100,50) on screen, scaled 2x, centred on graph (10,20).
    window.document = {
        getElementById: () => ({ getBoundingClientRect: () => ({ left: 100, top: 50, width: 400, height: 300 }) }),
    };
    window.graphManager = { network: { getScale: () => 2, getViewPosition: () => ({ x: 10, y: 20 }) } };
    const point = GB._internals._clientToGraph(340, 240);
    assertEq(point.x, 30, 'x maps back');
    assertEq(point.y, 40, 'y maps back');
    // The container centre maps to the view position.
    const centre = GB._internals._clientToGraph(100 + 200, 50 + 150);
    assertEq(centre.x, 10, 'centre x is the view position');
    assertEq(centre.y, 20, 'centre y is the view position');
});

test('paintedGridRect maps a painted scope grid to graph space', () => {
    const rect = GB._internals.paintedGridRect;
    assertEq(rect(null), null, 'no grid');
    assertEq(rect({}), null, 'empty grid');
    assertEq(rect({ w: 0, h: 4 }), null, 'zero width');
    assertEq(rect({ w: 4, h: 0 }), null, 'zero height');
    // Default spacing: the Map layout's scale (GRID_SCALE 1) = 40px per cell,
    // half a cell offset so cell 0's area is at the origin.
    assertEq(rect({ w: 8, h: 4 }), { x: -20, y: -20, width: 320, height: 160 }, 'map spacing');
    assertEq(rect({ w: 8, h: 4 }, 1), { x: -20, y: -20, width: 320, height: 160 }, 'engine units');
    // An explicit override scales with the spacing (3.5 → 140px/cell).
    assertEq(rect({ w: 8, h: 4 }, 3.5), { x: -70, y: -70, width: 1120, height: 560 }, 'override');
    const wide = rect({ w: 8, h: 4 }, 1);
    assertEq(wide.x + wide.width, 300, 'right edge is half a cell past the last column');
    assertEq(wide.y + wide.height, 140, 'bottom edge is half a cell past the last row');
});
