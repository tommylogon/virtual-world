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
        const editBtn = `<button class="btn btn-sm" style="font-size:10px;" onclick="window.InspectorMemory&&window.InspectorMemory.editMemory('${_state ? _state.escName : ''}','${esc(m.id)}')">✏️ Edit</button>`;
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

        _container.innerHTML = `
        <div style="position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9990;" class="mind-close"></div>
        <div style="position:fixed;top:4vh;left:50%;transform:translateX(-50%);width:min(1360px,96vw);height:90vh;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:9991;display:flex;flex-direction:column;overflow:hidden;">
            <div style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border);background:var(--bg-inset);flex-wrap:wrap;">
                <h3 style="margin:0;font-size:14px;">🧠 Memory Mind — ${esc(_state!.charName)}</h3>
                <div style="display:flex;gap:6px;flex-wrap:wrap;flex:1;">${_statsHtml(all)}</div>
                <button class="btn btn-sm mind-refresh" style="font-size:10px;" title="Re-read the character's memories">🔄</button>
                <button class="btn btn-sm mind-close" style="font-size:10px;">✕</button>
            </div>
            <div style="flex:1;display:grid;grid-template-columns:250px 1fr 380px;overflow:hidden;">
                <div style="border-right:1px solid var(--border);padding:12px;overflow-y:auto;background:var(--bg-inset);">
                    <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">People — derived from memories</div>
                    <div id="mind-people">${_peopleHtml()}</div>
                </div>
                <div style="padding:12px;overflow-y:auto;min-width:0;">
                    ${_timelineHtml(all)}
                    <div style="display:flex;gap:5px;flex-wrap:wrap;margin:10px 0 8px;align-items:center;">
                        ${filterBtns}
                        <input id="mind-search" placeholder="Search text…" value="${esc(_state!.query)}" style="margin-left:auto;background:var(--bg-input);border:1px solid var(--border);border-radius:5px;color:var(--text);padding:3px 8px;font-size:11px;width:160px;">
                    </div>
                    <div id="mind-list">${cards}</div>
                </div>
                <div style="border-left:1px solid var(--border);padding:12px;overflow-y:auto;background:var(--bg-inset);">
                    <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Memory detail</div>
                    <div id="mind-detail">${_detailHtml(selected, all)}</div>
                    <div style="margin-top:12px;" id="mind-access">${_accessibilityHtml(all)}</div>
                </div>
            </div>
        </div>`;

        // wiring
        _container.querySelectorAll<HTMLElement>('.mind-close').forEach(el =>
            el.addEventListener('click', () => M.close()));
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
            _state = {
                charName,
                escName: charName.replace(/'/g, "\\'"),
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
