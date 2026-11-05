"""Life experience generator and Aura/Diary importer for character backstory.

@module engine/life_experience - offline life-event generation and import into preconceived memories
@contributes deterministic life experience generator, Aura/Diary importer, and scenario injector
@docs docs/virtualWorld/Characters/Life Experience.md
"""

import json
import random
from typing import Any, Dict, List, Optional, Tuple, Union


BACKGROUND_ARCHETYPES = {
    "wanderer": [
        {
            "stage": "childhood",
            "template": "I spent my early years traveling between dusty border settlements, never staying in one place long enough to see the seasons change.",
            "importance": 6,
            "tags": ["childhood", "travel", "wanderer"],
            "category": "episodic",
            "location_hint": "outskirts",
        },
        {
            "stage": "youth",
            "template": "A severe storm on the high road scattered our caravan; I survived three days alone in the scrublands before finding the road again.",
            "importance": 7,
            "tags": ["survival", "hardship", "youth"],
            "category": "episodic",
            "location_hint": "wilderness",
        },
        {
            "stage": "adulthood",
            "template": "I learned to read the shift in mountain winds and navigate the unmapped passes between the old valleys.",
            "importance": 5,
            "tags": ["skill", "navigation", "adulthood"],
            "category": "semantic",
            "location_hint": "mountain",
        },
        {
            "stage": "recent",
            "template": "I arrived here with worn boots and an empty canteen, looking for a dry place to rest before setting out again.",
            "importance": 6,
            "tags": ["arrival", "current_situation"],
            "category": "episodic",
            "location_hint": "camp",
            "goal": {
                "id": "explore_surroundings",
                "text": "Map the nearby safe routes and water sources",
                "priority": 2,
                "category": "personal",
                "status": "active",
            },
        },
    ],
    "scholar": [
        {
            "stage": "childhood",
            "template": "My earliest memory is the scent of vellum and dried ink in the quiet corners of the town archive.",
            "importance": 5,
            "tags": ["childhood", "learning", "archive"],
            "category": "episodic",
            "location_hint": "library",
        },
        {
            "stage": "youth",
            "template": "I copied ancient herbal treatises under candlelight until my eyes ached and my fingers were stained with gall.",
            "importance": 6,
            "tags": ["study", "herbalism", "youth"],
            "category": "episodic",
            "location_hint": "scriptorium",
        },
        {
            "stage": "adulthood",
            "template": "I cataloged forgotten regional dialects and the obscure trade marks of defunct merchant leagues.",
            "importance": 5,
            "tags": ["knowledge", "languages", "scholarship"],
            "category": "semantic",
            "location_hint": "hall",
        },
        {
            "stage": "recent",
            "template": "A disputed historical account drew me here, hoping to verify the rumors of an uncataloged cache.",
            "importance": 7,
            "tags": ["investigation", "quest", "recent"],
            "category": "episodic",
            "location_hint": "study",
            "goal": {
                "id": "verify_historical_cache",
                "text": "Find and transcribe the historical records rumored to be kept here",
                "priority": 1,
                "category": "scholarship",
                "status": "active",
            },
        },
    ],
    "soldier": [
        {
            "stage": "childhood",
            "template": "My family worked the smithy on the garrison edge, mending spearheads and dented iron plate.",
            "importance": 5,
            "tags": ["childhood", "garrison", "craft"],
            "category": "episodic",
            "location_hint": "barracks",
        },
        {
            "stage": "youth",
            "template": "I stood my first night watch on the palisade during a freezing drizzle, listening to the dark outside the ditch.",
            "importance": 6,
            "tags": ["vigilance", "guard", "youth"],
            "category": "episodic",
            "location_hint": "gate",
        },
        {
            "stage": "adulthood",
            "template": "In the skirmish by the sunken ford, our line held long enough for the wagon train to withdraw into the trees.",
            "importance": 8,
            "tags": ["combat", "skirmish", "honor"],
            "category": "episodic",
            "location_hint": "ford",
        },
        {
            "stage": "recent",
            "template": "I left the regiment after my contract lapsed, keeping my service knife and a habit of sleeping with one boot laced.",
            "importance": 6,
            "tags": ["veteran", "survival", "recent"],
            "category": "episodic",
            "location_hint": "quarters",
            "goal": {
                "id": "secure_safe_haven",
                "text": "Identify the defensive strengths and hazards of this settlement",
                "priority": 2,
                "category": "security",
                "status": "active",
            },
        },
    ],
}


def _find_scenario_node(identifier: str, scenario_dict: Optional[dict]) -> Optional[str]:
    """Resolve an identifier (name or node ID) to a real node ID in the scenario.

    Returns the exact node ID if found, else None.
    """
    if not identifier or not scenario_dict:
        return None

    # Check graph.nodes list or dict
    nodes = []
    graph = scenario_dict.get("graph")
    if isinstance(graph, dict) and isinstance(graph.get("nodes"), list):
        nodes = graph["nodes"]
    elif isinstance(scenario_dict.get("nodes"), dict):
        nodes = list(scenario_dict["nodes"].values())
    elif isinstance(scenario_dict.get("nodes"), list):
        nodes = scenario_dict["nodes"]

    ident_clean = str(identifier).strip()
    ident_lower = ident_clean.lower()

    # Exact ID match first
    for n in nodes:
        if isinstance(n, dict):
            nid = str(n.get("id", ""))
            if nid == ident_clean:
                return nid

    # Name match second
    for n in nodes:
        if isinstance(n, dict):
            nname = str(n.get("name", "")).strip().lower()
            if nname == ident_lower:
                return str(n.get("id", ""))

    return None


class LifeExperienceResult:
    """The structured result of an authoring or import pass."""

    def __init__(self, character: str, memories: List[dict], goals: List[dict], report: dict):
        self.character = character
        self.preconceived_knowledge = {"memories": memories}
        self.goals = goals
        self.report = report

    @property
    def memories(self) -> List[dict]:
        return self.preconceived_knowledge.get("memories", [])

    def to_dict(self) -> dict:
        return {
            "character": self.character,
            "preconceived_knowledge": self.preconceived_knowledge,
            "goals": self.goals,
            "report": self.report,
        }


def generate_life_experience(
    character_name: str,
    seed: int = 42,
    background: str = "wanderer",
    stages: int = 4,
    scenario_dict: Optional[dict] = None,
) -> LifeExperienceResult:
    """Deterministically generate authored life experience memories.

    Generating twice with the same inputs and seed produces byte-identical outputs.
    Locations and entities are resolved against the scenario; unresolved references
    are omitted and reported.
    """
    rng = random.Random(seed)
    archetype = BACKGROUND_ARCHETYPES.get(background.lower(), BACKGROUND_ARCHETYPES["wanderer"])

    memories: List[dict] = []
    goals: List[dict] = []
    unresolved_locations: List[dict] = []
    unresolved_entities: List[dict] = []

    # Select templates deterministically
    available_templates = list(archetype)
    rng.shuffle(available_templates)
    selected = available_templates[: max(1, min(stages, len(available_templates)))]
    # Sort chronologically by stage
    stage_order = {"childhood": 0, "youth": 1, "adulthood": 2, "recent": 3}
    selected.sort(key=lambda t: stage_order.get(t.get("stage", ""), 99))

    for idx, tmpl in enumerate(selected):
        text = tmpl["template"].replace("{character}", character_name)
        importance = tmpl.get("importance", 5)
        tags = list(tmpl.get("tags", []))
        category = tmpl.get("category", "episodic")
        loc_hint = tmpl.get("location_hint")

        memory_entry: Dict[str, Any] = {
            "text": text,
            "importance": importance,
            "tags": tags,
            "source": "preconceived",
            "type": "backstory",
            "category": category,
        }

        # Resolve location if scenario provided
        if loc_hint:
            resolved_loc = _find_scenario_node(loc_hint, scenario_dict)
            if resolved_loc:
                memory_entry["location"] = resolved_loc
            else:
                unresolved_locations.append({
                    "event_index": idx,
                    "hint": loc_hint,
                    "message": f"Location hint '{loc_hint}' does not exist in scenario; omitted from memory."
                })

        memories.append(memory_entry)

        # Handle optional goal
        if "goal" in tmpl:
            g = dict(tmpl["goal"])
            g["id"] = f"{character_name.lower().replace(' ', '_')}_{g['id']}"
            goals.append(g)

    report = {
        "generator": "deterministic_v1",
        "seed": seed,
        "background": background,
        "events_count": len(memories),
        "unresolved_locations": unresolved_locations,
        "unresolved_entities": unresolved_entities,
        "unsupported_fields": [],
        "warnings": [],
    }

    return LifeExperienceResult(character_name, memories, goals, report)


def import_diary_export(
    diary_data: Union[dict, str],
    character_name: str,
    scenario_dict: Optional[dict] = None,
) -> LifeExperienceResult:
    """Import events from an Aura/Diary JSON export.

    Extracts first-person memories, verifies locations and entity references against
    the scenario, and reports unsupported fields.
    """
    if isinstance(diary_data, str):
        with open(diary_data, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif isinstance(diary_data, dict):
        data = diary_data
    else:
        raise ValueError("diary_data must be a dict or a file path")

    memories: List[dict] = []
    goals: List[dict] = []
    unresolved_locations: List[dict] = []
    unresolved_entities: List[dict] = []
    unsupported_fields: List[str] = []

    # Check for known unsupported sections in Aura/Diary export
    for key in ["emotional_trajectory", "relationships", "decision_loop_state"]:
        if key in data and data[key]:
            unsupported_fields.append(f"{key}: {len(data[key])} entries (VirtualWorld uses Player vitals/relationships)")

    events = data.get("events") or []
    for idx, evt in enumerate(events):
        if not isinstance(evt, dict):
            continue

        raw_memory = evt.get("raw_memory")
        outcome = evt.get("outcome_text")
        choice = evt.get("choice_made")

        # First-person memory text
        text = raw_memory or (f"{outcome} (I chose: {choice})" if outcome and choice else outcome or choice)
        if not text:
            continue

        # Importance scaled from emotional_impact (-1.0 to 1.0)
        impact = evt.get("emotional_impact", 0.5)
        try:
            val = abs(float(impact))
            importance = max(1, min(10, int(val * 8) + 2))
        except (ValueError, TypeError):
            importance = 5

        age_days = evt.get("age_days", 0)
        tags = ["life_experience", "diary_import"]
        if age_days > 0:
            tags.append(f"age_{age_days // 365}y")

        memory_entry: Dict[str, Any] = {
            "text": text,
            "importance": importance,
            "tags": tags,
            "source": "preconceived",
            "type": "backstory",
            "category": "episodic",
        }

        # Resolve location
        loc_id = evt.get("location_id")
        if loc_id:
            resolved_loc = _find_scenario_node(loc_id, scenario_dict)
            if resolved_loc:
                memory_entry["location"] = resolved_loc
            else:
                unresolved_locations.append({
                    "event_id": evt.get("event_id", idx),
                    "location_id": loc_id,
                    "message": f"Location '{loc_id}' not found in scenario; omitted from memory."
                })

        # Resolve involved persons
        persons = evt.get("involved_persons") or []
        resolved_entities = []
        for p in persons:
            p_name = p if isinstance(p, str) else (p.get("name") or p.get("id"))
            if not p_name:
                continue
            resolved_ent = _find_scenario_node(p_name, scenario_dict)
            if resolved_ent:
                resolved_entities.append(resolved_ent)
            else:
                unresolved_entities.append({
                    "event_id": evt.get("event_id", idx),
                    "person": p_name,
                    "message": f"Involved person '{p_name}' not found in scenario; omitted from memory."
                })

        if resolved_entities:
            memory_entry["entity_ids"] = resolved_entities

        memories.append(memory_entry)

    # Milestones mapping to GIMP goals if explicitly authored
    for m in data.get("milestones") or []:
        if isinstance(m, dict) and m.get("active_pursuit") and m.get("description"):
            goals.append({
                "id": f"milestone_{m.get('id', len(goals))}",
                "text": m["description"],
                "priority": m.get("priority", 2),
                "category": "backstory",
                "status": "active",
            })

    report = {
        "importer": "aura_diary_v1",
        "events_count": len(memories),
        "unresolved_locations": unresolved_locations,
        "unresolved_entities": unresolved_entities,
        "unsupported_fields": unsupported_fields,
        "warnings": [],
    }

    return LifeExperienceResult(character_name, memories, goals, report)


def apply_experience_to_scenario(
    scenario_dict: dict,
    character_name: str,
    result: LifeExperienceResult,
) -> dict:
    """Apply generated or imported life experience to a scenario dictionary.

    Writes to scenario_dict['players'][character_name]['preconceived_knowledge']['memories']
    and avoids duplicating existing entries.
    """
    if "players" not in scenario_dict or not isinstance(scenario_dict["players"], dict):
        scenario_dict["players"] = {}

    if character_name not in scenario_dict["players"] or not isinstance(scenario_dict["players"][character_name], dict):
        scenario_dict["players"][character_name] = {}

    pdata = scenario_dict["players"][character_name]
    if "preconceived_knowledge" not in pdata or not isinstance(pdata["preconceived_knowledge"], dict):
        pdata["preconceived_knowledge"] = {}

    pre = pdata["preconceived_knowledge"]
    if "memories" not in pre or not isinstance(pre["memories"], list):
        pre["memories"] = []

    existing_texts = {m.get("text") for m in pre["memories"] if isinstance(m, dict) and m.get("text")}

    for m in result.memories:
        if m.get("text") not in existing_texts:
            pre["memories"].append(dict(m))
            existing_texts.add(m.get("text"))

    # Apply goals if present
    if result.goals:
        if "goals" not in pdata or not isinstance(pdata["goals"], list):
            pdata["goals"] = []
        existing_goal_ids = {g.get("id") for g in pdata["goals"] if isinstance(g, dict) and g.get("id")}
        for g in result.goals:
            if g.get("id") not in existing_goal_ids:
                pdata["goals"].append(dict(g))
                existing_goal_ids.add(g.get("id"))

    return scenario_dict


def load_experience_into_player(player: Any, result: LifeExperienceResult, graph: Optional[Any] = None) -> int:
    """Load life experience into a live Player instance via AgentMind.

    Returns the number of memories newly added.
    """
    from engine.agent_memory import AgentMind
    mind = AgentMind(player, graph=graph)
    added = mind.load_preconceived(result.preconceived_knowledge)

    # Set goals if present
    if result.goals:
        import engine.goals as goals_engine
        for g in result.goals:
            player.goals = goals_engine.set_goal(
                player.goals,
                g["text"],
                priority=g.get("priority", 2),
                source="backstory",
                motivation=g.get("category", "personal"),
            )[0]

    return added
