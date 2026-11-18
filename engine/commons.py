"""Conversation state for The Commons.

@module commons
@contributes channels, membership, ordered messages, per-character read cursors, edit and delete message
@powers The Commons communication
@relates VirtualWorld, routes/commons.py
@docs docs/virtualWorld/Gameplay/The Commons.md

Character cognition and memory remain on Player and the standard agent path.
This model stores communication state only.
"""
import copy
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


PUBLIC_CHANNEL_ID = "public"
DEFAULT_COMMONS_THEME = "live_social"
COMMONS_THEMES = frozenset((DEFAULT_COMMONS_THEME, "town_board"))


class ChatAuthorizationError(PermissionError):
    """Raised when a perspective cannot read or post in a channel."""


class Commons:
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
        self.active_branch_id: str = "main"
        self.branches: Dict[str, Dict[str, Any]] = {
            "main": {
                "id": "main",
                "name": "main",
                "parent_id": None,
                "fork_message_id": None,
                "snapshot": None,
            }
        }
        self.anchored_clock: Optional[Dict[str, Any]] = None
        self.standalone_memories: Dict[str, List[Dict[str, Any]]] = {}

    def _capture_branch_snapshot(self) -> Dict[str, Any]:
        return {
            "messages": copy.deepcopy(self.messages),
            "participants": copy.deepcopy(self.participants),
            "channels": copy.deepcopy(self.channels),
            "next_message_id": self.next_message_id,
            "anchored_clock": copy.deepcopy(self.anchored_clock),
            "standalone_memories": copy.deepcopy(self.standalone_memories),
        }

    def _restore_branch_snapshot(self, snap: Optional[Dict[str, Any]]) -> None:
        if not snap:
            return
        self.messages = copy.deepcopy(snap.get("messages", []))
        self.participants = copy.deepcopy(snap.get("participants", {}))
        self.channels = copy.deepcopy(snap.get("channels", {
            PUBLIC_CHANNEL_ID: {
                "id": PUBLIC_CHANNEL_ID,
                "kind": "public",
                "name": "Public",
                "members": [],
                "created_by": "System",
            }
        }))
        self.next_message_id = int(snap.get("next_message_id", 1) or 1)
        self.anchored_clock = copy.deepcopy(snap.get("anchored_clock"))
        self.standalone_memories = copy.deepcopy(snap.get("standalone_memories", {}))

    def list_branches(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": bid,
                "name": b.get("name", bid),
                "parent_id": b.get("parent_id"),
                "fork_message_id": b.get("fork_message_id"),
                "active": bid == self.active_branch_id,
            }
            for bid, b in self.branches.items()
        ]

    def fork_branch(self, name: str = "", from_message_id: Optional[int] = None) -> Dict[str, Any]:
        """Fork the active conversation into a new isolated branch."""
        self.branches.setdefault(self.active_branch_id, {
            "id": self.active_branch_id, "name": self.active_branch_id,
            "parent_id": None, "fork_message_id": None, "snapshot": None,
        })
        self.branches[self.active_branch_id]["snapshot"] = self._capture_branch_snapshot()

        snap = self._capture_branch_snapshot()
        if from_message_id is not None:
            cutoff = int(from_message_id)
            snap["messages"] = [m for m in snap["messages"] if int(m.get("id", 0)) <= cutoff]
            snap["next_message_id"] = max((int(m.get("id", 0)) for m in snap["messages"]), default=0) + 1
            for p in snap["participants"].values():
                cursors = p.get("last_read_message_ids") or {}
                for cid, val in list(cursors.items()):
                    if val is not None and int(val) > cutoff:
                        cursors[cid] = cutoff
        branch_id = f"branch_{uuid.uuid4().hex[:8]}"
        label = str(name or "").strip()[:60] or f"branch-{len(self.branches)}"
        self.branches[branch_id] = {
            "id": branch_id,
            "name": label,
            "parent_id": self.active_branch_id,
            "fork_message_id": from_message_id,
            "snapshot": snap,
        }
        self.active_branch_id = branch_id
        self._restore_branch_snapshot(snap)
        return {
            "id": branch_id,
            "name": label,
            "parent_id": self.branches[branch_id]["parent_id"],
            "fork_message_id": from_message_id,
            "active": True,
        }

    def switch_branch(self, branch_id: str) -> Dict[str, Any]:
        bid = str(branch_id or "").strip()
        if bid not in self.branches:
            raise KeyError("Branch not found")
        if bid == self.active_branch_id:
            return {"id": bid, "name": self.branches[bid].get("name", bid), "active": True}
        self.branches.setdefault(self.active_branch_id, {
            "id": self.active_branch_id, "name": self.active_branch_id,
            "parent_id": None, "fork_message_id": None, "snapshot": None,
        })
        self.branches[self.active_branch_id]["snapshot"] = self._capture_branch_snapshot()
        self.active_branch_id = bid
        self._restore_branch_snapshot(self.branches[bid].get("snapshot"))
        return {"id": bid, "name": self.branches[bid].get("name", bid), "active": True}

    def reset_session(self, preserve_participants: bool = True) -> None:
        """Reset conversation messages/channels/memories on the active branch."""
        kept_participants = {}
        if preserve_participants:
            for name, p in self.participants.items():
                kept_participants[name] = {
                    "active": bool(p.get("active", name != "User")),
                    "blocked": bool(p.get("blocked", False)),
                    "last_read_message_ids": {},
                    "muted_channels": [],
                }
        self.messages = []
        self.channels = {
            PUBLIC_CHANNEL_ID: {
                "id": PUBLIC_CHANNEL_ID,
                "kind": "public",
                "name": "Public",
                "members": [],
                "created_by": "System",
            }
        }
        self.participants = kept_participants
        self.next_message_id = 1
        self.standalone_memories = {}

    def set_anchored_clock(self, anchor_datetime: Optional[str] = None, now_epoch: Optional[float] = None) -> Dict[str, Any]:
        """Set standalone anchored real-time clock: anchor_datetime + real elapsed seconds."""
        epoch = float(time.time() if now_epoch is None else now_epoch)
        if anchor_datetime:
            raw = str(anchor_datetime).strip().replace(" ", "T")
            if len(raw) == 16:
                raw = f"{raw}:00"
            dt = datetime.fromisoformat(raw[:19])
        else:
            dt = datetime.now().replace(microsecond=0)
        self.anchored_clock = {
            "anchor_datetime": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "anchor_real_epoch": epoch,
        }
        return dict(self.anchored_clock)

    def current_anchored_datetime(self, now_epoch: Optional[float] = None) -> datetime:
        if not self.anchored_clock:
            self.set_anchored_clock(now_epoch=now_epoch)
        epoch = float(time.time() if now_epoch is None else now_epoch)
        anchor_dt = datetime.fromisoformat(str(self.anchored_clock["anchor_datetime"])[:19])
        elapsed = max(0.0, epoch - float(self.anchored_clock.get("anchor_real_epoch", epoch)))
        return anchor_dt + timedelta(seconds=elapsed)

    def current_anchored_iso(self, now_epoch: Optional[float] = None) -> str:
        return self.current_anchored_datetime(now_epoch=now_epoch).strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def format_iso_label(iso_dt: str) -> str:
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        dt = datetime.fromisoformat(str(iso_dt)[:19])
        return f"{months[dt.month - 1]} {dt.day}, {dt.year} {dt.strftime('%H:%M')}"

    def add_standalone_memory(self, char_name: str, entry: Dict[str, Any], now_epoch: Optional[float] = None) -> Dict[str, Any]:
        mem = dict(entry)
        mem.setdefault("id", f"cmem_{uuid.uuid4().hex[:8]}")
        mem.setdefault("world_datetime", self.current_anchored_iso(now_epoch=now_epoch))
        mem.setdefault("branch_id", self.active_branch_id)
        mem.setdefault("timestamp", time.time())
        self.standalone_memories.setdefault(char_name, []).append(mem)
        return mem

    def set_participant(self, name: str, active: Optional[bool] = None,
                        blocked: Optional[bool] = None):
        if name not in self.participants:
            self.participants[name] = {
                "active": name != "User",
                "blocked": False,
                "last_read_message_ids": {},
                "muted_channels": [],
            }
        participant = self.participants[name]
        participant.setdefault("last_read_message_ids", {})
        participant.setdefault("muted_channels", [])
        if active is not None:
            participant["active"] = bool(active)
        if blocked is not None:
            participant["blocked"] = bool(blocked)
        return participant

    def set_muted(self, actor: str, channel_id: str, muted: bool) -> bool:
        self.require_access(actor, channel_id)
        participant = self.set_participant(actor)
        cid = str(channel_id)
        muted_channels = [
            str(existing) for existing in (participant.get("muted_channels") or [])
            if str(existing) != cid
        ]
        is_muted = bool(muted)
        if is_muted:
            muted_channels.append(cid)
        participant["muted_channels"] = muted_channels
        return is_muted

    def is_muted(self, character: str, channel_id: str) -> bool:
        participant = self.participants.get(character) or {}
        return str(channel_id) in (participant.get("muted_channels") or [])

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
        muted_channels = {str(cid) for cid in (participant.get("muted_channels") or [])}
        result = []
        for channel in self.channels.values():
            if not self.can_access(character, channel["id"]):
                continue
            latest_id = max(
                (message["id"] for message in self.messages
                 if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel["id"]
                 and not message.get("deleted")),
                default=None,
            )
            cursor = cursors.get(channel["id"])
            unread = sum(
                1 for message in self.messages
                if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel["id"]
                and (cursor is None or message["id"] > cursor)
                and message.get("author") != character
                and not message.get("deleted")
            )
            result.append({
                **channel,
                "members": list(channel["members"]),
                "unread_count": unread,
                "last_read_message_id": cursor,
                "latest_message_id": latest_id,
                "muted": channel["id"] in muted_channels,
            })
        return sorted(result, key=lambda item: (
            item["id"] != PUBLIC_CHANNEL_ID,
            -(item["latest_message_id"] or 0),
            item["name"].casefold(),
        ))

    def post_message(self, author: str, text: str = "", tick: int = 0,
                     channel_id: str = PUBLIC_CHANNEL_ID,
                     attachments: Optional[List[Dict[str, Any]]] = None,
                     world_datetime: Optional[str] = None) -> Dict[str, Any]:
        self.require_access(author, channel_id)
        if not text and not attachments:
            raise ValueError("Message must have text or attachments")
        message = {
            "id": self.next_message_id,
            "channel_id": channel_id,
            "author": author,
            "text": text,
            "timestamp": time.time(),
            "tick": tick,
            "branch_id": self.active_branch_id,
        }
        if world_datetime:
            message["world_datetime"] = str(world_datetime)
        if attachments:
            message["attachments"] = list(attachments)
        self.next_message_id += 1
        self.messages.append(message)
        return message

    def edit_message(self, message_id: int, author: str, text: str,
                     players: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Edit the text of an existing message (task-891).

        Only the author may edit the message. Enforces channel access.
        Records edited=True, original_text, and edited_at timestamp.
        """
        for msg in self.messages:
            if msg["id"] == message_id:
                if msg.get("deleted"):
                    raise ValueError("Cannot edit a deleted message")
                if msg.get("author") != author:
                    raise ChatAuthorizationError("Cannot edit another author's message")
                channel_id = msg.get("channel_id", PUBLIC_CHANNEL_ID)
                self.require_access(author, channel_id)
                if not msg.get("edited"):
                    msg["original_text"] = msg.get("text", "")
                old_text = msg.get("text", "")
                msg["text"] = str(text or "")
                msg["edited"] = True
                msg["edited_at"] = time.time()

                if players:
                    for p in players.values():
                        for mem in getattr(p, "memories", []) or []:
                            if isinstance(mem, dict) and old_text and old_text in str(mem.get("text", "")):
                                mem["text"] = str(mem["text"]).replace(old_text, msg["text"])
                                mem["edited"] = True

                return dict(msg)
        raise KeyError("Message not found")

    def delete_message(self, message_id: int, author: str,
                       players: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Delete a message, keeping a tombstone (task-891).

        Only the author may delete the message. Enforces channel access.
        Retains the message in self.messages with deleted=True to keep
        the id sequence and read cursors stable.
        """
        for msg in self.messages:
            if msg["id"] == message_id:
                if msg.get("deleted"):
                    return dict(msg)
                if msg.get("author") != author:
                    raise ChatAuthorizationError("Cannot delete another author's message")
                channel_id = msg.get("channel_id", PUBLIC_CHANNEL_ID)
                self.require_access(author, channel_id)
                original_text = msg.get("text", "")
                msg["original_text"] = original_text
                msg["deleted"] = True
                msg["deleted_at"] = time.time()
                msg["text"] = ""

                if players:
                    for p in players.values():
                        for mem in getattr(p, "memories", []) or []:
                            if isinstance(mem, dict) and original_text and original_text in str(mem.get("text", "")):
                                mem["retracted"] = True
                                mem["text"] = str(mem["text"]).replace(original_text, f"[Retracted by {author}]")

                return dict(msg)
        raise KeyError("Message not found")

    def read_messages(self, character: str, mode: str = "latest", n: int = 3,
                      from_id: Optional[int] = None, to_id: Optional[int] = None,
                      channel_id: str = PUBLIC_CHANNEL_ID,
                      include_deleted: bool = False) -> List[Dict[str, Any]]:
        self.require_access(character, channel_id)
        participant = self.set_participant(character)
        cursors = participant["last_read_message_ids"]
        last_id = cursors.get(channel_id)
        messages = [
            message for message in self.messages
            if message.get("channel_id", PUBLIC_CHANNEL_ID) == channel_id
        ]
        visible = messages if include_deleted else [m for m in messages if not m.get("deleted")]
        if mode == "latest":
            count = max(1, min(50, n or 3))
            results = visible[-count:]
        elif mode == "all":
            results = [message for message in visible
                       if last_id is None or message["id"] > last_id]
        elif mode == "range":
            lower = from_id or 1
            upper = to_id or (visible[-1]["id"] if visible else 1)
            results = [message for message in visible
                       if lower <= message["id"] <= upper]
        else:
            results = visible[-3:]

        if results:
            highest_id = max(message["id"] for message in results)
            if last_id is None or highest_id > last_id:
                cursors[channel_id] = highest_id
        elif mode == "all" and messages:
            highest_id = max(message["id"] for message in messages)
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
            and not message.get("deleted")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": [dict(message) for message in self.messages],
            "participants": {
                name: {
                    **participant,
                    "last_read_message_ids": dict(participant.get("last_read_message_ids", {})),
                    "muted_channels": list(participant.get("muted_channels", [])),
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
            participant["muted_channels"] = list(dict.fromkeys(
                str(cid) for cid in (participant.get("muted_channels") or [])
            ))
            self.participants[str(name)] = participant
        for message in self.messages:
            message.setdefault("channel_id", PUBLIC_CHANNEL_ID)
        self.next_message_id = int(data.get(
            "next_message_id", max((m.get("id", 0) for m in self.messages), default=0) + 1
        ))
