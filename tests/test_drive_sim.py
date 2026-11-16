"""Unit tests for tools/drive_sim.py HTTP simulation driver (task-860)."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.drive_sim import SimDriver, build_parser, main


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["--ticks", "25", "--character", "Vekka"])
    assert args.ticks == 25
    assert args.character == "Vekka"
    assert args.url == "http://127.0.0.1:4444"
    assert args.stop_on_death is True
    assert args.freeze_vitals is False


def test_extract_telemetry_fields():
    driver = SimDriver("http://localhost:4444")
    state = {
        "time_ticks": 105,
        "turn_number": 12,
        "players": {
            "Vekka": {
                "current_area": "Watchtower",
                "state": "alive",
                "vitals": {"Energy": 70, "Hunger": 80},
                "plan": {"index": 2, "label": "patrol"},
                "active_pursuit": {"label": "patrol", "reason": "Guard the perimeter."}
            }
        }
    }
    telemetry = driver.extract_telemetry(state, "Vekka")
    assert telemetry["time_ticks"] == 105
    assert telemetry["turn_number"] == 12
    assert telemetry["character"] == "Vekka"
    assert telemetry["current_area"] == "Watchtower"
    assert telemetry["plan_index"] == 2
    assert telemetry["pursuit"] == "patrol"
    assert telemetry["pursuit_reason"] == "Guard the perimeter."


def test_run_stops_on_arrival():
    driver = SimDriver("http://localhost:4444")
    mock_state_1 = {
        "time_ticks": 1,
        "turn_number": 1,
        "players": {"Vekka": {"current_area": "Camp Entrance", "state": "alive"}}
    }
    mock_state_2 = {
        "time_ticks": 2,
        "turn_number": 2,
        "players": {"Vekka": {"current_area": "Watchtower", "state": "alive"}}
    }

    with patch.object(driver, "apply_tick", return_value=(True, {"status": "success"})):
        with patch.object(driver, "get_state", side_effect=[(True, mock_state_1), (True, mock_state_2)]):
            res = driver.run(ticks=5, character="Vekka", stop_on_arrival="Watchtower")
            assert res["success"] is True
            assert res["stop_reason"] == "arrived_at_Watchtower"
            assert res["samples_count"] == 2


def test_run_writes_jsonl_output():
    driver = SimDriver("http://localhost:4444")
    mock_state = {
        "time_ticks": 42,
        "turn_number": 5,
        "players": {"Gribba": {"current_area": "Kitchen", "state": "alive"}}
    }

    with tempfile.NamedTemporaryFile("r", delete=False) as tf:
        out_path = tf.name

    try:
        with patch.object(driver, "apply_tick", return_value=(True, {"status": "success"})):
            with patch.object(driver, "get_state", return_value=(True, mock_state)):
                res = driver.run(ticks=3, character="Gribba", out_path=out_path)
                assert res["success"] is True

        with open(out_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 3
        assert lines[0]["character"] == "Gribba"
        assert lines[0]["current_area"] == "Kitchen"
        assert lines[0]["time_ticks"] == 42
    finally:
        Path(out_path).unlink(missing_ok=True)
