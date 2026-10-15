"""Conversation state for the Stage Chat surface.

@module stage_chat
@contributes channels, membership, ordered messages, and per-character read cursors
@powers Stage Chat communication
@relates VirtualWorld, routes/stage_chat.py
@docs docs/virtualWorld/Gameplay/The Commons.md

Character cognition and memory remain on Player and the standard agent path.
This model stores communication state only.
"""
import time
import uuid
from typing import Any, Dict, List, Optional


PUBLIC_CHANNEL_ID = "public"


class ChatAuthorizationError(PermissionError):
    """Raised when a perspective cannot read or post in a channel."""


class StageChat:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.participants: Dict[str, Dict[str, Any]] = {}
        self.channels: Dict[str, Dict[str, Any]] = {
            PUBLIC_CHANNEL_ID: {
                "id": PUBLIC_CHANNEL_ID,
                "kind": "public",
                "name": "Public",
                "members": [],
                "created_by": "System",
            }
        }
        self.next_message_id = 1

    def set_participant(self, name: str, active: Optional[bool] = None,
                        blocked: Optional[bool] = None):
        if name not in self.participants:
            self.participants[name] = {
                "active": name != "User",
                "blocked": False,
                "last_read_message_ids": {},
            }
        participant = self.participants[name]
        participant.setdefault("last_read_message_ids", {})
        if active is not None:
            participant["active"] = bool(active)
        if blocked is not None:
            participant["blocked"] = bool(blocked)
        return participant

    def _channel(self, channel_id: str) -> Dict[str, Any]:
        channel = self.channels.get(str(channel_id))
        if channel is None:
            raise KeyError("Conversation not found")
        return channel

    def can_access(self, character: str, channel_id: str) -> bool:
        channel = self.channels.get(str(channel_id))
        if channel is None:
            return False
        return channel["kind"] == "public" or character in channel["members"]

    def require_access(self, character: str, channel_id: str) -> Dict[str, Any]:
        channel = self._channel(channel_id)
        if not self.can_access(character, channel_id):
            raise ChatAuthorizationError("Not a member of this conversation")
        return channel

    def create_group(self, creator: str, name: str, members: List[str]) -> Dict[str, Any]:
        title = str(name or "").strip()
        if not title:
            raise ValueError("Group name is required")
        normalized = list(dict.fromkeys(
            str(member).strip() for member in (members or []) if str(member).strip()
        ))
        if creator not in normalized:
            normalized.insert(0, creator)
        if len(normalized) < 2:
            raise ValueError("A private group needs at least two members")
        channel_id = f"group_{uuid.uuid4().hex[:12]}"
        channel = {
            "id": channel_id,
            "kind": "group",
            "name": title[:80],
            "members": normalized,
            "created_by": creator,
        }
        self.channels[channel_id] = channel
        for member in normalized:
            self.set_participant(member)
        return dict(channel)

    def create_dm(self, first: str, second: str) -> Dict[str, Any]:
        left, right = str(first or "").strip(), str(second or "").strip()
        if not left or not right or left == right:
            raise ValueError("A direct message needs two different participants")
        members = sorted((left, right), key=str.casefold)
        for channel in self.channels.values():
            if channel["kind"] == "dm" and sorted(channel["members"], key=str.casefold) == members:
                return dict(channel)
        channel_id = f"dm_{uuid.uuid4().hex[:12]}"
        channel = {
            "id": channel_id,
            "kind": "dm",
            "name": " · ".join(members),
            "members": members,
            "created_by": left,
        }
        self.channels[channel_id] = channel
        self.set_participant(left)
        self.set_participant(right)
        return dict(channel)

    def update_group_members(self, channel_id: str, actor: str,
                             add: Optional[List[str]] = None,
                             remove: Optional[List[str]] = None) -> Dict[str, Any]:
        channel = self._channel(channel_id)
        if channel["kind"] != "group":
            raise ValueError("Membership can only be changed on a private group")
        if actor != channel["created_by"]:
            raise ChatAuthorizationError("Only the group creator can change membership")
        members = list(channel["members"])
        for name in add or []:
            name = str(name).strip()
            if name and name not in members:
                members.append(name)
                self.set_participant(name)
        for name in remove or []:
            name = str(name).strip()
            if name != channel["created_by"]:
                members = [member for member in members if member != name]
        if len(members) < 2:
            raise ValueError("A private group needs at least two members")
        channel["members"] = members
        return dict(channel)

    def list_channels(self, character: str) -> List[Dict[str, Any]]:
        participant = self.set_participant(character)
        cursors = participant["last_read_message_ids"]
        result = []
        for channel in self.channels.values():
            if not self.can_access(character, channel["id"]):
                continue
            latest_id = max(
                (message["id"] for message in self.messages
                 if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel["id"]),
                default=None,
            )
            cursor = cursors.get(channel["id"])
            unread = sum(
                1 for message in self.messages
                if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel["id"]
                and (cursor is None or message["id"] > cursor)
                and message.get("author") != character
            )
            result.append({
                **channel,
                "members": list(channel["members"]),
                "unread_count": unread,
                "last_read_message_id": cursor,
                "latest_message_id": latest_id,
            })
        return sorted(result, key=lambda item: (
            item["id"] != PUBLIC_CHANNEL_ID,
            -(item["latest_message_id"] or 0),
            item["name"].casefold(),
        ))

    def post_message(self, author: str, text: str, tick: int = 0,
                     channel_id: str = PUBLIC_CHANNEL_ID) -> Dict[str, Any]:
        self.require_access(author, channel_id)
        message = {
            "id": self.next_message_id,
            "channel_id": channel_id,
            "author": author,
            "text": text,
            "timestamp": time.time(),
            "tick": tick,
        }
        self.next_message_id += 1
        self.messages.append(message)
        return message

    def read_messages(self, character: str, mode: str = "latest", n: int = 3,
                      from_id: Optional[int] = None, to_id: Optional[int] = None,
                      channel_id: str = PUBLIC_CHANNEL_ID) -> List[Dict[str, Any]]:
        self.require_access(character, channel_id)
        participant = self.set_participant(character)
        cursors = participant["last_read_message_ids"]
        last_id = cursors.get(channel_id)
        messages = [
            message for message in self.messages
            if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel_id
        ]
        if mode == "latest":
            count = max(1, min(50, n or 3))
            results = messages[-count:]
        elif mode == "all":
            results = [message for message in messages
                       if last_id is None or message["id"] > last_id]
        elif mode == "range":
            lower = from_id or 1
            upper = to_id or (messages[-1]["id"] if messages else 1)
            results = [message for message in messages
                       if lower <= message["id"] <= upper]
        else:
            results = messages[-3:]

        if results:
            highest_id = max(message["id"] for message in results)
            if last_id is None or highest_id > last_id:
                cursors[channel_id] = highest_id
        return [dict(message) for message in results]

    def get_unread_count(self, character: str, channel_id: str = PUBLIC_CHANNEL_ID) -> int:
        if not self.can_access(character, channel_id):
            return 0
        participant = self.participants.get(character) or {}
        cursors = participant.get("last_read_message_ids", {})
        # Older saves used a single cursor for the public log.
        last_id = cursors.get(channel_id)
        if channel_id == PUBLIC_CHANNEL_ID and last_id is None:
            last_id = participant.get("last_read_message_id")
        return sum(
            1 for message in self.messages
            if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel_id
            and (last_id is None or message["id"] > last_id)
            and message.get("author") != character
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": [dict(message) for message in self.messages],
            "participants": {
                name: {
                    **participant,
                    "last_read_message_ids": dict(participant.get("last_read_message_ids", {})),
                }
                for name, participant in self.participants.items()
            },
            "channels": {
                channel_id: {**channel, "members": list(channel.get("members", []))}
                for channel_id, channel in self.channels.items()
            },
            "next_message_id": self.next_message_id,
        }

    def from_dict(self, data: Optional[Dict[str, Any]]):
        if not data:
            self.__init__()
            return
        self.messages = [dict(message) for message in data.get("messages", [])]
        self.channels = {PUBLIC_CHANNEL_ID: {
            "id": PUBLIC_CHANNEL_ID, "kind": "public", "name": "Public",
            "members": [], "created_by": "System",
        }}
        self.channels.update({
            str(channel_id): {
                **channel,
                "id": str(channel.get("id") or channel_id),
                "members": list(channel.get("members", [])),
            }
            for channel_id, channel in (data.get("channels", {}) or {}).items()
            if str(channel_id) != PUBLIC_CHANNEL_ID
        })
        self.participants = {}
        for name, saved in (data.get("participants", {}) or {}).items():
            participant = dict(saved)
            cursors = dict(participant.get("last_read_message_ids", {}) or {})
            if "public" not in cursors and participant.get("last_read_message_id") is not None:
                cursors["public"] = participant["last_read_message_id"]
            participant["last_read_message_ids"] = cursors
            participant.pop("last_read_message_id", None)
            self.participants[str(name)] = participant
        for message in self.messages:
            message.setdefault("channel_id", PUBLIC_CHANNEL_ID)
        self.next_message_id = int(data.get(
            "next_message_id", max((m.get("id", 0) for m in self.messages), default=0) + 1
        ))
