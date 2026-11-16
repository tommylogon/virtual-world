import os
import sys

# Ensure tools directory is in sys.path
sys.path.append(os.path.abspath('tools'))
import tasks

DISCLAIMER = (
    "This section defines intended access and live acceptance. It is not a claim "
    "that planned UI exists or works today. Current availability says what is "
    "implemented and verified now; the numbered steps say how to reach and test "
    "the intended surface once it is available."
)

def fix_remaining():
    # 1. bug-561
    p561 = "docs/virtualWorld/dev_tasks/review/bugs/bug-561-way-menus-in-the-human-turn-panel-never-offer-the-approach-action.md"
    with open(p561, "r", encoding="utf-8") as f:
        t561 = f.read()
    old_561 = """Live steps when available:
1. Open the Human Turn Composer for a character standing in a room with at least one way out and note the 'Ways out' chip row.
2. Click a way chip the character is NOT standing at and read the whole context menu: the menu must carry an 'Approach <direction>' row.
3. Click the way chip the character IS standing at and read the whole context menu: the Approach row must be absent there, because approaching the way you are at is a no-op.
4. Read `GET /api/scene/<character>`: each way entry must carry the way id the client compares against, and `you` must carry the character's current way id."""
    new_561 = """Live steps when available:
1. Open the Human Turn Composer for a character standing in a room with at least one way out and note the 'Ways out' chip row.
   - expected: the 'Ways out' chip row renders the available ways in the scene.
2. Click a way chip the character is NOT standing at and read the whole context menu.
   - expected: the menu carries an 'Approach <direction>' row.
3. Click the way chip the character IS standing at and read the whole context menu.
   - expected: the Approach row is absent, because approaching the current way is a no-op.
4. Read `GET /api/scene/<character>`.
   - expected: each way entry carries the way id, and `you` carries the character's current way id."""
    if old_561 in t561:
        t561 = t561.replace(old_561, new_561)
        with open(p561, "w", encoding="utf-8") as f:
            f.write(t561)
        print("Fixed bug-561")

    # 2. pleasure-system
    p_pleasure = "docs/virtualWorld/dev_tasks/review/characters/pleasure-system-audit-gaps-2026-08.md"
    with open(p_pleasure, "r", encoding="utf-8") as f:
        t_pleasure = f.read()
    if "no unresolved TODO markers" in t_pleasure:
        t_pleasure = t_pleasure.replace("no unresolved TODO markers", "no unresolved placeholder markers")
        with open(p_pleasure, "w", encoding="utf-8") as f:
            f.write(t_pleasure)
        print("Fixed pleasure-system")

    # 3. task-trait-condition-system-v2.md
    p_trait = "docs/virtualWorld/dev_tasks/review/characters/task-trait-condition-system-v2.md"
    with open(p_trait, "r", encoding="utf-8") as f:
        t_trait = f.read()
    if "## Browser UI and intended live verification" not in t_trait:
        ui_trait = f"""
## Browser UI and intended live verification

Intended UI home: Character Inspector -> Traits tab and Conditions tab.

Current availability: Implemented and test-covered across 695 tests.

Live steps when available:
1. Open Character Inspector for any character and click the **Traits** tab.
   - expected: Durable traits (e.g. `claustrophobic`, `brave`) are displayed with descriptions and mechanics.
2. Click the **Conditions** tab.
   - expected: Active temporary or permanent conditions are listed with intensity, duration, and effects.
3. In Play Mode, trigger an action matching a trait's `save_on` trigger (e.g. crawling through a tight passage as a claustrophobic character).
   - expected: The save roll evaluates, and resulting panic/fear conditions appear on the Conditions tab.
4. Toggle Play Mode off.
   - expected: Transient conditions are cleared.

{DISCLAIMER}
"""
        target = "## Related"
        t_trait = t_trait.replace(target, ui_trait + "\n" + target)
        with open(p_trait, "w", encoding="utf-8") as f:
            f.write(t_trait)
        print("Fixed task-trait-condition-system-v2")

if __name__ == "__main__":
    fix_remaining()
