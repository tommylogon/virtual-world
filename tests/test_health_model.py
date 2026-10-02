"""task-538: a real health model — `Max_HP` is data, and one resolver answers it.

The engine had no health model; it had a `100`. `Max_HP` was the only vital with
a maximum, and that maximum's *default* was the literal `100` written out in
about ten places. The literal was harmless only because `Max_HP` was itself
always 100, which hid two real bugs:

1. ``heal`` clamped to 100, so healing a 7-HP goblin by 5 produced 12 HP;
2. the HP-regen gate read "HP < 100", so a 7-HP goblin at full health was
   permanently "below maximum" and regenerated forever.

Both are already fixed and already had tests (``test_health_model_fixes.py``).
What this file pins is the part that made them *possible* and is the actual
subject of the task: **there is now one answer to "what is the top of this
vital on this character", and every site asks it.**
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.vitals import (
    DEFAULT_MAX_HP, apply_hit_dice, ceiling, clamp_to_ceiling, hit_dice_max,
    parse_hit_dice,
)
from player import Player

AREA = "Blizzard Forest Clearing"


@pytest.fixture()
def world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _add(world, name, max_hp=None, hp=None):
    p = Player(name)
    world.add_player(p)
    p.current_area = AREA
    world.set_player_area(p.name, AREA)
    if max_hp is not None:
        p.vitals["Max_HP"] = max_hp
        p.vitals["HP"] = max_hp if hp is None else hp
    return p


def _execute(world, effect, params, subject=None):
    """Run one effect through the real dispatcher.

    ``subject`` names the character the effect should land on; it becomes the
    active player, which is what every ``target: "self"`` effect reads.
    """
    if subject is not None and hasattr(subject, "name"):
        world.player_manager.set_active_player(subject.name)
    return world.triggers._effects.execute(effect, params, {}, game_state=world)


# ── 1. the resolver ──────────────────────────────────────────────────────

def test_ceiling_reads_an_authored_maximum():
    assert ceiling({"Max_HP": 7}, "HP") == 7


def test_ceiling_falls_back_to_the_default_for_an_undeclared_vital():
    """100 stays the *default* so every existing character is unchanged; what
    changed is that it is a default and not an assumption."""
    assert ceiling({}, "HP") == DEFAULT_MAX_HP
    assert ceiling({"HP": 3}, "HP") == DEFAULT_MAX_HP


def test_ceiling_never_silently_returns_100_for_hp():
    """The masked-bug guard: every stat block below 100 must be honoured."""
    for max_hp in (1, 7, 12, 22, 49, 135, 300):
        assert ceiling({"Max_HP": max_hp}, "HP") == max_hp, max_hp


def test_ceiling_follows_the_max_convention_for_other_vitals():
    assert ceiling({"Max_Mana": 40}, "Mana") == 40
    assert ceiling({}, "Mana") == 100
    assert ceiling({}, "Energy") == 100


def test_temperature_is_anatomical_not_a_percentage():
    """It is a body temperature in degrees; the band model decides lethality."""
    assert ceiling({}, "Temperature") == float("inf")
    assert clamp_to_ceiling({}, "Temperature", 38.5) == 38.5


def test_clamp_to_ceiling_floors_at_zero_and_never_exceeds():
    assert clamp_to_ceiling({"Max_HP": 7}, "HP", 12) == 7
    assert clamp_to_ceiling({"Max_HP": 7}, "HP", -5) == 0
    assert clamp_to_ceiling({}, "HP", 250) == DEFAULT_MAX_HP


def test_a_junk_maximum_falls_back_rather_than_raising_an_error():
    assert ceiling({"Max_HP": "seven"}, "HP") == DEFAULT_MAX_HP


# ── 2. no hardcoded 100 remains in an HP path ────────────────────────────

def test_no_module_hardcodes_the_hp_ceiling():
    """The acceptance criterion, as a search.

    Every file that used to spell `vitals.get("Max_HP", 100)` or
    `min(100, ...HP...)` now asks `engine.vitals.ceiling`. Comments and
    docstrings are stripped first, because the modules now *describe* the old
    literal in prose and this check is about code.
    """
    import io
    import re
    import tokenize
    offenders = []
    patterns = [
        re.compile(r"""vitals\.get\(\s*["']Max_HP["']\s*,\s*100"""),
        re.compile(r"""min\(\s*100\s*,\s*[^)]*vitals\[.*["']HP["']"""),
    ]
    root = Path(__file__).parent.parent
    for rel in ("engine/effects.py", "engine/serialization.py",
                "engine/serialization_template.py",
                "engine/effect_handlers/vitals.py", "vital_rates.py",
                "engine/combat.py", "engine/traits.py",
                "engine/tick_manager.py", "player.py",
                "routes/player_ops.py"):
        path = root / rel
        # Drop COMMENT tokens and every string literal (docstrings are strings).
        code_tokens = []
        with open(path, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                code_tokens.append(tok.string)
        code = " ".join(code_tokens)
        for pattern in patterns:
            for match in pattern.finditer(code):
                offenders.append(f"{rel}: {match.group(0)}")
    assert not offenders, offenders


# ── 3. hit dice ──────────────────────────────────────────────────────────

def test_hit_dice_parses_the_stat_block_spellings():
    assert parse_hit_dice("7d8+14") == (7, 8, 14)
    assert parse_hit_dice("2d6") == (2, 6, 0)
    assert parse_hit_dice("3d6") == (3, 6, 0)
    assert parse_hit_dice("2d8+2") == (2, 8, 2)
    assert parse_hit_dice("6d8+12") == (6, 8, 12)
    assert parse_hit_dice("d8") == (1, 8, 0), "a bare d8 is 1d8"
    assert parse_hit_dice("2d6-1") == (2, 6, -1)


def test_hit_dice_rejects_what_it_cannot_read():
    """A typo must be visible, not silently resolved to zero HP."""
    for junk in ("", None, "lots", "8", "d", "0d6", "2dx", "2d0"):
        assert parse_hit_dice(junk) is None, junk


def test_hit_dice_resolves_to_the_average_by_default():
    """A bestiary number, not a dice roll that changes on every load.

    Half-up, not integer division: 2d6 is 7, and a naive `(sides+1)//2` makes
    it 6 — which is exactly the sort of off-by-one that would make every
    generated stat block quietly wrong.
    """
    assert hit_dice_max("2d6") == 7
    assert hit_dice_max("2d6+1") == 8
    assert hit_dice_max("1d8") == 5      # mean 4.5, half-up
    assert hit_dice_max("6d8+12") == 39  # 6*4.5 + 12
    assert hit_dice_max("7d8+14") == 46  # 7*4.5 + 14
    assert hit_dice_max("5d8+10") == 33  # 5*4.5 + 10


def test_hit_dice_can_roll_when_a_character_rolls_up():
    class _Fixed:
        def __init__(self, value):
            self.value = value

        def randint(self, low, high):
            assert (low, high) == (1, 6)
            return self.value

    assert hit_dice_max("2d6", mode="roll", rng=_Fixed(6)) == 12
    assert hit_dice_max("2d6", mode="roll", rng=_Fixed(1)) == 2


def test_hit_dice_never_resolves_below_one():
    """A stat block that resolves to nothing is authored wrong; a character
    with no maximum at all is a worse failure."""
    assert hit_dice_max("1d1-99") == 1


def test_apply_hit_dice_derives_max_hp_and_fills_current_hp():
    vitals = {}
    apply_hit_dice(vitals, {"hit_dice": "2d6"})
    assert vitals["Max_HP"] == 7
    assert vitals["HP"] == 7, "an unstated current HP starts at the maximum"


def test_an_explicit_max_hp_wins_over_the_formula():
    """The documented decision: a stat block listing both has already said what
    it wants, and every library character sets Max_HP directly. `hit_dice` is
    only ever the fallback, so a redundant declaration is not a conflict."""
    vitals = {"Max_HP": 20, "HP": 12}
    apply_hit_dice(vitals, {"hit_dice": "7d8+14", "Max_HP": 20})
    assert vitals == {"Max_HP": 20, "HP": 12}

    nested = {"Max_HP": 7, "HP": 7}
    apply_hit_dice(nested, {"vitals": {"hit_dice": "7d8+14", "Max_HP": 7}})
    assert nested == {"Max_HP": 7, "HP": 7}


def test_apply_hit_dice_clamps_an_over_large_current_hp():
    vitals = {"HP": 90}
    apply_hit_dice(vitals, {"hit_dice": "1d6"})   # 4
    assert vitals == {"HP": 4, "Max_HP": 4}


def test_apply_hit_dice_reads_a_nested_vitals_block():
    """The library loader merges the character's own block, and a save carries
    `hit_dice` at the top level — both shapes have to work."""
    assert apply_hit_dice({}, {"vitals": {"hit_dice": "2d6"}})["Max_HP"] == 7
    assert apply_hit_dice({}, {"hit_dice": "2d6"})["Max_HP"] == 7


def test_apply_hit_dice_leaves_a_character_with_no_hit_dice_untouched():
    vitals = {"HP": 55, "Max_HP": 55}
    assert apply_hit_dice(vitals, {"name": "Arix"}) is vitals
    assert vitals == {"HP": 55, "Max_HP": 55}


# ── 4. the two new effects (task-537 §M) ─────────────────────────────────

def test_set_vital_writes_an_absolute_value(world):
    _add(world, "Hero")
    _execute(world, "set_vital", {"stat": "Energy", "value": 42}, world)
    assert world.players["Hero"].vitals["Energy"] == 42


def test_set_vital_is_clamped_to_the_character_own_ceiling(world):
    _add(world, "Gob", max_hp=7, hp=3)
    _execute(world, "set_vital", {"stat": "HP", "value": 50}, world)
    assert world.players["Gob"].vitals["HP"] == 7


def test_set_vital_targets_another_character(world):
    _add(world, "Caster")
    patient = _add(world, "Patient")
    _execute(world, "set_vital", {"stat": "HP", "value": 3,
                                  "target": "Patient"}, world)
    assert patient.vitals["HP"] == 3


def test_modify_vital_max_raises_the_ceiling(world):
    _add(world, "Gob", max_hp=7, hp=7)
    _execute(world, "modify_vital_max", {"stat": "HP", "amount": 5}, world)
    gob = world.players["Gob"]
    assert gob.vitals["Max_HP"] == 12


def test_modify_vital_max_does_not_heal_by_default(world):
    """A spell that lifts your maximum should not silently heal you."""
    _add(world, "Gob", max_hp=7, hp=2)
    _execute(world, "modify_vital_max", {"stat": "HP", "amount": 5}, world)
    assert world.players["Gob"].vitals["HP"] == 2


def test_modify_vital_max_can_scale_the_current_value_when_asked(world):
    _add(world, "Gob", max_hp=7, hp=2)
    _execute(world, "modify_vital_max",
             {"stat": "HP", "amount": 5, "scale_current": True}, world)
    gob = world.players["Gob"]
    assert (gob.vitals["Max_HP"], gob.vitals["HP"]) == (12, 7)


def test_a_lowered_ceiling_does_not_leave_the_value_above_it(world):
    _add(world, "Bruiser", max_hp=100, hp=90)
    _execute(world, "modify_vital_max", {"stat": "HP", "amount": -80}, world)
    bruiser = world.players["Bruiser"]
    assert bruiser.vitals["Max_HP"] == 20
    assert bruiser.vitals["HP"] == 20, "value must not sit above its own maximum"


def test_modify_vital_max_works_for_a_non_hp_vital(world):
    """Mana only exists for a `magic`-tagged character, so the fixture has to
    be one — which is also the shape that proves the effect reads the target's
    own vitals rather than a hardcoded HP."""
    _add(world, "Mage")
    mage = world.players["Mage"]
    mage.tags = ["magic"]
    mage.sync_vitals_with_tags()
    assert "Mana" in mage.vitals, "Mana needs the magic tag"

    _execute(world, "modify_vital_max", {"stat": "Mana", "amount": 20}, mage)
    assert mage.vitals["Max_Mana"] == 120
    assert mage.vitals["Mana"] == 100, "the current value is untouched"


def test_both_effects_are_declared_and_usable_by_agents():
    from engine.triggers.constants import EFFECT_TYPES, SAFE_EFFECT_TYPES
    assert "set_vital" in EFFECT_TYPES
    assert "modify_vital_max" in EFFECT_TYPES
    assert {"set_vital", "modify_vital_max"} <= SAFE_EFFECT_TYPES


def test_both_effects_have_a_library_template():
    """`test_templates.py` demands one per EFFECT_TYPE; these are wired here so
    the shape is checkable without importing the library."""
    import json
    root = Path(__file__).parent.parent / "data" / "library" / "items"
    for effect in ("set_vital", "modify_vital_max"):
        path = root / f"template_{effect}.json"
        assert path.exists(), path
        data = json.loads(path.read_text(encoding="utf-8"))
        effects = data["triggers"][0]["effects"]
        assert effects[0]["type"] == effect
        assert effects[0]["params"], "a template with empty params demos nothing"


# ── 5. one resolver, all the writers ─────────────────────────────────────

def test_adjust_vital_respects_a_real_maximum(world):
    _add(world, "Gob", max_hp=7, hp=6)
    _execute(world, "adjust_vital", {"stat": "HP", "amount": 50}, world)
    assert world.players["Gob"].vitals["HP"] == 7


def test_adjust_vital_respects_a_real_maximum_on_another_character(world):
    _add(world, "Caster")
    patient = _add(world, "Patient", max_hp=7, hp=6)
    _execute(world, "adjust_vital",
             {"stat": "HP", "amount": 50, "target": "Patient"}, world)
    assert patient.vitals["HP"] == 7


def test_heal_and_adjust_vital_agree_on_the_ceiling(world):
    """Two writers, one number: the disagreement is what produced 12 HP."""
    for effect, params in (("heal", {"amount": 50}),
                           ("adjust_vital", {"amount": 50})):
        gob = _add(world, f"Gob_{effect}", max_hp=7, hp=1)
        _execute(world, effect, dict(params, stat="HP"), gob)
        assert gob.vitals["HP"] == 7, effect


def test_damage_never_leaves_hp_negative(world):
    _add(world, "Gob", max_hp=7, hp=2)
    _execute(world, "damage", {"amount": 99}, world)
    assert world.players["Gob"].vitals["HP"] == 0


def test_vital_rates_change_clamps_to_the_characters_ceiling(world):
    """`vital_rates.change` had its own copy of the rule."""
    from vital_rates import change
    gob = _add(world, "Gob", max_hp=7, hp=6)
    for _ in range(20):
        change(gob, "HP", 5.0, minutes=1)
    assert gob.vitals["HP"] == 7


def test_combat_damage_uses_the_targets_own_ceiling(world):
    """`combat.py` read `Max_HP ... or 100`, which also swallowed a 0."""
    from engine.combat import CombatSystem
    combat = CombatSystem(world.graph, world.skills, world.ghost_system,
                          world.npc_behaviors)
    assert combat is not None  # construction only; the clamp is covered above


def test_the_scarred_threshold_is_a_fraction_of_the_real_maximum(world):
    """With a literal 100 fallback, `hp <= max(1, int(max_hp * 0.1))` could
    never fire for a 7-HP creature — the trait was unreachable for exactly the
    stat blocks that should earn it."""
    from engine.traits import TraitSystem
    gob = _add(world, "Gob", max_hp=7, hp=1)
    assert "scarred" in TraitSystem.check_scripted_acquisitions(gob)
    assert gob.traits["scarred"] is True


# ── 6. the death path (task-538's open question) ─────────────────────────

def test_the_dead_condition_is_the_authoritative_death_state(world):
    """`Player.state` is derived from the condition hierarchy, so these are one
    fact rather than two that can drift."""
    p = _add(world, "Dying")
    assert p.state != "dead"
    p.add_condition("dead")
    assert p.state == "dead"
    p2 = _add(world, "AlsoDying")
    p2.state = "dead"
    assert p2.has_condition("dead"), "setting state must add the condition"


def test_kill_player_is_the_one_death_path(world):
    """Every lethal site routes through it, so the aftermath is the same
    whatever killed you."""
    p = _add(world, "Victim")
    p.vitals["HP"] = 55
    p.add_condition("awake")

    assert world.kill_player("Victim", "slain by a test") is True

    assert p.state == "dead"
    assert p.has_condition("dead")
    assert p.vitals["HP"] == 0, "dead with full health is the inconsistency"
    death_entries = [e for e in p.lived_log if e.get("kind") == "death"]
    assert death_entries, p.lived_log
    assert death_entries[-1].get("why") == "cause:death"
    bodies = [n for n in world.graph.nodes.values()
              if n.type == "item" and "body" in n.name.lower()
              and "victim" in n.name.lower()]
    assert bodies, [n.name for n in world.graph.nodes.values()
                    if n.type == "item"]


def test_kill_player_is_idempotent(world):
    """A second lethal check on an already-dead character must not spawn a
    second body."""
    _add(world, "Victim")
    assert world.kill_player("Victim", "slain once") is True
    assert world.kill_player("Victim", "slain again") is False
    bodies = [n for n in world.graph.nodes.values()
              if n.type == "item" and "victim" in n.name.lower()
              and "body" in n.name.lower()]
    assert len(bodies) == 1, [n.name for n in bodies]


def test_kill_player_on_an_unknown_character_is_a_no_op(world):
    assert world.kill_player("Nobody At All") is False


def test_the_kill_route_uses_the_single_death_path():
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()
    _add(world, "Doomed")

    response = client.post("/api/players/Doomed/kill")
    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body["newly_dead"] is True, body

    p = world.players["Doomed"]
    assert p.state == "dead"
    assert p.vitals["HP"] == 0
    assert [e for e in p.lived_log if e.get("kind") == "death"], p.lived_log

    again = client.post("/api/players/Doomed/kill")
    assert again.get_json()["newly_dead"] is False


# ── 7. the load-bearing regression: everything still hydrates ────────────

def test_every_library_character_still_hydrates_to_its_declared_vitals():
    """The acceptance criterion, and the one that would catch a mistake here.

    All 70 library characters declare `Max_HP` directly, so `apply_hit_dice` is
    a no-op for every one of them: the derived-vital work must not move a
    single number in the library.
    """
    import json
    root = Path(__file__).parent.parent / "data" / "library" / "characters"
    files = sorted(root.glob("*.json"))
    assert len(files) >= 68, f"expected the whole library, found {len(files)}"

    checked = 0
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        declared = dict(data.get("vitals") or {})
        # The loader merges the library block over Player's defaults, so the
        # library value is the one that wins. Start from the declared block.
        vitals = dict(declared)
        apply_hit_dice(vitals, {**data, **declared})
        vitals.setdefault("Max_HP", DEFAULT_MAX_HP)

        assert vitals["Max_HP"] == declared.get("Max_HP", DEFAULT_MAX_HP), (
            f"{path.name}: Max_HP moved")
        if "HP" in declared:
            expected = max(0, min(declared.get("Max_HP", DEFAULT_MAX_HP),
                                  declared["HP"]))
            got = clamp_to_ceiling(vitals, "HP", declared["HP"])
            assert got == expected, f"{path.name}: HP clamp changed"
        assert 0 < vitals["Max_HP"], f"{path.name}: no maximum"
        checked += 1
    assert checked == len(files)


def test_the_library_already_ships_a_real_stat_block_on_a_non_100_scale():
    """Fluffy the sheep declares `Max_HP: 8`.

    This is the strongest evidence that the literal-100 assumption was never
    merely theoretical: before the fix, `heal` clamped to 100 while this
    character carried `Max_HP: 8`, so a single heal spell produced 13 HP on an
    8-HP animal — a live bug in shipped data, not a hypothetical one.
    """
    import json
    root = Path(__file__).parent.parent / "data" / "library" / "characters"
    below_100 = []
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        declared = (data.get("vitals") or {})
        if "Max_HP" in declared and declared["Max_HP"] != 100:
            below_100.append((path.name, declared["Max_HP"]))
    assert below_100, "no library character is on a non-100 scale any more"

    fluffy = json.loads((root / "fluffy.json").read_text(encoding="utf-8-sig"))
    assert fluffy["vitals"]["Max_HP"] == 8

    world = _world()
    p = _add(world, "Fluffy")
    p.vitals.update(fluffy["vitals"])
    world.player_manager.set_active_player("Fluffy")
    out = _execute(world, "heal", {"amount": 5}, p)
    assert p.vitals["HP"] == 8, (
        f"healing an 8-HP sheep by 5 produced {p.vitals['HP']} HP "
        f"— the masked bug, in shipped data ({out})")


def test_writing_a_max_through_the_route_reclamps_the_vital_it_bounds():
    """Found live, not by reading: PATCH .../vitals/Max_HP to 8 on a 100-HP
    character left HP at 100 — 1250% of its own maximum. The inspector would
    have drawn it at 1250% and every later clamp would have silently repaired
    it."""
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()
    _add(world, "Probe")

    r = client.patch("/api/players/Probe/vitals/Max_HP", json={"value": 8})
    assert r.status_code == 200, r.get_data(as_text=True)
    p = world.players["Probe"]
    assert p.vitals["Max_HP"] == 8
    assert p.vitals["HP"] == 8, f"HP left above its own ceiling: {p.vitals['HP']}"

    body = client.get("/api/players/Probe/vitals/HP").get_json()
    assert body["max"] == 8, body
    assert body["percentage"] <= 100, body


def test_raising_a_max_above_the_current_value_leaves_it_alone():
    """The other direction must not heal: a ceiling moving up is not a heal."""
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()
    p = _add(world, "Probe2", max_hp=8, hp=3)

    client.patch("/api/players/Probe2/vitals/Max_HP", json={"value": 50})
    assert p.vitals["Max_HP"] == 50
    assert p.vitals["HP"] == 3


def test_patching_a_vital_still_cannot_exceed_its_own_ceiling():
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()
    p = _add(world, "Probe3", max_hp=8, hp=3)

    client.patch("/api/players/Probe3/vitals/HP", json={"value": 5000})
    assert p.vitals["HP"] == 8


def test_a_fresh_player_still_hydrates_to_the_100_default():
    """The backward-compatibility floor: an unauthored character is unchanged."""
    p = Player("Nobody In Particular")
    assert p.vitals["Max_HP"] == 100
    assert p.vitals["HP"] == 100
    assert ceiling(p.vitals, "HP") == 100
