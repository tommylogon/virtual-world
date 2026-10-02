"""task-652: one emotional model — the affect map is the state, and everything
that should move a feeling moves it.

The model was already good and widely written to: eleven systems write the affect
map, `frightened` reaches it, the LLM's declared feeling has a route. What was
missing was the other two halves of the task's own goal, and both were provable
without guessing:

1. **A declared feeling was normalised two different ways.** The route used
   `map_label`, which substring-matches — so an LLM saying "hangry" became
   "angry" on a coincidence, which is precisely what task-505 was filed to
   prevent. Meanwhile `felt_from_llm` — the strict normaliser, with no
   production caller — consulted only `BASELINES` and so dropped every alias the
   module declares: `terrified`, `furious`, `tired`.

2. **The feeling never caused behaviour.** `background_social.py` writes
   emotions (`TIER_EMOTION`, `TIER_TARGET_EMOTION`, `FEAR_COSTS`) and reads
   none. Exactly one reader existed anywhere in the engine (`derive.py`, for
   consent). A character who had just been frightened drew from the identical
   table as one who had just been complimented.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import emotion as emotion_engine
from engine.background_social import (
    AFFECT_AFFINITY, AFFECT_FELT_THRESHOLD, AFFECT_TILT, action_weights,
    felt_axes,
)
from engine.emotion import LABEL_TO_DIM, raised_axes
from player import Player


# ── 1. one normaliser for a declared feeling ────────────────────────────

def test_a_declared_alias_is_not_dropped():
    """`terrified`, `furious` and `tired` are declared in `LABEL_TO_DIM` and
    `set_emotion` accepted them all. The LLM path rejected them."""
    for label, expected in (("terrified", "afraid"), ("furious", "angry"),
                            ("tired", "melancholic"), ("panic", "afraid"),
                            ("down", "sad"), ("mad", "angry")):
        felt = emotion_engine.felt_from_llm({"label": label, "intensity": 6})
        assert felt is not None, f"{label} was dropped"
        assert felt[0] == expected, f"{label} -> {felt[0]}, expected {expected}"


def test_every_alias_in_the_table_resolves():
    """A declared alias that cannot be resolved is a hole in the authored
    vocabulary, and there were eleven of them."""
    unresolvable = []
    for label in LABEL_TO_DIM:
        felt = emotion_engine.felt_from_llm({"label": label, "intensity": 5})
        if felt is None:
            unresolvable.append(label)
    assert not unresolvable, unresolvable


def test_the_eleven_axis_names_are_authored_not_inherited():
    """`map_label` resolved "sadness" and "anger" only by inverting the
    *expression* table, which is a different concern that happens to share eleven
    names. Those names belong next to `terrified`."""
    for axis in emotion_engine.AXIS_TO_EXPRESSION:
        assert axis in LABEL_TO_DIM, (
            f"{axis!r} resolves only by falling out of AXIS_TO_EXPRESSION")
        felt = emotion_engine.felt_from_llm({"label": axis, "intensity": 5})
        assert felt is not None, axis


def test_a_coincidental_substring_does_not_resolve():
    """The reason task-505 exists. "hangry" contains "angry"; a deliberate act by
    a model is not a typo."""
    assert emotion_engine.felt_from_llm({"label": "hangry", "intensity": 8}) is None


def test_invented_words_are_still_ignored_rather_than_snapped_to_the_nearest():
    """An LLM cannot invent a dimension."""
    for junk in ("snarfleblot", "qwertyuiop", "elevenish"):
        assert emotion_engine.felt_from_llm({"label": junk, "intensity": 9}) is None


def test_the_route_uses_the_strict_normaliser():
    """The wiring. `handle_spike_emotion` used `map_label`, so the loose path
    was live and the strict one was dead."""
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    world = app.world
    world.add_player(Player("Route Probe"))

    # A declared alias the old loose path would also have caught: proves the
    # route is still working, not dead.
    ok = client.post("/api/players/Route Probe/emotions",
                     json={"emotion": "terrified", "intensity": 8,
                           "delta": 40}).get_json()
    assert "ignored" not in ok, ok
    assert world.players["Route Probe"].emotions_map().get("afraid", 0) > 0, ok

    # And the coincidence the strict path refuses: "hangry" must be ignored
    # rather than read as "angry".
    before = dict(world.players["Route Probe"].emotions_map())
    ignored = client.post("/api/players/Route Probe/emotions",
                          json={"emotion": "hangry", "intensity": 8,
                                "delta": 40}).get_json()
    assert ignored.get("ignored") == "hangry", ignored
    assert world.players["Route Probe"].emotions_map()["angry"] == \
        before.get("angry", emotion_engine.BASELINES.get("angry", 0.0)), \
        "a coincidental substring moved the affect map"


# ── 2. the affect map is the state, and it is readable as such ───────────

def test_raised_axes_reports_what_is_actually_felt():
    """Only movement above resting. A baseline that happens to sit above zero must
    not make a character permanently feel it."""
    p = Player("Resting")
    assert raised_axes(p.emotions_map()) == {}

    p.spike_emotion("angry", 60)
    assert raised_axes(p.emotions_map()) == {"angry": 60.0}


def test_raised_axes_agrees_with_the_label_threshold():
    """The label the reader sees and the axes behaviour reads must not disagree
    about which feeling is leading."""
    for label, amount in (("afraid", 80), ("grateful", 40), ("sad", 25)):
        p = Player("Probe")
        p.spike_emotion(label, amount)
        axes = raised_axes(p.emotions_map())
        leading = emotion_engine.dominant_dimension(p.emotions_map())
        if leading:
            assert leading in axes, (
                f"the label says {leading} leads but raised_axes omits it")


def test_a_saved_emotion_map_survives_and_is_readable_after_load():
    from player import Player as _Player
    p = _Player("Persist")
    p.spike_emotion("grateful", 40)
    saved = p.to_dict()
    assert saved["emotions"]["grateful"] > emotion_engine.BASELINES["grateful"]
    assert saved["emotion"]["current"], "the legacy view still reads"


# ── 3. the feeling steers behaviour ──────────────────────────────────────

def _weights(actor, target=None):
    return action_weights(actor, target or Player("Target"))


def test_an_at_rest_character_draws_the_baseline_table():
    """The change must be invisible when nobody is feeling anything."""
    w = _weights(Player("Calm"))
    assert round(w["bully"], 2) == 3.6, w


def test_anger_tilts_the_draw_toward_bullying():
    angry = Player("Angry")
    angry.spike_emotion("angry", 60)
    base = _weights(Player("Calm"))["bully"]
    assert _weights(angry)["bully"] == pytest.approx(base * AFFECT_TILT), (
        "a frightened-and-furious character draws the identical table as a calm one")


def test_gratitude_tilts_the_draw_toward_complimenting():
    grateful = Player("Grateful")
    grateful.spike_emotion("grateful", 60)
    base = _weights(Player("Calm"))["compliment"]
    assert _weights(grateful)["compliment"] == pytest.approx(base * AFFECT_TILT)


def test_fear_tilts_the_draw_toward_confiding_or_apologising():
    scared = Player("Scared")
    scared.spike_emotion("afraid", 60)
    base = _weights(Player("Calm"))["apologise"]
    assert _weights(scared)["apologise"] == pytest.approx(base * AFFECT_TILT)


def test_the_strongest_matching_axis_decides_not_the_union():
    """A character who is 20 angry and 60 afraid must not get both effects
    applied at full strength."""
    mixed = Player("Mixed")
    mixed.spike_emotion("angry", 20)
    mixed.spike_emotion("afraid", 60)
    weights = _weights(mixed)
    calm = _weights(Player("Calm"))
    # `bully` matches only `angry` at 20 -> a much smaller tilt than 1.6.
    bully_tilt = weights["bully"] / calm["bully"]
    assert bully_tilt < AFFECT_TILT, bully_tilt
    # `apologise` matches `afraid` at 60 -> the full tilt.
    assert weights["apologise"] / calm["apologise"] == pytest.approx(AFFECT_TILT)


def test_a_feeling_never_opens_a_gated_action():
    """The constraint that keeps this readable: a feeling re-weights what is on
    offer, it never opens something the relationship band forbids. A frightened
    character does not become willing to flirt with a stranger."""
    for label, amount in (("sad", 80), ("eager", 80), ("craving", 80),
                          ("grateful", 80)):
        actor = Player("Keen")
        actor.spike_emotion(label, amount)
        weights = _weights(actor, Player("Stranger"))
        assert weights.get("confide", 0.0) == 0.0, label
        assert weights.get("flirt", 0.0) == 0.0, label


def test_a_barely_felt_axis_does_not_tilt_anything():
    """Below the threshold the tilt is noise, so it is not applied."""
    faint = Player("Faint")
    faint.spike_emotion("angry", AFFECT_FELT_THRESHOLD - 5)
    assert felt_axes(faint) == {}
    assert _weights(faint)["bully"] == pytest.approx(
        _weights(Player("Calm"))["bully"])


def test_every_affinity_names_a_real_dimension():
    """An affinity pointing at a dimension that does not exist is a rule that can
    never fire, which is how a behaviour modifier rots."""
    for action, axes in AFFECT_AFFINITY.items():
        for axis in axes:
            assert axis in emotion_engine.BASELINES, f"{action}: {axis}"


def test_every_action_declares_its_affinity():
    """Including `chat`, which expresses nothing — an explicit empty tuple is a
    statement, an absent key is an oversight."""
    from engine.background_social import ACTIONS
    assert set(AFFECT_AFFINITY) == set(ACTIONS), (
        set(ACTIONS) - set(AFFECT_AFFINITY))


def test_the_whole_social_table_is_reachable_through_feelings():
    """Not every action needs an affinity, but every axis named must be one a
    character can actually reach."""
    reachable = set()
    for axes in AFFECT_AFFINITY.values():
        reachable.update(axes)
    assert reachable <= set(emotion_engine.BASELINES)


def test_felt_axes_tolerates_a_thing_with_no_emotions_map():
    """The social layer runs against fakes and partial objects in tests and in
    the approach path; it must not raise."""
    assert felt_axes(object()) == {}
    assert felt_axes(None) == {}


# ── emergence: the tilt changes what actually gets drawn ─────────────────

def _draw_counts(spikes, target=None, n=4000):
    """Draw `n` actions from the real chooser and count them."""
    from collections import Counter

    from engine.background_social import choose_action

    actor = Player("Drawer")
    for dim, amount in (spikes or {}).items():
        actor.spike_emotion(dim, amount)
    counts = Counter()
    for tick in range(n):
        counts[choose_action(actor, target or Player("Target"), tick)] += 1
    return counts


def test_a_calm_character_barely_bullies_but_an_angry_one_does_more():
    """The mechanism test above proves the *weight* moved. This proves the
    *distribution* did, which is what a player actually experiences — and it is
    the AGENTS.md "micro-scenario the emergence" half of the rule.

    Deterministic: `choose_action` seeds its RNG from (actor, target, tick), so
    the same draw sequence is compared across both characters and the only
    difference is the affect map.

    The threshold is 1.3x, not 2x, and that number is the measurement rather than
    a hope: `bully` competes against seven other actions, so multiplying its
    weight by :data:`AFFECT_TILT` moves its *share* by less than the factor
    (measured 0.106 -> 0.152, i.e. 1.44x). Asserting a doubling here would be
    asserting a stronger mechanic than the one that ships.
    """
    calm = _draw_counts({})
    angry = _draw_counts({"angry": 90})

    calm_rate = calm["bully"] / sum(calm.values())
    angry_rate = angry["bully"] / sum(angry.values())
    assert angry_rate > calm_rate * 1.3, (
        f"bully rate barely moved: calm={calm_rate:.3f} angry={angry_rate:.3f}")

    # And the effect is a tilt, not a switch: a calm character still sometimes
    # bullies, because the band and the traits still decide.
    assert calm_rate > 0.0


def test_a_feeling_changes_the_draw_enough_to_see_in_a_camp():
    """Two draws with the same seed, different affect, different actions — the
    clearest statement that this is behaviour and not a cosmetic weight."""
    from engine.background_social import choose_action

    calm = Player("Calm")
    angry = Player("Angry")
    angry.spike_emotion("angry", 90)
    target = Player("Target")

    calm_draws = [choose_action(calm, target, t) for t in range(400)]
    angry_draws = [choose_action(angry, target, t) for t in range(400)]
    assert calm_draws != angry_draws, "the same seed produced the same sequence"

    calm_bully = calm_draws.count("bully")
    angry_bully = angry_draws.count("bully")
    assert angry_bully > calm_bully, (calm_bully, angry_bully)


def test_a_grateful_character_compliments_more_often():
    calm = _draw_counts({})
    grateful = _draw_counts({"grateful": 90})
    calm_rate = calm["compliment"] / sum(calm.values())
    grateful_rate = grateful["compliment"] / sum(grateful.values())
    assert grateful_rate > calm_rate * 1.5, (
        f"compliment rate barely moved: {calm_rate:.3f} -> {grateful_rate:.3f}")
