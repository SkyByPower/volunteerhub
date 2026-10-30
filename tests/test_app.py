import io

import pytest

from app import create_app
from app.extensions import db
from app.models import Assignment, Project, Volunteer
from config import TestConfig


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        admin = Volunteer(full_name="Admin User", email="admin@test.kz", role="admin", api_token="admintoken")
        admin.set_password("Admin123")
        vol = Volunteer(full_name="Vol User", email="vol@test.kz", api_token="voltoken")
        vol.set_password("Volunteer123")
        db.session.add_all([admin, vol])
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


ADMIN = {"X-API-Key": "admintoken"}
VOL = {"X-API-Key": "voltoken"}
PROJECT = {"title": "Tree planting", "description": "Planting trees in the park", "location": "Almaty",
           "start_date": "2026-11-01", "capacity": 10, "category": "ecology"}


def test_pages_render(client):
    for url in ["/", "/projects/", "/auth/login", "/auth/register", "/lang/ru"]:
        assert client.get(url, follow_redirects=True).status_code == 200


def test_custom_404(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404 and b"404" in r.data


def test_login_and_role_access(client):
    assert client.get("/volunteers/").status_code == 302  # anonymous → login
    login(client, "vol@test.kz", "Volunteer123")
    assert client.get("/volunteers/").status_code == 403  # volunteer is not admin
    client.post("/auth/logout")
    login(client, "admin@test.kz", "Admin123")
    assert client.get("/volunteers/").status_code == 200


def test_register_validation(client):
    r = client.post("/auth/register", data={"full_name": "A", "email": "bad", "password": "123",
                                             "password2": "321", "phone": "abc"})
    assert r.status_code == 200
    assert Volunteer.query.count() == 2


def test_project_crud_web(client, app):
    login(client, "admin@test.kz", "Admin123")
    data = dict(PROJECT, status="planned")
    r = client.post("/projects/new", data=data, follow_redirects=True)
    assert r.status_code == 200
    p = Project.query.filter_by(title="Tree planting").one()
    client.post(f"/projects/{p.id}/edit", data=dict(data, title="Tree planting 2"))
    assert db.session.get(Project, p.id).title == "Tree planting 2"
    client.post(f"/projects/{p.id}/delete")
    assert db.session.get(Project, p.id) is None


def test_search_and_pagination(client, app):
    for i in range(8):
        db.session.add(Project(title=f"Project {i}", description="Some description", location="Astana",
                               category="social"))
    db.session.commit()
    r = client.get("/projects/?q=Project 3")
    assert b"Project 3" in r.data and b"Project 4" not in r.data
    assert client.get("/projects/?page=2").status_code == 200


def test_apply_and_status_history(client, app):
    p = Project(title="Help", description="Helping people", location="Astana", capacity=2)
    db.session.add(p)
    db.session.commit()
    login(client, "vol@test.kz", "Volunteer123")
    client.post(f"/projects/{p.id}/apply", data={"note": "I want to help a lot"})
    a = Assignment.query.one()
    assert a.status == "pending"
    client.post("/auth/logout")
    login(client, "admin@test.kz", "Admin123")
    client.post(f"/assignments/{a.id}/status", data={"status": "approved"})
    a = db.session.get(Assignment, a.id)
    assert a.status == "approved" and a.history[0].new_status == "approved"


def test_upload_rejects_fake_pdf(client, app):
    p = Project(title="Docs", description="Document test", location="Astana")
    v = Volunteer.query.filter_by(email="vol@test.kz").one()
    a = Assignment(project=p, volunteer=v)
    db.session.add_all([p, a])
    db.session.commit()
    login(client, "vol@test.kz", "Volunteer123")
    client.post(f"/assignments/{a.id}/upload",
                data={"document": (io.BytesIO(b"not a pdf"), "evil.pdf")}, content_type="multipart/form-data")
    assert db.session.get(Assignment, a.id).agreement_file is None
    client.post(f"/assignments/{a.id}/upload",
                data={"document": (io.BytesIO(b"%PDF-1.4 test"), "agreement.pdf")}, content_type="multipart/form-data")
    assert db.session.get(Assignment, a.id).agreement_file.endswith("agreement.pdf")


def test_api_projects(client):
    assert client.post("/api/projects", json=PROJECT).status_code == 401
    assert client.post("/api/projects", json=PROJECT, headers=VOL).status_code == 403
    assert client.post("/api/projects", json={"title": "x"}, headers=ADMIN).status_code == 422
    r = client.post("/api/projects", json=PROJECT, headers=ADMIN)
    assert r.status_code == 201
    pid = r.get_json()["id"]
    assert client.get("/api/projects").get_json()["total"] == 1
    r = client.put(f"/api/projects/{pid}", json={"capacity": 20}, headers=ADMIN)
    assert r.get_json()["capacity"] == 20
    assert client.delete(f"/api/projects/{pid}", headers=ADMIN).status_code == 200
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_api_assignments(client):
    pid = client.post("/api/projects", json=PROJECT, headers=ADMIN).get_json()["id"]
    vid = Volunteer.query.filter_by(email="vol@test.kz").one().id
    r = client.post("/api/assignments", json={"project_id": pid, "volunteer_id": vid}, headers=ADMIN)
    assert r.status_code == 201
    aid = r.get_json()["id"]
    assert client.post("/api/assignments", json={"project_id": pid, "volunteer_id": vid},
                       headers=ADMIN).status_code == 409
    r = client.put(f"/api/assignments/{aid}", json={"status": "completed", "hours": 12}, headers=ADMIN)
    assert r.get_json()["status"] == "completed"
    assert client.get("/api/assignments", headers=VOL).get_json()["total"] == 1


def test_api_token(client):
    r = client.post("/api/auth/token", json={"email": "admin@test.kz", "password": "Admin123"})
    assert r.get_json()["token"] == "admintoken"
    assert client.post("/api/auth/token", json={"email": "admin@test.kz", "password": "x"}).status_code == 401
