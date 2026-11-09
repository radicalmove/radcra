"""One-course, one-inbox Sphere email pilot."""

import argparse
from contextlib import closing
from datetime import timedelta
from email.headerregistry import Address
from email.message import EmailMessage
from getpass import getpass
import os
from pathlib import Path
import smtplib
import ssl
import sys
from urllib.parse import urlsplit

from sqlalchemy import or_, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Comment, CommentStatus, CommentStatusEvent, Course, CourseMembership, MembershipState, NotificationOutbox, ReviewerEmailChallenge, User, UserRole
from app.security import token_hash, utc_now
from app.services.reviewer_email_access import mail_proof


PREVIEW_TEXT = "[Sphere automatic notification test] Test comment to check scheduled email delivery. No action needed."


def _configured(settings):
    return all((settings.notification_pilot_course_id, settings.notification_pilot_recipient,
                settings.notification_pilot_sender, settings.notification_pilot_url))


def _eligible(db, comment, event):
    from app.services.comments import visible_comment_for

    if event.status is CommentStatus.RESOLVED:
        if comment.author_user_id == event.actor_user_id:
            return False
        author = db.get(User, comment.author_user_id)
        if author is None or author.approved_at is None or author.deleted_at is not None:
            return False
        membership = db.scalar(select(CourseMembership).where(
            CourseMembership.course_id == comment.course_id,
            CourseMembership.user_id == author.id,
        ))
        if membership is not None and membership.state is not MembershipState.APPROVED:
            return False
        return visible_comment_for(db, author, comment.id) is not None

    leads = db.scalars(select(User).join(CourseMembership, CourseMembership.user_id == User.id).where(
        CourseMembership.course_id == comment.course_id,
        CourseMembership.role == UserRole.LD_DCD,
        CourseMembership.state == MembershipState.APPROVED,
        User.id != event.actor_user_id,
        User.approved_at.is_not(None),
        User.deleted_at.is_(None),
    ))
    return any(visible_comment_for(db, lead, comment.id) is not None for lead in leads)


def queue_pilot_event(db, comment, event):
    settings = get_settings()
    if not _configured(settings) or comment.course_id != settings.notification_pilot_course_id:
        return
    if _eligible(db, comment, event):
        db.flush()
        db.add(NotificationOutbox(event_id=event.id, next_attempt_at=event.created_at))


def deliver_one(db, settings, send, *, now=None):
    if not _configured(settings):
        return False
    instant = now or utc_now()
    row = db.execute(select(NotificationOutbox, CommentStatusEvent, Comment)
        .join(CommentStatusEvent, CommentStatusEvent.id == NotificationOutbox.event_id)
        .join(Comment, Comment.id == CommentStatusEvent.comment_id)
        .where(Comment.course_id == settings.notification_pilot_course_id,
               NotificationOutbox.finished_at.is_(None), NotificationOutbox.next_attempt_at <= instant)
        .order_by(NotificationOutbox.next_attempt_at, NotificationOutbox.event_id)
        .limit(1).with_for_update(of=NotificationOutbox, skip_locked=True)).first()
    if row is None:
        return False
    job, event, comment = row
    if not _eligible(db, comment, event):
        job.finished_at = instant
    else:
        address = Address(addr_spec=settings.notification_pilot_recipient)
        sender = Address(display_name="Sphere Notifications", addr_spec=settings.notification_pilot_sender)
        link = urlsplit(settings.notification_pilot_url)
        if link.scheme != "https" or not link.hostname or link.username or link.password:
            raise ValueError("Configure a trusted HTTPS Sphere URL.")
        resolved = event.status is CommentStatus.RESOLVED
        message = EmailMessage()
        message["From"], message["To"] = sender, address
        message["Subject"] = "[Sphere test] Comment resolved" if resolved else "[Sphere test] New comment"
        body = "A comment was resolved." if resolved else "A new comment was added."
        course = db.get(Course, comment.course_id)
        course_link = urlsplit(course.normalized_url) if course and course.is_confirmed else None
        if (course_link and course_link.scheme == "https" and course_link.hostname
                and not course_link.username and not course_link.password
                and f"https://{course_link.netloc}" == course.moodle_origin
                and course_link.path == "/course/view.php"
                and course_link.query == f"id={course.moodle_course_id}" and not course_link.fragment):
            destination = f"Open course in Moodle: {course.normalized_url}"
        else:
            destination = f"Open Sphere: {settings.notification_pilot_url}"
        if comment.id == settings.notification_pilot_preview_comment_id and comment.body == PREVIEW_TEXT:
            details = f"Location: {course.title}\nComment: {PREVIEW_TEXT}\n\n"
            footer = "Pilot notification; synthetic test comment."
        else:
            details = ""
            footer = "Pilot notification; no comment text is included."
        message.set_content(f"{body}\n\n{details}{destination}\n\n{footer}")
        job.attempts += 1
        try:
            send(message, address.addr_spec)
        except (OSError, smtplib.SMTPException) as exc:
            print(f"Sphere notification attempt {job.attempts} failed ({type(exc).__name__}).", file=sys.stderr)
            if job.attempts >= 3:
                job.finished_at = instant
            else:
                job.next_attempt_at = instant + timedelta(minutes=job.attempts)
        else:
            job.finished_at = instant
    db.commit()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="store_true", help="Read the app password from a systemd credential.")
    args = parser.parse_args()
    settings = get_settings()
    release_mail = _access_release_configured(settings)
    if not release_mail and not _configured(settings):
        parser.error("Configure Sphere access email or the comment notification pilot first.")
    if args.service:
        directory = os.environ.get("CREDENTIALS_DIRECTORY")
        if not directory:
            parser.error("Systemd credential directory is missing.")
        try:
            password = "".join((Path(directory) / "gmail-app-password").read_text().split())
        except (OSError, UnicodeError):
            parser.error("Cannot read the systemd Gmail credential.")
    else:
        if not sys.stdin.isatty():
            parser.error("Use an interactive terminal to enter the app password privately.")
        password = "".join(getpass("Sphere Gmail app password (hidden): ").split())
    if not password:
        parser.error("No app password entered.")

    def send(message, address):
        sender = message["From"].addresses[0].addr_spec
        with closing(smtplib.SMTP("smtp.gmail.com", 587, timeout=15)) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.user, smtp.password = sender, password
            smtp.auth("PLAIN", smtp.auth_plain)
            smtp.send_message(message, from_addr=sender, to_addrs=[address])
        print(f"Gmail accepted: {message['Subject']}")

    with SessionLocal() as db:
        for _ in range(10):
            if not deliver_access_mail(db, settings, send):
                break
        for _ in range(20):
            if not deliver_one(db, settings, send):
                break


def _access_release_configured(settings):
    return settings.reviewer_access_enabled and all((
        settings.reviewer_access_mail_secret, settings.reviewer_access_admin_email,
        settings.reviewer_access_origin, settings.reviewer_access_sender,
    ))


def deliver_access_mail(db, settings, send):
    secret = settings.reviewer_access_mail_secret
    release_mail = _access_release_configured(settings)
    if not secret or (settings.reviewer_access_enabled and not release_mail) or (not release_mail and not _configured(settings)):
        return False
    query = select(ReviewerEmailChallenge).where(
        or_(ReviewerEmailChallenge.verification_mail_pending.is_(True),
            ReviewerEmailChallenge.admin_mail_pending.is_(True),
            ReviewerEmailChallenge.approval_mail_pending.is_(True)),
    )
    if not release_mail:
        query = query.where(ReviewerEmailChallenge.course_id == settings.notification_pilot_course_id,
                            ReviewerEmailChallenge.email == settings.notification_pilot_recipient)
    challenge = db.scalar(query.order_by(ReviewerEmailChallenge.proof_expires_at).limit(1).with_for_update(skip_locked=True))
    if challenge is None:
        return False
    course = db.get(Course, challenge.course_id)
    if not course or not course.is_confirmed:
        return False
    origin = (settings.reviewer_access_origin if release_mail else settings.notification_pilot_url).rstrip("/")
    recipient = challenge.email if release_mail else settings.notification_pilot_recipient
    sender = settings.reviewer_access_sender if release_mail else settings.notification_pilot_sender
    link = urlsplit(origin)
    if link.scheme != "https" or not link.hostname or link.username or link.password or link.path or link.query or link.fragment:
        raise ValueError("Configure an HTTPS Sphere origin for access mail")
    if challenge.verification_mail_pending:
        field = "verification_mail_pending"
        proof = mail_proof(secret.get_secret_value(), challenge.browser_hash)
        if challenge.proof_expires_at.replace(tzinfo=utc_now().tzinfo) <= utc_now() or token_hash(proof) != challenge.proof_hash:
            setattr(challenge, field, False)
            db.commit()
            return True
        subject = "[Sphere test] Confirm your email"
        body = f"Open this link in the Chrome profile where you requested access:\n{origin}/reviewer-access/verify#{proof}"
    elif challenge.admin_mail_pending:
        field = "admin_mail_pending"
        subject = "[Sphere test] Course access request"
        if release_mail:
            recipient = settings.reviewer_access_admin_email
        body = f"{challenge.display_name or challenge.email} ({challenge.email}) requested access to {course.title}.\n\nReview pending requests: {origin}/admin"
        if challenge.admin_first:
            body += f"\n\nEmail unverified. Requested role: {challenge.requested_role} (advisory only). Choose the actual course role when approving."
    else:
        field = "approval_mail_pending"
        subject = "[Sphere test] Course access approved"
        body = f"Your course access was approved. Open {course.normalized_url} and choose Check access in Sphere."
        if challenge.admin_first:
            proof = mail_proof(secret.get_secret_value(), challenge.browser_hash)
            if challenge.proof_expires_at.replace(tzinfo=utc_now().tzinfo) <= utc_now() or token_hash(proof) != challenge.proof_hash:
                challenge.approval_mail_pending = False
                db.commit()
                return True
            member = db.scalar(select(CourseMembership).join(User, User.id == CourseMembership.user_id).where(
                CourseMembership.course_id == course.id, User.email == challenge.email))
            role = member.role.value if member else "reviewer"
            body = (f"Your access to {course.title} was approved. Assigned role: {role}.\n\n"
                    f"Confirm your email in the same Chrome profile within 20 minutes:\n{origin}/reviewer-access/verify#{proof}\n\n"
                    f"Then return to Moodle: {course.moodle_origin}/course/view.php?id={course.moodle_course_id}\n"
                    "Choose Check access in Sphere to connect this browser.")
    if release_mail and field != "verification_mail_pending":
        member = db.scalar(select(CourseMembership).join(User, User.id == CourseMembership.user_id).where(
            CourseMembership.course_id == course.id, User.email == challenge.email, User.deleted_at.is_(None)))
        expected = MembershipState.PENDING if field == "admin_mail_pending" else MembershipState.APPROVED
        if member is None or member.state is not expected:
            setattr(challenge, field, False)
            db.commit()
            return True
    if release_mail:
        subject = subject.replace("[Sphere test]", "Sphere:", 1)
    address = Address(addr_spec=recipient)
    message = EmailMessage()
    message["From"] = Address(display_name="Sphere Notifications", addr_spec=sender)
    message["To"] = address
    message["Subject"] = subject
    message.set_content(body)
    try:
        send(message, address.addr_spec)
    except (OSError, smtplib.SMTPException) as exc:
        db.rollback()
        print(f"Sphere access email failed ({type(exc).__name__}).", file=sys.stderr)
        return False
    setattr(challenge, field, False)
    db.commit()
    return True


if __name__ == "__main__":
    main()
