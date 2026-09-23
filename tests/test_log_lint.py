"""task-347: log_lint guards (tools/log_lint.cjs).

Runs the Node linter over synthetic fixtures to prove each rule fires and that
clean text stays clean. Skips if Node is unavailable. A real export log, when
present, is checked as a smoke test (it must not crash and must flag the
bug-28 apostrophe-stripping class).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "log_lint.cjs"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not available")

DIRTY = """=== CONVERSATION ===
You recently said: "that s so nice of you to say and i m going to be normal about it"
You recently said: "don t worry about it"

=== WITNESSED ===
[the man -> to you] said: "so miki you know you are really fun to hang out with right"
[Heard -> to you] a man's voice said: "so miki you know you are really fun to hang out with right"

=== I REMEMBER ===
I walked into the room and saw the table by the window.
I walked into the room and saw the table by the window.

=== YOUR STATE ===
the the cat sat on the mat
You pick up the earringfrom under the Booth Table.
You pick up the caddieonthe table.
Miki hugs your shoulders.
you is tall and you was quiet.
"""

CLEAN = """=== CONVERSATION ===
You recently said: "that's so nice of you to say and I'm going to be normal about it"

=== WITNESSED ===
[the man -> to you] said: "so miki you know you are really fun to hang out with right"

=== I REMEMBER ===
I walked into the room and saw the table by the window.

=== YOUR STATE ===
The cat sat on the mat.
You pick up the earring from under the Booth Table.
Miki hugs you.
You are tall and you were quiet.
"""

ALL_RULES = {
    "article-double", "missing-space", "apostrophe-strip", "double-attribution",
    "memory-dup", "pronoun-stitch", "appearance-grammar",
}


def _run(*args):
    return subprocess.run(
        [NODE, str(TOOL), *args],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
    )


@pytest.fixture
def write_fixture(tmp_path):
    def _write(text, name="log.txt"):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return str(p)
    return _write


def test_dirty_fixture_flags_every_rule(write_fixture):
    path = write_fixture(DIRTY)
    res = _run(path, "--json")
    assert res.returncode == 1, res.stderr
    findings = json.loads(res.stdout)["findings"]
    assert {f["rule"] for f in findings} == ALL_RULES


def test_clean_fixture_passes(write_fixture):
    path = write_fixture(CLEAN)
    res = _run(path)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "0 finding(s)" in res.stdout


def test_only_flag_restricts_rules(write_fixture):
    path = write_fixture(DIRTY)
    res = _run(path, "--only", "apostrophe-strip", "--json")
    findings = json.loads(res.stdout)["findings"]
    assert findings and {f["rule"] for f in findings} == {"apostrophe-strip"}


def test_no_args_is_usage_error():
    assert _run().returncode == 2


REAL_LOG = REPO / "data" / "exports" / "taco_bell_event_log_2026-08-23T16-19-57.txt"


@pytest.mark.skipif(not REAL_LOG.exists(), reason="sample export log not present")
def test_real_log_smoke_and_bug28_class():
    res = _run(str(REAL_LOG))
    assert res.returncode == 1  # findings, not a crash
    assert "apostrophe-strip=" in res.stdout  # the bug-28 class is observable
