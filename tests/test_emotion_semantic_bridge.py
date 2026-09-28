"""The embedding bridge for novel emotion labels (task-505).

A creative LLM says "flibbertigibbet-forlorn" and the curated keyword map has
never heard of it, so the feeling used to be dropped on the floor. The bridge
resolves it to the nearest affect dimension by embedding it and comparing it
against one anchor phrase per dimension.

The embedder is injected everywhere, so these tests never load a real model and
never touch the network. The default gate matters as much as the happy path: with
``emotion.semantic_labels`` off, an unrecognised label must stay a dict lookup
and a graceful no-op.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from engine import emotion as em
from engine.runtime_config import config as runtime_config


#: Anchor phrase -> its dimension, so a fake embedder can give every anchor a
#: distinct axis and a query a *different* one. Without this the anchors
# collapse onto a single axis and every label "matches" the first dimension.
ANCHOR_TO_DIM = {phrase: dim for dim, phrase in em.DIM_ANCHORS.items()}


class FakeEmbedder:
    """Orthogonal one-hot vectors, so a match is exact and never accidental.

    Each anchor phrase gets its own axis. A query gets the axis named by
    ``meaning``; a ``far`` embedder spreads the query thin over many axes
    instead, which cosines below the similarity floor against everything.
    """

    WIDTH = 1000

    def __init__(self, meaning=None, far=False, fail=False):
        self.meaning = meaning
        self.far = far
        self.fail = fail
        self.calls = 0

    @staticmethod
    def _one_hot(dim):
        vec = [0.0] * FakeEmbedder.WIDTH
        vec[list(em.DIM_ANCHORS).index(dim)] = 1.0
        return vec

    def _vector(self, phrase):
        if phrase in ANCHOR_TO_DIM:
            return self._one_hot(ANCHOR_TO_DIM[phrase])
        if self.far:
            return [1.0] * self.WIDTH
        return self._one_hot(self.meaning) if self.meaning else [0.0] * self.WIDTH

    def __call__(self, texts):
        self.calls += 1
        if self.fail:
            raise RuntimeError("no embedding provider configured")
        if isinstance(texts, str):
            return self._vector(texts)
        return [self._vector(t) for t in texts]


def _set_semantic_labels(value):
    """runtime_config has no public setter; the store is the documented one."""
    runtime_config._values["emotion.semantic_labels"] = value


@pytest.fixture(autouse=True)
def _clean():
    em.reset_anchor_cache()
    yield
    em.reset_anchor_cache()
    _set_semantic_labels(False)


# ── the gate ──

class TestSemanticGate:

    def test_off_by_default(self):
        assert runtime_config.get("emotion.semantic_labels") is False
        assert em.semantic_labels_enabled() is False

    def test_off_means_the_default_provider_is_never_reached(self):
        """The gate governs automatic provider use, not an injected embedder."""
        original = em._default_embed

        def explode(texts):  # pragma: no cover - must never run
            raise AssertionError("the default provider was reached with the gate off")

        try:
            em._default_embed = explode
            assert em.map_label("flibbertigibbet-forlorn") == []
            assert em.resolve_label_semantic("flibbertigibbet-forlorn") is None
        finally:
            em._default_embed = original

    def test_off_keeps_felt_from_llm_dropping_an_unknown(self):
        assert em.felt_from_llm({"label": "flibbertigibbet-forlorn", "intensity": 6}) is None

    def test_keyword_path_never_needs_the_gate(self):
        assert em.map_label("happy") == [("happy", 1.0)]
        assert em.map_label("terrified") == [("afraid", 1.0)]
        assert em.felt_from_llm({"label": "afraid", "intensity": 10}) == ("afraid", 15.0)


# ── resolution ──

class TestSemanticResolution:

    def test_novel_label_lands_on_a_real_dimension(self):
        embedder = FakeEmbedder(meaning="afraid")
        assert em.map_label("flibbertigibbet-forlorn", embed_fn=embedder) == [("afraid", 1.0)]

    def test_a_distant_label_stays_unresolved(self):
        """A near-zero best match is noise, not a meaning."""
        embedder = FakeEmbedder(far=True)
        assert em.map_label("qwertyuiop", embed_fn=embedder) == []

    def test_resolution_is_never_an_invented_dimension(self):
        embedder = FakeEmbedder(meaning="not-a-real-dimension")
        for dim, _ in em.map_label("novel", embed_fn=embedder):
            assert dim in em.BASELINES

    def test_the_keyword_path_wins_over_the_semantic_one(self):
        """Semantic resolution is a last resort, never an override.

        The embedder is rigged to answer "happy", so anything the keyword map can
        answer itself proves the embedder was never consulted.
        """
        embedder = FakeEmbedder(meaning="happy")
        assert em.map_label("happy", embed_fn=embedder) == [("happy", 1.0)]
        assert em.map_label("frighten", embed_fn=embedder) == [("afraid", 1.0)]
        assert em.map_label("terrified", embed_fn=embedder) == [("afraid", 1.0)]
        # ...and a label nothing knows falls through to the embedder
        assert em.map_label("zibberflump", embed_fn=embedder) == [("happy", 1.0)]

    def test_blank_label_resolves_to_nothing(self):
        assert em.map_label("", embed_fn=FakeEmbedder(meaning="afraid")) == []
        assert em.map_label("   ", embed_fn=FakeEmbedder(meaning="afraid")) == []
        assert em.resolve_label_semantic(None, embed_fn=FakeEmbedder(meaning="afraid")) is None


# ── the LLM feeling path ──

class TestFeltFromLLM:

    def test_novel_label_is_no_longer_dropped(self):
        embedder = FakeEmbedder(meaning="melancholic")
        assert em.felt_from_llm(
            {"label": "zibberflump", "intensity": 10},
            embed_fn=embedder) == ("melancholic", 15.0)

    def test_intensity_still_scales_the_spike(self):
        embedder = FakeEmbedder(meaning="afraid")
        assert em.felt_from_llm({"label": "snarfleblot", "intensity": 5},
                                embed_fn=embedder) == ("afraid", 7.5)

    def test_zero_intensity_is_still_nothing(self):
        embedder = FakeEmbedder(meaning="afraid")
        assert em.felt_from_llm({"label": "snarfleblot", "intensity": 0},
                                embed_fn=embedder) is None

    def test_unresolvable_label_is_still_nothing(self):
        embedder = FakeEmbedder(far=True)
        assert em.felt_from_llm({"label": "qwertyuiop", "intensity": 8},
                                embed_fn=embedder) is None

    def test_malformed_input_is_still_nothing(self):
        embedder = FakeEmbedder(meaning="afraid")
        assert em.felt_from_llm(None, embed_fn=embedder) is None
        assert em.felt_from_llm("happy", embed_fn=embedder) is None
        assert em.felt_from_llm({"intensity": 5}, embed_fn=embedder) is None
        assert em.felt_from_llm({"label": "novel"}, embed_fn=embedder) is None
        assert em.felt_from_llm({"label": "novel", "intensity": "lots"},
                                embed_fn=embedder) is None

    def test_a_substring_coincidence_is_still_rejected(self):
        """The LLM path gets the semantic bridge or nothing, never map_label.

        "hangry" contains "angry", so the recall path's substring fallback
        resolves it. A declared feeling is deliberate, so it must not be
        answered by luck: with an embedder that resolves nothing, the LLM path
        has to return None even though map_label would have matched.
        """
        assert "angry" in "hangry"                              # the coincidence
        assert em.map_label("hangry") == [("angry", 1.0)]      # recall path: substring
        assert em.felt_from_llm(                                 # LLM path: not substring
            {"label": "hangry", "intensity": 8},
            embed_fn=FakeEmbedder(far=True)) is None
        # and with no provider at all, which is the shipped default
        assert em.felt_from_llm({"label": "hangry", "intensity": 8}) is None

    def test_an_explicit_max_intensity_still_wins(self):
        embedder = FakeEmbedder(meaning="afraid")
        assert em.felt_from_llm({"label": "snarfleblot", "intensity": 10},
                                max_intensity=4.0, embed_fn=embedder) == ("afraid", 4.0)


# ── provider failure is never fatal ──

class TestProviderFailure:

    def test_a_raising_embedder_resolves_to_nothing(self):
        assert em.map_label("novel", embed_fn=FakeEmbedder(fail=True)) == []
        assert em.felt_from_llm({"label": "novel", "intensity": 5},
                                embed_fn=FakeEmbedder(fail=True)) is None

    def test_the_default_provider_is_only_tried_once(self):
        """No embedding model must cost one attempt, not one per label."""
        em.reset_anchor_cache()
        calls = []

        def flaky(texts):
            calls.append(texts)
            raise RuntimeError("sentence-transformers is not installed")

        _set_semantic_labels(True)
        # the default provider is the only one whose failure is remembered
        original = em._default_embed
        try:
            em._default_embed = flaky
            em.map_label("first-novel-label")
            em.map_label("second-novel-label")
            em.map_label("third-novel-label")
        finally:
            em._default_embed = original
        assert len(calls) == 1

    def test_a_caller_supplied_embed_fn_is_retried_not_remembered(self):
        """A caller's own embedder keeps its own failures — not memoised away."""
        attempts = []

        def flaky(texts):
            attempts.append(texts)
            raise RuntimeError("transient")

        assert em.map_label("first", embed_fn=flaky) == []
        assert em.map_label("second", embed_fn=flaky) == []
        assert len(attempts) == 2

    def test_a_zero_vector_from_a_failed_model_is_not_a_match(self):
        """embeddings.embed returns a zero vector on failure; that is not 'dim 0'."""
        def zeroed(texts):
            if isinstance(texts, str):
                return [0.0] * 8
            return [[0.0] * 8 for _ in texts]

        assert em.map_label("novel", embed_fn=zeroed) == []

    def test_anchors_are_embedded_once_and_reused(self):
        embedder = FakeEmbedder(meaning="afraid")
        em.map_label("zibberflump", embed_fn=embedder)
        after_first = embedder.calls
        em.map_label("snarfleblot", embed_fn=embedder)
        # one batch for the anchors, one query per label, no second anchor batch
        assert embedder.calls == after_first + 1

    def test_mismatched_anchor_count_is_not_trusted(self):
        def short(texts):
            if isinstance(texts, str):
                return [1.0] * 8
            return [[1.0] * 8]          # one vector for 36 anchors

        assert em.map_label("novel", embed_fn=short) == []


# ── the two mappers must agree ──

class TestAnchorsMirrorTheBrowserMapper:

    def test_same_dimensions_as_the_js_mapper(self):
        js = Path(__file__).parent.parent / "static" / "js" / "shared" / "emotion-mapper.js"
        source = js.read_text(encoding="utf-8")
        for dim in em.DIM_ANCHORS:
            assert f"{dim}:" in source, f"{dim} is missing from emotion-mapper.js"

    def test_every_anchor_dimension_is_a_real_baseline(self):
        for dim in em.DIM_ANCHORS:
            assert dim in em.BASELINES, f"{dim} has an anchor but no baseline"
