"""task-83 bulk rename — UTF-8 safe, word-boundary scoped.
Run once, then delete. Edits .ts sources only; .js rebuilt via ts_convert.py check.
Python files use explicit utf-8 read/write (never Get-Content/Set-Content)."""
import re, pathlib

def sub_file(path, pairs, skip_quoted_for=()):
    p = pathlib.Path(path)
    t = p.read_text(encoding="utf-8")
    orig = t
    for old, new in pairs:
        if old in skip_quoted_for:
            # Replace only outside single/double/backtick strings: split lines,
            # skip matches inside quotes by processing code segments.
            # Simple approach: replace on lines, but reject replacements that
            # sit inside tg-*-tp class strings (the only known hazard).
            def repl_line(line):
                if "tg-eff-tp" in line or "tg-beh-tp" in line:
                    # protect class strings: temporarily mask them
                    line = line.replace("tg-eff-tp", "TG_EFF_TP_MASK").replace("tg-beh-tp", "TG_BEH_TP_MASK")
                    line = re.sub(r"\b" + re.escape(old) + r"\b", new, line)
                    line = line.replace("TG_EFF_TP_MASK", "tg-eff-tp").replace("TG_BEH_TP_MASK", "tg-beh-tp")
                    return line
                return re.sub(r"\b" + re.escape(old) + r"\b", new, line)
            t = "\n".join(repl_line(l) for l in t.split("\n"))
        else:
            t = re.sub(r"\b" + re.escape(old) + r"\b", new, t)
    if t != orig:
        p.write_text(t, encoding="utf-8")
        print(f"edited {path}")
    else:
        print(f"no-change {path}")

# trigger-editor.ts: ep->effParams already has ct/cv partially done via editor;
# finish remaining cv + all ep here (ct done, skip).
sub_file("static/js/shared/trigger-editor.ts", [("cv", "condValue"), ("ep", "effParams")])

# trigger-graph.ts: ct->condType, ns->graphNodes, fp->fromPos, tp->toPos (quote-safe), nid->nodeId
# NOTE: counter `let nodeId = 0` renamed to nodeCounter first via editor to free the name.
sub_file("static/js/shared/trigger-graph.ts", [
    ("ct", "condType"),
    ("ns", "graphNodes"),
    ("fp", "fromPos"),
    ("tp", "toPos"),
    ("nid", "nodeId"),
], skip_quoted_for=("tp",))

sub_file("static/js/validator-panel.ts", [("tn", "triggerNode")])
sub_file("static/js/inspector/way-view-triggers.ts", [("ep", "edgeProps")])
sub_file("static/js/library-browser.ts", [("ep", "edgeProps")])
sub_file("static/js/ui/world-export.ts", [("ni", "nodeKey"), ("pi", "doorIdx"), ("oi", "otherIdx")])
sub_file("static/js/graph/network-manager.ts", [("ns", "sizeScale")])
sub_file("static/js/graph/layout-engine.ts", [("ns", "nodeScale")])
sub_file("static/js/inspector/sprite-sheet.ts", [("cv", "thumbCanvas")])
sub_file("static/js/soak/soak-api.ts", [("ct", "contentType")])
sub_file("static/js/nl-editor/tools.ts", [("nid", "normId")])

# Python: nid->node_id, nd->node (word-boundary; nd is loop var for node dict)
sub_file("routes/saveload.py", [("nid", "node_id"), ("nd", "node")])
sub_file("engine/nl_editor_validation.py", [("nid", "node_id")])
sub_file("tools/assemble_scenario.py", [("nid", "node_id")])

print("done")
