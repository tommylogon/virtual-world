#!/usr/bin/env python3
"""Dev-task helper: allocate ids, scaffold, move between status folders, check.

Git and the task files stay the single source of truth — this tool only
allocates the next id, writes a template, moves files with ``git mv`` and
updates the ``status:`` frontmatter when present, and validates that ids,
filenames and the folder each file lives in agree.

Usage:
    python tools/tasks.py next-id [--kind task|bug]
    python tools/tasks.py new --area characters --title "Nicknames" [--kind task] [--priority medium] [--status todo] [--related "..."] [--goal "..."]
    python tools/tasks.py move --id 447 [--kind task] --status review
    python tools/tasks.py list [--status todo] [--area ui] [--kind task]
    python tools/tasks.py validate [--quiet]
    python tools/tasks.py index [--clear]
    python tools/tasks.py help [command]
    python tools/tasks.py

Running with no command opens an interactive menu loop. Subcommands stay
one-shot so scripts can call them.

Folder is authoritative for status: todo / inprogress / review / done / cancelled.
A file's own ``status:`` frontmatter is advisory and is updated on ``move``.

Frontmatter is read as real YAML (``PyYAML``, with a small fallback when it is
not installed), so a list value stays a list. Dependency keys are
``related``, ``blocks``, ``blocked_by``, ``supersedes``, ``parent``,
``children`` and ``depends_on``; each takes a list or a bare id. Parsed
frontmatter and titles are cached in ``.tasks-index.json`` keyed by mtime+size.
That cache is derived only -- it changes no result, and ``index --clear``
deletes it.

On Windows, ``tools\\tasks.bat`` forwards to this script with the same
arguments, e.g. ``tools\\tasks.bat help`` or ``tasks list --status todo``.
Run ``help`` for the full guide, or ``help <command>`` for a single command.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml  # real YAML, so lists and quoted values survive
except ImportError:  # pragma: no cover - fallback keeps the tool usable
    yaml = None

# ── layout ───────────────────────────────────────────────────────────────

STATUSES = ("todo", "inprogress", "review", "done", "cancelled")
KINDS = ("task", "bug")
TERMINAL_STATUSES = {"done", "cancelled"}
ID_RE = re.compile(r"^(?P<kind>task|bug)-(?P<num>\d+)-(?P<slug>[^/]+)\.md$")
REF_RE = re.compile(r"\b(task|bug)-(\d+)\b", re.IGNORECASE)

# "# task-568: Town cells" -> "Town cells". Also matches "Bug 22 — ...".
TITLE_ID_PREFIX_RE = re.compile(
    r"^\s*(?:task|bug)\s*-?\s*\d+\s*[:\u2014\u2013-]\s*", re.IGNORECASE)

INDEX_NAME = ".tasks-index.json"
INDEX_VERSION = 2


def default_root() -> Path:
    return Path(__file__).resolve().parent.parent / "docs" / "virtualWorld" / "dev_tasks"


# ── model ────────────────────────────────────────────────────────────────


class Entry:
    __slots__ = ("path", "kind", "num", "slug", "status", "area",
                 "_fm", "_fm_error", "_title")

    def __init__(self, path: Path, root: Path, fm: Optional[Dict] = None,
                 fm_error: str = "", title: Optional[str] = None):
        self.path = path
        m = ID_RE.match(path.name)
        self.kind = m.group("kind") if m else ""
        self.num = int(m.group("num")) if m else -1
        self.slug = m.group("slug") if m else path.stem
        rel = path.relative_to(root)
        parts = rel.parts
        self.status = parts[0] if parts and parts[0] in STATUSES else ""
        # area = first directory under the status dir, if any
        self.area = parts[1] if self.status and len(parts) > 2 else ""
        self._fm = fm
        self._fm_error = fm_error
        self._title = title

    @property
    def id(self) -> str:
        return f"{self.kind}-{self.num}" if self.kind else self.path.name

    def frontmatter(self) -> Dict:
        """Parsed frontmatter, loading it from disk if not cached."""
        if self._fm is None:
            self._fm, self._fm_error = parse_frontmatter(read_text(self.path))
        return self._fm

    def frontmatter_error(self) -> str:
        """Non-empty when a frontmatter block exists but does not parse."""
        if self._fm is None:
            self._fm, self._fm_error = parse_frontmatter(read_text(self.path))
        return self._fm_error

    def title(self) -> str:
        if self._title is None:
            self._title = self._compute_title()
        return self._title

    def _compute_title(self) -> str:
        fm = self.frontmatter()
        raw = fm.get("title")
        if not raw:
            for line in read_text(self.path).splitlines():
                if line.startswith("# "):
                    raw = line[2:].strip()
                    break
        # A heading of only "Bug 12:" is a real thing in the tree; fall back
        # to the slug rather than printing an empty column.
        cleaned = clean_title(str(raw)) if raw else ""
        return cleaned or self.slug.replace("-", " ")


def clean_title(raw: str) -> str:
    """Drop a leading ``task-123:``/``Bug 12 —`` prefix and tidy whitespace."""
    return re.sub(r"\s+", " ", TITLE_ID_PREFIX_RE.sub("", raw)).strip()


def read_text(path: Path) -> str:
    # utf-8-sig transparently drops a leading BOM. 65 task files carry one,
    # and without this their frontmatter is invisible to every reader.
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _split_frontmatter(text: str) -> Optional[str]:
    """Return the raw frontmatter block, or None if the file has none."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end]


def _parse_frontmatter_fallback(block: str) -> Dict:
    """Minimal ``key: value`` / ``key: [a, b]`` reader for envs without PyYAML."""
    out: Dict = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            out[key.strip()] = [i for i in items if i]
        else:
            out[key.strip()] = value.strip("'\"")
    return out


def _jsonable(value):
    """Coerce YAML-native types to JSON-safe ones.

    PyYAML hands back ``datetime.date`` for ``created: 2026-08-17``, which the
    index cache cannot store. Normalising here rather than at dump time keeps
    a cold run and a cached run returning the *same* types.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


def parse_frontmatter(text: str) -> Tuple[Dict, str]:
    """Return ``(data, error)``.

    ``error`` is non-empty only when a frontmatter block is present but
    unparseable — the data is still returned as best-effort so the file stays
    usable, but ``validate`` reports the error rather than hiding it.
    """
    block = _split_frontmatter(text)
    if block is None:
        return {}, ""
    if yaml is None:
        return _jsonable(_parse_frontmatter_fallback(block)), ""
    try:
        data = yaml.safe_load(block)
    except Exception as exc:
        return _jsonable(_parse_frontmatter_fallback(block)), (
            f"{type(exc).__name__}: {str(exc).splitlines()[0]}")
    if data is None:
        return {}, ""
    if not isinstance(data, dict):
        return {}, f"frontmatter is {type(data).__name__}, expected a mapping"
    return _jsonable({str(k): v for k, v in data.items()}), ""


def _as_refs(value) -> List[str]:
    """Normalise a dependency value into a list of 'task-N' ids.

    Accepts a YAML list, a single id, or a comma/space separated string, so
    ``blocks: task-570`` and ``blocks: [task-570]`` behave the same.
    """
    if value is None:
        return []
    items = value if isinstance(value, list) else re.split(r"[,\s]+", str(value))
    out: List[str] = []
    for item in items:
        for kind, num in REF_RE.findall(str(item)):
            out.append(f"{kind.lower()}-{int(num)}")
    return out


def _parse_one(path: Path, root: Path) -> Tuple[Entry, int, int]:
    e = Entry(path, root)
    e.frontmatter()          # populate _fm / _fm_error
    e.title()                # populate _title
    st = path.stat()
    return e, st.st_mtime_ns, st.st_size


def _index_path(root: Path) -> Path:
    return root / INDEX_NAME


def _load_index(root: Path) -> Optional[Dict[str, List]]:
    p = _index_path(root)
    if not p.exists():
        return None
    try:
        blob = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if blob.get("version") != INDEX_VERSION:
        return None
    recs = blob.get("entries")
    return recs if isinstance(recs, dict) else None


def _save_index(root: Path, recs: Dict[str, List]) -> None:
    payload = {"version": INDEX_VERSION, "entries": recs}
    target = _index_path(root)
    tmp = target.with_suffix(".json.tmp")
    try:
        # Write-and-rename so a crash cannot leave a half-written cache. A
        # corrupt file is survivable anyway (_load_index returns None), but a
        # torn one still costs a full rescan on every command.
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(target)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def _rescan(root: Path, paths: List[Path], save: bool) -> List[Entry]:
    out: List[Entry] = []
    new_recs: Dict[str, List] = {}
    for p in paths:
        try:
            e, mtime_ns, size = _parse_one(p, root)
        except OSError:
            continue  # vanished between rglob and stat
        out.append(e)
        new_recs[str(p.relative_to(root))] = [
            mtime_ns, size, e.kind, e.num, e.slug, e.status, e.area,
            e.title(), e.frontmatter(), e.frontmatter_error(),
        ]
    if save:
        _save_index(root, new_recs)
    return out


def _cache_hit(recs: Dict[str, List], paths: List[Path], root: Path) -> Optional[List[Entry]]:
    """Return cached entries only if every record is present *and* current.

    A record must also be well-shaped: a hand-edited or externally rewritten
    cache must rescan rather than hand a wrong type to a caller.
    """
    if set(recs) != {str(p.relative_to(root)) for p in paths}:
        return None
    try:
        for p in paths:
            rec = recs[str(p.relative_to(root))]
            st = p.stat()
            if rec[0] != st.st_mtime_ns or rec[1] != st.st_size:
                return None
            if not isinstance(rec[7], str) or not isinstance(rec[8], dict):
                return None
    except (OSError, IndexError, TypeError, KeyError):
        return None
    return [Entry(root / rel, root, fm=rec[8], fm_error=rec[9], title=rec[7])
            for rel, rec in recs.items()]


def iter_entries(root: Path, use_cache: bool = True) -> List[Entry]:
    """Every markdown file under ``root`` as an Entry.

    Parsed frontmatter and titles are cached on disk, keyed by mtime+size, so
    repeated commands do not re-read ~650 files. The cache is derived only:
    delete it, or pass ``use_cache=False``, and the result is identical.
    """
    paths = sorted(root.rglob("*.md"))
    if not use_cache:
        return _rescan(root, paths, save=False)
    if (hit := _cache_hit(_load_index(root) or {}, paths, root)) is not None:
        return hit
    return _rescan(root, paths, save=True)


# ── git ──────────────────────────────────────────────────────────────────


def _git(args: List[str], cwd: Path) -> bool:
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd),
                           capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


def git_mv(src: Path, dst: Path, root: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    return _git(["mv", str(src), str(dst)], cwd=root)


# ── commands ─────────────────────────────────────────────────────────────


def next_id(root: Path, kind: str) -> int:
    nums = [e.num for e in iter_entries(root) if e.kind == kind and e.num >= 0]
    return (max(nums) + 1) if nums else 1


def find_by_id(entries: List[Entry], kind: str, num: int) -> List[Entry]:
    return [e for e in entries if e.kind == kind and e.num == num]


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "untitled"


def cmd_next_id(args) -> int:
    print(next_id(args.root, args.kind))
    return 0


def cmd_new(args) -> int:
    entries = iter_entries(args.root)
    num = next_id(args.root, args.kind)
    slug = slugify(args.title)
    status = args.status
    area_dir = args.root / status / args.area
    path = area_dir / f"{args.kind}-{num}-{slug}.md"

    if [e for e in entries if e.kind == args.kind and e.num == num]:
        print(f"error: {args.kind}-{num} already exists", file=sys.stderr)
        return 1
    if path.exists() and not args.force:
        print(f"error: {path} already exists (use --force)", file=sys.stderr)
        return 1

    area_dir.mkdir(parents=True, exist_ok=True)
    today = _dt.date.today().isoformat()
    related = args.related or ""
    goal = args.goal or "TODO"
    heading = f"{args.kind}-{num}"
    body = f"""---
type: {"bug" if args.kind == "bug" else "task"}
status: {status}
area: {args.area}
priority: {args.priority}
---

# {heading}: {args.title}

**Filed:** {today}
**Related:** {related}

## Goal

{goal}

## Acceptance

- TODO
"""
    path.write_text(body, encoding="utf-8")
    print(str(path))
    return 0


def _rewrite_status(path: Path, status: str) -> None:
    text = read_text(path)
    if not text.startswith("---"):
        return
    end = text.find("\n---", 3)
    if end == -1:
        return
    head = text[3:end]
    if re.search(r"^status:\s*.*$", head, flags=re.MULTILINE):
        head = re.sub(r"^status:\s*.*$", f"status: {status}", head, count=1, flags=re.MULTILINE)
    else:
        head = head.rstrip("\n") + f"\nstatus: {status}"
    path.write_text("---" + head + text[end:], encoding="utf-8")


def cmd_move(args) -> int:
    entries = find_by_id(iter_entries(args.root), args.kind, args.id)
    if not entries:
        print(f"error: no {args.kind}-{args.id} found", file=sys.stderr)
        return 1
    if len(entries) > 1:
        for e in entries:
            print(f"  {e.path}", file=sys.stderr)
        print(f"error: {args.kind}-{args.id} is ambiguous", file=sys.stderr)
        return 1

    src = entries[0].path
    if not entries[0].status:
        print(f"error: {src} is not under a status folder", file=sys.stderr)
        return 1
    rel = src.relative_to(args.root / entries[0].status)
    dst = args.root / args.status / rel

    if src.resolve() == dst.resolve():
        print(f"already in {args.status}: {src}")
        return 0

    if not git_mv(src, dst, args.root):
        shutil.move(str(src), str(dst))
    _rewrite_status(dst, args.status)
    print(f"{src}  ->  {dst}")
    return 0


def cmd_index(args) -> int:
    p = _index_path(args.root)
    if args.clear:
        if p.exists():
            p.unlink()
            print(f"removed {p}")
        else:
            print("no index present")
        return 0
    entries = _rescan(args.root, sorted(args.root.rglob("*.md")), save=True)
    if not p.exists():
        print("warn: could not write the index (read-only tree?)", file=sys.stderr)
    print(f"{len(entries)} files indexed -> {p}")
    return 0


def cmd_list(args) -> int:
    rows = [e for e in iter_entries(args.root) if e.kind]
    if args.status:
        rows = [e for e in rows if e.status == args.status]
    if args.area:
        rows = [e for e in rows if e.area == args.area]
    if args.kind:
        rows = [e for e in rows if e.kind == args.kind]
    rows.sort(key=lambda e: (e.kind, e.num))
    for e in rows:
        print(f"{e.id:<10} {e.status:<10} {e.area:<12} {e.title()}")
    return 0


def cmd_validate(args) -> int:
    entries = iter_entries(args.root)
    errors: List[str] = []
    warnings: List[str] = []

    # Duplicate ids
    seen: Dict[Tuple[str, int], List[Entry]] = {}
    for e in entries:
        if e.kind:
            seen.setdefault((e.kind, e.num), []).append(e)
    for (kind, num), group in seen.items():
        if len(group) > 1:
            where = ", ".join(str(g.path) for g in group)
            if all(g.status in TERMINAL_STATUSES for g in group):
                # Documented historical collisions (dev_Task_sequence.md
                # "Known historical duplicates") are left as-is.
                warnings.append(f"known historical duplicate id {kind}-{num} (terminal, left as-is): {where}")
            else:
                errors.append(f"duplicate id {kind}-{num}: {where}")

    # Filename / folder sanity
    known_ids = {f"{k}-{n}" for (k, n) in seen}
    for e in entries:
        if e.path.name.startswith(("task-", "bug-")) and not e.kind:
            warnings.append(f"filename does not match {ID_RE.pattern}: {e.path}")
        if e.kind and not e.status:
            warnings.append(f"not under a status folder: {e.path}")

        fm_err = e.frontmatter_error()
        if fm_err:
            errors.append(f"malformed frontmatter ({fm_err}): {e.path}")

        fm_status = e.frontmatter().get("status")
        if fm_status is not None and e.status and _norm(str(fm_status)) != _norm(e.status):
            warnings.append(
                f"frontmatter status '{fm_status}' != folder '{e.status}': {e.path}")

        # Referenced ids. Prose lines and frontmatter lists both count.
        lines = read_text(e.path).splitlines()
        for key in ("related", "blocks", "blocked_by", "supersedes", "parent",
                    "children", "depends_on"):
            for ref in _as_refs(e.frontmatter().get(key)):
                if ref not in known_ids:
                    warnings.append(f"dangling {key} reference {ref} in {e.path.name}")
        for line in lines:
            if re.match(r"\*\*(Related|Supersedes|Blocks|Depends on|Blocked by|Parent|Children)\b", line):
                for kind, num in REF_RE.findall(line):
                    ref = f"{kind.lower()}-{int(num)}"
                    if ref not in known_ids:
                        warnings.append(f"dangling reference {ref} in {e.path.name}")

    if not args.quiet:
        for w in warnings:
            print(f"warn: {w}")
    for err in errors:
        print(f"error: {err}", file=sys.stderr)
    print(f"\n{len(entries)} files, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def _norm(status: str) -> str:
    return status.strip().lower().replace("_", "").replace("-", "")


# ── cli ──────────────────────────────────────────────────────────────────


HELP_TEXT = """\
Virtual World dev-task helper — allocate ids, scaffold, move, list, validate.

Task and bug files live under docs/virtualWorld/dev_tasks/<status>/<area>/.
The FOLDER is authoritative for status; the `status:` frontmatter is
advisory and is rewritten on `move`. Moves use `git mv` when possible.

Commands:
    next-id   print the next free id for a kind
    new       scaffold a new task/bug file from the template
    move      move a file between status folders (updates frontmatter)
    list      list tasks/bugs, optionally filtered
    validate  check ids, filenames, folders and cross-references
    index     rebuild or clear the derived frontmatter cache
    help      show this guide, or `help <command>` for one command

Run with no command for an interactive menu (type `q` to quit).

Statuses: todo / inprogress / review / done / cancelled
Kinds:    task / bug
Areas:    bugs characters conditions docs gameplay graph items library
          refactor testing triggers ui world

Typical flow:
  python tools/tasks.py next-id
  python tools/tasks.py new --area gameplay --title "Pooled resource nodes" --goal "..."
  python tools/tasks.py move --id 504 --status inprogress
  python tools/tasks.py move --id 504 --status review
  python tools/tasks.py move --id 504 --status done
  python tools/tasks.py validate

On Windows the same arguments work through the wrapper, e.g.
  tools\\tasks.bat help
  tools\\tasks.bat list --status todo

Run `help <command>` (or `--help`) for the flags of a single command.
"""

HELP_TOPICS = {
    "next-id": """\
next-id [--kind task|bug]   (default kind: task)

Print the next free numeric id for the given kind by scanning every file
under the dev_tasks root. Does not create or modify anything.

  python tools/tasks.py next-id
  python tools/tasks.py next-id --kind bug
""",
    "new": """\
new --area AREA --title TITLE [--kind task|bug] [--priority medium]
    [--status todo] [--related "..."] [--goal "..."] [--force]

Scaffold a new file at <root>/<status>/<area>/<kind>-<num>-<slug>.md with the
frontmatter and Goal/Acceptance template filled in. The id comes from
`next-id`; the slug is derived from the title.

  --area      topic folder, e.g. gameplay, ui, graph (required)
  --title     human title; also sets the H1 and slug (required)
  --kind      task (default) or bug
  --priority  free text, default medium
  --status    starting folder, default todo
  --related   value for the **Related:** line, e.g. task-409
  --goal      text under ## Goal (defaults to TODO)
  --force     overwrite if the target path already exists

  python tools/tasks.py new --area ui --title "Compass polish" --kind task
""",
    "move": """\
move --id N [--kind task|bug] --status STATUS

Move an existing file from its current status folder to another, preserving
the area subfolder, via `git mv` (falls back to a plain move), then rewrite the
`status:` frontmatter to match. The folder is authoritative.

  --id      numeric id without the kind prefix, e.g. 447
  --kind    task (default) or bug
  --status  target status (required)

  python tools/tasks.py move --id 447 --status review
  python tools/tasks.py move --id 12 --kind bug --status done
""",
    "list": """\
list [--status STATUS] [--area AREA] [--kind task|bug]

Print "id status area title" for matching files. All filters are optional and
combine with AND.

  python tools/tasks.py list
  python tools/tasks.py list --status todo
  python tools/tasks.py list --area ui --kind task
""",
    "validate": """\
validate [--quiet]

Check the whole tree: duplicate ids, filenames that do not parse, files outside
a status folder, frontmatter/folder status mismatches, and dangling
Related/Blocks/Depends-on references. Historical terminal duplicates are
reported as warnings, everything else as errors (exit code 1).

  --quiet   suppress warnings, print only errors and the summary

  python tools/tasks.py validate
  python tools/tasks.py validate --quiet
""",
    "index": """\
index [--clear]

The tree is re-read and the derived frontmatter cache (`.tasks-index.json`) is
rewritten. The cache is only ever a speed-up: it is keyed by mtime+size and
deleting it changes no result. `list` and `validate` maintain it automatically;
you only need this after an external tool rewrote many files at once.

  --clear   delete the cache rather than rebuild it

  python tools/tasks.py index
  python tools/tasks.py index --clear
""",
    "help": """\
help [command]

Show the full guide, or one command's usage and flags.

  python tools/tasks.py help
  python tools/tasks.py help new
""",
}


def cmd_help(args) -> int:
    if args.topic:
        print(HELP_TOPICS[args.topic], end="")
    else:
        print(HELP_TEXT, end="")
    return 0


# ── interactive ──────────────────────────────────────────────────────────


INTERACTIVE_MENU = """\
Dev-task helper — interactive mode

  1) next-id    print the next free id
  2) new        scaffold a new task/bug
  3) move       move between status folders
  4) list       list tasks/bugs
  5) validate   check ids, filenames, folders and refs
  6) index      rebuild/clear the frontmatter cache
  7) help       show the full guide
  q) quit
"""


def _menu_input(prompt: str, default: str = "") -> str:
    try:
        value = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0)
    return value or default


def _menu_choice(prompt: str, choices, default: str) -> str:
    while True:
        raw = _menu_input(f"{prompt} [{'/'.join(choices)}] ({default}): ", default).lower()
        if raw in choices:
            return raw
        print(f"  please enter one of: {', '.join(choices)}")


def _menu_optional_choice(prompt: str, choices):
    while True:
        raw = _menu_input(f"{prompt} [{'/'.join(choices)}] (blank = any): ").lower()
        if not raw:
            return None
        if raw in choices:
            return raw
        print(f"  please enter one of: {', '.join(choices)} (or blank)")


def _menu_int(prompt: str) -> int:
    while True:
        raw = _menu_input(prompt)
        if raw.isdigit():
            return int(raw)
        print("  please enter a number")


def cmd_interactive(args) -> int:
    print(f"dev_tasks root: {args.root}")
    while True:
        print()
        print(INTERACTIVE_MENU, end="")
        choice = _menu_input("choice: ").lower()

        if choice in ("q", "quit", "exit"):
            return 0
        if choice in ("1", "next-id"):
            kind = _menu_choice("kind", KINDS, "task")
            cmd_next_id(argparse.Namespace(root=args.root, kind=kind))
        elif choice in ("2", "new"):
            kind = _menu_choice("kind", KINDS, "task")
            area = _menu_input("area (e.g. gameplay, ui): ")
            if not area:
                print("  area is required")
                continue
            title = _menu_input("title: ")
            if not title:
                print("  title is required")
                continue
            status = _menu_choice("status", STATUSES, "todo")
            priority = _menu_input("priority (medium): ", "medium")
            related = _menu_input("related (blank = none): ")
            goal = _menu_input("goal (blank = TODO): ")
            cmd_new(argparse.Namespace(
                root=args.root, kind=kind, area=area, title=title, status=status,
                priority=priority, related=related, goal=goal, force=False))
        elif choice in ("3", "move"):
            kind = _menu_choice("kind", KINDS, "task")
            num = _menu_int(f"{kind} id: ")
            status = _menu_choice("status", STATUSES, "todo")
            cmd_move(argparse.Namespace(root=args.root, kind=kind, id=num, status=status))
        elif choice in ("4", "list"):
            status = _menu_optional_choice("status", STATUSES)
            area = _menu_input("area (blank = any): ") or None
            kind = _menu_optional_choice("kind", KINDS)
            cmd_list(argparse.Namespace(root=args.root, status=status, area=area, kind=kind))
        elif choice in ("5", "validate"):
            cmd_validate(argparse.Namespace(root=args.root, quiet=False))
        elif choice in ("6", "index"):
            cmd_index(argparse.Namespace(root=args.root, clear=False))
        elif choice in ("7", "help"):
            cmd_help(argparse.Namespace(topic=None))
        else:
            print("  unknown choice")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Dev-task helper (allocate, scaffold, move, validate).")
    p.add_argument("--root", type=Path, default=default_root(),
                   help="dev_tasks root (default: docs/virtualWorld/dev_tasks)")
    p.set_defaults(func=cmd_interactive)
    sub = p.add_subparsers(dest="cmd")

    n = sub.add_parser("next-id", help="print the next free id")
    n.add_argument("--kind", choices=KINDS, default="task")
    n.set_defaults(func=cmd_next_id)

    nw = sub.add_parser("new", help="scaffold a new task file")
    nw.add_argument("--area", required=True)
    nw.add_argument("--title", required=True)
    nw.add_argument("--kind", choices=KINDS, default="task")
    nw.add_argument("--priority", default="medium")
    nw.add_argument("--status", choices=STATUSES, default="todo")
    nw.add_argument("--related", default="")
    nw.add_argument("--goal", default="")
    nw.add_argument("--force", action="store_true")
    nw.set_defaults(func=cmd_new)

    mv = sub.add_parser("move", help="move a task between status folders")
    mv.add_argument("--id", type=int, required=True)
    mv.add_argument("--kind", choices=KINDS, default="task")
    mv.add_argument("--status", choices=STATUSES, required=True)
    mv.set_defaults(func=cmd_move)

    ls = sub.add_parser("list", help="list tasks")
    ls.add_argument("--status", choices=STATUSES)
    ls.add_argument("--area")
    ls.add_argument("--kind", choices=KINDS)
    ls.set_defaults(func=cmd_list)

    v = sub.add_parser("validate", help="check ids, filenames, folders and refs")
    v.add_argument("--quiet", action="store_true")
    v.set_defaults(func=cmd_validate)

    ix = sub.add_parser("index", help="rebuild or clear the derived frontmatter cache")
    ix.add_argument("--clear", action="store_true", help="delete the cache instead")
    ix.set_defaults(func=cmd_index)

    hp = sub.add_parser("help", help="show the guide, or help for one command")
    hp.add_argument("topic", nargs="?", choices=sorted(HELP_TOPICS))
    hp.set_defaults(func=cmd_help)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Windows consoles default to cp1252 and crash on titles containing arrows,
    # em-dashes or curly quotes. Force UTF-8 on the output streams.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
