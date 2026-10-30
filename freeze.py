"""Build a read-only static copy of the site for GitHub Pages.

Usage:  flask --app run.py seed   (once, to have demo data)
        python freeze.py [out_dir]

Output layout (served from https://<user>.github.io/volunteerhub/):
    index.html          -> redirects to kk/
    404.html            -> custom 404 page
    kk/..., ru/...      -> one copy of every page per language
"""
import os
import shutil
import sys

from app import create_app
from app.models import Project
from config import Config


class StaticDemoConfig(Config):
    STATIC_DEMO = True
    PROJECTS_PER_PAGE = 100  # no pagination links: query strings need a server
    WTF_CSRF_ENABLED = False


def output_path(out, url):
    """'/' -> index.html, '/projects/' -> projects/index.html, '/projects/3' -> projects/3.html"""
    rel = url.strip("/")
    if not rel:
        return os.path.join(out, "index.html")
    if url.endswith("/"):
        return os.path.join(out, rel, "index.html")
    return os.path.join(out, rel + ".html")


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def main(out):
    app = create_app(StaticDemoConfig)
    base = app.config["DEMO_BASE"]
    with app.app_context():
        pages = ["/", "/projects/"] + [f"/projects/{p.id}" for p in Project.query.order_by(Project.id)]

    shutil.rmtree(out, ignore_errors=True)
    for lang in app.config["LANGUAGES"]:
        client = app.test_client()
        with client.session_transaction() as session:
            session["lang"] = lang
        # base_url sets SCRIPT_NAME, so url_for() builds links like /volunteerhub/kk/projects/
        base_url = f"http://localhost{base}/{lang}/"
        for url in pages:
            resp = client.get(url, base_url=base_url)
            if resp.status_code != 200:
                sys.exit(f"{lang}{url}: HTTP {resp.status_code}")
            write(output_path(os.path.join(out, lang), url), resp.data)
        shutil.copytree(app.static_folder, os.path.join(out, lang, "static"),
                        ignore=shutil.ignore_patterns("uploads"))
        if lang == app.config["DEFAULT_LANGUAGE"]:
            resp = client.get("/__missing__", base_url=base_url)
            write(os.path.join(out, "404.html"), resp.data)

    default = app.config["DEFAULT_LANGUAGE"]
    redirect = (f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={default}/">'
                f'<title>VolunteerHub</title><a href="{default}/">VolunteerHub</a>')
    write(os.path.join(out, "index.html"), redirect.encode())
    write(os.path.join(out, ".nojekyll"), b"")
    print(f"Static demo: {len(pages)} pages x {len(app.config['LANGUAGES'])} languages -> {out}/")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site")
