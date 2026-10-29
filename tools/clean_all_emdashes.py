import glob
import sys

sys.stdout.reconfigure(encoding='utf-8')

files = glob.glob('static/js/**/*.ts', recursive=True) + glob.glob('static/js/**/*.d.ts', recursive=True)
cleaned = 0
total_replaced = 0

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            content = fp.read()
        count = content.count('\u2014') + content.count('—')
        if count > 0:
            new_content = content.replace('\u2014', '-').replace('—', '-')
            with open(f, 'w', encoding='utf-8', newline='\n') as fp:
                fp.write(new_content)
            cleaned += 1
            total_replaced += count
            print(f'{f}: cleaned {count} em-dashes')
    except Exception as e:
        print(f'Error processing {f}: {e}')

print(f'Finished: Cleaned {total_replaced} em-dashes across {cleaned} files.')
