/**
 * graph-export — export the graph canvas as a high-resolution PNG.
 *
 * @module graph/graph-export — rasterise the vis graph + map background to a PNG
 * @contributes GraphExport: the export dialog, offscreen re-render, and PNG download
 * @powers "📷 PNG": capture the whole graph or the current view at 1x/2x/3x, map background included
 * @relates reads graphManager.network + window.GraphBackground.getExportLayers; saves via WorldExport
 * @docs docs/virtualWorld/World Building/Graph System.md
 *
 * Why a hidden second vis.Network: vis-network derives its canvas resolution
 * from `window.devicePixelRatio` alone (`_determinePixelRatio`), so the on-screen
 * canvas cannot be captured above screen resolution by scaling. Rebuilding the
 * currently rendered nodes/edges into an N-times-larger offscreen network redraws
 * every label, node and arrow as vectors at the higher resolution. The map layers
 * are DOM elements painted beneath that canvas, so they are redrawn by hand onto
 * the same composite, using the network's own camera transform.
 */
window.GraphExport = (() => {
    'use strict';

    // Backing-store cap: a large world at 3x can otherwise exceed the ~16k canvas limit.
    const MAX_DIM = 8192;
    // The app's canvas backdrop (vis draws on a transparent canvas).
    const BG_COLOR = '#0d1117';

    let busy = false;

    function _toast(message, kind) {
        if (kind === 'error' && typeof toastError === 'function') toastError(message);
        else if (typeof toastInfo === 'function') toastInfo(message);
    }

    function _liveNetwork() {
        return (typeof graphManager !== 'undefined' && graphManager && graphManager.network) || null;
    }

    function _scenarioName() {
        const data = (typeof worldState !== 'undefined' && worldState && worldState.data) || {};
        const name = data._scenario_name
            || (document.body && document.body.dataset && document.body.dataset.scenarioName)
            || '';
        return String(name).trim();
    }

    // ── dialog ───────────────────────────────────────────────────────────────

    function openDialog() {
        const modal = document.getElementById('graph-export-modal');
        if (!modal) return;
        _setStatus('');
        modal.style.display = 'flex';
    }

    function closeDialog() {
        const modal = document.getElementById('graph-export-modal');
        if (modal) modal.style.display = 'none';
    }

    function _setStatus(text) {
        const el = document.getElementById('gexport-status');
        if (el) el.textContent = text || '';
    }

    function _selectedScope() {
        const el = document.querySelector('input[name="gexport-scope"]:checked');
        return el ? el.value : 'graph';
    }

    function _selectedScale() {
        const el = document.querySelector('input[name="gexport-scale"]:checked');
        return el ? Number(el.value) || 2 : 2;
    }

    function _submit() {
        if (busy) return;
        const scope = _selectedScope();
        const scale = _selectedScale();
        const button = document.getElementById('gexport-go');
        busy = true;
        if (button) button.disabled = true;
        _setStatus('Rendering…');
        exportPNG({ scope, scale })
            .then((result) => {
                if (result && result.ok) {
                    _setStatus('');
                    closeDialog();
                } else {
                    _setStatus((result && result.reason) || 'Export failed.');
                }
            })
            .catch((error) => {
                _setStatus('Export failed: ' + _errorText(error));
            })
            .then(() => {
                busy = false;
                if (button) button.disabled = false;
            });
    }

    function _errorText(error) {
        return error && error.message ? error.message : String(error);
    }

    // ── pure helpers (exercised by tools/unit) ───────────────────────────────

    /** Map a normalised crop window onto source pixels of an image. */
    function _cropSource(crop, imageWidth, imageHeight) {
        const c = crop || { x: 0, y: 0, w: 1, h: 1 };
        return {
            sx: c.x * imageWidth,
            sy: c.y * imageHeight,
            sw: Math.max(1, c.w * imageWidth),
            sh: Math.max(1, c.h * imageHeight),
        };
    }

    /** Uniformly shrink an export size until its backing store fits the cap. */
    function _clampExportSize(baseW, baseH, scale, maxDim, pixelRatio) {
        const pr = pixelRatio > 0 ? pixelRatio : 1;
        let width = Math.max(1, Math.round(baseW * scale));
        let height = Math.max(1, Math.round(baseH * scale));
        const maxCss = maxDim / pr;
        const factor = Math.min(1, maxCss / width, maxCss / height);
        if (factor < 1) {
            width = Math.max(1, Math.floor(width * factor));
            height = Math.max(1, Math.floor(height * factor));
        }
        return { width, height, factor, clamped: factor < 1 };
    }

    /** The camera scale that keeps a viewport's field of view when it grows. */
    function _scaledView(viewScale, baseW, exportW) {
        if (!baseW) return viewScale;
        return viewScale * (exportW / baseW);
    }

    // ── data + rendering ─────────────────────────────────────────────────────

    /** Clone the currently rendered, visible nodes/edges, frozen at their positions. */
    function _collectVisible(live) {
        const data = live.body && live.body.data;
        if (!data || !data.nodes || !data.edges) return null;
        let positions = {};
        try { positions = live.getPositions(); } catch (error) { positions = {}; }

        const visible = new Set();
        const nodes = [];
        data.nodes.get().forEach((node) => {
            if (node.hidden) return;
            visible.add(node.id);
            const clone = Object.assign({}, node);
            delete clone.hidden;
            const pos = positions[node.id];
            if (pos) { clone.x = pos.x; clone.y = pos.y; }
            clone.physics = false;
            nodes.push(clone);
        });

        const edges = [];
        data.edges.get().forEach((edge) => {
            if (edge.hidden) return;
            if (!visible.has(edge.from) || !visible.has(edge.to)) return;
            const clone = Object.assign({}, edge);
            delete clone.hidden;
            edges.push(clone);
        });

        if (!nodes.length) return null;
        return { nodes, edges };
    }

    /** Wait for vis to finish a draw, or bail after a timeout. */
    function _waitForDraw(net, timeoutMs) {
        return new Promise((resolve) => {
            let done = false;
            const finish = () => { if (done) return; done = true; resolve(); };
            try { net.once('afterDrawing', finish); } catch (error) { finish(); }
            setTimeout(finish, timeoutMs);
        });
    }

    /** Decode node thumbnail images so circularImage nodes are not drawn blank. */
    function _preloadImages(nodes) {
        const seen = new Set();
        const jobs = [];
        nodes.forEach((node) => {
            if (node.shape !== 'circularImage' || !node.image || seen.has(node.image)) return;
            seen.add(node.image);
            jobs.push(new Promise((resolve) => {
                const image = new Image();
                image.onload = () => resolve();
                image.onerror = () => resolve();
                image.src = node.image;
            }));
        });
        return Promise.all(jobs);
    }

    /** Redraw every visible map layer into the current (graph-space) transform. */
    function _drawMapLayers(ctx, layers) {
        for (const layer of layers || []) {
            const image = layer.image;
            const rect = layer.rect;
            if (!image || !rect || !image.width || !image.height) continue;
            const src = _cropSource(layer.crop, image.width, image.height);
            ctx.save();
            ctx.globalAlpha = typeof layer.opacity === 'number' ? layer.opacity : 1;
            ctx.translate(rect.x + rect.width / 2, rect.y + rect.height / 2);
            ctx.rotate(((layer.rotation || 0) * Math.PI) / 180);
            // Crop is a scaled image inside a clipped frame — same model as the DOM.
            ctx.beginPath();
            ctx.rect(-rect.width / 2, -rect.height / 2, rect.width, rect.height);
            ctx.clip();
            ctx.drawImage(image, src.sx, src.sy, src.sw, src.sh,
                -rect.width / 2, -rect.height / 2, rect.width, rect.height);
            ctx.restore();
        }
    }

    /** Flatten the map layers and the offscreen vis canvas into one image. */
    function _composite(visCanvas, layers, net) {
        const composite = document.createElement('canvas');
        composite.width = visCanvas.width;
        composite.height = visCanvas.height;
        const ctx = composite.getContext('2d');
        const pixelRatio = window.devicePixelRatio || 1;

        ctx.fillStyle = BG_COLOR;
        ctx.fillRect(0, 0, composite.width, composite.height);

        let position = { x: 0, y: 0 };
        let cameraScale = 1;
        try { position = net.getViewPosition(); cameraScale = net.getScale(); } catch (error) { /* ignore */ }

        // Rebuild the network's own transform in backing-store pixels, so the
        // maps land under the nodes exactly as they do on screen.
        ctx.save();
        ctx.translate(composite.width / 2, composite.height / 2);
        ctx.scale(cameraScale * pixelRatio, cameraScale * pixelRatio);
        ctx.translate(-position.x, -position.y);
        _drawMapLayers(ctx, layers);
        ctx.restore();

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.drawImage(visCanvas, 0, 0);
        return composite;
    }

    function _toBlob(canvas) {
        return new Promise((resolve) => {
            if (!canvas.toBlob) { resolve(null); return; }
            canvas.toBlob((blob) => resolve(blob), 'image/png');
        });
    }

    function _downloadFallback(blob, name) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    function _fileName(scope, scale) {
        const base = (_scenarioName() || 'graph')
            .replace(/[^a-z0-9_-]+/gi, '_')
            .replace(/^_+|_+$/g, '') || 'graph';
        const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        return `${base}_graph_${scope}_${scale}x_${stamp}.png`;
    }

    // ── entry point ──────────────────────────────────────────────────────────

    /**
     * Render the current graph to a PNG and save it.
     *
     * @param {Object} [opts]
     * @param {'graph'|'view'} [opts.scope] - whole graph (fit all) or current viewport
     * @param {number} [opts.scale] - resolution multiplier
     * @returns {Promise<{ok: boolean, width?: number, height?: number, reason?: string}>}
     */
    async function exportPNG({ scope = 'graph', scale = 2 } = {}) {
        const live = _liveNetwork();
        if (!live) {
            _toast('Graph is not ready to export.', 'error');
            return { ok: false, reason: 'Graph is not ready.' };
        }
        if (typeof vis === 'undefined' || !vis.Network) {
            _toast('vis-network is not loaded.', 'error');
            return { ok: false, reason: 'vis-network is not loaded.' };
        }
        const container = document.getElementById('graph-container');
        if (!container) return { ok: false, reason: 'Graph container missing.' };

        const collected = _collectVisible(live);
        if (!collected) {
            _toast('No visible nodes to export.', 'error');
            return { ok: false, reason: 'No visible nodes to export.' };
        }

        const baseW = Math.max(1, container.clientWidth);
        const baseH = Math.max(1, container.clientHeight);
        const size = _clampExportSize(baseW, baseH, scale, MAX_DIM, window.devicePixelRatio || 1);

        const host = document.createElement('div');
        host.style.cssText = `position:fixed;left:-100000px;top:0;width:${size.width}px;height:${size.height}px;overflow:hidden;`;
        document.body.appendChild(host);

        let net = null;
        try {
            const options = GraphNetwork.buildOptions();
            options.physics = { enabled: false };
            options.interaction = { hover: false, dragNodes: false, dragView: false, zoomView: false };
            options.manipulation = { enabled: false };
            options.autoResize = false;
            options.layout = { improvedLayout: false };
            options.width = `${size.width}px`;
            options.height = `${size.height}px`;

            net = new vis.Network(host, {
                nodes: new vis.DataSet(collected.nodes),
                edges: new vis.DataSet(collected.edges),
            }, options);

            await _preloadImages(collected.nodes);

            if (scope === 'view') {
                net.moveTo({
                    position: live.getViewPosition(),
                    scale: _scaledView(live.getScale(), baseW, size.width),
                    animation: false,
                });
            } else {
                // fit() clamps to maxZoomLevel (default 1); lift it so the N-times
                // larger canvas can actually resolve the graph at higher scale.
                net.fit({ animation: false, maxZoomLevel: 1e6 });
            }

            await _waitForDraw(net, 1500);
            net.redraw();
            await _waitForDraw(net, 1500);

            const visCanvas = net.canvas.frame.canvas;
            const background = window.GraphBackground;
            const layers = background && typeof background.getExportLayers === 'function'
                ? background.getExportLayers()
                : [];
            const composite = _composite(visCanvas, layers, net);

            const blob = await _toBlob(composite);
            if (!blob) {
                _toast('Could not encode the PNG.', 'error');
                return { ok: false, reason: 'PNG encoding failed.' };
            }

            const name = _fileName(scope, size.clamped ? 'max' : scale);
            if (typeof WorldExport !== 'undefined' && WorldExport.saveFileWithDialog) {
                await WorldExport.saveFileWithDialog(blob, name);
            } else {
                _downloadFallback(blob, name);
            }
            _toast(`Exported ${composite.width}×${composite.height} PNG.`);
            return { ok: true, width: composite.width, height: composite.height };
        } catch (error) {
            _toast('Export failed: ' + _errorText(error), 'error');
            return { ok: false, reason: 'Export failed: ' + _errorText(error) };
        } finally {
            try { if (net) net.destroy(); } catch (error) { /* ignore */ }
            if (host.parentNode) host.parentNode.removeChild(host);
        }
    }

    return {
        openDialog,
        closeDialog,
        exportPNG,
        _submit,
        // Pure logic exposed for tools/unit/run.cjs. Not a product API.
        _internals: { _cropSource, _clampExportSize, _scaledView },
    };
})();
