"""Disposable two-origin staging. Captures mail; never connects to SMTP."""

from email.message import EmailMessage
from secrets import token_urlsafe

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import Base, SessionLocal
from app.main import app
from app.models import CourseMembership, MembershipState, UserRole
from app.security import utc_now
from app.services.accounts import provision_bootstrap_admin, register_account
from app.services.comments import create_comment
from app.services.courses import register_course
from app.services.notification_pilot import deliver_access_mail

settings = get_settings()
scoped = settings.reviewer_access_origin == "https://localhost:48142"
if (settings.database_url != "sqlite+pysqlite:///:memory:"
        or (scoped and (settings.reviewer_access_enabled or settings.reviewer_access_learn_trial_email != "stage-reviewer@example.com"))
        or (not scoped and (settings.reviewer_access_origin != "https://localhost:48140" or not settings.reviewer_access_enabled))):
    raise RuntimeError("LEARN test fixture requires isolated loopback configuration")

staging_db = create_engine("sqlite+pysqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
SessionLocal.configure(bind=staging_db)
Base.metadata.create_all(staging_db)
admin_password = token_urlsafe(32)
mail: list[dict[str, str]] = []
with SessionLocal() as db:
    provision_bootstrap_admin(db, email="stage-admin@example.com", password=admin_password)
    for origin, title in [("https://learn.canterbury.ac.nz", "Test Course - Richard D - Demo Course"),
                          ("https://my.uconline.ac.nz", "UCO isolated identity test")]:
        number = 1170 if scoped and origin == "https://my.uconline.ac.nz" else 3598
        course = register_course(db, course_url=f"{origin}/course/view.php?id={number}", title=title, moodle_course_id=number)
        if number == 1170:
            settings.notification_pilot_course_id = course.id
            settings.notification_pilot_recipient = "stage-reviewer@example.com"
            settings.notification_pilot_sender = "stage-notifications@example.com"
            settings.notification_pilot_url = settings.reviewer_access_origin
            reviewer = register_account(db, email=settings.notification_pilot_recipient, password=token_urlsafe(32),
                                        display_name="Staging Reviewer")
            reviewer.approved_at = utc_now()
            db.add(CourseMembership(course_id=course.id, user_id=reviewer.id, role=UserRole.LD_DCD,
                                    state=MembershipState.APPROVED, created_at=utc_now(), updated_at=utc_now(),
                                    approved_at=utc_now()))
            db.commit()
            create_comment(db, reviewer, course_id=course.id, page_url=course.normalized_url, page_title=title,
                           body="Existing CRJU160 staging feedback", anchor_type="text_highlight",
                           selected_quote="Dummy staging course content", css_selector="main p")


@app.get("/__staging/inbox")
def test_mailbox():
    def capture(message: EmailMessage, recipient: str):
        mail.append({"recipient": recipient, "subject": str(message["Subject"]), "body": message.get_content()})

    with SessionLocal() as db:
        while deliver_access_mail(db, settings, capture):
            pass
    return {"messages": mail, "admin_password": admin_password}
