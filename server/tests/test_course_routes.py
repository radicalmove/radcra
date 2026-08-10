from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import create_app
from app.models import Course, User, UserRole
from app.services.accounts import create_extension_login_code, exchange_extension_login_code
from app.services.courses import resolve_course


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


def extension_headers(client, role=UserRole.BETA_TESTER):
    session = client.db_factory()
    user = User(
        email=f"{role.value}@example.test",
        password_hash="hash",
        role=role,
        approved_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    code = create_extension_login_code(session, user, "https://abcdefghijklmnop.chromiumapp.org/")
    token = exchange_extension_login_code(session, code, "https://abcdefghijklmnop.chromiumapp.org/")
    session.close()
    return {"Authorization": f"Bearer {token}"}


def test_resolve_returns_the_registered_course_with_the_existing_json_shape(client):
    session = client.db_factory()
    course = resolve_course(
        session,
        moodle_course_id=12,
        course_url="https://moodle.example/course/view.php?id=12",
        title="Law",
    )
    expected = {
        "id": str(course.id),
        "moodle_course_id": "12",
        "course_url": "https://moodle.example/course/view.php?id=12",
        "title": "Law",
        "is_confirmed": True,
    }
    session.close()

    response = client.post(
        "/api/courses/resolve",
        headers=extension_headers(client),
        json={
            "course_url": "https://moodle.example/course/view.php?id=12",
            "title": "Law",
            "moodle_course_id": 12,
        },
    )

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.LD_DCD])
def test_resolve_reports_unregistered_course_and_registration_capability_without_inserting(client, role):
    headers = extension_headers(client, role)
    payload = {
        "course_url": "https://moodle.example/course/view.php?id=13",
        "title": "New course",
        "moodle_course_id": 13,
    }

    first = client.post("/api/courses/resolve", headers=headers, json=payload)
    second = client.post("/api/courses/resolve", headers=headers, json=payload)

    assert first.status_code == 404
    assert first.json() == {"registered": False, "can_register": True}
    assert second.status_code == 404
    assert second.json() == {"registered": False, "can_register": True}
    check = client.db_factory()
    assert check.query(Course).count() == 0
    check.close()


def test_resolve_derives_registration_capability_from_the_authenticated_role(client):
    response = client.post(
        "/api/courses/resolve",
        headers=extension_headers(client, UserRole.BETA_TESTER),
        json={
            "course_url": "https://moodle.example/course/view.php?id=14",
            "title": "New course",
            "moodle_course_id": 14,
            "role": "admin",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"registered": False, "can_register": False}
    check = client.db_factory()
    assert check.query(Course).count() == 0
    check.close()


def test_resolve_rejects_an_incomplete_course_identity(client):
    response = client.post(
        "/api/courses/resolve",
        headers=extension_headers(client),
        json={"course_url": "https://moodle.example/course/view.php?id=15", "title": "Incomplete"},
    )

    assert response.status_code == 422
    check = client.db_factory()
    assert check.query(Course).count() == 0
    check.close()


def test_resolve_does_not_match_a_registered_id_from_another_moodle_origin(client):
    session = client.db_factory()
    resolve_course(
        session,
        moodle_course_id=16,
        course_url="https://moodle.example/course/view.php?id=16",
        title="Law",
    )
    session.close()

    response = client.post(
        "/api/courses/resolve",
        headers=extension_headers(client),
        json={
            "course_url": "https://other.example/course/view.php?id=16",
            "title": "Law",
            "moodle_course_id": 16,
        },
    )

    assert response.status_code == 404
    assert response.json() == {"registered": False, "can_register": False}


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.LD_DCD])
def test_register_creates_a_confirmed_course_for_an_authorized_role(client, role):
    response = client.post(
        "/api/courses/register",
        headers=extension_headers(client, role),
        json={
            "course_url": "https://moodle.example/course/view.php?id=20",
            "title": "  New course  ",
            "moodle_course_id": 20,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["moodle_course_id"] == "20"
    assert body["course_url"] == "https://moodle.example/course/view.php?id=20"
    assert body["title"] == "New course"
    assert body["is_confirmed"] is True
    check = client.db_factory()
    assert check.query(Course).count() == 1
    check.close()


def test_register_is_idempotent_for_the_same_moodle_identity(client):
    headers = extension_headers(client, UserRole.ADMIN)
    payload = {
        "course_url": "https://moodle.example/course/view.php?id=21",
        "title": "Repeatable course",
        "moodle_course_id": 21,
    }

    first = client.post("/api/courses/register", headers=headers, json=payload)
    check = client.db_factory()
    course = check.query(Course).one()
    original = {
        "id": course.id,
        "title": course.title,
        "normalized_url": course.normalized_url,
        "confirmed_at": course.confirmed_at,
        "created_at": course.created_at,
    }
    check.close()

    second = client.post("/api/courses/register", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
    check = client.db_factory()
    assert check.query(Course).count() == 1
    course = check.query(Course).one()
    assert {field: getattr(course, field) for field in original} == original
    check.close()


@pytest.mark.parametrize("role", [UserRole.BETA_TESTER, UserRole.SME])
def test_register_rejects_unauthorized_roles_even_when_client_claims_admin(client, role):
    response = client.post(
        "/api/courses/register",
        headers=extension_headers(client, role),
        json={
            "course_url": "https://moodle.example/course/view.php?id=22",
            "title": "Unauthorized course",
            "moodle_course_id": 22,
            "role": "admin",
        },
    )

    assert response.status_code == 403
    check = client.db_factory()
    assert check.query(Course).count() == 0
    check.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"course_url": "https://moodle.example/course/view.php?id=23", "title": "Missing id"},
        {"course_url": "https://moodle.example/course/view.php?id=23", "title": "Invalid id", "moodle_course_id": 0},
        {"course_url": "https://moodle.example/course/view.php?id=23", "title": "Invalid id", "moodle_course_id": "not numeric"},
    ],
)
def test_register_rejects_an_invalid_or_incomplete_identity(client, payload):
    response = client.post("/api/courses/register", headers=extension_headers(client, UserRole.ADMIN), json=payload)

    assert response.status_code == 422
    check = client.db_factory()
    assert check.query(Course).count() == 0
    check.close()


def test_register_rejects_a_numeric_id_already_bound_to_another_moodle_origin(client):
    headers = extension_headers(client, UserRole.ADMIN)
    first = client.post(
        "/api/courses/register",
        headers=headers,
        json={
            "course_url": "https://moodle.example/course/view.php?id=24",
            "title": "Origin-bound course",
            "moodle_course_id": 24,
        },
    )
    conflicting = client.post(
        "/api/courses/register",
        headers=headers,
        json={
            "course_url": "https://other.example/course/view.php?id=24",
            "title": "Origin-bound course",
            "moodle_course_id": 24,
        },
    )

    assert first.status_code == 201
    assert conflicting.status_code == 409
    assert "different Moodle origin" in conflicting.json()["detail"]
    check = client.db_factory()
    assert check.query(Course).count() == 1
    check.close()
