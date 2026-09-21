"""Deterministic background survival runner (task-399).

Characters with ``simulation_mode == "background"`` do not run the LLM loop.
Instead this module makes *coarse, deterministic* decisions against the
**same** Player/graph state so the character stays the same person (see
docs/design/reversibility-contract.md).

Decisions are paced by an **action credit** measured in game minutes, not
ticks: a character is entitled to one decision per ``DECISION_MINUTES`` of
game time, and a tick grants ``time_per_tick_minutes / DECISION_MINUTES`` of
credit. At 1 min/tick that is one decision per 10 ticks (the old fixed
interval); at 15 min/tick it is ~1.5 decisions per tick, so a character takes
the same number of decisions per game hour whatever the tick length. Gating on
ticks instead meant a 15-minute world gave everyone a fifteenth as many
decisions per hour and they starved while food was in reach.

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

from graph import EDGE_IN, EDGE_CARRYING
from engine.trace import record
from vital_rates import tick_minutes

logger = logging.getLogger(__name__)

FOOD_TAGS = ("food", "eat", "edible", "meal")
DRINK_TAGS = ("drink", "water", "beverage")

THIRST_THRESHOLD = 45     # drive: high = parched; act before it gets urgent
HUNGER_THRESHOLD = 50     # drive: high = starving
ENERGY_THRESHOLD = 30     # resource: low = tired
BLADDER_THRESHOLD = 60    # drive: high = needs to go; well before it maxes at 100
HYGIENE_THRESHOLD = 40    # resource: low = filthy; go wash
ENTERTAINMENT_THRESHOLD = 40  # resource: low = bored; go do something
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

DECISION_MINUTES = 10     # game minutes between background decisions
MAX_ACTIONS_PER_TICK = 4  # bound so a very long tick cannot run away


class BackgroundSimulation:
    """Runs due background characters. Owned by the engine, called each tick."""

    def __init__(self, game_state):
        self.gs = game_state
        self._areas_cache = {}

    # ───────────────────────────── entry point ─────────────────────────────

    def process_due(self):
        """Spend each background character's accrued action credit.

        Credit accrues in game minutes, so the number of decisions per game
        hour is the same at any ``time_per_tick_minutes``. A character who is
        mid-activity (sleeping) or unconscious neither decides nor banks
        credit, so a long sleep cannot leave a backlog to dump on waking.
        """
        gain = tick_minutes(self.gs) / DECISION_MINUTES
        for name, p in list(self.gs.players.items()):
            if getattr(p, "simulation_mode", "active") != "background":
                continue
            if p.state == "dead":
                continue
            if p.activity or p.state == "unconscious":
                continue  # committed to a duration; no decisions, no banking

            credit = getattr(p, "_action_credit", None)
            if credit is None:
                # First sighting: act at once (the old next_due_tick == 0 path),
                # unless a save/tool set an explicit "not before" tick. Starting
                # at a random fraction instead would both delay the first
                # decision and permanently shorten every later interval.
                credit = 0.0 if self.gs.time_ticks < getattr(p, "next_due_tick", 0) else 1.0
            credit = min(credit + gain, MAX_ACTIONS_PER_TICK)

            spent = 0
            while credit >= 1.0 and spent < MAX_ACTIONS_PER_TICK:
                try:
                    self._act(name, p)
                except Exception as e:  # never let one character stall the tick
                    logger.warning("[background] %s: %s", name, e)
                    break
                credit -= 1.0
                spent += 1
                if p.activity or p.state == "unconscious":
                    break  # a duration started; stop spending this tick
            p._action_credit = credit

        # Social pass last (task-423): after everyone has moved and acted, so a
        # conversation happens where the characters actually ended up. Pairs per
        # area, once per tick, and gives both sides a short conversing activity —
        # which is why the loop above skips anyone mid-activity.
        try:
            from engine.background_social import run_social_pass
            run_social_pass(self.gs)
        except Exception as e:
            logger.warning("[background] social pass: %s", e)

    # ───────────────────────────── decisions ───────────────────────────────

    def _act(self, name, p):
        if p.activity:
            return  # mid-activity (e.g. sleeping) — leave them to it
        if p.state == "unconscious":
            return  # collapsed; the engine's recovery path handles waking

        v = p.vitals
        thirst = v.get("Thirst", 0)
        hunger = v.get("Hunger", 0)
        energy = v.get("Energy", 100)

        # Critical exhaustion wins over everything: without this, a character
        # chasing water they can't reach never sleeps and dies of exhaustion
        # (the exact failure the 2-day soak showed).
        if energy <= 15:
            self._sleep(p)
            return

        if thirst >= THIRST_THRESHOLD:
            # The scenario models natural water as an AREA tag ("water") you
            # drink from by standing in it, not as an item to consume.
            if self._in_water_area(p):
                p.vitals["Thirst"] = max(0, p.vitals.get("Thirst", 0) - DRINK_RESTORE)
                record(p, self.gs.time_ticks, "act",
                       f"drank from {p.current_area}", why="needs:drink",
                       area=p.current_area, tags=["need"])
                self.gs.add_log_entry(f"[{p.name}] drinks from {p.current_area}.")
                return
            if self._consume_here(p, DRINK_TAGS, "drink"):
                return
            if self._travel_toward(p, DRINK_TAGS, "thirst"):
                return
            return

        if energy <= ENERGY_THRESHOLD:
            self._sleep(p)
            return

        if hunger >= HUNGER_THRESHOLD:
            if self._consume_here(p, FOOD_TAGS, "eat"):
                return
            if self._travel_toward(p, FOOD_TAGS, "hunger"):
                return

        if v.get("Bladder", 0) >= BLADDER_THRESHOLD:
            if self._relieve(p):
                return
            if self._travel_toward(p, RELIEF_TAGS, "bladder"):
                return
            # Nowhere to go. The engine already docks Hygiene when the meter
            # maxes, which is the honest outcome for a camp with no latrine.
            return

        if v.get("Hygiene", 100) <= HYGIENE_THRESHOLD:
            if self._wash(p):
                return
            if self._travel_toward(p, BATH_TAGS, "hygiene"):
                return

        # Steadying the mind. Above boredom because a low-Sanity character is a
        # danger to others rather than merely unhappy, but below every survival
        # need: nothing here kills you.
        if v.get("Sanity", 100) <= SANITY_THRESHOLD:
            if self._recuperate(p):
                return

        # Boredom last: it is the only need here that nothing kills you for
        # ignoring, so it must never outrank food, water, sleep or relief.
        if v.get("Entertainment", 100) <= ENTERTAINMENT_THRESHOLD:
            if self._recreate(p):
                return
            if self._travel_toward(p, RECREATION_TAGS, "entertainment"):
                return

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

    def _consume_here(self, p, tags, kind):
        node = self._find_consumable(p, tags, verb=self._verb_for_need(kind))
        if not node:
            return False
        props = node.properties or {}
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

        tick = self.gs.time_ticks
        if kind == "drink":
            p.vitals["Thirst"] = max(0, p.vitals.get("Thirst", 0) - DRINK_RESTORE)
            verb = "drank"
        else:
            p.vitals["Hunger"] = max(0, p.vitals.get("Hunger", 0) - MEAL_RESTORE)
            verb = "ate"
        record(p, tick, "act", f"{verb} {node.name}", why=f"needs:{kind}",
               area=p.current_area, tags=["need"])
        self.gs.add_log_entry(f"[{p.name}] {verb} the {node.name}.")
        return True

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

    def _travel_toward(self, p, tags, need):
        step = self._target_step(p, tags, verb=self._verb_for_need(need))
        if not step:
            return False
        target_name, direction = step
        if not direction:
            return False
        old_active = self.gs.active_player
        self.gs.active_player = p.name
        try:
            self.gs.movement.move_to_area(direction)
        except Exception as e:
            logger.warning("[background] travel %s (%s): %s", p.name, direction, e)
            return False
        finally:
            self.gs.active_player = old_active
        record(p, self.gs.time_ticks, "move",
               f"travelled {direction} toward {target_name}",
               why=f"needs:{need}", area=p.current_area, tags=["travel"])
        self.gs.add_log_entry(f"[{p.name}] heads {direction} toward {target_name}.")
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

    def _target_step(self, p, tags, verb=None):
        """Nearest area holding ``tags`` reachable from the character's area.

        Returns ``(area_name, exit_label)`` or None. BFS walks the engine's own
        exits (``include_hidden=True`` so authoring-hidden passages still
        connect), which guarantees the returned label is one
        ``movement.move_to_area`` will accept.
        """
        areas = self._areas_with(tags, verb)
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
