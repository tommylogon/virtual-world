"""task-778: Standalone event-stream reader CLI tests (tools/stream_read.cjs)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "stream_read.cjs"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not available")

SAMPLE_EVENTS = [
    {
        "seq": 0,
        "tick": 10,
        "time": "08:00",
        "turn": 0,
        "actor": "Lyrie",
        "area": "Camp Entrance",
        "type": "action",
        "text": "Lyrie examines the bone gate.",
        "outcome": "success"
    },
    {
        "seq": 1,
        "tick": 11,
        "time": "08:01",
        "turn": 0,
        "actor": "Gribba",
        "area": "Food Storage",
        "type": "speech",
        "text": "Who goes there?",
        "outcome": None
    },
    {
        "seq": 2,
        "tick": 12,
        "time": "08:02",
        "turn": 1,
        "actor": "Lyrie",
        "area": "Camp Entrance",
        "type": "action",
        "text": "Lyrie draws her shortsword.",
        "outcome": "success"
    },
    {
        "seq": 3,
        "tick": 13,
        "time": "08:03",
        "turn": 1,
        "actor": None,
        "area": "Camp Entrance",
        "type": "system",
        "text": "Wind blows through the trees.",
        "outcome": None
    }
]


def _run_cli(args, cwd=REPO):
    cmd = [NODE, str(TOOL)] + list(args)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def test_stream_read_jsonl(tmp_path):
    jsonl_file = tmp_path / "run.jsonl"
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for ev in SAMPLE_EVENTS:
            f.write(json.dumps(ev) + "\n")

    # 1. Timeline default output
    code, stdout, stderr = _run_cli([str(jsonl_file)])
    assert code == 0, stderr
    lines = [l for l in stdout.strip().splitlines() if l.strip()]
    assert len(lines) == 4
    assert "Lyrie examines the bone gate." in lines[0]

    # 2. --json output
    code, stdout, stderr = _run_cli([str(jsonl_file), "--json"])
    assert code == 0
    parsed = json.loads(stdout)
    assert len(parsed) == 4
    assert parsed[0]["actor"] == "Lyrie"

    # 3. Filter by range --from 1 --to 2
    code, stdout, stderr = _run_cli([str(jsonl_file), "--from", "1", "--to", "2", "--json"])
    assert code == 0
    parsed = json.loads(stdout)
    assert len(parsed) == 2
    assert [p["seq"] for p in parsed] == [1, 2]

    # 4. Filter by actor --actor Lyrie
    code, stdout, stderr = _run_cli([str(jsonl_file), "--actor", "lyrie", "--json"])
    assert code == 0
    parsed = json.loads(stdout)
    assert len(parsed) == 2
    assert all(p["actor"] == "Lyrie" for p in parsed)

    # 5. Filter by area
    code, stdout, stderr = _run_cli([str(jsonl_file), "--area", "Food Storage", "--json"])
    assert code == 0
    parsed = json.loads(stdout)
    assert len(parsed) == 1
    assert parsed[0]["actor"] == "Gribba"

    # 6. Filter by type
    code, stdout, stderr = _run_cli([str(jsonl_file), "--type", "speech", "--json"])
    assert code == 0
    parsed = json.loads(stdout)
    assert len(parsed) == 1
    assert parsed[0]["text"] == "Who goes there?"

    # 7. Summary mode --mode summary --json
    code, stdout, stderr = _run_cli([str(jsonl_file), "--mode", "summary", "--json"])
    assert code == 0
    summary = json.loads(stdout)
    assert summary["total"] == 4
    actor_counts = {a["actor"]: a["count"] for a in summary["actors"]}
    assert actor_counts["Lyrie"] == 2
    assert actor_counts["Gribba"] == 1


def test_stream_read_json_envelope(tmp_path):
    json_file = tmp_path / "run.json"
    envelope = {
        "schema": 1,
        "scenario": "kraktooth_goblin_camp",
        "counts": {"events": len(SAMPLE_EVENTS)},
        "events": SAMPLE_EVENTS,
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2)

    # Read envelope JSON file
    code, stdout, stderr = _run_cli([str(json_file), "--actor", "Lyrie", "--json"])
    assert code == 0, stderr
    parsed = json.loads(stdout)
    assert len(parsed) == 2


def test_stream_read_errors_and_usage():
    # No args
    code, stdout, stderr = _run_cli([])
    assert code == 2

    # Non-existent file
    code, stdout, stderr = _run_cli(["nonexistent_file_xyz.jsonl"])
    assert code == 2

    # Unknown flag
    code, stdout, stderr = _run_cli(["tools/stream_read.cjs", "--bogus-flag"])
    assert code == 2

    # Help
    code, stdout, stderr = _run_cli(["--help"])
    assert code == 0
