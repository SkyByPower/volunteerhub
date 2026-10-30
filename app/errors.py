from flask import jsonify, render_template, request

from .extensions import db

ERRORS = {
    403: ("err.403", "err.403d", "bi-shield-lock"),
    404: ("err.404", "err.404d", "bi-compass"),
    413: ("err.413", "v.too_large", "bi-file-earmark-x"),
    500: ("err.500", "err.500d", "bi-cone-striped"),
}


def register_error_handlers(app):
    def handler(code):
        def handle(error):
            if code == 500:
                db.session.rollback()
            if request.path.startswith("/api/"):
                return jsonify(error=getattr(error, "description", str(error)), status=code), code
            title, desc, icon = ERRORS[code]
            return render_template(f"errors/{code}.html", code=code, title=title, desc=desc, icon=icon), code

        return handle

    for code in ERRORS:
        app.register_error_handler(code, handler(code))
