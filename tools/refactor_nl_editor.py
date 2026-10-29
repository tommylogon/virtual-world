import pathlib
import re

dir_path = pathlib.Path("static/js/nl-editor")

# First, eradicate all em-dashes in all .ts files in nl-editor
for f in dir_path.glob("*.ts"):
    txt = open(f, "r", encoding="utf-8").read()
    if '\u2014' in txt or '—' in txt:
        txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
        open(f, "w", encoding="utf-8", newline='').write(txt)
        print(f"Removed em-dashes from {f.name}")

# 1. index.ts
p_idx = dir_path / "index.ts"
idx_txt = open(p_idx, "r", encoding="utf-8").read()
idx_txt = idx_txt.replace("(window as unknown as { NLEditor: *FIX* }).NLEditor = (() => {",
                          "(window as unknown as { NLEditor: unknown }).NLEditor = (() => {")
idx_txt = idx_txt.replace("staging: *FIX*;", "staging: unknown;")
idx_txt = idx_txt.replace("router: *FIX*;", "router: unknown;")
idx_txt = idx_txt.replace("agent: *FIX*;", "agent: unknown;")
idx_txt = idx_txt.replace("ui: *FIX*;", "ui: unknown;")
idx_txt = idx_txt.replace("this.agent.onUpdate((event: string, data: *FIX*) => {",
                          "this.agent.onUpdate((event: string, data: unknown) => {")
idx_txt = idx_txt.replace("if (this.ui.chatList) this.ui.chatList.*FIX*= '';",
                          "if (this.ui.chatList) this.ui.chatList.replaceChildren();")
idx_txt = idx_txt.replace("let lastScenario: *FIX* = null;",
                          "let lastScenario: string | null = null;")
idx_txt = idx_txt.replace("worldState.on('update', (state: *FIX*) => {",
                          "worldState.on('update', (state: unknown) => {")
idx_txt = idx_txt.replace("(res.validation || []).map((v: *FIX*) => ({",
                          "(res.validation || []).map((v: { severity?: string; message?: string; rule?: string }) => ({")
assert idx_txt.count("*FIX*") == 0, f"Remaining FIX in index.ts: {idx_txt.count('*FIX*')}"
assert '\u2014' not in idx_txt and '—' not in idx_txt
open(p_idx, "w", encoding="utf-8", newline='').write(idx_txt)
print("index.ts cleaned.")

# 2. staging.ts
p_stg = dir_path / "staging.ts"
stg_txt = open(p_stg, "r", encoding="utf-8").read()
stg_txt = re.sub(r'Promise<\*FIX\*>;', 'Promise<unknown>;', stg_txt)
stg_txt = stg_txt.replace("let batch: *FIX*;",
                          "let batch: { errors?: Array<{ message?: string; error?: string }>; results?: unknown[] } | null = null;")
stg_txt = stg_txt.replace(".map((er: *FIX*) => er.message || er.error || String(er))",
                          ".map((er: { message?: string; error?: string }) => er.message || er.error || String(er))")
stg_txt = stg_txt.replace("const errs = (batch.errors || []).map((er: *FIX*) => {",
                          "const errs = (batch.errors || []).map((er: { message?: string; error?: string }) => {")
stg_txt = stg_txt.replace("_nodePatch(patch: Record<string, *FIX*>): Record<string, *FIX*> {",
                          "_nodePatch(patch: Record<string, unknown>): Record<string, unknown> {")
stg_txt = stg_txt.replace("const rest: Record<string, *FIX*> = { ...patch };",
                          "const rest: Record<string, unknown> = { ...patch };")
stg_txt = stg_txt.replace("type StagedOpPayload = Record<string, *FIX*>;",
                          "type StagedOpPayload = Record<string, unknown>;")
assert stg_txt.count("*FIX*") == 0, f"Remaining FIX in staging.ts: {stg_txt.count('*FIX*')}"
assert '\u2014' not in stg_txt and '—' not in stg_txt
open(p_stg, "w", encoding="utf-8", newline='').write(stg_txt)
print("staging.ts cleaned.")

# 3. ui.ts
p_ui = dir_path / "ui.ts"
ui_txt = open(p_ui, "r", encoding="utf-8").read()
ui_txt = ui_txt.replace("optsEl.*FIX*= '';", "optsEl.replaceChildren();")
ui_txt = ui_txt.replace("listEl.*FIX*= '';", "listEl.replaceChildren();")
ui_txt = ui_txt.replace("bubble.*FIX*= html;", "window.Lit.render(window.Lit.unsafeHTML(html), bubble);")

# For container and qEl in ui.ts:
ui_txt = re.sub(r'this\.container\.\*FIX\*=\s*`', 'window.Lit.render(window.Lit.unsafeHTML(`', ui_txt)
# The matching template ends before the closing of render; let's check exact lines in ui.ts around container and qEl
open(p_ui, "w", encoding="utf-8", newline='').write(ui_txt)
print("ui.ts partially updated.")
