"""Associative multi-facet memory retrieval engine.

Provides cue extraction, multi-facet scoring across all 7 channels, open-question
tripwire matching, and three-lane retrieval for VirtualWorld, building on shared
constants and lifecycle checks from ``story_memory.core.retrieval``.

@module engine/memory_retrieval
@contributes retrieve_associative_memories, score_memory, extract_cues, is_active_memory, is_open_question_match, normalize_tokens
@docs docs/virtualWorld/memory_architecture.md
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from engine import memory_dynamics
from engine.vector_store import VectorStore, _cosine, _ensure_story_memory

_ensure_story_memory()

from story_memory.core.retrieval import (
    NEED_TAG_MAP,
    STOPWORDS,
    _mem_about,
    _mem_location_display,
    _mem_locations,
    _mem_seq,
    _mem_status,
    _mem_text,
    is_active_memory,
    normalize_tokens,
)

logger = logging.getLogger(__name__)

_PRONOUN_SPEAKERS = {
    "i", "you", "me", "he", "she", "they", "we", "it",
    "someone", "anyone", "nobody", "everyone", "somebody", "anybody",
}

_SPEECH_DIRECTED_RE = re.compile(
    r"^(?:\[[^\]]*\]\s*)*([A-Za-z][A-Za-z0-9_' -]{0,40}?)\s+"
    r"(?:said|says|whispered|murmured|asked|replied|shouted|yelled|snapped|muttered|spoke|answered)"
    r"\s+to\s+([A-Za-z][A-Za-z0-9_' -]{0,40}?)\s*[:,\"]",
    re.IGNORECASE,
)
_SPEECH_TOLD_RE = re.compile(
    r"^(?:\[[^\]]*\]\s*)*([A-Za-z][A-Za-z0-9_' -]{0,40}?)\s+"
    r"told\s+([A-Za-z][A-Za-z0-9_' -]{0,40}?)\s*[:,\"]",
    re.IGNORECASE,
)
_SPEECH_ACTION_RE = re.compile(
    r"^(?:\[[^\]]*\]\s*)*([A-Za-z][A-Za-z0-9_' -]{0,40}?)\s+"
    r"(?:said|says|whispered|murmured|asked|replied|shouted|yelled|snapped|muttered|spoke|answered)"
    r"\s*[:,\"]",
    re.IGNORECASE,
)
_SPEECH_COLON_QUOTE_RE = re.compile(
    r"^(?:\[[^\]]*\]\s*)*([A-Za-z][A-Za-z0-9_' -]{0,40}?)\s*:\s*[\"']",
    re.IGNORECASE,
)
_SPEECH_TRAILING_RE = re.compile(
    r"[\"']\s*,?\s*([A-Za-z][A-Za-z0-9_' -]{0,40}?)\s+"
    r"(?:said|says|whispered|told)(?:\s+(?:to\s+)?([A-Za-z][A-Za-z0-9_' -]{0,40}?))?[.!?]?$",
    re.IGNORECASE,
)

_EMOTION_ALIASES = {
    "affection": "affectionate",
    "grief": "sad",
}


def _collapse_ws(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _is_hidden_cue_dict(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    if item.get("hidden") or item.get("stealthed") or item.get("is_hidden"):
        return True
    if item.get("visible") is False:
        return True
    if str(item.get("current_state") or "").strip().lower() == "hidden":
        return True
    return False


def _cue_entry_value(item: Any) -> str:
    if isinstance(item, dict):
        if _is_hidden_cue_dict(item):
            return ""
        return str(item.get("id") or item.get("name") or item.get("label") or "").strip()
    return str(item or "").strip()


def _expand_prefixed_variants(prefix: str, rest: str) -> Tuple[Set[str], Set[str]]:
    rest_words = re.sub(r"[_\s]+", " ", rest).strip()
    rest_slug = re.sub(r"\s+", "_", rest_words)
    ids: Set[str] = set()
    names: Set[str] = set()
    if rest_slug:
        ids.add(f"{prefix}_{rest_slug}")
    if rest_words:
        ids.add(f"{prefix}_{rest_words}")
        names.add(rest_words)
    return ids, names


def _resolve_world_actor_variants(raw_actor: str, world: Any, ids: Set[str], names: Set[str]) -> None:
    """Resolve an actor already present in cues to its canonical world player/node IDs."""
    if world is None or not raw_actor:
        return
    want = _collapse_ws(raw_actor)
    players = getattr(world, "players", None) or {}
    for pname, pobj in players.items():
        pname_l = _collapse_ws(pname)
        pid_l = _collapse_ws(getattr(pobj, "id", ""))
        if want == pname_l or (pid_l and want == pid_l) or want == f"player_{pname_l.replace(' ', '_')}":
            if pname_l:
                names.add(pname_l)
                slug = pname_l.replace(" ", "_")
                ids.add(pname_l)
                ids.add(f"player_{slug}")
                ids.add(f"player_{pname_l}")
            if pid_l:
                ids.add(pid_l)
            try:
                node_id = world._player_node_id(pname)
                if node_id:
                    ids.add(_collapse_ws(node_id))
            except Exception:
                pass
            return

    graph = getattr(world, "graph", None)
    if graph is None:
        return
    nodes = getattr(graph, "nodes", None) or {}
    for nid, node in nodes.items():
        if getattr(node, "type", None) not in ("character", "player"):
            continue
        nid_l = _collapse_ws(nid)
        nname_l = _collapse_ws(getattr(node, "name", ""))
        if want in (nid_l, nname_l):
            if nid_l:
                ids.add(nid_l)
            if nname_l:
                names.add(nname_l)
                slug = nname_l.replace(" ", "_")
                ids.add(f"player_{slug}")
                ids.add(f"char_{slug}")
            return


def _add_actor_variants(
    raw_actors: Any,
    actor_ids: Set[str],
    actor_names: Set[str],
    world: Any = None,
) -> None:
    for raw in (raw_actors or ()):
        val = _cue_entry_value(raw)
        s = _collapse_ws(val)
        if not s:
            continue
        if s.startswith("player_") or s.startswith("char_"):
            prefix, rest = s.split("_", 1)
            actor_ids.add(s)
            p_ids, p_names = _expand_prefixed_variants(prefix, rest)
            actor_ids.update(p_ids)
            actor_names.update(p_names)
        else:
            words = re.sub(r"[_\s]+", " ", s).strip()
            slug = re.sub(r"\s+", "_", words)
            actor_names.add(words)
            actor_ids.add(s)
            actor_ids.add(words)
            if slug:
                actor_ids.add(slug)
                actor_ids.add(f"player_{slug}")
                actor_ids.add(f"char_{slug}")
            actor_ids.add(f"player_{words}")
            actor_ids.add(f"char_{words}")
        if world is not None:
            _resolve_world_actor_variants(val, world, actor_ids, actor_names)


def _add_item_variants(raw_items: Any, item_ids: Set[str], item_names: Set[str]) -> None:
    for raw in (raw_items or ()):
        val = _cue_entry_value(raw)
        s = _collapse_ws(val)
        if not s:
            continue
        if s.startswith("item_"):
            item_ids.add(s)
            _, rest = s.split("_", 1)
            p_ids, p_names = _expand_prefixed_variants("item", rest)
            item_ids.update(p_ids)
            item_names.update(p_names)
        else:
            words = re.sub(r"[_\s]+", " ", s).strip()
            slug = re.sub(r"\s+", "_", words)
            item_names.add(words)
            item_ids.add(s)
            item_ids.add(words)
            if slug:
                item_ids.add(f"item_{slug}")
            item_ids.add(f"item_{words}")


def _expand_entity_ids(raw_eids: Iterable[str]) -> Set[str]:
    """Expand stored entity IDs to bridge space-vs-underscore mismatches."""
    out: Set[str] = set()
    for raw in raw_eids:
        s = _collapse_ws(raw)
        if not s:
            continue
        out.add(s)
        for prefix in ("player_", "char_", "item_", "area_", "loc_"):
            if s.startswith(prefix):
                rest = s[len(prefix):]
                rest_words = re.sub(r"[_\s]+", " ", rest).strip()
                rest_slug = re.sub(r"\s+", "_", rest_words)
                if rest_slug:
                    out.add(f"{prefix}{rest_slug}")
                if rest_words:
                    out.add(f"{prefix}{rest_words}")
                break
    return out


def _mem_entity_ids(m: Dict[str, Any]) -> Set[str]:
    eids = m.get("entity_ids")
    if eids is None and isinstance(m.get("who_what"), dict):
        eids = m["who_what"].get("entity_ids")
    return _expand_entity_ids(str(e) for e in (eids or ()) if e)


def _expand_area_keys(raw_value: Any, name: Optional[str] = None) -> Set[str]:
    """Return exact canonical, slug, and display forms for an area (never substrings)."""
    out: Set[str] = set()
    for candidate in (raw_value, name):
        s = _collapse_ws(candidate)
        if not s:
            continue
        out.add(s)
        if s.startswith("area_"):
            base = re.sub(r"[_\s]+", " ", s[5:]).strip()
            if base:
                out.add(base)
                out.add(f"area_{base.replace(' ', '_')}")
                out.add(f"area_{base}")
        elif s.startswith("loc_"):
            base = re.sub(r"[_\s]+", " ", s[4:]).strip()
            if base:
                out.add(base)
                out.add(f"loc_{base.replace(' ', '_')}")
                out.add(f"loc_{base}")
        else:
            slug = re.sub(r"\s+", "_", s)
            out.add(f"area_{slug}")
            out.add(f"loc_{slug}")
    return out


def _resolve_area_node(graph: Any, area_ref: str) -> Any:
    """Resolve an area ID or display name against graph without duplicating logic."""
    if graph is None or not area_ref:
        return None
    try:
        from engine.fog import resolve_known_area

        node = resolve_known_area(graph, area_ref)
        if node is not None:
            return node
    except Exception:
        pass
    want = _collapse_ws(area_ref)
    nodes = getattr(graph, "nodes", None) or {}
    for nid, node in nodes.items():
        if getattr(node, "type", None) != "area":
            continue
        nid_l = _collapse_ws(nid)
        nname_l = _collapse_ws(getattr(node, "name", ""))
        if want == nid_l or want == nname_l or want == f"area_{nname_l.replace(' ', '_')}":
            return node
    return None


def _way_is_visible(way_node: Any, area_name: str, direction: str, world: Any, player: Any) -> bool:
    props = getattr(way_node, "properties", None) or {}
    if props.get("hidden") is True:
        return False
    state = str(props.get("current_state") or "").strip().lower()
    if state != "hidden":
        return True
    if player is None:
        return False
    pm = getattr(world, "player_manager", None) if world is not None else None
    pname = getattr(player, "name", "") or ""
    try:
        from engine.room_perception import way_visible_to

        if pm is not None:
            return bool(way_visible_to(player, pm, pname, way_node, area_name, direction))
    except Exception:
        pass
    known = {str(k) for k in (getattr(player, "known", None) or ())}
    if getattr(way_node, "id", "") in known:
        return True
    discovered = getattr(player, "discovered_exits", None) or set()
    return (str(area_name), str(direction)) in discovered


def _collect_adjacent_areas(
    world: Any,
    area_node: Any,
    area_id_lower: str,
    player: Any = None,
) -> Set[str]:
    """Discover adjacent area forms via 2-hop EDGE_CONNECTION (area -> way -> area)."""
    adjacent: Set[str] = set()
    graph = getattr(world, "graph", None) if world is not None else None
    if graph is None or not callable(getattr(graph, "get_edges_for_source", None)):
        return adjacent
    start_id = str(getattr(area_node, "id", "") or area_id_lower)
    start_id_lower = _collapse_ws(start_id)
    area_name = str(getattr(area_node, "name", "") or start_id)
    if not start_id:
        return adjacent
    try:
        from graph import EDGE_CONNECTION

        for edge in graph.get_edges_for_source(start_id, EDGE_CONNECTION):
            mid = graph.get_node(edge.target)
            if mid is None:
                continue
            mid_type = getattr(mid, "type", None)
            if mid_type == "way":
                direction = str((getattr(edge, "properties", None) or {}).get("direction", "") or "")
                if not _way_is_visible(mid, area_name, direction, world, player):
                    continue
                for inner in graph.get_edges_for_source(mid.id, EDGE_CONNECTION):
                    dest = graph.get_node(inner.target)
                    if dest is None or getattr(dest, "type", None) != "area":
                        continue
                    if _collapse_ws(dest.id) == start_id_lower:
                        continue
                    adjacent.update(_expand_area_keys(dest.id, getattr(dest, "name", None)))
            elif mid_type == "area" and _collapse_ws(mid.id) != start_id_lower:
                adjacent.update(_expand_area_keys(mid.id, getattr(mid, "name", None)))
    except Exception:
        pass
    return adjacent


def _parse_dialogue_cues(data: Dict[str, Any], world: Any = None) -> Dict[str, Any]:
    """Extract attributed dialogue bindings and unattributed tokens from cues/payload."""
    dialogue_raw = list(data.get("dialogue") or ())
    if data.get("stimulus") is not None:
        stim = data.get("stimulus")
        if stim not in dialogue_raw and str(stim).strip():
            dialogue_raw.append(stim)

    attributed: List[Dict[str, Any]] = []
    attributed_tokens: Set[str] = set()
    unattributed_tokens: Set[str] = set()
    dialogue_tokens: Set[str] = set()
    speaker_ids_all: Set[str] = set()
    speaker_names_all: Set[str] = set()
    target_ids_all: Set[str] = set()
    target_names_all: Set[str] = set()
    dialogue_speakers: Set[str] = set()
    dialogue_targets: Set[str] = set()

    for item in dialogue_raw:
        if isinstance(item, dict):
            raw_speaker = str(
                item.get("speaker") or item.get("from") or item.get("actor") or ""
            ).strip()
            raw_target = str(
                item.get("target")
                or item.get("addressed_to")
                or item.get("whisper_target")
                or item.get("to")
                or ""
            ).strip()
            raw_text = str(
                item.get("text")
                or item.get("line")
                or item.get("speech")
                or item.get("utterance")
                or ""
            ).strip()
            line_tokens = normalize_tokens(raw_text) - STOPWORDS
            dialogue_tokens.update(line_tokens)

            spk_ids: Set[str] = set()
            spk_names: Set[str] = set()
            tgt_ids: Set[str] = set()
            tgt_names: Set[str] = set()

            if raw_speaker and _collapse_ws(raw_speaker) not in _PRONOUN_SPEAKERS:
                _add_actor_variants([raw_speaker], spk_ids, spk_names, world=world)
                speaker_ids_all.update(spk_ids)
                speaker_names_all.update(spk_names)
                dialogue_speakers.add(_collapse_ws(raw_speaker))

            if raw_target and _collapse_ws(raw_target) not in _PRONOUN_SPEAKERS:
                _add_actor_variants([raw_target], tgt_ids, tgt_names, world=world)
                target_ids_all.update(tgt_ids)
                target_names_all.update(tgt_names)
                dialogue_targets.add(_collapse_ws(raw_target))

            if spk_ids or spk_names:
                attributed_tokens.update(line_tokens)
                attributed.append({
                    "speaker": raw_speaker,
                    "target": raw_target,
                    "speaker_ids": spk_ids,
                    "speaker_names": spk_names,
                    "target_ids": tgt_ids,
                    "target_names": tgt_names,
                    "tokens": line_tokens,
                })
            else:
                unattributed_tokens.update(line_tokens)
        else:
            tokens = normalize_tokens(item) - STOPWORDS
            dialogue_tokens.update(tokens)
            unattributed_tokens.update(tokens)

    if data.get("last_thought"):
        lt_tokens = normalize_tokens(data["last_thought"]) - STOPWORDS
        dialogue_tokens.update(lt_tokens)
        unattributed_tokens.update(lt_tokens)

    if data.get("query"):
        q_tokens = normalize_tokens(data["query"]) - STOPWORDS
        dialogue_tokens.update(q_tokens)
        unattributed_tokens.update(q_tokens - attributed_tokens)

    return {
        "attributed_dialogue": attributed,
        "unattributed_dialogue_tokens": unattributed_tokens,
        "dialogue_tokens": dialogue_tokens,
        "speaker_ids": speaker_ids_all,
        "speaker_names": speaker_names_all,
        "target_ids": target_ids_all,
        "target_names": target_names_all,
        "dialogue_speakers": dialogue_speakers,
        "dialogue_targets": dialogue_targets,
    }


def _mem_dialogue_attribution(memory: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """Extract (speaker_ids, speaker_names, target_ids, target_names) from a memory."""
    spk_raw: List[str] = []
    tgt_raw: List[str] = []

    sources: List[Dict[str, Any]] = [memory]
    if isinstance(memory.get("data"), dict):
        sources.append(memory["data"])
    if isinstance(memory.get("who_what"), dict):
        sources.append(memory["who_what"])

    for src in sources:
        for k in ("speaker", "from", "uttered_by"):
            v = src.get(k)
            if v:
                spk_raw.append(str(v).strip())
        for k in ("target", "addressed_to", "whisper_target", "to"):
            v = src.get(k)
            if v:
                tgt_raw.append(str(v).strip())

    for tag in (memory.get("tags") or ()):
        ts = str(tag or "").strip()
        tl = ts.lower()
        if tl.startswith("speaker:") and len(ts) > 8:
            spk_raw.append(ts[8:].strip())
        elif tl.startswith("target:") and len(ts) > 7:
            tgt_raw.append(ts[7:].strip())
        elif tl.startswith("addressed_to:") and len(ts) > 13:
            tgt_raw.append(ts[13:].strip())
        elif tl.startswith("to:") and len(ts) > 3:
            tgt_raw.append(ts[3:].strip())

    text = _mem_text(memory).strip()
    if text and (not spk_raw or not tgt_raw):
        m_dir = _SPEECH_DIRECTED_RE.match(text) or _SPEECH_TOLD_RE.match(text)
        if m_dir:
            s_cand, t_cand = m_dir.group(1).strip(), m_dir.group(2).strip()
            if not spk_raw and _collapse_ws(s_cand) not in _PRONOUN_SPEAKERS:
                spk_raw.append(s_cand)
            if not tgt_raw and _collapse_ws(t_cand) not in _PRONOUN_SPEAKERS:
                tgt_raw.append(t_cand)
        else:
            m_action = _SPEECH_ACTION_RE.match(text) or _SPEECH_COLON_QUOTE_RE.match(text)
            if m_action and not spk_raw:
                s_cand = m_action.group(1).strip()
                if _collapse_ws(s_cand) not in _PRONOUN_SPEAKERS:
                    spk_raw.append(s_cand)
            elif not m_action:
                m_trail = _SPEECH_TRAILING_RE.search(text)
                if m_trail:
                    s_cand = m_trail.group(1).strip()
                    if not spk_raw and _collapse_ws(s_cand) not in _PRONOUN_SPEAKERS:
                        spk_raw.append(s_cand)
                    if m_trail.group(2) and not tgt_raw:
                        t_cand = m_trail.group(2).strip()
                        if _collapse_ws(t_cand) not in _PRONOUN_SPEAKERS:
                            tgt_raw.append(t_cand)

    mem_eids = _mem_entity_ids(memory)
    if spk_raw:
        # Link short parsed first names (e.g. "Jake") to full entity IDs ("player_jake_halloway")
        for s_item in list(spk_raw):
            slug = _collapse_ws(s_item).replace(" ", "_")
            if not slug:
                continue
            for eid in mem_eids:
                if eid.startswith(f"player_{slug}_") or eid.startswith(f"char_{slug}_"):
                    spk_raw.append(eid)

    if not spk_raw and str(memory.get("type") or "").strip().lower() == "speech":
        actor_eids = [
            e for e in mem_eids
            if e.startswith("player_") or e.startswith("char_")
        ]
        # Only assume speaker from entity_ids when there is a single unambiguous actor
        unique_slugs = {e.split("_", 1)[1].replace(" ", "_") for e in actor_eids if "_" in e}
        if len(unique_slugs) == 1 and actor_eids:
            spk_raw.append(actor_eids[0])

    spk_ids: Set[str] = set()
    spk_names: Set[str] = set()
    tgt_ids: Set[str] = set()
    tgt_names: Set[str] = set()
    _add_actor_variants(spk_raw, spk_ids, spk_names)
    _add_actor_variants(tgt_raw, tgt_ids, tgt_names)
    return spk_ids, spk_names, tgt_ids, tgt_names


def _canonical_emotion(label: Any) -> Tuple[str, Optional[str], Optional[str]]:
    raw = _collapse_ws(label)
    if not raw or raw == "neutral":
        return "", None, None
    raw = _EMOTION_ALIASES.get(raw, raw)
    dim: Optional[str] = None
    axis: Optional[str] = None
    try:
        from engine import emotion as _emo

        dim = _emo.resolve_label(raw)
        if dim:
            axis = _emo.AXES.get(dim)
        elif raw in _emo.AXES:
            dim = raw
            axis = _emo.AXES[raw]
    except Exception:
        dim = raw
    return raw, dim, axis


def _normalize_cue_intensity(raw_val: Any, default: float = 5.0) -> float:
    if raw_val is None:
        return default
    try:
        val = float(raw_val)
    except (TypeError, ValueError):
        return default
    if val <= 0.0:
        return 0.0
    if val <= 1.0:
        return round(val * 10.0, 4)
    if val <= 10.0:
        return val
    return min(10.0, round(val / 10.0, 4))


def _is_0_100_emotion_map(raw_map: Dict[str, Any]) -> bool:
    numeric = [
        float(v) for v in raw_map.values()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    return bool(numeric) and max(numeric) > 10.0


def _extract_emotion_cues(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract primary emotion, multi-dimensional affect vector (0-10), and targets."""
    raw_emo = data.get("emotion")
    primary_label = ""
    primary_intensity = 5.0

    if isinstance(raw_emo, dict):
        primary_label = _collapse_ws(
            raw_emo.get("current") or raw_emo.get("label") or raw_emo.get("emotion") or ""
        )
        raw_int = raw_emo.get("intensity")
        if raw_int is not None:
            primary_intensity = _normalize_cue_intensity(raw_int, default=5.0)
        elif data.get("emotion_intensity") is not None:
            primary_intensity = _normalize_cue_intensity(data.get("emotion_intensity"), default=5.0)
    else:
        primary_label = _collapse_ws(raw_emo or data.get("current_emotion") or "")
        if data.get("emotion_intensity") is not None:
            primary_intensity = _normalize_cue_intensity(data.get("emotion_intensity"), default=5.0)

    if primary_label == "neutral":
        primary_label = ""

    emotion_vector: Dict[str, float] = {}
    emotion_targets: List[Dict[str, str]] = []

    def _add_dim(lbl: Any, strength: float, who: str = "", why: str = "") -> None:
        raw, dim, _ = _canonical_emotion(lbl)
        if not raw or strength <= 0.0:
            return
        key = dim or raw
        emotion_vector[key] = max(emotion_vector.get(key, 0.0), min(10.0, strength))
        if raw != key:
            emotion_vector[raw] = max(emotion_vector.get(raw, 0.0), min(10.0, strength))
        if who or why:
            emotion_targets.append({
                "dim": key,
                "raw": raw,
                "who": _collapse_ws(who),
                "why": _collapse_ws(why),
            })

    if primary_label and primary_intensity > 0.0:
        _add_dim(primary_label, primary_intensity)

    raw_emos = data.get("emotions")
    if isinstance(raw_emos, dict):
        if isinstance(raw_emos.get("data"), dict):
            who = str(raw_emos.get("who") or "")
            why = str(raw_emos.get("why") or "")
            for k, v in raw_emos["data"].items():
                try:
                    num = float(v)
                except (TypeError, ValueError):
                    continue
                if num > 0:
                    _add_dim(k, min(10.0, num * 2.0), who=who, why=why)
        elif _is_0_100_emotion_map(raw_emos):
            try:
                from engine import emotion as _emo

                raised = _emo.raised_axes(raw_emos)
            except Exception:
                raised = {
                    k: float(v) for k, v in raw_emos.items()
                    if isinstance(v, (int, float)) and float(v) > 20.0
                }
            for k, over in raised.items():
                norm = min(10.0, 2.0 + (float(over) / 8.0))
                _add_dim(k, norm)
        else:
            numeric_vals = [
                float(v) for v in raw_emos.values()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            unit_scale = bool(numeric_vals) and max(numeric_vals) <= 1.0
            for k, v in raw_emos.items():
                if isinstance(v, bool):
                    continue
                try:
                    num = float(v)
                except (TypeError, ValueError):
                    continue
                if num <= 0.0:
                    continue
                strength = (num * 10.0) if unit_scale else min(10.0, num)
                _add_dim(k, strength)
    elif isinstance(raw_emos, (list, tuple)):
        for item in raw_emos:
            if isinstance(item, str):
                _add_dim(item, primary_intensity if primary_label else 5.0)
            elif isinstance(item, dict):
                lbl = item.get("label") or item.get("dimension") or item.get("emotion") or ""
                strength = _normalize_cue_intensity(item.get("intensity", item.get("value")), default=5.0)
                _add_dim(
                    lbl,
                    strength,
                    who=str(item.get("who") or item.get("target") or ""),
                    why=str(item.get("why") or ""),
                )

    for tgt in (data.get("emotion_targets") or ()):
        if isinstance(tgt, dict):
            emotion_targets.append({
                "dim": _canonical_emotion(tgt.get("label") or tgt.get("dimension") or "")[1] or "",
                "raw": _collapse_ws(tgt.get("label") or tgt.get("dimension") or ""),
                "who": _collapse_ws(tgt.get("who") or tgt.get("target") or ""),
                "why": _collapse_ws(tgt.get("why") or ""),
            })
        elif isinstance(tgt, str) and tgt.strip():
            emotion_targets.append({"dim": "", "raw": "", "who": _collapse_ws(tgt), "why": ""})

    if data.get("emotion_who"):
        emotion_targets.append({
            "dim": "",
            "raw": "",
            "who": _collapse_ws(data["emotion_who"]),
            "why": _collapse_ws(data.get("emotion_why") or ""),
        })

    if not primary_label and emotion_vector:
        best_k, best_v = max(emotion_vector.items(), key=lambda kv: kv[1])
        primary_label = best_k
        primary_intensity = best_v

    return {
        "emotion": primary_label,
        "emotion_intensity": primary_intensity if primary_label else 0.0,
        "emotion_vector": emotion_vector,
        "emotion_targets": emotion_targets,
    }


def _mem_emotion_entries(memory: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect normalized affect entries (label, dim, axis, intensity, who, why) from a memory."""
    entries: List[Dict[str, Any]] = []

    def _push(label: Any, intensity: float = 5.0, who: str = "", why: str = "") -> None:
        raw, dim, axis = _canonical_emotion(label)
        if not raw:
            return
        entries.append({
            "raw": raw,
            "dim": dim,
            "axis": axis,
            "intensity": intensity,
            "who": _collapse_ws(who),
            "why": _collapse_ws(why),
        })

    emo = memory.get("emotion")
    if isinstance(emo, dict):
        lbl = emo.get("current") or emo.get("label") or emo.get("emotion")
        _push(lbl, _normalize_cue_intensity(emo.get("intensity"), default=5.0),
              who=str(emo.get("who") or ""), why=str(emo.get("why") or ""))
    elif isinstance(emo, str) and emo.strip():
        _push(emo, 5.0)

    for me in (memory.get("memory_emotions") or ()):
        if isinstance(me, dict):
            lbl = me.get("label") or me.get("dimension") or me.get("emotion")
            _push(lbl, _normalize_cue_intensity(me.get("intensity"), default=5.0),
                  who=str(me.get("who") or ""), why=str(me.get("why") or ""))
        elif isinstance(me, str):
            _push(me, 5.0)

    raw_emos = memory.get("emotions")
    if isinstance(raw_emos, list):
        for me in raw_emos:
            if isinstance(me, dict):
                lbl = me.get("label") or me.get("dimension") or me.get("emotion")
                _push(lbl, _normalize_cue_intensity(me.get("intensity"), default=5.0),
                      who=str(me.get("who") or ""), why=str(me.get("why") or ""))
            elif isinstance(me, str):
                _push(me, 5.0)
    elif isinstance(raw_emos, dict):
        if isinstance(raw_emos.get("data"), dict):
            who = str(raw_emos.get("who") or "")
            why = str(raw_emos.get("why") or "")
            for k, v in raw_emos["data"].items():
                try:
                    num = float(v)
                except (TypeError, ValueError):
                    continue
                if num > 0:
                    _push(k, min(10.0, num * 2.0), who=who, why=why)
        else:
            for k, v in raw_emos.items():
                try:
                    num = float(v)
                except (TypeError, ValueError):
                    continue
                if num > 0:
                    _push(k, _normalize_cue_intensity(num, default=5.0))

    for rel in (memory.get("relationship_deltas") or ()):
        if isinstance(rel, dict) and isinstance(rel.get("data"), dict):
            who = str(rel.get("who") or "")
            why = str(rel.get("why") or "")
            for k, v in rel["data"].items():
                try:
                    num = float(v)
                except (TypeError, ValueError):
                    continue
                if num > 0:
                    _push(k, min(10.0, num * 2.0), who=who, why=why)

    for tag in (memory.get("tags") or ()):
        ts = _collapse_ws(tag)
        if not ts:
            continue
        if ts.startswith("emotion:"):
            _push(ts[8:], 5.0)
        else:
            _, dim, _ = _canonical_emotion(ts)
            if dim:
                _push(ts, 5.0)

    return entries


def _normalize_semantic_scores(raw_sem: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if not isinstance(raw_sem, dict):
        return out
    for k, v in raw_sem.items():
        try:
            score = float(v)
        except (TypeError, ValueError):
            continue
        key = str(k).strip()
        if not key:
            continue
        out[key] = max(out.get(key, float("-inf")), score)
        if "::" in key:
            _, _, mem_id = key.partition("::")
            if mem_id:
                out[mem_id] = max(out.get(mem_id, float("-inf")), score)
    return out


def extract_cues(data: Dict[str, Any], world: Any = None, player: Any = None) -> Dict[str, Any]:
    """Assemble structured situation cues from request payload and optional world context."""
    if isinstance(data.get("cues"), dict):
        data = {**data, **data["cues"]}

    actor_ids: Set[str] = set()
    actor_names: Set[str] = set()
    item_ids: Set[str] = set()
    item_names: Set[str] = set()
    needs: Set[str] = set()

    _add_actor_variants(data.get("actors"), actor_ids, actor_names, world=world)
    _add_item_variants(data.get("items"), item_ids, item_names)
    _add_item_variants(data.get("inventory"), item_ids, item_names)

    dialogue_info = _parse_dialogue_cues(data, world=world)
    actor_ids.update(dialogue_info["speaker_ids"])
    actor_names.update(dialogue_info["speaker_names"])

    # Add dialogue target actors unless target is the retrieving character themselves
    self_names: Set[str] = set()
    if player is not None:
        if getattr(player, "name", None):
            self_names.add(_collapse_ws(player.name))
        if getattr(player, "id", None):
            self_names.add(_collapse_ws(player.id))
    for k in ("self_name", "player_name", "character"):
        if data.get(k):
            self_names.add(_collapse_ws(data[k]))
    for tgt_name in dialogue_info["target_names"]:
        if tgt_name not in self_names:
            _add_actor_variants([tgt_name], actor_ids, actor_names, world=world)
    for tgt_id in dialogue_info["target_ids"]:
        stripped = tgt_id.split("_", 1)[1].replace("_", " ") if "_" in tgt_id else tgt_id
        if tgt_id not in self_names and stripped not in self_names:
            actor_ids.add(tgt_id)

    for n in (data.get("needs") or ()):
        ns = _collapse_ws(n)
        if ns:
            needs.add(ns if ns.startswith("need:") else f"need:{ns}")

    for eid in (data.get("entities") or ()):
        s = _collapse_ws(eid)
        if not s:
            continue
        if s.startswith("item_"):
            _add_item_variants([eid], item_ids, item_names)
        else:
            _add_actor_variants([eid], actor_ids, actor_names, world=world)

    emotion_info = _extract_emotion_cues(data)

    raw_area = str(data.get("current_area_id") or data.get("area_id") or "").strip()
    if not raw_area and player is not None:
        raw_area = str(getattr(player, "current_area", "") or "").strip()

    area_node = _resolve_area_node(getattr(world, "graph", None), raw_area) if world is not None else None
    area_id = _collapse_ws(getattr(area_node, "id", None) or raw_area)
    area_forms = _expand_area_keys(
        getattr(area_node, "id", None) or raw_area,
        getattr(area_node, "name", None),
    )

    adjacent_area_ids: Set[str] = set()
    for adj in (data.get("adjacent_areas") or data.get("adjacent_area_ids") or ()):
        adj_str = str(adj or "").strip()
        if not adj_str:
            continue
        adj_node = _resolve_area_node(getattr(world, "graph", None), adj_str) if world is not None else None
        adjacent_area_ids.update(
            _expand_area_keys(
                getattr(adj_node, "id", None) or adj_str,
                getattr(adj_node, "name", None),
            )
        )

    if world is not None and area_id:
        adjacent_area_ids.update(_collect_adjacent_areas(world, area_node, area_id, player=player))

    adjacent_area_ids -= area_forms

    semantic_scores = _normalize_semantic_scores(data.get("semantic_scores"))
    query_vector = data.get("query_vector")
    if not isinstance(query_vector, (list, tuple)):
        query_vector = None

    interest_tags = {_collapse_ws(t) for t in (data.get("interest_tags") or ()) if t}
    fear_tags = {_collapse_ws(t) for t in (data.get("fear_tags") or ()) if t}
    dislike_tags = {_collapse_ws(t) for t in (data.get("dislike_tags") or ()) if t}

    return {
        "actor_ids": actor_ids,
        "actor_names": actor_names,
        "item_ids": item_ids,
        "item_names": item_names,
        "dialogue_tokens": dialogue_info["dialogue_tokens"],
        "attributed_dialogue": dialogue_info["attributed_dialogue"],
        "unattributed_dialogue_tokens": dialogue_info["unattributed_dialogue_tokens"],
        "dialogue_speakers": dialogue_info["dialogue_speakers"],
        "dialogue_targets": dialogue_info["dialogue_targets"],
        "needs": needs,
        "emotion": emotion_info["emotion"],
        "emotion_intensity": emotion_info["emotion_intensity"],
        "emotion_vector": emotion_info["emotion_vector"],
        "emotion_targets": emotion_info["emotion_targets"],
        "area_id": area_id,
        "area_forms": area_forms,
        "adjacent_area_ids": adjacent_area_ids,
        "semantic_scores": semantic_scores,
        "query_vector": list(query_vector) if query_vector else None,
        "raw_query": str(data.get("query") or "").strip(),
        "interest_tags": interest_tags,
        "fear_tags": fear_tags,
        "dislike_tags": dislike_tags,
    }


def _match_emotion_channel(
    memory: Dict[str, Any],
    cues: Dict[str, Any],
    actor_ids: Set[str],
    actor_names: Set[str],
) -> Tuple[float, str, List[str]]:
    """Score Channel 4 emotional congruency across multi-dimensional & target-bound affect."""
    if "emotion_vector" in cues:
        cue_vec: Dict[str, float] = dict(cues.get("emotion_vector") or {})
        cue_targets: List[Dict[str, str]] = list(cues.get("emotion_targets") or ())
    else:
        parsed = _extract_emotion_cues(cues)
        cue_vec = parsed["emotion_vector"]
        cue_targets = parsed["emotion_targets"]

    if not cue_vec:
        return 0.0, "", []

    mem_entries = _mem_emotion_entries(memory)
    if not mem_entries:
        return 0.0, "", []

    # Collapse cue_vec aliases pointing to the same canonical dimension/raw key
    # while keeping highest intensity per canonical emotion key.
    canonical_cues: Dict[str, Tuple[str, Optional[str], Optional[str], float]] = {}
    for lbl, strength in cue_vec.items():
        raw, dim, axis = _canonical_emotion(lbl)
        if not raw or strength <= 0.0:
            continue
        canon_key = dim or raw
        prev = canonical_cues.get(canon_key)
        if prev is None or strength > prev[3]:
            canonical_cues[canon_key] = (raw, dim, axis, strength)

    dim_scores: List[Tuple[float, str]] = []
    target_who_set = {t["who"] for t in cue_targets if t.get("who")}
    why_tokens: Set[str] = set()
    for t in cue_targets:
        if t.get("why"):
            why_tokens.update(normalize_tokens(t["why"]) - STOPWORDS)
    dialogue_tokens = set(cues.get("dialogue_tokens") or ()) | why_tokens

    for canon_key, (cue_raw, cue_dim, cue_axis, cue_int) in canonical_cues.items():
        best_for_dim = 0.0
        for me in mem_entries:
            match_strength = 0.0
            if me["raw"] == cue_raw or (cue_dim and me["dim"] == cue_dim) or (cue_dim and me["raw"] == cue_dim):
                match_strength = 1.0
            elif cue_axis and me["axis"] == cue_axis:
                match_strength = 0.55
            if match_strength <= 0.0:
                continue

            base_emo = 1.5 * match_strength
            if cue_int >= 6.0:
                multiplier = 1.0 + ((cue_int - 5.0) * 0.3)
                cand = base_emo * multiplier
            elif cue_int < 3.0:
                cand = base_emo * max(0.65, cue_int / 3.0)
            else:
                cand = base_emo

            mem_who = me.get("who") or ""
            if mem_who:
                who_ids: Set[str] = set()
                who_names: Set[str] = set()
                _add_actor_variants([mem_who], who_ids, who_names)
                if (
                    mem_who in target_who_set
                    or (who_ids & actor_ids)
                    or (who_names & actor_names)
                ):
                    cand *= 1.3
            mem_why = me.get("why") or ""
            if mem_why and dialogue_tokens:
                if (normalize_tokens(mem_why) - STOPWORDS) & dialogue_tokens:
                    cand += 0.35

            if cand > best_for_dim:
                best_for_dim = cand

        if best_for_dim > 0.0:
            dim_scores.append((best_for_dim, canon_key))

    if not dim_scores:
        return 0.0, "", []

    dim_scores.sort(key=lambda pair: pair[0], reverse=True)
    total_emo = dim_scores[0][0]
    decay_weights = (0.65, 0.45, 0.3)
    for idx, (val, _) in enumerate(dim_scores[1:]):
        w = decay_weights[idx] if idx < len(decay_weights) else 0.2
        total_emo += val * w

    total_emo = min(6.0, total_emo)
    matched_dims = [k for _, k in dim_scores]
    return total_emo, matched_dims[0], matched_dims


def score_memory(
    memory: Dict[str, Any],
    cues: Dict[str, Any],
    current_tick: int,
    half_life: float = 300.0,
) -> Tuple[float, Dict[str, Any]]:
    """Score a single memory against multi-facet situation cues."""
    active, reason = is_active_memory(memory, current_tick)
    if not active:
        return 0.0, {"active": False, "reason": reason}

    mem_text = _mem_text(memory)
    if not mem_text and memory.get("kind") == "absence":
        tgt = memory.get("target") or (memory.get("data") or {}).get("expected_item") or "item"
        loc = _mem_location_display(memory) or (memory.get("data") or {}).get("subject") or "area"
        mem_text = f"Confirmed absent: {tgt} in {loc}"

    mem_tokens = normalize_tokens(mem_text)
    mem_tags = {str(t).lower() for t in (memory.get("tags") or ()) if t}
    mem_eids = _mem_entity_ids(memory)
    mem_locations = _mem_locations(memory)
    mem_loc_forms: Set[str] = set()
    for ml in mem_locations:
        mem_loc_forms.update(_expand_area_keys(ml))
    mem_location_display = _mem_location_display(memory)
    mem_id = str(memory.get("id") or "")

    if memory.get("kind") == "absence":
        if memory.get("target"):
            mem_eids.update(_expand_entity_ids([str(memory["target"])]))
        if isinstance(memory.get("data"), dict):
            if memory["data"].get("subject"):
                mem_eids.update(_expand_entity_ids([str(memory["data"]["subject"])]))
            if memory["data"].get("expected_item"):
                mem_eids.update(_expand_entity_ids([str(memory["data"]["expected_item"])]))

    facets_hit: List[str] = []
    matched_entities: List[str] = []
    matched_spatial_label = ""
    matched_actors: List[str] = []
    matched_items: List[str] = []
    matched_needs: List[str] = []
    matched_words: List[str] = []
    matched_emotion_label = ""

    actor_ids = _expand_entity_ids(str(a) for a in (cues.get("actor_ids") or ()) if a)
    actor_names = {_collapse_ws(a) for a in (cues.get("actor_names") or ()) if a}
    _add_actor_variants(cues.get("actors"), actor_ids, actor_names)

    item_ids = _expand_entity_ids(str(i) for i in (cues.get("item_ids") or ()) if i)
    item_names = {_collapse_ws(i) for i in (cues.get("item_names") or ()) if i}
    _add_item_variants(cues.get("items"), item_ids, item_names)
    _add_item_variants(cues.get("inventory"), item_ids, item_names)

    if "attributed_dialogue" in cues or "unattributed_dialogue_tokens" in cues:
        attributed_dialogue = list(cues.get("attributed_dialogue") or ())
        unattr_tokens = set(cues.get("unattributed_dialogue_tokens") or ())
        if not unattr_tokens and not attributed_dialogue and cues.get("dialogue_tokens"):
            unattr_tokens = set(cues["dialogue_tokens"])
    else:
        d_parsed = _parse_dialogue_cues(cues)
        attributed_dialogue = d_parsed["attributed_dialogue"]
        unattr_tokens = d_parsed["unattributed_dialogue_tokens"]
        if not unattr_tokens and not attributed_dialogue and cues.get("dialogue_tokens"):
            unattr_tokens = set(cues["dialogue_tokens"])
        actor_ids.update(d_parsed["speaker_ids"])
        actor_names.update(d_parsed["speaker_names"])

    # -- Channel 1: Spatial Proximity (exact canonical/slug/name sets) -----
    spatial_score = 0.0
    area_id = _collapse_ws(cues.get("area_id") or "")
    area_forms = {_collapse_ws(a) for a in (cues.get("area_forms") or ()) if a}
    if area_id:
        area_forms.update(_expand_area_keys(area_id))

    adjacent_forms: Set[str] = set()
    for adj in (cues.get("adjacent_area_ids") or ()):
        adjacent_forms.update(_expand_area_keys(adj))
    adjacent_forms -= area_forms

    if area_forms and ((area_forms & mem_loc_forms) or (area_forms & mem_eids)):
        spatial_score += 3.5
        matched_spatial_label = mem_location_display or area_id
        matched_entities.append(area_id or sorted(area_forms)[0])
        facets_hit.extend(["spatial", "area"])
    elif adjacent_forms and (mem_loc_forms & adjacent_forms):
        spatial_score += 1.5
        matched_spatial_label = f"adjacent: {mem_location_display}"
        facets_hit.extend(["spatial", "area"])
    elif adjacent_forms and (mem_eids & adjacent_forms):
        spatial_score += 1.5
        matched_adj = sorted(mem_eids & adjacent_forms)[0]
        matched_spatial_label = f"adjacent: {matched_adj}"
        facets_hit.extend(["spatial", "area"])

    m_items = mem_eids & item_ids
    if m_items:
        spatial_score += 2.0 * len(m_items)
        matched_items.extend(sorted(m_items))
        matched_entities.extend(sorted(m_items))
        if "item" not in facets_hit:
            facets_hit.append("item")

    for iname in item_names:
        iname_tokens = normalize_tokens(iname)
        if iname_tokens and iname_tokens.issubset(mem_tokens):
            if "item" not in facets_hit:
                spatial_score += 1.5
                matched_items.append(iname)
                matched_entities.append(iname)
                facets_hit.append("item")

    # -- Channel 2: Social Presence ----------------------------------------
    social_score = 0.0
    m_actors = mem_eids & actor_ids
    if m_actors:
        social_score += 2.5 * len(m_actors)
        matched_actors.extend(sorted(m_actors))
        matched_entities.extend(sorted(m_actors))
        facets_hit.extend(["social", "actor"])

    for aname in actor_names:
        aname_tokens = normalize_tokens(aname)
        if aname_tokens and aname_tokens.issubset(mem_tokens):
            if "social" not in facets_hit:
                social_score += 2.0
                matched_actors.append(aname)
                matched_entities.append(aname)
                facets_hit.extend(["social", "actor"])

    for sab in _mem_about(memory):
        if sab in actor_ids or sab in actor_names:
            if "social" not in facets_hit:
                social_score += 2.0
                matched_actors.append(sab)
                facets_hit.extend(["social", "actor"])

    # -- Channel 3: Conversational Echo (with speaker/addressee binding) ---
    conversational_score = 0.0
    best_attr_score = 0.0
    matched_words_set: Set[str] = set()
    matched_speaker = False
    matched_target = False

    if attributed_dialogue:
        mem_spk_ids, mem_spk_names, mem_tgt_ids, mem_tgt_names = _mem_dialogue_attribution(memory)
        has_mem_speaker = bool(mem_spk_ids or mem_spk_names)
        for d_entry in attributed_dialogue:
            entry_tokens = d_entry.get("tokens") or set()
            overlap = (mem_tokens & entry_tokens) - STOPWORDS
            if not overlap:
                continue
            cue_spk_ids = d_entry.get("speaker_ids") or set()
            cue_spk_names = d_entry.get("speaker_names") or set()
            spk_match = bool((mem_spk_ids & cue_spk_ids) or (mem_spk_names & cue_spk_names))
            if has_mem_speaker and not spk_match:
                # Conflicting speaker quote: do not credit unrelated speaker's words
                continue
            base_line = (len(overlap) / max(1, min(len(entry_tokens), 8))) * 3.0
            if spk_match:
                matched_speaker = True
                line_score = base_line + 1.5
                cue_tgt_ids = d_entry.get("target_ids") or set()
                cue_tgt_names = d_entry.get("target_names") or set()
                if (cue_tgt_ids or cue_tgt_names) and (mem_tgt_ids or mem_tgt_names):
                    if (mem_tgt_ids & cue_tgt_ids) or (mem_tgt_names & cue_tgt_names):
                        line_score += 1.0
                        matched_target = True
                    else:
                        line_score = max(0.5, line_score - 0.5)
                matched_words_set.update(overlap)
                best_attr_score = max(best_attr_score, line_score)
            else:
                matched_words_set.update(overlap)
                best_attr_score = max(best_attr_score, base_line)

    unattr_score = 0.0
    if unattr_tokens:
        m_unattr = (mem_tokens & unattr_tokens) - STOPWORDS
        if m_unattr:
            unattr_score = (len(m_unattr) / max(1, min(len(unattr_tokens), 8))) * 3.0
            matched_words_set.update(m_unattr)

    conversational_score = max(best_attr_score, unattr_score)
    if conversational_score > 0:
        matched_words = sorted(matched_words_set)
        facets_hit.extend(["conversational", "dialogue"])
        if matched_speaker:
            facets_hit.append("speaker_bound")
        if matched_target:
            facets_hit.append("addressee_bound")

    # -- Channel 4: Emotional Congruency (multi-dimensional & target-bound)-
    emotional_score, matched_emotion_label, matched_emotion_dims = _match_emotion_channel(
        memory, cues, actor_ids, actor_names
    )
    if emotional_score > 0:
        facets_hit.extend(["emotional", "emotion"])

    # -- Channel 5: Physical Need / Drive ----------------------------------
    need_score = 0.0
    active_needs = cues.get("needs") or ()
    for need_key in active_needs:
        vocabulary = NEED_TAG_MAP.get(need_key, set())
        if mem_tags & vocabulary:
            need_score += 3.0
            matched_needs.append(need_key)
            facets_hit.append("need")
            break
        elif mem_tokens & vocabulary:
            need_score += 2.0
            matched_needs.append(need_key)
            facets_hit.append("need")
            break

    # -- Channel 6: Temporal Recency & Activation --------------------------
    mem_tick = _mem_seq(memory)
    age = max(0, current_tick - mem_tick)
    recency_score = (0.5 ** (age / half_life)) * 2.0 if half_life > 0 else 0.0
    if recency_score >= 0.8:
        facets_hit.append("recency")

    memory_dynamics.ensure_dynamics(memory)
    eff_imp = memory_dynamics.effective_importance(memory) / 10.0
    importance_weight = eff_imp * 2.0

    # -- Channel 7: Semantic Embedding Similarity --------------------------
    semantic_score = 0.0
    semantic_scores = cues.get("semantic_scores") or {}
    sim: Optional[float] = None
    if mem_id and mem_id in semantic_scores:
        sim = float(semantic_scores[mem_id])
    elif memory.get("semantic_score") is not None:
        sim = float(memory["semantic_score"])
    elif memory.get("similarity") is not None:
        sim = float(memory["similarity"])
    elif cues.get("query_vector") and isinstance(memory.get("embedding"), (list, tuple)) and memory["embedding"]:
        sim = _cosine(cues["query_vector"], memory["embedding"])

    if sim is not None and sim > 0.0:
        semantic_score = sim * 3.0
        facets_hit.append("semantic")

    # -- Multi-facet intersection boost ------------------------------------
    situational_facets = set()
    if spatial_score > 0:
        situational_facets.add("spatial")
    if social_score > 0:
        situational_facets.add("social")
    if conversational_score > 0:
        situational_facets.add("conversational")
    if emotional_score > 0:
        situational_facets.add("emotional")
    if need_score > 0:
        situational_facets.add("need")
    if semantic_score > 0:
        situational_facets.add("semantic")

    intersection_boost = 0.0
    if len(situational_facets) >= 2:
        intersection_boost = (len(situational_facets) - 1) * 2.5

    situational_score = (
        spatial_score + social_score + conversational_score
        + emotional_score + need_score + semantic_score + intersection_boost
    )
    base_salience = (recency_score * 0.5) + (importance_weight * 0.5)

    if situational_score > 0:
        total = situational_score + base_salience
    else:
        total = base_salience if eff_imp >= 0.9 else (base_salience * 0.2)

    interest_tags = {str(t).strip().lower() for t in (cues.get("interest_tags") or ()) if t}
    fear_tags = {str(t).strip().lower() for t in (cues.get("fear_tags") or ()) if t}
    dislike_tags = {str(t).strip().lower() for t in (cues.get("dislike_tags") or ()) if t}
    persona_score = 0.0
    dislike_dampened = False
    if dislike_tags and memory_dynamics._memory_matches_tags(memory, dislike_tags):
        imp_val = memory_dynamics._memory_importance(memory)
        if imp_val < 7 and social_score == 0 and conversational_score == 0:
            total *= 0.45
            dislike_dampened = True
    elif fear_tags and memory_dynamics._memory_matches_tags(memory, fear_tags):
        persona_score = 1.0
        total += persona_score
        facets_hit.append("fear")
    elif interest_tags and memory_dynamics._memory_matches_tags(memory, interest_tags):
        persona_score = 0.7
        total += persona_score
        facets_hit.append("interest")

    domain_tags = {str(t).strip().lower() for t in (cues.get("domain_tags") or ()) if t}
    domain_score = 0.0
    if domain_tags and memory_dynamics._memory_matches_tags(memory, domain_tags):
        domain_score = 0.85
        total += domain_score
        facets_hit.append("domain")

    channel_vals = {
        "spatial": spatial_score,
        "social": social_score,
        "conversational": conversational_score,
        "emotional": emotional_score,
        "need": need_score,
        "semantic": semantic_score,
    }
    active_situational = {k: v for k, v in channel_vals.items() if v > 0}
    if active_situational:
        primary_signal = max(active_situational.items(), key=lambda x: x[1])[0]
    elif recency_score >= 0.5:
        primary_signal = "recency"
    else:
        primary_signal = "importance"

    percent_match = min(100, max(0, int(round(total * 10))))

    channels = {
        "spatial": round(spatial_score, 3),
        "social": round(social_score, 3),
        "conversational": round(conversational_score, 3),
        "emotional": round(emotional_score, 3),
        "need": round(need_score, 3),
        "recency": round(recency_score, 3),
        "semantic": round(semantic_score, 3),
    }

    points = {
        "spatial": int(round(spatial_score * 10)),
        "social": int(round(social_score * 10)),
        "conversational": int(round(conversational_score * 10)),
        "emotional": int(round(emotional_score * 10)),
        "need": int(round(need_score * 10)),
        "recency": int(round(recency_score * 10)),
        "semantic": int(round(semantic_score * 10)),
    }

    provenance = {
        "score": round(total, 3),
        "total_score": round(total, 3),
        "percent_match": percent_match,
        "primary_signal": primary_signal,
        "channels": channels,
        "points": points,
        "facets_hit": sorted(set(facets_hit)),
        "details": {
            "spatial": matched_spatial_label,
            "social": matched_actors,
            "conversational": matched_words,
            "emotional": matched_emotion_label,
            "emotional_dimensions": matched_emotion_dims,
            "need": matched_needs,
        },
    }

    breakdown: Dict[str, Any] = {
        "active": True,
        "facets_hit": sorted(set(facets_hit)),
        "channels": channels,
        "points": points,
        "primary_signal": primary_signal,
        "percent_match": percent_match,
        "_provenance": provenance,
        "provenance": provenance,
        "keyword_score": round(conversational_score, 3),
        "conversational_score": round(conversational_score, 3),
        "entity_score": round(spatial_score + social_score, 3),
        "spatial_score": round(spatial_score, 3),
        "social_score": round(social_score, 3),
        "need_score": round(need_score, 3),
        "emotion_score": round(emotional_score, 3),
        "emotional_score": round(emotional_score, 3),
        "recency_score": round(recency_score, 3),
        "recency_weight": round(recency_score, 3),
        "semantic_score": round(semantic_score, 3),
        "intersection_boost": round(intersection_boost, 3),
        "importance_weight": round(importance_weight, 3),
        "situational_score": round(situational_score, 3),
        "matched_words": matched_words,
        "matched_entities": matched_entities,
        "matched_items": matched_items,
        "matched_actors": matched_actors,
        "matched_spatial_label": matched_spatial_label,
        "matched_emotion_label": matched_emotion_label,
        "matched_emotion_dimensions": matched_emotion_dims,
        "matched_speaker_bound": matched_speaker,
        "matched_target_bound": matched_target,
        "matched_needs": matched_needs,
        "persona_score": round(persona_score, 3),
        "domain_score": round(domain_score, 3),
        "dislike_dampened": dislike_dampened,
        "total_score": round(total, 3),
    }

    return total, breakdown


def is_open_question_match(memory: Dict[str, Any], cues: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Determine if an open question's watch targets match current perception."""
    cat = memory.get("category") or memory_dynamics.category_for(memory)
    if cat != memory_dynamics.QUESTION and str(memory.get("type", "")) != "question":
        return False, []

    status = _mem_status(memory)
    if memory.get("answered_by") or status in ("resolved", "superseded", "invalidated"):
        return False, []

    watch_refs: Set[str] = set()
    for r in (memory.get("watch_refs") or ()):
        watch_refs.add(_collapse_ws(r))
    watch_cues = memory.get("watch_cues")
    if isinstance(watch_cues, dict):
        for r in (watch_cues.get("entities") or ()):
            watch_refs.add(_collapse_ws(r))
        for r in (watch_cues.get("keywords") or ()):
            watch_refs.add(_collapse_ws(r))
    for a in _mem_about(memory):
        watch_refs.add(_collapse_ws(a))
    for t in (memory.get("tags") or ()):
        watch_refs.add(_collapse_ws(t))

    if not watch_refs:
        watch_refs = normalize_tokens(_mem_text(memory)) - STOPWORDS

    matched: List[str] = []
    actor_ids = _expand_entity_ids(cues.get("actor_ids") or ())
    actor_names = {_collapse_ws(a) for a in (cues.get("actor_names") or ())}
    item_ids = _expand_entity_ids(cues.get("item_ids") or ())
    item_names = {_collapse_ws(i) for i in (cues.get("item_names") or ())}
    dialogue = cues.get("dialogue_tokens") or set()

    for ref in watch_refs:
        ref_norm = next(iter(_expand_entity_ids([ref])), ref)
        if ref in actor_ids or ref_norm in actor_ids or ref in actor_names:
            matched.append(ref)
        elif ref in item_ids or ref_norm in item_ids or ref in item_names:
            matched.append(ref)
        elif ref in dialogue:
            matched.append(ref)
        elif ref.startswith("concept:") and ref[8:] in dialogue:
            matched.append(ref)
        elif ref.startswith("item:") and ref[5:] in item_names:
            matched.append(ref)

    return len(matched) > 0, matched


def _player_node_id_for(player: Any, world: Any) -> str:
    pid = getattr(player, "id", None)
    if pid:
        return str(pid)
    pname = getattr(player, "name", "") or ""
    if world is not None and pname:
        try:
            return str(world._player_node_id(pname))
        except Exception:
            pass
    if not pname:
        return ""
    slug = re.sub(r"\s+", "_", pname.strip().lower())
    return f"player_{slug}"


def _carried_items_from_graph(player: Any, world: Any) -> List[str]:
    """Read carried/equipped item names and IDs from the world graph."""
    graph = getattr(world, "graph", None) if world is not None else None
    if graph is None or not callable(getattr(graph, "get_edges_for_target", None)):
        return []
    pnode_id = _player_node_id_for(player, world)
    if not pnode_id:
        return []
    out: List[str] = []
    try:
        from graph import EDGE_CARRYING, EDGE_EQUIPPED

        for edge in graph.get_edges_for_target(pnode_id, (EDGE_CARRYING, EDGE_EQUIPPED)):
            node = graph.get_node(edge.source)
            if node is not None and getattr(node, "type", None) == "item":
                out.append(str(node.id))
                if getattr(node, "name", None):
                    out.append(str(node.name))
    except Exception:
        pass
    return out


def _filter_stealth_cues(cues: Dict[str, Any], player: Any, world: Any) -> None:
    """Drop hidden/stealthed actors and hidden items from cues when world state marks them hidden."""
    if world is None:
        return
    known = {str(k).lower() for k in (getattr(player, "known", None) or ())}
    players_map = getattr(world, "players", None) or {}
    hidden_actor_keys: Set[str] = set()
    self_name = _collapse_ws(getattr(player, "name", ""))

    for pname, pobj in players_map.items():
        pname_l = _collapse_ws(pname)
        if pname_l == self_name:
            continue
        is_hidden = bool(
            getattr(pobj, "hidden", False)
            or getattr(pobj, "stealthed", False)
            or "hidden" in (getattr(pobj, "conditions", None) or ())
        )
        if is_hidden:
            _add_actor_variants([pname, getattr(pobj, "id", "")], hidden_actor_keys, hidden_actor_keys, world=world)

    if hidden_actor_keys:
        cues["actor_ids"] = {a for a in cues["actor_ids"] if a not in hidden_actor_keys}
        cues["actor_names"] = {a for a in cues["actor_names"] if a not in hidden_actor_keys}

    graph = getattr(world, "graph", None)
    if graph is not None and getattr(graph, "nodes", None):
        hidden_item_keys: Set[str] = set()
        for nid, node in graph.nodes.items():
            if getattr(node, "type", None) != "item":
                continue
            props = getattr(node, "properties", None) or {}
            if str(props.get("current_state") or "").strip().lower() == "hidden" and str(nid).lower() not in known:
                _add_item_variants([nid, getattr(node, "name", "")], hidden_item_keys, hidden_item_keys)
        if hidden_item_keys:
            cues["item_ids"] = {i for i in cues["item_ids"] if i not in hidden_item_keys}
            cues["item_names"] = {i for i in cues["item_names"] if i not in hidden_item_keys}


def retrieve_associative_memories(
    player: Any,
    payload: Dict[str, Any],
    world: Any = None,
    tick: Optional[int] = None,
    max_results: int = 6,
    min_score: float = 1.2,
    explain: bool = False,
    do_reinforce: bool = True,
) -> Dict[str, Any]:
    """Execute associative retrieval across structured situation cues."""
    memories: List[Dict[str, Any]] = list(getattr(player, "memories", []) or [])
    if not memories:
        return {
            "memories": [],
            "lanes": {
                "associative": [],
                "open_questions": [],
                "beliefs": [],
            },
            "stats": {"total_candidates": 0, "recalled_count": 0},
        }

    current_tick = int(tick if tick is not None else getattr(world, "time_ticks", 0) or 0)
    merged_payload = dict(payload or {})
    if isinstance(merged_payload.get("cues"), dict):
        merged_payload = {**merged_payload, **merged_payload["cues"]}
    if "inventory" not in merged_payload and world is not None:
        carried = _carried_items_from_graph(player, world)
        if carried:
            merged_payload["inventory"] = carried

    cues = extract_cues(merged_payload, world=world, player=player)
    _filter_stealth_cues(cues, player=player, world=world)

    if not cues.get("interest_tags"):
        cues["interest_tags"] = {str(t).strip().lower() for t in (getattr(player, "interest_tags", None) or ()) if t}
    if not cues.get("fear_tags"):
        cues["fear_tags"] = {str(t).strip().lower() for t in (getattr(player, "fear_tags", None) or ()) if t}
    if not cues.get("dislike_tags"):
        cues["dislike_tags"] = {str(t).strip().lower() for t in (getattr(player, "dislike_tags", None) or ()) if t}
    if not cues.get("domain_tags"):
        dom_tags: Set[str] = set()
        ign_tags: Set[str] = set()
        for entry in (getattr(player, "domains", None) or ()):
            if not isinstance(entry, dict) or not entry.get("domain"):
                continue
            slug = str(entry["domain"]).strip().lower()
            lvl = str(entry.get("level") or "familiar").strip().lower()
            if lvl == "ignorant":
                ign_tags.add(slug)
            else:
                dom_tags.add(slug)
                for term in (entry.get("jargon_terms") or ()):
                    t_clean = str(term).strip().lower()
                    if t_clean:
                        dom_tags.add(t_clean)
        if dom_tags:
            cues["domain_tags"] = dom_tags
        if ign_tags and not cues.get("ignorant_domain_tags"):
            cues["ignorant_domain_tags"] = ign_tags

    # Optional server-side VectorStore query when caller supplies query_vector + data_dir
    if not cues.get("semantic_scores") and cues.get("query_vector"):
        data_dir = (
            merged_payload.get("data_dir")
            or getattr(world, "data_dir", None)
            or getattr(player, "data_dir", None)
        )
        if data_dir:
            try:
                char_keys = [k for k in (getattr(player, "name", None), getattr(player, "id", None)) if k]
                hits = VectorStore(data_dir).search(
                    cues["query_vector"],
                    character=char_keys or None,
                    k=max(10, int(max_results) * 2),
                )
                sem_map: Dict[str, float] = {}
                for hit in hits:
                    mid = hit.get("memory_id")
                    hscore = float(hit.get("score") or 0.0)
                    if mid and hscore >= 0.35:
                        sem_map[str(mid)] = max(sem_map.get(str(mid), 0.0), hscore)
                cues["semantic_scores"] = sem_map
            except Exception:
                pass

    current_dt = None
    if world is not None and hasattr(world, "datetime_for_tick"):
        try:
            current_dt = world.datetime_for_tick(current_tick)
        except Exception:
            current_dt = None

    scored_candidates: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
    open_questions: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for m in memories:
        # Time-lock (task-976 / Timeline Vision): deny recall of future memories
        # dated or ticked after the active simulation clock.
        m_dt = m.get("world_datetime")
        if current_dt and isinstance(m_dt, str) and m_dt > current_dt:
            if explain:
                rejected.append({"id": m.get("id"), "text": _mem_text(m)[:60], "reason": "future_time_locked"})
            continue
        m_tick = m.get("tick")
        if isinstance(m_tick, (int, float)) and int(m_tick) > current_tick:
            if explain:
                rejected.append({"id": m.get("id"), "text": _mem_text(m)[:60], "reason": "future_time_locked"})
            continue

        is_q, q_matches = is_open_question_match(m, cues)
        if is_q:
            q_entry = dict(m)
            q_entry["matched_refs"] = q_matches
            open_questions.append(q_entry)
            continue

        score, breakdown = score_memory(m, cues, current_tick)
        if not breakdown.get("active"):
            if explain:
                rejected.append({"id": m.get("id"), "text": _mem_text(m)[:60], "reason": breakdown.get("reason")})
            continue

        if score >= min_score:
            scored_candidates.append((score, m, breakdown))
        elif explain:
            rejected.append({"id": m.get("id"), "text": _mem_text(m)[:60], "score": round(score, 3), "reason": "below_min_score"})

    scored_candidates.sort(key=lambda x: (x[0], _mem_seq(x[1])), reverse=True)

    picked_ids: Set[str] = set()
    associative_lane: List[Dict[str, Any]] = []

    for s, m, b in scored_candidates[:max_results]:
        entry = dict(m)
        entry["score"] = round(s, 3)
        entry["_provenance"] = b.get("_provenance", {})
        entry["provenance"] = b.get("provenance", {})
        entry["primary_signal"] = b.get("primary_signal", "associative")
        entry["percent_match"] = b.get("percent_match", 0)
        if explain:
            entry["explanation"] = b
        associative_lane.append(entry)
        picked_ids.add(str(entry.get("id")))

    beliefs_lane: List[Dict[str, Any]] = []
    active_actor_ids = cues.get("actor_ids") or set()
    if active_actor_ids:
        for s, m, b in scored_candidates:
            if str(m.get("id")) in picked_ids:
                continue
            cat = m.get("category") or memory_dynamics.category_for(m)
            if cat in (memory_dynamics.BELIEF, memory_dynamics.SOCIAL):
                eids = _mem_entity_ids(m)
                if eids & active_actor_ids:
                    entry = dict(m)
                    entry["score"] = round(s, 3)
                    entry["_provenance"] = b.get("_provenance", {})
                    entry["provenance"] = b.get("provenance", {})
                    entry["primary_signal"] = b.get("primary_signal", "associative")
                    entry["percent_match"] = b.get("percent_match", 0)
                    if explain:
                        entry["explanation"] = b
                    beliefs_lane.append(entry)
                    picked_ids.add(str(entry.get("id")))
                    if len(beliefs_lane) >= 2:
                        break

    open_questions.sort(
        key=lambda q: (
            len(q.get("matched_refs") or ()),
            memory_dynamics._memory_importance(q),
            _mem_seq(q),
        ),
        reverse=True,
    )
    active_questions = open_questions[:2]

    if do_reinforce:
        all_recalled = associative_lane + beliefs_lane
        for r in all_recalled:
            mid = r.get("id")
            stored = next((orig for orig in memories if orig.get("id") == mid), None)
            if stored is not None:
                memory_dynamics.reinforce(stored, tick=current_tick)
                if r.get("_provenance"):
                    stored["_provenance"] = r["_provenance"]
                    stored["provenance"] = r["_provenance"]

    combined_memories = associative_lane + beliefs_lane

    result: Dict[str, Any] = {
        "memories": combined_memories,
        "lanes": {
            "associative": associative_lane,
            "beliefs": beliefs_lane,
            "open_questions": active_questions,
        },
        "stats": {
            "total_candidates": len(memories),
            "recalled_count": len(combined_memories),
            "open_questions_count": len(active_questions),
        },
    }

    if explain:
        result["rejected"] = rejected[:10]
        result["cues"] = {
            "actors": sorted(cues["actor_ids"]),
            "items": sorted(cues["item_ids"]),
            "needs": sorted(cues["needs"]),
            "dialogue_tokens": list(cues["dialogue_tokens"])[:15],
            "dialogue_speakers": sorted(cues.get("dialogue_speakers") or ()),
            "dialogue_targets": sorted(cues.get("dialogue_targets") or ()),
            "area_id": cues["area_id"],
            "adjacent_area_ids": sorted(cues.get("adjacent_area_ids") or ()),
            "emotion": cues.get("emotion", ""),
            "emotions": dict(cues.get("emotion_vector") or {}),
        }

    return result


__all__ = [
    "logger",
    "STOPWORDS",
    "NEED_TAG_MAP",
    "normalize_tokens",
    "extract_cues",
    "is_active_memory",
    "score_memory",
    "is_open_question_match",
    "retrieve_associative_memories",
]
