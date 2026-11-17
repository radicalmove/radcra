from datetime import timedelta
import pytest
from sqlalchemy import select, func
from app.models import CourseMembership, MembershipState, User, UserRole
from app.security import utc_now
from app.services.accounts import register_account
from app.services.courses import register_course
from app.services.access import AccessDenied
from test_admin_routes import client


def seed(db):
    admin=register_account(db,email="admin@example.com",password="long enough password")
    admin.role,admin.approved_at=UserRole.ADMIN,utc_now()
    user=register_account(db,email="reviewer@example.com",password="long enough password")
    user.approved_at=utc_now()
    source=register_course(db,course_url="https://my.uconline.ac.nz/course/view.php?id=81",title="Source",moodle_course_id=81)
    target=register_course(db,course_url="https://learn.canterbury.ac.nz/course/view.php?id=81",title="Destination",moodle_course_id=81)
    m=CourseMembership(user_id=user.id,course_id=source.id,state=MembershipState.APPROVED,
        role=UserRole.SME,approved_at=utc_now(),created_at=utc_now(),updated_at=utc_now())
    db.add(m);db.commit()
    return admin,user,source,target,m


def test_preview_transfers_only_selected_approved_roles_and_is_idempotent(db_session):
    from app.models import CourseMigrationPreview, CourseMigrationMapping
    from app.services.course_migration import preview_transfer, apply_transfer
    a,u,s,t,m=seed(db_session)
    p=preview_transfer(db_session,a,s.normalized_url,t.normalized_url)
    assert p.rows[0]["membership_id"]==str(m.id) and p.rows[0]["eligible"]
    assert db_session.scalar(select(func.count()).select_from(CourseMembership))==1
    first=apply_transfer(db_session,a,p.id,[str(m.id)])
    assert first==apply_transfer(db_session,a,p.id,[str(m.id)])
    target=db_session.scalar(select(CourseMembership).where(CourseMembership.course_id==t.id))
    assert target.user_id==u.id and target.role is UserRole.SME and target.approved_by_user_id==a.id
    assert db_session.scalar(select(func.count()).select_from(CourseMigrationMapping))==1
    assert m.course_id==s.id and not t.email_onboarding_enabled
    with pytest.raises(AccessDenied):
        apply_transfer(db_session,a,p.id,[])


@pytest.mark.parametrize("change",["revoked","archived","unapproved","role","target","expired","actor","tampered","course"])
def test_stale_or_invalid_transfer_never_grants_access(db_session,change):
    from app.services.course_migration import preview_transfer,apply_transfer
    a,u,s,t,m=seed(db_session)
    p=preview_transfer(db_session,a,s.normalized_url,t.normalized_url)
    selection=[str(m.id)]
    if change=="revoked": m.state=MembershipState.REVOKED
    elif change=="archived": u.deleted_at=utc_now()
    elif change=="unapproved": u.approved_at=None
    elif change=="role": m.role=UserRole.LD_DCD
    elif change=="target":
        db_session.add(CourseMembership(user_id=u.id,course_id=t.id,state=MembershipState.REVOKED,
            role=UserRole.SME,created_at=utc_now(),updated_at=utc_now()))
    elif change=="expired": p.expires_at=utc_now()-timedelta(seconds=1)
    elif change=="actor": a.role=UserRole.LD_DCD
    elif change=="tampered": selection=["not-a-membership"]
    elif change=="course": t.is_confirmed=False
    db_session.commit()
    with pytest.raises(AccessDenied):
        apply_transfer(db_session,a,p.id,selection)
    assert db_session.scalar(select(func.count()).select_from(CourseMembership).where(
        CourseMembership.course_id==t.id,CourseMembership.state==MembershipState.APPROVED))==0


@pytest.mark.parametrize("restriction",["archived","pending","revoked","admin"])
def test_preview_excludes_ineligible_accounts(db_session,restriction):
    from app.services.course_migration import preview_transfer
    a,u,s,t,m=seed(db_session)
    if restriction=="archived":u.deleted_at=utc_now()
    elif restriction=="pending":m.state=MembershipState.PENDING
    elif restriction=="revoked":m.state=MembershipState.REVOKED
    else:m.role=UserRole.ADMIN
    db_session.commit()
    p=preview_transfer(db_session,a,s.normalized_url,t.normalized_url)
    assert not any(row["eligible"] for row in p.rows)


def test_forms_require_admin_csrf_and_confirmation(client):
    with client.db_factory() as db:
        a,u,s,t,m=seed(db)
        tid=t.id
    assert client.get("/admin/course-migration").status_code in (401,303)
    client.post("/auth/login",json={"email":"admin@example.com","password":"long enough password"})
    page=client.get("/admin/course-migration")
    assert page.status_code==200
    csrf=client.cookies["csrf_token"]
    assert client.post(f"/admin/courses/{tid}/email-onboarding",data={"enabled":"true"}).status_code==403
    assert client.post(f"/admin/courses/{tid}/email-onboarding",data={"enabled":"true","csrf_token":csrf},follow_redirects=False).status_code==303
    with client.db_factory() as db:
        from app.models import Course,AuditEvent
        assert db.get(Course,tid).email_onboarding_enabled
        assert db.scalar(select(AuditEvent).where(AuditEvent.action=="course.enrollment_changed"))
    client.post("/auth/login",json={"email":"reviewer@example.com","password":"long enough password"})
    assert client.get("/admin/course-migration").status_code==403


def test_partial_selection_and_conflicting_memberships_are_not_overwritten(db_session):
    from app.services.course_migration import preview_transfer,apply_transfer
    a,u,s,t,m=seed(db_session)
    other=register_account(db_session,email="other@example.com",password="long enough password")
    other.approved_at=utc_now()
    second=CourseMembership(user_id=other.id,course_id=s.id,role=UserRole.LD_DCD,
        state=MembershipState.APPROVED,created_at=utc_now(),updated_at=utc_now())
    conflict=CourseMembership(user_id=u.id,course_id=t.id,role=UserRole.BETA_TESTER,
        state=MembershipState.REVOKED,created_at=utc_now(),updated_at=utc_now())
    db_session.add_all([second,conflict]);db_session.commit()
    p=preview_transfer(db_session,a,s.normalized_url,t.normalized_url)
    assert not next(r for r in p.rows if r["user_id"]==str(u.id))["eligible"]
    assert len(apply_transfer(db_session,a,p.id,[str(second.id)]))==1
    assert conflict.state is MembershipState.REVOKED and conflict.role is UserRole.BETA_TESTER
    p2=preview_transfer(db_session,a,s.normalized_url,t.normalized_url)
    assert not any(r["eligible"] for r in p2.rows)


@pytest.mark.parametrize("url",["https://learn.canterbury.ac.nz/course/view.php?id=81",
    "https://my.uconline.ac.nz.evil.example/course/view.php?id=81",
    "https://my.uconline.ac.nz/mod/page/view.php?id=81",
    "https://my.uconline.ac.nz/course/view.php?id=81&id=82"])
def test_mapping_never_guesses_course_from_unsafe_or_wrong_origin_url(db_session,url):
    from app.services.course_migration import preview_transfer
    a,u,s,t,m=seed(db_session)
    with pytest.raises(AccessDenied):
        preview_transfer(db_session,a,url,t.normalized_url)


def test_admin_form_preview_and_apply_is_explicit_and_csrf_protected(client):
    import re
    with client.db_factory() as db:
        a,u,s,t,m=seed(db)
        mid,source,target=str(m.id),s.normalized_url,t.normalized_url
    client.post("/auth/login",json={"email":"admin@example.com","password":"long enough password"})
    client.get("/admin/course-migration")
    csrf=client.cookies["csrf_token"]
    response=client.post("/admin/course-migration/preview",data={"csrf_token":csrf,"source_url":source,"target_url":target})
    assert response.status_code==200 and "Review before granting access" in response.text
    action=re.search(r'action="(/admin/course-migration/[^"]+/apply)"',response.text)[1]
    assert client.post(action,data={"csrf_token":csrf,"membership_id":mid}).status_code==422
    assert client.post(action,data={"confirm":"yes","membership_id":mid}).status_code==403
    data={"csrf_token":csrf,"confirm":"yes","membership_id":mid}
    result=client.post(action,data=data)
    assert result.status_code==200 and "1 reviewer membership(s) transferred" in result.text
    assert client.post(action,data=data).status_code==200
