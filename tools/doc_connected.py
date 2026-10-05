"""doc_connected.py — a `## Connected` section on every curated note, from relations that already exist.

The vault's graph was mostly islands: notes that describe a system's *inside*
while nothing records what the note touches. This tool writes the missing half
of the map — not by inventing relations, but by joining four that the repo
already asserts and nothing surfaces:

    Features    rows of the Feature Map whose ``Docs`` cell points at this note
    Dev tasks   task files whose ``wiki:`` frontmatter already links this note
    Code        modules whose ``@docs`` header already points at this note
    Systems     the other notes in the same folder (the nearest neighbours)

Every section is delimited by ``<!-- connected:start/end -->`` so ``--apply`` is
idempotent: it replaces the block and never touches a human's prose.

    python tools/doc_connected.py --apply    # write/refresh the block
    python tools/doc_connected.py --report   # which notes have which relations
    python tools/doc_connected.py --check    # fail on a curated note with no block
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from feature_index import parse_features  # noqa: E402
from feature_pages import docs_links, slug  # noqa: E402
from doc_tags import curated_docs  # noqa: E402

VAULT = ROOT / "docs" / "virtualWorld"
DEV_TASKS = VAULT / "dev_tasks"
FEATURES = VAULT / "Features"
CODE_ROOTS = ("static/js", "engine", "routes")

START = "<!-- connected:start -->"
END = "<!-- connected:end -->"
CAP = 6

# Verified heading-level links. The vault had four heading refs in 885 notes, which
# is why "everything about memory" and "the loop that calls it" both resolved to a
# whole page the reader then had to scroll. Each entry is
# ``(referring note, target note, heading)`` and points at a section that exists —
# ``--check`` fails when one of these headings disappears, so the table cannot rot
# into links that land at the top of a page. Every pair below is a relation the
# repo already asserts in prose or in a ``@docs`` header; nothing here is invented.
SECTION_REFS: tuple[tuple[str, str, str], ...] = (
    ("Memory Dynamics", "Memory System", "Memory dynamics (task-685)"),
    ("Memory Dynamics", "Agent Engine", "Memory in the agent"),
    ("Memory System", "Memory Dynamics", "5. Query-driven retrieval"),
    ("Agent Engine", "Memory System", "Memory dynamics (task-685)"),
    ("Agent Engine", "Narration System", "Integration with Agent Engine"),
    ("Narration System", "Agent Engine", "Prompt Building"),
    ("Memory Dynamics", "Agent Engine", "Structured Actions (task-160)"),
    ("Search & Forage", "Background Simulation", "The entry point"),
    ("Background Simulation", "Search & Forage", "The verbs are three different things"),
    ("Per-Agent Knowledge (Fog of War)", "Background Simulation", "Wiring"),
    ("WorldPainter", "Grid to Graph", "The pipeline"),
    ("Grid to Graph", "WorldPainter", "Known constraints"),
    ("Memory Dynamics", "Emotion & Affect System", "How memory emotions reach the character"),
    ("Emotion & Affect System", "Memory System", "Memory emotion recall (residue)"),
)

_LINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\\?\|([^\]]*))?\]\]")
_WIKI_RE = re.compile(r"^wiki:\s*(.+)$", re.M)
_DOCS_RE = re.compile(r"^@docs\s+(.+)$", re.M)


def _stem(target: str) -> str:
    return Path(str(target).strip()).name


def features_by_doc() -> dict[str, list[tuple[int, str]]]:
    """doc stem -> [(row number, feature label)] for every Feature Map row."""
    out: dict[str, list[tuple[int, str]]] = {}
    for feature in parse_features():
        for target in docs_links(feature["docs"]):
            out.setdefault(_stem(target), []).append((feature["n"], feature["label"]))
    return out


def tasks_by_doc() -> dict[str, list[str]]:
    """doc stem -> [task wikilinks] from the ``wiki:`` key task frontmatter already carries."""
    out: dict[str, list[str]] = {}
    if not DEV_TASKS.exists():
        return out
    for task in sorted(DEV_TASKS.rglob("*.md")):
        text = task.read_text(encoding="utf-8", errors="replace")
        match = _WIKI_RE.search(text)
        if not match:
            continue
        rel = task.relative_to(VAULT).as_posix()[:-3]  # drop .md
        for target, _alias in _LINK_RE.findall(match.group(1)):
            out.setdefault(_stem(target), []).append(f"[[{rel}|{task.stem.split('-')[0]}]]")
    return out


def code_by_doc() -> dict[str, list[str]]:
    """doc stem -> [module paths] from ``@docs`` headers in JS and Python."""
    out: dict[str, list[str]] = {}
    for base in CODE_ROOTS:
        for path in sorted((ROOT / base).rglob("*")):
            if path.suffix not in (".js", ".py") or "node_modules" in path.parts:
                continue
            head = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:80])
            match = _DOCS_RE.search(head)
            if not match:
                continue
            first = match.group(1).strip().split()[0]
            if first.lower() in ("none", "n/a", "-"):
                continue
            rel = path.relative_to(ROOT).as_posix()
            out.setdefault(_stem(first), []).append(f"`{rel}`")
    return out


def siblings_for(path: Path) -> list[str]:
    """Other curated notes in the same folder (and Features/ pages share a bucket)."""
    if path.parent == FEATURES:
        pool = sorted(p.stem for p in FEATURES.glob("*.md") if p != path)
    else:
        pool = sorted(p.stem for p in path.parent.glob("*.md")
                      if p != path and p.is_file() and not p.name.startswith("_"))
    return [f"[[{s}]]" for s in pool[:CAP]]


def heading_exists(stem: str, heading: str) -> bool:
    """True when ``<stem>.md`` really has an ``## <heading>`` — a section link must land on it."""
    for path in VAULT.rglob(f"{stem}.md"):
        if f"## {heading}" in path.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def section_refs_for(stem: str) -> list[str]:
    return [f"[[{target}#{heading}]]" for src, target, heading in SECTION_REFS if src == stem]


RELATION_HEADINGS = ("**Read next**", "**Features**", "**Dev tasks**",
                     "**Code**", "**Neighbouring notes**")


def render(path: Path, features, tasks, code) -> str:
    """The block for one note, or ``""`` when it has no relation to anything.

    An empty `## Connected` is worse than none: it says "connected" and means
    "we did not check". Two generated notes (a template list and a manual test
    plan) genuinely have no inbound relation, so they get no block at all.
    """
    stem = path.stem
    refs = section_refs_for(stem)
    rows = features.get(stem) or []
    task_links = tasks.get(stem) or []
    mods = code.get(stem) or []
    sibs = siblings_for(path)
    if not (refs or rows or task_links or mods or sibs):
        return ""

    lines = [START, "## Connected", "",
             "*Generated by `python tools/doc_connected.py --apply` — relations the repo already "
             "asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, "
             "same-folder notes), not invented.*", ""]

    if refs:
        lines += [f"**Read next** — {', '.join(refs)}", ""]
    if rows:
        links = ", ".join(f"[[{slug(label)}|{label}]] (#{n})" for n, label in rows[:CAP])
        more = f" … +{len(rows) - CAP} more" if len(rows) > CAP else ""
        lines += [f"**Features** — {links}{more}", ""]
    if task_links:
        more = f" … +{len(task_links) - CAP} more" if len(task_links) > CAP else ""
        lines += [f"**Dev tasks** — {', '.join(task_links[:CAP])}{more}", ""]
    if mods:
        more = f" … +{len(mods) - CAP} more" if len(mods) > CAP else ""
        lines += [f"**Code** (`@docs`) — {', '.join(mods[:CAP])}{more}", ""]
    if sibs:
        lines += [f"**Neighbouring notes** — {', '.join(sibs)}", ""]
    lines += [END]
    return "\n".join(lines)


def apply_sections() -> tuple[int, int]:
    """Write (or refresh, or remove) the block on every curated note."""
    features, tasks, code = features_by_doc(), tasks_by_doc(), code_by_doc()
    changed = 0
    with_block = 0
    for path in curated_docs():
        if path.parent == FEATURES:
            continue
        text = path.read_text(encoding="utf-8")
        block = render(path, features, tasks, code)
        if START in text:
            pattern = re.escape(START) + r".*?" + re.escape(END) + r"\n+"
            new_text = re.sub(pattern, block + "\n" if block else "", text, flags=re.S)
        elif block:
            new_text = text.rstrip() + "\n\n" + block + "\n"
        else:
            new_text = text
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
        if block:
            with_block += 1
    return changed, with_block


def check() -> int:
    problems = []
    features, tasks, code = features_by_doc(), tasks_by_doc(), code_by_doc()
    for path in curated_docs():
        if path.parent == FEATURES:
            continue
        has_block = START in path.read_text(encoding="utf-8")
        expected = render(path, features, tasks, code)
        if expected and not has_block:
            problems.append(f"{path.relative_to(VAULT)}: no Connected section (run --apply)")
        elif not expected and has_block:
            problems.append(f"{path.relative_to(VAULT)}: stale empty Connected section "
                            f"(this note has no relation — run --apply)")
    # A section link that lands at the top of a page is a lie about the page, so a
    # renamed heading is a guard failure, not something to notice in the reader.
    for src, target, heading in SECTION_REFS:
        if not heading_exists(target, heading):
            problems.append(f"SECTION_REFS: {src} -> [[{target}#{heading}]] — no such heading")
    if problems:
        sys.stderr.write(f"{len(problems)} curated note(s) without a Connected section:\n")
        for line in problems[:20]:
            sys.stderr.write(f"  - {line}\n")
        if len(problems) > 20:
            sys.stderr.write(f"  … and {len(problems) - 20} more\n")
        return 1
    return 0


def report() -> None:
    features, tasks, code = features_by_doc(), tasks_by_doc(), code_by_doc()
    total = len(curated_docs())
    print(f"{total} curated notes")
    print(f"  notes with ≥1 Feature Map row pointing at them: {len(features)}")
    print(f"  notes referenced by a task's wiki: frontmatter      : {len(tasks)}")
    print(f"  notes pointed at by a module's @docs header         : {len(code)}")
    empty = [p.relative_to(VAULT) for p in curated_docs()
             if p.parent != FEATURES and p.stem not in features
             and p.stem not in tasks and p.stem not in code]
    print(f"  notes with no inbound relation from any of the three: {len(empty)}")
    for rel in empty[:10]:
        print(f"      {rel}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write/refresh the Connected block")
    parser.add_argument("--report", action="store_true", help="relation coverage per note")
    parser.add_argument("--check", action="store_true", help="fail on a curated note with no block")
    args = parser.parse_args()

    if args.apply:
        changed, with_block = apply_sections()
        print(f"Connected sections: {changed} note(s) updated, {with_block} carry a real relation")
        return 0
    if args.report:
        report()
        return 0
    if args.check:
        return check()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())