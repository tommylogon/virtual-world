"""Author daily schedules onto the camp's characters (task-409).

Dry-run by default; `--apply` writes. Idempotent — re-running replaces the
schedules it authored, so it is safe to iterate on the table below.

Why this shape: a schedule is what turns the survival loop into a *day*. Before
it, every character ate, drank, slept and socialised wherever it happened to be,
and moved only when a need pushed it somewhere. With it, Mikka goes to the
Workshop, Gribba cooks, Vekka scouts, and they gather at the Chief's Pit in the
evening and sleep in the halls — which is also what makes the camp legible to a
player watching time run.

Night is placed, not performed: the `sleep` step only walks them to the Sleeping
Halls, and the Energy system does the sleeping when it is due. That is deliberate
— a schedule that *forced* sleep would fight the exhaustion ladder, and vice
versa.

Animals get no schedule on purpose. A boar or a raven does not have a working
day, and inventing one would be authoring behaviour nobody asked for; they keep
the pure need-driven roaming they have now.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.schedule import normalize  # noqa: E402

DEFAULT_SCENARIO = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"

#: The camp's working day. `{work}` is filled from ROLES below.
CAMP_DAY = [
    {"start": "06:00", "activity": "work", "area": "{work}", "fallback": "wait"},
    {"start": "12:00", "activity": "eat", "area": "Cooking Area"},
    {"start": "13:00", "activity": "work", "area": "{work}"},
    {"start": "18:00", "activity": "socialise", "area": "Chief's Pit"},
    {"start": "22:00", "activity": "sleep", "area": "Sleeping Halls"},
]

#: A villager's day, for the Eldenford humans. They sleep where they live.
VILLAGE_DAY = [
    {"start": "06:30", "activity": "work", "area": "{work}", "fallback": "wait"},
    {"start": "12:30", "activity": "eat", "area": "Eldenford"},
    {"start": "13:30", "activity": "work", "area": "{work}"},
    {"start": "19:00", "activity": "socialise", "area": "Eldenford"},
    {"start": "22:00", "activity": "sleep", "area": "Eldenford"},
]

#: character name -> (work area, day template). Placements already imply these
#: roles; the schedule only makes the implication explicit and timed.
ROLES = {
    # ── goblin camp ──────────────────────────────────────────────────────
    "Gribba": ("Cooking Area", CAMP_DAY),
    "Mikka": ("Workshop", CAMP_DAY),
    "Vekka": ("Scouting Rooms", CAMP_DAY),
    "Zikka": ("Training Pit", CAMP_DAY),
    "Kiala": ("Training Pit", CAMP_DAY),
    "Krikka": ("Scrap Pile", CAMP_DAY),
    "Arix": ("Scrap Pile", CAMP_DAY),
    "Belne": ("Camp Entrance Trail", CAMP_DAY),
    "Rikka": ("Chief's Pit", CAMP_DAY),
    "Thrazz": ("Chief's Den", CAMP_DAY),
    "Leslie": ("Food Storage", CAMP_DAY),
    # ── Eldenford humans ─────────────────────────────────────────────────
    "Eldenford Blacksmith": ("Eldenford", VILLAGE_DAY),
    "Eldenford Elder": ("Eldenford", VILLAGE_DAY),
    "Eldenford Merchant": ("Eldenford", VILLAGE_DAY),
    "Eldenford Farmer": ("Abandoned Farm", VILLAGE_DAY),
    "Eldenford Road Guard Captain": ("Human Road", VILLAGE_DAY),
}


def build_schedule(work_area, template):
    return normalize([
        {**step, "area": step["area"].replace("{work}", work_area)}
        for step in template
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default=str(DEFAULT_SCENARIO))
    parser.add_argument("--apply", action="store_true",
                        help="write the changes (default: dry run)")
    args = parser.parse_args()

    path = Path(args.scenario)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    players = data.get("players") or {}

    # Fail loudly on a name that is not in the scenario: a typo would otherwise
    # silently leave a character with no day at all.
    unknown = sorted(set(ROLES) - set(players))
    if unknown:
        print(f"ERROR: no such character(s) in the scenario: {unknown}")
        return 1

    changed = 0
    for name in sorted(players):
        role = ROLES.get(name)
        schedule = build_schedule(*role) if role else None
        if schedule is None:
            continue
        current = players[name].get("schedule")
        if normalize(current) == schedule:
            continue
        players[name]["schedule"] = schedule
        changed += 1
        hours = ", ".join(
            f"{s['start'] // 60:02d}:{s['start'] % 60:02d} {s['activity']}"
            f"{'@' + s['area'] if s.get('area') else ''}"
            for s in schedule
        )
        print(f"  {name:28s} {hours}")

    unscheduled = sorted(set(players) - set(ROLES))
    print(f"\n{changed} schedule(s) to write; {len(unscheduled)} character(s) left "
          f"unscheduled:")
    print(f"  {', '.join(unscheduled)}")

    if not args.apply:
        print("\n(dry run — pass --apply to write)")
        return 0
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
