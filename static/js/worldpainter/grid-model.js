/**
 * grid-model.js — pure helpers for the WorldPainter editor.
 *
 * No DOM and no network: the editor (`static/js/worldpainter/editor.js`) keeps
 * its rendering dumb by deriving cell rows, colours, and feature placement from
 * these functions, which are covered by `tools/unit/test_worldpainter.js`.
 *
 * Mirrors the server contract in `engine/world_grid.py` (task-495): a scope owns
 * a bounded grid, paint lives on layers `biome`/`road`/`elevation`, and features
 * are child scopes placed at a cell.
 *
 * @module grid-model — WorldPainter grid view-model and cell maths
 * @contributes cell keys, drill-down mode suggestion, render rows, layer colours
 * @powers WorldPainter editor grid rendering and placement (task-495)
 * @relates static/js/worldpainter/editor.js; engine/world_grid.py; routes/world_grid_ops.py
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
(function () {
    'use strict';

    const MODES = ['world', 'town', 'interior'];
    const PAINT_LAYERS = ['biome', 'road', 'elevation'];

    // Keys are the real ids in `data/worldpainter/biomes.json` / `features`, so a
    // painted cell reads at a glance; anything else gets a deterministic hash
    // colour, so an unknown value is still stable (never blank).
    const BIOME_COLORS = {
        sparse_forest: '#6f9b52', dense_forest: '#2f6b34', pine_forest: '#2b5a4b',
        farmland: '#b6a24f', hills: '#8a7d52', mountains: '#6d6a63', cliff: '#7d746a',
        chasm: '#3a3a42', ravine: '#4a4640', beach: '#cbb78a', spring: '#4f9bb0',
        stream: '#3f88a0', river: '#2f6f96', lake: '#245a7a', deep_water: '#1b3a5b',
        ocean: '#1b3a5b',
    };
    const ROAD_COLORS = {
        road: '#8a7d5f', bridge: '#7a5a3a', ford: '#5f7f96', gate: '#6f7276',
        tunnel: '#3a3a42', town: '#a8763f', village: '#a8763f', ruin: '#6b6157',
        building: '#8a6b5a',
    };

    function cellKey(x, y) {
        return `${Math.trunc(x)},${Math.trunc(y)}`;
    }

    function parseCellKey(key) {
        const parts = String(key == null ? '' : key).split(',');
        if (parts.length !== 2) return null;
        const x = Number(parts[0]);
        const y = Number(parts[1]);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
        return { x, y };
    }

    function cellId(scopeId, x, y) {
        return `${scopeId}:${Math.trunc(x)},${Math.trunc(y)}`;
    }

    /** The mode a child scope should open in, given its parent's mode. */
    function nextMode(mode) {
        const i = MODES.indexOf(mode);
        if (i < 0) return MODES[0];
        return MODES[Math.min(i + 1, MODES.length - 1)];
    }

    function _hash(text) {
        let h = 0;
        const s = String(text == null ? '' : text);
        for (let i = 0; i < s.length; i += 1) {
            h = (h * 31 + s.charCodeAt(i)) | 0;
        }
        return Math.abs(h);
    }

    function layerColor(layer, value) {
        if (value == null || value === '') return null;
        const key = String(value).toLowerCase();
        if (layer === 'biome') return BIOME_COLORS[key] || `hsl(${_hash(key) % 360},45%,45%)`;
        if (layer === 'road') return ROAD_COLORS[key] || `hsl(${_hash(key) % 360},18%,55%)`;
        if (layer === 'elevation') {
            const n = Number(value);
            if (!Number.isFinite(n)) return '#666';
            const t = Math.max(0, Math.min(1, n));
            return `hsl(210,${20 + t * 45}%,${78 - t * 55}%)`;
        }
        return `hsl(${_hash(key) % 360},40%,50%)`;
    }

    /**
     * Bresenham line of cells from *a* to *b*, inclusive. The route tool uses
     * this so a two-click route paints the exact cells a straight trail covers
     * (a hand-rolled line rasteriser is standard, not a wheel worth a library).
     */
    function lineCells(a, b) {
        let x0 = Math.trunc(a.x);
        let y0 = Math.trunc(a.y);
        const x1 = Math.trunc(b.x);
        const y1 = Math.trunc(b.y);
        const cells = [];
        const dx = Math.abs(x1 - x0);
        const dy = Math.abs(y1 - y0);
        const sx = x0 < x1 ? 1 : -1;
        const sy = y0 < y1 ? 1 : -1;
        let err = dx - dy;
        for (;;) {
            cells.push({ x: x0, y: y0 });
            if (x0 === x1 && y0 === y1) break;
            const e2 = 2 * err;
            if (e2 > -dy) { err -= dy; x0 += sx; }
            if (e2 < dx) { err += dx; y0 += sy; }
        }
        return cells;
    }

    /** Chain waypoint segments into one de-duplicated cell path. */
    function routeCells(points) {
        const pts = points || [];
        const out = [];
        const seen = {};
        if (pts.length === 1) return [{ x: Math.trunc(pts[0].x), y: Math.trunc(pts[0].y) }];
        for (let i = 0; i + 1 < pts.length; i += 1) {
            lineCells(pts[i], pts[i + 1]).forEach((c) => {
                const k = cellKey(c.x, c.y);
                if (!seen[k]) { seen[k] = true; out.push(c); }
            });
        }
        return out;
    }

    /**
     * Turn a cell count into the game-time figures the world is authored in:
     * 1 cell = 1 turn = 1 minute, 60 turns/hour (240 cells => "4 h 00 m").
     */
    function routeStats(cellCount, minutesPerCell) {
        const per = minutesPerCell == null ? 1 : minutesPerCell;
        const turns = Math.round((Number(cellCount) || 0) * per);
        const hours = Math.floor(turns / 60);
        const mins = turns % 60;
        const label = turns >= 60
            ? `${cellCount} cells · ${turns} turns · ${hours} h ${String(mins).padStart(2, '0')} m`
            : `${cellCount} cells · ${turns} turns`;
        return { cells: cellCount, turns, minutes: turns, hours: hours + mins / 60, label };
    }

    function cellValue(payload, layer, x, y) {
        const layers = (payload && payload.layers) || {};
        return (layers[layer] || {})[cellKey(x, y)];
    }

    function featureAt(payload, x, y) {
        const feature = (payload && payload.feature) || {};
        return feature[cellKey(x, y)] || null;
    }

    function placementFor(payload, childId) {
        const list = (payload && payload.placements) || [];
        return list.find((p) => p.id === childId) || null;
    }

    /**
     * Full render model: rows of cells (y-major) carrying paint + feature, so the
     * editor only maps colours to styles. Off-grid when the scope has no grid.
     */
    function buildRows(payload) {
        const grid = (payload && payload.grid) || null;
        if (!grid || !grid.w || !grid.h) return [];
        const rows = [];
        for (let y = 0; y < grid.h; y += 1) {
            const row = [];
            for (let x = 0; x < grid.w; x += 1) {
                const cell = { x, y, key: cellKey(x, y), feature: featureAt(payload, x, y) };
                PAINT_LAYERS.forEach((layer) => {
                    const value = cellValue(payload, layer, x, y);
                    if (value != null && value !== '') {
                        cell[layer] = value;
                        cell.color = cell.color || layerColor(layer, value);
                    }
                });
                row.push(cell);
            }
            rows.push(row);
        }
        return rows;
    }

    /** Feature placements as a Map-like lookup for selection/badges. */
    function featureMap(payload) {
        const out = {};
        ((payload && payload.placements) || []).forEach((p) => {
            out[cellKey(p.x, p.y)] = p;
        });
        return out;
    }

    /**
     * Pure mirror of `engine/world_grid.ensure_grid` pruning, used by the editor's
     * resize dialog to warn how much paint/placement a shrink would drop.
     */
    function pruneGrid(payload, w, h) {
        const inBounds = (x, y) => x >= 0 && y >= 0 && x < w && y < h;
        const layers = {};
        Object.keys((payload && payload.layers) || {}).forEach((layer) => {
            const kept = {};
            Object.keys(payload.layers[layer]).forEach((key) => {
                const pos = parseCellKey(key);
                if (pos && inBounds(pos.x, pos.y)) kept[key] = payload.layers[layer][key];
            });
            if (Object.keys(kept).length) layers[layer] = kept;
        });
        const placements = ((payload && payload.placements) || [])
            .filter((p) => inBounds(p.x, p.y));
        return {
            paintKept: Object.keys(layers).reduce((n, l) => n + Object.keys(layers[l]).length, 0),
            placementsKept: placements.length,
        };
    }

    /**
     * How many areas + ways a painted grid would compile to, so the author sees
     * the node cost *before* minting it (a 5,000-cell paint is 5,000 areas plus
     * their passages, which is what makes the graph view choke).
     *
     * Mirrors `engine/world_compile.compile_grid`: biome cells become areas;
     * without merge it is one area per cell and a way per adjacent pair, with
     * merge it is one area per same-biome flood-fill region.
     */
    function estimateCompile(payload, regionMerge) {
        const biome = (payload && payload.layers && payload.layers.biome) || {};
        const cells = Object.keys(biome);
        if (!cells.length) return { areas: 0, ways: 0, total: 0 };
        const present = {};
        cells.forEach((k) => { present[k] = true; });
        const down = (k) => {
            const p = parseCellKey(k);
            return p ? cellKey(p.x, p.y + 1) : null;
        };
        const right = (k) => {
            const p = parseCellKey(k);
            return p ? cellKey(p.x + 1, p.y) : null;
        };

        if (!regionMerge) {
            let ways = 0;
            cells.forEach((k) => {
                if (present[down(k)]) ways += 1;
                if (present[right(k)]) ways += 1;
            });
            return { areas: cells.length, ways, total: cells.length + ways };
        }

        // Flood-fill same-biome cells into regions (4-neighbour), then count one
        // way per adjacent region pair.
        const regionOf = {};
        let rid = 0;
        cells.forEach((start) => {
            if (regionOf[start] != null) return;
            const biomeId = biome[start];
            const stack = [start];
            regionOf[start] = rid;
            while (stack.length) {
                const k = stack.pop();
                const pos = parseCellKey(k);
                [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([dx, dy]) => {
                    const nk = cellKey(pos.x + dx, pos.y + dy);
                    if (present[nk] && regionOf[nk] == null && biome[nk] === biomeId) {
                        regionOf[nk] = rid;
                        stack.push(nk);
                    }
                });
            }
            rid += 1;
        });
        const pairs = {};
        cells.forEach((k) => {
            [down(k), right(k)].forEach((nk) => {
                if (!present[nk] || regionOf[nk] === regionOf[k]) return;
                const a = regionOf[k];
                const b = regionOf[nk];
                pairs[`${Math.min(a, b)},${Math.max(a, b)}`] = true;
            });
        });
        const ways = Object.keys(pairs).length;
        return { areas: rid, ways, total: rid + ways };
    }

    function childrenAvailable(payload) {
        return ((payload && payload.children) || []).filter((c) => !c.placed);
    }

    const gridModel = {
        MODES, PAINT_LAYERS, BIOME_COLORS, ROAD_COLORS,
        cellKey, parseCellKey, cellId, nextMode, layerColor,
        lineCells, routeCells, routeStats, estimateCompile,
        cellValue, featureAt, placementFor, buildRows, featureMap,
        pruneGrid, childrenAvailable,
    };
    // main.js (loaded last) does `window.VW = {}` and re-registers singletons, so
    // the bare global is what survives; VW.gridModel is (re)attached there too.
    window.gridModel = gridModel;
    window.VW = window.VW || {};
    window.VW.gridModel = gridModel;
})();
