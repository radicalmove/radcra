"""Email proof and course approval are independent gates for a new browser."""

from datetime import timedelta
import hmac

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Course, CourseMembership, MembershipState, ReviewerEmailChallenge, User, UserRole
from app.security import generate_token, hash_password, token_hash, utc_now
from app.services.access import AccessDenied, AccessResult, _issue_access


def mail_proof(secret, browser_hash):
    return hmac.digest(secret.encode(), f"sphere-reviewer-email:{browser_hash}".encode(), "sha256").hex()


def begin(db, course_id, email, display_name="", *, mail_secret=None):
    course = db.get(Course, course_id)
    name = display_name.strip()
    try:
        address = validate_email(email, check_deliverability=False, allow_smtputf8=False).normalized.lower()
    except EmailNotValidError as exc:
        raise AccessDenied("Invalid access request") from exc
    if not course or not course.is_confirmed or len(name) > 100:
        raise AccessDenied("Invalid access request")
    now = utc_now()
    browser_secret = generate_token()
    browser_hash = token_hash(browser_secret)
    if mail_secret:
        # Serialize throttling across simultaneous requests on PostgreSQL.
        if db.bind.dialect.name == "postgresql":
            from sqlalchemy import text
            db.execute(text("SELECT pg_advisory_xact_lock(661315270691)"))
        recent = db.scalars(select(ReviewerEmailChallenge).where(
            ReviewerEmailChallenge.proof_expires_at > now - timedelta(minutes=40)).limit(30)).all()
        if len(recent) >= 30 or sum(row.email == address for row in recent) >= 3:
            raise AccessDenied("Please wait before requesting another email")
    proof = mail_proof(mail_secret, browser_hash) if mail_secret else generate_token()
    db.add(ReviewerEmailChallenge(course_id=course_id, email=address, display_name=name,
        proof_hash=token_hash(proof), browser_hash=browser_hash, verification_mail_pending=bool(mail_secret),
        proof_expires_at=now + timedelta(minutes=20), browser_expires_at=now + timedelta(days=7)))
    db.commit()
    return proof, browser_secret


def confirm_email(db, proof, browser_secret, *, queue_mail=False):
    now = utc_now()
    challenge = db.scalar(select(ReviewerEmailChallenge).where(
        ReviewerEmailChallenge.proof_hash == token_hash(proof),
        ReviewerEmailChallenge.browser_hash == token_hash(browser_secret),
        ReviewerEmailChallenge.proof_expires_at > now,
        ReviewerEmailChallenge.confirmed_at.is_(None),
    ).with_for_update())
    if challenge is None:
        raise AccessDenied("Invalid or expired email link")
    course = db.get(Course, challenge.course_id)
    user = db.scalar(select(User).where(User.email == challenge.email))
    if course is None or not course.is_confirmed or (user and (user.deleted_at or user.role is UserRole.ADMIN)):
        raise AccessDenied("Unable to request reviewer access")
    try:
        if user is None:
            if not challenge.display_name:
                raise AccessDenied("Enter your name to request access")
            user = User(email=challenge.email, display_name=challenge.display_name,
                        password_hash=hash_password(generate_token()), role=UserRole.BETA_TESTER, created_at=now)
            db.add(user)
            db.flush()
        membership = db.scalar(select(CourseMembership).where(
            CourseMembership.user_id == user.id, CourseMembership.course_id == challenge.course_id))
        created = membership is None
        if created:
            membership = CourseMembership(user_id=user.id, course_id=challenge.course_id, role=UserRole.BETA_TESTER,
                state=MembershipState.PENDING, created_at=now, updated_at=now)
            db.add(membership)
        elif membership.state not in {MembershipState.PENDING, MembershipState.APPROVED}:
            raise AccessDenied("Unable to request reviewer access")
        challenge.confirmed_at = now
        challenge.verification_mail_pending = False
        challenge.admin_mail_pending = created and queue_mail
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AccessDenied("Unable to request reviewer access") from exc
    return membership, created


def exchange(db, course_id, browser_secret):
    now = utc_now()
    challenge = db.scalar(select(ReviewerEmailChallenge).where(
        ReviewerEmailChallenge.course_id == course_id,
        ReviewerEmailChallenge.browser_hash == token_hash(browser_secret),
        ReviewerEmailChallenge.confirmed_at.is_not(None),
        ReviewerEmailChallenge.exchanged_at.is_(None),
        ReviewerEmailChallenge.browser_expires_at > now,
    ).with_for_update())
    if challenge is None:
        raise AccessDenied("Unable to verify reviewer access")
    membership = db.scalar(select(CourseMembership).join(User, User.id == CourseMembership.user_id).where(
        User.email == challenge.email, User.deleted_at.is_(None), User.role != UserRole.ADMIN,
        CourseMembership.course_id == course_id, CourseMembership.state == MembershipState.APPROVED))
    if membership is None:
        raise AccessDenied("Unable to verify reviewer access")
    token, credential = _issue_access(db, membership)
    challenge.exchanged_at = now
    db.commit()
    return AccessResult(membership, token, credential, "")
