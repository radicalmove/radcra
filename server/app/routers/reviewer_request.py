"""Browser entry point for course-scoped access requests."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import select
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from urllib.parse import urlencode

from app.db import get_session
from app.config import get_settings
from app.models import Course, CourseMembership, MembershipState, ReviewerEmailChallenge, User
from app.routers.auth import _csrf_response, _form_with_csrf, extension_redirect_uris
from app.routers.access import _access_json
from app.security import generate_token, token_hash, utc_now
from app.services.access import AccessDenied
from app.services.reviewer_email_access import begin, confirm_email, exchange
from app.url_validation import canonical_https_url

router = APIRouter(prefix="/reviewer-access")
COOKIE = "__Host-sphere-reviewer-request"


def course_cookie(course_id):
    return f"{COOKIE}-{course_id}"


def _browser_cookie(response, name, secret):
    response.set_cookie(name, secret, secure=True, httponly=True, samesite="lax", max_age=604800, path="/")
    return response


def request_mailer():
    settings = get_settings()
    if settings.reviewer_access_enabled:
        if all((settings.reviewer_access_mail_secret, settings.reviewer_access_admin_email,
                settings.reviewer_access_origin, settings.reviewer_access_sender)):
            return settings.reviewer_access_mail_secret.get_secret_value()
        raise HTTPException(status_code=503, detail="Course access email is not configured")
    if settings.reviewer_access_mail_secret and settings.notification_pilot_course_id and settings.notification_pilot_recipient:
        return settings.reviewer_access_mail_secret.get_secret_value()
    raise HTTPException(status_code=503, detail="Course access requests are not enabled yet")


def _page(request, **context):
    response = _csrf_response(request, "auth/reviewer_request.html", context)
    response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    return response


def _course_link(course: Course | None) -> str | None:
    if not course or not course.moodle_origin or not (course.moodle_course_id or "").isdigit():
        return None
    try:
        return canonical_https_url(f"{course.moodle_origin}/course/view.php?id={course.moodle_course_id}", "course link", max_length=4096)
    except ValueError:
        return None


@router.get("/request/{course_id}")
def request_page(request: Request, course_id: uuid.UUID, mode: str = "", db: DbSession = Depends(get_session)):
    course = db.get(Course, course_id)
    if not course or not course.is_confirmed:
        raise HTTPException(status_code=404, detail="Course not enabled for review")
    return _page(request, course=course, signin=mode == "signin", admin_first=get_settings().reviewer_access_enabled)


@router.post("/request/{course_id}")
async def submit_request(request: Request, course_id: uuid.UUID, mailer=Depends(request_mailer), db: DbSession = Depends(get_session)):
    form = await _form_with_csrf(request)
    email = form.get("email", "").strip().lower()
    settings = get_settings()
    signin = form.get("mode") == "signin"
    generic = "If this address is eligible, follow the email instructions. New requests need admin approval, then confirm your email in this same Chrome profile. Return to Moodle and choose Check access."
    if isinstance(mailer, str) and not settings.reviewer_access_enabled and (course_id != settings.notification_pilot_course_id or email != settings.notification_pilot_recipient):
        return _page(request, message="This course access pilot is not available for that address.")
    try:
        proof, browser_secret = begin(db, course_id, email, form.get("display_name", ""), mail_secret=mailer if isinstance(mailer, str) else None,
            admin_first=settings.reviewer_access_enabled, requested_role=form.get("requested_role", "beta_tester"), signin=signin)
    except AccessDenied:
        if settings.reviewer_access_enabled:
            response = _page(request, message=generic, request_link=f"/reviewer-access/request/{course_id}")
            name = course_cookie(course_id)
            saved = request.cookies.get(name, "")
            # Keep a genuine in-progress request usable, but never echo an
            # arbitrary cookie: that would disclose which addresses qualified.
            own_request = saved and db.scalar(select(ReviewerEmailChallenge.id).where(
                ReviewerEmailChallenge.course_id == course_id,
                ReviewerEmailChallenge.email == email,
                ReviewerEmailChallenge.browser_hash == token_hash(saved),
                ReviewerEmailChallenge.browser_expires_at > utc_now(),
                ReviewerEmailChallenge.exchanged_at.is_(None),
            ))
            return _browser_cookie(response, name, saved if own_request else generate_token())
        return _page(request, course=db.get(Course, course_id), message="Check the details and try again.", admin_first=False)
    if not isinstance(mailer, str) and not settings.reviewer_access_enabled:
        mailer.verification(course_id, email, proof)
    response = _page(request, message=generic if settings.reviewer_access_enabled else "Check your email and open the link in this same Chrome profile.",
                     request_link=f"/reviewer-access/request/{course_id}" if settings.reviewer_access_enabled else None)
    return _browser_cookie(response, course_cookie(course_id) if settings.reviewer_access_enabled else COOKIE, browser_secret)


@router.get("/verify")
def verify_page(request: Request):
    return _page(request, verify=True)


@router.post("/verify")
async def verify_request(request: Request, mailer=Depends(request_mailer), db: DbSession = Depends(get_session)):
    form = await _form_with_csrf(request)
    proof = form.get("proof", "")
    challenge = db.scalar(select(ReviewerEmailChallenge).where(ReviewerEmailChallenge.proof_hash == token_hash(proof)))
    cookie_name = course_cookie(challenge.course_id) if challenge and challenge.admin_first else COOKIE
    try:
        membership, created = confirm_email(db, proof, request.cookies.get(cookie_name, ""), queue_mail=isinstance(mailer, str))
    except AccessDenied:
        return _page(request, message="This link is expired, already used, or opened in a different Chrome profile.")
    if created and not isinstance(mailer, str):
        mailer.admin_request(db.get(User, membership.user_id), db.get(Course, membership.course_id))
    if membership.state is MembershipState.APPROVED:
        course = db.get(Course, membership.course_id)
        return _page(request, message="Email verified. You already have access to this course.",
                     course_link=_course_link(course))
    course = db.get(Course, membership.course_id)
    return _page(request, message="Email verified. Waiting for admin approval.",
                 course_link=_course_link(course), awaiting_approval=True)


@router.get("/finish/{course_id}")
def finish(request: Request, course_id: uuid.UUID, redirect_uri: str, db: DbSession = Depends(get_session)):
    if redirect_uri not in extension_redirect_uris() or "#" in redirect_uri:
        raise HTTPException(status_code=400, detail="Unapproved redirect URI")
    browser_secret = request.cookies.get(course_cookie(course_id), "")
    scoped = True
    if not browser_secret:
        browser_secret = request.cookies.get(COOKIE, "")
        scoped = False
    challenge = db.scalar(select(ReviewerEmailChallenge).where(
        ReviewerEmailChallenge.course_id == course_id,
        ReviewerEmailChallenge.browser_hash == token_hash(browser_secret),
        ReviewerEmailChallenge.admin_first.is_(scoped),
        ReviewerEmailChallenge.browser_expires_at > utc_now(),
        ReviewerEmailChallenge.exchanged_at.is_(None),
        ReviewerEmailChallenge.confirmed_at.is_not(None),
    ))
    member = None if challenge is None else db.scalar(select(CourseMembership).join(User, User.id == CourseMembership.user_id).where(
        CourseMembership.course_id == course_id, CourseMembership.state == MembershipState.APPROVED,
        User.email == challenge.email, User.approved_at.is_not(None), User.deleted_at.is_(None)))
    params = {"reviewer_code": browser_secret} if member else {"reviewer_status": "not-ready"}
    return RedirectResponse(f"{redirect_uri}#{urlencode(params)}", status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


class ReviewerExchange(BaseModel):
    course_id: uuid.UUID
    code: str = Field(min_length=32, max_length=128)


@router.post("/exchange")
def exchange_request(payload: ReviewerExchange, db: DbSession = Depends(get_session)):
    try:
        return _access_json(exchange(db, payload.course_id, payload.code))
    except AccessDenied as exc:
        raise HTTPException(status_code=403, detail="Course access is not ready") from exc
