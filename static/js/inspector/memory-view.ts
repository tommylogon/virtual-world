/**
 * InspectorMemory - Character memory management and natural-language Memory Weaver (task-730).
 * Extracted from inspector.js for modularity.
 *
 * @module inspector/memory-view - character memory management & NL memory weaver
 * @contributes InspectorMemory: unified NL Memory Weaver (Ask Opinion, Backdate Event, About a Person) + structured memory editor
 * @powers Node inspectors, Memory - inspecting, weaving, backdating, and correcting what a character remembers
 * @relates renders through InspectorPanel; mirrors the memory-manager store and /api/players/<n>/memories/context
 * @docs docs/virtualWorld/AI & Narration/Memory System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

window.InspectorMemory = (() => {
    const M = ((window as any).InspectorView ? new (window as any).InspectorView() : {}) as MemoryViewApi;

    // Rich memory-emotion vocabulary, grouped for the picker. Multiple emotions
    // may be attached to one memory (stored as memory_emotions: [{label,intensity}]).
    const EMOTION_GROUPS: MemoryViewEmotionGroup[] = [
        { label: 'Core', items: ['neutral','happy','sad','angry','afraid','surprised','disgusted'] },
        { label: 'Warm / Social', items: ['affectionate','hopeful','grateful','proud','amused','loved','admiring','excited'] },
        { label: 'Anxious / Tense', items: ['anxious','nervous','worried','uneasy','spooked','unnerved','restless','dread','paranoid'] },
        { label: 'Arousal / Desire', items: ['aroused','eager','hungry','craving','curious','mischievous'] },
        { label: 'Down / Heavy', items: ['lonely','ashamed','guilty','embarrassed','wistful','melancholic','hollow','tired','bored'] },
        { label: 'Calm / Content', items: ['calm','content','peaceful','relieved','satisfied','quiet','safe'] },
        { label: 'Determined / Bold', items: ['determined','brave','resolute','defiant','focused'] },
        { label: 'Jealous / Bitter', items: ['jealous','envious','frustrated','resentful','bitter'] }
    ];

    const REL_DIMS: string[] = ['trust', 'fear', 'attraction', 'respect', 'disgust', 'familiarity'];

    /**
     * Parse a natural-language relative time expression or tick string into a
     * simulation tick (task-730).
     */
    M.parseRelativeTime = function (
        input: string,
        currentTick = 0,
        minutesPerTick = 1,
        birthTick: number | null = null
    ): MemoryViewRelativeTime | null {
        const raw = String(input ?? '').trim();
        if (!raw) return null;
        const s = raw.toLowerCase();
        const cur = Number.isFinite(Number(currentTick)) ? Math.round(Number(currentTick)) : 0;
        const mpt = Math.max(0.1, Number(minutesPerTick) || 1);
        const minBirth = (birthTick !== null && birthTick !== undefined && Number.isFinite(Number(birthTick)))
            ? Math.round(Number(birthTick))
            : null;
        const finalize = (tick: number, label: string): MemoryViewRelativeTime => {
            if (minBirth !== null && tick < minBirth) {
                return {
                    tick: minBirth,
                    unclampedTick: tick,
                    beforeBirth: true,
                    label: `⛔ clamped to birthday (tick ${minBirth}; requested ${tick})`
                };
            }
            return { tick, label };
        };

        if (s === 'now' || s === 'current' || s === 'today' || s === 'just now') {
            return finalize(cur, `now (tick ${cur})`);
        }
        if (s === 'start' || s === 'scenario start' || s === 'beginning') {
            return finalize(0, 'scenario start (tick 0)');
        }
        if (s === 'yesterday') {
            const delta = Math.max(1, Math.round(1440 / mpt));
            const tick = cur - delta;
            return finalize(tick, `yesterday (tick ${tick})`);
        }

        // "<N> turns/ticks before start" or "before start <N>"
        const preMatch = s.match(/^(\d+(?:\.\d+)?)\s*(?:turns?|ticks?|t)?\s*before\s*start$/i)
            || s.match(/^before\s*start\s*[:\-]?\s*(\d+(?:\.\d+)?)$/i);
        if (preMatch) {
            const n = Math.max(1, Math.round( parseFloat(preMatch[1]) || 0 ));
            return finalize(-n, `${n} turns before start (tick -${n})`);
        }

        // "<N> turns/ticks ago"
        const turnsAgo = s.match(/^(\d+(?:\.\d+)?)\s*(?:turns?|ticks?)\s*ago$/i);
        if (turnsAgo) {
            const n = Math.round(parseFloat(turnsAgo[1]) || 0);
            const tick = cur - n;
            return finalize(tick, `${n} turns ago (tick ${tick})`);
        }

        // "<N> <unit> ago" or "-<N><unit>"
        const relMatch = s.match(/^(?:(\d+(?:\.\d+)?)|a|an)\s*(minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|wks?|w|months?|mos?|years?|yrs?|y)\s*(?:ago|back|earlier|before)?$/i);
        if (relMatch) {
            const amount = relMatch[1] ? parseFloat(relMatch[1]) : 1;
            const unit = relMatch[2].toLowerCase();
            let minutes = amount;
            let unitLabel = 'min';
            if (unit.startsWith('h')) {
                minutes = amount * 60;
                unitLabel = amount === 1 ? 'hour' : 'hours';
            } else if (unit.startsWith('d')) {
                minutes = amount * 1440;
                unitLabel = amount === 1 ? 'day' : 'days';
            } else if (unit.startsWith('w')) {
                minutes = amount * 10080;
                unitLabel = amount === 1 ? 'week' : 'weeks';
            } else if (unit.startsWith('mo')) {
                minutes = amount * 43200;
                unitLabel = amount === 1 ? 'month' : 'months';
            } else if (unit.startsWith('y')) {
                minutes = amount * 525600;
                unitLabel = amount === 1 ? 'year' : 'years';
            } else {
                unitLabel = amount === 1 ? 'minute' : 'minutes';
            }
            const deltaTicks = Math.max(1, Math.round(minutes / mpt));
            const tick = cur - deltaTicks;
            return finalize(tick, `${amount} ${unitLabel} ago (tick ${tick})`);
        }

        // "tick -250", "t120", "-250", "120"
        const tickMatch = s.match(/^(?:tick\s*|t)?([+-]?\d+)$/i);
        if (tickMatch) {
            const tick = parseInt(tickMatch[1], 10);
            if (!isNaN(tick)) {
                return finalize(tick, tick < 0 ? `${-tick} turns before start (tick ${tick})` : `tick ${tick}`);
            }
        }
        return null;
    };

    /**
     * Strip LLM commentary or duplicated conversational framing from memory text
     * so `memory.text` only ever stores the character's first-person memory (bug-519).
     */
    M.stripEditorialLeakage = function (memText: string, characterReply = ''): string {
        let cleaned = String(memText ?? '').trim();
        if (!cleaned) return '';
        const reply = String(characterReply ?? '').trim();
        if (reply && cleaned.length > reply.length + 10) {
            if (cleaned.startsWith(reply)) {
                cleaned = cleaned.slice(reply.length).replace(/^[\s\-:]+/, '').trim();
            } else if (cleaned.endsWith(reply)) {
                cleaned = cleaned.slice(0, cleaned.length - reply.length).replace(/[\s\-:]+$/, '').trim();
            }
        }
        const paragraphs = cleaned.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
        if (paragraphs.length > 1) {
            const last = paragraphs[paragraphs.length - 1];
            const metaPattern = /^(?:note|commentary|analysis|explanation|context|meta|author'?s?\s+note|\(note|\[note|this\s+memory\s+(?:reflects|captures|shows|establishes)|in\s+this\s+memory\b|as\s+requested\b)/i;
            if (metaPattern.test(last)) {
                paragraphs.pop();
            }
            cleaned = paragraphs.join('\n\n');
        }
        return cleaned.trim();
    };

    /**
     * Parse a model-returned Weaver or seed-memory JSON response.
     * Supports both the nested Weaver schema (`{character_reply, memory, counterpart_memory}`)
     * and the legacy flat schema (`{text, importance, tags, emotions}`).
     * Tolerates code fences, surrounding prose, and trailing commas.
     */
    M.parseWeaverResponse = function (raw: string): MemoryViewWeaverDraft | null {
        if (!raw) return null;
        let s = String(raw).trim();
        const fence = s.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
        if (fence) s = fence[1].trim();
        const objMatch = s.match(/\{[\s\S]*\}/);
        if (!objMatch) return null;
        s = objMatch[0].replace(/,\s*([}\]])/g, '$1');
        let parsed: any;
        try {
            parsed = JSON.parse(s);
        } catch (_e) {
            return null;
        }
        if (!parsed || typeof parsed !== 'object') return null;

        const memBlock = (parsed.memory && typeof parsed.memory === 'object') ? parsed.memory : parsed;
        const rawReply = String(parsed.character_reply || parsed.reply || '').trim();
        const rawText = String(memBlock.text || parsed.text || '').trim();
        const cleanText = M.stripEditorialLeakage(rawText, rawReply);

        const rawEmos = Array.isArray(memBlock.memory_emotions)
            ? memBlock.memory_emotions
            : (Array.isArray(memBlock.emotions) ? memBlock.emotions : (Array.isArray(parsed.emotions) ? parsed.emotions : []));
        const emotions: MemoryViewEmotion[] = rawEmos
            .filter((e: any) => e && e.label)
            .map((e: any) => ({
                label: String(e.label).trim().toLowerCase(),
                intensity: Math.max(1, Math.min(10, parseInt(String(e.intensity ?? 5), 10) || 5))
            }));

        const rawDeltas = Array.isArray(memBlock.relationship_deltas)
            ? memBlock.relationship_deltas
            : (Array.isArray(parsed.relationship_deltas) ? parsed.relationship_deltas : []);
        const relationship_deltas: MemoryViewRelationshipDelta[] = rawDeltas
            .filter((d: any) => d && d.who && typeof d.data === 'object')
            .map((d: any) => {
                const cleanData: Record<string, number> = {};
                for (const [k, v] of Object.entries(d.data || {})) {
                    const num = parseFloat(String(v));
                    if (!isNaN(num) && Math.abs(num) > 0) {
                        cleanData[String(k).trim().toLowerCase()] = Math.max(-5, Math.min(5, num));
                    }
                }
                return {
                    who: String(d.who).trim(),
                    why: String(d.why || '').trim(),
                    data: cleanData
                };
            });

        const tags = Array.isArray(memBlock.tags)
            ? memBlock.tags.filter(Boolean).map((t: any) => String(t).trim().toLowerCase())
            : [];
        const entities = Array.isArray(memBlock.entities)
            ? memBlock.entities.filter(Boolean).map((e: any) => String(e).trim())
            : [];
        const imp = parseInt(String(memBlock.importance ?? parsed.importance ?? 5), 10);
        const importance = !isNaN(imp) ? Math.max(1, Math.min(10, imp)) : 5;
        const confRaw = parseFloat(String(memBlock.confidence ?? parsed.confidence ?? 0.85));
        const confidence = !isNaN(confRaw)
            ? (confRaw > 1 ? Math.max(0.05, Math.min(1, confRaw / 100)) : Math.max(0.05, Math.min(1, confRaw)))
            : 0.85;
        const offsetRaw = memBlock.tick_offset_minutes ?? parsed.tick_offset_minutes;
        const tick_offset_minutes = (offsetRaw !== undefined && offsetRaw !== null && !isNaN(Number(offsetRaw)))
            ? Number(offsetRaw)
            : null;

        let counterpart_memory: MemoryViewCounterpartDraft | null = null;
        const cp = parsed.counterpart_memory || memBlock.counterpart_memory;
        if (cp && typeof cp === 'object' && cp.who && cp.text) {
            const cpEmos = (Array.isArray(cp.memory_emotions) ? cp.memory_emotions : (Array.isArray(cp.emotions) ? cp.emotions : []))
                .filter((e: any) => e && e.label)
                .map((e: any) => ({
                    label: String(e.label).trim().toLowerCase(),
                    intensity: Math.max(1, Math.min(10, parseInt(String(e.intensity ?? 5), 10) || 5))
                }));
            const cpDeltas = (Array.isArray(cp.relationship_deltas) ? cp.relationship_deltas : [])
                .filter((d: any) => d && d.who && typeof d.data === 'object')
                .map((d: any) => ({
                    who: String(d.who).trim(),
                    why: String(d.why || '').trim(),
                    data: d.data as Record<string, number>
                }));
            counterpart_memory = {
                who: String(cp.who).trim(),
                text: M.stripEditorialLeakage(String(cp.text).trim()),
                importance: Math.max(1, Math.min(10, parseInt(String(cp.importance ?? importance), 10) || importance)),
                memory_emotions: cpEmos,
                relationship_deltas: cpDeltas
            };
        }

        const type = String(memBlock.type || parsed.type || (relationship_deltas.length ? 'event' : 'memory')).trim();
        const category = String(
            memBlock.category || parsed.category || (relationship_deltas.length ? 'social' : (type === 'reflection' ? 'belief' : 'episodic'))
        ).trim();

        return {
            character_reply: rawReply,
            text: cleanText,
            type,
            category,
            importance,
            confidence,
            tick_offset_minutes,
            location: String(memBlock.location || parsed.location || '').trim(),
            entities,
            tags,
            emotions,
            memory_emotions: emotions,
            relationship_deltas,
            derived_expectation: String(memBlock.derived_expectation || parsed.derived_expectation || '').trim(),
            counterpart_memory
        };
    };

    M._parseSeedJson = function (raw: string): any {
        return M.parseWeaverResponse(raw);
    };

    M.addMemory = function (charName: string): void {
        M.showMemoryEditor(charName, null);
    };

    M.editMemory = function (charName: string, entryId: string): void {
        M.showMemoryEditor(charName, entryId);
    };

    M.openWeaver = function (charName: string, opts?: MemoryViewEditorOptions): void {
        M.showMemoryEditor(charName, null, { ...(opts || {}), openWeaver: true });
    };

    M.openWeaverAtTick = function (charName: string, tick: number, mode: 'opinion' | 'event' | 'social' = 'event'): void {
        M.showMemoryEditor(charName, null, { tick, mode, openWeaver: true });
    };

    M.suppressMemory = function (charName: string, entryId: string): void {
        (ApiClient as unknown as MemoryViewApiClient).suppressPlayerMemory(charName, { tags: [], duration: 1 }).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    M.unblockMemory = function (charName: string, entryId: string): void {
        (ApiClient as unknown as MemoryViewApiClient).unblockPlayerMemory(charName, {}).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    M.clearExpired = function (charName: string): void {
        const currentTick = VW?.state?.tick ?? 0;
        (ApiClient as unknown as MemoryViewApiClient).clearExpiredSuppressions(charName, currentTick).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    /**
     * Fetch the character's grounding & preview bundle from
     * `POST /api/players/<name>/memories/context`.
     */
    M.fetchMemoryContext = async function (charName: string, query = '', candidate: any = null): Promise<any> {
        try {
            const data = await ApiClient.getPlayerMemoriesContext(charName, { query, candidate });
            if (data.error) return null;
            return data;
        } catch (_e) {
            return null;
        }
    };

    M.showMemoryEditor = function (charName: string, entryId: string | null, opts?: MemoryViewEditorOptions): void {
        const player = worldState.players?.[charName];
        if (!player) return;
        M._closeMemoryEditor();
        const memories = player.memories || [];
        const existing = entryId ? memories.find((m: any) => m.id === entryId) : null;
        const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]): unknown => window.Lit.html(strings, ...values);
        const nothing = window.Lit.nothing;
        const esc = InspectorHelpers.esc;
        const escName = charName.replace(/'/g, "\\'");
        const currentTick = VW?.state?.tick ?? 0;
        const initialMode: 'opinion' | 'event' | 'social' = opts?.mode || 'event';

        const types = ['memory','observation','conversation','location','event','thought','reflection','discovery','combat','speech','reaction','item','exploration','action','failure','success','dream','expectation'];
        const defaultType = existing?.type || (initialMode === 'opinion' ? 'reflection' : 'memory');
        const typeOpts = types.map(t => htmlTag`<option value=${t} ?selected=${defaultType === t}>${t}</option>`);

        const categories = ['episodic', 'semantic', 'procedural', 'social', 'belief'];
        const deriveCat = (m: any): string => {
            if (m?.category) return String(m.category);
            if (String(m?.type || '') === 'reflection') return 'belief';
            const memTags = Array.isArray(m?.tags) ? m.tags.map((t: any) => String(t).toLowerCase()) : [];
            if (memTags.some((t: string) => t.startsWith('rel:'))) return 'social';
            return 'episodic';
        };
        const existingCat = existing
            ? String(existing.category || deriveCat(existing))
            : (initialMode === 'opinion' ? 'belief' : (initialMode === 'social' ? 'social' : ''));
        const catOpts = htmlTag`<option value="" ?selected=${!existingCat}>auto (from type)</option>${categories.map(c => htmlTag`<option value=${c} ?selected=${existingCat === c}>${c}</option>`)}`;
        const confPct = existing && typeof existing.confidence === 'number' ? Math.round(existing.confidence * 100) : null;
        const dynamics = existing
            ? `activation ${typeof existing.activation === 'number' ? existing.activation.toFixed(2) : '1.00'} · ↻ ${Number(existing.reinforcements) || 0}×${existing.last_recalled_tick != null ? ` · last recalled tick ${existing.last_recalled_tick}` : ''}${Number(existing.reflection_depth) > 0 ? ` · derived (depth ${existing.reflection_depth})` : ''}`
            : '';

        const tick = opts?.tick !== undefined ? opts.tick : (existing?.tick ?? currentTick);
        const preTicks = tick < 0 ? -tick : 0;

        const embedEnabled = !!(window.EmbeddingClient && window.EmbeddingClient.configured());
        const salience = existing?.salience_override || 0;

        M._gen = {
            charName,
            mode: initialMode,
            history: [],
            contextBundle: null,
            counterpartDraft: null
        };

        const modePlaceholder = (m: string): string => {
            if (m === 'opinion') {
                return `Ask ${charName} what they thought of a movie, book, place, or idea (e.g. "What did you think of the horror movie we watched last night?")...`;
            }
            if (m === 'social') {
                return `Describe a past moment between ${charName} and someone else (e.g. "Three days ago Rex shared his rations with you when you were starving")...`;
            }
            return `Describe a past event or memory in natural language (e.g. "Two years ago a kitchen fire burned your hand and made you cautious around stoves")...`;
        };

        const modal = htmlTag`<div class="modal-content memedit-modal" style="max-width:740px;max-height:90vh;overflow-y:auto;">
            <div class="modal-header" style="border-bottom:none;padding:16px 20px 6px;display:flex;align-items:center;justify-content:space-between;">
                <h3 style="font-size:15px;font-weight:700;margin:0;">${existing ? `✏️ Edit & Weave Memory - ${charName}` : `✨ Memory Weaver & Editor - ${charName}`}</h3>
                <span style="font-size:10px;color:var(--text-muted);font-family:monospace;">current tick: ${currentTick}</span>
            </div>
            <div style="padding:0 20px 16px;">
                <div class="memedit-section" style="border:1px solid #1f6feb55;background:var(--bg-inset);border-radius:8px;padding:10px 12px;margin-bottom:12px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
                        <div class="memedit-section-title" style="margin:0;">✨ Weave in ${charName}'s Voice (Natural Language)</div>
                        <div style="display:flex;gap:4px;flex-wrap:wrap;" id="mem-weaver-modes">
                            <button type="button" class="btn btn-sm mem-mode-btn" data-weaver-mode="opinion" style="font-size:10px;padding:2px 8px;${initialMode === 'opinion' ? 'border-color:#58a6ff;color:#58a6ff;' : ''}">💬 Ask Opinion / Reaction</button>
                            <button type="button" class="btn btn-sm mem-mode-btn" data-weaver-mode="event" style="font-size:10px;padding:2px 8px;${initialMode === 'event' ? 'border-color:#58a6ff;color:#58a6ff;' : ''}">🕰️ Backdate Event</button>
                            <button type="button" class="btn btn-sm mem-mode-btn" data-weaver-mode="social" style="font-size:10px;padding:2px 8px;${initialMode === 'social' ? 'border-color:#58a6ff;color:#58a6ff;' : ''}">🤝 About a Person</button>
                        </div>
                    </div>
                    <p id="mem-weaver-hint" style="font-size:10.5px;color:var(--text-muted);line-height:1.45;margin:0 0 6px;">Ask a question, describe a backdated event, or refine the draft below. ${charName} reacts in voice and drafts the structured memory fields.</p>
                    <textarea id="mem-gen-prompt" rows="2" class="memedit-textarea" style="min-height:52px;" placeholder="${modePlaceholder(initialMode)}">${opts?.prompt || ''}</textarea>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px;">
                        <button type="button" class="btn btn-sm btn-blue" id="mem-gen-run">✨ Weave / Refine</button>
                        <span id="mem-gen-status" class="memedit-status" style="font-size:10.5px;">&nbsp;</span>
                    </div>
                    <div id="mem-weaver-reply-box" style="display:none;margin-top:8px;padding:8px 10px;background:var(--bg-card);border-left:3px solid #bc8cff;border-radius:6px;">
                        <div style="font-size:9px;color:#bc8cff;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px;">🗣️ ${charName}'s reaction (kept separate from stored memory text)</div>
                        <div id="mem-weaver-reply" style="font-size:11px;font-style:italic;color:var(--text);line-height:1.45;"></div>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">📝 Memory Text (First-Person Record)</div>
                    <textarea id="mem-editor-content" rows="3" class="memedit-textarea" style="min-height:74px;" placeholder="First-person memory text stored on ${charName}...">${existing ? existing.text : ''}</textarea>
                    <textarea id="mem-gen-result" style="display:none;">${existing ? existing.text : ''}</textarea>
                    <div id="mem-editor-contra-preview" style="display:none;margin-top:6px;padding:6px 8px;background:#3d1a1a;border:1px solid #e05555;border-radius:6px;font-size:10.5px;color:#ff9b9b;"></div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">🕰️ When & Dynamics (Backdating)</div>
                    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:8px;">
                        <input type="text" id="mem-editor-reltime" placeholder="Relative time (e.g. '3 days ago', '2 hours ago', '5 years ago', '100 turns before start')" style="flex:1;min-width:210px;font-size:11px;padding:4px 8px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
                        <span id="mem-editor-reltime-preview" style="font-size:10px;color:#58a6ff;font-family:monospace;">tick ${tick}</span>
                    </div>
                    <div id="mem-editor-birth-gate" style="display:none;margin-bottom:8px;padding:5px 8px;border-radius:5px;font-size:10px;font-family:monospace;"></div>
                    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px;">
                        <button type="button" class="btn btn-sm mem-time-preset" data-rel="now" style="font-size:9.5px;padding:1px 6px;">Now</button>
                        <button type="button" class="btn btn-sm mem-time-preset" data-rel="1 hour ago" style="font-size:9.5px;padding:1px 6px;">1h ago</button>
                        <button type="button" class="btn btn-sm mem-time-preset" data-rel="yesterday" style="font-size:9.5px;padding:1px 6px;">Yesterday</button>
                        <button type="button" class="btn btn-sm mem-time-preset" data-rel="1 week ago" style="font-size:9.5px;padding:1px 6px;">1w ago</button>
                        <button type="button" class="btn btn-sm mem-time-preset" data-rel="1 year ago" style="font-size:9.5px;padding:1px 6px;">1y ago</button>
                        <button type="button" class="btn btn-sm mem-time-preset" data-rel="100 turns before start" style="font-size:9.5px;padding:1px 6px;">Pre-start (-100t)</button>
                    </div>
                    <div class="memedit-grid">
                        <div class="memedit-field" style="flex:1.3;">
                            <label>Type</label>
                            <select id="mem-editor-type">${typeOpts}</select>
                        </div>
                        <div class="memedit-field" style="flex:1;">
                            <label>Category (kind)</label>
                            <select id="mem-editor-category">${catOpts}</select>
                            <div class="memedit-hint">episodic / belief / social…</div>
                        </div>
                        <div class="memedit-field" style="flex:.8;">
                            <label>Importance (1-10)</label>
                            <input type="number" id="mem-editor-importance" min="1" max="10" value="${existing?.importance ?? 5}">
                        </div>
                        <div class="memedit-field" style="flex:.8;">
                            <label>Confidence (0-100)</label>
                            <input type="number" id="mem-editor-confidence" min="0" max="100" value="${confPct ?? 85}" placeholder="85">
                            <div class="memedit-hint">how sure the character is</div>
                        </div>
                        <div class="memedit-field" style="flex:.8;">
                            <label>Tick</label>
                            <input type="number" id="mem-editor-tick" value="${tick}">
                            <div class="memedit-hint">negative = before start</div>
                        </div>
                        <div class="memedit-field" style="flex:.95;">
                            <label>Turns before start</label>
                            <input type="number" id="mem-editor-prestart" min="0" value="${preTicks}" placeholder="0">
                            <div class="memedit-hint">simulate pre-scenario age</div>
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-top:6px;">
                        <label style="display:flex;align-items:center;gap:5px;font-size:10.5px;color:var(--text-dim);cursor:pointer;">
                            <input type="checkbox" id="mem-editor-age-decay" ?checked=${tick < currentTick}>
                            Simulate natural age decay for backdated memory (sets initial activation from elapsed ticks & resistance)
                        </label>
                        ${dynamics ? htmlTag`<div style="font-size:10px;color:var(--text-muted);" title="Live memory dynamics (read-only here - recall and decay move them)">📊 ${dynamics}</div>` : nothing}
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">💓 Emotions & Interpersonal Feelings</div>
                    <div class="memedit-field">
                        <label>Attached emotions (multiple)</label>
                        <div id="mem-gen-emotions" class="memedit-entitybox"></div>
                    </div>
                    <div class="memedit-field" style="margin-top:8px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                            <label style="margin:0;">Feelings toward other people (shifts derived trust / fear / attraction / respect)</label>
                            <button type="button" class="btn btn-sm" id="mem-rel-delta-add" style="font-size:10px;padding:1px 8px;">+ Add Person Delta</button>
                        </div>
                        <div id="mem-editor-rel-deltas"></div>
                        <div id="mem-editor-rel-preview" style="margin-top:6px;"></div>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">🌐 Context & Entities</div>
                    <div class="memedit-grid">
                        <div class="memedit-field">
                            <label>Source</label>
                            <input type="text" id="mem-editor-source" value="${existing ? esc(existing.source || 'manual') : 'manual'}" placeholder="auto / manual / trigger">
                        </div>
                        <div class="memedit-field">
                            <label>Location</label>
                            <input type="text" id="mem-editor-location" value="${existing ? existing.location || '' : ''}" placeholder="Area name">
                        </div>
                        <div class="memedit-field" style="flex:.7;">
                            <label>Salience (0-10)</label>
                            <input type="number" id="mem-editor-salience" min="0" max="10" value="${salience}" placeholder="0">
                            <div class="memedit-hint">recall boost</div>
                        </div>
                    </div>
                    <div class="memedit-field">
                        <label>Entity references (areas / items / characters)</label>
                        <div id="mem-editor-entities" class="memedit-entitybox"></div>
                    </div>
                    <div class="memedit-field" style="margin-top:6px;">
                        <label>Derived procedural expectation (optional rule/habit learned from this memory)</label>
                        <input type="text" id="mem-editor-expectation" value="" placeholder="e.g. When I smell smoke in the kitchen, I check the stove immediately." style="width:100%;font-size:11px;padding:4px 8px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;">
                    </div>
                    <div id="mem-editor-counterpart-box" style="display:none;margin-top:8px;padding:8px 10px;background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;">
                        <label style="display:flex;align-items:center;gap:6px;font-size:11px;font-weight:600;cursor:pointer;">
                            <input type="checkbox" id="mem-editor-counterpart-enable">
                            <span id="mem-editor-counterpart-label">Also record counterpart memory on the other character</span>
                        </label>
                        <textarea id="mem-editor-counterpart-text" rows="2" class="memedit-textarea" style="margin-top:6px;min-height:48px;font-size:11px;"></textarea>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">⚡ Connections & Tags</div>
                    <div class="memedit-field">
                        <label>Contradicts (memories this one conflicts with)</label>
                        <div id="mem-editor-contradicts" style="display:flex;flex-wrap:wrap;gap:4px;min-height:24px;"></div>
                    </div>
                    ${memories.filter((m: any) => m.id && m.id !== existing?.id).length
                        ? htmlTag`<div class="memedit-field">
                            <label>Link a conflicting memory</label>
                            <select id="mem-editor-contra-add">
                                <option value="">- choose a memory -</option>
                                ${memories.filter((m: any) => m.id && m.id !== existing?.id).slice(0, 200).map((m: any) => htmlTag`<option value=${m.id}>${String(m.id)} - ${String(m.text || '').slice(0, 60)}</option>`)}
                            </select>
                            <div class="memedit-hint">marking only - the engine never resolves a contradiction for the character</div>
                          </div>`
                        : nothing}
                    <div class="memedit-field" style="margin-top:6px;">
                        <label>Tags</label>
                        <div id="mem-editor-tags" style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:6px;"></div>
                    </div>
                </div>

                <div class="memedit-section">
                    <div class="memedit-section-title">🧠 Semantic</div>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                        <span style="font-size:11px;color:var(--text-muted);">Semantic memory:</span>
                        <span id="mem-editor-embed-status" class="memedit-status" style="color:${embedEnabled ? '#4caf50' : '#9aa4b2'};">${embedEnabled ? 'configured' : 'disabled'}</span>
                        ${existing ? htmlTag`<button class="btn btn-sm" id="mem-editor-embed-btn" style="font-size:10px;">🧠 Generate Embedding</button>` : nothing}
                    </div>
                    ${existing && existing.suppressions && existing.suppressions.length
                        ? htmlTag`<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:8px;">
                            <span style="font-size:11px;color:var(--text-muted);">Suppressions:</span>
                            <span style="font-size:10px;color:#e05555;">🚫 Blocked (${existing.suppressions.length})</span>
                            <button class="btn btn-sm" onclick="InspectorMemory.unblockMemory('${escName}','${existing.id}');document.getElementById('mem-editor-modal')?.remove();" style="font-size:10px;">🔓 Unblock</button>
                          </div>`
                        : nothing}
                </div>
            </div>
            <div class="memedit-foot">
                <button class="btn btn-sm btn-ghost" @click=${() => M._closeMemoryEditor()}>Cancel</button>
                <button class="btn btn-sm btn-green" id="mem-gen-save" @click=${() => M.saveMemory(charName, entryId || '')}>💾 Save Memory</button>
            </div>
        </div>`;

        const container = document.createElement('div');
        container.className = 'modal-overlay';
        container.id = 'mem-editor-modal';
        document.body.appendChild(container);
        window.Lit.render(modal, container);

        // 1. Emotions selector
        const initialEmos: MemoryViewEmotion[] = existing
            ? (Array.isArray(existing.memory_emotions) && existing.memory_emotions.length
                ? existing.memory_emotions
                : (existing.emotion && existing.emotion.label ? [existing.emotion] : []))
            : [];
        const genEmoEl = container.querySelector('#mem-gen-emotions') as HTMLElement | null;
        if (genEmoEl) M._attachEmotionSelector(genEmoEl, initialEmos);

        // 2. Relationship deltas selector
        const initialDeltas: MemoryViewRelationshipDelta[] = [];
        if (existing) {
            if (Array.isArray(existing.relationship_deltas) && existing.relationship_deltas.length) {
                existing.relationship_deltas.forEach((d: any) => {
                    if (d && d.who) initialDeltas.push({ who: d.who, why: d.why || '', data: { ...(d.data || {}) } });
                });
            } else if (existing.emotions && existing.emotions.who) {
                initialDeltas.push({
                    who: existing.emotions.who,
                    why: existing.emotions.why || '',
                    data: { ...(existing.emotions.data || {}) }
                });
            }
        } else if (opts?.targetPerson) {
            initialDeltas.push({ who: opts.targetPerson, why: '', data: {} });
        }
        const relDeltasEl = container.querySelector('#mem-editor-rel-deltas') as HTMLElement | null;
        if (relDeltasEl) M._attachRelationshipDeltaEditor(charName, relDeltasEl, initialDeltas);
        const addDeltaBtn = container.querySelector('#mem-rel-delta-add');
        if (addDeltaBtn && relDeltasEl) {
            addDeltaBtn.addEventListener('click', () => {
                M._relDeltas = M._relDeltas || [];
                const others = Object.keys(worldState.players || {}).filter(p => p !== charName);
                M._relDeltas.push({ who: others[0] || '', why: '', data: {} });
                M._attachRelationshipDeltaEditor(charName, relDeltasEl, M._relDeltas);
                M._refreshLivePreview(charName);
            });
        }

        // 3. Tag multiselect
        if (window.TagMultiselect) {
            const tagsEl = document.getElementById('mem-editor-tags');
            if (tagsEl) {
                M._tagSelect = new window.TagMultiselect(tagsEl, {
                    tags: Array.isArray(existing?.tags) ? existing.tags : [],
                    placeholder: 'Search or create tags...',
                    allowNew: true,
                    onChange: (tags: string[]) => { M._tagSelectTags = tags; }
                });
                M._genTagSelect = M._tagSelect;
            }
        }

        // 4. Entity-reference multiselect
        M._entitySelected = new Set<string>((existing?.entity_ids || []).filter(Boolean));
        const entEl = document.getElementById('mem-editor-entities');
        if (entEl) M._attachEntitySelector(entEl);

        // 5. Contradiction links
        M._contraRemoved = new Set<string>();
        M._contraAdded = [];
        const contraEl = document.getElementById('mem-editor-contradicts');
        const contraRemoved = (): Set<string> => M._contraRemoved || new Set<string>();
        const contraAdded = (): string[] => M._contraAdded || [];
        const renderContra = () => {
            if (!contraEl) return;
            const current = (existing?.contradicts || []).filter((id: string) => !contraRemoved().has(id));
            const all = current.concat(contraAdded());
            if (!all.length) {
                const noConf = document.createElement('span');
                noConf.style.cssText = 'font-size:10px;color:var(--text-muted);';
                noConf.textContent = 'no conflicts marked';
                contraEl.replaceChildren(noConf);
                return;
            }
            contraEl.replaceChildren(document.createRange().createContextualFragment(all.map((id: string) => {
                const target = memories.find((m: any) => m.id === id);
                const label = target ? String(target.text || '').slice(0, 40) : String(id);
                return `<span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;color:#e05555;border:1px solid #6e2c2c;border-radius:8px;padding:1px 6px;" title="${esc(label)}">⚡ ${esc(id)} ${esc(label)}<button type="button" data-contra-id="${esc(id)}" style="background:none;border:none;color:#e05555;cursor:pointer;font-size:10px;padding:0;">×</button></span>`;
            }).join('')));
            contraEl.querySelectorAll<HTMLButtonElement>('button[data-contra-id]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const id = btn.getAttribute('data-contra-id') || '';
                    M._contraAdded = contraAdded().filter(a => a !== id);
                    M._contraRemoved = contraRemoved();
                    M._contraRemoved.add(id);
                    renderContra();
                });
            });
        };
        renderContra();
        const contraAdd = container.querySelector('#mem-editor-contra-add');
        if (contraAdd) {
            contraAdd.addEventListener('change', () => {
                const id = (contraAdd as HTMLSelectElement).value;
                if (!id) return;
                if (!(existing?.contradicts || []).includes(id) && !contraAdded().includes(id)) {
                    M._contraAdded = contraAdded();
                    M._contraAdded.push(id);
                    M._contraRemoved = contraRemoved();
                    M._contraRemoved.delete(id);
                }
                (contraAdd as HTMLSelectElement).value = '';
                renderContra();
            });
        }

        // 6. Relative time & presets wiring + birthday gate
        const relInput = container.querySelector('#mem-editor-reltime') as HTMLInputElement | null;
        const relPreview = container.querySelector('#mem-editor-reltime-preview') as HTMLElement | null;
        const birthGateEl = container.querySelector('#mem-editor-birth-gate') as HTMLElement | null;
        const tickInputEl = container.querySelector('#mem-editor-tick') as HTMLInputElement | null;
        const preInputEl = container.querySelector('#mem-editor-prestart') as HTMLInputElement | null;
        const ageDecayCb = container.querySelector('#mem-editor-age-decay') as HTMLInputElement | null;
        const getBirthBounds = () => {
            const b = M._gen?.contextBundle;
            const bTick = b?.birth_tick !== undefined ? b.birth_tick : (player as any)?.birth_tick;
            return {
                birthTick: (bTick !== null && bTick !== undefined && Number.isFinite(Number(bTick))) ? Math.round(Number(bTick)) : null,
                birthday: b?.birthday || null,
                age: b?.age !== undefined ? b.age : null,
            };
        };
        const renderBirthGate = (candTick: number, wasClampedFrom?: number) => {
            if (!birthGateEl) return;
            const { birthTick, birthday, age } = getBirthBounds();
            if (birthTick === null) {
                birthGateEl.style.display = 'none';
                return;
            }
            if (tickInputEl) tickInputEl.min = String(birthTick);
            const bdayMeta = [birthday ? `🎂 ${birthday}` : '', age != null ? `age ${age}` : ''].filter(Boolean).join(', ');
            birthGateEl.style.display = 'block';
            if (candTick < birthTick || wasClampedFrom !== undefined) {
                birthGateEl.style.cssText = 'display:block;margin-bottom:8px;padding:5px 8px;border-radius:5px;font-size:10px;font-family:monospace;background:#3d1a1a;border:1px solid #e05555;color:#ff9b9b;';
                const badTick = wasClampedFrom !== undefined ? wasClampedFrom : candTick;
                birthGateEl.textContent = `⛔ Cannot create memory at tick ${badTick}: ${charName} was not born until tick ${birthTick}${bdayMeta ? ` (${bdayMeta})` : ''}.`;
            } else {
                birthGateEl.style.cssText = 'display:block;margin-bottom:8px;padding:4px 8px;border-radius:5px;font-size:10px;font-family:monospace;background:var(--bg-inset);border:1px solid var(--border);color:var(--text-muted);';
                birthGateEl.textContent = `🎂 Earliest allowed memory (birthday): tick ${birthTick}${bdayMeta ? ` (${bdayMeta})` : ''}`;
            }
        };
        const applyRelativeExpr = (expr: string) => {
            const mpt = M._gen?.contextBundle?.time_per_tick_minutes || (window as any).config?.minutes_per_tick || 1;
            const { birthTick } = getBirthBounds();
            const parsed = M.parseRelativeTime(expr, currentTick, mpt, birthTick);
            if (!parsed) return;
            if (tickInputEl) tickInputEl.value = String(parsed.tick);
            if (preInputEl) preInputEl.value = parsed.tick < 0 ? String(-parsed.tick) : '0';
            if (relPreview) {
                relPreview.textContent = parsed.label;
                relPreview.style.color = parsed.beforeBirth ? '#e05555' : '#58a6ff';
            }
            if (ageDecayCb) ageDecayCb.checked = parsed.tick < currentTick;
            renderBirthGate(parsed.tick, parsed.unclampedTick);
        };
        if (relInput) {
            relInput.addEventListener('input', () => applyRelativeExpr(relInput.value));
        }
        container.querySelectorAll<HTMLButtonElement>('.mem-time-preset').forEach(btn => {
            btn.addEventListener('click', () => {
                const expr = btn.dataset.rel || 'now';
                if (relInput) relInput.value = expr;
                applyRelativeExpr(expr);
            });
        });
        if (tickInputEl) {
            tickInputEl.addEventListener('input', () => {
                const t = parseInt(tickInputEl.value, 10) || 0;
                if (preInputEl) preInputEl.value = t < 0 ? String(-t) : '0';
                if (relPreview) {
                    relPreview.textContent = `tick ${t}`;
                    relPreview.style.color = '#58a6ff';
                }
                renderBirthGate(t);
            });
        }
        if (preInputEl) {
            preInputEl.addEventListener('input', () => {
                const pre = parseInt(preInputEl.value, 10) || 0;
                if (pre > 0 && tickInputEl) {
                    tickInputEl.value = String(-pre);
                    if (relPreview) relPreview.textContent = `${pre} turns before start (tick -${pre})`;
                    renderBirthGate(-pre);
                }
            });
        }
        renderBirthGate(tick);

        // 7. Weaver mode pills & Run button
        const promptArea = container.querySelector('#mem-gen-prompt') as HTMLTextAreaElement | null;
        container.querySelectorAll<HTMLButtonElement>('.mem-mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = (btn.dataset.weaverMode || 'event') as 'opinion' | 'event' | 'social';
                if (M._gen) M._gen.mode = mode;
                container.querySelectorAll<HTMLButtonElement>('.mem-mode-btn').forEach(b => {
                    const active = b.dataset.weaverMode === mode;
                    b.style.borderColor = active ? '#58a6ff' : '';
                    b.style.color = active ? '#58a6ff' : '';
                });
                if (promptArea) promptArea.placeholder = modePlaceholder(mode);
                const catSel = container.querySelector('#mem-editor-category') as HTMLSelectElement | null;
                if (catSel && !existing) {
                    catSel.value = mode === 'opinion' ? 'belief' : (mode === 'social' ? 'social' : 'episodic');
                }
            });
        });

        const runBtn = container.querySelector('#mem-gen-run');
        if (runBtn) runBtn.addEventListener('click', () => M._runMemoryGeneration());

        // Keep #mem-gen-result and #mem-editor-content synchronized for callers inspecting either ID
        const contentArea = container.querySelector('#mem-editor-content') as HTMLTextAreaElement | null;
        const hiddenResult = container.querySelector('#mem-gen-result') as HTMLTextAreaElement | null;
        if (contentArea) {
            contentArea.addEventListener('input', () => {
                if (hiddenResult) hiddenResult.value = contentArea.value;
                M._refreshLivePreview(charName);
            });
        }
        if (hiddenResult) {
            hiddenResult.addEventListener('input', () => {
                if (contentArea) contentArea.value = hiddenResult.value;
            });
        }

        // 8. Embedding button (existing memories only)
        const embedBtn = container.querySelector('#mem-editor-embed-btn');
        if (embedBtn && existing) {
            embedBtn.addEventListener('click', () => {
                const status = container.querySelector('#mem-editor-embed-status') as HTMLElement;
                const text = (container.querySelector('#mem-editor-content') as HTMLTextAreaElement | null)?.value || '';
                status.textContent = 'embedding…'; status.style.color = '#9aa4b2';
                M._embedForEntry(charName, existing.id, text).then(ok => {
                    status.textContent = ok ? '✓ embedding saved' : '✗ embed failed';
                    status.style.color = ok ? '#4caf50' : '#e05555';
                });
            });
        }

        // 9. Fetch grounding context asynchronously on open
        M.fetchMemoryContext(charName, existing?.text || '').then(bundle => {
            if (bundle && M._gen && M._gen.charName === charName) {
                M._gen.contextBundle = bundle;
                const curTickVal = parseInt(tickInputEl?.value || String(tick), 10);
                renderBirthGate(!isNaN(curTickVal) ? curTickVal : tick);
                if (existing || initialDeltas.length) {
                    M._refreshLivePreview(charName);
                }
            }
        });
    };

    /**
     * Attach the interpersonal feeling delta editor (`relationship_deltas`) and
     * bind it to `M._relDeltas`.
     */
    M._attachRelationshipDeltaEditor = function (
        charName: string,
        container: HTMLElement,
        initial: MemoryViewRelationshipDelta[]
    ): void {
        M._relDeltas = (Array.isArray(initial) ? initial : []).map(d => ({
            who: String(d.who || ''),
            why: String(d.why || ''),
            data: { ...(d.data || {}) }
        }));
        const others = Object.keys(worldState.players || {}).filter(p => p !== charName);

        function render(): void {
            container.replaceChildren();
            if (!M._relDeltas || M._relDeltas.length === 0) {
                const empty = document.createElement('div');
                empty.style.cssText = 'font-size:10px;color:var(--text-muted);padding:4px 0;';
                empty.textContent = 'No interpersonal shifts attached. Click "+ Add Person Delta" or weave an "About a Person" memory.';
                container.appendChild(empty);
                return;
            }
            M._relDeltas.forEach((delta, idx) => {
                const card = document.createElement('div');
                card.style.cssText = 'background:var(--bg-inset);border:1px solid var(--border);border-radius:6px;padding:6px 8px;margin-bottom:6px;';

                const topRow = document.createElement('div');
                topRow.style.cssText = 'display:flex;gap:6px;align-items:center;margin-bottom:6px;flex-wrap:wrap;';

                const whoSel = document.createElement('select');
                whoSel.style.cssText = 'font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
                const allWho = others.includes(delta.who) || !delta.who ? others : [delta.who, ...others];
                if (!allWho.length) {
                    const opt = document.createElement('option');
                    opt.value = delta.who || '';
                    opt.textContent = delta.who || '(no other characters)';
                    whoSel.appendChild(opt);
                } else {
                    allWho.forEach(name => {
                        const opt = document.createElement('option');
                        opt.value = name;
                        opt.textContent = `🧑 ${name}`;
                        if (name === delta.who) opt.selected = true;
                        whoSel.appendChild(opt);
                    });
                }
                whoSel.addEventListener('change', () => {
                    M._relDeltas![idx].who = whoSel.value;
                    M._refreshLivePreview(charName);
                });

                const whyInput = document.createElement('input');
                whyInput.type = 'text';
                whyInput.value = delta.why || '';
                whyInput.placeholder = 'Why they feel this way (e.g. shared rations, lied to me)...';
                whyInput.style.cssText = 'flex:1;min-width:160px;font-size:11px;padding:3px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
                whyInput.addEventListener('input', () => {
                    M._relDeltas![idx].why = whyInput.value;
                });

                const rmBtn = document.createElement('button');
                rmBtn.type = 'button';
                rmBtn.className = 'btn btn-sm btn-red';
                rmBtn.style.cssText = 'font-size:10px;padding:1px 6px;';
                rmBtn.textContent = '✕';
                rmBtn.addEventListener('click', () => {
                    M._relDeltas!.splice(idx, 1);
                    render();
                    M._refreshLivePreview(charName);
                });

                topRow.append(whoSel, whyInput, rmBtn);

                const dimsRow = document.createElement('div');
                dimsRow.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(95px,1fr));gap:4px;';
                REL_DIMS.forEach(dim => {
                    const wrap = document.createElement('label');
                    wrap.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:4px;font-size:10px;color:var(--text-dim);background:var(--bg-input);padding:2px 6px;border-radius:4px;border:1px solid var(--border);';
                    const span = document.createElement('span');
                    span.textContent = dim;
                    const inp = document.createElement('input');
                    inp.type = 'number';
                    inp.min = '-5';
                    inp.max = '5';
                    inp.step = '0.5';
                    inp.value = String(delta.data?.[dim] ?? 0);
                    inp.style.cssText = 'width:44px;font-size:10px;padding:1px 3px;background:var(--bg-inset);color:var(--text);border:1px solid var(--border);border-radius:3px;text-align:right;';
                    inp.addEventListener('input', () => {
                        const v = parseFloat(inp.value);
                        if (!isNaN(v) && Math.abs(v) > 0) {
                            M._relDeltas![idx].data[dim] = Math.max(-5, Math.min(5, v));
                        } else {
                            delete M._relDeltas![idx].data[dim];
                        }
                        M._refreshLivePreview(charName);
                    });
                    wrap.append(span, inp);
                    dimsRow.appendChild(wrap);
                });

                card.append(topRow, dimsRow);
                container.appendChild(card);
            });
        }
        render();
    };

    /**
     * Debounced live preview of contradiction detection and before/after
     * relationship profile shifts via `POST /api/players/<name>/memories/context`.
     */
    M._refreshLivePreview = function (charName: string): void {
        if (M._previewTimer) clearTimeout(M._previewTimer);
        M._previewTimer = setTimeout(async () => {
            const container = document.getElementById('mem-editor-modal');
            if (!container) return;
            const text = (container.querySelector('#mem-editor-content') as HTMLTextAreaElement | null)?.value?.trim() || '';
            const importance = parseInt((container.querySelector('#mem-editor-importance') as HTMLInputElement | null)?.value || '5', 10) || 5;
            const tick = parseInt((container.querySelector('#mem-editor-tick') as HTMLInputElement | null)?.value || '0', 10) || 0;
            const entity_ids = M._entitySelected ? Array.from(M._entitySelected) : [];
            const relationship_deltas = (M._relDeltas || []).filter(d => d && d.who && Object.keys(d.data || {}).length > 0);

            if (!text && !relationship_deltas.length) return;
            const bundle = await M.fetchMemoryContext(charName, text, {
                text,
                importance,
                tick,
                entity_ids,
                relationship_deltas
            });
            if (!bundle) return;
            if (M._gen && M._gen.charName === charName) {
                M._gen.contextBundle = bundle;
            }

            // Render contradiction preview banner
            const contraBox = container.querySelector('#mem-editor-contra-preview') as HTMLElement | null;
            if (contraBox) {
                const contras = Array.isArray(bundle.contradictions_preview) ? bundle.contradictions_preview : [];
                if (contras.length > 0) {
                    contraBox.style.display = 'block';
                    contraBox.replaceChildren(document.createRange().createContextualFragment(`<b>⚡ Contradiction detected (${contras.length}):</b> saving will link this memory as conflicting with `
                        + contras.map((c: any) => `<code>[${InspectorHelpers.esc(String(c.tick ?? 0))}] "${InspectorHelpers.esc(String(c.text || '').slice(0, 65))}"</code>`).join(', ')));
                } else {
                    contraBox.style.display = 'none';
                    contraBox.replaceChildren();
                }
            }

            // Render relationship before -> after preview
            const relPrevBox = container.querySelector('#mem-editor-rel-preview') as HTMLElement | null;
            if (relPrevBox) {
                const previews = Array.isArray(bundle.relationship_preview) ? bundle.relationship_preview : [];
                if (previews.length > 0) {
                    relPrevBox.replaceChildren(document.createRange().createContextualFragment(previews.map((p: any) => {
                        const b = p.before || {};
                        const a = p.after || {};
                        const shifts: string[] = [];
                        for (const dim of ['trust', 'fear', 'attraction', 'respect', 'disgust', 'familiarity']) {
                            const bv = Number(b[dim] || 0);
                            const av = Number(a[dim] || 0);
                            if (Math.abs(av - bv) >= 0.1) {
                                const color = av > bv ? (dim === 'fear' || dim === 'disgust' ? '#e05555' : '#4caf50') : (dim === 'fear' || dim === 'disgust' ? '#4caf50' : '#e05555');
                                shifts.push(`<span style="color:${color};font-family:monospace;">${dim}: ${bv} -> ${av}</span>`);
                            }
                        }
                        const roleShift = b.role !== a.role
                            ? `<span style="color:#bc8cff;">role: ${InspectorHelpers.esc(b.role || 'stranger')} -> ${InspectorHelpers.esc(a.role || 'stranger')}</span>`
                            : `<span style="color:var(--text-muted);">role: ${InspectorHelpers.esc(a.role || 'stranger')}</span>`;
                        return `<div style="font-size:10px;padding:4px 8px;background:var(--bg-card);border:1px solid var(--border);border-radius:5px;margin-top:4px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                            <b>📊 Impact on ${InspectorHelpers.esc(p.who)}:</b>
                            ${shifts.length ? shifts.join(' · ') : '<span style="color:var(--text-muted);">no net shift</span>'}
                            <span>(${roleShift})</span>
                        </div>`;
                    }).join('')));
                } else {
                    relPrevBox.replaceChildren();
                }
            }
        }, 220);
    };

    /**
     * Build a searchable multi-select of world entities (areas / items /
     * characters) and bind it to M._entitySelected. The selected ids become the
     * memory's entity_ids.
     */
    M._attachEntitySelector = function (container: HTMLElement): void {
        const nodes = worldState.graph?.nodes || {};
        const opts: MemoryViewEntityOption[] = [];
        for (const id in nodes) {
            const n = nodes[id];
            if (!n || !n.name) continue;
            opts.push({ id, name: n.name, type: n.type });
        }
        for (const cname in (worldState.players || {})) {
            const cid = 'player_' + cname.toLowerCase().replace(/\s+/g, '_');
            if (!opts.some(o => o.id === cid)) opts.push({ id: cid, name: cname, type: 'character' });
        }
        opts.sort((a, b) => a.name.localeCompare(b.name));

        container.replaceChildren();
        container.classList.add('memedit-entitybox');
        const input = document.createElement('input');
        input.className = 'memedit-search';
        input.placeholder = 'Search entities...';
        const list = document.createElement('div');
        list.className = 'memedit-entitylist';
        const typeIcon = (t: string): string => (({area:'🗺️',item:'📦',way:'🚪',character:'🧑'} as Record<string, string>)[t] || '•') + ' ';
        const selectedChips = document.createElement('div');
        selectedChips.className = 'memedit-chips';

        function renderChips() {
            const names = opts.filter(o => M._entitySelected!.has(o.id)).map(o => o.name);
            selectedChips.textContent = names.length ? 'Linked: ' + names.join(', ') : 'None linked yet';
        }
        function ops(): MemoryViewEntityOption[] { return opts.filter(o => !input.value || o.name.toLowerCase().includes(input.value.toLowerCase())); }
        function render() {
            list.replaceChildren();
            const matches = ops();
            if (matches.length === 0) { list.textContent = 'No matches.'; return; }
            matches.forEach(o => {
                const row = document.createElement('label');
                row.className = 'memedit-entityrow';
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.checked = M._entitySelected!.has(o.id);
                cb.addEventListener('change', () => {
                    if (cb.checked) M._entitySelected!.add(o.id); else M._entitySelected!.delete(o.id);
                    renderChips();
                });
                const txt = document.createElement('span');
                txt.textContent = typeIcon(o.type) + o.name + ' (' + o.type + ')';
                row.append(cb, txt);
                list.appendChild(row);
            });
        }
        input.addEventListener('input', render);
        container.append(selectedChips, input, list);
        renderChips();
        render();
    };

    M._closeMemoryEditor = function (): void {
        if (M._previewTimer) {
            clearTimeout(M._previewTimer);
            M._previewTimer = undefined;
        }
        const modal = document.getElementById('mem-editor-modal');
        if (modal) modal.remove();
    };

    /**
     * Embed the given text and upsert the vector for <char>::<id>. Returns a
     * promise resolving true on success / false on failure or disabled.
     */
    M._embedForEntry = function (charName: string, entryId: string, text: string): Promise<boolean> {
        if (!entryId || !window.EmbeddingClient?.configured()) return Promise.resolve(false);
        return EmbeddingClient.embed(text).then((vector: any) => {
            if (!vector) return false;
            return ApiClient.getMemoryEmbeddings({
                items: [{ key: `${charName}::${entryId}`, vector }],
                model: config.embedModel,
                dims: vector.length
            }).then(r => !r.error).catch(() => false);
        }).catch(() => false);
    };

    /**
     * Save a memory from the unified editor / weaver modal.
     */
    M.saveMemory = function (charName: string, entryId: string): void {
        const contentEl = document.getElementById('mem-editor-content') as HTMLTextAreaElement | null;
        const genResEl = document.getElementById('mem-gen-result') as HTMLTextAreaElement | null;
        const rawContent = (contentEl?.value || genResEl?.value || '').trim();
        const content = M.stripEditorialLeakage(rawContent);
        if (!content) return;

        const type = (document.getElementById('mem-editor-type') as HTMLSelectElement | null)?.value
            || (document.getElementById('mem-gen-type') as HTMLSelectElement | null)?.value
            || 'observation';
        const importance = parseInt(
            (document.getElementById('mem-editor-importance') as HTMLInputElement | null)?.value
            || (document.getElementById('mem-gen-importance') as HTMLInputElement | null)?.value
            || '5', 10
        ) || 5;
        const prestart = parseInt((document.getElementById('mem-editor-prestart') as HTMLInputElement | null)?.value as string, 10) || 0;
        const tickInput = parseInt((document.getElementById('mem-editor-tick') as HTMLInputElement | null)?.value as string, 10);
        const tick = prestart > 0 ? -prestart : (!isNaN(tickInput) ? tickInput : (VW?.state?.tick ?? 0));

        const bBundle = M._gen?.contextBundle;
        const birthTickRaw = bBundle?.birth_tick !== undefined ? bBundle.birth_tick : (worldState.players?.[charName] as any)?.birth_tick;
        const birthTick = (birthTickRaw !== null && birthTickRaw !== undefined && Number.isFinite(Number(birthTickRaw)))
            ? Math.round(Number(birthTickRaw))
            : null;
        if (birthTick !== null && tick < birthTick) {
            const bdayStr = bBundle?.birthday ? `, birthday ${bBundle.birthday}` : '';
            const msg = `Cannot save memory at tick ${tick}: ${charName} was not born until tick ${birthTick}${bdayStr}.`;
            const statusEl = document.getElementById('mem-gen-status');
            if (statusEl) {
                statusEl.textContent = `⛔ ${msg}`;
                statusEl.style.color = '#e05555';
            }
            const birthGateEl = document.getElementById('mem-editor-birth-gate');
            if (birthGateEl) {
                birthGateEl.style.cssText = 'display:block;margin-bottom:8px;padding:5px 8px;border-radius:5px;font-size:10px;font-family:monospace;background:#3d1a1a;border:1px solid #e05555;color:#ff9b9b;';
                birthGateEl.textContent = `⛔ ${msg}`;
            }
            return;
        }

        const location = (document.getElementById('mem-editor-location') as HTMLInputElement | null)?.value || '';
        const source = (document.getElementById('mem-editor-source') as HTMLInputElement | null)?.value || 'manual';
        const salience = parseInt((document.getElementById('mem-editor-salience') as HTMLInputElement | null)?.value as string, 10) || 0;
        const tags = M._tagSelect ? M._tagSelect.getValue() : (M._tagSelectTags || M._genTagSelectTags || []);
        const entity_ids = M._entitySelected ? Array.from(M._entitySelected) : [];
        const categorySel = (document.getElementById('mem-editor-category') as HTMLSelectElement | null)?.value || '';
        const confidenceInput = parseInt((document.getElementById('mem-editor-confidence') as HTMLInputElement | null)?.value as string, 10);
        const hasConfidence = !isNaN(confidenceInput);
        const simulateAgeDecay = !!(document.getElementById('mem-editor-age-decay') as HTMLInputElement | null)?.checked;
        const derivedExpectation = ((document.getElementById('mem-editor-expectation') as HTMLInputElement | null)?.value || '').trim();

        const emotions = Array.isArray(M._emoSelected)
            ? M._emoSelected.filter(e => e && e.label && e.label !== 'neutral')
            : [];
        const relationship_deltas = Array.isArray(M._relDeltas)
            ? M._relDeltas.filter(d => d && d.who && Object.keys(d.data || {}).length > 0)
            : [];

        const existingContra = entryId
            ? ((worldState.players?.[charName]?.memories || []).find((m: any) => m.id === entryId)?.contradicts || [])
            : [];
        const removedSet = M._contraRemoved || new Set<string>();
        const addedList = M._contraAdded || [];
        const contradicts = existingContra
            .filter((id: string) => !removedSet.has(id))
            .concat(addedList);
        const contraAddSel = document.getElementById('mem-editor-contra-add') as HTMLSelectElement | null;
        if (contraAddSel?.value && !contradicts.includes(contraAddSel.value)) {
            contradicts.push(contraAddSel.value);
        }

        const payload: MemoryViewMemoryPayload = {
            text: content,
            type,
            importance,
            tick,
            location,
            source,
            tags,
            salience_override: salience,
            force: true
        };
        if (categorySel) payload.category = categorySel;
        if (hasConfidence) payload.confidence = Math.max(0, Math.min(1, confidenceInput / 100));
        if (contradicts.length || entryId) payload.contradicts = contradicts;
        if (entity_ids.length) payload.entity_ids = entity_ids;
        if (emotions.length) {
            payload.memory_emotions = emotions;
            payload.emotion = emotions[0];
        }
        if (relationship_deltas.length) {
            payload.relationship_deltas = relationship_deltas;
            payload.emotions = relationship_deltas[0];
        }
        if (!entryId && simulateAgeDecay) {
            payload.simulate_age_decay = true;
        }
        if (!entryId && derivedExpectation) {
            payload.derived_expectation = derivedExpectation;
        }

        const cpEnabled = !!(document.getElementById('mem-editor-counterpart-enable') as HTMLInputElement | null)?.checked;
        const cpText = ((document.getElementById('mem-editor-counterpart-text') as HTMLTextAreaElement | null)?.value || '').trim();
        const cpDraft = M._gen?.counterpartDraft;

        const done = async (data: any) => {
            if (data && data.error) {
                const statusEl = document.getElementById('mem-gen-status');
                if (statusEl) {
                    statusEl.textContent = `⛔ ${data.error}`;
                    statusEl.style.color = '#e05555';
                }
                const birthGateEl = document.getElementById('mem-editor-birth-gate');
                if (birthGateEl) {
                    birthGateEl.style.cssText = 'display:block;margin-bottom:8px;padding:5px 8px;border-radius:5px;font-size:10px;font-family:monospace;background:#3d1a1a;border:1px solid #e05555;color:#ff9b9b;';
                    birthGateEl.textContent = `⛔ ${data.error}`;
                }
                return;
            }
            const id = (data && data.entry && data.entry.id) || (data && data.id) || entryId;
            if (id) M._embedForEntry(charName, id, content);

            if (!entryId && cpEnabled && cpDraft?.who && cpText) {
                const cpPayload: MemoryViewMemoryPayload = {
                    text: M.stripEditorialLeakage(cpText),
                    type: 'event',
                    category: 'social',
                    importance: cpDraft.importance || importance,
                    tick,
                    location,
                    source: 'manual',
                    tags: [`rel:${charName}`],
                    force: true,
                    simulate_age_decay: simulateAgeDecay,
                    memory_emotions: cpDraft.memory_emotions || [],
                    relationship_deltas: cpDraft.relationship_deltas?.length
                        ? cpDraft.relationship_deltas
                        : [{ who: charName, why: 'Shared event', data: { familiarity: 2 } }]
                };
                try {
                    await (ApiClient as unknown as MemoryViewApiClient).addPlayerMemory(cpDraft.who, cpPayload);
                } catch (_e) {
                    // Best-effort counterpart write
                }
            }

            M._closeMemoryEditor();
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        };

        if (entryId) {
            (ApiClient as unknown as MemoryViewApiClient).updatePlayerMemory(charName, entryId, payload).then(done);
        } else {
            (ApiClient as unknown as MemoryViewApiClient).addPlayerMemory(charName, payload).then(done);
        }
    };

    M.deleteMemory = function (charName: string, entryId: string): void {
        if (!entryId) {
            console.warn('[InspectorMemory] deleteMemory called without entryId for', charName);
            return;
        }
        (ApiClient as unknown as MemoryViewApiClient).deletePlayerMemory(charName, entryId).then(() => {
            worldState.fetch().then(() => { if (window.VW?.inspector) window.VW.inspector._reRender(); });
        });
    };

    // --- Memory Weaver & Generator (grounded first-person memories) ---

    /**
     * Open the unified Memory Weaver & Editor modal in natural-language weave mode.
     */
    M.generateMemory = function (charName: string, opts?: MemoryViewEditorOptions): void {
        M.showMemoryEditor(charName, null, { ...(opts || {}), openWeaver: true });
    };

    /**
     * Build the grounded identity block (persona record + appearance + mood +
     * recalled memories + relationship profiles) used to frame the character's voice.
     */
    M._identityBlock = function (charName: string, contextBundle?: any): string {
        const player = worldState.players?.[charName] || {};
        const bundle = contextBundle || M._gen?.contextBundle || null;
        const ps = bundle?.persona_summary || {};
        const lines: string[] = [`You are ${charName}.`];

        const pers = ps.personality || player.personality;
        if (pers) lines.push(`Personality: ${String(pers).trim()}`);
        const desc = ps.base_description || player.base_description || player.description;
        if (desc) lines.push(`Appearance & background: ${String(desc).trim()}`);
        if (Array.isArray(ps.values) && ps.values.length) lines.push(`Core values: ${ps.values.join(', ')}`);
        if (Array.isArray(ps.likes) && ps.likes.length) lines.push(`Likes / interests: ${ps.likes.join(', ')}`);
        if (Array.isArray(ps.dislikes) && ps.dislikes.length) lines.push(`Dislikes: ${ps.dislikes.join(', ')}`);
        if (Array.isArray(ps.fears) && ps.fears.length) lines.push(`Fears: ${ps.fears.join(', ')}`);
        if (ps.biography) lines.push(`Biography: ${String(ps.biography).trim()}`);
        const bday = ps.birthday || bundle?.birthday;
        const ageVal = ps.age ?? bundle?.age;
        const bTick = ps.birth_tick ?? bundle?.birth_tick;
        if (bday || ageVal != null || bTick != null) {
            const birthBits = [
                bday ? `birthday ${bday}` : '',
                ageVal != null ? `age ${ageVal}` : '',
                bTick != null ? `born at tick ${bTick}` : '',
            ].filter(Boolean).join(', ');
            lines.push(`Birth & age: ${birthBits} (never invent memories from before you were born).`);
        }

        const emo = bundle?.current_emotion || player.emotion;
        if (emo && emo.current && emo.current !== 'neutral') {
            lines.push(`Current mood: ${emo.current} (intensity ${emo.intensity ?? 0.5})`);
        }

        const recalled = Array.isArray(bundle?.recalled_memories) ? bundle.recalled_memories : [];
        if (recalled.length) {
            lines.push('Existing memories you already hold (stay consistent with these unless told otherwise):');
            recalled.slice(0, 6).forEach((m: any) => {
                lines.push(`- [tick ${m.tick ?? 0}] ${String(m.text || '').trim()}`);
            });
        }

        const people = Array.isArray(bundle?.people_profiles) ? bundle.people_profiles : [];
        if (people.length) {
            lines.push('People you know and how you currently feel about them:');
            people.slice(0, 8).forEach((p: any) => {
                const prof = p.profile || {};
                lines.push(`- ${p.name} (${prof.role || 'stranger'}): trust ${prof.trust ?? 0}, fear ${prof.fear ?? 0}, attraction ${prof.attraction ?? 0}, respect ${prof.respect ?? 0}`);
            });
        }

        lines.push('You are speaking in your own authentic voice and authoring your own first-person memory record.');
        return lines.join('\n');
    };

    M._buildSeedPrompt = function (
        charName: string,
        theme: string,
        mode: 'opinion' | 'event' | 'social' = 'event',
        contextBundle?: any
    ): string {
        const vocab = [...new Set(EMOTION_GROUPS.flatMap(g => g.items).filter(l => l !== 'neutral'))];
        const vocabStr = vocab.join(', ');
        const bundle = contextBundle || M._gen?.contextBundle || null;
        const knownChars = bundle?.world_entities?.characters?.length
            ? bundle.world_entities.characters.join(', ')
            : Object.keys(worldState.players || {}).filter(p => p !== charName).join(', ');
        const knownAreas = bundle?.world_entities?.areas?.length
            ? bundle.world_entities.areas.slice(0, 25).join(', ')
            : Object.keys(worldState.areas || {}).slice(0, 25).join(', ');

        const modeGuidance = mode === 'opinion'
            ? `Mode: OPINION / REACTION. The user is asking what ${charName} thought or felt about a movie, book, topic, place, or experience. React conversationally in "character_reply", and record the lasting first-person opinion or memory in "memory.text" (category "belief" or "episodic").`
            : mode === 'social'
            ? `Mode: ABOUT A PERSON. The user is describing or asking about an interpersonal moment involving another character (known characters: ${knownChars || 'none'}). React in "character_reply", write ${charName}'s first-person memory in "memory.text" (category "social"), populate "relationship_deltas" for each person involved, and if the other character was present, include "counterpart_memory" from their first-person perspective.`
            : `Mode: BACKDATED EVENT. The user is authoring or refining a past experience for ${charName} (known areas: ${knownAreas || 'any'}). React in "character_reply", write ${charName}'s vivid first-person memory in "memory.text" (category "episodic"), estimate "tick_offset_minutes" (negative for the past, e.g. -1440 for 1 day ago) if a relative time is implied, and include "derived_expectation" if this event taught ${charName} a lasting habit or caution.`;

        return `${modeGuidance}\n`
            + `Prompt / direction: ${theme}\n`
            + `Rules:\n`
            + `1) "character_reply": ${charName}'s conversational reaction to the user (1-2 sentences). NEVER put meta-commentary or conversational framing inside "memory.text".\n`
            + `2) "memory.text": ONLY the memory itself, in ${charName}'s first-person voice (1-3 vivid sentences, under ~55 words). No second editorial paragraph.\n`
            + `3) Return ONLY a single JSON object (no code fences, no preamble) shaped as:\n`
            + `{\n`
            + `  "character_reply": "<conversational reaction in voice>",\n`
            + `  "memory": {\n`
            + `    "text": "<first-person memory text ONLY>",\n`
            + `    "type": "<memory|reflection|event|conversation|observation|thought|dream>",\n`
            + `    "category": "<episodic|belief|social|procedural|semantic>",\n`
            + `    "importance": <1-10>,\n`
            + `    "confidence": <0.1-1.0>,\n`
            + `    "tick_offset_minutes": <negative minutes if in the past, or null>,\n`
            + `    "location": "<area name or empty string>",\n`
            + `    "entities": ["<character, area, or item name>", ...],\n`
            + `    "tags": ["<single-word tag>", ...],\n`
            + `    "memory_emotions": [{"label": "<emotion>", "intensity": <1-10>}],\n`
            + `    "relationship_deltas": [{"who": "<CharacterName>", "why": "<brief reason>", "data": {"trust": <-5..5>, "fear": <-5..5>, "attraction": <-5..5>, "respect": <-5..5>, "disgust": <-5..5>, "familiarity": <-5..5>}}],\n`
            + `    "derived_expectation": "<optional first-person procedural habit/rule learned, or empty string>"\n`
            + `  },\n`
            + `  "counterpart_memory": null\n`
            + `}\n`
            + `Use emotion labels from this vocabulary when one fits: ${vocabStr}.`;
    };

    M.buildWeaverMessages = function (
        charName: string,
        mode: 'opinion' | 'event' | 'social',
        history: Array<{ role: string; content: string }>,
        draftState?: any,
        contextBundle?: any
    ): Array<{ role: string; content: string }> {
        const messages: Array<{ role: string; content: string }> = [
            { role: 'system', content: M._identityBlock(charName, contextBundle) }
        ];
        const prior = Array.isArray(history) ? history.slice(-6) : [];
        for (let i = 0; i < prior.length - 1; i++) {
            messages.push(prior[i]);
        }
        const latestUser = prior.length ? prior[prior.length - 1].content : '';
        let promptBody = latestUser;
        if (draftState && draftState.text) {
            promptBody = `Current memory draft: "${draftState.text}" (tick ${draftState.tick ?? 0}, importance ${draftState.importance ?? 5}).\nRefinement / follow-up request: ${latestUser}`;
        }
        messages.push({
            role: 'user',
            content: M._buildSeedPrompt(charName, promptBody, mode, contextBundle)
        });
        return messages;
    };

    M._runMemoryGeneration = async function (): Promise<void> {
        const charName = M._gen && M._gen.charName;
        const container = document.getElementById('mem-editor-modal');
        if (!charName || !container) return;
        const status = container.querySelector('#mem-gen-status') as HTMLElement;
        const contentArea = (container.querySelector('#mem-editor-content') || container.querySelector('#mem-gen-result')) as HTMLTextAreaElement | null;
        const hiddenResult = container.querySelector('#mem-gen-result') as HTMLTextAreaElement | null;
        const impInput = (container.querySelector('#mem-editor-importance') || container.querySelector('#mem-gen-importance')) as HTMLInputElement | null;
        const promptInput = container.querySelector('#mem-gen-prompt') as HTMLTextAreaElement | null;
        const theme = promptInput?.value?.trim() || '';
        if (!theme) {
            status.textContent = 'Enter a question or memory idea first.'; status.style.color = '#e0a33c'; return;
        }
        if (!window.VW?.llm) {
            status.textContent = 'LLM client unavailable.'; status.style.color = '#e05555'; return;
        }
        const mode = M._gen?.mode || 'event';
        status.textContent = 'weaving with character…'; status.style.color = '#9aa4b2';
        try {
            const bundle = await M.fetchMemoryContext(charName, theme);
            if (bundle && M._gen) M._gen.contextBundle = bundle;

            const currentDraft = contentArea?.value?.trim()
                ? {
                    text: contentArea.value.trim(),
                    tick: parseInt((container.querySelector('#mem-editor-tick') as HTMLInputElement | null)?.value || '0', 10) || 0,
                    importance: parseInt(impInput?.value || '5', 10) || 5
                }
                : null;

            M._gen!.history = M._gen!.history || [];
            M._gen!.history.push({ role: 'user', content: theme });

            const messages = M.buildWeaverMessages(charName, mode, M._gen!.history, currentDraft, bundle);
            const text = await VW.llm.chat(messages, { streaming: false, max_tokens: Math.max(450, config.maxTokens || 450) });
            const raw = String(text || '').trim();
            const parsed = M.parseWeaverResponse(raw);
            const memText = (parsed && parsed.text)
                ? String(parsed.text).trim()
                : M.stripEditorialLeakage(raw.replace(/^["'`]+|["'`]+$/g, '').trim());
            if (!memText) {
                status.textContent = 'No memory returned.'; status.style.color = '#e05555'; return;
            }
            if (contentArea) contentArea.value = memText;
            if (hiddenResult) hiddenResult.value = memText;

            if (parsed) {
                M._gen!.history.push({ role: 'assistant', content: parsed.character_reply || memText });
                const replyBox = container.querySelector('#mem-weaver-reply-box') as HTMLElement | null;
                const replyEl = container.querySelector('#mem-weaver-reply') as HTMLElement | null;
                if (replyBox && replyEl) {
                    if (parsed.character_reply) {
                        replyBox.style.display = 'block';
                        replyEl.textContent = `"${parsed.character_reply}"`;
                    } else {
                        replyBox.style.display = 'none';
                    }
                }
                if (impInput && parsed.importance) {
                    impInput.value = String(Math.max(1, Math.min(10, parsed.importance)));
                }
                const confInput = container.querySelector('#mem-editor-confidence') as HTMLInputElement | null;
                if (confInput && parsed.confidence) {
                    confInput.value = String(Math.round(parsed.confidence * 100));
                }
                const typeSel = (container.querySelector('#mem-editor-type') || container.querySelector('#mem-gen-type')) as HTMLSelectElement | null;
                if (typeSel && parsed.type) {
                    typeSel.value = parsed.type;
                }
                const catSel = container.querySelector('#mem-editor-category') as HTMLSelectElement | null;
                if (catSel && parsed.category) {
                    catSel.value = parsed.category;
                }
                const locInput = container.querySelector('#mem-editor-location') as HTMLInputElement | null;
                if (locInput && parsed.location) {
                    locInput.value = parsed.location;
                }
                const expInput = container.querySelector('#mem-editor-expectation') as HTMLInputElement | null;
                if (expInput && parsed.derived_expectation) {
                    expInput.value = parsed.derived_expectation;
                }

                // Backdate tick if user hasn't typed a manual relative time and the LLM inferred tick_offset_minutes
                const relInput = container.querySelector('#mem-editor-reltime') as HTMLInputElement | null;
                const tickInputEl = container.querySelector('#mem-editor-tick') as HTMLInputElement | null;
                const preInputEl = container.querySelector('#mem-editor-prestart') as HTMLInputElement | null;
                const relPreview = container.querySelector('#mem-editor-reltime-preview') as HTMLElement | null;
                if (parsed.tick_offset_minutes !== null && (!relInput || !relInput.value.trim())) {
                    const curTick = bundle?.current_tick ?? (VW?.state?.tick ?? 0);
                    const mpt = Math.max(0.1, Number(bundle?.time_per_tick_minutes || 1));
                    const deltaTicks = Math.round(parsed.tick_offset_minutes / mpt);
                    let newTick = curTick + deltaTicks;
                    const minBirth = bundle?.birth_tick !== undefined && bundle?.birth_tick !== null
                        ? Math.round(Number(bundle.birth_tick))
                        : null;
                    if (minBirth !== null && Number.isFinite(minBirth) && newTick < minBirth) {
                        newTick = minBirth;
                    }
                    if (tickInputEl) tickInputEl.value = String(newTick);
                    if (preInputEl) preInputEl.value = newTick < 0 ? String(-newTick) : '0';
                    if (relPreview) relPreview.textContent = `tick ${newTick}`;
                }

                if (M._tagSelect && parsed.tags?.length) {
                    M._tagSelect.setValue(parsed.tags);
                } else if (M._genTagSelect && parsed.tags?.length) {
                    M._genTagSelect.setValue(parsed.tags);
                }

                // Link resolved entities in M._entitySelected
                if (Array.isArray(parsed.entities) && parsed.entities.length && M._entitySelected) {
                    const nodes = worldState.graph?.nodes || {};
                    for (const entName of parsed.entities) {
                        const lower = entName.toLowerCase();
                        for (const id in nodes) {
                            if (String(nodes[id]?.name || '').toLowerCase() === lower) {
                                M._entitySelected.add(id);
                            }
                        }
                        for (const cname in (worldState.players || {})) {
                            if (cname.toLowerCase() === lower) {
                                M._entitySelected.add('player_' + cname.toLowerCase().replace(/\s+/g, '_'));
                            }
                        }
                    }
                    const entEl = container.querySelector('#mem-editor-entities') as HTMLElement | null;
                    if (entEl) M._attachEntitySelector(entEl);
                }

                const genEmoEl = container.querySelector('#mem-gen-emotions') as HTMLElement | null;
                if (genEmoEl) M._attachEmotionSelector(genEmoEl, parsed.memory_emotions || []);

                const relDeltasEl = container.querySelector('#mem-editor-rel-deltas') as HTMLElement | null;
                if (relDeltasEl && parsed.relationship_deltas?.length) {
                    M._attachRelationshipDeltaEditor(charName, relDeltasEl, parsed.relationship_deltas);
                }

                // Optional counterpart memory for shared social events
                const cpBox = container.querySelector('#mem-editor-counterpart-box') as HTMLElement | null;
                const cpCheck = container.querySelector('#mem-editor-counterpart-enable') as HTMLInputElement | null;
                const cpLabel = container.querySelector('#mem-editor-counterpart-label') as HTMLElement | null;
                const cpText = container.querySelector('#mem-editor-counterpart-text') as HTMLTextAreaElement | null;
                if (cpBox && cpCheck && cpLabel && cpText) {
                    if (parsed.counterpart_memory && parsed.counterpart_memory.who && parsed.counterpart_memory.text) {
                        M._gen!.counterpartDraft = parsed.counterpart_memory;
                        cpBox.style.display = 'block';
                        cpCheck.checked = true;
                        cpLabel.textContent = `Also record counterpart memory on ${parsed.counterpart_memory.who}`;
                        cpText.value = parsed.counterpart_memory.text;
                    } else {
                        M._gen!.counterpartDraft = null;
                        cpBox.style.display = 'none';
                        cpCheck.checked = false;
                    }
                }

                status.textContent = '✓ woven in character voice (you can refine further or save)';
                status.style.color = '#4caf50';
                M._refreshLivePreview(charName);
            } else {
                status.textContent = '✓ drafted (text only - LLM did not return JSON)';
                status.style.color = '#e0a33c';
            }
        } catch (e) {
            const detail = (e as { message?: string } | null)?.message;
            status.textContent = '✗ ' + (detail || String(e));
            status.style.color = '#e05555';
        }
    };

    M._saveGeneratedMemory = function (): void {
        const charName = M._gen && M._gen.charName;
        if (!charName) return;
        M.saveMemory(charName, '');
    };

    /**
     * Build a multi-emotion picker bound to M._emoSelected (array of
     * {label,intensity}). Supports many emotions per memory.
     */
    M._attachEmotionSelector = function (container: HTMLElement, initial: MemoryViewEmotion[]): void {
        M._emoSelected = (Array.isArray(initial) ? initial : []).filter(e => e && e.label);
        container.replaceChildren();
        container.classList.add('memedit-entitybox');

        const bar = document.createElement('div');
        bar.style.cssText = 'display:flex;gap:6px;align-items:center;padding:6px;border-bottom:1px solid var(--border);flex-wrap:wrap;';
        const sel = document.createElement('select');
        sel.style.cssText = 'flex:1;min-width:140px;font-size:11px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
        EMOTION_GROUPS.forEach(g => {
            const og = document.createElement('optgroup');
            og.label = g.label;
            g.items.forEach(name => {
                const o = document.createElement('option');
                o.value = name; o.textContent = name;
                if (M._emoSelected!.some(e => e.label === name)) o.selected = true;
                og.appendChild(o);
            });
            sel.appendChild(og);
        });
        const int = document.createElement('input');
        int.type = 'number'; int.min = '1'; int.max = '10'; int.value = '5';
        int.style.cssText = 'width:56px;font-size:11px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
        int.title = 'Intensity (1-10)';
        const cust = document.createElement('input');
        cust.type = 'text';
        cust.placeholder = 'or type a custom label…';
        cust.style.cssText = 'flex:1;min-width:110px;font-size:11px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;';
        cust.title = 'Add an emotion label not in the list (e.g. an agent-invented one)';
        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn btn-sm btn-blue';
        addBtn.style.fontSize = '10px';
        addBtn.textContent = '➕ Add';
        addBtn.addEventListener('click', () => {
            const label = (cust.value || '').trim() || sel.value;
            if (!label) return;
            const intensity = Math.max(1, Math.min(10, parseInt(int.value, 10) || 5));
            const found = M._emoSelected!.find(e => e.label === label);
            if (found) found.intensity = intensity; else M._emoSelected!.push({ label, intensity });
            cust.value = '';
            render();
        });
        cust.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); addBtn.click(); } });
        bar.append(sel, cust, int, addBtn);

        const chips = document.createElement('div');
        chips.style.cssText = 'padding:6px;display:flex;flex-wrap:wrap;gap:6px;max-height:120px;overflow-y:auto;';

        function render(): void {
            chips.replaceChildren();
            if (M._emoSelected!.length === 0) {
                const none = document.createElement('div');
                none.textContent = 'No emotions selected. Pick and add.';
                none.style.cssText = 'font-size:10px;color:var(--text-muted);';
                chips.appendChild(none);
                return;
            }
            M._emoSelected!.forEach((e, idx) => {
                const chip = document.createElement('div');
                chip.style.cssText = 'display:flex;gap:4px;align-items:center;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:16px;padding:2px 8px;';
                const lbl = document.createElement('span');
                lbl.textContent = e.label;
                const iv = document.createElement('input');
                iv.type = 'number'; iv.min = '1'; iv.max = '10'; iv.value = String(e.intensity || 5);
                iv.style.cssText = 'width:40px;font-size:10px;padding:1px 3px;background:var(--bg-inset);color:var(--text);border:1px solid var(--border);border-radius:4px;';
                iv.addEventListener('change', () => {
                    M._emoSelected![idx].intensity = Math.max(1, Math.min(10, parseInt(iv.value, 10) || 5));
                });
                const rm = document.createElement('button');
                rm.type = 'button';
                rm.textContent = '×';
                rm.style.cssText = 'border:none;background:none;color:var(--text-muted);cursor:pointer;font-size:12px;line-height:1;';
                rm.addEventListener('click', () => { M._emoSelected!.splice(idx, 1); render(); });
                chip.append(lbl, iv, rm);
                chips.appendChild(chip);
            });
        }
        render();
        container.append(bar, chips);
    };

    return M;
})();

// ── Types ────────────────────────────────────────────────────────────────────
// A top-level `interface` in a classic script is a global binding, so every name
// below is prefixed with the file stem to stay unique across modules.

/** One emotion attached to a memory (`memory_emotions: [{label,intensity}]`). */
interface MemoryViewEmotion {
    label: string;
    intensity?: number;
}

/** One row of the emotion picker's grouped vocabulary. */
interface MemoryViewEmotionGroup {
    label: string;
    items: string[];
}

/** One searchable world entity offered by the entity-reference multiselect. */
interface MemoryViewEntityOption {
    id: string;
    name: string;
    type: string;
}

/** Parsed relative time result. */
interface MemoryViewRelativeTime {
    tick: number;
    label: string;
    unclampedTick?: number;
    beforeBirth?: boolean;
}

/** One interpersonal feeling delta toward another character. */
interface MemoryViewRelationshipDelta {
    who: string;
    why: string;
    data: Record<string, number>;
}

/** Optional counterpart memory drafted for the other character in a shared event. */
interface MemoryViewCounterpartDraft {
    who: string;
    text: string;
    importance: number;
    memory_emotions: MemoryViewEmotion[];
    relationship_deltas: MemoryViewRelationshipDelta[];
}

/** Normalized draft returned by `M.parseWeaverResponse`. */
interface MemoryViewWeaverDraft {
    character_reply: string;
    text: string;
    type: string;
    category: string;
    importance: number;
    confidence: number;
    tick_offset_minutes: number | null;
    location: string;
    entities: string[];
    tags: string[];
    emotions: MemoryViewEmotion[];
    memory_emotions: MemoryViewEmotion[];
    relationship_deltas: MemoryViewRelationshipDelta[];
    derived_expectation: string;
    counterpart_memory: MemoryViewCounterpartDraft | null;
}

/** Options when opening the unified Memory Weaver & Editor modal. */
interface MemoryViewEditorOptions {
    mode?: 'opinion' | 'event' | 'social';
    tick?: number;
    targetPerson?: string;
    prompt?: string;
    openWeaver?: boolean;
}

/** The body posted to `POST /api/players/<name>/memories/entry` for add/update. */
interface MemoryViewMemoryPayload {
    text: string;
    type: string;
    importance: number;
    tick: number;
    location: string;
    source: string;
    tags: string[];
    salience_override?: number;
    force: boolean;
    entity_ids?: string[];
    memory_emotions?: MemoryViewEmotion[];
    emotion?: MemoryViewEmotion;
    emotions?: MemoryViewRelationshipDelta;
    relationship_deltas?: MemoryViewRelationshipDelta[];
    category?: string;
    confidence?: number;
    contradicts?: string[];
    simulate_age_decay?: boolean;
    derived_expectation?: string;
}

/** The `TagMultiselect` surface this module calls back into. */
interface MemoryViewTagSelect {
    getValue(): string[];
    setValue(tags: string[]): void;
}

/**
 * The memory endpoints of `ApiClient` (routes/memories.py). globals.d.ts
 * declares only the graph/character calls, so the rest are narrowed here.
 */
interface MemoryViewApiClient {
    clearPlayerMemories(charName: string): Promise<unknown>;
    suppressPlayerMemory(charName: string, payload: unknown): Promise<unknown>;
    unblockPlayerMemory(charName: string, payload: unknown): Promise<unknown>;
    clearExpiredSuppressions(charName: string, tick: number): Promise<unknown>;
    updatePlayerMemory(charName: string, entryId: string, payload: unknown): Promise<unknown>;
    addPlayerMemory(charName: string, payload: unknown): Promise<unknown>;
    deletePlayerMemory(charName: string, entryId: string): Promise<unknown>;
}

/** `window.InspectorMemory` - the module's public surface. */
interface MemoryViewApi {
    addMemory(charName: string): void;
    editMemory(charName: string, entryId: string): void;
    openWeaver(charName: string, opts?: MemoryViewEditorOptions): void;
    openWeaverAtTick(charName: string, tick: number, mode?: 'opinion' | 'event' | 'social'): void;
    suppressMemory(charName: string, entryId: string): void;
    unblockMemory(charName: string, entryId: string): void;
    clearExpired(charName: string): void;
    showMemoryEditor(charName: string, entryId: string | null, opts?: MemoryViewEditorOptions): void;
    saveMemory(charName: string, entryId: string): void;
    deleteMemory(charName: string, entryId: string): void;
    generateMemory(charName: string, opts?: MemoryViewEditorOptions): void;
    parseRelativeTime(input: string, currentTick?: number, minutesPerTick?: number, birthTick?: number | null): MemoryViewRelativeTime | null;
    stripEditorialLeakage(memText: string, characterReply?: string): string;
    parseWeaverResponse(raw: string): MemoryViewWeaverDraft | null;
    fetchMemoryContext(charName: string, query?: string, candidate?: any): Promise<any>;
    buildWeaverMessages(
        charName: string,
        mode: 'opinion' | 'event' | 'social',
        history: Array<{ role: string; content: string }>,
        draftState?: any,
        contextBundle?: any
    ): Array<{ role: string; content: string }>;
    // internal
    _attachEntitySelector(container: HTMLElement): void;
    _attachRelationshipDeltaEditor(charName: string, container: HTMLElement, initial: MemoryViewRelationshipDelta[]): void;
    _refreshLivePreview(charName: string): void;
    _closeMemoryEditor(): void;
    _embedForEntry(charName: string, entryId: string, text: string): Promise<boolean>;
    _identityBlock(charName: string, contextBundle?: any): string;
    _buildSeedPrompt(charName: string, theme: string, mode?: 'opinion' | 'event' | 'social', contextBundle?: any): string;
    _parseSeedJson(raw: string): any;
    _runMemoryGeneration(): Promise<void>;
    _saveGeneratedMemory(): void;
    _attachEmotionSelector(container: HTMLElement, initial: MemoryViewEmotion[]): void;
    // live editor state, set by the attach helpers
    _tagSelect?: MemoryViewTagSelect;
    _tagSelectTags?: string[];
    _genTagSelect?: MemoryViewTagSelect;
    _genTagSelectTags?: string[];
    _entitySelected?: Set<string>;
    _emoSelected?: MemoryViewEmotion[];
    _relDeltas?: MemoryViewRelationshipDelta[];
    _contraRemoved?: Set<string>;
    _contraAdded?: string[];
    _previewTimer?: ReturnType<typeof setTimeout>;
    _gen?: {
        charName: string;
        mode?: 'opinion' | 'event' | 'social';
        history?: Array<{ role: string; content: string }>;
        contextBundle?: any;
        counterpartDraft?: MemoryViewCounterpartDraft | null;
    };
}
