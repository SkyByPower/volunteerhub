"""REST API (JSON). Auth: header `X-API-Key: <token>` (get it via POST /api/auth/token or the profile page)."""
from datetime import date
from functools import wraps

from flask import Blueprint, abort, g, jsonify, request
from sqlalchemy import or_

from ..extensions import db
from ..models import (
    ASSIGNMENT_STATUSES, PROJECT_CATEGORIES, PROJECT_STATUSES, Assignment, Project, Volunteer,
)

bp = Blueprint("api", __name__)


def error(message, code=400, **extra):
    return jsonify(error=message, status=code, **extra), code


def token_required(admin=False):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            token = request.headers.get("X-API-Key") or ""
            auth = request.headers.get("Authorization", "")
            if not token and auth.startswith("Bearer "):
                token = auth[7:]
            user = Volunteer.query.filter_by(api_token=token).first() if token else None
            if not user:
                return error("Invalid or missing API token", 401)
            if admin and not user.is_admin:
                return error("Admin role required", 403)
            g.api_user = user
            return view(*args, **kwargs)

        return wrapped

    return decorator


def paginated(query, serializer):
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    p = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(items=[serializer(i) for i in p.items], page=p.page, pages=p.pages,
                   per_page=per_page, total=p.total)


def parse_project(data, partial=False):
    """Validate a project JSON payload. Returns (clean_fields, errors)."""
    clean, errors = {}, {}
    rules = {
        "title": lambda v: isinstance(v, str) and 3 <= len(v.strip()) <= 150,
        "description": lambda v: isinstance(v, str) and 10 <= len(v.strip()) <= 5000,
        "location": lambda v: isinstance(v, str) and 2 <= len(v.strip()) <= 120,
        "category": lambda v: v in PROJECT_CATEGORIES,
        "status": lambda v: v in PROJECT_STATUSES,
        "capacity": lambda v: isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 500,
    }
    required = {"title", "description", "location", "start_date"}
    for field, ok in rules.items():
        if field in data:
            if ok(data[field]):
                clean[field] = data[field].strip() if isinstance(data[field], str) else data[field]
            else:
                errors[field] = "invalid value"
    for field in ("start_date", "end_date"):
        if data.get(field):
            try:
                clean[field] = date.fromisoformat(data[field])
            except (TypeError, ValueError):
                errors[field] = "expected YYYY-MM-DD"
    if not partial:
        for field in required - set(data):
            errors[field] = "required"
    start, end = clean.get("start_date"), clean.get("end_date")
    if start and end and end < start:
        errors["end_date"] = "must be after start_date"
    return clean, errors


@bp.post("/auth/token")
def get_token():
    data = request.get_json(silent=True) or {}
    user = Volunteer.query.filter_by(email=str(data.get("email", "")).strip().lower()).first()
    if not user or not user.check_password(str(data.get("password", ""))):
        return error("Invalid credentials", 401)
    if not user.api_token:
        user.generate_token()
        db.session.commit()
    return jsonify(token=user.api_token, user=user.to_dict())


@bp.get("/stats")
def stats():
    return jsonify(
        projects=Project.query.count(),
        volunteers=Volunteer.query.filter_by(role="volunteer").count(),
        assignments={s: Assignment.query.filter_by(status=s).count() for s in ASSIGNMENT_STATUSES},
    )


# ---------- projects ----------

@bp.get("/projects")
def list_projects():
    query = Project.query
    if q := request.args.get("q", "").strip():
        query = query.filter(or_(Project.title.ilike(f"%{q}%"), Project.location.ilike(f"%{q}%")))
    if (cat := request.args.get("category")) in PROJECT_CATEGORIES:
        query = query.filter_by(category=cat)
    if (st := request.args.get("status")) in PROJECT_STATUSES:
        query = query.filter_by(status=st)
    return paginated(query.order_by(Project.created_at.desc()), Project.to_dict)


@bp.get("/projects/<int:project_id>")
def get_project(project_id):
    project = db.session.get(Project, project_id) or abort(404, "Project not found")
    data = project.to_dict()
    data["assignments"] = [a.to_dict() for a in project.assignments]
    return jsonify(data)


@bp.post("/projects")
@token_required(admin=True)
def create_project():
    clean, errors = parse_project(request.get_json(silent=True) or {})
    if errors:
        return error("Validation failed", 422, fields=errors)
    project = Project(creator_id=g.api_user.id, **clean)
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@bp.put("/projects/<int:project_id>")
@token_required(admin=True)
def update_project(project_id):
    project = db.session.get(Project, project_id) or abort(404, "Project not found")
    clean, errors = parse_project(request.get_json(silent=True) or {}, partial=True)
    if errors:
        return error("Validation failed", 422, fields=errors)
    for key, value in clean.items():
        setattr(project, key, value)
    db.session.commit()
    return jsonify(project.to_dict())


@bp.delete("/projects/<int:project_id>")
@token_required(admin=True)
def delete_project(project_id):
    project = db.session.get(Project, project_id) or abort(404, "Project not found")
    db.session.delete(project)
    db.session.commit()
    return jsonify(message="deleted", id=project_id)


# ---------- assignments ----------

@bp.get("/assignments")
@token_required()
def list_assignments():
    query = Assignment.query
    if not g.api_user.is_admin:
        query = query.filter_by(volunteer_id=g.api_user.id)
    if (st := request.args.get("status")) in ASSIGNMENT_STATUSES:
        query = query.filter_by(status=st)
    if pid := request.args.get("project_id", type=int):
        query = query.filter_by(project_id=pid)
    return paginated(query.order_by(Assignment.updated_at.desc()), Assignment.to_dict)


@bp.post("/assignments")
@token_required(admin=True)
def create_assignment():
    data = request.get_json(silent=True) or {}
    project = db.session.get(Project, data.get("project_id") or 0)
    volunteer = db.session.get(Volunteer, data.get("volunteer_id") or 0)
    if not project or not volunteer:
        return error("project_id and volunteer_id must reference existing records", 422)
    if Assignment.query.filter_by(project_id=project.id, volunteer_id=volunteer.id).first():
        return error("Volunteer already assigned to this project", 409)
    status = data.get("status", "approved")
    if status not in ASSIGNMENT_STATUSES:
        return error("Validation failed", 422, fields={"status": "invalid value"})
    a = Assignment(project=project, volunteer=volunteer, status="pending",
                   role_title=str(data.get("role_title") or "Volunteer")[:80])
    db.session.add(a)
    a.change_status(status, g.api_user)
    db.session.commit()
    return jsonify(a.to_dict()), 201


@bp.put("/assignments/<int:assignment_id>")
@token_required(admin=True)
def update_assignment(assignment_id):
    a = db.session.get(Assignment, assignment_id) or abort(404, "Assignment not found")
    data = request.get_json(silent=True) or {}
    if "status" in data:
        if data["status"] not in ASSIGNMENT_STATUSES:
            return error("Validation failed", 422, fields={"status": "invalid value"})
        a.change_status(data["status"], g.api_user)
    if "hours" in data:
        if not isinstance(data["hours"], int) or not 0 <= data["hours"] <= 1000:
            return error("Validation failed", 422, fields={"hours": "0..1000"})
        a.hours = data["hours"]
    if "role_title" in data:
        a.role_title = str(data["role_title"])[:80]
    db.session.commit()
    data = a.to_dict()
    data["history"] = [{"from": h.old_status, "to": h.new_status, "at": h.changed_at.isoformat()}
                       for h in a.history]
    return jsonify(data)


@bp.delete("/assignments/<int:assignment_id>")
@token_required(admin=True)
def delete_assignment(assignment_id):
    a = db.session.get(Assignment, assignment_id) or abort(404, "Assignment not found")
    db.session.delete(a)
    db.session.commit()
    return jsonify(message="deleted", id=assignment_id)


@bp.get("/volunteers")
@token_required(admin=True)
def list_volunteers():
    query = Volunteer.query
    if q := request.args.get("q", "").strip():
        query = query.filter(or_(Volunteer.full_name.ilike(f"%{q}%"), Volunteer.email.ilike(f"%{q}%")))
    return paginated(query.order_by(Volunteer.full_name), Volunteer.to_dict)
