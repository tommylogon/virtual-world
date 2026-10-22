"""Catch a JSON content file that lost its trailing newline in this worktree.

Why this exists
---------------
``routes/helpers.py:save_registry`` rewrites every entry it is handed, and a
caller that passes the whole registry (materializing one contained item does
exactly that) used to rewrite all 225 item files to change one of them.
``json.dump`` writes no trailing newline, so each rewrite also stripped the
final byte from files nobody edited. The symptom was 207 item files showing a
one byte diff (``\\ No newline at end of file``) after a single item action.

``save_registry`` now appends the newline and skips files whose serialized
content has not changed, so the churn cannot come from there again.

This check is the regression guard, not a style crusade. The repo contains
thousands of JSON files that have never had a trailing newline, and rewriting
all of them would be a worse diff than the bug. So it only flags a file that
**had** the byte at ``HEAD`` and lost it in the working tree. That is exactly
the shape of the silent churn: an untouched file changing because something
else saved the registry.

Usage
-----
    python tools/json_newline_check.py --check     # exit 1 on regressions
    python tools/json_newline_check.py --fix       # restore the byte
    python tools/json_newline_check.py --report    # summary counts

Save files and autosaves are excluded: they are rewritten every turn and are
not authored content.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATHS = ("data/library", "data/scenarios")


def _changed_json(paths):
    """Return worktree .json paths under ``paths`` that git reports as changed.

    Only changed paths are examined: a byte that has been absent since the file
    was created is not a regression, and scanning 3900 files to say so is a waste
    of everyone's time.
    """
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no", "--"] + list(paths),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if out.returncode != 0:
        print(f"git status failed: {out.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    changed = []
    for line in out.stdout.splitlines():
        if len(line) < 4:
            continue
        relative_path = line[3:].strip().strip('"')
        if relative_path.endswith(".json"):
            changed.append(relative_path.replace("\\", "/"))
    return changed


def _worktree_lacks_newline(relative_path):
    path = os.path.join(REPO_ROOT, relative_path)
    try:
        with open(path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            return fh.read(1) != b"\n"
    except OSError:
        return False


def _head_has_newline(relative_path):
    out = subprocess.run(
        ["git", "show", f"HEAD:{relative_path}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if out.returncode != 0 or not out.stdout:
        return False
    return out.stdout.endswith(b"\n")


def _regressions(paths):
    offenders = []
    for relative_path in _changed_json(paths):
        if os.path.exists(os.path.join(REPO_ROOT, relative_path)) and _worktree_lacks_newline(relative_path) and _head_has_newline(relative_path):
            offenders.append(relative_path)
    return offenders


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if a changed file lost its trailing newline")
    parser.add_argument("--fix", action="store_true", help="append the missing trailing newline")
    parser.add_argument("--report", action="store_true", help="print counts grouped by folder")
    parser.add_argument(
        "--paths",
        nargs="+",
        default=list(DEFAULT_PATHS),
        help="paths to scan (default: data/library data/scenarios)",
    )
    args = parser.parse_args(argv)

    if not (args.check or args.fix or args.report):
        parser.error("choose one of --check, --fix, --report")

    offenders = _regressions(args.paths)

    if args.fix:
        for relative_path in offenders:
            with open(os.path.join(REPO_ROOT, relative_path), "ab") as fh:
                fh.write(b"\n")
        print(f"restored the trailing newline on {len(offenders)} changed JSON files")
        return 0

    if args.report:
        print(f"changed JSON files missing a newline they used to have: {len(offenders)}")
        counts = {}
        for relative_path in offenders:
            parts = relative_path.split("/")
            folder = "/".join(parts[:3]) if len(parts) >= 3 else relative_path
            counts[folder] = counts.get(folder, 0) + 1
        for folder, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"  {count:5d}  {folder}")
        return 0

    if offenders:
        print(f"{len(offenders)} changed JSON files lost a trailing newline they have at HEAD:")
        for relative_path in offenders[:20]:
            print(f"  {relative_path}")
        if len(offenders) > 20:
            print(f"  ... and {len(offenders) - 20} more")
        print("This is the save_registry churn. Fix with: python tools/json_newline_check.py --fix")
        return 1

    print("ok: no changed JSON file lost its trailing newline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
