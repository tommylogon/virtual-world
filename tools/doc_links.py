#!/usr/bin/env python3
"""Check — and repair — Obsidian ``[[wikilinks]]`` in the notes vault.

A link target resolves the way Obsidian resolves it: either as a vault-relative
path *without* the ``.md`` extension, or as a bare basename anywhere in the
vault. So ``[[Items & Inventory/Items Overview]]`` and ``[[Items Overview]]``
both point at the same note. The forms Obsidian also accepts are handled:

* ``[[Target|alias]]`` — an alias, including ``[[Target\\|alias]]``. The
  backslash is how a pipe is escaped inside a markdown table, and it is the
  single most common false "broken link" in this vault.
* ``[[Target#Heading]]`` and ``[[Target^block]]`` — a sub-target; only ``Target``
  identifies the note.
* a trailing ``.md``.

A link is **broken** when nothing in the vault answers to its target.

The dev-task tree is the reason this exists. ``tools/tasks.py move`` relocates a
task between status folders with ``git mv`` and does not touch the notes that
cite it, so every move silently rots inbound links. The fix has two halves:

* link tasks by **basename** (``[[task-54-weapon-system]]``), which Obsidian
  resolves from any folder, so a status move cannot break it; and
* keep this checker in front of it. ``tools/tasks.py links`` runs ``--check``,
  and ``tools/tasks.py move`` rewrites inbound links it just invalidated.

Usage:
    python tools/doc_links.py --check     # exit 1 when any link is broken
    python tools/doc_links.py --count     # how many broken, distinct and total
    python tools/doc_links.py --report    # the broken links, grouped by target
    python tools/doc_links.py --fix       # rewrite what can be resolved
    python tools/doc_links.py --orphans [--min-inbound N] [--all-notes]
                                           # the other direction: curated notes
                                           # nothing links to. Not a gate — an
                                           # orphan is often a destination.

The vault root is ``docs/virtualWorld``; ``.obsidian/`` is never scanned.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

VAULT = Path("docs/virtualWorld")
DEV_TASKS = VAULT / "dev_tasks"

# [[ ... ]]; the target may contain an escaped pipe, a heading or a block ref.
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
TASK_RE = re.compile(r"\b(task|bug)[-_](\d+)\b", re.IGNORECASE)
FILE_RE = re.compile(r"^(task|bug)[-_](\d+)[-_](.*)\.md$", re.IGNORECASE)


def iter_notes(vault: Path = VAULT) -> List[Path]:
    """Every markdown note in the vault, minus Obsidian's own state folder."""
    if not vault.exists():
        return []
    return sorted(p for p in vault.rglob("*.md") if ".obsidian" not in p.parts)


def build_index(notes: List[Path], vault: Path = VAULT) -> Dict[str, Path]:
    """Map every resolvable key to its note.

    Both the vault-relative path (``Items & Inventory/Items Overview``) and the
    bare basename (``Items Overview``) are keys. A basename that occurs more
    than once is removed: Obsidian would be ambiguous, so it must not resolve.
    """
    by_key: Dict[str, Path] = {}
    basename_counts: Counter = Counter()
    basenames: Dict[str, Path] = {}
    for p in notes:
        rel = p.relative_to(vault).as_posix()
        stem = rel[:-3] if rel.endswith(".md") else rel
        by_key[stem] = p
        base = p.stem
        basename_counts[base] += 1
        basenames[base] = p
    for base, n in basename_counts.items():
        if n == 1:
            by_key.setdefault(base, basenames[base])
    return by_key


def _split_alias(raw: str) -> Tuple[str, str]:
    """Return (target, display). An escaped ``\\|`` is a separator too."""
    raw = raw.replace("\\|", "|")
    if "|" in raw:
        target, _, display = raw.partition("|")
        return target.strip(), display
    return raw.strip(), ""


def target_key(raw: str) -> str:
    """Normalise a link body to its lookup key (no alias, heading or .md)."""
    target, _ = _split_alias(raw)
    target = target.split("#", 1)[0].split("^", 1)[0].strip()
    target = target.replace("\\", "/")
    for prefix in ("docs/virtualWorld/", "docs/virtualWorld", "./"):
        if target.startswith(prefix):
            target = target[len(prefix):]
            break
    if target.endswith(".md"):
        target = target[:-3]
    return target.strip("/")


def resolve(raw: str, index: Dict[str, Path], vault: Path = VAULT) -> Optional[Path]:
    key = target_key(raw)
    if not key:
        return None
    if key in index:
        return index[key]
    # A path whose folder is stale but whose basename is unique still resolves
    # in Obsidian; mirror that, then fall back to the note title.
    base = key.rsplit("/", 1)[-1]
    if base in index:
        return index[base]
    return None


INLINE_CODE_RE = re.compile(r"`[^`]*`")


def iter_links(vault: Path = VAULT) -> Iterator[Tuple[Path, int, str]]:
    """Yield (file, 1-based line, raw link body) for every real wikilink.

    Links inside fenced blocks or inline code are not links — Obsidian renders
    them literally. Mask inline code without changing its length so the match
    offsets still index the original line.
    """
    for p in iter_notes(vault):
        text = p.read_text(encoding="utf-8", errors="replace")
        in_fence = False
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            masked = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)
            for m in WIKILINK_RE.finditer(masked):
                yield p, i, line[m.start() + 2:m.end() - 2]


def broken_links(vault: Path = VAULT) -> List[Tuple[Path, int, str]]:
    index = build_index(iter_notes(vault), vault)
    return [(p, ln, raw) for p, ln, raw in iter_links(vault)
            if resolve(raw, index, vault) is None]


# ── repair ────────────────────────────────────────────────────────────────


def _norm_slug(s: str) -> str:
    """Normalise a task slug for comparison: case, separators, a stray `` 1``."""
    s = s.strip().lstrip("-").strip()
    s = re.sub(r"\s+\d+$", "", s)          # Obsidian's duplicate-name suffix
    s = s.replace("_", "-").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def task_by_id(vault: Path = VAULT) -> Dict[str, List[Tuple[Path, str]]]:
    """Map ``task-54`` / ``bug-6`` to [(current file, normalised slug)].

    Old bug files are ``bug_6-slug`` with an underscore and no zero-padding, so
    the id pattern must accept ``[-_]``. The list matters: two different tasks
    once shared an id (task-150, task-181 in the initial release, one later
    deleted), so an id alone is not enough to retarget safely.
    """
    out: Dict[str, List[Tuple[Path, str]]] = defaultdict(list)
    if not DEV_TASKS.exists():
        return out
    for p in DEV_TASKS.rglob("*.md"):
        m = FILE_RE.match(p.name)
        if m:
            tid = "%s-%d" % (m.group(1).lower(), int(m.group(2)))
            out[tid].append((p, _norm_slug(m.group(3))))
    return out


def _replacement(raw: str, index: Dict[str, Path],
                 tasks: Dict[str, List[Tuple[Path, str]]]) -> Optional[str]:
    """A new link body that resolves, or None.

    The repaired form is the bare basename for a task (Obsidian resolves it from
    any folder, so a later status move cannot break it) and the current
    vault-relative path otherwise.
    """
    target, display = _split_alias(raw)
    key = target_key(raw)
    # 1. We can already resolve it (via a full path or a unique basename).
    if key in index:
        new = key
    elif key.rsplit("/", 1)[-1] in index:
        new = key.rsplit("/", 1)[-1]
    else:
        # 2. A task cited by a stale path. Retarget only when id *and* slug
        #    agree with exactly one current file — a move preserves the slug,
        #    so a matching slug is proof of identity. A reused id (the task was
        #    deleted, another took the number) must not be retargeted.
        m = TASK_RE.search(key)
        if m:
            tid = "%s-%d" % (m.group(1).lower(), int(m.group(2)))
            ref_slug = _norm_slug(key[m.end():])
            matches = [p for p, slug in tasks.get(tid, []) if slug == ref_slug]
            if len(matches) != 1:
                return None
            new = matches[0].stem
        else:
            # 3. A prose note whose folder is wrong but whose basename is
            #    unique somewhere in the vault.
            base = key.rsplit("/", 1)[-1]
            candidates = [k for k in index if k.rsplit("/", 1)[-1] == base]
            if len(candidates) != 1:
                return None
            new = candidates[0]
    if new == target.strip():
        return None
    return new + (("|" + display) if display else "")


def _map_links(text: str, fn) -> Tuple[str, int]:
    """Apply ``fn(raw) -> new_body | None`` to every real link in one note.

    Fenced blocks and inline code are left untouched; ``None`` leaves a link
    as-is. Returns ``(new_text, rewritten_count)``.
    """
    out: List[str] = []
    in_fence = False
    changed = 0
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        masked = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)
        spans = [(m.start(), m.end(), line[m.start() + 2:m.end() - 2])
                 for m in WIKILINK_RE.finditer(masked)]
        newline = line
        for start, end, raw in reversed(spans):
            rep = fn(raw)
            if rep is None:
                continue
            newline = newline[:start] + "[[" + rep + "]]" + newline[end:]
            changed += 1
        out.append(newline)
    return "".join(out), changed


def retarget_links(vault: Path, old_key: str, new_key: str) -> Tuple[int, int]:
    """Point every link at ``old_key`` (path or basename) to ``new_key``.

    Used by ``tools/tasks.py move``: a task cited by a stale status-folder
    path is rewritten to its new basename, which Obsidian resolves from any
    folder. Returns ``(files_changed, links_changed)``.
    """
    old_key = target_key(old_key)
    old_base = old_key.rsplit("/", 1)[-1]
    new_key = target_key(new_key)
    files = links = 0
    for p in iter_notes(vault):
        text = p.read_text(encoding="utf-8", errors="replace")

        def fn(raw: str) -> Optional[str]:
            k = target_key(raw)
            if k == new_key or not (k == old_key or k.rsplit("/", 1)[-1] == old_base):
                return None
            _, display = _split_alias(raw)
            return new_key + (("|" + display) if display else "")

        new_text, n = _map_links(text, fn)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            files += 1
            links += n
    return files, links


def _fix_text(text: str, index: Dict[str, Path], tasks: Dict[str, Path]):
    """Rewrite resolvable broken links in one note. Returns (text, n, leftovers)."""
    unresolved: List[str] = []

    def fn(raw: str) -> Optional[str]:
        if resolve(raw, index) is not None:
            return None
        rep = _replacement(raw, index, tasks)
        if rep is None:
            unresolved.append(raw)
        return rep

    new_text, changed = _map_links(text, fn)
    return new_text, changed, unresolved


def fix(vault: Path = VAULT) -> Tuple[int, int, List[str]]:
    """Rewrite every link that can be resolved. Returns (files, links, leftovers)."""
    index = build_index(iter_notes(vault), vault)
    tasks = task_by_id(vault)
    changed_files = 0
    changed_links = 0
    leftovers: List[str] = []
    for p in iter_notes(vault):
        text = p.read_text(encoding="utf-8", errors="replace")
        new_text, n, unresolved = _fix_text(text, index, tasks)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            changed_files += 1
        changed_links += n
        for u in unresolved:
            leftovers.append("%s: %s" % (p.relative_to(vault).as_posix(), u))
    return changed_files, changed_links, leftovers


def inbound_counts(vault: Path = VAULT) -> Dict[Path, int]:
    """How many *other* notes link to each note.

    Resolution is this module's, not a fresh approximation: aliases, escaped
    pipes, heading and block refs, and the ambiguous-basename rule all already
    have one implementation here and a second one would drift.
    """
    index = build_index(iter_notes(vault), vault)
    counts: Dict[Path, int] = {}
    for src, _ln, raw in iter_links(vault):
        target = resolve(raw, index, vault)
        if target is None or target == src:
            continue
        counts[target] = counts.get(target, 0) + 1
    return counts


def orphans(vault: Path = VAULT, min_inbound: int = 1,
            curated_only: bool = True) -> List[Tuple[Path, int]]:
    """Notes nothing links to, ordered worst-first (fewest inbound, then name).

    An orphan is not a defect — ``History.md`` and the release notes are
    destinations, and a link nobody clicks is still how a reader arrives. This
    is a reading list, not a gate: it is why the vault had 688 notes with zero
    links and nobody could see which of them were supposed to be found.
    """
    counts = inbound_counts(vault)
    universe = iter_notes(vault)
    if curated_only:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from doc_tags import curated_docs  # local import: doc_links stays standalone

        curated = set(curated_docs())
        universe = [p for p in universe if p in curated]
    out = [(p, counts.get(p, 0)) for p in universe if counts.get(p, 0) < min_inbound]
    out.sort(key=lambda pair: (pair[1], pair[0].as_posix()))
    return out


# ── cli ───────────────────────────────────────────────────────────────────


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if any link is broken")
    parser.add_argument("--count", action="store_true", help="print broken-link counts")
    parser.add_argument("--report", action="store_true", help="list the broken links")
    parser.add_argument("--fix", action="store_true", help="rewrite resolvable broken links")
    parser.add_argument("--orphans", action="store_true",
                        help="list curated notes fewer than --min-inbound notes link to")
    parser.add_argument("--min-inbound", type=int, default=1,
                        help="inbound-link threshold for --orphans (default 1)")
    parser.add_argument("--all-notes", action="store_true",
                        help="with --orphans, include the task tree, not just curated notes")
    parser.add_argument("--vault", type=Path, default=VAULT)
    args = parser.parse_args(argv)

    if args.fix:
        files, links, leftovers = fix(args.vault)
        print(f"rewrote {links} link(s) in {files} file(s)")
        for lo in leftovers:
            print("  unresolved:", lo)
        return 0

    if args.orphans:
        found = orphans(args.vault, args.min_inbound, curated_only=not args.all_notes)
        if args.all_notes:
            scope, total = "note", len(iter_notes(args.vault))
        else:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from doc_tags import curated_docs

            scope, total = "curated note", len(curated_docs())
        plural = "" if total == 1 else "s"
        print(f"{len(found)} of {total} {scope}{plural} in the vault have "
              f"<{args.min_inbound} inbound link(s)")
        for path, n in found:
            print(f"  {n:>3}  {path.relative_to(args.vault).as_posix()}")
        return 0

    broken = broken_links(args.vault)
    distinct = Counter(target_key(raw) for _, _, raw in broken)
    if args.report or args.count:
        by_target: Dict[str, List[str]] = defaultdict(list)
        for p, ln, raw in broken:
            by_target[target_key(raw)].append(
                f"{p.relative_to(args.vault).as_posix()}:{ln}")
        for key in sorted(by_target):
            print(f"{len(by_target[key]):>3}  [[{key}]]")
            for where in by_target[key]:
                print(f"       {where}")
    if args.count:
        print(f"\nbroken occurrences: {len(broken)}")
        print(f"broken distinct:    {len(distinct)}")
    if not (args.report or args.count):
        print(f"broken wikilinks: {len(broken)} "
              f"({len(distinct)} distinct)")
    if args.check:
        if broken:
            print("Broken wikilinks found — run --report to list them.")
            return 1
        print("Wikilink check OK (0 broken).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
