import re
import sys

path = "static/js/inspector/mind-view.ts"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

assert '\u2014' not in content and '—' not in content, "Em-dash in original file"

replacements = [
    # Top & types
    ("function _catOf(m: *FIX*): string {",
     "function _catOf(m: Models.MemoryRecord): string {"),

    ("const tags = Array.isArray(m.tags) ? m.tags.map((t: *FIX*) => String(t).toLowerCase()) : [];",
     "const tags = Array.isArray(m.tags) ? m.tags.map((t: unknown) => String(t).toLowerCase()) : [];"),

    ("""interface PersonaState {
    status: 'loading' | 'ok' | 'error';
    record: Record<string, *FIX*>;
    schema: *FIX*;
    hints: Record<string, string>;
    /** Identity pick-list vocabulary served by GET /record (engine owns it). */
    suggestions?: Record<string, string[]>;
    lifecycle?: *FIX*;
    stale: boolean;
    dirty: boolean;
    preview: *FIX*;""",
     """interface PersonaState {
    status: 'loading' | 'ok' | 'error';
    record: Record<string, unknown>;
    schema: Record<string, unknown> | null;
    hints: Record<string, string>;
    /** Identity pick-list vocabulary served by GET /record (engine owns it). */
    suggestions?: Record<string, string[]>;
    lifecycle?: Record<string, unknown> | null;
    stale: boolean;
    dirty: boolean;
    preview: Record<string, unknown> | null;"""),

    ("const act = (m: *FIX*): number => (typeof m.activation === 'number' ? m.activation : 1);",
     "const act = (m: Models.MemoryRecord): number => (typeof m.activation === 'number' ? m.activation : 1);"),

    ("const conf = (m: *FIX*): number => (typeof m.confidence === 'number' ? m.confidence : (String(m.source) === 'manual' || String(m.source) === 'preconceived' ? 1 : 0.7));",
     "const conf = (m: Models.MemoryRecord): number => (typeof m.confidence === 'number' ? m.confidence : (String(m.source) === 'manual' || String(m.source) === 'preconceived' ? 1 : 0.7));"),

    ("function _memories(): *FIX*[] {",
     "function _memories(): Models.MemoryRecord[] {"),

    ("function _visible(memories: *FIX*[]): *FIX*[] {\n        if (!_state) return [];\n        return memories.filter((m: *FIX*) => {",
     "function _visible(memories: Models.MemoryRecord[]): Models.MemoryRecord[] {\n        if (!_state) return [];\n        return memories.filter((m: Models.MemoryRecord) => {"),

    ("const tags = (Array.isArray(m.tags) ? m.tags : []).map((t: *FIX*) => String(t).toLowerCase());",
     "const tags = (Array.isArray(m.tags) ? m.tags : []).map((t: unknown) => String(t).toLowerCase());"),

    ("function _statsHtml(memories: *FIX*[]): string {\n        const n = (pred: (m: *FIX*) => boolean) => memories.filter(pred).length;\n        const epis = n((m: *FIX*) => _catOf(m) === 'episodic');\n        const beliefs = n((m: *FIX*) => ['belief', 'semantic'].includes(_catOf(m)));\n        const social = n((m: *FIX*) => _catOf(m) === 'social');\n        const proc = n((m: *FIX*) => _catOf(m) === 'procedural');\n        const contra = n((m: *FIX*) => Array.isArray(m.contradicts) && m.contradicts.length);\n        const faded = n((m: *FIX*) => act(m) < 0.5);\n        const reinf = memories.reduce((a: number, m: *FIX*) => a + (Number(m.reinforcements) || 0), 0);\n        const avgConf = memories.length ? Math.round(memories.reduce((a: number, m: *FIX*) => a + conf(m), 0) / memories.length * 100) : 100;",
     "function _statsHtml(memories: Models.MemoryRecord[]): string {\n        const n = (pred: (m: Models.MemoryRecord) => boolean) => memories.filter(pred).length;\n        const epis = n((m: Models.MemoryRecord) => _catOf(m) === 'episodic');\n        const beliefs = n((m: Models.MemoryRecord) => ['belief', 'semantic'].includes(_catOf(m)));\n        const social = n((m: Models.MemoryRecord) => _catOf(m) === 'social');\n        const proc = n((m: Models.MemoryRecord) => _catOf(m) === 'procedural');\n        const contra = n((m: Models.MemoryRecord) => Array.isArray(m.contradicts) && m.contradicts.length);\n        const faded = n((m: Models.MemoryRecord) => act(m) < 0.5);\n        const reinf = memories.reduce((a: number, m: Models.MemoryRecord) => a + (Number(m.reinforcements) || 0), 0);\n        const avgConf = memories.length ? Math.round(memories.reduce((a: number, m: Models.MemoryRecord) => a + conf(m), 0) / memories.length * 100) : 100;"),

    ("function _timelineHtml(memories: *FIX*[]): string {\n        const ticks = memories.map((m: *FIX*) => Number(m.tick) || 0);\n        const min = ticks.length ? Math.min(...ticks) : 0;\n        const max = ticks.length ? Math.max(...ticks) : 0;\n        const span = Math.max(1, max - min);\n        const dots = memories.map((m: *FIX*) => {",
     "function _timelineHtml(memories: Models.MemoryRecord[]): string {\n        const ticks = memories.map((m: Models.MemoryRecord) => Number(m.tick) || 0);\n        const min = ticks.length ? Math.min(...ticks) : 0;\n        const max = ticks.length ? Math.max(...ticks) : 0;\n        const span = Math.max(1, max - min);\n        const dots = memories.map((m: Models.MemoryRecord) => {"),

    ("function _cardHtml(m: *FIX*): string {",
     "function _cardHtml(m: Models.MemoryRecord): string {"),

    ("function _recordAndEvidenceHtml(m: *FIX*, charName?: string): string {\n        const cname = charName || _state?.charName;\n        const p: *FIX* = cname ? worldState.players?.[cname] : null;\n        const livedLog: *FIX*[] = Array.isArray(p?.lived_log) ? p.lived_log : [];\n        const mText = (m.text || '').toLowerCase();\n        const mTick = typeof m.tick === 'number' ? m.tick : null;\n        const mTags = (Array.isArray(m.tags) ? m.tags : []).map((t: *FIX*) => String(t).toLowerCase());\n\n        // Find candidates in lived_log\n        const matchedLog = livedLog.filter((entry: *FIX*) => {\n            if (mTick !== null && typeof entry.tick === 'number' && Math.abs(entry.tick - mTick) <= 2) return true;\n            const eText = (entry.text || entry.description || entry.action || '').toLowerCase();\n            if (eText && (mText.includes(eText) || eText.includes(mText))) return true;\n            if (Array.isArray(entry.tags)) {\n                const eTags = (Array.isArray(entry.tags) ? entry.tags : []).map((t: *FIX*) => String(t).toLowerCase());\n                if (eTags.some(t => mTags.includes(t))) return true;\n            }\n            return false;\n        }).slice(0, 5);",
     "function _recordAndEvidenceHtml(m: Models.MemoryRecord, charName?: string): string {\n        const cname = charName || _state?.charName;\n        const p: Models.PlayerRuntimeModel | null = cname ? worldState.players?.[cname] : null;\n        const livedLog: Array<Record<string, unknown>> = Array.isArray(p?.lived_log) ? p.lived_log : [];\n        const mText = (m.text || '').toLowerCase();\n        const mTick = typeof m.tick === 'number' ? m.tick : null;\n        const mTags = (Array.isArray(m.tags) ? m.tags : []).map((t: unknown) => String(t).toLowerCase());\n\n        // Find candidates in lived_log\n        const matchedLog = livedLog.filter((entry: Record<string, unknown>) => {\n            if (mTick !== null && typeof entry.tick === 'number' && Math.abs((entry.tick as number) - mTick) <= 2) return true;\n            const eText = String(entry.text || entry.description || entry.action || '').toLowerCase();\n            if (eText && (mText.includes(eText) || eText.includes(mText))) return true;\n            if (Array.isArray(entry.tags)) {\n                const eTags = (Array.isArray(entry.tags) ? entry.tags : []).map((t: unknown) => String(t).toLowerCase());\n                if (eTags.some(t => mTags.includes(t))) return true;\n            }\n            return false;\n        }).slice(0, 5);"),

    ("const entityIds = (Array.isArray(m.entity_ids) ? m.entity_ids : []).map((e: *FIX*) => String(e));\n        const tags = (Array.isArray(m.tags) ? m.tags : []).map((t: *FIX*) => String(t));",
     "const entityIds = (Array.isArray(m.entity_ids) ? m.entity_ids : []).map((e: unknown) => String(e));\n        const tags = (Array.isArray(m.tags) ? m.tags : []).map((t: unknown) => String(t));"),

    ("? matchedLog.map((entry: *FIX*) => {",
     "? matchedLog.map((entry: Record<string, unknown>) => {"),

    ("function _detailHtml(m: *FIX* | null, all: *FIX*[]): string {\n        if (!m) return '<div class=\"mind-empty\">Pick a memory on the left to inspect its dynamics, evidence, and connections.</div>';\n        const cat = _catOf(m);\n        const color = CAT_COLORS[cat] || '#8b949e';\n        const byId = (id: string) => all.find((x: *FIX*) => x.id === id);",
     "function _detailHtml(m: Models.MemoryRecord | null, all: Models.MemoryRecord[]): string {\n        if (!m) return '<div class=\"mind-empty\">Pick a memory on the left to inspect its dynamics, evidence, and connections.</div>';\n        const cat = _catOf(m);\n        const color = CAT_COLORS[cat] || '#8b949e';\n        const byId = (id: string) => all.find((x: Models.MemoryRecord) => x.id === id);"),

    ("const entityIds = (Array.isArray(m.entity_ids) ? m.entity_ids : []).map((e: *FIX*) => String(e));\n        const siblings = entityIds.length\n            ? all.filter((x: *FIX*) => x.id !== m.id && (x.entity_ids || []).some((e: *FIX*) => entityIds.includes(String(e)))).slice(0, 5)\n            : [];\n        const sibRows = siblings.map((other: *FIX*) =>",
     "const entityIds = (Array.isArray(m.entity_ids) ? m.entity_ids : []).map((e: unknown) => String(e));\n        const siblings = entityIds.length\n            ? all.filter((x: Models.MemoryRecord) => x.id !== m.id && (x.entity_ids || []).some((e: unknown) => entityIds.includes(String(e)))).slice(0, 5)\n            : [];\n        const sibRows = siblings.map((other: Models.MemoryRecord) =>"),

    ("const relTags = (Array.isArray(m.tags) ? m.tags : []).filter((t: *FIX*) => String(t).toLowerCase().startsWith('rel:'));",
     "const relTags = (Array.isArray(m.tags) ? m.tags : []).filter((t: unknown) => String(t).toLowerCase().startsWith('rel:'));"),

    ("${emoList.map((e: *FIX*) => _bar(String(e.label || ''), (Number(e.intensity) || 0) / 10, 1, '#e0a33c')).join('')}",
     "${emoList.map((e: { label?: string; intensity?: number }) => _bar(String(e.label || ''), (Number(e.intensity) || 0) / 10, 1, '#e0a33c')).join('')}"),

    ("${relTags.length ? `<div style=\"font-size:10px;color:var(--f788ba, #f778ba);margin-bottom:8px;\">${relTags.map((t: *FIX*) => _badge(String(t), '#f778ba')).join(' ')}</div>` : ''}",
     "${relTags.length ? `<div style=\"font-size:10px;color:var(--f788ba, #f778ba);margin-bottom:8px;\">${relTags.map((t: unknown) => _badge(String(t), '#f778ba')).join(' ')}</div>` : ''}"),

    ("function _accessibilityHtml(all: *FIX*[]): string {\n        const sorted = [...all].sort((a: *FIX*, b: *FIX*) => act(a) - act(b)).slice(0, 7);\n        const faded = all.filter((m: *FIX*) => act(m) < 0.5).length;\n        const row = (m: *FIX*): string => {",
     "function _accessibilityHtml(all: Models.MemoryRecord[]): string {\n        const sorted = [...all].sort((a: Models.MemoryRecord, b: Models.MemoryRecord) => act(a) - act(b)).slice(0, 7);\n        const faded = all.filter((m: Models.MemoryRecord) => act(m) < 0.5).length;\n        const row = (m: Models.MemoryRecord): string => {"),

    ("function _goals(): *FIX*[] {\n        if (!_state) return [];\n        return worldState.players?.[_state.charName]?.goals || [];\n    }\n\n    function _goalRowHtml(g: *FIX*): string {\n        const statusColors: Record<string, string> = {\n            active: '#3fb950', completed: '#58a6ff', failed: '#f85149', abandoned: 'var(--text-dim)'\n        };\n        const val = (s: *FIX*) => esc(String(s ?? ''));",
     "function _goals(): Models.GoalModel[] {\n        if (!_state) return [];\n        return worldState.players?.[_state.charName]?.goals || [];\n    }\n\n    function _goalRowHtml(g: Models.GoalModel): string {\n        const statusColors: Record<string, string> = {\n            active: '#3fb950', completed: '#58a6ff', failed: '#f85149', abandoned: 'var(--text-dim)'\n        };\n        const val = (s: unknown) => esc(String(s ?? ''));"),

    ("? goals.map((g: *FIX*) => _goalRowHtml(g)).join('')",
     "? goals.map((g: Models.GoalModel) => _goalRowHtml(g)).join('')"),

    ("function _collectGoals(): *FIX*[] {\n        if (!_container) return [];\n        const box = _container.querySelector('#mind-goals-list');\n        if (!box) return [];\n        return Array.from(box.querySelectorAll('.mind-goal')).map((row: *FIX*) => ({\n            what: (row.querySelector('.goal-what') as HTMLInputElement)?.value.trim() || '',\n            why: (row.querySelector('.goal-why') as HTMLInputElement)?.value.trim() || '',\n            status: (row.querySelector('.goal-status') as HTMLSelectElement)?.value || 'active',\n            source: (row.querySelector('.goal-source') as HTMLInputElement)?.value.trim() || 'user',\n            tick: parseInt((row.querySelector('.goal-tick') as HTMLInputElement)?.value || '0', 10),\n        })).filter((g: *FIX*) => g.what);\n    }",
     "function _collectGoals(): Models.GoalModel[] {\n        if (!_container) return [];\n        const box = _container.querySelector('#mind-goals-list');\n        if (!box) return [];\n        return Array.from(box.querySelectorAll('.mind-goal')).map((row: Element) => ({\n            what: (row.querySelector('.goal-what') as HTMLInputElement)?.value.trim() || '',\n            why: (row.querySelector('.goal-why') as HTMLInputElement)?.value.trim() || '',\n            status: (row.querySelector('.goal-status') as HTMLSelectElement)?.value as Models.GoalStatus || 'active',\n            source: (row.querySelector('.goal-source') as HTMLInputElement)?.value.trim() || 'user',\n            tick: parseInt((row.querySelector('.goal-tick') as HTMLInputElement)?.value || '0', 10),\n        })).filter((g: Models.GoalModel) => g.what);\n    }"),

    ("function _goalHistory(): *FIX*[] {",
     "function _goalHistory(): Array<{ tick?: number; what?: string; why?: string; status?: string }> {"),

    ("const rows = log.slice().reverse().map((e: *FIX*) => {",
     "const rows = log.slice().reverse().map((e: { tick?: number; what?: string; why?: string; status?: string }) => {"),

    ("function _obligations(): *FIX*[] {\n        if (!_state) return [];\n        return worldState.players?.[_state.charName]?.obligations || [];\n    }",
     "function _obligations(): Models.ObligationModel[] {\n        if (!_state) return [];\n        return worldState.players?.[_state.charName]?.obligations || [];\n    }"),

    ("const rows = obligations.map((o: *FIX*) => {",
     "const rows = obligations.map((o: Models.ObligationModel) => {"),

    ("function _schedule(): *FIX*[] {\n        if (!_state) return [];\n        return worldState.players?.[_state.charName]?.schedule || [];\n    }\n\n    function _hhmm(minutes: *FIX*): string {",
     "function _schedule(): Array<{ time?: number | string; activity?: string; location?: string }> {\n        if (!_state) return [];\n        return worldState.players?.[_state.charName]?.schedule || [];\n    }\n\n    function _hhmm(minutes: number | string): string {"),

    ("const rows = steps.map((s: *FIX*) => `<div style=\"display:flex;gap:8px;align-items:baseline;font-size:10.5px;padding:2px 0;border-bottom:1px solid var(--border-light);\">",
     "const rows = steps.map((s: { time?: number | string; activity?: string; location?: string }) => `<div style=\"display:flex;gap:8px;align-items:baseline;font-size:10.5px;padding:2px 0;border-bottom:1px solid var(--border-light);\">"),

    ("function _activePursuit(): *FIX* {\n        if (!_state) return null;\n        return worldState.players?.[_state.charName]?.active_pursuit || null;\n    }\n\n    function _plan(): *FIX* {\n        if (!_state) return null;\n        return worldState.players?.[_state.charName]?.plan || null;\n    }\n\n    function _stepLabel(step: *FIX*): string {",
     "function _activePursuit(): Models.ActivePursuitModel | null {\n        if (!_state) return null;\n        return worldState.players?.[_state.charName]?.active_pursuit || null;\n    }\n\n    function _plan(): Models.PlanModel | null {\n        if (!_state) return null;\n        return worldState.players?.[_state.charName]?.plan || null;\n    }\n\n    function _stepLabel(step: Models.PlanStep | string): string {"),

    ("const a: *FIX* = worldState.players?.[_state.charName]?.activity;",
     "const a: unknown = worldState.players?.[_state.charName]?.activity;"),

    ("const p: *FIX* = worldState.players?.[_state.charName];\n        if (!p) return '';\n        const emo: *FIX* = p.emotion || null;",
     "const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;\n        if (!p) return '';\n        const emo: { label?: string; intensity?: number } | null = p.emotion || null;"),

    ("const mems: *FIX*[] = Array.isArray(p.memories) ? p.memories : [];\n        let lastFeeling: *FIX* = null;\n        for (let i = mems.length - 1; i >= 0; i--) {\n            const m = mems[i];\n            if (Array.isArray(m.emotions) && m.emotions.length > 0) {\n                const top = (m.emotions as Array<{ label?: string; intensity?: number }>)\n                    .slice().sort((a, b) => (Number(b.intensity) || 0) - (Number(a.intensity) || 0))[0];\n                if (top?.label) {\n                    lastFeeling = `${top.label} (${top.intensity || 1}/10) · ${m.text || 'memory'}`;\n                    break;\n                }\n            }\n        }\n        const fears = (p.fear_tags || []).map(String);\n        const presentArea = worldState.areas?.[p.current_area || ''] || {};\n        const liveTags = [ ...(presentArea.tags || []), ...(presentArea.features || []) ]\n            .map(t => String(t).toLowerCase());\n        const matchedFears = fears.filter(f => liveTags.includes(f.toLowerCase()));\n        const activeConditions = (Object.values(p.conditions || {}) as Array<Array<{ label?: string }>>)\n            .flat()\n            .map((e: *FIX*) => String(e.label || '').toLowerCase());",
     "const mems: Models.MemoryRecord[] = Array.isArray(p.memories) ? p.memories : [];\n        let lastFeeling: string | null = null;\n        for (let i = mems.length - 1; i >= 0; i--) {\n            const m = mems[i];\n            if (Array.isArray(m.emotions) && m.emotions.length > 0) {\n                const top = (m.emotions as Array<{ label?: string; intensity?: number }>)\n                    .slice().sort((a, b) => (Number(b.intensity) || 0) - (Number(a.intensity) || 0))[0];\n                if (top?.label) {\n                    lastFeeling = `${top.label} (${top.intensity || 1}/10) · ${m.text || 'memory'}`;\n                    break;\n                }\n            }\n        }\n        const fears = (p.fear_tags || []).map(String);\n        const presentArea = worldState.areas?.[p.current_area || ''] || {};\n        const liveTags = [ ...(presentArea.tags || []), ...(presentArea.features || []) ]\n            .map(t => String(t).toLowerCase());\n        const matchedFears = fears.filter(f => liveTags.includes(f.toLowerCase()));\n        const activeConditions = (Object.values(p.conditions || {}) as Array<Array<{ label?: string }>>)\n            .flat()\n            .map((e: { label?: string }) => String(e.label || '').toLowerCase());"),

    ("const p: *FIX* = worldState.players?.[_state.charName];\n        if (!p) return '';\n        const instances: *FIX* = p.conditions || {};",
     "const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;\n        if (!p) return '';\n        const instances: Record<string, Models.ConditionInstance[]> = p.conditions || {};"),

    ("const VW: *FIX* = window as *FIX*;\n        const events = VW.appEvents || (window as *FIX*).appEvents;",
     "const VW = window as unknown as Record<string, unknown>;\n        const events = (VW.appEvents || (window as unknown as { appEvents?: unknown }).appEvents) as { getCharacterState?: (n: string) => { current_action?: string; detailedTimeline?: Array<Record<string, unknown>> } };"),

    ("const AV: *FIX* = (window as *FIX*).InspectorAgentView;\n        const pillFn = AV && AV._renderConditionPill;",
     "const AV = (window as unknown as { InspectorAgentView?: { _renderConditionPill: Function } }).InspectorAgentView;\n        const pillFn = AV && AV._renderConditionPill;"),

    ("carrying *FIX* of these tags makes this character <code>frightened</code>.",
     "carrying any of these tags makes this character <code>frightened</code>."),

    ("const p: *FIX* = worldState.players?.[_state.charName];\n        if (!p) return '';\n        const area = worldState.areas?.[p.current_area || ''] || {};\n        const items = (area.items || []).map((item: *FIX*) => item.name).filter(Boolean).join(', ');\n        const others = Object.entries(worldState.players || {} as Record<string, *FIX*>)\n            .filter(([name, q]: [string, *FIX*]) => name !== _state!.charName && q.current_area === p.current_area);",
     "const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;\n        if (!p) return '';\n        const area = worldState.areas?.[p.current_area || ''] || {};\n        const items = (area.items || []).map((item: { name?: string }) => item.name).filter(Boolean).join(', ');\n        const others = Object.entries((worldState.players || {}) as Record<string, Models.PlayerRuntimeModel>)\n            .filter(([name, q]: [string, Models.PlayerRuntimeModel]) => name !== _state!.charName && q.current_area === p.current_area);"),

    ("const cs: *FIX* = events.getCharacterState(_state.charName) || {};\n        const curAction = cs.current_action || '(idle)';\n        const PlanTracker = (window as unknown as { PlanTracker?: { getPlan?: (n: string) => *FIX*[] } }).PlanTracker;\n        const plan: *FIX*[] | null = (PlanTracker && PlanTracker.getPlan) ? PlanTracker.getPlan(_state.charName) : null;\n        const planHtml = plan && plan.length\n            ? `<div style=\"margin-top:8px;\"><div style=\"font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px;\">Live Action Plan</div>\n            <ol style=\"margin:0;padding-left:20px;font-size:11px;line-height:1.7;\">${plan.map((step: *FIX*) => `<li>${esc(step)}</li>`).join('')}</ol></div>`\n            : '';",
     "const cs = (events && events.getCharacterState ? events.getCharacterState(_state.charName) : null) || {};\n        const curAction = cs.current_action || '(idle)';\n        const PlanTracker = (window as unknown as { PlanTracker?: { getPlan?: (n: string) => Array<Models.PlanStep | string> } }).PlanTracker;\n        const plan: Array<Models.PlanStep | string> | null = (PlanTracker && PlanTracker.getPlan) ? PlanTracker.getPlan(_state.charName) : null;\n        const planHtml = plan && plan.length\n            ? `<div style=\"margin-top:8px;\"><div style=\"font-size:9.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px;\">Live Action Plan</div>\n            <ol style=\"margin:0;padding-left:20px;font-size:11px;line-height:1.7;\">${plan.map((step: Models.PlanStep | string) => `<li>${esc(typeof step === 'object' && step !== null ? ((step as Models.PlanStep).description || (step as Models.PlanStep).action || JSON.stringify(step)) : step)}</li>`).join('')}</ol></div>`\n            : '';"),

    ("""                if (!list.length) {
                    live.*FIX*= `${head}<div style="font-size:10px;color:var(--text-dim);">None yet - teach them (Skill lessons, recipe notes) or raise the gating skill.</div>`;
                    return;
                }
                const srcColor: Record<string, string> = {
                    global: 'var(--text-dim)', taught: '#58a6ff', discovered: '#3fb950',
                    cookbook: '#d29922', skill: '#bc8cff',
                };
                live.*FIX*= `${head}${list.map((r) => {
                    const meta = [
                        r.skill ? `${esc(r.skill)} ${r.dc ?? 10}` : '',
                        r.duration_min ? `${r.duration_min}m` : '',
                    ].filter((s) => s).join(' · ');
                    return `<div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:11px;">
                        <span style="flex:1;"><a href="#" data-recipe-lib="${esc(r.id)}" style="color:var(--text);text-decoration:underline dotted;" title="Browse in the library (read-only here)">🧾 ${esc(r.name)}</a> <span style="font-size:9px;color:${srcColor[r.source] || 'var(--text-dim)'};">${esc(r.source)}</span>${meta ? ` <span style="font-size:9px;color:var(--text-muted);">${esc(meta)}</span>` : ''}</span>
                        ${controlled ? `<button class="btn btn-sm" onclick="runAction('Make ${esc(r.name)}','${_state!.escName}')" style="font-size:9px;padding:2px 8px;" title="Same as typing Make ${esc(r.name)} in the turn box">Make</button>` : ''}
                    </div>`;
                }).join('')}`;""",
     """                if (!list.length) {
                    window.Lit.render(window.Lit.unsafeHTML(`${head}<div style="font-size:10px;color:var(--text-dim);">None yet - teach them (Skill lessons, recipe notes) or raise the gating skill.</div>`), live);
                    return;
                }
                const srcColor: Record<string, string> = {
                    global: 'var(--text-dim)', taught: '#58a6ff', discovered: '#3fb950',
                    cookbook: '#d29922', skill: '#bc8cff',
                };
                window.Lit.render(window.Lit.unsafeHTML(`${head}${list.map((r: { id: string; name: string; source: string; skill?: string; dc?: number; duration_min?: number }) => {
                    const meta = [
                        r.skill ? `${esc(r.skill)} ${r.dc ?? 10}` : '',
                        r.duration_min ? `${r.duration_min}m` : '',
                    ].filter((s) => s).join(' · ');
                    return `<div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:11px;">
                        <span style="flex:1;"><a href="#" data-recipe-lib="${esc(r.id)}" style="color:var(--text);text-decoration:underline dotted;" title="Browse in the library (read-only here)">🧾 ${esc(r.name)}</a> <span style="font-size:9px;color:${srcColor[r.source] || 'var(--text-dim)'};">${esc(r.source)}</span>${meta ? ` <span style="font-size:9px;color:var(--text-muted);">${esc(meta)}</span>` : ''}</span>
                        ${controlled ? `<button class="btn btn-sm" onclick="runAction('Make ${esc(r.name)}','${_state!.escName}')" style="font-size:9px;padding:2px 8px;" title="Same as typing Make ${esc(r.name)} in the turn box">Make</button>` : ''}
                    </div>`;
                }).join('')}`), live);"""),

    ("const lib = (window as unknown as { VW?: *FIX* }).VW?.libraryBrowser;",
     "const lib = (window as unknown as { VW?: { libraryBrowser?: { open: (s: string) => void } } }).VW?.libraryBrowser;"),

    ("const cs: *FIX* = events.getCharacterState(_state.charName) || {};\n        const timeline: *FIX*[] = cs.detailedTimeline || [];",
     "const cs = (events && events.getCharacterState ? events.getCharacterState(_state.charName) : null) || {};\n        const timeline: Array<Record<string, unknown>> = cs.detailedTimeline || [];"),

    ("const hist: *FIX*[] = (agent && agent.getDisplayHistory) ? agent.getDisplayHistory(_state.charName) : [];\n        let body = '';\n        if (hist.length) {\n            body = hist.map((msg: *FIX*, i: number) => {",
     "const hist: Array<Record<string, unknown>> = (agent && agent.getDisplayHistory) ? agent.getDisplayHistory(_state.charName) : [];\n        let body = '';\n        if (hist.length) {\n            body = hist.map((msg: Record<string, unknown>, i: number) => {"),

    ("const p: *FIX* = worldState.players?.[_state.charName];\n        if (!p) return '<div class=\"mind-empty\">Character not found.</div>';",
     "const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;\n        if (!p) return '<div class=\"mind-empty\">Character not found.</div>';"),

    ("const p: *FIX* = worldState.players?.[me];\n        const rels: Record<string, number> = (p && p.relationships) ? p.relationships : {};\n        const othersExMe = (Object.entries(worldState.players || {}) as Array<[string, *FIX*]>)\n            .filter(([name]) => name !== me);",
     "const p: Models.PlayerRuntimeModel | null = worldState.players?.[me] || null;\n        const rels: Record<string, number> = (p && p.relationships) ? p.relationships : {};\n        const othersExMe = (Object.entries(worldState.players || {}) as Array<[string, Models.PlayerRuntimeModel]>)\n            .filter(([name]) => name !== me);"),

    ("// push while typing would destroy unsaved form input. *FIX*\n            // focused field counts - including chip inputs, which carry",
     "// push while typing would destroy unsaved form input. Any\n            // focused field counts - including chip inputs, which carry"),

    ("function _mosiac(): *FIX* {\n        const p = _state ? worldState.players?.[_state.charName] : null;\n        return (p && p.mosaic) ? p.mosaic : {};\n    }\n\n    function _mosaicHtml(): string {\n        const m = _mosiac();\n        const needs = (m.A || []).map((n: *FIX*) => `${esc(n.need)} ${n.value}`).join(', ') || 'nothing pressing';",
     "function _mosiac(): { A?: Array<{ need: string; value: number }>; O?: Array<{ charge: string }>; S?: unknown; P?: unknown; M?: unknown; C?: unknown } {\n        const p = _state ? worldState.players?.[_state.charName] : null;\n        return (p && (p as unknown as { mosaic?: Record<string, unknown> }).mosaic) ? (p as unknown as { mosaic: { A?: Array<{ need: string; value: number }>; O?: Array<{ charge: string }> } }).mosaic : {};\n    }\n\n    function _mosaicHtml(): string {\n        const m = _mosiac();\n        const needs = (m.A || []).map((n: { need: string; value: number }) => `${esc(n.need)} ${n.value}`).join(', ') || 'nothing pressing';"),

    ("${letter('O', 'obligations', (m.O || []).length ? (m.O || []).map((o: *FIX*) => esc(o.charge)).join(', ') : 'none')}",
     "${letter('O', 'obligations', (m.O || []).length ? (m.O || []).map((o: { charge: string }) => esc(o.charge)).join(', ') : 'none')}"),

    ("const p: *FIX* = worldState.players?.[_state.charName];\n        if (!p) return '';\n        const disp: *FIX* = p.disposition || {};\n        const weights: *FIX*[] = Array.isArray(disp.weights) ? disp.weights : [];\n        const entries = weights.slice().sort(\n            (a: *FIX*, b: *FIX*) => Math.abs(Number(b.value)) - Math.abs(Number(a.value)));\n        const weightRows = entries.map((w: *FIX*) => {",
     "const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;\n        if (!p) return '';\n        const disp = (p.disposition || {}) as { weights?: Array<{ name: string; value: number }>; actions?: Array<{ action: string; weight: number }> };\n        const weights: Array<{ name: string; value: number }> = Array.isArray(disp.weights) ? disp.weights : [];\n        const entries = weights.slice().sort(\n            (a: { value: number }, b: { value: number }) => Math.abs(Number(b.value)) - Math.abs(Number(a.value)));\n        const weightRows = entries.map((w: { name: string; value: number }) => {"),

    ("const p: *FIX* = worldState.players?.[_state.charName];\n        const actions: *FIX*[] = (p && p.disposition && Array.isArray(p.disposition.actions)) ? p.disposition.actions : [];\n        if (!actions.length) return '';\n        const rows = actions.map((a: *FIX*) => {",
     "const p: Models.PlayerRuntimeModel | null = worldState.players?.[_state.charName] || null;\n        const disp = (p?.disposition || {}) as { actions?: Array<{ action: string; weight: number }> };\n        const actions: Array<{ action: string; weight: number }> = Array.isArray(disp.actions) ? disp.actions : [];\n        if (!actions.length) return '';\n        const rows = actions.map((a: { action: string; weight: number }) => {"),

    ("function _personaFieldHtml(section: string, field: string, decl: *FIX*): { html: string; wide: boolean } {",
     "function _personaFieldHtml(section: string, field: string, decl: Record<string, unknown>): { html: string; wide: boolean } {"),

    ("const pd = (window as unknown as { InspectorPaperdoll?: *FIX* }).InspectorPaperdoll;\n        const playerConditions = ((worldState.players || {})[_state?.charName || '']?.conditions || {}) as Record<string, unknown>;\n        if (regionId && pd?.renderPaperdollConditionOverlay) {\n            const injured = ((playerConditions.injured || []) as *FIX*[])\n                .filter((i: *FIX*) => i.body_part === regionId);\n            const bleeding = ((playerConditions.bleeding || []) as *FIX*[])\n                .filter((i: *FIX*) => i.body_part === regionId);\n            const missing = ((playerConditions.missing || []) as *FIX*[])\n                .filter((i: *FIX*) => i.body_part === regionId);\n            if (injured.length) chips.push(`<span style=\"color:var(--yellow);\">🤕 Lv${Math.max(...injured.map((i: *FIX*) => i.level || 1))}</span>`);",
     "const pd = (window as unknown as { InspectorPaperdoll?: { renderPaperdollConditionOverlay?: Function; renderPaperdollFigureHtml?: Function; areasForFacing?: Function } }).InspectorPaperdoll;\n        const playerConditions = ((worldState.players || {})[_state?.charName || '']?.conditions || {}) as Record<string, unknown>;\n        if (regionId && pd?.renderPaperdollConditionOverlay) {\n            const injured = ((playerConditions.injured || []) as Array<{ body_part?: string; level?: number }>)\n                .filter((i: { body_part?: string }) => i.body_part === regionId);\n            const bleeding = ((playerConditions.bleeding || []) as Array<{ body_part?: string }>)\n                .filter((i: { body_part?: string }) => i.body_part === regionId);\n            const missing = ((playerConditions.missing || []) as Array<{ body_part?: string }>)\n                .filter((i: { body_part?: string }) => i.body_part === regionId);\n            if (injured.length) chips.push(`<span style=\"color:var(--yellow);\">🤕 Lv${Math.max(...injured.map((i: { level?: number }) => i.level || 1))}</span>`);"),

    ("const pd = (window as unknown as { InspectorPaperdoll?: *FIX* }).InspectorPaperdoll;",
     "const pd = (window as unknown as { InspectorPaperdoll?: { renderPaperdollConditionOverlay?: Function; renderPaperdollFigureHtml?: Function; areasForFacing?: Function } }).InspectorPaperdoll;"),

    ("""        const sel = _state.persona.bodyNav || null;
        const facing = _state.persona.dollFacing === 'back' ? 'back' : 'front';
        const doll = pane.querySelector('#mind-persona-doll');
        if (doll && pd?.renderPaperdollFigureHtml) {
            const player = (worldState.players || {})[_state?.charName || ''];
            doll.*FIX*= pd.renderPaperdollFigureHtml(
                _state?.charName || '', player || {}, esc,
                _state?.escName || '', { mode: 'navigate', selectedArea: sel, facing });
        }
        pane.querySelectorAll('[data-doll-facing]').forEach((btn) => {
            const face = (btn as HTMLElement).dataset.dollFacing;
            btn.classList.toggle('on', face === facing);
        });
        const nav = pane.querySelector('#mind-persona-bodynav');
        if (nav) {
            nav.*FIX*= sel
                ? _bodyNavSideHtml(sel)
                : `<div style="font-size:11px;color:var(--text-muted);">pick a bodypart on the doll - live status, sheet summary, sensitivity, markings. Arrows move · F/B flip · Esc clears.</div>`;
            _wireBodyNavJumps(pane);
            _wireBodyNavSliders(pane);
            _wireBodyNavMarks(pane);
        }""",
     """        const sel = _state.persona.bodyNav || null;
        const facing = _state.persona.dollFacing === 'back' ? 'back' : 'front';
        const doll = pane.querySelector('#mind-persona-doll');
        if (doll && pd?.renderPaperdollFigureHtml) {
            const player = (worldState.players || {})[_state?.charName || ''];
            window.Lit.render(window.Lit.unsafeHTML(pd.renderPaperdollFigureHtml(
                _state?.charName || '', player || {}, esc,
                _state?.escName || '', { mode: 'navigate', selectedArea: sel, facing })), doll);
        }
        pane.querySelectorAll('[data-doll-facing]').forEach((btn) => {
            const face = (btn as HTMLElement).dataset.dollFacing;
            btn.classList.toggle('on', face === facing);
        });
        const nav = pane.querySelector('#mind-persona-bodynav');
        if (nav) {
            window.Lit.render(window.Lit.unsafeHTML(sel
                ? _bodyNavSideHtml(sel)
                : `<div style="font-size:11px;color:var(--text-muted);">pick a bodypart on the doll - live status, sheet summary, sensitivity, markings. Arrows move · F/B flip · Esc clears.</div>`), nav);
            _wireBodyNavJumps(pane);
            _wireBodyNavSliders(pane);
            _wireBodyNavMarks(pane);
        }"""),

    ("const props = (p.schema?.properties || {}) as Record<string, *FIX*>;",
     "const props = (p.schema?.properties || {}) as Record<string, Record<string, unknown>>;"),

    ("open the fold and type - the compiled entry appears here without storing *FIX*thing.",
     "open the fold and type - the compiled entry appears here without storing anything."),

    ("// A dirty sheet lives only in the DOM (inputs write nowhere else). *FIX*",
     "// A dirty sheet lives only in the DOM (inputs write nowhere else). Any"),

    ("if (el) { el.*FIX*= _personaHtml(); _wirePersona(); }",
     "if (el) { window.Lit.render(window.Lit.unsafeHTML(_personaHtml()), el); _wirePersona(); }"),

    (".then((data: *FIX*) => {",
     ".then((data: { record?: Record<string, unknown>; schema?: Record<string, unknown>; hints?: Record<string, string>; suggestions?: Record<string, string[]>; lifecycle?: Record<string, unknown> }) => {"),

    ("function _collectPersona(): Record<string, *FIX*> {\n        const out: Record<string, *FIX*> = {};",
     "function _collectPersona(): Record<string, unknown> {\n        const out: Record<string, unknown> = {};"),

    ("cursor = cursor[parts[i]] as Record<string, *FIX*>;",
     "cursor = cursor[parts[i]] as Record<string, unknown>;"),

    ("}).then(r => r.json().then((data: *FIX*) => ({ ok: r.ok, data })))\n            .then(({ ok, data }: *FIX*) => {",
     "}).then(r => r.json().then((data: Record<string, unknown>) => ({ ok: r.ok, data })))\n            .then(({ ok, data }: { ok: boolean; data: Record<string, unknown> }) => {"),

    ("function _shortErr(data: *FIX*): string {",
     "function _shortErr(data: Record<string, unknown>): string {"),

    ("if (box) box.*FIX*= _personaStatesHtml();",
     "if (box) window.Lit.render(window.Lit.unsafeHTML(_personaStatesHtml()), box);"),

    ("box.*FIX*= `<span style=\"color:var(--text-muted);\">empty sheet - nothing to project.</span>`;",
     "window.Lit.render(window.Lit.unsafeHTML('<span style=\"color:var(--text-muted);\">empty sheet - nothing to project.</span>'), box);"),

    ("""        }).then(r => r.json().then((data: *FIX*) => ({ ok: r.ok, data })))
            .then(({ ok, data }: *FIX*) => {
                const live = _container?.querySelector('#mind-persona-codex');
                if (!live) return;
                if (!ok) {
                    live.*FIX*= `<span style="color:#e08a92;">cannot project: ${esc(data.error || 'rejected')}</span>`;
                    return;
                }
                const c = data.compiled || {};
                live.*FIX*= `${c.base_description ? `<div style="margin-bottom:6px;">${esc(c.base_description)}</div>` : ''}
                    ${c.personality ? `<div style="color:var(--text-dim);">${esc(c.personality)}</div>` : ''}
                    ${(c.interest_tags?.length || c.fear_tags?.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">drawn to ${(c.interest_tags || []).map(esc).join(', ') || '-'} · fears ${(c.fear_tags || []).map(esc).join(', ') || '-'}</div>` : ''}`;
            })""",
     """        }).then(r => r.json().then((data: Record<string, unknown>) => ({ ok: r.ok, data })))
            .then(({ ok, data }: { ok: boolean; data: { error?: string; compiled?: { base_description?: string; personality?: string; interest_tags?: string[]; fear_tags?: string[] } } }) => {
                const live = _container?.querySelector('#mind-persona-codex');
                if (!live) return;
                if (!ok) {
                    window.Lit.render(window.Lit.unsafeHTML(`<span style="color:#e08a92;">cannot project: ${esc(data.error || 'rejected')}</span>`), live);
                    return;
                }
                const c = data.compiled || {};
                window.Lit.render(window.Lit.unsafeHTML(`${c.base_description ? `<div style="margin-bottom:6px;">${esc(c.base_description)}</div>` : ''}
                    ${c.personality ? `<div style="color:var(--text-dim);">${esc(c.personality)}</div>` : ''}
                    ${(c.interest_tags?.length || c.fear_tags?.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">drawn to ${(c.interest_tags || []).map(esc).join(', ') || '-'} · fears ${(c.fear_tags || []).map(esc).join(', ') || '-'}</div>` : ''}`), live);
            })"""),

    ("const CI = (window as unknown as { CharacterImport?: *FIX* }).CharacterImport;\n        const llm = (window as unknown as { llmClient?: *FIX* }).llmClient;",
     "const CI = (window as unknown as { CharacterImport?: unknown }).CharacterImport;\n        const llm = (window as unknown as { llmClient?: unknown }).llmClient;"),

    ("const selected = all.find((m: *FIX*) => m.id === _state!.selectedId) || null;",
     "const selected = all.find((m: Models.MemoryRecord) => m.id === _state!.selectedId) || null;"),

    ("? visible.slice().reverse().map((m: *FIX*) => _cardHtml(m)).join('')",
     "? visible.slice().reverse().map((m: Models.MemoryRecord) => _cardHtml(m)).join('')"),

    ("""        if ((window as *FIX*).Lit?.render && (window as *FIX*).Lit?.unsafeHTML) {
            (window as *FIX*).Lit.render((window as *FIX*).Lit.unsafeHTML(modalContent), _container);
        } else {
            _container.*FIX*= modalContent;
        }""",
     """        window.Lit.render(window.Lit.unsafeHTML(modalContent), _container);"""),

    ("const IM: *FIX* = (window as *FIX*).InspectorMemory;",
     "const IM = (window as unknown as { InspectorMemory?: { renderEmotionControls: Function; wireEmotionControls: Function } }).InspectorMemory;"),

    ("const payload: *FIX* = { memory_emotions: emotions };",
     "const payload: Record<string, unknown> = { memory_emotions: emotions };"),

    ("goalsBox.addEventListener('click', (ev: *FIX*) => {",
     "goalsBox.addEventListener('click', (ev: MouseEvent) => {"),

    ("const TM: *FIX* = (window as unknown as { TagMultiselect?: unknown }).TagMultiselect;\n        const migPlayer: *FIX* = _state ? worldState.players?.[_state.charName] : null;\n        if (TM && migPlayer) {\n            const iSlot = _container.querySelector('#mind-interest-tags-slot');\n            if (iSlot) {\n                TM.render(iSlot, {\n                    selected: migPlayer.interest_tags || [],\n                    catalogType: 'tags',\n                    placeholder: 'Type an interest tag and press Enter...',\n                    onChange: (tags: *FIX*[]) => { ApiClient.updateCharacter(_state!.charName, { interest_tags: tags }).then(() => worldState.fetch()); }\n                });\n            }\n            const fSlot = _container.querySelector('#mind-fear-tags-slot');\n            if (fSlot) {\n                TM.render(fSlot, {\n                    selected: migPlayer.fear_tags || [],\n                    catalogType: 'tags',\n                    placeholder: 'Type a fear tag and press Enter...',\n                    onChange: (tags: *FIX*[]) => { ApiClient.updateCharacter(_state!.charName, { fear_tags: tags }).then(() => worldState.fetch()); }\n                });\n            }\n        }\n        const KB: *FIX* = (window as unknown as { KnownBySection?: unknown }).KnownBySection;",
     "const TM = (window as unknown as { TagMultiselect?: { render: Function } }).TagMultiselect;\n        const migPlayer: Models.PlayerRuntimeModel | null = _state ? worldState.players?.[_state.charName] : null;\n        if (TM && migPlayer) {\n            const iSlot = _container.querySelector('#mind-interest-tags-slot');\n            if (iSlot) {\n                TM.render(iSlot, {\n                    selected: migPlayer.interest_tags || [],\n                    catalogType: 'tags',\n                    placeholder: 'Type an interest tag and press Enter...',\n                    onChange: (tags: string[]) => { ApiClient.updateCharacter(_state!.charName, { interest_tags: tags }).then(() => worldState.fetch()); }\n                });\n            }\n            const fSlot = _container.querySelector('#mind-fear-tags-slot');\n            if (fSlot) {\n                TM.render(fSlot, {\n                    selected: migPlayer.fear_tags || [],\n                    catalogType: 'tags',\n                    placeholder: 'Type a fear tag and press Enter...',\n                    onChange: (tags: string[]) => { ApiClient.updateCharacter(_state!.charName, { fear_tags: tags }).then(() => worldState.fetch()); }\n                });\n            }\n        }\n        const KB = (window as unknown as { KnownBySection?: { build: Function } }).KnownBySection;"),

    ("const AV: *FIX* = (window as unknown as { InspectorAgentView?: unknown }).InspectorAgentView;",
     "const AV = (window as unknown as { InspectorAgentView?: { _deferredGravityControl: Function; _deferredAliasesSection: Function } }).InspectorAgentView;"),

    ("const rawBirth = _state.persona?.lifecycle?.birth_tick ?? (worldState.players?.[_state.charName] as *FIX*)?.birth_tick;",
     "const rawBirth = _state.persona?.lifecycle?.birth_tick ?? (worldState.players?.[_state.charName] as Record<string, unknown>)?.birth_tick;"),

    ("""                    if (list) list.*FIX*= (_visible(all2).length
                        ? _visible(all2).slice().reverse().map((m: *FIX*) => _cardHtml(m)).join('')
                        : `<div style="font-size:11px;color:var(--text-muted);padding:8px 0;">nothing matches this view.</div>`);""",
     """                    if (list) window.Lit.render(window.Lit.unsafeHTML(_visible(all2).length
                        ? _visible(all2).slice().reverse().map((m: Models.MemoryRecord) => _cardHtml(m)).join('')
                        : `<div style="font-size:11px;color:var(--text-muted);padding:8px 0;">nothing matches this view.</div>`), list);"""),

    ("if (el) el.*FIX*= _peopleHtml();\n            })\n            .catch(() => {\n                if (!_state) return;\n                _state.peopleStatus = 'error';\n                const el = _container?.querySelector('#mind-people');\n                if (el) el.*FIX*= _peopleHtml();",
     "if (el) window.Lit.render(window.Lit.unsafeHTML(_peopleHtml()), el);\n            })\n            .catch(() => {\n                if (!_state) return;\n                _state.peopleStatus = 'error';\n                const el = _container?.querySelector('#mind-people');\n                if (el) window.Lit.render(window.Lit.unsafeHTML(_peopleHtml()), el);"),

    ("const base = (window as *FIX*).InspectorView ? new (window as *FIX*).InspectorView() : {};",
     "const base: Record<string, unknown> = (window as unknown as { InspectorView?: new () => Record<string, unknown> }).InspectorView ? new ((window as unknown as { InspectorView: new () => Record<string, unknown> }).InspectorView)() : {};")
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
