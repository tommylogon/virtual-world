"""World event broadcast hub."""
import queue
import threading
import time
from collections import deque


class WorldEventHub:
    """Fan-out bus for live world/graph changes.

    The game has no server-push channel today: the GUI's event stream is built
    client-side from agent actions, so edits made by an external agent (e.g. via
    the MCP server) would only appear after a manual refresh. This hub gives any
    authoring path a way to broadcast 'something changed' so the live GUI can
    refetch state in real time.

    Keeps a short rollback buffer so late subscribers (MCP resource reads, page
    reloads) can see the most recent events instead of missing them entirely.
    """

    MAX_SUBSCRIBERS = 32

    def __init__(self, buffer_size=200):
        self._subscribers = []          # list of queue.Queue
        self._buffer = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._seq = 0

    def publish(self, event):
        """Broadcast an event dict to every subscriber. Never raises."""
        if not isinstance(event, dict):
            return
        with self._lock:
            self._seq += 1
            event = dict(event)
            event['seq'] = self._seq
            event['ts'] = time.time()
            self._buffer.append(event)
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                try:
                    q.get_nowait()
                except Exception:
                    pass
                try:
                    q.put_nowait({
                        'type': 'resync_required',
                        'reason': 'queue_overflow',
                        'seq': self._seq,
                        'ts': event['ts'],
                    })
                except Exception:
                    pass
            except Exception:
                pass

    def subscribe(self):
        """Return a fresh queue for one SSE client, or None if cap reached."""
        with self._lock:
            if len(self._subscribers) >= self.MAX_SUBSCRIBERS:
                return None
            q = queue.Queue(maxsize=256)
            self._subscribers.append(q)
            return q

    def unsubscribe(self, q):
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def recent(self, count=50):
        with self._lock:
            buf = list(self._buffer)
        return buf[-count:] if count > 0 else buf

    def since(self, seq: int):
        """Return events occurring strictly after sequence number `seq`.

        If `seq` is older than the oldest buffered event, returns None to
        signal that events were lost and a full resync is needed.
        """
        with self._lock:
            if not self._buffer:
                return []
            oldest_seq = self._buffer[0]['seq']
            if seq < oldest_seq - 1:
                return None
            return [e for e in self._buffer if e['seq'] > seq]

    def subscribers_count(self):
        with self._lock:
            return len(self._subscribers)


# Process-global singleton so routes and the after_request hook share state.
hub = WorldEventHub()
