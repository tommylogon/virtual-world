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

    /** The backend vocabulary document (`/api/world/painter/vocabulary`). */
    interface WpVocab {
        biomes?: WpPaletteEntry[];
        features?: WpPaletteEntry[];
        /** Short aliases the vocabulary endpoint also answers with. */
        b?: WpPaletteEntry[];
        f?: WpPaletteEntry[];
        layers?: unknown[];
        modes?: unknown[];
    }

    /** One preflight finding from `engine/world_compile.preflight`. */
    interface WpBlocker {
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
        scope: { id: string; name?: string; has_grid?: boolean; mode?: string; state?: string };
        grid?: { w: number; h: number; cell_scale?: number };
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

    /** In-progress grid-frame drag (task-597): move the scope, or resize it. */
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

    /** One pickable group in the place tool's dropdown (grid-model.areaGroups). */
    interface WpAreaGroup {
        key: string;
        label: string;
        areas: { id: string; name: string; placedHere?: { x: number; y: number } | null }[];
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
        /** Detaches the document-level grid-drag listeners, if any are attached. */
        gridDragRelease: (() => void) | null;
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
        /** `{scale}` — Konva owns the live transform. */
        view: { x?: number; y?: number; scale: number } | null;
        route: WpCell[];
        stage: WpKonvaStage | null;
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
     * this is the one narrowing — the non-Error branch keeps the old
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
// `SCOPES_URL` is what any scope *picker* should use; `BASE` stays for the
// per-scope grid payloads that expect the nested shape.
const SCOPES_URL = '/api/world/scopes?flat=1';
    const CELL = 22;           // base px per cell at scale 1
    // The zoom floor is a *legibility* floor, not an arithmetic one (task-595).
    // `_drawGridLines` stops drawing the lattice below 4px per cell, so at the
    // old 0.12 (< 3px per cell) the grid dissolved into a smear of paint blobs
    // and the author could not tell a road from a field. 0.25 keeps a cell at
    // 5.5px — lines still drawn, a 160-cell world still fits an 880px pane — so
    // zooming out to the floor leaves a readable map rather than a blank one.
    const MIN_SCALE = 0.25;
    const MAX_SCALE = 6;
    // main.js reloads the VW namespace last, so prefer the bare global it keeps.
    const GM = () => window.gridModel || window.VW.gridModel;

    const state: WpState = {
        scopeId: null,
        payload: null,
        tool: 'paint',
        layer: 'biome',
        value: 'sparse_forest',
        brush: 1,
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
        view: null,            // {scale} — Konva owns the live transform
        route: [],             // waypoints for the route/trail tool
        stage: null,
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
     * `any` on the way out on purpose: the answer is whatever JSON the route
     * answered with, and the callers either store it as the next payload or read
     * two or three fields off it. `unknown` would push a cast to every one of
     * them for no gain.
     */
    async function _req(url: string, options?: RequestInit): Promise<any> {
        const resp = await fetch(url, options);
        let data: any = null;
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
        // `worldSync` is a top-level `const` in world-sync.js, so `window.worldSync`
        // is undefined at runtime and this branch has never fired — main.js puts
        // the instance on `VW.worldSync`. Kept as-is rather than "fixed": the cast
        // documents what the guard actually reads, and changing the lookup is a
        // behaviour change this conversion did not ask for.
        const win = window as unknown as { worldSync?: { refresh(): void } };
        if (worldChanged && win.worldSync && typeof win.worldSync.refresh === 'function') {
            win.worldSync.refresh();
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

    async function ensureVocab(): Promise<WpVocab | null> {
        if (state.vocab) return state.vocab;
        try {
            state.vocab = await _req('/api/world/painter/vocabulary', { cache: 'no-store' });
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

    /**
     * The values the current layer may be painted with, in the **vocabulary's own
     * shape** — `{id, name, tags}` — because that is what the palette groups, the
     * select renders (`${o.name} (${o.id})`) and `_defaultValueForLayer` reads
     * (`o.id`). Wrapping them as `{value, label}` here would have every consumer
     * reading `undefined` and a dropdown full of it.
     */
    function _layerOptions(layer: string): WpPaletteEntry[] {
        const vocab = state.vocab || {};
        if (layer === 'biome') return (vocab.b || vocab.biomes || []).slice();
        if (layer === 'road') return (vocab.f || vocab.features || []).slice();
        if (layer === 'climate') {
            // Shaped like a record so one renderer serves every layer, with the
            // base °C in the name because that number is the whole point of
            // painting it (task-557) and it otherwise lives only in the report.
            return GM().CLIMATE_IDS.map((id: string) => {
                const c = GM().CLIMATES[id] || {};
                return {
                    id,
                    name: `${c.label} (${c.base}°C)`,
                    tags: ['climate'],
                };
            });
        }
        return [];
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
     * The biome palette, split so a town can be painted (task-561).
     *
     * 47 biomes in one column is unpickable, and the author's question when
     * painting a settlement is not "which biome" but "which *building*". So
     * building types are gathered into one section and sorted by their category
     * (residential, religious, commercial, civic, craft, military, industrial,
     * rural, transport), with the wild terrain above it where it already was. The
     * sections render as real `<optgroup>` elements -- a `<select>` nests them
     * natively -- so the palette is 130 options under ~25 headings rather than
     * 130 flat rows separated by un-paintable dash text.
     *
     * **Rooms** get the same treatment for the same reason, and it matters more
     * here: the indoor vocabulary is *purpose* first (where does a person sleep,
     * where do they cook) and an author drawing a floor plan is asking exactly
     * that question, not "which of the 80 biomes". Rooms sit between the wild
     * terrain and the buildings, because a plan is where terrain gives way to
     * rooms and a building is the thing you arrive at.
     */
    function _biomePalette(layer: string): WpPaletteEntry[] {
        const options = _layerOptions(layer);
        if (layer !== 'biome') return options.map((o) => ({ ...o, group: null }));
        const CATEGORIES = ['residential', 'religious', 'commercial', 'civic',
            'craft', 'industrial', 'military', 'rural', 'transport'];
        // A room's purpose, in the order a plan is drawn: arrive, move, then
        // the rooms you pass. Circulation first because it is what everything else
        // connects to, and the two "why people gather" purposes (living, civic)
        // before the service ones, which is the order a reader thinks in.
        const ROOM_PURPOSES = ['circulation', 'living', 'sleeping', 'cooking',
            'eating', 'storage', 'workshop', 'worship', 'records', 'study',
            'trade', 'civic', 'service', 'outdoor'];
        const wild: WpPaletteEntry[] = [];
        const rooms = new Map<string, WpPaletteEntry[]>(
            ROOM_PURPOSES.map((c) => [c, [] as WpPaletteEntry[]] as [string, WpPaletteEntry[]]));
        const buildings = new Map<string, WpPaletteEntry[]>(
            CATEGORIES.map((c) => [c, [] as WpPaletteEntry[]] as [string, WpPaletteEntry[]]));
        const structure: WpPaletteEntry[] = [];
        for (const option of options) {
            const tags = (option.tags || []).map((t) => String(t).toLowerCase());
            // Structure — wall, void, window, door, stairway — is neither terrain
            // nor a room nor a building, and it is what makes a floor plan mean
            // anything (task-562/568), so it gets its own section rather than
            // being sorted by its category.
            if (tags.includes('not_a_place')) { structure.push({ ...option, group: null }); continue; }
            if (tags.includes('indoor')) {
                const purpose = ROOM_PURPOSES.find((c) => tags.includes(c)) || 'other';
                if (!rooms.has(purpose)) rooms.set(purpose, []);
                rooms.get(purpose)!.push({ ...option, group: purpose });
                continue;
            }
            if (!tags.includes('building')) { wild.push({ ...option, group: null }); continue; }
            const category = CATEGORIES.find((c) => tags.includes(c)) || 'other';
            if (!buildings.has(category)) buildings.set(category, []);
            buildings.get(category)!.push({ ...option, group: category });
        }
        const out: WpPaletteEntry[] = wild.slice();
        if ([...rooms.values()].some((g) => g.length)) {
            out.push({ section: 'Rooms' });
            for (const purpose of [...ROOM_PURPOSES, 'other']) {
                const group = rooms.get(purpose);
                if (!group || !group.length) continue;
                out.push({ section: `${purpose[0].toUpperCase()}${purpose.slice(1)}` });
                out.push(...group);
            }
        }
        if (out.length) out.push({ section: 'Buildings' });
        for (const category of [...CATEGORIES, 'other']) {
            const group = buildings.get(category);
            if (!group || !group.length) continue;
            out.push({ section: `${category[0].toUpperCase()}${category.slice(1)}` });
            out.push(...group);
        }
        if (structure.length) {
            out.push({ section: 'Structure' });
            out.push(...structure);
        }
        return out;
    }

    function _defaultValueForLayer(layer: string): string {
        // The floor layer is a *storey index* (engine/world_grid.py): 0 is ground,
        // so 1 — "one storey up" — is the only useful value to start dragging
        // with. It used to default to a 0..1 height fraction, which is not a
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
            'background:var(--bg-panel,#1b1b21);color:var(--text,#ddd);border:1px solid ' +
            'var(--border,#444);border-radius:10px;width:min(1000px,94vw);max-height:92vh;' +
            'display:flex;flex-direction:column;padding:14px;font-size:13px;box-shadow:0 12px 40px rgba(0,0,0,0.55);');
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
            // `_valueControl`/`_layerSelect`), but the guard has to hold anyway:
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
        state.scopeId = scopeId;
        state.selectedChild = null;
        state.view = null;      // a new scope opens fitted
        state.route = [];
        state.refEdit = false;  // reference adjust is per-scope
        state.refDrag = null;
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
        // 0 — so reading it afterwards silently threw the view back to the top.
        // Only a box whose position has actually been applied is trusted, and only if it
        // can scroll. Two things make a capture wrong: an intermediate "Loading
        // grid…" shell has no overflow, and a second render inside the same task
        // sees the newest box before its scrollTop is applied — both report 0 and
        // would overwrite the author's real position.
        if (state.scrollBox && state.scrollRestored
                && state.scrollBox.scrollHeight > state.scrollBox.clientHeight) {
            state.scrollTop = state.scrollBox.scrollTop;
        }
        // Only ever called from open(), which assigns state.body before anything
        // renders; the assertion states that rather than re-testing it.
        const panel = state.body!;
        panel.textContent = '';
        const head = _el('div', 'display:flex;align-items:center;gap:10px;margin-bottom:10px;');
        head.appendChild(_el('div', 'font-weight:700;font-size:15px;', title));
        const spacer = _el('div', 'flex:1;');
        head.appendChild(spacer);
        head.appendChild(_btn('Close', close));
        panel.appendChild(head);
        const box = _el('div', 'overflow:auto;');
        panel.appendChild(box);
        state.scrollBox = box;
        // Restore AFTER the content is in. load() calls this while the box is
        // still empty, and scrollTop on an element with nothing to scroll is
        // clamped to 0 — so setting it here stored 0 and lost the position. One
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
        // Rail beside the canvas, not above it: the tool column and the map it
        // acts on are read together, and the map gets the width back (task-536).
        const withRail = _el('div', 'display:flex;gap:10px;align-items:flex-start;');
        withRail.appendChild(_toolRail(p));
        withRail.appendChild(_grid(p));
        box.appendChild(withRail);
        const panel = _cellPanel(p);
        if (panel) box.appendChild(panel);
        // The "what next" checklist sits below the map, not above it. The canvas
        // is the thing being looked at, and a collapsed progress bar wedged
        // between the toolbar and the art was the only thing standing between an
        // author and their paint — so it now reports from under the image.
        box.appendChild(_checklist(p));
        _renderChildren(box, p);
        if (state.status) {
            const color = state.statusError ? '#e66' : '#9c9';
            const status = _el('div', `margin-top:8px;font-size:12px;color:${color};`, state.status);
            status.setAttribute('data-role', 'wp-status');
            box.appendChild(status);
        }
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
        ['paint', '🖌 Paint', 'P', 'Paint the current layer and value. Drag to stroke.'],
        ['erase', '🧽 Erase', 'E', 'Clear the current layer on a cell. Drag to stroke.'],
        ['move', '✥ Move', 'M',
            'Shift the selected cells\' contents one cell. Arrow keys, or WASD, '
            + 'or the nudge buttons. Clamped to the grid; one request, one undo.'],
        ['route', '🧭 Route', 'R', 'Click waypoints, then ✓ Paint route — paints the '
            + 'current layer along the line (1 cell = 1 turn).'],
        ['feature', '🏠 Feature', 'F', 'Place a sub-zone (child scope) at a cell — not a '
            + 'road. Roads/bridges are painted on the road layer.'],
        ['area', '📍 Area', 'A', 'Put an area you already wrote (Northern Hills, Murk '
            + 'Lake…) on a cell of this map. Pick the area, then click where '
            + 'it belongs. Generate will not put a second area on that cell.'],
        ['inspect', '🔍 Inspect', 'I', 'Read a cell without changing it: what is painted '
            + 'on it, and which area or child scope sits there. Right-click does the '
            + 'same on any tool.'],
    ];

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
            // buttons with hover strings and no coach card behind any of them.
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
        _syncDraggable();
        render();
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
        // click it, their choice sticks — an author who collapsed it to get on
        // with painting should not have it pop back open on the next stroke.
        if (!state.checklistTouched) {
            state.checklistOpen = done === 0 || !_paintedCount(p);
        }
        const toggle = _btn(
            allDone ? '✔ all done' : `📋 ${done}/${steps.length} — what next`,
            () => {
                state.checklistOpen = !state.checklistOpen;
                state.checklistTouched = true;
                render();
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
        if (mode === 'town') {
            return 'A town is painted inside-out: the ground it stands on, the streets '
                + 'across it, the wall around it, then the buildings on it, then the '
                + 'names that make them addressable. Every painted cell becomes a '
                + 'place; walls are structure and never do, which is what makes them '
                + 'walls.';
        }
        if (mode === 'interior') {
            return 'An interior is a floor plan. Paint rooms, join them with doors, '
                + 'put a storey number where the level changes, and name the rooms — '
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

        const grid = {
            title: 'Size the grid.',
            how: 'One cell is one minute of walking, so the size is how long the '
                + 'place takes to cross. ▦ Grid… sets it.',
            done: !!p.scope.has_grid,
        };
        const ground = {
            title: 'Paint the ground.',
            how: 'Biome layer, a big brush, dragged over the area. Tick "merge '
                + 'same-biome" or every cell becomes its own area.',
            done: biomeCells.length > 0,
        };
        const roads = {
            title: 'Lay the roads.',
            how: 'Road layer, value "road", with the 🧭 Route tool — click '
                + 'waypoints, then ✓ Paint route.',
            done: roadCells.length > 0,
        };
        const namesStep = {
            title: 'Name the places.',
            how: 'Right-click a cell, use the name field. A place with no name '
                + 'compiles to "Inn (Eldenford 12,7)" and cannot be asked for.',
            done: names > 0 && names >= (biomeCells.length + roadCells.length) * 0.5,
        };
        const generate = {
            title: 'Generate.',
            how: 'Turns the painted cells into real areas and ways. Do it last, '
                + 'and generate the parent before its children so the gateways '
                + 'between them get minted.',
            done: generated,
            note: 'already generated — Ungenerate to start over',
        };
        const reference = {
            title: 'Line the art up.',
            how: 'Load a reference image, then ▦ match so the grid takes the '
                + "image's aspect and a cell is the same place in both.",
            done: !!(p.reference && p.reference.image),
        };

        if (mode === 'town') {
            return [grid, ground, roads,
                { title: 'Wall it in.', how: 'Biome layer, value "wall", along the '
                    + 'perimeter. Walls are structure: they never become places, '
                    + 'which is exactly what makes them walls.',
                    done: wallCells > 0 },
                { title: 'Open the gates.', how: 'Road layer, values "gate" and '
                    + '"bridge", on the wall line where a road leaves. This is how '
                    + 'a town gets more than one way in.',
                    done: roadCells.some((k) => /gate|bridge|ford|tunnel/.test(
                        String((layers.road || {})[k] || ''))) },
                { title: 'Place the buildings.', how: 'One cell each, from the '
                    + 'Buildings section of the value list. Buildings never merge, '
                    + 'so a terrace stays a terrace.', done: buildingCells > 0 },
                namesStep,
                { title: 'Give the buildings interiors.', how: '➕ Add feature… '
                    + 'names a child scope (mode becomes interior), then 🏠 Feature '
                    + 'places it on the building\'s cell.', done: children > 0 },
                generate];
        }
        if (mode === 'interior') {
            return [grid, ground, roads, namesStep, generate];
        }
        return [grid, reference, ground, roads, namesStep, generate];
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
            render();
        });
        _help(wrap.appendChild(layerSel), 'wp-layer');
        wrap.appendChild(_help(_valueControl(), 'wp-value')!);

        wrap.appendChild(_btn('▦ Grid…', () => _openGridDialog(p)));
        // Direct manipulation of the grid itself (task-597). The dialog is still
        // there for exact numbers; this is for the common "nudge it and see".
        const gridAdjust = _btn(state.gridEdit ? '✔ grid' : '✥ grid', () => {
            state.gridEdit = !state.gridEdit;
            state.gridDrag = null;
            _gridDragRelease();
            render();
            _status(state.gridEdit
                ? 'Grid adjust: drag the frame to move the scope on the graph map, '
                  + 'drag the E/S/SE handles to resize; click the size (or ▦ Grid…) '
                  + 'to type exact numbers.'
                : 'Grid adjust off.', false);
        }, 'padding:1px 6px;font-size:11px;');
        gridAdjust.title = 'Move the grid on the graph map (drag the frame) or resize it (drag a handle)';
        wrap.appendChild(gridAdjust);
        wrap.appendChild(_btn('➕ Add feature…', () => _promptNewScope(p.scope.id)));

        // Why this scope cannot be compiled yet, and what to do about it
        // (engine/world_compile.preflight). The compiler refuses the same
        // conditions, but it refuses them *after* the click and only states the
        // rule — so a scope promoted from existing areas (always `baked`, never
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
                + 'tap room, kitchen and cellar. It is a draft — edit the cells, '
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
                ? 'This scope cannot be compiled yet — ' + blocked.map((b) => b.text).join(' ')
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
     * One line describing a palette tile (task-596): what it is, and what it
     * does. `rec` is the vocabulary record, which carries the same prose and
     * tags the compiler reads, so the line cannot disagree with the world.
     */
    function _tileDetail(layer: string, rec: WpPaletteEntry): string {
        const name = rec.name || rec.id;
        const desc = (rec.descriptions || [])[0] || '';
        if (layer === 'road') {
            const bits = [desc];
            if ((rec.biomes || []).length) bits.push('crosses ' + (rec.biomes || []).join(', '));
            if (rec.entry_phrase) bits.push(`“${rec.entry_phrase}”`);
            return `${name} — ${bits.filter(Boolean).join(' · ')}`;
        }
        if (layer === 'biome') {
            const tags = (rec.tags || []).map((t) => String(t).toLowerCase());
            let kind = 'place';
            if (tags.includes('not_a_place')) {
                kind = (tags.find((t) => t.indexOf('cell_kind:') === 0) || 'cell_kind:solid')
                    .split(':')[1] || 'solid';
                kind = `not a place (${kind})`;
            } else if (tags.includes('building')) {
                kind = 'building';
            }
            const bits = [desc, kind];
            if (rec.surface) bits.push(`ground ${rec.surface}`);
            if (rec.refusal) bits.push(rec.refusal);
            return `${name} — ${bits.filter(Boolean).join(' · ')}`;
        }
        return `${name} — ${desc}`.replace(/ — $/, '');
    }

    function _valueControl(): HTMLElement {
        const options = _biomePalette(state.layer);
        if (state.layer === 'floor' || !options.filter((o) => !o.separator).length) {
            // No vocabulary (fetch failed) or a numeric layer: free text.
            const input = _el('input',
                'width:130px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            input.setAttribute('data-role', 'wp-value');
            input.value = state.value;
            input.placeholder = state.layer === 'floor' ? '+1 / -1' : 'value';
            input.title = state.layer === 'floor'
                ? 'Storey: 0 is ground, 1 is one up, -1 one down. Unbounded — 3 for a '
                  + 'room three storeys up, 80 for a tower, -900 for a hole.'
                : `Value painted on the ${state.layer} layer.`;
            input.addEventListener('input', () => { state.value = input.value; });
            return input;
        }
        // A real id, not free text — a mistyped biome silently compiles a barren
        // area, so the valid ids are the only choices.
        //
        // task-647: 105 tiles under 23 headings is navigable but not *findable*.
        // An author drawing a 30-location town floor plan is looking for one
        // tile ("Wall", "Door", "Kitchen") and the only way to reach it today is
        // to scroll and read. A filter box narrows the list on name or id as you
        // type, and hides any heading left with nothing under it. Same affordance
        // as the Scenario Manager's filter, where it was the difference between
        // usable and not on a 22-row list.
        const wrap = _el('div', 'display:flex;gap:4px;align-items:center;flex-wrap:wrap;');
        const filter = _el('input',
            'width:120px;padding:3px 6px;border-radius:5px;'
            + 'border:1px solid var(--border,#444);'
            + 'background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
        filter.type = 'search';
        filter.placeholder = 'Filter tiles…';
        filter.title = 'Narrow the palette by tile name or id. Empty shows everything.';
        filter.setAttribute('aria-label', 'Filter tiles by name or id');
        wrap.appendChild(filter);
        // The palette shows the tile as a colour as well as a name (task-596):
        // this is the same colour the map paints, so picking "Wall" vs "Forest"
        // is a decision about the map, not a guess from a label.
        const swatch = _el('span', 'display:inline-block;width:14px;height:14px;' +
            'border-radius:3px;border:1px solid #555;flex:0 0 auto;');
        swatch.setAttribute('data-role', 'wp-value-swatch');
        wrap.appendChild(swatch);
        const sel = _el('select', 'padding:3px;border-radius:5px;min-width:160px;');
        sel.setAttribute('data-role', 'wp-value');
        wrap.appendChild(sel);
        sel.title = `Value painted on the ${state.layer} layer.`;
        // What the highlighted tile *is* and *does* (task-596), without a second
        // panel: the palette used to be a wall of names, so "bridge" and "road"
        // looked interchangeable and a wall looked like a biome. The detail line
        // names the tile's prose, its ground, and — for the road layer — the
        // terrain it crosses and the verb you arrive with, which is exactly the
        // difference between a bridge (cross a gap) and a road (a worn track).
        const detail = _el('div', 'font-size:11px;color:var(--text-muted,#999);' +
            'line-height:1.4;flex-basis:100%;max-width:420px;');
        detail.setAttribute('data-role', 'wp-value-detail');
        detail.textContent = '';
        const describe = (id: string): void => {
            const rec = options.filter((o) => !o.separator).find((o) => o.id === id);
            const text = rec ? _tileDetail(state.layer, rec) : '';
            detail.textContent = text;
            detail.title = text;
            swatch.style.background = GM().layerColor(state.layer, id) || 'transparent';
            swatch.title = rec ? (rec.name || rec.id || '') : '';
        };
        const paintable = options.filter((o) => !o.separator);
        const ids = paintable.map((o) => o.id || '');
        if (ids.indexOf(state.value) < 0) state.value = ids[0] || '';
        // A section is a real <optgroup>, not a disabled <option>.
        //
        // The comment that used to sit here said "a `select` cannot nest", and
        // that is simply not true -- <optgroup> is part of HTML and nests in a
        // <select> natively. The consequence of believing it was a 130-entry
        // flat list whose only structure was disabled separator options, which
        // is exactly the palette an author scrolls looking for "Wall" or "Door"
        // while drawing a 30-location town floor plan. The grouping data was
        // already computed above (every option carries `group`); only the
        // rendering threw it away.
        // Two things that are easy to get wrong here, and were:
        //  - an <optgroup>'s visible heading is its `label` ATTRIBUTE. Setting
        //    textContent on it does not label it; it just puts a stray text node
        //    where the options go.
        //  - a section heading can be followed by nothing (the "Buildings"
        //    marker is pushed before the category loop, which may add
        //    nothing), so an empty group is removed rather than left as a
        //    blank heading.
        const openGroups: HTMLOptGroupElement[] = [];
        const closeGroup = (): void => {
            const g = openGroups.pop();
            if (g && g.children.length === 0) g.remove();
        };
        // `needle` empty => everything. Matching is on the displayed name and on
        // the id, because an author who knows it as "not_a_place" should be able
        // to type that too.
        const matches = (o: WpPaletteEntry, needle: string): boolean => {
            if (!needle) return true;
            const n = needle.toLowerCase();
            return String(o.name || '').toLowerCase().includes(n)
                || String(o.id || '').toLowerCase().includes(n);
        };
        const build = (needle: string): void => {
            sel.textContent = '';
            openGroups.length = 0;
            // task-648: 'civic' is legitimately BOTH a room purpose (a town hall
            // is a room) and a building category (a civic building), so the
            // palette rendered two headings with the identical name. Filtering
            // for "civic" showed both and the heading said nothing about which
            // was which. Disambiguate a repeated label at render time rather than
            // renaming either concept, because both are right.
            const labelCount: Record<string, number> = {};
            options.forEach((o) => { if (o.section) labelCount[o.section] = (labelCount[o.section] || 0) + 1; });
            const seen: Record<string, number> = {};
            const labelFor = (s: string): string => {
                if (labelCount[s] < 2) return s;
                seen[s] = (seen[s] || 0) + 1;
                return seen[s] === 1 ? `${s} (room)` : `${s} (building)`;
            };
            options.forEach((o) => {
                if (o.separator) { closeGroup(); return; }
                if (o.section) {
                    closeGroup();
                    // Open the heading eagerly: if nothing under it matches it is
                    // removed by closeGroup on the next section or at the end.
                    const og = _el('optgroup');
                    og.label = labelFor(o.section);
                    sel.appendChild(og);
                    openGroups.push(og);
                    return;
                }
                if (!matches(o, needle)) return;
                const opt = _el('option', null, `${o.name} (${o.id})`);
                opt.value = o.id || '';
                (openGroups[openGroups.length - 1] || sel).appendChild(opt);
            });
            while (openGroups.length) closeGroup();
        };
        build('');
        filter.addEventListener('input', () => {
            build(filter.value.trim());
            // A filter can hide the current value; keep the select legal.
            if (ids.indexOf(sel.value) < 0 && sel.options.length) sel.value = sel.options[0].value;
        });
        sel.value = state.value;
        describe(sel.value);
        // Drop focus after a pick so the next space press pans instead of
        // reopening the dropdown (bug-511). The keydown guard covers a control
        // reached by Tab; this covers the click-pick path the bug reported.
        sel.addEventListener('change', () => {
            state.value = sel.value;
            describe(sel.value);
            sel.blur();
        });
        wrap.appendChild(detail);
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
        groups.forEach((g: any) => {
            const og = _el('optgroup');
            og.label = g.key === 'elsewhere'
                ? `${g.label} — picking one moves it here`
                : g.label;
            g.areas.forEach((a: any) => {
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
            (a) => !groups.some((g: any) => g.areas.some((x: any) => x.id === a.id)));
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
            'flex:1 1 auto;min-width:0;position:relative;height:480px;'
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
        hud.appendChild(_btn(`${p.grid!.w}×${p.grid!.h} · 1 cell = 1 turn`,
            () => _openGridDialog(p),
            'font-size:11px;color:var(--text-muted,#999);padding:2px 6px;',
            'Set the exact grid size…'));
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
                { w: next.w, h: next.h, cell_scale: (p.grid && p.grid.cell_scale) || 1, mode: p.mode });
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
        if (stage) state.view = { x: stage.x(), y: stage.y(), scale: stage.scaleX() };
    }

    function _redrawGrid(): void {
        if (state.stage) state.stage.batchDraw();
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
     */
    function _refRectCells(p: WpPayload, img: WpTrackedImage | null): WpRect {
        const stored = (p.reference || {}).rect;
        if (stored && typeof stored.x === 'number' && typeof stored.y === 'number'
                && typeof stored.w === 'number' && typeof stored.h === 'number'
                && stored.w > 0 && stored.h > 0) {
            return { x: stored.x, y: stored.y, w: stored.w, h: stored.h };
        }
        const gw = (p.grid && p.grid.w) || 0;
        const gh = (p.grid && p.grid.h) || 0;
        const iw = (img && img.naturalWidth) || gw || 1;
        const ih = (img && img.naturalHeight) || gh || 1;
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
 * `state.gridDrag` — so without this the frame and its handles were redrawn at
 * the *old* extent and the drag showed nothing but the size label ticking over.
 */
function _gridExtent(p: WpPayload): { w: number; h: number } {
        const drag = state.gridDrag;
        if (drag && drag.kind !== 'move' && drag.w && drag.h) {
            return { w: drag.w, h: drag.h };
        }
        return { w: p.grid!.w, h: p.grid!.h };
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
        const drag = state.gridDrag;
        if (drag && drag.kind === 'move') {
            const off = drag.offset;
            ctx.fillStyle = '#e3b341';
            ctx.font = `${Math.max(10, 12 / scale)}px sans-serif`;
            ctx.fillText(`offset ${off.x.toFixed(1)}, ${off.y.toFixed(1)}`, 8 / scale, (ext.h * CELL) + 14 / scale);
        } else if (drag && drag.w && drag.h) {
            ctx.fillStyle = '#e3b341';
            ctx.font = `${Math.max(10, 12 / scale)}px sans-serif`;
            ctx.fillText(`${drag.w}×${drag.h}`, 8 / scale, (ext.h * CELL) + 14 / scale);
        }
        ctx.restore();
    }

    /** What a pointer press grabs in grid-adjust mode: a handle or the frame. */
    function _gridHit(p: WpPayload, pos: WpCell): { kind: string; key: string | null } | null {
        const scale = (state.stage && state.stage.scaleX()) || 1;
        const tol = 9 / scale;
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
        state.gridDrag = {
            kind: target.kind,
            key: target.key,
            start: { x: pos.x / CELL, y: pos.y / CELL },
            clientX: typeof raw.clientX === 'number' ? raw.clientX : 0,
            clientY: typeof raw.clientY === 'number' ? raw.clientY : 0,
            w: p.grid!.w,
            h: p.grid!.h,
            offset: Object.assign({ x: 0, y: 0 }, p.map_offset || {}),
        };
        _gridDragWatch(p);
    }

    /**
     * Track the drag on the document, not the stage.
     *
     * Konva's stage `mousemove` only fires while the pointer is over the canvas,
     * and its `mouseleave` *committed* the resize — so dragging a handle outward
     * ended the drag the instant it left the frame, and growing the grid took a
     * series of separate drags. Listening on the document also lets the pointer
     * travel beyond the frame, which is what dragging an edge handle implies.
     */
    function _gridDragWatch(p: WpPayload): void {
        _gridDragRelease();
        const onMove = (ev: MouseEvent): void => {
            if (!state.gridDrag) return;
            if (ev.cancelable) ev.preventDefault();
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
     * Where the pointer is in cell units, as a delta from where the drag began.
     *
     * `getRelativePointerPosition()` would go stale the moment the pointer left
     * the canvas, which is the whole point of listening on the document. A drag
     * is relative anyway, so start position plus scaled screen delta is both
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
            // scope by this many cells.
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
            } else if (drag.w !== p.grid!.w || drag.h !== p.grid!.h) {
                const stranded = GM().strandedCount(p, drag.w, drag.h);
                if (stranded > 0 && !window.confirm(
                    `Resize the grid to ${drag.w}×${drag.h}?\n\n`
                    + `${stranded} painted cell(s) or placement(s) outside it will be removed. `
                    + 'This can be undone.')) {
                    render();
                    return;
                }
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid`, {
                    w: drag.w, h: drag.h,
                    cell_scale: (p.grid && p.grid.cell_scale) || 1,
                    mode: p.mode,
                });
                _status(`Grid resized to ${drag.w}×${drag.h}` +
                    (stranded ? `, ${stranded} out-of-bounds cell(s) removed` : '') + '.', false);
            }
            _notify(true);
        } catch (e) {
            _status(`Grid adjust failed: ${errText(e)}`, true);
        }
        render();
    }

    function _drawGridLines(ctx: CanvasRenderingContext2D, p: WpPayload): void {
        const ext = _gridExtent(p);
        const w = ext.w * CELL;
        const h = ext.h * CELL;
        ctx.save();
        // No opaque fill: the reference image (a layer beneath) must show through.
        const scale = state.stage ? state.stage.scaleX() : 1;
        // The extent and origin have to be visible (task-597): a bold frame
        // around the grid, a marker at cell (0,0), and a faint box around the
        // painted content so an author can see at a glance how much of the grid
        // is used and which corner is the origin.
        ctx.strokeStyle = state.gridEdit ? '#e3b341' : 'rgba(255,255,255,0.35)';
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
        ctx.font = `${Math.max(9, 11 / scale)}px sans-serif`;
        ctx.fillText(`0,0 · ${ext.w}×${ext.h}`, 6 / scale, -5 / scale);
        // Below ~4px per cell the lines become moiré — paint only.
        if (CELL * scale >= 4) {
            ctx.strokeStyle = 'rgba(255,255,255,0.07)';
            ctx.lineWidth = 1 / scale;
            ctx.beginPath();
            for (let x = 0; x <= p.grid!.w; x += 1) {
                ctx.moveTo(x * CELL, 0);
                ctx.lineTo(x * CELL, h);
            }
            for (let y = 0; y <= p.grid!.h; y += 1) {
                ctx.moveTo(0, y * CELL);
                ctx.lineTo(w, y * CELL);
            }
            ctx.stroke();
        }
        ctx.restore();
    }

    function _drawPaint(ctx: CanvasRenderingContext2D, p: WpPayload): void {
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
                ctx.fillRect(pos.x * CELL + 1, pos.y * CELL + 1, CELL - 2, CELL - 2);
            });
        });
        ctx.restore();
    }

    function _drawFeatures(ctx: CanvasRenderingContext2D, p: WpPayload): void {
        ctx.save();
        ctx.font = `${Math.max(9, CELL - 8)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        (p.placements || []).forEach((pl) => {
            const selected = pl.id === state.selectedChild;
            ctx.fillStyle = selected ? '#f5c542' : '#7b5aa6';
            ctx.fillRect(pl.x * CELL + 2, pl.y * CELL + 2, CELL - 4, CELL - 4);
            ctx.fillStyle = '#fff';
            ctx.fillText('🏠', pl.x * CELL + CELL / 2, pl.y * CELL + CELL / 2);
        });
        // Placed areas (task-528) sit in the same decor layer but are a different
        // kind of thing — a node that already exists, not a child scope — so they
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
            if (CELL >= 26) {
                ctx.fillStyle = '#d9f2e5';
                ctx.font = '9px sans-serif';
                ctx.fillText(_ellipsize(a.name, 12), a.x * CELL + CELL / 2,
                    a.y * CELL + CELL + 8);
            }
        });
        ctx.restore();
    }

    function _ellipsize(text: unknown, max: number): string {
        const s = String(text == null ? '' : text);
        return s.length > max ? `${s.slice(0, max - 1)}…` : s;
    }

    function _drawRoute(ctx: CanvasRenderingContext2D): void {
        // In-progress paint stroke (drag): drawn optimistically, committed on
        // mouse-up as one batch. Without this a brush drag felt like "click and
        // wait" — now it paints a live trail.
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
        try {
            if (cells.length === 1) {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint`,
                    { layer, x: cells[0].x, y: cells[0].y, value });
            } else {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                    { edits: cells.map((c) => ({ layer, x: c.x, y: c.y, value })) });
            }
            _notify(true);
            render();
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
        // the active tool and nothing else — a drag means different things under
        // different tools, and which one is always the tool the author can see.
        // In reference-adjust mode the drag belongs to the picture, so only space
        // pans there.
        const dragPaints = () => _isPaintTool() || state.tool === 'move';
        stage.draggable(state.spaceDown || (!state.refEdit && !state.gridEdit && !dragPaints()
            && state.tool !== 'select'));        stage.on('dragstart', () => { dragged = true; });
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
        stage.on('mousemove', () => {
            // The active grid drag tracks itself on the document (it must outlive
            // the pointer leaving the canvas); nothing else may claim the pointer.
            if (state.gridEdit) return;
            if (state.refEdit) { _refMouseMove(p); return; }
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
                state.brushHover = _brushCells(p, cell.x, cell.y);
                _redrawDecor();
            } else {
                state.brushHover = null;
                _redrawDecor();
            }
            _updateCellInfo(p);
        });
        stage.on('mouseup mouseleave', () => {
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
        // Right-click is "what is this?" on any tool, so a cell is never a dead
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
     * map with two of them. So it is one batch — clear every source cell on every
     * layer it has, then write each value at its new home — which means one undo
     * step, one request, and a rejection of the whole thing if any cell would land
     * off the grid. Clamping is what the task asks for and it is also the honest
     * behaviour: a cell shifted past the edge is dropped from the move, not
     * silently wrapped to the other side.
     */
    async function _nudge(p: WpPayload, dx: number, dy: number): Promise<void> {
        const cells = _selectedCells(p);
        if (!cells.length) { _status('Nothing selected — use the ⬚ Select tool first.', true); return; }
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
            _status('The whole selection is against that edge — nowhere to move it.');
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
            _notify(true);
            render();
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
            _notify(true);
            render();
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
        render();
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
    // Hover reads the cell from the payload, and a click (or right-click on any
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
        render();
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
        head.appendChild(_btn('✕', () => { state.inspected = null; render(); },
            'margin-left:auto;padding:1px 7px;', 'Close the cell panel'));
        wrap.appendChild(head);

        const rows = _el('div', 'display:flex;flex-direction:column;gap:2px;margin-top:6px;');
        const row = (label: string, value: string): void => {
            const r = _el('div', 'display:flex;gap:6px;align-items:baseline;');
            r.appendChild(_el('span', 'color:var(--text-muted,#999);min-width:78px;', label));
            r.appendChild(_el('span', null, value));
            rows.appendChild(r);
        };
        row('biome', info.biome ? String(info.biome).replace(/_/g, ' ') : '—');
        row('road', info.road ? String(info.road).replace(/_/g, ' ') : '—');
        row('floor', GM().floorLabel(info.floor));
        // Structure is not a place, and saying so is the point: the author just
        // painted a wall and it will not appear in the graph (task-562).
        row('structure', info.kind
            ? `not a place — ${STRUCTURE_NOTES[info.kind] || info.kind}`
            : '—');
        // A building is entered with `in`; a shut one is the author's cue that it
        // still owes an interior (task-563).
        row('enter', info.enter || '—');
        row('area', info.area ? `${info.area.name} (${info.area.id})` : '—');
        row('sub-zone', info.child ? `${info.child.name || info.child.id} (${info.child.id})` : '—');
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
        row('exits', ['N', 'E', 'S', 'W']
            .map((d) => `${d}: ${label(neighbours[d])}`).join(' · '));
        wrap.appendChild(rows);

        // The cell's name (task-560) — what the place is *called*, which is what
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
                edits: GM().PAINT_LAYERS.map((layer: any) => ({ layer, x, y, value: null })),
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
            render();
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
        const scale = Math.max(MIN_SCALE, Math.min(1.5,
            Math.min(stage.width() / (p.grid!.w * CELL), stage.height() / (p.grid!.h * CELL))));
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
            _notify(true);
            const stats = GM().routeStats(edits.length);
            _status(`🧭 Painted ${stats.label} on ${state.layer}.`, false);
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
        const cur = p.grid || { w: 10, h: 10, cell_scale: 1 };
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
        const sIn = mk('scale', cur.cell_scale ?? 1, 64);
        sIn.setAttribute('data-role', 'wp-grid-scale');
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
        GM().MODES.forEach((m: any) => {
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
            const lost = GM().PAINT_LAYERS.reduce((n: number, l: any) =>
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
                    cell_scale: parseFloat(sIn.value) || 1,
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

    function _status(text: string, isError?: boolean): void {
        state.status = text;
        state.statusError = !!isError;
        _log((isError ? '⚠ ' : '') + text, isError ? 'error-msg' : 'system-msg');
        render();
    }

    window.VW = window.VW || {};
    window.VW.worldPainter = { open, close, refresh: () => (state.scopeId ? load(state.scopeId) : showChooser()) };
    window.worldPainter = window.VW.worldPainter;
})();
