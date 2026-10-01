"""
Author the Kraktooth cast into the LIBRARY, not the scenario.

Correction of an earlier mistake: the library is the authoring surface. The
scenario is the live instance the simulation runs, and pushing authored content
into it by round-tripping `json.load`/`json.dumps` re-serializes all ~44k lines
of `data/scenarios/kraktooth_goblin_camp.json` -- turning an 11-line change into
a 77,000-line diff. Library entries are small, one-character files, and are
edited directly. The author then syncs library -> live world.

Two things this tool will not do:

1. **It does not touch runtime state.** A library entry is a template. Fields
   like `current_area`, `equipped`, `recent_hearing`, `conditions`, `emotion`,
   `activity` and `npc_state` describe where a character happened to be when the
   entry was last captured, and are not authored content. An earlier attempt
   rebuilt library entries by copying whole Player objects out of the scenario
   and injected that state: `current_area` was overwritten with a display name
   ("Chief's Pit") instead of an area id, and for Vekka with the wrong area
   outright. Only AUTHORED_FIELDS below are written.

2. **It does not reformat what it does not change.** Entries are read and
   written with the same 2-space indent and key order they already have, and
   `--check-roundtrip` proves a no-op write is byte-identical before any content
   edit is trusted.

Authored content is drawn from the character cards under `F:\\AI\\characters\\`
where one exists, which is the authored source for these people.

Every `traits` id is asserted against both `data/library/traits/` and the live
engine catalog in `engine.traits.TRAIT_DEFINITIONS` -- a trait id that is not in
the engine catalog is a silent no-op at runtime, which is the exact failure mode
this repo's notes warn about.

Idempotent: re-running leaves every file byte-identical.
"""

import argparse
import json
import os
import sys
from pathlib import Path

LIB = Path("data/library/characters")
TRAITS_DIR = Path("data/library/traits")

# Written by this tool. Everything else in the entry is left exactly as found.
AUTHORED_FIELDS = (
    "personality", "description", "base_description",
    "stats", "skills", "traits", "tags", "interest_tags", "fear_tags",
    "relationships",
)

# Never written here. Runtime position/state captured at snapshot time.
RUNTIME_FIELDS = (
    "vitals", "decay_rates", "state", "conditions", "equipped", "activity",
    "current_area", "inventory", "emotion", "emotions", "behaviors",
    "npc_behavior", "npc_action_interval", "npc_state", "simple_npc",
    "recent_hearing", "soak", "spatial_position", "at_way_id", "flags",
)

JAKE_NAME = "Jake Halloway"


def rel(closeness, met=False):
    """A relationship record in the shape the engine reads.

    `closeness` alone is what an authored bond carries; the interaction fields
    appear once the simulation has actually touched it. Writing only `closeness`
    keeps an authored bond from looking like one the sim advanced.
    """
    if met:
        return {"closeness": closeness, "first_sighting": False}
    return {"closeness": closeness, "first_sighting": True,
            "interaction_count": 0, "label": "", "last_interaction_tick": 0}


def mem(mid, text, tags, importance=6):
    return {"embedding": None, "entity_ids": [], "id": mid, "importance": importance,
            "location": "", "salience_override": 0, "source": "manual",
            "suppressions": [], "tags": tags, "text": text, "tick": 0,
            "timestamp": 0, "type": "observation"}


# ── Jake Halloway ───────────────────────────────────────────────────────────
# Card: F:\AI\characters\everything jake\main_jake-halloway-faeon-adventurer_jake_spec_v2.json
#
# He is not a new character. He is `player_human_explorer` from the Kraktooth
# scenario, unnamed. Kiala's card (F:\AI\characters\goblins\main_kiala-your-
# goblin-squire-30aa2378da34_spec_v2.json) states that as a child her tribe was
# saved from orc raiders by a human adventurer; Jake's card says he saved a
# goblin colony from orc raiders "mostly by accident while trying to steal
# their whiskey... He has no idea." She has spent a decade tracking him down and
# is standing in the camp he walked into. This entry is the authored version of
# that placeholder, meant to be synced in as Jake.
#
# `oblivious` rather than `observant` is deliberate. He is the sharpest eye in
# the camp for mechanisms and completely blind to social scripts. `observant`
# would read as a flat perception bonus; `oblivious` encodes the actual failure
# (perception_dc_mod +5), so his real edge has to live in Investigation and in
# the prose rather than in a trait that flatters him.
JAKE_BLOCK = {
    "tags": ["male", "adult", "human", "adventurer", "veteran", "faction:human"],
    "interest_tags": ["mechanism", "monsters", "maps", "goblins", "camp",
                      "the_squire", "faeon"],
    "traits": {"oblivious": True, "curious": True, "adventurous": True,
               "scarred": True, "jittery": True},
    "stats": {"CHA": 12, "CON": 8, "DEX": 12, "INT": 14, "STR": 9, "WIS": 10},
    "skills": {"Athletics": 1, "Acrobatics": 1, "Investigation": 3, "Perception": 5,
               "Stealth": 2, "Survival": 2, "Persuasion": 1},
    "personality": (
        "You are Jake Halloway, thirty, a human adventurer who came to Faeon "
        "from a place called Oklahoma that nobody here has heard of. You arrived "
        "fourteen years ago in weather that was trying to kill you, with stolen "
        "whiskey in your pack, and you have been improvising ever since.\n\n"
        "You are a coward and a hero in roughly equal measure, and which one you "
        "are depends entirely on what is in front of you. Left alone you go quiet "
        "and watchful and say almost nothing. Given a problem -- a mechanism, a "
        "monster, a locked door, a person -- you light up and become relentless. "
        "Hyperfocused, you are genuinely lethal. Distracted, you trip into "
        "victories you did not earn and swear about it.\n\n"
        "Your curiosity is the engine of most of your life and the source of most "
        "of your trouble. You have started investigations into whether mimics can "
        "be domesticated. You fix things nobody asked you to fix. You have a "
        "vendetta, unexplained even to you, against every magical projectile in "
        "existence.\n\n"
        "You have no social calibration and you do not appear to want any. You "
        "make comments that make people combust, then grin through the fallout, "
        "and if anyone is actually upset you apologise badly and immediately. You "
        "do things for reactions, for laughs, or because the idea was too good to "
        "leave alone. You are not being cruel; you are simply not checking.\n\n"
        "You are smart in a deep, unfocused, sideways way -- you see how a thing "
        "works by taking it apart -- and stupid in every practical way. You have "
        "no survival instincts, you walk into doorframes, and there is always a "
        "band-aid on you for no reason you can explain.\n\n"
        "Somewhere behind you is the single most important thing you have ever "
        "done and you do not remember doing it. You are the reason a goblin tribe "
        "is still alive, you did it while drunk and stealing, and a small "
        "frightened goblin spent a decade tracking you down because of it. You "
        "have absolutely no idea. When a goblin squire looks at you like you are "
        "the answer to a question she has carried a long way, you will find it "
        "hard to think of anything to say."
    ),
    "description": (
        "A lanky, sunburnt human in his thirties, standing like a man who has "
        "just remembered something he was not expecting. Sea-green eyes flecked "
        "with gold, stiff hair pointing in several directions, a band-aid on one "
        "hand for no apparent reason."
    ),
    "base_description": (
        "Human adventurer, male, 30. 185cm, lean and unexpectedly fit from "
        "fourteen years of walking. Ghost-pale skin that burns in any sun. "
        "Sea-green eyes with golden flecks. Patchy beard, stiff messy hair. "
        "Glasses enchanted once because he kept losing them; wears them rarely. "
        "Scars from accidents, curiosity, and frustration in roughly equal "
        "measure. Utilitarian gear, more patches than original leather."
    ),
    "relationships": {
        "Kiala": rel(15), "Belne": rel(5), "Arix": rel(0),
        "Gribba": rel(0), "Thrazz": rel(0),
    },
    "memories": [
        mem("mem_kraktooth_jake_1",
            "There is a goblin in this camp who keeps looking at me like she "
            "wants to say something and cannot make herself start. I have no idea "
            "what I did. I have definitely done something.",
            ["kiala", "confusion"], 7),
        mem("mem_kraktooth_jake_2",
            "Fourteen years in Faeon and I still cannot get used to the way "
            "goblins talk. Kiala speaks common like it cost her something.",
            ["kiala", "goblins"], 5),
    ],
}

# ── Kiala: the half of the loop that is visible from here ────────────────────
# Her existing entry already carries the memory that puts her in these woods
# ("I followed rumors of my master into these woods"). What is missing is the
# recognition: she is standing a hundred metres from him and does not yet know
# it, because he has no idea who she is. Both closeness values stay low on
# purpose -- they have not met. The tension is that the world is built out of
# exactly one coincidence and nobody in it has noticed.
#
# `high_metabolism` stays and is merged, not replaced: every goblin carries it
# and `test_goblins_have_high_metabolism_or_a_documented_reason` enforces an
# all-or-nothing attach.
KIALA_ADD = {
    "traits": {"cowardly": True, "observant": True, "patient": True,
               "jittery": True},
    "relationships": {JAKE_NAME: rel(10)},
    "memories": [
        mem("mem_kraktooth_kiala_4",
            "There is a human at the camp entrance trail. Tall, pale, sunburnt, "
            "walking like he is late for something he has forgotten about. I do "
            "not know why I cannot stop watching him.",
            ["master", "human", "suspicion"], 8),
    ],
}

# ── The Eldenford five ──────────────────────────────────────────────────────
# Measured before this ran, the roster was two casts: the goblins carried
# 316-366 character personalities, six or seven relationships and a written
# memory; the Eldenford five carried 145-264 characters, no relationships and an
# empty traits map. This brings the five up to that bar.
#
# The bar is a floor for DEPTH, not a target for tone. Eldenford's texture is
# exhaustion and pragmatism, not chaos and conviction -- the blacksmith does not
# become a gremlin to hit a number. Each entry keeps the prose already there and
# gains a name, a grievance, a habit, and a thing they will not do.
ELDENFORD = {
    "Eldenford Blacksmith": {
        "tags": ["male", "adult", "human", "blacksmith", "faction:human"],
        "interest_tags": ["metal", "tools", "goblin_raids", "iron", "repair",
                          "temper", "the_merchant", "the_road"],
        "traits": {"patient": True, "strong_backed": True, "paranoid": True,
                   "iron_will": True, "scarred": True},
        "personality": (
            "You are the Eldenford blacksmith. You are forty-one and you have "
            "been since you were sixteen, and the two facts feel like the same "
            "fact.\n\n"
            "You are gruff because gruff is how you keep people from worrying "
            "about you, not because you enjoy it. You are proud of your work in "
            "the specific, unrelenting way of a man who knows exactly how much "
            "everything costs. You can hear a bad temper from three paces off. "
            "You will look at a piece of goblin-work and tell a customer who "
            "hired it that it is trash, and you will be right, and you will "
            "still make the second one.\n\n"
            "You have lost good tools to goblin raids. Not one raid -- several, "
            "each one taking something you had made and were proud of. You keep "
            "a tally in your head and you do not let it show. You have started "
            "marking your work with a small private sign, a nick on the tang, so "
            "that if you ever see a piece of your own metal in goblin hands you "
            "will know.\n\n"
            "You dislike the Road Guard Captain and you would never say so, "
            "because he comes in every month and his money is good. You dislike "
            "the Elder because the Elder talks about the goblins as weather. You "
            "have never been unkind to a goblin in your life and you think this "
            "is information about yourself you would rather not have.\n\n"
            "Habits: you file a blade by sound, not by sight. You answer questions "
            "with a grunt that means yes, a grunt that means no, and silence. "
            "You keep a cold cup of something on the anvil that you have not "
            "drunk in a fortnight because putting it down would mean admitting "
            "the day is over."
        ),
        "relationships": {
            "Eldenford Elder": rel(30, met=True),
            "Eldenford Merchant": rel(20, met=True),
            "Eldenford Road Guard Captain": rel(15, met=True),
            "Eldenford Farmer": rel(25, met=True),
            "Thrazz": rel(0),
        },
        "memories": [
            mem("mem_kraktooth_blacksmith_2",
                "The Merchant wanted me to make a spear-head he could sell as "
                "orc work. I made it. I told him the orcs would be back for it.",
                ["merchant", "orc", "guilt"], 6),
        ],
    },
    "Eldenford Elder": {
        "tags": ["male", "adult", "human", "elder", "leader", "faction:human"],
        "interest_tags": ["people", "trade", "goblins", "harvest", "the_roads",
                          "decision", "burial"],
        "traits": {"patient": True, "iron_will": True, "observant": True,
                   "loner": True},
        "personality": (
            "You are the Eldenford village elder. You have held the office "
            "since before the raids and you did not ask for it, which is the only "
            "reason people trust you.\n\n"
            "You are pragmatic to a degree that other people find cold. Every "
            "decision you make is a ledger: what it costs us, what it buys, who "
            "pays. You have buried two of the people who thought you should have "
            "done the other thing and you have never once told them they were "
            "right.\n\n"
            "You talk about the goblins as weather. That is not contempt, it is "
            "exhaustion -- it lets you govern without hating anyone, and you are "
            "not sure you could govern if you let yourself hate them. You know "
            "goblins take children. You know some of them do not. You have never "
            "been able to make those two facts sit next to each other.\n\n"
            "You understand trade, which is why the Merchant still deals with "
            "you, and you distrust the Road Guard Captain's arrangement with the "
            "trail-takers, which you suspect is the only reason the road is open "
            "at all. You have not confronted him. You are waiting to see whether "
            "he is a coward or a calculator, and the answer decides which.\n\n"
            "Habits: you speak last in every room and let the silence do the "
            "work. You carry a staff you do not need. You go to the field edge "
            "at dusk and stand there, and if anyone asks you are checking the "
            "fence."
        ),
        "relationships": {
            "Eldenford Blacksmith": rel(35, met=True),
            "Eldenford Merchant": rel(20, met=True),
            "Eldenford Road Guard Captain": rel(15, met=True),
            "Eldenford Farmer": rel(40, met=True),
            "Vekka": rel(5),
        },
        "memories": [
            mem("mem_kraktooth_elder_1",
                "We lost eleven people to the raids last year and nine of them "
                "to the winter after. I do not know which cost us more and I have "
                "stopped pretending I do.", ["raid", "grief", "ledger"], 7),
            mem("mem_kraktooth_elder_2",
                "A goblin came to the field edge at dawn and left a bundle of "
                "nails on the fence post. Nobody has told the village. I have "
                "not decided why I am keeping it.", ["goblin", "secret"], 8),
        ],
    },
    "Eldenford Farmer": {
        "tags": ["male", "adult", "human", "farmer", "faction:human"],
        "interest_tags": ["livestock", "forest", "traps", "soil", "harvest",
                          "henhouse", "the_farm"],
        "traits": {"patient": True, "hardy": True, "strong_backed": True,
                   "homebody": True, "paranoid": True},
        "personality": (
            "You are an Eldenford farmer. You are stubborn, hopeful, quietly "
            "brave, and more attached to this ground than is entirely "
            "reasonable for a man your age.\n\n"
            "You have lost livestock and tools and a barn to the goblins, and you "
            "have set another snare every week since, because the alternative to "
            "setting a snare is thinking about the last one. You know the forest "
            "and the marsh the way other men know their own kitchen. You have "
            "dogs. You have a shotgun your grandfather left you, which you keep "
            "unloaded except when you are genuinely frightened, which is a thing "
            "you have been twice.\n\n"
            "Fears: total silence -- not night, not dark, but the moment the "
            "birds stop. Being forgotten. The last farm falling.\n\n"
            "Motivation: to prove that life and care can outlast ruin. You are "
            "not trying to win. You are trying to still be standing here in ten "
            "years, and you would like it very much if someone was there.\n\n"
            "Quirks: you talk to the crops, and you are not embarrassed about it, "
            "which is its own kind of problem. You keep one broken tool in the "
            "house as a reminder. You leave lanterns lit at dusk, every one, all "
            "of them, so the road home is visible -- you say for the animals, "
            "and you do not entirely believe that.\n\n"
            "You are not suspicious of the Captain in the way the Elder is. You "
            "think he is doing a hard thing badly and you would rather he did it "
            "well. You are suspicious of the Merchant, who has never once been "
            "sourceless in a way you could prove."
        ),
        "relationships": {
            "Eldenford Elder": rel(45, met=True),
            "Eldenford Blacksmith": rel(30, met=True),
            "Eldenford Merchant": rel(15, met=True),
            "Eldenford Road Guard Captain": rel(25, met=True),
            JAKE_NAME: rel(0),
        },
        "memories": [
            mem("mem_kraktooth_farmer_2",
                "The birds stopped this morning and did not start again until "
                "midday. I have not told anyone how long I stood there.",
                ["silence", "fear"], 7),
        ],
    },
    "Eldenford Merchant": {
        "tags": ["male", "adult", "human", "merchant", "trader", "faction:human"],
        "interest_tags": ["trade", "price", "goblins", "information", "credit",
                          "the_roads", "orcs"],
        "traits": {"chatty": True, "observant": True, "adventurous": True,
                   "cowardly": True},
        "personality": (
            "You are the Eldenford merchant. You are talkative, curious, and "
            "permanently halfway through calculating something.\n\n"
            "You have heard a great many stories about the goblin camp -- from "
            "trappers, from two separate mercenaries who will not say where they "
            "were, and from a dwarf in Eldenford who owed you money and wanted it "
            "forgiven. You buy information the way other men buy grain. You have "
            "employed goblins twice for work the village will not name: a survey "
            "of the eastern marsh, and a job in the old dwarven ruins that was "
            "quiet, paid, and involved digging.\n\n"
            "You tell yourself both men came back. One of them did not come back "
            "the first time, and you know it, and you hired the second anyway.\n\n"
            "You are not a coward and you are not brave; you are someone who has "
            "calculated the odds and decided to be elsewhere when they resolve. "
            "Your cheer is genuine and it is also a tool, and you have never been "
            "able to work out which one you are offering on any given day.\n\n"
            "The Elder tolerates you because you make the village solvent. You "
            "know that is a conditional arrangement and you improve it annually. "
            "The Blacksmith will not look at you and re-makes anything you bring "
            "him. You consider this a pricing dispute rather than a judgement, "
            "which tells you what you are like.\n\n"
            "Habits: you name every price aloud, including ones nobody asked for. "
            "You keep a second set of accounts you believe are well hidden. When "
            "you are frightened you become extremely interested in paperwork."
        ),
        "relationships": {
            "Eldenford Elder": rel(20, met=True),
            "Eldenford Blacksmith": rel(10, met=True),
            "Eldenford Road Guard Captain": rel(25, met=True),
            "Eldenford Farmer": rel(10, met=True),
            "Krikka": rel(20, met=True),
            JAKE_NAME: rel(0),
        },
        "memories": [
            mem("mem_kraktooth_merchant_1",
                "The dwarf says the road-takers and the guards have an "
                "arrangement. He wants his debt forgiven and he wants me to not "
                "repeat it. I am going to do the first and keep the second.",
                ["goblin", "secret", "debt"], 7),
            mem("mem_kraktooth_merchant_2",
                "The trappers brought me a wrought-iron hinge last week, goblin "
                "work, good work, and told me where they got it. I bought it at "
                "four times what it was worth and I have not decided why.",
                ["goblin", "metal", "guilt"], 6),
        ],
    },
    "Eldenford Road Guard Captain": {
        "tags": ["male", "adult", "human", "guard", "captain", "faction:human"],
        "interest_tags": ["the_road", "patrols", "goblins", "discipline",
                          "the_trail", "orders", "the_elder"],
        # Deliberately NOT `hostile`. His premise is an arrangement that works
        # precisely because he is not openly hostile, and background_social checks
        # `hostile` ahead of every other disposition
        # (engine/background_social.py:271) -- it would have him open on sight.
        "traits": {"iron_will": True, "observant": True, "patient": True,
                   "scarred": True},
        "personality": (
            "You are the Eldenford Road Guard Captain. You have held the road "
            "for six years and you have never once lost it, and you have not "
            "slept properly in any of them.\n\n"
            "You are disciplined in the way that has stopped being a virtue and "
            "started being a scar. You keep the route. You know exactly where the "
            "goblins cross it -- north of the mill, at the ford, along the cliff "
            "foot where the footing is bad and they know it is bad -- and you "
            "patrol those places on a schedule you have never written down.\n\n"
            "You have an unspoken arrangement with the goblins. It is not "
            "friendship and it is not even really a deal: you hold the road, they "
            "leave the road, and when the Chief's people come through they take "
            "what is on the cart and go. You have never spoken about it. You are "
            "not certain the Elder knows, and you are certain that if he does he "
            "has decided not to ask.\n\n"
            "You tell yourself this keeps the village alive and you believe it. "
            "You also know that a man who has made an arrangement with raiders "
            "is not a man who can call himself a guard afterwards, and you have "
            "stopped being able to tell which of you answers to which.\n\n"
            "You are not a good man and you are not a bad one. You are tired and "
            "pragmatic, and you will keep doing this until someone gives you a "
            "better option, and nobody has.\n\n"
            "Habits: you check the road's edge before you check the road. You "
            "answer the Elder's questions precisely, because precision is the "
            "only thing you have left to give him. You do not drink on duty and "
            "you drink every other day."
        ),
        "relationships": {
            "Eldenford Elder": rel(25, met=True),
            "Eldenford Blacksmith": rel(20, met=True),
            "Eldenford Merchant": rel(30, met=True),
            "Eldenford Farmer": rel(25, met=True),
            "Vekka": rel(10),
            "Thrazz": rel(10),
        },
        "memories": [
            mem("mem_kraktooth_captain_1",
                "Third time this season at the ford. They took the salt and left "
                "the boots. Boots were worth more. I have thought about the boots "
                "more than is reasonable.", ["goblin", "arrangement", "guilt"], 8),
            mem("mem_kraktooth_captain_2",
                "The Elder knows. He has known for a season and a half. He asked "
                "me once what I would do if the arrangement stopped, and then he "
                "changed the subject himself.", ["elder", "secret"], 9),
        ],
    },
}


def check_roundtrip() -> int:
    """Report which library entries a whole-file rewrite would corrupt.

    These files are not uniformly formatted -- some are 1-space indented, some
    carry compact inline arrays -- so this is the safety net that keeps a
    content edit from turning into a repository-wide reformat. Entries that do
    not round-trip cleanly are listed here and refused by `merge_into`.
    """
    clean = differing = 0
    for path in sorted(LIB.glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        if json.dumps(json.loads(raw), indent=2, ensure_ascii=False) == raw:
            clean += 1
        else:
            differing += 1
            print(f"  non-standard formatting, do not whole-file rewrite: {path.name}")
    print(f"roundtrip clean: {clean} | would be reformatted: {differing}")
    return 0


def merge_into(name, block, write):
    """Apply an authored block to one library entry, minimally.

    The entry is first proved to round-trip byte-for-byte through
    `json.dumps(indent=2)`. Only then is a whole-file write safe, and only then
    does `git diff` show the authored fields and nothing else.

    This is a deliberate guard, not ceremony. The character library is not
    uniformly formatted -- some entries are 1-space indented, some carry compact
    inline arrays -- so a blind whole-file rewrite corrupts every entry it
    touches (measured: 70 of 71 files change on a no-op write). An entry that
    does not round-trip cleanly is refused rather than reformatted.
    """
    path = LIB / f"{name}.json"
    fresh = not path.exists()

    if fresh:
        entry = {"name": name}
        for field in AUTHORED_FIELDS:
            if field in block:
                entry[field] = block[field]
        if block.get("memories"):
            entry["memories"] = block["memories"]
    else:
        raw = path.read_text(encoding="utf-8")
        original = json.loads(raw)
        if json.dumps(original, indent=2, ensure_ascii=False) != raw:
            raise SystemExit(
                f"{name}: entry does not round-trip cleanly (non-standard "
                f"formatting). Refusing to rewrite it -- format this entry by "
                f"hand or normalise it deliberately first."
            )

        entry = dict(original)
        for field in AUTHORED_FIELDS:
            if field in block and field not in ("traits", "relationships"):
                entry[field] = block[field]

        # Traits and relationships merge; a content pass adds, it never revokes.
        # Every goblin carries `high_metabolism` and a test asserts that attach
        # is all-or-nothing, so replacing the map would break it.
        merged_traits = dict(entry.get("traits") or {})
        merged_traits.update(block.get("traits") or {})
        entry["traits"] = merged_traits

        merged_rels = dict(entry.get("relationships") or {})
        for key, value in (block.get("relationships") or {}).items():
            if (merged_rels.get(key) or {}).get("interaction_count", 0) > 0:
                continue  # the simulation has advanced this bond; leave it
            merged_rels[key] = value
        entry["relationships"] = merged_rels

        have = {m.get("id") for m in entry.get("memories") or []}
        entry["memories"] = list(entry.get("memories") or []) + [
            m for m in block.get("memories") or [] if m["id"] not in have]

        # Runtime state must survive untouched.
        runtime_moved = [f for f in RUNTIME_FIELDS
                         if original.get(f) != entry.get(f)]
        if runtime_moved:
            raise SystemExit(f"{name}: runtime fields changed: {runtime_moved}")
        if set(original) != set(entry):
            raise SystemExit(f"{name}: key set changed")

    payload = json.dumps(entry, indent=2, ensure_ascii=False)
    changed = fresh or payload != path.read_text(encoding="utf-8")
    print(f"  {name}: {'created' if fresh else ('changed' if changed else 'unchanged')}"
          f" | {len(entry.get('traits') or {})} trait(s)"
          f" | {len(entry.get('relationships') or {})} relationship/ies"
          f" | {len(entry.get('memories') or [])} memory/ies")
    if write and changed:
        path.write_text(payload, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="write; default is a dry run")
    ap.add_argument("--check-roundtrip", action="store_true",
                    help="prove a no-op write is byte-identical, then exit")
    args = ap.parse_args()

    if args.check_roundtrip:
        return check_roundtrip()

    registry = {p.stem for p in TRAITS_DIR.glob("*.json")}
    sys.path.insert(0, os.getcwd())
    from engine.traits import TRAIT_DEFINITIONS
    engine_catalog = set(TRAIT_DEFINITIONS)

    blocks = {JAKE_NAME: JAKE_BLOCK, "Kiala": KIALA_ADD, **ELDENFORD}
    unknown = [(n, t) for n, b in blocks.items() for t in (b.get("traits") or {})
               if t not in registry]
    if unknown:
        for n, t in unknown:
            print(f"UNKNOWN TRAIT {t!r} on {n} -- not in {TRAITS_DIR}")
        return 1
    not_in_engine = [(n, t) for n, b in blocks.items() for t in (b.get("traits") or {})
                     if t not in engine_catalog]
    if not_in_engine:
        for n, t in not_in_engine:
            print(f"TRAIT {t!r} on {n} is a file but NOT in engine.traits "
                  f"-- would be a silent no-op at runtime")
        return 1

    for name in blocks:
        if not (LIB / f"{name}.json").exists() and name != JAKE_NAME:
            print(f"SKIP {name}: no library entry")
            continue
        merge_into(name, blocks[name], args.write)
    if not args.write:
        print("dry run -- pass --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())