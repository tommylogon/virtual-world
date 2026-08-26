"""Properties effect handlers (set_parameter, adjust_parameter, set_description, append_description, rename)."""

import time


def handle_set_parameter(self, params, context, item_node=None, target_item_node=None, game_state=None):
    """Set a key in a target node's ``parameters`` dict to an explicit value.

    Targets via node_id / self / target_tag fan-out (any node type — item,
    way, area, character). Read back with ``{param:<key>}`` in descriptions.
    game_state: unused.
    """
    key = str(params.get("key", "")).strip()
    if not key:
        return []
    target_node = self._resolve_effect_target(params, item_node, target_item_node)
    if target_node is None:
        return []
    params_dict = target_node.properties.setdefault("parameters", {})
    if not isinstance(params_dict, dict):
        params_dict = {}
        target_node.properties["parameters"] = params_dict
    params_dict[key] = params.get("value", "")
    target_node.updated = time.time()
    message = params.get(
        "message",
        f"Set '{key}' on {target_node.name} to '{params_dict[key]}'.",
    )
    return [message] if message else []


def handle_adjust_parameter(self, params, context, item_node=None, target_item_node=None, game_state=None):
    """Add a numeric delta to a key in a target node's ``parameters`` dict.

    For counters/gauges (e.g. ``{delta: +1}`` on a charges param). Targets via
    node_id / self / target_tag fan-out on any node type.
    game_state: unused.
    """
    key = str(params.get("key", "")).strip()
    if not key:
        return []
    target_node = self._resolve_effect_target(params, item_node, target_item_node)
    if target_node is None:
        return []
    params_dict = target_node.properties.setdefault("parameters", {})
    if not isinstance(params_dict, dict):
        params_dict = {}
        target_node.properties["parameters"] = params_dict
    try:
        current = int(params_dict.get(key, 0))
    except (ValueError, TypeError):
        current = 0
    delta = int(params.get("delta", 0))
    params_dict[key] = current + delta
    target_node.updated = time.time()
    message = params.get(
        "message",
        f"Adjusted '{key}' on {target_node.name} to '{params_dict[key]}'.",
    )
    return [message] if message else []


def handle_set_description(self, params, context, item_node=None, game_state=None):
    """Replace the description on a target node.

    game_state: unused.
    """
    target = params.get("target", "")
    new_desc = params.get("value") or params.get("description", "")
    if not target or not new_desc:
        return []
    target_node = self.graph.get_node(target)
    if target_node is None:
        return []
    target_node.properties["description"] = self._render_template_fn(
        new_desc, context
    )
    msg = params.get("message", "Description changed.")
    msg = self._render_template_fn(msg, context)
    return [msg]


def handle_append_description(self, params, context, item_node=None, game_state=None):
    """Append text to the description on a target node.

    game_state: unused.
    """
    target = params.get("target", "")
    append_text = params.get("text", "")
    if not target or not append_text:
        return []
    target_node = self.graph.get_node(target)
    if target_node is None:
        return []
    current = target_node.properties.get("description", "")
    target_node.properties["description"] = (
        current + "\n" + self._render_template_fn(append_text, context)
    )
    msg = params.get("message", "Description updated.")
    msg = self._render_template_fn(msg, context)
    return [msg]


def handle_rename(self, params, context, item_node=None, game_state=None):
    """Rename a node (used for the "unknown name" discovery flow).

    Targets the triggering item by default; pass ``node_id`` (or ``"self"``)
    to target a different node. The display name lives on ``Node.name`` —
    set there so examine/matching/take all see the new name. ``properties``
    is left untouched except mirroring into ``properties["name"]`` for
    any legacy readers.

    game_state: unused.
    """
    new_name = params.get("name", "")
    if not new_name:
        return []
    node_id = params.get("node_id", "")
    if not node_id or node_id == "self":
        if item_node:
            node_id = item_node.id
        else:
            return []
    target_node = self.graph.get_node(node_id)
    if target_node is None:
        return []
    rendered = self._render_template_fn(new_name, context)
    target_node.name = rendered
    target_node.properties["name"] = rendered
    msg = params.get("message", f"It is now called {rendered}.")
    msg = self._render_template_fn(msg, context)
    return [msg]


HANDLERS = {
    "set_parameter": handle_set_parameter,
    "adjust_parameter": handle_adjust_parameter,
    "set_description": handle_set_description,
    "append_description": handle_append_description,
    "rename": handle_rename,
}
