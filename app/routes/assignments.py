import os

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..forms import AssignmentForm, DocumentForm
from ..i18n import t
from ..models import ASSIGNMENT_STATUSES, Assignment, Project, Volunteer
from ..utils import admin_required, delete_upload, safe_next, safe_sort, save_upload, upload_path

bp = Blueprint("assignments", __name__)

SORTS = {
    "updated": Assignment.updated_at.desc(),
    "newest": Assignment.created_at.desc(),
    "oldest": Assignment.created_at.asc(),
}


def get_assignment(assignment_id, owner_ok=True):
    """Load an assignment; admins see all, volunteers only their own."""
    a = db.session.get(Assignment, assignment_id) or abort(404)
    if not current_user.is_admin and not (owner_ok and a.volunteer_id == current_user.id):
        abort(403)
    return a


def fill_choices(form):
    form.project_id.choices = [(p.id, p.title) for p in Project.query.order_by(Project.title)]
    form.volunteer_id.choices = [
        (v.id, f"{v.full_name} — {v.email}") for v in Volunteer.query.order_by(Volunteer.full_name)
    ]


@bp.route("/")
@login_required
def list_assignments():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    project_id = request.args.get("project", type=int)
    sort = safe_sort("sort", SORTS, "updated")

    query = Assignment.query.join(Project).join(Volunteer)
    if not current_user.is_admin:
        query = query.filter(Assignment.volunteer_id == current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Project.title.ilike(like), Volunteer.full_name.ilike(like),
                                 Assignment.role_title.ilike(like)))
    if status in ASSIGNMENT_STATUSES:
        query = query.filter(Assignment.status == status)
    if project_id:
        query = query.filter(Assignment.project_id == project_id)

    pagination = query.order_by(SORTS[sort]).paginate(
        page=request.args.get("page", 1, type=int), per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    projects = Project.query.order_by(Project.title).all() if current_user.is_admin else []
    return render_template("assignments/list.html", pagination=pagination, q=q, status=status,
                           project_id=project_id, sort=sort, statuses=ASSIGNMENT_STATUSES,
                           projects=projects, sorts=SORTS.keys())


@bp.route("/<int:assignment_id>")
@login_required
def detail(assignment_id):
    a = get_assignment(assignment_id)
    return render_template("assignments/detail.html", a=a, doc_form=DocumentForm(),
                           statuses=ASSIGNMENT_STATUSES)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    form = AssignmentForm()
    fill_choices(form)
    if request.method == "GET":
        form.project_id.data = request.args.get("project", type=int)
        form.role_title.data = form.role_title.data or t("role.volunteer")
    if form.validate_on_submit():
        exists = Assignment.query.filter_by(project_id=form.project_id.data,
                                            volunteer_id=form.volunteer_id.data).first()
        if exists:
            form.volunteer_id.errors.append(t("flash.assignment_exists"))
        else:
            a = Assignment(project_id=form.project_id.data, volunteer_id=form.volunteer_id.data,
                           role_title=form.role_title.data.strip(), hours=form.hours.data or 0,
                           note=form.note.data, status="pending")
            db.session.add(a)
            a.change_status(form.status.data, current_user._get_current_object())
            a.certificate_file = save_upload(form.certificate.data, "doc") if form.certificate.data else None
            db.session.commit()
            flash(t("flash.assignment_created"), "success")
            return redirect(url_for("assignments.detail", assignment_id=a.id))
    return render_template("assignments/form.html", form=form, title=t("assignments.new"))


@bp.route("/<int:assignment_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(assignment_id):
    a = get_assignment(assignment_id)
    form = AssignmentForm(obj=a)
    fill_choices(form)
    if form.validate_on_submit():
        duplicate = Assignment.query.filter(
            Assignment.project_id == form.project_id.data, Assignment.volunteer_id == form.volunteer_id.data,
            Assignment.id != a.id,
        ).first()
        if duplicate:
            form.volunteer_id.errors.append(t("flash.assignment_exists"))
        else:
            a.project_id = form.project_id.data
            a.volunteer_id = form.volunteer_id.data
            a.role_title = form.role_title.data.strip()
            a.hours = form.hours.data or 0
            a.note = form.note.data
            a.change_status(form.status.data, current_user._get_current_object())
            cert = form.certificate.data
            if cert and getattr(cert, "filename", ""):
                stored = save_upload(cert, "doc")
                if stored:
                    delete_upload(a.certificate_file)
                    a.certificate_file = stored
            db.session.commit()
            flash(t("flash.assignment_updated"), "success")
            return redirect(url_for("assignments.detail", assignment_id=a.id))
    return render_template("assignments/form.html", form=form, a=a, title=t("assignments.edit"))


@bp.route("/<int:assignment_id>/status", methods=["POST"])
@admin_required
def change_status(assignment_id):
    a = get_assignment(assignment_id)
    new_status = request.form.get("status")
    if new_status in ASSIGNMENT_STATUSES:
        a.change_status(new_status, current_user._get_current_object())
        db.session.commit()
        flash(t("flash.status_changed"), "success")
    return redirect(safe_next(request.form.get("next"), url_for("assignments.detail", assignment_id=a.id)))


@bp.route("/<int:assignment_id>/upload", methods=["POST"])
@login_required
def upload(assignment_id):
    """Volunteer uploads a signed agreement; admin may upload a certificate (?kind=certificate)."""
    a = get_assignment(assignment_id)
    kind = request.args.get("kind", "agreement")
    if kind == "certificate" and not current_user.is_admin:
        abort(403)
    form = DocumentForm()
    if form.validate_on_submit() and form.document.data:
        stored = save_upload(form.document.data, "doc")
        if stored:
            field = "certificate_file" if kind == "certificate" else "agreement_file"
            delete_upload(getattr(a, field))
            setattr(a, field, stored)
            db.session.commit()
            flash(t("flash.file_uploaded"), "success")
    elif form.errors:
        for errors in form.errors.values():
            for e in errors:
                flash(str(e), "danger")
    else:
        flash(t("flash.file_missing"), "warning")
    return redirect(url_for("assignments.detail", assignment_id=a.id))


@bp.route("/<int:assignment_id>/file/<kind>")
@login_required
def download(assignment_id, kind):
    a = get_assignment(assignment_id)
    rel = {"agreement": a.agreement_file, "certificate": a.certificate_file}.get(kind)
    if not rel or not os.path.isfile(upload_path(rel)):
        abort(404)
    return send_file(upload_path(rel), mimetype="application/pdf",
                     download_name=os.path.basename(rel).split("_", 1)[-1])


@bp.route("/<int:assignment_id>/delete", methods=["POST"])
@login_required
def delete(assignment_id):
    a = get_assignment(assignment_id)
    # volunteers may only withdraw their own pending application
    if not current_user.is_admin and a.status != "pending":
        abort(403)
    delete_upload(a.agreement_file)
    delete_upload(a.certificate_file)
    db.session.delete(a)
    db.session.commit()
    flash(t("flash.assignment_deleted" if current_user.is_admin else "flash.withdrawn"), "info")
    return redirect(url_for("assignments.list_assignments"))
