import secrets
from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


ROLES = ("admin", "volunteer")
PROJECT_STATUSES = ("planned", "active", "completed")
PROJECT_CATEGORIES = ("ecology", "education", "social", "health", "animals", "culture")
ASSIGNMENT_STATUSES = ("pending", "approved", "active", "completed", "rejected")


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Volunteer(UserMixin, TimestampMixin, db.Model):
    """System user. Role decides access: admin manages everything, volunteer takes part."""

    __tablename__ = "volunteers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(80))
    skills = db.Column(db.String(255))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(255))
    role = db.Column(db.String(20), nullable=False, default="volunteer")
    password_hash = db.Column(db.String(255), nullable=False)
    api_token = db.Column(db.String(64), unique=True, index=True)

    assignments = db.relationship(
        "Assignment", back_populates="volunteer", cascade="all, delete-orphan", lazy="dynamic"
    )
    projects_created = db.relationship("Project", back_populates="creator", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self):
        self.api_token = secrets.token_hex(24)
        return self.api_token

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def initials(self):
        parts = self.full_name.split()
        return "".join(p[0] for p in parts[:2]).upper()

    @property
    def total_hours(self):
        return sum(a.hours or 0 for a in self.assignments if a.status == "completed")

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "city": self.city,
            "role": self.role,
            "skills": self.skills,
        }


class Project(TimestampMixin, db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="social")
    location = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date)
    capacity = db.Column(db.Integer, nullable=False, default=10)
    status = db.Column(db.String(20), nullable=False, default="planned")
    cover_image = db.Column(db.String(255))
    creator_id = db.Column(db.Integer, db.ForeignKey("volunteers.id", ondelete="SET NULL"))

    creator = db.relationship("Volunteer", back_populates="projects_created")
    assignments = db.relationship(
        "Assignment", back_populates="project", cascade="all, delete-orphan", lazy="dynamic"
    )

    @property
    def taken_slots(self):
        return self.assignments.filter(
            Assignment.status.in_(("approved", "active", "completed"))
        ).count()

    @property
    def fill_percent(self):
        return min(100, round(self.taken_slots * 100 / self.capacity)) if self.capacity else 0

    @property
    def is_full(self):
        return self.taken_slots >= self.capacity

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "location": self.location,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "capacity": self.capacity,
            "taken_slots": self.taken_slots,
            "status": self.status,
            "cover_image": self.cover_image,
        }


class Assignment(TimestampMixin, db.Model):
    """Association object between Project and Volunteer (many-to-many) with status tracking."""

    __tablename__ = "assignments"
    __table_args__ = (db.UniqueConstraint("project_id", "volunteer_id", name="uq_project_volunteer"),)

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey("volunteers.id"), nullable=False)
    role_title = db.Column(db.String(80), default="Volunteer")
    hours = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), nullable=False, default="pending")
    note = db.Column(db.String(500))
    agreement_file = db.Column(db.String(255))
    certificate_file = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    project = db.relationship("Project", back_populates="assignments")
    volunteer = db.relationship("Volunteer", back_populates="assignments")
    history = db.relationship(
        "StatusLog", back_populates="assignment", cascade="all, delete-orphan",
        order_by="StatusLog.changed_at.desc()",
    )

    def change_status(self, new_status, user=None):
        if new_status == self.status:
            return
        self.history.append(StatusLog(old_status=self.status, new_status=new_status, changed_by=user))
        self.status = new_status

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project": self.project.title if self.project else None,
            "volunteer_id": self.volunteer_id,
            "volunteer": self.volunteer.full_name if self.volunteer else None,
            "role_title": self.role_title,
            "hours": self.hours,
            "status": self.status,
            "note": self.note,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StatusLog(db.Model):
    """History of assignment status changes."""

    __tablename__ = "status_logs"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("volunteers.id", ondelete="SET NULL"))
    changed_at = db.Column(db.DateTime, default=utcnow)

    assignment = db.relationship("Assignment", back_populates="history")
    changed_by = db.relationship("Volunteer")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Volunteer, int(user_id))
