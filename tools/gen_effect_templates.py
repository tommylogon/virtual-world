#!/usr/bin/env python3
"""Generate library template items — one per trigger effect (task: template items).

Creates data/library/items/template_<effect>.json for EVERY effect type in
engine.triggers.constants. Each item carries a wired ``triggers`` array
(trigger_type on_use → the effect's params) so placing the item and using it
demonstrates the effect. Names follow ``template_<effect>``; the human name is
"Template: <Effect label>".

Effects that mutate the world state dangerously (end_scenario,
restart_scenario) are included with explicit WARNING labels in the name and
description so nobody wires them into a live scenario by accident.

Re-run after adding new effect types:  python tools/gen_effect_templates.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from engine.triggers.constants import EFFECT_TYPES  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "library", "items")

#: Human-readable labels
LABELS = {
    "destroy_self": "Destroy Self",
    "message": "Message",
    "damage": "Damage",
    "save": "Save Gate",
    "heal": "Heal",
    "spawn_item": "Spawn Item",
    "spawn_character": "Spawn Character",
    "give_item": "Give Item",
    "remove_item": "Remove Item",
    "consume_item": "Consume Item",
    "set_state": "Set State",
    "set_environment": "Set Environment",
    "teleport": "Teleport",
    "rename": "Rename",
    "unlock_way": "Unlock Way",
    "drain": "Drain (uses)",
    "set_description": "Set Description",
    "append_description": "Append Description",
    "adjust_vital": "Adjust Vital",
    "adjust_environment": "Adjust Environment",
    "set_hidden": "Set Hidden",
    "adjust_uses": "Adjust Uses",
    "end_scenario": "END SCENARIO (warning)",
    "restart_scenario": "RESTART SCENARIO (warning)",
    "apply_condition": "Apply Condition",
    "remove_condition": "Remove Condition",
    "apply_trait": "Apply Trait",
    "remove_trait": "Remove Trait",
    "add_tag": "Add Tag",
    "remove_tag": "Remove Tag",
    "set_parameter": "Set Parameter",
    "adjust_parameter": "Adjust Parameter",
    "surface_memory": "Surface Memory",
    "suppress_memory": "Suppress Memory",
    "unblock_memory": "Unblock Memory",
    "schedule_trigger": "Schedule Trigger",
    "spawn_way": "Spawn Way",
    "spawn_area": "Spawn Area",
    "set_way_target": "Set Way Target",
    "set_way_view": "Set Way View",
    "llm_respond": "LLM Respond",
    "scry": "Scry",
}

#: Effects that mutate scenario state; description carries a loud warning.
DANGEROUS = {"end_scenario", "restart_scenario", "spawn_area", "spawn_way"}

#: Per-effect demo params (the wired trigger's effect params).
DEMO_PARAMS = {
    "message": {"message": "[template:message] You hear a clear, quiet voice: the template spoke."},
    "damage": {"amount": 1, "target": "self", "message": "[template:damage] The template nicks you for 1."},
    "heal": {"amount": 3, "stat": "HP", "target": "self", "message": "[template:heal] Warmth spreads through you (+3 HP)."},
    "save": {
        "stat": "WIS", "dc": 15,
        "on_success": [{"type": "message", "params": {"message": "[template:save] You hold steady."}}],
        "on_fail": [{"type": "message", "params": {"message": "[template:save] You tremble and falter."}}],
    },
    "spawn_item": {"item_id": "apple", "into": "area", "message": "[template:spawn_item] An apple materializes beside you."},
    "spawn_character": {"character_id": "jake", "display_name": "Template Visitor", "area": "self",
                        "message": "[template:spawn_character] A familiar shape steps into view."},
    "give_item": {"item_id": "apple", "target": "self", "message": "[template:give_item] An apple drops into your hands."},
    "remove_item": {"item_id": "apple", "message": "[template:remove_item] Any apple you held is gone."},
    "consume_item": {"item": "apple", "message": "[template:consume_item] One apple you carried is consumed."},
    "set_state": {"node_id": "self", "state": "on", "message": "[template:set_state] The template now reads: on."},
    "set_environment": {"target_node": "self", "light": 90, "temperature": 22, "air": "fresh",
                        "message": "[template:set_environment] The room brightens and warms."},
    "teleport": {"area": "Template Arena", "message": "[template:teleport] The world spins...",
                 "fail_message": "[template:teleport] No 'Template Arena' exists — edit this effect's area to your world."},
    "rename": {"name": "Template (Renamed)", "message": "[template:rename] The template changes name."},
    "unlock_way": {"way_id": "way_template_door", "message": "[template:unlock_way] A distant lock clicks.",
                   "fail_message": "[template:unlock_way] No template door here."},
    "drain": {"amount": 1, "message": "[template:drain] The template's own uses tick down."},
    "set_description": {"target": "self", "value": "This description was REWRITTEN by the set_description template.",
                        "message": "[template:set_description] You read the rewritten text."},
    "append_description": {"target": "self", "text": " [appended by the template.]",
                           "message": "[template:append_description] New words join the description."},
    "adjust_vital": {"stat": "Energy", "amount": 5, "target": "self",
                     "message": "[template:adjust_vital] +5 Energy."},
    "adjust_environment": {"temperature": 2, "light": 5, "target_node": "self",
                           "message": "[template:adjust_environment] The room feels slightly warmer."},
    "set_hidden": {"node_id": "self", "hidden": True,
                   "message": "[template:set_hidden] The template fades from sight (use on hand to find it)."},
    "adjust_uses": {"node_id": "self", "delta": -1, "message": "[template:adjust_uses] One use spent."},
    "end_scenario": {"message": "[template:end_scenario] The scenario ends NOW."},
    "restart_scenario": {"message": "[template:restart_scenario] The scenario restarts NOW."},
    "apply_condition": {"condition": "exhausted", "duration": 3, "level": 1, "target": "self",
                        "message": "[template:apply_condition] A wave of exhaustion washes over you."},
    "remove_condition": {"condition": "exhausted", "target": "self",
                         "message": "[template:remove_condition] The exhaustion lifts."},
    "apply_trait": {"trait": "curious", "target": "self",
                    "message": "[template:apply_trait] A spark of curiosity ignites."},
    "remove_trait": {"trait": "curious", "target": "self",
                     "message": "[template:remove_trait] The curiosity fades."},
    "add_tag": {"node_id": "self", "tag": "template_marked", "message": "[template:add_tag] Marked."},
    "remove_tag": {"node_id": "self", "tag": "template_marked", "message": "[template:remove_tag] Unmarked."},
    "set_parameter": {"node_id": "self", "key": "template_param", "value": "demo",
                      "message": "[template:set_parameter] Parameter set."},
    "adjust_parameter": {"node_id": "self", "key": "template_param", "delta": 1,
                         "message": "[template:adjust_parameter] Parameter nudged."},
    "surface_memory": {"text": "[template:surface_memory] The template surfaces an old memory.",
                       "importance": 3, "message": "[template:surface_memory] A memory surfaces."},
    "suppress_memory": {"keyword": "template", "message": "[template:suppress_memory] Some memories fade back."},
    "unblock_memory": {"keyword": "template", "message": "[template:unblock_memory] Blocked memories resurface."},
    "schedule_trigger": {"delay_ticks": 2, "target": "self", "label": "template delayed",
                         "message": "[template:schedule_trigger] Something is scheduled 2 ticks ahead."},
    "spawn_way": {"name": "Template Door", "current_state": "open", "room1": "self",
                  "message": "[template:spawn_way] A door shimmers into being.",
                  "fail_message": "[template:spawn_way] The door needs authored areas."},
    "spawn_area": {"name": "Template Room", "message": "[template:spawn_area] A new room forms.",
                   "fail_message": "[template:spawn_area] Check the area name."},
    "set_way_target": {"way_id": "way_template_door", "area": "Template Arena",
                       "message": "[template:set_way_target] A door repoints.",
                       "fail_message": "[template:set_way_target] No template door here."},
    "set_way_view": {"way_id": "way_template_door", "view_from_a": "a shimmering corridor",
                     "message": "[template:set_way_view] The door's view shifts.",
                     "fail_message": "[template:set_way_view] No template door here."},
    "llm_respond": {"instructions": "You are the Template Speaker. One short eerie sentence about being a template.",
                    "fallback_message": "[template:llm_respond] The template stays silent.", "max_words": 30},
    "scry": {"target": "Taco Bell", "message": "[template:scry] The image sharpens...",
             "fail_message": "[template:scry] No 'Taco Bell' — edit the target area."},
}


def build_effect(effect_type: str) -> dict:
    label = LABELS.get(effect_type, effect_type.replace("_", " ").title())
    base_desc = (
        f"Template item demonstrating the '{effect_type}' trigger effect. "
        "Use me when on the ground or in your hands; the wired on_use trigger "
        "shows the effect. Place me by importing from the library (library "
        "browser → Item → Import to World)."
    )
    if effect_type in DANGEROUS:
        base_desc = (
            f"⚠️ DANGEROUS TEMPLATE — {label}. "
            "Using this RUNS the effect on the live world immediately. "
            "Keep out of authoring scenarios; use only to understand the mechanic."
        )
    props = {
        "name": f"Template: {label}",
        "description": base_desc,
        "tags": ["template", "demo"],
        "actions": ["examine", "use"],
        "uses": 3 if effect_type in ("drain", "adjust_uses") else -1,
        "max_uses": 3 if effect_type in ("drain", "adjust_uses") else 0,
        "weight": 0.1,
        "current_state": "normal",
        "triggers": [
            {
                "trigger_type": "on_use",
                "effects": [{"type": effect_type, "params": DEMO_PARAMS.get(effect_type, {})}],
            }
        ],
    }
    return props


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    written = []
    for effect_type in EFFECT_TYPES:
        path = os.path.join(OUT_DIR, f"template_{effect_type}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(build_effect(effect_type), f, indent=2, ensure_ascii=False)
        written.append(effect_type)
    print(f"Wrote {len(written)} template items to {OUT_DIR}")
    print("ids:", ", ".join(f"template_{e}" for e in written))


if __name__ == "__main__":
    main()
