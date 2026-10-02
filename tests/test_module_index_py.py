"""The @module/@contributes/@docs contract extended to Python (task-576).

Same guard the front end has, now over `engine/` and `routes/`: a module whose
docstring carries no `@module`/`@contributes` is uncovered, and a `@docs` that
points at nothing is a problem.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import js_module_index as idx


def _write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_parses_tags_from_a_python_module_docstring(tmp_path):
    p = _write(tmp_path, "engine/foo.py", '''"""Foo does a thing.

@module foo
@contributes the doing of the thing
@docs docs/virtualWorld/Gameplay/Search & Forage.md
"""
import os
''')
    meta = idx.parse_py(p)
    assert meta["module"] == "foo"
    assert meta["contributes"] == "the doing of the thing"
    assert meta["docs"].endswith("Search & Forage.md")


def test_finds_tags_far_down_a_long_docstring(tmp_path):
    body = "\n".join(f"line {i}" for i in range(200))
    p = _write(tmp_path, "engine/long.py",
               '"""Long.\n\n' + body + '\n\n@module long\n@contributes a lot\n"""\n')
    assert idx.parse_py(p)["module"] == "long"


def test_module_without_contributes_is_uncovered(tmp_path):
    p = _write(tmp_path, "engine/bare.py", '"""Bare.\n\n@module bare\n"""\n')
    assert idx.uncovered([(p, idx.parse_py(p))]) == [str(p).replace("\\", "/")]


def test_docs_target_must_resolve(tmp_path):
    # A folder satisfies the contract while pointing at nothing readable.
    (tmp_path / "docs" / "virtualWorld").mkdir(parents=True)
    p = _write(tmp_path, "engine/foo.py",
               '"""Foo.\n\n@module foo\n@contributes x\n@docs docs/virtualWorld\n"""\n')
    problems = idx.docs_problems([(p, idx.parse_py(p))])
    assert problems and "docs/virtualWorld" in problems[0][1]


def test_a_new_python_module_is_held_to_the_contract():
    # The check compares against the recorded baseline; a path not in it fails.
    baseline = Path("docs/design/py-module-baseline.txt")
    assert baseline.exists(), "the Python baseline must exist for the guard"
    known = set(baseline.read_text(encoding="utf-8").split())
    assert "engine/not_a_real_module.py" not in known
