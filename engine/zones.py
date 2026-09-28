"""Zone-driven fidelity: a distant zone is a record, not a graph (task-500).

A 500-zone world that holds every area and way node at once is the offloading
win this task is about, and the node-count blow-up that freezes the graph view
(task-400). So a zone you are not in holds its **scope record** and nothing else,
and materialises its areas and ways on approach.

This is the one slice of task-500 that is not owned by another task: the task's
own header says so. Fidelity-*tier selection* is task-411 + task-418
(`engine/attention.py`), and chunk load/evict is task-401. What is left here is
the zone as the **materialisation** key.

**Provenance is the selector.** Every compiled node already carries
``properties.generated.scope_id`` (`engine.generation.provenance`), so releasing
a zone is "delete exactly the nodes that recipe produced for it" — the same
mechanism the design doc's 🧹 Ungenerate calls for, used as the runtime
half of a materialise/release cycle.

## The safety rules, which are the actual content

Releasing a zone is destructive and mostly irreversible, so the refusals matter
more than the happy path. Four, in the order they are checked:

1. **A zone someone is standing in is not released.** Its areas vanish under their
   feet, and `current_area` becomes a dangling reference.
2. **A zone whose parent this store released is not released.** The gateway way
   (`way_gateway_<parent>_<child>`) is emitted by whichever scope compiles second,
   so releasing a child without the parent present leaves an orphan, and
   re-materialising needs the parent's cell area to link against. Only a parent
   *this store* released blocks — a parent that was never materialised is the
   author's own doing and is not a reason to keep a zone resident.
3. **A ``baked`` zone is never released.** A baked zone compiles once and is
   hand-edited thereafter, so a release/re-materialise cycle would silently
   destroy the edits — the clobber trap
   (`docs/design/worldpainter-knowledge-and-fog.md`, task-496) wearing a
   different hat. A baked zone is a permanent graph citizen.
4. **A zone with hand-authored nodes in it is not released** unless every
   non-generated node in it is one the compiler can rebuild. Same reason, found
   by inspection rather than by policy.

Refusing is the default. Anything that cannot be rebuilt is left alone, and
:meth:`ZoneStore.releasable` is the query a caller asks before assuming a zone
can go.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

UNMADE = "unmade"
MATERIALIZED = "materialized"
RELEASED = "released"

#: A way the compiler mints to link a placed child to its parent's cell
#: (task-496). Both ends have to exist for it to mean anything.
GATEWAY_PREFIX = "way_gateway_"


def is_generated(node: Any) -> bool:
    """True when the compiler produced this node and can produce it again."""
    props = getattr(node, "properties", None)
    if props is None and isinstance(node, dict):
        props = node
    return bool(isinstance(props, dict) and props.get("generated"))


def generated_scope_id(node: Any) -> str:
    props = getattr(node, "properties", None)
    if props is None and isinstance(node, dict):
        props = node
    generated = (props or {}).get("generated") or {}
    return str(generated.get("scope_id") or "")


def authored_scope_id(node: Any) -> str:
    """The scope a hand-placed node claims, via ``world_scope_id``."""
    props = getattr(node, "properties", None)
    if props is None and isinstance(node, dict):
        props = node
    if not isinstance(props, dict):
        return ""
    return str(props.get("world_scope_id") or "")


def scope_nodes(graph, scope_id: str) -> List[str]:
    """Node ids a release would remove: everything generated for *scope_id*.

    Both generators are included on purpose. A compiled grid's areas carry
    ``generated.scope_id``, and a hand-placed area that was *placed* on a cell
    carries ``world_scope_id``; a zone holding only the second kind would look
    empty and be released while still holding content.
    """
    out = []
    for node in graph.nodes.values():
        if getattr(node, "type", None) not in ("area", "way"):
            continue
        if (generated_scope_id(node) == scope_id
                or authored_scope_id(node) == scope_id):
            out.append(node.id)
    return sorted(out)


def _gateway_scopes(way_id: str) -> Tuple[str, str]:
    """``(parent, child)`` from a gateway way id, or empty strings."""
    if not str(way_id).startswith(GATEWAY_PREFIX):
        return "", ""
    rest = str(way_id)[len(GATEWAY_PREFIX):]
    parent, _sep, child = rest.partition("_")
    # The child id may itself contain underscores, so take the long side: the
    # parent is the shorter of the two non-empty halves and this is only ever
    # used to *check* linkage, never to reconstruct an id.
    return parent, child


class ReleaseRefused(ValueError):
    """A zone cannot be released, and says which rule stopped it."""


class ZoneStore:
    """Which zones are materialised, and materialise/release them on demand.

    *manifest* is the world scope manifest (``world_scopes``); *graph* is the
    runtime graph. *compile* is the one injection point that makes this testable
    and keeps a materialise/release cycle from importing the compiler implicitly:
    a caller passes the same callable it uses to build a zone in the first place.
    """

    def __init__(self, graph, manifest: Dict[str, dict],
                 compile_scope: Optional[Callable[[str], Any]] = None,
                 seed: Optional[str] = None):
        self.graph = graph
        self.manifest = manifest
        #: Injection point for tests and for a caller whose zones come from
        #: somewhere other than the painted manifest. ``None`` means the real
        #: compiler, which is what production wants.
        self._compile = compile_scope
        self.seed = seed
        #: Zones that were released and can be rebuilt: scope_id -> recipe seed.
        #: A released zone's record stays in the manifest the whole time, which
        #: is the point — the zone exists, it just is not a graph citizen.
        self.released: Dict[str, str] = {}

    # ── the query ────────────────────────────────────────────────────────

    def occupied_areas(self) -> Set[str]:
        """Area ids a live character is standing in.

        Deliberately derived from the graph rather than passed in, so the rule
        cannot be satisfied by a caller that forgot. An ``in`` edge from a
        character node is the only place "somebody is here" is recorded.
        """
        here = set()
        for node in self.graph.nodes.values():
            if getattr(node, "type", None) != "character":
                continue
            for edge in self.graph.get_edges_for_source(node.id, "in"):
                here.add(str(edge.target))
        return here

    def is_materialised(self, scope_id: str) -> bool:
        return bool(scope_nodes(self.graph, scope_id))

    def node_count(self) -> int:
        return len(self.graph.nodes)

    def unreleasable_handwork(self, scope_id: str) -> List[str]:
        """Hand-authored nodes in the zone the compiler would not rebuild.

        A zone holding any of these cannot be released, because a
        release/materialise cycle replaces them with the recipe's version and the
        edit is gone. A baked zone is the policy-level version of the same fact.
        """
        hand = []
        for node_id in scope_nodes(self.graph, scope_id):
            node = self.graph.get_node(node_id)
            if not is_generated(node):
                hand.append(node_id)
        return sorted(hand)

    def releasable(self, scope_id: str) -> Optional[str]:
        """Why this zone cannot be released, or None if it can.

        A single string rather than a list: the rules are ordered and the first
        one that fires is the one a caller needs to hear, because fixing an
        occupied zone does not help if the zone is also baked.
        """
        record = self.manifest.get(scope_id)
        if record is None:
            return f"no such scope {scope_id!r}"
        if record.get("paint_policy") == "baked":
            return ("scope is baked: it compiles once and is hand-edited "
                    "afterwards, so a release would destroy the edits")
        if not self.is_materialised(scope_id):
            return "already released"
        occupied = self.occupied_areas() & set(scope_nodes(self.graph, scope_id))
        if occupied:
            return (f"{len(occupied)} area(s) have a character in them: "
                    f"{', '.join(sorted(occupied)[:3])}")
        parent = record.get("parent_id")
        if (parent and str(parent) in self.released
                and not self.is_materialised(parent)):
            # Only a parent **this store released** blocks. A parent that was
            # never materialised is the author's own doing — the zone compiled
            # anyway — and refusing on that would make the rule fire on every
            # scope whose parent has no grid of its own, which is a normal
            # authoring shape and not a reason to keep a zone resident.
            return (f"parent {parent!r} was released, so this zone's gateway "
                    "has nothing to link to")
        hand = self.unreleasable_handwork(scope_id)
        if hand:
            return (f"{len(hand)} hand-authored node(s) the compiler would not "
                    f"rebuild: {', '.join(hand[:3])}")
        return None

    # ── the actions ──────────────────────────────────────────────────────

    def release(self, scope_id: str, *, force: bool = False) -> Dict[str, Any]:
        """Drop a zone's generated nodes, keeping its scope record.

        Returns what was removed so a caller can log or assert on it. Refuses
        by default; ``force`` exists for an author who has just exported, and
        says so in the returned report.

        Releasing an already-released zone is a **no-op, not an error**, for the
        same reason the scope-id migration treats a re-run as success: a second
        release is the normal way to confirm the first took, and raising there
        teaches callers to ignore the result.
        """
        if not self.is_materialised(scope_id):
            return {"scope_id": scope_id, "removed": [], "count": 0,
                    "forced": False, "refused_because": None,
                    "already": True}
        reason = self.releasable(scope_id)
        if reason and not force:
            raise ReleaseRefused(f"cannot release {scope_id!r}: {reason}")

        doomed = set(scope_nodes(self.graph, scope_id))
        seeds = set()
        for node_id in doomed:
            node = self.graph.get_node(node_id)
            generated = ((getattr(node, "properties", None) or {})
                         .get("generated") or {})
            if generated.get("seed") is not None:
                seeds.add(str(generated["seed"]))
        record = self.manifest.get(scope_id) or {}

        # The seed comes from the NODES, not from what this store was configured
        # with. `compile_grid` mints its own default (`<scope>:grid.v2`) when it is
        # given none, so a store-level seed is a guess and a rebuild on a guessed
        # seed produces a *different* zone wearing the old one's name — which is
        # worse than not rebuilding at all.
        ambiguous_seed = sorted(seeds) if len(seeds) > 1 else None
        if len(seeds) == 1:
            self.released[str(scope_id)] = seeds.pop()
        else:
            self.released[str(scope_id)] = str(
                record.get("generated_seed") or self.seed or "")

        for node_id in doomed:
            self.graph.remove_node(node_id)
        record["state"] = RELEASED
        # `area_ids` is the zone's inventory, not its graph membership. Keeping
        # it is what lets a rebuild be checked against what used to be there.
        return {
            "scope_id": scope_id,
            "removed": sorted(doomed),
            "count": len(doomed),
            "forced": bool(reason),
            "refused_because": reason,
            "already": False,
            "seed": self.released.get(str(scope_id)),
            # Set when the zone was not built from one seed, so a rebuild cannot be
            # trusted to match. Reported rather than guessed.
            "ambiguous_seed": ambiguous_seed,
        }

    def materialise(self, scope_id: str) -> Dict[str, Any]:
        """Rebuild a released zone by re-running its recipe.

        ``paint_policy`` is respected the same way ``apply_patch`` respects it:
        a canonical zone is reproducible, a baked one is not, so a baked zone is
        refused here too rather than silently regenerated from paint that no
        longer matches the hand edits.
        """
        record = self.manifest.get(scope_id)
        if record is None:
            raise ReleaseRefused(f"no such scope {scope_id!r}")
        if record.get("paint_policy") == "baked":
            raise ReleaseRefused(
                f"cannot materialise {scope_id!r}: a baked zone is not "
                "reproducible from its paint")
        if self.is_materialised(scope_id):
            return {"scope_id": scope_id, "added": [], "count": 0,
                    "already": True}

        from engine import generation
        from engine import world_compile

        seed = self.released.get(str(scope_id)) or self.seed
        tick = 0
        for node in self.graph.nodes.values():
            generated = (getattr(node, "properties", None) or {}).get("generated") or {}
            tick = max(tick, int(generated.get("generated_at_tick") or 0))
        if self._compile is not None:
            patch = self._compile(scope_id)
        else:
            # The default is the real compiler rather than a refusal: a store
            # built in production should just work, and the injection point
            # exists for tests, not as a licence to have no behaviour.
            patch = world_compile.compile_grid(
                self.manifest, scope_id, seed=seed, tick=tick)
        generation.apply_patch(self.graph, self.manifest, patch,
                              allow_regenerate=True)
        self.released.pop(str(scope_id), None)
        return {"scope_id": scope_id,
                "added": sorted(n.id for n in patch.nodes),
                "count": len(patch.nodes),
                "already": False}

    def approach(self, scope_id: str) -> Dict[str, Any]:
        """Materialise a zone because somebody is going there. Idempotent."""
        if self.is_materialised(scope_id):
            return {"scope_id": scope_id, "added": [], "count": 0, "already": True}
        return self.materialise(scope_id)

    def materialised_scopes(self) -> List[str]:
        return sorted(
            scope_id for scope_id in self.manifest
            if self.is_materialised(scope_id)
        )

    def released_scopes(self) -> List[str]:
        return sorted(s for s in self.released if not self.is_materialised(s))
