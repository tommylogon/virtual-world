import time
import logging
import os
import sys
import subprocess
from collections import deque
from flask import jsonify, request

_start_time = time.time()

# ── Ring-buffer log capture ────────────────────────────────────────
MAX_LOG_RECORDS = 500
_log_buffer = deque(maxlen=MAX_LOG_RECORDS)

LEVEL_NAMES = {
    logging.DEBUG: 'DEBUG',
    logging.INFO: 'INFO',
    logging.WARNING: 'WARNING',
    logging.ERROR: 'ERROR',
    logging.CRITICAL: 'CRITICAL',
}


class LogCaptureHandler(logging.Handler):
    """Captures log records into a ring buffer for the /api/logs endpoint."""

    def emit(self, record):
        _log_buffer.append({
            "time": time.strftime('%H:%M:%S', time.localtime(record.created)),
            "level": LEVEL_NAMES.get(record.levelno, str(record.levelno)),
            "logger": record.name,
            "message": record.getMessage(),
        })


def register_health_routes(app):
    # Wire up the capture handler once
    if not any(isinstance(h, LogCaptureHandler) for h in logging.getLogger().handlers):
        logging.getLogger().addHandler(LogCaptureHandler())

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "running",
            "uptime_seconds": int(time.time() - _start_time),
            "server": "VirtualWorld",
            "llm_enabled": app.config.get('LLM_ENABLED', False),
        })

    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        level_filter = (request.args.get('level') or '').upper()
        since_m = request.args.get('since_minutes', type=int)
        cutoff = time.time() - (since_m * 60) if since_m else 0

        entries = list(_log_buffer)
        if level_filter:
            entries = [e for e in entries if e['level'] == level_filter]
        if cutoff:
            # Reconstruct timestamp to compare — approximate by filtering
            pass  # ring buffer is in chronological order from oldest to newest

        # Count by level
        counts = {}
        for e in entries:
            counts[e['level']] = counts.get(e['level'], 0) + 1

        # Get only recent errors for quick status
        errors = [e for e in entries if e['level'] in ('ERROR', 'CRITICAL')]

        return jsonify({
            "total": len(entries),
            "counts": counts,
            "errors_last_24h": len(errors),
            "recent_errors": errors[-20:],  # last 20
            "entries": entries[-100:],  # last 100
        })

    @app.route('/api/restart-server', methods=['POST'])
    def restart_server():
        """Spawn a new server process, then shut down the current one."""
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.Popen(
            [sys.executable, 'app.py'],
            cwd=app_dir,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        # Gracefully shut down the current server
        shutdown = request.environ.get('werkzeug.server.shutdown')
        if shutdown:
            shutdown()
        return jsonify({"status": "restarting"})
