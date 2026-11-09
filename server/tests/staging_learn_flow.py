"""Disposable two-origin staging. Captures mail; never connects to SMTP."""

from email.message import EmailMessage
from secrets import token_urlsafe

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import Base, SessionLocal
from app.main import app
from app.services.accounts import provision_bootstrap_admin
from app.services.courses import register_course
from app.services.notification_pilot import deliver_access_mail

settings = get_settings()
if (settings.database_url != "sqlite+pysqlite:///:memory:"
        or settings.reviewer_access_origin != "https://localhost:48140"
        or not settings.reviewer_access_enabled):
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
        register_course(db, course_url=f"{origin}/course/view.php?id=3598", title=title, moodle_course_id=3598)


@app.get("/__staging/inbox")
def test_mailbox():
    def capture(message: EmailMessage, recipient: str):
        mail.append({"recipient": recipient, "subject": str(message["Subject"]), "body": message.get_content()})

    with SessionLocal() as db:
        while deliver_access_mail(db, settings, capture):
            pass
    return {"messages": mail, "admin_password": admin_password}
