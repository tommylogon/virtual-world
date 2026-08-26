"""State effect handlers (set_state, set_hidden)."""

import time


def handle_set_state(self, params, context, item_node=None, game_state=None):
    """Set the current_state property on a node.

    When the state changes, fires on_state_exit and on_state_enter
    triggers recursively.

    game_state: passed through to recursive trigger calls.
    """
    new_state = params.get("state", "open")
    target_node = self._resolve_effect_target(params, item_node)
    if target_node is None:
        return []
    old_state = target_node.properties.get("current_state", "")
    target_node.properties["current_state"] = new_state
    outputs = [
        params.get("message", f"{target_node.name} is now {new_state}.")
    ]
    if old_state != new_state and self._trigger_fn:
        outputs.extend(
            self._trigger_fn(
                target_node,
                "on_state_exit",
                context=context,
                expected_target_state=old_state,
                game_state=game_state,
            )
        )
        outputs.extend(
            self._trigger_fn(
                target_node,
                "on_state_enter",
                context=context,
                expected_target_state=new_state,
                game_state=game_state,
            )
        )
    return outputs


def handle_set_hidden(self, params, context, item_node=None, game_state=None):
    """Toggle the hidden state on a node (via current_state).

    game_state: unused.
    """
    hidden = params.get("hidden", True)
    target_node = self._resolve_effect_target(params, item_node)
    if target_node is None:
        return []
    if hidden:
        target_node.properties["current_state"] = "hidden"
    else:
        if target_node.properties.get("current_state") == "hidden":
            target_node.properties["current_state"] = "normal"
    target_node.updated = time.time()
    return [
        params.get(
            "message",
            f"{target_node.name} is now {'hidden' if hidden else 'visible'}.",
        )
    ]


HANDLERS = {
    "set_state": handle_set_state,
    "set_hidden": handle_set_hidden,
}
