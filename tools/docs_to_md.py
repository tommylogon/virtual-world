#!/usr/bin/env python3
"""Concatenate all Markdown under docs/ (except dev_tasks/) into one MD file.

Usage:
    python tools/docs_to_md.py [--out PATH] [--root docs]
"""
import argparse
from pathlib import Path


def collect_md(root):
    exclude_dirs = {"dev_tasks", "design"}
    exclude_names = {"feature-index.md", "js-module-index.md", "roadmap-computed.md",
                     "CHANGELOG.md", "PATCH_NOTES.md"}
    exclude_prefixes = ("Patch Notes", "Patch-Notes", "patch-notes", "patch_notes")
    files = []
    for p in sorted(Path(root).rglob("*.md")):
        if any(part in exclude_dirs for part in p.parts):
            continue
        if p.name in exclude_names:
            continue
        if p.name.startswith(exclude_prefixes):
            continue
        files.append(p)
    return files


def strip_frontmatter(text):
    if text.startswith("---"):
        import re
        m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
        if m:
            return text[m.end():]
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/virtualWorld")
    ap.add_argument("--out", default="docs_combined.md")
    args = ap.parse_args()

    files = collect_md(args.root)
    out = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        text = strip_frontmatter(text)
        out.append(f"# {f.as_posix()}\n\n{text.strip()}\n")
    Path(args.out).write_text("\n\n---\n\n".join(out), encoding="utf-8")
    print(f"wrote {args.out} from {len(files)} markdown files")


if __name__ == "__main__":
    main()
