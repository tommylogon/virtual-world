#!/usr/bin/env python3
"""Dev-task helper: allocate ids, scaffold, move between status folders, check.

Git and the task files stay the single source of truth — this tool only
allocates the next id, writes a template, moves files with ``git mv`` and
updates the ``status:`` frontmatter when present, and validates that ids,
filenames and the folder each file lives in agree.

Usage:
    python tools/tasks.py next-id [--kind task|bug]
    python tools/tasks.py new --area characters --title "Nicknames" [--kind task] [--priority medium] [--status todo] [--related "..."] [--goal "..."] [--json @file]
    python tools/tasks.py move --id 447 [--kind task] --status review
    python tools/tasks.py set --id 447 [--priority high] [--section acceptance --value "..."]
    python tools/tasks.py list [--status todo] [--area ui] [--kind task]
    python tools/tasks.py validate [--quiet] [--schema]
    python tools/tasks.py status [--json]
    python tools/tasks.py roadmap [--out PATH]
    python tools/tasks.py graph [--json]
    python tools/tasks.py next [--limit N] [--json]
    python tools/tasks.py backfill [--status S...] [--content] [--write]
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
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, deque
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


# === canonical card schema ==============================================
#
# A card's body is a fixed, ordered set of level-2 sections. The tree grew a
# dozen synonyms for the same idea over time (## Files Affected / ## Files
# Changed / ## Files; ## Verification / ## Testing / ## Tests; ## Goal /
# ## Summary / ## Purpose). The alias tables below fold every one back to a
# canonical heading so `backfill` can normalise a body without reading
# meaning out of it. Order here is the order the writer emits.
CANONICAL_SECTIONS = (
    ("what", "What",
     ("goal", "summary", "purpose", "context", "overview", "description")),
    ("why", "Why",
     ("problem", "motivation", "rationale", "background", "current state", "impact")),
    ("how", "How",
     ("implementation", "approach", "design", "fix", "changes", "plan", "solution")),
    ("verify", "Steps to verify",
     ("verification", "testing", "tests", "test plan", "how to verify",
      "live verification", "how to test")),
    ("acceptance", "Acceptance", ("acceptance criteria", "done when")),
    ("files", "Files",
     ("files affected", "files changed", "files touched", "affected files")),
)

# The `## Steps to verify` section carries the expected and observed outcome:
#   1. <action>
#      - expected: ...
#      - observed: ...
# `backfill` seeds those lines and `validate --strict` requires them on a done
# card, but it never invents the observed value.
SECTION_TITLE_BY_KEY = {key: title for key, title, _ in CANONICAL_SECTIONS}
SECTION_KEY_BY_HEADING = {}
for _key, _title, _aliases in CANONICAL_SECTIONS:
    SECTION_KEY_BY_HEADING[_title.lower()] = _key
    for _alias in _aliases:
        SECTION_KEY_BY_HEADING[_alias.lower()] = _key

DEPENDENCY_KEYS = ("related", "blocks", "blocked_by", "depends_on",
                   "supersedes", "parent", "children")
# Frontmatter keys the schema knows, in the order `new`/`set` emit them.
CANONICAL_FRONTMATTER = ("type", "status", "area", "priority", "horizon",
                         "effort", "goal", "wiki") + DEPENDENCY_KEYS
HORIZONS = ("now", "next", "later")
PRIORITIES = ("low", "medium", "high")
EFFORTS = ("S", "M", "L")

# The template body used by `new` and appended by `backfill` for a missing
# section. Kept here so the two writers cannot drift.
SECTION_STUBS = {
    "what": "TODO",
    "why": "TODO",
    "how": "TODO",
    "verify": "1. TODO\n   - expected: TODO\n   - observed: TODO",
    "acceptance": "- [ ] TODO",
    "files": "- TODO",
}

H2_RE = re.compile(r"^##(?!#)\s*(.+?)\s*$", re.MULTILINE)


def iter_h2(text: str):
    """Yield ``(heading, body)`` for every level-2 section, in file order."""
    marks = list(H2_RE.finditer(text))
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        yield m.group(1).strip(), text[start:end].strip("\n")


def body_sections(text: str) -> Dict[str, str]:
    """Canonical key -> body text, synonyms folded in (first heading wins)."""
    out: Dict[str, str] = {}
    for heading, body in iter_h2(text):
        key = SECTION_KEY_BY_HEADING.get(heading.lower())
        if key and key not in out:
            out[key] = body
    return out


def section_synonyms(text: str):
    """``(heading, canonical key)`` for each level-2 heading that is a synonym
    rather than the canonical title. `backfill` renames these in place."""
    found = []
    for heading, _ in iter_h2(text):
        key = SECTION_KEY_BY_HEADING.get(heading.lower())
        if key and heading != SECTION_TITLE_BY_KEY[key]:
            found.append((heading, key))
    return found


def missing_sections(text: str):
    """Canonical keys the body has no section for, in canonical order."""
    present = body_sections(text)
    return [key for key, _t, _a in CANONICAL_SECTIONS if key not in present]


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


def try_read_text(path: Path) -> str:
    """``read_text`` that returns "" when the file vanished mid-walk.

    The tree is edited concurrently (moves, backfills), so a file can
    disappear between a directory scan and a read; a read-only command must
    skip it rather than crash.
    """
    try:
        return read_text(path)
    except OSError:
        return ""


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


def _load_doc_links():
    """Import tools/doc_links.py whether run as a script or as ``tools.tasks``."""
    try:
        from tools import doc_links
    except ImportError:
        import doc_links  # when tools/ itself is on sys.path
    return doc_links


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


def _load_json_payload(spec: str) -> Dict:
    """Parse a --json argument. ``@path`` reads a file, else it is inline JSON."""
    spec = spec.strip()
    if spec.startswith("@"):
        spec = Path(spec[1:]).read_text(encoding="utf-8-sig")
    data = json.loads(spec)
    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")
    return data


# --- local LLM client (LM Studio / any OpenAI-compatible endpoint) --------
#
# The content backfill authors with the LOCAL model so the pass costs no API
# tokens and runs offline. Defaults point at LM Studio; override with the
# VW_LLM_BASE / VW_LLM_MODEL environment variables or the --llm-base /
# --llm-model flags. Nothing here is imported unless --content is asked for, so
# the read-only commands never touch a network socket.
DEFAULT_LLM_BASE = os.environ.get("VW_LLM_BASE", "http://localhost:1234/v1")
DEFAULT_LLM_MODEL = os.environ.get("VW_LLM_MODEL", "glm-4-9b-0414")
LOCAL_LLM_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")


def is_local_base(base: str) -> bool:
    """True when ``base`` points at this machine (so it is safe by default)."""
    m = re.match(r"^[a-z]+://(?:\[)?([^\]:/]+)", base.strip(), re.IGNORECASE)
    return bool(m) and m.group(1).lower() in LOCAL_LLM_HOSTS


def llm_chat(messages, base: str = DEFAULT_LLM_BASE,
             model: str = DEFAULT_LLM_MODEL, timeout: int = 300) -> str:
    """One non-streamed chat completion over the OpenAI wire format."""
    import urllib.request  # local import: only the LLM path needs it
    url = base.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages,
                       "temperature": 0.2, "stream": False}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer not-needed"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _extract_json(text: str) -> Dict:
    """Pull the first JSON object out of a model reply (tolerates fences)."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("model did not return a JSON object")
    return data


BACKFILL_SYSTEM = (
    "You maintain a software task tracker. Given ONE task card, return ONLY a "
    "JSON object (no prose, no code fence) with keys: what (one paragraph), why "
    "(one paragraph), how (short paragraph or bullets), steps (array of "
    "{action, expected, observed}), acceptance (array of short strings), files "
    "(array of repo paths). Ground every claim in the card text. Never invent "
    "history: when an outcome is not stated, set observed to \"TODO\".")


def llm_backfill_sections(entry: Entry, text: str, base: str,
                          model: str) -> Dict:
    """Ask the local model to fill a card's canonical sections, as markdown."""
    body = text
    fm_block = _split_frontmatter(text)
    if fm_block is not None:
        body = text[text.find("\n---", 3) + 5:]
    user = (f"Card {entry.id} ({entry.status}, {entry.area}): {entry.title()}\n\n"
            f"{body.strip()[:6000]}")
    raw = llm_chat([{"role": "system", "content": BACKFILL_SYSTEM},
                    {"role": "user", "content": user}], base, model)
    return _llm_to_sections(_extract_json(raw))


def _llm_to_sections(data: Dict) -> Dict[str, str]:
    """Map the model's JSON to canonical-key -> markdown body."""
    out: Dict[str, str] = {}
    for key in ("what", "why", "how"):
        v = data.get(key)
        if isinstance(v, (list, tuple)):
            v = "\n".join(f"- {str(x).strip()}" for x in v if str(x).strip())
        if str(v or "").strip():
            out[key] = str(v).strip()
    steps = data.get("steps")
    if isinstance(steps, list) and steps:
        lines = []
        for i, s in enumerate(steps, 1):
            if isinstance(s, dict):
                lines.append(f"{i}. {str(s.get('action') or '').strip()}")
                lines.append(f"   - expected: {str(s.get('expected') or 'TODO').strip()}")
                lines.append(f"   - observed: {str(s.get('observed') or 'TODO').strip()}")
            else:
                lines.append(f"{i}. {str(s).strip()}")
        if lines:
            out["verify"] = "\n".join(lines)
    acc = data.get("acceptance")
    if isinstance(acc, list) and acc:
        out["acceptance"] = "\n".join(
            f"- [ ] {str(a).strip().lstrip('- [ ]').strip()}" for a in acc if str(a).strip())
    files = data.get("files")
    if isinstance(files, list) and files:
        out["files"] = "\n".join(f"- `{str(f).strip()}`" for f in files if str(f).strip())
    return out


def _fmt_refs(value) -> str:
    return ", ".join(_as_refs(value))


def _section_md(key: str, value) -> str:
    """Render one canonical section. A list becomes a bullet/checklist; an
    empty value falls back to the canonical stub."""
    if value is None or value == "":
        return SECTION_STUBS.get(key, "TODO")
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value if str(v).strip()]
        if not items:
            return SECTION_STUBS.get(key, "TODO")
        if key == "acceptance":
            return "\n".join(f"- [ ] {v.lstrip('- [ ]').strip()}" for v in items)
        if key == "files":
            return "\n".join(v if v.startswith(("-", "`")) else f"- `{v}`" for v in items)
        return "\n".join(items)
    return str(value).strip()


def render_card(*, kind: str, num: int, title: str, status: str, area: str,
                priority: str, filed: str, related: str = "", wiki: str = "",
                payload: Optional[Dict] = None) -> str:
    """Build a canonical card body (frontmatter + ordered sections).

    The section set is ``CANONICAL_SECTIONS``; ``payload`` may supply any of the
    canonical keys plus frontmatter fields (``horizon``, ``effort``, ``goal``,
    ``wiki`` and the dependency keys). Empty sections fall back to stubs, so a
    scaffolded card is always the right *shape* even before it is written into.
    """
    payload = payload or {}
    fm = [f"type: {'bug' if kind == 'bug' else 'task'}",
          f"status: {status}",
          f"area: {area}",
          f"priority: {priority}"]
    horizon = str(payload.get("horizon") or "").strip().lower()
    if horizon in HORIZONS:
        fm.append(f"horizon: {horizon}")
    effort = str(payload.get("effort") or "").strip()
    if effort in EFFORTS:
        fm.append(f"effort: {effort}")
    goal = str(payload.get("goal") or "").strip()
    if goal:
        fm.append(f"goal: {goal}")
    w = str(payload.get("wiki") or wiki or "").strip()
    if w:
        fm.append(f'wiki: "{w}"')
    for key in DEPENDENCY_KEYS:
        val = payload.get(key)
        if val:
            fm.append(f"{key}: [{_fmt_refs(val)}]")

    rel = _fmt_refs(payload.get("related") or related)
    out = ["---", *fm, "---", "",
           f"# {kind}-{num}: {title}", "",
           f"**Filed:** {filed}",
           f"**Related:** {rel}", ""]
    for key, heading, _aliases in CANONICAL_SECTIONS:
        out += [f"## {heading}", "", _section_md(key, payload.get(key)), ""]
    return "\n".join(out).rstrip() + "\n"


# --- merge writer ---------------------------------------------------------
#
# `backfill --write` rewrites a card in place: synonym headings become the
# canonical title, a `group:` key becomes `area:`, derived type/area/priority are
# added, and each canonical section is merged (a stub is replaced by real content;
# a section the card never had is inserted). Everything the schema does not own
# (## Landed, ## Notes, ## Non-goals, ...) is preserved, after the canonical block
# in its original order.


def _is_stub(body: str) -> bool:
    """True when a section holds only TODO/TBD placeholders (so it may be filled)."""
    lines = [l.strip() for l in (body or "").splitlines() if l.strip()]
    if not lines:
        return True
    for line in lines:
        v = line.lower()
        v = re.sub(r"^[0-9]+[.)]\s*", "", v)
        v = v.lstrip("-* ").strip()
        v = re.sub(r"^(expected|observed|action|note|step)s?\s*:\s*", "", v)
        if v not in ("todo", "tbd", "..."):
            return False
    return True


def _update_frontmatter(block: str, updates: Dict) -> str:
    """Set/replace keys in a raw frontmatter block; always leads with a newline.

    The returned block is meant to be concatenated after the opening ``---``,
    so it starts with ``\\n`` for both a well-formed block (``\\ntype: ...``) and
    an empty one. That keeps ``---`` and the first key on separate lines even
    when the source file opened as ``---type: ...`` (a real malformed shape).
    """
    lines = [l for l in block.lstrip("\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()

    def setkey(key, value):
        for i, l in enumerate(lines):
            if re.match(rf"^{re.escape(key)}\s*:", l):
                lines[i] = f"{key}: {value}"
                return
        lines.append(f"{key}: {value}")

    # group -> area: replace the group line, do not add a second key.
    if "area" in updates and any(re.match(r"^group\s*:", l) for l in lines):
        lines = [f"area: {updates['area']}" if re.match(r"^group\s*:", l) else l
                 for l in lines]
        updates = {k: v for k, v in updates.items() if k != "area"}
    for key, value in updates.items():
        if value is not None:
            setkey(key, value)
    return "\n" + "\n".join(lines)


def merge_card(text: str, new_sections: Optional[Dict] = None, *,
               add_missing: bool = True, overwrite: bool = False,
               preserve_order: bool = True,
               fm_updates: Optional[Dict] = None) -> str:
    """Return ``text`` rewritten to the canonical schema.

    ``preserve_order`` (default) keeps each section at the position the author
    put it, renaming a synonym in place and appending the canonical sections the
    card lacked. ``preserve_order=False`` emits the canonical blocks in
    ``CANONICAL_SECTIONS`` order, then the sections the schema does not own.
    Either way the *set* of sections is the same; only their order differs, and
    ``body_sections`` folds by key so downstream reads are identical.
    """
    fm_block = _split_frontmatter(text)
    if fm_block is not None:
        end = text.find("\n---", 3)
        body = text[end + 4:].lstrip("\n")
    else:
        body, fm_block = text, None

    m = H2_RE.search(body)
    preamble = body[:m.start()].rstrip("\n") if m else body.rstrip("\n")

    canonical: Dict[str, str] = {}
    # ``order`` records the emission sequence as (kind, name, chunk): a canonical
    # key (chunk is None, the body lives in ``canonical``) or an unknown heading.
    order: List[Tuple[str, str, Optional[str]]] = []
    present_keys = set()
    for heading, chunk in iter_h2(body):
        key = SECTION_KEY_BY_HEADING.get(heading.lower())
        if key is None or key in present_keys:
            # Unknown heading, or a SECOND synonym for a canonical section (e.g.
            # ## Why then ## Problem): keep it verbatim rather than dropping it.
            order.append(("unknown", heading, chunk))
        else:
            canonical[key] = chunk
            present_keys.add(key)
            order.append(("key", key, None))

    for key, value in (new_sections or {}).items():
        if key not in SECTION_TITLE_BY_KEY or value is None:
            continue
        if key not in canonical or overwrite or _is_stub(canonical[key]):
            canonical[key] = value
            if key not in present_keys:
                order.append(("key", key, None))
                present_keys.add(key)

    if add_missing:
        for key, _title, _a in CANONICAL_SECTIONS:
            canonical.setdefault(key, SECTION_STUBS[key])
            if key not in present_keys:
                order.append(("key", key, None))
                present_keys.add(key)

    if preserve_order:
        blocks = order
    else:
        blocks = [("key", key, None) for key, _t, _a in CANONICAL_SECTIONS
                  if key in canonical]
        blocks += [b for b in order if b[0] == "unknown"]

    out = [preamble, ""]
    for kind, name, chunk in blocks:
        if kind == "key":
            out += [f"## {SECTION_TITLE_BY_KEY[name]}", "", canonical[name].strip(), ""]
        else:
            out += [f"## {name}", "", (chunk or "").strip(), ""]
    new_body = "\n".join(out).rstrip() + "\n"

    fm_updates = fm_updates or {}
    if fm_block is None and not fm_updates:
        return new_body
    return ("---" + _update_frontmatter(fm_block or "", fm_updates)
            + "\n---\n\n" + new_body)


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

    payload: Dict = {}
    if getattr(args, "json", None):
        try:
            payload = _load_json_payload(args.json)
        except Exception as exc:
            print(f"error: --json is not valid JSON: {exc}", file=sys.stderr)
            return 1

    # --goal / --related still work alongside --json; the payload wins.
    if args.goal and "what" not in payload:
        payload["what"] = args.goal

    area_dir.mkdir(parents=True, exist_ok=True)
    body = render_card(kind=args.kind, num=num, title=args.title, status=status,
                       area=args.area,
                       priority=str(payload.get("priority") or args.priority),
                       filed=_dt.date.today().isoformat(),
                       related=args.related, wiki=getattr(args, "wiki", "") or "",
                       payload=payload)
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

    # A move changes the vault-relative path every path-style [[wikilink]] cites,
    # which is how inbound links silently rotted (task-662). Rewrite them to the
    # new basename, which Obsidian resolves from any status folder.
    vault = args.root.parent
    old_key = src.relative_to(vault).with_suffix("").as_posix()
    moved = 0
    try:
        _, moved = _load_doc_links().retarget_links(vault, old_key, dst.stem)
    except Exception as exc:  # never let link repair block the move
        print(f"warn: could not rewrite inbound links: {exc}", file=sys.stderr)

    print(f"{src}  ->  {dst}")
    if moved:
        print(f"  rewrote {moved} inbound wikilink(s)")
    return 0


def apply_set(text: str, fm_updates: Dict[str, str],
              sections: Optional[Dict[str, str]] = None) -> str:
    """Return ``text`` with frontmatter fields and/or sections updated.

    Pure (no I/O) so ``set`` and the MCP skin share it. With ``sections`` it
    replaces those canonical sections in place and touches nothing else; with
    only ``fm_updates`` it rewrites just those frontmatter keys.
    """
    if sections:
        return merge_card(text, sections, overwrite=True, add_missing=False,
                          preserve_order=True, fm_updates=fm_updates)
    fm_block = _split_frontmatter(text)
    if fm_block is None:
        # A legacy card with no frontmatter block (it carried a prose
        # `**Status:**` header instead): synthesize one above the body so
        # `set` can still record a field.
        return ("---" + _update_frontmatter("", fm_updates)
                + "\n---\n\n" + text.lstrip("\n"))
    end = text.find("\n---", 3)
    return "---" + _update_frontmatter(fm_block, fm_updates) + text[end:]


def cmd_set(args) -> int:
    """Set frontmatter fields and/or replace one canonical section body.

    Frontmatter-only ``set`` rewrites just those keys (no section reformatting).
    With ``--section KEY --value TEXT`` (or ``--value-file``) it replaces that
    canonical section in place. Nothing else in the card is reordered.
    """
    entries = find_by_id(iter_entries(args.root), args.kind, args.id)
    if not entries:
        print(f"error: no {args.kind}-{args.id} found", file=sys.stderr)
        return 1
    if len(entries) > 1:
        print(f"error: {args.kind}-{args.id} is ambiguous", file=sys.stderr)
        return 1
    entry = entries[0]
    text = read_text(entry.path)

    fm_updates: Dict[str, str] = {}
    for key in ("area", "priority", "horizon", "effort", "goal"):
        value = getattr(args, key, None)
        if value is not None:
            fm_updates[key] = str(value)
    if getattr(args, "wiki", None) is not None:
        fm_updates["wiki"] = f'"{args.wiki}"'
    for key in DEPENDENCY_KEYS:
        value = getattr(args, key, None)
        if value is not None:
            fm_updates[key] = f"[{_fmt_refs(value)}]"

    sections: Dict[str, str] = {}
    if args.section:
        body = args.value
        if body is None and getattr(args, "value_file", None):
            body = Path(args.value_file).read_text(encoding="utf-8-sig")
        if body is None:
            print("error: --section needs --value or --value-file", file=sys.stderr)
            return 1
        sections[args.section] = body

    if not fm_updates and not sections:
        print("error: nothing to set", file=sys.stderr)
        return 1

    try:
        new_text = apply_set(text, fm_updates, sections)
    except ValueError as exc:
        print(f"error: {entry.path}: {exc}", file=sys.stderr)
        return 1

    if new_text == text:
        print(f"unchanged: {entry.path}")
        return 0
    entry.path.write_text(new_text, encoding="utf-8")
    print(str(entry.path))
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


def _tally(entries: List[Entry]) -> Dict:
    by_status: Dict[str, int] = {}
    by_area: Dict[str, Dict[str, int]] = {}
    by_horizon: Dict[str, int] = {}
    for e in entries:
        by_status[e.status] = by_status.get(e.status, 0) + 1
        area = e.area or "?"
        by_area.setdefault(area, {})
        by_area[area][e.status] = by_area[area].get(e.status, 0) + 1
        h = str(e.frontmatter().get("horizon") or "").strip().lower()
        if h:
            by_horizon[h] = by_horizon.get(h, 0) + 1
    return {"total": len(entries), "by_status": by_status,
            "by_area": by_area, "by_horizon": by_horizon}


def cmd_status(args) -> int:
    """Counts by folder status, area and horizon. Read-only."""
    entries = [e for e in iter_entries(args.root) if e.kind]
    counts = _tally(entries)
    if getattr(args, "json", False):
        print(json.dumps(counts, indent=2))
        return 0
    print(f"{counts['total']} cards")
    print("by status: " + ", ".join(
        f"{s} {counts['by_status'].get(s, 0)}" for s in STATUSES))
    if counts["by_horizon"]:
        print("by horizon: " + ", ".join(
            f"{h} {counts['by_horizon'][h]}"
            for h in HORIZONS if h in counts["by_horizon"]))
    print("by area:")
    for area in sorted(counts["by_area"]):
        parts = counts["by_area"][area]
        cells = " ".join(f"{s}:{parts.get(s, 0)}"
                         for s in STATUSES if parts.get(s))
        print(f"  {area:<14} {cells}")
    return 0


def _roadmap_buckets(entries: List[Entry]):
    """Split the actionable work into (now, next, later).

    Computed from the dependency graph and folder status so a roadmap exists
    without anyone hand-tagging 400 cards:
      * ``inprogress`` or a startable ``high`` card, or ``horizon: now`` -> Now
      * any open predecessor, or ``horizon: later``                    -> Later
      * everything else startable                                      -> Next
    An explicit ``horizon:`` always wins over the computed bucket.
    """
    cards, succ, pred = _dep_graph(entries)
    actionable = [e for e in entries if e.status in ("todo", "inprogress")]
    prio = {"high": 0, "medium": 1, "low": 2}

    def horizon(e: Entry) -> str:
        return str(e.frontmatter().get("horizon") or "").strip().lower()

    def blocked(e: Entry) -> bool:
        return any(cards[p].status not in TERMINAL_STATUSES for p in pred[e.id])

    def rank(e: Entry):
        return (-_unblocks(e.id, cards, succ),
                prio.get(str(e.frontmatter().get("priority") or "").lower(), 1),
                {"now": 0, "next": 1, "later": 2}.get(horizon(e), 3),
                e.num)

    now: List[Entry] = []
    nxt: List[Entry] = []
    later: List[Entry] = []
    for e in actionable:
        h = horizon(e)
        if h == "later" or (blocked(e) and h != "now"):
            later.append(e)
        elif h == "now" or e.status == "inprogress" \
                or prio.get(str(e.frontmatter().get("priority") or "").lower(), 1) == 0:
            now.append(e)
        else:
            nxt.append(e)
    return (sorted(now, key=rank), sorted(nxt, key=rank), sorted(later, key=rank))


def cmd_roadmap(args) -> int:
    """Generate the roadmap view, computed from the graph + folders.

    Now / Next / Later are derived (see ``_roadmap_buckets``) rather than read
    from a hand-set ``horizon:``; a card that *does* carry one still overrides
    its computed bucket. The ``review`` pile is called out as a verification
    queue. Derived, so regenerate freely; writes only with ``--out``.
    """
    entries = [e for e in iter_entries(args.root) if e.kind]
    counts = _tally([e for e in entries if e.status not in TERMINAL_STATUSES])
    now, nxt, later = _roadmap_buckets(entries)
    cards, succ, pred = _dep_graph(entries)
    critical = _longest_path(sorted(cards), succ, pred) if cards else []
    review = [e for e in entries if e.status == "review"]

    lines = ["# Roadmap", "",
             "*Generated by `python tools/tasks.py roadmap` - do not edit by hand.*", "",
             f"**{counts['by_status'].get('todo', 0) + counts['by_status'].get('inprogress', 0)} "
             f"actionable** - todo {counts['by_status'].get('todo', 0)}, "
             f"inprogress {counts['by_status'].get('inprogress', 0)}"
             f"  ·  **{len(review)} in review** (verification queue)", ""]

    def section(title: str, blurb: str, picked: List[Entry]) -> None:
        lines.extend([f"## {title} — {len(picked)}", "", blurb, ""])
        if not picked:
            lines.extend(["_nothing_", ""])
            return
        for e in picked:
            h = str(e.frontmatter().get("horizon") or "").strip().lower()
            tag = f", {h}" if h else ""
            lines.append(f"- `{e.id}` {e.title()}  "
                         f"_({e.status}, {e.area}{tag}; unblocks {_unblocks(e.id, cards, succ)})_")
        lines.append("")

    section("Now", "In progress, or startable and high-priority.", now)
    section("Next", "Startable once nothing else is picked up first.", nxt)
    section("Later", "Blocked by open work, or explicitly deferred.", later)

    if critical:
        lines.extend(["## Critical path", "",
                      "*The longest real dependency chain.*", "",
                      " → ".join(f"`{i}`" for i in critical), ""])
    by_area = Counter(r.area or "?" for r in review)
    lines.extend(["## Review queue", "",
                  f"{len(review)} cards await verification, by area: "
                  + ", ".join(f"{a} {n}" for a, n in sorted(by_area.items())),
                  ""])

    text = "\n".join(lines).rstrip() + "\n"
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0


# --- dependency graph -----------------------------------------------------
#
# Ordering edges come from the frontmatter dependency keys, not `related`:
#   blocked_by: [b] / depends_on: [d] / parent: [p]  ->  b/d/p precedes this
#   blocks: [c] / children: [c]                      ->  this precedes c
# `supersedes` and `related` are informational and carry no ordering.

def _dep_graph(entries: List[Entry]):
    """Return ``(cards, succ, pred)``: id->Entry and the adjacency in both
    directions, restricted to ids that exist (a dangling ref is ignored)."""
    cards = {e.id: e for e in entries if e.kind}
    succ: Dict[str, set] = {i: set() for i in cards}
    pred: Dict[str, set] = {i: set() for i in cards}

    def link(before: str, after: str) -> None:
        if before in cards and after in cards and before != after:
            succ[before].add(after)
            pred[after].add(before)

    for e in entries:
        if not e.kind:
            continue
        fm = e.frontmatter()
        for d in _as_refs(fm.get("blocked_by")):
            link(d, e.id)
        for d in _as_refs(fm.get("depends_on")):
            link(d, e.id)
        for d in _as_refs(fm.get("blocks")):
            link(e.id, d)
        for d in _as_refs(fm.get("children")):
            link(e.id, d)
        for d in _as_refs(fm.get("parent")):
            link(d, e.id)
    return cards, succ, pred


def _find_cycles(nodes, succ) -> List[List[str]]:
    """Every elementary cycle reachable from ``nodes`` (iterative DFS)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    cycles: List[List[str]] = []
    seen = set()
    for start in nodes:
        if color[start] != WHITE:
            continue
        stack = [start]
        path = [start]
        on_path = {start}
        color[start] = GRAY
        iters = {start: iter(sorted(succ[start]))}
        while stack:
            node = stack[-1]
            nxt = next(iters[node], None)
            if nxt is None:
                color[node] = BLACK
                stack.pop()
                path.pop()
                on_path.discard(node)
                continue
            if color[nxt] == GRAY and nxt in on_path:
                idx = path.index(nxt)
                cyc = path[idx:] + [nxt]
                key = tuple(sorted(cyc[:-1]))
                if key not in seen:
                    seen.add(key)
                    cycles.append(cyc)
            elif color[nxt] == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                on_path.add(nxt)
                stack.append(nxt)
                iters[nxt] = iter(sorted(succ[nxt]))
    return cycles


def _longest_path(nodes, succ, pred) -> List[str]:
    """Longest chain of nodes in the DAG (by node count). ``[]`` if cyclic."""
    indeg = {n: len(pred[n]) for n in nodes}
    dist = {n: 1 for n in nodes}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes}
    q = deque(sorted(n for n in nodes if indeg[n] == 0))
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for m in sorted(succ[n]):
            if dist[n] + 1 > dist[m]:
                dist[m] = dist[n] + 1
                prev[m] = n
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    if seen != len(nodes):
        return []
    end = max(nodes, key=lambda n: dist[n])
    path = []
    node: Optional[str] = end
    while node is not None:
        path.append(node)
        node = prev[node]
    return list(reversed(path))


def _unblocks(card_id: str, cards, succ) -> int:
    """Open cards that become startable once ``card_id`` is terminal."""
    return sum(1 for s in succ[card_id] if cards[s].status not in TERMINAL_STATUSES)


def cmd_graph(args) -> int:
    """Report dependency edges, cycles and the critical path. Read-only."""
    entries = [e for e in iter_entries(args.root) if e.kind]
    cards, succ, pred = _dep_graph(entries)
    nodes = sorted(cards)
    edges = sorted((a, b) for a in succ for b in succ[a])
    cycles = _find_cycles(nodes, succ)
    path = _longest_path(nodes, succ, pred)
    if getattr(args, "json", False):
        print(json.dumps({
            "nodes": len(nodes), "edges": len(edges),
            "cycles": cycles, "critical_path": path}, indent=2))
        return 0
    print(f"{len(nodes)} cards, {len(edges)} dependency edges")
    if cycles:
        print(f"{len(cycles)} cycle(s):")
        for cyc in cycles:
            print("  " + " -> ".join(cyc))
    else:
        print("no cycles")
    if path:
        print(f"critical path ({len(path)}): " + " -> ".join(path))
    else:
        print("critical path: (none)")
    return 0


def cmd_next(args) -> int:
    """Rank the open cards that can start now (every predecessor is terminal).

    Ordered by how many open cards the card unblocks, then priority, then
    horizon, then id. Read-only; this is "what can I pick up next".
    """
    entries = [e for e in iter_entries(args.root) if e.kind]
    cards, succ, pred = _dep_graph(entries)
    limit = getattr(args, "limit", None) or 20
    open_statuses = {"todo", "inprogress"}
    open_cards = [e for e in entries if e.status in open_statuses]

    def blocked(e: Entry) -> bool:
        return any(cards[p].status not in TERMINAL_STATUSES for p in pred[e.id])

    startable = [e for e in open_cards if not blocked(e)]
    prio = {"high": 0, "medium": 1, "low": 2}
    hor = {"now": 0, "next": 1, "later": 2}
    startable.sort(key=lambda e: (
        -_unblocks(e.id, cards, succ),
        prio.get(str(e.frontmatter().get("priority") or "").lower(), 1),
        hor.get(str(e.frontmatter().get("horizon") or "").lower(), 3),
        e.num))
    picked = startable[:limit]
    if getattr(args, "json", False):
        print(json.dumps({
            "open": len(open_cards), "startable": len(startable),
            "cards": [{"id": e.id, "status": e.status, "area": e.area,
                       "priority": str(e.frontmatter().get("priority") or ""),
                       "horizon": str(e.frontmatter().get("horizon") or ""),
                       "unblocks": _unblocks(e.id, cards, succ),
                       "title": e.title()} for e in picked]}, indent=2))
        return 0
    print(f"{len(open_cards)} open, {len(startable)} startable now"
          + (f" (showing {len(picked)})" if len(picked) < len(startable) else ""))
    for e in picked:
        h = str(e.frontmatter().get("horizon") or "-")
        pr = str(e.frontmatter().get("priority") or "-")
        print(f"{e.id:<10} {e.status:<10} {e.area:<12} "
              f"h={h:<5} p={pr:<6} unblocks={_unblocks(e.id, cards, succ)}  {e.title()}")
    return 0


def _frontmatter_needs(text: str) -> List[str]:
    fm, _ = parse_frontmatter(text)
    needs = []
    if not fm.get("type"):
        needs.append("type")
    if not fm.get("area"):
        needs.append("area" + (" (from group)" if fm.get("group") else ""))
    if not fm.get("priority"):
        needs.append("priority")
    return needs


def _backfill_plan(entry: Entry) -> Dict:
    text = read_text(entry.path)
    return {"synonyms": section_synonyms(text),
            "missing": missing_sections(text),
            "frontmatter": _frontmatter_needs(text)}


def cmd_backfill(args) -> int:
    """Report the canonical-schema gap; optionally draft content with a local LLM.

    Default is a read-only report: per card, the synonym headings to rename, the
    canonical sections it lacks, and the frontmatter keys it lacks. With
    ``--content`` it asks a LOCAL model (LM Studio by default - no API tokens) to
    draft the missing sections from the card's own text and prints them. Nothing
    is written yet; the merge writer is the next step.
    """
    wanted = set(args.status) if getattr(args, "status", None) else set(STATUSES)
    entries = [e for e in iter_entries(args.root) if e.kind and e.status in wanted]
    if getattr(args, "card", None) is not None:
        entries = [e for e in entries
                   if e.num == args.card
                   and (not getattr(args, "kind", None) or e.kind == args.kind)]

    if getattr(args, "write", False):
        return _backfill_write(args, entries)
    if getattr(args, "content", False):
        return _backfill_content(args, entries)

    report = []
    for e in entries:
        plan = _backfill_plan(e)
        if plan["synonyms"] or plan["missing"] or plan["frontmatter"]:
            report.append((e, plan))
    if getattr(args, "json", False):
        print(json.dumps({
            "scanned": len(entries), "needing_work": len(report),
            "cards": [{"id": e.id, "status": e.status, "area": e.area,
                       "rename": [h for h, _k in p["synonyms"]],
                       "missing": p["missing"], "frontmatter": p["frontmatter"]}
                      for e, p in report]}, indent=2))
        return 0
    for e, p in report:
        bits = []
        if p["synonyms"]:
            bits.append("rename=" + ",".join(h for h, _k in p["synonyms"]))
        if p["missing"]:
            bits.append("missing=" + ",".join(p["missing"]))
        if p["frontmatter"]:
            bits.append("fm=" + ",".join(p["frontmatter"]))
        print(f"{e.id:<10} {e.status:<10} {e.area:<12} " + "  ".join(bits))
    print(f"\n{len(entries)} cards scanned, {len(report)} need work")
    return 0


def _backfill_content(args, entries: List[Entry]) -> int:
    """Draft the missing sections of each card with a local model (dry run)."""
    base = getattr(args, "llm_base", None) or DEFAULT_LLM_BASE
    model = getattr(args, "llm_model", None) or DEFAULT_LLM_MODEL
    limit = getattr(args, "limit", None) or 5
    if not is_local_base(base) and not getattr(args, "allow_remote", False):
        print(f"refusing a non-local LLM base {base!r} without --allow-remote",
              file=sys.stderr)
        return 2
    todo = [e for e in entries if _backfill_plan(e)["missing"]]
    n = min(limit, len(todo))
    print(f"# {len(todo)} cards missing content; drafting {n} with {model} "
          f"at {base}", file=sys.stderr)
    for e in todo[:n]:
        try:
            sections = llm_backfill_sections(e, read_text(e.path), base, model)
        except Exception as exc:
            print(f"{e.id}: LLM error: {exc}", file=sys.stderr)
            continue
        print(f"\n## {e.id} {e.title()}  ({e.status}/{e.area})")
        for key, _title, _aliases in CANONICAL_SECTIONS:
            if key in sections:
                print(f"\n### {SECTION_TITLE_BY_KEY[key]}\n\n{sections[key]}")
    print("\n(preview only - nothing written; add --write to apply)",
          file=sys.stderr)
    return 0


def _needs_work(entry: Entry) -> bool:
    p = _backfill_plan(entry)
    return bool(p["synonyms"] or p["missing"] or p["frontmatter"])


def _backfill_write(args, entries: List[Entry]) -> int:
    """Merge the canonical schema into each card and write it back.

    Structure-only unless ``--content`` (which drafts the missing sections with
    the local model first). ``--force`` overwrites sections that already hold
    content; by default only stubs are replaced. Bounded by ``--limit`` so a run
    is paced.
    """
    use_llm = getattr(args, "content", False)
    base = getattr(args, "llm_base", None) or DEFAULT_LLM_BASE
    model = getattr(args, "llm_model", None) or DEFAULT_LLM_MODEL
    if use_llm and not is_local_base(base) \
            and not getattr(args, "allow_remote", False):
        print(f"refusing a non-local LLM base {base!r} without --allow-remote",
              file=sys.stderr)
        return 2
    limit = getattr(args, "limit", None) or (
        1 if getattr(args, "card", None) is not None else 15)
    targets = [e for e in entries if _needs_work(e)]
    print(f"# {len(targets)} cards need work; writing {min(limit, len(targets))}"
          + (f" with {model}" if use_llm else " (structure only)"), file=sys.stderr)
    changed = 0
    for e in targets[:limit]:
        text = read_text(e.path)
        plan = _backfill_plan(e)
        sections: Dict[str, str] = {}
        if use_llm and plan["missing"]:
            try:
                sections = llm_backfill_sections(e, text, base, model)
            except Exception as exc:
                print(f"{e.id}: LLM error: {exc}", file=sys.stderr)
        fm = parse_frontmatter(text)[0]
        fm_updates: Dict[str, str] = {}
        if not fm.get("type"):
            fm_updates["type"] = e.kind
        if not fm.get("status"):
            fm_updates["status"] = e.status
        if not fm.get("area") and e.area:
            fm_updates["area"] = e.area
        if not fm.get("priority"):
            fm_updates["priority"] = "medium"
        new_text = merge_card(text, sections,
                              overwrite=getattr(args, "force", False),
                              preserve_order=not getattr(args, "canonical_order", False),
                              fm_updates=fm_updates)
        if new_text != text:
            e.path.write_text(new_text, encoding="utf-8")
            changed += 1
            print(f"  {e.id:<10} {e.status:<10} {e.area}")
    print(f"\n{changed} cards rewritten", file=sys.stderr)
    return 0


def _schema_warnings(entries: List[Entry]) -> List[str]:
    """Canonical-schema gaps, so `validate --schema` can report the backlog.

    Warns (never errors, for now) when a non-terminal or done card lacks a
    canonical section or frontmatter key, when a done card still has an
    unchecked acceptance box, and when its verification still reads
    ``observed: TODO``. These become errors once the backfill has cleared the
    tree, which is why they are reported but not fatal.
    """
    out: List[str] = []
    for e in entries:
        if not e.kind or e.status not in ("todo", "inprogress", "review", "done"):
            continue
        text = try_read_text(e.path)
        miss = missing_sections(text)
        if miss:
            out.append(f"{e.id} ({e.status}) missing section(s): {', '.join(miss)}")
        needs = _frontmatter_needs(text)
        if needs:
            out.append(f"{e.id} ({e.status}) missing frontmatter: {', '.join(needs)}")
        if e.status == "done":
            secs = body_sections(text)
            if re.search(r"^\s*-\s*\[ \]", secs.get("acceptance", ""), re.MULTILINE):
                out.append(f"{e.id} done with an unchecked acceptance box")
            if re.search(r"observed\s*:\s*TODO", secs.get("verify", ""), re.IGNORECASE):
                out.append(f"{e.id} done with observed: TODO")
    return out


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
        lines = try_read_text(e.path).splitlines()
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

    if getattr(args, "schema", False):
        warnings.extend(_schema_warnings(entries))

    if not args.quiet:
        for w in warnings:
            print(f"warn: {w}")
    for err in errors:
        print(f"error: {err}", file=sys.stderr)
    print(f"\n{len(entries)} files, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_links(args) -> int:
    """Check the vault's [[wikilinks]] (delegates to tools/doc_links.py)."""
    try:
        doc_links = _load_doc_links()
    except ImportError as exc:
        print(f"error: cannot import tools/doc_links.py: {exc}", file=sys.stderr)
        return 2
    argv = ["--report"] if getattr(args, "report", False) else ["--check"]
    return doc_links.main(argv)


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
    set       set frontmatter fields and/or replace one section
    list      list tasks/bugs, optionally filtered
    validate  check ids, filenames, folders and cross-references
    links     check the vault's [[wikilinks]] against the notes on disk
    index     rebuild or clear the derived frontmatter cache
    status    counts by status / area / horizon
    roadmap   generate the roadmap view from folders + horizon
    graph     dependency edges, cycles and the critical path
    next      rank the open cards that can start now
    backfill  report the canonical-schema gap (What/Why/How/Verify/Files)
    help      show this guide, or `help <command>` for one command

Run with no command for an interactive menu (type `q` to quit).

Statuses: todo / inprogress / review / done / cancelled
Kinds:    task / bug
Areas:    bugs characters conditions docs emotions gameplay graph items
          library refactor testing triggers ui world

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
    "set": """\
set --id N [--kind task|bug] [FIELD VALUE...] [--section KEY --value TEXT]

Update a card's frontmatter and/or replace one canonical section. With no
--section the writer touches only the frontmatter keys you pass, leaving the
body byte-for-byte. With --section it replaces that canonical section in place.

  --area --priority --horizon --effort --goal --wiki
  --related --blocks --blocked-by --depends-on --supersedes --parent --children
  --section   one of: what why how verify acceptance files
  --value     the new section body (or --value-file to read it from a file)

  python tools/tasks.py set --id 447 --priority high --horizon now
  python tools/tasks.py set --id 447 --section acceptance --value "- [ ] done"
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
validate [--quiet] [--schema]

Check the whole tree: duplicate ids, filenames that do not parse, files outside
a status folder, frontmatter/folder status mismatches, and dangling
Related/Blocks/Depends-on references. Historical terminal duplicates are
reported as warnings, everything else as errors (exit code 1).

  --quiet   suppress warnings, print only errors and the summary
  --schema  also warn on canonical-schema gaps: a card lacking a canonical
            section or frontmatter key, a done card with an unchecked
            acceptance box, or a done card whose observed still reads TODO

  python tools/tasks.py validate
  python tools/tasks.py validate --schema
""",
    "links": """\
links [--report]

Resolve every [[wikilink]] in the vault against the notes on disk and fail if
any is broken. This is the guard that keeps a task move from rotting the notes
that cite it: `move` rewrites inbound links, and this catches what it misses.

  --report  list the broken links, grouped by target

  python tools/tasks.py links
  python tools/tasks.py links --report

Implementation lives in tools/doc_links.py.
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
    "status": """\
status [--json]

Count cards by folder status, by area and by `horizon:` frontmatter. Read-only;
this is the polling view a roadmap refreshes from.

  --json   machine-readable counts (status, area, horizon)

  python tools/tasks.py status
  python tools/tasks.py status --json
""",
    "roadmap": """\
roadmap [--out PATH]

Generate the roadmap, computed from the dependency graph and the folders rather
than from hand-set tags. Buckets:

  Now    in progress, or startable and high-priority
  Next   startable once nothing else is picked up first
  Later  blocked by open work, or explicitly deferred

A card that *does* carry `horizon: now|next|later` overrides its computed
bucket. The `review` pile is reported separately as a verification queue, and
the critical path (longest dependency chain) is shown. Derived, so regenerate
freely; prints to stdout unless --out names a file.

  --out   write to a file instead of stdout

  python tools/tasks.py roadmap
  python tools/tasks.py roadmap --out docs/design/roadmap-computed.md
""",
    "graph": """\
graph [--json]

Build the dependency DAG from the frontmatter keys (blocked_by, depends_on,
parent -> precedes; blocks, children -> succeeds; related/supersedes carry no
ordering), then report the node/edge counts, any cycles, and the longest
dependency chain (the critical path). Read-only.

  --json   machine-readable nodes/edges/cycles/critical_path

  python tools/tasks.py graph
  python tools/tasks.py graph --json
""",
    "next": """\
next [--limit N] [--json]

Rank the OPEN cards whose predecessors are all terminal -- i.e. what can be
picked up now. Ordered by how many open cards the card unblocks, then priority,
then horizon, then id. Read-only.

  --limit  max cards to show (default 20)
  --json   machine-readable list

  python tools/tasks.py next
  python tools/tasks.py next --limit 5
""",
    "backfill": """\
backfill [--status S...] [--json] [--content] [--write] [--card N]
         [--kind task|bug] [--force] [--canonical-order] [--limit N]

Report the canonical-schema gap across the tree (dry run): per card, the synonym
headings to rename (## Files Affected -> ## Files), the canonical sections it
lacks, and the frontmatter keys it lacks. A card is canonical when its body
carries What / Why / How / Steps to verify / Acceptance / Files, where Steps to
verify holds the expected and observed outcome.

  --status          limit to these statuses (default: all)
  --json            machine-readable plan
  --content         draft the missing sections with a LOCAL model (LM Studio
                    by default - no API tokens); add --write to apply
  --write           merge the schema into each card (default is a dry run)
  --card N          only this numeric id (with --kind when ambiguous)
  --force           overwrite sections that already hold content
  --canonical-order emit the canonical section order; the default preserves the
                    author's order and only appends what was missing
  --limit N         max cards per run (default 15; 1 with --card)
  --llm-base URL / --llm-model ID / --allow-remote

  python tools/tasks.py backfill --status review done
  python tools/tasks.py backfill --card 748 --write
  python tools/tasks.py backfill --content --write --limit 20
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
    nw.add_argument("--json", help="JSON payload: section bodies + frontmatter (or @file)")
    nw.add_argument("--wiki", default="", help='Obsidian link, e.g. "[[Feature Map]]"')
    nw.add_argument("--force", action="store_true")
    nw.set_defaults(func=cmd_new)

    mv = sub.add_parser("move", help="move a task between status folders")
    mv.add_argument("--id", type=int, required=True)
    mv.add_argument("--kind", choices=KINDS, default="task")
    mv.add_argument("--status", choices=STATUSES, required=True)
    mv.set_defaults(func=cmd_move)

    se = sub.add_parser("set", help="set frontmatter and/or replace one section")
    se.add_argument("--id", type=int, required=True)
    se.add_argument("--kind", choices=KINDS, default="task")
    se.add_argument("--area")
    se.add_argument("--priority")
    se.add_argument("--horizon", choices=HORIZONS)
    se.add_argument("--effort", choices=EFFORTS)
    se.add_argument("--goal")
    se.add_argument("--wiki")
    for _key in DEPENDENCY_KEYS:
        se.add_argument("--" + _key.replace("_", "-"), dest=_key)
    se.add_argument("--section", choices=sorted(SECTION_TITLE_BY_KEY),
                    help="canonical section to replace")
    se.add_argument("--value", help="new body for --section")
    se.add_argument("--value-file", help="read the --section body from a file")
    se.set_defaults(func=cmd_set)

    ls = sub.add_parser("list", help="list tasks")
    ls.add_argument("--status", choices=STATUSES)
    ls.add_argument("--area")
    ls.add_argument("--kind", choices=KINDS)
    ls.set_defaults(func=cmd_list)

    st = sub.add_parser("status", help="counts by status/area/horizon")
    st.add_argument("--json", action="store_true")
    st.set_defaults(func=cmd_status)

    rm = sub.add_parser("roadmap", help="generate the roadmap view")
    rm.add_argument("--out", help="write to a file instead of stdout")
    rm.set_defaults(func=cmd_roadmap)

    gr = sub.add_parser("graph", help="dependency edges, cycles, critical path")
    gr.add_argument("--json", action="store_true")
    gr.set_defaults(func=cmd_graph)

    nx = sub.add_parser("next", help="rank the open cards that can start now")
    nx.add_argument("--limit", type=int, help="max cards to show (default 20)")
    nx.add_argument("--json", action="store_true")
    nx.set_defaults(func=cmd_next)

    bf = sub.add_parser("backfill", help="report the canonical-schema gap")
    bf.add_argument("--status", nargs="+", choices=STATUSES)
    bf.add_argument("--json", action="store_true")
    bf.add_argument("--content", action="store_true",
                    help="draft missing sections with a local LLM")
    bf.add_argument("--write", action="store_true",
                    help="apply the merge (default is a dry run)")
    bf.add_argument("--card", type=int, help="only this numeric id")
    bf.add_argument("--kind", choices=KINDS, help="with --card, task or bug")
    bf.add_argument("--force", action="store_true",
                    help="overwrite sections that already hold content")
    bf.add_argument("--canonical-order", action="store_true",
                    help="emit canonical section order instead of preserving it")
    bf.add_argument("--limit", type=int, help="max cards per run")
    bf.add_argument("--llm-base", help="OpenAI-compatible base (default LM Studio)")
    bf.add_argument("--llm-model", help="model id (default glm-4-9b-0414)")
    bf.add_argument("--allow-remote", action="store_true",
                    help="permit a non-local LLM base")
    bf.set_defaults(func=cmd_backfill)

    v = sub.add_parser("validate", help="check ids, filenames, folders and refs")
    v.add_argument("--quiet", action="store_true")
    v.add_argument("--schema", action="store_true",
                   help="also warn on canonical-schema gaps (sections/frontmatter)")
    v.set_defaults(func=cmd_validate)

    ix = sub.add_parser("index", help="rebuild or clear the derived frontmatter cache")
    ix.add_argument("--clear", action="store_true", help="delete the cache instead")
    ix.set_defaults(func=cmd_index)

    lk = sub.add_parser("links", help="check the vault's [[wikilinks]]")
    lk.add_argument("--report", action="store_true", help="list the broken links")
    lk.set_defaults(func=cmd_links)

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
