#!/usr/bin/env python3
"""Dev-task helper: allocate ids, scaffold, move between status folders, check.

Git and the task files stay the single source of truth - this tool only
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
    python tools/tasks.py link-deps [--status S...] [--write]
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

Those dependency keys are the machine-readable graph (``graph``, ``next`` and
``roadmap`` read nothing else) and Obsidian reads none of it, so
``link-deps`` renders the same relations as ``[[wikilinks]]`` in each card's
preamble and keeps them in step whenever a dependency is written.

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
import time
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

# "# task-568: Town cells" -> "Town cells". Also matches "Bug 22 - ...".
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
    ("browser_ui", "Browser UI and intended live verification",
     ("browser ui requirement and live steps", "browser verification steps",
      "browser verification", "browser live verification",
      "intended browser ui", "ui and live verification")),
    ("verify", "Steps to verify",
     ("verification", "testing", "tests", "test plan", "how to verify",
      "live verification", "how to test")),
    ("acceptance", "Acceptance", ("acceptance criteria", "done when")),
    ("files", "Files",
     ("files affected", "files changed", "files touched", "affected files")),
)

# The `## Browser UI and intended live verification` section names the UI home,
# current availability, and the live path when the UI is available. It describes
# intended access and testability; it must not imply a planned UI already works.
# A genuinely headless task states why browser UI is N/A and gives an observable
# alternative verification path.
#
# The `## Steps to verify` section carries the expected and observed outcome:
#   1. <action>
#      - expected: ...
#      - observed: ...
# `backfill` seeds those lines; validation never invents the observed value.
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
#
# The stubs make the intended browser surface and its future live acceptance
# path explicit. They distinguish a planned UI from a UI that exists and has
# actually been checked. Replace the placeholders; do not delete the sections.
BROWSER_UI_STUB = (
    "Intended UI home: TODO - name the page, panel, tab, or control where this "
    "behavior belongs. If no browser UI is appropriate, write 'Not applicable' "
    "here, explain why below, and give an observable alternative.\n\n"
    "Current availability: TODO - for example, planned/not implemented, "
    "present but not live-checked, or live-checked with date and evidence.\n\n"
    "Live steps when available:\n"
    "1. TODO - describe how to reach the surface and the interaction to perform.\n"
    "   - expected: TODO - describe what the user can see or do.\n\n"
    "Why no browser UI: (only when Intended UI home is Not applicable) TODO - "
    "explain why browser interaction is not appropriate.\n\n"
    "Alternative verification steps: (only when Intended UI home is Not "
    "applicable)\n"
    "1. TODO - describe an observable alternative.\n"
    "   - expected: TODO - describe the result.\n\n"
    "This section defines intended access and live acceptance. It is not a claim "
    "that planned UI exists or works today. Current availability says what is "
    "implemented and verified now; the numbered steps say how to reach and test "
    "the intended surface once it is available."
)
VERIFY_STUB = (
    "1. Follow the intended live path in Browser UI and intended live "
    "verification when that surface is available.\n"
    "   - expected: TODO\n"
    "   - observed: TODO\n"
    "2. Record the browser surface and interaction actually used (for example: "
    "navigate, click, hover, type, expand, or scroll to the bottom).\n"
    "   - expected: TODO\n"
    "   - observed: TODO\n"
    "3. Run the targeted regression test for the mechanism.\n"
    "   - expected: TODO\n"
    "   - observed: TODO"
)

SECTION_STUBS = {
    "what": "TODO",
    "why": "TODO",
    "how": "TODO",
    "browser_ui": BROWSER_UI_STUB,
    "verify": VERIFY_STUB,
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


def browser_ui_issue(text: str) -> str:
    """Return why the browser-UI intent/verification section is incomplete.

    This deliberately validates the *planned access path*, not whether the UI
    already exists. Availability is stated by the card author; numbered steps
    describe how to reach and check the surface once it is available. A task
    with no appropriate browser surface must explain why and provide an
    observable alternative.
    """
    section = body_sections(text).get("browser_ui", "")
    if not section.strip():
        return "missing Browser UI and intended live verification section"

    def field(label: str) -> str:
        match = re.search(
            rf"(?im)^[ \t]*(?:[-*][ \t]*)?{re.escape(label)}[ \t]*:[ \t]*([^\r\n]*)",
            section,
        )
        return match.group(1).strip() if match else ""

    def has_field(label: str) -> bool:
        return bool(re.search(
            rf"(?im)^[ \t]*(?:[-*][ \t]*)?{re.escape(label)}[ \t]*:",
            section,
        ))

    def placeholder(value: str) -> bool:
        return not value or bool(re.search(r"(?i)\b(?:TODO|TBD)\b", value))

    home = field("Intended UI home")
    availability = field("Current availability")
    if placeholder(home):
        return "Intended UI home is missing or left as a placeholder"
    if placeholder(availability):
        return "Current availability is missing or left as a placeholder"
    # Markdown wrapping can split a phrase across lines in a task card.
    if not re.search(r"(?i)\bnot\s+a\s+claim\b", section):
        return "must distinguish intended UI from a claim that it works today"

    no_browser_ui = bool(re.match(r"(?i)^(?:not applicable|n/a|no browser ui|none)\b", home))
    steps = re.findall(r"(?m)^[ \t]*\d+[.)][ \t]+([^\r\n]+)", section)
    usable_steps = [step for step in steps if not placeholder(step.strip())]
    if not usable_steps:
        return "needs at least one numbered, non-placeholder verification step"

    expected_values = re.findall(
        r"(?im)^[ \t]*[-*][ \t]*expected[ \t]*:[ \t]*([^\r\n]*)", section)
    if not any(not placeholder(value.strip()) for value in expected_values):
        return "verification steps need a non-placeholder expected observable result"

    if no_browser_ui:
        reason = field("Why no browser UI")
        if placeholder(reason):
            return "a no-browser-UI exception needs a reason"
        if not has_field("Alternative verification steps"):
            return "a no-browser-UI exception needs alternative verification steps"
    else:
        if not has_field("Live steps when available"):
            return "Live steps when available field is missing"
    return ""


def default_root() -> Path:
    return Path(__file__).resolve().parent.parent / "docs" / "virtualWorld" / "dev_tasks"


# ── dependency wikilinks ─────────────────────────────────────────────────
#
# The dependency keys above are the machine-readable graph, and Obsidian reads
# none of it: 746 of 885 cards linked to nothing at all. This section renders
# that same frontmatter as [[wikilinks]] so the relations are navigable in the
# vault.
#
# The block lives in the card preamble, ahead of the first ``## `` heading,
# because ``merge_card`` rewrites section bodies but carries the preamble
# through verbatim -- so a ``set --section`` cannot drop it.
#
# The link form is the bare basename (``[[task-570-hostile-distribution...]]``).
# Obsidian resolves a basename from any folder, so a ``move`` between status
# folders cannot break one, which is the same rule ``doc_links.py`` states and
# the reason ``move`` retargets inbound links. Every stem under dev_tasks is
# unique (899 distinct of 899), so a basename is never ambiguous.
#
# A ref that resolves to no card is left out rather than linked: a broken
# [[wikilink]] fails ``links``, and ``validate`` already warns about the
# dangling frontmatter ref itself.

DEPS_START = "<!-- deps:start -->"
DEPS_END = "<!-- deps:end -->"

# Emission order: what holds this card back, what it holds back, then the rest.
DEP_LINK_ORDER = ("blocked_by", "depends_on", "blocks", "children",
                  "parent", "supersedes", "related")
DEP_LABELS = {
    "blocked_by": "Blocked by",
    "depends_on": "Depends on",
    "blocks": "Blocks",
    "children": "Children",
    "parent": "Parent",
    "supersedes": "Supersedes",
    "related": "Related",
}


def dep_stems(root: Optional[Path] = None) -> Dict[str, str]:
    """``task-570`` -> ``task-570-hostile-distribution-consumer``, every card.

    The stem is the wikilink target. Built from the whole tree rather than from
    a filtered set, so a ref resolves no matter which cards a command is
    looking at.
    """
    root = root or default_root()
    out: Dict[str, str] = {}
    for e in iter_entries(root):
        if e.kind and e.id not in out:
            out[e.id] = e.path.stem
    return out


def _dep_lines(fm: Dict, stems: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """``(markdown lines, unresolved refs)`` for one card's dependency keys."""
    lines: List[str] = []
    unresolved: List[str] = []
    for key in DEP_LINK_ORDER:
        refs: List[str] = []
        for ref in _as_refs(fm.get(key)):
            if ref not in refs:
                refs.append(ref)
        links = [f"[[{stems[r]}]]" for r in refs if r in stems]
        unresolved.extend(f"{key}: {r}" for r in refs if r not in stems)
        if links:
            lines.append(f"**{DEP_LABELS[key]}:** " + ", ".join(links))
    return lines, unresolved


def dep_block(fm: Dict, stems: Dict[str, str]) -> str:
    """The marker-delimited block, or ``""`` when no dependency resolves."""
    lines, _ = _dep_lines(fm, stems)
    return "\n".join([DEPS_START, *lines, DEPS_END]) if lines else ""


def _join_block(before: str, after: str, block: str) -> str:
    """Splice ``block`` between two chunks, one blank line on each side."""
    if not block:
        if not after.strip():
            return before.rstrip("\n") + "\n"
        return before.rstrip("\n") + "\n\n" + after.lstrip("\n")
    if not after.strip():
        return before.rstrip("\n") + "\n\n" + block + "\n"
    return before.rstrip("\n") + "\n\n" + block + "\n\n" + after.lstrip("\n")


def refresh_dep_block(text: str, stems: Dict[str, str],
                      fm: Optional[Dict] = None) -> Tuple[str, List[str]]:
    """Return ``text`` with its dependency block inserted, refreshed or removed.

    Idempotent: the span between the markers is replaced wholesale, and a card
    whose dependencies have all gone loses the block instead of keeping a stale
    one. Returns ``(new_text, unresolved refs)``.
    """
    fm = parse_frontmatter(text)[0] if fm is None else fm
    block = dep_block(fm, stems)
    _, unresolved = _dep_lines(fm, stems)

    span = re.search(re.escape(DEPS_START) + r".*?" + re.escape(DEPS_END),
                     text, re.S)
    if span:
        return _join_block(text[:span.start()], text[span.end():], block), unresolved

    if not block:
        return text, unresolved

    m = H2_RE.search(text)
    if m:
        return _join_block(text[:m.start()], text[m.start():], block), unresolved
    return _join_block(text, "", block), unresolved


def _write_card(path: Path, text: str) -> None:
    """Write a card, keeping a UTF-8 BOM the file already carries.

    ``read_text`` strips one via utf-8-sig, so a plain utf-8 write would silently
    drop it from any card a migration touches. A handful of legacy cards carry
    one (the underscore-named bugs among them).
    """
    has_bom = path.read_bytes().startswith(b"\xef\xbb\xbf")
    path.write_text(text, encoding="utf-8-sig" if has_bom else "utf-8")


def dep_block_gap(text: str, stems: Dict[str, str]) -> str:
    """``""`` when a card's dependency block matches its frontmatter, else why.

    The rot guard: a card whose frontmatter names relations while its block is
    missing or stale reads as unlinked in Obsidian even though the graph knows
    better. It returns early for the ~92% of cards that carry no dependency, so
    the check is cheap, and it compares the block body rather than the whole
    file so incidental whitespace is not reported.
    """
    fm = parse_frontmatter(text)[0]
    if not any(_as_refs(fm.get(k)) for k in DEPENDENCY_KEYS):
        return ""
    want = dep_block(fm, stems)
    span = re.search(re.escape(DEPS_START) + r".*?" + re.escape(DEPS_END),
                     text, re.S)
    if span is None:
        return "has dependency frontmatter but no [[wikilink]] block" if want else ""
    if span.group(0) != want:
        return "dependency [[wikilink]] block is stale"
    return ""


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
    """Drop a leading ``task-123:``/``Bug 12 -`` prefix and tidy whitespace."""
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
    unparseable - the data is still returned as best-effort so the file stays
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


def validate_task_payload(payload: Dict, root: Path, *, allow_stubs: bool = False) -> List[str]:
    """Validate task creation payload against required fields, placeholders, and linked tasks."""
    if allow_stubs:
        return []

    errors: List[str] = []

    # 1. Content completeness (ban TODO / placeholder stubs)
    required_sections = ["what", "why", "how", "acceptance", "files"]
    for sec in required_sections:
        val = payload.get(sec)
        if val is None or (isinstance(val, (str, list, tuple)) and len(val) == 0):
            errors.append(f"missing required section '{sec}'")
        elif isinstance(val, str) and _is_stub(val):
            errors.append(f"section '{sec}' cannot be a placeholder or TODO")
        elif isinstance(val, (list, tuple)):
            clean = [str(x).strip() for x in val if str(x).strip()]
            if not clean:
                errors.append(f"section '{sec}' list cannot be empty")
            elif all(_is_stub(str(x)) for x in clean):
                errors.append(f"section '{sec}' items cannot all be TODOs")

    # 2. Browser UI verification
    bui = payload.get("browser_ui")
    if bui is None:
        errors.append("missing 'browser_ui' specification (must provide dict or text)")
    elif isinstance(bui, dict):
        home = str(bui.get("home") or "").strip()
        avail = str(bui.get("availability") or "").strip()
        if not home or _is_stub(home):
            errors.append("browser_ui.home is missing or a placeholder")
        if not avail or _is_stub(avail):
            errors.append("browser_ui.availability is missing or a placeholder")

        is_na = bool(re.match(r"(?i)^(?:not applicable|n/a|no browser ui|none)\b", home))
        if is_na:
            reason = str(bui.get("reason") or "").strip()
            alt = bui.get("alt_steps") or bui.get("alternative_steps")
            if not reason or _is_stub(reason):
                errors.append("browser_ui with N/A home must provide a valid 'reason'")
            if not alt:
                errors.append("browser_ui with N/A home must provide 'alt_steps'")
        else:
            steps = bui.get("steps") or bui.get("live_steps")
            if not steps:
                errors.append("browser_ui needs 'steps' (live verification steps)")
    elif isinstance(bui, str):
        if _is_stub(bui):
            errors.append("browser_ui cannot be a TODO stub")
        else:
            issue = browser_ui_issue(f"## Browser UI and intended live verification\n\n{bui}")
            if issue:
                errors.append(f"browser_ui issue: {issue}")

    # 3. Linked task validation
    # Keys can be in payload directly or under a 'linked' dict
    linked_dict = payload.get("linked", {}) if isinstance(payload.get("linked"), dict) else {}
    for key in DEPENDENCY_KEYS:
        val = payload.get(key) or linked_dict.get(key)
        if not val:
            continue
        refs = _as_refs(val)
        for ref in refs:
            m = REF_RE.match(ref)
            if not m:
                errors.append(f"invalid task reference format: '{ref}'")
                continue
            r_kind, r_num = m.group(1).lower(), int(m.group(2))
            found = find_by_id(iter_entries(root), r_kind, r_num)
            if not found:
                errors.append(f"linked {r_kind}-{r_num} does not exist in dev_tasks")

    return errors


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
    if key == "browser_ui" and isinstance(value, dict):
        home = str(value.get("home") or "").strip()
        avail = str(value.get("availability") or "").strip()
        lines = [
            f"Intended UI home: {home}",
            "",
            f"Current availability: {avail}",
            "",
        ]
        is_na = bool(re.match(r"(?i)^(?:not applicable|n/a|no browser ui|none)\b", home))
        if is_na:
            reason = str(value.get("reason") or "").strip()
            lines.extend([
                f"Why no browser UI: {reason}",
                "",
                "Alternative verification steps:",
            ])
            alt_steps = value.get("alt_steps") or value.get("alternative_steps") or []
            if isinstance(alt_steps, str):
                lines.append(alt_steps.strip())
            else:
                for i, s in enumerate(alt_steps, 1):
                    lines.append(f"{i}. {str(s).strip()}")
        else:
            lines.append("Live steps when available:")
            steps = value.get("steps") or value.get("live_steps") or []
            if isinstance(steps, str):
                lines.append(steps.strip())
            else:
                for i, s in enumerate(steps, 1):
                    lines.append(f"{i}. {str(s).strip()}")
        lines.extend([
            "",
            "This section defines intended access and live acceptance. It is not a claim "
            "that planned UI exists or works today. Current availability says what is "
            "implemented and verified now; the numbered steps say how to reach and test "
            "the intended surface once it is available.",
        ])
        return "\n".join(lines).strip()
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


def _payload_dep_block(payload: Dict, related: str,
                       stems: Optional[Dict[str, str]]) -> str:
    """The dependency block for a card ``new``/``add_task`` is about to write."""
    linked_dict = payload.get("linked", {}) if isinstance(payload.get("linked"), dict) else {}
    dep_fm = {k: payload.get(k) or linked_dict.get(k) for k in DEPENDENCY_KEYS if payload.get(k) or linked_dict.get(k)}
    if related and "related" not in dep_fm:
        dep_fm["related"] = related
    if not dep_fm:
        return ""
    return dep_block(dep_fm, dep_stems() if stems is None else stems)


def render_card(*, kind: str, num: int, title: str, status: str, area: str,
                priority: str, filed: str, related: str = "", wiki: str = "",
                payload: Optional[Dict] = None,
                stems: Optional[Dict[str, str]] = None) -> str:
    """Build a canonical card body (frontmatter + ordered sections).

    The section set is ``CANONICAL_SECTIONS``; ``payload`` may supply any of the
    canonical keys plus frontmatter fields (``horizon``, ``effort``, ``goal``,
    ``wiki`` and the dependency keys). Empty sections fall back to stubs, so a
    scaffolded card is always the right *shape* even before it is written into.

    ``stems`` maps a dependency id to its current file stem so the scaffolded
    card's ``[[wikilinks]]`` resolve; it defaults to a scan of the tree.
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
    linked_dict = payload.get("linked", {}) if isinstance(payload.get("linked"), dict) else {}
    for key in DEPENDENCY_KEYS:
        val = payload.get(key) or linked_dict.get(key)
        if val:
            fm.append(f"{key}: [{_fmt_refs(val)}]")

    rel = _fmt_refs(payload.get("related") or linked_dict.get("related") or related)
    out = ["---", *fm, "---", "",
           f"# {kind}-{num}: {title}", "",
           f"**Filed:** {filed}",
           f"**Related:** {rel}", ""]
    block = _payload_dep_block(payload, related, stems)
    if block:
        out += [block, ""]
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

    # Policy (task-797): a card must name the note it concerns, so that note can
    # carry a real changelog of the work that touched it. Without this the
    # task <-> feature edge is optional and the wiki has no history.
    if not (getattr(args, "wiki", "") or str(payload.get("wiki") or "").strip()):
        print("error: --wiki is required - name the note this card concerns, "
              'e.g. "[[Feature Map]]" or "[[World Building/Movement|Movement]]".',
              file=sys.stderr)
        return 1

    allow_stubs = getattr(args, "allow_stubs", False) or getattr(args, "scaffold", False)
    val_errors = validate_task_payload(payload, args.root, allow_stubs=allow_stubs)
    if val_errors:
        print("error: task payload validation failed (pass complete fields or use --allow-stubs):", file=sys.stderr)
        for err in val_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    area_dir.mkdir(parents=True, exist_ok=True)
    body = render_card(kind=args.kind, num=num, title=args.title, status=status,
                       area=args.area,
                       priority=str(payload.get("priority") or args.priority),
                       filed=_dt.date.today().isoformat(),
                       related=args.related, wiki=getattr(args, "wiki", "") or "",
                       payload=payload, stems=dep_stems(args.root))
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
    body = "---" + head + text[end:]
    # Right after `git mv`, a vault watcher (Obsidian's indexer, the Windows
    # indexer or Defender) can still hold the renamed file, and the first
    # write then fails with `OSError: [Errno 22] Invalid argument` on Windows.
    # That used to leave the card moved but its frontmatter still saying
    # `status: review`, and abort `move` before it retargeted inbound links.
    # Retry a few times before giving up.
    last: Optional[OSError] = None
    for attempt in range(6):
        try:
            path.write_text(body, encoding="utf-8")
            return
        except OSError as exc:
            last = exc
            time.sleep(0.15 * (attempt + 1))
    raise last if last else RuntimeError("status rewrite failed")



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
              sections: Optional[Dict[str, str]] = None,
              stems: Optional[Dict[str, str]] = None) -> str:
    """Return ``text`` with frontmatter fields and/or sections updated.

    Pure (no I/O) so ``set`` and the MCP skin share it. With ``sections`` it
    replaces those canonical sections in place and touches nothing else; with
    only ``fm_updates`` it rewrites just those frontmatter keys.

    Writing a dependency key also refreshes the card's ``[[wikilink]]`` block
    from the merged frontmatter, so the links cannot describe the previous
    relations. ``stems`` maps a dependency id to its current file stem and
    defaults to a scan of the tree.
    """
    if sections:
        new_text = merge_card(text, sections, overwrite=True, add_missing=False,
                              preserve_order=True, fm_updates=fm_updates)
    else:
        fm_block = _split_frontmatter(text)
        if fm_block is None:
            # A legacy card with no frontmatter block (it carried a prose
            # `**Status:**` header instead): synthesize one above the body so
            # `set` can still record a field.
            new_text = ("---" + _update_frontmatter("", fm_updates)
                        + "\n---\n\n" + text.lstrip("\n"))
        else:
            end = text.find("\n---", 3)
            new_text = "---" + _update_frontmatter(fm_block, fm_updates) + text[end:]

    if any(key in fm_updates for key in DEPENDENCY_KEYS):
        merged = dict(parse_frontmatter(text)[0])
        merged.update({k: v for k, v in fm_updates.items()
                       if k in DEPENDENCY_KEYS})
        new_text, _ = refresh_dep_block(
            new_text, dep_stems() if stems is None else stems, fm=merged)
    return new_text


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
    if getattr(args, "status", None) is not None:
        print("error: use move to change status, not set "
              f"({args.kind}-{args.id}); status lives in the folder, "
              "frontmatter is advisory", file=sys.stderr)
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
        new_text = apply_set(text, fm_updates, sections,
                             stems=dep_stems(args.root))
    except ValueError as exc:
        print(f"error: {entry.path}: {exc}", file=sys.stderr)
        return 1

    if new_text == text:
        print(f"unchanged: {entry.path}")
        return 0
    _write_card(entry.path, new_text)
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
    critical = _longest_path(sorted(cards), succ, pred, cards=cards) if cards else []
    review = [e for e in entries if e.status == "review"]

    lines = ["# Roadmap", "",
             "*Generated by `python tools/tasks.py roadmap` - do not edit by hand.*", "",
             f"**{counts['by_status'].get('todo', 0) + counts['by_status'].get('inprogress', 0)} "
             f"actionable** - todo {counts['by_status'].get('todo', 0)}, "
             f"inprogress {counts['by_status'].get('inprogress', 0)}"
             f"  ·  **{len(review)} in review** (verification queue)", ""]

    def section(title: str, blurb: str, picked: List[Entry]) -> None:
        lines.extend([f"## {title} - {len(picked)}", "", blurb, ""])
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


def _longest_path(nodes, succ, pred, cards: Optional[Dict[str, Entry]] = None) -> List[str]:
    """Longest chain of nodes in the DAG (by node count). ``[]`` if cyclic or no chain.

    When ``cards`` is supplied, terminal cards ({'done', 'cancelled'}) are
    excluded from the traversal so the critical path describes remaining open work
    rather than completed historical chains (task-819).
    """
    if cards is not None:
        nodes = [n for n in nodes if cards.get(n) and cards[n].status not in TERMINAL_STATUSES]
        succ = {n: [s for s in succ.get(n, []) if cards.get(s) and cards[s].status not in TERMINAL_STATUSES] for n in nodes}
        pred = {n: [p for p in pred.get(n, []) if cards.get(p) and cards[p].status not in TERMINAL_STATUSES] for n in nodes}
    if not nodes:
        return []
    indeg = {n: len(pred[n]) for n in nodes}
    dist = {n: 1 for n in nodes}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes}
    q = deque(sorted(n for n in nodes if indeg[n] == 0))
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for m in sorted(succ.get(n, [])):
            if dist[n] + 1 > dist[m]:
                dist[m] = dist[n] + 1
                prev[m] = n
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    if seen != len(nodes):
        return []
    end = max(nodes, key=lambda n: dist[n])
    if dist[end] <= 1:
        return []
    path = []
    node: Optional[str] = end
    while node is not None:
        path.append(node)
        node = prev[node]
    return list(reversed(path))


def _unblocks(card_id: str, cards, succ) -> int:
    """Open cards that become startable once ``card_id`` is terminal.

    Scheduling note (task-819): TERMINAL_STATUSES remains {'done', 'cancelled'}.
    Cards in 'review' stay non-terminal for scheduling; work must not start on
    unverified implementations before they land in master.
    """
    return sum(1 for s in succ[card_id] if cards[s].status not in TERMINAL_STATUSES)


def cmd_graph(args) -> int:
    """Report dependency edges, cycles and the critical path. Read-only."""
    entries = [e for e in iter_entries(args.root) if e.kind]
    cards, succ, pred = _dep_graph(entries)
    nodes = sorted(cards)
    edges = sorted((a, b) for a in succ for b in succ[a])
    cycles = _find_cycles(nodes, succ)
    path = _longest_path(nodes, succ, pred, cards=cards)
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

    Scheduling note (task-819): Predecessors must be in TERMINAL_STATUSES
    ({'done', 'cancelled'}). Cards in 'review' stay non-terminal to prevent
    building on unverified work before it lands in master.
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

    The ``observed: TODO`` check covers ``review`` as well as ``done``: a card
    claiming to be under review with nothing recorded as observed is exactly
    the "acceptance criteria never demonstrated live" case the filing
    discipline forbids, and it is cheaper to catch at the review gate than at
    the done gate.
    """
    out: List[str] = []
    for e in entries:
        if not e.kind or e.status not in ("todo", "inprogress", "review", "done"):
            continue
        text = try_read_text(e.path)
        miss = missing_sections(text)
        if miss:
            out.append(f"{e.id} ({e.status}) missing section(s): {', '.join(miss)}")
        sections = body_sections(text)
        if "browser_ui" in sections:
            ui_issue = browser_ui_issue(text)
            if ui_issue:
                out.append(f"{e.id} ({e.status}) browser UI intent: {ui_issue}")
        needs = _frontmatter_needs(text)
        if needs:
            out.append(f"{e.id} ({e.status}) missing frontmatter: {', '.join(needs)}")
        if e.status == "done":
            secs = body_sections(text)
            if re.search(r"^\s*-\s*\[ \]", secs.get("acceptance", ""), re.MULTILINE):
                out.append(f"{e.id} done with an unchecked acceptance box")
        if e.status in ("review", "done"):
            secs = body_sections(text)
            if re.search(r"observed\s*:\s*TODO", secs.get("verify", ""), re.IGNORECASE):
                out.append(f"{e.id} {e.status} with observed: TODO")
    return out


def cmd_validate(args) -> int:
    entries = iter_entries(args.root)
    errors: List[str] = []
    warnings: List[str] = []
    stems = {e.id: e.path.stem for e in entries if e.kind}

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
    browser_ui_statuses = {"todo", "inprogress", "review", "done"}
    browser_ui_root = Path(args.root).resolve()
    browser_gaps = []
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
            errors.append(
                f"frontmatter status '{fm_status}' != folder '{e.status}': {e.path} (run move, never hand-edit status)")

        # Referenced ids. Prose lines and frontmatter lists both count.
        text = try_read_text(e.path)
        try:
            folder_status = e.path.resolve().relative_to(browser_ui_root).parts[0]
        except (ValueError, IndexError):
            folder_status = ""
        frontmatter = e.frontmatter()
        declared_status = _norm(str(frontmatter.get("status") or ""))
        declared_type = _norm(str(frontmatter.get("type") or ""))
        is_task_card = bool(e.kind) or declared_type in {"task", "bug"} or bool(
            re.match(r"^(?:task|bug)-", e.path.name, re.IGNORECASE))
        browser_ui_eligible = (
            is_task_card
            and (folder_status in browser_ui_statuses or e.status in browser_ui_statuses)
            and folder_status != "cancelled"
            and e.status not in {"cancelled", "superseded"}
            and declared_status not in {"cancelled", "superseded"}
        )
        if browser_ui_eligible:
            ui_issue = browser_ui_issue(text)
            if ui_issue:
                browser_gaps.append((e.id or e.path.stem, ui_issue))
        lines = text.splitlines()
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

        gap = dep_block_gap(text, stems)
        if gap:
            warnings.append(f"{e.id}: {gap} (run link-deps --write)")

    # wiki: policy. A card with no `wiki:` is not tied to any note, so that note
    # cannot show a changelog of the work that touched it. Reported as one count
    # rather than per card: most of the tree predates the policy, and 900 lines
    # of the same warning is noise, not signal.
    open_no_wiki = [
        e.id for e in entries
        if e.kind and e.status in ("todo", "inprogress")
        and not str(e.frontmatter().get("wiki") or "").strip()
    ]
    if open_no_wiki:
        warnings.append(
            f"{len(open_no_wiki)} open card(s) carry no `wiki:` - policy: a new "
            'card must name the note it concerns (e.g. "[[Feature Map]]")')

    # Browser acceptance is required for all non-cancelled, non-superseded task
    # cards in todo/inprogress/review/done, including legacy done-folder cards
    # whose filenames do not parse into an id. Keep gaps aggregated in normal
    # output; --schema lists the affected cards individually.
    if browser_gaps:
        examples = ", ".join(f"{task_id}: {issue}" for task_id, issue in browser_gaps[:4])
        suffix = "" if len(browser_gaps) <= 4 else f" (+{len(browser_gaps) - 4} more)"
        warnings.append(
            f"{len(browser_gaps)} non-cancelled card(s) have missing/incomplete browser UI intent: "
            f"{examples}{suffix}; run validate --schema for per-card details")

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


def cmd_link_deps(args) -> int:
    """Render each card's dependency frontmatter as [[wikilinks]].

    This is the migration and the repair for the dependency block: it walks the
    cards, renders the frontmatter keys (``blocked_by``, ``depends_on``,
    ``blocks``, ``children``, ``parent``, ``supersedes``, ``related``) as
    basename wikilinks, and inserts, refreshes or removes the marker-delimited
    block to match. Default is a dry run; ``--write`` applies it. A ref that
    resolves to no card is reported and left out, so the run cannot create a
    broken link.
    """
    wanted = set(args.status) if getattr(args, "status", None) else set(STATUSES)
    entries = [e for e in iter_entries(args.root) if e.kind and e.status in wanted]
    stems = dep_stems(args.root)

    changed: List[Tuple[Entry, str, List[str]]] = []
    unresolved_all: List[str] = []
    links_added = 0
    for e in sorted(entries, key=lambda x: (x.kind, x.num)):
        text = try_read_text(e.path)
        if not text:
            continue
        new_text, unresolved = refresh_dep_block(text, stems)
        if unresolved:
            unresolved_all.extend(f"{e.id}: {u}" for u in unresolved)
        if new_text != text:
            # Only the block changes, so the delta is the links it added (or,
            # for a card whose deps all vanished, removed).
            links_added += (new_text.count("[[") - text.count("[["))
            changed.append((e, new_text, unresolved))

    write = getattr(args, "write", False)
    if getattr(args, "json", False):
        print(json.dumps({
            "scanned": len(entries), "cards_to_change": len(changed),
            "written": len(changed) if write else 0,
            "links_added": links_added,
            "unresolved": unresolved_all,
            "cards": [{"id": e.id, "status": e.status, "area": e.area}
                      for e, _t, _u in changed]}, indent=2))
        return 0

    for e, _new_text, unresolved in changed:
        note = f"  ({len(unresolved)} unresolved)" if unresolved else ""
        print(f"{e.id:<10} {e.status:<10} {e.area:<12}{note}")
    for u in unresolved_all:
        print(f"warn: unresolved dependency ref {u}", file=sys.stderr)

    if write:
        for e, new_text, _u in changed:
            _write_card(e.path, new_text)
        print(f"\n{len(entries)} cards scanned, {len(changed)} rewritten, "
              f"{links_added} link line(s), {len(unresolved_all)} unresolved")
    else:
        print(f"\n{len(entries)} cards scanned, {len(changed)} would change, "
              f"{len(unresolved_all)} unresolved")
        print("(dry run - re-run with --write to apply)")
    return 0


def _norm(status: str) -> str:
    return status.strip().lower().replace("_", "").replace("-", "")


# ── cli ──────────────────────────────────────────────────────────────────


HELP_TEXT = """\
Virtual World dev-task helper - allocate ids, scaffold, move, list, validate.

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
    link-deps render dependency frontmatter as [[wikilinks]] (repair/migration)
    index     rebuild or clear the derived frontmatter cache
    status    counts by status / area / horizon
    roadmap   generate the roadmap view from folders + horizon
    graph     dependency edges, cycles and the critical path
    next      rank the open cards that can start now
    backfill  report the canonical-schema gap (including browser UI intent)
    help      show this guide, or `help <command>` for one command

Run with no command for the interactive menu: `?` lists the keys, `x` cancels
one action, `q` quits. It keeps the card in hand, the kind and area last used,
and an undo stack for this session; nothing is persisted.

Statuses: todo / inprogress / review / done / cancelled
Kinds:    task / bug
Areas:    read from the folders that exist under each status, so the menu
          lists the real ones. `--area` accepts any name and creates it.

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
new --area AREA --title TITLE --wiki NOTE [--json PAYLOAD] [--kind task|bug]
    [--priority medium] [--status todo] [--related "..."] [--goal "..."]
    [--allow-stubs] [--force]

Create a new file at <root>/<status>/<area>/<kind>-<num>-<slug>.md. By default,
cards must be fully specified (What, Why, How, Browser UI intent, Acceptance, Files)
and cannot contain TODO placeholders. Pass full card content via --json (@file or string).

  --area        topic folder, e.g. gameplay, ui, graph (required)
  --title       human title; also sets the H1 and slug (required)
  --wiki        Obsidian note this concerns, e.g. "[[Feature Map]]" (required)
  --json        JSON object containing section bodies, browser_ui, and linked tasks
  --allow-stubs permit placeholder/TODO stubs (default: rejected)
  --kind        task (default) or bug
  --priority    free text, default medium
  --status      starting folder, default todo
  --related     value for the Related line, e.g. task-409
  --goal        text under What / Goal
  --force       overwrite if the target path already exists

  python tools/tasks.py new --area ui --title "Compass polish" --wiki "[[Feature Map]]" --json @task.json
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
  --section   one of: what why how browser_ui verify acceptance files
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
a status folder, frontmatter/folder status mismatches, dangling references,
and missing/incomplete browser UI intent on non-cancelled cards, including done.
Browser UI intent
describes the intended UI home and live acceptance path; it does not claim the
UI is implemented or testable today.

  --quiet   suppress warnings, print only errors and the summary
  --schema  also list per-card canonical-schema gaps: missing sections or
            frontmatter, incomplete browser UI intent, unchecked done
            acceptance, or review/done verification whose observed still
            reads TODO

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
    "link-deps": """\
link-deps [--status STATUS...] [--write] [--json]

Render each card's dependency frontmatter (related, blocked_by, depends_on,
blocks, children, parent, supersedes) as [[wikilinks]] in the card preamble,
between `<!-- deps:start -->` and `<!-- deps:end -->`. The dependency keys are
the machine-readable graph and Obsidian reads none of them, so a card's
relations were invisible in the vault.

Links are the bare basename ([[task-570-hostile-distribution-consumer]]), which
Obsidian resolves from any folder, so a `move` between status folders cannot
break one. A ref that resolves to no card is reported and left out, so a run
never creates a broken link.

Idempotent: the block is replaced wholesale, and a card whose dependencies all
disappeared loses the block. `new` and `set` keep the block in step when they
write a dependency, so this is the migration for cards written before it
existed and the repair for one edited by hand.

  --status  limit to cards in these status folders (default: all)
  --write   apply the block (default is a dry run that prints what would change)
  --json    machine-readable summary

  python tools/tasks.py link-deps
  python tools/tasks.py link-deps --write
  python tools/tasks.py link-deps --status todo inprogress review --write
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
headings to rename, the canonical sections it lacks (including Browser UI and
intended live verification), and the frontmatter keys it lacks. The browser
section records intended access and future live steps separately from whether
the UI is available today. Steps to verify holds expected and observed results.

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
#
# The menu is the surface a human uses by hand, so it holds a little state
# between actions: the kind and area last used, the card in hand, and a journal
# of what this session changed so a wrong keystroke can be reversed. Every
# mutation still goes through the same ``cmd_*`` function the flags use, so the
# two surfaces cannot drift apart. None of this is persisted: the session is a
# convenience, never a second source of truth.

CHECKBOX_RE = re.compile(r"^(\s*)-\s*\[([ xX])\]\s*(.*)$")
SECTION_MARK_RE = re.compile(r"^##\s+(.+?)\s*$")
MENU_ROW_LIMIT = 40
LOG_HEADING = "## Log"


class _Cancel(Exception):
    """The user aborted one action (``x`` or Ctrl+C). Not an error."""


class _Quit(Exception):
    """End of input: leave the menu the same way ``q`` does."""


def card_body(text: str) -> str:
    """The body after the frontmatter block, or the whole text when absent."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def card_checkboxes(text: str) -> List[Dict]:
    """Every checkbox in a card, in file order, with the section it sits in.

    ``line`` is the zero-based line in ``text`` (so a caller can rewrite that
    exact line), ``section`` is the canonical key it belongs to or "" for a
    section the schema does not own.
    """
    out: List[Dict] = []
    section_key = ""
    for i, line in enumerate(text.splitlines()):
        mark = SECTION_MARK_RE.match(line)
        if mark:
            section_key = SECTION_KEY_BY_HEADING.get(mark.group(1).strip().lower(), "")
            continue
        box = CHECKBOX_RE.match(line)
        if box:
            out.append({"line": i,
                        "number": len(out) + 1,
                        "section": section_key,
                        "checked": box.group(2).lower() == "x",
                        "label": box.group(3).strip()})
    return out


def set_checkbox(text: str, number: int, checked: bool = True,
                 observed: Optional[str] = None) -> Tuple[str, str]:
    """Tick (or untick) one checkbox, optionally recording what was observed.

    Returns ``(new_text, label)``. ``observed`` rewrites the ``- observed:``
    line under the box when it already has one and inserts one when it does
    not, so ticking a box and recording what was actually seen is one edit.
    Raises ``IndexError`` for a number the card does not have.
    """
    boxes = card_checkboxes(text)
    if number < 1 or number > len(boxes):
        raise IndexError(f"no checkbox {number} (the card has {len(boxes)})")
    box = boxes[number - 1]
    lines = text.splitlines()
    match = CHECKBOX_RE.match(lines[box["line"]])
    gap = match.group(1) if match else ""
    lines[box["line"]] = f"{gap}- [{'x' if checked else ' '}] {box['label']}"
    if observed is not None:
        note = re.sub(r"\s+", " ", str(observed)).strip()
        obs = f"{gap}  - observed: {note}"
        nxt = box["line"] + 1
        if nxt < len(lines) and re.match(r"^\s*-\s*observed\s*:", lines[nxt], re.I):
            lines[nxt] = obs
        else:
            lines.insert(nxt, obs)
    return "\n".join(lines).rstrip("\n") + "\n", box["label"]


def format_card_body(text: str) -> List[str]:
    """The body lines with every checkbox numbered, so ``check 3`` is unambiguous."""
    out: List[str] = []
    number = 0
    for line in card_body(text).splitlines():
        box = CHECKBOX_RE.match(line)
        if box:
            number += 1
            out.append(f"{box.group(1)}[{number}] "
                       f"[{'x' if box.group(2).lower() == 'x' else ' '}] "
                       f"{box.group(3)}")
            continue
        out.append(line)
    return out


def append_log_line(text: str, note: str,
                    when: Optional[str] = None) -> str:
    """Append a dated line to the card's ``## Log`` section, creating it.

    The card is the log of the work (the tree's own rule), so recording what
    happened must cost one line rather than an editor round trip.
    """
    note = re.sub(r"\s+", " ", str(note)).strip()
    if not note:
        raise ValueError("empty log note")
    stamp = (when or _dt.date.today().isoformat()) + " - " + note
    lines = text.rstrip("\n").splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.strip().lower() == LOG_HEADING.lower()), None)
    if start is None:
        return "\n".join(lines + ["", LOG_HEADING, "", "- " + stamp]) + "\n"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if SECTION_MARK_RE.match(lines[j]):
            end = j
            break
    body = lines[start + 1:end]
    while body and not body[-1].strip():
        body.pop()
    body.append("- " + stamp)
    tail = [""] + lines[end:] if end < len(lines) else []
    return "\n".join(lines[:start + 1] + body + tail) + "\n"


CARD_QUERY_RE = re.compile(r"^(?:(task|bug)\s*[-#]?\s*)?(\d+)$", re.IGNORECASE)


def resolve_cards(entries: List[Entry], query: str,
                  kind: Optional[str] = None) -> List[Entry]:
    """Find the cards a typed reference could mean.

    Accepts ``504``, ``task 504``, ``bug-12`` or a fragment of the title or
    slug. An exact id wins outright; only when the query is not id-shaped is a
    case-insensitive substring tried, so a number never returns a card that
    merely mentions it.
    """
    q = str(query or "").strip()
    if not q:
        return []
    cards = [e for e in entries if e.kind]
    match = CARD_QUERY_RE.match(q)
    if match:
        wanted = (match.group(1) or kind or "").lower()
        num = int(match.group(2))
        hits = [e for e in cards
                if e.num == num and (not wanted or e.kind == wanted)]
        if hits:
            return sorted(hits, key=lambda e: e.num)
        # The id exists under the other kind: offer it rather than "not found".
        return sorted([e for e in cards if e.num == num], key=lambda e: e.num)
    needle = q.lower()
    return sorted([e for e in cards
                   if needle in e.title().lower() or needle in e.slug.lower()],
                  key=lambda e: e.num)


def card_age_days(entry: Entry, now: Optional[_dt.date] = None) -> int:
    """Days since the card was last touched, or 0 when it cannot be read."""
    try:
        stamp = _dt.date.fromtimestamp(entry.path.stat().st_mtime)
    except OSError:
        return 0
    return max(0, ((now or _dt.date.today()) - stamp).days)


def area_names(root: Path) -> List[str]:
    """The area folders that actually exist, sorted.

    The disk is the source of truth here for the same reason the folder is
    authoritative for status: a hardcoded list drifts from the tree it claims
    to describe.
    """
    seen = set()
    for status in STATUSES:
        parent = root / status
        if parent.is_dir():
            seen.update(p.name for p in parent.iterdir() if p.is_dir())
    return sorted(seen)


def _as_int(raw: str) -> Optional[int]:
    return int(raw) if raw.lstrip("-").isdigit() else None


class Session:
    """What the menu remembers between actions.

    Deliberately small and in memory only: kind, area and the card in hand are
    conveniences, and the journal is a this-session undo stack.
    """

    def __init__(self, root: Path):
        self.root = root
        self.kind = "task"
        self.area = ""
        self.current: Optional[Entry] = None
        self.journal: List[Dict] = []
        self.last_validate: Optional[Tuple[str, int]] = None

    def entries(self) -> List[Entry]:
        return iter_entries(self.root)

    def record_write(self, path: Path) -> None:
        """Snapshot a card before it is rewritten, so the write can be undone."""
        self.journal.append({"op": "write", "path": path, "before": read_text(path)})

    def record_move(self, src: Path, dst: Path) -> None:
        self.journal.append({"op": "move", "src": src, "dst": dst})

    def refresh_current(self) -> None:
        if self.current is None:
            return
        hits = resolve_cards(self.entries(), self.current.id)
        self.current = hits[0] if hits else None


# ── menu input ───────────────────────────────────────────────────────────


def _menu_input(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    tail = "" if prompt.endswith((" ", ">")) else ": "
    try:
        value = input(f"{prompt}{hint}{tail}")
    except EOFError:
        print()
        raise _Quit
    except KeyboardInterrupt:
        print()
        raise _Cancel
    value = value.strip()
    if value.lower() in ("x", "cancel", ":q"):
        raise _Cancel
    return value or default


def _menu_choice(prompt: str, choices, default: str) -> str:
    while True:
        raw = _menu_input(f"{prompt} [{'/'.join(choices)}]", default).lower()
        if raw in choices:
            return raw
        print(f"  please enter one of: {', '.join(choices)}")


def _menu_optional_choice(prompt: str, choices):
    while True:
        raw = _menu_input(f"{prompt} [{'/'.join(choices)}] (blank = any)").lower()
        if not raw:
            return None
        if raw in choices:
            return raw
        print(f"  please enter one of: {', '.join(choices)} (or blank)")


def _menu_int(prompt: str, lo: Optional[int] = None,
              hi: Optional[int] = None) -> Optional[int]:
    while True:
        raw = _menu_input(prompt)
        if not raw:
            return None
        value = _as_int(raw)
        if value is not None and (lo is None or value >= lo) and (hi is None or value <= hi):
            return value
        span = f"{lo}-{hi}" if lo is not None and hi is not None else "a number"
        print(f"  please enter {span}, or blank to cancel")


def _menu_multiline(prompt: str) -> str:
    print(f"  {prompt} (end with a single `.` on its own line)")
    lines: List[str] = []
    while True:
        line = _menu_input("  | ")
        if line == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _prompt(session: Session) -> str:
    counts = Counter(e.status for e in session.entries() if e.kind)
    hand = (f"{session.current.id} {session.current.status}"
            if session.current else "no card in hand")
    return (f"\n{counts.get('todo', 0)} todo | {counts.get('inprogress', 0)} active"
            f" | {counts.get('review', 0)} review  [{hand}] > ")


def _print_header(session: Session) -> None:
    counts = Counter(e.status or "?" for e in session.entries() if e.kind)
    print()
    print("  " + "  ".join(f"{s} {counts.get(s, 0)}" for s in STATUSES))
    if session.last_validate:
        stamp, code = session.last_validate
        print(f"  last validate at {stamp}: " + ("clean" if code == 0 else "errors, run v"))


def _print_session_end(session: Session) -> None:
    if not session.journal:
        print("  no changes this session")
        return
    print(f"  {len(session.journal)} change(s) this session:")
    for item in session.journal[-10:]:
        if item["op"] == "write":
            print(f"   write  {item['path'].name}")
        else:
            print(f"   move   {item['src'].name} -> {item['dst'].parent.parent.name}")


def _paged(lines: List[str]) -> None:
    """Print with a pager when a human is at the terminal; never when piped."""
    if not sys.stdin.isatty():
        print("\n".join(lines))
        return
    height = max(10, shutil.get_terminal_size((100, 30)).lines - 4)
    i = 0
    while i < len(lines):
        print("\n".join(lines[i:i + height]))
        i += height
        if i < len(lines):
            try:
                if input("  -- more -- (enter, or q) ").strip().lower() == "q":
                    print()
                    return
            except (EOFError, KeyboardInterrupt):
                print()
                return


# ── card lookups ─────────────────────────────────────────────────────────


def _pick_card(session: Session, query: str,
               kind: Optional[str] = None) -> Optional[Entry]:
    """Resolve one card from a typed reference, asking when it is ambiguous."""
    hits = resolve_cards(session.entries(), query, kind=kind)
    if not hits:
        print(f"  no card matches {query!r}")
        return None
    if len(hits) == 1:
        return hits[0]
    shown = hits[:MENU_ROW_LIMIT]
    for i, entry in enumerate(shown, 1):
        print(f"  {i:>2}) {entry.id:<10} {entry.status:<10} "
              f"{entry.area:<12} {entry.title()}")
    if len(hits) > len(shown):
        print(f"  ... and {len(hits) - len(shown)} more; narrow the query")
    pick = _menu_int("which", 1, len(shown))
    return shown[pick - 1] if pick else None


def _card_in_hand(session: Session) -> Optional[Entry]:
    if session.current is not None:
        return session.current
    card = _pick_card(session, _menu_input("card (id, or part of the title)"))
    if card:
        session.current = card
    return card


def _target(session: Session, query: str = "") -> Optional[Entry]:
    """The card a command acts on: the typed one, else the one in hand."""
    if not query:
        return _card_in_hand(session)
    card = _pick_card(session, query)
    if card:
        session.current = card
    return card


def format_card_preview(text: str) -> List[str]:
    """A compact scaffold preview: the frontmatter, then each section's state.

    Printing the whole stub template buries the two decisions that matter (what
    the card says and how much of it is still placeholder), so the preview shows
    the shape and marks each empty section instead.
    """
    out: List[str] = []
    head = _split_frontmatter(text)
    if head is not None:
        out.append("---")
        out.extend(head.strip("\n").splitlines())
        out.append("---")
    body = card_body(text)
    title = next((line for line in body.splitlines() if line.startswith("# ")), "")
    if title:
        out.append(title)
    sections = body_sections(text)
    for key, _heading, _aliases in CANONICAL_SECTIONS:
        value = (sections.get(key) or "").strip()
        stub_text = SECTION_STUBS.get(key, "").strip()
        if not value:
            state = "(missing)"
        elif _is_stub(value) or (stub_text and value == stub_text):
            state = "(TODO stub)"
        else:
            state = " ".join(value.split())[:60]
        out.append(f"  {key:<11} {state}")
    return out


def _recent_wikis(session: Session, limit: int = 8) -> List[str]:
    counts = Counter(str(e.frontmatter().get("wiki") or "").strip()
                     for e in session.entries() if e.kind)
    counts.pop("", None)
    return [wiki for wiki, _n in counts.most_common(limit)]


def _done_blockers(card: Entry) -> List[str]:
    """Why a card should not be filed as done yet, in the schema's own terms."""
    text = read_text(card.path)
    out: List[str] = []
    unchecked = [b for b in card_checkboxes(text) if not b["checked"]]
    if unchecked:
        out.append(f"{len(unchecked)} unchecked box(es)")
    verify = body_sections(text).get("verify", "")
    if re.search(r"observed\s*:\s*TODO", verify, re.IGNORECASE):
        out.append("observed: TODO in Steps to verify")
    return out


def _show_card(card: Entry, session: Session) -> None:
    text = read_text(card.path)
    fm = card.frontmatter()
    print()
    print(f"{card.id}  {card.title()}")
    print(f"  status={card.status}  area={card.area or '-'}  "
          f"priority={fm.get('priority') or '-'}  horizon={fm.get('horizon') or '-'}")
    print(f"  wiki={fm.get('wiki') or '-'}")
    for key in DEPENDENCY_KEYS:
        refs = _as_refs(fm.get(key))
        if refs:
            print(f"  {key.replace('_', ' ')}: {', '.join(refs)}")
    print(f"  path={card.path.relative_to(session.root).as_posix()}")
    gaps = _schema_warnings([card])
    if gaps:
        print(f"  {len(gaps)} schema gap(s):")
        for gap in gaps:
            print(f"    - {gap}")
    print()
    _paged(format_card_body(text))


# ── menu actions ─────────────────────────────────────────────────────────


def _cmd_show(session: Session, query: str = "") -> None:
    card = (_target(session, query) if query
            else _pick_card(session, _menu_input("card (blank = in hand)")))
    if card:
        session.current = card
        _show_card(card, session)


def _cmd_use(session: Session, query: str = "") -> None:
    card = _pick_card(session, query or _menu_input("card"))
    if card:
        session.current = card
        print(f"  in hand: {card.id}  {card.title()}")


def _cmd_check(session: Session, query: str = "") -> None:
    card = _target(session, query)
    if not card:
        return
    text = read_text(card.path)
    boxes = card_checkboxes(text)
    if not boxes:
        print("  this card has no checkboxes")
        return
    print(f"  {card.id}  {card.title()}")
    for box in boxes:
        print(f"  [{box['number']}] [{'x' if box['checked'] else ' '}] "
              f"{box['label']}  ({box['section'] or 'unsectioned'})")
    number = _menu_int("tick which", 1, len(boxes))
    if number is None:
        return
    observed = None
    if boxes[number - 1]["section"] in ("verify", "acceptance"):
        observed = _menu_input("observed (blank = leave the line alone)")
    try:
        new_text, label = set_checkbox(text, number, True, observed or None)
    except IndexError as exc:
        print(f"  {exc}")
        return
    session.record_write(card.path)
    _write_card(card.path, new_text)
    print(f"  ticked: {label}")


def _cmd_note(session: Session, query: str = "") -> None:
    card = _target(session, query)
    if not card:
        return
    note = _menu_input("note")
    if not note:
        print("  nothing recorded")
        return
    session.record_write(card.path)
    _write_card(card.path, append_log_line(read_text(card.path), note))
    print(f"  logged on {card.id}")


_FLOW = {"todo": "inprogress", "inprogress": "review", "review": "done",
         "done": "done", "cancelled": "todo"}


def _cmd_move(session: Session, query: str = "") -> None:
    card = _target(session, query)
    if not card:
        return
    if not card.status:
        print(f"  {card.path} is not under a status folder")
        return
    status = _menu_choice("to status", STATUSES,
                          _FLOW.get(card.status, "todo"))
    if status == card.status:
        print(f"  {card.id} is already in {status}")
        return
    print(f"  {card.id}  {card.status} -> {status}   {card.title()}")
    blockers = _done_blockers(card) if status == "done" else []
    if blockers:
        print("  not verified: " + "; ".join(blockers))
        if _menu_input('type "close" to file it anyway').lower() != "close":
            print("  cancelled")
            return
    elif _menu_input("move it", "y").lower() not in ("y", "yes"):
        print("  cancelled")
        return
    dst = session.root / status / card.path.relative_to(session.root / card.status)
    if cmd_move(argparse.Namespace(root=session.root, kind=card.kind,
                                   id=card.num, status=status)) != 0:
        return
    session.record_move(card.path, dst)
    card.path, card.status = dst, status


def _menu_area(session: Session) -> str:
    areas = area_names(session.root)
    if areas:
        print("  areas on disk: " + ", ".join(areas))
    raw = _menu_input("area", session.area)
    if not raw:
        return ""
    if raw not in areas:
        print(f"  note: {raw!r} is not an existing area folder; it will be created")
    session.area = raw
    return raw


def _menu_wiki(session: Session) -> str:
    recent = _recent_wikis(session)
    if recent:
        print("  recently used notes:")
        for i, wiki in enumerate(recent, 1):
            print(f"  {i}) {wiki}")
    raw = _menu_input("wiki note, e.g. [[Feature Map]]")
    if not raw:
        return ""
    if raw.isdigit() and recent and 1 <= int(raw) <= len(recent):
        return recent[int(raw) - 1]
    if not raw.startswith("[["):
        raw = f"[[{raw.strip('[]').strip()}]]"
    return raw


def _cmd_add(session: Session) -> None:
    """Scaffold a card, showing exactly what stubs it will carry first."""
    kind = _menu_choice("kind", KINDS, session.kind)
    area = _menu_area(session)
    if not area:
        return
    title = _menu_input("title")
    if not title:
        print("  title is required")
        return
    status = _menu_choice("status", STATUSES, "todo")
    priority = _menu_choice("priority", PRIORITIES, "medium")
    wiki = _menu_wiki(session)
    if not wiki:
        print("  a card must name the note it concerns (that is the wiki policy)")
        return
    what = _menu_input("what is it, one line (blank = TODO)")
    horizon = _menu_optional_choice("horizon", HORIZONS)

    num = next_id(session.root, kind)
    payload: Dict = {"wiki": wiki}
    if what:
        payload["what"] = what
    if horizon:
        payload["horizon"] = horizon
    preview = render_card(kind=kind, num=num, title=title, status=status,
                          area=area, priority=priority,
                          filed=_dt.date.today().isoformat(),
                          wiki=wiki, payload=payload,
                          stems=dep_stems(session.root))
    stubs = [key for key in SECTION_TITLE_BY_KEY if not payload.get(key)]
    print()
    _paged(format_card_preview(preview))
    print()
    print(f"  {len(stubs)} of {len(SECTION_TITLE_BY_KEY)} section(s) would be "
          f"TODO stubs: {', '.join(stubs)}")
    print("  the tree rejects stub cards unless the stub is explicit "
          "(filing discipline in AGENTS.md).")
    if _menu_input('type "stub" to file it anyway').lower() != "stub":
        print("  cancelled, nothing written")
        return
    if cmd_new(argparse.Namespace(
            root=session.root, kind=kind, area=area, title=title,
            status=status, priority=priority, related="", goal="",
            wiki=wiki, json=json.dumps(payload), allow_stubs=True,
            force=False)) != 0:
        return
    session.kind, session.area = kind, area
    hits = resolve_cards(session.entries(), f"{kind}-{num}")
    session.current = hits[0] if hits else None
    print("  next: `w` to write a section, or `m` to move it.")


def _cmd_list(session: Session) -> None:
    status = _menu_optional_choice("status", STATUSES)
    area = _menu_input("area (blank = any)") or None
    kind = _menu_optional_choice("kind", KINDS)
    rows = [e for e in session.entries() if e.kind]
    if status:
        rows = [e for e in rows if e.status == status]
    if area:
        rows = [e for e in rows if e.area == area]
    if kind:
        rows = [e for e in rows if e.kind == kind]
    rows.sort(key=lambda e: (e.kind, e.num))
    print(f"  {len(rows)} card(s)")
    shown = rows[:MENU_ROW_LIMIT]
    for i, entry in enumerate(shown, 1):
        print(f"  {i:>3}) {entry.id:<10} {entry.status:<10} "
              f"{entry.area:<12} {entry.title()}")
    if len(rows) > len(shown):
        print(f"  ... {len(rows) - len(shown)} more; add a filter to see them")
    if not shown:
        return
    pick = _menu_int("open which", 1, len(shown))
    if pick:
        session.current = shown[pick - 1]
        _show_card(session.current, session)


def _cmd_review(session: Session) -> None:
    rows = [e for e in session.entries() if e.kind and e.status == "review"]
    rows.sort(key=card_age_days, reverse=True)
    if not rows:
        print("  the verification queue is empty")
        return
    print(f"  {len(rows)} card(s) in review, oldest first")
    shown = rows[:15]
    for i, entry in enumerate(shown, 1):
        print(f"  {i:>2}) {entry.id:<10} {card_age_days(entry):>4}d "
              f"{entry.area:<12} {entry.title()}")
    pick = _menu_int("open which", 1, len(shown))
    if pick:
        session.current = shown[pick - 1]
        _show_card(session.current, session)


def _cmd_next(session: Session) -> None:
    print()
    cmd_next(argparse.Namespace(root=session.root, limit=None, json=False))
    print("  put one in hand with `u <id>`")


def _cmd_status(session: Session) -> None:
    print()
    cmd_status(argparse.Namespace(root=session.root, json=False))


def _cmd_roadmap(session: Session) -> None:
    print()
    cmd_roadmap(argparse.Namespace(root=session.root, out=None))


def _cmd_graph(session: Session) -> None:
    print()
    cmd_graph(argparse.Namespace(root=session.root, json=False))


def _set_namespace(root: Path, kind: str, num: int, **over) -> argparse.Namespace:
    """A ``cmd_set`` namespace with every flag the parser can supply."""
    base: Dict = {"root": root, "kind": kind, "id": num, "area": None,
                  "priority": None, "horizon": None, "effort": None,
                  "goal": None, "wiki": None, "section": None, "value": None,
                  "value_file": None}
    for key in DEPENDENCY_KEYS:
        base[key] = None
    base.update(over)
    return argparse.Namespace(**base)


def _journaled_set(session: Session, card: Entry,
                   namespace: argparse.Namespace) -> None:
    """Run ``cmd_set`` and keep the undo entry only when it actually wrote."""
    session.record_write(card.path)
    if cmd_set(namespace) != 0:
        session.journal.pop()


def _cmd_set(session: Session, query: str = "") -> None:
    card = _target(session, query)
    if not card:
        return
    fields = ("area", "priority", "horizon", "effort", "goal", "wiki")
    print("  frontmatter: " + " ".join(fields))
    print("  deps: " + " ".join(DEPENDENCY_KEYS))
    print("  section: " + " ".join(key for key, _title, _alias in CANONICAL_SECTIONS))
    key = _menu_input("field or section").lower()
    if not key:
        return
    if key in fields:
        value = _menu_input(key)
        if not value:
            print("  nothing changed")
            return
        _journaled_set(session, card, _set_namespace(
            session.root, card.kind, card.num, **{key: value}))
        return
    if key in DEPENDENCY_KEYS:
        value = _menu_input(f"{key} (comma separated ids, blank = clear)")
        _journaled_set(session, card, _set_namespace(
            session.root, card.kind, card.num, **{key: value}))
        return
    if key not in SECTION_TITLE_BY_KEY:
        print(f"  {key!r} is not a field, dependency or canonical section")
        return
    current = body_sections(read_text(card.path)).get(key, "")
    print(f"\n  current {SECTION_TITLE_BY_KEY[key]}:\n")
    _paged(format_card_body(current) if current else ["  (empty)"])
    print()
    body = _menu_multiline(f"new body for {SECTION_TITLE_BY_KEY[key]}")
    if not body:
        print("  nothing changed")
        return
    _journaled_set(session, card, _set_namespace(
        session.root, card.kind, card.num, section=key, value=body))


def _cmd_deps(session: Session) -> None:
    print()
    cmd_link_deps(argparse.Namespace(root=session.root, status=None,
                                     write=False, json=False))
    if _menu_input("write these", "n").lower() in ("y", "yes"):
        cmd_link_deps(argparse.Namespace(root=session.root, status=None,
                                         write=True, json=False))
        print("  dependency links are derived from frontmatter, so `d` rebuilds "
              "rather than undoes them")


def _cmd_validate(session: Session) -> None:
    print()
    code = cmd_validate(argparse.Namespace(root=session.root, quiet=False,
                                           schema=False))
    session.last_validate = (_dt.datetime.now().strftime("%H:%M"), code)
    gaps = _schema_warnings(session.entries())
    if not gaps:
        print("no canonical-schema gaps")
        return
    print(f"\n{len(gaps)} canonical-schema gap(s)")
    if _menu_input("list them", "n").lower() in ("y", "yes"):
        for gap in gaps:
            print("  " + gap)


def _cmd_gates(session: Session) -> None:
    print("\n== validate ==")
    code = cmd_validate(argparse.Namespace(root=session.root, quiet=False,
                                           schema=False))
    print("\n== dependency links (dry run) ==")
    cmd_link_deps(argparse.Namespace(root=session.root, status=None,
                                     write=False, json=False))
    print("\n== wikilinks ==")
    links = cmd_links(argparse.Namespace(root=session.root, report=False))
    session.last_validate = (_dt.datetime.now().strftime("%H:%M"), code)
    print("\n" + ("gates clean" if code == 0 and links == 0
                  else "gates report problems above"))


def _cmd_index(session: Session) -> None:
    action = _menu_choice("cache action", ("rebuild", "clear"), "rebuild")
    cmd_index(argparse.Namespace(root=session.root,
                                 clear=action == "clear"))


def _cmd_next_id(session: Session) -> None:
    kind = _menu_choice("kind", KINDS, session.kind)
    session.kind = kind
    cmd_next_id(argparse.Namespace(root=session.root, kind=kind))


def _cmd_help(session: Session) -> None:
    topic = _menu_input("command (blank = full guide)")
    if topic and topic not in HELP_TOPICS:
        print(f"  no help for {topic!r}; topics: {', '.join(sorted(HELP_TOPICS))}")
        return
    cmd_help(argparse.Namespace(topic=topic or None))


def _undo_last(session: Session) -> None:
    if not session.journal:
        print("  nothing to undo in this session")
        return
    item = session.journal[-1]
    label = (item["path"].name if item["op"] == "write"
             else f"move {item['dst'].name} to {item['dst'].parent.parent.name}")
    if _menu_input(f"undo {label}", "y").lower() not in ("y", "yes"):
        return
    session.journal.pop()
    if item["op"] == "write":
        _write_card(item["path"], item["before"])
        print(f"  restored {item['path'].name}")
    else:
        src, dst = item["src"], item["dst"]
        if not dst.exists():
            print("  the moved file is gone; nothing restored")
            return
        src.parent.mkdir(parents=True, exist_ok=True)
        if not git_mv(dst, src, session.root):
            shutil.move(str(dst), str(src))
        _rewrite_status(src, src.relative_to(session.root).parts[0])
        print(f"  moved {dst.name} back to {src.parent.parent.name}")
    session.refresh_current()


INTERACTIVE_MENU = """\
the card in hand (set it with `u`) is the default target

  s show CARD     body with numbered boxes, plus this card's schema gaps
  u use CARD      put a card in hand
  c check         tick a box and record what you actually observed
  o note          append a dated line to the card's Log

  n next          startable cards, ranked by what they unblock
  r review        verification queue, oldest first
  l list          filter, numbered, open one by number
  t status        counts by status / area / horizon
  p roadmap       now / next / later, critical path
  g graph         dependency edges and cycles

  a add           scaffold a task or bug (preview, then confirm)
  m move          change the status folder, refusing an unverified done
  w set           one frontmatter field, dep, or a whole section
  d deps          render dependency links (dry run first)

  v validate      tree check, then the per-card gaps
  f gates         validate + deps + wikilinks in one pass
  i index         rebuild or clear the frontmatter cache
  e help [cmd]    the full guide, or one command's flags

  z undo last write/move    ? or blank menu    x cancel    q quit
"""

_ALIASES = {
    "1": "next-id", "2": "add", "3": "move", "4": "list",
    "5": "validate", "6": "index", "7": "help",
    "s": "show", "u": "use", "c": "check", "o": "note",
    "n": "next", "r": "review", "l": "list", "t": "status",
    "p": "roadmap", "g": "graph", "a": "add", "m": "move",
    "w": "set", "d": "deps", "v": "validate", "f": "gates",
    "i": "index", "e": "help", "z": "undo",
    "show": "show", "cat": "show", "open": "show", "use": "use",
    "check": "check", "note": "note", "log": "note",
    "next": "next", "review": "review", "list": "list",
    "status": "status", "roadmap": "roadmap", "graph": "graph",
    "new": "add", "add": "add", "move": "move", "set": "set",
    "write": "set", "deps": "deps", "link-deps": "deps",
    "validate": "validate", "gates": "gates", "index": "index",
    "help": "help", "undo": "undo",
}


def _dispatch(session: Session, choice: str) -> None:
    parts = choice.split(None, 1)
    action = _ALIASES.get(parts[0], parts[0])
    rest = parts[1].strip() if len(parts) > 1 else ""
    if action == "show":
        _cmd_show(session, rest)
    elif action == "use":
        _cmd_use(session, rest)
    elif action == "check":
        _cmd_check(session, rest)
    elif action == "note":
        _cmd_note(session, rest)
    elif action == "next":
        _cmd_next(session)
    elif action == "review":
        _cmd_review(session)
    elif action == "list":
        _cmd_list(session)
    elif action == "status":
        _cmd_status(session)
    elif action == "roadmap":
        _cmd_roadmap(session)
    elif action == "graph":
        _cmd_graph(session)
    elif action == "add":
        _cmd_add(session)
    elif action == "move":
        _cmd_move(session, rest)
    elif action == "set":
        _cmd_set(session, rest)
    elif action == "deps":
        _cmd_deps(session)
    elif action == "validate":
        _cmd_validate(session)
    elif action == "gates":
        _cmd_gates(session)
    elif action == "index":
        _cmd_index(session)
    elif action == "next-id":
        _cmd_next_id(session)
    elif action == "help":
        _cmd_help(session)
    elif action == "undo":
        _undo_last(session)
    else:
        print(f"  unknown choice {choice!r}; blank or `?` shows the menu")


def cmd_interactive(args) -> int:
    if not Path(args.root).is_dir():
        print(f"error: dev_tasks root not found: {args.root}", file=sys.stderr)
        return 1
    session = Session(args.root)
    print(f"dev_tasks root: {args.root}")
    _print_header(session)
    print("  `?` menu, `x` cancels an action, `q` quits")
    while True:
        try:
            choice = _menu_input(_prompt(session)).strip().lower()
        except _Cancel:
            continue
        except _Quit:
            _print_session_end(session)
            return 0
        if choice in ("q", "quit", "exit"):
            _print_session_end(session)
            return 0
        if choice in ("", "?", "menu"):
            print()
            _print_header(session)
            print(INTERACTIVE_MENU, end="")
            continue
        try:
            _dispatch(session, choice)
        except _Cancel:
            print("  cancelled")
        except _Quit:
            _print_session_end(session)
            return 0
    return 0


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
    nw.add_argument("--allow-stubs", "--scaffold", dest="allow_stubs", action="store_true",
                    help="permit placeholder/TODO stubs (default: rejected)")
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
                   help="also list per-card canonical-schema gaps (including browser UI intent)")
    v.set_defaults(func=cmd_validate)

    ix = sub.add_parser("index", help="rebuild or clear the derived frontmatter cache")
    ix.add_argument("--clear", action="store_true", help="delete the cache instead")
    ix.set_defaults(func=cmd_index)

    lk = sub.add_parser("links", help="check the vault's [[wikilinks]]")
    lk.add_argument("--report", action="store_true", help="list the broken links")
    lk.set_defaults(func=cmd_links)

    ld = sub.add_parser("link-deps",
                        help="render dependency frontmatter as [[wikilinks]]")
    ld.add_argument("--status", nargs="+", choices=STATUSES,
                    help="only cards in these status folders")
    ld.add_argument("--write", action="store_true",
                    help="apply the block (default is a dry run)")
    ld.add_argument("--json", action="store_true")
    ld.set_defaults(func=cmd_link_deps)

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
