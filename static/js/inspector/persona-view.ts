/**
 * InspectorPersonaView - Character Persona inspector and schema authoring (task-830, task-441).
 *
 * Full-surface schema editor for character persona, appearance, identity, and
 * narrative definitions. Communicates with GET/PUT /api/players/<n>/record and
 * preview compiler POST /api/players/<n>/record/compile.
 *
 * Extracted from mind-view.ts (task-441) to separate Persona definition authoring
 * from runtime Mind inspection.
 *
 * @module inspector/persona-view - character persona schema editor and compiler preview
 * @contributes InspectorPersonaView: persona editor, doll body navigator, and compiler UI
 * @powers Character Inspector Persona tab, schema-driven character record editing
 * @relates InspectorMindView, InspectorPaperdoll, ApiClient, worldState
 * @docs docs/virtualWorld/Characters/Persona.md
 */

const _personaModuleInit = true;

interface PersonaHostState {
    charName: string;
    escName: string;
    persona: PersonaState | null;
    tab?: string;
}

const InspectorPersonaView = (() => {
    'use strict';

    let _state: PersonaHostState | null = null;
    let _container: HTMLElement | null = null;

    const esc = (value: unknown): string => {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    // -- persona (task-830) -----------------------------------------
    // The full 828 schema, editable, with one explicit Compile. Reads
    // GET /record (block + schema + consumer hints), writes PUT /record,
    // projects via POST /record/compile (preview before clobber).
    const _PERSONA_ID_LISTS = new Set([
        'likes', 'dislikes', 'fears', 'interests', 'kinks', 'turn_ons',
        'turn_offs', 'traumas', 'boundaries', 'traits', 'aspirations',
        'quirks', 'habits', 'hard_limits', 'soft_limits',
    ]);

    function _normalizeSlug(val: string): string {
        return (val || '')
            .normalize('NFKD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, '_')
            .replace(/_+/g, '_')
            .replace(/-+/g, '-')
            .replace(/^[-_]+|[-_]+$/g, '');
    }

    let _knownTagsCache: Set<string> | null = null;
    function _ensureKnownTags(): void {
        if (_knownTagsCache !== null) return;
        _knownTagsCache = new Set();
        fetch('/api/tags/search?q=')
            .then((r) => r.json())
            .then((list: any[]) => {
                _knownTagsCache = new Set((list || []).map((t) => String(t.id || t.name || '').toLowerCase()));
                if (_state?.tab === 'persona') _personaRepaint(false);
            })
            .catch(() => { /* best-effort */ });
    }

    const _PERSONA_SECTIONS: Array<[string, string]> = [
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

    function _personaVal(path: string): unknown {
        const rec = _state?.persona?.record || {};
        const parts = path.split('.');
        let cur: unknown = rec;
        for (const p of parts) {
            if (typeof cur !== 'object' || cur === null) return undefined;
            cur = (cur as Record<string, unknown>)[p];
        }
        return cur;
    }

    const _PERSONA_INTIMACY = new Set(['personality.kinks', 'personality.turn_ons',
        'personality.turn_offs', 'personality.boundaries', 'personality.experience']);
    const _PERSONA_TONES: Record<string, string> = {
        fears: 'danger', traumas: 'danger', turn_offs: 'danger', dislikes: 'danger',
        interests: 'info', likes: 'info',
    };

    function _personaCss(): string {
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
        #mind-persona .pf-chip.pf-chip-free{border-style:dashed;}
        #mind-persona .pf-warnings{background:rgba(210,153,34,0.15);border:1px solid #d29922;border-radius:6px;padding:8px 10px;margin-bottom:10px;font-size:11px;color:#d29922;}
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
    function _parseMark(raw: string): { area: string | null; text: string } {
        const s = String(raw || '');
        const i = s.indexOf(_MARK_SEP);
        if (i <= 0) return { area: null, text: s };
        return { area: s.slice(0, i), text: s.slice(i + _MARK_SEP.length) };
    }
    function _formatMark(area: string, text: string): string {
        return `${area}${_MARK_SEP}${text}`;
    }
    function _allMarks(): string[] {
        const mods = _personaVal('appearance.body.modifications');
        return Array.isArray(mods) ? mods.map((m) => String(m)).filter((s) => s.trim()) : [];
    }
    function _setAllMarks(values: string[]): void {
        if (!_state?.persona) return;
        const rec = _state.persona.record || {};
        const appearance = (rec.appearance = rec.appearance || {});
        const body = (appearance.body = appearance.body || {});
        body.modifications = values;
        const hidden = _container?.querySelector(
            'input[type="hidden"][data-persona-path="appearance.body.modifications"]') as HTMLInputElement | null;
        if (hidden) hidden.value = values.join('\n');
        _personaDirty();
    }

    function _personaChipBox(path: string, values: string[], tone: string): string {
        const chips = values.map((v) =>
            `<span class="pf-chip${tone ? ` ${tone}` : ''}">${esc(v)}<b data-chip-x="${esc(path)}" data-chip-v="${esc(v)}">×</b></span>`).join('');
        const joined = esc(values.join('\n')).replace(/\n/g, '&#10;');
        return `<div class="pf-chips">${chips}<input class="pf-chip-new" data-chip-new="${esc(path)}" placeholder="add…" style="flex:1;min-width:90px;background:transparent;border:none;color:var(--text);font-size:12px;outline:none;"><input type="hidden" data-persona-path="${esc(path)}" value="${joined}"></div>`;
    }

    // task-843: the model's provenance. A field the converter invented (rather
    // than read from the source) is marked so the author can tell guess from
    // fact at a glance. A parent path marks its children and a child marks its
    // group, so an inferred whole reads as one cluster. Cleared by the next
    // `_fetchPersona` (save, compile, or reopening the tab).
    function _sparkle(path: string): string {
        const arr = _state?.persona?.inferred;
        const set = new Set(Array.isArray(arr) ? arr : []);
        if (!set.size) return '';
        let hit = set.has(path);
        if (!hit) {
            for (const p of set) {
                if (p.startsWith(path + '.') || path.startsWith(p + '.')) { hit = true; break; }
            }
        }
        return hit
            ? ` <span class="pf-inferred" style="color:var(--yellow);" title="inferred by the model - not stated in the source; review or clear it">✨</span>`
            : '';
    }

    function _personaFieldHtml(section: string, field: string, decl: any): { html: string; wide: boolean } {
        const path = `${section}.${field}`;
        const hint = _state?.persona?.hints[path] || (decl && decl.description) || '';
        const hintIco = hint ? ` <span class="pf-hint" title="${esc(hint)}">ⓘ</span>` : '';
        const label = `<div class="pf-label"><span>${esc(field)}${_sparkle(path)}</span>${hintIco}</div>`;
        const val = _personaVal(path);
        const tone = _PERSONA_TONES[field] || '';
        if (path === 'personality.experience') {
            if (typeof val === 'object' && val !== null) {
                const exp = val as Record<string, any>;
                const lvl = exp.intimacy_level || '';
                const partners = Array.isArray(exp.significant_partners) ? exp.significant_partners : [];
                const hardLims = Array.isArray(exp.hard_limits) ? exp.hard_limits : [];
                const softLims = Array.isArray(exp.soft_limits) ? exp.soft_limits : [];
                const inner = `
                    <div style="margin-bottom:6px;">
                        <div class="pf-sub">Intimacy Level</div>
                        <input class="pf-in" data-persona-path="personality.experience.intimacy_level" value="${esc(lvl)}" placeholder="e.g. none, romantic_only, experienced, veteran">
                    </div>
                    <div style="margin-bottom:6px;">
                        <div class="pf-sub">Significant Partners</div>
                        ${_personaChipBox('personality.experience.significant_partners', partners, 'info')}
                    </div>
                    <div style="margin-bottom:6px;">
                        <div class="pf-sub">Hard Limits (Strict boundaries)</div>
                        ${_personaChipBox('personality.experience.hard_limits', hardLims, 'danger')}
                    </div>
                    <div style="margin-bottom:6px;">
                        <div class="pf-sub">Soft Limits (Open with trust)</div>
                        ${_personaChipBox('personality.experience.soft_limits', softLims, 'danger')}
                    </div>
                    <button type="button" class="btn btn-sm" id="mind-persona-toggle-exp" style="font-size:10px;margin-top:4px;">Switch to free-text experience</button>
                `;
                return { html: `<div class="pf-span"><fieldset class="pf-group"><legend>experience${hintIco}</legend>${inner}</fieldset></div>`, wide: true };
            } else {
                const str = val === undefined || val === null ? '' : String(val);
                return { html: `<div class="pf-span">${label}<textarea class="pf-in" data-persona-path="${esc(path)}" rows="3">${esc(str)}</textarea><button type="button" class="btn btn-sm" id="mind-persona-toggle-exp" style="font-size:10px;margin-top:4px;">Switch to structured experience</button></div>`, wide: true };
            }
        }
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
            const isBirthday = path === 'identity.birthday';
            const listAttrs = listId
                ? ` list="${esc(listId)}" autocomplete="off" placeholder="type or pick"`
                : (isBirthday ? ` placeholder="dd.mm.yyyy (e.g. 14.03.1998)" pattern="\\d{2}\\.\\d{2}\\.\\d{4}"` : '');
            const datalist = listId
                ? `<datalist id="${esc(listId)}">${opts.map((o) => `<option value="${esc(o)}"></option>`).join('')}</datalist>`
                : '';
            return { html: `<div>${label}<input class="pf-in" data-persona-path="${esc(path)}" value="${esc(str)}"${numeric ? ' inputmode="decimal"' : ''}${listAttrs}>${datalist}</div>`, wide: false };
        }
        if (decl.type === 'array') {
            const values = Array.isArray(val) ? (val as unknown[]).map((v) => String(v)) : [];
            return { html: `<div class="pf-span">${label}${_personaChipBox(path, values, tone)}</div>`, wide: true };
        }
        if (decl.type === 'object' && decl.properties) {
            // modifications[] is authored on the doll side panel (task-852 P3) -
            // keep a hidden input so collect/save still round-trips, no second editor.
            const skipSubs = path === 'appearance.body' ? new Set(['modifications']) : null;
            const subs = Object.keys(decl.properties).map((sub) => {
                if (skipSubs?.has(sub)) return '';
                const subDecl = decl.properties[sub];
                const subPath = `${path}.${sub}`;
                const subVal = _personaVal(subPath);
                if (subDecl?.type === 'array') {
                    const values = Array.isArray(subVal) ? (subVal as unknown[]).map((v) => String(v)) : [];
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

    // -- persona body navigator (task-847) -------------------------
    // The paperdoll's AREA_TO_REGIONS, read - never re-declared. Clicking
    // an area shows live region status (same data as the 🩺 modal) plus the
    // linked schema values as a descriptive summary. The schema inputs
    // below stay the only editors; summary lines jump to their field.
    const _REGION_SCHEMA_MAP: Record<string, string[]> = {
        head: ['appearance.hair.color', 'appearance.hair.length',
            'appearance.hair.style', 'appearance.eyes.color',
            'appearance.face.shape', 'appearance.face.features'],
        torso: ['appearance.body.chest'],
        waist: ['appearance.body.waist', 'appearance.body.hips',
            'appearance.body.butt'],
        legs: ['appearance.body.legs'],
        feet: ['appearance.style.footwear'],
    };

    function _schemaLineSummary(path: string): string {
        const val = _personaVal(path);
        if (val === undefined || val === null || String(val).trim() === '') return '';
        if (Array.isArray(val)) {
            const items = val.map((v) => String(v)).filter((s) => s.trim() !== '');
            if (!items.length) return '';
            return items.map((s) => `· ${esc(s)}`).join('<br>');
        }
        return esc(String(val));
    }

    function _bodyNavSideHtml(area: string): string {
        const pd = (window as unknown as { InspectorPaperdoll?: any }).InspectorPaperdoll;
        const regions = ((pd?.AREA_TO_REGIONS || {})[area] || []) as string[];
        const player = (worldState.players || {})[_state?.charName || ''];
        const bodyState = player?.body_state || {};
        const playerConditions = player?.conditions || {};
        const regionName = (regionId: string) =>
            (player?.body_region_names?.[regionId] || regionId.replace(/_/g, ' '));
        const rows = regions.map((regionId) => {
            const bs = bodyState[regionId] || {};
            const injured = ((playerConditions.injured || []) as any[])
                .filter((i: any) => i.body_part === regionId);
            const bleeding = ((playerConditions.bleeding || []) as any[])
                .filter((i: any) => i.body_part === regionId);
            const missing = ((playerConditions.missing || []) as any[])
                .filter((i: any) => i.body_part === regionId);
            const exposed = player?.region_exposed?.[regionId] !== false;
            const sensNum = bs.sensitivity !== undefined ? parseFloat(bs.sensitivity) : NaN;
            const sens = Number.isFinite(sensNum) ? sensNum.toFixed(2) : '-';
            const chips: string[] = [];
            if (injured.length) chips.push(`<span style="color:var(--yellow);">🤕 Lv${Math.max(...injured.map((i: any) => i.level || 1))}</span>`);
            if (bleeding.length) chips.push(`<span style="color:var(--red);">🩸 bleeding</span>`);
            if (missing.length) chips.push(`<span style="color:var(--red);">✖ missing</span>`);
            if (!exposed) chips.push(`<span style="color:var(--text-dim);">🛡️ covered</span>`);
            if (!chips.length) chips.push(`<span style="color:var(--text-dim);">healthy</span>`);
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
        const markRows = areaMarks.map((m) =>
            `<div class="pf-mark-row"><span>${esc(m.text)}</span>`
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

    function _bodyNavHtml(): string {
        const pd = (window as unknown as { InspectorPaperdoll?: any }).InspectorPaperdoll;
        const map = pd?.AREA_TO_REGIONS || {};
        const areas = Object.keys(map).filter((a) => ((map[a] || []) as string[]).length > 0);
        if (!areas.length || typeof pd?.renderPaperdollFigureHtml !== 'function') return '';
        const sel = _state?.persona?.bodyNav || null;
        const facing = _state?.persona?.dollFacing === 'back' ? 'back' : 'front';
        const player = (worldState.players || {})[_state?.charName || ''];
        const doll = pd.renderPaperdollFigureHtml(
            _state?.charName || '', player || {}, esc,
            _state?.escName || '', { mode: 'navigate', selectedArea: sel, facing });
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

    function _wireBodyNav(pane: Element): void {
        const pd = (window as unknown as { InspectorPaperdoll?: any }).InspectorPaperdoll;
        if (pd) {
            pd.onNavigate = (charName: string, area: string) => {
                if (!_state?.persona || charName !== _state.charName) return;
                _state.persona.bodyNav = area;
                _refreshBodyNav(pane);
            };
        }
        pane.querySelectorAll('[data-doll-facing]').forEach((btn) => {
            btn.addEventListener('click', () => {
                _setDollFacing(pane, (btn as HTMLElement).dataset.dollFacing === 'back' ? 'back' : 'front');
            });
        });
        const doll = pane.querySelector('#mind-persona-doll') as HTMLElement | null;
        if (doll && !(doll as HTMLElement & { _navKeys?: boolean })._navKeys) {
            (doll as HTMLElement & { _navKeys?: boolean })._navKeys = true;
            doll.addEventListener('keydown', (ev: KeyboardEvent) => {
                if (!_state?.persona || ev.altKey || ev.ctrlKey || ev.metaKey) return;
                if (ev.key === 'f' || ev.key === 'F' || ev.key === 'b' || ev.key === 'B') {
                    ev.preventDefault();
                    _setDollFacing(pane, (ev.key === 'b' || ev.key === 'B') ? 'back' : 'front');
                    return;
                }
                if (ev.key === 'Escape') {
                    if (!_state.persona.bodyNav) return;
                    ev.preventDefault();
                    ev.stopPropagation();
                    _state.persona.bodyNav = null;
                    _refreshBodyNav(pane);
                    return;
                }
                const dir = ({ ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' } as Record<string, 'left' | 'right' | 'up' | 'down'>)[ev.key];
                if (!dir) return;
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

    function _refreshBodyNav(pane: Element): void {
        if (!_state?.persona) return;
        const pd = (window as unknown as { InspectorPaperdoll?: any }).InspectorPaperdoll;
        const sel = _state.persona.bodyNav || null;
        const facing = _state.persona.dollFacing === 'back' ? 'back' : 'front';
        const doll = pane.querySelector('#mind-persona-doll');
        if (doll && pd?.renderPaperdollFigureHtml) {
            const player = (worldState.players || {})[_state?.charName || ''];
            doll.replaceChildren(document.createRange().createContextualFragment(pd.renderPaperdollFigureHtml(
                _state?.charName || '', player || {}, esc,
                _state?.escName || '', { mode: 'navigate', selectedArea: sel, facing })));
        }
        pane.querySelectorAll('[data-doll-facing]').forEach((btn) => {
            const face = (btn as HTMLElement).dataset.dollFacing;
            btn.classList.toggle('on', face === facing);
        });
        const nav = pane.querySelector('#mind-persona-bodynav');
        if (nav) {
            nav.replaceChildren(document.createRange().createContextualFragment(sel
                ? _bodyNavSideHtml(sel)
                : `<div style="font-size:11px;color:var(--text-muted);">pick a bodypart on the doll - live status, sheet summary, sensitivity, markings. Arrows move · F/B flip · Esc clears.</div>`));
            _wireBodyNavJumps(pane);
            _wireBodyNavSliders(pane);
            _wireBodyNavMarks(pane);
        }
    }

    // The faces' area lists are declared once, in paperdoll-view (AREA_FACE).
    function _navAreas(): string[] {
        const pd = (window as unknown as { InspectorPaperdoll?: any }).InspectorPaperdoll;
        const facing = _state?.persona?.dollFacing === 'back' ? 'back' : 'front';
        return typeof pd?.areasForFacing === 'function' ? (pd.areasForFacing(facing) as string[]) : [];
    }

    // Flip the doll. A selection that is not on the new face moves to the
    // first area of that face rather than pointing at a slot nobody can see.
    function _setDollFacing(pane: Element, face: 'front' | 'back'): void {
        if (!_state?.persona) return;
        _state.persona.dollFacing = face;
        const areas = _navAreas();
        const sel = _state.persona.bodyNav;
        if (sel && !areas.includes(sel)) _state.persona.bodyNav = areas[0] || null;
        _refreshBodyNav(pane);
    }

    // Arrow keys move to the nearest visible slot in that direction, read from
    // the rendered grid, so the key map follows whichever face template is on
    // screen and no layout is declared a second time.
    function _navNeighbour(pane: Element, dir: 'left' | 'right' | 'up' | 'down'): string | null {
        const slots = Array.from(pane.querySelectorAll('#mind-persona-doll .paperdoll-slot[data-area]')) as HTMLElement[];
        if (!slots.length) return null;
        const sel = _state?.persona?.bodyNav || null;
        const cur = slots.find((el) => el.dataset.area === sel);
        if (!cur) return slots[0].dataset.area || null;
        const mid = (el: HTMLElement) => {
            const r = el.getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        };
        const c = mid(cur);
        let best: string | null = null;
        let bestScore = Infinity;
        for (const el of slots) {
            if (el === cur) continue;
            const o = mid(el);
            const dx = o.x - c.x;
            const dy = o.y - c.y;
            const ahead = dir === 'right' ? dx : dir === 'left' ? -dx : dir === 'down' ? dy : -dy;
            if (ahead <= 4) continue;
            const off = (dir === 'left' || dir === 'right') ? Math.abs(dy) : Math.abs(dx);
            const score = ahead + off * 2;
            if (score < bestScore) { bestScore = score; best = el.dataset.area || null; }
        }
        return best;
    }

    function _wireBodyNavMarks(pane: Element): void {
        const add = () => {
            const area = _state?.persona?.bodyNav;
            const input = pane.querySelector('#mind-persona-mark-new') as HTMLInputElement | null;
            if (!area || !input) return;
            const text = input.value.trim();
            if (!text) return;
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
            if ((ev as KeyboardEvent).key === 'Enter') { (ev as KeyboardEvent).preventDefault(); add(); }
        });
        pane.querySelectorAll('[data-mark-x]').forEach((el) => {
            el.addEventListener('click', () => {
                const raw = (el as HTMLElement).dataset.markX || '';
                _setAllMarks(_allMarks().filter((m) => m !== raw));
                _refreshBodyNav(pane);
            });
        });
    }

    function _wireBodyNavSliders(pane: Element): void {
        pane.querySelectorAll('[data-sens-region]').forEach((el) => {
            el.addEventListener('change', () => {
                const region = (el as HTMLElement).dataset.sensRegion || '';
                const value = parseInt((el as HTMLInputElement).value, 10) || 0;
                if (!_state || !region) return;
                ApiClient.updatePlayerBody(_state.charName, { [region]: value / 100 })
                    .then(() => {
                        const player = (worldState.players || {})[_state?.charName || ''];
                        if (player) {
                            player.body_state = player.body_state || {};
                            player.body_state[region] = player.body_state[region] || {};
                            player.body_state[region].sensitivity = value / 100;
                        }
                        _refreshBodyNav(pane);
                    }).catch(() => { /* leave the slider where it was */ });
            });
        });
    }

    function _wireBodyNavJumps(pane: Element): void {
        pane.querySelectorAll('[data-persona-jump]').forEach((el) => {
            el.addEventListener('click', () => {
                const path = (el as HTMLElement).dataset.personaJump || '';
                const target = pane.querySelector(`[data-persona-path="${path}"]`)
                    || pane.querySelector(`[data-persona-path^="${path}."]`);
                if (target) {
                    (target as HTMLElement).scrollIntoView({ block: 'center', behavior: 'smooth' });
                    const box = (target as HTMLElement).closest('.pf-chips') || target;
                    (box as HTMLElement).style.boxShadow = '0 0 0 2px rgba(88,166,255,.5)';
                    setTimeout(() => { (box as HTMLElement).style.boxShadow = ''; }, 1200);
                }
            });
        });
    }

    function _personaBadges(): string {
        const rec = _state?.persona?.record || {};
        const ident = (rec.identity || {}) as Record<string, unknown>;
        const picks: Array<[string, unknown]> = [
            ['pronouns', ident.pronouns], ['age', ident.age],
            ['birthday', ident.birthday], ['gender', ident.gender],
            ['species', ident.species], ['occupation', ident.occupation],
        ];
        const chips = picks
            .filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== '')
            .map(([k, v]) => `<span class="pf-badge">${esc(k)} · ${esc(String(v))}</span>`).join('');
        if (!chips) return '';
        return `<div class="pf-badges">${chips}</div>`;
    }

    // task-852 P1: character header - name, one-liner, badges, state chips
    // (✓ saved / ● unsaved / ⚠ uncompiled), actions on the right.
    function _personaStatesHtml(): string {
        const p = _state?.persona;
        if (!p) return '';
        // Both flags already exist: `dirty` is set by an edit to a sheet field and
        // cleared by the post-save re-read; `stale` is the server's
        // persona_prose_stale node flag (prose_stale from GET /record). Compile
        // reads the SAVED block, so an unsaved edit is also uncompiled.
        const bits: string[] = [];
        if (p.dirty) {
            bits.push(`<span class="pf-state pf-state-dirty" title="Edits on this sheet are not stored yet. Press save block.">\u25cf unsaved</span>`);
        } else {
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

    function _personaHeaderHtml(): string {
        const name = _state ? _state.charName : '';
        const player = (worldState.players || {})[name];
        // One-liner is authored identity prose, never equipment projection.
        const prose = ((player?.base_description || '') as string);
        const oneLiner = prose ? esc(prose.split('\n')[0]) : '';
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
                    ${_state?.persona?.has_undo ? `<button class="btn btn-sm" id="mind-persona-revert" style="font-size:11px;" title="Revert compiled prose to pre-compile snapshot">↺ revert compile</button>` : ''}
                    <button class="btn btn-sm" id="mind-persona-save" style="font-size:11px;">💾 save block</button>
                    <button class="btn btn-sm btn-blue" id="mind-persona-compile" style="font-size:11px;" title="Project the block into base_description / personality + tags">⚙ compile</button>
                </div>
            </div>
        </div>`;
    }

    function _personaHtml(): string {
        const p = _state?.persona;
        if (!p || p.status === 'loading') {
            return `<div style="font-size:11px;color:var(--text-muted);">reading the structured block…</div>`;
        }
        if (p.status === 'error') {
            return `<div style="font-size:11px;color:var(--text-muted);">record unavailable. <button class="btn btn-sm" id="mind-persona-retry" style="font-size:10px;">↻ retry</button></div>`;
        }
        const props = (p.schema?.properties || {}) as Record<string, any>;
        const openSet = new Set(p.openSections || []);
        const sections = _PERSONA_SECTIONS.map(([section, label]) => {
            const fields = props[section]?.properties || {};
            const names = Object.keys(fields);
            const filled = names.filter((f) => {
                const v = _personaVal(`${section}.${f}`);
                if (v === undefined || v === null || v === '') return false;
                if (Array.isArray(v)) return v.length > 0;
                if (typeof v === 'object') return Object.keys(v as object).length > 0;
                return true;
            }).length;
            const renderable = (f: string) => {
                const r = _personaFieldHtml(section, f, fields[f]);
                return r.wide ? `<div class="pf-span">${r.html}</div>` : r.html;
            };
            let inner: string;
            if (section === 'personality') {
                const plain = names.filter((f) => !_PERSONA_INTIMACY.has(`${section}.${f}`));
                const intimate = names.filter((f) => _PERSONA_INTIMACY.has(`${section}.${f}`));
                inner = `<div class="pf-grid">${plain.map(renderable).join('')}</div>`;
                if (intimate.length) {
                    const iOpen = openSet.has('Intimacy') ? ' open' : '';
                    inner += `<details class="pf-fold pf-intimacy" data-fold="Intimacy"${iOpen}><summary>Intimacy · ${intimate.length} fields</summary><div style="padding:2px 10px 10px;"><div class="pf-grid">${intimate.map(renderable).join('')}</div></div></details>`;
                }
            } else {
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
                <div style="margin-bottom:8px;">
                    <label style="display:flex;align-items:center;gap:6px;font-weight:600;cursor:pointer;">
                        <input type="checkbox" id="mind-persona-apply-base" checked> Apply Base Description
                    </label>
                    <div style="margin-left:20px;margin-top:4px;">
                        <div style="color:var(--text-muted);font-size:11px;">CURRENT</div><div>${esc(p.preview.base_description?.current || '(empty)')}</div>
                        <div style="color:var(--text-muted);font-size:11px;margin-top:4px;">COMPILED</div><div>${esc(p.preview.base_description?.compiled || '(empty)')}</div>
                    </div>
                </div>
                <div style="margin-bottom:8px;">
                    <label style="display:flex;align-items:center;gap:6px;font-weight:600;cursor:pointer;">
                        <input type="checkbox" id="mind-persona-apply-pers" checked> Apply Personality Prose
                    </label>
                    <div style="margin-left:20px;margin-top:4px;">
                        <div style="color:var(--text-muted);font-size:11px;">CURRENT</div><div>${esc(p.preview.personality?.current || '(empty)')}</div>
                        <div style="color:var(--text-muted);font-size:11px;margin-top:4px;">COMPILED</div><div>${esc(p.preview.personality?.compiled || '(empty)')}</div>
                    </div>
                </div>
                <div style="display:flex;gap:6px;margin-top:10px;">
                    <button class="btn btn-sm btn-blue" id="mind-persona-apply-selected" style="font-size:11px;">✓ Apply selected</button>
                    <button class="btn btn-sm" id="mind-persona-confirm" style="font-size:11px;">✓ Apply all</button>
                    <button class="btn btn-sm" id="mind-persona-cancel" style="font-size:11px;">keep mine</button>
                </div>
            </div>` : '';
        const warningsBox = p.warnings && p.warnings.length ? `<div class="pf-warnings">
                <div style="font-weight:600;margin-bottom:4px;">Preference Contradictions (Non-blocking):</div>
                ${p.warnings.map((w: string) => `<div>• ${esc(w)}</div>`).join('')}
            </div>` : '';
        const tagDatalist = `<datalist id="mind-persona-tag-suggestions">${[...(_knownTagsCache || [])].map((t) => `<option value="${esc(t)}"></option>`).join('')}</datalist>`;
        const msg = p.msg ? `<div style="font-size:11px;color:var(--text-muted);margin-top:8px;">${esc(p.msg)}</div>` : '';
        return `${_personaCss()}
            ${_personaHeaderHtml()}
            <details class="pf-fold" data-fold="Codex"${openSet.has('Codex') ? ' open' : ''}><summary>Codex entry - live preview</summary>
                <div style="padding:2px 10px 10px;"><div class="pf-codex" id="mind-persona-codex">open the fold and type - the compiled entry appears here without storing anything.</div></div>
            </details>
            ${warningsBox}${tagDatalist}${preview}
            <div class="pf-workspace">
                <div class="pf-doll-col">${_bodyNavHtml()}</div>
                <div class="pf-sheet-col">${sections}${msg}</div>
            </div>`;
    }

    // A dirty sheet lives only in the DOM (inputs write nowhere else). Any
    // rebuild of the pane or the whole modal must read the form back into the
    // record first, or the edits vanish while the chip still says unsaved.
    function _syncPersonaFromForm(): void {
        const p = _state?.persona;
        if (!p || !p.dirty || p.status !== 'ok') return;
        if (!_container?.querySelector('#mind-persona [data-persona-path]')) return;
        p.record = _collectPersona();
    }

    function _personaRepaint(syncForm = true): void {
        if (syncForm) _syncPersonaFromForm();
        const el = _container?.querySelector('#mind-persona');
        if (el) { el.replaceChildren(document.createRange().createContextualFragment(_personaHtml())); _wirePersona(); }
    }

    function _fetchPersona(): void {
        if (!_state) return;
        _ensureKnownTags();
        if (!_state.persona) {
            _state.persona = {
                status: 'loading', record: {}, schema: null, hints: {},
                stale: false, dirty: false, preview: null, msg: '',
                openSections: ['Identity', 'Appearance'], dollFacing: 'front',
            };
        } else {
            _state.persona.status = 'loading';
            _state.persona.msg = '';
        }
        ApiClient.getPlayerRecord(_state.charName)
            .then((data: any) => {
                if (!_state || !_state.persona) return;
                const keepOpen = _state.persona.openSections || ['Identity', 'Appearance'];
                const keepNav = _state.persona.bodyNav;
                const keepFacing = _state.persona.dollFacing || 'front';
                _state.persona = {
                    status: 'ok', record: data.record || {},
                    schema: data.schema || null, hints: data.hints || {},
                    suggestions: data.suggestions || {},
                    lifecycle: data.lifecycle || null,
                    stale: !!data.prose_stale, dirty: false, preview: null, msg: '',
                    has_undo: !!data.has_undo,
                    warnings: data.warnings || [],
                    openSections: keepOpen, bodyNav: keepNav, dollFacing: keepFacing,
                };
                _personaRepaint();
            })
            .catch(() => {
                if (!_state || !_state.persona) return;
                _state.persona.status = 'error';
                _personaRepaint();
            });
    }

    function _collectPersona(): Record<string, any> {
        const out: Record<string, any> = {};
        _container?.querySelectorAll<HTMLElement>('[data-persona-path]').forEach((el) => {
            const path = el.dataset.personaPath || '';
            const parts = path.split('.');
            if (parts.length < 2) return;
            const raw = (el as HTMLInputElement).value;
            let value: unknown = raw;
            const sectionProps = (_state?.persona?.schema?.properties?.[parts[0]]?.properties) || {};
            let decl = sectionProps[parts[1]];
            if (parts.length > 2 && decl?.properties) decl = decl.properties[parts[2]];
            if (!decl || decl.type === 'string') {
                value = raw.trim();
            } else if (decl.type === 'number' || _PERSONA_NUMBERS.has(parts.slice(0, 2).join('.'))) {
                const trimmed = raw.trim();
                value = trimmed === '' ? undefined : Number(trimmed);
            } else if (decl.type === 'array') {
                value = raw.split('\n').map((s) => s.trim()).filter((s) => s);
            } else if (decl.type === 'object') {
                value = raw.trim();
            } else {
                value = raw.trim();
            }
            if (value === undefined || value === '' || (Array.isArray(value) && !value.length)) return;
            let cursor = out;
            for (let i = 0; i < parts.length - 1; i++) {
                cursor[parts[i]] = cursor[parts[i]] || {};
                cursor = cursor[parts[i]] as Record<string, any>;
            }
            cursor[parts[parts.length - 1]] = value;
        });
        return out;
    }

    function _personaMsg(text: string): void {
        if (_state?.persona) {
            _state.persona.msg = text;
            _personaRepaint();
        }
    }

    function _savePersona(): void {
        if (!_state) return;
        const record = _collectPersona();
        ApiClient.savePlayerRecord(_state.charName, record, false)
            .then(({ ok, data }: any) => {
                if (!ok) {
                    _personaMsg(`save rejected: ${data.error || _shortErr(data)}`);
                    return;
                }
                _fetchPersona();
                worldState.fetch();
            })
            .catch((e: unknown) => _personaMsg(`save failed: ${String(e)}`));
    }

    function _shortErr(data: any): string {
        try { return JSON.stringify(data).slice(0, 160); } catch { return 'unknown error'; }
    }

    function _compilePersona(force: boolean, sections?: string[]): void {
        if (!_state) return;
        if (!force && _state.persona?.dirty) {
            _personaMsg('unsaved edits: save the block first. Compile reads the saved block, not the sheet.');
            return;
        }
        const opts: { force?: boolean; sections?: string[] } = {};
        if (force) opts.force = true;
        if (sections && sections.length) opts.sections = sections;
        ApiClient.compilePlayerRecord(_state.charName, opts)
            .then(({ ok, data }: any) => {
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
            .catch((e: unknown) => _personaMsg(`compile failed: ${String(e)}`));
    }

    let _codexTimer: number | null = null;

    function _personaDirty(): void {
        if (_state?.persona) _state.persona.dirty = true;
        const box = _container?.querySelector('#mind-persona-states');
        if (box) box.replaceChildren(document.createRange().createContextualFragment(_personaStatesHtml()));
    }

    function _chipValues(box: Element): string[] {
        const hidden = box.querySelector('input[type="hidden"]') as HTMLInputElement | null;
        const raw = hidden ? hidden.value : '';
        return raw.split('\n').map((s) => s.trim()).filter((s) => s);
    }

    function _chipPaint(box: Element, values: string[], keepFocus: boolean): void {
        const hidden = box.querySelector('input[type="hidden"]') as HTMLInputElement | null;
        const input = box.querySelector('.pf-chip-new') as HTMLInputElement | null;
        const path = input?.dataset.chipNew || hidden?.dataset.personaPath || '';
        const tone = (Object.keys(_PERSONA_TONES).find((k) => path.endsWith('.' + k)) || '') as string;
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
        if (hidden) hidden.value = values.join('\n');
        if (keepFocus && input) input.focus();
        _personaDirty();
        _scheduleCodex();
    }

    function _scheduleCodex(): void {
        if (_codexTimer) window.clearTimeout(_codexTimer);
        _codexTimer = window.setTimeout(() => { _codexTimer = null; _previewCodex(); }, 800);
    }

    function _previewCodex(): void {
        if (!_state?.persona || !_container) return;
        const box = _container.querySelector('#mind-persona-codex');
        if (!box || !(box.closest('details') as HTMLDetailsElement | null)?.open) return;
        const record = _collectPersona();
        if (!Object.keys(record).length) {
            box.replaceChildren(document.createRange().createContextualFragment(`<span style="color:var(--text-muted);">empty sheet - nothing to project.</span>`));
            return;
        }
        ApiClient.compilePlayerRecord(_state.charName, { record })
            .then(({ ok, data }: any) => {
                const live = _container?.querySelector('#mind-persona-codex');
                if (!live) return;
                if (!ok) {
                    live.replaceChildren(document.createRange().createContextualFragment(`<span style="color:#e08a92;">cannot project: ${esc(data.error || 'rejected')}</span>`));
                    return;
                }
                const c = data.compiled || {};
                live.replaceChildren(document.createRange().createContextualFragment(`${c.base_description ? `<div style="margin-bottom:6px;">${esc(c.base_description)}</div>` : ''}
                    ${c.personality ? `<div style="color:var(--text-dim);">${esc(c.personality)}</div>` : ''}
                    ${(c.interest_tags?.length || c.fear_tags?.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">drawn to ${(c.interest_tags || []).map(esc).join(', ') || '-'} · fears ${(c.fear_tags || []).map(esc).join(', ') || '-'}</div>` : ''}`));
            })
            .catch(() => { /* preview is best-effort; save shows real errors */ });
    }

    function _importPersonaFile(file: File): void {
        if (!_state?.persona) return;
        const CI = (window as unknown as { CharacterImport?: any }).CharacterImport;
        const llm = (window as unknown as { llmClient?: any }).llmClient;
        if (!CI) { _personaMsg('importer not loaded - rebuild the frontend.'); return; }
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
                    if (!schema) { _personaMsg('schema not loaded - retry the tab.'); return; }
                    _personaMsg(`converting ${parsed.kind} “${file.name}”…`);
                    const answer = await llm.chat(
                        CI.buildConvertPrompt(parsed.sourceText, schema),
                        { label: 'persona/import-convert', temperature: 0.2, max_tokens: 4000 });
                    const text = typeof answer === 'string' ? answer
                        : (answer?.content || answer?.message || '');
                    const converted = CI.extractJsonBlock(text);
                    if (!_state?.persona) return;
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
                } catch (e) {
                    _personaMsg(`import failed: ${e instanceof Error ? e.message : String(e)} - nothing stored.`);
                }
            })();
        };
        reader.onerror = () => _personaMsg('could not read that file.');
        reader.readAsText(file);
    }

    function _wirePersona(): void {
        if (!_container) return;
        const on = (sel: string, fn: () => void) => {
            const el = _container?.querySelector(sel);
            if (el) el.addEventListener('click', fn);
        };
        on('#mind-persona-retry', () => _fetchPersona());
        on('#mind-persona-save', () => _savePersona());
        on('#mind-persona-import', () => {
            const picker = _container?.querySelector('#mind-persona-file') as HTMLInputElement | null;
            if (picker) picker.click();
        });
        const picker = _container?.querySelector('#mind-persona-file') as HTMLInputElement | null;
        if (picker && !(picker as HTMLInputElement & { _wired?: boolean })._wired) {
            (picker as HTMLInputElement & { _wired?: boolean })._wired = true;
            picker.addEventListener('change', () => {
                const file = picker.files && picker.files[0];
                picker.value = '';
                if (file) _importPersonaFile(file);
            });
        }
        on('#mind-persona-compile', () => _compilePersona(false));
        on('#mind-persona-confirm', () => _compilePersona(true));
        on('#mind-persona-apply-selected', () => {
            const applyBase = (_container?.querySelector('#mind-persona-apply-base') as HTMLInputElement | null)?.checked;
            const applyPers = (_container?.querySelector('#mind-persona-apply-pers') as HTMLInputElement | null)?.checked;
            const sections: string[] = ['tags'];
            if (applyBase) sections.push('base_description');
            if (applyPers) sections.push('personality');
            _compilePersona(true, sections);
        });
        on('#mind-persona-revert', () => {
            if (!_state) return;
            ApiClient.revertPlayerCompile(_state.charName)
                .then(({ ok, data }: any) => {
                    if (!ok) {
                        _personaMsg(`revert failed: ${data.error || _shortErr(data)}`);
                        return;
                    }
                    _personaMsg('reverted to pre-compile snapshot.');
                    _fetchPersona();
                    worldState.fetch();
                })
                .catch((e: unknown) => _personaMsg(`revert failed: ${String(e)}`));
        });
        on('#mind-persona-toggle-exp', () => {
            if (!_state?.persona) return;
            const rec = _state.persona.record;
            if (!rec.personality) rec.personality = {};
            const cur = rec.personality.experience;
            if (typeof cur === 'object' && cur !== null) {
                // convert to string
                rec.personality.experience = cur.intimacy_level || '';
            } else {
                // convert to object
                rec.personality.experience = {
                    intimacy_level: cur ? String(cur) : '',
                    significant_partners: [],
                    hard_limits: [],
                    soft_limits: [],
                };
            }
            _personaDirty();
            _personaRepaint(false);
        });
        on('#mind-persona-cancel', () => {
            if (_state?.persona) {
                _state.persona.preview = null;
                _personaRepaint();
            }
        });
        const pane = _container.querySelector('#mind-persona');
        pane?.querySelectorAll('[data-lock]').forEach((el) => {
            el.addEventListener('click', () => {
                const path = (el as HTMLElement).dataset.lock || '';
                const body = pane.querySelector(`[data-lockbody="${path}"]`);
                if (body) {
                    const locked = (body as HTMLElement).classList.toggle('pf-locked');
                    (el as HTMLElement).textContent = locked
                        ? '🔒 sealed - never compiled to prose. click to reveal.'
                        : '🔓 revealed - still never compiled to prose.';
                }
            });
        });
        pane?.querySelectorAll('[data-chip-x]').forEach((el) => {
            el.addEventListener('click', () => {
                const box = (el as HTMLElement).closest('.pf-chips');
                if (!box) return;
                const v = (el as HTMLElement).dataset.chipV || '';
                _chipPaint(box, _chipValues(box).filter((x) => x !== v), true);
            });
        });
        pane?.querySelectorAll('.pf-chip-new').forEach((el) => {
            (el as HTMLInputElement).addEventListener('keydown', (ev: KeyboardEvent) => {
                if (ev.key !== 'Enter' && ev.key !== ',') return;
                ev.preventDefault();
                const box = (el as HTMLElement).closest('.pf-chips');
                if (!box) return;
                const path = (el as HTMLElement).dataset.chipNew || '';
                const lastPart = path.split('.').pop() || '';
                const raw = (el as HTMLInputElement).value.trim().replace(/,+$/, '');
                (el as HTMLInputElement).value = '';
                if (!raw) return;
                const v = _PERSONA_ID_LISTS.has(lastPart) ? _normalizeSlug(raw) : raw;
                if (!v) return;
                const cur = _chipValues(box);
                if (!cur.includes(v)) cur.push(v);
                _chipPaint(box, cur, true);
            });
        });
        // Only sheet fields mark the block dirty. The chip draft box, the mark
        // draft box and the sensitivity sliders carry no data-persona-path
        // (sliders persist on their own through PUT /body).
        const paneFlag = pane as (Element & { _pfInput?: boolean }) | null;
        if (pane && paneFlag && !paneFlag._pfInput) {
            paneFlag._pfInput = true;
            pane.addEventListener('input', (ev) => {
                const t = ev.target as HTMLElement | null;
                if (!t || !t.closest('[data-persona-path]')) return;
                _personaDirty();
                _scheduleCodex();
            });
        }
        if (pane) _wireBodyNav(pane);
        pane?.querySelectorAll('details').forEach((d) => {
            d.addEventListener('toggle', () => {
                const key = (d as HTMLElement).dataset.fold;
                if (key && _state?.persona) {
                    const set = new Set(_state.persona.openSections || []);
                    if ((d as HTMLDetailsElement).open) set.add(key);
                    else set.delete(key);
                    _state.persona.openSections = [...set];
                }
                if ((d as HTMLDetailsElement).open
                    && d.querySelector('#mind-persona-codex')) _previewCodex();
            });
        });
        if ((pane?.querySelector('[data-fold="Codex"]') as HTMLDetailsElement | null)?.open) {
            _previewCodex();
        }
    }

    return {
        bind(state: PersonaHostState, container: HTMLElement | null): void {
            _state = state;
            _container = container;
        },
        unbind(): void {
            _state = null;
            _container = null;
        },
        fetch: _fetchPersona,
        html: _personaHtml,
        wire: _wirePersona,
        syncFromForm: _syncPersonaFromForm,
        repaint: _personaRepaint,

        // Test helpers and constants
        _parseMark,
        _formatMark,
        _allMarks,
        _PERSONA_TEXTAREAS,
        _PERSONA_TONES,
    };
})();

(window as unknown as { InspectorPersonaView: typeof InspectorPersonaView }).InspectorPersonaView = InspectorPersonaView;
