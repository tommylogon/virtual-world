/**
 * sky-scape.js — Engine-driven Sky Clock (task-228/229/234 UI, roadmap 3.3).
 *
 * Renders the sky state the ENGINE computes (game_time, game_day, moon_phase,
 * forecast schedule + override) in two places:
 *   - the compact top-bar widget (replaces the bare `#ui-time` clock): a single
 *     live line — time · date · moon · weather
 *   - the **World Sky panel** (modal): the animated sky STAGE from
 *     docs/design/sky-clock-mockup-v2-real-moon.html, ported to be driven by
 *     live state instead of demo chips. Controls (time skips, moon/weather
 *     displays) read the engine; authoring happens through the forecast APIs.
 *
 * Pure presentation — no state of its own; every render takes `state` from
 * `/api/state` (worldState.data) and refreshes on state:updated.
 */

window.SkyScape = (() => {
    'use strict';

    // ── Weather chips (from Time & Weather.md + forecast states) ──
    const WEATHER_CHIP = {
        'clear': '☀️', 'cloudy': '☁️', 'rainy': '🌧️', 'stormy': '⛈️',
        'foggy': '🌫️', 'windy': '💨', 'snowy': '🌨️', 'rain': '🌧️',
        'storm': '⛈️', 'snow': '🌨️',
    };
    const MOON_CHIP = {
        'new_moon': '🌑', 'crescent': '🌒', 'quarter': '🌓', 'gibbous': '🌔',
        'full_moon': '🌕', 'waning': '🌖', 'blood_moon': '🔴',
    };
    const SEASON_BY_MONTH = ['winter', 'winter', 'spring', 'spring', 'spring',
        'summer', 'summer', 'summer', 'autumn', 'autumn', 'autumn', 'winter'];
    const SEASON_STYLE = {
        spring: { sunrise: 6, sunset: 18.5, hillBack: '#79b85f', hillFront: '#5da344', crown: '#f2a9c8' },
        summer: { sunrise: 5, sunset: 20, hillBack: '#4e9a3f', hillFront: '#3c8631', crown: '#2f7d33' },
        autumn: { sunrise: 6.5, sunset: 18, hillBack: '#c08a3e', hillFront: '#a9762f', crown: '#d97a2b' },
        winter: { sunrise: 8, sunset: 16.5, hillBack: '#dfe8f2', hillFront: '#cdd9e6', crown: '#e9eef5' },
    };
    // Mirrors environment_propagation/weather_forecast tables.
    const WEATHER_LAYER = {
        clear: { clouds: 1, dim: 0, precip: null, tint: '255,255,255', o: 0.5 },
        cloudy: { clouds: 6, dim: 0.2, precip: null, tint: '208,214,226', o: 0.85 },
        rainy: { clouds: 6, dim: 0.36, precip: 'rain', drops: 70, tint: '118,128,146', o: 0.9 },
        stormy: { clouds: 7, dim: 0.5, precip: 'rain', drops: 120, lightning: true, tint: '66,72,88', o: 0.95 },
        snowy: { clouds: 5, dim: 0.28, precip: 'snow', flakes: 60, tint: '234,239,247', o: 0.85 },
        foggy: { clouds: 2, dim: 0.16, precip: null, fog: true, tint: '202,208,218', o: 0.6 },
        windy: { clouds: 4, dim: 0.1, precip: null, tint: '190,200,214', o: 0.8 },
    };
    const SKY = [
        [0, '#040613', '#0a0f26'], [4, '#070a1c', '#141a38'],
        [5.5, '#1d2547', '#7a4a63'], [6.5, '#37477f', '#f08a5d'],
        [8, '#4a86d8', '#a9d3f2'], [12, '#3f8ce6', '#bfe3fa'],
        [16, '#4a86d8', '#f3cf9a'], [18.5, '#493f7d', '#f2814f'],
        [20, '#1c2148', '#5d3a66'], [21.5, '#070a1c', '#141a38'],
        [24, '#040613', '#0a0f26'],
    ];

    let _modalEl = null;
    let _timer = null;

    // ── state helpers ──────────────────────────────────────────────────

    function _hx(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
    function _mix(a, b, t) {
        const A = _hx(a), B = _hx(b);
        return `rgb(${Math.round(A[0] + (B[0] - A[0]) * t)},${Math.round(A[1] + (B[1] - A[1]) * t)},${Math.round(A[2] + (B[2] - A[2]) * t)})`;
    }
    function _skyAt(t) {
        let i = 0;
        while (i < SKY.length - 2 && SKY[i + 1][0] < t) i++;
        const a = SKY[i], b = SKY[i + 1], span = (b[0] - a[0]) || 1;
        const k = Math.max(0, Math.min(1, (t - a[0]) / span));
        return [_mix(a[1], b[1], k), _mix(a[2], b[2], k)];
    }
    function _hour(state) {
        const t = state?.game_time || '00:00';
        const [h, m] = t.split(':').map(Number);
        return (h || 0) + (m || 0) / 60;
    }
    function _monthName(m) {
        return ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m % 13] || '';
    }
    function _season(state) {
        return SEASON_BY_MONTH[Math.max(1, Math.min(12, (state?.game_month || 1))) - 1] || 'summer';
    }

    /** Effective weather: override wins, else the forecast entry at "now". */
    function effectiveWeather(state) {
        const ov = state?.forecast_override;
        if (ov && ov.weather) return ov.weather;
        const sched = state?.forecast_schedule;
        if (sched && Array.isArray(sched.entries) && sched.entries.length) {
            const period = { hourly: 1440, weekly: 10080, yearly: 525600 }[sched.granularity] || 1440;
            const day = (state?.game_day || 1) - 1;
            const [hh, mm] = (state?.game_time || '00:00').split(':').map(Number);
            const offset = ((sched.granularity === 'hourly' ? 0 : day * 1440) + (hh || 0) * 60 + (mm || 0)) % period;
            let found = null;
            for (let i = 0; i < sched.entries.length; i++) {
                const e = sched.entries[i];
                const start = Number(e.offset || 0);
                const end = i + 1 < sched.entries.length ? Number(sched.entries[i + 1].offset || 0) : period;
                if (start <= offset && offset < end) { found = e; break; }
            }
            if (found && found.weather) return found.weather;
        }
        return 'clear';
    }

    /** Next forecast change from "now" (minutes + label), for the widget. */
    function nextForecastChange(state) {
        const sched = state?.forecast_schedule;
        if (!sched || !Array.isArray(sched.entries) || sched.entries.length < 2) return null;
        const period = { hourly: 1440, weekly: 10080, yearly: 525600 }[sched.granularity] || 1440;
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
        if (!el) return;
        const moon = state?.moon_phase || {};
        const weather = effectiveWeather(state);
        const moonIcon = MOON_CHIP[moon.name] || '🌑';
        const weatherIcon = WEATHER_CHIP[weather] || '☀️';
        const date = `${_monthName(state?.game_month)} Day ${state?.game_day || 1}`;
        const moonLabel = (moon.name || '').replace(/_/g, ' ');
        const next = nextForecastChange(state);
        let html = `🕐 ${(state?.game_time || '').slice(0, 5)}`;
        html += ` · ${date}`;
        html += ` · <span title="Moon phase (light bonus ${moon.light_bonus || 0})">${moonIcon} ${moonLabel}</span>`;
        html += ` · <span title="Weather">${weatherIcon} ${weather}</span>`;
        if (next) html += ` · <span title="Next forecast change">${next.weather ? WEATHER_CHIP[next.weather] || '⛅' : ''} ${next.label}</span>`;
        el.textContent = '';
        el.title = 'World Sky — click to open';
        el.style.cursor = 'pointer';
        const span = document.createElement('span');
        span.innerHTML = html;
        el.appendChild(span);
        if (!el._skyClickBound) {
            el._skyClickBound = true;
            el.addEventListener('click', () => SkyScape.openWorldSky());
        }
    }

    // ── World Sky modal ────────────────────────────────────────────────

    function openWorldSky() {
        if (_modalEl) { _modalEl.style.display = 'flex'; _renderStage(); return; }
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);display:flex;align-items:flex-start;justify-content:center;z-index:21000;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card,#121522);border:1px solid var(--border,#262c3f);border-radius:16px;margin-top:6vh;width:640px;max-width:94vw;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,0.5);';
        box.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--border,#262c3f);">
                <div style="font-weight:600;font-size:14px;">🌍 World Sky</div>
                <button class="btn btn-sm btn-ghost" id="sky-close" style="padding:0 6px;">✕</button>
            </div>
            <div id="sky-stage" style="height:340px;position:relative;overflow:hidden;background:#0b0d12;"></div>
            <div id="sky-readout" style="padding:8px 14px;font-size:12px;color:var(--text,#edf0ff);border-top:1px solid var(--border,#262c3f);"></div>
            <div style="padding:12px 14px;border-top:1px solid var(--border,#262c3f);display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">Clock:</span>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="15">+15m</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="60">+1h</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="1440">+1 day</button>
                <span style="flex:1;"></span>
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">Override:</span>
                <select id="sky-weather-select" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px 6px;">
                    <option value="">—</option>
                    <option>clear</option><option>cloudy</option><option>rainy</option>
                    <option>stormy</option><option>snowy</option><option>foggy</option><option>windy</option>
                </select>
                <input type="number" id="sky-duration" min="1" value="5" style="width:52px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="duration (turns)">
                <button class="btn btn-sm btn-primary" id="sky-set-override" style="font-size:11px;">Set</button>
                <button class="btn btn-sm btn-ghost" id="sky-clear-override" style="font-size:11px;">Clear</button>
            </div>
            <div style="padding:8px 14px;font-size:10.5px;color:var(--text-dim,#6b7390);border-top:1px solid var(--border,#262c3f);">Forecast schedule + GM override drive this sky. Overrides auto-revert after their duration (see <code>forecast_schedule</code> / <code>forecast_override</code> in world state).</div>
        `;
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        _modalEl = overlay;
        overlay.addEventListener('mousedown', (ev) => { if (ev.target === overlay) _closeSky(); });
        box.querySelector('#sky-close').addEventListener('click', _closeSky);
        box.querySelectorAll('.sky-skip').forEach(btn => {
            btn.addEventListener('click', () => _skipTime(Number(btn.dataset.min || 60)));
        });
        box.querySelector('#sky-set-override').addEventListener('click', _setOverride);
        box.querySelector('#sky-clear-override').addEventListener('click', _clearOverride);
        _renderStage();
        if (_timer) clearInterval(_timer);
        _timer = setInterval(() => { if (document.contains(overlay)) _renderStage(); }, 3000);
    }

    function _closeSky() {
        if (_timer) { clearInterval(_timer); _timer = null; }
        if (_modalEl) _modalEl.remove();
        _modalEl = null;
    }

    function _state() {
        return (typeof worldState !== 'undefined' && worldState.data) || {};
    }

    function _skipTime(minutes) {
        const state = _state();
        const perTick = Number(state.time_per_tick_minutes || 1);
        const extraTicks = Math.max(1, Math.round(minutes / Math.max(0.1, perTick)));
        // Advance via the same clock the engine uses: POST clock_start? No —
        // tick-based: use time_per_tick settings? The cleanest engine path is
        // a temporary override of clock_start is wrong; instead adjust the
        // task-234 set_time-style rotation by N minutes via the settings API.
        const [hh, mm] = (state.game_time || '08:00').split(':').map(Number);
        const targetMin = ((hh || 0) * 60 + (mm || 0) + minutes) % 1440;
        fetch('/api/settings/clock_start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clock_start_hour: Math.floor(targetMin / 60), clock_start_minute: targetMin % 60 })
        }).then(() => worldState?.fetch?.());
    }

    function _setOverride() {
        const sel = document.getElementById('sky-weather-select');
        const dur = document.getElementById('sky-duration');
        const data = { weather: sel.value };
        const d = parseInt(dur.value, 10);
        if (d > 0) data.duration_ticks = d;
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

    // ── stage render (engine-driven port of the v2 mockup) ─────────────

    function _renderStage() {
        const stageEl = document.getElementById('sky-stage');
        const readoutEl = document.getElementById('sky-readout');
        if (!stageEl || !_modalEl) return;
        const state = _state();
        const t = _hour(state);
        const season = _season(state);
        const ss = SEASON_STYLE[season] || SEASON_STYLE.summer;
        const weather = effectiveWeather(state);
        const w = WEATHER_LAYER[weather] || WEATHER_LAYER.clear;
        const moon = state.moon_phase || { name: 'new_moon', light_bonus: 0 };
        const moonIcon = MOON_CHIP[moon.name] || '🌑';

        const [top, bot] = _skyAt(t);
        const sr = ss.sunrise, ssSet = ss.sunset, dayLen = ssSet - sr;

        let html = `<div style="position:absolute;inset:0;background:linear-gradient(to bottom, ${top}, ${bot});transition:background 0.4s linear;"></div>`;
        // stars (fade by darkness)
        const darkness = (t >= sr && t <= ss) ? Math.max(0, .35 - Math.min((t - sr) / dayLen, (ssSet - t) / dayLen) * 1.4) : Math.min(1, .4 + (t > ssSet ? t - ssSet : sr - t) * .5);
        let stars = '';
        for (let i = 0; i < 70; i++) {
            const x = (i * 37 % 100), y = (i * 53 % 62);
            stars += `<span style="position:absolute;left:${x}%;top:${y}%;width:${1 + (i % 3) * 0.5}px;height:${1 + (i % 3) * 0.5}px;border-radius:50%;background:#fff;opacity:${(i % 5) / 10};"></span>`;
        }
        html += `<div style="position:absolute;inset:0;opacity:${darkness.toFixed(2)};transition:opacity .6s;">${stars}</div>`;

        // sun arc
        if (t >= sr && t <= ssSet) {
            const p = (t - sr) / dayLen;
            html += `<div style="position:absolute;left:${6 + p * 88}%;bottom:${10 + Math.sin(p * Math.PI) * 62}%;transform:translate(-50%,50%);width:56px;height:56px;border-radius:50%;background:radial-gradient(circle at 38% 35%,#fff8e0,#ffd24a 55%,#ff9d2e 80%);box-shadow:0 0 36px 14px rgba(255,205,95,.55);opacity:${(1 - w.dim * 0.8).toFixed(2)};"></div>`;
        }
        // moon — v2 "real moon": age-based rise so First Quarter is an afternoon moon.
        const MOON_AGE = { 'new_moon': 0, 'crescent': 0.125, 'quarter': 0.25, 'gibbous': 0.375, 'full_moon': 0.5, 'waning': 0.625, 'blood_moon': 0.5 };
        const age = MOON_AGE[moon.name] ?? 0.5;
        const moonRise = (sr + age * 24) % 24;
        const moonSet = (moonRise + dayLen) % 24;
        let sinceRise = t - moonRise;
        if (sinceRise < 0) sinceRise += 24;
        const moonUp = sinceRise <= dayLen;
        const sep = Math.min(age, 1 - age) * 360;
        const vis = Math.max(0, Math.min(1, (sep - 12) / 28));
        if (moonUp && vis > 0.02) {
            const mp = sinceRise / dayLen;
            const glow = moon.name === 'blood_moon' ? 'rgba(255,60,40,0.5)' : 'rgba(236,233,205,0.28)';
            html += `<div style="position:absolute;left:${6 + mp * 88}%;bottom:${10 + Math.sin(mp * Math.PI) * 62}%;transform:translate(-50%,50%);width:44px;height:44px;border-radius:50%;background:radial-gradient(circle at 32% 34%,rgba(90,90,80,.28) 0 7%,transparent 8%),radial-gradient(circle at 60% 62%,rgba(90,90,80,.22) 0 10%,transparent 11%),${moon.name === 'blood_moon' ? '#c05046' : '#ece9d8'};box-shadow:0 0 24px 7px ${glow};opacity:${(vis * (t > sr && t < ssSet ? 0.92 : 1)).toFixed(2)};"></div>`;
        }

        // clouds
        let clouds = '';
        for (let i = 0; i < (w.clouds || 0); i++) {
            const s = 0.7 + ((i * 7) % 10) / 10;
            clouds += `<div style="position:absolute;left:${-20 + (i * 29) % 100}%;top:${5 + (i * 17) % 30}%;width:${95 * s}px;height:${36 * s}px;filter:blur(${5 + (i % 3) * 2}px);background:radial-gradient(closest-side at 35% 60%,rgba(${w.tint},${w.o}),rgba(${w.tint},0) 75%),radial-gradient(closest-side at 70% 45%,rgba(${w.tint},${w.o * 0.9}),rgba(${w.tint},0) 72%);"></div>`;
        }
        html += `<div style="position:absolute;inset:0;pointer-events:none;">${clouds}</div>`;

        // precipitation / fog
        if (w.precip === 'rain') {
            let drops = '';
            for (let i = 0; i < 40; i++) {
                drops += `<span style="position:absolute;top:-30px;left:${(i * 23) % 100}%;width:1.5px;height:16px;background:linear-gradient(rgba(170,200,255,0),rgba(170,200,255,.75));opacity:${.35 + (i % 5) / 10};"></span>`;
            }
            html += `<div style="position:absolute;inset:0;pointer-events:none;overflow:hidden;">${drops}</div>`;
        } else if (w.precip === 'snow') {
            let flakes = '';
            for (let i = 0; i < 30; i++) {
                flakes += `<span style="position:absolute;top:-14px;left:${(i * 31) % 100}%;width:${4 + (i % 4)}px;height:${4 + (i % 4)}px;border-radius:50%;background:rgba(255,255,255,.92);opacity:${.5 + (i % 3) / 10};"></span>`;
            }
            html += `<div style="position:absolute;inset:0;pointer-events:none;overflow:hidden;">${flakes}</div>`;
        }
        if (w.fog) html += `<div style="position:absolute;left:-25%;width:150%;height:24%;top:44%;filter:blur(15px);background:linear-gradient(to bottom,transparent,rgba(214,220,231,.55),transparent);"></div>`;

        // ground
        html += `<div style="position:absolute;left:0;right:0;bottom:0;height:24%;background:${ss.hillFront};">
            <div style="position:absolute;width:150%;height:150%;left:-40%;bottom:-78%;border-radius:50% 50% 0 0;background:${ss.hillBack};"></div>
        </div>`;
        html += `<div style="position:absolute;left:12%;bottom:24%;">${'' /* tree icons by season */}</div>`;

        // dim + readout
        html += `<div style="position:absolute;inset:0;background:#0b1020;opacity:${w.dim};pointer-events:none;"></div>`;
        const [hh, mm] = (state.game_time || '00:00').split(':');
        const moonLabel = (moon.name || 'new_moon').replace(/_/g, ' ');
        const next = nextForecastChange(state);
        html += `<div style="position:absolute;top:10px;left:10px;color:#fff;background:rgba(8,10,24,.42);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:8px 12px;">
            <div style="font-size:22px;font-weight:800;">${hh}:${mm}</div>
            <div style="font-size:11px;opacity:.92;">Day ${state.game_day || 1} · ${_monthName(state.game_month || 1)} ${state.game_year || 1} · ${season}</div>
        </div>`;
        stageEl.innerHTML = html;

        if (readoutEl) {
            const dayLenTxt = `${Math.floor(dayLen)}h ${Math.round((dayLen % 1) * 60)}m`;
            readoutEl.innerHTML = `<strong>${weather}</strong> weather · moon <strong>${moonIcon} ${moonLabel}</strong> (+${moon.light_bonus || 0} night light): ${moon.name === 'blood_moon' ? 'the sky runs red' : 'rises ' + String(Math.floor(moonRise)).padStart(2, '0') + ':' + String(Math.round((moonRise % 1) * 60)).padStart(2, '0')} · ☀ ${dayLenTxt} daylight${next ? ` · forecast change ${next.label}` : ''}${state.forecast_override ? ' · GM override ACTIVE' : ''}`;
        }
    }

    // ── wiring ─────────────────────────────────────────────────────────

    function wire() {
        if (wire._done) return;
        wire._done = true;
        function _paint() {
            const el = document.getElementById('ui-time');
            if (el && worldState?.data) renderTopBar(el, _state());
            if (_modalEl) _renderStage();
        }
        try {
            if (window.appEvents && typeof window.appEvents.on === 'function') {
                window.appEvents.on('state:updated', _paint);
            }
            if (typeof worldState !== 'undefined' && worldState?.on) {
                worldState.on('update', _paint);
            }
        } catch (e) { /* event wiring optional */ }
        // Paint immediately if data is already available, or retry shortly.
        _paint();
        setTimeout(_paint, 600);
    }

    return {
        renderTopBar, effectiveWeather, nextForecastChange,
        openWorldSky, close: _closeSky, wire,
    };
})();

// Auto-wire after DOM ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.SkyScape?.wire());
} else {
    setTimeout(() => window.SkyScape?.wire(), 200);
}
