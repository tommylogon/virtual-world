"""Audit the authored content passes against the library on disk.

    python tools/audit_item_content.py           # report
    python tools/audit_item_content.py --strict  # exit 1 on anything missing

**Why this exists.** On 2026-09-30, 545 authored items were absent from
`data/library/items` and the pass that produced them was reported as written,
because the count came from what the generator *wrote* rather than what was
*there*. A stray delete — one `Remove-Item` that hit a filename with a space in
it and whose error was silenced — took them, and nothing in the repository
noticed, because the tables that produced them were in a temp directory.

The same thing is also a test (`tests/test_library_content_pass.py`), so a
regression fails the suite rather than needing somebody to remember to run this.
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import item_shapes  # noqa: E402

PASSES = (1, 2, 3, 4, 5)


def load(n):
    """Import pass *n* from `tools/`, by path so a stale `sys.modules` cannot win."""
    name = "item_content_pass%d" % n
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(TOOLS, "item_content_pass%d.py" % n))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def records_by_pass():
    return {"pass%d" % n: load(n).build() for n in PASSES}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    missing = item_shapes.audit(records_by_pass(), verbose=True)
    total = sum(len(v) for v in missing.values())
    if total and "--strict" in argv:
        print("\n%d authored item(s) are missing from the library — run the "
              "passes that own them." % total)
        return 1
    if not total:
        print("\nevery authored item is on disk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
