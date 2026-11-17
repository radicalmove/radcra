"""Per-course enrollment policy; never enable all courses through a global flag."""
import json
from sqlalchemy import select
from app.models import AuditEvent, CourseMembership, MembershipState, User, UserRole
from app.security import utc_now
from app.services.access import AccessDenied

LEARN_ORIGIN = "https://learn.canterbury.ac.nz"


def is_learn(course):
    return bool(course and course.is_confirmed and course.moodle_origin == LEARN_ORIGIN)


def enrollment_enabled(settings, course):
    from app.services.learn_trial import mail_configured
    return is_learn(course) and bool(course.email_onboarding_enabled) and mail_configured(settings)


def managed_course(course):
    # A deliberate admin opt-in transitions the old invited-only trial.
    return bool(course and course.moodle_origin == LEARN_ORIGIN) and (course.moodle_course_id != "3598"
        or course.email_onboarding_enabled or course.email_onboarding_configured)


def require_admin(actor):
    if not actor or actor.role is not UserRole.ADMIN or not actor.approved_at or actor.deleted_at:
        raise AccessDenied("Administrator access required")


def set_enrollment(db, actor, course, enabled):
    require_admin(actor)
    if not is_learn(course) or type(enabled) is not bool:
        raise AccessDenied("Select a confirmed LEARN course")
    course.email_onboarding_enabled = enabled
    course.email_onboarding_configured = True
    db.add(AuditEvent(actor_user_id=actor.id, action="course.enrollment_changed", entity_type="course",
        entity_id=str(course.id), details=json.dumps({"enabled":enabled}), created_at=utc_now()))
    db.commit()


def approved_email(db, course, email):
    return bool(is_learn(course) and db.scalar(select(CourseMembership.id).join(User, User.id == CourseMembership.user_id).where(
        CourseMembership.course_id == course.id, CourseMembership.state == MembershipState.APPROVED,
        User.email == email, User.approved_at.is_not(None), User.deleted_at.is_(None),
        User.role != UserRole.ADMIN)))
