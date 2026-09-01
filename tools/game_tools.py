#game_tools.py
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "move",
            "description": "Move the active player in a direction",
            "parameters": {
                "type": "object",
                "properties": {"direction": {"type": "string"}},
                "required": ["direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "look",
            "description": "Describe the current area.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_state",
            "description": "Get a summary of the active player's state and area.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_item",
            "description": "Take an item from the area into the active player's inventory.",
            "parameters": {"type": "object", "properties": {"item_name": {"type": "string"}}, "required": ["item_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "drop_item",
            "description": "Drop an item from inventory into the area.",
            "parameters": {"type": "object", "properties": {"item_name": {"type": "string"}}, "required": ["item_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "use_item",
            "description": "Use an item (optional target).",
            "parameters": {"type": "object", "properties": {"item_name": {"type": "string"}, "target": {"type": "string"}}, "required": ["item_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rest",
            "description": "Rest for N minutes, optionally on an item (e.g., bed).",
            "parameters": {"type": "object", "properties": {"minutes": {"type": "integer"}, "target": {"type": "string"}}, "required": ["minutes"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_inventory",
            "description": "List names of items in the active player's inventory.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fumble_around",
            "description": "Blindly search in darkness when you can't see. Uses Perception check with disadvantage.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "switch_player",
            "description": "Switch the active player by name.",
            "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        }
    }
]


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return f"Error: {e}"


def get_tools(world):
    """Return a mapping of tool name -> callable. `world` should be a VirtualWorld instance."""
    def _ensure_tick():
        try:
            if not getattr(world, '_action_time_consumed', False):
                world.tick(1)
        except Exception:
            pass
    def tool_move(direction: str):
        out = _safe_call(world.move_to_area, direction)
        _ensure_tick()
        return out

    def tool_look():
        try:
            desc = world.get_area_description()
            items = world.get_area_items()
            _ensure_tick()
            return {"description": desc, "items": items}
        except Exception as e:
            return f"Error: {e}"

    def tool_get_state():
        p = world.player
        current_area = world.current_area
        
        # Build comprehensive state information
        out = {
            "player": {
                "name": p.name,
                "state": p.state,
                "state_timer": getattr(p, 'state_timer', 0),
                "vitals": p.vitals,
                "stats": p.stats,
                "skills": p.skills,
                "traits": p.traits,
                "inventory": [],
                "discovered_exits": list(p.discovered_exits) if hasattr(p, 'discovered_exits') else []
            },
            "area": {
                "name": current_area.name if current_area else None,
                "description": current_area.description if current_area else "",
                "environment": current_area.environment if current_area else {},
                "exits": list(current_area.exits.keys()) if current_area else [],
                "items": [i.name for i in current_area.items] if current_area else [],
                # Detailed exit info including states and locked_with requirements
                "exits_detail": current_area.exits if current_area else {}
            },
            "game": {
                "time": world.get_current_time(),
                "time_ticks": world.time_ticks,
                "recent_logs": world.game_log[-5:] if len(world.game_log) >= 5 else world.game_log[:],
            }
        }
        
        # Add AI-actionable advice based on current state
        advice = []
        
        # Check vitals and provide specific recommendations
        vitals = p.vitals
        if vitals.get("Energy", 100) <= 50:
            advice.append("Low Energy: Consider resting (rest 10) or using energizing items (coffee, energy drinks).")
        if vitals.get("Hunger", 100) <= 50:
            advice.append("Low Hunger: Find food using inventory items or look for edible objects in the area.")
        if vitals.get("Thirst", 100) <= 50:
            advice.append("Low Thirst: Seek drinks immediately. Check inventory for beverages or look for liquid sources.")
        if vitals.get("HP", 100) < 70:
            advice.append("Low HP: Use healing items (medicine, potions) or rest to regenerate (requires Energy/Hunger/Thirst > 25%).")
        if vitals.get("Hygiene", 100) <= 50:
            advice.append("Low Hygiene: Look for soap or bathing facilities.")
        if vitals.get("Social", 100) <= 50:
            advice.append("Low Social: Try speaking to someone. Company restores social well-being — solitude drains it.")
        
        # Environmental issues
        if current_area:
            env = current_area.environment
            def _light_to_level(val):
                try:
                    v = int(val)
                except (ValueError, TypeError):
                    return str(val) if str(val) in ('pitch_black','dim','normal','bright','blinding') else 'normal'
                if v <= 20: return 'pitch_black'
                elif v <= 40: return 'dim'
                elif v <= 70: return 'normal'
                elif v <= 90: return 'bright'
                else: return 'blinding'
            light_level = _light_to_level(env.get("light", 80))
            if light_level in ('pitch_black', 'dim') and not (isinstance(p.traits, dict) and (p.traits.get("dark_vision") or p.traits.get("darkvision"))):
                advice.append("Darkness: Light level too low. Use a light source (flashlight, candle, lamp) to see.")
            if env.get("air") == "toxic":
                advice.append("CRITICAL: Toxic air damaging HP! Find way to improve air quality or leave immediately.")
            if env.get("temperature") > 35:
                advice.append("Dangerous heat: Finding shade, water, or cooler area is urgent.")
            if env.get("temperature") < 0:
                advice.append("Freezing temperatures: Seek warmth immediately to prevent HP loss.")
            if env.get("smell") in ["mold", "rot", "urine"] and vitals.get("Hygiene", 100) > 30:
                advice.append("Foul smell: Consider moving to a different area or cleaning the area.")
        
        # Player state restrictions
        if p.state in ["sleeping", "unconscious"]:
            advice.append(f"Currently {p.state}: Wait for state timer to expire or wake up naturally.")
        elif p.state in ["bound"]:
            advice.append("You are bound! Need to struggle or find help to free yourself.")
        
        # Check for locked exits — triggers handle unlocking now
        if current_area:
            for exit_name, exit_data in current_area.exits.items():
                if exit_data.get("state") == "locked":
                    advice.append(f"Locked exit '{exit_name}': Try using a key item on it.")
        
        out["advice"] = advice
        
        _ensure_tick()
        return out

    def tool_take_item(item_name: str):
        out = _safe_call(world.take_item, item_name)
        _ensure_tick()
        return out

    def tool_drop_item(item_name: str):
        out = _safe_call(world.drop_item, item_name)
        _ensure_tick()
        return out

    def tool_use_item(item_name: str, target: str = None):
        if target:
            out = _safe_call(world.use_item_on, item_name, target)
        else:
            out = _safe_call(world.use_item, item_name)
        _ensure_tick()
        return out

    def tool_rest(minutes: int, target: str = None):
        out = _safe_call(world.rest, minutes, target)
        _ensure_tick()
        return out

    def tool_list_inventory():
        out = {"inventory": world.get_inventory()}
        _ensure_tick()
        return out

    def tool_switch_player(name: str):
        try:
            world.set_active_player(name)
            out = {"status": "ok", "active": world.active_player}
            _ensure_tick()
            return out
        except Exception as e:
            return f"Error: {e}"
    def tool_fumble_around(action: str = ""):
        out = _safe_call(world.fumble_around)
        _ensure_tick()
        return out

    return {
        "move": tool_move,
        "look": tool_look,
        "get_state": tool_get_state,
        "take_item": tool_take_item,
        "drop_item": tool_drop_item,
        "use_item": tool_use_item,
        "rest": tool_rest,
        "list_inventory": tool_list_inventory,
        "switch_player": tool_switch_player,
        "fumble_around": tool_fumble_around, 
    }
