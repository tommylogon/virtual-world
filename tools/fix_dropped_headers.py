"""Relocate a leading run of type-only declarations so tsc keeps the header.

tsc DROPS a file's leading JSDoc when the first statement is type-only, and
js_module_index.py reads @module/@contributes out of the EMITTED .js. Five files
lost their module contract this way - their .ts is correct and their .js is not,
which is the worst shape to debug.

Types hoist, so moving the block to the end of the file is semantically inert.
The emitted .js gains a `"use strict"` line it did not have, which is the
intended migration behaviour anyway.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"F:\AI\viwo\virtual-world")
JS = REPO / "static" / "js"
DECL = re.compile(r"^(?:export\s+)?(?:interface|type)\s")


def block_end(lines: list[str], start: int) -> int:
    """End (exclusive) of the type declaration beginning at `start`."""
    depth = 0
    seen = False
    for i in range(start, len(lines)):
        line = lines[i]
        code = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`", "", line)
        depth += code.count("{") - code.count("}")
        if depth <= 0 and (seen or ";" in code or code.rstrip().endswith("}")):
            return i + 1
        if depth > 0:
            seen = True
    return len(lines)


def leading_type_run(lines: list[str]) -> tuple[int, int] | None:
    """Span of leading type-only declarations, skipping the header + comments."""
    i = 0
    while i < len(lines) and (lines[i].lstrip().startswith(("/*", "*", "//")) or not lines[i].strip()):
        i += 1
    start = i
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith(("//", "/*", "*")):
            i += 1
            continue
        if not DECL.match(lines[i]):
            break
        i = block_end(lines, i)
    return (start, i) if i > start else None


def main() -> int:
    apply = "--apply" in sys.argv
    targets = [a for a in sys.argv[1:] if not a.startswith("--")] or [
        "static/js/graph/overlays.ts",
        "static/js/item-library/consumable-triggers.ts",
        "static/js/shared/diff-modal.ts",
        "static/js/shared/item-containment.ts",
        "static/js/shared/trigger-suggest-ai.ts",
    ]
    for rel in targets:
        path = REPO / rel
        lines = path.read_text(encoding="utf-8").splitlines()
        span = leading_type_run(lines)
        if not span:
            print(f"  {rel}: no leading type-only declarations")
            continue
        start, end = span
        moved = lines[start:end]
        first = next((l.strip() for l in moved if l.strip()), "")
        print(f"  {rel}: moving {end - start} line(s) starting '{first[:52]}'")
        if not apply:
            continue
        rest = lines[:start] + lines[end:]
        note = ["", "// Type declarations relocated from the top of this file: a leading",
                "// type-only statement makes tsc drop this file's leading JSDoc, and",
                "// js_module_index.py reads @module/@contributes from the emitted .js.",
                "// Types hoist, so position is semantically irrelevant."]
        path.write_text("\n".join(rest + note + moved) + "\n", encoding="utf-8", newline="")
    if not apply:
        print("\ndry run. Pass --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())