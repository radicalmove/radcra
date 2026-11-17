# Per-course LEARN access: staging evidence

18 November 2026. Implemented on `codex/learn-course-onboarding`, not deployed.

## What is implemented

- Default-off enrollment for each registered LEARN course. An approved administrator explicitly enables or disables new email access requests in course administration.
- Admin-first approval and assigned role, followed by email proof in the requesting Chrome profile. Disabling new enrollment does not revoke already-approved memberships or trusted devices; approved reviewers can request a new-browser sign-in link.
- Explicit UCO-to-LEARN URL mapping, reviewer-selection preview, 20-minute expiry, stale-state validation, idempotent apply and audit trail. Existing target memberships, including revoked ones, are never overwritten. Only eligible approved users and non-admin source roles can transfer.
- UCO and the original course-3598 invitation trial remain on their old paths until an admin deliberately transitions that course. The global access flag is not required.
- Old comments, locations, replies, attachments, sessions and device credentials stay on the source course. Transfer and preview do not queue announcements.
- Managed LEARN courses cannot use anonymous legacy reviewer selection/sign-in. Broad legacy UCO sessions cannot access LEARN content without a course-scoped sign-in. Dashboard visibility and lead controls use the approved course membership rather than the account's global fallback role.

## Verification

- Fresh full backend suite: **324 passed**, with one existing Starlette/httpx deprecation warning.
- Extension: **538 passed, 9 intentionally skipped**; TypeScript checking passed.
- Chrome/Chromium browser tests: admin enables two courses, previews and applies a selected transfer, completes request/approval/email proof on another course, checks disabled enrollment and cross-course denial, then the extension signs in to both LEARN courses and reconnects after switching and reload.
- Browser tests use synthetic pages/accounts and captured mail at loopback-only HTTPS port 48144. The extension is compiled with staging endpoints and a fixture public key; this is not a claim that the unmodified published Store binary was routed to staging. The pending local Help-copy edits were present in the test build but are not part of this backend feature commit.
- Read-only existing-backup rehearsal on the mini: restore into a private UTF-8 PostgreSQL cluster with Unix socket only; migrate from schema 17 to 18, downgrade to 17, then upgrade to 18 again. Original row fingerprints matched on every original table, including 19 users, 10 courses, 15 memberships, 158 comments, 158 locations, 13 replies and 0 attachments.
- Two concurrent PostgreSQL applies against the same target produced one successful grant, one stale-preview rejection, one target membership and one mapping; no duplicates.
- The stopped temporary PostgreSQL copies were removed after verification. No live database migration, membership change, mail delivery, service restart or Store operation was performed.
- Independent code review found two legacy-access bypasses and a mail-queue starvation case; regression tests were written before their fixes. Final review reported no remaining blockers. Additional unconfirmed-course isolation coverage also passes.

## Reproduce locally

Run the backend tests from `server`: `../.venv/bin/python -m pytest -q`.
The browser fixture entrypoint is `tests.staging_course_migration:app`. It refuses any database other than its in-memory fixture, any global/trial bypass, or a service origin other than `https://localhost:48144`. Use synthetic mail settings and temporary local TLS certificates; no Gmail secret is needed. The `/__staging/inbox` route exposes only synthetic test credentials/mail and must never be deployed.

Build the extension for that loopback endpoint using the fixture public key and exact UCO/LEARN patterns. Configure the fixture redirect allowlist with that build's Chromium redirect URI and `https://extension.chromiumapp.org/`. Run:

```sh
SPHERE_COURSE_STAGING=1 SPHERE_COURSE_EXTENSION=1 \
  SPHERE_EXTENSION_TEST_CHROME=/path/to/Chrome-for-Testing \
  npx playwright test e2e/course-migration.spec.ts --reporter=line
```

Start with a fresh fixture for the complete two-test sequence. Run unit tests before the staging build: the existing build-config unit tests replace generated `dist` output with fixture host patterns. Running them concurrently with the browser test invalidates that build.

The PostgreSQL rehearsal helper is `server/tests/rehearse_course_onboarding.py`. It requires an already-restored disposable cluster at a `/tmp/sphere-course-rehearsal.*` socket path and never creates a live-service connection. Rehearse against a private backup copy, not the production DSN.

## Production boundary

This is ready for staging review, not an automatic rollout. Before production, approve the server migration and exact first LEARN course(s), verify real mail configuration, and take a fresh matched backup. Apply schema 18 and this backend together. Preserve the global access flag as off. Register each destination course and explicitly opt in its enrollment. Preview and confirm real reviewer transfers individually; do not infer mappings from course titles or IDs.

No new extension behavior or site permissions are required for the backend workflow. The separately pending Help and website instructions still need their own release/publication decision. The published Store version remains 0.6.17.
