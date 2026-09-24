"""Deterministic background survival runner (task-399).

Characters with ``simulation_mode == "background"`` do not run the LLM loop.
Instead this module makes *coarse, deterministic* decisions against the
**same** Player/graph state so the character stays the same person (see
docs/design/reversibility-contract.md).

Every character takes **one action per turn** — the turn is the unit of agency,
and a turn is the same amount of game time for everyone. Background decisions used
to be paced by an "action credit" measured in game minutes (one decision per 10
game minutes), which put this tier on a different clock from the live one: at a
1-minute turn it acted ten times less often than the player, at 15 minutes
slightly more, and the two agreed only around T=10 by coincidence. A live
character and a background character now spend a turn the same way, which is also
what makes promotion between the tiers safe.

v1 scope — survival only:
    drink when thirsty, eat when hungry, sleep when tired, travel one hop
    toward a known food/water area when the local area has none.

Every decision writes an objective trace entry with a reason tag
(docs/design/trace-format.md) so the span can later be summarized into memory.

Deliberately NOT here yet: schedules/work, relationships, dialogue, combat.
Those are the next slices. No LLM calls are made.
"""

from __future__ import annotations

import logging
import random
from collections import deque

from graph import EDGE_IN, EDGE_CARRYING, EDGE_TRIGGERS
from engine.trace import record
from vital_rates import tick_minutes

logger = logging.getLogger(__name__)

FOOD_TAGS = ("food", "eat", "edible", "meal")
DRINK_TAGS = ("drink", "water", "beverage")


def _surface_need_recall(gs, player, need):
    """task-403: surface one recalled memory when a need is pressing.

    Memory only — it never changes what the character does — and ``AgentMind``
    dedupes to one surfacing per in-game day per need, so a long soak does not
    accumulate recall spam. Failures are swallowed: recall is a nice-to-have and
    must never abort a survival action.
    """
    try:
        from engine.agent_memory import AgentMind
        minutes = float(getattr(gs, "time_ticks", 0) or 0) * float(
            getattr(gs, "time_per_tick_minutes", 1) or 1)
        AgentMind(player, getattr(gs, "graph", None), game_state=gs).surface_need_memory(
            need, getattr(gs, "time_ticks", 0), day_key=int(minutes // 1440))
    except Exception:
        pass

THIRST_THRESHOLD = 45     # drive: high = parched; act before it gets urgent
HUNGER_THRESHOLD = 50     # drive: high = starving
ENERGY_THRESHOLD = 30     # resource: low = tired
BLADDER_THRESHOLD = 60    # drive: high = needs to go; well before it maxes at 100
HYGIENE_THRESHOLD = 40    # resource: low = filthy; go wash
ENTERTAINMENT_THRESHOLD = 40  # resource: low = bored; go do something
#: How long one work block lasts, in game minutes (task-409). Short on purpose:
#: `_act` skips anyone mid-activity, so this is the longest a working character
#: can go without eating, drinking or relieving itself. See the block comment on
#: `working` in activities.py for why a long block is a trap.
WORK_MINUTES = 30

#: resource: low = unravelling; rest a while. This is the "rest" half of the
#: task-432 sources — see `_recuperate` for why it is a bounded *rest* rather
#: than sleep.
SANITY_THRESHOLD = 40
#: How long one recuperative rest lasts, in game minutes.
SANITY_REST_MINUTES = 60

MEAL_RESTORE = 45         # Hunger (drive) reduced by this when eating
DRINK_RESTORE = 50        # Thirst (drive) reduced by this when drinking

#: A relief site: an area tag (a latrine) or a fixture standing in the area.
RELIEF_TAGS = ("latrine", "toilet", "privy", "restroom", "bathroom")
#: A washing site: an area tag (a river) or a fixture (a wash spot, a shower).
BATH_TAGS = ("bathing", "wash", "shower", "bath", "washing")
BATH_HYGIENE = 70         # fallback when a fixture does not author its own amount
#: A recreational site: a fixture (a drum, a dice game, a fire) or an area that
#: is itself the gathering place. The amount comes from the fixture's authored
#: `adjust_vital Entertainment`, like washing.
RECREATION_TAGS = ("recreation",)
ENTERTAINMENT_RESTORE = 15  # fallback when a fixture does not author its own amount

#: Finding something in the *field* (an item you are not carrying) is a skill
#: check, not a guarantee: a perceptive forager eats, a clumsy one goes hungry
#: and moves on (task-469). Carried items never need a check.
FORAGE_SKILL = "Perception"
FORAGE_DC = 10

#: Minutes each background action takes. A turn is a *timeframe*, and these fill
#: it, so the number of actions per turn is **emergent** rather than budgeted: a
#: character does what fits and stops as soon as nothing is due (task-436).
#:
#: This is not a rate constant and must not be confused with the LLM **decision**
#: cadence, which is one per turn per focused character and is the thing that
#: costs money. A deterministic character fills its whole timeframe; an LLM
#: decides once and the engine resolves the rest.
#:
#: `travel` is a single step, so a walk legitimately repeats until the timeframe
#: runs out. Every other entry is a task: once done it is not repeated in the
#: same timeframe, which is what stops a 30-minute turn from becoming thirty
#: meals. This replaces the old per-turn action *budget* (`actions_per_turn`),
#: which handed out one action per game minute and so assumed actions had no
#: duration — making long turns frantic as well as wasteful.
TASK_MINUTES = {
    "drink": 2,
    "eat": 10,
    "relieve": 5,
    "wash": 5,
    "recreate": 15,
    "recuperate": 30,
    "work": 30,
    "forage": 5,   # searching the area for something edible; may find nothing
    "travel": 1,   # one step; repeats until the timeframe is full
    "sleep": 1,    # lying down — the sleeping activity occupies what follows
}


def minutes_in_turn(gs) -> float:
    """The timeframe one turn covers, in game minutes: what a flow must fill."""
    try:
        return max(1.0, float(tick_minutes(gs)))
    except Exception:
        return 1.0


class BackgroundSimulation:
    """Runs due background characters. Owned by the engine, called each tick."""

    def __init__(self, game_state):
        self.gs = game_state
        self._areas_cache = {}

    # ───────────────────────────── entry point ─────────────────────────────

    def process_due(self):
        """Fill every character's timeframe — deterministically, for the
        characters that do not have a decision of their own this turn.

        A turn is a *timeframe* of T game minutes, and a character fills it with
        an action flow: each action consumes its `TASK_MINUTES` duration until the
        timeframe is full or nothing is due. The number of actions is therefore
        emergent — one at a 1-minute turn, and at 15 minutes the four or five
        things that actually fit. It is not a budget handed out per turn.

        The loop stops as soon as `_act` reports nothing to do, which is the
        common case: a fed, rested character spends a whole turn doing nothing at
        all. That is the point — survival is infrastructure, not a treadmill.

        A focused character has already spent its decision, which was this turn's
        first minute, so it flows for the remainder. Beyond that, an LLM-driven
        character and a deterministic one differ in who chose, not in how much
        time they get. The human's own character is never puppeted: its minutes
        are the player's.

        A character mid-activity (sleeping) or unconscious is skipped entirely, so
        a long sleep cannot leave a backlog to dump on waking.
        """
        for name, p in list(self.gs.players.items()):
            # A declared soak order drives this character for its span (its
            # intent, not the generic need policy) — see engine/soak.
            if getattr(p, "soak_order", None):
                continue
            focused = getattr(p, "simulation_mode", "active") != "background"
            # Human-driven characters (autonomy False) are never puppeted: the
            # player's minutes are theirs. This is the documented marker
            # (player.py:194, event-stream.js:136). `gs.active_player` is a
            # registry *key* (a string), so the old identity check against it
            # never matched and the human was simulated behind the player's back.
            if focused and getattr(p, "autonomy", True) is False:
                continue
            if p.state == "dead":
                continue
            if p.activity or p.state == "unconscious":
                continue  # committed to a duration; nothing to spend

            # An explicit "not before" tick (a save, a tool, a delayed event)
            # defers the character entirely. Nothing is banked, so a long
            # deferral cannot turn into a burst when it lifts.
            if self.gs.time_ticks < getattr(p, "next_due_tick", 0):
                continue

            remaining = minutes_in_turn(self.gs)
            if focused:
                remaining -= 1.0  # its decision was this turn's first minute
            served = set()  # tasks already done in THIS timeframe (not travel)
            while remaining > 0:
                try:
                    used = self._act(name, p, served, remaining)
                except Exception as e:  # never let one character stall the turn
                    logger.warning("[background] %s: %s", name, e)
                    break
                if not used:
                    break  # nothing is due; the rest of the timeframe passes
                remaining -= used
                if p.activity or p.state == "unconscious":
                    break  # a duration took over; it owns the rest of the turn

        # Social pass last (task-423): after everyone has moved and acted, so a
        # conversation happens where the characters actually ended up. Pairs per
        # area, once per tick, and gives both sides a short conversing activity —
        # which is why the loop above skips anyone mid-activity.
        try:
            from engine.background_social import (
                run_social_pass, run_social_approach, run_theft_pass,
            )
            run_social_pass(self.gs)
            run_social_approach(self.gs)
            # Actor-driven agenda last (task-468): a thief reaches for something
            # after everyone has moved, and its failed attempt writes the line
            # the interrupt evaluator reads.
            run_theft_pass(self.gs)
        except Exception as e:
            logger.warning("[background] social pass: %s", e)

    # ───────────────────────────── decisions ───────────────────────────────

    def _begin_task(self, p, activity_type, duration, remaining):
        """A task longer than what is left of the timeframe spans turns.

        A ten-minute meal cannot happen inside a one-minute turn. Without this
        the cost is **overdrawn**: the meal resolves instantly, so a fine-grained
        clock lets a character perform fifteen whole tasks in fifteen minutes
        while a coarse one admits only the two or three that fit. That asymmetry
        is the residual resolution dependence this fixes.

        The activity is authored in **minutes**, so however the clock is sliced
        the character is eating for ten minutes: ten turns at a 1-minute turn,
        most of one turn at fifteen. `process_due` skips anyone mid-activity and
        `ActivitySystem.tick_activity` ends it — and the type must be listed in
        `ACTIVITY_INTERRUPTIBLE` or it never expires and strands them busy.
        """
        if duration <= remaining:
            return  # it fits in what is left; just spend the minutes
        if p.activity:
            # A helper already opened an activity for this task (`_recuperate`
            # starts a `resting` block, `_pursue_schedule` a `working` one).
            # Overwriting it would discard that duration — and for `resting` it
            # silently replaced a correctly minute-converted one with ours.
            return
        p.activity = {
            "type": activity_type,
            "started_at_tick": self.gs.time_ticks,
            "target_item": None,
            "duration_minutes": float(duration),
            "elapsed_minutes": 0.0,
            "elapsed_ticks": 0,
            "visible": True,
        }

    def _act(self, name, p, served=None, remaining=None):
        """Take the character's next action in this turn's flow.

        Returns the **minutes the action took**, or ``None`` if nothing was due —
        which is the common case and ends the flow, letting the rest of the
        timeframe pass quietly. The caller fills a timeframe with these, so an
        action's duration is what limits how many fit in a turn.

        ``served`` is the set of tasks already done *in this timeframe*. A task
        is not repeated once done — otherwise a character whose meal did not fully
        clear their hunger would eat again, and again, as many times as the turn
        was long. Travel is deliberately **not** recorded: a walk is progress, so
        a character keeps stepping toward food until they reach it, at one minute
        a step.

        ``remaining`` is how much of the timeframe is left. A task longer than
        that does not resolve instantly — it starts an activity and spans turns,
        so its cost is the same game time at any clock resolution.
        """
        if served is None:
            served = set()
        if remaining is None:
            remaining = minutes_in_turn(self.gs)
        if p.activity:
            return None  # mid-activity (e.g. sleeping) — leave them to it
        if p.state == "unconscious":
            return None  # collapsed; the engine's recovery path handles waking

        v = p.vitals
        thirst = v.get("Thirst", 0)
        hunger = v.get("Hunger", 0)
        energy = v.get("Energy", 100)

        # Critical exhaustion wins over everything: without this, a character
        # chasing water they can't reach never sleeps and dies of exhaustion
        # (the exact failure the 2-day soak showed).
        if energy <= 15:
            self._sleep(p)
            served.add("sleep")
            return TASK_MINUTES["sleep"]

        if thirst >= THIRST_THRESHOLD:
            _surface_need_recall(self.gs, p, "thirst")
            # The scenario models natural water as an AREA tag ("water") you
            # drink from by standing in it, not as an item to consume.
            if self._in_water_area(p):
                p.vitals["Thirst"] = max(0, p.vitals.get("Thirst", 0) - DRINK_RESTORE)
                record(p, self.gs.time_ticks, "act",
                       f"drank from {p.current_area}", why="needs:drink",
                       area=p.current_area, tags=["need"])
                self.gs.add_log_entry(f"[{p.name}] drinks from {p.current_area}.")
                served.add("drink")
                self._begin_task(p, "drinking", TASK_MINUTES["drink"], remaining)
                return TASK_MINUTES["drink"]
            if "drink" not in served:
                outcome = self._consume_here(p, DRINK_TAGS, "drink")
                if outcome is True:
                    served.add("drink")
                    self._begin_task(p, "drinking", TASK_MINUTES["drink"], remaining)
                    return TASK_MINUTES["drink"]
                if outcome == "failed":
                    # Searched here and missed: spend the time, then head to a
                    # different source next (served blocks a retry this frame).
                    served.add("drink")
                    self._begin_task(p, "foraging", TASK_MINUTES["forage"], remaining)
                    return TASK_MINUTES["forage"]
            if self._travel_toward(p, DRINK_TAGS, "thirst"):
                return TASK_MINUTES["travel"]
            return None  # no water within reach; nothing else to try for it

        if energy <= ENERGY_THRESHOLD:
            self._sleep(p)
            served.add("sleep")
            return TASK_MINUTES["sleep"]

        if hunger >= HUNGER_THRESHOLD:
            _surface_need_recall(self.gs, p, "hunger")
            if "eat" not in served:
                outcome = self._consume_here(p, FOOD_TAGS, "eat")
                if outcome is True:
                    served.add("eat")
                    self._begin_task(p, "eating", TASK_MINUTES["eat"], remaining)
                    return TASK_MINUTES["eat"]
                if outcome == "failed":
                    served.add("eat")
                    self._begin_task(p, "foraging", TASK_MINUTES["forage"], remaining)
                    return TASK_MINUTES["forage"]
                if outcome is False:
                    spawned = self._forage_spawn(p, FOOD_TAGS)
                    if spawned is not None:
                        if self._consume_here(p, FOOD_TAGS, "eat") is True:
                            served.add("eat")
                            self._begin_task(p, "eating", TASK_MINUTES["eat"], remaining)
                            return TASK_MINUTES["eat"]
                        # Found something useless (junk, an herb): spend the search
                        # time and look elsewhere next turn — the wilds are not a
                        # pantry, and survival is not guaranteed (task-471/472).
                        served.add("eat")
                        self._begin_task(p, "foraging", TASK_MINUTES["forage"], remaining)
                        return TASK_MINUTES["forage"]
            if self._travel_toward(p, FOOD_TAGS, "hunger"):
                return TASK_MINUTES["travel"]

        if v.get("Bladder", 0) >= BLADDER_THRESHOLD:
            if "relieve" not in served and self._relieve(p):
                served.add("relieve")
                self._begin_task(p, "relieving", TASK_MINUTES["relieve"], remaining)
                return TASK_MINUTES["relieve"]
            if self._travel_toward(p, RELIEF_TAGS, "bladder"):
                return TASK_MINUTES["travel"]
            # Nowhere to go. The engine already docks Hygiene when the meter
            # maxes, which is the honest outcome for a camp with no latrine.
            return None

        if v.get("Hygiene", 100) <= HYGIENE_THRESHOLD:
            if "wash" not in served and self._wash(p):
                served.add("wash")
                self._begin_task(p, "washing", TASK_MINUTES["wash"], remaining)
                return TASK_MINUTES["wash"]
            if self._travel_toward(p, BATH_TAGS, "hygiene"):
                return TASK_MINUTES["travel"]

        # Steadying the mind. Above boredom because a low-Sanity character is a
        # danger to others rather than merely unhappy, but below every survival
        # need: nothing here kills you.
        if v.get("Sanity", 100) <= SANITY_THRESHOLD:
            if "recuperate" not in served and self._recuperate(p):
                served.add("recuperate")
                self._begin_task(p, "recuperating", TASK_MINUTES["recuperate"], remaining)
                return TASK_MINUTES["recuperate"]

        # What the day says to do, once every survival need is satisfied
        # (task-409). Above boredom, so a full character works at its trade
        # instead of milling about; below hunger and thirst, so a smith still
        # breaks off to eat.
        if "work" not in served and self._pursue_schedule(p):
            served.add("work")
            return TASK_MINUTES["work"]

        # Boredom last: it is the only need here that nothing kills you for
        # ignoring, so it must never outrank food, water, sleep or relief.
        if v.get("Entertainment", 100) <= ENTERTAINMENT_THRESHOLD:
            if "recreate" not in served and self._recreate(p):
                served.add("recreate")
                self._begin_task(p, "recreating", TASK_MINUTES["recreate"], remaining)
                return TASK_MINUTES["recreate"]
            if self._travel_toward(p, RECREATION_TAGS, "entertainment"):
                return TASK_MINUTES["travel"]

        return None  # nothing is due — the rest of the timeframe passes quietly

    # ─────────────────── public policy hooks (task-464) ────────────────────
    # The timeskip runner drives a *specific* character through these, instead
    # of the roster sweep in `process_due`. Same decisions, same clock.

    def take_action(self, p, served=None, remaining=1.0):
        """One deterministic action for *p*. Returns minutes used or None."""
        return self._act(p.name, p, served, remaining)

    def step_toward_area(self, p, area_name, reason="timeskip"):
        """One hop toward a named area."""
        return self._travel_to_area(p, area_name, reason)

    def step_toward_tags(self, p, tags, need="timeskip"):
        """One hop toward the nearest area that satisfies *tags*."""
        return self._travel_toward(p, tags, need)

    def find_matching(self, p, *, tags=(), name=None):
        """A reachable node matching a name (substring) or tag set."""
        want = str(name).lower() if name else None
        tag_set = {str(t).lower() for t in (tags or ())}
        graph = self.gs.graph
        player_id = self.gs._player_node_id(p.name)
        area_id = (self.gs.area_node_id(p.current_area) if p.current_area else None)

        candidates = []
        for e in graph.edges:
            if e.type == EDGE_CARRYING and e.target == player_id:
                node = graph.get_node(e.source)
                if node is not None:
                    candidates.append(node)
        if area_id:
            held = list(self._spatial_items(area_id))
            candidates.extend(held)
            for holder in held:
                candidates.extend(self._spatial_items(holder.id))

        for node in candidates:
            props = node.properties or {}
            if props.get("current_state") == "hidden":
                continue
            node_tags = {str(t).lower() for t in (props.get("tags") or [])}
            if want and (want in str(node.name).lower() or want == str(node.id).lower()):
                return node
            if tag_set and (tag_set & node_tags):
                return node
        return None

    # ───────────────────────────── actions ─────────────────────────────────

    def _service_here(self, p, tags):
        """(offered, fixture_item) for a service in the character's area.

        A service can come from the area itself (a latrine room, a river) or
        from a fixture standing in it (a wash spot, a shower). Fixtures are
        standing items, which task-406's on_tick path already supports.
        """
        if not p.current_area:
            return False, None
        area_id = self.gs.area_node_id(p.current_area)
        node = self.gs.graph.get_node(area_id) if area_id else None
        if node is not None and self._has_tag(node, tags):
            return True, None
        if area_id:
            for item in self._spatial_items(area_id):
                if self._has_tag(item, tags):
                    return True, item
        return False, None

    @staticmethod
    def _has_tag(node, tags):
        node_tags = {str(t).lower() for t in (node.properties.get("tags") or [])}
        return bool(set(tags) & node_tags)

    def _relieve(self, p):
        offered, _ = self._service_here(p, RELIEF_TAGS)
        if not offered:
            return False
        p.vitals["Bladder"] = 0
        record(p, self.gs.time_ticks, "act", f"relieved themselves in {p.current_area}",
               why="needs:relieve", area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] relieves themselves.")
        return True

    def _wash(self, p):
        offered, fixture = self._service_here(p, BATH_TAGS)
        if not offered:
            return False
        amount = self._wash_amount(fixture)
        p.vitals["Hygiene"] = max(0, min(100, p.vitals.get("Hygiene", 0) + amount))
        record(p, self.gs.time_ticks, "act", f"washed in {p.current_area}",
               why="needs:wash", area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] washes up.")
        return True

    def _recreate(self, p):
        """Pass the time with something recreational (task-425).

        Entertainment had no recurring source at all: novelty paid once per area
        and once per item, ever, and `ACTIVITY_REGEN` has nothing recreational,
        so a settled goblin's Entertainment decayed to 0 within a day and stayed
        there. An authored fixture is what makes a camp lively.

        The need gate is also the anti-spam: after using one, Entertainment sits
        above the threshold for the better part of a day, so a character does not
        stand at the drum beating it every ten minutes.
        """
        offered, fixture = self._service_here(p, RECREATION_TAGS)
        if not offered:
            return False
        amount = self._fixture_amount(fixture, "entertainment",
                                      default=ENTERTAINMENT_RESTORE)
        p.vitals["Entertainment"] = max(
            0, min(100, p.vitals.get("Entertainment", 0) + amount))
        record(p, self.gs.time_ticks, "act", f"passed the time in {p.current_area}",
               why="needs:entertainment", area=p.current_area, tags=["need"])
        self.gs.add_log_entry(
            f"[{p.name}] finds some entertainment in the {p.current_area}.")
        return True

    def _recuperate(self, p):
        """Rest a while to steady the mind (task-432).

        Sleep is Sanity's main source, but `_tick_sleeping` wakes a character the
        moment Energy is full — *before* it checks any duration — so sleep cannot
        help anybody who is not exhausted, and gating Sanity recovery on Energy
        meant a character whose day costs little Energy never slept and never
        recovered. Resting is duration-based, so it works at full Energy.

        Deliberately a bounded block: `_act` skips anyone mid-activity, so a
        sprawling rest would stop them eating and drinking. One hour is enough to
        matter and short enough to be safe.
        """
        if p.activity:
            return False
        try:
            minutes_per_tick = float(getattr(self.gs, "time_per_tick_minutes", 1) or 1)
        except (TypeError, ValueError):
            minutes_per_tick = 1.0
        duration = max(1, int(round(SANITY_REST_MINUTES / max(0.001, minutes_per_tick))))
        try:
            self.gs.activities.start_activity(p.name, "resting", duration_ticks=duration)
        except Exception:
            return False
        record(p, self.gs.time_ticks, "act", f"rested in {p.current_area}",
               why="needs:sanity", area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] stops to steady themselves.")
        return True

    def _wash_amount(self, fixture, default=BATH_HYGIENE):
        """The Hygiene a fixture grants (kept as a named wrapper for callers)."""
        return self._fixture_amount(fixture, "hygiene", default)

    def _fixture_amount(self, fixture, stat, default):
        """The ``stat`` a fixture grants, read from its authored `adjust_vital`.

        Read rather than hardcoded so the library entry stays the single source
        of truth for how much a fixture helps — the same rule for washing and for
        recreation, so authoring a new fixture needs no engine change.
        """
        if fixture is None:
            return default
        for edge in self.gs.graph.get_edges_for_source(fixture.id):
            if edge.type != "triggers":
                continue
            trigger = self.gs.graph.get_node(edge.target)
            if trigger is None:
                continue
            props = trigger.properties or {}
            candidates = list(props.get("effects") or [])
            if props.get("effect_type"):
                candidates.append({"type": props.get("effect_type"),
                                   "params": props.get("effect_params") or {}})
            for effect in candidates:
                if effect.get("type") != "adjust_vital":
                    continue
                params = effect.get("params") or {}
                if str(params.get("stat", "")).lower() != str(stat).lower():
                    continue
                try:
                    return int(params.get("amount", default))
                except (TypeError, ValueError):
                    return default
        return default

    def _requires_search(self, node) -> bool:
        """True when an item sits inside/on another *item* (a basket, a larder).

        Open-area resources are plain maintenance — a camp that starves beside a
        visible stew is not the game we want. Only something tucked away is a
        Perception check (task-469); carried items are never searched for.
        """
        try:
            for edge in self.gs.graph.edges:
                if edge.source != node.id or edge.type not in self.REACHABLE_RELATIONS:
                    continue
                parent = self.gs.graph.get_node(edge.target)
                if parent is not None and getattr(parent, "type", "") == "item":
                    return True
        except Exception:
            return False
        return False

    def _forage_check(self, p, kind) -> bool:
        """Perception vs a flat DC for spotting food/water in the field.

        A skill check reads the *active* player, so the character is swapped in
        for the roll (the same trick `_travel_toward` uses) and restored after.
        A missing skill system fails open: going hungry should be the exception,
        not the default.
        """
        active = getattr(self.gs, "active_player", None)
        try:
            self.gs.active_player = p.name
            success, _total, _msg = self.gs.skill_check(FORAGE_SKILL, FORAGE_DC)
        except Exception:
            return True
        finally:
            try:
                self.gs.active_player = active
            except Exception:
                pass
        return bool(success)

    def _forage_spawn(self, p, want_tags):
        """A search can turn something up in an area that had nothing (task-471).

        Only areas that can plausibly hold a find yield one (see
        engine/foraging), and the per-area daily cap still applies.
        """
        try:
            from engine.foraging import find_or_spawn, best_skill_for
            skill = best_skill_for(self.gs, p, want_tags)
            return find_or_spawn(self.gs, p, p.current_area, skill=skill,
                                 want_tags=want_tags)
        except Exception as e:
            logger.warning("[background] forage spawn: %s", e)
            return None

    def _has_authored_consume(self, node, trigger_type) -> bool:
        """True when *node* authors an ``on_eat``/``on_drink`` trigger.

        An authored consumable owns its own effect and depletion (bread is
        destroyed, a glass empties and persists). When it does, the background
        tier must run *that* path rather than the hardcoded count/uses/remove.
        """
        try:
            edges = self.gs.graph.get_edges_for_source(node.id, EDGE_TRIGGERS)
        except Exception:
            return False
        for edge in edges:
            tt = (edge.properties or {}).get("trigger_type", "")
            if isinstance(tt, (list, tuple)):
                if trigger_type in tt:
                    return True
            elif tt == trigger_type:
                return True
        return False

    def _consume_via_authored(self, p, node, verb) -> bool:
        """Run the player consume path with *p* swapped into the active slot.

        This is the same trick `_travel_toward`/`_forage_check` use: the authored
        path reads the active player, so the background character is briefly
        active. Returns True when it ran; False lets the caller fall back.
        """
        active = getattr(self.gs, "active_player", None)
        try:
            self.gs.active_player = getattr(p, "name", None)
            if verb == "drink":
                self.gs.item_actions.drink_item(self.gs, node.name)
            else:
                self.gs.item_actions.eat_item(self.gs, node.name)
            return True
        except Exception as e:
            logger.warning("[background] authored %s failed for %s: %s",
                           verb, getattr(p, "name", "?"), e)
            return False
        finally:
            try:
                self.gs.active_player = active
            except Exception:
                pass

    def _consume_here(self, p, tags, kind):
        node = self._find_consumable(p, tags, verb=self._verb_for_need(kind))
        if not node:
            return False
        # Carried food is yours and open-area resources are plain maintenance;
        # only something tucked into a container has to be noticed first
        # (task-469). A miss costs the search time, not the item.
        if self._requires_search(node) and not self._forage_check(p, kind):
            record(p, self.gs.time_ticks, "act",
                   f"searched {p.current_area} for {kind} and found nothing",
                   why="forage:fail", area=p.current_area, tags=["need", "forage"])
            self.gs.add_log_entry(
                f"[{p.name}] searches for {kind} but finds nothing.")
            return "failed"

        verb = "drink" if kind == "drink" else "eat"
        trigger_type = "on_drink" if kind == "drink" else "on_eat"
        # One consumption path (task-424): an authored consumable resolves through
        # the player path, so its triggers fire and it depletes its own way. The
        # hardcoded count/uses/remove below stays only as a fallback for items that
        # author no consumption, and says so in the log.
        if self._has_authored_consume(node, trigger_type):
            if self._consume_via_authored(p, node, verb):
                self._areas_cache.clear()
                self._record_consumption(p, node, kind, restore=False)
                return True

        props = node.properties or {}
        logger.info("[background] %s: %s authors no consume trigger; using the "
                    "hardcoded fallback", getattr(p, "name", "?"), node.name)
        count = props.get("count")
        uses = props.get("uses")
        if isinstance(count, int) and count > 1:
            props["count"] = count - 1
        elif isinstance(uses, (int, float)) and uses > 1:
            props["uses"] = uses - 1
        else:
            self.gs.graph.remove_node(node.id)
        # The set of areas holding a resource changes when the last item in an
        # area is consumed; a stale cache makes characters keep "head toward"
        # their own now-empty area instead of a real source.
        self._areas_cache.clear()

        self._record_consumption(p, node, kind, restore=True)
        return True

    def _record_consumption(self, p, node, kind, *, restore: bool):
        """The need-level trace + log for a background meal.

        ``restore`` applies the hardcoded MEAL_RESTORE/DRINK_RESTORE. It is True
        only on the fallback path: when the item authors its own consumption, its
        ``adjust_vital`` trigger is the one source of truth and applying the
        constant too would double the restore (task-424).
        """
        tick = self.gs.time_ticks
        if kind == "drink":
            if restore:
                p.vitals["Thirst"] = max(0, p.vitals.get("Thirst", 0) - DRINK_RESTORE)
            verb = "drank"
        else:
            if restore:
                p.vitals["Hunger"] = max(0, p.vitals.get("Hunger", 0) - MEAL_RESTORE)
            verb = "ate"
        record(p, tick, "act", f"{verb} {node.name}", why=f"needs:{kind}",
               area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] {verb} the {node.name}.")

    def _sleep(self, p):
        try:
            self.gs.activities.start_activity(p.name, "sleeping")
        except Exception:
            return
        record(p, self.gs.time_ticks, "act", "went to sleep", why="needs:energy",
               area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] settles down to sleep.")

    @staticmethod
    def _verb_for_need(need):
        """The action a search is really for, so a drink is not counted as food.

        Accepts both vocabularies in use: needs are `thirst`/`hunger` and the
        consume kind is `drink`/`eat`.
        """
        return "drink" if str(need).lower() in ("thirst", "drink") else "eat"

    def _hop(self, p, target_name, direction, need=None, tags=None,
             reason=None, depth=0):
        """Cross one way toward *target_name* (task-475).

        Uses the verb the way needs (crawl / climb / jump) and rolls ground that
        is genuinely risky. A refusal costs the turn and nothing more: the way is
        remembered so the next turn routes around it, and one alternative hop is
        tried immediately as a detour.
        """
        from engine import traversal
        area = p.current_area
        why = f"{reason}:travel" if reason else f"needs:{need}"
        result = traversal.hop(self.gs, p, direction)

        if result.ok:
            record(p, self.gs.time_ticks, "move",
                   f"travelled {direction} toward {target_name}",
                   why=why, area=p.current_area, tags=["travel"])
            self.gs.add_log_entry(f"[{p.name}] heads {direction} toward {target_name}.")
            return True

        traversal.note_refusal(self.gs, p, area, direction)
        if result.condition:
            try:
                self.gs.conditions.apply_condition(p.name, result.condition,
                                                   source="traversal")
            except Exception as e:
                logger.warning("[background] %s condition: %s", p.name, e)
        record(p, self.gs.time_ticks, "traversal", result.detail,
               why=result.why, area=area, tags=["travel"])
        self.gs.add_log_entry(
            f"[{p.name}] can't take the {direction} ({result.detail}).")

        # One detour: a different first hop toward the same goal, now that the
        # refused way is on the avoid list.
        if depth == 0:
            step = self._target_step(
                p, tags, verb=self._verb_for_need(need) if need else None,
                areas={target_name} if not tags else None,
                avoid=traversal.avoid(self.gs, p))
            if step:
                alt_name, alt_dir = step
                if alt_dir and alt_dir != direction:
                    return self._hop(p, alt_name, alt_dir, need=need, tags=tags,
                                     reason=reason, depth=1)
        return False

    def _travel_toward(self, p, tags, need):
        from engine import traversal
        step = self._target_step(p, tags, verb=self._verb_for_need(need),
                                 avoid=traversal.avoid(self.gs, p))
        if not step:
            return False
        target_name, direction = step
        if not direction:
            return False
        return self._hop(p, target_name, direction, need, tags)

    def _pursue_schedule(self, p):
        """Walk to and carry out the step the clock is in (task-409).

        This is what a character does with time that no survival need claims:
        go to the place its day says it should be, and get on with it. It runs
        *after* every survival need, so a smith still breaks off to eat, drink or
        sleep, and *before* boredom, so a full character works rather than
        milling about.

        Returns True when it did something, so `_act` stops for this decision.
        """
        from engine.schedule import BLOCKING_ACTIVITIES, current_step, minutes_of_day
        if not getattr(p, "schedule", None):
            return False
        step = current_step(p.schedule, minutes_of_day(self.gs))
        if not step:
            return False

        # Get there first. Standing in the wrong room and "working" is no day.
        area = step.get("area")
        if area and p.current_area != area:
            return self._travel_to_area(p, area, "schedule")

        activity = BLOCKING_ACTIVITIES.get(step["activity"])
        if activity:
            return self._start_blocking_activity(p, activity, step["activity"],
                                                 WORK_MINUTES)
        # `socialise`, `patrol`, `guard` and `roam` need nothing beyond being
        # present: company is handled by the social pass, and the others are
        # satisfied by the travel itself.
        return False

    def _travel_to_area(self, p, area_name, reason):
        """One hop toward a *named* area, reusing the need-travel path."""
        from engine import traversal
        step = self._target_step(p, None, areas={area_name},
                                 avoid=traversal.avoid(self.gs, p))
        if not step:
            return False
        target_name, direction = step
        if not direction:
            return False
        return self._hop(p, target_name, direction, reason=reason)

    def _start_blocking_activity(self, p, activity, reason, minutes):
        """Start a short, interruptible activity expressed in GAME MINUTES.

        Short is the point: `_act` skips anyone mid-activity, so the duration is
        the longest a character can go without eating, drinking or relieving
        itself. Long blocks are tick-length traps too — one that rounds to a
        single tick at 15 min/tick looks harmless and is not.
        """
        if p.activity:
            return False
        try:
            minutes_per_tick = float(getattr(self.gs, "time_per_tick_minutes", 1) or 1)
        except (TypeError, ValueError):
            minutes_per_tick = 1.0
        duration = max(1, int(round(minutes / max(0.001, minutes_per_tick))))
        try:
            self.gs.activities.start_activity(p.name, activity, duration_ticks=duration)
        except Exception:
            return False
        record(p, self.gs.time_ticks, "act", f"{reason} in {p.current_area}",
               why=f"schedule:{reason}", area=p.current_area, tags=["schedule"])
        self.gs.add_log_entry(f"[{p.name}] gets on with {reason}.")
        return True

    # ───────────────────────────── lookups ─────────────────────────────────

    #: Spatial relations a forager can reach *through*. An area holds things in,
    #: on, under, behind, beside or at it, and an item can hold the same ways —
    #: berries in a bush, bread on a table, a pouch beside a log.
    REACHABLE_RELATIONS = ("in", "on", "under", "behind", "beside", "at")

    def _spatial_items(self, container_id):
        """Items *container_id* holds by any spatial relation."""
        graph = self.gs.graph
        for rel in self.REACHABLE_RELATIONS:
            for edge in graph.get_edges_for_target(container_id, rel):
                node = graph.get_node(edge.source)
                if node is not None and node.type == "item":
                    yield node

    def _find_consumable(self, p, tags, depth=1, verb=None):
        """Nearest edible thing the character can actually reach.

        Carried first, then anything the area holds by a spatial relation, then
        ONE level into what those hold. Before this it only looked at items with
        an ``in`` edge to the area, so food in a container — berries on a bush, a
        larder, a basket — was invisible and the background tier could starve
        beside a full store.
        """
        graph = self.gs.graph
        player_id = self.gs._player_node_id(p.name)
        area_id = (self.gs.area_node_id(p.current_area)
                   if p.current_area else None)
        # carried items first
        for e in graph.edges:
            if e.type == EDGE_CARRYING and e.target == player_id:
                node = graph.get_node(e.source)
                if node and self._is_consumable(node, tags, verb):
                    return node
        if not area_id:
            return None
        for node in self._spatial_items(area_id):
            if self._is_consumable(node, tags, verb):
                return node
        if depth > 0:
            for holder in self._spatial_items(area_id):
                for node in self._spatial_items(holder.id):
                    if self._is_consumable(node, tags, verb):
                        return node
        return None

    def _is_consumable(self, node, tags, verb=None):
        """Can this node satisfy the search?

        The tag branch is inherently intent-specific (FOOD_TAGS vs DRINK_TAGS).
        The action branch must be too: it used to accept an item carrying EITHER
        an `eat` or a `drink` action, so a hungry character would eat a water
        skin and Hunger was satisfied.
        """
        props = node.properties or {}
        if props.get("current_state") == "hidden":
            return False
        # A spent container is not a free refill (task-424): `uses == 0` means
        # empty, so it cannot satisfy a need until it is refilled.
        if props.get("uses", -1) == 0:
            return False
        node_tags = {str(t).lower() for t in (props.get("tags", []) or [])}
        if set(tags) & node_tags:
            return True
        if not verb:
            return False
        actions = props.get("actions", [])
        if isinstance(actions, str):
            actions = [a.strip() for a in actions.split(",")]
        return verb in {str(a).lower() for a in (actions or [])}

    # ── navigation ────────────────────────────────────────────────────────
    # Way edges in the scenario reference sanitized area ids (e.g.
    # "area_chiefs_pit") while the area node id keeps the apostrophe
    # ("area_chief's_pit"), so strict-id pathfinding returns None from most
    # areas. Resolve both endpoints by normalized name instead.

    @staticmethod
    def _norm(text):
        return "".join(ch for ch in str(text).lower() if ch.isalnum())

    def _norm_area_table(self):
        if getattr(self, "_area_table", None) is not None:
            return self._area_table
        table = {}
        for node in self.gs.graph.nodes.values():
            if node.type != "area":
                continue
            table[self._norm(node.name)] = node.id
            key = self._norm(node.id)
            table[key] = node.id
            if key.startswith("area"):
                table[key[4:]] = node.id
        self._area_table = table
        return table

    def _resolve_area_id(self, area_id_or_name):
        if not area_id_or_name:
            return None
        node = self.gs.graph.get_node(area_id_or_name)
        if node and node.type == "area":
            return node.id
        return self._norm_area_table().get(self._norm(area_id_or_name))

    def _target_step(self, p, tags, verb=None, areas=None, avoid=None):
        """Nearest area holding ``tags`` reachable from the character's area.

        Returns ``(area_name, exit_label)`` or None. BFS walks the engine's own
        exits (``include_hidden=True`` so authoring-hidden passages still
        connect), which guarantees the returned label is one
        ``movement.move_to_area`` will accept.

        ``areas`` overrides the tag lookup with an explicit set of area names —
        what a schedule needs, since a step names its destination directly rather
        than describing it by tags (task-409). ``avoid`` is a set of
        ``(area, label)`` keys the character is routing around for now, so a way
        that just turned them back is not retried every turn (task-475).
        """
        areas = set(areas) if areas else self._areas_with(tags, verb)
        start = p.current_area
        if not start or not areas:
            return None
        seen = {start}
        queue = deque([(start, None)])
        while queue:
            current, first = queue.popleft()
            # Never treat the current area as a travel target: _act already
            # tried to consume/water here, so travel only makes sense to a
            # different area (otherwise we'd return a None direction and stall).
            if current in areas and current != start:
                return current, first
            for label, exit_data in self.gs.build_exits_for_area(
                    current, include_hidden=True).items():
                if avoid:
                    from engine.traversal import avoid_key
                    if avoid_key(current, label) in avoid:
                        continue
                target = exit_data.get("target")
                if target and target not in seen:
                    seen.add(target)
                    queue.append((target, first or label))
        return None

    def _in_water_area(self, p):
        """True if the character's area is itself a water source (natural
        water is modelled as an area tag, not an item)."""
        if not p.current_area:
            return False
        node = self.gs.graph.get_node(self._resolve_area_id(p.current_area))
        if not node:
            return False
        ntags = {str(t).lower() for t in (node.properties.get("tags", []) or [])}
        return "water" in ntags

    def _areas_with(self, tags, verb=None):
        """Areas from which the character could satisfy this need.

        Reaches into containers exactly like `_find_consumable` does: a berry on
        a bush makes the forest a food area, otherwise nobody would ever travel
        to where the renewed supply actually is.
        """
        key = (tuple(tags), verb)
        if key in self._areas_cache:
            return self._areas_cache[key]
        areas = set()
        want = {str(t).lower() for t in tags}
        for node in self.gs.graph.nodes.values():
            if node.type != "area":
                continue
            # an area can itself be the resource (water sources, larders)
            ntags = {str(t).lower() for t in (node.properties.get("tags", []) or [])}
            if want & ntags:
                areas.add(node.name)
                continue
            for held in self._spatial_items(node.id):
                if self._is_consumable(held, tags, verb):
                    areas.add(node.name)
                    break
                if any(self._is_consumable(inner, tags, verb)
                       for inner in self._spatial_items(held.id)):
                    areas.add(node.name)
                    break
        self._areas_cache[key] = areas
        return areas
