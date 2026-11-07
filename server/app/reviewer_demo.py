"""Isolated Store-review environment. Never loaded by the live app entry point."""

from collections import defaultdict, deque
from html import escape
import hmac
import json
import os
from pathlib import Path
from secrets import token_urlsafe
from time import monotonic
from urllib.parse import urlencode
import uuid

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
import httpx
from sqlalchemy import select

ORIGIN = "https://fld-mini.tail4ccaba.ts.net:8443"


def build_demo(directory: Path | None = None, factory=None):
    directory = directory or Path(os.environ["SPHERE_REVIEW_DEMO_HOME"])
    access = json.loads((directory / "private/access.json").read_text())
    courses = json.loads((directory / "private/courses.json").read_text())
    from app.config import get_settings
    from app.db import Base, SessionLocal, engine, get_session
    from app.main import create_app
    from app.models import CourseMembership, MembershipState, UserRole
    from app.security import token_hash, utc_now
    from app.services.access import _issue_access
    from app.services.accounts import register_account
    from app.services.courses import register_course

    if factory is None:
        expected = f"sqlite+pysqlite:///{directory}/sphere.db"
        if get_settings().database_url != expected:
            raise RuntimeError("Demo requires its own SQLite database")
        Base.metadata.create_all(engine)
        factory = SessionLocal
    app = create_app()
    def db_session():
        with factory() as db:
            yield db
    app.dependency_overrides[get_session] = db_session
    membership_ids = {}
    with factory() as db:
        from app.models import User
        user = db.scalar(select(User).where(User.email == access["sphere_email"]))
        if user is None:
            user = register_account(db, email=access["sphere_email"], password=access["sphere_password"], display_name="Demo Reviewer")
        user.approved_at = utc_now()
        for item in courses:
            course = register_course(db, course_url=f"{ORIGIN}/course/view.php?id={item['id']}", moodle_course_id=item["id"], title=item["title"])
            member = db.scalar(select(CourseMembership).where(CourseMembership.course_id == course.id, CourseMembership.user_id == user.id))
            if member is None:
                member = CourseMembership(course_id=course.id, user_id=user.id, role=UserRole.LD_DCD, state=MembershipState.APPROVED, created_at=utc_now(), updated_at=utc_now())
                db.add(member)
                db.flush()
            membership_ids[str(course.id)] = member.id
        db.commit()

    codes = {}
    failures = defaultdict(deque)
    settings = get_settings()
    redirects = {x.strip() for x in settings.extension_redirect_uris.split(",") if x.strip()}
    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}

    @app.middleware("http")
    async def demo_gate(request, call_next):
        # Cookies are shared across ports on a hostname. Discard every cookie
        # from the existing pilot/test Moodle before handling a demo request.
        request.scope["headers"] = [
            (name, value) if name.lower() != b"cookie" else
            (name, "; ".join(part.strip() for part in value.decode("latin1").split(";")
                             if part.strip().startswith(("demo_csrf=", "MoodleSessionSphereDemo=", "MOODLEID1_SphereDemo="))).encode("latin1"))
            for name, value in request.scope["headers"]
        ]
        path = request.url.path
        api_allowed = path.startswith(("/api/comments", "/api/attachments")) or path in {
            "/api/me", "/api/access/course", "/api/access/renew", "/api/courses/resolve",
        }
        if path.startswith(("/admin", "/register", "/login", "/auth", "/extension", "/api/")):
            # Moodle login belongs to Moodle, not the Sphere admin application.
            if path.startswith("/login/"):
                return await proxy_moodle(request)
            if not api_allowed:
                return Response(status_code=404)
        if api_allowed or path == "/health" or path.startswith("/reviewer-access/"):
            return await call_next(request)
        return await proxy_moodle(request)

    async def proxy_moodle(request):
        # Fixed loopback destination: request input can never select a host.
        proxy_headers = {key: value for key, value in request.headers.items() if key.lower() not in {"connection", "content-length", "accept-encoding"}}
        proxy_headers.update({"host": "fld-mini.tail4ccaba.ts.net:8443", "x-forwarded-proto": "https"})
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as proxy:
            result = await proxy.request(request.method, f"http://127.0.0.1:8091{request.url.path}", params=request.url.query, headers=proxy_headers, content=await request.body())
        response = Response(result.content, status_code=result.status_code)
        response.raw_headers = [(k, v) for k, v in result.headers.raw if k.lower() not in {b"content-encoding", b"content-length", b"transfer-encoding", b"connection"}]
        response.headers["Content-Length"] = str(len(result.content))
        return response

    @app.get("/reviewer-access/request/{course_id}")
    async def request_demo(course_id: str):
        if course_id not in membership_ids:
            raise HTTPException(404)
        return HTMLResponse('<h1>Sphere reviewer demonstration</h1><p>Use the demo password supplied in the Store Test instructions. Return to the Moodle course and choose Sign in, then Check access. This demonstration does not send email or create new accounts.</p>', headers=headers)

    @app.get("/reviewer-access/finish/{course_id}")
    async def sign_in_demo(request: Request, course_id: str, redirect_uri: str):
        if course_id not in membership_ids or redirect_uri not in redirects:
            raise HTTPException(400)
        csrf = token_urlsafe(32)
        markup = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
        <title>Sphere demo sign-in</title><style>body{{font:18px system-ui;max-width:550px;margin:8vh auto;padding:24px;background:#f4f9ff;color:#0c447c}}input,button{{font:inherit;padding:12px;margin:12px 0}}label{{display:block}}button{{background:#185fa5;color:white;border:0;border-radius:6px}}</style>
        <h1>Sphere demo sign-in</h1><p>Dummy course data only. Use the Sphere password supplied with the reviewer instructions.</p>
        <form method="post"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="redirect_uri" value="{escape(redirect_uri, quote=True)}"><label>Demo password <input name="password" type="password" autocomplete="current-password" required></label><button>Connect to this course</button></form></html>"""
        response = HTMLResponse(markup, headers=headers)
        response.set_cookie("demo_csrf", csrf, secure=True, httponly=True, samesite="lax", max_age=600)
        return response

    @app.post("/reviewer-access/finish/{course_id}")
    async def finish_demo(request: Request, course_id: str):
        form = await request.form()
        redirect = str(form.get("redirect_uri", ""))
        csrf = str(form.get("csrf", ""))
        if course_id not in membership_ids or redirect not in redirects or not csrf or not hmac.compare_digest(csrf, request.cookies.get("demo_csrf", "")):
            raise HTTPException(403)
        address = request.client.host if request.client else "unknown"
        attempts = failures[address]
        now = monotonic()
        while attempts and now - attempts[0] > 600:
            attempts.popleft()
        if len(attempts) >= 15:
            raise HTTPException(429, "Wait before trying again")
        if not hmac.compare_digest(str(form.get("password", "")), access["sphere_password"]):
            attempts.append(now)
            raise HTTPException(403, "Incorrect demo password")
        for digest, (_, expires) in list(codes.items()):
            if expires <= now:
                del codes[digest]
        if len(codes) >= 200:
            raise HTTPException(429)
        code = token_urlsafe(40)
        codes[token_hash(code)] = (course_id, now + 120)
        return RedirectResponse(f"{redirect}#{urlencode({'reviewer_code': code})}", status_code=303, headers=headers)

    @app.post("/reviewer-access/exchange")
    async def exchange_demo(request: Request):
        body = await request.json()
        digest = token_hash(str(body.get("code", "")))
        saved = codes.get(digest)
        if not saved or saved[0] != body.get("course_id") or saved[1] <= monotonic():
            raise HTTPException(403, "Invalid demo access code")
        del codes[digest]
        with factory() as db:
            member = db.get(CourseMembership, membership_ids[saved[0]])
            token, device = _issue_access(db, member)
            db.commit()
        return {"state": "approved", "role": "ld_dcd", "session_token": token, "expires_in": 28800, "device_credential": device}

    return app
