/**
 * sprite-sheet-geometry — the pure half of the character-art sheet slicer.
 *
 * @module inspector/sprite-sheet-geometry — pure slice geometry: a grid is a frame plus interior dividers
 * @contributes SpriteSheetGeometry.cutsFromGrid/cellsFromCuts/clampCuts/moveDivider/addDivider/removeDivider/recountCuts/guttersFromProfile/cutsFromProfiles (pure)
 * @powers Character art — the "✂️ Split sheet" slicer's grid model and whitespace auto-detect
 * @relates consumed by inspector/sprite-sheet.js; DOM/canvas half lives there
 * @docs docs/virtualWorld/Characters/Character Images & Expression Packs.md
 *
 * Why this is a frame plus dividers rather than a row/column COUNT:
 * `computeCells` could only ever describe one shape — `width/cols × height/rows`
 * spanning the whole sheet. Real character and expression sheets are not that
 * shape: they carry a title banner, an outer margin, and panels of different
 * sizes side by side (one wide full-body pose beside a column of small detail
 * panels). For those, a count-based grid has no answer at all, which is why the
 * slicer fell back to one hand-drawn box per panel.
 *
 * A frame + interior dividers describes a strict superset of the old grid:
 *   - the frame excludes a banner/footer by dragging its edge, with no wasted cell;
 *   - uneven dividers give mixed panel sizes inside one grid;
 *   - evenly spaced dividers reproduce the old uniform grid *exactly*
 *     (`recountCuts` + `cellsFromCuts` round the same boundaries `computeCells`
 *     rounded), so the existing behaviour is preserved, not approximated.
 *
 * Everything here is pure so the geometry stays testable in the Node sandbox —
 * the canvas half in sprite-sheet.js cannot run there.
 */

// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

/** One output cell, in source pixels. */
interface SpriteCell {
    row: number;
    col: number;
    x: number;
    y: number;
    w: number;
    h: number;
}

/**
 * The slicer's grid, in source pixels.
 *
 * The frame is the region the grid covers; `colCuts`/`rowCuts` are the interior
 * dividers. A grid of R rows and C columns therefore has `rowCuts.length + 1`
 * rows and `colCuts.length + 1` columns — the counts are derived, never stored,
 * so dragging a divider can never desynchronise the two.
 */
interface SpriteCuts {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    colCuts: number[];
    rowCuts: number[];
}

/** Options for the cut models. */
interface SpriteCutOpts {
    /** Smallest permitted cell edge in source px. */
    minCell?: number;
}

/** Options for whitespace detection. */
interface SpriteDetectOpts extends SpriteCutOpts {
    /** A row/column is 'blank' when fewer than this fraction of it has ink. */
    blankRatio?: number;
    /** Ignore blank runs thinner than this (source px) — noise, not a gutter. */
    minRun?: number;
    /** Trim a frame edge inward by this much when no margin is detected. */
    edgePad?: number;
    /** Ink fraction above which a run counts as 'content' when flanking a gutter. */
    contentRatio?: number;
    /** How far from a run to look for flanking content, in PROFILE units. */
    flank?: number;
}

/** A per-row or per-column ink profile: 0 = all background, 1 = all foreground. */
type SpriteProfile = number[];

/** The public surface of inspector/sprite-sheet-geometry. */
interface SpriteSheetGeometryApi {
    MIN_CELL_PX: number;
    evenBoundaries(from: number, to: number, n: number): number[];
    cutsFromGrid(width: number, height: number, rows: number, cols: number): SpriteCuts;
    cellsFromCuts(cuts: SpriteCuts, labelTrim?: number): SpriteCell[];
    clampCuts(cuts: SpriteCuts, width: number, height: number, opts?: SpriteCutOpts): SpriteCuts;
    recountCuts(cuts: SpriteCuts, rows: number, cols: number, opts?: SpriteCutOpts): SpriteCuts;
    moveDivider(cuts: SpriteCuts, axis: 'x' | 'y', index: number, to: number, opts?: SpriteCutOpts): SpriteCuts;
    addDivider(cuts: SpriteCuts, axis: 'x' | 'y', at: number): SpriteCuts;
    removeDivider(cuts: SpriteCuts, axis: 'x' | 'y', index: number): SpriteCuts;
    hitDivider(cuts: SpriteCuts, axis: 'x' | 'y', at: number, tol: number, opts?: SpriteCutOpts): number;
    guttersFromProfile(profile: SpriteProfile, opts?: SpriteDetectOpts): number[];
    cutsFromProfiles(rowProfile: SpriteProfile, colProfile: SpriteProfile,
                     width: number, height: number, opts?: SpriteDetectOpts): SpriteCuts;
    profileRects(img: unknown): { rows: SpriteProfile; cols: SpriteProfile };
}

/** The public surface of inspector/sprite-sheet-geometry. */
(function () {
const SpriteSheetGeometry: SpriteSheetGeometryApi = (() => {
    'use strict';

    /**
     * Smallest cell edge, in source px. Below this a divider cannot move far
     * enough to be useful and a drag would produce slivers that crop to nothing.
     */
    const MIN_CELL_PX = 8;

    const clampNum = (n: unknown, fallback: number): number =>
        (typeof n === 'number' && Number.isFinite(n) ? n : fallback);

    /**
     * `n + 1` evenly spaced boundaries from `from` to `to`, each rounded
     * independently. Independent rounding is deliberate: it is what makes the
     * cells tile the span *exactly* (the last boundary lands on `to`), which is
     * the guarantee `computeCells` documented and its tests assert.
     */
    function evenBoundaries(from: number, to: number, n: number): number[] {
        const count = Math.max(1, Math.floor(n) || 1);
        const span = to - from;
        const out: number[] = [];
        for (let i = 0; i <= count; i++) {
            out.push(Math.round(from + (span * i) / count));
        }
        // Independent rounding can repeat a boundary on a span too small to hold
        // `count` cells; dedupe so a cell is never zero-width.
        return out.filter((v, i) => i === 0 || v > out[i - 1]);
    }

    /** A full-sheet grid: frame = the whole image, dividers evenly spaced. */
    function cutsFromGrid(width: number, height: number, rows: number, cols: number): SpriteCuts {
        const w = Math.max(0, Math.round(width));
        const h = Math.max(0, Math.round(height));
        const colEdges = evenBoundaries(0, w, cols);
        const rowEdges = evenBoundaries(0, h, rows);
        return {
            x0: 0, y0: 0, x1: w, y1: h,
            colCuts: colEdges.slice(1, -1),
            rowCuts: rowEdges.slice(1, -1),
        };
    }

    /**
     * Cells for a frame + dividers, in reading order (top-left first).
     *
     * `labelTrim` (0-0.9) drops that fraction off the BOTTOM of every cell, which
     * is where sprite sheets put the caption banner.
     */
    function cellsFromCuts(cuts: SpriteCuts, labelTrim?: number): SpriteCell[] {
        const trim = Math.min(0.9, Math.max(0, clampNum(labelTrim, 0)));
        const xs = [cuts.x0, ...cuts.colCuts, cuts.x1];
        const ys = [cuts.y0, ...cuts.rowCuts, cuts.y1];
        const cells: SpriteCell[] = [];
        for (let row = 0; row < ys.length - 1; row++) {
            for (let col = 0; col < xs.length - 1; col++) {
                const x = xs[col];
                const y = ys[row];
                const w = xs[col + 1] - x;
                const fullH = ys[row + 1] - y;
                const h = Math.max(1, Math.round(fullH * (1 - trim)));
                if (w > 0 && fullH > 0) cells.push({ row, col, x, y, w, h });
            }
        }
        return cells;
    }

    /**
     * Force a cuts object to be legal: a positive frame inside the sheet,
     * dividers ascending and at least `minCell` from their neighbours and the
     * frame edges. Returns a new object; never mutates the input.
     */
    function clampCuts(cuts: SpriteCuts, width: number, height: number,
                       opts: SpriteCutOpts = {}): SpriteCuts {
        const minCell = Math.max(1, Math.round(clampNum(opts.minCell, MIN_CELL_PX)));
        let x0 = Math.round(Math.min(Math.max(0, cuts.x0), Math.max(0, width)));
        let y0 = Math.round(Math.min(Math.max(0, cuts.y0), Math.max(0, height)));
        let x1 = Math.round(Math.min(Math.max(0, cuts.x1), Math.max(0, width)));
        let y1 = Math.round(Math.min(Math.max(0, cuts.y1), Math.max(0, height)));
        if (x1 - x0 < minCell) x1 = Math.min(width, x0 + minCell);
        if (y1 - y0 < minCell) y1 = Math.min(height, y0 + minCell);

        const fix = (list: number[], lo: number, hi: number): number[] => {
            const sorted = list.map(v => Math.round(v)).filter(v => v > lo && v < hi).sort((a, b) => a - b);
            const out: number[] = [];
            let cursor = lo;
            for (const v of sorted) {
                if (v - cursor < minCell) continue;
                out.push(v);
                cursor = v;
            }
            // Trailing dividers too close to the far edge are dropped rather than
            // nudged, so the last cell keeps its full width.
            const keep: number[] = [];
            for (let i = 0; i < out.length; i++) {
                if (hi - out[i] < minCell) break;
                keep.push(out[i]);
            }
            return keep;
        };

        return {
            x0, y0, x1, y1,
            colCuts: fix(cuts.colCuts, x0, x1),
            rowCuts: fix(cuts.rowCuts, y0, y1),
        };
    }

    /**
     * Change rows/cols while keeping the frame. Dividers are re-spaced evenly
     * inside the frame, so the numeric inputs stay an "add or remove a line"
     * control and the drag stays a "nudge a line" control — they cannot fight.
     */
    function recountCuts(cuts: SpriteCuts, rows: number, cols: number,
                         opts: SpriteCutOpts = {}): SpriteCuts {
        const next: SpriteCuts = {
            x0: cuts.x0, y0: cuts.y0, x1: cuts.x1, y1: cuts.y1,
            colCuts: [], rowCuts: [],
        };
        const colEdges = evenBoundaries(cuts.x0, cuts.x1, cols);
        const rowEdges = evenBoundaries(cuts.y0, cuts.y1, rows);
        next.colCuts = colEdges.slice(1, -1);
        next.rowCuts = rowEdges.slice(1, -1);
        return clampCuts(next, cuts.x1, cuts.y1, opts);
    }

    /**
     * Move the divider at `index` to `to`, clamped between its neighbours so a
     * line can never be dragged through another. Neighbours are the frame edges
     * at the ends.
     */
    function moveDivider(cuts: SpriteCuts, axis: 'x' | 'y', index: number, to: number,
                         opts: SpriteCutOpts = {}): SpriteCuts {
        const minCell = Math.max(1, Math.round(clampNum(opts.minCell, MIN_CELL_PX)));
        const list = axis === 'x' ? cuts.colCuts : cuts.rowCuts;
        const i = Math.floor(index);
        if (!Number.isFinite(i) || i < 0 || i >= list.length) return cuts;
        const lo = axis === 'x' ? cuts.x0 : cuts.y0;
        const hi = axis === 'x' ? cuts.x1 : cuts.y1;
        const lower = (i > 0 ? list[i - 1] : lo) + minCell;
        const upper = (i < list.length - 1 ? list[i + 1] : hi) - minCell;
        const value = Math.round(Math.min(Math.max(to, Math.min(lower, upper)), Math.max(lower, upper)));
        const next = list.slice();
        next[i] = value;
        return axis === 'x'
            ? { x0: cuts.x0, y0: cuts.y0, x1: cuts.x1, y1: cuts.y1, colCuts: next, rowCuts: cuts.rowCuts }
            : { x0: cuts.x0, y0: cuts.y0, x1: cuts.x1, y1: cuts.y1, colCuts: cuts.colCuts, rowCuts: next };
    }

    /** Insert a divider, keeping the list sorted. */
    function addDivider(cuts: SpriteCuts, axis: 'x' | 'y', at: number): SpriteCuts {
        const value = Math.round(at);
        const list = (axis === 'x' ? cuts.colCuts : cuts.rowCuts).slice();
        if (!Number.isFinite(value)) return cuts;
        list.push(value);
        list.sort((a, b) => a - b);
        return axis === 'x'
            ? { x0: cuts.x0, y0: cuts.y0, x1: cuts.x1, y1: cuts.y1, colCuts: list, rowCuts: cuts.rowCuts }
            : { x0: cuts.x0, y0: cuts.y0, x1: cuts.x1, y1: cuts.y1, colCuts: cuts.colCuts, rowCuts: list };
    }

    /** Drop the divider at `index` (double-click on a line). */
    function removeDivider(cuts: SpriteCuts, axis: 'x' | 'y', index: number): SpriteCuts {
        const list = axis === 'x' ? cuts.colCuts : cuts.rowCuts;
        const i = Math.floor(index);
        if (!Number.isFinite(i) || i < 0 || i >= list.length) return cuts;
        const next = list.slice();
        next.splice(i, 1);
        return axis === 'x'
            ? { x0: cuts.x0, y0: cuts.y0, x1: cuts.x1, y1: cuts.y1, colCuts: next, rowCuts: cuts.rowCuts }
            : { x0: cuts.x0, y0: cuts.y0, x1: cuts.x1, y1: cuts.y1, colCuts: cuts.colCuts, rowCuts: next };
    }

    /**
     * Index of the divider within `tol` of `at`, or -1.
     *
     * `at`/`tol` are in the SAME space as the cuts. Callers convert from pointer
     * coordinates first and pass a screen-space tolerance, because a fixed pixel
     * tolerance is unusable at a different zoom.
     */
    function hitDivider(cuts: SpriteCuts, axis: 'x' | 'y', at: number, tol: number,
                        opts: SpriteCutOpts = {}): number {
        const minCell = Math.max(1, Math.round(clampNum(opts.minCell, MIN_CELL_PX)));
        const list = axis === 'x' ? cuts.colCuts : cuts.rowCuts;
        const t = Math.abs(tol);
        // Nearest first, so overlapping tolerance bands still resolve to the
        // closest line rather than the lowest index.
        let best = -1;
        let bestDist = Infinity;
        for (let i = 0; i < list.length; i++) {
            const d = Math.abs(list[i] - at);
            if (d <= t && d < bestDist) { bestDist = d; best = i; }
        }
        if (best >= 0) return best;
        // A miss still counts when the two lines are closer together than the
        // tolerance (otherwise a dense grid has dead zones between its lines).
        for (let i = 0; i < list.length; i++) {
            if (at > list[i] - t && at < list[i] + t) {
                const dist = Math.abs(list[i] - at);
                if (dist < bestDist) { bestDist = dist; best = i; }
            }
        }
        return best;
    }

    /**
     * Centres of the blank runs in an ink profile, as divider candidates.
     *
     * A run touching the start or end of the profile is a margin, not a gutter —
     * the caller turns those into the frame edges — so they are not returned
     * here. Runs thinner than `minRun` are noise (the white inside an eye, the
     * gap in a letter) and are ignored.
     *
     * A run is only a gutter when it has CONTENT on both sides within `flank`.
     * This is the rule that makes the difference on a real sheet: the blank space
     * below the last row of panels is a perfectly good blank run, but it is
     * followed only by a small footer caption, so it is the outside of the grid
     * and not a divider inside it. Requiring ink on both sides is what stops the
     * proposal growing a row for every caption and every margin.
     */
    function guttersFromProfile(profile: SpriteProfile, opts: SpriteDetectOpts = {}): number[] {
        if (!profile || !profile.length) return [];
        const blankRatio = clampNum(opts.blankRatio, 0.01);
        const minRun = Math.max(1, Math.round(clampNum(opts.minRun, 8)));
        const contentRatio = clampNum(opts.contentRatio, 0.05);
        // `flank` is in PROFILE UNITS, like every other value in this function,
        // and defaults to a fraction of the profile rather than a multiple of
        // `minRun`. That matters: `minRun` reaching here has usually already been
        // downscaled from source pixels into samples by `cutsFromProfiles`, so a
        // default derived from it shrinks with the sampling rate and stops being
        // able to reach the art at all. Scaling off the profile length holds up
        // whatever the sample size — measured 10% of the profile finds the
        // gutters on a 1200px sheet and still rejects the trailing margin run.
        const flank = Math.max(2, Math.round(clampNum(opts.flank, profile.length * 0.1)));

        const hasContent = (from: number, to: number): boolean => {
            const lo = Math.max(0, from);
            const hi = Math.min(profile.length - 1, to);
            for (let i = lo; i <= hi; i++) if (profile[i] > contentRatio) return true;
            return false;
        };

        const out: number[] = [];
        let start = -1;
        for (let i = 0; i <= profile.length; i++) {
            const blank = i < profile.length && profile[i] <= blankRatio;
            if (blank && start < 0) start = i;
            if (!blank && start >= 0) {
                const end = i;                 // blank run is [start, end)
                const isMargin = start === 0 || end === profile.length;
                if (!isMargin && end - start >= minRun
                        && hasContent(start - 1 - flank, start - 1)
                        && hasContent(end, end + flank)) {
                    out.push((start + end) / 2);
                }
                start = -1;
            }
        }
        return out;
    }

    /**
     * Propose a whole grid from per-row and per-column ink profiles.
     *
     * The frame is the content bounding box — so a uniform outer margin is
     * trimmed automatically and a sheet photographed with a border still fits.
     * Interior gutters become the dividers, which is what gives a title banner
     * its own band and separates a wide panel from the narrow ones beside it.
     *
     * This PROPOSES; it never asserts. A sheet with no clean whitespace yields
     * no dividers and the caller falls back to an even grid, and every value here
     * remains draggable.
     */
    function cutsFromProfiles(rowProfile: SpriteProfile, colProfile: SpriteProfile,
                              width: number, height: number,
                              opts: SpriteDetectOpts = {}): SpriteCuts {
        const minCell = Math.max(1, Math.round(clampNum(opts.minCell, MIN_CELL_PX)));
        const minRun = Math.max(1, Math.round(clampNum(opts.minRun, 8)));
        const edgePad = Math.max(0, Math.round(clampNum(opts.edgePad, 0)));
        const blankRatio = clampNum(opts.blankRatio, 0.01);

        // A profile is a SAMPLE, not the image: `profileRects` caps the long edge
        // at 400px so detection stays fast on a 4000px sheet. Its indices are
        // therefore in sample space and must be scaled back into source pixels,
        // or every cut lands at the wrong place on anything bigger than the cap.
        const colLen = colProfile ? colProfile.length : 0;
        const rowLen = rowProfile ? rowProfile.length : 0;
        const colScale = colLen > 0 && width > 0 ? width / colLen : 1;
        const rowScale = rowLen > 0 && height > 0 ? height / rowLen : 1;
        const colMinRun = Math.max(1, Math.min(colLen || 1, minRun / colScale));
        const rowMinRun = Math.max(1, Math.min(rowLen || 1, minRun / rowScale));

        // Leading/trailing blank run -> frame edge. Returns sample indices.
        const contentBox = (profile: SpriteProfile): [number, number] | null => {
if (!profile || !profile.length) return null;
            let start = 0;
            let end = profile.length;
            while (start < end && profile[start] <= blankRatio) start++;
            while (end > start && profile[end - 1] <= blankRatio) end--;
            // Blank to both edges means no content at all in that axis; keep it
            // whole rather than collapsing the frame to nothing.
            if (start >= end) return null;
            return [start, end];
        };

        const colBox = contentBox(colProfile);
        const rowBox = contentBox(rowProfile);
        const x0 = Math.min(width, colBox ? colBox[0] * colScale : 0) + edgePad;
        const y0 = Math.min(height, rowBox ? rowBox[0] * rowScale : 0) + edgePad;
        // The `max` keeps a near-empty content box from collapsing the frame, but
        // it must stay capped at the sheet: letting it push past the edge made
        // clampCuts snap the frame out to the FULL width, turning a tight crop
        // into the whole sheet.
        const x1 = Math.min(width, Math.max(x0 + minCell, colBox ? colBox[1] * colScale : width)) - edgePad;
        const y1 = Math.min(height, Math.max(y0 + minCell, rowBox ? rowBox[1] * rowScale : height)) - edgePad;
        if (x1 - x0 < minCell || y1 - y0 < minCell) return cutsFromGrid(width, height, 1, 1);

        // Gutters are computed on the FULL profile (a gutter's position is measured
        // against the whole sheet, not the trimmed frame), then scaled into source
        // pixels and filtered to the frame.
        const scaleCuts = (profile: SpriteProfile, scale: number, lo: number, hi: number,
                           run: number): number[] =>
            guttersFromProfile(profile, { ...opts, minRun: run })
                .map(v => v * scale)
                .filter(v => v > lo && v < hi);

        const colCuts = scaleCuts(colProfile, colScale, x0, x1, colMinRun);
        const rowCuts = scaleCuts(rowProfile, rowScale, y0, y1, rowMinRun);

        // A sheet has at most a couple of dozen panels per axis. Past that the
        // detection has locked onto art whitespace rather than gutters, and a
        // proposal that large is worse than no proposal: it would hand the author
        // hundreds of slivers instead of a grid to drag. Callers treat "no
        // dividers" as "fall back to the even grid", which is a safe answer.
        const MAX_DIVIDERS = 16;
        if (colCuts.length > MAX_DIVIDERS || rowCuts.length > MAX_DIVIDERS) {
            return clampCuts({ x0, y0, x1, y1, colCuts: [], rowCuts: [] }, width, height, { minCell });
        }
        return clampCuts({ x0, y0, x1, y1, colCuts, rowCuts }, width, height, { minCell });
    }

    /**
     * Ink profiles for an image: for each row/column, the fraction of pixels
     * that differ from the sheet's background.
     *
     * "Background" is taken as the modal luminance of the sheet rather than
     * assumed white, because dark-background sheets exist and a white-keyed
     * detector reports them as 100% ink and finds no gutters at all.
     *
     * The image is sampled, not read at full size: a 4000px sheet is reduced to
     * `maxSamples` px on the long edge first, which is ample for gutter
     * detection and keeps this a few milliseconds.
     */
    function profileRects(img: unknown): { rows: SpriteProfile; cols: SpriteProfile } {
        const empty = { rows: [], cols: [] };
        const src = img as { naturalWidth?: number; naturalHeight?: number; width?: number; height?: number };
        const natW = Number(src && (src.naturalWidth || src.width));
        const natH = Number(src && (src.naturalHeight || src.height));
        if (!natW || !natH || typeof document === 'undefined') return empty;
        const maxSamples = 400;
        const scale = Math.min(1, maxSamples / Math.max(natW, natH));
        const w = Math.max(1, Math.round(natW * scale));
        const h = Math.max(1, Math.round(natH * scale));
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) return empty;
        ctx.drawImage(img as CanvasImageSource, 0, 0, w, h);
        let data: Uint8ClampedArray;
        try {
            data = ctx.getImageData(0, 0, w, h).data;
        } catch (err) {
            // A cross-origin image taints the canvas; nothing to detect from.
            return empty;
        }

        const lum: number[] = new Array(w * h);
        const hist = new Uint32Array(256);
        for (let i = 0; i < w * h; i++) {
            const p = i * 4;
            // Rec. 601 luma; alpha is ignored because a sheet is opaque by the
            // time it reaches here, and a transparent PNG reads as black ink.
            const v = (data[p] * 299 + data[p + 1] * 587 + data[p + 2] * 114) / 1000;
            lum[i] = v;
            hist[Math.max(0, Math.min(255, Math.round(v)))]++;
        }
        // Modal luminance = the sheet's background. Falls back to white if the
        // histogram is empty.
        let modal = 255;
        let best = 0;
        for (let i = 0; i < 256; i++) if (hist[i] > best) { best = hist[i]; modal = i; }
        // Tolerance in luminance steps. 28 is wide enough for a paper-textured
        // or JPEG-compressed background and narrow enough to still catch art.
        const tol = 28;

        const rows: SpriteProfile = new Array(h);
        const cols: SpriteProfile = new Array(w);
        for (let y = 0; y < h; y++) {
            let ink = 0;
            const base = y * w;
            for (let x = 0; x < w; x++) if (Math.abs(lum[base + x] - modal) > tol) ink++;
            rows[y] = ink / w;
        }
        for (let x = 0; x < w; x++) {
            let ink = 0;
            for (let y = 0; y < h; y++) if (Math.abs(lum[y * w + x] - modal) > tol) ink++;
            cols[x] = ink / h;
        }
        return { rows, cols };
    }

    return {
        MIN_CELL_PX,
        evenBoundaries, cutsFromGrid, cellsFromCuts, clampCuts, recountCuts,
        moveDivider, addDivider, removeDivider, hitDivider,
        guttersFromProfile, cutsFromProfiles, profileRects,
    };
})();

(window as unknown as { SpriteSheetGeometry: SpriteSheetGeometryApi }).SpriteSheetGeometry = SpriteSheetGeometry;
})();