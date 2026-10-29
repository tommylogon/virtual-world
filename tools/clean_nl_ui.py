p = 'static/js/nl-editor/ui.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('this.container.*FIX*= `', 'window.Lit.render(window.Lit.unsafeHTML(`')
txt = txt.replace('                    </div>\n                </div>\n            `;\n\n            this.chatList', '                    </div>\n                </div>\n            `), this.container);\n\n            this.chatList')
txt = txt.replace('bubble.*FIX*= html;', 'window.Lit.render(window.Lit.unsafeHTML(html), bubble);')
txt = txt.replace('qEl.*FIX*= `', 'window.Lit.render(window.Lit.unsafeHTML(`')
txt = txt.replace('                </div>\n            `;\n\n            document.getElementById(\'nl-clarify-dismiss\')', '                </div>\n            `), qEl);\n\n            document.getElementById(\'nl-clarify-dismiss\')')
txt = txt.replace("optsEl.*FIX*= '';", "optsEl.replaceChildren();")
txt = txt.replace("listEl.*FIX*= '';", "listEl.replaceChildren();")

assert '\u2014' not in txt and '—' not in txt, 'Em-dash found in ui.ts'
rem = txt.count('*FIX*')
assert rem == 0, f'Remaining FIX in ui.ts: {rem}'
open(p, 'w', encoding='utf-8', newline='').write(txt)
print('ui.ts 100% clean!')
