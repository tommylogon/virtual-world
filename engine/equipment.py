"""Equipment system for the virtual world engine.

Manages equipping/unequipping items to body slots, equipment descriptions,
and hygiene modifiers.
"""

from typing import Optional, Dict, List, Any
from graph import Node, Edge, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN


# Tags marking an item as an intrinsic ability (a spell, power, or talent)
# rather than a physical object. These never show in another character's
# examine/equipment narrative. Physical items that merely contain magic
# (scrolls, spell books) stay visible unless they carry one of these tags.
INTRINSIC_ABILITY_TAGS = frozenset(
    {"spell", "ability", "innate", "intrinsic", "power"}
)


class EquipmentSystem:
    """Manages equipment on body slots for all players."""

    EQUIP_SLOTS = {
        "head": {"max_depth": 3, "label": "Head"},
        "neck": {"max_depth": 2, "label": "Neck"},
        "torso": {"max_depth": 5, "label": "Torso"},
        "arms": {"max_depth": 2, "label": "Arms"},
        "hands": {"max_depth": 2, "label": "Hands"},
        "legs": {"max_depth": 4, "label": "Legs"},
        "feet": {"max_depth": 3, "label": "Feet"},
        "back": {"max_depth": 2, "label": "Back"},
        "waist": {"max_depth": 2, "label": "Waist"},
        "accessory": {"max_depth": None, "label": "Accessory"},
        "hand_left": {"max_depth": 1, "label": "Left Hand"},
        "hand_right": {"max_depth": 1, "label": "Right Hand"},
    }

    def __init__(self, graph, trigger_system, logging_events, player_manager, world=None):
        self.graph = graph
        self.triggers = trigger_system
        self.logging = logging_events
        self.player_manager = player_manager
        self.world = world

    def _get_slot_for_item(self, item_node: Node) -> Optional[str]:
        """Auto-detect which slot an item belongs to based on equip_slots property."""
        equip_slots = item_node.properties.get("equip_slots", [])
        if isinstance(equip_slots, str):
            equip_slots = [slot.strip() for slot in equip_slots.split(",")]
        if equip_slots:
            return equip_slots[0]
        return None

    def _slot_has_area(self, slot: str, stack: list) -> bool:
        """Check if a slot has area for another item in its stack."""
        if slot not in self.EQUIP_SLOTS:
            return False
        slot_config = self.EQUIP_SLOTS[slot]
        max_depth = slot_config["max_depth"]
        if max_depth is None:
            return True
        return len(stack) < max_depth

    @staticmethod
    def _is_marker(item_id) -> bool:
        """Check if an item_id is a slot marker (not a real item node)."""
        return item_id and str(item_id).startswith("__")

    @staticmethod
    def _get_extra_hand_slot(tags: list, slot: str) -> Optional[str]:
        """Return the other hand slot if item is two-handed and equipped in a hand, else None."""
        if "two_handed" in tags and slot in ("hand_left", "hand_right"):
            return "hand_right" if slot == "hand_left" else "hand_left"
        return None

    @staticmethod
    def _get_extra_slots(tags: list, equip_slots: list, slot: str) -> List[str]:
        """Return extra slots an item also occupies beyond its primary slot.

        - ``equips_all_slots`` tag: the item covers every declared equip slot
          (e.g. a full-body EVA suit), so every other slot in ``equip_slots``
          is occupied. Returned in declaration order so the primary slot is
          skipped but the rest keep their authored order.
        """
        if "equips_all_slots" not in tags:
            return []
        return [s for s in equip_slots if s != slot]

    def equip_item(self, item_name: str, slot: str = None, under: str = None) -> str:
        """Equip an item from inventory to a body slot. Returns output message."""
        player = self.player_manager.get_active_player_obj()
        if not player:
            raise ValueError("No active player.")
        if player.state in ["sleeping", "unconscious", "dead", "bound"]:
            raise ValueError(f"You can't equip items while {player.state}.")

        item_node = self.player_manager.find_item_node(item_name)
        if not item_node:
            raise ValueError(f"You don't have '{item_name}'.")

        player_id = self.player_manager.get_player_node_id(self.player_manager.active_player)
        is_carried = False
        for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
            if edge.source == item_node.id:
                is_carried = True
                break
        if not is_carried:
            # Check if it's inside a container that the player carries or wears
            for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
                for container_edge in self.graph.get_edges_for_target(player_id, edge_type):
                    container_node = self.graph.get_node(container_edge.source)
                    if container_node and container_node.type == "item":
                        for content_edge in self.graph.get_edges_for_target(container_node.id, EDGE_IN):
                            if content_edge.source == item_node.id:
                                is_carried = True
                                break
                    if is_carried:
                        break
                if is_carried:
                    break
        if not is_carried:
            raise ValueError(f"You aren't carrying '{item_name}'.")

        # One instance per name: equipping a second copy — or the same node
        # twice — stacks nonsense ("Earring over Earring", taco_bell
        # 2026-08-24). Refuse; remove first to re-slot.
        wanted = item_node.name.lower().replace('_', ' ').replace('-', ' ').strip()
        for worn_edge in self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
            worn = self.graph.get_node(worn_edge.source)
            if not worn:
                continue
            worn_name = worn.name.lower().replace('_', ' ').replace('-', ' ').strip()
            if worn_name == wanted:
                raise ValueError(f"You're already wearing the {worn.name}.")

        equip_slots = item_node.properties.get("equip_slots", [])
        if isinstance(equip_slots, str):
            equip_slots = [s.strip() for s in equip_slots.split(",")]

        if not equip_slots:
            raise ValueError(f"The {item_name} can't be equipped.")

        if slot:
            if slot not in self.EQUIP_SLOTS:
                raise ValueError(f"Unknown slot '{slot}'.")
            if slot not in equip_slots:
                raise ValueError(f"The {item_name} doesn't fit in the {slot} slot.")
        else:
            slot = self._get_slot_for_item(item_node)
            if not slot:
                raise ValueError(f"The {item_name} can't be equipped.")

        current_stack = player.equipped.get(slot, [])
        if not self._slot_has_area(slot, current_stack):
            raise ValueError(f"The {slot} slot is full. Remove something first.")

        tags = item_node.properties.get("tags", [])
        other_hand = self._get_extra_hand_slot(tags, slot)
        if other_hand:
            other_stack = player.equipped.get(other_hand, [])
            if not self._slot_has_area(other_hand, other_stack):
                raise ValueError("Both hands are needed for a two-handed item. Free your other hand first.")

        # Full-body items (equips_all_slots tag) occupy every declared slot.
        extra_slots = self._get_extra_slots(tags, equip_slots, slot)
        blocked = [
            s for s in extra_slots
            if not self._slot_has_area(s, player.equipped.get(s, []))
        ]
        if blocked:
            raise ValueError(
                f"The {item_name} covers the {' and '.join(blocked)} slot"
                f"{'' if len(blocked) == 1 else 's'}, but "
                f"{'it is' if len(blocked) == 1 else 'they are'} already occupied."
            )

        stack = player.equipped.setdefault(slot, [])
        if under:
            for index, existing_id in enumerate(stack):
                existing = self.graph.get_node(existing_id)
                if existing and existing.name == under:
                    stack.insert(index + 1, item_node.id)
                    break
            else:
                stack.append(item_node.id)
        else:
            stack.append(item_node.id)

        if other_hand:
            player.equipped.setdefault(other_hand, [])
            player.equipped[other_hand].append(f"__multi_slot_{item_node.id}")

        for extra_slot in extra_slots:
            player.equipped.setdefault(extra_slot, [])
            player.equipped[extra_slot].append(f"__multi_slot_{item_node.id}")

        self.graph.add_edge(Edge(
            source=item_node.id,
            target=player_id,
            type=EDGE_EQUIPPED,
            properties={"slot": slot}
        ))

        item_node.properties.pop("last_relation", None)

        trigger_outputs = self.triggers._execute_triggers(item_node, "on_equip", game_state=self.world)

        self._maybe_update_equipment_description(player)

        area_name = None
        current_area = self.player_manager.current_area
        if current_area:
            area_name = current_area.name
        self.logging.record_turn_event(
            self.player_manager.active_player,
            "equip",
            f"equipped the {item_name} on {slot}",
            area_name=area_name
        )

        output = f"You equip the {item_name} on your {slot}."
        if extra_slots:
            covered = ', '.join(extra_slots)
            output += f" It also covers your {covered}."
        if trigger_outputs:
            output += "\n" + "\n".join(trigger_outputs)
        return output

    def _sync_equipped_from_graph(self, player, player_id):
        """Rebuild player.equipped from graph EDGE_EQUIPPED edges to fix desyncs."""
        from collections import defaultdict
        equipped_items = defaultdict(list)
        for edge in self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
            slot_name = edge.properties.get("slot", "")
            if slot_name:
                equipped_items[slot_name].append(edge)
        for slot_name in player.equipped:
            if slot_name in equipped_items:
                edges = sorted(equipped_items[slot_name], key=lambda e: e.properties.get("order", 0))
                player.equipped[slot_name] = [e.source for e in edges]
            else:
                player.equipped[slot_name] = []

    def unequip_item(self, slot: str = None, item_name: str = None) -> str:
        """Unequip an item from a slot or by item name. Returns output message."""
        player = self.player_manager.get_active_player_obj()
        if not player:
            raise ValueError("No active player.")
        if player.state in ["sleeping", "unconscious", "dead", "bound"]:
            raise ValueError(f"You can't unequip items while {player.state}.")

        player_id = self.player_manager.get_player_node_id(self.player_manager.active_player)

        def _clean_multi_slot_markers(removed_id):
            """Remove multi-slot markers for the given item from all slots."""
            marker = f"__multi_slot_{removed_id}"
            for s in list(player.equipped.keys()):
                player.equipped[s] = [
                    x for x in player.equipped[s] if str(x) != marker
                ]

        # Desync recovery: if slot is targeted but its stack is empty, rebuild from graph
        if slot and slot in player.equipped and not player.equipped[slot]:
            self._sync_equipped_from_graph(player, player_id)
            if not player.equipped[slot]:
                raise ValueError(f"Nothing equipped in your {slot}.")

        if slot and slot in player.equipped and player.equipped[slot]:
            item_id = player.equipped[slot].pop()
            if self._is_marker(item_id):
                player.equipped[slot] = [
                    x for x in player.equipped[slot] if str(x) != item_id
                ]
                real_id = str(item_id).replace("__multi_slot_", "")
                _clean_multi_slot_markers(real_id)
                self.graph.remove_edge(real_id, player_id, EDGE_EQUIPPED)
                self.graph.add_edge(Edge(source=real_id, target=player_id, type=EDGE_CARRYING))
                real_item = self.graph.get_node(real_id)
                if real_item:
                    self.triggers._execute_triggers(real_item, "on_unequip", game_state=self.world)
                    area_name = None
                    current_area = self.player_manager.current_area
                    if current_area:
                        area_name = current_area.name
                    self.logging.record_turn_event(
                        self.player_manager.active_player,
                        "unequip",
                        f"unequipped the {real_item.name} from {slot}",
                        area_name=area_name
                    )
                    self._maybe_update_equipment_description(player)
                    return f"You unequip the {real_item.name} from your {slot}."
                self._maybe_update_equipment_description(player)
                return f"You unequip the item from your {slot}."
            _clean_multi_slot_markers(item_id)
            self.graph.remove_edge(item_id, player_id, EDGE_EQUIPPED)
            self.graph.add_edge(Edge(source=item_id, target=player_id, type=EDGE_CARRYING))
            item_node = self.graph.get_node(item_id)
            if item_node:
                self.triggers._execute_triggers(item_node, "on_unequip", game_state=self.world)
                area_name = None
                current_area = self.player_manager.current_area
                if current_area:
                    area_name = current_area.name
                self.logging.record_turn_event(
                    self.player_manager.active_player,
                    "unequip",
                    f"unequipped the {item_node.name} from {slot}",
                    area_name=area_name
                )
                self._maybe_update_equipment_description(player)
                return f"You remove the {item_node.name} from your {slot}."
            self._maybe_update_equipment_description(player)
            return f"You unequip from your {slot}."

        if item_name:
            for slot_name, stack in list(player.equipped.items()):
                for index, item_id in enumerate(stack):
                    if self._is_marker(item_id):
                        continue
                    item_node = self.graph.get_node(item_id)
                    if item_node and item_node.name.lower() == item_name.lower():
                        removed = stack.pop(index)
                        self.graph.remove_edge(removed, player_id, EDGE_EQUIPPED)
                        self.graph.add_edge(Edge(source=removed, target=player_id, type=EDGE_CARRYING))
                        _clean_multi_slot_markers(removed)
                        if item_node:
                            self.triggers._execute_triggers(item_node, "on_unequip", game_state=self.world)
                            area_name = None
                            current_area = self.player_manager.current_area
                            if current_area:
                                area_name = current_area.name
                            self.logging.record_turn_event(
                                self.player_manager.active_player,
                                "unequip",
                                f"unequipped the {item_node.name} from {slot_name}",
                                area_name=area_name
                            )
                        self._maybe_update_equipment_description(player)
                        return f"You remove the {item_name} from your {slot_name}."
            raise ValueError(f"You aren't wearing '{item_name}'.")

        raise ValueError(
            "Specify which slot to unequip from (e.g. 'unequip head') or which item ('unequip helmet')."
        )

    def get_visible_equipment(self, player_name: str = None) -> dict:
        """Return the outermost item of each slot for a player (what others see at a glance)."""
        player = self.player_manager.get_player(player_name or self.player_manager.active_player)
        if not player:
            return {}
        visible = {}
        for slot, stack in player.equipped.items():
            if slot in ("hand_left", "hand_right"):
                visible_items = [
                    self.graph.get_node(item_id) for item_id in stack
                    if item_id and not self._is_marker(item_id)
                ]
                visible_items = [
                    n for n in visible_items
                    if n and not self._is_intrinsic_ability(n)
                ]
                real = [n.name for n in visible_items]
                if real:
                    visible[slot] = real[-1]
                else:
                    markers = [
                        item_id for item_id in stack
                        if str(item_id).startswith("__multi_slot_")
                    ]
                    if markers:
                        real_id = markers[-1].replace("__multi_slot_", "")
                        real_node = self.graph.get_node(real_id)
                        if real_node:
                            tags = real_node.properties.get("tags", [])
                            if isinstance(tags, str):
                                tags = [t.strip() for t in tags.split(",")]
                            if "two_handed" in tags:
                                visible[slot] = f"{real_node.name} (two-handed)"
                            elif "equips_all_slots" in tags:
                                visible[slot] = f"{real_node.name} (part of a full-body suit)"
                            else:
                                visible[slot] = real_node.name
                continue
            if not stack:
                continue
            real_nodes = [
                self.graph.get_node(item_id) for item_id in stack
                if item_id and not self._is_marker(item_id)
            ]
            real_nodes = [
                n for n in real_nodes
                if n and not self._is_intrinsic_ability(n)
            ]
            if real_nodes:
                visible[slot] = real_nodes[-1].name
        return visible

    @staticmethod
    def _is_intrinsic_ability(item_node: Optional[Node]) -> bool:
        """True when an item is an intrinsic ability rather than a physical object."""
        if item_node is None:
            return False
        tags = item_node.properties.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        return bool(INTRINSIC_ABILITY_TAGS.intersection(tags))

    def _drop_intrinsic_abilities(self, full: dict, player_name: str) -> dict:
        """Remove equipped intrinsic abilities from an equipment dict by name.

        Used when building the *visible appearance* of a character, so
        spells/talents never leak into what others see.
        """
        player_id = self.player_manager.get_player_node_id(player_name)
        hidden_names = set()
        for edge in self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED):
            node = self.graph.get_node(edge.source)
            if node and self._is_intrinsic_ability(node):
                hidden_names.add(node.name)
        if not hidden_names:
            return full
        return {
            slot: [name for name in names if name not in hidden_names]
            for slot, names in full.items()
        }

    def get_full_equipment(self, player_name: str = None) -> dict:
        """Return all equipment stacks for a player."""
        player = self.player_manager.get_player(player_name or self.player_manager.active_player)
        if not player:
            return {}
        full = {}
        for slot, stack in player.equipped.items():
            real = [
                self.graph.get_node(item_id) for item_id in stack
                if item_id and not self._is_marker(item_id)
            ]
            if real:
                full[slot] = [n.name for n in real]
        return full

    def _equipped_full_body_items(self, player) -> List[tuple]:
        """Return (node, declared_slots) for each equipped item tagged equips_all_slots."""
        result = []
        seen = set()
        for stack in player.equipped.values():
            for item_id in stack:
                if self._is_marker(item_id):
                    continue
                node = self.graph.get_node(item_id)
                if node and node.id not in seen and "equips_all_slots" in node.properties.get("tags", []):
                    seen.add(node.id)
                    slots = node.properties.get("equip_slots", [])
                    result.append((node, slots if isinstance(slots, list) else []))
        return result

    def get_equipment_narrative(self, player_name: str = None, viewer_name: str = None) -> str:
        """Return a plain-English description of visible equipment.
        Viewer sees surface-level. Self-knowledge sees stacks."""
        player = self.player_manager.get_player(player_name or self.player_manager.active_player)
        if not player:
            return ""
        is_self = (viewer_name is None) or (viewer_name == (player_name or self.player_manager.active_player))
        # Full-body items (equips_all_slots) are reported once with every covered
        # slot, so their primary-slot line isn't repeated in the per-slot loop.
        full_body = self._equipped_full_body_items(player)
        full_body_nodes = {node.id for node, _ in full_body}
        reported_slots = set()
        for stack_slot, stack in player.equipped.items():
            real_ids = [i for i in stack if not self._is_marker(i)]
            if not real_ids:
                continue
            top_node = self.graph.get_node(real_ids[-1])
            if top_node and top_node.id in full_body_nodes:
                reported_slots.add(stack_slot)

        if is_self:
            full = self.get_full_equipment(player_name)
            parts = []
            for slot in ["head", "neck", "torso", "arms", "hands", "legs", "feet", "back", "waist", "accessory"]:
                if slot in reported_slots:
                    continue
                items = full.get(slot, [])
                if not items:
                    continue
                if len(items) == 1:
                    parts.append(f"{items[0]} on your {slot}")
                else:
                    outer = items[-1]
                    inner = ", ".join(items[:-1])
                    parts.append(f"{outer} over {inner} on your {slot}")
            for node, slots in full_body:
                covered = ", ".join(slots) if slots else node.name
                parts.append(f"{node.name} over your {covered}")
            hands = []
            for hand in ["hand_left", "hand_right"]:
                if hand in full:
                    hands.extend(full[hand])
            if hands:
                parts.append(f"carrying {' and '.join(hands)} in your hands")
            acc = full.get("accessory", [])
            if acc:
                parts.append(f"wearing {', '.join(acc)} as accessories")
            if not parts:
                return "You are wearing nothing."
            return "You are wearing: " + "; ".join(parts) + "."
        else:
            visible = self.get_visible_equipment(player_name)
            parts = []
            for slot in ["head", "neck", "torso", "arms", "hands", "legs", "feet", "back", "waist"]:
                if slot in visible and slot not in reported_slots:
                    parts.append(f"a {visible[slot]} on their {slot}")
            for node, slots in full_body:
                covered = ", ".join(slots) if slots else node.name
                parts.append(f"a {node.name} over their {covered}")
            if "accessory" in visible:
                parts.append(f"wearing {visible['accessory']}")
            if "hand_left" in visible or "hand_right" in visible:
                hand_items = []
                if "hand_left" in visible:
                    hand_items.append(visible["hand_left"])
                if "hand_right" in visible:
                    hand_items.append(visible["hand_right"])
                parts.append(f"holding {' and '.join(hand_items)}")
            if not parts:
                return f"{player.name} is wearing nothing."
            return f"{player.name} is wearing " + ", ".join(parts) + "."

    def _maybe_update_equipment_description(self, player):
        """Auto-update description only if auto_generate_descriptions is enabled."""
        if self.world is not None and not getattr(self.world, 'auto_generate_descriptions', True):
            return
        self._update_equipment_description(player)

    def _update_equipment_description(self, player):
        """Rebuild player.description from base_description and current equipment.
        Tries LLM first, falls back to code-generated 3rd-person text."""
        base = player.base_description or ''
        full = self.get_full_equipment(player.name) or {}
        full = self._drop_intrinsic_abilities(full, player.name)

        equip_lines = []
        for slot in ['head', 'neck', 'torso', 'arms', 'hands', 'legs', 'feet', 'back', 'waist', 'accessory', 'hand_left', 'hand_right']:
            items = full.get(slot, [])
            if items:
                equip_lines.append(f"- {slot}: {' → '.join(items)} (innermost to outermost)")
        equip_text = '\n'.join(equip_lines) if equip_lines else 'Nothing worn.'

        prompt = (
            "You are writing a visual appearance description for a character in a fantasy RPG.\n\n"
            f"BASELINE APPEARANCE (naked physical traits):\n{base if base else '(none described)'}\n\n"
            f"CURRENT EQUIPMENT:\n{equip_text}\n\n"
            "Write a vivid, natural 3rd-person description of how this character looks right now. "
            "Merge their baseline physical traits with what they're wearing into smooth prose. "
            "2-4 sentences. Do not list slots or use bullet points. "
            "Describe only visible appearance — no backstory, no personality."
        )

        self.logging.log_llm_call("_update_equipment_description", prompt, player_name=player.name)

        parts = [base] if base else []
        slot_labels = {
            'head': 'head', 'neck': 'neck', 'torso': 'torso', 'arms': 'arms',
            'hands': 'hands', 'legs': 'legs', 'feet': 'feet', 'back': 'back',
            'waist': 'waist', 'accessory': 'accessory',
            'hand_left': 'left hand', 'hand_right': 'right hand'
        }
        fallback_parts = []
        for slot in ['head', 'neck', 'torso', 'arms', 'hands', 'legs', 'feet', 'back', 'waist', 'accessory']:
            items = full.get(slot, [])
            if items:
                outermost = items[-1]
                inner = items[:-1]
                if inner:
                    fallback_parts.append(f"{outermost} over {'/'.join(inner)} on their {slot_labels.get(slot, slot)}")
                else:
                    fallback_parts.append(f"{outermost} on their {slot_labels.get(slot, slot)}")
        for hand in ['hand_left', 'hand_right']:
            items = full.get(hand, [])
            if items:
                fallback_parts.append(f"{items[-1]} in their {slot_labels.get(hand, hand)}")
        if fallback_parts:
            parts.append(f"{player.name} is wearing " + ", ".join(fallback_parts) + ".")
        player.description = '\n'.join(parts)

    def update_equipment_description(self, player):
        return self._update_equipment_description(player)

    def add_entertainment_gain(self, amount: int = 5):
        """Add entertainment value to the active player."""
        player = self.player_manager.get_active_player_obj()
        if player:
            player.vitals["Entertainment"] = min(
                100, player.vitals.get("Entertainment", 50) + amount
            )

    def get_hygiene_modifier(self, player_name: str = None) -> int:
        """Return a social penalty modifier based on Hygiene level.
        Returns 0 at 100 Hygiene, down to -5 at 0 Hygiene."""
        player = self.player_manager.get_player(player_name or self.player_manager.active_player)
        if not player:
            return 0
        hygiene = player.vitals.get("Hygiene", 100)
        return -((100 - hygiene) // 20)
