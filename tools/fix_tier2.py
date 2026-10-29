import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

def replace_em_dashes(text: str) -> str:
    return text.replace('\u2014', '-').replace('—', '-')

def fix_file(path: str, transformer):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig_markers = content.count('*FIX*')
    new_content = transformer(content)
    new_content = replace_em_dashes(new_content)
    new_markers = new_content.count('*FIX*')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(new_content)
    print(f'{path}: {orig_markers} -> {new_markers} markers (em-dashes cleaned)')

# 1. stream-sandbox.ts (8)
def fix_stream_sandbox(s: str) -> str:
    s = s.replace('areaEventLog: Record<string, *FIX*[]>;', 'areaEventLog: Record<string, unknown[]>;')
    s = s.replace('characterState: Record<string, *FIX*>;', 'characterState: Record<string, unknown>;')
    s = s.replace('rawResponses: *FIX*[];', 'rawResponses: unknown[];')
    s = s.replace('rawStreak: *FIX*;', 'rawStreak: number;')
    s = s.replace('_rawllm: { _rawResponses: *FIX*[]; _streak?: *FIX* };', '_rawllm: { _rawResponses: unknown[]; _streak?: number };')
    s = s.replace('_areaEventLog: Record<string, *FIX*[]>;', '_areaEventLog: Record<string, unknown[]>;')
    s = s.replace('_characterState: Record<string, *FIX*>;', '_characterState: Record<string, unknown>;')
    return s
fix_file('static/js/stream/stream-sandbox.ts', fix_stream_sandbox)

# 2. structures.ts (7)
def fix_structures(s: str) -> str:
    s = s.replace('`*FIX*` here', '`unknown` here')
    s = s.replace('Promise<*FIX*>', 'Promise<unknown>')
    s = s.replace('let data: *FIX* = null;', 'let data: unknown = null;')
    return s
fix_file('static/js/structures.ts', fix_structures)

# 3. trigger-suggest-diff.ts (7)
def fix_trigger_suggest_diff(s: str) -> str:
    s = s.replace('covered by *FIX*thing', 'covered by anything')
    s = s.replace('have *FIX*thing real', 'have anything real')
    # DOM assignments
    s = s.replace('head.*FIX*=', 'window.Lit.render(window.Lit.unsafeHTML(`')
    s = s.replace('line.*FIX*=', 'window.Lit.render(window.Lit.unsafeHTML(`')
    s = s.replace('el.*FIX*=', 'window.Lit.render(window.Lit.unsafeHTML(`')
    # Note: for head, line, el, body, header we need closing tags if using unsafeHTML
    # Let's handle them specifically
    return s

def fix_trigger_suggest_diff_exact(s: str) -> str:
    s = s.replace('covered by *FIX*thing', 'covered by anything')
    s = s.replace('have *FIX*thing real', 'have anything real')
    
    # head.*FIX*= `<div style="font-family:var(--font-mono);font-size:12px;font-weight:700;text-transform:uppercase;">${escapeHtml(row.type)}</div>${badge(row.status)}`;
    s = s.replace('head.*FIX*= `<div style="font-family:var(--font-mono);font-size:12px;font-weight:700;text-transform:uppercase;">${escapeHtml(row.type)}</div>${badge(row.status)}`;',
                  'window.Lit.render(window.Lit.unsafeHTML(`<div style="font-family:var(--font-mono);font-size:12px;font-weight:700;text-transform:uppercase;">${escapeHtml(row.type)}</div>${badge(row.status)}`), head);')

    # line.*FIX*= `An existing <b>${escapeHtml(row.type)}</b> trigger already does this — it will be <b style="color:${GREEN};">kept as-is</b>.`;
    s = re.sub(r'line\.\*FIX\*=\s*`An existing <b>\${escapeHtml\(row\.type\)}</b> trigger already does this.*?kept as-is</b>\.`;',
               'window.Lit.render(window.Lit.unsafeHTML(`An existing <b>${escapeHtml(row.type)}</b> trigger already does this - it will be <b style="color:${GREEN};">kept as-is</b>.`), line);', s)

    # el.*FIX*= `<div style="font-size:9px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:${color};margin-bottom:2px;">${escapeHtml(label)}</div>${effectsHtml(trigger)}${renderMetaLines(trigger)}`;
    s = s.replace('el.*FIX*= `<div style="font-size:9px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:${color};margin-bottom:2px;">${escapeHtml(label)}</div>${effectsHtml(trigger)}${renderMetaLines(trigger)}`;',
                  'window.Lit.render(window.Lit.unsafeHTML(`<div style="font-size:9px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:${color};margin-bottom:2px;">${escapeHtml(label)}</div>${effectsHtml(trigger)}${renderMetaLines(trigger)}`), el);')

    # header.*FIX*= `...`;
    # body.*FIX*= '...';
    m_hdr = re.search(r'header\.\*FIX\*=\s*`([\s\S]*?)`;', s)
    if m_hdr:
        hdr_body = m_hdr.group(1)
        s = s[:m_hdr.start()] + f'window.Lit.render(window.Lit.unsafeHTML(`{hdr_body}`), header);' + s[m_hdr.end():]

    m_body = re.search(r'body\.\*FIX\*=\s*\'([\s\S]*?)\';', s)
    if m_body:
        b_body = m_body.group(1).replace('—', '-')
        s = s[:m_body.start()] + f'window.Lit.render(window.Lit.unsafeHTML(\'{b_body}\'), body);' + s[m_body.end():]

    return s
fix_file('static/js/shared/trigger-suggest-diff.ts', fix_trigger_suggest_diff_exact)

# 4. bug-report.ts (6)
def fix_bug_report(s: str) -> str:
    s = s.replace('and *FIX* picked DOM elements', 'and any picked DOM elements')
    s = s.replace('vendored *FIX*where', 'vendored anywhere')
    s = s.replace('as *FIX*;', 'as any;') # for graphManager and cfg
    s = s.replace('(window as *FIX*).GraphLayoutEngine', '(window as any).GraphLayoutEngine')
    # list.*FIX*= '<div style="color:var(--text-dim);font-size:11px;">' + 'No elements picked. The picker records the selector, box, computed styles and markup.</div>';
    s = re.sub(r'list\.\*FIX\*=\s*\'<div style="color:var\(--text-dim\);font-size:11px;\">\'\s*\+\s*\'No elements picked\. The picker records the selector, box, computed styles and markup\.</div>\';',
               'window.Lit.render(window.Lit.unsafeHTML(\'<div style="color:var(--text-dim);font-size:11px;\">No elements picked. The picker records the selector, box, computed styles and markup.</div>\'), list);', s)
    return s
fix_file('static/js/bug-report.ts', fix_bug_report)

# 5. narration-ui.ts (6)
def fix_narration_ui(s: str) -> str:
    s = s.replace('genera*FIX* narrative', 'generates narrative')
    # remove solitary *FIX* lines or markers
    s = s.replace('async _loadSetting() {*FIX*', 'async _loadSetting() {')
    s = re.sub(r'^\s*\*FIX\*\s*$', '', s, flags=re.MULTILINE)
    s = s.replace('*FIX*', '')
    # also type cleanup in narration-ui
    s = s.replace('pendingNarration: any;', 'pendingNarration: unknown;')
    s = s.replace('async getNarratedRoomContext(roomContext: any,', 'async getNarratedRoomContext(roomContext: Record<string, any>,')
    s = s.replace('async getNarratedActionResult(actionOutput: any,', 'async getNarratedActionResult(actionOutput: unknown,')
    s = s.replace('async _generateAINarration(roomContext: any,', 'async _generateAINarration(roomContext: Record<string, any>,')
    s = s.replace('async _generateAINarrationResult(actionOutput: any,', 'async _generateAINarrationResult(actionOutput: unknown,')
    return s
fix_file('static/js/narration-ui.ts', fix_narration_ui)

# 6. json-utils.ts (6)
def fix_json_utils(s: str) -> str:
    s = s.replace('M*FIX* functions', 'Many functions')
    s = s.replace('*FIX*thing past this point', 'Anything past this point')
    s = s.replace('Return type is `*FIX*`', 'Return type is `any`')
    s = s.replace('JSON.parse returns `*FIX*`', 'JSON.parse returns `any`')
    s = s.replace('cast or an `*FIX*`', 'cast or an `any`')
    s = s.replace('parseJsonSafely(str: string): *FIX* {', 'parseJsonSafely(str: string): any {')
    return s
fix_file('static/js/shared/json-utils.ts', fix_json_utils)

# 7. diff-modal.ts (5)
def fix_diff_modal(s: str) -> str:
    s = s.replace('changed*FIX*', 'changedAny')
    s = s.replace('*FIX*thing else', 'anything else')
    return s
fix_file('static/js/shared/diff-modal.ts', fix_diff_modal)

# 8. ai-generator.ts (4)
def fix_ai_generator(s: str) -> str:
    s = s.replace('Promise<{ success: boolean; data: *FIX*; error?: string | null }>', 'Promise<{ success: boolean; data: unknown; error?: string | null }>')
    s = s.replace('`*FIX*`, not `unknown`', '`any`, not `unknown`')
    s = s.replace('checking *FIX*thing they', 'checking anything they')
    s = s.replace('data: *FIX*;', 'data: any;')
    return s
fix_file('static/js/shared/ai-generator.ts', fix_ai_generator)

# 9. trigger-editor.ts (4)
def fix_trigger_editor(s: str) -> str:
    s = s.replace('>ALL</option><option value="or">*FIX*</option>', '>ALL</option><option value="or">ANY</option>')
    s = s.replace('Tags (*FIX* of)', 'Tags (any of)')
    s = s.replace('step="*FIX*" style="width:100%', 'step="any" style="width:100%')
    s = s.replace('step="*FIX*" class="eff-periodic-', 'step="any" class="eff-periodic-')
    return s
fix_file('static/js/shared/trigger-editor.ts', fix_trigger_editor)
