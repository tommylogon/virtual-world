import os
import logging
from flask import Flask, render_template
from logger import setup_logger
from version import APP_VERSION

logger = logging.getLogger(__name__)


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
                               app_version=APP_VERSION)

    @app.route('/GLM')
    def glm_template():
        return render_template('GLM_index.html')

    @app.route('/deepseek')
    def deepseek_template():
        return render_template('deepseek_index.html')
