"""Run only against the disposable Unix-socket PostgreSQL clone."""
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

url=os.environ["DATABASE_URL"]
assert "host=/tmp/sphere-course-rehearsal." in url
engine=create_engine(url)
def migrate(target):
    subprocess.run([sys.executable,"-m","alembic","upgrade",target],check=True)
def fingerprints():
    with engine.connect() as c:
        tables=c.exec_driver_sql("select tablename from pg_tables where schemaname='public' and tablename not in ('alembic_version','course_migration_previews','course_migration_mappings') order by tablename").scalars()
        result={}
        for table in tables:
            assert table.replace("_","").isalnum()
            values=c.exec_driver_sql(f"""select (to_jsonb(t)-'email_onboarding_enabled'-'email_onboarding_configured'-'course_onboarding'-'signin_only')::text from "{table}" t""").scalars().all()
            result[table]=(len(values),hashlib.sha256("\n".join(sorted(values)).encode()).hexdigest())
        return result
migrate("20261110_17")
before=fingerprints()
migrate("head")
assert before==fingerprints()
with engine.connect() as c:
    assert c.exec_driver_sql("select count(*) from courses where email_onboarding_enabled or email_onboarding_configured").scalar_one()==0
    assert c.exec_driver_sql("select version_num from alembic_version").scalar_one()=="20261118_18"
print("Upgrade preserved all original row fingerprints:",{k:v[0] for k,v in before.items()})
subprocess.run([sys.executable,"-m","alembic","downgrade","20261110_17"],check=True)
assert before==fingerprints()
migrate("head")
assert before==fingerprints()
print("Downgrade and repeat upgrade verified.")

from app.models import CourseMembership, CourseMigrationMapping, MembershipState, UserRole, User
from app.security import utc_now
from app.services.accounts import register_account
from app.services.courses import register_course
from app.services.course_migration import preview_transfer,apply_transfer
from app.services.access import AccessDenied
factory=sessionmaker(engine)
with factory() as db:
    from secrets import token_urlsafe
    suffix=token_urlsafe(8)
    admin=register_account(db,email=f"stage-admin-{suffix}@example.com",password=token_urlsafe(32))
    admin.role,admin.approved_at=UserRole.ADMIN,utc_now()
    reviewer=register_account(db,email=f"stage-reviewer-{suffix}@example.com",password=token_urlsafe(32))
    reviewer.approved_at=utc_now()
    src=register_course(db,course_url="https://my.uconline.ac.nz/course/view.php?id=900001",title="Synthetic source",moodle_course_id=900001)
    dst=register_course(db,course_url="https://learn.canterbury.ac.nz/course/view.php?id=900001",title="Synthetic target",moodle_course_id=900001)
    member=CourseMembership(user_id=reviewer.id,course_id=src.id,role=UserRole.SME,state=MembershipState.APPROVED,
        created_at=utc_now(),updated_at=utc_now(),approved_at=utc_now())
    db.add(member);db.commit()
    p1=preview_transfer(db,admin,src.normalized_url,dst.normalized_url)
    p2=preview_transfer(db,admin,src.normalized_url,dst.normalized_url)
    aid,mid,did=admin.id,str(member.id),dst.id
    ids=[p1.id,p2.id]
def apply(pid):
    with factory() as db:
        try:
            return len(apply_transfer(db,db.get(User,aid),pid,[mid]))
        except AccessDenied:
            db.rollback()
            return 0
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(apply,ids))
assert sorted(results)==[0,1],results
with factory() as db:
    assert db.scalar(select(func.count()).select_from(CourseMembership).where(CourseMembership.course_id==did))==1
    assert db.scalar(select(func.count()).select_from(CourseMigrationMapping).where(CourseMigrationMapping.target_course_id==did))==1
print("Concurrent PostgreSQL apply: one grant, one stale preview, no duplicates.")
