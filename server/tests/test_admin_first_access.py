from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import CourseMembership, MembershipState, ReviewerEmailChallenge, User, UserRole
from app.security import utc_now
from app.services.access import AccessDenied
from app.services.courses import resolve_course
from app.services.reviewer_email_access import begin, confirm_email, exchange
from test_admin_routes import client


def course(db):
    return resolve_course(db, moodle_course_id=456, course_url="https://learn.example.com/course/view.php?id=456", title="Demonstration course")


def test_admin_first_request_is_pending_before_email_and_role_is_advisory(db_session):
    c = course(db_session)
    proof, browser = begin(db_session, c.id, "reviewer@example.com", "Reviewer", admin_first=True, requested_role="sme", mail_secret="test-only")
    member = db_session.scalar(select(CourseMembership))
    challenge = db_session.scalar(select(ReviewerEmailChallenge))
    assert member.state is MembershipState.PENDING and member.role is UserRole.BETA_TESTER
    assert db_session.get(User, member.user_id).role is UserRole.BETA_TESTER
    assert challenge.requested_role == "sme" and challenge.admin_first
    assert challenge.admin_mail_pending and not challenge.verification_mail_pending
    with pytest.raises(AccessDenied):
        confirm_email(db_session, proof, browser)
    with pytest.raises(AccessDenied):
        exchange(db_session, c.id, browser)


@pytest.mark.parametrize("role", ["admin", "invalid"])
def test_request_cannot_request_admin(db_session, role):
    with pytest.raises(AccessDenied):
        begin(db_session, course(db_session).id, "reviewer@example.com", "Reviewer", admin_first=True, requested_role=role)


def test_signin_unknown_does_not_create_account(db_session):
    with pytest.raises(AccessDenied):
        begin(db_session, course(db_session).id, "unknown@example.com", admin_first=True, signin=True)
    assert db_session.scalar(select(User)) is None


def test_approved_signin_is_browser_bound_single_use_and_course_scoped(db_session):
    c = course(db_session)
    begin(db_session, c.id, "reviewer@example.com", "Reviewer", admin_first=True)
    member = db_session.scalar(select(CourseMembership))
    member.state, member.role, member.approved_at = MembershipState.APPROVED, UserRole.SME, utc_now()
    db_session.get(User, member.user_id).approved_at = utc_now()
    db_session.commit()
    proof, browser = begin(db_session, c.id, "reviewer@example.com", admin_first=True, signin=True)
    with pytest.raises(AccessDenied):
        confirm_email(db_session, proof, "wrong browser")
    import uuid
    with pytest.raises(AccessDenied):
        exchange(db_session, uuid.uuid4(), browser)
    confirm_email(db_session, proof, browser)
    with pytest.raises(AccessDenied):
        confirm_email(db_session, proof, browser)
    assert exchange(db_session, c.id, browser).membership.role is UserRole.SME
    with pytest.raises(AccessDenied):
        exchange(db_session, c.id, browser)


@pytest.mark.parametrize("restriction", ["expired", "deleted", "admin", "revoked"])
def test_signin_proof_cannot_bypass_restrictions(db_session, restriction):
    c = course(db_session)
    begin(db_session, c.id, "reviewer@example.com", "Reviewer", admin_first=True)
    member = db_session.scalar(select(CourseMembership))
    user = db_session.get(User, member.user_id)
    member.state, member.approved_at, user.approved_at = MembershipState.APPROVED, utc_now(), utc_now()
    db_session.commit()
    proof, browser = begin(db_session, c.id, user.email, admin_first=True, signin=True)
    latest = db_session.scalar(select(ReviewerEmailChallenge).where(ReviewerEmailChallenge.browser_hash.is_not(None)).order_by(ReviewerEmailChallenge.browser_expires_at.desc()))
    if restriction == "expired":
        latest.proof_expires_at = utc_now() - timedelta(seconds=1)
    elif restriction == "deleted":
        user.deleted_at = utc_now()
    elif restriction == "admin":
        user.role = UserRole.ADMIN
    else:
        member.state = MembershipState.REVOKED
    db_session.commit()
    with pytest.raises(AccessDenied):
        confirm_email(db_session, proof, browser)
    with pytest.raises(AccessDenied):
        exchange(db_session, c.id, browser)


@pytest.mark.parametrize("state", [MembershipState.REJECTED, MembershipState.REVOKED])
def test_inactive_member_cannot_self_restore(db_session, state):
    c = course(db_session)
    begin(db_session, c.id, "reviewer@example.com", "Reviewer", admin_first=True)
    member = db_session.scalar(select(CourseMembership))
    member.state = state
    db_session.commit()
    with pytest.raises(AccessDenied):
        begin(db_session, c.id, "reviewer@example.com", "Reviewer", admin_first=True)
    assert member.state is state


def test_admin_first_browser_flow_and_mail(client, monkeypatch):
    from pydantic import SecretStr
    from app.config import get_settings
    from app.services.accounts import register_account
    from app.services.notification_pilot import deliver_access_mail
    settings = get_settings()
    for key, value in dict(reviewer_access_enabled=True, reviewer_access_mail_secret=SecretStr("test-only"),
            reviewer_access_admin_email="admin@example.com", reviewer_access_sender="sender@example.com",
            reviewer_access_origin="https://testserver").items():
        monkeypatch.setattr(settings, key, value)
    with client.db_factory() as db:
        cid = course(db).id
        admin = register_account(db, email="admin@example.com", password="long enough password")
        admin.role, admin.approved_at = UserRole.ADMIN, utc_now()
        db.commit()
    path = f"/reviewer-access/request/{cid}"
    page = client.get(path)
    assert '>Request access<' in page.text and 'name="requested_role"' in page.text
    assert 'Email address' in page.text
    signin = client.get(path, params={"mode": "signin", "email": 'a"@example.com'})
    assert 'Send sign-in link' in signin.text and 'name="display_name"' not in signin.text
    assert 'a&#34;@example.com' in signin.text
    csrf = client.cookies['csrf_token']
    response = client.post(path, data=dict(csrf_token=csrf, email="reviewer@example.com", display_name="Reviewer", requested_role="ld_dcd"))
    assert 'admin approval' in response.text
    messages = []
    def drain():
        with client.db_factory() as db:
            assert deliver_access_mail(db, settings, lambda msg, to: messages.append((msg, to)))
            assert not deliver_access_mail(db, settings, lambda msg, to: messages.append((msg, to)))
    drain()
    assert messages[0][1] == 'admin@example.com'
    assert 'Email unverified' in messages[0][0].get_content()
    assert 'ld_dcd' in messages[0][0].get_content()
    with client.db_factory() as db:
        mid = db.scalar(select(CourseMembership.id))
        challenge = db.scalar(select(ReviewerEmailChallenge))
        challenge.proof_expires_at = utc_now() - timedelta(days=1)
        db.commit()
    client.post('/auth/login', json=dict(email="admin@example.com", password="long enough password"))
    pending = client.get('/admin/users')
    assert 'Email unverified' in pending.text and 'ld_dcd' in pending.text
    assert client.post(f'/admin/memberships/{mid}/approve-request', data=dict(csrf_token=csrf, role="sme"), follow_redirects=False).status_code == 303
    with client.db_factory() as db:
        challenge = db.scalar(select(ReviewerEmailChallenge))
        assert challenge.proof_expires_at.replace(tzinfo=utc_now().tzinfo) > utc_now() + timedelta(minutes=19)
    drain()
    body = messages[-1][0].get_content()
    assert 'sme' in body and 'https://learn.example.com/course/view.php?id=456' in body
    proof = body.split('/reviewer-access/verify#')[-1].split()[0]
    assert client.post('/reviewer-access/verify', data=dict(csrf_token=csrf, proof=proof)).status_code == 200
    with client.db_factory() as db:
        assert db.scalar(select(ReviewerEmailChallenge)).confirmed_at is not None
    assert 'type="password"' not in client.get('/register').text
    assert client.post('/register', data=dict(csrf_token=csrf)).status_code == 403
