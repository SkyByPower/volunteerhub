import os

from flask import Flask

from config import BASE_DIR, Config
from .extensions import csrf, db, login_manager, migrate
from .i18n import LazyText, init_i18n


def create_app(config_class=Config):
    app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PRIVATE_UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_message = LazyText("flash.need_login")

    init_i18n(app)

    from .routes import register_blueprints
    register_blueprints(app)

    from .errors import register_error_handlers
    register_error_handlers(app)

    from .cli import register_cli
    register_cli(app)

    return app
