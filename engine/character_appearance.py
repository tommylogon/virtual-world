"""Structured appearance and personality (task-507, expanded 828).

Optional structured fields alongside prose, in two modes - prose-only,
or fully structured - with the structured block as source of truth and
prose as the narrative layer rendered *once* from it via an explicit
compile step.

Storage: ONE block on the character graph node
``properties["persona"]`` with four sections nested underneath::

    identity     pronouns, age, gender, species, occupation, sexuality, mbti,
                 alignment, birthday, potential_storylines
    appearance   overview, height_cm, weight_kg, build, hair{}, eyes{},
                 skin{}, face{}, body{+modifications[]}, voice{}, scent,
                 style{}
    personality  likes, dislikes, fears, interests, kinks, turn_ons,
                 turn_offs, traumas, boundaries, traits, aspirations,
                 quirks, habits, speech_pattern{}, experience
    narrative    biography{}, secrets{}, example_dialogues[],
                 role_in_town, arc, media[]


Growth (task-829): every field is mutable at runtime via
``set_persona_field`` / ``add_persona_id`` / ``remove_persona_id`` /
``advance_age`` so items and trigger effects can change lenses, hair,
tattoos, prosthetics, kinks, traumas, fears - characters become more
than they started.

@module character_appearance
@contributes StructuredError, identity_suggestions, normalize_slug, get_record, is_structured, appearance
@docs docs/virtualWorld/AI & Narration/Memory System.md
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple

#: Node property holding the structured block. One key, not two, so "is this
#: character structured?" is a single membership test.
RECORD_KEY = "persona"
#: Legacy block key, carried by old scenarios and library saves. The load shim
#: in ``get_record`` resolves it when the new key is absent.
_LEGACY_KEY = "appearance"

#: The curated appearance schema: field -> (kind, subfields).
#: ``kind`` is "number" | "text" | "enum" | "idlist" | "proselist", and
#: ``subfields`` only for groups.
APPEARANCE_FIELDS: Dict[str, Any] = {
    "overview": ("text", None),
    "height_cm": ("number", None),
    "weight_kg": ("number", None),
    "build": ("text", None),
    "hair": ("group", ("color", "length", "style", "accessories")),
    "eyes": ("group", ("color", "shape", "special")),
    "skin": ("group", ("tone", "condition", "distinguishing_features")),
    "face": ("group", ("shape", "features", "makeup")),
    "body": ("group", ("chest", "waist", "hips", "legs", "butt",
                        "modifications")),
    "voice": ("group", ("pitch", "accent", "mannerisms")),
    "scent": ("text", None),
    "style": ("group", ("clothing", "accessories", "footwear")),
}

#: Identity fields: who this person is on paper. pronouns/age are the
#: two task-733 prose gates; sexuality feeds prompt voice. mbti and alignment
#: feed disposition / prompt voice; birthday is calendar metadata vs age.
IDENTITY_FIELDS: Dict[str, Any] = {
    "pronouns": ("text", None),
    "age": ("number", None),
    "gender": ("text", None),
    "species": ("text", None),
    "occupation": ("text", None),
    "sexuality": ("text", None),
    "mbti": ("text", None),
    "alignment": ("text", None),
    "birthday": ("text", None),
    "potential_storylines": ("proselist", None),
}

#: Suggested values for identity text fields, offered by the Persona tab as a
#: pick-list next to the free-text input (task-852). The stored value stays a
#: plain string: validation never checks it against these. Only fields with a
#: declared vocabulary appear here; ``species`` is added from
#: ``engine.species.SPECIES_PROFILES`` by ``identity_suggestions`` so that
#: table stays the one species list. ``occupation`` has no declared
#: vocabulary and is deliberately absent.
#:
#: ``pronouns`` lists only sets ``engine.pronouns`` can resolve (first token
#: before "/", see ``_EXPLICIT``); a test pins that. "it/its" and "any" are
#: left out until that module can act on them.
IDENTITY_SUGGESTIONS: Dict[str, tuple] = {
    "pronouns": ("she/her", "he/him", "they/them", "she/they", "he/they"),
    "gender": ("woman", "man", "non-binary", "genderqueer", "agender",
               "genderfluid", "trans woman", "trans man"),
    "sexuality": ("straight", "gay", "lesbian", "bisexual", "pansexual",
                  "asexual", "queer", "demisexual"),
    "mbti": (
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP",
    ),
    "alignment": (
        "Lawful Good", "Neutral Good", "Chaotic Good",
        "Lawful Neutral", "True Neutral", "Chaotic Neutral",
        "Lawful Evil", "Neutral Evil", "Chaotic Evil",
    ),
}


def identity_suggestions() -> Dict[str, List[str]]:
    """Field -> suggested values, for the Persona tab's pick-lists."""
    from engine.species import SPECIES_PROFILES
    out: Dict[str, List[str]] = {
        field: list(values) for field, values in IDENTITY_SUGGESTIONS.items()}
    out["species"] = sorted(SPECIES_PROFILES)
    return out

#: Narrative fields: biography/secrets/dialogue/role. Biography and
#: secrets project to memories/known (task-404/366); dialogues and voice
#: feed prompt voice.
NARRATIVE_FIELDS: Dict[str, Any] = {
    "biography": ("group", ("early_life", "adulthood", "current_situation")),
    "secrets": ("group", ("deepest_secret", "hidden_facts", "known_by")),
    "example_dialogues": ("proselist", None),
    "role_in_town": ("text", None),
    "arc": ("text", None),
    "media": ("proselist", None),
}

#: Personality fields, all lists of **ids** or prose. The mechanic each
#: one feeds is named here so a field cannot be added without saying
#: what reads it.
PERSONALITY_FIELDS: Dict[str, str] = {
    "likes": "gifts and dialogue targeting",
    "dislikes": "gifts and dialogue targeting",
    "fears": "engine.fear fear_tags; the same id vocabulary",
    "interests": "attention/interest_tags; what they notice",
    "kinks": "affect_for_stimulus -> arousal",
    "turn_ons": "affect_for_stimulus -> arousal (WorldGraph names)",
    "turn_offs": "affect_for_stimulus -> disgust and negative arousal",
    "traumas": "fear_tags + frightened condition; backstory wounds",
    "boundaries": "consent gate for intimacy prompts",
    "traits": "personality trait tags (slugs)",
    "aspirations": "goals/plans projection tags (slugs)",
    "quirks": "prompt voice colour tags (slugs)",
    "habits": "background behaviour tags (slugs)",
    "speech_pattern": "prompt voice (style/dialect/catchphrases)",
    "experience": "intimacy prompt context (WorldGraph experience)",
}

#: Canonical 18 skills (D&D-style skill list).
CANONICAL_SKILLS: Tuple[str, ...] = (
    "Acrobatics",
    "Animal Handling",
    "Arcana",
    "Athletics",
    "Deception",
    "History",
    "Insight",
    "Intimidation",
    "Investigation",
    "Medicine",
    "Nature",
    "Perception",
    "Performance",
    "Persuasion",
    "Religion",
    "Sleight of Hand",
    "Stealth",
    "Survival",
)

_CANONICAL_SKILL_MAP: Dict[str, str] = {
    s.lower().replace(" ", "_").replace("-", "_"): s
    for s in CANONICAL_SKILLS
}


def _normalize_skill(raw: Any) -> str:
    """Map a skill name or slug to its canonical name when it matches CANONICAL_SKILLS."""
    text = str(raw or "").strip()
    if not text:
        return ""
    key = normalize_slug(text).replace("-", "_")
    return _CANONICAL_SKILL_MAP.get(key, text)


def _apparent_age_bracket(age: float) -> str:
    """Return an observable apparent-age bracket instead of an exact number."""
    if age < 13:
        return "child"
    if age < 16:
        return "young teenager"
    if age < 18:
        return "mid-teens"
    if age < 20:
        return "late teens"
    if age < 26:
        return "early twenties"
    if age < 30:
        return "late twenties"
    if age < 34:
        return "early thirties"
    if age < 37:
        return "mid-thirties"
    if age < 40:
        return "late thirties"
    if age < 44:
        return "early forties"
    if age < 47:
        return "mid-forties"
    if age < 50:
        return "late forties"
    if age < 55:
        return "early fifties"
    if age < 60:
        return "late fifties"
    if age < 70:
        return "sixties"
    if age < 80:
        return "seventies"
    return "elderly"


#: Valid fluency tiers for structured language competence (task-966).
LANGUAGE_FLUENCY_LEVELS: tuple = (
    "native", "fluent", "conversational", "broken", "none",
)

#: Valid competence tiers for structured domain knowledge (task-968).
DOMAIN_COMPETENCE_LEVELS: tuple = (
    "ignorant", "novice", "familiar", "expert",
)

#: Capabilities fields (task-733, task-966, task-968): skills, languages, domains, weaknesses.
#: Project to player skills, languages, domains, and traits.
CAPABILITIES_FIELDS: Dict[str, Any] = {
    "skills": ("idlist", None),
    "languages": ("languages", None),
    "domains": ("domains", None),
    "weaknesses": ("idlist", None),
}

#: Which personality fields hold ids (slug discipline) vs free prose.
ID_LIST_FIELDS = frozenset({
    "likes", "dislikes", "fears", "interests", "kinks", "turn_ons",
    "turn_offs", "traumas", "boundaries", "traits", "aspirations",
    "quirks", "habits",
})
PROSE_LIST_FIELDS = frozenset()

#: Group subfields that hold lists of short strings (kit, features,
#: garments) rather than a single value. A bare string wraps to one item,
#: because a form often posts one; anything else must be a list.
APPEARANCE_LIST_SUBS = frozenset({
    "accessories", "distinguishing_features", "modifications",
    "clothing", "footwear",
})
#: An id is a slug: lowercase, digits, underscore or dash. Deliberately strict,
#: because the alternative is a display name sneaking in and becoming a
#: reference that breaks on rename.
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def normalize_slug(value: Any) -> str:
    """Normalize a string to a valid tag slug: lowercase, [a-z0-9_-], no leading/trailing punctuation.

    Converts diacritics to ascii, replaces spaces and non-alphanumeric punctuation with underscores,
    and collapses repeated separators.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("_-")

#: Plausible human ranges, used to reject a typo rather than to police a design.
HEIGHT_CM_RANGE = (40, 260)
WEIGHT_KG_RANGE = (10, 400)


class StructuredError(ValueError):
    """A structured block that cannot be accepted. Carries per-field detail."""


# ── reading ──

def get_record(node) -> Dict[str, Any]:
    """The structured block on *node*, or ``{}``.

    Prose-only characters simply have no block, and that is the normal case, not
    a missing feature - hence the empty default rather than a fill-in template.

    Load shim (task-865): resolves the old ``appearance`` block key when the new
    ``persona`` key is absent.  The value is returned through the new key without
    mutating the node here - mutation happens at the next write (set_record).
    """
    if node is None:
        return {}
    props = getattr(node, "properties", None) or {}
    record = props.get(RECORD_KEY)
    if record is None:
        record = props.get(_LEGACY_KEY)
    return dict(record) if isinstance(record, dict) else {}


def is_structured(node) -> bool:
    """True when this character has a structured block at all."""
    return bool(get_record(node))


def appearance(node) -> Dict[str, Any]:
    return dict(get_record(node).get("appearance") or {})


def personality(node) -> Dict[str, Any]:
    return dict(get_record(node).get("personality") or {})


def identity(node) -> Dict[str, Any]:
    return dict(get_record(node).get("identity") or {})


def capabilities(node) -> Dict[str, Any]:
    return dict(get_record(node).get("capabilities") or {})


def narrative(node) -> Dict[str, Any]:
    return dict(get_record(node).get("narrative") or {})


# ── writing ──

def _clean_short_list(raw: Any, dotted: str) -> List[str]:
    """A list of short free-text strings (kit, features, dialogue lines).

    A bare string wraps to one item; anything else must be a list. Empty
    strings drop out; an empty result is ``[]``, letting the caller decide
    whether the field survives.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple, set)):
        raise StructuredError(f"{dotted} must be a list of strings")
    out = []
    for entry in raw:
        entry = str(entry).strip()
        if entry and entry not in out:
            out.append(entry)
    return out


#: Canonical dd.mm.yyyy birthday format (also accepts d.m.yyyy, dd/mm/yyyy,
#: dd-mm-yyyy, or ISO yyyy-mm-dd on input and normalizes to dd.mm.yyyy).
BIRTHDAY_CANONICAL_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
_BIRTHDAY_DMY_RE = re.compile(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$")
_BIRTHDAY_ISO_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")


def parse_birthday(raw: Any) -> Optional[tuple]:
    """Parse a birthday string into ``(day, month, year)`` ints, or ``None``.

    Accepts ``dd.mm.yyyy`` (canonical), ``d.m.yyyy``, ``dd/mm/yyyy``,
    ``dd-mm-yyyy``, or ISO ``yyyy-mm-dd``. Validates ``1 <= day <= 31``,
    ``1 <= month <= 12``, ``1 <= year <= 9999``.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    m = _BIRTHDAY_DMY_RE.match(s)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m_iso = _BIRTHDAY_ISO_RE.match(s)
        if not m_iso:
            return None
        year, month, day = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1 <= year <= 9999):
        return None
    return (day, month, year)


def normalize_birthday(raw: Any) -> str:
    """Validate and normalize *raw* into ``dd.mm.yyyy`` format.

    Raises :class:`StructuredError` when *raw* is not a valid date.
    """
    parsed = parse_birthday(raw)
    if parsed is None:
        raise StructuredError(
            f"identity.birthday must be in dd.mm.yyyy format (e.g. 14.03.1998), got {raw!r}"
        )
    day, month, year = parsed
    return f"{day:02d}.{month:02d}.{year:04d}"


def _clean_identity(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StructuredError("identity must be an object")
    out: Dict[str, Any] = {}
    for field in IDENTITY_FIELDS:
        if field not in raw:
            continue
        value = raw[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if field == "age":
            try:
                age = float(value)
            except (TypeError, ValueError):
                raise StructuredError(
                    f"identity.age must be a number, got {value!r}")
            if age < 0:
                raise StructuredError(
                    f"identity.age of {age:g} is not plausible")
            out[field] = age
            continue
        if field == "birthday":
            out[field] = normalize_birthday(value)
            continue
        out[field] = str(value).strip()
    return out


def _clean_narrative(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StructuredError("narrative must be an object")
    out: Dict[str, Any] = {}
    for field, (kind, subfields) in NARRATIVE_FIELDS.items():
        if field not in raw:
            continue
        value = raw[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if kind == "group":
            if not isinstance(value, dict):
                raise StructuredError(f"narrative.{field} must be an object")
            group = {}
            for k, v in value.items():
                if k not in subfields:
                    continue
                if k in ("hidden_facts", "known_by"):
                    items = _clean_short_list(v, f"narrative.{field}.{k}")
                    if items:
                        group[k] = items
                    continue
                v = str(v).strip()
                if v:
                    group[k] = v
            if group:
                out[field] = group
            continue
        if field == "media":
            # task-922: media can be list of strings or list of structured objects
            # { title, medium, opinion, familiarity }
            if value is None:
                continue
            if isinstance(value, (str, dict)):
                value = [value]
            if not isinstance(value, (list, tuple, set)):
                raise StructuredError(f"narrative.{field} must be a list")
            media_items = []
            for item in value:
                if isinstance(item, dict):
                    m_dict = {}
                    title = str(item.get("title", "") or "").strip()
                    if not title:
                        continue
                    m_dict["title"] = title
                    for k in ("medium", "when", "opinion", "familiarity"):
                        v = str(item.get(k, "") or "").strip()
                        if v:
                            m_dict[k] = v
                    media_items.append(m_dict)
                else:
                    s = str(item).strip()
                    if s:
                        media_items.append(s)
            if media_items:
                out[field] = media_items
            continue
        if kind == "proselist":
            items = _clean_short_list(value, f"narrative.{field}")
            if items:
                out[field] = items
            continue
        out[field] = str(value).strip()
    return out


def _clean_appearance(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StructuredError("appearance must be an object")
    out: Dict[str, Any] = {}
    for field, (kind, subfields) in APPEARANCE_FIELDS.items():
        if field not in raw:
            continue
        value = raw[field]
        if kind == "group":
            if not isinstance(value, dict):
                raise StructuredError(f"appearance.{field} must be an object")
            group = {}
            for k, v in value.items():
                if k not in subfields:
                    continue
                if k in APPEARANCE_LIST_SUBS:
                    items = _clean_short_list(
                        v, f"appearance.{field}.{k}")
                    if items:
                        group[k] = items
                    continue
                v = str(v).strip() if not isinstance(v, list) else ""
                if v:
                    group[k] = v
            if group:
                out[field] = group
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if kind == "number":
            try:
                out[field] = float(value)
            except (TypeError, ValueError):
                raise StructuredError(
                    f"appearance.{field} must be a number, got {value!r}")
            continue
        out[field] = str(value).strip()
    for field, bounds, label in (
            ("height_cm", HEIGHT_CM_RANGE, "height"),
            ("weight_kg", WEIGHT_KG_RANGE, "weight")):
        if field in out and not (bounds[0] <= out[field] <= bounds[1]):
            raise StructuredError(
                f"appearance.{field} of {out[field]:g}{label} is not plausible")
    return out


def normalize_language_entry(entry: Any) -> Dict[str, Any]:
    """Normalize a single language entry into ``{language, fluency, known_words, literate}`` (task-966).

    Legacy string tags like ``"common"`` normalize to ``fluency="native"`` and
    ``literate=True``; other legacy string tags normalize to ``fluency="fluent"``
    and ``literate=True``.
    """
    if isinstance(entry, str):
        lang = normalize_slug(entry)
        if not lang:
            raise StructuredError("capabilities.languages entry cannot be empty")
        fluency = "native" if lang == "common" else "fluent"
        return {
            "language": lang,
            "fluency": fluency,
            "known_words": [],
            "literate": True,
        }
    if not isinstance(entry, dict):
        raise StructuredError(
            "capabilities.languages entries must be strings or {language, fluency, known_words, literate} objects"
        )
    raw_lang = entry.get("language")
    if raw_lang is None:
        raw_lang = entry.get("id") if entry.get("id") is not None else entry.get("name")
    lang = normalize_slug(raw_lang)
    if not lang:
        raise StructuredError("capabilities.languages entry requires a non-empty language id")
    raw_fluency = entry.get("fluency")
    fluency = "fluent" if raw_fluency is None or str(raw_fluency).strip() == "" else str(raw_fluency).strip().lower()
    if fluency not in LANGUAGE_FLUENCY_LEVELS:
        raise StructuredError(
            f"capabilities.languages[{lang}].fluency must be one of "
            f"{', '.join(LANGUAGE_FLUENCY_LEVELS)}; got {fluency!r}"
        )
    if "literate" in entry and entry["literate"] is not None:
        literate = bool(entry["literate"])
    else:
        literate = fluency in ("native", "fluent")
    raw_words = entry.get("known_words")
    words_out: List[str] = []
    seen_words: set = set()
    if raw_words is not None:
        if isinstance(raw_words, str):
            raw_iter = [w.strip() for w in raw_words.split(",") if w.strip()]
        elif isinstance(raw_words, (list, tuple, set)):
            raw_iter = [str(w).strip() for w in raw_words if str(w).strip()]
        else:
            raise StructuredError(
                f"capabilities.languages[{lang}].known_words must be a list of strings"
            )
        for w in raw_iter:
            if w and w not in seen_words:
                seen_words.add(w)
                words_out.append(w)
    return {
        "language": lang,
        "fluency": fluency,
        "known_words": words_out,
        "literate": literate,
    }


def normalize_languages(raw: Any) -> List[Dict[str, Any]]:
    """Normalize a capabilities.languages value into a deduplicated list of structured entries."""
    if raw is None:
        return []
    if isinstance(raw, str):
        items: List[Any] = [s.strip() for s in raw.split(",") if s.strip()]
    elif isinstance(raw, dict):
        items = []
        for k, v in raw.items():
            if isinstance(v, dict):
                merged = dict(v)
                merged.setdefault("language", k)
                items.append(merged)
            elif isinstance(v, str):
                items.append({"language": k, "fluency": v})
            else:
                items.append({"language": k})
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        raise StructuredError("capabilities.languages must be a list or object")

    by_lang: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for item in items:
        if isinstance(item, str) and not item.strip():
            continue
        norm = normalize_language_entry(item)
        lang = norm["language"]
        if lang not in by_lang:
            order.append(lang)
        by_lang[lang] = norm
    return [by_lang[lang] for lang in order]


def normalize_domain_entry(entry: Any) -> Dict[str, Any]:
    """Normalize one structured capabilities.domains entry (task-968).

    Accepts a string slug (defaults to ``level='familiar'``) or a dict with
    ``{domain, level, notes, jargon_terms}``.
    """
    if isinstance(entry, str):
        dom = normalize_slug(entry)
        if not dom:
            raise StructuredError("capabilities.domains entry cannot be empty")
        return {
            "domain": dom,
            "level": "familiar",
            "notes": "",
            "jargon_terms": [],
        }
    if not isinstance(entry, dict):
        raise StructuredError(
            "capabilities.domains entries must be strings or {domain, level, notes, jargon_terms} objects"
        )
    raw_dom = entry.get("domain")
    if raw_dom is None:
        raw_dom = entry.get("id") if entry.get("id") is not None else entry.get("name")
    dom = normalize_slug(raw_dom)
    if not dom:
        raise StructuredError("capabilities.domains entry requires a non-empty domain id")
    raw_level = entry.get("level")
    level = "familiar" if raw_level is None or str(raw_level).strip() == "" else str(raw_level).strip().lower()
    if level not in DOMAIN_COMPETENCE_LEVELS:
        raise StructuredError(
            f"capabilities.domains[{dom}].level must be one of "
            f"{', '.join(DOMAIN_COMPETENCE_LEVELS)}; got {level!r}"
        )
    notes = str(entry.get("notes") or "").strip()
    raw_terms = entry.get("jargon_terms")
    terms_out: List[str] = []
    seen_terms: set = set()
    if raw_terms is not None:
        if isinstance(raw_terms, str):
            raw_iter = [t.strip() for t in raw_terms.split(",") if t.strip()]
        elif isinstance(raw_terms, (list, tuple, set)):
            raw_iter = [str(t).strip() for t in raw_terms if str(t).strip()]
        else:
            raise StructuredError(
                f"capabilities.domains[{dom}].jargon_terms must be a list of strings"
            )
        for t in raw_iter:
            if t and t not in seen_terms:
                seen_terms.add(t)
                terms_out.append(t)
    return {
        "domain": dom,
        "level": level,
        "notes": notes,
        "jargon_terms": terms_out,
    }


def normalize_domains(raw: Any) -> List[Dict[str, Any]]:
    """Normalize a capabilities.domains value into a deduplicated list of structured entries."""
    if raw is None:
        return []
    if isinstance(raw, str):
        items: List[Any] = [s.strip() for s in raw.split(",") if s.strip()]
    elif isinstance(raw, dict):
        items = []
        for k, v in raw.items():
            if isinstance(v, dict):
                merged = dict(v)
                merged.setdefault("domain", k)
                items.append(merged)
            elif isinstance(v, str):
                items.append({"domain": k, "level": v})
            else:
                items.append({"domain": k})
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        raise StructuredError("capabilities.domains must be a list or object")

    by_dom: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for item in items:
        if isinstance(item, str) and not item.strip():
            continue
        norm = normalize_domain_entry(item)
        dom = norm["domain"]
        if dom not in by_dom:
            order.append(dom)
        by_dom[dom] = norm
    return [by_dom[dom] for dom in order]


def _clean_capabilities(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StructuredError("capabilities must be an object")
    out: Dict[str, Any] = {}
    for field in ("skills", "languages", "domains", "weaknesses"):
        if field not in raw:
            continue
        val = raw[field]
        if val is None:
            continue
        if field == "languages":
            langs = normalize_languages(val)
            if langs:
                out[field] = langs
            continue
        if field == "domains":
            doms = normalize_domains(val)
            if doms:
                out[field] = doms
            continue
        if field == "skills":
            if isinstance(val, dict):
                skills_dict: Dict[str, int] = {}
                for k, v in val.items():
                    k_str = str(k).strip()
                    if not k_str:
                        continue
                    try:
                        skills_dict[k_str] = int(v)
                    except (TypeError, ValueError):
                        skills_dict[k_str] = 1
                if skills_dict:
                    out[field] = skills_dict
                continue
            if isinstance(val, str):
                val = [s.strip() for s in val.split(",") if s.strip()]
            if not isinstance(val, (list, tuple, set)):
                raise StructuredError("capabilities.skills must be a list or object")
            skills_list = [str(x).strip() for x in val if str(x).strip()]
            if skills_list:
                out[field] = skills_list
            continue
        if isinstance(val, str):
            val = [s.strip() for s in val.split(",") if s.strip()]
        if not isinstance(val, (list, tuple, set)):
            raise StructuredError(f"capabilities.{field} must be a list")
        items = [str(x).strip() for x in val if str(x).strip()]
        if items:
            out[field] = items
    return out


def _clean_personality(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StructuredError("personality must be an object")
    out: Dict[str, Any] = {}
    for field in PERSONALITY_FIELDS:
        if field not in raw:
            continue
        value = raw[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if field == "speech_pattern":
            if not isinstance(value, dict):
                raise StructuredError(
                    "personality.speech_pattern must be an object")
            group = {}
            for k in ("style", "dialect"):
                v = str(value.get(k, "") or "").strip()
                if v:
                    group[k] = v
            phrases = _clean_short_list(
                value.get("catchphrases"), "personality.speech_pattern.catchphrases")
            if phrases:
                group["catchphrases"] = phrases
            if group:
                out[field] = group
            continue
        if field == "experience":
            # task-923: support both legacy string and structured intimacy experience
            if isinstance(value, dict):
                exp: Dict[str, Any] = {}
                lvl = str(value.get("intimacy_level", "") or "").strip()
                if lvl:
                    exp["intimacy_level"] = lvl
                partners = _clean_short_list(
                    value.get("significant_partners"),
                    "personality.experience.significant_partners",
                )
                if partners:
                    exp["significant_partners"] = partners
                for lim_key in ("hard_limits", "soft_limits"):
                    raw_lims = value.get(lim_key)
                    if raw_lims:
                        cleaned_lims = []
                        if isinstance(raw_lims, str):
                            raw_lims = [raw_lims]
                        if isinstance(raw_lims, (list, tuple, set)):
                            for lim_entry in raw_lims:
                                slug = normalize_slug(lim_entry)
                                if slug and slug not in cleaned_lims:
                                    cleaned_lims.append(slug)
                        if cleaned_lims:
                            exp[lim_key] = cleaned_lims
                if exp:
                    out[field] = exp
            else:
                out[field] = str(value).strip()
            continue
        if field in PROSE_LIST_FIELDS:
            items = _clean_short_list(value, f"personality.{field}")
            if items:
                out[field] = items
            continue
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple, set)):
            raise StructuredError(
                f"personality.{field} must be a list of ids")
        ids, bad = [], []
        for entry in value:
            entry = str(entry).strip()
            if not entry:
                continue
            if not _ID_RE.match(entry):
                bad.append(entry)
                continue
            if entry not in ids:
                ids.append(entry)
        if bad:
            raise StructuredError(
                f"personality.{field} must hold ids, not display names; "
                f"rejected {bad}")
        if ids:
            out[field] = ids
    return out


def validate(record: Any) -> Dict[str, Any]:
    """Validate and normalise a structured block.

    Raises :class:`StructuredError` naming the offending field. Rejecting is the
    right behaviour: a silently dropped kink is a character who mysteriously does
    not respond, which is far harder to notice than a 400.
    """
    if record is None:
        return {}
    if not isinstance(record, dict):
        raise StructuredError("the structured block must be an object")
    unknown = sorted(set(record) - {"appearance", "personality",
                                    "identity", "capabilities", "narrative"})
    if unknown:
        raise StructuredError(f"unknown top-level keys: {unknown}")
    out: Dict[str, Any] = {}
    identity_block = _clean_identity(record.get("identity"))
    appearance_block = _clean_appearance(record.get("appearance"))
    personality_block = _clean_personality(record.get("personality"))
    capabilities_block = _clean_capabilities(record.get("capabilities"))
    narrative_block = _clean_narrative(record.get("narrative"))
    if identity_block:
        out["identity"] = identity_block
    if appearance_block:
        out["appearance"] = appearance_block
    if personality_block:
        out["personality"] = personality_block
    if narrative_block:
        out["narrative"] = narrative_block
    if capabilities_block:
        out["capabilities"] = capabilities_block
    return out


def validate_persona_conflicts(record: Any) -> List[str]:
    """Find conflicting preference tags across polar pairs in a persona record (task-916).

    Checks:
    - likes vs dislikes
    - turn_ons vs turn_offs
    - fears vs kinks

    Returns a list of human-readable warning strings. Non-blocking.
    """
    if not isinstance(record, dict):
        return []
    pers = record.get("personality", record)
    if not isinstance(pers, dict):
        return []

    warnings: List[str] = []

    def _check_pair(field_a: str, field_b: str) -> None:
        list_a = set(pers.get(field_a) or ())
        list_b = set(pers.get(field_b) or ())
        overlap = sorted(list_a & list_b)
        for tag in overlap:
            warnings.append(
                f"Conflicting preferences: '{tag}' appears in both {field_a} and {field_b}"
            )

    _check_pair("likes", "dislikes")
    _check_pair("turn_ons", "turn_offs")
    _check_pair("fears", "kinks")
    return warnings


def validate_before_compile(record: Any) -> Tuple[bool, List[str]]:
    """Validate a persona record before compiling into prose primitives (task-919).

    Returns (is_valid, errors). Fails closed if critical validation errors exist.
    """
    if record is None:
        return True, []
    if not isinstance(record, dict):
        return False, ["Persona record must be an object"]
    if not record:
        return True, []

    errors: List[str] = []

    unknown = sorted(set(record) - {"appearance", "personality", "identity", "capabilities", "narrative"})
    if unknown:
        errors.append(f"Unknown top-level sections: {unknown}")

    ident = record.get("identity")
    if ident is not None and not isinstance(ident, dict):
        errors.append("identity section must be an object")
    elif isinstance(ident, dict):
        if "age" in ident and ident["age"] is not None:
            try:
                age = float(ident["age"])
                if age < 0 or age > 10000:
                    errors.append(f"identity.age ({age:g}) is out of plausible range")
            except (TypeError, ValueError):
                errors.append(f"identity.age must be numeric, got {ident['age']!r}")
        if "birthday" in ident and ident["birthday"] is not None:
            if parse_birthday(ident["birthday"]) is None:
                errors.append(f"identity.birthday is invalid: {ident['birthday']!r}")

    app_sec = record.get("appearance")
    if app_sec is not None and not isinstance(app_sec, dict):
        errors.append("appearance section must be an object")
    elif isinstance(app_sec, dict):
        for field, (kind, _) in APPEARANCE_FIELDS.items():
            if field in app_sec and kind == "number" and app_sec[field] is not None:
                try:
                    val = float(app_sec[field])
                    if field == "height_cm" and not (HEIGHT_CM_RANGE[0] <= val <= HEIGHT_CM_RANGE[1]):
                        errors.append(f"appearance.height_cm ({val:g}) is out of range")
                    elif field == "weight_kg" and not (WEIGHT_KG_RANGE[0] <= val <= WEIGHT_KG_RANGE[1]):
                        errors.append(f"appearance.weight_kg ({val:g}) is out of range")
                except (TypeError, ValueError):
                    errors.append(f"appearance.{field} must be numeric, got {app_sec[field]!r}")

    pers = record.get("personality")
    if pers is not None and not isinstance(pers, dict):
        errors.append("personality section must be an object")
    elif isinstance(pers, dict):
        for field in ID_LIST_FIELDS:
            if field in pers:
                vals = pers[field]
                if isinstance(vals, str):
                    vals = [vals]
                if not isinstance(vals, (list, tuple, set)):
                    errors.append(f"personality.{field} must be a list of ids")
                else:
                    for v in vals:
                        s = str(v).strip()
                        if s and not _ID_RE.match(s):
                            errors.append(f"personality.{field} contains invalid slug {v!r}")

    cap = record.get("capabilities")
    if cap is not None and not isinstance(cap, dict):
        errors.append("capabilities section must be an object")
    elif isinstance(cap, dict):
        if "weaknesses" in cap and cap["weaknesses"] is not None:
            vals = cap["weaknesses"]
            if isinstance(vals, str):
                vals = [vals]
            if not isinstance(vals, (list, tuple, set)):
                errors.append("capabilities.weaknesses must be a list")
        if "languages" in cap and cap["languages"] is not None:
            try:
                normalize_languages(cap["languages"])
            except StructuredError as e:
                errors.append(str(e))
        if "domains" in cap and cap["domains"] is not None:
            try:
                normalize_domains(cap["domains"])
            except StructuredError as e:
                errors.append(str(e))
        if "skills" in cap and cap["skills"] is not None:
            vals = cap["skills"]
            if isinstance(vals, str):
                vals = [vals]
            if not isinstance(vals, (list, tuple, set, dict)):
                errors.append("capabilities.skills must be a list or object")

    narr = record.get("narrative")
    if narr is not None and not isinstance(narr, dict):
        errors.append("narrative section must be an object")

    return len(errors) == 0, errors


def get_character_boundaries(node) -> Dict[str, List[str]]:
    """Return consolidated boundaries, hard limits, and soft limits for a character node (task-923)."""
    record = get_record(node)
    pers = record.get("personality") or {}
    boundaries = list(pers.get("boundaries") or [])
    exp = pers.get("experience")
    hard_limits = list(boundaries)
    soft_limits: List[str] = []
    if isinstance(exp, dict):
        for h in (exp.get("hard_limits") or []):
            if h not in hard_limits:
                hard_limits.append(h)
        soft_limits = list(exp.get("soft_limits") or [])
    return {
        "boundaries": boundaries,
        "hard_limits": hard_limits,
        "soft_limits": soft_limits,
    }


def validate_persona_batch(characters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a batch of character persona sheets (task-924).

    Returns a structured health summary:
    {
        "total": int,
        "valid_count": int,
        "warning_count": int,
        "error_count": int,
        "results": [
            {
                "name": str,
                "valid": bool,
                "errors": list[str],
                "warnings": list[str],
            }
        ]
    }
    """
    total = len(characters)
    valid_count = 0
    warning_count = 0
    error_count = 0
    results = []

    for char in characters:
        name = str(char.get("name") or char.get("id") or "unnamed")
        record = char.get("record") or char.get("persona") or char
        is_persona = any(k in record for k in ("identity", "appearance", "personality", "narrative"))
        if not is_persona and "properties" in char:
            record = char["properties"].get("persona") or {}

        char_errors: List[str] = []
        try:
            cleaned = validate(record)
            is_valid, compile_errors = validate_before_compile(cleaned)
            if not is_valid:
                char_errors.extend(compile_errors)
        except StructuredError as e:
            char_errors.append(str(e))

        warnings = validate_persona_conflicts(record)

        is_ok = len(char_errors) == 0
        if is_ok:
            valid_count += 1
            if warnings:
                warning_count += 1
        else:
            error_count += 1

        results.append({
            "name": name,
            "valid": is_ok,
            "errors": char_errors,
            "warnings": warnings,
        })

    return {
        "total": total,
        "valid_count": valid_count,
        "warning_count": warning_count,
        "error_count": error_count,
        "results": results,
    }


def set_record(node, record: Any) -> Dict[str, Any]:
    """Validate and store a structured block on *node*; returns what was stored.

    An empty block removes the key, so a character can go back to prose-only.
    """
    cleaned = validate(record)
    props = getattr(node, "properties", None)
    if props is None:
        raise StructuredError("node has no properties")
    if cleaned:
        props[RECORD_KEY] = cleaned
    else:
        props.pop(RECORD_KEY, None)
    # task-865: always evict the legacy key on write so we do not carry two copies.
    props.pop(_LEGACY_KEY, None)
    return cleaned


def clear_record(node) -> None:
    """Drop the structured block. Prose-only authoring, restored."""
    if node is not None and getattr(node, "properties", None) is not None:
        node.properties.pop(RECORD_KEY, None)
        node.properties.pop(_LEGACY_KEY, None)


#: Dotted paths ``set_persona_field`` may write, as section -> allowed keys.
#: ``*`` means any declared field of the section; the whole record still
#: passes through :func:`validate`, so this is a guardrail, not the gate.
SETTABLE_SECTIONS = ("identity", "appearance", "personality", "capabilities", "narrative")


def set_persona_field(node, path: str, value: Any) -> Dict[str, Any]:
    """Write one dotted path inside the structured block (task-829 growth).

    ``appearance.eyes.color``, ``identity.age``,
    ``personality.speech_pattern.style`` - one handler for lenses,
    haircuts, tattoos and prosthetics, so content needs no bespoke
    effect each. Appending to a list uses ``add_persona_id`` instead;
    lists here are replaced whole. Marks compiled prose stale (see
    ``PROSE_STALE_KEY``); the explicit Compile refreshes it.
    """
    parts = [p for p in str(path or "").split(".") if p]
    if len(parts) < 2 or parts[0] not in SETTABLE_SECTIONS:
        raise StructuredError(
            f"persona path must be '<section>.<field>...', got {path!r}")
    record = get_record(node)
    cursor = record
    for part in parts[:-1]:
        child = cursor.get(part)
        if not isinstance(child, dict):
            child = {}
            cursor[part] = child
        cursor = child
    cursor[parts[-1]] = value
    stored = set_record(node, record)
    _mark_prose_stale(node)
    return stored


def add_persona_id(node, field: str, entry: str) -> bool:
    """Append *entry* to a personality id-list (kinks, fears, ...).

    Returns True when the list changed. Slug discipline enforced by
    :func:`validate`; fear/interest mirroring onto the Player is the
    effect handler's job (it owns the player), not this module's.
    """
    field = str(field or "").strip()
    if field not in ID_LIST_FIELDS:
        raise StructuredError(
            f"add_persona_id targets id-lists {sorted(ID_LIST_FIELDS)}, "
            f"got {field!r}")
    record = get_record(node)
    listed = ((record.get("personality") or {}).get(field)) or []
    entry = str(entry or "").strip()
    if not entry:
        raise StructuredError("add_persona_id needs a non-empty id")
    if entry in listed:
        return False
    record.setdefault("personality", {})[field] = list(listed) + [entry]
    set_record(node, record)
    _mark_prose_stale(node)
    return True


def remove_persona_id(node, field: str, entry: str) -> bool:
    """Remove *entry* from a personality id-list. Returns True on change."""
    field = str(field or "").strip()
    if field not in ID_LIST_FIELDS:
        raise StructuredError(
            f"remove_persona_id targets id-lists {sorted(ID_LIST_FIELDS)}, "
            f"got {field!r}")
    record = get_record(node)
    listed = ((record.get("personality") or {}).get(field)) or []
    if str(entry or "").strip() not in listed:
        return False
    record.setdefault("personality", {})[field] = [
        e for e in listed if e != str(entry).strip()]
    set_record(node, record)
    _mark_prose_stale(node)
    return True


def advance_age(node, years: float) -> float:
    """Bump authored ``identity.age`` by *years*; returns the new age.

    Author override until task-735's birth-tick clock lands, which derives
    elapsed age - this stays as the manual knob.
    """
    try:
        delta = float(years)
    except (TypeError, ValueError):
        raise StructuredError(f"advance_age needs a number, got {years!r}")
    record = get_record(node)
    current = (record.get("identity") or {}).get("age", 0)
    try:
        current = float(current)
    except (TypeError, ValueError):
        current = 0
    record.setdefault("identity", {})["age"] = current + delta
    set_record(node, record)
    _mark_prose_stale(node)
    return record["identity"]["age"]


#: Node property flagging compiled prose as older than the block. Set by
#: every mutator above, cleared when compile is applied - the Persona tab
#: reads it to show "recompile needed". A flag, not a copy: the block is
#: the state, the prose is the projection.
PROSE_STALE_KEY = "persona_prose_stale"


def _mark_prose_stale(node) -> None:
    props = getattr(node, "properties", None)
    if props is not None:
        props[PROSE_STALE_KEY] = True


def mark_prose_stale(node) -> None:
    """Flag compiled prose as older than the block (routes + handlers)."""
    _mark_prose_stale(node)


def prose_is_stale(node) -> bool:
    return bool((getattr(node, "properties", None) or {}).get(PROSE_STALE_KEY))


#: Every structured field names its consumer (task-828 acceptance), as
#: dotted-path -> hint. Served by GET /record so the Persona tab renders
#: each field with its reader beside it.
CONSUMER_HINTS: Dict[str, str] = {
    "identity.pronouns": "e.g. she/her, he/him, they/them; used for narration pronouns (tags fallback)",
    "identity.age": "numeric age in years (e.g. 16); used for lifecycle gate & compiled prose",
    "identity.gender": "gender identity label (e.g. female, non-binary); used for prompts + address",
    "identity.species": "species / kind (e.g. human, elf); used for compiled prose + prompts",
    "identity.occupation": "job, role, or status (e.g. Student, blacksmith); used for compiled prose + background behaviour",
    "identity.sexuality": "orientation label (e.g. straight, bisexual, ace); used for prompt voice + intimacy context",
    "identity.mbti": "4-letter type (e.g. INFP, INTJ); used for prompt voice",
    "identity.alignment": "moral alignment (e.g. Neutral Good); used for disposition reader + prompts",
    "identity.birthday": "birth date (dd.mm.yyyy); used for lifecycle birth_tick & earliest memory gate",
    "identity.potential_storylines": "storyline hooks/ideas; authoring notes (currently unwired)",
    "capabilities.skills": f"canonical skills ({', '.join(CANONICAL_SKILLS)}); projected to skills",
    "capabilities.languages": "structured language competence ({language, fluency, known_words, literate}); compiled onto Player.languages",
    "capabilities.domains": "structured domain competence and blind spots ({domain, level, notes, jargon_terms}); compiled onto Player.domains",
    "capabilities.weaknesses": "mechanical/situational liabilities (e.g. nearsighted, panic_freeze, peanut_allergy, clumsy); projected to traits",
    "narrative.media": "books, movies, bands, games (title, medium, when watched/read, opinion, familiarity); hydrated as lore memories & interest_tags",
    "appearance.overview": "1-2 sentence third-person summary of overall look/vibe; used for compiled prose",
    "appearance.height_cm": "number in cm (e.g. 160); converted to ft/in in compiled prose",
    "appearance.weight_kg": "number in kg (e.g. 48); used for compiled prose",
    "appearance.build": "body frame/build (e.g. petite, slender, stocky); used for compiled prose + equipment fit",
    "appearance.hair": "length, style, color (third-person phrases); used for compiled prose (grows/cut via effects)",
    "appearance.eyes": "eye color/look (e.g. bright blue); used for compiled prose (lenses via effects)",
    "appearance.skin": "skin tone/texture (e.g. pale porcelain); used for compiled prose",
    "appearance.face": "shape, distinguishing features, makeup (third-person); used for compiled prose",
    "appearance.body": "third-person descriptions per part (chest/waist/hips/legs/butt); used for compiled prose + equipment",
    "appearance.voice": "pitch, accent, mannerisms (how they sound/speak); used for prompt voice + compiled prose",
    "appearance.scent": "scent notes (e.g. black clove, rain, coffee); used for prompt voice + compiled prose",
    "appearance.style": "typical clothing, accessories, footwear; used for compiled prose + auto-dress context",
    "personality.likes": "comma-separated tags of things they enjoy (e.g. gummy_worms, vinyl); used for gifts + dialogue targeting",
    "personality.dislikes": "comma-separated tags of things they hate (e.g. small_talk, neon_lights); used for gifts + dialogue targeting",
    "personality.fears": "comma-separated tags of what scares them (e.g. abandonment, heights); used for fear engine (fear_tags)",
    "personality.interests": "comma-separated topic tags (e.g. horror_fx, astronomy); used for attention (interest_tags)",
    "personality.kinks": "comma-separated tags; used for affect (arousal)",
    "personality.turn_ons": "comma-separated tags; used for affect (arousal)",
    "personality.turn_offs": "comma-separated tags; used for affect (disgust, arousal down)",
    "personality.traumas": "comma-separated trigger tags (e.g. bullying, drowning); used for fear_tags + frightened condition",
    "personality.boundaries": "comma-separated limit tags; used as consent gate for intimacy prompts",
    "personality.traits": "comma-separated personality adjectives (e.g. anxious, loyal); used for personality prose & traits",
    "personality.aspirations": "comma-separated goal/ambition tags (e.g. fx_artist, escape_town); used for goals / plans projection",
    "personality.quirks": "comma-separated small mannerism tags (e.g. sleeve_tugging, nail_biting); used for prompt voice colour",
    "personality.habits": "comma-separated routine tags (e.g. late_night_sketching); used for prompt voice + background behaviour",
    "personality.speech_pattern": "voice style, dialect, and catchphrases; used for prompt voice + compiled prose",
    "personality.experience": "intimacy level, partners, hard/soft limits (or free text); used for intimacy prompt context",
    "narrative.biography": "origin, backstory, current situation (third-person); used for memories + prompt backstory",
    "narrative.secrets": "hidden truths or lies they keep; deepest_secret hydrates to internal_pressure secret memory (never compiled to prose)",
    "narrative.secrets.known_by": "DEPRECATED - shared secrets belong in the knower's own memories",
    "narrative.example_dialogues": "short sample lines showing how they talk; used for prompt voice",
    "narrative.role_in_town": "DEPRECATED (use identity.occupation and narrative.biography instead); no longer compiled to description",
    "narrative.arc": "where their story is heading or could turn; used for prompts + plans",
}


# ── ids → prose ──

def resolve_ids(ids, lookup) -> List[str]:
    """Map ids to display names via *lookup*, leaving unknown ids visible.

    An id with no resolvable name is kept as itself rather than dropped: a kink
    that quietly vanishes from a description is a bug report with no cause.
    """
    out = []
    for entry in ids or ():
        entry = str(entry)
        try:
            out.append(str(lookup(entry) or entry))
        except Exception:
            out.append(entry)
    return out


def render_prose(node, resolve=None) -> str:
    """Render the structured appearance as a third-person description.

    This is the *narrative* layer: written once, into ``base_description``,
    where the existing equipment/LLM description pipeline picks it up. It is
    deliberately plain and factual - the LLM's voice owns the prose, this only
    has to get the facts onto the page in a readable order.
    """
    return render_record_prose(get_record(node), resolve)


def render_record_prose(record: Dict[str, Any], resolve=None) -> str:
    """Render a validated block's appearance as prose (no node needed)."""
    looks = dict((record or {}).get("appearance") or {})
    if resolve:
        for group in ("hair", "eyes", "skin"):
            block = looks.get(group)
            if isinstance(block, dict):
                looks[group] = {k: resolve(v) for k, v in block.items()}

    clauses: List[str] = []
    if "height_cm" in looks:
        clauses.append(f"{_ft_in(looks['height_cm'])} tall")
    if "build" in looks:
        clauses.append(str(looks["build"]))
    if "weight_kg" in looks:
        clauses.append(f"weighing about {looks['weight_kg']:g} kg")

    hair = looks.get("hair") or {}
    hair_bits = [hair[k] for k in ("length", "style", "color") if hair.get(k)]
    if hair_bits:
        clauses.append(_join(hair_bits))
    elif "color" in hair:
        clauses.append(str(hair["color"]))

    eyes = looks.get("eyes") or {}
    if eyes.get("color"):
        clauses.append(f"{eyes['color']} eyes")

    skin = looks.get("skin") or {}
    if skin.get("tone"):
        clauses.append(f"{skin['tone']} skin")

    if looks.get("overview"):
        clauses.append(str(looks["overview"]).rstrip("."))
    face = looks.get("face") or {}
    face_bits = [face[k] for k in ("shape", "features", "makeup")
                 if face.get(k)]
    if face_bits:
        clauses.append(_join(face_bits))
    body = looks.get("body") or {}
    body_bits = [f"{k}: {body[k]}" for k in ("chest", "waist", "hips", "legs", "butt")
                 if body.get(k)]
    if body_bits:
        clauses.append("; ".join(body_bits))
    for mod in (body.get("modifications") or []):
        # task-852 P3: region-linked marks are stored as "area::text" in the
        # same modifications[] list. Strip the area for prose; keep legacy
        # unprefixed strings unchanged.
        text = str(mod)
        if "::" in text:
            area, _, text = text.partition("::")
            area_label = area.replace("_", " ").strip()
            if text.strip():
                clauses.append(
                    f"bearing {text.strip()} on the {area_label}"
                    if area_label else f"bearing {text.strip()}"
                )
        elif text.strip():
            clauses.append(f"bearing {text.strip()}")
    voice = looks.get("voice") or {}
    voice_bits = [voice[k] for k in ("pitch", "accent", "mannerisms")
                  if voice.get(k)]
    if voice_bits:
        clauses.append(f"speaking {_join(voice_bits)}")
    if looks.get("scent"):
        clauses.append(f"smelling of {looks['scent']}")
    style = looks.get("style") or {}
    kit = []
    for k in ("clothing", "accessories", "footwear"):
        v = style.get(k)
        if isinstance(v, str) and v:
            kit.append(v)
        elif isinstance(v, (list, tuple)):
            kit.extend([str(i) for i in v if str(i).strip()])
    if kit:
        clauses.append(f"dressed in {_join(kit)}")

    if not clauses:
        return ""
    return _join(clauses).capitalize() + "."


def compile_persona(node, resolve=None) -> Dict[str, Any]:
    """Project the structured block into the prose primitives the sim reads.

    Explicit and total: returns ``base_description`` (identity lead +
    appearance facts), ``description`` (base plus narrative situation when
    present), ``personality`` (traits/quirks/habits/speech prose), plus the
    ``interest_tags`` / ``fear_tags`` / ``traits`` projections. Callers
    decide what to write and never clobber hand prose without ``force`` -
    see the record routes. Pure: reads the node, writes nothing.
    """
    return compile_record(get_record(node), resolve)


def compile_record(record: Dict[str, Any], resolve=None) -> Dict[str, Any]:
    """Project a validated block (not necessarily stored) into primitives.

    The dry-run seam: the import flow and the Persona tab's live preview
    compile a candidate block without touching the node.
    """
    record = dict(record or {})
    is_valid, errors = validate_before_compile(record)
    if not is_valid:
        raise StructuredError("; ".join(errors))

    ident = record.get("identity") or {}
    pers = record.get("personality") or {}
    cap = record.get("capabilities") or {}
    narr = record.get("narrative") or {}

    lead_bits = []
    if ident.get("age") is not None:
        try:
            lead_bits.append(_apparent_age_bracket(float(ident["age"])))
        except (TypeError, ValueError):
            pass
    for key in ("species", "occupation"):
        if ident.get(key):
            lead_bits.append(str(ident[key]))
    lead = f"A {' '.join(lead_bits)}. " if lead_bits else ""
    body = render_record_prose(record, resolve)
    base_description = (lead + body).strip()

    extra = []
    bio = narr.get("biography") or {}
    if bio.get("current_situation"):
        extra.append(str(bio["current_situation"]).rstrip(".") + ".")
    description = (base_description + " " + " ".join(extra)).strip()

    prose_bits = []
    traits = list(pers.get("traits") or [])
    cap_skills = cap.get("skills") or []
    cap_weaknesses = [
        normalize_slug(w) or str(w).strip()
        for w in (cap.get("weaknesses") or [])
        if str(w).strip()
    ]
    all_traits = sorted(set(traits) | set(cap_weaknesses))

    projected_skills: Dict[str, int] = {}
    if isinstance(cap_skills, dict):
        for k, v in cap_skills.items():
            skill_name = _normalize_skill(k)
            if not skill_name:
                continue
            try:
                projected_skills[skill_name] = int(v)
            except (TypeError, ValueError):
                projected_skills[skill_name] = 1
    elif isinstance(cap_skills, (list, tuple, set)):
        for k in cap_skills:
            skill_name = _normalize_skill(k)
            if skill_name:
                projected_skills[skill_name] = 1
    if traits:
        prose_bits.append(_join(traits).capitalize() + ".")
    for key in ("quirks", "habits", "aspirations"):
        for entry in (pers.get(key) or []):
            prose_bits.append(str(entry).rstrip(".") + ".")
    speech = pers.get("speech_pattern") or {}
    if isinstance(speech, dict):
        style_val = str(speech.get("style", "") or "").strip().rstrip(".")
        dialect_val = str(speech.get("dialect", "") or "").strip().rstrip(".")
        catches = speech.get("catchphrases") or []
        if style_val or dialect_val or catches:
            if style_val and dialect_val:
                line = f"Speaks {style_val} ({dialect_val})"
            elif style_val:
                line = f"Speaks {style_val}"
            elif dialect_val:
                line = f"Speaks with a {dialect_val} dialect"
            else:
                line = "Speech"
            if catches:
                quoted = ", ".join(f'"{c}"' for c in catches)
                line += f", fond of {quoted}"
            prose_bits.append(line.rstrip(".") + ".")
    exp_val = pers.get("experience")
    if isinstance(exp_val, dict):
        exp_parts = []
        if exp_val.get("intimacy_level"):
            exp_parts.append(f"Intimacy experience: {exp_val['intimacy_level']}.")
        if exp_val.get("significant_partners"):
            exp_parts.append(f"Past partners: {_join(exp_val['significant_partners'])}.")
        if exp_val.get("hard_limits"):
            exp_parts.append(f"Hard limits: {', '.join(exp_val['hard_limits'])}.")
        if exp_val.get("soft_limits"):
            exp_parts.append(f"Soft limits: {', '.join(exp_val['soft_limits'])}.")
        if exp_parts:
            prose_bits.append(" ".join(exp_parts))
    elif exp_val:
        prose_bits.append(str(exp_val).rstrip(".") + ".")
    if ident.get("sexuality"):
        prose_bits.append(
            f"Orientation: {str(ident['sexuality']).rstrip('.')}.")
    if ident.get("mbti"):
        prose_bits.append(
            f"MBTI: {str(ident['mbti']).strip().rstrip('.')}.")
    if ident.get("alignment"):
        prose_bits.append(
            f"Alignment: {str(ident['alignment']).strip().rstrip('.')}.")
    dialogues = (narr.get("example_dialogues") or [])[:3]
    if dialogues:
        quoted = ", ".join(f'"{d}"' for d in dialogues)
        prose_bits.append(f"Example lines: {quoted}.")
    personality_prose = " ".join(prose_bits).strip()

    return {
        "base_description": base_description,
        "description": description,
        "personality": personality_prose,
        "interest_tags": sorted(set(pers.get("interests") or ())
                                | set(pers.get("likes") or ())
                                | {
                                    normalize_slug(m.get("title") if isinstance(m, dict) else m)
                                    for m in (narr.get("media") or [])
                                    if (m.get("title") if isinstance(m, dict) else m) and normalize_slug(m.get("title") if isinstance(m, dict) else m)
                                }),
        "fear_tags": sorted(set(pers.get("fears") or ())
                            | set(pers.get("traumas") or ())),
        "dislike_tags": sorted(set(pers.get("dislikes") or ())),
        "traits": all_traits,
        "skills": projected_skills,
        "languages": normalize_languages(cap.get("languages") or []),
        "domains": normalize_domains(cap.get("domains") or []),
    }


def _ft_in(centimetres: float) -> str:
    total_inches = centimetres / 2.54
    feet = int(total_inches // 12)
    inches = int(round(total_inches - feet * 12))
    if inches == 12:
        feet, inches = feet + 1, 0
    return f"{feet} foot {inches} inch" if inches else f"{feet} feet"


def _join(parts: List[str]) -> str:
    parts = [str(p) for p in parts if str(p).strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


# ── the mechanic ──

#: Kink id -> the affect axes a match moves. All positive: a kink pulls toward
#: arousal and, usually, toward liking whoever triggered it.
KINK_AXES: Dict[str, Dict[str, float]] = {
    "affectionate": {"aroused": 6.0, "happy": 2.0},
    "teasing": {"aroused": 8.0, "happy": 3.0},
    "boldness": {"aroused": 5.0},
    "dominance": {"aroused": 7.0},
    "submission": {"aroused": 7.0, "grateful": 2.0},
    "exhibitionism": {"aroused": 9.0},
    "voyeurism": {"aroused": 8.0},
}

#: Turn-off id -> the affect axes a match moves. Disgust, anger or fear *up*,
#: arousal *down*.
#:
#: Kept as a separate table rather than one table with a sign flipped. Negating a
#: shared table turns "disgust up, arousal down" into "disgust down, arousal up"
#: - the exact opposite of a turn-off - because the sign of an axis is semantic
#: here, not an arithmetic consequence of which list it came from.
TURN_OFF_AXES: Dict[str, Dict[str, float]] = {
    "cruelty": {"disgusted": 9.0, "angry": 4.0, "aroused": -6.0},
    "deception": {"disgusted": 7.0, "angry": 3.0, "aroused": -4.0},
    "coercion": {"disgusted": 10.0, "afraid": 5.0, "aroused": -8.0},
    "incompetence": {"disgusted": 4.0, "irritated": 5.0},
    "abuse": {"disgusted": 10.0, "sad": 5.0, "aroused": -7.0},
}

#: Every stimulus id the mechanic knows, for the schema and the tests.
AFFECT_AXES: Dict[str, Dict[str, float]] = {**KINK_AXES, **TURN_OFF_AXES}

#: What a kink or turn-off the tables do not cover still does. A kink nobody
#: wrote axes for is still a kink; a turn-off nobody wrote axes for still turns
#: something off.
KINK_FALLBACK: Dict[str, float] = {"aroused": 5.0}
TURN_OFF_FALLBACK: Dict[str, float] = {"disgusted": 5.0, "aroused": -3.0}


def affect_for_stimulus(node, stimulus_id: str) -> Dict[str, float]:
    """Affect deltas for *stimulus_id* against this character's record.

    The mechanic task-507 asks for: a kink raises arousal, a turn-off raises
    disgust and pushes arousal down. Returns ``{}`` for an unknown stimulus, a
    character with no structured record, or a character who is simply neutral
    about it - never a guess, so an unrelated stimulus cannot nudge a character.
    """
    record = get_record(node)
    if not record:
        return {}
    key = str(stimulus_id or "").strip()
    if not key:
        return {}
    listed = record.get("personality") or {}
    wants = set(listed.get("kinks") or ())
    refuses = set(listed.get("turn_offs") or ())
    deltas: Dict[str, float] = {}

    def _apply(axes: Dict[str, float]) -> None:
        for axis, magnitude in axes.items():
            deltas[axis] = deltas.get(axis, 0.0) + magnitude

    if key in wants:
        _apply(KINK_AXES.get(key, KINK_FALLBACK))
    if key in refuses:
        # A turn-off is defined against the same vocabulary, so an id that is
        # both is contradictory: refuse wins, because a character cannot be
        # simultaneously drawn to and repelled by the same thing in a way that
        # is worth modelling here.
        _apply(TURN_OFF_AXES.get(key, TURN_OFF_FALLBACK))
    return {axis: round(value, 2) for axis, value in deltas.items() if value}


def knows_personality_id(node, field: str, value: str) -> bool:
    """Whether *value* is in this character's *field* list (``likes`` etc)."""
    listed = (get_record(node).get("personality") or {}).get(str(field)) or ()
    return str(value) in set(listed)


def schema_for_llm() -> Dict[str, Any]:
    """The JSON schema of the whole structured block, for the LLM-fill flow.

    Task-507 wants the model handed the schema of all fields plus the character
    card. Returning it from one place means the prompt and the validator cannot
    disagree about what exists.
    """
    appearance_block: Dict[str, Any] = {}
    for field, (kind, subfields) in APPEARANCE_FIELDS.items():
        if kind == "group":
            appearance_block[field] = {
                "type": "object",
                "properties": {
                    sub: ({"type": "array", "items": {"type": "string"}}
                          if sub in APPEARANCE_LIST_SUBS
                          else {"type": "string",
                                "description": f"{field} {sub}"})
                    for sub in subfields
                },
            }
        elif kind == "number":
            appearance_block[field] = {"type": "number"}
        else:
            appearance_block[field] = {"type": "string"}

    personality_block: Dict[str, Any] = {}
    for field, mechanic in PERSONALITY_FIELDS.items():
        if field == "speech_pattern":
            personality_block[field] = {
                "type": "object",
                "description": f"ids of {mechanic}",
                "properties": {
                    "style": {"type": "string"},
                    "dialect": {"type": "string"},
                    "catchphrases": {"type": "array",
                                     "items": {"type": "string"}},
                },
            }
        elif field == "experience":
            personality_block[field] = {
                "oneOf": [
                    {"type": "string", "description": f"ids of {mechanic}"},
                    {
                        "type": "object",
                        "description": "structured intimacy experience and limits",
                        "properties": {
                            "intimacy_level": {"type": "string"},
                            "significant_partners": {"type": "array", "items": {"type": "string"}},
                            "hard_limits": {"type": "array", "items": {"type": "string"}},
                            "soft_limits": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                ]
            }
        elif field in PROSE_LIST_FIELDS:
            personality_block[field] = {
                "type": "array",
                "items": {"type": "string"},
                "description": f"ids of {mechanic}",
            }
        else:
            personality_block[field] = {
                "type": "array",
                "items": {"type": "string", "pattern": _ID_RE.pattern},
                "description": f"ids of {mechanic}",
            }
    identity_block: Dict[str, Any] = {}
    for field in IDENTITY_FIELDS:
        if field == "age":
            identity_block[field] = {"type": "number",
                                     "description": "age in years; integer"}
        elif field == "birthday":
            identity_block[field] = {
                "type": "string",
                "pattern": BIRTHDAY_CANONICAL_RE.pattern,
                "description": "birth date in dd.mm.yyyy format (e.g. 14.03.1998)",
            }
        elif field == "occupation":
            # No declared vocabulary: any string is fine.
            identity_block[field] = {"type": "string",
                                     "description": "job / role in town; free text"}
        else:
            voc = IDENTITY_SUGGESTIONS.get(field)
            vals = ", ".join(voc) if voc else "free text"
            identity_block[field] = {
                "type": "string",
                "description": f"{field}: {vals}",
            }
    capabilities_block: Dict[str, Any] = {
        "skills": {
            "type": "array",
            "items": {"type": "string", "enum": list(CANONICAL_SKILLS)},
            "description": f"canonical character skills: {', '.join(CANONICAL_SKILLS)}",
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "canonical language slug (e.g. common, english, elvish)"},
                    "fluency": {"type": "string", "enum": list(LANGUAGE_FLUENCY_LEVELS)},
                    "known_words": {"type": "array", "items": {"type": "string"}},
                    "literate": {"type": "boolean"},
                },
                "required": ["language", "fluency"],
            },
            "description": "known languages with fluency (native/fluent/conversational/broken/none), literacy, and exact known_words lexicon",
        },
        "domains": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "canonical domain slug (e.g. silicone_molding, law, computer_science, sports)"},
                    "level": {"type": "string", "enum": list(DOMAIN_COMPETENCE_LEVELS)},
                    "notes": {"type": "string", "description": "specific competence, blind-spot, or background note"},
                    "jargon_terms": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["domain", "level"],
            },
            "description": "domain knowledge and explicit blind spots (ignorant/novice/familiar/expert), notes, and specialist jargon_terms",
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "mechanical/situational liabilities and flaw traits (e.g. nearsighted, panic_freeze, peanut_allergy, clumsy)",
        },
    }
    narrative_block: Dict[str, Any] = {}
    for field, (kind, subfields) in NARRATIVE_FIELDS.items():
        if kind == "group":
            narrative_block[field] = {
                "type": "object",
                "properties": {
                    sub: ({"type": "array", "items": {"type": "string"}}
                          if sub in ("hidden_facts", "known_by")
                          else {"type": "string"})
                    for sub in subfields
                },
            }
        elif field == "media":
            narrative_block[field] = {
                "type": "array",
                "items": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "medium": {"type": "string"},
                                "opinion": {"type": "string"},
                                "familiarity": {"type": "string"},
                            },
                            "required": ["title"],
                        },
                    ]
                },
            }
        elif kind == "proselist":
            narrative_block[field] = {"type": "array",
                                      "items": {"type": "string"}}
        else:
            narrative_block[field] = {"type": "string"}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "identity": {
                "type": "object",
                "additionalProperties": False,
                "properties": identity_block,
            },
            "appearance": {
                "type": "object",
                "additionalProperties": False,
                "properties": appearance_block,
            },
            "personality": {
                "type": "object",
                "additionalProperties": False,
                "properties": personality_block,
            },
            "capabilities": {
                "type": "object",
                "additionalProperties": False,
                "properties": capabilities_block,
            },
            "narrative": {
                "type": "object",
                "additionalProperties": False,
                "properties": narrative_block,
            },
        },
    }
