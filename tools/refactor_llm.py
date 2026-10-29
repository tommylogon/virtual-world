import re

# 1. llm-client.ts was already written and clean

# 2. llm-bench.ts
p = 'static/js/llm-bench.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')

txt = txt.replace('let panel: *FIX* = null;', 'let panel: HTMLElement | null = null;')
txt = txt.replace('let toggleBtn: *FIX* = null;', 'let toggleBtn: HTMLElement | null = null;')
txt = txt.replace('let runs: *FIX*[] = [];', 'let runs: Array<Record<string, unknown>> = [];')
txt = txt.replace('function $ (sel: *FIX*, root: *FIX* = document) { return root.querySelector(sel); }', 'function $ (sel: string, root: ParentNode = document): HTMLElement | null { return root.querySelector(sel); }')
txt = txt.replace('function $$ (sel: *FIX*, root: *FIX* = document) { return [...root.querySelectorAll(sel)]; }', 'function $$ (sel: string, root: ParentNode = document): HTMLElement[] { return [...root.querySelectorAll(sel)] as HTMLElement[]; }')
txt = txt.replace('function el (tag: *FIX*, cls?: *FIX*, html?: *FIX*) {', 'function el (tag: string, cls?: string, html?: string) {')
txt = txt.replace('if (html !== undefined) e.*FIX*= html;', 'if (html !== undefined) window.Lit.render(window.Lit.unsafeHTML(html), e);')
txt = txt.replace('function esc (s: *FIX*) {', 'function esc (s: unknown) {')
txt = txt.replace('panel.*FIX*= `', 'window.Lit.render(window.Lit.unsafeHTML(`')
txt = txt.replace('`;\n  document.body.appendChild(panel);', '`), panel);\n  document.body.appendChild(panel);')

txt = txt.replace("(e: *FIX*) => { if (e.key === 'Enter') addCustomModel(); };", "(e: KeyboardEvent) => { if (e.key === 'Enter') addCustomModel(); };")
txt = txt.replace("(e: *FIX*) => {", "(e: Event) => {")
txt = txt.replace("runs.sort((a: *FIX*, b: *FIX*) =>", "runs.sort((a: Record<string, unknown>, b: Record<string, unknown>) =>")
txt = txt.replace("async function saveRun (run: *FIX*) {", "async function saveRun (run: Record<string, unknown>) {")
txt = txt.replace("$('#llmb-drill').*FIX*= '';", "$('#llmb-drill')?.replaceChildren();")
txt = txt.replace("let abortCtrl: *FIX* = null;", "let abortCtrl: AbortController | null = null;")
txt = txt.replace(".map((m: *FIX*) => (m && m.id) ? String(m.id) : null)", ".map((m: Record<string, unknown>) => (m && m.id) ? String(m.id) : null)")
txt = txt.replace("container.*FIX*= '';", "container.replaceChildren();")
txt = txt.replace("const add = (id: *FIX*, prechecked: *FIX*) => {", "const add = (id: string, prechecked: boolean) => {")
txt = txt.replace('wrap.*FIX*= `<input type="checkbox"', 'window.Lit.render(window.Lit.unsafeHTML(`<input type="checkbox"')
txt = txt.replace('chip);`\n    container.appendChild(wrap);', 'chip);`), wrap);\n    container.appendChild(wrap);')
txt = txt.replace("models.forEach((m: *FIX*) => add(m, true));", "models.forEach((m: string) => add(m, true));")
txt = txt.replace('chip active);`\n    container.appendChild(wrap);', 'chip active);`), wrap);\n    container.appendChild(wrap);')
txt = txt.replace("sel.*FIX*= '<option value=\"\">-- select a character --</option>';", "window.Lit.render(window.Lit.unsafeHTML('<option value=\"\">-- select a character --</option>'), sel);")
txt = txt.replace("async function capturePrompt (charName: *FIX*) {", "async function capturePrompt (charName: string) {")
txt = txt.replace("function approxTokens (s: *FIX*) {", "function approxTokens (s: unknown) {")
txt = txt.replace("function validateFormat (output: *FIX*) {", "function validateFormat (output: string) {")

txt = txt.replace(
    'output.replace(keyRe, (_: *FIX*, k: *FIX*) => { (seen as *FIX*)[k] = ((seen as *FIX*)[k] || 0) + 1; });',
    'output.replace(keyRe, (_: string, k: string) => { (seen as Record<string, number>)[k] = ((seen as Record<string, number>)[k] || 0) + 1; return ""; });'
)
txt = txt.replace(
    'Object.entries(seen).forEach(([k, c]) => { if ((c as *FIX*) > 1) dup.add(k); });',
    'Object.entries(seen).forEach(([k, c]) => { if ((c as number) > 1) dup.add(k); });'
)

txt = txt.replace("function buildKnownSet (roomParts: *FIX*, player: *FIX*, currentArea: *FIX*) {", "function buildKnownSet (roomParts: unknown, player: unknown, currentArea: unknown) {")
txt = txt.replace("const add = (s: *FIX*) => { if (s) known.add(String(s).toLowerCase()); };", "const add = (s: unknown) => { if (s) known.add(String(s).toLowerCase()); };")
txt = txt.replace("let charNameOf = (p: *FIX*) => p && (p.name || p.id || '');", "let charNameOf = (p: { name?: string; id?: string } | null) => p && (p.name || p.id || '');")

txt = txt.replace(
    "function findHallucinations (output: *FIX*, parsed: *FIX*, roomParts: *FIX*, player: *FIX*, currentArea: *FIX*, charName: *FIX*) {",
    "function findHallucinations (output: string, parsed: Record<string, unknown>, roomParts: unknown, player: unknown, currentArea: unknown, charName: string) {"
)

# Common words set
txt = txt.replace("'some','*FIX*','all'", "'some','any','all'")
txt = txt.replace("'another','m*FIX*','much'", "'another','many','much'")
txt = txt.replace("'comp*FIX*','companies'", "'company','companies'")
txt = txt.replace("'*FIX*where','somewhere'", "'anywhere','somewhere'")

txt = txt.replace("catch (e: *FIX*) {", "catch (e: unknown) {")
txt = txt.replace("let firstChunk: *FIX* = null;", "let firstChunk: number | null = null;")
txt = txt.replace("onChunk: (chunk: *FIX*) => {", "onChunk: (chunk: string) => {")
txt = txt.replace("(error as *FIX*).message", "(error as Error).message")
txt = txt.replace("tbody.*FIX*= '';", "tbody.replaceChildren();")
txt = txt.replace("tr.*FIX*= `", "window.Lit.render(window.Lit.unsafeHTML(`")
txt = txt.replace("`;\n      tbody.appendChild(tr);", "`), tr);\n      tbody.appendChild(tr);")
txt = txt.replace("function showDrill (id: *FIX*) {", "function showDrill (id: string) {")
txt = txt.replace("const r = runs.find((x: *FIX*) => x.id === id);", "const r = runs.find((x: Record<string, unknown>) => x.id === id);")
txt = txt.replace("d.*FIX*= `", "window.Lit.render(window.Lit.unsafeHTML(`")
txt = txt.replace("`;\n    d.classList.add('open');", "`), d);\n    d.classList.add('open');")
txt = txt.replace("async function importRuns (file: *FIX*) {", "async function importRuns (file: File) {")

rem = txt.count('*FIX*')
print(f"Remaining in llm-bench.ts: {rem}")
if rem > 0:
    for i, l in enumerate(txt.splitlines()):
        if '*FIX*' in l:
            print(f"  {i+1}: {l.strip()[:100]}")
assert rem == 0, f"llm-bench.ts rem: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in llm-bench.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("llm-bench.ts clean!")
