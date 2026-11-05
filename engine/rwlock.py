"""
engine/rwlock.py - Reader-Writer lock with writer preference and re-entrant locking.

Allows concurrent read operations while ensuring exclusive write operations.
Supports re-entrancy for both readers and writers on the same thread, and allows
a writer thread to acquire read locks without deadlocking.

@module engine/rwlock
@contributes ReadWriteLock: reader-writer lock with writer preference
@docs none pure concurrency utility
"""
import threading
from contextlib import contextmanager
from typing import Optional, Dict


class ReadWriteLock:
    """A re-entrant reader-writer lock with writer preference."""

    def __init__(self):
        self._lock = threading.Lock()
        self._read_ok = threading.Condition(self._lock)
        self._write_ok = threading.Condition(self._lock)
        # Map thread_id -> count of active read acquisitions
        self._readers: Dict[int, int] = {}
        # Active writer tracking
        self._writer_thread: Optional[int] = None
        self._writer_count: int = 0
        # Count of writers currently waiting to acquire
        self._writers_waiting: int = 0

    def acquire_read(self, timeout: Optional[float] = None) -> bool:
        """Acquire a read lock. Concurrent with other readers; waits for active/waiting writers."""
        tid = threading.get_ident()
        with self._lock:
            # Re-entrant read: already reading or current active writer
            if tid == self._writer_thread or tid in self._readers:
                self._readers[tid] = self._readers.get(tid, 0) + 1
                return True

            # Wait while a writer is active or writers are queued
            while self._writer_thread is not None or self._writers_waiting > 0:
                if not self._read_ok.wait(timeout=timeout):
                    return False
                # If timeout woke us up, check condition again
                if timeout is not None and (self._writer_thread is not None or self._writers_waiting > 0):
                    return False

            self._readers[tid] = 1
            return True

    def release_read(self):
        """Release a previously acquired read lock."""
        tid = threading.get_ident()
        with self._lock:
            if tid not in self._readers:
                return
            self._readers[tid] -= 1
            if self._readers[tid] <= 0:
                del self._readers[tid]
                # If no more readers are active, wake up a waiting writer
                if not self._readers and self._writers_waiting > 0:
                    self._write_ok.notify()

    def acquire_write(self, timeout: Optional[float] = None) -> bool:
        """Acquire an exclusive write lock. Waits for all readers to release."""
        tid = threading.get_ident()
        with self._lock:
            # Re-entrant write by the current writer
            if tid == self._writer_thread:
                self._writer_count += 1
                return True

            self._writers_waiting += 1
            try:
                # Wait until no active writer and no active readers (other than this thread if any)
                while self._writer_thread is not None or bool(self._readers):
                    # If this thread is somehow a reader, cannot upgrade without deadlock
                    if tid in self._readers and len(self._readers) > 1:
                        # Multiple readers exist; upgrading would deadlock
                        return False
                    if not self._write_ok.wait(timeout=timeout):
                        return False
                    if timeout is not None and (self._writer_thread is not None or bool(self._readers)):
                        return False

                self._writer_thread = tid
                self._writer_count = 1
                return True
            finally:
                self._writers_waiting -= 1

    def release_write(self):
        """Release an exclusive write lock."""
        tid = threading.get_ident()
        with self._lock:
            if tid != self._writer_thread:
                return
            self._writer_count -= 1
            if self._writer_count <= 0:
                self._writer_thread = None
                self._writer_count = 0
                if self._writers_waiting > 0:
                    self._write_ok.notify()
                else:
                    self._read_ok.notify_all()

    def __enter__(self):
        self.acquire_write()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_write()

    @contextmanager
    def read_lock(self, timeout: Optional[float] = None):
        """Context manager for acquiring and releasing a read lock."""
        acquired = self.acquire_read(timeout=timeout)
        if not acquired:
            raise TimeoutError("Timed out acquiring read lock")
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_lock(self, timeout: Optional[float] = None):
        """Context manager for acquiring and releasing a write lock."""
        acquired = self.acquire_write(timeout=timeout)
        if not acquired:
            raise TimeoutError("Timed out acquiring write lock")
        try:
            yield
        finally:
            self.release_write()
