/**
 * static/js/types/worldpainter.d.ts - Ambient types for WorldPainter modules
 */

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
     * snake_case counts, the nested one camelCase - both are accepted (task-615).
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
        startOffset: WpCell;
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
        /** Detaches the document-level grid-drag listeners, if any are attached. */
        gridDragRelease: (() => void) | null;
        /**
         * A cell-size candidate being previewed by dragging the cell (0,0) corner
         * handle (task-597): the grid it would set, drawn on the canvas before
         * anything is committed. Null unless a cell-size drag is in progress.
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

    interface WpRecentItem {
        layer: string;
        value: string;
    }

