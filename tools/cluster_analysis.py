#!/usr/bin/env python3
"""
tools/cluster_analysis.py

Analyzes scratch/client_audit_data.json and extracts:
1. Subsystem groupings and file responsibilities
2. Duplication matrices (Modal backdrops, Headers, Sliders, Tabs, Badges)
3. Model/Domain contracts needed vs currently untyped 'any'
4. Candidate Component Specifications (props, events, outputs)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "scratch" / "client_audit_data.json"

def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    records = data["records"]

    # Group by directory
    by_dir = {}
    for r in records:
        d = r["dir"]
        by_dir.setdefault(d, []).append(r)

    print("=== DIRECTORY SUMMARY ===")
    for d, files in sorted(by_dir.items(), key=lambda x: len(x[1]), reverse=True):
        lines = sum(f["lines"] for f in files)
        anys = sum(f["any_count"] for f in files)
        print(f"Dir: {d:25} | Files: {len(files):2} | Lines: {lines:6} | Any: {anys:4}")

    # Duplication matrix
    print("\n=== DUPLICATION AUDIT ===")
    modals = [r["file"] for r in records if r["duplication_flags"]["modal"]]
    headers = [r["file"] for r in records if r["duplication_flags"]["header_sync"]]
    dangers = [r["file"] for r in records if r["duplication_flags"]["danger_zone"]]
    tabs = [r["file"] for r in records if r["duplication_flags"]["tabs"]]
    sliders = [r["file"] for r in records if r["duplication_flags"]["slider"]]
    badges = [r["file"] for r in records if r["duplication_flags"]["badge"]]

    print(f"Files implementing Modals/Overlays: {len(modals)}")
    for f in modals[:10]:
        print(f"  - {f}")
    print(f"Files implementing Headers/Sync: {len(headers)}")
    for f in headers[:10]:
        print(f"  - {f}")
    print(f"Files implementing Danger Zones/Deletes: {len(dangers)}")
    for f in dangers[:10]:
        print(f"  - {f}")
    print(f"Files implementing Tab navigation: {len(tabs)}")
    for f in tabs[:10]:
        print(f"  - {f}")
    print(f"Files implementing Sliders/Ranges: {len(sliders)}")
    for f in sliders[:10]:
        print(f"  - {f}")
    print(f"Files implementing Badges/Chips: {len(badges)}")
    for f in badges[:10]:
        print(f"  - {f}")

    # Worst 'any' offenders
    print("\n=== WORST 'ANY' OFFENDERS ===")
    worst_any = sorted(records, key=lambda r: r["any_count"], reverse=True)[:15]
    for r in worst_any:
        print(f"{r['file']:45} | Any: {r['any_count']:4} | Lines: {r['lines']:5} | Arch: {r['dom_arch']}")

    # Monolithic files (> 1500 lines)
    print("\n=== MONOLITHIC FILES (> 1500 lines) ===")
    monoliths = [r for r in records if r["lines"] > 1500]
    for r in monoliths:
        print(f"{r['file']:45} | Lines: {r['lines']:5} | Any: {r['any_count']:4} | Arch: {r['dom_arch']}")

if __name__ == "__main__":
    main()
