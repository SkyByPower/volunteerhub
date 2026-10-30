from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from ..extensions import db
from ..forms import VolunteerAdminForm
from ..i18n import t
from ..models import ROLES, Assignment, Volunteer
from ..utils import admin_required, delete_upload, safe_sort
from .auth import email_taken, fill_profile

bp = Blueprint("volunteers", __name__)

SORTS = {
    "newest": Volunteer.created_at.desc(),
    "oldest": Volunteer.created_at.asc(),
    "name": Volunteer.full_name.asc(),
}


def get_volunteer(volunteer_id):
    return db.session.get(Volunteer, volunteer_id) or abort(404)


@bp.route("/")
@admin_required
def list_volunteers():
    q = request.args.get("q", "").strip()
    role = request.args.get("role", "")
    city = request.args.get("city", "")
    sort = safe_sort("sort", SORTS, "newest")

    query = Volunteer.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Volunteer.full_name.ilike(like), Volunteer.email.ilike(like),
                                 Volunteer.city.ilike(like), Volunteer.skills.ilike(like)))
    if role in ROLES:
        query = query.filter_by(role=role)
    if city:
        query = query.filter_by(city=city)

    cities = [c for (c,) in db.session.query(Volunteer.city).distinct().order_by(Volunteer.city) if c]
    pagination = query.order_by(SORTS[sort]).paginate(
        page=request.args.get("page", 1, type=int), per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    return render_template("volunteers/list.html", pagination=pagination, q=q, role=role, city=city,
                           sort=sort, roles=ROLES, cities=cities, sorts=SORTS.keys())


@bp.route("/<int:volunteer_id>")
@admin_required
def detail(volunteer_id):
    volunteer = get_volunteer(volunteer_id)
    assignments = volunteer.assignments.order_by(Assignment.updated_at.desc()).all()
    return render_template("volunteers/detail.html", volunteer=volunteer, assignments=assignments)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    form = VolunteerAdminForm()
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append(t("v.required"))
        elif email_taken(form.email.data):
            form.email.errors.append(t("flash.email_taken"))
        else:
            v = Volunteer(role=form.role.data)
            fill_profile(v, form)
            v.set_password(form.password.data)
            v.generate_token()
            db.session.add(v)
            db.session.commit()
            flash(t("flash.volunteer_created"), "success")
            return redirect(url_for("volunteers.detail", volunteer_id=v.id))
    return render_template("volunteers/form.html", form=form, title=t("volunteers.new"))


@bp.route("/<int:volunteer_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(volunteer_id):
    v = get_volunteer(volunteer_id)
    form = VolunteerAdminForm(obj=v)
    if form.validate_on_submit():
        if email_taken(form.email.data, v.id):
            form.email.errors.append(t("flash.email_taken"))
        else:
            fill_profile(v, form)
            # an admin cannot demote themselves and lock everyone out
            if v.id != current_user.id:
                v.role = form.role.data
            if form.password.data:
                v.set_password(form.password.data)
            db.session.commit()
            flash(t("flash.volunteer_updated"), "success")
            return redirect(url_for("volunteers.detail", volunteer_id=v.id))
    return render_template("volunteers/form.html", form=form, volunteer=v, title=t("volunteers.edit"))


@bp.route("/<int:volunteer_id>/delete", methods=["POST"])
@admin_required
def delete(volunteer_id):
    v = get_volunteer(volunteer_id)
    if v.id == current_user.id:
        flash(t("flash.cant_delete_self"), "warning")
        return redirect(url_for("volunteers.detail", volunteer_id=v.id))
    for a in v.assignments:
        delete_upload(a.agreement_file)
        delete_upload(a.certificate_file)
    delete_upload(v.avatar)
    db.session.delete(v)
    db.session.commit()
    flash(t("flash.volunteer_deleted"), "info")
    return redirect(url_for("volunteers.list_volunteers"))
