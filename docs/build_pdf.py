#!/usr/bin/env python3
"""Build docs.pdf from the docs/ folder.

Usage examples
--------------
python docs/build_pdf.py
python docs/build_pdf.py --section virtualWorld --status done,inprogress
python docs/build_pdf.py --max-files 200 --output docs/quick-ref.pdf

Ordering strategy
-----------------
1. Top-level dirs: design/, scenarios/, superpowers/ (alphabetical within each)
2. docs/virtualWorld/ section files, ordered by the section table in _Index.md
   (everything not listed there falls back to alphabetical)
3. docs/virtualWorld/dev_tasks/ in workflow order:
   todo/ -> inprogress/ -> review/ -> done/
   alphabetical within each status bucket

Output: docs/docs.html  (intermediate)
        docs/docs.pdf  (final, produced by Playwright browser tool)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import markdown
except ImportError:
    sys.exit("markdown is required: pip install markdown")


REPO_ROOT = Path(__file__).resolve().parent
DOCS_DIR = REPO_ROOT
OUTPUT_HTML = DOCS_DIR / "docs.html"
OUTPUT_PDF = DOCS_DIR / "docs.pdf"

# ---------------------------------------------------------------------------
# Parse ordering from _Index.md
# ---------------------------------------------------------------------------

WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


def extract_index_order(index_path: Path) -> List[str]:
    """Return relative paths (under docs/virtualWorld/) in section-table order.

    We scan every wiki link in _Index.md and keep the first occurrence order.
    Only paths that actually exist on disk are retained.
    """
    text = index_path.read_text(encoding="utf-8", errors="replace")
    seen: list[str] = []
    seen_set: set[str] = set()
    for m in WIKI_LINK_RE.finditer(text):
        candidate = m.group(1).strip()
        # Normalise: wiki links use forward slashes
        candidate = candidate.replace("\\", "/")
        if candidate not in seen_set:
            seen.append(candidate)
            seen_set.add(candidate)
    # Keep only paths that exist inside docs/virtualWorld/
    base = DOCS_DIR / "virtualWorld"
    ordered = []
    for rel in seen:
        if (base / rel).is_file():
            ordered.append(rel)
    return ordered


# ---------------------------------------------------------------------------
# File collection & ordering
# ---------------------------------------------------------------------------

TOP_LEVEL_DIRS = ["design", "scenarios", "superpowers"]

DEV_TASKS_STATUS_ORDER = ["todo", "inprogress", "review", "done"]


def matches_section(path: Path, section: str | None) -> bool:
    if section is None:
        return True
    rel = path.relative_to(DOCS_DIR).as_posix().lower()
    return rel.startswith(section.lower() + "/") or rel.startswith(section.lower() + "\\")


def matches_status(path: Path, allowed_statuses: set[str] | None) -> bool:
    if not allowed_statuses:
        return True
    rel = path.relative_to(DOCS_DIR / "virtualWorld" / "dev_tasks")
    if str(rel).startswith(".."):
        return False
    status = rel.parts[0] if rel.parts else ""
    return status in allowed_statuses


def matches_exclude(path: Path, exclude_prefixes: list[str] | None) -> bool:
    if not exclude_prefixes:
        return True
    rel = path.relative_to(DOCS_DIR).as_posix().lower()
    return not any(rel.startswith(p.lower().rstrip("/") + "/") or rel.startswith(p.lower().rstrip("\\") + "\\") for p in exclude_prefixes)


def collect_files(index_order: List[str], section: str | None, allowed_statuses: set[str] | None, max_files: int | None, exclude_prefixes: list[str] | None) -> List[Tuple[Path, str]]:
    """Return [(path, heading_prefix), ...] in desired page order.

    heading_prefix is used to generate a clickable in-document TOC title line.
    """
    files: List[Tuple[Path, str]] = []

    # 1. Top-level dirs
    for dirname in TOP_LEVEL_DIRS:
        d = DOCS_DIR / dirname
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*.md")):
            if not matches_section(f, section):
                continue
            if not matches_exclude(f, exclude_prefixes):
                continue
            files.append((f, dirname))
            if max_files is not None and len(files) >= max_files:
                return files

    # 2. virtualWorld/ ordered by _Index.md, then remaining files alphabetically
    vw_base = DOCS_DIR / "virtualWorld"
    vw_indexed = {p.replace("\\", "/"): p for p in index_order}

    indexed_paths: List[Path] = []
    remaining: List[Path] = []

    for f in sorted(vw_base.rglob("*.md")):
        if not matches_section(f, section):
            continue
        if not matches_exclude(f, exclude_prefixes):
            continue
        rel = f.relative_to(vw_base).as_posix()
        if rel in vw_indexed:
            indexed_paths.append(f)
        else:
            remaining.append(f)

    # Put indexed files in _Index.md order
    seen_idx: set[Path] = set()
    for rel in index_order:
        if max_files is not None and len(files) >= max_files:
            break
        for f in indexed_paths:
            if f.relative_to(vw_base).as_posix() == rel and f not in seen_idx:
                files.append((f, "virtualWorld"))
                seen_idx.add(f)
                if max_files is not None and len(files) >= max_files:
                    break

    for f in sorted(remaining):
        if max_files is not None and len(files) >= max_files:
            break
        if not matches_exclude(f, exclude_prefixes):
            continue
        files.append((f, "virtualWorld"))

    # 3. dev_tasks/ ordered by status workflow
    dt_base = DOCS_DIR / "virtualWorld" / "dev_tasks"
    if dt_base.is_dir():
        status_files: dict[str, List[Path]] = {s: [] for s in DEV_TASKS_STATUS_ORDER}
        for f in dt_base.rglob("*.md"):
            if not matches_status(f, allowed_statuses):
                continue
            if not matches_exclude(f, exclude_prefixes):
                continue
            rel = f.relative_to(dt_base)
            status = rel.parts[0] if rel.parts else ""
            if status in status_files:
                status_files[status].append(f)

        for status in DEV_TASKS_STATUS_ORDER:
            if max_files is not None and len(files) >= max_files:
                break
            for f in sorted(status_files[status]):
                files.append((f, f"dev_tasks/{status}"))
                if max_files is not None and len(files) >= max_files:
                    break

    return files


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

MD_EXTENSIONS = [
    "extra",
    "tables",
    "toc",
    "nl2br",
    "sane_lists",
]


def md_to_html(md_text: str, title: str) -> str:
    """Convert a markdown snippet to a self-contained HTML fragment."""
    body = markdown.markdown(md_text, extensions=MD_EXTENSIONS)
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.55;
      color: #1a1a1a;
      max-width: 100%;
      margin: 0;
      padding: 2.4rem 3rem;
    }}
    h1, h2, h3, h4 {{
      page-break-after: avoid;
      margin-top: 1.4em;
      margin-bottom: 0.4em;
    }}
    h1 {{ font-size: 1.6em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }}
    h2 {{ font-size: 1.3em; border-bottom: 1px solid #e5e5e5; padding-bottom: 0.15em; }}
    h3 {{ font-size: 1.1em; }}
    p {{ margin: 0.6em 0; }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1em 0;
      font-size: 10pt;
    }}
    th, td {{
      border: 1px solid #bbb;
      padding: 0.35em 0.6em;
      text-align: left;
    }}
    th {{ background: #f5f5f5; }}
    code {{
      background: #f4f4f4;
      padding: 0.15em 0.35em;
      border-radius: 3px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.92em;
    }}
    pre {{
      background: #f7f7f7;
      border: 1px solid #e3e3e3;
      padding: 0.8em 1em;
      overflow-x: auto;
      font-size: 10pt;
      line-height: 1.45;
    }}
    pre code {{
      background: transparent;
      padding: 0;
    }}
    blockquote {{
      border-left: 3px solid #ccc;
      margin: 1em 0;
      padding: 0.4em 1em;
      color: #444;
    }}
    ul, ol {{ margin: 0.5em 0; padding-left: 1.6em; }}
    img {{ max-width: 100%; height: auto; }}
    a {{ color: #1155cc; text-decoration: none; }}
    hr {{ border: none; border-top: 1px solid #ddd; margin: 2em 0; }}
    .page-break {{ page-break-after: always; }}
  </style>
</head>
<body>
  {body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build docs.pdf from docs/")
    parser.add_argument("--section", help="Only include this top-level section, e.g. virtualWorld or design")
    parser.add_argument("--status", help="Comma-separated dev_tasks statuses to include: todo,inprogress,review,done")
    parser.add_argument("--max-files", type=int, help="Cap number of markdown files included")
    parser.add_argument("--output", help="Output HTML path, default docs/docs.html")
    parser.add_argument("--exclude", help="Comma-separated path prefixes to exclude, e.g. virtualWorld/dev_tasks")
    args = parser.parse_args()

    index_path = DOCS_DIR / "virtualWorld" / "_Index.md"
    if not index_path.is_file():
        sys.exit(f"Cannot find {index_path}")

    index_order = extract_index_order(index_path)
    allowed_statuses = {s.strip() for s in args.status.split(",") if s.strip()} if args.status else None
    exclude_prefixes = [s.strip() for s in args.exclude.split(",") if s.strip()] if args.exclude else None
    file_entries = collect_files(index_order, args.section, allowed_statuses, args.max_files, exclude_prefixes)

    if not file_entries:
        sys.exit("No markdown files found for the selected filters.")

    html_pages: List[str] = []
    for path, section in file_entries:
        rel = path.relative_to(DOCS_DIR).as_posix()
        title = f"{section}/{path.name}"
        md_text = path.read_text(encoding="utf-8", errors="replace")
        page_html = md_to_html(md_text, title)
        html_pages.append(page_html)

    combined = "\n".join(html_pages)
    output_html = Path(args.output) if args.output else OUTPUT_HTML
    output_html.write_text(combined, encoding="utf-8")
    print(f"Wrote {output_html} ({len(file_entries)} pages)")
    print(f"Next: open {output_html} in a browser and print to PDF,")
    print(f"      or use the Playwright tool to render {output_html} -> {OUTPUT_PDF}")


if __name__ == "__main__":
    main()

