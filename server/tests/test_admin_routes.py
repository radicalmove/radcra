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
from app.models import AuditEvent, Course, CourseMembership, MembershipState, User, UserRole
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


def test_admin_shortcut_returns_to_admin_after_login_and_excludes_reviewers(client):
    with client.db_factory() as db:
        admin = register_account(db, email="shortcut-admin@example.test", password="long enough password")
        admin.role, admin.approved_at = UserRole.ADMIN, datetime.now(UTC)
        reviewer = register_account(db, email="shortcut-reviewer@example.test", password="long enough password")
        reviewer.approved_at = datetime.now(UTC)
        db.commit()
    login = client.get("/admin")
    assert login.url.path == "/login" and "Admin sign-in" in login.text
    response = client.post("/login", data={"csrf_token": client.cookies["csrf_token"], "next": "/admin",
        "email": "shortcut-admin@example.test", "password": "long enough password"})
    assert response.url.path == "/admin/users"
    client.post("/auth/login", json={"email": "shortcut-reviewer@example.test", "password": "long enough password"})
    assert client.get("/admin").status_code == 403


def test_crju160_request_notifies_admin_only_after_email_confirmation(client):
    from app.routers.reviewer_request import request_mailer
    from app.services.courses import resolve_course

    class CapturedMail:
        proofs = []
        requests = []

        def verification(self, course_id, email, proof):
            self.proofs.append((course_id, email, proof))

        def admin_request(self, reviewer, course):
            self.requests.append((reviewer.email, course.moodle_course_id))

    mail = CapturedMail()
    with client.db_factory() as db:
        course_id = resolve_course(db, moodle_course_id=1170,
            course_url="https://my.uconline.ac.nz/course/view.php?id=1170", title="CRJU160").id
    path = f"/reviewer-access/request/{course_id}"
    assert "CRJU160" in client.get(path).text
    form = {"csrf_token": client.cookies["csrf_token"], "email": "reviewer@example.com", "display_name": "Test Reviewer"}
    assert client.post(path, data=form).status_code == 503
    client.app.dependency_overrides[request_mailer] = lambda: mail
    response = client.post(path, data=form)
    assert "Check your email" in response.text
    assert mail.requests == []
    _, _, proof = mail.proofs[0]
    assert proof not in response.text
    assert client.get("/reviewer-access/verify").headers["cache-control"] == "no-store"
    assert mail.requests == []
    assert "Waiting for admin approval" in client.post("/reviewer-access/verify", data={"csrf_token": form["csrf_token"], "proof": proof}).text
    assert "already used" in client.post("/reviewer-access/verify", data={"csrf_token": form["csrf_token"], "proof": proof}).text
    assert mail.requests == [("reviewer@example.com", "1170")]


@pytest.mark.parametrize("release_mode", [False, True])
def test_access_queue_delivers_verification_admin_and_approval(client, monkeypatch, release_mode):
    from pydantic import SecretStr
    from sqlalchemy import select
    from app.config import get_settings
    from app.services.courses import resolve_course
    from app.services.notification_pilot import deliver_access_mail

    settings = get_settings()
    redirect = "https://abcdefghijklmnop.chromiumapp.org/"
    with client.db_factory() as db:
        pilot_id = resolve_course(db, moodle_course_id=1170,
            course_url="https://my.uconline.ac.nz/course/view.php?id=1170", title="CRJU160").id
        course_id = resolve_course(db, moodle_course_id=1171,
            course_url="https://my.uconline.ac.nz/course/view.php?id=1171", title="Second course").id if release_mode else pilot_id
        admin = register_account(db, email="admin@example.test", password="long enough password")
        admin.role, admin.approved_at = UserRole.ADMIN, datetime.now(UTC)
        db.commit()
    for key, value in {
        "reviewer_access_mail_secret": SecretStr("test-only-mail-secret"),
        "notification_pilot_course_id": pilot_id,
        "notification_pilot_recipient": "pilot@example.com" if release_mode else "reviewer@example.com",
        "notification_pilot_sender": "sender@example.com",
        "notification_pilot_url": "https://testserver",
        "extension_redirect_uris": redirect,
        "reviewer_access_enabled": release_mode,
        "reviewer_access_admin_email": "admin-inbox@example.com",
        "reviewer_access_origin": "https://testserver",
        "reviewer_access_sender": "release-sender@example.com",
    }.items():
        monkeypatch.setattr(settings, key, value)
    path = f"/reviewer-access/request/{course_id}"
    client.get(path)
    csrf = client.cookies["csrf_token"]
    assert "Check your email" in client.post(path, data={"csrf_token": csrf, "email": "reviewer@example.com", "display_name": "Reviewer"}).text
    messages = []
    def drain():
        with client.db_factory() as db:
            assert deliver_access_mail(db, settings, lambda msg, to: messages.append((msg, to)))
            assert not deliver_access_mail(db, settings, lambda msg, to: messages.append((msg, to)))
    drain()
    proof = messages[0][0].get_content().split("#")[-1].strip()
    assert "Waiting for admin approval" in client.post("/reviewer-access/verify", data={"csrf_token": csrf, "proof": proof}).text
    drain()
    finish = f"/reviewer-access/finish/{course_id}"
    assert client.get(finish, params={"redirect_uri": redirect}, follow_redirects=False).headers["location"].endswith("reviewer_status=not-ready")
    with client.db_factory() as db:
        membership_id = db.scalar(select(CourseMembership.id))
    client.post("/auth/login", json={"email": "admin@example.test", "password": "long enough password"})
    assert client.post(f"/admin/memberships/{membership_id}/approve-request", data={"csrf_token": csrf, "role": "sme"}, follow_redirects=False).status_code == 303
    drain()
    callback = client.get(finish, params={"redirect_uri": redirect}, follow_redirects=False).headers["location"]
    code = callback.split("reviewer_code=")[1]
    payload = {"course_id": str(course_id), "code": code}
    access = client.post("/reviewer-access/exchange", json=payload).json()
    assert access["role"] == "sme"
    headers = {"Authorization": f"Bearer {access['session_token']}"}
    assert client.get("/api/me", params={"course_id": str(course_id)}, headers=headers).json()["user"]["role"] == "sme"
    assert client.post("/reviewer-access/exchange", json=payload).status_code == 403
    assert client.post("/api/access/reviewers/sign-in", json={"course_handle": str(course_id), "membership_id": str(membership_id)}).status_code == 403
    if release_mode:
        assert client.post("/api/access/reviewers", json={"course_handle": str(course_id)}).status_code == 403
        assert client.get("/api/me", params={"course_id": str(pilot_id)}, headers=headers).status_code == 404
    prefix = "Sphere:" if release_mode else "[Sphere test]"
    assert [(str(msg["Subject"]), to) for msg, to in messages] == [
        (f"{prefix} Confirm your email", "reviewer@example.com"),
        (f"{prefix} Course access request", "admin-inbox@example.com" if release_mode else "reviewer@example.com"),
        (f"{prefix} Course access approved", "reviewer@example.com"),
    ]
    assert all(str(msg["To"]) == to for msg, to in messages)
    assert all("pilot@example.com" != to for _, to in messages)
    assert "https://testserver/admin" in messages[1][0].get_content()
    if release_mode:
        assert all(msg["From"].addresses[0].addr_spec == "release-sender@example.com" for msg, _ in messages)
    client.get(path)
    assert "Check your email" in client.post(path, data={"csrf_token": csrf, "email": "reviewer@example.com"}).text
    drain()
    new_proof = messages[-1][0].get_content().split("#")[-1].strip()
    verified = client.post("/reviewer-access/verify", data={"csrf_token": csrf, "proof": new_proof})
    assert "Open course in Moodle" in verified.text
    assert f"https://my.uconline.ac.nz/course/view.php?id={1171 if release_mode else 1170}" in verified.text


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


def test_crju160_pending_request_is_first_and_approval_sets_only_course_role(client):
    now = datetime.now(UTC)
    with client.db_factory() as db:
        admin = register_account(db, email="admin@example.test", password="long enough password")
        reviewer = register_account(db, email="reviewer@example.test", password="long enough password", display_name="CRJU160 Test Reviewer")
        admin.role, admin.approved_at = UserRole.ADMIN, now
        course = Course(moodle_course_id="1170", normalized_url="https://my.uconline.ac.nz/course/view.php?id=1170",
                        moodle_origin="https://my.uconline.ac.nz", title="CRJU160", identity_title="crju160",
                        is_confirmed=True, created_at=now)
        db.add(course)
        db.flush()
        pending = CourseMembership(user_id=reviewer.id, course_id=course.id, role=UserRole.BETA_TESTER,
                                   state=MembershipState.PENDING, created_at=now, updated_at=now)
        db.add(pending)
        db.commit()
        membership_id, reviewer_id = pending.id, reviewer.id
    client.post("/auth/login", json={"email": "admin@example.test", "password": "long enough password"})
    page = client.get("/admin/users")
    assert page.text.index("Pending requests") < page.text.index("1. Select a course")
    assert "CRJU160 Test Reviewer" in page.text
    csrf = client.cookies["csrf_token"]
    route = f"/admin/memberships/{membership_id}/approve-request"
    assert client.post(route, data={"csrf_token": csrf, "role": "admin"}).status_code == 422
    assert client.post(route, data={"csrf_token": csrf, "role": "sme"}, follow_redirects=False).status_code == 303
    assert client.post(route, data={"csrf_token": csrf, "role": "ld_dcd"}).status_code == 409
    with client.db_factory() as db:
        membership = db.get(CourseMembership, membership_id)
        assert membership.state is MembershipState.APPROVED and membership.role is UserRole.SME
        assert db.get(User, reviewer_id).role is UserRole.BETA_TESTER


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
