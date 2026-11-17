# Per-course LEARN onboarding: production rollout

18 November 2026 NZ time (17 November UTC). User explicitly approved a controlled server rollout followed by enabling the first LEARN course. This supersedes the staging-only hold for this server change, not for any Chrome Store or public-site operation.

## Released

- Backend commit: `662c4e9`, from `codex/learn-course-onboarding`.
- Release: `/home/fldadmin/sphere-course-release.lJ2wGYsi/server` on fld-mini.
- Previous release retained: `/home/fldadmin/sphere-0.6.17-stage.UYH6CgdB/server`.
- PostgreSQL schema: `20261110_17` → `20261118_18`.
- App and notification worker now use the same new release through `98-sphere-course-onboarding.conf` working-directory overrides. Prior units/drop-ins, runtime environment and environment file were preserved privately under the release directory; no secret values are recorded here.
- The global reviewer access switch remains false. Existing trial configuration is retained, but course 3598 deliberately uses the new managed per-course policy.

## Gates completed

1. Fresh local backend suite: **324 passed**, one existing Starlette/httpx deprecation warning. The earlier staging/browser/database-copy evidence remains in `sphere-learn-course-onboarding-staging.md`.
2. Mail queue was empty; paused its timer and verified no active worker before stopping the web service to freeze writes.
3. Created a matched native backup: `/home/fldadmin/backups/beta-testing-app/20261117T190357.859036Z-native`. All file checksums passed.
4. Restored that fresh backup into a private Unix-socket-only disposable PostgreSQL 16 cluster. Verified schema, every original table's row fingerprints, and attachment archive count. Stopped and removed only the disposable restore cluster; the backup remains.
5. Applied migration 18. Every original row fingerprint matched the frozen baseline. This includes 19 users, 11 courses, 15 memberships, 158 comments, 158 locations, 13 replies, 428 device credentials and 601 sessions.
6. Compared every approved active user's UCO course role and visible comment IDs with the prior release: unchanged. Candidate health passed before enabling enrollment.
7. Enabled only `https://learn.canterbury.ac.nz/course/view.php?id=3598` through the audited enrollment service, acting as the existing approved administrator. This added one audit event; it did not grant memberships or transfer reviewers/comments.
8. Live HTTPS checks passed: course lookup, Name/Email/Role request form with no password field, new-browser sign-in form, anonymous reviewer-list denial (403), unauthenticated admin denial (401), and unknown-course denial (404).
9. Rechecked original data after enablement: all fingerprints except the expected new audit event still match; all UCO role/comment reads remain unchanged. CRJU160 retains **11 comments, 8 unresolved**.
10. Resumed the existing mail timer. Its next automatic run completed successfully from the new release, exit 0, and the timer scheduled its next run. No new test request, real email, comment or reviewer grant was created during these checks.

## User-facing state

- LEARN 3598 now accepts passwordless requests with name, email and requested role. An administrator chooses the actual course role; email confirmation and browser-bound access still apply.
- Other LEARN courses must be registered and explicitly enabled. Reviewer migration requires a separate source/target preview and confirmation; none was performed here.
- The first requested reviewer address is an existing reviewer account, not the administrator account. It currently has no LEARN 3598 membership; use Request access to exercise the real onboarding flow rather than silently granting it during deployment.
- The unlisted Chrome Store extension remains 0.6.17. No upload, publish, extension installation, public-site publication or public-site credential change was made.
- Live checks used actual HTTPS endpoints and read-only backend visibility comparisons, not a newly signed-in human Chrome session. Full browser request/approval/email/switching coverage was performed against the isolated staging fixture before this rollout; a real new-user email approval remains the next human-facing check.

## Recovery

Retain the private pre-change backup and prior release/configuration. The new schema is additive, but do not blindly restore the old database after accepting new user activity. For a fault, pause the notification timer, disable new enrollment through the audited admin control, preserve current data, and assess a forward fix or a verified rollback. Moving the new working-directory overrides aside returns the processes to their retained prior configuration; any schema rollback must account for data written since deployment. Do not delete courses, users or comments to force a downgrade.
