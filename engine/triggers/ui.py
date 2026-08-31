"""UI helpers for TriggerSystem.

Moved from engine/trigger_system.py.
"""

from typing import Any, List

from graph import EDGE_TRIGGERS, Node

from engine.item_actions import normalize_item_actions


class UiMixin:
    """Available-actions and contextual-failure helpers."""

    def _get_available_actions(self, item_node: Node) -> List[dict]:
        """Return a list of action descriptors for an item given the current context.

        The returned list is used by the UI to render available
        interaction buttons.

        *game_state* is not required here (graph info is accessed via
        ``self.graph`` and *item_node*).
        """
        actions = item_node.properties.get("actions", [])
        if isinstance(actions, str):
            actions = [a.strip() for a in actions.split(",")]
        actions = normalize_item_actions(actions)

        trigger_edges = self.graph.get_edges_for_source(
            item_node.id, EDGE_TRIGGERS
        )
        trigger_types = set()
        for trigger_edge in trigger_edges:
            trigger_node = self.graph.get_node(trigger_edge.target)
            if trigger_node:
                tt = trigger_node.properties.get("trigger_type", "")
                # trigger_type may be a single string or a list (multi-select editor)
                if isinstance(tt, list):
                    trigger_types.update(str(x) for x in tt)
                elif tt:
                    trigger_types.add(tt)

        tags = [t.lower() for t in item_node.properties.get("tags", [])]
        state = item_node.properties.get("current_state", "")
        result = []

        result.append(
            {
                "action": "examine",
                "label": "Examine the object",
                "enabled": True,
            }
        )

        if "take" in actions:
            result.append({"action": "take", "label": "Pick up", "enabled": True})

        if "drop" in actions:
            result.append(
                {
                    "action": "drop",
                    "label": "Drop from inventory",
                    "enabled": True,
                }
            )

        if "open" in actions or "openable" in tags:
            if state in ("closed", "normal", ""):
                result.append({"action": "open", "label": "Open", "enabled": True})
            else:
                result.append(
                    {
                        "action": "open",
                        "label": "Open",
                        "enabled": False,
                        "reason": "Already open",
                    }
                )

        if "close" in actions or (state == "open"):
            if state == "open":
                result.append(
                    {"action": "close", "label": "Close", "enabled": True}
                )
            else:
                result.append(
                    {
                        "action": "close",
                        "label": "Close",
                        "enabled": False,
                        "reason": "Already closed",
                    }
                )

        if "use" in actions or "on_use" in trigger_types or "on_use_progressive" in trigger_types or "on_use_on" in trigger_types:
            label = "Use"
            if "on_use_on" in trigger_types:
                for trigger_edge in trigger_edges:
                    trigger_node = self.graph.get_node(trigger_edge.target)
                    if not trigger_node:
                        continue
                    tt = trigger_node.properties.get("trigger_type", "")
                    tt_list = tt if isinstance(tt, list) else ([tt] if tt else [])
                    if "on_use_on" in tt_list:
                        target_name = trigger_node.properties.get(
                            "target_name", ""
                        )
                        if target_name:
                            label = f"Use on {target_name}"
                            break
            result.append({"action": "use", "label": label, "enabled": True})

        if "eat" in actions or "food" in tags:
            result.append({"action": "eat", "label": "Eat", "enabled": True})

        if "drink" in actions or "drink" in tags:
            result.append({"action": "drink", "label": "Drink", "enabled": True})

        if "on_toggle_on" in trigger_types or "on_toggle_off" in trigger_types:
            toggle_state = "on" if state == "off" else "off"
            result.append(
                {
                    "action": "toggle",
                    "label": f"Toggle {toggle_state}",
                    "enabled": True,
                }
            )

        return result

    def _contextual_failure(
        self, verb: str, target_name: str, available_actions: List[dict]
    ) -> str:
        """Generate a first-person contextual failure reason.

        Explains why *verb* can't be performed on *target_name*, and
        suggests available alternatives from the *available_actions* list.
        """
        reasons = {
            "take": "I reach for the {item} but stop -- I have no need for it.",
            "use": "I examine the {item} but can't figure out what to do with it.",
            "eat": "I pause -- that's not food.",
            "drink": "That's not something you drink.",
            "open": "The {item} doesn't open.",
            "close": "The {item} isn't something you can close.",
            "break": "I don't think breaking the {item} would accomplish anything.",
        }
        msg = reasons.get(verb, "I try, but nothing useful happens.")
        msg = msg.format(item=target_name)

        valid = [a["label"] for a in available_actions if a["enabled"]]
        if valid:
            msg += (
                f" I could {valid[0].lower()}"
                + (
                    f" or {', '.join(v.lower() for v in valid[1:])}."
                    if len(valid) > 1
                    else "."
                )
            )
        return msg
