from pathlib import Path


def test_site_publishing_uses_repo_scoped_ssh_key_with_verified_hosts():
    workflow = Path('../.github/workflows/pages.yml').read_text()
    assert 'secrets.SPHERE_PAGES_DEPLOY_KEY' in workflow
    assert 'SPHERE_PAGES_REPOSITORY_TOKEN' not in workflow
    assert 'StrictHostKeyChecking=yes' in workflow
    assert 'https://api.github.com/meta' in workflow
    assert 'trap ' in workflow and 'EXIT' in workflow
    assert 'chmod 600' in workflow
    assert 'git@github.com:radicalmove/radicalmove.github.io.git' in workflow
    assert 'git -C "$pages" add sphere radcra' in workflow
    assert 'persist-credentials: false' in workflow
