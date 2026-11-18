"use strict";
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
const InspectorPersonaView = (() => {
    'use strict';
    let _state = null;
    let _container = null;
    const esc = (value) => {
        if (value === null || value === undefined)
            return '';
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
        'skills', 'weaknesses',
    ]);
    const _LANGUAGE_FLUENCY_LEVELS = [
        'native', 'fluent', 'conversational', 'broken', 'none',
    ];
    const _DOMAIN_COMPETENCE_LEVELS = [
        'ignorant', 'novice', 'familiar', 'expert',
    ];
    function _normalizeDomainEntry(entry) {
        if (typeof entry === 'string') {
            const slug = _normalizeSlug(entry);
            if (!slug)
                return null;
            return { domain: slug, level: 'familiar', notes: '', jargon_terms: [] };
        }
        if (typeof entry === 'object' && entry !== null) {
            const obj = entry;
            const slug = _normalizeSlug(String(obj.domain ?? obj.id ?? obj.name ?? ''));
            const rawLevel = String(obj.level ?? 'familiar').trim().toLowerCase();
            const level = _DOMAIN_COMPETENCE_LEVELS.includes(rawLevel) ? rawLevel : 'familiar';
            const notes = String(obj.notes ?? '').trim();
            const termsRaw = Array.isArray(obj.jargon_terms) ? obj.jargon_terms : [];
            const jargon_terms = termsRaw.map((t) => String(t).trim()).filter((t) => t);
            return { domain: slug, level, notes, jargon_terms };
        }
        return null;
    }
    function _normalizeLanguageEntry(entry) {
        if (typeof entry === 'string') {
            const slug = _normalizeSlug(entry);
            if (!slug)
                return null;
            const fluency = slug === 'common' ? 'native' : 'fluent';
            return { language: slug, fluency, known_words: [], literate: true };
        }
        if (typeof entry === 'object' && entry !== null) {
            const obj = entry;
            const slug = _normalizeSlug(String(obj.language ?? obj.id ?? obj.name ?? ''));
            const rawFluency = String(obj.fluency ?? 'fluent').trim().toLowerCase();
            const fluency = _LANGUAGE_FLUENCY_LEVELS.includes(rawFluency) ? rawFluency : 'fluent';
            const wordsRaw = Array.isArray(obj.known_words) ? obj.known_words : [];
            const known_words = wordsRaw.map((w) => String(w).trim()).filter((w) => w);
            const literate = obj.literate !== undefined && obj.literate !== null
                ? Boolean(obj.literate)
                : (fluency === 'native' || fluency === 'fluent');
            return { language: slug, fluency, known_words, literate };
        }
        return null;
    }
    function _normalizeSlug(val) {
        return (val || '')
            .normalize('NFKD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, '_')
            .replace(/_+/g, '_')
            .replace(/-+/g, '-')
            .replace(/^[-_]+|[-_]+$/g, '');
    }
    let _knownTagsCache = null;
    function _ensureKnownTags() {
        if (_knownTagsCache !== null)
            return;
        _knownTagsCache = new Set();
        fetch('/api/tags/search?q=')
            .then((r) => r.json())
            .then((list) => {
            _knownTagsCache = new Set((list || []).map((t) => String(t.id || t.name || '').toLowerCase()));
            if (_state?.tab === 'persona')
                _personaRepaint(false);
        })
            .catch(() => { });
    }
    const _PERSONA_SECTIONS = [
        ['identity', 'Identity'], ['appearance', 'Appearance'],
        ['personality', 'Personality'], ['capabilities', 'Capabilities'], ['narrative', 'Narrative'],
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
        weaknesses: 'danger',
        interests: 'info', likes: 'info',
    };
    function _personaCss() {
        return `<style>
        #mind-persona .pf-badges{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px;}
        #mind-persona .pf-badge{font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:999px;padding:2px 10px;color:var(--text-dim);}
        #mind-persona .pf-span{grid-column:1/-1;}
        #mind-persona .pf-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline;margin-bottom:3px;}
        #mind-persona .pf-hint{font-size:11px;font-weight:400;text-transform:none;letter-spacing:normal;color:var(--text-muted);opacity:.78;}
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
        #mind-persona .pf-lock-note{font-size:11px;color:var(--text-muted);margin-bottom:6px;}
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
    const _CANONICAL_SKILLS = [
        'Acrobatics', 'Animal Handling', 'Arcana', 'Athletics', 'Deception',
        'History', 'Insight', 'Intimidation', 'Investigation', 'Medicine',
        'Nature', 'Perception', 'Performance', 'Persuasion', 'Religion',
        'Sleight of Hand', 'Stealth', 'Survival',
    ];
    function _personaChipBox(path, values, tone) {
        const chips = values.map((v) => `<span class="pf-chip${tone ? ` ${tone}` : ''}">${esc(v)}<b data-chip-x="${esc(path)}" data-chip-v="${esc(v)}">×</b></span>`).join('');
        const joined = esc(values.join('\n')).replace(/\n/g, '&#10;');
        const isSkills = path === 'capabilities.skills';
        const listAttr = isSkills ? ' list="pf-dl-capabilities-skills" autocomplete="off"' : '';
        const placeholder = isSkills ? 'add skill…' : 'add…';
        const datalist = isSkills
            ? `<datalist id="pf-dl-capabilities-skills">${_CANONICAL_SKILLS.map((s) => `<option value="${esc(s)}"></option>`).join('')}</datalist>`
            : '';
        return `<div class="pf-chips">${chips}<input class="pf-chip-new" data-chip-new="${esc(path)}" placeholder="${placeholder}"${listAttr} style="flex:1;min-width:90px;background:transparent;border:none;color:var(--text);font-size:12px;outline:none;">${datalist}<input type="hidden" data-persona-path="${esc(path)}" value="${joined}"></div>`;
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
    function _languageRowHtml(entry) {
        const norm = entry || { language: '', fluency: 'fluent', known_words: [], literate: true };
        const fluencyOpts = _LANGUAGE_FLUENCY_LEVELS.map((lvl) => `<option value="${lvl}"${lvl === norm.fluency ? ' selected' : ''}>${lvl}</option>`).join('');
        return `<div class="pf-lang-row" data-lang-row style="display:grid;grid-template-columns:1.5fr 1fr auto auto;gap:6px;align-items:center;margin-bottom:6px;padding:6px;border:1px solid var(--border);border-radius:6px;background:var(--bg-inset);">
            <input class="pf-in" data-lang-field="language" value="${esc(norm.language)}" placeholder="language id (e.g. common, english)">
            <select class="pf-in" data-lang-field="fluency">${fluencyOpts}</select>
            <label style="display:inline-flex;align-items:center;gap:4px;font-size:12px;color:var(--text-dim);white-space:nowrap;cursor:pointer;"><input type="checkbox" data-lang-field="literate"${norm.literate ? ' checked' : ''}> literate</label>
            <button type="button" class="btn btn-sm" data-lang-del title="Remove" style="padding:2px 7px;">×</button>
            <div style="grid-column:1/-1;"><div class="pf-sub">known_words</div>${_personaChipBox('capabilities.languages.known_words', norm.known_words, '')}</div>
        </div>`;
    }
    function _domainRowHtml(entry) {
        const norm = entry || { domain: '', level: 'familiar', notes: '', jargon_terms: [] };
        const levelOpts = _DOMAIN_COMPETENCE_LEVELS.map((lvl) => `<option value="${lvl}"${lvl === norm.level ? ' selected' : ''}>${lvl}</option>`).join('');
        return `<div class="pf-domain-row" data-domain-row style="display:grid;grid-template-columns:1.5fr 1fr auto;gap:6px;align-items:center;margin-bottom:6px;padding:6px;border:1px solid var(--border);border-radius:6px;background:var(--bg-inset);">
            <input class="pf-in" data-domain-field="domain" value="${esc(norm.domain)}" placeholder="domain slug (e.g. silicone_molding, law, sports)">
            <select class="pf-in" data-domain-field="level">${levelOpts}</select>
            <button type="button" class="btn btn-sm" data-domain-del title="Remove" style="padding:2px 7px;">×</button>
            <input class="pf-in" data-domain-field="notes" value="${esc(norm.notes)}" placeholder="competence notes or blind-spot details..." style="grid-column:1/-1;">
            <div style="grid-column:1/-1;"><div class="pf-sub">jargon_terms</div>${_personaChipBox('capabilities.domains.jargon_terms', norm.jargon_terms, '')}</div>
        </div>`;
    }
    function _personaFieldHtml(section, field, decl) {
        const path = `${section}.${field}`;
        const hint = _state?.persona?.hints[path] || (decl && decl.description) || '';
        const hintInline = hint ? `<span class="pf-hint">- ${esc(hint)}</span>` : '';
        const label = `<div class="pf-label"><span>${esc(field)}${_sparkle(path)}</span>${hintInline}</div>`;
        const val = _personaVal(path);
        const tone = _PERSONA_TONES[field] || '';
        if (path === 'personality.experience') {
            if (typeof val === 'object' && val !== null) {
                const exp = val;
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
                return { html: `<div class="pf-span"><fieldset class="pf-group"><legend>experience${hintInline ? ` ${hintInline}` : ''}</legend>${inner}</fieldset></div>`, wide: true };
            }
            else {
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
        if (path === 'capabilities.languages') {
            const items = Array.isArray(val) ? val : [];
            const rows = items
                .map((item) => _normalizeLanguageEntry(item))
                .filter((x) => x !== null)
                .map((x) => _languageRowHtml(x))
                .join('');
            return {
                html: `<div class="pf-span">${label}<div data-lang-list="capabilities.languages">${rows}</div><button type="button" class="btn btn-sm" id="mind-persona-add-lang" style="font-size:11px;margin-top:2px;">+ add language</button></div>`,
                wide: true,
            };
        }
        if (path === 'capabilities.domains') {
            const items = Array.isArray(val) ? val : [];
            const rows = items
                .map((item) => _normalizeDomainEntry(item))
                .filter((x) => x !== null)
                .map((x) => _domainRowHtml(x))
                .join('');
            return {
                html: `<div class="pf-span">${label}<div data-domain-list="capabilities.domains">${rows}</div><button type="button" class="btn btn-sm" id="mind-persona-add-domain" style="font-size:11px;margin-top:2px;">+ add domain</button></div>`,
                wide: true,
            };
        }
        if (path === 'narrative.media') {
            const items = Array.isArray(val) ? val : [];
            const rowHtml = (entry) => {
                const obj = (typeof entry === 'object' && entry !== null)
                    ? entry
                    : { title: String(entry ?? '') };
                const t = String(obj.title ?? '');
                const m = String(obj.medium ?? '');
                const w = String(obj.when ?? '');
                const f = String(obj.familiarity ?? '');
                const o = String(obj.opinion ?? '');
                return `<div class="pf-media-row" data-media-row style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;gap:5px;align-items:center;margin-bottom:6px;padding:6px;border:1px solid var(--border);border-radius:6px;background:var(--bg-inset);">
                    <input class="pf-in" data-media-field="title" value="${esc(t)}" placeholder="Title (e.g. Evil Dead II)">
                    <input class="pf-in" data-media-field="medium" value="${esc(m)}" placeholder="medium (movie/book/band)">
                    <input class="pf-in" data-media-field="when" value="${esc(w)}" placeholder="when (e.g. age 14, last fall)">
                    <input class="pf-in" data-media-field="familiarity" value="${esc(f)}" placeholder="familiarity (e.g. obsessed)">
                    <button type="button" class="btn btn-sm" data-media-del title="Remove" style="padding:2px 7px;">×</button>
                    <input class="pf-in" data-media-field="opinion" value="${esc(o)}" placeholder="what they think / feel about it..." style="grid-column:1/-1;">
                </div>`;
            };
            const rows = items.map(rowHtml).join('');
            return {
                html: `<div class="pf-span">${label}<div data-media-list="narrative.media">${rows}</div><button type="button" class="btn btn-sm" id="mind-persona-add-media" style="font-size:11px;margin-top:2px;">+ add media</button></div>`,
                wide: true,
            };
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
                ? `<div class="pf-lock-note">🔒 sealed - never compiled to prose.</div>${subs}`
                : subs;
            return { html: `<div class="pf-span"><fieldset class="pf-group"><legend>${esc(field)}${hintInline ? ` ${hintInline}` : ''}</legend>${locked}${markHidden}</fieldset></div>`, wide: true };
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
            doll.replaceChildren(document.createRange().createContextualFragment(pd.renderPaperdollFigureHtml(_state?.charName || '', player || {}, esc, _state?.escName || '', { mode: 'navigate', selectedArea: sel, facing })));
        }
        pane.querySelectorAll('[data-doll-facing]').forEach((btn) => {
            const face = btn.dataset.dollFacing;
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
                ApiClient.updatePlayerBody(_state.charName, { [region]: value / 100 })
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
            ['birthday', ident.birthday], ['gender', ident.gender],
            ['species', ident.species], ['occupation', ident.occupation],
        ];
        const chips = picks
            .filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== '')
            .map(([k, v]) => `<span class="pf-badge">${esc(k)} · ${esc(String(v))}</span>`);
        const lc = _state?.persona?.lifecycle;
        const player = (worldState.players || {})[_state?.charName || ''];
        const preg = lc?.pregnancy || player?.pregnancy;
        const cyc = lc?.reproductive_cycle || player?.reproductive_cycle;
        if (preg && typeof preg === 'object') {
            chips.push(`<span class="pf-badge" style="border-color:#f778ba;color:#f778ba;">pregnant · ${esc(String(preg.stage || 'gestating').replace(/_/g, ' '))}</span>`);
        }
        else if (cyc && typeof cyc === 'object' && cyc.pattern && cyc.pattern !== 'none') {
            const phase = String(cyc.phase || '').replace(/_/g, ' ');
            const dayStr = cyc.day && cyc.length_days ? ` (d${cyc.day}/${cyc.length_days})` : '';
            chips.push(`<span class="pf-badge">${esc(cyc.pattern)} · ${esc(phase)}${esc(dayStr)}</span>`);
        }
        if (!chips.length)
            return '';
        return `<div class="pf-badges">${chips.join('')}</div>`;
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
                    <button class="btn btn-sm" id="mind-persona-export" style="font-size:11px;" title="Export the persona form as JSON with field hints">📤 export</button>
                    <input type="file" id="mind-persona-file" accept=".json,.md,.txt" style="display:none;">
                    ${_state?.persona?.has_undo ? `<button class="btn btn-sm" id="mind-persona-revert" style="font-size:11px;" title="Revert compiled prose to pre-compile snapshot">↺ revert compile</button>` : ''}
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
            const names = Object.keys(fields).filter((f) => {
                if (section === 'narrative' && f === 'role_in_town') {
                    const v = _personaVal('narrative.role_in_town');
                    return v !== undefined && v !== null && String(v).trim() !== '';
                }
                return true;
            });
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
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:8px;">
                    <span style="font-weight:600;">Compile preview - hand prose differs</span>
                    <button type="button" class="btn btn-sm" id="mind-persona-polish" style="font-size:11px;">✨ Polish with LLM</button>
                </div>
                <div style="margin-bottom:8px;">
                    <label style="display:flex;align-items:center;gap:6px;font-weight:600;cursor:pointer;">
                        <input type="checkbox" id="mind-persona-apply-base" checked> Apply Base Description
                    </label>
                    <div style="margin-left:20px;margin-top:4px;">
                        <div style="color:var(--text-muted);font-size:11px;">CURRENT</div><div>${esc(p.preview.base_description?.current || '(empty)')}</div>
                        <div style="color:var(--text-muted);font-size:11px;margin-top:4px;">COMPILED (editable)</div>
                        <textarea class="pf-in" id="mind-persona-compiled-base" rows="3" style="margin-top:2px;font-size:11px;">${esc(p.preview.base_description?.compiled || '')}</textarea>
                    </div>
                </div>
                <div style="margin-bottom:8px;">
                    <label style="display:flex;align-items:center;gap:6px;font-weight:600;cursor:pointer;">
                        <input type="checkbox" id="mind-persona-apply-pers"${p.preview.personality?.current ? '' : ' checked'}> Apply Personality Prose
                    </label>
                    <div style="margin-left:20px;margin-top:4px;">
                        <div style="color:var(--text-muted);font-size:11px;">CURRENT</div><div>${esc(p.preview.personality?.current || '(empty)')}</div>
                        <div style="color:var(--text-muted);font-size:11px;margin-top:4px;">COMPILED (editable)</div>
                        <textarea class="pf-in" id="mind-persona-compiled-pers" rows="4" style="margin-top:2px;font-size:11px;">${esc(p.preview.personality?.compiled || '')}</textarea>
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
                ${p.warnings.map((w) => `<div>• ${esc(w)}</div>`).join('')}
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
        const el = _container?.id === 'mind-persona' ? _container : _container?.querySelector('#mind-persona');
        if (el) {
            el.replaceChildren(document.createRange().createContextualFragment(_personaHtml()));
            _wirePersona();
        }
    }
    function _fetchPersona() {
        if (!_state)
            return;
        _ensureKnownTags();
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
        ApiClient.getPlayerRecord(_state.charName)
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
                lifecycle: data.lifecycle || null,
                stale: !!data.prose_stale, dirty: false, preview: null, msg: '',
                has_undo: !!data.has_undo,
                warnings: data.warnings || [],
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
        _container?.querySelectorAll('.pf-chip-new').forEach((inputEl) => {
            if (inputEl.value.trim())
                _commitChipDraft(inputEl, false);
        });
        const out = {};
        _container?.querySelectorAll('[data-persona-path]').forEach((el) => {
            if (el.closest('[data-lang-row]'))
                return;
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
        const mediaList = _container?.querySelector('[data-media-list="narrative.media"]');
        if (mediaList) {
            const items = [];
            mediaList.querySelectorAll('[data-media-row]').forEach((row) => {
                const get = (f) => (row.querySelector(`[data-media-field="${f}"]`)?.value || '').trim();
                const title = get('title');
                if (!title)
                    return;
                const obj = { title };
                for (const k of ['medium', 'when', 'familiarity', 'opinion']) {
                    const v = get(k);
                    if (v)
                        obj[k] = v;
                }
                items.push(obj);
            });
            if (items.length) {
                out.narrative = out.narrative || {};
                out.narrative.media = items;
            }
        }
        const langList = _container?.querySelector('[data-lang-list="capabilities.languages"]');
        if (langList) {
            const items = [];
            langList.querySelectorAll('[data-lang-row]').forEach((row) => {
                const langInput = row.querySelector('[data-lang-field="language"]');
                const language = _normalizeSlug((langInput?.value || '').trim());
                if (!language)
                    return;
                const fluencyEl = row.querySelector('[data-lang-field="fluency"]');
                const rawFluency = (fluencyEl?.value || 'fluent').trim().toLowerCase();
                const fluency = _LANGUAGE_FLUENCY_LEVELS.includes(rawFluency) ? rawFluency : 'fluent';
                const litEl = row.querySelector('[data-lang-field="literate"]');
                const literate = Boolean(litEl?.checked);
                const chipBox = row.querySelector('.pf-chips');
                const known_words = chipBox ? _chipValues(chipBox) : [];
                items.push({ language, fluency, known_words, literate });
            });
            if (items.length) {
                out.capabilities = out.capabilities || {};
                out.capabilities.languages = items;
            }
        }
        const domainList = _container?.querySelector('[data-domain-list="capabilities.domains"]');
        if (domainList) {
            const items = [];
            domainList.querySelectorAll('[data-domain-row]').forEach((row) => {
                const domInput = row.querySelector('[data-domain-field="domain"]');
                const domain = _normalizeSlug((domInput?.value || '').trim());
                if (!domain)
                    return;
                const levelEl = row.querySelector('[data-domain-field="level"]');
                const rawLevel = (levelEl?.value || 'familiar').trim().toLowerCase();
                const level = _DOMAIN_COMPETENCE_LEVELS.includes(rawLevel) ? rawLevel : 'familiar';
                const notesEl = row.querySelector('[data-domain-field="notes"]');
                const notes = (notesEl?.value || '').trim();
                const chipBox = row.querySelector('.pf-chips');
                const jargon_terms = chipBox ? _chipValues(chipBox) : [];
                items.push({ domain, level, notes, jargon_terms });
            });
            if (items.length) {
                out.capabilities = out.capabilities || {};
                out.capabilities.domains = items;
            }
        }
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
        ApiClient.savePlayerRecord(_state.charName, record, false)
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
    function _readPreviewOverrides() {
        const baseEl = _container?.querySelector('#mind-persona-compiled-base');
        const persEl = _container?.querySelector('#mind-persona-compiled-pers');
        const out = {};
        if (baseEl && baseEl.value.trim())
            out.base_description = baseEl.value.trim();
        if (persEl && persEl.value.trim())
            out.personality = persEl.value.trim();
        return Object.keys(out).length ? out : undefined;
    }
    async function _polishCompilePreview(auto = false) {
        if (!_state?.persona?.preview)
            return;
        const llm = window.llmClient;
        if (!llm || typeof llm.chat !== 'function') {
            if (!auto)
                _personaMsg('no model connected - configure one in Settings to polish prose.');
            return;
        }
        const btn = _container?.querySelector('#mind-persona-polish');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '✨ polishing...';
        }
        try {
            const rec = _state.persona.record || _collectPersona();
            const curBase = String(_state.persona.preview.base_description?.current || '').trim();
            const curPers = String(_state.persona.preview.personality?.current || '').trim();
            const prompt = `You are polishing two character sheet prose fields for "${_state.charName}" from structured JSON data.
Return ONLY valid JSON with two string keys: "base_description" and "personality".

Rules for "base_description":
- Smooth, evocative third-person physical/sensory description ONLY (build, apparent age, face, hair, eyes, body details, voice, scent, general wardrobe aesthetic).
- Eliminate snake_case slugs (e.g. "oversized_band_hoodies" -> "oversized band hoodies"), eliminate repeated adjectives, and NEVER include backstory or secrets.
- Use third-person pronouns, never first-person ("my").

Rules for "personality":
- Smooth, natural second-person ("You are ...") if CURRENT personality uses "you", otherwise third-person.
- Preserve all core identity, setting anchors, backstory/friendships, and emotional stakes from CURRENT personality if provided, and weave in the structured traits, habits, quirks, speech style/dialect/catchphrases, aspirations, MBTI, and Alignment cleanly.
- Eliminate ALL snake_case slugs.

CURRENT base_description: ${JSON.stringify(curBase)}
CURRENT personality: ${JSON.stringify(curPers)}
STRUCTURED RECORD: ${JSON.stringify(rec)}`;
            const ans = await llm.chat(prompt, { label: 'persona/compile-polish', temperature: 0.3, max_tokens: 1400 });
            const raw = typeof ans === 'string' ? ans : (ans?.content || ans?.message || '');
            const m = raw.match(/\{[\s\S]*\}/);
            if (!m)
                throw new Error('LLM did not return JSON');
            const parsed = JSON.parse(m[0]);
            if (!_state?.persona?.preview)
                return;
            if (typeof parsed.base_description === 'string' && parsed.base_description.trim()) {
                _state.persona.preview.base_description.compiled = parsed.base_description.trim();
            }
            if (typeof parsed.personality === 'string' && parsed.personality.trim()) {
                _state.persona.preview.personality.compiled = parsed.personality.trim();
            }
            _personaRepaint(false);
        }
        catch (e) {
            if (!auto)
                _personaMsg(`LLM polish failed: ${e instanceof Error ? e.message : String(e)}`);
        }
        finally {
            const b = _container?.querySelector('#mind-persona-polish');
            if (b) {
                b.disabled = false;
                b.textContent = '✨ Polish with LLM';
            }
        }
    }
    function _compilePersona(force, sections, overrides) {
        if (!_state)
            return;
        if (!force && _state.persona?.dirty) {
            _personaMsg('unsaved edits: save the block first. Compile reads the saved block, not the sheet.');
            return;
        }
        const opts = {};
        if (force)
            opts.force = true;
        if (sections && sections.length)
            opts.sections = sections;
        if (overrides)
            opts.overrides = overrides;
        ApiClient.compilePlayerRecord(_state.charName, opts)
            .then(({ ok, data }) => {
            if (!ok || !_state?.persona) {
                _personaMsg(`compile rejected: ${data.error || _shortErr(data)}`);
                return;
            }
            if (data.needs_confirm) {
                _state.persona.preview = data.preview;
                _state.persona.msg = '';
                _personaRepaint();
                void _polishCompilePreview(true);
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
            box.replaceChildren(document.createRange().createContextualFragment(_personaStatesHtml()));
    }
    function _commitChipDraft(inputEl, keepFocus) {
        const box = inputEl.closest('.pf-chips');
        if (!box)
            return false;
        const raw = inputEl.value.trim();
        inputEl.value = '';
        if (!raw)
            return false;
        const path = inputEl.dataset.chipNew || '';
        const lastPart = path.split('.').pop() || '';
        const isSlug = _PERSONA_ID_LISTS.has(lastPart);
        const cur = _chipValues(box);
        let added = false;
        for (const piece of raw.split(/[,\n]+/)) {
            const trimmed = piece.trim();
            if (!trimmed)
                continue;
            const v = isSlug ? _normalizeSlug(trimmed) : trimmed;
            if (v && !cur.includes(v)) {
                cur.push(v);
                added = true;
            }
        }
        if (added)
            _chipPaint(box, cur, keepFocus);
        return added;
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
            box.replaceChildren(document.createRange().createContextualFragment(`<span style="color:var(--text-muted);">empty sheet - nothing to project.</span>`));
            return;
        }
        ApiClient.compilePlayerRecord(_state.charName, { record })
            .then(({ ok, data }) => {
            const live = _container?.querySelector('#mind-persona-codex');
            if (!live)
                return;
            if (!ok) {
                live.replaceChildren(document.createRange().createContextualFragment(`<span style="color:#e08a92;">cannot project: ${esc(data.error || 'rejected')}</span>`));
                return;
            }
            const c = data.compiled || {};
            live.replaceChildren(document.createRange().createContextualFragment(`${c.base_description ? `<div style="margin-bottom:6px;">${esc(c.base_description)}</div>` : ''}
                    ${c.personality ? `<div style="color:var(--text-dim);">${esc(c.personality)}</div>` : ''}
                    ${(c.interest_tags?.length || c.fear_tags?.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">drawn to ${(c.interest_tags || []).map(esc).join(', ') || '-'} · fears ${(c.fear_tags || []).map(esc).join(', ') || '-'}</div>` : ''}`));
        })
            .catch(() => { });
    }
    function _exportPersona() {
        if (!_state?.persona)
            return;
        const current = _collectPersona();
        const props = (_state.persona.schema?.properties || {});
        const fullRecord = {};
        for (const [section] of _PERSONA_SECTIONS) {
            const sDecl = props[section]?.properties || {};
            const sCur = (current[section] || {});
            const outSec = {};
            for (const field of Object.keys(sDecl)) {
                const fDecl = sDecl[field];
                if (sCur[field] !== undefined) {
                    outSec[field] = sCur[field];
                }
                else if (fDecl?.type === 'array') {
                    outSec[field] = [];
                }
                else if (fDecl?.type === 'object' && fDecl?.properties) {
                    const subOut = {};
                    for (const sub of Object.keys(fDecl.properties)) {
                        subOut[sub] = fDecl.properties[sub]?.type === 'array' ? [] : '';
                    }
                    outSec[field] = subOut;
                }
                else if (fDecl?.type === 'number') {
                    outSec[field] = null;
                }
                else {
                    outSec[field] = '';
                }
            }
            fullRecord[section] = outSec;
        }
        const payload = {
            character: _state.charName,
            record: fullRecord,
            hints: _state.persona.hints || {},
        };
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const safe = (_state.charName || 'character').toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '');
        a.href = url;
        a.download = `${safe || 'character'}_persona.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        _personaMsg(`exported ${a.download}.`);
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
                    const rawText = String(reader.result ?? '');
                    if (file.name.toLowerCase().endsWith('.json')) {
                        try {
                            const maybeExport = JSON.parse(rawText);
                            if (maybeExport && typeof maybeExport === 'object'
                                && maybeExport.record && typeof maybeExport.record === 'object'
                                && !Array.isArray(maybeExport.record)) {
                                if (!_state?.persona)
                                    return;
                                _state.persona.record = maybeExport.record;
                                _state.persona.inferred = [];
                                _state.persona.dirty = true;
                                _state.persona.msg = `loaded exported persona JSON "${file.name}": review, then save.`;
                                _personaRepaint(false);
                                return;
                            }
                        }
                        catch { /* fall through to CharacterImport */ }
                    }
                    const parsed = CI.parseInputFile(rawText, file.name);
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
    function _wireChipScope(scope) {
        scope.querySelectorAll('[data-chip-x]').forEach((el) => {
            const xEl = el;
            if (xEl._pfWired)
                return;
            xEl._pfWired = true;
            xEl.addEventListener('click', () => {
                const box = xEl.closest('.pf-chips');
                if (!box)
                    return;
                const v = xEl.dataset.chipV || '';
                _chipPaint(box, _chipValues(box).filter((x) => x !== v), true);
            });
        });
        scope.querySelectorAll('.pf-chip-new').forEach((el) => {
            const inputEl = el;
            if (inputEl._pfWired)
                return;
            inputEl._pfWired = true;
            inputEl.addEventListener('keydown', (ev) => {
                if (ev.key !== 'Enter' && ev.key !== ',')
                    return;
                ev.preventDefault();
                _commitChipDraft(inputEl, true);
            });
            inputEl.addEventListener('blur', () => {
                if (inputEl.value.trim())
                    _commitChipDraft(inputEl, false);
            });
            inputEl.addEventListener('input', () => {
                if (inputEl.value.trim())
                    _personaDirty();
            });
        });
    }
    function _wireLanguageRow(row) {
        const delBtn = row.querySelector('[data-lang-del]');
        if (delBtn && !delBtn._pfWired) {
            delBtn._pfWired = true;
            delBtn.addEventListener('click', () => {
                row.remove();
                _personaDirty();
                _scheduleCodex();
            });
        }
        row.querySelectorAll('[data-lang-field]').forEach((inp) => {
            const el = inp;
            if (el._pfWired)
                return;
            el._pfWired = true;
            el.addEventListener('input', () => { _personaDirty(); _scheduleCodex(); });
            el.addEventListener('change', () => { _personaDirty(); _scheduleCodex(); });
        });
        _wireChipScope(row);
    }
    function _wireDomainRow(row) {
        const delBtn = row.querySelector('[data-domain-del]');
        if (delBtn && !delBtn._pfWired) {
            delBtn._pfWired = true;
            delBtn.addEventListener('click', () => {
                row.remove();
                _personaDirty();
                _scheduleCodex();
            });
        }
        row.querySelectorAll('[data-domain-field]').forEach((inp) => {
            const el = inp;
            if (el._pfWired)
                return;
            el._pfWired = true;
            el.addEventListener('input', () => { _personaDirty(); _scheduleCodex(); });
            el.addEventListener('change', () => { _personaDirty(); _scheduleCodex(); });
        });
        _wireChipScope(row);
    }
    function _wirePersona() {
        if (!_container)
            return;
        const on = (sel, fn) => {
            const el = _container?.querySelector(sel);
            if (el && !el._pfWired) {
                el._pfWired = true;
                el.addEventListener('click', fn);
            }
        };
        on('#mind-persona-retry', () => _fetchPersona());
        on('#mind-persona-save', () => _savePersona());
        on('#mind-persona-import', () => {
            const picker = _container?.querySelector('#mind-persona-file');
            if (picker)
                picker.click();
        });
        on('#mind-persona-export', () => _exportPersona());
        on('#mind-persona-add-lang', () => {
            const list = _container?.querySelector('[data-lang-list="capabilities.languages"]');
            if (!list)
                return;
            const frag = document.createRange().createContextualFragment(_languageRowHtml());
            const row = frag.firstElementChild;
            list.appendChild(frag);
            if (row) {
                _wireLanguageRow(row);
                row.querySelector('[data-lang-field="language"]')?.focus();
            }
            _personaDirty();
            _scheduleCodex();
        });
        _container.querySelectorAll('[data-lang-row]').forEach((row) => _wireLanguageRow(row));
        on('#mind-persona-add-domain', () => {
            const list = _container?.querySelector('[data-domain-list="capabilities.domains"]');
            if (!list)
                return;
            const frag = document.createRange().createContextualFragment(_domainRowHtml());
            const row = frag.firstElementChild;
            list.appendChild(frag);
            if (row) {
                _wireDomainRow(row);
                row.querySelector('[data-domain-field="domain"]')?.focus();
            }
            _personaDirty();
            _scheduleCodex();
        });
        _container.querySelectorAll('[data-domain-row]').forEach((row) => _wireDomainRow(row));
        on('#mind-persona-add-media', () => {
            const list = _container?.querySelector('[data-media-list="narrative.media"]');
            if (!list)
                return;
            const frag = document.createRange().createContextualFragment(`<div class="pf-media-row" data-media-row style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;gap:5px;align-items:center;margin-bottom:6px;padding:6px;border:1px solid var(--border);border-radius:6px;background:var(--bg-inset);">
                <input class="pf-in" data-media-field="title" value="" placeholder="Title (e.g. Evil Dead II)">
                <input class="pf-in" data-media-field="medium" value="" placeholder="medium (movie/book/band)">
                <input class="pf-in" data-media-field="when" value="" placeholder="when (e.g. age 14, last fall)">
                <input class="pf-in" data-media-field="familiarity" value="" placeholder="familiarity (e.g. obsessed)">
                <button type="button" class="btn btn-sm" data-media-del title="Remove" style="padding:2px 7px;">×</button>
                <input class="pf-in" data-media-field="opinion" value="" placeholder="what they think / feel about it..." style="grid-column:1/-1;">
            </div>`);
            const row = frag.firstElementChild;
            list.appendChild(frag);
            row?.querySelector('[data-media-del]')?.addEventListener('click', () => { row.remove(); _personaDirty(); });
            row?.querySelectorAll('[data-media-field]').forEach((inp) => inp.addEventListener('input', () => _personaDirty()));
            row?.querySelector('[data-media-field="title"]')?.focus();
            _personaDirty();
        });
        _container.querySelectorAll('[data-media-del]').forEach((btn) => {
            const b = btn;
            if (b._pfWired)
                return;
            b._pfWired = true;
            b.addEventListener('click', () => {
                b.closest('[data-media-row]')?.remove();
                _personaDirty();
            });
        });
        _container.querySelectorAll('[data-media-field]').forEach((inp) => {
            const i = inp;
            if (i._pfWired)
                return;
            i._pfWired = true;
            i.addEventListener('input', () => _personaDirty());
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
        on('#mind-persona-polish', () => { void _polishCompilePreview(false); });
        on('#mind-persona-confirm', () => _compilePersona(true, ['all'], _readPreviewOverrides()));
        on('#mind-persona-apply-selected', () => {
            const applyBase = _container?.querySelector('#mind-persona-apply-base')?.checked;
            const applyPers = _container?.querySelector('#mind-persona-apply-pers')?.checked;
            const sections = ['tags', 'traits', 'skills', 'languages'];
            if (applyBase)
                sections.push('base_description');
            if (applyPers)
                sections.push('personality');
            _compilePersona(true, sections, _readPreviewOverrides());
        });
        on('#mind-persona-revert', () => {
            if (!_state)
                return;
            ApiClient.revertPlayerCompile(_state.charName)
                .then(({ ok, data }) => {
                if (!ok) {
                    _personaMsg(`revert failed: ${data.error || _shortErr(data)}`);
                    return;
                }
                _personaMsg('reverted to pre-compile snapshot.');
                _fetchPersona();
                worldState.fetch();
            })
                .catch((e) => _personaMsg(`revert failed: ${String(e)}`));
        });
        on('#mind-persona-toggle-exp', () => {
            if (!_state?.persona)
                return;
            const rec = _state.persona.record;
            if (!rec.personality)
                rec.personality = {};
            const cur = rec.personality.experience;
            if (typeof cur === 'object' && cur !== null) {
                // convert to string
                rec.personality.experience = cur.intimacy_level || '';
            }
            else {
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
        if (pane)
            _wireChipScope(pane);
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
    return {
        bind(state, container) {
            _state = state;
            _container = container;
        },
        unbind() {
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
        _LANGUAGE_FLUENCY_LEVELS,
        _normalizeLanguageEntry,
        _languageRowHtml,
        _DOMAIN_COMPETENCE_LEVELS,
        _normalizeDomainEntry,
        _domainRowHtml,
        _collectPersona,
    };
})();
window.InspectorPersonaView = InspectorPersonaView;
