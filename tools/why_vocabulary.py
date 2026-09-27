"""One-off: enumerate the `why` prefixes the engine actually writes.

Task-543's spec listed a vocabulary that turned out to be incomplete — the
rejection counter caught `traversal:`, `forage:` and `schedule:` in a real run.
This measures reality so the accepted set is derived from the code rather than
copied from a task file (one writer, no drift).
"""
import collections
import pathlib
import re
import sys

PATTERN = re.compile(r"""why\s*=\s*f?["']([a-z_]+):""")
SKIP = {"live_log"}


def main() -> int:
    found = collections.Counter()
    sites = collections.defaultdict(list)
    for path in sorted(pathlib.Path("engine").glob("*.py")):
        if path.stem in SKIP:
            continue
        for index, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            for match in PATTERN.finditer(line):
                prefix = match.group(1)
                found[prefix] += 1
                sites[prefix].append(f"{path.name}:{index}")
    for prefix, count in sorted(found.items(), key=lambda kv: -kv[1]):
        print(f"{prefix + ':':<14} {count:>4}   {', '.join(sites[prefix][:3])}")
    print(f"\n{len(found)} distinct prefixes, {sum(found.values())} literal sites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
