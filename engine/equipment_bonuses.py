"""Aggregate equipment bonuses from equipped items.

Reads item properties and tags to compute defense, weapon damage,
effective temperature range, and type-based resistances.
"""
import re
from typing import Dict, List, Optional, Tuple
from graph import Node, EDGE_EQUIPPED


# Tags that flag an item as contributing to defense
DEFENSE_TAGS = {"armor", "clothing"}


def get_equipment_nodes(player, graph) -> List[Node]:
    """Return all item nodes currently equipped by a player."""
    player_node_id = f"player_{player.name}".replace(' ', '_')
    nodes = []
    for edge in graph.get_edges_for_target(player_node_id, EDGE_EQUIPPED):
        node = graph.get_node(edge.source)
        if node and node.type == "item":
            nodes.append(node)
    return nodes


def parse_damage(value) -> tuple:
    """Parse a unified damage field into (count, sides, flat_bonus).

    Accepts:
      "2d6+3", "1d8"  → dice notation (count > 0)
      "8", 8          → flat damage (count == 0, flat_bonus = value)
      None, ""        → (0, 0, 0)

    Returns (count, sides, flat_bonus). count > 0 means dice.
    """
    if value is None or value == '':
        return (0, 0, 0)
    if isinstance(value, str) and ('d' in value.lower()):
        m = re.match(r'^(\d+)[dD](\d+)(?:\s*[+-]\s*(\d+))?$', value.strip())
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
        return (0, 0, 0)
    try:
        flat = int(value)
        return (0, 0, flat)
    except (ValueError, TypeError):
        return (0, 0, 0)


def aggregate_bonuses(player, graph) -> dict:
    """Aggregate all equipment bonuses for a player.

    Returns:
        defense (int): sum of 'defense' from armor/clothing
        damage (int): highest flat 'damage' from weapon-tagged items
        damage_dice (tuple|None): best (count, sides, flat_bonus) from weapon
        damage_skill (str|None): skill name for damage modifier from best weapon
        damage_type (str|None): damage type from best weapon
        insulation (int): sum of 'insulation' from worn items (shifts effective temp)
        resistances (dict): damage_type → total resistance value
    """
    defense = 0
    damage = 0
    damage_dice = (0, 0, 0)
    damage_skill = None
    damage_type = None
    insulation = 0
    resistances = {}
    wind_resistance = 0
    water_resistance = 0

    for node in get_equipment_nodes(player, graph):
        props = node.properties or {}
        tags = [t.lower() for t in props.get("tags", [])]

        if any(t in DEFENSE_TAGS for t in tags):
            defense += int(props.get("defense", 0))

        if "weapon" in tags:
            parsed = parse_damage(props.get("damage"))
            if parsed[0] > 0:
                # dice: track best (more dice, then more sides)
                if parsed[0] > damage_dice[0] or (parsed[0] == damage_dice[0] and parsed[1] > damage_dice[1]):
                    damage_dice = parsed
                    damage_skill = props.get("damage_skill") or None
                    damage_type = props.get("damage_type") or None
            elif parsed[2] > damage:
                damage = parsed[2]

        if "resistance" in tags:
            item_resists = props.get("resistances", {})
            if isinstance(item_resists, dict):
                for dtype, val in item_resists.items():
                    try:
                        resistances[dtype] = max(resistances.get(dtype, 0), int(val))
                    except (ValueError, TypeError):
                        pass

        insulation += int(props.get("insulation", 0))
        # task-231: wind/water resistance are max-percentile over worn items.
        try:
            wind_resistance = max(wind_resistance, int(props.get("wind_resistance", 0) or 0))
            water_resistance = max(water_resistance, int(props.get("water_resistance", 0) or 0))
        except (ValueError, TypeError):
            pass

    # Wet clothing (task-190): soaked garments insulate far worse. Levels
    # scale the loss — 1: 60% kept, 2: 40%, 3: 20%.
    wet_levels = [
        inst.get("level", 1) for cid, instances in getattr(player, "conditions", {}).items()
        if cid == "wet" for inst in instances if inst is not None
    ]
    if wet_levels:
        keep = {1: 0.6, 2: 0.4, 3: 0.2}.get(max(wet_levels), 0.6)
        insulation = int(insulation * keep)

    return {
        "defense": defense,
        "damage": damage,
        "damage_dice": damage_dice if damage_dice != (0, 0, 0) else None,
        "damage_skill": damage_skill,
        "damage_type": damage_type,
        "insulation": insulation,
        "resistances": resistances,
        "wind_resistance": wind_resistance,
        "water_resistance": water_resistance,
    }


def effective_temperature(ambient_temp: float, bonuses: dict,
                          wind_level: str = "none", humidity: str = "dry") -> float:
    """Shift ambient temperature by equipment insulation, wind chill, humidity.

    Defaulted kwargs (task-231/232): existing callers keep working untouched;
    callers with environment context pass ``env.get("wind")`` /
    ``env.get("humidity")`` for wind chill & humidity feel. Wind chill is
    resisted by item ``wind_resistance``; the humidity modifier depends on
    whether the air is hot (>20°C → feels warmer) or cold (→ feels colder).
    """
    from engine.weather_forecast import WIND_CHILL, HUMIDITY_TEMP_MOD
    insulation = bonuses.get("insulation", 0)

    wind_chill = WIND_CHILL.get(str(wind_level or "none"), 0)
    if wind_chill:
        wind_resist = float(bonuses.get("wind_resistance", 0) or 0)
        wind_chill = wind_chill * (1.0 - min(max(wind_resist, 0) / 100.0, 0.85))

    hot = ambient_temp + insulation > 20
    humid_mod = HUMIDITY_TEMP_MOD.get(str(humidity or "dry"), (0, 0))
    humidity_mod = humid_mod[0] if hot else humid_mod[1]

    return ambient_temp + insulation + wind_chill + humidity_mod


def resisted_damage(base_damage: int, damage_type: str, bonuses: dict) -> int:
    """Reduce damage by the player's resistance to the given type."""
    resist = bonuses.get("resistances", {}).get(damage_type, 0)
    return max(0, base_damage - resist)
