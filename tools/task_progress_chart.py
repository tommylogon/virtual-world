#!/usr/bin/env python3
"""Render task-card status history by area as a self-contained SVG.

Historical points come from weekly Git snapshots of the task tree. The final
point comes from the working tree and is checked against ``tasks.py status``.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = REPO_ROOT / "docs" / "virtualWorld" / "dev_tasks"
TASK_ROOT_REL = TASK_ROOT.relative_to(REPO_ROOT).as_posix()
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "assets" / "task-status-over-time.svg"
CARD_NAME = re.compile(r"^(?:task|bug)-\d+-[^/]+\.md$")
STATUSES = ("todo", "inprogress", "review", "done", "cancelled")
STATUS_LABELS = {
    "todo": "Todo",
    "inprogress": "In progress",
    "review": "Review",
    "done": "Done",
    "cancelled": "Cancelled",
}
STATUS_COLORS = {
    "todo": "#667085",
    "inprogress": "#d97706",
    "review": "#2563eb",
    "done": "#15803d",
    "cancelled": "#dc2626",
}


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def first_tracked_date() -> date:
    dates = git("log", "--reverse", "--format=%cs", "--", TASK_ROOT_REL).splitlines()
    if not dates:
        raise RuntimeError(f"No Git history found for {TASK_ROOT_REL}")
    return date.fromisoformat(dates[0])


def weekly_dates(start: date, end: date) -> list[date]:
    dates = [start]
    while dates[-1] < end:
        next_week = dates[-1] + timedelta(days=7)
        if end - next_week <= timedelta(days=3):
            break
        dates.append(next_week)
    if dates[-1] != end:
        dates.append(end)
    return dates


def classify_path(path: str) -> tuple[str, str] | None:
    parts = path.replace("\\", "/").split("/")
    if len(parts) < 2 or parts[0] not in STATUSES:
        return None
    if not CARD_NAME.fullmatch(parts[-1]):
        return None
    area = parts[1] if len(parts) > 2 else "?"
    return area, parts[0]


def summarize(paths: list[str]) -> dict[str, Counter]:
    result: dict[str, Counter] = defaultdict(Counter)
    for path in paths:
        classified = classify_path(path)
        if classified:
            area, status = classified
            result[area][status] += 1
    return dict(result)


def git_snapshot_paths(day: date) -> list[str]:
    before = datetime.combine(day + timedelta(days=1), time.min).isoformat()
    commit = git("rev-list", "-1", f"--before={before}", "HEAD")
    if not commit:
        return []
    output = git("ls-tree", "-r", "--name-only", commit, "--", TASK_ROOT_REL)
    prefix = TASK_ROOT_REL + "/"
    return [line[len(prefix):] for line in output.splitlines() if line.startswith(prefix)]


def working_tree_paths() -> list[str]:
    return [path.relative_to(TASK_ROOT).as_posix() for path in TASK_ROOT.rglob("*.md")]


def tracker_totals() -> dict:
    output = subprocess.check_output(
        [sys.executable, str(REPO_ROOT / "tools" / "tasks.py"), "status", "--json"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    )
    return json.loads(output)


def verify_current_snapshot(snapshot: dict[str, Counter], expected: dict) -> None:
    status_counts = Counter()
    area_counts = Counter()
    for area, counts in snapshot.items():
        area_counts[area] += sum(counts.values())
        status_counts.update(counts)

    expected_status = Counter(expected["by_status"])
    expected_area = Counter({area or "?": sum(counts.values())
                             for area, counts in expected["by_area"].items()})
    if sum(status_counts.values()) != expected["total"]:
        raise RuntimeError(
            f"Chart snapshot has {sum(status_counts.values())} cards; "
            f"tasks.py reports {expected['total']}"
        )
    if status_counts != expected_status or area_counts != expected_area:
        raise RuntimeError("Chart snapshot does not match tasks.py status totals")


def xesc(value: object) -> str:
    return html.escape(str(value), quote=True)


def nice_max(value: int) -> int:
    return max(5, int(math.ceil(value / 5.0) * 5))


def render_svg(days: list[date], snapshots: list[dict[str, Counter]], output: Path) -> None:
    areas = sorted(
        snapshots[-1],
        key=lambda area: (-sum(snapshots[-1][area].values()), area),
    )
    cols = 3
    panel_w = 448
    panel_h = 166
    margin_x = 28
    header_h = 112
    rows = math.ceil(len(areas) / cols)
    width = margin_x * 2 + cols * panel_w
    height = header_h + rows * panel_h + 18

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Task-card status by discipline over time</title>',
        '<desc id="desc">Weekly counts of todo, in-progress, review, done, and cancelled '
        'task cards for each discipline from the first tracked snapshot through the current '
        'working tree. Each discipline has its own vertical scale.</desc>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#1f2937}'
        '.muted{fill:#667085}.grid{stroke:#d0d5dd;stroke-width:1}.axis{stroke:#475467;stroke-width:1}</style>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{margin_x}" y="34" font-size="24" font-weight="700">'
        'Task status by discipline over time</text>',
        f'<text x="{margin_x}" y="58" class="muted" font-size="13">'
        f'Weekly snapshots · {days[0].isoformat()} to {days[-1].isoformat()} · '
        f'{sum(sum(counts.values()) for counts in snapshots[-1].values())} cards now</text>',
    ]

    legend_x = margin_x
    legend_y = 88
    for status in STATUSES:
        elements.append(
            f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 24}" '
            f'y2="{legend_y}" stroke="{STATUS_COLORS[status]}" stroke-width="3"/>'
        )
        elements.append(
            f'<circle cx="{legend_x + 12}" cy="{legend_y}" r="3" '
            f'fill="#ffffff" stroke="{STATUS_COLORS[status]}" stroke-width="2"/>'
        )
        elements.append(
            f'<text x="{legend_x + 31}" y="{legend_y + 4}" font-size="12">'
            f'{STATUS_LABELS[status]}</text>'
        )
        legend_x += 31 + len(STATUS_LABELS[status]) * 7 + 32

    tick_ids = sorted({0, len(days) // 3, (2 * len(days)) // 3, len(days) - 1})
    draw_order = ("todo", "inprogress", "review", "cancelled", "done")

    for area_index, area in enumerate(areas):
        col = area_index % cols
        row = area_index // cols
        x = margin_x + col * panel_w
        y = header_h + row * panel_h
        current = snapshots[-1][area]
        current_total = sum(current.values())
        elements.append(
            f'<text x="{x}" y="{y + 15}" font-size="13" font-weight="700">'
            f'{xesc(area)} · {current_total} cards</text>'
        )

        plot_x = x + 39
        plot_y = y + 27
        plot_w = panel_w - 55
        plot_h = 96
        maximum = nice_max(max(
            (counts.get(status, 0)
             for snapshot in snapshots
             for counts in [snapshot.get(area, Counter())]
             for status in STATUSES),
            default=0,
        ))

        for tick in (0, maximum // 2, maximum):
            yy = plot_y + plot_h - (tick / maximum) * plot_h
            elements.append(
                f'<line class="grid" x1="{plot_x}" y1="{yy:.1f}" '
                f'x2="{plot_x + plot_w}" y2="{yy:.1f}"/>'
            )
            elements.append(
                f'<text x="{plot_x - 7}" y="{yy + 4:.1f}" class="muted" '
                f'font-size="10" text-anchor="end">{tick}</text>'
            )
        elements.append(
            f'<line class="axis" x1="{plot_x}" y1="{plot_y}" '
            f'x2="{plot_x}" y2="{plot_y + plot_h}"/>'
        )
        elements.append(
            f'<line class="axis" x1="{plot_x}" y1="{plot_y + plot_h}" '
            f'x2="{plot_x + plot_w}" y2="{plot_y + plot_h}"/>'
        )

        for tick_id in tick_ids:
            xx = plot_x + (tick_id / max(1, len(days) - 1)) * plot_w
            elements.append(
                f'<line class="axis" x1="{xx:.1f}" y1="{plot_y + plot_h}" '
                f'x2="{xx:.1f}" y2="{plot_y + plot_h + 4}"/>'
            )
            elements.append(
                f'<text x="{xx:.1f}" y="{plot_y + plot_h + 17}" class="muted" '
                f'font-size="10" text-anchor="middle">{days[tick_id].strftime("%b %d")}</text>'
            )

        for status in draw_order:
            values = [snapshot.get(area, Counter()).get(status, 0) for snapshot in snapshots]
            if not any(values):
                continue
            points = []
            for idx, value in enumerate(values):
                xx = plot_x + (idx / max(1, len(values) - 1)) * plot_w
                yy = plot_y + plot_h - (value / maximum) * plot_h
                points.append((xx, yy))
            path_data = " ".join(
                ("M" if idx == 0 else "L") + f"{xx:.1f},{yy:.1f}"
                for idx, (xx, yy) in enumerate(points)
            )
            color = STATUS_COLORS[status]
            elements.append(
                f'<path d="{path_data}" fill="none" stroke="{color}" '
                'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
            )
            for xx, yy in points:
                elements.append(
                    f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="2.4" '
                    f'fill="#ffffff" stroke="{color}" stroke-width="1.7"/>'
                )

    elements.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(elements) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(),
                        help="final working-tree snapshot date (YYYY-MM-DD)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="SVG output path")
    args = parser.parse_args()

    start = first_tracked_date()
    days = weekly_dates(start, args.as_of)
    snapshots = [summarize(git_snapshot_paths(day)) for day in days[:-1]]
    current = summarize(working_tree_paths())
    expected = tracker_totals()
    verify_current_snapshot(current, expected)
    snapshots.append(current)
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    render_svg(days, snapshots, output)
    print(f"Wrote {output} with {len(days)} snapshots and {expected['total']} current cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
