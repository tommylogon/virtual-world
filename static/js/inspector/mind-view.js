"use strict";
/**
 * InspectorMindView - the Memory Mind dashboard (task-691 stage 4).
 *
 * A full-surface view of one character's memory dynamics, the wired version of
 * docs/design/memory-mockup.html: timeline ribbon, category filters, dynamics
 * badges, a memory detail pane with connections (contradicts / derived-from /
 * same-entity), per-person derived profiles from the /memories/people endpoint
 * (engine/derive.py - the same numbers the prompt sees), and an accessibility
 * panel showing current activation (what decay is working on right now).
 *
 * Reads ONLY existing state: worldState memories + the people endpoint. Every
 * number shown is a field the backend wrote or a value derive.py computes -
 * no decorative data.
 *
 * @module inspector/mind-view - the character's memory mind (dashboard)
 * @contributes InspectorMindView.open(charName): full-surface memory dashboard
 * @powers Node inspectors, Memory - inspecting and correcting what a character remembers
 * @relates complements inspector/memory-view (the editor); reads /api/players/<n>/memories/people
 * @docs docs/virtualWorld/AI & Narration/Memory Dynamics.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
/** Category of a memory, derived the same way memory-view and the recall
 *  block derive it for pre-dynamics entries. */
function _catOf(m) {
    if (m.category)
        return String(m.category);
    if (String(m.type || '') === 'reflection')
        return 'belief';
    const tags = Array.isArray(m.tags) ? m.tags.map((t) => String(t).toLowerCase()) : [];
    if (tags.some((t) => t.startsWith('rel:')))
        return 'social';
    return 'episodic';
}
const CAT_COLORS = {
    episodic: '#58a6ff', semantic: '#39c5cf', belief: '#bc8cff',
    social: '#f778ba', procedural: '#d29922'
};
const InspectorMindView = (() => {
    'use strict';
    let _state = null;
    let _container = null;
    const esc = (value) => {
        const s = String(value ?? '');
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    };
    const act = (m) => (typeof m.activation === 'number' ? m.activation : 1);
    const conf = (m) => (typeof m.confidence === 'number' ? m.confidence : (String(m.source) === 'manual' || String(m.source) === 'preconceived' ? 1 : 0.7));
    function _memories() {
        if (!_state)
            return [];
        return worldState.players?.[_state.charName]?.memories || [];
    }
    function _visible(memories) {
        if (!_state)
            return [];
        const f = _state.filter;
        const q = _state.query.toLowerCase().trim();
        return memories.filter((m) => {
            if (f === 'episodic' && _catOf(m) !== 'episodic')
                return false;
            if (f === 'beliefs' && !['belief', 'semantic'].includes(_catOf(m)))
                return false;
            if (f === 'social' && _catOf(m) !== 'social')
                return false;
            if (f === 'procedural' && _catOf(m) !== 'procedural')
                return false;
            if (f === 'contradicted' && !(Array.isArray(m.contradicts) && m.contradicts.length))
                return false;
            if (f === 'faded' && !(act(m) < 0.5))
                return false;
            if (f.startsWith('person:')) {
                const who = f.slice(7).toLowerCase();
                const tags = (Array.isArray(m.tags) ? m.tags : []).map((t) => String(t).toLowerCase());
                if (!tags.includes('rel:' + who))
                    return false;
            }
            if (q && !String(m.text || '').toLowerCase().includes(q))
                return false;
            return true;
        });
    }
    // ── pieces ───────────────────────────────────────────────────────────
    function _statsHtml(memories) {
        const n = (pred) => memories.filter(pred).length;
        const epis = n((m) => _catOf(m) === 'episodic');
        const beliefs = n((m) => ['belief', 'semantic'].includes(_catOf(m)));
        const social = n((m) => _catOf(m) === 'social');
        const proc = n((m) => _catOf(m) === 'procedural');
        const contra = n((m) => Array.isArray(m.contradicts) && m.contradicts.length);
        const faded = n((m) => act(m) < 0.5);
        const reinf = memories.reduce((a, m) => a + (Number(m.reinforcements) || 0), 0);
        const avgConf = memories.length ? Math.round(memories.reduce((a, m) => a + conf(m), 0) / memories.length * 100) : 100;
        const chip = (num, label, color) => `<div class="mstat" style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:4px 10px;text-align:center;min-width:64px;">
                <div style="font-size:14px;font-weight:600;${color ? `color:${color};` : ''}">${num}</div>
                <div style="font-size:8.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;">${label}</div></div>`;
        return [
            chip(memories.length, 'memories'),
            chip(epis, 'episodic', CAT_COLORS.episodic),
            chip(beliefs, 'beliefs', CAT_COLORS.belief),
            chip(social, 'social', CAT_COLORS.social),
            chip(proc, 'procedural', CAT_COLORS.procedural),
            chip(contra, 'contradicted', contra ? '#e05555' : undefined),
            chip(faded, 'faded', faded ? '#d29922' : undefined),
            chip(`↻ ${reinf}`, 'reinforcements', '#4caf50'),
            chip(`${avgConf}%`, 'avg conf'),
        ].join('');
    }
    function _timelineHtml(memories) {
        const ticks = memories.map((m) => Number(m.tick) || 0);
        const min = Math.min(0, ...ticks);
        const max = Math.max(1, ...ticks);
        const W = 760, H = 64, PAD = 18;
        const span = Math.max(1, max - min);
        const dots = memories.map((m) => {
            const x = PAD + ((Number(m.tick) || 0) - min) / span * (W - 2 * PAD);
            const imp = Number(m.importance) || 5;
            const r = 2.5 + imp * 0.35;
            const color = CAT_COLORS[_catOf(m)] || '#8b949e';
            const ring = Array.isArray(m.contradicts) && m.contradicts.length
                ? `<circle cx="${x.toFixed(1)}" cy="${H / 2}" r="${(r + 2.5).toFixed(1)}" fill="none" stroke="#e05555" stroke-opacity="0.55" stroke-width="1.5"/>` : '';
            const sel = _state && _state.selectedId === m.id
                ? `<circle cx="${x.toFixed(1)}" cy="${H / 2}" r="${(r + 4).toFixed(1)}" fill="none" stroke="#58a6ff" stroke-width="1.2"/>` : '';
            return `${ring}${sel}<circle class="mind-dot" data-id="${esc(m.id)}" cx="${x.toFixed(1)}" cy="${H / 2}" r="${r.toFixed(1)}" fill="${color}" style="cursor:pointer;"><title>${esc(`tick ${m.tick} · imp ${imp} · ${_catOf(m)}`)}\n${esc(String(m.text || '').slice(0, 120))}</title></circle>`;
        }).join('');
        const marks = [0, 0.25, 0.5, 0.75, 1].map(p => `<text x="${(PAD + p * (W - 2 * PAD)).toFixed(0)}" y="${H - 6}" fill="#6e7681" font-size="8" text-anchor="middle" font-family="monospace">${esc(Math.round(min + p * span))}</text>`).join('');
        return `<svg width="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;">
            <line x1="${PAD}" y1="${H / 2}" x2="${W - PAD}" y2="${H / 2}" stroke="#30363d" stroke-width="2"/>${marks}${dots}</svg>
            <div style="font-size:9px;color:var(--text-muted);margin-top:3px;">position = tick · size = importance · red ring = contradicted · click a dot to select</div>`;
    }
    function _badge(label, color, title) {
        return `<span style="font-size:9px;padding:1px 6px;border-radius:8px;border:1px solid ${color};color:${color};${title ? '' : ''}" ${title ? `title="${esc(title)}"` : ''}>${esc(label)}</span>`;
    }
    function _cardHtml(m) {
        const cat = _catOf(m);
        const imp = Number(m.importance) || 5;
        const impColor = imp >= 8 ? '#e05555' : imp >= 6 ? '#e0a33c' : imp >= 4 ? '#4caf50' : '#888';
        const selected = _state && _state.selectedId === m.id;
        const faded = act(m) < 0.5;
        const badges = [
            _badge(cat, CAT_COLORS[cat] || '#8b949e'),
        ];
        if (typeof m.confidence === 'number' || String(m.source) === 'manual') {
            const c = Math.round(conf(m) * 100);
            badges.push(_badge(`conf ${c}%`, c < 50 ? '#d29922' : '#8b949e', 'how sure the character is'));
        }
        const reinf = Number(m.reinforcements) || 0;
        if (reinf > 0)
            badges.push(_badge(`↻ ×${reinf}`, '#4caf50', 'reinforced by recall or re-encounter'));
        const contra = Array.isArray(m.contradicts) ? m.contradicts.length : 0;
        if (contra > 0)
            badges.push(_badge(`⚡ ${contra}`, '#e05555', `conflicts with ${contra} other memor${contra === 1 ? 'y' : 'ies'}`));
        if (Number(m.reflection_depth) > 0)
            badges.push(_badge(`depth ${m.reflection_depth}`, '#bc8cff', `derived memory (from ${Array.isArray(m.source_memory_ids) ? m.source_memory_ids.length : '?'} source memories)`));
        if (String(m.source) === 'manual')
            badges.push(_badge('SEED', '#39c5cf'));
        return `<div class="mind-card" data-id="${esc(m.id)}" style="background:var(--bg-card);border:1px solid ${selected ? '#1f6feb' : 'var(--border)'};border-left:3px solid ${impColor};border-radius:6px;padding:7px 9px;margin-bottom:6px;font-size:11px;cursor:pointer;${faded ? 'opacity:0.55;' : ''}">
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                <span style="color:var(--text-dim);font-size:10px;font-family:monospace;">[${esc(m.tick ?? 0)}]</span>
                ${badges.join('')}
                <span style="margin-left:auto;font-size:10px;color:${impColor};font-weight:600;">⭐ ${imp}</span>
            </div>
            <div style="margin-top:3px;line-height:1.4;">${esc(m.text || '')}</div>
        </div>`;
    }
    function _bar(label, value, max, color, center = false) {
        const pct = Math.max(0, Math.min(1, Math.abs(value) / max)) * 100;
        const fill = center
            ? `<div style="height:100%;width:${(pct / 2).toFixed(1)}%;background:${color};margin-left:50%;"></div>`
            : `<div style="height:100%;width:${pct.toFixed(1)}%;background:${color};"></div>`;
        return `<div style="display:flex;align-items:center;gap:6px;font-size:10.5px;margin:3px 0;">
            <span style="width:62px;color:var(--text-dim);">${esc(label)}</span>
            <div style="flex:1;height:7px;background:var(--bg-input);border-radius:3px;overflow:hidden;position:relative;${center ? '' : ''}">${center ? '<div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border);"></div>' : ''}${fill}</div>
            <span style="width:34px;text-align:right;font-family:monospace;font-size:10px;color:var(--text-dim);">${esc(Math.round(value * 100) / 100)}</span></div>`;
    }
    function _detailHtml(m, all) {
        if (!m)
            return `<div style="font-size:11px;color:var(--text-muted);">Select a memory to see its dynamics and connections.</div>`;
        const cat = _catOf(m);
        const emoList = Array.isArray(m.memory_emotions) && m.memory_emotions.length
            ? m.memory_emotions
            : (m.emotion && m.emotion.label ? [m.emotion] : []);
        const byId = (id) => all.find((x) => x.id === id);
        const contraRows = (Array.isArray(m.contradicts) ? m.contradicts : []).map((id) => {
            const other = byId(id);
            return `<div class="mind-conn" data-id="${esc(id)}" style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid var(--border-light);font-size:10.5px;cursor:pointer;">
                <span style="font-family:monospace;font-size:9px;color:var(--text-muted);min-width:46px;">${esc(other?.tick ?? '?')}</span>
                <span style="color:#e05555;">contradicts</span>
                <span style="color:var(--text-dim);flex:1;">${esc(other ? String(other.text).slice(0, 70) : id)}</span></div>`;
        }).join('');
        const derivedRows = (Array.isArray(m.source_memory_ids) ? m.source_memory_ids : []).map((id) => {
            const other = byId(id);
            return `<div class="mind-conn" data-id="${esc(id)}" style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid var(--border-light);font-size:10.5px;cursor:pointer;">
                <span style="font-family:monospace;font-size:9px;color:var(--text-muted);min-width:46px;">${esc(other?.tick ?? '?')}</span>
                <span style="color:#bc8cff;">derived from</span>
                <span style="color:var(--text-dim);flex:1;">${esc(other ? String(other.text).slice(0, 70) : id)}</span></div>`;
        }).join('');
        const entityIds = (Array.isArray(m.entity_ids) ? m.entity_ids : []).map((e) => String(e));
        const siblings = entityIds.length
            ? all.filter((x) => x.id !== m.id && (x.entity_ids || []).some((e) => entityIds.includes(String(e)))).slice(0, 5)
            : [];
        const sibRows = siblings.map((other) => `<div class="mind-conn" data-id="${esc(other.id)}" style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid var(--border-light);font-size:10.5px;cursor:pointer;">
                <span style="font-family:monospace;font-size:9px;color:var(--text-muted);min-width:46px;">${esc(other.tick ?? '?')}</span>
                <span style="color:var(--text-muted);">same entity</span>
                <span style="color:var(--text-dim);flex:1;">${esc(String(other.text || '').slice(0, 70))}</span></div>`).join('');
        const relTags = (Array.isArray(m.tags) ? m.tags : []).filter((t) => String(t).toLowerCase().startsWith('rel:'));
        const eName = _state ? _state.escName : '';
        const mid = esc(m.id);
        const isSuppressed = Array.isArray(m.suppressions) && m.suppressions.length > 0;
        const editBtn = `<div style="display:flex;gap:4px;flex-wrap:wrap;">
            <button class="btn btn-sm" style="font-size:10px;" onclick="window.InspectorMemory&&window.InspectorMemory.editMemory('${eName}','${mid}')">✏️ Edit</button>
            ${isSuppressed
            ? `<button class="btn btn-sm" style="font-size:10px;color:#4caf50;" onclick="window.InspectorMemory&&window.InspectorMemory.unblockMemory('${eName}','${mid}')" title="Unblock - make recallable again">🔓 Unblock</button>`
            : `<button class="btn btn-sm" style="font-size:10px;color:#e0a33c;" onclick="window.InspectorMemory&&window.InspectorMemory.suppressMemory('${eName}','${mid}')" title="Suppress - hold out of recall">🚫 Suppress</button>`}
            <button class="btn btn-sm btn-red" style="font-size:10px;" onclick="window.InspectorMemory&&window.InspectorMemory.deleteMemory('${eName}','${mid}')" title="Delete this memory">🗑 Delete</button>
        </div>`;
        return `<div style="background:var(--bg-card);border:1px solid #1f6feb;border-radius:6px;padding:10px;">
            <div style="font-size:13px;font-weight:600;line-height:1.4;">${esc(m.text || '')}</div>
            <div style="font-size:10.5px;color:var(--text-dim);margin:4px 0 8px;">${esc(m.type || '')} · ${_badge(cat, CAT_COLORS[cat] || '#8b949e')} · tick ${esc(m.tick ?? 0)} · importance ${esc(m.importance ?? 5)} · source ${esc(m.source || 'auto')}</div>
            <div style="background:var(--bg-inset);border:1px solid var(--border);border-radius:5px;padding:8px 10px;margin-bottom:8px;">
                <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Dynamics</div>
                ${_bar('activation', act(m), 1, '#4caf50')}
                ${_bar('confidence', conf(m), 1, '#58a6ff')}
                <div style="display:flex;justify-content:space-between;font-size:10.5px;padding:2px 0;">
                    <span style="color:var(--text-dim);">reinforcements</span><span style="font-family:monospace;">${esc(Number(m.reinforcements) || 0)} ↻</span></div>
                <div style="display:flex;justify-content:space-between;font-size:10.5px;padding:2px 0;">
                    <span style="color:var(--text-dim);">last recalled</span><span style="font-family:monospace;">${m.last_recalled_tick != null ? esc(m.last_recalled_tick) : 'never'}</span></div>
                ${Number(m.reflection_depth) > 0 ? `<div style="display:flex;justify-content:space-between;font-size:10.5px;padding:2px 0;">
                    <span style="color:var(--text-dim);">reflection depth</span><span style="font-family:monospace;">${esc(m.reflection_depth)}</span></div>` : ''}
            </div>
            ${emoList.length ? `<div style="background:var(--bg-inset);border:1px solid var(--border);border-radius:5px;padding:8px 10px;margin-bottom:8px;">
                <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Emotional encoding</div>
                ${emoList.map((e) => _bar(String(e.label || ''), (Number(e.intensity) || 0) / 10, 1, '#e0a33c')).join('')}
            </div>` : ''}
            ${(contraRows || derivedRows || sibRows) ? `<div style="background:var(--bg-inset);border:1px solid var(--border);border-radius:5px;padding:8px 10px;margin-bottom:8px;">
                <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Connections</div>
                ${contraRows}${derivedRows}${sibRows}
            </div>` : ''}
            ${relTags.length ? `<div style="font-size:10px;color:var(--f788ba, #f778ba);margin-bottom:8px;">${relTags.map((t) => _badge(String(t), '#f778ba')).join(' ')}</div>` : ''}
            <div style="background:var(--bg-inset);border:1px solid var(--border);border-radius:5px;padding:8px 10px;margin-bottom:8px;">
                <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Feelings - edit</div>
                <div id="mind-mem-emotions"></div>
                <button class="btn btn-sm mind-mem-emo-save" style="font-size:10px;margin-top:6px;">💾 Save feelings</button>
            </div>
            ${editBtn}
        </div>`;
    }
    function _accessibilityHtml(all) {
        if (!all.length)
            return '';
        const sorted = [...all].sort((a, b) => act(a) - act(b)).slice(0, 7);
        const faded = all.filter((m) => act(m) < 0.5).length;
        const row = (m) => {
            const a = act(m);
            const color = a < 0.5 ? '#d29922' : '#4caf50';
            return `<div class="mind-conn" data-id="${esc(m.id)}" style="cursor:pointer;margin:5px 0;">
                <div style="display:flex;justify-content:space-between;gap:8px;font-size:10.5px;color:var(--text-dim);">
                    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(String(m.text || '').slice(0, 46))}</span>
                    <span style="font-family:monospace;font-size:10px;">${a.toFixed(2)}</span></div>
                <div style="height:6px;background:var(--bg-input);border-radius:3px;overflow:hidden;margin-top:2px;">
                    <div style="height:100%;width:${(a * 100).toFixed(1)}%;background:${color};"></div></div>
            </div>`;
        };
        return `<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:10px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;display:flex;justify-content:space-between;">
                <span>Accessibility now (activation)</span><span style="text-transform:none;">${faded} below 0.5</span></div>
            ${sorted.map(row).join('')}
            <div style="font-size:9px;color:var(--text-muted);margin-top:4px;line-height:1.5;">Recall (↻) raises activation; decay lowers it every tick at a rate each memory resists differently. Every memory is kept for life - decay lowers how likely it is to be recalled, it never forgets one.</div>
        </div>`;
    }
    function _goals() {
        if (!_state)
            return [];
        return worldState.players?.[_state.charName]?.goals || [];
    }
    function _goalStatusColor(status) {
        switch (status) {
            case 'active': return '#58a6ff';
            case 'reached': return '#4caf50';
            case 'blocked': return '#e05555';
            case 'dropped': return '#6e7681';
            default: return '#d29922'; // proposed
        }
    }
    function _goalRowHtml(g) {
        const inputStyle = 'font-size:10.5px;background:var(--bg-input);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:2px 6px;';
        const statuses = ['proposed', 'active', 'reached', 'blocked', 'dropped'];
        const color = _goalStatusColor(String(g.status || 'proposed'));
        const val = (s) => esc(String(s ?? ''));
        const blocked = Array.isArray(g.blocked_by) && g.blocked_by.length
            ? `<div style="font-size:9.5px;color:#e05555;margin-top:3px;">⛔ blocked by ${esc(g.blocked_by.join(', '))}</div>` : '';
        return `<div class="mind-goal" style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid ${color};border-radius:6px;padding:7px 9px;margin-bottom:7px;">
            <div style="display:flex;gap:6px;align-items:center;">
                <input class="mind-goal-what" value="${val(g.what)}" placeholder="what they want" style="${inputStyle}flex:1;">
                <select class="mind-goal-status" style="${inputStyle}font-size:10px;">${statuses.map(s => `<option value="${s}"${s === (g.status || 'proposed') ? ' selected' : ''}>${s}</option>`).join('')}</select>
                <span class="mind-goal-del" title="remove goal" style="cursor:pointer;color:var(--red);font-size:12px;padding:2px;">✕</span>
            </div>
            <input class="mind-goal-motivation" value="${val(g.motivation)}" placeholder="motivation (why at all)" style="${inputStyle}width:100%;margin-top:4px;">
            <input class="mind-goal-intention" value="${val(g.intention)}" placeholder="intention (why this one)" style="${inputStyle}width:100%;margin-top:4px;">
            <input class="mind-goal-blocks" value="${val((g.blocks || []).join(', '))}" placeholder="blocked by (goal id or item:node_id, comma-separated)" style="${inputStyle}width:100%;margin-top:4px;">
            ${blocked}
        </div>`;
    }
    function _goalsHtml() {
        const goals = _goals();
        const body = goals.length
            ? goals.map((g) => _goalRowHtml(g)).join('')
            : `<div class="mind-goal-empty" style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">no goals - driven only by needs right now.</div>`;
        return `${body}<button class="btn btn-sm mind-add-goal" style="font-size:10px;">➕ Add goal</button>`;
    }
    function _collectGoals() {
        const box = _container?.querySelector('#mind-goals');
        if (!box)
            return [];
        return Array.from(box.querySelectorAll('.mind-goal')).map((row) => ({
            what: (row.querySelector('.mind-goal-what')?.value || '').trim(),
            status: row.querySelector('.mind-goal-status')?.value || 'proposed',
            motivation: (row.querySelector('.mind-goal-motivation')?.value || '').trim(),
            intention: (row.querySelector('.mind-goal-intention')?.value || '').trim(),
            blocks: (row.querySelector('.mind-goal-blocks')?.value || '').trim(),
        })).filter((g) => g.what);
    }
    async function _saveGoals() {
        if (!_state)
            return;
        await ApiClient.updateCharacter(_state.charName, { goals: _collectGoals() });
        await worldState.fetch();
    }
    function _goalHistory() {
        if (!_state)
            return [];
        return worldState.players?.[_state.charName]?.goal_log || [];
    }
    function _goalHistoryHtml() {
        const log = _goalHistory();
        if (!log.length)
            return '';
        const rows = log.slice().reverse().map((e) => {
            const color = _goalStatusColor(String(e.status || ''));
            return `<div style="display:flex;gap:6px;align-items:baseline;font-size:10px;padding:2px 0;border-bottom:1px solid var(--border-light);">
                <span style="font-family:monospace;color:var(--text-muted);min-width:34px;">t${esc(e.tick)}</span>
                ${_badge(String(e.status || ''), color)}
                <span style="color:var(--text-dim);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(e.what || e.goal_id || '')}</span>
            </div>`;
        }).join('');
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Goal history - replay</div>
            ${rows}
        </div>`;
    }
    function _obligations() {
        if (!_state)
            return [];
        return worldState.players?.[_state.charName]?.obligations || [];
    }
    function _obligationColor(status) {
        switch (status) {
            case 'offered': return '#d29922';
            case 'accepted': return '#58a6ff';
            case 'done': return '#4caf50';
            default: return '#6e7681'; // refused / forgotten
        }
    }
    function _obligationsHtml() {
        const obligations = _obligations();
        if (!obligations.length)
            return '';
        const rows = obligations.map((o) => {
            const color = _obligationColor(String(o.status || 'offered'));
            const meta = [o.from ? `from ${o.from}` : '', o.due ? `due t${o.due}` : ''].filter(Boolean).join(' / ');
            return `<div style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid ${color};border-radius:6px;padding:7px 9px;margin-bottom:7px;">
                <div style="display:flex;align-items:center;gap:6px;">
                    <b style="font-size:11.5px;line-height:1.35;">${esc(o.charge || '')}</b>
                    <span style="margin-left:auto;">${_badge(String(o.status || 'offered'), color)}</span>
                </div>
                ${meta ? `<div style="font-size:9.5px;color:var(--text-muted);margin-top:3px;">${esc(meta)}</div>` : ''}
            </div>`;
        }).join('');
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Obligations - what they owe</div>
            ${rows}
        </div>`;
    }
    function _schedule() {
        if (!_state)
            return [];
        return worldState.players?.[_state.charName]?.schedule || [];
    }
    function _hhmm(minutes) {
        const m = (Number(minutes) || 0) % 1440;
        return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
    }
    function _scheduleHtml() {
        const steps = _schedule();
        if (!steps.length)
            return '';
        const rows = steps.map((s) => `<div style="display:flex;gap:8px;align-items:baseline;font-size:10.5px;padding:2px 0;border-bottom:1px solid var(--border-light);">
            <span style="font-family:monospace;color:var(--text-muted);min-width:34px;">${_hhmm(s.start)}</span>
            <span style="color:var(--text);">${esc(s.activity || '')}</span>
            ${s.area ? `<span style="color:var(--text-dim);">at ${esc(s.area)}</span>` : ''}
        </div>`).join('');
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Schedule - their day</div>
            ${rows}
        </div>`;
    }
    function _activePursuit() {
        if (!_state)
            return null;
        return worldState.players?.[_state.charName]?.active_pursuit || null;
    }
    function _plan() {
        if (!_state)
            return null;
        return worldState.players?.[_state.charName]?.plan || null;
    }
    function _stepLabel(step) {
        if (!step)
            return '-';
        switch (step.kind) {
            case 'travel': return 'travel ' + (step.area || (step.tags || []).join('/') || '');
            case 'take': return 'take ' + ((step.spec && (step.spec.tags || []).join('/')) || step.spec?.name || '');
            case 'drop': return 'drop ' + ((step.spec && (step.spec.tags || []).join('/')) || '');
            case 'activity': return 'activity ' + (step.activity || '');
            default: return String(step.kind || 'step');
        }
    }
    // task-714: the pursuit is character data (task-818), so the panel reads
    // Player.active_pursuit / Player.plan - what they are doing, not just why.
    function _pursuitHtml() {
        const pursuit = _activePursuit();
        const plan = _plan();
        if (!pursuit && !plan) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">no assigned pursuit - needs and goals only right now.</div>`;
        }
        const rows = [];
        if (pursuit) {
            rows.push(`<div style="display:flex;align-items:center;gap:6px;">
                <b style="font-size:11.5px;line-height:1.35;">${esc(pursuit.label || pursuit.template_id || '')}</b>
                <span style="font-size:9px;color:var(--text-muted);margin-left:auto;">${esc(pursuit.template_id || '')}</span>
            </div>`);
            if (pursuit.reason)
                rows.push(`<div style="font-size:9.5px;color:var(--text-muted);margin-top:3px;line-height:1.45;">${esc(pursuit.reason)}</div>`);
        }
        if (plan) {
            const steps = Array.isArray(plan.steps) ? plan.steps : [];
            const idx = Math.max(0, Number(plan.index || 0));
            rows.push(`<div style="font-size:10px;color:var(--text-dim);margin-top:4px;">step ${Math.min(idx + 1, steps.length)}/${steps.length}: ${esc(_stepLabel(steps[idx]))}</div>`);
        }
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Pursuit &amp; plan - what they are doing</div>
            <div style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid #58a6ff;border-radius:6px;padding:7px 9px;">${rows.join('')}</div>
        </div>`;
    }
    function _activityHtml() {
        if (!_state)
            return '';
        const a = worldState.players?.[_state.charName]?.activity;
        if (!a || !a.type)
            return '';
        const parts = [];
        if (a.elapsed_minutes != null)
            parts.push(`${Math.round(Number(a.elapsed_minutes))} min`);
        if (a.duration_minutes != null)
            parts.push(`of ${Math.round(Number(a.duration_minutes))} min`);
        if (a.catch_count != null)
            parts.push(`caught ${a.catch_count}`);
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Activity - what is underway</div>
            <div style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid #3fb950;border-radius:6px;padding:7px 9px;">
                <b style="font-size:11.5px;">${esc(a.type)}</b>
                ${parts.length ? `<span style="font-size:9.5px;color:var(--text-muted);margin-left:6px;">${esc(parts.join(' / '))}</span>` : ''}
            </div>
        </div>`;
    }
    function _feelingHtml() {
        if (!_state)
            return '';
        const p = worldState.players?.[_state.charName];
        if (!p)
            return '';
        const emo = p.emotion || null;
        const axes = (p.emotions && typeof p.emotions === 'object') ? p.emotions : {};
        const raised = Object.entries(axes)
            .map(([axis, amt]) => [axis, Number(amt)])
            .sort((a, b) => b[1] - a[1]).slice(0, 5);
        const current = emo && emo.current && emo.current !== 'neutral' ? emo.current : '';
        if (!current && !raised.length)
            return '';
        const head = current
            ? `${esc(current)}${emo.intensity ? ` (${Math.round(Number(emo.intensity))})` : ''}`
            : 'neutral';
        const desc = emo && emo.description
            ? `<div style="font-size:9.5px;color:var(--text-muted);margin-top:3px;line-height:1.45;">${esc(emo.description)}</div>` : '';
        const bars = raised.map(([axis, amt]) => `<div style="display:flex;gap:6px;align-items:baseline;font-size:10px;">
            <span style="color:var(--text-dim);min-width:84px;">${esc(axis)}</span><span style="color:var(--text-muted);">${Math.round(amt)}</span>
        </div>`).join('');
        // task-714: the cause the panel can honestly show without task-725 (the
        // memory gap): the most recent memory that itself carried this feeling.
        // A true triggering event needs a memory that records it - see task-725.
        const mems = Array.isArray(p.memories) ? p.memories : [];
        let lastFeeling = null;
        for (const mem of mems) {
            const labels = (Array.isArray(mem.memory_emotions) && mem.memory_emotions.length
                ? mem.memory_emotions
                : (mem.emotion && mem.emotion.label ? [mem.emotion] : []))
                .map((e) => String(e.label || '').toLowerCase());
            if (!labels.length)
                continue;
            if (current && !labels.includes(String(current).toLowerCase()))
                continue;
            if (!lastFeeling || (Number(mem.tick) || 0) > (Number(lastFeeling.tick) || 0))
                lastFeeling = mem;
        }
        const cause = lastFeeling
            ? `<div style="font-size:9.5px;color:var(--text-muted);margin-top:5px;line-height:1.45;">last felt in a memory: <span style="color:var(--text-dim);">"${esc(String(lastFeeling.text || '').slice(0, 110))}"</span> <span style="font-family:monospace;">t${esc(lastFeeling.tick ?? 0)}</span></div>`
            : '';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Feeling - their mood</div>
            <b style="font-size:11.5px;">${head}</b>
            ${desc}
            ${bars}
            ${cause}
        </div>`;
    }
    // task-714: what is happening to the body, shown only when there is
    // something to explain (state, a condition with its cause, or a vital out of
    // band). Reads the same Player fields the header row reads; the point is the
    // reason, not a second vitals panel. Engine-vs-data: a death *reason* needs a
    // memory that records it (task-725) - this shows the state and the drivers.
    function _bodyHtml() {
        if (!_state)
            return '';
        const p = worldState.players?.[_state.charName];
        if (!p)
            return '';
        const state = String(p.state || 'awake');
        const instances = p.conditions || {};
        const condRows = [];
        for (const [cid, list] of Object.entries(instances)) {
            if (cid === 'awake')
                continue;
            const arr = Array.isArray(list) ? list : [];
            for (const c of arr) {
                const bits = [];
                if (c && c.source)
                    bits.push(`why: ${esc(c.source)}`);
                if (c && c.duration != null)
                    bits.push(`left: ${esc(c.duration)}t`);
                if (c && c.level)
                    bits.push(`lvl ${esc(c.level)}`);
                condRows.push(`<div style="font-size:10.5px;padding:2px 0;border-bottom:1px solid var(--border-light);"><b style="color:#e05555;">${esc(cid)}</b>${bits.length ? ` <span style="color:var(--text-muted);">${bits.join(' / ')}</span>` : ''}</div>`);
            }
        }
        const VW = window;
        const vitals = p.vitals || {};
        // The core vitals the header row renders. Optional scenario vitals
        // (Arousal / Pleasure / Stimulation) sit at 0 when their system is off
        // and would read as "low" for every character, so they are not drivers.
        const CORE = ['HP', 'Energy', 'Hunger', 'Thirst', 'Bladder', 'Temperature', 'Sanity', 'Social', 'Entertainment', 'Hygiene'];
        const out = CORE
            .filter((n) => vitals[n] !== undefined)
            .map((n) => ({ n, lvl: String(VW.VitalColor?.level?.(vitals, n) || 'ok') }))
            .filter((x) => x.lvl !== 'ok');
        const vitalRows = out.map(({ n, lvl }) => {
            const color = lvl === 'critical' || lvl === 'bad' ? '#e05555' : '#e0a33c';
            return `<div style="font-size:10.5px;padding:2px 0;"><b style="color:${color};">${esc(n)} ${esc(vitals[n])}</b> <span style="color:var(--text-muted);">${esc(lvl)}</span></div>`;
        });
        const stateBad = state !== 'awake';
        if (!stateBad && !condRows.length && !vitalRows.length)
            return '';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Body - what is driving them</div>
            ${stateBad ? `<div style="font-size:11px;margin-bottom:4px;">state: <b style="color:${state === 'dead' ? 'var(--red)' : 'var(--orange)'};">${esc(state)}</b></div>` : ''}
            ${condRows.join('')}
            ${vitalRows.join('')}
        </div>`;
    }
    // ── task-787: mind surfaces moved out of the Bio / Advanced tabs ──────
    // Same markup, same runtime sources, same handlers. One home each: the
    // interest/fear tag editors, the recipe list, what-I-see, latest thoughts,
    // the PlanTracker plan, the knowledge chips, the event timeline and the
    // conversation memory all live here now, not beside the character's
    // definition (personality, appearance, stats) or in Advanced.
    /** DOM-safe id fragment for a character name (apostrophes break raw ids). */
    function _safeId() {
        return String(_state ? _state.charName : '').replace(/[^a-zA-Z0-9_-]/g, '_');
    }
    /** Is an AI provider configured? Mirrors agent-view's side-effect-free read. */
    function _isAiReady() {
        const AV = window.InspectorAgentView;
        return !!(AV && AV._isAiConfigured && AV._isAiConfigured());
    }
    function _interestTagsHtml() {
        if (!_state)
            return '';
        const AI = _isAiReady();
        const suffix = AI ? '' : ' - No AI provider configured. Add an API key and model in Settings first.';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Interest tags - what they notice</div>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Items matching these surface in the agent's prompt. Examine/take removes them from attention.</div>
            <div id="interest-tag-multiselect-mind-${_safeId()}"></div>
            <button class="btn btn-sm" ${AI ? '' : 'disabled'} onclick="InspectorAgentView._generateInterestTags('${_state.escName}')" style="font-size:10px;padding:2px 10px;margin-top:4px;" title="Ask the character's LLM to pick interest tags. Your hand-placed tags are kept - picks are added.${suffix}">✨ Generate from Personality</button>
        </div>`;
    }
    function _fearTagsHtml() {
        if (!_state)
            return '';
        const AI = _isAiReady();
        const suffix = AI ? '' : ' - No AI provider configured. Add an API key and model in Settings first.';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Fear tags - what unsettles them</div>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Meeting a co-located character, item, or area carrying any of these tags makes this character <code>frightened</code>. Leave empty for a character nothing unsettles.</div>
            <div id="fear-tag-multiselect-mind-${_safeId()}"></div>
            <button class="btn btn-sm" ${AI ? '' : 'disabled'} onclick="InspectorAgentView._generateFearTags('${_state.escName}')" style="font-size:10px;padding:2px 10px;margin-top:4px;" title="Ask the character's LLM to pick fear tags. Your hand-placed tags are kept - picks are added.${suffix}">😨 Generate from Personality</button>
        </div>`;
    }
    function _whatISeeHtml() {
        if (!_state)
            return '';
        const p = worldState.players?.[_state.charName];
        if (!p)
            return '';
        const area = worldState.areas?.[p.current_area];
        let body;
        if (area) {
            body = `<div>${area.description || ''}</div>`;
            const items = (area.items || []).map((item) => item.name).filter(Boolean).join(', ');
            if (items)
                body += `<div style="margin-top:4px;color:var(--text-dim);font-size:11px;">Items: ${items}</div>`;
            const others = Object.entries(worldState.players || {})
                .filter(([name, q]) => name !== _state.charName && q.current_area === p.current_area);
            if (others.length)
                body += `<div style="margin-top:4px;color:var(--pink);font-size:11px;">Also: ${others.map(([name]) => name).join(', ')}</div>`;
        }
        else {
            body = `<span style="color:var(--text-muted);">Unknown location</span>`;
        }
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">What I see - the room right now</div>
            <div style="font-size:12px;padding:8px 12px;background:var(--bg-inset);border-radius:6px;border-left:3px solid #58a6ff;">${body}</div>
        </div>`;
    }
    function _latestThoughtsHtml() {
        if (!_state)
            return '';
        const cs = events.getCharacterState(_state.charName) || {};
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Latest thoughts - the last turn</div>
            <div class="decision-trace" style="font-size:11px;">
                <div class="trace-thought">${esc(cs.lastThought || 'No recent thoughts.')}</div>
                ${cs.lastSpeech ? `<div style="color:var(--pink);font-style:italic;margin-top:4px;">💬 "${esc(cs.lastSpeech)}"</div>` : ''}
                ${cs.lastAction ? `<div style="color:var(--accent);font-weight:500;margin-top:4px;">⚡ ${esc(cs.lastAction)}</div>` : ''}
                ${cs.lastActionResult ? `<div style="color:var(--orange);font-size:10px;margin-top:4px;">→ ${esc(cs.lastActionResult)}</div>` : ''}
            </div>
        </div>`;
    }
    function _planHtml() {
        if (!_state)
            return '';
        const plan = (PlanTracker && PlanTracker.getPlan) ? PlanTracker.getPlan(_state.charName) : null;
        if (!plan || !plan.length)
            return '';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Plan - the current intent</div>
            <ol style="margin:0;padding-left:20px;font-size:11px;line-height:1.7;">${plan.map((step) => `<li>${esc(step)}</li>`).join('')}</ol>
        </div>`;
    }
    function _knowledgeHtml() {
        if (!_state)
            return '';
        const known = worldState.players?.[_state.charName]?.known || [];
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Knowledge - known from the start (${known.length})</div>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:6px;">Known ways/items become visible, people are never masked, known areas reveal hidden exits.
                <button class="btn btn-sm btn-blue" onclick="KnownBySection.openKnowledgeModal('${_state.escName}')" style="font-size:10px;margin-left:6px;" title="Select every runtime entity this character knows, grouped by category">🎛 Manage</button>
            </div>
            <div id="mind-knowledge-chips-${_safeId()}"></div>
        </div>`;
    }
    // Recipes a character knows: global / skill: / item: / discovered. Mirrors
    // engine/crafting.py learning rules via the shared agent-view helper.
    function _recipesHtml() {
        if (!_state)
            return '';
        // Task-841: known recipes are procedural knowledge - rendered
        // from the backend projection (registry + knowledge), never
        // executed here. Filled by _fetchRecipes below.
        return `<div style="margin-top:14px;" id="mind-recipes"><div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Recipes - what they can make</div>
            <div style="font-size:10px;color:var(--text-dim);">reading the known list…</div></div>`;
    }
    function _fetchRecipes() {
        if (!_state)
            return;
        fetch(`/api/players/${encodeURIComponent(_state.charName)}/recipes`, {
            headers: { 'Accept': 'application/json' }
        }).then(r => r.ok ? r.json() : Promise.reject(new Error(String(r.status))))
            .then((data) => {
            const live = _container?.querySelector('#mind-recipes');
            if (!live || !_state)
                return;
            const list = data.recipes || [];
            const player = worldState.players?.[_state.charName];
            // autonomy False = a human drives this character; only they
            // get the Make button. Everyone else is read-only.
            const controlled = player && player.autonomy === false;
            const head = `<div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Recipes - what they can make${list.length ? ` (${list.length})` : ''}</div>`;
            if (!list.length) {
                live.innerHTML = `${head}<div style="font-size:10px;color:var(--text-dim);">None yet - teach them (Skill lessons, recipe notes) or raise the gating skill.</div>`;
                return;
            }
            const srcColor = {
                global: 'var(--text-dim)', taught: '#58a6ff', discovered: '#3fb950',
                cookbook: '#d29922', skill: '#bc8cff',
            };
            live.innerHTML = `${head}${list.map((r) => {
                const meta = [
                    r.skill ? `${esc(r.skill)} ${r.dc ?? 10}` : '',
                    r.duration_min ? `${r.duration_min}m` : '',
                ].filter((s) => s).join(' · ');
                return `<div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:11px;">
                        <span style="flex:1;"><a href="#" data-recipe-lib="${esc(r.id)}" style="color:var(--text);text-decoration:underline dotted;" title="Browse in the library (read-only here)">🧾 ${esc(r.name)}</a> <span style="font-size:9px;color:${srcColor[r.source] || 'var(--text-dim)'};">${esc(r.source)}</span>${meta ? ` <span style="font-size:9px;color:var(--text-muted);">${esc(meta)}</span>` : ''}</span>
                        ${controlled ? `<button class="btn btn-sm" onclick="runAction('Make ${esc(r.name)}','${_state.escName}')" style="font-size:9px;padding:2px 8px;" title="Same as typing Make ${esc(r.name)} in the turn box">Make</button>` : ''}
                    </div>`;
            }).join('')}`;
            live.querySelectorAll('[data-recipe-lib]').forEach((a) => {
                a.addEventListener('click', (ev) => {
                    ev.preventDefault();
                    const lib = window.VW?.libraryBrowser;
                    if (lib && typeof lib.open === 'function')
                        lib.open('recipes');
                });
            });
        })
            .catch(() => { });
    }
    function _eventsTimelineHtml() {
        if (!_state)
            return '';
        const cs = events.getCharacterState(_state.charName) || {};
        const timeline = cs.detailedTimeline || [];
        let body;
        if (timeline.length > 0) {
            const startIdx = Math.max(0, timeline.length - 50);
            const blocks = [];
            for (let i = startIdx; i < timeline.length; i++) {
                const entry = timeline[i];
                const phase = entry.phase || 'unknown';
                const icons = { think: '💭', decide: '🎯', act: '⚡', action: '⚡', result: '→', react: '🔄', speech: '💬', observe: '👁️' };
                const icon = icons[phase] || '•';
                const label = phase.charAt(0).toUpperCase() + phase.slice(1);
                let contentText = '';
                if (entry.thought)
                    contentText = entry.thought;
                else if (entry.speech)
                    contentText = `"${entry.speech}"`;
                else if (entry.action)
                    contentText = entry.action;
                else if (entry.result)
                    contentText = entry.result;
                else if (entry.message)
                    contentText = entry.message;
                else
                    contentText = phase;
                blocks.push(`<div class="timeline-entry" onclick="InspectorAgentView._showTimelineDetail('${_state.escName}', ${i}, this)">
                    <div class="timeline-entry-header">
                        <span class="timeline-tick">[${events.tickToTime(entry.tick || 0)}]</span>
                        <span class="timeline-phase-badge timeline-phase-${phase}">${icon} ${label}</span>
                    </div>
                    <div class="timeline-entry-content">${esc(contentText)}</div>
                </div>`);
            }
            body = blocks.join('');
        }
        else {
            body = `<div style="font-size:11px;color:var(--text-muted);padding:8px;">No timeline entries yet. The timeline captures every thought, decision, action, result, and reaction as the character experiences them.</div>`;
        }
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Timeline - the lived trace</div>
            <div class="timeline-viewer" id="timeline-${_safeId()}">${body}</div>
            <div id="timeline-detail-${_safeId()}" style="display:none;"></div>
        </div>`;
    }
    function _conversationHtml() {
        if (!_state)
            return '';
        const hist = (agent && agent.getDisplayHistory) ? agent.getDisplayHistory(_state.charName) : [];
        let body;
        if (hist.length > 0) {
            body = hist.map((msg, i) => {
                const role = msg.role || 'unknown';
                const content = String(msg.content || '');
                const roleLabel = role === 'user' ? '👤 Prompt' : '🤖 Response';
                const roleColor = role === 'user' ? 'var(--accent)' : 'var(--purple)';
                return `<div style="padding:6px 8px;border-bottom:1px solid var(--border-light);">
                    <div style="font-size:9px;color:${roleColor};font-weight:600;margin-bottom:2px;">${roleLabel} #${i + 1}</div>
                    <div style="color:var(--text-dim);font-size:10px;max-height:40px;overflow:hidden;">${esc(content)}${content.length > 250 ? '...' : ''}</div>
                </div>`;
            }).join('');
        }
        else {
            body = `<div style="font-size:10px;color:var(--text-muted);">This character has no conversation history yet. History builds as the agent takes actions.</div>`;
        }
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Conversation memory (${hist.length} exchanges)</div>
            <div style="max-height:300px;overflow-y:auto;font-size:11px;">${body}</div>
        </div>`;
    }
    // ── task-729: the editing half ────────────────────────────────────────
    // The relationship store, the emotional state and the memory editor move
    // here so reading why a character feels and pursues is also where a
    // designer corrects it. Same stores, same agent-view / memory-view
    // handlers - no second source of truth.
    /** Emotion select + intensity, writing `{ emotion: { current, intensity } }`. */
    function _emotionEditorHtml() {
        if (!_state)
            return '';
        const p = worldState.players?.[_state.charName];
        if (!p)
            return '';
        const emotion = p.emotion || { current: 'neutral', intensity: 0 };
        const icons = { happy: '😊', sad: '😢', angry: '😠', afraid: '😨', surprised: '😲', disgusted: '🤢', neutral: '😐' };
        const opts = Object.keys(icons).map(e => `<option value="${e}"${emotion.current === e ? ' selected' : ''}>${icons[e]} ${e}</option>`).join('');
        return `<div style="margin-top:8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;padding:7px 9px;">
            <span style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;">Set feeling</span>
            <select id="mind-emotion" style="font-size:10px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:1px 4px;">${opts}</select>
            <span style="font-size:10px;color:var(--text-dim);">intensity</span>
            <input type="range" id="mind-emotion-intensity" min="0" max="1" step="0.05" value="${emotion.intensity || 0}" style="width:70px;">
            <span id="mind-emotion-val" style="min-width:30px;font-size:10px;color:var(--text-dim);">${(emotion.intensity || 0).toFixed(2)}</span>
        </div>`;
    }
    /** The authored relationship store (Player.relationships), moved out of Bio. */
    function _relationshipsHtml() {
        if (!_state)
            return '';
        const me = _state.charName;
        const p = worldState.players?.[me];
        if (!p)
            return '';
        const othersExMe = Object.entries(worldState.players || {})
            .filter(([name]) => name !== me);
        const rows = [];
        for (const [otherName] of othersExMe) {
            const rel = p.relationships?.[otherName];
            if (!rel)
                continue;
            const closeness = rel.closeness ?? 0;
            const relColor = closeness > 0 ? (closeness > 50 ? '#3fb950' : '#e3b341') : (closeness < 0 ? (closeness < -50 ? '#f85149' : '#d47766') : 'var(--text-muted)');
            const desc = closeness <= -75 ? 'mortal enemy' : closeness <= -50 ? 'enemy' : closeness <= -25 ? 'rival' : closeness < 0 ? 'unfriendly' : closeness === 0 ? 'neutral' : closeness <= 25 ? 'acquaintance' : closeness <= 50 ? 'friend' : closeness <= 75 ? 'close friend' : 'inseparable';
            rows.push(`<div class="relationship-item-inspector" data-other="${esc(otherName)}" style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                <span style="min-width:70px;font-size:11px;font-weight:500;">${esc(otherName)}</span>
                <input type="range" min="-100" max="100" value="${closeness}" class="rel-slider" data-agent="${esc(me)}" data-other="${esc(otherName)}" style="flex:1;height:4px;accent-color:${relColor};">
                <span style="font-size:10px;color:var(--text-muted);min-width:28px;text-align:right;" class="rel-val">${closeness}</span>
                <span style="font-size:9px;color:var(--text-dim);min-width:70px;" class="rel-label">${desc}</span>
                <input type="text" class="rel-label-input" data-agent="${esc(me)}" data-other="${esc(otherName)}" value="${esc(rel.label || '')}" placeholder="label (e.g. mom, brother)" style="width:80px;font-size:9px;padding:1px 3px;">
                <label title="Tick if you know their name (first_sighting=false)" style="display:flex;align-items:center;gap:2px;font-size:9px;color:var(--text-dim);cursor:pointer;">
                    <input type="checkbox" class="rel-known" data-agent="${esc(me)}" data-other="${esc(otherName)}" ${rel.first_sighting ? '' : 'checked'}> name
                </label>
                <span class="mind-rel-del" data-agent="${esc(me)}" data-other="${esc(otherName)}" style="cursor:pointer;color:var(--red);font-size:12px;padding:0 2px;" title="Remove relationship">✕</span>
            </div>`);
        }
        const hasUnrelated = othersExMe.some(([name]) => !p.relationships?.[name]);
        const addSel = hasUnrelated
            ? `<select id="rel-add-select-${me.replace(/\s+/g, '_')}" style="font-size:10px;max-width:160px;margin-top:4px;">
                <option value="">+ Add relationship...</option>
                ${othersExMe.filter(([name]) => !p.relationships?.[name]).map(([name]) => `<option value="${esc(name)}">${esc(name)}</option>`).join('')}
              </select>`
            : `<div style="font-size:10px;color:var(--text-muted);margin-top:4px;">All players have a relationship entry.</div>`;
        return `<div style="margin-bottom:16px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Relationships - authored store (${rows.length})</div>
            ${rows.join('') || `<div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">no relationships authored.</div>`}
            ${addSel}
        </div>`;
    }
    /** The memory editor toolbar (add / generate / clear all / clear expired). */
    function _memoryToolbarHtml() {
        if (!_state)
            return '';
        const e = _state.escName;
        return `<div style="display:flex;gap:4px;flex-wrap:wrap;margin:8px 0;">
            <button class="btn btn-sm btn-blue" onclick="InspectorMemory.addMemory('${e}')" style="font-size:10px;">+ Add Memory</button>
            <button class="btn btn-sm btn-green" onclick="InspectorMemory.generateMemory('${e}')" title="Write a first-person seed memory via the LLM" style="font-size:10px;">✨ Gen Memory</button>
            <button class="btn btn-sm" onclick="InspectorMemory.clearExpired('${e}')" style="font-size:10px;" title="Drop expired suppressions">🧹 Clear Expired</button>
            <button class="btn btn-sm btn-red" onclick="if(confirm('Clear all memories?')){ApiClient.clearPlayerMemories('${e}').then(()=>worldState.fetch())}" style="font-size:10px;">🗑 Clear All</button>
        </div>`;
    }
    // Re-render while the panel is open whenever the world state updates, so a
    // mutation (a memory save, a relationship add, a tag change) reflects here
    // too - memory-view's handlers finish with worldState.fetch() + inspector
    // _reRender(), and only the fetch reaches this modal.
    let _subscribed = false;
    function _ensureSubscribed() {
        if (_subscribed)
            return;
        _subscribed = true;
        worldState.on('update', () => {
            if (!_state || !_container)
                return;
            // Never wipe an in-progress persona edit: a background state
            // push while typing would destroy unsaved form input. Any
            // focused field counts - including chip inputs, which carry
            // no data-path until their pill is committed.
            const active = document.activeElement;
            if (_state.tab === 'persona' && active
                && active.closest('#mind-persona')
                && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA'))
                return;
            _render();
        });
    }
    function _mosiac() {
        if (!_state)
            return null;
        return worldState.players?.[_state.charName]?.mosiac || null;
    }
    function _mosiacHtml() {
        const m = _mosiac();
        if (!m)
            return '';
        const letter = (key, label, body) => `<div style="margin-bottom:5px;"><span style="font-family:monospace;color:#58a6ff;">${key}</span> <span style="color:var(--text-muted);font-size:9.5px;text-transform:uppercase;letter-spacing:.06em;">${label}</span><div style="font-size:10.5px;line-height:1.4;">${body}</div></div>`;
        const needs = (m.A || []).map((n) => `${esc(n.need)} ${n.value}`).join(', ') || 'nothing pressing';
        const step = m.S && m.S.step
            ? `${_hhmm(m.S.step.start)} ${esc(m.S.step.activity)}${m.S.step.area ? ' at ' + esc(m.S.step.area) : ''}`
            : 'no schedule';
        const tierCounts = Object.keys(m.C || {}).map(k => `${esc(k)} ${(m.C[k] || []).length}`).join(' / ') || 'none';
        return `<div style="margin-bottom:12px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">MOSIAC - the decision context</div>
            ${letter('M', 'motivation', esc(m.M || '-'))}
            ${letter('I', 'intention', esc(m.I || '-'))}
            ${letter('O', 'obligations', (m.O || []).length ? (m.O || []).map((o) => esc(o.charge)).join(', ') : 'none')}
            ${letter('S', 'schedule', step)}
            ${letter('A', 'attention', esc(needs))}
            ${letter('C', 'choices', esc(tierCounts))}
        </div>`;
    }
    // task-802 / 805 / 806: the derived decision weights, the authored dials and
    // the whispered lines - the same traits the soak weighs (task-804's input).
    function _dispositionHtml() {
        if (!_state)
            return '';
        const p = worldState.players?.[_state.charName];
        if (!p)
            return '';
        const disp = p.disposition || {};
        const weights = Array.isArray(disp.weights) ? disp.weights : [];
        const dials = disp.dials || (p.personality_dials || {});
        const whispers = Array.isArray(p.trait_behavior) ? p.trait_behavior : [];
        const entries = weights.slice().sort((a, b) => Math.abs(Number(b.value)) - Math.abs(Number(a.value)));
        const dialEntries = Object.entries(dials);
        const gated = Array.isArray(disp.gated) ? disp.gated : [];
        if (!entries.length && !dialEntries.length && !whispers.length && !gated.length) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">no disposition signals - an unauthored character scores neutral.</div>`;
        }
        const weightRows = entries.map((w) => {
            const v = Number(w.value);
            const label = w.kind
                ? `${esc(w.name)} <span style="color:var(--text-muted);">${esc(w.kind)}</span>`
                : esc(w.name);
            const range = `base ${w.base} range [${w.lo}, ${w.hi}]`;
            return `<div style="display:flex;gap:6px;align-items:baseline;font-size:10px;">
                <span style="color:var(--text-dim);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(range)}">${label}</span>
                <span style="font-family:monospace;color:${v >= 0 ? '#58a6ff' : '#e05555'};">${v > 0 ? '+' : ''}${v.toFixed(2)}</span>
            </div>`;
        }).join('');
        const dialRows = dialEntries.map(([k, v]) => `<div style="display:flex;gap:6px;align-items:baseline;font-size:10px;">
                <span style="color:var(--text-dim);flex:1;">${esc(k)}</span>
                <span style="font-family:monospace;color:var(--text-muted);">${Number(v).toFixed(2)}</span>
            </div>`).join('');
        const whisperRows = whispers.map((w) => `<div style="font-size:9.5px;color:var(--text-muted);line-height:1.45;margin-top:3px;">${esc(w)}</div>`).join('');
        const gatedRow = gated.length
            ? `<div style="font-size:9.5px;color:#e05555;margin-top:4px;line-height:1.45;">excluded by values: ${gated.map(g => esc(g)).join(', ')}</div>`
            : '';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Disposition - what they weigh</div>
            <div style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid #bc8cff;border-radius:6px;padding:7px 9px;">
                ${weightRows}
                ${dialRows}
                ${gatedRow}
                ${whisperRows}
            </div>
        </div>`;
    }
    // task-801 / 803: the soak candidate verbs, the score each contributes, and
    // which the character's values exclude - the action side of the score model.
    function _actionsHtml() {
        if (!_state)
            return '';
        const p = worldState.players?.[_state.charName];
        const actions = (p && p.disposition && Array.isArray(p.disposition.actions)) ? p.disposition.actions : [];
        if (!actions.length)
            return '';
        const gated = new Set(((p.disposition && p.disposition.gated) || []).map((g) => String(g).toLowerCase()));
        const rows = actions.map((a) => {
            const off = gated.has(String(a.verb).toLowerCase());
            const scores = (a.scores || []).join(', ') || '-';
            return `<div style="display:flex;gap:6px;align-items:baseline;font-size:10px;${off ? 'opacity:.45;text-decoration:line-through;' : ''}">
                <span style="color:var(--text-dim);min-width:64px;">${esc(a.verb)}</span>
                <span style="color:var(--text-muted);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(scores)}</span>
            </div>`;
        }).join('');
        const excluded = gated.size;
        return `<details style="margin-top:14px;">
            <summary style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;cursor:pointer;">Actions - what they can choose (${actions.length}${excluded ? `, ${excluded} excluded` : ''})</summary>
            <div style="margin-top:6px;">${rows}</div>
        </details>`;
    }
    function _peopleHtml() {
        if (!_state)
            return '';
        if (_state.peopleStatus === 'loading') {
            return `<div style="font-size:10.5px;color:var(--text-muted);">deriving profiles…</div>`;
        }
        if (_state.peopleStatus === 'error' || !_state.people.length) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">${_state.peopleStatus === 'error' ? 'profiles unavailable.' : 'no rel-tagged memories yet - feelings about people appear as the character experiences them.'}</div>`;
        }
        const DIMS = [['trust', '#4caf50'], ['fear', '#e0a33c'], ['attraction', '#f778ba'], ['disgust', '#3fb950'], ['respect', '#bc8cff']];
        return _state.people.map((p) => {
            const selected = _state && _state.filter === 'person:' + p.name;
            const profile = p.profile;
            const rows = DIMS.map(([dim, color]) => _bar(dim, Number(profile[dim] || 0), 100, color, true)).join('');
            return `<div class="mind-person" data-person="${esc(p.name)}" style="background:var(--bg-card);border:1px solid ${selected ? '#1f6feb' : 'var(--border)'};border-radius:6px;padding:8px 10px;margin-bottom:7px;cursor:pointer;">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <b style="font-size:11.5px;">${esc(p.name)}</b>
                    <span style="font-size:9px;color:var(--text-muted);margin-left:auto;">${esc(p.profile.role || 'stranger')} · ${p.memory_count} mem${p.memory_count === 1 ? '' : 's'}${p.profile.has_signal ? '' : ' · no signal yet'}</span>
                </div>
                ${rows}
                ${p.profile.summary ? `<div style="font-size:9.5px;color:var(--text-muted);margin-top:4px;line-height:1.45;">${esc(p.profile.summary)}</div>` : ''}
            </div>`;
        }).join('');
    }
    // ── persona (task-830) ─────────────────────────────────────────
    // The full 828 schema, editable, with one explicit Compile. Reads
    // GET /record (block + schema + consumer hints), writes PUT /record,
    // projects via POST /record/compile (preview before clobber).
    const _PERSONA_SECTIONS = [
        ['identity', 'Identity'], ['appearance', 'Appearance'],
        ['personality', 'Personality'], ['narrative', 'Narrative'],
    ];
    const _PERSONA_NUMBERS = new Set(['identity.age', 'appearance.height_cm', 'appearance.weight_kg']);
    const _PERSONA_TEXTAREAS = new Set([
        'appearance.overview',
        'narrative.arc',
        'narrative.role_in_town',
        'narrative.biography.early_life',
        'narrative.biography.adulthood',
        'narrative.biography.current_situation',
        'narrative.secrets.deepest_secret',
    ]);
    function _personaVal(path) {
        const rec = _state?.persona?.record || {};
        const parts = path.split('.');
        let cur = rec;
        for (const p of parts) {
            if (typeof cur !== 'object' || cur === null)
                return undefined;
            cur = cur[p];
        }
        return cur;
    }
    const _PERSONA_INTIMACY = new Set(['personality.kinks', 'personality.turn_ons',
        'personality.turn_offs', 'personality.boundaries', 'personality.experience']);
    const _PERSONA_TONES = {
        fears: 'danger', traumas: 'danger', turn_offs: 'danger', dislikes: 'danger',
        interests: 'info', likes: 'info',
    };
    function _personaCss() {
        return `<style>
        #mind-persona .pf-badges{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px;}
        #mind-persona .pf-badge{font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:999px;padding:2px 10px;color:var(--text-dim);}
        #mind-persona .pf-span{grid-column:1/-1;}
        #mind-persona .pf-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;}
        #mind-persona .pf-hint{cursor:help;font-size:10px;}
        #mind-persona .pf-in{width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px 9px;font-size:13px;box-sizing:border-box;box-shadow:inset 0 1px 2px rgba(0,0,0,.25);}
        #mind-persona .pf-in:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 2px rgba(88,166,255,.18);}
        #mind-persona textarea.pf-in{resize:vertical;font-family:inherit;min-height:56px;line-height:1.4;}
        #mind-persona fieldset.pf-group{border:1px solid var(--border);border-radius:6px;padding:7px 9px;margin:0;}
        #mind-persona fieldset.pf-group>legend{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);padding:0 4px;}
        #mind-persona .pf-sub{font-size:11px;color:var(--text-muted);margin-bottom:2px;}
        #mind-persona .pf-chips{display:flex;flex-wrap:wrap;gap:5px;background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:5px 7px;box-shadow:inset 0 1px 2px rgba(0,0,0,.25);}
        #mind-persona .pf-chips:focus-within{border-color:var(--accent);box-shadow:0 0 0 2px rgba(88,166,255,.18);}
        #mind-persona .pf-chip{display:inline-flex;align-items:center;gap:5px;font-size:12px;background:var(--bg-card);border:1px solid var(--border);border-radius:999px;padding:2px 6px 2px 10px;}
        #mind-persona .pf-chip.danger{border-color:#8a3a42;color:#e08a92;}
        #mind-persona .pf-chip.info{border-color:#2a6a7a;color:#7ad0e0;}
        #mind-persona .pf-chip b{cursor:pointer;font-weight:700;color:var(--text-muted);}
        #mind-persona .pf-chip b:hover{color:var(--text);}
        #mind-persona .pf-chip-new{flex:1;min-width:90px;background:transparent;border:none;color:var(--text);font-size:12px;outline:none;}
        #mind-persona details.pf-intimacy{border-style:dashed;margin-top:8px;}
        #mind-persona .pf-locked{filter:blur(4px);cursor:pointer;user-select:none;}
        #mind-persona .pf-lock-note{font-size:11px;color:var(--text-muted);margin-bottom:4px;cursor:pointer;}
        #mind-persona .pf-codex{background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;padding:8px 10px;font-size:12px;line-height:1.5;}
        #mind-persona .pf-head{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;padding:4px 2px 12px;margin-bottom:12px;border-bottom:1px solid var(--border);}
        #mind-persona .pf-head-main{min-width:240px;flex:1;}
        #mind-persona .pf-head-name{font-family:Georgia,'Times New Roman',serif;font-size:26px;font-weight:600;line-height:1.2;}
        #mind-persona .pf-head-prose{font-size:13px;color:var(--text-dim);font-style:italic;margin:4px 0 8px;max-width:min(640px,100%);}
        #mind-persona .pf-head-side{display:flex;flex-direction:column;gap:8px;align-items:flex-end;}
        #mind-persona .pf-states{display:flex;gap:8px;align-items:center;font-size:12px;flex-wrap:wrap;justify-content:flex-end;}
        #mind-persona .pf-state{display:inline-flex;align-items:center;gap:4px;border:1px solid currentColor;border-radius:999px;padding:2px 10px;font-size:11px;font-weight:600;white-space:nowrap;background:var(--bg-input);}
        #mind-persona .pf-state-ok{color:var(--green);}
        #mind-persona .pf-state-dirty{color:#e0a33c;}
        #mind-persona .pf-state-stale{color:#e0a33c;}
        #mind-persona .pf-actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;}
        #mind-persona .pf-workspace{display:grid;grid-template-columns:minmax(280px,340px) minmax(0,1fr);gap:18px 22px;align-items:start;}
        @media (max-width:920px){#mind-persona .pf-workspace{grid-template-columns:1fr;}#mind-persona .pf-doll-col{position:static;}}
        @media (max-width:640px){#mind-persona .pf-head{gap:10px;}#mind-persona .pf-head-main{min-width:0;flex-basis:100%;}#mind-persona .pf-head-name{font-size:21px;}#mind-persona .pf-head-side{align-items:flex-start;width:100%;}#mind-persona .pf-states,#mind-persona .pf-actions{justify-content:flex-start;}}
        #mind-persona .pf-doll-col{position:sticky;top:8px;background:var(--bg-inset);border:1px solid var(--border);border-radius:10px;padding:10px 12px;}
        #mind-persona .pf-facing{display:flex;gap:4px;margin-bottom:8px;}
        #mind-persona .pf-facing button{font-size:11px;padding:3px 10px;}
        #mind-persona .pf-facing button.on{border-color:var(--accent);color:var(--accent);}
        #mind-persona .pf-mark-list{display:flex;flex-direction:column;gap:4px;margin-top:6px;}
        #mind-persona .pf-mark-row{display:flex;align-items:center;gap:6px;font-size:12px;}
        #mind-persona .pf-mark-row b{cursor:pointer;color:var(--text-muted);}
        #mind-persona .pf-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;}
        @media (max-width:760px){#mind-persona .pf-grid{grid-template-columns:1fr;}}
        #mind-persona details.pf-fold{border:1px solid var(--border);border-radius:8px;margin-bottom:12px;background:var(--bg-card);}
        #mind-persona details.pf-fold>summary{cursor:pointer;padding:10px 14px;font-size:12px;font-weight:600;color:var(--text);letter-spacing:.02em;list-style:none;}
        #mind-persona details.pf-fold.pf-intimacy{border-style:dashed;}
        #mind-persona #mind-persona-doll:focus{outline:none;}
        #mind-persona #mind-persona-doll:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:8px;}
        </style>`;
    }
    // task-852 P3: markings live in appearance.body.modifications[] as
    // "area::text". Same array, no second store. Unprefixed = unassigned.
    const _MARK_SEP = '::';
    function _parseMark(raw) {
        const s = String(raw || '');
        const i = s.indexOf(_MARK_SEP);
        if (i <= 0)
            return { area: null, text: s };
        return { area: s.slice(0, i), text: s.slice(i + _MARK_SEP.length) };
    }
    function _formatMark(area, text) {
        return `${area}${_MARK_SEP}${text}`;
    }
    function _allMarks() {
        const mods = _personaVal('appearance.body.modifications');
        return Array.isArray(mods) ? mods.map((m) => String(m)).filter((s) => s.trim()) : [];
    }
    function _setAllMarks(values) {
        if (!_state?.persona)
            return;
        const rec = _state.persona.record || {};
        const appearance = (rec.appearance = rec.appearance || {});
        const body = (appearance.body = appearance.body || {});
        body.modifications = values;
        const hidden = _container?.querySelector('input[type="hidden"][data-persona-path="appearance.body.modifications"]');
        if (hidden)
            hidden.value = values.join('\n');
        _personaDirty();
    }
    function _personaChipBox(path, values, tone) {
        const chips = values.map((v) => `<span class="pf-chip${tone ? ` ${tone}` : ''}">${esc(v)}<b data-chip-x="${esc(path)}" data-chip-v="${esc(v)}">×</b></span>`).join('');
        const joined = esc(values.join('\n')).replace(/\n/g, '&#10;');
        return `<div class="pf-chips">${chips}<input class="pf-chip-new" data-chip-new="${esc(path)}" placeholder="add…" style="flex:1;min-width:90px;background:transparent;border:none;color:var(--text);font-size:12px;outline:none;"><input type="hidden" data-persona-path="${esc(path)}" value="${joined}"></div>`;
    }
    // task-843: the model's provenance. A field the converter invented (rather
    // than read from the source) is marked so the author can tell guess from
    // fact at a glance. A parent path marks its children and a child marks its
    // group, so an inferred whole reads as one cluster. Cleared by the next
    // `_fetchPersona` (save, compile, or reopening the tab).
    function _sparkle(path) {
        const arr = _state?.persona?.inferred;
        const set = new Set(Array.isArray(arr) ? arr : []);
        if (!set.size)
            return '';
        let hit = set.has(path);
        if (!hit) {
            for (const p of set) {
                if (p.startsWith(path + '.') || path.startsWith(p + '.')) {
                    hit = true;
                    break;
                }
            }
        }
        return hit
            ? ` <span class="pf-inferred" style="color:var(--yellow);" title="inferred by the model - not stated in the source; review or clear it">✨</span>`
            : '';
    }
    function _personaFieldHtml(section, field, decl) {
        const path = `${section}.${field}`;
        const hint = _state?.persona?.hints[path] || (decl && decl.description) || '';
        const hintIco = hint ? ` <span class="pf-hint" title="${esc(hint)}">ⓘ</span>` : '';
        const label = `<div class="pf-label"><span>${esc(field)}${_sparkle(path)}</span>${hintIco}</div>`;
        const val = _personaVal(path);
        const tone = _PERSONA_TONES[field] || '';
        if (!decl || decl.type === 'string' || decl.type === 'number' || !_state) {
            const numeric = decl?.type === 'number' || _PERSONA_NUMBERS.has(path);
            const str = val === undefined || val === null ? '' : String(val);
            if (_PERSONA_TEXTAREAS.has(path)) {
                return { html: `<div class="pf-span">${label}<textarea class="pf-in" data-persona-path="${esc(path)}" rows="3">${esc(str)}</textarea></div>`, wide: true };
            }
            // Identity text fields stay free-form; a native datalist adds a
            // pick-list from the engine's vocabulary. Picking fires `input`
            // on the field, so the dirty chip and form-sync work unchanged.
            const opts = section === 'identity' && !numeric
                ? (_state?.persona?.suggestions?.[field] || []) : [];
            const listId = opts.length ? `pf-dl-${section}-${field}` : '';
            const listAttrs = listId ? ` list="${esc(listId)}" autocomplete="off" placeholder="type or pick"` : '';
            const datalist = listId
                ? `<datalist id="${esc(listId)}">${opts.map((o) => `<option value="${esc(o)}"></option>`).join('')}</datalist>`
                : '';
            return { html: `<div>${label}<input class="pf-in" data-persona-path="${esc(path)}" value="${esc(str)}"${numeric ? ' inputmode="decimal"' : ''}${listAttrs}>${datalist}</div>`, wide: false };
        }
        if (decl.type === 'array') {
            const values = Array.isArray(val) ? val.map((v) => String(v)) : [];
            return { html: `<div class="pf-span">${label}${_personaChipBox(path, values, tone)}</div>`, wide: true };
        }
        if (decl.type === 'object' && decl.properties) {
            // modifications[] is authored on the doll side panel (task-852 P3) -
            // keep a hidden input so collect/save still round-trips, no second editor.
            const skipSubs = path === 'appearance.body' ? new Set(['modifications']) : null;
            const subs = Object.keys(decl.properties).map((sub) => {
                if (skipSubs?.has(sub))
                    return '';
                const subDecl = decl.properties[sub];
                const subPath = `${path}.${sub}`;
                const subVal = _personaVal(subPath);
                if (subDecl?.type === 'array') {
                    const values = Array.isArray(subVal) ? subVal.map((v) => String(v)) : [];
                    return `<div style="margin-bottom:5px;"><div class="pf-sub">${esc(sub)}${_sparkle(subPath)}</div>${_personaChipBox(subPath, values, tone)}</div>`;
                }
                const str = subVal === undefined || subVal === null ? '' : String(subVal);
                if (_PERSONA_TEXTAREAS.has(subPath)) {
                    return `<div style="margin-bottom:8px;"><div class="pf-sub">${esc(sub)}${_sparkle(subPath)}</div><textarea class="pf-in" data-persona-path="${esc(subPath)}" rows="3">${esc(str)}</textarea></div>`;
                }
                return `<div style="margin-bottom:5px;"><div class="pf-sub">${esc(sub)}${_sparkle(subPath)}</div><input class="pf-in" data-persona-path="${esc(subPath)}" value="${esc(str)}"></div>`;
            }).join('');
            const markHidden = path === 'appearance.body'
                ? (() => {
                    const values = _allMarks();
                    const joined = esc(values.join('\n')).replace(/\n/g, '&#10;');
                    return `<input type="hidden" data-persona-path="appearance.body.modifications" value="${joined}">`;
                })()
                : '';
            const locked = path === 'narrative.secrets'
                ? `<div class="pf-lock-note" data-lock="${esc(path)}">🔒 sealed - never compiled to prose. click to reveal.</div><div class="pf-locked" data-lockbody="${esc(path)}">${subs}</div>`
                : subs;
            return { html: `<div class="pf-span"><fieldset class="pf-group"><legend>${esc(field)}${hintIco}</legend>${locked}${markHidden}</fieldset></div>`, wide: true };
        }
        const str = val === undefined || val === null ? '' : String(val);
        if (_PERSONA_TEXTAREAS.has(path)) {
            return { html: `<div class="pf-span">${label}<textarea class="pf-in" data-persona-path="${esc(path)}" rows="3">${esc(str)}</textarea></div>`, wide: true };
        }
        return { html: `<div>${label}<input class="pf-in" data-persona-path="${esc(path)}" value="${esc(str)}"></div>`, wide: false };
    }
    // ── persona body navigator (task-847) ─────────────────────────
    // The paperdoll's AREA_TO_REGIONS, read - never re-declared. Clicking
    // an area shows live region status (same data as the 🩺 modal) plus the
    // linked schema values as a descriptive summary. The schema inputs
    // below stay the only editors; summary lines jump to their field.
    const _REGION_SCHEMA_MAP = {
        head: ['appearance.hair.color', 'appearance.hair.length',
            'appearance.hair.style', 'appearance.eyes.color',
            'appearance.face.shape', 'appearance.face.features'],
        torso: ['appearance.body.chest'],
        waist: ['appearance.body.waist', 'appearance.body.hips',
            'appearance.body.butt'],
        legs: ['appearance.body.legs'],
        feet: ['appearance.style.footwear'],
    };
    function _schemaLineSummary(path) {
        const val = _personaVal(path);
        if (val === undefined || val === null || String(val).trim() === '')
            return '';
        if (Array.isArray(val)) {
            const items = val.map((v) => String(v)).filter((s) => s.trim() !== '');
            if (!items.length)
                return '';
            return items.map((s) => `· ${esc(s)}`).join('<br>');
        }
        return esc(String(val));
    }
    function _bodyNavSideHtml(area) {
        const pd = window.InspectorPaperdoll;
        const regions = ((pd?.AREA_TO_REGIONS || {})[area] || []);
        const player = (worldState.players || {})[_state?.charName || ''];
        const bodyState = player?.body_state || {};
        const playerConditions = player?.conditions || {};
        const regionName = (regionId) => (player?.body_region_names?.[regionId] || regionId.replace(/_/g, ' '));
        const rows = regions.map((regionId) => {
            const bs = bodyState[regionId] || {};
            const injured = (playerConditions.injured || [])
                .filter((i) => i.body_part === regionId);
            const bleeding = (playerConditions.bleeding || [])
                .filter((i) => i.body_part === regionId);
            const missing = (playerConditions.missing || [])
                .filter((i) => i.body_part === regionId);
            const exposed = player?.region_exposed?.[regionId] !== false;
            const sensNum = bs.sensitivity !== undefined ? parseFloat(bs.sensitivity) : NaN;
            const sens = Number.isFinite(sensNum) ? sensNum.toFixed(2) : '-';
            const chips = [];
            if (injured.length)
                chips.push(`<span style="color:var(--yellow);">🤕 Lv${Math.max(...injured.map((i) => i.level || 1))}</span>`);
            if (bleeding.length)
                chips.push(`<span style="color:var(--red);">🩸 bleeding</span>`);
            if (missing.length)
                chips.push(`<span style="color:var(--red);">✖ missing</span>`);
            if (!exposed)
                chips.push(`<span style="color:var(--text-dim);">🛡️ covered</span>`);
            if (!chips.length)
                chips.push(`<span style="color:var(--text-dim);">healthy</span>`);
            const slider = Number.isFinite(sensNum)
                ? `<input type="range" min="0" max="100" value="${Math.round(sensNum * 100)}" data-sens-region="${esc(regionId)}" title="sensitivity baseline - writes on release" style="width:90px;vertical-align:middle;accent-color:var(--accent);">`
                : '';
            return `<div style="margin-bottom:6px;"><span style="font-size:12px;text-transform:capitalize;">${esc(regionName(regionId))}</span> `
                + `<span style="font-size:10px;color:var(--text-muted);">sens ${sens}</span> ${slider} `
                + `<span style="font-size:10px;">${chips.join(' · ')}</span></div>`;
        }).join('');
        const linked = (_REGION_SCHEMA_MAP[area] || [])
            .map((path) => {
            const leaf = path.split('.').slice(-1)[0];
            const summary = _schemaLineSummary(path);
            const body = summary
                ? summary
                : `<span style="color:var(--text-muted);">- empty, fill it below</span>`;
            return `<div style="margin-bottom:5px;"><span style="font-size:11px;color:var(--text-muted);">${esc(leaf)}</span> `
                + `<span data-persona-jump="${esc(path)}" title="jump to field" style="cursor:pointer;color:var(--accent);font-size:12px;">⤴</span><br>${body}</div>`;
        }).join('');
        const areaMarks = _allMarks()
            .map((raw) => ({ raw, ..._parseMark(raw) }))
            .filter((m) => m.area === area && m.text.trim());
        const markRows = areaMarks.map((m) => `<div class="pf-mark-row"><span>${esc(m.text)}</span>`
            + `<b data-mark-x="${esc(m.raw)}" title="remove">×</b></div>`).join('');
        const markEditor = `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);">
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">markings on ${esc(area)}</div>
            <div class="pf-mark-list" id="mind-persona-marks">${markRows || '<div style="font-size:11px;color:var(--text-muted);">none yet</div>'}</div>
            <div style="display:flex;gap:6px;margin-top:6px;">
                <input class="pf-in" id="mind-persona-mark-new" placeholder="scar, tattoo, piercing…" style="flex:1;font-size:12px;padding:4px 8px;">
                <button class="btn btn-sm" id="mind-persona-mark-add" style="font-size:11px;" type="button">add</button>
            </div>
        </div>`;
        const descBlock = linked
            ? `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);">${linked}</div>`
            : `<div style="margin-top:8px;font-size:11px;color:var(--text-muted);">no schema field maps to this area - live status + markings only.</div>`;
        return `${rows}${descBlock}${markEditor}`;
    }
    function _bodyNavHtml() {
        const pd = window.InspectorPaperdoll;
        const map = pd?.AREA_TO_REGIONS || {};
        const areas = Object.keys(map).filter((a) => (map[a] || []).length > 0);
        if (!areas.length || typeof pd?.renderPaperdollFigureHtml !== 'function')
            return '';
        const sel = _state?.persona?.bodyNav || null;
        const facing = _state?.persona?.dollFacing === 'back' ? 'back' : 'front';
        const player = (worldState.players || {})[_state?.charName || ''];
        const doll = pd.renderPaperdollFigureHtml(_state?.charName || '', player || {}, esc, _state?.escName || '', { mode: 'navigate', selectedArea: sel, facing });
        const side = sel
            ? _bodyNavSideHtml(sel)
            : `<div style="font-size:11px;color:var(--text-muted);">pick a bodypart on the doll - live status, sheet summary, sensitivity, markings. Arrows move · F/B flip · Esc clears.</div>`;
        const unassigned = _allMarks().filter((raw) => !_parseMark(raw).area);
        const orphan = unassigned.length
            ? `<div style="margin-top:8px;font-size:11px;color:var(--text-muted);">unassigned markings (pick a region, then re-add): ${unassigned.map((m) => esc(_parseMark(m).text || m)).join(' · ')}</div>`
            : '';
        return `<div>
            <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);margin-bottom:6px;">🩺 body</div>
            <div class="pf-facing" role="group" aria-label="doll facing">
                <button type="button" class="btn btn-sm${facing === 'front' ? ' on' : ''}" data-doll-facing="front" title="front view (F)">front</button>
                <button type="button" class="btn btn-sm${facing === 'back' ? ' on' : ''}" data-doll-facing="back" title="back view (B)">back</button>
            </div>
            <div id="mind-persona-doll" tabindex="0" aria-label="body doll" title="arrows move the selection, F / B flip the doll, Esc clears">${doll}</div>
            <div id="mind-persona-bodynav" style="margin-top:8px;">${side}</div>
            ${orphan}
        </div>`;
    }
    function _wireBodyNav(pane) {
        const pd = window.InspectorPaperdoll;
        if (pd) {
            pd.onNavigate = (charName, area) => {
                if (!_state?.persona || charName !== _state.charName)
                    return;
                _state.persona.bodyNav = area;
                _refreshBodyNav(pane);
            };
        }
        pane.querySelectorAll('[data-doll-facing]').forEach((btn) => {
            btn.addEventListener('click', () => {
                _setDollFacing(pane, btn.dataset.dollFacing === 'back' ? 'back' : 'front');
            });
        });
        const doll = pane.querySelector('#mind-persona-doll');
        if (doll && !doll._navKeys) {
            doll._navKeys = true;
            doll.addEventListener('keydown', (ev) => {
                if (!_state?.persona || ev.altKey || ev.ctrlKey || ev.metaKey)
                    return;
                if (ev.key === 'f' || ev.key === 'F' || ev.key === 'b' || ev.key === 'B') {
                    ev.preventDefault();
                    _setDollFacing(pane, (ev.key === 'b' || ev.key === 'B') ? 'back' : 'front');
                    return;
                }
                if (ev.key === 'Escape') {
                    if (!_state.persona.bodyNav)
                        return;
                    ev.preventDefault();
                    ev.stopPropagation();
                    _state.persona.bodyNav = null;
                    _refreshBodyNav(pane);
                    return;
                }
                const dir = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' }[ev.key];
                if (!dir)
                    return;
                ev.preventDefault();
                const next = _navNeighbour(pane, dir);
                if (next && next !== _state.persona.bodyNav) {
                    _state.persona.bodyNav = next;
                    _refreshBodyNav(pane);
                }
            });
        }
        _wireBodyNavJumps(pane);
        _wireBodyNavSliders(pane);
        _wireBodyNavMarks(pane);
    }
    function _refreshBodyNav(pane) {
        if (!_state?.persona)
            return;
        const pd = window.InspectorPaperdoll;
        const sel = _state.persona.bodyNav || null;
        const facing = _state.persona.dollFacing === 'back' ? 'back' : 'front';
        const doll = pane.querySelector('#mind-persona-doll');
        if (doll && pd?.renderPaperdollFigureHtml) {
            const player = (worldState.players || {})[_state?.charName || ''];
            doll.innerHTML = pd.renderPaperdollFigureHtml(_state?.charName || '', player || {}, esc, _state?.escName || '', { mode: 'navigate', selectedArea: sel, facing });
        }
        pane.querySelectorAll('[data-doll-facing]').forEach((btn) => {
            const face = btn.dataset.dollFacing;
            btn.classList.toggle('on', face === facing);
        });
        const nav = pane.querySelector('#mind-persona-bodynav');
        if (nav) {
            nav.innerHTML = sel
                ? _bodyNavSideHtml(sel)
                : `<div style="font-size:11px;color:var(--text-muted);">pick a bodypart on the doll - live status, sheet summary, sensitivity, markings. Arrows move · F/B flip · Esc clears.</div>`;
            _wireBodyNavJumps(pane);
            _wireBodyNavSliders(pane);
            _wireBodyNavMarks(pane);
        }
    }
    // The faces' area lists are declared once, in paperdoll-view (AREA_FACE).
    function _navAreas() {
        const pd = window.InspectorPaperdoll;
        const facing = _state?.persona?.dollFacing === 'back' ? 'back' : 'front';
        return typeof pd?.areasForFacing === 'function' ? pd.areasForFacing(facing) : [];
    }
    // Flip the doll. A selection that is not on the new face moves to the
    // first area of that face rather than pointing at a slot nobody can see.
    function _setDollFacing(pane, face) {
        if (!_state?.persona)
            return;
        _state.persona.dollFacing = face;
        const areas = _navAreas();
        const sel = _state.persona.bodyNav;
        if (sel && !areas.includes(sel))
            _state.persona.bodyNav = areas[0] || null;
        _refreshBodyNav(pane);
    }
    // Arrow keys move to the nearest visible slot in that direction, read from
    // the rendered grid, so the key map follows whichever face template is on
    // screen and no layout is declared a second time.
    function _navNeighbour(pane, dir) {
        const slots = Array.from(pane.querySelectorAll('#mind-persona-doll .paperdoll-slot[data-area]'));
        if (!slots.length)
            return null;
        const sel = _state?.persona?.bodyNav || null;
        const cur = slots.find((el) => el.dataset.area === sel);
        if (!cur)
            return slots[0].dataset.area || null;
        const mid = (el) => {
            const r = el.getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        };
        const c = mid(cur);
        let best = null;
        let bestScore = Infinity;
        for (const el of slots) {
            if (el === cur)
                continue;
            const o = mid(el);
            const dx = o.x - c.x;
            const dy = o.y - c.y;
            const ahead = dir === 'right' ? dx : dir === 'left' ? -dx : dir === 'down' ? dy : -dy;
            if (ahead <= 4)
                continue;
            const off = (dir === 'left' || dir === 'right') ? Math.abs(dy) : Math.abs(dx);
            const score = ahead + off * 2;
            if (score < bestScore) {
                bestScore = score;
                best = el.dataset.area || null;
            }
        }
        return best;
    }
    function _wireBodyNavMarks(pane) {
        const add = () => {
            const area = _state?.persona?.bodyNav;
            const input = pane.querySelector('#mind-persona-mark-new');
            if (!area || !input)
                return;
            const text = input.value.trim();
            if (!text)
                return;
            input.value = '';
            const next = _allMarks().filter((raw) => {
                const p = _parseMark(raw);
                return !(p.area === area && p.text === text);
            });
            next.push(_formatMark(area, text));
            _setAllMarks(next);
            _refreshBodyNav(pane);
        };
        pane.querySelector('#mind-persona-mark-add')?.addEventListener('click', add);
        pane.querySelector('#mind-persona-mark-new')?.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter') {
                ev.preventDefault();
                add();
            }
        });
        pane.querySelectorAll('[data-mark-x]').forEach((el) => {
            el.addEventListener('click', () => {
                const raw = el.dataset.markX || '';
                _setAllMarks(_allMarks().filter((m) => m !== raw));
                _refreshBodyNav(pane);
            });
        });
    }
    function _wireBodyNavSliders(pane) {
        pane.querySelectorAll('[data-sens-region]').forEach((el) => {
            el.addEventListener('change', () => {
                const region = el.dataset.sensRegion || '';
                const value = parseInt(el.value, 10) || 0;
                if (!_state || !region)
                    return;
                fetch(`/api/players/${encodeURIComponent(_state.charName)}/body`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sensitivity: { [region]: value / 100 } }),
                }).then(r => r.ok ? r.json() : Promise.reject(new Error(String(r.status))))
                    .then(() => {
                    const player = (worldState.players || {})[_state?.charName || ''];
                    if (player) {
                        player.body_state = player.body_state || {};
                        player.body_state[region] = player.body_state[region] || {};
                        player.body_state[region].sensitivity = value / 100;
                    }
                    _refreshBodyNav(pane);
                }).catch(() => { });
            });
        });
    }
    function _wireBodyNavJumps(pane) {
        pane.querySelectorAll('[data-persona-jump]').forEach((el) => {
            el.addEventListener('click', () => {
                const path = el.dataset.personaJump || '';
                const target = pane.querySelector(`[data-persona-path="${path}"]`)
                    || pane.querySelector(`[data-persona-path^="${path}."]`);
                if (target) {
                    target.scrollIntoView({ block: 'center', behavior: 'smooth' });
                    const box = target.closest('.pf-chips') || target;
                    box.style.boxShadow = '0 0 0 2px rgba(88,166,255,.5)';
                    setTimeout(() => { box.style.boxShadow = ''; }, 1200);
                }
            });
        });
    }
    function _personaBadges() {
        const rec = _state?.persona?.record || {};
        const ident = (rec.identity || {});
        const picks = [
            ['pronouns', ident.pronouns], ['age', ident.age],
            ['gender', ident.gender], ['species', ident.species],
            ['occupation', ident.occupation],
        ];
        const chips = picks
            .filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== '')
            .map(([k, v]) => `<span class="pf-badge">${esc(k)} · ${esc(String(v))}</span>`).join('');
        if (!chips)
            return '';
        return `<div class="pf-badges">${chips}</div>`;
    }
    // task-852 P1: character header - name, one-liner, badges, state chips
    // (✓ saved / ● unsaved / ⚠ uncompiled), actions on the right.
    function _personaStatesHtml() {
        const p = _state?.persona;
        if (!p)
            return '';
        // Both flags already exist: `dirty` is set by an edit to a sheet field and
        // cleared by the post-save re-read; `stale` is the server's
        // persona_prose_stale node flag (prose_stale from GET /record). Compile
        // reads the SAVED block, so an unsaved edit is also uncompiled.
        const bits = [];
        if (p.dirty) {
            bits.push(`<span class="pf-state pf-state-dirty" title="Edits on this sheet are not stored yet. Press save block.">\u25cf unsaved</span>`);
        }
        else {
            bits.push(`<span class="pf-state pf-state-ok" title="The sheet matches the stored block.">\u2713 saved</span>`);
        }
        if (p.dirty || p.stale) {
            const why = p.dirty
                ? 'The sheet changed since the last compile. Save the block first: compile reads the saved block.'
                : 'The block changed since the last compile, so the compiled prose is stale. Press compile to refresh.';
            bits.push(`<span class="pf-state pf-state-stale" title="${esc(why)}">\u26a0 uncompiled</span>`);
        }
        return bits.join('');
    }
    function _personaHeaderHtml() {
        const name = _state ? _state.charName : '';
        const player = (worldState.players || {})[name];
        // One-liner is authored identity prose, never equipment projection.
        const prose = (player?.base_description || '');
        const oneLiner = prose ? esc(prose.split('\n')[0].slice(0, 160)) : '';
        return `<div class="pf-head">
            <div class="pf-head-main">
                <div class="pf-head-name">${esc(name)}</div>
                ${oneLiner ? `<div class="pf-head-prose">${oneLiner}</div>` : ''}
                ${_personaBadges()}
            </div>
            <div class="pf-head-side">
                <div class="pf-states" id="mind-persona-states" role="status" aria-live="polite">${_personaStatesHtml()}</div>
                <div class="pf-actions">
                    <button class="btn btn-sm" id="mind-persona-import" style="font-size:11px;" title="Import a card (.json) or prose (.md/.txt) and convert it to this sheet">📥 import</button>
                    <input type="file" id="mind-persona-file" accept=".json,.md,.txt" style="display:none;">
                    <button class="btn btn-sm" id="mind-persona-save" style="font-size:11px;">💾 save block</button>
                    <button class="btn btn-sm btn-blue" id="mind-persona-compile" style="font-size:11px;" title="Project the block into base_description / personality + tags">⚙ compile</button>
                </div>
            </div>
        </div>`;
    }
    function _personaHtml() {
        const p = _state?.persona;
        if (!p || p.status === 'loading') {
            return `<div style="font-size:11px;color:var(--text-muted);">reading the structured block…</div>`;
        }
        if (p.status === 'error') {
            return `<div style="font-size:11px;color:var(--text-muted);">record unavailable. <button class="btn btn-sm" id="mind-persona-retry" style="font-size:10px;">↻ retry</button></div>`;
        }
        const props = (p.schema?.properties || {});
        const openSet = new Set(p.openSections || []);
        const sections = _PERSONA_SECTIONS.map(([section, label]) => {
            const fields = props[section]?.properties || {};
            const names = Object.keys(fields);
            const filled = names.filter((f) => {
                const v = _personaVal(`${section}.${f}`);
                if (v === undefined || v === null || v === '')
                    return false;
                if (Array.isArray(v))
                    return v.length > 0;
                if (typeof v === 'object')
                    return Object.keys(v).length > 0;
                return true;
            }).length;
            const renderable = (f) => {
                const r = _personaFieldHtml(section, f, fields[f]);
                return r.wide ? `<div class="pf-span">${r.html}</div>` : r.html;
            };
            let inner;
            if (section === 'personality') {
                const plain = names.filter((f) => !_PERSONA_INTIMACY.has(`${section}.${f}`));
                const intimate = names.filter((f) => _PERSONA_INTIMACY.has(`${section}.${f}`));
                inner = `<div class="pf-grid">${plain.map(renderable).join('')}</div>`;
                if (intimate.length) {
                    const iOpen = openSet.has('Intimacy') ? ' open' : '';
                    inner += `<details class="pf-fold pf-intimacy" data-fold="Intimacy"${iOpen}><summary>Intimacy · ${intimate.length} fields</summary><div style="padding:2px 10px 10px;"><div class="pf-grid">${intimate.map(renderable).join('')}</div></div></details>`;
                }
            }
            else {
                // Doll lives in the left workspace column - appearance fold is fields only.
                inner = `<div class="pf-grid">${names.map(renderable).join('')}</div>`;
            }
            const count = names.length;
            // Folds, not a wall: who they are reads at a glance, the
            // depths are one click away. Open state survives re-renders.
            return `<details class="pf-fold" data-fold="${esc(label)}"${openSet.has(label) ? ' open' : ''}>
                <summary>${label} · ${filled}/${count} filled</summary>
                <div style="padding:2px 10px 10px;">${inner}</div>
            </details>`;
        }).join('');
        const preview = p.preview ? `<div style="border:1px solid #1f6feb;border-radius:6px;padding:8px 10px;margin:10px 0;font-size:11px;">
                <div style="font-weight:600;margin-bottom:6px;">Compile preview - hand prose differs</div>
                <div style="margin-bottom:6px;"><div style="color:var(--text-muted);font-size:11px;">BASE NOW</div><div>${esc(p.preview.base_description?.current || '(empty)')}</div>
                <div style="color:var(--text-muted);font-size:11px;margin-top:4px;">BASE COMPILED</div><div>${esc(p.preview.base_description?.compiled || '(empty)')}</div></div>
                <div style="margin-bottom:8px;"><div style="color:var(--text-muted);font-size:11px;">PERSONALITY NOW</div><div>${esc(p.preview.personality?.current || '(empty)')}</div>
                <div style="color:var(--text-muted);font-size:11px;margin-top:4px;">PERSONALITY COMPILED</div><div>${esc(p.preview.personality?.compiled || '(empty)')}</div></div>
                <button class="btn btn-sm" id="mind-persona-confirm" style="font-size:11px;">✓ replace with compiled</button>
                <button class="btn btn-sm" id="mind-persona-cancel" style="font-size:11px;">keep mine</button>
            </div>` : '';
        const msg = p.msg ? `<div style="font-size:11px;color:var(--text-muted);margin-top:8px;">${esc(p.msg)}</div>` : '';
        return `${_personaCss()}
            ${_personaHeaderHtml()}
            <details class="pf-fold" data-fold="Codex"${openSet.has('Codex') ? ' open' : ''}><summary>Codex entry - live preview</summary>
                <div style="padding:2px 10px 10px;"><div class="pf-codex" id="mind-persona-codex">open the fold and type - the compiled entry appears here without storing anything.</div></div>
            </details>
            ${preview}
            <div class="pf-workspace">
                <div class="pf-doll-col">${_bodyNavHtml()}</div>
                <div class="pf-sheet-col">${sections}${msg}</div>
            </div>`;
    }
    // A dirty sheet lives only in the DOM (inputs write nowhere else). Any
    // rebuild of the pane or the whole modal must read the form back into the
    // record first, or the edits vanish while the chip still says unsaved.
    function _syncPersonaFromForm() {
        const p = _state?.persona;
        if (!p || !p.dirty || p.status !== 'ok')
            return;
        if (!_container?.querySelector('#mind-persona [data-persona-path]'))
            return;
        p.record = _collectPersona();
    }
    function _personaRepaint(syncForm = true) {
        if (syncForm)
            _syncPersonaFromForm();
        const el = _container?.querySelector('#mind-persona');
        if (el) {
            el.innerHTML = _personaHtml();
            _wirePersona();
        }
    }
    function _fetchPersona() {
        if (!_state)
            return;
        if (!_state.persona) {
            _state.persona = {
                status: 'loading', record: {}, schema: null, hints: {},
                stale: false, dirty: false, preview: null, msg: '',
                openSections: ['Identity', 'Appearance'], dollFacing: 'front',
            };
        }
        else {
            _state.persona.status = 'loading';
            _state.persona.msg = '';
        }
        fetch(`/api/players/${encodeURIComponent(_state.charName)}/record`, {
            headers: { 'Accept': 'application/json' }
        }).then(r => r.ok ? r.json() : Promise.reject(new Error(String(r.status))))
            .then((data) => {
            if (!_state || !_state.persona)
                return;
            const keepOpen = _state.persona.openSections || ['Identity', 'Appearance'];
            const keepNav = _state.persona.bodyNav;
            const keepFacing = _state.persona.dollFacing || 'front';
            _state.persona = {
                status: 'ok', record: data.record || {},
                schema: data.schema || null, hints: data.hints || {},
                suggestions: data.suggestions || {},
                stale: !!data.prose_stale, dirty: false, preview: null, msg: '',
                openSections: keepOpen, bodyNav: keepNav, dollFacing: keepFacing,
            };
            _personaRepaint();
        })
            .catch(() => {
            if (!_state || !_state.persona)
                return;
            _state.persona.status = 'error';
            _personaRepaint();
        });
    }
    function _collectPersona() {
        const out = {};
        _container?.querySelectorAll('[data-persona-path]').forEach((el) => {
            const path = el.dataset.personaPath || '';
            const parts = path.split('.');
            if (parts.length < 2)
                return;
            const raw = el.value;
            let value = raw;
            const sectionProps = (_state?.persona?.schema?.properties?.[parts[0]]?.properties) || {};
            let decl = sectionProps[parts[1]];
            if (parts.length > 2 && decl?.properties)
                decl = decl.properties[parts[2]];
            if (!decl || decl.type === 'string') {
                value = raw.trim();
            }
            else if (decl.type === 'number' || _PERSONA_NUMBERS.has(parts.slice(0, 2).join('.'))) {
                const trimmed = raw.trim();
                value = trimmed === '' ? undefined : Number(trimmed);
            }
            else if (decl.type === 'array') {
                value = raw.split('\n').map((s) => s.trim()).filter((s) => s);
            }
            else if (decl.type === 'object') {
                value = raw.trim();
            }
            else {
                value = raw.trim();
            }
            if (value === undefined || value === '' || (Array.isArray(value) && !value.length))
                return;
            let cursor = out;
            for (let i = 0; i < parts.length - 1; i++) {
                cursor[parts[i]] = cursor[parts[i]] || {};
                cursor = cursor[parts[i]];
            }
            cursor[parts[parts.length - 1]] = value;
        });
        return out;
    }
    function _personaMsg(text) {
        if (_state?.persona) {
            _state.persona.msg = text;
            _personaRepaint();
        }
    }
    function _savePersona() {
        if (!_state)
            return;
        const record = _collectPersona();
        fetch(`/api/players/${encodeURIComponent(_state.charName)}/record`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ record, render: false }),
        }).then(r => r.json().then((data) => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
            if (!ok) {
                _personaMsg(`save rejected: ${data.error || _shortErr(data)}`);
                return;
            }
            _fetchPersona();
            worldState.fetch();
        })
            .catch((e) => _personaMsg(`save failed: ${String(e)}`));
    }
    function _shortErr(data) {
        try {
            return JSON.stringify(data).slice(0, 160);
        }
        catch {
            return 'unknown error';
        }
    }
    function _compilePersona(force) {
        if (!_state)
            return;
        if (!force && _state.persona?.dirty) {
            _personaMsg('unsaved edits: save the block first. Compile reads the saved block, not the sheet.');
            return;
        }
        fetch(`/api/players/${encodeURIComponent(_state.charName)}/record/compile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(force ? { force: true } : {}),
        }).then(r => r.json().then((data) => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
            if (!ok || !_state?.persona) {
                _personaMsg(`compile rejected: ${data.error || _shortErr(data)}`);
                return;
            }
            if (data.needs_confirm) {
                _state.persona.preview = data.preview;
                _state.persona.msg = '';
                _personaRepaint();
                return;
            }
            _state.persona.preview = null;
            _state.persona.msg = 'compiled - prose + tags projected.';
            _fetchPersona();
            worldState.fetch();
        })
            .catch((e) => _personaMsg(`compile failed: ${String(e)}`));
    }
    let _codexTimer = null;
    function _personaDirty() {
        if (_state?.persona)
            _state.persona.dirty = true;
        const box = _container?.querySelector('#mind-persona-states');
        if (box)
            box.innerHTML = _personaStatesHtml();
    }
    function _chipValues(box) {
        const hidden = box.querySelector('input[type="hidden"]');
        const raw = hidden ? hidden.value : '';
        return raw.split('\n').map((s) => s.trim()).filter((s) => s);
    }
    function _chipPaint(box, values, keepFocus) {
        const hidden = box.querySelector('input[type="hidden"]');
        const input = box.querySelector('.pf-chip-new');
        const path = input?.dataset.chipNew || hidden?.dataset.personaPath || '';
        const tone = (Object.keys(_PERSONA_TONES).find((k) => path.endsWith('.' + k)) || '');
        const cls = tone && _PERSONA_TONES[tone] ? ` ${_PERSONA_TONES[tone]}` : '';
        box.querySelectorAll('.pf-chip').forEach((c) => c.remove());
        for (const v of values) {
            const chip = document.createElement('span');
            chip.className = `pf-chip${cls}`;
            chip.textContent = v;
            const x = document.createElement('b');
            x.textContent = '×';
            x.setAttribute('data-chip-x', path);
            x.setAttribute('data-chip-v', v);
            chip.appendChild(x);
            box.insertBefore(chip, input);
        }
        if (hidden)
            hidden.value = values.join('\n');
        if (keepFocus && input)
            input.focus();
        _personaDirty();
        _scheduleCodex();
    }
    function _scheduleCodex() {
        if (_codexTimer)
            window.clearTimeout(_codexTimer);
        _codexTimer = window.setTimeout(() => { _codexTimer = null; _previewCodex(); }, 800);
    }
    function _previewCodex() {
        if (!_state?.persona || !_container)
            return;
        const box = _container.querySelector('#mind-persona-codex');
        if (!box || !box.closest('details')?.open)
            return;
        const record = _collectPersona();
        if (!Object.keys(record).length) {
            box.innerHTML = `<span style="color:var(--text-muted);">empty sheet - nothing to project.</span>`;
            return;
        }
        fetch(`/api/players/${encodeURIComponent(_state.charName)}/record/compile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ record }),
        }).then(r => r.json().then((data) => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
            const live = _container?.querySelector('#mind-persona-codex');
            if (!live)
                return;
            if (!ok) {
                live.innerHTML = `<span style="color:#e08a92;">cannot project: ${esc(data.error || 'rejected')}</span>`;
                return;
            }
            const c = data.compiled || {};
            live.innerHTML = `${c.base_description ? `<div style="margin-bottom:6px;">${esc(c.base_description)}</div>` : ''}
                    ${c.personality ? `<div style="color:var(--text-dim);">${esc(c.personality)}</div>` : ''}
                    ${(c.interest_tags?.length || c.fear_tags?.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">drawn to ${(c.interest_tags || []).map(esc).join(', ') || '-'} · fears ${(c.fear_tags || []).map(esc).join(', ') || '-'}</div>` : ''}`;
        })
            .catch(() => { });
    }
    function _importPersonaFile(file) {
        if (!_state?.persona)
            return;
        const CI = window.CharacterImport;
        const llm = window.llmClient;
        if (!CI) {
            _personaMsg('importer not loaded - rebuild the frontend.');
            return;
        }
        if (!llm || typeof llm.chat !== 'function') {
            _personaMsg('no model connected - configure one in Settings first.');
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            void (async () => {
                try {
                    const parsed = CI.parseInputFile(String(reader.result ?? ''), file.name);
                    const schema = _state?.persona?.schema;
                    if (!schema) {
                        _personaMsg('schema not loaded - retry the tab.');
                        return;
                    }
                    _personaMsg(`converting ${parsed.kind} “${file.name}”…`);
                    const answer = await llm.chat(CI.buildConvertPrompt(parsed.sourceText, schema), { label: 'persona/import-convert', temperature: 0.2, max_tokens: 4000 });
                    const text = typeof answer === 'string' ? answer
                        : (answer?.content || answer?.message || '');
                    const converted = CI.extractJsonBlock(text);
                    if (!_state?.persona)
                        return;
                    // The form IS the preview: load the conversion for
                    // review, store nothing. Save validates server-side. The
                    // answer is split so the record stays the exact shape
                    // `PUT /record` validates and the model's provenance
                    // drives the ✨ marker instead of riding inside the record.
                    const split = CI.splitConvertAnswer(converted);
                    _state.persona.record = split.record;
                    _state.persona.inferred = split.inferred;
                    _state.persona.preview = null;
                    _state.persona.dirty = true;
                    const notes = [...(parsed.warnings || [])];
                    if (parsed.deterministic?.lorebook?.length) {
                        notes.push(`${parsed.deterministic.lorebook.length} lorebook entries belong in memories, not here`);
                    }
                    const infNote = split.inferred.length
                        ? ` ${split.inferred.length} field(s) inferred - marked ✨, review them.` : '';
                    _state.persona.msg = `imported ${parsed.kind}: review, then save.${infNote}${notes.length ? ' ' + notes.join(' ') : ''}`;
                    _personaRepaint(false);
                }
                catch (e) {
                    _personaMsg(`import failed: ${e instanceof Error ? e.message : String(e)} - nothing stored.`);
                }
            })();
        };
        reader.onerror = () => _personaMsg('could not read that file.');
        reader.readAsText(file);
    }
    function _wirePersona() {
        if (!_container)
            return;
        const on = (sel, fn) => {
            const el = _container?.querySelector(sel);
            if (el)
                el.addEventListener('click', fn);
        };
        on('#mind-persona-retry', () => _fetchPersona());
        on('#mind-persona-save', () => _savePersona());
        on('#mind-persona-import', () => {
            const picker = _container?.querySelector('#mind-persona-file');
            if (picker)
                picker.click();
        });
        const picker = _container?.querySelector('#mind-persona-file');
        if (picker && !picker._wired) {
            picker._wired = true;
            picker.addEventListener('change', () => {
                const file = picker.files && picker.files[0];
                picker.value = '';
                if (file)
                    _importPersonaFile(file);
            });
        }
        on('#mind-persona-compile', () => _compilePersona(false));
        on('#mind-persona-confirm', () => _compilePersona(true));
        on('#mind-persona-cancel', () => {
            if (_state?.persona) {
                _state.persona.preview = null;
                _personaRepaint();
            }
        });
        const pane = _container.querySelector('#mind-persona');
        pane?.querySelectorAll('[data-lock]').forEach((el) => {
            el.addEventListener('click', () => {
                const path = el.dataset.lock || '';
                const body = pane.querySelector(`[data-lockbody="${path}"]`);
                if (body) {
                    const locked = body.classList.toggle('pf-locked');
                    el.textContent = locked
                        ? '🔒 sealed - never compiled to prose. click to reveal.'
                        : '🔓 revealed - still never compiled to prose.';
                }
            });
        });
        pane?.querySelectorAll('[data-chip-x]').forEach((el) => {
            el.addEventListener('click', () => {
                const box = el.closest('.pf-chips');
                if (!box)
                    return;
                const v = el.dataset.chipV || '';
                _chipPaint(box, _chipValues(box).filter((x) => x !== v), true);
            });
        });
        pane?.querySelectorAll('.pf-chip-new').forEach((el) => {
            el.addEventListener('keydown', (ev) => {
                if (ev.key !== 'Enter' && ev.key !== ',')
                    return;
                ev.preventDefault();
                const box = el.closest('.pf-chips');
                if (!box)
                    return;
                const v = el.value.trim().replace(/,+$/, '');
                el.value = '';
                if (!v)
                    return;
                const cur = _chipValues(box);
                if (!cur.includes(v))
                    cur.push(v);
                _chipPaint(box, cur, true);
            });
        });
        // Only sheet fields mark the block dirty. The chip draft box, the mark
        // draft box and the sensitivity sliders carry no data-persona-path
        // (sliders persist on their own through PUT /body).
        const paneFlag = pane;
        if (pane && paneFlag && !paneFlag._pfInput) {
            paneFlag._pfInput = true;
            pane.addEventListener('input', (ev) => {
                const t = ev.target;
                if (!t || !t.closest('[data-persona-path]'))
                    return;
                _personaDirty();
                _scheduleCodex();
            });
        }
        if (pane)
            _wireBodyNav(pane);
        pane?.querySelectorAll('details').forEach((d) => {
            d.addEventListener('toggle', () => {
                const key = d.dataset.fold;
                if (key && _state?.persona) {
                    const set = new Set(_state.persona.openSections || []);
                    if (d.open)
                        set.add(key);
                    else
                        set.delete(key);
                    _state.persona.openSections = [...set];
                }
                if (d.open
                    && d.querySelector('#mind-persona-codex'))
                    _previewCodex();
            });
        });
        if (pane?.querySelector('[data-fold="Codex"]')?.open) {
            _previewCodex();
        }
    }
    // ── shell ────────────────────────────────────────────────────────────
    function _render() {
        if (!_state || !_container)
            return;
        _syncPersonaFromForm();
        const dollHadFocus = document.activeElement?.id === 'mind-persona-doll';
        const all = _memories();
        const visible = _visible(all);
        const selected = all.find((m) => m.id === _state.selectedId) || null;
        const filters = [
            ['all', 'All'], ['episodic', 'Episodic'], ['beliefs', 'Beliefs'],
            ['social', 'Social'], ['procedural', 'Procedural'],
            ['contradicted', '⚡ Contradicted'], ['faded', 'Faded']
        ];
        const filterBtns = filters.map(([key, label]) => {
            const active = _state.filter === key;
            return `<span class="mind-fbtn" data-filter="${key}" style="padding:2px 9px;border:1px solid ${active ? '#1f6feb' : 'var(--border)'};border-radius:11px;font-size:10.5px;color:${active ? '#58a6ff' : 'var(--text-dim)'};background:var(--bg-input);cursor:pointer;">${label}</span>`;
        }).join('');
        const cards = visible.length
            ? visible.slice().reverse().map((m) => _cardHtml(m)).join('')
            : `<div style="font-size:11px;color:var(--text-muted);padding:8px 0;">nothing matches this view.</div>`;
        // task-820: one tabbed mind surface over the existing renderers.
        const tab = _state.tab || 'mind';
        const hdr = 'font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;';
        const tabs = [
            ['mind', 'Mind'], ['persona', 'Persona'],
            ['perception', 'Perception'],
            ['memories', 'Memories'], ['people', 'People'],
        ];
        const tabBar = tabs.map(([key, label]) => {
            const active = tab === key;
            return `<span class="mind-tab" data-tab="${key}" style="padding:5px 12px;border:1px solid ${active ? '#1f6feb' : 'transparent'};border-radius:6px 6px 0 0;font-size:11.5px;color:${active ? '#58a6ff' : 'var(--text-dim)'};background:${active ? 'var(--bg-inset)' : 'transparent'};cursor:pointer;">${label}</span>`;
        }).join('');
        const gridStyle = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:6px 28px;align-items:start;';
        const mindPane = `<div style="flex:1;padding:12px;overflow-y:auto;background:var(--bg-inset);">
            <div style="${gridStyle}">
                <div>${_mosiacHtml()}${_dispositionHtml()}${_actionsHtml()}</div>
                <div><div style="${hdr}">Goals - what they are pursuing</div>
                    <div id="mind-goals">${_goalsHtml()}</div>
                    ${_goalHistoryHtml()}${_obligationsHtml()}${_scheduleHtml()}${_pursuitHtml()}${_planHtml()}${_latestThoughtsHtml()}${_interestTagsHtml()}${_fearTagsHtml()}</div>
            </div></div>`;
        const perceptionPane = `<div style="flex:1;padding:12px;overflow-y:auto;">
            <div style="${gridStyle}">
                <div>${_activityHtml()}${_feelingHtml()}${_emotionEditorHtml()}${_bodyHtml()}${_whatISeeHtml()}</div>
                <div>${_knowledgeHtml()}${_recipesHtml()}</div>
            </div></div>`;
        const memoriesPane = `<div style="flex:1;display:flex;overflow:hidden;">
            <div style="flex:1;padding:12px;overflow-y:auto;min-width:0;">
                ${_timelineHtml(all)}
                ${_memoryToolbarHtml()}
                <div style="display:flex;gap:5px;flex-wrap:wrap;margin:10px 0 8px;align-items:center;">
                    ${filterBtns}
                    <input id="mind-search" placeholder="Search text…" value="${esc(_state.query)}" style="margin-left:auto;background:var(--bg-input);border:1px solid var(--border);border-radius:5px;color:var(--text);padding:3px 8px;font-size:11px;width:160px;">
                </div>
                <div id="mind-list">${cards}</div>
                ${_eventsTimelineHtml()}${_conversationHtml()}
            </div>
            <div style="width:380px;border-left:1px solid var(--border);padding:12px;overflow-y:auto;background:var(--bg-inset);">
                <div style="${hdr}">Memory detail</div>
                <div id="mind-detail">${_detailHtml(selected, all)}</div>
                <div style="margin-top:12px;" id="mind-access">${_accessibilityHtml(all)}</div>
            </div></div>`;
        const peoplePane = `<div style="flex:1;padding:12px;overflow-y:auto;">
            <div style="max-width:640px;">${_relationshipsHtml()}<div style="${hdr}">People - derived from memories</div>
                <div id="mind-people">${_peopleHtml()}</div></div></div>`;
        const personaPane = `<div style="flex:1;padding:16px 20px;overflow-y:auto;">
            <div id="mind-persona">${_personaHtml()}</div></div>`;
        const tabBody = tab === 'perception' ? perceptionPane
            : tab === 'memories' ? memoriesPane
                : tab === 'people' ? peoplePane
                    : tab === 'persona' ? personaPane : mindPane;
        _container.innerHTML = `
        <div style="position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9990;" class="mind-close"></div>
        <div style="position:fixed;top:4vh;left:50%;transform:translateX(-50%);width:min(1360px,96vw);height:90vh;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:9991;display:flex;flex-direction:column;overflow:hidden;">
            <div style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border);background:var(--bg-inset);flex-wrap:wrap;">
                <h3 style="margin:0;font-size:14px;">🧠 Mind - ${esc(_state.charName)}</h3>
                <div style="display:flex;gap:6px;flex-wrap:wrap;flex:1;">${_statsHtml(all)}</div>
                <button class="btn btn-sm mind-refresh" style="font-size:10px;" title="Re-read the character's memories">🔄</button>
                <button class="btn btn-sm mind-close" style="font-size:10px;">✕</button>
            </div>
            <div style="display:flex;gap:2px;padding:6px 16px 0;border-bottom:1px solid var(--border);background:var(--bg-card);flex-wrap:wrap;">
                ${tabBar}
            </div>
            <div style="flex:1;overflow:hidden;display:flex;">
                ${tabBody}
            </div>
        </div>`;
        // wiring
        _container.querySelectorAll('.mind-close').forEach(el => el.addEventListener('click', () => M.close()));
        _container.querySelectorAll('.mind-tab').forEach(el => el.addEventListener('click', () => { if (_state) {
            _state.tab = el.dataset.tab || 'mind';
            _render();
        } }));
        // task-756: per-memory emotion editing lives here, not in the memory modal.
        const emoBox = _container.querySelector('#mind-mem-emotions');
        if (emoBox && selected) {
            const IM = window.InspectorMemory;
            const initial = Array.isArray(selected.memory_emotions) && selected.memory_emotions.length
                ? selected.memory_emotions
                : (selected.emotion && selected.emotion.label ? [selected.emotion] : []);
            if (IM && IM._attachEmotionSelector)
                IM._attachEmotionSelector(emoBox, initial);
            const saveEmo = _container.querySelector('.mind-mem-emo-save');
            if (saveEmo)
                saveEmo.addEventListener('click', async () => {
                    if (!_state)
                        return;
                    const emotions = Array.isArray(IM?._emoSelected) ? IM._emoSelected : [];
                    const payload = { memory_emotions: emotions };
                    if (emotions.length)
                        payload.emotion = emotions[0];
                    await ApiClient.updatePlayerMemory(_state.charName, selected.id, payload);
                    await worldState.fetch();
                    _render();
                });
        }
        // task-821: the GIMP goal editor lives in the Mind panel. Delegated, so a
        // row added after a render is still wired and nothing binds twice.
        const goalsBox = _container.querySelector('#mind-goals');
        if (goalsBox) {
            goalsBox.addEventListener('focusout', () => _saveGoals());
            goalsBox.addEventListener('change', () => _saveGoals());
            goalsBox.addEventListener('click', (ev) => {
                const del = ev.target.closest('.mind-goal-del');
                if (del) {
                    del.closest('.mind-goal')?.remove();
                    _saveGoals();
                    return;
                }
                if (ev.target.closest('.mind-add-goal')) {
                    const empty = goalsBox.querySelector('.mind-goal-empty');
                    if (empty)
                        empty.remove();
                    goalsBox.insertAdjacentHTML('afterbegin', _goalRowHtml({}));
                    goalsBox.querySelector('.mind-goal-what')?.focus();
                }
            });
        }
        // task-787: interest/fear tag multiselects and the knowledge chips, moved
        // out of the Bio / Advanced tabs. Same stores, same handlers.
        const TM = window.TagMultiselect;
        const migPlayer = _state ? worldState.players?.[_state.charName] : null;
        if (TM && migPlayer) {
            const itBox = _container.querySelector(`#interest-tag-multiselect-mind-${_safeId()}`);
            if (itBox)
                new TM(itBox, {
                    tags: Array.isArray(migPlayer.interest_tags) ? migPlayer.interest_tags : [],
                    appliesTo: 'characters', allowNew: true, placeholder: 'e.g. magic, food, documents...',
                    onChange: (tags) => { ApiClient.updateCharacter(_state.charName, { interest_tags: tags }).then(() => worldState.fetch()); }
                });
            const ftBox = _container.querySelector(`#fear-tag-multiselect-mind-${_safeId()}`);
            if (ftBox)
                new TM(ftBox, {
                    tags: Array.isArray(migPlayer.fear_tags) ? migPlayer.fear_tags : [],
                    appliesTo: 'characters', allowNew: true, placeholder: 'e.g. goblin, the dark, magic...',
                    onChange: (tags) => { ApiClient.updateCharacter(_state.charName, { fear_tags: tags }).then(() => worldState.fetch()); }
                });
        }
        const KB = window.KnownBySection;
        const kbBox = _container.querySelector(`#mind-knowledge-chips-${_safeId()}`);
        if (KB && kbBox && _state)
            kbBox.appendChild(KB.buildKnownChips(_state.charName));
        // task-729: the relationship editor reuses agent-view's binder (same
        // selectors, same store); the emotion control writes the same
        // `{ emotion: { current, intensity } }` payload as the header row.
        const AV = window.InspectorAgentView;
        if (AV && AV._bindRelationshipSliders && _state)
            AV._bindRelationshipSliders(_container, _state.charName);
        _container.querySelectorAll('.mind-rel-del').forEach(el => el.addEventListener('click', () => {
            if (!_state)
                return;
            const other = el.dataset.other || '';
            if (other && AV && AV._removeRelationship)
                AV._removeRelationship(el.dataset.agent || _state.charName, other);
        }));
        const emoSel = _container.querySelector('#mind-emotion');
        const emoRange = _container.querySelector('#mind-emotion-intensity');
        const emoVal = _container.querySelector('#mind-emotion-val');
        if (emoSel && emoRange && _state) {
            // Save on release, not on every drag step: the worldState update the
            // save triggers re-renders this panel, which would move the thumb.
            emoRange.addEventListener('input', () => { if (emoVal)
                emoVal.textContent = (parseFloat(emoRange.value) || 0).toFixed(2); });
            const saveEmotion = () => ApiClient.updateCharacter(_state.charName, { emotion: { current: emoSel.value, intensity: parseFloat(emoRange.value) || 0 } }).then(() => worldState.fetch());
            emoSel.addEventListener('change', saveEmotion);
            emoRange.addEventListener('change', saveEmotion);
        }
        _container.querySelectorAll('.mind-fbtn').forEach(el => el.addEventListener('click', () => { if (_state) {
            _state.filter = el.dataset.filter || 'all';
            _render();
        } }));
        _container.querySelectorAll('.mind-card').forEach(el => el.addEventListener('click', () => { if (_state) {
            _state.selectedId = el.dataset.id || '';
            _render();
        } }));
        _container.querySelectorAll('.mind-dot').forEach(el => el.addEventListener('click', () => { if (_state) {
            _state.selectedId = el.dataset.id || '';
            _render();
        } }));
        _container.querySelectorAll('.mind-conn').forEach(el => el.addEventListener('click', () => { if (_state) {
            _state.selectedId = el.dataset.id || '';
            _render();
        } }));
        _container.querySelectorAll('.mind-person').forEach(el => el.addEventListener('click', () => {
            if (!_state)
                return;
            const person = 'person:' + (el.dataset.person || '');
            _state.filter = _state.filter === person ? 'all' : person;
            _render();
        }));
        const refresh = _container.querySelector('.mind-refresh');
        if (refresh)
            refresh.addEventListener('click', () => { _fetchPeople(); _fetchPersona(); _fetchRecipes(); _render(); });
        _wirePersona();
        // A rebuild drops focus; keep keyboard navigation alive on the doll.
        if (dollHadFocus)
            _container.querySelector('#mind-persona-doll')?.focus({ preventScroll: true });
        if (_container.querySelector('#mind-recipes'))
            _fetchRecipes();
        const search = _container.querySelector('#mind-search');
        if (search) {
            search.addEventListener('input', () => {
                if (_state) {
                    _state.query = search.value;
                    const list = _container?.querySelector('#mind-list');
                    const all2 = _memories();
                    if (list)
                        list.innerHTML = (_visible(all2).length
                            ? _visible(all2).slice().reverse().map((m) => _cardHtml(m)).join('')
                            : `<div style="font-size:11px;color:var(--text-muted);padding:8px 0;">nothing matches this view.</div>`);
                    _wireList();
                }
            });
        }
    }
    function _wireList() {
        if (!_container)
            return;
        _container.querySelectorAll('.mind-card').forEach(el => el.addEventListener('click', () => { if (_state) {
            _state.selectedId = el.dataset.id || '';
            _render();
        } }));
    }
    function _fetchPeople() {
        if (!_state)
            return;
        _state.peopleStatus = 'loading';
        fetch(`/api/players/${encodeURIComponent(_state.charName)}/memories/people`, {
            headers: { 'Accept': 'application/json' }
        }).then(r => r.ok ? r.json() : Promise.reject(new Error(String(r.status))))
            .then((data) => {
            if (!_state)
                return;
            _state.people = data.people || [];
            _state.peopleStatus = 'ok';
            const el = _container?.querySelector('#mind-people');
            if (el)
                el.innerHTML = _peopleHtml();
        })
            .catch(() => {
            if (!_state)
                return;
            _state.peopleStatus = 'error';
            const el = _container?.querySelector('#mind-people');
            if (el)
                el.innerHTML = _peopleHtml();
        });
    }
    const M = {
        /**
         * Open the Memory Mind for a character. A snapshot of the live
         * worldState memories; 🔄 re-reads.
         */
        open(charName) {
            const player = worldState.players?.[charName];
            if (!player)
                return;
            M.close();
            _container = document.createElement('div');
            _container.id = 'mind-view-modal';
            document.body.appendChild(_container);
            _ensureSubscribed();
            _state = {
                charName,
                escName: charName.replace(/'/g, "\\'"),
                tab: 'mind',
                filter: 'all',
                query: '',
                selectedId: '',
                people: [],
                peopleStatus: 'loading',
                persona: null,
            };
            _render();
            _fetchPeople();
            _fetchPersona();
        },
        close() {
            if (_container) {
                _container.remove();
                _container = null;
            }
            _state = null;
        },
        // Test helpers
        _parseMark,
        _formatMark,
        _allMarks,
        _PERSONA_TEXTAREAS,
        _PERSONA_TONES,
    };
    return M;
})();
window.InspectorMindView = InspectorMindView;
