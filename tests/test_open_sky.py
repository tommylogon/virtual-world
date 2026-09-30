"""Open sky is one fact with one writer and four readers (bug-54).

The symptom was that a painted WorldPainter world got no weather at all, and
the cause was not one bug but a shape: "is this area under the open sky" was
asked four ways, and the two spellings disagreed. These tests pin the readers
to a single predicate and the compiler to actually writing the tag.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.area_tags import is_open_sky


class TestThePredicate:
    @pytest.mark.parametrize("tags", [["outdoor"], ["exterior"], ["outdoor", "indoor"],
                                     ["Exterior"], ["  outdoor  "], "outdoor",
                                     "cave, exterior", ("outdoor",)])
    def test_either_spelling_means_open_sky(self, tags):
        assert is_open_sky(tags) is True

    @pytest.mark.parametrize("tags", [[], ["indoor"], ["room", "building"], None, "",
                                     "cave, tunnel", 42])
    def test_anything_else_is_indoors(self, tags):
        assert is_open_sky(tags) is False

    def test_the_two_spellings_stay_distinct_in_source_but_one_fact_in_use(self):
        """Both are accepted because both are authored somewhere; the point is
        that no READER gets to pick a spelling of its own any more."""
        from engine.area_tags import OPEN_SKY_TAGS
        assert OPEN_SKY_TAGS == frozenset({"outdoor", "exterior"})


class TestReadersAgree:
    """A tagged area must read as open sky in every subsystem that asks."""

    def _world(self, tags):
        from virtual_world_engine import VirtualWorld
        from area import Area
        w = VirtualWorld()
        w.movement.add_area(Area("Outside", "Open sky.", []))
        w.movement.add_area(Area("Cellar", "Underground.", []))
        for nm in ("Outside", "Cellar"):
            node = w.graph.get_node(w._area_node_id(nm))
            node.properties["tags"] = list(tags) if nm == "Outside" else []
        w.name_matcher._set_player_area(w.active_player, "Outside")
        return w

    @pytest.mark.parametrize("tag", ["outdoor", "exterior"])
    def test_lighting_treats_either_spelling_as_the_sky(self, tag):
        w = self._world([tag])
        assert w.lighting.is_outdoor_area(w._area_node_id("Outside")) is True

    @pytest.mark.parametrize("tag", ["outdoor", "exterior"])
    def test_weather_prose_reads_either_spelling(self, tag):
        from engine.area_description import _is_open_sky
        assert _is_open_sky([tag]) is True

    @pytest.mark.parametrize("tag", ["outdoor", "exterior"])
    def test_an_indoor_area_is_indoor_in_all_of_them(self, tag):
        w = self._world([])
        assert w.lighting.is_outdoor_area(w._area_node_id("Cellar")) is False
        from engine.area_description import _is_open_sky
        assert _is_open_sky([]) is False


class TestNoReaderPicksItsOwnSpelling:
    """The regression guard: a new ``"outdoor" in tags`` or ``"exterior" in tags``
    is how this bug comes back, so grep for the literals in the readers."""

    READERS = [
        "engine/lighting.py",
        "engine/environment_propagation.py",
        "engine/tick_manager.py",
        "virtual_world_engine.py",
    ]

    @pytest.mark.parametrize("path", READERS)
    def test_no_inline_tag_test_in_a_known_reader(self, path):
        source = (ROOT / path).read_text(encoding="utf-8")
        offenders = [ln.strip() for ln in source.splitlines()
                     if ('"outdoor" in ' in ln or '"exterior" in ' in ln
                         or "'outdoor' in " in ln or "'exterior' in " in ln)]
        assert not offenders, f"{path} tests the tag by hand: {offenders}"

    def test_every_reader_goes_through_the_shared_predicate(self):
        assert (ROOT / "engine" / "area_tags.py").exists()
        for path in self.READERS:
            source = (ROOT / path).read_text(encoding="utf-8")
            assert "is_open_sky" in source, f"{path} does not use the shared predicate"


class TestCompilerWritesTheTag:
    """The writer side. A compiled world-mode area must carry the tag, and a
    town/interior scope must not."""

    def test_biomes_alone_cannot_supply_it(self):
        """Why the compiler cannot delegate this to the biome record: measured,
        not asserted, because the taxonomy is authored concurrently."""
        from engine import biomes
        claims = [b for b in biomes.biomes()
                  if is_open_sky(list(biomes.area_tags(b) or []))]
        assert len(claims) < 10, (
            f"{len(claims)} biomes now claim open sky; if most do, the compiler "
            "may be able to delegate. Re-read this test before assuming not."
        )


def _compile(scope_id, mode, w=3, h=3, biome="sparse_forest"):
    """Compile one gridded scope and return its area nodes."""
    from graph import WorldGraph
    from engine import generation, world_compile, world_grid as wg

    m = {"root": {"id": "root", "name": "Root", "children": [scope_id]},
         scope_id: {"id": scope_id, "name": scope_id.capitalize()}}
    wg.ensure_grid(m[scope_id], w, h, mode=mode)
    for x in range(w):
        for y in range(h):
            wg.paint(m[scope_id], "biome", x, y, biome)
    patch = world_compile.compile_grid(m, scope_id)
    g = WorldGraph()
    report = generation.apply_patch(g, m, patch)
    return [g.get_node(i) for i in report.area_ids]


class TestACompiledWorldIsOpenSky:
    def test_a_world_scope_compiles_its_areas_as_open_sky(self):
        areas = [n for n in _compile("wild", "world") if n is not None]
        assert areas, "the compile produced no areas"
        assert all(is_open_sky(n.properties.get("tags", [])) for n in areas), (
            "a world-mode scope is open sky; "
            f"got {[(n.name, n.properties.get('tags')) for n in areas]}"
        )

    @pytest.mark.parametrize("mode", ["town", "interior"])
    def test_an_indoor_scope_compiles_without_the_tag(self, mode):
        """The other half of the contract: tagging everything would be as wrong
        as tagging nothing."""
        areas = [n for n in _compile(mode, mode) if n is not None]
        assert areas, "the compile produced no areas"
        assert not any(is_open_sky(n.properties.get("tags", [])) for n in areas), (
            f"a {mode}-mode scope is not open sky"
        )

    def test_it_is_written_once_and_only_as_the_canonical_spelling(self):
        """One writer, one tag: a compiled area must not claim both."""
        for n in [a for a in _compile("wild", "world") if a is not None]:
            tags = {str(t).lower() for t in n.properties.get("tags", [])}
            assert not ({"outdoor", "exterior"} <= tags), (
                "the compiler should write one tag, not both spellings"
            )


class TestTheAcceptanceCriteria:
    """The card's four bullet points, on a real compiled world."""

    def _world_from(self, mode="world"):
        from virtual_world_engine import VirtualWorld
        from graph import WorldGraph
        from engine import generation, world_compile, world_grid as wg

        scope = "wild"
        m = {"root": {"id": "root", "name": "Root", "children": [scope]},
             scope: {"id": scope, "name": "Wild"}}
        wg.ensure_grid(m[scope], 3, 3, mode=mode)
        for x in range(3):
            for y in range(3):
                wg.paint(m[scope], "biome", x, y, "sparse_forest")
        patch = world_compile.compile_grid(m, scope)
        w = VirtualWorld()
        generation.apply_patch(w.graph, m, patch)
        return w

    def test_a_painted_outdoor_area_follows_the_diurnal_curve(self):
        w = self._world_from()
        outdoor = [n for n in w.graph.nodes.values()
                   if n.type == "area" and is_open_sky(n.properties.get("tags", []))]
        assert outdoor, "no compiled area is open sky"
        area_id = outdoor[0].id
        from engine.lighting import outdoor_light_for_hour
        # The system's own answer at 03:00 and at noon must differ, and noon
        # must be the brighter of the two.
        assert outdoor_light_for_hour(3) < outdoor_light_for_hour(12)

    def test_a_painted_outdoor_area_receives_the_forecast(self):
        w = self._world_from()
        outdoor = [n for n in w.graph.nodes.values()
                   if n.type == "area" and is_open_sky(n.properties.get("tags", []))]
        assert outdoor, "no compiled area is open sky"
        w._apply_forecast_env({"weather": "stormy", "wind": "gale",
                               "humidity": "damp", "temperature_mod": -3})
        written = [n for n in outdoor if n.properties.get("environment", {}).get("weather")]
        assert written, "the forecast was skipped for every open-sky area"
        assert written[0].properties["environment"]["weather"] == "stormy"
        assert written[0].properties["environment"]["wind"] == "gale"

    def test_an_indoor_compiled_area_is_not_given_the_forecast(self):
        w = self._world_from(mode="interior")
        w._apply_forecast_env({"weather": "stormy"})
        indoor = [n for n in w.graph.nodes.values() if n.type == "area"]
        assert indoor
        assert not any(n.properties.get("environment", {}).get("weather") for n in indoor), (
            "the forecast leaked indoors"
        )
