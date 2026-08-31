"""Combine / split verbs for ItemActions (task-155 stackable instances).

Two identical consumable copies (e.g. two breads) can be merged into one
stack (uses + weight summed) or one stack can be split back into equal
parts. Weight reconciliation (task-155A) keeps ``weight`` proportional to
``uses`` for items that track ``max_uses``.

Methods hang off the ItemActions context (graph, matching, trigger_system,
equipment, ghost_system, world) via the mixin pattern (task-314).
"""

import copy
import re

from graph import Edge, Node, EDGE_CARRYING, EDGE_EQUIPPED

#: Properties that must match for two instances to be "stackable twins" (D).
_STACKABLE_KEYS = ["actions", "tags", "current_state", "equip_slots", "max_uses"]

#: WorldGraph.add_node appends a hex suffix to duplicate ids AND names
#: (e.g. ``bread_5e2713ac``) — strip it so copies compare as the same kind.
_AUTO_SUFFIX = re.compile(r"_[0-9a-f]{6,8}$")


def _prop_key(value):
    return str(value or "").strip().lower()


def _base_name(name):
    return _AUTO_SUFFIX.sub("", str(name or "").strip().lower())


def stackable_twins(node_a, node_b) -> bool:
    """Two item nodes are stackable when they share the same kind
    (library_id, or same base name) AND identical usable identity."""
    if node_a is None or node_b is None:
        return False
    pa, pb = node_a.properties or {}, node_b.properties or {}
    same_kind = bool(
        pa.get("library_id") and pa.get("library_id") == pb.get("library_id")
    ) or _base_name(node_a.name) == _base_name(node_b.name)
    if not same_kind:
        return False
    return all(
        _prop_key(pa.get(k)) == _prop_key(pb.get(k))
        for k in _STACKABLE_KEYS
    )


class StackingMixin:
    """combine / split for stackable consumable instances."""

    def _all_carry_nodes(self, player_manager, item_name: str):
        """Every item node the player carries/equips matching *item_name*."""
        player_id = player_manager._player_node_id(player_manager.active_player)
        needle = str(item_name).lower()
        out = []
        for edge in self.graph.get_edges_for_target(player_id, (EDGE_CARRYING, EDGE_EQUIPPED)):
            node = self.graph.get_node(edge.source)
            if node and node.type == "item" and (
                needle in node.name.lower() or needle in node.id.lower()
            ):
                out.append(node)
        return out

    def combine_items(self, player_manager, source_name: str, target_name: str) -> str:
        """Merge two stackable instances: uses add (clamped at max_uses),
        weight recomputes, the source instance is destroyed."""
        sources = self._all_carry_nodes(player_manager, source_name)
        targets = self._all_carry_nodes(player_manager, target_name)
        if not sources:
            raise ValueError(f"You don't have '{source_name}' to combine.")
        if not targets:
            raise ValueError(f"You don't have '{target_name}' to combine.")
        source = sources[0]
        target = next((t for t in targets if t.id != source.id), None)
        if target is None:
            raise ValueError(f"There's only one '{target_name}' — find another to combine it with.")
        if not stackable_twins(source, target):
            raise ValueError(f"The {source.name} and {target.name} can't be combined — they aren't the same kind.")

        from engine.items.carry_weight import reconcile_item_weight

        src_uses = int(source.properties.get("uses", -1) or 0)
        tgt_uses = int(target.properties.get("uses", -1) or 0)
        max_uses = int(target.properties.get("max_uses", 0) or 0)
        old_weight = float(target.properties.get("weight", 0) or 0)
        if max_uses > 0:
            combined = tgt_uses + src_uses
            overflow = max(0, combined - max_uses)
            target.properties["uses"] = min(max_uses, combined)
            note = f" Some is wasted — it's completely full." if overflow > 0 else ""
        else:
            target.properties["uses"] = tgt_uses + src_uses
            note = ""

        # capacity re-check: the merged stack may be heavier than the target was
        reconcile_item_weight(target)
        delta = float(target.properties.get("weight", 0) or 0) - old_weight
        if delta > 0:
            cap_error = self._check_player_capacity(player_manager, delta)
            if cap_error:
                raise ValueError(cap_error)

        # destroy the source instance (all edges + node)
        for edge in list(self.graph.edges):
            if edge.source == source.id or edge.target == source.id:
                self.graph.edges.remove(edge)
        self.graph.remove_node(source.id)

        result = (
            f"You combine the {source.name} into the {target.name}: "
            f"it now holds {target.properties['uses']} uses.{note}"
        )
        return result

    def split_item(self, player_manager, item_name: str, parts: int = 2) -> str:
        """Split one stack into N equal parts; a new node carries the
        remainder and lands in the player's inventory."""
        nodes = self._all_carry_nodes(player_manager, item_name)
        if not nodes:
            raise ValueError(f"You don't have '{item_name}' to split.")
        node = nodes[0]
        uses = int(node.properties.get("uses", -1) or 0)
        if uses < 2:
            raise ValueError(f"The {node.name} doesn't have enough uses to split.")
        parts = max(2, int(parts or 2))
        per = max(1, uses // parts)
        if per < 1:
            raise ValueError(f"The {node.name} doesn't have enough uses to split.")

        from engine.items.carry_weight import reconcile_item_weight

        node.properties["uses"] = per
        reconcile_item_weight(node)

        new_props = copy.deepcopy(node.properties)
        new_props["uses"] = uses - per
        max_uses = int(new_props.get("max_uses", 0) or 0)
        if new_props.get("base_weight") and max_uses > 0:
            new_props["weight"] = round(
                float(new_props["base_weight"]) * ((uses - per) / max_uses), 3
            )
        new_node = Node(
            id=f"{node.id}_part",
            name=node.name,
            type=node.type,
            properties=new_props,
        )
        self.graph.nodes[new_node.id] = new_node
        player_id = player_manager._player_node_id(player_manager.active_player)
        self.graph.add_edge(Edge(source=new_node.id, target=player_id, type=EDGE_CARRYING))

        return (
            f"You split the {node.name}: {per} uses stay put and "
            f"{uses - per} go into your pack."
        )
