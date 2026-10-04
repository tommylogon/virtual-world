/**
 * sprite-sheet — slice an uploaded character-art sheet into one image per slot.
 *
 * @module inspector/sprite-sheet — grid/box-slice a sprite sheet into expression slots
 * @contributes SpriteSheet.computeCells/parseNames/defaultNames/clampBox (pure) + openDialog
 * @powers Character art — the "✂️ Split sheet" control in the character Expression Pack panel
 * @relates reads/writes via ApiClient.uploadNodeImage and InspectorHelpers expression slots; geometry in inspector/sprite-sheet-geometry.js
 * @docs docs/virtualWorld/Characters/Character Images & Expression Packs.md
 *
 * Why a client-side slice: the sheet is one image the user already has on disk;
 * cropping happens in a canvas in the browser and each tile is uploaded to its
 * own expression slot through the existing single-image endpoint. No server
 * change and no base64 in the scenario — the server still owns the files.
 *
 * The grid is a FRAME plus interior dividers, not a rows/cols count (task-678).
 * Real sheets are a title banner, an outer margin, and panels of mixed sizes —
 * a wide full-body pose beside a column of small detail panels — and a count
 * describes none of that. So the user drags:
 *   - the frame edges, to fit the grid onto the art and off a banner/footer;
 *   - an interior divider, to make rows/columns uneven (mixed panel sizes);
 *   - and "Auto-fit" proposes the whole grid from the sheet's whitespace
 *     gutters, which is what removes the hand-drawn box per panel.
 * Every proposed value stays draggable — detection proposes, it never asserts.
 *
 * "Draw boxes" remains as the escape hatch for genuinely irregular layouts, but
 * an existing box can now be moved and resized instead of deleted and redrawn.
 *
 * Two views sit side by side: the sheet with its overlay, and a live strip of
 * the actual crops. The strip is the only way to tell whether a cut landed on an
 * eyebrow before uploading, which is what made the old dialog a guess-then-check.
 *
 * The slice geometry is split out as pure functions (inspector/sprite-sheet-
 * geometry.js) because the canvas half cannot run in the Node unit sandbox;
 * test_sprite_sheet_geometry.js covers the geometry, not the DOM.
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

/** One cell of a slice, in source pixels. */
interface SpriteCell {
    row: number;
    col: number;
    x: number;
    y: number;
    w: number;
    h: number;
}

/** Options for `computeCells`. */
interface SpriteCellOpts {
    labelTrim?: number;
}

/** A clamped drag rectangle, in source pixels. */
interface SpriteBox {
    x: number;
    y: number;
    w: number;
    h: number;
    name?: string;
    label?: string;
    draft?: boolean;
    cell?: SpriteCell;
}

/** A box the user is currently dragging, before it is committed. */
interface SpriteDraft {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
}

/** A crop target ready for upload. */
interface SpriteTarget {
    x: number;
    y: number;
    w: number;
    h: number;
    name: string;
}

/** The slicer's grid: a frame plus interior dividers, in source pixels. */
interface SpriteCuts {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    colCuts: number[];
    rowCuts: number[];
}

/** What a press grabbed: a frame edge/corner, a divider, a box handle, or a box. */
type SpriteGrabKind = 'frame-n1' | 'frame-n2' | 'frame-e1' | 'frame-e2'
    | 'frame-s1' | 'frame-s2' | 'frame-w1' | 'frame-w2'
    | 'frame-nw' | 'frame-ne' | 'frame-sw' | 'frame-se'
    | 'col' | 'row' | 'box-move' | 'box-nw' | 'box-n' | 'box-ne'
    | 'box-sw' | 'box-s' | 'box-se' | 'box-e' | 'box-w';

/** A drag in progress. Positions are source pixels. */
interface SpriteDrag {
    kind: SpriteGrabKind;
    index?: number;
    startX: number;
    startY: number;
    orig: SpriteCuts | SpriteBox;
}

/** Everything the open dialog remembers while it is up. */
interface SpriteState {
    nodeId: string;
    kind: string;
    img: HTMLImageElement | null;
    file: File | null;
    boxes: SpriteBox[];
    draft: SpriteDraft | null;
    scale: number;
    /** Grid-mode geometry. Null until an image is loaded. */
    cuts: SpriteCuts | null;
    /** Natural-size offscreen copy of the sheet; source for every crop. */
    src: HTMLCanvasElement | null;
    drag: SpriteDrag | null;
    /** Index into `boxes` of the box showing handles, or -1. */
    selected: number;
    /** 'fit' scales the preview to the pane; 1 is one source px per screen px. */
    zoom: 'fit' | 1;
    /** Names aligned to the current cell list, parallel to `cells`. */
    names: string[];
    /** Detach document drag listeners on close. */
    releaseDrag: (() => void) | null;
}

/** A pointer event on the preview canvas. */
interface SpriteMouseEvent {
    clientX: number;
    clientY: number;
    preventDefault?(): void;
}

/** inspector/helpers.js is not declared in globals.d.ts. */
interface SpriteHelpers {
    EXPRESSION_ORDER?: string[];
    _exprCache?: Record<string, {
        expressions?: Record<string, unknown>;
        profile_image?: string;
        image?: string;
    }>;
    _refreshExpressionGrid?(nodeId: string, kind: string): void;
}

/** The public surface of inspector/sprite-sheet. */
interface SpriteSheetApi {
    computeCells(width: number, height: number, rows: number, cols: number,
                  opts?: SpriteCellOpts): SpriteCell[];
    clampBox(x0: number, y0: number, x1: number, y1: number, width: number, height: number,
             minSize?: number): SpriteBox | null;
    parseNames(text: unknown, count: number): string[];
    defaultNames(count: number): string[];
    defaultNameFor(index: number): string;
    slug(value: unknown): string;
    openDialog(nodeId: string, kind: string): void;
    closeDialog(): void;
    EMOTION_ORDER: string[];
}

/** The public surface of inspector/sprite-sheet. */
const _SpriteSheet: SpriteSheetApi = (() => {
    'use strict';

    /** inspector/helpers.js is not declared in globals.d.ts. */
    function _helpers(): SpriteHelpers | null {
        const holder = window as unknown as { InspectorHelpers?: SpriteHelpers };
        return holder.InspectorHelpers || null;
    }

    /** The pure geometry module, loaded before this one. */
    function _geometry(): typeof window.SpriteSheetGeometry | null {
        const holder = window as unknown as { SpriteSheetGeometry?: typeof window.SpriteSheetGeometry };
        return holder.SpriteSheetGeometry || null;
    }

    /** Null until `openDialog` runs, and null again after it closes. */
    let _state: SpriteState | null = null;

    // Fallback order, used only when InspectorHelpers is not loaded yet at call
    // time. InspectorHelpers.EXPRESSION_ORDER is the source of truth when present;
    // this must stay identical to it or the tile labels drift the moment the
    // helpers load after this module.
    const EMOTION_ORDER = ['neutral', 'happy', 'sad', 'angry', 'surprised',
        'fearful', 'disgusted', 'confused', 'determined', 'exhausted', 'smug',
        'worried', 'curious', 'embarrassed', 'proud', 'bored', 'suspicious',
        'hopeful', 'frustrated', 'relieved', 'defiant', 'sleepy', 'shocked',
        'amused', 'concerned', 'confident', 'nervous', 'playful', 'serious',
        'tearful', 'thoughtful'];

    //: A drawn box smaller than this (in source pixels, on either axis) is
    //: treated as a stray click, not a panel.
    const MIN_BOX_PX = 8;

    //: Screen-space grab radius for a divider or handle, in CSS px. Kept in
    //: screen space so a divider stays grabbable at every zoom level — a fixed
    //: source-px radius vanishes when the sheet is scaled down to fit.
    const GRAB_PX = 7;

    //: Length of a divider handle's drawn tail, in screen px.
    const HANDLE_PX = 9;

    /** Filename-safe key for an expression name (mirrors InspectorHelpers). */
    function slug(value: unknown): string {
        return String(value || '').trim().toLowerCase()
            .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    }

    /**
     * Source rectangles for a rows×cols grid over a sheet of `width`×`height`.
     *
     * Kept as the public, count-based entry point (the unit tests and any caller
     * outside the dialog use it) and now a thin wrapper over the frame+dividers
     * model, so the two can never disagree. Rows/cols are fractions of the sheet,
     * so the last row/column absorbs any rounding remainder — tiles always tile
     * the sheet exactly with no gaps or overlap. `labelTrim` (0-0.9) drops that
     * fraction off the BOTTOM of every cell, which is where sprite sheets put the
     * caption banner.
     *
     * @param {number} width - natural sheet width in px
     * @param {number} height - natural sheet height in px
     * @param {number} rows
     * @param {number} cols
     * @param {object} [opts] - { labelTrim } fraction of cell height to drop
     * @returns {Array<{row,col,x,y,w,h}>}
     */
    function computeCells(width: number, height: number, rows: number, cols: number,
                          opts: SpriteCellOpts = {}): SpriteCell[] {
        const G = _geometry();
        if (!G) return [];
        return G.cellsFromCuts(G.cutsFromGrid(width, height, rows, cols),
            Math.min(0.9, Math.max(0, Number(opts.labelTrim) || 0)));
    }

    /**
     * Normalise two drag corners into a clamped, positive-size box.
     *
     * Coordinates may be given in any order (dragging up/left is fine). The box
     * is clamped to the sheet and `null` is returned for a too-small drag so the
     * caller can treat it as a stray click rather than a panel.
     *
     * @param {number} x0 @param {number} y0 - first corner
     * @param {number} x1 @param {number} y1 - second corner
     * @param {number} width  - sheet width (clamp bound)
     * @param {number} height - sheet height (clamp bound)
     * @param {number} [minSize] - minimum width/height in px
     * @returns {{x:number,y:number,w:number,h:number}|null}
     */
    function clampBox(x0: number, y0: number, x1: number, y1: number, width: number,
                      height: number, minSize: number = MIN_BOX_PX): SpriteBox | null {
        const left = Math.max(0, Math.min(x0, x1));
        const top = Math.max(0, Math.min(y0, y1));
        const right = Math.min(width, Math.max(x0, x1));
        const bottom = Math.min(height, Math.max(y0, y1));
        const w = right - left;
        const h = bottom - top;
        if (w < minSize || h < minSize) return null;
        return { x: Math.round(left), y: Math.round(top), w: Math.round(w), h: Math.round(h) };
    }

    /**
     * Parse a user-typed name list into `count` keys, in cell order.
     *
     * Accepts commas or newlines. Blank entries stay blank (that cell is skipped
     * on upload), and extra entries beyond `count` are ignored. Names are
     * slugified so a custom key ("Ex-cited!") lands as `ex_cited`.
     *
     * @param {string} text
     * @param {number} count
     * @returns {string[]} length `count`
     */
    function parseNames(text: unknown, count: number): string[] {
        const n = Math.max(0, Math.floor(count) || 0);
        const parts = String(text || '').split(/[\n,]+/).map(slug).filter(Boolean);
        const out: string[] = [];
        for (let i = 0; i < n; i++) out.push(parts[i] || '');
        return out;
    }

    /**
     * Default names for `count` cells: the canonical 31-tile expression order
     * first, then blank for any overflow. The canonical order is read from
     * InspectorHelpers so the dialog and the gallery never drift apart.
     *
     * Overflow is deliberately left blank rather than filled with `slotN`
     * placeholders: the textarea's own contract is "blank = skip", so a sheet
     * wider than the authored vocabulary simply does not upload the extra
     * tiles, instead of inventing names for art nobody specified.
     *
     * @param {number} count
     * @returns {string[]}
     */
    function defaultNames(count: number): string[] {
        const n = Math.max(0, Math.floor(count) || 0);
        const helpers = _helpers();
        const base = (helpers && helpers.EXPRESSION_ORDER)
            ? helpers.EXPRESSION_ORDER.slice()
            : EMOTION_ORDER.slice();
        const out: string[] = base.slice(0, n);
        for (let i = out.length; i < n; i++) out.push('');
        return out;
    }

    /** Default name for the box at `index` (canonical order, then blank). */
    function defaultNameFor(index: number): string {
        return defaultNames(index + 1)[index];
    }

    // ── DOM / canvas half (not loaded in the Node unit sandbox) ──

    function _loadImage(file: File): Promise<HTMLImageElement> {
        return new Promise((resolve, reject) => {
            const url = URL.createObjectURL(file);
            const img = new Image();
            img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
            img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Could not read image')); };
            img.src = url;
        });
    }

    /**
     * A natural-size copy of the sheet, so every crop reads the same pixels.
     *
     * Bounded on purpose: a natural-size canvas is 4 bytes per pixel, so a
     * 4000×6000 sheet is 96 MB and a 8000×12000 one is 384 MB — enough to fail
     * or to stall the tab. Past the budget this returns null and callers crop
     * straight from the `<img>`, which is the original behaviour and needs no copy.
     */
    const SRC_COPY_MAX_PX = 40_000_000;

    function _buildSource(img: HTMLImageElement): HTMLCanvasElement | null {
        const w = img.naturalWidth;
        const h = img.naturalHeight;
        if (!w || !h || w * h > SRC_COPY_MAX_PX) return null;
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) return null;
        ctx.drawImage(img, 0, 0);
        return canvas;
    }

    function _modalRoot(): HTMLElement | null { return document.getElementById('sprite-sheet-modal'); }

    function closeDialog(): void {
        const s = _state;
        if (s && s.releaseDrag) s.releaseDrag();
        const root = _modalRoot();
        if (root) root.remove();
        _state = null;
    }

    function _mode(): 'boxes' | 'grid' {
        const el = document.querySelector('input[name="ss-mode"]:checked') as HTMLInputElement | null;
        return (el && el.value) === 'boxes' ? 'boxes' : 'grid';
    }

    function _readControls(): { rows: number; cols: number; labelTrim: number; kind: string } {
        const val = (id: string, fallback: number) => {
            const el = document.getElementById(id) as HTMLInputElement | null;
            const n = el ? parseInt(el.value, 10) : NaN;
            return Number.isFinite(n) ? n : fallback;
        };
        const trimEl = document.getElementById('ss-label-trim') as HTMLInputElement | null;
        const trimPct = trimEl ? parseFloat(trimEl.value) : 10;
        const kindEl = document.querySelector('input[name="ss-kind"]:checked') as HTMLInputElement | null;
        return {
            rows: Math.min(20, Math.max(1, val('ss-rows', 3))),
            cols: Math.min(20, Math.max(1, val('ss-cols', 4))),
            labelTrim: Math.min(0.9, Math.max(0, (Number.isFinite(trimPct) ? trimPct : 10) / 100)),
            kind: (kindEl && kindEl.value) || 'profile',
        };
    }

    // ── names ────────────────────────────────────────────────────────
    // Names are aligned to the cell LIST by index, and the cell list changes
    // whenever a divider is added or removed. Growing the list appends the next
    // canonical key; shrinking it drops the tail. What is kept, is kept — so
    // nudging a divider never renames the tile the author already named.

    /** Name for cell `index`, falling back to the canonical order. */
    function _nameAt(index: number): string {
        const s = _state;
        if (s && s.names[index]) return s.names[index];
        return defaultNameFor(index);
    }

    /** Re-fit `names` to `count` cells, preserving what already fits. */
    function _resizeNames(count: number): void {
        const s = _state;
        if (!s) return;
        const kept = s.names.slice(0, count);
        while (kept.length < count) kept.push(defaultNameFor(kept.length));
        s.names = kept;
        _writeNamesText();
    }

    function _writeNamesText(): void {
        const ta = document.getElementById('ss-names') as HTMLTextAreaElement | null;
        const s = _state;
        if (!ta || !s) return;
        // Preserve the author's focus/caret so typing is not interrupted.
        const active = document.activeElement === ta;
        const start = active ? ta.selectionStart : -1;
        ta.value = s.names.join(', ');
        if (active && start >= 0) ta.setSelectionRange(start, start);
    }

    function _readNamesText(): void {
        const ta = document.getElementById('ss-names') as HTMLTextAreaElement | null;
        const s = _state;
        if (!ta || !s) return;
        s.names = parseNames(ta.value, s.names.length);
        // parseNames blanks a missing entry; keep the canonical default in state
        // so clearing a name in the box list can be undone by typing again.
        s.names = s.names.map((v, i) => v || defaultNameFor(i));
    }

    // ── cells ────────────────────────────────────────────────────────

    /** The current cell list for grid mode, or null in boxes mode / no image. */
    function _cells(): SpriteCell[] | null {
        const s = _state;
        const G = _geometry();
        if (!s || !G || !s.cuts) return null;
        return G.cellsFromCuts(s.cuts, _readControls().labelTrim);
    }

    /** All crop targets for the current mode: [{x,y,w,h,name}]. */
    function _targets(): SpriteTarget[] {
        const s = _state;
        if (!s) return [];
        if (_mode() === 'boxes') {
            return s.boxes
                .map(b => ({ x: b.x, y: b.y, w: b.w, h: b.h, name: b.name as string }))
                .filter(t => t.name);
        }
        const cells = _cells();
        if (!cells) return [];
        return cells.map((c, i) => ({ x: c.x, y: c.y, w: c.w, h: c.h, name: _nameAt(i) }))
            .filter(t => t.name);
    }

    // ── preview ──────────────────────────────────────────────────────

    /** Scale for the current zoom and pane size. */
    function _fitScale(): number {
        const s = _state;
        if (!s || !s.img) return 1;
        const wrap = document.getElementById('ss-preview-wrap');
        const availW = (wrap && wrap.clientWidth) || 560;
        const availH = (wrap && wrap.clientHeight) || 520;
        if (s.zoom === 1) return 1;
        return Math.min(1, availW / s.img.naturalWidth, availH / s.img.naturalHeight);
    }

    function _toSource(ev: SpriteMouseEvent): { x: number; y: number } {
        const canvas = document.getElementById('ss-preview') as HTMLCanvasElement | null;
        const s = _state;
        if (!canvas || !s) return { x: 0, y: 0 };
        const rect = canvas.getBoundingClientRect();
        const sx = rect.width ? canvas.width / rect.width : 1;
        const sy = rect.height ? canvas.height / rect.height : 1;
        return {
            x: (ev.clientX - rect.left) * sx / s.scale,
            y: (ev.clientY - rect.top) * sy / s.scale,
        };
    }

/**
 * The frame grips, in source pixels: four corners plus two per edge.
 *
 * Two per edge rather than one at the midpoint, because the midpoint is exactly
 * where an even grid puts a divider — and a divider is hit-tested first, since a
 * line running along the frame edge is more often meant to be dragged inward. With
 * a single midpoint grip, the north and south frame edges were unreachable on any
 * even-column or even-row grid, which is most of them.
 */
function _frameHandles(cuts: SpriteCuts): Record<string, { x: number; y: number }> {
        const q1x = cuts.x0 + (cuts.x1 - cuts.x0) * 0.25;
        const q3x = cuts.x0 + (cuts.x1 - cuts.x0) * 0.75;
        const q1y = cuts.y0 + (cuts.y1 - cuts.y0) * 0.25;
        const q3y = cuts.y0 + (cuts.y1 - cuts.y0) * 0.75;
        return {
            'frame-nw': { x: cuts.x0, y: cuts.y0 },
            'frame-n1': { x: q1x, y: cuts.y0 },
            'frame-n2': { x: q3x, y: cuts.y0 },
            'frame-ne': { x: cuts.x1, y: cuts.y0 },
            'frame-e1': { x: cuts.x1, y: q1y },
            'frame-e2': { x: cuts.x1, y: q3y },
            'frame-se': { x: cuts.x1, y: cuts.y1 },
            'frame-s1': { x: q1x, y: cuts.y1 },
            'frame-s2': { x: q3x, y: cuts.y1 },
            'frame-sw': { x: cuts.x0, y: cuts.y1 },
            'frame-w1': { x: cuts.x0, y: q1y },
            'frame-w2': { x: cuts.x0, y: q3y },
        };
    }

    /** The eight resize grips of a box, in source pixels. */
    function _boxHandles(box: SpriteBox): Record<string, { x: number; y: number }> {
        const mx = box.x + box.w / 2;
        const my = box.y + box.h / 2;
        return {
            'box-nw': { x: box.x, y: box.y },
            'box-n': { x: mx, y: box.y },
            'box-ne': { x: box.x + box.w, y: box.y },
            'box-e': { x: box.x + box.w, y: my },
            'box-se': { x: box.x + box.w, y: box.y + box.h },
            'box-s': { x: mx, y: box.y + box.h },
            'box-sw': { x: box.x, y: box.y + box.h },
            'box-w': { x: box.x, y: my },
        };
    }

    /** Redraw the sheet preview with the current grid / boxes. */
    function _drawOverlay() {
        const s = _state;
        if (!s || !s.img) return;
        const canvas = document.getElementById('ss-preview') as HTMLCanvasElement | null;
        if (!canvas) return;
        const img = s.img;
        const scale = _fitScale();
        const dw = Math.max(1, Math.round(img.naturalWidth * scale));
        const dh = Math.max(1, Math.round(img.naturalHeight * scale));
        if (canvas.width !== dw || canvas.height !== dh) { canvas.width = dw; canvas.height = dh; }
        s.scale = scale;
        const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
        ctx.clearRect(0, 0, dw, dh);
        ctx.drawImage(s.src || img, 0, 0, dw, dh);

        const tol = GRAB_PX / scale;
        const boxes = _mode() === 'boxes';

        if (!boxes && s.cuts) {
            const cuts = s.cuts;
            const cells = G_cells(s);
            const labelTrim = _readControls().labelTrim;

            // Dim everything outside the frame so a banner/footer being excluded
            // reads as excluded rather than merely cut off.
            ctx.fillStyle = 'rgba(0,0,0,0.45)';
            ctx.beginPath();
            ctx.rect(0, 0, dw, dh);
            ctx.rect(cuts.x0 * scale, cuts.y0 * scale,
                (cuts.x1 - cuts.x0) * scale, (cuts.y1 - cuts.y0) * scale);
            ctx.fill('evenodd');

            // Interior dividers.
            ctx.strokeStyle = 'rgba(255,255,255,0.55)';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 4]);
            ctx.beginPath();
            cuts.colCuts.forEach(cx => {
                ctx.moveTo(cx * scale, cuts.y0 * scale);
                ctx.lineTo(cx * scale, cuts.y1 * scale);
            });
            cuts.rowCuts.forEach(cy => {
                ctx.moveTo(cuts.x0 * scale, cy * scale);
                ctx.lineTo(cuts.x1 * scale, cy * scale);
            });
            ctx.stroke();
            ctx.setLineDash([]);

            // The trim line, so the caption banner height is visible.
            if (labelTrim > 0) {
                ctx.strokeStyle = 'rgba(255, 120, 120, 0.95)';
                ctx.setLineDash([4, 3]);
                ctx.beginPath();
                (cells || []).forEach(cell => {
                    const cutY = cell.y + cell.h;
                    ctx.moveTo(cell.x * scale, cutY);
                    ctx.lineTo((cell.x + cell.w) * scale, cutY);
                });
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // The frame, bold: it is the thing being fitted to the art.
            ctx.strokeStyle = '#e3b341';
            ctx.lineWidth = 2;
            ctx.strokeRect(cuts.x0 * scale, cuts.y0 * scale,
                (cuts.x1 - cuts.x0) * scale, (cuts.y1 - cuts.y0) * scale);

            // Cells + labels.
            ctx.font = '11px sans-serif';
            ctx.textBaseline = 'top';
            (cells || []).forEach((cell, i) => {
                const x = cell.x * scale;
                const y = cell.y * scale;
                const w = cell.w * scale;
                const h = cell.h * scale;
                ctx.strokeStyle = 'rgba(90, 200, 255, 0.9)';
                ctx.lineWidth = 1;
                ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
                _tag(ctx, _nameAt(i), x + 2, y + 2);
            });

            // Grips: every frame grip, plus a nub at the MIDDLE of every divider. The nub is
            // deliberately not at the frame edge — a press near the frame is a frame
            // grip now, so a nub there would advertise the wrong target.
            Object.values(_frameHandles(cuts)).forEach(h =>
                _drawGrip(ctx, h.x * scale, h.y * scale, tol, scale));
            const midY = (cuts.y0 + cuts.y1) / 2;
            const midX = (cuts.x0 + cuts.x1) / 2;
            cuts.colCuts.forEach(cx => _drawGrip(ctx, cx * scale, midY * scale, tol, scale));
            cuts.rowCuts.forEach(cy => _drawGrip(ctx, midX * scale, cy * scale, tol, scale));
            return;
        }

        // Boxes mode.
        const rects = s.boxes.map((b, i) => {
            const selected = i === s.selected;
            return { b, label: b.name || '(unnamed)', selected };
        });
        ctx.lineWidth = 2;
        ctx.font = '11px sans-serif';
        ctx.textBaseline = 'top';
        rects.forEach(r => {
            const b = r.b;
            const x = b.x * scale;
            const y = b.y * scale;
            ctx.strokeStyle = r.selected ? '#e3b341' : 'rgba(90, 200, 255, 0.95)';
            ctx.strokeRect(x + 0.5, y + 0.5, b.w * scale - 1, b.h * scale - 1);
            _tag(ctx, r.label, x + 2, y + 2);
            if (r.selected) {
                Object.values(_boxHandles(b)).forEach(h =>
                    _drawGrip(ctx, h.x * scale, h.y * scale, tol, scale));
            }
        });
        if (s.draft) {
            const d = s.draft;
            const box = clampBox(d.x0, d.y0, d.x1, d.y1, img.naturalWidth, img.naturalHeight, 0);
            if (box) {
                ctx.strokeStyle = 'rgba(255, 200, 80, 0.95)';
                ctx.setLineDash([4, 3]);
                ctx.strokeRect(box.x * scale, box.y * scale, box.w * scale, box.h * scale);
                ctx.setLineDash([]);
            }
        }
    }

    /** Small cells wrapper so _drawOverlay reads linearly. */
    function G_cells(s: SpriteState): SpriteCell[] | null {
        const G = _geometry();
        return G ? G.cellsFromCuts(s.cuts as SpriteCuts, _readControls().labelTrim) : null;
    }

    /** A filled label chip at (x,y) in canvas px. */
    function _tag(ctx: CanvasRenderingContext2D, text: string, x: number, y: number): void {
        if (!text) return;
        const tw = ctx.measureText(text).width;
        ctx.fillStyle = 'rgba(0,0,0,0.7)';
        ctx.fillRect(x, y, tw + 6, 14);
        ctx.fillStyle = '#fff';
        ctx.fillText(text, x + 3, y + 1);
    }

    /** A grab affordance: a filled square plus a tick toward the line it moves. */
    function _drawGrip(ctx: CanvasRenderingContext2D, x: number, y: number,
                       tol: number, scale: number): void {
        const r = Math.max(3, Math.min(5, GRAB_PX / 2));
        ctx.fillStyle = '#e3b341';
        ctx.fillRect(x - r, y - r, r * 2, r * 2);
        ctx.strokeStyle = 'rgba(227,179,65,0.6)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, y - Math.max(6, HANDLE_PX * scale));
        ctx.lineTo(x, y + Math.max(6, HANDLE_PX * scale));
        ctx.stroke();
    }

    // ── tile strip (the second view) ────────────────────────────────

    /**
     * Render the actual crops as thumbnails.
     *
     * This is the check the old dialog made impossible: the overlay shows where
     * the CUT is, the strip shows what comes back from it. An unnamed cell is
     * drawn dimmed and marked "skip", so a grid that covers a banner or a text
     * block is visible as such before anything is uploaded.
     */
    function _drawTiles() {
        const s = _state;
        const wrap = document.getElementById('ss-tiles');
        if (!s || !wrap || !s.img) return;
        const boxes = _mode() === 'boxes';
        const items: { x: number; y: number; w: number; h: number; name: string; skip: boolean }[] = [];
        if (boxes) {
            s.boxes.forEach(b => items.push({ x: b.x, y: b.y, w: b.w, h: b.h,
                name: b.name || '', skip: !b.name }));
        } else {
            const cells = _cells();
            (cells || []).forEach((c, i) => {
                const name = _nameAt(i);
                items.push({ x: c.x, y: c.y, w: c.w, h: c.h, name, skip: !name });
            });
        }
        if (!items.length) {
            wrap.innerHTML = '<div style="font-size:11px;color:var(--text-muted);">No tiles yet.</div>';
            return;
        }

        const THUMB = 68;
        const src = s.src || s.img;
        wrap.innerHTML = '';
        items.forEach((it, i) => {
            const scale = Math.min(THUMB / Math.max(1, it.w), THUMB / Math.max(1, it.h));
            const tw = Math.max(1, Math.round(it.w * scale));
            const th = Math.max(1, Math.round(it.h * scale));
            const cell = document.createElement('div');
            cell.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:3px;';
            const cv = document.createElement('canvas');
            cv.width = tw;
            cv.height = th;
            cv.style.cssText = `width:${tw}px;height:${th}px;border:1px solid ${it.skip ? 'var(--border)' : 'var(--accent)'};border-radius:3px;${it.skip ? 'opacity:0.4;' : ''}`;
            const ctx = cv.getContext('2d');
            if (ctx) ctx.drawImage(src, it.x, it.y, it.w, it.h, 0, 0, tw, th);
            const cap = document.createElement('div');
            cap.textContent = it.name || 'skip';
            cap.title = `${it.name || 'skip'} — ${it.w}×${it.h} at ${it.x},${it.y}`;
            cap.style.cssText = 'font-size:10px;max-width:74px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:' + (it.skip ? 'var(--text-muted)' : 'var(--text)');
            const n = document.createElement('div');
            n.textContent = `#${i + 1}`;
            n.style.cssText = 'font-size:9px;color:var(--text-dim);';
            cell.appendChild(cv);
            cell.appendChild(cap);
            cell.appendChild(n);
            cell.title = cap.title;
            wrap.appendChild(cell);
        });
    }

    /** Rebuild both views. */
    function _render(): void {
        _drawOverlay();
        _drawTiles();
    }

    // ── hit testing ─────────────────────────────────────────────────

    /** What a press at source px (x,y) grabs, or null. */
    function _hit(x: number, y: number): SpriteDrag | null {
        const s = _state;
        const G = _geometry();
        if (!s) return null;
        const tol = GRAB_PX / s.scale;

        if (_mode() === 'boxes') {
            // Grips of ANY box, topmost first — not just the selected one. Requiring a
            // prior selection (by clicking its list row) meant a corner grab silently
            // did nothing and, because the press then fell through to the
            // contains-the-point test, usually moved the box instead of resizing it.
            // Selection now only controls which box *shows* its grips.
            for (let i = s.boxes.length - 1; i >= 0; i--) {
                const b = s.boxes[i];
                const handles = _boxHandles(b);
                for (const key of Object.keys(handles)) {
                    const h = handles[key];
                    if (Math.abs(x - h.x) <= tol && Math.abs(y - h.y) <= tol) {
                        return { kind: key as SpriteGrabKind, index: i,
                                 startX: x, startY: y, orig: { ...b } };
                    }
                }
            }
            // Topmost first, so a later box inside an earlier one is reachable.
            for (let i = s.boxes.length - 1; i >= 0; i--) {
                const b = s.boxes[i];
                if (x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) {
                    return { kind: 'box-move', index: i, startX: x, startY: y, orig: { ...b } };
                }
            }
            return null;
        }

        if (!s.cuts || !G) return null;
        // A press NEAR the frame boundary is a frame grip; a press away from it is a
        // divider. Fixed grip positions cannot solve this — an even grid puts a
        // divider exactly where a handle would sensibly sit, and dividers were
        // being hit-tested first, which made the north/south frame edges
        // unreachable whenever a column divider crossed them.
        const onFrameEdge = Math.abs(x - s.cuts.x0) <= tol || Math.abs(x - s.cuts.x1) <= tol
            || Math.abs(y - s.cuts.y0) <= tol || Math.abs(y - s.cuts.y1) <= tol;
        const frameAt = () => {
            for (const key of Object.keys(_frameHandles(s.cuts as SpriteCuts))) {
                const h = _frameHandles(s.cuts as SpriteCuts)[key];
                if (Math.abs(x - h.x) <= tol && Math.abs(y - h.y) <= tol) {
                    return { kind: key as SpriteGrabKind, index: s.selected,
                             startX: x, startY: y, orig: { ...(s.cuts as SpriteCuts) } };
                }
            }
            return null;
        };
        if (onFrameEdge) {
            const grip = frameAt();
            if (grip) return grip;
        }
        const colIndex = G.hitDivider(s.cuts, 'x', x, tol);
        if (colIndex >= 0) {
            return { kind: 'col', index: colIndex, startX: x, startY: y, orig: { ...s.cuts } };
        }
        const rowIndex = G.hitDivider(s.cuts, 'y', y, tol);
        if (rowIndex >= 0) {
            return { kind: 'row', index: rowIndex, startX: x, startY: y, orig: { ...s.cuts } };
        }
        return frameAt();
    }

    /** Apply a drag to the geometry/boxes. `dx`/`dy` are pointer deltas, source px. */
    function _applyDrag(x: number, y: number): void {
        const s = _state;
        const G = _geometry();
        const drag = s && s.drag;
        if (!s || !drag || !G) return;
        const dx = x - drag.startX;
        const dy = y - drag.startY;
        const kind = drag.kind;

        if (kind === 'box-move') {
            const i = drag.index as number;
            const img = s.img;
            const b = s.boxes[i];
            if (!b || !img) return;
            b.x = Math.round(Math.min(Math.max(0, (drag.orig as SpriteBox).x + dx), img.naturalWidth - b.w));
            b.y = Math.round(Math.min(Math.max(0, (drag.orig as SpriteBox).y + dy), img.naturalHeight - b.h));
            _renderBoxList();
            _drawOverlay();
            return;
        }
        if (kind.startsWith('box-')) {
            const i = drag.index as number;
            const o = drag.orig as SpriteBox;
            const b = s.boxes[i];
            if (!b) return;
            let x0 = o.x;
            let y0 = o.y;
            let x1 = o.x + o.w;
            let y1 = o.y + o.h;
            if (kind.includes('w')) x0 = o.x + dx;
            if (kind.includes('e')) x1 = o.x + o.w + dx;
            if (kind.includes('n')) y0 = o.y + dy;
            if (kind.includes('s')) y1 = o.y + o.h + dy;
            const fixed = clampBox(x0, y0, x1, y1, s.img ? s.img.naturalWidth : 0,
                s.img ? s.img.naturalHeight : 0, MIN_BOX_PX);
            if (fixed) { b.x = fixed.x; b.y = fixed.y; b.w = fixed.w; b.h = fixed.h; }
            _renderBoxList();
            _drawOverlay();
            return;
        }

        const o = drag.orig as SpriteCuts;
        let next: SpriteCuts = { x0: o.x0, y0: o.y0, x1: o.x1, y1: o.y1,
                                 colCuts: o.colCuts.slice(), rowCuts: o.rowCuts.slice() };
        if (kind === 'col') {
            next = G.moveDivider(next, 'x', drag.index as number, o.colCuts[drag.index as number] + dx);
        } else if (kind === 'row') {
            next = G.moveDivider(next, 'y', drag.index as number, o.rowCuts[drag.index as number] + dy);
        } else {
            // Frame grips: only the axes the grip owns move.
            if (kind.includes('w')) next.x0 = o.x0 + dx;
            if (kind.includes('e')) next.x1 = o.x1 + dx;
            if (kind.includes('n')) next.y0 = o.y0 + dy;
            if (kind.includes('s')) next.y1 = o.y1 + dy;
            next = G.clampCuts(next, s.img ? s.img.naturalWidth : 0,
                s.img ? s.img.naturalHeight : 0, {});
            if (next.x0 !== o.x0 || next.y0 !== o.y0 || next.x1 !== o.x1 || next.y1 !== o.y1) {
                // The frame grew or shrank; re-space the interior dividers over the
                // new frame so they keep their relative positions instead of
                // piling up against one edge.
                next = G.recountCuts(next, next.rowCuts.length + 1, next.colCuts.length + 1, {});
            }
        }
        s.cuts = next;
        _syncRowColInputs();
        // The overlay tracks the drag live; the strip is rebuilt on release,
        // because re-cropping every tile on each mousemove is the one thing here
        // that is genuinely expensive.
        _drawOverlay();
    }

    /** Keep the numeric rows/cols inputs honest about the divider counts. */
    function _syncRowColInputs(): void {
        const s = _state;
        if (!s || !s.cuts) return;
        const rowsEl = document.getElementById('ss-rows') as HTMLInputElement | null;
        const colsEl = document.getElementById('ss-cols') as HTMLInputElement | null;
        if (rowsEl) rowsEl.value = String(s.cuts.rowCuts.length + 1);
        if (colsEl) colsEl.value = String(s.cuts.colCuts.length + 1);
    }

    /**
     * Track the drag on the document, not the canvas.
     *
     * A canvas-only `mousemove` stops at the edge, which is exactly the case that
     * matters here: growing a frame or pulling a divider out is a drag that
     * travels past the image. The listener lives on `document` and is removed on
     * release or close, so a closed dialog cannot keep the page alive.
     */
    function _watchDrag(): void {
        const s = _state;
        if (!s) return;
        if (s.releaseDrag) s.releaseDrag();
        const onMove = (ev: MouseEvent): void => {
            if (!_state || !_state.drag) return;
            if (ev.cancelable) ev.preventDefault();
            const p = _toSource(ev);
            _applyDrag(p.x, p.y);
        };
        const onUp = (): void => {
            if (!_state) return;
            const had = !!_state.drag;
            _state.drag = null;
            if (s.releaseDrag) s.releaseDrag();
            if (had) _render();
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        s.releaseDrag = function () {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }

    // ── box list ────────────────────────────────────────────────────

    function _renderBoxList(): void {
        const s = _state;
        if (!s) return;
        const list = document.getElementById('ss-box-list');
        if (!list) return;
        if (!s.boxes.length) {
            list.innerHTML = '<div style="font-size:11px;color:var(--text-muted);">No boxes yet — drag on the image to box each panel. Click a box to move or resize it.</div>';
            return;
        }
        list.innerHTML = s.boxes.map((b, i) => `
            <div class="ss-box-row" data-i="${i}" style="display:flex;align-items:center;gap:6px;margin-bottom:3px;padding:2px 4px;border-radius:3px;${i === s.selected ? 'background:var(--bg-inset);' : ''}">
                <span style="font-size:10px;color:var(--text-muted);width:34px;">#${i + 1}</span>
                <input type="text" class="ss-box-name" data-i="${i}" value="${_escAttr(b.name)}" style="flex:1;font-size:11px;">
                <span style="font-size:10px;color:var(--text-muted);">${b.w}×${b.h}</span>
                <button class="btn btn-sm btn-danger" data-remove="${i}" title="Remove box">🗑</button>
            </div>`).join('');
        list.querySelectorAll('.ss-box-row').forEach(el => {
            el.addEventListener('mousedown', (ev) => {
                const t = ev.target as HTMLElement;
                if (t.tagName === 'INPUT' || t.tagName === 'BUTTON') return;
                s.selected = parseInt((el as HTMLElement).dataset.i as string, 10);
                _renderBoxList();
                _drawOverlay();
            });
        });
        list.querySelectorAll('.ss-box-name').forEach(el => {
            el.addEventListener('input', () => {
                const i = parseInt((el as HTMLElement).dataset.i as string, 10);
                if (s.boxes[i]) s.boxes[i].name = slug((el as HTMLInputElement).value);
                _drawTiles();
            });
        });
        list.querySelectorAll('[data-remove]').forEach(el => {
            el.addEventListener('click', () => {
                const i = parseInt((el as HTMLElement).dataset.remove as string, 10);
                s.boxes.splice(i, 1);
                if (s.selected >= s.boxes.length) s.selected = s.boxes.length - 1;
                _renderBoxList();
                _render();
            });
        });
    }

    /**
     * Track a brand-new box on the document and commit it on release.
     *
     * The canvas alone is not enough: the commit has to happen wherever the
     * pointer is let go, and the drag has to keep updating once it leaves the
     * image — the same reasoning as `_watchDrag`.
     */
    function _watchDraft(): void {
        const s = _state;
        if (!s) return;
        if (s.releaseDrag) s.releaseDrag();
        const onMove = (ev: MouseEvent): void => {
            if (!_state || !_state.draft) return;
            if (ev.cancelable) ev.preventDefault();
            const p = _toSource(ev);
            _state.draft.x1 = p.x;
            _state.draft.y1 = p.y;
            _drawOverlay();
        };
        const onUp = (): void => {
            const st = _state;
            if (st && st.releaseDrag) st.releaseDrag();
            if (!st || !st.draft) return;
            const d = st.draft;
            st.draft = null;
            const img = st.img;
            const box = img
                ? clampBox(d.x0, d.y0, d.x1, d.y1, img.naturalWidth, img.naturalHeight)
                : null;
            if (box) {
                box.name = defaultNameFor(st.boxes.length);
                st.boxes.push(box);
                st.selected = st.boxes.length - 1;
                _renderBoxList();
            }
            _render();
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        s.releaseDrag = function () {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }

    function _escAttr(v: unknown): string {
        return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
            .replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function _setStatus(text: unknown, isError?: boolean): void {
        const el = document.getElementById('ss-status');
        if (el) {
            el.textContent = (text as string) || '';
            el.style.color = isError ? 'var(--red, #e06c75)' : 'var(--text-muted)';
        }
    }

    function _syncModeUi(): void {
        const boxes = _mode() === 'boxes';
        const grid = document.getElementById('ss-grid-controls');
        const namesWrap = document.getElementById('ss-names-wrap');
        const boxWrap = document.getElementById('ss-box-wrap');
        const tilesWrap = document.getElementById('ss-tiles-wrap');
        const hint = document.getElementById('ss-mode-hint');
        if (grid) grid.style.display = boxes ? 'none' : 'flex';
        if (namesWrap) namesWrap.style.display = boxes ? 'none' : 'block';
        if (boxWrap) boxWrap.style.display = boxes ? 'block' : 'none';
        // The crop strip is the point of the second view, and it applies to both
        // modes — boxes are crops too — so it is never hidden.
        if (tilesWrap) tilesWrap.style.display = 'block';
        if (hint) {
            hint.textContent = boxes
                ? 'Drag a rectangle over each panel. Click a box to move or resize it; drag its corner to change size.'
                : 'Drag the yellow frame onto the art, and drag any white line to make rows or columns uneven. The dashed red line is where the caption banner is trimmed.';
        }
        _renderBoxList();
        _render();
    }

    /** Default the name list to the canonical order (grid mode). */
    function _resetNames(): void {
        const s = _state;
        const { rows, cols } = _readControls();
        if (!s) return;
        _resizeNames(rows * cols);
    }

    /**
     * Propose a grid from the sheet's whitespace.
     *
     * Detection is a starting point, not a verdict: it trims a uniform outer
     * margin and turns blank runs into dividers, so a title banner gets its own
     * band and a wide panel separates from the narrow ones beside it. Every value
     * it sets is draggable afterwards, and a sheet with no clean whitespace falls
     * back to the current rows×cols rather than proposing nothing.
     */
    function _autoFit(): void {
        const s = _state;
        const G = _geometry();
        if (!s || !s.img || !G) return;
        const started = Date.now();
        const profiles = G.profileRects(s.img);
        const { rows, cols } = _readControls();
        const detected = (profiles.rows.length && profiles.cols.length)
            ? G.cutsFromProfiles(profiles.rows, profiles.cols,
                s.img.naturalWidth, s.img.naturalHeight, { minRun: 8, blankRatio: 0.01 })
            : null;
        // A sheet with no clean whitespace yields no dividers; that is not a
        // failure, it just means the even grid is the better starting point.
        const usable = detected && (detected.colCuts.length || detected.rowCuts.length)
            ? detected : null;
        const cuts: SpriteCuts = usable
            ? usable
            : G.cutsFromGrid(s.img.naturalWidth, s.img.naturalHeight, rows, cols);
        _setStatus(usable
            ? `Auto-fit: ${cuts.colCuts.length + 1} columns × ${cuts.rowCuts.length + 1} rows `
              + `from whitespace in ${Date.now() - started}ms. Drag anything to adjust.`
            : 'No clean gutters found — kept the even grid. Drag the frame and lines to fit the art.');
        s.cuts = cuts;
        _syncRowColInputs();
        _resizeNames((cuts.rowCuts.length + 1) * (cuts.colCuts.length + 1));
        _render();
    }

    /** Apply the numeric rows/cols as a divider count, keeping the frame. */
    function _applyRowCols(): void {
        const s = _state;
        const G = _geometry();
        if (!s || !s.img || !G) return;
        const { rows, cols } = _readControls();
        s.cuts = G.recountCuts(s.cuts || G.cutsFromGrid(s.img.naturalWidth, s.img.naturalHeight, rows, cols),
            rows, cols, {});
        _syncRowColInputs();
        _resizeNames(rows * cols);
        _render();
    }

    function _setZoom(zoom: 'fit' | 1): void {
        const s = _state;
        if (!s) return;
        s.zoom = zoom;
        const fitBtn = document.getElementById('ss-zoom-fit');
        const oneBtn = document.getElementById('ss-zoom-1');
        if (fitBtn) fitBtn.classList.toggle('btn-blue', zoom === 'fit');
        if (oneBtn) oneBtn.classList.toggle('btn-blue', zoom === 1);
        _drawOverlay();
    }

    // ── dialog ──────────────────────────────────────────────────────

    /** Attach the pointer handlers for both modes. */
    function _wireCanvasDrag(): void {
        const canvas = document.getElementById('ss-preview') as HTMLCanvasElement | null;
        if (!canvas) return;
        canvas.addEventListener('mousedown', (ev) => {
            const s = _state;
            if (!s) return;
            if (ev.preventDefault) ev.preventDefault();
            const p = _toSource(ev);

            if (_mode() === 'boxes') {
                const hit = _hit(p.x, p.y);
                if (hit) {
                    s.drag = hit;
                    _watchDrag();
                    return;
                }
                // Empty space starts a new box; the commit happens on document mouseup.
                s.draft = { x0: p.x, y0: p.y, x1: p.x, y1: p.y };
                _watchDraft();
                _drawOverlay();
                return;
            }

            const hit = _hit(p.x, p.y);
            if (hit) { s.drag = hit; _watchDrag(); return; }

            // Dragging inside a cell adds a divider there, so a mixed-size split
            // is one gesture instead of a trip to the numeric inputs.
            const cells = _cells();
            const G = _geometry();
            const cuts = s.cuts;
            if (cells && G && cuts) {
                const cell = cells.find(c => p.x >= c.x && p.x <= c.x + c.w
                    && p.y >= c.y && p.y <= c.y + c.h);
                if (cell) {
                    let next = G.addDivider(cuts, 'x', p.x);
                    if (s.scale > 0.02) next = G.addDivider(next, 'y', p.y);
                    s.cuts = next;
                    _syncRowColInputs();
                    _resizeNames((next.rowCuts.length + 1) * (next.colCuts.length + 1));
                    _render();
                }
            }
        });

        canvas.addEventListener('dblclick', (ev) => {
            const s = _state;
            const G = _geometry();
            if (!s || !G || _mode() !== 'grid' || !s.cuts) return;
            const p = _toSource(ev);
            const tol = GRAB_PX / s.scale;
            const base = s.cuts;
            const colIndex = G.hitDivider(base, 'x', p.x, tol);
            const rowIndex = G.hitDivider(base, 'y', p.y, tol);
            if (colIndex < 0 && rowIndex < 0) return;
            let next = base;
            if (colIndex >= 0) next = G.removeDivider(next, 'x', colIndex);
            if (rowIndex >= 0) next = G.removeDivider(next, 'y', rowIndex);
            s.cuts = next;
            _syncRowColInputs();
            _resizeNames((next.rowCuts.length + 1) * (next.colCuts.length + 1));
            _render();
        });

        canvas.addEventListener('mousemove', (ev) => {
            const s = _state;
            if (!s) return;
            if (s.draft) {
                const p = _toSource(ev);
                s.draft.x1 = p.x;
                s.draft.y1 = p.y;
                _drawOverlay();
                return;
            }
            if (s.drag) return;
            // Cursor feedback: a resize/crosshair over grabbable geometry.
            const p = _toSource(ev);
            const hit = _hit(p.x, p.y);
            const cursor = !hit ? 'crosshair'
                : (hit.kind === 'col' ? 'ew-resize' : hit.kind === 'row' ? 'ns-resize'
                    : hit.kind === 'box-move' ? 'move' : (hit.kind.includes('e') || hit.kind.includes('w')
                        ? 'ew-resize' : (hit.kind.includes('n') || hit.kind.includes('s') ? 'ns-resize' : 'move')));
            if (canvas.style.cursor !== cursor) canvas.style.cursor = cursor;
        });
    }

    function openDialog(nodeId: string, kind: string): void {
        if (_modalRoot()) closeDialog();

        const startKind = kind === 'full' ? 'full' : 'profile';
        const root = document.createElement('div');
        root.id = 'sprite-sheet-modal';
        root.className = 'modal';
        root.innerHTML = `
            <div class="modal-content" style="width:min(1180px,96vw);">
                <div class="modal-header">
                    <h3>✂️ Split sprite sheet</h3>
                    <button class="modal-close" id="ss-close">&times;</button>
                </div>
                <div style="padding:14px 20px;">
                    <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">
                        Pick one sheet; each tile/box is uploaded to its own expression slot.
                    </div>
                    <input type="file" id="ss-file" accept="image/*" style="font-size:11px;margin-bottom:10px;">
                    <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;margin-bottom:8px;">
                        <label style="font-size:11px;">Mode<br>
                            <span>
                                <label style="font-size:11px;"><input type="radio" name="ss-mode" value="grid" checked> Grid</label>
                                <label style="font-size:11px;margin-left:6px;"><input type="radio" name="ss-mode" value="boxes"> Draw boxes</label>
                            </span>
                        </label>
                        <label style="font-size:11px;">Slot<br>
                            <span>
                                <label style="font-size:11px;"><input type="radio" name="ss-kind" value="profile" ${startKind === 'profile' ? 'checked' : ''}> Profile</label>
                                <label style="font-size:11px;margin-left:6px;"><input type="radio" name="ss-kind" value="full" ${startKind === 'full' ? 'checked' : ''}> Full body</label>
                            </span>
                        </label>
                        <span style="font-size:11px;">Zoom<br>
                            <span>
                                <button class="btn btn-sm btn-blue" id="ss-zoom-fit" type="button" title="Scale the sheet to fit the pane">Fit</button>
                                <button class="btn btn-sm" id="ss-zoom-1" type="button" title="One image pixel per screen pixel — scroll to reach the whole sheet">100%</button>
                            </span>
                        </span>
                    </div>
                    <div id="ss-grid-controls" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-bottom:8px;">
                        <label style="font-size:11px;">Columns<br><input type="number" id="ss-cols" value="4" min="1" max="20" style="width:60px;"></label>
                        <label style="font-size:11px;">Rows<br><input type="number" id="ss-rows" value="3" min="1" max="20" style="width:60px;"></label>
                        <label style="font-size:11px;">Trim label %<br><input type="number" id="ss-label-trim" value="10" min="0" max="90" step="1" style="width:70px;"></label>
                        <button class="btn btn-sm" id="ss-reset-names" type="button" title="Refill the names with the canonical expression order">Reset names</button>
                        <button class="btn btn-sm btn-blue" id="ss-autofit" type="button" title="Propose a grid from the sheet's whitespace gutters">✨ Auto-fit</button>
                    </div>
                    <div id="ss-mode-hint" style="font-size:11px;color:var(--text-muted);margin-bottom:6px;"></div>
                    <div id="ss-names-wrap" style="margin-bottom:6px;">
                        <label style="font-size:11px;">Names (comma or newline, one per tile — blank = skip)<br>
                            <textarea id="ss-names" rows="2" style="width:100%;font-size:11px;"></textarea>
                        </label>
                    </div>
                    <div id="ss-box-wrap" style="display:none;margin-bottom:6px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                            <span style="font-size:11px;">Boxes</span>
                            <button class="btn btn-sm btn-secondary" id="ss-clear-boxes" type="button">Clear all</button>
                        </div>
                        <div id="ss-box-list" style="max-height:130px;overflow-y:auto;"></div>
                    </div>
                    <div style="display:flex;gap:10px;align-items:flex-start;margin-top:6px;">
                        <div id="ss-preview-wrap" style="flex:1 1 auto;min-width:0;height:520px;overflow:auto;border:1px solid var(--border);border-radius:6px;background:var(--bg-inset);">
                            <canvas id="ss-preview" style="display:block;cursor:crosshair;"></canvas>
                        </div>
                        <div id="ss-tiles-wrap" style="flex:0 0 300px;display:none;">
                            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">Crops that will be uploaded</div>
                            <div id="ss-tiles" style="display:flex;flex-wrap:wrap;gap:8px;align-content:flex-start;max-height:500px;overflow-y:auto;"></div>
                        </div>
                    </div>
                    <div id="ss-status" style="font-size:11px;min-height:16px;margin-top:8px;color:var(--text-muted);"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="ss-cancel" type="button">Cancel</button>
                    <button class="btn btn-green" id="ss-run" type="button" disabled>✂️ Slice &amp; upload</button>
                </div>
            </div>`;
        document.body.appendChild(root);

        _state = { nodeId, kind: startKind, img: null, file: null, boxes: [], draft: null,
                   scale: 1, cuts: null, src: null, drag: null, selected: -1,
                   zoom: 'fit', names: [], releaseDrag: null };

        const closeEl = document.getElementById('ss-close') as HTMLButtonElement | null;
        if (closeEl) closeEl.onclick = closeDialog;
        const cancelEl = document.getElementById('ss-cancel') as HTMLButtonElement | null;
        if (cancelEl) cancelEl.onclick = closeDialog;
        root.addEventListener('click', (e) => { if (e.target === root) closeDialog(); });

        const fileEl = document.getElementById('ss-file') as HTMLInputElement | null;
        if (fileEl) {
            fileEl.addEventListener('change', async () => {
                const file = fileEl.files && fileEl.files[0];
                if (!file) return;
                try {
                    const img = await _loadImage(file);
                    if (!_state) return;
                    const G = _geometry();
                    if (!G) { _setStatus('Geometry module failed to load.', true); return; }
                    _state.img = img;
                    _state.file = file;
                    _state.src = _buildSource(img);
                    _state.cuts = G.cutsFromGrid(img.naturalWidth, img.naturalHeight,
                        _readControls().rows, _readControls().cols);
                    _state.boxes = [];
                    _state.selected = -1;
                    const runBtn = document.getElementById('ss-run') as HTMLButtonElement | null;
                    if (runBtn) runBtn.disabled = false;
                    _setStatus(`Loaded ${img.naturalWidth}×${img.naturalHeight}. `
                        + 'Try ✨ Auto-fit, or drag the frame onto the art.');
                    _resizeNames(_readControls().rows * _readControls().cols);
                    _render();
                    _renderBoxList();
                } catch (err) {
                    _setStatus((err as Error).message || 'Could not read image.', true);
                }
            });
        }

        ['ss-cols', 'ss-rows'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', _applyRowCols);
        });
        const trimEl = document.getElementById('ss-label-trim');
        if (trimEl) trimEl.addEventListener('input', _render);
        const namesEl = document.getElementById('ss-names');
        if (namesEl) namesEl.addEventListener('input', () => {
            _readNamesText();
            _render();
        });
        document.querySelectorAll('input[name="ss-kind"]').forEach(el => {
            el.addEventListener('change', () => { if (_state) _state.kind = _readControls().kind; });
        });
        document.querySelectorAll('input[name="ss-mode"]').forEach(el => {
            el.addEventListener('change', _syncModeUi);
        });
        const resetBtn = document.getElementById('ss-reset-names') as HTMLButtonElement | null;
        if (resetBtn) resetBtn.onclick = _resetNames;
        const autofitBtn = document.getElementById('ss-autofit') as HTMLButtonElement | null;
        if (autofitBtn) autofitBtn.onclick = _autoFit;
        const fitBtn = document.getElementById('ss-zoom-fit') as HTMLButtonElement | null;
        if (fitBtn) fitBtn.onclick = () => _setZoom('fit');
        const oneBtn = document.getElementById('ss-zoom-1') as HTMLButtonElement | null;
        if (oneBtn) oneBtn.onclick = () => _setZoom(1);
        const clearBtn = document.getElementById('ss-clear-boxes') as HTMLButtonElement | null;
        if (clearBtn) clearBtn.onclick = () => {
            if (!_state) return;
            _state.boxes = [];
            _state.selected = -1;
            _renderBoxList();
            _render();
        };
        const runBtn = document.getElementById('ss-run') as HTMLButtonElement | null;
        if (runBtn) runBtn.onclick = _runUpload;
        // Re-fit the preview when the pane is resized, so Fit stays honest.
        const wrap = document.getElementById('ss-preview-wrap');
        if (wrap && typeof ResizeObserver !== 'undefined') {
            new ResizeObserver(() => { if (_state && _state.zoom === 'fit') _drawOverlay(); }).observe(wrap);
        }
        window.addEventListener('resize', () => { if (_state && _state.zoom === 'fit') _drawOverlay(); });
        _wireCanvasDrag();
        _syncModeUi();
    }

    /** Crop every named target and upload it to its expression slot. */
    async function _runUpload() {
        if (!_state || !_state.img || !_state.file) return;
        const { kind } = _readControls();
        const targets = _targets();
        if (!targets.length) { _setStatus('No named tiles/boxes to upload.', true); return; }

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
        const runBtn = document.getElementById('ss-run') as HTMLButtonElement | null;
        if (runBtn) runBtn.disabled = true;
        const failures: string[] = [];
        let mergedExpressions: Record<string, unknown> | null = null;
        let neutralUrl: string | null = null;
        const state = _state;
        const src = (state.src || state.img) as CanvasImageSource;
        for (let i = 0; i < targets.length; i++) {
            const t = targets[i];
            _setStatus(`Uploading ${i + 1}/${targets.length} — ${t.name}…`);
            try {
                canvas.width = t.w;
                canvas.height = t.h;
                ctx.clearRect(0, 0, t.w, t.h);
                ctx.drawImage(src, t.x, t.y, t.w, t.h, 0, 0, t.w, t.h);
                const blob = await new Promise<Blob | null>(res => canvas.toBlob(res, 'image/png'));
                if (!blob) throw new Error('canvas produced no image');
                const file = new File([blob], t.name + '.png', { type: 'image/png' });
                const res = await api.uploadNodeImage(state.nodeId, file, kind, t.name);
                if (res && res.error) throw new Error(res.error);
                if (res && res.expressions) mergedExpressions = res.expressions;
                if (t.name === 'neutral' && res && res.image) neutralUrl = res.image;
            } catch (err) {
                failures.push(`${t.name}: ${(err as Error).message || err}`);
            }
        }

        const nodeId = state.nodeId;
        // Merge the batch result into the gallery cache so the thumbnails update
        // without waiting for a full inspector re-render (the server returns the
        // whole `expressions` map on each upload).
        const H = _helpers();
        if (H && mergedExpressions && H._exprCache) {
            const cache = H._exprCache[nodeId] || (H._exprCache[nodeId] = {});
            cache.expressions = mergedExpressions;
            if (neutralUrl) {
                if (kind === 'profile') cache.profile_image = neutralUrl;
                else cache.image = neutralUrl;
            }
        }
        if (failures.length) {
            _setStatus(`Uploaded ${targets.length - failures.length}/${targets.length}. Failed → ${failures.join('; ')}`, true);
            if (runBtn) runBtn.disabled = false;
        } else {
            _setStatus(`Done — uploaded ${targets.length} tile(s).`);
        }
        if (typeof events !== 'undefined' && events) events.log(`Sprite sheet: uploaded ${targets.length - failures.length}/${targets.length} expression tile(s).`, failures.length ? 'error-msg' : 'system-msg');
        // Refresh the gallery once, not per tile.
        if (H && H._refreshExpressionGrid) H._refreshExpressionGrid(nodeId, kind);
        if (typeof graphManager !== 'undefined' && graphManager) { graphManager._lastSig = ''; }
        if (typeof worldState !== 'undefined' && worldState) worldState.fetch();
        if (typeof graphManager !== 'undefined' && graphManager) graphManager.loadGraphData();
        if (!failures.length) closeDialog();
    }

    return { computeCells, clampBox, parseNames, defaultNames, defaultNameFor, slug,
             openDialog, closeDialog, EMOTION_ORDER };
})();

(window as unknown as { SpriteSheet: SpriteSheetApi }).SpriteSheet = _SpriteSheet;