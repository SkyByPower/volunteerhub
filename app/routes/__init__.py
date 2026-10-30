from ..extensions import csrf


def register_blueprints(app):
    from .api import bp as api_bp
    from .assignments import bp as assignments_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .projects import bp as projects_bp
    from .volunteers import bp as volunteers_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(projects_bp, url_prefix="/projects")
    app.register_blueprint(volunteers_bp, url_prefix="/volunteers")
    app.register_blueprint(assignments_bp, url_prefix="/assignments")
    app.register_blueprint(api_bp, url_prefix="/api")
    csrf.exempt(api_bp)  # API uses token auth instead of CSRF tokens
