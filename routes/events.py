"""Live world-event SSE endpoint."""
import json
import queue
from flask import Response, jsonify, request, stream_with_context
from engine.world_events import hub


def register_events_routes(app):
    @app.route('/api/events/recent')
    def events_recent():
        count = request.args.get('count', type=int) or 50
        return jsonify({'events': hub.recent(count)})

    @app.route('/api/events')
    def world_events_stream():
        """Server-sent events: broadcast every world/graph mutation."""
        q = hub.subscribe()

        def gen():
            try:
                # hello so the client can confirm the stream is open
                yield 'event: hello\ndata: {"ok": true}\n\n'
                while True:
                    try:
                        ev = q.get(timeout=15)
                        yield 'data: ' + json.dumps(ev) + '\n\n'
                    except queue.Empty:
                        yield ': keepalive\n\n'
            except GeneratorExit:
                pass
            finally:
                hub.unsubscribe(q)

        return Response(stream_with_context(gen()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
