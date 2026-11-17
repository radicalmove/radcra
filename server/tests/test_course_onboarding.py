import pytest
from app.config import Settings
from app.models import Course, User, UserRole
from app.security import utc_now
from app.services.courses import register_course


def learn(db, number=20):
    return register_course(db, course_url=f"https://learn.canterbury.ac.nz/course/view.php?id={number}",
                           title=f"LEARN {number}", moodle_course_id=number)


def mail_settings():
    return Settings(reviewer_access_mail_secret="test-only", reviewer_access_admin_email="admin@example.com",
                    reviewer_access_origin="https://review.example.com", reviewer_access_sender="sender@example.com")


def test_course_enrollment_defaults_off(db_session):
    c = learn(db_session)
    assert c.email_onboarding_enabled is False


def test_only_admin_can_enable_exact_confirmed_learn_course(db_session):
    from app.services.course_onboarding import set_enrollment, enrollment_enabled
    from app.services.access import AccessDenied
    c = learn(db_session)
    admin = User(email="admin@example.com", display_name="Admin", password_hash="unused",
                 role=UserRole.ADMIN, approved_at=utc_now(), created_at=utc_now())
    db_session.add(admin)
    db_session.commit()
    for role in (UserRole.SME, UserRole.LD_DCD, UserRole.BETA_TESTER):
        admin.role = role
        with pytest.raises(AccessDenied):
            set_enrollment(db_session, admin, c, True)
    admin.role = UserRole.ADMIN
    other = register_course(db_session, course_url="https://my.uconline.ac.nz/course/view.php?id=20",
                            title="UCO", moodle_course_id=20)
    with pytest.raises(AccessDenied):
        set_enrollment(db_session, admin, other, True)
    assert not enrollment_enabled(mail_settings(), c)
    set_enrollment(db_session, admin, c, True)
    assert enrollment_enabled(mail_settings(), c)
    assert not enrollment_enabled(Settings(), c)
    assert not other.email_onboarding_enabled
    c.is_confirmed = False
    assert not enrollment_enabled(mail_settings(), c)
    with pytest.raises(AccessDenied):
        set_enrollment(db_session, admin, c, True)
