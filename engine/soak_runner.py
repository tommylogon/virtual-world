"""engine/soak_runner.py — reusable headless long-horizon soak engine.

This is the single implementation behind both ``tools/soak_sim.py`` (CLI) and
the ``/soak`` web UI (``routes/soak_ops.py``). It loads a scenario, drives
``world.tick_turn()`` in a tight loop and records what happened.

Two ways to use it:

* CLI / tests: ``run = SoakRun(config); run.execute()`` — synchronous, with an
  optional ``on_tick`` callback for live progress printing.
* Web: ``run = start_run(config)`` — the same ``execute`` on a daemon thread;
  poll ``run.snapshot()`` for live progress and ``run.report()`` when finished.

It deliberately makes no LLM calls: tick processing uses only the deterministic
simple-NPC / background-simulation paths. Each run owns a fresh ``VirtualWorld``
and never touches ``app.world`` or the scenario file.

Note: ``random.seed`` is process-global, so the registry allows a single active
run at a time; that also keeps the soak from saturating the box.
"""
from __future__ import annotations

import csv
import io
import json
import random
import statistics
import threading
import time
import traceback
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent

MINUTES_PER_DAY = 1440

# Aggregate vitals recorded for every sample. Anything numeric found on a
# character is included, so mature-mode meters appear automatically.
CORE_VITALS = (
    "Hunger", "Thirst", "Energy", "HP", "Social",
    "Hygiene", "Sanity", "Entertainment", "Temperature",
)
# Vitals charted per character for drill-down (averaged view uses all numeric).
DEFAULT_CHAR_VITALS = ("Hunger", "Thirst", "Energy", "HP", "Temperature")

# Run statuses.
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_FINISHED = "finished"
STATUS_STOPPED = "stopped"
STATUS_ERROR = "error"
TERMINAL = (STATUS_FINISHED, STATUS_STOPPED, STATUS_ERROR)

DEFAULT_SCENARIO = "data/scenarios/kraktooth_goblin_camp.json"
MAX_EVENTS = 4000
MAX_SAMPLES = 2000


# ─────────────────────────── small helpers ───────────────────────────

def ticks_per_day(minutes_per_tick: float) -> int:
    """Ticks in one game day at this world's tick length."""
    return max(1, int(round(MINUTES_PER_DAY / max(1e-9, minutes_per_tick))))


def parse_kv_pairs(spec) -> dict:
    """'a=1,b=2' (or an already-parsed mapping) -> numeric/string dict."""
    out: dict = {}
    if not spec:
        return out
    if isinstance(spec, dict):
        for key, value in spec.items():
            out[str(key).strip()] = _coerce_scalar(value)
        return out
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"Bad key=value chunk: {chunk!r}")
        key, value = chunk.split("=", 1)
        out[key.strip()] = _coerce_scalar(value.strip())
    return out


def _coerce_scalar(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def fmt_span(ticks: int, minutes_per_tick: float) -> str:
    """Ticks -> 'XdHHhMMm' game time."""
    total_min = max(0, ticks) * (minutes_per_tick or 1)
    days = int(total_min // 1440)
    hours = int((total_min % 1440) // 60)
    mins = int(total_min % 60)
    return f"{days}d{hours:02d}h{mins:02d}m"


def human_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds or 0)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def progress_bar(frac: float, width: int = 20) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = int(frac * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def infer_cause(player) -> str:
    v = getattr(player, "vitals", {}) or {}
    if (v.get("Thirst") or 0) >= 100:
        return "dehydration"
    if (v.get("Hunger") or 0) >= 100:
        return "starvation"
    if (v.get("Energy", 1) or 0) <= 0:
        return "exhaustion"
    if (v.get("HP", 1) or 0) <= 0:
        return "hp_loss"
    return "unknown"


def resolve_scenario(path: str) -> Path:
    """Resolve a scenario path and refuse anything outside the project root."""
    raw = Path(str(path or DEFAULT_SCENARIO))
    candidate = raw if raw.is_absolute() else (ROOT / raw)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        raise ValueError(f"Scenario must live inside the project: {path!r}")
    if not resolved.is_file():
        raise ValueError(f"Scenario not found: {path!r}")
    return resolved


# ─────────────────────────── configuration ───────────────────────────

@dataclass
class SoakConfig:
    """Everything the headless soak can vary — mirrors tools/soak_sim.py flags."""

    scenario: str = DEFAULT_SCENARIO
    ticks: int = 10080
    minutes_per_tick: Optional[float] = None
    engine_decay: bool = False
    decay_overrides: dict = field(default_factory=dict)
    starting_vitals: dict = field(default_factory=dict)
    traits: dict = field(default_factory=dict)
    background_all: bool = False
    mature: bool = False
    neutral_environment: bool = False
    debug_hp: bool = False
    seed: int = 1234
    sample_every: int = 0          # 0 = auto (~MAX_SAMPLES samples)
    track_vitals: list = field(default_factory=list)  # empty = defaults
    track_characters: bool = True
    label: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "SoakConfig":
        data = dict(data or {})
        cfg = cls()
        cfg.scenario = str(data.get("scenario") or cfg.scenario)
        try:
            cfg.ticks = max(1, int(data.get("ticks") or cfg.ticks))
        except (TypeError, ValueError):
            cfg.ticks = cfg.ticks
        mpt = data.get("minutes_per_tick")
        if mpt in ("", None):
            cfg.minutes_per_tick = None
        else:
            try:
                cfg.minutes_per_tick = float(mpt)
            except (TypeError, ValueError):
                cfg.minutes_per_tick = None
        for flag in ("engine_decay", "background_all", "mature",
                     "neutral_environment", "debug_hp", "track_characters"):
            if flag in data:
                cfg.__dict__[flag] = bool(data.get(flag))
        cfg.decay_overrides = parse_kv_pairs(data.get("decay_overrides"))
        cfg.starting_vitals = parse_kv_pairs(data.get("starting_vitals"))
        cfg.traits = {str(k): str(v) for k, v in
                      parse_kv_pairs(data.get("traits")).items()}
        try:
            cfg.seed = int(data.get("seed", cfg.seed))
        except (TypeError, ValueError):
            cfg.seed = cfg.seed
        try:
            cfg.sample_every = max(0, int(data.get("sample_every") or 0))
        except (TypeError, ValueError):
            cfg.sample_every = 0
        tv = data.get("track_vitals") or []
        if isinstance(tv, str):
            tv = [s.strip() for s in tv.split(",") if s.strip()]
        cfg.track_vitals = [str(v) for v in tv]
        cfg.label = str(data.get("label") or "")
        return cfg

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────── the run ───────────────────────────

class SoakRun:
    """One soak experiment. Call :meth:`execute` (sync) or :meth:`start` (thread)."""

    def __init__(self, config: SoakConfig):
        self.id = uuid.uuid4().hex[:12]
        self.config = config
        self.status = STATUS_QUEUED
        self.error: Optional[str] = None
        self.label = config.label or self._default_label()

        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.created_at = time.time()

        # Live progress (guarded by _lock).
        self._lock = threading.RLock()
        self.tick = 0
        self.minutes_per_tick = float(config.minutes_per_tick or 1)
        self.ticks_per_second = 0.0
        self.instant_tps = 0.0
        self.elapsed_s = 0.0
        self.eta_s = 0.0
        self.alive = 0
        self.dead = 0
        self.character_count = 0
        self.progress_frac = 0.0
        self.growth: dict = {}
        self.deaths_by_cause: dict = {}
        self.sample_every = config.sample_every

        # Recorded output.
        self._samples: list = []
        self._events: deque = deque(maxlen=MAX_EVENTS)
        self.deaths: list = []
        self._death_by_name: dict = {}
        self._char_series: dict = {}
        self._char_vitals: list = []
        self._track_characters = False
        self.tracked_vitals: list = []
        self._prev_hp: dict = {}
        self._cancel = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.summary: Optional[dict] = None
        self.characters: list = []
        self._scenario_path: Optional[Path] = None

    # ── identity / labels ──

    def _default_label(self) -> str:
        name = Path(self.config.scenario).stem
        return f"{name} · {self.config.ticks} ticks"

    def to_summary(self) -> dict:
        """Lightweight row for the run list (no samples)."""
        with self._lock:
            return {
                "id": self.id,
                "label": self.label,
                "status": self.status,
                "error": self.error,
                "created_at": self.created_at,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "elapsed_s": round(self.elapsed_s, 2),
                "config": self.config.to_dict(),
                "scenario": self.config.scenario,
                "scenario_name": Path(self.config.scenario).stem,
                "ticks": self.config.ticks,
                "tick": self.tick,
                "progress_frac": self.progress_frac,
                "game_span": fmt_span(self.tick, self.minutes_per_tick),
                "total_game_span": fmt_span(self.config.ticks, self.minutes_per_tick),
                "minutes_per_tick": self.minutes_per_tick,
                "ticks_per_second": round(self.ticks_per_second, 1),
                "alive": self.alive,
                "dead": self.dead,
                "characters": self.character_count,
                "deaths_by_cause": dict(self.deaths_by_cause),
                "has_report": self.summary is not None,
            }

    # ── public control ──

    def start(self) -> "SoakRun":
        if self._thread and self._thread.is_alive():
            return self
        self._thread = threading.Thread(
            target=self.execute, name=f"soak-{self.id}", daemon=True)
        self._thread.start()
        return self

    def cancel(self) -> None:
        self._cancel.set()

    def is_running(self) -> bool:
        return self.status == STATUS_RUNNING and not self._cancel.is_set()

    # ── live snapshot (polled by the web UI) ──

    def snapshot(self, since: int = 0, event_since: int = 0) -> dict:
        """Progress + samples newer than ``since`` + events newer than ``event_since``.

        ``next_since`` / ``next_event_since`` are the cursors the client should
        send on its next poll; combined they make polling incremental.
        """
        with self._lock:
            samples = self._samples[since:] if since >= 0 else list(self._samples)
            next_since = len(self._samples)
            events = list(self._events)
            next_event_since = len(events)
            events = events[event_since:] if event_since >= 0 else events
            return {
                "run": self.to_summary(),
                "progress": self._progress_dict(),
                "samples": samples,
                "deaths": list(self.deaths),
                "events": events,
                "next_since": next_since,
                "next_event_since": next_event_since,
                "finished": self.status in TERMINAL,
                "has_report": self.summary is not None,
            }

    def _progress_dict(self) -> dict:
        remaining = max(0, self.config.ticks - self.tick)
        projected = {
            key: round(n / max(self.ticks_per_second, 1e-9), 1)
            for key, n in (
                ("1day", 1 * ticks_per_day(self.minutes_per_tick)),
                ("1week", 7 * ticks_per_day(self.minutes_per_tick)),
                ("1month", 30 * ticks_per_day(self.minutes_per_tick)),
            )
        }
        return {
            "tick": self.tick,
            "ticks": self.config.ticks,
            "fraction": self.progress_frac,
            "game_span": fmt_span(self.tick, self.minutes_per_tick),
            "total_game_span": fmt_span(self.config.ticks, self.minutes_per_tick),
            "minutes_per_tick": self.minutes_per_tick,
            "ticks_per_second": round(self.ticks_per_second, 1),
            "instant_tps": round(self.instant_tps, 1),
            "elapsed_s": round(self.elapsed_s, 2),
            "eta_s": round(self.eta_s, 1),
            "alive": self.alive,
            "dead": self.dead,
            "characters": self.character_count,
            "remaining_ticks": remaining,
            "deaths_by_cause": dict(self.deaths_by_cause),
            "growth": dict(self.growth),
            "projected_wall_seconds": projected,
        }

    # ── report / exports ──

    def report(self, include_samples: bool = False) -> dict:
        with self._lock:
            if self.summary is None:
                raise RuntimeError("Run has not finished yet")
            out = {
                "summary": self.summary,
                "deaths": list(self.deaths),
                "config": self.config.to_dict(),
                "characters": list(self.characters),
            }
            if include_samples:
                out["samples"] = list(self._samples)
            return out

    def events(self) -> list:
        with self._lock:
            return list(self._events)

    def samples(self) -> list:
        with self._lock:
            return list(self._samples)

    def character_series(self, name: str) -> Optional[dict]:
        with self._lock:
            series = self._char_series.get(name)
            if series is None:
                return None
            ticks = [s["tick"] for s in self._samples]
            return {"name": name, "ticks": ticks, "series": {k: list(v) for k, v in series.items()}}

    def export_csv(self, kind: str = "samples") -> str:
        """CSV text for one of: samples, deaths, characters, growth."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        with self._lock:
            if kind == "deaths":
                writer.writerow(["tick", "game_span", "name", "cause", "area",
                                 "hunger", "thirst", "energy", "hp", "tags"])
                for d in self.deaths:
                    writer.writerow([d.get("tick"), d.get("game_span"), d.get("name"),
                                     d.get("cause"), d.get("area"), d.get("hunger"),
                                     d.get("thirst"), d.get("energy"), d.get("hp"),
                                     ";".join(d.get("tags") or [])])
            elif kind == "characters":
                writer.writerow(["name", "state", "alive", "area", "death_tick",
                                 "death_game_span", "cause", "tags", "final_vitals"])
                for c in self.characters:
                    writer.writerow([c.get("name"), c.get("state"), c.get("alive"),
                                     c.get("area"), c.get("death_tick"),
                                     c.get("death_game_span"), c.get("cause"),
                                     ";".join(c.get("tags") or []),
                                     json.dumps(c.get("vitals") or {}, sort_keys=True)])
            elif kind == "growth":
                writer.writerow(["tick", "game_span", "wall_s", "ticks_per_second",
                                 "alive", "dead",
                                 "game_log", "turn_events", "delayed_events",
                                 "graph_nodes", "total_memories", "total_trace"])
                for s in self._samples:
                    g = s.get("growth") or {}
                    writer.writerow([s.get("tick"), s.get("game_span"), s.get("wall_s"),
                                     s.get("ticks_per_second"), s.get("alive"), s.get("dead"),
                                     g.get("game_log"), g.get("turn_events"),
                                     g.get("delayed_events"), g.get("graph_nodes"),
                                     g.get("total_memories"), g.get("total_trace")])
            else:  # samples
                vitals = self.tracked_vitals or list(CORE_VITALS)
                header = ["tick", "game_span", "wall_s", "ticks_per_second",
                          "alive", "dead"]
                for v in vitals:
                    header += [f"{v}_avg", f"{v}_min", f"{v}_max"]
                header += ["game_log", "turn_events", "delayed_events",
                           "graph_nodes", "total_memories", "total_trace"]
                writer.writerow(header)
                for s in self._samples:
                    row = [s.get("tick"), s.get("game_span"), s.get("wall_s"),
                           s.get("ticks_per_second"), s.get("alive"), s.get("dead")]
                    for v in vitals:
                        agg = (s.get("vitals") or {}).get(v) or {}
                        row += [agg.get("avg"), agg.get("min"), agg.get("max")]
                    g = s.get("growth") or {}
                    row += [g.get("game_log"), g.get("turn_events"),
                            g.get("delayed_events"), g.get("graph_nodes"),
                            g.get("total_memories"), g.get("total_trace")]
                    writer.writerow(row)
        return buf.getvalue()

    # ── the loop ──

    def execute(self, on_tick: Optional[Callable[[int], None]] = None) -> dict:
        """Run the soak synchronously. Returns the final summary."""
        config = self.config
        with self._lock:
            self.status = STATUS_RUNNING
            self.started_at = time.time()
        rng_state = random.getstate()
        try:
            self._scenario_path = resolve_scenario(config.scenario)
            from virtual_world_engine import VirtualWorld

            random.seed(config.seed)
            with open(self._scenario_path, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
            world = VirtualWorld()
            world.load_from_dict(data)

            if config.minutes_per_tick:
                world.time_per_tick_minutes = config.minutes_per_tick
            minutes_per_tick = getattr(world, "time_per_tick_minutes", 1) or 1
            players = world.player_manager.players

            self._apply_config(world, players, config, minutes_per_tick)
            self._init_tracking(world, players)

            ticks = config.ticks
            sample_every = config.sample_every or max(1, ticks // MAX_SAMPLES)
            self.sample_every = sample_every

            self._add_event("info", f"Soak started · {len(players)} characters · "
                                    f"{ticks} ticks ({fmt_span(ticks, minutes_per_tick)})")

            t0 = time.perf_counter()
            last_sample = t0
            last_death_count = 0
            milestone = 0

            for i in range(1, ticks + 1):
                if self._cancel.is_set():
                    self._add_event("warn", "Cancelled by user")
                    break
                world.tick_turn()
                self._collect_deaths(i, players, minutes_per_tick)

                if config.debug_hp:
                    self._collect_hp_drops(i, world, players)

                now = time.perf_counter()
                elapsed = now - t0
                with self._lock:
                    self.tick = i
                    self.elapsed_s = elapsed
                    self.ticks_per_second = i / max(elapsed, 1e-9)
                    self.instant_tps = (i - (self._samples[-1]["tick"] if self._samples else 0)) / max(now - last_sample, 1e-9)
                    self.progress_frac = min(1.0, i / ticks)
                    self.eta_s = (ticks - i) / max(self.ticks_per_second, 1e-9)

                if i % sample_every == 0 or i == ticks:
                    self._record_sample(i, world, players, minutes_per_tick, elapsed)
                    last_sample = now
                    bucket = int(self.progress_frac * 10)
                    if bucket > milestone and bucket < 10:
                        milestone = bucket
                        self._add_event("info", f"{bucket * 10}% · {fmt_span(i, minutes_per_tick)} · "
                                                f"{self.ticks_per_second:,.1f} ticks/s")
                    if len(self.deaths) != last_death_count:
                        last_death_count = len(self.deaths)

                if on_tick:
                    on_tick(i)
                # Cancel may have arrived during a sample/event flush.
                if self._cancel.is_set():
                    break

            wall = time.perf_counter() - t0
            self._finalize(world, players, minutes_per_tick, wall)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            with self._lock:
                self.status = STATUS_ERROR
                self.error = f"{type(exc).__name__}: {exc}"
                self.finished_at = time.time()
                self._add_event("error", self.error)
            traceback.print_exc()
        finally:
            # Leave the process RNG exactly as we found it: a run's seed must
            # not leak into the live app or a sibling run.
            random.setstate(rng_state)
        return self.summary or {}

    # ── config / setup ──

    def _apply_config(self, world, players, config, minutes_per_tick) -> None:
        overrides = config.decay_overrides
        if config.engine_decay or overrides:
            for p in players.values():
                if config.engine_decay:
                    p.decay_rates = {}
                for stat, rate in overrides.items():
                    p.decay_rates[stat] = rate

        if config.traits:
            for p in players.values():
                tags = set(p.tags or [])
                for tag, trait_id in config.traits.items():
                    if tag in tags:
                        p.traits[trait_id] = True

        if config.background_all:
            for p in players.values():
                p.simulation_mode = "background"
                p.next_due_tick = 0

        if config.mature:
            world.mature_content = True
            for p in players.values():
                p.sync_pleasure_vitals(True)

        if config.starting_vitals:
            for p in players.values():
                for stat, val in config.starting_vitals.items():
                    p.vitals[stat] = val

        if config.neutral_environment:
            benign = {
                "light": "normal", "temperature": 20, "air": "fresh",
                "smell": "neutral", "noise": "quiet", "wind": "none",
                "humidity": "dry",
            }
            for node in world.graph.nodes.values():
                if node.type == "area":
                    node.properties["environment"] = dict(benign)
            for p in players.values():
                p.vitals["Temperature"] = 37.0
            world.forecast_override = None
            sched = getattr(world, "forecast_schedule", None)
            if isinstance(sched, dict):
                sched["entries"] = []
                sched["current_state"] = "clear"
                sched["transition_table"] = {}
            world._forecast_sched_obj = None

    def _init_tracking(self, world, players) -> None:
        with self._lock:
            self.minutes_per_tick = float(getattr(world, "time_per_tick_minutes", 1) or 1)
            self.character_count = len(players)
            self.alive = len(players)
            self.dead = 0
            all_vitals: set = set()
            for p in players.values():
                for k, v in (getattr(p, "vitals", {}) or {}).items():
                    if k.startswith("Max_"):
                        continue  # caps, not meters
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        all_vitals.add(k)
            tracked = [v for v in (self.config.track_vitals or []) if v in all_vitals]
            if not tracked:
                tracked = [v for v in CORE_VITALS if v in all_vitals]
            tracked += [v for v in sorted(all_vitals) if v not in tracked]
            self.tracked_vitals = tracked

            self._char_vitals = [v for v in (self.config.track_vitals or DEFAULT_CHAR_VITALS)
                                 if v in all_vitals]
            if not self._char_vitals:
                self._char_vitals = [v for v in DEFAULT_CHAR_VITALS if v in all_vitals]
            self._track_characters = (self.config.track_characters
                                      and self.character_count <= 500)
            if self._track_characters:
                self._char_series = {
                    name: {v: [] for v in self._char_vitals} for name in players
                }
            self._prev_hp = {name: p.vitals.get("HP") for name, p in players.items()}
            self.growth = self._growth(world, players)

    def _growth(self, world, players) -> dict:
        return {
            "game_log": len(getattr(world, "game_log", []) or []),
            "turn_events": len(getattr(world, "turn_events", []) or []),
            "delayed_events": len(getattr(world, "delayed_events", []) or []),
            "graph_nodes": len(world.graph.nodes),
            "total_memories": sum(len(getattr(p, "memories", []) or []) for p in players.values()),
            "total_trace": sum(len(getattr(p, "trace_log", []) or []) for p in players.values()),
        }

    # ── per-tick collection ──

    def _collect_deaths(self, tick: int, players, minutes_per_tick: float) -> None:
        for name, p in players.items():
            if name in self._death_by_name:
                continue
            if getattr(p, "state", None) == "dead":
                cause = infer_cause(p)
                record = {
                    "name": name,
                    "tick": tick,
                    "game_span": fmt_span(tick, minutes_per_tick),
                    "area": getattr(p, "current_area", None),
                    "cause": cause,
                    "hunger": p.vitals.get("Hunger"),
                    "thirst": p.vitals.get("Thirst"),
                    "energy": p.vitals.get("Energy"),
                    "hp": p.vitals.get("HP"),
                    "tags": list(p.tags or []),
                }
                with self._lock:
                    self.deaths.append(record)
                    self._death_by_name[name] = record
                    self.dead = len(self._death_by_name)
                    self.alive = max(0, self.character_count - self.dead)
                    self.deaths_by_cause[cause] = self.deaths_by_cause.get(cause, 0) + 1
                self._add_event("death", f"☠ {name} died ({cause}) at {record['game_span']}"
                                         + (f" in {record['area']}" if record["area"] else ""))

    def _collect_hp_drops(self, tick: int, world, players) -> None:
        for name, p in players.items():
            hp = p.vitals.get("HP")
            before = self._prev_hp.get(name)
            if before is not None and hp is not None and hp < before:
                node = None
                area = getattr(p, "current_area", None)
                if area:
                    try:
                        node = world.graph.get_node(world.area_node_id(area))
                    except Exception:
                        node = None
                env = node.properties.get("environment") if node else None
                conds = list((getattr(p, "conditions", None) or {}).keys())
                self._add_event(
                    "hp", f"[hp] t={tick} {name} {before}->{hp} (-{round(before - hp, 2)}) "
                          f"temp={p.vitals.get('Temperature')} area={area} cond={conds} env={env}")
            self._prev_hp[name] = hp

    def _record_sample(self, tick: int, world, players, minutes_per_tick: float, elapsed: float) -> None:
        vitals_agg: dict = {}
        for stat in self.tracked_vitals:
            vals = [p.vitals.get(stat) for p in players.values()
                    if p.state != "dead" and isinstance(p.vitals.get(stat), (int, float))
                    and not isinstance(p.vitals.get(stat), bool)]
            if vals:
                vitals_agg[stat] = {
                    "avg": round(statistics.mean(vals), 2),
                    "min": round(min(vals), 2),
                    "max": round(max(vals), 2),
                }
        sample = {
            "tick": tick,
            "game_span": fmt_span(tick, minutes_per_tick),
            "wall_s": round(elapsed, 3),
            "ticks_per_second": round(self.ticks_per_second, 1),
            "alive": self.alive,
            "dead": self.dead,
            "vitals": vitals_agg,
            "growth": self._growth(world, players),
            "deaths_by_cause": dict(self.deaths_by_cause),
        }
        with self._lock:
            self._samples.append(sample)
            if self._track_characters:
                for name, series in self._char_series.items():
                    p = players.get(name)
                    for stat in series:
                        value = p.vitals.get(stat) if p else None
                        series[stat].append(round(value, 2) if isinstance(value, (int, float))
                                            and not isinstance(value, bool) else None)

    def _add_event(self, kind: str, message: str) -> None:
        with self._lock:
            self._events.append({"t": round(time.time() - (self.started_at or time.time()), 2),
                                 "kind": kind, "message": message})

    # ── finish ──

    def _finalize(self, world, players, minutes_per_tick: float, wall: float) -> None:
        cancelled = self._cancel.is_set()
        ticks_done = self.tick
        survivors = [n for n, p in players.items()
                     if n not in self._death_by_name and p.state != "dead"]
        final = {n: dict(players[n].vitals) for n in survivors}

        def stat_of(key, src, fn):
            vals = [src[n][key] for n in src if src[n].get(key) is not None]
            return round(fn(vals), 1) if vals else None

        def proj(ticks):
            return round(ticks / max(self.ticks_per_second, 1e-9), 1)

        death_ticks = [d["tick"] for d in self.deaths]
        self.characters = self._build_characters(players, minutes_per_tick)
        survivor_vitals = {}
        for k in ("Hunger", "Thirst", "Energy", "HP", "Social", "Hygiene",
                  "Sanity", "Entertainment"):
            if not survivors:
                break
            entry = {
                "avg": stat_of(k, final, statistics.mean),
                "min": stat_of(k, final, min),
                "max": stat_of(k, final, max),
            }
            if entry["avg"] is not None:
                survivor_vitals[k] = entry

        by_area: dict = {}
        for d in self.deaths:
            key = d.get("area") or "unknown"
            by_area[key] = by_area.get(key, 0) + 1

        summary = {
            "id": self.id,
            "label": self.label,
            "status": STATUS_STOPPED if cancelled else STATUS_FINISHED,
            "scenario": str(self._scenario_path.relative_to(ROOT)) if self._scenario_path else self.config.scenario,
            "scenario_name": Path(self.config.scenario).stem,
            "ticks": self.config.ticks,
            "ticks_completed": ticks_done,
            "completed": not cancelled and ticks_done >= self.config.ticks,
            "game_span": fmt_span(ticks_done, minutes_per_tick),
            "total_game_span": fmt_span(self.config.ticks, minutes_per_tick),
            "minutes_per_tick": minutes_per_tick,
            "wall_seconds": round(wall, 2),
            "ticks_per_second": round(self.ticks_per_second, 1),
            "projected_wall_seconds": {
                "1day": proj(1 * ticks_per_day(minutes_per_tick)),
                "1week": proj(7 * ticks_per_day(minutes_per_tick)),
                "1month": proj(30 * ticks_per_day(minutes_per_tick)),
            },
            "characters": self.character_count,
            "deaths": len(self.deaths),
            "survivors": len(survivors),
            "causes": dict(self.deaths_by_cause),
            "death_ticks": {
                "first": min(death_ticks) if death_ticks else None,
                "median": int(statistics.median(death_ticks)) if death_ticks else None,
                "last": max(death_ticks) if death_ticks else None,
            },
            "death_by_area": by_area,
            "game_log_entries": len(getattr(world, "game_log", []) or []),
            "turn_events": len(getattr(world, "turn_events", []) or []),
            "delayed_events": len(getattr(world, "delayed_events", []) or []),
            "graph_nodes": len(world.graph.nodes),
            "total_memories": sum(len(getattr(p, "memories", []) or []) for p in players.values()),
            "total_trace": sum(len(getattr(p, "trace_log", []) or []) for p in players.values()),
            "survivor_vitals": survivor_vitals,
            "survivors_list": survivors,
            "sample_count": len(self._samples),
            "sample_every": self.sample_every,
            "config": self.config.to_dict(),
        }
        with self._lock:
            self.summary = summary
            self.status = summary["status"]
            self.alive = len(survivors)
            self.dead = len(self.deaths)
            self.tick = ticks_done
            self.progress_frac = 1.0 if not cancelled else self.progress_frac
            self.finished_at = time.time()
        self._add_event(
            "info",
            f"Soak {'cancelled' if cancelled else 'finished'} · {ticks_done} ticks in "
            f"{human_duration(wall)} · {len(survivors)}/{self.character_count} alive")

    def _build_characters(self, players, minutes_per_tick: float) -> list:
        rows = []
        for name, p in players.items():
            death = self._death_by_name.get(name)
            series = self._char_series.get(name) if self._track_characters else None
            stats = {}
            if series:
                for stat, values in series.items():
                    clean = [v for v in values if v is not None]
                    if clean:
                        stats[stat] = {
                            "min": round(min(clean), 2),
                            "max": round(max(clean), 2),
                            "avg": round(statistics.mean(clean), 2),
                            "last": clean[-1],
                        }
            rows.append({
                "name": name,
                "state": getattr(p, "state", "alive"),
                "alive": name not in self._death_by_name and getattr(p, "state", None) != "dead",
                "area": getattr(p, "current_area", None),
                "tags": list(getattr(p, "tags", []) or []),
                "death_tick": death["tick"] if death else None,
                "death_game_span": death["game_span"] if death else None,
                "cause": death["cause"] if death else None,
                "vitals": dict(getattr(p, "vitals", {}) or {}),
                "stats": stats,
            })
        rows.sort(key=lambda r: (r["alive"] is False, r["death_tick"] or 0, r["name"]))
        return rows


# ─────────────────────────── run registry ───────────────────────────
#
# A single module-level registry keeps the web routes thin. Only one run may be
# active at a time (global RNG + CPU), but finished runs stay queryable/export-
# able until removed or until the oldest are pruned.

_RUNS: "dict[str, SoakRun]" = {}
_RUNS_ORDER: list = []
_RUNS_LOCK = threading.RLock()
_MAX_RETAINED = 20


def start_run(config: SoakConfig) -> SoakRun:
    """Create + start a run. Raises RuntimeError when one is already active."""
    with _RUNS_LOCK:
        active = [r for r in _RUNS.values() if r.status in (STATUS_QUEUED, STATUS_RUNNING)]
        if active:
            raise RuntimeError(f"A soak is already running ({active[0].id}); stop it first.")
        run = SoakRun(config)
        _RUNS[run.id] = run
        _RUNS_ORDER.append(run.id)
        _prune()
    run.start()
    return run


def _prune() -> None:
    while len(_RUNS_ORDER) > _MAX_RETAINED:
        oldest = _RUNS_ORDER[0]
        run = _RUNS.get(oldest)
        if run and run.status in (STATUS_QUEUED, STATUS_RUNNING):
            break
        _RUNS_ORDER.pop(0)
        _RUNS.pop(oldest, None)


def get_run(run_id: str) -> Optional[SoakRun]:
    with _RUNS_LOCK:
        return _RUNS.get(run_id)


def list_runs() -> list:
    with _RUNS_LOCK:
        runs = [_RUNS[rid].to_summary() for rid in _RUNS_ORDER if rid in _RUNS]
    runs.sort(key=lambda r: r["created_at"], reverse=True)
    return runs


def active_run() -> Optional[SoakRun]:
    with _RUNS_LOCK:
        for run in _RUNS.values():
            if run.status in (STATUS_QUEUED, STATUS_RUNNING):
                return run
    return None


def remove_run(run_id: str) -> bool:
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return False
        if run.status in (STATUS_QUEUED, STATUS_RUNNING):
            raise RuntimeError("Cannot delete a running soak")
        _RUNS.pop(run_id, None)
        if run_id in _RUNS_ORDER:
            _RUNS_ORDER.remove(run_id)
        return True


def list_scenarios() -> list:
    """Scenario files offered by the UI: data/scenarios/*.json + world_template.

    Each entry carries the scenario's tick length and character count when the
    file can be read, so the form can show a real horizon and cast size before
    anything starts. Results are cached by (mtime, size).
    """
    seen: dict = {}
    for path in sorted((ROOT / "data" / "scenarios").glob("*.json")):
        if path.name.startswith(("autosave", "unnamed")):
            continue
        seen[str(path.relative_to(ROOT)).replace("\\", "/")] = path
    template = ROOT / "world_template.json"
    if template.is_file():
        seen["world_template.json"] = template
    out = []
    for rel, path in seen.items():
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        entry = {"path": rel, "name": path.stem, "size": size,
                 "is_template": path.name == "world_template.json"}
        entry.update(_scenario_detail(path))
        out.append(entry)
    out.sort(key=lambda s: (not s["is_template"], s["name"].lower()))
    return out


_SCENARIO_DETAIL_CACHE: dict = {}


def _scenario_detail(path: Path) -> dict:
    try:
        st = path.stat()
    except OSError:
        return {}
    key = str(path)
    stamp = (st.st_mtime, st.st_size)
    cached = _SCENARIO_DETAIL_CACHE.get(key)
    if cached and cached[0] == stamp:
        return cached[1]
    detail: dict = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        mpt = data.get("time_per_tick_minutes")
        # serialization.py defaults a missing value to 5, so the UI must show 5
        # rather than "1" for scenarios that don't carry the field.
        detail["minutes_per_tick"] = mpt if mpt not in (None, "") else 5
        players = data.get("players")
        detail["characters"] = len(players) if isinstance(players, (dict, list)) else None
        detail["mature_content"] = bool(data.get("mature_content"))
    except Exception as exc:  # noqa: BLE001 - a bad scenario should not kill meta
        detail["error"] = f"{type(exc).__name__}: {exc}"
    _SCENARIO_DETAIL_CACHE[key] = (stamp, detail)
    return detail
