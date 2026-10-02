"""Move in-file ambient `declare`s into globals.d.ts, or delete them when the
name already has a REAL declaration.

Why this exists: lanes were told globals.d.ts was off-limits, so 19 files grew
their own `declare const ui: any` / `declare class StreamTurnCards {...}`
blocks. Those erase at emit (so no runtime collision) but they collide at the
type level twice over:

  1. with each other - `ui`, `AIGenerator`, `GraphNetwork`, `extractAssistantText`
     and `reinitChoices` are declared in 2+ files at once (TS2451)
  2. with the REAL declaration - `declare class StreamTurnCards` sits alongside
     the actual class in stream-turn-cards.ts, and `declare const ui: any`
     alongside the actual const in ui-controller.ts

Fix, per name:
  - a real declaration exists  -> delete every declare for it; the real one wins
  - no real declaration       -> keep exactly one, in globals.d.ts, and remove
                                 it from the file that had it

Run with --apply to write; default is a dry run.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(r"F:\AI\viwo\virtual-world")
JS_ROOT = REPO / "static" / "js"
GLOBALS = JS_ROOT / "types" / "globals.d.ts"
MARK = "// >>> hoisted from converted modules - generated, do not hand-edit >>>"

DECL_START = re.compile(r"^declare\s+(const|function|class)\s+([A-Za-z_$][\w$]*)")
REAL_START = re.compile(r"^(?:const|let|class|function|async\s+function)\s+([A-Za-z_$][\w$]*)")


def statement_at(lines: list[str], start: int) -> int:
    """End line (exclusive) of the declaration beginning at `start`.

    Balances braces so a multi-line `declare const X: { ... };` is taken whole.
    """
    depth = 0
    seen_brace = False
    for i in range(start, len(lines)):
        line = lines[i]
        # ignore braces inside string literals on this line
        code = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`", "", line)
        for ch in code:
            if ch == "{":
                depth += 1
                seen_brace = True
            elif ch == "}":
                depth -= 1
        if seen_brace and depth <= 0:
            return i + 1
        if not seen_brace and ";" in code:
            return i + 1
    return len(lines)


def collect():
    """name -> list of (path, start, end, kind, text) for in-file declares."""
    found = defaultdict(list)
    for path in sorted(JS_ROOT.rglob("*.ts")):
        if "vendor" in path.parts or path == GLOBALS:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            m = DECL_START.match(lines[i])
            if not m:
                i += 1
                continue
            end = statement_at(lines, i)
            found[m.group(2)].append((path, i, end, m.group(1), "\n".join(lines[i:end])))
            i = end
    return found


def real_names() -> set[str]:
    """Names with a REAL (emitting) top-level declaration, or already ambient."""
    names = set()
    for path in sorted(JS_ROOT.rglob("*.ts")):
        if "vendor" in path.parts or path == GLOBALS:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = REAL_START.match(line)
            if m and not line.startswith("declare "):
                names.add(m.group(1))
    for line in GLOBALS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^declare\s+(?:const|function|class)\s+([A-Za-z_$][\w$]*)", line)
        if m:
            names.add(m.group(1))
    return names


def main() -> int:
    found = collect()
    reals = real_names()
    drop, hoist = [], {}
    for name, sites in sorted(found.items()):
        if name in reals:
            drop.append((name, sites, "redundant - a real declaration exists"))
        else:
            keep = max(sites, key=lambda s: len(s[4]))
            drop.append((name, [s for s in sites if s is not keep], "hoisted to globals.d.ts"))
            hoist[name] = keep

    print(f"in-file ambient declares: {sum(len(v) for v in found.values())} across {len(found)} names")
    print(f"  deleted (real declaration exists): {sum(len(s) for _, s, _ in drop if 'redundant' in _)}")
    print(f"  hoisted to globals.d.ts          : {len(hoist)}")
    print()
    for name, sites, why in drop:
        real_note = " (real decl in a converted file)" if "redundant" in why else ""
        print(f"  {name:<22} {len(sites)} declare(s) -> {why}{real_note}")
        for p, s, e, _, _ in sites:
            print(f"        {p.relative_to(REPO).as_posix()}:{s + 1}")

    if "--apply" not in sys.argv:
        print("\ndry run. Pass --apply.")
        return 0

    # 1. delete the declare blocks
    by_file = defaultdict(list)
    for name, sites, why in drop:
        for path, s, e, _, _ in sites:
            by_file[path].append((s, e))
    for path, ranges in by_file.items():
        lines = path.read_text(encoding="utf-8").splitlines()
        for s, e in sorted(ranges, reverse=True):
            del lines[s:e]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")

    # 2. append the hoisted block to globals.d.ts
    if hoist:
        gtext = GLOBALS.read_text(encoding="utf-8")
        block = [MARK]
        for name, (path, s, e, kind, text) in sorted(hoist.items()):
            owner = path.relative_to(JS_ROOT).as_posix()
            block.append(f"// {name} — owner: {owner}")
            block.append(text)
            block.append("")
        gtext = gtext.rstrip("\n") + "\n\n" + "\n".join(block)
        GLOBALS.write_text(gtext, encoding="utf-8", newline="")
    print(f"\nrewrote {len(by_file)} file(s); hoisted {len(hoist)} declaration(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())