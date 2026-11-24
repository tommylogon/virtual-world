"""Speech delivery tone vocabulary and subjective listener-side perception.

Unlike physical speech volume (whisper/say/sing/shout/scream), delivery tone
is subjective perception rather than telepathy:
  - The speaker declares an optional ``intended_tone`` (voluntary delivery).
  - Each listener perceives a ``perceived_tone`` filtered through:
      1. Speaker involuntary body strain (an overloaded/shaking speaker trying
         to sound warm or casual leaks through as ``strained``).
      2. Listener prior moodiness and closeness (``teasing`` from a stranger or
         heard while deeply ashamed/angry mislands as ``mocking``).
      3. Listener Insight / familiarity (a low-Insight stranger can miss subtle
         ``sarcastic`` delivery and take polite words at face value).

Single source of truth shared by engine/speech.py, routes/action_handlers.py,
and prototypes/emotions/.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

#: Canonical optional speaker delivery tones (never emotion names; omit when neutral).
SPEECH_TONES: Tuple[str, ...] = (
    "warm",
    "teasing",
    "sarcastic",
    "cold",
    "hostile",
    "serious",
    "apologetic",
    "guarded",
)

#: Perceived delivery states (includes subjective listener-side reinterpretations).
PERCEIVED_TONE_STATES: Tuple[str, ...] = SPEECH_TONES + ("mocking", "strained")

#: Common natural-language synonyms normalized onto the 8 canonical tones.
TONE_ALIASES: Dict[str, str] = {
    "warm": "warm",
    "warmly": "warm",
    "gentle": "warm",
    "gently": "warm",
    "kind": "warm",
    "kindly": "warm",
    "soft": "warm",
    "softly": "warm",
    "affectionate": "warm",
    "reassuring": "warm",
    "friendly": "warm",
    "teasing": "teasing",
    "teasingly": "teasing",
    "playful": "teasing",
    "playfully": "teasing",
    "joking": "teasing",
    "jokingly": "teasing",
    "banter": "teasing",
    "lighthearted": "teasing",
    "sarcastic": "sarcastic",
    "sarcastically": "sarcastic",
    "ironic": "sarcastic",
    "dry": "sarcastic",
    "dryly": "sarcastic",
    "snarky": "sarcastic",
    "condescending": "sarcastic",
    "patronizing": "sarcastic",
    "mocking": "sarcastic",
    "cold": "cold",
    "coldly": "cold",
    "flat": "cold",
    "flatly": "cold",
    "detached": "cold",
    "dismissive": "cold",
    "curt": "cold",
    "curtly": "cold",
    "icy": "cold",
    "hostile": "hostile",
    "sharp": "hostile",
    "sharply": "hostile",
    "harsh": "hostile",
    "harshly": "hostile",
    "snapping": "hostile",
    "aggressive": "hostile",
    "angry": "hostile",
    "angrily": "hostile",
    "bitter": "hostile",
    "serious": "serious",
    "seriously": "serious",
    "grave": "serious",
    "gravely": "serious",
    "earnest": "serious",
    "earnestly": "serious",
    "urgent": "serious",
    "firm": "serious",
    "stern": "serious",
    "apologetic": "apologetic",
    "apologetically": "apologetic",
    "sorry": "apologetic",
    "contrite": "apologetic",
    "hesitant": "apologetic",
    "sheepish": "apologetic",
    "placating": "apologetic",
    "guarded": "guarded",
    "guardedly": "guarded",
    "defensive": "guarded",
    "defensively": "guarded",
    "tense": "guarded",
    "wary": "guarded",
    "evasive": "guarded",
}

#: Natural non-robotic adverb/phrase rendered for room context and narration.
TONE_ADVERBS: Dict[str, str] = {
    "warm": "warmly",
    "teasing": "teasingly",
    "sarcastic": "sarcastically",
    "cold": "coldly",
    "hostile": "sharply",
    "serious": "seriously",
    "apologetic": "apologetically",
    "guarded": "guardedly",
    "mocking": "in a sharp, mocking tone",
    "strained": "in a strained, forced tone",
}

_PREFIX_TAG_RE = re.compile(r"^\[(lang|tone):([^\]]+)\]\s*", re.IGNORECASE)


def normalize_speech_tone(raw: Any) -> Optional[str]:
    """Normalize a raw tone string onto the 8 canonical delivery tones, or None."""
    if raw is None:
        return None
    cleaned = str(raw).strip().lower()
    if not cleaned or cleaned in ("none", "null", "neutral", "plain", "normal", "default"):
        return None
    if cleaned in TONE_ALIASES:
        return TONE_ALIASES[cleaned]
    # Handle short phrases like "dry sarcasm" or "playful banter"
    for token in re.findall(r"[a-z]+", cleaned):
        if token in TONE_ALIASES:
            return TONE_ALIASES[token]
    return None


def strip_speech_prefixes(raw_speech: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Strip leading [lang:...] and/or [tone:...] prefixes in any order.

    Returns ``(clean_speech, explicit_lang, explicit_tone)``.
    """
    speech = str(raw_speech or "").strip()
    explicit_lang: Optional[str] = None
    explicit_tone: Optional[str] = None
    while speech:
        m = _PREFIX_TAG_RE.match(speech)
        if not m:
            break
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if key == "lang" and val:
            explicit_lang = val
        elif key == "tone":
            explicit_tone = normalize_speech_tone(val)
        speech = speech[m.end() :].strip()
    return speech, explicit_lang, explicit_tone


def format_tone_adverb(perceived_tone: Optional[str], strained_leak: bool = False) -> str:
    """Return a natural spoken-delivery phrase, or empty string when plain."""
    if strained_leak:
        return TONE_ADVERBS["strained"]
    if not perceived_tone:
        return ""
    return TONE_ADVERBS.get(str(perceived_tone).strip().lower(), "")


def _player_insight(player: Any, default: int = 10) -> int:
    stats = getattr(player, "stats", None)
    if isinstance(stats, dict):
        try:
            return int(stats.get("WIS", stats.get("Insight", default)) or default)
        except (TypeError, ValueError):
            pass
    return default


def _player_closeness(listener: Any, speaker: Any, speaker_name: Optional[str] = None) -> float:
    if listener is None:
        return 0.0
    sname = speaker_name or getattr(speaker, "name", None)
    if not sname:
        return 0.0
    try:
        from engine.relationships import get_relationship

        rel = get_relationship(listener, sname) or {}
        return float(rel.get("closeness", 0.0) or 0.0)
    except Exception:
        return 0.0


def _speaker_is_strained(
    speaker: Any,
    speaker_autonomic: Optional[Dict[str, float]],
    speaker_overloaded: bool,
) -> bool:
    if speaker_overloaded:
        return True
    if speaker_autonomic:
        peak = max(
            abs(float(speaker_autonomic.get("heart_rate", 0.0) or 0.0)),
            abs(float(speaker_autonomic.get("muscle_tension", 0.0) or 0.0)),
            abs(float(speaker_autonomic.get("gut_throat", 0.0) or 0.0)),
            abs(float(speaker_autonomic.get("breathing", 0.0) or 0.0)),
        )
        if peak >= 55.0:
            return True
    if speaker is not None and hasattr(speaker, "emotions_map"):
        try:
            from engine.emotion import BASELINES

            emap = speaker.emotions_map() or {}
            stress_dims = ("afraid", "terrified", "angry", "furious", "ashamed", "humiliated", "anxious", "dread")
            max_over = max(
                (float(emap.get(d, 0.0) or 0.0) - float(BASELINES.get(d, 10.0)) for d in stress_dims),
                default=0.0,
            )
            if max_over >= 45.0:
                return True
        except Exception:
            pass
    return False


def _listener_prior_distress(
    listener: Any,
    listener_families: Optional[Dict[str, float]],
) -> Tuple[float, float]:
    """Return (prior_shame_sad_over_baseline, prior_anger_over_baseline)."""
    if listener_families:
        shame_over = max(0.0, float(listener_families.get("shame", 8.0) or 0.0) - 8.0)
        sad_over = max(0.0, float(listener_families.get("sadness", 8.0) or 0.0) - 8.0)
        anger_over = max(0.0, float(listener_families.get("anger", 8.0) or 0.0) - 8.0)
        return shame_over + sad_over, anger_over
    if listener is not None and hasattr(listener, "emotions_map"):
        try:
            from engine.emotion import BASELINES

            emap = listener.emotions_map() or {}
            shame_over = max(
                (
                    max(0.0, float(emap.get(d, 0.0) or 0.0) - float(BASELINES.get(d, 8.0)))
                    for d in ("ashamed", "humiliated", "embarrassed")
                ),
                default=0.0,
            )
            sad_over = max(
                (
                    max(0.0, float(emap.get(d, 0.0) or 0.0) - float(BASELINES.get(d, 8.0)))
                    for d in ("sad", "grieving", "lonely", "melancholic")
                ),
                default=0.0,
            )
            anger_over = max(
                (
                    max(0.0, float(emap.get(d, 0.0) or 0.0) - float(BASELINES.get(d, 8.0)))
                    for d in ("angry", "furious", "irritated", "resentful")
                ),
                default=0.0,
            )
            return shame_over + sad_over, anger_over
        except Exception:
            pass
    return 0.0, 0.0


def perceive_speech_tone(
    intended_tone: Any,
    *,
    speaker: Any = None,
    listener: Any = None,
    speaker_name: Optional[str] = None,
    speaker_autonomic: Optional[Dict[str, float]] = None,
    speaker_overloaded: bool = False,
    listener_families: Optional[Dict[str, float]] = None,
    closeness: Optional[float] = None,
    listener_insight: Optional[int] = None,
    same_area: Optional[bool] = None,
    distance: Optional[int] = None,
    proximity_hops: Optional[int] = None,
    proximity_checked: bool = False,
) -> Dict[str, Any]:
    """Compute a listener's subjective perception of a speaker's delivery tone.

    Spatial proximity (``same_area``, cross-area ``distance``, and intra-room
    ``proximity_hops``) dampens subtle vocal-strain leaks and subtle sarcasm so
    a listener across a yard or in an adjacent area cannot read micro-tension
    the way someone standing right beside the speaker does.

    Returns a dict:
      - intended_tone: canonical intended tone or None
      - perceived_tone: canonical perceived tone ("mocking"/"strained" possible) or None
      - strained_leak: True when speaker's involuntary distress bled through delivery
      - misread_reason: short machine tag when perceived_tone != intended_tone
      - perception_note: concise plain-English summary for prompts/telemetry
      - adverb: natural adverb/phrase for room context rendering
    """
    intended = normalize_speech_tone(intended_tone)
    if intended is None:
        return {
            "intended_tone": None,
            "perceived_tone": None,
            "strained_leak": False,
            "misread_reason": None,
            "perception_note": "",
            "adverb": "",
        }

    close_val = float(closeness) if closeness is not None else _player_closeness(listener, speaker, speaker_name)
    insight_val = int(listener_insight) if listener_insight is not None else _player_insight(listener, default=10)
    strained = _speaker_is_strained(speaker, speaker_autonomic, speaker_overloaded)
    prior_shame_sad, prior_anger = _listener_prior_distress(listener, listener_families)

    if distance is not None:
        eff_distance = max(0, int(distance))
    elif same_area is False:
        eff_distance = 1
    else:
        eff_distance = 0
    in_same_area = (eff_distance == 0) and (same_area is not False)
    across_room = in_same_area and bool(proximity_checked) and (proximity_hops is None)

    # 1. Speaker involuntary body strain leaks through attempted warmth/casualness/composure,
    # attenuated by physical distance (same-area close > across room > adjacent area > far).
    if intended in ("warm", "teasing", "serious") and strained:
        if in_same_area and not across_room:
            if speaker_overloaded and (insight_val >= 10 or close_val >= 20.0):
                return {
                    "intended_tone": intended,
                    "perceived_tone": "strained",
                    "strained_leak": True,
                    "misread_reason": "speaker_body_strain_leak",
                    "perception_note": f"tried to sound {intended}, but their voice came out tight and strained",
                    "adverb": TONE_ADVERBS["strained"],
                }
            if insight_val >= 13 or close_val >= 25.0:
                return {
                    "intended_tone": intended,
                    "perceived_tone": "strained",
                    "strained_leak": True,
                    "misread_reason": "speaker_body_strain_leak",
                    "perception_note": f"aimed for {intended}, but tension bled through their voice",
                    "adverb": TONE_ADVERBS["strained"],
                }
        elif across_room:
            if speaker_overloaded and (insight_val >= 12 or close_val >= 30.0):
                return {
                    "intended_tone": intended,
                    "perceived_tone": "strained",
                    "strained_leak": True,
                    "misread_reason": "speaker_body_strain_leak",
                    "perception_note": f"tried to sound {intended} from across the room, but the strain still carried",
                    "adverb": TONE_ADVERBS["strained"],
                }
            if insight_val >= 15 or close_val >= 45.0:
                return {
                    "intended_tone": intended,
                    "perceived_tone": "strained",
                    "strained_leak": True,
                    "misread_reason": "speaker_body_strain_leak",
                    "perception_note": f"aimed for {intended} across the room, though tight tension still showed",
                    "adverb": TONE_ADVERBS["strained"],
                }
        elif eff_distance == 1:
            # Cross-area listeners cannot read subtle micro-strain; only outright overload
            # leaks across one open hop to someone very perceptive or very close.
            if speaker_overloaded and (insight_val >= 15 or close_val >= 45.0 or (insight_val >= 13 and close_val >= 35.0)):
                return {
                    "intended_tone": intended,
                    "perceived_tone": "strained",
                    "strained_leak": True,
                    "misread_reason": "speaker_body_strain_leak",
                    "perception_note": f"called out trying to sound {intended}, though the strain carried across the distance",
                    "adverb": TONE_ADVERBS["strained"],
                }
        # eff_distance >= 2: subtle vocal strain does not carry through multiple areas.

    # 2. Teasing is subjective: warm banter with a steady friend, sharp/mocking when
    # heard by an already ashamed/angry listener or from someone you are not close to.
    if intended == "teasing":
        if prior_shame_sad >= 25.0 or prior_anger >= 25.0:
            return {
                "intended_tone": intended,
                "perceived_tone": "mocking",
                "strained_leak": False,
                "misread_reason": "listener_mood_misread",
                "perception_note": "heard the teasing banter as sharp and mocking through their current raw mood",
                "adverb": TONE_ADVERBS["mocking"],
            }
        if close_val < 15.0:
            return {
                "intended_tone": intended,
                "perceived_tone": "mocking",
                "strained_leak": False,
                "misread_reason": "low_closeness_misread",
                "perception_note": "heard the teasing remark from a non-close speaker as mocking",
                "adverb": TONE_ADVERBS["mocking"],
            }

    # 3. Low-Insight or distant strangers can miss subtle sarcasm and take polite words at face value.
    if intended == "sarcastic":
        missed_sarcasm = False
        if eff_distance >= 2:
            missed_sarcasm = close_val < 35.0 and insight_val <= 13
        elif eff_distance == 1 or across_room:
            missed_sarcasm = close_val < 25.0 and insight_val <= 11
        else:
            missed_sarcasm = close_val < 15.0 and insight_val <= 8
        if missed_sarcasm:
            return {
                "intended_tone": intended,
                "perceived_tone": None,
                "strained_leak": False,
                "misread_reason": "missed_subtle_sarcasm",
                "perception_note": "missed the sarcastic edge and took the words at face value",
                "adverb": "",
            }

    return {
        "intended_tone": intended,
        "perceived_tone": intended,
        "strained_leak": False,
        "misread_reason": None,
        "perception_note": f"sounded {TONE_ADVERBS.get(intended, intended)}",
        "adverb": TONE_ADVERBS.get(intended, ""),
    }
