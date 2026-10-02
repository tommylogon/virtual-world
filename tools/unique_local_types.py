"""Give file-local interface/type aliases unique names.

Every top-level `interface` in a classic script is GLOBAL, so 35 names declared
across the converted files all merge. They do not merge cleanly - the shapes
differ per file - which is why 94 errors are TS2687 ("all declarations of 'id'
must have identical modifiers"), TS2717 ("subsequent property declarations must
have the same type") and TS2374 (duplicate index signature).

Two same-named types with different shapes are not the same type, so sharing a
name is simply wrong. Each file gets its own name; the file that uses a name
most keeps the original.

Safety: only files that DECLARE the name are touched, and the rename is
word-boundary with a negative lookbehind for `.` so `x.GraphNode` is untouched.
Files that merely *use* a name they do not declare keep resolving to the keeper.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(r"F:\AI\viwo\virtual-world")
JS_ROOT = REPO / "static" / "js"

DECL = re.compile(r"^(?:export\s+)?(interface|type)\s+([A-Za-z_$][\w$]*)")
USE = re.compile(r"(?<![.\w$])([A-Za-z_$][\w$]*)")


def pascal(fragment: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", fragment)
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def main() -> int:
    apply = "--apply" in sys.argv

    declares: dict[str, list[Path]] = defaultdict(list)
    texts: dict[Path, list[str]] = {}
    for path in sorted(JS_ROOT.rglob("*.ts")):
        if "vendor" in path.parts or path.name == "globals.d.ts":
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        texts[path] = lines
        for line in lines:
            m = DECL.match(line)
            if m:
                declares[m.group(2)].append(path)

    dupes = {n: ps for n, ps in declares.items() if len(ps) > 1}
    print(f"names declared in 2+ files: {len(dupes)}")

    plan = []
    for name, paths in sorted(dupes.items()):
        # keeper = the file referencing it most; it is the likeliest owner
        scored = []
        for p in paths:
            uses = sum(len(USE.findall(l)) for l in texts[p] if USE.search(l) and name in l)
            scored.append((uses, p.name, p))
        scored.sort(reverse=True)
        keeper = scored[0][2]
        for _, _, p in scored[1:]:
            stem = pascal(p.stem)
            new = f"{stem}{name}"
            # `character-art.ts` + `CharacterArtApi` would give
            # CharacterArtCharacterArtApi; collapse the stutter.
            if name.startswith(stem) and len(name) > len(stem):
                new = stem + name[len(stem):]
            if new == name:
                continue
            plan.append((p, name, new))

    for p, old, new in plan:
        rel = p.relative_to(REPO).as_posix()
        print(f"  {rel}: {old} -> {new}")

    if not apply:
        print("\ndry run. Pass --apply.")
        return 0

    for p, old, new in plan:
        pattern = re.compile(rf"(?<![.\w$]){re.escape(old)}(?![\w$])")
        out = [pattern.sub(new, line) for line in texts[p]]
        p.write_text("\n".join(out) + "\n", encoding="utf-8", newline="")
    print(f"\nrenamed in {len({p for p, _, _ in plan})} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())