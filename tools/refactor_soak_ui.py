import re

p = 'static/js/soak/soak-ui.ts'
txt = open(p, 'r', encoding='utf-8').read()

assert '\u2014' not in txt and '—' not in txt, "Em-dash in original soak-ui.ts"

replacements = [
    # Top & helpers
    ("const S = window.SoakState as *FIX*;",
     "const S = window.SoakState as unknown as Record<string, Function> & { selected: () => Record<string, unknown> | null; state: { meta?: { scenarios?: Array<{ path: string; name?: string }>; core_vitals?: string[] }; runs?: Array<{ id: string; label?: string; status?: string }> }; selectRun: (id: string | null) => Promise<void>; removeRun: (id: string | null) => Promise<void>; setConfig: (cfg: Record<string, unknown>) => void; fullSamples: (id: string) => Promise<Record<string, unknown>>; on: (cb: (t: string, p: unknown) => void) => void };"),

    ("const el = (id: string): *FIX* => document.getElementById(id);",
     "type SoakElement = HTMLElement & HTMLInputElement & HTMLSelectElement & { checked: boolean; value: string };\n    const el = (id: string): SoakElement | null => document.getElementById(id) as SoakElement | null;"),

    ("(container as HTMLElement).*FIX*= template;",
     "window.Lit.render(window.Lit.unsafeHTML(template), container);"),

    ("compareData: null as *FIX*,",
     "compareData: null as Record<string, unknown> | null,"),

    ("points: *FIX*[];\n        width: number;\n        area?: { lower: *FIX*[]; upper: *FIX*[] };",
     "points: Array<[number, number]>;\n        width: number;\n        area?: { lower: Array<[number, number]>; upper: Array<[number, number]> };"),

    ("function data(): *FIX* { return S.selected(); }\n    function meta(): *FIX* { return S.state.meta || {}; }\n    function scenarioInfo(path: string): *FIX* {\n        return (meta().scenarios || []).find((s: *FIX*) => s.path === path) || {};\n    }\n    function minutesPerTick(config: *FIX*): number {",
     "function data(): Record<string, unknown> | null { return S.selected(); }\n    function meta(): { scenarios?: Array<{ path: string; name?: string }>; core_vitals?: string[] } { return S.state.meta || {}; }\n    function scenarioInfo(path: string): { path?: string; name?: string } {\n        return (meta().scenarios || []).find((s: { path: string }) => s.path === path) || {};\n    }\n    function minutesPerTick(config: { minutes_per_tick?: number }): number {"),

    ("function gameSpan(ticks: number, config: *FIX*): string {",
     "function gameSpan(ticks: number, config: { minutes_per_tick?: number }): string {"),

    ("const options = (meta().scenarios || []).map((s: *FIX*) => {",
     "const options = (meta().scenarios || []).map((s: { path: string; name?: string }) => {"),

    ("function setForm(config: *FIX*): void {",
     "function setForm(config: Record<string, unknown>): void {"),

    ("function stringifyMap(value: *FIX*): string {",
     "function stringifyMap(value: unknown): string {"),

    ("function applyConfig(config: *FIX*): void {",
     "function applyConfig(config: Record<string, unknown>): void {"),

    ("box.querySelectorAll('[data-vital]').forEach((btn: *FIX*) => {",
     "box.querySelectorAll('[data-vital]').forEach((btn: Element) => {"),

    ("const presets = P.PRESETS.map((p: *FIX*) => htmlTag`<button type=\"button\" class=\"soak-preset\" data-preset=\"${p.id}\">",
     "const presets = P.PRESETS.map((p: { id: string; label: string; description?: string }) => htmlTag`<button type=\"button\" class=\"soak-preset\" data-preset=\"${p.id}\">"),

    ("box.querySelectorAll('[data-preset]').forEach((btn: *FIX*) => {\n            btn.addEventListener('click', () => {\n                const preset = P.PRESETS.find((p: *FIX*) => p.id === btn.getAttribute('data-preset'));",
     "box.querySelectorAll('[data-preset]').forEach((btn: Element) => {\n            btn.addEventListener('click', () => {\n                const preset = P.PRESETS.find((p: { id: string }) => p.id === btn.getAttribute('data-preset'));"),

    ("const savedItems = list.map((item: *FIX*, idx: number) => htmlTag`<div class=\"soak-saved\">",
     "const savedItems = list.map((item: { name?: string }, idx: number) => htmlTag`<div class=\"soak-saved\">"),

    ("""        box.querySelectorAll('[data-load]').forEach((node: *FIX*) => {
            node.addEventListener('click', () => {
                const item = P.loadSaved()[Number(node.getAttribute('data-load'))];
                if (item) { applyConfig(Object.assign({}, meta().defaults, item.config)); toast('Config loaded', 'info', 2000); }
            });
        });
        box.querySelectorAll('[data-del]').forEach((node: *FIX*) => {
            node.addEventListener('click', () => {
                P.removeSaved(Number(node.getAttribute('data-del')));
                renderSaved();
            });
        });""",
     """        box.querySelectorAll('[data-load]').forEach((node: Element) => {
            node.addEventListener('click', () => {
                const item = P.loadSaved()[Number(node.getAttribute('data-load'))];
                if (item) { applyConfig(Object.assign({}, meta().defaults, item.config)); toast('Config loaded', 'info', 2000); }
            });
        });
        box.querySelectorAll('[data-del]').forEach((node: Element) => {
            node.addEventListener('click', () => {
                P.removeSaved(Number(node.getAttribute('data-del')));
                renderSaved();
            });
        });"""),

    ("const runItems = runs.map((r: *FIX*) => {",
     "const runItems = runs.map((r: { id: string; label?: string; status?: string; ticks?: number }) => {"),

    ("""        box.querySelectorAll('[data-run]').forEach((node: *FIX*) => {
            node.addEventListener('click', (ev: *FIX*) => {
                if (ev.target.getAttribute('data-del')) return;
                S.selectRun(node.getAttribute('data-run')).catch((e: *FIX*) => toast(e.message, 'error'));
            });
        });
        box.querySelectorAll('[data-del]').forEach((node: *FIX*) => {
            node.addEventListener('click', async (ev: *FIX*) => {""",
     """        box.querySelectorAll('[data-run]').forEach((node: Element) => {
            node.addEventListener('click', (ev: Event) => {
                if ((ev.target as HTMLElement).getAttribute('data-del')) return;
                S.selectRun(node.getAttribute('data-run')).catch((e: { message: string }) => toast(e.message, 'error'));
            });
        });
        box.querySelectorAll('[data-del]').forEach((node: Element) => {
            node.addEventListener('click', async (ev: Event) => {"""),

    ("function samples(): *FIX*[] { const d = data(); return (d && d.samples) || []; }",
     "function samples(): Array<Record<string, unknown>> { const d = data(); return (d && (d.samples as Array<Record<string, unknown>>)) || []; }"),

    ("function vitalSeries(stat: string, mode: string): *FIX*[] {\n        return samples().map((s: *FIX*) => {",
     "function vitalSeries(stat: string, mode: string): Array<[number, number]> {\n        return samples().map((s: Record<string, unknown>) => {"),

    ("""    function vitalBand(stat: string): { lower: *FIX*[]; upper: *FIX*[] } {
        return {
            lower: samples().map((s: *FIX*) => [s.tick, ((s.vitals || {})[stat] || {}).min]),
            upper: samples().map((s: *FIX*) => [s.tick, ((s.vitals || {})[stat] || {}).max]),
        };
    }

    function survivalPoints(): *FIX*[] {
        const total = charactersCount() || 1;
        return samples().map((s: *FIX*) => [s.tick, (s.alive / total) * 100]);
    }""",
     """    function vitalBand(stat: string): { lower: Array<[number, number]>; upper: Array<[number, number]> } {
        return {
            lower: samples().map((s: Record<string, unknown>) => [s.tick as number, (((s.vitals as Record<string, Record<string, number>>) || {})[stat] || {}).min]),
            upper: samples().map((s: Record<string, unknown>) => [s.tick as number, (((s.vitals as Record<string, Record<string, number>>) || {})[stat] || {}).max]),
        };
    }

    function survivalPoints(): Array<[number, number]> {
        const total = charactersCount() || 1;
        return samples().map((s: Record<string, unknown>) => [s.tick as number, ((s.alive as number) / total) * 100]);
    }"""),

    ("((d && d.deaths) || []).forEach((x: *FIX*) => { counts[x.cause] = (counts[x.cause] || 0) + 1; });",
     "((d && (d.deaths as Array<{ cause: string }>)) || []).forEach((x: { cause: string }) => { counts[x.cause] = (counts[x.cause] || 0) + 1; });"),

    ("((d && d.deaths) || []).forEach((x: *FIX*) => { const k = x.area || 'unknown'; counts[k] = (counts[k] || 0) + 1; });",
     "((d && (d.deaths as Array<{ area?: string }>)) || []).forEach((x: { area?: string }) => { const k = x.area || 'unknown'; counts[k] = (counts[k] || 0) + 1; });"),

    ("const legendItems = series.map((s: *FIX*) => htmlTag`<span class=\"soak-legend-item\"><span class=\"soak-legend-swatch\" style=\"background:${s.color}\"></span>${s.name}</span>`);",
     "const legendItems = series.map((s: { color: string; name: string }) => htmlTag`<span class=\"soak-legend-item\"><span class=\"soak-legend-swatch\" style=\"background:${s.color}\"></span>${s.name}</span>`);"),

    ("const first = rows.find((s: *FIX*) => Object.keys(s.vitals || {}).length);\n        let last: *FIX* = null;",
     "const first = rows.find((s: Record<string, unknown>) => Object.keys(s.vitals || {}).length);\n        let last: Record<string, unknown> | null = null;"),

    ("function syncRangeInputs(payload: *FIX*): void {",
     "function syncRangeInputs(payload: { start?: number; end?: number }): void {"),

    ("let payload: *FIX*;",
     "let payload: Record<string, unknown> | null;"),

    ("deaths: solo ? deaths.filter((d: *FIX*) => d.name === ui.stCharacter) : deaths,",
     "deaths: solo ? deaths.filter((d: { name?: string }) => d.name === ui.stCharacter) : deaths,"),

    ("function renderSpaceTimeDensity(layout: *FIX*): void {",
     "function renderSpaceTimeDensity(layout: Record<string, unknown>): void {"),

    ("function renderSpaceTimeIntegrity(payload: *FIX*): void {",
     "function renderSpaceTimeIntegrity(payload: { runs?: Array<{ integrity?: Record<string, unknown> }> }): void {"),

    ("function renderSpaceTimeLegend(payload: *FIX*): void {",
     "function renderSpaceTimeLegend(payload: Record<string, unknown>): void {"),

    ("function renderCollisions(collisions: *FIX*): void {",
     "function renderCollisions(collisions: Array<{ area: string; ticks: number; pairs: Array<{ pair: string; ticks: number }> }>): void {"),

    ("""        const rows = collisions.map((row: *FIX*) => {
            const pairs = row.pairs.slice(0, 5)
                .map((p: *FIX*) => htmlTag`<div><button type="button" class="soak-link-btn" data-st-pair="${p.pair}">${p.pair}</button> <span class="soak-hint">${F.fmtInt(p.ticks)}t</span></div>`);""",
     """        const rows = collisions.map((row: { area: string; ticks: number; pairs: Array<{ pair: string; ticks: number }> }) => {
            const pairs = row.pairs.slice(0, 5)
                .map((p: { pair: string; ticks: number }) => htmlTag`<div><button type="button" class="soak-link-btn" data-st-pair="${p.pair}">${p.pair}</button> <span class="soak-hint">${F.fmtInt(p.ticks)}t</span></div>`);"""),

    ("async function renderWhy(payload: *FIX*, range: *FIX*, minutes: number): Promise<void> {",
     "async function renderWhy(payload: Record<string, unknown>, range: { from: number; to: number }, minutes: number): Promise<void> {"),

    ("""        const groups = why.map((row: *FIX*) => row.group);
        const total = why.reduce((sum: number, row: *FIX*) => sum + row.count, 0);
        const rows = why.map((row: *FIX*) => htmlTag`<tr><td>${row.group}</td><td class="soak-num">${F.fmtInt(row.count)}</td><td class="soak-num">${F.pct(row.share, 0)}</td></tr>`);""",
     """        const groups = why.map((row: { group: string }) => row.group);
        const total = why.reduce((sum: number, row: { count: number }) => sum + row.count, 0);
        const rows = why.map((row: { group: string; count: number; share: number }) => htmlTag`<tr><td>${row.group}</td><td class="soak-num">${F.fmtInt(row.count)}</td><td class="soak-num">${F.pct(row.share, 0)}</td></tr>`);"""),

    ("let stackEvents: *FIX*[] = [];",
     "let stackEvents: Array<Record<string, unknown>> = [];"),

    ("const legendItems = why.map((row: *FIX*) => htmlTag`<span class=\"soak-legend-item\"><i class=\"soak-legend-swatch\" style=\"background:${whyColor(row.group, groups)}\"></i>${row.group} · ${F.fmtInt(row.count)}</span>`);",
     "const legendItems = why.map((row: { group: string; count: number }) => htmlTag`<span class=\"soak-legend-item\"><i class=\"soak-legend-swatch\" style=\"background:${whyColor(row.group, groups)}\"></i>${row.group} · ${F.fmtInt(row.count)}</span>`);"),

    ("function renderKinds(payload: *FIX*) {",
     "function renderKinds(payload: Record<string, unknown>) {"),

    ("""        const slices = kinds.slice(0, 8).map((row: *FIX*, i: number) => ({
            label: row.kind, value: row.count, color: palette[i % palette.length],
        }));
        if (kinds.length > 8) {
            const rest = kinds.slice(8).reduce((sum: number, row: *FIX*) => sum + row.count, 0);
            slices.push({ label: `${kinds.length - 8} more`, value: rest, color: '#6e7681' });
        }
        renderLit(unsafeSvg(C.renderDonut({ slices, size: 190, thickness: 28, centerLabel: 'actions' })), box);
        if (legendBox) {
            const legendItems = kinds.slice(0, 8).map((row: *FIX*, i: number) => htmlTag`<span class="soak-legend-item"><i class="soak-legend-swatch" style="background:${palette[i % palette.length]}"></i>${row.kind} · ${F.fmtInt(row.count)}</span>`);""",
     """        const slices = kinds.slice(0, 8).map((row: { kind: string; count: number }, i: number) => ({
            label: row.kind, value: row.count, color: palette[i % palette.length],
        }));
        if (kinds.length > 8) {
            const rest = kinds.slice(8).reduce((sum: number, row: { count: number }) => sum + row.count, 0);
            slices.push({ label: `${kinds.length - 8} more`, value: rest, color: '#6e7681' });
        }
        renderLit(unsafeSvg(C.renderDonut({ slices, size: 190, thickness: 28, centerLabel: 'actions' })), box);
        if (legendBox) {
            const legendItems = kinds.slice(0, 8).map((row: { kind: string; count: number }, i: number) => htmlTag`<span class="soak-legend-item"><i class="soak-legend-swatch" style="background:${palette[i % palette.length]}"></i>${row.kind} · ${F.fmtInt(row.count)}</span>`);"""),

    ("const deathTicks = ((data() && data().deaths) || []).map((d: *FIX*) => d.tick);",
     "const deathTicks = ((data() && (data()!.deaths as Array<{ tick: number }>)) || []).map((d: { tick: number }) => d.tick);"),

    ("const deaths = (d.deaths || []).filter((x: *FIX*) => {",
     "const deaths = (d.deaths || []).filter((x: { name?: string; cause?: string; area?: string; tick?: number; tags?: string[] }) => {"),

    ("const rows = deaths.map((x: *FIX*) => htmlTag`<tr>",
     "const rows = deaths.map((x: { name?: string; cause?: string; area?: string; tick?: number; tags?: string[] }) => htmlTag`<tr>"),

    ("<td>${(x.tags || []).slice(0, 4).map((t: *FIX*) => htmlTag`<span class=\"soak-tag\">${t}</span>`)}</td>",
     "<td>${(x.tags || []).slice(0, 4).map((t: string) => htmlTag`<span class=\"soak-tag\">${t}</span>`)}</td>"),

    ("box.querySelectorAll('[data-metric]').forEach((btn: *FIX*) => {",
     "box.querySelectorAll('[data-metric]').forEach((btn: Element) => {"),

    ("const a: *FIX* = firstGrowth[k]; const b: *FIX* = finalGrowth[k];",
     "const a: unknown = firstGrowth[k]; const b: unknown = finalGrowth[k];"),

    ("let rows = chars.filter((c: *FIX*) => {",
     "let rows = chars.filter((c: { name: string; vitals?: Record<string, number>; tags?: string[] }) => {"),

    ("rows.sort((a: *FIX*, b: *FIX*) => {",
     "rows.sort((a: Record<string, unknown>, b: Record<string, unknown>) => {"),

    ("const charRows = rows.map((c: *FIX*) => {",
     "const charRows = rows.map((c: { name: string; vitals?: Record<string, number>; tags?: string[] }) => {"),

    ("<td>${(c.tags || []).slice(0, 3).map((t: *FIX*) => htmlTag`<span class=\"soak-tag\">${t}</span>`)}</td>",
     "<td>${(c.tags || []).slice(0, 3).map((t: string) => htmlTag`<span class=\"soak-tag\">${t}</span>`)}</td>"),

    ("tableBox.querySelectorAll('[data-char]').forEach((row: *FIX*) => {",
     "tableBox.querySelectorAll('[data-char]').forEach((row: Element) => {"),

    ("points: series.series[m].map((y: *FIX*, idx: number) => [series.ticks[idx], y]),",
     "points: series.series[m].map((y: number, idx: number) => [series.ticks[idx], y]),"),

    ("const char = ((data() && data().characters) || []).find((c: *FIX*) => c.name === name);",
     "const char = ((data() && (data()!.characters as Array<{ name: string; vitals?: Record<string, number> }>)) || []).find((c: { name: string }) => c.name === name);"),

    ("box.querySelectorAll('[data-kind]').forEach((btn: *FIX*) => {",
     "box.querySelectorAll('[data-kind]').forEach((btn: Element) => {"),

    ("const filtered = all.filter((e: *FIX*) => {",
     "const filtered = all.filter((e: { kind?: string; message?: string; tick?: number }) => {"),

    ("const eventRows = filtered.slice(-500).map((e: *FIX*) => htmlTag`<div class=\"soak-event soak-event-${e.kind}\">",
     "const eventRows = filtered.slice(-500).map((e: { kind?: string; message?: string; tick?: number }) => htmlTag`<div class=\"soak-event soak-event-${e.kind}\">"),

    ("const opts = runs.map((r: *FIX*) => htmlTag`<option value=\"${r.id}\">${r.label} (${r.status})</option>`);",
     "const opts = runs.map((r: { id: string; label?: string; status?: string }) => htmlTag`<option value=\"${r.id}\">${r.label} (${r.status})</option>`);"),

    ("""        const toSeries = (body: *FIX*, color: string, dash?: string) => ({
            name: (body.summary && body.summary.scenario_name) || 'run',
            color: color, dash: dash,
            points: (body.samples || []).map((s: *FIX*) => [s.tick, (((s.vitals || {})[metric]) || {}).avg]),
        });""",
     """        const toSeries = (body: { summary?: { scenario_name?: string }; samples?: Array<{ tick: number; vitals?: Record<string, { avg?: number }> }> }, color: string, dash?: string) => ({
            name: (body.summary && body.summary.scenario_name) || 'run',
            color: color, dash: dash,
            points: (body.samples || []).map((s: { tick: number; vitals?: Record<string, { avg?: number }> }) => [s.tick, (((s.vitals || {})[metric]) || {}).avg]),
        });"""),

    ("""        const runsById: Record<string, *FIX*> = {};
        (S.state.runs || []).forEach((r: *FIX*) => { runsById[r.id] = r; });""",
     """        const runsById: Record<string, { id: string; label?: string; status?: string }> = {};
        (S.state.runs || []).forEach((r: { id: string; label?: string; status?: string }) => { runsById[r.id] = r; });"""),

    ("const getVal = (body: *FIX*, id: string, field: string) => {",
     "const getVal = (body: Record<string, unknown>, id: string, field: string) => {"),

    ("function buildCli(config: *FIX*) {",
     "function buildCli(config: Record<string, unknown>) {"),

    ("S.on((type: string, payload: *FIX*) => {",
     "S.on((type: string, payload: unknown) => {"),

    ("""const deaths = events.filter((e: *FIX*) => e.kind === 'death');
                deaths.forEach((e: *FIX*) => toast(e.message, 'warn', 5000));""",
     """const deaths = events.filter((e: { kind?: string; message?: string }) => e.kind === 'death');
                deaths.forEach((e: { message?: string }) => toast(e.message || '', 'warn', 5000));""")
]

applied = 0
for src, dst in replacements:
    if src in txt:
        txt = txt.replace(src, dst)
        applied += 1
    else:
        print(f"FAILED TO FIND:\n{src[:80]}...")

# Clean remaining comments
txt = txt.replace("`*FIX*` is the honest annotation", "`any` is the honest annotation")
txt = txt.replace("`globals.d.ts` declares `SoakSpacetime` as `*FIX*`", "`globals.d.ts` declares `SoakSpacetime` as `any`")
txt = txt.replace("rather than letting `*FIX*` propagate", "rather than letting `any` propagate")

print(f"Applied {applied}/{len(replacements)} replacements.")
rem = txt.count('*FIX*')
print(f"Remaining in soak-ui.ts: {rem}")
assert rem == 0, f"Remaining in soak-ui.ts: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in soak-ui.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("soak-ui.ts 100% clean!")
