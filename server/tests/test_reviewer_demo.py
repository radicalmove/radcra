import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def test_demo_access_is_password_gated_course_scoped_and_one_use(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.db import Base
    from app import models
    from app.reviewer_demo import build_demo

    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    private = tmp_path / "private"
    private.mkdir()
    (private / "access.json").write_text(json.dumps({"sphere_email": "reviewer@sphere.example", "sphere_password": "isolated-test-password"}))
    (private / "courses.json").write_text(json.dumps([{"id": 2, "title": "Demo A"}, {"id": 3, "title": "Demo B"}]))
    monkeypatch.setattr(get_settings(), "extension_redirect_uris", "https://extension.chromiumapp.org/")
    app = build_demo(tmp_path, factory)
    with TestClient(app, base_url="https://fld-mini.tail4ccaba.ts.net:8443") as client:
        course = client.post("/api/access/course", json={"moodle_origin": "https://fld-mini.tail4ccaba.ts.net:8443", "moodle_course_id": 2}).json()["course_handle"]
        other = client.post("/api/access/course", json={"moodle_origin": "https://fld-mini.tail4ccaba.ts.net:8443", "moodle_course_id": 3}).json()["course_handle"]
        path = f"/reviewer-access/finish/{course}"
        redirect = "https://extension.chromiumapp.org/"
        page = client.get(path, params={"redirect_uri": redirect})
        csrf = client.cookies["demo_csrf"]
        assert page.status_code == 200
        assert client.post(path, data={"redirect_uri": redirect, "password": "wrong", "csrf": csrf}).status_code == 403
        issued = client.post(path, data={"redirect_uri": redirect, "password": "isolated-test-password", "csrf": csrf}, follow_redirects=False)
        code = issued.headers["location"].split("reviewer_code=")[1]
        assert client.post("/reviewer-access/exchange", json={"course_id": other, "code": code}).status_code == 403
        result = client.post("/reviewer-access/exchange", json={"course_id": course, "code": code}).json()
        assert result["role"] == "ld_dcd"
        headers = {"Authorization": f"Bearer {result['session_token']}"}
        assert client.get("/api/me", params={"course_id": course}, headers=headers).json()["user"]["role"] == "ld_dcd"
        assert client.get("/api/me", params={"course_id": other}, headers=headers).status_code == 404
        assert client.post("/reviewer-access/exchange", json={"course_id": course, "code": code}).status_code == 403
        for path in ["/admin", "/admin/users", "/register", "/api/courses/register", "/api/access/redeem"]:
            assert client.post(path).status_code == 404
