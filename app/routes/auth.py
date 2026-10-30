from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import LoginForm, ProfileForm, RegisterForm
from ..i18n import t
from ..models import Volunteer
from ..utils import delete_upload, save_upload

bp = Blueprint("auth", __name__)


def fill_profile(user, form):
    """Copy shared profile fields from a form to a Volunteer (DRY for register/profile/admin edit)."""
    user.full_name = form.full_name.data.strip()
    user.email = form.email.data.strip().lower()
    user.phone = (form.phone.data or "").strip() or None
    user.city = (form.city.data or "").strip() or None
    user.skills = (form.skills.data or "").strip() or None
    user.bio = (form.bio.data or "").strip() or None
    if form.avatar.data and getattr(form.avatar.data, "filename", ""):
        stored = save_upload(form.avatar.data, "image")
        if stored:
            delete_upload(user.avatar)
            user.avatar = stored


def email_taken(email, exclude_id=None):
    q = Volunteer.query.filter(Volunteer.email == email.strip().lower())
    if exclude_id:
        q = q.filter(Volunteer.id != exclude_id)
    return db.session.query(q.exists()).scalar()


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        if email_taken(form.email.data):
            form.email.errors.append(t("flash.email_taken"))
        else:
            user = Volunteer(role="volunteer")
            fill_profile(user, form)
            user.set_password(form.password.data)
            user.generate_token()
            db.session.add(user)
            db.session.commit()
            flash(t("flash.registered"), "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = Volunteer.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"{t('flash.login_ok')} {user.full_name}", "success")
            nxt = request.args.get("next")
            # prevent open redirects: only allow relative paths
            if not nxt or urlsplit(nxt).netloc or not nxt.startswith("/"):
                nxt = url_for("main.dashboard")
            return redirect(nxt)
        flash(t("flash.login_bad"), "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(t("flash.logout"), "info")
    return redirect(url_for("main.index"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        if email_taken(form.email.data, current_user.id):
            form.email.errors.append(t("flash.email_taken"))
        else:
            fill_profile(current_user, form)
            if form.password.data:
                current_user.set_password(form.password.data)
            db.session.commit()
            flash(t("flash.profile_saved"), "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)


@bp.route("/profile/token", methods=["POST"])
@login_required
def regenerate_token():
    current_user.generate_token()
    db.session.commit()
    flash(t("flash.token_new"), "success")
    return redirect(url_for("auth.profile"))
