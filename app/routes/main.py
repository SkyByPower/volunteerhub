from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import ASSIGNMENT_STATUSES, Assignment, Project, Volunteer

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    stats = {
        "projects": Project.query.count(),
        "volunteers": Volunteer.query.filter_by(role="volunteer").count(),
        "hours": db.session.query(func.coalesce(func.sum(Assignment.hours), 0))
        .filter(Assignment.status == "completed").scalar(),
        "assignments": Assignment.query.count(),
    }
    latest = Project.query.filter(Project.status != "completed").order_by(Project.created_at.desc()).limit(3).all()
    return render_template("main/index.html", stats=stats, latest=latest)


@bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        counts = dict(
            db.session.query(Assignment.status, func.count(Assignment.id)).group_by(Assignment.status).all()
        )
        by_status = [(s, counts.get(s, 0)) for s in ASSIGNMENT_STATUSES]
        total = sum(c for _, c in by_status) or 1
        pending = (Assignment.query.filter_by(status="pending")
                   .order_by(Assignment.created_at.desc()).limit(6).all())
        recent = Assignment.query.order_by(Assignment.updated_at.desc()).limit(6).all()
        stats = {
            "projects": Project.query.count(),
            "active": Project.query.filter_by(status="active").count(),
            "volunteers": Volunteer.query.filter_by(role="volunteer").count(),
            "pending": counts.get("pending", 0),
        }
        return render_template("main/dashboard_admin.html", stats=stats, by_status=by_status,
                               total=total, pending=pending, recent=recent)

    mine = current_user.assignments.order_by(Assignment.updated_at.desc()).all()
    joined_ids = [a.project_id for a in mine]
    recommended = (Project.query.filter(Project.status != "completed", ~Project.id.in_(joined_ids or [0]))
                   .order_by(Project.start_date).limit(3).all())
    stats = {
        "hours": current_user.total_hours,
        "projects": len(mine),
        "certificates": sum(1 for a in mine if a.certificate_file),
        "pending": sum(1 for a in mine if a.status == "pending"),
    }
    return render_template("main/dashboard_volunteer.html", stats=stats, mine=mine[:5], recommended=recommended)
