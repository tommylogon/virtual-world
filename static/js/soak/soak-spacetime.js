/**
 * @module soak-spacetime — the space-time swimlane view for the Soak Lab (task-544)
 * @contributes pure lane/row/overlap geometry, the swimlane renderer, the occupancy heatmap and the why-over-time stack
 * @powers Soak lab — answering "did those two ever share a room?" — who was where, when, and what decided it
 * @relates consumes soak-telemetry payloads via soak-api.js; drawn by soak-ui.js; geometry tested by tools/unit/test_soak_spacetime.js
 * @docs none
 *
 * WHY THIS EXISTS, and why it is not a line chart
 * -----------------------------------------------
 * Every other chart in the lab is vitals-over-time, and an average Energy line is
 * close to useless in a soak: it hides the exact thing a soak is run to catch —
 * one character collapsing while the mean stays flat. A time x area heatmap shows
 * where the world is busy, which is useful, but it aggregates characters away, so
 * it cannot show *who* was where or reveal a meeting.
 *
 * A space-time swimlane answers the question a line chart cannot: **did those two
 * ever share a room?** Time on x, area lanes on y, one bar per presence interval.
 * Two bars overlapping in the same lane is a collision, and that is the thing the
 * view exists to surface.
 *
 * WHY THE GEOMETRY IS PURE AND SEPARATE
 * -------------------------------------
 * Everything above `renderSwimlanes` is a pure function of its input: no DOM, no
 * globals, no measurement. Lane assignment, greedy row packing, overlap
 * detection and windowing are the parts that can be *wrong* in ways a screenshot
 * will not reveal — an off-by-one in the window silently drops a character's
 * whole afternoon, and a greedy row packer that mis-packs turns two people in a
 * room into two people who appear not to meet. So they are testable, and
 * `tools/unit/test_soak_spacetime.js` pins them.
 */
(function () {
    'use strict';

    const F = window.SoakFormat;
    const esc = (s) => F.esc(s);

    // ── lane ordering ────────────────────────────────────────────────────

    /**
     * Order area lanes, spatially when a layout exists and alphabetically
     * otherwise.
     *
     * The spatial ordering matters more than it looks. An alphabetical axis puts a
     * camp's storehouse and longhouse at opposite ends of the chart and destroys
     * the spatial read — "everyone is in the north half" is a finding, and only a
     * spatial axis can show it. `placements` is the world grid's
     * `area_placements: {area_id: {x, y}}` (task-528), which is a *cell* index, so
     * rows are taken from y and columns from x.
     *
     * Areas with no placement sort after the placed ones, alphabetically, so the
     * axis is still total and stable. "Stable" is load-bearing: the same run must
     * produce the same axis on every refresh, or a band appears to move between
     * polls.
     */
    function laneOrder(areas, placements) {
        const names = Array.from(new Set((areas || []).filter(Boolean)));
        const place = placements || {};
        const withPos = names.filter((name) => {
            const p = place[name];
            return p && Number.isFinite(Number(p.x)) && Number.isFinite(Number(p.y));
        });
        const without = names.filter((name) => !withPos.includes(name));
        withPos.sort((a, b) => {
            const pa = place[a]; const pb = place[b];
            const ay = Number(pa.y); const by = Number(pb.y);
            if (ay !== by) return ay - by;
            const ax = Number(pa.x); const bx = Number(pb.x);
            if (ax !== bx) return ax - bx;
            return a < b ? -1 : (a > b ? 1 : 0);
        });
        return withPos.concat(without.sort());
    }

    // ── windowing ────────────────────────────────────────────────────────

    /**
     * Clip intervals to [from, to] and drop the ones entirely outside.
     *
     * A 30-day run is tens of thousands of intervals; drawing all of them freezes
     * the tab. Clipping rather than dropping is what makes zoom work: an interval
     * that starts before the window still contributes the part you can see.
     *
     * Returns the clipped intervals, each with the character, area, and clipped
     * bounds. A zero-width result is kept, not dropped: a character who is
     * *leaving* the window at that instant is present at the boundary, and
     * dropping it would make the view disagree with the data at exactly the
     * moment someone is looking closely.
     */
    function clipToWindow(intervals, from, to) {
        const lo = Math.min(from, to);
        const hi = Math.max(from, to);
        const out = [];
        (intervals || []).forEach((iv) => {
            const start = Number(iv.from_tick);
            const end = Number(iv.to_tick);
            if (!Number.isFinite(start) || !Number.isFinite(end)) return;
            if (end < lo || start > hi) return;
            out.push({
                character: iv.character,
                area: iv.area,
                from_tick: Math.max(start, lo),
                to_tick: Math.min(end, hi),
                clipped_start: start < lo,
                clipped_end: end > hi,
            });
        });
        return out;
    }

    /**
     * Aggregate intervals to at most `buckets` columns, returning character
     * occupancy per column rather than one rect per interval.
     *
     * Used by the zoomed-out overview. Returns a density per (character, bucket)
     * in 0..1 — the fraction of the bucket that character occupied — so a
     * character who was there the whole time and one who dashed through read
     * differently, which is the difference the view is for.
     */
    function bucketOccupancy(intervals, from, to, buckets) {
        const lo = Math.min(from, to);
        const hi = Math.max(from, to);
        const n = Math.max(1, Math.floor(buckets) || 1);
        const span = (hi - lo) || 1;
        const width = span / n;
        const acc = new Map(); // character -> Float array
        (intervals || []).forEach((iv) => {
            const start = Math.max(Number(iv.from_tick), lo);
            const end = Math.min(Number(iv.to_tick), hi);
            if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return;
            const first = Math.max(0, Math.floor((start - lo) / width));
            const last = Math.min(n - 1, Math.floor((Math.max(start, end - 1e-9) - lo) / width));
            let row = acc.get(iv.character);
            if (!row) { row = new Array(n).fill(0); acc.set(iv.character, row); }
            for (let b = first; b <= last; b += 1) {
                const bStart = lo + b * width;
                const bEnd = bStart + width;
                const overlap = Math.min(end, bEnd) - Math.max(start, bStart);
                if (overlap > 0) row[b] = Math.min(1, row[b] + overlap / width);
            }
        });
        const characters = Array.from(acc.keys()).sort();
        return { characters, buckets: n, from: lo, to: hi, width, density: acc };
    }

    // ── row packing and overlap detection ────────────────────────────────

    /**
     * Pack intervals into non-overlapping sub-rows within one lane, greedily.
     *
     * This is what makes a collision *visible*. Two characters in one room become
     * two bars on two stacked sub-rows; a single character who oscillates between
     * two rooms gets a zigzag between lanes. If everything were drawn at one y,
     * a collision and a sequential handover would look identical — which is the
     * difference the whole view exists to expose.
     *
     * Greedy first-fit is the right choice here and not merely the easy one: rows
     * are only ever read by eye, and first-fit keeps the row count within one of
     * optimal for interval graphs.
     *
     * Intervals must be sorted by `from_tick`. Touching intervals (one ends exactly
     * where the next begins) share a row, because that is not an overlap.
     */
    function packRows(intervals) {
        const sorted = (intervals || []).slice().sort(
            (a, b) => (a.from_tick - b.from_tick) || (a.to_tick - b.to_tick));
        const rowEnds = [];
        return sorted.map((iv) => {
            let row = rowEnds.findIndex((end) => end <= iv.from_tick);
            if (row === -1) { row = rowEnds.length; rowEnds.push(iv.to_tick); }
            else rowEnds[row] = iv.to_tick;
            return Object.assign({}, iv, { row });
        });
    }

    /**
     * Every pair of characters sharing one area-lane at one instant.
     *
     * Sweeps a lane's row-packed intervals and reports each overlapping pair once,
     * keyed so the same meeting is not reported twice from adjacent ticks. A "pair"
     * here is *a collision*, which is the point — the caller decides whether two
     * people in a room is expected.
     */
    function findCollisions(intervals) {
        const packed = packRows(intervals);
        const hits = [];
        for (let i = 0; i < packed.length; i += 1) {
            for (let j = i + 1; j < packed.length; j += 1) {
                const a = packed[i]; const b = packed[j];
                if (a.row === b.row) continue;              // packed apart: not a meeting
                if (a.area !== b.area) continue;            // different rooms
                if (a.character === b.character) continue;  // nobody meets themselves
                const from = Math.max(a.from_tick, b.from_tick);
                const to = Math.min(a.to_tick, b.to_tick);
                if (to > from) {
                    hits.push({
                        area: a.area,
                        first: a.character,
                        second: b.character,
                        from_tick: from,
                        to_tick: to,
                        ticks: to - from,
                    });
                }
            }
        }
        return hits;
    }

    /** Group collisions by area, ranked by total shared ticks. */
    function collisionsByArea(collisions) {
        const acc = new Map();
        (collisions || []).forEach((hit) => {
            let row = acc.get(hit.area);
            if (!row) { row = { area: hit.area, ticks: 0, pairs: new Map() }; acc.set(hit.area, row); }
            row.ticks += hit.ticks;
            const key = [hit.first, hit.second].sort().join(' + ');
            row.pairs.set(key, (row.pairs.get(key) || 0) + hit.ticks);
        });
        return Array.from(acc.values())
            .map((row) => ({
                area: row.area,
                ticks: row.ticks,
                pairs: Array.from(row.pairs.entries())
                    .map(([pair, ticks]) => ({ pair, ticks }))
                    .sort((a, b) => b.ticks - a.ticks),
            }))
            .sort((a, b) => b.ticks - a.ticks);
    }

    // ── layout ───────────────────────────────────────────────────────────

    const LAYOUT_DEFAULTS = {
        laneHeight: 22,
        rowHeight: 13,
        ribbonHeight: 3,
        laneGap: 8,
        paddingLeft: 150,
        paddingRight: 18,
        paddingTop: 10,
        paddingBottom: 30,
        width: 900,
        minRowHeight: 3,
    };

    /**
     * Turn a telemetry payload into drawable geometry.
     *
     * Returns lanes (with their packed rows), the totals needed to size the
     * canvas, and the collisions. Keeping this pure means the layout can be
     * asserted in a test without a DOM — the failure mode being guarded is
     * "renders without freezing and without dropping anyone", which a screenshot
     * cannot check.
     */
    function buildLayout(payload, options) {
        const o = Object.assign({}, LAYOUT_DEFAULTS, options || {});
        const from = Number(o.from !== undefined ? o.from : (payload && payload.from_tick) || 0);
        const to = Number(o.to !== undefined ? o.to
            : (payload && payload.to_tick) || maxTick(payload));
        const order = laneOrder((payload && payload.areas) || [],
            (payload && payload.area_placements) || null);
        const clipped = clipToWindow((payload && payload.intervals) || [], from, to);

        const byArea = new Map();
        order.forEach((area) => byArea.set(area, []));
        clipped.forEach((iv) => {
            if (!byArea.has(iv.area)) byArea.set(iv.area, []);   // unlisted area
            byArea.get(iv.area).push(iv);
        });

        const lanes = [];
        let y = o.paddingTop;
        let maxRows = 1;
        byArea.forEach((list, area) => {
            const packed = packRows(list);
            const rows = Math.max(1, packed.reduce((m, iv) => Math.max(m, iv.row + 1), 0));
            maxRows = Math.max(maxRows, rows);
            lanes.push({ area, rows, intervals: packed, top: y, height: rows * o.rowHeight });
            y += rows * o.rowHeight + o.laneGap;
        });

        const plotWidth = Math.max(10, o.width - o.paddingLeft - o.paddingRight);
        const height = y - o.laneGap + o.paddingBottom;
        const span = (to - from) || 1;
        const xOf = (tick) => o.paddingLeft + ((tick - from) / span) * plotWidth;

        return {
            from, to, width: o.width, height, lanes, maxRows,
            // Every padding the renderers read must be on the layout, not just
            // the ones buildLayout needs itself. A missing one becomes an
            // `undefined`/`NaN` SVG attribute, which the browser silently drops —
            // the grid lines and death rules then simply do not appear, with no
            // error anywhere. Pinned by a test.
            paddingLeft: o.paddingLeft,
            paddingRight: o.paddingRight,
            paddingTop: o.paddingTop,
            paddingBottom: o.paddingBottom,
            plotWidth,
            rowHeight: o.rowHeight,
            ribbonHeight: o.ribbonHeight,
            xOf,
            /** Row y for a packed interval, inside its lane. */
            yOf(lane, interval) {
                return lane.top + interval.row * o.rowHeight;
            },
            collisions: collisionsByArea(findCollisions(clipped)),
            visibleIntervals: clipped.length,
        };
    }

    function maxTick(payload) {
        let max = 0;
        ((payload && payload.intervals) || []).forEach((iv) => {
            if (Number(iv.to_tick) > max) max = Number(iv.to_tick);
        });
        return max;
    }

    // ── why-over-time ────────────────────────────────────────────────────

    /**
     * Bucket `why` groups into a stacked series over the time axis.
     *
     * The point is not the total: it is seeing a rule *start dominating*. A run
     * where `needs` holds steady at 48% and `traversal` climbs from nothing to a
     * third by day three is telling you the movement gates got worse, and a flat
     * ranked bar chart cannot show that.
     */
    function whyOverTime(events, from, to, buckets) {
        const lo = Math.min(from, to);
        const hi = Math.max(from, to);
        const n = Math.max(1, Math.floor(buckets) || 1);
        const width = ((hi - lo) || 1) / n;
        const series = new Map();   // group -> Int array
        (events || []).forEach((event) => {
            const group = event && event.why_group;
            if (!group) return;
            const tick = Number(event.tick);
            if (!Number.isFinite(tick) || tick < lo || tick > hi) return;
            const index = Math.min(n - 1, Math.floor((tick - lo) / width));
            let row = series.get(group);
            if (!row) { row = new Array(n).fill(0); series.set(group, row); }
            row[index] += 1;
        });
        return {
            groups: Array.from(series.keys()).sort(),
            buckets: n,
            from: lo,
            to: hi,
            width,
            series,
        };
    }

    // ── renderers ────────────────────────────────────────────────────────

    const CHARACTER_COLORS = [
        '#58a6ff', '#3fb950', '#e3b341', '#f85149', '#bc8cff', '#f778ba',
        '#56d4dd', '#d29922', '#7ee787', '#ff7b72', '#a5a5f5', '#79c0ff',
    ];

    /** Stable per-character colour, so a band keeps its identity across refreshes. */
    function characterColor(name, characters) {
        const index = (characters || []).indexOf(name);
        if (index < 0) return '#8b949e';
        return CHARACTER_COLORS[index % CHARACTER_COLORS.length];
    }

    function formatTick(tick, minutesPerTick) {
        if (!minutesPerTick) return `#${Math.round(tick)}`;
        const totalMinutes = tick * minutesPerTick;
        const day = Math.floor(totalMinutes / 1440);
        const hour = Math.floor((totalMinutes % 1440) / 60);
        const minute = Math.floor(totalMinutes % 60);
        const clock = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
        return day > 0 ? `d${day + 1} ${clock}` : clock;
    }

    /**
     * Draw the swimlanes. `layout` comes from `buildLayout`; `payload` supplies
     * the character roster, deaths and condition spans.
     *
     * Sizing is in **pixels, 1 layout unit = 1 px**, and the box scrolls both
     * ways. That is the whole difference between this being readable and being
     * cramped: a viewBox scaled to `width: 100%` shrinks a tall diagram to fit
     * the viewport width, so eighteen lanes each holding several stacked rows get
     * squashed into unreadable hairlines — and a cramped view is worse than no
     * view, because it looks like it answered the question.
     *
     * With one character selected the caller lays the chart out narrower, because
     * a lone lane stretched across the full card width is a meaningless smear.
     */
    function renderSwimlanes(layout, payload, options) {
        const o = Object.assign({ minutesPerTick: null, deaths: [], condition_spans: [] },
            options || {});
        // "Nothing to draw" is checked on the *data*, not on the lane count. A
        // payload can name eighteen areas and contain no intervals at all, and
        // drawing eighteen empty rails says "everybody stayed put" — which is a
        // claim the data does not make, and the opposite of what happened when a
        // stale character name matched nobody.
        if (!layout || !layout.lanes.length || !layout.visibleIntervals) {
            return `<div class="soak-empty-inline">No presence recorded in this window.`
                + ` Intervals are written on every area change, so the lanes fill in`
                + ` as soon as somebody moves.</div>`;
        }
        const characters = (payload && payload.characters) || [];
        const deaths = o.deaths || [];
        const spans = o.condition_spans || [];
        const W = layout.width;
        const H = layout.height;

        let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"`
            + ` class="soak-chart soak-spacetime" role="img">`;

        // Lane backgrounds + labels.
        layout.lanes.forEach((lane) => {
            svg += `<rect x="${layout.paddingLeft}" y="${lane.top.toFixed(1)}"`
                + ` width="${layout.plotWidth}" height="${lane.height.toFixed(1)}"`
                + ` class="soak-lane"/>`;
            svg += `<text x="${layout.paddingLeft - 8}" y="${(lane.top + lane.height / 2 + 3).toFixed(1)}"`
                + ` text-anchor="end" class="soak-lane-label">${esc(lane.area)}</text>`;
        });

        // Character bands. Hover title carries the full interval, because the
        // bar itself is a few pixels tall and the numbers are the point.
        layout.lanes.forEach((lane) => {
            lane.intervals.forEach((iv) => {
                const x0 = layout.xOf(iv.from_tick);
                const x1 = layout.xOf(iv.to_tick);
                const w = Math.max(1, x1 - x0);
                const y = layout.yOf(lane, iv);
                const h = Math.max(3, layout.rowHeight - 3);
                const color = characterColor(iv.character, characters);
                const title = `${iv.character} · ${lane.area} · `
                    + `${formatTick(iv.from_tick, o.minutesPerTick)}–`
                    + `${formatTick(iv.to_tick, o.minutesPerTick)}`;
                svg += `<rect x="${x0.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}"`
                    + ` height="${h}" fill="${color}" class="soak-band">`
                    + `<title>${esc(title)}</title></rect>`;
            });
        });

        // Condition ribbons, drawn under the band row they belong to. Subtle on
        // purpose: a ribbon marks an incident, and when a hundred characters each
        // carry one for most of the run, a loud ribbon turns the whole chart into
        // noise. The dot at the left edge is what carries the signal; the strip
        // only shows duration.
        layout.lanes.forEach((lane) => {
            const inLane = lane.intervals;
            spans.forEach((span) => {
                if (!inLane.some((iv) => iv.character === span.character)) return;
                const host = inLane.find((iv) => iv.character === span.character);
                if (!host) return;
                const x0 = layout.xOf(Math.max(span.from_tick, layout.from));
                const x1 = layout.xOf(Math.min(span.to_tick, layout.to));
                if (x1 < x0) return;
                const y = layout.yOf(lane, host) + layout.rowHeight - layout.ribbonHeight - 1;
                svg += `<rect x="${x0.toFixed(1)}" y="${y.toFixed(1)}"`
                    + ` width="${Math.max(1, x1 - x0).toFixed(1)}" height="${layout.ribbonHeight}"`
                    + ` class="soak-ribbon"><title>${esc(`${span.character}: ${span.condition}`)}`
                    + `</title></rect>`;
            });
        });

        // Deaths, marked on the band at the tick they occurred.
        deaths.forEach((death) => {
            const x = layout.xOf(death.tick);
            if (x < layout.paddingLeft - 1 || x > layout.width) return;
            svg += `<g class="soak-death"><line x1="${x.toFixed(1)}" y1="${layout.paddingTop}"`
                + ` x2="${x.toFixed(1)}" y2="${(layout.height - layout.paddingBottom).toFixed(1)}"`
                + ` class="soak-death-line"/>`
                + `<circle cx="${x.toFixed(1)}" cy="${layout.paddingTop}"`
                + ` r="3" class="soak-death-dot"><title>${esc(`${death.name} died — ${death.cause}`)}`
                + `</title></circle></g>`;
        });

        // Time axis.
        const tickCount = 8;
        for (let i = 0; i <= tickCount; i += 1) {
            const value = layout.from + ((layout.to - layout.from) * i) / tickCount;
            const x = layout.xOf(value);
            svg += `<line x1="${x.toFixed(1)}" y1="${layout.paddingTop}"`
                + ` x2="${x.toFixed(1)}" y2="${(layout.height - layout.paddingBottom).toFixed(1)}"`
                + ` class="soak-grid-line"/>`;
            svg += `<text x="${x.toFixed(1)}" y="${layout.height - 9}" text-anchor="middle"`
                + ` class="soak-axis-label">${esc(formatTick(value, o.minutesPerTick))}</text>`;
        }
        svg += '</svg>';
        return svg;
    }

    /**
     * Time x area occupancy heatmap: the zoomed-out companion to the swimlanes,
     * not a replacement. Shows where the world is busy; cannot show who.
     */
    function renderHeatmap(layout, payload, options) {
        const o = Object.assign({ buckets: 48, height: null }, options || {});
        if (!layout || !layout.lanes.length) {
            return '<div class="soak-empty-inline">No presence recorded for this run yet.</div>';
        }
        const byArea = new Map();
        layout.lanes.forEach((lane) => {
            const density = bucketOccupancy(lane.intervals, layout.from, layout.to, o.buckets);
            byArea.set(lane.area, density);
        });
        const n = Math.max(1, Math.floor(o.buckets) || 1);
        const cell = Math.max(3, Math.min(14, Math.floor(560 / n)));
        const labelWidth = 132;
        const width = labelWidth + n * cell + 12;
        const height = layout.lanes.length * cell + 20;

        let svg = `<svg viewBox="0 0 ${width} ${height}" class="soak-chart" role="img">`;
        layout.lanes.forEach((lane, row) => {
            const density = byArea.get(lane.area);
            const chars = density.characters;
            svg += `<text x="${labelWidth - 8}" y="${row * cell + cell / 2 + 3}"`
                + ` text-anchor="end" class="soak-lane-label">${esc(lane.area)}</text>`;
            for (let b = 0; b < n; b += 1) {
                let total = 0;
                chars.forEach((name) => {
                    total += density.density.get(name)[b] || 0;
                });
                if (total <= 0) continue;
                // Capped so one crowded room does not flatten every other lane.
                const intensity = Math.min(1, total / 4);
                const tick = layout.from + (b + 0.5) * density.width;
                svg += `<rect x="${(labelWidth + b * cell).toFixed(1)}"`
                    + ` y="${row * cell}" width="${cell}" height="${cell}"`
                    + ` fill="#58a6ff" opacity="${(0.12 + intensity * 0.8).toFixed(2)}">`
                    + `<title>${esc(`${lane.area} · ${total.toFixed(1)} present · `
                        + formatTick(tick, o.minutesPerTick))}</title></rect>`;
            }
        });
        svg += '</svg>';
        return svg;
    }

    /**
     * Restrict the view to one character.
     *
     * With twenty-three goblins in eighteen areas, the question is rarely "where
     * was everyone" — it is "what did *this one* do all day". That question is
     * unreadable in the full view: a single character's bands are spread across
     * every lane, interleaved with everybody else's, and identifying them by
     * colour across a crowded chart is exactly the kind of visual search this view
     * is supposed to make unnecessary.
     *
     * Isolating one character collapses the problem to a single lane, which is
     * where the answer lives. `null` clears the filter and shows everyone again.
     *
     * The area axis is **pruned to the areas that character actually visited**.
     * Keeping all eighteen would draw fourteen empty rails, which is worse than
     * useless: it reads as "they were nowhere" for rooms they simply never
     * entered, and it pushes the lanes you came to read off the screen. Relative
     * order is preserved among the kept lanes, so the sequence of rooms is still
     * legible.
     */
    function filterCharacter(payload, name) {
        if (!name) return payload;
        const intervals = (payload.intervals || []).filter((iv) => iv.character === name);
        const condition_spans = (payload.condition_spans || [])
            .filter((span) => span.character === name);
        const visited = new Set(intervals.map((iv) => iv.area));
        return Object.assign({}, payload, {
            characters: [name],
            intervals,
            condition_spans,
            areas: (payload.areas || []).filter((area) => visited.has(area)),
        });
    }

    /**
     * Collisions over a window, optionally narrowed to one character.
     *
     * Deliberately computed from the **unfiltered** interval set, and only then
     * narrowed. Isolating Arix and then finding that Arix met nobody is exactly
     * backwards: the reason to drill into one character is to see who they were
     * with, and filtering the other people out of the input destroys the only
     * question worth asking. So the chart narrows and the collision list does not
     * — it is narrowed by *who is in the pair*, not by deleting intervals.
     */
    function collisionsFor(payload, name, from, to) {
        const source = payload || {};
        const lo = from !== undefined ? from : (source.from_tick || 0);
        const hi = to !== undefined ? to : maxTick(source);
        const clipped = clipToWindow(source.intervals || [], lo, hi);
        const all = collisionsByArea(findCollisions(clipped));
        if (!name) return all;
        return all
            .map((row) => ({
                area: row.area,
                ticks: row.pairs
                    .filter((p) => p.pair.split(' + ').includes(name))
                    .reduce((sum, p) => sum + p.ticks, 0),
                pairs: row.pairs.filter((p) => p.pair.split(' + ').includes(name)),
            }))
            .filter((row) => row.pairs.length > 0)
            .sort((a, b) => b.ticks - a.ticks);
    }

    window.SoakSpacetime = {
        laneOrder,
        clipToWindow,
        bucketOccupancy,
        packRows,
        findCollisions,
        collisionsByArea,
        collisionsFor,
        buildLayout,
        whyOverTime,
        characterColor,
        filterCharacter,
        formatTick,
        renderSwimlanes,
        renderHeatmap,
        LAYOUT_DEFAULTS,
    };
}());
