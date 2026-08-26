"""Tests for tokenize_command helper."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from routes.helpers import tokenize_command


def test_simple_unquoted():
    assert tokenize_command("go north") == ["go", "north"]


def test_double_quoted_single_token():
    assert tokenize_command('go "front door"') == ["go", "front door"]


def test_single_quoted_single_token():
    assert tokenize_command("go 'front door'") == ["go", "front door"]


def test_multiple_quoted_args():
    assert tokenize_command('put "brass key" in "wooden chest"') == ["put", "brass key", "in", "wooden chest"]


def test_empty_string():
    assert tokenize_command("") == []


def test_only_whitespace():
    assert tokenize_command("   ") == []


def test_single_word():
    assert tokenize_command("look") == ["look"]


def test_mixed_quoted_and_unquoted():
    assert tokenize_command('use "healing potion" on self') == ["use", "healing potion", "on", "self"]


def test_nested_quote_in_string():
    assert tokenize_command("say 'hello world'") == ["say", "hello world"]


def test_unclosed_quote():
    assert tokenize_command('go "front door') == ["go", "front door"]
