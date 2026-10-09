"""hazard_index.py — validate terrain hazards (task-745).

The registry is policy-as-data (`data/worldpainter/hazards.json`). This tool is
the gate: `--check` runs `engine.hazards.validate()` and exits non-zero on any
problem; `--report` prints each hazard's ladder so a retune is reviewable.

Usage:
    python tools/hazard_index.py --check
    python tools/hazard_index.py --report
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import hazards  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail on any problem in the registry")
    parser.add_argument("--report", action="store_true",
                        help="print each hazard's ability and ladder")
    args = parser.parse_args()

    if args.report:
        for hid, rec in sorted(hazards.hazards().items()):
            rungs = " ".join(f"{t}:{d}" for t, d in hazards.ladder(rec))
            print(f"{hid:12} {str(rec.get('ability') or '?'):4} {rungs}")

    problems = hazards.validate()
    if args.check:
        if problems:
            for problem in problems:
                print(f"FAIL {problem}")
            return 1
        print(f"hazard registry OK ({len(hazards.hazards())} hazards)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
