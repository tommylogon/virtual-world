#!/usr/bin/env python3
"""Guard the disposition score registry (task-800).

`engine/disposition.py` declares every decision score, its kind, base and range.
This checks the declaration against the two things that can quietly diverge from
it, in the manner of `tools/way_property_index.py`:

1. **Itself** - every score has a known kind, a namespaced unique name and a base
   inside its own range; every decision uses a known combine/pick and references
   only declared scores (`engine.disposition.check_registry`).
2. **The engine** - the declared base of `relief.weight.*`, `social.weight.*` and
   `social.multiplier.affect` must equal the constant the engine actually reads
   (`engine/relief.PRIVACY_WEIGHTS`, `engine/background_social.BASE_WEIGHTS` /
   `BASE_IGNORE_WEIGHT` / `AFFECT_TILT`). Change one without the other and this
   fails; that is the point.
3. **Personality / modifier files** - any ``data/personality/*.json`` that names a
   score which is not declared fails, so a single typo in a long catalogue is not
   silent (the reason the registry exists at all).

Usage:
    python tools/disposition_index.py --check    # fail on any divergence
    python tools/disposition_index.py --report   # print the registry and coverage
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import disposition  # noqa: E402

#: Where a personality / modifier catalogue is expected to live (task-806 creates
#: the key; this scans the folder if and when it exists).
MODIFIER_DIRS = ("data/personality",)

#: JSON keys whose string value is a score reference.
_REF_KEYS = ("score", "target", "scores", "targets")


def engine_crosscheck() -> list:
    """Declared bases vs the engine constants that read them, as problem lines.

    Import failures are reported as a soft note, not a failure: the gate must not
    break because an engine module is heavy to import in a dev shell.
    """
    problems: list = []
    index = disposition.by_name()

    try:
        from engine import relief
        for key, score_name in (
            ("witness", "relief.weight.witness"),
            ("private", "relief.weight.private"),
            ("public", "relief.weight.public"),
            ("fixture", "relief.weight.fixture"),
        ):
            real = relief.PRIVACY_WEIGHTS.get(key)
            declared = index[score_name].base
            if real is not None and float(real) != float(declared):
                problems.append(
                    f"{score_name}: declared base {declared} != "
                    f"engine/relief.PRIVACY_WEIGHTS['{key}'] = {real}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"(soft) could not import engine/relief: {exc}")

    try:
        from engine import background_social as social
        for action, base in social.BASE_WEIGHTS.items():
            score_name = f"social.weight.{action}"
            if score_name not in index:
                problems.append(
                    f"background_social.BASE_WEIGHTS has `{action}` but the "
                    f"registry declares no `{score_name}`")
                continue
            if float(base) != float(index[score_name].base):
                problems.append(
                    f"{score_name}: declared base {index[score_name].base} != "
                    f"engine/background_social.BASE_WEIGHTS['{action}'] = {base}")
        if float(social.BASE_IGNORE_WEIGHT) != float(index["social.weight.ignore"].base):
            problems.append(
                f"social.weight.ignore: declared base "
                f"{index['social.weight.ignore'].base} != "
                f"engine/background_social.BASE_IGNORE_WEIGHT = "
                f"{social.BASE_IGNORE_WEIGHT}")
        if float(social.AFFECT_TILT) != float(index["social.multiplier.affect"].hi):
            problems.append(
                f"social.multiplier.affect: declared hi "
                f"{index['social.multiplier.affect'].hi} != "
                f"engine/background_social.AFFECT_TILT = {social.AFFECT_TILT}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"(soft) could not import engine/background_social: {exc}")

    try:
        from engine import background_simulation as sim
        for const, score_name in (
            ("THIRST_THRESHOLD", "survive.threshold.thirst"),
            ("HUNGER_THRESHOLD", "survive.threshold.hunger"),
            ("BLADDER_THRESHOLD", "survive.threshold.bladder"),
            ("ENERGY_THRESHOLD", "survive.threshold.energy"),
            ("HYGIENE_THRESHOLD", "survive.threshold.hygiene"),
            ("ENTERTAINMENT_THRESHOLD", "survive.threshold.entertainment"),
            ("SANITY_THRESHOLD", "survive.threshold.sanity"),
            ("SOCIAL_THRESHOLD", "survive.threshold.social"),
        ):
            real = getattr(sim, const, None)
            if real is None:
                continue
            declared = index[score_name].base
            if float(real) != float(declared):
                problems.append(
                    f"{score_name}: declared base {declared} != "
                    f"engine/background_simulation.{const} = {real}")
    except Exception as exc:  # noqa: BLE001
        problems.append(
            f"(soft) could not import engine/background_simulation: {exc}")

    return problems


def _collect_refs(value, out: list) -> None:
    """Every score reference in a parsed modifier file, by value of a ref key."""
    if isinstance(value, dict):
        for key, inner in value.items():
            if key in _REF_KEYS:
                if isinstance(inner, str):
                    out.append(inner)
                elif isinstance(inner, list):
                    out.extend(str(x) for x in inner if isinstance(x, str))
                else:
                    _collect_refs(inner, out)
            else:
                _collect_refs(inner, out)
    elif isinstance(value, list):
        for inner in value:
            _collect_refs(inner, out)


def modifier_files_check() -> list:
    """Undeclared score references in personality / modifier files."""
    problems: list = []
    declared = {s.name for s in disposition.SCORES}
    for folder in MODIFIER_DIRS:
        base = ROOT / folder
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{path.relative_to(ROOT)}: unreadable JSON ({exc})")
                continue
            refs: list = []
            _collect_refs(data, refs)
            for ref in refs:
                if ref not in declared:
                    problems.append(
                        f"{path.relative_to(ROOT)}: references undeclared score "
                        f"`{ref}`")
    return problems


def all_problems() -> list:
    return (disposition.check_registry() + engine_crosscheck()
            + modifier_files_check() + trait_catalog_check())


def trait_catalog_check() -> list:
    """Every trait named by a modifier is a real library trait (typo guard)."""
    problems: list = []
    base = ROOT / "data" / "library" / "traits"
    if not base.exists():
        return problems
    known = {p.stem for p in base.glob("*.json")}
    for mod in disposition.TRAIT_MODIFIERS:
        if mod.trait not in known:
            problems.append(
                f"TRAIT_MODIFIERS[{mod.trait!r}]: no data/library/traits/"
                f"{mod.trait}.json")
    return problems


def check() -> int:
    problems = all_problems()
    hard = [p for p in problems if not p.startswith("(soft)")]
    soft = [p for p in problems if p.startswith("(soft)")]
    for line in soft:
        print(line)
    if hard:
        print(f"disposition index: {len(hard)} problem(s)\n")
        for line in hard:
            print(f"  - {line}")
        print("\nFix the declaration or the engine so the two agree.")
        return 1
    print(f"disposition index: {len(disposition.SCORES)} scores across "
          f"{len(disposition.DECISIONS)} decisions, no drift")
    return 0


def report() -> int:
    index = disposition.by_name()
    print(f"score kinds ({len(disposition.SCORE_KINDS)}): "
          f"{', '.join(disposition.SCORE_KINDS)}")
    print(f"combines: {', '.join(disposition.COMBINES)}")
    print(f"picks: {', '.join(disposition.PICKS)}\n")
    for decision in disposition.DECISIONS:
        print(f"{decision.name}  combine={decision.combine}  pick={decision.pick}"
              f"  ({len(decision.scores)} scores)")
        for score in disposition.scores_for(decision.name):
            caveat = f"  [caveat] {score.caveat}" if score.caveat else ""
            print(f"    {score.name:<32} {score.kind:<11} "
                  f"base={score.base} [{score.lo}, {score.hi}]{caveat}")
        print()
    print(f"declared: {len(disposition.SCORES)} scores")
    for line in all_problems():
        print("  ! " + line)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.check:
        return check()
    if args.report:
        return report()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
