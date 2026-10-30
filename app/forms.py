import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField, DateField, IntegerField, PasswordField, SelectField, StringField, TextAreaField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional, Regexp, ValidationError,
)

from .i18n import LazyText as _
from .models import ASSIGNMENT_STATUSES, PROJECT_CATEGORIES, PROJECT_STATUSES, ROLES

IMAGE_EXT = ["jpg", "jpeg", "png", "webp"]
PHONE_RE = r"^\+?[0-9\s\-()]{10,18}$"
NAME_RE = r"^[A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі\s\-]+$"


def required():
    return DataRequired(message=_("v.required"))


def length(min=-1, max=-1):
    return Length(min=min, max=max, message=_("v.length" if min > 0 else "v.max_length"))


def choices(values, prefix):
    return [(v, _(f"{prefix}.{v}")) for v in values]


def strong_password(form, field):
    if field.data and not (re.search(r"[A-Za-zА-Яа-я]", field.data) and re.search(r"\d", field.data)):
        raise ValidationError(_("v.password_strength"))


class LoginForm(FlaskForm):
    email = StringField(_("f.email"), validators=[required(), Email(message=_("v.email"))])
    password = PasswordField(_("f.password"), validators=[required()])
    remember = BooleanField(_("remember_me"))


class ProfileFieldsMixin:
    full_name = StringField(
        _("f.full_name"),
        validators=[required(), length(3, 120), Regexp(NAME_RE, message=_("v.name_chars"))],
    )
    email = StringField(_("f.email"), validators=[required(), Email(message=_("v.email")), length(max=120)])
    phone = StringField(_("f.phone"), validators=[Optional(), Regexp(PHONE_RE, message=_("v.phone"))])
    city = StringField(_("f.city"), validators=[Optional(), length(max=80)])
    skills = StringField(_("f.skills"), validators=[Optional(), length(max=255)])
    bio = TextAreaField(_("f.bio"), validators=[Optional(), length(max=1000)])
    avatar = FileField(_("f.avatar"), validators=[FileAllowed(IMAGE_EXT, _("v.image_only"))])


class RegisterForm(ProfileFieldsMixin, FlaskForm):
    password = PasswordField(_("f.password"), validators=[required(), length(6, 64), strong_password])
    password2 = PasswordField(
        _("f.password2"), validators=[required(), EqualTo("password", message=_("v.password_match"))]
    )


class ProfileForm(ProfileFieldsMixin, FlaskForm):
    password = PasswordField(_("f.password_new"), validators=[Optional(), length(6, 64), strong_password])


class VolunteerAdminForm(ProfileFieldsMixin, FlaskForm):
    role = SelectField(_("f.role"), choices=choices(ROLES, "role"), validators=[required()])
    password = PasswordField(_("f.password"), validators=[Optional(), length(6, 64), strong_password])


class ProjectForm(FlaskForm):
    title = StringField(_("f.title"), validators=[required(), length(3, 150)])
    description = TextAreaField(_("f.description"), validators=[required(), length(10, 5000)])
    category = SelectField(_("f.category"), choices=choices(PROJECT_CATEGORIES, "cat"), validators=[required()])
    location = StringField(_("f.location"), validators=[required(), length(2, 120)])
    start_date = DateField(_("f.start_date"), validators=[required()])
    end_date = DateField(_("f.end_date"), validators=[Optional()])
    capacity = IntegerField(
        _("f.capacity"),
        validators=[required(), NumberRange(min=1, max=500, message=_("v.range"))],
    )
    status = SelectField(_("f.status"), choices=choices(PROJECT_STATUSES, "st"), validators=[required()])
    cover_image = FileField(_("f.cover"), validators=[FileAllowed(IMAGE_EXT, _("v.image_only"))])

    def validate_end_date(self, field):
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError(_("v.date_order"))


class AssignmentForm(FlaskForm):
    project_id = SelectField(_("f.project"), coerce=int, validators=[required()])
    volunteer_id = SelectField(_("f.volunteer"), coerce=int, validators=[required()])
    role_title = StringField(_("f.role_title"), validators=[required(), length(2, 80)])
    hours = IntegerField(
        _("f.hours"), default=0,
        validators=[Optional(), NumberRange(min=0, max=1000, message=_("v.range"))],
    )
    status = SelectField(_("f.status"), choices=choices(ASSIGNMENT_STATUSES, "st"), validators=[required()])
    note = TextAreaField(_("f.note"), validators=[Optional(), length(max=500)])
    certificate = FileField(_("f.certificate"), validators=[FileAllowed(["pdf"], _("v.pdf_only"))])


class ApplyForm(FlaskForm):
    note = TextAreaField(_("f.motivation"), validators=[required(), length(10, 500)])


class DocumentForm(FlaskForm):
    document = FileField(_("f.agreement"), validators=[FileAllowed(["pdf"], _("v.pdf_only"))])
