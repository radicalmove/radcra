# Sphere publishing repair and admin polish implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution with verification gates.

**Goal:** Restore automated public-site publication and ship a professional, consistently branded administration UI without altering access controls.

**Architecture:** Isolate website authentication in its existing workflow. Share admin presentation through a Jinja shell and scoped CSS; retain handlers and form contracts.

**Tech Stack:** GitHub Actions/CLI, SSH deploy keys, FastAPI/Jinja, CSS, pytest and headless Chromium.

## 1. Publishing repair

- [ ] Add a failing regression test in `server/tests/test_site_publishing.py` requiring the dedicated secret, strict host checking, explicit cleanup and no personal token dependency.
- [ ] Update `.github/workflows/pages.yml` to prepare a temporary SSH key and trusted host file, clone/push the existing target with that key, and clean it on exit. Preserve the existing path allowlist.
- [ ] Create a private temporary deploy key; register the public key on only the target repo and pipe the private key into the source Actions secret. Validate with `git ls-remote`; remove the local temporary private key afterwards.
- [ ] Run regression tests, commit only workflow/test changes, and push the feature branch. Dispatch the existing workflow against that exact branch and verify success plus public website responses. No main-branch merge or unrelated site content is needed for the proof run. Once verified, integrate only the workflow repair into main so future automatic publications use the fixed credentials.

## 2. Admin presentation

- [ ] Add failing rendered-response tests to `server/tests/test_admin_routes.py` for branding, active navigation, pending-first ordering, migration-shell reuse and retained CSRF form actions. Add anonymous and reviewer denial checks.
- [ ] Create `server/app/templates/admin/shell.html`. Convert `admin/users.html` and `admin/course_migration.html` to extend it. Modify only HTML structure/copy and `server/app/static/admin.css`.
- [ ] Use scoped blue/white tokens, readable cards and tables, 44px controls, focus indicators, natural checkbox sizing and responsive navigation/overflow regions. Do not add external dependencies or change server handlers.
- [ ] Run targeted tests, full backend suite and headless browser checks at desktop and phone widths with synthetic data; inspect rendered screenshots.
- [ ] Request independent code review and resolve blockers. Commit and push only these changes, leaving unrelated edits intact.

## 3. Release and handoff

- [ ] Stage a new immutable backend release from the committed tree; compare old/new contents and confirm no schema changes. Preserve the previous release and unit override.
- [ ] Point app and mail worker to the same release, reload/restart only the app, and verify health, schema18, existing UCO visibility, course3598 setting and notification timer. Roll back the working directory on a failed gate.
- [ ] Verify the deployed UI assets and admin protections over HTTPS. Record release, commit, test and workflow evidence; do not claim a human Chrome sign-in if only synthetic browser and live HTTP checks were performed.
