import os
import uuid
from functools import wraps

from flask import abort, current_app, flash, request
from flask_login import current_user
from werkzeug.utils import secure_filename

from .i18n import t

# file signatures: the first bytes must match the extension
SIGNATURES = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],
}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def _extension(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def _signature_ok(file_storage, ext):
    head = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    if ext == "webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return any(head.startswith(sig) for sig in SIGNATURES.get(ext, []))


def save_upload(file_storage, kind):
    """Validate and save an uploaded file.

    kind: "image" or "doc". Returns the stored relative path (e.g. "docs/ab12_file.pdf")
    or None if the file is invalid (a flash message explains why).
    """
    if not file_storage or not file_storage.filename:
        return None
    allowed = (
        current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        if kind == "image"
        else current_app.config["ALLOWED_DOC_EXTENSIONS"]
    )
    ext = _extension(file_storage.filename)
    if ext not in allowed:
        flash(t("v.image_only" if kind == "image" else "v.pdf_only"), "danger")
        return None
    if not _signature_ok(file_storage, ext):
        flash(t("v.bad_file"), "danger")
        return None

    safe = secure_filename(file_storage.filename) or f"file.{ext}"
    rel_path = f"{'images' if kind == 'image' else 'docs'}/{uuid.uuid4().hex[:12]}_{safe}"
    path = upload_path(rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_storage.save(path)
    return rel_path


def upload_path(rel_path):
    """Images live under static/ (public); documents live in instance/ (private)."""
    root = current_app.config["PRIVATE_UPLOAD_FOLDER" if rel_path.startswith("docs/") else "UPLOAD_FOLDER"]
    return os.path.join(root, rel_path)


def delete_upload(rel_path):
    # the seeded sample certificate is shared by several rows
    if not rel_path or rel_path.endswith("sample_certificate.pdf"):
        return
    path = upload_path(rel_path)
    if os.path.isfile(path):
        os.remove(path)


def safe_sort(arg_name, options, default):
    """Pick a sort key from a whitelist so request args never reach order_by directly."""
    key = request.args.get(arg_name, default)
    return key if key in options else default


def safe_next(target, fallback):
    """Return target only if it is a local path (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return fallback
