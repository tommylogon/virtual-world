"""Bug reports filed from the running app become real dev-task files.

@module bug_reports_ops
@contributes the /api/bugs/report handler: turns a report into a bug task file plus its screenshot
@relates tools/tasks.py for id allocation and slugging; routes/docs_ops.py for why the image lives under static/
@docs none — the module docstring below is the contract

A report arrives as ``multipart/form-data`` (the same shape the node-image upload
already uses) and is turned into ``docs/virtualWorld/dev_tasks/todo/<area>/bug-N-<slug>.md``
plus, when a screenshot came with it, a PNG under ``static/images/bug-reports/``.

Three decisions worth stating, because they are not the obvious ones:

* **Ids come from `tools/tasks.py`, not from a counter here.** The task tree is the
  source of truth for ids, and the tool already owns allocation (`next_id`), slugging
  (`slugify`) and the file template. A second allocator would drift from it and
  produce ids the tool then rejects.
* **The file is created with an exclusive create (``open('x')``), not
  ``write_text`` + exists check.** ``next_id`` is ``max(existing) + 1``, so two reports
  filed in the same instant pick the same number; the exclusive create is what makes
  the loser retry instead of silently overwriting the winner's report.
* **The screenshot lives under ``static/``, not next to the task file.**
  ``routes/docs_ops.py`` refuses to serve anything under ``dev_tasks`` (``_safe_vault_path``),
  so an image beside the task could not be rendered by the docs reader. Under
  ``static/`` it is served with no extra wiring, exactly like node art and background maps.

The tree root is overridable with ``DEV_TASKS_ROOT`` and the image directory with
``BUG_REPORT_IMAGES_DIR``, so tests write to a tmp directory instead of the real
tree and the real ``static/``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import jsonify, request

try:
    from werkzeug.utils import secure_filename
except ImportError:  # pragma: no cover - werkzeug ships with flask
    secure_filename = None  # type: ignore[assignment]

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from tools import tasks as dev_tasks
except ImportError:  # pragma: no cover - namespace package fallback
    import tasks as dev_tasks  # type: ignore[no-redef]


# ── limits ────────────────────────────────────────────────────────────────────

#: Screenshot ceiling. Checked per route rather than via ``MAX_CONTENT_LENGTH`` so
#: the 2.48 MB ``GET /api/state`` payload keeps working untouched.
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

#: Frontmatter `area:` must be one of these or `tools/tasks.py validate` complains
#: about a directory it does not recognise. Mirrors the tool's own list.
AREAS = ('bugs', 'characters', 'conditions', 'docs', 'gameplay', 'graph', 'items',
         'library', 'refactor', 'testing', 'triggers', 'ui', 'world')

MAX_MESSAGE_CHARS = 20000
MAX_ELEMENT_HTML_CHARS = 4000
MAX_ELEMENTS = 12


def _error(message: str, status: int = 400):
    return jsonify({'status': 'error', 'error': message}), status


# ── helpers ───────────────────────────────────────────────────────────────────

def _display_path(path: Path, root: Path) -> str:
    """How to name a written file in a response: repo-relative when it is inside
    the repo (the normal case), otherwise relative to the configured tree root."""
    for base in (_REPO_ROOT, root):
        try:
            return path.resolve().relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def _relative_link(target: Path, start_dir: Path) -> str:
    """A link from inside the task file to the image beside it in the repo.

    Resolved with ``relpath`` rather than hardcoded ``../../..`` because the depth
    depends on the status and area folders, and a wrong-depth link is a broken
    image in the vault rather than a visible error.
    """
    try:
        return os.path.relpath(target.resolve(), start_dir.resolve()).replace('\\', '/')
    except ValueError:  # different drive on Windows
        return target.as_posix()


def _clean_text(value: Optional[str], limit: int) -> str:
    text = (value or '').replace('\x00', '').strip()
    return text[:limit]


def _derive_title(message: str, fallback: str = 'Untitled report') -> str:
    """First line of the message, trimmed to something a filename can hold."""
    for line in message.splitlines():
        stripped = line.strip().lstrip('#').strip()
        if stripped:
            stripped = stripped.rstrip('.')
            return stripped[:70]
    return fallback


def _fence(text: str, language: str = '') -> str:
    """Wrap in a fence long enough that the content cannot close it early."""
    longest = 0
    run = 0
    for char in text:
        run = run + 1 if char == '`' else 0
        longest = max(longest, run)
    ticks = '`' * max(3, longest + 1)
    return f"{ticks}{language}\n{text}\n{ticks}\n"


def _element_section(index: int, element: Dict[str, Any]) -> str:
    """One picked DOM element as a markdown block an agent can act on."""
    selector = element.get('selector') or '(no selector)'
    lines = [f"#### {index}. `{selector}`", '']
    summary = element.get('summary')
    if summary:
        lines.append(f"- {summary}")
    rect = element.get('rect')
    if isinstance(rect, dict):
        lines.append(
            "- rect: x={x} y={y} w={w} h={h}".format(
                x=rect.get('x'), y=rect.get('y'),
                w=rect.get('width'), h=rect.get('height')))
    ancestors = element.get('ancestors')
    if isinstance(ancestors, list) and ancestors:
        lines.append("- ancestors: " + " > ".join(str(a) for a in ancestors[:8]))
    computed = element.get('computed')
    if isinstance(computed, dict) and computed:
        pairs = ", ".join(f"{k}: {v}" for k, v in list(computed.items())[:24])
        lines.append(f"- computed: {pairs}")
    own_text = element.get('text')
    if own_text:
        lines += ["", "Visible text:", "", _fence(str(own_text)[:500])]
    html = element.get('outerHTML')
    if html:
        lines += ["", "Markup:", "", _fence(str(html)[:MAX_ELEMENT_HTML_CHARS], 'html')]
    return "\n".join(lines) + "\n"


def _evidence_block(context: Dict[str, Any], elements: List[Dict[str, Any]],
                    image_path: Optional[Path], task_dir: Path) -> str:
    lines = ["## Evidence", ""]
    if image_path is not None:
        lines += [f"![screenshot]({_relative_link(image_path, task_dir)})", ""]
    if context:
        lines += ["App state at capture:", "", _fence(json.dumps(context, indent=2, default=str), 'json')]
    if elements:
        lines += ["", "### Picked elements", ""]
        for i, element in enumerate(elements[:MAX_ELEMENTS], start=1):
            lines.append(_element_section(i, element))
    if not image_path and not context and not elements:
        lines.append("_No evidence was attached._")
    return "\n".join(lines) + "\n"


def _render_bug_file(num: int, title: str, area: str, message: str,
                     context: Dict[str, Any], elements: List[Dict[str, Any]],
                     image_path: Optional[Path], task_dir: Path) -> str:
    """The task file. Frontmatter and heading shape match ``tools/tasks.py new``."""
    filed = _dt.date.today().isoformat()
    return (
        "---\n"
        "type: bug\n"
        "status: todo\n"
        f"area: {area}\n"
        "priority: medium\n"
        "---\n"
        "\n"
        f"# bug-{num}: {title}\n"
        "\n"
        f"**Filed:** {filed} (in-app report)\n"
        "**Related:** \n"
        "\n"
        "## Goal\n"
        "\n"
        f"{message}\n"
        "\n"
        "## Acceptance\n"
        "\n"
        "- TODO\n"
        "\n"
        + _evidence_block(context, elements, image_path, task_dir)
    )


def _create_task_file(root: Path, area: str, title: str, message: str,
                      context: Dict[str, Any], elements: List[Dict[str, Any]],
                      image_path: Optional[Path], attempts: int = 8) -> Tuple[int, Path]:
    """Allocate the next bug id and create its file, retrying on a lost race.

    ``next_id`` is derived from the tree, so two simultaneous reports collide by
    construction. The exclusive create below is what turns that collision into a
    retry rather than an overwrite.
    """
    slug = dev_tasks.slugify(title)[:80] or 'untitled'
    last_error: Optional[Exception] = None
    for _ in range(attempts):
        num = dev_tasks.next_id(root, 'bug')
        path = root / 'todo' / area / f"bug-{num}-{slug}.md"
        body = _render_bug_file(num, title, area, message, context, elements,
                                image_path, path.parent)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write(body)
            return num, path
        except FileExistsError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"could not allocate a bug id after {attempts} attempts: {last_error}")


def _save_screenshot(app, upload, slug: str) -> Optional[Path]:
    """Store an uploaded screenshot under ``static/images/bug-reports/``."""
    if upload is None or not upload.filename:
        return None
    ext = (upload.filename.rsplit('.', 1)[-1] or '').lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"unsupported image type '.{ext}'")
    images_dir = Path(
        app.config.get('BUG_REPORT_IMAGES_DIR')
        or (Path(app.root_path) / 'static' / 'images' / 'bug-reports'))
    images_dir.mkdir(parents=True, exist_ok=True)
    import time
    base = secure_filename(f"{slug}-bug") if secure_filename else slug
    filename = f"{base or 'bug'}-{int(time.time() * 1000)}.{ext}"
    path = images_dir / filename
    upload.save(path)
    return path


def _parse_elements(raw: Optional[str]) -> List[Dict[str, Any]]:
    """The picked-element payload from the client, defensively."""
    parsed = _load_json(raw)
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)][:MAX_ELEMENTS]


def _parse_context(raw: Optional[str]) -> Dict[str, Any]:
    """The client's view of the app at capture time (mode, pitch, camera, url)."""
    parsed = _load_json(raw)
    return parsed if isinstance(parsed, dict) else {}


def _load_json(raw: Optional[str]) -> Any:
    """JSON from a form field. Bad input is dropped, never a 500."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


# ── handler ───────────────────────────────────────────────────────────────────

def handle_bug_report(app):
    """POST /api/bugs/report — write a bug task file, return its id and path."""
    message = _clean_text(request.form.get('message'), MAX_MESSAGE_CHARS)
    if not message:
        return _error('A description is required.')

    title = _clean_text(request.form.get('title'), 120) or _derive_title(message)
    area = _clean_text(request.form.get('area'), 40) or 'bugs'
    if area not in AREAS:
        return _error(f"Unknown area '{area}'. Expected one of: {', '.join(AREAS)}.")

    context = _parse_context(request.form.get('context'))
    elements = _parse_elements(request.form.get('elements'))

    declared = request.content_length
    if declared and declared > MAX_SCREENSHOT_BYTES + 65536:
        return _error('That report is too large to attach (screenshot limit 8 MB).', 413)

    image_path: Optional[Path] = None
    image_url: Optional[str] = None
    upload = request.files.get('screenshot')
    try:
        image_path = _save_screenshot(app, upload, dev_tasks.slugify(title))
    except ValueError as exc:
        return _error(str(exc))
    except OSError as exc:
        return _error(f"Could not save the screenshot: {exc}", 500)
    if image_path is not None:
        # Only claim a URL when the file really is under the app's static dir —
        # a hardcoded prefix would hand back a link that 404s.
        static_root = Path(app.root_path) / 'static'
        try:
            image_path.resolve().relative_to(static_root.resolve())
            image_url = '/static/' + image_path.resolve().relative_to(static_root.resolve()).as_posix()
        except ValueError:
            image_url = None

    root = Path(app.config.get('DEV_TASKS_ROOT') or dev_tasks.default_root())
    try:
        num, path = _create_task_file(
            root, area, title, message, context, elements, image_path)
    except OSError as exc:
        return _error(f"Could not write the task file: {exc}", 500)
    except RuntimeError as exc:
        return _error(str(exc), 500)

    return jsonify({
        'status': 'success',
        'id': f'bug-{num}',
        'path': _display_path(path, root),
        'image': image_url,
    })