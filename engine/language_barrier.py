"""Listener-side language comprehension barrier (task-967).

@module language_barrier
@contributes per-listener speech masking, inscription reading gate, speaker lang resolution
@docs docs/virtualWorld/AI & Narration/Narration System.md

Masks foreign speech and written inscriptions at the perception boundary before
prompt assembly so characters with partial (`known_words`) or zero (`none`)
competence only perceive recognized words, known names, and delivery cues
rather than unmasked plaintext.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from engine.character_appearance import normalize_languages, normalize_slug

_WORD_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*", re.UNICODE)
_FLUENT_LEVELS = frozenset({"native", "fluent"})


def _node_props(node: Any) -> Dict[str, Any]:
    if isinstance(node, dict):
        return node.get("properties") or {}
    return getattr(node, "properties", None) or {}


def get_player_languages(player: Any, graph: Any = None) -> list[Dict[str, Any]]:
    """Return normalized ``[{language, fluency, known_words, literate}]`` for *player*."""
    if player is None:
        return []

    raw_langs: Any = None
    appearance = getattr(player, "appearance", None)
    if isinstance(appearance, dict):
        caps = appearance.get("capabilities")
        if isinstance(caps, dict) and isinstance(caps.get("languages"), list):
            raw_langs = caps.get("languages")

    if raw_langs is None and isinstance(getattr(player, "languages", None), list):
        raw_langs = getattr(player, "languages")

    if raw_langs is None and graph is not None and hasattr(graph, "nodes"):
        pname = getattr(player, "name", "")
        if pname:
            node = graph.nodes.get(f"player_{pname}") or graph.nodes.get(pname)
            if node is not None:
                props = _node_props(node)
                node_app = props.get("appearance")
                if isinstance(node_app, dict) and isinstance((node_app.get("capabilities") or {}).get("languages"), list):
                    raw_langs = node_app["capabilities"]["languages"]
                elif isinstance(props.get("languages"), list):
                    raw_langs = props.get("languages")

    if not raw_langs:
        return []
    return normalize_languages(raw_langs)


def resolve_speaker_language(
    speaker: Any,
    explicit_lang: Optional[str] = None,
    graph: Any = None,
) -> str:
    """Resolve the normalized language slug for an utterance by *speaker*."""
    if explicit_lang and str(explicit_lang).strip():
        return normalize_slug(str(explicit_lang))

    if speaker is None:
        return ""

    active = getattr(speaker, "active_language", None)
    if isinstance(active, str) and active.strip():
        return normalize_slug(active)

    langs = get_player_languages(speaker, graph=graph)
    if not langs:
        return ""

    for target_fluency in ("native", "fluent"):
        for entry in langs:
            if entry.get("fluency") == target_fluency and entry.get("language"):
                return str(entry["language"])
    return str(langs[0].get("language") or "")


def listener_language_entry(
    listener: Any,
    lang: str,
    graph: Any = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Return ``(has_authored_languages, matching_entry)`` for *listener* and *lang*."""
    langs = get_player_languages(listener, graph=graph)
    if not langs:
        return False, None
    target = normalize_slug(lang)
    for entry in langs:
        if entry.get("language") == target:
            return True, entry
    return True, None


def extract_known_names_for_listener(
    listener: Any,
    extra_names: Optional[Iterable[str]] = None,
) -> Set[str]:
    """Collect proper names (self, met characters, known places) recognizable across languages."""
    names: Set[str] = set()
    if listener is not None:
        own = getattr(listener, "name", None)
        if isinstance(own, str) and own.strip():
            names.add(own.strip())
        rels = getattr(listener, "relationships", None)
        if isinstance(rels, dict):
            for other, rel in rels.items():
                if isinstance(rel, dict) and rel.get("first_sighting") is False and isinstance(other, str):
                    names.add(other.strip())
        places = getattr(listener, "known_places", None)
        if isinstance(places, (list, set, tuple)):
            for place in places:
                if isinstance(place, str) and place.strip():
                    names.add(place.strip())
    if extra_names:
        for name in extra_names:
            if isinstance(name, str) and name.strip():
                names.add(name.strip())
    return names


def _build_allowed_vocab(
    entry: Optional[Dict[str, Any]],
    known_names: Optional[Iterable[str]],
) -> Tuple[Set[str], Set[str]]:
    single_words: Set[str] = set()
    phrases: Set[str] = set()
    raw_items = list((entry or {}).get("known_words") or [])
    if known_names:
        raw_items.extend(known_names)
    for item in raw_items:
        norm = str(item or "").strip().lower()
        if not norm:
            continue
        if " " in norm:
            phrases.add(norm)
        else:
            for tok in _WORD_RE.findall(norm):
                single_words.add(tok.lower())
    return single_words, phrases


def mask_text_for_listener(
    text: str,
    lang: Optional[str],
    listener: Any,
    *,
    graph: Any = None,
    known_names: Optional[Iterable[str]] = None,
    for_reading: bool = False,
) -> Tuple[str, bool]:
    """Mask words in *text* outside *listener*'s competence in *lang*.

    Returns ``(output_text, was_masked)``.
    Legacy characters with no authored ``languages`` pass through unmasked.
    """
    if not text or not lang:
        return text, False

    has_langs, entry = listener_language_entry(listener, str(lang), graph=graph)
    if not has_langs:
        return text, False

    fluency = (entry or {}).get("fluency", "none")
    literate = (entry or {}).get("literate", True) is not False

    if for_reading and not literate:
        masked = _WORD_RE.sub("???", text)
        return masked, masked != text

    if fluency in _FLUENT_LEVELS:
        return text, False

    single_words, phrases = _build_allowed_vocab(entry, known_names)

    # Preserve multi-word known phrases verbatim before word-level masking.
    protected_spans: list[Tuple[int, int]] = []
    lower_text = text.lower()
    for phrase in phrases:
        start = 0
        while True:
            idx = lower_text.find(phrase, start)
            if idx == -1:
                break
            protected_spans.append((idx, idx + len(phrase)))
            start = idx + len(phrase)

    def _is_protected(start: int, end: int) -> bool:
        return any(s <= start and end <= e for s, e in protected_spans)

    def _replace(match: re.Match[str]) -> str:
        tok = match.group(0)
        if tok.isdigit() or _is_protected(match.start(), match.end()):
            return tok
        if tok.lower() in single_words:
            return tok
        return "???"

    masked = _WORD_RE.sub(_replace, text)
    return masked, True
