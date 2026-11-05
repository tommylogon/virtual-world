"""
tests/test_concurrency_race.py - Concurrency test verifying bug-536 fix.

Verifies that concurrent GET read paths and mutating requests do not raise
'RuntimeError: dictionary changed size during iteration' or 500s.
"""
import threading
import time
import pytest
from engine.rwlock import ReadWriteLock
from graph import WorldGraph, Node, Edge


def test_rwlock_basic_concurrency():
    """Verify that multiple readers can hold the lock concurrently, but writers are exclusive."""
    lock = ReadWriteLock()
    active_readers = 0
    max_concurrent_readers = 0
    writer_active = False
    violations = []

    def reader_task():
        nonlocal active_readers, max_concurrent_readers
        for _ in range(20):
            with lock.read_lock():
                if writer_active:
                    violations.append("Reader entered while writer active")
                active_readers += 1
                if active_readers > max_concurrent_readers:
                    max_concurrent_readers = active_readers
                time.sleep(0.001)
                active_readers -= 1

    def writer_task():
        nonlocal writer_active
        for _ in range(5):
            with lock.write_lock():
                writer_active = True
                if active_readers > 0:
                    violations.append(f"Writer active with {active_readers} readers")
                time.sleep(0.005)
                writer_active = False

    threads = [threading.Thread(target=reader_task) for _ in range(4)]
    threads.append(threading.Thread(target=writer_task))

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not violations, f"Lock violations detected: {violations}"
    assert max_concurrent_readers > 1, "Expected multiple concurrent readers"


def test_rwlock_reentrancy():
    """Verify re-entrant read and write locking on the same thread."""
    lock = ReadWriteLock()

    # Nested read locks
    with lock.read_lock():
        with lock.read_lock():
            assert True

    # Nested write locks
    with lock.write_lock():
        with lock.write_lock():
            # Writer acquiring read lock
            with lock.read_lock():
                assert True


def test_graph_concurrent_read_write_stress():
    """Stress test concurrent WorldGraph mutations and reader iterations."""
    graph = WorldGraph()
    # Seed initial areas and items
    for i in range(50):
        graph.add_node(Node(id=f"area_{i}", type="area", name=f"Area {i}"))
        graph.add_node(Node(id=f"item_{i}", type="item", name=f"Item {i}"))
        graph.add_edge(Edge(source=f"item_{i}", target=f"area_{i}", type="in"))

    stop_event = threading.Event()
    exceptions = []

    def writer_loop():
        count = 0
        while not stop_event.is_set() and count < 100:
            count += 1
            node_id = f"scratch_{count}"
            try:
                with graph.write_lock():
                    graph.add_node(Node(id=node_id, type="item", name=f"Scratch {count}"))
                    graph.add_edge(Edge(source=node_id, target="area_0", type="in"))
                    graph._rebuild_indexes()
                    graph.remove_node(node_id)
            except Exception as e:
                exceptions.append(f"Writer error: {e}")
            time.sleep(0.001)

    def reader_loop():
        while not stop_event.is_set():
            try:
                with graph.read_lock():
                    d = graph.to_dict()
                    assert len(d["nodes"]) >= 100
                    # Test edge indexes while mutations happen
                    edges = graph.get_edges_for_source("area_0")
                    targets = graph.get_edges_for_target("area_0")
            except Exception as e:
                exceptions.append(f"Reader error: {e}")
                break
            time.sleep(0.001)

    writer_thread = threading.Thread(target=writer_loop)
    reader_threads = [threading.Thread(target=reader_loop) for _ in range(4)]

    for t in reader_threads:
        t.start()
    writer_thread.start()

    writer_thread.join(timeout=10)
    stop_event.set()
    for t in reader_threads:
        t.join(timeout=5)

    assert not exceptions, f"Concurrent exceptions raised: {exceptions}"


def test_api_concurrent_get_and_mutations():
    """Verify that concurrent API GET reads and POST mutations return 200 without racing."""
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    exceptions = []
    stop_event = threading.Event()

    def get_reader():
        while not stop_event.is_set():
            try:
                resp = client.get("/api/state")
                assert resp.status_code == 200
            except Exception as e:
                exceptions.append(f"GET /api/state failed: {e}")
                break
            time.sleep(0.002)

    def post_writer():
        for i in range(15):
            try:
                # Add a node then delete it
                resp = client.post("/api/graph/node", json={
                    "id": f"concurrency_node_{i}",
                    "type": "item",
                    "name": f"Concurrency Node {i}"
                })
                assert resp.status_code == 200
                resp_del = client.delete(f"/api/graph/node/concurrency_node_{i}")
                assert resp_del.status_code == 200
            except Exception as e:
                exceptions.append(f"Mutation failed: {e}")
                break
            time.sleep(0.005)

    reader_thread = threading.Thread(target=get_reader)
    writer_thread = threading.Thread(target=post_writer)

    reader_thread.start()
    writer_thread.start()

    writer_thread.join(timeout=10)
    stop_event.set()
    reader_thread.join(timeout=5)

    assert not exceptions, f"Concurrent API failures: {exceptions}"
