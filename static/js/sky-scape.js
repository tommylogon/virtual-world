"use strict";
/**
 * sky-scape.js — Engine-driven Sky Clock (task-228/229/234 UI, roadmap 3.3).
 *
 * Renders the sky state the ENGINE computes (game_time, game_day, moon_phase,
 * forecast + override) in two places:
 *   - the compact top-bar widget (replaces the bare `#ui-time` clock): a single
 *     live line — time · date · moon · weather
 *   - the **World Sky panel** (modal): the animated sky STAGE from
 *     docs/design/sky-clock-mockup-v2-real-moon.html, ported to be driven by
 *     live state instead of demo chips. Controls (time skips, moon/weather
 *     displays) read the engine; authoring happens through the forecast APIs.
 *
 * Pure presentation — no state of its own; every render takes `state` from
 * `/api/state` (worldState.data) and refreshes on state:updated.
 *
 * @module sky-scape — the engine-driven Sky Clock UI
 * @contributes SkyScape: top-bar time/date/moon/weather line + the World Sky modal stage
 * @powers Time & weather — seeing the sky state the engine computes (task-228/229/234)
 * @relates pure presentation over /api/state; refreshes on state:updated
 * @docs docs/design/sky-widget-reconciled.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// The local binding is `_SkyScape` because `SkyScape` is already a declared
// ambient global in types/globals.d.ts; a top-level `const SkyScape` would be a
// duplicate declaration.
const _SkyScape = (() => {
    'use strict';
    // ── Weather chips (from Time & Weather.md + forecast states) ──
    const WEATHER_CHIP = {
        'clear': '☀️', 'cloudy': '☁️', 'rainy': '🌧️', 'stormy': '⛈️',
        'foggy': '🌫️', 'windy': '💨', 'snowy': '🌨️', 'rain': '🌧️',
        'storm': '⛈️', 'snow': '🌨️',
    };
    // The map above is the **fallback** now (task-772): the weather vocabulary
    // is library data (`data/library/weather`), so the live icons are fetched
    // from `/api/vocabulary/weather` and override it. The built-in map still
    // covers the first frame before the fetch resolves and the non-canonical
    // spellings ("rain", "storm") an authored forecast may carry.
    const _WEATHER_ICONS = {};
    // The canonical registry ids, in registry order — kept separate from
    // `_WEATHER_ICONS`, which also holds alias spellings for chip lookup and
    // must not be offered as selectable weather in a dropdown.
    const _WEATHER_IDS = [];
    // spelling -> canonical id, from the engine (task-772). Resolves an authored
    // spelling ("overcast") to the id the sky stage's weather map keys on, so the
    // top bar and the stage cannot disagree about the same moment's weather.
    const _WEATHER_ALIASES = {};
    let _vocabLoaded = false;
    let _repaint = null;
    /** Icon for a weather value: registry first, built-in map, else the fallback. */
    function _weatherChip(w, fallback = '☀️') {
        return _WEATHER_ICONS[w] || WEATHER_CHIP[w] || fallback;
    }
    /** Fetch the weather-type icons from the library registry once (task-772). */
    function _loadWeatherVocabulary() {
        if (_vocabLoaded)
            return;
        _vocabLoaded = true;
        fetch('/api/vocabulary/weather', { cache: 'no-store' })
            .then((r) => (r.ok ? r.json() : null))
            .then((d) => {
            const entries = (d && d.entries) || [];
            _WEATHER_IDS.length = 0;
            for (const e of entries) {
                const icon = e && e.record && e.record.icon;
                if (e && e.id && icon)
                    _WEATHER_ICONS[e.id] = icon;
                if (e && e.id && !_WEATHER_IDS.includes(e.id))
                    _WEATHER_IDS.push(e.id);
            }
            // Resolve authored spellings ("overcast") to their canonical
            // id's icon; the alias table comes from the engine, not a copy.
            const aliases = (d && d.aliases) || {};
            for (const [spelling, cid] of Object.entries(aliases)) {
                _WEATHER_ALIASES[spelling] = cid;
                if (_WEATHER_ICONS[cid])
                    _WEATHER_ICONS[spelling] = _WEATHER_ICONS[cid];
            }
            if (_repaint)
                _repaint();
        })
            .catch(() => { });
    }
    const MOON_CHIP = {
        'new_moon': '🌑', 'crescent': '🌒', 'quarter': '🌓', 'gibbous': '🌔',
        'full_moon': '🌕', 'waning': '🌖', 'blood_moon': '🔴',
    };
    // The month→season table is **not here** (task-554). It was duplicated in
    // this file — once as SEASON_BY_MONTH and once inline in the iframe
    // postMessage — while the engine read a season nowhere, so "winter" only ever
    // meant a sky tint. The engine resolves the season from the clock and ships it
    // in world_state; these two functions are the one place it is read.
    let _modalEl = null;
    let _timer = null;
    // ── state helpers ──────────────────────────────────────────────────
    function _monthName(m) {
        return ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m % 13] || '';
    }
    /** Days in a game month, from the scenario's calendar (default 30). */
    function _daysPerMonth(state) {
        const cfg = state && state.calendar_config;
        const n = cfg && Number(cfg.days_per_month);
        return Number.isFinite(n) && n > 0 ? Math.floor(n) : 30;
    }
    /** Day-of-month (1-based). ``game_day`` is the absolute day, so the raw
     *  counter must be reduced mod the month length to read as a date. */
    function _dayOfMonth(state) {
        const dpm = _daysPerMonth(state);
        return ((Math.max(1, Number(state?.game_day) || 1) - 1) % dpm) + 1;
    }
    /**
     * The season the engine says it is, with the old month table as a fallback
     * only for the frames before the first state arrives. That fallback is
     * deliberately the *old* table and nothing more: a second real table is what
     * this change removed.
     */
    function _season(state) {
        const fromEngine = state?.season;
        if (typeof fromEngine === 'string' && fromEngine)
            return fromEngine;
        const m = Math.max(1, Math.min(12, (state?.game_month || 1)));
        return ['winter', 'winter', 'spring', 'spring', 'spring',
            'summer', 'summer', 'summer', 'autumn', 'autumn', 'autumn',
            'winter'][m - 1] || 'summer';
    }
    /** Effective weather: override wins, else the forecast entry at "now". */
    function effectiveWeather(state) {
        const ov = state?.forecast_override;
        if (ov && ov.weather)
            return ov.weather;
        const sched = state?.forecast_schedule;
        if (sched && Array.isArray(sched.entries) && sched.entries.length) {
            const period = GRANULARITY_MINUTES[sched.granularity || ''] || 1440;
            const day = (state?.game_day || 1) - 1;
            const [hh, mm] = (state?.game_time || '00:00').split(':').map(Number);
            const offset = ((sched.granularity === 'hourly' ? 0 : day * 1440) + (hh || 0) * 60 + (mm || 0)) % period;
            let found = null;
            for (let i = 0; i < sched.entries.length; i++) {
                const e = sched.entries[i];
                const start = Number(e.offset || 0);
                const end = i + 1 < sched.entries.length ? Number(sched.entries[i + 1].offset || 0) : period;
                if (start <= offset && offset < end) {
                    found = e;
                    break;
                }
            }
            if (found && found.weather)
                return found.weather;
        }
        return 'clear';
    }
    /** Next forecast change from "now" (minutes + label), for the widget. */
    function nextForecastChange(state) {
        const sched = state?.forecast_schedule;
        if (!sched || !Array.isArray(sched.entries) || sched.entries.length < 2)
            return null;
        const period = GRANULARITY_MINUTES[sched.granularity || ''] || 1440;
        const day = sched.granularity === 'hourly' ? 0 : ((state?.game_day || 1) - 1) * 1440;
        const [hh, mm] = (state?.game_time || '00:00').split(':').map(Number);
        const now = (day + (hh || 0) * 60 + (mm || 0)) % period;
        const sorted = [...sched.entries].sort((a, b) => (a.offset || 0) - (b.offset || 0));
        for (const e of sorted) {
            const off = Number(e.offset || 0);
            if (off > now) {
                const delta = Math.round(off - now);
                const h = Math.floor(delta / 60), m = delta % 60;
                const when = h > 0 ? (m ? `${h}h ${m}m` : `${h}h`) : `${m}m`;
                return { when, weather: e.weather || 'change', label: `in ${when}: ${e.weather || 'change'}` };
            }
        }
        const first = Number(sorted[0]?.offset || 0) + period;
        const delta = Math.round(first - now);
        return { when: `${Math.floor(delta / 60)}h`, weather: sorted[0]?.weather, label: `in ${Math.floor(delta / 60)}h` };
    }
    // ── top-bar widget ─────────────────────────────────────────────────
    function renderTopBar(el, state) {
        if (!el)
            return;
        const moon = state?.moon_phase || {};
        const weather = effectiveWeather(state);
        const moonIcon = MOON_CHIP[moon.name || ''] || '🌑';
        const weatherIcon = _weatherChip(weather);
        const date = `${_monthName(state?.game_month || 0)} ${_dayOfMonth(state)}, ${state?.game_year || 1}`;
        const moonLabel = (moon.name || '').replace(/_/g, ' ');
        const next = nextForecastChange(state);
        let html = `🕐 ${(state?.game_time || '').slice(0, 5)}`;
        html += ` · ${date}`;
        html += ` · <span title="Moon phase (light bonus ${moon.light_bonus || 0})">${moonIcon} ${moonLabel}</span>`;
        html += ` · <span title="Weather">${weatherIcon} ${weather}</span>`;
        if (next)
            html += ` · <span title="Next forecast change">${next.weather ? _weatherChip(next.weather, '⛅') : ''} ${next.label}</span>`;
        el.textContent = '';
        el.title = 'World Sky — click to open';
        el.style.cursor = 'pointer';
        const span = document.createElement('span');
        span.innerHTML = html;
        el.appendChild(span);
        if (!el._skyClickBound) {
            el._skyClickBound = true;
            el.addEventListener('click', () => _SkyScape.openWorldSky());
        }
    }
    // ── World Sky modal ────────────────────────────────────────────────
    //
    // The modal used to embed the whole `sky-atmosphere.html` console (its own
    // header, time slider, season/moon deck) and stack a second header and three
    // loose control rows on top — two UIs, two headers, two time controls. It is
    // now a single surface: the console is reduced to a **scene-only hero**
    // (`_embedStageCss` hides its chrome), and every control lives in a card
    // built from the app's own design tokens (`_MODAL_CSS`).
    const MODAL_CSS = `
#sky-overlay{position:fixed;inset:0;background:rgba(2,5,11,.68);backdrop-filter:blur(3px);display:flex;align-items:flex-start;justify-content:center;z-index:21000;padding:5vh 16px;}
.vwsky{width:min(1120px,96vw);max-height:92vh;display:flex;flex-direction:column;background:var(--bg-card,#161b22);border:1px solid var(--border,#30363d);border-radius:14px;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,.6);color:var(--text,#e6edf3);font-family:var(--font,'Segoe UI',sans-serif);}
.vwsky-head{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--border,#30363d);background:var(--bg-inset,#1c2128);flex:0 0 auto;}
.vwsky-title{font-size:13px;font-weight:700;letter-spacing:.05em;}
.vwsky-sum{font-size:11px;color:var(--text-dim,#8b949e);}
.vwsky-x{margin-left:auto;background:none;border:1px solid transparent;color:var(--text-dim,#8b949e);font-size:15px;line-height:1;cursor:pointer;border-radius:6px;padding:2px 9px;}
.vwsky-x:hover{background:var(--bg-hover,#30363d);color:var(--text,#e6edf3);}
.vwsky-body{overflow:auto;padding:12px 14px 14px;display:flex;flex-direction:column;gap:10px;}
.vwsky-stage{position:relative;height:238px;border:1px solid var(--border,#30363d);border-radius:10px;overflow:hidden;background:#04070d;flex:0 0 auto;}
.vwsky-stage iframe{display:block;width:100%;height:100%;border:0;}
.vwsky-stats{display:flex;flex-wrap:wrap;gap:8px;padding:1px 1px 0;}
.vwsky-stat{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--text,#e6edf3);background:var(--bg-inset,#1c2128);border:1px solid var(--border-light,#21262d);border-radius:99px;padding:3px 11px;}
.vwsky-stat b{font-size:9px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted,#6e7681);font-weight:700;}
.vwsky-transport{display:flex;flex-wrap:wrap;gap:6px;align-items:center;}
.vwsky-at{margin-left:auto;font-family:var(--font-mono,monospace);font-size:11px;color:var(--text-dim,#8b949e);}
.vwsky-card{background:var(--bg-inset,#1c2128);border:1px solid var(--border-light,#21262d);border-radius:10px;padding:10px 12px;}
.vwsky-lab{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--text-dim,#8b949e);font-weight:700;margin-bottom:9px;}
.vwsky-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
.vwsky-sep{width:1px;height:22px;background:var(--border,#30363d);}
.vwsky-in,.vwsky-sel{font:inherit;font-size:12px;background:var(--bg-input,#21262d);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:6px;padding:5px 8px;outline:none;}
.vwsky-in:focus,.vwsky-sel:focus{border-color:var(--accent,#58a6ff);}
.vwsky-in[type=number]{text-align:center;}
.vwsky-btn{font:inherit;font-size:12px;background:var(--bg-hover,#30363d);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:6px;padding:5px 11px;cursor:pointer;}
.vwsky-btn:hover{border-color:var(--text-muted,#6e7681);}
.vwsky-btn.pri{background:var(--accent-dim,#1f6feb);border-color:var(--accent-dim,#1f6feb);color:#fff;font-weight:600;}
.vwsky-btn.pri:hover{background:var(--accent,#58a6ff);border-color:var(--accent,#58a6ff);}
.vwsky-btn.sm{padding:4px 9px;font-size:11px;}
.vwsky-lab-inline{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--text-dim,#8b949e);}
.vwsky-dot{display:none;font-size:11px;color:var(--orange,#e3b341);margin-left:6px;}
.vwsky-status{font-size:11px;color:var(--text-muted,#6e7681);margin-left:auto;}
.vwsky-grid{display:grid;grid-template-columns:78px 1.05fr .85fr .8fr .8fr 56px 56px .8fr 1.35fr 28px;gap:6px;align-items:center;min-width:820px;}
.vwsky-fhead{font-size:9.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted,#6e7681);font-weight:700;padding:0 4px 2px;}
.vwsky-fhead>span{padding:0 2px;}
.vwsky-rows{display:flex;flex-direction:column;gap:6px;max-height:196px;overflow:auto;padding:2px;}
.vwsky-fcell{font:inherit;font-size:11px;background:var(--bg-input,#21262d);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:5px;padding:4px 6px;min-width:0;outline:none;}
.vwsky-fcell:focus{border-color:var(--accent,#58a6ff);}
.vwsky-del{font-size:11px;background:none;border:1px solid transparent;color:var(--text-muted,#6e7681);border-radius:5px;cursor:pointer;padding:3px 6px;}
.vwsky-del:hover{color:var(--red,#f85149);background:var(--bg-hover,#30363d);}
.vwsky-tl{margin:2px 0 8px;user-select:none;}
.vwsky-ruler{position:relative;height:14px;}
.vwsky-ruler>span{position:absolute;transform:translateX(-50%);font-size:9px;color:var(--text-muted,#6e7681);}
.vwsky-ruler>i{position:absolute;bottom:-3px;width:1px;height:4px;background:var(--border,#30363d);}
.vwsky-trackwrap{position:relative;}
.vwsky-track{position:relative;height:46px;border-radius:8px;background:var(--bg,#0d1117);border:1px solid var(--border,#30363d);overflow:hidden;cursor:crosshair;touch-action:none;}
.vwsky-blk{position:absolute;top:4px;bottom:4px;border-radius:6px;border-left:3px solid rgba(255,255,255,.4);display:flex;align-items:center;gap:5px;padding:0 7px;overflow:hidden;cursor:grab;font-size:11px;color:var(--text,#e6edf3);white-space:nowrap;}
.vwsky-blk:active{cursor:grabbing;}
.vwsky-blk .nm{overflow:hidden;text-overflow:ellipsis;}
.vwsky-now{position:absolute;top:0;bottom:0;width:2px;background:var(--orange,#e3b341);box-shadow:0 0 6px var(--orange,#e3b341);}
.vwsky-now::before{content:'';position:absolute;top:-1px;left:-2px;width:6px;height:6px;border-radius:50%;background:var(--orange,#e3b341);}
.vwsky-scrub{position:absolute;top:0;bottom:0;width:1px;background:var(--accent,#58a6ff);pointer-events:none;}
.vwsky-tip{position:absolute;top:-19px;transform:translateX(-50%);font-size:10px;background:var(--bg-hover,#30363d);border:1px solid var(--border,#30363d);border-radius:4px;padding:1px 6px;color:var(--text,#e6edf3);pointer-events:none;white-space:nowrap;}
.vwsky-presets{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;}
.vwsky-chip{font:inherit;font-size:11px;background:var(--bg-input,#21262d);color:var(--text-dim,#8b949e);border:1px solid var(--border,#30363d);border-radius:99px;padding:3px 10px;cursor:pointer;}
.vwsky-chip:hover{color:var(--text,#e6edf3);border-color:var(--text-muted,#6e7681);}
.vwsky-empty{font-size:11px;color:var(--text-muted,#6e7681);padding:12px;border:1px dashed var(--border,#30363d);border-radius:8px;text-align:center;}
.vwsky-note{font-size:10.5px;line-height:1.55;color:var(--text-muted,#6e7681);margin-top:9px;}
.vwsky-note code{font-family:var(--font-mono,monospace);background:var(--bg,#0d1117);padding:0 3px;border-radius:3px;}
.vwsky-table{width:100%;min-height:96px;margin-top:6px;font-family:var(--font-mono,monospace);font-size:11px;background:var(--bg,#0d1117);color:var(--text,#e6edf3);border:1px solid var(--border,#30363d);border-radius:8px;padding:8px;outline:none;box-sizing:border-box;resize:vertical;}
.vwsky-table:focus{border-color:var(--accent,#58a6ff);}
.vwsky-foot{display:flex;flex-wrap:wrap;gap:16px;padding:9px 16px;border-top:1px solid var(--border,#30363d);font-size:10.5px;color:var(--text-muted,#6e7681);flex:0 0 auto;}
.vwsky-foot code{color:var(--text-dim,#8b949e);font-family:var(--font-mono,monospace);}
.vwsky-det{margin-top:9px;}
.vwsky-det>summary{font-size:10.5px;color:var(--text-dim,#8b949e);cursor:pointer;user-select:none;}
.vwsky-tabs{display:flex;gap:6px;align-items:center;}
.vwsky-tab{font:inherit;font-size:11px;background:var(--bg-inset,#1c2128);color:var(--text-dim,#8b949e);border:1px solid var(--border-light,#21262d);border-radius:8px;padding:5px 13px;cursor:pointer;}
.vwsky-tab:hover{color:var(--text,#e6edf3);}
.vwsky-tab.on{background:var(--bg-hover,#30363d);color:var(--text,#e6edf3);border-color:var(--border,#30363d);font-weight:600;}
.vwsky-rbadge{font-size:9px;letter-spacing:.04em;margin-left:8px;padding:1px 8px;border-radius:99px;background:var(--bg-hover,#30363d);color:var(--text-dim,#8b949e);text-transform:none;font-weight:600;}
.vwsky-rbadge.live{background:rgba(63,185,80,.16);color:var(--green,#3fb950);}
.vwsky-rwrap{max-height:340px;overflow:auto;border:1px solid var(--border-light,#21262d);border-radius:8px;}
.vwsky-rtable{border-collapse:separate;border-spacing:0;width:100%;font-size:11px;}
.vwsky-rtable th,.vwsky-rtable td{padding:5px 8px;text-align:center;border-bottom:1px solid var(--border-light,#21262d);white-space:nowrap;}
.vwsky-rtable thead th{position:sticky;top:0;z-index:2;background:var(--bg-inset,#1c2128);font-size:9.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--text-muted,#6e7681);}
.vwsky-rtable .vwsky-rcorner,.vwsky-rtable .vwsky-rname{position:sticky;left:0;z-index:1;background:var(--bg-inset,#1c2128);text-align:left;font-weight:600;color:var(--text,#e6edf3);}
.vwsky-rtable thead .vwsky-rcorner{z-index:3;}
.vwsky-rtable tbody tr:hover td{background:var(--bg-hover,#30363d);}
.vwsky-rtable .vwsky-rtoday{background:rgba(88,166,255,.07);}
.vwsky-rchip{display:block;font-size:14px;line-height:1.15;}
.vwsky-rtemp{display:block;font-size:9.5px;color:var(--text-dim,#8b949e);font-family:var(--font-mono,monospace);}
`;
    // Injected into the same-origin stage iframe so the embedded console shows as
    // a pure sky scene: its own header, deck and time slider are hidden and the
    // canvas is told to fill, so nothing is duplicated by the modal around it.
    const STAGE_CSS = `
html,body{min-height:0!important;height:100%!important;padding:0!important;margin:0!important;display:block!important;background:transparent!important;overflow:hidden!important;}
.console{width:100%!important;max-width:none!important;min-height:0!important;height:100%!important;border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important;display:block!important;}
.top,.deck{display:none!important;}
.scene{height:100%!important;min-height:0!important;border-radius:0!important;}
`;
    function _ensureModalStyle() {
        if (document.getElementById('vwsky-style'))
            return;
        const style = document.createElement('style');
        style.id = 'vwsky-style';
        style.textContent = MODAL_CSS;
        document.head.appendChild(style);
    }
    function _embedStageCss(iframe) {
        try {
            const doc = iframe && iframe.contentDocument;
            if (!doc || !doc.head)
                return;
            let style = doc.getElementById('vwsky-embed');
            if (!style) {
                style = doc.createElement('style');
                style.id = 'vwsky-embed';
                doc.head.appendChild(style);
            }
            style.textContent = STAGE_CSS;
        }
        catch (e) { /* cross-origin guard; the stage just keeps its own chrome */ }
    }
    function _headSummary() {
        const weather = effectiveWeather(_state());
        const chip = _weatherChip(weather, '');
        return `${chip} ${weather}`.trim();
    }
    function openWorldSky() {
        _ensureModalStyle();
        if (_modalEl) {
            _modalEl.style.display = 'flex';
            _sendStateToIframe();
            return;
        }
        const overlay = document.createElement('div');
        overlay.id = 'sky-overlay';
        const box = document.createElement('div');
        box.className = 'vwsky';
        box.innerHTML = `
            <div class="vwsky-head">
                <span style="font-size:15px;">🌦</span>
                <span class="vwsky-title">World Sky</span>
                <span class="vwsky-sum" id="sky-head-summary"></span>
                <button class="vwsky-x" id="sky-close" title="Close">✕</button>
            </div>
            <div class="vwsky-body">
                <div class="vwsky-stage"><iframe id="sky-atmosphere-frame" src="/static/sky-atmosphere.html" title="Sky"></iframe></div>

                <div class="vwsky-stats" id="sky-stats"></div>
                <div class="vwsky-transport">
                    <button class="vwsky-btn sm" id="sky-play" title="Play the day through the forecast">▶ Play day</button>
                    <span class="vwsky-sep"></span>
                    <button class="vwsky-btn sm sky-jump" data-hour="6">Dawn</button>
                    <button class="vwsky-btn sm sky-jump" data-hour="12">Noon</button>
                    <button class="vwsky-btn sm sky-jump" data-hour="18">Dusk</button>
                    <button class="vwsky-btn sm sky-jump" data-hour="0">Midnight</button>
                    <button class="vwsky-btn sm" id="sky-now" title="Back to the live clock">⏱ Now</button>
                    <span class="vwsky-at" id="sky-at"></span>
                </div>

                <div class="vwsky-tabs">
                    <button class="vwsky-tab on" id="sky-tab-forecast" title="Author and view the forecast">Forecast</button>
                    <button class="vwsky-tab" id="sky-tab-regions" title="The next days, per open-sky area">Regions</button>
                </div>
                <div id="sky-view-forecast" class="vwsky-view">

                <div class="vwsky-card">
                    <span class="vwsky-lab">⏰ Time &amp; date</span>
                    <div class="vwsky-row">
                        <input type="time" id="sky-time-input" class="vwsky-in" style="width:98px;" title="Exact time (HH:MM)">
                        <button class="vwsky-btn sm sky-set-time">Set</button>
                        <span class="vwsky-sep"></span>
                        <button class="vwsky-btn sm sky-skip" data-min="-60">−1h</button>
                        <button class="vwsky-btn sm sky-skip" data-min="-15">−15m</button>
                        <button class="vwsky-btn sm sky-skip" data-min="15">+15m</button>
                        <button class="vwsky-btn sm sky-skip" data-min="60">+1h</button>
                        <button class="vwsky-btn sm sky-skip" data-min="1440">+1d</button>
                        <span class="vwsky-sep"></span>
                        <input type="number" id="sky-date-day" class="vwsky-in" style="width:54px;" min="1" max="30" title="Day">
                        <span style="color:var(--text-muted,#6e7681);">/</span>
                        <input type="number" id="sky-date-month" class="vwsky-in" style="width:54px;" min="1" max="12" title="Month">
                        <span style="color:var(--text-muted,#6e7681);">/</span>
                        <input type="number" id="sky-date-year" class="vwsky-in" style="width:68px;" min="1" title="Year">
                        <button class="vwsky-btn sm sky-set-date">Set</button>
                    </div>
                </div>

                <div class="vwsky-card">
                    <span class="vwsky-lab">🌤 Override<span class="sky-override-active vwsky-dot">● active</span></span>
                    <div class="vwsky-row">
                        <select id="sky-override-weather" class="vwsky-sel" title="weather">
                            <option value="">— weather</option>
                            <option value="clear">☀️ clear</option><option value="cloudy">☁️ cloudy</option><option value="rainy">🌧️ rainy</option>
                            <option value="stormy">⛈️ stormy</option><option value="snowy">🌨️ snowy</option><option value="foggy">🌫️ foggy</option><option value="windy">💨 windy</option>
                        </select>
                        <select id="sky-override-wind" class="vwsky-sel" title="wind magnitude">
                            <option value="">— wind</option>
                            <option value="none">none</option><option value="breeze">breeze</option><option value="wind">wind</option>
                            <option value="gale">gale</option><option value="storm">storm</option><option value="hurricane">hurricane</option>
                        </select>
                        <select id="sky-override-wind-direction" class="vwsky-sel" title="wind blows from">
                            <option value="">— dir</option>
                            <option value="north">N ↑</option><option value="northeast">NE ↗</option><option value="east">E →</option>
                            <option value="southeast">SE ↘</option><option value="south">S ↓</option><option value="southwest">SW ↙</option>
                            <option value="west">W ←</option><option value="northwest">NW ↖</option>
                        </select>
                        <select id="sky-override-humidity" class="vwsky-sel" title="humidity">
                            <option value="">— humidity</option>
                            <option value="dry">dry</option><option value="humid">humid</option><option value="wet">wet</option><option value="flooding">flooding</option>
                        </select>
                        <label class="vwsky-lab-inline">for <input type="number" id="sky-override-duration" class="vwsky-in" style="width:54px;" min="1" value="5" title="duration (turns)"> turns</label>
                        <button class="vwsky-btn pri" id="sky-override-set">Set override</button>
                        <button class="vwsky-btn" id="sky-override-clear">Clear</button>
                    </div>
                </div>

                <div class="vwsky-card">
                    <span class="vwsky-lab">🌦 Forecast</span>
                    <div class="vwsky-row" style="margin-bottom:10px;">
                        <label class="vwsky-lab-inline">mode <select id="sky-sched-mode" class="vwsky-sel" title="forecast mode">
                            <option value="authored">authored</option>
                            <option value="deterministic">deterministic</option>
                            <option value="random">random</option>
                            <option value="hybrid">hybrid</option>
                            <option value="generated">generated</option>
                        </select></label>
                        <label class="vwsky-lab-inline">period <select id="sky-sched-granularity" class="vwsky-sel" title="period entries repeat over">
                            <option value="hourly">hourly · 1 day</option>
                            <option value="weekly">weekly · 7 days</option>
                            <option value="yearly">yearly · 365 days</option>
                        </select></label>
                        <label class="vwsky-lab-inline">seed <input type="number" id="sky-sched-seed" class="vwsky-in" style="width:80px;" title="reproducibility seed"></label>
                        <label class="vwsky-lab-inline">every <input type="number" id="sky-sched-interval" class="vwsky-in" style="width:56px;" min="1" value="1" title="ticks between state-machine transitions"> ticks</label>
                        <button class="vwsky-btn sm" id="sky-sched-add">+ entry</button>
                        <button class="vwsky-btn pri sm" id="sky-sched-save">Save</button>
                        <span class="vwsky-status sky-sched-status"></span>
                    </div>
                    <div id="sky-sched-timeline" class="vwsky-tl"></div>
                    <div class="vwsky-fhead vwsky-grid">
                        <span>Offset</span><span>Weather</span><span>Wind</span><span>From</span><span>Humidity</span>
                        <span>Temp Δ</span><span>Light Δ</span><span>Air</span><span>Message</span><span></span>
                    </div>
                    <div id="sky-sched-entries" class="vwsky-rows"></div>
                    <div class="vwsky-presets" id="sky-sched-presets"></div>
                    <div class="vwsky-note">Offsets are minutes into the period; entries repeat each period. Temperature and light are shown <em>in-game</em> as engine-derived values; here you author only the <code>temperature_mod</code> / <code>light_mod</code> deltas. <code>wind</code> is magnitude; <code>wind_direction</code> is where it blows <em>from</em>. authored &amp; hybrid use the entries; deterministic / random / generated roll the table.</div>
                    <details class="vwsky-det">
                        <summary>Transition table — deterministic / random / generated</summary>
                        <textarea id="sky-sched-table" class="vwsky-table" spellcheck="false" placeholder='{ "clear": { "clear": 7, "cloudy": 2 } }'></textarea>
                    </details>
                </div>

                </div>
                <div id="sky-view-regions" class="vwsky-view" style="display:none;">
                    <div class="vwsky-card">
                        <span class="vwsky-lab">Regions<span class="vwsky-rbadge" id="sky-regions-badge"></span></span>
                        <div class="vwsky-row" style="margin-bottom:9px;">
                            <input type="text" id="sky-regions-filter" class="vwsky-in" placeholder="Filter areas..." style="width:172px;" title="Filter areas by name">
                            <span class="vwsky-sep"></span>
                            <label class="vwsky-lab-inline">days <input type="number" id="sky-regions-days" class="vwsky-in" style="width:54px;" min="1" max="30" value="7"></label>
                            <button class="vwsky-btn sm" id="sky-regions-refresh">Refresh</button>
                            <span class="vwsky-status" id="sky-regions-status"></span>
                        </div>
                        <div id="sky-regions-grid" class="vwsky-rwrap"></div>
                        <div class="vwsky-note">The generated per-area weather the engine would roll for each of the next <em>N</em> days, starting today. A pure projection over <code>generate_weather_field</code> - opening this tab never advances the clock. A <strong>preview</strong> badge means the world's forecast mode is not <code>generated</code>, so the live sim follows its authored forecast instead.</div>
                    </div>
                </div>
            </div>
            <div class="vwsky-foot">
                <span>Clock <code id="sky-clock-readout"></code></span>
                <span>Moon <code id="sky-moon-readout"></code></span>
                <span>Forecast <code id="sky-forecast-readout"></code></span>
            </div>
        `;
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        _modalEl = overlay;
        overlay.addEventListener('mousedown', (ev) => { if (ev.target === overlay)
            _closeSky(); });
        box.querySelector('#sky-close').addEventListener('click', _closeSky);
        box.querySelectorAll('.sky-skip').forEach(btn => {
            btn.addEventListener('click', () => {
                _skipTime(Number(btn.dataset.min || 60));
                _populateControls();
            });
        });
        box.querySelector('.sky-set-time')?.addEventListener('click', _setExactTime);
        box.querySelector('.sky-set-date')?.addEventListener('click', _setExactDate);
        box.querySelector('#sky-override-set')?.addEventListener('click', _setOverride);
        box.querySelector('#sky-override-clear')?.addEventListener('click', _clearOverride);
        box.querySelector('#sky-sched-add')?.addEventListener('click', () => _addEntryRow());
        box.querySelector('#sky-sched-save')?.addEventListener('click', _saveSchedule);
        box.querySelector('#sky-play')?.addEventListener('click', _togglePlay);
        box.querySelector('#sky-now')?.addEventListener('click', () => { _stopPlay(); _endScrub(); });
        box.querySelectorAll('.sky-jump').forEach((b) => {
            b.addEventListener('click', () => _jumpToHour(Number(b.dataset.hour) || 0));
        });
        box.querySelector('#sky-tab-forecast')?.addEventListener('click', () => _switchSkyTab('forecast'));
        box.querySelector('#sky-tab-regions')?.addEventListener('click', () => _switchSkyTab('regions'));
        box.querySelector('#sky-regions-refresh')?.addEventListener('click', () => _renderRegions(true));
        box.querySelector('#sky-regions-days')?.addEventListener('change', () => _renderRegions(true));
        box.querySelector('#sky-regions-filter')?.addEventListener('input', () => _renderRegions(false));
        const iframe = document.getElementById('sky-atmosphere-frame');
        iframe.addEventListener('load', () => { _embedStageCss(iframe); _sendStateToIframe(); });
        window.addEventListener('message', (ev) => {
            if (ev.data?.type === 'sky:ready')
                _sendStateToIframe();
        });
        _populateControls();
        _sendStateToIframe();
        if (_timer)
            clearInterval(_timer);
        _timer = setInterval(() => {
            if (document.contains(overlay) && !_scrubActive)
                _sendStateToIframe();
        }, 3000);
    }
    // The stage map keys on canonical ids, so an authored spelling ("overcast")
    // must be resolved first or it falls through to "clear".
    const STAGE_WEATHER_MAP = { clear: 'clear', cloudy: 'overcast', rainy: 'rain', stormy: 'storm', snowy: 'snow', foggy: 'fog', windy: 'partly' };
    const MOON_INDEX = { new_moon: 0, crescent: 1, quarter: 2, gibbous: 3, full_moon: 4, waning: 5, blood_moon: 4 };
    /** Post a sky state to the stage at a given hour. Shared by "now" and by the
     *  timeline's hover-scrub, so the hero sky is a live preview of the forecast. */
    function _postSky(hour, weather, syncLabel) {
        const iframe = document.getElementById('sky-atmosphere-frame');
        if (!iframe || !iframe.contentWindow)
            return;
        const state = _state();
        const canon = _WEATHER_ALIASES[weather] || weather;
        const moon = state?.moon_phase || {};
        const phase = MOON_INDEX[moon.name || ''] !== undefined ? MOON_INDEX[moon.name || ''] : 0;
        // The engine's area temperature, so the hero's readout is the sim's number,
        // not the stage's own seasonal guess (the two disagreed by 3 degrees).
        const envTemp = _currentAreaEnv(state).env.temperature;
        iframe.contentWindow.postMessage({
            type: 'engine:sky-state',
            t: hour,
            season: _season(state),
            weather: STAGE_WEATHER_MAP[canon] || 'clear',
            phase: phase,
            tempC: envTemp !== undefined && envTemp !== null ? Number(envTemp) : undefined,
            engineTime: syncLabel || (state?.game_time || '').slice(0, 5),
            engineDay: state?.game_day || 1,
        }, '*');
    }
    function _sendStateToIframe() {
        const state = _state();
        const t = (state?.game_time || '09:40').split(':').map(Number);
        _postSky((t[0] || 0) + (t[1] || 0) / 60, effectiveWeather(state), null);
    }
    function _closeSky() {
        if (_timer) {
            clearInterval(_timer);
            _timer = null;
        }
        _stopPlay();
        if (_modalEl)
            _modalEl.remove();
        _modalEl = null;
    }
    function _state() {
        return (typeof worldState !== 'undefined' && worldState.data) || {};
    }
    function _skipTime(minutes) {
        const state = _state();
        const [hh, mm] = (state.game_time || '08:00').split(':').map(Number);
        const targetMin = ((hh || 0) * 60 + (mm || 0) + minutes) % 1440;
        // Clamp to 0..1439 (negative wraparound)
        const clamped = ((targetMin % 1440) + 1440) % 1440;
        fetch('/api/settings/clock_start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clock_start_hour: Math.floor(clamped / 60), clock_start_minute: clamped % 60 })
        }).then(() => worldState?.fetch?.());
    }
    function _setExactTime() {
        const input = document.getElementById('sky-time-input');
        if (!input || !input.value)
            return;
        const [h, m] = input.value.split(':').map(Number);
        if (isNaN(h) || isNaN(m))
            return;
        fetch('/api/settings/clock_start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clock_start_hour: h, clock_start_minute: m })
        }).then(() => worldState?.fetch?.());
    }
    function _setExactDate() {
        const d = parseInt(document.getElementById('sky-date-day')?.value || '');
        const m = parseInt(document.getElementById('sky-date-month')?.value || '');
        const y = parseInt(document.getElementById('sky-date-year')?.value || '');
        if (isNaN(d) && isNaN(m) && isNaN(y))
            return;
        const body = {};
        if (!isNaN(d))
            body.day = d;
        if (!isNaN(m))
            body.month = m;
        if (!isNaN(y))
            body.year = y;
        fetch('/api/settings/date', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(() => worldState?.fetch?.());
    }
    function _setOverride() {
        const weather = document.getElementById('sky-override-weather')?.value || '';
        const wind = document.getElementById('sky-override-wind')?.value || '';
        const windDir = document.getElementById('sky-override-wind-direction')?.value || '';
        const humidity = document.getElementById('sky-override-humidity')?.value || '';
        const dur = parseInt(document.getElementById('sky-override-duration')?.value || '5');
        const data = {};
        if (weather)
            data.weather = weather;
        if (wind)
            data.wind = wind;
        if (windDir)
            data.wind_direction = windDir;
        if (humidity)
            data.humidity = humidity;
        if (dur > 0)
            data.duration_ticks = dur;
        fetch('/api/settings/forecast-override', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-WV-Editor': 'sky-widget' },
            body: JSON.stringify(data)
        }).then(() => worldState?.fetch?.());
    }
    function _clearOverride() {
        fetch('/api/settings/forecast-override', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-WV-Editor': 'sky-widget' },
            body: JSON.stringify({ clear_all: true })
        }).then(() => worldState?.fetch?.());
    }
    function _populateControls() {
        const state = _state();
        if (!state)
            return;
        const timeInput = document.getElementById('sky-time-input');
        const dayInput = document.getElementById('sky-date-day');
        const monthInput = document.getElementById('sky-date-month');
        const yearInput = document.getElementById('sky-date-year');
        const clockReadout = document.getElementById('sky-clock-readout');
        const moonReadout = document.getElementById('sky-moon-readout');
        const forecastReadout = document.getElementById('sky-forecast-readout');
        if (timeInput) {
            const t = (state.game_time || '09:40').slice(0, 5);
            timeInput.value = t;
        }
        if (dayInput) {
            dayInput.value = String(_dayOfMonth(state));
            dayInput.max = String(_daysPerMonth(state));
        }
        if (monthInput)
            monthInput.value = String(state.game_month || 1);
        if (yearInput)
            yearInput.value = String(state.game_year || 1);
        if (clockReadout)
            clockReadout.textContent = `${state.game_time || '?'} · Day ${state.game_day || 1}, ${_monthName(state.game_month || 1)} ${state.game_year || 1}`;
        if (moonReadout) {
            const moon = state.moon_phase || {};
            const icon = MOON_CHIP[moon.name || ''] || '🌑';
            const label = (moon.name || '').replace(/_/g, ' ');
            const bonus = moon.light_bonus || 0;
            const next = nextForecastChange(state);
            moonReadout.textContent = `${icon} ${label} (+${bonus} night light) · ${next ? `next: ${next.weather || 'change'} ${next.label}` : 'no forecast change'}`;
        }
        if (forecastReadout) {
            const sched = state.forecast_schedule || {};
            const entries = (sched.entries || []).length;
            forecastReadout.textContent = `${entries} entries · ${sched.granularity || 'hourly'}`;
        }
        _updateHeadSummary();
        _renderStats();
        _updateOverrideIndicator();
        _populateWeatherSelect();
        _renderScheduleEditor();
    }
    /** The header's one-line "what the sky is right now" summary. */
    function _updateHeadSummary() {
        const el = document.getElementById('sky-head-summary');
        if (el)
            el.textContent = _headSummary();
    }
    /** The controlled player's current area — the place the sky is "over". */
    function _currentAreaEnv(state) {
        const players = (state.players || {});
        const name = state.active_player;
        const p = (name && players[name]) || {};
        const areaId = p.current_area_id;
        const g = state.graph;
        const rawNodes = (g && g.nodes) || [];
        const arr = (Array.isArray(rawNodes) ? rawNodes
            : Object.values(rawNodes));
        const node = arr.find((n) => n && n.type === 'area'
            && (n.id === areaId || (!areaId && n.name === p.current_area)));
        const props = (node && node.properties);
        const env = (props && props.environment) || {};
        return { env: env, area: String((node && node.name) || p.current_area || '') };
    }
    /** The hero's live readout — the real environment of the area you are in. */
    function _renderStats() {
        const el = document.getElementById('sky-stats');
        if (!el)
            return;
        const { env } = _currentAreaEnv(_state());
        const parts = [];
        const add = (label, value) => {
            if (value)
                parts.push(`<span class="vwsky-stat"><b>${_esc(label)}</b>${_esc(value)}</span>`);
        };
        const wind = env.wind ? `${String(env.wind)}${env.wind_direction ? ' · ' + String(env.wind_direction) : ''}` : '';
        add('Wind', wind);
        add('Humidity', env.humidity ? String(env.humidity) : '');
        add('Air', env.air ? String(env.air) : '');
        add('Temp', env.temperature != null ? `${Math.round(Number(env.temperature))}°C` : '');
        add('Light', env.light != null ? `${Math.round(Number(env.light))}%` : '');
        add('Precip', env.precipitation ? `${env.precipitation} mm/h` : '');
        add('Snow', env.snow_depth ? `${env.snow_depth} cm` : '');
        el.innerHTML = parts.join('');
    }
    let _playTimer = null;
    function _stopPlay() {
        if (_playTimer !== null) {
            clearInterval(_playTimer);
            _playTimer = null;
        }
        const btn = document.getElementById('sky-play');
        if (btn)
            btn.textContent = '▶ Play day';
    }
    function _updateAtLabel(weather, label) {
        const el = document.getElementById('sky-at');
        if (el)
            el.textContent = `${label} · ${weather || '—'}`;
    }
    /** "Play the day": step a preview through the forecast, sky and ribbon in step. */
    function _togglePlay() {
        if (_playTimer !== null) {
            _stopPlay();
            _endScrub();
            return;
        }
        const sched = (_state().forecast_schedule || {});
        const gran = sched.granularity || 'hourly';
        const period = GRANULARITY_MINUTES[gran] || 1440;
        const entries = _domEntries();
        let minute = _nowMinutes();
        const btn = document.getElementById('sky-play');
        if (btn)
            btn.textContent = '⏸ Pause';
        _playTimer = window.setInterval(() => {
            minute = (minute + 15) % period;
            const weather = _weatherAt(entries, period, minute);
            _scrubTo(minute, entries, period, gran);
            _updateAtLabel(weather, _fmtOffset(minute, gran));
        }, 130);
    }
    function _jumpToHour(hour) {
        _stopPlay();
        const sched = (_state().forecast_schedule || {});
        const gran = sched.granularity || 'hourly';
        const period = GRANULARITY_MINUTES[gran] || 1440;
        const minute = Math.max(0, Math.min(period, hour * 60));
        const entries = _domEntries();
        _scrubTo(minute, entries, period, gran);
        _updateAtLabel(_weatherAt(entries, period, minute), _fmtOffset(minute, gran));
    }
    // -- regions outlook (task-762) ------------------------------------
    // A days x per-area table, projected over the generated field via
    // GET /api/settings/forecast/outlook. It is a *read*: switching to this tab
    // never ticks the world. The hero and transport stay visible above, so the
    // sky the table describes is always on screen.
    let _regionsData = null;
    let _regionsFetching = false;
    function _switchSkyTab(which) {
        const regions = which === 'regions';
        const f = document.getElementById('sky-view-forecast');
        const r = document.getElementById('sky-view-regions');
        if (f)
            f.style.display = regions ? 'none' : '';
        if (r)
            r.style.display = regions ? '' : 'none';
        document.getElementById('sky-tab-forecast')?.classList.toggle('on', !regions);
        document.getElementById('sky-tab-regions')?.classList.toggle('on', regions);
        if (regions && !_regionsData)
            _renderRegions(true);
    }
    /** Render (and optionally refetch) the regions table. `force` re-hits the API. */
    function _renderRegions(force) {
        const grid = document.getElementById('sky-regions-grid');
        if (!grid)
            return;
        const status = document.getElementById('sky-regions-status');
        if (force && !_regionsFetching) {
            _regionsFetching = true;
            const daysEl = document.getElementById('sky-regions-days');
            const days = Math.max(1, Math.min(30, Number(daysEl?.value) || 7));
            if (status)
                status.textContent = 'loading...';
            fetch(`/api/settings/forecast/outlook?days=${days}`, { cache: 'no-store' })
                .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
                .then((d) => {
                _regionsData = d;
                _regionsFetching = false;
                if (status)
                    status.textContent = '';
                _renderRegions(false);
            })
                .catch(() => {
                _regionsFetching = false;
                if (status)
                    status.textContent = 'could not load outlook';
                grid.innerHTML = '<div class="vwsky-empty">Could not load the outlook.</div>';
            });
            return;
        }
        if (!_regionsData)
            return;
        grid.innerHTML = _regionsTable(_regionsData);
    }
    /** The table: one row per open-sky area, one column per day, today first. */
    function _regionsTable(data) {
        const days = data.days || [];
        if (!days.length)
            return '<div class="vwsky-empty">No open-sky areas to forecast.</div>';
        // The badge is the honesty line: a live field vs a preview the sim is not
        // actually running.
        const badge = document.getElementById('sky-regions-badge');
        if (badge) {
            badge.textContent = data.generated ? 'live field' : `preview - mode: ${data.mode || 'authored'}`;
            badge.classList.toggle('live', !!data.generated);
        }
        const filterEl = document.getElementById('sky-regions-filter');
        const q = (filterEl?.value || '').trim().toLowerCase();
        const all = data.areas || [];
        const areas = all.filter((a) => !q || a.name.toLowerCase().includes(q));
        let head = '<thead><tr><th class="vwsky-rcorner">Area</th>';
        for (const d of days) {
            const moon = MOON_CHIP[(d.moon && d.moon.name) || ''] || '';
            const cls = d.offset === 0 ? ' class="vwsky-rtoday"' : '';
            head += `<th${cls}>${_esc(_monthName(d.month))} ${_esc(d.day_of_month)}<br>${moon}</th>`;
        }
        head += '</tr></thead>';
        let body = '';
        for (const a of areas) {
            body += `<tr><td class="vwsky-rname" title="${_esc(a.id)}">${_esc(a.name)}</td>`;
            for (const d of days) {
                const state = (d.states || {})[a.id] || '';
                const temp = (d.temps || {})[a.id];
                const cls = d.offset === 0 ? ' class="vwsky-rtoday"' : '';
                const t = temp != null ? `${Math.round(Number(temp))}\u00b0` : '';
                body += `<td${cls} title="${_esc(a.name)} - ${_esc(state)}${t ? ', ' + t : ''}">`
                    + `<span class="vwsky-rchip">${_weatherChip(state, '')}</span>`
                    + `<span class="vwsky-rtemp">${t}</span></td>`;
            }
            body += '</tr>';
        }
        const count = `${areas.length} of ${all.length} areas - ${days.length} days`;
        return `<table class="vwsky-rtable">${head}<tbody>${body}</tbody></table>`
            + `<div class="vwsky-note" style="padding:7px 9px;">${_esc(count)}</div>`;
    }
    /** The "override active" dot. Refreshed here *and* on every state update
     *  (see `_paint`) so setting or clearing an override shows immediately,
     *  instead of only after the modal is reopened or the clock is skipped. */
    function _updateOverrideIndicator() {
        const active = document.querySelector('.sky-override-active');
        if (active)
            active.style.display = _state().forecast_override ? 'inline' : 'none';
    }
    // ── forecast editor (task-762) ─────────────────────────────
    // Author and view `forecast_schedule` over the existing GET/POST
    // /api/settings/forecast — no second engine. The timeline lays the entries
    // out over the period granularity and each row edits one entry; the columns
    // are honest (deltas, not a per-entry temperature; no precipitation, which
    // is not modelled).
    const SCHED_WEATHER_ORDER = ['clear', 'cloudy', 'windy', 'rainy', 'stormy', 'foggy', 'snowy'];
    const SCHED_WINDS = ['none', 'breeze', 'wind', 'gale', 'storm', 'hurricane'];
    const SCHED_DIRECTIONS = ['north', 'northeast', 'east', 'southeast',
        'south', 'southwest', 'west', 'northwest'];
    const SCHED_HUMIDITIES = ['dry', 'humid', 'wet', 'flooding'];
    /** Minimal HTML-escape for values the author types into the modal. */
    function _esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }
    function _options(values, selected, blank) {
        let html = `<option value="">${_esc(blank)}</option>`;
        for (const v of values) {
            html += `<option value="${_esc(v)}"${v === selected ? ' selected' : ''}>${_esc(v)}</option>`;
        }
        if (selected && !values.includes(selected)) {
            html += `<option value="${_esc(selected)}" selected>${_esc(selected)}</option>`;
        }
        return html;
    }
    /** Weather ids for the entry select: the canonical set plus any registry ids. */
    function _weatherIds() {
        const ids = [...SCHED_WEATHER_ORDER];
        for (const id of _WEATHER_IDS)
            if (!ids.includes(id))
                ids.push(id);
        return ids;
    }
    /** Rebuild the override weather dropdown from the registry (task-772), so a
     *  world's own extreme types are selectable, not just the built-in seven. */
    function _populateWeatherSelect() {
        const sel = document.getElementById('sky-override-weather');
        if (!sel)
            return;
        const ids = _weatherIds();
        const sig = ids.join(',');
        if (sel.dataset.sig === sig)
            return; // registry unchanged since last build
        sel.dataset.sig = sig;
        const current = sel.value;
        sel.innerHTML = '<option value="">— weather</option>' + ids.map((id) => {
            const chip = _weatherChip(id, '');
            return `<option value="${_esc(id)}"${id === current ? ' selected' : ''}>${chip ? chip + ' ' : ''}${_esc(id)}</option>`;
        }).join('');
    }
    /** A compact "where in the period" label for an offset in minutes. */
    function _offsetHint(off, granularity) {
        if (!Number.isFinite(off) || off < 0)
            return '';
        const hh = Math.floor((off % 1440) / 60);
        const mm = off % 60;
        const t = `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
        const days = Math.floor(off / 1440);
        if (granularity === 'hourly')
            return t;
        if (granularity === 'weekly')
            return `D${days + 1} ${t}`;
        return `+${days}d ${t}`;
    }
    function _entryFieldsHtml(e) {
        const num = (v) => (v === undefined || v === null || v === '' ? '' : String(v));
        return ''
            + `<input type="number" class="vwsky-fcell" data-f="offset" value="${num(e.offset ?? 0)}" title="minutes into the period">`
            + `<select class="vwsky-fcell" data-f="weather" title="weather">${_options(_weatherIds(), e.weather || '', '— weather')}</select>`
            + `<select class="vwsky-fcell" data-f="wind" title="wind magnitude">${_options(SCHED_WINDS, e.wind || '', '— wind')}</select>`
            + `<select class="vwsky-fcell" data-f="wind_direction" title="wind blows from">${_options(SCHED_DIRECTIONS, e.wind_direction || '', '— dir')}</select>`
            + `<select class="vwsky-fcell" data-f="humidity" title="humidity">${_options(SCHED_HUMIDITIES, e.humidity || '', '— humidity')}</select>`
            + `<input type="number" class="vwsky-fcell" step="0.5" data-f="temperature_mod" value="${num(e.temperature_mod)}" title="temperature delta (degrees C)">`
            + `<input type="number" class="vwsky-fcell" step="1" data-f="light_mod" value="${num(e.light_mod)}" title="light delta">`
            + `<input type="text" class="vwsky-fcell" data-f="air" value="${_esc(e.air)}" placeholder="air" title="air (free text)">`
            + `<input type="text" class="vwsky-fcell" data-f="message" value="${_esc(e.message)}" placeholder="message" title="log message on this entry">`
            + `<button class="vwsky-del sky-sched-del" title="remove entry">✕</button>`;
    }
    function _wireRow(row) {
        row.querySelector('.sky-sched-del')?.addEventListener('click', () => row.remove());
    }
    function _addEntryRow(e) {
        const box = document.getElementById('sky-sched-entries');
        if (!box)
            return;
        const granularity = document.getElementById('sky-sched-granularity')?.value || 'hourly';
        const row = document.createElement('div');
        row.className = 'vwsky-grid sky-sched-row';
        row.innerHTML = _entryFieldsHtml(e || { offset: _nextOffset() });
        _wireRow(row);
        // Drop the "no entries" placeholder if present.
        box.querySelector('div:not(.sky-sched-row)')?.remove();
        box.appendChild(row);
        if (e?.offset !== undefined) {
            const off = row.querySelector('[data-f="offset"]');
            if (off)
                off.title = _offsetHint(Number(e.offset), granularity);
        }
    }
    /** One past the last entry's offset, so a new row lands after the others. */
    function _nextOffset() {
        let max = -1;
        document.querySelectorAll('#sky-sched-entries [data-f="offset"]').forEach((el) => {
            const v = parseFloat(el.value);
            if (Number.isFinite(v) && v > max)
                max = v;
        });
        return max + 60;
    }
    function _renderScheduleEditor() {
        const state = _state();
        const sched = (state.forecast_schedule || {});
        const mode = document.getElementById('sky-sched-mode');
        const gran = document.getElementById('sky-sched-granularity');
        const seed = document.getElementById('sky-sched-seed');
        const interval = document.getElementById('sky-sched-interval');
        if (mode)
            mode.value = sched.mode || 'authored';
        if (gran)
            gran.value = sched.granularity || 'hourly';
        if (seed)
            seed.value = (sched.seed === null || sched.seed === undefined) ? '' : String(sched.seed);
        if (interval)
            interval.value = String(sched.transition_interval || 1);
        const table = document.getElementById('sky-sched-table');
        if (table) {
            const tt = sched.transition_table;
            table.value = (tt && Object.keys(tt).length) ? JSON.stringify(tt, null, 2) : '';
        }
        const box = document.getElementById('sky-sched-entries');
        if (box) {
            const entries = Array.isArray(sched.entries) ? sched.entries : [];
            if (entries.length) {
                box.innerHTML = '';
                for (const e of entries)
                    _addEntryRow(e);
            }
            else {
                box.innerHTML = `<div class="vwsky-empty">No entries yet — add one, or pick a preset below.</div>`;
            }
        }
        _renderTimeline(sched);
        const presets = document.getElementById('sky-sched-presets');
        if (presets && !presets.childElementCount) {
            presets.innerHTML = SCHED_PRESETS.map((p, i) => `<button class="vwsky-chip" data-preset="${i}">${_esc(p.name)}</button>`).join('');
            presets.querySelectorAll('[data-preset]').forEach((b) => {
                b.addEventListener('click', () => _applyPreset(SCHED_PRESETS[Number(b.dataset.preset)].hours));
            });
        }
    }
    // ── interactive timeline (task-762) ────────────────────────────────
    // The forecast is temporal, so time *is* the editor: entries are draggable
    // blocks over a ruled period, a playhead marks "now", and hovering the track
    // scrubs the hero sky through the forecast live — no save, no round-trip.
    const WEATHER_TINT = {
        clear: 'rgba(210,164,65,.26)', cloudy: 'rgba(139,148,158,.28)',
        windy: 'rgba(110,118,129,.26)', rainy: 'rgba(88,166,255,.28)',
        stormy: 'rgba(188,140,255,.30)', foggy: 'rgba(139,148,158,.20)',
        snowy: 'rgba(230,237,243,.26)', blizzard: 'rgba(230,237,243,.36)',
        thunderstorm: 'rgba(188,140,255,.36)', heatwave: 'rgba(248,81,73,.28)',
        cold_snap: 'rgba(88,166,255,.36)',
    };
    function _canonOf(w) {
        return _WEATHER_ALIASES[w] || w;
    }
    function _weatherTint(w) {
        return WEATHER_TINT[_canonOf(w)] || 'rgba(139,148,158,.24)';
    }
    /** Minutes-since-midnight of the current game time, for the "now" playhead. */
    function _nowMinutes() {
        const t = (_state().game_time || '00:00').split(':').map(Number);
        return (t[0] || 0) * 60 + (t[1] || 0);
    }
    /** The entries as they are on screen right now (unsaved edits included). */
    function _domEntries() {
        const out = [];
        document.querySelectorAll('#sky-sched-entries .sky-sched-row').forEach((row) => {
            const get = (f) => row.querySelector(`[data-f="${f}"]`)?.value ?? '';
            out.push({
                offset: parseInt(get('offset') || '0', 10) || 0,
                weather: get('weather'), wind: get('wind'),
                wind_direction: get('wind_direction'), humidity: get('humidity'),
            });
        });
        return out;
    }
    /** The active entry's weather at a period offset (wrapping) — for the scrub. */
    function _weatherAt(entries, period, minutes) {
        if (!entries.length)
            return effectiveWeather(_state());
        const off = ((minutes % period) + period) % period;
        let best = null;
        let wrap = null;
        for (const e of entries) {
            const eo = Number(e.offset) || 0;
            if (!wrap || eo < (Number(wrap.offset) || 0))
                wrap = e;
            if (eo <= off && (!best || eo > (Number(best.offset) || 0)))
                best = e;
        }
        const chosen = best || wrap;
        return (chosen && chosen.weather) || '';
    }
    function _fmtOffset(minutes, granularity) {
        const total = Math.round(minutes);
        const hh = Math.floor((total % 1440) / 60);
        const mm = total % 60;
        const t = `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
        if (granularity === 'hourly')
            return t;
        return `Day ${Math.floor(total / 1440) + 1} ${t}`;
    }
    let _scrubActive = false;
    function _endScrub() {
        if (!_scrubActive)
            return;
        _scrubActive = false;
        const scrub = document.getElementById('sky-scrub');
        const tip = document.getElementById('sky-tip');
        if (scrub)
            scrub.style.display = 'none';
        if (tip)
            tip.style.display = 'none';
        _sendStateToIframe(); // snap the sky back to now
    }
    function _scrubTo(minutes, entries, period, granularity) {
        _scrubActive = true;
        const pct = Math.min(100, Math.max(0, (minutes / period) * 100));
        const weather = _weatherAt(entries, period, minutes);
        _postSky((minutes / 60) % 24, weather || effectiveWeather(_state()), `${_fmtOffset(minutes, granularity)} · preview`);
        const scrub = document.getElementById('sky-scrub');
        const tip = document.getElementById('sky-tip');
        if (scrub) {
            scrub.style.display = 'block';
            scrub.style.left = `${pct}%`;
        }
        if (tip) {
            tip.style.display = 'block';
            tip.style.left = `${pct}%`;
            tip.textContent = `${_fmtOffset(minutes, granularity)} · ${weather || '—'}`;
        }
    }
    /** The period as an editable track: draggable blocks, a ruler, a "now" line. */
    function _renderTimeline(sched) {
        const tl = document.getElementById('sky-sched-timeline');
        if (!tl)
            return;
        const granularity = sched.granularity || 'hourly';
        const period = GRANULARITY_MINUTES[granularity] || 1440;
        const entries = _domEntries();
        const sorted = entries.map((e, i) => ({ e, i }))
            .sort((a, b) => (Number(a.e.offset) || 0) - (Number(b.e.offset) || 0));
        const rulerFracs = granularity === 'hourly' ? [0, .25, .5, .75, 1]
            : granularity === 'weekly' ? [0, 1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7, 1]
                : [0, .25, .5, .75, 1];
        const ruler = rulerFracs.map((f) => {
            const lbl = granularity === 'hourly' ? `${String(Math.round(f * 24)).padStart(2, '0')}:00`
                : granularity === 'weekly' ? `D${Math.round(f * 7) + 1}` : `M${Math.round(f * 12) + 1}`;
            return `<i style="left:${f * 100}%"></i><span style="left:${f * 100}%">${lbl}</span>`;
        }).join('');
        const blocks = sorted.map(({ e, i }) => {
            const start = Number(e.offset) || 0;
            const after = sorted.find((o) => (Number(o.e.offset) || 0) > start);
            const end = after ? (Number(after.e.offset) || 0) : period;
            const left = (start / period) * 100;
            const width = Math.max(3, ((end - start) / period) * 100);
            const w = e.weather || '';
            return `<div class="vwsky-blk" data-i="${i}" style="left:${left}%;width:${width}%;background:${_weatherTint(w)}" title="${_esc(_fmtOffset(start, granularity))}">
                <span>${_weatherChip(w, '·')}</span><span class="nm">${_esc(w || 'no weather')}</span></div>`;
        }).join('');
        const nowPct = granularity === 'hourly' ? (_nowMinutes() / period) * 100 : -1;
        const playhead = (nowPct >= 0 && nowPct <= 100)
            ? `<div class="vwsky-now" style="left:${nowPct}%" title="now"></div>` : '';
        tl.innerHTML = `<div class="vwsky-ruler">${ruler}</div>`
            + `<div class="vwsky-trackwrap">`
            + `<div class="vwsky-track" id="sky-tl-track">${blocks}${playhead}</div>`
            + `<div class="vwsky-scrub" id="sky-scrub" style="display:none;"></div>`
            + `<div class="vwsky-tip" id="sky-tip" style="display:none;"></div>`
            + `</div>`;
        const track = tl.querySelector('#sky-tl-track');
        if (track)
            _wireTimeline(track, entries, period, granularity);
    }
    function _wireTimeline(track, entries, period, granularity) {
        const posToMin = (clientX) => {
            const rect = track.getBoundingClientRect();
            return Math.max(0, Math.min(period, ((clientX - rect.left) / rect.width) * period));
        };
        let drag = null;
        track.querySelectorAll('.vwsky-blk').forEach((blk) => {
            blk.addEventListener('pointerdown', (ev) => {
                ev.preventDefault();
                const i = Number(blk.dataset.i);
                drag = { i, el: blk, startX: ev.clientX, startOffset: Number(entries[i]?.offset) || 0 };
                try {
                    blk.setPointerCapture(ev.pointerId);
                }
                catch (e) { /* synthetic/edge pointer */ }
            });
        });
        track.addEventListener('pointermove', (ev) => {
            if (drag) {
                const rect = track.getBoundingClientRect();
                const delta = ((ev.clientX - drag.startX) / rect.width) * period;
                const off = Math.max(0, Math.min(period - 15, Math.round((drag.startOffset + delta) / 15) * 15));
                drag.el.style.left = `${(off / period) * 100}%`;
                const row = document.querySelectorAll('#sky-sched-entries .sky-sched-row')[drag.i];
                const inp = row?.querySelector('[data-f="offset"]');
                if (inp)
                    inp.value = String(off);
            }
            else {
                _scrubTo(posToMin(ev.clientX), entries, period, granularity);
            }
        });
        track.addEventListener('pointerleave', () => { if (!drag)
            _endScrub(); });
        // Re-render on release so block widths re-derive from the new offsets.
        const finish = () => {
            if (drag) {
                drag = null;
                _renderTimeline(_state().forecast_schedule);
            }
        };
        track.addEventListener('pointerup', finish);
        window.addEventListener('pointerup', finish);
    }
    /** Preset day-shapes, seeded in hours, so an author gets a starting point. */
    const SCHED_PRESETS = [
        { name: '☀️ Clear', hours: [[0, 'clear']] },
        { name: '🌦 Showery', hours: [[0, 'cloudy'], [6, 'rainy'], [10, 'rainy'], [13, 'cloudy'], [19, 'clear']] },
        { name: '⛈️ Storm front', hours: [[0, 'cloudy'], [5, 'stormy'], [9, 'rainy'], [14, 'cloudy'], [18, 'clear']] },
        { name: '❄️ Snow day', hours: [[0, 'snowy'], [9, 'snowy'], [16, 'cloudy']] },
        { name: '🌫️ Foggy dawn', hours: [[0, 'foggy'], [4, 'foggy'], [8, 'clear']] },
    ];
    function _applyPreset(hours) {
        const box = document.getElementById('sky-sched-entries');
        if (!box)
            return;
        box.innerHTML = '';
        for (const [h, weather] of hours)
            _addEntryRow({ offset: Math.round(h * 60), weather });
        _renderTimeline(_state().forecast_schedule);
    }
    /** Read the editor DOM back into a forecast, or report a validation error. */
    function _collectSchedule() {
        const mode = document.getElementById('sky-sched-mode')?.value || 'authored';
        const granularity = document.getElementById('sky-sched-granularity')?.value || 'hourly';
        const seedRaw = document.getElementById('sky-sched-seed')?.value ?? '';
        const intervalRaw = document.getElementById('sky-sched-interval')?.value ?? '1';
        const tableRaw = document.getElementById('sky-sched-table')?.value ?? '';
        let transition_table = {};
        if (tableRaw.trim()) {
            try {
                transition_table = JSON.parse(tableRaw);
            }
            catch {
                return { error: 'transition table is not valid JSON' };
            }
            if (typeof transition_table !== 'object' || transition_table === null || Array.isArray(transition_table)) {
                return { error: 'transition table must be a JSON object' };
            }
        }
        const entries = [];
        document.querySelectorAll('#sky-sched-entries .sky-sched-row').forEach((row) => {
            const get = (f) => row.querySelector(`[data-f="${f}"]`)?.value ?? '';
            const entry = { offset: parseInt(get('offset') || '0', 10) || 0 };
            for (const f of ['weather', 'wind', 'wind_direction', 'humidity', 'air', 'message']) {
                const v = get(f).trim();
                if (v)
                    entry[f] = v;
            }
            const tm = parseFloat(get('temperature_mod'));
            if (Number.isFinite(tm))
                entry.temperature_mod = tm;
            const lm = parseFloat(get('light_mod'));
            if (Number.isFinite(lm))
                entry.light_mod = lm;
            entries.push(entry);
        });
        entries.sort((a, b) => (Number(a.offset) || 0) - (Number(b.offset) || 0));
        const schedule = {
            mode, granularity, entries,
            current_state: (_state().forecast_schedule || {}).current_state || 'clear',
            transition_interval: Math.max(1, parseInt(intervalRaw, 10) || 1),
            transition_table,
            seed: seedRaw.trim() ? (parseInt(seedRaw, 10) || 0) : null,
        };
        return { schedule };
    }
    function _saveSchedule() {
        const status = document.querySelector('.sky-sched-status');
        const collected = _collectSchedule();
        if (collected.error) {
            if (status) {
                status.textContent = '✗ ' + collected.error;
                status.style.color = 'var(--red,#f85149)';
            }
            return;
        }
        fetch('/api/settings/forecast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-WV-Editor': 'sky-widget' },
            body: JSON.stringify({ schedule: collected.schedule }),
        })
            .then((r) => (r.ok ? r.json() : Promise.reject('HTTP ' + r.status)))
            .then(() => {
            if (status) {
                status.textContent = '✓ saved';
                status.style.color = 'var(--green,#3fb950)';
            }
            return worldState?.fetch?.();
        })
            .catch((err) => {
            if (status) {
                status.textContent = '✗ ' + err;
                status.style.color = 'var(--red,#f85149)';
            }
        });
    }
    // ── wiring ─────────────────────────────────────────────────────────
    // Declared before `wire` is bound so `_done` is a plain `boolean` rather
    // than the `false` literal TypeScript would otherwise infer here.
    const _wireState = { done: false };
    function wire() {
        if (_wireState.done)
            return;
        _wireState.done = true;
        function _paint() {
            const el = document.getElementById('sky-time');
            if (el && worldState?.data)
                renderTopBar(el, _state());
            if (_modalEl) {
                _updateHeadSummary();
                _renderStats();
                _updateOverrideIndicator();
                _populateWeatherSelect();
                if (!_scrubActive)
                    _sendStateToIframe();
            }
        }
        try {
            const bus = window.appEvents;
            if (bus && typeof bus.on === 'function') {
                bus.on('state:updated', _paint);
            }
            if (typeof worldState !== 'undefined' && worldState?.on) {
                worldState.on('update', _paint);
            }
        }
        catch (e) { /* event wiring optional */ }
        _repaint = _paint;
        _loadWeatherVocabulary();
        _paint();
        setTimeout(_paint, 600);
    }
    return {
        renderTopBar, effectiveWeather, nextForecastChange,
        openWorldSky, close: _closeSky, wire,
    };
})();
window.SkyScape = _SkyScape;
// Auto-wire after DOM ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.SkyScape?.wire());
}
else {
    setTimeout(() => window.SkyScape?.wire(), 200);
}
/** Minutes in one schedule period, by granularity. */
const GRANULARITY_MINUTES = {
    hourly: 1440, weekly: 10080, yearly: 525600,
};
