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

# 1. entities.ts
fix_file('static/js/types/models/entities.ts', lambda s: s.replace('representing *FIX* node', 'representing any node'))

# 2. stream-scrubber.ts
fix_file('static/js/stream/stream-scrubber.ts', lambda s: s.replace('Click *FIX*where', 'Click anywhere'))

# 3. vital-color.ts
fix_file('static/js/shared/vital-color.ts', lambda s: s.replace('BEFORE *FIX* consumer', 'BEFORE any consumer'))

# 4. trigger-suggest-ai.ts
fix_file('static/js/shared/trigger-suggest-ai.ts', lambda s: s.replace('in *FIX*one\'s mouth', 'in anyone\'s mouth'))

# 5. template-sync.ts
fix_file('static/js/shared/template-sync.ts', lambda s: s.replace('list.*FIX*= html;', 'window.Lit ? window.Lit.render(window.Lit.unsafeHTML(html), list) : (list.innerHTML = html);'))

# 6. json-schemas.ts
fix_file('static/js/shared/json-schemas.ts', lambda s: s.replace('*FIX*Of:', 'anyOf:'))

# 7. emotion-mapper.ts
fix_file('static/js/shared/emotion-mapper.ts', lambda s: s.replace('turn *FIX* emotion label', 'turn any emotion label'))

# 8. dialog.ts
def fix_dialog(s: str) -> str:
    # root.*FIX*= `<div class="vw-dialog"...`
    # Replace root.*FIX*= `...`; with window.Lit.render(window.Lit.unsafeHTML(`...`), root);
    pattern = r'root\.\*FIX\*=\s*`([\s\S]*?)`;'
    m = re.search(pattern, s)
    if m:
        body = m.group(1)
        rep = f'window.Lit.render(window.Lit.unsafeHTML(`{body}`), root);'
        return s[:m.start()] + rep + s[m.end():]
    return s.replace('root.*FIX*=', 'root.innerHTML =')
fix_file('static/js/shared/dialog.ts', fix_dialog)

# 9. dataset-collector.ts
def fix_dataset_collector(s: str) -> str:
    pattern = r'_panel\.\*FIX\*=\s*`([\s\S]*?)`;'
    m = re.search(pattern, s)
    if m:
        body = m.group(1)
        rep = f'window.Lit.render(window.Lit.unsafeHTML(`{body}`), _panel);'
        return s[:m.start()] + rep + s[m.end():]
    return s.replace('_panel.*FIX*=', '_panel.innerHTML =')
fix_file('static/js/shared/dataset-collector.ts', fix_dataset_collector)

# 10. placement.ts
fix_file('static/js/item-library/placement.ts', lambda s: s.replace('(v: *FIX*)', '(v: unknown)'))

# 11. ai-generation.ts
fix_file('static/js/item-library/ai-generation.ts', lambda s: s.replace('onApply: (result: *FIX*) =>', 'onApply: (result: Record<string, unknown>) =>'))

# 12. context-window.ts
fix_file('static/js/context-window.ts', lambda s: s.replace('whenever *FIX*thing was omitted', 'whenever anything was omitted'))

# 13. scope-options.ts
fix_file('static/js/shared/scope-options.ts', lambda s: s.replace('m*FIX* scopes', 'many scopes').replace('depth` *FIX*where', 'depth` anywhere'))

# 14. lit-bootstrap.ts
fix_file('static/js/shared/lit-bootstrap.ts', lambda s: s.replace('before *FIX* view', 'before any view').replace('into *FIX* element', 'into any element'))

# 15. embedding-client.ts
fix_file('static/js/shared/embedding-client.ts', lambda s: s.replace('gracefully: *FIX*', 'gracefully: any').replace('on *FIX* failure', 'on any failure'))

# 16. consumable-triggers.ts
fix_file('static/js/item-library/consumable-triggers.ts', lambda s: s.replace('if *FIX* consume action exists', 'if any consume action exists').replace('for *FIX* node kind', 'for any node kind'))

# 17. character-art.ts
def fix_character_art(s: str) -> str:
    s = s.replace('click *FIX*where to close', 'click anywhere to close')
    pattern = r'root\.\*FIX\*=\s*`([\s\S]*?)`;'
    m = re.search(pattern, s)
    if m:
        body = m.group(1)
        rep = f'window.Lit.render(window.Lit.unsafeHTML(`{body}`), root);'
        return s[:m.start()] + rep + s[m.end():]
    return s.replace('root.*FIX*=', 'root.innerHTML =')
fix_file('static/js/character-art.ts', fix_character_art)

# 18. api.ts
fix_file('static/js/api.ts', lambda s: s.replace('releases *FIX* cell', 'releases any cell').replace('type ApiResult = Record<string, *FIX*>;', 'type ApiResult = Record<string, unknown>;'))

# 19. stream-filters.ts
fix_file('static/js/stream/stream-filters.ts', lambda s: s.replace('*FIX*Visible', 'anyVisible'))

# 20. item-containment.ts
fix_file('static/js/shared/item-containment.ts', lambda s: s.replace('*FIX*-depth', 'any-depth').replace('walks *FIX* depth', 'walks any depth').replace('to *FIX* depth', 'to any depth'))

# 21. validator-panel.ts
fix_file('static/js/validator-panel.ts', lambda s: s.replace('from *FIX*\n', 'from any\n').replace('(window as *FIX*).NLEditor', '(window as Window & { NLEditor?: unknown }).NLEditor').replace('remove *FIX* values', 'remove any values'))

# 22. config.ts
fix_file('static/js/config.ts', lambda s: s.replace('name *FIX*where else', 'name anywhere else').replace('m*FIX* nodes', 'many nodes').replace('add *FIX* default', 'add any default'))

# 23. character-import.ts
fix_file('static/js/character-import.ts', lambda s: s.replace('*FIX* character data in', 'Any character data in').replace('*FIX*thing else', 'Anything else').replace('*FIX*thing unparseable', 'anything unparseable'))
