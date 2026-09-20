/**
 * graph-background.js — reference map behind the vis.js graph.
 *
 * @module graph/graph-background — the reference map overlay
 * @contributes the map image, its transform (rect/rotation/crop/opacity), and per-scenario layout persistence
 * @powers the right-click 🗺 map: drag/resize/rotate/crop a background and lock node positions
 * @relates uses storage (graph_assets) + the graphManager.network view transform; opened from GraphEventHandlers.onContext
 * @docs none
 *
 * UX: right-click empty canvas → 🗺 Add background image. In edit mode the
 * image gets on-canvas handles: drag the body to move, corners to scale about
 * the centre, the top handle to rotate, and (in crop mode) the inner edge
 * handles to crop. Nothing else is on screen.
 *
 * Rendering: an <img> layer is inserted as the container's FIRST child, so it
 * paints beneath the (transparent) vis canvas — nodes draw over the map, and
 * the map never covers the legend. The layer is kept in sync with the network
 * view transform on every `afterDrawing`, so it pans/zooms with the graph.
 * A second, small handle layer sits above the canvas (pointer-events: none,
 * handles only) so the handles stay clickable.
 *
 * Persistence: IndexedDB store `graph_assets`, keyed by scenario name:
 * { image (data URL), rect, rotation, crop, opacity, locked, positions }.
 */
(() => {
    'use strict';

    const STORE = 'graph_assets';
    const OPACITY_DEFAULT = 0.45;
    const HANDLE = 10;

    const state = {
        physicsDisabledByLock: false,                 // did WE freeze physics for a lock?
        imagePath: null,                              // /static/images/backgrounds/… (in the world)
        image: null,                                  // HTMLImageElement
        rect: null,                                   // {x, y, width, height} in graph space
        rotation: 0,                                  // degrees
        crop: { x: 0, y: 0, w: 1, h: 1 },             // normalised source window
        opacity: OPACITY_DEFAULT,
        locked: false,
        positions: {},                                // nodeId -> {x, y}
        key: null,
        editing: false,
        cropping: false,
        layer: null, space: null, frame: null, img: null,
        handleLayer: null, handleSpace: null, handles: null,
    };

    function _network() {
        return (typeof graphManager !== 'undefined' && graphManager && graphManager.network) || null;
    }

    function _scenarioKey() {
        const raw = (typeof worldState !== 'undefined' && worldState && worldState.data) || {};
        return raw._scenario_name || (document.body && document.body.dataset && document.body.dataset.scenarioName) || 'default';
    }

    /**
     * The scenario's identity, or null when the world has no name.
     *
     * The IndexedDB cache is keyed on this. An unnamed scenario returns null so
     * the cache is NOT consulted at all — otherwise every unnamed scenario would
     * share the 'default' slot and a map added in one would appear in the next.
     */
    function _scenarioIdentity() {
        const raw = (typeof worldState !== 'undefined' && worldState && worldState.data) || {};
        return String(raw._scenario_name || '').trim() || null;
    }

    /** Drop all background state WITHOUT persisting it (scenario changed). */
    function reset() {
        state.image = null;
        state.imagePath = null;
        state.rect = null;
        state.rotation = 0;
        state.crop = { x: 0, y: 0, w: 1, h: 1 };
        state.opacity = OPACITY_DEFAULT;
        state.locked = false;
        state.positions = {};
        state.editing = false;
        state.cropping = false;
        _render();
        _updateHint();
    }

    /**
     * Persist the map's path + transform on the WORLD (scenario-level), so it
     * travels with the file and can be committed. Debounced: drags call this on
     * pointer-up, not per frame.
     */
    let _worldSaveTimer = null;
    function saveToWorld(immediate = false) {
        if (typeof ApiClient === 'undefined' || !ApiClient.saveGraphBackground) return;
        const payload = {
            image: state.imagePath || null,
            rect: state.rect,
            rotation: state.rotation,
            crop: state.crop,
            opacity: state.opacity,
            locked: state.locked,
        };
        const post = () => {
            ApiClient.saveGraphBackground(payload).catch(() => { /* local copy still has it */ });
        };
        clearTimeout(_worldSaveTimer);
        if (immediate) { post(); return; }
        _worldSaveTimer = setTimeout(post, 400);
    }

    async function _persist() {
        if (typeof storage === 'undefined' || !storage || !state.key) return;
        try {
            await storage.set(STORE, state.key, {
                key: state.key,
                // Store the PATH when we have one — never duplicate a big base64
                // blob that already lives on the server.
                image: state.imagePath || (state.image ? state.image.src : null),
                rect: state.rect,
                rotation: state.rotation,
                crop: state.crop,
                opacity: state.opacity,
                locked: state.locked,
                positions: state.positions,
                updated: Date.now(),
            });
        } catch (e) { /* ignore */ }
    }

    function _setImageSrc(src) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => { state.image = img; resolve(true); };
            img.onerror = () => { state.image = null; resolve(false); };
            img.src = src;
        });
    }

    async function _restore() {
        state.key = _scenarioKey();
        const identity = _scenarioIdentity();
        // The WORLD copy wins — it travels with the scenario and can be
        // committed. IndexedDB is only a local fallback, and only for a NAMED
        // scenario: with no name there is no way to tell two worlds apart, so
        // showing a cached map would leak it into the next scenario.
        let record = (typeof worldState !== 'undefined' && worldState?.data?.graph_background) || null;
        if (!record && identity && typeof storage !== 'undefined' && storage) {
            try { record = await storage.get(STORE, state.key); } catch (e) { record = null; }
        }
        if (!record) {
            // This world has no background of its own — show NOTHING rather than
            // leaving the previous scenario's map on screen. (No-op when we are
            // already clear, so frequent state updates stay cheap.)
            if (state.image || state.rect) reset();
            return;
        }
        if (typeof record.opacity === 'number') state.opacity = record.opacity;
        if (typeof record.rotation === 'number') state.rotation = record.rotation;
        if (record.crop && typeof record.crop.w === 'number') state.crop = record.crop;
        state.locked = !!record.locked;
        state.positions = record.positions || {};
        state.rect = record.rect || null;
        if (record.image) {
            const src = String(record.image);
            // A server path travels with the world; a data: URL is a local copy.
            state.imagePath = src.startsWith('/static/') ? src : null;
            await _setImageSrc(src);
        }
    }

    /* ── view sync ─────────────────────────────────────────────────────── */

    function _syncView() {
        const net = _network();
        if (!net || !state.space) return;
        const container = document.getElementById('graph-container');
        const w = container ? container.clientWidth : 0;
        const h = container ? container.clientHeight : 0;
        let scale = 1, pos = { x: 0, y: 0 };
        try { scale = net.getScale(); pos = net.getViewPosition(); } catch (e) { return; }
        const t = `translate(${w / 2}px, ${h / 2}px) scale(${scale}) translate(${-pos.x}px, ${-pos.y}px)`;
        state.space.style.transform = t;
        if (state.handleSpace) state.handleSpace.style.transform = t;
    }

    /* ── DOM rendering ─────────────────────────────────────────────────── */

    function _ensureLayers() {
        if (state.layer) return;
        const container = document.getElementById('graph-container');
        if (!container) return;

        const layer = document.createElement('div');
        layer.id = 'graph-bg-layer';
        layer.style.cssText = 'position:absolute;inset:0;overflow:hidden;pointer-events:none;';
        const space = document.createElement('div');
        space.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;transform-origin:0 0;';
        const frame = document.createElement('div');
        frame.style.cssText = 'position:absolute;transform-origin:center center;overflow:hidden;pointer-events:none;';
        const img = document.createElement('img');
        img.style.cssText = 'position:absolute;left:0;top:0;transform-origin:0 0;pointer-events:none;user-select:none;';
        img.draggable = false;
        frame.appendChild(img);
        space.appendChild(frame);
        layer.appendChild(space);
        // First child ⇒ paints beneath the transparent canvas (nodes over map).
        container.insertBefore(layer, container.firstChild);

        const hLayer = document.createElement('div');
        hLayer.id = 'graph-bg-handle-layer';
        hLayer.style.cssText = 'position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:5;';
        const hSpace = document.createElement('div');
        hSpace.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;transform-origin:0 0;';
        hLayer.appendChild(hSpace);
        container.appendChild(hLayer);

        state.layer = layer;
        state.space = space;
        state.frame = frame;
        state.img = img;
        state.handleLayer = hLayer;
        state.handleSpace = hSpace;

        _buildHandles();
        frame.addEventListener('mousedown', (ev) => {
            if (!state.editing) return;
            _startDrag(ev, 'move', null);
        });
    }

    function _handleEl(dir, css) {
        const el = document.createElement('div');
        el.dataset.dir = dir;
        el.style.cssText = css;
        el.addEventListener('mousedown', (ev) => {
            if (!state.editing) return;
            const kind = dir === 'rot' ? 'rotate' : (dir.indexOf('c') === 0 ? 'crop' : 'resize');
            _startDrag(ev, kind, dir);
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
        // Handles live INSIDE the frame so they inherit its rotation; the crop
        // shade does too.
        state.frame.appendChild(cropShade);
        Object.values(corners).forEach(el => state.frame.appendChild(el));
        state.frame.appendChild(rotate);
        ['cx0', 'cx1', 'cy0', 'cy1'].forEach(k => state.frame.appendChild(state.handles[k]));
    }

    function _positionHandles() {
        const h = state.handles;
        if (!h || !state.rect) return;
        const w = state.rect.width;
        const ht = state.rect.height;
        const show = state.editing;
        const cropShow = state.editing && state.cropping;
        const place = (el, x, y, visible) => {
            el.style.display = visible ? 'block' : 'none';
            if (visible) { el.style.left = x + 'px'; el.style.top = y + 'px'; }
        };
        place(h.corners.nw, 0, 0, show);
        place(h.corners.ne, w, 0, show);
        place(h.corners.se, w, ht, show);
        place(h.corners.sw, 0, ht, show);
        place(h.rotate, w / 2, -30, show);
        const c = state.crop;
        place(h.cx0, c.x * w, ht / 2, cropShow);
        place(h.cx1, (c.x + c.w) * w, ht / 2, cropShow);
        place(h.cy0, w / 2, c.y * ht, cropShow);
        place(h.cy1, w / 2, (c.y + c.h) * ht, cropShow);
        h.cropShade.style.display = cropShow ? 'block' : 'none';
        if (cropShow) {
            h.cropShade.style.left = (c.x * w) + 'px';
            h.cropShade.style.top = (c.y * ht) + 'px';
            h.cropShade.style.width = (c.w * w) + 'px';
            h.cropShade.style.height = (c.h * ht) + 'px';
        }
    }

    function _render() {
        _ensureLayers();
        if (!state.layer) return;
        const has = !!(state.image && state.rect);
        state.layer.style.display = has ? 'block' : 'none';
        state.handleLayer.style.display = has && state.editing ? 'block' : 'none';
        if (!has) { _syncView(); return; }

        const r = state.rect;
        const c = state.crop;
        const frame = state.frame;
        frame.style.left = r.x + 'px';
        frame.style.top = r.y + 'px';
        frame.style.width = r.width + 'px';
        frame.style.height = r.height + 'px';
        frame.style.transform = `rotate(${state.rotation}deg)`;
        frame.style.opacity = String(state.opacity);
        frame.style.pointerEvents = state.editing ? 'auto' : 'none';
        frame.style.cursor = state.editing ? 'move' : 'default';
        frame.style.outline = state.editing ? '1px dashed rgba(88,166,255,0.8)' : 'none';

        // Crop is modelled as a scaled image inside an overflow-hidden frame:
        // the cropped fraction is enlarged to fill the frame.
        const dw = r.width / Math.max(0.01, c.w);
        const dh = r.height / Math.max(0.01, c.h);
        if (state.img.src !== state.image.src) state.img.src = state.image.src;
        state.img.style.width = dw + 'px';
        state.img.style.height = dh + 'px';
        state.img.style.left = (-c.x * dw) + 'px';
        state.img.style.top = (-c.y * dh) + 'px';

        _positionHandles();
        _syncView();
    }

    /* ── interaction ───────────────────────────────────────────────────── */

    function _startDrag(ev, kind, dir) {
        _ensureLayers();
        if (!state.editing || !state.rect) return;
        ev.preventDefault();
        ev.stopPropagation();

        const net = _network();
        const scale = net ? net.getScale() : 1;
        const startMouse = { x: ev.clientX, y: ev.clientY };
        const startRect = { x: state.rect.x, y: state.rect.y, width: state.rect.width, height: state.rect.height };
        const startCrop = { x: state.crop.x, y: state.crop.y, w: state.crop.w, h: state.crop.h };
        const startRotation = state.rotation;
        const rad = (startRotation * Math.PI) / 180;
        const cos = Math.cos(-rad);
        const sin = Math.sin(-rad);
        const centre = {
            x: startRect.x + startRect.width / 2,
            y: startRect.y + startRect.height / 2,
        };

        const onMove = (e) => {
            const dgx = (e.clientX - startMouse.x) / (scale || 1);
            const dgy = (e.clientY - startMouse.y) / (scale || 1);

            if (kind === 'move') {
                state.rect.x = startRect.x + dgx;
                state.rect.y = startRect.y + dgy;
            } else if (kind === 'rotate') {
                const gx = startRect.x + startRect.width / 2 + dgx;
                const gy = startRect.y + startRect.height / 2 + dgy;
                let angle = Math.atan2(gy - centre.y, gx - centre.x) * 180 / Math.PI + 90;
                state.rotation = ((angle % 360) + 360) % 360;
            } else if (kind === 'resize') {
                // Into frame-local space, then scale about the centre.
                const lx = dgx * cos - dgy * sin;
                const ly = dgx * sin + dgy * cos;
                const sx = (dir === 'ne' || dir === 'se') ? 1 : -1;
                const sy = (dir === 'sw' || dir === 'se') ? 1 : -1;
                const w = Math.max(40, startRect.width + lx * sx);
                const h = Math.max(40, startRect.height + ly * sy);
                state.rect.width = w;
                state.rect.height = h;
                state.rect.x = centre.x - w / 2;
                state.rect.y = centre.y - h / 2;
            } else if (kind === 'crop') {
                const lx = dgx * cos - dgy * sin;
                const ly = dgx * sin + dgy * cos;
                const c = { ...startCrop };
                const dx = lx * c.w / Math.max(1, startRect.width);
                const dy = ly * c.h / Math.max(1, startRect.height);
                const MIN = 0.05;
                if (dir === 'cx0') {
                    const nx = Math.max(0, Math.min(c.x + c.w - MIN, c.x + dx));
                    const nw = c.w - (nx - c.x);
                    state.crop = { ...c, x: nx, w: nw };
                } else if (dir === 'cx1') {
                    state.crop = { ...c, w: Math.max(MIN, Math.min(1 - c.x, c.w + dx)) };
                } else if (dir === 'cy0') {
                    const ny = Math.max(0, Math.min(c.y + c.h - MIN, c.y + dy));
                    const nh = c.h - (ny - c.y);
                    state.crop = { ...c, y: ny, h: nh };
                } else if (dir === 'cy1') {
                    state.crop = { ...c, h: Math.max(MIN, Math.min(1 - c.y, c.h + dy)) };
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

    /* ── public actions ────────────────────────────────────────────────── */

    /** Read a File as a data URL (the local fallback when upload is unavailable). */
    function _readFileAsDataUrl(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ''));
            reader.onerror = () => resolve('');
            reader.readAsDataURL(file);
        });
    }

    async function addFromFile(file) {
        if (!file) return;

        // 1. Upload the FILE, so the world stores a path rather than a
        //    multi-megabyte base64 blob inside the scenario JSON.
        let src = null;
        if (typeof ApiClient !== 'undefined' && ApiClient.uploadBackgroundImage) {
            try {
                const result = await ApiClient.uploadBackgroundImage(file);
                if (result && result.image) {
                    state.imagePath = result.image;
                    src = result.image;
                }
            } catch (e) { /* fall through to the local copy */ }
        }
        // 2. Fallback: keep it browser-local if the upload failed.
        if (!src) {
            src = await _readFileAsDataUrl(file);
            state.imagePath = null;
        }
        if (!src || !(await _setImageSrc(src))) return;

        state.rotation = 0;
        state.crop = { x: 0, y: 0, w: 1, h: 1 };
        state.editing = true;
        state.cropping = false;
        fitToNodes();
        _render();
        saveToWorld(true);
        try {
            events.log(
                state.imagePath
                    ? '🗺 Background map uploaded — saved to the world as a file path.'
                    : '🗺 Background image added (local only — upload failed).',
                'system-msg',
            );
        } catch (e) { /* ignore */ }
    }

    function _pickFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.addEventListener('change', () => {
            const file = input.files && input.files[0];
            if (file) addFromFile(file);
        });
        input.click();
    }

    function fitToNodes(padding = 140) {
        if (!state.image) return;
        const net = _network();
        let positions = {};
        try { positions = net ? net.getPositions() : {}; } catch (e) { positions = {}; }
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const id of Object.keys(positions)) {
            const p = positions[id];
            if (!p) continue;
            minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
            minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
        }
        if (!isFinite(minX)) { minX = minY = -400; maxX = maxY = 400; }
        const w = Math.max(1, maxX - minX) + padding * 2;
        const h = Math.max(1, maxY - minY) + padding * 2;
        const cx = (minX + maxX) / 2;
        const cy = (minY + maxY) / 2;
        const aspect = (state.image.width || 1) / (state.image.height || 1);
        let iw = w;
        let ih = w / aspect;
        if (ih > h) { ih = h; iw = h * aspect; }             // contain, never crop
        state.rect = { x: cx - iw / 2, y: cy - ih / 2, width: iw, height: ih };
        _render();
        _persist();
        saveToWorld();
    }

    function setEditing(on) {
        state.editing = !!on;
        if (!state.editing) state.cropping = false;
        _render();
        _updateHint();
    }

    function setCropping(on) {
        state.cropping = !!on;
        if (state.cropping) state.editing = true;
        _render();
        _updateHint();
    }

    function setOpacity(value) {
        state.opacity = Math.max(0, Math.min(1, Number(value)));
        _render();
        _persist();
        saveToWorld();
    }

    function removeImage() {
        state.image = null;
        state.rect = null;
        state.editing = false;
        state.cropping = false;
        state.imagePath = null;
        _render();
        _persist();
        saveToWorld(true);
    }

    function _capturePositions() {
        const net = _network();
        if (!net) return;
        try { state.positions = net.getPositions(); } catch (e) { /* ignore */ }
    }

    function _applyPositions() {
        const net = _network();
        if (!net || !state.positions) return;
        for (const id of Object.keys(state.positions)) {
            const pos = state.positions[id];
            if (!pos) continue;
            try { net.moveNode(id, pos.x, pos.y); } catch (e) { /* node gone */ }
        }
    }

    function setLocked(locked) {
        state.locked = !!locked;
        const net = _network();
        if (state.locked) { _applyPositions(); _capturePositions(); }
        _applyLockState(net);
        _persist();
        saveToWorld();
        // Locking is the moment a layout becomes intentional — persist it.
        if (state.locked) persistPositionsToWorld();
    }

    /**
     * Write every node's canvas position into the world as `properties.x`/`y`.
     *
     * This is what makes a layout durable: it survives reloads, travels with the
     * scenario file, and can be committed — unlike the browser-local copy in
     * IndexedDB. One atomic batch request, so it is one undo step.
     */
    async function persistPositionsToWorld() {
        const net = _network();
        if (!net || typeof ApiClient === 'undefined' || !ApiClient.batchGraph) return { saved: 0 };
        let positions = {};
        try { positions = net.getPositions(); } catch (e) { return { saved: 0 }; }

        const ops = [];
        for (const id of Object.keys(positions)) {
            const position = positions[id];
            if (!position) continue;
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
        if (!ops.length) return { saved: 0 };
        try {
            const result = await ApiClient.batchGraph(ops);
            const failures = result && result.errors ? result.errors.length : 0;
            try {
                events.log(
                    `💾 Layout saved to the world: ${ops.length} node position(s)` +
                    (failures ? `, ${failures} failed` : '') + '.',
                    failures ? 'error-msg' : 'system-msg',
                );
            } catch (e) { /* ignore */ }
            return { saved: ops.length, failures };
        } catch (e) {
            try { events.log('💾 Layout save failed — see the console.', 'error-msg'); } catch (err) { /* ignore */ }
            return { saved: 0 };
        }
    }

    function savePositions() {
        _capturePositions();
        _persist();
        const count = Object.keys(state.positions).length;
        try { events.log(`💾 Graph layout captured (${count} nodes)`, 'system-msg'); } catch (e) { /* ignore */ }
        persistPositionsToWorld();
    }

    /* ── on-canvas hint (only while editing) ───────────────────────────── */

    function _updateHint() {
        let chip = document.getElementById('gbg-hint');
        if (!state.editing) { if (chip) chip.remove(); return; }
        if (!chip) {
            chip = document.createElement('div');
            chip.id = 'gbg-hint';
            chip.style.cssText = 'position:absolute;left:50%;bottom:10px;transform:translateX(-50%);z-index:6;background:rgba(13,17,23,0.92);border:1px solid var(--border,#444);border-radius:6px;padding:6px 10px;font-size:11px;color:var(--text,#eee);display:flex;gap:8px;align-items:center;';
            const container = document.getElementById('graph-container');
            if (container) container.appendChild(chip);
        }
        chip.innerHTML = `<span>${state.cropping ? '✂ drag the amber edges to crop' : '🖼 drag to move · corners resize · top dot rotates'}</span>
            <label style="display:flex;align-items:center;gap:4px;">🎚<input id="gbg-op" type="range" min="0" max="1" step="0.05" value="${state.opacity}" style="width:70px;"></label>
            <button class="btn btn-sm" id="gbg-crop">${state.cropping ? 'Done cropping' : '✂ Crop'}</button>
            <button class="btn btn-sm" id="gbg-done">✔ Done</button>`;
        chip.querySelector('#gbg-op').addEventListener('input', (e) => setOpacity(e.target.value));
        chip.querySelector('#gbg-crop').addEventListener('click', () => setCropping(!state.cropping));
        chip.querySelector('#gbg-done').addEventListener('click', () => setEditing(false));
    }

    /* ── right-click menu ──────────────────────────────────────────────── */

    function showCanvasMenu(ev) {
        const menu = document.getElementById('context-menu');
        if (!menu) return;
        const has = !!state.image;
        const item = (action, label, active, hint, color) =>
            `<div class="context-menu-item" data-gbg="${action}" style="${color ? `color:${color};` : ''}">${label}${hint ? `<span style="float:right;color:var(--text-dim);">${hint}</span>` : ''}${active ? ' <span style="color:#58a6ff;">●</span>' : ''}</div>`;
        const sep = '<div class="context-menu-separator"></div>';
        const rows = ['<div class="context-menu-header" style="padding:6px 12px;font-size:10px;color:var(--text-dim);border-bottom:1px solid var(--border-light);text-transform:uppercase;letter-spacing:0.5px;">🗺 Graph map</div>'];
        if (has) {
            rows.push(item('edit', state.editing ? '✔ Done editing' : '🖼 Edit image', state.editing));
            rows.push(item('crop', state.cropping ? '✔ Done cropping' : '✂ Crop', state.cropping));
            rows.push(item('fit', '⤢ Fit to nodes'));
            rows.push(item('opacity', '🎚 Opacity…', false, Math.round(state.opacity * 100) + '%'));
            rows.push(item('remove', '🗑 Remove image', false, '', '#f85149'));
        } else {
            rows.push(item('add', '🖼 Add background image…'));
        }
        rows.push(sep);
        rows.push(item('lock', state.locked ? '🔓 Unlock nodes' : '🔒 Lock nodes', state.locked));
        rows.push(item('save', '💾 Save layout to world'));
        menu.innerHTML = rows.join('');
        menu.style.display = 'block';
        menu.style.left = ev.clientX + 'px';
        menu.style.top = ev.clientY + 'px';
        setTimeout(() => document.addEventListener('click', () => { menu.style.display = 'none'; }, { once: true }), 0);
        menu.querySelectorAll('[data-gbg]').forEach((el) => {
            el.addEventListener('click', () => {
                menu.style.display = 'none';
                _menuAction(el.dataset.gbg);
            });
        });
    }

    function _menuAction(action) {
        switch (action) {
            case 'add': _pickFile(); break;
            case 'edit': setEditing(!state.editing); break;
            case 'crop': setCropping(!state.cropping); break;
            case 'fit': fitToNodes(); break;
            case 'opacity': {
                const current = Math.round(state.opacity * 100);
                const value = prompt('Background opacity (0-100):', String(current));
                if (value !== null) setOpacity(Number(value) / 100);
                break;
            }
            case 'remove': removeImage(); break;
            case 'lock': setLocked(!state.locked); break;
            case 'save': savePositions(); break;
            default: break;
        }
    }

    async function init() {
        _ensureLayers();
        const net = _network();
        const container = document.getElementById('graph-container');
        if (container) {
            // Keep the map glued to the graph view on every redraw (pan, zoom,
            // drag) — afterDrawing fires with the view transform already applied.
            const sync = () => _syncView();
            if (net) { try { net.on('afterDrawing', sync); } catch (e) { /* ignore */ } }
            window.addEventListener('resize', sync);
        }
        await _restore();
        _applyLockState(net);
        _render();

        // The WORLD is authoritative: whenever it is (re)fetched — including
        // after loading a different scenario — re-derive the background from it
        // instead of leaving whatever was on screen. Loading the camp after a
        // map was added elsewhere must NOT show that other world's map.
        if (typeof appEvents !== 'undefined' && appEvents && appEvents.on) {
            appEvents.on('state:updated', () => { _onWorldRefetched(); });
        }
    }

    /** Re-apply physics for the current lock state, undoing our own freeze. */
    function _applyLockState(net) {
        if (state.locked) {
            if (net) net.setOptions({ physics: { enabled: false } });
            if (typeof graphManager !== 'undefined' && graphManager) graphManager._physicsEnabled = false;
            state.physicsDisabledByLock = true;
        } else if (state.physicsDisabledByLock) {
            // WE froze physics for the previous world's lock — undo it, so a new
            // scenario doesn't inherit the old one's frozen layout.
            if (net) net.setOptions({ physics: { enabled: true } });
            if (typeof graphManager !== 'undefined' && graphManager) graphManager._physicsEnabled = true;
            state.physicsDisabledByLock = false;
        }
    }

    /** The world was refetched: restore (or clear) this world's background. */
    async function _onWorldRefetched() {
        // Never stomp an edit in progress — a debounced save is still in flight.
        if (state.editing) return;
        await _restore();
        _applyLockState(_network());
        if (Object.keys(state.positions).length) _applyPositions();
        _render();
    }

    window.GraphBackground = {
        init,
        reset,
        addFromFile,
        showCanvasMenu,
        fitToNodes,
        setEditing,
        setCropping,
        setOpacity,
        setLocked,
        savePositions,
        persistPositionsToWorld,
        removeImage,
        _state: state,
    };
})();
