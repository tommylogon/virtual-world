"""Tests for tools/feature_pages.py — every Feature Map row has a page.

The mechanism this proves: the row is the denominator, a page is derived from
it, and the three ways the join rots (a row with no page, a page whose sections
were deleted, a page whose ``feature_id`` drifted from its row) are all caught.
The last test runs against the real Feature Map, which is the only assertion
that proves the vault is actually covered.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import feature_pages
from tools.feature_index import parse_features

ROOT = Path(__file__).parent.parent
FEATURES_DIR = ROOT / "docs" / "virtualWorld" / "Features"


# ── the pure parts ────────────────────────────────────────────────────────


def test_slug_is_the_link_stable_id():
    assert feature_pages.slug("Take / drop / give") == "take-drop-give"
    assert feature_pages.slug("The **sky**") == "the-sky"


def test_status_word_reads_a_cell_with_a_reason():
    assert feature_pages.status_word("**unwired** — because nothing calls it") == "unwired"
    assert feature_pages.status_word("wired") == "wired"
    assert feature_pages.status_word("") == "planned"


def test_docs_links_splits_aliases_and_none():
    assert feature_pages.docs_links("[[Rooms & Areas]]") == ["Rooms & Areas"]
    assert feature_pages.docs_links("[[Memory System\\|Memory]]") == ["Memory System"]
    assert feature_pages.docs_links("none") == []


def test_section_key_routes_a_row_to_its_table():
    assert feature_pages.section_key("In a game") == "in-game"
    assert feature_pages.section_key("In the editor") == "in-editor"


# ── the guard ─────────────────────────────────────────────────────────────


def _audit_against(monkeypatch, rows, pages):
    """Run the real ``audit`` over a fake map and a fake Features/ folder."""
    monkeypatch.setattr(feature_pages, "parse_features", lambda: rows)
    monkeypatch.setattr(feature_pages, "FEATURES_DIR", pages)
    problems, features, _count = feature_pages.audit()
    return problems, features


def _row(n, label, section="In a game", docs="[[Deep Note]]", status="wired"):
    return {"n": n, "label": label, "section": section, "docs": docs,
            "status": status, "what": "do the thing"}


def _write_page(pages: Path, row, body=None):
    target = pages / f"{feature_pages.slug(row['label'])}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body if body is not None else feature_pages.render_page(
        row, [], "2026-10-05"), encoding="utf-8")
    return target


def test_a_row_without_a_page_is_a_problem(monkeypatch, tmp_path):
    rows = [_row(1, "Alpha"), _row(2, "Beta")]
    pages = tmp_path / "Features"
    _write_page(pages, rows[0])
    (pages / "Features Overview.md").write_text("[[alpha]]\n", encoding="utf-8")
    problems, _ = _audit_against(monkeypatch, rows, pages)
    assert any("row 2" in p and "no page" in p for p in problems), problems


def test_a_page_missing_a_required_section_is_a_problem(monkeypatch, tmp_path):
    rows = [_row(1, "Alpha")]
    pages = tmp_path / "Features"
    body = feature_pages.render_page(rows[0], [], "2026-10-05").replace("## Where it lives", "## Elsewhere")
    _write_page(pages, rows[0], body)
    (pages / "Features Overview.md").write_text("[[alpha]]\n", encoding="utf-8")
    problems, _ = _audit_against(monkeypatch, rows, pages)
    assert any("Where it lives" in p for p in problems), problems


def test_a_page_whose_feature_id_drifted_is_a_problem(monkeypatch, tmp_path):
    rows = [_row(7, "Alpha")]
    pages = tmp_path / "Features"
    body = feature_pages.render_page(rows[0], [], "2026-10-05").replace("feature_id: 7", "feature_id: 6")
    _write_page(pages, rows[0], body)
    (pages / "Features Overview.md").write_text("[[alpha]]\n", encoding="utf-8")
    problems, _ = _audit_against(monkeypatch, rows, pages)
    assert any("feature_id does not match row 7" in p for p in problems), problems


def test_a_page_with_no_row_behind_it_is_a_problem(monkeypatch, tmp_path):
    rows = [_row(1, "Alpha")]
    pages = tmp_path / "Features"
    _write_page(pages, rows[0])
    _write_page(pages, _row(99, "Ghost"))
    (pages / "Features Overview.md").write_text("[[alpha]] [[ghost]]\n", encoding="utf-8")
    problems, _ = _audit_against(monkeypatch, rows, pages)
    assert any("no Feature Map row behind it" in p for p in problems), problems


def test_scaffold_never_overwrites_prose(monkeypatch, tmp_path):
    rows = [_row(1, "Alpha")]
    pages = tmp_path / "Features"
    pages.mkdir(parents=True)
    existing = pages / "alpha.md"
    existing.write_text("# Alpha\n\nhand written\n", encoding="utf-8")
    monkeypatch.setattr(feature_pages, "parse_features", lambda: rows)
    monkeypatch.setattr(feature_pages, "FEATURES_DIR", pages)
    assert feature_pages.scaffold(today="2026-10-05") == 0
    assert existing.read_text(encoding="utf-8") == "# Alpha\n\nhand written\n"


def test_the_overview_must_list_every_feature(monkeypatch, tmp_path):
    # The front door: a folder of 76 pages with no index is 76 islands.
    rows = [_row(1, "Alpha"), _row(2, "Beta")]
    pages = tmp_path / "Features"
    for row in rows:
        _write_page(pages, row)
    (pages / "Features Overview.md").write_text("[[alpha]]\n", encoding="utf-8")
    problems, _ = _audit_against(monkeypatch, rows, pages)
    assert any("does not list 'Beta'" in p for p in problems), problems


# ── the real vault ────────────────────────────────────────────────────────


def test_every_feature_map_row_has_a_page_on_the_real_map():
    rows = parse_features()
    problems, _features, page_count = feature_pages.audit()
    assert problems == [], problems[:10]
    assert page_count == len(rows) == 76, (page_count, len(rows))


def test_feature_pages_are_reachable_from_the_map_and_the_index():
    # An orphan page passes `audit` (it has a row) yet is invisible in Obsidian's
    # graph — the two guards together are what "connected" means.
    from tools import doc_links

    vault = Path("docs/virtualWorld")  # relative: doc_links keys its counts the same way
    counts = doc_links.inbound_counts(vault)
    unreached = [p.name for p in sorted((vault / "Features").glob("*.md"))
                 if p.stem != "Features Overview" and counts.get(p, 0) == 0]
    assert unreached == [], unreached
