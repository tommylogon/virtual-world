"""Equipment effect handlers (add_tag, remove_tag, adjust_uses, destroy_self, drain, consume_item)."""

import time


def _normalize_tags(raw_tags):
    """Return a mutable list from a tag list or comma-string."""
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        return [t.strip() for t in raw_tags.split(",") if t.strip()]
    if isinstance(raw_tags, list):
        return list(raw_tags)
    return []


def handle_add_tag(self, params, context, item_node=None, target_item_node=None, game_state=None):
    """Add a tag to a target node's tags list.

    Tag from params['tag']; targets via node_id / self / target_tag fan-out.
    game_state: unused.
    """
    tag = str(params.get("tag", "")).strip()
    if not tag:
        return []
    target_node = self._resolve_effect_target(params, item_node, target_item_node)
    if target_node is None:
        return []
    tags = _normalize_tags(target_node.properties.get("tags"))
    if tag not in tags:
        tags.append(tag)
    target_node.properties["tags"] = tags
    target_node.updated = time.time()
    message = params.get("message", f"Added tag '{tag}' to {target_node.name}.")
    return [message] if message else []


def handle_remove_tag(self, params, context, item_node=None, target_item_node=None, game_state=None):
    """Remove a tag from a target node's tags list.

    Tag from params['tag']; targets via node_id / self / target_tag fan-out.
    game_state: unused.
    """
    tag = str(params.get("tag", "")).strip()
    if not tag:
        return []
    target_node = self._resolve_effect_target(params, item_node, target_item_node)
    if target_node is None:
        return []
    tags = _normalize_tags(target_node.properties.get("tags"))
    if tag in tags:
        tags.remove(tag)
    target_node.properties["tags"] = tags
    target_node.updated = time.time()
    message = params.get("message", f"Removed tag '{tag}' from {target_node.name}.")
    return [message] if message else []


def handle_adjust_uses(self, params, context, item_node=None, target_item_node=None, game_state=None):
    """Change the remaining-use count on an item node.

    Uses node_id from params, or falls back to target_item_node (for on_use_on).
    game_state: unused.
    """
    node_id = params.get("node_id", "")
    target_node = None
    if node_id and node_id != "self":
        target_node = self.graph.get_node(node_id)
    if target_node is None and node_id == "self" and item_node:
        target_node = item_node
    if target_node is None and target_item_node:
        target_node = target_item_node
    if target_node is None:
        return []
    delta = int(params.get("delta", -1))
    current_uses = int(target_node.properties.get("uses", -1))
    if current_uses >= 0:
        target_node.properties["uses"] = max(0, current_uses + delta)
        target_node.updated = time.time()
        message = params.get(
            "message",
            f"{target_node.name} uses: {current_uses} -> {target_node.properties['uses']}.",
        )
        if not message:
            return []
        return [message]
    return []


def handle_destroy_self(self, params, context, item_node=None, game_state=None):
    """Remove the triggering item node from the graph.

    game_state: unused.
    """
    if item_node is None:
        return []
    msg = params.get("message", "The item crumbles to dust!")
    for edge in self.graph.edges[:]:
        if edge.source == item_node.id and edge.type == EDGE_IN:
            self.graph.edges.remove(edge)
    self.graph.remove_node(item_node.id)
    return [msg]


def handle_drain(self, params, context, item_node=None, game_state=None):
    """Reduce an item's remaining uses.

    game_state: unused.
    """
    if item_node is None:
        return []
    amount = int(params.get("amount", 1))
    stat = params.get("stat", "uses")
    outputs = []
    if stat == "uses":
        uses = item_node.properties.get("uses", -1)
        if uses > 0:
            item_node.properties["uses"] = max(0, uses - amount)
            if item_node.properties["uses"] == 0:
                outputs.append(
                    params.get(
                        "message",
                        f"The {item_node.name} runs out of power.",
                    )
                )
    return outputs


def handle_consume_item(self, params, context, item_node=None, game_state=None):
    """Remove a named item from the active player's inventory,
    decrementing uses if tracked.

    game_state must provide:
      game_state.player
      game_state.active_player
      game_state._player_node_id(name) -> str
    """
    consume_name = params.get("item", "")
    if not consume_name or not game_state or not game_state.player:
        return []
    player_id = game_state._player_node_id(game_state.active_player)
    inventory_edges = self.graph.get_edges_for_target(
        player_id, EDGE_CARRYING
    )
    needle = str(consume_name).lower()
    target_item_id = None
    for edge in inventory_edges:
        node = self.graph.get_node(edge.source)
        if (
            node
            and node.type == "item"
            and (needle in node.name.lower() or needle in node.id.lower())
        ):
            target_item_id = node.id
            break
    if target_item_id is None:
        return []
    for edge in self.graph.edges[:]:
        if (
            edge.source == target_item_id
            and edge.target == player_id
            and edge.type == EDGE_CARRYING
        ):
            self.graph.edges.remove(edge)
    target_node = self.graph.get_node(target_item_id)
    if target_node:
        uses = int(target_node.properties.get("uses", -1))
        if uses > 0:
            target_node.properties["uses"] = uses - 1
            if target_node.properties["uses"] <= 0:
                self.graph.remove_node(target_item_id)
        elif uses == 1:
            self.graph.remove_node(target_item_id)
    msg = params.get("message", f"{consume_name} is consumed.")
    msg = self._render_template_fn(msg, context)
    return [msg]


HANDLERS = {
    "add_tag": handle_add_tag,
    "remove_tag": handle_remove_tag,
    "adjust_uses": handle_adjust_uses,
    "destroy_self": handle_destroy_self,
    "drain": handle_drain,
    "consume_item": handle_consume_item,
}
