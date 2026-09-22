/**
 * @module soak-api — fetch wrappers for /api/soak
 * @contributes a thin, error-normalising HTTP client for soak runs, exports and character series
 * @powers starting/stopping runs, incremental polling, report + CSV downloads, run comparison
 * @relates used by soak-state.js; mirrors routes/soak.py
 * @docs none
 */
(function () {
    'use strict';

    async function request(url, options) {
        const resp = await fetch(url, options);
        const ct = resp.headers.get('content-type') || '';
        let body = null;
        if (ct.includes('application/json')) {
            body = await resp.json().catch(() => null);
        } else {
            body = await resp.text();
        }
        if (!resp.ok) {
            const message = body && body.error ? body.error : `HTTP ${resp.status}`;
            const err = new Error(message);
            err.status = resp.status;
            throw err;
        }
        return body;
    }

    function json(body) {
        return {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        };
    }

    window.SoakApi = {
        meta: () => request('/api/soak/meta'),
        listRuns: () => request('/api/soak/runs'),
        getRun: (id, since, eventSince) => request(
            `/api/soak/runs/${id}?since=${since || 0}&event_since=${eventSince || 0}`),
        startRun: (config) => request('/api/soak/runs', json(config)),
        stopRun: (id) => request(`/api/soak/runs/${id}/stop`, { method: 'POST' }),
        deleteRun: (id) => request(`/api/soak/runs/${id}`, { method: 'DELETE' }),
        report: (id, opts) => request(
            `/api/soak/runs/${id}/report?download=${opts && opts.download ? 1 : 0}`
            + `&samples=${opts && opts.samples ? 1 : 0}`),
        exportUrl: (id, kind) => `/api/soak/runs/${id}/export?kind=${kind}&download=1`,
        characters: (id) => request(`/api/soak/runs/${id}/characters`),
        characterSeries: (id, name) => request(
            `/api/soak/runs/${id}/characters/${encodeURIComponent(name)}/series`),
        samples: (id) => request(`/api/soak/runs/${id}/samples`),
        events: (id) => request(`/api/soak/runs/${id}/events`),
    };
})();
