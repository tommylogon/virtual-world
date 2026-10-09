"""
Dev Tasks MCP Server
====================
Read and edit the VirtualWorld dev-task tree (docs/virtualWorld/dev_tasks)
over MCP. This is a thin skin over ``tools/tasks.py`` -- the same core the CLI
uses -- so a write here goes through the same schema, merge writer and
movers, and the CLI, the MCP server and any generated file cannot drift.

Tools:
    list_tasks(status, area, kind)     list cards, optionally filtered
    get_task(id, kind)                 the full markdown of one card
    next_free_id(kind)                 the next free numeric id
    task_status()                      counts by status / area / horizon
    roadmap()                          the horizon roadmap view
    next_tasks(limit)                  open cards that can start now, ranked
    dependency_graph()                 edges, cycles, critical path
    backfill_report(status)            the canonical-schema gap (read-only)
    add_task(...)                      scaffold a card (dry_run by default)
    set_task(...)                      set frontmatter / a section (dry_run by default)

The two write tools default to ``dry_run=True`` and return the exact card the
tool would write; pass ``dry_run=False`` to apply it. Nothing here runs the
local LLM: ``backfill_report`` is the read-only gap report, not the content pass.

Run:
    python tools/tasks_mcp.py
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path
from typing import Dict, Optional

from fastmcp import FastMCP

from tools import tasks

mcp = FastMCP("Dev Tasks")

ROOT = tasks.default_root()


def _root() -> Path:
    return tasks.default_root()


def _run(func, **kw):
    """Call a ``cmd_*`` core function, capturing its stdout/stderr as text."""
    args = argparse.Namespace(root=_root(), **kw)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = func(args)
    return code, buf.getvalue().strip()


def _one(kind: str, num: int):
    """Return the single matching Entry, or a string explaining why not."""
    entries = tasks.find_by_id(tasks.iter_entries(_root()), kind, num)
    if not entries:
        return f"no {kind}-{num} found"
    if len(entries) > 1:
        return "ambiguous: " + ", ".join(str(e.path) for e in entries)
    return entries[0]


# ── read tools ───────────────────────────────────────────────────────────


@mcp.tool()
def list_tasks(status: str = "", area: str = "", kind: str = "") -> str:
    """List dev-task cards, optionally filtered.

    Args:
        status: todo | inprogress | review | done | cancelled (blank = all).
        area: topic folder, e.g. gameplay, ui, graph (blank = all).
        kind: task | bug (blank = both).
    """
    _, out = _run(tasks.cmd_list, status=status or None,
                  area=area or None, kind=kind or None)
    return out or "no matching cards"


@mcp.tool()
def get_task(id: int, kind: str = "task") -> str:
    """Return the full markdown of one card.

    Args:
        id: numeric id, e.g. 748.
        kind: task (default) or bug.
    """
    entry = _one(kind, id)
    return entry if isinstance(entry, str) else tasks.read_text(entry.path)


@mcp.tool()
def next_free_id(kind: str = "task") -> int:
    """The next free numeric id for a kind (task or bug). Read-only."""
    return tasks.next_id(_root(), kind)


@mcp.tool()
def task_status() -> str:
    """JSON counts of the tree by folder status, area and horizon. Read-only."""
    _, out = _run(tasks.cmd_status, json=True)
    return out


@mcp.tool()
def roadmap() -> str:
    """The roadmap view: open cards grouped by their `horizon:` frontmatter
    (now / next / later). Derived from the folders, so safe to regenerate."""
    _, out = _run(tasks.cmd_roadmap, out=None)
    return out


@mcp.tool()
def next_tasks(limit: int = 20) -> str:
    """Rank the open cards whose predecessors are all terminal -- what can be
    picked up now. Ordered by how many open cards the card unblocks, then
    priority, then horizon.

    Args:
        limit: max cards to show (default 20).
    """
    _, out = _run(tasks.cmd_next, limit=limit, json=False)
    return out


@mcp.tool()
def dependency_graph() -> str:
    """The dependency DAG: node/edge counts, any cycles, and the critical path
    (longest chain). Edges come from blocked_by / depends_on / parent (precede)
    and blocks / children (succeed); related and supersedes carry no ordering."""
    _, out = _run(tasks.cmd_graph, json=False)
    return out


@mcp.tool()
def backfill_report(status: str = "") -> str:
    """Report the canonical-schema gap (read-only): per card, the synonym
    headings to rename, the canonical sections it lacks, and the frontmatter
    keys it lacks. This does NOT run the LLM content pass.

    Args:
        status: comma-separated statuses to limit to (blank = all).
    """
    wanted = [s.strip() for s in status.split(",") if s.strip()] or None
    _, out = _run(tasks.cmd_backfill, status=wanted, json=False, content=False,
                  write=False, card=None, kind=None, force=False,
                  canonical_order=False, limit=None, llm_base=None,
                  llm_model=None, allow_remote=False)
    return out


# ── write tools (dry_run by default) ─────────────────────────────────────


def _fm_updates_from_fields(fields: Optional[Dict]) -> Dict[str, str]:
    updates: Dict[str, str] = {}
    for key, value in (fields or {}).items():
        if value is None:
            continue
        if key == "wiki":
            updates["wiki"] = f'"{value}"'
        elif key in tasks.DEPENDENCY_KEYS:
            updates[key] = f"[{tasks._fmt_refs(value)}]"
        else:
            updates[key] = str(value)
    return updates


@mcp.tool()
def add_task(area: str, title: str, kind: str = "task",
             priority: str = "medium", status: str = "todo",
             goal: str = "", related: str = "",
             sections: Optional[Dict] = None, dry_run: bool = True) -> str:
    """Scaffold a new card. Returns the path written, or (dry_run, the default)
    the exact card text it would write.

    Args:
        area: topic folder, e.g. gameplay, ui (required).
        title: human title; also the H1 and slug (required).
        kind: task (default) or bug.
        priority: low | medium | high.
        status: starting folder (default todo).
        goal: text for the What section.
        related: value for the **Related:** line, e.g. "task-409".
        sections: mapping of canonical keys (what/why/how/verify/acceptance/
            files) plus frontmatter fields (horizon/effort/wiki/dependency keys)
            to their bodies.
        dry_run: True (default) previews; False writes the file.
    """
    if status not in tasks.STATUSES:
        return f"invalid status {status!r}; expected one of {', '.join(tasks.STATUSES)}"
    if kind not in tasks.KINDS:
        return f"invalid kind {kind!r}; expected task or bug"
    payload = dict(sections or {})
    if goal and "what" not in payload:
        payload["what"] = goal
    num = tasks.next_id(_root(), kind)
    if dry_run:
        return tasks.render_card(
            kind=kind, num=num, title=title, status=status, area=area,
            priority=priority, filed=tasks._dt.date.today().isoformat(),
            related=related, payload=payload)
    _, out = _run(tasks.cmd_new, area=area, title=title, kind=kind,
                  priority=priority, status=status, related=related,
                  goal=goal, json=json.dumps(payload) if payload else None,
                  wiki="", force=False)
    return out


@mcp.tool()
def set_task(id: int, kind: str = "task", fields: Optional[Dict] = None,
             section: str = "", value: str = "", dry_run: bool = True) -> str:
    """Update a card's frontmatter and/or replace one canonical section.

    With no ``section`` the writer touches only the frontmatter keys in
    ``fields`` and leaves the body untouched. With ``section`` it replaces that
    one canonical section in place.

    Args:
        id: numeric id.
        kind: task (default) or bug.
        fields: frontmatter keys to set -- area, priority, horizon, effort,
            goal, wiki, and the dependency keys (related, blocks, blocked_by,
            depends_on, supersedes, parent, children). A dependency value may be
            a list, a single "task-N", or a comma-separated string.
        section: canonical key to replace: what/why/how/verify/acceptance/files.
        value: the new body for ``section``.
        dry_run: True (default) returns the new text; False writes the file.
    """
    entry = _one(kind, id)
    if isinstance(entry, str):
        return entry
    fm_updates = _fm_updates_from_fields(fields)
    sections = {section: value} if section else {}
    if section and section not in tasks.SECTION_TITLE_BY_KEY:
        return ("invalid section {!r}; expected one of {}".format(
            section, ", ".join(sorted(tasks.SECTION_TITLE_BY_KEY))))
    if not fm_updates and not sections:
        return "nothing to set: pass fields and/or section+value"
    try:
        new_text = tasks.apply_set(tasks.read_text(entry.path), fm_updates, sections)
    except ValueError as exc:
        return f"error: {entry.path}: {exc}"
    if dry_run:
        return new_text
    entry.path.write_text(new_text, encoding="utf-8")
    return str(entry.path)


@mcp.resource("tasks://docs")
def docs_resource() -> str:
    """Self-describing reference for the Dev Tasks MCP server."""
    return "\n".join([
        "# Dev Tasks MCP Server",
        "",
        "Read/edit the VirtualWorld dev-task tree over the same core the CLI",
        "(`tools/tasks.py`) uses, so writes cannot drift from the CLI.",
        "",
        "Root: docs/virtualWorld/dev_tasks/<status>/<area>/<kind>-<num>-<slug>.md",
        "Folder is authoritative for status; `status:` frontmatter is advisory.",
        "",
        "## Tools",
        "  list_tasks(status, area, kind)   list cards",
        "  get_task(id, kind)               full markdown of one card",
        "  next_free_id(kind)               next free id",
        "  task_status()                    JSON counts (status/area/horizon)",
        "  roadmap()                        open cards grouped by horizon",
        "  next_tasks(limit)                startable cards, ranked",
        "  dependency_graph()               edges, cycles, critical path",
        "  backfill_report(status)          canonical-schema gap (read-only)",
        "  add_task(...)                    scaffold a card (dry_run default)",
        "  set_task(...)                    set frontmatter/section (dry_run default)",
        "",
        "## Canonical sections",
        "  What / Why / How / Steps to verify / Acceptance / Files",
        "  `Steps to verify` holds `- expected:` and `- observed:` per step.",
        "",
        "## Statuses / kinds / areas",
        "  todo inprogress review done cancelled",
        "  task bug",
        "  bugs characters conditions docs emotions gameplay graph items",
        "  library refactor testing triggers ui world",
    ])


if __name__ == "__main__":
    mcp.run()
