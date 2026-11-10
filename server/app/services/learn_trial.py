"""Single-course trial policy; keep the existing UCO access paths independent."""

from sqlalchemy import and_, select

from app.models import Course

ORIGIN = "https://learn.canterbury.ac.nz"
COURSE_NUMBER = "3598"


def trial_course_condition():
    return and_(Course.moodle_origin == ORIGIN, Course.moodle_course_id == COURSE_NUMBER)


def is_trial_course(course):
    return bool(course and course.moodle_origin == ORIGIN and course.moodle_course_id == COURSE_NUMBER)


def trial_course_id(db):
    return db.scalar(select(Course.id).where(trial_course_condition()))


def trial_email(settings):
    return (settings.reviewer_access_learn_trial_email or "").strip().lower()


def email_trial_enabled(settings, course):
    return is_trial_course(course) and bool(trial_email(settings))


def mail_configured(settings):
    return all((settings.reviewer_access_mail_secret, settings.reviewer_access_admin_email,
                settings.reviewer_access_origin, settings.reviewer_access_sender))


def trial_member_allowed(settings, course, email):
    return (settings.reviewer_access_enabled or not is_trial_course(course)
            or (email_trial_enabled(settings, course) and email == trial_email(settings) and mail_configured(settings)))


def challenge_allowed(settings, course, challenge):
    if settings.reviewer_access_enabled:
        return True
    if is_trial_course(course):
        return challenge.admin_first and bool(trial_email(settings)) and challenge.email == trial_email(settings) and mail_configured(settings)
    return not challenge.admin_first
