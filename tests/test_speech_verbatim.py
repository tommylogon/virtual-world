"""Speech text must survive storage and rendering byte-for-byte (bug-28).

A 2026-08-23 export (``data/exports/taco_bell_event_log_2026-08-23T16-19-57.txt``)
showed a character quoting its OWN earlier line in the anti-repeat section as
``"no. no licking. absolutely not, that s— that s advanced dlc content"``
while the ``You said:`` echo of the very same utterance, in the very same
turn, was verbatim.  The corruption was exactly ``'`` -> space plus a full
lowercase, applied somewhere between the speech event and the prompt.

The offending transform no longer exists, so these are guards: they pin the
invariant that nothing in the speech pipeline rewrites the spoken string.
A future pass that normalises punctuation or case will fail them.
"""

import pytest

from graph import Node
from player import Player
from virtual_world_engine import VirtualWorld


# Apostrophes, capitals, an em dash, ellipses, interrobangs and asterisks --
# exactly the material the historical transform was eating.
LINE = "NO. No licking — that's NOT weird, I'm sure! You've... *stop*"


@pytest.fixture
def world():
    world = VirtualWorld()
    world.graph.add_node(Node(id="area_verbatim_hall", type="area",
                              name="Verbatim Hall", properties={}))
    return world


def _room(world, names, area="Verbatim Hall"):
    speaker_name = world.active_player
    world.set_player_area(speaker_name, area)
    for name in names:
        world.add_player(Player(name))
        world.set_player_area(name, area)
    return speaker_name


class TestSpeechTextIsNeverRewritten:
    """Every hop from the spoken string to a rendered prompt keeps it verbatim."""

    def test_recent_hearing_keeps_text_verbatim(self, world):
        speaker_name = _room(world, ["Lyrie"])
        listener = world.player_manager.get_player("Lyrie")
        speaker = world.player_manager.get_player(speaker_name)

        world.broadcast_speech(speaker_name, LINE)

        for who in (speaker, listener):
            heard = [h for h in who.recent_hearing
                     if h.get("speaker") == speaker_name and h.get("text")]
            assert heard, f"{who.name} heard nothing"
            assert heard[-1]["text"] == LINE, (
                f"{who.name}'s recent_hearing text was rewritten: "
                f"{heard[-1]['text']!r}"
            )

    def test_speech_log_keeps_text_verbatim(self, world):
        speaker_name = _room(world, ["Lyrie"])

        world.broadcast_speech(speaker_name, LINE)

        assert any(e.get("text") == LINE for e in world.speech_log), \
            "speech_log did not hold the text verbatim"

    def test_turn_event_description_keeps_text_verbatim(self, world):
        speaker_name = _room(world, ["Lyrie"])

        world.broadcast_speech(speaker_name, LINE)

        spoken = [e for e in world.turn_events
                  if e.get("action") == "speak"
                  and "that's NOT weird" in str(e.get("description", ""))]
        assert spoken, "no speak turn event preserved the line"
        assert "that s NOT weird" not in spoken[0]["description"], \
            "apostrophe was stripped from the turn event"
        assert "not weird" in spoken[0]["description"].lower()

    def test_adjacent_area_hearing_keeps_text_verbatim(self, world):
        """A whisper reaching a second room copies the entry -- verbatim too."""
        speaker_name = _room(world, ["Lyrie"])
        listener = world.player_manager.get_player("Lyrie")

        world.broadcast_speech(speaker_name, LINE, speech_level="whisper",
                               whisper_target="Lyrie")

        heard = [h for h in listener.recent_hearing if h.get("speaker") == speaker_name]
        assert heard, "directed whisper did not reach its target"
        assert heard[-1]["text"] == LINE

    def test_narration_listen_renders_verbatim(self, world):
        speaker_name = _room(world, ["Lyrie"])
        world.broadcast_speech(speaker_name, LINE)
        world.set_active_player("Lyrie")

        rendered = world.narration.listen()

        assert LINE in rendered, f"listen() rewrote the line: {rendered!r}"

    def test_own_speech_quoted_back_is_verbatim(self, world):
        """The anti-repeat echo quotes the speaker's own row back unchanged.

        This is the exact shape ``PromptBuilder.ownRecentSpeech`` builds
        client-side from ``recent_hearing``; the server side of the same data
        must therefore hand over an unmodified string.
        """
        speaker_name = _room(world, ["Lyrie"])
        world.broadcast_speech(speaker_name, LINE)

        own = [h["text"] for h in
               world.player_manager.get_player(speaker_name).recent_hearing
               if h.get("speaker") == speaker_name]
        assert own, "speaker did not hear their own line"
        quoted = "; ".join(f'"{t}"' for t in own)
        assert LINE in quoted
