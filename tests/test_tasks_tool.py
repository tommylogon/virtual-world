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


# ── canonical schema ─────────────────────────────────────────────────────


def test_body_sections_folds_synonyms():
    text = ("# t\n\n## Files Affected\n\n- a\n\n## Verification\n\nx\n\n"
            "## Goal\n\ng\n")
    secs = tasks.body_sections(text)
    assert secs["files"].strip() == "- a"
    assert secs["verify"].strip() == "x"
    assert secs["what"].strip() == "g"


def test_missing_sections_lists_canonical_order():
    text = "# t\n\n## What\n\nw\n\n## Acceptance\n\n- [ ] x\n"
    assert tasks.missing_sections(text) == ["why", "how", "browser_ui", "verify", "files"]


def test_section_synonyms_reports_only_non_canonical_headings():
    text = "## Goal\n\nx\n\n## Files\n\ny\n\n## Files Changed\n\nz\n"
    assert tasks.section_synonyms(text) == [("Goal", "what"), ("Files Changed", "files")]


def test_new_json_payload_writes_canonical_card(tmp_path):
    root = tmp_path / "dev_tasks"
    payload = json.dumps({
        "what": "w", "why": "y", "how": "h",
        "acceptance": ["a1", "a2"], "files": ["f.py"],
        "browser_ui": {
            "home": "Character Inspector -> Bio",
            "availability": "Planned; bio view needs a compass link",
            "steps": ["1. Open bio\n   - expected: Compass link visible"]
        },
        "horizon": "now", "wiki": "[[Feature Map]]", "priority": "high",
    })
    args = tasks.argparse.Namespace(
        root=root, area="ui", title="Compass", kind="task", priority="medium",
        status="todo", related="", goal="", json=payload, wiki="", force=False,
        allow_stubs=False)
    assert tasks.cmd_new(args) == 0
    text = next(root.rglob("*.md")).read_text(encoding="utf-8")
    fm, err = tasks.parse_frontmatter(text)
    assert err == ""
    assert fm["horizon"] == "now" and fm["priority"] == "high"
    assert fm["wiki"] == "[[Feature Map]]"
    assert tasks.body_sections(text)["what"].strip() == "w"
    assert "- [ ] a1" in text and "- [ ] a2" in text
    assert "`f.py`" in text
    assert "## Browser UI and intended live verification" in text
    assert "Intended UI home: Character Inspector -> Bio" in text
    assert "Current availability: Planned; bio view needs a compass link" in text
    assert "Live steps when available:" in text
    assert "not a claim that planned UI exists or works today" in text
    assert "## Steps to verify" in text


def test_new_json_rejects_incomplete_payload_without_allow_stubs(tmp_path):
    root = tmp_path / "dev_tasks"
    payload = json.dumps({
        "what": "w", "why": "TODO",
        "wiki": "[[Feature Map]]",
    })
    args = tasks.argparse.Namespace(
        root=root, area="ui", title="Incomplete", kind="task", priority="medium",
        status="todo", related="", goal="", json=payload, wiki="", force=False,
        allow_stubs=False)
    assert tasks.cmd_new(args) == 1


def test_new_json_rejects_nonexistent_linked_task(tmp_path):
    root = tmp_path / "dev_tasks"
    payload = json.dumps({
        "what": "w", "why": "y", "how": "h",
        "acceptance": ["a1"], "files": ["f.py"],
        "browser_ui": {
            "home": "Not applicable",
            "reason": "CLI only tool",
            "availability": "Verified via CLI",
            "alt_steps": ["1. Run command\n   - expected: Output ok"]
        },
        "wiki": "[[Feature Map]]",
        "linked": {"blocks": ["task-99999"]}
    })
    args = tasks.argparse.Namespace(
        root=root, area="ui", title="BadLink", kind="task", priority="medium",
        status="todo", related="", goal="", json=payload, wiki="", force=False,
        allow_stubs=False)
    assert tasks.cmd_new(args) == 1


def test_new_json_at_file_is_bom_tolerant(tmp_path):
    root = tmp_path / "dev_tasks"
    payload = tmp_path / "payload.json"
    # --wiki has been mandatory since task-797; keep this test focused on BOM
    # tolerant JSON loading while satisfying the current card contract.
    payload.write_text('{"what": "w", "wiki": "[[Feature Map]]"}', encoding="utf-8-sig")
    args = tasks.argparse.Namespace(
        root=root, area="ui", title="BOM", kind="task", priority="medium",
        status="todo", related="", goal="", json="@" + str(payload),
        wiki="", force=False, allow_stubs=True)
    assert tasks.cmd_new(args) == 0


# ── status / roadmap / backfill ──────────────────────────────────────────


def test_status_counts(tmp_path, capsys):
    root = _tree(tmp_path)
    assert tasks.cmd_status(tasks.argparse.Namespace(root=root, json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total"] == 2
    assert data["by_status"] == {"todo": 1, "done": 1}


def test_roadmap_groups_by_horizon(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-a.md",
           "---\nstatus: todo\narea: ui\nhorizon: now\n---\n\n# task-1: A\n")
    _write(root / "todo" / "ui" / "task-2-b.md",
           "---\nstatus: todo\narea: ui\n---\n\n# task-2: B\n")
    _write(root / "todo" / "ui" / "task-3-c.md",
           "---\nstatus: todo\narea: ui\nblocked_by: [task-2]\n---\n\n# task-3: C\n")
    _write(root / "todo" / "ui" / "task-4-d.md",
           "---\nstatus: todo\narea: ui\nhorizon: later\n---\n\n# task-4: D\n")
    assert tasks.cmd_roadmap(tasks.argparse.Namespace(root=root, out=None)) == 0
    out = capsys.readouterr().out
    now_i, next_i, later_i = out.index("## Now"), out.index("## Next"), out.index("## Later")
    # horizon: now wins -> Now; a plain startable card -> Next;
    # an open predecessor -> Later; horizon: later overrides startability.
    assert now_i < out.index("task-1") < next_i
    assert next_i < out.index("task-2") < later_i
    assert out.index("task-3") > later_i
    assert out.index("task-4") > later_i


def test_backfill_reports_gap(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "review" / "ui" / "task-5-thing.md",
           "---\nstatus: review\narea: ui\n---\n\n# task-5: Thing\n\n"
           "## Goal\n\ng\n\n## Verification\n\nv\n")
    assert tasks.cmd_backfill(
        tasks.argparse.Namespace(root=root, status=None, json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    card = data["cards"][0]
    assert "Goal" in card["rename"]
    assert "why" in card["missing"] and "files" in card["missing"]
    assert "type" in card["frontmatter"]


# ── merge writer ─────────────────────────────────────────────────────────


def test_merge_card_renames_synonyms_and_preserves_unknown():
    text = ("---\nstatus: todo\n---\n\n# t\n\n## Summary\n\ns\n\n"
            "## Files Affected\n\n- a\n\n## Landed\n\nevidence\n")
    out = tasks.merge_card(text, {})
    assert "## What" in out and "## Files" in out
    assert "## Summary" not in out and "## Files Affected" not in out
    assert "## Landed" in out and "evidence" in out      # unknown preserved


def test_merge_card_preserves_original_section_order_by_default():
    # Rename in place; the sections the card lacked are appended, so `## Landed`
    # stays where the author put it (before the appended canonical block).
    text = ("---\nstatus: todo\n---\n\n# t\n\n## Summary\n\ns\n\n"
            "## Landed\n\nevidence\n")
    out = tasks.merge_card(text, {})
    assert out.index("## What") < out.index("## Landed") < out.index("## Acceptance")


def test_merge_card_canonical_order_option():
    text = ("---\nstatus: todo\n---\n\n# t\n\n## Landed\n\nevidence\n\n"
            "## Summary\n\ns\n")
    out = tasks.merge_card(text, {}, preserve_order=False)
    assert out.index("## What") < out.index("## Acceptance") < out.index("## Landed")


def test_merge_card_keeps_a_duplicate_synonym_section():
    # ## Why and ## Problem both map to `why`; the second must NOT be dropped.
    text = ("---\nstatus: todo\n---\n\n# t\n\n## Why\n\nfirst\n\n"
            "## Problem\n\nsecond\n")
    out = tasks.merge_card(text, {})
    assert "first" in out and "second" in out
    assert "## Problem" in out


def test_merge_card_migrates_group_to_area_and_adds_type():
    text = "---\ngroup: Graph & Area UX\nwiki: \"[[X]]\"\n---\n\n# t\n\n## Summary\n\ns\n"
    out = tasks.merge_card(text, {}, fm_updates={"type": "task", "area": "graph"})
    assert "area: graph" in out and "group:" not in out
    assert "type: task" in out and 'wiki: "[[X]]"' in out


def test_merge_card_replaces_a_stub_but_keeps_real_content():
    text = ("---\nstatus: todo\n---\n\n# t\n\n## What\n\nreal\n\n"
            "## Why\n\nTODO\n")
    out = tasks.merge_card(text, {"why": "authored"}, overwrite=False)
    assert "authored" in out          # the stub was filled
    assert "real" in out              # the real section was left alone


def test_merge_card_synthesizes_a_newline_after_the_fence():
    # A card with no frontmatter: adding keys must not glue `---` to the first
    # key (`---type: bug`), which corrupted bug-12 in the copy proof.
    out = tasks.merge_card("# Bug 12: \n\nbody\n", {},
                           fm_updates={"type": "bug", "area": "bugs"})
    assert out.startswith("---\ntype: bug\narea: bugs\n---\n")
    fm, err = tasks.parse_frontmatter(out)
    assert err == "" and fm["type"] == "bug"


def test_merge_card_no_frontmatter_and_no_updates_adds_no_fence():
    out = tasks.merge_card("# t\n\n## What\n\nw\n", {})
    assert not out.startswith("---")
    assert "## What" in out and "## Acceptance" in out
    assert "## Browser UI and intended live verification" in out
    assert "Intended UI home: TODO" in out


# ── set ──────────────────────────────────────────────────────────────────


def _set_args(root, **over):
    ns = dict(root=root, kind="task", id=1, area=None, priority=None,
              horizon=None, effort=None, goal=None, wiki=None,
              section=None, value=None, value_file=None)
    for key in tasks.DEPENDENCY_KEYS:
        ns[key] = None
    ns.update(over)
    return tasks.argparse.Namespace(**ns)


def test_set_frontmatter_only_leaves_body_untouched(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    body = "# task-1: Thing\n\n## Goal\n\ng\n\nprose that must survive\n"
    _write(root / "todo" / "ui" / "task-1-thing.md",
           "---\nstatus: todo\n---\n\n" + body)
    assert tasks.cmd_set(_set_args(root, priority="high")) == 0
    text = (root / "todo" / "ui" / "task-1-thing.md").read_text(encoding="utf-8")
    assert "priority: high" in text
    assert body in text, "a frontmatter-only set must not reformat the body"


def test_set_replaces_one_section_in_place(tmp_path):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-thing.md",
           "---\nstatus: todo\n---\n\n# task-1: Thing\n\n"
           "## Acceptance\n\n- [ ] old\n\n## Notes\n\nkeep me\n")
    assert tasks.cmd_set(_set_args(
        root, section="acceptance", value="- [ ] new")) == 0
    text = (root / "todo" / "ui" / "task-1-thing.md").read_text(encoding="utf-8")
    assert "- [ ] new" in text and "- [ ] old" not in text
    assert "## Notes" in text and "keep me" in text


def test_set_writes_dependency_list(tmp_path):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-thing.md", "---\nstatus: todo\n---\n\n# t\n")
    assert tasks.cmd_set(_set_args(root, blocked_by="task-2, task-3")) == 0
    text = (root / "todo" / "ui" / "task-1-thing.md").read_text(encoding="utf-8")
    assert "blocked_by: [task-2, task-3]" in text


def test_set_creates_frontmatter_when_the_card_has_none(tmp_path):
    # task-437 in the real tree: a legacy card with a prose **Status:** header
    # and no `---` block. `set` must synthesize one rather than refuse.
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "gameplay" / "task-1-legacy.md",
           "# task-1: Legacy\n\n**Status:** todo\n\nbody\n")
    assert tasks.cmd_set(_set_args(root, blocked_by="task-436")) == 0
    text = (root / "todo" / "gameplay" / "task-1-legacy.md").read_text(encoding="utf-8")
    assert text.startswith("---\nblocked_by: [task-436]\n---\n\n# task-1: Legacy")
    fm, err = tasks.parse_frontmatter(text)
    assert err == "" and fm["blocked_by"] == ["task-436"]


# ── dependency wikilinks (link-deps) ─────────────────────────────────────


def _dep_tree(tmp_path: Path) -> Path:
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "world" / "task-1-paint-a-world.md",
           "---\nstatus: todo\nblocked_by: [task-2]\nrelated: [task-3]\n---\n\n"
           "# task-1: Paint a world\n\n## What\n\nbody\n")
    _write(root / "done" / "graph" / "task-2-link-nodes.md",
           "---\nstatus: done\n---\n\n# task-2: Link nodes\n\n## What\n\nbody\n")
    _write(root / "todo" / "graph" / "task-3-tidy-nodes.md",
           "---\nstatus: todo\n---\n\n# task-3: Tidy nodes\n\n## What\n\nbody\n")
    return root


def test_dep_stems_maps_id_to_basename(tmp_path):
    stems = tasks.dep_stems(_dep_tree(tmp_path))
    assert stems["task-2"] == "task-2-link-nodes"
    assert stems["task-3"] == "task-3-tidy-nodes"


def test_refresh_dep_block_inserts_basename_links(tmp_path):
    root = _dep_tree(tmp_path)
    text = tasks.read_text(root / "todo" / "world" / "task-1-paint-a-world.md")
    new, unresolved = tasks.refresh_dep_block(text, tasks.dep_stems(root))
    assert unresolved == []
    assert tasks.DEPS_START in new and tasks.DEPS_END in new
    assert "**Blocked by:** [[task-2-link-nodes]]" in new
    assert "**Related:** [[task-3-tidy-nodes]]" in new
    # the block sits ahead of the first section, where merge_card preserves it
    assert new.index(tasks.DEPS_END) < new.index("## What")
    # and the frontmatter is untouched
    assert "blocked_by: [task-2]" in new and "related: [task-3]" in new


def test_refresh_dep_block_is_idempotent(tmp_path):
    root = _dep_tree(tmp_path)
    stems = tasks.dep_stems(root)
    text = tasks.read_text(root / "todo" / "world" / "task-1-paint-a-world.md")
    once, _ = tasks.refresh_dep_block(text, stems)
    twice, _ = tasks.refresh_dep_block(once, stems)
    assert twice == once


def test_refresh_dep_block_removes_the_block_when_deps_go(tmp_path):
    root = _dep_tree(tmp_path)
    stems = tasks.dep_stems(root)
    text = tasks.read_text(root / "todo" / "world" / "task-1-paint-a-world.md")
    with_block, _ = tasks.refresh_dep_block(text, stems)
    stripped = tasks.refresh_dep_block(
        with_block, stems, fm={"blocked_by": [], "related": []})[0]
    assert tasks.DEPS_START not in stripped
    assert "## What" in stripped, "the body survives removing the block"


def test_unresolvable_ref_is_reported_and_not_linked(tmp_path):
    root = _dep_tree(tmp_path)
    # task-99 does not exist: it must not become a broken [[wikilink]]
    _write(root / "todo" / "world" / "task-1-paint-a-world.md",
           "---\nstatus: todo\nblocked_by: [task-99, task-2]\n---\n\n"
           "# task-1: Paint a world\n\n## What\n\nbody\n")
    text = tasks.read_text(root / "todo" / "world" / "task-1-paint-a-world.md")
    new, unresolved = tasks.refresh_dep_block(text, tasks.dep_stems(root))
    block = new.split(tasks.DEPS_START)[1].split(tasks.DEPS_END)[0]
    assert "task-99" not in block, "a dangling ref is never linked"
    assert "[[task-2-link-nodes]]" in block, "the resolvable ref still links"
    assert unresolved == ["blocked_by: task-99"]
    # the frontmatter keeps the ref, so `validate` still reports it as dangling
    assert "blocked_by: [task-99, task-2]" in new


def test_render_card_carries_the_block(tmp_path):
    stems = tasks.dep_stems(_dep_tree(tmp_path))
    card = tasks.render_card(kind="task", num=9, title="New", status="todo",
                             area="ui", priority="low", filed="2026-10-11",
                             payload={"blocked_by": ["task-2"]}, stems=stems)
    assert "**Blocked by:** [[task-2-link-nodes]]" in card
    assert card.index(tasks.DEPS_END) < card.index("## What")


def test_apply_set_refreshes_only_when_a_dependency_changes(tmp_path):
    root = _dep_tree(tmp_path)
    stems = tasks.dep_stems(root)
    path = root / "todo" / "world" / "task-1-paint-a-world.md"
    text = tasks.read_text(path)

    set_dep = tasks.apply_set(text, {"blocked_by": "[task-3]"}, stems=stems)
    assert "**Blocked by:** [[task-3-tidy-nodes]]" in set_dep
    assert "task-2-link-nodes" not in set_dep.split("## What")[0]

    set_other = tasks.apply_set(text, {"priority": "high"}, stems=stems)
    assert tasks.DEPS_START not in set_other, \
        "a non-dependency set must not invent a block"


def test_set_keeps_the_block_in_step(tmp_path):
    root = _dep_tree(tmp_path)
    path = root / "todo" / "world" / "task-1-paint-a-world.md"
    assert tasks.cmd_set(_set_args(root, blocked_by="task-3")) == 0
    text = tasks.read_text(path)
    assert "blocked_by: [task-3]" in text
    assert "**Blocked by:** [[task-3-tidy-nodes]]" in text
    assert "task-2-link-nodes" not in text


def test_link_deps_writes_and_then_reports_nothing(tmp_path, capsys):
    root = _dep_tree(tmp_path)
    assert tasks.cmd_link_deps(
        tasks.argparse.Namespace(root=root, status=None, write=True,
                                 json=False)) == 0
    assert tasks.DEPS_START in tasks.read_text(
        root / "todo" / "world" / "task-1-paint-a-world.md")
    capsys.readouterr()
    # a second run must be a clean no-op
    assert tasks.cmd_link_deps(
        tasks.argparse.Namespace(root=root, status=None, write=False,
                                 json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["cards_to_change"] == 0
    assert data["unresolved"] == []


def test_validate_warns_when_a_dep_block_is_missing(tmp_path, capsys):
    root = _dep_tree(tmp_path)
    assert tasks.cmd_validate(
        tasks.argparse.Namespace(root=root, quiet=False, schema=False)) == 0
    out = capsys.readouterr().out
    assert "no [[wikilink]] block" in out
    # after the migration the warning is gone
    tasks.cmd_link_deps(tasks.argparse.Namespace(root=root, status=None,
                                                 write=True, json=False))
    capsys.readouterr()
    assert tasks.cmd_validate(
        tasks.argparse.Namespace(root=root, quiet=False, schema=False)) == 0
    assert "no [[wikilink]] block" not in capsys.readouterr().out


def test_link_deps_preserves_a_utf8_bom(tmp_path):
    # read_text strips the BOM via utf-8-sig, so the writer must put it back.
    root = _dep_tree(tmp_path)
    path = root / "todo" / "world" / "task-1-paint-a-world.md"
    text = tasks.read_text(path)
    _write(path, text, bom=True)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert tasks.cmd_link_deps(tasks.argparse.Namespace(
        root=root, status=None, write=True, json=False)) == 0
    assert path.read_bytes().startswith(b"\xef\xbb\xbf"), "BOM must survive"
    assert tasks.DEPS_START in tasks.read_text(path)


def test_basename_dep_link_survives_a_status_move(tmp_path, capsys):
    # The whole reason the block uses a bare basename: `move` changes the
    # folder, not the stem, so an inbound link cannot rot.
    root = _dep_tree(tmp_path)
    assert tasks.cmd_link_deps(tasks.argparse.Namespace(
        root=root, status=None, write=True, json=False)) == 0
    before = tasks.read_text(root / "todo" / "world" / "task-1-paint-a-world.md")
    assert "[[task-2-link-nodes]]" in before

    assert tasks.cmd_move(tasks.argparse.Namespace(
        root=root, kind="task", id=2, status="review")) == 0
    assert (root / "review" / "graph" / "task-2-link-nodes.md").exists()

    after = tasks.read_text(root / "todo" / "world" / "task-1-paint-a-world.md")
    assert "[[task-2-link-nodes]]" in after, "the link must not change"
    assert tasks.dep_block_gap(after, tasks.dep_stems(root)) == "", \
        "and it must still match the frontmatter"


# ── dependency graph / next ──────────────────────────────────────────────

def test_graph_finds_the_critical_path(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-a.md",
           "---\nstatus: todo\nblocks: [task-2]\n---\n\n# task-1: A\n")
    _write(root / "todo" / "ui" / "task-2-b.md",
           "---\nstatus: todo\nblocks: [task-3]\n---\n\n# task-2: B\n")
    _write(root / "todo" / "ui" / "task-3-c.md",
           "---\nstatus: todo\n---\n\n# task-3: C\n")
    assert tasks.cmd_graph(tasks.argparse.Namespace(root=root, json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["critical_path"] == ["task-1", "task-2", "task-3"]
    assert data["cycles"] == []


def test_graph_detects_a_cycle(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-a.md",
           "---\nstatus: todo\nblocks: [task-2]\n---\n\n# task-1: A\n")
    _write(root / "todo" / "ui" / "task-2-b.md",
           "---\nstatus: todo\nblocks: [task-1]\n---\n\n# task-2: B\n")
    assert tasks.cmd_graph(tasks.argparse.Namespace(root=root, json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["cycles"], "a 2-cycle must be reported"
    assert data["critical_path"] == [], "no critical path across a cycle"


def test_next_excludes_blocked_and_terminal_unblocks(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "done" / "ui" / "task-1-base.md",
           "---\nstatus: done\nblocks: [task-2]\n---\n\n# task-1: Base\n")
    _write(root / "todo" / "ui" / "task-2-next.md",
           "---\nstatus: todo\nblocks: [task-3]\n---\n\n# task-2: Next\n")
    _write(root / "todo" / "ui" / "task-3-last.md",
           "---\nstatus: todo\n---\n\n# task-3: Last\n")
    assert tasks.cmd_next(tasks.argparse.Namespace(root=root, json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    ids = [c["id"] for c in data["cards"]]
    assert "task-2" in ids, "task-2 is unblocked (task-1 is done)"
    assert "task-3" not in ids, "task-3 is blocked by the open task-2"


# ── validate --schema ────────────────────────────────────────────────────


def test_validate_schema_warns_on_gaps_and_unchecked_done(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "done" / "ui" / "task-1-done.md",
           "---\nstatus: done\n---\n\n# task-1: Done\n\n"
           "## Acceptance\n\n- [ ] never checked\n")
    assert tasks.cmd_validate(
        tasks.argparse.Namespace(root=root, quiet=False, schema=True)) == 0
    out = capsys.readouterr().out
    assert "missing section" in out
    assert "unchecked acceptance box" in out
    assert "missing frontmatter" in out


def test_validate_without_schema_flag_emits_no_schema_warnings(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-thin.md", "---\nstatus: todo\n---\n\n# t\n")
    assert tasks.cmd_validate(
        tasks.argparse.Namespace(root=root, quiet=False, schema=False)) == 0
    assert "missing section" not in capsys.readouterr().out


def test_validate_warns_when_non_cancelled_card_lacks_browser_ui_intent(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-1-thin.md",
           "---\nstatus: todo\n---\n\n# task-1: Thin\n")
    assert tasks.cmd_validate(
        tasks.argparse.Namespace(root=root, quiet=False, schema=False)) == 0
    out = capsys.readouterr().out
    assert "non-cancelled card(s) have missing/incomplete browser UI intent" in out
    assert "task-1: missing Browser UI and intended live verification section" in out


def test_validate_includes_legacy_done_folder_cards_in_browser_ui_intent_check(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "done" / "ui" / "finished-with-legacy-name.md",
           "---\ntype: task\nstatus: done\n---\n\n# Finished\n")
    _write(root / "done" / "ui" / "task-4-superseded.md",
           "---\ntype: task\nstatus: superseded\n---\n\n# Superseded\n")
    _write(root / "done" / "ui" / "audit-notes.md",
           "---\ntype: doc\nstatus: done\n---\n\n# Notes\n")
    _write(root / "cancelled" / "ui" / "task-5-cancelled.md",
           "---\ntype: task\nstatus: cancelled\n---\n\n# Cancelled\n")
    assert tasks.cmd_validate(
        tasks.argparse.Namespace(root=root, quiet=False, schema=False)) == 0
    out = capsys.readouterr().out
    assert "non-cancelled card(s) have missing/incomplete browser UI intent" in out
    assert "1 non-cancelled card(s) have missing/incomplete browser UI intent" in out
    assert "finished-with-legacy-name.md: missing Browser UI and intended live verification section" in out
    assert "task-4: missing Browser UI" not in out
    assert "task-5: missing Browser UI" not in out


def test_validate_warns_when_browser_ui_section_is_still_a_template(tmp_path, capsys):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "ui" / "task-2-template.md",
           "---\nstatus: todo\n---\n\n# task-2: Template\n\n"
           "## Browser UI and intended live verification\n\n"
           + tasks.BROWSER_UI_STUB + "\n")
    assert tasks.cmd_validate(
        tasks.argparse.Namespace(root=root, quiet=False, schema=False)) == 0
    out = capsys.readouterr().out
    assert "task-2: Intended UI home is missing or left as a placeholder" in out


def test_browser_ui_intent_accepts_future_surface_and_headless_exception():
    future_ui = """## Browser UI and intended live verification
Intended UI home: Character Inspector → Mind → Memories.
Current availability: panel exists; generator is planned and not implemented.
Live steps when available:
1. Load the fixture, open Mind → Memories, and select the seeded memory.
   - expected: the same Player memory is visible in the ordinary memory list.

This section defines intended access and live acceptance. It is not a
claim that planned UI exists or works today.
"""
    assert tasks.browser_ui_issue(future_ui) == ""

    headless = """## Browser UI and intended live verification
Intended UI home: Not applicable — this task changes a command-line importer.
Current availability: no browser-facing behavior is added by this task.
Live steps when available: Not applicable.
Why no browser UI: authors run the importer outside the game editor.
Alternative verification steps:
1. Run the importer against a fixture and inspect its JSON output.
   - expected: output follows the existing scenario memory schema.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
"""
    assert tasks.browser_ui_issue(headless) == ""


def test_browser_ui_intent_rejects_template_placeholders():
    template = """## Browser UI and intended live verification
Intended UI home: Character Inspector → Mind.
Current availability: planned, not implemented.
Live steps when available:
1. TODO — open the intended surface.
   - expected: TODO

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
"""
    assert "non-placeholder" in tasks.browser_ui_issue(template)


# ── interactive menu ─────────────────────────────────────────────────────
#
# The menu is the surface a human uses by hand, so its state helpers are pure
# and testable without a terminal, and the two policy gates (a stub needs an
# explicit word, an unverified card needs one before `done`) are driven end to
# end through cmd_interactive.


def _feed(monkeypatch, *lines: str) -> None:
    """Answer ``input()`` from ``lines``; running out is EOF, never a hang."""
    queue = list(lines)

    def fake_input(prompt: str = "") -> str:
        if not queue:
            raise EOFError
        return queue.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)


def test_resolve_cards_accepts_id_kind_prefix_and_title_fragment(tmp_path):
    entries = tasks.iter_entries(_tree(tmp_path))
    assert [e.id for e in tasks.resolve_cards(entries, "2")] == ["task-2"]
    assert [e.id for e in tasks.resolve_cards(entries, "task 1")] == ["task-1"]
    assert [e.id for e in tasks.resolve_cards(entries, "paint")] == ["task-1"]
    assert tasks.resolve_cards(entries, "nothing like this") == []


def test_resolve_cards_offers_the_other_kind_rather_than_not_found(tmp_path):
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "bugs" / "bug-7-x.md",
           "---\nstatus: todo\n---\n\n# bug-7: X\n")
    entries = tasks.iter_entries(root)
    assert [e.id for e in tasks.resolve_cards(entries, "task 7")] == ["bug-7"]


def test_card_checkboxes_are_numbered_in_file_order_with_their_section():
    text = ("---\nstatus: todo\n---\n## Acceptance\n\n- [ ] one\n- [x] two\n\n"
            "## Steps to verify\n\n1. do it\n   - expected: yes\n")
    boxes = tasks.card_checkboxes(text)
    assert [b["number"] for b in boxes] == [1, 2]
    assert [b["checked"] for b in boxes] == [False, True]
    assert [b["section"] for b in boxes] == ["acceptance", "acceptance"]


def test_set_checkbox_ticks_and_writes_observed_in_the_same_pass():
    text = ("## Acceptance\n\n- [ ] a panel opens\n\n## Steps to verify\n\n"
            "1. Click it.\n   - expected: a panel\n   - observed: TODO\n")
    new, label = tasks.set_checkbox(text, 1, True, "a panel opened")
    assert label == "a panel opens"
    assert "- [x] a panel opens" in new
    assert "- observed: a panel opened" in new
    assert "   - observed: TODO" in new, "an unrelated step's observed line survives"


def test_set_checkbox_inserts_the_observed_line_under_the_box():
    new, _ = tasks.set_checkbox("## Acceptance\n\n- [ ] a\n", 1, True, "yes")
    assert new.splitlines()[-2:] == ["- [x] a", "  - observed: yes"]


def test_set_checkbox_rejects_a_number_the_card_does_not_have():
    try:
        tasks.set_checkbox("## Acceptance\n\n- [ ] a\n", 4)
    except IndexError as exc:
        assert "no checkbox 4" in str(exc)
    else:
        raise AssertionError("an out-of-range box must not silently no-op")


def test_append_log_line_creates_then_extends_one_log_section():
    text = "# t\n\n## What\n\nx\n"
    once = tasks.append_log_line(text, "did  a thing", when="2026-10-19")
    assert "## Log" in once
    assert "- 2026-10-19 - did a thing" in once
    twice = tasks.append_log_line(once, "did more", when="2026-10-19")
    assert twice.count("## Log") == 1
    assert twice.index("did a thing") < twice.index("did more")


def test_append_log_line_keeps_a_later_section_after_the_log():
    text = "# t\n\n## Log\n\n- old\n\n## Files\n\n- a.py\n"
    new = tasks.append_log_line(text, "new", when="2026-10-19")
    assert new.index("- old") < new.index("new") < new.index("## Files")


def test_area_names_reads_the_folders_on_disk(tmp_path):
    assert tasks.area_names(_tree(tmp_path)) == ["graph", "world"]


def test_format_card_preview_marks_stubs_instead_of_printing_the_template():
    card = ("---\nstatus: todo\narea: world\n---\n\n# task-1: T\n\n"
            "## What\n\nreal content\n\n## Why\n\nTODO\n\n"
            "## Browser UI and intended live verification\n\n"
            f"{tasks.SECTION_STUBS['browser_ui']}\n")
    preview = "\n".join(tasks.format_card_preview(card))
    assert "real content" in preview
    assert "why         (TODO stub)" in preview
    assert "browser_ui  (TODO stub)" in preview
    assert "name the page, panel" not in preview, "the template body is not the preview"


def _gated_tree(tmp_path: Path) -> Path:
    root = tmp_path / "dev_tasks"
    _write(root / "todo" / "world" / "task-1-paint-a-world.md",
           "---\nstatus: todo\narea: world\npriority: medium\n"
           'wiki: "[[Feature Map]]"\n---\n\n# task-1: Paint a world\n\n'
           "## What\n\nPaint it.\n\n## Acceptance\n\n- [ ] a world exists\n")
    return root


def test_menu_add_refuses_a_stub_without_the_explicit_word(tmp_path, monkeypatch):
    root = _gated_tree(tmp_path)
    _feed(monkeypatch, "a", "task", "world", "Second card", "todo", "medium",
          "1", "the what", "", "x")
    assert tasks.cmd_interactive(tasks.argparse.Namespace(root=root)) == 0
    assert not list(root.rglob("task-2-*.md")), "a cancelled preview must write nothing"


def test_menu_add_writes_the_wiki_that_was_asked_for(tmp_path, monkeypatch):
    # The old menu hardcoded `wiki: "[[Feature Map]]"`. It must now be the
    # answer, and a stub still needs the explicit word.
    root = _gated_tree(tmp_path)
    _feed(monkeypatch, "a", "task", "world", "Second card", "todo", "medium",
          "[[World Building/Movement|Movement]]", "the what", "", "stub")
    assert tasks.cmd_interactive(tasks.argparse.Namespace(root=root)) == 0
    written = list(root.rglob("task-2-*.md"))
    assert len(written) == 1
    text = written[0].read_text(encoding="utf-8")
    assert 'wiki: "[[World Building/Movement|Movement]]"' in text
    assert "## What\n\nthe what" in text


def test_menu_move_refuses_done_with_an_unchecked_box(tmp_path, monkeypatch):
    root = _gated_tree(tmp_path)
    _feed(monkeypatch, "m 1", "done", "")
    assert tasks.cmd_interactive(tasks.argparse.Namespace(root=root)) == 0
    assert (root / "todo" / "world" / "task-1-paint-a-world.md").exists()
    assert not (root / "done").exists()


def test_menu_move_files_done_when_the_operator_types_close(tmp_path, monkeypatch):
    root = _gated_tree(tmp_path)
    _feed(monkeypatch, "m 1", "done", "close")
    assert tasks.cmd_interactive(tasks.argparse.Namespace(root=root)) == 0
    assert (root / "done" / "world" / "task-1-paint-a-world.md").exists()


def test_menu_undo_restores_a_card_it_cancelled_a_move_for(tmp_path, monkeypatch):
    root = _gated_tree(tmp_path)
    _feed(monkeypatch, "m 1", "review", "y", "z", "y")
    assert tasks.cmd_interactive(tasks.argparse.Namespace(root=root)) == 0
    restored = root / "todo" / "world" / "task-1-paint-a-world.md"
    assert restored.exists()
    assert restored.read_text(encoding="utf-8").count("status: todo") == 1

def test_longest_path_excludes_terminal_cards_when_cards_provided():
    class FakeEntry:
        def __init__(self, card_id, status):
            self.id = card_id
            self.status = status

    cards = {
        'task-1': FakeEntry('task-1', 'done'),
        'task-2': FakeEntry('task-2', 'review'),
        'task-3': FakeEntry('task-3', 'todo'),
        'task-4': FakeEntry('task-4', 'cancelled'),
    }
    succ = {
        'task-1': ['task-2'],
        'task-2': ['task-3'],
        'task-3': ['task-4'],
        'task-4': [],
    }
    pred = {
        'task-1': [],
        'task-2': ['task-1'],
        'task-3': ['task-2'],
        'task-4': ['task-3'],
    }
    path = tasks._longest_path(list(cards.keys()), succ, pred, cards=cards)
    assert path == ['task-2', 'task-3']

