import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    # Flask-SQLAlchemy 3 resolves relative SQLite paths against the instance/ folder
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///volunteer.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")  # public images
    PRIVATE_UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")  # PDFs, served after auth check
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_DOC_EXTENSIONS = {"pdf"}

    PROJECTS_PER_PAGE = 6
    ITEMS_PER_PAGE = 10

    LANGUAGES = ["kk", "ru"]
    DEFAULT_LANGUAGE = "kk"

    # read-only snapshot for GitHub Pages (see freeze.py); interactive links go to LIVE_URL
    STATIC_DEMO = False
    DEMO_BASE = os.getenv("DEMO_BASE", "/volunteerhub")  # GitHub Pages project path
    LIVE_URL = os.getenv("LIVE_URL", "https://volunteerhub-skybypower.onrender.com")


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
