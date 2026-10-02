"""Ambiguous character targets ask, never guess (task-448).

Two characters can share a display name (a family surname, a reused generic
name, an alias). The matcher already refuses to pick; these pin that the action
route surfaces a structured chooser whose picks resolve to the identity key, and
that an identity-key target hits exactly that character.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player

AREA = "Blizzard Forest Clearing"


def _place(w, key):
    w.players[key].current_area = AREA
    w.set_player_area(key, AREA)


def _app_with_two_violets():
    from app import create_app
    app = create_app({"TESTING": True})
    w = app.world
    # Keep the world's own cast out of the way so only our two candidates share
    # the attacker's area.
    attacker = Player("Attacker")
    w.add_player(attacker)
    _place(w, attacker.name)

    before = set(w.players)
    w.add_player(Player("Violet"))
    w.add_player(Player("Violet"))
    vkeys = [k for k in w.players if k not in before]
    assert len(vkeys) == 2, vkeys
    for k in vkeys:
        _place(w, k)
    w.active_player = "Attacker"
    return app, w, vkeys


def test_ambiguous_attack_returns_a_chooser_not_a_pick():
    app, w, vkeys = _app_with_two_violets()
    body = app.test_client().post(
        "/api/action", json={"character": "Attacker", "command": "attack violet"}
    ).get_json()

    assert "choices" in body, "an ambiguous target must offer a chooser"
    group = body["choices"][0]
    assert group["verb"] == "attack"
    assert {o["key"] for o in group["options"]} == set(vkeys)
    # Both candidates are labelled "Violet" but must carry a distinguishing detail.
    assert all(o["label"] == "Violet" for o in group["options"])
    assert all(o["detail"] for o in group["options"])
    assert "Do you mean" in body["output"]
    # Never auto-pick: the exact ambiguity text, not an attack result.
    assert "Violet" in body["output"]


def test_key_target_from_the_chooser_hits_exactly_that_character(monkeypatch):
    app, w, vkeys = _app_with_two_violets()
    # The FIRST duplicate keys as the bare display name "Violet", so a plain
    # "attack Violet" is ambiguous. Only the chooser's `key:Violet` handle can
    # name it — that is the case worth pinning.
    chosen = vkeys[0]
    seen = {}

    def fake_attack(attacker, target, *args, **kwargs):
        seen["target"] = target
        return "ok"

    monkeypatch.setattr(w, "_player_attack", fake_attack)
    body = app.test_client().post(
        "/api/action", json={"character": "Attacker", "command": f"attack key:{chosen}"}
    ).get_json()

    assert body.get("choices") is None, "a key target is unambiguous"
    assert seen.get("target") == chosen


def test_ambiguous_lead_offers_the_chooser_instead_of_erroring():
    """`lead` is a real verb; an ambiguous one must ask, not 500.

    Regression: the ambiguity branch left `target_player` None and then read
    `target_player.current_area`, so `lead violet` raised AttributeError and the
    route returned 500 with the chooser discarded.
    """
    app, w, vkeys = _app_with_two_violets()
    resp = app.test_client().post(
        "/api/action", json={"character": "Attacker", "command": "lead violet"}
    )
    body = resp.get_json()

    assert resp.status_code == 200, body
    assert "choices" in body
    group = body["choices"][0]
    assert group["verb"] == "lead"
    assert {o["key"] for o in group["options"]} == set(vkeys)
    assert "Do you mean" in body["output"]


def test_lead_by_key_reaches_the_chosen_character(monkeypatch):
    app, w, vkeys = _app_with_two_violets()
    chosen = vkeys[0]
    seen = {}

    def fake_lead(attacker, target, *args, **kwargs):
        seen["target"] = target
        return "ok"

    monkeypatch.setattr(w.grapple, "lead", fake_lead)
    body = app.test_client().post(
        "/api/action", json={"character": "Attacker", "command": f"lead key:{chosen}"}
    ).get_json()

    assert body.get("choices") is None
    assert seen.get("target") == chosen
