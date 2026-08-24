import os

from flask import Flask

from app.extensions import bootstrap, db, login, migrate
from config import config

login.login_view = 'auth.login'


def create_app(config_name=None):
    config_name = config_name or os.environ.get('FLASK_CONFIG') or 'default'
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    bootstrap.init_app(app)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app import cli
    cli.register(app)

    return app
