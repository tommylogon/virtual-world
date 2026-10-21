#!/usr/bin/env python3
"""Convert all Markdown under docs/ (except dev_tasks/) into a single PDF.

Usage:
    python tools/docs_to_pdf.py [--out PATH] [--root docs]

Requires: markdown-it-py, pymupdf (already in requirements? pymupdf present).
"""
import argparse
import os
import re
from pathlib import Path

from markdown_it import MarkdownIt
import pymupdf


def strip_frontmatter(text):
    if text.startswith("---"):
        m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
        if m:
            return text[m.end():]
    return text


def collect_md(root, exclude):
    files = []
    for p in sorted(Path(root).rglob("*.md")):
        rel = p.relative_to(root).as_posix()
        if any(seg in rel.split("/") for seg in exclude) or any(rel.startswith(e) for e in exclude):
            continue
        # exclude dev_tasks anywhere
        if "dev_tasks" in p.parts:
            continue
        files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs")
    ap.add_argument("--out", default="docs_combined.pdf")
    ap.add_argument("--exclude", nargs="*", default=["dev_tasks"])
    args = ap.parse_args()

    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    files = collect_md(args.root, args.exclude)
    print(f"found {len(files)} markdown files", flush=True)

    writer = pymupdf.DocumentWriter(args.out)
    def rectfn(i, filled):
        return pymupdf.paper_rect("a4"), pymupdf.Rect(50, 50, 545, 792), pymupdf.Matrix(1, 0, 0, 1, 0, 0)

    for idx, f in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {f.as_posix()}", flush=True)
        text = f.read_text(encoding="utf-8", errors="replace")
        text = strip_frontmatter(text)
        body = md.render(text)
        html = f"<h1>{f.as_posix()}</h1>\n{body}\n<hr/>"
        story = pymupdf.Story(html)
        story.write(writer, rectfn)
        if idx % 10 == 0 or idx == len(files):
            print(f"wrote {idx}/{len(files)}", flush=True)
    writer.close()
    print(f"done: {args.out} from {len(files)} markdown files", flush=True)


if __name__ == "__main__":
    main()
