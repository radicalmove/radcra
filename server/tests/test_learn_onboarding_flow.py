import pytest
from sqlalchemy import select
from app.config import get_settings
from app.models import Course, CourseMembership, MembershipState, ReviewerEmailChallenge, User, UserRole
from app.security import utc_now
from app.services.accounts import register_account
from app.services.courses import register_course
from app.services.notification_pilot import deliver_access_mail
from test_admin_routes import client


def configure(monkeypatch):
    from pydantic import SecretStr
    s = get_settings()
    for key, value in dict(reviewer_access_enabled=False, reviewer_access_learn_trial_email=None,
            reviewer_access_mail_secret=SecretStr("test-only"), reviewer_access_admin_email="admin@example.com",
            reviewer_access_sender="sender@example.com", reviewer_access_origin="https://testserver",
            extension_redirect_uris="https://extension.chromiumapp.org/").items():
        monkeypatch.setattr(s, key, value)
    return s


def setup_course(client, number, enabled=True):
    with client.db_factory() as db:
        c = register_course(db, course_url=f"https://learn.canterbury.ac.nz/course/view.php?id={number}",
                            title=f"Course {number}", moodle_course_id=number)
        c.email_onboarding_enabled = enabled
        db.commit()
        return c.id


@pytest.mark.parametrize("number", [41, 42])
def test_course_opt_in_request_approval_email_and_signin_after_enrollment_disabled(client, monkeypatch, number):
    s = configure(monkeypatch)
    cid = setup_course(client, number)
    path = f"/reviewer-access/request/{cid}"
    page = client.get(path)
    assert 'name="requested_role"' in page.text
    csrf = client.cookies["csrf_token"]
    response = client.post(path, data=dict(csrf_token=csrf, display_name="Reviewer", email="reader@example.com", requested_role="sme"))
    assert response.status_code == 200 and "admin approval" in response.text
    messages = []
    def drain():
        with client.db_factory() as db:
            assert deliver_access_mail(db, s, lambda msg, to: messages.append((msg,to)))
    drain()
    assert messages[-1][1] == "admin@example.com"
    with client.db_factory() as db:
        member = db.scalar(select(CourseMembership))
        mid = member.id
        user = db.get(User, member.user_id)
        assert member.state is MembershipState.PENDING and member.role is UserRole.BETA_TESTER
        admin = register_account(db, email="admin@example.com", password="long enough password")
        admin.role, admin.approved_at = UserRole.ADMIN, utc_now()
        db.commit()
    client.post("/auth/login", json=dict(email="admin@example.com", password="long enough password"))
    assert client.post(f"/admin/memberships/{mid}/approve-request", data=dict(csrf_token=csrf, role="sme"), follow_redirects=False).status_code==303
    drain()
    proof=messages[-1][0].get_content().split("/reviewer-access/verify#")[-1].split()[0]
    assert "Email verified" in client.post("/reviewer-access/verify", data=dict(csrf_token=csrf, proof=proof)).text
    finish=client.get(f"/reviewer-access/finish/{cid}",params={"redirect_uri":"https://extension.chromiumapp.org/"},follow_redirects=False)
    from urllib.parse import parse_qs,urlsplit
    code=parse_qs(urlsplit(finish.headers["location"]).fragment)["reviewer_code"][0]
    assert client.post("/reviewer-access/exchange",json={"course_id":str(cid),"code":code}).status_code==200
    with client.db_factory() as db:
        db.get(Course,cid).email_onboarding_enabled=False
        db.commit()
    assert client.get(path).status_code == 404
    assert client.get(path,params={"mode":"signin"}).status_code==200
    response=client.post(path,data=dict(csrf_token=csrf,mode="signin",email="reader@example.com"))
    assert response.status_code==200
    drain()
    assert messages[-1][1]=="reader@example.com"
    proof=messages[-1][0].get_content().split("/reviewer-access/verify#")[-1].split()[0]
    assert "Email verified" in client.post("/reviewer-access/verify",data=dict(csrf_token=csrf,proof=proof)).text
    assert client.post(path,data=dict(csrf_token=csrf,email="new@example.com",display_name="New")).status_code==404
    with client.db_factory() as db:
        assert db.scalar(select(User).where(User.email=="new@example.com")) is None


def test_disabled_course_cannot_send_enrollment_mail(client,monkeypatch):
    s=configure(monkeypatch)
    cid=setup_course(client,43)
    path=f"/reviewer-access/request/{cid}"
    client.get(path)
    client.post(path,data=dict(csrf_token=client.cookies["csrf_token"],email="reader@example.com",display_name="Reader"))
    with client.db_factory() as db:
        db.get(Course,cid).email_onboarding_enabled=False
        db.commit()
        messages=[]
        assert not deliver_access_mail(db,s,lambda *args:messages.append(args))
        assert not messages


def test_revoked_signin_does_not_block_other_course_mail(client,monkeypatch):
    from app.services.reviewer_email_access import begin
    s=configure(monkeypatch)
    a=setup_course(client,61)
    b=setup_course(client,62)
    with client.db_factory() as db:
        user=register_account(db,email="old@example.com",password="long enough password")
        user.approved_at=utc_now()
        member=CourseMembership(user_id=user.id,course_id=a,state=MembershipState.APPROVED,
            role=UserRole.SME,created_at=utc_now(),updated_at=utc_now(),approved_at=utc_now())
        db.add(member);db.commit()
        begin(db,a,user.email,admin_first=True,signin=True,course_onboarding=True,mail_secret="test-only")
        member.state=MembershipState.REVOKED
        db.commit()
        begin(db,b,"new@example.com","New",admin_first=True,course_onboarding=True,mail_secret="test-only")
        messages=[]
        while deliver_access_mail(db,s,lambda msg,to:messages.append(to)):
            pass
        assert messages==["admin@example.com"]


@pytest.mark.parametrize("enabled",[False,True])
def test_managed_learn_memberships_cannot_use_anonymous_legacy_signin(client,monkeypatch,enabled):
    configure(monkeypatch)
    cid=setup_course(client,71,enabled)
    with client.db_factory() as db:
        user=register_account(db,email="victim@example.com",password="long enough password")
        user.approved_at=utc_now()
        member=CourseMembership(user_id=user.id,course_id=cid,role=UserRole.LD_DCD,
            state=MembershipState.APPROVED,created_at=utc_now(),updated_at=utc_now(),approved_at=utc_now())
        db.add(member);db.commit()
        mid=member.id
    assert client.post("/api/access/reviewers",json={"course_handle":str(cid)}).status_code==403
    assert client.post("/api/access/reviewers/sign-in",json={"course_handle":str(cid),"membership_id":str(mid)}).status_code==403


@pytest.mark.parametrize("confirmed",[False,True])
def test_legacy_uco_lead_cannot_see_managed_learn_comments_without_membership(client,monkeypatch,confirmed):
    from app.services.accounts import create_extension_login_code,exchange_extension_login_code
    from app.services.comments import create_comment, dashboard_comments_for, visible_comment_for
    s=configure(monkeypatch)
    cid=setup_course(client,72)
    with client.db_factory() as db:
        lead=register_account(db,email="lead@example.com",password="long enough password")
        lead.role,lead.approved_at=UserRole.LD_DCD,utc_now()
        admin=register_account(db,email="admin@example.com",password="long enough password")
        admin.role,admin.approved_at=UserRole.ADMIN,utc_now()
        db.commit()
        c=db.get(Course,cid)
        comment=create_comment(db,admin,course_id=cid,page_url=c.normalized_url,page_title=c.title,
            body="Private LEARN feedback",anchor_type="text_highlight",selected_quote="Private",css_selector="main p")
        comment_id=comment.id
        c.is_confirmed=confirmed
        db.commit()
        code=create_extension_login_code(db,lead,"https://extension.chromiumapp.org/")
        token=exchange_extension_login_code(db,code,"https://extension.chromiumapp.org/")
        assert visible_comment_for(db,lead,comment_id) is None
        assert not dashboard_comments_for(db,lead)
    assert client.get("/api/comments",params={"course_id":str(cid)},headers={"Authorization":f"Bearer {token}"}).status_code==404
    client.post("/auth/login",json={"email":"lead@example.com","password":"long enough password"})
    assert client.get(f"/dashboard/threads/{comment_id}").status_code==404


def test_learn_course_lead_has_dashboard_controls_without_global_lead_role(client,monkeypatch):
    from app.services.comments import create_comment
    configure(monkeypatch)
    cid=setup_course(client,73)
    with client.db_factory() as db:
        lead=register_account(db,email="course-lead@example.com",password="long enough password")
        lead.approved_at=utc_now()
        db.add(CourseMembership(user_id=lead.id,course_id=cid,role=UserRole.LD_DCD,
            state=MembershipState.APPROVED,created_at=utc_now(),updated_at=utc_now()))
        db.commit()
        c=db.get(Course,cid)
        comment=create_comment(db,lead,course_id=cid,page_url=c.normalized_url,page_title=c.title,
            body="Lead feedback",anchor_type="text_highlight",selected_quote="Lead",css_selector="p")
        comment_id=comment.id
    client.post("/auth/login",json={"email":"course-lead@example.com","password":"long enough password"})
    page=client.get(f"/dashboard/threads/{comment_id}")
    assert page.status_code==200
    assert "Change status" in page.text and "Share with SME" in page.text
