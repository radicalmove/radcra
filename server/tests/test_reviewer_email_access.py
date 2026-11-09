from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import CourseMembership, MembershipState, User, UserRole
from app.services.access import AccessDenied, renew_device
from app.services.courses import resolve_course


def test_crju160_email_proof_and_approval_are_both_required(db_session):
    from app.services.reviewer_email_access import begin, confirm_email, exchange

    course = resolve_course(db_session, moodle_course_id=1170,
                            course_url="https://my.uconline.ac.nz/course/view.php?id=1170", title="CRJU160")
    other = resolve_course(db_session, moodle_course_id=1171,
                           course_url="https://my.uconline.ac.nz/course/view.php?id=1171", title="Other course")
    proof, browser_secret = begin(db_session, course.id, "reviewer@example.com", "Test Reviewer")
    assert db_session.scalar(select(User)) is None
    with pytest.raises(AccessDenied):
        exchange(db_session, course.id, browser_secret)
    with pytest.raises(AccessDenied):
        confirm_email(db_session, proof, "another browser")
    confirm_email(db_session, proof, browser_secret)
    with pytest.raises(AccessDenied):
        confirm_email(db_session, proof, browser_secret)
    member = db_session.scalar(select(CourseMembership))
    assert member.state is MembershipState.PENDING
    with pytest.raises(AccessDenied):
        exchange(db_session, course.id, browser_secret)
    member.state = MembershipState.APPROVED
    member.role = UserRole.SME
    member.approved_at = datetime.now(UTC)
    db_session.get(User, member.user_id).approved_at = member.approved_at
    db_session.commit()
    with pytest.raises(AccessDenied):
        exchange(db_session, other.id, browser_secret)
    access = exchange(db_session, course.id, browser_secret)
    assert access.membership.role is UserRole.SME
    assert renew_device(db_session, course_id=course.id, device_credential=access.device_credential).session_token
    with pytest.raises(AccessDenied):
        exchange(db_session, course.id, browser_secret)
    with pytest.raises(AccessDenied):
        renew_device(db_session, course_id=other.id, device_credential=access.device_credential)
    new_proof, new_browser = begin(db_session, course.id, "reviewer@example.com")
    same_membership, created = confirm_email(db_session, new_proof, new_browser)
    assert not created and same_membership.id == member.id
    assert exchange(db_session, course.id, new_browser).membership.role is UserRole.SME
