"""Generate ambient declarations for globals still defined in .js modules.

A converted caller needs a type for a global whose owner is still plain .js.
Hand-writing that type is where errors creep in: the GraphNetwork declaration
was picked from the wrong file and listed four members that belong to a
different module, while the real API has 34.

So derive it from the definition instead. For `window.X = { ... }` in a .js
file, read the object literal's top-level keys and emit a declaration with the
real member names. Argument and return types stay `any` - the goal is that the
NAMES are right, which is what callers actually need. Narrowing them is real
work and belongs with converting the module.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(r"F:\AI\viwo\virtual-world")
JS_ROOT = REPO / "static" / "js"
GLOBALS = JS_ROOT / "types" / "globals.d.ts"
MARK = "// >>> ambient shapes for still-unconverted .js modules >>>"
ENDMARK = "// <<< ambient shapes <<<"

ASSIGN = re.compile(r"^\s*window\.([A-Za-z_$][\w$]*)\s*=\s*\{\s*$")


def strip_noise(line: str) -> str:
    line = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`", '""', line)
    return re.sub(r"//.*$", "", line)


def object_body(lines: list[str], start: int) -> list[tuple[int, str]]:
    """Top-level member lines of an object literal whose `{` is on the line
    BEFORE `start` - so we begin already one level deep.

    A line belongs to the object if the depth AT THE START of that line is 1,
    not after counting its braces: a member like `async init() {` carries its
    own opening brace, and testing after the increment would drop every method.
    """
    out, depth = [], 1
    for i in range(start, len(lines)):
        raw = lines[i].strip()
        if depth == 1 and raw and not raw.startswith(("//", "/*", "*")):
            out.append((i + 1, raw))
        depth += strip_noise(lines[i]).count("{") - strip_noise(lines[i]).count("}")
        if depth <= 0:
            break
    return out


MEMBER = re.compile(r"^([A-Za-z_$][\w$]*)\s*(\(|:|=|,|\?)")
GETTER = re.compile(r"^(get|set)\s+([A-Za-z_$][\w$]*)")
KEYWORDS = {"if", "for", "while", "switch", "return", "function", "const", "let", "var", "try", "catch"}


def members(body: list[tuple[int, str]]) -> tuple[list[str], list[str]]:
    methods, fields = [], []
    for _, raw in body:
        # `async init() {` must match on `init`, not on the `async` prefix
        raw = re.sub(r"^(?:async|get|set)\s+", "", raw)
        g = GETTER.match(raw)
        if g:
            fields.append(g.group(2))
            continue
        m = MEMBER.match(raw)
        if not m:
            continue
        name, nxt = m.group(1), m.group(2)
        if name in KEYWORDS:
            continue
        (methods if nxt == "(" else fields).append(name)
    return methods, fields


def main() -> int:
    wanted = sys.argv[1:] if any(a != "--apply" for a in sys.argv[1:]) else ["GraphNetwork"]
    emitted, missing = [], []

    for name in wanted:
        found = None
        for path in sorted(JS_ROOT.rglob("*.js")):
            if "vendor" in path.parts:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines):
                m = ASSIGN.match(line)
                if m and m.group(1) == name:
                    found = (path, i, object_body(lines, i + 1))
                    break
            if found:
                break
        if not found:
            missing.append(name)
            continue
        path, start, body = found
        methods, fields = members(body)
        rel = path.relative_to(REPO).as_posix()
        print(f"{name}  <- {rel}:{start + 1}   {len(methods)} method(s), {len(fields)} field(s)")
        block = [f"declare const {name}: {{"]
        for f in sorted(set(fields)):
            block.append(f"    {f}: any;")
        for m in sorted(set(methods)):
            block.append(f"    {m}(...args: any[]): any;")
        block.append("};")
        emitted.append((name, "\n".join(block), rel))

    if missing:
        print(f"\nnot found as `window.X = {{`: {', '.join(missing)}")

    if "--apply" not in sys.argv:
        print("\ndry run. Pass --apply to write into globals.d.ts")
        for name, block, _ in emitted:
            print("\n" + block)
        return 0

    gtext = GLOBALS.read_text(encoding="utf-8")
    for name, block, rel in emitted:
        pattern = re.compile(rf"declare const {re.escape(name)}:\s*\{{.*?\n\}};", re.S)
        annotation = f"// owner: {rel}\n"
        if pattern.search(gtext):
            gtext = pattern.sub(lambda _m: annotation + block, gtext, count=1)
            print(f"  replaced existing declaration for {name}")
        else:
            gtext = gtext.rstrip("\n") + "\n\n" + MARK + "\n" + annotation + block + "\n" + ENDMARK + "\n"
            print(f"  appended {name}")
    GLOBALS.write_text(gtext, encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    sys.exit(main())