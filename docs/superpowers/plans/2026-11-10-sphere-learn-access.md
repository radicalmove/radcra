# Sphere LEARN and reviewer access implementation plan

> Use superpowers:subagent-driven-development for implementation and review. Work only in the isolated `codex/sphere-learn` checkout; no deploy or Store operations.

**Goal:** A separately testable two-host Sphere build with admin-first passwordless reviewer access and branded sign-in.

**Architecture:** Extend the staged server and its captured email fixture, migrate LMS identities to origin plus course ID, add the trusted-device email reconnect path to the extension, and exercise both with local Chrome.

**Tech stack:** FastAPI, SQLAlchemy, Alembic, TypeScript, Chrome MV3, Playwright.

- [ ] Baseline copied backend and extension in the isolated worktree; run `pytest tests` from server and `npm test` from extension.
- [ ] Server identity (`models.py` Course, `services/courses.py`, related routes, migration 16): write failing same-ID LEARN/UCO and migration tests; implement composite uniqueness and reject mismatched/unsafe origin; prove preservation of course UUIDs.
- [ ] Server onboarding (`reviewer_email_access.py`, `reviewer_request.py`, admin and mail, migration 17): test pending unverified request, admin assignment, link delivery only after approval, browser binding, replay/expiry, access only after both gates, and existing approved member verification. Preserve legacy paths outside the isolated staging configuration.
- [ ] Extension (`reviewer-course-access.ts`, `background.ts`, `overlay/root.ts`): test remembered credential plus matching email, new device fallback and initial Request access. Produce a separate dev build restricted to exact LEARN/UCO hosts and loopback staging, no Store key or live service origin.
- [ ] Brand reviewer request/confirmation and admin sign-in using existing logo, scoped auth CSS, keyboard/focus/mobile checks. Verify request form has Name, Email address, Requested role, Request access and no password.
- [ ] Full local browser test with captured inbox, confirm assigned role and same-browser reconnect; check actual designated LEARN course without modifying Moodle or using live Sphere. Run both suites, version/package test and isolated deployment evidence; leave live pilot and Store untouched.
