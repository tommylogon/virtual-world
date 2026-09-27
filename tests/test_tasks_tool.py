"""Tests for the dev-task helper (tools/tasks.py).

Covers the parsing core that the roadmap work depends on: real YAML
frontmatter, UTF-8 BOM files, malformed blocks, title cleanup, and the
correctness invariant that the derived index cache never changes a result.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import tasks


def _write(path: Path, text: str, bom: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(text, encoding=encoding)
    return path


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "world" / "task-1-paint-a-world.md",
           "---\nstatus: todo\narea: world\ntitle: Paint a world\n---\n\n"
           "# task-1: Paint a world\n\nbody\n")
    _write(root / "done" / "graph" / "task-2-link-nodes.md",
           "---\nstatus: done\narea: graph\ncreated: 2026-08-17\n---\n\n"
           "# task-2: Link nodes\n", bom=True)
    return root


# ── frontmatter parsing ──────────────────────────────────────────────────


def test_parses_yaml_list_not_just_colon_split():
    data, err = tasks.parse_frontmatter(
        "---\nblocks: [task-2, task-3]\nstatus: todo\n---\n\nbody\n")
    assert err == ""
    assert data["blocks"] == ["task-2", "task-3"]


def test_keeps_colon_inside_quoted_value():
    data, err = tasks.parse_frontmatter(
        '---\ntitle: "Condition: Blind"\n---\n\nbody\n')
    assert err == ""
    assert data["title"] == "Condition: Blind"


def test_unquoted_colon_reports_error_but_still_returns_data():
    # The pre-fix shape of task-266: a bare colon in a plain scalar.
    data, err = tasks.parse_frontmatter(
        "---\ntitle: Condition: Blind\nstatus: done\n---\n\nbody\n")
    assert err, "an unparseable block must not be silent"
    assert data.get("status") == "done", "best-effort data keeps the file usable"


def test_swallowed_body_reports_error():
    # The pre-fix shape of task-230: a '##' section inside the block.
    data, err = tasks.parse_frontmatter(
        "---\nstatus: done\n\n## Implemented\n\n- a bullet with: a colon\n---\n")
    assert err


def test_yaml_date_is_coerced_to_string():
    # PyYAML yields datetime.date, which the index cache cannot store.
    data, err = tasks.parse_frontmatter("---\ncreated: 2026-08-17\n---\n")
    assert err == ""
    assert data["created"] == "2026-08-17"
    assert isinstance(data["created"], str)


def test_absent_and_empty_blocks_are_not_errors():
    assert tasks.parse_frontmatter("no frontmatter here\n") == ({}, "")
    assert tasks.parse_frontmatter("---\n---\n\nbody\n") == ({}, "")


def test_fallback_parser_matches_pyyaml(monkeypatch):
    # The tool must stay usable in a bare env with no PyYAML installed.
    sample = ("---\nblocks: [task-570, task-572]\nstatus: todo\n"
              "area: world\n---\n\nbody\n")
    with_yaml, err_yaml = tasks.parse_frontmatter(sample)
    monkeypatch.setattr(tasks, "yaml", None)
    without, err_without = tasks.parse_frontmatter(sample)
    assert without == with_yaml
    assert err_without == err_yaml == ""


# ── BOM ──────────────────────────────────────────────────────────────────


def test_bom_prefixed_file_frontmatter_is_visible(tmp_path):
    root = tmp_path / "dev_tasks"
    _write(root / "done" / "graph" / "task-2-link-nodes.md",
           "---\nstatus: done\n---\n\n# Link nodes\n", bom=True)
    entry = tasks.iter_entries(root)[0]
    assert entry.frontmatter()["status"] == "done"
    assert entry.frontmatter_error() == ""


# ── titles ───────────────────────────────────────────────────────────────


def test_title_strips_task_id_prefix():
    assert tasks.clean_title("task-568: Town cells") == "Town cells"


def test_title_strips_bug_id_prefix_with_dash():
    assert tasks.clean_title("Bug 22 — Static inspector") == "Static inspector"


def test_title_keeps_a_number_that_is_not_an_id():
    assert tasks.clean_title("3 storeys below") == "3 storeys below"


def test_title_falls_back_to_slug_when_heading_is_empty(tmp_path):
    # bug-12 in the real tree: a heading of literally "Bug 12: ".
    root = tmp_path / "dev_tasks"
    _write(root / "cancelled" / "bug-12-error message on something.md",
           "# Bug 12: \n\nlog text\n")
    entry = tasks.iter_entries(root)[0]
    assert entry.title() == "error message on something"


# ── dependency refs ──────────────────────────────────────────────────────


def test_as_refs_accepts_list_string_and_none():
    assert tasks._as_refs(None) == []
    assert tasks._as_refs(["task-2"]) == ["task-2"]
    assert tasks._as_refs("task-2") == ["task-2"]
    assert tasks._as_refs("task-2, task-3") == ["task-2", "task-3"]


def test_validate_reports_dangling_blocked_by(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "world" / "task-9-thing.md",
           "---\nstatus: todo\nblocked_by: [task-404]\n---\n\n# thing\n")
    assert tasks.cmd_validate(tasks.argparse.Namespace(root=root, quiet=False)) == 0
    assert "dangling blocked_by reference task-404" in capsys.readouterr().out


def test_validate_passes_when_blocked_by_resolves(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "world" / "task-9-thing.md",
           "---\nstatus: todo\nblocked_by: [task-8]\n---\n\n# thing\n")
    _write(root / "done" / "world" / "task-8-base.md",
           "---\nstatus: done\n---\n\n# base\n")
    assert tasks.cmd_validate(tasks.argparse.Namespace(root=root, quiet=False)) == 0
    assert "dangling" not in capsys.readouterr().out


# ── index cache ──────────────────────────────────────────────────────────


def test_cached_entries_match_uncached_entries(tmp_path):
    root = _tree(tmp_path)
    snap = lambda es: [(e.id, e.status, e.area, e.title(), e.frontmatter())
                       for e in es]
    cold = snap(tasks.iter_entries(root, use_cache=False))
    assert not tasks._index_path(root).exists(), "use_cache=False must not write"
    # First cached call finds no index: full rescan, and it saves.
    snap(tasks.iter_entries(root))
    assert tasks._index_path(root).exists()
    # Second call is a real cache HIT -- this is the path that deserializes,
    # and the one that could disagree with a cold rescan.
    warm = snap(tasks.iter_entries(root))
    assert warm == cold


def test_index_command_actually_writes_the_cache(tmp_path):
    root = _tree(tmp_path)
    assert tasks.cmd_index(tasks.argparse.Namespace(root=root, clear=False)) == 0
    assert tasks._index_path(root).exists(), "index reported success but wrote nothing"


def test_index_clear_removes_the_cache(tmp_path):
    root = _tree(tmp_path)
    tasks.cmd_index(tasks.argparse.Namespace(root=root, clear=False))
    assert tasks.cmd_index(tasks.argparse.Namespace(root=root, clear=True)) == 0
    assert not tasks._index_path(root).exists()
    # Still correct after the cache is gone.
    assert len(tasks.iter_entries(root)) == 2


def test_corrupt_cache_record_falls_back_to_a_rescan(tmp_path):
    # A hand-edited cache must never hand a wrong *type* to a caller.
    root = _tree(tmp_path)
    tasks.iter_entries(root)
    p = tasks._index_path(root)
    blob = json.loads(p.read_text(encoding="utf-8"))
    for rec in blob["entries"].values():
        rec[8] = "not-a-mapping"
    p.write_text(json.dumps(blob), encoding="utf-8")
    assert [e.frontmatter() for e in tasks.iter_entries(root)] != ["not-a-mapping"] * 2
    assert tasks.cmd_validate(tasks.argparse.Namespace(root=root, quiet=True)) == 0


def test_truncated_cache_file_falls_back_to_a_rescan(tmp_path):
    root = _tree(tmp_path)
    tasks.iter_entries(root)
    tasks._index_path(root).write_text('{"version": 2, "entries": {"a": [1', encoding="utf-8")
    assert len(tasks.iter_entries(root)) == 2


def test_cache_is_invalidated_when_a_file_changes(tmp_path):
    root = _tree(tmp_path)

    def title_of(entries):
        return {e.id: e.title() for e in entries}

    assert title_of(tasks.iter_entries(root))["task-2"] == "Link nodes"
    p = root / "done" / "graph" / "task-2-link-nodes.md"
    _write(p, "---\nstatus: done\n---\n\n# Renamed nodes\n")
    # Force a distinct mtime/size so the staleness check cannot miss it.
    import os
    st = p.stat()
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000))
    assert title_of(tasks.iter_entries(root))["task-2"] == "Renamed nodes"
