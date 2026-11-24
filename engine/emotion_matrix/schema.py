"""Shared data structures, vocabularies, and DBT Handout 6 emotion profiles.

Keeps the 13 core Matrix families (10 DBT emotions + 3 VirtualWorld structural
axes: calm, surprise, arousal) cleanly mapped onto VirtualWorld's 36-dimension
affect map and 12 canonical expression portrait keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

#: The 13 core families operated on by the Emotional Matrix.
#: First 10 are the DBT Handout 6 core emotion families; last 3 are VirtualWorld's
#: structural axes (resting equilibrium, prediction error, physiological drive).
DBT_FAMILIES: Tuple[str, ...] = (
    "anger",
    "disgust",
    "envy",
    "fear",
    "happiness",
    "jealousy",
    "love",
    "sadness",
    "shame",
    "guilt",
)

VIWO_STRUCTURAL_FAMILIES: Tuple[str, ...] = (
    "calm",
    "surprise",
    "arousal",
)

FAMILIES: Tuple[str, ...] = DBT_FAMILIES + VIWO_STRUCTURAL_FAMILIES

#: Resting baseline (0-100) per core family. Calm and positive states rest above zero
#: so calm is a state, not an absence.
FAMILY_BASELINES: Dict[str, float] = {
    "anger": 8.0,
    "disgust": 5.0,
    "envy": 5.0,
    "fear": 10.0,
    "happiness": 40.0,
    "jealousy": 8.0,
    "love": 25.0,
    "sadness": 8.0,
    "shame": 8.0,
    "guilt": 8.0,
    "calm": 50.0,
    "surprise": 15.0,
    "arousal": 15.0,
}

#: Core family -> primary dimension key in engine/emotion.py BASELINES (36-dim map).
FAMILY_TO_PRIMARY_DIM: Dict[str, str] = {
    "anger": "angry",
    "disgust": "disgusted",
    "envy": "envious",
    "fear": "afraid",
    "happiness": "happy",
    "jealousy": "jealous",
    "love": "loving",
    "sadness": "sad",
    "shame": "ashamed",
    "guilt": "guilty",
    "calm": "calm",
    "surprise": "surprised",
    "arousal": "aroused",
}

#: All 36 engine/emotion.py dimensions -> 13 Matrix families.
DIM_TO_FAMILY: Dict[str, str] = {
    # anger
    "angry": "anger",
    "irritated": "anger",
    "resentful": "anger",
    # disgust
    "disgusted": "disgust",
    "repulsed": "disgust",
    # envy vs jealousy (explicitly split per DBT Handout 6)
    "envious": "envy",
    "jealous": "jealousy",
    # fear
    "afraid": "fear",
    "anxious": "fear",
    "uneasy": "fear",
    "dread": "fear",
    "spooked": "fear",
    # happiness
    "happy": "happiness",
    "excited": "happiness",
    "elated": "happiness",
    "proud": "happiness",
    # love / bond
    "affectionate": "love",
    "loving": "love",
    "grateful": "love",
    "admiring": "love",
    # sadness
    "sad": "sadness",
    "lonely": "sadness",
    "melancholic": "sadness",
    "nostalgic": "sadness",
    # shame vs guilt (explicitly split per DBT Handout 6)
    "ashamed": "shame",
    "embarrassed": "shame",
    "guilty": "guilt",
    # calm
    "calm": "calm",
    "content": "calm",
    "peaceful": "calm",
    "satisfied": "calm",
    # surprise
    "surprised": "surprise",
    # arousal
    "aroused": "arousal",
    "eager": "arousal",
    "craving": "arousal",
    "curious": "arousal",
}

#: 13 families -> 11 non-neutral canonical expression keys (12 total with "neutral").
#: Preserves existing VirtualWorld sprite-sheet portrait compatibility.
FAMILY_TO_EXPRESSION: Dict[str, str] = {
    "anger": "angry",
    "disgust": "disgusted",
    "envy": "envious",
    "fear": "afraid",
    "happiness": "happy",
    "jealousy": "envious",
    "love": "affectionate",
    "sadness": "sad",
    "shame": "ashamed",
    "guilt": "ashamed",
    "calm": "calm",
    "surprise": "surprised",
    "arousal": "aroused",
}

#: The 8 non-voluntary autonomic body channels covering all 10 DBT Handout 6 sheets.
#: Unsigned channels: 0..100. Signed channels: -100..+100.
AUTONOMIC_CHANNELS: Tuple[str, ...] = (
    "heart_rate",      # 0..100 (resting -> pounding/exploding)
    "breathing",       # 0..100 (steady -> shallow/breathless/choking)
    "muscle_tension",  # 0..100 (relaxed -> clamped jaw/fists -> trembling)
    "vasomotor",       # -100..+100 (pale/cold <-> hot/red/flushed)
    "sweat_chills",    # -100..+100 (chills/hair erect/goosebumps <-> clammy/sweating)
    "gut_throat",      # 0..100 (settled -> knot/butterflies/lump -> nauseous/gagging)
    "motor_tone",      # -100..+100 (slumped/heavy/dizzy/shrunk <-> buoyant/energetic)
    "eyes_tears",      # 0..100 (dry/steady -> stinging/glossy -> spilling tears)
)

SIGNED_AUTONOMIC_CHANNELS = frozenset({"vasomotor", "sweat_chills", "motor_tone"})

#: Settling rate per tick (points toward 0). Adrenaline/heart_rate and vasomotor
#: linger longer than acute startle, modeling real physiological inertia.
AUTONOMIC_INERTIA_DECAY: Dict[str, float] = {
    "heart_rate": 6.0,
    "breathing": 9.0,
    "muscle_tension": 7.0,
    "vasomotor": 6.5,
    "sweat_chills": 8.0,
    "gut_throat": 5.5,
    "motor_tone": 5.0,
    "eyes_tears": 5.0,
}

#: Full psychological + physiological profile per Matrix family, grounded in DBT Handout 6.
EMOTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "anger": {
        "valence": -0.75,
        "arousal": 0.85,
        "decay_per_tick": 1.3,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.85,
            "breathing": 0.45,
            "muscle_tension": 0.95,
            "vasomotor": 0.85,      # hot, flushed red face
            "sweat_chills": 0.25,
            "gut_throat": 0.25,
            "motor_tone": 0.35,     # forward tension / explosive energy
            "eyes_tears": 0.35,     # angry tears at high peak
        },
        "urges": ["confront", "snap", "push_back", "walk_out", "slam"],
        "disposition_tilts": {"social.weight.bully": 1.0},
        "somatic_bands": (
            "Heat hammers behind your ears, your jaw clamps tight, and your hands curl into fists on their own.",
            "Your face feels hot and your shoulders lock rigid, irritation burning close to the surface.",
            "A tight edge settles into your jaw and shoulders.",
        ),
        "urge_phrase": "part of you wants to snap back, slam something, or walk straight out",
        "observable_tells": (
            "face flushed red, jaw clamped hard, fists clenched white-knuckled",
            "brows drawn low, jaw set tight, posture stiff and coiled",
            "shoulders slightly tense, expression clipped",
        ),
        "masked_micro_tell": "keeping their voice level, though their jaw stays locked and color rises along their neck",
        "reasoning_tug": "The heat in your chest makes it feel obvious they did this on purpose and crossed a line.",
        "aftereffects": ["attention_narrowing", "rumination", "future_rehearsal"],
    },
    "disgust": {
        "valence": -0.75,
        "arousal": 0.45,
        "decay_per_tick": 1.4,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.25,
            "breathing": 0.30,
            "muscle_tension": 0.45,
            "vasomotor": -0.35,     # pale / queasy
            "sweat_chills": -0.45,  # skin crawling / unclean chill
            "gut_throat": 0.95,     # nausea, gagging, lump in throat, food aversion
            "motor_tone": -0.35,    # recoil / faintness at extreme peak
            "eyes_tears": 0.10,
        },
        "urges": ["recoil", "push_away", "wash_clean", "avoid_eating", "scorn"],
        "disposition_tilts": {"social.weight.ignore": 0.8},
        "somatic_bands": (
            "Your stomach flips violently, a sour lump rising in your throat as your skin crawls.",
            "Nausea turns in your gut and you feel an immediate urge to step back and wash clean.",
            "Something here leaves a sour, unpleasant turn in your stomach.",
        ),
        "urge_phrase": "every instinct wants to push it away, look elsewhere, or get clean",
        "observable_tells": (
            "pale and visibly gagging, nose and upper lip pulled tight as they recoil",
            "upper lip tightened in distaste, leaning back and looking away",
            "faint wrinkle at the bridge of their nose, keeping distance",
        ),
        "masked_micro_tell": "staying polite, though their upper lip tightens slightly and they keep a stiff arm's distance",
        "reasoning_tug": "The revulsion in your gut makes everything about this feel tainted and wrong.",
        "aftereffects": ["attention_narrowing", "contamination_hypersensitivity", "rumination"],
    },
    "envy": {
        "valence": -0.60,
        "arousal": 0.60,
        "decay_per_tick": 0.7,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.45,
            "breathing": 0.25,
            "muscle_tension": 0.80, # teeth clamping, mouth tight, rigid body
            "vasomotor": 0.55,      # hot flush
            "sweat_chills": 0.10,
            "gut_throat": 0.65,     # sour pain in pit of stomach
            "motor_tone": 0.15,
            "eyes_tears": 0.05,
        },
        "urges": ["acquire", "outdo", "undermine", "criticize", "avoid_envied"],
        "disposition_tilts": {"social.weight.bully": 0.7, "social.weight.tease": 0.5},
        "somatic_bands": (
            "A sour knot twists in the pit of your stomach and your jaw locks as your eyes stick to what they have.",
            "Rigidity pulls across your shoulders and mouth, acutely aware of what they got and you did not.",
            "A small, sharp pinch sits in your gut watching what someone else holds.",
        ),
        "urge_phrase": "you feel a restless pull to take it, outdo them, or cut down what they have",
        "observable_tells": (
            "mouth pressed into a hard tight line, jaw clenched, gaze fixed sharply on what the other holds",
            "posture rigid, smile not reaching their eyes, glances darting back repeatedly",
            "slight tightening around their mouth as they watch",
        ),
        "masked_micro_tell": "playing it off lightly, though their jaw tightens whenever attention stays on the other person",
        "reasoning_tug": "That ache in your gut makes what you already have feel hollow compared to theirs.",
        "aftereffects": ["attention_narrowing", "discounting_own_worth", "comparison_rumination"],
    },
    "fear": {
        "valence": -0.80,
        "arousal": 0.95,
        "decay_per_tick": 1.3,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.95,     # fast pounding heartbeat
            "breathing": 0.90,      # breathlessness, choking sensation
            "muscle_tension": 0.85, # cramping, trembling, frozen rigidity
            "vasomotor": -0.80,     # cold, blood draining, pale
            "sweat_chills": 0.80,   # clammy sweat / chills / hair erect
            "gut_throat": 0.75,     # butterflies, lump in throat, nausea
            "motor_tone": -0.25,    # freeze or coiled flight
            "eyes_tears": 0.30,     # wide darting eyes / whimpering
        },
        "urges": ["flee", "hide", "freeze", "plead", "avoid"],
        "disposition_tilts": {"social.weight.confide": 0.7, "social.weight.ignore": 0.5},
        "somatic_bands": (
            "Your heart hammers against your ribs, your breath catches shallow, your hands feel cold and clammy, and the hairs on your arms stand up.",
            "A tight lump sits in your throat and your pulse runs fast as your eyes check the exits.",
            "A cold prickle of unease coils in your stomach and keeps you braced.",
        ),
        "urge_phrase": "every nerve wants to back away, freeze still, or get out of here",
        "observable_tells": (
            "pale and clammy, chest heaving with shallow breaths, eyes wide and darting, hands visibly trembling",
            "shoulders pulled up tight, gaze flickering toward the exits, breathing quick and shallow",
            "posture slightly guarded, glancing around more than usual",
        ),
        "masked_micro_tell": "trying to hold steady, though their fingers tremble faintly and their eyes flick toward the door",
        "reasoning_tug": "With your pulse pounding like this, it feels certain something bad is about to happen.",
        "aftereffects": ["hypervigilance", "attention_narrowing", "disorientation", "rumination"],
    },
    "happiness": {
        "valence": 0.85,
        "arousal": 0.65,
        "decay_per_tick": 1.2,
        "is_negative": False,
        "autonomic": {
            "heart_rate": 0.30,
            "breathing": 0.10,
            "muscle_tension": 0.0,
            "vasomotor": 0.35,      # warm bright glow/flush
            "sweat_chills": 0.0,
            "gut_throat": 0.0,
            "motor_tone": 0.85,     # energetic, active, bouncy, open/expansive
            "eyes_tears": 0.15,     # happy tears at peak
        },
        "urges": ["share", "smile", "engage", "keep_going", "help"],
        "disposition_tilts": {"social.weight.joke": 0.9, "social.weight.compliment": 0.7},
        "somatic_bands": (
            "Light, restless energy fills your chest and limbs, your face warm and open as laughter sits right behind your ribs.",
            "A steady warmth settles through your chest and your posture loosens with easy energy.",
            "A quiet lightness makes the room feel a little brighter.",
        ),
        "urge_phrase": "you feel drawn to share the moment, stay with it, and be generous",
        "observable_tells": (
            "face bright and glowing, posture open and bouncy, an irrepressible grin breaking across their expression",
            "easy warm smile, shoulders loose and relaxed, lively energy in how they move",
            "slight softening around their eyes and mouth",
        ),
        "masked_micro_tell": "trying to look serious, though the corners of their mouth keep pulling upward",
        "reasoning_tug": "",
        "aftereffects": ["positive_buffer", "prosocial_openness", "positive_recall_bias"],
    },
    "jealousy": {
        "valence": -0.70,
        "arousal": 0.85,
        "decay_per_tick": 0.6,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.85,     # fast heartbeat
            "breathing": 0.75,      # breathlessness, choking sensation
            "muscle_tension": 0.80, # teeth clenching, muscles tensing
            "vasomotor": 0.45,      # stung pride heat
            "sweat_chills": 0.20,
            "gut_throat": 0.70,     # lump in throat, tight gut
            "motor_tone": 0.15,     # hyper-alert watchful posture
            "eyes_tears": 0.20,
        },
        "urges": ["cling", "interrogate", "watch_closely", "control", "push_away_rival"],
        "disposition_tilts": {"social.weight.bully": 0.6, "social.weight.flirt": 0.3},
        "somatic_bands": (
            "Your breath comes tight and fast, a hard lump pressing your throat as your heart races with stung, possessive alarm.",
            "Your jaw tightens and your pulse picks up, hyper-aware of every glance and distance between them.",
            "A wary, tight watchfulness pulls at your chest whenever someone else gets their attention.",
        ),
        "urge_phrase": "a sharp pull wants you to hold on tighter, question them, or push the rival out",
        "observable_tells": (
            "jaw clenched, breathing quick, eyes locked intensely onto every move and glance",
            "stiff and watchful, posture angled defensively between them, expression guarded and mistrustful",
            "wary glances lingering longer than casual",
        ),
        "masked_micro_tell": "acting casual, though their eyes keep snapping back to track every word and gesture",
        "reasoning_tug": "That tightness in your throat makes it feel certain you are being pushed aside or lied to.",
        "aftereffects": ["relationship_hypervigilance", "broad_mistrust", "attention_narrowing"],
    },
    "love": {
        "valence": 0.85,
        "arousal": 0.55,
        "decay_per_tick": 0.45,
        "is_negative": False,
        "autonomic": {
            "heart_rate": 0.45,     # warm fast flutter
            "breathing": 0.15,
            "muscle_tension": 0.0,
            "vasomotor": 0.55,      # warm flush
            "sweat_chills": 0.0,
            "gut_throat": 0.15,     # warm flutter
            "motor_tone": 0.55,     # warm, relaxed, open energy
            "eyes_tears": 0.10,
        },
        "urges": ["draw_close", "touch", "give", "protect", "express_warmth"],
        "disposition_tilts": {"social.weight.compliment": 0.9, "social.weight.flirt": 0.8},
        "somatic_bands": (
            "Warmth floods through your chest and cheeks as your pulse flutters fast, open and drawn irresistibly close.",
            "A steady, trusting warmth softens your shoulders and keeps your attention pulled toward them.",
            "A gentle fondness warms the edge of your thoughts.",
        ),
        "urge_phrase": "you want to step closer, share time, and do something good for them",
        "observable_tells": (
            "warm flush across their cheeks, soft steady eye contact, posture leaning openly toward them",
            "gentle smile, relaxed shoulders, gaze lingering warmly",
            "softened gaze and an easy, receptive posture",
        ),
        "masked_micro_tell": "trying to play it cool, though their cheeks stay warm and their gaze keeps drifting back",
        "reasoning_tug": "The warmth in your chest makes it easy to overlook flaws and assume the best of them.",
        "aftereffects": ["positive_buffer", "positive_side_bias", "daydreaming", "openness"],
    },
    "sadness": {
        "valence": -0.80,
        "arousal": 0.25,
        "decay_per_tick": 0.65,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.15,
            "breathing": 0.50,      # sighing, breathlessness, sobbing
            "muscle_tension": 0.15,
            "vasomotor": -0.25,     # dull/pale
            "sweat_chills": -0.15,
            "gut_throat": 0.70,     # hollow ache in chest/gut, difficulty swallowing
            "motor_tone": -0.85,    # heavy, tired, lethargic, slumped, dizzy
            "eyes_tears": 0.95,     # stinging, unstoppable tears, drooping eyes
        },
        "urges": ["withdraw", "go_quiet", "give_up_effort", "seek_comfort"],
        "disposition_tilts": {"social.weight.confide": 0.8, "social.weight.ignore": 0.6},
        "somatic_bands": (
            "A heavy hollow ache sits in your chest and gut, your limbs feel leaden, swallowing is hard, and hot tears press behind your eyes as if once they start they will not stop.",
            "Your energy drains out of your shoulders and a dull hollow weight settles behind your ribs.",
            "A quiet heaviness tugs at your chest and slows your movements.",
        ),
        "urge_phrase": "you feel pulled to go quiet, withdraw, and stop trying",
        "observable_tells": (
            "shoulders slumped low, eyes glossy and spilling tears, movements slow and deflated",
            "posture sunken, eyes drooping and distant, voice quiet and slow",
            "shoulders dropped slightly, expression muted and low",
        ),
        "masked_micro_tell": "trying to hold their posture up, though their eyes stay glossy and they swallow hard between words",
        "reasoning_tug": "Everything feels heavy enough that remembering good moments feels out of reach.",
        "aftereffects": ["happy_memory_suppression", "rumination", "lethargy", "appetite_drag"],
    },
    "shame": {
        "valence": -0.85,
        "arousal": 0.70,
        "decay_per_tick": 0.6,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.65,
            "breathing": 0.45,
            "muscle_tension": 0.65, # rigid slumped posture
            "vasomotor": 0.90,      # burning hot face/ears
            "sweat_chills": 0.35,
            "gut_throat": 0.85,     # sharp drop/pain in pit of stomach
            "motor_tone": -0.75,    # shrinking down, sinking back
            "eyes_tears": 0.45,     # averted gaze, stinging eyes
        },
        "urges": ["shrink", "hide_face", "withdraw", "avoid_observer", "appease"],
        "disposition_tilts": {"social.weight.ignore": 0.9},
        "somatic_bands": (
            "A sick drop hits the pit of your stomach as heat burns up your face and ears; your shoulders curl inward as if you could shrink out of sight.",
            "Your stomach knots tight and your ears burn hot, making eye contact feel unbearable.",
            "A self-conscious warmth creeps up your neck and makes you want to pull back.",
        ),
        "urge_phrase": "every instinct wants you to shrink down, cover your face, or disappear from view",
        "observable_tells": (
            "face and ears flushed deep red, head bowed, shoulders hunched tight, eyes locked on the floor",
            "gaze darting down and away, posture pulled small and rigid, cheeks flushed",
            "looking away slightly, posture pulled inward",
        ),
        "masked_micro_tell": "trying to stay composed, though heat climbs their ears and they refuse to meet anyone's eyes",
        "reasoning_tug": "The drop in your stomach makes it feel certain everyone sees right through you and wants you gone.",
        "aftereffects": ["self_preoccupation", "problem_solving_impairment", "shutting_down", "defensive_blame"],
    },
    "guilt": {
        "valence": -0.65,
        "arousal": 0.60,
        "decay_per_tick": 0.7,
        "is_negative": True,
        "autonomic": {
            "heart_rate": 0.55,
            "breathing": 0.65,      # suffocating chest tightness
            "muscle_tension": 0.50, # jitteriness, nervous restlessness
            "vasomotor": 0.70,      # hot red face
            "sweat_chills": 0.30,
            "gut_throat": 0.60,     # tight knot in chest/gut
            "motor_tone": -0.25,    # bowed head, restless fidgeting
            "eyes_tears": 0.25,
        },
        "urges": ["repair", "confess", "apologize", "make_amends", "resolve_change"],
        "disposition_tilts": {"social.weight.apologise": 1.0, "social.weight.confide": 0.5},
        "somatic_bands": (
            "Your face burns hot and your chest feels tight and suffocating, jittery nerves pushing you to undo what you caused.",
            "A restless, suffocating tightness sits in your chest and your hands fidget, nagging at what you got wrong.",
            "A nagging tightness sits behind your ribs over what you did or failed to do.",
        ),
        "urge_phrase": "a pressing restless urge pushes you to own up, apologize, and fix the damage",
        "observable_tells": (
            "face flushed hot, head bowed, hands fidgeting restlessly as they glance up in obvious contrition",
            "uneasy fidgeting, chest tight, posture apologetic and hesitant",
            "slightly hunched and restless, glancing back with uneasy concern",
        ),
        "masked_micro_tell": "keeping quiet, though their fingers fidget restlessly and they keep glancing back with a tight expression",
        "reasoning_tug": "That tightness in your chest keeps replaying what you could have done differently.",
        "aftereffects": ["repair_motivation", "rumination", "behavioral_resolution"],
    },
    "calm": {
        "valence": 0.45,
        "arousal": 0.10,
        "decay_per_tick": 1.0,
        "is_negative": False,
        "autonomic": {
            "heart_rate": 0.0,
            "breathing": 0.0,
            "muscle_tension": 0.0,
            "vasomotor": 0.0,
            "sweat_chills": 0.0,
            "gut_throat": 0.0,
            "motor_tone": 0.15,
            "eyes_tears": 0.0,
        },
        "urges": ["steady", "observe", "rest"],
        "disposition_tilts": {"social.weight.chat": 0.4},
        "somatic_bands": (
            "Your breathing runs slow and even, shoulders loose, mind clear and unhurried.",
            "A steady, settled calm rests in your chest.",
            "You feel reasonably composed and even.",
        ),
        "urge_phrase": "you feel steady enough to look closely before acting",
        "observable_tells": (
            "breathing slow and even, posture completely relaxed and unhurried",
            "composed and relaxed",
            "",
        ),
        "masked_micro_tell": "",
        "reasoning_tug": "",
        "aftereffects": ["positive_buffer", "composure_recovery"],
    },
    "surprise": {
        "valence": 0.05,
        "arousal": 0.90,
        "decay_per_tick": 3.2,
        "is_negative": False,
        "autonomic": {
            "heart_rate": 0.70,
            "breathing": 0.60,      # sharp intake of breath
            "muscle_tension": 0.50, # sudden jolt
            "vasomotor": -0.15,
            "sweat_chills": 0.15,
            "gut_throat": 0.25,
            "motor_tone": 0.30,     # instant orientation
            "eyes_tears": 0.0,
        },
        "urges": ["orient", "examine", "pause"],
        "disposition_tilts": {},
        "somatic_bands": (
            "A sharp jolt kicks your pulse upright and catches your breath mid-chest.",
            "Your breath hitches in sudden startle as your attention snaps onto what just changed.",
            "A brief flicker of surprise catches you off guard.",
        ),
        "urge_phrase": "everything pauses for a beat while you try to make sense of what just happened",
        "observable_tells": (
            "jolted rigid, eyes wide, breath visibly caught mid-chest",
            "brows shot up, pausing mid-motion in sudden surprise",
            "brief blink of surprise",
        ),
        "masked_micro_tell": "smoothing their face quickly, though they blinked and paused half a beat too long",
        "reasoning_tug": "",
        "aftereffects": ["orienting_focus"],
    },
    "arousal": {
        "valence": 0.35,
        "arousal": 0.80,
        "decay_per_tick": 1.4,
        "is_negative": False,
        "autonomic": {
            "heart_rate": 0.65,
            "breathing": 0.55,
            "muscle_tension": 0.30,
            "vasomotor": 0.70,      # warm flush
            "sweat_chills": 0.25,
            "gut_throat": 0.20,
            "motor_tone": 0.50,     # eager restless focus
            "eyes_tears": 0.0,
        },
        "urges": ["pursue", "approach", "examine", "seek_closeness"],
        "disposition_tilts": {"social.weight.flirt": 0.8},
        "somatic_bands": (
            "A hot restless pulse runs through your chest and skin, narrowing your focus onto what you want.",
            "Warmth and eager tension pull your attention sharply forward.",
            "A faint restless pull tugs at your curiosity and appetite.",
        ),
        "urge_phrase": "your attention keeps pulling forward toward what you want",
        "observable_tells": (
            "skin flushed warm, breathing noticeably quicker, gaze intently fixed",
            "eager posture leaning forward, slight flush across their cheeks",
            "attentive, leaning in slightly",
        ),
        "masked_micro_tell": "trying to look indifferent, though their breathing quickens slightly and their attention keeps snapping back",
        "reasoning_tug": "",
        "aftereffects": ["desire_narrowing"],
    },
}


@dataclass
class EmotionEvent:
    """One prompting event entering Track 1 (Reactive / Emotional Mind)."""
    kind: str  # "speech", "action", "goal", "threat", "exposure", "memory", "discrepancy", "repair", "check_facts"
    summary: str
    source_name: Optional[str] = None
    target_name: Optional[str] = None  # optional explicit emotional target (defaults to source_name)
    tick: int = 0
    witnesses: List[str] = field(default_factory=list)
    expectations: List[str] = field(default_factory=list)
    speech_text: str = ""
    valence_hint: Optional[str] = None  # optional structured cue for deterministic events
    tags: List[str] = field(default_factory=list)
    exertion: float = 0.0  # 0..1 physical exertion (dash/combat)
    speech_tone: Optional[str] = None  # speaker's optional intended delivery tone
    perceived_tone: Optional[str] = None  # listener's subjective perceived tone
    tone_strained: bool = False
    tone_perception_note: str = ""
    speaker_overloaded: bool = False
    speaker_autonomic: Optional[Dict[str, float]] = None
    same_area: Optional[bool] = None
    distance: Optional[int] = None
    proximity_hops: Optional[int] = None
    proximity_checked: bool = False


@dataclass
class EpisodeRecord:
    """Bounded Worksheet-4 causal trace for Mind Inspector & rumination tracking."""
    id: str
    tick: int
    family: str
    peak_delta: float
    prompting_event: Dict[str, Any]
    appraisal: str
    urges: List[str]
    target_name: Optional[str] = None
    secondary_of: Optional[str] = None
    suppressed: bool = False
    resolved: bool = False
    rumination_ticks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tick": self.tick,
            "family": self.family,
            "peak_delta": round(self.peak_delta, 1),
            "target_name": self.target_name,
            "prompting_event": dict(self.prompting_event),
            "appraisal": self.appraisal,
            "urges": list(self.urges),
            "secondary_of": self.secondary_of,
            "suppressed": self.suppressed,
            "resolved": self.resolved,
            "rumination_ticks": self.rumination_ticks,
        }


@dataclass
class CharacterEmotionState:
    """Live per-character Track 1 state (families + per-target overlays + autonomic + episodes)."""
    families: Dict[str, float] = field(default_factory=lambda: dict(FAMILY_BASELINES))
    target_families: Dict[str, Dict[str, float]] = field(default_factory=dict)
    autonomic: Dict[str, float] = field(
        default_factory=lambda: {ch: 0.0 for ch in AUTONOMIC_CHANNELS}
    )
    episodes: List[EpisodeRecord] = field(default_factory=list)
    reinforced_families: Dict[str, float] = field(default_factory=dict)
    overload_streak: int = 0
    numbness_ticks: int = 0
    human_override_mode: bool = False
    last_cue_signature: str = ""

    def to_36_dim_map(self) -> Dict[str, float]:
        """Project the 13-family Matrix cleanly onto ViWo's 36-dimension affect map."""
        from engine import emotion as viwo_emotion
        out = viwo_emotion.baseline()
        for fam, val in self.families.items():
            primary = FAMILY_TO_PRIMARY_DIM.get(fam)
            if primary and primary in out:
                out[primary] = round(max(0.0, min(100.0, val)), 2)
        return out


@dataclass
class MatrixStepResult:
    """Full output of processing one event through any of the prototype engines."""
    engine_name: str
    latency_ms: float
    before_families: Dict[str, float]
    raw_deltas: Dict[str, float]
    applied_deltas: Dict[str, float]
    after_families: Dict[str, float]
    autonomic: Dict[str, float]
    vulnerability_load: float
    vulnerability_factors: List[str]
    positive_buffer: float
    regulation_capacity: float
    peak_arousal: float
    overloaded: bool
    suppressed_families: List[str]
    secondary_triggered: List[str]
    dominant_family: str
    portrait_expression: str
    valence: float
    arousal: float
    gut_appraisal: str
    recalled_memories: List[Dict[str, Any]]
    prompt_your_state: str
    observer_tells_normal: str
    observer_tells_dim: str
    observer_tells_insight: str
    skill_penalties: Dict[str, int]
    disposition_tilts: Dict[str, float]
    episodes: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    target_families: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_name": self.engine_name,
            "latency_ms": round(self.latency_ms, 2),
            "before_families": {k: round(v, 1) for k, v in self.before_families.items()},
            "raw_deltas": {k: round(v, 1) for k, v in self.raw_deltas.items() if abs(v) >= 0.5},
            "applied_deltas": {k: round(v, 1) for k, v in self.applied_deltas.items() if abs(v) >= 0.5},
            "after_families": {k: round(v, 1) for k, v in self.after_families.items()},
            "target_families": {
                tgt: {k: round(v, 1) for k, v in fams.items()}
                for tgt, fams in self.target_families.items()
            },
            "autonomic": {k: round(v, 1) for k, v in self.autonomic.items()},
            "vulnerability_load": round(self.vulnerability_load, 2),
            "vulnerability_factors": list(self.vulnerability_factors),
            "positive_buffer": round(self.positive_buffer, 2),
            "regulation_capacity": round(self.regulation_capacity, 1),
            "peak_arousal": round(self.peak_arousal, 1),
            "overloaded": self.overloaded,
            "suppressed_families": list(self.suppressed_families),
            "secondary_triggered": list(self.secondary_triggered),
            "dominant_family": self.dominant_family,
            "portrait_expression": self.portrait_expression,
            "valence": round(self.valence, 2),
            "arousal": round(self.arousal, 2),
            "gut_appraisal": self.gut_appraisal,
            "recalled_memories": list(self.recalled_memories),
            "prompt_your_state": self.prompt_your_state,
            "observer_tells_normal": self.observer_tells_normal,
            "observer_tells_dim": self.observer_tells_dim,
            "observer_tells_insight": self.observer_tells_insight,
            "skill_penalties": dict(self.skill_penalties),
            "disposition_tilts": {k: round(v, 2) for k, v in self.disposition_tilts.items()},
            "episodes": list(self.episodes),
            "metadata": dict(self.metadata),
        }


class EmotionPrototype(Protocol):
    """Unified interface implemented by Prototypes A, B, and C."""
    name: str

    def process_event(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        world: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]] = None,
    ) -> MatrixStepResult:
        ...

    def tick(
        self,
        state: CharacterEmotionState,
        player: Any,
        world: Any,
        ticks: int = 1,
    ) -> Dict[str, Any]:
        ...
