"""Tests for tools/doc_links.py — the vault [[wikilink]] resolver and repairer.

The mechanism this proves: how a target resolves (path, escaped-pipe alias,
basename, ambiguity), that code spans and fences are not links, and that the
task-move repair retargets by id **and** slug so a reused id is never mislinked.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import doc_links, tasks


def _note(vault: Path, rel: str, body: str = "") -> Path:
    p = vault / (rel if rel.endswith(".md") else rel + ".md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


# ── resolution ────────────────────────────────────────────────────────────


def test_vault_relative_path_resolves(tmp_path):
    v = tmp_path / "vault"
    _note(v, "Items & Inventory/Items Overview")
    assert doc_links.resolve("Items & Inventory/Items Overview",
                             doc_links.build_index(doc_links.iter_notes(v), v), v)


def test_escaped_pipe_alias_resolves(tmp_path):
    # The shape that made the original "143" wrong: a table alias.
    v = tmp_path / "vault"
    _note(v, "Items & Inventory/Items Overview")
    index = doc_links.build_index(doc_links.iter_notes(v), v)
    assert doc_links.resolve("Items & Inventory/Items Overview\\|Items Overview", index, v)


def test_basename_resolves_anywhere(tmp_path):
    v = tmp_path / "vault"
    _note(v, "Environment/Temperature System")
    index = doc_links.build_index(doc_links.iter_notes(v), v)
    assert doc_links.resolve("Temperature System", index, v)


def test_ambiguous_basename_does_not_resolve(tmp_path):
    v = tmp_path / "vault"
    _note(v, "Environment/Temperature System")
    _note(v, "Rules Engine/Temperature System")
    index = doc_links.build_index(doc_links.iter_notes(v), v)
    assert doc_links.resolve("Temperature System", index, v) is None
    # ...but the explicit path still does.
    assert doc_links.resolve("Environment/Temperature System", index, v)


def test_heading_and_md_suffix_are_ignored(tmp_path):
    v = tmp_path / "vault"
    _note(v, "A/Note")
    index = doc_links.build_index(doc_links.iter_notes(v), v)
    assert doc_links.resolve("A/Note#Section", index, v)
    assert doc_links.resolve("A/Note.md", index, v)


def test_code_span_and_fence_are_not_links(tmp_path):
    v = tmp_path / "vault"
    _note(v, "Real")
    _note(v, "Doc", "prose\n`[[Ghost]]`\n```\n[[Fenced]]\n```\n[[Real]]\n")
    broken = doc_links.broken_links(v)
    assert broken == [], broken


def test_folder_link_is_broken(tmp_path):
    v = tmp_path / "vault"
    _note(v, "Doc", "see [[dev_tasks/todo/]]\n")
    assert len(doc_links.broken_links(v)) == 1


# ── repair ────────────────────────────────────────────────────────────────


def test_fix_retargets_stale_task_by_id_and_slug(tmp_path):
    v = tmp_path / "vault"
    _note(v, "dev_tasks/review/items/task-54-weapon_system", "task\n")
    _note(v, "Doc", "see [[dev_tasks/todo/items/task-54-weapon-system|weapon]]\n")
    files, links, leftovers = doc_links.fix(v)
    assert (files, links) == (1, 1)
    assert leftovers == []
    text = (v / "Doc.md").read_text(encoding="utf-8")
    assert "[[task-54-weapon_system|weapon]]" in text
    assert doc_links.broken_links(v) == []


def test_reused_id_with_different_slug_is_not_retargeted(tmp_path):
    # The historical task-181 collision: the cited file was deleted, another
    # task took the number. Retargeting would be a wrong link.
    v = tmp_path / "vault"
    _note(v, "dev_tasks/done/triggers/task-181-trigger-editor-effect-groups", "task\n")
    _note(v, "Doc", "see [[todo/gameplay/task-181-command-parser-multiwindow-targets]]\n")
    _, links, leftovers = doc_links.fix(v)
    assert links == 0
    assert len(leftovers) == 1
    assert "command-parser" in leftovers[0]


def test_legacy_bug_underscore_name_is_retargeted(tmp_path):
    v = tmp_path / "vault"
    _note(v, "dev_tasks/done/bugs/bug_6-inspector-equip-slots-white-bg", "bug\n")
    _note(v, "Doc", "[[bug_6-inspector-equip-slots-white-bg 1|bug-6]]\n")
    _, links, _ = doc_links.fix(v)
    assert links == 1
    assert "[[bug_6-inspector-equip-slots-white-bg|bug-6]]" in \
        (v / "Doc.md").read_text(encoding="utf-8")


def test_retarget_links_rewrites_stale_status_folder(tmp_path):
    v = tmp_path / "vault"
    _note(v, "dev_tasks/done/items/task-9-x", "task\n")
    _note(v, "Doc", "[[dev_tasks/todo/items/task-9-x|nine]]\n")
    files, links = doc_links.retarget_links(
        v, "dev_tasks/todo/items/task-9-x", "task-9-x")
    assert (files, links) == (1, 1)
    assert "[[task-9-x|nine]]" in (v / "Doc.md").read_text(encoding="utf-8")


def test_move_rewrites_inbound_links(tmp_path, capsys):
    # The wiring test: tasks.cmd_move must repair citations, not just relocate.
    vault = tmp_path / "vault"
    root = vault / "dev_tasks"
    src = root / "todo" / "items" / "task-9-x.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("---\nstatus: todo\narea: items\n---\n\n# task-9: x\n", encoding="utf-8")
    _note(vault, "Doc", "[[dev_tasks/todo/items/task-9-x|x]]\n")

    rc = tasks.cmd_move(tasks.argparse.Namespace(
        root=root, kind="task", id=9, status="done"))
    assert rc == 0
    text = (vault / "Doc.md").read_text(encoding="utf-8")
    assert "[[task-9-x|x]]" in text, text


def test_vault_link_check_clean_on_repo_vault():
    # The real vault is the strongest regression: it is expected at zero.
    broken = doc_links.broken_links(Path("docs/virtualWorld"))
    assert broken == [], broken[:10]
