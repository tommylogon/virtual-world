/**
 * InspectorMindView — the Memory Mind dashboard (task-691 stage 4).
 *
 * A full-surface view of one character's memory dynamics, the wired version of
 * docs/design/memory-mockup.html: timeline ribbon, category filters, dynamics
 * badges, a memory detail pane with connections (contradicts / derived-from /
 * same-entity), per-person derived profiles from the /memories/people endpoint
 * (engine/derive.py — the same numbers the prompt sees), and an accessibility
 * panel showing current activation (what decay is working on right now).
 *
 * Reads ONLY existing state: worldState memories + the people endpoint. Every
 * number shown is a field the backend wrote or a value derive.py computes —
 * no decorative data.
 *
 * @module inspector/mind-view — the character's memory mind (dashboard)
 * @contributes InspectorMindView.open(charName): full-surface memory dashboard
 * @powers Node inspectors, Memory — inspecting and correcting what a character remembers
 * @relates complements inspector/memory-view (the editor); reads /api/players/<n>/memories/people
 * @docs docs/virtualWorld/AI & Narration/Memory Dynamics.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

/** Category of a memory, derived the same way memory-view and the recall
 *  block derive it for pre-dynamics entries. */
function _catOf(m: any): string {
    if (m.category) return String(m.category);
    if (String(m.type || '') === 'reflection') return 'belief';
    const tags = Array.isArray(m.tags) ? m.tags.map((t: any) => String(t).toLowerCase()) : [];
    if (tags.some((t: string) => t.startsWith('rel:'))) return 'social';
    return 'episodic';
}

const CAT_COLORS: Record<string, string> = {
    episodic: '#58a6ff', semantic: '#39c5cf', belief: '#bc8cff',
    social: '#f778ba', procedural: '#d29922'
};

interface MindPerson {
    name: string;
    memory_count: number;
    profile: {
        trust?: number; fear?: number; attraction?: number; disgust?: number;
        respect?: number; familiarity?: number; consent?: number;
        role?: string; summary?: string; has_signal?: boolean;
    };
}

interface MindState {
    charName: string;
    escName: string;
    tab: string;             // mind | perception | memories | people
    filter: string;          // all | episodic | beliefs | social | procedural | contradicted | faded | person:<Name>
    query: string;
    selectedId: string;
    people: MindPerson[];
    peopleStatus: 'loading' | 'ok' | 'error';
}

let _state: MindState | null = null;
let _container: HTMLElement | null = null;

const InspectorMindView = (() => {
    'use strict';

    const esc = (value: unknown): string => {
        const s = String(value ?? '');
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    };
    const act = (m: any): number => (typeof m.activation === 'number' ? m.activation : 1);
    const conf = (m: any): number => (typeof m.confidence === 'number' ? m.confidence : (String(m.source) === 'manual' || String(m.source) === 'preconceived' ? 1 : 0.7));

    function _memories(): any[] {
        if (!_state) return [];
        return worldState.players?.[_state.charName]?.memories || [];
    }

    function _visible(memories: any[]): any[] {
        if (!_state) return [];
        const f = _state.filter;
        const q = _state.query.toLowerCase().trim();
        return memories.filter((m: any) => {
            if (f === 'episodic' && _catOf(m) !== 'episodic') return false;
            if (f === 'beliefs' && !['belief', 'semantic'].includes(_catOf(m))) return false;
            if (f === 'social' && _catOf(m) !== 'social') return false;
            if (f === 'procedural' && _catOf(m) !== 'procedural') return false;
            if (f === 'contradicted' && !(Array.isArray(m.contradicts) && m.contradicts.length)) return false;
            if (f === 'faded' && !(act(m) < 0.5)) return false;
            if (f.startsWith('person:')) {
                const who = f.slice(7).toLowerCase();
                const tags = (Array.isArray(m.tags) ? m.tags : []).map((t: any) => String(t).toLowerCase());
                if (!tags.includes('rel:' + who)) return false;
            }
            if (q && !String(m.text || '').toLowerCase().includes(q)) return false;
            return true;
        });
    }

    // ── pieces ───────────────────────────────────────────────────────────
    function _statsHtml(memories: any[]): string {
        const n = (pred: (m: any) => boolean) => memories.filter(pred).length;
        const epis = n((m: any) => _catOf(m) === 'episodic');
        const beliefs = n((m: any) => ['belief', 'semantic'].includes(_catOf(m)));
        const social = n((m: any) => _catOf(m) === 'social');
        const proc = n((m: any) => _catOf(m) === 'procedural');
        const contra = n((m: any) => Array.isArray(m.contradicts) && m.contradicts.length);
        const faded = n((m: any) => act(m) < 0.5);
        const reinf = memories.reduce((a: number, m: any) => a + (Number(m.reinforcements) || 0), 0);
        const avgConf = memories.length ? Math.round(memories.reduce((a: number, m: any) => a + conf(m), 0) / memories.length * 100) : 100;
        const chip = (num: number | string, label: string, color?: string): string =>
            `<div class="mstat" style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:4px 10px;text-align:center;min-width:64px;">
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

    function _timelineHtml(memories: any[]): string {
        const ticks = memories.map((m: any) => Number(m.tick) || 0);
        const min = Math.min(0, ...ticks);
        const max = Math.max(1, ...ticks);
        const W = 760, H = 64, PAD = 18;
        const span = Math.max(1, max - min);
        const dots = memories.map((m: any) => {
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
        const marks = [0, 0.25, 0.5, 0.75, 1].map(p =>
            `<text x="${(PAD + p * (W - 2 * PAD)).toFixed(0)}" y="${H - 6}" fill="#6e7681" font-size="8" text-anchor="middle" font-family="monospace">${esc(Math.round(min + p * span))}</text>`).join('');
        return `<svg width="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;">
            <line x1="${PAD}" y1="${H / 2}" x2="${W - PAD}" y2="${H / 2}" stroke="#30363d" stroke-width="2"/>${marks}${dots}</svg>
            <div style="font-size:9px;color:var(--text-muted);margin-top:3px;">position = tick · size = importance · red ring = contradicted · click a dot to select</div>`;
    }

    function _badge(label: string, color: string, title?: string): string {
        return `<span style="font-size:9px;padding:1px 6px;border-radius:8px;border:1px solid ${color};color:${color};${title ? '' : ''}" ${title ? `title="${esc(title)}"` : ''}>${esc(label)}</span>`;
    }

    function _cardHtml(m: any): string {
        const cat = _catOf(m);
        const imp = Number(m.importance) || 5;
        const impColor = imp >= 8 ? '#e05555' : imp >= 6 ? '#e0a33c' : imp >= 4 ? '#4caf50' : '#888';
        const selected = _state && _state.selectedId === m.id;
        const faded = act(m) < 0.5;
        const badges: string[] = [
            _badge(cat, CAT_COLORS[cat] || '#8b949e'),
        ];
        if (typeof m.confidence === 'number' || String(m.source) === 'manual') {
            const c = Math.round(conf(m) * 100);
            badges.push(_badge(`conf ${c}%`, c < 50 ? '#d29922' : '#8b949e', 'how sure the character is'));
        }
        const reinf = Number(m.reinforcements) || 0;
        if (reinf > 0) badges.push(_badge(`↻ ×${reinf}`, '#4caf50', 'reinforced by recall or re-encounter'));
        const contra = Array.isArray(m.contradicts) ? m.contradicts.length : 0;
        if (contra > 0) badges.push(_badge(`⚡ ${contra}`, '#e05555', `conflicts with ${contra} other memor${contra === 1 ? 'y' : 'ies'}`));
        if (Number(m.reflection_depth) > 0) badges.push(_badge(`depth ${m.reflection_depth}`, '#bc8cff', `derived memory (from ${Array.isArray(m.source_memory_ids) ? m.source_memory_ids.length : '?'} source memories)`));
        if (String(m.source) === 'manual') badges.push(_badge('SEED', '#39c5cf'));
        return `<div class="mind-card" data-id="${esc(m.id)}" style="background:var(--bg-card);border:1px solid ${selected ? '#1f6feb' : 'var(--border)'};border-left:3px solid ${impColor};border-radius:6px;padding:7px 9px;margin-bottom:6px;font-size:11px;cursor:pointer;${faded ? 'opacity:0.55;' : ''}">
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                <span style="color:var(--text-dim);font-size:10px;font-family:monospace;">[${esc(m.tick ?? 0)}]</span>
                ${badges.join('')}
                <span style="margin-left:auto;font-size:10px;color:${impColor};font-weight:600;">⭐ ${imp}</span>
            </div>
            <div style="margin-top:3px;line-height:1.4;">${esc(m.text || '')}</div>
        </div>`;
    }

    function _bar(label: string, value: number, max: number, color: string, center = false): string {
        const pct = Math.max(0, Math.min(1, Math.abs(value) / max)) * 100;
        const fill = center
            ? `<div style="height:100%;width:${(pct / 2).toFixed(1)}%;background:${color};margin-left:50%;"></div>`
            : `<div style="height:100%;width:${pct.toFixed(1)}%;background:${color};"></div>`;
        return `<div style="display:flex;align-items:center;gap:6px;font-size:10.5px;margin:3px 0;">
            <span style="width:62px;color:var(--text-dim);">${esc(label)}</span>
            <div style="flex:1;height:7px;background:var(--bg-input);border-radius:3px;overflow:hidden;position:relative;${center ? '' : ''}">${center ? '<div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border);"></div>' : ''}${fill}</div>
            <span style="width:34px;text-align:right;font-family:monospace;font-size:10px;color:var(--text-dim);">${esc(Math.round(value * 100) / 100)}</span></div>`;
    }

    function _detailHtml(m: any | null, all: any[]): string {
        if (!m) return `<div style="font-size:11px;color:var(--text-muted);">Select a memory to see its dynamics and connections.</div>`;
        const cat = _catOf(m);
        const emoList = Array.isArray(m.memory_emotions) && m.memory_emotions.length
            ? m.memory_emotions
            : (m.emotion && m.emotion.label ? [m.emotion] : []);
        const byId = (id: string) => all.find((x: any) => x.id === id);
        const contraRows = (Array.isArray(m.contradicts) ? m.contradicts : []).map((id: string) => {
            const other = byId(id);
            return `<div class="mind-conn" data-id="${esc(id)}" style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid var(--border-light);font-size:10.5px;cursor:pointer;">
                <span style="font-family:monospace;font-size:9px;color:var(--text-muted);min-width:46px;">${esc(other?.tick ?? '?')}</span>
                <span style="color:#e05555;">contradicts</span>
                <span style="color:var(--text-dim);flex:1;">${esc(other ? String(other.text).slice(0, 70) : id)}</span></div>`;
        }).join('');
        const derivedRows = (Array.isArray(m.source_memory_ids) ? m.source_memory_ids : []).map((id: string) => {
            const other = byId(id);
            return `<div class="mind-conn" data-id="${esc(id)}" style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid var(--border-light);font-size:10.5px;cursor:pointer;">
                <span style="font-family:monospace;font-size:9px;color:var(--text-muted);min-width:46px;">${esc(other?.tick ?? '?')}</span>
                <span style="color:#bc8cff;">derived from</span>
                <span style="color:var(--text-dim);flex:1;">${esc(other ? String(other.text).slice(0, 70) : id)}</span></div>`;
        }).join('');
        const entityIds = (Array.isArray(m.entity_ids) ? m.entity_ids : []).map((e: any) => String(e));
        const siblings = entityIds.length
            ? all.filter((x: any) => x.id !== m.id && (x.entity_ids || []).some((e: any) => entityIds.includes(String(e)))).slice(0, 5)
            : [];
        const sibRows = siblings.map((other: any) =>
            `<div class="mind-conn" data-id="${esc(other.id)}" style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid var(--border-light);font-size:10.5px;cursor:pointer;">
                <span style="font-family:monospace;font-size:9px;color:var(--text-muted);min-width:46px;">${esc(other.tick ?? '?')}</span>
                <span style="color:var(--text-muted);">same entity</span>
                <span style="color:var(--text-dim);flex:1;">${esc(String(other.text || '').slice(0, 70))}</span></div>`).join('');
        const relTags = (Array.isArray(m.tags) ? m.tags : []).filter((t: any) => String(t).toLowerCase().startsWith('rel:'));
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
                ${emoList.map((e: any) => _bar(String(e.label || ''), (Number(e.intensity) || 0) / 10, 1, '#e0a33c')).join('')}
            </div>` : ''}
            ${(contraRows || derivedRows || sibRows) ? `<div style="background:var(--bg-inset);border:1px solid var(--border);border-radius:5px;padding:8px 10px;margin-bottom:8px;">
                <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Connections</div>
                ${contraRows}${derivedRows}${sibRows}
            </div>` : ''}
            ${relTags.length ? `<div style="font-size:10px;color:var(--f788ba, #f778ba);margin-bottom:8px;">${relTags.map((t: any) => _badge(String(t), '#f778ba')).join(' ')}</div>` : ''}
            <div style="background:var(--bg-inset);border:1px solid var(--border);border-radius:5px;padding:8px 10px;margin-bottom:8px;">
                <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Feelings - edit</div>
                <div id="mind-mem-emotions"></div>
                <button class="btn btn-sm mind-mem-emo-save" style="font-size:10px;margin-top:6px;">💾 Save feelings</button>
            </div>
            ${editBtn}
        </div>`;
    }

    function _accessibilityHtml(all: any[]): string {
        if (!all.length) return '';
        const sorted = [...all].sort((a: any, b: any) => act(a) - act(b)).slice(0, 7);
        const faded = all.filter((m: any) => act(m) < 0.5).length;
        const row = (m: any): string => {
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
            <div style="font-size:9px;color:var(--text-muted);margin-top:4px;line-height:1.5;">Recall (↻) raises activation; decay lowers it every tick at a rate each memory resists differently. Every memory is kept for life — decay lowers how likely it is to be recalled, it never forgets one.</div>
        </div>`;
    }

    function _goals(): any[] {
        if (!_state) return [];
        return worldState.players?.[_state.charName]?.goals || [];
    }

    function _goalStatusColor(status: string): string {
        switch (status) {
            case 'active': return '#58a6ff';
            case 'reached': return '#4caf50';
            case 'blocked': return '#e05555';
            case 'dropped': return '#6e7681';
            default: return '#d29922';   // proposed
        }
    }

    function _goalRowHtml(g: any): string {
        const inputStyle = 'font-size:10.5px;background:var(--bg-input);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:2px 6px;';
        const statuses = ['proposed', 'active', 'reached', 'blocked', 'dropped'];
        const color = _goalStatusColor(String(g.status || 'proposed'));
        const val = (s: any) => esc(String(s ?? ''));
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

    function _goalsHtml(): string {
        const goals = _goals();
        const body = goals.length
            ? goals.map((g: any) => _goalRowHtml(g)).join('')
            : `<div class="mind-goal-empty" style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">no goals - driven only by needs right now.</div>`;
        return `${body}<button class="btn btn-sm mind-add-goal" style="font-size:10px;">➕ Add goal</button>`;
    }

    function _collectGoals(): any[] {
        const box = _container?.querySelector('#mind-goals');
        if (!box) return [];
        return Array.from(box.querySelectorAll('.mind-goal')).map((row: any) => ({
            what: (row.querySelector('.mind-goal-what')?.value || '').trim(),
            status: row.querySelector('.mind-goal-status')?.value || 'proposed',
            motivation: (row.querySelector('.mind-goal-motivation')?.value || '').trim(),
            intention: (row.querySelector('.mind-goal-intention')?.value || '').trim(),
            blocks: (row.querySelector('.mind-goal-blocks')?.value || '').trim(),
        })).filter((g: any) => g.what);
    }

    async function _saveGoals(): Promise<void> {
        if (!_state) return;
        await ApiClient.updateCharacter(_state.charName, { goals: _collectGoals() });
        await worldState.fetch();
    }

    function _goalHistory(): any[] {
        if (!_state) return [];
        return worldState.players?.[_state.charName]?.goal_log || [];
    }

    function _goalHistoryHtml(): string {
        const log = _goalHistory();
        if (!log.length) return '';
        const rows = log.slice().reverse().map((e: any) => {
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

    function _obligations(): any[] {
        if (!_state) return [];
        return worldState.players?.[_state.charName]?.obligations || [];
    }

    function _obligationColor(status: string): string {
        switch (status) {
            case 'offered': return '#d29922';
            case 'accepted': return '#58a6ff';
            case 'done': return '#4caf50';
            default: return '#6e7681';   // refused / forgotten
        }
    }

    function _obligationsHtml(): string {
        const obligations = _obligations();
        if (!obligations.length) return '';
        const rows = obligations.map((o: any) => {
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

    function _schedule(): any[] {
        if (!_state) return [];
        return worldState.players?.[_state.charName]?.schedule || [];
    }

    function _hhmm(minutes: any): string {
        const m = (Number(minutes) || 0) % 1440;
        return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
    }

    function _scheduleHtml(): string {
        const steps = _schedule();
        if (!steps.length) return '';
        const rows = steps.map((s: any) => `<div style="display:flex;gap:8px;align-items:baseline;font-size:10.5px;padding:2px 0;border-bottom:1px solid var(--border-light);">
            <span style="font-family:monospace;color:var(--text-muted);min-width:34px;">${_hhmm(s.start)}</span>
            <span style="color:var(--text);">${esc(s.activity || '')}</span>
            ${s.area ? `<span style="color:var(--text-dim);">at ${esc(s.area)}</span>` : ''}
        </div>`).join('');
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Schedule - their day</div>
            ${rows}
        </div>`;
    }

    function _activePursuit(): any {
        if (!_state) return null;
        return worldState.players?.[_state.charName]?.active_pursuit || null;
    }

    function _plan(): any {
        if (!_state) return null;
        return worldState.players?.[_state.charName]?.plan || null;
    }

    function _stepLabel(step: any): string {
        if (!step) return '-';
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
    function _pursuitHtml(): string {
        const pursuit = _activePursuit();
        const plan = _plan();
        if (!pursuit && !plan) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">no assigned pursuit - needs and goals only right now.</div>`;
        }
        const rows: string[] = [];
        if (pursuit) {
            rows.push(`<div style="display:flex;align-items:center;gap:6px;">
                <b style="font-size:11.5px;line-height:1.35;">${esc(pursuit.label || pursuit.template_id || '')}</b>
                <span style="font-size:9px;color:var(--text-muted);margin-left:auto;">${esc(pursuit.template_id || '')}</span>
            </div>`);
            if (pursuit.reason) rows.push(`<div style="font-size:9.5px;color:var(--text-muted);margin-top:3px;line-height:1.45;">${esc(pursuit.reason)}</div>`);
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

    function _activityHtml(): string {
        if (!_state) return '';
        const a: any = worldState.players?.[_state.charName]?.activity;
        if (!a || !a.type) return '';
        const parts: string[] = [];
        if (a.elapsed_minutes != null) parts.push(`${Math.round(Number(a.elapsed_minutes))} min`);
        if (a.duration_minutes != null) parts.push(`of ${Math.round(Number(a.duration_minutes))} min`);
        if (a.catch_count != null) parts.push(`caught ${a.catch_count}`);
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Activity - what is underway</div>
            <div style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid #3fb950;border-radius:6px;padding:7px 9px;">
                <b style="font-size:11.5px;">${esc(a.type)}</b>
                ${parts.length ? `<span style="font-size:9.5px;color:var(--text-muted);margin-left:6px;">${esc(parts.join(' / '))}</span>` : ''}
            </div>
        </div>`;
    }

    function _feelingHtml(): string {
        if (!_state) return '';
        const p: any = worldState.players?.[_state.charName];
        if (!p) return '';
        const emo: any = p.emotion || null;
        const axes = (p.emotions && typeof p.emotions === 'object') ? p.emotions : {};
        const raised = Object.entries(axes)
            .map(([axis, amt]) => [axis, Number(amt)] as [string, number])
            .sort((a, b) => b[1] - a[1]).slice(0, 5);
        const current = emo && emo.current && emo.current !== 'neutral' ? emo.current : '';
        if (!current && !raised.length) return '';
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
        const mems: any[] = Array.isArray(p.memories) ? p.memories : [];
        let lastFeeling: any = null;
        for (const mem of mems) {
            const labels = (Array.isArray(mem.memory_emotions) && mem.memory_emotions.length
                ? mem.memory_emotions
                : (mem.emotion && mem.emotion.label ? [mem.emotion] : []))
                .map((e: any) => String(e.label || '').toLowerCase());
            if (!labels.length) continue;
            if (current && !labels.includes(String(current).toLowerCase())) continue;
            if (!lastFeeling || (Number(mem.tick) || 0) > (Number(lastFeeling.tick) || 0)) lastFeeling = mem;
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
    function _bodyHtml(): string {
        if (!_state) return '';
        const p: any = worldState.players?.[_state.charName];
        if (!p) return '';
        const state = String(p.state || 'awake');
        const instances: any = p.conditions || {};
        const condRows: string[] = [];
        for (const [cid, list] of Object.entries(instances)) {
            if (cid === 'awake') continue;
            const arr = Array.isArray(list) ? list : [];
            for (const c of arr) {
                const bits: string[] = [];
                if (c && c.source) bits.push(`why: ${esc(c.source)}`);
                if (c && c.duration != null) bits.push(`left: ${esc(c.duration)}t`);
                if (c && c.level) bits.push(`lvl ${esc(c.level)}`);
                condRows.push(`<div style="font-size:10.5px;padding:2px 0;border-bottom:1px solid var(--border-light);"><b style="color:#e05555;">${esc(cid)}</b>${bits.length ? ` <span style="color:var(--text-muted);">${bits.join(' / ')}</span>` : ''}</div>`);
            }
        }
        const VW: any = window as any;
        const vitals = p.vitals || {};
        // The core vitals the header row renders. Optional scenario vitals
        // (Arousal / Pleasure / Stimulation) sit at 0 when their system is off
        // and would read as "low" for every character, so they are not drivers.
        const CORE: string[] = ['HP', 'Energy', 'Hunger', 'Thirst', 'Bladder', 'Temperature', 'Sanity', 'Social', 'Entertainment', 'Hygiene'];
        const out = CORE
            .filter((n) => vitals[n] !== undefined)
            .map((n) => ({ n, lvl: String(VW.VitalColor?.level?.(vitals, n) || 'ok') }))
            .filter((x) => x.lvl !== 'ok');
        const vitalRows = out.map(({ n, lvl }) => {
            const color = lvl === 'critical' || lvl === 'bad' ? '#e05555' : '#e0a33c';
            return `<div style="font-size:10.5px;padding:2px 0;"><b style="color:${color};">${esc(n)} ${esc(vitals[n])}</b> <span style="color:var(--text-muted);">${esc(lvl)}</span></div>`;
        });
        const stateBad = state !== 'awake';
        if (!stateBad && !condRows.length && !vitalRows.length) return '';
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
    function _safeId(): string {
        return String(_state ? _state.charName : '').replace(/[^a-zA-Z0-9_-]/g, '_');
    }

    /** Is an AI provider configured? Mirrors agent-view's side-effect-free read. */
    function _isAiReady(): boolean {
        const AV: any = (window as any).InspectorAgentView;
        return !!(AV && AV._isAiConfigured && AV._isAiConfigured());
    }

    function _interestTagsHtml(): string {
        if (!_state) return '';
        const AI = _isAiReady();
        const suffix = AI ? '' : ' - No AI provider configured. Add an API key and model in Settings first.';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Interest tags - what they notice</div>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Items matching these surface in the agent's prompt. Examine/take removes them from attention.</div>
            <div id="interest-tag-multiselect-mind-${_safeId()}"></div>
            <button class="btn btn-sm" ${AI ? '' : 'disabled'} onclick="InspectorAgentView._generateInterestTags('${_state.escName}')" style="font-size:10px;padding:2px 10px;margin-top:4px;" title="Ask the character's LLM to pick interest tags. Your hand-placed tags are kept - picks are added.${suffix}">✨ Generate from Personality</button>
        </div>`;
    }

    function _fearTagsHtml(): string {
        if (!_state) return '';
        const AI = _isAiReady();
        const suffix = AI ? '' : ' - No AI provider configured. Add an API key and model in Settings first.';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Fear tags - what unsettles them</div>
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">Meeting a co-located character, item, or area carrying any of these tags makes this character <code>frightened</code>. Leave empty for a character nothing unsettles.</div>
            <div id="fear-tag-multiselect-mind-${_safeId()}"></div>
            <button class="btn btn-sm" ${AI ? '' : 'disabled'} onclick="InspectorAgentView._generateFearTags('${_state.escName}')" style="font-size:10px;padding:2px 10px;margin-top:4px;" title="Ask the character's LLM to pick fear tags. Your hand-placed tags are kept - picks are added.${suffix}">😨 Generate from Personality</button>
        </div>`;
    }

    function _whatISeeHtml(): string {
        if (!_state) return '';
        const p: any = worldState.players?.[_state.charName];
        if (!p) return '';
        const area = worldState.areas?.[p.current_area];
        let body: string;
        if (area) {
            body = `<div>${area.description || ''}</div>`;
            const items = (area.items || []).map((item: any) => item.name).filter(Boolean).join(', ');
            if (items) body += `<div style="margin-top:4px;color:var(--text-dim);font-size:11px;">Items: ${items}</div>`;
            const others = Object.entries(worldState.players || {} as Record<string, any>)
                .filter(([name, q]: [string, any]) => name !== _state!.charName && q.current_area === p.current_area);
            if (others.length) body += `<div style="margin-top:4px;color:var(--pink);font-size:11px;">Also: ${others.map(([name]) => name).join(', ')}</div>`;
        } else {
            body = `<span style="color:var(--text-muted);">Unknown location</span>`;
        }
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">What I see - the room right now</div>
            <div style="font-size:12px;padding:8px 12px;background:var(--bg-inset);border-radius:6px;border-left:3px solid #58a6ff;">${body}</div>
        </div>`;
    }

    function _latestThoughtsHtml(): string {
        if (!_state) return '';
        const cs: any = events.getCharacterState(_state.charName) || {};
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

    function _planHtml(): string {
        if (!_state) return '';
        const plan: any[] | null = (PlanTracker && PlanTracker.getPlan) ? PlanTracker.getPlan(_state.charName) : null;
        if (!plan || !plan.length) return '';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Plan - the current intent</div>
            <ol style="margin:0;padding-left:20px;font-size:11px;line-height:1.7;">${plan.map((step: any) => `<li>${esc(step)}</li>`).join('')}</ol>
        </div>`;
    }

    function _knowledgeHtml(): string {
        if (!_state) return '';
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
    function _recipesHtml(): string {
        if (!_state) return '';
        const AV: any = (window as any).InspectorAgentView;
        const p: any = worldState.players?.[_state.charName];
        const list: any[] = (AV && AV._knownRecipeNames && p) ? AV._knownRecipeNames(_state.charName, p) : [];
        const head = `<div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Recipes - what they can make${list.length ? ` (${list.length})` : ''}</div>`;
        if (!list.length) {
            return `<div style="margin-top:14px;">${head}
                <div style="font-size:10px;color:var(--text-dim);">None yet - create a recipe node (type: recipe) with learned_by: ["global"] (or "skill:&lt;name&gt;", "item:&lt;name&gt;", discoverable:true) to add one.</div>
            </div>`;
        }
        return `<div style="margin-top:14px;">${head}
            ${list.map((r: any) => `<div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:11px;">
                <span style="flex:1;">🧾 ${esc(r.name)}</span>
                <button class="btn btn-sm" data-help="craft" onclick="runAction('craft ${esc(r.name)}','${_state!.escName}')" style="font-size:9px;padding:2px 8px;">Craft</button>
            </div>`).join('')}
        </div>`;
    }

    function _eventsTimelineHtml(): string {
        if (!_state) return '';
        const cs: any = events.getCharacterState(_state.charName) || {};
        const timeline: any[] = cs.detailedTimeline || [];
        let body: string;
        if (timeline.length > 0) {
            const startIdx = Math.max(0, timeline.length - 50);
            const blocks: string[] = [];
            for (let i = startIdx; i < timeline.length; i++) {
                const entry = timeline[i];
                const phase = entry.phase || 'unknown';
                const icons: Record<string, string> = { think: '💭', decide: '🎯', act: '⚡', action: '⚡', result: '→', react: '🔄', speech: '💬', observe: '👁️' };
                const icon = icons[phase] || '•';
                const label = phase.charAt(0).toUpperCase() + phase.slice(1);
                let contentText = '';
                if (entry.thought) contentText = entry.thought;
                else if (entry.speech) contentText = `"${entry.speech}"`;
                else if (entry.action) contentText = entry.action;
                else if (entry.result) contentText = entry.result;
                else if (entry.message) contentText = entry.message;
                else contentText = phase;
                blocks.push(`<div class="timeline-entry" onclick="InspectorAgentView._showTimelineDetail('${_state!.escName}', ${i}, this)">
                    <div class="timeline-entry-header">
                        <span class="timeline-tick">[${events.tickToTime(entry.tick || 0)}]</span>
                        <span class="timeline-phase-badge timeline-phase-${phase}">${icon} ${label}</span>
                    </div>
                    <div class="timeline-entry-content">${esc(contentText)}</div>
                </div>`);
            }
            body = blocks.join('');
        } else {
            body = `<div style="font-size:11px;color:var(--text-muted);padding:8px;">No timeline entries yet. The timeline captures every thought, decision, action, result, and reaction as the character experiences them.</div>`;
        }
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Timeline - the lived trace</div>
            <div class="timeline-viewer" id="timeline-${_safeId()}">${body}</div>
            <div id="timeline-detail-${_safeId()}" style="display:none;"></div>
        </div>`;
    }

    function _conversationHtml(): string {
        if (!_state) return '';
        const hist: any[] = (agent && agent.getDisplayHistory) ? agent.getDisplayHistory(_state.charName) : [];
        let body: string;
        if (hist.length > 0) {
            body = hist.map((msg: any, i: number) => {
                const role = msg.role || 'unknown';
                const content = String(msg.content || '');
                const roleLabel = role === 'user' ? '👤 Prompt' : '🤖 Response';
                const roleColor = role === 'user' ? 'var(--accent)' : 'var(--purple)';
                return `<div style="padding:6px 8px;border-bottom:1px solid var(--border-light);">
                    <div style="font-size:9px;color:${roleColor};font-weight:600;margin-bottom:2px;">${roleLabel} #${i + 1}</div>
                    <div style="color:var(--text-dim);font-size:10px;max-height:40px;overflow:hidden;">${esc(content)}${content.length > 250 ? '...' : ''}</div>
                </div>`;
            }).join('');
        } else {
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
    function _emotionEditorHtml(): string {
        if (!_state) return '';
        const p: any = worldState.players?.[_state.charName];
        if (!p) return '';
        const emotion = p.emotion || { current: 'neutral', intensity: 0 };
        const icons: Record<string, string> = { happy: '😊', sad: '😢', angry: '😠', afraid: '😨', surprised: '😲', disgusted: '🤢', neutral: '😐' };
        const opts = Object.keys(icons).map(e =>
            `<option value="${e}"${emotion.current === e ? ' selected' : ''}>${icons[e]} ${e}</option>`).join('');
        return `<div style="margin-top:8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;padding:7px 9px;">
            <span style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;">Set feeling</span>
            <select id="mind-emotion" style="font-size:10px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:1px 4px;">${opts}</select>
            <span style="font-size:10px;color:var(--text-dim);">intensity</span>
            <input type="range" id="mind-emotion-intensity" min="0" max="1" step="0.05" value="${emotion.intensity || 0}" style="width:70px;">
            <span id="mind-emotion-val" style="min-width:30px;font-size:10px;color:var(--text-dim);">${(emotion.intensity || 0).toFixed(2)}</span>
        </div>`;
    }

    /** The authored relationship store (Player.relationships), moved out of Bio. */
    function _relationshipsHtml(): string {
        if (!_state) return '';
        const me = _state.charName;
        const p: any = worldState.players?.[me];
        if (!p) return '';
        const othersExMe = (Object.entries(worldState.players || {}) as Array<[string, any]>)
            .filter(([name]) => name !== me);
        const rows: string[] = [];
        for (const [otherName] of othersExMe) {
            const rel = p.relationships?.[otherName];
            if (!rel) continue;
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
    function _memoryToolbarHtml(): string {
        if (!_state) return '';
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
    function _ensureSubscribed(): void {
        if (_subscribed) return;
        _subscribed = true;
        worldState.on('update', () => { if (_state && _container) _render(); });
    }

    function _mosiac(): any {
        if (!_state) return null;
        return worldState.players?.[_state.charName]?.mosiac || null;
    }

    function _mosiacHtml(): string {
        const m = _mosiac();
        if (!m) return '';
        const letter = (key: string, label: string, body: string) => `<div style="margin-bottom:5px;"><span style="font-family:monospace;color:#58a6ff;">${key}</span> <span style="color:var(--text-muted);font-size:9.5px;text-transform:uppercase;letter-spacing:.06em;">${label}</span><div style="font-size:10.5px;line-height:1.4;">${body}</div></div>`;
        const needs = (m.A || []).map((n: any) => `${esc(n.need)} ${n.value}`).join(', ') || 'nothing pressing';
        const step = m.S && m.S.step
            ? `${_hhmm(m.S.step.start)} ${esc(m.S.step.activity)}${m.S.step.area ? ' at ' + esc(m.S.step.area) : ''}`
            : 'no schedule';
        const tierCounts = Object.keys(m.C || {}).map(k => `${esc(k)} ${(m.C[k] || []).length}`).join(' / ') || 'none';
        return `<div style="margin-bottom:12px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">MOSIAC - the decision context</div>
            ${letter('M', 'motivation', esc(m.M || '-'))}
            ${letter('I', 'intention', esc(m.I || '-'))}
            ${letter('O', 'obligations', (m.O || []).length ? (m.O || []).map((o: any) => esc(o.charge)).join(', ') : 'none')}
            ${letter('S', 'schedule', step)}
            ${letter('A', 'attention', esc(needs))}
            ${letter('C', 'choices', esc(tierCounts))}
        </div>`;
    }

    // task-802 / 805 / 806: the derived decision weights, the authored dials and
    // the whispered lines - the same traits the soak weighs (task-804's input).
    function _dispositionHtml(): string {
        if (!_state) return '';
        const p: any = worldState.players?.[_state.charName];
        if (!p) return '';
        const disp: any = p.disposition || {};
        const weights: any[] = Array.isArray(disp.weights) ? disp.weights : [];
        const dials = disp.dials || (p.personality_dials || {});
        const whispers: string[] = Array.isArray(p.trait_behavior) ? p.trait_behavior : [];
        const entries = weights.slice().sort(
            (a: any, b: any) => Math.abs(Number(b.value)) - Math.abs(Number(a.value)));
        const dialEntries = Object.entries(dials);
        const gated: string[] = Array.isArray(disp.gated) ? disp.gated : [];
        if (!entries.length && !dialEntries.length && !whispers.length && !gated.length) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">no disposition signals - an unauthored character scores neutral.</div>`;
        }
        const weightRows = entries.map((w: any) => {
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
        const dialRows = dialEntries.map(([k, v]) =>
            `<div style="display:flex;gap:6px;align-items:baseline;font-size:10px;">
                <span style="color:var(--text-dim);flex:1;">${esc(k)}</span>
                <span style="font-family:monospace;color:var(--text-muted);">${Number(v).toFixed(2)}</span>
            </div>`).join('');
        const whisperRows = whispers.map((w: string) =>
            `<div style="font-size:9.5px;color:var(--text-muted);line-height:1.45;margin-top:3px;">${esc(w)}</div>`).join('');
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
    function _actionsHtml(): string {
        if (!_state) return '';
        const p: any = worldState.players?.[_state.charName];
        const actions: any[] = (p && p.disposition && Array.isArray(p.disposition.actions)) ? p.disposition.actions : [];
        if (!actions.length) return '';
        const gated = new Set<string>(((p.disposition && p.disposition.gated) || []).map((g: string) => String(g).toLowerCase()));
        const rows = actions.map((a: any) => {
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

    function _peopleHtml(): string {
        if (!_state) return '';
        if (_state.peopleStatus === 'loading') {
            return `<div style="font-size:10.5px;color:var(--text-muted);">deriving profiles…</div>`;
        }
        if (_state.peopleStatus === 'error' || !_state.people.length) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">${_state.peopleStatus === 'error' ? 'profiles unavailable.' : 'no rel-tagged memories yet — feelings about people appear as the character experiences them.'}</div>`;
        }
        const DIMS: Array<[string, string]> = [['trust', '#4caf50'], ['fear', '#e0a33c'], ['attraction', '#f778ba'], ['disgust', '#3fb950'], ['respect', '#bc8cff']];
        return _state.people.map((p: MindPerson) => {
            const selected = _state && _state.filter === 'person:' + p.name;
            const profile = p.profile as unknown as Record<string, number | string | boolean | undefined>;
            const rows = DIMS.map(([dim, color]) =>
                _bar(dim, Number(profile[dim] || 0), 100, color, true)).join('');
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

    // ── shell ────────────────────────────────────────────────────────────
    function _render(): void {
        if (!_state || !_container) return;
        const all = _memories();
        const visible = _visible(all);
        const selected = all.find((m: any) => m.id === _state!.selectedId) || null;
        const filters: Array<[string, string]> = [
            ['all', 'All'], ['episodic', 'Episodic'], ['beliefs', 'Beliefs'],
            ['social', 'Social'], ['procedural', 'Procedural'],
            ['contradicted', '⚡ Contradicted'], ['faded', 'Faded']
        ];
        const filterBtns = filters.map(([key, label]) => {
            const active = _state!.filter === key;
            return `<span class="mind-fbtn" data-filter="${key}" style="padding:2px 9px;border:1px solid ${active ? '#1f6feb' : 'var(--border)'};border-radius:11px;font-size:10.5px;color:${active ? '#58a6ff' : 'var(--text-dim)'};background:var(--bg-input);cursor:pointer;">${label}</span>`;
        }).join('');
        const cards = visible.length
            ? visible.slice().reverse().map((m: any) => _cardHtml(m)).join('')
            : `<div style="font-size:11px;color:var(--text-muted);padding:8px 0;">nothing matches this view.</div>`;

        // task-820: one tabbed mind surface over the existing renderers.
        const tab = _state!.tab || 'mind';
        const hdr = 'font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;';
        const tabs: Array<[string, string]> = [
            ['mind', 'Mind'], ['perception', 'Perception'],
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
                    <input id="mind-search" placeholder="Search text…" value="${esc(_state!.query)}" style="margin-left:auto;background:var(--bg-input);border:1px solid var(--border);border-radius:5px;color:var(--text);padding:3px 8px;font-size:11px;width:160px;">
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
            <div style="max-width:640px;">${_relationshipsHtml()}<div style="${hdr}">People — derived from memories</div>
                <div id="mind-people">${_peopleHtml()}</div></div></div>`;
        const tabBody = tab === 'perception' ? perceptionPane
            : tab === 'memories' ? memoriesPane
            : tab === 'people' ? peoplePane : mindPane;

        _container.innerHTML = `
        <div style="position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9990;" class="mind-close"></div>
        <div style="position:fixed;top:4vh;left:50%;transform:translateX(-50%);width:min(1360px,96vw);height:90vh;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:9991;display:flex;flex-direction:column;overflow:hidden;">
            <div style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border);background:var(--bg-inset);flex-wrap:wrap;">
                <h3 style="margin:0;font-size:14px;">🧠 Mind — ${esc(_state!.charName)}</h3>
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
        _container.querySelectorAll<HTMLElement>('.mind-close').forEach(el =>
            el.addEventListener('click', () => M.close()));
        _container.querySelectorAll<HTMLElement>('.mind-tab').forEach(el =>
            el.addEventListener('click', () => { if (_state) { _state.tab = el.dataset.tab || 'mind'; _render(); } }));
        // task-756: per-memory emotion editing lives here, not in the memory modal.
        const emoBox = _container.querySelector('#mind-mem-emotions') as HTMLElement | null;
        if (emoBox && selected) {
            const IM: any = (window as any).InspectorMemory;
            const initial = Array.isArray(selected.memory_emotions) && selected.memory_emotions.length
                ? selected.memory_emotions
                : (selected.emotion && selected.emotion.label ? [selected.emotion] : []);
            if (IM && IM._attachEmotionSelector) IM._attachEmotionSelector(emoBox, initial);
            const saveEmo = _container.querySelector('.mind-mem-emo-save');
            if (saveEmo) saveEmo.addEventListener('click', async () => {
                if (!_state) return;
                const emotions = Array.isArray(IM?._emoSelected) ? IM._emoSelected : [];
                const payload: any = { memory_emotions: emotions };
                if (emotions.length) payload.emotion = emotions[0];
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
            goalsBox.addEventListener('click', (ev: any) => {
                const del = ev.target.closest('.mind-goal-del');
                if (del) { del.closest('.mind-goal')?.remove(); _saveGoals(); return; }
                if (ev.target.closest('.mind-add-goal')) {
                    const empty = goalsBox.querySelector('.mind-goal-empty');
                    if (empty) empty.remove();
                    goalsBox.insertAdjacentHTML('afterbegin', _goalRowHtml({}));
                    (goalsBox.querySelector('.mind-goal-what') as HTMLElement | null)?.focus();
                }
            });
        }
        // task-787: interest/fear tag multiselects and the knowledge chips, moved
        // out of the Bio / Advanced tabs. Same stores, same handlers.
        const TM: any = (window as unknown as { TagMultiselect?: unknown }).TagMultiselect;
        const migPlayer: any = _state ? worldState.players?.[_state.charName] : null;
        if (TM && migPlayer) {
            const itBox = _container.querySelector(`#interest-tag-multiselect-mind-${_safeId()}`);
            if (itBox) new TM(itBox, {
                tags: Array.isArray(migPlayer.interest_tags) ? migPlayer.interest_tags : [],
                appliesTo: 'characters', allowNew: true, placeholder: 'e.g. magic, food, documents...',
                onChange: (tags: any[]) => { ApiClient.updateCharacter(_state!.charName, { interest_tags: tags }).then(() => worldState.fetch()); }
            });
            const ftBox = _container.querySelector(`#fear-tag-multiselect-mind-${_safeId()}`);
            if (ftBox) new TM(ftBox, {
                tags: Array.isArray(migPlayer.fear_tags) ? migPlayer.fear_tags : [],
                appliesTo: 'characters', allowNew: true, placeholder: 'e.g. goblin, the dark, magic...',
                onChange: (tags: any[]) => { ApiClient.updateCharacter(_state!.charName, { fear_tags: tags }).then(() => worldState.fetch()); }
            });
        }
        const KB: any = (window as unknown as { KnownBySection?: unknown }).KnownBySection;
        const kbBox = _container.querySelector(`#mind-knowledge-chips-${_safeId()}`);
        if (KB && kbBox && _state) kbBox.appendChild(KB.buildKnownChips(_state.charName));

        // task-729: the relationship editor reuses agent-view's binder (same
        // selectors, same store); the emotion control writes the same
        // `{ emotion: { current, intensity } }` payload as the header row.
        const AV: any = (window as unknown as { InspectorAgentView?: unknown }).InspectorAgentView;
        if (AV && AV._bindRelationshipSliders && _state) AV._bindRelationshipSliders(_container, _state.charName);
        _container.querySelectorAll<HTMLElement>('.mind-rel-del').forEach(el =>
            el.addEventListener('click', () => {
                if (!_state) return;
                const other = el.dataset.other || '';
                if (other && AV && AV._removeRelationship) AV._removeRelationship(el.dataset.agent || _state.charName, other);
            }));
        const emoSel = _container.querySelector('#mind-emotion') as HTMLSelectElement | null;
        const emoRange = _container.querySelector('#mind-emotion-intensity') as HTMLInputElement | null;
        const emoVal = _container.querySelector('#mind-emotion-val') as HTMLElement | null;
        if (emoSel && emoRange && _state) {
            // Save on release, not on every drag step: the worldState update the
            // save triggers re-renders this panel, which would move the thumb.
            emoRange.addEventListener('input', () => { if (emoVal) emoVal.textContent = (parseFloat(emoRange.value) || 0).toFixed(2); });
            const saveEmotion = () => ApiClient.updateCharacter(_state!.charName, { emotion: { current: emoSel.value, intensity: parseFloat(emoRange.value) || 0 } }).then(() => worldState.fetch());
            emoSel.addEventListener('change', saveEmotion);
            emoRange.addEventListener('change', saveEmotion);
        }
        _container.querySelectorAll<HTMLElement>('.mind-fbtn').forEach(el =>
            el.addEventListener('click', () => { if (_state) { _state.filter = el.dataset.filter || 'all'; _render(); } }));
        _container.querySelectorAll<HTMLElement>('.mind-card').forEach(el =>
            el.addEventListener('click', () => { if (_state) { _state.selectedId = el.dataset.id || ''; _render(); } }));
        _container.querySelectorAll<HTMLElement>('.mind-dot').forEach(el =>
            el.addEventListener('click', () => { if (_state) { _state.selectedId = el.dataset.id || ''; _render(); } }));
        _container.querySelectorAll<HTMLElement>('.mind-conn').forEach(el =>
            el.addEventListener('click', () => { if (_state) { _state.selectedId = el.dataset.id || ''; _render(); } }));
        _container.querySelectorAll<HTMLElement>('.mind-person').forEach(el =>
            el.addEventListener('click', () => {
                if (!_state) return;
                const person = 'person:' + (el.dataset.person || '');
                _state.filter = _state.filter === person ? 'all' : person;
                _render();
            }));
        const refresh = _container.querySelector('.mind-refresh');
        if (refresh) refresh.addEventListener('click', () => { _fetchPeople(); _render(); });
        const search = _container.querySelector('#mind-search') as HTMLInputElement | null;
        if (search) {
            search.addEventListener('input', () => {
                if (_state) { _state.query = search.value; 
                    const list = _container?.querySelector('#mind-list');
                    const all2 = _memories();
                    if (list) list.innerHTML = (_visible(all2).length
                        ? _visible(all2).slice().reverse().map((m: any) => _cardHtml(m)).join('')
                        : `<div style="font-size:11px;color:var(--text-muted);padding:8px 0;">nothing matches this view.</div>`);
                    _wireList();
                }
            });
        }
    }

    function _wireList(): void {
        if (!_container) return;
        _container.querySelectorAll<HTMLElement>('.mind-card').forEach(el =>
            el.addEventListener('click', () => { if (_state) { _state.selectedId = el.dataset.id || ''; _render(); } }));
    }

    function _fetchPeople(): void {
        if (!_state) return;
        _state.peopleStatus = 'loading';
        fetch(`/api/players/${encodeURIComponent(_state.charName)}/memories/people`, {
            headers: { 'Accept': 'application/json' }
        }).then(r => r.ok ? r.json() : Promise.reject(new Error(String(r.status))))
            .then((data: { people?: MindPerson[] }) => {
                if (!_state) return;
                _state.people = data.people || [];
                _state.peopleStatus = 'ok';
                const el = _container?.querySelector('#mind-people');
                if (el) el.innerHTML = _peopleHtml();
            })
            .catch(() => {
                if (!_state) return;
                _state.peopleStatus = 'error';
                const el = _container?.querySelector('#mind-people');
                if (el) el.innerHTML = _peopleHtml();
            });
    }

    const M = {
        /**
         * Open the Memory Mind for a character. A snapshot of the live
         * worldState memories; 🔄 re-reads.
         */
        open(charName: string): void {
            const player = worldState.players?.[charName];
            if (!player) return;
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
                peopleStatus: 'loading'
            };
            _render();
            _fetchPeople();
        },

        close(): void {
            if (_container) {
                _container.remove();
                _container = null;
            }
            _state = null;
        },
    };

    return M;
})();

(window as unknown as { InspectorMindView: typeof InspectorMindView }).InspectorMindView = InspectorMindView;
