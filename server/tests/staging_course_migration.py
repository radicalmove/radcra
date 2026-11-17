"""Loopback-only, synthetic staging for normal LEARN access; no SMTP worker."""
from secrets import token_urlsafe
from sqlalchemy import create_engine, select, func
from sqlalchemy.pool import StaticPool
from app.config import get_settings
from app.db import Base, SessionLocal
from app.main import app
from app.models import CourseMembership, MembershipState, UserRole, User, CourseMigrationMapping, Comment
from app.security import utc_now
from app.services.accounts import provision_bootstrap_admin, register_account
from app.services.courses import register_course
from app.services.comments import create_comment
from app.services.notification_pilot import deliver_access_mail

s=get_settings()
if s.database_url!="sqlite+pysqlite:///:memory:" or s.reviewer_access_origin!="https://localhost:48144":
    raise RuntimeError("Only isolated loopback staging is permitted")
if s.reviewer_access_enabled or s.reviewer_access_learn_trial_email:
    raise RuntimeError("No global or trial bypass in per-course tests")
engine=create_engine("sqlite+pysqlite://",poolclass=StaticPool,connect_args={"check_same_thread":False})
SessionLocal.configure(bind=engine)
Base.metadata.create_all(engine)
password=token_urlsafe(32)
mail=[]
ids={}
with SessionLocal() as db:
    provision_bootstrap_admin(db,email="stage-admin@example.com",password=password)
    reviewer=register_account(db,email="stage-reviewer@example.com",password=token_urlsafe(32),display_name="Staging Reviewer")
    reviewer.approved_at=utc_now()
    for key,origin,number in [("source","https://my.uconline.ac.nz",81),("target","https://learn.canterbury.ac.nz",81),
                              ("other","https://learn.canterbury.ac.nz",82),("disabled","https://learn.canterbury.ac.nz",83)]:
        c=register_course(db,course_url=f"{origin}/course/view.php?id={number}",title=f"Synthetic {key}",moodle_course_id=number)
        ids[key]=str(c.id)
        if key=="source":
            db.add(CourseMembership(user_id=reviewer.id,course_id=c.id,role=UserRole.SME,
                state=MembershipState.APPROVED,created_at=utc_now(),updated_at=utc_now(),approved_at=utc_now()))
            db.commit()
            create_comment(db,reviewer,course_id=c.id,page_url=c.normalized_url,page_title=c.title,
                body="Existing UCO history stays here",anchor_type="text_highlight",
                selected_quote="Dummy",css_selector="main p")


@app.get("/__staging/inbox")
def inbox():
    with SessionLocal() as db:
        for _ in range(30):
            if not deliver_access_mail(db,s,lambda msg,to:mail.append(
                    {"recipient":to,"body":msg.get_content(),"subject":str(msg["Subject"])})):
                break
        state={"memberships":db.scalar(select(func.count()).select_from(CourseMembership)),
               "mappings":db.scalar(select(func.count()).select_from(CourseMigrationMapping)),
               "comments":db.scalar(select(func.count()).select_from(Comment))}
    return {"messages":mail,"admin_password":password,"courses":ids,"state":state}
