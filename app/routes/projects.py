from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..forms import ApplyForm, ProjectForm
from ..i18n import t
from ..models import PROJECT_CATEGORIES, PROJECT_STATUSES, Assignment, Project
from ..utils import admin_required, delete_upload, safe_sort, save_upload

bp = Blueprint("projects", __name__)

SORTS = {
    "newest": Project.created_at.desc(),
    "oldest": Project.created_at.asc(),
    "title": Project.title.asc(),
    "start": Project.start_date.asc(),
    "capacity": Project.capacity.desc(),
}


def get_project(project_id):
    return db.session.get(Project, project_id) or abort(404)


@bp.route("/")
def list_projects():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    status = request.args.get("status", "")
    sort = safe_sort("sort", SORTS, "newest")

    query = Project.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Project.title.ilike(like), Project.description.ilike(like),
                                 Project.location.ilike(like)))
    if category in PROJECT_CATEGORIES:
        query = query.filter_by(category=category)
    if status in PROJECT_STATUSES:
        query = query.filter_by(status=status)

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(SORTS[sort]).paginate(
        page=page, per_page=current_app.config["PROJECTS_PER_PAGE"], error_out=False
    )
    return render_template("projects/list.html", pagination=pagination, q=q, category=category,
                           status=status, sort=sort, categories=PROJECT_CATEGORIES,
                           statuses=PROJECT_STATUSES, sorts=SORTS.keys())


@bp.route("/<int:project_id>")
def detail(project_id):
    project = get_project(project_id)
    my_assignment = None
    if current_user.is_authenticated:
        my_assignment = project.assignments.filter_by(volunteer_id=current_user.id).first()
    team = project.assignments.order_by(Assignment.created_at).all()
    return render_template("projects/detail.html", project=project, team=team,
                           my_assignment=my_assignment, apply_form=ApplyForm())


def _save_project(project, form):
    form.populate_obj(project)  # cover_image is overwritten below
    project.title = project.title.strip()
    project.location = project.location.strip()
    return project


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    form = ProjectForm()
    if form.validate_on_submit():
        cover = form.cover_image.data
        project = Project(creator_id=current_user.id)
        _save_project(project, form)
        project.cover_image = save_upload(cover, "image") if cover else None
        db.session.add(project)
        db.session.commit()
        flash(t("flash.project_created"), "success")
        return redirect(url_for("projects.detail", project_id=project.id))
    return render_template("projects/form.html", form=form, title=t("projects.new"))


@bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(project_id):
    project = get_project(project_id)
    old_cover = project.cover_image
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        cover = form.cover_image.data
        _save_project(project, form)
        project.cover_image = old_cover
        if cover and getattr(cover, "filename", ""):
            stored = save_upload(cover, "image")
            if stored:
                delete_upload(old_cover)
                project.cover_image = stored
        db.session.commit()
        flash(t("flash.project_updated"), "success")
        return redirect(url_for("projects.detail", project_id=project.id))
    return render_template("projects/form.html", form=form, project=project, title=t("projects.edit"))


@bp.route("/<int:project_id>/delete", methods=["POST"])
@admin_required
def delete(project_id):
    project = get_project(project_id)
    for a in project.assignments:
        delete_upload(a.agreement_file)
        delete_upload(a.certificate_file)
    delete_upload(project.cover_image)
    db.session.delete(project)
    db.session.commit()
    flash(t("flash.project_deleted"), "info")
    return redirect(url_for("projects.list_projects"))


@bp.route("/<int:project_id>/apply", methods=["POST"])
@login_required
def apply(project_id):
    project = get_project(project_id)
    form = ApplyForm()
    if not form.validate_on_submit():
        for errors in form.errors.values():
            for e in errors:
                flash(str(e), "danger")
        return redirect(url_for("projects.detail", project_id=project.id))
    if project.assignments.filter_by(volunteer_id=current_user.id).first():
        flash(t("flash.already_applied"), "warning")
    elif project.is_full or project.status == "completed":
        flash(t("flash.project_full"), "warning")
    else:
        db.session.add(Assignment(project_id=project.id, volunteer_id=current_user.id, status="pending",
                                  role_title=t("role.volunteer"), note=form.note.data.strip()))
        db.session.commit()
        flash(t("flash.applied"), "success")
    return redirect(url_for("projects.detail", project_id=project.id))
