/**
 * editor.js — WorldPainter 3-mode grid editor (task-495).
 *
 * A plain-DOM overlay (no Lit, no ordering constraints) that renders one world
 * scope's authoring grid at its own resolution and lets the author:
 *   - select a scope and drill into its children (recursive scope grids);
 *   - set/resize the grid and pick its mode (world / town / interior);
 *   - paint cells on the biome / road / floor layers;
 *   - place, move, and remove feature (child-scope) placements.
 *
 * Backend: `routes/world_grid_ops.py` (`GET/POST /api/world/scopes/<id>/grid*`).
 * The pure view-model lives in `static/js/worldpainter/grid-model.js`; every
 * mutation POSTs and re-renders from the server response so the editor never
 * holds a divergent copy of the manifest.
 *
 * Overlap follows the documented rule (`engine/world_grid.py`): forbidden by
 * default, with an explicit "displace" confirmation.
 *
 * @module worldpainter/editor — WorldPainter grid editing overlay
 * @contributes the 3-mode scope grid editor UI: paint, feature place/move/remove, area placement, cell inspection, drill-down
 * @powers WorldPainter authored worlds (task-495) feeding the grid-to-graph compiler (task-496)
 * @relates static/js/worldpainter/grid-model.js; routes/world_grid_ops.py; engine/world_grid.py
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(function () {
    'use strict';

    // ───────────────────────────── types ─────────────────────────────
    //
    // Every name here is declared INSIDE the IIFE and prefixed with the file
    // stem on purpose. A top-level `interface`/`type` in a classic script is a
    // GLOBAL binding, so two files declaring the same name is a redeclaration
    // error across the whole corpus — which is what happened the last time this
    // was converted. Function scope cannot collide.
    //
    // Cross-module globals stay ambient in `static/js/types/globals.d.ts`;
    // nothing here redeclares one.

    /** A grid cell in world units. */
    interface WpCell { x: number; y: number }

    /** `{x, y, w, h}` in CELL units: reference rect, painted bounds, crops. */
    interface WpRect { x: number; y: number; w: number; h: number }

    /** A cell the palette can be built from, and a bare section heading. */
    interface WpPaletteEntry {
        /** Tile id. Absent on a heading row. */
        id?: string;
        name?: string;
        tags?: string[];
        descriptions?: string[];
        biomes?: string[];
        entry_phrase?: string;
        surface?: string;
        refusal?: string;
        /** Section this tile files under, or null for ungrouped terrain. */
        group?: string | null;
        /** Set instead of `id` on a heading row. */
        section?: string;
        separator?: boolean;
    }

    /** A palette tile/section as `grid-model.paletteSections` returns them. */
    interface WpPaletteTile { id: string; name: string; kind: string; rec: WpPaletteEntry }
    interface WpPaletteSection { id: string; label: string; tiles: WpPaletteTile[] }

    /** The backend vocabulary document (`/api/world/painter/vocabulary`). */
    interface WpVocab {
        biomes?: WpPaletteEntry[];
        features?: WpPaletteEntry[];
        /** Short aliases the vocabulary endpoint also answers with. */
        b?: WpPaletteEntry[];
        f?: WpPaletteEntry[];
        layers?: unknown[];
        modes?: unknown[];
        metres_per_storey?: number;
    }

    /** One preflight finding from `engine/world_compile.preflight`. */
    interface WpBlocker {
        code?: string;
        severity: string;
        text?: string;
        remedy?: string;
    }

    /**
     * A scope as the chooser and the child list see it. The flat endpoint sends
     * snake_case counts, the nested one camelCase — both are accepted (task-615).
     */
    interface WpScopeCard {
        id: string;
        name?: string;
        depth?: number;
        kind?: string;
        state?: string;
        mode?: string;
        placed?: boolean;
        area_count?: number | null;
        item_count?: number | null;
        areaCount?: number | null;
        itemCount?: number | null;
    }

    /** A breadcrumb entry. */
    interface WpScopeRef { id: string; name?: string }

    /** A child-scope placement, or an area placement, or an unplaced area. */
    interface WpPlacement { id: string; name?: string; x: number; y: number }

    /** The reference image record on the scope. */
    interface WpReference {
        image?: string | null;
        opacity?: number | null;
        visible?: boolean;
        rect?: WpRect;
        crop?: Partial<WpRect>;
    }

    /** The patch `updateReference` sends. */
    interface WpReferencePatch {
        image?: string | null;
        opacity?: number | null;
        visible?: boolean;
        reset?: boolean;
        rect?: WpRect;
        crop?: Partial<WpRect>;
    }

    /** A boundary way Generate minted around a placed area (task-528). */
    interface WpBoundaryWay {
        way_id: string;
        area_id?: string;
        to_name?: string;
        to_id?: string;
        direction?: string;
        overridden?: boolean;
    }

    /** A seam the author has taken over, or removed. */
    interface WpBoundaryOverride {
        way_id: string;
        action?: string;
        hand_way_id?: string;
    }

    /** One scope's grid manifest: `GET /api/world/scopes/<id>/grid`. */
    interface WpPayload {
        scope: {
            id: string;
            name?: string;
            has_grid?: boolean;
            mode?: string;
            state?: string;
            sibling_traversal?: boolean;
            sibling_traversal_effective?: boolean;
        };
        sibling_traversal?: boolean;
        sibling_traversal_effective?: boolean;
        grid?: { w: number; h: number };
        mode?: string;
        layers?: Record<string, Record<string, string>>;
        names?: Record<string, unknown>;
        children?: WpScopeCard[];
        blockers?: WpBlocker[];
        reference?: WpReference;
        placements?: WpPlacement[];
        area_placements?: WpPlacement[];
        unplaced_areas?: WpPlacement[];
        map_offset?: { x: number; y: number };
        boundary_ways?: WpBoundaryWay[];
        boundary_overrides?: WpBoundaryOverride[];
        breadcrumb?: WpScopeRef[];
        report?: { node_count?: number; edge_count?: number; notes?: string[] };
        deleted_nodes?: number;
        b?: WpPaletteEntry[];
        f?: WpPaletteEntry[];
        biomes?: WpPaletteEntry[];
        features?: WpPaletteEntry[];
    }

    /** One row of the per-mode checklist. */
    interface WpChecklistStep {
        title: string;
        how: string;
        done: boolean;
        note?: string;
        tool?: string;
        layer?: string;
        value?: string;
        action?: () => void;
    }

    /** What `GM().cellInfo()` returns, as far as this file reads it. */
    interface WpCellInfo {
        key?: string;
        x: number;
        y: number;
        empty?: boolean;
        name?: string;
        biome?: unknown;
        road?: unknown;
        floor?: unknown;
        kind?: string;
        enter?: string;
        area?: { id: string; name?: string } | null;
        child?: { id: string; name?: string } | null;
        painted?: boolean;
    }

    /** In-progress reference-image drag (move / resize / crop). */
    interface WpRefDrag {
        kind: string;
        key: string | null;
        start: WpCell;
        rect: WpRect;
        crop: Partial<WpRect>;
    }

    /** In-progress grid-frame drag (task-597): move the scope, resize the frame, or resize a cell corner. */
    interface WpGridDrag {
        kind: string;
        key: string | null;
        start: WpCell;
        /** Pointer position in screen px at mousedown, so the drag is a *delta*
         *  from where it began rather than an absolute hit on the canvas. */
        clientX: number;
        clientY: number;
        w: number;
        h: number;
        offset: WpCell;
        anchorScreen?: { x: number; y: number; w: number; h: number } | null;
        pxPerCell?: number | null;
    }

    /** The marquee being dragged, task-536. */
    interface WpMarquee { anchor: WpCell; to: WpCell; add?: boolean }

    /**
     * The palette stamps `__src` on the `<img>` it makes, so a re-render can tell
     * whether it already points at the payload's reference URL without touching
     * `src` (which would restart the load).
     */
    type WpTrackedImage = HTMLImageElement & { __src?: string };

    /**
     * Konva 9, the UMD bundle templates/index.html pulls from unpkg. Only the
     * surface this file calls is declared; Konva ships no types and it is not
     * worth vendoring them for. The `sceneFunc` context is a real
     * CanvasRenderingContext2D at draw time, which is what every `ctx.*` below
     * assumes.
     */
    interface WpKonvaEvent {
        evt: {
            button: number;
            shiftKey: boolean;
            altKey?: boolean;
            deltaY: number;
            preventDefault(): void;
        };
    }

    interface WpKonvaNode {
        x(): number;
        x(value: number): unknown;
        y(): number;
        y(value: number): unknown;
        width(): number;
        width(value: number): unknown;
        height(): number;
        height(value: number): unknown;
        crop(value: { x: number; y: number; width: number; height: number }): unknown;
        image(value: unknown): unknown;
        add(...nodes: unknown[]): unknown;
        batchDraw(): void;
        destroyChildren(): void;
        remove(): void;
    }

    interface WpKonvaStage extends WpKonvaNode {
        scale(v: { x: number; y: number }): unknown;
        scaleX(): number;
        position(v?: { x: number; y: number }): { x: number; y: number };
        draggable(v?: boolean): boolean;
        on(events: string, handler: (e: WpKonvaEvent) => void): void;
        getRelativePointerPosition(): WpCell | null;
        getPointerPosition(): WpCell;
    }

    interface WpKonvaFactory {
        Stage: new (cfg: unknown) => WpKonvaStage;
        Layer: new (cfg?: unknown) => WpKonvaNode;
        Shape: new (cfg: {
            listening?: boolean;
            sceneFunc: (ctx: CanvasRenderingContext2D) => void;
        }) => WpKonvaNode;
        Rect: new (cfg: unknown) => WpKonvaNode;
        Image: new (cfg: unknown) => WpKonvaNode;
    }

    /** The five Konva layers the painter keeps. */
    interface WpKonvaLayers {
        ref: WpKonvaNode;
        bg: WpKonvaNode;
        paint: WpKonvaNode;
        decor: WpKonvaNode;
        select: WpKonvaNode;
    }

    /** One paint-batch edit, as `grid/paint_batch` wants it. */
    interface WpEdit { layer: string; x: number; y: number; value: string | null }

    /** The painter's whole mutable state. Declared, not inferred: the inferred
     *  type gave every field `null`, which is how `state.overlay.remove()` and
     *  forty other reads became `never`. */
    interface WpState {
        scopeId: string | null;
        payload: WpPayload | null;
        tool: string;
        layer: string;
        value: string;
        /** Whether the palette panel is open (task-759); survives a render. */
        paletteOpen: boolean;
        /** Active palette rail section id, and the search box text (task-759). */
        paletteCategory: string | null;
        paletteQuery: string;
        brush: number;
        brushHover: WpCell[] | null;
        paintAlpha: number;
        stroke: WpCell[];
        stroking: boolean;
        strokeLayer: string | null;
        strokeValue: string | null;
        strokeKeys: Record<string, boolean>;
        spaceDown: boolean;
        vocab: WpVocab | null;
        backgrounds: string[] | null;
        refImage: WpTrackedImage | null;
        refNode: WpKonvaNode | null;
        refEdit: boolean;
        refDrag: WpRefDrag | null;
        gridEdit: boolean;
        gridDrag: WpGridDrag | null;
        /** Detaches the document-level grid-drag listeners, if *FIX* are attached. */
        gridDragRelease: (() => void) | null;
        /**
         * A cell-size candidate being previewed by dragging the cell (0,0) corner
         * handle (task-597): the grid it would set, drawn on the canvas before
         * *FIX*thing is committed. Null unless a cell-size drag is in progress.
         */
        cellSizePreview: { w: number; h: number; pxPerCell: number } | null;
        /** The HUD's size readout, relabelled once the reference size is known. */
        dimsBtn: HTMLButtonElement | null;
        selectedChild: string | null;
        selectedArea: string | null;
        /** Keyed by scope id: a selection is *this map's* selection. */
        selection: Record<string, Record<string, boolean>>;
        marquee: WpMarquee | null;
        nudged: WpCell | null;
        inspected: WpCell | null;
        cellInfoEl: HTMLElement | null;
        cellInfoKey: string | null;
        /** Rebuilt by every render; `scrollTop` is carried across so a refresh
         *  mid-task does not throw the author back to the top of the panel. */
        scrollBox: HTMLElement | null;
        scrollTop: number;
        /** True once the pending position has actually been written to the box. */
        scrollRestored: boolean;
        merge: boolean;
        /** `{scale}` - Konva owns the live transform. */
        view: { x?: number; y?: number; scale: number } | null;
        route: WpCell[];
        stage: WpKonvaStage | null;
        paintCache: HTMLCanvasElement | null;
        paintCacheValid: boolean;
        recents: Array<{ layer: string; value: string }>;
        resizeObs: ResizeObserver | null;
        shapes: Record<string, WpKonvaNode> | null;
        layers: WpKonvaLayers | null;
        gridHolder: HTMLElement | null;
        routeInfoEl: HTMLElement | null;
        zoomInBtn: HTMLButtonElement | null;
        zoomOutBtn: HTMLButtonElement | null;
        overlay: HTMLElement | null;
        body: HTMLElement | null;
        checklistOpen: boolean;
        checklistTouched: boolean;
        status: string;
        statusError: boolean;
        visionOrigin: { x: number; y: number; floor?: number } | null;
        visionTarget: { x: number; y: number; floor?: number } | null;
        visionFacing: string | null;
        visionRay: { visible: boolean; steps: Array<{ x: number; y: number; z: number; blocked: boolean; obscurity: number; height: number }>; reason?: string } | null;
        visionVisibleSet: Set<string> | null;
        visionLens: boolean;
        _keyDown: ((e: KeyboardEvent) => void) | null;
        _keyUp: ((e: KeyboardEvent) => void) | null;
    }

    /**
     * Konva 9, the UMD bundle templates/index.html pulls from unpkg. It is not in
     * globals.d.ts and the bundle ships no types, so `WpKonvaFactory` declares
     * only the surface this file calls. `sceneFunc` receives a real
     * CanvasRenderingContext2D at draw time, which is what every `ctx.*` below
     * assumes.
     */
    function _konva(): WpKonvaFactory | null {
        return (window as unknown as { Konva?: WpKonvaFactory }).Konva || null;
    }

    /**
     * `catch (e)` is `unknown` under strict. Almost every handler below wants the
     * message and nothing else, and `_req` always rejects with an `Error`, so
     * this is the one narrowing - the non-Error branch keeps the old
     * string-interpolation behaviour rather than swallowing it.
     */
    function errText(e: unknown): string {
        return e instanceof Error ? e.message : String(e);
    }

    const BASE = '/api/world/scopes';
// The bare endpoint answers a tree that inlines ONLY the root and its immediate
// children -- a scope nested two deep (`goblin_camp` > `test`) is absent from it
// entirely, so it cannot be chosen for painting. `?flat=1` returns every scope
// with its `depth` and `parent_id`, which is the complete list.
// `SCOPES_URL` is what *FIX* scope *picker* should use; `BASE` stays for the
// per-scope grid payloads that expect the nested shape.
const SCOPES_URL = '/api/world/scopes?flat=1';
    const CELL = 22;           // base px per cell at scale 1
    // The zoom floor is a *legibility* floor, not an arithmetic one (task-595).
    // `_drawGridLines` stops drawing the lattice below 4px per cell, so at the
    // old 0.12 (< 3px per cell) the grid dissolved into a smear of paint blobs
    // and the author could not tell a road from a field. 0.25 keeps a cell at
    // 5.5px - lines still drawn, a 160-cell world still fits an 880px pane - so
    // zooming out to the floor leaves a readable map rather than a blank one.
    const MIN_SCALE = 0.25;
    const MAX_SCALE = 20;
    // main.js reloads the VW namespace last, so prefer the bare global it keeps.
    const GM = () => window.gridModel || window.VW.gridModel;

    const state: WpState = {
        scopeId: null,
        payload: null,
        tool: 'paint',
        layer: 'biome',
        value: 'sparse_forest',
        brush: 1,
        paletteOpen: false,
        paletteCategory: null,
        paletteQuery: '',
        brushHover: null,
        paintAlpha: 0.75,
        stroke: [],
        stroking: false,
        strokeLayer: null,
        strokeValue: null,
        strokeKeys: {},
        spaceDown: false,
        vocab: null,
        backgrounds: null,
        refImage: null,
        refNode: null,
        refEdit: false,       // adjust mode: move/resize/crop the reference image
        refDrag: null,        // {kind, key, start, rect, crop} during a ref edit
        // Grid adjust mode (task-597): drag the frame to set the scope's map
        // layout offset, or an edge/corner handle to resize the extent, instead
        // of typing numbers into the dialog.
        gridEdit: false,
        gridDrag: null,       // {kind, key, start, w, h, offset} during a grid edit
        gridDragRelease: null,
        // Set while dragging the cell (0,0) corner handle (task-597); the canvas
        // draws the candidate extent and the cells it would strand.
        cellSizePreview: null,
        dimsBtn: null,
        selectedChild: null,
        selectedArea: null,   // area picked by the 📍 Area place tool (task-528)
        // Cell selection and the marquee being dragged (task-536). Keyed by scope
        // id, because a selection is *this map's* selection: switching tools keeps
        // it, switching maps must not smuggle it across.
        selection: {},         // {scopeId: {'x,y': true}}
        marquee: null,         // {anchor: {x, y}, to: {x, y}} while dragging
        nudged: null,          // last move offset, for the status line
        inspected: null,      // {x, y} the cell the inspector panel is showing (task-540)
        cellInfoEl: null,     // HUD hover readout for the cell under the pointer
        cellInfoKey: null,    // last hovered cell+content, to skip pointless DOM writes
        // The current scroll container (rebuilt by every render) and the author's
        // position in it. Without this, each action threw the view back to the top
        // and a long panel had to be re-scrolled every time.
        scrollBox: null,
        scrollTop: 0,
        scrollRestored: false,
        merge: false,
        view: null,            // {scale} - Konva owns the live transform
        route: [],             // waypoints for the route/trail tool
        stage: null,
        paintCache: null,
        paintCacheValid: false,
        recents: [],
        resizeObs: null,
        shapes: null,
        layers: null,
        gridHolder: null,
        routeInfoEl: null,
        zoomInBtn: null,
        zoomOutBtn: null,
        overlay: null,
        body: null,
        // The per-mode checklist's open/closed state. `checklistTouched` records
        // that the author clicked it, which stops it re-deciding for them.
        checklistOpen: true,
        checklistTouched: false,
        status: '',
        statusError: false,
        visionOrigin: null,
        visionTarget: null,
        visionFacing: null,
        visionRay: null,
        visionVisibleSet: null,
        visionLens: false,
        _keyDown: null,
        _keyUp: null,
    };

    // ───────────────────────────── dom/net ─────────────────────────────

    /**
     * Build an element. Generic over the tag so `_el('input', …).value` and
     * `_el('select', …).options` are typed, which is most of what this file does
     * with what it gets back.
     */
    function _el<K extends keyof HTMLElementTagNameMap>(
        tag: K, style?: string | null, text?: string | null,
    ): HTMLElementTagNameMap[K] {
        const el = document.createElement(tag);
        if (style) el.setAttribute('style', style);
        if (text != null) el.textContent = text;
        return el;
    }

    function _btn(label: string, onClick: (ev: MouseEvent) => void, style?: string | null,
        title?: string | null): HTMLButtonElement {
        const b = _el('button', 'cursor:pointer;border:1px solid var(--border,#444);' +
            'background:var(--bg-card,#2a2a32);color:var(--text,#ddd);border-radius:5px;' +
            'padding:3px 8px;font-size:12px;' + (style || ''), label);
        if (title) b.title = title;
        b.addEventListener('click', onClick);
        return b;
    }

    /**
     * Hook a painter control into the HelpCenter (task-521). The launcher button
     * was the only hinted control in this overlay, so every in-editor control —
     * the ones you actually have to understand — was unhelpfully silent.
     */
    function _help<T extends HTMLElement>(el: T | null, key: string): T | null {
        if (el) el.setAttribute('data-help', key);
        return el;
    }

    /**
     * The preflight bar: what blocks this scope from compiling, and what to do.
     *
     * Renders beside ⚙ Generate rather than behind it, because the whole point is
     * that the author finds out *before* pressing it. A block is stated with its
     * remedy inline; a warn is folded behind a count so a map with six naming
     * reminders does not bury the one that matters.
     */
    function _blockerBadge(blockers: WpBlocker[]): HTMLElement {
        const blocks = blockers.filter((b) => b && b.severity === 'block');
        const warns = blockers.filter((b) => b && b.severity !== 'block');
        // A block is what the author must deal with; a warn is only interesting
        // once there is nothing blocking, so the panel shows one set or the other
        // rather than letting six naming reminders bury the one that matters.
        const lead = blocks.length ? blocks : warns;
        const tone = blocks.length ? '#f77' : '#c96';

        const badge = _el('span', 'display:inline-flex;align-items:center;gap:4px;' +
            'font-size:11px;padding:2px 7px;border-radius:10px;cursor:help;' +
            `color:${tone};border:1px solid ${tone}55;background:${tone}12;`);
        _help(badge, 'wp-blockers');

        const detail = _el('div', 'display:none;flex-direction:column;gap:5px;' +
            'flex-basis:100%;width:100%;margin-top:2px;padding:6px 8px;border-radius:6px;' +
            'border:1px solid var(--border,#3a3a44);background:rgba(13,17,23,0.6);');
        for (const b of lead) {
            if (!b) continue;
            const row = _el('div', 'font-size:11px;line-height:1.45;' +
                `color:${b.severity === 'block' ? '#f77' : '#c96'};`);
            row.appendChild(_el('b', null, b.severity === 'block' ? '✖ ' : '⚠ '));
            row.appendChild(document.createTextNode(b.text || ''));
            if (b.remedy) {
                const fix = _el('div', 'color:var(--text-muted,#999);padding-left:12px;');
                fix.textContent = '→ ' + b.remedy;
                row.appendChild(fix);
            }
            detail.appendChild(row);
        }
        if (warns.length > lead.length) {
            const more = _el('div', 'font-size:11px;color:var(--text-muted,#999);');
            more.textContent = `…and ${warns.length - lead.length} more. `
                + 'Hover ⚙ Generate for the full report.';
            detail.appendChild(more);
        }

        const closedLabel = blocks.length
            ? `⚠ ${blocks.length} to fix before Generate`
            : `⚠ ${warns.length} to know`;
        badge.textContent = closedLabel;
        badge.setAttribute('data-role', 'wp-blockers');
        let open = false;
        badge.addEventListener('click', () => {
            open = !open;
            detail.style.display = open ? 'flex' : 'none';
            badge.textContent = open ? '▲ hide' : closedLabel;
        });

        // Its own row under the toolbar, so it needs a wrapping container:
        // appended straight into the toolbar's `div` flow, the badge and the
        // expanded panel would be laid out as toolbar buttons and the panel's
        // full-width text would be squeezed into a flex item.
        const holder = _el('span', 'display:flex;flex-wrap:wrap;align-items:center;gap:8px;' +
            'flex-basis:100%;width:100%;');
        holder.appendChild(badge);
        holder.appendChild(detail);
        return holder;
    }

    /**
     * One POST/GET against the backend.
     *
     * `*FIX*` on the way out on purpose: the answer is whatever JSON the route
     * answered with, and the callers either store it as the next payload or read
     * two or three fields off it. `unknown` would push a cast to every one of
     * them for no gain.
     */
    async function _req(url: string, options?: RequestInit): Promise<*FIX*> {
        const resp = await fetch(url, options);
        let data: *FIX* = null;
        try { data = await resp.json(); } catch (e) { data = null; }
        if (!resp.ok) throw new Error((data && data.error) || `${resp.status} ${resp.statusText}`);
        return data;
    }

    function _log(text: string, cls?: string | null) {
        if (window.events && typeof window.events.log === 'function') {
            window.events.log(text, cls || 'system-msg');
        }
    }

    function _notify(worldChanged: boolean) {
        const win = window as unknown as {
            worldSync?: { refresh(): void };
            VW?: { worldSync?: { refresh(): void } };
            graphManager?: { _lastSig?: string; loadGraphData?: () => void };
        };
        const sync = win.worldSync || win.VW?.worldSync;
        if (worldChanged && sync && typeof sync.refresh === 'function') {
            sync.refresh();
        }
        if (worldChanged && win.graphManager && typeof win.graphManager.loadGraphData === 'function') {
            win.graphManager._lastSig = '';
            win.graphManager.loadGraphData();
        }
    }

    const _post = (path: string, body?: unknown) => _req(BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    });

    /**
     * A POST to a path that is not under `/api/world/scopes`.
     *
     * `/api/world/promote` is the one WorldPainter endpoint that lives outside
     * the scopes prefix, so `_post('/promote', …)` asked for
     * `/api/world/scopes/promote` — which matches the scope *read* route, so the
     * server answered 405 and the painter said "Promote failed". Absolute path
     * or nothing.
     */
    const _post_root = (path: string, body?: unknown) => _req(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    });

    /**
     * What each structure kind is *to movement*, in the author's terms (task-562).
     * The cells here never become places, so the panel has to say what they do
     * instead of reporting "biome: wall" and leaving it at that.
     */
    const STRUCTURE_NOTES: Record<string, string> = {
        solid: 'solid — nothing passes it',
        see_through: 'you can see through it, not walk through it',
        passable: 'a threshold — you go through it',
    };

    // ───────────────────────────── open/close ──────────────────────────

    const _layerOptionsCache = new Map<string, WpPaletteEntry[]>();
    const _paletteSectionsCache = new Map<string, WpPaletteSection[]>();

    function _clearPaletteMemos(): void {
        _layerOptionsCache.clear();
        _paletteSectionsCache.clear();
    }

    async function ensureVocab(): Promise<WpVocab | null> {
        if (state.vocab) return state.vocab;
        try {
            state.vocab = await _req('/api/world/painter/vocabulary', { cache: 'no-store' });
            _clearPaletteMemos();
            // The climates come from the backend, ids and base °C both (task-557);
            // only the colour is local, so a new climate needs no editor change.
            GM().useClimatesFromVocab(state.vocab);
        } catch (e) {
            // The editor still works without it (free-text values), just no dropdown.
            state.vocab = { biomes: [], features: [], layers: GM().PAINT_LAYERS, modes: GM().MODES };
        }
        return state.vocab;
    }

    async function ensureBackgrounds() {
        if (state.backgrounds) return state.backgrounds;
        try {
            state.backgrounds = (await _req('/api/world/painter/backgrounds',
                { cache: 'no-store' })).images || [];
        } catch (e) {
            state.backgrounds = [];
        }
        return state.backgrounds;
    }

    interface WpRecentItem {
        layer: string;
        value: string;
    }

    function _saveScopePrefs(): void {
        if (!state.scopeId || typeof localStorage === 'undefined') return;
        try {
            const prefs = {
                tool: state.tool,
                layer: state.layer,
                value: state.value,
                zoom: state.stage ? state.stage.scaleX() : (state.view ? state.view.scale : undefined),
                paletteOpen: state.paletteOpen,
            };
            localStorage.setItem(`wp_scope_prefs_${state.scopeId}`, JSON.stringify(prefs));
        } catch {}
    }

    function _loadScopePrefs(scopeId: string): void {
        if (!scopeId || typeof localStorage === 'undefined') return;
        try {
            const raw = localStorage.getItem(`wp_scope_prefs_${scopeId}`);
            if (!raw) return;
            const prefs = JSON.parse(raw);
            if (prefs && typeof prefs === 'object') {
                if (typeof prefs.tool === 'string') state.tool = prefs.tool;
                if (typeof prefs.layer === 'string') state.layer = prefs.layer;
                if (typeof prefs.value === 'string') state.value = prefs.value;
                if (typeof prefs.paletteOpen === 'boolean') state.paletteOpen = prefs.paletteOpen;
                if (typeof prefs.zoom === 'number' && prefs.zoom >= MIN_SCALE && prefs.zoom <= MAX_SCALE) {
                    state.view = { scale: prefs.zoom };
                }
            }
        } catch {}
    }

    function _getRecents(): WpRecentItem[] {
        if (typeof localStorage === 'undefined') return [];
        try {
            const raw = localStorage.getItem('wp_recents');
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed.slice(0, 8) : [];
        } catch {
            return [];
        }
    }

    function _pushRecent(layer: string, value: string): void {
        if (!layer || value == null || value === '' || typeof localStorage === 'undefined') return;
        try {
            const recents = _getRecents().filter((r) => !(r.layer === layer && r.value === value));
            recents.unshift({ layer, value });
            const trimmed = recents.slice(0, 8);
            localStorage.setItem('wp_recents', JSON.stringify(trimmed));
        } catch {}
    }

    function _recentsRow(): HTMLElement {
        const wrap = _el('div', 'display:inline-flex;gap:4px;align-items:center;flex-wrap:wrap;');
        wrap.setAttribute('data-role', 'wp-recents');
        const recents = _getRecents();
        if (!recents.length) return wrap;
        const label = _el('span', 'font-size:10px;color:var(--text-muted,#888);margin-right:2px;', 'Recents:');
        wrap.appendChild(label);
        recents.forEach((r) => {
            const chip = _el('button',
                'display:inline-flex;align-items:center;gap:3px;padding:1px 5px;font-size:10px;'
                + 'border-radius:4px;border:1px solid var(--border,#444);background:var(--bg-card,#25252d);'
                + 'color:var(--text,#ccc);cursor:pointer;');
            const swatch = _el('span', 'display:inline-block;width:8px;height:8px;border-radius:2px;');
            swatch.style.background = GM().layerColor(r.layer, r.value) || '#777';
            chip.appendChild(swatch);
            const nameText = r.value.length > 14 ? r.value.slice(0, 13) + '...' : r.value;
            chip.appendChild(_el('span', null, `${r.layer}:${nameText}`));
            chip.title = `Arm ${r.layer}: ${r.value}`;
            chip.addEventListener('click', () => {
                state.tool = 'paint';
                state.layer = r.layer;
                state.value = r.value;
                _saveScopePrefs();
                softRender();
                _status(`Armed recent ${r.layer}: "${r.value}".`, false);
            });
            wrap.appendChild(chip);
        });
        return wrap;
    }

    function _ensurePaintCache(p: WpPayload): void {
        if (!p.grid) return;
        if (typeof document === 'undefined' || typeof document.createElement !== 'function') return;
        if (!state.paintCache || state.paintCache.width !== p.grid.w || state.paintCache.height !== p.grid.h) {
            const c = document.createElement('canvas');
            c.width = p.grid.w;
            c.height = p.grid.h;
            state.paintCache = c;
            state.paintCacheValid = false;
        }
        if (state.paintCacheValid) return;
        const ctx = state.paintCache.getContext('2d');
        if (!ctx) return;
        ctx.clearRect(0, 0, p.grid.w, p.grid.h);
        const layers = p.layers || {};
        const layerOrder = ['biome', 'current', 'road'];
        const otherLayers = Object.keys(layers).filter((l) => layerOrder.indexOf(l) < 0);
        const allLayers = [...layerOrder, ...otherLayers];
        allLayers.forEach((layer) => {
            const cells = layers[layer] || {};
            Object.keys(cells).forEach((key) => {
                const pos = GM().parseCellKey(key);
                if (!pos) return;
                const color = GM().layerColor(layer, cells[key]);
                if (!color) return;
                ctx.fillStyle = color;
                ctx.fillRect(pos.x, pos.y, 1, 1);
            });
        });
        state.paintCacheValid = true;
    }

    function _patchPaintCache(p: WpPayload, cells: Array<{ x: number; y: number }>): void {
        if (!p.grid || !state.paintCache || !state.paintCacheValid) {
            _ensurePaintCache(p);
            return;
        }
        const ctx = state.paintCache.getContext('2d');
        if (!ctx) return;
        const layers = p.layers || {};
        const layerOrder = ['biome', 'current', 'road'];
        const otherLayers = Object.keys(layers).filter((l) => layerOrder.indexOf(l) < 0);
        const allLayers = [...layerOrder, ...otherLayers];
        cells.forEach((cell) => {
            ctx.clearRect(cell.x, cell.y, 1, 1);
            const key = GM().cellKey(cell.x, cell.y);
            allLayers.forEach((layer) => {
                const val = layers[layer] && layers[layer][key];
                if (val !== undefined && val !== null && val !== '') {
                    const color = GM().layerColor(layer, val);
                    if (color) {
                        ctx.fillStyle = color;
                        ctx.fillRect(cell.x, cell.y, 1, 1);
                    }
                }
            });
        });
    }

    function _updateStatusBar(): void {
        const statusBar = (state.body && state.body.querySelector('[data-role="wp-status"]'))
            || (state.overlay && state.overlay.querySelector('[data-role="wp-status"]'));
        if (statusBar) {
            statusBar.textContent = state.status;
            (statusBar as HTMLElement).style.color = state.statusError ? '#e66' : '#9c9';
        }
    }

    function softRender(): void {
        const p = state.payload;
        if (!p || !state.body || !state.gridHolder || !state.stage) {
            render();
            return;
        }
        // 1. Update status bar
        _updateStatusBar();

        // 2. Update estimate
        const estEl = state.overlay && state.overlay.querySelector('[data-role="wp-estimate"]') as HTMLElement | null;
        if (estEl) {
            const est = GM().estimateCompile(p, state.merge);
            estEl.textContent = `≈ ${est.areas} areas · ${est.ways} ways`
                + (est.links ? ` · 🔗 ${est.links} linked` : '');
        }

        // 3. Update value readout and swatch
        const swatch = state.overlay && state.overlay.querySelector('[data-role="wp-value-swatch"]') as HTMLElement | null;
        if (swatch) {
            swatch.style.background = GM().layerColor(state.layer, state.value) || 'transparent';
        }
        const pick = state.overlay && state.overlay.querySelector('[data-role="wp-value"]') as HTMLElement | null;
        if (pick) {
            const sections = _paletteSections(state.layer);
            const tile = GM().paletteTile(sections, state.value) as WpPaletteTile | null;
            pick.textContent = (tile ? tile.name : (state.value || '(no tiles)')) + '  ▾';
        }
        const detail = state.overlay && state.overlay.querySelector('[data-role="wp-value-detail"]') as HTMLElement | null;
        if (detail) {
            const sections = _paletteSections(state.layer);
            const tile = GM().paletteTile(sections, state.value) as WpPaletteTile | null;
            const text = tile ? GM().tileDetail(state.layer, tile.rec) as string : '';
            detail.textContent = text;
            detail.title = text;
        }

        // 4. Update tool rail buttons active state and tool rail options
        const oldRail = state.overlay && state.overlay.querySelector('[data-role="wp-rail"]');
        if (oldRail && oldRail.parentElement) {
            const freshRail = _toolRail(p);
            oldRail.replaceWith(freshRail);
        }

        // 5. Update recents row
        const oldRecents = state.overlay && state.overlay.querySelector('[data-role="wp-recents"]');
        if (oldRecents && oldRecents.parentElement) {
            const freshRecents = _recentsRow();
            oldRecents.replaceWith(freshRecents);
        }

        // 6. Update palette dock in studio row
        const withRail = state.overlay && state.overlay.querySelector('[data-role="wp-studio-row"]') as HTMLElement | null;
        if (withRail) {
            const existingPalette = withRail.querySelector('[data-role="wp-palette"]');
            if (state.paletteOpen && !existingPalette) {
                const pal = _palettePanel();
                if (pal) withRail.appendChild(pal);
            } else if (!state.paletteOpen && existingPalette) {
                existingPalette.remove();
            } else if (state.paletteOpen && existingPalette) {
                const freshPal = _palettePanel();
                if (freshPal) existingPalette.replaceWith(freshPal);
            }
        }

        // 7. Update cell panel (inspector)
        if (state.scrollBox) {
            const existingPanel = state.scrollBox.querySelector('[data-role="wp-cellpanel"]');
            if (state.inspected) {
                const freshPanel = _cellPanel(p);
                if (existingPanel && freshPanel) {
                    existingPanel.replaceWith(freshPanel);
                } else if (!existingPanel && freshPanel) {
                    const railRow = state.scrollBox.querySelector('[data-role="wp-studio-row"]');
                    if (railRow && railRow.nextSibling) {
                        state.scrollBox.insertBefore(freshPanel, railRow.nextSibling);
                    } else {
                        state.scrollBox.appendChild(freshPanel);
                    }
                }
            } else if (existingPanel) {
                existingPanel.remove();
            }
        }

        // 8. Update checklist
        if (state.scrollBox) {
            const existingChecklist = state.scrollBox.querySelector('[data-role="wp-checklist"]');
            if (existingChecklist) {
                const freshChecklist = _checklist(p);
                existingChecklist.replaceWith(freshChecklist);
            }
        }

        // 9. Redraw Konva layers
        _redrawGrid();
        _redrawDecor();
    }

    /**
     * The values the current layer may be painted with, in the **vocabulary's own
     * shape** - `{id, name, tags}` - because that is what the palette groups, the
     * select renders (`${o.name} (${o.id})`) and `_defaultValueForLayer` reads
     * (`o.id`). Wrapping them as `{value, label}` here would have every consumer
     * reading `undefined` and a dropdown full of it.
     */
    function _layerOptions(layer: string): WpPaletteEntry[] {
        const cached = _layerOptionsCache.get(layer);
        if (cached) return cached;
        const vocab = state.vocab || {};
        let res: WpPaletteEntry[] = [];
        if (layer === 'biome') res = (vocab.b || vocab.biomes || []).slice();
        else if (layer === 'road') res = (vocab.f || vocab.features || []).slice();
        else if (layer === 'climate') {
            // Shaped like a record so one renderer serves every layer, with the
            // base °C in the name because that number is the whole point of
            // painting it (task-557) and it otherwise lives only in the report.
            res = GM().CLIMATE_IDS.map((id: string) => {
                const c = GM().CLIMATES[id] || {};
                return {
                    id,
                    name: `${c.label} (${c.base}°C)`,
                    tags: ['climate'],
                };
            });
        }
        if (state.vocab) _layerOptionsCache.set(layer, res);
        return res;
    }

    /** A climate legend, shown while the climate layer is active (task-557). */
    function _climateLegend(): HTMLElement | null {
        if (state.layer !== 'climate') return null;
        const box = _el('div', 'display:flex;gap:6px;align-items:center;flex-wrap:wrap;' +
            'padding:4px 8px;margin-bottom:6px;border:1px solid var(--border,#3a3a44);' +
            'border-radius:6px;font-size:11px;');
        box.setAttribute('data-role', 'wp-climate-legend');
        box.appendChild(_el('span', 'color:var(--text-muted,#999);',
            'compiles to base_temperature:'));
        GM().CLIMATE_IDS.forEach((id: string) => {
            const c = GM().CLIMATES[id] || {};
            const chip = _el('span',
                'display:inline-flex;align-items:center;gap:4px;padding:1px 6px;'
                + 'border-radius:9px;border:1px solid var(--border,#3a3a44);',
                c.label);
            const swatch = _el('span',
                'display:inline-block;width:9px;height:9px;border-radius:2px;',
                '');
            swatch.style.background = c.color;
            chip.insertBefore(swatch, chip.firstChild);
            chip.title = `${c.label}: ${c.base}°C base, plus the day's curve`;
            box.appendChild(chip);
        });
        box.appendChild(_el('span', 'color:var(--text-muted,#777);',
            '· unpainted is Temperate'));
        box.title = 'A region takes the majority climate of its cells, and a '
            + 'climate boundary never splits an area. Only world scopes compile '
            + 'a climate; a town or interior keeps its own air.';
        return box;
    }

    /**
     * The layer's records grouped into rail sections (task-759).
     *
     * The grouping is derived from each record's own `terrain` and `tags` by the
     * view-model (`grid-model.paletteSections`) - rooms by purpose, buildings by
     * category, wild terrain by `terrain`, structure on its own. It is never a
     * hand-kept category list, which would be a second taxonomy beside the
     * vocabulary the compiler reads.
     */
    function _paletteSections(layer: string): WpPaletteSection[] {
        const p = state.payload;
        const mode = p ? (p.mode || (p.scope && p.scope.mode) || '') : '';
        const memoKey = `${layer}:${mode}`;
        const cached = _paletteSectionsCache.get(memoKey);
        if (cached) return cached;
        const all = GM().paletteSections(layer, _layerOptions(layer)) as WpPaletteSection[];
        // Both the toolbar value picker and the palette panel read through here,
        // so the mode filter (task-774) cannot make them disagree.
        const filtered = GM().paletteForMode(all, mode || null) as WpPaletteSection[];
        if (state.vocab) _paletteSectionsCache.set(memoKey, filtered);
        return filtered;
    }

    function _defaultValueForLayer(layer: string): string {
        // The floor layer is a *storey index* (engine/world_grid.py): 0 is ground,
        // so 1 - "one storey up" - is the only useful value to start dragging
        // with. It used to default to a 0..1 height fraction, which is not a
        // storey and cannot express "eighty floors up".
        // storey and cannot express "eighty floors up".
        if (layer === 'floor') return '1';
        const options = _layerOptions(layer);
        if (!options.length) return '';
        const preferred = ({ biome: 'sparse_forest', road: 'road' } as Record<string, string>)[layer];
        if (preferred && options.some((o) => o.id === preferred)) return preferred;
        return options[0].id || '';
    }

    /**
     * Open the painter on a scope.
     *
     * `options` arms the editor for a job: `{tool: 'area', areaId}` comes from
     * the graph's "Place on map…" action (task-528), so the author lands straight
     * in the place tool with the area they clicked already picked.
     */
    async function open(scopeId: string | null,
        options?: { tool?: string; areaId?: string | null } | null): Promise<void> {
        const opts = options || {};
        state.selectedArea = null;
        state.inspected = null;   // a cell of the previous scope means nothing here
        if (opts.tool) state.tool = opts.tool;
        if (opts.areaId) state.selectedArea = opts.areaId;
        if (state.overlay && document.body.contains(state.overlay)) {
            state.overlay.remove();
        }
        const overlay = _el('div',
            'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9500;display:flex;' +
            'align-items:center;justify-content:center;');
        overlay.addEventListener('click', (ev) => { if (ev.target === overlay) close(); });
        const panel = _el('div',
            'background:var(--bg-panel,#1b1b21);color:var(--text,#ddd);' +
            'border-radius:0;width:100%;height:100%;box-sizing:border-box;' +
            'display:flex;flex-direction:column;padding:14px;font-size:13px;');
        panel.setAttribute('data-role', 'worldpainter');
        state.overlay = overlay;
        state.body = panel;
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
        _bindKeys();

        await ensureVocab();
        await ensureBackgrounds();
        if (scopeId) {
            state.scopeId = scopeId;
            load(scopeId);
        } else {
            showChooser();
        }
    }

    function close(): void {
        _unbindKeys();
        _gridDragRelease();
        state.dimsBtn = null;
        state.cellSizePreview = null;
        if (state.resizeObs) { state.resizeObs.disconnect(); state.resizeObs = null; }
        if (state.overlay) state.overlay.remove();
        state.overlay = null;
        state.payload = null;
        state.scrollBox = null;
        state.scrollTop = 0;
        state.scrollRestored = false;
    }

    /**
     * Keys for the rail and the selection (task-536).
     *
     * One handler, because the interesting cases are *combinations* — Escape with
     * a selection and a half-finished route, Ctrl+A while a route is being drawn
     * — and two handlers deciding what each of them does is how a key ends up
     * meaning two things. The order is deliberate: the selection is dropped before
     * the tool is reset, so Escape peels off the least-committed thing first.
     *
     * Space = pan, so left-drag is free for painting or marqueeing.
     */
    function _bindKeys(): void {
        _unbindKeys();
        state._keyDown = (e) => {
            const tag = ((e.target as HTMLElement | null)?.tagName) || '';
            const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
            const isSelect = tag === 'SELECT';
            const p = state.payload;

            if (e.key === 'Escape') {
                if (typing) return;
                // The selection is the least-committed thing on screen: drop it
                // before dropping a route or resetting the tool.
                if (p && _selectedCells(p).length) {
                    _setSelection(p, {});
                    state.marquee = null;
                    _status('Selection cleared.');
                    _redrawDecor();
                    render();
                    return;
                }
                // Route points and a picked area are half-finished work: drop
                // them and go back to painting rather than leaving the tool armed.
                if (state.tool !== 'paint' || state.route.length || state.selectedArea
                    || state.inspected) {
                    state.tool = 'paint';
                    state.route = [];
                    state.selectedArea = null;
                    state.inspected = null;
                    if (state.routeInfoEl) state.routeInfoEl.textContent = _routeLabel();
                    _redrawDecor();
                    render();
                }
                return;
            }
            // Space pans even when a toolbar <select> still holds focus (bug-511).
            // Choosing a biome used to leave the dropdown focused, and the next
            // space press was consumed by the browser as "open the focused
            // dropdown" — the keydown was swallowed by the `typing` guard below,
            // so the pan handler never saw it. All controls blur on change (see
            // `_valueControl`/`_layerSelect`), but the guard has to hold *FIX*way:
            // a control focused by Tab must not silently disable panning.
            if (isSelect && e.code === 'Space') {
                e.preventDefault();
                if (!state.spaceDown) {
                    state.spaceDown = true;
                    _syncDraggable();
                }
                return;
            }
            if (typing) return;

            if ((e.ctrlKey || e.metaKey) && (e.key || '').toLowerCase() === 'a' && p) {
                e.preventDefault();
                const keys: Record<string, boolean> = {};
                for (let y = 0; y < p.grid!.h; y += 1) {
                    for (let x = 0; x < p.grid!.w; x += 1) keys[GM().cellKey(x, y)] = true;
                }
                _setSelection(p, keys);
                _status(`Selected all ${p.grid!.w * p.grid!.h} cells.`);
                _redrawDecor();
                render();
                return;
            }
            if (e.ctrlKey || e.metaKey) return;

            const tool = TOOLS.find(
                (t) => t[2].toLowerCase() === (e.key || '').toLowerCase());
            if (tool) { e.preventDefault(); _selectTool(tool[0]); return; }

            // Arrow keys (or WASD) nudge a selection. They only do that when there
            // is one to nudge: with nothing selected an arrow key is the map's to
            // use, and a selection the author cannot see is not worth guessing at.
            const nudge = {
                arrowup: [0, -1], w: [0, -1],
                arrowdown: [0, 1], s: [0, 1],
                arrowleft: [-1, 0], a: [-1, 0],
                arrowright: [1, 0], d: [1, 0],
            }[(e.key || '').toLowerCase()];
            if (nudge && p && _selectedCells(p).length) {
                e.preventDefault();
                _nudge(p, nudge[0], nudge[1]);
                return;
            }

            if (e.code !== 'Space' || state.spaceDown) return;
            state.spaceDown = true;
            _syncDraggable();
            e.preventDefault();
        };
        state._keyUp = (e) => {
            if (e.code !== 'Space') return;
            state.spaceDown = false;
            _syncDraggable();
        };
        document.addEventListener('keydown', state._keyDown);
        document.addEventListener('keyup', state._keyUp);
    }

    function _unbindKeys(): void {
        if (state._keyDown) document.removeEventListener('keydown', state._keyDown);
        if (state._keyUp) document.removeEventListener('keyup', state._keyUp);
        state._keyDown = null;
        state._keyUp = null;
        state.spaceDown = false;
    }

    // ───────────────────────────── loading ─────────────────────────────

    async function showChooser(): Promise<void> {
        state.scopeId = null;
        state.payload = null;
        const box = _renderShell('🗺️ WorldPainter');
        box.appendChild(_el('div', 'color:var(--text-muted,#999);margin-bottom:10px;',
            'Choose a scope to open its grid.'));
        const list = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;', 'Loading…');
        box.appendChild(list);
        box.appendChild(_btn('➕ New root scope', () => _promptNewScope(null)));
        try {
            const root = await _req(SCOPES_URL, { cache: 'no-store' });
            list.textContent = '';
            // task-623: this used to read only `root.children`, which is the
            // single ROOT scope. Its children -- the zone scopes an author
            // actually paints in -- were never walked, so the painter offered
            // 1 scope on a world that has 6. Walk the whole tree and show depth,
            // because the hierarchy is what tells you which scope is which.
            // `window.ScopeOptions` is a real window member (shared/scope-options.js).
            const scopeOptions = (window as unknown as {
                ScopeOptions?: { flattenScopes(payload: unknown): WpScopeCard[] };
            }).ScopeOptions;
            const scopes = scopeOptions
                ? scopeOptions.flattenScopes(root)
                : (root.children || []);
            if (!scopes.length) {
                list.appendChild(_el('div', 'color:var(--text-muted,#999);',
                    'No scopes yet. Create one to start painting.'));
                return;
            }
            scopes.forEach((card: WpScopeCard) => list.appendChild(_scopeCard(card)));
        } catch (e) {
            list.textContent = `Failed to load scopes: ${errText(e)}`;
        }
    }

    function _scopeCard(card: WpScopeCard, onOpen?: (card: WpScopeCard) => void): HTMLElement {
        // Indent by depth so a child zone reads as belonging to its parent.
        const indent = '  '.repeat(Math.max(0, card.depth || 0));
        const el = _el('div',
            'border:1px solid var(--border,#444);border-radius:8px;padding:8px 10px;' +
            'min-width:150px;cursor:pointer;background:var(--bg-card,#24242b);' +
            (card.depth ? 'margin-left:' + (card.depth * 16) + 'px;' : ''));
        const head = _el('div', 'display:flex;align-items:center;gap:6px;');
        head.appendChild(_el('span', 'font-weight:600;flex:1 1 auto;', indent + (card.name || card.id)));
        head.appendChild(_iconBtn('✏️', 'Rename scope', () => renameScope(card.id, card.name)));
        head.appendChild(_iconBtn('🗑', 'Delete scope', () => deleteScope(card.id, card.name)));
        el.appendChild(head);
        // Show what the scope holds, so the chooser is a chooser rather than a
        // list of names (task-615: never claim a scope with content is "not built").
        // The flat endpoint returns snake_case (`area_count`); the nested one used
        // camelCase in some shapes, so accept both rather than render nothing.
        const areas = card.area_count != null ? card.area_count : card.areaCount;
        const items = card.item_count != null ? card.item_count : card.itemCount;
        const bits = [`${card.kind || 'scope'} · ${card.state || ''}${card.mode ? ' · ' + card.mode : ''}`];
        if (areas != null) bits.push(`${areas} area${areas === 1 ? '' : 's'}`);
        if (items) bits.push(`${items} item${items === 1 ? '' : 's'}`);
        el.appendChild(_el('div', 'font-size:10px;color:var(--text-muted,#999);', bits.join(' · ')));
        el.addEventListener('click', () => (onOpen ? onOpen(card) : load(card.id)));
        return el;
    }

    /** Small icon button that doesn't trigger the card's own click. */
    function _iconBtn(label: string, title: string, onClick: () => void): HTMLButtonElement {
        const b = _el('button',
            'cursor:pointer;border:1px solid var(--border,#444);background:transparent;' +
            'color:var(--text,#ddd);border-radius:5px;padding:1px 5px;font-size:11px;line-height:1.2;',
            label);
        b.title = title;
        b.addEventListener('click', (e) => { e.stopPropagation(); onClick(); });
        return b;
    }

    async function load(scopeId: string): Promise<void> {
        _saveScopePrefs();
        state.scopeId = scopeId;
        state.selectedChild = null;
        state.view = null;      // a new scope opens fitted, or restored from prefs
        state.route = [];
        state.refEdit = false;  // reference adjust is per-scope
        state.refDrag = null;
        state.cellSizePreview = null;   // a candidate belongs to one scope only
        state.paintCache = null;
        state.paintCacheValid = false;
        _loadScopePrefs(scopeId);
        const box = _renderShell('🗺️ WorldPainter');
        box.appendChild(_el('div', 'color:var(--text-muted,#999);', 'Loading grid…'));
        try {
            state.payload = await _req(`${BASE}/${encodeURIComponent(scopeId)}/grid`,
                { cache: 'no-store' });
            render();
        } catch (e) {
            box.textContent = '';
            box.appendChild(_el('div', 'color:#e66;', `Failed to load grid: ${errText(e)}`));
        }
    }

    /**
     * Refetch the open scope's payload in place. Used after a rename/delete of a
     * scope that appears as a *card* in this scope's list: the card's name comes
     * from the payload, so redrawing it without refetching showed the pre-edit
     * list. Unlike `load()` this keeps the author's view and selection.
     */
    async function _reloadPayload(): Promise<void> {
        if (!state.scopeId) return;
        state.payload = await _req(`${BASE}/${encodeURIComponent(state.scopeId)}/grid`,
            { cache: 'no-store' });
        render();
    }

    /** Shared header (title + close) and a fresh body container. */
    function _renderShell(title: string): HTMLElement {
        // Read the author's position BEFORE the wipe below. Clearing the panel
        // detaches the old scroll box, and a detached element reports scrollTop
        // 0 - so reading it afterwards silently threw the view back to the top.
        // Only a box whose position has actually been applied is trusted, and only if it
        // can scroll. Two things make a capture wrong: an intermediate "Loading
        // grid…" shell has no overflow, and a second render inside the same task
        // sees the newest box before its scrollTop is applied - both report 0 and
        // would overwrite the author's real position.
        if (state.scrollBox && state.scrollRestored
                && state.scrollBox.scrollHeight > state.scrollBox.clientHeight) {
            state.scrollTop = state.scrollBox.scrollTop;
        }
        // Only ever called from open(), which assigns state.body before *FIX*thing
        // renders; the assertion states that rather than re-testing it.
        const panel = state.body!;
        panel.textContent = '';
        const head = _el('div', 'display:flex;align-items:center;gap:10px;margin-bottom:10px;');
        head.appendChild(_el('div', 'font-weight:700;font-size:15px;', title));
        const spacer = _el('div', 'flex:1;');
        head.appendChild(spacer);
        head.appendChild(_btn('Close', close));
        panel.appendChild(head);
        const box = _el('div', 'display:flex;flex-direction:column;flex:1 1 auto;min-height:0;overflow:auto;');
        panel.appendChild(box);
        state.scrollBox = box;
        // Fixed status bar at bottom of panel (task-776): stays visible without scrolling.
        const statusBar = _el('div',
            'flex:0 0 auto;margin-top:6px;font-size:12px;min-height:18px;display:flex;align-items:center;'
            + 'border-top:1px solid var(--border,#2b2b36);padding-top:4px;');
        statusBar.setAttribute('data-role', 'wp-status');
        statusBar.setAttribute('data-role-fixed', 'wp-status-bar');
        panel.appendChild(statusBar);
        _updateStatusBar();

        // Restore AFTER the content is in. load() calls this while the box is
        // still empty, and scrollTop on an element with nothing to scroll is
        // clamped to 0 - so setting it here stored 0 and lost the position. One
        // frame later the body is populated and the assignment sticks.
        const want = state.scrollTop;
        state.scrollRestored = false;
        requestAnimationFrame(function () {
            box.scrollTop = want;
            state.scrollRestored = true;
        });
        return box;
    }

    // ───────────────────────────── rendering ───────────────────────────

    function render(): void {
        const p = state.payload;
        if (!p) { showChooser(); return; }
        state.routeInfoEl = null;   // the old HUD element dies with the panel
        state.cellInfoEl = null;
        state.cellInfoKey = null;
        const box = _renderShell('🗺️ WorldPainter');

        box.appendChild(_breadcrumb(p.breadcrumb));
        box.appendChild(_toolbar(p));
        // The climate legend only exists while the climate layer is active, and
        // it sits directly under the layer control that switches to it (task-557).
        const legend = _climateLegend();
        if (legend) box.appendChild(legend);

        if (!p.scope.has_grid) {
            box.appendChild(_noGridPanel(p));
            box.appendChild(_checklist(p));
            _renderChildren(box, p);
            return;
        }

        box.appendChild(_featureBar(p));
        if (state.tool === 'area') box.appendChild(_areaBar(p));

        // Studio row: Tool rail on left, Canvas in center, Palette dock on right (task-881).
        // Docking the palette beside the canvas means opening it never shoves the
        // canvas below the fold or forces vertical scrolling to paint.
        const withRail = _el('div', 'display:flex;gap:10px;align-items:stretch;flex:1 1 auto;min-height:0;');
        withRail.setAttribute('data-role', 'wp-studio-row');
        withRail.appendChild(_toolRail(p));
        withRail.appendChild(_grid(p));
        if (state.paletteOpen) {
            const palette = _palettePanel();
            if (palette) withRail.appendChild(palette);
        }
        box.appendChild(withRail);
        const panel = _cellPanel(p);
        if (panel) box.appendChild(panel);
        // The "what next" checklist sits below the map, not above it. The canvas
        // is the thing being looked at, and a collapsed progress bar wedged
        // between the toolbar and the art was the only thing standing between an
        // author and their paint - so it now reports from under the image.
        box.appendChild(_checklist(p));
        _renderChildren(box, p);
        _updateStatusBar();
    }

    function _breadcrumb(trail?: WpScopeRef[] | null): HTMLElement {
        const row = _el('div', 'margin-bottom:8px;font-size:12px;display:flex;gap:6px;flex-wrap:wrap;');
        (trail || []).forEach((node, i) => {
            if (i) row.appendChild(_el('span', 'color:var(--text-muted,#888);', '›'));
            const link = _el('a', 'cursor:pointer;color:#7ab;', node.name);
            link.addEventListener('click', () => load(node.id));
            row.appendChild(link);
        });
        return row;
    }

    /**
     * The tool rail (task-536): a vertical column down the left of the canvas.
     *
     * Four tool buttons in a top row is a toolbar for four things; eight is a
     * toolbar for a spreadsheet. A rail keeps the active tool obvious, gives each
     * one a key, and leaves the width for the map — which is the thing being
      * looked at. The layer/value controls stay in the top row; the brush moved
      * to the rail so it travels with the active tool (task-536).
      */
    const TOOLS: [string, string, string, string][] = [
        ['select', '⬚ Select', 'V',
            'Click cells to select, shift-click to add, drag for a marquee. '
            + 'Ctrl+A all, Escape clear. With cells selected, Paint and Erase '
            + 'apply to the whole selection in one request.'],
        ['paint', '🖌 Paint', 'P',
            'Paint the current layer and value. Drag to stroke. '
            + 'Alt+click samples the active layer value under the cursor into the brush.'],
        ['erase', '🧽 Erase', 'E', 'Clear the current layer on a cell. Drag to stroke.'],
        ['move', '✥ Move', 'M',
            'Shift the selected cells\' contents one cell. Arrow keys, or WASD, '
            + 'or the nudge buttons. Clamped to the grid; one request, one undo.'],
        ['route', '🧭 Route', 'R', 'Click waypoints, then ✓ Paint route - paints the '
            + 'current layer along the line (1 cell = 1 turn).'],
        ['vision', '👁 Vision', 'L', 'Debug 2.5D line of sight (LoS) raycasting. '
            + 'Click an origin cell, then click *FIX* target cell to cast a sightline ray. '
            + 'Inspect elevation clearance, obscurity, and directional facing.'],
        ['feature', '🏠 Feature', 'F', 'Place a sub-zone (child scope) at a cell - not a '
            + 'road. Roads/bridges are painted on the road layer.'],
        ['area', '📍 Area', 'A', 'Put an area you already wrote (Northern Hills, Murk '
            + 'Lake…) on a cell of this map. Pick the area, then click where '
            + 'it belongs. Generate will not put a second area on that cell.'],
        ['inspect', '🔍 Inspect', 'I', 'Read a cell without changing it: what is painted '
            + 'on it, and which area or child scope sits there. Right-click does the '
            + 'same on *FIX* tool.'],
    ];

    function _recomputeVisionField(p: WpPayload): void {
        if (!state.visionOrigin) {
            state.visionVisibleSet = null;
            return;
        }
        const origFloor = state.visionOrigin.floor != null
            ? state.visionOrigin.floor
            : GM().tileFloor(p, state.visionOrigin.x, state.visionOrigin.y);
        const visSet = GM().computeVisibleCells(
            p,
            [state.visionOrigin.x, state.visionOrigin.y, origFloor],
            60,
            state.visionFacing || null,
            state.visionFacing ? 120.0 : 360.0
        );
        state.visionVisibleSet = visSet;
    }

    function _toolRail(p: WpPayload): HTMLElement {
        const rail = _el('div', 'display:flex;flex-direction:column;gap:4px;flex:0 0 auto;');
        rail.setAttribute('data-role', 'wp-rail');
        TOOLS.forEach(([id, label, key, hint]) => {
            const active = state.tool === id;
            const btn = _btn(label, () => _selectTool(id),
                'text-align:left;white-space:nowrap;'
                + (active ? 'outline:2px solid #7ab;background:#1e3550;' : ''),
                `${hint}\n\nShortcut: ${key}`);
            btn.setAttribute('data-tool', id);
            if (active) btn.setAttribute('aria-pressed', 'true');
            // Hooked into the HelpCenter per tool (task-521). The rail was eight
            // buttons with hover strings and no coach card behind *FIX* of them.
            _help(btn, 'wp-tool-' + id);
            rail.appendChild(btn);
        });
        const options = _railOptions(p);
        if (options) {
            rail.appendChild(_el('hr', 'border:0;border-top:1px solid var(--border,#3a3a44);'
                + 'width:100%;margin:6px 0;'));
            rail.appendChild(options);
        }
        return rail;
    }

    /** The options that belong to the *active* tool (task-536). */
    function _railOptions(p: WpPayload): HTMLElement | null {
        const count = _selectedCells(p).length;
        if (state.tool === 'select') {
            const box = _el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                count ? `${count} cell${count === 1 ? '' : 's'} selected` : 'no cells selected'));
            box.appendChild(_btn('Select all', () => {
                const cells: Record<string, boolean> = {};
                for (let y = 0; y < p.grid!.h; y += 1) {
                    for (let x = 0; x < p.grid!.w; x += 1) cells[GM().cellKey(x, y)] = true;
                }
                _setSelection(p, cells);
                _status(`Selected all ${p.grid!.w * p.grid!.h} cells.`);
            }, 'width:100%;', 'Select every cell on this grid (Ctrl+A)'));
            box.appendChild(_btn('Clear', () => {
                _setSelection(p, {});
                _status('Selection cleared.');
            }, 'width:100%;', 'Select nothing (Escape)'));
            if (count) {
                box.appendChild(_btn('Invert', () => {
                    const next: Record<string, boolean> = {};
                    for (let y = 0; y < p.grid!.h; y += 1) {
                        for (let x = 0; x < p.grid!.w; x += 1) {
                            const k = GM().cellKey(x, y);
                            if (!_sel(p)[k]) next[k] = true;
                        }
                    }
                    _setSelection(p, next);
                }, 'width:100%;', 'Select everything you had not selected'));
            }
            return box;
        }
        if (state.tool === 'move') {
            const box = _el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                count ? `Move ${count} cell${count === 1 ? '' : 's'}` : 'Select cells first'));
            const grid = _el('div', 'display:grid;grid-template-columns:repeat(3,1fr);gap:2px;');
            grid.appendChild(_el('span'));
            grid.appendChild(_btn('↑', () => _nudge(p, 0, -1), 'padding:2px 6px;', 'Up'));
            grid.appendChild(_el('span'));
            grid.appendChild(_btn('←', () => _nudge(p, -1, 0), 'padding:2px 6px;', 'Left'));
            grid.appendChild(_btn('↓', () => _nudge(p, 0, 1), 'padding:2px 6px;', 'Down'));
            grid.appendChild(_btn('→', () => _nudge(p, 1, 0), 'padding:2px 6px;', 'Right'));
            box.appendChild(grid);
            return box;
        }
        if (state.tool === 'paint' || state.tool === 'erase' || state.tool === 'route') {
            const box = _el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);', 'brush'));
            const brushSel = _el('select', 'padding:3px;border-radius:5px;');
            brushSel.setAttribute('data-role', 'wp-brush');
            [1, 2, 3, 5, 8, 12].forEach((n) => {
                const opt = _el('option', null, `${n}×${n}`);
                opt.value = String(n);
                if (n === state.brush) opt.selected = true;
                brushSel.appendChild(opt);
            });
            brushSel.addEventListener('change', () => {
                state.brush = parseInt(brushSel.value, 10) || 1;
                brushSel.blur();
            });
            box.appendChild(brushSel);
            _help(brushSel, 'wp-brush');
            return box;
        }
        if (state.tool === 'vision') {
            const box = _el('div', 'display:flex;flex-direction:column;gap:5px;align-items:flex-start;width:100%;');
            const orig = state.visionOrigin;
            const tgt = state.visionTarget;
            box.appendChild(_el('span', 'font-size:11px;font-weight:600;color:var(--text,#ddd);', 'Raycast Debugger'));
            box.appendChild(_el('span', 'font-size:10.5px;color:var(--text-muted,#999);line-height:1.3;',
                orig ? `Origin: (${orig.x}, ${orig.y}) z=${orig.floor ?? 0}` : 'Click canvas to set origin'));
            if (tgt) {
                box.appendChild(_el('span', 'font-size:10.5px;color:var(--text-muted,#999);line-height:1.3;',
                    `Target: (${tgt.x}, ${tgt.y}) z=${tgt.floor ?? 0}`));
            }
            if (state.visionRay) {
                const vis = state.visionRay.visible;
                const statusBadge = _el('span',
                    'font-size:10.5px;padding:2px 6px;border-radius:4px;font-weight:700;'
                    + (vis ? 'background:#1f4a2c;color:#3fb950;' : 'background:#5c2226;color:#f85149;'),
                    vis ? '✔ CLEAR SIGHTLINE' : '✖ BLOCKED');
                box.appendChild(statusBadge);
                if (state.visionRay.reason) {
                    box.appendChild(_el('span', 'font-size:10px;color:#f85149;line-height:1.2;', state.visionRay.reason));
                }
            }

            // Facing cone control
            box.appendChild(_el('span', 'font-size:10px;color:var(--text-muted,#999);margin-top:3px;', 'facing arc (120°):'));
            const facingSel = _el('select', 'padding:2px 4px;font-size:11px;border-radius:4px;width:100%;');
            facingSel.setAttribute('data-role', 'wp-vision-facing');
            const dirs = [
                ['', 'Omnidirectional (360°)'],
                ['n', 'North (N)'],
                ['ne', 'North-East (NE)'],
                ['e', 'East (E)'],
                ['se', 'South-East (SE)'],
                ['s', 'South (S)'],
                ['sw', 'South-West (SW)'],
                ['w', 'West (W)'],
                ['nw', 'North-West (NW)']
            ];
            dirs.forEach(([val, lbl]) => {
                const opt = _el('option', null, lbl);
                opt.value = val;
                if ((state.visionFacing || '') === val) opt.selected = true;
                facingSel.appendChild(opt);
            });
            facingSel.addEventListener('change', () => {
                state.visionFacing = facingSel.value || null;
                if (state.visionOrigin && state.payload) {
                    _recomputeVisionField(state.payload);
                }
                _redrawDecor();
            });
            box.appendChild(facingSel);

            // Vision Lens toggle
            const lensBtn = _btn(state.visionLens ? '✔ Vision Lens: ON' : 'Vision Lens: OFF', () => {
                state.visionLens = !state.visionLens;
                if (state.visionLens && state.visionOrigin && state.payload) {
                    _recomputeVisionField(state.payload);
                }
                render();
            }, 'font-size:10.5px;width:100%;' + (state.visionLens ? 'outline:1px solid #7ab;background:#1e3550;' : ''));
            lensBtn.title = 'Highlight all visible cells from origin (LoS field)';
            box.appendChild(lensBtn);

            if (orig || tgt) {
                box.appendChild(_btn('Clear ray', () => {
                    state.visionOrigin = null;
                    state.visionTarget = null;
                    state.visionRay = null;
                    state.visionVisibleSet = null;
                    _redrawDecor();
                    _status('Vision debugger cleared.');
                }, 'font-size:10.5px;width:100%;', 'Clear current origin and target'));
            }
            return box;
        }
        return null;
    }

    /**
     * Whether the canvas pans on a plain left-drag, re-decided on every tool
     * change (task-536).
     *
     * A drag means a different thing per tool — pan, paint stroke, marquee, and now
     * "nothing" under Move — and `draggable` is set once when the stage is wired.
     * A tool switch therefore has to re-ask, or the author selects a tool and drags
     * the map across instead of moving their cells.
     */
    function _syncDraggable(): void {
        if (!state.stage) return;
        const toolOwnsDrag = _isPaintTool() || state.tool === 'select'
            || state.tool === 'move';
        state.stage.draggable(state.spaceDown
            || (!state.refEdit && !state.gridEdit && !toolOwnsDrag));
    }

    function _selectTool(id: string): void {
        state.tool = id;
        if (id !== 'area') state.selectedArea = null;
        if (id !== 'move') state.nudged = null;
        state.marquee = null;
        state.brushHover = null;
        _syncDraggable();
        _saveScopePrefs();
        softRender();
    }

    /**
     * The per-mode "what do I do now" list, with live progress.
     *
     * The painter explained its *controls* and never its *sequence*. A new scope
     * showed a tool rail, four layers and a Generate button, and nothing said
     * that a town is painted ground → streets → walls → buildings → names, or
     * that a cell with no name cannot be asked for by name. That ordering is the
     * part which is not inferable from the UI, so it is written out here.
     *
     * Progress is **derived from the payload, not remembered in localStorage**:
     * a checkbox an author can tick without doing the thing is worse than no
     * checklist, and the state that decides "done" already exists on the record.
     * The panel opens itself for a scope with nothing on it yet and gets out of
     * the way once there is paint.
     */
    function _checklist(p: WpPayload): HTMLElement {
        const steps = _checklistSteps(p);
        const done = steps.filter((s) => s.done).length;
        const allDone = done === steps.length;

        // Self-showing while the author has not taken control of it: open for a
        // scope with nothing on it, collapse once there is real paint. Once they
        // click it, their choice sticks - an author who collapsed it to get on
        // with painting should not have it pop back open on the next stroke.
        if (!state.checklistTouched) {
            state.checklistOpen = done === 0 || !_paintedCount(p);
        }
        const toggle = _btn(
            allDone ? '✔ all done' : `📋 ${done}/${steps.length} - what next`,
            () => {
                state.checklistOpen = !state.checklistOpen;
                state.checklistTouched = true;
                softRender();
            },
            'font-size:11px;padding:2px 8px;',
            allDone
                ? 'Every step for this mode is done.'
                : 'What this kind of scope needs, in the order it needs it.');
        _help(toggle, 'wp-checklist');

        const wrap = _el('div',
            'border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;' +
            'padding:6px 8px;background:rgba(13,17,23,0.35);');
        wrap.setAttribute('data-role', 'wp-checklist');
        wrap.appendChild(toggle);
        if (!state.checklistOpen) return wrap;

        const mode = p.mode || 'world';
        const hint = _el('div', 'font-size:11px;color:var(--text-muted,#999);' +
            'padding:4px 0 6px;line-height:1.5;');
        hint.textContent = _checklistIntro(mode);
        wrap.appendChild(hint);

        for (const s of steps) {
            const row = _el('div', 'display:flex;gap:6px;align-items:flex-start;' +
                'padding:3px 0;font-size:12px;line-height:1.45;' +
                (s.done ? 'color:var(--text-muted,#999);' : 'color:var(--text,#ddd);'));
            row.appendChild(_el('span', 'flex:0 0 auto;width:14px;text-align:center;',
                s.done ? '✔' : '○'));
            const text = _el('div', 'flex:1;min-width:0;');
            text.appendChild(_el('b', null, s.title + ' '));
            text.appendChild(document.createTextNode(s.how));
            if (s.done && s.note) {
                text.appendChild(_el('div', 'color:#7a7;', '→ ' + s.note));
            }
            row.appendChild(text);

            if (!s.done) {
                row.style.cursor = 'pointer';
                row.title = 'Click to arm this step (' + (s.tool ? `tool: ${s.tool}` : 'action') + ')';
                row.setAttribute('data-actionable', 'true');
                row.addEventListener('click', () => {
                    if (s.tool) state.tool = s.tool;
                    if (s.layer) state.layer = s.layer;
                    if (s.value) state.value = s.value;
                    _saveScopePrefs();
                    if (s.action) {
                        s.action();
                    } else {
                        softRender();
                        _status(`Armed step: ${s.title}` + (s.tool ? ` Tool: ${s.tool}` : '') + (s.layer ? ` (${s.layer}: ${s.value})` : '') + '.', false);
                    }
                });
            }
            wrap.appendChild(row);
        }
        return wrap;
    }

    function _paintedCount(p: WpPayload | null): number {
        const layers = (p && p.layers) || {};
        const n = (layer: string) => Object.keys(layers[layer] || {}).length;
        return n('biome') + n('road');
    }

    function _checklistIntro(mode: string): string {
        if (mode === 'settlement' || mode === 'town') {
            return 'A settlement is painted inside-out: the ground it stands on, the streets '
                + 'across it, the wall around it, then the buildings on it, then the '
                + 'names that make them addressable. Every painted cell becomes a '
                + 'place; walls are structure and never do, which is what makes them '
                + 'walls.';
        }
        if (mode === 'interior') {
            return 'An interior is a floor plan. Paint rooms, join them with doors, '
                + 'put a storey number where the level changes, and name the rooms - '
                + 'corridors always merge into one place, rooms never do.';
        }
        return 'A world scope is deliberately coarse: the shape of the land and how '
            + 'you get around it. Detail belongs one rung down in a child scope, so '
            + 'a single Generate never mints thousands of places at once.';
    }

    /**
     * Steps per mode, each with a `done` predicate over the payload.
     *
     * The `how` half of each line is the part that is not inferable from a
     * tooltip: which *order*, which *layer*, and which value type. The `done`
     * half only ever reads state the server already told us, so a step cannot
     * claim itself satisfied by something that does not compile.
     */
    function _checklistSteps(p: WpPayload): WpChecklistStep[] {
        const mode = p.mode || 'world';
        const layers = (p && p.layers) || {};
        const biomeCells = Object.keys(layers.biome || {});
        const roadCells = Object.keys(layers.road || {});
        const names = Object.values(p.names || {}).filter(Boolean).length;
        const children = (p.children || []).length;
        const generated = p.scope.state === 'materialized';
        const wallCells = biomeCells.filter((k) => /(^|,)wall$/.test(
            String((layers.biome || {})[k] || ''))).length;
        const buildingCells = biomeCells.filter((k) => {
            const v = String((layers.biome || {})[k] || '');
            return /cottage|house|residential|tenement|inn|tavern|shop|smithy|workshop|warehouse|mill|barn|chapel|shrine|temple|town_hall|market|mansion|brothel|school|infirmary|library|stable|watch_house|bank|fast_food|mall/.test(v);
        }).length;

        const grid: WpChecklistStep = {
            title: 'Size the grid.',
            how: 'One cell is one minute of walking, so the size is how long the '
                + 'place takes to cross. ▦ Grid… sets it.',
            done: !!p.scope.has_grid,
            action: () => _openGridDialog(p),
        };
        const ground: WpChecklistStep = {
            title: 'Paint the ground.',
            how: 'Biome layer, a big brush, dragged over the area. Tick "merge '
                + 'same-biome" or every cell becomes its own area.',
            done: biomeCells.length > 0,
            tool: 'paint',
            layer: 'biome',
            value: 'sparse_forest',
        };
        const roads: WpChecklistStep = {
            title: 'Lay the roads.',
            how: 'Road layer, value "road", with the 🧭 Route tool — click '
                + 'waypoints, then ✓ Paint route.',
            done: roadCells.length > 0,
            tool: 'route',
            layer: 'road',
            value: 'road',
        };
        const namesStep: WpChecklistStep = {
            title: 'Name the places.',
            how: 'Right-click a cell, use the name field. A place with no name '
                + 'compiles to "Inn (Eldenford 12,7)" and cannot be asked for.',
            done: names > 0 && names >= (biomeCells.length + roadCells.length) * 0.5,
            tool: 'select',
        };
        const generateStep: WpChecklistStep = {
            title: 'Generate.',
            how: 'Turns the painted cells into real areas and ways. Do it last, '
                + 'and generate the parent before its children so the gateways '
                + 'between them get minted.',
            done: generated,
            note: 'already generated - Ungenerate to start over',
            action: () => generate(),
        };
        const reference: WpChecklistStep = {
            title: 'Line the art up.',
            how: 'Load a reference image, then ▦ match so the grid takes the '
                + "image's aspect and a cell is the same place in both.",
            done: !!(p.reference && p.reference.image),
            action: () => {
                const sel = state.overlay && state.overlay.querySelector('[data-role="wp-bg-select"]') as HTMLSelectElement | null;
                if (sel) sel.focus();
                else _status('Choose a reference image from the HUD dropdown.', false);
            },
        };

        if (mode === 'settlement' || mode === 'town') {
            return [grid, ground, roads,
                { title: 'Wall it in.', how: 'Biome layer, value "wall", along the '
                    + 'perimeter. Walls are structure: they never become places, '
                    + 'which is exactly what makes them walls.',
                    done: wallCells > 0,
                    tool: 'paint',
                    layer: 'biome',
                    value: 'wall' },
                { title: 'Open the gates.', how: 'Road layer, values "gate" and '
                    + '"bridge", on the wall line where a road leaves. This is how '
                    + 'a town gets more than one way in.',
                    done: roadCells.some((k) => /gate|bridge|ford|tunnel/.test(
                        String((layers.road || {})[k] || ''))),
                    tool: 'paint',
                    layer: 'road',
                    value: 'gate' },
                { title: 'Place the buildings.', how: 'One cell each, from the '
                    + 'Buildings section of the value list. Buildings never merge, '
                    + 'so a terrace stays a terrace.',
                    done: buildingCells > 0,
                    tool: 'paint',
                    layer: 'biome',
                    value: 'house' },
                namesStep,
                { title: 'Give the buildings interiors.', how: '➕ Add feature… '
                    + 'names a child scope (mode becomes interior), then 🏠 Feature '
                    + 'places it on the building\'s cell.',
                    done: children > 0,
                    tool: 'feature' },
                generateStep];
        }
        if (mode === 'interior') {
            return [grid, ground, roads, namesStep, generateStep];
        }
        return [grid, reference, ground, roads, namesStep, generateStep];
    }

    function _toolbar(p: WpPayload): HTMLElement {
        const wrap = _el('div', 'display:flex;flex-wrap:nowrap;gap:8px;align-items:center;' +

            'padding:8px;border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;' +

            'overflow-x:auto;');
        const modeBadge = _el('span',
            'font-size:11px;padding:2px 8px;border-radius:10px;background:#2d4a6b;color:#cfe;',
            `mode: ${p.mode || 'unset'}`);
        wrap.appendChild(modeBadge);

        // The tools themselves live in the left rail now (task-536); what is left
        // here is what the *write* tools share, plus the compile controls.
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);',
            'layer'));
        const layerSel = _el('select', 'padding:3px;border-radius:5px;');
        layerSel.setAttribute('data-role', 'wp-layer');
        layerSel.title = 'Which layer you paint: biome, road or floor. '
            + 'Roads, bridges and fords are on the road layer. Floor is a storey '
            + 'number: 0 is ground, 1 one up, -1 one down, and as far as you like.';
        GM().PAINT_LAYERS.forEach((l: string) => {
            const opt = _el('option', null, l);
            opt.value = l;
            if (l === state.layer) opt.selected = true;
            layerSel.appendChild(opt);
        });
        layerSel.addEventListener('change', () => {
            state.layer = layerSel.value;
            state.value = _defaultValueForLayer(state.layer);
            _saveScopePrefs();
            softRender();
        });
        _help(wrap.appendChild(layerSel), 'wp-layer');
        wrap.appendChild(_help(_valueControl(), 'wp-value')!);
        wrap.appendChild(_recentsRow());

        // Unified Grid control (task-876): combines exact-number dialog and on-canvas direct adjust.
        const gridBox = _el('div', 'position:relative;display:inline-flex;align-items:center;');
        const gridBtn = _btn(
            (state.gridEdit ? '✔ ' : '▦ ') + (p.grid ? `${p.grid.w}×${p.grid.h}` : 'Grid') + ' ▾',
            () => {
                const existing = gridBox.querySelector('[data-role="wp-grid-menu"]');
                if (existing) { existing.remove(); return; }
                const menu = _el('div',
                    'position:absolute;top:100%;left:0;z-index:99;background:var(--bg-card,#23232b);'
                    + 'border:1px solid var(--border,#3a3a44);border-radius:6px;padding:6px;'
                    + 'display:flex;flex-direction:column;gap:4px;min-width:180px;box-shadow:0 4px 12px rgba(0,0,0,0.5);margin-top:2px;');
                menu.setAttribute('data-role', 'wp-grid-menu');

                const adjustBtn = _btn(state.gridEdit ? '✔ Done adjusting handles' : '✥ Adjust handles on canvas', () => {
                    menu.remove();
                    state.gridEdit = !state.gridEdit;
                    state.gridDrag = null;
                    _gridDragRelease();
                    render();
                    _status(state.gridEdit
                        ? 'Grid adjust: drag the green handle on cell (0,0) to resize cells inside the image, '
                          + 'drag the frame to move the scope on the graph map, or drag the E/S/SE handles '
                          + 'to resize the frame.'
                        : 'Grid adjust off.', false);
                }, 'text-align:left;font-size:11px;' + (state.gridEdit ? 'outline:1px solid #7ab;background:#1e3550;' : ''));
                adjustBtn.setAttribute('data-role', 'wp-grid-adjust');
                adjustBtn.title = 'Resize cells (drag the green corner on cell 0,0), move the grid on the graph map, or resize the frame';
                menu.appendChild(adjustBtn);

                const exactBtn = _btn('▦ Exact dimensions…', () => {
                    menu.remove();
                    _openGridDialog(p);
                }, 'text-align:left;font-size:11px;');
                exactBtn.title = 'Open dialog to set exact width, height, mode, or choose region presets';
                menu.appendChild(exactBtn);

                gridBox.appendChild(menu);
            },
            'font-size:11px;' + (state.gridEdit ? 'outline:2px solid #7ab;background:#1e3550;' : ''),
            'Grid settings: resize dimensions, presets, or adjust directly on canvas'
        );
        gridBox.appendChild(gridBtn);
        wrap.appendChild(gridBox);

        const lensBtn = _btn(
            state.visionLens ? '👁 Vision Lens: ON' : '👁 Vision Lens',
            () => {
                state.visionLens = !state.visionLens;
                if (state.visionLens && !state.visionOrigin && p.grid) {
                    state.visionOrigin = {
                        x: Math.floor(p.grid.w / 2),
                        y: Math.floor(p.grid.h / 2),
                        floor: GM().tileFloor(p, Math.floor(p.grid.w / 2), Math.floor(p.grid.h / 2))
                    };
                }
                if (state.visionOrigin && state.payload) {
                    _recomputeVisionField(state.payload);
                }
                render();
            },
            'font-size:11px;' + (state.visionLens ? 'outline:2px solid #58a6ff;background:#1f4a7d;' : ''),
            'Toggle Character Vision Lens: highlight 2.5D raycast line-of-sight on grid'
        );
        lensBtn.setAttribute('data-role', 'wp-vision-lens');
        wrap.appendChild(lensBtn);

        wrap.appendChild(_btn('➕ Add feature…', () => _promptNewScope(p.scope.id)));

        // Why this scope cannot be compiled yet, and what to do about it
        // (engine/world_compile.preflight). The compiler refuses the same
        // conditions, but it refuses them *after* the click and only states the
        // rule - so a scope promoted from existing areas (always `baked`, never
        // carrying paint) used to fail with a sentence that explained neither how
        // it got that way nor how out of it. Said here, the button and its
        // reason are side by side.
        const blockers = Array.isArray(p.blockers) ? p.blockers : [];
        if (blockers.length) wrap.appendChild(_blockerBadge(blockers));
        // A building *type* brings its own floor plan (task-567). Only meaningful
        // on an interior scope, and offering it elsewhere would let an author paint
        // rooms onto a world map, which is a wall grid already says something.
        if (p.scope.mode === 'interior') {
            wrap.appendChild(_help(_btn('🏠 Paint an interior…', paintInterior, '',
                'Paint a building type\'s floor plan in as cells: a tavern gets a '
                + 'tap room, kitchen and cellar. It is a draft - edit the cells, '
                + 'then Generate.'), 'wp-paint-interior')!);
        }

        // Compile the painted grid into real area/way nodes (task-496/398).
        const merge = _el('input');
        merge.type = 'checkbox';
        merge.checked = !!state.merge;
        merge.setAttribute('data-role', 'wp-merge');
        merge.addEventListener('change', () => { state.merge = merge.checked; render(); });
        _help(wrap.appendChild(merge), 'wp-merge');
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);',
            'merge same-biome'));

        // Sibling-scope border traversal (task-775): stitch facing border cells
        // directly across adjacent child scopes placed on a parent chunk grid.
        const sib = _el('input');
        sib.type = 'checkbox';
        const sibOwn = !!(p.sibling_traversal || (p.scope && p.scope.sibling_traversal));
        const sibEff = !!(p.sibling_traversal_effective || (p.scope && p.scope.sibling_traversal_effective));
        sib.checked = sibOwn || sibEff;
        sib.setAttribute('data-role', 'wp-sibling-traversal');
        sib.title = sibEff && !sibOwn
            ? 'Inherited from parent scope - click to set explicitly on this scope'
            : 'Stitch facing passable border cells directly between adjacent sibling scopes (task-775)';
        sib.addEventListener('change', async () => {
            try {
                state.payload = await _post(
                    `/${encodeURIComponent(p.scope.id)}/grid/sibling_traversal`,
                    { enabled: sib.checked });
                _notify(true);
                render();
                _status(sib.checked
                    ? 'Sibling border traversal enabled.'
                    : 'Sibling border traversal disabled.', false);
            } catch (e) {
                _status(`Sibling traversal failed: ${errText(e)}`, true);
            }
        });
        wrap.appendChild(sib);
        const sibLabel = _el('span', 'font-size:12px;color:var(--text-muted,#999);',
            'sibling traversal');
        sibLabel.title = sib.title;
        wrap.appendChild(sibLabel);

        // Node-cost estimate, so painting 5,000 cells can't surprise the author
        // with a 15,000-node graph ("the laptop killer").
        const est = GM().estimateCompile(p, state.merge);
        const estEl = _el('span', 'font-size:11px;color:'
            + (est.total > 3000 ? '#c96' : 'var(--text-muted,#999)') + ';',
            `≈ ${est.areas} areas · ${est.ways} ways`
            + (est.links ? ` · 🔗 ${est.links} linked` : ''));
        estEl.title = est.links
            ? `${est.links} island(s) have no painted neighbour; each is joined to the `
              + 'nearest painted cell with a single way (not one per neighbour).'
            : 'Areas and ways this grid will compile to';
        estEl.setAttribute('data-role', 'wp-estimate');
        _help(wrap.appendChild(estEl), 'wp-estimate');
        const blocked = blockers.filter((b) => b && b.severity === 'block');
        wrap.appendChild(_help(_btn('⚙ Generate', () => generate(), 'outline:1px solid #7ab;',
            blocked.length
                ? 'This scope cannot be compiled yet - ' + blocked.map((b) => b.text).join(' ')
                : 'Turn this scope\'s painted cells into real areas and ways.'),
            'wp-generate')!);
        wrap.appendChild(_help(
            _btn('🧹 Ungenerate', () => ungenerate(), 'color:#c96;',
                'Delete this zone\'s generated nodes but keep its painted grid, so you can regenerate a clean slate.'),
            'wp-ungenerate')!);

        wrap.appendChild(_btn('⟳', () => load(state.scopeId!)));
        return wrap;
    }

    /**
     * The compact value control in the toolbar (task-759).
     *
     * It shows the tile you are about to paint (swatch + name) and its one-line
     * description, and a button that opens the palette panel (`_palettePanel`).
     * The tile itself is chosen in the panel; this is the read-out. A numeric
     * layer (floor) has no vocabulary and stays a free-text input.
     */
    function _valueControl(): HTMLElement {
        const options = _layerOptions(state.layer);
        if (state.layer === 'floor' || !options.length) {
            // No vocabulary (fetch failed) or a numeric layer: free text.
            const wrap = _el('div', 'display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap;');
            const input = _el('input',
                'width:90px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            input.setAttribute('data-role', 'wp-value');
            input.value = state.value;
            input.placeholder = state.layer === 'floor' ? '+1 / -1' : 'value';
            input.title = state.layer === 'floor'
                ? 'Storey: 0 is ground, 1 is one up, -1 one down. Unbounded - 3 for a '
                  + 'room three storeys up, 80 for a tower, -900 for a hole.'
                : `Value painted on the ${state.layer} layer.`;
            input.addEventListener('input', () => { state.value = input.value; });
            wrap.appendChild(input);

            if (state.layer === 'floor' && state.payload && state.payload.grid) {
                const btnImport = _btn('📥 Import heightmap…', () => _openHeightmapImportDialog(state.payload!),
                    'font-size:11px;padding:2px 6px;', 'Import greyscale heightmap PNG into the floor layer (task-877)');
                btnImport.setAttribute('data-role', 'wp-heightmap-import');
                wrap.appendChild(btnImport);

                const btnExport = _btn('📤 Export heightmap…', () => _openHeightmapExportDialog(state.payload!),
                    'font-size:11px;padding:2px 6px;', 'Export floor layer as greyscale PNG (task-877)');
                btnExport.setAttribute('data-role', 'wp-heightmap-export');
                wrap.appendChild(btnExport);
            }
            return wrap;
        }
        const sections = _paletteSections(state.layer);
        const all = GM().flattenPalette(sections) as WpPaletteTile[];
        const ids = all.map((t) => t.id);
        if (ids.indexOf(state.value) < 0) state.value = ids[0] || '';
        const wrap = _el('div', 'display:flex;gap:6px;align-items:center;flex-wrap:wrap;');
        // The palette shows the tile as a colour as well as a name (task-596):
        // this is the same colour the map paints, so picking "Wall" vs "Forest"
        // is a decision about the map, not a guess from a label.
        const swatch = _el('span', 'display:inline-block;width:14px;height:14px;' +
            'border-radius:3px;border:1px solid #555;flex:0 0 auto;');
        swatch.setAttribute('data-role', 'wp-value-swatch');
        wrap.appendChild(swatch);
        const pick = _btn('', () => { state.paletteOpen = !state.paletteOpen; _saveScopePrefs(); softRender(); },
            'min-width:150px;text-align:left;',
            'Open the palette to choose what this layer paints (task-759).');
        pick.setAttribute('data-role', 'wp-value');
        wrap.appendChild(pick);
        // What the tile *is* and *does* (task-596): the palette used to be a wall
        // of names; the detail line names the prose, the kind, the ground, and -
        // for the road layer - the terrain it crosses and the verb you arrive
        // with, which is the difference between a bridge and a road.
        const detail = _el('div', 'font-size:11px;color:var(--text-muted,#999);' +
            'line-height:1.4;flex-basis:100%;max-width:460px;');
        detail.setAttribute('data-role', 'wp-value-detail');
        const tile = GM().paletteTile(sections, state.value) as WpPaletteTile | null;
        const text = tile ? GM().tileDetail(state.layer, tile.rec) as string : '';
        pick.textContent = (tile ? tile.name : '(no tiles)') + '  ▾';
        detail.textContent = text;
        detail.title = text;
        swatch.style.background = GM().layerColor(state.layer, state.value) || 'transparent';
        swatch.title = tile ? tile.name : '';
        wrap.appendChild(detail);
        return wrap;
    }

    /**
     * The palette surface (task-759): a category rail derived from the records'
     * own terrain/tags, a tile grid, a search box, and a detail panel. It is a
     * view over the same vocabulary the compiler reads - no second read of
     * `biomes.json` - and picking a tile sets `state.value` and nothing else.
     *
     * Open state, category and query live on `state` so a render (which the panel
     * itself triggers on a pick) rebuilds it where the author left it.
     */
    function _palettePanel(): HTMLElement | null {
        const layer = state.layer;
        if (layer === 'floor') return null;
        const sections = _paletteSections(layer);
        if (!sections.length) return null;
        const wrap = _el('div', 'border:1px solid var(--border,#3a3a44);border-radius:8px;' +
            'padding:8px;background:var(--bg-card,#23232b);width:320px;flex:0 0 320px;' +
            'display:flex;flex-direction:column;gap:6px;max-height:560px;overflow:hidden;');
        wrap.setAttribute('data-role', 'wp-palette');
        const head = _el('div', 'display:flex;align-items:center;gap:6px;');
        head.appendChild(_el('span', 'font-weight:600;font-size:13px;', 'Palette'));
        head.appendChild(_el('div', 'flex:1;'));
        head.appendChild(_btn('✕', () => { state.paletteOpen = false; _saveScopePrefs(); softRender(); },
            'padding:2px 8px;', 'Close the palette dock'));
        wrap.appendChild(head);

        const subHint = _el('div', 'font-size:11px;color:var(--text-muted,#999);line-height:1.2;',
            'hover to preview · click to paint');
        wrap.appendChild(subHint);

        const search = _el('input', 'width:100%;box-sizing:border-box;padding:3px 6px;border-radius:5px;' +
            'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
        search.type = 'search';
        search.placeholder = 'Search tiles by name or id…';
        search.value = state.paletteQuery;
        search.setAttribute('data-role', 'wp-palette-search');
        search.setAttribute('aria-label', 'Search palette tiles by name or id');
        wrap.appendChild(search);

        const rail = _el('div', 'display:flex;gap:4px;flex-wrap:wrap;max-height:90px;overflow-y:auto;padding-bottom:2px;');
        rail.setAttribute('data-role', 'wp-palette-rail');
        wrap.appendChild(rail);
        const grid = _el('div', 'display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));' +
            'gap:4px;flex:1 1 auto;overflow-y:auto;padding:2px;min-height:120px;');
        grid.setAttribute('data-role', 'wp-palette-grid');
        wrap.appendChild(grid);
        const detailBox = _el('div', 'font-size:11px;color:var(--text-muted,#999);line-height:1.45;' +
            'border-top:1px solid var(--border,#333);padding-top:6px;min-height:50px;flex:0 0 auto;');
        detailBox.setAttribute('data-role', 'wp-palette-detail');
        wrap.appendChild(detailBox);

        const showDetail = (t: WpPaletteTile): void => {
            detailBox.textContent = '';
            detailBox.appendChild(_el('div', 'font-weight:600;color:var(--text,#ddd);', t.name));
            (GM().detailRows(layer, t.rec) as { label: string; value: string }[]).forEach((r) => {
                detailBox.appendChild(_el('div', null, r.label + ': ' + r.value));
            });
        };

        const build = (): void => {
            const filtered = GM().filterPalette(sections, state.paletteQuery) as WpPaletteSection[];
            // The rail is hidden while searching, because a match can land in *FIX*
            // category; the grid then shows every hit instead.
            rail.textContent = '';
            if (!state.paletteQuery && filtered.length) {
                if (!filtered.some((s) => s.id === state.paletteCategory)) {
                    state.paletteCategory = filtered[0].id;
                }
                filtered.forEach((s) => {
                    const active = s.id === state.paletteCategory;
                    const b = _btn(s.label, () => { state.paletteCategory = s.id; build(); },
                        'padding:2px 8px;font-size:11px;' +
                        (active ? 'background:#2d4a6b;color:#cfe;' : ''),
                        `${s.label} (${s.tiles.length})`);
                    b.setAttribute('data-role', 'wp-palette-cat');
                    b.setAttribute('data-cat', s.id);
                    rail.appendChild(b);
                });
            }
            const tiles = state.paletteQuery
                ? GM().flattenPalette(filtered) as WpPaletteTile[]
                : ((filtered.find((s) => s.id === state.paletteCategory) || filtered[0]) || { tiles: [] }).tiles;
            grid.textContent = '';
            tiles.forEach((t) => {
                const selected = t.id === state.value;
                const b = _el('button', 'display:flex;align-items:center;gap:6px;text-align:left;' +
                    'cursor:pointer;border:1px solid ' + (selected ? '#5a8fd0' : 'var(--border,#3a3a44)') +
                    ';border-radius:6px;padding:4px 6px;font-size:11px;' +
                    'background:' + (selected ? '#2d4a6b' : 'var(--bg-card,#2a2a32)') + ';color:var(--text,#ddd);');
                b.setAttribute('data-role', 'wp-palette-tile');
                b.setAttribute('data-id', t.id);
                const sw = _el('span', 'display:inline-block;width:12px;height:12px;border-radius:3px;' +
                    'border:1px solid #555;flex:0 0 auto;');
                sw.style.background = GM().layerColor(layer, t.id) || 'transparent';
                b.appendChild(sw);
                b.appendChild(_el('span', null, t.name));
                b.addEventListener('mouseenter', () => showDetail(t));
                b.addEventListener('focus', () => showDetail(t));
                b.addEventListener('click', (ev) => {
                    state.value = t.id;
                    _pushRecent(layer, state.value);
                    _saveScopePrefs();
                    // Drop focus so the next Space reaches the pan handler (bug-511).
                    (ev.currentTarget as HTMLElement).blur();
                    softRender();
                });
                grid.appendChild(b);
            });
            if (tiles.length) {
                showDetail(tiles.find((t) => t.id === state.value) || tiles[0]);
            } else {
                detailBox.textContent = 'No tile matches that search.';
            }
        };

        search.addEventListener('input', () => { state.paletteQuery = search.value; build(); });
        search.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape') {
                state.paletteOpen = false;
                _saveScopePrefs();
                softRender();
            }
        });
        build();
        return wrap;
    }

    /** Cancels (returns nothing) when the author backs out of the size warning. */
    function generate(): Promise<void> | void {
        const p = state.payload!;
        const est = GM().estimateCompile(p, state.merge);
        if (est.total > 3000 && !window.confirm(
            `This will create about ${est.areas} areas and ${est.ways} ways `
            + `(${est.total} nodes).\n\nThe graph view may become unresponsive. `
            + `Consider "merge same-biome", or generating smaller zones.\n\nContinue?`)) {
            return;
        }
        const body = { region_merge: !!state.merge };
        const run = async (allowRegenerate: boolean) => {
            try {
                const result = await _post(
                    `/${encodeURIComponent(p.scope.id)}/grid/generate`,
                    allowRegenerate ? { ...body, allow_regenerate: true } : body);
                state.payload = result;
                state.selectedChild = null;
                _notify(true);
                const r = result.report || {};
                const notes = (r.notes || []).join('; ');
                _status(`⚙ Generated ${r.node_count || 0} node(s), ` +
                    `${r.edge_count || 0} edge(s)` +
                    (notes ? ` — ${notes}` : ''), false);
            } catch (e) {
                if (!allowRegenerate && /already materialized/.test(errText(e))
                        && window.confirm(`${errText(e)}\n\nRe-run generation?`)) {
                    return run(true);
                }
                _status(`Generate failed: ${errText(e)}`, true);
            }
        };
        return run(false);
    }

    function ungenerate(): void {
        const p = state.payload;
        if (!p || !p.scope) return;
        if (!window.confirm(
                `Delete every generated node for “${p.scope.name}”?\n\n` +
                `The painted grid, reference and placements are kept, and the scope `
                + `returns to unmade so you can ⚙ Generate again.`)) {
            return;
        }
        (async () => {
            try {
                const result = await _post(
                    `/${encodeURIComponent(p.scope.id)}/grid/ungenerate`, {});
                state.payload = result;
                state.selectedChild = null;
                _notify(true);
                _status(`🧹 Removed ${result.deleted_nodes || 0} generated node(s) — grid kept.`, false);
            } catch (e) {
                _status(`Ungenerate failed: ${errText(e)}`, true);
            }
        })();
    }

    function _noGridPanel(p: WpPayload): HTMLElement {
        const box = _el('div', 'padding:14px;border:1px dashed var(--border,#555);' +
            'border-radius:8px;margin-bottom:10px;color:var(--text-muted,#999);',
            'This scope has no grid yet.');
        box.appendChild(_el('div', null, ' '));
        box.appendChild(_btn('▦ Create grid…', () => _openGridDialog(p)));
        return box;
    }

    function _featureBar(p: WpPayload): HTMLElement {
        const wrap = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;');
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'Feature:'));
        const sel = _el('select', 'padding:3px;border-radius:5px;min-width:160px;');
        sel.setAttribute('data-role', 'wp-feature');
        const none = _el('option', null, '— none (click a placed feature) —');
        none.value = '';
        sel.appendChild(none);
        (p.children || []).forEach((c) => {
            const opt = _el('option', null, `${c.name}${c.placed ? ' (placed)' : ''}`);
            opt.value = c.id;
            if (c.id === state.selectedChild) opt.selected = true;
            sel.appendChild(opt);
        });
        sel.addEventListener('change', () => { state.selectedChild = sel.value || null; render(); });
        wrap.appendChild(sel);

        if (state.selectedChild) {
            const child = (p.children || []).find((c) => c.id === state.selectedChild);
            wrap.appendChild(_btn('Open ▸', () => load(state.selectedChild!)));
            if (child && child.placed) {
                wrap.appendChild(_btn('🗑 Remove', () => removeFeature(state.selectedChild!)));
            }
            wrap.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                'Pick “Feature”, then click a cell to place/move.'));
        }
        return wrap;
    }

    /**
     * The place tool's picker (task-528/541): the areas that can go on a cell of
     * THIS map, grouped by scope. Only shown while the tool is active, so the
     * painter's default surface stays as it was.
     *
     * Grouping is the point: a flat list of every unplaced area in the world made
     * a child scope's interior look like it belonged on the world map.
     */
    function _areaBar(p: WpPayload): HTMLElement {
        const wrap = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;');
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'Area:'));
        const sel = _el('select', 'padding:3px;border-radius:5px;min-width:200px;');
        sel.setAttribute('data-role', 'wp-area');
        const none = _el('option', null, '— pick an area to place —');
        none.value = '';
        sel.appendChild(none);
        const groups = GM().areaGroups(p, state.selectedArea);
        groups.forEach((g: *FIX*) => {
            const og = _el('optgroup');
            og.label = g.key === 'elsewhere'
                ? `${g.label} — picking one moves it here`
                : g.label;
            g.areas.forEach((a: *FIX*) => {
                const where = a.placedHere ? ` (${a.placedHere.x},${a.placedHere.y})` : '';
                const opt = _el('option', null, a.name + where);
                opt.value = a.id;
                if (a.id === state.selectedArea) opt.selected = true;
                og.appendChild(opt);
            });
            sel.appendChild(og);
        });
        sel.addEventListener('change', () => {
            state.selectedArea = sel.value || null;
            render();
        });
        wrap.appendChild(sel);
        if (!groups.length) {
            wrap.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                `No areas available here — every area of “${p.scope.name}” already sits on a map.`));
        } else {
            wrap.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                'Then click a cell. Click a placed 📍 to take it off the map again.'));
        }
        // A 200x133 world draws cells about 5px wide, so the marker cannot carry
        // a name. The list is how you see what is where: name + cell, and picking
        // one lets you move it.
        const placedHere = (p.area_placements || []).filter(
            (a) => !groups.some((g: *FIX*) => g.areas.some((x: *FIX*) => x.id === a.id)));
        if (placedHere.length) {
            const list = _el('div', 'display:flex;flex-wrap:wrap;gap:6px;width:100%;margin-top:2px;');
            placedHere.forEach((a) => {
                const chip = _btn(`📍 ${a.name} (${a.x},${a.y})`, () => {
                    state.selectedArea = a.id;
                    render();
                }, 'font-size:11px;padding:1px 7px;border-radius:10px;' +
                    'border-color:#2f7d5a;color:#9fd8bd;', `Move "${a.name}" — click, then click a new cell`);
                list.appendChild(chip);
            });
            wrap.appendChild(list);
        }
        return wrap;
    }

    // ───────────────────── grid surface (Konva canvas) ────────────────────
    //
    // Konva draws the grid on a canvas as a fixed number of shapes (background
    // grid, paint, features, route) — a 160x100 world costs the same to render
    // as a 10x10, and work is proportional to *painted* cells, not grid area.
    // Pan/zoom and hit-testing are Konva's, so none of it is hand-rolled. The
    // same payload the DOM version used drives it, so the backend is unchanged.

    function _grid(p: WpPayload): HTMLElement {
        // `flex:1 1 auto; min-width:0` is load-bearing since the rail moved beside
        // the grid (task-536). This element used to be a child of the panel's
        // *column* flex box, where `align-items:stretch` gave it the full width for
        // free; as a flex item in a **row** it takes its content width instead, and
        // its only child is the absolutely-positioned holder, which contributes
        // nothing — so without this the wrapper collapsed to 0px, the 900px canvas
        // overflowed a zero-width box, and the grid simply did not appear.
        // `min-width:0` is the other half: a flex item's default `min-width:auto`
        // refuses to shrink below its content, which fights the zoom buttons.
        const wrap = _el('div',
            'flex:1 1 auto;min-width:0;min-height:240px;position:relative;'
            + 'border:1px solid var(--border,#3a3a44);'
            + 'border-radius:8px;background:#0d0d11;overflow:hidden;margin-bottom:10px;');
        wrap.setAttribute('data-role', 'wp-grid');
        const holder = _el('div', 'position:absolute;inset:0;');
        wrap.appendChild(holder);
        state.gridHolder = holder;
        state.stage = null;
        // Mount after the wrap is in the DOM so Konva can measure the container.
        requestAnimationFrame(() => _mountGrid(p));
        wrap.appendChild(_gridHud(p));
        return wrap;
    }

    function _gridHud(p: WpPayload): HTMLElement {
        const hud = _el('div', 'position:absolute;left:8px;top:8px;z-index:3;display:flex;' +
            'gap:6px;align-items:center;flex-wrap:wrap;background:rgba(13,17,23,0.85);' +
            'border:1px solid var(--border,#3a3a44);border-radius:6px;padding:4px 6px;' +
            'pointer-events:auto;');
        state.dimsBtn = null;
        // Keep references so the controls can reflect the clamp (task-595): at
        // the floor the − button is disabled rather than silently doing nothing.
        const zoomIn = _btn('＋', () => _zoomBy(p, 1.25), 'padding:1px 7px;');
        const zoomOut = _btn('−', () => _zoomBy(p, 0.8), 'padding:1px 7px;');
        state.zoomInBtn = zoomIn;
        state.zoomOutBtn = zoomOut;
        hud.appendChild(zoomIn);
        hud.appendChild(zoomOut);
        hud.appendChild(_btn('⤢ Fit', () => _fitGrid(p), 'padding:1px 7px;'));
        _syncZoomButtons();   // a rebuild starts at the current scale
        // task-717: the dims readout is also the exact-size control — clicking it
        // opens the ▦ Grid… dialog, so precise resize is discoverable from the
        // canvas instead of only from the toolbar.
        // task-597: the count is the *output* here, with the cell size beside it.
        // The author measures cells against the reference art, so "1 cell ≈ 77px"
        // is the number that means something; the count follows from it.
        const pxCell = (state.refImage && state.refImage.naturalWidth)
            ? GM().cellSizeForGrid(state.refImage.naturalWidth, p.grid!.w) : null;
        const dimsBtn = _btn(`${p.grid!.w}×${p.grid!.h} · 1 cell = 1 turn`
            + (pxCell ? ` ≈ ${Math.round(pxCell)}px` : ''),
            () => _openGridDialog(p),
            'font-size:11px;color:var(--text-muted,#999);padding:2px 6px;',
            'Set the exact grid size…');
        state.dimsBtn = dimsBtn;
        hud.appendChild(dimsBtn);
        // The scope's reference (map) image — pick an uploaded background, or
        // upload/point at one. Its `appendChild` was dropped in 0dc60c48, which
        // left `_referenceControl` orphaned and the picker gone from the HUD.
        hud.appendChild(_referenceControl(p));
        // Painted-cell transparency: lets the reference art show through.
        const alpha = _el('input', 'width:64px;');
        alpha.type = 'range';
        alpha.min = '0.15';
        alpha.max = '1';
        alpha.step = '0.05';
        alpha.value = String(state.paintAlpha);
        alpha.setAttribute('data-role', 'wp-alpha');
        alpha.addEventListener('input', () => {
            state.paintAlpha = parseFloat(alpha.value);
            _redrawGrid();
        });
        hud.appendChild(alpha);
        // What the cell under the pointer holds (task-540). A marker on a 200x133
        // world is ~5px and carries no name, so this is the only way to tell a
        // painted cell from a placed area while moving the mouse.
        const readout = _el('span', 'font-size:11px;color:#9ab;margin-left:6px;' +
            'max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;');
        readout.setAttribute('data-role', 'wp-cellinfo');
        readout.textContent = 'hover a cell to read it';
        state.cellInfoEl = readout;
        hud.appendChild(readout);
        if (state.tool === 'route') {
            const info = _el('span', 'font-size:11px;color:#7ab;margin-left:6px;');
            info.setAttribute('data-role', 'wp-route-info');
            info.textContent = _routeLabel();
            state.routeInfoEl = info;
            hud.appendChild(info);
            hud.appendChild(_btn('✓ Paint route', () => applyRoute(), 'outline:1px solid #7ab;'));
            hud.appendChild(_btn('✕ Clear', () => { state.route = []; render(); }));
        }
        return hud;
    }

    function _referenceControl(p: WpPayload): HTMLElement {
        const wrap = _el('span', 'display:flex;align-items:center;gap:4px;');
        const ref = p.reference || {};
        const sel = _el('select', 'padding:2px;border-radius:5px;max-width:190px;font-size:11px;');
        sel.setAttribute('data-role', 'wp-bg-select');
        const none = _el('option', null, '🗺 reference…');
        none.value = '';
        sel.appendChild(none);
        const known = (state.backgrounds || []).slice();
        if (ref.image && known.indexOf(ref.image) < 0) known.unshift(ref.image);
        known.forEach((url) => {
            const opt = _el('option', null, url.split('/').pop());
            opt.value = url;
            sel.appendChild(opt);
        });
        sel.value = ref.image || '';
        sel.addEventListener('change', () => updateReference({ image: sel.value || null }));
        wrap.appendChild(sel);

        // The picker only lists images already on the server. A new one has to be
        // uploaded into static/images/backgrounds (the same endpoint the graph
        // background uses), or referenced by URL — so offer both here instead of
        // making the author drop the file in by hand.
        const uploadInput = _el('input');
        uploadInput.type = 'file';
        uploadInput.accept = 'image/*';
        uploadInput.style.display = 'none';
        uploadInput.setAttribute('data-role', 'wp-bg-upload');
        uploadInput.addEventListener('change', async () => {
            const file = uploadInput.files && uploadInput.files[0];
            if (!file) return;
            try {
                // ApiClient's declared answer shape only carries `image`; the route also
                // answers `{error}` on a rejected upload, which is what this
                // checks first.
                const res = await ApiClient.uploadBackgroundImage(file) as
                    (Awaited<ReturnType<typeof ApiClient.uploadBackgroundImage>> & { error?: string }) | null;
                if (!res || res.error) throw new Error((res && res.error) || 'upload failed');
                state.backgrounds = null;          // refresh the picker list
                await ensureBackgrounds();
                await updateReference({ image: res.image });
                _status(`Reference: ${String(res.image).split('/').pop()}.`, false);
            } catch (e) {
                _status(`Upload failed: ${errText(e)}`, true);
            } finally {
                uploadInput.value = '';
            }
        });
        wrap.appendChild(uploadInput);
        const uploadBtn = _btn('⬆', () => uploadInput.click(), 'padding:1px 6px;');
        uploadBtn.title = 'Upload an image into static/images/backgrounds';
        wrap.appendChild(uploadBtn);
        const urlBtn = _btn('🔗', () => {
            const url = window.prompt(
                'Reference image URL (/static/…, https://… or data:):', ref.image || '');
            if (url !== null) updateReference({ image: url.trim() || null });
        }, 'padding:1px 6px;');
        urlBtn.title = 'Use an image by URL';
        wrap.appendChild(urlBtn);

        if (ref.image) {
            wrap.appendChild(_btn(ref.visible ? '👁' : '🚫', () =>
                updateReference({ visible: !ref.visible }), 'padding:1px 6px;'));
            const op = _el('input', 'width:64px;');
            op.type = 'range';
            op.min = '0';
            op.max = '1';
            op.step = '0.05';
            op.value = String(ref.opacity == null ? 0.5 : ref.opacity);
            op.setAttribute('data-role', 'wp-bg-opacity');
            op.addEventListener('change', () =>
                updateReference({ opacity: parseFloat(op.value) }));
            wrap.appendChild(op);
            // One click: make the grid the image's aspect, so painted cells and
            // the reference share geometry instead of fighting at different ratios.
            wrap.appendChild(_help(_btn('▦ match', () => _gridFromReference(p),
                'padding:1px 6px;font-size:11px;'), 'wp-reference')!);
            // Move/resize/crop the picture (task-524). The rect is stored in cell
            // units, so the graph map layout draws the same geometry.
            const adjustBtn = _btn(state.refEdit ? '✔ adjust' : '✥ adjust', () => {
                state.refEdit = !state.refEdit;
                state.refDrag = null;
                render();
                _status(state.refEdit
                    ? 'Reference: drag to move · corners resize · edges crop.'
                    : 'Reference adjust off.', false);
            }, 'padding:1px 6px;font-size:11px;');
            adjustBtn.title = 'Move, resize and crop the reference image';
            _help(wrap.appendChild(adjustBtn), 'wp-reference-adjust');
            const resetBtn = _btn('⤢ reset', () => updateReference({ reset: true }),
                'padding:1px 6px;font-size:11px;');
            resetBtn.title = 'Fit the whole image to the grid again (clears move/resize/crop)';
            wrap.appendChild(resetBtn);
        }
        return wrap;
    }

    /**
     * Rescale a stored reference rect (in cell units) proportionally when the
     * grid extent changes from `oldGrid` to `newGrid`, so a custom-positioned
     * or cropped background image stays aligned with the grid borders.
     */
    function _scaleRefRect(rect: WpRect, oldGrid: { w: number; h: number },
        newGrid: { w: number; h: number }): WpRect {
        const sx = (oldGrid.w > 0 && newGrid.w > 0) ? (newGrid.w / oldGrid.w) : 1;
        const sy = (oldGrid.h > 0 && newGrid.h > 0) ? (newGrid.h / oldGrid.h) : 1;
        return {
            x: rect.x * sx,
            y: rect.y * sy,
            w: rect.w * sx,
            h: rect.h * sy,
        };
    }

    /**
     * Adjust `state.stage` (and `state.view`) so the reference image rect
     * occupies the exact same screen-space box as `beforeScreen`.
     *
     * When the author drags the cell `(0,0)` corner handle, the grid cell count
     * (`w*h`) changes while `CELL` (22 stage units) stays constant. Without
     * counter-scaling the stage camera, changing `w` from 20 to 80 makes the stage
     * 4x larger on screen. Anchoring the screen rect of the reference image keeps
     * the background art fixed in the viewport while the grid cells visibly grow
     * or shrink inside its borders.
     */
    function _anchorStageToRefScreen(
        beforeScreen: { x: number; y: number; w: number; h: number } | null,
        afterCells: WpRect,
    ): void {
        const stage = state.stage;
        if (!stage || !beforeScreen || beforeScreen.w <= 0 || beforeScreen.h <= 0
                || afterCells.w <= 0 || afterCells.h <= 0) return;
        const scaleW = beforeScreen.w / (afterCells.w * CELL);
        const scaleH = beforeScreen.h / (afterCells.h * CELL);
        const nextScale = Math.max(0.05, Math.min(MAX_SCALE, Math.max(scaleW, scaleH)));
        const cx = beforeScreen.x + beforeScreen.w / 2;
        const cy = beforeScreen.y + beforeScreen.h / 2;
        const nextX = cx - (afterCells.x + afterCells.w / 2) * CELL * nextScale;
        const nextY = cy - (afterCells.y + afterCells.h / 2) * CELL * nextScale;
        stage.scale({ x: nextScale, y: nextScale });
        stage.position({ x: nextX, y: nextY });
        _captureView();
        _syncZoomButtons();
    }

    function _refScreenBox(p: WpPayload, extOverride?: { w: number; h: number }):
        { x: number; y: number; w: number; h: number } | null {
        const stage = state.stage;
        if (!stage) return null;
        const rect = _refRectCells(p, state.refImage, extOverride);
        const scale = stage.scaleX() || 1;
        return {
            x: stage.x() + rect.x * CELL * scale,
            y: stage.y() + rect.y * CELL * scale,
            w: rect.w * CELL * scale,
            h: rect.h * CELL * scale,
        };
    }

    /**
     * Make the grid the image's aspect ratio (the `▦ match` button).
     *
     * The painter fits the image *into* the grid, so a grid with a different
     * ratio leaves empty bands and the painted cells and the art disagree about
     * where a place is. A shrink **prunes** out-of-bounds paint and placements
     * server-side (`world_grid.ensure_grid`), so the count is shown and confirmed
     * first — losing a hand-placed area to a one-click convenience is not a trade
     * worth making silently.
     */
    async function _gridFromReference(p: WpPayload): Promise<void> {
        const img = state.refImage;
        if (!img || !img.naturalWidth) { _status('Load a reference image first.'); return; }
        const next = GM().gridForImageAspect(p.grid && p.grid.w, img.naturalWidth, img.naturalHeight);
        if (!next) { _status('That image has no readable size — try another file.', true); return; }
        const stranded = GM().strandedCount(p, next.w, next.h);
        if (stranded > 0) {
            const go = window.confirm(
                `Match the grid to the image (${img.naturalWidth}×${img.naturalHeight})?\n\n`
                + `The grid becomes ${next.w}×${next.h} cells, and ${stranded} painted cell(s) or `
                + `placement(s) currently outside it will be removed. This can be undone.`);
            if (!go) return;
        }
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid`,
                { w: next.w, h: next.h, mode: p.mode });
            state.view = null;   // refit to the new aspect
            _status(`Grid set to ${next.w}×${next.h} (image aspect ${img.naturalWidth}×${img.naturalHeight})`
                + (stranded ? `, ${stranded} out-of-bounds cell(s) removed` : '') + '.', false);
        } catch (e) {
            _status(`Grid failed: ${errText(e)}`, true);
        }
    }

    async function updateReference(patch: WpReferencePatch): Promise<void> {
        const p = state.payload!;
        const ref = p.reference || {};
        const body: Record<string, unknown> = {
            image: ref.image || null,
            opacity: ref.opacity,
            visible: ref.visible,
            ...patch,
        };
        if (body.image == null) body.opacity = undefined;   // cleared
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/reference`, body);
            render();
        } catch (e) {
            _status(`Reference failed: ${errText(e)}`, true);
        }
    }

    function _routeLabel(): string {
        const stats = GM().routeStats(GM().routeCells(state.route || []).length);
        return `route: ${stats.label}`;
    }

    function _mountGrid(p: WpPayload): void {
        const K = _konva();
        if (!K || !state.gridHolder) return;
        const holder = state.gridHolder;
        const stage = new K.Stage({
            container: holder,
            width: holder.clientWidth || 900,
            height: holder.clientHeight || 480,
        });
        // The panel fills the viewport, so the canvas has to follow a window
        // resize instead of keeping its mount size — Konva sizes a stage once
        // and never tracks its container.
        const hadViewOnMount = Boolean(state.view);
        let fittedRealSize = holder.clientWidth > 0 && holder.clientHeight > 0;
        if (state.resizeObs) state.resizeObs.disconnect();
        state.resizeObs = null;
        if (typeof ResizeObserver !== 'undefined') {
            const ro = new ResizeObserver(() => {
                stage.width(holder.clientWidth || 900);
                stage.height(holder.clientHeight || 480);
                if (!fittedRealSize && holder.clientWidth > 0 && holder.clientHeight > 0) {
                    fittedRealSize = true;
                    if (!hadViewOnMount && !state.cellSizePreview && !state.gridDrag) {
                        _fitGrid(p);
                        return;
                    }
                }
                stage.batchDraw();
            });
            ro.observe(holder);
            state.resizeObs = ro;
        }
        const shape = (draw: (ctx: CanvasRenderingContext2D) => void): WpKonvaNode =>
            new K.Shape({ listening: false, sceneFunc: draw });
        const bgShape = shape((ctx) => _drawGridLines(ctx, p));
        const paintShape = shape((ctx) => _drawPaint(ctx, p));
        const featureShape = shape((ctx) => _drawFeatures(ctx, p));
        const routeShape = shape((ctx) => _drawRoute(ctx));
        const refShape = shape((ctx) => _drawRefHandles(ctx, p));
        const gridHandleShape = shape((ctx) => _drawGridHandles(ctx, p));
        const refLayer = new K.Layer({ listening: false });
        const bg = new K.Layer({ listening: false });
        const paint = new K.Layer({ listening: false });
        const decor = new K.Layer({ listening: false });
        // Reference image sits under the grid lines, fitted to the grid without
        // distortion, so the art lines up with the same geometry you paint.
        const refNode = new K.Image({
            x: 0,
            y: 0,
            width: p.grid!.w * CELL,
            height: p.grid!.h * CELL,
            opacity: (p.reference && p.reference.opacity != null) ? p.reference.opacity : 0.5,
            visible: !!(p.reference && p.reference.visible),
            listening: false,
        });
        state.refNode = refNode;
        const refImg = _ensureRefImage(p);
        if (refImg && refImg.complete && refImg.naturalWidth) {
            refNode.image(refImg);
            _applyRefTransform(p);
        }
        refLayer.add(refNode);
        bg.add(bgShape);
        paint.add(paintShape);
        decor.add(featureShape);
        decor.add(routeShape);
        decor.add(refShape);
        decor.add(gridHandleShape);
        stage.add(refLayer);
        stage.add(bg);
        stage.add(paint);
        stage.add(decor);
        // The selection sits above the cells and below nothing else that matters:
        // it has to be visible while the author drags a marquee over painted
        // ground, and it is rebuilt on every redraw rather than added to the decor
        // batch (which is rebuilt too, but one shape type at a time).
        const select = new K.Layer({ listening: false });
        stage.add(select);
        state.stage = stage;
        state.layers = { ref: refLayer, bg, paint, decor, select };
        state.shapes = { bgShape, paintShape, featureShape, routeShape };
        _wireGrid(p);
        if (state.view) {
            // Rebuild (paint/layer change) keeps the author's place on the map.
            stage.scale({ x: state.view.scale, y: state.view.scale });
            stage.position({ x: state.view.x || 0, y: state.view.y || 0 });
            _syncZoomButtons();
            _redrawGrid();
        } else {
            _fitGrid(p);
        }
    }

    function _captureView(): void {
        const stage = state.stage;
        if (stage) {
            state.view = { x: stage.x(), y: stage.y(), scale: stage.scaleX() };
            _saveScopePrefs();
        }
    }

    function _redrawGrid(): void {
        if (state.stage) state.stage.batchDraw();
        // The reference image decodes after the HUD is built, so the dims button
        // learns the image's real pixel size here rather than on a full re-render.
        if (state.dimsBtn && state.payload && state.payload.grid && !state.cellSizePreview) {
            const iw = (state.refImage && state.refImage.naturalWidth) || 0;
            const px = iw > 0 ? GM().cellSizeForGrid(iw, state.payload.grid.w) : null;
            state.dimsBtn.textContent = `${state.payload.grid.w}×${state.payload.grid.h} · 1 cell = 1 turn`
                + (px ? ` ≈ ${Math.round(px)}px` : '');
        }
    }

    /**
     * Redraw only the decor + selection layers (in-progress paint stroke, feature
     * markers, route waypoints, cell selection). A paint *drag* changes nothing
     * else: the ref/bg/paint layers keep their canvases and the stage transform is
     * unchanged until mouse-up. Calling ``stage.batchDraw()`` on every painted cell
     * re-rasterised the reference image each frame, which made painting crawl once
     * a large reference (deep_forest) was loaded.
     */
    function _redrawDecor(): void {
        const layers = state.layers;
        if (layers && layers.decor) layers.decor.batchDraw();
        else _redrawGrid();
        _drawSelection(state.payload, layers && layers.select);
        if (layers && layers.select) layers.select.batchDraw();
    }

    function _drawSelection(p: WpPayload | null, layer: WpKonvaNode | null): void {
        const K = _konva();
        if (!p || !layer || !K) return;
        layer.destroyChildren();
        const sel = _sel(p);
        const keys = Object.keys(sel);
        keys.forEach((k) => {
            const c = GM().parseCellKey(k);
            if (!c) return;
            layer.add(new K.Rect({
                x: c.x * CELL + 1, y: c.y * CELL + 1,
                width: CELL - 2, height: CELL - 2,
                fill: 'rgba(122,170,255,0.22)', stroke: '#7abff', strokeWidth: 1,
                listening: false,
            }));
        });
        if (state.marquee) {
            const a = state.marquee.anchor;
            const b = state.marquee.to;
            layer.add(new K.Rect({
                x: Math.min(a.x, b.x) * CELL,
                y: Math.min(a.y, b.y) * CELL,
                width: (Math.abs(b.x - a.x) + 1) * CELL,
                height: (Math.abs(b.y - a.y) + 1) * CELL,
                fill: 'rgba(122,170,255,0.14)', stroke: '#7ab', strokeWidth: 1,
                dash: [4, 3], listening: false,
            }));
        }
    }

    function _ensureRefImage(p: WpPayload): WpTrackedImage | null {
        const ref = p.reference;
        if (!ref || !ref.image) { state.refImage = null; return null; }
        if (state.refImage && state.refImage.__src === ref.image) return state.refImage;
        const img = new window.Image() as WpTrackedImage;
        img.__src = ref.image;
        img.onload = () => {
            state.refImage = img;
            if (state.refNode && state.payload) {
                state.refNode.image(img);
                _applyRefTransform(state.payload);
                _redrawGrid();
            }
        };
        img.onerror = () => { state.refImage = null; };
        img.src = ref.image;
        return img;
    }

    /** Fit the reference into the grid bounds, preserving its aspect ratio. */
    /**
     * The reference's destination rect in **cell** units. A stored rect (the
     * author's move/resize) wins; otherwise fit the whole image into the grid,
     * preserving aspect ratio and centring it. Cell units (not px) so the graph
     * map layout can draw the same picture at its own spacing (task-524).
     *
     * During a `px / cell` preview or grid resize drag (`_gridExtent(p)`), the
     * reference rect scales with the candidate extent so the background image and
     * the grid stay bounded together instead of the lattice detaching from the art.
     */
    function _refRectCells(p: WpPayload, img: WpTrackedImage | null,
        extOverride?: { w: number; h: number; pxPerCell?: number }): WpRect {
        const savedGrid = p.grid || { w: 1, h: 1 };
        const preview = extOverride || state.cellSizePreview;
        const ext = preview || savedGrid;
        const stored = (p.reference || {}).rect;
        const iw = (img && img.naturalWidth) || ext.w || 1;
        const ih = (img && img.naturalHeight) || ext.h || 1;
        if (preview && preview.pxPerCell && preview.pxPerCell > 0 && iw > 1 && ih > 1) {
            return { x: 0, y: 0, w: iw / preview.pxPerCell, h: ih / preview.pxPerCell };
        }
        if (stored && typeof stored.x === 'number' && typeof stored.y === 'number'
                && typeof stored.w === 'number' && typeof stored.h === 'number'
                && stored.w > 0 && stored.h > 0) {
            if (ext.w !== savedGrid.w || ext.h !== savedGrid.h) {
                return _scaleRefRect(stored, savedGrid, ext);
            }
            return { x: stored.x, y: stored.y, w: stored.w, h: stored.h };
        }
        const gw = ext.w || 0;
        const gh = ext.h || 0;
        return GM().fitReferenceRect(gw, gh, iw, ih);
    }

    /** Draw the reference into its rect (px) with the stored crop window. */
    function _applyRefTransform(p: WpPayload): void {
        const node = state.refNode;
        if (!node) return;
        const img = state.refImage;
        const rect = _refRectCells(p, img);
        node.x(rect.x * CELL);
        node.y(rect.y * CELL);
        node.width(rect.w * CELL);
        node.height(rect.h * CELL);
        const iw = (img && img.naturalWidth) || 0;
        const ih = (img && img.naturalHeight) || 0;
        if (!iw || !ih) return;
        const crop = (p.reference || {}).crop;
        node.crop(crop && crop.w
            ? { x: crop.x! * iw, y: crop.y! * ih, width: crop.w * iw, height: crop.h! * ih }
            : { x: 0, y: 0, width: iw, height: ih });
    }

    /** Handle anchor points (cell units): corners resize, edges crop. */
    function _refHandlePoints(rect: WpRect): Record<string, WpCell> {
        return GM().referenceHandlePoints(rect);
    }

    function _drawRefHandles(ctx: CanvasRenderingContext2D, p: WpPayload): void {
        if (!state.refEdit || !state.refImage || !(p.reference && p.reference.image)) return;
        const rect = _refRectCells(p, state.refImage);
        const scale = (state.stage && state.stage.scaleX()) || 1;
        ctx.save();
        ctx.strokeStyle = '#58a6ff';
        ctx.lineWidth = 1.5 / scale;
        ctx.setLineDash([6 / scale, 4 / scale]);
        ctx.strokeRect(rect.x * CELL, rect.y * CELL, rect.w * CELL, rect.h * CELL);
        ctx.setLineDash([]);
        const pts = _refHandlePoints(rect);
        Object.keys(pts).forEach((key) => {
            ctx.beginPath();
            ctx.arc(pts[key].x * CELL, pts[key].y * CELL, 5 / scale, 0, Math.PI * 2);
            ctx.fillStyle = key.length === 2 ? '#58a6ff' : '#e3b341';   // corners vs edges
            ctx.fill();
        });
        ctx.restore();
    }

    /** What a pointer press grabs on the reference: a handle or the body. */
    function _refHit(p: WpPayload, pos: WpCell): { kind: string; key: string | null } | null {
        const rect = _refRectCells(p, state.refImage);
        const scale = (state.stage && state.stage.scaleX()) || 1;
        const tol = 9 / scale;
        const pts = _refHandlePoints(rect);
        for (const key of Object.keys(pts)) {
            if (Math.abs(pos.x - pts[key].x * CELL) <= tol
                    && Math.abs(pos.y - pts[key].y * CELL) <= tol) {
                return { kind: key.length === 2 ? 'resize' : 'crop', key };
            }
        }
        const x = rect.x * CELL, y = rect.y * CELL, w = rect.w * CELL, h = rect.h * CELL;
        if (pos.x >= x && pos.x <= x + w && pos.y >= y && pos.y <= y + h) {
            return { kind: 'move', key: null };
        }
        return null;
    }

    function _refMouseDown(p: WpPayload): void {
        if (!state.refImage || !(p.reference && p.reference.image)) return;
        const pos = state.stage!.getRelativePointerPosition();
        if (!pos) return;
        const target = _refHit(p, pos);
        if (!target) return;
        state.refDrag = {
            kind: target.kind,
            key: target.key,
            start: { x: pos.x / CELL, y: pos.y / CELL },
            rect: _refRectCells(p, state.refImage),
            crop: Object.assign({ x: 0, y: 0, w: 1, h: 1 }, (p.reference || {}).crop || {}),
        };
    }

    function _refMouseMove(p: WpPayload): void {
        const drag = state.refDrag;
        if (!drag) return;
        const pos = state.stage!.getRelativePointerPosition();
        if (!pos) return;
        const cx = pos.x / CELL;
        const cy = pos.y / CELL;
        let r: WpRect = Object.assign({}, drag.rect);
        let crop: Partial<WpRect> = Object.assign({}, drag.crop);
        if (drag.kind === 'move') {
            r.x = drag.rect.x + (cx - drag.start.x);
            r.y = drag.rect.y + (cy - drag.start.y);
        } else {
            // Pure geometry lives in grid-model (unit-tested): corners resize,
            // edges crop.
            const next = GM().referenceHandleDrag(drag.rect, drag.crop, drag.key, cx, cy);
            r = next.rect;
            crop = next.crop;
        }
        state.refDrag!.rect = r;
        state.refDrag!.crop = crop;
        // Live preview without a round-trip; persisted on mouse-up.
        p.reference = Object.assign({}, p.reference, { rect: r, crop });
        _applyRefTransform(p);
        _redrawGrid();
    }

    function _refMouseUp(): void {
        const drag = state.refDrag;
        if (!drag) return;
        state.refDrag = null;
        const p = state.payload;
        if (!p || !(p.reference && p.reference.image)) return;
        updateReference({ rect: drag.rect, crop: drag.crop });
    }

    // ───────────────── grid frame adjust (task-597) ───────────────

    /**
     * The grid size to *draw*, which is the in-progress drag size while a resize is
     * running and the saved size otherwise.
     *
     * The drawing reads the payload, and a resize drag only updates
     * `state.gridDrag` - so without this the frame and its handles were redrawn at
     * the *old* extent and the drag showed nothing but the size label ticking over.
     *
     * A `px / cell` preview (task-597) takes the same path: the slider is a resize
     * the author has not committed yet, so it must look exactly like one.
     */
    function _gridExtent(p: WpPayload): { w: number; h: number } {
        const drag = state.gridDrag;
        if (drag && drag.kind === 'resize' && drag.w && drag.h) {
            return { w: drag.w, h: drag.h };
        }
        const preview = state.cellSizePreview;
        if (preview) return { w: preview.w, h: preview.h };
        return { w: p.grid!.w, h: p.grid!.h };
    }

    /**
     * Where the draggable cell-size corner handle sits on the canvas (in cell units).
     * Placed at the bottom-right corner of the top-left cell of the reference image
     * (`(rect.x + 1, rect.y + 1)`), so the author can grab the corner of that cell,
     * drag it smaller or larger over the background art, and release to snap to the
     * closest `{w, h}` grid (task-597).
     */
    function _cellCornerHandlePoint(p: WpPayload): WpCell | null {
        if (!state.refImage || !state.refImage.naturalWidth || !(p.reference && p.reference.image)) {
            return null;
        }
        if (p.scope.state === 'materialized') return null;
        const rect = _refRectCells(p, state.refImage);
        return { x: rect.x + 1, y: rect.y + 1 };
    }

    /** Resize handles on the grid frame; only meaningful in adjust mode. */
    function _drawGridHandles(ctx: CanvasRenderingContext2D, p: WpPayload): void {
        if (!state.gridEdit) return;
        const scale = (state.stage && state.stage.scaleX()) || 1;
        const ext = _gridExtent(p);
        const pts = GM().gridHandlePoints(ext.w, ext.h);
        ctx.save();
        Object.keys(pts).forEach((key) => {
            ctx.beginPath();
            ctx.arc(pts[key].x * CELL, pts[key].y * CELL, 6 / scale, 0, Math.PI * 2);
            // Corner (two letters) is the both-axes handle; edges are one axis.
            ctx.fillStyle = key.length === 2 ? '#e3b341' : '#58a6ff';
            ctx.fill();
        });
        // Cell-size corner handle on cell (0,0) of the reference image (task-597):
        // highlights the first cell and puts a green diamond/circle at its corner
        // so you can grab the cell corner itself and shrink/grow all cells inside
        // the background image borders.
        const cellCorner = _cellCornerHandlePoint(p);
        if (cellCorner) {
            const rx = (cellCorner.x - 1) * CELL;
            const ry = (cellCorner.y - 1) * CELL;
            ctx.strokeStyle = '#3fb950';
            ctx.lineWidth = 1.75 / scale;
            ctx.setLineDash([4 / scale, 3 / scale]);
            ctx.strokeRect(rx, ry, CELL, CELL);
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.arc(cellCorner.x * CELL, cellCorner.y * CELL, 6.5 / scale, 0, Math.PI * 2);
            ctx.fillStyle = '#3fb950';
            ctx.fill();
            ctx.strokeStyle = '#0d1117';
            ctx.lineWidth = 1.5 / scale;
            ctx.stroke();
        }
        const drag = state.gridDrag;
        if (drag && drag.kind === 'move') {
            const off = drag.offset;
            ctx.fillStyle = '#e3b341';
            ctx.font = `${12 / scale}px sans-serif`;
            ctx.fillText(`offset ${off.x.toFixed(1)}, ${off.y.toFixed(1)}`, 8 / scale, (ext.h * CELL) + 14 / scale);
        } else if (drag && drag.kind === 'cell-size' && state.cellSizePreview) {
            const pr = state.cellSizePreview;
            ctx.fillStyle = '#3fb950';
            ctx.font = `${12 / scale}px sans-serif`;
            ctx.fillText(`1 cell ≈ ${Math.round(pr.pxPerCell)}px -> snaps to ${pr.w}×${pr.h}`,
                8 / scale, (ext.h * CELL) + 14 / scale);
        } else if (drag && drag.w && drag.h) {
            ctx.fillStyle = '#e3b341';
            ctx.font = `${12 / scale}px sans-serif`;
            ctx.fillText(`${drag.w}×${drag.h}`, 8 / scale, (ext.h * CELL) + 14 / scale);
        }
        ctx.restore();
    }

    /** What a pointer press grabs in grid-adjust mode: a cell corner, a frame handle, or the frame. */
    function _gridHit(p: WpPayload, pos: WpCell): { kind: string; key: string | null } | null {
        const scale = (state.stage && state.stage.scaleX()) || 1;
        const tol = 10 / scale;
        const cellCorner = _cellCornerHandlePoint(p);
        if (cellCorner && Math.abs(pos.x - cellCorner.x * CELL) <= tol
                && Math.abs(pos.y - cellCorner.y * CELL) <= tol) {
            return { kind: 'cell-size', key: 'cell' };
        }
        const pts = GM().gridHandlePoints(p.grid!.w, p.grid!.h);
        for (const key of Object.keys(pts)) {
            if (Math.abs(pos.x - pts[key].x * CELL) <= tol
                    && Math.abs(pos.y - pts[key].y * CELL) <= tol) {
                return { kind: 'resize', key };
            }
        }
        const w = p.grid!.w * CELL;
        const h = p.grid!.h * CELL;
        if (pos.x >= 0 && pos.x <= w && pos.y >= 0 && pos.y <= h) {
            return { kind: 'move', key: null };
        }
        return null;
    }

    /** Konva's `evt` is typed as a partial event, so the pointer coordinates are
     *  read defensively rather than asserted as a MouseEvent. */
    function _gridMouseDown(p: WpPayload, ev?: unknown): void {
        const raw = (ev || {}) as { clientX?: number; clientY?: number };
        const pos = state.stage!.getRelativePointerPosition();
        if (!pos) return;
        const target = _gridHit(p, pos);
        if (!target) return;
        const anchorScreen = target.kind === 'cell-size' ? _refScreenBox(p, p.grid) : null;
        const imgW = (state.refImage && state.refImage.naturalWidth) || 0;
        const startPx = (target.kind === 'cell-size' && imgW > 0)
            ? (GM().cellSizeForGrid(imgW, p.grid!.w) || 32)
            : null;
        state.gridDrag = {
            kind: target.kind,
            key: target.key,
            start: { x: pos.x / CELL, y: pos.y / CELL },
            clientX: typeof raw.clientX === 'number' ? raw.clientX : 0,
            clientY: typeof raw.clientY === 'number' ? raw.clientY : 0,
            w: p.grid!.w,
            h: p.grid!.h,
            offset: Object.assign({ x: 0, y: 0 }, p.map_offset || {}),
            anchorScreen,
            pxPerCell: startPx,
        };
        _gridDragWatch(p);
    }

    /**
     * Track the drag on the document, not the stage.
     *
     * Konva's stage `mousemove` only fires while the pointer is over the canvas,
     * and its `mouseleave` *committed* the resize - so dragging a handle outward
     * ended the drag the instant it left the frame, and growing the grid took a
     * series of separate drags. Listening on the document also lets the pointer
     * travel beyond the frame, which is what dragging an edge handle implies.
     */
    function _gridDragWatch(p: WpPayload): void {
        _gridDragRelease();
        const onMove = (ev: MouseEvent): void => {
            if (!state.gridDrag) return;
            if (ev.cancelable) ev.preventDefault();
            if (state.gridDrag.kind === 'cell-size') {
                _gridDragCellCornerScreen(p, ev.clientX, ev.clientY);
                return;
            }
            const cell = _gridPointerCell(ev.clientX, ev.clientY);
            if (cell) _gridDragTo(p, cell.x, cell.y);
        };
        const onUp = (): void => {
            _gridDragRelease();
            _gridMouseUp(p);
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        state.gridDragRelease = function () {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }

    function _gridDragRelease(): void {
        if (state.gridDragRelease) {
            state.gridDragRelease();
            state.gridDragRelease = null;
        }
    }

    /**
     * Dragging the cell `(0,0)` corner handle in screen coordinates:
     * measures the pointer distance from the top-left corner of the fixed
     * reference image on screen, converts that directly into `pxPerCell` in
     * reference-image pixels, and updates `state.cellSizePreview` so all cells
     * grow or shrink continuously under the cursor inside the background image!
     */
    function _gridDragCellCornerScreen(p: WpPayload, clientX: number, clientY: number): void {
        const drag = state.gridDrag;
        const stage = state.stage;
        const img = state.refImage;
        if (!drag || !stage || !img || !img.naturalWidth || !drag.anchorScreen) return;
        const holderRect = state.gridHolder ? state.gridHolder.getBoundingClientRect() : null;
        if (!holderRect) return;
        const sx = clientX - holderRect.left - drag.anchorScreen.x;
        const sy = clientY - holderRect.top - drag.anchorScreen.y;
        // Take the larger axis from the cell's top-left origin so dragging
        // diagonally, horizontally, or vertically feels natural.
        const screenCellPx = Math.max(4, Math.max(sx, sy));
        const imgPxPerScreenPx = img.naturalWidth / Math.max(1, drag.anchorScreen.w);
        const range = GM().cellSizeRange(img.naturalWidth, img.naturalHeight);
        if (!range) return;
        const px = Math.min(range.max, Math.max(range.min,
            Math.round(screenCellPx * imgPxPerScreenPx)));
        const next = GM().gridForCellSize(img.naturalWidth, img.naturalHeight, px);
        if (!next) return;
        drag.w = next.w;
        drag.h = next.h;
        drag.pxPerCell = px;
        state.cellSizePreview = { w: next.w, h: next.h, pxPerCell: px };
        _applyRefTransform(p);
        const afterCells = _refRectCells(p, img, state.cellSizePreview);
        _anchorStageToRefScreen(drag.anchorScreen, afterCells);
        if (state.dimsBtn) {
            state.dimsBtn.textContent = `${next.w}×${next.h} · 1 cell = 1 turn ≈ ${px}px`;
        }
        if (state.stage) state.stage.batchDraw();
    }

    /**
     * Where the pointer is in cell units, as a delta from where the drag began.
     *
     * `getRelativePointerPosition()` would go stale the moment the pointer left
     * the canvas, which is the whole point of listening on the document. A drag
     * is relative *FIX*way, so start position plus scaled screen delta is both
     * correct outside the canvas and immune to the stale reading.
     */
    function _gridPointerCell(clientX: number, clientY: number): { x: number; y: number } | null {
        const drag = state.gridDrag;
        const stage = state.stage;
        if (!drag || !stage) return null;
        const scale = stage.scaleX() || 1;
        return {
            x: drag.start.x + (clientX - drag.clientX) / (CELL * scale),
            y: drag.start.y + (clientY - drag.clientY) / (CELL * scale),
        };
    }

    function _gridDragTo(p: WpPayload, cx: number, cy: number): void {
        const drag = state.gridDrag;
        if (!drag) return;
        if (drag.kind === 'move') {
            // Repositioning the *scope* on the graph map (task-523), not the
            // canvas: the grid stays put; map_offset moves every node of the
            // scope by this m*FIX* cells.
            state.gridDrag!.offset = {
                x: drag.offset.x + (cx - drag.start.x),
                y: drag.offset.y + (cy - drag.start.y),
            };
        } else {
            const next = GM().gridHandleDrag(drag.w, drag.h, drag.key, { x: cx, y: cy });
            state.gridDrag!.w = next.w;
            state.gridDrag!.h = next.h;
        }
        // Both layers: the frame and grid lines are on bg, the handles and the
        // size readout on decor. Redrawing only decor is why the number moved and
        // the line did not.
        const bg = state.layers && state.layers.bg;
        if (bg) bg.batchDraw();
        _redrawDecor();
    }

    async function _gridMouseUp(p: WpPayload): Promise<void> {
        const drag = state.gridDrag;
        if (!drag) return;
        state.gridDrag = null;
        const savedAnchor = drag.anchorScreen;
        const oldGrid = { w: p.grid!.w, h: p.grid!.h };
        state.cellSizePreview = null;
        try {
            if (drag.kind === 'move') {
                const offset = {
                    x: Math.round(drag.offset.x * 10) / 10,
                    y: Math.round(drag.offset.y * 10) / 10,
                };
                // The offset route answers with just the offset, not the whole
                // grid, so adopt the field rather than replace the payload.
                const resp = await _post(`/${encodeURIComponent(p.scope.id)}/offset`, offset);
                p.map_offset = (resp && resp.map_offset) || offset;
                _status(`Grid offset set to ${offset.x}, ${offset.y} cells.`, false);
            } else if (drag.kind === 'cell-size' && (drag.w !== p.grid!.w || drag.h !== p.grid!.h)) {
                const why = drag.pxPerCell ? `1 cell ≈ ${Math.round(drag.pxPerCell)}px` : 'cell resize';
                const committed = await _commitGridSize(p, drag.w, drag.h, why, oldGrid);
                if (!committed) {
                    _applyRefTransform(p);
                    if (savedAnchor) {
                        const origCells = _refRectCells(p, state.refImage, oldGrid);
                        _anchorStageToRefScreen(savedAnchor, origCells);
                    }
                    _redrawGrid();
                    return;
                }
            } else if (drag.w !== p.grid!.w || drag.h !== p.grid!.h) {
                await _commitGridSize(p, drag.w, drag.h, 'frame resize');
            }
            _notify(true);
        } catch (e) {
            _status(`Grid adjust failed: ${errText(e)}`, true);
        }
        render();
        if (drag.kind === 'cell-size' && state.payload && savedAnchor) {
            const afterCells = _refRectCells(state.payload, state.refImage);
            _anchorStageToRefScreen(savedAnchor, afterCells);
            _redrawGrid();
        }
    }

    /**
     * Commit a grid extent, offering the count of what the shrink would strand
     * before it does it.
     *
     * One path for the handle drag and the `px / cell` slider, so every resize
     * loses the same cells to the same rule, and the count in the warning is
     * exactly the set the canvas highlighted while the author was dragging.
     * Server-side the shrink *prunes* out-of-bounds paint and placements
     * (`world_grid.ensure_grid`) rather than leaving them dangling.
     */
    async function _commitGridSize(
        p: WpPayload, w: number, h: number, why: string,
        rescaleRefFrom?: { w: number; h: number },
    ): Promise<boolean> {
        const stranded = GM().strandedCount(p, w, h);
        if (stranded > 0 && !window.confirm(
            `Resize the grid to ${w}×${h} (${why})?\n\n`
            + `${stranded} painted cell(s) or placement(s) outside it will be removed. `
            + 'This can be undone.')) {
            return false;
        }
        const storedRect = (p.reference || {}).rect;
        state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid`,
            { w, h, mode: p.mode });
        if (rescaleRefFrom && storedRect && typeof storedRect.w === 'number' && storedRect.w > 0
                && (rescaleRefFrom.w !== w || rescaleRefFrom.h !== h) && state.payload) {
            const scaledRect = _scaleRefRect(storedRect, rescaleRefFrom, { w, h });
            const ref = state.payload.reference || {};
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/reference`, {
                image: ref.image || null,
                opacity: ref.opacity,
                visible: ref.visible,
                crop: ref.crop,
                rect: scaledRect,
            });
        }
        _status(`Grid set to ${w}×${h} (${why})`
            + (stranded ? `, ${stranded} out-of-bounds cell(s) removed` : '') + '.', false);
        return true;
    }

    function _drawGridLines(ctx: CanvasRenderingContext2D, p: WpPayload): void {
        const ext = _gridExtent(p);
        const preview = state.cellSizePreview;
        const hasRefImg = Boolean(state.refImage && state.refImage.naturalWidth
            && p.reference && p.reference.image);
        const refRect = (preview && hasRefImg) ? _refRectCells(p, state.refImage, preview) : null;
        // During a `px / cell` preview (slider or cell-corner drag), bind the
        // outer frame and the cell lattice strictly to the borders of the
        // background reference image so cells visibly grow or shrink inside the
        // image borders without ever overhanging into empty space outside the art.
        const w = refRect ? (refRect.w * CELL) : (ext.w * CELL);
        const h = refRect ? (refRect.h * CELL) : (ext.h * CELL);
        const maxCols = refRect ? Math.ceil(refRect.w) : ext.w;
        const maxRows = refRect ? Math.ceil(refRect.h) : ext.h;
        ctx.save();
        // No opaque fill: the reference image (a layer beneath) must show through.
        const scale = state.stage ? state.stage.scaleX() : 1;
        // The extent and origin have to be visible (task-597): a bold frame
        // around the grid, a marker at cell (0,0), and a faint box around the
        // painted content so an author can see at a glance how much of the grid
        // is used and which corner is the origin.
        ctx.strokeStyle = state.gridEdit ? '#e3b341' : 'rgba(255,255,255,0.45)';
        ctx.lineWidth = 2 / scale;
        ctx.strokeRect(0, 0, w, h);
        const bounds = GM().paintedBounds(p);
        if (bounds) {
            ctx.fillStyle = 'rgba(227,179,65,0.08)';
            ctx.fillRect(bounds.x * CELL, bounds.y * CELL, bounds.w * CELL, bounds.h * CELL);
            ctx.strokeStyle = 'rgba(227,179,65,0.5)';
            ctx.lineWidth = 1 / scale;
            ctx.setLineDash([5 / scale, 4 / scale]);
            ctx.strokeRect(bounds.x * CELL, bounds.y * CELL, bounds.w * CELL, bounds.h * CELL);
            ctx.setLineDash([]);
        }
        // Origin marker at (0,0) plus its label.
        ctx.fillStyle = '#e3b341';
        ctx.beginPath();
        ctx.arc(0, 0, 4 / scale, 0, Math.PI * 2);
        ctx.fill();
        ctx.font = `${11 / scale}px sans-serif`;
        ctx.fillText(preview
            ? `0,0 · snaps to ${ext.w}×${ext.h} (1 cell ≈ ${Math.round(preview.pxPerCell)}px)`
            : `0,0 · ${ext.w}×${ext.h}`, 6 / scale, -5 / scale);
        // Below ~4px per cell the lines become moire - paint only.
        if (CELL * scale >= 4) {
            ctx.save();
            // Clip the lattice strictly to the frame/image box so partial cells at
            // the right or bottom edge of the reference image never stick out.
            ctx.beginPath();
            ctx.rect(0, 0, w, h);
            ctx.clip();
            const hasRef = Boolean(p.reference && p.reference.image && p.reference.visible);
            ctx.strokeStyle = preview
                ? 'rgba(255,230,140,0.60)'
                : (hasRef ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.09)');
            ctx.lineWidth = (preview ? 1.25 : 1) / scale;
            ctx.beginPath();
            for (let x = 0; x <= maxCols; x += 1) {
                ctx.moveTo(x * CELL, 0);
                ctx.lineTo(x * CELL, h);
            }
            for (let y = 0; y <= maxRows; y += 1) {
                ctx.moveTo(0, y * CELL);
                ctx.lineTo(w, y * CELL);
            }
            ctx.stroke();
            ctx.restore();
        }
        // The cells a shrink would strand (task-597), drawn on the candidate
        // extent so the author sees *which* cells go and not only how m*FIX*. They
        // sit outside the new frame by definition, and the confirm dialog that
        // will remove them names the same count `strandedCells` produced.
        if (preview) {
            ctx.fillStyle = 'rgba(247,119,119,0.30)';
            ctx.strokeStyle = '#f77';
            ctx.lineWidth = 1 / scale;
            GM().strandedCells(p, preview.w, preview.h).forEach((c: *FIX*) => {
                ctx.fillRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
                ctx.strokeRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
            });
        }
        ctx.restore();
    }

    function _drawPaint(ctx: CanvasRenderingContext2D, p: WpPayload): void {
        if (!p.grid) return;
        if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
            _ensurePaintCache(p);
            if (state.paintCache) {
                ctx.save();
                ctx.globalAlpha = state.paintAlpha == null ? 1 : state.paintAlpha;
                ctx.imageSmoothingEnabled = false;
                ctx.drawImage(state.paintCache, 0, 0, p.grid.w, p.grid.h, 0, 0, p.grid.w * CELL, p.grid.h * CELL);
                ctx.restore();
                return;
            }
        }
        ctx.save();
        ctx.globalAlpha = state.paintAlpha == null ? 1 : state.paintAlpha;
        const layers = p.layers || {};
        Object.keys(layers).forEach((layer) => {
            const cells = layers[layer] || {};
            Object.keys(cells).forEach((key) => {
                const pos = GM().parseCellKey(key);
                if (!pos) return;
                const color = GM().layerColor(layer, cells[key]);
                if (!color) return;
                ctx.fillStyle = color;
                ctx.fillRect(pos.x * CELL, pos.y * CELL, CELL, CELL);
            });
        });
        ctx.restore();
    }

    function _drawFeatures(ctx: CanvasRenderingContext2D, p: WpPayload): void {
        ctx.save();
        ctx.globalAlpha = state.paintAlpha == null ? 1 : state.paintAlpha;
        const scale = state.stage ? state.stage.scaleX() : 1;
        ctx.font = `${Math.max(9, CELL - 8)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        (p.placements || []).forEach((pl) => {
            const selected = pl.id === state.selectedChild;
            ctx.fillStyle = selected ? '#f5c542' : 'rgba(123,90,166,0.82)';
            ctx.fillRect(pl.x * CELL + 4, pl.y * CELL + 4, CELL - 8, CELL - 8);
            ctx.strokeStyle = selected ? '#fff' : '#d8c4f0';
            ctx.lineWidth = 1 / scale;
            ctx.strokeRect(pl.x * CELL + 4, pl.y * CELL + 4, CELL - 8, CELL - 8);
            ctx.fillStyle = '#fff';
            ctx.font = `${Math.max(8, CELL - 10)}px sans-serif`;
            ctx.fillText('🏠', pl.x * CELL + CELL / 2, pl.y * CELL + CELL / 2 - (CELL * scale >= 20 && pl.name ? 2 : 0));
            if (CELL * scale >= 20 && pl.name) {
                const label = _ellipsize(pl.name, 14);
                ctx.font = `${Math.max(3, Math.min(9, 10 / scale))}px sans-serif`;
                ctx.strokeStyle = 'rgba(13,17,23,0.9)';
                ctx.lineWidth = 2.5 / scale;
                ctx.strokeText(label, pl.x * CELL + CELL / 2, pl.y * CELL + CELL - 3);
                ctx.fillStyle = selected ? '#fff6cc' : '#f0e6ff';
                ctx.fillText(label, pl.x * CELL + CELL / 2, pl.y * CELL + CELL - 3);
            }
        });
        // Placed areas (task-528) sit in the same decor layer but are a different
        // kind of thing - a node that already exists, not a child scope - so they
        // get their own colour and a corner notch instead of the house glyph.
        (p.area_placements || []).forEach((a) => {
            const selected = a.id === state.selectedArea;
            ctx.fillStyle = selected ? '#f5c542' : '#2f7d5a';
            ctx.fillRect(a.x * CELL + 2, a.y * CELL + 2, CELL - 4, CELL - 4);
            ctx.strokeStyle = '#d9f2e5';
            ctx.lineWidth = 1;
            ctx.strokeRect(a.x * CELL + 2.5, a.y * CELL + 2.5, CELL - 5, CELL - 5);
            // A name is worth showing when the cell is big enough to hold one;
            // at 1x the map is a mosaic and only the marker reads.
            if (CELL * scale >= 20 && a.name) {
                const label = _ellipsize(a.name, 12);
                ctx.font = '9px sans-serif';
                ctx.strokeStyle = 'rgba(13,17,23,0.9)';
                ctx.lineWidth = 2.5 / scale;
                ctx.strokeText(label, a.x * CELL + CELL / 2, a.y * CELL + CELL + 8);
                ctx.fillStyle = '#d9f2e5';
                ctx.fillText(label, a.x * CELL + CELL / 2, a.y * CELL + CELL + 8);
            }
        });
        ctx.restore();
    }

    function _ellipsize(text: unknown, max: number): string {
        const s = String(text == null ? '' : text);
        return s.length > max ? `${s.slice(0, max - 1)}…` : s;
    }

    function _drawVisionDecor(ctx: CanvasRenderingContext2D): void {
        if (state.tool !== 'vision' && !state.visionLens) return;

        // 1. Draw LoS field highlights (if lens active or vision tool has origin)
        if (state.visionVisibleSet && (state.visionLens || state.tool === 'vision')) {
            ctx.save();
            ctx.fillStyle = 'rgba(45, 85, 132, 0.28)';
            state.visionVisibleSet.forEach((key: string) => {
                const c = GM().parseCellKey(key);
                if (c) {
                    ctx.fillRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
                }
            });
            ctx.restore();
        }

        // 2. Draw origin marker
        if (state.visionOrigin) {
            const ox = state.visionOrigin.x * CELL + CELL / 2;
            const oy = state.visionOrigin.y * CELL + CELL / 2;
            ctx.save();
            ctx.beginPath();
            ctx.arc(ox, oy, CELL * 0.45, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(45, 85, 132, 0.7)';
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#58a6ff';
            ctx.stroke();

            // Pupil / eye dot
            ctx.beginPath();
            ctx.arc(ox, oy, CELL * 0.18, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();

            // Facing cone arc indicator
            if (state.visionFacing) {
                const compassAngles: Record<string, number> = {
                    e: 0, se: 45, s: 90, sw: 135,
                    w: 180, nw: 225, n: 270, ne: 315
                };
                const f = state.visionFacing.toLowerCase();
                if (compassAngles[f] != null) {
                    const centerRad = (compassAngles[f] * Math.PI) / 180;
                    const halfRad = (60 * Math.PI) / 180;
                    ctx.beginPath();
                    ctx.moveTo(ox, oy);
                    ctx.arc(ox, oy, CELL * 2.5, centerRad - halfRad, centerRad + halfRad);
                    ctx.closePath();
                    ctx.fillStyle = 'rgba(88, 166, 255, 0.18)';
                    ctx.fill();
                    ctx.strokeStyle = '#58a6ff';
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }
            ctx.restore();
        }

        // 3. Draw raycast line and steps
        if (state.visionOrigin && state.visionTarget && state.visionRay) {
            const ox = state.visionOrigin.x * CELL + CELL / 2;
            const oy = state.visionOrigin.y * CELL + CELL / 2;
            const tx = state.visionTarget.x * CELL + CELL / 2;
            const ty = state.visionTarget.y * CELL + CELL / 2;

            ctx.save();
            // Highlight supercover steps
            const steps = state.visionRay.steps || [];
            steps.forEach((s) => {
                ctx.fillStyle = s.blocked ? 'rgba(248, 81, 73, 0.35)' : 'rgba(63, 185, 80, 0.2)';
                ctx.fillRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2);
                if (s.blocked) {
                    ctx.strokeStyle = '#f85149';
                    ctx.lineWidth = 1.5;
                    ctx.strokeRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2);
                }
            });

            // Ray line
            ctx.beginPath();
            ctx.moveTo(ox, oy);
            ctx.lineTo(tx, ty);
            ctx.lineWidth = 2.5;
            ctx.strokeStyle = state.visionRay.visible ? '#3fb950' : '#f85149';
            ctx.stroke();

            // Target marker
            ctx.beginPath();
            ctx.arc(tx, ty, 4, 0, Math.PI * 2);
            ctx.fillStyle = state.visionRay.visible ? '#3fb950' : '#f85149';
            ctx.fill();

            ctx.restore();
        }
    }

    function _drawRoute(ctx: CanvasRenderingContext2D): void {
        // In-progress paint stroke (drag): drawn optimistically, committed on
        // mouse-up as one batch. Without this a brush drag felt like "click and
        // wait" - now it paints a live trail.
        if (state.stroke && state.stroke.length) {
            ctx.save();
            ctx.globalAlpha = state.paintAlpha == null ? 1 : state.paintAlpha;
            ctx.fillStyle = state.strokeValue == null
                ? '#8a8a8a'
                : (GM().layerColor(state.strokeLayer, state.strokeValue) || '#cccccc');
            state.stroke.forEach((c) => {
                ctx.fillRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
            });
            ctx.restore();
        }
        // Brush hover preview: outline the cells the brush would cover.
        // Above the route early-return on purpose: with no route in
        // progress this is the only thing left to draw, and the return
        // below would skip it entirely (task-719).
        const hover = state.brushHover;
        if (hover && hover.length && state.payload) {
            ctx.save();
            ctx.strokeStyle = 'rgba(255,255,255,0.55)';
            ctx.lineWidth = Math.max(1, 1.5 / ((state.stage && state.stage.scaleX()) || 1));
            ctx.setLineDash([4 / ((state.stage && state.stage.scaleX()) || 1), 3 / ((state.stage && state.stage.scaleX()) || 1)]);
            hover.forEach((c) => {
                ctx.strokeRect(c.x * CELL + 0.5, c.y * CELL + 0.5, CELL - 1, CELL - 1);
            });
            ctx.setLineDash([]);
            ctx.restore();
        }
        _drawVisionDecor(ctx);
        const pts = state.route || [];
        if (!pts.length) return;
        ctx.save();
        ctx.strokeStyle = '#7ab';
        ctx.lineWidth = Math.max(1.5, CELL / 6);
        ctx.setLineDash([6, 4]);
        if (pts.length > 1) {
            ctx.beginPath();
            pts.forEach((pt, i) => {
                const cx = pt.x * CELL + CELL / 2;
                const cy = pt.y * CELL + CELL / 2;
                if (i === 0) ctx.moveTo(cx, cy); else ctx.lineTo(cx, cy);
            });
            ctx.stroke();
        }
        ctx.setLineDash([]);
        ctx.fillStyle = '#f5c542';
        pts.forEach((pt) => {
            ctx.beginPath();
            ctx.arc(pt.x * CELL + CELL / 2, pt.y * CELL + CELL / 2, 3, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.restore();
    }

    function _isPaintTool(): boolean {
        return state.tool === 'paint' || state.tool === 'erase';
    }

    /**
     * Whether the active tool actually acts on an N x N footprint.
     *
     * Paint and Erase stroke it; Route widens its trail with it in applyRoute.
     * Every other tool (select, move, feature, area, inspect) acts on the one
     * cell under the pointer, so showing the brush outline there promises a
     * footprint the click never uses (bug-558).
     */
    function _toolUsesBrush(): boolean {
        return _isPaintTool() || state.tool === 'route';
    }

    function _strokeAdd(p: WpPayload, cell: WpCell | null): boolean {
        if (!cell) return false;
        const keys = state.strokeKeys || (state.strokeKeys = {});
        let added = false;
        _brushCells(p, cell.x, cell.y).forEach((b) => {
            const k = GM().cellKey(b.x, b.y);
            if (!keys[k]) { keys[k] = true; state.stroke.push(b); added = true; }
        });
        return added;
    }

    async function _commitStroke(p: WpPayload): Promise<void> {
        state.stroking = false;
        const cells = state.stroke || [];
        const layer = state.strokeLayer;
        const value = state.strokeValue;
        state.stroke = [];
        state.strokeKeys = {};
        if (!cells.length) { _redrawDecor(); return; }
        if (layer && value !== null && value !== undefined) {
            _pushRecent(layer, value);
        }
        try {
            if (cells.length === 1) {
                // Slim ack + optimistic patch (bug-545): the server returns
                // `{ok}` without rebuilding the payload, and the one cell
                // lands in the local layer map immediately. A failure falls
                // back to a full render so a rejected paint never lingers.
                const ack = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint`,
                    { layer, x: cells[0].x, y: cells[0].y, value, slim: 1 });
                // A slim ack carries no `layers` (old servers answer full
                // payloads, which fall through to the render below).
                if (ack && layer && !('layers' in (ack as object)) && state.payload && state.payload.layers) {
                    const key = GM().cellKey(cells[0].x, cells[0].y);
                    const map = state.payload.layers[layer] || (state.payload.layers[layer] = {});
                    if (value === null || value === undefined || value === '') delete map[key];
                    else map[key] = value;
                    _patchPaintCache(state.payload, cells);
                    _notify(true);
                    softRender();
                    const hadNoPaint = Array.isArray(state.payload.blockers)
                        && state.payload.blockers.some((b) => b && b.code === 'no-paint');
                    if (hadNoPaint && Object.keys(map).length > 0) {
                        state.payload.blockers = state.payload.blockers!.filter((b) => !b || b.code !== 'no-paint');
                        load(p.scope.id);
                    } else if (!hadNoPaint && Object.keys(map).length === 0) {
                        load(p.scope.id);
                    }
                    return;
                }
                // Old server (or unexpected shape): fall back to the payload.
                if (ack && ('layers' in (ack as object))) {
                    state.payload = ack;
                    _patchPaintCache(state.payload || p, cells);
                    _notify(true);
                    softRender();
                    return;
                }
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint`,
                    { layer, x: cells[0].x, y: cells[0].y, value });
                _patchPaintCache(state.payload || p, cells);
            } else {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                    { edits: cells.map((c) => ({ layer, x: c.x, y: c.y, value })) });
                _patchPaintCache(state.payload || p, cells);
            }
            _notify(true);
            softRender();
        } catch (e) {
            _status(`Paint failed: ${errText(e)}`, true);
        }
    }

    function _wireGrid(p: WpPayload): void {
        // Only ever reached from _mountGrid, which assigns state.stage first.
        const stage = state.stage!;
        let dragged = false;
        // Paint/erase drag = paint. Pan is space-drag (or the zoom buttons), so a
        // stroke is never interrupted by a pan. Select drag = marquee, decided by
        // the active tool and nothing else - a drag means different things under
        // different tools, and which one is always the tool the author can see.
        // In reference-adjust mode the drag belongs to the picture, so only space
        // pans there.
        const dragPaints = () => _isPaintTool() || state.tool === 'move';
        stage.draggable(state.spaceDown || (!state.refEdit && !state.gridEdit && !dragPaints()
            && state.tool !== 'select'));
        stage.on('dragstart', () => { dragged = true; });
        stage.on('dragend', _captureView);

        stage.on('mousedown', (e) => {
            if (state.refEdit && !state.spaceDown) { _refMouseDown(p); return; }
            if (state.gridEdit && !state.spaceDown) { _gridMouseDown(p, e.evt); return; }
            if (e.evt && e.evt.button !== 0) return;
            if (state.tool === 'select' && !state.spaceDown) {
                const cell = _cellAtPointer(p);
                if (!cell) return;
                state.marquee = { anchor: cell, to: cell,
                    add: !!(e.evt && e.evt.shiftKey) };
                _redrawDecor();
                return;
            }
            if (!_isPaintTool() || state.spaceDown) return;
            // Alt+click samples the active layer value under the cursor into the brush (task-879).
            if (e.evt && e.evt.altKey) {
                const cell = _cellAtPointer(p);
                if (!cell) return;
                const val = GM().cellValue(p, state.layer, cell.x, cell.y);
                if (val !== undefined && val !== null && val !== '') {
                    state.value = String(val);
                    _pushRecent(state.layer, state.value);
                    _saveScopePrefs();
                    softRender();
                    _status(`Sampled ${state.layer} "${state.value}" from cell (${cell.x}, ${cell.y}).`, false);
                } else {
                    _status(`Cell (${cell.x}, ${cell.y}) has no paint on the ${state.layer} layer.`, false);
                }
                return;
            }
            // A selection is the whole point of the Select tool: with cells
            // selected, a paint click is one batch over all of them rather than a
            // single-cell edit the author then has to repeat by hand.
            if (_selectedCells(p).length) { _applyToSelection(p); return; }
            state.stroke = [];
            state.strokeKeys = {};
            state.strokeLayer = state.layer;
            state.strokeValue = state.tool === 'erase' ? null : state.value;
            state.stroking = true;
            _strokeAdd(p, _cellAtPointer(p));
            _redrawDecor();
        });

        let moveRaf: number | null = null;
        stage.on('mousemove', () => {
            // The active grid drag tracks itself on the document (it must outlive
            // the pointer leaving the canvas); nothing else may claim the pointer.
            if (state.gridEdit) return;
            if (state.refEdit) { _refMouseMove(p); return; }
            if (moveRaf !== null) return;
            moveRaf = requestAnimationFrame(() => {
                moveRaf = null;
                if (!state.stage) return;
                const cell = _cellAtPointer(p);
                if (state.marquee && cell) {
                    if (cell.x !== state.marquee.to.x || cell.y !== state.marquee.to.y) {
                        state.marquee.to = cell;
                        _redrawDecor();
                    }
                    return;
                }
                if (state.stroking && _strokeAdd(p, cell)) _redrawDecor();
                else if (cell) {
                    state.brushHover = _toolUsesBrush()
                        ? _brushCells(p, cell.x, cell.y)
                        : [{ x: cell.x, y: cell.y }];
                    _redrawDecor();
                } else {
                    state.brushHover = null;
                    _redrawDecor();
                }
                _updateCellInfo(p);
            });
        });

        stage.on('mouseup mouseleave', () => {
            if (moveRaf !== null) {
                cancelAnimationFrame(moveRaf);
                moveRaf = null;
            }
            // No grid branch: the drag owns its own document mouseup, so a
            // `mouseleave` here would commit the resize the moment the pointer
            // left the frame.
            if (state.refEdit) { _refMouseUp(); return; }
            if (state.marquee) { _commitMarquee(p); return; }
            if (state.stroking) _commitStroke(p);
            state.brushHover = null;
            _redrawDecor();
        });

        stage.on('click tap', () => {
            if (state.refEdit || state.gridEdit) return;   // adjust modes own the pointer
            if (dragged) { dragged = false; return; }
            if (_isPaintTool()) return;   // already committed by the stroke
            if (state.tool === 'select') return;   // committed by the marquee
            const cell = _cellAtPointer(p);
            if (cell) _gridClick(p, cell);
        });
        // Right-click is "what is this?" on *FIX* tool, so a cell is never a dead
        // end you have to switch tools to inspect.
        stage.on('contextmenu', (e) => {
            e.evt.preventDefault();
            if (state.refEdit || state.gridEdit) return;
            const cell = _cellAtPointer(p);
            if (cell) inspectCell(p, cell.x, cell.y);
        });
        stage.on('wheel', (e) => {
            e.evt.preventDefault();
            const old = stage.scaleX();
            const ptr = stage.getPointerPosition();
            const gridPt = { x: (ptr.x - stage.x()) / old, y: (ptr.y - stage.y()) / old };
            const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, old * (e.evt.deltaY < 0 ? 1.12 : 0.89)));
            stage.scale({ x: next, y: next });
            stage.position({ x: ptr.x - gridPt.x * next, y: ptr.y - gridPt.y * next });
            _captureView();
            _syncZoomButtons();
            _redrawGrid();
        });
    }

    // ───────────────── cell selection and move (task-536) ───────────────

    /** The cell keys selected on this scope, as a set-like object. */
    function _sel(p: WpPayload | null): Record<string, boolean> {
        const id = (p && p.scope && p.scope.id) || state.scopeId || '';
        if (!state.selection[id]) state.selection[id] = {};
        return state.selection[id];
    }

    function _selectedCells(p: WpPayload | null): WpCell[] {
        return Object.keys(_sel(p)).map((k) => GM().parseCellKey(k))
            .filter(Boolean)
            .map((c) => ({ x: c.x, y: c.y }));
    }

    function _setSelection(p: WpPayload | null, keys: Record<string, boolean>): void {
        _sel(p);
        state.selection[(p && p.scope && p.scope.id) || state.scopeId || ''] = keys;
    }

    /** The cells a marquee from the anchor to `to` covers, clipped to the grid. */
    function _marqueeCells(p: WpPayload, to: WpCell): Record<string, boolean> {
        const a = (state.marquee && state.marquee.anchor) || to;
        const x0 = Math.max(0, Math.min(a.x, to.x));
        const x1 = Math.min(p.grid!.w - 1, Math.max(a.x, to.x));
        const y0 = Math.max(0, Math.min(a.y, to.y));
        const y1 = Math.min(p.grid!.h - 1, Math.max(a.y, to.y));
        const out: Record<string, boolean> = {};
        for (let y = y0; y <= y1; y += 1) {
            for (let x = x0; x <= x1; x += 1) out[GM().cellKey(x, y)] = true;
        }
        return out;
    }

    /**
     * Shift the selected cells' contents one cell, in one request (task-536).
     *
     * A move is *not* a paint of the destination on top of the source: the source
     * has to end up empty or the move is a smear, and a smear of a road leaves the
     * map with two of them. So it is one batch - clear every source cell on every
     * layer it has, then write each value at its new home - which means one undo
     * step, one request, and a rejection of the whole thing if *FIX* cell would land
     * off the grid. Clamping is what the task asks for and it is also the honest
     * behaviour: a cell shifted past the edge is dropped from the move, not
     * silently wrapped to the other side.
     */
    async function _nudge(p: WpPayload, dx: number, dy: number): Promise<void> {
        const cells = _selectedCells(p);
        if (!cells.length) { _status('Nothing selected - use the ⬚ Select tool first.', true); return; }
        const layers = GM().PAINT_LAYERS;
        const layerCells: Record<string, Record<string, string>> = {};
        layers.forEach((l: string) => { layerCells[l] = p.layers?.[l] || {}; });
        const edits: WpEdit[] = [];
        const moving: { from: WpCell; to: WpCell }[] = [];
        cells.forEach((c) => {
            const nx = c.x + dx;
            const ny = c.y + dy;
            if (nx < 0 || ny < 0 || nx >= p.grid!.w || ny >= p.grid!.h) return;   // clamped off
            moving.push({ from: c, to: { x: nx, y: ny } });
        });
        if (!moving.length) {
            _status('The whole selection is against that edge - nowhere to move it.');
            return;
        }
        // Clear first, then write: a value moving one cell east must not be
        // cleared by its own neighbour's clear on the next step of the same batch.
        moving.forEach(({ from }) => layers.forEach((l: string) => {
            const k = GM().cellKey(from.x, from.y);
            if (layerCells[l][k] != null) {
                edits.push({ layer: l, x: from.x, y: from.y, value: null });
            }
        }));
        moving.forEach(({ from, to }) => layers.forEach((l: string) => {
            const k = GM().cellKey(from.x, from.y);
            const value = layerCells[l][k];
            if (value != null) edits.push({ layer: l, x: to.x, y: to.y, value });
        }));
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                { edits });
            const next = {};
            moving.forEach(({ to }) => { (next as Record<string, boolean>)[GM().cellKey(to.x, to.y)] = true; });
            _setSelection(p, next);
            const dropped = cells.length - moving.length;
            _status(`Moved ${moving.length} cell${moving.length === 1 ? '' : 's'}`
                + (dropped ? `, ${dropped} left at the edge.` : '.'));
            state.paintCacheValid = false;
            _notify(true);
            softRender();
        } catch (e) {
            _status(`Move failed: ${errText(e)}`, true);
        }
    }

    /** Paint the active value (or erase) across the whole selection, one request. */
    async function _applyToSelection(p: WpPayload): Promise<boolean> {
        const cells = _selectedCells(p);
        if (!cells.length) return false;
        const layer = state.layer;
        const value = state.tool === 'erase' ? null : state.value;
        if (state.tool === 'paint' && (value == null || value === '')) {
            _status('Pick a value to paint first.', true);
            return true;
        }
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                { edits: cells.map((c) => ({ layer, x: c.x, y: c.y, value })) });
            _status(`${state.tool === 'erase' ? 'Cleared' : 'Painted'} ${cells.length} `
                + `cell${cells.length === 1 ? '' : 's'} on ${layer}.`);
            state.paintCacheValid = false;
            _notify(true);
            softRender();
        } catch (e) {
            _status(`${state.tool === 'erase' ? 'Clear' : 'Paint'} failed: ${errText(e)}`, true);
        }
        return true;
    }

    function _cellAtPointer(p: WpPayload): WpCell | null {
        const rp = state.stage && state.stage.getRelativePointerPosition();
        if (!rp) return null;
        const x = Math.floor(rp.x / CELL);
        const y = Math.floor(rp.y / CELL);
        if (x < 0 || y < 0 || x >= p.grid!.w || y >= p.grid!.h) return null;
        return { x, y };
    }

    /** Turn a finished drag into a selection (task-536). */
    function _commitMarquee(p: WpPayload): void {
        const drag = state.marquee;
        state.marquee = null;
        if (!drag) return;
        const keys = _marqueeCells(p, drag.to);
        const k = GM().cellKey(drag.anchor.x, drag.anchor.y);
        const single = Object.keys(keys).length === 1;
        if (drag.add) {
            // Shift adds to what was already selected; it never clears, which is
            // the whole point of holding shift.
            _setSelection(p, Object.assign({}, _sel(p), keys));
        } else if (single && _sel(p)[k]) {
            // A click on an already-selected cell takes it back. The same gesture
            // that made the selection removes it, so there is no state where the
            // only way out of a stray selection is a keyboard shortcut.
            const next = { ..._sel(p) };
            delete next[k];
            _setSelection(p, next);
        } else {
            _setSelection(p, keys);
        }
        const n = Object.keys(_sel(p)).length;
        _status(n ? `${n} cell${n === 1 ? '' : 's'} selected.`
            : 'Selection cleared.');
        _redrawDecor();
        softRender();
    }

    function _gridClick(p: WpPayload, cell: WpCell): void {
        const fmap = GM().featureMap(p);
        const placement = fmap[GM().cellKey(cell.x, cell.y)] || null;
        onCellClick(p, cell.x, cell.y, placement);
    }

    // ─────────────────────── cell inspector (task-540) ──────────────────
    //
    // Placing an area or painting a cell used to leave no way to find out what
    // had ended up there: the marker is ~5px on a big map and carries no name.
    // Hover reads the cell from the payload, and a click (or right-click on *FIX*
    // tool) opens a panel with the same facts plus the actions that apply to
    // exactly that cell.

    /** One line describing a cell, for the HUD hover readout. */
    function _cellLine(info: WpCellInfo | null): string {
        if (!info) return '';
        if (info.empty) return `(${info.x},${info.y}) — nothing here`;
        const bits = [];
        // The author's name leads, because it is the thing they wrote (task-560);
        // the paint layers are the evidence for it.
        if (info.name) bits.push(info.name);
        else if (info.biome) bits.push(String(info.biome).replace(/_/g, ' '));
        if (info.road) bits.push(String(info.road).replace(/_/g, ' '));
        // A structure cell says what it is, because it is not a place and the
        // author needs to know that before generating (task-562).
        if (info.kind) bits.push(STRUCTURE_NOTES[info.kind] || info.kind);
        // A building without an interior says so on hover, because "the door is
        // locked" is a thing the author wants to notice *while* painting, not
        // discover in play (task-563).
        if (info.enter && !info.child) bits.push(info.enter);
        if (info.floor !== null) bits.push(GM().floorLabel(info.floor));
        if (info.area) bits.push(`📍 ${info.area.name}`);
        if (info.child) bits.push(`🏠 ${info.child.name || info.child.id}`);
        return `(${info.x},${info.y}) ${bits.join(' · ')}`;
    }

    function _updateCellInfo(p: WpPayload): void {
        const el = state.cellInfoEl;
        if (!el) return;
        const cell = _cellAtPointer(p);
        const info = cell ? GM().cellInfo(p, cell.x, cell.y, state.vocab) : null;
        // Konva fires mousemove per pixel; only touch the DOM when the cell or
        // its content actually changed.
        const key = info ? `${info.key}|${info.name}|${info.biome}|${info.road}|${info.floor}|` +
            `${info.area ? info.area.id : ''}|${info.child ? info.child.id : ''}` : '';
        if (key === state.cellInfoKey) return;
        state.cellInfoKey = key;
        el.textContent = _cellLine(info) || 'hover a cell to read it';
    }

    function inspectCell(p: WpPayload, x: number, y: number): void {
        state.inspected = { x, y };
        softRender();
    }

    function _cellPanel(p: WpPayload): HTMLElement | null {
        const at = state.inspected;
        if (!at || !p.scope.has_grid) return null;
        const info = GM().cellInfo(p, at.x, at.y, state.vocab);
        const wrap = _el('div', 'border:1px solid var(--border,#3a3a44);border-radius:8px;' +
            'padding:8px;margin-bottom:10px;font-size:12px;');
        wrap.setAttribute('data-role', 'wp-cellpanel');
        const head = _el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;');
        head.appendChild(_el('strong', null, `Cell (${info.x},${info.y})`));
        head.appendChild(_el('span', 'color:var(--text-muted,#999);',
            info.empty ? 'nothing on this cell' : 'what is on this cell'));
        head.appendChild(_btn('✕', () => { state.inspected = null; softRender(); },
            'margin-left:auto;padding:1px 7px;', 'Close the cell panel'));
        wrap.appendChild(head);

        const rows = _el('div', 'display:flex;flex-direction:column;gap:2px;margin-top:6px;');
        const row = (label: string, value: string): void => {
            const r = _el('div', 'display:flex;gap:6px;align-items:baseline;');
            r.appendChild(_el('span', 'color:var(--text-muted,#999);min-width:78px;', label));
            r.appendChild(_el('span', null, value));
            rows.appendChild(r);
        };
        row('biome', info.biome ? String(info.biome).replace(/_/g, ' ') : '-');
        row('road', info.road ? String(info.road).replace(/_/g, ' ') : '-');
        row('floor', GM().floorLabel(info.floor));
        // Structure is not a place, and saying so is the point: the author just
        // painted a wall and it will not appear in the graph (task-562).
        row('structure', info.kind
            ? `not a place - ${STRUCTURE_NOTES[info.kind] || info.kind}`
            : '-');
        // A building is entered with `in`; a shut one is the author's cue that it
        // still owes an interior (task-563).
        row('enter', info.enter || '-');
        row('area', info.area ? `${info.area.name} (${info.area.id})` : '-');
        row('sub-zone', info.child ? `${info.child.name || info.child.id} (${info.child.id})` : '-');
        // Where you can leave this cell (task-596). Ways join adjacent cells, so
        // a cell's exits are its passable neighbours; a solid neighbour is a
        // wall to your face, and the map edge is not an exit at all.
        const neighbours = GM().cellNeighbours(p, at.x, at.y, state.vocab);
        const label = (n: WpCellInfo | null): string => {
            if (n === null) return 'map edge';
            const noun = String(n.road || n.biome || '').replace(/_/g, ' ');
            const solid = n.kind && n.kind !== 'place' ? ` (${n.kind})` : '';
            const what = noun ? `${noun}${solid}` : 'empty';
            return n.name ? `${what} “${n.name}”` : what;
        };
        row('exits', ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            .map((d) => `${d}: ${label(neighbours[d])}`).join(' · '));
        wrap.appendChild(rows);

        // The cell's name (task-560) - what the place is *called*, which is what
        // it compiles to. First, because a painted town is a list of names, and
        // "Building 3,4" is not an address.
        const nameRow = _el('div', 'display:flex;gap:6px;align-items:center;margin-top:6px;');
        nameRow.appendChild(_el('span', 'color:var(--text-muted,#999);min-width:78px;', 'name'));
        const nameInput = _el('input', 'flex:1;min-width:0;padding:2px 6px;border-radius:5px;' +
            'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
        nameInput.value = info.name || '';
        nameInput.placeholder = 'unnamed — compiles to a coordinate';
        nameInput.title = 'The name this place compiles to. Needed for a town: a building is not addressable until it has one.';
        nameInput.addEventListener('change', () => {
            setCellName(p, info.x, info.y, nameInput.value);
        });
        nameInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') nameInput.blur(); });
        nameRow.appendChild(nameInput);
        wrap.appendChild(nameRow);

        const actions = _el('div', 'display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;');
        if (info.area) {
            actions.appendChild(_btn(`📍 Move ${info.area.name}`, () => {
                state.tool = 'area';
                state.selectedArea = info.area!.id;
                render();
            }, '', 'Switch to the Area tool with this area picked, then click its new cell'));
            actions.appendChild(_btn('🗑 Unplace', () => unplaceArea(info.area!.id),
                '', 'Take this area off the map; the area itself is untouched'));
            if (window.VW && window.VW.inspector) {
                actions.appendChild(_btn('🔎 Open area', () => {
                    state.overlay!.remove();
                    window.VW.inspector.showNode(info.area!.id);
                }, '', 'Open this area in the graph inspector'));
            }
        }
        if (info.child) {
            actions.appendChild(_btn(`📂 Open ${info.child.name || info.child.id}`, () => {
                load(info.child!.id);
            }, '', 'Drill into this sub-zone'));
            actions.appendChild(_btn('🗑 Remove sub-zone', () => removeFeature(info.child!.id),
                '', 'Take the child scope off this cell (the scope itself is kept)'));
        }
        if (info.painted) {
            actions.appendChild(_btn('🧽 Clear paint', () => clearCell(p, info.x, info.y),
                '', 'Erase every paint layer on this one cell (one undo step)'));
        }
        if (!actions.childNodes.length) {
            actions.appendChild(_el('span', 'color:var(--text-muted,#999);',
                'Nothing to do here — paint it, or place an area/feature on it.'));
        }
        wrap.appendChild(actions);
        // The ways Generate minted out of the area placed on this cell, and what
        // the author has already done about them (task-528). Listed here because
        // the seam is the author\'s decision, and the cell it belongs to is the
        // one place the painter can show it next to the thing it joins.
        const seams = _seamPanel(p, info.area && info.area.id);
        if (seams) wrap.appendChild(seams);
        // …and the one action that changes what an area *is* rather than where it
        // sits: promote it into a child scope, with the gateway to it (task-535).
        if (info.area) {
            wrap.appendChild(_btn('🪜 Make this a scope…',
                () => promoteArea(info.area!.id), 'margin-top:8px;width:100%;',
                'Turn this area into a child scope of '
                + `${p.scope.name}, with a way in from its cell`));
        }
        return wrap;
    }

    /**
     * The boundary ways of one placed area, each with a way to take it away or
     * hand it back.
     *
     * Removing a seam here deletes the generated way *and* records the decision,
     * so it does not come back on the next Generate — the record is the whole
     * reason the two live in one request. A seam already handed over (a hand
     * written way of the author\'s own) is listed as such, with only "Restore".
     */
    function _seamPanel(p: WpPayload, areaId?: string | null): HTMLElement | null {
        if (!areaId) return null;
        const rows = (p.boundary_ways || []).filter((w) => w.area_id === areaId);
        const taken = (p.boundary_overrides || []).filter((o) => {
            const row = rows.find((w) => w.way_id === o.way_id);
            return row === undefined;
        });
        if (!rows.length && !taken.length) return null;

        const box = _el('div', 'margin-top:8px;padding-top:8px;border-top:1px solid ' +
            'var(--border,#3a3a44);display:flex;flex-direction:column;gap:3px;');
        box.setAttribute('data-role', 'wp-seams');
        box.appendChild(_el('div', 'color:var(--text-muted,#999);font-size:11px;',
            'Ways out of this area — Generate made these, you decide'));

        const line = (label: string, title: string, action: HTMLElement | null): void => {
            const r = _el('div', 'display:flex;gap:6px;align-items:center;');
            const text = _el('span', 'flex:1;min-width:0;', label);
            text.title = title || label;
            r.appendChild(text);
            if (action) r.appendChild(action);
            box.appendChild(r);
        };

        rows.forEach((w) => {
            const seamId = w.way_id;
            const where = w.to_name || w.to_id || 'somewhere';
            const label = w.direction ? `${w.direction} → ${where}` : `to ${where}`;
            if (w.overridden) {
                line(label, 'You have taken this seam over; Generate leaves it alone', null);
                return;
            }
            line(label, 'Remove this way. Generate will not put it back.',
                _btn('✕', () => setSeam(p, seamId, 'suppress'), 'padding:1px 7px;',
                    'Delete this way and keep Generate from re-adding it'));
        });

        // A seam the author removed (or replaced) has no node left to list, so it
        // is read back from the record — otherwise restoring it would need a
        // remembered way id, which is exactly what an author should not have to do.
        taken.forEach((o) => {
            const restore = _btn('↺', () => setSeam(p, o.way_id, 'auto'),
                'padding:1px 7px;', 'Hand this seam back to Generate');
            const what = o.action === 'hand' && o.hand_way_id
                ? `your own way (${o.hand_way_id})` : 'removed by you';
            line(`to ${what}`, 'Generate left this one alone; restore it', restore);
        });
        return box;
    }

    /** Take one boundary seam over, or hand it back to the compiler (task-528). */
    async function setSeam(p: WpPayload, wayId: string, action: string): Promise<void> {
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/boundary_override`,
                { way_id: wayId, action });
            _status(action === 'auto'
                ? 'Generate will mint that way again.'
                : 'Way removed — Generate will not put it back.');
            _notify(true);
            render();
        } catch (e) {
            _status(`Could not change that way: ${errText(e)}`, true);
        }
    }

    /** Erase all three paint layers on one cell, in a single request/undo step. */
    async function clearCell(p: WpPayload, x: number, y: number): Promise<void> {
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, {
                edits: GM().PAINT_LAYERS.map((layer: *FIX*) => ({ layer, x, y, value: null })),
            });
            _status(`Cleared the paint on (${x},${y}).`);
            _notify(true);
            render();
        } catch (e) {
            _status(`Clear failed: ${errText(e)}`, true);
        }
    }

    /**
     * Set (or clear) one cell's author name (task-560).
     *
     * Its own route rather than a paint layer, because a name is not paint: there
     * is no name vocabulary, the eraser should not wipe it, and "clear this cell"
     * must not silently unname a place. An empty box clears it, and the server drops
     * the entry entirely so an unnamed scope loads byte-identically.
     */
    async function setCellName(p: WpPayload, x: number, y: number, name: unknown): Promise<void> {
        const wanted = String(name || '').trim();
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/name`,
                { x, y, name: wanted });
            _status(wanted
                ? `Named (${x},${y}) “${wanted}”.`
                : `Cleared the name on (${x},${y}).`);
            _notify(true);
            softRender();
        } catch (e) {
            _status(`Name failed: ${errText(e)}`, true);
        }
    }

    /**
     * Grey out a zoom control that is already at its clamp (task-595). The
     * buttons used to look live at the floor and do nothing when pressed, which
     * reads as a broken control rather than a reached limit.
     */
    function _syncZoomButtons(): void {
        const scale = state.stage ? state.stage.scaleX() : null;
        if (!scale) return;
        if (state.zoomOutBtn) state.zoomOutBtn.disabled = scale <= MIN_SCALE + 1e-6;
        if (state.zoomInBtn) state.zoomInBtn.disabled = scale >= MAX_SCALE - 1e-6;
    }

    function _zoomBy(p: WpPayload, factor: number): void {
        const stage = state.stage;
        if (!stage) return;
        const old = stage.scaleX();
        const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, old * factor));
        const c = { x: stage.width() / 2, y: stage.height() / 2 };
        const gridPt = { x: (c.x - stage.x()) / old, y: (c.y - stage.y()) / old };
        stage.scale({ x: next, y: next });
        stage.position({ x: c.x - gridPt.x * next, y: c.y - gridPt.y * next });
        _captureView();
        _syncZoomButtons();
        _redrawGrid();
    }

    function _fitGrid(p: WpPayload): void {
        const stage = state.stage;
        if (!stage) return;
        const scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE,
            Math.min(
                (stage.width() * 0.88) / (p.grid!.w * CELL),
                (stage.height() * 0.88) / (p.grid!.h * CELL),
            )));
        stage.scale({ x: scale, y: scale });
        stage.position({
            x: (stage.width() - p.grid!.w * CELL * scale) / 2,
            y: (stage.height() - p.grid!.h * CELL * scale) / 2,
        });
        _captureView();
        _syncZoomButtons();
        _redrawGrid();
    }

    async function applyRoute(): Promise<void> {
        const p = state.payload;
        const cells: WpCell[] = GM().routeCells(state.route || []);
        if (cells.length < 2) { _status('Route needs at least two waypoints.'); return; }
        const value = state.value;
        if (value == null || value === '') { _status('Pick a paint value first.'); return; }
        // Brush widens the trail: a 3×3 brush turns a 1-cell line into a 3-wide river.
        const seen: Record<string, boolean> = {};
        const wide: WpCell[] = [];
        cells.forEach((c) => {
            _brushCells(p!, c.x, c.y).forEach((b) => {
                const k = GM().cellKey(b.x, b.y);
                if (!seen[k]) { seen[k] = true; wide.push(b); }
            });
        });
        const edits = wide.map((c) => ({ layer: state.layer, x: c.x, y: c.y, value }));
        try {
            state.payload = await _post(`/${encodeURIComponent(p!.scope.id)}/grid/paint_batch`,
                { edits });
            state.route = [];
            _patchPaintCache(state.payload || p!, edits);
            _notify(true);
            const stats = GM().routeStats(edits.length);
            _status(`🧭 Painted ${stats.label} on ${state.layer}.`, false);
            softRender();
        } catch (e) {
            _status(`Route failed: ${errText(e)}`, true);
        }
    }

    function _renderChildren(box: HTMLElement, p: WpPayload): void {
        const kids = p.children || [];
        if (!kids.length) return;
        const head = _el('div', 'font-size:12px;color:var(--text-muted,#999);margin:8px 0 4px;',
            'Child scopes');
        box.appendChild(head);
        const row = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;');
        kids.forEach((c) => row.appendChild(_scopeCard(c, (card) => load(card.id))));
        box.appendChild(row);
    }

    // ───────────────────────────── mutations ───────────────────────────

    async function onCellClick(p: WpPayload, x: number, y: number,
        placement: WpPlacement | null): Promise<void> {
        if (state.tool === 'inspect') {
            inspectCell(p, x, y);
            return;
        }
        if (state.tool === 'route') {
            // Collect waypoints; the HUD's "Paint route" rasterises the line and
            // batch-paints it in one request (a 240-cell trail is one undo).
            state.route.push({ x, y });
            if (state.routeInfoEl) state.routeInfoEl.textContent = _routeLabel();
            _redrawDecor();
            return;
        }
        if (state.tool === 'vision') {
            if (!state.visionOrigin) {
                state.visionOrigin = { x, y, floor: GM().tileFloor(p, x, y) };
                state.visionTarget = null;
                state.visionRay = null;
                _recomputeVisionField(p);
                _redrawDecor();
                render();
                _status(`Vision origin set to (${x}, ${y}, floor ${state.visionOrigin.floor}). Click *FIX* target cell to cast ray, or click origin again to clear.`);
                return;
            }
            if (state.visionOrigin.x === x && state.visionOrigin.y === y) {
                state.visionOrigin = null;
                state.visionTarget = null;
                state.visionRay = null;
                state.visionVisibleSet = null;
                _redrawDecor();
                render();
                _status('Vision debugger cleared.');
                return;
            }
            state.visionTarget = { x, y, floor: GM().tileFloor(p, x, y) };
            const origin: [number, number, number] = [
                state.visionOrigin.x,
                state.visionOrigin.y,
                state.visionOrigin.floor ?? 0
            ];
            const target: [number, number, number] = [x, y, state.visionTarget.floor ?? 0];
            const ray = GM().castSightRay(p, origin, target);
            state.visionRay = ray;
            _redrawDecor();
            render();
            const lastStep = ray.steps && ray.steps.length ? ray.steps[ray.steps.length - 1] : null;
            const obsStr = lastStep ? (lastStep.obscurity || 0).toFixed(2) : '0';
            _status(`Ray (${origin[0]},${origin[1]},z=${origin[2]}) -> (${target[0]},${target[1]},z=${target[2]}): ${ray.visible ? 'CLEAR' : 'BLOCKED'} (${ray.steps.length} steps, cum_obs=${obsStr}${ray.reason ? ', ' + ray.reason : ''})`);
            return;
        }
        if (state.tool === 'feature') {
            if (state.selectedChild) {
                await placeFeature(state.selectedChild, x, y);
            } else if (placement) {
                state.selectedChild = placement.id;
                render();
            } else {
                _status('Select a feature first (Feature dropdown above).');
            }
            return;
        }
        if (state.tool === 'area') {
            await onAreaCellClick(p, x, y);
            return;
        }
        if (!p.scope.has_grid) return;
        return _paintAt(p, x, y);
    }

    /**
     * Place tool (task-528). One click places the picked area; a click on a cell
     * that already holds one offers to take it off the map, so removing needs no
     * second mode to learn.
     */
    async function onAreaCellClick(p: WpPayload, x: number, y: number): Promise<void> {
        if (!p.scope.has_grid) { _status('This scope has no grid to place on.', true); return; }
        const here = GM().areaAt(p, x, y);
        if (here) {
            if (!window.confirm(`Take "${here.name}" off this map? The area itself stays.`)) return;
            await unplaceArea(here.id);
            return;
        }
        if (!state.selectedArea) {
            _status('Pick an area from the Area dropdown first.');
            return;
        }
        await placeArea(state.selectedArea, x, y);
    }

    async function placeArea(areaId: string, x: number, y: number, onOverlap?: string): Promise<void> {
        const p = state.payload!;
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/place_area`,
                { area_id: areaId, x, y, on_overlap: onOverlap || 'forbid' });
            _status(`Placed on cell (${x},${y}).`);
            _notify(true);
            render();
        } catch (e) {
            // The server names the occupant, so a clash is actionable as-is.
            const msg = errText(e);
            if (/already holds/.test(msg) && window.confirm(`${msg}\n\nDisplace it?`)) {
                await placeArea(areaId, x, y, 'displace');
                return;
            }
            _status(`Place failed: ${msg}`, true);
        }
    }

    async function unplaceArea(areaId: string): Promise<void> {
        const p = state.payload!;
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/unplace_area`,
                { area_id: areaId });
            if (state.selectedArea === areaId) state.selectedArea = null;
            _status('Taken off the map (the area itself is untouched).');
            _notify(true);
            render();
        } catch (e) {
            _status(`Unplace failed: ${errText(e)}`, true);
        }
    }

    /**
     * Make the selected area into a child scope of this one, placed on the cell
     * it is standing on (task-535).
     *
     * The cell it is on is the natural home for the scope: it is where the author
     * put the area, so the new scope's gateway opens from exactly the doorstep
     * they chose. If that cell already holds a hand-placed area, that area becomes
     * the doorstep (the server's `gateway` overlap) — which is the goblin camp
     * case: an entrance parked by the road, with the camp itself promoted behind
     * it.
     *
     * The name is asked for first because a scope is a level of the world and its
     * name appears in the breadcrumb, the scope list and every way named after it.
     * `prompt` rather than a modal: this is one field, and the painter is already
     * a modal over a canvas.
     */
    /**
     * Paint a building type's plan into this scope (task-567).
     *
     * The point of the prompt's wording is that this is a *draft*: the plan goes
     * in as paint, the scope stays unmade, and the author edits the cells (with
     * the rail's marquee, if they like) before running ⚙ Generate. So the button
     * says "paint" and the status says what happened, rather than either of them
     * claiming an interior was built.
     */
    async function paintInterior(): Promise<void> {
        const p = state.payload!;
        const vocab = state.vocab!;
        const options = (vocab.b ? vocab.b : (vocab.biomes || []))
            .filter((r) => (r.tags || []).indexOf('building') >= 0)
            .map((r) => r.id || '');
        if (!options.length) {
            _status('No building types in the vocabulary.', true);
            return;
        }
        const pick = window.prompt(
            `Paint which building's interior into "${p.scope.name}"?\n\n`
            + options.join(', '),
            options.indexOf('inn') >= 0 ? 'inn' : options[0]);
        if (!pick || !options.indexOf(pick)) {
            if (pick) _status(`${pick} is not a building type.`, true);
            return;
        }
        try {
            const res = await _post(
                `/${encodeURIComponent(p.scope.id)}/grid/interior`, { building: pick });
            state.payload = res;
            const notes = (res.report && res.report.notes) || [];
            _status(`Painted the ${pick} plan — edit the cells, then ⚙ Generate.`);
            for (let i = 0; i < Math.min(notes.length, 2); i += 1) {
                _status(notes[i]);
            }
            _notify(true);
            render();
        } catch (e) {
            _status(`Could not paint that interior: ${errText(e)}`, true);
        }
    }

    async function promoteArea(areaId: string): Promise<void> {
        const p = state.payload!;
        // The area is a row of `area_placements` (id/name/x/y) — the payload
        // carries no `areas` list, so looking there found nothing and returned
        // silently, leaving the button a no-op with no prompt and no request.
        const area = ((p.area_placements || []).find((a) => a.id === areaId))
            || ((p.unplaced_areas || []).find((a) => a.id === areaId));
        if (!area) {
            _status(`No area '${areaId}' on this map to make a scope of.`, true);
            return;
        }
        const defaultName = `${area.name} interior`;
        const name = (window.prompt(
            'Name for the new child scope:', defaultName) || '').trim();
        if (!name) return;
        const hasCell = Number.isInteger(area.x) && Number.isInteger(area.y);
        const body: Record<string, unknown> = {
            scope_id: (window.prompt(
                'Id for the new scope (lower-case, no spaces):',
                _slug(name)) || '').trim() || _slug(name),
            name,
            area_ids: [areaId],
            parent_id: p.scope.id,
            entry_area_id: areaId,
            mode: 'interior',
        };
        if (hasCell) body.cell = { x: area.x, y: area.y };
        try {
            const res = await _post_root('/api/world/promote', body);
            state.selectedArea = null;
            // The parent grid is what moved (a placement appeared, an area left),
            // so the whole payload is re-read rather than patched by hand.
            await _reloadPayload();
            _status(`"${res.name}" is now a scope of its own, entered from `
                + `${hasCell ? `cell (${area.x},${area.y})` : 'nowhere yet'}.`);
_notify(true);
        } catch (e) {
            _status(`Promote failed: ${errText(e)}`, true);
        }
    }

    /** A scope id: lower-case, dashes, no leading or trailing separator. */
    function _slug(text: unknown): string {
        return String(text || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .slice(0, 40) || 'scope';
    }

    /** Cells an N×N brush covers, clipped to the grid. */
    function _brushCells(p: WpPayload, x: number, y: number): WpCell[] {
        const n = Math.max(1, state.brush | 0);
        const off = Math.floor((n - 1) / 2);
        const out: WpCell[] = [];
        for (let dy = 0; dy < n; dy += 1) {
            for (let dx = 0; dx < n; dx += 1) {
                const cx = x - off + dx;
                const cy = y - off + dy;
                if (cx >= 0 && cy >= 0 && cx < p.grid!.w && cy < p.grid!.h) {
                    out.push({ x: cx, y: cy });
                }
            }
        }
        return out;
    }

    async function _paintAt(p: WpPayload, x: number, y: number): Promise<void> {
        const value = state.tool === 'erase' ? null : state.value;
        if (state.tool === 'paint' && (value == null || value === '')) {
            _status('Pick a paint value, or use Erase.');
            return;
        }
        const cells = _brushCells(p, x, y);
        try {
            if (cells.length === 1) {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint`,
                    { layer: state.layer, x, y, value });
            } else {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                    { edits: cells.map((c) => ({ layer: state.layer, x: c.x, y: c.y, value })) });
            }
            _notify(true);
            render();
        } catch (e) {
            _status(`Paint failed: ${errText(e)}`, true);
        }
    }

    async function placeFeature(childId: string, x: number, y: number,
            onOverlap?: string): Promise<void> {
        const p = state.payload!;
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/place`,
                { child_id: childId, x, y, on_overlap: onOverlap || 'forbid' });
            _notify(true);
            render();
        } catch (e) {
            if (!onOverlap && /already holds/.test(errText(e))
                    && window.confirm(`${errText(e)}\n\nDisplace the occupant?`)) {
                return placeFeature(childId, x, y, 'displace');
            }
            _status(`Place failed: ${errText(e)}`, true);
        }
    }

    async function removeFeature(childId: string): Promise<void> {
        try {
            state.payload = await _post(
                `/${encodeURIComponent(state.payload!.scope.id)}/grid/remove`,
                { child_id: childId });
            state.selectedChild = null;
            _notify(true);
            render();
        } catch (e) {
            _status(`Remove failed: ${errText(e)}`, true);
        }
    }

    /** Rename a scope's display name (its id, and every node reference, stays). */
    async function renameScope(scopeId: string, currentName?: string | null): Promise<void> {
        const name = window.prompt('Rename scope:', currentName || scopeId);
        if (name == null) return;
        const clean = name.trim();
        if (!clean || clean === currentName) return;
        try {
            await _post(`/${encodeURIComponent(scopeId)}/rename`, { name: clean });
            _notify(true);
            // A renamed *child* is a card in this scope's list, and the card's
            // name lives in the payload — refetch it. `render()` alone redrew the
            // stale list and the card kept its old label. Renaming the open scope
            // itself needs a full load (its title/breadcrumb changed).
            if (state.scopeId === scopeId) await load(scopeId);
            else await _reloadPayload();
            _status(`Renamed to “${clean}”.`, false);
        } catch (e) {
            _status(`Rename failed: ${errText(e)}`, true);
        }
    }

    /**
     * Delete a scope. Refuses one that still has children (delete those first);
     * a generated scope's areas/ways/items go with it. If it was the open scope,
     * fall back to its parent.
     */
    async function deleteScope(scopeId: string, name?: string | null): Promise<void> {
        const label = name || scopeId;
        if (!window.confirm(`Delete scope “${label}”?\n\n`
            + `This removes the scope, unplaces it, and deletes the areas/ways/items `
            + `generated for it. Scopes that still have children must be emptied first.`)) {
            return;
        }
        const trail = (state.payload && state.payload.breadcrumb) || [];
        const parentId = trail.length > 1 ? trail[trail.length - 2].id : null;
        try {
            const result = await _post(`/${encodeURIComponent(scopeId)}/delete`, {});
            _notify(true);
            if (state.scopeId === scopeId) {
                if (parentId) load(parentId); else open(null);
            } else {
                // Deleted scope was a card here: refetch so the card disappears.
                await _reloadPayload();
            }
            _status(`Deleted “${label}” (${result.deleted_nodes || 0} generated node(s)).`, false);
        } catch (e) {
            _status(`Delete failed: ${errText(e)}`, true);
        }
    }

    async function _promptNewScope(parentId: string | null): Promise<void> {
        const name = window.prompt('Feature name:', 'New feature');
        if (!name) return;
        const mode = parentId && state.payload
            ? GM().nextMode(state.payload.mode) : 'world';
        const body: Record<string, unknown> = { name, parent_id: parentId || null, mode };
        if (state.payload && state.payload.grid) {
            body.w = Math.max(1, Math.min(8, state.payload.grid.w));
            body.h = Math.max(1, Math.min(8, state.payload.grid.h));
        }
        try {
            const created = await _post('', body);
            _notify(true);
            if (parentId && state.payload) {
                state.selectedChild = created.scope.id;
                // Re-open the parent so the new child appears in its list.
                state.payload = await _req(
                    `${BASE}/${encodeURIComponent(parentId)}/grid`, { cache: 'no-store' });
                render();
                _status(`Created “${created.scope.name}” — pick Feature and click a cell to place it.`);
            } else {
                load(created.scope.id);
            }
        } catch (e) {
            _status(`Create failed: ${errText(e)}`, true);
        }
    }

    function _openGridDialog(p: WpPayload): void {
        const wrap = _el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;' +
            'padding:8px;border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;');
        const cur = p.grid || { w: 10, h: 10 };
        const mk = (name: string, val: string | number, width?: number): HTMLInputElement => {
            wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', name));
            const inp = _el('input',
                `width:${width || 56}px;padding:3px 6px;border-radius:5px;border:1px solid ` +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            inp.value = String(val);
            wrap.appendChild(inp);
            return inp;
        };
        const wIn = mk('w', cur.w);
        wIn.setAttribute('data-role', 'wp-grid-w');
        const hIn = mk('h', cur.h);
        hIn.setAttribute('data-role', 'wp-grid-h');
        // Presets sized in *turns*: 1 cell = 1 turn, 60 turns/hour. A two-route
        // region (e.g. two 240-cell trails) needs roughly this much canvas.
        const PRESETS: [string, number, number][] = [
            ['region 160×100', 160, 100], ['wide 180×70', 180, 70], ['small 60×60', 60, 60],
        ];
        PRESETS.forEach(([label, pw, ph]) => {
            wrap.appendChild(_btn(label, () => { wIn.value = String(pw); hIn.value = String(ph); refreshWarn(); },
                'padding:2px 6px;font-size:11px;'));
        });
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'mode'));
        const modeSel = _el('select', 'padding:3px;border-radius:5px;');
        modeSel.setAttribute('data-role', 'wp-grid-mode');
        GM().MODES.forEach((m: *FIX*) => {
            const opt = _el('option', null, m);
            opt.value = m;
            if (m === (p.mode || 'world')) opt.selected = true;
            modeSel.appendChild(opt);
        });
        wrap.appendChild(modeSel);

        const warn = _el('span', 'font-size:11px;color:#c96;');
        wrap.appendChild(warn);
        const refreshWarn = (): void => {
            const w = parseInt(wIn.value, 10), h = parseInt(hIn.value, 10);
            if (!w || !h || w < 1 || h < 1) { warn.textContent = 'w and h must be ≥ 1'; return; }
            const pr = GM().pruneGrid(p, w, h);
            const lost = GM().PAINT_LAYERS.reduce((n: number, l: *FIX*) =>
                n + Object.keys((p.layers || {})[l] || {}).length, 0) - pr.paintKept;
            const lostP = (p.placements || []).length - pr.placementsKept;
            warn.textContent = (lost > 0 || lostP > 0)
                ? `shrink drops ${lost} paint cell(s), ${lostP} placement(s)` : '';
        };
        [wIn, hIn].forEach((i) => i.addEventListener('input', refreshWarn));
        refreshWarn();

        wrap.appendChild(_btn('Apply', async () => {
            try {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid`, {
                    w: parseInt(wIn.value, 10),
                    h: parseInt(hIn.value, 10),
                    mode: modeSel.value,
                });
                _notify(true);
                render();
            } catch (e) {
                _status(`Grid failed: ${e instanceof Error ? e.message : String(e)}`, true);
            }
        }));
        wrap.appendChild(_btn('Cancel', () => wrap.remove()));
        // Live at the bottom of the open panel so Apply/Cancel are always reachable.
        state.body!.appendChild(wrap);
    }

    /**
     * Dialog to import a greyscale heightmap image into the floor layer (task-877).
     *
     * Converts pixel luminance (0..255) to metres in range [blackM, whiteM],
     * then to whole storeys via round(metres / metresPerStorey).
     * Resamples the image to the grid dimensions (w × h).
     * Calculates the count of neighbouring pairs exceeding the scope's climb threshold.
     * Commits as a single paint_batch undo step.
     */
    function _openHeightmapImportDialog(p: WpPayload): void {
        const existing = state.body!.querySelector('[data-role="wp-heightmap-dialog"]');
        if (existing) existing.remove();

        const wrap = _el('div', 'display:flex;flex-direction:column;gap:8px;padding:12px;' +
            'border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;' +
            'background:var(--bg-card,#23232b);box-shadow:0 4px 16px rgba(0,0,0,0.4);');
        wrap.setAttribute('data-role', 'wp-heightmap-dialog');

        const head = _el('div', 'display:flex;align-items:center;justify-content:space-between;');
        head.appendChild(_el('span', 'font-weight:600;font-size:13px;', 'Import Heightmap (Floor Layer)'));
        head.appendChild(_btn('✕', () => wrap.remove(), 'padding:2px 8px;font-size:11px;', 'Close'));
        wrap.appendChild(head);

        const grid = p.grid || { w: 10, h: 10 };
        const metresPerStorey = (state.vocab && state.vocab.metres_per_storey) || 3;
        const scope*FIX* = p.scope as *FIX*;
        const climbThreshold = (scope*FIX* && scope*FIX*.climb && scope*FIX*.climb.max_storey_step) != null
            ? Number(scope*FIX*.climb.max_storey_step) : 3;

        const info = _el('div', 'font-size:11px;color:var(--text-muted,#999);',
            `Grid size: ${grid.w}×${grid.h} · 1 storey step = ${metresPerStorey}m · Climb threshold: >${climbThreshold} storeys (${climbThreshold * metresPerStorey}m)`);
        wrap.appendChild(info);

        const fileRow = _el('div', 'display:flex;align-items:center;gap:8px;');
        const fileInput = _el('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.setAttribute('data-role', 'wp-heightmap-file');
        fileRow.appendChild(fileInput);
        wrap.appendChild(fileRow);

        const rangeRow = _el('div', 'display:flex;align-items:center;gap:12px;flex-wrap:wrap;');
        const mkNum = (label: string, defVal: number, role: string): HTMLInputElement => {
            rangeRow.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', label));
            const inp = _el('input',
                'width:64px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            inp.type = 'number';
            inp.value = String(defVal);
            inp.setAttribute('data-role', role);
            rangeRow.appendChild(inp);
            return inp;
        };
        const blackInput = mkNum('Black (m):', 0, 'wp-heightmap-black');
        const whiteInput = mkNum('White (m):', 60, 'wp-heightmap-white');
        wrap.appendChild(rangeRow);

        const previewBox = _el('div', 'font-size:11px;color:var(--text-muted,#999);padding:6px;' +
            'background:var(--bg-dark,#1a1a20);border-radius:4px;min-height:36px;line-height:1.45;');
        previewBox.setAttribute('data-role', 'wp-heightmap-preview');
        previewBox.textContent = 'Select an image to preview conversion.';
        wrap.appendChild(previewBox);

        let parsedFloorEdits: { layer: string; x: number; y: number; value: number }[] | null = null;

        const updatePreview = (img: HTMLImageElement): void => {
            const minM = parseFloat(blackInput.value) || 0;
            const maxM = parseFloat(whiteInput.value) || 0;
            const canvas = document.createElement('canvas');
            canvas.width = grid.w;
            canvas.height = grid.h;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            ctx.drawImage(img, 0, 0, grid.w, grid.h);
            const imgData = ctx.getImageData(0, 0, grid.w, grid.h).data;

            const floorMap: Record<string, number> = {};
            const edits: { layer: string; x: number; y: number; value: number }[] = [];
            let minStorey = Infinity;
            let maxStorey = -Infinity;

            for (let y = 0; y < grid.h; y += 1) {
                for (let x = 0; x < grid.w; x += 1) {
                    const idx = (y * grid.w + x) * 4;
                    const r = imgData[idx];
                    const g = imgData[idx + 1];
                    const b = imgData[idx + 2];
                    const lum = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
                    const metres = GM().luminanceToMetres(lum, minM, maxM);
                    const storeys = GM().metresToStoreys(metres, metresPerStorey);
                    const k = GM().cellKey(x, y);
                    floorMap[k] = storeys;
                    edits.push({ layer: 'floor', x, y, value: storeys });
                    if (storeys < minStorey) minStorey = storeys;
                    if (storeys > maxStorey) maxStorey = storeys;
                }
            }
            parsedFloorEdits = edits;

            const climbCliffs = GM().climbGatedSteps(grid, floorMap, climbThreshold);
            previewBox.*FIX*= `Metres: <b>${minM}m</b> to <b>${maxM}m</b><br>`
                + `Storeys: <b>${minStorey === Infinity ? 0 : minStorey}</b> to <b>${maxStorey === -Infinity ? 0 : maxStorey}</b><br>`
                + `Climb-gated steps (> ${climbThreshold} storeys): <b>${climbCliffs}</b> cell pairs`;
        };

        let loadedImage: HTMLImageElement | null = null;
        fileInput.addEventListener('change', () => {
            const file = fileInput.files && fileInput.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (ev) => {
                const img = new Image();
                img.onload = () => {
                    loadedImage = img;
                    updatePreview(img);
                };
                img.src = String(ev.target && ev.target.result);
            };
            reader.readAsDataURL(file);
        });

        [blackInput, whiteInput].forEach((inp) => inp.addEventListener('input', () => {
            if (loadedImage) updatePreview(loadedImage);
        }));

        const actions = _el('div', 'display:flex;gap:8px;justify-content:flex-end;margin-top:4px;');
        const applyBtn = _btn('Apply to floor layer', async () => {
            if (!parsedFloorEdits || !parsedFloorEdits.length) {
                _status('No heightmap image loaded.', true);
                return;
            }
            try {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, {
                    edits: parsedFloorEdits,
                });
                wrap.remove();
                _notify(true);
                render();
                _status(`Heightmap imported: painted ${parsedFloorEdits.length} cells to floor layer.`, false);
            } catch (e) {
                _status(`Heightmap import failed: ${e instanceof Error ? e.message : String(e)}`, true);
            }
        }, 'font-weight:600;');
        applyBtn.setAttribute('data-role', 'wp-heightmap-apply');
        actions.appendChild(applyBtn);
        actions.appendChild(_btn('Cancel', () => wrap.remove()));
        wrap.appendChild(actions);

        state.body!.appendChild(wrap);
    }

    /**
     * Dialog to export the current floor layer as a greyscale PNG (task-877).
     */
    function _openHeightmapExportDialog(p: WpPayload): void {
        const existing = state.body!.querySelector('[data-role="wp-heightmap-dialog"]');
        if (existing) existing.remove();

        const wrap = _el('div', 'display:flex;flex-direction:column;gap:8px;padding:12px;' +
            'border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;' +
            'background:var(--bg-card,#23232b);box-shadow:0 4px 16px rgba(0,0,0,0.4);');
        wrap.setAttribute('data-role', 'wp-heightmap-dialog');

        const head = _el('div', 'display:flex;align-items:center;justify-content:space-between;');
        head.appendChild(_el('span', 'font-weight:600;font-size:13px;', 'Export Heightmap (Floor Layer)'));
        head.appendChild(_btn('✕', () => wrap.remove(), 'padding:2px 8px;font-size:11px;', 'Close'));
        wrap.appendChild(head);

        const grid = p.grid || { w: 10, h: 10 };
        const metresPerStorey = (state.vocab && state.vocab.metres_per_storey) || 3;
        const floorMap = (p.layers && p.layers.floor) || {};

        let minStorey = 0;
        let maxStorey = 0;
        for (let y = 0; y < grid.h; y += 1) {
            for (let x = 0; x < grid.w; x += 1) {
                const rawVal = floorMap[GM().cellKey(x, y)];
                const s = rawVal != null ? Number(rawVal) : 0;
                if (s < minStorey) minStorey = s;
                if (s > maxStorey) maxStorey = s;
            }
        }
        const minM = GM().storeysToMetres(minStorey, metresPerStorey);
        const maxM = GM().storeysToMetres(maxStorey, metresPerStorey);

        const info = _el('div', 'font-size:11px;color:var(--text-muted,#999);',
            `Grid: ${grid.w}×${grid.h} · Storeys: ${minStorey} to ${maxStorey} · Metres: ${minM}m to ${maxM}m`);
        wrap.appendChild(info);

        const rangeRow = _el('div', 'display:flex;align-items:center;gap:12px;flex-wrap:wrap;');
        const mkNum = (label: string, defVal: number, role: string): HTMLInputElement => {
            rangeRow.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', label));
            const inp = _el('input',
                'width:64px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            inp.type = 'number';
            inp.value = String(defVal);
            inp.setAttribute('data-role', role);
            rangeRow.appendChild(inp);
            return inp;
        };
        const blackInput = mkNum('Black (m):', minM, 'wp-heightmap-export-black');
        const whiteInput = mkNum('White (m):', Math.max(minM + 3, maxM), 'wp-heightmap-export-white');
        wrap.appendChild(rangeRow);

        const actions = _el('div', 'display:flex;gap:8px;justify-content:flex-end;margin-top:4px;');
        const exportBtn = _btn('Download Heightmap PNG', () => {
            const expMinM = parseFloat(blackInput.value) || 0;
            const expMaxM = parseFloat(whiteInput.value) || (expMinM + 3);

            const canvas = document.createElement('canvas');
            canvas.width = grid.w;
            canvas.height = grid.h;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            const imgData = ctx.createImageData(grid.w, grid.h);
            for (let y = 0; y < grid.h; y += 1) {
                for (let x = 0; x < grid.w; x += 1) {
                    const idx = (y * grid.w + x) * 4;
                    const s = floorMap[GM().cellKey(x, y)] != null ? floorMap[GM().cellKey(x, y)] : 0;
                    const m = GM().storeysToMetres(s, metresPerStorey);
                    const lum = GM().metresToLuminance(m, expMinM, expMaxM);
                    imgData.data[idx] = lum;
                    imgData.data[idx + 1] = lum;
                    imgData.data[idx + 2] = lum;
                    imgData.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(imgData, 0, 0);

            const link = document.createElement('a');
            link.download = `heightmap_${p.scope.id}_${expMinM}m_to_${expMaxM}m.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
            wrap.remove();
            _status(`Heightmap exported (${grid.w}×${grid.h}, ${expMinM}m to ${expMaxM}m).`, false);
        }, 'font-weight:600;');
        exportBtn.setAttribute('data-role', 'wp-heightmap-download');
        actions.appendChild(exportBtn);
        actions.appendChild(_btn('Cancel', () => wrap.remove()));
        wrap.appendChild(actions);

        state.body!.appendChild(wrap);
    }

    function _status(text: string, isError?: boolean): void {
        state.status = text;
        state.statusError = !!isError;
        _log((isError ? '⚠ ' : '') + text, isError ? 'error-msg' : 'system-msg');
        _updateStatusBar();
    }

    window.VW = window.VW || {};
    window.VW.worldPainter = { open, close, refresh: () => (state.scopeId ? load(state.scopeId) : showChooser()) };
    window.worldPainter = window.VW.worldPainter;
})();
