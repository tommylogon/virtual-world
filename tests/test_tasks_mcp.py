"""Tests for the dev-task MCP skin (tools/tasks_mcp.py).

The skin must reuse the CLI core, so these check that the tools read the tree
correctly and that the write tools preview by default and only write when
``dry_run=False``.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import tasks_mcp


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-thing.md",
           "---\nstatus: todo\narea: ui\nblocks: [task-2]\n---\n\n"
           "# task-1: Thing\n\n## What\n\nw\n")
    _write(root / "todo" / "ui" / "task-2-other.md",
           "---\nstatus: todo\narea: ui\n---\n\n# task-2: Other\n")
    return root


def test_mcp_read_tools(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    monkeypatch.setattr(tasks_mcp, "_root", lambda: root)
    assert "task-1" in tasks_mcp.list_tasks(area="ui")
    assert "# task-1: Thing" in tasks_mcp.get_task(1)
    assert tasks_mcp.next_free_id("task") == 3
    assert json.loads(tasks_mcp.task_status())["total"] == 2
    assert "task-1" in tasks_mcp.dependency_graph() or "2 cards" in tasks_mcp.dependency_graph()
    assert "task-1" in tasks_mcp.next_tasks()


def test_mcp_add_task_previews_then_writes(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    monkeypatch.setattr(tasks_mcp, "_root", lambda: root)
    preview = tasks_mcp.add_task(area="ui", title="New One", dry_run=True)
    assert "## Acceptance" in preview
    assert not list((root / "todo" / "ui").glob("task-3*")), "dry run wrote a file"
    path = tasks_mcp.add_task(area="ui", title="New One", dry_run=False)
    assert Path(path).exists()
    assert "task-3" in Path(path).name


def test_mcp_set_task_previews_then_writes(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    monkeypatch.setattr(tasks_mcp, "_root", lambda: root)
    target = root / "todo" / "ui" / "task-1-thing.md"
    before = target.read_text(encoding="utf-8")
    preview = tasks_mcp.set_task(1, fields={"priority": "high"}, dry_run=True)
    assert "priority: high" in preview
    assert target.read_text(encoding="utf-8") == before, "dry run wrote the file"
    path = tasks_mcp.set_task(1, fields={"priority": "high"}, dry_run=False)
    assert "priority: high" in Path(path).read_text(encoding="utf-8")


def test_mcp_set_task_rejects_a_bad_section(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    monkeypatch.setattr(tasks_mcp, "_root", lambda: root)
    assert "invalid section" in tasks_mcp.set_task(1, section="nope", value="x")
