#!/usr/bin/env python3
"""
tools/audit_client_codebase.py

Exhaustive AST/regex scanner across all TypeScript files in static/js/
Extracts:
1. File roles, classes, and exported surfaces
2. DOM rendering mechanics (innerHTML, createElement, lit-html, unsafeHTML)
3. Event handling patterns (inline onclick string, addEventListener, lit @click, window globals)
4. Type safety metrics (occurrences of : any, as any, interface, type)
5. Duplication indicators (modals, node headers, delete prompts, tabs, badges, sliders)
6. Model/State dependencies (worldState, networkManager, inspector, config, ApiClient)
"""

import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC_JS = ROOT / "static" / "js"

def scan_file(file_path: Path):
    rel_path = file_path.relative_to(ROOT).as_posix()
    content = file_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    line_count = len(lines)

    # Class / Interface / Type declarations
    classes = re.findall(r"^\s*(?:export\s+)?class\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
    interfaces = re.findall(r"^\s*(?:export\s+)?interface\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
    types = re.findall(r"^\s*(?:export\s+)?type\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
    
    # Top-level functions
    functions = re.findall(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
    methods = re.findall(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+)?(?:async\s+)?([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?::\s*[^;{]+)?\s*\{", content, re.MULTILINE)
    # Filter out keywords from methods
    keywords = {"if", "for", "while", "switch", "catch", "constructor", "function"}
    methods = [m for m in methods if m not in keywords]

    # Type safety metrics
    any_count = len(re.findall(r":\s*any\b|<any>|as\s+any\b|as\s+unknown\s+as\s+any\b", content))
    unknown_count = len(re.findall(r":\s*unknown\b|<unknown>|as\s+unknown\b", content))

    # DOM generation mechanics
    inner_html_count = len(re.findall(r"\.innerHTML\s*=", content))
    create_element_count = len(re.findall(r"document\.createElement\(", content))
    lit_html_blocks = len(re.findall(r"(?:htmlTag|window\.Lit\.html|Lit\.html|html)\s*`", content))
    unsafe_html_count = len(re.findall(r"unsafeHTML\(", content))
    lit_render_count = len(re.findall(r"(?:render|renderInto|renderPanel)\s*\(", content))

    # Event binding styles
    inline_onclick = len(re.findall(r"on(?:click|change|input|submit|keydown|keyup)\s*=\s*['\"][^'\"]+['\"]", content))
    add_event_listener = len(re.findall(r"\.addEventListener\(", content))
    lit_event_binding = len(re.findall(r"@(click|change|input|submit|keydown|keyup)\s*=", content))
    window_export = len(re.findall(r"window\.([A-Za-z0-9_]+)\s*=", content))

    # Duplication pattern detection
    has_modal_backdrop = bool(re.search(r"backdrop|modal-overlay|rgba\(0,\s*0,\s*0|position:\s*fixed", content, re.I))
    has_header_sync = bool(re.search(r"sync-id|Sync ID|lowercase|inspector-header", content, re.I))
    has_danger_zone = bool(re.search(r"danger|delete|remove-node|confirm\(", content, re.I))
    has_tabs = bool(re.search(r"tab-nav|tab-btn|active-tab|tabContent", content, re.I))
    has_slider = bool(re.search(r"type=['\"]range['\"]|slider|bench-range", content, re.I))
    has_badge = bool(re.search(r"badge|chip|status-pill", content, re.I))

    # State / Global dependencies
    touches_world_state = "worldState" in content
    touches_network_manager = "networkManager" in content or "GraphNetwork" in content
    touches_inspector = "inspector" in content or "InspectorPanel" in content
    touches_config = "config" in content or "ConfigManager" in content
    touches_api_client = "ApiClient" in content or "/api/" in content

    # Dominant rendering architecture
    if lit_html_blocks > 0 or lit_render_count > 0:
        if inner_html_count > 3:
            dom_arch = "hybrid_lit_innerhtml"
        else:
            dom_arch = "lit_html"
    elif inner_html_count > 0 and create_element_count > 0:
        dom_arch = "hybrid_dom_innerhtml"
    elif inner_html_count > 0:
        dom_arch = "inner_html"
    elif create_element_count > 0:
        dom_arch = "document_create_element"
    else:
        dom_arch = "logic_only"

    return {
        "file": rel_path,
        "name": file_path.name,
        "dir": file_path.parent.relative_to(STATIC_JS).as_posix() if file_path.parent != STATIC_JS else ".",
        "lines": line_count,
        "classes": classes,
        "interfaces": interfaces,
        "types": types,
        "functions_count": len(functions) + len(methods),
        "functions_sample": (functions + methods)[:8],
        "any_count": any_count,
        "unknown_count": unknown_count,
        "inner_html_count": inner_html_count,
        "create_element_count": create_element_count,
        "lit_html_blocks": lit_html_blocks,
        "unsafe_html_count": unsafe_html_count,
        "lit_render_count": lit_render_count,
        "inline_onclick": inline_onclick,
        "add_event_listener": add_event_listener,
        "lit_event_binding": lit_event_binding,
        "window_export": window_export,
        "dom_arch": dom_arch,
        "duplication_flags": {
            "modal": has_modal_backdrop,
            "header_sync": has_header_sync,
            "danger_zone": has_danger_zone,
            "tabs": has_tabs,
            "slider": has_slider,
            "badge": has_badge
        },
        "dependencies": {
            "worldState": touches_world_state,
            "networkManager": touches_network_manager,
            "inspector": touches_inspector,
            "config": touches_config,
            "apiClient": touches_api_client
        }
    }

def main():
    records = []
    for root, dirs, files in os.walk(STATIC_JS):
        # Skip vendor
        if "vendor" in Path(root).parts:
            continue
        for file in files:
            if file.endswith(".ts") and not file.endswith(".d.ts"):
                fp = Path(root) / file
                records.append(scan_file(fp))

    records.sort(key=lambda r: r["lines"], reverse=True)

    summary = {
        "total_files": len(records),
        "total_lines": sum(r["lines"] for r in records),
        "total_any": sum(r["any_count"] for r in records),
        "total_inner_html": sum(r["inner_html_count"] for r in records),
        "total_create_element": sum(r["create_element_count"] for r in records),
        "total_lit_blocks": sum(r["lit_html_blocks"] for r in records),
        "total_unsafe_html": sum(r["unsafe_html_count"] for r in records),
        "dom_architectures": {},
        "records": records
    }

    for r in records:
        arch = r["dom_arch"]
        summary["dom_architectures"][arch] = summary["dom_architectures"].get(arch, 0) + 1

    out_file = ROOT / "scratch" / "client_audit_data.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Audit complete: {len(records)} files scanned.")
    print(f"Total lines: {summary['total_lines']}")
    print(f"Total 'any' instances: {summary['total_any']}")
    print(f"DOM Architectures: {summary['dom_architectures']}")
    print(f"Wrote raw audit database to {out_file}")

if __name__ == "__main__":
    main()
