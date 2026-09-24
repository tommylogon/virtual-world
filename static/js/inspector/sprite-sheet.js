/**
 * sprite-sheet — slice an uploaded sprite sheet into one image per expression.
 *
 * @module inspector/sprite-sheet — grid/box-slice a sprite sheet into expression slots
 * @contributes SpriteSheet.computeCells/parseNames/defaultNames/clampBox (pure) + openDialog
 * @powers the "✂️ Split sheet" control in the character Expression Pack panel
 * @relates reads/writes via ApiClient.uploadNodeImage and InspectorHelpers expression slots
 * @docs docs/virtualWorld/Characters/Character Images & Expression Packs.md
 *
 * Why a client-side slice: the sheet is one image the user already has on disk;
 * cropping happens in a canvas in the browser and each tile is uploaded to its
 * own expression slot through the existing single-image endpoint. No server
 * change and no base64 in the scenario — the server still owns the files.
 *
 * Two slicing modes, because real sheets are not always an even grid:
 *   - "Even grid": rows×cols over the whole sheet (a clean 4×3 face sheet).
 *   - "Draw boxes": drag a rectangle per panel (art packs where big panels —
 *     turnarounds, magic poses — sit beside smaller ones, so no even grid fits).
 * Both feed the same crop + upload path.
 *
 * The slice geometry is split out as pure functions because the canvas half
 * cannot run in the Node unit sandbox; test_sprite_sheet.js covers the geometry
 * and naming, not the DOM.
 */
window.SpriteSheet = (() => {
    'use strict';

    // Fallback order, used only when InspectorHelpers is not loaded yet at call
    // time. InspectorHelpers.EXPRESSION_ORDER is the source of truth when present.
    const EMOTION_ORDER = ['neutral', 'happy', 'sad', 'angry', 'afraid',
        'surprised', 'disgusted', 'aroused', 'affectionate', 'ashamed',
        'envious', 'calm'];

    //: A drawn box smaller than this (in source pixels, on either axis) is
    //: treated as a stray click, not a panel.
    const MIN_BOX_PX = 8;

    /** Filename-safe key for an expression name (mirrors InspectorHelpers). */
    function slug(value) {
        return String(value || '').trim().toLowerCase()
            .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    }

    /**
     * Source rectangles for a rows×cols grid over a sheet of `width`×`height`.
     *
     * Rows/cols are fractions of the sheet, so the last row/column absorbs any
     * rounding remainder — tiles always tile the sheet exactly with no gaps or
     * overlap. `labelTrim` (0-0.9) drops that fraction off the BOTTOM of every
     * cell, which is where sprite sheets put the caption banner.
     *
     * @param {number} width - natural sheet width in px
     * @param {number} height - natural sheet height in px
     * @param {number} rows
     * @param {number} cols
     * @param {object} [opts] - { labelTrim } fraction of cell height to drop
     * @returns {Array<{row,col,x,y,w,h}>}
     */
    function computeCells(width, height, rows, cols, opts = {}) {
        const r = Math.max(1, Math.floor(rows) || 1);
        const c = Math.max(1, Math.floor(cols) || 1);
        const trim = Math.min(0.9, Math.max(0, Number(opts.labelTrim) || 0));
        const cellW = width / c;
        const cellH = height / r;
        const cells = [];
        for (let row = 0; row < r; row++) {
            for (let col = 0; col < c; col++) {
                const x = Math.round(col * cellW);
                const y = Math.round(row * cellH);
                const w = Math.round((col + 1) * cellW) - x;
                const fullH = Math.round((row + 1) * cellH) - y;
                const h = Math.max(1, Math.round(fullH * (1 - trim)));
                cells.push({ row, col, x, y, w, h });
            }
        }
        return cells;
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
    function clampBox(x0, y0, x1, y1, width, height, minSize = MIN_BOX_PX) {
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
    function parseNames(text, count) {
        const n = Math.max(0, Math.floor(count) || 0);
        const parts = String(text || '').split(/[\n,]+/).map(slug).filter(Boolean);
        const out = [];
        for (let i = 0; i < n; i++) out.push(parts[i] || '');
        return out;
    }

    /**
     * Default names for `count` cells: the canonical emotion order first, then
     * `slot13`, `slot14`, … for any overflow. The canonical order is read from
     * InspectorHelpers so the dialog and the gallery never drift apart.
     *
     * @param {number} count
     * @returns {string[]}
     */
    function defaultNames(count) {
        const n = Math.max(0, Math.floor(count) || 0);
        const base = (window.InspectorHelpers && window.InspectorHelpers.EXPRESSION_ORDER)
            ? window.InspectorHelpers.EXPRESSION_ORDER.slice()
            : EMOTION_ORDER.slice();
        const out = base.slice(0, n);
        for (let i = out.length; i < n; i++) out.push('slot' + (i + 1));
        return out;
    }

    /** Default name for the box at `index` (canonical order, then slotN). */
    function defaultNameFor(index) {
        return defaultNames(index + 1)[index];
    }

    // ── DOM / canvas half (not loaded in the Node unit sandbox) ──

    let _state = null;   // { nodeId, kind, img, mode, boxes[], draft, scale } while open

    function _loadImage(file) {
        return new Promise((resolve, reject) => {
            const url = URL.createObjectURL(file);
            const img = new Image();
            img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
            img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Could not read image')); };
            img.src = url;
        });
    }

    function _modalRoot() { return document.getElementById('sprite-sheet-modal'); }

    function closeDialog() {
        const root = _modalRoot();
        if (root) root.remove();
        _state = null;
    }

    function _mode() {
        const el = document.querySelector('input[name="ss-mode"]:checked');
        return (el && el.value) === 'boxes' ? 'boxes' : 'grid';
    }

    function _readControls() {
        const val = (id, fallback) => {
            const el = document.getElementById(id);
            const n = el ? parseInt(el.value, 10) : NaN;
            return Number.isFinite(n) ? n : fallback;
        };
        const trimEl = document.getElementById('ss-label-trim');
        const trimPct = trimEl ? parseFloat(trimEl.value) : 10;
        return {
            rows: Math.min(20, Math.max(1, val('ss-rows', 3))),
            cols: Math.min(20, Math.max(1, val('ss-cols', 4))),
            labelTrim: Math.min(0.9, Math.max(0, (Number.isFinite(trimPct) ? trimPct : 10) / 100)),
            kind: (document.querySelector('input[name="ss-kind"]:checked') || {}).value || 'profile',
        };
    }

    /** All crop targets for the current mode: [{x,y,w,h,name}]. */
    function _targets() {
        const { rows, cols, labelTrim } = _readControls();
        if (_mode() === 'boxes') {
            return _state.boxes.map(b => ({ x: b.x, y: b.y, w: b.w, h: b.h, name: b.name }))
                .filter(t => t.name);
        }
        const text = document.getElementById('ss-names').value;
        const cells = computeCells(_state.img.naturalWidth, _state.img.naturalHeight,
            rows, cols, { labelTrim });
        const names = parseNames(text, cells.length);
        return cells.map((c, i) => ({ x: c.x, y: c.y, w: c.w, h: c.h, name: names[i] }))
            .filter(t => t.name);
    }

    /** Redraw the sheet preview with the current grid / boxes. */
    function _drawOverlay() {
        if (!_state || !_state.img) return;
        const canvas = document.getElementById('ss-preview');
        if (!canvas) return;
        const img = _state.img;
        const scale = Math.min(1, 560 / img.naturalWidth);
        const dw = Math.max(1, Math.round(img.naturalWidth * scale));
        const dh = Math.max(1, Math.round(img.naturalHeight * scale));
        canvas.width = dw;
        canvas.height = dh;
        _state.scale = scale;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, dw, dh);
        ctx.drawImage(img, 0, 0, dw, dh);

        let rects = [];
        if (_mode() === 'boxes') {
            rects = _state.boxes.map(b => ({ ...b, label: b.name || '(unnamed)' }));
            if (_state.draft) {
                const d = _state.draft;
                const box = clampBox(d.x0, d.y0, d.x1, d.y1, img.naturalWidth, img.naturalHeight, 0);
                if (box) rects.push({ ...box, label: '', draft: true });
            }
        } else {
            const { rows, cols, labelTrim } = _readControls();
            const cells = computeCells(dw, dh, rows, cols, { labelTrim });
            const names = parseNames(document.getElementById('ss-names').value, cells.length);
            rects = cells.map((c, i) => ({ x: c.x, y: c.y, w: c.w, h: c.h, label: names[i] || '(skip)', cell: c }));
            if (labelTrim > 0) {
                ctx.strokeStyle = 'rgba(255, 120, 120, 0.95)';
                ctx.setLineDash([4, 3]);
                cells.forEach(cell => {
                    const cutY = cell.y + cell.h;
                    ctx.beginPath();
                    ctx.moveTo(cell.x, cutY);
                    ctx.lineTo(cell.x + cell.w, cutY);
                    ctx.stroke();
                });
                ctx.setLineDash([]);
            }
        }

        ctx.lineWidth = 2;
        ctx.font = '11px sans-serif';
        ctx.textBaseline = 'top';
        rects.forEach(r => {
            const x = r.x * (_mode() === 'boxes' ? scale : 1);
            const y = r.y * (_mode() === 'boxes' ? scale : 1);
            const w = r.w * (_mode() === 'boxes' ? scale : 1);
            const h = r.h * (_mode() === 'boxes' ? scale : 1);
            ctx.strokeStyle = r.draft ? 'rgba(255, 200, 80, 0.95)' : 'rgba(90, 200, 255, 0.95)';
            ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
            if (r.label) {
                const tw = ctx.measureText(r.label).width;
                ctx.fillStyle = 'rgba(0,0,0,0.7)';
                ctx.fillRect(x + 2, y + 2, tw + 6, 14);
                ctx.fillStyle = '#fff';
                ctx.fillText(r.label, x + 5, y + 3);
            }
        });
    }

    /** Default the name list to rows×cols canonical keys (grid mode). */
    function _resetNames() {
        const ta = document.getElementById('ss-names');
        const { rows, cols } = _readControls();
        if (ta) ta.value = defaultNames(rows * cols).join(', ');
        _drawOverlay();
    }

    function _renderBoxList() {
        const list = document.getElementById('ss-box-list');
        if (!list) return;
        if (!_state.boxes.length) {
            list.innerHTML = '<div style="font-size:11px;color:var(--text-muted);">No boxes yet — drag on the image to box each panel.</div>';
            return;
        }
        list.innerHTML = _state.boxes.map((b, i) => `
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
                <span style="font-size:10px;color:var(--text-muted);width:34px;">#${i + 1}</span>
                <input type="text" class="ss-box-name" data-i="${i}" value="${_escAttr(b.name)}" style="flex:1;font-size:11px;">
                <span style="font-size:10px;color:var(--text-muted);">${b.w}×${b.h}</span>
                <button class="btn btn-sm btn-danger" data-remove="${i}" title="Remove box">🗑</button>
            </div>`).join('');
        list.querySelectorAll('.ss-box-name').forEach(el => {
            el.addEventListener('input', () => {
                const i = parseInt(el.dataset.i, 10);
                if (_state.boxes[i]) _state.boxes[i].name = slug(el.value);
                _drawOverlay();
            });
        });
        list.querySelectorAll('[data-remove]').forEach(el => {
            el.addEventListener('click', () => {
                _state.boxes.splice(parseInt(el.dataset.remove, 10), 1);
                _renderBoxList();
                _drawOverlay();
            });
        });
    }

    function _escAttr(v) {
        return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
            .replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function _setStatus(text, isError) {
        const el = document.getElementById('ss-status');
        if (el) {
            el.textContent = text || '';
            el.style.color = isError ? 'var(--red, #e06c75)' : 'var(--text-muted)';
        }
    }

    function _syncModeUi() {
        const boxes = _mode() === 'boxes';
        const grid = document.getElementById('ss-grid-controls');
        const namesWrap = document.getElementById('ss-names-wrap');
        const boxWrap = document.getElementById('ss-box-wrap');
        const hint = document.getElementById('ss-mode-hint');
        if (grid) grid.style.display = boxes ? 'none' : 'flex';
        if (namesWrap) namesWrap.style.display = boxes ? 'none' : 'block';
        if (boxWrap) boxWrap.style.display = boxes ? 'block' : 'none';
        if (hint) {
            hint.textContent = boxes
                ? 'Drag a rectangle over each panel. Names default to the canonical order; edit any box.'
                : 'Even rows×cols over the whole sheet. The red dashed line is where the caption banner is trimmed.';
        }
        _renderBoxList();
        _drawOverlay();
    }

    /** Attach the drag-to-box handlers (only meaningful in boxes mode). */
    function _wireCanvasDrag() {
        const canvas = document.getElementById('ss-preview');
        if (!canvas) return;
        const toNatural = (ev) => {
            const rect = canvas.getBoundingClientRect();
            const sx = canvas.width / rect.width;
            const sy = canvas.height / rect.height;
            const scale = _state.scale || 1;
            return {
                x: (ev.clientX - rect.left) * sx / scale,
                y: (ev.clientY - rect.top) * sy / scale,
            };
        };
        canvas.addEventListener('mousedown', (ev) => {
            if (_mode() !== 'boxes' || !_state.img) return;
            ev.preventDefault();
            const p = toNatural(ev);
            _state.draft = { x0: p.x, y0: p.y, x1: p.x, y1: p.y };
            _drawOverlay();
        });
        canvas.addEventListener('mousemove', (ev) => {
            if (!_state.draft) return;
            const p = toNatural(ev);
            _state.draft.x1 = p.x;
            _state.draft.y1 = p.y;
            _drawOverlay();
        });
        const finish = () => {
            if (!_state.draft) return;
            const d = _state.draft;
            _state.draft = null;
            const box = clampBox(d.x0, d.y0, d.x1, d.y1, _state.img.naturalWidth, _state.img.naturalHeight);
            if (box) {
                box.name = defaultNameFor(_state.boxes.length);
                _state.boxes.push(box);
                _renderBoxList();
            }
            _drawOverlay();
        };
        canvas.addEventListener('mouseup', finish);
        canvas.addEventListener('mouseleave', finish);
    }

    function openDialog(nodeId, kind) {
        if (_modalRoot()) closeDialog();

        const startKind = kind === 'full' ? 'full' : 'profile';
        const root = document.createElement('div');
        root.id = 'sprite-sheet-modal';
        root.className = 'modal';
        root.innerHTML = `
            <div class="modal-content" style="width:680px;">
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
                            <label style="font-size:11px;"><input type="radio" name="ss-mode" value="grid" checked> Even grid</label>
                            <label style="font-size:11px;margin-left:6px;"><input type="radio" name="ss-mode" value="boxes"> Draw boxes</label>
                        </label>
                        <label style="font-size:11px;">Slot<br>
                            <span>
                                <label style="font-size:11px;"><input type="radio" name="ss-kind" value="profile" ${startKind === 'profile' ? 'checked' : ''}> Profile</label>
                                <label style="font-size:11px;margin-left:6px;"><input type="radio" name="ss-kind" value="full" ${startKind === 'full' ? 'checked' : ''}> Full body</label>
                            </span>
                        </label>
                    </div>
                    <div id="ss-grid-controls" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-bottom:8px;">
                        <label style="font-size:11px;">Columns<br><input type="number" id="ss-cols" value="4" min="1" max="20" style="width:60px;"></label>
                        <label style="font-size:11px;">Rows<br><input type="number" id="ss-rows" value="3" min="1" max="20" style="width:60px;"></label>
                        <label style="font-size:11px;">Trim label %<br><input type="number" id="ss-label-trim" value="10" min="0" max="90" step="1" style="width:70px;"></label>
                        <button class="btn btn-sm" id="ss-reset-names" type="button">Reset names</button>
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
                    <div style="margin-top:6px;text-align:center;">
                        <canvas id="ss-preview" style="max-width:100%;border:1px solid var(--border);border-radius:6px;cursor:crosshair;"></canvas>
                    </div>
                    <div id="ss-status" style="font-size:11px;min-height:16px;margin-top:8px;color:var(--text-muted);"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="ss-cancel" type="button">Cancel</button>
                    <button class="btn btn-green" id="ss-run" type="button" disabled>✂️ Slice &amp; upload</button>
                </div>
            </div>`;
        document.body.appendChild(root);

        _state = { nodeId, kind: startKind, img: null, file: null, boxes: [], draft: null, scale: 1 };

        document.getElementById('ss-close').onclick = closeDialog;
        document.getElementById('ss-cancel').onclick = closeDialog;
        root.addEventListener('click', (e) => { if (e.target === root) closeDialog(); });

        const fileEl = document.getElementById('ss-file');
        fileEl.addEventListener('change', async () => {
            const file = fileEl.files && fileEl.files[0];
            if (!file) return;
            try {
                _state.img = await _loadImage(file);
                _state.file = file;
                document.getElementById('ss-run').disabled = false;
                _setStatus(`Loaded ${_state.img.naturalWidth}×${_state.img.naturalHeight}.`);
                _resetNames();
            } catch (err) {
                _setStatus(err.message || 'Could not read image.', true);
            }
        });

        ['ss-cols', 'ss-rows'].forEach(id => {
            document.getElementById(id).addEventListener('change', _resetNames);
        });
        ['ss-label-trim', 'ss-names'].forEach(id => {
            document.getElementById(id).addEventListener('input', _drawOverlay);
        });
        document.querySelectorAll('input[name="ss-kind"]').forEach(el => {
            el.addEventListener('change', () => { _state.kind = _readControls().kind; });
        });
        document.querySelectorAll('input[name="ss-mode"]').forEach(el => {
            el.addEventListener('change', _syncModeUi);
        });
        document.getElementById('ss-reset-names').onclick = _resetNames;
        document.getElementById('ss-clear-boxes').onclick = () => {
            _state.boxes = [];
            _renderBoxList();
            _drawOverlay();
        };
        document.getElementById('ss-run').onclick = _runUpload;
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
        const ctx = canvas.getContext('2d');
        const runBtn = document.getElementById('ss-run');
        runBtn.disabled = true;
        const failures = [];
        let mergedExpressions = null;
        let neutralUrl = null;
        for (let i = 0; i < targets.length; i++) {
            const t = targets[i];
            _setStatus(`Uploading ${i + 1}/${targets.length} — ${t.name}…`);
            try {
                canvas.width = t.w;
                canvas.height = t.h;
                ctx.clearRect(0, 0, t.w, t.h);
                ctx.drawImage(_state.img, t.x, t.y, t.w, t.h, 0, 0, t.w, t.h);
                const blob = await new Promise(res => canvas.toBlob(res, 'image/png'));
                if (!blob) throw new Error('canvas produced no image');
                const file = new File([blob], t.name + '.png', { type: 'image/png' });
                const res = await api.uploadNodeImage(_state.nodeId, file, kind, t.name);
                if (res && res.error) throw new Error(res.error);
                if (res && res.expressions) mergedExpressions = res.expressions;
                if (t.name === 'neutral' && res && res.image) neutralUrl = res.image;
            } catch (err) {
                failures.push(`${t.name}: ${err.message || err}`);
            }
        }

        const nodeId = _state.nodeId;
        // Merge the batch result into the gallery cache so the thumbnails update
        // without waiting for a full inspector re-render (the server returns the
        // whole `expressions` map on each upload).
        const H = window.InspectorHelpers;
        if (H && mergedExpressions) {
            const cache = H._exprCache[nodeId] || (H._exprCache[nodeId] = {});
            cache.expressions = mergedExpressions;
            if (neutralUrl) {
                if (kind === 'profile') cache.profile_image = neutralUrl;
                else cache.image = neutralUrl;
            }
        }
        if (failures.length) {
            _setStatus(`Uploaded ${targets.length - failures.length}/${targets.length}. Failed → ${failures.join('; ')}`, true);
            runBtn.disabled = false;
        } else {
            _setStatus(`Done — uploaded ${targets.length} tile(s).`);
        }
        if (window.events) events.log(`Sprite sheet: uploaded ${targets.length - failures.length}/${targets.length} expression tile(s).`, failures.length ? 'error-msg' : 'system-msg');
        // Refresh the gallery once, not per tile.
        if (H) H._refreshExpressionGrid(nodeId, kind);
        if (window.graphManager) { graphManager._lastSig = ''; }
        if (window.worldState) worldState.fetch();
        if (window.graphManager) graphManager.loadGraphData();
        if (!failures.length) closeDialog();
    }

    return { computeCells, clampBox, parseNames, defaultNames, defaultNameFor, slug,
             openDialog, closeDialog, EMOTION_ORDER };
})();
