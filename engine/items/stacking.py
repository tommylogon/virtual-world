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
import uuid

from graph import Edge, Node, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN

#: Properties that must match for two instances to be "stackable twins" (D).
_STACKABLE_KEYS = ["actions", "tags", "current_state", "equip_slots", "max_uses"]


def is_stackable(node) -> bool:
    """True when an item authors the explicit ``stackable`` marker (task-473).

    Deliberately opt-in: dropping two identical ``uses: -1`` props on the floor
    must not fuse them, and the existing ``quantity`` pool (task-504) is a
    different model. Only an item that says ``stackable: true`` participates in
    take-from-stack and merge-on-put.
    """
    props = getattr(node, "properties", None) or {}
    return bool(props.get("stackable"))

#: WorldGraph.add_node appends a hex suffix to duplicate ids AND names
#: (e.g. ``bread_5e2713ac``) — strip it so copies compare as the same kind.
_AUTO_SUFFIX = re.compile(r"_[0-9a-f]{6,8}$")


def _display_name(name):
    """Strip a leading article for verb phrasing (matches take_drop_actions)."""
    return re.sub(r'^(?:the|a|an)\s+', '', str(name or '').strip())


def _prop_key(value):
    return str(value or "").strip().lower()


def _base_name(name):
    return _AUTO_SUFFIX.sub("", str(name or "").strip().lower())


def stackable_twins(node_a, node_b) -> bool:
    """Two item nodes are stackable when they share the same kind
    (library_id, or same base name) AND identical usable identity."""
    if node_a is None or node_b is None:
        return False
    # task-504: stacking is the OTHER direction from a pool. A pool is one node
    # standing for many of a kind in the world; a stack is many copies merged
    # into one carried node. Merging the two would sum a pool's count into a
    # carried copy's `uses` and destroy the pool, so a pool is never a twin of
    # anything — including another pool at a different size.
    from engine.room_perception import item_quantity

    if item_quantity(node_a) > 1 or item_quantity(node_b) > 1:
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

    def _destroy_node(self, node):
        for edge in list(self.graph.edges):
            if edge.source == node.id or edge.target == node.id:
                self.graph.edges.remove(edge)
        self.graph.remove_node(node.id)

    def merge_stack_into(self, moving_node, holder_id):
        """Merge ``moving_node`` into a matching stack at ``holder_id`` (task-473).

        ``holder_id`` is a container or area node. If it already holds a
        ``stackable`` twin (same kind/identity, via :func:`stackable_twins`), the
        moving node's uses are added to the twin (clamped at ``max_uses``), its
        weight recomputed, and the moving node destroyed. Returns the prose
        result, or ``None`` when there is nothing to merge with.

        Both sides must carry the explicit ``stackable`` marker: a pile of raw
        meat merges, two ordinary identical props on the floor do not.
        """
        if moving_node is None or not is_stackable(moving_node):
            return None
        twin = None
        for edge in self.graph.get_edges_for_target(holder_id, EDGE_IN):
            cand = self.graph.get_node(edge.source)
            if (cand is not None and cand.id != moving_node.id
                    and is_stackable(cand) and stackable_twins(moving_node, cand)):
                twin = cand
                break
        if twin is None:
            return None

        from engine.items.carry_weight import reconcile_item_weight

        def _uses(node):
            try:
                return int(node.properties.get("uses", 0) or 0)
            except (TypeError, ValueError):
                return 0

        added = _uses(moving_node)
        current = _uses(twin)
        # Review fix (finding 7): `uses` is a count, so a depleted (0) or
        # inexhaustible (-1) stack is not a number of units to merge. Refuse
        # rather than subtracting a phantom unit and destroying the node.
        if added <= 0:
            return None
        max_uses = int(twin.properties.get("max_uses", 0) or 0)
        # Review fix (finding 2): when the destination cannot hold the whole
        # stack, refuse the merge so the normal put/drop path leaves the moving
        # node intact. Clamping here would destroy the overflow silently.
        if max_uses > 0 and current + added > max_uses:
            return None
        combined = current + added
        twin.properties["uses"] = combined
        reconcile_item_weight(twin)
        self._destroy_node(moving_node)
        return (f"You add the {_display_name(moving_node.name)} to the "
                f"{_display_name(twin.name)} — it now holds {combined} uses.")

    def take_from_stack(self, player_manager, item_node, amount: int = 1) -> str:
        """Draw ``amount`` units from a homogeneous world stack (task-473).

        The stack is one node carrying N ``uses``; taking spawns a discrete copy
        (``uses: 1``) into the taker's inventory and decrements the stack. At
        zero the original node is removed. Mirrors ``_harvest_pool`` but reads
        ``uses`` rather than ``quantity`` and clones the node itself rather than
        hydrating a declared yield.
        """
        from engine.items.carry_weight import reconcile_item_weight
        from engine.room_perception import normalize_name

        try:
            remaining = int(item_node.properties.get("uses", 1) or 1)
        except (TypeError, ValueError):
            remaining = 1
        if remaining < 1:
            raise ValueError(f"The {_display_name(item_node.name)} is empty.")
        wanted = min(max(1, int(amount or 1)), remaining)

        player_id = player_manager._player_node_id(player_manager.active_player)
        area_id = player_manager._get_current_area_id()

        copies = []
        for _ in range(wanted):
            props = copy.deepcopy(item_node.properties)
            props["uses"] = 1
            new_id = f"{item_node.id}_{uuid.uuid4().hex[:8]}"
            copy_node = Node(id=new_id, name=item_node.name, type="item",
                             properties=props)
            self.graph.add_node(copy_node)
            # Review fix (finding 1): the clone inherits the stack's aggregate
            # weight. Reconcile each unit so it weighs base_weight/max_uses
            # rather than the whole pile.
            reconcile_item_weight(copy_node)
            copies.append(copy_node)

        total_weight = sum(float(c.properties.get("weight", 0) or 0) for c in copies)
        cap_error = self._check_player_capacity(player_manager, total_weight)
        to_player = cap_error is None
        # task-425: the draw path pays first-meeting novelty exactly as the
        # quantity-pool path does (review fix, finding 6).
        self._register_item_discovery(player_manager, item_node)
        for copy_node in copies:
            self._register_item_discovery(player_manager, copy_node)
            if to_player:
                self.graph.add_edge(Edge(source=copy_node.id, target=player_id,
                                         type=EDGE_CARRYING))
            else:
                self.graph.add_edge(Edge(source=copy_node.id, target=area_id,
                                         type=EDGE_IN))

        item_node.properties["uses"] = remaining - wanted
        reconcile_item_weight(item_node)

        area_name = player_manager.current_area.name if player_manager.current_area else None
        result = (f"You take {wanted} {item_node.name} from the "
                  f"{_display_name(item_node.name)}.")
        if not to_player:
            result += " Your pack is full, so you leave them at your feet."
        player_manager.record_turn_event(
            player_manager.active_player, "take",
            f"took {wanted} from the {_display_name(item_node.name)}",
            area_name=area_name,
        )

        if item_node.properties["uses"] <= 0:
            # Review fix (finding 5): empty through the shared teardown so an
            # authored `on_depleted` / persistent-empty state is honoured.
            result += f" The {_display_name(item_node.name)} is picked clean."
            result = self._finish_depleted(item_node, result)
        else:
            result += f" {item_node.properties['uses']} remain."
        return result

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
        # task-473: a uuid suffix, not a fixed "_part". The old
        # `f"{node.id}_part"` written by raw dict assignment meant splitting a
        # part again produced `bread_part_part`, silently overwriting the first
        # rather than creating a third node.
        new_node = Node(
            id=f"{node.id}_{uuid.uuid4().hex[:8]}",
            name=node.name,
            type=node.type,
            properties=new_props,
        )
        self.graph.add_node(new_node)
        player_id = player_manager._player_node_id(player_manager.active_player)
        self.graph.add_edge(Edge(source=new_node.id, target=player_id, type=EDGE_CARRYING))

        return (
            f"You split the {node.name}: {per} uses stay put and "
            f"{uses - per} go into your pack."
        )
