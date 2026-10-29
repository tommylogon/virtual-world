with open('static/js/inspector/trigger-helpers.ts', 'r', encoding='utf-8') as f:
    content = f.read().replace('\r\n', '\n')

content = content.replace(
    'const effectParams = eff?.params || {};',
    'const effectParams: Record<string, any> = (eff?.params as Record<string, any>) || {};'
)

content = content.replace(
    'const descVal = effectParams.value || effectParams.description || \'\';',
    'const descVal = String(effectParams.value || effectParams.description || \'\');'
)

content = content.replace(
    'else if (effectType === \'append_description\' && effectParams.text) detail += ` +"${(effectParams.text||\'\').substring(0,25)}${(effectParams.text||\'\').length > 25 ? \'...\' : \'\'}"`;',
    'else if (effectType === \'append_description\' && effectParams.text) detail += ` +"${String(effectParams.text||\'\').substring(0,25)}${String(effectParams.text||\'\').length > 25 ? \'...\' : \'\'}"`;'
)

content = content.replace(
    'const triggerId = def.id || \'\';',
    'const triggerId = String(def.id || \'\');'
)

content = content.replace(
    'if (w != null && !isNaN(parseFloat(w))) total += parseFloat(w);',
    'if (w != null && !isNaN(parseFloat(String(w)))) total += parseFloat(String(w));'
)

content = content.replace(
    '!isNaN(parseFloat(w)) ? htmlTag',
    '!isNaN(parseFloat(String(w))) ? htmlTag'
)

assert '\u2014' not in content, 'em-dash detected'

with open('static/js/inspector/trigger-helpers.ts', 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print('Updated trigger-helpers.ts successfully')
