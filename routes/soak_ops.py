"""Soak-run API logic: start/stop/inspect/export long-horizon soaks.

Thin sibling ``routes/soak.py`` only maps URLs to these functions. All the real
work (the tick loop) lives in :mod:`engine.soak_runner`, so the web UI and
``tools/soak_sim.py`` cannot drift apart.
"""
from __future__ import annotations

import json
import logging

from flask import Response, jsonify, request

from engine import soak_runner
from engine.soak_runner import SoakConfig

logger = logging.getLogger(__name__)

# Parameter guard rails — long enough to be a real soak, short enough that the
# UI stays responsive and the box does not melt.
MAX_TICKS = 5_000_000
MIN_TICKS = 1
MAX_TRACK_VITALS = 40


def _error(message, code=400):
    return jsonify({"error": message}), code


def meta():
    """Everything the UI needs to render its form before any run exists."""
    scenarios = soak_runner.list_scenarios()
    active = soak_runner.active_run()
    return jsonify({
        "scenarios": scenarios,
        "defaults": {
            "scenario": soak_runner.DEFAULT_SCENARIO,
            "ticks": 10080,
            "minutes_per_tick": None,
            "engine_decay": False,
            "background_all": False,
            "mature": False,
            "neutral_environment": False,
            "debug_hp": False,
            "seed": 1234,
            "sample_every": 0,
            "track_characters": True,
            "track_vitals": list(soak_runner.DEFAULT_CHAR_VITALS),
        },
        "core_vitals": list(soak_runner.CORE_VITALS),
        "limits": {
            "min_ticks": MIN_TICKS,
            "max_ticks": MAX_TICKS,
            "max_retained_runs": soak_runner._MAX_RETAINED,
            "max_track_vitals": MAX_TRACK_VITALS,
        },
        "active_run_id": active.id if active else None,
        "run_count": len(soak_runner.list_runs()),
    })


def _build_config(payload: dict) -> SoakConfig:
    """Validate a request body into a SoakConfig (raises ValueError -> 400)."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    try:
        ticks = int(payload.get("ticks", 10080))
    except (TypeError, ValueError):
        raise ValueError("ticks must be an integer")
    if ticks < MIN_TICKS or ticks > MAX_TICKS:
        raise ValueError(f"ticks must be between {MIN_TICKS} and {MAX_TICKS}")

    mpt = payload.get("minutes_per_tick")
    if mpt not in (None, ""):
        try:
            mpt = float(mpt)
        except (TypeError, ValueError):
            raise ValueError("minutes_per_tick must be a number")
        if mpt <= 0:
            raise ValueError("minutes_per_tick must be > 0")
    else:
        mpt = None

    # Resolve the scenario up front so a bad path fails before a run starts.
    soak_runner.resolve_scenario(payload.get("scenario") or soak_runner.DEFAULT_SCENARIO)

    vitals = payload.get("track_vitals") or []
    if isinstance(vitals, str):
        vitals = [v.strip() for v in vitals.split(",") if v.strip()]
    if len(vitals) > MAX_TRACK_VITALS:
        raise ValueError(f"At most {MAX_TRACK_VITALS} tracked vitals")

    spec = dict(payload)
    spec["ticks"] = ticks
    spec["minutes_per_tick"] = mpt
    spec["track_vitals"] = vitals
    try:
        return SoakConfig.from_dict(spec)
    except ValueError as exc:  # bad key=value chunk
        raise ValueError(str(exc))


def start():
    payload = request.get_json(silent=True) or {}
    try:
        config = _build_config(payload)
    except ValueError as exc:
        return _error(str(exc), 400)
    try:
        run = soak_runner.start_run(config)
    except RuntimeError as exc:
        return _error(str(exc), 409)
    except Exception as exc:  # noqa: BLE001
        logger.exception("soak start failed")
        return _error(f"Could not start soak: {exc}", 500)
    return jsonify(run.snapshot()), 201


def list_runs():
    active = soak_runner.active_run()
    return jsonify({"runs": soak_runner.list_runs(),
                    "active_run_id": active.id if active else None})


def get_run(run_id: str):
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    since = request.args.get("since", type=int)
    event_since = request.args.get("event_since", type=int)
    return jsonify(run.snapshot(since=since if since is not None else 0,
                                event_since=event_since if event_since is not None else 0))


def stop(run_id: str):
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    run.cancel()
    return jsonify(run.snapshot())


def delete(run_id: str):
    try:
        removed = soak_runner.remove_run(run_id)
    except RuntimeError as exc:
        return _error(str(exc), 409)
    if not removed:
        return _error("Unknown run", 404)
    return jsonify({"removed": run_id})


def report(run_id: str):
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    include_samples = request.args.get("samples") in ("1", "true", "yes")
    try:
        payload = run.report(include_samples=include_samples)
    except RuntimeError as exc:
        return _error(str(exc), 409)
    if request.args.get("download"):
        body = json.dumps(payload, indent=2)
        return _download(body, f"soak-{run_id}.json", "application/json")
    return jsonify(payload)


def export(run_id: str):
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    kind = request.args.get("kind", "samples")
    if kind not in ("samples", "deaths", "characters", "growth"):
        return _error("kind must be samples, deaths, characters or growth", 400)
    body = run.export_csv(kind)
    filename = f"soak-{run_id}-{kind}.csv"
    if request.args.get("download"):
        return _download(body, filename, "text/csv")
    return Response(body, mimetype="text/csv")


def characters(run_id: str):
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    return jsonify({"characters": run.characters,
                    "final": run.summary is not None})


def character_series(run_id: str, name: str):
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    series = run.character_series(name)
    if series is None:
        return _error("No series recorded for that character", 404)
    return jsonify(series)


def events(run_id: str):
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    return jsonify({"events": run.events()})


def samples(run_id: str):
    """Full sample history in one shot (used by compare + offline charts)."""
    run = soak_runner.get_run(run_id)
    if run is None:
        return _error("Unknown run", 404)
    return jsonify({"samples": run.samples(),
                    "tracked_vitals": run.tracked_vitals,
                    "summary": run.summary})


def _download(body: str, filename: str, mimetype: str) -> Response:
    return Response(body, mimetype=mimetype, headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    })
