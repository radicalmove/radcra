from datetime import UTC, datetime
import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import create_app
from app.models import AuditEvent, Course, User, UserRole
from app.services.accounts import register_account


@pytest.fixture
def client():
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    app = create_app()

    def session_override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = session_override
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.db_factory = factory
        yield test_client


def test_admin_can_approve_and_change_a_role_with_auditing(client):
    session = client.db_factory()
    admin = register_account(session, email="admin@example.test", password="long enough password")
    admin.role, admin.approved_at = UserRole.ADMIN, datetime.now(UTC)
    member = register_account(session, email="member@example.test", password="long enough password")
    session.commit()
    member_id = str(member.id)
    session.close()
    client.post("/auth/login", json={"email": "admin@example.test", "password": "long enough password"})

    approved = client.post(f"/admin/users/{member_id}/approve", json={})
    changed = client.post(f"/admin/users/{member_id}/role", json={"role": "sme"})

    assert approved.status_code == 200
    assert changed.status_code == 200
    check = client.db_factory()
    member = check.get(User, uuid.UUID(member_id))
    assert member.approved_at is not None and member.role is UserRole.SME
    assert {event.action for event in check.query(AuditEvent).all()} == {"user.approved", "user.role_changed"}
    check.close()


def test_admin_access_page_is_course_first(client):
    session = client.db_factory()
    admin = register_account(session, email="admin@example.test", password="long enough password")
    admin.role, admin.approved_at = UserRole.ADMIN, datetime.now(UTC)
    now = datetime.now(UTC)
    course_a = Course(
        moodle_course_id="896",
        normalized_url="https://moodle.example.test/course/view.php?id=896",
        moodle_origin="https://moodle.example.test",
        title="CRJU150 Main Copy",
        identity_title="CRJU150 Main Copy",
        is_confirmed=True,
        created_at=now,
        confirmed_at=now,
    )
    course_b = Course(
        moodle_course_id="999",
        normalized_url="https://moodle.example.test/course/view.php?id=999",
        moodle_origin="https://moodle.example.test",
        title="A Second Course",
        identity_title="A Second Course",
        is_confirmed=True,
        created_at=now,
        confirmed_at=now,
    )
    session.add_all([course_a, course_b])
    session.commit()
    course_a_id = str(course_a.id)
    session.close()
    client.post("/auth/login", json={"email": "admin@example.test", "password": "long enough password"})

    unselected = client.get("/admin/users")
    assert unselected.status_code == 200
    assert "1. Select a course" in unselected.text
    assert "CRJU150 Main Copy" in unselected.text and "A Second Course" in unselected.text
    assert "Select a course above to create invitations" in unselected.text
    assert "Create reviewer invitation" not in unselected.text

    selected = client.get(f"/admin/users?course_id={course_a_id}")
    assert selected.status_code == 200
    assert "2. Manage CRJU150 Main Copy" in selected.text
    assert f'/admin/courses/{course_a_id}/invitations' in selected.text
    assert "No reviewers for this course yet." in selected.text


def test_admin_browser_mutations_require_csrf(client):
    session = client.db_factory()
    admin = register_account(session, email="admin@example.test", password="long enough password")
    admin.role, admin.approved_at = UserRole.ADMIN, datetime.now(UTC)
    member = register_account(session, email="member@example.test", password="long enough password")
    session.commit()
    member_id = str(member.id)
    session.close()
    client.post("/auth/login", json={"email": "admin@example.test", "password": "long enough password"})

    assert client.post(f"/admin/users/{member_id}/approve", data={}).status_code == 403


@pytest.mark.parametrize("payload", [{}, {"role": None}, {"role": "not-a-role"}])
def test_admin_role_changes_reject_malformed_json_with_validation_response(client, payload):
    session = client.db_factory()
    admin = register_account(session, email="admin@example.test", password="long enough password")
    admin.role, admin.approved_at = UserRole.ADMIN, datetime.now(UTC)
    member = register_account(session, email="member@example.test", password="long enough password")
    session.commit()
    member_id = str(member.id)
    session.close()
    client.post("/auth/login", json={"email": "admin@example.test", "password": "long enough password"})

    response = client.post(f"/admin/users/{member_id}/role", json=payload)

    assert response.status_code == 422


def _logged_in_admin(client):
    session = client.db_factory()
    admin = register_account(session, email="archive-admin@example.test", password="long enough password")
    admin.role, admin.approved_at = UserRole.ADMIN, datetime.now(UTC)
    target = register_account(session, email="archive-target@example.test", password="long enough password", display_name="Archive Target")
    session.commit()
    target_id = str(target.id)
    session.close()
    assert client.post("/auth/login", json={"email": "archive-admin@example.test", "password": "long enough password"}).status_code == 200
    page = client.get("/admin/users")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert csrf is not None
    return target_id, csrf.group(1)


def test_admin_can_archive_and_restore_account_from_separate_sections(client):
    target_id, csrf = _logged_in_admin(client)

    active = client.get("/admin/users")
    assert "Archive Target" in active.text
    assert "Delete account" in active.text
    assert "course comments and review history remain available in course review" in active.text

    archived = client.post(f"/admin/users/{target_id}/archive", data={"csrf_token": csrf}, follow_redirects=False)
    assert archived.status_code == 303

    deleted = client.get("/admin/users")
    assert "Archive Target" not in deleted.text.split("Deleted accounts", 1)[0]
    assert "Deleted accounts" in deleted.text
    assert "Restore account" in deleted.text

    csrf = re.search(r'name="csrf_token" value="([^"]+)"', deleted.text).group(1)
    restored = client.post(f"/admin/users/{target_id}/restore", data={"csrf_token": csrf}, follow_redirects=False)
    assert restored.status_code == 303
    assert "Archive Target" in client.get("/admin/users").text


def test_admin_archive_requires_csrf(client):
    target_id, _ = _logged_in_admin(client)

    response = client.post(f"/admin/users/{target_id}/archive", data={})

    assert response.status_code == 403
