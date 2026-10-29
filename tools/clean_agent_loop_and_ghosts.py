import sys

# 1. agent-loop.ts
p = "static/js/nl-editor/agent-loop.ts"
content = open(p, "r", encoding="utf-8").read()
content = content.replace('\u2014', ' - ').replace('—', ' - ')
content = content.replace("JSON tool-call object *FIX*where in the prose", "JSON tool-call object anywhere in the prose")
content = content.replace("- Before creating *FIX* item from scratch", "- Before creating any item from scratch")
assert '\u2014' not in content and '—' not in content, "Em-dash remaining in agent-loop.ts"
assert content.count("*FIX*") == 0, f"Remaining FIX in agent-loop.ts: {content.count('*FIX*')}"
open(p, "w", encoding="utf-8", newline='').write(content)
print("agent-loop.ts cleaned.")

# 2. ghosts.ts
p = "static/js/nl-editor/ghosts.ts"
content = open(p, "r", encoding="utf-8").read()
content = content.replace('\u2014', ' - ').replace('—', ' - ')
content = content.replace("before *FIX*thing is applied", "before anything is applied")
assert '\u2014' not in content and '—' not in content, "Em-dash remaining in ghosts.ts"
assert content.count("*FIX*") == 0, f"Remaining FIX in ghosts.ts: {content.count('*FIX*')}"
open(p, "w", encoding="utf-8", newline='').write(content)
print("ghosts.ts cleaned.")
