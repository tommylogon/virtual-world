"""Background social interactions (task-423, absorbing task-417).

One event, two participants, two asymmetric outcomes: Rikka teases Vekka and
Rikka's memory reads "I teased Vekka" with closeness up while Vekka's reads
"Rikka teased me" with closeness down. No LLM; a weighted draw over gated
actions, then a computed six-tier outcome.

The gate is a component rather than a separate pass (task-417): same area, both
background, capped per in-game day, or a crowded camp becomes a relationship
treadmill. Relationship changes go through engine/relationships.py (task-420).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from player import Player
from engine.background_social import (
    ACTIONS,
    CONFIDE_BAND,
    MEETINGS_PER_CHARACTER_PER_DAY,
    NARRATIVE_TAGS,
    SOCIAL_COOLDOWN_MINUTES,
    TIER_SCALE,
    TIERS,
    _reading,
    action_weights,
    affinity,
    choose_action,
    ignore_weight,
    meetings_allowed,
    pair_for_area,
    perform,
    resolve_tier,
    run_social_pass,
)

AREA = "Verdant Hollow"
ELSEWHERE = "Cold Ridge"


def _world(minutes_per_tick=1):
    world = create_app({"TESTING": True}).world
    world.time_per_tick_minutes = minutes_per_tick
    world.movement.add_area(Area(AREA, "A hollow.", []))
    world.movement.add_area(Area(ELSEWHERE, "A ridge.", []))
    return world


def _player(world, name, area=AREA, background=True, **vitals):
    p = Player(name)
    world.add_player(p)
    world.set_player_area(name, area)
    p.current_area = area
    p.simulation_mode = "background" if background else "active"
    p.vitals.update({"Social": 50, "Entertainment": 50, "Hunger": 0,
                     "Thirst": 0, "Energy": 100, **vitals})
    return p


def _pair(world, closeness=0, traits=None, area=AREA):
    a = _player(world, "Rikka", area)
    b = _player(world, "Vekka", area)
    if closeness:
        a.relationships["Vekka"] = {"closeness": closeness,
                                    "last_interaction_tick": 0,
                                    "interaction_count": 1}
        b.relationships["Rikka"] = {"closeness": closeness,
                                    "last_interaction_tick": 0,
                                    "interaction_count": 1}
    if traits:
        a.traits.update(traits)
    return a, b


# ── the gate: co-presence (task-417) ─────────────────────────────────────


def test_two_background_characters_in_different_areas_never_meet():
    world = _world()
    _player(world, "Rikka", AREA)
    _player(world, "Vekka", ELSEWHERE)
    assert run_social_pass(world, tick=0) == []


def test_an_area_with_one_background_character_has_no_pairs():
    world = _world()
    a = _player(world, "Rikka")
    assert pair_for_area(world, "", AREA, 0) == []
    assert run_social_pass(world, tick=0) == []


def test_attended_characters_are_not_paired():
    """An attended character's social life belongs to the LLM loop."""
    world = _world()
    _player(world, "Rikka", background=False)
    _player(world, "Vekka", AREA)
    assert run_social_pass(world, tick=0) == []


def test_a_busy_or_unconscious_character_is_not_paired():
    world = _world()
    a, b = _pair(world)
    b.activity = {"type": "sleeping", "started_at_tick": 0}
    assert run_social_pass(world, tick=0) == []
    b.activity = None
    b.state = "unconscious"
    assert run_social_pass(world, tick=0) == []


def test_pairing_is_deterministic():
    """Same relationship state, same pairs — whatever the dict order."""
    def pairs_once():
        world = _world()
        for name in ("A", "B", "C", "D"):
            _player(world, name)
        got = pair_for_area(world, "", AREA, 0)
        return sorted((p.name, q.name) for p, q in got)

    assert pairs_once() == pairs_once()


def test_everyone_gets_at_most_one_pair_per_pass():
    world = _world()
    for name in ("A", "B", "C"):
        _player(world, name)
    pairs = pair_for_area(world, "", AREA, 0)
    used = [p.name for pair in pairs for p in pair]
    assert len(used) == len(set(used))
    assert len(pairs) == 1  # three people, one pair, one left over


def test_the_daily_cap_is_enforced_and_rolls_over():
    """Driven through the real pass, looping because a draw may come up `ignore`
    (which costs nothing — see bg_social BASE_WEIGHTS)."""
    world = _world()
    a, b = _pair(world)
    assert meetings_allowed(a, world, 0) == MEETINGS_PER_CHARACTER_PER_DAY

    tick = 0
    for _ in range(MEETINGS_PER_CHARACTER_PER_DAY * (SOCIAL_COOLDOWN_MINUTES + 2)):
        run_social_pass(world, tick=tick)
        if meetings_allowed(a, world, tick) <= 0:
            break
        tick += 1

    assert meetings_allowed(a, world, tick) == 0
    assert pair_for_area(world, "", AREA, tick) == []
    # A day later the budget is back.
    day = max(1, int(round(1440 / world.time_per_tick_minutes)))
    assert meetings_allowed(a, world, day + 1) == MEETINGS_PER_CHARACTER_PER_DAY


def test_the_cap_is_tick_length_independent():
    for minutes in (1, 15):
        world = _world(minutes_per_tick=minutes)
        a, _ = _pair(world)
        day = max(1, int(round(1440 / minutes)))
        assert meetings_allowed(a, world, day - 1) == MEETINGS_PER_CHARACTER_PER_DAY
        world._social_day["Rikka"] = {"day": 0, "count": MEETINGS_PER_CHARACTER_PER_DAY}
        assert meetings_allowed(a, world, day + 1) == MEETINGS_PER_CHARACTER_PER_DAY


# ── selection: a draw, not argmax ────────────────────────────────────────


def test_selection_is_a_weighted_draw_not_argmax():
    """Over many events one character must show more than one action."""
    world = _world()
    a, b = _pair(world)
    seen = {choose_action(a, b, tick) for tick in range(200)}
    assert len(seen) > 1, f"argmax: always {seen}"
    assert seen - {"ignore"}, "never actually engaged"


def test_an_introvert_ignores_far_more_often_than_an_extrovert():
    world = _world()
    intro, target = _pair(world, traits={"introvert": True})
    extro, target2 = _pair(world)

    intro_ignores = sum(choose_action(intro, target, t) == "ignore" for t in range(300))
    extro_ignores = sum(choose_action(extro, target2, t) == "ignore" for t in range(300))
    assert intro_ignores > extro_ignores * 2, (intro_ignores, extro_ignores)
    assert ignore_weight(intro) > ignore_weight(extro)


def test_a_hostile_character_leans_toward_bullying():
    world = _world()
    hostile, target = _pair(world, traits={"hostile": True})
    mild, target2 = _pair(world)
    assert (action_weights(hostile, target)["bully"]
            > action_weights(mild, target2)["bully"])


def test_bands_gate_the_intimate_actions():
    """Flirt and confide unlock with closeness — the Diary's min-quality gate."""
    world = _world()
    cold, target = _pair(world, closeness=-10)
    warm, target2 = _pair(world, closeness=60)
    assert action_weights(cold, target)["flirt"] == 0
    assert action_weights(cold, target)["confide"] == 0
    assert action_weights(warm, target2)["flirt"] > 0
    assert action_weights(warm, target2)["confide"] > 0


def test_need_pressure_raises_reaching_out():
    world = _world()
    lonely, target = _pair(world)
    lonely.vitals["Social"] = 10
    content, target2 = _pair(world)
    content.vitals["Social"] = 100
    assert (action_weights(lonely, target)["chat"]
            > action_weights(content, target2)["chat"])


# ── outcome: the six-tier ladder ─────────────────────────────────────────


def test_tiers_come_from_the_seeded_roll_and_are_reproducible():
    world = _world()
    a, b = _pair(world)
    first = [resolve_tier(a, b, "chat", t) for t in range(60)]
    second = [resolve_tier(a, b, "chat", t) for t in range(60)]
    assert first == second
    assert set(first) <= set(TIERS)


def test_warmer_relationships_land_better():
    """The band is a modifier, so a friend's joke lands more often than a rival's."""
    world = _world()
    warm, target = _pair(world, closeness=70)
    cold, target2 = _pair(world, closeness=-40)

    def successes(actor, tgt):
        return sum(TIER_SCALE[resolve_tier(actor, tgt, "joke", t)] > 0
                   for t in range(400))

    assert successes(warm, target) > successes(cold, target2)


def test_the_sign_rule_a_tease_reads_opposite_by_band():
    """Load-bearing: a tease between friends is affection for both sides; the
    same tease at low closeness is an attack on the target."""
    friendly = _reading("tease", closeness=60)
    hostile = _reading("tease", closeness=-30)

    assert friendly["target"]["Social"] > 0
    assert hostile["target"]["Social"] < 0
    assert hostile["rel_target"] < 0
    # The actor's own read stays positive either way — it was their idea.
    assert friendly["actor"]["Social"] > 0
    assert hostile["actor"]["Social"] > 0


def test_bullying_is_never_warm_however_it_lands():
    reading = _reading("bully", closeness=80)
    assert reading["target"]["Social"] < 0
    assert reading["rel_target"] < 0


def test_failure_tiers_are_damped_so_the_camp_is_not_monotonically_miserable():
    failures = [TIER_SCALE[t] for t in TIERS if TIER_SCALE[t] < 0]
    successes = [TIER_SCALE[t] for t in TIERS if TIER_SCALE[t] > 0]
    assert abs(sum(failures)) < sum(successes)


# ── one event, two asymmetric records ────────────────────────────────────


def test_one_event_writes_two_different_memories_and_deltas():
    world = _world()
    actor, target = _pair(world, closeness=70)
    actor.relationships["Vekka"]["closeness"] = 60
    target.relationships["Rikka"]["closeness"] = 60

    outcome = perform(world, actor, target, "", AREA, 0, action="tease")
    assert outcome is not None

    actor_mem = [m for m in actor.memories if m.get("type") == "social"]
    target_mem = [m for m in target.memories if m.get("type") == "social"]
    assert len(actor_mem) == 1 and len(target_mem) == 1
    assert actor_mem[0]["text"] != target_mem[0]["text"]
    assert actor_mem[0]["text"].startswith("I ")
    assert target_mem[0]["text"].startswith("Rikka ")
    assert actor_mem[0]["source"] == "background"


def test_memories_carry_entity_ids_for_both_parties_and_the_area():
    """The field that makes "every memory Vekka has about Rikka" a lookup."""
    world = _world()
    actor, target = _pair(world)
    perform(world, actor, target, "area_verdant_hollow", AREA, 0, action="chat")

    memory = [m for m in target.memories if m.get("type") == "social"][0]
    assert "player_Rikka" in memory["entity_ids"]
    assert "player_Vekka" in memory["entity_ids"]
    assert "area_verdant_hollow" in memory["entity_ids"]
    assert memory["location"] == AREA


def test_memories_and_traces_use_the_narrative_vocabulary():
    world = _world()
    actor, target = _pair(world)
    perform(world, actor, target, "", AREA, 0, action="chat")

    memory = [m for m in actor.memories if m.get("type") == "social"][0]
    assert "social" in memory["tags"]
    assert any(t in NARRATIVE_TAGS.values() for t in memory["tags"])
    assert memory["importance"] >= 4

    entry = actor.trace_log[-1]
    assert entry["kind"] == "social"
    assert entry["why"].startswith("social:")
    assert entry["area"] == AREA
    assert any(t.startswith("rel:") for t in entry["tags"])


def test_both_sides_get_their_own_trace_entry():
    world = _world()
    actor, target = _pair(world)
    perform(world, actor, target, "", AREA, 0, action="chat")
    assert actor.trace_log[-1]["kind"] == "social"
    assert target.trace_log[-1]["kind"] == "social"


def test_a_relationship_delta_records_its_cause():
    """task-420: the change must be explainable afterwards."""
    world = _world()
    actor, target = _pair(world, closeness=70)
    perform(world, actor, target, "", AREA, 0, action="chat")
    rel_entries = [e for e in actor.trace_log if e["kind"] == "relationship"]
    for entry in rel_entries:
        assert entry["delta"]["cause"] in ACTIONS
        assert entry["delta"]["with"] == "Vekka"


# ── rate limiting: the cap, not a blocking activity ───────────────────────


def test_an_interaction_does_not_block_the_survival_ladder():
    """A conversation must not stop a character eating, sleeping or washing.

    task-423 §4 specified a blocking `conversing` activity. Measured, it broke the
    survival ladder at short ticks: a 10-tick block at 1 min/tick repeated over a
    day dropped camp Hygiene 70 -> 28 and Entertainment 38 -> 11, because a
    blocked character cannot act — while at 15 min/tick it rounded to one tick and
    never blocked anything, so the damage was invisible there. The daily cap
    already holds the rate to 6-7 interactions per character per day at both tick
    lengths, so the cap is the bound and the activity is gone.
    """
    world = _world()
    actor, target = _pair(world)
    perform(world, actor, target, "", AREA, 0, action="chat")
    assert actor.activity is None
    assert target.activity is None


def test_the_cooldown_is_expressed_in_game_minutes():
    """A character cannot be drawn into another interaction until the cooldown
    has passed in GAME minutes, so it does not stretch or shrink with the tick."""
    for minutes_per_tick, expected_ticks in ((1, SOCIAL_COOLDOWN_MINUTES),
                                             (15, SOCIAL_COOLDOWN_MINUTES // 15)):
        world = _world(minutes_per_tick=minutes_per_tick)
        actor, target = _pair(world)
        perform(world, actor, target, "", AREA, 0, action="chat")
        assert pair_for_area(world, "", AREA, expected_ticks - 1) == []
        assert pair_for_area(world, "", AREA, expected_ticks + 1) != []


def test_the_cooldown_spreads_a_day_rather_than_letting_it_burst():
    """Six interactions land spread out, not in the first six ticks."""
    world = _world(minutes_per_tick=1)
    actor, target = _pair(world)
    ticks_used = []
    for tick in range(2000):
        if pair_for_area(world, "", AREA, tick):
            perform(world, actor, target, "", AREA, tick, action="chat")
            ticks_used.append(tick)
        if len(ticks_used) >= MEETINGS_PER_CHARACTER_PER_DAY:
            break
    assert len(ticks_used) == MEETINGS_PER_CHARACTER_PER_DAY
    # Consecutive interactions are at least the cooldown apart.
    gaps = [b - a for a, b in zip(ticks_used, ticks_used[1:])]
    assert gaps and min(gaps) >= SOCIAL_COOLDOWN_MINUTES


# ── the pass as a whole ──────────────────────────────────────────────────


def test_the_pass_changes_both_sides_but_leaves_third_parties_alone():
    world = _world()
    actor, target = _pair(world)
    bystander = _player(world, "Gribba", ELSEWHERE)
    before = len(bystander.memories)

    # A draw may come up `ignore`, which is a legitimate no-op; loop until the
    # pass actually engages.
    outcomes = []
    for tick in range(50):
        outcomes = run_social_pass(world, tick=tick)
        if outcomes:
            break

    assert len(outcomes) == 1
    assert actor.memories and target.memories
    assert len(bystander.memories) == before


def test_replaying_the_same_state_reproduces_the_same_history():
    def run_once():
        world = _world()
        for name in ("Arix", "Belne", "Rikka", "Vekka"):
            _player(world, name)
        return [(o["actor"], o["target"], o["action"], o["tier"])
                for o in run_social_pass(world, tick=7)]

    assert run_once() == run_once()


def test_social_outcomes_do_not_replace_food_as_the_death_cause():
    """Survivability guard: a burst of interactions must not drain a character
    out of existence in a day."""
    world = _world()
    actor, target = _pair(world, closeness=50)
    for tick in range(1440):
        for p in (actor, target):
            p.activity = None
            p.conditions.pop("busy", None)
            p.vitals.setdefault("Hunger", 0)
            p.vitals["Hunger"] = 0
            p.vitals["Thirst"] = 0
            p.vitals["Energy"] = 100
        pair_for_area(world, "", AREA, tick) or None
        if pair_for_area(world, "", AREA, tick):
            perform(world, actor, target, "", AREA, tick, action="chat")
    assert actor.state != "dead"
    assert target.state != "dead"
