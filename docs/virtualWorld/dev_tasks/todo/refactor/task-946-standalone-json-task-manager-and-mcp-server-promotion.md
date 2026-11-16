---
type: task
status: todo
area: refactor
priority: high
horizon: next
effort: L
wiki: "[[Feature Map]]"
tags: [tasks-tool, json-schema, mcp, codesearch, repo-extraction]
related: [task-797]
---

# task-946: Standalone JSON task manager and MCP server promotion

**Filed:** 2026-11-12
**Related:** task-797

<!-- deps:start -->
**Related:** [[task-797-require-wiki-on-task-cards-and-generate-per-feature-changelogs]]
<!-- deps:end -->

## What

Promote tools/tasks.py and tools/tasks_mcp.py into a standalone repository (modeled on codesearch) with a dedicated name, migrate canonical task storage from Markdown to structured JSON with first-class tags and graph invalidation edges, provide temporary JSON-to-Markdown previews, safely retire .md files in docs/virtualWorld/dev_tasks after doc tooling migrates, and integrate codesearch duplicate/relationship detection.

## Why

Task cards currently live as Obsidian Markdown files with YAML frontmatter plus comment-delimited dependency blocks, while .tasks-index.json caches parsed metadata. Moving canonical storage to JSON eliminates YAML/BOM parsing fragility, makes tags and graph lifecycle fields (superseded_by, invalidated_at) first-class, indexes cleanly in codesearch's existing json_parser, and allows the existing FastMCP server (tools/tasks_mcp.py) and CLI (tools/tasks.py) to serve multiple projects as an independent tool.

## How

1. Standalone repo & naming: extract tools/tasks.py, tools/tasks_mcp.py, and task tests into a separate repository (candidate names: taskgraph, taskweave, devtasks-mcp) with configurable root discovery (TASKS_ROOT / config file) replacing the hardcoded docs/virtualWorld/dev_tasks default, while leaving a thin VirtualWorld wrapper or MCP entry.
2. Canonical JSON schema & tags (Phase 1 starter landed in tools/tasks.py): support normalized tags in CANONICAL_FRONTMATTER and list --tag / MCP list_tasks(tag=...), entry_to_json(), render_markdown_from_json(), export-json, and preview-md so JSON tasks can render temporary Markdown previews on demand.
3. Graph invalidation & lifecycle: upgrade supersedes from informational-only (current _dep_graph behavior) to an enforced supersede workflow recording superseded_by, invalidated_at, and optional target cancellation/archival, excluding superseded tasks from next and roadmap critical paths.
4. Obsidian & .md retirement gate: audit and migrate dependent doc scripts (tools/doc_links.py, tools/doc_connected.py, tools/doc_tags.py, tools/page_changelog.py, tools/task_progress_chart.py) so Obsidian/wiki reports read JSON or generated gitignored Markdown previews before deleting Markdown task files from docs/virtualWorld/dev_tasks.
5. Codesearch duplicate & relation lookup: before scaffolding a task in CLI/MCP, query codesearch (HTTP or MCP) for semantically similar open/recent tasks to warn on duplicates and propose related, supersedes, or blocked_by links automatically.
6. Repair baseline test drift: fix the 4 FastMCP FunctionTool invocation failures in tests/test_tasks_mcp.py and align tests/test_tasks_tool.py with strict validate rules during extraction.

## Browser UI and intended live verification

Intended UI home: Not applicable

Current availability: CLI and FastMCP server workflow (starter tags, export-json, and preview-md shipped in tools/tasks.py; standalone extraction and MD retirement planned).

Why no browser UI: Task management, JSON schema conversion, codesearch duplicate checks, and MCP tools operate via CLI/MCP rather than a game browser UI panel.

Alternative verification steps:
1. Run `python tools/tasks.py export-json --dir <tmp_dir>` and inspect generated JSON task schema and tags.
   - expected: Exported JSON files contain schema_version, normalized tags, linked edges, canonical sections, and extra_sections.
2. Run `python tools/tasks.py preview-md --file <task.json>` to confirm temporary Markdown preview output.
   - expected: Rendered Markdown preserves frontmatter, tags, dependency links, canonical sections, and extra sections cleanly.
3. Run `python -m pytest tests/test_tasks_tool.py -k test_tags_filter_and_json_roundtrip_preview` and MCP tool verification tests.
   - expected: CLI tag filtering, JSON export, Markdown preview, and MCP helper updates pass without regression.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Export all tasks to JSON with `python tools/tasks.py export-json --dir <tmp_dir>` and render a preview with `python tools/tasks.py preview-md --file <task.json>`.
   - expected: Exported JSON includes schema_version, tags, linked edges, sections, and extra_sections; preview-md reproduces valid canonical Markdown.
   - observed: Starter round-trip verified in test_tags_filter_and_json_roundtrip_preview; full-repo extraction pending.
2. Run `python tools/tasks.py list --tag <slug>` and FastMCP `list_tasks(tag=...)` after standalone extraction.
   - expected: Filtering returns only tasks matching normalized tag slugs across CLI and MCP.
   - observed: CLI list --tag verified on task-946 and task-947; standalone extraction pending.
3. Run supersede lifecycle and codesearch duplicate lookup before creating a task.
   - expected: Superseded task gets superseded_by/invalidated_at and leaves next ranking; duplicate creation surfaces related/supersedes candidates.
   - observed: Pending graph invalidation and codesearch client implementation.

## Acceptance

- [ ] Standalone repo created with renamed package/CLI and FastMCP server configured for external project roots.
- [ ] Canonical task JSON schema supports tags, typed linked graph edges, superseded_by, invalidated_at, sections, and extra_sections.
- [ ] Temporary JSON-to-Markdown preview renders cleanly from JSON without making Markdown the source of truth.
- [ ] All VirtualWorld doc link/chart scripts read JSON cleanly before legacy .md files are removed from docs/virtualWorld/dev_tasks.
- [ ] Supersede lifecycle excludes invalidated tasks from next/roadmap recommendations and preserves traceable audit links.
- [ ] Codesearch duplicate and relationship suggestion integrated into task creation CLI and MCP.
- [ ] Task tool and MCP test suites pass cleanly in the standalone repo and wrapper.

## Files

- `tools/tasks.py`
- `tools/tasks_mcp.py`
- `tools/doc_links.py`
- `tools/doc_connected.py`
- `tools/doc_tags.py`
- `tools/page_changelog.py`
- `tools/task_progress_chart.py`
- `tests/test_tasks_tool.py`
- `tests/test_tasks_mcp.py`
