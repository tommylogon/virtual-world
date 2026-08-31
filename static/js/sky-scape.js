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

    let _modalEl = null;
    let _timer = null;

    // ── state helpers ──────────────────────────────────────────────────

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
        if (_modalEl) { _modalEl.style.display = 'flex'; _sendStateToIframe(); return; }
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);display:flex;align-items:flex-start;justify-content:center;z-index:21000;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card,#121522);border:1px solid var(--border,#262c3f);border-radius:16px;margin-top:6vh;width:min(960px,94vw);max-width:94vw;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,0.5);';
        box.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:11px 18px;border-bottom:1px solid var(--border,#262c3f);">
                <div style="font-weight:700;font-size:13px;letter-spacing:.16em;">🌍 ATMOSPHERE <span style="font-size:10px;color:var(--text-dim,#6b7390);margin-left:2px;">time · season · weather · moon</span></div>
                <button class="btn btn-sm btn-ghost" id="sky-close" style="padding:0 6px;">✕</button>
            </div>
            <iframe id="sky-atmosphere-frame" src="/static/sky-atmosphere.html" style="width:100%;border:none;display:block;background:#000;min-height:520px;"></iframe>
            <div style="padding:8px 14px;border-top:1px solid var(--border,#262c3f);display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">⏰ Time:</span>
                <input type="time" id="sky-time-input" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;width:80px;" title="Exact time (HH:MM)">
                <button class="btn btn-sm btn-ghost sky-set-time" style="font-size:10px;padding:3px 8px;">Set</button>
                <span style="border-left:1px solid var(--border,#262c3f);height:22px;width:0;"></span>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="-15">-15m</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="-60">-1h</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="15">+15m</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="60">+1h</button>
                <button class="btn btn-sm btn-ghost sky-skip" data-min="1440">+1d</button>
                <span style="border-left:1px solid var(--border,#262c3f);height:22px;width:0;"></span>
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">📅 Date:</span>
                <input type="number" id="sky-date-day" min="1" max="30" style="width:44px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="Day">
                <span style="color:var(--text-dim);font-size:11px;">/</span>
                <input type="number" id="sky-date-month" min="1" max="12" style="width:44px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="Month">
                <span style="color:var(--text-dim);font-size:11px;">/</span>
                <input type="number" id="sky-date-year" min="1" style="width:56px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="Year">
                <button class="btn btn-sm btn-ghost sky-set-date" style="font-size:10px;padding:3px 8px;">Set</button>
            </div>
            <div style="padding:8px 14px;border-top:1px solid var(--border,#262c3f);display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
                <span style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-dim,#6b7390);font-weight:700;">🌤 Override:</span>
                <select id="sky-override-weather" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;">
                    <option value="">— weather</option>
                    <option value="clear">☀️ clear</option><option value="cloudy">☁️ cloudy</option><option value="rainy">🌧️ rainy</option>
                    <option value="stormy">⛈️ stormy</option><option value="snowy">🌨️ snowy</option><option value="foggy">🌫️ foggy</option><option value="windy">💨 windy</option>
                </select>
                <select id="sky-override-wind" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;">
                    <option value="">— wind</option>
                    <option value="none">none</option><option value="breeze">breeze</option><option value="wind">wind</option>
                    <option value="gale">gale</option><option value="storm">storm</option><option value="hurricane">hurricane</option>
                </select>
                <select id="sky-override-humidity" style="font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;">
                    <option value="">— humidity</option>
                    <option value="dry">dry</option><option value="humid">humid</option><option value="wet">wet</option><option value="flooding">flooding</option>
                </select>
                <input type="number" id="sky-override-duration" min="1" value="5" style="width:52px;font-size:11px;background:var(--bg-input,#0d1018);color:var(--text,#edf0ff);border:1px solid var(--border,#262c3f);border-radius:6px;padding:4px;" title="duration (turns)">
                <button class="btn btn-sm btn-primary" id="sky-override-set" style="font-size:11px;">Set</button>
                <button class="btn btn-sm btn-ghost" id="sky-override-clear" style="font-size:11px;">Clear</button>
                <span class="sky-override-active" style="display:none;font-size:10px;color:var(--orange,#f0883e);margin-left:4px;">● override active</span>
            </div>
            <div style="padding:8px 14px;font-size:10.5px;color:var(--text-dim,#6b7390);border-top:1px solid var(--border,#262c3f);">Clock: <code id="sky-clock-readout"></code> · Moon: <code id="sky-moon-readout"></code> · Forecast: <code id="sky-forecast-readout"></code></div>
        `;
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        _modalEl = overlay;
        overlay.addEventListener('mousedown', (ev) => { if (ev.target === overlay) _closeSky(); });
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
        // Wire iframe load → feed state
        const iframe = document.getElementById('sky-atmosphere-frame');
        iframe.addEventListener('load', () => _sendStateToIframe());
        // Listen for 'sky:ready' from the iframe
        window.addEventListener('message', (ev) => {
            if (ev.data?.type === 'sky:ready') _sendStateToIframe();
        });
        _populateControls();
        _sendStateToIframe();
        // Poll state updates to the iframe
        if (_timer) clearInterval(_timer);
        _timer = setInterval(() => {
            if (document.contains(overlay)) _sendStateToIframe();
        }, 3000);
    }

    function _sendStateToIframe() {
        const iframe = document.getElementById('sky-atmosphere-frame');
        if (!iframe || !iframe.contentWindow) return;
        const state = _state();
        const t = (state?.game_time || '09:40').split(':').map(Number);
        const hour = (t[0] || 0) + (t[1] || 0) / 60;
        const m = Math.max(1, Math.min(12, state?.game_month || 1));
        const seasonMap = ['winter', 'winter', 'spring', 'spring', 'spring', 'summer', 'summer', 'summer', 'autumn', 'autumn', 'autumn', 'winter'];
        const season = seasonMap[m - 1] || 'winter';
        const weather = effectiveWeather(state);
        const weatherMap = { clear: 'clear', cloudy: 'overcast', rainy: 'rain', stormy: 'storm', snowy: 'snow', foggy: 'fog', windy: 'partly' };
        const moonIdx = { new_moon: 0, crescent: 1, quarter: 2, gibbous: 3, full_moon: 4, waning: 5, blood_moon: 4 };
        const moon = state?.moon_phase || {};
        const phase = moonIdx[moon.name] !== undefined ? moonIdx[moon.name] : 0;
        iframe.contentWindow.postMessage({
            type: 'engine:sky-state',
            t: hour,
            season: season,
            weather: weatherMap[weather] || 'clear',
            phase: phase,
            engineTime: (state?.game_time || '').slice(0, 5),
            engineDay: state?.game_day || 1,
        }, '*');
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
        if (!input || !input.value) return;
        const [h, m] = input.value.split(':').map(Number);
        if (isNaN(h) || isNaN(m)) return;
        fetch('/api/settings/clock_start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clock_start_hour: h, clock_start_minute: m })
        }).then(() => worldState?.fetch?.());
    }

    function _setExactDate() {
        const d = parseInt(document.getElementById('sky-date-day')?.value);
        const m = parseInt(document.getElementById('sky-date-month')?.value);
        const y = parseInt(document.getElementById('sky-date-year')?.value);
        if (isNaN(d) && isNaN(m) && isNaN(y)) return;
        const body = {};
        if (!isNaN(d)) body.day = d;
        if (!isNaN(m)) body.month = m;
        if (!isNaN(y)) body.year = y;
        fetch('/api/settings/date', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(() => worldState?.fetch?.());
    }

    function _setOverride() {
        const weather = document.getElementById('sky-override-weather')?.value || '';
        const wind = document.getElementById('sky-override-wind')?.value || '';
        const humidity = document.getElementById('sky-override-humidity')?.value || '';
        const dur = parseInt(document.getElementById('sky-override-duration')?.value || '5');
        const data = {};
        if (weather) data.weather = weather;
        if (wind) data.wind = wind;
        if (humidity) data.humidity = humidity;
        if (dur > 0) data.duration_ticks = dur;
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
        if (!state) return;
        const timeInput = document.getElementById('sky-time-input');
        const dayInput = document.getElementById('sky-date-day');
        const monthInput = document.getElementById('sky-date-month');
        const yearInput = document.getElementById('sky-date-year');
        const clockReadout = document.getElementById('sky-clock-readout');
        const moonReadout = document.getElementById('sky-moon-readout');
        const forecastReadout = document.getElementById('sky-forecast-readout');
        const overrideActive = document.querySelector('.sky-override-active');
        if (timeInput) {
            const t = (state.game_time || '09:40').slice(0, 5);
            timeInput.value = t;
        }
        if (dayInput) dayInput.value = state.game_day || 1;
        if (monthInput) monthInput.value = state.game_month || 1;
        if (yearInput) yearInput.value = state.game_year || 1;
        if (clockReadout) clockReadout.textContent = `${state.game_time || '?'} · Day ${state.game_day || 1}, ${_monthName(state.game_month || 1)} ${state.game_year || 1}`;
        if (moonReadout) {
            const moon = state.moon_phase || {};
            const icon = MOON_CHIP[moon.name] || '🌑';
            const label = (moon.name || '').replace(/_/g, ' ');
            const bonus = moon.light_bonus || 0;
            const next = nextForecastChange(state);
            moonReadout.textContent = `${icon} ${label} (+${bonus} night light) · ${next ? `next: ${next.weather || 'change'} ${next.label}` : 'no forecast change'}`;
        }
        if (forecastReadout) {
            const sched = state.forecast_schedule || {};
            const entries = (sched.entries || []).length;
            const ov = state.forecast_override;
            forecastReadout.textContent = `${entries} entries (${sched.granularity || 'hourly'})${ov ? ' · GM override ACTIVE' : ''}`;
        }
        if (overrideActive) {
            const ov = state.forecast_override;
            overrideActive.style.display = ov ? 'inline' : 'none';
        }
    }

    // ── wiring ─────────────────────────────────────────────────────────

    function wire() {
        if (wire._done) return;
        wire._done = true;
        function _paint() {
            const el = document.getElementById('sky-time');
            if (el && worldState?.data) renderTopBar(el, _state());
            if (_modalEl) _sendStateToIframe();
        }
        try {
            if (window.appEvents && typeof window.appEvents.on === 'function') {
                window.appEvents.on('state:updated', _paint);
            }
            if (typeof worldState !== 'undefined' && worldState?.on) {
                worldState.on('update', _paint);
            }
        } catch (e) { /* event wiring optional */ }
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
