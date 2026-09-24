/**
 * Unit tests for SpriteSheet slice geometry + naming (task-445 follow-up).
 *
 * Only the pure half is covered: the canvas/DOM half of
 * static/js/inspector/sprite-sheet.js cannot run in this Node sandbox.
 */
'use strict';
const SS = window.SpriteSheet;

const sum = (arr, f) => arr.reduce((a, x) => a + f(x), 0);

test('computeCells tiles a 4x3 sheet into 12 covering cells', () => {
    const cells = SS.computeCells(1536, 1024, 3, 4, {});
    assertEq(cells.length, 12, '12 tiles');
    // Columns tile exactly.
    assertEq(cells[0].x, 0, 'first x');
    assertEq(cells[3].x, 1152, 'last col x');
    assertEq(cells[3].x + cells[3].w, 1536, 'columns cover width');
    // Rows cover height with no gap (remainder absorbed, never dropped).
    assertEq(cells[8].y + cells[8].h, 1024, 'rows cover height');
    assertEq(sum(cells.slice(0, 4), c => c.w), 1536, 'row widths sum to sheet width');
    assertEq(sum([cells[0], cells[4], cells[8]], c => c.h), 1024, 'col heights sum to sheet height');
});

test('computeCells labelTrim crops only the bottom of each cell', () => {
    const full = SS.computeCells(400, 300, 3, 4, {});
    const cut = SS.computeCells(400, 300, 3, 4, { labelTrim: 0.1 });
    assertEq(cut[0].x, full[0].x, 'x unchanged');
    assertEq(cut[0].y, full[0].y, 'y unchanged');
    assertEq(cut[0].w, full[0].w, 'w unchanged');
    assertTrue(cut[0].h < full[0].h, 'height reduced by the label band');
    assertEq(cut[0].h, Math.round(full[0].h * 0.9), 'exactly 10% off');
});

test('computeCells clamps labelTrim and guards a zero grid', () => {
    assertEq(SS.computeCells(100, 100, 1, 1, { labelTrim: 5 })[0].h, 10, 'trim clamped to 0.9');
    assertEq(SS.computeCells(100, 100, 0, 0, {})[0].h, 100, 'rows/cols floored at 1');
    assertFalse(SS.computeCells(100, 100, 1, 1, { labelTrim: -3 })[0].h !== 100, 'negative trim -> 0');
});

test('computeCells lets the last col/row absorb a rounding remainder', () => {
    const cells = SS.computeCells(100, 100, 3, 3, {});
    assertEq(sum(cells.slice(0, 3), c => c.w), 100, 'width exactly covered');
    assertEq(sum([cells[0], cells[3], cells[6]], c => c.h), 100, 'height exactly covered');
});

test('parseNames splits on commas/newlines, slugs, and pads blanks', () => {
    assertEq(SS.parseNames('happy, sad\n angry', 4), ['happy', 'sad', 'angry', ''], 'comma+newline+pad');
    assertEq(SS.parseNames('Ex-cited!', 1), ['ex_cited'], 'slugifies custom keys');
    assertEq(SS.parseNames('a,b,c,d,e', 2), ['a', 'b'], 'extra names ignored');
    assertEq(SS.parseNames('', 2), ['', ''], 'empty -> all skip');
});

test('defaultNames follows the canonical order and overflows to slotN', () => {
    const twelve = SS.defaultNames(12);
    assertEq(twelve.length, 12, 'twelve names');
    assertEq(twelve[0], 'neutral', 'starts neutral');
    assertEq(twelve[7], 'aroused', 'canonical slot 8 is aroused (not excited)');
    assertEq(twelve[11], 'calm', 'ends calm');
    assertEq(SS.defaultNames(3), ['neutral', 'happy', 'sad'], 'truncates');
    assertEq(SS.defaultNames(14).slice(12), ['slot13', 'slot14'], 'overflows to slotN');
});

test('slug normalises punctuation and spacing', () => {
    assertEq(SS.slug('  Very Angry!! '), 'very_angry', 'spaces + punctuation');
    assertEq(SS.slug('__'), '', 'punctuation-only is empty');
});

test('clampBox normalises any drag direction into a positive box', () => {
    assertEq(SS.clampBox(10, 20, 110, 220, 500, 500),
        { x: 10, y: 20, w: 100, h: 200 }, 'down-right drag');
    assertEq(SS.clampBox(110, 220, 10, 20, 500, 500),
        { x: 10, y: 20, w: 100, h: 200 }, 'up-left drag normalises');
});

test('clampBox clamps to the sheet and rejects stray clicks', () => {
    assertEq(SS.clampBox(-50, -50, 120, 130, 100, 100),
        { x: 0, y: 0, w: 100, h: 100 }, 'clamped to bounds');
    assertEq(SS.clampBox(10, 10, 14, 40, 100, 100), null, 'too narrow -> null (stray click)');
    assertEq(SS.clampBox(10, 10, 40, 12, 100, 100), null, 'too short -> null');
});

test('defaultNameFor walks the canonical order then slotN', () => {
    assertEq(SS.defaultNameFor(0), 'neutral', 'first box');
    assertEq(SS.defaultNameFor(7), 'aroused', 'eighth box');
    assertEq(SS.defaultNameFor(12), 'slot13', 'overflow');
});
