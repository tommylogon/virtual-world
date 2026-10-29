import re

# 1. budget.ts & diff.ts (clean em-dashes)
for fname in ['budget.ts', 'diff.ts']:
    p = f'static/js/nl-editor/{fname}'
    txt = open(p, 'r', encoding='utf-8').read()
    txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
    assert '\u2014' not in txt and '—' not in txt
    open(p, 'w', encoding='utf-8', newline='').write(txt)
    print(f'{fname} em-dashes cleared.')

# 2. index.ts
p = 'static/js/nl-editor/index.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace("(window as unknown as { NLEditor: *FIX* }).NLEditor = (() => {",
                  "(window as unknown as { NLEditor: unknown }).NLEditor = (() => {")
txt = txt.replace("staging: *FIX*;", "staging: unknown;")
txt = txt.replace("router: *FIX*;", "router: unknown;")
txt = txt.replace("agent: *FIX*;", "agent: unknown;")
txt = txt.replace("ui: *FIX*;", "ui: unknown;")
txt = txt.replace("this.agent.onUpdate((event: string, data: *FIX*) => {",
                  "this.agent.onUpdate((event: string, data: unknown) => {")
txt = txt.replace("if (this.ui.chatList) this.ui.chatList.*FIX*= '';",
                  "if (this.ui.chatList) this.ui.chatList.replaceChildren();")
txt = txt.replace("let lastScenario: *FIX* = null;",
                  "let lastScenario: string | null = null;")
txt = txt.replace("worldState.on('update', (state: *FIX*) => {",
                  "worldState.on('update', (state: unknown) => {")
txt = txt.replace("(res.validation || []).map((v: *FIX*) => ({",
                  "(res.validation || []).map((v: { severity?: string; message?: string; rule?: string }) => ({")
assert '\u2014' not in txt and '—' not in txt
rem = txt.count('*FIX*')
assert rem == 0, f"Remaining in index.ts: {rem}"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("index.ts 100% clean!")

# 3. staging.ts
p = 'static/js/nl-editor/staging.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = re.sub(r'Promise<\*FIX\*>;', 'Promise<unknown>;', txt)
txt = txt.replace("let batch: *FIX*;",
                  "let batch: { errors?: Array<{ message?: string; error?: string }>; results?: unknown[] } | null = null;")
txt = txt.replace(".map((er: *FIX*) => er.message || er.error || String(er))",
                  ".map((er: { message?: string; error?: string }) => er.message || er.error || String(er))")
txt = txt.replace("const errs = (batch.errors || []).map((er: *FIX*) => {",
                  "const errs = (batch.errors || []).map((er: { message?: string; error?: string }) => {")
txt = txt.replace("_nodePatch(patch: Record<string, *FIX*>): Record<string, *FIX*> {",
                  "_nodePatch(patch: Record<string, unknown>): Record<string, unknown> {")
txt = txt.replace("const rest: Record<string, *FIX*> = { ...patch };",
                  "const rest: Record<string, unknown> = { ...patch };")
txt = txt.replace("const out: Record<string, *FIX*> = {};",
                  "const out: Record<string, unknown> = {};")
txt = txt.replace("type StagedOpPayload = Record<string, *FIX*>;",
                  "type StagedOpPayload = Record<string, unknown>;")
assert '\u2014' not in txt and '—' not in txt
rem = txt.count('*FIX*')
assert rem == 0, f"Remaining in staging.ts: {rem}"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("staging.ts 100% clean!")
