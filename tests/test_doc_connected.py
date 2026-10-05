"""Tests for tools/doc_connected.py — the `## Connected` block and its section links.

Two mechanisms are worth pinning. The block must be *regenerable*: `--apply`
replaces exactly what it wrote and never a human's prose, which is what makes it
safe to re-run after any Feature Map or task move. And `SECTION_REFS` is a
hand-maintained table, so a renamed heading would otherwise turn a section link
into a promise that lands at the top of a page — that has to be a guard failure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import doc_connected

VAULT = Path("docs/virtualWorld")


def test_section_refs_all_point_at_a_heading_that_exists():
    broken = [(src, target, heading) for src, target, heading in doc_connected.SECTION_REFS
              if not doc_connected.heading_exists(target, heading)]
    assert broken == [], broken


def test_section_refs_are_symmetric_where_they_claim_to_be():
    pairs = {(src, target, heading) for src, target, heading in doc_connected.SECTION_REFS}
    for src, target, heading in pairs:
        back = [p for p in pairs if p[0] == target]
        assert back, f"{src} -> [[{target}#{heading}]] has no return link"


def test_render_only_rewrites_the_block_it_wrote(tmp_path):
    path = tmp_path / "Note.md"
    path.write_text("# Note\n\nhuman prose\n", encoding="utf-8")
    block = doc_connected.render(path, {"Note": [(7, "Thing")]}, {}, {})
    text = path.read_text(encoding="utf-8") + "\n" + block + "\n"
    again = doc_connected.render(path, {"Note": [(7, "Thing")]}, {}, {})
    assert text.replace(block, again) == text, "--apply must be idempotent"
    assert "human prose" in text


def test_a_curated_note_with_no_block_fails_the_check(tmp_path, monkeypatch):
    note = tmp_path / "Note.md"
    note.write_text("# Note\n", encoding="utf-8")
    monkeypatch.setattr(doc_connected, "curated_docs", lambda: [note])
    monkeypatch.setattr(doc_connected, "VAULT", tmp_path)
    # features/tasks/code are real, so "Memory System" below is a real Feature Map
    # row target: this note has a relation and must therefore carry a block.
    monkeypatch.setattr(doc_connected, "features_by_doc",
                        lambda: {"Note": [(1, "Memory")]})
    monkeypatch.setattr(doc_connected, "tasks_by_doc", lambda: {})
    monkeypatch.setattr(doc_connected, "code_by_doc", lambda: {})
    # The SECTION_REFS audit looks under VAULT, which is a tmp dir here; it has its
    # own test against the real vault and would otherwise drown this one.
    monkeypatch.setattr(doc_connected, "heading_exists", lambda *_: True)
    assert doc_connected.check() == 1


def test_a_note_with_no_relation_gets_no_block_at_all(tmp_path, monkeypatch):
    # An empty `## Connected` claims a check that never happened.
    note = tmp_path / "Lonely.md"
    note.write_text("# Lonely\n", encoding="utf-8")
    assert doc_connected.render(note, {}, {}, {}) == ""
    monkeypatch.setattr(doc_connected, "curated_docs", lambda: [note])
    monkeypatch.setattr(doc_connected, "VAULT", tmp_path)
    monkeypatch.setattr(doc_connected, "features_by_doc", lambda: {})
    monkeypatch.setattr(doc_connected, "tasks_by_doc", lambda: {})
    monkeypatch.setattr(doc_connected, "code_by_doc", lambda: {})
    monkeypatch.setattr(doc_connected, "heading_exists", lambda *_: True)
    assert doc_connected.check() == 0


def test_every_connected_block_on_the_real_vault_matches_a_real_relation():
    # Both directions: a note with a relation and no block, and a block on a
    # note that has none. `check()` is the gate; this is the same rule stated as
    # a test so a failure names the file.
    features, tasks, code = (doc_connected.features_by_doc(), doc_connected.tasks_by_doc(),
                             doc_connected.code_by_doc())
    problems = []
    for path in doc_connected.curated_docs():
        if path.parent == doc_connected.FEATURES:
            continue
        expected = doc_connected.render(path, features, tasks, code)
        has_block = doc_connected.START in path.read_text(encoding="utf-8")
        if bool(expected) != has_block:
            problems.append(f"{path.name}: expected block={bool(expected)}, found={has_block}")
    assert problems == [], problems[:10]


def test_the_real_connected_blocks_carry_a_real_relation():
    # A block with nothing in it is worse than no block: it says "connected"
    # and means "we did not check".
    empty = []
    for path in doc_connected.curated_docs():
        if path.parent == doc_connected.FEATURES:
            continue
        text = path.read_text(encoding="utf-8")
        if doc_connected.START not in text:
            continue
        block = text.split(doc_connected.START, 1)[1].split(doc_connected.END, 1)[0]
        if not any(h in block for h in ("**Read next**", "**Features**", "**Dev tasks**",
                                        "**Code**", "**Neighbouring notes**")):
            empty.append(path.name)
    assert empty == [], empty
