"use strict";
/**
 * graph-background.ts — reference maps behind the vis.js graph.
 *
 * ⚠️ `graph-background.js` is GENERATED from this file — edit the .ts, then run
 *    `npm run build:ts`. (Second converted module; see docs/design/typescript-migration.md.)
 *
 * @module graph/graph-background — the multi-layer reference map overlay
 * @contributes the map layers (path, transform, crop, opacity, order, visibility) and per-scenario layout persistence
 * @powers the right-click 🗺 map: add/select/move/scale/rotate/crop several reference images, and lock node positions
 * @relates uses storage (graph_assets) + the graphManager.network view transform; opened from GraphEventHandlers.onContext
 * @docs docs/virtualWorld/World Building/Graph System.md
 *
 * UX: right-click empty canvas → 🗺 Add background image. A layer panel lists
 * every image; the selected one gets on-canvas handles: drag the body to move,
 * corners to scale about the centre, the top handle to rotate, and (in crop
 * mode) the inner handles to crop. Arrow keys nudge, alt-click cycles through
 * overlapping layers, images snap to each other's edges and centres.
 *
 * Rendering: image frames live in a layer that is the container's FIRST child,
 * so they paint beneath the (transparent) vis canvas — nodes draw over the map,
 * and the map never covers the legend. That layer is kept in sync with the
 * network view transform on every `afterDrawing`, so maps pan/zoom with graph.
 *
 * Interaction: because the images paint BENEATH the canvas (which owns pointer
 * events), nothing inside the paint layer can be clicked — so every interactive
 * part lives in an above-canvas interact layer that is `pointer-events: none`
 * except on its own hit boxes and handles. That is what makes a map draggable
 * at all, and it is what lets several maps be selected individually.
 *
 * Persistence: the world block `graph_background`
 * ({ layers: [...], positions, layoutLocked }) travels with the scenario and can
 * be committed; IndexedDB store `graph_assets`, keyed by the scenario name, is
 * the local fallback for images that were never uploaded. A legacy single
 * `graph_background` block is migrated on read.
 */
/* ── module ────────────────────────────────────────────────────────────── */
(() => {
    'use strict';
    const STORE = 'graph_assets';
    const OPACITY_DEFAULT = 0.45;
    const HANDLE = 10;
    const SNAP_PX = 8; // snap distance, in screen pixels
    const MIN_CROP = 0.05;
    const MIN_LAYER_SIZE = 40;
    const state = {
        // ── data ──────────────────────────────────────────────────────────
        layers: [],
        activeId: null,
        positions: {},
        layoutLocked: false, // node physics freeze + saved positions
        key: null, // scenario cache key
        // ── view / interaction ────────────────────────────────────────────
        editing: false,
        cropping: false,
        physicsDisabledByLock: false,
        // ── DOM ───────────────────────────────────────────────────────────
        paintLayer: null, paintSpace: null,
        interactLayer: null, interactSpace: null,
        activeFrame: null, handles: null,
        hitBoxes: {}, // layerId -> hit box element
        panel: null,
        _dragLayerId: null,
        _panelSignature: null,
        _nudgeTimer: null,
        // Convenience views of the ACTIVE layer, so `_state.image` / `_state.rect`
        // keep meaning what they meant in the single-image version.
        get active() { return state.layers.find((layer) => layer.id === state.activeId) || null; },
        get image() { const active = state.active; return active ? active.image : null; },
        get rect() { const active = state.active; return active ? active.rect : null; },
        get rotation() { const active = state.active; return active ? active.rotation : 0; },
        get crop() { const active = state.active; return active ? active.crop : { x: 0, y: 0, w: 1, h: 1 }; },
        get opacity() { const active = state.active; return active ? active.opacity : OPACITY_DEFAULT; },
        get imagePath() { const active = state.active; return active ? active.imagePath : null; },
        // `locked` keeps its ORIGINAL meaning (the node-layout freeze).
        get locked() { return state.layoutLocked; },
        set locked(value) { state.layoutLocked = !!value; },
    };
    function _network() {
        if (typeof graphManager === 'undefined' || !graphManager)
            return null;
        return graphManager.network || null;
    }
    function _uid() {
        return 'bg-' + Math.random().toString(36).slice(2, 9);
    }
    /**
     * The scenario's identity, or null when the world has no name.
     *
     * The IndexedDB cache is keyed on this. An unnamed scenario returns null so
     * the cache is NOT consulted at all — otherwise every unnamed scenario would
     * share the 'default' slot and a map added in one would appear in the next.
     *
     * Must accept the same fallbacks as _scenarioKey(): the body dataset is how
     * Save/Export Scenario records the name (ui/saveload-view.js), so ignoring
     * it here left the identity null and silently disabled the cached map.
     */
    function _scenarioIdentity() {
        const data = (typeof worldState !== 'undefined' && worldState && worldState.data) || {};
        const name = data._scenario_name
            || (document.body && document.body.dataset && document.body.dataset.scenarioName)
            || '';
        return String(name).trim() || null;
    }
    /** Cache key — derived from the identity so the two cannot disagree. */
    function _scenarioKey() {
        return _scenarioIdentity() || 'default';
    }
    /* ── layer model ───────────────────────────────────────────────────── */
    const DEFAULT_CROP = () => ({ x: 0, y: 0, w: 1, h: 1 });
    function _normalizeLayer(raw) {
        if (!raw || typeof raw !== 'object')
            return null;
        const source = raw;
        const rawRect = source.rect;
        const rectRecord = rawRect && typeof rawRect === 'object' ? rawRect : null;
        const rect = rectRecord
            && ['x', 'y', 'width', 'height'].every((key) => typeof rectRecord[key] === 'number')
            ? { x: rectRecord.x, y: rectRecord.y, width: rectRecord.width, height: rectRecord.height }
            : null;
        const image = typeof source.image === 'string' && source.image ? source.image : null;
        // A layer needs BOTH: an image to draw and a transform to draw it with.
        // A rect with nothing in it is not a layer (it would render nothing and
        // still appear in the panel).
        if (!image || !rect)
            return null;
        const crop = source.crop;
        return {
            id: typeof source.id === 'string' && source.id ? source.id : _uid(),
            label: typeof source.label === 'string' ? source.label : '',
            imagePath: image.startsWith('/static/') ? image : null,
            imageSrc: image, // path or data URL
            image: null, // HTMLImageElement, decoded lazily
            rect,
            rotation: typeof source.rotation === 'number' ? source.rotation : 0,
            crop: crop && typeof crop.w === 'number'
                ? { x: crop.x || 0, y: crop.y || 0, w: crop.w, h: crop.h }
                : DEFAULT_CROP(),
            opacity: typeof source.opacity === 'number' ? source.opacity : OPACITY_DEFAULT,
            locked: !!source.locked,
            visible: source.visible !== false,
        };
    }
    /**
     * Normalize a world block, migrating the legacy single-image shape.
     *
     * Legacy: { image, rect, rotation, crop, opacity, locked, positions }.
     * Its `locked` meant the NODE-LAYOUT freeze, so it becomes `layoutLocked`;
     * per-layer `locked` (image cannot be dragged) starts false.
     */
    function _normalizeBlock(block) {
        if (!block || typeof block !== 'object')
            return null;
        const source = block;
        const positions = source.positions && typeof source.positions === 'object'
            ? source.positions
            : {};
        if (Array.isArray(source.layers)) {
            return {
                layers: source.layers.map(_normalizeLayer).filter((layer) => layer !== null),
                positions,
                layoutLocked: !!source.layoutLocked,
            };
        }
        const migrated = _normalizeLayer({
            id: 'layer-1',
            image: source.image,
            rect: source.rect,
            rotation: source.rotation,
            crop: source.crop,
            opacity: source.opacity,
            locked: false,
            visible: true,
        });
        return {
            layers: migrated ? [migrated] : [],
            positions,
            layoutLocked: !!source.locked,
        };
    }
    /**
     * Does a stored/world record actually carry a background?
     *
     * Every scenario serializes the key, so a world with no map arrives as `{}`
     * — which is TRUTHY in JS. Treating that as a record used to short-circuit
     * BOTH the per-scenario cache lookup and the clear: `rect` was nulled while
     * the previous scenario's image stayed on screen, so the new scenario's own
     * map never loaded (bug-39). A record only counts when it has something in it.
     */
    function _hasBackground(block) {
        const normalized = _normalizeBlock(block);
        if (!normalized)
            return false;
        if (normalized.layers.some((layer) => layer.imageSrc && layer.rect))
            return true;
        if (normalized.layoutLocked)
            return true;
        return Object.keys(normalized.positions).length > 0;
    }
    /** Serialize the block for the world / IndexedDB. */
    function _snapshot() {
        return {
            layers: state.layers.map((layer) => ({
                id: layer.id,
                label: layer.label,
                image: layer.imagePath || layer.imageSrc || null,
                rect: layer.rect,
                rotation: layer.rotation,
                crop: layer.crop,
                opacity: layer.opacity,
                locked: layer.locked,
                visible: layer.visible,
            })),
            positions: state.positions,
            layoutLocked: state.layoutLocked,
        };
    }
    function _active() {
        return state.layers.find((layer) => layer.id === state.activeId) || null;
    }
    function _setActive(id, { render = true } = {}) {
        if (!state.layers.some((layer) => layer.id === id))
            return;
        state.activeId = id;
        state.cropping = false;
        if (render)
            _render();
    }
    /** Drop all background state WITHOUT persisting it (scenario changed). */
    function reset() {
        state.layers.forEach(_removeLayerEl);
        state.layers = [];
        state.activeId = null;
        state.positions = {};
        state.layoutLocked = false;
        state.editing = false;
        state.cropping = false;
        _render();
        _updateHint();
    }
    /* ── persistence ───────────────────────────────────────────────────── */
    /**
     * Persist the layers + transform on the WORLD (scenario-level), so they
     * travel with the file and can be committed. Debounced: drags call this on
     * pointer-up, not per frame.
     */
    let worldSaveTimer;
    function saveToWorld(immediate = false) {
        if (typeof ApiClient === 'undefined' || !ApiClient.saveGraphBackground)
            return;
        const payload = _snapshot();
        const post = () => {
            ApiClient.saveGraphBackground(payload).catch(() => { });
        };
        clearTimeout(worldSaveTimer);
        if (immediate) {
            post();
            return;
        }
        worldSaveTimer = setTimeout(post, 400);
    }
    async function _persist() {
        if (typeof storage === 'undefined' || !storage || !state.key)
            return;
        try {
            await storage.set(STORE, state.key, Object.assign({ key: state.key, updated: Date.now() }, _snapshot()));
        }
        catch (error) { /* ignore */ }
    }
    /** Decode a layer's image source; resolves with the element or null. */
    function _setImageSrc(src) {
        return new Promise((resolve) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => resolve(null);
            image.src = src;
        });
    }
    /** Make sure every layer with a source has a decoded image. */
    async function _decodeLayers() {
        for (const layer of state.layers) {
            if (!layer.image && layer.imageSrc) {
                layer.image = await _setImageSrc(layer.imageSrc);
            }
        }
    }
    async function _restore() {
        state.key = _scenarioKey();
        const identity = _scenarioIdentity();
        // The WORLD copy wins — it travels with the scenario and can be
        // committed. IndexedDB is only a local fallback, and only for a NAMED
        // scenario: with no name there is no way to tell two worlds apart, so
        // showing a cached map would leak it into the next scenario.
        // (`graph_background` holds the multi-layer block; a legacy single-image
        // block is migrated by _normalizeBlock.)
        const worldBlock = (typeof worldState !== 'undefined' && worldState?.data?.graph_background) || null;
        let block = _hasBackground(worldBlock) ? _normalizeBlock(worldBlock) : null;
        if (!block && identity && typeof storage !== 'undefined' && storage) {
            let cached = null;
            try {
                cached = await storage.get(STORE, state.key);
            }
            catch (error) {
                cached = null;
            }
            if (_hasBackground(cached))
                block = _normalizeBlock(cached);
        }
        if (!block) {
            // This world has no background of its own — show NOTHING rather than
            // leaving the previous scenario's maps on screen. (No-op when we are
            // already clear, so frequent state updates stay cheap.)
            if (state.layers.length)
                reset();
            return;
        }
        if (!block.layers.length && !block.layoutLocked && !Object.keys(block.positions).length) {
            if (state.layers.length)
                reset();
            return;
        }
        // Replace the layer set, keeping DOM elements for ids we already have so
        // an unchanged map does not flicker on every state refresh.
        const previous = new Map(state.layers.map((layer) => [layer.id, layer]));
        const next = block.layers.map((layer) => {
            const existing = previous.get(layer.id);
            if (existing) {
                existing.imagePath = layer.imagePath;
                if (existing.imageSrc !== layer.imageSrc) {
                    existing.imageSrc = layer.imageSrc;
                    existing.image = null;
                }
                return existing;
            }
            return layer;
        });
        for (const old of state.layers)
            if (!next.includes(old))
                _removeLayerEl(old);
        state.layers = next;
        if (!state.layers.some((layer) => layer.id === state.activeId)) {
            state.activeId = state.layers.length ? state.layers[state.layers.length - 1].id : null;
            state.cropping = false;
        }
        state.positions = block.positions;
        state.layoutLocked = block.layoutLocked;
        await _decodeLayers();
    }
    /* ── view sync ─────────────────────────────────────────────────────── */
    /**
     * Screen point → graph space.
     *
     * Derived from the SAME transform _syncView applies to the layers, rather
     * than from vis's DOMtoCanvas: mixing the two put the cursor hundreds of
     * units away from the layer under it (vis converts canvas-relative
     * coordinates, and its viewport origin is not the container's).
     */
    function _clientToGraph(clientX, clientY) {
        const network = _network();
        const container = document.getElementById('graph-container');
        if (!network || !container)
            return null;
        const bounds = container.getBoundingClientRect();
        let scale = 1;
        let viewPosition = { x: 0, y: 0 };
        try {
            scale = network.getScale() || 1;
            viewPosition = network.getViewPosition();
        }
        catch (error) {
            return null;
        }
        return {
            x: (clientX - bounds.left - bounds.width / 2) / (scale || 1) + viewPosition.x,
            y: (clientY - bounds.top - bounds.height / 2) / (scale || 1) + viewPosition.y,
        };
    }
    function _syncView() {
        const network = _network();
        if (!network || !state.paintSpace)
            return;
        const container = document.getElementById('graph-container');
        const width = container ? container.clientWidth : 0;
        const height = container ? container.clientHeight : 0;
        let scale = 1;
        let viewPosition = { x: 0, y: 0 };
        try {
            scale = network.getScale();
            viewPosition = network.getViewPosition();
        }
        catch (error) {
            return;
        }
        const transform = `translate(${width / 2}px, ${height / 2}px) scale(${scale}) translate(${-viewPosition.x}px, ${-viewPosition.y}px)`;
        state.paintSpace.style.transform = transform;
        if (state.interactSpace)
            state.interactSpace.style.transform = transform;
    }
    /* ── DOM: paint layer (beneath the canvas) ─────────────────────────── */
    function _ensureLayers() {
        if (state.paintLayer)
            return;
        const container = document.getElementById('graph-container');
        if (!container)
            return;
        const paintLayer = document.createElement('div');
        paintLayer.id = 'graph-bg-layer';
        paintLayer.style.cssText = 'position:absolute;inset:0;overflow:hidden;pointer-events:none;';
        const paintSpace = document.createElement('div');
        paintSpace.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;transform-origin:0 0;';
        paintLayer.appendChild(paintSpace);
        // First child ⇒ paints beneath the transparent canvas (nodes over map).
        container.insertBefore(paintLayer, container.firstChild);
        // Everything the user can actually touch lives ABOVE the canvas: the
        // canvas owns pointer events, so anything painted beneath it is inert.
        const interactLayer = document.createElement('div');
        interactLayer.id = 'graph-bg-interact-layer';
        interactLayer.style.cssText = 'position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:5;';
        const interactSpace = document.createElement('div');
        interactSpace.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;transform-origin:0 0;';
        interactLayer.appendChild(interactSpace);
        container.appendChild(interactLayer);
        // The active layer's handles, in their own frame so they inherit its
        // rotation exactly like the old single-image version did.
        const activeFrame = document.createElement('div');
        activeFrame.style.cssText = 'position:absolute;transform-origin:center center;overflow:visible;pointer-events:none;';
        interactSpace.appendChild(activeFrame);
        state.paintLayer = paintLayer;
        state.paintSpace = paintSpace;
        state.interactLayer = interactLayer;
        state.interactSpace = interactSpace;
        state.activeFrame = activeFrame;
        _buildHandles();
        _ensurePanel();
    }
    function _ensureLayerEl(layer) {
        if (layer.el)
            return;
        const frame = document.createElement('div');
        frame.style.cssText = 'position:absolute;transform-origin:center center;overflow:hidden;pointer-events:none;';
        const img = document.createElement('img');
        img.style.cssText = 'position:absolute;left:0;top:0;transform-origin:0 0;pointer-events:none;user-select:none;';
        img.draggable = false;
        frame.appendChild(img);
        state.paintSpace?.appendChild(frame);
        layer.el = frame;
        layer.imgEl = img;
    }
    function _removeLayerEl(layer) {
        if (layer && layer.el && layer.el.parentNode)
            layer.el.parentNode.removeChild(layer.el);
        if (layer) {
            layer.el = null;
            layer.imgEl = null;
        }
        if (layer && state.hitBoxes[layer.id]) {
            const box = state.hitBoxes[layer.id];
            if (box.parentNode)
                box.parentNode.removeChild(box);
            delete state.hitBoxes[layer.id];
        }
    }
    function _handleEl(dir, css) {
        const el = document.createElement('div');
        el.dataset.dir = dir;
        el.style.cssText = css;
        el.addEventListener('mousedown', (event) => {
            if (!state.editing)
                return;
            const kind = dir === 'rot' ? 'rotate' : (dir.indexOf('c') === 0 ? 'crop' : 'resize');
            _startDrag(event, kind, dir);
        });
        return el;
    }
    function _buildHandles() {
        const base = `position:absolute;width:${HANDLE}px;height:${HANDLE}px;margin-left:${-HANDLE / 2}px;margin-top:${-HANDLE / 2}px;background:#58a6ff;border:1px solid #0d1117;border-radius:2px;pointer-events:auto;display:none;box-sizing:border-box;`;
        const rotBase = `position:absolute;width:14px;height:14px;margin-left:-7px;margin-top:-7px;background:#bc8cff;border:1px solid #0d1117;border-radius:50%;pointer-events:auto;cursor:grab;display:none;box-sizing:border-box;`;
        const cropBase = `position:absolute;width:12px;height:12px;margin-left:-6px;margin-top:-6px;background:#e3b341;border:1px solid #0d1117;border-radius:2px;pointer-events:auto;cursor:crosshair;display:none;box-sizing:border-box;`;
        const corners = {
            nw: _handleEl('nw', base + 'cursor:nwse-resize;'),
            ne: _handleEl('ne', base + 'cursor:nesw-resize;'),
            se: _handleEl('se', base + 'cursor:nwse-resize;'),
            sw: _handleEl('sw', base + 'cursor:nesw-resize;'),
        };
        const rotate = _handleEl('rot', rotBase);
        const cropShade = document.createElement('div');
        cropShade.style.cssText = 'position:absolute;border:1px dashed #e3b341;background:rgba(227,179,65,0.08);pointer-events:none;display:none;box-sizing:border-box;';
        state.handles = {
            corners,
            rotate,
            cropShade,
            cx0: _handleEl('cx0', cropBase),
            cx1: _handleEl('cx1', cropBase),
            cy0: _handleEl('cy0', cropBase),
            cy1: _handleEl('cy1', cropBase),
        };
        // Handles live INSIDE the active frame so they inherit its rotation; the
        // crop shade does too.
        const activeFrame = state.activeFrame;
        if (!activeFrame)
            return;
        activeFrame.appendChild(cropShade);
        Object.values(corners).forEach((cornerHandle) => activeFrame.appendChild(cornerHandle));
        activeFrame.appendChild(rotate);
        const cropKeys = ['cx0', 'cx1', 'cy0', 'cy1'];
        cropKeys.forEach((key) => activeFrame.appendChild(state.handles[key]));
    }
    /** One hit box per visible layer, mirroring its geometry (edit mode only). */
    function _ensureHitBox(layer) {
        let box = state.hitBoxes[layer.id];
        if (!box) {
            box = document.createElement('div');
            box.dataset.layerId = layer.id;
            box.style.cssText = 'position:absolute;transform-origin:center center;pointer-events:none;background:transparent;box-sizing:border-box;';
            box.addEventListener('mousedown', (event) => {
                if (!state.editing)
                    return;
                if (event.altKey) {
                    _cycleAtPointer(event);
                    event.preventDefault();
                    event.stopPropagation();
                    return;
                }
                if (layer.id !== state.activeId)
                    _setActive(layer.id);
                if (layer.locked)
                    return; // selectable, but not draggable
                _startDrag(event, 'move', null);
            });
            // Insert before the active frame, so handles stay on top of hit boxes.
            state.interactSpace?.insertBefore(box, state.activeFrame);
            state.hitBoxes[layer.id] = box;
        }
        return box;
    }
    function _positionHandles() {
        const handles = state.handles;
        const layer = _active();
        if (!handles || !layer || !layer.rect)
            return;
        const width = layer.rect.width;
        const height = layer.rect.height;
        const show = state.editing && layer.visible && !layer.locked;
        const cropShow = show && state.cropping;
        // Handles live in graph space, so they shrink with the view. Counter-scale
        // them to a constant on-screen size, or they are a few pixels wide at the
        // zoom levels where maps are actually placed.
        const network = _network();
        const scale = network ? (network.getScale() || 1) : 1;
        const inverseScale = scale > 0 ? 1 / scale : 1;
        const place = (el, x, y, visible) => {
            el.style.display = visible ? 'block' : 'none';
            if (visible) {
                el.style.left = x + 'px';
                el.style.top = y + 'px';
                el.style.transform = `scale(${inverseScale})`;
            }
        };
        place(handles.corners.nw, 0, 0, show);
        place(handles.corners.ne, width, 0, show);
        place(handles.corners.se, width, height, show);
        place(handles.corners.sw, 0, height, show);
        place(handles.rotate, width / 2, -30, show);
        const crop = layer.crop;
        place(handles.cx0, crop.x * width, height / 2, cropShow);
        place(handles.cx1, (crop.x + crop.w) * width, height / 2, cropShow);
        place(handles.cy0, width / 2, crop.y * height, cropShow);
        place(handles.cy1, width / 2, (crop.y + crop.h) * height, cropShow);
        handles.cropShade.style.display = cropShow ? 'block' : 'none';
        if (cropShow) {
            handles.cropShade.style.left = (crop.x * width) + 'px';
            handles.cropShade.style.top = (crop.y * height) + 'px';
            handles.cropShade.style.width = (crop.w * width) + 'px';
            handles.cropShade.style.height = (crop.h * height) + 'px';
        }
    }
    /** Geometry shared by a layer's paint frame and its hit box. */
    function _placeBox(el, layer) {
        const rect = layer.rect;
        if (!rect)
            return;
        el.style.left = rect.x + 'px';
        el.style.top = rect.y + 'px';
        el.style.width = rect.width + 'px';
        el.style.height = rect.height + 'px';
        el.style.transform = `rotate(${layer.rotation}deg)`;
    }
    function _render() {
        _ensureLayers();
        if (!state.paintLayer || !state.interactLayer || !state.activeFrame)
            return;
        const visibleLayers = state.layers.filter((layer) => layer.visible && layer.image && layer.rect);
        state.paintLayer.style.display = visibleLayers.length ? 'block' : 'none';
        state.interactLayer.style.display = visibleLayers.length ? 'block' : 'none';
        const active = _active();
        const handlesOn = !!(state.editing && active && active.visible && active.image && active.rect);
        state.activeFrame.style.display = handlesOn ? 'block' : 'none';
        state.layers.forEach((layer, index) => {
            _ensureLayerEl(layer);
            const box = _ensureHitBox(layer);
            const shown = !!(layer.visible && layer.image && layer.rect);
            if (layer.el)
                layer.el.style.display = shown ? 'block' : 'none';
            box.style.display = shown ? 'block' : 'none';
            box.style.zIndex = String(index + 1);
            box.style.pointerEvents = (state.editing && shown && !layer.locked) ? 'auto' : 'none';
            box.style.cursor = (state.editing && shown && !layer.locked) ? 'move' : 'default';
            box.style.outline = (state.editing && shown && layer === active)
                ? '1px dashed rgba(88,166,255,0.9)'
                : (state.editing && shown ? '1px dashed rgba(139,148,158,0.35)' : 'none');
            if (!shown)
                return;
            const rect = layer.rect;
            const crop = layer.crop;
            const frame = layer.el;
            const img = layer.imgEl;
            if (!rect || !frame || !img || !layer.image)
                return;
            frame.style.zIndex = String(index + 1);
            _placeBox(frame, layer);
            frame.style.opacity = String(layer.opacity);
            // The hit box must cover the image exactly, or the map is neither
            // selectable nor draggable — nothing beneath the canvas can be.
            _placeBox(box, layer);
            // Crop is modelled as a scaled image inside an overflow-hidden frame:
            // the cropped fraction is enlarged to fill the frame.
            const drawWidth = rect.width / Math.max(0.01, crop.w);
            const drawHeight = rect.height / Math.max(0.01, crop.h);
            if (img.src !== layer.image.src)
                img.src = layer.image.src;
            img.style.width = drawWidth + 'px';
            img.style.height = drawHeight + 'px';
            img.style.left = (-crop.x * drawWidth) + 'px';
            img.style.top = (-crop.y * drawHeight) + 'px';
        });
        if (handlesOn && active) {
            _placeBox(state.activeFrame, active);
            state.activeFrame.style.opacity = String(active.opacity);
        }
        _positionHandles();
        _syncView();
        _renderPanel();
    }
    /* ── interaction ───────────────────────────────────────────────────── */
    /** Layers whose rect contains a graph-space point, topmost first. */
    function _layersAt(gx, gy) {
        return state.layers
            .map((layer, index) => ({ layer, index }))
            .filter(({ layer }) => layer.visible && layer.rect && _pointInLayer(layer, gx, gy))
            .sort((a, b) => b.index - a.index)
            .map(({ layer }) => layer);
    }
    function _pointInLayer(layer, gx, gy) {
        const rect = layer.rect;
        if (!rect)
            return false;
        // Into the layer's unrotated local space.
        const radians = (-layer.rotation * Math.PI) / 180;
        const centreX = rect.x + rect.width / 2;
        const centreY = rect.y + rect.height / 2;
        const deltaX = gx - centreX;
        const deltaY = gy - centreY;
        const localX = deltaX * Math.cos(radians) - deltaY * Math.sin(radians);
        const localY = deltaX * Math.sin(radians) + deltaY * Math.cos(radians);
        return Math.abs(localX) <= rect.width / 2 && Math.abs(localY) <= rect.height / 2;
    }
    /** Alt-click: step to the next layer under the pointer (topmost → down). */
    function _cycleAtPointer(event) {
        const point = _clientToGraph(event.clientX, event.clientY);
        if (!point)
            return;
        const stack = _layersAt(point.x, point.y);
        if (!stack.length)
            return;
        const current = stack.findIndex((layer) => layer.id === state.activeId);
        const next = stack[(current + 1) % stack.length] || stack[0];
        _setActive(next.id);
    }
    /** Snap a rect's edges/centre to the other layers and to node bounds. */
    function _snapRect(rect, movingLayer) {
        const network = _network();
        const scale = network ? (network.getScale() || 1) : 1;
        const tolerance = SNAP_PX / (scale || 1);
        const xLines = [];
        const yLines = [];
        for (const layer of state.layers) {
            if (layer === movingLayer || !layer.visible || !layer.rect)
                continue;
            const other = layer.rect;
            xLines.push(other.x, other.x + other.width / 2, other.x + other.width);
            yLines.push(other.y, other.y + other.height / 2, other.y + other.height);
        }
        const bounds = _nodeBounds();
        if (bounds) {
            xLines.push(bounds.minX, (bounds.minX + bounds.maxX) / 2, bounds.maxX);
            yLines.push(bounds.minY, (bounds.minY + bounds.maxY) / 2, bounds.maxY);
        }
        const snapped = { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
        let bestX = null;
        const xCandidates = [snapped.x, snapped.x + snapped.width / 2, snapped.x + snapped.width];
        for (const candidate of xCandidates) {
            for (const line of xLines) {
                const delta = line - candidate;
                if (Math.abs(delta) <= tolerance && (bestX === null || Math.abs(delta) < Math.abs(bestX.delta)))
                    bestX = { delta };
            }
        }
        if (bestX)
            snapped.x += bestX.delta;
        let bestY = null;
        const yCandidates = [snapped.y, snapped.y + snapped.height / 2, snapped.y + snapped.height];
        for (const candidate of yCandidates) {
            for (const line of yLines) {
                const delta = line - candidate;
                if (Math.abs(delta) <= tolerance && (bestY === null || Math.abs(delta) < Math.abs(bestY.delta)))
                    bestY = { delta };
            }
        }
        if (bestY)
            snapped.y += bestY.delta;
        return snapped;
    }
    function _nodeBounds() {
        const network = _network();
        if (!network)
            return null;
        let positions = {};
        try {
            positions = network.getPositions();
        }
        catch (error) {
            return null;
        }
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const id of Object.keys(positions)) {
            const position = positions[id];
            if (!position)
                continue;
            minX = Math.min(minX, position.x);
            maxX = Math.max(maxX, position.x);
            minY = Math.min(minY, position.y);
            maxY = Math.max(maxY, position.y);
        }
        if (!isFinite(minX))
            return null;
        return { minX, minY, maxX, maxY };
    }
    function _startDrag(event, kind, dir) {
        _ensureLayers();
        const layer = _active();
        if (!state.editing || !layer || !layer.rect)
            return;
        event.preventDefault();
        event.stopPropagation();
        const network = _network();
        const scale = network ? network.getScale() : 1;
        const startMouse = { x: event.clientX, y: event.clientY };
        const startRect = { x: layer.rect.x, y: layer.rect.y, width: layer.rect.width, height: layer.rect.height };
        const startCrop = { x: layer.crop.x, y: layer.crop.y, w: layer.crop.w, h: layer.crop.h };
        const startRotation = layer.rotation;
        const radians = (startRotation * Math.PI) / 180;
        const cos = Math.cos(-radians);
        const sin = Math.sin(-radians);
        const centre = {
            x: startRect.x + startRect.width / 2,
            y: startRect.y + startRect.height / 2,
        };
        const onMove = (moveEvent) => {
            const deltaX = (moveEvent.clientX - startMouse.x) / (scale || 1);
            const deltaY = (moveEvent.clientY - startMouse.y) / (scale || 1);
            const active = _active();
            if (!active || !active.rect)
                return;
            if (kind === 'move') {
                const moved = (moveEvent.altKey || moveEvent.shiftKey)
                    ? { x: startRect.x + deltaX, y: startRect.y + deltaY, width: startRect.width, height: startRect.height }
                    : _snapRect({ x: startRect.x + deltaX, y: startRect.y + deltaY, width: startRect.width, height: startRect.height }, active);
                active.rect.x = moved.x;
                active.rect.y = moved.y;
            }
            else if (kind === 'rotate') {
                const pointerX = startRect.x + startRect.width / 2 + deltaX;
                const pointerY = startRect.y + startRect.height / 2 + deltaY;
                let angle = Math.atan2(pointerY - centre.y, pointerX - centre.x) * 180 / Math.PI + 90;
                if (moveEvent.shiftKey)
                    angle = Math.round(angle / 15) * 15; // 15° steps
                active.rotation = ((angle % 360) + 360) % 360;
            }
            else if (kind === 'resize') {
                // Into frame-local space, then scale about the centre.
                const localX = deltaX * cos - deltaY * sin;
                const localY = deltaX * sin + deltaY * cos;
                const signX = (dir === 'ne' || dir === 'se') ? 1 : -1;
                const signY = (dir === 'sw' || dir === 'se') ? 1 : -1;
                const width = Math.max(MIN_LAYER_SIZE, startRect.width + localX * signX);
                const height = Math.max(MIN_LAYER_SIZE, startRect.height + localY * signY);
                if (moveEvent.shiftKey) {
                    // Preserve aspect ratio.
                    const aspect = startRect.width / Math.max(1, startRect.height);
                    active.rect.width = width;
                    active.rect.height = Math.max(MIN_LAYER_SIZE, width / aspect);
                }
                else {
                    active.rect.width = width;
                    active.rect.height = height;
                }
                active.rect.x = centre.x - active.rect.width / 2;
                active.rect.y = centre.y - active.rect.height / 2;
            }
            else if (kind === 'crop') {
                const localX = deltaX * cos - deltaY * sin;
                const localY = deltaX * sin + deltaY * cos;
                const crop = { ...startCrop };
                const deltaCropX = localX * crop.w / Math.max(1, startRect.width);
                const deltaCropY = localY * crop.h / Math.max(1, startRect.height);
                if (dir === 'cx0') {
                    const nextX = Math.max(0, Math.min(crop.x + crop.w - MIN_CROP, crop.x + deltaCropX));
                    active.crop = { ...crop, x: nextX, w: crop.w - (nextX - crop.x) };
                }
                else if (dir === 'cx1') {
                    active.crop = { ...crop, w: Math.max(MIN_CROP, Math.min(1 - crop.x, crop.w + deltaCropX)) };
                }
                else if (dir === 'cy0') {
                    const nextY = Math.max(0, Math.min(crop.y + crop.h - MIN_CROP, crop.y + deltaCropY));
                    active.crop = { ...crop, y: nextY, h: crop.h - (nextY - crop.y) };
                }
                else if (dir === 'cy1') {
                    active.crop = { ...crop, h: Math.max(MIN_CROP, Math.min(1 - crop.y, crop.h + deltaCropY)) };
                }
            }
            _render();
        };
        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            _persist();
            saveToWorld();
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }
    /* ── layer operations ──────────────────────────────────────────────── */
    /** Read a File as a data URL (the local fallback when upload is unavailable). */
    function _readFileAsDataUrl(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ''));
            reader.onerror = () => resolve('');
            reader.readAsDataURL(file);
        });
    }
    function _labelFromFile(file) {
        const base = String((file && file.name) || '').replace(/\.[a-z0-9]+$/i, '');
        return base.slice(0, 40) || 'Image';
    }
    /**
     * Add a NEW layer from a file. Upload first so the world stores a path
     * rather than a multi-megabyte base64 blob inside the scenario JSON; keep
     * the browser-local copy only if the upload fails.
     */
    async function addFromFile(file) {
        if (!file)
            return null;
        let src = null;
        let path = null;
        if (typeof ApiClient !== 'undefined' && ApiClient.uploadBackgroundImage) {
            try {
                const result = await ApiClient.uploadBackgroundImage(file);
                if (result && result.image) {
                    path = result.image;
                    src = result.image;
                }
            }
            catch (error) { /* fall through to the local copy */ }
        }
        if (!src)
            src = await _readFileAsDataUrl(file);
        if (!src)
            return null;
        const layer = {
            id: _uid(),
            label: _labelFromFile(file),
            imagePath: path,
            imageSrc: src,
            image: await _setImageSrc(src),
            rect: null,
            rotation: 0,
            crop: DEFAULT_CROP(),
            opacity: OPACITY_DEFAULT,
            locked: false,
            visible: true,
        };
        state.layers.push(layer);
        state.activeId = layer.id;
        state.editing = true;
        state.cropping = false;
        _fitLayer(layer);
        _render();
        _updateHint();
        _persist();
        saveToWorld(true);
        try {
            events.log(path
                ? `🗺 Map layer "${layer.label}" uploaded — saved to the world as a file path.`
                : `🗺 Map layer "${layer.label}" added (local only — upload failed).`, 'system-msg');
        }
        catch (error) { /* ignore */ }
        return layer;
    }
    function _pickFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.multiple = true;
        input.addEventListener('change', () => {
            const files = Array.from(input.files || []);
            files.reduce((chain, file) => chain.then(() => addFromFile(file)), Promise.resolve());
        });
        input.click();
    }
    /** Fit a layer's rect to the node bounds (contain, never crop). */
    function _fitLayer(layer, padding = 140) {
        if (!layer || !layer.image)
            return;
        const bounds = _nodeBounds();
        const minX = bounds ? bounds.minX : -400;
        const minY = bounds ? bounds.minY : -400;
        const maxX = bounds ? bounds.maxX : 400;
        const maxY = bounds ? bounds.maxY : 400;
        const width = Math.max(1, maxX - minX) + padding * 2;
        const height = Math.max(1, maxY - minY) + padding * 2;
        const centreX = (minX + maxX) / 2;
        const centreY = (minY + maxY) / 2;
        const aspect = (layer.image.width || 1) / (layer.image.height || 1);
        let fitWidth = width;
        let fitHeight = width / aspect;
        if (fitHeight > height) {
            fitHeight = height;
            fitWidth = height * aspect;
        }
        layer.rect = { x: centreX - fitWidth / 2, y: centreY - fitHeight / 2, width: fitWidth, height: fitHeight };
    }
    function fitToNodes(padding = 140) {
        const layer = _active();
        if (!layer || !layer.image)
            return;
        _fitLayer(layer, padding);
        _render();
        _persist();
        saveToWorld();
    }
    function removeLayer(id) {
        const layer = state.layers.find((candidate) => candidate.id === id);
        if (!layer)
            return;
        _removeLayerEl(layer);
        state.layers = state.layers.filter((candidate) => candidate.id !== id);
        if (state.activeId === id) {
            state.activeId = state.layers.length ? state.layers[state.layers.length - 1].id : null;
            state.cropping = false;
        }
        _render();
        _updateHint();
        _persist();
        saveToWorld(true);
    }
    /** Legacy name: removes the active layer (`remove all` lives in the panel). */
    function removeImage() {
        const layer = _active();
        if (layer)
            removeLayer(layer.id);
    }
    function setEditing(on) {
        state.editing = !!on;
        if (!state.editing)
            state.cropping = false;
        _render();
        _updateHint();
    }
    function setCropping(on) {
        state.cropping = !!on;
        if (state.cropping)
            state.editing = true;
        _render();
        _updateHint();
    }
    function setLayerOpacity(id, value, { persist = true } = {}) {
        const layer = state.layers.find((candidate) => candidate.id === id);
        if (!layer)
            return;
        layer.opacity = Math.max(0, Math.min(1, Number(value)));
        _render();
        if (persist) {
            _persist();
            saveToWorld();
        }
    }
    /** Opacity of the active layer (legacy single-image signature). */
    function setOpacity(value) {
        const layer = _active();
        if (layer)
            setLayerOpacity(layer.id, value);
    }
    function setLayerVisibility(id, visible) {
        const layer = state.layers.find((candidate) => candidate.id === id);
        if (!layer)
            return;
        layer.visible = !!visible;
        _render();
        _persist();
        saveToWorld();
    }
    function setLayerLocked(id, locked) {
        const layer = state.layers.find((candidate) => candidate.id === id);
        if (!layer)
            return;
        layer.locked = !!locked;
        _render();
        _persist();
        saveToWorld();
    }
    function renameLayer(id, label) {
        const layer = state.layers.find((candidate) => candidate.id === id);
        if (!layer)
            return;
        layer.label = String(label || '').slice(0, 60);
        _render();
        _persist();
        saveToWorld();
    }
    /** Move a layer in the stack: delta +1 is one step toward the front. */
    function moveLayer(id, delta) {
        const index = state.layers.findIndex((candidate) => candidate.id === id);
        if (index === -1)
            return;
        const target = Math.max(0, Math.min(state.layers.length - 1, index + delta));
        if (target === index)
            return;
        const [layer] = state.layers.splice(index, 1);
        state.layers.splice(target, 0, layer);
        _render();
        _persist();
        saveToWorld();
    }
    function removeAllLayers() {
        state.layers.forEach(_removeLayerEl);
        state.layers = [];
        state.activeId = null;
        state.cropping = false;
        _render();
        _updateHint();
        _persist();
        saveToWorld(true);
    }
    /* ── node layout (unchanged behaviour) ─────────────────────────────── */
    function _capturePositions() {
        const network = _network();
        if (!network)
            return;
        try {
            state.positions = network.getPositions();
        }
        catch (error) { /* ignore */ }
    }
    function _applyPositions() {
        const network = _network();
        if (!network || !state.positions)
            return;
        // Only move nodes still present in the rendered DataSet — saved layouts
        // and IndexedDB records outlive world refetches, projections and
        // filtered views. vis-network LOGS (never throws) on an unknown id, so
        // the try/catch below can't silence it; skip those ids here (bug-36).
        const live = new Set(network.body?.data?.nodes?.getIds?.() || []);
        for (const id of Object.keys(state.positions)) {
            const position = state.positions[id];
            if (!position)
                continue;
            if (!live.has(id))
                continue;
            try {
                network.moveNode(id, position.x, position.y);
            }
            catch (error) { /* node gone */ }
        }
    }
    function setLayoutLocked(locked) {
        state.layoutLocked = !!locked;
        const network = _network();
        if (state.layoutLocked) {
            _applyPositions();
            _capturePositions();
        }
        _applyLockState(network);
        _persist();
        saveToWorld();
        // Locking is the moment a layout becomes intentional — persist it.
        if (state.layoutLocked)
            persistPositionsToWorld();
    }
    /** Legacy name for the node-layout freeze. */
    function setLocked(locked) {
        setLayoutLocked(locked);
    }
    /**
     * Write every node's canvas position into the world as `properties.x`/`y`.
     *
     * This is what makes a layout durable: it survives reloads, travels with the
     * scenario file, and can be committed — unlike the browser-local copy in
     * IndexedDB. One atomic batch request, so it is one undo step.
     */
    async function persistPositionsToWorld() {
        const network = _network();
        if (!network || typeof ApiClient === 'undefined' || !ApiClient.batchGraph)
            return { saved: 0 };
        let positions = {};
        try {
            positions = network.getPositions();
        }
        catch (error) {
            return { saved: 0 };
        }
        const ops = [];
        for (const id of Object.keys(positions)) {
            const position = positions[id];
            if (!position)
                continue;
            ops.push({
                type: 'update_node',
                payload: {
                    node_id: id,
                    patch: {
                        properties: {
                            x: Math.round(position.x * 10) / 10,
                            y: Math.round(position.y * 10) / 10,
                        },
                    },
                },
            });
        }
        if (!ops.length)
            return { saved: 0 };
        try {
            const result = await ApiClient.batchGraph(ops);
            const failures = result && result.errors ? result.errors.length : 0;
            try {
                events.log(`💾 Layout saved to the world: ${ops.length} node position(s)` +
                    (failures ? `, ${failures} failed` : '') + '.', failures ? 'error-msg' : 'system-msg');
            }
            catch (error) { /* ignore */ }
            return { saved: ops.length, failures };
        }
        catch (error) {
            try {
                events.log('💾 Layout save failed — see the console.', 'error-msg');
            }
            catch (innerError) { /* ignore */ }
            return { saved: 0 };
        }
    }
    function savePositions() {
        _capturePositions();
        _persist();
        const count = Object.keys(state.positions).length;
        try {
            events.log(`💾 Graph layout captured (${count} nodes)`, 'system-msg');
        }
        catch (error) { /* ignore */ }
        persistPositionsToWorld();
    }
    /* ── layer panel ───────────────────────────────────────────────────── */
    function _ensurePanel() {
        if (state.panel)
            return;
        const container = document.getElementById('graph-container');
        if (!container)
            return;
        const panel = document.createElement('div');
        panel.id = 'gbg-panel';
        panel.style.cssText = 'position:absolute;right:8px;top:8px;z-index:6;width:210px;background:rgba(13,17,23,0.94);border:1px solid var(--border,#444);border-radius:6px;font-size:11px;color:var(--text,#eee);display:none;overflow:hidden;';
        panel.addEventListener('mousedown', (event) => event.stopPropagation());
        panel.addEventListener('click', _onPanelClick);
        panel.addEventListener('dragstart', (event) => {
            const target = event.target;
            const row = target?.closest('[data-row-layer]');
            if (!row)
                return;
            state._dragLayerId = row.dataset.rowLayer || null;
            try {
                if (event.dataTransfer) {
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', state._dragLayerId || '');
                }
            }
            catch (error) { /* ignore */ }
        });
        // Reorder on DROP only: the panel is rewritten on every _render(), so a
        // live dragover preview would destroy the element being dragged.
        panel.addEventListener('dragover', (event) => {
            if (!state._dragLayerId)
                return;
            const target = event.target;
            if (!target?.closest('[data-row-layer]'))
                return;
            event.preventDefault();
            try {
                if (event.dataTransfer)
                    event.dataTransfer.dropEffect = 'move';
            }
            catch (error) { /* ignore */ }
        });
        panel.addEventListener('drop', (event) => {
            const target = event.target;
            const row = target?.closest('[data-row-layer]');
            if (!row || !state._dragLayerId)
                return;
            event.preventDefault();
            const dragging = state._dragLayerId;
            const overId = row.dataset.rowLayer || null;
            state._dragLayerId = null;
            if (!overId || dragging === overId)
                return;
            const from = state.layers.findIndex((layer) => layer.id === dragging);
            const to = state.layers.findIndex((layer) => layer.id === overId);
            if (from === -1 || to === -1)
                return;
            const [layer] = state.layers.splice(from, 1);
            state.layers.splice(to, 0, layer);
            _render();
            _persist();
            saveToWorld();
        });
        panel.addEventListener('dragend', () => { state._dragLayerId = null; });
        container.appendChild(panel);
        state.panel = panel;
    }
    function _onPanelClick(event) {
        const target = event.target;
        const el = target?.closest('[data-act]');
        if (!el)
            return;
        const action = el.dataset.act;
        const id = el.dataset.id || null;
        switch (action) {
            case 'add':
                _pickFile();
                break;
            case 'done':
                setEditing(false);
                break;
            case 'select':
                if (id)
                    _setActive(id);
                break;
            case 'visible': {
                const layer = state.layers.find((candidate) => candidate.id === id);
                if (layer && id)
                    setLayerVisibility(id, !layer.visible);
                break;
            }
            case 'lock': {
                const layer = state.layers.find((candidate) => candidate.id === id);
                if (layer && id)
                    setLayerLocked(id, !layer.locked);
                break;
            }
            case 'rename': {
                const layer = state.layers.find((candidate) => candidate.id === id);
                if (!layer || !id)
                    break;
                const value = prompt('Layer name:', layer.label || '');
                if (value !== null)
                    renameLayer(id, value);
                break;
            }
            case 'up':
                if (id)
                    moveLayer(id, 1);
                break;
            case 'down':
                if (id)
                    moveLayer(id, -1);
                break;
            case 'remove':
                if (id)
                    removeLayer(id);
                break;
            case 'removeAll':
                removeAllLayers();
                break;
            default: break;
        }
    }
    function _renderPanel() {
        const panel = state.panel;
        if (!panel)
            return;
        const show = (state.editing || state.cropping) && state.layers.length > 0;
        panel.style.display = show ? 'block' : 'none';
        if (!show)
            return;
        // _render() runs on every mousemove of a drag; rewriting innerHTML that
        // often is wasteful and fights drag-and-drop, so only redraw when the
        // list actually changes.
        const signature = state.layers
            .map((layer) => `${layer.id}:${layer.visible ? 1 : 0}${layer.locked ? 1 : 0}:${layer.label}`)
            .join('|') + `#${state.activeId}#${state.layers.length}`;
        if (signature === state._panelSignature)
            return;
        state._panelSignature = signature;
        const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
        const esc = (value) => String(value == null ? '' : value)
            .replace(/[&<>"]/g, (character) => entities[character]);
        const rows = state.layers.map((layer, index) => {
            const isActive = layer.id === state.activeId;
            return `<div data-row-layer="${layer.id}" draggable="true" data-act="select" data-id="${layer.id}"
                style="display:flex;align-items:center;gap:4px;padding:3px 6px;cursor:pointer;border-left:2px solid ${isActive ? '#58a6ff' : 'transparent'};background:${isActive ? 'rgba(88,166,255,0.12)' : 'transparent'};">
                <span style="opacity:0.6;cursor:grab;">⠿</span>
                <span data-act="visible" data-id="${layer.id}" title="Show/hide" style="cursor:pointer;">${layer.visible ? '👁' : '🚫'}</span>
                <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(layer.label)}">${esc(layer.label || ('Layer ' + (index + 1)))}</span>
                <span data-act="lock" data-id="${layer.id}" title="${layer.locked ? 'Unlock (drag)' : 'Lock (no dragging)'}" style="cursor:pointer;">${layer.locked ? '🔒' : '🔓'}</span>
                <span data-act="up" data-id="${layer.id}" title="Bring forward" style="cursor:pointer;opacity:${index === state.layers.length - 1 ? 0.3 : 1};">▲</span>
                <span data-act="down" data-id="${layer.id}" title="Send back" style="cursor:pointer;opacity:${index === 0 ? 0.3 : 1};">▼</span>
                <span data-act="rename" data-id="${layer.id}" title="Rename" style="cursor:pointer;">✎</span>
                <span data-act="remove" data-id="${layer.id}" title="Remove" style="cursor:pointer;color:#f85149;">🗑</span>
            </div>`;
        }).join('');
        panel.innerHTML = `
            <div style="display:flex;align-items:center;gap:6px;padding:5px 6px;border-bottom:1px solid var(--border,#444);">
                <span style="flex:1;font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-dim,#999);">🗺 Maps (${state.layers.length})</span>
                <span data-act="add" title="Add another image" style="cursor:pointer;">➕</span>
                <span data-act="removeAll" title="Remove all layers" style="cursor:pointer;color:#f85149;">🗑</span>
                <span data-act="done" title="Done editing" style="cursor:pointer;">✔</span>
            </div>
            ${rows}`;
    }
    /* ── keyboard nudges ───────────────────────────────────────────────── */
    function _onKeyDown(event) {
        if (!state.editing)
            return;
        const layer = _active();
        if (!layer || !layer.rect || layer.locked)
            return;
        const target = event.target;
        const tag = (target && target.tagName) || '';
        if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable)
            return;
        if (event.ctrlKey || event.metaKey || event.altKey)
            return;
        const step = event.shiftKey ? 10 : 1;
        let deltaX = 0;
        let deltaY = 0;
        if (event.key === 'ArrowLeft')
            deltaX = -step;
        else if (event.key === 'ArrowRight')
            deltaX = step;
        else if (event.key === 'ArrowUp')
            deltaY = -step;
        else if (event.key === 'ArrowDown')
            deltaY = step;
        else
            return;
        event.preventDefault();
        layer.rect.x += deltaX;
        layer.rect.y += deltaY;
        _render();
        if (state._nudgeTimer)
            clearTimeout(state._nudgeTimer);
        state._nudgeTimer = setTimeout(() => { _persist(); saveToWorld(); }, 300);
    }
    /* ── on-canvas hint (only while editing) ───────────────────────────── */
    function _updateHint() {
        let chip = document.getElementById('gbg-hint');
        if (!state.editing) {
            if (chip)
                chip.remove();
            return;
        }
        if (!chip) {
            chip = document.createElement('div');
            chip.id = 'gbg-hint';
            chip.style.cssText = 'position:absolute;left:50%;bottom:10px;transform:translateX(-50%);z-index:6;background:rgba(13,17,23,0.92);border:1px solid var(--border,#444);border-radius:6px;padding:6px 10px;font-size:11px;color:var(--text,#eee);display:flex;gap:8px;align-items:center;';
            const container = document.getElementById('graph-container');
            if (container)
                container.appendChild(chip);
        }
        const layer = _active();
        chip.innerHTML = `<span>${state.cropping
            ? '✂ drag the amber edges to crop'
            : (layer ? '🖼 drag to move · corners resize · top dot rotates · alt-click cycles' : '🖼 add an image from the panel')}</span>
            <label style="display:flex;align-items:center;gap:4px;">🎚<input id="gbg-op" type="range" min="0" max="1" step="0.05" value="${layer ? layer.opacity : OPACITY_DEFAULT}" style="width:70px;"></label>
            <button class="btn btn-sm" id="gbg-crop">${state.cropping ? 'Done cropping' : '✂ Crop'}</button>
            <button class="btn btn-sm" id="gbg-done">✔ Done</button>`;
        const opacitySlider = chip.querySelector('#gbg-op');
        opacitySlider?.addEventListener('input', (inputEvent) => setOpacity(inputEvent.target.value));
        const cropButton = chip.querySelector('#gbg-crop');
        cropButton?.addEventListener('click', () => setCropping(!state.cropping));
        const doneButton = chip.querySelector('#gbg-done');
        doneButton?.addEventListener('click', () => setEditing(false));
    }
    /* ── right-click menu ──────────────────────────────────────────────── */
    function showCanvasMenu(event) {
        const menu = document.getElementById('context-menu');
        if (!menu)
            return;
        const hasLayers = state.layers.length > 0;
        const layer = _active();
        const item = (action, label, active = false, hint = '', color = '') => `<div class="context-menu-item" data-gbg="${action}" style="${color ? `color:${color};` : ''}">${label}${hint ? `<span style="float:right;color:var(--text-dim);">${hint}</span>` : ''}${active ? ' <span style="color:#58a6ff;">●</span>' : ''}</div>`;
        const separator = '<div class="context-menu-separator"></div>';
        const rows = ['<div class="context-menu-header" style="padding:6px 12px;font-size:10px;color:var(--text-dim);border-bottom:1px solid var(--border-light);text-transform:uppercase;letter-spacing:0.5px;">🗺 Graph map</div>'];
        rows.push(item('add', hasLayers ? '🖼 Add another image…' : '🖼 Add background image…'));
        if (hasLayers) {
            rows.push(item('edit', state.editing ? '✔ Done editing' : '🖼 Edit images', state.editing));
            rows.push(item('crop', state.cropping ? '✔ Done cropping' : '✂ Crop', state.cropping));
            rows.push(item('fit', '⤢ Fit to nodes', false, '', layer ? '' : '#666'));
            rows.push(item('opacity', '🎚 Opacity…', false, layer ? Math.round(layer.opacity * 100) + '%' : ''));
            rows.push(item('layer-lock', layer && layer.locked ? '🔓 Unlock image' : '🔒 Lock image', !!(layer && layer.locked)));
            rows.push(item('remove', '🗑 Remove image', false, '', '#f85149'));
        }
        rows.push(separator);
        rows.push(item('lock', state.layoutLocked ? '🔓 Unlock nodes' : '🔒 Lock nodes', state.layoutLocked));
        rows.push(item('save', '💾 Save layout to world'));
        menu.innerHTML = rows.join('');
        menu.style.display = 'block';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        setTimeout(() => document.addEventListener('click', () => { menu.style.display = 'none'; }, { once: true }), 0);
        menu.querySelectorAll('[data-gbg]').forEach((element) => {
            element.addEventListener('click', () => {
                menu.style.display = 'none';
                _menuAction(element.dataset.gbg || '');
            });
        });
    }
    function _menuAction(action) {
        const layer = _active();
        switch (action) {
            case 'add':
                _pickFile();
                break;
            case 'edit':
                setEditing(!state.editing);
                break;
            case 'crop':
                setCropping(!state.cropping);
                break;
            case 'fit':
                fitToNodes();
                break;
            case 'opacity': {
                if (!layer)
                    break;
                const value = prompt('Layer opacity (0-100):', String(Math.round(layer.opacity * 100)));
                if (value !== null)
                    setOpacity(Number(value) / 100);
                break;
            }
            case 'layer-lock':
                if (layer)
                    setLayerLocked(layer.id, !layer.locked);
                break;
            case 'remove':
                removeImage();
                break;
            case 'lock':
                setLayoutLocked(!state.layoutLocked);
                break;
            case 'save':
                savePositions();
                break;
            default: break;
        }
    }
    async function init() {
        _ensureLayers();
        const network = _network();
        const container = document.getElementById('graph-container');
        if (container) {
            // Keep the maps glued to the graph view on every redraw (pan, zoom,
            // drag) — afterDrawing fires with the view transform already applied.
            const sync = () => _syncView();
            if (network) {
                try {
                    network.on('afterDrawing', sync);
                }
                catch (error) { /* ignore */ }
            }
            window.addEventListener('resize', sync);
        }
        document.addEventListener('keydown', _onKeyDown);
        await _restore();
        _applyLockState(network);
        _render();
        // The WORLD is authoritative: whenever it is (re)fetched — including
        // after loading a different scenario — re-derive the maps from it
        // instead of leaving whatever was on screen. Loading the camp after a
        // map was added elsewhere must NOT show that other world's map.
        if (typeof appEvents !== 'undefined' && appEvents && appEvents.on) {
            appEvents.on('state:updated', () => { _onWorldRefetched(); });
        }
    }
    /** Re-apply physics for the current lock state, undoing our own freeze. */
    function _applyLockState(network) {
        if (state.layoutLocked) {
            if (network)
                network.setOptions({ physics: { enabled: false } });
            if (typeof graphManager !== 'undefined' && graphManager)
                graphManager._physicsEnabled = false;
            state.physicsDisabledByLock = true;
        }
        else if (state.physicsDisabledByLock) {
            // WE froze physics for the previous world's lock — undo it, so a new
            // scenario doesn't inherit the old one's frozen layout.
            if (network)
                network.setOptions({ physics: { enabled: true } });
            if (typeof graphManager !== 'undefined' && graphManager)
                graphManager._physicsEnabled = true;
            state.physicsDisabledByLock = false;
        }
    }
    /** The world was refetched: restore (or clear) this world's maps. */
    async function _onWorldRefetched() {
        // Never stomp an edit in progress — a debounced save is still in flight.
        if (state.editing)
            return;
        await _restore();
        _applyLockState(_network());
        if (Object.keys(state.positions).length)
            _applyPositions();
        _render();
    }
    /**
     * Visible map layers, decoded and ready to rasterise. Exposed so the PNG
     * exporter redraws exactly the maps on screen (crop, rotation and opacity
     * included) without reaching into module state.
     */
    function getExportLayers() {
        return state.layers
            .filter((layer) => !!(layer.visible && layer.image && layer.rect))
            .map((layer) => ({
            image: layer.image,
            rect: { x: layer.rect.x, y: layer.rect.y, width: layer.rect.width, height: layer.rect.height },
            rotation: layer.rotation,
            crop: { x: layer.crop.x, y: layer.crop.y, w: layer.crop.w, h: layer.crop.h },
            opacity: layer.opacity,
        }));
    }
    const api = {
        init,
        reset,
        addFromFile,
        showCanvasMenu,
        fitToNodes,
        setEditing,
        setCropping,
        setOpacity,
        setLayerOpacity,
        setLayerVisibility,
        setLayerLocked,
        renameLayer,
        moveLayer,
        removeLayer,
        removeAllLayers,
        setLocked,
        setLayoutLocked,
        savePositions,
        persistPositionsToWorld,
        removeImage,
        getExportLayers,
        _state: state,
        // Pure logic exposed for tools/unit/run.cjs. Not a product API.
        _internals: {
            _normalizeLayer,
            _normalizeBlock,
            _hasBackground,
            _snapshot,
            _pointInLayer,
            _layersAt,
            _snapRect,
            _clientToGraph,
        },
    };
    // Classic script: publish on window (no import/export — see the migration doc).
    window.GraphBackground = api;
})();
