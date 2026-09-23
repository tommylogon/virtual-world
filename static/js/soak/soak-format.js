/**
 * @module soak-format — pure formatting/color helpers for the Soak Lab UI
 * @contributes number/duration/time formatting, vital color mapping, HTML escaping, config<->query-string codecs
 * @powers live stat readouts, chart axes, run list rows, CLI command + share links
 * @relates used by soak-ui.js, soak-charts.js, soak-state.js, soak-presets.js
 * @docs none
 */
(function () {
    'use strict';

    const VITAL_COLORS = {
        HP: '#f85149',
        Energy: '#e3b341',
        Hunger: '#f0883e',
        Thirst: '#58a6ff',
        Temperature: '#ff7b72',
        Social: '#bc8cff',
        Hygiene: '#3fb950',
        Sanity: '#f778ba',
        Entertainment: '#79c0ff',
        Bladder: '#d29922',
        Arousal: '#ff6ac1',
        Stimulation: '#ff9ecd',
        Pleasure: '#c297ff',
    };
    const PALETTE = ['#58a6ff', '#3fb950', '#e3b341', '#f85149', '#bc8cff',
        '#f778ba', '#79c0ff', '#f0883e', '#56d4dd', '#d29922'];

    function vitalColor(name, index) {
        if (VITAL_COLORS[name]) return VITAL_COLORS[name];
        return PALETTE[(index || 0) % PALETTE.length];
    }

    function fmtInt(v) {
        if (v === null || v === undefined || Number.isNaN(v)) return '—';
        return Math.round(v).toLocaleString('en-US');
    }

    function fmtNum(v, digits) {
        if (v === null || v === undefined || Number.isNaN(v)) return '—';
        const d = digits === undefined ? 1 : digits;
        const n = Number(v);
        if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
        if (Math.abs(n) >= 1e4) return (n / 1e3).toFixed(1) + 'k';
        return n.toLocaleString('en-US', { maximumFractionDigits: d });
    }

    function fmtSigned(v, digits) {
        if (v === null || v === undefined || Number.isNaN(v)) return '—';
        const n = Number(v);
        return (n > 0 ? '+' : '') + n.toFixed(digits === undefined ? 1 : digits);
    }

    function fmtDuration(seconds) {
        if (seconds === null || seconds === undefined || !isFinite(seconds)) return '—';
        let s = Math.max(0, Math.round(seconds));
        const h = Math.floor(s / 3600); s %= 3600;
        const m = Math.floor(s / 60); const sec = s % 60;
        if (h) return h + 'h' + String(m).padStart(2, '0') + 'm';
        if (m) return m + 'm' + String(sec).padStart(2, '0') + 's';
        return sec + 's';
    }

    function fmtClock(ts) {
        if (!ts) return '—';
        const d = new Date(ts * 1000);
        return d.toLocaleTimeString('en-US', { hour12: false });
    }

    function fmtBytes(n) {
        if (!n) return '0 B';
        if (n < 1024) return n + ' B';
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
        return (n / 1024 / 1024).toFixed(1) + ' MB';
    }

    function pct(frac, digits) {
        if (frac === null || frac === undefined || !isFinite(frac)) return '—';
        return (frac * 100).toFixed(digits === undefined ? 1 : digits) + '%';
    }

    function esc(s) {
        return String(s === null || s === undefined ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function titleCase(s) {
        return String(s || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    }

    /** Serialize the subset of a config worth sharing/reloading. */
    function configToQuery(config) {
        const out = {};
        const keys = ['scenario', 'ticks', 'minutes_per_tick', 'engine_decay', 'background_all',
            'mature', 'neutral_environment', 'debug_hp', 'seed', 'sample_every', 'label',
            'decay_overrides', 'starting_vitals', 'traits'];
        keys.forEach((k) => {
            const v = config ? config[k] : undefined;
            if (v === undefined || v === null || v === '' || v === false) return;
            if (typeof v === 'object') {
                const parts = Object.keys(v).map((kk) => kk + '=' + v[kk]);
                if (parts.length) out[k] = parts.join(',');
            } else {
                out[k] = v;
            }
        });
        if (Array.isArray(config && config.track_vitals) && config.track_vitals.length) {
            out.track_vitals = config.track_vitals.join(',');
        }
        return new URLSearchParams(out).toString();
    }

    function queryToConfig(search) {
        const params = new URLSearchParams(search || '');
        if (![...params.keys()].length) return null;
        const cfg = {};
        params.forEach((value, key) => {
            if (key === 'ticks' || key === 'seed' || key === 'sample_every') {
                cfg[key] = Number(value);
            } else if (key === 'minutes_per_tick') {
                cfg[key] = value === '' ? null : Number(value);
            } else if (key === 'engine_decay' || key === 'background_all' || key === 'mature'
                || key === 'neutral_environment' || key === 'debug_hp') {
                cfg[key] = value !== 'false' && value !== '0';
            } else if (key === 'track_vitals') {
                cfg[key] = value.split(',').filter(Boolean);
            } else if (key === 'decay_overrides' || key === 'starting_vitals' || key === 'traits') {
                cfg[key] = value;
            } else {
                cfg[key] = value;
            }
        });
        return cfg;
    }

    window.SoakFormat = {
        VITAL_COLORS, PALETTE,
        vitalColor, fmtInt, fmtNum, fmtSigned, fmtDuration, fmtClock, fmtBytes,
        pct, esc, titleCase, configToQuery, queryToConfig,
    };
})();
