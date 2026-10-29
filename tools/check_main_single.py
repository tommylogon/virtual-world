with open('static/js/main.ts', 'r', encoding='utf-8') as f:
    txt = f.read()

txt = txt.replace('\u2014', ' - ').replace('—', ' - ')

txt = txt.replace('so *FIX* module that tests', 'so any module that tests')
txt = txt.replace('designers can set *FIX* state', 'designers can set any state')
txt = txt.replace('before *FIX*thing that renders', 'before anything that renders')
txt = txt.replace('// Reflect *FIX* graph change', '// Reflect any graph change')

txt = txt.replace('(window as *FIX*).gridModel', '(window as unknown as { gridModel?: unknown }).gridModel')
txt = txt.replace('(window as *FIX*).worldPainter', '(window as unknown as { worldPainter?: unknown }).worldPainter')
txt = txt.replace('(window as *FIX*).structures', '(window as unknown as { structures?: unknown }).structures')
txt = txt.replace('const win = window as *FIX*;', 'const win = window as unknown as Record<string, unknown>;')
txt = txt.replace('.then((res: *FIX*) =>', '.then((res: unknown) =>')
txt = txt.replace('openCreateModal(\'area\', async (data: *FIX*) =>', 'openCreateModal(\'area\', async (data: unknown) =>')
txt = txt.replace('openCreateModal(\'item\', async (data: *FIX*) =>', 'openCreateModal(\'item\', async (data: unknown) =>')
txt = txt.replace('openCreateModal(\'connection\', async (data: *FIX*) =>', 'openCreateModal(\'connection\', async (data: unknown) =>')
txt = txt.replace('function connectSummary(res: *FIX*, payload: *FIX*) {', 'function connectSummary(res: unknown, payload: unknown) {')
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
txt = txt.replace('(config as *FIX*)', '(config as unknown as Record<string, Function>)')
txt = txt.replace('(ApiClient as *FIX*)', '(ApiClient as unknown as Record<string, Function>)')
txt = txt.replace('([name, r]: [string, *FIX*])', '([name, r]: [string, unknown])')
txt = txt.replace('([n, r]: [string, *FIX*])', '([n, r]: [string, unknown])')
txt = txt.replace('const set = (id: string, val: *FIX*) =>', 'const set = (id: string, val: unknown) =>')
txt = txt.replace('(window as *FIX*).CreateModal', '(window as unknown as { CreateModal?: { _tagMSArea?: { setValue: Function }; _tagMSConn?: { setValue: Function } } }).CreateModal')
txt = txt.replace('catch (err: *FIX*) {', 'catch (err: unknown) {')
txt = txt.replace('catch(e: *FIX*) {', 'catch(e: unknown) {')
txt = txt.replace('(onSubmit: (data: *FIX*) => void)', '(onSubmit: (data: unknown) => void)')
txt = txt.replace('catch((err: *FIX*) =>', 'catch((err: { message?: string } | null) =>')
txt = txt.replace('.action(cmd).then((data: *FIX*) =>', '.action(cmd).then((data: unknown) =>')
txt = txt.replace('.playerSpeak(speakerName, text, areaName).then((res: *FIX*) =>', '.playerSpeak(speakerName, text, areaName).then((res: unknown) =>')
txt = txt.replace('(window as *FIX*).VWSimultaneousControls', '(window as unknown as { VWSimultaneousControls?: { init(): void; render(): void } }).VWSimultaneousControls')
txt = txt.replace('worldState.on(\'update\', (state: *FIX*) => {', 'worldState.on(\'update\', (state: unknown) => {')
txt = txt.replace('(window as *FIX*).narrationUI', '(window as unknown as { narrationUI?: unknown }).narrationUI')

for i, l in enumerate(txt.splitlines()):
    if '*FIX*' in l:
        print(f'{i+1}: {l.strip()[:100]}')
