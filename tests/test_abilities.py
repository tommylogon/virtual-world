"""task-606: scale-correct ability scores per size tier.

The engine had one number for ability scores — whatever a stat block said, and
for a character with no stat block, 10 — while the six size tiers had nothing to
say about strength. The task's own phrase was "a leviathan is not STR 9", and
the honest half of that turned out to be: several library characters were not
STR 9, they were **no** STR at all.

These tests pin:

1. the curve, as reference points plus a tolerance (not exclusive boxes, which
   would flag every wolf in the `small` category);
2. the two stat-key vocabularies the library really had, folded into one;
3. the library itself — no character contradicts its own size any more, and no
   character's authored number was lost along the way.
"""
import json
import sys
from pathlib import Path

import inspect

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.abilities import (
    ABILITIES, MASS_SCALED_ABILITIES, PLAUSIBLE_MAX, PLAUSIBLE_MIN,
    SIZE_TIER_DEFAULTS, SIZE_TIER_REFERENCE, TOLERANCE, ability_range,
    describe_curve, is_inanimate, is_scale_correct, normalize_stat_block,
    scale_issues, stats_for_size, tolerance_band,
)
from engine.size import SIZE_TIERS
from player import Player

CHARACTERS = Path(__file__).parent.parent / "data" / "library" / "characters"


@pytest.fixture()
def world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _library():
    return sorted(CHARACTERS.glob("*.json"))


# ── the curve ────────────────────────────────────────────────────────────

def test_every_size_tier_has_a_reference():
    """5e's canonical blocks match the existing six tiers, which is what makes
    the tier the spine and the values inside it the authoring surface."""
    assert set(SIZE_TIER_REFERENCE) == set(SIZE_TIERS)


def test_the_reference_is_the_decided_5e_table():
    """Tommy's decided baseline, verbatim. A test rather than a comment because a
    table in a comment is a table nobody reads."""
    assert SIZE_TIER_REFERENCE["tiny"]["STR"] == (2, 3)        # Rat, Sprite
    assert SIZE_TIER_REFERENCE["small"]["STR"] == (8, 8)       # Goblin
    assert SIZE_TIER_REFERENCE["normal"]["STR"] == (10, 13)    # Human commoner
    assert SIZE_TIER_REFERENCE["huge"]["STR"] == (18, 19)      # Ogre, Troll
    assert SIZE_TIER_REFERENCE["giant"]["STR"] == (21, 23)     # Hill Giant
    assert SIZE_TIER_REFERENCE["titanic"]["STR"] == (27, 45)    # Dragon / Tarrasque


def test_only_str_and_con_scale_with_mass():
    """The mental abilities have nothing to do with how much of you there is, and
    pretending otherwise is how a leviathan ends up INT 3."""
    assert MASS_SCALED_ABILITIES == ("STR", "CON")
    assert ability_range("titanic", "INT") is None
    assert tolerance_band("titanic", "WIS") is None


def test_the_tolerance_is_what_makes_the_curve_usable():
    """A tier is a bucket, and 5e's `small` contains both a goblin (STR 8) and an
    imp. An exclusive box would flag every wolf in it."""
    band = tolerance_band("small", "STR")
    low, high = SIZE_TIER_REFERENCE["small"]["STR"]
    assert band == (low / TOLERANCE, high * TOLERANCE)


def test_a_leviathan_at_str_9_is_reported():
    """The task's own sentence, as an assertion."""
    issues = scale_issues({"STR": 9, "CON": 9}, "titanic")
    assert any("STR" in i for i in issues), issues
    assert is_scale_correct({"STR": 9, "CON": 9}, "titanic") is False


def test_the_real_5e_blocks_are_all_consistent_with_their_own_tier():
    """Nothing the curve ships with may fail its own check.

    Each ability is tested against its OWN reference, not against a single
    shared number — the first version of this test set `CON = STR` and then
    complained that a rat's CON 2 was wrong, which it is not for a rat.
    """
    for tier, reference in SIZE_TIER_REFERENCE.items():
        block = {"STR": reference["STR"][0], "CON": reference["CON"][0]}
        assert scale_issues(block, tier) == [], f"{tier} lows {block}"
        block = {"STR": reference["STR"][1], "CON": reference["CON"][1]}
        assert scale_issues(block, tier) == [], f"{tier} highs {block}"


def test_an_unauthored_size_is_never_a_finding():
    """A character with no size is a person, and a person with STR 9 is a weedy
    person. Absence is not a defect."""
    assert scale_issues({"STR": 9, "CON": 9}, None) == []
    assert scale_issues({"STR": 9, "CON": 9}, "") == []


def test_an_impossible_score_is_reported_regardless_of_size():
    for bad in (0, -5, PLAUSIBLE_MAX + 1):
        assert scale_issues({"STR": bad}, "normal"), bad
    assert PLAUSIBLE_MIN == 1


def test_a_non_numeric_ability_is_reported_rather_than_crashing():
    issues = scale_issues({"STR": "very strong"}, "normal")
    assert any("not a number" in i for i in issues), issues


def test_a_creature_with_no_stat_block_at_all_is_reported():
    """Half of the task's complaint: worse than STR 9 is no STR."""
    assert any("no STR or CON" in i for i in scale_issues({}, "small"))
    assert any("no STR or CON" in i for i in scale_issues({"CHA": 8}, "small"))


def test_an_unknown_size_is_reported_once():
    issues = scale_issues({"STR": 10, "CON": 10}, "colossal-but-not-a-tier")
    assert any("not one of" in i for i in issues), issues


# ── inanimate things are not judged by a curve about bodies ─────────────

def test_a_training_dummy_is_not_judged_against_the_curve():
    """`Straw Practice Dummy` is `giant` with STR 1 **on purpose**: the whole
    point of it is that it cannot fight back. Reporting that as a defect is a
    flag nobody can act on."""
    dummy = Player("Straw Practice Dummy")
    dummy.size = "giant"
    dummy.stats = {"STR": 1, "DEX": 1, "CON": 20, "INT": 1, "WIS": 1, "CHA": 1}
    dummy.tags = ["training", "dummy", "straw", "practice", "inanimate"]
    assert is_inanimate(dummy) is True
    assert scale_issues(entity=dummy) == []


def test_a_creature_is_still_judged():
    assert is_inanimate(Player("Ogre")) is False
    assert scale_issues({"STR": 1, "CON": 1}, "giant") != []


# ── stats_for_size ───────────────────────────────────────────────────────

def test_stats_for_size_gives_a_complete_block_per_tier():
    for tier in SIZE_TIERS:
        block = stats_for_size(tier)
        assert set(block) == set(ABILITIES), tier
        assert all(isinstance(v, int) for v in block.values()), tier


def test_strength_and_constitution_rise_with_size():
    strengths = [stats_for_size(t)["STR"] for t in
                 ("tiny", "small", "normal", "huge", "giant", "titanic")]
    assert strengths == sorted(strengths), strengths


def test_an_unknown_size_is_a_person():
    assert stats_for_size("colossal") == stats_for_size("normal")
    assert stats_for_size(None) == stats_for_size("normal")


def test_overrides_apply_last_and_only_where_the_ability_exists():
    block = stats_for_size("huge", overrides={"CON": 20, "NOPE": 99})
    assert block["CON"] == 20
    assert "NOPE" not in block


def test_the_derived_block_satisfies_its_own_curve():
    for tier in SIZE_TIERS:
        assert scale_issues(stats_for_size(tier), tier) == [], tier


def test_describe_curve_renders_the_same_table_it_enforces():
    curve = describe_curve()
    for tier, entry in curve.items():
        assert entry["abilities"] == dict(SIZE_TIER_REFERENCE[tier])
        assert entry["example"] == dict(SIZE_TIER_DEFAULTS[tier])
        assert tuple(entry["tolerated"]["STR"]) == tolerance_band(tier, "STR")


# ── the two vocabularies the library actually had ───────────────────────

def test_a_lowercase_stat_block_becomes_readable():
    """`the butcher` was authored `str: 18` and fought at STR 10."""
    out = normalize_stat_block({"str": 18, "cha": 4, "dex": 14,
                                "int": 6, "con": 20, "wis": 10})
    assert out["STR"] == 18
    assert out["CON"] == 20
    assert out["CHA"] == 4


def test_non_ability_keys_survive():
    """A normaliser, not a filter."""
    out = normalize_stat_block({"STR": 11, "attack_bonus": 3, "spell_save": "dc"})
    assert out["attack_bonus"] == 3
    assert out["spell_save"] == "dc"


def test_a_canonical_key_beats_a_lowercase_one():
    out = normalize_stat_block({"STR": 11, "str": 99})
    assert out["STR"] == 11
    assert "str" not in out, "the two spellings of one fact must not both survive"


def test_normalising_is_idempotent():
    once = normalize_stat_block({"str": 18, "attack_bonus": 3})
    assert normalize_stat_block(once) == once


def test_junk_is_an_empty_block_not_a_crash():
    assert normalize_stat_block(None) == {}
    assert normalize_stat_block("STR 18") == {}
    assert normalize_stat_block([]) == {}


def test_every_stat_writer_folds_the_case():
    """The normaliser has to be at every writer, and a normaliser that has to be
    remembered in six places is a normaliser that will be missed in the seventh.
    """
    import engine.effects as effects_module
    import engine.serialization as serialization
    import routes.library_ops as library_ops
    import routes.player_ops as player_ops

    for module in (effects_module, serialization, library_ops, player_ops):
        source = inspect.getsource(module)
        assert "normalize_stat_block" in source, (
            f"{module.__name__} assigns player.stats without folding the case")

    # And it is the same function everywhere, not four copies of it.
    assert effects_module.normalize_stat_block is normalize_stat_block
    assert serialization.normalize_stat_block is normalize_stat_block


def test_the_library_loader_folds_a_lowercase_block():
    """The wiring: the loader is where a stat block actually reaches a Player."""
    folded = normalize_stat_block({"str": 18, "con": 20})
    assert folded["STR"] == 18
    assert folded["CON"] == 20


# ── the library itself ───────────────────────────────────────────────────

def test_no_library_character_contradicts_its_own_size():
    """The load-bearing assertion, over all 70 files."""
    offenders = []
    for path in _library():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        stats = normalize_stat_block(data.get("stats"))
        issues = scale_issues(stats, data.get("size"), entity=data)
        if issues:
            offenders.append(f"{path.name}: {'; '.join(issues)}")
    assert not offenders, offenders


def test_every_library_character_that_states_a_size_is_scale_sane():
    """A size with nothing at all attached is the failure this task is about."""
    for path in _library():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not data.get("size"):
            continue
        stats = normalize_stat_block(data.get("stats"))
        assert "STR" in stats or is_inanimate(data), (
            f"{path.name} is {data['size']} with no STR and is not inanimate")


def test_no_authored_number_was_lost():
    """The authoring pass rewrote 67 files; none of their numbers may have moved.

    Checked against the values in git rather than a hand-written list, because a
    hand-written list is exactly what goes stale.
    """
    import subprocess

    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--",
         "data/library/characters/"],
        capture_output=True, text=True).stdout.split()
    if not changed:
        pytest.skip("no library diff in this checkout to compare against")
    for path in changed:
        original = subprocess.run(["git", "show", f"HEAD:{path}"],
                                  capture_output=True)
        if original.returncode != 0:
            continue
        before = normalize_stat_block(
            json.loads(original.stdout.decode("utf-8-sig")).get("stats"))
        after = normalize_stat_block(
            json.loads(Path(path).read_text(encoding="utf-8-sig")).get("stats"))
        for ability, value in before.items():
            if ability in ABILITIES:
                assert after.get(ability) == value, (
                    f"{path.name}: {ability} was {value}, now "
                    f"{after.get(ability)}")


def test_the_library_now_has_authored_sizes():
    """task-606's premise: the gap was authored data, and one file out of 70 had
    a size on it."""
    sizes = {}
    for path in _library():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("size"):
            sizes[data["size"]] = sizes.get(data["size"], 0) + 1
    assert len(sizes) >= 4, f"expected several tiers, got {sizes}"
    assert sum(sizes.values()) >= 60, f"only {sum(sizes.values())} sized"


def test_every_library_stat_block_uses_the_canonical_spelling():
    """One spelling of one fact, so a reader never has to guess."""
    for path in _library():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for key in (data.get("stats") or {}):
            assert str(key) not in {"str", "dex", "con", "int", "wis", "cha"}, \
                f"{path.name} still spells an ability as {key!r}"


# ── the wiring: the author is told, and can read the curve ──────────────

def test_the_curve_is_readable_over_the_api():
    from app import create_app
    client = create_app({"TESTING": True}).test_client()

    body = client.get("/api/abilities/curve").get_json()
    assert set(body["curve"]) == set(SIZE_TIERS)
    assert body["tiers"] == list(SIZE_TIERS)
    for tier in SIZE_TIERS:
        assert body["defaults"][tier]["STR"] == SIZE_TIER_DEFAULTS[tier]["STR"]
        # JSON has no tuples, so the reference arrives as a list.
        assert body["curve"][tier]["abilities"]["CON"] == list(
            SIZE_TIER_REFERENCE[tier]["CON"])


def test_writing_a_leviathan_at_str_9_is_reported_not_refused():
    """The task's own sentence, through the authoring API.

    Stored, because a leviathan at STR 9 was always storable and refusing the
    write would be a new rule; reported, because that is the whole value of a
    curve with no clamp.
    """
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    from player import Player as _Player
    p = _Player("Test Leviathan")
    app.world.add_player(p)

    body = client.post("/api/players/Test Leviathan", json={
        "size": "titanic", "stats": {"STR": 9, "CON": 9, "DEX": 10,
                                     "INT": 15, "WIS": 11, "CHA": 13},
    }).get_json()
    assert body["status"] == "updated"
    assert any("STR" in w for w in body.get("scale_warnings", [])), body
    assert app.world.players["Test Leviathan"].vitals["Max_HP"], \
        "a refused write would have lost the character"


def test_a_scale_sane_block_reports_no_warnings():
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    from player import Player as _Player
    app.world.add_player(_Player("Test Ogre"))

    body = client.post("/api/players/Test Ogre", json={
        "size": "huge", "stats": {"STR": 19, "CON": 15, "DEX": 8,
                                  "INT": 6, "WIS": 7, "CHA": 7},
    }).get_json()
    assert "scale_warnings" not in body, body


def test_a_written_stat_block_is_folded_however_it_was_spelled():
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    from player import Player as _Player
    app.world.add_player(_Player("Test Butcher"))

    client.post("/api/players/Test Butcher",
                json={"stats": {"str": 18, "con": 20, "attack_bonus": 3}})
    stats = app.world.players["Test Butcher"].stats
    assert stats["STR"] == 18, stats
    assert stats["CON"] == 20, stats
    assert stats["attack_bonus"] == 3, "not a filter"
