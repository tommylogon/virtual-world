"""Trigger testing (editor run button) for TriggerSystem.

Moved from engine/trigger_system.py.
"""

from typing import Any, List, Optional

from graph import Node

from engine.triggers.effect_resolution import _effects_list_from_properties


class TestingMixin:
    """Editor test-run helpers."""

    def test_trigger(
        self,
        trigger_def: dict,
        item_node: Optional[Node] = None,
        game_state: Optional[Any] = None,
        dry_run: bool = True,
        context: Optional[dict] = None,
    ) -> dict:
        """Evaluate a single trigger definition against the live world.

        Used by the editor's "Run" button to test a trigger without having to
        play through the scenario. ``trigger_def`` is the trigger's ``properties``
        dict (``trigger_type``, ``conditions``, ``effects``, ``conditions_logic``).

        Returns a dict:
        - ``trigger_type`` — the trigger's type
        - ``conditions`` — list of ``{condition, expected, passed, detail}``
        - ``conditions_pass`` — whether all conditions evaluated true
        - ``fireable`` — whether the trigger type makes sense in this context
        - ``outputs`` — the messages the effects WOULD produce (dry run) or DID
          produce (live run)
        - ``side_effects`` — list of strings describing what a live run changed

        In dry-run mode, effects are NOT executed -- instead each effect's type +
        params are reported as "would run". In live mode, effects run through the
        normal pipeline and ``outputs`` holds the real result messages.
        """
        trigger_type = trigger_def.get("trigger_type", "")
        # The editor stores trigger_type as an array (multi-select). Normalize
        # to the first entry so the fireable check + output label work.
        if isinstance(trigger_type, (list, tuple)):
            trigger_type = str(trigger_type[0]) if trigger_type else ""
        conditions = trigger_def.get("conditions", [])
        conditions_logic = trigger_def.get("conditions_logic", "and")
        effects = _effects_list_from_properties(trigger_def) or []
        if not effects:
            effects = [{"type": "message", "params": {}}]
        if context is None:
            context = {}
        context = dict(context)
        context["item_node"] = item_node
        if game_state is not None:
            context["game_state"] = game_state

        # Build template context like _execute_triggers does
        context.setdefault(
            "game_time", game_state.get_current_time() if game_state else ""
        )
        context.setdefault(
            "time_ticks", str(game_state.time_ticks) if game_state else ""
        )
        context.setdefault(
            "turn_number", str(game_state.turn_number) if game_state else ""
        )
        context.setdefault(
            "player_name", game_state.active_player if game_state else ""
        )
        context.setdefault(
            "area_name",
            game_state.current_area.name if game_state and game_state.current_area else "",
        )
        context.setdefault("item_name", item_node.name if item_node else "")
        context.setdefault(
            "item_state",
            item_node.properties.get("current_state", "") if item_node else "",
        )
        context.setdefault(
            "item_description",
            item_node.properties.get("description", "") if item_node else "",
        )
        context.setdefault("item_properties", item_node.properties if item_node else {})
        if item_node:
            context.setdefault(
                "item_params", item_node.properties.get("parameters", {})
            )
        if game_state and game_state.player:
            context.setdefault(
                "player_hp", str(game_state.player.vitals.get("HP", 0))
            )
            context.setdefault(
                "player_energy",
                str(game_state.player.vitals.get("Energy", 0)),
            )
            context.setdefault(
                "player_sanity",
                str(game_state.player.vitals.get("Sanity", 0)),
            )

        # Does this trigger type plausibly fire in this context?
        itemful_types = {
            "on_take", "on_drop", "on_examine", "on_inspect", "on_use",
            "on_use_on", "on_eat", "on_drink", "on_read", "on_light",
            "on_activate", "on_equip", "on_unequip", "on_throw", "on_break",
            "on_toggle_on", "on_toggle_off", "on_depleted", "on_open",
            "on_close", "on_state_enter", "on_state_exit", "on_auto_open",
        }
        if not trigger_type:
            fireable = False
            fireable_reason = "no trigger type selected"
        else:
            fireable = trigger_type not in itemful_types or item_node is not None
            fireable_reason = (
                "" if fireable else
                f"this trigger type ({trigger_type}) needs an item/way context to fire"
            )

        # Evaluate conditions individually + as a tree
        cond_results = []
        if conditions:
            cond_tree = (
                {"operator": conditions_logic, "conditions": conditions}
                if isinstance(conditions, list)
                else conditions
            )
            cond_pass = self._evaluate_conditions(
                cond_tree, context, game_state=game_state
            )
            for cond in (conditions if isinstance(conditions, list) else conditions.get("conditions", [])):
                ctype = cond.get("type", "")
                try:
                    # Evaluate via the tree wrapper so context (speech, area, etc.)
                    # reaches leaf conditions exactly like the live trigger walk.
                    passed = self._evaluate_conditions(
                        {"operator": "and", "conditions": [cond]},
                        context,
                        game_state=game_state,
                    )
                except Exception as e:  # pragma: no cover - defensive
                    passed = False
                cond_results.append({
                    "condition": ctype,
                    "passed": passed,
                    "detail": cond,
                })
        else:
            cond_pass = True
            cond_results = [{"condition": "(none)", "passed": True, "detail": {}}]

        outputs = []
        side_effects = []

        if dry_run or not cond_pass:
            # Report what WOULD run without touching the world
            for effect in effects:
                etype = effect.get("type", "message")
                eparams = effect.get("params", {})
                if isinstance(eparams, dict) and eparams.get("success_message"):
                    eparams = dict(eparams)
                    eparams["message"] = eparams["success_message"]
                rendered_msg = self._render_template(
                    eparams.get("message", ""), context
                )
                outputs.append(
                    f"[dry-run] {etype}" + (f": {rendered_msg}" if rendered_msg else "")
                )
                if etype in ("apply_trait", "remove_trait"):
                    target = eparams.get("target", "self")
                    side_effects.append(
                        f"would {etype.replace('_', ' ')} '{eparams.get('trait', '?')}' on {target}"
                    )
                elif eparams.get("node_id") or eparams.get("target"):
                    side_effects.append(f"would modify node: {eparams.get('node_id') or eparams.get('target')}")
                if etype in ("spawn_item", "remove_item", "teleport", "set_environment", "adjust_vital"):
                    side_effects.append(f"would run effect: {etype}")
        else:
            # Live run -- build a fake trigger edge and walk it via _execute_triggers
            for effect in effects:
                etype = effect.get("type", "message")
                eparams = effect.get("params", {})
                if isinstance(eparams, dict) and eparams.get("success_message"):
                    eparams = dict(eparams)
                    eparams["message"] = eparams["success_message"]
                try:
                    result = self._effects.execute(
                        etype, eparams, context,
                        item_node=item_node, game_state=game_state,
                    )
                    outputs.extend(result)
                except Exception as e:  # pragma: no cover - defensive
                    outputs.append(f"[effect error: {e}]")

        return {
            "trigger_type": trigger_type,
            "conditions": cond_results,
            "conditions_pass": cond_pass,
            "fireable": fireable,
            "fireable_reason": fireable_reason,
            "outputs": outputs,
            "side_effects": side_effects,
        }
