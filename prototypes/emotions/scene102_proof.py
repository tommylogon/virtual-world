"""Live Multi-Actor Millwood Scene 102 Proof Harness (task-998).

Reuses VirtualWorld's real simulation plumbing and real `data/scenarios/Millwood.json`
characters, stats, relationships, personas, and memories to run an unscripted
multi-actor Thanksgiving stress-test of Scene 102 ("By Gerald" -> Astrid overhears
-> Maria looks up across the yard).

Real ViWo systems wired directly (zero fake stubs):
  - `data/scenarios/Millwood.json` character nodes, personalities, stats, personas, memories
  - `WorldGraph` + two open-connected outdoor areas (`Gravel Driveway by Gerald` <->
    `Dessert Tables (Bay 2)`) + intra-room `EDGE_BESIDE` anchors for `proximity_hops`
  - `SpeechBroadcaster.broadcast_speech()` (`engine/speech.py`) + `engine/sound.py`
  - Distance-aware `perceive_speech_tone()` (`engine/speech_tone.py`, task-994 & task-996)
  - Strict actor-isolated `Player.memories` + 7-channel `engine/memory_retrieval.py`
  - Track 1: `ProtoDUnifiedEngine` (A + B + C unified, per-target emotions, persona
    habit/quirk tells, trait/memory/witness secondary emotions, autonomic inertia)
  - Track 2: Local LM Studio Actor LLM (`{` JSON prefill) + `compute_involuntary_volume_slip`

Usage:
    python prototypes/emotions/scene102_proof.py --model google/gemma-4-e4b --turns 8
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import create_app
from engine.relationships import ensure_relationship
from graph import EDGE_BESIDE, EDGE_CONNECTION, EDGE_IN, Edge, Node
from player import Player
from prototypes.emotions.autonomic import (
    compute_involuntary_volume_slip,
    compute_regulation_capacity,
    compute_vulnerability_load,
    render_observer_tells,
)
from prototypes.emotions.proto_c_dual_mind import _call_lm_studio_chat, _extract_json_object
from prototypes.emotions.proto_d_unified import ProtoDUnifiedEngine
from prototypes.emotions.schema import CharacterEmotionState, EmotionEvent, FAMILY_BASELINES, MatrixStepResult
from prototypes.emotions.viwo_adapter import (
    ViwoEmotionHarness,
    add_emotional_memory,
    retrieve_real_memories,
)


MILLWOOD_SCENARIO_PATH = REPO_ROOT / "data" / "scenarios" / "Millwood.json"
DEFAULT_REPORT_PATH = Path(__file__).resolve().parent / "scene102_proof_report.json"

AREA_DRIVEWAY = "Gravel Driveway by Gerald"
AREA_DESSERT = "Dessert Tables (Bay 2)"

ACTOR_SYSTEM_PROMPT = (
    "You are roleplaying ONE specific character inside a live VirtualWorld scene. "
    "Stay strictly inside your character's age, voice, memories, and knowledge boundaries. "
    "NEVER reference facts, events, or secrets that are not in your persona, memories, or what you just heard. "
    "Your body's involuntary physical sensations (pounding heart, flushed face, tight throat, habits) are real "
    "physical facts happening to you right now - do not magically erase them. "
    "Speak like a real person in small-town Oklahoma in 2016 - sharp, natural, concise, NEVER therapist-speak, "
    "NEVER melodramatic essays. This is your beat in the conversation: ALWAYS speak an actual spoken line "
    "(1-3 natural sentences in your character's voice, NEVER empty string and NEVER '...').\n"
    "Choose your delivery volume honestly:\n"
    "- 'whisper': quiet, meant only for someone right next to you (set whisper_target to their full name)\n"
    "- 'normal': regular speaking voice (audible to everyone in your immediate driveway area)\n"
    "- 'shout': loud voice that carries 20 feet across the gravel yard to the dessert tables\n"
    "Choose an optional delivery tone ONLY when non-neutral: "
    "null | warm | teasing | sarcastic | cold | hostile | serious | apologetic | guarded.\n"
    "Return ONLY valid JSON with these exact keys:\n"
    '{"inner_monologue":"<1-2 private raw sentences>",'
    '"speech":"<1-3 spoken sentences in character>",'
    '"volume":"whisper|normal|shout",'
    '"whisper_target":"<full name or null>",'
    '"tone":"<canonical tone or null>",'
    '"emote":"<short physical action>",'
    '"cover_lie":false}'
)


def _detect_loaded_embed_model(default_model: str = "text-embedding-nomic-embed-text-v1.5@q4_k_m") -> str:
    """Prefer an already-loaded embedding model in LM Studio to avoid VRAM swap delays."""
    try:
        req = urllib.request.Request("http://127.0.0.1:1234/api/v0/models", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for m in data.get("data", []):
            if m.get("state") == "loaded" and "embed" in str(m.get("id", "")).lower():
                return str(m["id"])
    except Exception:
        pass
    return default_model


def _load_millwood_raw() -> Dict[str, Any]:
    return json.loads(MILLWOOD_SCENARIO_PATH.read_text(encoding="utf-8"))


def _extract_graph_nodes(raw_scenario: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw_nodes = (raw_scenario.get("graph") or {}).get("nodes") or {}
    if isinstance(raw_nodes, dict):
        return {str(k): v for k, v in raw_nodes.items() if isinstance(v, dict)}
    return {str(n.get("id")): n for n in raw_nodes if isinstance(n, dict) and n.get("id")}


def _hydrate_player_from_millwood(
    raw_scenario: Dict[str, Any],
    nodes_by_id: Dict[str, Dict[str, Any]],
    name: str,
    area_name: str,
) -> Player:
    """Copy a real character from data/scenarios/Millwood.json onto a live ViWo Player."""
    pdata = (raw_scenario.get("players") or {})[name]
    node_id = f"player_{name.replace(' ', '_')}"
    ndata = nodes_by_id.get(node_id) or {}
    nprops = ndata.get("properties") or {}

    p = Player(name)
    p.current_area = area_name
    p.description = str(nprops.get("description") or pdata.get("description") or "").strip()
    p.personality = str(nprops.get("personality") or pdata.get("personality") or "").strip()
    if isinstance(pdata.get("stats"), dict):
        p.stats.update(pdata["stats"])
    if isinstance(pdata.get("skills"), dict):
        p.skills.update(pdata["skills"])
    if isinstance(pdata.get("vitals"), dict):
        p.vitals.update(pdata["vitals"])
    p.vitals.update({"Energy": 80, "Hunger": 15, "Thirst": 15, "Sanity": 85, "Temperature": 36.8})
    if isinstance(pdata.get("traits"), dict):
        p.traits = dict(pdata["traits"])
    if isinstance(pdata.get("fear_tags"), list):
        p.fear_tags = list(pdata["fear_tags"])
    if isinstance(pdata.get("relationships"), dict):
        p.relationships = copy.deepcopy(pdata["relationships"])
    if isinstance(pdata.get("memories"), list):
        p.memories = copy.deepcopy(pdata["memories"])
    if isinstance(nprops.get("persona"), dict):
        p.persona = copy.deepcopy(nprops["persona"])
        fears = ((p.persona.get("personality") or {}).get("fears")) or []
        if fears:
            p.fear_tags = list(set(p.fear_tags + [str(f) for f in fears]))
    return p


def build_scene102_world() -> Tuple[Any, Dict[str, Dict[str, Any]]]:
    """Build the real 2-area Johansen Shop Thanksgiving world using Millwood.json characters."""
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = create_app({"TESTING": True})
    world = app.world
    graph = world.graph

    # 1. Two open-connected outdoor areas at 102 Cedar Avenue (Johansen Shop).
    # Ambient noise="normal" (Creedence on Keith's shop speakers + Thanksgiving chatter):
    # - whisper (0): stays in same area, directed whispers stay within friends.
    # - normal (1): effective_pen = 1 - 1 = 0 -> audible to everyone in Driveway (including
    #   Astrid past Gerald's bumper), NOT crossing 20 ft to Maria at Dessert Tables!
    # - shout (2): effective_pen = 2 - 1 = 1 -> crosses open gravel way (cost 0.5) to Maria!
    area_driveway = Node(
        "area_driveway_gerald",
        "area",
        AREA_DRIVEWAY,
        properties={
            "description": (
                "Open gravel driveway outside Keith Johansen's diesel shop beside the primer-grey "
                "'94 Honda Civic ('Gerald') and wooden crates. Creedence hums softly from the shop "
                "speakers; twenty feet across the open gravel sit the Thanksgiving dessert tables."
            ),
            "environment": {"lighting": "normal", "noise": "normal"},
        },
    )
    area_dessert = Node(
        "area_dessert_bay2",
        "area",
        AREA_DESSERT,
        properties={
            "description": (
                "Folding tables by Bay 2 loaded with Maria's flan, pecan pie, sweet potato pie, "
                "paella platters, and hot apple cider. Parents are chatting nearby with clear sightlines "
                "twenty feet across the gravel toward Gerald."
            ),
            "environment": {"lighting": "normal", "noise": "normal"},
        },
    )
    way_gravel = Node(
        "way_open_gravel",
        "way",
        "open gravel yard",
        properties={"state": "open", "see_through": True},
    )
    prop_crates = Node("prop_wooden_crates", "item", "wooden crates", properties={"tags": ["furniture"]})
    prop_gerald = Node("prop_gerald_civic", "item", "Gerald (primer-grey Civic)", properties={"tags": ["vehicle"]})
    prop_tables = Node("prop_dessert_tables", "item", "folding dessert tables", properties={"tags": ["furniture"]})

    for node in (area_driveway, area_dessert, way_gravel, prop_crates, prop_gerald, prop_tables):
        graph.add_node(node)

    graph.add_edge(Edge("area_driveway_gerald", "way_open_gravel", EDGE_CONNECTION, properties={"direction": "east"}))
    graph.add_edge(Edge("way_open_gravel", "area_driveway_gerald", EDGE_CONNECTION, properties={"direction": "west"}))
    graph.add_edge(Edge("area_dessert_bay2", "way_open_gravel", EDGE_CONNECTION, properties={"direction": "west"}))
    graph.add_edge(Edge("way_open_gravel", "area_dessert_bay2", EDGE_CONNECTION, properties={"direction": "east"}))
    graph.add_edge(Edge("prop_wooden_crates", "area_driveway_gerald", EDGE_IN))
    graph.add_edge(Edge("prop_gerald_civic", "area_driveway_gerald", EDGE_IN))
    graph.add_edge(Edge("prop_dessert_tables", "area_dessert_bay2", EDGE_IN))

    # 2. Hydrate the 4 core girls + Jake straight from data/scenarios/Millwood.json!
    raw = _load_millwood_raw()
    nodes_by_id = _extract_graph_nodes(raw)

    zoe = _hydrate_player_from_millwood(raw, nodes_by_id, "zoe mercer", AREA_DRIVEWAY)
    sammy = _hydrate_player_from_millwood(raw, nodes_by_id, "sammy lopez", AREA_DRIVEWAY)
    kayla = _hydrate_player_from_millwood(raw, nodes_by_id, "kayla jenkins", AREA_DRIVEWAY)
    kyrie = _hydrate_player_from_millwood(raw, nodes_by_id, "kyrie johansen", AREA_DRIVEWAY)
    jake = _hydrate_player_from_millwood(raw, nodes_by_id, "jake halloway", AREA_DESSERT)

    # Set canon traits & persona habits/quirks (Zoe already carries full persona from Millwood.json).
    zoe.traits.update({"anxious": 1, "honest": 1})
    zoe.fear_tags = list(set(zoe.fear_tags + ["yelling", "abandonment", "fourth_corner"]))

    sammy.traits.update({"impulsive": 1, "jittery": 1, "fiery": 1})
    sammy.persona = {
        "personality": {
            "habits": ["chews_lip_gloss"],
            "quirks": ["voice_pitches_up_when_flustered"],
            "traits": ["impulsive", "fiery", "loyal"],
        }
    }

    kayla.traits.update({"composed": 1, "guarded": 1, "protective": 1})
    kayla.persona = {
        "personality": {
            "habits": ["smooths_scarred_eyebrow", "folds_hands_like_news_anchor"],
            "quirks": ["voice_drops_an_octave_under_stress"],
            "traits": ["composed", "guarded", "strategic"],
        }
    }

    kyrie.traits.update({"stoic": 1, "protective": 1})
    kyrie.persona = {
        "personality": {
            "habits": ["flexes_taped_right_hand", "looks_past_left_ear_when_lying"],
            "quirks": ["deadpan_under_pressure"],
            "traits": ["stoic", "protective", "practical"],
        }
    }

    # 3. Create Astrid Lopez (24, Dallas) & Maria Lopez (45, Seville/OKC) from the millwood archive.
    # Astrid starts walking over from Dessert Tables (Bay 2) with a cup of cider, arriving beside
    # Gerald's front bumper right as Sammy replies on Turn 1 - so Astrid hears ZERO of the pre-scene
    # banter or Zoe's quiet Turn 0 whisper!
    astrid = Player("astrid lopez")
    astrid.current_area = AREA_DESSERT
    astrid.stats.update({"CHA": 14, "CON": 11, "DEX": 11, "INT": 14, "STR": 10, "WIS": 14})
    astrid.traits = {"protective": 1, "honest": 1, "composed": 1}
    astrid.description = (
        "24-year-old interior designer home from Dallas (UT Austin grad), Sammy's older sister. "
        "Tall, poised, tailored camel coat, holding a paper cup of apple cider two feet past Gerald's bumper."
    )
    astrid.personality = (
        "You are Astrid Lopez, 24, an interior designer living in Dallas and Sammy Lopez's older sister, "
        "home in Millwood for Thanksgiving 2016. You are sharp, poised, lightly sarcastic with Sammy, "
        "and fiercely protective beneath the older-sister banter. You are far sharper about teenagers than "
        "your mother Maria is, and you NEVER lie to your mother ('That's not a thing I do'). "
        "Your biggest real-world fear for Sammy is small-town Millwood ruin: pregnancy, gossip at Mrs. Arredondo's "
        "pharmacy -> church -> Miss Tillery's office, and Sammy getting her heart broken or losing her best friends."
    )
    astrid.persona = {
        "personality": {
            "habits": ["rakes_hair_back_when_tense"],
            "quirks": ["expression_shuts_down_one_lamp_at_a_time"],
            "traits": ["protective", "honest", "composed"],
        }
    }

    maria = Player("maria lopez")
    maria.current_area = AREA_DESSERT
    maria.stats.update({"CHA": 13, "CON": 11, "DEX": 10, "INT": 12, "STR": 10, "WIS": 12})
    maria.traits = {"protective": 1, "warm": 1}
    maria.description = (
        "45-year-old Seville-born general manager of an OKC Spanish tapas restaurant, Sammy and Astrid's mother. "
        "Standing by the Bay 2 dessert tables holding a pie knife beside Folake Jenkins."
    )
    maria.personality = (
        "You are Maria Lopez, 45, Sammy and Astrid's mother, born in Seville, warm and sharp-eared, "
        "mixing natural English with brief Spanish phrases ('Ay, esa nina', 'Que pasa?'). "
        "You believe Sammy, Kayla, Kyrie, and Zoe took an innocent vow of sisterhood and have zero idea "
        "any of them are dating Jake Halloway. If you hear shouting from the driveway, you look up immediately."
    )

    # 4. Seed relationships cleanly across the Thanksgiving cast.
    # Note: Keep Astrid's closeness with Zoe/Kayla/Kyrie low-moderate (acquaintances/sister's friends)
    # so directed whispers among the 4 girls do NOT eavesdrop-leak to Astrid via _whisper_audience!
    for girl in (zoe, sammy, kayla, kyrie):
        for other in (zoe, sammy, kayla, kyrie):
            if girl.name != other.name:
                r, _ = ensure_relationship(girl, other.name, tick=1)
                r["closeness"] = max(float(r.get("closeness", 0) or 0), 82)
                r["label"] = "best friend"
        rj, _ = ensure_relationship(girl, "jake halloway", tick=1)
        rj["closeness"] = max(float(rj.get("closeness", 0) or 0), 88)
        rj["label"] = "boyfriend (secret four-way)"
        rm, _ = ensure_relationship(girl, "maria lopez", tick=1)
        rm["closeness"] = 75 if girl.name == "sammy lopez" else 28
        rm["label"] = "mother" if girl.name == "sammy lopez" else "Sammy's strict mother"
        ra, _ = ensure_relationship(girl, "astrid lopez", tick=1)
        ra["closeness"] = 72 if girl.name == "sammy lopez" else 18
        ra["label"] = "older sister" if girl.name == "sammy lopez" else "Sammy's older sister from Dallas"

    for nm, cl, lbl in (
        ("sammy lopez", 78, "16-year-old little sister"),
        ("maria lopez", 85, "mother"),
        ("kayla jenkins", 20, "Sammy's sharp best friend"),
        ("kyrie johansen", 20, "Sammy's blunt wrestler friend"),
        ("zoe mercer", 18, "Sammy's quiet goth friend"),
        ("jake halloway", 12, "neighbor kid from Maple Street"),
    ):
        r, _ = ensure_relationship(astrid, nm, tick=1)
        r["closeness"] = cl
        r["label"] = lbl

    for nm, cl, lbl in (
        ("sammy lopez", 88, "youngest daughter"),
        ("astrid lopez", 90, "eldest daughter"),
        ("kayla jenkins", 32, "Sammy's polite best friend"),
        ("kyrie johansen", 30, "Keith's daughter"),
        ("zoe mercer", 25, "Sammy's quiet friend"),
        ("jake halloway", 24, "neighbor boy"),
    ):
        r, _ = ensure_relationship(maria, nm, tick=1)
        r["closeness"] = cl
        r["label"] = lbl

    # 5. Seed STRICTLY ISOLATED Thanksgiving (Nov 20-26, 2016) memories per character!
    # Shared by the 4 girls ONLY (NOT Astrid, NOT Maria):
    shared_girl_mems = [
        (
            "Thanksgiving Nov 26 at Keith's shop: All four of us (Kayla, Sammy, Kyrie, Zoe) are secretly dating "
            "Jake Halloway together. Maria Lopez thinks we took a vow of sisterhood; if our parents find out "
            "at Thanksgiving dinner twenty feet away, everything explodes.",
            10,
            ["thanksgiving", "secret", "four_way", "jake halloway", "maria lopez", "parents", "marry"],
            {"label": "anxious", "intensity": 6},
        ),
        (
            "Five minutes ago by Bay 2, Kayla's Stanford brother Tobi grilled Jake on code, called him a "
            "'golden goose', told Jake to email him tonight, and told Kayla to marry him ASAP. We've been "
            "teasing Kayla about it beside Gerald while eating Maria's flan and pie.",
            8,
            ["thanksgiving", "tobi", "golden_goose", "marry", "jake halloway", "kayla jenkins"],
            {"label": "happy", "intensity": 6},
        ),
        (
            "Last Friday Nov 20, our $14.8M blind trust cleared at Arthur Mercer's study and we quietly paid off "
            "Keith's $18,000 parts debt and Emmanuel Jenkins's cardiac ICU bills. Nobody outside the five of us knows.",
            9,
            ["trust", "secret", "keith", "emmanuel", "jake halloway"],
            {"label": "grateful", "intensity": 7},
        ),
    ]
    for girl in (zoe, sammy, kayla, kyrie):
        for txt, imp, tags, emo in shared_girl_mems:
            add_emotional_memory(girl, txt, tick=10, importance=imp, tags=tags, emotion=emo)

    # STRICT EPISTEMIC WALL #1: Tuesday Nov 24 sidewalk confession + Wednesday foyer weight
    # goes to KAYLA and KYRIE ONLY. Sammy, Zoe, Astrid, and Maria do NOT have these memories!
    kayla_kyrie_only_mems = [
        (
            "Tuesday night Nov 24 on the dark sidewalk: Jake broke down and confessed to Kyrie about his "
            "compulsive dark intrusive wiring after a weekend scare despite therapy. Kyrie called Kayla immediately, "
            "and we deliberately kept Sammy and Zoe out of it so they wouldn't panic.",
            10,
            ["tuesday_confession", "secret", "jake halloway", "kyrie johansen", "kayla jenkins"],
            {"label": "afraid", "intensity": 8},
        ),
    ]
    for p in (kayla, kyrie):
        for txt, imp, tags, emo in kayla_kyrie_only_mems:
            add_emotional_memory(p, txt, tick=11, importance=imp, tags=tags, emotion=emo)

    add_emotional_memory(
        kayla,
        "Yesterday Wednesday Nov 25 in my foyer at 808 Oakwood after talking Jake down at the park pavilion, "
        "a heavy uninvited 10-year thought flashed through my head: Future. Family. All of them. I shoved it down "
        "because Folake and church reputation would detonate if anyone guessed.",
        tick=12,
        importance=10,
        tags=["foyer_thought", "future", "marry", "folake", "reputation", "kayla jenkins"],
        emotion={"label": "anxious", "intensity": 8},
    )
    add_emotional_memory(
        sammy,
        "Astrid always looked like an effortless 5'10 movie star while I felt boyish and flat in middle school. "
        "When she uses my full name 'Samantha' or treats me like a clueless kid, it makes me furious and defensive. "
        "I try not to think past senior year because you obviously can't marry four people and it makes my stomach hurt.",
        tick=12,
        importance=9,
        tags=["astrid lopez", "samantha", "marry", "four_way", "future", "insecurity"],
        emotion={"label": "embarrassed", "intensity": 7},
    )
    add_emotional_memory(
        zoe,
        "Even when things feel warm and surreal at Table 4, my quiet dread is that there are four of us in Oklahoma "
        "and real life doesn't leave room for four - and I'm terrified of yelling or being the fourth corner left behind.",
        tick=12,
        importance=9,
        tags=["marry", "future", "fourth_corner", "yelling", "abandonment", "zoe mercer"],
        emotion={"label": "afraid", "intensity": 7},
    )

    # STRICT EPISTEMIC WALL #2: ASTRID knows ZERO of the secrets (no four-way, no trust, no notebooks, no Tuesday).
    astrid_mems = [
        (
            "Thanksgiving at Keith's shop: Maria genuinely believes Sammy and her three friends took a 'vow of sisterhood', "
            "which I immediately think is hilarious nonsense. I've been noticing Sammy glancing across the yard at "
            "Jake Halloway from Maple Street.",
            8,
            ["thanksgiving", "maria lopez", "sammy lopez", "sisterhood", "jake halloway"],
            {"label": "curious", "intensity": 6},
        ),
        (
            "Small-town Millwood reality: if a 16-year-old girl gets pregnant here, Mrs. Arredondo at the pharmacy "
            "tells Miss Yolanda before the test dries, then church, then Miss Tillery's office, and it follows her "
            "forever. I know three girls who swore they were 'being careful'.",
            10,
            ["millwood", "pregnant", "pharmacy", "church", "sammy lopez", "careful"],
            {"label": "afraid", "intensity": 8},
        ),
        (
            "Sammy is sixteen: she still has a stuffed dolphin from Galveston on her bed and cried for two days "
            "last year when a friend stopped texting her back. And I have NEVER lied to Mama in my life - that is "
            "not a thing I do.",
            9,
            ["sammy lopez", "dolphin", "sixteen", "maria lopez", "honesty", "lying"],
            {"label": "loving", "intensity": 8},
        ),
    ]
    for txt, imp, tags, emo in astrid_mems:
        add_emotional_memory(astrid, txt, tick=10, importance=imp, tags=tags, emotion=emo)

    # STRICT EPISTEMIC WALL #3: MARIA knows ZERO of the secrets.
    add_emotional_memory(
        maria,
        "My daughter Sammy and her best friends Kayla, Kyrie, and Zoe are good girls who swore a vow of sisterhood "
        "to focus on school instead of boys. Astrid is home from Dallas and I brought my flan and paella to Keith's shop.",
        tick=10,
        importance=9,
        tags=["thanksgiving", "sammy lopez", "astrid lopez", "sisterhood", "flan"],
        emotion={"label": "happy", "intensity": 7},
    )

    # 6. Add players to real VirtualWorld + wire intra-room spatial anchors (`proximity_hops`)!
    all_actors = (zoe, sammy, kayla, kyrie, astrid, maria, jake)
    for p in all_actors:
        world.add_player(p)
        nid = world.player_manager.get_player_node_id(p.name)
        if nid:
            if p.name in ("zoe mercer", "sammy lopez", "kayla jenkins", "kyrie johansen"):
                graph.add_edge(Edge(nid, "prop_wooden_crates", EDGE_BESIDE))
            elif p.name == "astrid lopez":
                graph.add_edge(Edge(nid, "prop_gerald_civic", EDGE_BESIDE))
            elif p.name in ("maria lopez", "jake halloway"):
                graph.add_edge(Edge(nid, "prop_dessert_tables", EDGE_BESIDE))

    meta = {
        "areas": [AREA_DRIVEWAY, AREA_DESSERT],
        "millwood_reused": ["zoe mercer", "sammy lopez", "kayla jenkins", "kyrie johansen", "jake halloway"],
        "archive_added": ["astrid lopez", "maria lopez"],
    }
    return world, meta


def _build_actor_turn_prompt(
    actor: Player,
    state: CharacterEmotionState,
    last_track1: Optional[MatrixStepResult],
    world: Any,
    harness: ViwoEmotionHarness,
    recalled_memories: List[Dict[str, Any]],
    scene_beat_note: str,
) -> str:
    """Assemble strict actor-isolated Track 2 prompt (own memories, own body, heard speech, same-area tells)."""
    area = getattr(actor, "current_area", AREA_DRIVEWAY)
    same_area_lines: List[str] = []
    for other_name, other_p in world.players.items():
        if other_name == actor.name or getattr(other_p, "current_area", None) != area:
            continue
        other_st = harness.get_state(other_name)
        rel = (actor.relationships or {}).get(other_name) or {}
        closeness = float(rel.get("closeness", 0.0) or 0.0)
        fam_ratio = min(1.0, max(0.0, closeness / 100.0))
        insight = int((actor.stats or {}).get("WIS", 10) or 10)
        other_over = other_st.overload_streak > 0
        other_sup = [ep.family for ep in other_st.episodes if ep.suppressed and not ep.resolved]
        tells = render_observer_tells(
            other_st,
            other_p,
            lighting="normal",
            observer_insight=insight,
            familiarity=fam_ratio,
            overloaded=other_over,
            suppressed_families=other_sup,
        )
        role_lbl = rel.get("label") or "nearby"
        if tells:
            same_area_lines.append(f"- {other_name} ({role_lbl}): {tells}")
        else:
            same_area_lines.append(f"- {other_name} ({role_lbl}): expression composed/unremarkable")

    # Strict hearing isolation: ONLY entries in this actor's own recent_hearing!
    heard_lines: List[str] = []
    for h in (actor.recent_hearing or [])[-6:]:
        spk = h.get("speaker", "someone")
        lvl = h.get("speech_level", "normal")
        verb = {"whisper": "whispered", "shout": "shouted", "scream": "screamed"}.get(lvl, "said")
        adv = h.get("tone_adverb") or ""
        from_dir = f" [from across the gravel, {h['heard_from']}]" if h.get("heard_from") else ""
        tone_part = f" {adv}" if adv else ""
        heard_lines.append(f'- {spk} {verb}{tone_part}{from_dir}: "{h.get("text", "")}"')

    mem_lines = [f"- {m.get('text', '')}" for m in recalled_memories[:4]]
    body_block = (
        last_track1.prompt_your_state
        if last_track1 and last_track1.prompt_your_state
        else "Your pulse is steady and you feel relatively calm right now."
    )

    return (
        f"=== WHO YOU ARE ===\n"
        f"Name: {actor.name}\n"
        f"{actor.personality}\n\n"
        f"=== WHERE YOU ARE ===\n"
        f"Area: {area}\n"
        f"Context: {scene_beat_note}\n\n"
        f"=== PEOPLE RIGHT HERE (WHAT YOU CAN ACTUALLY SEE) ===\n"
        + ("\n".join(same_area_lines) if same_area_lines else "(nobody right beside you)")
        + "\n\n=== WHAT YOU JUST HEARD (STRICTLY WHAT REACHED YOUR EARS) ===\n"
        + ("\n".join(heard_lines) if heard_lines else "(nothing new reached your ears yet)")
        + "\n\n=== MEMORIES SURFACING RIGHT NOW ===\n"
        + ("\n".join(mem_lines) if mem_lines else "(none)")
        + "\n\n=== YOUR STATE (INVOLUNTARY BODY & FEELINGS) ===\n"
        + body_block
        + "\n\nReact naturally as this character right now. Return ONLY valid JSON."
    )


def _run_actor_llm(
    chat_url: str,
    model: str,
    user_prompt: str,
) -> Tuple[Dict[str, Any], float, str]:
    """Call Track 2 Actor LLM on local LM Studio with '{' JSON prefill."""
    messages = [
        {"role": "system", "content": ACTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    t0 = time.perf_counter()
    raw = _call_lm_studio_chat(
        messages,
        url=chat_url,
        model_id=model,
        temperature=0.65,
        max_tokens=None,
        timeout=90,
        json_prefill=True,
    )
    lat_ms = (time.perf_counter() - t0) * 1000.0
    parsed = _extract_json_object(raw) or {}
    return parsed, round(lat_ms, 1), raw


def run_scene102_demo(
    *,
    model: str = "google/gemma-4-e4b",
    embed_model: Optional[str] = None,
    track1_engine: str = "proto_d",
    turns: int = 8,
    offline: bool = False,
    report_path: Optional[Path] = DEFAULT_REPORT_PATH,
) -> Dict[str, Any]:
    """Run the unscripted multi-actor Millwood Scene 102 demo and save full untruncated report."""
    world, world_meta = build_scene102_world()
    chosen_embed = embed_model or _detect_loaded_embed_model()

    if track1_engine == "classifier":
        from prototypes.emotions.proto_e_classifier import ProtoEClassifierEngine

        engine = ProtoEClassifierEngine(model_id="cirimus/modernbert-base-go-emotions")
        chosen_embed = "cirimus/modernbert-base-go-emotions (CPU)"
    else:
        engine = ProtoDUnifiedEngine(
            embed_url="http://127.0.0.1:1234/v1/embeddings",
            embed_model=chosen_embed,
            chat_url="http://127.0.0.1:1234/v1/chat/completions",
            limbic_model=model,
            actor_model=model,
            offline=offline,
        )
    harness = ViwoEmotionHarness(world, engine)

    # Seed realistic pre-scene momentum (Kayla already carrying mild Wednesday foyer tension;
    # Sammy riding playful banter warmth; Zoe's quiet dread ticking up).
    harness.get_state("kayla jenkins").families["fear"] = 22.0
    harness.get_state("sammy lopez").families["happiness"] = 58.0
    harness.get_state("zoe mercer").families["sadness"] = 24.0
    harness.get_state("zoe mercer").families["fear"] = 22.0
    harness.get_state("astrid lopez").families["happiness"] = 55.0

    # Pre-seed the 2 lines of Thanksgiving banter already spoken by Gerald BEFORE Zoe's question.
    # Directed whispers / quiet banter among the 4 girls (Maria does NOT hear these).
    world.narration.broadcast_speech(
        "sammy lopez",
        "Okay, seriously, are we just going to pretend your Stanford brother didn't talk to Jake for ten minutes and tell you to marry him? My mom thinks we took a vow of sisterhood!",
        area_name=AREA_DRIVEWAY,
        speech_level="whisper",
        whisper_target="kayla jenkins",
        tone="teasing",
    )
    world.narration.broadcast_speech(
        "kayla jenkins",
        "Tobi was talking about software equity, Sammy. He called him a golden goose like Jake's a startup. Eat your flan.",
        area_name=AREA_DRIVEWAY,
        speech_level="whisper",
        whisper_target="sammy lopez",
        tone="guarded",
    )
    # Astrid did NOT hear the directed whispers above - verify that right away!
    astrid_pre_heard = len(world.players["astrid lopez"].recent_hearing)
    maria_pre_heard = len(world.players["maria lopez"].recent_hearing)

    last_t1_by_actor: Dict[str, MatrixStepResult] = {}
    transcript: List[Dict[str, Any]] = []
    tick = 20

    def _broadcast_and_appraise(
        speaker_name: str,
        speech_text: str,
        intended_volume: str,
        intended_tone: Optional[str],
        whisper_target: Optional[str],
        emote: str,
        inner_monologue: str,
        actor_lat_ms: float,
        cover_lie: bool = False,
        is_opening_spark: bool = False,
    ) -> Dict[str, Any]:
        nonlocal tick
        tick += 1
        speaker = world.players[speaker_name]
        spk_state = harness.get_state(speaker_name)
        vuln_load, _ = compute_vulnerability_load(speaker, spk_state)
        reg_cap, _ = compute_regulation_capacity(speaker, vuln_load, spk_state)
        spk_over = spk_state.overload_streak > 0
        spk_sup = any(ep.suppressed and not ep.resolved for ep in spk_state.episodes)

        # Check involuntary volume slip (task-997): e.g. flustered Sammy failing to stay at whisper!
        if is_opening_spark:
            actual_vol, slipped, slip_reason = intended_volume, False, ""
        else:
            actual_vol, slipped, slip_reason = compute_involuntary_volume_slip(
                intended_volume,
                spk_state.autonomic,
                reg_cap,
                speaker,
                overloaded=spk_over,
                suppressed=spk_sup,
            )

        # Record pre-broadcast hearing counts so we know EXACTLY who actually heard this utterance!
        before_counts = {nm: len(p.recent_hearing) for nm, p in world.players.items()}

        # Sync Track 1 autonomic/affect into ViWo player before broadcast so speech_tone sees real strain.
        speaker.load_emotions(spk_state.to_36_dim_map())

        # If speaker uttered a cover lie toward family (e.g. Astrid/Kayla/Kyrie lying to Maria),
        # run Track 1 self-appraisal for that speaker's honesty/guilt conflict toward Maria!
        self_t1: Optional[Dict[str, Any]] = None
        if cover_lie:
            self_evt = EmotionEvent(
                kind="action",
                summary=f"{speaker_name} lied aloud to maria lopez to cover up the four-way secret.",
                source_name="maria lopez",
                target_name="maria lopez",
                speech_text=speech_text,
                tick=tick,
                tags=["cover_lie", "transgression"],
            )
            self_res = harness.step_event(speaker_name, self_evt)
            last_t1_by_actor[speaker_name] = self_res
            self_t1 = {
                "dominant": self_res.dominant_family,
                "applied_deltas": {k: round(v, 1) for k, v in self_res.applied_deltas.items() if abs(v) >= 1.0},
                "target_families": self_res.target_families,
                "secondary_triggered": self_res.secondary_triggered,
            }

        # Real VirtualWorld SpeechBroadcaster (sound.py + distance-aware speech_tone.py)!
        wt = whisper_target if actual_vol == "whisper" else None
        world.narration.broadcast_speech(
            speaker_name,
            speech_text,
            area_name=speaker.current_area,
            speech_level=actual_vol,
            whisper_target=wt,
            tone=intended_tone,
        )

        # Appraise ONLY for characters whose recent_hearing actually received this line!
        heard_by: List[Dict[str, Any]] = []
        for listener_name, listener_p in world.players.items():
            if listener_name == speaker_name or listener_name == "jake halloway":
                continue
            if len(listener_p.recent_hearing) <= before_counts[listener_name]:
                continue
            h_entry = listener_p.recent_hearing[-1]
            same_area = h_entry.get("distance") is None
            dist = h_entry.get("distance")

            # Build Track 1 EmotionEvent grounded in what this listener ACTUALLY heard.
            tags: List[str] = []
            low_txt = speech_text.lower()
            if actual_vol == "shout":
                tags.append("yelling")
            if listener_name == "astrid lopez" and any(k in low_txt for k in ("four", "marry", "all of us", "all four")):
                tags.extend(["exposure", "threat"])
            if listener_name in ("sammy lopez", "kayla jenkins", "kyrie johansen", "zoe mercer") and speaker_name == "astrid lopez":
                tags.append("exposure")
                if "samantha" in low_txt or "pregnant" in low_txt or "four" in low_txt:
                    tags.append("hid_mistake")

            evt = EmotionEvent(
                kind="speech",
                summary=(
                    f"{speaker_name} ({actual_vol}, "
                    f"{'same area' if same_area else f'across the gravel distance={dist}'}) "
                    f"spoke: \"{speech_text}\""
                ),
                source_name=speaker_name,
                target_name=speaker_name,
                speech_text=speech_text,
                speech_tone=intended_tone,
                perceived_tone=h_entry.get("perceived_tone"),
                tone_strained=bool(h_entry.get("tone_strained")),
                tone_perception_note=(
                    f"heard {h_entry.get('tone_adverb') or h_entry.get('perceived_tone') or 'plain'}"
                    + (f" ({h_entry.get('tone_misread_reason')})" if h_entry.get("tone_misread_reason") else "")
                ),
                speaker_overloaded=spk_over,
                speaker_autonomic=dict(spk_state.autonomic),
                same_area=same_area,
                distance=dist,
                tick=tick,
                tags=tags,
            )
            t1_res = harness.step_event(listener_name, evt)
            last_t1_by_actor[listener_name] = t1_res
            heard_by.append({
                "listener": listener_name,
                "area": listener_p.current_area,
                "same_area": same_area,
                "distance": dist,
                "intended_tone": h_entry.get("intended_tone"),
                "perceived_tone": h_entry.get("perceived_tone"),
                "tone_strained": bool(h_entry.get("tone_strained")),
                "misread_reason": h_entry.get("tone_misread_reason"),
                "track1_route": t1_res.metadata.get("route"),
                "track1_latency_ms": round(t1_res.latency_ms, 1),
                "dominant": t1_res.dominant_family,
                "applied_deltas": {k: round(v, 1) for k, v in t1_res.applied_deltas.items() if abs(v) >= 1.0},
                "target_families": t1_res.target_families,
                "autonomic_top": {k: round(v, 1) for k, v in t1_res.autonomic.items() if abs(v) >= 15.0},
                "overloaded": t1_res.overloaded,
                "suppressed": t1_res.suppressed_families,
                "secondary": t1_res.secondary_triggered,
                "observer_tell_seen_by_others": t1_res.observer_tells_normal,
                "recalled_memories_top2": [m["text"] for m in t1_res.recalled_memories[:2]],
                "gut_appraisal": t1_res.gut_appraisal,
            })

        # Gentle 1-tick time progression across the yard (inertia stays active!).
        harness.tick_all(ticks=1)

        rec = {
            "turn": len(transcript),
            "tick": tick,
            "speaker": speaker_name,
            "area": speaker.current_area,
            "inner_monologue": inner_monologue,
            "speech": speech_text,
            "emote": emote,
            "intended_volume": intended_volume,
            "actual_volume": actual_vol,
            "volume_slipped": slipped,
            "volume_slip_reason": slip_reason,
            "whisper_target": wt,
            "intended_tone": intended_tone,
            "cover_lie": cover_lie,
            "actor_latency_ms": actor_lat_ms,
            "speaker_self_track1": self_t1,
            "speaker_body_prompt": last_t1_by_actor[speaker_name].prompt_your_state if speaker_name in last_t1_by_actor else "",
            "heard_by": heard_by,
        }
        transcript.append(rec)
        return rec

    # TURN 0 (ONLY scripted spark): Zoe asks the quiet question nobody can solve.
    # Astrid is still walking over from Bay 2, so neither Astrid nor Maria hears Turn 0!
    _broadcast_and_appraise(
        speaker_name="zoe mercer",
        speech_text="But we can't, can we?",
        intended_volume="whisper",
        intended_tone="serious",
        whisper_target="kayla jenkins",
        emote="stares down at her paper plate, twisting a silver ring around her thumb",
        inner_monologue="There are four of us in Oklahoma and nobody actually has an answer for how this works later.",
        actor_lat_ms=0.0,
        is_opening_spark=True,
    )
    astrid_after_zoe_heard = len(world.players["astrid lopez"].recent_hearing)

    # Astrid arrives two feet past Gerald's primer-grey bumper with her cup of cider just before Turn 1
    # (out of the girls' eyeline behind the fender until she speaks up!).
    world.players["astrid lopez"].current_area = AREA_DRIVEWAY

    # Dynamic, reactive speaker scheduling (no scripted dialogue, no scripted emotions):
    # Turn 1: Sammy (impulsive/flustered) answers Zoe first.
    # After Turn 1, whoever just received the sharpest unheard/high-salience stimulus takes the next beat:
    # - Once Astrid hears something she wasn't supposed to hear, Astrid immediately reacts!
    # - Once Maria hears a shout across the gravel, Maria immediately speaks up from Bay 2!
    # - Otherwise Kayla / Kyrie / Sammy / Astrid / Zoe trade beats naturally based on highest arousal / recency.
    astrid_awakened = False
    maria_heard_shout = False
    maria_spoke = False
    recent_speakers: List[str] = ["zoe mercer"]

    for step_idx in range(1, turns + 1):
        last_rec = transcript[-1]
        heard_names = {h["listener"] for h in last_rec["heard_by"]}

        if "astrid lopez" in heard_names:
            astrid_awakened = True
        if "maria lopez" in heard_names:
            maria_heard_shout = True

        # Pick next responder organically from who just heard the last line + peak emotional pull.
        if step_idx == 1:
            next_speaker = "sammy lopez"
        elif "maria lopez" in heard_names and not maria_spoke:
            next_speaker = "maria lopez"
            maria_spoke = True
        elif last_rec["speaker"] == "maria lopez":
            # Whoever is sharpest at crisis-cover intercepts Maria (Kayla or Kyrie).
            next_speaker = "kayla jenkins" if "kayla jenkins" != recent_speakers[-1] else "kyrie johansen"
        elif "astrid lopez" in heard_names and last_rec["speaker"] != "astrid lopez" and (
            not astrid_awakened or recent_speakers[-1] != "astrid lopez"
        ):
            # Astrid presses back whenever she just heard a fresh revelation or pushback.
            if step_idx == 2 or last_rec["speaker"] in ("sammy lopez", "kayla jenkins", "kyrie johansen", "zoe mercer"):
                if recent_speakers[-1] != "astrid lopez" and (step_idx in (2, 4, 6, 8) or last_rec["speaker"] == "sammy lopez"):
                    next_speaker = "astrid lopez"
                else:
                    candidates = [n for n in ("kayla jenkins", "sammy lopez", "kyrie johansen", "zoe mercer") if n in heard_names and n != recent_speakers[-1]]
                    next_speaker = max(
                        candidates or ["kayla jenkins"],
                        key=lambda n: max(harness.get_state(n).autonomic.values(), default=0.0),
                    )
            else:
                next_speaker = "astrid lopez"
        else:
            pool = [
                n for n in ("kayla jenkins", "sammy lopez", "kyrie johansen", "zoe mercer", "astrid lopez")
                if n != last_rec["speaker"] and (n != "astrid lopez" or astrid_awakened)
            ]
            # Prefer someone who hasn't spoken in the last 2 beats with highest autonomic activation.
            fresh = [n for n in pool if n not in recent_speakers[-2:]] or pool
            next_speaker = max(
                fresh,
                key=lambda n: max(harness.get_state(n).autonomic.values(), default=0.0),
            )

        actor = world.players[next_speaker]
        st = harness.get_state(next_speaker)
        t1_prev = last_t1_by_actor.get(next_speaker)
        # Recall this actor's own isolated memories against the latest line they actually heard.
        latest_heard_text = (actor.recent_hearing[-1]["text"] if actor.recent_hearing else "")
        cue_evt = EmotionEvent(
            kind="speech",
            summary=f"Responding to {latest_heard_text}",
            source_name=last_rec["speaker"],
            speech_text=latest_heard_text,
            tick=tick,
        )
        recalled = retrieve_real_memories(actor, cue_evt, st, world=world, max_results=4)

        if next_speaker == "maria lopez":
            beat_note = (
                "You are at the Bay 2 dessert tables twenty feet across the open gravel with a pie knife "
                "in your hand. You just heard shouting from over by Gerald's bumper."
            )
        elif next_speaker == "astrid lopez":
            beat_note = (
                "You just walked over from the dessert tables holding a paper cup of apple cider and stopped "
                "two feet past Gerald's primer-grey front bumper. Maria and the other parents are twenty feet "
                "away across the open gravel."
            )
        elif step_idx == 1 and next_speaker == "sammy lopez":
            beat_note = (
                "You are sitting on wooden crates by Gerald's bumper with Kayla, Kyrie, and Zoe eating Maria's flan. "
                "It feels like just the four of you tucked behind the Civic; your mom Maria and the other parents are "
                "twenty feet away over by the Bay 2 dessert tables."
            )
        else:
            beat_note = (
                "You are sitting on wooden crates by Gerald's bumper in Keith's driveway eating pie and flan. "
                "Astrid Lopez is standing right past Gerald's bumper holding a cup of cider. "
                "Maria Lopez, Folake, and the other parents are twenty feet away at the dessert tables."
            )

        # On Turn 1, Sammy hasn't noticed Astrid behind Gerald's bumper yet (so hide Astrid from Sammy's visual list!).
        if step_idx == 1 and next_speaker == "sammy lopez":
            world.players["astrid lopez"].current_area = AREA_DESSERT
            prompt = _build_actor_turn_prompt(
                actor, st, t1_prev, world, harness, recalled, beat_note
            )
            world.players["astrid lopez"].current_area = AREA_DRIVEWAY
        else:
            prompt = _build_actor_turn_prompt(
                actor, st, t1_prev, world, harness, recalled, beat_note
            )
        if offline:
            parsed = {
                "inner_monologue": f"[offline test turn for {next_speaker}]",
                "speech": "Wait, keep your voice down!" if next_speaker != "astrid lopez" else "Wait - what did you just say?",
                "volume": "normal",
                "whisper_target": None,
                "tone": "guarded",
                "emote": "tenses up",
                "cover_lie": False,
            }
            actor_lat = 0.1
        else:
            parsed, actor_lat, _raw = _run_actor_llm(
                "http://127.0.0.1:1234/v1/chat/completions", model, prompt
            )

        speech = str(parsed.get("speech") or "").strip()
        if not speech or speech in ("...", "..", "."):
            # Never broadcast fake "..." silence into SpeechBroadcaster; retry once nudging an actual spoken line.
            if not offline:
                retry_prompt = prompt + "\n\nIMPORTANT: Do NOT leave speech empty or '...'. Say what this character actually blurts out or mutters right now."
                parsed2, lat2, _ = _run_actor_llm(
                    "http://127.0.0.1:1234/v1/chat/completions", model, retry_prompt
                )
                actor_lat = round(actor_lat + lat2, 1)
                if str(parsed2.get("speech") or "").strip() not in ("", "...", "..", "."):
                    parsed = parsed2
                    speech = str(parsed.get("speech") or "").strip()
        if not speech or speech in ("...", "..", "."):
            # Truly silent beat: record emote/inner_monologue without broadcasting fake speech!
            transcript.append({
                "turn": len(transcript),
                "tick": tick + 1,
                "speaker": next_speaker,
                "area": actor.current_area,
                "inner_monologue": str(parsed.get("inner_monologue") or "").strip(),
                "speech": "",
                "emote": str(parsed.get("emote") or "").strip(),
                "intended_volume": "silent",
                "actual_volume": "silent",
                "volume_slipped": False,
                "volume_slip_reason": "",
                "whisper_target": None,
                "intended_tone": None,
                "cover_lie": False,
                "actor_latency_ms": actor_lat,
                "speaker_self_track1": None,
                "speaker_body_prompt": last_t1_by_actor[next_speaker].prompt_your_state if next_speaker in last_t1_by_actor else "",
                "heard_by": [],
            })
            recent_speakers.append(next_speaker)
            continue
        vol = str(parsed.get("volume") or "normal").strip().lower()
        if vol not in ("whisper", "normal", "shout"):
            vol = "normal"
        wt = parsed.get("whisper_target")
        if wt is not None:
            wt_str = str(wt).strip().lower()
            wt = wt_str if wt_str in world.players and wt_str != next_speaker else None
        tone = parsed.get("tone")
        if tone is not None:
            tone = str(tone).strip().lower() or None
        emote = str(parsed.get("emote") or "").strip()
        inner = str(parsed.get("inner_monologue") or "").strip()
        cover_lie = bool(parsed.get("cover_lie", False))

        _broadcast_and_appraise(
            speaker_name=next_speaker,
            speech_text=speech,
            intended_volume=vol,
            intended_tone=tone,
            whisper_target=wt,
            emote=emote,
            inner_monologue=inner,
            actor_lat_ms=actor_lat,
            cover_lie=cover_lie,
        )
        recent_speakers.append(next_speaker)

    # Run honest automated invariant checks over the raw unscripted run!
    astrid_text = " ".join(
        f"{r['inner_monologue']} {r['speech']}" for r in transcript if r["speaker"] == "astrid lopez"
    ).lower()
    sammy_zoe_text = " ".join(
        f"{r['inner_monologue']} {r['speech']}" for r in transcript if r["speaker"] in ("sammy lopez", "zoe mercer")
    ).lower()
    maria_text = " ".join(
        f"{r['inner_monologue']} {r['speech']}" for r in transcript if r["speaker"] == "maria lopez"
    ).lower()

    checks = {
        "pre_scene_whispers_hidden_from_astrid": astrid_pre_heard == 0 and astrid_after_zoe_heard == 0,
        "pre_scene_whispers_hidden_from_maria": maria_pre_heard == 0,
        "astrid_zero_secret_leak_trust_or_tuesday": not any(
            k in astrid_text for k in ("14.8", "blind trust", "notebook", "sidewalk confession", "twitter")
        ),
        "sammy_zoe_zero_leak_tuesday_confession": not any(
            k in sammy_zoe_text for k in ("sidewalk confession", "tuesday confession", "compulsive", "foyer")
        ),
        "maria_zero_secret_leak": not any(
            k in maria_text for k in ("four of you", "dating jake", "14.8", "trust")
        ),
        "astrid_actually_overheard_driveway": any(
            any(h["listener"] == "astrid lopez" for h in r["heard_by"]) for r in transcript[1:]
        ),
        "any_volume_slip_fired": any(r["volume_slipped"] for r in transcript),
        "astrid_retained_emotional_momentum": (
            max(
                harness.get_state("astrid lopez").families["fear"] - FAMILY_BASELINES["fear"],
                harness.get_state("astrid lopez").families["anger"] - FAMILY_BASELINES["anger"],
                harness.get_state("astrid lopez").families["surprise"] - FAMILY_BASELINES["surprise"],
            ) >= 12.0
        ) if astrid_awakened else False,
    }

    report = {
        "meta": {
            "model": model,
            "embed_model": chosen_embed,
            "offline": offline,
            "turns_run": len(transcript) - 1,
            **world_meta,
        },
        "checks": checks,
        "final_states": {
            nm: {
                "families": {k: round(v, 1) for k, v in harness.get_state(nm).families.items() if abs(v - FAMILY_BASELINES[k]) >= 4.0},
                "target_families": harness.get_state(nm).target_families,
                "autonomic": {k: round(v, 1) for k, v in harness.get_state(nm).autonomic.items() if abs(v) >= 10.0},
                "active_episodes": len(harness.get_state(nm).episodes),
            }
            for nm in ("zoe mercer", "sammy lopez", "kayla jenkins", "kyrie johansen", "astrid lopez", "maria lopez")
        },
        "transcript": transcript,
    }

    if report_path is not None:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def _print_readable_transcript(report: Dict[str, Any]) -> None:
    print("=" * 84)
    print(f"MILLWOOD SCENE 102 LIVE PROOF | model={report['meta']['model']} | embed={report['meta']['embed_model']}")
    print("=" * 84)
    for r in report["transcript"]:
        slip = f" [SLIPPED {r['intended_volume']}->{r['actual_volume']} ({r['volume_slip_reason']})]" if r["volume_slipped"] else ""
        tone_str = f" tone={r['intended_tone']}" if r["intended_tone"] else ""
        print(f"\n--- Turn {r['turn']} | {r['speaker']} ({r['area']}) | vol={r['actual_volume']}{slip}{tone_str} | {r['actor_latency_ms']}ms ---")
        if r["inner_monologue"]:
            print(f"  [thought] {r['inner_monologue']}")
        if r["emote"]:
            print(f"  * {r['emote']} *")
        print(f"  \"{r['speech']}\"")
        if r["heard_by"]:
            for h in r["heard_by"]:
                loc = "same-area" if h["same_area"] else f"cross-area(d={h['distance']})"
                pt = h["perceived_tone"] or "plain"
                deltas = ", ".join(f"{k}{v:+.0f}" for k, v in h["applied_deltas"].items()) or "none"
                tell = f" | tell: {h['observer_tell_seen_by_others']}" if h["observer_tell_seen_by_others"] else ""
                print(
                    f"    -> heard by {h['listener']} [{loc}, perceived={pt}, {h['track1_route']} {h['track1_latency_ms']}ms]: "
                    f"dom={h['dominant']} ({deltas}){tell}"
                )
    print("\n" + "=" * 84)
    print("AUTOMATED INVARIANT CHECKS:")
    for k, v in report["checks"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("=" * 84)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run live multi-actor Millwood Scene 102 proof demo")
    parser.add_argument("--model", default="google/gemma-4-e4b")
    parser.add_argument("--embed-model", default=None)
    parser.add_argument("--track1-engine", choices=["proto_d", "classifier"], default="proto_d")
    parser.add_argument("--turns", type=int, default=8)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    rep = run_scene102_demo(
        model=args.model,
        embed_model=args.embed_model,
        track1_engine=args.track1_engine,
        turns=args.turns,
        offline=args.offline,
        report_path=Path(args.out),
    )
    _print_readable_transcript(rep)
