"""doc_tags.py — one controlled tag vocabulary for the vault's curated docs.

Obsidian's tag pane is only worth having when the tag set is closed. This vault
had 36 ``tags:`` lines carrying 75 distinct tokens, 70 of which appeared exactly
once — not a vocabulary, just noise that makes the tag pane useless. This tool
owns the list, applies it, and fails when a curated doc carries a tag the list
does not have.

Namespaces (the ``/`` is the point — Obsidian nests on it):

    system/<domain>   which part of the engine the note documents
    surface/<where>   in-game | in-editor | lens | api | data | docs
    status/<word>     mirrors the Feature Map's own vocabulary
    topic/<word>      cross-cutting concerns that cut across systems

Curated docs only (everything outside ``dev_tasks/``). Task files keep the
frontmatter the task tooling parses; their ad-hoc tags are a separate cleanup.

    python tools/doc_tags.py --apply    # write/refresh tags on curated docs
    python tools/doc_tags.py --report   # per-tag usage, untagged notes
    python tools/doc_tags.py --check    # fail on a tag outside the vocabulary
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "docs" / "virtualWorld"
FEATURES = VAULT / "Features"

DOMAINS = {
    "world", "items", "characters", "memory", "ai", "rules", "library",
    "ui", "environment", "graph", "gameplay", "testing", "docs", "data",
}
SURFACES = {"in-game", "in-editor", "lens", "api", "docs"}
STATUSES = {"wired", "authored", "planned", "unwired"}
TOPICS = {
    "memory-dynamics", "retrieval", "embeddings", "reflection", "turns",
    "authoring", "determinism", "performance", "validation",
}

#: Folder (relative to the vault) -> the system domain its notes document.
FOLDER_DOMAIN = {
    "AI & Narration": "ai",
    "Characters": "characters",
    "Environment": "environment",
    "Gameplay": "gameplay",
    "Items & Inventory": "items",
    "Library System": "library",
    "Rules Engine": "rules",
    "Templates": "data",
    "UI & Settings": "ui",
    "World Building": "world",
    "testing": "testing",
    "design": "docs",
}

#: Root-level notes whose domain cannot be read off a folder.
ROOT_DOMAIN = {
    "Feature Map": "docs",
    "Simulation Model": "world",
    "History": "docs",
    "Roadmap": "docs",
    "Roadmap-core-systems": "docs",
    "Scenario Catalogue": "data",
    "Scenario Workflows & UI Audit": "docs",
    "ScenarioCreationGuide": "ui",
    "Welcome": "docs",
    "_Index": "docs",
    "Emotion & Mood — Whole-System Analysis": "characters",
}

#: Notes whose folder is broader than the system they document.
FILE_DOMAIN = {
    "Memory System": "memory",
    "Memory Dynamics": "memory",
    "Turn-Based System": "ai",
    "Turn Queue & Human Turns": "gameplay",
    "Agent Engine": "ai",
    "LLM Providers": "ai",
    "Narration System": "ai",
    "Items Overview": "items",
    "Item & Action Model": "items",
    "Characters Overview": "characters",
    "Emotion & Affect System": "characters",
    "Relationships System": "characters",
    "NPC Behavior System": "characters",
    "Background Simulation": "characters",
    "Search & Forage": "gameplay",
    "Per-Agent Knowledge (Fog of War)": "gameplay",
    "Graph System": "graph",
    "WorldPainter": "graph",
    "Grid to Graph": "graph",
    "World Scopes": "world",
    "Rooms & Areas": "world",
    "Doors & Connections": "world",
    "Way Properties": "world",
    "Temperature System": "environment",
    "Light System": "environment",
    "Time & Weather": "environment",
    "Tags System": "library",
    "Inspector Panels": "ui",
    "Event Stream": "ui",
    "Soak Lab": "testing",
    "Library 2.0 - Unified Library Design": "library",
    "diff-modal": "ui",
    "Domain & Role Tags": "library",
}

#: Topical tags for notes whose subject is a named cross-cutting concern.
FILE_TOPICS = {
    "Memory System": {"memory-dynamics"},
    "Memory Dynamics": {"memory-dynamics", "reflection", "retrieval"},
    "Turn Queue & Human Turns": {"turns"},
    "Turn-Based System": {"turns"},
    "Agent Engine": {"turns", "reflection"},
    "Graph System": {"determinism"},
    "Way Properties": {"determinism"},
    "Soak Lab": {"performance"},
    "Validator & Issues": {"validation"},
    "Event Log Export": {"validation"},
    "Feature Map": {"validation"},
    "NL Editor": {"authoring"},
    "ScenarioCreationGuide": {"authoring"},
    "Scenarios Catalogue": {"authoring"},
}

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
_TAGS_RE = re.compile(r"^tags:\s*(.*)$", re.M)

_TAG_INDEX: dict[str, set[str]] | None = None


def tag_index() -> dict[str, set[str]]:
    """stem -> tags, built once from the notes that already carry tags.

    A feature page inherits its domain from the deep doc it links, which is the
    honest way round: the system doc knows what it documents, and the feature
    page follows it. Without this join every unmapped deep doc falls back to a
    default domain and 40 pages claim to be the same system.
    """
    global _TAG_INDEX
    if _TAG_INDEX is None:
        index: dict[str, set[str]] = {}
        for path in curated_docs():
            if path.parent == FEATURES:
                continue
            tags = set(read_tags(path.read_text(encoding="utf-8")))
            if tags:
                index[path.stem] = tags
                index.setdefault(path.stem.lower(), tags)
        _TAG_INDEX = index
    return _TAG_INDEX


def curated_docs() -> list[Path]:
    """Every vault note outside dev_tasks and Obsidian state."""
    return sorted(
        p for p in VAULT.rglob("*.md")
        if ".obsidian" not in p.parts and "dev_tasks" not in p.parts
    )


def vocabulary() -> set[str]:
    return ({"system/" + d for d in DOMAINS}
            | {"surface/" + s for s in SURFACES}
            | {"status/" + s for s in STATUSES}
            | {"topic/" + t for t in TOPICS})


def known(tag: str) -> bool:
    return tag in vocabulary()


def read_tags(text: str) -> list[str]:
    m = _FM_RE.match(text)
    if not m:
        return []
    line = _TAGS_RE.search(m.group(1))
    if not line:
        return []
    raw = line.group(1).strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


def derive_tags(path: Path) -> list[str]:
    """The tags this note should carry, from where it lives and what it is."""
    tags: set[str] = set()
    rel_parts = path.relative_to(VAULT).parts

    if rel_parts[0] == "Features":
        text = path.read_text(encoding="utf-8")
        section = re.search(r"^section:\s*(\S+)", text, re.M)
        status = re.search(r"^status:\s*(\S+)", text, re.M)
        if section:
            tags.add("surface/" + section.group(1))
        if status and status.group(1) in STATUSES:
            tags.add("status/" + status.group(1))
        # The domain follows the deep doc the page links: a feature page about
        # the cellar inherits system/world from [[Rooms & Areas]]. Only the
        # **How it works** links count — the Connected section links the Feature
        # Map, and inheriting from that would tag every feature page as docs.
        # The join is through the deep doc's own tags, so it stays correct as
        # those change.
        how = re.search(r"^## How it works\s*$(.*?)(?=^## )", text, re.S | re.M)
        links = re.findall(r"\[\[([^\]|#]+)", how.group(1) if how else "")
        index = tag_index()
        for target in links:
            stem = Path(target.strip()).name
            if stem in ("Feature Map", "Features Overview"):
                continue
            inherited = {t for t in index.get(stem, set()) if t.startswith("system/")}
            if inherited:
                tags |= inherited
            else:
                domain = FILE_DOMAIN.get(stem) or FOLDER_DOMAIN.get(target.split("/")[0])
                if domain:
                    tags.add("system/" + domain)
        if not any(t.startswith("system/") for t in tags):
            tags.add("system/gameplay")
        return sorted(tags)

    folder = rel_parts[0] if len(rel_parts) > 1 else ""
    domain = FILE_DOMAIN.get(path.stem) or FOLDER_DOMAIN.get(folder) or ROOT_DOMAIN.get(path.stem)
    if domain:
        tags.add("system/" + domain)
    tags |= {"topic/" + t for t in FILE_TOPICS.get(path.stem, set())}
    if path.parent == VAULT and path.stem.startswith("Patch Notes"):
        tags.add("surface/docs")
    return sorted(tags)


def apply_tags() -> int:
    """Write derived tags into each note's frontmatter. Other keys untouched."""
    changed = 0
    for path in curated_docs():
        text = path.read_text(encoding="utf-8")
        want = derive_tags(path)
        if not want:
            continue
        line = f"tags: [{', '.join(want)}]"
        m = _FM_RE.match(text)
        if not m:
            new_text = f"---\ntype: doc\n{line}\n---\n\n{text.lstrip()}"
        elif _TAGS_RE.search(m.group(1)):
            new_text = _TAGS_RE.sub(line, text, count=1)
        else:
            block = m.group(1).rstrip()
            new_text = f"---\n{block}\n{line}\n---\n{text[m.end():]}"
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
    return changed


def check() -> int:
    problems: list[str] = []
    untagged: list[str] = []
    for path in curated_docs():
        tags = read_tags(path.read_text(encoding="utf-8"))
        if not tags:
            untagged.append(str(path.relative_to(VAULT)))
        for tag in tags:
            if not known(tag):
                problems.append(f"{path.relative_to(VAULT)}: '{tag}' is not in the vocabulary")
    for rel in untagged:
        sys.stderr.write(f"  - {rel}: no tags (run --apply)\n")
    if problems or untagged:
        sys.stderr.write(f"{len(problems)} out-of-vocabulary tag(s), "
                         f"{len(untagged)} untagged note(s)\n")
        return 1
    return 0


def report() -> None:
    counts: Counter[str] = Counter()
    untagged = 0
    total = 0
    for path in curated_docs():
        total += 1
        tags = read_tags(path.read_text(encoding="utf-8"))
        if not tags:
            untagged += 1
        counts.update(tags)
    print(f"{total} curated notes · {untagged} untagged · {len(counts)} distinct tags\n")
    for tag, n in counts.most_common():
        print(f"  {n:>3}  {tag}")
    unused = sorted(vocabulary() - set(counts))
    if unused:
        print("\nunused vocabulary entries:", ", ".join(unused))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write derived tags into frontmatter")
    parser.add_argument("--report", action="store_true", help="per-tag usage and untagged notes")
    parser.add_argument("--check", action="store_true", help="fail on a tag outside the vocabulary")
    args = parser.parse_args()

    if args.apply:
        changed = apply_tags()
        print(f"tagged {changed} note(s)")
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