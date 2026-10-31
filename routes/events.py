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
        if q is None:
            return jsonify({
                'error': 'Subscriber connection cap reached',
                'cap': hub.MAX_SUBSCRIBERS,
            }), 429

        last_id_raw = request.headers.get('Last-Event-ID') or request.args.get('since')

        def gen():
            try:
                # hello so the client can confirm the stream is open
                yield 'event: hello\ndata: {"ok": true}\n\n'

                # Catch-up replay for reconnecting clients
                if last_id_raw is not None:
                    try:
                        last_seq = int(last_id_raw)
                        replayed = hub.since(last_seq)
                        if replayed is None:
                            # Missed events fell outside buffer: request full resync
                            yield 'data: {"type": "resync_required", "reason": "buffer_expired"}\n\n'
                        else:
                            for ev in replayed:
                                yield f'id: {ev.get("seq", "")}\ndata: ' + json.dumps(ev) + '\n\n'
                    except (ValueError, TypeError):
                        pass

                while True:
                    try:
                        ev = q.get(timeout=15)
                        yield f'id: {ev.get("seq", "")}\ndata: ' + json.dumps(ev) + '\n\n'
                    except queue.Empty:
                        yield ': keepalive\n\n'
            except (GeneratorExit, BrokenPipeError, ConnectionResetError):
                pass
            finally:
                hub.unsubscribe(q)

        return Response(stream_with_context(gen()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
