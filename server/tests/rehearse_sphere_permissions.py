"""Exercise copied memberships through the candidate API without exposing data."""

import os
from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.engine import make_url


def main():
    url = make_url(os.environ["DATABASE_URL"])
    socket = Path(url.query.get("host", ""))
    if (url.database != "sphere_rehearsal" or url.host or socket.parent != Path("/tmp")
            or not socket.name.startswith("sphere-upgrade-")):
        raise SystemExit("Not a disposable rehearsal database")

    from app.config import get_settings
    from app.db import SessionLocal
    from app.main import app
    from app.models import Course, CourseMembership, MembershipState, User, UserRole
    from app.services.access import _issue_access
    from app.services.accounts import create_dashboard_session
    from app.services.courses import register_course
    from app.services.reviewer_email_access import begin, confirm_email, exchange

    uco = "https://my.uconline.ac.nz"
    learn = "https://learn.canterbury.ac.nz"
    get_settings().reviewer_access_enabled = True
    with SessionLocal() as db, TestClient(app, base_url="https://rehearsal.invalid") as client:
        unscoped = db.execute(text("""
            SELECT count(*) FROM sessions s JOIN users u ON s.user_id = u.id
            WHERE s.kind = 'extension' AND s.membership_id IS NULL AND u.role <> 'admin'
              AND u.deleted_at IS NULL AND s.revoked_at IS NULL AND s.expires_at > now()
        """)).scalar_one()
        print(f"Active legacy reviewer sessions requiring course sign-in if email access is enabled: {unscoped}")
        courses = db.scalars(select(Course).where(Course.moodle_origin == uco, Course.is_confirmed.is_(True))).all()
        assert courses, "No copied UCO courses to exercise"
        learn_course = register_course(db, course_url=f"{learn}/course/view.php?id=3598",
                                       title="LEARN rehearsal", moodle_course_id=3598)
        uco_course = next((c for c in courses if c.moodle_course_id == "3598"), courses[0])
        same_number = register_course(db, course_url=f"{learn}/course/view.php?id={uco_course.moodle_course_id}",
                                       title="LEARN identity rehearsal", moodle_course_id=uco_course.moodle_course_id)
        assert same_number.id != uco_course.id
        for host, course in [(uco, uco_course), (learn, same_number)]:
            lookup = client.post("/api/access/course", json={"moodle_origin": host, "moodle_course_id": int(course.moodle_course_id)})
            assert lookup.status_code == 200 and lookup.json()["course_handle"] == str(course.id)
        rows = db.execute(select(CourseMembership, User).join(User, User.id == CourseMembership.user_id).where(
            CourseMembership.course_id.in_([course.id for course in courses]),
            CourseMembership.state == MembershipState.APPROVED,
            User.deleted_at.is_(None), User.approved_at.is_not(None),
        )).all()
        assert rows, "No approved copied UCO membership to exercise"
        shown = set()
        for member, user in rows:
            token, _ = _issue_access(db, member)
            db.commit()
            headers = {"Authorization": f"Bearer {token}"}
            me = client.get("/api/me", params={"course_id": str(member.course_id)}, headers=headers)
            assert me.status_code == 200 and me.json()["user"]["role"] == member.role.value
            comments = client.get("/api/comments", params={"course_id": str(member.course_id)}, headers=headers)
            assert comments.status_code == 200
            shown.update(comment["id"] for comment in comments.json())
            denied = client.get("/api/comments", params={"course_id": str(learn_course.id)}, headers=headers)
            assert denied.status_code == 404, "UCO approval granted unintended LEARN access"
        print(f"Copied approved UCO memberships exercised: {len(rows)}; distinct visible comments: {len(shown)}")
        print("LEARN course lookup, same-number isolation and cross-course authorization passed.")

        eligible = []
        reserved = set()
        for member, user in rows:
            if user.role is UserRole.ADMIN:
                continue
            try:
                validate_email(user.email, check_deliverability=False, allow_smtputf8=False)
            except EmailNotValidError:
                reserved.add(user.id)
            else:
                eligible.append((member, user))
        print(f"Copied reviewer accounts with non-mail-eligible addresses: {len(reserved)}")
        assert eligible, "No copied UCO reviewer with a mail-eligible address"
        original, reviewer = eligible[0]
        prior_user_id, prior_role = reviewer.id, original.role
        proof, browser = begin(db, learn_course.id, reviewer.email, reviewer.display_name, admin_first=True)
        pending = db.scalar(select(CourseMembership).where(
            CourseMembership.course_id == learn_course.id, CourseMembership.user_id == prior_user_id))
        assert pending is not None and pending.state is MembershipState.PENDING
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN, User.deleted_at.is_(None),
                                            User.approved_at.is_not(None)).limit(1))
        assert admin is not None
        client.cookies.set("dashboard_session", create_dashboard_session(db, admin))
        client.get("/login")
        approval = client.post(f"/admin/memberships/{pending.id}/approve-request",
                               data={"csrf_token": client.cookies["csrf_token"], "role": "sme"},
                               follow_redirects=False)
        assert approval.status_code == 303
        db.expire_all()  # Approval was committed by a different request session.
        confirmed, _ = confirm_email(db, proof, browser)
        assert confirmed.user_id == prior_user_id and confirmed.role is UserRole.SME
        access = exchange(db, learn_course.id, browser)
        headers = {"Authorization": f"Bearer {access.session_token}"}
        me = client.get("/api/me", params={"course_id": str(learn_course.id)}, headers=headers)
        assert me.status_code == 200 and me.json()["user"]["role"] == "sme"
        assert client.get("/api/comments", params={"course_id": str(original.course_id)}, headers=headers).status_code == 404
        db.refresh(original)
        assert original.role is prior_role and original.state is MembershipState.APPROVED
        print("An existing UCO reviewer gained separately approved LEARN access on the same user ID; UCO role unchanged.")


if __name__ == "__main__":
    main()
