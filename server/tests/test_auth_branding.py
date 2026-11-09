from pathlib import Path

from fastapi.testclient import TestClient


def test_admin_login_uses_sphere_brand_and_keeps_password_auth():
    from app.main import app
    with TestClient(app, base_url='https://testserver') as client:
        response = client.get('/login?next=%2Fadmin')
    assert response.status_code == 200
    assert '/static/sphere-auth.css' in response.text
    assert '/static/sphere-logo.png' in response.text
    assert 'name="viewport"' in response.text
    assert 'Admin sign-in' in response.text
    assert 'type="password"' in response.text


def test_reviewer_template_uses_same_sphere_auth_shell():
    template = Path('app/templates/auth/reviewer_request.html').read_text()
    assert 'auth/shell.html' in template
    assert 'type="password"' not in template
