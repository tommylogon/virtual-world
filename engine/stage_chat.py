"""Stage Chat's public conversation state.

@module stage_chat
@contributes ordered messages and per-character perspective cursors
@powers Stage Chat
@relates VirtualWorld, routes/stage_chat.py
@docs none

Stores the public stage log with per-character perspective tracking (last read
id, active/blocked state). It is a standalone social room with no item/world
bindings.
"""
import time
from typing import Dict, List, Optional, Any


class StageChat:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        # {char_name: {"active": bool, "blocked": bool, "last_read_message_id": Optional[int]}}
        self.participants: Dict[str, Dict[str, Any]] = {}
        self.next_message_id: int = 1

    def post_message(self, author: str, text: str, tick: int = 0) -> Dict[str, Any]:
        """Post a message to the public stage log."""
        msg = {
            "id": self.next_message_id,
            "author": author,
            "text": text,
            "timestamp": time.time(),
            "tick": tick
        }
        self.next_message_id += 1
        self.messages.append(msg)
        return msg

    def set_participant(self, name: str, active: Optional[bool] = None, blocked: Optional[bool] = None):
        """Update or register a participant in stage chat."""
        if name not in self.participants:
            self.participants[name] = {
                "active": True,
                "blocked": False,
                "last_read_message_id": None
            }
        if active is not None:
            self.participants[name]["active"] = bool(active)
        if blocked is not None:
            self.participants[name]["blocked"] = bool(blocked)

    def read_messages(self, character: str, mode: str = "latest", n: int = 3,
                      from_id: Optional[int] = None, to_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read messages according to character perspective mode.

        Modes:
          - 'latest': read the last n messages
          - 'all': read all messages since last_read_message_id (or all if never read)
          - 'range': read messages between from_id and to_id (inclusive)
        """
        self.set_participant(character)
        last_id = self.participants[character]["last_read_message_id"]

        results: List[Dict[str, Any]] = []
        if mode == "latest":
            count = max(1, min(50, n or 3))
            results = self.messages[-count:] if self.messages else []
        elif mode == "all":
            if last_id is None:
                results = list(self.messages)
            else:
                results = [m for m in self.messages if m["id"] > last_id]
        elif mode == "range":
            f_id = from_id or 1
            t_id = to_id or (self.messages[-1]["id"] if self.messages else 1)
            results = [m for m in self.messages if f_id <= m["id"] <= t_id]
        else:
            # fallback to latest
            results = self.messages[-3:] if self.messages else []

        if results:
            highest_id = max(m["id"] for m in results)
            if last_id is None or highest_id > last_id:
                self.participants[character]["last_read_message_id"] = highest_id

        return results

    def get_unread_count(self, character: str) -> int:
        """Count how many messages exist that this character has not yet read."""
        if character not in self.participants:
            return len(self.messages)
        last_id = self.participants[character]["last_read_message_id"]
        if last_id is None:
            return len(self.messages)
        return sum(1 for m in self.messages if m["id"] > last_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": self.messages,
            "participants": self.participants,
            "next_message_id": self.next_message_id
        }

    def from_dict(self, data: Optional[Dict[str, Any]]):
        if not data:
            return
        self.messages = list(data.get("messages", []))
        self.participants = dict(data.get("participants", {}))
        self.next_message_id = data.get("next_message_id", len(self.messages) + 1)
