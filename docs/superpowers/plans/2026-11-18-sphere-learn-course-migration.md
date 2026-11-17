# Sphere normal LEARN access implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Work in staging only; do not deploy, send real mail, change real memberships, or publish an extension.

**Goal:** Enable admin-controlled LEARN onboarding per course and explicit, previewed UCO-to-LEARN reviewer transfers without moving comments.

**Architecture:** Add a default-off enrollment setting to confirmed LEARN courses and a separate audited mapping/transfer service. Preserve UCO legacy behavior and the existing 3598 invited-email trial during rollout. Use existing user IDs, course-scoped memberships, CSRF-protected admin forms and the existing email worker.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Jinja templates, pytest, Chrome.

**Approved design:** `docs/superpowers/specs/2026-11-17-sphere-learn-course-migration-design.md`.

## Workspace and safety

- [ ] Preserve the existing uncommitted instruction edits in the current checkout. Use a dedicated integration branch in this worktree before new implementation; do not commit unrelated changes.
- [ ] Capture baseline test results with `cd server && ../.venv/bin/python -m pytest -q` and the extension type check.
- [ ] Use disposable test databases and captured mail only. Production must remain on its current configuration throughout this plan.

## Task 1: Course enrollment policy

**Files:** modify `server/app/models.py`; create `server/alembic/versions/20261118_18_learn_course_onboarding.py`, `server/app/services/course_onboarding.py`, and `server/tests/test_course_onboarding.py`.

- [ ] Write failing tests for default-off enrollment, exact LEARN origin validation, confirmed-course requirement, and independent courses sharing the same numeric Moodle ID across origins. Run the new test file and verify meaningful failures.
- [ ] Add `Course.email_onboarding_enabled` as non-null boolean with false database default. Migration must not update existing users, memberships, comments or trial configuration.
- [ ] Implement a policy helper that admits admin-first email enrollment only for a confirmed exact-origin LEARN course with its flag on and complete mail configuration. Existing approved memberships remain valid when enrollment is disabled; revocation remains a separate operation.
- [ ] Preserve the existing global mode and scoped 3598 trial as explicit legacy paths. Opt-in for 3598 must be an explicit admin transition, not a side effect of migration.
- [ ] Verify migration upgrade/downgrade on a private PostgreSQL copy, then commit only Task 1 files.

## Task 2: Access and mail routing

**Files:** modify `server/app/services/learn_trial.py`, `server/app/routers/reviewer_request.py`, `server/app/services/reviewer_email_access.py`, `server/app/services/notification_pilot.py`; extend `server/tests/test_reviewer_email_access.py` and `server/tests/test_notification_pilot.py`.

- [ ] Write failing tests for two opted-in LEARN courses, disabled courses, legacy UCO access, the unchanged 3598 trial, and incomplete mail settings.
- [ ] Apply the enrollment policy at request creation, verification, finish/exchange and mail dispatch. Do not merely expose the request form or turn on the global flag.
- [ ] Distinguish new enrollment from sign-in by an already approved member. Disabling enrollment must stop new requests and outstanding enrollment mail, but must not invalidate approved users or prevent them signing in with email proof on a new browser.
- [ ] Verify every requested role is advisory and cannot become an admin role. New requests require admin approval followed by same-profile email verification. Existing user IDs must be reused without reviving archived users.
- [ ] Preserve the existing course-specific notification recipient behavior; enrollment mail must not cause comment notifications to expand to unrelated courses.
- [ ] Run the access and notification test suites, including rejection and rate-limit cases. Commit only these changes after they pass.

## Task 3: Admin course settings and reviewer-transfer preview

**Files:** create `server/app/services/course_migration.py`, `server/app/routers/course_migration.py`, `server/app/templates/admin/course_migration.html`, and `server/tests/test_course_migration.py`; modify `server/app/main.py`, `server/app/templates/admin/users.html`.

- [ ] Write failing authorization and CSRF tests: only approved, unarchived admins can enable onboarding or apply a reviewer transfer. Ordinary reviewers and learning designers cannot bulk grant access.
- [ ] Add an explicit course-enrollment control and a link to migration setup on the admin course page. Scope enrollment changes to the exact registered course ID and origin.
- [ ] Resolve source UCO and target LEARN from explicit canonical URLs. Require confirmed courses, exact expected origins and distinct UUIDs. Never match by title or numeric ID alone.
- [ ] Produce a read-only preview showing eligible approved active users, existing source membership roles and proposed target roles. Exclude pending/revoked memberships, archived/unapproved users and admin privileges. Surface existing target memberships as manual-review conflicts, never overwrite them.
- [ ] Persist a preview record with actor, source, destination, eligible membership IDs/roles and a fingerprint. Apply only selected preview rows after explicit confirmation; reject tampered, expired or stale previews. Recheck actor, source eligibility and all target conflicts inside a transaction.
- [ ] Add a source/target mapping and transfer audit schema to migration 18 before it has been deployed anywhere. Record actor, timestamp and granted memberships. Use database uniqueness plus transaction handling so repeat requests and concurrent applies cannot duplicate grants.
- [ ] Copy membership roles and user references only. Never copy sessions, device credentials, passwords, invitations, pending requests, comments or attachments. Transfer confirmation does not implicitly enable onboarding or send mail.
- [ ] Test idempotency, partial selections, invalid roles, duplicate numeric IDs, changes after preview, previously revoked target access, concurrent conflict rollback, and untouched source comments/roles. Commit after tests pass.

## Task 4: Staging integration and handoff

**Files:** extend `server/tests/staging_reviewer_flow.py`; create a staging evidence record under `docs/`; update `docs/sphere-getting-started.md` only where necessary.

- [ ] Run all backend tests, migration tests, extension tests and type checks. Record command results, skips and environmental limitations.
- [ ] On a disposable private database copy, fingerprint existing users, memberships, comments and attachments before upgrade. Verify all original records are unchanged except intentional new schema values. Keep credentials and dumps out of Git.
- [ ] Use captured mail and synthetic reviewers to test request, admin approval, email confirmation, same-browser reconnect and new-profile sign-in on two LEARN courses. Test a disabled third course. Exercise the real admin forms in Chrome and confirm the actor and selected grants in the audit.
- [ ] Test preview/apply, then recheck source UCO permissions, comments and target isolation. Repeat apply and verify no duplicates and no messages queued.
- [ ] Test published 0.6.17 against the staging server through the existing isolated browser fixture; do not change the public Store package or use production mail. If extension code is required, prepare it separately and report the version/review implications.
- [ ] Review the complete diff and evidence, commit the scoped work, and hand off staging results. Ask for separate production rollout approval with the exact courses and reviewers listed. Do not deploy as part of this plan.
