/**
 * tools/unit/test_soak_spacetime.js — the space-time swimlane geometry (task-544).
 *
 * These pin the parts that can be wrong in ways a screenshot will not reveal. An
 * off-by-one in the window silently drops a character's whole afternoon; a
 * mis-packing row packer turns two people in a room into two people who appear
 * never to meet — and a meeting is the entire reason this view exists.
 */
'use strict';

const ST_API = window.SoakSpacetime;

const ST_IV = (character, area, from, to) => ({
    character, area, from_tick: from, to_tick: to,
});

// ── lane ordering ───────────────────────────────────────────────────────

test('laneOrder is alphabetical when there is no layout', () => {
    assertEq(
        JSON.stringify(ST_API.laneOrder(['Storehouse', 'Camp Entrance', 'Longhouse'], null)),
        JSON.stringify(['Camp Entrance', 'Longhouse', 'Storehouse']));
});

test('laneOrder sorts spatially by row then column when a layout exists', () => {
    const placements = {
        Storehouse: { x: 7, y: 3 },
        Longhouse: { x: 2, y: 3 },
        'Camp Entrance': { x: 5, y: 1 },
    };
    // The point of the spatial axis: the two hall buildings are neighbours, not
    // at opposite ends of the chart the way an alphabetical axis would put them.
    assertEq(
        JSON.stringify(ST_API.laneOrder(Object.keys(placements), placements)),
        JSON.stringify(['Camp Entrance', 'Longhouse', 'Storehouse']));
});

test('laneOrder puts unplaced areas last but keeps the axis total and stable', () => {
    const placements = { Longhouse: { x: 0, y: 0 }, Storehouse: { x: 1, y: 0 } };
    const areas = ['Zebra Den', 'Longhouse', 'Storehouse', 'Alpha Hut'];
    const once = ST_API.laneOrder(areas, placements);
    const twice = ST_API.laneOrder(areas.slice().reverse(), placements);
    assertEq(JSON.stringify(once), JSON.stringify(twice));
    assertEq(JSON.stringify(once),
        JSON.stringify(['Longhouse', 'Storehouse', 'Alpha Hut', 'Zebra Den']));
});

test('laneOrder deduplicates and drops falsy names', () => {
    assertEq(JSON.stringify(ST_API.laneOrder(['A', 'A', '', null, undefined, 'B'], null)),
        JSON.stringify(['A', 'B']));
});

test('laneOrder ignores a placement with non-numeric coordinates', () => {
    const placements = { A: { x: 'left', y: 'top' }, B: { x: 1, y: 1 } };
    // A broken placement must not produce NaN keys, which would sort randomly
    // and make the axis jump between refreshes.
    assertEq(JSON.stringify(ST_API.laneOrder(['A', 'B'], placements)),
        JSON.stringify(['B', 'A']));
});

// ── windowing ───────────────────────────────────────────────────────────

test('clipToWindow drops intervals entirely outside the window', () => {
    const kept = ST_API.clipToWindow([ST_IV('Jake', 'Camp', 100, 200)], 0, 50);
    assertEq(kept.length, 0);
});

test('clipToWindow clips rather than drops, so a zoom can start mid-stay', () => {
    // This is what makes zoom work at all: Jake was in the storehouse from 0 and
    // is still there at 500, so a window of 100..200 must show the overlap.
    const out = ST_API.clipToWindow([ST_IV('Jake', 'Store', 0, 500)], 100, 200);
    assertEq(out.length, 1);
    assertEq(out[0].from_tick, 100);
    assertEq(out[0].to_tick, 200);
    assertEq(out[0].clipped_start, true);
    assertEq(out[0].clipped_end, true);
});

test('clipToWindow flags only the side that was actually cut', () => {
    const [whole] = ST_API.clipToWindow([ST_IV('Jake', 'Camp', 100, 200)], 0, 500);
    assertEq(whole.clipped_start, false);
    assertEq(whole.clipped_end, false);
    const [start] = ST_API.clipToWindow([ST_IV('Jake', 'Camp', 100, 200)], 0, 150);
    assertEq(start.clipped_start, false);
    assertEq(start.clipped_end, true);
});

test('clipToWindow keeps a boundary-touching interval (present at the instant)', () => {
    // Dropping it would make the view disagree with the data exactly where
    // someone is looking most closely.
    const out = ST_API.clipToWindow([ST_IV('Jake', 'Camp', 200, 300)], 0, 200);
    assertEq(out.length, 1);
    assertEq(out[0].from_tick, 200);
});

test('clipToWindow handles a reversed window and non-numeric bounds', () => {
    const out = ST_API.clipToWindow([ST_IV('Jake', 'Camp', 10, 20), ST_IV('X', 'Y', NaN, 5)], 20, 10);
    assertEq(out.length, 1);
    assertEq(out[0].from_tick, 10);
    assertEq(out[0].to_tick, 20);
});

test('clipToWindow tolerates a missing interval list', () => {
    assertEq(ST_API.clipToWindow(null, 0, 10).length, 0);
    assertEq(ST_API.clipToWindow(undefined, 0, 10).length, 0);
});

// ── bucketing ───────────────────────────────────────────────────────────

test('bucketOccupancy gives a full stay a density of 1 in every bucket', () => {
    const out = ST_API.bucketOccupancy([ST_IV('Jake', 'Camp', 0, 100)], 0, 100, 4);
    const row = out.density.get('Jake');
    assertEq(JSON.stringify(row), JSON.stringify([1, 1, 1, 1]));
});

test('bucketOccupancy reads a brief visit as partial density', () => {
    // A character who dashed through must not look like one who was there all
    // along — that difference is the point of the overview. Ten ticks of a
    // 25-tick bucket is 0.4, not 1.
    const out = ST_API.bucketOccupancy([ST_IV('Jake', 'Camp', 0, 10)], 0, 100, 4);
    const row = out.density.get('Jake');
    assertEq(row[0], 0.4);
    assertEq(row[1], 0);
    assertEq(row[2], 0);
    assertEq(row[3], 0);
});

test('bucketOccupancy sums overlapping characters into one density', () => {
    // A is there for both buckets (1 + 1); B only for the first (1 + 0).
    const out = ST_API.bucketOccupancy(
        [ST_IV('A', 'Camp', 0, 100), ST_IV('B', 'Camp', 0, 50)], 0, 100, 2);
    const total = [0, 1].map((b) => ['A', 'B']
        .reduce((sum, n) => sum + out.density.get(n)[b], 0));
    assertEq(JSON.stringify(total), JSON.stringify([2, 1]));
});

// ── row packing and collisions ──────────────────────────────────────────

test('packRows puts non-overlapping intervals on one row', () => {
    const packed = ST_API.packRows([ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Camp', 10, 20)]);
    assertEq(packed[0].row, 0);
    assertEq(packed[1].row, 0);
});

test('packRows splits genuinely overlapping intervals onto separate rows', () => {
    // This is the property that makes a collision visible at all. If both landed
    // on one row, two people in a room would look like a handover.
    const packed = ST_API.packRows([ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Camp', 5, 15)]);
    assertEq(packed[0].row !== packed[1].row, true);
});

test('packRows reuses a freed row instead of always growing', () => {
    const packed = ST_API.packRows([
        ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Camp', 0, 10),
        ST_IV('C', 'Camp', 10, 20),
    ]);
    const rows = packed.map((p) => p.row);
    assertEq(Math.max(...rows), 1, 'the third interval should reuse a freed row');
});

test('packRows sorts its input rather than trusting the caller', () => {
    const packed = ST_API.packRows([ST_IV('A', 'Camp', 50, 60), ST_IV('B', 'Camp', 0, 10)]);
    assertEq(packed[0].from_tick, 0, 'packing must be deterministic regardless of input order');
});

test('packRows tolerates an empty list', () => {
    assertEq(ST_API.packRows(null).length, 0);
    assertEq(ST_API.packRows([]).length, 0);
});

test('findCollisions reports two characters sharing a room', () => {
    const hits = ST_API.findCollisions([ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Camp', 5, 15)]);
    assertEq(hits.length, 1);
    assertEq(hits[0].area, 'Camp');
    assertEq(hits[0].first, 'A');
    assertEq(hits[0].second, 'B');
    assertEq(hits[0].from_tick, 5);
    assertEq(hits[0].to_tick, 10);
    assertEq(hits[0].ticks, 5);
});

test('findCollisions ignores characters in different rooms', () => {
    const hits = ST_API.findCollisions([ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Pit', 0, 10)]);
    assertEq(hits.length, 0);
});

test('findCollisions ignores a sequential handover', () => {
    // A leaves exactly as B arrives: not a meeting, and reporting it as one
    // would bury the real collisions in noise.
    const hits = ST_API.findCollisions([ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Camp', 10, 20)]);
    assertEq(hits.length, 0);
});

test('findCollisions never pairs a character with itself', () => {
    // A character ping-ponging between two rooms has several intervals in the
    // same list; that is churn, not a meeting.
    const hits = ST_API.findCollisions([
        ST_IV('A', 'Camp', 0, 10), ST_IV('A', 'Camp', 20, 30), ST_IV('A', 'Pit', 10, 20),
    ]);
    assertEq(hits.length, 0);
});

test('findCollisions reports a meeting three ways as three pairs', () => {
    const hits = ST_API.findCollisions([
        ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Camp', 0, 10), ST_IV('C', 'Camp', 0, 10),
    ]);
    assertEq(hits.length, 3);
});

test('collisionsByArea ranks by total shared ticks and names the pairs', () => {
    const hits = ST_API.findCollisions([
        ST_IV('A', 'Camp', 0, 10), ST_IV('B', 'Camp', 0, 10),
        ST_IV('C', 'Pit', 0, 4), ST_IV('D', 'Pit', 0, 4),
    ]);
    const ranked = ST_API.collisionsByArea(hits);
    assertEq(ranked[0].area, 'Camp');
    assertEq(ranked[0].ticks, 10);
    assertEq(ranked[0].pairs[0].pair, 'A + B');
    assertEq(ranked[1].area, 'Pit');
    assertEq(ranked[1].ticks, 4);
});

test('collisionsByArea tolerates no collisions at all', () => {
    assertEq(ST_API.collisionsByArea([]).length, 0);
    assertEq(ST_API.collisionsByArea(null).length, 0);
});

// ── layout ──────────────────────────────────────────────────────────────

const SPACETIME_PAYLOAD = {
    areas: ['Camp Entrance', 'Longhouse', 'Storehouse'],
    characters: ['Arix', 'Belne'],
    intervals: [
        ST_IV('Arix', 'Camp Entrance', 0, 10),
        ST_IV('Belne', 'Longhouse', 0, 5),
        ST_IV('Arix', 'Longhouse', 10, 20),
        ST_IV('Belne', 'Longhouse', 12, 18),
    ],
};

test('buildLayout places every clipped interval on a lane', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    const placed = layout.lanes.reduce((n, lane) => n + lane.intervals.length, 0);
    assertEq(placed, 4);
    assertEq(layout.visibleIntervals, 4);
});

test('buildLayout gives each lane a non-overlapping vertical slot', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    for (let i = 1; i < layout.lanes.length; i += 1) {
        const previous = layout.lanes[i - 1];
        const lane = layout.lanes[i];
        assertTrue(previous.top + previous.height <= lane.top + 0.001,
            'lanes must not overlap vertically');
    }
});

test('buildLayout reports the collision the swimlane exists to surface', () => {
    // Belne and Arix are both in the Longhouse at tick 12.
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    assertEq(layout.collisions.length, 1);
    assertEq(layout.collisions[0].area, 'Longhouse');
    assertEq(layout.collisions[0].ticks, 6);
});

test('buildLayout gives a lane one row when nobody overlaps there', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    const entrance = layout.lanes.find((l) => l.area === 'Camp Entrance');
    assertEq(entrance.rows, 1);
});

test('buildLayout exposes every padding the renderers read', () => {
    // A missing padding is the worst kind of bug here: it becomes an
    // `undefined`/`NaN` SVG attribute, which the browser drops without
    // complaint. The grid lines and death rules then just do not appear, and
    // nothing anywhere reports an error.
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    ['paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom',
        'rowHeight', 'ribbonHeight', 'plotWidth', 'width', 'height',
        'from', 'to'].forEach((key) => {
        assertTrue(typeof layout[key] === 'number' && Number.isFinite(layout[key]),
            `layout.${key} must be a finite number, got ${layout[key]}`);
    });
});

test('renderSwimlanes emits no undefined or NaN coordinates', () => {
    // The guard for the class of bug above, at the level it actually bites.
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    const svg = ST_API.renderSwimlanes(layout, SPACETIME_PAYLOAD, {
        deaths: [{ name: 'Belne', tick: 15, cause: 'exhaustion' }],
        condition_spans: [{ character: 'Belne', condition: 'sick', from_tick: 1, to_tick: 4 }],
    });
    assertTrue(svg.indexOf('undefined') === -1, 'svg must not contain undefined');
    assertTrue(svg.indexOf('NaN') === -1, 'svg must not contain NaN');
});

test('renderSwimlanes draws the grid lines it declares', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    const svg = ST_API.renderSwimlanes(layout, SPACETIME_PAYLOAD, {});
    assertTrue((svg.match(/soak-grid-line/g) || []).length >= 5, 'expected a time grid');
});

test('buildLayout xOf maps the window onto the plot area', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 100 });
    assertEq(layout.xOf(0), layout.paddingLeft);
    assertEq(Math.round(layout.xOf(100)), layout.paddingLeft + layout.plotWidth);
});

test('buildLayout windowing drops out-of-window intervals but keeps the axis', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 8 });
    assertEq(layout.visibleIntervals, 2, 'only the two intervals inside 0..8');
    assertEq(layout.lanes.length, 3, 'the lane axis still lists every area');
});

test('buildLayout survives a payload with no intervals', () => {
    const layout = ST_API.buildLayout({ areas: ['A'], characters: [], intervals: [] },
        { from: 0, to: 10 });
    assertEq(layout.visibleIntervals, 0);
    assertEq(layout.collisions.length, 0);
    assertTrue(layout.height > 0, 'the canvas still needs a height to draw an axis on');
});

test('buildLayout tolerates a missing payload entirely', () => {
    const layout = ST_API.buildLayout(null, { from: 0, to: 10 });
    assertEq(layout.lanes.length, 0);
    assertEq(layout.visibleIntervals, 0);
});

// ── why over time ───────────────────────────────────────────────────────

test('whyOverTime buckets decided events and ignores the rest', () => {
    const events = [
        { tick: 5, why_group: 'needs' },
        { tick: 15, why_group: 'needs' },
        { tick: 25, why_group: 'plan' },
        { tick: 999, why_group: 'needs' },   // outside the window
        { tick: 5, why_group: '' },          // unattributed: not a decision
    ];
    const out = ST_API.whyOverTime(events, 0, 40, 4);
    assertEq(JSON.stringify(out.groups), JSON.stringify(['needs', 'plan']));
    assertEq(JSON.stringify(out.series.get('needs')), JSON.stringify([1, 1, 0, 0]));
    assertEq(JSON.stringify(out.series.get('plan')), JSON.stringify([0, 0, 1, 0]));
});

test('whyOverTime clamps the last event into the final bucket', () => {
    const out = ST_API.whyOverTime([{ tick: 40, why_group: 'needs' }], 0, 40, 4);
    assertEq(out.series.get('needs')[3], 1);
});

test('whyOverTime tolerates missing input', () => {
    const out = ST_API.whyOverTime(null, 0, 10, 2);
    assertEq(out.groups.length, 0);
    assertEq(out.buckets, 2);
});

// ── character isolation ─────────────────────────────────────────────────

const DRILL_PAYLOAD = {
    areas: ['Camp', 'Longhouse', 'Storehouse'],
    characters: ['Arix', 'Belne', 'Croak'],
    intervals: [
        ST_IV('Arix', 'Camp', 0, 10),
        ST_IV('Belne', 'Camp', 0, 10),
        ST_IV('Arix', 'Longhouse', 10, 20),
        ST_IV('Croak', 'Storehouse', 0, 30),
    ],
    condition_spans: [
        { character: 'Arix', condition: 'sick', from_tick: 1, to_tick: 5 },
        { character: 'Belne', condition: 'wet', from_tick: 2, to_tick: 8 },
    ],
};

test('filterCharacter keeps only that character\'s intervals', () => {
    const out = ST_API.filterCharacter(DRILL_PAYLOAD, 'Arix');
    assertEq(out.intervals.length, 2);
    assertEq(out.intervals.every((iv) => iv.character === 'Arix'), true);
    assertEq(out.characters.length, 1);
    assertEq(out.characters[0], 'Arix');
});

test('filterCharacter keeps only that character\'s condition spans', () => {
    // A ribbon for somebody else on an isolated chart would be a lie: the lane
    // it belongs to is no longer drawn.
    const out = ST_API.filterCharacter(DRILL_PAYLOAD, 'Belne');
    assertEq(out.condition_spans.length, 1);
    assertEq(out.condition_spans[0].character, 'Belne');
});

test('filterCharacter prunes the area axis to the rooms actually visited', () => {
    // Fourteen empty rails are worse than useless: each reads as "they were
    // nowhere" for a room they simply never entered, and it pushes the lanes the
    // reader came for off the screen.
    const out = ST_API.filterCharacter(DRILL_PAYLOAD, 'Arix');
    assertEq(JSON.stringify(out.areas), JSON.stringify(['Camp', 'Longhouse']));
    assertEq(out.areas.indexOf('Storehouse'), -1, 'Arix never went to the storehouse');
});

test('filterCharacter preserves the relative order of the lanes it keeps', () => {
    // The sequence of rooms is the answer, so the axis order must survive the
    // pruning. 'Storehouse' is dropped from the middle here, and what is left
    // must still read in the original order.
    const out = ST_API.filterCharacter(DRILL_PAYLOAD, 'Arix');
    assertEq(JSON.stringify(out.areas), JSON.stringify(['Camp', 'Longhouse']));
    const layout = ST_API.buildLayout(out, { from: 0, to: 30 });
    assertEq(JSON.stringify(layout.lanes.map((l) => l.area)),
        JSON.stringify(['Camp', 'Longhouse']));
});

test('filterCharacter with no name returns the payload untouched', () => {
    assertEq(ST_API.filterCharacter(DRILL_PAYLOAD, null).intervals.length, 4);
    assertEq(ST_API.filterCharacter(DRILL_PAYLOAD, null).areas.length, 3);
    assertEq(ST_API.filterCharacter(DRILL_PAYLOAD, undefined).intervals.length, 4);
});

test('filterCharacter on an unknown name yields an empty, safe payload', () => {
    // A stale selection after switching runs must not throw or draw another
    // character's chart under the wrong name.
    const out = ST_API.filterCharacter(DRILL_PAYLOAD, 'Nobody');
    assertEq(out.intervals.length, 0);
    assertEq(out.characters.length, 1);
    assertEq(out.areas.length, 0, 'nobody visited anywhere');
    const layout = ST_API.buildLayout(out, { from: 0, to: 30 });
    assertEq(layout.visibleIntervals, 0);
    assertEq(ST_API.renderSwimlanes(layout, out, {}).indexOf('No presence recorded') !== -1, true);
});

test('an isolated character still shows a collision with the person they met', () => {
    // Arix and Belne share the camp for ten ticks. Isolating Arix must still
    // report Belne — the reason to drill into one goblin is to find out who they
    // were with, and filtering the other people out of the input destroys the
    // only question worth asking. So the collisions come from the UNFILTERED
    // intervals and are narrowed by who is in the pair.
    const shown = ST_API.filterCharacter(DRILL_PAYLOAD, 'Arix');
    assertEq(ST_API.buildLayout(shown, { from: 0, to: 30 }).collisions.length, 0,
        'the isolated chart itself has nobody to overlap with');

    const rows = ST_API.collisionsFor(DRILL_PAYLOAD, 'Arix', 0, 30);
    assertEq(rows.length, 1);
    assertEq(rows[0].area, 'Camp');
    assertEq(rows[0].ticks, 10);
    assertEq(rows[0].pairs[0].pair, 'Arix + Belne');
});

test('collisionsFor narrows to one character without dropping the other', () => {
    const rows = ST_API.collisionsFor(DRILL_PAYLOAD, 'Belne', 0, 30);
    assertEq(rows.length, 1);
    assertEq(rows[0].pairs[0].pair, 'Arix + Belne');
    // Belne never shared the storehouse, so that lane must not appear.
    assertEq(rows.some((r) => r.area === 'Storehouse'), false);
});

test('collisionsFor with no name ranks everyone, as the overview does', () => {
    const rows = ST_API.collisionsFor(DRILL_PAYLOAD, null, 0, 30);
    assertEq(rows.length, 1);
    assertEq(rows[0].ticks, 10);
});

test('collisionsFor on a loner returns nothing rather than a zero row', () => {
    // Croak is alone in the storehouse all run; an empty row would read as a
    // collision with nobody.
    const rows = ST_API.collisionsFor(DRILL_PAYLOAD, 'Croak', 0, 30);
    assertEq(rows.length, 0);
});

test('renderSwimlanes says so when lanes exist but no interval does', () => {
    // A stale character name must not render empty rails: that says "everybody
    // stayed put", which is the opposite of what happened.
    const empty = { areas: ['Camp', 'Pit'], characters: ['Nobody'], intervals: [] };
    const layout = ST_API.buildLayout(empty, { from: 0, to: 30 });
    assertEq(layout.lanes.length, 2, 'lanes still exist');
    assertEq(layout.visibleIntervals, 0);
    const svg = ST_API.renderSwimlanes(layout, empty, {});
    assertTrue(svg.indexOf('No presence recorded') !== -1);
    assertTrue(svg.indexOf('<svg') === -1);
});

// ── colour + formatting ─────────────────────────────────────────────────

test('characterColor is stable and falls back for strangers', () => {
    const cast = ['Arix', 'Belne'];
    assertEq(ST_API.characterColor('Arix', cast), ST_API.characterColor('Arix', cast));
    assertTrue(ST_API.characterColor('Arix', cast) !== ST_API.characterColor('Belne', cast));
    assertEq(ST_API.characterColor('Nobody', cast), '#8b949e');
});

test('characterColor wraps rather than returning undefined past the palette', () => {
    const many = Array.from({ length: 30 }, (_, i) => `C${i}`);
    const colour = ST_API.characterColor('C0', many);
    assertTrue(typeof colour === 'string' && colour.startsWith('#'));
});

test('formatTick renders a clock, and a day prefix once past midnight', () => {
    assertEq(ST_API.formatTick(0, 1), '00:00');
    assertEq(ST_API.formatTick(90, 1), '01:30');
    assertEq(ST_API.formatTick(1440, 1), 'd2 00:00');
});

test('formatTick falls back to a raw tick without a minutes-per-tick', () => {
    assertEq(ST_API.formatTick(42, null), '#42');
    assertEq(ST_API.formatTick(42, 0), '#42');
});

// ── renderers ───────────────────────────────────────────────────────────

test('renderSwimlanes escapes area and character names', () => {
    const layout = ST_API.buildLayout({
        areas: ['<script>x</script>'], characters: ['A&B'], intervals: [ST_IV('A&B', '<script>x</script>', 0, 10)],
    }, { from: 0, to: 10 });
    const svg = ST_API.renderSwimlanes(layout, { characters: ['A&B'] }, {});
    assertTrue(svg.indexOf('<script>') === -1, 'area name must be escaped');
    assertTrue(svg.indexOf('A&amp;B') !== -1, 'character name must be escaped');
});

test('renderSwimlanes shows an empty state rather than an empty axis', () => {
    const layout = ST_API.buildLayout({ areas: [], characters: [], intervals: [] }, { from: 0, to: 10 });
    const svg = ST_API.renderSwimlanes(layout, {}, {});
    assertTrue(svg.indexOf('No presence recorded') !== -1);
    assertTrue(svg.indexOf('<svg') === -1, 'an empty axis is worse than no axis');
});

test('renderSwimlanes marks deaths with their cause', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    const svg = ST_API.renderSwimlanes(layout, SPACETIME_PAYLOAD, {
        deaths: [{ name: 'Belne', tick: 15, cause: 'exhaustion' }],
    });
    assertTrue(svg.indexOf('Belne died — exhaustion') !== -1);
    assertTrue(svg.indexOf('soak-death-line') !== -1);
});

test('renderSwimlanes draws condition ribbons from spans', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 30 });
    const svg = ST_API.renderSwimlanes(layout, SPACETIME_PAYLOAD, {
        condition_spans: [{ character: 'Belne', condition: 'sick', from_tick: 1, to_tick: 4 }],
    });
    assertTrue(svg.indexOf('soak-ribbon') !== -1);
    assertTrue(svg.indexOf('Belne: sick') !== -1);
});

test('renderSwimlanes clips a death marker outside the window away', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 10 });
    const svg = ST_API.renderSwimlanes(layout, SPACETIME_PAYLOAD, {
        deaths: [{ name: 'Belne', tick: 999, cause: 'hunger' }],
    });
    assertTrue(svg.indexOf('soak-death-line') === -1);
});

test('renderHeatmap shows an empty state with no presence', () => {
    const layout = ST_API.buildLayout({ areas: [], characters: [], intervals: [] }, { from: 0, to: 10 });
    assertTrue(ST_API.renderHeatmap(layout, {}, {}).indexOf('No presence recorded') !== -1);
});

test('renderHeatmap shades a busy bucket harder than an empty one', () => {
    const layout = ST_API.buildLayout(SPACETIME_PAYLOAD, { from: 0, to: 20 });
    const svg = ST_API.renderHeatmap(layout, SPACETIME_PAYLOAD, { buckets: 10 });
    assertTrue(svg.indexOf('<rect') !== -1, 'a populated lane must draw cells');
});
