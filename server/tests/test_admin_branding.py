import re
from datetime import UTC, datetime

import pytest

from test_admin_routes import client
from app.models import UserRole
from app.services.accounts import register_account


def sign_in(client, role=UserRole.ADMIN):
    with client.db_factory() as db:
        user = register_account(db, email='brand-admin@example.test', password='long enough password')
        user.role, user.approved_at = role, datetime.now(UTC)
        db.commit()
    assert client.post('/auth/login', json={'email':'brand-admin@example.test','password':'long enough password'}).status_code == 200


@pytest.mark.parametrize('path,active', [('/admin/users','Course access'),('/admin/course-migration','Reviewer transfers')])
def test_admin_pages_share_branded_shell_and_current_navigation(client, path, active):
    sign_in(client)
    page = client.get(path)
    assert page.status_code == 200
    assert 'class="sphere-admin-app"' in page.text
    assert '/static/sphere-logo.png' in page.text and '/static/admin.css' in page.text
    assert 'class="admin-banner"' in page.text
    assert 'aria-label="Administration"' in page.text
    assert re.search(r'aria-current="page"[^>]*>' + active + r'</a>', page.text)
    assert 'href="#sphere-admin"' in page.text
    assert '/static/sphere-auth.css' not in page.text
    assert 'name="viewport"' in page.text
    assert 'https://fonts.' not in page.text
    for form in re.findall(r'<form\b.*?</form>', page.text, flags=re.S):
        if 'method="post"' in form:
            assert 'name="csrf_token"' in form


def test_pending_requests_stay_before_course_selection_and_have_empty_state(client):
    sign_in(client)
    page = client.get('/admin/users')
    assert page.text.index('id="pending-requests"') < page.text.index('1. Select a course')
    assert 'class="admin-empty"' in page.text
    assert 'No course access requests waiting for approval.' in page.text


@pytest.mark.parametrize('path', ['/admin/users','/admin/course-migration'])
def test_admin_polish_does_not_open_pages_to_anonymous_or_reviewers(client, path):
    assert client.get(path).status_code == 401
    sign_in(client, UserRole.SME)
    assert client.get(path).status_code == 403
