with open('tools/refactor_core_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# let's run it without the assertion and print remaining lines
code = code.replace('assert rem == 0, f"main.ts rem: {rem}"', '# assert rem == 0')
exec(code)

for i, l in enumerate(txt.splitlines()):
    if '*FIX*' in l:
        print(f'{i+1}: {l.strip()[:100]}')
