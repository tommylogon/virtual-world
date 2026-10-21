import hashlib
import os
import logging
from flask import Flask, jsonify, redirect, render_template, url_for
from logger import setup_logger
from version import APP_VERSION

logger = logging.getLogger(__name__)


def _client_asset_version(app):
    """Fingerprint files that are delivered to an already-open browser tab."""
    roots = [
        os.path.join(app.static_folder or '', 'js'),
        os.path.join(app.static_folder or '', 'css'),
    ]
    files = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for current, _dirs, names in os.walk(root):
            for name in names:
                if name.endswith(('.js', '.css')):
                    files.append(os.path.join(current, name))

    template = os.path.join(app.root_path, app.template_folder or 'templates', 'index.html')
    version_file = os.path.join(app.root_path, 'version.py')
    files.extend(path for path in (template, version_file) if os.path.isfile(path))

    digest = hashlib.sha256()
    for path in sorted(files):
        try:
            stat = os.stat(path)
        except OSError:
            continue
        relative = os.path.relpath(path, app.root_path).replace(os.sep, '/')
        digest.update(f'{relative}:{stat.st_mtime_ns}:{stat.st_size}\n'.encode('utf-8'))
    return digest.hexdigest()[:16]


def register_pages_routes(app):
    """Register page-serving routes (favicon, index, alternate frontends)."""

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    @app.route('/')
    def index():
        source = getattr(app.world, '_scenario_source', None)
        scenario_name = os.path.splitext(os.path.basename(source))[0] if source else ''
        return render_template('index.html', scenario_name=scenario_name,
                               app_version=APP_VERSION,
                               client_version=_client_asset_version(app))

    @app.route('/api/client-version')
    def client_version():
        response = jsonify({'version': _client_asset_version(app)})
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        return response

    @app.route('/GLM')
    def glm_template():
        return render_template('GLM_index.html')

    @app.route('/soak')
    def soak_page():
        """Standalone analytics UI for the headless soak runner."""
        return render_template('soak.html', app_version=APP_VERSION)

    @app.route('/commons')
    def commons_page():
        """The Commons social communication page (task-824)."""
        return render_template('commons.html', app_version=APP_VERSION)

    @app.route('/stage-chat')
    def legacy_commons_page_redirect():
        """Redirect the former page address to The Commons."""
        return redirect(url_for('commons_page'), code=301)

    @app.route('/deepseek')
    def deepseek_template():
        return render_template('deepseek_index.html')
