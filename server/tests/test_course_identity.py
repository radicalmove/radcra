from datetime import UTC, datetime

import pytest

from app.models import Comment, Course, User
from app.services.courses import confirm_course, find_registered_course, register_course, resolve_course


def test_find_registered_course_is_read_only_for_existing_and_missing_identities(db_session):
    registered = resolve_course(
        db_session,
        moodle_course_id=123,
        course_url="https://moodle.example/course/view.php?id=123",
        title="Law",
    )
    original = {
        "moodle_course_id": registered.moodle_course_id,
        "moodle_origin": registered.moodle_origin,
        "normalized_url": registered.normalized_url,
        "title": registered.title,
        "is_confirmed": registered.is_confirmed,
        "confirmed_at": registered.confirmed_at,
    }

    found = find_registered_course(
        db_session,
        moodle_course_id=123,
        course_url="https://moodle.example/course/view.php?id=123",
        title="Changed client title",
    )
    missing = find_registered_course(
        db_session,
        moodle_course_id=456,
        course_url="https://moodle.example/course/view.php?id=456",
        title="Other",
    )

    assert found is registered
    assert missing is None
    assert db_session.query(Course).count() == 1
    assert {field: getattr(registered, field) for field in original} == original


def test_find_registered_course_requires_a_stable_moodle_identity(db_session):
    with pytest.raises(ValueError, match="moodle_course_id is required"):
        find_registered_course(
            db_session,
            course_url="https://moodle.example/course/view.php?id=123",
            title="Law",
        )


def test_moodle_numeric_id_creates_a_confirmed_stable_course(db_session):
    course = resolve_course(db_session, moodle_course_id=123, course_url="https://moodle.example/course/view.php?id=123", title="Law")

    assert course.moodle_course_id == "123"
    assert course.is_confirmed is True
    assert db_session.query(Course).count() == 1


def test_register_course_upgrades_an_exact_temporary_identity_without_creating_a_duplicate(db_session):
    temporary = resolve_course(db_session, course_url="https://moodle.example/course/view.php?id=124", title="Intro")

    registered = register_course(
        db_session,
        moodle_course_id=124,
        course_url=" HTTPS://Moodle.Example/course/view.php?id=124 ",
        title=" Intro ",
    )

    assert registered.id == temporary.id
    assert registered.moodle_course_id == "124"
    assert registered.moodle_origin == "https://moodle.example"
    assert registered.is_confirmed is True
    assert db_session.query(Course).count() == 1


def test_register_course_rejects_a_different_stable_id_for_the_same_identity(db_session):
    resolve_course(
        db_session,
        moodle_course_id=125,
        course_url="https://moodle.example/course/view.php?id=125",
        title="Same identity",
    )

    with pytest.raises(ValueError, match="already belongs to Moodle course 125"):
        register_course(
            db_session,
            moodle_course_id=126,
            course_url="https://moodle.example/course/view.php?id=125",
            title="Same identity",
        )


def test_url_and_title_create_an_unconfirmed_temporary_identity(db_session):
    course = resolve_course(db_session, course_url=" HTTPS://Moodle.Example/course/view.php?x=1 ", title="  Intro to Law  ")

    assert course.moodle_course_id is None
    assert course.is_confirmed is False
    assert course.normalized_url == "https://moodle.example/course/view.php?x=1"
    assert course.title == "Intro to Law"


def test_confirm_mapping_reuses_existing_course_and_moves_comments_without_duplicates(db_session):
    author = User(email="tester@example.test", password_hash="hash", approved_at=datetime.now(UTC), created_at=datetime.now(UTC))
    db_session.add(author)
    temporary = resolve_course(db_session, course_url="https://moodle.example/course/view.php?x=1", title="Intro")
    existing = resolve_course(db_session, moodle_course_id=777, course_url="https://moodle.example/course/view.php?id=777", title="Intro")
    comment = Comment(course_id=temporary.id, author_user_id=author.id, body="Needs work", category="learning_design_content_flow", status="open", created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    db_session.add(comment)
    db_session.commit()

    mapped = confirm_course(db_session, temporary, target_course_id=existing.id)

    assert mapped.id == existing.id
    assert db_session.query(Course).count() == 1
    assert db_session.get(Comment, comment.id).course_id == existing.id


def test_confirm_mapping_upgrades_temporary_course_to_a_new_stable_identity_without_losing_comments(db_session):
    author = User(email="tester@example.test", password_hash="hash", approved_at=datetime.now(UTC), created_at=datetime.now(UTC))
    db_session.add(author)
    temporary = resolve_course(db_session, course_url="https://moodle.example/course/view.php?id=88", title="Intro")
    comment = Comment(course_id=temporary.id, author_user_id=author.id, body="Needs work", category="learning_design_content_flow", status="open", created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    db_session.add(comment)
    db_session.commit()

    confirmed = confirm_course(db_session, temporary, moodle_course_id=88, course_url="https://moodle.example/course/view.php?id=88", title="Intro")

    assert confirmed.id == temporary.id
    assert confirmed.moodle_course_id == "88" and confirmed.is_confirmed is True
    assert db_session.query(Course).count() == 1
    assert db_session.get(Comment, comment.id).course_id == confirmed.id
