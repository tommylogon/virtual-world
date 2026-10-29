import re
import sys

path = "static/js/inspector/mind-view.ts"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

assert '\u2014' not in content and '—' not in content, "Em-dash in original file"

replacements = [
    (
"""    function _visible(memories: *FIX*[]): *FIX*[] {
        if (!_state) return [];
        const f = _state.filter;
        const q = _state.query.toLowerCase().trim();
        return memories.filter((m: *FIX*) => {""",
"""    function _visible(memories: Models.MemoryRecord[]): Models.MemoryRecord[] {
        if (!_state) return [];
        const f = _state.filter;
        const q = _state.query.toLowerCase().trim();
        return memories.filter((m: Models.MemoryRecord) => {"""
    ),
    (
"""    function _timelineHtml(memories: *FIX*[]): string {
        const ticks = memories.map((m: *FIX*) => Number(m.tick) || 0);
        const min = Math.min(0, ...ticks);
        const max = Math.max(1, ...ticks);
        const W = 760, H = 64, PAD = 18;
        const span = Math.max(1, max - min);
        const dots = memories.map((m: *FIX*) => {""",
"""    function _timelineHtml(memories: Models.MemoryRecord[]): string {
        const ticks = memories.map((m: Models.MemoryRecord) => Number(m.tick) || 0);
        const min = Math.min(0, ...ticks);
        const max = Math.max(1, ...ticks);
        const W = 760, H = 64, PAD = 18;
        const span = Math.max(1, max - min);
        const dots = memories.map((m: Models.MemoryRecord) => {"""
    ),
    (
"""    function _recordAndEvidenceHtml(m: *FIX*, charName?: string): string {
        if (!m) return '';
        const cname = charName || (_state ? _state.charName : '');
        const p: *FIX* = cname ? worldState.players?.[cname] : null;
        const livedLog: *FIX*[] = Array.isArray(p?.lived_log) ? p.lived_log : [];
        const mTick = Number(m.tick ?? 0);
        const mLoc = String(m.location || '').trim().toLowerCase();
        const mTags = (Array.isArray(m.tags) ? m.tags : []).map((t: *FIX*) => String(t).toLowerCase());
        const mRelTags = mTags.filter((t: string) => t.startsWith('rel:'));

        const matchedLog = livedLog.filter((entry: *FIX*) => {
            if (!entry || typeof entry !== 'object') return false;
            const eTick = Number(entry.tick ?? NaN);
            if (!isNaN(eTick) && eTick === mTick) return true;
            if (!isNaN(eTick) && Math.abs(eTick - mTick) <= 2) {
                const eArea = String(entry.area || '').trim().toLowerCase();
                if (mLoc && eArea && mLoc === eArea) return true;
                const eTags = (Array.isArray(entry.tags) ? entry.tags : []).map((t: *FIX*) => String(t).toLowerCase());""",
"""    function _recordAndEvidenceHtml(m: Models.MemoryRecord, charName?: string): string {
        if (!m) return '';
        const cname = charName || (_state ? _state.charName : '');
        const p: Models.PlayerRuntimeModel | null = cname ? (worldState.players?.[cname] || null) : null;
        const livedLog: Array<Record<string, unknown>> = Array.isArray(p?.lived_log) ? p.lived_log : [];
        const mTick = Number(m.tick ?? 0);
        const mLoc = String(m.location || '').trim().toLowerCase();
        const mTags = (Array.isArray(m.tags) ? m.tags : []).map((t: unknown) => String(t).toLowerCase());
        const mRelTags = mTags.filter((t: string) => t.startsWith('rel:'));

        const matchedLog = livedLog.filter((entry: Record<string, unknown>) => {
            if (!entry || typeof entry !== 'object') return false;
            const eTick = Number((entry as { tick?: number }).tick ?? NaN);
            if (!isNaN(eTick) && eTick === mTick) return true;
            if (!isNaN(eTick) && Math.abs(eTick - mTick) <= 2) {
                const eArea = String((entry as { area?: string }).area || '').trim().toLowerCase();
                if (mLoc && eArea && mLoc === eArea) return true;
                const eTags = (Array.isArray((entry as { tags?: unknown[] }).tags) ? (entry as { tags: unknown[] }).tags : []).map((t: unknown) => String(t).toLowerCase());"""
    ),
    (
"""    function _detailHtml(m: *FIX* | null, all: *FIX*[]): string {
        if (!m) return `<div style="font-size:11px;color:var(--text-muted);">Select a memory to see its dynamics and connections.</div>`;
        const cat = _catOf(m);
        const emoList = Array.isArray(m.memory_emotions) && m.memory_emotions.length
            ? m.memory_emotions
            : (m.emotion && m.emotion.label ? [m.emotion] : []);
        const byId = (id: string) => all.find((x: *FIX*) => x.id === id);""",
"""    function _detailHtml(m: Models.MemoryRecord | null, all: Models.MemoryRecord[]): string {
        if (!m) return `<div style="font-size:11px;color:var(--text-muted);">Select a memory to see its dynamics and connections.</div>`;
        const cat = _catOf(m);
        const emoList = Array.isArray(m.memory_emotions) && m.memory_emotions.length
            ? m.memory_emotions
            : (m.emotion && m.emotion.label ? [m.emotion] : []);
        const byId = (id: string) => all.find((x: Models.MemoryRecord) => x.id === id);"""
    ),
    (
"""    function _accessibilityHtml(all: *FIX*[]): string {
        if (!all.length) return '';
        const sorted = [...all].sort((a: *FIX*, b: *FIX*) => act(a) - act(b)).slice(0, 7);
        const faded = all.filter((m: *FIX*) => act(m) < 0.5).length;
        const row = (m: *FIX*): string => {""",
"""    function _accessibilityHtml(all: Models.MemoryRecord[]): string {
        if (!all.length) return '';
        const sorted = [...all].sort((a: Models.MemoryRecord, b: Models.MemoryRecord) => act(a) - act(b)).slice(0, 7);
        const faded = all.filter((m: Models.MemoryRecord) => act(m) < 0.5).length;
        const row = (m: Models.MemoryRecord): string => {"""
    ),
    (
"""    function _goals(): *FIX*[] {
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

    function _goalRowHtml(g: *FIX*): string {
        const inputStyle = 'font-size:10.5px;background:var(--bg-input);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:2px 6px;';
        const statuses = ['proposed', 'active', 'reached', 'blocked', 'dropped'];
        const color = _goalStatusColor(String(g.status || 'proposed'));
        const val = (s: *FIX*) => esc(String(s ?? ''));""",
"""    function _goals(): Models.GoalModel[] {
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

    function _goalRowHtml(g: Models.GoalModel): string {
        const inputStyle = 'font-size:10.5px;background:var(--bg-input);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:2px 6px;';
        const statuses = ['proposed', 'active', 'reached', 'blocked', 'dropped'];
        const color = _goalStatusColor(String(g.status || 'proposed'));
        const val = (s: unknown) => esc(String(s ?? ''));"""
    ),
    (
"""    function _collectGoals(): *FIX*[] {
        const box = _container?.querySelector('#mind-goals');
        if (!box) return [];
        return Array.from(box.querySelectorAll('.mind-goal')).map((row: *FIX*) => ({
            what: (row.querySelector('.mind-goal-what')?.value || '').trim(),
            status: row.querySelector('.mind-goal-status')?.value || 'proposed',
            motivation: (row.querySelector('.mind-goal-motivation')?.value || '').trim(),
            intention: (row.querySelector('.mind-goal-intention')?.value || '').trim(),
            blocks: (row.querySelector('.mind-goal-blocks')?.value || '').trim(),
        })).filter((g: *FIX*) => g.what);
    }""",
"""    function _collectGoals(): Models.GoalModel[] {
        const box = _container?.querySelector('#mind-goals');
        if (!box) return [];
        return Array.from(box.querySelectorAll('.mind-goal')).map((row: Element) => ({
            what: ((row.querySelector('.mind-goal-what') as HTMLInputElement)?.value || '').trim(),
            status: ((row.querySelector('.mind-goal-status') as HTMLSelectElement)?.value as Models.GoalStatus) || 'proposed',
            motivation: ((row.querySelector('.mind-goal-motivation') as HTMLInputElement)?.value || '').trim(),
            intention: ((row.querySelector('.mind-goal-intention') as HTMLInputElement)?.value || '').trim(),
            blocks: (((row.querySelector('.mind-goal-blocks') as HTMLInputElement)?.value || '').split(',').map(s => s.trim()).filter(Boolean)),
        })).filter((g: Models.GoalModel) => g.what);
    }"""
    ),
    (
"""        // A true triggering event needs a memory that records it - see task-725.
        const mems: *FIX*[] = Array.isArray(p.memories) ? p.memories : [];
        let lastFeeling: *FIX* = null;
        for (const mem of mems) {
            const labels = (Array.isArray(mem.memory_emotions) && mem.memory_emotions.length
                ? mem.memory_emotions
                : (mem.emotion && mem.emotion.label ? [mem.emotion] : []))
                .map((e: *FIX*) => String(e.label || '').toLowerCase());""",
"""        // A true triggering event needs a memory that records it - see task-725.
        const mems: Models.MemoryRecord[] = Array.isArray(p.memories) ? p.memories : [];
        let lastFeeling: Models.MemoryRecord | null = null;
        for (const mem of mems) {
            const labels = (Array.isArray(mem.memory_emotions) && mem.memory_emotions.length
                ? mem.memory_emotions
                : (mem.emotion && mem.emotion.label ? [mem.emotion] : []))
                .map((e: { label?: string }) => String(e.label || '').toLowerCase());"""
    ),
    (
"""    function _bodyHtml(): string {
        if (!_state) return '';
        const p: *FIX* = worldState.players?.[_state.charName];
        if (!p) return '';
        const state = String(p.state || 'awake');
        const instances: *FIX* = p.conditions || {};""",
"""    function _bodyHtml(): string {
        if (!_state) return '';
        const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;
        if (!p) return '';
        const state = String(p.state || 'awake');
        const instances: Record<string, Models.ConditionInstance[]> = p.conditions || {};"""
    ),
    (
"""        const VW: *FIX* = window as *FIX*;""",
"""        const VW = window as unknown as Record<string, { VitalColor?: { level?: (v: unknown, n: string) => string } }>;"""
    ),
    (
"""    function _isAiReady(): boolean {
        const AV: *FIX* = (window as *FIX*).InspectorAgentView;
        return !!(AV && AV._isAiConfigured && AV._isAiConfigured());
    }""",
"""    function _isAiReady(): boolean {
        const AV = (window as unknown as { InspectorAgentView?: { _isAiConfigured?: () => boolean } }).InspectorAgentView;
        return !!(AV && AV._isAiConfigured && AV._isAiConfigured());
    }"""
    ),
    (
"""    function _whatISeeHtml(): string {
        if (!_state) return '';
        const p: *FIX* = worldState.players?.[_state.charName];
        if (!p) return '';
        const area = worldState.areas?.[p.current_area];
        let body: string;
        if (area) {
            body = `<div>${area.description || ''}</div>`;
            const items = (area.items || []).map((item: *FIX*) => item.name).filter(Boolean).join(', ');
            if (items) body += `<div style="margin-top:4px;color:var(--text-dim);font-size:11px;">Items: ${items}</div>`;
            const others = Object.entries(worldState.players || {} as Record<string, *FIX*>)
                .filter(([name, q]: [string, *FIX*]) => name !== _state!.charName && q.current_area === p.current_area);""",
"""    function _whatISeeHtml(): string {
        if (!_state) return '';
        const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;
        if (!p) return '';
        const area = worldState.areas?.[p.current_area];
        let body: string;
        if (area) {
            body = `<div>${area.description || ''}</div>`;
            const items = (area.items || []).map((item: { name?: string }) => item.name).filter(Boolean).join(', ');
            if (items) body += `<div style="margin-top:4px;color:var(--text-dim);font-size:11px;">Items: ${items}</div>`;
            const others = Object.entries((worldState.players || {}) as Record<string, Models.PlayerRuntimeModel>)
                .filter(([name, q]: [string, Models.PlayerRuntimeModel]) => name !== _state!.charName && q.current_area === p.current_area);"""
    ),
    (
"""    function _latestThoughtsHtml(): string {
        if (!_state) return '';
        const cs: *FIX* = events.getCharacterState(_state.charName) || {};""",
"""    function _latestThoughtsHtml(): string {
        if (!_state) return '';
        const cs: { lastThought?: string; lastSpeech?: string; lastAction?: string; lastActionResult?: string } = (events && events.getCharacterState ? events.getCharacterState(_state.charName) : null) || {};"""
    ),
    (
"""    function _planHtml(): string {
        if (!_state) return '';
        const plan: *FIX*[] | null = (PlanTracker && PlanTracker.getPlan) ? PlanTracker.getPlan(_state.charName) : null;
        if (!plan || !plan.length) return '';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Plan - the current intent</div>
            <ol style="margin:0;padding-left:20px;font-size:11px;line-height:1.7;">${plan.map((step: *FIX*) => `<li>${esc(step)}</li>`).join('')}</ol>
        </div>`;
    }""",
"""    function _planHtml(): string {
        if (!_state) return '';
        const plan: Array<Models.PlanStep | string> | null = (PlanTracker && PlanTracker.getPlan) ? PlanTracker.getPlan(_state.charName) : null;
        if (!plan || !plan.length) return '';
        return `<div style="margin-top:14px;">
            <div style="font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;">Plan - the current intent</div>
            <ol style="margin:0;padding-left:20px;font-size:11px;line-height:1.7;">${plan.map((step: Models.PlanStep | string) => `<li>${esc(typeof step === 'object' && step !== null ? ((step as Models.PlanStep).description || (step as Models.PlanStep).action || JSON.stringify(step)) : step)}</li>`).join('')}</ol>
        </div>`;
    }"""
    ),
    (
"""    function _conversationHtml(): string {
        if (!_state) return '';
        const hist: *FIX*[] = (agent && agent.getDisplayHistory) ? agent.getDisplayHistory(_state.charName) : [];
        let body: string;
        if (hist.length > 0) {
            body = hist.map((msg: *FIX*, i: number) => {""",
"""    function _conversationHtml(): string {
        if (!_state) return '';
        const hist: Array<{ role?: string; content?: string }> = (agent && agent.getDisplayHistory) ? agent.getDisplayHistory(_state.charName) : [];
        let body: string;
        if (hist.length > 0) {
            body = hist.map((msg: { role?: string; content?: string }, i: number) => {"""
    ),
    (
"""    function _emotionEditorHtml(): string {
        if (!_state) return '';
        const p: *FIX* = worldState.players?.[_state.charName];""",
"""    function _emotionEditorHtml(): string {
        if (!_state) return '';
        const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;"""
    ),
    (
"""    function _relationshipsHtml(): string {
        if (!_state) return '';
        const me = _state.charName;
        const p: *FIX* = worldState.players?.[me];
        if (!p) return '';
        const othersExMe = (Object.entries(worldState.players || {}) as Array<[string, *FIX*]>)
            .filter(([name]) => name !== me);""",
"""    function _relationshipsHtml(): string {
        if (!_state) return '';
        const me = _state.charName;
        const p: Models.PlayerRuntimeModel | null = worldState.players?.[me] || null;
        if (!p) return '';
        const othersExMe = (Object.entries(worldState.players || {}) as Array<[string, Models.PlayerRuntimeModel]>)
            .filter(([name]) => name !== me);"""
    ),
    (
"""    function _mosiac(): *FIX* {
        if (!_state) return null;
        return worldState.players?.[_state.charName]?.mosiac || null;
    }

    function _mosiacHtml(): string {
        const m = _mosiac();
        if (!m) return '';
        const letter = (key: string, label: string, body: string) => `<div style="margin-bottom:5px;"><span style="font-family:monospace;color:#58a6ff;">${key}</span> <span style="color:var(--text-muted);font-size:9.5px;text-transform:uppercase;letter-spacing:.06em;">${label}</span><div style="font-size:10.5px;line-height:1.4;">${body}</div></div>`;
        const needs = (m.A || []).map((n: *FIX*) => `${esc(n.need)} ${n.value}`).join(', ') || 'nothing pressing';""",
"""    function _mosiac(): { A?: Array<{ need: string; value: number }>; O?: Array<{ charge: string }>; S?: { step?: { start?: number; activity?: string; area?: string } }; P?: unknown; M?: string; I?: string; C?: Record<string, unknown[]> } | null {
        if (!_state) return null;
        return (worldState.players?.[_state.charName] as unknown as { mosiac?: { A?: Array<{ need: string; value: number }>; O?: Array<{ charge: string }>; S?: { step?: { start?: number; activity?: string; area?: string } }; P?: unknown; M?: string; I?: string; C?: Record<string, unknown[]> } })?.mosiac || null;
    }

    function _mosiacHtml(): string {
        const m = _mosiac();
        if (!m) return '';
        const letter = (key: string, label: string, body: string) => `<div style="margin-bottom:5px;"><span style="font-family:monospace;color:#58a6ff;">${key}</span> <span style="color:var(--text-muted);font-size:9.5px;text-transform:uppercase;letter-spacing:.06em;">${label}</span><div style="font-size:10.5px;line-height:1.4;">${body}</div></div>`;
        const needs = (m.A || []).map((n: { need: string; value: number }) => `${esc(n.need)} ${n.value}`).join(', ') || 'nothing pressing';"""
    ),
    (
"""    function _dispositionHtml(): string {
        if (!_state) return '';
        const p: *FIX* = worldState.players?.[_state.charName];
        if (!p) return '';
        const disp: *FIX* = p.disposition || {};
        const weights: *FIX*[] = Array.isArray(disp.weights) ? disp.weights : [];
        const dials = disp.dials || (p.personality_dials || {});
        const whispers: string[] = Array.isArray(p.trait_behavior) ? p.trait_behavior : [];
        const entries = weights.slice().sort(
            (a: *FIX*, b: *FIX*) => Math.abs(Number(b.value)) - Math.abs(Number(a.value)));
        const dialEntries = Object.entries(dials);
        const gated: string[] = Array.isArray(disp.gated) ? disp.gated : [];
        if (!entries.length && !dialEntries.length && !whispers.length && !gated.length) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">no disposition signals - an unauthored character scores neutral.</div>`;
        }
        const weightRows = entries.map((w: *FIX*) => {""",
"""    function _dispositionHtml(): string {
        if (!_state) return '';
        const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;
        if (!p) return '';
        const disp = (p.disposition || {}) as { weights?: Array<{ name: string; value: number; kind?: string; base?: number; lo?: number; hi?: number }>; dials?: Record<string, number>; gated?: string[] };
        const weights: Array<{ name: string; value: number; kind?: string; base?: number; lo?: number; hi?: number }> = Array.isArray(disp.weights) ? disp.weights : [];
        const dials = disp.dials || ((p as unknown as { personality_dials?: Record<string, number> }).personality_dials || {});
        const whispers: string[] = Array.isArray((p as unknown as { trait_behavior?: string[] }).trait_behavior) ? (p as unknown as { trait_behavior: string[] }).trait_behavior : [];
        const entries = weights.slice().sort(
            (a: { value: number }, b: { value: number }) => Math.abs(Number(b.value)) - Math.abs(Number(a.value)));
        const dialEntries = Object.entries(dials);
        const gated: string[] = Array.isArray(disp.gated) ? disp.gated : [];
        if (!entries.length && !dialEntries.length && !whispers.length && !gated.length) {
            return `<div style="font-size:10.5px;color:var(--text-muted);">no disposition signals - an unauthored character scores neutral.</div>`;
        }
        const weightRows = entries.map((w: { name: string; value: number; kind?: string; base?: number; lo?: number; hi?: number }) => {"""
    ),
    (
"""    function _actionsHtml(): string {
        if (!_state) return '';
        const p: *FIX* = worldState.players?.[_state.charName];
        const actions: *FIX*[] = (p && p.disposition && Array.isArray(p.disposition.actions)) ? p.disposition.actions : [];
        if (!actions.length) return '';
        const gated = new Set<string>(((p.disposition && p.disposition.gated) || []).map((g: string) => String(g).toLowerCase()));
        const rows = actions.map((a: *FIX*) => {""",
"""    function _actionsHtml(): string {
        if (!_state) return '';
        const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;
        const actions: Array<{ verb: string; scores?: number[] }> = (p && p.disposition && Array.isArray((p.disposition as { actions?: unknown[] }).actions)) ? (p.disposition as { actions: Array<{ verb: string; scores?: number[] }> }).actions : [];
        if (!actions.length) return '';
        const gated = new Set<string>((((p.disposition as { gated?: string[] })?.gated) || []).map((g: string) => String(g).toLowerCase()));
        const rows = actions.map((a: { verb: string; scores?: number[] }) => {"""
    ),
    (
"""            const injured = ((playerConditions.injured || []) as *FIX*[])
                .filter((i: *FIX*) => i.body_part === regionId);
            const bleeding = ((playerConditions.bleeding || []) as *FIX*[])
                .filter((i: *FIX*) => i.body_part === regionId);
            const missing = ((playerConditions.missing || []) as *FIX*[])
                .filter((i: *FIX*) => i.body_part === regionId);
            const exposed = player?.region_exposed?.[regionId] !== false;
            const sensNum = bs.sensitivity !== undefined ? parseFloat(bs.sensitivity) : NaN;
            const sens = Number.isFinite(sensNum) ? sensNum.toFixed(2) : '-';
            const chips: string[] = [];
            if (injured.length) chips.push(`<span style="color:var(--yellow);">🤕 Lv${Math.max(...injured.map((i: *FIX*) => i.level || 1))}</span>`);""",
"""            const injured = ((playerConditions.injured || []) as Array<{ body_part?: string; level?: number }>)
                .filter((i: { body_part?: string }) => i.body_part === regionId);
            const bleeding = ((playerConditions.bleeding || []) as Array<{ body_part?: string }>)
                .filter((i: { body_part?: string }) => i.body_part === regionId);
            const missing = ((playerConditions.missing || []) as Array<{ body_part?: string }>)
                .filter((i: { body_part?: string }) => i.body_part === regionId);
            const exposed = player?.region_exposed?.[regionId] !== false;
            const sensNum = bs.sensitivity !== undefined ? parseFloat(bs.sensitivity) : NaN;
            const sens = Number.isFinite(sensNum) ? sensNum.toFixed(2) : '-';
            const chips: string[] = [];
            if (injured.length) chips.push(`<span style="color:var(--yellow);">🤕 Lv${Math.max(...injured.map((i: { level?: number }) => i.level || 1))}</span>`);"""
    ),
    (
"""                if (!ok) {
                    live.*FIX*= `<span style="color:#e08a92;">cannot project: ${esc(data.error || 'rejected')}</span>`;
                    return;
                }
                const c = data.compiled || {};
                live.*FIX*= `${c.base_description ? `<div style="margin-bottom:6px;">${esc(c.base_description)}</div>` : ''}
                    ${c.personality ? `<div style="color:var(--text-dim);">${esc(c.personality)}</div>` : ''}
                    ${(c.interest_tags?.length || c.fear_tags?.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">drawn to ${(c.interest_tags || []).map(esc).join(', ') || '-'} · fears ${(c.fear_tags || []).map(esc).join(', ') || '-'}</div>` : ''}`;""",
"""                if (!ok) {
                    window.Lit.render(window.Lit.unsafeHTML(`<span style="color:#e08a92;">cannot project: ${esc((data as { error?: string }).error || 'rejected')}</span>`), live);
                    return;
                }
                const c = (data as { compiled?: { base_description?: string; personality?: string; interest_tags?: string[]; fear_tags?: string[] } }).compiled || {};
                window.Lit.render(window.Lit.unsafeHTML(`${c.base_description ? `<div style="margin-bottom:6px;">${esc(c.base_description)}</div>` : ''}
                    ${c.personality ? `<div style="color:var(--text-dim);">${esc(c.personality)}</div>` : ''}
                    ${(c.interest_tags?.length || c.fear_tags?.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">drawn to ${(c.interest_tags || []).map(esc).join(', ') || '-'} · fears ${(c.fear_tags || []).map(esc).join(', ') || '-'}</div>` : ''}`), live);"""
    ),
    (
"""        const TM: *FIX* = (window as unknown as { TagMultiselect?: unknown }).TagMultiselect;
        const migPlayer: *FIX* = _state ? worldState.players?.[_state.charName] : null;
        if (TM && migPlayer) {
            const itBox = _container.querySelector(`#interest-tag-multiselect-mind-${_safeId()}`);
            if (itBox) new TM(itBox, {
                tags: Array.isArray(migPlayer.interest_tags) ? migPlayer.interest_tags : [],
                appliesTo: 'characters', allowNew: true, placeholder: 'e.g. magic, food, documents...',
                onChange: (tags: *FIX*[]) => { ApiClient.updateCharacter(_state!.charName, { interest_tags: tags }).then(() => worldState.fetch()); }
            });
            const ftBox = _container.querySelector(`#fear-tag-multiselect-mind-${_safeId()}`);
            if (ftBox) new TM(ftBox, {
                tags: Array.isArray(migPlayer.fear_tags) ? migPlayer.fear_tags : [],
                appliesTo: 'characters', allowNew: true, placeholder: 'e.g. goblin, the dark, magic...',
                onChange: (tags: *FIX*[]) => { ApiClient.updateCharacter(_state!.charName, { fear_tags: tags }).then(() => worldState.fetch()); }
            });
        }
        const KB: *FIX* = (window as unknown as { KnownBySection?: unknown }).KnownBySection;""",
"""        const TM = (window as unknown as { TagMultiselect?: new (el: Element, opts: unknown) => unknown }).TagMultiselect;
        const migPlayer: Models.PlayerRuntimeModel | null = _state ? (worldState.players?.[_state.charName] || null) : null;
        if (TM && migPlayer) {
            const itBox = _container.querySelector(`#interest-tag-multiselect-mind-${_safeId()}`);
            if (itBox) new TM(itBox, {
                tags: Array.isArray(migPlayer.interest_tags) ? migPlayer.interest_tags : [],
                appliesTo: 'characters', allowNew: true, placeholder: 'e.g. magic, food, documents...',
                onChange: (tags: string[]) => { ApiClient.updateCharacter(_state!.charName, { interest_tags: tags }).then(() => worldState.fetch()); }
            });
            const ftBox = _container.querySelector(`#fear-tag-multiselect-mind-${_safeId()}`);
            if (ftBox) new TM(ftBox, {
                tags: Array.isArray(migPlayer.fear_tags) ? migPlayer.fear_tags : [],
                appliesTo: 'characters', allowNew: true, placeholder: 'e.g. goblin, the dark, magic...',
                onChange: (tags: string[]) => { ApiClient.updateCharacter(_state!.charName, { fear_tags: tags }).then(() => worldState.fetch()); }
            });
        }
        const KB = (window as unknown as { KnownBySection?: { buildKnownChips?: (name: string) => Node } }).KnownBySection;"""
    )
]

applied = 0
for src, dst in replacements:
    if src in content:
        content = content.replace(src, dst)
        applied += 1
    else:
        print(f"FAILED TO FIND:\n{src[:100]}...")

print(f"Applied {applied}/{len(replacements)} replacements.")
remaining = content.count("*FIX*")
print(f"Remaining *FIX* markers: {remaining}")

assert '\u2014' not in content and '—' not in content, "Em-dash introduced!"

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Saved mind-view.ts successfully.")
