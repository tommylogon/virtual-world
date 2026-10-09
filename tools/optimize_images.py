#!/usr/bin/env python3
"""optimize_images.py — report WebP savings for static images, optionally convert.

The static image tree (``static/images``) is dominated by PNGs that compress
very poorly: character expression portraits (~300 KB each at 384x335) and
photographic backgrounds (up to ~4.3 MB at 1536x1024). Re-encoding as WebP
reduces them by roughly an order of magnitude, which cuts both transfer size and
the main-thread decode cost of a refresh.

Dry-run by default: prints per-file before/after bytes and a total, and writes
nothing. Pass ``--apply`` to write ``.webp`` siblings, and ``--update-refs`` to
rewrite the ``images/nodes/<name>.<ext>`` paths in ``data/`` and ``engine/`` to
the new ``.webp`` names. Originals are kept unless ``--delete-originals``.

Usage:
    python tools/optimize_images.py                       # report only
    python tools/optimize_images.py --max-dim 1024        # report a downscale
    python tools/optimize_images.py --apply --update-refs # convert + rewrite refs

Gates: this is a one-off tool, not wired to CI.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - environment guard
    print("Pillow is required: pip install Pillow", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIRS = [ROOT / "static" / "images"]
SOURCE_EXTS = {".png", ".jpg", ".jpeg"}
# Data + engine text files that may hold a literal image path to rewrite.
REF_GLOBS = ["data/**/*.json", "engine/**/*.py", "static/js/**/*.ts"]


def human(n: int) -> str:
    return f"{n / 1024:,.0f} KB"


def collect(dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for d in dirs:
        if d.is_file() and d.suffix.lower() in SOURCE_EXTS:
            files.append(d)
        elif d.is_dir():
            for p in d.rglob("*"):
                if p.suffix.lower() in SOURCE_EXTS:
                    files.append(p)
    return sorted(files)


def encode_webp(src: Path, quality: int, max_dim: int) -> bytes:
    with Image.open(src) as im:
        im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
        if max_dim and max(im.size) > max_dim:
            scale = max_dim / max(im.size)
            new = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
            im = im.resize(new, Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=quality, method=6)
        return buf.getvalue()


def rewrite_refs(renames: dict[str, str], apply: bool) -> int:
    """Rewrite ``<old-basename>.<ext>`` references to the new ``.webp`` name.

    Matches the basename (with optional path prefix) so both
    ``images/nodes/foo-123.png`` and a bare ``foo-123.png`` are caught. Returns
    the number of files changed (or that would change on a dry run)."""
    if not renames:
        return 0
    # Longest names first so a prefix never shadows a full match.
    names = sorted(renames.keys(), key=len, reverse=True)
    pattern = re.compile(r"(" + "|".join(re.escape(n) for n in names) + r")")
    changed = 0
    for glob in REF_GLOBS:
        for path in ROOT.glob(glob):
            if ".kilo" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            new_text = pattern.sub(lambda m: renames[m.group(1)], text)
            if new_text != text:
                changed += 1
                if apply:
                    path.write_text(new_text, encoding="utf-8")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="Report/convert static images to WebP.")
    ap.add_argument("paths", nargs="*", type=Path, default=None,
                    help="Files or directories (default: static/images).")
    ap.add_argument("--quality", type=int, default=82, help="WebP quality (default 82).")
    ap.add_argument("--max-dim", type=int, default=0,
                    help="Downscale so the longest side is at most this (0 = keep).")
    ap.add_argument("--apply", action="store_true", help="Write .webp files.")
    ap.add_argument("--update-refs", action="store_true",
                    help="Rewrite image paths in data/ and engine/ to .webp.")
    ap.add_argument("--delete-originals", action="store_true",
                    help="Remove the source files after a successful convert.")
    args = ap.parse_args()

    dirs = args.paths or DEFAULT_DIRS
    files = collect(dirs)
    if not files:
        print("No images found.", file=sys.stderr)
        return 1

    before_total = 0
    after_total = 0
    renames: dict[str, str] = {}
    written = 0
    print(f"Scanning {len(files)} image(s); quality={args.quality}, max-dim={args.max_dim or 'keep'}")
    for src in files:
        before = src.stat().st_size
        try:
            data = encode_webp(src, args.quality, args.max_dim)
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"  ! {src.relative_to(ROOT)}: {e}")
            before_total += before
            after_total += before
            continue
        after = len(data)
        before_total += before
        after_total += after
        dst = src.with_suffix(".webp")
        renames[src.name] = dst.name
        pct = (1 - after / before) * 100 if before else 0
        print(f"  {src.relative_to(ROOT)}: {human(before)} -> {human(after)}  ({pct:.0f}% smaller)")
        if args.apply:
            dst.write_bytes(data)
            written += 1
            if args.delete_originals:
                os.remove(src)

    pct_total = (1 - after_total / before_total) * 100 if before_total else 0
    print(f"\n{len(files)} image(s): {human(before_total)} -> {human(after_total)}  ({pct_total:.0f}% smaller)")

    if args.apply:
        print(f"Wrote {written} .webp file(s).")
    if args.update_refs:
        changed = rewrite_refs(renames, apply=args.apply)
        verb = "Rewrote" if args.apply else "Would rewrite"
        print(f"{verb} references in {changed} file(s).")
    elif args.apply:
        print("NOTE: originals' paths in data/ still point at the old files. "
              "Re-run with --update-refs (and --delete-originals) to finish the migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
