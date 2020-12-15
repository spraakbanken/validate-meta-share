"""Initialise Flask application."""

import logging
import os
import sys
import time

import flask_reverse_proxy
from flask import Flask

log = logging.getLogger("validatems" + __name__)


def create_app():
    """Instanciate app."""
    app = Flask(__name__)

    # Read config
    if os.path.exists(app.config.root_path + "/../config.py") is False:
        print("copy config_default.py to config.py and add your settings")
        app.config.from_pyfile(app.config.root_path + "/../config_default.py")
    else:
        app.config.from_pyfile(app.config.root_path + "/../config.py")

    app.secret_key = app.config["SECRET_KEY"]

    # Configure logger
    logfmt = "%(asctime)-15s - %(levelname)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    if app.config.get("DEBUG"):
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                            format=logfmt, datefmt=datefmt)
    else:
        today = time.strftime("%Y-%m-%d")
        logdir = app.config.get("LOG_DIR")
        logfile = os.path.join(logdir, f"{today}.log")
        # Create log dir if it does not exist
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        logging.basicConfig(filename=logfile, level=logging.INFO,
                            format=logfmt, datefmt=datefmt)

    # Create instance_folder if it does not exist
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    log.info("Application restarted")

    # Fix proxy chaos
    app.wsgi_app = flask_reverse_proxy.ReverseProxied(app.wsgi_app)
    app.wsgi_app = FixScriptName(app.wsgi_app, app.config)

    from . import views
    app.register_blueprint(views.general)

    @app.after_request
    def cleanup(response):
        log.debug("Cleaning up")
        for filename in os.listdir(app.instance_path):
            if filename.lower().endswith(".xml"):
                file_path = os.path.join(app.instance_path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    log.error('Failed to remove %s. Reason: %s' % (file_path, e))
        return response

    return app


class FixScriptName(object):
    """Set the environment SCRIPT_NAME."""
    def __init__(self, app, config):
        self.app = app
        self.config = config

    def __call__(self, environ, start_response):
        script_name = self.config["APPLICATION_ROOT"]
        if script_name:
            environ["SCRIPT_NAME"] = script_name

        return self.app(environ, start_response)
