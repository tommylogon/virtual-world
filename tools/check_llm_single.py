with open('static/js/llm-client.ts', 'r', encoding='utf-8') as f:
    txt = f.read()

txt = txt.replace('\u2014', ' - ').replace('—', ' - ')

# English words
txt = txt.replace('How m*FIX* times a length-stopped', 'How many times a length-stopped')
txt = txt.replace('well past *FIX* local model\'s practical', 'well past any local model\'s practical')
txt = txt.replace('(m*FIX* providers reject response_format', '(many providers reject response_format')
txt = txt.replace('declares `llmClient: *FIX*` so', 'declares `llmClient: any` so')

# Window and types
txt = txt.replace('(window as *FIX*).VW = (window as *FIX*).VW || {};', '(window as unknown as { VW: Record<string, unknown> }).VW = (window as unknown as { VW: Record<string, unknown> }).VW || {};')
txt = txt.replace('tool_calls?: *FIX*[];', 'tool_calls?: Array<Record<string, unknown>>;')
txt = txt.replace('tools?: *FIX*[];', 'tools?: Array<Record<string, unknown>>;')
txt = txt.replace('Promise<*FIX*>', 'Promise<unknown>')
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
txt = txt.replace('requestBody: *FIX*, body: *FIX*,', 'requestBody: unknown, body: unknown,')
txt = txt.replace('completion: *FIX*', 'completion: Record<string, unknown>')
txt = txt.replace('_extractResponsesToolCalls(completion: Record<string, unknown>): *FIX*[] | null {', '_extractResponsesToolCalls(completion: Record<string, unknown>): Array<Record<string, unknown>> | null {')
txt = txt.replace('.filter((o: *FIX*) => o.type === \'function_call\')', '.filter((o: { type?: string }) => o.type === \'function_call\')')
txt = txt.replace('.map((o: *FIX*) => ({', '.map((o: Record<string, unknown>) => ({')
txt = txt.replace('.filter((item: *FIX*) => item.type === \'message\')', '.filter((item: { type?: string }) => item.type === \'message\')')
txt = txt.replace('? item.content.map((c: *FIX*) => c.text || \'\').join(\'\')', '? (item.content as Array<{ text?: string }>).map((c: { text?: string }) => c.text || \'\').join(\'\')')
txt = txt.replace('(m: *FIX*) => m.id || m.name || m', '(m: { id?: string; name?: string } | string) => (typeof m === \'object\' && m ? m.id || m.name : m)')

for i, l in enumerate(txt.splitlines()):
    if '*FIX*' in l:
        print(f'{i+1}: {l.strip()[:100]}')
