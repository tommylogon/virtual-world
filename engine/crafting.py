"""Crafting & recipe system (task-2).

Recipes are graph nodes of type ``recipe`` whose ``properties`` declare:

.. code-block:: json
   {
     "inputs": [{"item": "egg", "count": 1, "consumed": true},
                 {"item": "pan", "count": 1, "consumed": false}],
     "conditions": [{"type": "state_equals", "target": "oven", "value": "on"}],
     "outputs": [{"item": "fried_egg", "count": 1}],
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
``give_item`` effect (lands in the player's hands/inventory) — so output
``item`` values are library ids.
"""


class CraftingSystem:
    def __init__(self, graph, player_manager, trigger_system, effects, game_state=None):
        self.graph = graph
        self.player_manager = player_manager
        self.trigger_system = trigger_system
        self.effects = effects
        self.world = game_state

    # ────────────────────────── lookup ──────────────────────────

    def recipe_nodes(self):
        return [n for n in self.graph.nodes.values() if n.type == "recipe"]

    def _find_recipe(self, recipe_name):
        needle = str(recipe_name).lower()
        for node in self.recipe_nodes():
            if needle in node.name.lower() or needle in node.id.lower():
                return node
        return None

    def _recipe_learned(self, player, recipe_node) -> bool:
        props = recipe_node.properties or {}
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
                item_needle = rule[5:].strip().lower()
                player_id_getter = getattr(self.player_manager, "get_player_node_id", None) or getattr(self.player_manager, "_player_node_id", None)
                if player_id_getter is None:
                    return False
                player_id = player_id_getter(player.name)
                from graph import EDGE_CARRYING, EDGE_EQUIPPED
                for edge in self.graph.get_edges_for_target(player_id, (EDGE_CARRYING, EDGE_EQUIPPED)):
                    n = self.graph.get_node(edge.source)
                    if n and (item_needle in n.name.lower() or item_needle in n.id.lower()):
                        return True
        return recipe_node.id in (player.crafting_known or [])

    def _recipe_known_names(self, player_name) -> list:
        player = self.player_manager.players.get(player_name)
        if not player:
            return []
        out = []
        for node in self.recipe_nodes():
            if self._recipe_learned(player, node):
                out.append(node.name)
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
                except Exception as e:  # noqa: BLE001 — a bad output shouldn't kill the craft
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
        # fail closed for anything else — crafting gates must be explicit
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
            raise ValueError(f"{student_name} isn't here — they can't learn that from you.")

        subject = str(subject or '').strip()
        if subject.lower().startswith('skill:'):
            skill_name = subject[6:].strip()
            teacher_skills = getattr(teacher, 'skills', {}) or {}
            if int(teacher_skills.get(skill_name, 0) or 0) < 1:
                raise ValueError(f"You don't know '{skill_name}' well enough to teach it.")
            student_skills = dict(getattr(student, 'skills', {}) or {})
            student_skills[skill_name] = int(student_skills.get(skill_name, 0) or 0) + 1
            student.skills = student_skills
            return f"You spend a while going over the basics with {student_name} — they gain a bit of {skill_name}."

        recipe_node = self._find_recipe(subject)
        if recipe_node is None:
            raise ValueError(f"You don't know any recipe called '{subject}'.")
        if not self._recipe_learned(teacher, recipe_node):
            raise ValueError(f"You don't know how to make '{recipe_node.name}'.")
        known = list(getattr(student, 'crafting_known', []) or [])
        if recipe_node.name in known:
            return f"{student_name} already knows how to make {recipe_node.name}."
        known.append(recipe_node.name)
        student.crafting_known = known
        return f"You walk {student_name} through it — they now know how to make {recipe_node.name}."

    def craft(self, player_manager, recipe_name: str) -> str:
        recipe_node = self._find_recipe(recipe_name)
        if recipe_node is None:
            raise ValueError(f"You don't know any recipe for '{recipe_name}'.")
        player = player_manager.players.get(player_manager.active_player)
        if not player:
            raise ValueError("No active character.")
        if not self._recipe_learned(player, recipe_node):
            raise ValueError(f"You don't know how to craft '{recipe_node.name}'.")

        props = recipe_node.properties or {}
        inputs = props.get("inputs", [])
        if isinstance(inputs, str):
            raise ValueError("Recipe inputs must be a JSON list.")
        # check inputs exist
        for inp in inputs:
            needed = inp.get("item", "") if isinstance(inp, dict) else str(inp)
            count = int(inp.get("count", 1)) if isinstance(inp, dict) else 1
            nodes = self._input_nodes(player_manager, needed)
            total = sum(max(1, int(n.properties.get("uses", -1) or 0)) for n in nodes) if nodes else 0
            if not nodes or (count > 1 and total < count):
                raise ValueError(f"You need {count} {needed} and don't have them.")
        # extra gates
        for cond in props.get("conditions", []) or []:
            if not self._condition_passes(cond, player):
                raise ValueError(f"The conditions to craft '{recipe_node.name}' aren't met.")
        # skill check
        skill_cfg = props.get("skill_check", {}) or {}
        if skill_cfg.get("skill"):
            skill = skill_cfg["skill"]
            dc = int(skill_cfg.get("dc", 10))
            success, _, message = player_manager.skill_check(skill, dc)
            if not success:
                return f"You try to craft the {recipe_node.name}, but fumble. {message}"

        # consume inputs (consumed flag)
        for inp in inputs:
            consumed = inp.get("consumed", True) if isinstance(inp, dict) else True
            count = int(inp.get("count", 1)) if isinstance(inp, dict) else 1
            if not consumed:
                continue
            nodes = self._input_nodes(player_manager, inp.get("item", "") if isinstance(inp, dict) else str(inp))
            for node in nodes[:max(1, count)]:
                self._consume_input(player_manager, node, count)

        # outputs
        outputs = props.get("outputs", []) or []
        msgs = self._spawn_outputs(player_manager, outputs)

        # discovery
        if props.get("discoverable"):
            known = player.crafting_known or []
            if recipe_node.name not in known:
                known.append(recipe_node.name)
            player.crafting_known = known

        result = f"You craft {recipe_node.name.lower()}!"
        for m in msgs:
            text = str(m).strip()
            if text:
                result += f"\n{text}"
        area_name = player_manager.current_area.name if player_manager.current_area else None
        player_manager.record_turn_event(
            player_manager.active_player, "craft",
            f"crafted {recipe_node.name}",
            area_name=area_name,
        )
        return result
