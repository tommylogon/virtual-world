"use strict";
/**
 * @module soak-api — fetch wrappers for /api/soak
 * @contributes a thin, error-normalising HTTP client for soak runs, exports, character series and telemetry
 * @powers starting/stopping runs, incremental polling, report + CSV downloads, run comparison, the space-time view
 * @relates used by soak-state.js; mirrors routes/soak.py
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(function () {
    'use strict';
    async function request(url, options) {
        const resp = await fetch(url, options);
        const ct = resp.headers.get('content-type') || '';
        let body = null;
        if (ct.includes('application/json')) {
            body = await resp.json().catch(() => null);
        }
        else {
            body = await resp.text();
        }
        if (!resp.ok) {
            const message = body && body.error ? body.error : `HTTP ${resp.status}`;
            const err = new Error(String(message));
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
    const SoakApi = {
        meta: () => request('/api/soak/meta'),
        listRuns: () => request('/api/soak/runs'),
        getRun: (id, since, eventSince) => request(`/api/soak/runs/${id}?since=${since || 0}&event_since=${eventSince || 0}`),
        startRun: (config) => request('/api/soak/runs', json(config)),
        stopRun: (id) => request(`/api/soak/runs/${id}/stop`, { method: 'POST' }),
        deleteRun: (id) => request(`/api/soak/runs/${id}`, { method: 'DELETE' }),
        report: (id, opts) => request(`/api/soak/runs/${id}/report?download=${opts && opts.download ? 1 : 0}`
            + `&samples=${opts && opts.samples ? 1 : 0}`),
        exportUrl: (id, kind) => `/api/soak/runs/${id}/export?kind=${kind}&download=1`,
        characters: (id) => request(`/api/soak/runs/${id}/characters`),
        characterSeries: (id, name) => request(`/api/soak/runs/${id}/characters/${encodeURIComponent(name)}/series`),
        samples: (id) => request(`/api/soak/runs/${id}/samples`),
        events: (id) => request(`/api/soak/runs/${id}/events`),
        // task-543/544: the run's measurement store. This is the space-time
        // view's only data source — deliberately NOT a character's lived_log,
        // which is capped at 200 entries and salience-filtered and therefore
        // cannot answer "where was everyone".
        telemetry: (id, withEvents) => request(`/api/soak/runs/${id}/telemetry?events=${withEvents ? 1 : 0}`),
        telemetryJsonlUrl: (id) => `/api/soak/runs/${id}/telemetry.jsonl`,
    };
    // SoakApi is not declared in static/js/types/globals.d.ts (shared hub, not
    // editable from a conversion lane), so it is published through a cast.
    window.SoakApi = SoakApi;
}());
