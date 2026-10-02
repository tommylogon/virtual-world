#!/usr/bin/env python3
"""TypeScript conversion helper for the classic-script front end.

The migration convention lives in ``docs/design/typescript-migration.md``; this
tool automates the mechanical half of it and reports the part that needs
judgment. It does not invent types.

Subcommands
-----------
``report``       How far is the corpus from converting? Error distribution by
                 code, by cause, and per file. This is the denominator for any
                 wave plan.
``list``         Per-file readiness: lines, lit usage, undeclared globals,
                 DOM property accesses, ``@ts-check`` status.
``plan PATH``    What one file needs before it can convert.
``convert PATH`` Header-preserving ``.js`` -> ``.ts`` rename, then the build.
                 Dry run unless ``--apply``.
``check [PATH]`` The verification gate from the migration doc.
``sweep``        Add ``// @ts-check`` to ``.js`` files. Zero behaviour risk, and
                 the only fully automatic step in the migration.

Design note: every judgment here is delegated to ``tsc``. Undeclared globals,
missing properties and error codes are read out of the compiler rather than
guessed with a regex, so the report cannot drift from the compiler the way a
hand-maintained list already has (see ``docs/design/typescript-migration-plan.md``
claiming ~29 ambient symbols where ``globals.d.ts`` has 13).

Usage::

    python tools/ts_convert.py report
    python tools/ts_convert.py list --sort errors --limit 20
    python tools/ts_convert.py plan static/js/shared/dom-utils.js
    python tools/ts_convert.py convert static/js/shared/dom-utils.js
    python tools/ts_convert.py convert static/js/shared/dom-utils.js --apply
    python tools/ts_convert.py check
    python tools/ts_convert.py sweep --max-errors 0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_ROOT = REPO_ROOT / "static" / "js"
VENDOR = "static/js/vendor"
BUILD_CONFIG = REPO_ROOT / "tsconfig.json"
CHECK_CONFIG = REPO_ROOT / "tsconfig.check.json"
GLOBALS_DTS = JS_ROOT / "types" / "globals.d.ts"

# Marker the emitted file carries; see tools/ts_convert.py convert.
GENERATED_NOTE = "GENERATED"

#: Set by the CLI: probe the lenient check config instead of the strict build.
#: Readiness defaults to strict because strict is what gates a conversion.
LENIENT = False

# Element types a querySelector result can be, and the instance properties the
# front end reaches for on them.
ELEMENT_TYPES = (
    "HTMLElement",
    "Element",
    "HTMLInputElement",
    "HTMLSelectElement",
    "HTMLTextAreaElement",
    "HTMLButtonElement",
    "HTMLFormElement",
    "HTMLAnchorElement",
    "HTMLImageElement",
    "HTMLCanvasElement",
    "HTMLDialogElement",
    "Node",
)

ERROR_LINE = re.compile(r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.*)$")
HEADER_LINE = re.compile(r"^\s*\*?\s*@(module|contributes|powers|relates|docs)\b")


# --------------------------------------------------------------------------
# repo plumbing
# --------------------------------------------------------------------------

def tsc_path() -> str:
    """Path to the repo-local tsc, honouring the Windows .cmd shim."""
    name = "tsc.cmd" if os.name == "nt" else "tsc"
    candidate = REPO_ROOT / "node_modules" / ".bin" / name
    if not candidate.exists():
        sys.exit("error: typescript is not installed. Run `npm install` first.")
    return str(candidate)


def npm(*args: str) -> list[str]:
    """``npm`` as an argv prefix. On Windows npm is a .cmd shim, so invoking the
    bare name raises FileNotFoundError without a shell."""
    name = "npm.cmd" if os.name == "nt" else "npm"
    found = shutil.which(name) or shutil.which("npm")
    if not found:
        sys.exit("error: npm is not on PATH")
    return [found, *args]


def run_tsc(config: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [tsc_path(), "-p", str(config)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def write_measure_config(directory: Path) -> Path:
    """A checkJs-on view of the whole corpus, written outside the repo.

    ``tsconfig.check.json`` has ``checkJs: false``, so today the 151 ``.js``
    files are parsed but never type-checked. Enabling it in a temp config is
    how the report gets a denominator without changing what the repo checks.

    The compiler options deliberately mirror ``tsconfig.json`` - the *build*
    config, which is ``strict: true`` - not the lenient check config. Readiness
    has to be measured against the settings that will actually gate a
    conversion: under a lenient probe a file with an implicit-``any`` parameter
    reports zero errors and then fails ``noEmitOnError`` the moment it is
    renamed. Use ``--lenient`` to see the old, flattering number.
    """
    compiler_options = {
        "target": "ES2022",
        "module": "esnext",
        "lib": ["DOM", "DOM.Iterable", "ES2022"],
        "allowJs": True,
        "checkJs": True,
        "noEmit": True,
        "strict": True,
        "forceConsistentCasingInFileNames": True,
        "skipLibCheck": True,
        "types": [],
    }
    if LENIENT:
        compiler_options["strict"] = False
        compiler_options["noImplicitAny"] = False
    config = {
        "compilerOptions": compiler_options,
        "include": [
            (JS_ROOT / "**" / "*.js").as_posix(),
            (JS_ROOT / "**" / "*.ts").as_posix(),
        ],
        "exclude": [(REPO_ROOT / VENDOR).as_posix()],
    }
    path = directory / "tsconfig.checkjs-probe.json"
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def source_files() -> list[Path]:
    """Every hand-written front-end file, vendor excluded."""
    out = []
    for pattern in ("**/*.js", "**/*.ts"):
        for path in sorted(JS_ROOT.glob(pattern)):
            if VENDOR in path.relative_to(REPO_ROOT).as_posix():
                continue
            if "types" in path.relative_to(JS_ROOT).parts:
                continue
            out.append(path)
    return out


# --------------------------------------------------------------------------
# error model
# --------------------------------------------------------------------------

class Finding:
    __slots__ = ("path", "line", "col", "code", "message", "cause", "subject")

    def __init__(self, path: str, line: int, col: int, code: str, message: str):
        self.path = path
        self.line = line
        self.col = col
        self.code = code
        self.message = message
        self.cause = classify(code, message)
        self.subject = subject_of(message)

    @property
    def key(self) -> str:
        return f"{self.path}:{self.line}:{self.col}"


def classify(code: str, message: str) -> str:
    """Bucket a compiler error by what it would take to fix it.

    The buckets are the point of this tool: 'declare the symbol' and 'narrow the
    element type' are mechanical, while everything else needs a human.
    """
    if code == "TS2304":
        return "undeclared-identifier"
    if code in ("TS7005", "TS7006", "TS7008", "TS7010", "TS7015", "TS7017", "TS7031", "TS7032", "TS7043", "TS7044"):
        return "implicit-any"
    if code in ("TS18048", "TS2532", "TS18047"):
        return "possibly-undefined"
    if code == "TS2339" and message.startswith("Property '") and "Window & typeof globalThis" in message:
        prop = re.match(r"Property '([^']+)'", message).group(1)
        return "undeclared-window-global" if prop != "Lit" else "lit-untyped"
    if code == "TS2339" and "does not exist on type" in message:
        if re.search(r"does not exist on type '(" + "|".join(ELEMENT_TYPES) + r")'", message):
            return "untyped-dom-element"
        return "missing-property"
    if code == "TS2552":
        return "misspelled-name"
    if code == "TS2551":
        return "misspelled-property"
    if code == "TS2322":
        return "type-mismatch"
    if code in ("TS2307", "TS2300", "TS2688", "TS2792"):
        return "module-resolution"
    if code.startswith("TS23") and code.endswith("4"):
        return "call-signature"
    return "other"


def subject_of(message: str) -> str:
    match = re.match(r"(?:Property|Cannot find name) '([^']+)'", message)
    return match.group(1) if match else ""


def parse_errors(output: str) -> list[Finding]:
    findings = []
    for line in output.splitlines():
        match = ERROR_LINE.match(line.strip())
        if not match:
            continue
        rel = Path(match.group("file"))
        try:
            rel = rel.resolve().relative_to(REPO_ROOT)
        except ValueError:
            rel = Path(rel.name)
        findings.append(
            Finding(rel.as_posix(), int(match.group("line")), int(match.group("col")),
                   match.group("code"), match.group("msg"))
        )
    return findings


def collect() -> list[Finding]:
    with tempfile.TemporaryDirectory() as tmp:
        config = write_measure_config(Path(tmp))
        _, output = run_tsc(config)
    return parse_errors(output)


# --------------------------------------------------------------------------
# per-file model
# --------------------------------------------------------------------------

def has_ts_check(path: Path) -> bool:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
        if line.strip().startswith("// @ts-check"):
            return True
    return False


def uses_lit(text: str) -> bool:
    return "window.Lit" in text or re.search(r"(?<![\w.])Lit\.", text) is not None


def header_of(text: str) -> list[str]:
    """The leading ``@module``/``@contributes``/... comment block, verbatim."""
    block, in_block = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("/*"):
            in_block = True
        if in_block:
            block.append(line)
            if stripped.endswith("*/"):
                return block
        elif block:
            break
    return block if any(HEADER_LINE.match(line) for line in block) else []


def build_index() -> list[dict]:
    findings = collect()
    by_file = defaultdict(list)
    for finding in findings:
        by_file[finding.path].append(finding)

    rows = []
    for path in source_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        file_findings = by_file.get(rel, [])
        rows.append({
            "path": rel,
            "ext": path.suffix,
            "lines": len(text.splitlines()),
            "errors": len(file_findings),
            "causes": dict(Counter(f.cause for f in file_findings)),
            "undeclared": sorted({f.subject for f in file_findings if f.cause == "undeclared-identifier"}),
            "window_globals": sorted({f.subject for f in file_findings if f.cause == "undeclared-window-global"}),
            "dom_props": sorted({f.subject for f in file_findings if f.cause == "untyped-dom-element"}),
            "lit": uses_lit(text),
            "ts_check": has_ts_check(path),
            "has_sibling_ts": path.with_suffix(".ts").exists() if path.suffix == ".js" else False,
        })
    return rows


# --------------------------------------------------------------------------
# output helpers
# --------------------------------------------------------------------------

def bar(count: int, width: int = 28) -> str:
    return "#" * min(width, count)


def rel_of(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------

def cmd_report(args) -> int:
    rows = build_index()
    findings = collect()
    total = len(findings)
    causes = Counter(f.cause for f in findings)
    codes = Counter(f.code for f in findings)
    dirty = [r for r in rows if r["errors"]]
    converted = [r for r in rows if r["ext"] == ".ts"]

    if args.json:
        print(json.dumps({
            "total_errors": total,
            "files_total": len(rows),
            "files_with_errors": len(dirty),
            "by_cause": dict(causes.most_common()),
            "by_code": dict(codes.most_common()),
            "by_file": sorted(
                ({"path": r["path"], "errors": r["errors"], "causes": r["causes"]} for r in rows),
                key=lambda r: -r["errors"],
            ),
        }, indent=2))
        return 0

    print(f"TypeScript conversion readiness - {len(rows)} front-end files, "
          f"{len(converted)} already .ts\n")
    mode = "lenient (check config)" if LENIENT else "strict (build config - this is the real gate)"
    print(f"checkJs errors: {total} across {len(dirty)} files   [{mode}]")
    print("(tsconfig.check.json has checkJs:false, so none of this is enforced today)\n")

    print("By cause - what each bucket costs to clear:")
    for cause, count in causes.most_common():
        share = count * 100 // max(total, 1)
        print(f"  {cause:<24} {count:>5}  {share:>2}%  {bar(count)}")
    print()

    print("Top error codes:")
    for code, count in codes.most_common(args.top):
        print(f"  TS{code[2:]:<6} {count:>5}")
    print()

    declare = causes["undeclared-identifier"] + causes["undeclared-window-global"] + causes["lit-untyped"]
    element = causes["untyped-dom-element"]
    implicit = causes["implicit-any"]
    judgment = total - declare - element - implicit

    def pct(n: int) -> str:
        return f"{n * 100 // max(total, 1):>2}%"

    print("What it costs to clear, by kind of work:")
    print(f"  declare a symbol (globals.d.ts / Window)   {declare:>5}  {pct(declare)}   batchable, no design decision")
    print(f"  annotate an implicit-any parameter         {implicit:>5}  {pct(implicit)}   per signature, no design decision")
    print(f"  narrow a querySelector result type        {element:>5}  {pct(element)}   one pattern, mostly codemodable")
    print(f"  actual judgment / design decisions         {judgment:>5}  {pct(judgment)}")
    print()
    print(f"  {implicit + declare + element} of {total} "
          f"({(implicit + declare + element) * 100 // max(total, 1)}%) are mechanical. "
          f"The {implicit} implicit-any errors are the single largest block and are one repeated pattern.")
    print()

    print("Files with most errors:")
    for row in sorted(dirty, key=lambda r: -r["errors"])[:args.top]:
        lit = " lit" if row["lit"] else ""
        print(f"  {row['errors']:>4}  {row['path']}  ({row['lines']} lines{lit})")

    if total == 0:
        print("\ncheckJs is clean. `python tools/ts_convert.py sweep` can start the "
              "@ts-check rollout.")
    return 1 if total else 0


def cmd_list(args) -> int:
    rows = build_index()
    if args.convertible:
        rows = [r for r in rows if r["ext"] == ".js" and not r["has_sibling_ts"]]
    if args.clean:
        rows = [r for r in rows if r["errors"] == 0]
    key = args.sort
    rows.sort(key=lambda r: -(r[key] if isinstance(r[key], int) else 0))

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"{'errors':>7} {'lines':>6}  flags  path")
    for row in rows[:args.limit]:
        flags = "".join([
            "L" if row["lit"] else "-",
            "T" if row["ts_check"] else "-",
            "S" if row["has_sibling_ts"] else "-",
        ])
        print(f"{row['errors']:>7} {row['lines']:>6}  {flags:<5}  {row['path']}")
    print(f"\n{len(rows)} files.  flags: L=uses window.Lit  T=@ts-check  S=sibling .ts exists")
    return 0


def cmd_plan(args) -> int:
    path = rel_of(args.path)
    if not path.exists():
        sys.exit(f"error: {path} does not exist")
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(REPO_ROOT).as_posix()

    findings = [f for f in collect() if f.path == rel]
    causes = Counter(f.cause for f in findings)
    undeclared = sorted({f.subject for f in findings if f.cause == "undeclared-identifier"})
    window_globals = sorted({f.subject for f in findings if f.cause == "undeclared-window-global"})
    dom_props = Counter(f.subject for f in findings if f.cause == "untyped-dom-element")

    print(f"{rel}  ({len(text.splitlines())} lines)\n")
    print(f"  checkJs errors      {len(findings)}")
    for cause, count in causes.most_common():
        print(f"    {cause:<24} {count:>4}")
    print(f"  header block        {'present' if header_of(text) else 'MISSING'}")
    print(f"  uses window.Lit     {uses_lit(text)}")
    print(f"  @ts-check           {has_ts_check(path)}")
    if dom_props:
        print(f"  element properties  {', '.join(f'{k} x{v}' for k, v in dom_props.most_common(8))}")
    if undeclared:
        print(f"\n  needs in globals.d.ts ({len(undeclared)}): {', '.join(undeclared)}")
    if window_globals:
        print(f"  needs on Window ({len(window_globals)}): {', '.join(window_globals)}")

    print()
    if not findings:
        print("  Ready to convert: no type errors. "
              "`convert --apply` will rename and rebuild.")
    else:
        print("  Not ready. The rename alone will fail the build "
              "(`noEmitOnError: true` in tsconfig.json).")
        if undeclared or window_globals:
            print("  Step 1: declare the symbols above, or widen a local type instead.")
        if dom_props:
            print(f"  Step 2: {sum(dom_props.values())} element-property accesses need a narrowed "
                  "querySelector result.")
    return 0


def header_survived(ts_path: Path) -> tuple[bool, str]:
    """Did ``@module`` make it into the emitted ``.js``?

    tsc drops a file's leading JSDoc when the first statement is type-only (an
    ``interface`` or ``type`` alias), because the JSDoc is attached to a node
    that emits nothing. ``js_module_index.py`` reads ``@module`` out of the
    *emitted* .js, so a conversion can silently strip the module contract while
    looking perfectly correct in the .ts. Verified with a five-case probe; the
    fix is to keep a value declaration first.
    """
    emitted = ts_path.with_suffix(".js")
    if not emitted.exists():
        return False, "emitted .js is missing"
    if "@module" not in ts_path.read_text(encoding="utf-8"):
        return True, "source has no @module header"
    if "@module" in emitted.read_text(encoding="utf-8"):
        return True, "header preserved"
    return False, ("@module is in the .ts but NOT in the emitted .js — the first "
                   "statement is probably type-only; move a value declaration above it")


def cmd_convert(args) -> int:
    path = rel_of(args.path)
    if path.suffix != ".js":
        sys.exit(f"error: {path} is not a .js file")
    if not path.exists():
        sys.exit(f"error: {path} does not exist")
    target = path.with_suffix(".ts")
    if target.exists():
        sys.exit(f"error: {target} already exists - already converted")

    text = path.read_text(encoding="utf-8")
    header = header_of(text)
    rel = path.relative_to(REPO_ROOT).as_posix()
    plan = [f for f in collect() if f.path == rel]

    print(f"{rel} -> {target.relative_to(REPO_ROOT).as_posix()}")
    print(f"  header block   {'preserved (' + str(len(header)) + ' lines)' if header else 'MISSING - js_module_index.py will fail'}")
    print(f"  checkJs errors {len(plan)}")
    if plan:
        counts = Counter(f.cause for f in plan)
        print("  " + "; ".join(f"{cause} x{n}" for cause, n in counts.most_common()))
        print("  These do not block the rename - they block the strict build. "
              "Fix them in the .ts.")

    if not args.apply:
        print("\ndry run. Pass --apply to write the .ts, delete the .js and rebuild.")
        return 0

    body = text
    if args.note and not any(GENERATED_NOTE in line for line in header):
        note = f"// {GENERATED_NOTE}: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`."
        if header:
            body = body.replace("\n".join(header), "\n".join(header) + "\n" + note, 1)
        else:
            body = note + "\n" + body

    target.write_text(body, encoding="utf-8", newline="")
    path.unlink()
    print(f"\nwrote {target.relative_to(REPO_ROOT).as_posix()}, removed {rel}")

    code, output = run_tsc(BUILD_CONFIG)
    if code != 0:
        print("build:ts FAILED - the .js was not regenerated. Fix the .ts, then:")
        print("    npm run build:ts")
        print(output[:4000])
        return 1
    print("build:ts ok")

    survived, why = header_survived(target)
    if survived:
        print("header check    ok")
    else:
        print(f"header check    FAILED - {why}")
        print("                `python tools/js_module_index.py --check` will fail until this is fixed.")
        return 1

    print("\nNext: python tools/ts_convert.py check " + rel)
    return 0


def cmd_check(args) -> int:
    """The verification gate from docs/design/typescript-migration.md."""
    steps = []

    steps.append(("build:ts", npm("run", "build:ts")))
    steps.append(("typecheck", npm("run", "typecheck")))
    steps.append(("lint", npm("run", "lint")))

    # The module contract lives in the emitted .js, and tsc will silently drop a
    # leading JSDoc when a file starts with a type-only statement. Checked after
    # build:ts, not before, or it reads the previous emit.
    def emitted_modules() -> list[Path]:
        seen: dict[str, Path] = {}
        for path in args.paths or source_files():
            ts = rel_of(path)
            if ts.suffix != ".ts":
                ts = ts.with_suffix(".ts")
            if not ts.exists() or "vendor" in ts.parts:
                continue
            seen[ts.relative_to(REPO_ROOT).as_posix()] = ts
        return sorted(seen.values(), key=lambda p: p.as_posix())

    steps.append(("module:check", [sys.executable, "tools/js_module_index.py", "--check"]))

    for path in args.paths:
        emitted = rel_of(path).with_suffix(".js")
        if emitted.exists():
            steps.append((f"node --check {emitted.name}", ["node", "--check", str(emitted)]))

    steps.append(("unit", ["node", "tools/unit/run.cjs"]))

    failed = 0
    for name, command in steps:
        proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True)
        status = "ok" if proc.returncode == 0 else f"FAILED ({proc.returncode})"
        print(f"  {name:<24} {status}")
        if proc.returncode != 0:
            failed += 1
            tail = (proc.stdout + proc.stderr).strip().splitlines()
            for line in tail[-25:]:
                print(f"      {line}")
    print()
    lost = []
    for ts in emitted_modules():
        survived, why = header_survived(ts)
        if not survived:
            lost.append(f"{ts.relative_to(REPO_ROOT).as_posix()}: {why}")

    if lost:
        print(f"  {len(lost)} converted file(s) LOST their @module header in the emitted .js:")
        for entry in lost:
            print(f"    - {entry}")
        failed += 1
    else:
        print(f"  header survival  ok ({len(emitted_modules())} converted files)")

    print()
    print("gate failed" if failed else "gate green")
    return 1 if failed else 0


def cmd_sweep(args) -> int:
    """Add ``// @ts-check`` to .js files.

    The only fully automatic step in the migration: no rename, no emit, no
    strict-mode change. It starts type-checking a file in place, so the error
    distribution is visible before a wave is committed.
    """
    rows = [r for r in build_index() if r["ext"] == ".js" and not r["has_sibling_ts"]]
    eligible = [r for r in rows if not r["ts_check"] and r["errors"] <= args.max_errors]
    skipped = [r for r in rows if not r["ts_check"] and r["errors"] > args.max_errors]

    print(f"{len(eligible)} of {len(rows)} files at or under --max-errors={args.max_errors} "
          f"and not yet opted in")
    print(f"{len(skipped)} files exceed the threshold\n")

    if args.report_only or not args.apply:
        for row in eligible[: args.limit]:
            print(f"  would add @ts-check  {row['path']}  ({row['errors']} errors)")
        if not args.apply:
            print("\ndry run. Pass --apply to write.")
        return 0

    written = 0
    for row in eligible:
        path = REPO_ROOT / row["path"]
        text = path.read_text(encoding="utf-8")
        path.write_text("// @ts-check\n" + text, encoding="utf-8", newline="")
        written += 1
        print(f"  @ts-check  {row['path']}")
    print(f"\nwrote {written} files")
    print("Now `npm run typecheck` reports these. Fix or raise --max-errors deliberately.")
    return 0


# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lenient", action="store_true",
                        help="probe with the lenient check config instead of the strict build; "
                             "flatters readiness, do not plan waves from it")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("report", help="error distribution across the corpus")
    p.add_argument("--json", action="store_true")
    p.add_argument("--top", type=int, default=15)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("list", help="per-file conversion readiness")
    p.add_argument("--sort", default="errors", choices=["errors", "lines", "path"])
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--convertible", action="store_true", help="only .js with no sibling .ts")
    p.add_argument("--clean", action="store_true", help="only files with zero errors")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("plan", help="what one file needs before it can convert")
    p.add_argument("path")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("convert", help="header-preserving .js -> .ts rename")
    p.add_argument("path")
    p.add_argument("--apply", action="store_true", help="write the .ts and delete the .js")
    p.add_argument("--note", action="store_true", default=True,
                   help="prepend a generated-file note to the header (default)")
    p.add_argument("--no-note", dest="note", action="store_false")
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("check", help="the migration verification gate")
    p.add_argument("paths", nargs="*", help="converted files, to node --check the emitted .js")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("sweep", help="add // @ts-check to .js files")
    p.add_argument("--max-errors", type=int, default=0)
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--report-only", action="store_true")
    p.set_defaults(func=cmd_sweep)

    args = parser.parse_args()
    global LENIENT
    LENIENT = args.lenient
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
