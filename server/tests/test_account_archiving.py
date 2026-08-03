from datetime import UTC, datetime
from datetime import timedelta
import hashlib

import pytest
from sqlalchemy import select

from app.models import AuditEvent, Comment, CommentCategory, CommentStatus, Course, CourseMembership, DeviceCredential, ExtensionLoginCode, MembershipState, PageLocation, ReconnectCredential, ReviewerInvitation, Session, User, UserRole
from app.security import hash_password, token_hash, utc_now
from app.services.accounts import AccountNotApprovedError, AuthorizationError, archive_account, change_role, restore_account, verify_dashboard_session
from app.services.access import AccessDenied, create_invitation, find_approved_reviewer, list_approved_reviewers, redeem_invitation, renew_device, resume_membership, sign_in_existing_reviewer
from app.services.comments import replace_sme_recipients, sme_recipient_state, visible_page_comments_for


def account(db_session, email: str, role: UserRole = UserRole.BETA_TESTER) -> User:
    now = utc_now()
    value = User(email=email, display_name=email.split("@", 1)[0], password_hash="hash", role=role, approved_at=now, created_at=now)
    db_session.add(value)
    db_session.flush()
    return value


def confirmed_course(db_session, moodle_course_id: str = "896", title: str = "CRJU150") -> Course:
    now = utc_now()
    value = Course(
        moodle_course_id=moodle_course_id,
        normalized_url=f"https://moodle.example.test/course/view.php?id={moodle_course_id}",
        moodle_origin="https://moodle.example.test",
        title=title,
        identity_title=title,
        is_confirmed=True,
        confirmed_at=now,
        created_at=now,
    )
    db_session.add(value)
    db_session.flush()
    return value


def test_user_supports_a_persisted_deleted_at_marker(db_session):
    deleted_at = datetime.now(UTC)
    account = User(
        email="archived@example.test",
        display_name="Archived",
        password_hash="hash",
        role=UserRole.BETA_TESTER,
        created_at=deleted_at,
        deleted_at=deleted_at,
    )
    db_session.add(account)
    db_session.commit()

    stored = db_session.get(User, account.id)

    assert stored is not None
    assert stored.deleted_at is not None
    assert stored.deleted_at.replace(tzinfo=UTC) == deleted_at


def test_archive_account_revokes_access_credentials_and_preserves_history(db_session):
    admin = account(db_session, "admin@example.test", UserRole.ADMIN)
    target = account(db_session, "target@example.test")
    course = confirmed_course(db_session)
    membership = CourseMembership(
        user_id=target.id,
        course_id=course.id,
        role=UserRole.BETA_TESTER,
        state=MembershipState.APPROVED,
        approved_at=utc_now(),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(membership)
    db_session.flush()
    dashboard = Session(user_id=target.id, token_hash=token_hash("dashboard-token"), kind="dashboard", expires_at=utc_now() + timedelta(hours=1), created_at=utc_now())
    extension = Session(user_id=target.id, membership_id=membership.id, token_hash=token_hash("extension-token"), kind="extension", expires_at=utc_now() + timedelta(hours=1), created_at=utc_now())
    login_code = ExtensionLoginCode(user_id=target.id, code_hash=token_hash("login-code"), redirect_uri="https://abcdefghijklmnop.chromiumapp.org/", expires_at=utc_now() + timedelta(minutes=5), created_at=utc_now())
    device = DeviceCredential(membership_id=membership.id, family_id="family", credential_hash=token_hash("device"), expires_at=utc_now() + timedelta(days=1), created_at=utc_now())
    reconnect = ReconnectCredential(membership_id=membership.id, code_hash=hash_password("reconnect"), created_at=utc_now())
    invitation = ReviewerInvitation(course_id=course.id, created_by_user_id=admin.id, email_hash=hashlib.sha256(target.email.encode()).hexdigest(), code_hash=hash_password("invitation"), allowed_role=UserRole.BETA_TESTER, expires_at=utc_now() + timedelta(days=1), created_at=utc_now())
    db_session.add_all([dashboard, extension, login_code, device, reconnect, invitation])
    db_session.commit()

    archived = archive_account(db_session, admin, target)

    assert archived.deleted_at is not None
    assert dashboard.revoked_at is not None
    assert extension.revoked_at is not None
    assert login_code.revoked_at is not None
    assert device.revoked_at is not None
    assert reconnect.revoked_at is not None
    assert invitation.revoked_at is not None
    assert db_session.scalar(select(AuditEvent).where(AuditEvent.action == "user.archived", AuditEvent.entity_id == str(target.id))) is not None
    assert db_session.get(CourseMembership, membership.id) is not None


def test_restore_account_keeps_old_credentials_revoked(db_session):
    admin = account(db_session, "admin-restore@example.test", UserRole.ADMIN)
    target = account(db_session, "restore@example.test")
    session = Session(user_id=target.id, token_hash=token_hash("restore-token"), kind="dashboard", expires_at=utc_now() + timedelta(hours=1), created_at=utc_now())
    db_session.add(session)
    db_session.commit()

    archive_account(db_session, admin, target)
    restored = restore_account(db_session, admin, target)

    assert restored.deleted_at is None
    assert session.revoked_at is not None
    assert db_session.scalar(select(AuditEvent).where(AuditEvent.action == "user.restored", AuditEvent.entity_id == str(target.id))) is not None


def test_archived_account_cannot_use_an_existing_dashboard_session(db_session):
    target = account(db_session, "blocked@example.test")
    raw_token = "blocked-token"
    db_session.add(Session(user_id=target.id, token_hash=token_hash(raw_token), kind="dashboard", expires_at=utc_now() + timedelta(hours=1), created_at=utc_now()))
    target.deleted_at = utc_now()
    db_session.commit()

    with pytest.raises(AccountNotApprovedError):
        verify_dashboard_session(db_session, raw_token)


def test_archived_account_cannot_use_course_access_issuance_paths(db_session):
    admin = account(db_session, "admin-access@example.test", UserRole.ADMIN)
    target = account(db_session, "blocked-access@example.test")
    first_course = confirmed_course(db_session)
    second_course = confirmed_course(db_session, "897", "CRJU151")
    membership = CourseMembership(user_id=target.id, course_id=first_course.id, role=UserRole.BETA_TESTER, state=MembershipState.APPROVED, approved_at=utc_now(), created_at=utc_now(), updated_at=utc_now())
    db_session.add(membership)
    db_session.commit()
    _, invitation_code = create_invitation(db_session, admin, second_course, target.email, UserRole.BETA_TESTER)

    archive_account(db_session, admin, target)
    db_session.add(ReconnectCredential(membership_id=membership.id, code_hash=hash_password("fresh-reconnect"), created_at=utc_now()))
    db_session.add(DeviceCredential(membership_id=membership.id, family_id="fresh-family", credential_hash=token_hash("fresh-device"), expires_at=utc_now() + timedelta(days=1), created_at=utc_now()))
    db_session.commit()

    with pytest.raises(AccessDenied):
        redeem_invitation(db_session, course_id=second_course.id, display_name="Blocked", email=target.email, role=UserRole.BETA_TESTER, invitation_code=invitation_code)
    with pytest.raises(AccessDenied):
        sign_in_existing_reviewer(db_session, course_id=first_course.id, membership_id=membership.id)
    with pytest.raises(AccessDenied):
        resume_membership(db_session, course_id=first_course.id, email=target.email, reconnect_code="fresh-reconnect")
    with pytest.raises(AccessDenied):
        renew_device(db_session, course_id=first_course.id, device_credential="fresh-device")


def test_archived_account_is_not_an_active_reviewer_or_sme_recipient(db_session):
    admin = account(db_session, "admin-reviewer@example.test", UserRole.ADMIN)
    target = account(db_session, "archived-reviewer@example.test", UserRole.SME)
    course = confirmed_course(db_session)
    membership = CourseMembership(user_id=target.id, course_id=course.id, role=UserRole.SME, state=MembershipState.APPROVED, approved_at=utc_now(), created_at=utc_now(), updated_at=utc_now())
    db_session.add(membership)
    db_session.commit()

    archive_account(db_session, admin, target)

    assert list_approved_reviewers(db_session, course_id=course.id) == []
    assert find_approved_reviewer(db_session, course_id=course.id, email=target.email) is None


def test_archive_and_role_change_protect_self_and_last_active_administrator(db_session):
    first_admin = account(db_session, "first-admin@example.test", UserRole.ADMIN)
    second_admin = account(db_session, "second-admin@example.test", UserRole.ADMIN)

    with pytest.raises(AuthorizationError):
        archive_account(db_session, first_admin, first_admin)
    archive_account(db_session, first_admin, second_admin)
    with pytest.raises(AuthorizationError):
        archive_account(db_session, first_admin, first_admin)
    with pytest.raises(AuthorizationError):
        change_role(db_session, first_admin, first_admin, UserRole.SME)


def test_archived_author_history_remains_readable_but_archived_sme_cannot_be_shared_with(db_session):
    admin = account(db_session, "admin-history@example.test", UserRole.ADMIN)
    author = account(db_session, "author-history@example.test", UserRole.BETA_TESTER)
    sme = account(db_session, "sme-history@example.test", UserRole.SME)
    course = confirmed_course(db_session)
    author_membership = CourseMembership(user_id=author.id, course_id=course.id, role=UserRole.BETA_TESTER, state=MembershipState.APPROVED, approved_at=utc_now(), created_at=utc_now(), updated_at=utc_now())
    sme_membership = CourseMembership(user_id=sme.id, course_id=course.id, role=UserRole.SME, state=MembershipState.APPROVED, approved_at=utc_now(), created_at=utc_now(), updated_at=utc_now())
    location = PageLocation(course_id=course.id, page_url="https://moodle.example.test/course/view.php?id=896", page_title="Introduction", anchor_type="visual_pin", relative_x=.5, relative_y=.5, css_selector="#intro", created_at=utc_now())
    comment = Comment(course_id=course.id, location_id=None, author_user_id=author.id, author_role=UserRole.BETA_TESTER, body="Historical feedback", category=CommentCategory.GENERAL, status=CommentStatus.OPEN, created_at=utc_now(), updated_at=utc_now())
    db_session.add_all([author_membership, sme_membership, location, comment])
    db_session.commit()
    comment.location_id = location.id
    db_session.commit()

    archive_account(db_session, admin, sme)

    visible = visible_page_comments_for(db_session, admin, course.id)
    assert [item.comment.body for item in visible] == ["Historical feedback"]
    assert sme_recipient_state(db_session, comment)[0] == []
    with pytest.raises(ValueError):
        replace_sme_recipients(db_session, admin, comment.id, [sme.id])

