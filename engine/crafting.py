"""Crafting & recipe system (task-2; recipe-entry shape: task-831).

Recipes are data entries, NEVER graph nodes. Graph nodes are physical
entities (items, characters, areas, ways); knowledge lives ON things. The
canonical home is ``data/library/recipes/<id>.json``; a recipe may also ride
on an item's properties (cookbook, recipe note) or in a character's
``crafting_known`` store. The ``type: recipe`` node lookup below
(``recipe_nodes`` / ``_find_recipe``) is TECH DEBT retained for the existing
tests - new code reads the registry, and new recipes are authored as entries.

A recipe entry declares:

.. code-block:: json
   {
     "id": "fried_eggs",
     "name": "Fried Eggs",
     "ingredients": [{"item": "egg", "count": 1, "consumed": true},
                     {"item": "pan", "count": 1, "consumed": false}],
     "conditions": [{"type": "state_equals", "target": "oven", "value": "on"}],
     "duration_min": 10,
     "outputs": [{"item": "fried_egg", "count": 1}],
     "outcomes": {"crit_success": {...}, "success": {...},
                  "fail": {...}, "crit_fail": {...}},
     "skill_check": {"skill": "Cooking", "dc": 10},
     "learned_by": ["global"],
     "discoverable": true
   }

Learning (any of): ``global`` (everyone), ``skill:<name>`` (character has the
skill at level >= 1), ``item:<name>`` (character carries an item whose name or
id matches). ``discoverable`` records the recipe in the character's
``crafting_known`` list after the first successful craft (persisted via player
serialization).

Conditions are evaluated through the shared trigger-condition leaves; the
documented recipe-safe set: ``state_equals`` (target node NAME or id),
``has_item`` (player inventory), ``random_chance``. Unknown condition types
fail closed.

Inputs are matched carrying-first, then the current area (reachable items).
``consumed: true`` inputs are eaten: one use if the item tracks uses, the
whole node otherwise. Outputs are hydrated from the item library via the
``give_item`` effect (lands in the player's hands/inventory) - so output
``item`` values are library ids.
"""

import json
import os
import random as _random
import re

#: Tier names the check degree maps to. ``strong_success`` is a success
#: degree (margin >= 5), not a fifth outcome - it shares the success
#: outputs. ``auto_fail`` (a condition prevents the attempt) fails.
TIER_MAP = {
    "crit_fail": "crit_fail",
    "crit_success": "crit_success",
    "fail": "fail",
    "auto_fail": "fail",
    "success": "success",
    "strong_success": "success",
}

OUTCOME_TIERS = ("crit_success", "success", "fail", "crit_fail")


def _default_recipe_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "data", "library", "recipes")


def load_registry(directory=None) -> dict:
    """Read every ``<id>.json`` recipe entry into ``{id: entry}``.

    Lightweight by design: presence and shape (dict with ``id``) only.
    The full contract lives in ``tools/recipe_check.py`` - the engine
    reads what the gate has already approved, and skips what it cannot
    parse rather than refusing to craft anything.
    """
    directory = directory or _default_recipe_dir()
    out = {}
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, name), encoding="utf-8") as f:
                entry = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(entry, dict) and entry.get("id"):
            out[str(entry["id"])] = entry
    return out


class CraftingSystem:
    def __init__(self, graph, player_manager, trigger_system, effects, game_state=None, recipe_dir=None):
        self.graph = graph
        self.player_manager = player_manager
        self.trigger_system = trigger_system
        self.effects = effects
        self.world = game_state
        self.recipe_dir = recipe_dir
        #: Injectable dice for tests: ``roll_fn() -> int`` (a d20 face).
        #: ``None`` rolls for real. Threaded into the tier check only.
        self.roll_fn = None

    # ────────────────────────── lookup ──────────────────────────

    def _registry(self) -> dict:
        return load_registry(self.recipe_dir)

    def recipe_nodes(self):
        """Retired (task-831): recipes are registry entries, never nodes."""
        return []

    def _find_recipe(self, recipe_name):
        def norm(text):
            return "_".join(
                re.sub(r"[^a-z0-9]+", " ", str(text).lower()).split())
        needle = norm(recipe_name)
        for entry in self._registry().values():
            if not isinstance(entry, dict):
                continue
            if needle in norm(entry.get("name", "")) or \
                    needle in norm(entry.get("id", "")):
                return entry
        return None

    def _recipe_learned(self, player, entry) -> bool:
        props = entry if isinstance(entry, dict) else {}
        learned_by = props.get("learned_by", [])
        if isinstance(learned_by, str):
            learned_by = [learned_by]
        for rule in learned_by:
            rule = str(rule).strip()
            if rule == "global":
                return True
            if rule.startswith("skill:"):
                skill_name = rule[6:].strip()
                known = player.crafting_known or []
                if skill_name in known:
                    return True
                player_skills = getattr(player, "skills", {}) or {}
                if isinstance(player_skills, dict) and int(player_skills.get(skill_name, 0) or 0) >= 1:
                    return True
            if rule.startswith("item:"):
                if self._carries_item(player, rule[5:].strip()):
                    return True
        return str(entry.get("id", "")) in (player.crafting_known or []) or \
            str(entry.get("name", "")) in (player.crafting_known or [])

    def _carries_item(self, player, needle: str) -> bool:
        """Whether *player* carries/equips an item matching *needle*."""
        needle = str(needle or "").strip().lower()
        if not needle:
            return False
        player_id_getter = getattr(self.player_manager, "get_player_node_id", None) or getattr(self.player_manager, "_player_node_id", None)
        if player_id_getter is None:
            return False
        player_id = player_id_getter(player.name)
        from graph import EDGE_CARRYING, EDGE_EQUIPPED
        for edge in self.graph.get_edges_for_target(player_id, (EDGE_CARRYING, EDGE_EQUIPPED)):
            n = self.graph.get_node(edge.source)
            if n and (needle in n.name.lower() or needle in n.id.lower()):
                return True
        return False

    def _recipe_source(self, player, entry) -> str | None:
        """Why *player* knows *entry*: global/skill/cookbook/taught/discovered.

        First matching rule wins. A name in ``crafting_known`` reads as
        "discovered" for discoverable recipes (learned by doing) and
        "taught" otherwise (someone must have taught it).
        """
        learned_by = entry.get("learned_by", []) if isinstance(entry, dict) else []
        if isinstance(learned_by, str):
            learned_by = [learned_by]
        for rule in learned_by:
            if str(rule).strip() == "global":
                return "global"
        for rule in learned_by:
            rule = str(rule).strip()
            if rule.startswith("skill:"):
                skill_name = rule[6:].strip()
                known = player.crafting_known or []
                if skill_name in known:
                    return "skill"
                player_skills = getattr(player, "skills", {}) or {}
                if isinstance(player_skills, dict) and int(player_skills.get(skill_name, 0) or 0) >= 1:
                    return "skill"
        for rule in learned_by:
            rule = str(rule).strip()
            if rule.startswith("item:") and self._carries_item(player, rule[5:].strip()):
                return "cookbook"
        known = player.crafting_known or []
        if str(entry.get("id", "")) in known or str(entry.get("name", "")) in known:
            return "discovered" if entry.get("discoverable") else "taught"
        return None

    def known_recipes(self, player_name: str) -> list:
        """One projection per character (task-841): id, name, source,
        skill, dc, duration. No new stores - registry + knowledge read."""
        player = self.player_manager.players.get(player_name)
        if not player:
            return []
        out = []
        for entry in self._registry().values():
            if not isinstance(entry, dict):
                continue
            source = self._recipe_source(player, entry)
            if source is None:
                continue
            skill = entry.get("skill_check", {}) or {}
            out.append({
                "id": entry.get("id", ""),
                "name": entry.get("name", entry.get("id", "")),
                "source": source,
                "skill": skill.get("skill"),
                "dc": int(skill.get("dc", 10)),
                "duration_min": int(entry.get("duration_min", 0) or 0),
                # Ingredient names for prompt guidance (the prompt
                # builder matches these against carried/area items;
                # the backend re-resolves leniently, so this is
                # guidance, never enforcement).
                "ingredients": [
                    {"item": str(i.get("item", "")),
                     "count": int(i.get("count", 1) or 1)}
                    for i in (entry.get("ingredients",
                                        entry.get("inputs", [])) or [])
                    if isinstance(i, dict) and str(i.get("item", "")).strip()
                ],
            })
        out.sort(key=lambda r: str(r["name"]).lower())
        return out

    def _recipe_known_names(self, player_name) -> list:
        player = self.player_manager.players.get(player_name)
        if not player:
            return []
        out = []
        for entry in self._registry().values():
            if isinstance(entry, dict) and self._recipe_learned(player, entry):
                out.append(entry.get("name", entry.get("id", "")))
        return out

    # ────────────────────────── craft ──────────────────────────

    def _pid(self, player_manager, name):
        getter = getattr(player_manager, "get_player_node_id", None) or getattr(player_manager, "_player_node_id", None)
        if getter is None:
            return None
        return getter(name)

    def _input_nodes(self, player_manager, item_needle):
        """Carrying/equipped first, then reachable area items."""
        player_id = self._pid(player_manager, player_manager.active_player)
        if player_id is None:
            return []
        needle = str(item_needle).lower()
        picked = []
        from graph import EDGE_CARRYING, EDGE_EQUIPPED
        for edge in self.graph.get_edges_for_target(player_id, (EDGE_CARRYING, EDGE_EQUIPPED)):
            n = self.graph.get_node(edge.source)
            if n and n.type == "item" and (needle in n.name.lower() or needle in n.id.lower()):
                picked.append(n)
        if not picked:
            try:
                from engine.item_reach import find_reachable
                matching = getattr(self.world, "matching", None) or getattr(self.world, "name_matcher", None)
                if matching is not None:
                    n = find_reachable(self.graph, matching, player_manager, item_needle)
                    if n:
                        picked.append(n)
            except Exception:
                pass
        return picked

    def _consume_input(self, player_manager, item_node, count: int):
        """Consume *count* units of an input (one use at a time, else remove)."""
        from engine.items.carry_weight import reconcile_item_weight
        for _ in range(max(1, count)):
            uses = int(item_node.properties.get("uses", -1) or 0)
            if uses > 0:
                item_node.properties["uses"] = uses - 1
                reconcile_item_weight(item_node)
                if item_node.properties["uses"] <= 0:
                    player_id = self._pid(player_manager, player_manager.active_player)
                    for edge in list(self.graph.edges):
                        if edge.source == item_node.id or edge.target == item_node.id:
                            self.graph.edges.remove(edge)
                    self.graph.remove_node(item_node.id)
                    return
            else:
                player_id = self._pid(player_manager, player_manager.active_player)
                for edge in list(self.graph.edges):
                    if edge.source == item_node.id or edge.target == item_node.id:
                        self.graph.edges.remove(edge)
                self.graph.remove_node(item_node.id)
                return

    def _spawn_outputs(self, player_manager, outputs) -> list:
        msgs = []
        for out in outputs:
            item_id = out.get("item", "") if isinstance(out, dict) else str(out)
            count = int(out.get("count", 1)) if isinstance(out, dict) else 1
            if not item_id:
                continue
            for _ in range(max(1, count)):
                try:
                    results = self.effects.handle_give_item(
                        {"item_id": item_id, "target": "self"},
                        context={},
                        game_state=self.world,
                    )
                    msgs.extend(results if isinstance(results, list) else [results])
                except Exception as e:  # noqa: BLE001 - a bad output shouldn't kill the craft
                    msgs.append(f"The {item_id} fails to materialize: {e}")
        return msgs

    def _condition_passes(self, cond: dict, player) -> bool:
        ctype = (cond or {}).get("type", "")
        if ctype == "state_equals":
            target_name = cond.get("target", "")
            if not target_name:
                return False
            needle = str(target_name).lower()
            for node_id, node in self.graph.nodes.items():
                if needle in node.name.lower() or needle in node_id.lower():
                    return str(node.properties.get("current_state", "")) == str(cond.get("value", ""))
            return False
        if ctype == "has_item":
            return bool(self._input_nodes(self.player_manager, cond.get("item") or cond.get("value") or ""))
        if ctype == "random_chance":
            import random
            try:
                return random.random() < (float(cond.get("value", 0)) / 100.0)
            except (TypeError, ValueError):
                return False
        if ctype == "skill_check":
            skill = cond.get("skill", "Athletics")
            dc = int(cond.get("dc", 10))
            try:
                success, _, _ = self.player_manager.skill_check(skill, dc)
            except Exception:
                success = False
            return success
        # fail closed for anything else - crafting gates must be explicit
        return False

    def teach(self, player_manager, student_name: str, subject: str) -> str:
        """task-197: teach a recipe or skill to another character (same area).

        ``subject`` is either a recipe name or ``"skill:<name>"``. The teacher
        (the acting character) must actually know the subject; a skill lesson
        bumps the student's skill by 1.
        """
        teacher_name = player_manager.active_player
        teacher = player_manager.players.get(teacher_name)
        student = player_manager.players.get(student_name)
        if not student:
            raise ValueError(f"There's no one named '{student_name}' here.")
        if teacher_name == student_name:
            raise ValueError("You already know everything you could teach yourself.")
        if student.current_area != teacher.current_area:
            raise ValueError(f"{student_name} isn't here - they can't learn that from you.")

        subject = str(subject or '').strip()
        if subject.lower().startswith('skill:'):
            skill_name = subject[6:].strip()
            teacher_skills = getattr(teacher, 'skills', {}) or {}
            if int(teacher_skills.get(skill_name, 0) or 0) < 1:
                raise ValueError(f"You don't know '{skill_name}' well enough to teach it.")
            student_skills = dict(getattr(student, 'skills', {}) or {})
            student_skills[skill_name] = int(student_skills.get(skill_name, 0) or 0) + 1
            student.skills = student_skills
            return f"You spend a while going over the basics with {student_name} - they gain a bit of {skill_name}."

        recipe = self._find_recipe(subject)
        if recipe is None:
            raise ValueError(f"You don't know any recipe called '{subject}'.")
        if not self._recipe_learned(teacher, recipe):
            raise ValueError(f"You don't know how to make '{recipe.get('name', subject)}'.")
        known = list(getattr(student, 'crafting_known', []) or [])
        if recipe.get("name") in known:
            return f"{student_name} already knows how to make {recipe.get('name')}."
        known.append(recipe.get("name", subject))
        student.crafting_known = known
        return f"You walk {student_name} through it - they now know how to make {recipe.get('name')}."

    def resolve_craft_tier(self, entry: dict, player) -> tuple:
        """Roll a recipe's check and map the degree to a tier (task-840 Q5).

        The seam a future minigame replaces: staged rolls feed the same
        four tiers. Returns ``(tier, check_message)``; one roll through
        the shared pipeline, so tier and success agree by construction.
        """
        return self._resolve_tier(player, entry)

    def check_craft(self, player_manager, recipe_name: str) -> dict:
        """Fail-closed requirement check (task-840): find, learned,
        inputs present, conditions met. Raises naming the gap; rolls
        nothing, consumes nothing, spawns nothing."""
        entry = self._find_recipe(recipe_name)
        if entry is None:
            raise ValueError(f"You don't know any recipe for '{recipe_name}'.")
        player = player_manager.players.get(player_manager.active_player)
        if not player:
            raise ValueError("No active character.")
        if not self._recipe_learned(player, entry):
            raise ValueError(f"You don't know how to craft '{entry.get('name', recipe_name)}'.")
        recipe_label = entry.get("name", recipe_name)
        self._verify_inputs(player_manager, entry, recipe_label)
        for cond in entry.get("conditions", []) or []:
            if not self._condition_passes(cond, player):
                raise ValueError(f"The conditions to craft '{recipe_label}' aren't met.")
        return entry

    def _verify_inputs(self, player_manager, entry: dict, recipe_label: str) -> list:
        """Return the entry's inputs, raising on the first gap."""
        inputs = entry.get("ingredients", entry.get("inputs", []))
        if isinstance(inputs, str):
            raise ValueError("Recipe inputs must be a JSON list.")
        for inp in inputs:
            needed = inp.get("item", "") if isinstance(inp, dict) else str(inp)
            count = int(inp.get("count", 1)) if isinstance(inp, dict) else 1
            nodes = self._input_nodes(player_manager, needed)
            total = sum(max(1, int(n.properties.get("uses", -1) or 0)) for n in nodes) if nodes else 0
            if not nodes or (count > 1 and total < count):
                raise ValueError(f"You need {count} {needed} and don't have them.")
        return inputs

    def start_cooking(self, player_manager, recipe_name: str) -> str:
        """Begin a timed cooking Activity (task-840 Q2), or resolve
        instantly when the recipe has no duration. Check-first: a
        missing list fails closed before anything starts."""
        entry = self.check_craft(player_manager, recipe_name)
        minutes = entry.get("duration_min", 0) or 0
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 0
        if minutes <= 0:
            return self.craft(player_manager, recipe_name)
        player = player_manager.players.get(player_manager.active_player)
        recipe_label = entry.get("name", recipe_name)
        self.world.activities.start_activity(
            player.name, "cooking", duration_minutes=float(minutes),
            recipe_id=entry.get("id", recipe_name))
        return (f"You start cooking {recipe_label.lower()} "
                f"({minutes} min) - interruption ends it with nothing "
                f"consumed and the pot waiting.")

    def complete_cooking(self, player_manager, player_name: str,
                           recipe_ref: str = "") -> str:
        """Finish a cooking Activity: recheck, tier-roll, consume, spawn.

        Called by the Activity completion path (``finish_craft``). A
        missing recipe, eaten inputs, or an unlit fire since fail
        closed with nothing consumed and nothing spawned.
        """
        player = player_manager.players.get(player_name)
        if not player:
            return "No cook to finish for."
        if not recipe_ref:
            activity = getattr(player, "activity", None) or {}
            recipe_ref = activity.get("recipe_id") or ""
        entry = self._find_recipe(recipe_ref) if recipe_ref else None
        if entry is None:
            return "The recipe is gone - nothing to finish."
        recipe_label = entry.get("name", recipe_ref)
        try:
            self._verify_inputs(player_manager, entry, recipe_label)
        except ValueError as e:
            return f"{e} The pot waits."
        for cond in entry.get("conditions", []) or []:
            if not self._condition_passes(cond, player):
                return (f"The conditions to craft '{recipe_label}' aren't "
                        f"met anymore. The pot waits.")
        tier, check_message = self.resolve_craft_tier(entry, player)
        return self._finish(player_manager, player, entry, recipe_label,
                            tier, check_message)

    def _finish(self, player_manager, player, entry: dict,
                recipe_label: str, tier: str, check_message: str) -> str:
        """Consume per the tier flag, spawn the tier outputs, report."""
        outcomes = entry.get("outcomes", {}) or {}
        outcome = outcomes.get(tier, {}) or {}
        if tier in ("fail", "crit_fail"):
            consume = bool(outcome.get("consume_inputs", True))
        else:
            consume = True
        # The tier's own outputs win; absent means the top-level success
        # default (back-compat with pre-outcome recipes). An explicit
        # empty list stays empty (pot boiled dry - nothing spawns).
        if tier in outcomes and "outputs" in outcome:
            tier_outputs = outcome.get("outputs") or []
        else:
            tier_outputs = entry.get("outputs", []) or []
        inputs = entry.get("ingredients", entry.get("inputs", [])) or []

        # consume inputs (consumed flag, gated by the tier's consume flag)
        if consume:
            for inp in inputs:
                consumed = inp.get("consumed", True) if isinstance(inp, dict) else True
                count = int(inp.get("count", 1)) if isinstance(inp, dict) else 1
                if not consumed:
                    continue
                nodes = self._input_nodes(player_manager, inp.get("item", "") if isinstance(inp, dict) else str(inp))
                for node in nodes[:max(1, count)]:
                    self._consume_input(player_manager, node, count)

        # outputs for the tier that actually happened
        outputs = self._resolve_outputs({"outputs": tier_outputs})
        msgs = self._spawn_outputs(player_manager, outputs)

        # discovery
        if entry.get("discoverable"):
            known = player.crafting_known or []
            if recipe_label not in known:
                known.append(recipe_label)
            player.crafting_known = known

        tier_message = (outcome.get("message") or "").strip()
        if tier in ("fail", "crit_fail"):
            result = f"You try to craft the {recipe_label.lower()}, but fumble."
            if tier_message:
                result += f" {tier_message}"
            if check_message:
                result += f" {check_message}"
        else:
            result = f"You craft {recipe_label.lower()}!"
            if tier == "crit_success" and tier_message:
                result += f" {tier_message}"
        for m in msgs:
            text = str(m).strip()
            if text:
                result += f"\n{text}"
        area = getattr(player, "current_area", None)
        area_name = getattr(area, "name", area) if area else None
        try:
            player_manager.record_turn_event(
                getattr(player, "name", player_manager.active_player),
                "craft", f"crafted {recipe_label} ({tier})",
                area_name=area_name,
            )
        except Exception:
            pass
        return result

    def craft(self, player_manager, recipe_name: str) -> str:
        entry = self.check_craft(player_manager, recipe_name)
        player = player_manager.players.get(player_manager.active_player)
        recipe_label = entry.get("name", recipe_name)
        tier, check_message = self.resolve_craft_tier(entry, player)
        return self._finish(player_manager, player, entry, recipe_label,
                            tier, check_message)

    def _resolve_outputs(self, outcome: dict) -> list:
        """The outputs for one outcome tier, honouring per-entry weights.

        Entries may carry ``weight`` (crit-fail lotteries); default weight
        is 1 and a single entry stays deterministic - recipes stay
        learnable unless the author opts into variance.
        """
        outputs = (outcome or {}).get("outputs", []) or []
        weighted = [(o, float(o.get("weight", 1) or 0))
                    for o in outputs if isinstance(o, dict)]
        if not weighted:
            return [o for o in outputs if isinstance(o, dict)]
        picks = [o for o, w in weighted if w > 0]
        if len(picks) <= 1:
            return picks
        return [_random.choices(picks, weights=[w for _, w in weighted if w > 0])[0]]

    def _resolve_tier(self, player, entry) -> tuple:
        """Roll the recipe's skill check once and map the degree to a tier.

        One roll through the shared ``checks.resolve`` pipeline (same
        modifiers, conditions and advantage as every other check), so the
        tier and the success agree by construction. ``roll_fn`` injects
        dice for tests. Returns ``(tier, message)``.
        """
        from engine import checks
        skill_cfg = entry.get("skill_check", {}) or {}
        if not skill_cfg.get("skill"):
            return "success", ""
        result = checks.resolve(
            player, kind=str(skill_cfg["skill"]),
            dc=int(skill_cfg.get("dc", 10)), roll_fn=self.roll_fn)
        return TIER_MAP.get(result.tier, "fail"), result.message

