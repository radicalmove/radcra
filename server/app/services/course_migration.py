"""Explicit, audited membership transfer. Course content and credentials never move."""
import hashlib
import json
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models import (AuditEvent, Course, CourseMembership, CourseMigrationMapping,
                        CourseMigrationPreview, MembershipState, User, UserRole)
from app.security import utc_now
from app.services.access import AccessDenied
from app.services.course_onboarding import require_admin
from app.services.courses import normalize_url, normalize_moodle_course_id

UCO = "https://my.uconline.ac.nz"
LEARN = "https://learn.canterbury.ac.nz"
REVIEWER_ROLES = {UserRole.BETA_TESTER, UserRole.SME, UserRole.LD_DCD}


def _resolve(db, value, origin):
    try:
        normalized = normalize_url(value)
        parsed = urlsplit(normalized)
        query = parse_qs(parsed.query)
        number = query.get("id", [])
        if (f"{parsed.scheme}://{parsed.netloc}" != origin or parsed.path != "/course/view.php"
                or parsed.fragment or set(query) != {"id"} or len(number) != 1):
            raise ValueError
        number = normalize_moodle_course_id(number[0])
        result = db.scalar(select(Course).where(Course.moodle_origin == origin,
            Course.moodle_course_id == number, Course.is_confirmed.is_(True)))
        if result is None:
            raise ValueError
        return result
    except ValueError as exc:
        raise AccessDenied("Choose registered UCO and LEARN course URLs") from exc


def _snapshot(db, source, target):
    """Lock-order independent state fingerprint, including target revocations."""
    source_rows = db.execute(select(CourseMembership, User).join(User, User.id == CourseMembership.user_id)
        .where(CourseMembership.course_id == source.id).order_by(CourseMembership.id)).all()
    target_rows = db.scalars(select(CourseMembership).where(CourseMembership.course_id == target.id)
        .order_by(CourseMembership.id)).all()
    present = {m.user_id for m in target_rows}
    rows = []
    state = {"courses": [(str(c.id), c.moodle_origin, c.moodle_course_id, c.is_confirmed, c.normalized_url)
                         for c in (source, target)],
             "source": [], "target": []}
    for m, user in source_rows:
        eligible = (m.state is MembershipState.APPROVED and m.role in REVIEWER_ROLES
            and user.approved_at is not None and user.deleted_at is None and user.role is not UserRole.ADMIN)
        reason = ("Existing target access: review manually" if user.id in present else
                  "Eligible" if eligible else "Source account or membership is not eligible")
        rows.append({"membership_id":str(m.id),"user_id":str(user.id),"name":user.display_name,
            "email":user.email,"role":m.role.value,"eligible":eligible and user.id not in present,"reason":reason})
        state["source"].append((str(m.id),str(user.id),m.role.value,m.state.value,
            str(m.updated_at), str(user.approved_at),str(user.deleted_at),user.role.value,user.email,user.display_name))
    for m in target_rows:
        state["target"].append((str(m.id),str(m.user_id),m.role.value,m.state.value,str(m.updated_at)))
    mapping = db.scalar(select(CourseMigrationMapping).where(CourseMigrationMapping.target_course_id == target.id))
    state["mapping"] = None if not mapping else str(mapping.source_course_id)
    return rows, hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()


def preview_transfer(db, actor, source_url, target_url):
    require_admin(actor)
    source, target = _resolve(db,source_url,UCO), _resolve(db,target_url,LEARN)
    rows, fingerprint = _snapshot(db,source,target)
    mapping = db.scalar(select(CourseMigrationMapping).where(CourseMigrationMapping.target_course_id == target.id))
    if mapping and mapping.source_course_id != source.id:
        raise AccessDenied("This LEARN course is already mapped to another UCO course")
    p = CourseMigrationPreview(actor_user_id=actor.id, source_course_id=source.id,target_course_id=target.id,
        rows=rows,fingerprint=fingerprint,created_at=utc_now(),expires_at=utc_now()+timedelta(minutes=20))
    db.add(p); db.commit(); db.refresh(p)
    return p


def apply_transfer(db, actor, preview_id, selected):
    require_admin(actor)
    # All transfer operators lock the target before the preview. Unique membership
    # constraints also reject conflicts introduced by other account-admin paths.
    initial = db.get(CourseMigrationPreview,preview_id)
    if not initial or initial.actor_user_id != actor.id:
        raise AccessDenied("Preview not found")
    target = db.scalar(select(Course).where(Course.id == initial.target_course_id).with_for_update()
        .execution_options(populate_existing=True))
    p = db.scalar(select(CourseMigrationPreview).where(CourseMigrationPreview.id == preview_id)
        .with_for_update().execution_options(populate_existing=True))
    source = db.get(Course,p.source_course_id,populate_existing=True)
    selection = sorted(set(selected))
    if not selection or len(selection) != len(selected):
        raise AccessDenied("Select the reviewers to transfer")
    if p.applied_at:
        if selection != p.selection:
            raise AccessDenied("This preview was already applied with a different selection")
        return p.result
    if p.expires_at.replace(tzinfo=utc_now().tzinfo) <= utc_now():
        raise AccessDenied("Preview expired; create a new preview")
    if not source or not target or not source.is_confirmed or not target.is_confirmed:
        raise AccessDenied("Course is no longer confirmed")
    # Revalidate stable URLs and origin identities, not just course UUIDs.
    if _resolve(db,source.normalized_url,UCO).id != source.id or _resolve(db,target.normalized_url,LEARN).id != target.id:
        raise AccessDenied("Course identity changed")
    # Read locks prevent concurrent source role/revocation changes until commit.
    db.scalars(select(CourseMembership).where(CourseMembership.course_id.in_([source.id,target.id]))
        .order_by(CourseMembership.id).with_for_update().execution_options(populate_existing=True)).all()
    db.scalars(select(User).join(CourseMembership,CourseMembership.user_id==User.id)
        .where(CourseMembership.course_id==source.id).order_by(User.id)
        .with_for_update(of=User).execution_options(populate_existing=True)).all()
    rows, fingerprint = _snapshot(db,source,target)
    if fingerprint != p.fingerprint:
        raise AccessDenied("Access changed since preview; create a new preview")
    eligible = {r["membership_id"]:r for r in rows if r["eligible"]}
    if not set(selection).issubset(eligible):
        raise AccessDenied("Invalid selection; create a new preview")
    now, results = utc_now(), []
    try:
        mapping = db.scalar(select(CourseMigrationMapping).where(CourseMigrationMapping.target_course_id==target.id))
        if not mapping:
            db.add(CourseMigrationMapping(source_course_id=source.id,target_course_id=target.id,
                                         actor_user_id=actor.id,created_at=now))
        elif mapping.source_course_id != source.id:
            raise AccessDenied("Destination has a different source mapping")
        for key in selection:
            row=eligible[key]
            member=CourseMembership(user_id=uuid.UUID(row["user_id"]),course_id=target.id,
                role=UserRole(row["role"]),state=MembershipState.APPROVED,
                approved_by_user_id=actor.id,approved_at=now,created_at=now,updated_at=now)
            db.add(member); db.flush()
            results.append(str(member.id))
        p.applied_at,p.selection,p.result=now,selection,results
        db.add(AuditEvent(actor_user_id=actor.id,action="course.reviewers_transferred",
            entity_type="course_migration",entity_id=str(p.id),created_at=now,
            details=json.dumps({"source":str(source.id),"target":str(target.id),
                                "selected":selection,"created":results})))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AccessDenied("Access changed during transfer; create a new preview") from exc
    return results
