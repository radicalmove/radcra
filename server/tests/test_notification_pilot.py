from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.models import CourseMembership, MembershipState, User, UserRole
from app.services.comments import create_comment, update_comment_status
from app.services.courses import resolve_course


def test_comment_events_queue_and_deliver_only_to_pilot_inbox(db_session, monkeypatch):
    from app.models import NotificationOutbox
    from app.services.notification_pilot import deliver_one

    now = datetime.now(UTC)
    author = User(email="author@example.test", password_hash="unused", approved_at=now, created_at=now)
    lead = User(email="lead@example.test", password_hash="unused", approved_at=now, created_at=now)
    db_session.add_all([author, lead])
    course = resolve_course(db_session, moodle_course_id=42, course_url="https://moodle.example/course/view.php?id=42", title="Private course title")
    db_session.add(CourseMembership(user_id=lead.id, course_id=course.id, role=UserRole.LD_DCD, state=MembershipState.APPROVED, created_at=now, updated_at=now))
    db_session.commit()
    settings = get_settings()
    monkeypatch.setattr(settings, "notification_pilot_course_id", course.id)
    monkeypatch.setattr(settings, "notification_pilot_recipient", "pilot@example.test")
    monkeypatch.setattr(settings, "notification_pilot_sender", "sphere@example.test")
    monkeypatch.setattr(settings, "notification_pilot_url", "https://sphere.example/")

    comment = create_comment(db_session, author, course_id=course.id, page_url="https://moodle.example/page/9", page_title="Private page", body="Private comment", anchor_type="text_highlight", selected_quote="Private quote", css_selector="#content")
    update_comment_status(db_session, lead, comment, "resolved")
    update_comment_status(db_session, lead, comment, "resolved")
    self_comment = create_comment(db_session, lead, course_id=course.id, page_url="https://moodle.example/page/9", page_title="Private page", body="Private self-comment", anchor_type="text_highlight", selected_quote="Private quote", css_selector="#content")
    update_comment_status(db_session, lead, self_comment, "resolved")
    other = resolve_course(db_session, moodle_course_id=43, course_url="https://moodle.example/course/view.php?id=43", title="Outside pilot")
    db_session.add(CourseMembership(user_id=lead.id, course_id=other.id, role=UserRole.LD_DCD, state=MembershipState.APPROVED, created_at=now, updated_at=now))
    db_session.commit()
    outside = create_comment(db_session, author, course_id=other.id, page_url="https://moodle.example/page/10", page_title="Outside pilot", body="Outside pilot", anchor_type="text_highlight", selected_quote="Outside pilot", css_selector="#content")
    update_comment_status(db_session, lead, outside, "resolved")
    assert len(db_session.scalars(select(NotificationOutbox)).all()) == 2

    def unavailable(*args):
        raise OSError("SMTP offline")

    assert deliver_one(db_session, settings, unavailable)
    assert db_session.get(type(comment), comment.id).status.value == "resolved"
    sent = []
    while deliver_one(db_session, settings, lambda message, address: sent.append((message, address)), now=now + timedelta(minutes=2)):
        pass
    assert {str(message["Subject"]) for message, _ in sent} == {"[Sphere test] New comment", "[Sphere test] Comment resolved"}
    assert len(sent) == 2
    for message, address in sent:
        assert address == str(message["To"]) == "pilot@example.test"
        assert "Open course in Moodle: https://moodle.example/course/view.php?id=42" in message.get_content()
        assert "Private" not in message.as_string()
        assert "author@example.test" not in message.as_string()
        assert "lead@example.test" not in message.as_string()

    from app.services.notification_pilot import PREVIEW_TEXT
    monkeypatch.setattr(settings, "notification_pilot_preview_comment_id", comment.id)
    update_comment_status(db_session, lead, comment, "open")
    comment.body = PREVIEW_TEXT
    update_comment_status(db_session, lead, comment, "resolved")
    assert deliver_one(db_session, settings, lambda message, address: sent.append((message, address)))
    preview = sent[-1][0].get_content()
    assert "Location: Private course title" in preview
    assert f"Comment: {PREVIEW_TEXT}" in preview
