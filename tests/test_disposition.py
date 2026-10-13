"""Tests for the disposition score registry (task-800).

The registry is the shared currency every contributor writes into, so the two
things worth proving are: (1) the declaration is internally sound - every score
carries a kind, a base and a range, and every decision references only declared
scores; and (2) the gate actually fails on an undeclared reference, so a typo in a
long modifier catalogue is not silent.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import disposition
from tools import disposition_index as di


def test_registry_is_internally_consistent():
    assert disposition.check_registry() == []


def test_every_score_declares_kind_base_and_range():
    assert disposition.SCORES, "the registry must declare at least one score"
    for score in disposition.SCORES:
        assert score.kind in disposition.SCORE_KINDS, score.name
        assert score.lo <= score.base <= score.hi, score.name
        # namespaced: `relief.weight.witness`, never a bare word
        assert "." in score.name, score.name


def test_every_decision_uses_a_known_combine_and_pick():
    for decision in disposition.DECISIONS:
        assert decision.combine in disposition.COMBINES, decision.name
        assert decision.pick in disposition.PICKS, decision.name


def test_scores_for_returns_declared_scores():
    scores = disposition.scores_for("relieve")
    assert scores and all(s.kind in disposition.SCORE_KINDS for s in scores)
    # the dependency is real: relieve's pick is argmin, so its terms are utilities
    assert {s.name for s in scores} <= {s.name for s in disposition.SCORES}


def test_unknown_score_raises():
    try:
        disposition.validate_score("choice.utility.forceful_action")
    except KeyError as exc:
        assert "forceful_action" in str(exc)
    else:  # pragma: no cover - would mean the name was declared
        raise AssertionError("an undeclared score must raise KeyError")


def test_unknown_decision_raises():
    try:
        disposition.scores_for("no_such_decision")
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("an unknown decision must raise KeyError")


def test_engine_crosscheck_is_clean_on_the_real_tree():
    """The declared bases equal the constants the engine actually reads."""
    hard = [p for p in di.engine_crosscheck() if not p.startswith("(soft)")]
    assert hard == [], hard


def test_gate_flags_an_undeclared_score_in_a_modifier_file(monkeypatch, tmp_path):
    """Mechanism: a modifier naming an undeclared score fails the scan."""
    monkeypatch.setattr(di, "ROOT", tmp_path)
    monkeypatch.setattr(di, "MODIFIER_DIRS", ("data/personality",))
    folder = tmp_path / "data" / "personality"
    folder.mkdir(parents=True)
    (folder / "sample.json").write_text(json.dumps({
        "modifiers": [
            {"target": "choice.utility.forceful_action", "coefficient": 0.4},
        ],
    }), encoding="utf-8")
    problems = di.modifier_files_check()
    assert any("choice.utility.forceful_action" in p for p in problems), problems


def test_gate_accepts_a_declared_score_reference(monkeypatch, tmp_path):
    """The other direction: a declared score raises nothing."""
    monkeypatch.setattr(di, "ROOT", tmp_path)
    monkeypatch.setattr(di, "MODIFIER_DIRS", ("data/personality",))
    folder = tmp_path / "data" / "personality"
    folder.mkdir(parents=True)
    (folder / "ok.json").write_text(json.dumps({
        "target": "relief.weight.witness",
    }), encoding="utf-8")
    assert di.modifier_files_check() == []


# ── task-801: the action-side feature table ────────────────────────────────────

def test_every_soak_verb_contributes_to_a_declared_score():
    declared = {s.name for s in disposition.SCORES}
    for verb in disposition.SOAK_VERBS:
        features = disposition.features_of(verb)
        assert features, f"soak verb {verb!r} contributes nothing"
        assert set(features) <= declared, (verb, features)


def test_feature_table_and_targets_reference_only_declared_scores():
    # the whole point of the feature table: unknown scores are impossible
    assert disposition.check_features() == []


def test_target_tags_contribute_by_the_real_vocabularies():
    # a latrine is a relief fixture (engine/relief.RELIEF_TAGS), a lake is water
    # (background_simulation.DRINK_TAGS)
    assert "relief.fixture_bonus" in disposition.features_of("go", ["latrine"])
    assert "survive.utility.need_relief" in disposition.features_of("go", ["water"])
    # an unknown tag contributes nothing and never a stray key
    assert disposition.features_of("go", ["not_a_tag"]) == {
        "survive.utility.need_relief": 1.0}


def test_features_merge_verb_and_target():
    merged = disposition.features_of("drink", ["water"])
    # the verb's own channel plus the target's, summed
    assert merged["survive.utility.need_relief"] == 2.0


# ── task-802: character weights from traits + live modifiers ────────────────────

class _FakePlayer:
    def __init__(self, traits=None, vitals=None, memories=None, emotions=None,
                 morals=None, dials=None):
        self.traits = traits or {}
        self.vitals = vitals or {}
        self.memories = memories or []
        self.morals = morals or {}
        self.personality_dials = dials or {}
        self.personality = ""
        self._emotions = emotions or {}

    def emotions_map(self):
        return self._emotions


def test_unauthored_character_scores_neutral():
    # the backward-compat rule: absent traits read dial 0.5, so weights are empty
    assert disposition.trait_weights(_FakePlayer()) == {}


def test_a_trait_derives_a_weight_not_a_per_character_number():
    w = disposition.trait_weights(_FakePlayer(traits={"cowardly": True}))
    # (1.0 - 0.5) * 2.0
    assert w["relief.weight.witness"] == 1.0
    # a numeric dial scales between the neutral ends
    half = disposition.trait_weights(_FakePlayer(traits={"cowardly": 0.75}))
    assert half["relief.weight.witness"] == 0.5


def test_needs_fire_only_past_the_threshold_and_read_both_directions():
    hungry = _FakePlayer(vitals={"Hunger": 80})       # drive: fill toward 100
    w = disposition.need_weights(hungry)
    assert w["survive.utility.need_relief"] == 30.0    # 80 - 50
    assert w["attention.salience.remembered"] == 1.0
    assert disposition.need_weights(_FakePlayer(vitals={"Hunger": 10})) == {}
    tired = _FakePlayer(vitals={"Energy": 10})         # meter: deplete toward 0
    assert disposition.need_weights(tired)["survive.utility.need_relief"] == 20.0


def test_emotion_tilts_a_social_weight(monkeypatch):
    import engine.emotion as emotion_mod
    monkeypatch.setattr(emotion_mod, "raised_axes",
                        lambda values, min_margin=None: {"angry": 40.0})
    w = disposition.emotion_weights(_FakePlayer())
    assert w["social.weight.bully"] == 1.0


def test_relationship_closeness_unlocks_warm_actions(monkeypatch):
    import engine.relationships as rel_mod
    monkeypatch.setattr(rel_mod, "get_relationship",
                        lambda player, name: {"closeness": 60})
    w = disposition.relationship_weights(_FakePlayer(), "Vekka")
    assert "social.weight.confide" in w and "social.weight.flirt" in w
    monkeypatch.setattr(rel_mod, "get_relationship",
                        lambda player, name: {"closeness": 0})
    assert disposition.relationship_weights(_FakePlayer(), "Vekka") == {}


def test_a_memory_of_the_target_raises_salience():
    p = _FakePlayer(memories=[{"text": "Rikka teased me in the sleeping halls"}])
    assert disposition.memory_weights(p, "Rikka")["attention.salience.remembered"] == 1.0
    assert disposition.memory_weights(p, "Zikka") == {}


def test_character_weights_merge_traits_and_live_state():
    p = _FakePlayer(traits={"cowardly": True}, vitals={"Hunger": 80})
    w = disposition.character_weights(p)
    assert w["relief.weight.witness"] == 1.0            # from the trait
    assert w["survive.utility.need_relief"] == 30.0     # from the need


def test_character_tables_reference_only_declared_scores():
    assert disposition.check_character() == []


# ── task-803: value gates as hard exclusions ───────────────────────────────────

def test_a_value_gate_removes_the_option():
    honest = _FakePlayer(traits={"honest": True})
    assert disposition.is_gated(honest, "steal")
    assert disposition.filter_actions(honest, ["steal", "take", "look"]) == \
        ["take", "look"]


def test_the_gate_is_trait_driven_not_global():
    plain = _FakePlayer()
    assert disposition.gated_verbs(plain) == set()
    assert disposition.filter_actions(plain, ["steal", "take"]) == ["steal", "take"]


def test_a_gate_only_subtracts_and_never_enables():
    # the invariant: whatever the flags, the result is a subset of the input
    for p in (
        _FakePlayer(traits={"honest": True}),
        _FakePlayer(traits={"nonviolent": True}),
        _FakePlayer(morals={"loyal": True}),
        _FakePlayer(),
    ):
        verbs = ["steal", "take", "attack", "look", "flirt"]
        out = disposition.filter_actions(p, verbs)
        assert set(out) <= set(verbs)
        assert len(out) <= len(verbs)


def test_moral_flags_come_from_morals_not_only_traits():
    p = _FakePlayer(morals={"nonviolent": True})
    assert disposition.filter_actions(p, ["attack", "look"]) == ["look"]


def test_real_library_trait_prudish_excludes_flirt():
    p = _FakePlayer(traits={"prudish": True})
    assert disposition.filter_actions(p, ["flirt", "chat"]) == ["chat"]


# ── task-804: the resolver (combine + pick modes) ──────────────────────────────

def test_argmin_picks_the_lowest_scoring_candidate():
    # relieve sums its utility; fewer witnesses scores lower (better)
    r = disposition.resolve("relieve", [
        ("busy_hall", {"relief.witnesses": 4}),
        ("empty_room", {"relief.witnesses": 0}),
    ])
    assert r.key == "empty_room"
    assert r.mode == "argmin"


def test_argmax_is_a_real_mode(monkeypatch):
    # no shipped decision declares argmax yet, so prove the branch directly
    dec = disposition.Decision(
        "_t_argmax", "add", "argmax", tuple(s.name for s in disposition.SCORES))
    monkeypatch.setattr(disposition, "DECISIONS",
                        disposition.DECISIONS + (dec,))
    r = disposition.resolve("_t_argmax", [("a", {}), ("b", {"relief.witnesses": 2})])
    assert r.key == "b"


def test_weighted_draw_is_deterministic_given_a_seed():
    cands = [("chat", {"social.weight.chat": 1.0}),
             ("joke", {"social.weight.joke": 1.0})]
    assert disposition.resolve("social", cands, seed=7).key == \
        disposition.resolve("social", cands, seed=7).key


def test_ties_break_stably_on_the_key():
    cands = [("zebra", {}), ("apple", {})]          # identical scores
    first = disposition.resolve("relieve", cands).key
    second = disposition.resolve("relieve", cands).key
    assert first == second == "apple"               # alphabetically first, stable


def test_conditions_report_the_winners_contributions_largest_first():
    r = disposition.resolve("relieve", [("room", {"relief.witnesses": 3})])
    values = [abs(v) for _, v in r.contributions]
    assert values == sorted(values, reverse=True)
    assert dict(r.contributions)["relief.witnesses"] == 3.0


def test_threshold_then_utility_picks_the_best_utility():
    r = disposition.resolve("hunt", [
        ("wait", {}),
        ("stalk", {"hunt.utility.prey_value": 5.0}),
    ])
    assert r.key == "stalk"
    assert r.mode == "threshold-then-utility"


def test_resolver_rejects_unknown_decision_and_empty_set():
    for args in (("no_such", []), ("relieve", [])):
        try:
            disposition.resolve(*args)
        except (KeyError, ValueError):
            pass
        else:  # pragma: no cover
            raise AssertionError(f"resolve{args} should have raised")


# ── task-805: whispers for the LLM ─────────────────────────────────────────────

def test_whispers_are_prose_from_the_traits():
    lines = disposition.whispers(_FakePlayer(traits={"cowardly": True}))
    assert any("audience" in line for line in lines)
    # an unauthored character whispers nothing
    assert disposition.whispers(_FakePlayer()) == []


def test_whispers_include_a_pressing_need():
    assert "You are hungry." in disposition.whispers(_FakePlayer(vitals={"Hunger": 80}))


def test_trait_behavior_prompts_reads_the_library_definitions():
    from engine.traits import TraitSystem
    prompts = TraitSystem.behavior_prompts(_FakePlayer(traits={"exhibitionist": True}))
    assert prompts and "seen" in prompts[0].lower()


# ── task-806: personality dials, distinct from the prose ───────────────────────

def test_a_dial_moves_a_weight_and_defaults_neutral():
    # no dial and no capability -> neutral
    assert disposition.trait_weights(_FakePlayer()) == {}
    # an authored dial drives the weight
    dialled = disposition.trait_weights(_FakePlayer(dials={"cowardly": 1.0}))
    assert dialled["relief.weight.witness"] == 1.0


def test_a_dial_wins_over_a_capability_of_the_same_name():
    # a neutral dial must override a present capability (the two homes are distinct)
    p = _FakePlayer(traits={"cowardly": True}, dials={"cowardly": 0.5})
    assert disposition.trait_weights(p) == {}
    # and a capability still reads when no dial exists (existing characters unchanged)
    assert disposition.trait_weights(_FakePlayer(traits={"cowardly": True}))[
        "relief.weight.witness"] == 1.0


def test_the_prose_personality_string_is_separate_from_the_dials():
    from engine.traits import TraitSystem
    p = _FakePlayer(dials={"cowardly": 0.9})
    p.personality = "a nervous clerk"
    assert TraitSystem.dial_value(p, "cowardly") == 0.9
    assert p.personality == "a nervous clerk"          # untouched by dial reads


def test_dials_normalize_and_clamp_on_load():
    from engine.serialization import normalize_dials
    assert normalize_dials({"cowardly": 2, "bad": "x"}) == {"cowardly": 1.0}
    assert normalize_dials(None) == {}


# ── the serialization wiring (the caller the engine cards were missing) ─────────

def test_disposition_payload_wires_traits_needs_gates_and_dials():
    # the live path: trait + need + dial + moral -> the payload the Mind panel reads
    from engine.serialization import _disposition_payload
    p = _FakePlayer(traits={"patient": True}, vitals={"Hunger": 80},
                    dials={"cowardly": 0.9}, morals={"honest": True})
    payload = _disposition_payload(p)
    weights = {w["name"]: w["value"] for w in payload["weights"]}
    assert weights["social.weight.bully"] == -1.0          # patient, scale -2.0 * 0.5
    assert weights["survive.utility.need_relief"] == 30.0  # hunger 80 - threshold 50
    # each weight carries its registry kind/base/range (task-800)
    bully = next(w for w in payload["weights"] if w["name"] == "social.weight.bully")
    assert bully["kind"] == "weight" and bully["base"] == 2.0 and bully["hi"] == 100.0
    # dials and moral gates ride along
    assert payload["dials"] == {"cowardly": 0.9}
    assert "steal" in payload["gated"]
    # the action side lists the soak verbs and what each contributes
    assert any(a["verb"] == "drink" and "survive.utility.need_relief" in a["scores"]
               for a in payload["actions"])

