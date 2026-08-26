# engine/matching.py — Name and item matching utilities extracted from VirtualWorld

import difflib
import re
from typing import List, Optional, Tuple

from graph import Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED


# Words too common to count as significant when matching characters by
# description ("the tall man in the corner" → "tall", "corner").
CHARACTER_DESCRIPTION_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "of", "to",
    "for", "with", "by", "from", "near", "next", "behind", "beside", "around",
    "under", "over", "across", "against", "is", "are", "was", "were", "has",
    "have", "had", "he", "she", "it", "they", "them", "his", "her", "their",
    "him", "its", "who", "whom", "that", "this", "these", "those", "which",
    "not", "you", "can", "could", "would", "should", "will", "looks", "look",
    "seems", "seem", "wearing", "wears", "stands", "standing", "sits",
    "sitting", "watches", "watching", "been", "being", "than", "as", "while",
})

# Generic descriptors too vague to uniquely identify anyone on their own.
CHARACTER_GENERIC_WORDS = frozenset({
    "man", "woman", "person", "people", "guy", "girl", "boy", "lady",
    "figure", "stranger", "someone", "somebody", "shadow", "shape",
})


def node_aliases(node) -> List[str]:
    """Normalize a node's ``aliases`` property into a lowercase list.

    Aliases are subjective names characters assign to things they observe
    ("the Butcher", "Hollow-Eyes", "the trapdoor"). They can be a list or a
    comma/``|``-separated string, and are stored hidden on the target node
    (item / way / area / character). Returns [] when absent.
    """
    if node is None:
        return []
    raw = node.properties.get("aliases") if hasattr(node, "properties") else None
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [a for a in re.split(r"[,\|]", raw) if a.strip()]
    out = []
    for a in raw:
        a = str(a).strip().lower()
        if a and a not in out:
            out.append(a)
    return out


class NameMatching:
    """Three-tier name matching for exits, items, and reachability checks.
    
    Uses exact match → substring/contains → fuzzy difflib matching.
    Stores fuzzy match notes for downstream notification.
    """

    def __init__(self, graph, game_state):
        self.graph = graph
        self.gs = game_state  # Duck-typed VirtualWorld instance
        self._fuzzy_match_note = None

    # ────────────────────── Exit Direction Matching ──────────────────────

    @staticmethod
    def way_handle(way_node, direction="", area_name=""):
        """Reference handle for a way in prompts and matching.

        ``direction`` (the per-side edge label) wins when set. Otherwise a
        short name is derived from the way node's name — the current area's
        "Name - " prefix is stripped, underscores become spaces — so a way
        named "Task 18 - final door" with an empty direction still resolves
        as "final door". Falls back to "door".
        """
        direction = (direction or "").strip()
        if direction:
            return direction
        name = (way_node.name if way_node else "") or ""
        name = name.strip()
        if area_name:
            prefix = f"{area_name} - "
            if name.lower().startswith(prefix.lower()):
                name = name[len(prefix):]
        name = name.replace("_", " ").strip()
        return name or "door"

    def _collect_exits(self, area_id: str) -> list:
        """Every connection edge from the area as (edge, way_node, handle,
        target_area_name). Unlike the old matcher, empty-direction edges are
        included — their handle comes from the way node's name."""
        out = []
        if not area_id:
            return out
        area_name = ""
        if getattr(self.gs, "current_area", None):
            area_name = self.gs.current_area.name or ""
        for edge in self.graph.get_edges_for_source(area_id, "connection"):
            way_node = self.graph.get_node(edge.target)
            if not way_node:
                continue
            direction = edge.properties.get("direction") or ""
            handle = self.way_handle(way_node, direction, area_name)
            target_area_name = ""
            for conn in self.graph.get_edges_for_source(way_node.id, "connection"):
                if conn.target != area_id:
                    target_node = self.graph.get_node(conn.target)
                    if target_node:
                        target_area_name = target_node.name
                        break
            out.append((edge, way_node, handle, target_area_name))
        return out

    def resolve_exit(self, area_id: str, input_str: str):
        """Resolve an exit by any facet, returning (edge, way_node, handle)
        or (None, None, "").

        Tiers: exact handle → cardinal → word-boundary substring → way node
        name / target area name → description words → state word → fuzzy.
        Handles empty-direction ways (via ``way_handle``) so ``go`` and
        ``examine`` can always reach a door that only has a name.
        """
        if not area_id or not input_str:
            return None, None, ""
        input_lower = input_str.lower().strip()

        from engine.character_spatial import resolve_transit_movement
        transit_hit = resolve_transit_movement(self.graph, self.gs, area_id, input_lower)
        if transit_hit:
            return transit_hit

        exits_info = self._collect_exits(area_id)
        if not exits_info:
            return None, None, ""
        handles = [info[2] for info in exits_info]

        def _pick(matches):
            if len(matches) == 1:
                edge, way_node, handle, _ = matches[0]
                return edge, way_node, handle
            if len(matches) > 1:
                edge, way_node, handle, _ = matches[0]
                return edge, way_node, handle
            return None, None, ""

        # 1. Exact match (case-insensitive) on the handle
        exact = [info for info in exits_info if info[2].lower() == input_lower]
        if exact:
            return _pick(exact)

        # 2. Cardinal match ("north", "south"...)
        for edge, way_node, handle, _ in exits_info:
            cardinal = edge.properties.get("cardinal", "") or ""
            if cardinal.lower() == input_lower:
                self._fuzzy_match_note = f"matched '{input_str}' as exit '{handle}' (cardinal match)"
                return edge, way_node, handle

        # 3. Word-boundary substring on the handle
        direct_matches = []
        for info in exits_info:
            hl = info[2].lower()
            if re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', hl):
                direct_matches.append(info)
                continue
            if re.search(r'(?<!\w)' + re.escape(hl) + r'(?!\w)', input_lower):
                direct_matches.append(info)
        if direct_matches:
            return _pick(direct_matches)

        # 3b. Alias tier — the way node's aliases, or the aliases of the area
        # it leads to ("go to the butcher shop", "go through the trapdoor").
        alias_matches = []
        area_nodes_by_name = {}
        for n in self.graph.nodes.values():
            if n.type == "area":
                area_nodes_by_name.setdefault(n.name.lower(), n)
        for info in exits_info:
            _, way_node, _, target_area_name = info
            target_area_node = area_nodes_by_name.get((target_area_name or "").lower()) if target_area_name else None
            for alias in node_aliases(way_node) + node_aliases(target_area_node):
                if alias == input_lower or re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', alias):
                    alias_matches.append(info)
                    break
        if len(alias_matches) == 1:
            self._fuzzy_match_note = f"matched '{input_str}' as exit '{alias_matches[0][2]}' (alias match)"
            return alias_matches[0][0], alias_matches[0][1], alias_matches[0][2]
        if len(alias_matches) > 1:
            self._fuzzy_match_note = f"matched '{input_str}' as exit '{alias_matches[0][2]}' (alias match, ambiguous)"
            return alias_matches[0][0], alias_matches[0][1], alias_matches[0][2]

        # 4. Way node name / target area name — word-boundary both ways
        name_matches = []
        for info in exits_info:
            _, way_node, handle, target_area_name = info
            candidates = [handle.lower()]
            if way_node and way_node.name:
                candidates.append(way_node.name.lower())
            if target_area_name:
                candidates.append(target_area_name.lower())
            for candidate in candidates:
                if re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', candidate):
                    name_matches.append(info)
                    break
                if re.search(r'(?<!\w)' + re.escape(candidate) + r'(?!\w)', input_lower):
                    name_matches.append(info)
                    break
        if name_matches:
            return _pick(name_matches)

        # 5. Description words — "the circular door with the keycard slot"
        significant = [
            w for w in re.findall(r"[a-z]+", input_lower)
            if len(w) >= 4 and w not in CHARACTER_DESCRIPTION_STOPWORDS
        ]
        if significant:
            desc_scored = []
            for info in exits_info:
                _, way_node, handle, target_area_name = info
                text = ""
                if way_node and way_node.properties.get("description"):
                    text += " " + str(way_node.properties["description"])
                if target_area_name:
                    text += " " + target_area_name
                text = text.lower()
                count = sum(
                    1 for w in set(significant)
                    if re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text)
                )
                desc_scored.append((count, info))
            best_count = max((c for c, _ in desc_scored), default=0)
            if best_count >= 2:
                top = [info for c, info in desc_scored if c == best_count]
                return _pick(top)
            if best_count == 1:
                top = [info for c, info in desc_scored if c == best_count]
                if len(top) == 1:
                    distinctive = [w for w in set(significant) if len(w) >= 6]
                    if distinctive:
                        return top[0][0], top[0][1], top[0][2]

        # 6. State word — "examine locked door" resolves via current_state
        state_words = {
            "open", "closed", "locked", "blocked", "broken", "jammed",
        }
        input_words = set(re.findall(r"[a-z]+", input_lower))
        state_hits = input_words & state_words
        if state_hits:
            state_matches = []
            for info in exits_info:
                _, way_node, handle, _ = info
                way_state = ""
                if way_node:
                    way_state = str(way_node.properties.get("current_state", "")).lower()
                if way_state in state_hits:
                    state_matches.append(info)
            if state_matches:
                return _pick(state_matches)

        # 7. Fuzzy difflib match on handles (tight cutoff)
        scored = difflib.get_close_matches(input_lower, handles, n=1, cutoff=0.6)
        if scored:
            for info in exits_info:
                if info[2].lower() == scored[0]:
                    self._fuzzy_match_note = f"matched '{input_str}' as exit '{info[2]}' (fuzzy match)"
                    return info[0], info[1], info[2]
        return None, None, ""

    def _match_exit_direction(self, area_id: str, input_str: str) -> Optional[str]:
        """Backward-compat wrapper: resolve an exit and return its handle."""
        _, _, handle = self.resolve_exit(area_id, input_str)
        return handle or None

    # ────────────────────── Item Name Matching ──────────────────────

    def _match_item_name(self, input_str: str) -> Optional[str]:
        """Find the closest matching item name in the area or player inventory.

        Tries exact match first, then substring/contains (word-boundary aware),
        then fuzzy difflib match. Stores a note in self._fuzzy_match_note
        when non-exact matching is used.
        """
        if not input_str:
            return None
        input_lower = input_str.lower().strip()
        player_id = self.gs._player_node_id(self.gs.active_player)
        area_id = self.gs._get_current_area_id()

        item_names = []
        # Area items
        if area_id:
            for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                node = self.graph.get_node(edge.source)
                if node:
                    item_names.append(node.name)
            # Items inside containers in the area (unhidden after examine)
            for container_edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                container_node = self.graph.get_node(container_edge.source)
                if container_node and container_node.type == "item":
                    if container_node.properties.get("current_state") == "locked":
                        continue
                    for content_edge in self.graph.get_edges_for_target(container_node.id, EDGE_IN):
                        node = self.graph.get_node(content_edge.source)
                        if node and node.type == "item" and node.properties.get("current_state") != "hidden":
                            item_names.append(node.name)
        # Carried items
        for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
            node = self.graph.get_node(edge.source)
            if node:
                if node.name not in item_names:
                    item_names.append(node.name)
        # Items inside carried containers
        for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
            container_node = self.graph.get_node(edge.source)
            if container_node and container_node.type == "item":
                if container_node.properties.get("current_state") == "locked":
                    continue
                for content_edge in self.graph.get_edges_for_target(container_node.id, EDGE_IN):
                    node = self.graph.get_node(content_edge.source)
                    if node and node.type == "item" and node.properties.get("current_state") != "hidden":
                        if node.name not in item_names:
                            item_names.append(node.name)
        if not item_names:
            return None

        # 1. Exact match (case-insensitive)
        for name in item_names:
            if name.lower() == input_lower:
                return name

        # Guard: no substring/fuzzy matching for pathological single-char inputs
        if len(input_lower) < 2:
            return None

        # 2. Word-boundary substring — input as a whole word inside a name,
        #    or name appearing as a whole word inside the input. Raw substring
        #    is NOT used ("stove" must not match "stovepipe").
        direct_matches = []
        for name in item_names:
            nl = name.lower()
            if re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', nl):
                direct_matches.append(name)
                continue
            if re.search(r'(?<!\w)' + re.escape(nl) + r'(?!\w)', input_lower):
                direct_matches.append(name)
        if len(direct_matches) == 1:
            self._fuzzy_match_note = f"matched '{input_str}' as item '{direct_matches[0]}' (substring match)"
            return direct_matches[0]
        if len(direct_matches) > 1:
            self._fuzzy_match_note = f"matched '{input_str}' as item '{direct_matches[0]}' (substring match, ambiguous)"
            return direct_matches[0]

        # 2b. Alias + description tier — input matches an item's aliases, or
        #     the significant words of its description ("withered crown",
        #     "pale petals" → the crushed flower crown).
        item_nodes_by_name = {}
        for n in self.graph.nodes.values():
            if n.type == "item":
                item_nodes_by_name.setdefault(n.name, n)
        alias_matches = []
        desc_scored = []  # (word-hit count, item name) via description words
        for name in item_names:
            node = item_nodes_by_name.get(name)
            if node is None:
                continue
            for alias in node_aliases(node):
                if alias == input_lower or re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', alias):
                    alias_matches.append(name)
                    break
            # Description words — same significant-word scoring as characters
            desc_text = (str(node.properties.get("description", "") or "")).lower()
            if desc_text:
                significant = [
                    w for w in re.findall(r"[a-z]+", input_lower)
                    if len(w) >= 4 and w not in CHARACTER_DESCRIPTION_STOPWORDS
                ]
                count = sum(
                    1 for w in set(significant)
                    if re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', desc_text)
                )
                if count >= 2:
                    desc_scored.append((count, name))
                elif count == 1:
                    distinctive = [w for w in set(significant) if len(w) >= 6]
                    if distinctive:
                        desc_scored.append((count, name))
        if len(alias_matches) == 1:
            self._fuzzy_match_note = f"matched '{input_str}' as item '{alias_matches[0]}' (alias match)"
            return alias_matches[0]
        if len(alias_matches) > 1:
            self._fuzzy_match_note = f"matched '{input_str}' as item '{alias_matches[0]}' (alias match, ambiguous)"
            return alias_matches[0]
        if desc_scored:
            best_count = max(c for c, _ in desc_scored)
            top = [name for c, name in desc_scored if c == best_count]
            if len(top) == 1:
                self._fuzzy_match_note = f"matched '{input_str}' as item '{top[0]}' (by description)"
                return top[0]
            self._fuzzy_match_note = f"matched '{input_str}' as item '{top[0]}' (by description, ambiguous)"
            return alias_matches[0]

        # 3. Fuzzy difflib match — score each item name against the input (tight cutoff)
        scored = difflib.get_close_matches(input_lower, [n.lower() for n in item_names], n=1, cutoff=0.7)
        if scored:
            for name in item_names:
                if name.lower() == scored[0]:
                    self._fuzzy_match_note = f"matched '{input_str}' as item '{name}' (fuzzy match)"
                    return name
        return None

    # ────────────────────── Character Name Matching ──────────────────────

    def _match_character_name(
        self,
        input_str: str,
        exclude_self: bool = True,
    ) -> Tuple[Optional[str], List[str]]:
        """Resolve a character target by name, name substring, or description.

        Used for targeting characters the actor may not have met yet
        ("attack the tall man in the corner"). Matching tiers:

        1. Exact name (case-insensitive)
        2. Word-boundary substring on the name
        3. Fuzzy difflib match on the name
        4. Description words — significant words from the input matched
           against each same-area character's description/base_description.

        Returns ``(name, candidates)``:
        - ``name`` is the matched player name, or None when ambiguous/unmatched.
        - ``candidates`` is a non-empty list of player names when the input
          is ambiguous (so the caller can prompt for a choice).
        """
        if not input_str:
            return None, []
        input_lower = input_str.lower().strip()
        current_area = self.gs.current_area.name if self.gs.current_area else None

        same_area = []
        for pname in self.gs.players:
            if exclude_self and pname == self.gs.active_player:
                continue
            player = self.gs.players[pname]
            if player.current_area == current_area:
                same_area.append(pname)
        if not same_area:
            return None, []

        # 1. Exact name
        exact = [p for p in same_area if p.lower() == input_lower]
        if len(exact) == 1:
            return exact[0], []
        if len(exact) > 1:
            return None, exact

        # 2. Word-boundary substring on the name
        name_matches = []
        for p in same_area:
            nl = p.lower()
            if re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', nl):
                name_matches.append(p)
                continue
            if re.search(r'(?<!\w)' + re.escape(nl) + r'(?!\w)', input_lower):
                name_matches.append(p)
        if len(name_matches) == 1:
            self._fuzzy_match_note = f"matched '{input_str}' as character '{name_matches[0]}' (name match)"
            return name_matches[0], []
        if len(name_matches) > 1:
            return None, name_matches

        # 2b. Alias tier — subjective names assigned to a character they've
        # observed ("attack the butcher", "talk to Hollow-Eyes").
        alias_matches = []
        for p in same_area:
            player_node = self.graph.get_node(self.gs._player_node_id(p))
            for alias in node_aliases(player_node):
                if alias == input_lower or re.search(r'(?<!\w)' + re.escape(input_lower) + r'(?!\w)', alias):
                    alias_matches.append(p)
                    break
        if len(alias_matches) == 1:
            self._fuzzy_match_note = f"matched '{input_str}' as character '{alias_matches[0]}' (alias match)"
            return alias_matches[0], []
        if len(alias_matches) > 1:
            return None, alias_matches

        # 3. Fuzzy name match (tight cutoff — only accept a clear single winner)
        scored = difflib.get_close_matches(input_lower, [p.lower() for p in same_area], n=1, cutoff=0.6)
        if scored:
            for p in same_area:
                if p.lower() == scored[0]:
                    self._fuzzy_match_note = f"matched '{input_str}' as character '{p}' (fuzzy match)"
                    return p, []

        # 4. Description-word matching
        significant = [
            w for w in re.findall(r"[a-z]+", input_lower)
            if len(w) >= 4 and w not in CHARACTER_DESCRIPTION_STOPWORDS
        ]
        if significant:
            scored_players = []
            for p in same_area:
                player = self.gs.players[p]
                text = (
                    f"{player.description or ''} "
                    f"{player.base_description or ''}"
                ).lower()
                count = sum(
                    1 for w in set(significant)
                    if re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text)
                )
                scored_players.append((count, p))
            best_count = max((c for c, _ in scored_players), default=0)
            if best_count >= 2:
                top = [p for c, p in scored_players if c == best_count]
                if len(top) == 1:
                    self._fuzzy_match_note = (
                        f"matched '{input_str}' as character '{top[0]}' (by description)"
                    )
                    return top[0], []
                return None, top
            if best_count == 1:
                distinctive = [
                    w for w in set(significant)
                    if len(w) >= 6 and w not in CHARACTER_GENERIC_WORDS
                ]
                top = [p for c, p in scored_players if c == best_count]
                if distinctive and len(top) == 1:
                    player = self.gs.players[top[0]]
                    text = (
                        f"{player.description or ''} "
                        f"{player.base_description or ''}"
                    ).lower()
                    if any(
                        re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text)
                        for w in distinctive
                    ):
                        self._fuzzy_match_note = (
                            f"matched '{input_str}' as character '{top[0]}' (by description)"
                        )
                        return top[0], []
                if len(top) > 1:
                    return None, top

        # 5. Generic descriptor fallback — "the woman"/"the man"/"the stranger".
        # Runs even when no ≥4-char significant words exist (e.g. "the man"),
        # resolving when the kind word literally appears in exactly one
        # description, or matches one character's gender pronouns; genderless
        # kinds only when a single occupant is present.
        generic_kind = [
            w for w in re.findall(r"[a-z]+", input_lower)
            if w in CHARACTER_GENERIC_WORDS
        ]
        # Only a pure generic label ("the woman", "the man") gets the fallback —
        # if the input also names descriptive words ("distant room man") those
        # describe someone/something else, so a generic kind must not resolve.
        descriptive_words = [
            w for w in re.findall(r"[a-z]+", input_lower)
            if len(w) >= 4
            and w not in CHARACTER_DESCRIPTION_STOPWORDS
            and w not in CHARACTER_GENERIC_WORDS
        ]
        if generic_kind and not descriptive_words:
            texts = {}
            for p in same_area:
                player = self.gs.players[p]
                texts[p] = (
                    f"{player.description or ''} "
                    f"{player.base_description or ''}"
                ).lower()
            literal = [
                p for p, text in texts.items()
                if any(
                    re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text)
                    for w in generic_kind
                )
            ]
            if len(literal) == 1:
                self._fuzzy_match_note = (
                    f"matched '{input_str}' as character '{literal[0]}' (by description)"
                )
                return literal[0], []
            if len(literal) > 1:
                return None, literal

            male_hint = any(w in ("man", "guy", "boy") for w in generic_kind)
            female_hint = any(w in ("woman", "girl", "lady") for w in generic_kind)
            hits = []
            if male_hint or female_hint:
                for p, text in texts.items():
                    if male_hint and re.search(r"\b(?:he|his|him)\b", text):
                        hits.append(p)
                    elif female_hint and re.search(r"\b(?:she|her|hers)\b", text):
                        hits.append(p)
            else:
                hits = same_area
            if len(hits) == 1:
                self._fuzzy_match_note = (
                    f"matched '{input_str}' as character '{hits[0]}' (by description)"
                )
                return hits[0], []
        return None, []

    # ────────────────────── Item Reachability ──────────────────────

    def _is_item_reachable(self, item_id: str, area_id: str) -> bool:
        """Check if an item node is actually in the current area, inventory, or an examined container."""
        # In the area directly
        for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
            if edge.source == item_id:
                return True
        # In player inventory (carried or equipped — a worn backpack counts)
        player_id = self.gs._player_node_id(self.gs.active_player)
        for edge in self.graph.get_edges_for_target(player_id, (EDGE_CARRYING, EDGE_EQUIPPED)):
            if edge.source == item_id:
                return True
        # Inside a container in the area (must be unhidden = examined)
        for ce in self.graph.get_edges_for_target(area_id, EDGE_IN):
            for content_edge in self.graph.get_edges_for_target(ce.source, EDGE_IN):
                if content_edge.source == item_id:
                    node = self.graph.get_node(item_id)
                    if node and node.properties.get("current_state") != "hidden":
                        return True
        # Inside a container in the player's inventory (carried or equipped)
        for et in (EDGE_CARRYING, EDGE_EQUIPPED):
            for ce in self.graph.get_edges_for_target(player_id, et):
                for content_edge in self.graph.get_edges_for_target(ce.source, EDGE_IN):
                    if content_edge.source == item_id:
                        node = self.graph.get_node(item_id)
                        if node and node.properties.get("current_state") != "hidden":
                            return True
        # On/under/beside/behind/at a surface in the area (spatial placement).
        # NOTE: get_edges_for_target(area, EDGE_IN) already expands spatial edges
        # (graph.py:98-103), so the first loop above covers placed items too.
        return False

    # ────────────────────── Player Area Assignment ──────────────────────

    def _set_player_area(self, player_name: str, area_name: str):
        """Update both the player object and the graph location edge."""
        player = self.gs.players.get(player_name)
        if not player:
            return
        player_node_id = self.gs._player_node_id(player_name)
        # Remove ALL existing location edges (in + legacy location) before
        # adding the new one. Area node ids can differ from the id derived
        # from the area name (e.g. case: "Task 2" vs "area_Task_2"), so a
        # targeted remove would silently miss and leave a stale edge behind.
        for edge in list(self.graph.get_edges_for_source(player_node_id, EDGE_IN)):
            self.graph.remove_edge(edge.source, edge.target, edge.type)
        # Find actual area node ID from graph by name (handles non-standard IDs)
        new_area_id = self.gs._area_node_id(area_name)
        for node in self.graph.nodes.values():
            if node.type == "area" and node.name == area_name:
                new_area_id = node.id
                break
        self.graph.add_edge(Edge(source=player_node_id, target=new_area_id, type=EDGE_IN))
        player.current_area = area_name
