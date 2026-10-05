"""Tests for tools/doc_tags.py — one closed vocabulary for the vault's tags.

The mechanism this proves: a tag set is only worth having when it is closed, and
the tags a note *should* carry are derived from where it lives and what it links
rather than typed by hand. Three things are worth guarding: the derivation is
stable, `--check` actually fails on a tag the list does not have, and applying
tags leaves a human's other frontmatter keys alone.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import doc_tags

ROOT = Path(__file__).parent.parent


def _derive(tmp_path: Path, monkeypatch, rel: str, body: str = ""):
    """``derive_tags`` reads the file from disk, so a fixture must be a real file.

    The vault root is redirected to ``tmp_path``: an earlier version of this
    helper pointed at the *real* ``docs/virtualWorld`` and overwrote two real
    notes with fixture text. Fixtures write to the filesystem — put them in the
    filesystem's throwaway part.
    """
    monkeypatch.setattr(doc_tags, "VAULT", tmp_path)
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return doc_tags.derive_tags(path)


def test_every_vocabulary_entry_is_namespaced():
    # A bare word is what made the tag pane useless: 70 of 75 tokens appeared once.
    for tag in doc_tags.vocabulary():
        namespace, _, name = tag.partition("/")
        assert namespace in ("system", "surface", "status", "topic"), tag
        assert name and " " not in name, tag


def test_read_tags_handles_both_frontmatter_shapes():
    assert doc_tags.read_tags("---\ntags: [a/b, c/d]\n---\n") == ["a/b", "c/d"]
    assert doc_tags.read_tags("---\ntags: a/b\n---\n") == ["a/b"]
    assert doc_tags.read_tags("# no frontmatter\n") == []
    assert doc_tags.read_tags("---\ntype: doc\n---\n") == []


def test_derivation_reads_the_folder_first(tmp_path, monkeypatch):
    tags = _derive(tmp_path, monkeypatch, "UI & Settings/Event Stream.md",
                   "---\ntype: doc\n---\n# Event Stream\n")
    assert "system/ui" in tags


def test_a_file_override_beats_its_folder():
    # Memory System lives in AI & Narration but documents system/memory.
    assert "system/memory" in doc_tags.derive_tags(
        ROOT / "docs" / "virtualWorld" / "AI & Narration" / "Memory System.md")


def test_a_feature_page_inherits_from_the_deep_doc_it_links(tmp_path, monkeypatch):
    body = (
        "---\ntype: feature\nstatus: wired\nsection: in-game\n---\n"
        "# Memory\n\n## How it works\n\n- [[Memory System]]\n\n"
        "## Connected\n\n- [[Feature Map]]\n")
    tags = _derive(tmp_path, monkeypatch, "Features/memory.md", body)
    assert "system/memory" in tags
    assert "status/wired" in tags and "surface/in-game" in tags
    # The Connected section links the Feature Map; inheriting from *that* would
    # tag every page in the folder as docs. This is the regression that guard is for.
    assert "system/docs" not in tags


def test_check_fails_on_a_tag_outside_the_vocabulary(tmp_path, monkeypatch):
    note = tmp_path / "Note.md"
    note.write_text("---\ntags: [system/ui, system/not-a-domain]\n---\n# N\n", encoding="utf-8")
    monkeypatch.setattr(doc_tags, "curated_docs", lambda: [note])
    monkeypatch.setattr(doc_tags, "VAULT", tmp_path)
    assert doc_tags.check() == 1


def test_check_fails_on_an_untagged_note(tmp_path, monkeypatch):
    note = tmp_path / "Note.md"
    note.write_text("# N\n", encoding="utf-8")
    monkeypatch.setattr(doc_tags, "curated_docs", lambda: [note])
    monkeypatch.setattr(doc_tags, "VAULT", tmp_path)
    assert doc_tags.check() == 1


def test_apply_preserves_other_frontmatter_keys(tmp_path, monkeypatch):
    note = tmp_path / "AI & Narration" / "Memory System.md"
    note.parent.mkdir(parents=True)
    note.write_text("---\ntype: doc\nstatus: draft\n---\n\n# Memory System\n", encoding="utf-8")
    monkeypatch.setattr(doc_tags, "curated_docs", lambda: [note])
    monkeypatch.setattr(doc_tags, "VAULT", tmp_path)
    assert doc_tags.apply_tags() == 1
    text = note.read_text(encoding="utf-8")
    assert "type: doc" in text and "status: draft" in text
    assert doc_tags.read_tags(text) == ["system/memory", "topic/memory-dynamics"]
    assert "# Memory System" in text, "the body must survive"


def test_apply_is_idempotent(tmp_path, monkeypatch):
    note = tmp_path / "Memory Dynamics.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("---\ntype: doc\n---\n\n# Memory Dynamics\n", encoding="utf-8")
    monkeypatch.setattr(doc_tags, "curated_docs", lambda: [note])
    monkeypatch.setattr(doc_tags, "VAULT", tmp_path)
    doc_tags.apply_tags()
    once = note.read_text(encoding="utf-8")
    assert doc_tags.apply_tags() == 0
    assert note.read_text(encoding="utf-8") == once


def test_the_real_vault_is_inside_the_vocabulary():
    # The regression that matters: 157 curated notes, every tag closed.
    problems = []
    untagged = []
    for path in doc_tags.curated_docs():
        tags = doc_tags.read_tags(path.read_text(encoding="utf-8"))
        if not tags:
            untagged.append(path.name)
        problems += [f"{path.name}: {t}" for t in tags if not doc_tags.known(t)]
    assert problems == [], problems[:10]
    assert untagged == [], untagged[:10]
    assert len(doc_tags.curated_docs()) == 157
